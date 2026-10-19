"""Our child (Hit List #73, v0.15 Room to Grow): the child the user and a romance companion had or took in together
(companion/life/expecting.py), growing up in real time.

The app decides, the user overrides ("the world exists outside of User", Vanta 2026-10-08). Rules and seeds only, no
model:

- The child is in `circle_children` (title 'ours', parent_id the companion) with their birthday; their age comes from
  it. A short sheet from the bank (companion/world/data/our_child.json), seeded by the child: a temperament for life,
  what they are into lately (a new pick each month) and a quirk (each season), by age band (baby, toddler, small
  child, school age, teen), lines that fit their city's era only.
- Milestones come in real time from their birthday (first smile, first word, first steps, the first day of school
  ...), each on a seeded day; once reached they are a Today line and go in the scrapbook.
- Family life changes the companion's days by rules, as much as Settings > Realism > Family life says (`family_life`,
  0 easy kids, only the good days, to 3 true-to-life chaos): broken nights until the child sleeps through (tired, so
  lower), bedtimes and the school run, childcare from their money, a sitter for evenings out, sick days off work,
  and family days out (a walk in the park, the zoo) as outings with the user, the child in words only.
- Who stays home is the engine's `family:care`, from both their jobs and their money: both keep working, the
  companion goes part-time, stays home, or the user does. The user can change it on the Character page.
- Their people become grandparents, aunts and uncles, with lines of their own; holidays and traditions grow the
  child's part as they grow.
- At 18 the child is an adult person in their circle (`grow_up`), never a romance, never in Matchlight, and never in
  a chat with the adult side's lines.

Children keep v0.14's limits everywhere: words only (the child's name is in families.names, so no picture is made of
words naming them, and a family day out has no photo), and with the adult side of life on a reply carries the family
lines or the adult side's, never both (companion/memory/sides.py; `quiet` keeps it off the calendar). A second child
can come as its own step, no sooner than a year and a half after the first came home (companion/life/parenthood.py).
"""
import json
import random
import re
from datetime import date, timedelta
from functools import cache

from companion import consequences
from companion.clock import stamp
from companion.database import decode, encode, many, optional
from companion.errors import require
from companion.life import ages, families, steps
from companion.life.steps import FAMILY
from companion.world import catalog, generators

ACTIVE = True
TITLE = 'ours'
GROWN = 18
USUAL = 2
LEVELS = ('easy', 'gentle', 'true to life', 'chaos')
BANDS = (('baby', 0, 0), ('toddler', 1, 3), ('small_child', 4, 6), ('school_age', 7, 12), ('teen', 13, 17))
CARE = ('both_work', 'part_time', 'them_home', 'you_home')
CARE_LABELS = {'both_work': 'You both work', 'part_time': '{name} goes part-time', 'them_home': '{name} stays home',
               'you_home': 'You stay home'}
# Until the youngest starts school, who looks after them; then both work again.
SCHOOL = 5
# Weeks the companion is off work after a child comes: the one who carried, else a parent taking them in.
LEAVE_WEEKS = {'expecting_them': 14, 'expecting_you': 2, 'surrogacy': 2}
ADOPTING_LEAVE = 12
LEAVE = 'Parental leave'
HOME_DAY = 'Home day'
SICK_DAY = 'Family sick day'
LABELS = {HOME_DAY: 'A day at home', SICK_DAY: 'A day off to look after family'}
# What their pay is as a share of a full one while they look after the child (companion/life/work.py `pay`): part
# time, or at home (the household lives mostly on the user's pay then).
PAY = {'part_time': 0.6, 'them_home': 0.3}
# Childcare each month as a share of a month's take-home: their half of it, both working or part-time.
CHILDCARE = {'both_work': 0.09, 'part_time': 0.045}
OLD_CARE = 0.5  # An older city's minder costs less.
SITTER = 0.012  # A paid sitter for an evening out, when nobody in the family nearby can.
SITTER_UNDER = 13
EVENING = '17:00'
OUT_ACTIVITIES = ('dinner', 'drinks', 'show', 'hobby', 'meet-family', 'meet-friends', 'big-day', 'wedding')
# Each year, workdays home with a sick child (from 1 to 12), by Family life; none on an easy life.
SICK_DAYS = (0, 2, 5, 9)
# Each night's chance of a broken night until they sleep through, by Family life; a third of it while a toddler.
BROKEN = (0.0, 0.15, 0.35, 0.55)
# Sleeping through the night, in days from birth, by Family life: sooner on an easy life.
SLEEPS = ((60, 120), (100, 220), (120, 300), (200, 420))
# A family day out every so many days, on a weekend, from one year old to fifteen.
OUTING_EVERY = 35
OUTING_AGES = (1, 15)
OUTING_AHEAD = 7
NEWBORN_DAYS = 90
SOLIDS_DAYS = 180
FOOD = re.compile(r'\b(?:banana\w*|mash\w*|pur[ée]e\w*|food|eat\w*|spoon\w*|porridge|oatmeal|biscuits?|cookies?|toast|apple\w*|'
                  r'peas|carrots?|avocado|yogh?urt|crusts?|rusks?|snacks?|bread|cheese|berr(?:y|ies)|pasta|rice)\b',
                  re.IGNORECASE)
