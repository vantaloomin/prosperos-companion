"""Alternative timelines: historical edits, switching and freezing (PRD C4, T7, M6).

Editing an earlier message never rewrites the live relationship. It creates a separate, inactive
timeline holding a copy of everything before that message: the conversation, the companion's
committed events and the posts showing them, the circle and the circle's diary. The edited words
wait on the new timeline as its draft until they are sent there. Memories are not copied; a
timeline sees what its ancestors remembered before the fork (companion/lineage.py).

Only the active timeline advances with real time. Choosing another one freezes the active one:
its unreviewed events are rejected, its unfinished batches stop, its hidden upcoming agenda is
dropped, and replies still being written there are stopped and withheld. Both revisions advance,
so any work that finishes later is revalidated and cannot reach the newly active companion (T7).
A timeline's life resumes from the moment it is chosen; time spent frozen is never filled in.
"""
import re

from companion.characters import require_current
from companion.database import decode, encode, identifier, many, one, optional
from companion.errors import require
from companion.life import encounters, feed, home, network, social

ID = re.compile(r'\b[0-9a-f]{32}\b')
FROZEN_EVENT = 'The timeline was frozen before this event was reviewed.'
FROZEN_RUN = 'The timeline was frozen before this batch finished.'
FROZEN_IMAGE = 'The timeline was set aside before this image started.'


def view(connection, row: dict, active_id: str) -> dict:
    stats = one(connection, "SELECT COUNT(*) AS messages, MAX(created_at) AS last_message_at FROM messages "
                "WHERE timeline_id=? AND redacted_at IS NULL AND (role='user' OR status='complete')", (row['id'],))
    latest = optional(connection, "SELECT text FROM messages WHERE timeline_id=? AND role='user' "
                      'AND redacted_at IS NULL ORDER BY seq DESC LIMIT 1', (row['id'],))
    label = row['label'] or ('Original' if row['parent_id'] is None else 'Alternative')
    return {'id': row['id'], 'label': label, 'status': row['status'], 'active': row['id'] == active_id,
            'parent_id': row['parent_id'], 'fork_message_id': row['fork_message_id'], 'forked_at': row['forked_at'],
            'created_at': row['created_at'], 'activated_at': row['activated_at'], 'frozen_at': row['frozen_at'],
            'draft': row['draft'], 'messages': stats['messages'], 'last_message_at': stats['last_message_at'],
            'latest_text': (latest['text'][:160] if latest else '')}


def listing(database) -> dict:
    with database.connect() as connection:
        companion = require_current(connection)
        rows = many(connection, 'SELECT * FROM timelines WHERE companion_id=? ORDER BY created_at, rowid',
                    (companion['id'],))
        return {'active_id': companion['active_timeline_id'],
                'timelines': [view(connection, row, companion['active_timeline_id']) for row in rows]}


def timeline(connection, companion, timeline_id) -> dict:
    row = optional(connection, 'SELECT * FROM timelines WHERE id=? AND companion_id=?',
                   (timeline_id, companion['id']))
    require(row is not None, 'That timeline could not be found.', 404)
    return row


def update(database, timeline_id, body) -> dict:
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        timeline(connection, companion, timeline_id)
        if body.label is not None:
            connection.execute('UPDATE timelines SET label=? WHERE id=?', (body.label.strip(), timeline_id))
        if body.clear_draft:
            connection.execute('UPDATE timelines SET draft=NULL WHERE id=?', (timeline_id,))
        return view(connection, timeline(connection, companion, timeline_id), companion['active_timeline_id'])


# Forking ----------------------------------------------------------------------------------------

