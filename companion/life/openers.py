"""The companion texts first (realism: real people start conversations too).

Fixed triggers decide when the companion opens a conversation, from saved state only: a plan the
user mentioned whose day has passed, news from the companion's own committed life, an event that
touches something the user told them, or, only for a character given an absence trait, a long
silence. The facts come from that state; a model only phrases the message in the character's voice,
and a trigger that needs phrasing waits when no model is connected.

It is off until the user turns it on. It never texts while the workspace is paused, during quiet
hours, while the companion is asleep, soon after the last message, more often than the daily cap,
or twice in a row without an answer. Each trigger fires once per timeline. The message is saved as
an ordinary companion message with no `reply_to`, so the next reply sees it in the transcript.
"""
from dataclasses import dataclass
from datetime import timedelta

from companion import notifications, self_facts
from companion.characters import current
from companion.clock import parse, stamp
from companion.database import decode, encode, identifier, many, one, optional, settings
from companion.errors import DomainError
from companion.life import occasions, recommendations, routine, storylines
from companion.life.mood import ABSENCE_HOURS, last_presence
from companion.memory import context
from companion.memory.records import OPEN_PLANS, eligible
from companion.memory.retrieval import terms
from companion.providers.chat import INCOMPLETE
from companion.providers.scheduling import BackgroundInterrupted, Work
from companion.text_models import CHAT, config_for, key_for
from companion.traits import NAMES, absence_traits, strongest

OPENER = Work(15, 'companion message', True)
FOLLOW_UP_WITHIN = timedelta(days=3)
FOLLOW_UP_AFTER = timedelta(hours=1)
NEWS_WITHIN = timedelta(hours=24)
SILENCE = timedelta(hours=ABSENCE_HOURS * 2)
MAX_LENGTH = 600
# Words too common to say an event "reminded" the companion of something the user said.
COMMON = {'with', 'went', 'time', 'that', 'this', 'from', 'some', 'they', 'have', 'into', 'about', 'their',
          'over', 'just', 'like', 'good', 'long', 'more', 'most', 'work', 'home', 'evening', 'morning',
          'afternoon', 'friend', 'friends', 'spent', 'took', 'through', 'usual', 'around', 'while', 'went',
          'little', 'really', 'today', 'there', 'after', 'before', 'again', 'first', 'last', 'next', 'make'}
FINISHED = {'loved it': 'Okay, I finished {title}. You were so right, I loved it.',
            'liked it': 'Finished {title}! Really liked it, thank you for that.',
            'thought it was fine': 'Finally finished {title}. It was... fine? I see why people like it.',
            'was not really into it': "So I finished {title}. Honestly? Not really my thing. Sorry!"}
VOICE = {'mild': "Hey you. It's been a little while.", 'moderate': "You've been quiet. Everything okay?",
         'strong': 'So... are you ignoring me now?'}
INSTRUCTION = (
    'The user has not written. Write one short message to them yourself, as a text that starts a new exchange '
    '(one to three sentences, no greeting formula unless it fits your voice). Why you are writing: {reason} '
    'Stay within these facts: do not add events, places or people, and never claim to know what the user did. '
    'Reply with the message text only.'
)


@dataclass(frozen=True)
class Trigger:
    key: str
    kind: str
    reason: str
    template: str | None = None
    sources: tuple = ()


def plan_follow_ups(connection, companion, now) -> list[Trigger]:
    """A plan the user mentioned whose time has passed, without a known outcome."""
    result = []
    for memory in eligible(connection, companion, companion['active_timeline_id'], stamp(now)):
        if memory['layer'] != 'plan' or memory['plan_status'] not in OPEN_PLANS:
            continue
        end = memory['applies_until'] or memory['applies_from']
        if not end or not now - FOLLOW_UP_WITHIN <= parse(end) <= now - FOLLOW_UP_AFTER:
            continue
        result.append(Trigger(
            f"plan:{memory['id']}", 'follow_up',
            f"The user told you about a plan ({memory['subject']}: {memory['value']}) and its time has passed. "
            'You do not know how it went. Ask about it warmly.',
            f"Hey! How did the {memory['subject'][0].lower() + memory['subject'][1:]} go?", (memory['id'],)))
    return result


def recent_events(connection, timeline_id, now, where) -> list[dict]:
    return many(connection, "SELECT * FROM life_events WHERE timeline_id=? AND status='committed' AND decided_at>? "
                f'AND ends_at<=? AND {where} ORDER BY decided_at DESC LIMIT 10',
                (timeline_id, stamp(now - NEWS_WITHIN), stamp(now)))


def news(connection, companion, now) -> list[Trigger]:
    """An open question in the companion's life that just settled."""
    rows = recent_events(connection, companion['active_timeline_id'], now,
                         "kind='thread' AND json_extract(details, '$.state')='settled'")
    return [Trigger(f"news:{row['id']}", 'news', f'Something in your own life just turned out: {row["summary"]} '
                    'Tell the user, the way you would text a friend.', None, (row['id'],)) for row in rows]