HOLIDAY_AFTER = 3  # Days after a holiday its line stays.
PEOPLE_AGES = (2, 10)  # The ages the grandparents', aunts' and uncles' lines are written for.
MOVING_DAYS = 300
MOVING = re.compile(r'\b(?:crawl\w*|walk\w*|toddl\w*|ran|run\w*|climb\w*|steps?|stood|standing)\b', re.IGNORECASE)
BEDTIMES = {'baby': '7', 'toddler': '7', 'small_child': '7:30', 'school_age': '8', 'teen': '10'}
SHEET_PEOPLE = 'grandparents'
RECENT_DAYS = 1
OLD_ERAS = {'victorian', 'steampunk', 'frontier', 'medieval', 'fantasy'}
# Things in the child's bank an older city doesn't have yet, beyond families.UNFIT: no flashlight in 1895, and no
# newspaper, piano, telescope or grocery list in Camelot.
_FLASHLIGHT = r'flashlights?'
_CASTLE = (_FLASHLIGHT + r'|newspapers?|telescopes?|pianos?|comics?|grocer(?:y|ies)|soccer|homework|debate team|'
           r'guitars?')
UNFIT = {era: re.compile(rf'\b(?:{words})\b', re.IGNORECASE) for era, words in (
    ('victorian', _FLASHLIGHT), ('steampunk', _FLASHLIGHT), ('frontier', _FLASHLIGHT), ('medieval', _CASTLE),
    ('fantasy', _CASTLE))}
NO_BIKES = {'medieval', 'fantasy'}

# (key, label, days from birth (low, high) or a special rule, eras it needs).
MILESTONES = (
    ('smile', 'First smile', (35, 60)), ('laugh', 'First laugh', (90, 130)), ('sleeps', 'Sleeps through the night', None),
    ('sits', 'Sitting up', (160, 220)), ('crawls', 'Crawling', (200, 300)), ('word', 'First word', (300, 420)),
    ('steps', 'First steps', (330, 450)), ('sentence', 'First sentence', (600, 800)),
    ('school', 'First day of school', None), ('bike', 'Rode a bike', (1900, 2600)),
    ('tooth', 'Lost a first tooth', (2150, 2400)), ('reads', 'Reading on their own', (2200, 2700)),
    ('big_school', 'Started big school', None), ('teen', 'Turned thirteen', 13), ('job', 'First job', (5700, 6100)),
    ('driving', 'Passed their driving test', (6200, 6550)), ('grown', 'Turned eighteen', 18),
)
MODERN_ONLY = {'big_school', 'driving'}
DID = {'smile': 'smiled for the first time', 'laugh': 'laughed out loud for the first time',
       'sleeps': 'slept right through the night for the first time', 'sits': 'sat up on {their} own',
       'crawls': 'started crawling', 'word': 'said {their} first word', 'steps': 'took {their} first steps',
       'sentence': 'said {their} first whole sentence', 'school': 'started school', 'bike': 'rode a bike on {their} own',
       'tooth': 'lost {their} first tooth', 'reads': 'read a whole book on {their} own',
       'big_school': 'started big school', 'teen': 'turned thirteen', 'job': 'started {their} first job',
       'driving': 'passed {their} driving test', 'grown': 'turned eighteen'}
OLD_DID = {'school': 'had {their} first lessons', 'job': 'started {their} first paid work'}
OLD_LABELS = {'school': 'First lessons', 'job': 'First paid work'}


@cache
def bank() -> dict:
    return json.loads((catalog.DATA / 'our_child.json').read_text(encoding='utf-8'))


@cache
def tags() -> dict[str, set[str]]:
    found = {}
    for tag, texts in bank()['tags'].items():
        for text in texts:
            found.setdefault(text, set()).add(tag)
    return found


def level(connection) -> int:
    row = optional(connection, 'SELECT * FROM life_settings WHERE id=1') or {}
    return int(row.get('family_life', USUAL))


def quiet(connection) -> bool:
    """With the adult side of life on, none of it goes on the calendar or in a reply carrying the adult side."""
    return families.withheld(connection)


def children(connection, timeline_id: str | None) -> list[dict]:
    """The pair's own children, oldest first, grown ones too."""
    if not ACTIVE or not timeline_id:
        return []
    return many(connection, "SELECT * FROM circle_children WHERE timeline_id=? AND title=? AND status='born' "
                'ORDER BY born_on, id', (timeline_id, TITLE))


def at_home(connection, timeline_id: str | None, day: date) -> list[dict]:
    """Those under 18 on this day."""
    return [child for child in children(connection, timeline_id) if families.age_of(child, day) < GROWN]


def journey_of(connection, child: dict) -> dict:
    row = optional(connection, 'SELECT route, arrived_on FROM family_journeys WHERE id=?', (child['storyline_id'],))
    return row or {'route': 'expecting_them', 'arrived_on': child['born_on']}


def arrived(connection, child: dict) -> date:
    return date.fromisoformat(journey_of(connection, child)['arrived_on'] or child['born_on'])


def first(name: str) -> str:
    return name.split()[0]


def companion_first(companion: dict) -> str:
    return first(companion['version']['definition']['name'])


def era(connection, companion: dict) -> str:
    return families.era_of(connection, companion['version']['definition'])


def band(child: dict, day: date) -> str | None:
    years = families.age_of(child, day)
    return next((key for key, low, high in BANDS if low <= years <= high), None)


def fitting(lines: list[dict], era_: str) -> list[dict]:
    """The bank lines for their city: its things (families.UNFIT) and its voice ('older' or 'modern' tags)."""
    unfit, wrong = families.UNFIT.get(era_), 'modern' if families.older(era_) else 'older'
    more = UNFIT.get(era_)
    found = [line for line in lines if not (unfit and unfit.search(line['text'])) and
             not (more and more.search(line['text'])) and wrong not in tags().get(line['text'], ())]
    return found or lines


