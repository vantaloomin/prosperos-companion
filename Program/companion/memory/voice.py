"""Their voice stays theirs (v1.0): a few short excerpts of the companion's own earlier replies in every chat reply's
system prompt, so they still sound like themselves when the model changes.

The app picks the excerpts by rule from replies the user kept: finished, never edited, the only version of their
turn (not a regenerate), not an answer to an out-of-character message, and from before the conversation sent with
the reply, so they are not already in it. It mixes days and lengths, and leaves out anything that reads intimate or
names a child (companion/memory/sides.py), whatever the settings, so it fails closed. The user can pin up to three
replies with "Pin their voice" in a reply's menu; pins come first. The pick only changes when the conversation's
window steps or a pin changes, so prompt caching holds. A character with no kept replies yet has their example
messages in their sheet already ('Voice'), so nothing more is added. Rules only, no model call.
"""
import random
import re

from companion import prompt_library
from companion.database import identifier, many, one, optional
from companion.errors import DomainError, require
from companion.memory import sides

LIMIT = 3
GROUP_LIMIT = 2
PINS = 3
# The newest kept replies the pick looks through.
POOL = 60
# An excerpt: the first sentence or two, cut at a sentence end where it can be.
EXCERPT_CHARS = 160
MIN_CHARS = 25
MIN_WORDS = 5
SHORT, LONG = 80, 150
SENTENCE = re.compile(r'(?<=[.!?…])["”’)\]*]*\s+')
OOC = re.compile(r'^\s*(?:ooc\s*:|\(\()', re.IGNORECASE)

# The section's opening line, editable in Settings > Advanced > Prompts (companion/prompt_library.py).
INTRO = ('A few things you said before, in your own words. They show how you sound: your rhythm, your words, your '
         'humor. Keep sounding like this in new words: never reuse these lines or their phrases, never open a reply '
         'with them, and never bring up what they were about.')


def excerpt(text: str) -> str | None:
    """The first sentence or two of a reply, or None when it is too short to show a voice. The opening is where a
    voice shows most: the A/B tried sentences from the middle, and they carried stories the model retold."""
    text = ' '.join(text.split())
    sentences = SENTENCE.split(text)
    found = sentences[0]
    if len(sentences) > 1 and len(found) < SHORT and len(found) + len(sentences[1]) < EXCERPT_CHARS:
        found = f'{found} {sentences[1]}'
    if len(found) > EXCERPT_CHARS:
        found = found[:EXCERPT_CHARS].rsplit(' ', 1)[0] + '…'
    return found if len(found) >= MIN_CHARS and len(found.split()) >= MIN_WORDS else None


def length_kind(text: str) -> str:
    return 'short' if len(text) < SHORT else 'long' if len(text) > LONG else 'medium'


def safe(text: str, children: set[str]) -> bool:
    """Nothing from the adult side and nothing about a child, always."""
    return not sides.reads_intimate([text]) and not re.search(sides.CHILD_WORDS, text) \
        and not sides.names_child([text], children)


def choose(candidates: list[dict], seed: str, limit: int) -> list[dict]:
    """Up to `limit` of these, each new pick from another day and another length when there is one. The same
    candidates and seed always give the same pick."""
    shuffled = sorted(candidates, key=lambda item: item['id'])
    random.Random(seed).shuffle(shuffled)
    picked: list[dict] = []
    while shuffled and len(picked) < limit:
        days = {item['day'] for item in picked}
        kinds = {item['kind'] for item in picked}
        best = min(shuffled, key=lambda item: ((item['day'] in days) + (item['kind'] in kinds), shuffled.index(item)))
        picked.append(best)
        shuffled.remove(best)
    return picked


def candidate(message: dict, children: set[str]) -> dict | None:
    text = excerpt(message['text'])
    if text is None or not safe(text, children):
        return None
    return {'id': message['id'], 'origin': message.get('origin_id') or message['id'], 'text': text,
            'day': message['created_at'][:10], 'kind': length_kind(text)}


