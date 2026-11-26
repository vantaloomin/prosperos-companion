"""Telling it again in the Story (docs/story.md, "Another reply and changing your line").

The story has one course: there are no timelines here, as a chat has, and no earlier versions to page back to. So
the replies to the user's latest line can be told again (Another reply), and the line itself can be said differently
and answered anew (Edit), only while nothing has come after them. What the replies told before had done is taken
back where rules did it:

- nobody in the scene learned anything from them (companion/story_secrets.py `unsay`);
- the people met in them are as they were before: someone first named there is a stranger again, and the
  sentences kept about anyone are gone (`met_before` on the narrator's reply holds how they were);
- someone who said yes in them has not said it: their rules answer again, the same way;
- what a companion said about themselves in them is not on record (companion/self_facts.py).

How a companion felt about the old words stays felt, and so does a relationship step they settled: those were
theirs, not the telling's.

A reply's own wording can also be changed in place (Edit on the narrator's reply or a companion's line), at any
point of the story: the story goes on from the new words, as every later reply reads them. What the old wording
left behind follows it: the sentences kept about the people met, what a companion said about themselves and, for a
line of the latest exchange, what it let the others in the scene learn.
"""
from companion import story_cast, story_people, story_said, story_secrets, story_visits
from companion.database import decode, encode, many, optional

PEOPLE = ('city_id', 'name', 'first_met_at', 'last_met_at', 'last_day', 'meetings', 'notes')
MOVED_ON = 'The story has gone on since then.'
LATEST_ONLY = 'Only your latest line can be changed, and only until the story goes on.'


def latest(connection) -> dict | None:
    """The user's latest line, the one still being answered."""
    return optional(connection, "SELECT * FROM story_messages WHERE role='user' ORDER BY seq DESC LIMIT 1")


def at_the_end(connection, user: dict) -> bool:
    """Whether nothing has come after the line but its own replies. Going somewhere else puts the story past it."""
    last = optional(connection, 'SELECT id, reply_to FROM story_messages ORDER BY seq DESC LIMIT 1')
    return last is not None and user['id'] in (last['id'], last['reply_to'])


# The people met ---------------------------------------------------------------------------------------

def met(connection, keys) -> dict[str, dict | None]:
    """{key: their story_people row, or None for someone not met} for the people in the scene."""
    keys = list(keys)
    marks = ', '.join('?' for _ in keys)
    rows = {row['key']: row for row in many(connection, f'SELECT * FROM story_people WHERE key IN ({marks})', keys)} \
        if keys else {}
    return {key: rows.get(key) for key in keys}


def keep(connection, told: dict, before: dict[str, dict | None]) -> None:
    """After the narrator's reply is saved: how the people it changed were before it, kept on the reply for a
    retelling. Only the latest reply can be told again, so only it holds any."""
    now = met(connection, before)
    changed = {key: row for key, row in before.items() if now[key] != row}
    connection.execute('UPDATE story_messages SET met_before=NULL WHERE met_before IS NOT NULL')
    if changed:
        connection.execute('UPDATE story_messages SET met_before=? WHERE id=?', (encode(changed), told['id']))


def restore(connection, before: dict[str, dict | None]) -> None:
    for key, row in before.items():
        connection.execute('DELETE FROM story_people WHERE key=?', (key,))
        if row:
            connection.execute(f"INSERT INTO story_people (key, {', '.join(PEOPLE)}) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                               (key, *(row[field] for field in PEOPLE)))


# Taking the replies back ----------------------------------------------------------------------------------

def take_back(connection, user: dict, timestamp: str) -> None:
    """The replies to the line go, and with them what they had done (the module's own notes say what)."""
    rows = many(connection, 'SELECT * FROM story_messages WHERE reply_to=? ORDER BY seq', (user['id'],))
    if not rows:
        return
    ids = [row['id'] for row in rows]
    marks = ', '.join('?' for _ in ids)
    story_secrets.unsay(connection, ids, timestamp)
    for row in rows:
        if row['met_before']:
            restore(connection, decode(row['met_before']))
        if row['role'] == 'cast' and row['speaker'] is None:
            # How asking someone out went (companion/story_pursuit.py `settle`): a yes was saved at the same moment.
            connection.execute("DELETE FROM dating_swipes WHERE source='story' AND matched=1 AND created_at=?",
                               (row['created_at'],))
    connection.execute(f'DELETE FROM self_facts WHERE story_message_id IN ({marks})', ids)
    connection.execute('DELETE FROM story_messages WHERE reply_to=?', (user['id'],))


# Saying the line differently ------------------------------------------------------------------------------

def reword(connection, user: dict, text: str, view: dict, now, timestamp: str) -> dict:
    """The user's line with new words, read as a new line is: what the old words gave away is taken back, and the
    companions in the scene hear the new ones (companion/story_visits.py `said_again`)."""
    story_secrets.unsay(connection, [user['id']], timestamp)
    connection.execute('UPDATE story_messages SET text=? WHERE id=?', (text, user['id']))
    said = {**user, 'text': text}
    story_visits.said_again(connection, said, user['text'], view, now)
    story_secrets.sync(connection, view, now)
    story_secrets.heard(connection, said, view)
    return said


# A reply's wording, changed in place --------------------------------------------------------------------

def editable(row: dict) -> bool:
    return row['role'] in ('narrator', story_cast.ROLE) and row['status'] == 'complete'


def reword_reply(connection, row: dict, text: str, view: dict, met: list[tuple[dict, dict]], timestamp: str) -> dict:
    """The narrator's reply or a companion's line with the user's wording. `met` is (their `known` row, their sheet)
    for everyone the user has met."""
    connection.execute('UPDATE story_messages SET text=? WHERE id=?', (text, row['id']))
    changed = {**row, 'text': text}
    if row['role'] == 'narrator':
        for known, sheet in met:
            story_people.reworded(connection, known, sheet, row['text'], text)
    else:
        respoken(connection, changed, view, timestamp)
    return changed


def respoken(connection, line: dict, view: dict, timestamp: str) -> None:
    """A companion's line as the user reworded it: what they said about themselves is noted again from the new
    words. While it is part of the latest exchange, the scene is still the one it was said in, so what it lets the
    others there learn is read again too, and a slip that is no longer in it was never made."""
    connection.execute('DELETE FROM self_facts WHERE story_message_id=?', (line['id'],))
    user = latest(connection)
    if user and line['reply_to'] == user['id'] and at_the_end(connection, user):
        story_secrets.unsay(connection, [line['id']], timestamp)
        if not story_secrets.heard(connection, line, view):
            connection.execute('DELETE FROM story_messages WHERE role=? AND reply_to=? AND speaker=?',
                               (story_cast.NOTE, line['reply_to'], line['speaker']))
    companion = story_visits.by_id(connection, line['speaker'])
    if companion and story_visits.counts(connection):
        story_said.noted(connection, companion, line)


def shown(row: dict) -> dict:
    """A story line as the API gives it: without what is kept for a retelling."""
    return {key: value for key, value in row.items() if key != 'met_before'}