def fork(database, body) -> dict:
    """Edit from here: a new inactive timeline with everything before `message_id`, and the edited
    words as its draft. The timeline the message is on is left exactly as it was."""
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        message = optional(connection, 'SELECT * FROM messages WHERE id=?', (body.message_id,))
        require(message is not None, 'That message could not be found.', 404)
        parent = timeline(connection, companion, message['timeline_id'])
        require(message['role'] == 'user', 'Only your own messages can be edited.', 422)
        require(message['redacted_at'] is None, 'This message was deleted.', 409)
        timestamp, new_id = database.now(), identifier()
        count = one(connection, 'SELECT COUNT(*) AS n FROM timelines WHERE companion_id=?', (companion['id'],))['n']
        connection.execute(
            'INSERT INTO timelines (id, companion_id, parent_id, forked_after_seq, status, created_at, label, '
            "fork_message_id, forked_at, draft) VALUES (?, ?, ?, ?, 'frozen', ?, ?, ?, ?, ?)",
            (new_id, companion['id'], parent['id'], message['seq'] - 1, timestamp,
             body.label.strip() or f'Timeline {count + 1}', message['id'], message['created_at'], body.text))
        copy_history(connection, parent['id'], new_id, message)
        return view(connection, timeline(connection, companion, new_id), companion['active_timeline_id'])


def columns(connection, table) -> list[str]:
    return [row[1] for row in connection.execute(f'PRAGMA table_info({table})')]


def insert(connection, table, rows: list[dict]):
    if not rows:
        return
    names = columns(connection, table)
    marks = ', '.join('?' * len(names))
    connection.executemany(f'INSERT INTO {table} ({", ".join(names)}) VALUES ({marks})',
                           [tuple(row.get(name) for name in names) for row in rows])


def remap(value, ids: dict):
    """Rewrite identities inside a stored text (keys, JSON details) to their copies."""
    if value is None:
        return None
    return ID.sub(lambda match: ids.get(match.group(), match.group()), value)


def copied_key(key: str, ids: dict, new_id: str) -> str:
    changed = remap(key, ids)
    return changed if changed != key else f'fork:{new_id}:{key}'


def copy_history(connection, parent_id, new_id, message):
    """Copy the parent's history before the edited message into the new timeline."""
    cutoff = message['created_at']
    ids = {parent_id: new_id}
    messages = many(connection, 'SELECT * FROM messages WHERE timeline_id=? AND seq<? ORDER BY seq',
                    (parent_id, message['seq']))
    events = many(connection, "SELECT * FROM life_events WHERE timeline_id=? AND status='committed' "
                  "AND (ends_at<=? OR (kind='plan' AND created_at<=?)) ORDER BY starts_at", (parent_id, cutoff, cutoff))
    people = many(connection, 'SELECT * FROM circle_people WHERE timeline_id=? ORDER BY ordinal', (parent_id,))
    for row in messages + events + people:
        ids[row['id']] = identifier()
    recommended = [row for row in many(connection, 'SELECT * FROM recommendations WHERE timeline_id=?', (parent_id,))
                   if row['message_id'] in ids]
    for row in recommended:
        ids[row['id']] = identifier()
    # A post links the version of an event it was made with; a corrected event's earlier versions
    # point at the copy of its current one, so the post carries over showing the correction.
    for row in many(connection, "SELECT id FROM life_events WHERE timeline_id=? AND status='superseded'",
                    (parent_id,)):
        current = feed.current_revision(connection, row['id'])
        if current and current['id'] in ids:
            ids[row['id']] = ids[current['id']]
    posts = [post for post in many(connection, 'SELECT * FROM feed_posts WHERE timeline_id=?', (parent_id,))
             if all(link['event_id'] in ids for link in post_links(connection, post['id']))]
    for post in posts:
        ids[post['id']] = identifier()
    copy_messages(connection, messages, ids, new_id)
    insert(connection, 'life_events', [{
        **row, 'id': ids[row['id']], 'timeline_id': new_id, 'supersedes_id': None,
        'idempotency_key': copied_key(row['idempotency_key'], ids, new_id), 'details': remap(row['details'], ids),
    } for row in events])
    insert(connection, 'circle_people', [{**row, 'id': ids[row['id']], 'timeline_id': new_id} for row in people])
    home.copy(connection, parent_id, new_id, cutoff, ids)
    copy_posts(connection, posts, ids, new_id)
    social.copy(connection, parent_id, new_id, cutoff, ids, remap)
    # Triggers already used before the fork stay used, so the copy is not texted about them again.
    insert(connection, 'openers', [{**row, 'id': identifier(), 'timeline_id': new_id, 'message_id': ids[row['message_id']],
                                    'notify': None} for row in many(connection, 'SELECT * FROM openers WHERE timeline_id=?',
                                                                    (parent_id,)) if row['message_id'] in ids])
    insert(connection, 'recommendations', [{**row, 'id': ids[row['id']], 'timeline_id': new_id,
                                            'message_id': ids[row['message_id']]} for row in recommended])
    copy_storylines(connection, parent_id, new_id, ids, cutoff[:10])
    network.copy(connection, parent_id, new_id, cutoff)
    encounters.copy(connection, parent_id, new_id, cutoff)
    agenda = many(connection, "SELECT * FROM life_agenda WHERE timeline_id=? AND status IN ('happened','skipped') "
                  'AND ends_at<=?', (parent_id, cutoff))
    insert(connection, 'life_agenda', [{
        **row, 'id': identifier(), 'timeline_id': new_id, 'subject': ids.get(row['subject'], row['subject']),
        'entry': remap(row['entry'], ids), 'prepared': None} for row in agenda])


