"""Precomputed schedules for the companion and their circle (PRD T4, T8, T9).

Each subject's routine is expanded a rolling week ahead and composed without a model, seeded by
the slot, so filling in a long absence at once and advancing a few slots at a time on a running
server write the same entries. Upcoming entries stay hidden; when their slot ends they become
`happened`, or `skipped` when a pause covers them. An entry records the character version or
person revision it was built from, and upcoming entries built from an older one are rebuilt.

For the companion, the agenda is scaffolding: what they did becomes part of their account only
through reviewed life events, which the capped batches (T5) draw from these entries. Circle
members' happened entries are their visible diary.
"""
from datetime import timedelta

from companion import self_facts
from companion.clock import parse, stamp
from companion.database import decode, encode, identifier, many, optional
from companion.life import body, circle, composer, recommendations, routine, storylines
from companion.workspace import overlapping_pause
from companion.world import generators

HORIZON = timedelta(days=7)
BACKFILL = timedelta(days=30)
COMPANION = 'companion'
BUSY = {'work', 'study', 'sleep'}
WORKING = {'work', 'study'}


def subjects(connection, companion, world, now) -> list[tuple[str, dict, str]]:
    """(subject, definition, basis) with the circle first, so the companion's entries can name a
    circle member who is free."""
    version = companion['version']
    definition = version['definition']
    result = []
    for person in circle.ensure(connection, companion, world, now):
        if not decode(person['schedule']):
            continue  # Lives out of town: no routine here.
        result.append((person['id'], {'name': person['name'], 'schedule': decode(person['schedule']),
                                      'home_city': definition.get('home_city', ''),
                                      'location': definition.get('location', ''),
                                      'near': decode(person['details']).get('neighborhood', ''),
                                      'haunts': decode(person['details']).get('haunts', [])},
                       f"{person['id']}:{person['revision']}"))
    # What the companion has said they like or dislike leans their plans too (companion/self_facts.py).
    result.append((COMPANION, {**definition, 'self_tastes': self_facts.tastes(connection, companion['active_timeline_id'])},
                   version['id']))
    return result


def seed_for(timeline_id, subject, slot_key) -> str:
    # The companion's seed is its event key, so a slot composed here or by the simulation agrees.
    if subject == COMPANION:
        return f'life:{timeline_id}:{slot_key}'
    return f'agenda:{timeline_id}:{subject}:{slot_key}'


def extend(connection, companion, world, now) -> dict:
    """Bring every subject's agenda up to a week ahead and settle what has ended. Cheap: no model."""
    timeline_id, timezone = companion['active_timeline_id'], companion['version']['timezone']
    found = subjects(connection, companion, world, now)
    active = [subject for subject, _definition, _basis in found]
    # Removed people's upcoming entries go; what already happened stays.
    marks = ','.join('?' * len(active))
    connection.execute(f"DELETE FROM life_agenda WHERE timeline_id=? AND status='upcoming' AND subject NOT IN "
                       f'({marks})', (timeline_id, *active))
    written = 0
    for subject, definition, basis in found:
        written += extend_subject(connection, timeline_id, timezone, subject, definition, basis, world, now)
    settled = settle(connection, timeline_id, now)
    started = storylines.advance(connection, companion, now)
    return {'written': written, 'settled': settled, 'storylines': started}


