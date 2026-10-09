"""Group chats: the user and several companions in one chat (docs/group-chat.md).

Each reply in a group is one ordinary model call for one companion, built from what that companion knows.
Every speaker's prompt starts with the same shared part, so the second and third speaker reuse the first
one's cached work:

1. the group rules (an editable prompt),
2. the cast: each member's name and public line, in join order,
3. the transcript as "Name: message" lines, written the same way for everyone and trimmed in chunks,

and only then the speaker's private part: their own 1:1 sections (memory/context.py, in its usual order) with
one `group` section, and the turn. Nothing personal goes above the transcript, or the prefix would differ for
every speaker.

The app decides everything here by rules: who is in a group, who sees which messages (`sees_from` and
`left_seq` on each stay), who answers and in what order. The model only writes the chosen speaker's line.

Seams the later group chat PRs build on:
- `public_line`: a member's "Others see" line in the cast block (world/perception.py).
- `group_lines`: the speaker's private group section (secrets, closeness between members, mood).
- `plan`, `weights` and `chime_in`: who answers whom (closeness between members, later ignoring someone).
- Members are person keys (`companion:<id>`), so guests from a circle or the town can join as another kind.

Groups also start conversations on their own: a member shares something from their day and the others answer
it as they answer the user (`GroupChats.first_words`; the rules are in companion/group_openers.py).
"""
import asyncio
import json
import logging
import random
import re
import time
from dataclasses import dataclass, field

from companion import away, group_openers, in_character, prompt_library, secrets, texting
from companion.characters import by_id
from companion.database import identifier, many, one, optional
from companion.errors import DomainError, require
from companion.life import reactions
from companion.memory import closeness, context, pairs
from companion.memory.budget import token_estimate
from companion.providers.chat import INCOMPLETE
from companion.providers.scheduling import CONVERSATION
from companion.text_models import CHAT, config_for, default_name, key_for
from companion.world import perception

LOG = logging.getLogger(__name__)

# A reply that names nobody may draw one more answer from a member who feels at least this close to its writer.
CHIME_IN_LEVEL, CHIME_IN_CHANCE = 4, 0.25
# Closeness between members, as the speaker's group section words it (memory/pairs.py stages).
FEELS = (
    'You have only just met {name}: friendly, a little polite, and you keep personal things to yourself.',
    'You are still getting to know {name}: friendly, but you keep it light and hold the personal things back.',
    'You are at ease with {name}: you tease a little, share everyday things and pick up where you left off.',
    'You and {name} are close: you talk openly, look out for them and take their side when it matters.',
    'You and {name} go back a long way: shorthand, in-jokes and plain honesty, even about hard things.',
)
HOW_YOU_KNOW = 'How you know {name}: {how}'
THEIR_SELF_VIEW = '{name} has let you see how they see themselves: {view}'

# Replies to each user message when nobody is named; a setting per group.
DEFAULT_CAP, MAX_CAP = 2, 3
# Oldest transcript lines drop this many at a time, so the shared prefix stays the same for many turns.
CHUNK = 20
# The share of the reply's context the shared transcript may take; the rest is the cast and the speaker's own part.
TRANSCRIPT_SHARE = 0.4
NAME_LIMIT = 60
HISTORY_LIMIT = 300

# Replies at a person's pace, with the Life setting `paced_replies` on (the default): each reply is written
# whole, then shown once the time a person would take has passed since the message before it showed, to read
# that message, think and type their own. Replies come one after another, never all at once. Off in tests
# unless a test turns it on.
PACED = True
READ_SECONDS = (1.0, 4.0)       # From 1 s, plus READ_PER_CHARACTER, up to 4 s.
READ_PER_CHARACTER = 0.02
THINK_SECONDS = (0.5, 2.5)
TYPE_CHARACTERS_PER_SECOND = (5.0, 8.0)
PACE_SECONDS = (2.5, 15.0)      # Never sooner than this after the message before, nor later.

RULES = """This is a group chat. The user and the people listed below write to each other in one shared \
conversation, the way friends do in a group text.

How the chat works:
- The chat so far is written as "Name: message" lines. "User" is the user. Lines in [square brackets] are notes \
from the app about who joined or left, not messages.
- Everyone in the group reads every message sent while they are in it. Nobody knows what was said in private \
chats they were not part of, or in the group before they could see it.
- You are told below which one of these people you are, with what only that person knows. Write only that \
person's next message: one message, in their own voice, with no name in front of it. Never write lines for \
anyone else.
- Talk to the whole group or to one person in it, and keep it as short as a real group text unless the moment \
needs more."""

TURN = 'Write {name}\'s next message in the group chat "{group}": only what {name} says, with no name in front.'

USER = 'User'
APP = 'app'


def member_key(companion_id: str) -> str:
    return f'companion:{companion_id}'


def companion_of(key: str) -> str | None:
    return key.split(':', 1)[1] if key.startswith('companion:') else None


# Groups and members ---------------------------------------------------------------------------------

def require_group(connection, group_id: str) -> dict:
    group = optional(connection, 'SELECT * FROM group_chats WHERE id=?', (group_id,))
    if group is None:
        raise DomainError('That group chat is gone.', 404, 'no_group')
    return group


def stays(connection, group_id: str) -> list[dict]:
    """Every stay of every member, in join order."""
    return many(connection, 'SELECT * FROM group_members WHERE group_id=? ORDER BY joined_at, rowid', (group_id,))


