"""Visits with the other parent (Hit List #78, v0.16 Such Stuff as Dreams): the stays a child of parents who live apart
spends with the parent they don't live with, planned by the app and on the calendar.

The app decides, the user overrides ("the world exists outside of User", Vanta 2026-10-08). Rules and seeds only, no
model. Every co-parenting case gets planned stays (`cases`):

- The user and a companion who split up with children of their own (companion/life/custody.py): the custody pattern
  sets the rhythm (every other weekend with the parent they don't live with, or a week each, turn and turn about).
- A companion and their own ex with a child of theirs (companion/life/own_family.py), and the kids a companion had
  before (companion/life/kids.py): the same, with the ex in their circle as the other parent.

The Getting together slider (life_settings.together_realism) nudges how often extra stays come on top (`EXTRAS`): a
week in summer, a birthday split between the two homes, a public holiday. Across cities (long distance after a split,
or an ex who lives out of town) the rhythm can't be every other weekend: a stay comes every few weeks by the same
slider (`FAR_WEEKS`), and it works like a trip: the child goes to the other parent's city, handed over at the station,
and sends a postcard in words. A visit asked for in the chat while split up across cities books a stay
(companion/life/long_distance.py `for_the_child`).

Stays show on the calendar (the Character page's Life admin, companion/life/admin.py) and on Today, each with Move
(to the next free weekend, week or day) and Skip this one, after which the app plans a make-up stay when the next one
is more than ten days off; a skip can be undone until the stay would have started. Where the children are on a day
follows the stays (`decides`): custody.with_them, kids.today_line and own_family.with_them read them. The chat context
says whose weekend it is, a stay under way, and a stay the user moved or skipped (`context_lines`).

Children keep v0.14's limits everywhere: words only, and with the adult side of life on nothing about them goes in a
chat prompt (families.withheld).
"""
from datetime import date, datetime, timedelta

from companion.clock import parse, stamp
from companion.database import decode, identifier, many, optional
from companion.errors import require
from companion.life import families, shifts, steps
from companion.world import generators

ACTIVE = True
AHEAD = 21  # Days planned ahead, like the rest of the calendar (companion/life/admin.py).
SHOWN = 14  # Days ahead Today shows.
GROWN = 18
DAYTIME_UNDER = 3  # Children this young have a day with the other parent, not a weekend away.
# Across cities, weeks between stays by the Getting together slider (0 to 3).
FAR_WEEKS = {0: 8, 1: 6, 2: 4, 3: 3}
# What comes on top of the rhythm at each level of the Getting together slider.
EXTRAS = {0: (), 1: ('summer',), 2: ('summer', 'birthday'), 3: ('summer', 'birthday', 'holiday')}
# The month the summer week falls in, north and south of the equator.
SUMMER = {True: 7, False: 1}
# A skipped stay is made up when the next one is further off than this.
MAKE_UP_AFTER = 10
MOVE_TRIES = 4
# How long the chat context mentions a stay the user moved or skipped.
CHANGED = timedelta(days=3)
REASONS = ('rota', 'far', 'summer', 'birthday', 'holiday', 'asked', 'make-up')
PLANNED = ('rota', 'far', 'summer', 'birthday', 'holiday')  # The app's own, planned again when the rhythm changes.
OURS, OWN, KIDS = 'ours', 'own', 'kids'
YOU, COMPANION, OTHER, HOME = 'you', 'companion', 'other', 'home'


class Case:
    """One co-parenting case: whose children, with whom they stay (`host`), the rhythm (`rhythm(day)`: whether the
    host has them that day; None across cities) and, across cities, the city a stay is in."""

    def __init__(self, family: str, subject: str, kids: list[dict], host: str, other: str, rhythm, far: bool,
                 city: dict | None, since: date):
        self.family, self.subject, self.kids, self.host, self.other = family, subject, kids, host, other
        self.rhythm, self.far, self.city, self.since = rhythm, far, city, since
        self.level = 2  # The Getting together slider, set for a planning pass (`plan_ahead`).
        self.home = None  # Across cities, the city the children live in.


def level(connection) -> int:
    from companion.life import together
    return together.level(connection)


def first(name: str) -> str:
    return name.split()[0] if name.split() else name


def under_age(kids: list[dict], day: date) -> list[dict]:
    return [kid for kid in kids if kid['status'] == 'born' and families.age_of(kid, day) < GROWN]


# The cases -------------------------------------------------------------------------------------------------------------

