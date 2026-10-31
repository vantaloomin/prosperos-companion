"""The private feed (PRD F1, F2, F4).

A post never carries its own account of an event. It references life events and shows the
current committed revision of each, so a correction updates the post, a pending proposal waits
until it is committed, and a rejected one never appears. A post with nothing committed to show
is left out of the feed and the unread count.

Every batch makes one post per event, stamped when that event ended, so a catch-up after days away
reads as the separate moments they were rather than one card with one time. Older return batches
made one 'digest' post; those stay as they are. The image columns are a hook for a later image
job: the text never waits for an image.
"""
from companion.characters import definition_for_timeline, require_current
from companion.clock import parse, zone
from companion.database import decode, identifier, many, one, optional
from companion.errors import require
from companion.life import composer, loss, post_comments, social, user_posts
from companion.world import decades, looks

REACTIONS = ('heart', 'laugh', 'wow', 'sad', 'hug')
# A photo sent in chat waits on a post keyed to the event its slot will become (companion/images/photos.py).
PHOTO_KEY = 'photo:'
# Whose posts each feed filter keeps; 'all' keeps everyone's.
SOURCES = {'companion': ('companion',), 'circle': ('person',), 'mine': (user_posts.USER,)}
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


def image_outdated(connection, post, shown) -> bool:
    """True when the shown image was made from an event version that has since been corrected or
    withdrawn, so the post can say the picture shows the earlier account (F1, M3). Wording is
    compared rather than identities, which differ on a copied timeline."""
    if not post['image_ref']:
        return False
    job = optional(connection, 'SELECT inputs FROM image_jobs WHERE id=?', (post['image_ref'],))
    if job is None:
        return False
    drawn = [(event['summary'], event['caption']) for event in decode(job['inputs'])['events']]
    return drawn != [(event['summary'], event['caption']) for event in shown][:len(drawn)]


def said_events(connection, post, shown: list[dict]) -> list[dict]:
    """The events with the companion's own pronouns (companion/life/composer.said); the image check compares the
    words as written. `mine` is the caption and summary as the companion says them on their own post ("I worked
    late"); summary and caption stay as written for chat."""
    definition = definition_for_timeline(connection, post['timeline_id']) if shown else {}
    return [{**event, 'summary': composer.said(event['summary'], definition), 'mine': mine(event, definition)}
            for event in shown]


def mine(event: dict, definition: dict) -> dict:
    line = composer.mine(event['summary'], definition.get('name', ''), definition and looks.pronouns_of(definition))
    return {'caption': line if event['caption'] == event['summary'] else event['caption'], 'summary': line}


def post_view(connection, post) -> dict | None:
    removed = post['status'] == 'removed'
    shown = [] if removed else shown_events(connection, post['id'])
    if not shown and not removed:
        return None
    return {'id': post['id'], 'kind': post['kind'], 'source': 'life', 'intro': post['intro'],
            'events': said_events(connection, post, shown),
            'status': post['status'], 'read': post['read_at'] is not None, 'read_at': post['read_at'],
            'reaction': post['reaction'], 'occurs_at': post['occurs_at'], 'created_at': post['created_at'],
            'image': {'status': post['image_status'], 'job_id': post['image_job_id'], 'ref': post['image_ref'],
                      'error': post['image_error'], 'updated_at': post['image_updated_at'],
                      'outdated': image_outdated(connection, post, shown)}}


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


def publish_run(connection, run, results, timestamp) -> list[str]:
    """One post per event, at the time it ended, for a return (catch-up) batch and a background batch
    alike. An event photographed in chat while it was happening joins its photo's post instead.
    Returns the background batch's posts, which may be announced as notifications; a catch-up
    batch announces nothing, since the user is already back."""
    event_ids = [result['event_id'] for result in results
                 if result.get('event_id') and result['outcome'] in {'proposed', 'committed'}]
    posts = [photo_post(connection, event_id) or event_post(connection, run, event_id, timestamp)
             for event_id in event_ids]
    return posts if run['mode'] == 'background' else []


