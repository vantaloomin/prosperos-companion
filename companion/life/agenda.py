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

from companion.clock import parse, stamp
from companion.database import decode, encode, identifier, many, optional
from companion.life import circle, composer, routine
from companion.workspace import overlapping_pause

HORIZON = timedelta(days=7)
BACKFILL = timedelta(days=30)
COMPANION = 'companion'
BUSY = {'work', 'study', 'sleep'}


def subjects(connection, companion, world, now) -> list[tuple[str, dict, str]]:
    """(subject, definition, basis) with the circle first, so the companion's entries can name a
    circle member who is free."""
    version = companion['version']
    definition = version['definition']
    result = []
    for person in circle.ensure(connection, companion, world, now):
        result.append((person['id'], {'name': person['name'], 'schedule': decode(person['schedule']),
                                      'home_city': definition.get('home_city', ''),
                                      'location': definition.get('location', '')},
                       f"{person['id']}:{person['revision']}"))
    result.append((COMPANION, definition, version['id']))
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
    return {'written': written, 'settled': settled}


def extend_subject(connection, timeline_id, timezone, subject, definition, basis, world, now) -> int:
    stale = connection.execute("DELETE FROM life_agenda WHERE timeline_id=? AND subject=? AND status='upcoming' "
                               'AND basis!=?', (timeline_id, subject, basis)).rowcount
    cursor = optional(connection, 'SELECT through FROM agenda_cursors WHERE timeline_id=? AND subject=?',
                      (timeline_id, subject))
    created = optional(connection, 'SELECT created_at FROM timelines WHERE id=?', (timeline_id,))
    through = parse(cursor['through']) if cursor else parse(created['created_at'])
    if stale:
        # Rebuild from now: the past is already settled under the old basis.
        through = min(through, now)
    start, end = max(through, now - BACKFILL), now + HORIZON
    if start >= end:
        return 0
    schedule, _default = routine.blocks(definition)
    recent = recent_activities(connection, timeline_id, subject, stamp(start))
    written = 0
    for slot in routine.slots(schedule, timezone, start, end):
        if optional(connection, 'SELECT id FROM life_agenda WHERE timeline_id=? AND subject=? AND slot_key=?',
                    (timeline_id, subject, slot.key)):
            continue
        entry = None
        if slot.block.kind not in routine.RESTING:
            company = free_people(connection, timeline_id, slot) if subject == COMPANION else []
            entry = composer.compose(slot.view(), definition, world, seed_for(timeline_id, subject, slot.key),
                                     recent[-3:], company)
            if entry:
                recent.append(entry['activity'])
        connection.execute(
            'INSERT INTO life_agenda (id, timeline_id, subject, slot_key, starts_at, ends_at, local_date, block, entry, '
            'basis, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (identifier(), timeline_id, subject, slot.key, stamp(slot.starts_at), stamp(slot.ends_at),
             slot.local_date.isoformat(), encode(slot.block.view()), encode(entry) if entry else None, basis,
             stamp(now)))
        written += 1
    connection.execute('INSERT INTO agenda_cursors (timeline_id, subject, through) VALUES (?, ?, ?) '
                       'ON CONFLICT (timeline_id, subject) DO UPDATE SET through=excluded.through',
                       (timeline_id, subject, stamp(end)))
    return written


def recent_activities(connection, timeline_id, subject, before) -> list[str]:
    rows = many(connection, 'SELECT entry FROM life_agenda WHERE timeline_id=? AND subject=? AND starts_at<? '
                'AND entry IS NOT NULL ORDER BY starts_at DESC LIMIT 3', (timeline_id, subject, before))
    return [decode(row['entry'])['activity'] for row in reversed(rows)]


def free_people(connection, timeline_id, slot) -> list[dict]:
    """Circle members with nothing busy overlapping the slot, in circle order."""
    result = []
    for person in circle.people(connection, timeline_id):
        overlapping = many(connection, 'SELECT block FROM life_agenda WHERE timeline_id=? AND subject=? '
                           'AND starts_at<? AND ends_at>?', (timeline_id, person['id'], stamp(slot.ends_at),
                                                             stamp(slot.starts_at)))
        if not any(decode(row['block'])['kind'] in BUSY for row in overlapping):
            result.append({'id': person['id'], 'name': person['name']})
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
    """A circle member's entries that have happened, newest first. Upcoming ones stay hidden."""
    rows = many(connection, "SELECT * FROM life_agenda WHERE timeline_id=? AND subject=? AND status='happened' "
                'AND entry IS NOT NULL AND starts_at<? ORDER BY starts_at DESC LIMIT ?',
                (timeline_id, subject, before or '9999', limit))
    return [entry_view(row) for row in rows]


def current(connection, timeline_id, subject, now) -> dict | None:
    """The block a subject is in right now: where they are, never what will happen there."""
    row = optional(connection, 'SELECT * FROM life_agenda WHERE timeline_id=? AND subject=? AND starts_at<=? '
                   'AND ends_at>? LIMIT 1', (timeline_id, subject, stamp(now), stamp(now)))
    return decode(row['block']) if row else None


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
    result = []
    for row in circle.people(connection, timeline_id, include_removed):
        person = circle.view(row)
        block = current(connection, timeline_id, row['id'], now) if row['status'] == 'active' else None
        result.append({**person, 'now': block, 'recent': diary(connection, timeline_id, row['id'], limit=3)})
    return result


def unprepared(connection, timeline_id, basis, now, limit) -> list[dict]:
    """The companion's next upcoming entries that something happens in and that have no wording yet."""
    rows = many(connection, "SELECT * FROM life_agenda WHERE timeline_id=? AND subject=? AND status='upcoming' "
                'AND basis=? AND entry IS NOT NULL AND prepared IS NULL AND ends_at>? ORDER BY starts_at LIMIT ?',
                (timeline_id, COMPANION, basis, stamp(now), limit))
    return [{**row, 'block': decode(row['block']), 'entry': decode(row['entry'])} for row in rows]


def save_prepared(connection, entry_id, prepared: dict):
    connection.execute('UPDATE life_agenda SET prepared=? WHERE id=?', (encode(prepared), entry_id))
