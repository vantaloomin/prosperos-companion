"""Desktop notifications (PRD "Compute and job control", C6, M4).

Notifications are off by default. A background batch queues one notification per new post; the
open interface asks for the next one to show as a Windows desktop notification. Delivery honours
quiet hours, a daily cap and a minimum gap, and when more than one is waiting they collapse into a
single digest, never a burst. Turning notifications off, or revoking background activity, cancels
what is queued. A character's absence traits may give the message text their voice, but never
change when or how often a notification is shown, and settings and prompts stay neutral.
"""
from datetime import datetime, timedelta

from companion.characters import current
from companion.clock import parse, stamp, zone
from companion.database import identifier, many, one, optional, settings
from companion.errors import require
from companion.life import feed
from companion.life.mood import ABSENCE_HOURS, last_presence
from companion.traits import NAMES, absence_traits, strongest

PREVIEWS = ('full', 'name', 'private')
# A queued notification whose post never became visible (an event still waiting for review, then
# rejected) is dropped after this long, so it cannot surface days later.
STALE = timedelta(hours=48)
APP_TITLE = 'Prospero Companion'
CAPTION_LIMIT = 160
# In-character openings for absence traits, by intensity. Wording only; never timing.
VOICE = {'mild': 'Thinking of you.', 'moderate': "You've been quiet lately.", 'strong': 'Did you forget about me?'}


def notification_settings(connection) -> dict:
    return one(connection, 'SELECT * FROM notification_settings WHERE id=1')


def view(row: dict) -> dict:
    return {**row, 'enabled': bool(row['enabled'])}


def read(database) -> dict:
    with database.connect() as connection:
        return {**view(notification_settings(connection)), 'queued': queued_count(connection)}


def update(database, body) -> dict:
    changes = body.model_dump(exclude_none=True)
    for key in ('quiet_start', 'quiet_end'):
        if key in changes:
            changes[key] = clock_time(changes[key])
    with database.connect(write=True) as connection:
        row = notification_settings(connection)
        changed = {key: int(value) if isinstance(value, bool) else value
                   for key, value in changes.items() if row[key] != value}
        if changed:
            columns = ', '.join(f'{key}=?' for key in changed)
            connection.execute(f'UPDATE notification_settings SET {columns}, updated_at=? WHERE id=1',
                               (*changed.values(), database.now()))
        if changed.get('enabled') == 0:
            cancel_queued(connection, database.now(), 'Notifications were turned off.')
        return {**view(notification_settings(connection)), 'queued': queued_count(connection)}


def clock_time(value: str) -> str:
    hours, _, minutes = value.partition(':')
    require(hours.isdigit() and minutes.isdigit() and int(hours) < 24 and int(minutes) < 60,
            'Use a time such as 22:00.', 422)
    return f'{int(hours):02d}:{int(minutes):02d}'


def queued_count(connection) -> int:
    return one(connection, "SELECT COUNT(*) AS n FROM notifications WHERE status='queued'")['n']


def cancel_queued(connection, timestamp, reason):
    connection.execute("UPDATE notifications SET status='cancelled', reason=?, settled_at=? WHERE status='queued'",
                       (reason, timestamp))


def enqueue_posts(connection, post_ids, timestamp):
    """Called as a background batch publishes. Nothing is queued while notifications are off."""
    if not notification_settings(connection)['enabled']:
        return
    for post_id in post_ids:
        connection.execute("INSERT OR IGNORE INTO notifications (id, post_id, status, created_at) "
                           "VALUES (?, ?, 'queued', ?)", (identifier(), post_id, timestamp))


def in_quiet_hours(local: datetime, start: str, end: str) -> bool:
    """Quiet hours may cross midnight (22:00 to 08:00). Equal start and end means none."""
    now = local.strftime('%H:%M')
    if start == end:
        return False
    return start <= now < end if start < end else now >= start or now < end