def cases(connection, companion: dict, today: date) -> list[Case]:
    """Every co-parenting case this companion has now, with children under 18."""
    if not ACTIVE or not companion.get('active_timeline_id'):
        return []
    found = [ours(connection, companion, today), *own(connection, companion, today), kids_case(connection, companion,
                                                                                               today)]
    return [case for case in found if case and case.kids]


def ours(connection, companion: dict, today: date) -> Case | None:
    """The user and the companion split up with children of their own: they stay with the parent they don't live
    with (the user, unless they live with the user)."""
    from companion.life import custody, our_child
    state = custody.found(connection, companion)
    if not state or not state['split']:
        return None
    state = {**state, 'stays': None}  # The rhythm itself, not the stays read from it.
    host = COMPANION if state['pattern'] == 'with_you' else YOU
    between = state['far']
    city = (between.their_city if host == COMPANION else between.your_city) if between else None
    rhythm = None if between else (lambda day: custody.with_them(state, day) == (host == COMPANION))
    row = custody.ended(connection, companion)
    case = Case(OURS, row['id'], our_child.at_home(connection, companion['active_timeline_id'], today), host,
                'the user', rhythm, bool(between), city, state['since'])
    case.home = (between.your_city if host == COMPANION else between.their_city) if between else None
    return case


def own_pattern(connection, companion: dict, person: dict) -> str:
    from companion.life import custody
    return custody.OWN_PATTERNS[custody.own_outcome(connection, companion, person)['picked']]


def own(connection, companion: dict, today: date) -> list[Case]:
    """A companion's own child with an ex of theirs (companion/life/own_family.py), one case per ex."""
    from companion.life import own_family
    by_parent = {}
    for child in own_family.own_children(connection, companion['active_timeline_id']):
        by_parent.setdefault(child['parent_id'], []).append(child)
    result = []
    for person_id, children in by_parent.items():
        person = optional(connection, "SELECT * FROM circle_people WHERE id=? AND status='active' AND role=?",
                          (person_id, own_family.EX))
        if person is None or not (decode(person['details']) or {}).get('co_parent'):
            continue
        pattern = own_pattern(connection, companion, person)
        result.append(with_ex(connection, companion, OWN, person, children, pattern,
                              lambda day, pattern=pattern: own_rhythm(pattern, day), today))
    return result


def own_rhythm(pattern: str, day: date) -> bool:
    """Whether a companion's own child is with them on this day: every night but every other weekend, a week each, or
    every other weekend only (the weeks alternate by the calendar's week number)."""
    odd = day.isocalendar().week % 2 == 1
    weekend = day.weekday() >= 5
    if pattern == 'shared':
        return not odd
    if pattern == 'weekends':
        return weekend and not odd
    return not (weekend and odd)


def kids_case(connection, companion: dict, today: date) -> Case | None:
    """The kids a companion had before (companion/life/kids.py), when they live part of the time with their other
    parent."""
    from companion.life import kids
    row = kids.record(connection, companion['active_timeline_id']) if kids.ACTIVE else None
    if not row or not row['other_id']:
        return None
    pattern, _how = kids.pattern_of(connection, row)
    person = optional(connection, "SELECT * FROM circle_people WHERE id=? AND status='active'", (row['other_id'],))
    if pattern not in kids.CUSTODY or person is None:
        return None
    since = date.fromisoformat(row['since'])
    return with_ex(connection, companion, KIDS, person, kids.own(connection, companion['active_timeline_id']), pattern,
                   lambda day: kids.with_them(pattern, since, day), today)


def with_ex(connection, companion: dict, family: str, person: dict, children: list[dict], pattern: str, rhythm,
            today: date) -> Case:
    """A case with an ex in their circle: the stays are with the ex, or with the companion when the children live
    with the ex. An ex who lives out of town is in another city (the city a relative out of town is in)."""
    from companion.life import outings, trips
    host = COMPANION if pattern == 'weekends' else OTHER
    away = not (decode(person['details']) or {}).get('local', True)
    home = outings.city_data(connection, companion['version']['definition']) if away else None
    city = (trips.hometown(person['id'], home) if host == OTHER else home) if home else None
    seeded = shifts.monday_of(today) - timedelta(weeks=int(generators.unit(f"stays:{person['id']}", 'since') * 8))
    case = Case(family, person['id'], under_age(children, today), host, first(person['name']),
                None if away else (lambda day: rhythm(day) == (host == COMPANION)), away, city, seeded)
    case.home = (home if host == OTHER else trips.hometown(person['id'], home)) if home else None
    return case


# Where the children are -------------------------------------------------------------------------------------------------

