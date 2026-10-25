"""Their hours and yours (v1.1.0): a companion in another time zone keeps hours that overlap the user's evenings.

A companion's day runs on their home city's clock, and the user's on theirs. Rules only, no model:

- Fitting. When the app makes a companion (their first version, companion/characters.py `insert_version`), it looks
  at the user's evenings (EVENING, the user's time) through the week. When sleep or work would cover more than CLASH of
  them, it moves the whole week later or earlier by whole hours, the least that frees FREE of those evenings, and gives
  them a life that explains it: a night owl, an early riser, or odd hours working remotely. The city keeps its clock;
  only their routine moves, and the Character page can put it back. A world from before this (`settle_all`) gets the
  same once, for a companion whose sleep covers most of the user's evenings.
- Live on my clock. A switch on the Character page moves their whole week onto the user's time zone: the week as
  written, moved by the gap between the two clocks, and kept in step when either clock changes (daylight saving, or
  the user's own zone). In their city they keep odd hours, working remotely on the user's hours or living by night.
  Off, the week goes back (to the fitted hours when it had them).

`definition['their_hours']`: {mode: 'fit' | 'mine' | 'city', shift: minutes the week is moved from as written,
why, zone: the user's zone it follows ('mine'), fit: the fitted shift to go back to}. 'city' is the user's choice to
keep the city's hours, so nothing fits them again. The schedule saved is always the moved one, on the city's clock, so
everything that reads their day reads it as it is.
"""
from datetime import date, datetime, time, timedelta

from companion.clock import stamp, zone
from companion.database import decode, many, optional, settings
from companion.life import routine

# The user's evening, their time, and how much of it sleep or work may cover before a companion's week is moved.
EVENING = (time(18), time(23))
CLASH = 0.4
FREE = 0.8
# A world from before this: a companion's week is moved once, when sleep alone covers more than this of the evenings.
ASLEEP_MOST = 0.5
UPGRADE_KEY = 'their_hours_fitted'
# A move of up to this many hours is a habit (night owl, early riser); more is remote work on someone else's hours.
HABIT_HOURS = 4
BUSY = {'sleep', 'work', 'study'}
WHY = {
    'night_owl': 'You are a night owl: you stay up late and sleep in.',
    'early_riser': 'You are an early riser: up with the sun, early to bed.',
    'remote': 'You work remotely for a team in another time zone, so you keep odd hours for {city}.',
    'nights': 'You live by night: you sleep through much of the day in {city} and are up when others sleep.',
    'mine': "You live on the user's clock ({zone}): you work remotely on their hours, so you keep odd hours for {city}.",
    'mine_free': "You live on the user's clock ({zone}), so you keep odd hours for {city}: up when they are.",
}
# The Character page's words for each reason (src/features/character/theirHoursText.ts mirrors these).
NOTE = {'fit': 'Hours fitted to yours', 'mine': 'Living on your clock', 'city': 'Back on their city\'s hours',
        'step': 'Kept on your clock'}


# --- Clocks ---------------------------------------------------------------------------------------------------------