def held(connection, config, workspace, now) -> str | None:
    """Why nothing may be shown right now, or None."""
    if workspace['paused_at'] is not None:
        return 'paused'
    if in_quiet_hours(now.astimezone(zone(workspace['user_timezone'])), config['quiet_start'], config['quiet_end']):
        return 'quiet_hours'
    shown = many(connection, "SELECT delivered_at FROM notification_deliveries WHERE delivered_at>? "
                 'ORDER BY delivered_at DESC', (stamp(now - timedelta(days=1)),))
    if len(shown) >= config['daily_cap']:
        return 'daily_cap'
    if shown and now - parse(shown[0]['delivered_at']) < timedelta(minutes=config['min_gap_minutes']):
        return 'min_gap'
    return None


def ready_posts(connection, companion, now) -> list[tuple[dict, dict]]:
    """Queued notifications whose post is visible and unread on the active timeline. The rest are
    settled: read or removed posts and other timelines are dropped, and so is anything stale."""
    timestamp, ready = stamp(now), []
    for item in many(connection, "SELECT * FROM notifications WHERE status='queued' ORDER BY created_at"):
        post = optional(connection, 'SELECT * FROM feed_posts WHERE id=?', (item['post_id'],))
        shown = feed.post_view(connection, post) if post and post['timeline_id'] == companion[
            'active_timeline_id'] and post['status'] == 'visible' else None
        if shown and not shown['read']:
            ready.append((item, shown))
        elif shown or post is None or post['status'] != 'visible' or now - parse(item['created_at']) > STALE \
                or post['timeline_id'] != companion['active_timeline_id']:
            connection.execute("UPDATE notifications SET status='dropped', reason=?, settled_at=? WHERE id=?",
                               ('Already seen or no longer shown.', timestamp, item['id']))
    return ready


def voice(connection, companion, now) -> str | None:
    """An in-character opening when the character has an absence trait and the user has been away."""
    traits = absence_traits(companion['version']['definition'])
    if not traits:
        return None
    since = last_presence(connection, companion['active_timeline_id'])
    if since is None or now - parse(since) < timedelta(hours=ABSENCE_HOURS):
        return None
    return VOICE[NAMES[strongest(traits)]]


def caption(post: dict) -> str:
    text = post['intro'] or post['events'][0]['caption']
    return text if len(text) <= CAPTION_LIMIT else text[:CAPTION_LIMIT - 1].rstrip() + '…'


def message(config, companion, posts, voiced) -> dict:
    """Title and body for one post or a digest, within the chosen preview privacy."""
    name, count = companion['version']['name'], len(posts)
    if config['preview'] == 'private':
        return {'title': APP_TITLE, 'body': 'Something new is waiting.' if count == 1
                else f'{count} new things are waiting.'}
    if config['preview'] == 'name' or count > 1:
        body = f'{name} shared something new.' if count == 1 else f'{name} shared {count} new moments.'
        if config['preview'] == 'full' and count > 1:
            body = f'{body} Latest: {caption(posts[-1])}'
    else:
        body = caption(posts[0])
    return {'title': name, 'body': f'{voiced} {body}' if voiced else body}


def deliver(database, focused=False) -> dict:
    """The next notification to show, if any. While the app has focus nothing is shown and the queue
    waits; posts read meanwhile are dropped. Several waiting posts become one digest."""
    now = database.clock.now()
    with database.connect(write=True) as connection:
        config = notification_settings(connection)
        companion = current(connection)
        if not config['enabled'] or companion is None:
            return {'notification': None, 'held': 'off'}
        ready = ready_posts(connection, companion, now)
        if not ready:
            return {'notification': None, 'held': None}
        reason = 'focused' if focused else held(connection, config, settings(connection), now)
        if reason:
            return {'notification': None, 'held': reason}
        posts = [post for _item, post in ready]
        delivery_id, timestamp = identifier(), stamp(now)
        kind = 'post' if len(ready) == 1 else 'digest'
        shown = message(config, companion, posts, voice(connection, companion, now))
        connection.execute('INSERT INTO notification_deliveries (id, kind, post_count, delivered_at) '
                           'VALUES (?, ?, ?, ?)', (delivery_id, kind, len(ready), timestamp))
        connection.executemany("UPDATE notifications SET status=?, delivery_id=?, settled_at=? WHERE id=?",
                               [('delivered' if kind == 'post' else 'digested', delivery_id, timestamp, item['id'])
                                for item, _post in ready])
        return {'notification': {'id': delivery_id, 'kind': kind, 'post_ids': [post['id'] for post in posts],
                                 **shown}, 'held': None}
