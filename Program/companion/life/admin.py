"""Life admin calendar (Hit List #23): the boring stuff happens too.

The dentist every six months, the car inspection, the lease renewal and taxes in April, plus the week's errands and
paperwork, all decided without a model. What comes due follows the city's country and era
(companion/world/data/life_admin.json, keyed by the city's holiday calendar): taxes are due April 15 in the US and
March 15 in the 1920s, Japan has a residence tax notice in June, a car needs its MOT in London and its smog check in
Los Angeles, and Victorian London pays rent on the quarter days. A city with no cars has no car inspection, and nobody
files taxes in Camelot. The week's errands and paperwork are seeded draws from the banks in the same file, and on
Bring on the drama a surprise now and then (a parking ticket, a bank error to sort out).

This is also where the other home features put the time things take on a day: vet visits (Pets), chores (Home
upkeep), grocery runs (Kitchen) and haircuts (Looks) all come through `add`, so there is one calendar.

An entry takes a slot in the companion's agenda (companion/life/agenda.py) the way outings do, so the life simulation
tells it as an event, and the chat context sees it in their next day's plans. It never lands on, or cancels, a plan
with the user, a trip away or a family tradition: it moves to the nearest free time instead (`place`). What gives way to a
new plan with the user follows the Life admin slider (`stands`): on Off and Light everything moves for the user; on
True to life an appointment booked with someone else (`fixed`) holds its time, so an outing asked for then goes to
another day and the companion says so (companion/life/outings.py); on Dramatic anything due that very day holds too.
Chores and paperwork always move. The user overrides any of it by moving the entry to another day themselves. Someone who leaves things to the
last minute puts off a chore now and then, never past its deadline.

Only the companion is tracked: circle members and townsfolk have no calendar. Costs are counted in money.household when
an entry is done (`purchases`). The Realism tab's Life admin slider (on the home features' shared scale) sets how much there
is: off, light (only what comes due), true to life, or dramatic (more errands, and surprises).
"""
import json
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

from companion.clock import stamp, zone
from companion.database import decode, encode, identifier, many, optional
from companion.errors import require
from companion.life import home, money, outings, own_plans, routine, traditions, trips
from companion.world import catalog, generators

DATA = Path(__file__).parents[1] / 'world' / 'data' / 'life_admin.json'
# Seeded appointments, errands and surprises; their tests turn them on (tests/conftest.py turns them off).
ACTIVE = True
SOURCES = ('admin', 'pets', 'upkeep', 'kitchen', 'looks')
AHEAD = 21  # Days planned ahead, so Today shows what is coming.
MOVE_DAYS = 14  # How far an entry may move to find a free time.
LATER = 365  # How far the Character page looks for what comes due later.
OFFICE = ('08:00', '18:00')  # Appointments out happen in opening hours.
BUSY = {'work', 'study', 'sleep'}
# The home features' shared realism scale: 0 off, 1 light (only what comes due), 2 true to life, 3 dramatic.
LEVELS = (0, 1, 2, 3)
DEFAULT_LEVEL = 2
# Per week, by level: (chance of a first errand or piece of paperwork, of a second, of a third, of a surprise).
WEEKLY = {0: (0.0, 0.0, 0.0, 0.0), 1: (0.0, 0.0, 0.0, 0.0), 2: (0.85, 0.35, 0.0, 0.08), 3: (1.0, 0.8, 0.45, 0.35)}
# How far ahead of a deadline it gets done, in days (earliest, latest), by habit.
LEAD = {'organised': (21, 45), 'average': (5, 18), 'scattered': (0, 3)}
# The chance a chore gets put off when its day comes, by habit, on each level (never on Easy life's light level).
PUT_OFF = {'organised': 0.0, 'average': 0.12, 'scattered': 0.35}
MAX_PUT_OFF = 2
ORGANISED = ('organi', 'punctual', 'meticulous', 'methodical', 'disciplined', 'responsible', 'reliable', 'careful',
             'diligent', 'conscientious', 'practical', 'efficient', 'orderly', 'tidy', 'neat', 'planner', 'prepared')
SCATTERED = ('scatter', 'messy', 'chaotic', 'forgetful', 'absent', 'impulsive', 'spontaneous', 'carefree', 'lazy',
             'procrastinat', 'disorgan', 'dreamy', 'flaky', 'easygoing', 'easy-going', 'laid-back', 'laid back',
             'distracted', 'unreliable', 'last-minute', 'last minute', 'reckless')
HABIT_WORDS = {'organised': 'Gets things done early.', 'average': 'Gets things done in time, mostly.',
               'scattered': 'Leaves things to the last minute.'}
METER = {'organised': 85, 'average': 60, 'scattered': 35}
CAPTIONS = ('One less thing.', 'Crossed off the list.', 'Adulting.', 'Done and dusted.',
            'That was the boring part of the week.', 'Finally.')