def extend_subject(connection, timeline_id, timezone, subject, definition, basis, world, now) -> int:
    stale = connection.execute("DELETE FROM life_agenda WHERE timeline_id=? AND subject=? AND status='upcoming' "
                               'AND basis!=?', (timeline_id, subject, basis)).rowcount
    cursor = optional(connection, 'SELECT through FROM agenda_cursors WHERE timeline_id=? AND subject=?',
                      (timeline_id, subject))
    # A timeline's days begin when it last became active: nothing is filled in for time it spent
    # frozen or before a fork was chosen (C4).
    created = optional(connection, 'SELECT COALESCE(activated_at, created_at) AS since FROM timelines WHERE id=?',
                       (timeline_id,))
    through = parse(cursor['through']) if cursor else parse(created['since'])
    if stale:
        # Rebuild from now: the past is already settled under the old basis.
        through = min(through, now)
    start, end = max(through, now - BACKFILL), now + HORIZON
    if start >= end:
        return 0
    schedule, _default = routine.blocks(definition)
    recent = recent_activities(connection, timeline_id, subject, stamp(start))
    days_off = public_holidays(world, definition, start, end)
    days = {}
    written = 0
    for slot in routine.slots(schedule, timezone, start, end):
        if optional(connection, 'SELECT id FROM life_agenda WHERE timeline_id=? AND subject=? AND slot_key=?',
                    (timeline_id, subject, slot.key)):
            continue
        local_date = slot.local_date.isoformat()
        if local_date not in days:
            days[local_date] = day_facts(connection, timeline_id, subject, definition, world, slot.local_date,
                                         days_off.get(local_date))
        block, entry = day_block(slot.block.view(), days[local_date]), None
        if block['kind'] not in routine.RESTING:
            company = free_people(connection, timeline_id, slot) if subject == COMPANION else []
            celebrants = birthdays(connection, timeline_id, local_date, company) if subject == COMPANION else []
            seed = seed_for(timeline_id, subject, slot.key)
            entry = (recommendations.session_for(connection, timeline_id, slot, block, definition, seed, company)
                     if subject == COMPANION else None) or composer.compose(
                {**slot.view(), 'block': block}, definition, world, seed, recent[-3:], company, celebrants)
            if entry:
                recent.append(entry['activity'])
        connection.execute(
            'INSERT INTO life_agenda (id, timeline_id, subject, slot_key, starts_at, ends_at, local_date, block, entry, '
            'basis, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (identifier(), timeline_id, subject, slot.key, stamp(slot.starts_at), stamp(slot.ends_at),
             slot.local_date.isoformat(), encode(block), encode(entry) if entry else None, basis,
             stamp(now)))
        written += 1
    connection.execute('INSERT INTO agenda_cursors (timeline_id, subject, through) VALUES (?, ?, ?) '
                       'ON CONFLICT (timeline_id, subject) DO UPDATE SET through=excluded.through',
                       (timeline_id, subject, stamp(end)))
    return written


def day_facts(connection, timeline_id, subject, definition, world, day, holiday) -> dict:
    """What every block on one local date shares: weather, annual events, a holiday and how the subject feels."""
    local_date = day.isoformat()
    return {'weather': composer.weather(world, definition, local_date),
            'happenings': composer.happenings(world, definition, local_date), 'holiday': holiday,
            'body': body.state_on(f'{timeline_id}:{subject}', day,
                                  body.previous_entries(connection, timeline_id, subject, day), world, definition)}


def day_block(block: dict, facts: dict) -> dict:
    block = body.apply(holiday_block(block, facts['holiday']), facts['body'])
    if facts['weather']:
        block['weather'] = facts['weather']
    if facts['happenings']:
        block['happenings'] = facts['happenings']
    return block


def public_holidays(world, definition, start, end) -> dict[str, str]:
    """Local dates of public holidays in the companion's city, with their names (from the world data)."""
    data = circle.city_data(definition, world)
    if not data:
        return {}
    found = generators.holidays(data, (start - timedelta(days=1)).date(), (end + timedelta(days=1)).date())
    return {item['date']: item['name'] for item in found if item['kind'] == 'public'}


def holiday_block(block: dict, holiday: str | None) -> dict:
    """On a public holiday, a work or study block becomes a day off named after the holiday."""
    if not holiday or block['kind'] not in WORKING:
        return block
    return {**block, 'kind': 'leisure', 'label': f'{holiday} (day off)', 'holiday': holiday}


def recent_activities(connection, timeline_id, subject, before) -> list[str]:
    rows = many(connection, 'SELECT entry FROM life_agenda WHERE timeline_id=? AND subject=? AND starts_at<? '
                'AND entry IS NOT NULL ORDER BY starts_at DESC LIMIT 3', (timeline_id, subject, before))
    return [decode(row['entry'])['activity'] for row in reversed(rows)]


def free_people(connection, timeline_id, slot) -> list[dict]:
    """Circle members with nothing busy overlapping the slot, in circle order."""
    result = []
    for person in circle.people(connection, timeline_id):
        if not decode(person['schedule']):
            continue
        overlapping = many(connection, 'SELECT block FROM life_agenda WHERE timeline_id=? AND subject=? '
                           'AND starts_at<? AND ends_at>?', (timeline_id, person['id'], stamp(slot.ends_at),
                                                             stamp(slot.starts_at)))
        if not any(decode(row['block'])['kind'] in BUSY or decode(row['block']).get('sick_day')
                   for row in overlapping):
            result.append({'id': person['id'], 'name': person['name']})
    return result