def current_members(connection, group_id: str) -> list[dict]:
    """Who is in the group now, in join order."""
    return [stay for stay in stays(connection, group_id) if stay['left_at'] is None]


def companion_name(connection, companion_id: str) -> str:
    found = by_id(connection, companion_id)
    require(found is not None, 'That companion is no longer in this workspace.', 404)
    return found['version']['name']


def label_for(name: str, taken: set[str]) -> str:
    """How they are named in the chat: their first name, or their full name when someone in it shares it."""
    first = name.split()[0] if name.split() else name
    return name if first.casefold() in {label.casefold() for label in taken} else first


def next_seq(connection, group_id: str) -> int:
    return one(connection, 'SELECT COALESCE(MAX(seq), 0) + 1 AS seq FROM group_messages WHERE group_id=?',
               (group_id,))['seq']


def add_line(connection, group_id: str, timestamp: str, author: str, name: str, text: str, *, status='complete',
             reply_to=None, client_id=None) -> dict:
    """One message, with who was present when it was written (the witness rule needs no replay of joins)."""
    message_id, seq = identifier(), next_seq(connection, group_id)
    present = [stay['member'] for stay in current_members(connection, group_id)]
    connection.execute(
        'INSERT INTO group_messages (id, group_id, seq, author, name, text, status, present, reply_to, client_id, '
        'created_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (message_id, group_id, seq, author, name, text, status, json.dumps(present), reply_to, client_id, timestamp,
         None if status == 'streaming' else timestamp))
    connection.execute('UPDATE group_chats SET updated_at=? WHERE id=?', (timestamp, group_id))
    return one(connection, 'SELECT * FROM group_messages WHERE id=?', (message_id,))


def note(connection, group_id: str, timestamp: str, text: str) -> dict:
    return add_line(connection, group_id, timestamp, APP, '', text)


def join(connection, group_id: str, companion_id: str, timestamp: str, sees_from: int | None = None) -> dict:
    """A new stay; `sees_from` None means from their join on."""
    name = companion_name(connection, companion_id)
    taken = {stay['name'] for stay in current_members(connection, group_id)}
    stay_id = identifier()
    connection.execute('INSERT INTO group_members (id, group_id, member, name, joined_at, sees_from) '
                       'VALUES (?, ?, ?, ?, ?, ?)',
                       (stay_id, group_id, member_key(companion_id), label_for(name, taken), timestamp,
                        sees_from or next_seq(connection, group_id)))
    return one(connection, 'SELECT * FROM group_members WHERE id=?', (stay_id,))