def for_age(lines: list[dict], era_: str, days: int) -> list[dict]:
    """The lines for their city that a child this many days old can do: a line's 'from' is the age in years it is
    written for (a one-year-old doesn't carry the groceries), and a young baby eats nothing solid."""
    return [line for line in fitting(lines, era_) if line.get('from', 0) * 365 <= days and
            (days >= SOLIDS_DAYS or not FOOD.search(line['text']))]


def filled(text: str, child: dict, **values) -> str:
    line = families.fill_child(text, child)
    for key, value in values.items():
        line = line.replace(f'{{{key}}}', value)
    return line[:1].upper() + line[1:]


# The child's sheet ---------------------------------------------------------------------------------------------------

def sheet(connection, companion: dict, child: dict, day: date) -> dict | None:
    """{temperament, likes, quirk} for this day: a temperament for life, what they are into this month and a quirk
    this season, for their age band. A newborn has only their temperament yet, and a young baby eats nothing solid."""
    group = band(child, day)
    if group is None:
        return None
    seed, era_ = f"ours:{child['id']}", era(connection, companion)
    month, season = day.year * 12 + day.month, (day.year * 12 + day.month) // 3
    temperament = generators.pick(seed, 'temperament', bank()['temperaments'])['text']
    days = (day - date.fromisoformat(child['born_on'])).days
    if days < NEWBORN_DAYS:
        return {'temperament': temperament, 'likes': None, 'quirk': None}
    likes = filled(generators.pick(seed, f'likes:{group}:{month}', for_age(bank()[f'likes_{group}'], era_, days))['text'],
                   child)
    quirk = generators.pick(seed, f'quirk:{group}:{season}', for_age(bank()[f'quirks_{group}'], era_, days))['text']
    return {'temperament': temperament, 'likes': likes[:1].lower() + likes[1:], 'quirk': filled(quirk, child)}


# Milestones -------------------------------------------------------------------------------------------------------

def span(seed: str, label: str, low_high: tuple[int, int]) -> int:
    low, high = low_high
    return low + int(generators.unit(seed, label) * (high - low + 1))


def first_monday_of_september(year: int) -> date:
    day = date(year, 9, 1)
    return day + timedelta(days=(7 - day.weekday()) % 7)


def school_start(born: date, years: int) -> date:
    """The first Monday in September once they are `years` old."""
    day = first_monday_of_september(born.year + years)
    return day if ages.age_on(born, born.strftime('%m-%d'), day) >= years else first_monday_of_september(
        born.year + years + 1)


def milestone_day(key: str, rule, born: date, seed: str, level_: int) -> date:
    if key == 'sleeps':
        return born + timedelta(days=span(seed, key, SLEEPS[level_]))
    if key in ('school', 'big_school'):
        return school_start(born, SCHOOL if key == 'school' else 11)
    if isinstance(rule, int):
        return ages.birthday_in(born.year + rule, born.strftime('%m-%d'))
    return born + timedelta(days=span(seed, key, rule))


def fits_era(key: str, era_: str) -> bool:
    if key in MODERN_ONLY:
        return not families.older(era_)
    return key != 'bike' or era_ not in NO_BIKES


def milestones(connection, companion: dict, child: dict) -> list[dict]:
    """Every milestone with its day, those before the child came home left out: {key, label, on}."""
    born, seed, era_ = date.fromisoformat(child['born_on']), f"ours:{child['id']}", era(connection, companion)
    home, level_, old = arrived(connection, child), level(connection), families.older(era_)
    result = []
    for key, label, rule in MILESTONES:
        if not fits_era(key, era_):
            continue
        day = milestone_day(key, rule, born, seed, level_)
        if day > home or key in ('teen', 'grown'):
            result.append({'key': key, 'label': (OLD_LABELS.get(key) if old else None) or label,
                           'on': day.isoformat()})
    return sorted(result, key=lambda item: item['on'])


def did(connection, companion: dict, child: dict, key: str) -> str:
    text = (OLD_DID.get(key) if families.older(era(connection, companion)) else None) or DID[key]
    return families.fill_child(text, child)


def reached(connection, companion: dict, child: dict, day: date) -> list[dict]:
    return [item for item in milestones(connection, companion, child) if item['on'] <= day.isoformat()]


def sleeping_through(connection, companion: dict, child: dict, day: date) -> bool:
    return any(item['key'] == 'sleeps' for item in reached(connection, companion, child, day)) or \
        families.age_of(child, day) >= 1


# Who stays home ----------------------------------------------------------------------------------------------------

def family_row(connection, timeline_id: str) -> dict:
    return optional(connection, 'SELECT * FROM our_family WHERE timeline_id=?', (timeline_id,)) or {}


def care_facts(connection, companion: dict, now) -> dict:
    """What the engine reads for who stays home: whether the companion works, their money, who carried the first
    child, whether they wanted children and the city's era."""
    from companion.life import money, parenthood, work
    definition, kids = companion['version']['definition'], children(connection, companion['active_timeline_id'])
    route = journey_of(connection, kids[0])['route'] if kids else ''
    found = money.profile(definition)
    return {'works': int(work.works(definition)), 'tier': found.tier if found else 1,
            'carried': int(route == 'expecting_them'), 'carried_you': int(route == 'expecting_you'),
            'wants': parenthood.wants(connection, companion), 'old': int(families.older(era(connection, companion))),
            'level': level(connection)}


