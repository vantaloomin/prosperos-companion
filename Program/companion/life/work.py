"""Work life (Hit List #22): slammed weeks, slow weeks, a raise once a year.

The companion's job has a life of its own, decided without a model. Each week is slammed, normal or slow (a seeded
roll by the Work life slider, and always slammed in the week their running project is due). There is always one
running project, picked from a bank by the kind of work they do and their city's era
(companion/world/data/work_life.json), lasting three to eight weeks and ending well, fine or rough. Once a year, on
their review day, pay goes up by what their country and era give (US raises of a few percent, none in Camelot most
years); now and then that is a promotion, and on True to life and up a raise can be frozen. A storyline promotion
(companion/life/storylines.py) is a promotion here too. Vacation days follow the country and era (eleven in the US,
twenty-five in the UK, none in Victorian London): a week in the summer and long weekends spread over the year, which
the agenda shows as days off and trips (companion/life/trips.py) can use.

A slammed week puts a late night or two on the shared calendar (companion/life/admin.py, source 'work'), right after
work. It clashes with plans the user makes the way an appointment does: on True to life and Dramatic it holds its
time, so an outing asked for then goes to another day and the companion names it; on Light it moves for the user. It is
never cancelled, and the user can move it like any entry. Late nights also come through the existing disruptions
(companion/life/disruptions.py): a slammed week tilts work slots toward staying late, a slow week away from it.

On Dramatic, rarely, they are laid off or quit (likelier after slammed weeks in a row) and job hunt for a few weeks
before starting at a new place in the same line of work. Easy life's Light level keeps a steady job. Pay changes reach
the budget through money.household (`pay`). Only the companion is tracked; coworkers in the circle stay as they are.
"""
import json
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

from companion.clock import stamp, zone
from companion.database import decode, encode, identifier, many, optional
from companion.life import admin, money, outings, routine
from companion.world import catalog, generators

DATA = Path(__file__).parents[1] / 'world' / 'data' / 'work_life.json'
# Off in tests unless a test turns it on (tests/conftest.py), so other tests' days stay as written.
ACTIVE = True
LEVELS = (0, 1, 2, 3)
DEFAULT_LEVEL = 2
# Per level: the chance a week is slammed, and that it is slow; the rest are ordinary.
WEEKS = {0: (0.0, 0.0), 1: (0.06, 0.2), 2: (0.18, 0.15), 3: (0.28, 0.12)}
# Late nights on the calendar in a slammed week, by level (fewest, most).
LATE_NIGHTS = {0: (0, 0), 1: (0, 1), 2: (1, 2), 3: (1, 3)}
LATE_MINUTES = (90, 180)
# At the yearly review: the chance of a promotion instead of a raise, and of no raise at all.
PROMOTION = {0: 0.0, 1: 0.1, 2: 0.15, 3: 0.2}
PROMOTION_RAISE = (8.0, 15.0)
FREEZE = {0: 0.0, 1: 0.0, 2: 0.08, 3: 0.15}
# Dramatic only: the weekly chance of being laid off, and of quitting (times QUIT_SLAMMED after two slammed weeks).
LAYOFF_WEEKLY = 0.0012
QUIT_WEEKLY = 0.0008
QUIT_SLAMMED = 5
HUNT_WEEKS = (3, 10)
# Between jobs, a share of their pay to live on: severance after a layoff, savings after quitting.
HUNT_PAY = {'laid-off': 0.6, 'quit': 0.3}
NEW_JOB_PAY = (0.95, 1.12)
PROJECT_WEEKS = (3, 8)
# How a project turns out: (well, fine) chances by level; the rest is rough.
OUTCOMES = {0: (0.6, 0.3), 1: (0.65, 0.3), 2: (0.55, 0.3), 3: (0.45, 0.3)}
OUTCOME_WORDS = {'well': 'it went well', 'fine': 'it went fine', 'rough': 'it was a rough one'}
# Disruptions' work table tilted by the week (companion/life/disruptions.py tilts).
TILTS = {'slammed': {'over': 3.0}, 'slow': {'over': 0.25}}
CATCH_UP_DAYS = 60
AHEAD_DAYS = 14
RECENT_DAYS = 30
# Days off the agenda shows for work life (agenda.holiday_block), by the name it is given.
LABELS = {'Vacation': 'Vacation day', 'Job hunt': 'Job hunting'}
LATE_TITLE = 'Late night at work'
LATE_DONE = 'stayed late at work on '
WORKLOAD_WORDS = {'slammed': 'Slammed this week', 'normal': 'An ordinary week at work', 'slow': 'A slow week at work'}