def kept(connection, messages: list[dict]) -> list[dict]:
    """The companion's replies here that count as kept: the only version of their turn, never edited, and not an
    answer to an out-of-character message."""
    replies = [message for message in messages if message['role'] == 'companion'][-POOL:]
    if not replies:
        return []
    ids = [message['id'] for message in replies] + [message.get('origin_id') or message['id'] for message in replies]
    marks = ','.join('?' * len(ids))
    edited = {row['message_id'] for row in many(
        connection, f'SELECT DISTINCT message_id FROM message_edits WHERE message_id IN ({marks})', tuple(ids))}
    asked = [message['reply_to'] for message in replies if message['reply_to']]
    retried = {row['reply_to'] for row in many(
        connection, f"SELECT reply_to FROM messages WHERE reply_to IN ({','.join('?' * len(asked))}) "
                    'GROUP BY reply_to HAVING COUNT(*) > 1', tuple(asked))} if asked else set()
    users = {message['id']: message['text'] for message in messages if message['role'] == 'user'}
    return [message for message in replies
            if message['id'] not in edited and (message.get('origin_id') or message['id']) not in edited
            and message['reply_to'] not in retried and not OOC.match(users.get(message['reply_to']) or '')]


def pinned(connection, companion_id: str) -> list[str]:
    return [row['message_id'] for row in many(
        connection, 'SELECT message_id FROM voice_pins WHERE companion_id=? ORDER BY created_at, message_id',
        (companion_id,))]


def excerpts(connection, companion: dict, messages: list[dict], older: list[dict], group: bool = False) -> list[str]:
    """The excerpts for this reply: pins first (found in this timeline by id or by the message they were copied
    from), then the app's pick from `older`, the part of the conversation not sent with it."""
    limit = GROUP_LIMIT if group else LIMIT
    children = sides.every_name(connection)
    pins = pinned(connection, companion['id'])
    by_id = {message['id']: message for message in messages if message['role'] == 'companion'}
    by_id |= {message['origin_id']: message for message in messages
              if message['role'] == 'companion' and message.get('origin_id')}
    chosen = [found for pin in pins if pin in by_id and (found := candidate(by_id[pin], children))][:limit]
    taken = {item['origin'] for item in chosen}
    pool = [found for message in kept(connection, older) if (found := candidate(message, children))
            and found['origin'] not in taken]
    chosen += choose(pool, f"{companion['id']}:{len(older)}", limit - len(chosen))
    return [item['text'] for item in chosen]


def offer(packet, connection, companion, messages: list[dict], older: list[dict], group: dict | None = None):
    """Adds the 'voice' section as one piece, so it is all there or not at all."""
    found = excerpts(connection, companion, messages, older, group is not None)
    if found:
        lines = [prompt_library.text(connection, 'voice'), *(f'- "{text}"' for text in found)]
        packet.offer('voice', 'voice', '\n'.join(lines))


# "Pin their voice" ---------------------------------------------------------------------------------------------------

def pin(database, message_id: str, pinned_now: bool = True) -> dict:
    """Pin a reply as sounding like them, or unpin it. Up to PINS each; the newest pin past that is refused."""
    with database.connect(write=True) as connection:
        message = one(connection, 'SELECT m.*, t.companion_id FROM messages m JOIN timelines t ON t.id=m.timeline_id '
                                  'WHERE m.id=?', (message_id,))
        require(message['role'] == 'companion' and message['status'] == 'complete' and not message['redacted_at'],
                'Only a finished reply of theirs can be pinned.', 422)
        key = message['origin_id'] or message['id']
        companion_id = message['companion_id']
        if not pinned_now:
            connection.execute('DELETE FROM voice_pins WHERE companion_id=? AND message_id IN (?, ?)',
                               (companion_id, key, message['id']))
        elif not optional(connection, 'SELECT 1 FROM voice_pins WHERE companion_id=? AND message_id=?',
                          (companion_id, key)):
            if len(pinned(connection, companion_id)) >= PINS:
                raise DomainError(f'Up to {PINS} replies can be pinned. Unpin one first.', 409, 'voice_pins_full')
            connection.execute('INSERT INTO voice_pins (id, companion_id, message_id, created_at) VALUES (?, ?, ?, ?)',
                               (identifier(), companion_id, key, database.now()))
        return view(connection, companion_id)


def view(connection, companion_id: str) -> dict:
    """The pins, with the text each one shows, for the reply menu and the Character page."""
    keys = pinned(connection, companion_id)
    rows = {}
    if keys:
        marks = ','.join('?' * len(keys))
        for row in many(connection, f'SELECT id, origin_id, text, created_at FROM messages WHERE id IN ({marks}) '
                                    f'OR origin_id IN ({marks})', (*keys, *keys)):
            rows.setdefault(row['origin_id'] or row['id'], row)
    pins = [{'message_id': key, 'text': excerpt(rows[key]['text']) or rows[key]['text'][:EXCERPT_CHARS],
             'created_at': rows[key]['created_at']} for key in keys if key in rows]
    return {'pins': pins, 'limit': PINS}
