"""What happens to someone is written into their own life: the one door for life events about circle people.

A storyline beat (companion/life/storylines.py) used to be a sentence and nothing else: "Kaito went through a breakup"
while his diary said nothing and his people still listed his girlfriend (tester, 2026-11-10). Now every beat that names
someone goes through `record`, which writes a line into their diary (agenda.diary reads it) and makes the change it
describes on their record: a new employer, a partner who is now an ex, two friends who are not speaking. `take_back`
puts the record back when the user ends the storyline or changes how it went; what already happened keeps its words.

Each kind of event is an `Effect` in EFFECTS: its diary line (a template with {name}, {other}, {partner}, filled when
read so a rename carries over) and a small `apply` that changes the record through companion/life/records.py or
circle_love.change. Rules and templates only, no model.
"""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time

from companion.clock import stamp, zone
from companion.database import decode, encode, identifier, many, optional
from companion.life import circle, circle_love, records

COMPANION = 'companion'


@dataclass(frozen=True)
class Effect:
    text: str
    tone: str = 'mixed'
    apply: Callable | None = None
    touches: str = ''  # 'job' or 'love': what of theirs it changes, never when the user set it


def apps(row: dict, touches: str) -> bool:
    """The app chose what this change would touch, so it may change it: what the user set stays."""
    from companion.life import casting
    if touches == 'job':
        return casting.job_is_apps(row) and 'role' not in set(circle.details_of(row).get('edited', ()))
    if touches == 'love':
        return casting.love_is_apps(row)
    return True


@dataclass
class Event:
    """One event being recorded: who it is about, the rest of the cast, and the names its line needs."""
    connection: object
    companion: dict
    row: dict
    other: dict | None
    day: str
    source: str
    now: datetime
    names: dict


# The changes ----------------------------------------------------------------------------------------------------------

def promoted(event: Event) -> list[dict]:
    return listed(records.write(event.connection, event.row['id'], event.now, {'promoted_on': event.day}))


def new_job(event: Event) -> list[dict]:
    """The same line of work at another employer, on that job's hours; a job in someone's own words with no career
    the city knows keeps its words and hours and only loses the old employer."""
    row, details = event.row, circle.details_of(event.row)
    data = city(event)
    work = elsewhere(data, row['career'], event.source, details) if data and details.get('local', True) else None
    if not work:
        return listed(records.write(event.connection, row['id'], event.now, {'employer': '', 'job_since': event.day}))
    shown = details.get('career') or work['career']['name']
    schedule = [block | {'label': shown} if block['kind'] == 'work' else block for block in work['schedule']]
    return listed(records.write(event.connection, row['id'], event.now,
                                {'employer': work['employer']['name'], 'job_since': event.day}, schedule=schedule))


def elsewhere(data: dict, career_id: str, seed: str, details: dict) -> dict | None:
    """A job in this career at an employer that is not their old one, or None when the city has no such career or no
    other place for it."""
    from companion.world import catalog, generators
    if not career_id or career_id not in catalog.careers_for(data):
        return None
    home = next((hood['id'] for hood in data['neighborhoods'] if hood['name'] == details.get('neighborhood')), None)
    for attempt in range(6):
        work = generators.job(data, career_id, seed=f'{seed}:{attempt}', home=home)
        if work['employer']['name'] != details.get('employer'):
            return work
    return None  # The city has nowhere else for this line of work.


def left_job(event: Event) -> list[dict]:
    """A coworker who left the companion's work: a former coworker now, doing the companion's line of work somewhere
    else, on that job's hours (or, with no career the city knows, as they were, minus the companion's workplace)."""
    from companion.life import outings, work
    definition, timeline_id = event.companion['version']['definition'], event.companion['active_timeline_id']
    data = outings.city_data(event.connection, definition)
    career = (work.career_of(definition, data) or {}) if data else {}
    found = elsewhere(data, career.get('id') or '', event.source,
                      {'employer': (work.state(event.connection, timeline_id) or {}).get('employer')}) if data else None
    details = {'works_with_companion': None, 'left_on': event.day}
    if not found:
        name = definition['name'].split()[0]
        return listed(records.write(event.connection, event.row['id'], event.now,
                                    details | {'career': f'Used to work with {name}', 'employer': ''},
                                    role='former coworker'))
    return listed(records.write(event.connection, event.row['id'], event.now,
                                details | {'career': career['name'], 'employer': found['employer']['name']},
                                role='former coworker', career=career['id'], schedule=found['schedule']))