def birthdays(connection, timeline_id, local_date, free) -> list[dict]:
    """Circle members whose birthday is on this date: out-of-town ones always (a call), local ones
    only when free at the slot (`free` from free_people)."""
    free_ids, result = {person['id'] for person in free}, []
    for person in circle.people(connection, timeline_id):
        if circle.birthday(person['id']) != local_date[5:]:
            continue
        local = bool(decode(person['schedule']))
        if not local or person['id'] in free_ids:
            result.append({'id': person['id'], 'name': person['name'], 'local': local})
    return result


def settle(connection, timeline_id, now) -> int:
    """Upcoming entries that have ended happen, unless a pause covers them (T6)."""
    due = many(connection, "SELECT id, starts_at, ends_at FROM life_agenda WHERE timeline_id=? AND status='upcoming' "
               'AND ends_at<=?', (timeline_id, stamp(now)))
    for row in due:
        status = 'skipped' if overlapping_pause(connection, row['starts_at'], row['ends_at']) else 'happened'
        connection.execute('UPDATE life_agenda SET status=? WHERE id=?', (status, row['id']))
    return len(due)


def entry_view(row: dict) -> dict:
    return {'subject': row['subject'], 'slot': row['slot_key'], 'starts_at': row['starts_at'],
            'ends_at': row['ends_at'], 'local_date': row['local_date'], 'block': decode(row['block']),
            'entry': decode(row['entry']) if row['entry'] else None, 'status': row['status']}


def companion_entry(connection, timeline_id, slot_key, basis) -> dict | None:
    """The precomputed companion entry for a slot, when it was built from the current version."""
    row = optional(connection, 'SELECT * FROM life_agenda WHERE timeline_id=? AND subject=? AND slot_key=? '
                   'AND basis=?', (timeline_id, COMPANION, slot_key, basis))
    return row and {**row, 'entry': decode(row['entry']) if row['entry'] else None,
                    'prepared': decode(row['prepared']) if row['prepared'] else None}


def diary(connection, timeline_id, subject, limit=20, before=None) -> list[dict]:
    """A circle member's entries that have happened, newest first. Upcoming ones stay hidden.
    Committed companion events this person was part of are included: an entry they overlap carries
    `with_companion`, and one with no overlapping entry appears on its own."""
    before = before or '9999'
    rows = many(connection, "SELECT * FROM life_agenda WHERE timeline_id=? AND subject=? AND status='happened' "
                'AND entry IS NOT NULL AND starts_at<? ORDER BY starts_at DESC LIMIT ?',
                (timeline_id, subject, before, limit))
    shared = many(connection, "SELECT id, summary, starts_at, ends_at FROM life_events WHERE timeline_id=? "
                  "AND status='committed' AND json_extract(details, '$.with.id')=? AND starts_at<? "
                  'ORDER BY starts_at DESC LIMIT ?', (timeline_id, subject, before, limit))
    result, used = [], set()
    for row in rows:
        item = entry_view(row)
        together = next((event for event in shared if event['starts_at'] < row['ends_at']
                         and event['ends_at'] > row['starts_at']), None)
        item['with_companion'] = {'event_id': together['id'], 'summary': together['summary']} if together else None
        if together:
            used.add(together['id'])
        result.append(item)
    for event in shared:
        if event['id'] not in used:
            result.append({'subject': subject, 'slot': None, 'starts_at': event['starts_at'],
                           'ends_at': event['ends_at'], 'local_date': None, 'block': None,
                           'entry': {'summary': event['summary']}, 'status': 'happened',
                           'with_companion': {'event_id': event['id'], 'summary': event['summary']}})
    return sorted(result, key=lambda item: item['starts_at'], reverse=True)[:limit]


def current(connection, timeline_id, subject, now) -> dict | None:
    """The block a subject is in right now: where they are, never what will happen there."""
    row = optional(connection, 'SELECT * FROM life_agenda WHERE timeline_id=? AND subject=? AND starts_at<=? '
                   'AND ends_at>? LIMIT 1', (timeline_id, subject, stamp(now), stamp(now)))
    return decode(row['block']) if row else None