def copy_storylines(connection, parent_id, new_id, ids, cutoff_date):
    """Storylines that had started by the fork carry over with their cast; later starts are the copy's own."""
    rows = [row for row in many(connection, 'SELECT * FROM storylines WHERE timeline_id=? AND started_on<=?',
                                (parent_id, cutoff_date))
            if all(person in ids for person in decode(row['cast_ids']))]
    insert(connection, 'storylines', [{**row, 'id': identifier(), 'timeline_id': new_id,
                                       'cast_ids': encode([ids[person] for person in decode(row['cast_ids'])])}
                                      for row in rows])
    if optional(connection, 'SELECT through FROM storyline_days WHERE timeline_id=?', (parent_id,)):
        connection.execute('INSERT INTO storyline_days (timeline_id, through) VALUES (?, ?)', (new_id, cutoff_date))


def post_links(connection, post_id) -> list[dict]:
    return many(connection, 'SELECT * FROM feed_post_events WHERE post_id=? ORDER BY position', (post_id,))


def copy_messages(connection, messages, ids, new_id):
    insert(connection, 'messages', [{
        **row, 'id': ids[row['id']], 'timeline_id': new_id, 'client_id': None,
        'reply_to': ids.get(row['reply_to']) if row['reply_to'] else None,
        'status': 'incomplete' if row['status'] == 'streaming' else row['status'],
        'receipt': remap(row['receipt'], ids), 'origin_id': row['origin_id'] or row['id'],
    } for row in messages])
    for row in messages:
        # The same text has the same embedding, so recall in the fork needs no new requests.
        connection.execute(
            'INSERT OR IGNORE INTO memory_vectors (owner_kind, owner_id, model, digest, vector, created_at) '
            "SELECT owner_kind, ?, model, digest, vector, created_at FROM memory_vectors "
            "WHERE owner_kind='message' AND owner_id=?", (ids[row['id']], row['id']))


def copy_posts(connection, posts, ids, new_id):
    copies = []
    for post in posts:
        drawn = post['image_status'] == 'completed' and post['image_ref']
        copies.append({**post, 'id': ids[post['id']], 'timeline_id': new_id,
                       'idempotency_key': copied_key(post['idempotency_key'], ids, new_id),
                       'image_status': 'completed' if drawn else 'none', 'image_job_id': None,
                       'image_ref': post['image_ref'] if drawn else None, 'image_error': None})
    insert(connection, 'feed_posts', copies)
    for post in posts:
        insert(connection, 'feed_post_events', [{**link, 'post_id': ids[post['id']], 'event_id': ids[link['event_id']]}
                                                for link in post_links(connection, post['id'])])
    links = many(connection, 'SELECT * FROM message_post_links')
    insert(connection, 'message_post_links', [
        {'message_id': ids[link['message_id']], 'post_id': ids[link['post_id']]}
        for link in links if link['message_id'] in ids and link['post_id'] in ids])
    sent = many(connection, 'SELECT * FROM chat_photos')
    insert(connection, 'chat_photos', [
        {**photo, 'message_id': ids[photo['message_id']], 'post_id': ids[photo['post_id']],
         'event_key': remap(photo['event_key'], ids)}
        for photo in sent if photo['message_id'] in ids and photo['post_id'] in ids])