def event_post(connection, run, event_id, timestamp) -> str:
    event = one(connection, 'SELECT ends_at FROM life_events WHERE id=?', (event_id,))
    return create(connection, run['timeline_id'], 'event', f'event:{event_id}', [event_id], event['ends_at'],
                  timestamp, run['id'])


def photographed(connection, event_key) -> bool:
    """Whether a photo was sent in chat of the slot that will become the event with this key."""
    return optional(connection, "SELECT id FROM feed_posts WHERE idempotency_key=? AND status!='removed'",
                    (PHOTO_KEY + event_key,)) is not None


def photo_post(connection, event_id) -> str | None:
    """The post a chat photo of this event's slot waits on, with the event joined to it, so the feed
    shows the same picture the chat did and the event is told once."""
    event = optional(connection, 'SELECT idempotency_key FROM life_events WHERE id=?', (event_id,))
    post = event and optional(connection, "SELECT id FROM feed_posts WHERE idempotency_key=? AND status!='removed'",
                              (PHOTO_KEY + event['idempotency_key'],))
    if not post:
        return None
    connection.execute('INSERT OR IGNORE INTO feed_post_events (post_id, event_id, position) VALUES (?, ?, 0)',
                       (post['id'], event_id))
    return post['id']


def post_event(database, event_id, intro='') -> dict:
    """An explicit post for a committed event the simulation did not write (F1)."""
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        event = current_revision(connection, event_id)
        require(event is not None, 'This item could not be found.', 404)
        require(event['status'] == 'committed' and event['timeline_id'] == companion['active_timeline_id'],
                'Only a committed event on the active timeline can be posted.', 409)
        post_id = photo_post(connection, event['id']) or create(
            connection, event['timeline_id'], 'event', f"event:{event['id']}", [event['id']], event['ends_at'],
            database.now(), intro=intro)
        return post_view(connection, one(connection, 'SELECT * FROM feed_posts WHERE id=?', (post_id,)))


def visible_posts(connection, timeline_id, include_hidden=False) -> list[dict]:
    statuses = "('visible','hidden')" if include_hidden else "('visible')"
    rows = many(connection, f'SELECT * FROM feed_posts WHERE timeline_id=? AND status IN {statuses} '
                'ORDER BY occurs_at DESC, id DESC', (timeline_id,))
    mourning = grief_test(connection, timeline_id)
    # A post the user already read or reacted to stays: holding back never takes away what they saw (a workspace
    # from before v0.15 had these posts on show).
    return [view for view in (post_view(connection, row) for row in rows
                              if row['read_at'] or row['reaction'] or not mourning(row['occurs_at'])) if view]


def grief_test(connection, timeline_id):
    """A test for whether a life post falls on a day grief is raw or heavy (companion/life/loss.py): those posts are
    held back, so the feed shows only the quiet status (companion/life/social.py) those days."""
    losses = loss.rows(connection, timeline_id) if loss.ACTIVE else []
    if not losses:
        return lambda _occurs_at: False
    row = optional(connection, 'SELECT v.timezone FROM timelines t JOIN companions c ON c.id=t.companion_id '
                   'JOIN character_versions v ON v.id=c.active_version_id WHERE t.id=?', (timeline_id,))
    timezone = zone(row['timezone'] if row else 'UTC')

    def mourning(occurs_at: str) -> bool:
        day = parse(occurs_at).astimezone(timezone).date()
        return any(loss.stage(found, day) in ('raw', 'heavy') for found in losses)
    return mourning


def everything(connection, companion, now: str, include_hidden=False, source='all') -> list[dict]:
    """Life posts, social posts (companion/life/social.py) and the user's own (companion/life/user_posts.py)
    together, newest first, with likes and comments. `source` keeps only the companion's own posts, the circle's
    or the user's. Likes and
    comments are worked out over every post, so a filter or a hidden post never changes them."""
    timeline_id, name = companion['active_timeline_id'], companion['version']['name']
    people = social.active_people(connection, timeline_id)
    posts = [{**post, 'author': social.author_view(social.COMPANION, people, name),
              '_basis': (social.COMPANION, {'mood': (post['events'] or [{}])[0].get('mood', '')})}
             for post in visible_posts(connection, timeline_id, include_hidden=True)]
    posts += social.visible(connection, companion, include_hidden=True)
    mine = user_posts.visible(connection, now, include_hidden=True)
    known = tuple(social.known_audience(connection, companion, parse(now)))
    everyone = tuple(user_posts.crowd(connection, parse(now))) if mine else ()
    social.add_audiences(posts + mine, now, people, name, known, everyone, social.trolls(connection))
    authors = SOURCES.get(source)
    posts = [post for post in posts + mine if (include_hidden or post['status'] == 'visible')
             and (authors is None or post['author']['kind'] in authors)]
    post_comments.attach(connection, posts, now)
    return sorted(of_the_year(posts), key=lambda post: (post['occurs_at'], post['id']), reverse=True)


