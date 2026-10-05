"""The private feed (PRD F1, F2, F4).

A post never carries its own account of an event. It references life events and shows the
current committed revision of each, so a correction updates the post, a pending proposal waits
until it is committed, and a rejected one never appears. A post with nothing committed to show
is left out of the feed and the unread count.

Return batches make one digest post; background batches make one post per event (T5). The
image columns are a hook for a later image job: the text never waits for an image.
"""
from companion.characters import require_current
from companion.database import decode, identifier, many, one, optional
from companion.errors import require

REACTIONS = ('heart', 'laugh', 'wow', 'sad', 'hug')
IMAGE_STATES = ('none', 'queued', 'running', 'completed', 'failed', 'cancelled', 'interrupted')


def current_revision(connection, event_id) -> dict | None:
    """Follow corrections to the event's active version."""
    event = optional(connection, 'SELECT * FROM life_events WHERE id=?', (event_id,))
    while event and event['status'] == 'superseded':
        event = optional(connection, 'SELECT * FROM life_events WHERE supersedes_id=? ORDER BY revision DESC '
                         'LIMIT 1', (event['id'],))
    return event


def event_view(event) -> dict:
    details = decode(event['details'])
    return {'id': event['id'], 'summary': event['summary'], 'caption': details.get('post') or event['summary'],
            'mood': details.get('mood', ''), 'label': details.get('label', ''), 'kind': event['kind'],
            'starts_at': event['starts_at'], 'ends_at': event['ends_at'], 'revision': event['revision']}


def shown_events(connection, post_id) -> list[dict]:
    result = []
    for link in many(connection, 'SELECT event_id FROM feed_post_events WHERE post_id=? ORDER BY position',
                     (post_id,)):
        event = current_revision(connection, link['event_id'])
        if event and event['status'] == 'committed':
            result.append(event_view(event))
    return result


def post_view(connection, post) -> dict | None:
    removed = post['status'] == 'removed'
    shown = [] if removed else shown_events(connection, post['id'])
    if not shown and not removed:
        return None
    return {'id': post['id'], 'kind': post['kind'], 'intro': post['intro'], 'events': shown,
            'status': post['status'], 'read': post['read_at'] is not None, 'read_at': post['read_at'],
            'reaction': post['reaction'], 'occurs_at': post['occurs_at'], 'created_at': post['created_at'],
            'image': {'status': post['image_status'], 'job_id': post['image_job_id'], 'ref': post['image_ref'],
                      'error': post['image_error'], 'updated_at': post['image_updated_at']}}