def rows_for(connection, timeline_id: str, family: str, subject: str | None = None) -> list[dict]:
    """A case's stays, in date order (every case of the family without `subject`)."""
    if subject is None:
        return many(connection, 'SELECT * FROM family_stays WHERE timeline_id=? AND family=? ORDER BY start_date',
                    (timeline_id, family))
    return many(connection, 'SELECT * FROM family_stays WHERE timeline_id=? AND family=? AND subject=? ORDER BY '
                'start_date', (timeline_id, family, subject))


def decides(rows: list[dict] | None, day: date) -> str | None:
    """Who has the children on this day by the stays: the host of a planned stay over it, HOME (the parent they live
    with) when the stay planned for it moved or was skipped, None when the rhythm decides."""
    value, moved = day.isoformat(), None
    for row in rows or ():
        if row['status'] == 'planned' and row['start_date'] <= value <= row['end_date']:
            return row['host']
        if row['first_start'] <= value <= row['first_end']:
            moved = HOME
    return moved


def with_companion(rows: list[dict] | None, day: date, otherwise: bool) -> bool:
    """Whether the children are with the companion on this day: as the stays say, else `otherwise` (the rhythm)."""
    found = decides(rows, day)
    if found is None:
        return otherwise
    if found == HOME:
        return next(row['host'] for row in rows if row['first_start'] <= day.isoformat() <= row['first_end']) != COMPANION
    return found == COMPANION


# Planning ---------------------------------------------------------------------------------------------------------------

def plan_ahead(connection, companion: dict, now: datetime) -> int:
    """Called when the agenda extends: each case's stays for the next three weeks, and stays that no longer fit (back
    together, a child grown, where they live changed) taken off. Cheap: no model."""
    timeline_id = companion.get('active_timeline_id')
    if not ACTIVE or not timeline_id:
        return 0
    today, chosen = steps.local_today(companion, now), level(connection)
    found, written, keep = cases(connection, companion, today), 0, set()
    for case in found:
        case.level = chosen
        wanted = desired(connection, companion, case, today)
        keep |= {(case.family, case.subject)}
        written += insert_all(connection, companion, case, wanted, now)
        drop_stale(connection, timeline_id, case, {item['key'] for item in wanted}, today)
    for row in many(connection, "SELECT id, family, subject FROM family_stays WHERE timeline_id=? AND start_date>? AND "
                    "status IN ('planned', 'skipped')", (timeline_id, today.isoformat())):
        if (row['family'], row['subject']) not in keep:
            connection.execute('DELETE FROM family_stays WHERE id=?', (row['id'],))
    return written


def desired(connection, companion: dict, case: Case, today: date) -> list[dict]:
    """The stays the app wants for a case in the next three weeks: the extras first, then the rhythm's around them."""
    home = city_of(connection, companion)
    extras = summer(case, home, today) + birthdays(case, today) + holidays(case, home, today)
    taken = [*extras, *[dict(row) for row in rows_for(connection, companion['active_timeline_id'], case.family,
                                                       case.subject) if row['status'] == 'planned'
                        and row['reason'] not in PLANNED]]
    rhythm = far_spans(case, home, today) if case.far else rota_spans(case, today)
    return extras + [item for item in rhythm if not overlaps(item, taken)]


def city_of(connection, companion: dict) -> dict:
    from companion.life import outings
    return outings.city_data(connection, companion['version']['definition']) or {}


def window(today: date) -> tuple[date, date]:
    return today + timedelta(days=1), today + timedelta(days=AHEAD)


def span(case: Case, reason: str, start: date, end: date, extra: str = '') -> dict:
    return {'key': f'{case.family}:{case.subject}:{reason}:{start.isoformat()}', 'reason': reason,
            'start_date': start.isoformat(), 'end_date': end.isoformat(), 'extra': extra}


def rota_spans(case: Case, today: date) -> list[dict]:
    """The runs of days the rhythm gives the host, starting in the next three weeks (a run already under way is the
    rhythm's own: it was there before stays were planned)."""
    first_day, last_day = window(today)
    result, start = [], None
    day = today - timedelta(days=7)
    while day <= last_day + timedelta(days=8):
        if case.rhythm(day) and start is None:
            start = day
        elif not case.rhythm(day) and start is not None:
            if first_day <= start <= last_day:
                result.append(span(case, 'rota', start, day - timedelta(days=1)))
            start = None
        day += timedelta(days=1)
    return result