def of_the_year(posts: list[dict]) -> list[dict]:
    """In a world from before emoji (decades.without_emoji), the posts and comments the app wrote without them."""
    if (decades.world_year() or decades.EMOJI_FROM) >= decades.EMOJI_FROM:
        return posts
    for post in posts:
        if isinstance(post.get('text'), str) and (post.get('author') or {}).get('kind') != user_posts.USER:
            post['text'] = decades.without_emoji(post['text'])
        for comment in (post.get('audience') or {}).get('comments') or ():
            comment['text'] = decades.without_emoji(comment['text'])
    return posts


def shown(connection, post_id, now: str) -> dict | None:
    """One post as the feed shows it, author, likes and comments included. A removed post is shown
    bare, with no likes or comments."""
    companion = require_current(connection)
    found = next((post for post in everything(connection, companion, now, include_hidden=True)
                  if post['id'] == post_id), None)
    if found:
        return found
    if row := social.find(connection, post_id):
        post = social.view(row, social.active_people(connection, row['timeline_id']), companion['version']['name'])
    elif row := user_posts.find(connection, post_id):
        post = user_posts.view(row)
    else:
        post = post_view(connection, one(connection, 'SELECT * FROM feed_posts WHERE id=?', (post_id,)))
        post = post and {**post, 'author': social.author_view(social.COMPANION, {}, companion['version']['name'])}
    if post:
        post.pop('_basis', None)
        post['audience'] = {'likes': [], 'comments': []}
        post['thread'] = {'comments': [], 'waiting': False}
    return post


def listing(database, before=None, limit=20, include_hidden=False, source='all') -> dict:
    """Newest first; `before` is the `next_before` of the previous page."""
    with database.connect() as connection:
        companion = require_current(connection)
        posts = everything(connection, companion, database.now(), include_hidden, source)
        if before:
            occurs_at, _, post_id = before.partition('|')
            posts = [post for post in posts if (post['occurs_at'], post['id']) < (occurs_at, post_id)]
        page = posts[:limit]
        more = len(posts) > limit
        return {'posts': page, 'next_before': f"{page[-1]['occurs_at']}|{page[-1]['id']}" if more else None,
                'unread': unread(connection, companion['active_timeline_id'])}


def unread(connection, timeline_id) -> int:
    return sum(1 for post in visible_posts(connection, timeline_id) if not post['read']) + \
        social.unread(connection, timeline_id)


def get(database, post_id) -> dict:
    with database.connect() as connection:
        view = shown(connection, post_id, database.now())
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
        social.mark_read(connection, timeline_id, timestamp, post_ids)
        return {'unread': unread(connection, timeline_id)}


def set_status(database, post_id, status) -> dict:
    """Hide is reversible. Remove clears the post's own text for good; its events stay in the
    companion's life and the conversation, since the post never owned them. Its comments go with it."""
    with database.connect(write=True) as connection:
        if status == 'removed':
            post_comments.forget(connection, post_id)
        if row := social.find(connection, post_id):
            social.set_status(connection, row, status, database.now())
            return shown(connection, post_id, database.now())
        if row := user_posts.find(connection, post_id):
            user_posts.set_status(connection, row, status, database.now())
            return shown(connection, post_id, database.now())
        post = one(connection, 'SELECT * FROM feed_posts WHERE id=?', (post_id,))
        require(post['status'] != 'removed', 'This post was removed.', 409)
        if status == 'removed':
            connection.execute("UPDATE feed_posts SET status='removed', intro='', reaction=NULL, image_ref=NULL, "
                               'removed_at=? WHERE id=?', (database.now(), post_id))
            connection.execute('DELETE FROM feed_post_events WHERE post_id=?', (post_id,))
        else:
            connection.execute('UPDATE feed_posts SET status=? WHERE id=?', (status, post_id))
        return shown(connection, post_id, database.now())