# The kind of work a career is, by its sector (any word of it), for the project bank.
KINDS = {
    'office': ('business', 'commerce', 'clerical', 'finance', 'legal', 'real-estate', 'insurance', 'trade'),
    'tech': ('technology', 'biotech', 'engineering', 'aerospace', 'science'),
    'care': ('healthcare', 'healing', 'medicine', 'social-services', 'care', 'religion', 'church', 'spiritualism'),
    'teaching': ('education', 'learning'),
    'service': ('hospitality', 'food', 'victualling', 'retail', 'tourism', 'recreation', 'fitness', 'services',
                'domestic', 'domestic-service', 'household', 'court', 'palace', 'gardens'),
    'handson': ('trades', 'crafts', 'construction', 'building', 'manufacturing', 'textiles', 'cloth', 'garment',
                'mining', 'quarrying', 'fishing', 'maritime', 'shipbuilding', 'marine-trades', 'agriculture',
                'farming', 'ranching', 'forest', 'milling', 'city-works'),
    'transport': ('logistics', 'transit', 'transport', 'railroad', 'freight', 'shipping', 'communications', 'river'),
    'creative': ('creative', 'entertainment', 'music', 'arts', 'media', 'press', 'newspaper'),
    'public': ('government', 'law', 'law-enforcement', 'public-safety', 'security', 'military', 'army', 'defense',
               'gates', 'labour'),
}
ERA_GROUPS = {'modern': 'modern', 'future': 'modern', 'other': 'modern', 'jazz-age': 'jazz-age',
              'victorian': 'industrial', 'steampunk': 'industrial', 'frontier': 'industrial'}


@lru_cache(maxsize=1)
def data() -> dict:
    return json.loads(DATA.read_text(encoding='utf-8'))


def level(connection) -> int:
    row = optional(connection, 'SELECT work_realism FROM life_settings WHERE id=1')
    return row['work_realism'] if row and row['work_realism'] in LEVELS else DEFAULT_LEVEL


def era_group(city: dict | None) -> str:
    return ERA_GROUPS.get(city.get('era') or 'modern', 'old') if city else 'modern'


def rules(city: dict | None) -> dict:
    """Vacation days, raises and the review month for a city's country and era."""
    found = data()['rules']
    key = catalog.calendar_id(city) if city else 'us'
    if key and key in found:
        return found[key]
    group = era_group(city)
    if group == 'modern':
        country = (city or {}).get('country', '').strip().lower()
        return found['countries'].get(country) and {**found['modern'], **found['countries'][country]} \
            or found['modern']
    return found['old' if group == 'old' else 'industrial' if group == 'industrial' else 'us-1920s']


def works(definition: dict) -> bool:
    return any(block.kind == 'work' for block in routine.blocks(definition)[0])


def workdays(definition: dict) -> frozenset[int]:
    return frozenset(day for block in routine.blocks(definition)[0] if block.kind == 'work' for day in block.days)


def work_block(definition: dict, day: date) -> dict | None:
    """The day's last work block (the one a late night follows)."""
    found = [block.view() for block in routine.blocks(definition)[0] if block.kind == 'work' and day.weekday() in
             block.days]
    return max(found, key=lambda block: block['end'] if block['end'] > block['start'] else '24:00', default=None)


def career_of(definition: dict, city: dict | None) -> dict | None:
    if not city:
        return None
    try:
        return money.career_for(definition, city)[0]
    except (KeyError, TypeError):
        return None


def kind_of(career: dict | None) -> str:
    """The project bank a career draws from: adult work its own, then by sector, else the general bank."""
    if not career:
        return 'general'
    if career.get('adult') and 'modern' in (career.get('eras') or ['modern']):
        return 'adult'
    sector = (career.get('sector') or '').lower()
    for kind, words in KINDS.items():
        if sector in words or any(word in sector.split('-') for word in words):
            return kind
    return 'general'


def projects(kind: str, group: str) -> list[str]:
    bank = data()['projects']
    found = [item['title'] for item in bank.get(kind, ()) if group in item['eras']]
    return found or [item['title'] for item in bank['general'] if group in item['eras']]


def local_today(companion: dict, now: datetime) -> date:
    return now.astimezone(zone(companion['version']['timezone'])).date()


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


# --- State ---

def state(connection, timeline_id: str) -> dict | None:
    row = optional(connection, 'SELECT * FROM work_life WHERE timeline_id=?', (timeline_id,))
    return {**row, 'project': decode(row['project'])} if row else None


def new_project(seed: str, index: int, kind: str, group: str, start: date, used: list[str]) -> dict:
    """The next running project, from the bank, not one of the last few."""
    options = [title for title in projects(kind, group) if title not in used[-8:]] or projects(kind, group)
    title = generators.pick(seed, f'project:{index}', options)
    weeks = PROJECT_WEEKS[0] + int(generators.unit(seed, 'weeks', index) * (PROJECT_WEEKS[1] - PROJECT_WEEKS[0] + 1))
    due = monday_of(start) + timedelta(weeks=weeks, days=int(generators.unit(seed, 'due-day', index) * 5))
    return {'title': title, 'index': index, 'started': start.isoformat(), 'due': max(due, start).isoformat()}