def far_spans(case: Case, home: dict, today: date) -> list[dict]:
    """Across cities: a weekend every few weeks by the Getting together slider (with the Friday or Monday when it is a
    public holiday), counted from the week they began living apart."""
    from companion.life import trips
    weeks, (first_day, last_day) = FAR_WEEKS[case.level], window(today)
    result = []
    saturday = first_day + timedelta(days=(5 - first_day.weekday()) % 7)
    while saturday <= last_day:
        if ((shifts.monday_of(saturday) - shifts.monday_of(case.since)).days // 7) % weeks == 1 % weeks:
            days = trips.days_off(home, saturday) if home else [saturday, saturday + timedelta(days=1)]
            result.append(span(case, 'far', days[0], days[-1]))
        saturday += timedelta(days=7)
    return result


def summer(case: Case, home: dict, today: date) -> list[dict]:
    """A week in summer with the host, Monday to Sunday, in a seeded week of July (January south of the equator); not
    when they already spend a week each."""
    if 'summer' not in EXTRAS[case.level] or shared(case, today) or \
            all(families.age_of(kid, today) < DAYTIME_UNDER for kid in case.kids):
        return []
    north = (home.get('lat') or 1) >= 0
    first_day, last_day = window(today)
    result = []
    for year in {first_day.year, last_day.year}:
        start = date(year, SUMMER[north], 1)
        mondays = [start + timedelta(days=offset) for offset in range(31) if (start + timedelta(days=offset)).weekday()
                   == 0 and (start + timedelta(days=offset + 6)).month == SUMMER[north]]
        monday = generators.pick(f'stays:summer:{case.subject}:{year}', 'week', mondays)
        if monday and first_day <= monday <= last_day:
            result.append(span(case, 'summer', monday, monday + timedelta(days=6)))
    return result


def shared(case: Case, today: date) -> bool:
    """A week each: the rhythm gives the host a whole week in the next fortnight."""
    if not case.rhythm:
        return False
    monday = shifts.monday_of(today) + timedelta(days=7)
    return any(all(case.rhythm(start + timedelta(days=offset)) for offset in range(7))
               for start in (monday, monday + timedelta(days=7)))


def birthdays(case: Case, today: date) -> list[dict]:
    """A child's birthday split between the two homes: the day with the host when the rhythm has the child at the
    other home. Not across cities."""
    if 'birthday' not in EXTRAS[case.level] or case.far:
        return []
    first_day, last_day = window(today)
    result = []
    for kid in case.kids:
        born = date.fromisoformat(kid['born_on'])
        for year in {first_day.year, last_day.year}:
            try:
                day = born.replace(year=year)
            except ValueError:
                day = date(year, 3, 1)  # Born on February 29.
            if first_day <= day <= last_day and day > born and not case.rhythm(day):
                result.append(span(case, 'birthday', day, day, kid['id']))
    return result


def holidays(case: Case, home: dict, today: date) -> list[dict]:
    """Every other public holiday on a weekday with the host, when the rhythm has the children at the other home. Not
    across cities."""
    if 'holiday' not in EXTRAS[case.level] or case.far or not home:
        return []
    first_day, last_day = window(today)
    result = []
    for item in generators.holidays(home, first_day, last_day):
        day = date.fromisoformat(item['date'])
        if item['kind'] == 'public' and day.weekday() < 5 and not case.rhythm(day) and \
                generators.unit(f"stays:holiday:{case.subject}:{item['date']}", 'host') < 0.5:
            result.append(span(case, 'holiday', day, day, item['name']))
    return result


def overlaps(item: dict, others: list[dict]) -> bool:
    return any(item['start_date'] <= other['end_date'] and other['start_date'] <= item['end_date'] and
               other.get('key') != item.get('key') for other in others)


def insert_all(connection, companion: dict, case: Case, wanted: list[dict], now: datetime) -> int:
    written = 0
    for item in wanted:
        written += insert(connection, companion, case, item, now)
    return written


def daytime(case: Case, item: dict) -> bool:
    """Children all under three spend a day with the host rather than a weekend away (Iris, 2026-10-20): a weekend
    stay of the rhythm, a make-up or one asked for is its first day; the rest of it stays at home."""
    days = (date.fromisoformat(item['end_date']) - date.fromisoformat(item['start_date'])).days + 1
    start = date.fromisoformat(item['start_date'])
    return 2 <= days <= 3 and item['reason'] in ('rota', 'far', 'make-up', 'asked') and bool(case.kids) and \
        all(families.age_of(kid, start) < DAYTIME_UNDER for kid in case.kids)


def insert(connection, companion: dict, case: Case, item: dict, now: datetime, message_id: str | None = None,
           host: str | None = None, travels: str | None = None, city: dict | None = None) -> int:
    """A stay, once per key. Across cities the child travels to the host, unless the stay says who does."""
    city = city or case.city
    travels = travels if travels is not None else ('child' if case.far else '')
    end = item['start_date'] if daytime(case, item) else item['end_date']
    if end != item['end_date'] and travels == 'child':
        # Too young to travel for a day: the parent they don't live with comes to them.
        travels, city = {YOU: 'you', COMPANION: 'companion'}.get(host or case.host, ''), case.home or city
    return connection.execute(
        'INSERT OR IGNORE INTO family_stays (id, timeline_id, key, family, subject, host, reason, extra, start_date, '
        'end_date, first_start, first_end, city_name, travels, message_id, created_at, updated_at) VALUES (?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (identifier(), companion['active_timeline_id'], item['key'], case.family, case.subject, host or case.host,
         item['reason'], item.get('extra', ''), item['start_date'], end, item['start_date'], item['end_date'],
         (city or {}).get('name', '') if case.far or travels else '', travels, message_id,
         stamp(now), stamp(now))).rowcount