def offset(timezone: str, instant: datetime) -> int:
    """Minutes ahead of UTC a zone is at an instant."""
    return int(instant.astimezone(zone(timezone)).utcoffset().total_seconds() // 60)


def gap(city_zone: str, user_zone: str, instant: datetime) -> int:
    """Minutes the city's clock is ahead of the user's: the shift that puts a week written on the user's clock onto the
    city's."""
    return offset(city_zone, instant) - offset(user_zone, instant)


def minutes(value: str) -> int:
    hours, mins = value.split(':')
    return int(hours) * 60 + int(mins)


def clock(total: int) -> str:
    return f'{total // 60:02d}:{total % 60:02d}'


def shifted(schedule: list[dict], by: int) -> list[dict]:
    """The week moved by `by` minutes: each block keeps its length, and a block that starts on another day moves to it."""
    if not by:
        return schedule
    result = []
    for block in schedule:
        start = minutes(block['start']) + by
        days = sorted({(day + start // 1440) % 7 for day in block.get('days', range(7))})
        result.append({**block, 'start': clock(start % 1440), 'end': clock((minutes(block['end']) + by) % 1440),
                       'days': days})
    return result


def written(definition: dict) -> list[dict]:
    """Their week as saved, the gentle default day spelled out when there is none."""
    return [dict(item) for item in definition.get('schedule') or routine.DEFAULT_SCHEDULE]


# --- How much of the user's evenings they have free -----------------------------------------------------------------

def evenings(user_zone: str, day: date) -> list[tuple[datetime, datetime]]:
    """The user's evenings for the week from `day`, as instants."""
    tz = zone(user_zone)
    return [(datetime.combine(day + timedelta(days=offset_days), EVENING[0], tz),
             datetime.combine(day + timedelta(days=offset_days), EVENING[1], tz)) for offset_days in range(7)]


def covered(schedule: list[dict], city_zone: str, user_zone: str, day: date, kinds=BUSY) -> float:
    """The share of the user's evenings this week that the companion spends in `kinds` (asleep or at work)."""
    blocks = [block for block in routine.blocks({'schedule': schedule})[0] if block.kind in kinds]
    total = taken = 0.0
    for start, end in evenings(user_zone, day):
        total += (end - start).total_seconds()
        spans = sorted((max(slot.starts_at, start), min(slot.ends_at, end))
                       for slot in routine.slots(blocks, city_zone, start, end))
        reach = start
        for left, right in spans:
            left = max(left, reach)
            if right > left:
                taken += (right - left).total_seconds()
                reach = right
    return taken / total if total else 0.0


def best_shift(schedule: list[dict], city_zone: str, user_zone: str, day: date) -> int:
    """The least move, in whole hours either way, that frees FREE of the user's evenings; else the one that frees most."""
    best, best_free = 0, 1 - covered(schedule, city_zone, user_zone, day)
    for hours in (step for size in range(1, 13) for step in (size, -size)):
        free = 1 - covered(shifted(schedule, hours * 60), city_zone, user_zone, day)
        if free >= FREE - 1e-9:
            return hours * 60
        if free > best_free + 0.05:
            best, best_free = hours * 60, free
    return best


def why_for(schedule: list[dict], by: int) -> str:
    works = any(block.get('kind') in ('work', 'study') for block in schedule)
    if abs(by) <= HABIT_HOURS * 60:
        return 'night_owl' if by > 0 else 'early_riser'
    return 'remote' if works else 'nights'


# --- Fitting a companion's week -------------------------------------------------------------------------------------

def user_zone(connection) -> str:
    return settings(connection)['user_timezone']


def known(connection) -> bool:
    """Whether the user's zone is known (from this PC or chosen, companion/workspace.py): nothing fits a guess."""
    return settings(connection)['user_timezone_source'] != 'default'


def fitted(connection, definition: dict, now: datetime) -> dict:
    """A new companion's definition with their week moved to overlap the user's evenings, when it would clash; as it
    is when it doesn't, when they already have hours of their own, or when they live in the user's zone."""
    if definition.get('their_hours') or not definition.get('timezone') or not known(connection):
        return definition
    mine = user_zone(connection)
    schedule, day = written(definition), now.astimezone(zone(mine)).date()
    if covered(schedule, definition['timezone'], mine, day) <= CLASH:
        return definition
    by = best_shift(schedule, definition['timezone'], mine, day)
    if not by:
        return definition
    return {**definition, 'schedule': shifted(schedule, by),
            'their_hours': {'mode': 'fit', 'shift': by, 'why': why_for(schedule, by), 'zone': '', 'fit': by}}


def settled(previous: dict, definition: dict, mine: str, now: datetime) -> dict:
    """A revised definition with its week where the switch on the Character page says: the mode the form sent, the
    shift worked out here from the version before (the form never moves the week itself)."""
    before = previous.get('their_hours') or {}
    wanted = definition.get('their_hours') or {}
    mode = wanted.get('mode') or before.get('mode')
    if not mode:
        return definition
    current, fit = int(before.get('shift') or 0), int(before.get('fit') or 0)
    schedule = written(definition)
    if mode == 'mine':
        target, why = gap(definition['timezone'], mine, now), before.get('why') if before.get('mode') == 'mine' else (
            'mine' if any(block.get('kind') in ('work', 'study') for block in schedule) else 'mine_free')
        hours = {'mode': 'mine', 'shift': target, 'why': why, 'zone': mine, 'fit': fit}
    elif mode == 'fit' and fit:
        target = fit
        hours = {'mode': 'fit', 'shift': fit, 'why': why_for(shifted(schedule, -current), fit), 'zone': '', 'fit': fit}
    else:
        target, hours = 0, {'mode': 'city', 'shift': 0, 'why': '', 'zone': '', 'fit': fit}
    return {**definition, 'schedule': shifted(schedule, target - current), 'their_hours': hours}


def why_text(definition: dict, city: str) -> str:
    """The line their chat context gets about keeping hours that don't match their city's, '' with none."""
    hours = definition.get('their_hours') or {}
    line = WHY.get(hours.get('why') or '')
    if not line or hours.get('mode') == 'city':
        return ''
    return line.format(city=city or 'where you live', zone=hours.get('zone') or 'their time zone')


# --- Keeping worlds in step -----------------------------------------------------------------------------------------

def revise(connection, companion_id: str, definition: dict, note: str, timestamp: str):
    """A new version of a companion with their week moved (not the Character page's own save)."""
    from companion.characters import insert_version
    from companion.models import CharacterDefinition
    row = optional(connection, 'SELECT number FROM character_versions WHERE companion_id=? ORDER BY number DESC LIMIT 1',
                   (companion_id,))
    version_id = insert_version(connection, companion_id, row['number'] + 1,
                                CharacterDefinition.model_validate(definition), note, timestamp)
    connection.execute('UPDATE companions SET active_version_id=? WHERE id=?', (version_id, companion_id))


def saved_definitions(connection) -> list[tuple[str, dict]]:
    rows = many(connection, 'SELECT c.id, v.definition FROM companions c JOIN character_versions v '
                'ON v.id=c.active_version_id ORDER BY c.created_at')
    return [(row['id'], decode(row['definition'])) for row in rows]


def settle_all(connection, now: datetime) -> int:
    """Once per world, fit the week of a companion whose sleep covers most of the user's evenings; and always, keep
    anyone living on the user's clock in step with it. Returns how many companions changed."""
    if not known(connection):
        return 0
    mine, timestamp, changed = user_zone(connection), stamp(now), 0
    first = optional(connection, 'SELECT value FROM app_identity WHERE key=?', (UPGRADE_KEY,)) is None
    for companion_id, definition in saved_definitions(connection):
        hours = definition.get('their_hours') or {}
        if hours.get('mode') == 'mine':
            target = gap(definition['timezone'], mine, now)
            if target != hours.get('shift') or mine != hours.get('zone'):
                moved = {**definition, 'schedule': shifted(written(definition), target - int(hours.get('shift') or 0)),
                         'their_hours': {**hours, 'shift': target, 'zone': mine}}
                revise(connection, companion_id, moved, NOTE['step'], timestamp)
                changed += 1
        elif first and not hours and definition.get('timezone'):
            day = now.astimezone(zone(mine)).date()
            if covered(written(definition), definition['timezone'], mine, day, {'sleep'}) > ASLEEP_MOST:
                moved = fitted(connection, {**definition, 'schedule': written(definition)}, now)
                if moved.get('their_hours'):
                    revise(connection, companion_id, moved, NOTE['fit'], timestamp)
                    changed += 1
    if first:
        connection.execute('INSERT OR REPLACE INTO app_identity (key, value) VALUES (?, ?)', (UPGRADE_KEY, timestamp))
    return changed