def words(text: str) -> set[str]:
    return {word for word in terms(text) if len(word) >= 4 and word not in COMMON}


def reminders(connection, companion, now) -> list[Trigger]:
    """Something the companion did today that touches what the user told them about themselves."""
    facts = [memory for memory in eligible(connection, companion, companion['active_timeline_id'], stamp(now))
             if memory['layer'] in {'user_fact', 'shared_experience'} and not memory['boundary']]
    result = []
    for row in recent_events(connection, companion['active_timeline_id'], now, "kind='ordinary'"):
        found = words(row['summary'])
        match = next((memory for memory in facts if found & words(f"{memory['subject']} {memory['value']}")), None)
        if match:
            result.append(Trigger(
                f"reminder:{row['id']}", 'reminder',
                f'Earlier you {row["summary"]} It reminded you of something the user told you '
                f"({match['subject']}: {match['value']}). Tell them, briefly.", None, (row['id'], match['id'])))
    return result


def silence(connection, companion, now) -> list[Trigger]:
    """Only a character with an absence trait reaches out about a long silence (C6, M4)."""
    traits = absence_traits(companion['version']['definition'])
    since = last_presence(connection, companion['active_timeline_id'])
    if not traits or since is None or now - parse(since) < SILENCE:
        return []
    intensity = NAMES[strongest(traits)]
    return [Trigger(f'silence:{since}', 'silence',
                    f'The user has not written for {round((now - parse(since)).total_seconds() / 86400)} days. Because '
                    f"of your {' and '.join(trait['name'] for trait in traits)} ({intensity}), you reach out, in "
                    'proportion and in character. You do not know why they were away and must not guess or accuse.',
                    VOICE[intensity])]


def finished(connection, companion, now) -> list[Trigger]:
    """Something the user recommended, finished in the companion's committed account."""
    rows = recommendations.finished_recently(connection, companion['active_timeline_id'], stamp(now - NEWS_WITHIN))
    result = []
    for row in rows:
        item = decode(row['details'])['recommendation']
        template = FINISHED.get(item['verdict'], FINISHED['liked it']).format(title=item['title'])
        result.append(Trigger(f"finished:{item['id']}", 'recommendation',
                              f"You just finished {item['title']}, which the user recommended to you. Your verdict: "
                              f"{item['verdict']}. Tell them, honestly and briefly. You know nothing about it beyond its "
                              'name: do not describe plot, people or details.', template, (row['id'],)))
    return result


def storyline_news(connection, companion, now) -> list[Trigger]:
    """A beat in a storyline that happened today or yesterday (companion/life/storylines.py)."""
    return [Trigger(key, 'storyline', f"Something just happened in your life: {beat['text']} Tell the user, the "
                    'way you would text a friend. Do not add what happens next.', beat['share'])
            for key, beat in storylines.fresh_beats(connection, companion, now)]


def occasion(connection, companion, now) -> list[Trigger]:
    """The user's birthday, the companion's own, or a milestone in how long they have talked: on the day."""
    return [Trigger(item['key'], 'occasion', f"{item['text'][2:]} Write to the user about it, warmly and in your own "
                    'voice.', item['template']) for item in occasions.occasions(connection, companion, now)
            if item['days'] == 0]


# In priority order; later features add their own.
FINDERS = [occasion, plan_follow_ups, finished, storyline_news, news, reminders, silence]


def candidates(connection, companion, now) -> list[Trigger]:
    timeline_id = companion['active_timeline_id']
    fired = {row['trigger_key'] for row in many(connection, 'SELECT trigger_key FROM openers WHERE timeline_id=?',
                                                 (timeline_id,))}
    return [trigger for finder in FINDERS for trigger in finder(connection, companion, now) if trigger.key not in fired]


def held(connection, companion, life, now) -> str | None:
    """Why the companion should not text right now, or None."""
    workspace, timeline_id = settings(connection), companion['active_timeline_id']
    if not life['texts_first']:
        return 'off'
    if workspace['paused_at'] is not None:
        return 'paused'
    quiet = notifications.notification_settings(connection)
    if notifications.in_quiet_hours(now.astimezone(notifications.zone(workspace['user_timezone'])),
                                    quiet['quiet_start'], quiet['quiet_end']):
        return 'quiet_hours'
    version = companion['version']
    schedule, _default = routine.blocks(version['definition'])
    slot, _next = routine.current_and_next(schedule, version['timezone'], now)
    if slot and slot.block.kind in routine.RESTING:
        return 'asleep'
    last = optional(connection, "SELECT role, created_at, id FROM messages WHERE timeline_id=? AND status='complete' "
                    'ORDER BY seq DESC LIMIT 1', (timeline_id,))
    if last and now - parse(last['created_at']) < timedelta(hours=life['texts_gap_hours']):
        return 'recent_conversation'
    if last and last['role'] == 'companion' and optional(connection, 'SELECT id FROM openers WHERE message_id=?',
                                                         (last['id'],)):
        return 'waiting_for_answer'
    sent = one(connection, 'SELECT COUNT(*) AS n FROM openers WHERE timeline_id=? AND created_at>?',
               (timeline_id, stamp(now - timedelta(days=1))))['n']
    return 'daily_cap' if sent >= life['texts_daily'] else None