def drop_stale(connection, timeline_id: str, case: Case, keys: set[str], today: date) -> int:
    """The app's own stays in the next three weeks that the rhythm no longer gives (where they live changed, the
    slider moved): taken off, unless the user moved or skipped them; any of them with the other parent as host when
    the host changed."""
    first_day, last_day = window(today)
    dropped = 0
    for row in rows_for(connection, timeline_id, case.family, case.subject):
        upcoming = first_day.isoformat() <= row['first_start'] <= last_day.isoformat()
        mine = row['reason'] in PLANNED and row['status'] == 'planned' and not row['moved_reason']
        if upcoming and ((mine and row['key'] not in keys) or row['host'] != case.host and row['reason'] != 'asked'):
            connection.execute('DELETE FROM family_stays WHERE id=?', (row['id'],))
            dropped += 1
    return dropped


# What the user can change -----------------------------------------------------------------------------------------------

def owned(connection, companion: dict, stay_id: str) -> dict:
    row = optional(connection, 'SELECT * FROM family_stays WHERE id=?', (stay_id,))
    require(row is not None and row['timeline_id'] == companion['active_timeline_id'], 'That stay was not found.', 404)
    return row


def still_to_come(row: dict, today: date) -> bool:
    return row['start_date'] > today.isoformat()


def move(connection, companion: dict, stay_id: str, now: datetime) -> dict:
    """Move a stay still to come to the next weekend, week or day free of the case's other stays."""
    row = owned(connection, companion, stay_id)
    today = steps.local_today(companion, now)
    require(row['status'] == 'planned' and still_to_come(row, today), 'Only a stay still to come can move.', 409)
    others = [other for other in rows_for(connection, row['timeline_id'], row['family'], row['subject'])
              if other['status'] == 'planned' and other['id'] != row['id']]
    start, end = date.fromisoformat(row['start_date']), date.fromisoformat(row['end_date'])
    for week in range(1, MOVE_TRIES + 1):
        item = {'start_date': (start + timedelta(weeks=week)).isoformat(),
                'end_date': (end + timedelta(weeks=week)).isoformat()}
        if not overlaps(item, others):
            connection.execute("UPDATE family_stays SET start_date=?, end_date=?, moved_reason='user', updated_at=? "
                               'WHERE id=?', (item['start_date'], item['end_date'], stamp(now), row['id']))
            return owned(connection, companion, stay_id)
    require(False, 'There is no free weekend for it in the next month.', 409)


def skip(connection, companion: dict, stay_id: str, now: datetime) -> dict:
    """Skip a stay still to come; the app re-plans the next one: a make-up stay the weekend after, when the next one
    is further off than MAKE_UP_AFTER days."""
    row = owned(connection, companion, stay_id)
    today = steps.local_today(companion, now)
    require(row['status'] == 'planned' and still_to_come(row, today), 'Only a stay still to come can be skipped.', 409)
    connection.execute("UPDATE family_stays SET status='skipped', skipped_at=?, updated_at=? WHERE id=?",
                       (stamp(now), stamp(now), row['id']))
    make_up(connection, companion, row, now)
    return owned(connection, companion, stay_id)