def names_text(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ', '.join(names[:-1]) + f' and {names[-1]}'


def clean_name(name: str | None) -> str:
    return ' '.join((name or '').split())[:NAME_LIMIT]


def create(database, companion_ids: list[str], name: str | None = None, ties=None) -> dict:
    """A new group of two or more companions, any of them; it never changes who the main character is. `ties`
    are the backstories the user wrote for pairs meeting in a group for the first time; any other such pair gets
    the one the app works out (memory/pairs.py)."""
    chosen = list(dict.fromkeys(companion_ids))
    require(len(chosen) >= 2, 'Pick at least two companions for a group.', 422)
    timestamp = database.now()
    with database.connect(write=True) as connection:
        pairs.tell_all(connection, ties, timestamp)
        pairs.tell_rest(connection, chosen, database.clock.now(), timestamp)
        group_id = identifier()
        connection.execute('INSERT INTO group_chats (id, name, reply_cap, created_at, updated_at) '
                           'VALUES (?, ?, ?, ?, ?)', (group_id, clean_name(name), DEFAULT_CAP, timestamp, timestamp))
        for companion_id in chosen:
            join(connection, group_id, companion_id, timestamp, sees_from=1)
        names = [stay['name'] for stay in current_members(connection, group_id)]
        note(connection, group_id, timestamp, f'You started a group with {names_text(names)}.')
        return group_view(connection, group_id)


def update(database, group_id: str, name: str | None = None, reply_cap: int | None = None) -> dict:
    timestamp = database.now()
    with database.connect(write=True) as connection:
        group = require_group(connection, group_id)
        if name is not None and clean_name(name) != group['name']:
            connection.execute('UPDATE group_chats SET name=? WHERE id=?', (clean_name(name), group_id))
            note(connection, group_id, timestamp,
                 f'You named the group "{clean_name(name)}".' if clean_name(name) else "You removed the group's name.")
        if reply_cap is not None:
            require(1 <= reply_cap <= MAX_CAP, f'Replies per message is 1 to {MAX_CAP}.', 422)
            connection.execute('UPDATE group_chats SET reply_cap=? WHERE id=?', (reply_cap, group_id))
        return group_view(connection, group_id)


def add(database, group_id: str, companion_id: str, everything: bool = False, ties=None) -> dict:
    """Add someone later. By default they see the chat from now on; `everything` shows them all of it. `ties` as
    for create."""
    timestamp = database.now()
    with database.connect(write=True) as connection:
        group = require_group(connection, group_id)
        key = member_key(companion_id)
        require(all(stay['member'] != key for stay in current_members(connection, group_id)),
                'They are already in this group.', 409)
        pairs.tell_all(connection, ties, timestamp)
        pairs.tell_rest(connection, [companion_id, *(companion_of(stay['member']) for stay in current_members(
            connection, group_id) if companion_of(stay['member']))], database.clock.now(), timestamp)
        stay = join(connection, group_id, companion_id, timestamp, sees_from=1 if everything else None)
        if everything:
            secrets.history(connection, group_id, key, timestamp)
            reactions.showed_everything(connection, group, key, database.clock.now())
        note(connection, group_id, timestamp, f"You added {stay['name']}.")
        return group_view(connection, group_id)


def leave(connection, group_id: str, stay: dict, timestamp: str, text: str):
    """The stay ends before this line: nothing from here on reaches them. What they saw stays known."""
    line = add_line(connection, group_id, timestamp, APP, '', text)
    connection.execute('UPDATE group_members SET left_at=?, left_seq=? WHERE id=?', (timestamp, line['seq'], stay['id']))
    connection.execute("UPDATE group_messages SET present=? WHERE id=?",
                       (json.dumps([item for item in json.loads(line['present']) if item != stay['member']]),
                        line['id']))


def remove(database, group_id: str, companion_id: str) -> dict:
    timestamp = database.now()
    with database.connect(write=True) as connection:
        require_group(connection, group_id)
        stay = next((item for item in current_members(connection, group_id)
                     if item['member'] == member_key(companion_id)), None)
        require(stay is not None, "They aren't in this group.", 404)
        leave(connection, group_id, stay, timestamp, f"You removed {stay['name']}.")
        return group_view(connection, group_id)


def leave_everywhere(connection, companion_id: str, timestamp: str):
    """Start over or Delete: the companion leaves every group. Their old lines stay, under their name."""
    rows = many(connection, 'SELECT * FROM group_members WHERE member=? AND left_at IS NULL',
                (member_key(companion_id),))
    for stay in rows:
        leave(connection, stay['group_id'], stay, timestamp, f"{stay['name']} is no longer in the group.")
    pairs.forget(connection, companion_id)


def copy(database, group_id: str) -> dict:
    """New group with these people: the same members, a fresh history."""
    with database.connect() as connection:
        members = [companion_of(stay['member']) for stay in current_members(connection, group_id)]
    return create(database, [member for member in members if member])


def delete(database, group_id: str) -> dict:
    with database.connect(write=True) as connection:
        require_group(connection, group_id)
        connection.execute('DELETE FROM group_moments WHERE message_id IN (SELECT id FROM group_messages '
                           'WHERE group_id=?)', (group_id,))
        connection.execute('DELETE FROM group_messages WHERE group_id=?', (group_id,))
        connection.execute('DELETE FROM group_members WHERE group_id=?', (group_id,))
        connection.execute('DELETE FROM group_chats WHERE id=?', (group_id,))
    return {'groups': listing(database)}


# Views ------------------------------------------------------------------------------------------------

def message_view(row: dict, kept: frozenset = frozenset()) -> dict:
    kind = 'user' if row['author'] == 'user' else APP if row['author'] == APP else 'companion'
    return {'id': row['id'], 'seq': row['seq'], 'kind': kind, 'companion_id': companion_of(row['author']),
            'name': row['name'], 'text': row['text'], 'status': row['status'], 'error': row['error'],
            'reply_to': row['reply_to'], 'guard': row['guard'], 'created_at': row['created_at'],
            'kept': row['id'] in kept}


def member_view(connection, stay: dict) -> dict:
    companion_id = companion_of(stay['member'])
    found = by_id(connection, companion_id) if companion_id else None
    return {'companion_id': companion_id, 'name': found['version']['name'] if found else stay['name'],
            'label': stay['name'], 'main': bool(found and found['slot'] == 1), 'joined_at': stay['joined_at'],
            'sees_from': stay['sees_from']}


def title(connection, group: dict) -> str:
    return group['name'] or names_text([stay['name'] for stay in current_members(connection, group['id'])] or ['Nobody'])


def group_view(connection, group_id: str) -> dict:
    group = require_group(connection, group_id)
    return {'id': group['id'], 'name': group['name'], 'title': title(connection, group),
            'reply_cap': group['reply_cap'], 'created_at': group['created_at'], 'updated_at': group['updated_at'],
            'members': [member_view(connection, stay) for stay in current_members(connection, group_id)]}


def listing(database) -> list[dict]:
    """Every group, most recently active first, with its latest message."""
    with database.connect() as connection:
        result = []
        for group in many(connection, 'SELECT * FROM group_chats ORDER BY updated_at DESC, rowid DESC'):
            latest = optional(connection, "SELECT * FROM group_messages WHERE group_id=? AND status='complete' "
                              'ORDER BY seq DESC LIMIT 1', (group['id'],))
            result.append({**group_view(connection, group['id']), 'latest': latest and message_view(latest)})
        return result


def history(connection, group_id: str, after_seq: int = 0) -> list[dict]:
    rows = many(connection, 'SELECT * FROM group_messages WHERE group_id=? AND seq>? ORDER BY seq DESC LIMIT ?',
                (group_id, after_seq, HISTORY_LIMIT))
    kept = frozenset(row['message_id'] for row in many(
        connection, 'SELECT message_id FROM group_moments WHERE message_id IN (SELECT id FROM group_messages '
        'WHERE group_id=?)', (group_id,)))
    return [message_view(row, kept) for row in reversed(rows)]


def keep_moment(database, group_id: str, message_id: str, kept: bool = True) -> dict:
    """Keep a member's message as a shared moment (or let it go): it brings everyone who was in the group when it
    was written a little closer to each other (memory/pairs.py), the way a kept moment does in a 1:1 chat."""
    with database.connect(write=True) as connection:
        require_group(connection, group_id)
        row = optional(connection, "SELECT * FROM group_messages WHERE id=? AND group_id=? AND status='complete'",
                       (message_id, group_id))
        require(row is not None and companion_of(row['author']) is not None,
                'Only a finished message from someone in the group can be kept as a shared moment.', 422)
        if kept:
            connection.execute('INSERT OR IGNORE INTO group_moments (message_id, created_at) VALUES (?, ?)',
                               (message_id, database.now()))
        else:
            connection.execute('DELETE FROM group_moments WHERE message_id=?', (message_id,))
        return {'messages': history(connection, group_id)}


def untold(database, companion_ids: list[str]) -> list[dict]:
    """Pairs among these companions meeting in a group for the first time, whose backstory can still be written."""
    with database.connect() as connection:
        return pairs.untold(connection, companion_ids, database.clock.now())


# What a speaker sees ---------------------------------------------------------------------------------

def visible(connection, group_id: str, member: str, until_seq: int | None = None) -> list[dict]:
    """The finished messages this member could see: from each stay's `sees_from` until it ended."""
    windows = [(stay['sees_from'], stay['left_seq'] or 2 ** 62)
               for stay in stays(connection, group_id) if stay['member'] == member]
    rows = many(connection, "SELECT * FROM group_messages WHERE group_id=? AND status='complete' AND seq<=? "
                'ORDER BY seq', (group_id, until_seq or 2 ** 62))
    return [row for row in rows if any(start <= row['seq'] < end for start, end in windows)]


def line(row: dict) -> str:
    """A transcript line, the same bytes for every speaker, their own lines included."""
    if row['author'] == APP:
        text = re.sub(r'^You\b', 'The user', row['text'])
        return f'[{text}]'
    return f"{USER if row['author'] == 'user' else row['name']}: {row['text']}"


def window(rows: list[dict], budget: int) -> int:
    """Where the transcript starts: the oldest lines drop CHUNK at a time until the rest fits, always keeping
    the newest line. Speakers who see the same messages get the same start."""
    costs = [token_estimate(line(row)) + 1 for row in rows]
    start = 0
    while start + CHUNK < len(rows) and sum(costs[start:]) > budget:
        start += CHUNK
    while start < len(rows) - 1 and sum(costs[start:]) > budget:
        start += 1  # A single huge line: only then does trimming go line by line.
    return start


def public_line(connection, member: str) -> str:
    """How others see this member ("Others see", world/perception.py), for the cast block. Only the public line:
    their private "I see myself" lines ride in their own character section. Must not depend on who is speaking,
    or the shared prefix would differ."""
    companion_id = companion_of(member)
    return perception.companion_lines(connection, companion_id)['public'] if companion_id else ''


def cast_text(connection, group_id: str) -> str:
    lines = []
    for stay in current_members(connection, group_id):
        public = public_line(connection, stay['member'])
        lines.append(f"- {stay['name']}" + (f': {public}' if public else ''))
    return '## Who is in this group (besides the user)\n' + '\n'.join(lines)


def shared_part(connection, group: dict, member: str, budget: int, until_seq: int | None) -> tuple[str, list[dict]]:
    """The group rules, the cast and the transcript; returns the text and the messages trimmed from it."""
    rows = visible(connection, group['id'], member, until_seq)
    start = window(rows, int(budget * TRANSCRIPT_SHARE))
    kept = rows[start:]
    transcript = '## The group chat so far\n' + ('\n'.join(line(row) for row in kept) or '(No messages yet.)')
    rules = prompt_library.text(connection, 'group-rules')
    return '\n\n'.join((rules, cast_text(connection, group['id']), transcript)), rows[:start]


def group_lines(connection, group: dict, stay: dict, now) -> list[tuple[str, str]]:
    """The speaker's own view of the group, private to them: how close they feel to each member, and the secrets
    they know with who here must not find out (companion/secrets.py). Later: who they're not speaking to."""
    members = [item for item in current_members(connection, group['id']) if item['member'] != stay['member']]
    lines = [(f"group:{group['id']}",
              f"You are {stay['name']} in the group chat \"{title(connection, group)}\" with "
              f"{names_text(['the user', *(item['name'] for item in members)])}.")]
    if stay['sees_from'] > 1:
        lines.append((f"group:{group['id']}:joined", 'You were added to this group later and have seen only what '
                      'was said since you joined; never claim to know what was said before.'))
    for item in members:
        lines += member_lines(connection, stay['member'], item, now)
    lines += secrets.group_lines(connection, stay['member'], [item['member'] for item in members],
                                 {item['member']: item['name'] for item in members}, now)
    return lines


def member_lines(connection, speaker: str, item: dict, now) -> list[tuple[str, str]]:
    """How close the speaker feels to one member, how they know each other, and (once close) how that member
    sees themselves. The stage key changes only when the stage does, so the section stays cacheable."""
    found = pairs.between(connection, speaker, item['member'], now)
    if found is None:
        return []
    level, name = found['ab']['level'], item['name']
    result = [(f"pair:{item['member']}:{level}", FEELS[level - 1].format(name=name))]
    if found['how']:
        result.append((f"pair:{item['member']}:how", HOW_YOU_KNOW.format(name=name, how=found['how'])))
    if level >= pairs.SELF_VIEW_LEVEL and (view := pairs.self_view(connection, item['member'])):
        result.append((f"pair:{item['member']}:self", THEIR_SELF_VIEW.format(name=name, view=view)))
    return result


def recall_rows(rows: list[dict], group: dict, title_text: str) -> list[dict]:
    """Messages trimmed from the transcript, as recall items in the speaker's private part."""
    return [{'id': row['id'], 'role': f"in the group chat {title_text}, {line(row).split(':', 1)[0]}",
             'text': row['text'], 'created_at': row['created_at']} for row in rows if row['author'] != APP]


def prompt(connection, group: dict, companion: dict, stay: dict, now, config: dict, until_seq: int,
           query: str, turn: str | None = None) -> dict:
    """One speaker's request: the shared part, then their private sections, then the turn (by default, their
    next message; a group starting a conversation passes its own)."""
    budget = config['context_tokens'] - config['max_output_tokens']
    shared, trimmed = shared_part(connection, group, stay['member'], budget, until_seq)
    earlier = visible(connection, group['id'], stay['member'], until_seq)
    private = context.build(connection, companion, now, max(budget - token_estimate(shared), 1000), group={
        'older': recall_rows(trimmed, group, title(connection, group)), 'query': query,
        'lines': group_lines(connection, group, stay, now),
        'previous': earlier[-2]['created_at'] if len(earlier) > 1 else None})
    turn = turn or TURN.format(name=stay['name'], group=title(connection, group))
    # What changes with every message goes with the turn, so the system prompt stays cacheable.
    return {'system': f"{shared}\n\n{private['system']}", 'shared': shared, 'note': private['note'], 'turn': turn,
            'messages': [{'role': 'user', 'content': f"{context.NOTE_OPEN}\n{private['note']}\n\n{turn}"}],
            'receipt': private['receipt']}


def add_note(packet: dict, text: str) -> dict:
    """An instruction for this reply only, added to the notes just before the turn."""
    notes = packet['messages'][-1]['content'].removesuffix(packet['turn'])
    return {**packet, 'messages': [{'role': 'user', 'content': f"{notes}{text}\n\n{packet['turn']}"}]}


# Who answers ----------------------------------------------------------------------------------------

def mentioned(text: str, members: list[dict]) -> list[str]:
    """Members named in a message, in the order they come up ("Sally, what do you think?")."""
    found = []
    for stay in members:
        words = {stay['name'], stay['name'].split()[0]}
        hits = [match.start() for word in words if word
                for match in re.finditer(rf'(?<!\w){re.escape(word)}(?!\w)', text, re.IGNORECASE)]
        if hits:
            found.append((min(hits), stay['member']))
    return [member for _at, member in sorted(found)]


def weights(connection, group_id: str, members: list[dict], now) -> dict[str, float]:
    """Whoever hasn't spoken lately is likelier to answer; closeness with the user tips it a little."""
    rows = many(connection, "SELECT author FROM group_messages WHERE group_id=? AND status='complete' "
                'ORDER BY seq DESC LIMIT 40', (group_id,))
    result = {}
    for stay in members:
        since = next((index for index, row in enumerate(rows) if row['author'] == stay['member']), len(rows))
        companion = by_id(connection, companion_of(stay['member']) or '')
        level = closeness.state(connection, companion, now)['level'] if companion else 1
        result[stay['member']] = 1 + min(since, 10) / 2 + level / 4
    return result


def plan(members: list[dict], text: str, seed: str, cap: int, weight: dict[str, float],
         done: frozenset = frozenset()) -> list[str]:
    """Who answers a user message, in order: anyone named first, then up to `cap` in all, drawn by weight.
    Seeded by the message, so a retry picks the same people."""
    candidates = [stay for stay in members if stay['member'] not in done]
    named = [member for member in mentioned(text, members) if member not in done]
    order = list(named)
    pool = [stay['member'] for stay in candidates if stay['member'] not in named]
    rng = random.Random(seed)
    wanted = max(min(cap, len(members)) - len(done), len(named))
    while pool and len(order) < wanted:
        pick = rng.choices(pool, [weight.get(member, 1) for member in pool])[0]
        order.append(pick)
        pool.remove(pick)
    return order


def chime_in(connection, queue: list[str], spoken: set[str], speaker: str, members: list[dict], seed: str,
             now) -> bool:
    """After a reply that named nobody, a member who feels close to its writer and hasn't spoken this round may
    answer it too, a little more often the closer they are. Uses the round's one extra answer."""
    rng = random.Random(f'group-chime:{seed}')
    for stay in members:
        if stay['member'] in spoken or stay['member'] in queue:
            continue
        level = pairs.closeness(connection, stay['member'], speaker, now) or 1
        if level >= CHIME_IN_LEVEL and rng.random() < CHIME_IN_CHANCE * (level - CHIME_IN_LEVEL + 1):
            queue.insert(0, stay['member'])
            return True
    return False


def banter(queue: list[str], spoken: set[str], reply: str, members: list[dict], allowed: bool) -> bool:
    """A reply that names another member who hasn't spoken this round has them answer next. Beyond the plan,
    that happens once per round, so two companions never loop. Returns whether that extra answer was used."""
    for member in mentioned(reply, [stay for stay in members if stay['member'] not in spoken]):
        if member in queue:
            queue.remove(member)
            queue.insert(0, member)
            return False
        if allowed:
            queue.insert(0, member)
            return True
    return False


# Cleaning a reply ----------------------------------------------------------------------------------

def tidy(text: str, speaker: str, members: list[dict]) -> str:
    """The speaker's own words only: a leading "Name:" goes, and the reply stops where it starts writing
    someone else's line."""
    names = {stay['name'] for stay in members} | {USER, 'You'}
    label = r'\**\s*:\s*\**\s*'  # "Name:", "**Name:**" or "**Name**:"
    text = re.sub(rf'^\s*\**{re.escape(speaker)}{label}', '', text.strip(), flags=re.IGNORECASE)
    others = '|'.join(re.escape(name) for name in sorted(names - {speaker}, key=len, reverse=True))
    cut = re.search(rf'(?m)^\s*\**(?:{others}){label}', text) if others else None
    return (text[:cut.start()] if cut else text).strip()


def pace_seconds(before: str, reply: str, seed: str) -> float:
    """How long after `before` showed a person would send `reply`: read, think, type. Seeded per reply."""
    rng = random.Random(f'group-pace:{seed}')
    low, high = READ_SECONDS
    reading = min(high, low + READ_PER_CHARACTER * len(before))
    typing = len(reply) / rng.uniform(*TYPE_CHARACTERS_PER_SECOND)
    return min(PACE_SECONDS[1], max(PACE_SECONDS[0], reading + rng.uniform(*THINK_SECONDS) + typing))


def paced(connection) -> bool:
    life = optional(connection, 'SELECT paced_replies FROM life_settings WHERE id=1')
    return PACED and bool(life is None or life['paced_replies'])


# Running replies ------------------------------------------------------------------------------------

@dataclass
class Round:
    """The replies being written for one user message."""
    user_id: str
    task: asyncio.Task | None = None
    phase: str = 'preparing'
    live: dict = field(default_factory=dict)
    # When the latest message in the round showed (time.monotonic) and its text, for the pace.
    shown_at: float = field(default_factory=time.monotonic)
    before: str = ''


def record(database, group_id: str, text: str, client_id: str) -> dict:
    """The user's message, saved once whatever retries come."""
    with database.connect(write=True) as connection:
        existing = optional(connection, 'SELECT * FROM group_messages WHERE client_id=?', (client_id,))
        if existing:
            return existing
        require_group(connection, group_id)
        require(current_members(connection, group_id), 'Add someone to this group to keep talking.', 409)
        row = add_line(connection, group_id, database.now(), 'user', USER, text, client_id=client_id)
        secrets.witness(connection, row)  # The user can tell them; then they know.
        return row


def recover(database):
    """A reply cut off by the app closing stays visibly failed."""
    with database.connect(write=True) as connection:
        connection.execute("UPDATE group_messages SET status='failed', error=?, completed_at=COALESCE(completed_at, ?) "
                           "WHERE status='streaming'", ('The app closed before this reply finished.', database.now()))


class GroupChats:
    """Writes the replies in each group, one speaker at a time, with the conversation's model and scheduler."""

    def __init__(self, state):
        self.state = state
        self.rounds: dict[str, Round] = {}
        self.locks: dict[str, asyncio.Lock] = {}
        self.tried: set[str] = set()

    @property
    def database(self):
        return self.state.database

    def view(self, group_id: str, after_seq: int = 0) -> dict:
        with self.database.connect() as connection:
            group = group_view(connection, group_id)
            messages = history(connection, group_id, after_seq)
            ready = config_for(connection, CHAT) is not None
        running = self.rounds.get(group_id)
        return {'group': group, 'messages': messages, 'ready': ready, 'busy': running is not None,
                'phase': running.phase if running else None,
                'live': {key: ''.join(value) for key, value in running.live.items()} if running else {}}

    async def send(self, group_id: str, text: str, client_id: str, wait: bool = True) -> dict:
        user = record(self.database, group_id, text, client_id)
        with self.database.connect() as connection:
            if config_for(connection, CHAT) is None:
                return {'message': message_view(user), 'connection': 'not_configured'}
            answered = optional(connection, 'SELECT id FROM group_messages WHERE reply_to=?', (user['id'],))
        running = self.rounds.get(group_id)
        if not answered and not (running and running.user_id == user['id']):
            await self.start(group_id, user, wait)
        return {'message': message_view(user), 'connection': 'ready'}

    async def retry(self, group_id: str, wait: bool = True) -> dict:
        """Write again the replies to the latest user message that failed or were stopped."""
        with self.database.connect(write=True) as connection:
            require_group(connection, group_id)
            user = optional(connection, "SELECT * FROM group_messages WHERE group_id=? AND author='user' "
                            'ORDER BY seq DESC LIMIT 1', (group_id,))
            require(user is not None, 'There is nothing to answer yet.', 409)
            require(group_id not in self.rounds, 'Replies are still being written.', 409)
            connection.execute("DELETE FROM group_messages WHERE reply_to=? AND status IN ('failed', 'cancelled')",
                               (user['id'],))
            if config_for(connection, CHAT) is None:
                raise DomainError('Add a text model in Settings > Models so they can reply.', 409, 'not_configured')
        await self.start(group_id, user, wait)
        return self.view(group_id)

    def stop(self, group_id: str) -> bool:
        running = self.rounds.get(group_id)
        if running is None or running.task is None:
            return False
        running.task.cancel()
        return True

    async def start(self, group_id: str, user: dict, wait: bool):
        running = Round(user['id'], before=user['text'])
        lock = self.locks.setdefault(group_id, asyncio.Lock())

        async def go():
            async with lock:
                self.rounds[group_id] = running
                try:
                    await self.round(group_id, user, running)
                finally:
                    if self.rounds.get(group_id) is running:
                        del self.rounds[group_id]
                    self.state.conversation.after_turn()

        running.task = asyncio.create_task(go())
        if wait:
            try:
                await asyncio.shield(running.task)
            except asyncio.CancelledError:
                if not running.task.done():
                    raise

    async def first_words(self, wait: bool = True) -> dict | None:
        """Let one group whose turn it is start a conversation (companion/group_openers.py). Returns what was
        chosen, or None."""
        with self.database.connect() as connection:
            found = group_openers.due(connection, self.database.clock.now(), frozenset(self.tried))
        if not found:
            return None
        group_id, chosen = found[0]
        # Tried once per run of the app: a model that keeps failing must not be asked again every minute.
        self.tried.add(group_openers.news_key(group_id, chosen['event']['id']))
        running = Round('', before='')
        running.task = asyncio.create_task(self.open_up(group_id, chosen, running))
        if wait:
            await asyncio.shield(running.task)
        return {'group_id': group_id, 'member': chosen['stay']['member'], 'event_id': chosen['event']['id']}

    async def open_up(self, group_id: str, chosen: dict, running: Round):
        """The chosen member's opening line, then the others answering it. Nothing is written if the group
        stopped being free while it waited its turn (the user wrote, or replies were running)."""
        stay, event = chosen['stay'], chosen['event']
        async with self.locks.setdefault(group_id, asyncio.Lock()):
            with self.database.connect() as connection:
                life = one(connection, 'SELECT * FROM life_settings WHERE id=1')
                if group_openers.group_held(connection, group_id, life, self.database.clock.now()):
                    return
                turn = prompt_library.text(connection, 'group-first-texts', name=stay['name'], news=event['summary'])
            self.rounds[group_id] = running
            try:
                line_row = await self.speak(group_id, {'id': None, 'text': '', 'turn': turn}, stay, running)
                if line_row and self.opened(line_row, group_id, event):
                    await self.round(group_id, line_row, running, frozenset({stay['member']}))
            finally:
                if self.rounds.get(group_id) is running:
                    del self.rounds[group_id]
                self.state.conversation.after_turn()

    def opened(self, row: dict, group_id: str, event: dict) -> bool:
        """Keep a finished opening line, marked with the news it shared and drawn from the away allowance;
        one that failed or was held back goes, as if never started."""
        with self.database.connect(write=True) as connection:
            if row['status'] != 'complete':
                connection.execute('DELETE FROM group_messages WHERE id=?', (row['id'],))
                return False
            connection.execute('UPDATE group_messages SET client_id=? WHERE id=?',
                               (group_openers.news_key(group_id, event['id']), row['id']))
            away.record(connection, 'group', group_id, row['id'], row['completed_at'] or self.database.now())
        return True

    def newer(self, connection, group_id: str, user: dict) -> bool:
        return optional(connection, "SELECT id FROM group_messages WHERE group_id=? AND author='user' AND seq>?",
                        (group_id, user['seq'])) is not None

    async def round(self, group_id: str, user: dict, running: Round, opener: frozenset = frozenset()):
        """Speakers in turn, each seeing the replies before theirs; it ends early if the user writes again.
        `user` may be a member's opening line instead, with its writer in `opener`."""
        with self.database.connect(write=True) as connection:
            secrets.sync(connection, self.database.clock.now())
        with self.database.connect() as connection:
            group = require_group(connection, group_id)
            members = current_members(connection, group_id)
            done = opener | frozenset(row['author'] for row in many(
                connection, "SELECT author FROM group_messages WHERE reply_to=? AND status='complete'", (user['id'],)))
            queue = plan(members, user['text'], user['id'], group['reply_cap'],
                         weights(connection, group_id, members, self.database.clock.now()), done)
        spoken, extra = set(done), True
        while queue:
            member = queue.pop(0)
            with self.database.connect() as connection:
                if self.newer(connection, group_id, user):
                    return
                members = current_members(connection, group_id)
            stay = next((item for item in members if item['member'] == member), None)
            if stay is None:
                continue  # Removed while the round ran.
            spoken.add(member)
            reply = await self.speak(group_id, user, stay, running)
            if not reply or reply['status'] != 'complete':
                continue
            if banter(queue, spoken, reply['text'], members, extra):
                extra = False
            elif extra and not mentioned(reply['text'], members):
                with self.database.connect() as connection:
                    if chime_in(connection, queue, spoken, member, members, reply['id'], self.database.clock.now()):
                        extra = False

    async def speak(self, group_id: str, user: dict, stay: dict, running: Round) -> dict | None:
        database = self.database
        with database.connect(write=True) as connection:
            config = config_for(connection, CHAT)
            if config is None:
                return None
            row = add_line(connection, group_id, database.now(), stay['member'], stay['name'], '', status='streaming',
                           reply_to=user['id'])
            hold = paced(connection)
            # Secrets this speaker knows that someone here must not find out: the reply is checked before it shows.
            watch = secrets.watched(connection, stay['member'], json.loads(row['present']))
        # A paced or checked reply is written out of sight and shows whole when it is sent, like a text.
        text, status, error, guard = [], 'complete', None, None
        running.phase = 'preparing'
        if not hold and not watch:
            running.live[row['id']] = text
        companion = None
        try:
            with database.connect() as connection:
                group = require_group(connection, group_id)
                companion = by_id(connection, companion_of(stay['member']) or '')
                require(companion is not None, 'That companion is no longer in this workspace.', 404)
                packet = await asyncio.to_thread(self.packet, group, companion, stay, config, row['seq'], user)
            active = in_character.applies(user['text'], companion['version']['definition'])
            status, error = await self.write(config, packet, text, running, active)
            if watch and status == 'complete':
                status, error, guard = await self.check(config, packet, text, running, active, stay, watch, row)
            if hold and status == 'complete':
                await self.pace(running, ''.join(text), row['id'])
        except asyncio.CancelledError:
            self.finish(row, ''.join(text), 'cancelled', 'Stopped.', companion, stay, running, guard)
            raise
        except DomainError as failure:
            status, error = 'failed', failure.message
        except Exception as failure:  # noqa: BLE001 - a failure must still leave a visible state.
            LOG.exception('A group reply failed unexpectedly.')
            status, error = 'failed', f"Couldn't finish the reply: {failure}"
        return self.finish(row, ''.join(text), status, error, companion, stay, running, guard)

    async def check(self, config, packet, text: list, running: Round, active: bool, stay: dict, watch: list[dict],
                    row: dict) -> tuple[str, str | None, str | None]:
        """A knower's reply with someone here who must not find out: a draft that gives a secret away is written
        once more with a private reminder. If that still gives it away, it stays as a slip only at the soap opera
        drama setting; otherwise the reply is held back. Returns the status, error and what the check did."""
        present = json.loads(row['present'])
        with self.database.connect() as connection:
            members = current_members(connection, row['group_id'])
            labels = {item['member']: item['name'] for item in members}

            def slipped() -> list[dict]:
                draft = tidy(''.join(text), stay['name'], members)
                return [secret for secret in watch if secrets.hits(secret, draft, stay['member'])]

            given = slipped()
            if not given:
                return 'complete', None, None
            reminder = secrets.reminder(given, stay['name'], present, connection, labels)
            allowed = secrets.slips_allowed(connection)
        text.clear()
        status, error = await self.write(config, add_note(packet, reminder), text, running, active)
        if status != 'complete' or not slipped():
            return status, error, 'redrafted'
        if allowed:
            return 'complete', None, 'revealed'
        text.clear()
        return 'cancelled', f"{stay['name']} nearly let a secret slip, so this reply wasn't sent.", 'held'

    async def pace(self, running: Round, reply: str, seed: str):
        """Wait out what is left of the time a person would take; writing it already used some of that time."""
        left = running.shown_at + pace_seconds(running.before, reply, seed) - time.monotonic()
        if left > 0:
            await asyncio.sleep(left)

    def packet(self, group, companion, stay, config, until_seq, user) -> dict:
        with self.database.connect() as connection:
            packet = prompt(connection, group, companion, stay, self.database.clock.now(), config, until_seq,
                            user['text'], user.get('turn'))
        if in_character.out_of_character(user['text']):
            reminder = in_character.OUT_OF_CHARACTER_NOTE.format(name=stay['name'], model=default_name(config))
            packet = add_note(packet, reminder)
        return packet

    async def write(self, config, packet, text: list, running: Round, active: bool) -> tuple[str, str | None]:
        guard, status, error = in_character.Guard(active), 'complete', None
        provider, scheduler = self.state.conversation.provider, self.state.conversation.scheduler
        running.phase = 'waiting'
        try:
            async with scheduler.reserve(config, CONVERSATION, config['timeout_seconds']):
                running.phase = 'writing'
                async for chunk in provider.stream(config, key_for(self.state.vault, config), packet['system'],
                                                   packet['messages']):
                    if piece := guard.feed(chunk.text):
                        text.append(piece)
                    if chunk.finish_reason in INCOMPLETE:
                        status, error = 'failed', INCOMPLETE[chunk.finish_reason]
        finally:
            if piece := guard.flush():
                text.append(piece)
        return status, error

    def finish(self, row, text, status, error, companion, stay, running: Round, guard: str | None = None) -> dict:
        """Saved in its final state before its live text is let go, so a poll never sees it blank. A finished
        reply is witnessed: everyone present learns any secret it gives away."""
        database = self.database
        with database.connect(write=True) as connection:
            members = current_members(connection, row['group_id'])
            if status == 'complete':
                text = tidy(text, stay['name'], members)
                if not text:
                    status, error = 'failed', 'The model returned no reply text.'
                elif companion:
                    text = texting.restyle(text, companion['version']['definition'], row['id'])
            connection.execute('UPDATE group_messages SET text=?, status=?, error=?, guard=?, completed_at=? WHERE id=?',
                               (text, status, error, guard, database.now(), row['id']))
            saved = one(connection, 'SELECT * FROM group_messages WHERE id=?', (row['id'],))
            if status == 'complete':
                secrets.witness(connection, saved)
        running.live.pop(row['id'], None)
        if status == 'complete':
            running.shown_at, running.before = time.monotonic(), text
        return saved

