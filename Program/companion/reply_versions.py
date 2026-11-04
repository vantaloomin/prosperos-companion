"""Versions of one reply, and which one the conversation goes on from.

Replies to one message (`reply_to`) are versions of each other: Another reply adds one, and paging back to an
earlier one and leaving it there makes it the active one, so the next reply is written from the version on screen
and it stays on screen once the conversation moves on. A full reply sent after a holding text ("brb, boss is here",
companion/life/pacing.py) answers no message of its own; its later versions point at it with `version_of`. So does
a message the companion sent first (companion/life/openers.py) while it is still their newest: another version is
written from the same reason, never a reply to anything.
"""
from companion.database import decode, many, one, optional
from companion.errors import require
from companion.images import photos
from companion.voice import notes as voice_notes


def activate(connection, message: dict) -> None:
    """Make `message` the version shown and remembered, and none of its siblings."""
    if message['reply_to']:
        connection.execute('UPDATE messages SET active=0 WHERE reply_to=?', (message['reply_to'],))
    elif message['role'] == 'companion':
        # The full reply after a holding text, or a message they sent first: its first version and later ones.
        root = message.get('version_of') or message['id']
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


def first_text(connection, message: dict) -> dict | None:
    """When `message` is a message the companion sent first (companion/life/openers.py), or another version of one:
    its first version and the reason they wrote it. None for any other message. Only their newest message gets
    another version, and a photo text or a voice note keeps the words it was sent with."""
    if message['role'] != 'companion' or message['reply_to'] or message['held_line']:
        return None
    root = one(connection, 'SELECT * FROM messages WHERE id=?', (message['version_of'] or message['id'],))
    opener = optional(connection, 'SELECT facts FROM openers WHERE message_id=?', (root['id'],))
    if opener is None:
        return None
    later = optional(connection, 'SELECT id FROM messages WHERE timeline_id=? AND seq>? AND superseded_at IS NULL '
                     'AND (version_of IS NULL OR version_of<>?) LIMIT 1', (root['timeline_id'], root['seq'], root['id']))
    require(later is None, 'Another version is only for their newest message.', 409)
    require(not photos.for_messages(connection, [root['id']]) and not voice_notes.for_messages(connection, [root['id']]),
            'A photo or a voice note keeps the words it was sent with.', 409)
    return {'message': root, 'reason': decode(opener['facts'])['reason']}


def mark_first_texts(connection, messages: list[dict]) -> list[dict]:
    """Message views marked `first_text` when the companion sent them first, so the chat can offer another version
    of their newest one (`first_text`)."""
    ids = [message['id'] for message in messages if message['role'] == 'companion' and not message['reply_to']]
    found = set()
    for start in range(0, len(ids), 500):
        part = ids[start:start + 500]
        rows = many(connection, f"SELECT message_id FROM openers WHERE message_id IN ({','.join('?' * len(part))})",
                    tuple(part))
        found.update(row['message_id'] for row in rows)
    return [{**message, 'first_text': message['id'] in found} for message in messages]