def make_up(connection, companion: dict, row: dict, now: datetime) -> int:
    from companion.life import trips
    end = date.fromisoformat(max(row['end_date'], row['first_end']))  # A day's stay planned from a weekend.
    others = [other for other in rows_for(connection, row['timeline_id'], row['family'], row['subject'])
              if other['status'] == 'planned' and other['start_date'] > end.isoformat()]
    if others and (date.fromisoformat(others[0]['start_date']) - end).days <= MAKE_UP_AFTER or \
            rhythm_soon(connection, companion, row, end):
        return 0
    home = city_of(connection, companion)
    saturday = end + timedelta(days=(5 - end.weekday()) % 7 or 7)
    for week in range(MOVE_TRIES):
        days = trips.days_off(home, saturday + timedelta(weeks=week)) if home else \
            [saturday + timedelta(weeks=week), saturday + timedelta(weeks=week, days=1)]
        item = {'key': f"{row['family']}:{row['subject']}:make-up:{days[0].isoformat()}", 'reason': 'make-up',
                'start_date': days[0].isoformat(), 'end_date': days[-1].isoformat(), 'extra': row['id']}
        if not overlaps(item, others):
            found = next((case for case in cases(connection, companion, end) if (case.family, case.subject) ==
                          (row['family'], row['subject'])), None)
            case = Case(row['family'], row['subject'], found.kids if found else [], row['host'], '', None,
                        bool(row['travels']), None, end)
            return insert(connection, companion, case, item, now, host=row['host'], travels=row['travels'],
                          city={'name': row['city_name']} if row['city_name'] else None)
    return 0


def rhythm_soon(connection, companion: dict, row: dict, end: date) -> bool:
    """The rhythm gives the host the children again within MAKE_UP_AFTER days of a skipped stay's end."""
    found = next((case for case in cases(connection, companion, end) if (case.family, case.subject) ==
                  (row['family'], row['subject'])), None)
    return bool(found and found.rhythm) and any(found.rhythm(end + timedelta(days=offset))
                                                 for offset in range(1, MAKE_UP_AFTER + 1))


def undo(connection, companion: dict, stay_id: str, now: datetime) -> dict:
    """Take back skipping a stay that has not come yet: its make-up comes off unless the user moved it."""
    row = owned(connection, companion, stay_id)
    today = steps.local_today(companion, now)
    require(row['status'] == 'skipped' and still_to_come(row, today), 'That can no longer be undone.', 409)
    connection.execute("DELETE FROM family_stays WHERE timeline_id=? AND reason='make-up' AND extra=? AND "
                       "status='planned' AND moved_reason=''", (row['timeline_id'], row['id']))
    connection.execute("UPDATE family_stays SET status='planned', skipped_at=NULL, updated_at=? WHERE id=?",
                       (stamp(now), row['id']))
    return owned(connection, companion, stay_id)


# Asked for in the chat --------------------------------------------------------------------------------------------------

def book_asked(connection, companion: dict, saturdays: list[date], lives: str, message_id: str,
               now: datetime) -> date | None:
    """A visit the user asked for in the chat while split up across cities (long_distance.for_the_child): a weekend
    with the parent the child doesn't live with, the one who asked travelling, the first of `saturdays` free of the
    case's other stays. The Saturday booked, or None."""
    from companion.life import long_distance
    case = ours(connection, companion, steps.local_today(companion, now))
    if case is None:
        return None
    host = YOU if lives == 'them' else COMPANION
    between = long_distance.far(connection, companion)
    city = (between.their_city if host == YOU else between.your_city) if between else None
    taken = [row for row in rows_for(connection, companion['active_timeline_id'], OURS, case.subject)
             if row['status'] == 'planned']
    for saturday in saturdays:
        item = {'key': f'{OURS}:{case.subject}:asked:{saturday.isoformat()}', 'reason': 'asked',
                'start_date': saturday.isoformat(), 'end_date': (saturday + timedelta(days=1)).isoformat()}
        if not overlaps(item, taken):
            insert(connection, companion, case, item, now, message_id, host, host, city)
            return saturday
    return None


# Words -------------------------------------------------------------------------------------------------------------------

def noun(row: dict) -> str:
    """'weekend', 'long weekend', 'week', 'day', 'summer week', 'birthday' or the holiday's name."""
    if row['reason'] == 'summer':
        return 'summer week'
    if row['reason'] == 'birthday':
        return 'birthday'
    if row['reason'] == 'holiday' and row['extra']:
        return row['extra']
    days = (date.fromisoformat(row['end_date']) - date.fromisoformat(row['start_date'])).days + 1
    if days == 1 and row['reason'] in ('rota', 'far', 'make-up', 'asked'):
        return f"{date.fromisoformat(row['start_date']):%A}"  # A day with them: "Yedidya's Saturday with you".
    return 'day' if days == 1 else 'week' if days >= 6 else 'long weekend' if days >= 3 else 'weekend'