# Switching --------------------------------------------------------------------------------------

def activate(database, timeline_id) -> dict:
    """Choose a timeline. The previously active one is frozen and its pending work reconciled.

    Returns the timelines and the reply attempts that were still being written on the frozen
    timeline, which the caller stops; they could never become active there anyway."""
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        target = timeline(connection, companion, timeline_id)
        previous, stopped = companion['active_timeline_id'], []
        if target['id'] != previous:
            timestamp = database.now()
            stopped = freeze(connection, previous, timestamp)
            connection.execute("UPDATE timelines SET status='active', frozen_at=NULL, activated_at=? WHERE id=?",
                               (timestamp, timeline_id))
            connection.execute('UPDATE companions SET active_timeline_id=? WHERE id=?', (timeline_id, companion['id']))
            # Life resumes now: the time this timeline spent frozen is never simulated.
            connection.execute(
                'INSERT INTO life_cursors (timeline_id, simulated_through, last_reconciled_at, updated_at) '
                'VALUES (?, ?, NULL, ?) ON CONFLICT(timeline_id) DO UPDATE SET '
                'simulated_through=MAX(simulated_through, excluded.simulated_through), updated_at=excluded.updated_at',
                (timeline_id, timestamp, timestamp))
            connection.execute('UPDATE agenda_cursors SET through=MAX(through, ?) WHERE timeline_id=?',
                               (timestamp, timeline_id))
            connection.execute('UPDATE workspace_settings SET permission_revision=permission_revision+1, '
                               'memory_revision=memory_revision+1, updated_at=? WHERE id=1', (timestamp,))
    result = listing(database)
    return {**result, 'stopped_reply_ids': stopped}


def freeze(connection, timeline_id, timestamp) -> list[str]:
    connection.execute("UPDATE timelines SET status='frozen', frozen_at=? WHERE id=?", (timestamp, timeline_id))
    connection.execute("UPDATE life_events SET status='rejected', rejection=?, decided_at=? "
                       "WHERE timeline_id=? AND status='proposed'", (FROZEN_EVENT, timestamp, timeline_id))
    connection.execute("UPDATE life_runs SET status='failed', error=?, finished_at=?, lease_until=NULL "
                       "WHERE timeline_id=? AND status IN ('planned','running','interrupted')",
                       (FROZEN_RUN, timestamp, timeline_id))
    # Images not started yet are cancelled; one already being made finishes on the frozen post only.
    for job in many(connection, "SELECT id, post_id FROM image_jobs WHERE timeline_id=? AND status='queued'",
                    (timeline_id,)):
        connection.execute("UPDATE image_jobs SET status='cancelled', error=?, error_code='cancelled', finished_at=? "
                           'WHERE id=?', (FROZEN_IMAGE, timestamp, job['id']))
        feed.apply_image(connection, job['post_id'], job['id'], 'cancelled', timestamp, error=FROZEN_IMAGE)
    # Hidden upcoming entries are rebuilt from the moment the timeline is chosen again.
    connection.execute("DELETE FROM life_agenda WHERE timeline_id=? AND status='upcoming'", (timeline_id,))
    connection.execute('UPDATE agenda_cursors SET through=MIN(through, ?) WHERE timeline_id=?', (timestamp, timeline_id))
    return [row['id'] for row in many(connection, "SELECT id FROM messages WHERE timeline_id=? AND status='streaming'",
                                      (timeline_id,))]
