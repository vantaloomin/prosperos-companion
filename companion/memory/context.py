"""Companion context builder (PRD M10), replacing the Study's Story-path assemble_memory.

Eligibility (authority, scope, exclusion, time) is applied before ranking. Character guidance and
the user's boundaries are required: if they cannot fit, the builder reports the limit instead of
dropping them. Everything else is added in priority order until the budget is spent, and the
receipt records what was included and what was left out, by identity only.
"""
from dataclasses import dataclass, field
from datetime import datetime

from companion.clock import parse, stamp, zone
from companion.database import many, settings
from companion.errors import DomainError
from companion.events import committed
from companion.memory.budget import token_estimate
from companion.memory.chunks import compile_chunks
from companion.memory.hybrid_recall import hybrid_hits
from companion.memory.records import OPEN_PLANS, blocked_messages, eligible

RECENT_MESSAGES = 24
RECALL_LIMIT = 8
RECENT_EVENTS = 5
RECALLED_LAYERS = {'shared_experience', 'relationship', 'companion_life', 'plan'}

GUIDANCE = (
    'You are {name}, a fictional companion talking with the user. Speak as {name} in your own voice. '
    'Describe only your own fictional actions, feelings and plans; never decide what the user does, feels, '
    'agrees to or did while away. Your fictional life is not evidence about the real world. '
    'Use remembered details naturally when relevant instead of announcing that you remember them. '
    'Relationship framing: {relationship}. Treat anything marked as a boundary as binding.'
)
HEADINGS = {'boundaries': "The user's boundaries", 'time': 'Time', 'profile': 'What you know about the user',
            'commitments': 'Open plans and commitments', 'temporary': "The user's current circumstances",
            'companion_life': 'Your recent life (committed fictional events)',
            'recalled': 'Possibly relevant memories'}


@dataclass
class Packet:
    budget: int
    sections: dict = field(default_factory=dict)
    included: dict = field(default_factory=dict)
    omitted: dict = field(default_factory=dict)
    used: int = 0

    def require(self, section, identity, text):
        self.used += token_estimate(text)
        if self.used > self.budget:
            raise DomainError('Required character guidance and boundaries do not fit the model context. '
                              'Increase the context allowance or shorten them.', 422, 'context_limit')
        self.place(section, identity, text)

    def offer(self, section, identity, text) -> bool:
        cost = token_estimate(text)
        if self.used + cost > self.budget:
            self.omitted.setdefault(section, []).append(identity)
            return False
        self.used += cost
        self.place(section, identity, text)
        return True

    def place(self, section, identity, text):
        self.sections.setdefault(section, []).append(text)
        self.included.setdefault(section, []).append(identity)


NEUTRAL_ABSENCE = 'Time apart is fine with you: do not express hurt, guilt or pressure about absence.'


def character_text(version) -> str:
    """How the character feels about absence is a user-chosen trait; product controls stay neutral."""
    definition = version['definition']
    lines = [GUIDANCE.format(name=definition['name'], relationship=definition['relationship'])]
    reaction = definition.get('absence_reaction')
    lines.append(f'How you react to time apart, in character: {reaction}' if reaction else NEUTRAL_ABSENCE)
    for key in ('identity', 'personality', 'voice', 'background', 'appearance', 'routine', 'location'):
        if definition.get(key):
            lines.append(f'{key.capitalize()}: {definition[key]}')
    if definition.get('interests'):
        lines.append('Interests: ' + ', '.join(definition['interests']))
    return '\n'.join(lines)


def local_time(instant: datetime, timezone: str) -> str:
    return instant.astimezone(zone(timezone)).strftime('%A %d %B %Y, %H:%M (%Z)')


def time_text(now, user_tz, companion_tz, previous) -> str:
    lines = [f"User's local time: {local_time(now, user_tz)}.",
             f'Your local time: {local_time(now, companion_tz)}.']
    if previous:
        hours = (now - parse(previous)).total_seconds() / 3600
        if hours >= 6:
            lines.append(f'The previous message in this conversation was about {round(hours)} hours ago.')
    return '\n'.join(lines)


def memory_text(memory) -> str:
    label = 'Boundary' if memory['boundary'] else memory['layer'].replace('_', ' ').capitalize()
    timing = ''
    if memory['applies_from'] or memory['applies_until']:
        timing = f" (applies {memory['applies_from'] or '…'} to {memory['applies_until'] or '…'})"
    status = f" [{memory['plan_status']}]" if memory['plan_status'] else ''
    return f"- {label}: {memory['subject']}: {memory['value']}{status}{timing} (stated {memory['stated_at'][:10]})"


def transcript(connection, timeline_id, blocked, until_seq=None) -> list[dict]:
    rows = many(connection, "SELECT * FROM messages WHERE timeline_id=? AND active=1 AND status='complete' "
                "AND redacted_at IS NULL AND seq<=? ORDER BY seq", (timeline_id, until_seq or 2 ** 62))
    return [row for row in rows if row['id'] not in blocked]