def create(connection, timeline_id, kind, key, event_ids, occurs_at, timestamp, run_id=None, intro='') -> str:
    existing = optional(connection, 'SELECT id FROM feed_posts WHERE idempotency_key=?', (key,))
    if existing:
        return existing['id']
    post_id = identifier()
    connection.execute('INSERT INTO feed_posts (id, timeline_id, kind, idempotency_key, run_id, intro, occurs_at, '
                       'created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                       (post_id, timeline_id, kind, key, run_id, intro, occurs_at, timestamp))
    connection.executemany('INSERT INTO feed_post_events (post_id, event_id, position) VALUES (?, ?, ?)',
                           [(post_id, event_id, index) for index, event_id in enumerate(event_ids)])
    return post_id


def publish_run(connection, run, results, timestamp):
    """One digest for a return batch, one post per event for a background batch (T5)."""
    event_ids = [result['event_id'] for result in results
                 if result.get('event_id') and result['outcome'] in {'proposed', 'committed'}]
    if not event_ids:
        return
    if run['mode'] == 'return':
        create(connection, run['timeline_id'], 'digest', f"digest:{run['id']}", event_ids, run['window_end'],
               timestamp, run['id'])
        return
    for event_id in event_ids:
        event = one(connection, 'SELECT ends_at FROM life_events WHERE id=?', (event_id,))
        create(connection, run['timeline_id'], 'event', f'event:{event_id}', [event_id], event['ends_at'],
               timestamp, run['id'])


def post_event(database, event_id, intro='') -> dict:
    """An explicit post for a committed event the simulation did not write (F1)."""
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        event = current_revision(connection, event_id)
        require(event is not None, 'This item could not be found.', 404)
        require(event['status'] == 'committed' and event['timeline_id'] == companion['active_timeline_id'],
                'Only a committed event on the active timeline can be posted.', 409)
        post_id = create(connection, event['timeline_id'], 'event', f"event:{event['id']}", [event['id']],
                         event['ends_at'], database.now(), intro=intro)
        return post_view(connection, one(connection, 'SELECT * FROM feed_posts WHERE id=?', (post_id,)))


def visible_posts(connection, timeline_id, include_hidden=False) -> list[dict]:
    statuses = "('visible','hidden')" if include_hidden else "('visible')"
    rows = many(connection, f'SELECT * FROM feed_posts WHERE timeline_id=? AND status IN {statuses} '
                'ORDER BY occurs_at DESC, id DESC', (timeline_id,))
    return [view for view in (post_view(connection, row) for row in rows) if view]


def listing(database, before=None, limit=20, include_hidden=False) -> dict:
    """Newest first; `before` is the `next_before` of the previous page."""
    with database.connect() as connection:
        companion = require_current(connection)
        posts = visible_posts(connection, companion['active_timeline_id'], include_hidden)
        if before:
            occurs_at, _, post_id = before.partition('|')
            posts = [post for post in posts if (post['occurs_at'], post['id']) < (occurs_at, post_id)]
        page = posts[:limit]
        more = len(posts) > limit
        return {'posts': page, 'next_before': f"{page[-1]['occurs_at']}|{page[-1]['id']}" if more else None,
                'unread': unread(connection, companion['active_timeline_id'])}


def unread(connection, timeline_id) -> int:
    return sum(1 for post in visible_posts(connection, timeline_id) if not post['read'])


def get(database, post_id) -> dict:
    with database.connect() as connection:
        view = post_view(connection, one(connection, 'SELECT * FROM feed_posts WHERE id=?', (post_id,)))
        require(view is not None, 'This item could not be found.', 404)
        return view


def mark_read(database, post_ids=None) -> dict:
    """Read state records when the user saw a post (observation time, T1)."""
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        timestamp, timeline_id = database.now(), companion['active_timeline_id']
        if post_ids is None:
            connection.execute('UPDATE feed_posts SET read_at=? WHERE timeline_id=? AND read_at IS NULL',
                               (timestamp, timeline_id))
        else:
            connection.executemany('UPDATE feed_posts SET read_at=? WHERE id=? AND timeline_id=? AND read_at IS NULL',
                                   [(timestamp, post_id, timeline_id) for post_id in post_ids])
        return {'unread': unread(connection, timeline_id)}


def set_status(database, post_id, status) -> dict:
    """Hide is reversible. Remove clears the post's own text for good; its events stay in the
    companion's life and the conversation, since the post never owned them."""
    with database.connect(write=True) as connection:
        post = one(connection, 'SELECT * FROM feed_posts WHERE id=?', (post_id,))
        require(post['status'] != 'removed', 'This post was removed.', 409)
        if status == 'removed':
            connection.execute("UPDATE feed_posts SET status='removed', intro='', reaction=NULL, image_ref=NULL, "
                               'removed_at=? WHERE id=?', (database.now(), post_id))
            connection.execute('DELETE FROM feed_post_events WHERE post_id=?', (post_id,))
        else:
            connection.execute('UPDATE feed_posts SET status=? WHERE id=?', (status, post_id))
        return post_view(connection, one(connection, 'SELECT * FROM feed_posts WHERE id=?', (post_id,)))


def react(database, post_id, reaction) -> dict:
    require(reaction is None or reaction in REACTIONS, 'Unknown reaction.', 422)
    with database.connect(write=True) as connection:
        post = one(connection, 'SELECT * FROM feed_posts WHERE id=?', (post_id,))
        require(post['status'] != 'removed', 'This post was removed.', 409)
        connection.execute('UPDATE feed_posts SET reaction=?, read_at=COALESCE(read_at, ?) WHERE id=?',
                           (reaction, database.now(), post_id))
        return post_view(connection, one(connection, 'SELECT * FROM feed_posts WHERE id=?', (post_id,)))


def link_message(database, message_id, post_id):
    with database.connect(write=True) as connection:
        post = one(connection, 'SELECT * FROM feed_posts WHERE id=?', (post_id,))
        require(post['status'] != 'removed', 'This post was removed.', 409)
        connection.execute('INSERT OR IGNORE INTO message_post_links (message_id, post_id) VALUES (?, ?)',
                           (message_id, post_id))
        connection.execute('UPDATE feed_posts SET read_at=COALESCE(read_at, ?) WHERE id=?', (database.now(), post_id))


def linked_post(connection, message_id) -> dict | None:
    link = optional(connection, 'SELECT post_id FROM message_post_links WHERE message_id=?', (message_id,))
    if link is None:
        return None
    return post_view(connection, one(connection, 'SELECT * FROM feed_posts WHERE id=?', (link['post_id'],)))


def export(database) -> dict:
    """Everything the user can see in the feed, hidden posts included (F2)."""
    with database.connect() as connection:
        companion = require_current(connection)
        posts = visible_posts(connection, companion['active_timeline_id'], include_hidden=True)
        return {'format': 'prospero-companion-feed', 'version': 1, 'exported_at': database.now(),
                'companion': companion['version']['name'], 'posts': list(reversed(posts))}


def set_image(database, post_id, job_id, status, ref=None, error=None) -> dict:
    """For the image job: a result only lands if it belongs to the post's current job, so a late
    result cannot overwrite a newer one (F4). Queuing a new job replaces the current job id."""
    require(status in IMAGE_STATES, 'Unknown image state.', 422)
    with database.connect(write=True) as connection:
        post = one(connection, 'SELECT * FROM feed_posts WHERE id=?', (post_id,))
        require(post['status'] != 'removed', 'This post was removed.', 409)
        if status != 'queued':
            require(post['image_job_id'] == job_id, 'This image job is no longer current for the post.', 409)
        connection.execute('UPDATE feed_posts SET image_status=?, image_job_id=?, image_ref=COALESCE(?, image_ref), '
                           'image_error=?, image_updated_at=? WHERE id=?',
                           (status, job_id, ref, error, database.now(), post_id))
        return post_view(connection, one(connection, 'SELECT * FROM feed_posts WHERE id=?', (post_id,)))