ERA_GROUPS = {'modern': 'modern', 'future': 'modern', 'other': 'modern', 'jazz-age': 'industrial',
              'victorian': 'industrial', 'steampunk': 'industrial', 'frontier': 'industrial'}
# Place kinds an entry can name a real place of; a shop or workshop could be any kind, so those stay unnamed.
NAMED_PLACES = {'library', 'market', 'guildhall', 'temple', 'docks', 'fitness', 'park', 'cafe'}
REASONS = {'clash': 'moved for a plan', 'put-off': 'put off', 'user': 'moved by you', 'away': 'moved for a trip'}


@lru_cache(maxsize=1)
def data() -> dict:
    return json.loads(DATA.read_text(encoding='utf-8'))


def era_group(city: dict | None) -> str:
    return ERA_GROUPS.get(city['era'], 'old') if city else 'modern'


def rules_for(city: dict | None) -> list[dict]:
    """The recurring appointments and deadlines a city's country and era keep, filtered to its region."""
    calendars = data()['calendars']
    key = catalog.calendar_id(city) if city else None
    found = calendars.get(key) if key else None
    if found is None:
        found = calendars.get(era_group(city), [])
    region = (city or {}).get('region', '')
    return [rule for rule in found if (not rule.get('regions') or region in rule['regions'])
            and region not in rule.get('except_regions', ())]


def habit(definition: dict) -> str:
    """'organised', 'average' or 'scattered', from the words of their personality, skills and flaws."""
    words = ' '.join([definition.get('personality', ''), *definition.get('skills', ()),
                      *definition.get('flaws', ())]).lower()
    tidy, messy = sum(stem in words for stem in ORGANISED), sum(stem in words for stem in SCATTERED)
    return 'organised' if tidy > messy else 'scattered' if messy > tidy else 'average'


def level(connection) -> int:
    row = optional(connection, 'SELECT admin_realism FROM life_settings WHERE id=1')
    return row['admin_realism'] if row and row['admin_realism'] in LEVELS else DEFAULT_LEVEL


def local_now(companion: dict, now: datetime) -> datetime:
    return now.astimezone(zone(companion['version']['timezone']))


# --- Where an entry fits ---

def minutes_of(at: str) -> int:
    return int(at[:2]) * 60 + int(at[3:5])


def clock(total: int) -> str:
    total = max(0, min(total, 23 * 60 + 59))
    return f'{total // 60:02d}:{total % 60:02d}'


def free_blocks(schedule, day: date) -> list[dict]:
    return [block.view() for block in schedule if day.weekday() in block.days and block.kind not in BUSY]