def care_found(connection, companion: dict, now=None) -> dict:
    """{care, how ('set' or 'seeded'), consequence_id}: who looks after the children until the youngest is at school.
    Recorded once the first child is home (`advance`); a read with no clock works it out the same way."""
    timeline_id = companion['active_timeline_id']
    set_to = family_row(connection, timeline_id).get('care')
    if set_to:
        return {'care': set_to, 'how': 'set', 'consequence_id': None}
    subject = f'family:care:{timeline_id}'
    if now is not None:
        outcome = steps.decide(connection, companion, 'family:care', subject, care_facts(connection, companion, now),
                               FAMILY.topic, now)
    else:
        outcome = consequences.recorded(connection, subject, 'family:care')
        if outcome is None:
            options = consequences.odds('family:care', care_facts(connection, companion, None),
                                        steps.names(companion, FAMILY.topic))
            outcome = {'id': None, 'picked': consequences.roll(f'{timeline_id}:{subject}:family:care', options)}
    return {'care': CARE[outcome['picked']], 'how': 'seeded', 'consequence_id': outcome['id']}


def caring(connection, companion: dict, day: date, apart: dict | None | bool = False) -> str | None:
    """Who looks after them on this day: the care picked while the youngest is under school age, else None. Split up
    (companion/life/custody.py), the companion works and the children go to daycare in their weeks, none when they
    live with the user. `apart` is custody.found when the caller has it, for a run of days."""
    from companion.life import custody
    kids = at_home(connection, companion['active_timeline_id'], day)
    if not kids or families.age_of(kids[-1], day) >= SCHOOL:
        return None
    split = custody.found(connection, companion) if apart is False else apart
    if split and split['split']:
        return None if split['pattern'] == 'with_you' else 'both_work'
    return care_found(connection, companion)['care']


def companion_of(connection, timeline_id: str) -> dict | None:
    from companion.characters import by_id
    row = optional(connection, 'SELECT companion_id FROM timelines WHERE id=?', (timeline_id,))
    found = by_id(connection, row['companion_id']) if row else None
    return {**found, 'active_timeline_id': timeline_id} if found else None


def pay(connection, timeline_id: str, day: date) -> float:
    """Their pay as a share of a full one on this day (companion/life/work.py `pay`)."""
    companion = companion_of(connection, timeline_id) if children(connection, timeline_id) else None
    if companion is None:
        return 1.0
    return PAY.get(caring(connection, companion, day) or '', 1.0)


# Their days ----------------------------------------------------------------------------------------------------------

def leave_weeks(connection, child: dict) -> int:
    route = journey_of(connection, child)['route']
    return LEAVE_WEEKS.get(route, ADOPTING_LEAVE)


def days_off(connection, companion: dict, start: date, end: date) -> dict[str, str]:
    """{local date: label} for companion/life/work.py `days_off`: parental leave after each child comes, then days at
    home by who looks after them (every workday at home, or one a week part-time) and sick days."""
    from companion.life import work
    timeline_id = companion.get('active_timeline_id')
    if not children(connection, timeline_id):
        return {}
    from companion.life import custody
    workdays, result, apart = work.workdays(companion['version']['definition']), {}, custody.found(connection, companion)
    day = start
    while day <= end:
        if label := day_label(connection, companion, day, workdays, apart):
            result[day.isoformat()] = label
        day += timedelta(days=1)
    return result


def day_label(connection, companion: dict, day: date, workdays, apart: dict | None) -> str | None:
    kids = at_home(connection, companion['active_timeline_id'], day)
    if not kids or day.weekday() not in workdays:
        return None
    for child in kids:
        home = arrived(connection, child)
        if home <= day < home + timedelta(weeks=leave_weeks(connection, child)):
            return LEAVE
    care = caring(connection, companion, day, apart)
    if care == 'them_home' or care == 'part_time' and day.weekday() == part_time_day(companion, workdays):
        return HOME_DAY
    if care != 'you_home' and any(sick_on(connection, child, day) for child in kids) and custody_here(apart, day):
        return SICK_DAY
    return None


def part_time_day(companion: dict, workdays) -> int | None:
    days = sorted(workdays)
    return generators.pick(f"ours:{companion['active_timeline_id']}", 'part-time-day', days) if days else None


def custody_here(apart: dict | None, day: date) -> bool:
    from companion.life import custody
    return custody.with_them(apart, day)


def with_you(connection, companion: dict, day: date) -> bool:
    """Whether the children are with the companion on this day: always, unless their parents live apart
    (companion/life/custody.py)."""
    from companion.life import custody
    return custody.here(connection, companion, day)


def sick_on(connection, child: dict, day: date) -> bool:
    """Whether a child (1 to 12) is home sick on this day: a few workdays a year by Family life."""
    years = families.age_of(child, day)
    count = SICK_DAYS[level(connection)]
    if not count or not 1 <= years <= 12:
        return False
    rng = random.Random(f"ours:{child['id']}:sick:{day.year}")
    start = date(day.year, 1, 1)
    workdays = [start + timedelta(days=offset) for offset in range(365) if (start + timedelta(days=offset)).weekday() < 5]
    return day in set(rng.sample(workdays, count))


def broken_night(connection, timeline_id: str, day: date) -> dict | None:
    """The body state a broken night leaves (companion/life/agenda.py `day_facts`): tired, until the youngest sleeps
    through; less often once they are a toddler. None on an easy life."""
    chance = BROKEN[level(connection)]
    kids = at_home(connection, timeline_id, day) if chance else []
    if not kids:
        return None
    youngest = kids[-1]
    companion = companion_of(connection, timeline_id)
    if companion is None or arrived(connection, youngest) > day - timedelta(days=1) or \
            not with_you(connection, companion, day - timedelta(days=1)):
        return None
    if sleeping_through(connection, companion, youngest, day):
        chance = chance / 3 if families.age_of(youngest, day) < 3 else 0.0
    if generators.unit(f"ours:{youngest['id']}", 'night', day.isoformat()) >= chance:
        return None
    return {'state': 'tired', 'because': 'after a broken night'}


