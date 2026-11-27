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

Another reply can be undone once (Undo, `put_back`), until the next line is sent: the replies told before are kept
on the user's line with what they had done (`told_before`), and come back in place of the ones told since.

A reply's own wording can also be changed in place (Edit on the narrator's reply or a companion's line), at any
point of the story: the story goes on from the new words, as every later reply reads them. What the old wording
left behind follows it: the sentences kept about the people met, what a companion said about themselves and, for a
line of the latest exchange, what it let the others in the scene learn.
"""
from companion import story_cast, story_chapters, story_people, story_private, story_said, story_secrets, story_visits
from companion.database import decode, encode, many, optional

PEOPLE = ('city_id', 'name', 'first_met_at', 'last_met_at', 'last_day', 'meetings', 'notes')
HELD = ('self_facts', 'news_holders', 'dating_swipes')  # Rows the replies left, kept whole for Undo.
MOVED_ON = 'The story has gone on since then.'
NO_UNDO = 'There is no earlier reply to bring back.'
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

def take_back(connection, user: dict, timestamp: str) -> dict | None:
    """The replies to the line go, and with them what they had done (the module's own notes say what). Returns
    what was taken, as `put_back` reads it, or None when there were no replies."""
    rows = many(connection, 'SELECT * FROM story_messages WHERE reply_to=? ORDER BY seq', (user['id'],))
    if not rows:
        return None
    ids = [row['id'] for row in rows]
    marks = ', '.join('?' for _ in ids)
    taken = {'at': timestamp, 'rows': rows, 'people': met(connection, touched(rows)),
             'self_facts': many(connection, f'SELECT * FROM self_facts WHERE story_message_id IN ({marks})', ids),
             'news_holders': many(connection, f'SELECT * FROM news_holders WHERE message_id IN ({marks})', ids),
             'dating_swipes': []}
    story_secrets.unsay(connection, ids, timestamp)
    for row in rows:
        if row['met_before']:
            restore(connection, decode(row['met_before']))
        if row['role'] == 'cast' and row['speaker'] is None:
            # How asking someone out went (companion/story_pursuit.py `settle`): a yes was saved at the same moment.
            said_yes = "source='story' AND matched=1 AND created_at=?"
            taken['dating_swipes'] += many(connection, f'SELECT * FROM dating_swipes WHERE {said_yes}',
                                           (row['created_at'],))
            connection.execute(f'DELETE FROM dating_swipes WHERE {said_yes}', (row['created_at'],))
    connection.execute(f'DELETE FROM self_facts WHERE story_message_id IN ({marks})', ids)
    connection.execute('DELETE FROM story_messages WHERE reply_to=?', (user['id'],))
    story_chapters.keep_waiting(connection)
    return taken


def touched(rows: list[dict]) -> list[str]:
    """The people the replies changed: the ones whose earlier selves they hold."""
    return sorted({key for row in rows if row['met_before'] for key in decode(row['met_before'])})


# Undo on Another reply ------------------------------------------------------------------------------------

def hold(connection, user: dict, taken: dict | None) -> None:
    """The replies just taken back are kept on the user's line, so that Another reply can be undone. One step back:
    what was kept before goes."""
    connection.execute('UPDATE story_messages SET told_before=? WHERE id=?', (taken and encode(taken), user['id']))


def let_go(connection) -> None:
    """The story goes on (a new line, or the latest one said differently): nothing is kept to undo."""
    connection.execute('UPDATE story_messages SET told_before=NULL WHERE told_before IS NOT NULL')


def put_back(connection, user: dict, timestamp: str) -> None:
    """Undo: the replies told since go as on a retelling, and the ones kept on the line are back as they were, with
    what they had done: the people met in them, a yes, what a companion said about themselves, and what they let
    the others in the scene learn."""
    held = decode(user['told_before'])
    take_back(connection, user, timestamp)
    seq = optional(connection, 'SELECT COALESCE(MAX(seq), 0) AS seq FROM story_messages')['seq']
    for place, row in enumerate(held['rows'], start=1):
        insert(connection, 'story_messages', {**row, 'seq': seq + place})
    restore(connection, held['people'])
    for table in HELD:
        for row in held[table]:
            insert(connection, table, row)
    ids = [row['id'] for row in held['rows']]
    marks = ', '.join('?' for _ in ids)
    connection.execute(f'UPDATE knowledge_holders SET ended_at=NULL WHERE ended_at=? AND message_id IN ({marks})',
                       (held['at'], *ids))
    hold(connection, user, None)


def insert(connection, table: str, row: dict) -> None:
    fields = list(row)
    connection.execute(f"INSERT OR REPLACE INTO {table} ({', '.join(fields)}) VALUES ({', '.join('?' for _ in fields)})",
                       [row[field] for field in fields])


# Saying the line differently ------------------------------------------------------------------------------

def reword(connection, user: dict, text: str, view: dict, now, timestamp: str) -> dict:
    """The user's line with new words, read as a new line is: what the old words gave away is taken back, and the
    companions in the scene hear the new ones (companion/story_visits.py `said_again`). An earlier reply kept for Undo
    answered the old words, and goes."""
    story_secrets.unsay(connection, [user['id']], timestamp)
    let_go(connection)
    connection.execute('UPDATE story_messages SET text=? WHERE id=?', (text, user['id']))
    said = {**user, 'text': text, 'told_before': None}
    story_private.mark(connection, said, view)
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
    """A story line as the API gives it: without what is kept for a retelling, and with whether Another reply on it
    can be undone (`undo`)."""
    return {**{key: value for key, value in row.items() if key not in ('met_before', 'told_before')},
            'undo': bool(row.get('told_before'))}