def broke_up(event: Event) -> list[dict]:
    partner = circle_love.named(event.connection, event.companion, event.row,
                                circle_love.state(event.connection, event.row, people(event)).get('partner'))
    event.names['partner'] = (partner or {}).get('name') or 'their partner'
    return listed(circle_love.change(event.connection, event.row, 'single', event.day, event.source, event.now,
                                     people=people(event)))


def not_speaking(event: Event) -> list[dict]:
    """Only the first of the two writes it: it is one tie, kept on both rows."""
    if not event.other or event.row['id'] > event.other['id']:
        return []
    return circle_love.tie_between(event.connection, event.row, event.other, '', event.now)


def together(event: Event) -> list[dict]:
    other = event.other
    partner = {'key': other['seed'], 'name': other['name'], 'circle_id': other['id']}
    undos = listed(circle_love.change(event.connection, event.row, 'seeing', event.day, event.source, event.now,
                                      partner=partner, people=people(event)))
    if event.row['id'] < other['id']:
        undos += circle_love.tie_between(event.connection, event.row, other, 'partners', event.now)
    return undos


def apart(event: Event) -> list[dict]:
    other = event.other
    partner = {'key': other['seed'], 'name': other['name'], 'circle_id': other['id']}
    exes = [*circle_love.state(event.connection, event.row, people(event))['exes'], {**partner, 'until': event.day}]
    return listed(records.write(event.connection, event.row['id'], event.now, {'partner': {
        'state': 'single', 'since': event.day, 'source': event.source, 'exes': exes}}))


def picked(event: Event) -> list[dict]:
    partner = circle_love.new_partner(event.connection, event.companion, event.row)
    event.names['partner'] = partner['name']
    return listed(circle_love.change(event.connection, event.row, 'seeing', event.day, event.source, event.now,
                                     partner=partner, people=people(event)))


def engaged(event: Event) -> list[dict]:
    found = circle_love.state(event.connection, event.row, people(event))
    partner = found['partner'] if found['state'] == 'seeing' and found['partner'] else \
        circle_love.new_partner(event.connection, event.companion, event.row)
    partner = circle_love.named(event.connection, event.companion, event.row, partner) or partner
    event.names['partner'] = partner.get('name') or 'their partner'
    return listed(circle_love.change(event.connection, event.row, 'engaged', event.day, event.source, event.now,
                                     partner=partner, people=people(event)))


def separated(event: Event) -> list[dict]:
    if not event.other or event.row['id'] > event.other['id']:
        return []
    return circle_love.tie_between(event.connection, event.row, event.other, 'separated', event.now)


def treatment(event: Event) -> list[dict]:
    return listed(records.write(event.connection, event.row['id'], event.now, {'in_treatment_since': event.day}))


def dating_companion(event: Event) -> list[dict]:
    """The companion and their best friend decided to try dating: the friend is their partner now
    (companion/life/love_life.py), when the companion can have a love life of their own."""
    from companion.life import love_life
    return love_life.start_with(event.connection, event.companion, event.row, date.fromisoformat(event.day), event.now)


def listed(undo: dict | None) -> list[dict]:
    return [undo] if undo else []


def city(event: Event) -> dict | None:
    from companion.life import outings
    return outings.city_data(event.connection, event.companion['version']['definition'])


def people(event: Event) -> list[dict]:
    return circle.people(event.connection, event.companion['active_timeline_id'])