def purchases(connection, timeline_id: str, start: date, day: date) -> list[dict]:
    """Childcare each month while both work (half while part-time) until the youngest is at school, and a paid sitter
    for an evening out when nobody in the family nearby can (companion/life/money.py household)."""
    from companion.life import money
    companion = companion_of(connection, timeline_id) if children(connection, timeline_id) else None
    found = money.profile(companion['version']['definition']) if companion else None
    if not found:
        return []
    from companion.life import custody
    month, result, apart = money.monthly_share(found), [], custody.found(connection, companion)
    old = OLD_CARE if families.older(era(connection, companion)) else 1.0
    paid = start
    while paid <= day:
        share = CHILDCARE.get(caring(connection, companion, paid, apart) or '', 0)
        if share and paid.day == 1 and not any(on_leave(connection, child, paid) for child in
                                                at_home(connection, timeline_id, paid)):
            result.append({'text': 'paid their half of the childcare', 'date': paid.isoformat(), 'spend': '',
                           'cost': round(month * share * old, 2), 'for': 'childcare'})
        paid += timedelta(days=1)
    for outing in evenings_out(connection, companion, start, day):
        if sitter_for(connection, companion, date.fromisoformat(outing['local_date']))['paid']:
            result.append({'text': 'paid a sitter for an evening out', 'date': outing['local_date'], 'spend': '',
                           'cost': round(month * SITTER, 2), 'for': 'sitter'})
    return result


def on_leave(connection, child: dict, day: date) -> bool:
    home = arrived(connection, child)
    return home <= day < home + timedelta(weeks=leave_weeks(connection, child))


def evenings_out(connection, companion: dict, start: date, end: date) -> list[dict]:
    from companion.life import outings
    return [outing for outing in outings.in_force(connection, companion['active_timeline_id'], start.isoformat())
            if outing['local_date'] <= end.isoformat() and outing['activity'] in OUT_ACTIVITIES
            and (outing['at_time'] or '') >= EVENING]


def sitter_for(connection, companion: dict, day: date) -> dict:
    """Who watches the children under 13 while the pair is out for the evening: a grandparent, an aunt or an uncle
    nearby (seeded), else a paid sitter. {who, paid}; who None with nobody to watch."""
    kids = [child for child in at_home(connection, companion['active_timeline_id'], day)
            if families.age_of(child, day) < SITTER_UNDER]
    if not kids:
        return {'who': None, 'paid': False}
    family = [person for person in relatives(connection, companion) if person['local']]
    person = generators.pick(f"ours:{companion['active_timeline_id']}", f'sitter:{day.isoformat()}', family) \
        if family and generators.unit(f"ours:{companion['active_timeline_id']}", 'sitter', day.isoformat()) < 0.7 \
        else None
    if person:
        return {'who': person['said'], 'paid': False}
    return {'who': 'a sitter' if not families.older(era(connection, companion)) else 'a neighbor', 'paid': True}


def relatives(connection, companion: dict) -> list[dict]:
    """The companion's parents and siblings (the children's grandparents, aunts and uncles), as they say them:
    {id, kind ('grandparents' or 'aunts_uncles'), said ('your mom Ana'), local}."""
    from companion.life import circle
    result = []
    for person in circle.people(connection, companion['active_timeline_id']):
        kind, details = circle.role_kind(person['role']), decode(person['details']) or {}
        if kind not in ('parent', 'sibling') or details.get('late') or details.get('our_child'):
            continue
        role = circle.said(circle.relation(kind, details.get('pronouns') or ''), companion['version']['definition'])
        result.append({'id': person['id'], 'kind': 'grandparents' if kind == 'parent' else 'aunts_uncles',
                       'said': f"your {role} {first(person['name'])}", 'local': details.get('local', True) is not False})
    return result


# Family days out ------------------------------------------------------------------------------------------------------

def outing_ages(connection, timeline_id: str, day: date) -> list[dict]:
    return [child for child in at_home(connection, timeline_id, day)
            if OUTING_AGES[0] <= families.age_of(child, day) <= OUTING_AGES[1]]


def family_outings(connection, companion: dict) -> list[dict]:
    from companion.life import outings
    return [outing for outing in outings.in_force(connection, companion['active_timeline_id'])
            if outing['place'].get('family')]


def plan_outing(connection, companion: dict, today: date, now) -> dict | None:
    """Every five weeks or so, a weekend day out with the user and the children (1 to 15): a walk in the park, or the
    zoo or a museum in a city that has them. An outing like any other, with the children in words only (no photo)."""
    from companion.life import outings, together, wedding
    timeline_id = companion['active_timeline_id']
    if quiet(connection) or steps.apart(connection, companion) or not outing_ages(connection, timeline_id, today):
        return None
    last = max((date.fromisoformat(item['local_date']) for item in family_outings(connection, companion)),
               default=today - timedelta(days=OUTING_EVERY))
    due = max(last + timedelta(days=OUTING_EVERY), today + timedelta(days=2))
    day = due + timedelta(days=(5 - due.weekday()) % 7 + int(generators.unit(timeline_id, 'family-day', due) * 2))
    if day > today + timedelta(days=OUTING_AHEAD) or outings.taken(connection, companion, day):
        return None
    data, definition = outings.city_data(connection, companion['version']['definition']), companion['version']['definition']
    activity = 'museum' if not families.older(era(connection, companion)) and \
        generators.unit(timeline_id, 'family-kind', day) < 0.4 else 'walk'
    item = outings.pick_place(data, activity, day, '11:00', definition, f'ours:{timeline_id}:{day}', True,
                              'zoo aquarium' if activity == 'museum' else '') if data else None
    anchor = wedding.anchor(connection, timeline_id)
    if item is None or anchor is None:
        return None
    names = [first(child['name']) for child in outing_ages(connection, timeline_id, day)]
    place = {**outings.place_view(item, data), 'family': names, 'no_photo': True}
    return together.insert(connection, companion, anchor, activity, place, day, '11:00', '15:00', None, stamp(now))