def time_in(block: dict, at: str | None, office: bool, jitter: float = 0.0) -> str | None:
    """The time in a block an entry starts: the time asked when the block holds it, else a seeded half hour from half
    an hour in to an hour and a half before it ends; an appointment out keeps to opening hours."""
    if at and own_plans.holds(block, at):
        return at
    start, end = minutes_of(block['start']), minutes_of(block['end'])
    end = end if end > start else 24 * 60
    low = start + 30 if end - start > 60 else start
    high = max(low, end - 90)
    if office:
        low, high = max(low, minutes_of(OFFICE[0]) + 30), min(high, minutes_of(OFFICE[1]) - 30)
        if low >= min(end, minutes_of(OFFICE[1])):
            return None
        high = max(low, high)
    return clock(low + int(jitter * ((high - low) // 30 + 1)) * 30)


class Taken:
    """What already holds the companion's days from one date on: trips and traditions take whole days, plans with the
    user, their own plans and other entries take the block their time falls in, and public holidays close offices."""

    def __init__(self, connection, companion: dict, start: date, days: int, skip: str | None = None):
        timeline_id, definition = companion['active_timeline_id'], companion['version']['definition']
        end = start + timedelta(days=days)
        self.schedule = routine.blocks(definition)[0]
        self.away = set(trips.by_date(connection, timeline_id, start.isoformat()))
        city = traditions.city_for(connection, definition)
        self.away |= set(traditions.on_dates(connection, companion, city, start, end)) if city else set()
        data_city = outings.city_data(connection, definition)
        self.closed = {item['date'] for item in generators.holidays(data_city, start, end)
                       if item['kind'] == 'public'} if data_city else set()
        self.times: dict[str, list[str]] = {}
        for plan in own_plans.in_force(connection, timeline_id, start.isoformat()):
            self.times.setdefault(plan['local_date'], []).append(plan['at_time'] or '19:00')
        for outing in outings.in_force(connection, timeline_id, start.isoformat()):
            self.times.setdefault(outing['local_date'], []).append(outing['at_time'])
        self.entries: dict[str, list[str]] = {}
        self.jitter = 0.0  # Where in a free block an entry goes (time_in), seeded by the caller.
        for row in many(connection, "SELECT id, local_date, at_time FROM life_admin WHERE timeline_id=? AND "
                        "status='planned' AND local_date>=?", (timeline_id, start.isoformat())):
            if row['id'] != skip:
                self.entries.setdefault(row['local_date'], []).append(row['at_time'])

    def held(self, day: date, block: dict, by_user_only: bool = False) -> bool:
        local = day.isoformat()
        times = self.times.get(local, []) + ([] if by_user_only else self.entries.get(local, []))
        return any(own_plans.holds(block, at) for at in times)

    def blocked(self, day: date, out: bool) -> bool:
        return day.isoformat() in self.away or out and day.isoformat() in self.closed

    def claim(self, day: date, at: str):
        self.entries.setdefault(day.isoformat(), []).append(at)

    def fits(self, day: date, at: str | None, out: bool, fixed: bool) -> str | None:
        """The time on this day an entry can have, or None."""
        if self.blocked(day, out):
            return None
        office = out and fixed
        for block in free_blocks(self.schedule, day):
            if fixed and at and not own_plans.holds(block, at):
                continue
            found = time_in(block, at, office, self.jitter)
            if found and not self.held(day, block):
                return found
        return None


def place(taken: Taken, day: date, at: str | None, out: bool, fixed: bool, earliest: date,
          deadline: date | None = None) -> tuple[date, str] | None:
    """The nearest free time from `day` on (a booked time keeps its hour if it can), never after a deadline: then the
    days before it, back to `earliest`."""
    days = [day + timedelta(days=offset) for offset in range(MOVE_DAYS + 1)]
    if deadline:
        days = [found for found in days if found <= deadline]
        days += [deadline - timedelta(days=offset) for offset in range(1, MOVE_DAYS + 1)
                 if earliest <= deadline - timedelta(days=offset) < day]
    for candidate in days:
        for wanted in dict.fromkeys((at, None) if not fixed else (at,)):
            found = taken.fits(candidate, wanted, out, fixed)
            if found:
                return candidate, found
    if fixed and at:  # Nowhere at that hour: any free time with the office open.
        return place(taken, day, None, out, True, earliest, deadline)
    return None


# --- Adding entries (the shared way in for Pets, Home upkeep, Kitchen and Looks) ---

def add(connection, companion: dict, *, key: str, source: str, kind: str, title: str, done: str, day: date,
        at: str | None = None, minutes: int = 60, fixed: bool = False, place_item: dict | None = None,
        cost: float = 0.0, now: datetime, spend: str = '', line: str = '', deadline: date | None = None,
        out: bool | None = None) -> dict | None:
    """Put something on the companion's calendar, at the nearest free time from `day` (and `at`, 'HH:MM'). The same
    `key` twice returns the entry already there. `done` is what they did, said after their name ("took Biscuit to the
    vet"). `fixed` is for times booked with someone else, which hold their hour; anything else moves out of the way of
    plans. `cost` is in the city's currency (or `spend`, a price tier), counted once it is done. None when no free
    time is found within two weeks; nothing is cancelled to make room."""
    require(source in SOURCES, 'Unknown life admin source.', 400)
    timeline_id = companion['active_timeline_id']
    found = optional(connection, 'SELECT * FROM life_admin WHERE timeline_id=? AND key=?', (timeline_id, key))
    if found:
        return view(found)
    today = local_now(companion, now).date()
    out = bool(place_item) or fixed if out is None else out
    taken = Taken(connection, companion, min(day, today), MOVE_DAYS * 2)
    taken.jitter = generators.unit(key, 'time')
    spot = place(taken, max(day, today), at, out, fixed, today, deadline)
    if spot is None:
        return None
    entry_id = identifier()
    connection.execute(
        'INSERT INTO life_admin (id, timeline_id, key, source, kind, title, done_text, line, local_date, at_time, '
        'first_date, deadline, minutes, fixed, out_of_home, place, cost, spend, created_at, updated_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (entry_id, timeline_id, key, source, kind, title[:120], done[:240], line[:240], spot[0].isoformat(), spot[1],
         day.isoformat(), deadline.isoformat() if deadline else None, max(5, min(int(minutes), 600)), int(fixed),
         int(out), encode(place_item) if place_item else None, round(float(cost), 2), spend, stamp(now), stamp(now)))
    return get(connection, entry_id)


def remove(connection, timeline_id: str, key: str) -> bool:
    """Take a planned entry off the calendar (a pet that died, a chore no longer needed). Done ones stay."""
    return connection.execute("UPDATE life_admin SET status='removed' WHERE timeline_id=? AND key=? AND "
                              "status='planned'", (timeline_id, key)).rowcount > 0


def get(connection, entry_id: str) -> dict:
    row = optional(connection, 'SELECT * FROM life_admin WHERE id=?', (entry_id,))
    require(row is not None, 'That calendar entry could not be found.', 404)
    return view(row)


def view(row: dict) -> dict:
    return {**row, 'place': decode(row['place']) if row['place'] else None, 'fixed': bool(row['fixed']),
            'out_of_home': bool(row['out_of_home'])}


def upcoming(connection, timeline_id: str, since: str, until: str | None = None) -> list[dict]:
    """Planned entries from `since` (a local date) to `until`, in time order."""
    rows = many(connection, "SELECT * FROM life_admin WHERE timeline_id=? AND status='planned' AND local_date>=? "
                'AND local_date<=? ORDER BY local_date, at_time', (timeline_id, since, until or '9999-12-31'))
    return [view(row) for row in rows]


def ends(item: dict) -> str:
    return clock(minutes_of(item['at_time']) + item['minutes'])


def stands(item: dict, chosen: int) -> bool:
    """Whether an entry holds its time against a new plan with the user, by the Life admin slider: nothing does on
    Off or Light, an appointment booked with someone else does on True to life, and on Dramatic so does anything due
    that very day (taxes on the 15th)."""
    if chosen < 2:
        return False
    return item['fixed'] or (chosen >= 3 and item['deadline'] == item['local_date'])


def holds(connection, companion: dict, day: date, at: str) -> bool:
    """Whether an entry that stands (`stands`) has the part of the day this time falls in (an outing asked for then
    goes to another day, and the companion says so)."""
    schedule = routine.blocks(companion['version']['definition'])[0]
    block = next((block for block in free_blocks(schedule, day) if own_plans.holds(block, at)), None)
    chosen = level(connection)
    return bool(block) and any(stands(item, chosen) and own_plans.holds(block, item['at_time']) for item in upcoming(
        connection, companion['active_timeline_id'], day.isoformat(), day.isoformat()))


def make_room(connection, companion: dict, day: date, at: str, now: datetime) -> int:
    """A new plan with the user has this time: whatever in the block it falls in does not stand (`stands`) moves to
    another time."""
    taken = Taken(connection, companion, local_now(companion, now).date(), MOVE_DAYS * 2)
    chosen, moved = level(connection), 0
    for item in upcoming(connection, companion['active_timeline_id'], day.isoformat(), day.isoformat()):
        if stands(item, chosen):
            continue
        block = next((block for block in free_blocks(taken.schedule, day) if own_plans.holds(block, item['at_time'])),
                     None)
        if block and own_plans.holds(block, at):
            moved += move(connection, companion, item, 'clash', now, day)
    return moved


def move(connection, companion: dict, item: dict, reason: str, now: datetime, after: date | None = None,
         days: int = 0) -> int:
    """Move an entry to the nearest free time, `days` on from `after` (its own day). 0 when nowhere is free: it
    stays where it is rather than going."""
    today = local_now(companion, now).date()
    taken = Taken(connection, companion, today, MOVE_DAYS * 2, skip=item['id'])
    taken.jitter = generators.unit(item['key'], 'time', item['moves'])
    current = date.fromisoformat(item['local_date'])
    start = max((after or current) + timedelta(days=days), today)
    deadline = date.fromisoformat(item['deadline']) if item['deadline'] else None
    keep = item['at_time'] if item['fixed'] else None
    spot = place(taken, start, keep, item['out_of_home'], item['fixed'], today, deadline)
    if spot is None or (spot[0].isoformat(), spot[1]) == (item['local_date'], item['at_time']):
        return 0
    connection.execute('UPDATE life_admin SET local_date=?, at_time=?, moved_from=COALESCE(moved_from, ?), '
                       'moved_reason=?, moves=moves+1, revision=revision+1, updated_at=? WHERE id=?',
                       (spot[0].isoformat(), spot[1], item['local_date'], reason, stamp(now), item['id']))
    return 1


def user_move(connection, companion: dict, entry_id: str, now: datetime) -> dict:
    """The user moves an entry to another day: the nearest free time from the next day on."""
    item = get(connection, entry_id)
    require(item['timeline_id'] == companion['active_timeline_id'] and item['status'] == 'planned',
            'Only something still to do can move.', 409)
    require(move(connection, companion, item, 'user', now, days=1) > 0,
            'There is no free time for it in the next two weeks.', 409)
    return get(connection, entry_id)


# --- Seeded appointments, deadlines, errands and surprises ---

def owns(definition: dict, connection, timeline_id: str, day: date) -> set[str]:
    """What the companion has that some admin needs: a car, a horse, a rented home, glasses, a job."""
    found = set()
    for item in home.items_on(connection, timeline_id, day):
        if item['kind'] == 'vehicle' and item['variety'] in ('car', 'motorcar', 'horse'):
            found.add('horse' if item['variety'] == 'horse' else 'car')
        if item['kind'] == 'home' and (item.get('rent') or money.profile(definition)):
            found.add('rent')
    looks_text = ' '.join([definition.get('appearance', ''), definition.get('in_photos', ''),
                           json.dumps(definition.get('looks') or {})]).lower()
    if any(word in looks_text for word in ('glasses', 'spectacles', 'contact lens')):
        found.add('glasses')
    if any(block['kind'] == 'work' for block in definition.get('schedule') or ()):
        found.add('work')
    return found


def next_on(month_day: str, today: date) -> date:
    month, day = int(month_day[:2]), int(month_day[3:])
    for year in (today.year, today.year + 1):
        try:
            found = date(year, month, day)
        except ValueError:
            found = date(year, month, 28)
        if found >= today:
            return found
    return today


def occurrences(rule: dict, seed: str, start: date, end: date) -> list[tuple[date, date | None]]:
    """(day it is planned for, its deadline) for each time a rule comes due between two dates."""
    found = []
    if rule.get('every_months'):
        period = round(rule['every_months'] * 30.44)
        base = date(2000, 1, 1)
        phase = int(generators.unit(seed, 'phase', rule['id']) * period)
        step = -(-((start - base).days - phase) // period)
        day = base + timedelta(days=phase + step * period)
        while day <= end:
            found.append((day, None))
            day += timedelta(days=period)
    for month_day in [*([rule['on']] if rule.get('on') else []), *rule.get('on_days', ())]:
        due = next_on(month_day, start)
        while due <= end + timedelta(days=max(LEAD['organised'])):
            found.append((due, due))
            due = next_on(month_day, due + timedelta(days=1))
    return found


def planned_day(rule: dict, day: date, due: date | None, seed: str, kind: str) -> date:
    if not (rule.get('lead') and due):
        return day
    low, high = LEAD[kind]
    return due - timedelta(days=low + int(generators.unit(seed, 'lead', rule['id'], due) * (high - low + 1)))


def plan_rules(connection, companion: dict, city: dict | None, seed: str, today: date, now) -> int:
    definition, timeline_id = companion['version']['definition'], companion['active_timeline_id']
    has, kind, added = owns(definition, connection, timeline_id, today), habit(definition), 0
    for rule in rules_for(city):
        if rule.get('needs') and rule['needs'] not in has:
            continue
        for day, due in occurrences(rule, seed, today, today + timedelta(days=AHEAD + max(LEAD['organised']))):
            target = planned_day(rule, day, due, seed, kind)
            if not today <= target <= today + timedelta(days=AHEAD):
                continue
            added += bool(add(connection, companion, key=f"admin:{rule['id']}:{(due or day).isoformat()}",
                              source='admin', kind=rule['id'], title=rule['title'], done=rule['done'], day=target,
                              minutes=rule['minutes'], fixed=rule['fixed'], spend=rule['cost'], deadline=due, now=now,
                              cost=priced(definition, rule['cost'], f"{seed}:{rule['id']}:{day.isoformat()}"),
                              place_item=city_place(city, rule['where'], seed, rule['id']),
                              out=rule['where'] != 'home'))
    return added


def city_place(city: dict | None, where: str, seed: str, label: str) -> dict | None:
    """A real place of that kind in their city, when the entry happens at one."""
    if not city or where not in NAMED_PLACES:
        return None
    found = generators.pick(seed, f'place:{label}', [item for item in city['places'] if item['kind'] == where])
    if not found:
        return None
    hoods = {hood['id']: hood['name'] for hood in city['neighborhoods']}
    return {'id': found['id'], 'name': found['name'], 'kind': found['kind'],
            'neighborhood': hoods.get(found.get('neighborhood'), '')}


def priced(definition: dict, spend: str, seed: str) -> float:
    """A price tier as an amount in their city's money, a seeded 60% to 140% of the tier's share of a month's pay, so
    two small bills are not the same to the cent. 0 where money does not apply."""
    found = money.profile(definition)
    if not found or not spend:
        return 0.0
    share = money.PURCHASES.get(spend, 0) * money.monthly_share(found) * (0.6 + 0.8 * generators.unit(seed, 'price'))
    return round(share, 0 if share >= 20 else 2)


def recent_titles(connection, timeline_id: str, around: date) -> set[str]:
    """Titles on the calendar within eight weeks either side, so a week's draw does not repeat one."""
    rows = many(connection, 'SELECT title FROM life_admin WHERE timeline_id=? AND first_date>=? AND first_date<=?',
                (timeline_id, (around - timedelta(weeks=8)).isoformat(), (around + timedelta(weeks=8)).isoformat()))
    return {row['title'] for row in rows}


def bank(name: str, group: str, has: set[str], payable: bool) -> list[dict]:
    return [item for item in data()[name] if group in item['eras'] and (not item.get('needs') or item['needs'] in has)
            and (payable or not item['cost'])]


def plan_week(connection, companion: dict, city: dict | None, seed: str, monday: date, today: date, chances,
              now) -> int:
    """One week's errands, paperwork and maybe a surprise, on seeded days."""
    definition, timeline_id = companion['version']['definition'], companion['active_timeline_id']
    has, group = owns(definition, connection, timeline_id, today), era_group(city)
    payable = bool(money.profile(definition)) or city is None
    week, added = f'{seed}:{monday.isoformat()}', 0
    for index, chance in enumerate(chances):
        surprise = index == 3
        if generators.unit(week, 'roll', index) >= chance:
            continue
        name = 'surprises' if surprise else generators.pick(week, f'bank:{index}', ['errands', 'paperwork'])
        used = recent_titles(connection, timeline_id, monday)
        item = generators.pick(week, f'item:{index}', [found for found in bank(name, group, has, payable)
                                                       if found['title'] not in used])
        day = monday + timedelta(days=int(generators.unit(week, 'day', index) * 7))
        if not item or not today <= day <= today + timedelta(days=AHEAD):
            continue
        added += bool(add(connection, companion, key=f'admin:{name}:{monday.isoformat()}:{index}', source='admin',
                          kind=name.rstrip('s'), title=item['title'], done=item['done'], day=day,
                          minutes=item['minutes'], fixed=item['fixed'], spend=item['cost'], line=item.get('line', ''),
                          cost=priced(definition, item['cost'], f'{week}:{index}'),
                          place_item=city_place(city, item['where'], week, str(index)), out=item['where'] != 'home',
                          now=now))
    return added


def put_off(connection, companion: dict, today: date, chance: float, now) -> int:
    """Chores due today or tomorrow that get put off, by their habit: a day to three later, at most twice, never past
    a deadline. Seeded by the entry and how often it moved, so the same day always goes the same way."""
    if not chance:
        return 0
    moved = 0
    for item in upcoming(connection, companion['active_timeline_id'], today.isoformat(),
                         (today + timedelta(days=1)).isoformat()):
        if item['fixed'] or item['source'] != 'admin' or item['moves'] >= MAX_PUT_OFF:
            continue
        roll = f"{item['key']}:{item['moves']}"
        if generators.unit(roll, 'put-off') >= chance:
            continue
        later = 1 + int(generators.unit(roll, 'days') * 3)
        if item['deadline'] and date.fromisoformat(item['local_date']) + timedelta(days=later) > \
                date.fromisoformat(item['deadline']):
            continue
        moved += move(connection, companion, item, 'put-off', now, days=later)
    return moved


def reflow(connection, companion: dict, today: date, now) -> int:
    """Entries that a plan with the user, their own plan, a trip or a tradition now takes move to another time."""
    taken = Taken(connection, companion, today, MOVE_DAYS * 2)
    moved = 0
    for item in upcoming(connection, companion['active_timeline_id'], today.isoformat()):
        day = date.fromisoformat(item['local_date'])
        block = next((block for block in free_blocks(taken.schedule, day)
                      if own_plans.holds(block, item['at_time'])), None)
        away = day.isoformat() in taken.away
        if away or block is None or taken.held(day, block, by_user_only=True):
            moved += move(connection, companion, item, 'away' if away else 'clash', now, day)
    return moved


def finish_due(connection, companion: dict, now) -> int:
    """Entries whose time has passed are done (their cost is then counted)."""
    local = local_now(companion, now)
    done = 0
    for item in upcoming(connection, companion['active_timeline_id'], '0000-01-01', local.date().isoformat()):
        if item['local_date'] < local.date().isoformat() or ends(item) <= local.strftime('%H:%M'):
            connection.execute("UPDATE life_admin SET status='done', updated_at=? WHERE id=?",
                               (stamp(now), item['id']))
            done += 1
    return done


def from_home(connection, companion: dict, world, today: date, now) -> int:
    """The other home features' time-taking items on this calendar, each added once (by the feature's own key).
    Home upkeep's big cleans (laundry takes no real time and stays off); the feature has already kept them off plans
    with the user."""
    from companion.life import upkeep
    definition, timeline_id = companion['version']['definition'], companion['active_timeline_id']
    if not getattr(upkeep, 'chores_between', None) or not upkeep.level(connection):
        return 0
    upkeep.ensure(connection, timeline_id, definition, world, now)
    added = 0
    for chore in upkeep.chores_between(connection, timeline_id, definition, today, today + timedelta(days=AHEAD)):
        if chore['kind'] == 'big-clean':
            added += bool(add(connection, companion, key=upkeep.big_clean_key(chore['date']), source='upkeep',
                              kind='big-clean', title='Big clean', done='did a big clean', minutes=180,
                              day=date.fromisoformat(chore['date']), out=False, now=now))
    return added


def plan_ahead(connection, companion: dict, world, now) -> dict:
    """Called each time the agenda extends: finish what is over, plan the next three weeks, move what clashes and
    what gets put off. Cheap: no model."""
    finished = finish_due(connection, companion, now)
    today = local_now(companion, now).date()
    added = 0
    chosen = level(connection)
    if ACTIVE:
        added += from_home(connection, companion, world, today, now)
    if ACTIVE and chosen:
        definition = companion['version']['definition']
        # What they own (a car, a rented home) decides some of it, so the home is assembled first.
        home.ensure(connection, companion['active_timeline_id'], definition, world, now)
        city = outings.city_data(connection, definition)
        seed = f"admin:{companion['active_timeline_id']}"
        added += plan_rules(connection, companion, city, seed, today, now)
        monday = today - timedelta(days=today.weekday())
        for week in range(0, AHEAD // 7 + 1):
            added += plan_week(connection, companion, city, seed, monday + timedelta(weeks=week), today,
                               WEEKLY[chosen], now)
    moved = reflow(connection, companion, today, now)
    if ACTIVE and chosen >= 2:
        moved += put_off(connection, companion, today, PUT_OFF[habit(companion['version']['definition'])], now)
    return {'finished': finished, 'added': added, 'moved': moved}


# --- The agenda ---

def as_plans(connection, timeline_id: str, since: str) -> dict[str, list[dict]]:
    """Planned entries by local date in the shape own_plans.assign takes. The id changes when the entry moves, so the
    agenda composes the slot again."""
    result = {}
    for item in [*upcoming(connection, timeline_id, since), *[
            view(row) for row in many(connection, "SELECT * FROM life_admin WHERE timeline_id=? AND status='done' "
                                      'AND local_date>=?', (timeline_id, since))]]:
        result.setdefault(item['local_date'], []).append(
            {'id': f"admin:{item['id']}:{item['revision']}", 'at_time': item['at_time'], 'admin': item})
    return result


def doing(item: dict) -> str:
    """'returned three library books at Enoch Pratt Free Library'."""
    place_item, text = item['place'], item['done_text'].rstrip('.')
    if place_item and place_item['name'].lower() not in text.lower():
        text += f" at {place_item['name']}"
    return text


def entry(plan: dict, block: dict, definition: dict) -> dict:
    """The agenda entry for the slot an entry takes: it happening."""
    item = plan['admin']
    summary = f"{definition['name']} {doing(item)}."
    if item['line']:
        summary = f"{item['line'].rstrip('.')}. {summary}"
    return {'summary': summary, 'post': generators.pick(item['key'], 'admin-post', list(CAPTIONS)),
            'mood': 'content', 'activity': routine.slug(item['title']), 'place': item['place'], 'with': None,
            'weather': block.get('weather'),
            'admin': {'id': item['id'], 'key': item['key'], 'source': item['source'], 'at': item['at_time'],
                      'until': ends(item)}, 'composer_version': 'admin-1'}


# --- Money ---

def purchases(connection, timeline_id: str, start: date, day: date) -> list[dict]:
    """Done entries this pay period with a cost, as money.household purchases."""
    rows = many(connection, "SELECT * FROM life_admin WHERE timeline_id=? AND status='done' AND local_date>=? AND "
                "local_date<=? AND (cost>0 OR spend!='')", (timeline_id, start.isoformat(), day.isoformat()))
    return [{'text': row['title'][:1].lower() + row['title'][1:], 'date': row['local_date'], 'spend': row['spend'],
             'cost': row['cost'] or None, 'for': 'admin'} for row in rows]


# --- What Today and the Character page show ---

def day_text(local_date: str) -> str:
    return date.fromisoformat(local_date).strftime('%A, %B %d').replace(' 0', ' ')


def item_view(item: dict, definition: dict) -> dict:
    found = money.profile(definition)
    cost = item['cost'] or (money.PURCHASES.get(item['spend'], 0) * money.monthly_share(found) if found else 0)
    return {'id': item['id'], 'key': item['key'], 'source': item['source'], 'kind': item['kind'],
            'title': item['title'], 'line': item['line'], 'local_date': item['local_date'], 'at_time': item['at_time'],
            'until': ends(item), 'fixed': item['fixed'], 'status': item['status'],
            'place': item['place']['name'] if item['place'] else '',
            'moved_from': item['moved_from'], 'moved_reason': REASONS.get(item['moved_reason'] or '', ''),
            'moves': item['moves'], 'deadline': item['deadline'],
            'cost_text': money.amount(cost, found.city['currency']) if found and cost else '', 'movable': True}


def shown_item(key: str, source: str, kind: str, title: str, day: str, today: date, cost_text: str = '',
               fixed: bool = True) -> dict:
    """Another home feature's item, in the shape of an entry, shown read-only: it follows that feature's own draw and
    Realism setting, has no set hour here, and its cost is counted by that feature."""
    return {'id': key, 'key': key, 'source': source, 'kind': kind, 'title': title, 'line': '', 'local_date': day,
            'at_time': '', 'until': '', 'fixed': fixed, 'status': 'planned' if day >= today.isoformat() else 'done',
            'place': '', 'moved_from': None, 'moved_reason': '', 'moves': 0, 'deadline': None, 'cost_text': cost_text,
            'movable': False}


def home_items(connection, companion: dict, start: date, end: date, now=None) -> list[dict]:
    """Pets' vet visits (companion/life/pets.py), Looks' haircuts, colours, nails and eye tests
    (companion/life/grooming.py) and Kitchen's grocery runs (companion/life/kitchen.py, once its kitchen exists: this
    only reads), alongside this calendar's own entries."""
    from companion.life import grooming, kitchen, pets
    timeline_id = companion['active_timeline_id']
    profile = money.profile(companion['version']['definition'])
    found = []
    for visit in getattr(pets, 'vet_visits', lambda *_args: [])(connection, timeline_id, start, end):
        title = f"Vet {'check-up' if visit['kind'] == 'checkup' else 'visit'} for {visit['pet']}"
        found.append(shown_item(f"pets:{visit['kind']}:{visit['pet_id']}:{visit['date']}", 'pets', visit['kind'],
                                title, visit['date'], start))
    for item in getattr(grooming, 'appointments', lambda *_args: [])(connection, timeline_id, start, end):
        cost = money.PURCHASES.get(item.get('spend') or '', 0) * money.monthly_share(profile) if profile else 0
        found.append(shown_item(f"looks:{item['kind']}:{item['date']}", 'looks', item['kind'], item['title'],
                                item['date'], start, money.amount(cost, profile.city['currency']) if cost else ''))
    runs = getattr(kitchen, 'grocery_runs', None)
    if runs and now and optional(connection, 'SELECT 1 FROM kitchen_state WHERE timeline_id=?', (timeline_id,)):
        for run in runs(connection, timeline_id, start, end, companion['version']['definition'], None, now):
            found.append(shown_item(f"kitchen:groceries:{run['date']}", 'kitchen', 'groceries', run['text'],
                                    run['date'], start, fixed=False))
    return found


def by_day(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda item: (item['local_date'], item['at_time'] or '99:99'))


def later(connection, companion: dict, city: dict | None, today: date) -> list[dict]:
    """What comes due after the next three weeks, within a year: one line per kind, soonest first."""
    definition, seed = companion['version']['definition'], f"admin:{companion['active_timeline_id']}"
    has, result = owns(definition, connection, companion['active_timeline_id'], today), {}
    start = today + timedelta(days=AHEAD + 1)
    for rule in rules_for(city):
        if rule.get('needs') and rule['needs'] not in has:
            continue
        found = occurrences(rule, seed, start, today + timedelta(days=LATER))
        if found and rule['id'] not in result:
            day, due = found[0]
            result[rule['id']] = {'kind': rule['id'], 'title': rule['title'], 'local_date': day.isoformat(),
                                  'due': bool(due)}
    return sorted(result.values(), key=lambda item: item['local_date'])


GIVES_WAY = {0: 'Plans with you always come first.', 1: 'Plans with you always come first.',
             2: 'Plans with you come first, except appointments booked with someone else.',
             3: 'Appointments and anything due that day hold; everything else moves for plans with you.'}


def state_lines(items: list[dict], kind: str, today: date, chosen: int = DEFAULT_LEVEL) -> list[str]:
    """Their admin in plain words ("Taxes are due April 15.")."""
    week = [item for item in items if item['local_date'] <= (today + timedelta(days=6)).isoformat()]
    lines = [f"{len(week)} thing{'s' if len(week) != 1 else ''} on the list this week." if week
             else 'Nothing on the list this week.', HABIT_WORDS[kind], GIVES_WAY[chosen]]
    for item in items:
        if item['deadline'] and item['deadline'] != item['local_date']:
            lines.append(f"{item['title']}: due {day_text(item['deadline'])}.")
    lines += [f"Put off {'twice' if item['moves'] > 1 else 'once'}: {item['title']}." for item in items
              if item['moved_reason'] == 'put off']
    return lines


def overview(connection, companion: dict, now, show_meter: bool = False) -> dict:
    """The Character page's Life admin panel: plain words, what is coming up, what comes due later and what got done
    lately. The meter only with Hidden values on."""
    definition, timeline_id = companion['version']['definition'], companion['active_timeline_id']
    today = local_now(companion, now).date()
    items = [item_view(item, definition) for item in upcoming(connection, timeline_id, today.isoformat())]
    shown = by_day([*items, *home_items(connection, companion, today, today + timedelta(days=AHEAD), now)])
    done = many(connection, "SELECT * FROM life_admin WHERE timeline_id=? AND status='done' AND local_date>=? "
                'ORDER BY local_date DESC, at_time DESC LIMIT 8', (timeline_id, (today - timedelta(days=30)).isoformat()))
    kind = habit(definition)
    pending, chosen = sum(item['moved_reason'] == 'put off' for item in items), level(connection)
    return {'state': state_lines(items, kind, today, chosen), 'habit': kind, 'upcoming': shown,
            'later': later(connection, companion, outings.city_data(connection, definition), today),
            'done': [item_view(view(row), definition) for row in done], 'level': chosen,
            'meter': max(0, min(100, METER[kind] - 10 * pending)) if show_meter else None}


def today_items(connection, companion: dict, now) -> list[dict]:
    """The next week's entries, for Today's Plans."""
    today = local_now(companion, now).date()
    definition = companion['version']['definition']
    end = today + timedelta(days=7)
    return by_day([*(item_view(item, definition) for item in upcoming(
        connection, companion['active_timeline_id'], today.isoformat(), end.isoformat())),
        *home_items(connection, companion, today, end, now)])