def ensure(connection, companion: dict, today: date, now: datetime) -> dict | None:
    """The companion's work state, made the first time (or afresh when they change careers): when they started, their
    yearly review day and a project part way along. None when they have no job in their week."""
    definition, timeline_id = companion['version']['definition'], companion['active_timeline_id']
    if not works(definition):
        return None
    city = outings.city_data(connection, definition)
    career = career_of(definition, city)
    career_id = career['id'] if career else ''
    found = state(connection, timeline_id)
    if found and found['career'] == career_id:
        return found
    seed = f"work:{timeline_id}:{career_id}"
    started = today - timedelta(days=0 if found else 200 + int(generators.unit(seed, 'tenure') * 2400))
    month = rules(city).get('review_month')
    review = f'{month:02d}-{1 + int(generators.unit(seed, "review") * 27):02d}' if month else started.strftime('%m-%d')
    project = new_project(seed, 0, kind_of(career), era_group(city),
                          today - timedelta(days=int(generators.unit(seed, 'into') * 14)), [])
    connection.execute(
        'INSERT INTO work_life (timeline_id, career, kind, started_on, review_on, pay, status, project, used, '
        'checked_through, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?) '
        'ON CONFLICT (timeline_id) DO UPDATE SET career=excluded.career, kind=excluded.kind, '
        "started_on=excluded.started_on, review_on=excluded.review_on, pay=1, status='working', hunt_until=NULL, "
        'hunt_reason=NULL, employer=\'\', project=excluded.project, checked_through=excluded.checked_through, '
        'updated_at=excluded.updated_at',
        (timeline_id, career_id, kind_of(career), started.isoformat(), review, 'working', encode(project),
         encode([project['title']]), today.isoformat(), stamp(now), stamp(now)))
    return state(connection, timeline_id)


def record(connection, timeline_id: str, key: str, kind: str, day: date, text: str, pay: float, change: float,
           now: datetime) -> bool:
    return connection.execute(
        'INSERT OR IGNORE INTO work_events (id, timeline_id, key, kind, local_date, text, pay, change, created_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (identifier(), timeline_id, key, kind, day.isoformat(), text, round(pay, 4), round(change, 2), stamp(now))
    ).rowcount > 0


def update(connection, timeline_id: str, now: datetime, **fields):
    names = ', '.join(f'{name}=?' for name in fields)
    values = [encode(value) if isinstance(value, (dict, list)) else value for value in fields.values()]
    connection.execute(f'UPDATE work_life SET {names}, updated_at=? WHERE timeline_id=?',
                       (*values, stamp(now), timeline_id))


# --- How each week goes ---

def workload(found: dict, monday: date, chosen: int) -> str:
    """'slammed', 'normal' or 'slow' for the week starting this Monday: slammed the week the project is due."""
    if not chosen or found['status'] != 'working':
        return 'normal'
    due = date.fromisoformat(found['project']['due'])
    if monday <= due < monday + timedelta(days=7):
        return 'slammed'
    slammed, slow = WEEKS[chosen]
    roll = generators.unit(f"work:{found['timeline_id']}", 'week', monday)
    return 'slammed' if roll < slammed else 'slow' if roll < slammed + slow else 'normal'


def week_of(connection, companion: dict, day: date) -> str | None:
    """The workload of the week this day is in, or None without work life."""
    found = state(connection, companion['active_timeline_id']) if ACTIVE else None
    chosen = level(connection) if found else 0
    return workload(found, monday_of(day), chosen) if found and chosen else None


def tilt(connection, companion: dict, day: date, tilts: dict | None) -> dict | None:
    """Disruptions' tilt for a work slot this day: more staying late in a slammed week, less in a slow one."""
    week = week_of(connection, companion, day)
    if week not in TILTS:
        return tilts
    found = dict(tilts or {})
    for key, factor in TILTS[week].items():
        found[key] = found.get(key, 1) * factor
    return found


# --- Vacation days ---

@lru_cache(maxsize=64)
def vacation_plan(seed: str, year: int, allowance: int, days: frozenset[int], months: tuple[int, ...],
                  closed: frozenset[str], since: str) -> tuple[str, ...]:
    """A year's vacation days: a week (or what the allowance has) in their summer months, then single days on
    Fridays and Mondays spread over the year, leaving a day or two unused now and then. Workdays only."""
    if not allowance or not days:
        return ()
    def workday(day: date) -> bool:
        return day.weekday() in days and day.isoformat() not in closed and day.isoformat() >= since
    taken: list[date] = []
    if allowance >= 5 and months:
        month = months[int(generators.unit(seed, 'month', year) * len(months))]
        first = date(year, month, 1) + timedelta(days=int(generators.unit(seed, 'week', year) * 21))
        start = monday_of(first) + timedelta(weeks=1)
        taken += [day for day in (start + timedelta(days=offset) for offset in range(7)) if workday(day)][:5]
    left = allowance - len(taken) - int(generators.unit(seed, 'unused', year) * 3)
    for index in range(max(0, left) * 3):
        if len(taken) >= allowance - (allowance - len(taken) - max(0, left)) or left <= 0:
            break
        day = date(year, 1, 1) + timedelta(days=int(generators.unit(seed, 'single', year, index) * 365))
        day = day + timedelta(days=(4 - day.weekday()) % 7 if generators.unit(seed, 'side', year, index) < 0.6
                              else (0 - day.weekday()) % 7)
        if day.year == year and workday(day) and day not in taken:
            taken.append(day)
            left -= 1
    return tuple(sorted(day.isoformat() for day in taken))