def doing(outing: dict) -> str:
    """'took Mia to Patterson Park' (companion/life/outings.py `doing`)."""
    return f"took {steps.names_text(outing['place']['family'])} to {outing['place']['name']}"


# Each day --------------------------------------------------------------------------------------------------------

def advance(connection, companion: dict, world, now) -> None:
    """Once a day (companion/life/agenda.py): who stays home is decided once the first child is home, a child who
    turned 18 joins the circle as an adult, and a family day out is planned when one is due."""
    timeline_id = companion.get('active_timeline_id')
    kids = children(connection, timeline_id)
    if not kids or companion['version']['definition'].get('relationship') != 'romance':
        return
    today = steps.local_today(companion, now)
    ensure_row(connection, timeline_id, now)
    care_found(connection, companion, now)
    from companion.life import custody
    custody.advance(connection, companion, now)
    for child in kids:
        if families.age_of(child, today) >= GROWN:
            grow_up(connection, companion, world, child, today, now)
    plan_outing(connection, companion, today, now)


def ensure_row(connection, timeline_id: str, now) -> None:
    connection.execute('INSERT OR IGNORE INTO our_family (timeline_id, care, created_at, updated_at) VALUES '
                       '(?, NULL, ?, ?)', (timeline_id, stamp(now), stamp(now)))


def grow_up(connection, companion: dict, world, child: dict, today: date, now) -> str | None:
    """At 18 the child is an adult person in their circle (a son or daughter, living in town), once."""
    from companion.life import circle
    timeline_id = companion['active_timeline_id']
    rows = circle.people(connection, timeline_id, include_removed=True)
    found = next((row for row in rows if grown_as(row, child)), None)
    if found:
        return found['id']
    person = circle.build(companion['version']['definition'], world, timeline_id, 1, f"ours:{child['id']}:grown",
                          {row['name'] for row in rows}, sheet=False)[0]
    role = {'she/her': 'daughter', 'he/him': 'son'}.get(child['pronouns'], 'child')
    person |= {'name': first(child['name']), 'role': role,
               'details': person['details'] | {'pronouns': child['pronouns'], 'age': families.age_of(child, today),
                                               'local': True, 'our_child': child['id']}}
    ordinal = max((row['ordinal'] for row in rows), default=-1) + 1
    circle.insert(connection, timeline_id, [person], ordinal, now)
    person_id = optional(connection, 'SELECT id FROM circle_people WHERE timeline_id=? AND ordinal=?',
                         (timeline_id, ordinal))['id']
    born = date.fromisoformat(child['born_on'])
    ages.keep(connection, 'circle', person_id, families.age_of(child, today), born.strftime('%m-%d'), today, now)
    return person_id


def grown_as(person: dict, child: dict) -> bool:
    """Whether a circle person is this child grown up (on a fork the child's row is a copy, so by name too)."""
    details = decode(person['details']) or {}
    return bool(details.get('our_child')) and (details['our_child'] == child['id'] or
                                               first(person['name']) == first(child['name']))


def grown_child(person: dict) -> bool:
    """A circle person who is the pair's grown child: never a romance, never in Matchlight, never with the adult
    side."""
    return bool((decode(person['details']) or {}).get('our_child'))


# The chat context ----------------------------------------------------------------------------------------------------

def child_text(connection, child: dict, today: date) -> str:
    """'- Mia (your daughter, 2 years old): yours and the user's, adopted.'"""
    from companion.life import expecting
    route = journey_of(connection, child)['route']
    row = optional(connection, 'SELECT * FROM family_journeys WHERE id=?', (child['storyline_id'],))
    whose = 'adopted' if route in expecting.ADOPTING else ''
    if route in expecting.FOSTERING and row and not any(
            stage['key'] == 'adopted' and stage['on'] <= today.isoformat() for stage in decode(row['stages']) or []):
        whose = 'your foster child'
    word = {'she/her': 'daughter', 'he/him': 'son'}.get(child['pronouns'], 'child')
    return (f"- {child['name']} (your {word}, {families.how_old(child, today)}): yours and the user's"
            f"{', ' + whose if whose else ''}.")


def context_lines(connection, companion: dict, now) -> list[tuple[str, str]]:
    """(identity, line) for the 'kids' section: each child of the pair under 18 with their sheet, who looks after
    them, their days, what their grandparents, aunts and uncles are like with them, and their part in a holiday that
    is near. None in a reply carrying the adult side's lines."""
    timeline_id = companion.get('active_timeline_id')
    today = steps.local_today(companion, now) if timeline_id else None
    kids = at_home(connection, timeline_id, today) if today else []
    if not kids or quiet(connection):
        return []
    result = []
    for child in kids:
        result.append((f"ours:{child['id']}", child_text(connection, child, today)))
        if found := sheet(connection, companion, child, today):
            result.append((f"ours:sheet:{child['id']}:{today.month}", sheet_line(child, found)))
        result += people_line(connection, companion, child, today) + holiday_line(connection, companion, child, today)
    from companion.life import custody
    return result + custody.context_lines(connection, companion, kids, today, now) + \
        days_lines(connection, companion, kids, today)


def sheet_line(child: dict, found: dict) -> str:
    """'- Mia is easygoing and quick to laugh. Lately she is into puddles. Mia names every bird Gerald.'"""
    line = f"- {first(child['name'])} is {found['temperament']}."
    if found['likes']:
        line += (f" Lately {families.fill_child('{they}', child)} {families.fill_child('{are}', child)} into "
                 f"{found['likes']}. {found['quirk']}")
    return line


