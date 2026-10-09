"""Editing a companion reply in place, from the reply's Edit or the sidecar. A stopped reply can be edited too,
and the edit makes it the finished reply. The user's own messages are not edited here:
memories come from the user's words, so changing those is Edit on the message (a new timeline) instead.

An edited reply is what every later reply and recall sees. What the old wording said about her goes with
it, the way it does when a reply is replaced (docs/architecture.md): self-facts the user has not decided
on and plans she made in that reply are noted again from the new text. Each edit keeps the text it
replaced in `message_edits`, so it can be undone by editing back.
"""
from companion import self_facts
from companion.characters import for_timeline, require_current
from companion.database import identifier, one
from companion.errors import require
from companion.life import own_plans

TEXT_LIMIT = 8000
# A reply the user stopped, or one the model cut short, can be finished by hand.
UNFINISHED = ('cancelled', 'incomplete')


def editable(message: dict) -> bool:
    if message['redacted_at'] is not None:
        return False
    return message['status'] == 'complete' or (message['status'] in UNFINISHED and message['superseded_at'] is None)


def keep(connection, message: dict) -> None:
    """An edited stopped reply becomes a finished one: the version of this turn the conversation goes on from."""
    connection.execute("UPDATE messages SET status='complete', error=NULL, completed_at=COALESCE(completed_at, ?) "
                       'WHERE id=?', (message['created_at'], message['id']))
    if message['reply_to']:
        connection.execute('UPDATE messages SET active=0 WHERE reply_to=?', (message['reply_to'],))
    connection.execute('UPDATE messages SET active=1 WHERE id=?', (message['id'],))


def edit(database, message_id: str, text: str, expected_text: str) -> dict:
    text = text.strip()
    require(text, 'A reply cannot be edited to nothing. Delete it from recall instead.', 422)
    with database.connect(write=True) as connection:
        message = one(connection, 'SELECT * FROM messages WHERE id=?', (message_id,))
        require(message['role'] == 'companion', "Only the companion's replies can be edited.", 422)
        require(editable(message), 'Only a reply that is still shown can be edited. One still being written can be '
                'stopped first.', 409)
        require(message['text'] == expected_text, 'This reply changed since the edit was proposed. Ask again.', 409)
        now = database.now()
        connection.execute('UPDATE messages SET text=? WHERE id=?', (text[:TEXT_LIMIT], message_id))
        if message['status'] != 'complete':
            keep(connection, message)
        connection.execute('INSERT INTO message_edits (id, message_id, before_text, after_text, created_at) '
                           'VALUES (?, ?, ?, ?, ?)', (identifier(), message_id, message['text'], text, now))
        # What the old wording said about her leaves with it; decisions the user made on self-facts stay.
        connection.execute("DELETE FROM self_facts WHERE message_id=? AND status IN ('noted', 'conflict')",
                           (message_id,))
        connection.execute('DELETE FROM companion_plans WHERE message_id=?', (message_id,))
        # The memory model reads the new wording again too.
        connection.execute('DELETE FROM self_fact_jobs WHERE message_id=?', (message_id,))
        edited = one(connection, 'SELECT * FROM messages WHERE id=?', (message_id,))
        if edited['active']:
            self_facts.note(connection, edited, now)
            own_plans.note(connection, edited, for_timeline(connection, edited['timeline_id'])
                           or require_current(connection), now)
        return {'id': message_id, 'text': edited['text'], 'previous_text': message['text']}