def children_of(case: Case, row: dict) -> list[dict]:
    """The children a stay is for: the birthday child alone on their birthday."""
    if row['reason'] == 'birthday':
        return [kid for kid in case.kids if kid['id'] == row['extra']] or case.kids
    return case.kids


def names(kids: list[dict]) -> str:
    return steps.names_text([first(kid['name']) for kid in kids])


def possessive(text: str) -> str:
    return f"{text}'s"


def child_word(kids: list[dict], word: str) -> str:
    """'she', 'them', 'is' ... for one child by their pronouns; for several, the plural."""
    if len(kids) > 1:
        return {'they': 'they', 'them': 'them', 'their': 'their', 'are': 'are', 'is': 'are'}[word]
    return families.fill_child('{are}' if word == 'is' else '{' + word + '}', kids[0])


def day_span(row: dict) -> str:
    """'Saturday October 24 to Sunday October 25', or one day."""
    from companion.life import trips
    if row['start_date'] == row['end_date']:
        return trips.day_text(row['start_date'])
    return f"{trips.day_text(row['start_date'])} to {trips.day_text(row['end_date'])}"


def first_span(row: dict) -> str:
    return day_span({**row, 'start_date': row['first_start'], 'end_date': row['first_end']})


# The chat context -------------------------------------------------------------------------------------------------------

def told_who(case: Case, host: str) -> str:
    """The host as the companion is told: 'the user', 'you' or the ex's first name."""
    return {YOU: 'the user', COMPANION: 'you'}.get(host, case.other)


def resident(case: Case, host: str) -> str:
    """Who the children live with, as the companion is told."""
    return 'the user' if host == COMPANION else 'you'


def context_lines(connection, companion: dict, now: datetime) -> list[tuple[str, str]]:
    """For 'circle_now': each case's stay under way or coming in the next week, and one the user moved or skipped in
    the last few days. Nothing with the adult side on (families.withheld)."""
    if not ACTIVE or not companion.get('active_timeline_id') or families.withheld(connection):
        return []
    today = steps.local_today(companion, now)
    result = []
    for case in cases(connection, companion, today):
        rows = rows_for(connection, companion['active_timeline_id'], case.family, case.subject)
        result += next_line(case, rows, today) + changed_lines(case, rows, today, now)
    return result


def next_line(case: Case, rows: list[dict], today: date) -> list[tuple[str, str]]:
    value = today.isoformat()
    soon = (today + timedelta(days=7)).isoformat()
    row = next((row for row in rows if row['status'] == 'planned' and row['end_date'] >= value and
                row['start_date'] <= soon), None)
    if row is None:
        return []
    kids = children_of(case, row)
    if row['start_date'] <= value:
        return [(f"stay:{row['id']}:now", under_way(case, row, kids, today))]
    line = f"- {day_span(row)}: {possessive(names(kids))} {noun(row)} with {told_who(case, row['host'])}."
    return [(f"stay:{row['id']}", line + travel_text(case, row, kids, ahead=True))]


def under_way(case: Case, row: dict, kids: list[dict], today: date) -> str:
    """'- Ivy is with the user until Sunday: the user's weekend with her.'"""
    end = 'today' if row['end_date'] == today.isoformat() else f"{date.fromisoformat(row['end_date']):%A}"
    who, them = told_who(case, row['host']), child_word(kids, 'them')
    if row['travels'] == 'child' and row['host'] != COMPANION:
        text = (f"- {names(kids)} {child_word(kids, 'is')} staying with {who} in {row['city_name']} until {end}, when "
                f"you meet {them} at the station.")
        if row['start_date'] < today.isoformat():
            text += f" {child_word(kids, 'they').capitalize()} sent you a postcard from {row['city_name']}."
        return text
    whose = 'your' if row['host'] == COMPANION else possessive(who)
    return (f"- {names(kids)} {child_word(kids, 'is')} with {who} until {end}: {whose} {noun(row)} with {them}."
            + travel_text(case, row, kids, ahead=False))


def travel_text(case: Case, row: dict, kids: list[dict], ahead: bool) -> str:
    """Across cities: who goes where, handed over at the station."""
    them, they, city = child_word(kids, 'them'), child_word(kids, 'they').capitalize(), row['city_name'] or 'their city'
    if row['travels'] == 'you':
        return f" The user {'comes' if ahead else 'came'} to {city} to see {them}."
    if row['travels'] == 'companion':
        return f" You {'go' if ahead else 'went'} to {city} to see {them}."
    if row['travels'] != 'child':
        return ''
    if row['host'] == COMPANION:
        return f" {they} {verb(kids, 'comes', 'come')} to you; you meet {them} at the station." if ahead else \
            f' You see {them} off at the station on the last day.'
    return f" {they} {verb(kids, 'goes', 'go')} to {city}; you hand {them} over at the station."