CARE_WORDS = {
    'both_work': 'you both work; on workdays {names} {go} to {minder}',
    'part_time': 'you went part-time to be with {names} more, home on {day}s; the rest of the week {names} {go} to '
                 '{minder}',
    'them_home': 'you stay home with {names} for now, and the user works',
    'you_home': 'the user stays home with {names} for now, and you work',
    'split': 'on your workdays {names} {go} to {minder}',
}


def days_lines(connection, companion: dict, kids: list[dict], today: date) -> list[tuple[str, str]]:
    """Who looks after them, and the shape of the day: the school run and bedtime."""
    names = steps.names_text([first(child['name']) for child in kids])
    result, here = [], with_you(connection, companion, today)
    if (care := caring(connection, companion, today)) and here:
        from companion.life import custody, work
        care = 'split' if (custody.found(connection, companion) or {}).get('split') else care
        minder = 'a neighbor who minds children' if families.older(era(connection, companion)) else 'daycare'
        day = part_time_day(companion, work.workdays(companion['version']['definition']))
        words = CARE_WORDS[care].format(names=names, go='go' if len(kids) > 1 else 'goes', minder=minder,
                                        day=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday',
                                             'Sunday'][day or 0])
        result.append((f'ours:care:{care}', f'- Looking after {names}: {words}.'))
    school = [first(child['name']) for child in kids if SCHOOL <= families.age_of(child, today) <= 12]
    youngest = kids[-1]
    bed = BEDTIMES[band(youngest, today)]
    run = f"weekday mornings start with the school run for {steps.names_text(school)}; " if school else ''
    if here:
        result.append((f'ours:routine:{bool(school)}:{bed}', f"- Your days with {names}: {run}bedtime is around {bed}"
                                                            f"{'' if band(youngest, today) == 'teen' else ' in the evening'}."))
    return result


def people_line(connection, companion: dict, child: dict, today: date) -> list[tuple[str, str]]:
    """Each month, one of their grandparents, aunts or uncles with them, from the bank, for a child of the ages the
    lines are written for."""
    people = relatives(connection, companion)
    if not PEOPLE_AGES[0] <= families.age_of(child, today) <= PEOPLE_AGES[1]:
        return []
    month = today.year * 12 + today.month
    person = generators.pick(f"ours:{child['id']}", f'people:{month}', people)
    if person is None or arrived(connection, child) > today - timedelta(days=30):
        return []
    line = generators.pick(f"ours:{child['id']}", f'people-line:{month}',
                           fitting(bank()[person['kind']], era(connection, companion)))['text']
    return [(f"ours:people:{child['id']}:{month}", f"- {filled(line, child, who=person['said'])}")]


def holiday_line(connection, companion: dict, child: dict, today: date) -> list[tuple[str, str]]:
    """A kept tradition just kept (that day and the few after): the child's part in it, for their age. A baby not
    yet on the move has no lines about crawling or walking."""
    from companion.life import traditions
    kept = [item for item in traditions.upcoming(connection, companion, today - timedelta(days=HOLIDAY_AFTER),
                                                 HOLIDAY_AFTER) if item['date'] <= today]
    if not kept:
        return []
    holiday, years = kept[-1], families.age_of(child, today)
    moving = (today - date.fromisoformat(child['born_on'])).days >= MOVING_DAYS
    lines = [line for line in fitting(bank()['holiday_part'], era(connection, companion))
             if line['ages'][0] <= years <= line['ages'][1] and (moving or not MOVING.search(line['text']))]
    line = generators.pick(f"ours:{child['id']}", f"holiday:{holiday['holiday']}:{today.year}", lines)
    if line is None:
        return []
    text = line['text'].replace('a {holiday}', 'an {holiday}') if holiday['name'][:1] in 'AEIO' else line['text']
    return [(f"ours:holiday:{child['id']}:{holiday['holiday']}", f"- {filled(text, child, holiday=holiday['name'])}")]


def today_lines(connection, companion: dict, now) -> list[tuple[str, str]]:
    """For 'circle_now': a milestone today or yesterday, a broken night, a sick day, a sitter tonight."""
    timeline_id = companion.get('active_timeline_id')
    today = steps.local_today(companion, now) if timeline_id else None
    kids = at_home(connection, timeline_id, today) if today else []
    if not kids or quiet(connection):
        return []
    result = []
    for child in kids:
        for item in reached(connection, companion, child, today):
            gap = (today - date.fromisoformat(item['on'])).days
            if gap <= RECENT_DAYS and item['key'] != 'grown':
                when = 'today' if gap == 0 else 'yesterday'
                result.append((f"ours:milestone:{child['id']}:{item['key']}",
                               f"- {first(child['name'])} {did(connection, companion, child, item['key'])} {when}."))
        if sick_on(connection, child, today) and today.weekday() < 5 and with_you(connection, companion, today):
            result.append((f"ours:sick:{child['id']}", f"- {first(child['name'])} is home sick today, so one of you "
                                                        f"is home to look after {families.fill_child('{them}', child)}."))
    if broken_night(connection, timeline_id, today):
        result.append(('ours:night', f"- {first(kids[-1]['name'])} had you up in the night; you're running on "
                                     'little sleep today.'))
    if evenings_out(connection, companion, today, today):
        who = sitter_for(connection, companion, today)['who']
        if who:
            names = steps.names_text([first(child['name']) for child in kids
                                      if families.age_of(child, today) < SITTER_UNDER])
            result.append(('ours:sitter', f'- Tonight {who} is watching {names} while you two are out.'))
    from companion.life import custody
    return result + custody.today_line(connection, companion, kids, today)