def vacation_days(connection, companion: dict, year: int, found: dict | None = None) -> list[str]:
    definition, timeline_id = companion['version']['definition'], companion['active_timeline_id']
    found = found or state(connection, timeline_id)
    if not found or not level(connection):
        return []
    city = outings.city_data(connection, definition)
    rule = rules(city)
    closed = frozenset(item['date'] for item in generators.holidays(city, date(year, 1, 1), date(year, 12, 31))
                       if item['kind'] == 'public') if city else frozenset()
    plan = vacation_plan(f'vacation:{timeline_id}:{found["career"]}', year, int(rule.get('vacation') or 0),
                         workdays(definition), tuple(rule.get('vacation_month') or ()), closed, found['started_on'])
    hunting = hunt_span(found)
    return [day for day in plan if not hunting or not hunting[0] <= day <= hunting[1]]


def hunt_span(found: dict) -> tuple[str, str] | None:
    if found['status'] != 'hunting':
        return None
    return found['hunt_since'], found['hunt_until']


def days_off(connection, companion: dict, start: date, end: date) -> dict[str, str]:
    """{local date: 'Vacation' or 'Job hunt'} for the agenda: vacation days, and workdays while between jobs."""
    if not ACTIVE:
        return {}
    found = state(connection, companion['active_timeline_id'])
    if not found or not level(connection):
        return {}
    result = {}
    for year in range(start.year, end.year + 1):
        for day in vacation_days(connection, companion, year, found):
            if start.isoformat() <= day <= end.isoformat():
                result[day] = 'Vacation'
    if span := hunt_span(found):
        days, day = workdays(companion['version']['definition']), max(start, date.fromisoformat(span[0]))
        while day <= min(end, date.fromisoformat(span[1]) - timedelta(days=1)):
            if day.weekday() in days:
                result[day.isoformat()] = 'Job hunt'
            day += timedelta(days=1)
    return result


def vacation_dates(connection, companion: dict, start: date, end: date) -> set[str]:
    """Vacation days between two dates, for trips' long weekends (companion/life/trips.py)."""
    return {day for day, name in days_off(connection, companion, start, end).items() if name == 'Vacation'}


# --- Moving through the days ---

def review(connection, companion: dict, found: dict, day: date, chosen: int, rule: dict, now) -> float:
    """The yearly review: a raise by the country and era, now and then a promotion, on True to life and up sometimes
    a freeze. Returns the new pay."""
    seed, timeline_id = f"work:{companion['active_timeline_id']}:{day.year}", companion['active_timeline_id']
    pay = found['pay']
    roll = generators.unit(seed, 'review')
    low, high = rule.get('raise') or (2.0, 4.0)
    if roll < PROMOTION[chosen]:
        change = PROMOTION_RAISE[0] + generators.unit(seed, 'promotion') * (PROMOTION_RAISE[1] - PROMOTION_RAISE[0])
        record(connection, timeline_id, f'review:{day.year}', 'promotion', day,
               f'promoted at work, with a raise of about {round(change)}%', pay * (1 + change / 100), change, now)
        return pay * (1 + change / 100)
    if roll < PROMOTION[chosen] + FREEZE[chosen] or generators.unit(seed, 'given') >= rule.get('raise_chance', 1.0):
        record(connection, timeline_id, f'review:{day.year}', 'freeze', day, 'no raise this year', pay, 0, now)
        return pay
    change = low + generators.unit(seed, 'raise') * (high - low)
    if change < 0.5:
        record(connection, timeline_id, f'review:{day.year}', 'freeze', day, 'no raise this year', pay, 0, now)
        return pay
    record(connection, timeline_id, f'review:{day.year}', 'raise', day,
           f'the yearly raise, about {round(change, 1):g}%', pay * (1 + change / 100), change, now)
    return pay * (1 + change / 100)