EFFECTS = {
    'promoted': Effect('{name} got a promotion at work.', 'good', promoted),
    'big_order': Effect('{name} landed a big order.', 'good'),
    'job_offer': Effect('{name} got a job offer and is deciding whether to take it.'),
    'new_job': Effect('{name} started a new job.', 'good', new_job, 'job'),
    'stayed_put': Effect('{name} turned the job offer down.'),
    'gave_notice': Effect('{name} gave notice at work.'),
    'left_job': Effect("It was {name}'s last day at work.", 'mixed', left_job, 'job'),
    'broke_up': Effect('{name} and {partner} broke up.', 'bad', broke_up, 'love'),
    'doing_better': Effect('{name} is doing better after the breakup.', 'good'),
    'fell_out': Effect('{name} and {other} had a falling out.', 'bad'),
    'made_up': Effect('{name} and {other} made up.', 'good'),
    'not_speaking': Effect("{name} and {other} still aren't speaking.", 'bad', not_speaking),
    'together': Effect('{name} and {other} are seeing each other.', 'good', together, 'love'),
    'apart': Effect('{name} and {other} broke up.', 'bad', apart, 'love'),
    'picked': Effect('{name} is seeing someone new.', 'good', picked, 'love'),
    'engaged': Effect('{name} and {partner} got engaged.', 'good', engaged, 'love'),
    'separated': Effect('{name} and {other} separated.', 'bad', separated, 'love'),
    'health_scare': Effect('{name} had a health scare and is waiting on test results.', 'bad'),
    'results_fine': Effect("{name}'s test results came back fine.", 'good'),
    'treatment': Effect("{name}'s test results mean treatment, starting soon.", 'bad', treatment),
    'dating_companion': Effect('', 'good', dating_companion),
}


# Recording and taking back ---------------------------------------------------------------------------------------

def moment(companion: dict, day: str, at: str) -> str:
    local = datetime.combine(date.fromisoformat(day), time.fromisoformat(at), zone(companion['version']['timezone']))
    return stamp(local)


def record(connection, companion: dict, *, subject: str, source: str, kind: str, day: str, at: str,
           other: str | None = None, now) -> bool:
    """Write one event about `subject` (a circle id) once: its line and its change. False when it was already
    written (it is idempotent, so it also fills in beats that happened before v1.3.4), or the person is gone."""
    timeline_id = companion['active_timeline_id']
    if optional(connection, 'SELECT id FROM person_events WHERE timeline_id=? AND subject=? AND source=?',
                (timeline_id, subject, source)):
        return False
    row = optional(connection, "SELECT * FROM circle_people WHERE id=? AND status='active'", (subject,))
    if row is None:
        return False
    effect = EFFECTS[kind]
    names = {'other': other} if other else {}
    other_row = optional(connection, 'SELECT * FROM circle_people WHERE id=?', (other,)) if other and \
        other != COMPANION else None
    event = Event(connection, companion, row, other_row, day, source, now, names)
    allowed = apps(row, effect.touches) and (other_row is None or apps(other_row, effect.touches))
    undo = effect.apply(event) if effect.apply and allowed else []
    connection.execute(
        'INSERT INTO person_events (id, timeline_id, subject, source, kind, local_date, at_time, starts_at, tone, '
        'text, names, undo, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (identifier(), timeline_id, subject, source, kind, day, at, moment(companion, day, at), effect.tone,
         effect.text, encode(event.names), encode(undo), stamp(now)))
    return True


def take_back(connection, timeline_id: str, source_prefix: str, now, forget: bool = False) -> int:
    """Undo what events from these sources changed, newest first, and end them (their lines leave the diaries);
    `forget` deletes them, so the same source can be recorded again (an outcome changed)."""
    from companion.life import love_life
    rows = many(connection, "SELECT * FROM person_events WHERE timeline_id=? AND source LIKE ? AND status='active' "
                'ORDER BY starts_at DESC, created_at DESC', (timeline_id, f'{source_prefix}%'))
    for row in rows:
        for undo in reversed(decode(row['undo']) or []):
            if undo.get('partner_id'):
                love_life.stop_with(connection, undo, now)
            else:
                records.restore(connection, undo, now)
    if forget:
        connection.execute('DELETE FROM person_events WHERE timeline_id=? AND source LIKE ?',
                           (timeline_id, f'{source_prefix}%'))
    else:
        connection.execute("UPDATE person_events SET status='ended' WHERE timeline_id=? AND source LIKE ?",
                           (timeline_id, f'{source_prefix}%'))
    return len(rows)


# Reading -----------------------------------------------------------------------------------------------------------

def filled(row: dict, names: dict[str, str], companion_name: str) -> str:
    found = decode(row['names']) or {}
    other = found.get('other')
    values = {'name': names.get(row['subject'], 'Someone'),
              'other': companion_name if other == COMPANION else names.get(other, 'someone'),
              'partner': found.get('partner') or 'their partner'}
    return row['text'].format(**values)