def react(database, post_id, reaction) -> dict:
    require(reaction is None or reaction in REACTIONS, 'Unknown reaction.', 422)
    with database.connect(write=True) as connection:
        if row := social.find(connection, post_id):
            social.react(connection, row, reaction, database.now())
            return shown(connection, post_id, database.now())
        require(user_posts.find(connection, post_id) is None, 'That is your own post.', 409)
        post = one(connection, 'SELECT * FROM feed_posts WHERE id=?', (post_id,))
        require(post['status'] != 'removed', 'This post was removed.', 409)
        connection.execute('UPDATE feed_posts SET reaction=?, read_at=COALESCE(read_at, ?) WHERE id=?',
                           (reaction, database.now(), post_id))
        return shown(connection, post_id, database.now())


def link_message(database, message_id, post_id):
    with database.connect(write=True) as connection:
        if row := social.find(connection, post_id):
            social.link_message(connection, row, message_id, database.now())
            return
        require(user_posts.find(connection, post_id) is None, 'That is your own post.', 409)
        post = one(connection, 'SELECT * FROM feed_posts WHERE id=?', (post_id,))
        require(post['status'] != 'removed', 'This post was removed.', 409)
        connection.execute('INSERT OR IGNORE INTO message_post_links (message_id, post_id) VALUES (?, ?)',
                           (message_id, post_id))
        connection.execute('UPDATE feed_posts SET read_at=COALESCE(read_at, ?) WHERE id=?', (database.now(), post_id))


def linked_post(connection, message_id) -> dict | None:
    link = optional(connection, 'SELECT post_id FROM message_post_links WHERE message_id=?', (message_id,))
    if link is None:
        return social.linked(connection, message_id)
    return post_view(connection, one(connection, 'SELECT * FROM feed_posts WHERE id=?', (link['post_id'],)))


def export(database) -> dict:
    """Everything the user can see in the feed, hidden posts included (F2)."""
    with database.connect() as connection:
        companion = require_current(connection)
        posts = everything(connection, companion, database.now(), include_hidden=True)
        return {'format': 'prospero-companion-feed', 'version': 2, 'exported_at': database.now(),
                'companion': companion['version']['name'], 'posts': list(reversed(posts))}


def set_image(database, post_id, job_id, status, ref=None, error=None) -> dict:
    """For the image job: a result only lands if it belongs to the post's current job, so a late
    result cannot overwrite a newer one (F4). Queuing a new job replaces the current job id."""
    require(status in IMAGE_STATES, 'Unknown image state.', 422)
    with database.connect(write=True) as connection:
        post = one(connection, 'SELECT * FROM feed_posts WHERE id=?', (post_id,))
        require(post['status'] != 'removed', 'This post was removed.', 409)
        applied = apply_image(connection, post_id, job_id, status, database.now(), ref, error,
                              replace=status == 'queued')
        require(applied, 'This image job is no longer current for the post.', 409)
        return post_view(connection, one(connection, 'SELECT * FROM feed_posts WHERE id=?', (post_id,)))


def apply_image(connection, post_id, job_id, status, timestamp, ref=None, error=None, replace=False) -> bool:
    """Record a job's state on its post inside the caller's transaction. Only the post's current
    job may change it unless `replace` makes this job current. Returns whether it applied."""
    post = one(connection, 'SELECT status, image_job_id FROM feed_posts WHERE id=?', (post_id,))
    if post['status'] == 'removed' or (not replace and post['image_job_id'] != job_id):
        return False
    connection.execute('UPDATE feed_posts SET image_status=?, image_job_id=?, image_ref=COALESCE(?, image_ref), '
                       'image_error=?, image_updated_at=? WHERE id=?',
                       (status, job_id, ref, error, timestamp, post_id))
    return True