def recall_pool(memories, older) -> tuple[list, dict]:
    chunks, owners = [], {}
    for memory in memories:
        for chunk in compile_chunks(f"memory:{memory['id']}", memory['subject'],
                                    f"{memory['subject']}: {memory['value']}", 'memory'):
            chunks.append(chunk)
            owners[chunk.id] = ('memory', memory)
    for message in older:
        for chunk in compile_chunks(f"message:{message['id']}", message['role'], message['text']):
            chunks.append(chunk)
            owners[chunk.id] = ('message', message)
    return chunks, owners


def recalled(memories, older, query) -> list[tuple[str, str]]:
    """Pinned memories first, then lexical recall over eligible memories and older turns."""
    result = [(memory['id'], memory_text(memory)) for memory in memories if memory['pinned']]
    chunks, owners = recall_pool([memory for memory in memories if not memory['pinned']], older)
    hits = hybrid_hits(chunks, [query], {'rankings': []}, RECALL_LIMIT) if query.strip() else []
    seen = set()
    for hit in hits:
        kind, owner = owners[hit.chunk.id]
        if owner['id'] in seen:
            continue
        seen.add(owner['id'])
        text = memory_text(owner) if kind == 'memory' else \
            f"- Earlier ({owner['created_at'][:10]}, {owner['role']}): {hit.chunk.text.strip()}"
        result.append((owner['id'], text))
    return result


def partition(memories) -> dict:
    groups = {'boundaries': [], 'profile': [], 'commitments': [], 'temporary': [], 'recallable': []}
    for memory in memories:
        if memory['boundary']:
            groups['boundaries'].append(memory)
        elif memory['layer'] == 'plan' and memory['plan_status'] in OPEN_PLANS:
            groups['commitments'].append(memory)
        elif memory['layer'] in {'user_fact', 'temporary'}:
            groups['profile' if memory['layer'] == 'user_fact' else 'temporary'].append(memory)
        elif memory['layer'] in RECALLED_LAYERS:
            groups['recallable'].append(memory)
    groups['profile'].sort(key=lambda memory: (not memory['pinned'], memory['subject']))
    groups['commitments'].sort(key=lambda memory: (memory['applies_from'] or '~', memory['subject']))
    return groups


def fit_conversation(packet, recent) -> list[dict]:
    """Newest turns first, so a tight budget drops the oldest turns, never the latest one."""
    kept = []
    for index in range(len(recent) - 1, -1, -1):
        cost = token_estimate(recent[index]['text'])
        if packet.used + cost > packet.budget:
            packet.omitted['conversation'] = [message['id'] for message in recent[:index + 1]]
            break
        packet.used += cost
        kept.insert(0, recent[index])
    packet.included['conversation'] = [message['id'] for message in kept]
    return kept


def build(connection, companion, now: datetime, budget: int, until_seq: int | None = None) -> dict:
    """Assemble the next reply's inputs from the active timeline's saved state.

    `until_seq` is the message being answered, so an alternative never sees the reply it replaces.
    """
    timeline_id, version = companion['active_timeline_id'], companion['version']
    groups = partition(eligible(connection, companion, timeline_id, stamp(now)))
    messages = transcript(connection, timeline_id, blocked_messages(connection, companion['id']), until_seq)
    recent, older = messages[-RECENT_MESSAGES:], messages[:-RECENT_MESSAGES]
    packet = Packet(budget)
    packet.require('character', version['id'], character_text(version))
    for memory in groups['boundaries']:
        packet.require('boundaries', memory['id'], memory_text(memory))
    previous = recent[-2]['created_at'] if len(recent) > 1 else None
    packet.require('time', 'clock', time_text(now, settings(connection)['user_timezone'], version['timezone'],
                                              previous))
    conversation = fit_conversation(packet, recent)
    for section in ('profile', 'commitments', 'temporary'):
        for memory in groups[section]:
            packet.offer(section, memory['id'], memory_text(memory))
    for event in committed(connection, timeline_id)[-RECENT_EVENTS:]:
        packet.offer('companion_life', event['id'], f"- {event['starts_at'][:16]}: {event['summary']}")
    query = next((message['text'] for message in reversed(recent) if message['role'] == 'user'), '')
    for identity, text in recalled(groups['recallable'], older, query):
        packet.offer('recalled', identity, text)
    return render(packet, conversation)


def render(packet, conversation) -> dict:
    parts = ['\n'.join(packet.sections['character'])]
    for key, heading in HEADINGS.items():
        if packet.sections.get(key):
            parts.append(f'## {heading}\n' + '\n'.join(packet.sections[key]))
    chat = [{'role': 'user' if message['role'] == 'user' else 'assistant', 'content': message['text']}
            for message in conversation]
    receipt = {'budget_tokens': packet.budget, 'estimated_tokens': packet.used,
               'included': packet.included, 'omitted': packet.omitted}
    return {'system': '\n\n'.join(parts), 'messages': chat, 'receipt': receipt}