class Openers:
    """Decides and writes the companion's first messages for one process."""

    def __init__(self, database, vault, provider, scheduler):
        self.database = database
        self.vault = vault
        self.provider = provider
        self.scheduler = scheduler

    async def check(self) -> dict:
        now = self.database.clock.now()
        with self.database.connect() as connection:
            companion = current(connection)
            if companion is None:
                return {'state': 'no_companion', 'message': None}
            life = one(connection, 'SELECT * FROM life_settings WHERE id=1')
            if reason := held(connection, companion, life, now):
                return {'state': reason, 'message': None}
            config = config_for(connection, CHAT)
            found = candidates(connection, companion, now)
        for trigger in found:
            if trigger.template is None and config is None:
                continue
            try:
                text, wording = await self.write(trigger, config, now)
            except BackgroundInterrupted:
                return {'state': 'interrupted', 'message': None}
            if text:
                return self.save(companion, trigger, text, wording, now)
        return {'state': 'nothing', 'message': None}

    async def write(self, trigger, config, now) -> tuple[str | None, str]:
        if config is None:
            return trigger.template, 'template'
        with self.database.connect() as connection:
            companion = current(connection)
            packet = context.build(connection, companion, now, config['context_tokens'] - config['max_output_tokens'])
        ask = '(' + INSTRUCTION.format(reason=trigger.reason) + ')'
        messages = list(packet['messages'])
        if messages and messages[-1]['role'] == 'user':
            messages[-1] = {'role': 'user', 'content': messages[-1]['content'] + '\n\n' + ask}
        else:
            messages.append({'role': 'user', 'content': ask})
        text = []
        try:
            async with self.scheduler.reserve(config, OPENER) as lease:
                async for chunk in self.provider.stream(config, key_for(self.vault, config), packet['system'],
                                                        messages):
                    if lease.stop.is_set():
                        raise BackgroundInterrupted()
                    text.append(chunk.text)
                    if chunk.finish_reason in INCOMPLETE:
                        return trigger.template, 'template'
        except BackgroundInterrupted:
            raise
        except DomainError:
            return trigger.template, 'template'
        written = ''.join(text).strip().strip('"').strip()
        if not written or len(written) > MAX_LENGTH:
            return trigger.template, 'template'
        return written, 'model'

    def save(self, companion, trigger, text, wording, now) -> dict:
        from companion.conversation import message_view, next_seq
        timestamp = stamp(now)
        with self.database.connect(write=True) as connection:
            latest = current(connection)
            timeline_id = latest['active_timeline_id']
            # The world moved on while the message was written: the user wrote, or the timeline or
            # character changed. Try again on the next check.
            if (timeline_id != companion['active_timeline_id'] or latest['active_version_id'] != companion[
                    'active_version_id'] or held(connection, latest, one(
                    connection, 'SELECT * FROM life_settings WHERE id=1'), now)
                    or optional(connection, 'SELECT id FROM openers WHERE timeline_id=? AND trigger_key=?',
                                (timeline_id, trigger.key))):
                return {'state': 'superseded', 'message': None}
            message_id = identifier()
            connection.execute(
                'INSERT INTO messages (id, timeline_id, seq, role, text, reply_to, status, active, '
                'character_version_id, memory_revision, created_at, completed_at) '
                "VALUES (?, ?, ?, 'companion', ?, NULL, 'complete', 1, ?, ?, ?, ?)",
                (message_id, timeline_id, next_seq(connection, timeline_id), text, latest['active_version_id'],
                 settings(connection)['memory_revision'], timestamp, timestamp))
            connection.execute('INSERT INTO openers (id, timeline_id, trigger_key, kind, facts, message_id, wording, '
                               'created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                               (identifier(), timeline_id, trigger.key, trigger.kind,
                                encode({'reason': trigger.reason, 'sources': list(trigger.sources)}), message_id,
                                wording, timestamp))
            notifications.enqueue_message(connection, message_id, timestamp)
            row = one(connection, 'SELECT * FROM messages WHERE id=?', (message_id,))
            self_facts.note(connection, row, timestamp)
        return {'state': 'sent', 'kind': trigger.kind, 'message': message_view(row)}


def opener_for(connection, message_id) -> dict | None:
    return optional(connection, 'SELECT kind, wording, created_at FROM openers WHERE message_id=?', (message_id,))