# The screens --------------------------------------------------------------------------------------------------------

def child_view(connection, companion: dict, child: dict, today: date) -> dict:
    found = sheet(connection, companion, child, today) or {}
    done = reached(connection, companion, child, today)
    years = families.age_of(child, today)
    return {'id': child['id'], 'name': child['name'], 'pronouns': child['pronouns'], 'born_on': child['born_on'],
            'arrived_on': arrived(connection, child).isoformat(), 'journey_id': child['storyline_id'],
            'age': years, 'age_text': families.age_text(child, today), 'grown': years >= GROWN,
            'relation': {'she/her': 'daughter', 'he/him': 'son'}.get(child['pronouns'], 'child'),
            'temperament': found.get('temperament'), 'likes': found.get('likes'), 'quirk': found.get('quirk'),
            'milestones': [{'key': item['key'], 'label': item['label'], 'date': item['on']} for item in done],
            'latest': ({'label': done[-1]['label'], 'date': done[-1]['on']} if done else None)}


def view(connection, companion: dict, now, show_odds: bool) -> dict:
    """The pair's children for the Family panel and Today: each child and who looks after them."""
    timeline_id = companion.get('active_timeline_id')
    kids = children(connection, timeline_id)
    if not kids:
        return {'shown': False, 'children': []}
    from companion.life import custody
    today = steps.local_today(companion, now)
    care = care_found(connection, companion)
    name = companion_first(companion)
    apart = custody.view(connection, companion, show_odds)
    return {'shown': True, 'children': [child_view(connection, companion, child, today) for child in kids],
            'care': care['care'], 'care_how': care['how'],
            'care_now': caring(connection, companion, today) is not None and not (apart and apart['split']),
            'care_consequence_id': care['consequence_id'] if show_odds else None,
            'cares': [{'key': key, 'label': CARE_LABELS[key].format(name=name)} for key in CARE], 'custody': apart}


def today_view(connection, companion: dict, now) -> list[dict]:
    """For Today: each child under 18, their age, what they are into lately and the latest milestone."""
    from companion.life import custody
    timeline_id = companion.get('active_timeline_id')
    today = steps.local_today(companion, now) if timeline_id else None
    kids = at_home(connection, timeline_id, today) if today else []
    where = custody.where_today(connection, companion, today) if kids else None
    return [{**{key: value for key, value in child_view(connection, companion, child, today).items()
                if key in ('id', 'name', 'age_text', 'relation', 'likes', 'latest')}, 'where_today': where}
            for child in kids]


def update(connection, companion: dict, now, care: str | None = None, child_id: str | None = None,
           name: str | None = None, custody: str | None = None) -> None:
    """The user sets who looks after them ('auto' lets the app decide again), where they live after a breakup, or
    renames a child."""
    timeline_id = companion['active_timeline_id']
    require(bool(children(connection, timeline_id)), 'There is no child of yours yet.', 404)
    if care is not None:
        require(care in ('auto', *CARE), 'Pick who looks after them.', 422)
        ensure_row(connection, timeline_id, now)
        connection.execute('UPDATE our_family SET care=?, updated_at=? WHERE timeline_id=?',
                           (None if care == 'auto' else care, stamp(now), timeline_id))
    if custody is not None:
        from companion.life import custody as apart
        apart.update(connection, companion, custody, now)
    if child_id is not None and name is not None:
        rename(connection, companion, child_id, name, now)


def rename(connection, companion: dict, child_id: str, name: str, now) -> None:
    child = optional(connection, 'SELECT * FROM circle_children WHERE id=? AND timeline_id=? AND title=?',
                     (child_id, companion['active_timeline_id'], TITLE))
    require(child is not None, 'That child is not one of yours.', 404)
    name = ' '.join(name.split())
    require(0 < len(name) <= 40, 'Give a name of up to 40 characters.', 422)
    connection.execute('UPDATE circle_children SET name=?, updated_at=? WHERE id=?', (name, stamp(now), child_id))
    row = optional(connection, 'SELECT * FROM family_journeys WHERE id=?', (child['storyline_id'],))
    if row:
        connection.execute('UPDATE family_journeys SET details=?, updated_at=? WHERE id=?',
                           (encode({**(decode(row['details']) or {}), 'name': name, 'renamed': True}), stamp(now),
                            row['id']))


def change(connection, companion: dict, consequence_id: str, option: int, now) -> dict:
    """Who stays home made to go another way under Hidden values: the days and money follow the pick."""
    consequences.change(connection, consequence_id, option, stamp(now))
    return consequences.by_id(connection, consequence_id)


# The scrapbook and branches -------------------------------------------------------------------------------------------

def scrapbook_items(connection, companion: dict, low: date, high: date) -> list[dict]:
    """Each milestone in a stretch of days, for the companion's year (companion/life/scrapbook.py)."""
    result = []
    for child in children(connection, companion.get('active_timeline_id')):
        for item in milestones(connection, companion, child):
            if low.isoformat() <= item['on'] <= high.isoformat():
                result.append({'date': item['on'], 'text': f"{first(child['name'])}: {item['label'].lower()}"})
    return result


def copy(connection, parent_id: str, new_id: str) -> None:
    """A fork keeps who looks after them and where they live after a breakup (the children come with the journeys,
    companion/life/expecting.py)."""
    row = family_row(connection, parent_id)
    if row:
        connection.execute('INSERT INTO our_family (timeline_id, care, custody, created_at, updated_at) VALUES '
                           '(?, ?, ?, ?, ?)', (new_id, row['care'], row['custody'], row['created_at'], row['updated_at']))
