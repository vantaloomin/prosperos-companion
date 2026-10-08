"""One shared allowance for messages sent while the user is away.

Every companion may start a conversation on their own (companion/life/openers.py), and each such message
can cost a model call. Left running all day, that adds up across many companions, so they share one
allowance: at most `life_settings.away_daily` messages in any 24 hours, from everyone together. Group chats
draw from the same allowance: ask `allowed` before writing a message nobody asked for, and `record` it in
the same transaction that saves it. 0 means no one messages first.
"""
from datetime import timedelta

from companion.clock import stamp
from companion.database import identifier, one

WINDOW = timedelta(days=1)


def daily(connection) -> int:
    return one(connection, 'SELECT away_daily FROM life_settings WHERE id=1')['away_daily']


def spent(connection, now) -> int:
    return one(connection, 'SELECT COUNT(*) AS n FROM away_messages WHERE created_at>?',
               (stamp(now - WINDOW),))['n']


def left(connection, now) -> int:
    return max(0, daily(connection) - spent(connection, now))


def allowed(connection, now) -> bool:
    return left(connection, now) > 0


def record(connection, kind: str, thread_id: str, message_id: str, timestamp: str):
    """`kind` is the chat it went to: 'companion' for a one-to-one chat (thread_id is its timeline)."""
    connection.execute('INSERT INTO away_messages (id, kind, thread_id, message_id, created_at) '
                       'VALUES (?, ?, ?, ?, ?)', (identifier(), kind, thread_id, message_id, timestamp))