def finish_project(connection, companion: dict, found: dict, day: date, chosen: int, now) -> dict:
    """The project that was due is done, with how it went; the next one starts."""
    timeline_id, project = companion['active_timeline_id'], found['project']
    seed = f'work:{timeline_id}:{found["career"]}'
    well, fine = OUTCOMES[chosen]
    roll = generators.unit(seed, 'outcome', project['index'])
    outcome = 'well' if roll < well else 'fine' if roll < well + fine else 'rough'
    record(connection, timeline_id, f"project:{found['career']}:{project['index']}", 'project', day,
           f"wrapped up {project['title']}; {OUTCOME_WORDS[outcome]}", found['pay'], 0, now)
    city = outings.city_data(connection, companion['version']['definition'])
    used = decode(found['used']) if isinstance(found['used'], str) else found['used']
    following = new_project(seed, project['index'] + 1, found['kind'], era_group(city), day + timedelta(days=1), used)
    return {'project': following, 'used': [*used, following['title']][-12:]}


def lose_job(connection, companion: dict, found: dict, day: date, slammed_run: int, now) -> dict | None:
    """Dramatic only: rarely laid off or quitting this week, then a job hunt of a few weeks."""
    seed = f"work:{companion['active_timeline_id']}:lose:{day.isoformat()}"
    roll = generators.unit(seed, 'roll')
    quit_chance = QUIT_WEEKLY * (QUIT_SLAMMED if slammed_run >= 2 else 1)
    reason = 'laid-off' if roll < LAYOFF_WEEKLY else 'quit' if roll < LAYOFF_WEEKLY + quit_chance else None
    if not reason:
        return None
    weeks = HUNT_WEEKS[0] + int(generators.unit(seed, 'weeks') * (HUNT_WEEKS[1] - HUNT_WEEKS[0] + 1))
    until = day + timedelta(weeks=weeks)
    text = 'laid off, and looking for work' if reason == 'laid-off' else 'quit your job, and looking for work'
    record(connection, companion['active_timeline_id'], f'lose:{day.isoformat()}', reason, day, text,
           found['pay'], 0, now)
    return {'status': 'hunting', 'hunt_since': day.isoformat(), 'hunt_until': until.isoformat(), 'hunt_reason': reason}


def new_job(connection, companion: dict, found: dict, day: date, now) -> dict:
    """The hunt is over: a new place in the same line of work, at about the same pay or a little more."""
    definition, timeline_id = companion['version']['definition'], companion['active_timeline_id']
    seed = f'work:{timeline_id}:job:{day.isoformat()}'
    city = outings.city_data(connection, definition)
    employer = ''
    if city and found['career']:
        try:
            employer = generators.job(city, found['career'], seed=seed)['employer']['name']
        except (KeyError, TypeError, ValueError, IndexError):
            employer = ''
    pay = found['pay'] * (NEW_JOB_PAY[0] + generators.unit(seed, 'pay') * (NEW_JOB_PAY[1] - NEW_JOB_PAY[0]))
    record(connection, timeline_id, f'job:{day.isoformat()}', 'new-job', day,
           f'started a new job{" at " + employer if employer and not employer.startswith("a ") else ""}', pay,
           (pay / found['pay'] - 1) * 100, now)
    used = decode(found['used']) if isinstance(found['used'], str) else found['used']
    project = new_project(f'work:{timeline_id}:{found["career"]}:{day.isoformat()}', found['project']['index'] + 1,
                          found['kind'], era_group(city), day, used)
    return {'status': 'working', 'hunt_until': None, 'hunt_reason': None, 'employer': employer, 'pay': pay,
            'started_on': day.isoformat(), 'review_on': day.strftime('%m-%d') if not rules(city).get('review_month')
            else found['review_on'], 'project': project, 'used': [*used, project['title']][-12:]}


def storyline_promotions(connection, companion: dict, found: dict, today: date, now) -> float:
    """A promotion storyline that ended with the promotion (companion/life/storylines.py) raises their pay too."""
    pay = found['pay']
    for row in many(connection, "SELECT id, stages FROM storylines WHERE timeline_id=? AND story='promotion_chance'",
                    (companion['active_timeline_id'],)):
        for stage in decode(row['stages']):
            if stage.get('tone') == 'good' and 'got the promotion' in stage.get('text', '') and \
                    found['started_on'] <= stage['on'] <= today.isoformat():
                change = PROMOTION_RAISE[0] + generators.unit(row['id'], 'promotion') * \
                    (PROMOTION_RAISE[1] - PROMOTION_RAISE[0])
                if record(connection, companion['active_timeline_id'], f"storyline:{row['id']}", 'promotion',
                          date.fromisoformat(stage['on']), f'promoted at work, with a raise of about {round(change)}%',
                          pay * (1 + change / 100), change, now):
                    pay *= 1 + change / 100
    return pay


