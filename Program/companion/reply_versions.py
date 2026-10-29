"""Versions of one reply, and which one the conversation goes on from.

Replies to one message (`reply_to`) are versions of each other: Another reply adds one, and paging back to an
earlier one and leaving it there makes it the active one, so the next reply is written from the version on screen
and it stays on screen once the conversation moves on. A full reply sent after a holding text ("brb, boss is here",
companion/life/pacing.py) answers no message of its own; its later versions point at it with `version_of`.
"""
from companion.database import one
from companion.errors import require


def activate(connection, message: dict) -> None:
    """Make `message` the version shown and remembered, and none of its siblings."""
    if message['reply_to']:
        connection.execute('UPDATE messages SET active=0 WHERE reply_to=?', (message['reply_to'],))
    elif root := message.get('version_of') or (message['held_line'] and message['role'] == 'companion' and message['id']):
        connection.execute('UPDATE messages SET active=0 WHERE id=? OR version_of=?', (root, root))
    connection.execute('UPDATE messages SET active=1 WHERE id=?', (message['id'],))


def choose(database, message_id: str) -> dict:
    """The user paged to this version and kept it: the conversation goes on from it."""
    with database.connect(write=True) as connection:
        message = one(connection, "SELECT * FROM messages WHERE id=? AND role='companion'", (message_id,))
        require(message['status'] == 'complete' and message['redacted_at'] is None and not message['superseded_at'],
                'Only a finished reply can be the one the conversation goes on from.', 409)
        activate(connection, message)
        return {'id': message_id, 'active': True}