def verb(kids: list[dict], one: str, more: str) -> str:
    """The verb for the children: 'goes' for one child she or he, 'go' for several or one who is they."""
    return more if child_word(kids, 'they') == 'they' else one


def changed_lines(case: Case, rows: list[dict], today: date, now: datetime) -> list[tuple[str, str]]:
    """A stay still to come that the user moved or skipped in the last few days."""
    result = []
    for row in rows:
        if row['first_start'] <= today.isoformat() or now - parse(row['updated_at']) > CHANGED:
            continue
        kids = children_of(case, row)
        what = f"{possessive(names(kids))} {noun(row)} with {told_who(case, row['host'])}"
        if row['status'] == 'skipped':
            made = next((other for other in rows if other['reason'] == 'make-up' and other['extra'] == row['id'] and
                         other['status'] == 'planned'), None)
            text = (f"- {what} on {day_span(row)} is off this time; {child_word(kids, 'they')} "
                    f"{verb(kids, 'stays', 'stay')} with {resident(case, row['host'])} "
                    'then.' + (f' It is made up {day_span(made)}.' if made else ''))
            result.append((f"stay:{row['id']}:skipped", text))
        elif row['moved_reason'] == 'user':
            result.append((f"stay:{row['id']}:moved:{row['start_date']}",
                           f"- {what} moved from {first_span(row)} to {day_span(row)}."))
    return result


# The screens -------------------------------------------------------------------------------------------------------------

def shown_who(case: Case, host: str, companion: dict) -> str:
    return {YOU: 'you', COMPANION: first(companion['version']['definition']['name'])}.get(host, case.other)


def item_line(case: Case, row: dict, companion: dict) -> str:
    """Under the title: where it is and the handover, or why the app planned it."""
    name, them = first(companion['version']['definition']['name']), child_word(children_of(case, row), 'them')
    if row['travels'] == 'child':
        return f"In {row['city_name']}, with a handover at the station" if row['city_name'] else \
            'A handover at the station'
    if row['travels'] == 'you':
        return f"In {row['city_name']}: you go to see {them}"
    if row['travels'] == 'companion':
        return f"In {row['city_name']}: {name} comes to see {them}"
    return {'make-up': 'Making up for the one skipped', 'asked': 'You asked for it in the chat'}.get(row['reason'], '')


def item_view(case: Case, row: dict, companion: dict, today: date, made_up: str | None = None) -> dict:
    """A stay in the shape of a calendar entry (companion/life/admin.py `item_view`), with what the user can do."""
    kids = children_of(case, row)
    moved = row['moved_reason'] == 'user' and row['first_start'] != row['start_date']
    return {'id': f"stay:{row['id']}", 'key': row['key'], 'source': 'family', 'kind': row['reason'],
            'title': f"{possessive(names(kids))} {noun(row)} with {shown_who(case, row['host'], companion)}",
            'line': item_line(case, row, companion), 'local_date': row['start_date'], 'end_date': row['end_date'],
            'at_time': '', 'until': '', 'fixed': False, 'status': row['status'], 'place': '',
            'moved_from': row['first_start'] if moved else None, 'moved_reason': 'moved by you' if moved else '',
            'moves': int(moved), 'deadline': None, 'cost_text': '', 'movable': False, 'detail': '',
            'stay': {'id': row['id'], 'status': row['status'],
                     'can_change': row['status'] == 'planned' and still_to_come(row, today),
                     'undo': row['status'] == 'skipped' and still_to_come(row, today), 'made_up': made_up}}


def items(connection, companion: dict, now: datetime, days: int = AHEAD) -> list[dict]:
    """Every case's stays from today to `days` ahead, skipped ones included, for the calendar and Today."""
    today = steps.local_today(companion, now)
    until = (today + timedelta(days=days)).isoformat()
    result = []
    for case in cases(connection, companion, today):
        rows = rows_for(connection, companion['active_timeline_id'], case.family, case.subject)
        made = {row['extra']: row['start_date'] for row in rows if row['reason'] == 'make-up' and
                row['status'] == 'planned'}
        for row in rows:
            if row['end_date'] >= today.isoformat() and row['start_date'] <= until:
                result.append(item_view(case, row, companion, today, made.get(row['id'])))
    return sorted(result, key=lambda item: item['local_date'])