def day_on(connection, timeline_id, local_date) -> dict:
    """The weather (observed where looked up, else typical) and annual events recorded for the companion's
    city on a local date, and how the companion feels that day (companion/life/body.py)."""
    row = optional(connection, "SELECT json_extract(block, '$.weather') AS weather, json_extract(block, "
                   "'$.happenings') AS happenings FROM life_agenda WHERE timeline_id=? AND subject=? AND "
                   "local_date=? ORDER BY json_extract(block, '$.weather.observed') IS NULL, starts_at LIMIT 1",
                   (timeline_id, COMPANION, local_date))
    state = optional(connection, "SELECT json_extract(block, '$.body') AS body FROM life_agenda WHERE timeline_id=? "
                     "AND subject=? AND local_date=? AND json_extract(block, '$.body') IS NOT NULL LIMIT 1",
                     (timeline_id, COMPANION, local_date))
    return {'weather': decode(row['weather']) if row and row['weather'] else None,
            'happenings': decode(row['happenings']) if row and row['happenings'] else [],
            'body': decode(state['body']) if state else None}


def happenings_text(events) -> str:
    return 'Annual events in the city today: ' + '; '.join(
        event['name'] + (f" ({event['neighborhood']})" if event['neighborhood'] else '') for event in events) + '.'


def weather_text(conditions: dict) -> str:
    text = f"High {conditions['high_f']}°F, low {conditions['low_f']}°F, "
    text += 'with rain.' if conditions['rain'] else 'dry.'
    # The month's note can describe sunshine, so it is left out on a rainy day.
    return text if conditions['rain'] else f"{text} {conditions['note']}"


def forget_person(connection, timeline_id, person_id, now):
    """After a rename, removal or restore, rebuild this person's upcoming entries and the companion's
    upcoming entries that name them."""
    connection.execute('UPDATE agenda_cursors SET through=MIN(through, ?) WHERE timeline_id=? AND subject=?',
                       (stamp(now), timeline_id, person_id))
    removed = connection.execute(
        "DELETE FROM life_agenda WHERE timeline_id=? AND subject=? AND status='upcoming' "
        "AND json_extract(entry, '$.with.id')=?", (timeline_id, COMPANION, person_id)).rowcount
    if removed:
        connection.execute('UPDATE agenda_cursors SET through=MIN(through, ?) WHERE timeline_id=? AND subject=?',
                           (stamp(now), timeline_id, COMPANION))


def circle_view(connection, timeline_id, now, include_removed=False) -> list[dict]:
    """The circle with where each person is right now and what they did recently."""
    result, known = [], circle.ties(circle.people(connection, timeline_id))
    for row in circle.people(connection, timeline_id, include_removed):
        person = circle.view(row)
        block = current(connection, timeline_id, row['id'], now) if row['status'] == 'active' else None
        result.append({**person, 'now': block, 'recent': diary(connection, timeline_id, row['id'], limit=3),
                       'knows': known.get(row['id'], [])})
    return result


def unprepared(connection, timeline_id, basis, now, limit) -> list[dict]:
    """The companion's next upcoming entries that something happens in and that have no wording yet."""
    rows = many(connection, "SELECT * FROM life_agenda WHERE timeline_id=? AND subject=? AND status='upcoming' "
                'AND basis=? AND entry IS NOT NULL AND prepared IS NULL AND ends_at>? ORDER BY starts_at LIMIT ?',
                (timeline_id, COMPANION, basis, stamp(now), limit))
    return [{**row, 'block': decode(row['block']), 'entry': decode(row['entry'])} for row in rows]


def save_prepared(connection, entry_id, prepared: dict):
    connection.execute('UPDATE life_agenda SET prepared=? WHERE id=?', (encode(prepared), entry_id))


def upcoming(connection, timeline_id, basis, now, hours=24, limit=4) -> list[dict]:
    """The companion's next precomputed entries, for the chat context only: likely plans the
    companion may mention as intentions. They are not events and nothing commits them."""
    rows = many(connection, "SELECT * FROM life_agenda WHERE timeline_id=? AND subject=? AND status='upcoming' "
                'AND basis=? AND entry IS NOT NULL AND starts_at>? AND starts_at<? ORDER BY starts_at LIMIT ?',
                (timeline_id, COMPANION, basis, stamp(now), stamp(now + timedelta(hours=hours)), limit))
    return [entry_view(row) for row in rows]


def intention_text(item) -> str:
    entry = item['entry']
    text = f"- {item['local_date']}, {item['block']['label'].lower()} ({item['block']['start']}): "
    text += entry['activity'].replace('-', ' ')
    if entry.get('place'):
        text += f" at {entry['place']['name']}"
    if entry.get('with'):
        text += f" with {entry['with']['name']}"
    return text