def advance(connection, companion: dict, now: datetime) -> dict | None:
    """Walk the days since last time: reviews, projects ending, on Dramatic a lost job, and the end of a hunt."""
    timeline_id = companion['active_timeline_id']
    today = local_today(companion, now)
    found = ensure(connection, companion, today, now)
    if not found:
        return None
    chosen = level(connection)
    city = outings.city_data(connection, companion['version']['definition'])
    rule = rules(city)
    day = max(date.fromisoformat(found['checked_through']) + timedelta(days=1), today - timedelta(days=CATCH_UP_DAYS))
    changes: dict = {}
    while chosen and day <= today:
        current = {**found, **changes}
        if current['status'] == 'hunting':
            if day.isoformat() >= current['hunt_until']:
                changes.update(new_job(connection, companion, current, day, now))
        else:
            if day.strftime('%m-%d') == current['review_on'] and (day - date.fromisoformat(current['started_on'])).days > 300:
                changes['pay'] = review(connection, companion, current, day, chosen, rule, now)
            if day.isoformat() > current['project']['due']:
                changes.update(finish_project(connection, companion, current, day, chosen, now))
            if chosen >= 3 and day.weekday() == 0:
                run = sum(workload(current, day - timedelta(weeks=back), chosen) == 'slammed' for back in (1, 2))
                if lost := lose_job(connection, companion, current, day, run, now):
                    changes.update(lost)
        day += timedelta(days=1)
    if chosen:
        changes['pay'] = storyline_promotions(connection, companion, {**found, **changes}, today, now)
    update(connection, timeline_id, now, checked_through=today.isoformat(), **changes)
    return state(connection, timeline_id)