def for_person(connection, timeline_id: str, subject: str, before: str | None = None, limit: int = 20) -> list[dict]:
    """A person's events with a line, newest first: {kind, starts_at, local_date, tone, text}."""
    rows = many(connection, "SELECT * FROM person_events WHERE timeline_id=? AND subject=? AND status='active' "
                "AND text!='' AND starts_at<? ORDER BY starts_at DESC LIMIT ?",
                (timeline_id, subject, before or '9999', limit))
    if not rows:
        return []
    names = {row['id']: row['name'] for row in circle.people(connection, timeline_id, include_removed=True)}
    from companion.characters import definition_for_timeline
    companion_name = (definition_for_timeline(connection, timeline_id).get('name') or '').split(' ')[0]
    return [{'kind': row['kind'], 'starts_at': row['starts_at'], 'local_date': row['local_date'],
             'tone': row['tone'], 'text': filled(row, names, companion_name)} for row in rows]


def lately(connection, timeline_id: str, subject: str, today: date, days: int = 14, limit: int = 2) -> list[str]:
    from datetime import timedelta
    since = (today - timedelta(days=days)).isoformat()
    return [item['text'] for item in for_person(connection, timeline_id, subject, limit=limit)
            if item['local_date'] >= since]


def bad_day(connection, timeline_id: str, subject: str, day: date) -> bool:
    """A bad event happened to them that day or the day before."""
    from datetime import timedelta
    return bool(optional(connection, "SELECT id FROM person_events WHERE timeline_id=? AND subject=? AND "
                         "status='active' AND tone='bad' AND local_date BETWEEN ? AND ?",
                         (timeline_id, subject, (day - timedelta(days=1)).isoformat(), day.isoformat())))


def bad_days(connection, timeline_id: str) -> set[tuple[str, str]]:
    """(subject, local date) for every day someone is having a bad time: a bad event's day and the day after
    (`bad_day` for all of them at once)."""
    from datetime import timedelta
    found = set()
    for row in many(connection, "SELECT subject, local_date FROM person_events WHERE timeline_id=? AND "
                    "status='active' AND tone='bad'", (timeline_id,)):
        day = date.fromisoformat(row['local_date'])
        found |= {(row['subject'], day.isoformat()), (row['subject'], (day + timedelta(days=1)).isoformat())}
    return found


# Timelines -------------------------------------------------------------------------------------------------------

def copy(connection, parent_id: str, new_id: str, ids: dict, cutoff: str, now) -> None:
    """A fork keeps the events up to its day, with their ids remapped; what later events changed on the copied rows
    is taken back on the copy."""
    rows = many(connection, "SELECT * FROM person_events WHERE timeline_id=? AND status='active' "
                'ORDER BY starts_at DESC, created_at DESC', (parent_id,))
    for row in rows:
        undo = [{**item, 'id': ids.get(item.get('id'), item.get('id'))} for item in decode(row['undo']) or []]
        if row['starts_at'] > cutoff:
            for item in reversed(undo):
                if not item.get('partner_id'):
                    records.restore(connection, item, now)
            continue
        if row['subject'] not in ids:
            continue
        names = decode(row['names']) or {}
        names = {**names, **({'other': ids.get(names['other'], names['other'])} if names.get('other') else {})}
        connection.execute(
            'INSERT OR IGNORE INTO person_events (id, timeline_id, subject, source, kind, local_date, at_time, '
            'starts_at, tone, text, names, undo, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (identifier(), new_id, ids[row['subject']], remapped(row['source'], ids), row['kind'], row['local_date'],
             row['at_time'], row['starts_at'], row['tone'], row['text'], encode(names),
             encode([item for item in undo if not item.get('partner_id')]), row['status'], row['created_at']))


def remapped(source: str, ids: dict) -> str:
    kind, _sep, rest = source.partition(':')
    found, _sep, beat = rest.partition(':')
    return f'{kind}:{ids.get(found, found)}:{beat}' if beat else source


def roll_back(connection, timeline_id: str, day: date, now) -> int:
    """Back when (companion/back_when_rollback.py): events after `day` have not happened; their changes go."""
    rows = many(connection, 'SELECT DISTINCT source FROM person_events WHERE timeline_id=? AND local_date>?',
                (timeline_id, day.isoformat()))
    return sum(take_back(connection, timeline_id, row['source'], now, forget=True) for row in rows)

