"""The user's chats, the way a messaging app lists them: who, the latest message and how many are unread.

Each companion has one chat, their active timeline. Other kinds of chat (group chats) add their own entries
through `KINDS` and keep their read position in the same table, keyed by their own id. Unread counts the
messages someone else sent after the last one the user saw or wrote; a held reply (companion/life/pacing.py) counts
once its time has come. Nothing here says whether anyone is around: no presence, no read receipts.
"""
from companion.characters import current
from companion.clock import stamp
from companion.database import many, one, optional

PREVIEW = 120


def mark_read(connection, thread_id: str, seq: int | None, timestamp: str) -> None:
    """The user has seen the chat up to `seq` (its latest message when None). Never moves backwards."""
    if seq is None:
        seq = one(connection, 'SELECT COALESCE(MAX(seq), 0) AS seq FROM messages WHERE timeline_id=?',
                  (thread_id,))['seq']
    connection.execute('INSERT INTO chat_reads (thread_id, read_seq, read_at) VALUES (?, ?, ?) '
                       'ON CONFLICT(thread_id) DO UPDATE SET read_seq=MAX(read_seq, excluded.read_seq), '
                       'read_at=excluded.read_at', (thread_id, seq, timestamp))


def shown(where: str = '') -> str:
    return (f"{where}role='companion' AND active=1 AND status='complete' AND redacted_at IS NULL "
            'AND superseded_at IS NULL AND (held_until IS NULL OR held_until<=?)')


def unread(connection, timeline_id: str, now) -> int:
    """Their messages after both the last one the user saw and the user's own last message: writing back
    means the user read what came before."""
    seen = one(connection, "SELECT MAX(COALESCE((SELECT read_seq FROM chat_reads WHERE thread_id=?), 0), "
               "COALESCE((SELECT MAX(seq) FROM messages WHERE timeline_id=? AND role='user'), 0)) AS seq",
               (timeline_id, timeline_id))['seq']
    return one(connection, f'SELECT COUNT(*) AS n FROM messages WHERE timeline_id=? AND seq>? AND {shown()}',
               (timeline_id, seen, stamp(now)))['n']


def latest(connection, timeline_id: str, now) -> dict | None:
    """The last message either of them sent that the user can see."""
    row = optional(connection, "SELECT role, text, created_at FROM messages WHERE timeline_id=? AND active=1 AND "
                   "status='complete' AND redacted_at IS NULL AND superseded_at IS NULL AND "
                   '(held_until IS NULL OR held_until<=?) ORDER BY seq DESC LIMIT 1', (timeline_id, stamp(now)))
    if row is None:
        return None
    text = ' '.join(row['text'].split())
    return {'role': row['role'], 'text': text if len(text) <= PREVIEW else text[:PREVIEW - 1].rstrip() + '…',
            'at': row['created_at']}


def companion_chats(connection, now) -> list[dict]:
    focus = current(connection)
    rows = many(connection, 'SELECT c.id, c.active_timeline_id, c.created_at, v.name FROM companions c '
                'JOIN character_versions v ON v.id=c.active_version_id')
    chats = []
    for row in rows:
        last = latest(connection, row['active_timeline_id'], now)
        chats.append({'kind': 'companion', 'id': row['id'], 'thread_id': row['active_timeline_id'],
                      'name': row['name'], 'focus': bool(focus and focus['id'] == row['id']),
                      'unread': unread(connection, row['active_timeline_id'], now), 'last': last,
                      'active_at': last['at'] if last else row['created_at']})
    return chats


# Each kind of chat lists its own entries: (connection, now) -> [{kind, id, thread_id, name, focus, unread,
# last, active_at}].
KINDS = [companion_chats]


def listed(database) -> dict:
    """Every chat, the most recently active first."""
    now = database.clock.now()
    with database.connect() as connection:
        chats = [chat for kind in KINDS for chat in kind(connection, now)]
    chats.sort(key=lambda chat: chat['active_at'], reverse=True)
    return {'chats': chats, 'unread': sum(chat['unread'] for chat in chats)}


def read(database, thread_id: str, seq: int | None) -> dict:
    with database.connect(write=True) as connection:
        mark_read(connection, thread_id, seq, database.now())
    return listed(database)