def plan_late_nights(connection, companion: dict, found: dict, today: date, chosen: int, now) -> int:
    """A slammed week's late nights on the shared calendar, right after work, on seeded workdays. They hold their
    time against plans with the user on True to life and up (admin.stands), and move for them on Light."""
    definition, timeline_id = companion['version']['definition'], companion['active_timeline_id']
    days, added = workdays(definition), 0
    off = days_off(connection, companion, today, today + timedelta(days=AHEAD_DAYS + 7))
    for week in range(0, AHEAD_DAYS // 7 + 1):
        monday = monday_of(today) + timedelta(weeks=week)
        if workload(found, monday, chosen) != 'slammed':
            continue
        seed = f'work:{timeline_id}:late:{monday.isoformat()}'
        low, high = LATE_NIGHTS[chosen]
        count = low + int(generators.unit(seed, 'count') * (high - low + 1))
        options = [monday + timedelta(days=offset) for offset in range(7)
                   if (monday + timedelta(days=offset)).weekday() in days
                   and (monday + timedelta(days=offset)).isoformat() not in off]
        due = date.fromisoformat(found['project']['due'])
        picks = sorted(options, key=lambda day: (day != due - timedelta(days=1), generators.unit(seed, 'day', day)))
        last = max(options, default=None)
        for index, day in enumerate(picks[:count]):
            block = work_block(definition, day)
            if not block or day < today:
                continue
            minutes = LATE_MINUTES[0] + int(generators.unit(seed, 'minutes', index) * 4) * 30
            title = found['project']['title']
            added += bool(admin.add(
                connection, companion, key=f'work:late:{monday.isoformat()}:{index}', source='work', kind='late-night',
                title=LATE_TITLE, done=f'{LATE_DONE}{title}', day=day,
                at=block['end'] if block['end'] > block['start'] else None, minutes=min(minutes, 180),
                fixed=chosen >= 2, deadline=last, out=False, now=now))
    return added


def plan_ahead(connection, companion: dict, world, now: datetime) -> dict:
    """Called each time the agenda extends, before life admin settles its calendar. Cheap: no model."""
    if not ACTIVE:
        return {}
    chosen = level(connection)
    found = advance(connection, companion, now)
    timeline_id = companion['active_timeline_id']
    # Late nights follow the slider as it is now: held on True to life and up, movable on Light, gone when off.
    if not found or not chosen:
        connection.execute("UPDATE life_admin SET status='removed', updated_at=? WHERE timeline_id=? AND source='work' "
                           "AND status='planned'", (stamp(now), timeline_id))
        return {}
    connection.execute("UPDATE life_admin SET fixed=? WHERE timeline_id=? AND source='work' AND status='planned'",
                       (int(chosen >= 2), timeline_id))
    if found['status'] == 'hunting':
        connection.execute("UPDATE life_admin SET status='removed', updated_at=? WHERE timeline_id=? AND "
                           "source='work' AND status='planned'", (stamp(now), timeline_id))
        return {'added': 0}
    return {'added': plan_late_nights(connection, companion, found, local_today(companion, now), chosen, now)}


# --- The day's account ---

SLAMMED = ('{name} put in a long {label} on {project}.', '{name} spent the {label} buried in {project}.',
           'The {label} was all {project}, and {name} barely looked up.',
           '{name} raced through the {label} to keep {project} on track.')
SLOW = ('A slow {label}: {name} caught up on small things and left on time.',
        '{name} had a quiet {label}, with time to tidy up loose ends.',
        'Not much happened during the {label}, and {name} did not mind.')
STEADY = ('{name} worked on {project} during the {label}.', '{name} made steady progress on {project}.')
HUNT = ('{name} spent the morning on job applications.', '{name} sent out a few applications and followed up on one.',
        '{name} had a phone call about a job that might go somewhere.', '{name} went over their résumé again.',
        '{name} answered two job listings and went for a walk to clear their head.',
        '{name} had an interview and came away hopeful.')
HUNT_OLD = ('{name} went round asking after work.', '{name} answered a notice for a position and waited to hear.',
            '{name} called on a few places that might be hiring.')
SLAMMED_POSTS = ('Long day. Longer week.', 'Deadline week, send snacks.', 'Inbox: overflowing.')
SLOW_POSTS = ('Quiet one today.', 'A slow day, for once.', 'Left on time, a miracle.')
CAPTIONS_HUNT = ('Job hunting is a job.', 'Fingers crossed.', 'Applications out.')


def touch(connection, companion: dict, entry: dict | None, block: dict, day: date, seed: str) -> dict | None:
    """A work slot's account by the week (a long day on the project when slammed, a quiet one when slow, now and
    then the project by name), and a day of job hunting while between jobs."""
    if not ACTIVE or block.get('kind') not in ('work', 'leisure'):
        return entry
    name = companion['version']['definition']['name']
    if block.get('holiday') == 'Job hunt':
        city = outings.city_data(connection, companion['version']['definition'])
        lines = HUNT if era_group(city) == 'modern' else HUNT_OLD
        return {**(entry or {}), 'summary': generators.pick(seed, 'hunt', list(lines)).format(name=name),
                'post': generators.pick(seed, 'hunt-post', list(CAPTIONS_HUNT)), 'mood': 'restless',
                'activity': 'job-hunting', 'place': None, 'with': None, 'weather': block.get('weather'),
                'composer_version': 'work-1'}
    if block.get('kind') != 'work' or block.get('holiday') or block.get('sick_day') or not entry:
        return entry
    week = week_of(connection, companion, day)
    found = state(connection, companion['active_timeline_id'])
    if not week or not found:
        return entry
    label, project = routine_label(block), found['project']['title']
    if week == 'slammed':
        lines, posts, mood = SLAMMED, SLAMMED_POSTS, 'busy'
    elif week == 'slow':
        lines, posts, mood = SLOW, SLOW_POSTS, 'relaxed'
    elif generators.unit(seed, 'project-line') < 0.4:
        lines, posts, mood = STEADY, (), entry.get('mood')
    else:
        return entry
    summary = generators.pick(seed, 'work-week', list(lines)).format(name=name, label=label, project=project)
    return {**entry, 'summary': summary, 'mood': mood or entry.get('mood'),
            'post': generators.pick(seed, 'work-post', list(posts)) if posts else entry.get('post')}


def routine_label(block: dict) -> str:
    from companion.life import composer
    return composer.span(block)


# --- What the chat, the Character page and the budget see ---

def recent_events(connection, timeline_id: str, since: str) -> list[dict]:
    return many(connection, 'SELECT * FROM work_events WHERE timeline_id=? AND local_date>=? ORDER BY local_date',
                (timeline_id, since))


def pay(connection, timeline_id: str, day: date) -> dict | None:
    """Their pay as a share of the career's base, and whether they are between jobs (money.household)."""
    if not ACTIVE:
        return None
    found = state(connection, timeline_id)
    if not found or not level(connection):
        return None
    hunting = found['status'] == 'hunting' and found['hunt_since'] <= day.isoformat()
    factor = found['pay'] * (HUNT_PAY.get(found['hunt_reason'] or '', 0.5) if hunting else 1)
    return {'factor': round(factor, 4), 'between_jobs': hunting}


def day_text(local: str) -> str:
    return date.fromisoformat(local).strftime('%A, %B %d').replace(' 0', ' ')


def short_day(local: str) -> str:
    return date.fromisoformat(local).strftime('%B %d').replace(' 0', ' ')


def tenure(started: str, today: date) -> str:
    days = (today - date.fromisoformat(started)).days
    if days < 60:
        return 'a few weeks'
    if days < 365:
        return f'about {round(days / 30)} months'
    years = round(days / 365)
    return 'about a year' if years == 1 else f'about {years} years'


def vacation_line(days: list[str], today: date) -> str:
    """'You are off work Friday, October 30 (a vacation day).' or a run of days as one stretch."""
    upcoming = sorted({day for day in days if today.isoformat() <= day <= (today + timedelta(days=21)).isoformat()})
    if not upcoming:
        return ''
    run = [upcoming[0]]
    for day in upcoming[1:]:
        if (date.fromisoformat(day) - date.fromisoformat(run[-1])).days <= 3:
            run.append(day)
    if run[0] == today.isoformat():
        return f'You are on vacation from work through {day_text(run[-1])}.' if len(run) > 1 else \
            'You have today off work (a vacation day).'
    if len(run) == 1:
        return f'You have {day_text(run[0])} off work (a vacation day).'
    return f'You are off work from {day_text(run[0])} through {day_text(run[-1])} (vacation).'


EVENT_LINES = {
    'raise': 'On {day} you got {text} at work.',
    'promotion': 'On {day} you were {text}.',
    'freeze': 'At your review on {day} there was {text}: your pay stays as it is.',
    'project': 'On {day} you {text}.',
    'laid-off': 'On {day} you were {text}.',
    'quit': 'On {day} you {text}.',
    'new-job': 'On {day} you {text}.',
}


def context_lines(connection, companion: dict, now: datetime) -> list[tuple[str, str]]:
    """(identity, line) for the chat context's Work section: this week, the project, time off and what changed
    lately. [] without a job or with Work life off."""
    if not ACTIVE:
        return []
    timeline_id = companion['active_timeline_id']
    found, chosen = state(connection, timeline_id), level(connection)
    if not found or not chosen or not works(companion['version']['definition']):
        return []
    today, lines = local_today(companion, now), []
    if found['status'] == 'hunting':
        lines.append(('status', 'You are between jobs and looking for work; nothing is lined up yet.'))
    else:
        week, project = workload(found, monday_of(today), chosen), found['project']
        due = date.fromisoformat(project['due'])
        due_text = f" It is due {day_text(project['due'])}." if 0 <= (due - today).days <= 21 else ''
        lines.append(('week', {'slammed': 'Work is slammed this week.', 'slow': 'Work is slow this week.',
                               'normal': 'An ordinary week at work.'}[week]))
        lines.append(('project', f"At work you are in the middle of {project['title']}.{due_text}"))
        lines.append(('tenure', f"You have been at this job for {tenure(found['started_on'], today)}."))
        if line := vacation_line(vacation_days(connection, companion, today.year, found)
                                 + vacation_days(connection, companion, today.year + 1, found), today):
            lines.append(('vacation', line))
    for event in recent_events(connection, timeline_id, (today - timedelta(days=RECENT_DAYS)).isoformat())[-3:]:
        lines.append((f"event:{event['id']}",
                      EVENT_LINES[event['kind']].format(day=short_day(event['local_date']), text=event['text'])))
    return [(f'work:{today.isoformat()}:{key}', f'- {line}') for key, line in lines]


def overview(connection, companion: dict, now: datetime, show_meter: bool = False) -> dict | None:
    """The Character page's Work life panel: plain words, the project, time off and what changed. Vacation counts and
    pay as a number only with Hidden values on. None without a job in their week."""
    timeline_id = companion['active_timeline_id']
    if not works(companion['version']['definition']):
        return None
    chosen = level(connection)
    found = state(connection, timeline_id) if ACTIVE else None
    if not found and ACTIVE:
        found = ensure(connection, companion, local_today(companion, now), now)
    today = local_today(companion, now)
    if not found:
        return None
    week = workload(found, monday_of(today), chosen)
    days = vacation_days(connection, companion, today.year, found) if chosen else []
    late = [admin.item_view(item, companion['version']['definition'])
            for item in admin.upcoming(connection, timeline_id, today.isoformat())
            if item['source'] == 'work'][:4]
    state_lines = []
    if not chosen:
        state_lines.append('Work life is off: their job stays as written.')
    elif found['status'] == 'hunting':
        state_lines.append('Between jobs and job hunting.')
    else:
        state_lines.append(WORKLOAD_WORDS[week] + '.')
        state_lines.append(f"Working on {found['project']['title']}, due {day_text(found['project']['due'])}.")
        if line := vacation_line(days + vacation_days(connection, companion, today.year + 1, found), today):
            state_lines.append(line.replace('You are', 'They are').replace('You have', 'They have')
                               .replace('your', 'their'))
    events = recent_events(connection, timeline_id, (today - timedelta(days=365)).isoformat())
    meter = None
    if show_meter and chosen:
        used = sum(day < today.isoformat() for day in days)
        city = outings.city_data(connection, companion['version']['definition'])
        meter = {'vacation_total': len(days), 'vacation_used': used, 'pay_percent': round(found['pay'] * 100),
                 'allowance': int(rules(city).get('vacation') or 0), 'level': chosen}
    return {'state': state_lines, 'workload': week if chosen and found['status'] == 'working' else None,
            'status': found['status'], 'project': found['project'], 'started_on': found['started_on'],
            'tenure': tenure(found['started_on'], today), 'employer': found['employer'],
            'late_nights': late, 'vacation': [day for day in days if day >= today.isoformat()][:10],
            'events': [{'id': event['id'], 'kind': event['kind'], 'local_date': event['local_date'],
                        'text': event['text']} for event in reversed(events)][:8],
            'level': chosen, 'meter': meter}
