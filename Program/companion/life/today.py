"""The Today view: the companion's routine, plans and what changed since the last visit (PRD Today, C5)."""
from companion import moods as feelings
from companion.characters import require_current
from companion.clock import parse, stamp, zone
from companion.database import many, optional, settings
from companion.events import view as event_view
from companion.life import agenda, circle, feed, mood, occasions, routine, simulation, thoughts
from companion.memory.records import OPEN_PLANS, eligible

AVAILABILITY = {'sleep': 'asleep', 'work': 'working', 'study': 'working', 'errand': 'out', 'social': 'out'}
RECENT_LIMIT = 10


def availability(slot) -> dict:
    """Routine availability explains a slow or short reply; it never locks the conversation (C5)."""
    if slot is None:
        return {'state': 'free', 'label': '', 'until': None}
    return {'state': AVAILABILITY.get(slot.block.kind, 'free'), 'label': slot.block.label,
            'until': stamp(slot.ends_at)}


def last_seen(connection, timeline_id) -> str | None:
    row = optional(connection, 'SELECT last_seen_at FROM visits WHERE timeline_id=?', (timeline_id,))
    return row['last_seen_at'] if row else None


def changes(connection, timeline_id, since) -> list[dict]:
    """Events committed since the last visit, or the latest few on a first visit."""
    if since:
        rows = many(connection, "SELECT * FROM life_events WHERE timeline_id=? AND status='committed' "
                    'AND decided_at>? ORDER BY starts_at DESC LIMIT ?', (timeline_id, since, RECENT_LIMIT))
    else:
        rows = many(connection, "SELECT * FROM life_events WHERE timeline_id=? AND status='committed' "
                    'ORDER BY starts_at DESC LIMIT ?', (timeline_id, RECENT_LIMIT))
    return [event_view(row) for row in rows]


def plans(connection, companion, now) -> dict:
    timeline_id = companion['active_timeline_id']
    user_plans = [{'id': memory['id'], 'subject': memory['subject'], 'value': memory['value'],
                   'status': memory['plan_status'], 'applies_from': memory['applies_from'],
                   'applies_until': memory['applies_until']}
                  for memory in eligible(connection, companion, timeline_id, stamp(now))
                  if memory['layer'] == 'plan' and memory['plan_status'] in OPEN_PLANS]
    companion_plans = many(connection, "SELECT * FROM life_events WHERE timeline_id=? AND status='committed' "
                           "AND kind='plan' AND ends_at>=? ORDER BY starts_at", (timeline_id, stamp(now)))
    # Open threads whose outcome is not committed yet.
    threads = many(connection, "SELECT * FROM life_events WHERE timeline_id=? AND status='committed' "
                   "AND kind='thread' AND json_extract(details, '$.state')='open' AND NOT EXISTS (SELECT 1 "
                   "FROM life_events settled WHERE settled.kind='thread' AND settled.status='committed' "
                   "AND json_extract(settled.details, '$.state')='settled' AND json_extract(settled.details, "
                   "'$.thread_key')=json_extract(life_events.details, '$.thread_key')) "
                   'ORDER BY starts_at DESC LIMIT 5', (timeline_id,))
    return {'shared': user_plans, 'companion': [event_view(row) for row in companion_plans],
            'threads': [event_view(row) for row in threads]}


def day(connection, timeline_id, local_date) -> dict:
    """The companion's local day: typical weather, the city's annual events and circle birthdays."""
    found = agenda.day_on(connection, timeline_id, local_date)
    birthdays = [{'id': person['id'], 'name': person['name']} for person in circle.people(connection, timeline_id)
                 if circle.birthday(person['id']) == local_date[5:]]
    return {'date': local_date, **found, 'birthdays': birthdays}


def view(database) -> dict:
    now = database.clock.now()
    with database.connect() as connection:
        companion = require_current(connection)
        timeline_id, version = companion['active_timeline_id'], companion['version']
        workspace, life = settings(connection), simulation.life_settings(connection)
        since = last_seen(connection, timeline_id)
        review = many(connection, "SELECT * FROM life_events WHERE timeline_id=? AND status='proposed' "
                      'ORDER BY starts_at', (timeline_id,))
        latest_run = optional(connection, 'SELECT * FROM life_runs WHERE timeline_id=? ORDER BY created_at DESC '
                              'LIMIT 1', (timeline_id,))
        position = simulation.cursor(connection, timeline_id)
        result = {
            'now': stamp(now), 'last_seen_at': since,
            'user_timezone': workspace['user_timezone'], 'companion_timezone': version['timezone'],
            'companion_local_time': now.astimezone(zone(version['timezone'])).isoformat(timespec='minutes'),
            'paused': workspace['paused_at'] is not None, 'paused_at': workspace['paused_at'],
            'changes': changes(connection, timeline_id, since),
            'review': [event_view(row) for row in review],
            'plans': plans(connection, companion, now),
            'feed_unread': feed.unread(connection, timeline_id),
            'last_run': simulation.run_view(latest_run),
            'simulated_through': position['simulated_through'],
            'clock_behind': now < parse(position['simulated_through']),
            'limits': simulation.settings_view(life),
            # Hidden values: how they feel stays unseen unless the user turns it on (companion/moods.py).
            'mood': mood.active(connection, companion, now) if workspace['show_moods'] else None,
            'feeling': feelings.view(connection, f"companion:{companion['id']}", {feelings.USER: 'you'}, now)
            if workspace['show_moods'] else None,
            'day': day(connection, timeline_id, now.astimezone(zone(version['timezone'])).date().isoformat()),
            'occasions': occasions.occasions(connection, companion, now),
        }
    schedule, default = routine.blocks(version['definition'])
    current, upcoming = routine.current_and_next(schedule, version['timezone'], now)
    result['routine'] = {'default_schedule': default, 'current': current.view() if current else None,
                         'next': upcoming.view() if upcoming else None}
    result['availability'] = availability(current)
    result['mind'] = thoughts.view(database)
    return result


def mark_seen(database) -> dict:
    """Records that the user looked at Today. It never moves backward with the clock."""
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        connection.execute('INSERT INTO visits (timeline_id, last_seen_at) VALUES (?, ?) ON CONFLICT(timeline_id) '
                           'DO UPDATE SET last_seen_at=MAX(last_seen_at, excluded.last_seen_at)',
                           (companion['active_timeline_id'], database.now()))
        return {'last_seen_at': last_seen(connection, companion['active_timeline_id'])}

