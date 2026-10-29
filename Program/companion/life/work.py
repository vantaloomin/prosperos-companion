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
import re
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

from companion.clock import stamp, zone
from companion.database import decode, encode, identifier, many, optional
from companion.errors import require
from companion.life import admin, job_words, money, outings, routine, shifts
from companion.world import catalog, generators, wording

DATA = Path(__file__).parents[1] / 'world' / 'data' / 'work_life.json'
# Off in tests unless a test turns it on (tests/conftest.py), so other tests' days stay as written.
ACTIVE = True
LEVELS = (0, 1, 2, 3)
DEFAULT_LEVEL = 2
# Per level: the chance a week is slammed, and that it is slow; the rest are ordinary.
WEEKS = {0: (0.0, 0.0), 1: (0.06, 0.2), 2: (0.18, 0.15), 3: (0.28, 0.12)}
# The chance the week a project is due is slammed, by level: on Steady a deadline is mostly met without a crunch.
DUE_SLAMMED = {0: 0.0, 1: 0.3, 2: 1.0, 3: 1.0}
# Late nights on the calendar in a slammed week, by level (fewest, most).
LATE_NIGHTS = {0: (0, 0), 1: (0, 1), 2: (1, 2), 3: (1, 3)}
LATE_MINUTES = (90, 180)
# At the yearly review: the chance of a promotion instead of a raise, and of no raise at all.
PROMOTION = {0: 0.0, 1: 0.1, 2: 0.15, 3: 0.2}
PROMOTION_RAISE = (8.0, 15.0)
# A storyline promotion raises pay only when there was no promotion in the year before it.
PROMOTION_GAP_DAYS = 365
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
# How far ahead the user can move a project's due date.
DUE_AHEAD_DAYS = 365
# How a project turns out: (well, fine) chances by level; the rest is rough.
OUTCOMES = {0: (0.6, 0.3), 1: (0.65, 0.3), 2: (0.55, 0.3), 3: (0.45, 0.3)}
OUTCOME_WORDS = {'well': 'it went well', 'fine': 'it went fine', 'rough': 'it was a rough one'}
# Disruptions' work table tilted by the week (companion/life/disruptions.py tilts).
TILTS = {'slammed': {'over': 3.0}, 'slow': {'over': 0.25}}
# Long enough that a yearly review is never skipped after months away.
CATCH_UP_DAYS = 400
AHEAD_DAYS = 14
RECENT_DAYS = 30
# Days off the agenda shows for work life (agenda.holiday_block), by the name it is given.
LABELS = {'Vacation': 'Vacation day', 'Job hunt': 'Job hunting', 'Parental leave': 'On parental leave',
          'Home day': 'A day at home', 'Family sick day': 'A day off to look after family',
          'Bed rest': 'On bed rest at home'}
LATE_TITLE = 'Staying late at work'
STUDY_LATE_TITLE = 'Late night studying'
STUDY_LATE_DONE = 'stayed up late studying for '
LATE_DONE = 'stayed late at work on '
WORKLOAD_WORDS = {'slammed': 'Slammed this week', 'normal': 'An ordinary week at work', 'slow': 'A slow week at work'}
STUDY_WORKLOAD = {'slammed': 'Slammed this week', 'normal': 'An ordinary week of classes', 'slow': 'A light week of classes'}
WEEK_LINES = {'slammed': 'Work is slammed this week.', 'slow': 'Work is slow this week.', 'normal': 'An ordinary week at work.'}
STUDY_WEEK_LINES = {'slammed': 'Your classes are slammed this week.', 'slow': 'A light week of classes.',
                    'normal': 'An ordinary week of classes.'}
YEARS = ('first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh')

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
# Which projects in a kind's bank fit a career (the projects' `fits`; a project without `fits` suits anyone of the
# kind): by career id first, then by sector. A career with neither draws only the projects anyone of the kind could do.
TRADES_BY_SECTOR = {
    'finance': ('finance', 'insurance'), 'insurance': ('insurance', 'finance'), 'legal': ('legal',),
    'real-estate': ('property',), 'business': ('marketing', 'clerical'), 'clerical': ('clerical',),
    'commerce': ('clerical', 'trade'), 'trade': ('trade', 'finance'),
    'technology': ('software',), 'biotech': ('science',), 'science': ('science',), 'engineering': ('engineering',),
    'aerospace': ('engineering',),
    'healthcare': ('clinical',), 'medicine': ('clinical',), 'healing': ('clinical', 'pharmacy'), 'care': ('clinical',),
    'social-services': ('social',), 'religion': ('church',), 'church': ('church',), 'spiritualism': ('church',),
    'education': ('school',), 'learning': ('school', 'library'),
    'hospitality': ('food',), 'food': ('food',), 'victualling': ('food',), 'retail': ('retail',),
    'tourism': ('leisure',), 'recreation': ('leisure',), 'fitness': ('leisure',), 'services': ('hospitality',),
    'domestic': ('household',), 'domestic-service': ('household',), 'household': ('household',),
    'court': ('household',), 'palace': ('household', 'food'), 'gardens': ('household',),
    'construction': ('building',), 'building': ('building',), 'city-works': ('building',), 'crafts': ('crafts',),
    'cloth': ('crafts',), 'garment': ('crafts',), 'textiles': ('crafts', 'industry'), 'agriculture': ('farming',),
    'farming': ('farming',), 'ranching': ('farming',), 'forest': ('farming',), 'milling': ('farming', 'industry'),
    'fishing': ('sea',), 'maritime': ('sea',), 'marine-trades': ('sea', 'crafts'), 'shipbuilding': ('sea', 'crafts'),
    'manufacturing': ('industry',), 'mining': ('industry',), 'quarrying': ('industry',),
    'logistics': ('shipping',), 'shipping': ('shipping',), 'river': ('shipping',), 'transit': ('transit',),
    'railroad': ('transit',), 'freight': ('freight',), 'communications': ('post',),
    'entertainment': ('stage', 'music'), 'music': ('music',), 'creative': ('design',), 'arts': ('photo', 'design'),
    'media': ('press',), 'press': ('press',), 'newspaper': ('press',),
    'law': ('police',), 'law-enforcement': ('police',), 'security': ('police',), 'gates': ('police',),
    'public-safety': ('police',), 'military': ('military',), 'army': ('military',), 'defense': ('military',),
    'government': ('government',), 'labour': ('government',),
}
TRADES_BY_CAREER = {
    'underwriter': ('insurance', 'finance'), 'marketing-coordinator': ('marketing',), 'counting-clerk': ('trade', 'finance'),
    'merchant-factor': ('trade', 'finance'), 'courier': ('clerical', 'trade'), 'office-clerk': ('clerical',),
    'stenographer': ('clerical', 'legal'), 'typist': ('clerical',), 'scribe': ('clerical', 'legal'),
    'arbiter': ('legal',), 'court-clerk': ('government',),
    'radio-repairman': ('radio',), 'defense-engineer': ('engineering',), 'chart-copyist': ('science',),
    'navigator': ('science',), 'tube-fitter': ('engineering',), 'draughtsman': ('engineering',),
    'pharmacist': ('pharmacy',), 'druggist': ('pharmacy',), 'apothecary': ('pharmacy', 'clinical'),
    'medical-researcher': ('research',), 'physician-resident': ('clinical', 'research'),
    'biologist': ('academic',), 'professor': ('academic',), 'graduate-student': ('academic',),
    'undergraduate': ('academic',), 'institute-lecturer': ('academic',), 'folklore-lecturer': ('academic',),
    'librarian': ('library',), 'museum-curator': ('library',), 'rare-books-cataloguer': ('library',),
    'convent-teacher': ('school',),
    'hotel-clerk': ('hospitality',), 'hotel-front-desk': ('hospitality',), 'event-planner': ('hospitality', 'food'),
    'casino-dealer': ('hospitality', 'leisure'), 'innkeeper': ('food', 'hospitality'), 'chauffeur': ('household',),
    'hatcheck-attendant': ('food', 'hospitality'), 'cook': ('food', 'household'), 'palace-cook': ('food', 'household'),
    'bootblack': ('retail',), 'elevator-operator': ('hospitality',), 'market-keeper': ('retail', 'food'),
    'fishmonger': ('retail', 'food'),
    'blacksmith': ('crafts', 'mechanic'), 'garage-mechanic': ('mechanic',), 'boatbuilder': ('sea', 'crafts'),
    'dressmaker': ('crafts',), 'undertaker': ('crafts', 'building'), 'iceman': ('industry',),
    'dowser': ('farming',), 'mill-hand': ('industry',), 'assayer': ('industry',), 'lighthouse-keeper': ('sea',),
    'tide-clerk': ('sea',), 'emerald-cutter': ('crafts',),
    'port-logistics': ('shipping', 'freight'), 'cabman': ('transit',), 'railway-porter': ('transit',),
    'railway-signalman': ('transit',), 'carter': ('freight',), 'canal-boatman': ('shipping',),
    'lock-keeper': ('shipping',), 'airship-mail-rigger': ('post',), 'telegraph-operator': ('post',),
    'stage-driver': ('freight', 'transit'), 'teamster': ('freight',), 'miller': ('farming', 'industry'),
    'actor': ('stage',), 'dancer': ('stage',), 'chorus-dancer': ('stage',), 'burlesque-dancer': ('stage',),
    'taxi-dancer': ('stage', 'music'), 'art-model': ('photo',), 'performer': ('stage', 'music'),
    'musician': ('music',), 'jazz-musician': ('music',), 'saloon-pianist': ('music',), 'song-plugger': ('music',),
    'town-musician': ('music',), 'minstrel': ('music', 'stage'), 'music-hall-singer': ('music', 'stage'),
    'photographer': ('photo',), 'graphic-designer': ('design',), 'fashion-assistant': ('design', 'photo'),
    'private-detective': ('police',), 'tide-waiter': ('government',),
    'subscription-creator': ('creator',), 'cam-model': ('creator',), 'glamour-model': ('creator', 'film'),
    'adult-film-performer': ('film',), 'adult-video-editor': ('editor',), 'exotic-dancer': ('dancer',),
    'burlesque-performer': ('dancer',), 'phone-sex-operator': ('phone',), 'professional-dominatrix': ('domme',),
    'adult-store-clerk': ('shop',), 'erotica-author': ('author',),
}
# Careers whose sector would put them in the wrong bank.
KIND_BY_CAREER = {'defense-engineer': 'tech', 'scribe': 'office', 'arbiter': 'office', 'convent-teacher': 'teaching',
                  'undergraduate': 'study', 'graduate-student': 'study'}
# Students: coursework from the study bank, in what they study (job_words.field_of_study), never a teacher's projects;
# never laid off; a few years in, not a decade.
STUDY = 'study'
STUDY_YEARS = {'undergraduate': 4, 'graduate-student': 6}
# Fewer fitting projects than this for an era, and the general bank joins in.
MIN_OPTIONS = 4
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
    """Whether they have a job; running their own business (companion/life/business.py), Work life steps aside."""
    if definition.get('business'):
        return False
    return any(block.kind == 'work' for block in routine.blocks(definition)[0])


def workdays(definition: dict) -> frozenset[int]:
    return frozenset(day for block in routine.blocks(definition)[0] if block.kind == 'work' for day in block.days)


def after_work(definition: dict, day: date, block: dict) -> str | None:
    """When a late night starts: the end of the day's work, or the start of the free time that follows within an
    hour and a half. None after an overnight shift or when the day has no free time after work (a 12-hour shift that
    ends in sleep), so a late night never lands on a day off or the next morning."""
    if block['end'] <= block['start']:
        return None
    end = admin.minutes_of(block['end'])
    for free in admin.free_blocks(routine.blocks(definition)[0], day):
        start, stop = admin.minutes_of(free['start']), admin.minutes_of(free['end']) or 24 * 60
        if start <= end < stop:
            return block['end']
        if end < start <= end + 90:
            return free['start']
    return None


def work_block(definition: dict, day: date) -> dict | None:
    """The day's last work block (the one a late night follows)."""
    found = [block.view() for block in routine.blocks(definition)[0] if block.kind == 'work' and block.on(day)]
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
    if career['id'] in KIND_BY_CAREER:
        return KIND_BY_CAREER[career['id']]
    if career.get('adult') and 'modern' in (career.get('eras') or ['modern']):
        return 'adult'
    sector = (career.get('sector') or '').lower()
    for kind, words in KINDS.items():
        if sector in words or any(word in sector.split('-') for word in words):
            return kind
    return 'general'


def trades_of(career: dict | None) -> frozenset[str]:
    if not career:
        return frozenset()
    return frozenset(TRADES_BY_CAREER.get(career['id']) or TRADES_BY_SECTOR.get((career.get('sector') or '').lower(), ()))


def in_world(item: dict, city: dict | None) -> bool:
    """A project that names one world stays in it (the Emerald City's gates only in Oz), one with dragons or elves
    only in a made-up world, and one about kings and dukes never in a republic."""
    city = city or {}
    if item.get('cities') and city.get('id') not in item['cities']:
        return False
    if item.get('fantasy') and city.get('setting') != 'fictional':
        return False
    return not (item.get('monarchy') and 'republic' in (city.get('country') or '').lower())


def projects(kind: str, group: str, trades: frozenset[str] = frozenset(), city: dict | None = None,
             field: str = '') -> list[str]:
    """The projects a career could be running: its kind's that fit its trades (or anyone of the kind), in its era and
    world; the general bank joins in when that leaves too few. A student's coursework names what they study
    (`field`), and without one stays any student's."""
    bank = data()['projects']
    def pool(name: str) -> list[str]:
        return [item['title'] for item in bank.get(name, ()) if group in item['eras'] and in_world(item, city)
                and (not item.get('fits') or trades & set(item['fits']))]
    if kind == STUDY:
        return [title.replace('{field}', field) for title in pool(STUDY) if field or '{field}' not in title]
    found = pool(kind) if kind != 'general' else []
    if len(found) < MIN_OPTIONS:
        found += pool('general')
    return found or [item['title'] for item in bank['general'] if group in item['eras']]


def local_today(companion: dict, now: datetime) -> date:
    return now.astimezone(zone(companion['version']['timezone'])).date()


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


# --- State ---

def state(connection, timeline_id: str) -> dict | None:
    row = optional(connection, 'SELECT * FROM work_life WHERE timeline_id=?', (timeline_id,))
    return {**row, 'project': decode(row['project'])} if row else None


def new_project(seed: str, index: int, career: dict | None, city: dict | None, start: date, used: list[str],
                field: str = '') -> dict:
    """The next running project, from the bank, fitting their career (and what a student studies), not one of the
    last few, in the city's own English."""
    found = [wording.regional(city, title)
             for title in projects(kind_of(career), era_group(city), trades_of(career), city, field)]
    title = generators.pick(seed, f'project:{index}', [title for title in found if title not in used[-8:]] or found)
    weeks = PROJECT_WEEKS[0] + int(generators.unit(seed, 'weeks', index) * (PROJECT_WEEKS[1] - PROJECT_WEEKS[0] + 1))
    due = monday_of(start) + timedelta(weeks=weeks, days=int(generators.unit(seed, 'due-day', index) * 5))
    return {'title': title, 'index': index, 'started': start.isoformat(), 'due': max(due, start).isoformat(),
            **({'field': field} if field else {})}


def field_of(definition: dict, career: dict | None) -> str:
    """What a student studies, for their coursework; '' for anyone else."""
    return job_words.field_of_study(definition) if kind_of(career) == STUDY else ''


def ensure(connection, companion: dict, today: date, now: datetime) -> dict | None:
    """The companion's work state, made the first time (or afresh when they change careers): when they started, their
    yearly review day and a project part way along. None when they have no job in their week."""
    definition, timeline_id = companion['version']['definition'], companion['active_timeline_id']
    if not works(definition):
        return None
    city = outings.city_data(connection, definition)
    career = career_of(definition, city)
    career_id = career['id'] if career else ''
    found, field = state(connection, timeline_id), field_of(definition, career)
    if found and found['career'] == career_id:
        return refreshed(connection, found, career, city, field, today, now)
    seed = f"work:{timeline_id}:{career_id}"
    years = STUDY_YEARS.get(career_id)
    span = (years * 365 - 200) if years else 2400
    started = today - timedelta(days=0 if found else 200 + int(generators.unit(seed, 'tenure') * span))
    month = rules(city).get('review_month')
    review = f'{month:02d}-{1 + int(generators.unit(seed, "review") * 27):02d}' if month else started.strftime('%m-%d')
    project = new_project(seed, 0, career, city, today - timedelta(days=int(generators.unit(seed, 'into') * 14)), [],
                          field)
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


def refreshed(connection, found: dict, career: dict | None, city: dict | None, field: str, today: date, now) -> dict:
    """Their work state, with a new project when the one running no longer fits: a student still on a project from
    before students had their own (a teacher's syllabus), or coursework in what they no longer study. A project the
    user wrote stays."""
    project = found['project']
    if STUDY not in (found['kind'], kind_of(career)):
        return found
    if project.get('own') or (found['kind'] == kind_of(career) and project.get('field', '') == field):
        return found
    fresh = new_project(f"work:{found['timeline_id']}:{found['career']}:{field}", project['index'] + 1, career, city,
                        today, used_titles(found), field)
    update(connection, found['timeline_id'], now, kind=kind_of(career), project=fresh,
           used=[*used_titles(found), fresh['title']][-12:])
    return state(connection, found['timeline_id'])


def set_project(connection, companion: dict, title: str | None, now: datetime, due: date | None = None) -> dict | None:
    """What they are working on, in the user's words, and when it is due (today to a year on); then the next comes
    from the bank as before. No title keeps it; an empty one gives the app's pick back, with the app's due date too
    when the user had moved it."""
    today = local_today(companion, now)
    found = ensure(connection, companion, today, now)
    if not found:
        return None
    require(due is None or today <= due <= today + timedelta(days=DUE_AHEAD_DAYS),
            'Pick a due date between today and a year from now.', 422)
    project = found['project']
    if title is not None and (title := ' '.join(title.split())):
        project = {**project, 'title': title, 'own': True}
    elif title is not None:
        definition = companion['version']['definition']
        city = outings.city_data(connection, definition)
        career = career_of(definition, city)
        fresh = new_project(f"work:{found['timeline_id']}:{found['career']}:own", project['index'], career, city,
                            date.fromisoformat(project['started']), used_titles(found), field_of(definition, career))
        fresh['due'] = max(fresh['due'], today.isoformat()) if project.get('own_due') else project['due']
        project = fresh
    if due is not None:
        project = {**project, 'due': due.isoformat(), 'own_due': True}
    update(connection, found['timeline_id'], now, project=project)
    return state(connection, found['timeline_id'])


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
    """'slammed', 'normal' or 'slow' for the week starting this Monday: slammed the week the project is due (on Steady
    only some of those weeks)."""
    if not chosen or found['status'] != 'working':
        return 'normal'
    due = date.fromisoformat(found['project']['due'])
    roll = generators.unit(f"work:{found['timeline_id']}", 'week', monday)
    if monday <= due < monday + timedelta(days=7) and generators.unit(f"work:{found['timeline_id']}", 'due', monday) \
            < DUE_SLAMMED[chosen]:
        return 'slammed'
    slammed, slow = WEEKS[chosen]
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
    """{local date: 'Vacation', 'Job hunt' or a big day's title} for the agenda: vacation days, workdays while between
    jobs, and a workday a big day falls in their working hours (companion/life/big_days.py)."""
    from companion.life import big_days, expecting, our_child, own_family
    # Weeks of parental leave after a baby of theirs (companion/life/own_family.py), days home with the pair's own
    # (companion/life/our_child.py), bed rest while they carry one (companion/life/expecting.py), then big days.
    result = {**own_family.leave_days(connection, companion, start, end),
              **our_child.days_off(connection, companion, start, end),
              **expecting.days_off(connection, companion, start, end),
              **big_days.days_off(connection, companion, start, end)}
    found = state(connection, companion['active_timeline_id']) if ACTIVE else None
    if not found or not level(connection):
        return result
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
    if not rule.get('paid', True):
        # No money where they live (Oz): now and then a promotion, never a raise or a freeze.
        if roll < PROMOTION[chosen]:
            record(connection, timeline_id, f'review:{day.year}', 'promotion', day, 'promoted at work', pay, 0, now)
        return pay
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
    following = next_project(connection, companion, found)
    return {'project': following, 'used': [*used_titles(found), following['title']][-12:]}


def used_titles(found: dict) -> list[str]:
    return decode(found['used']) if isinstance(found['used'], str) else found['used']


def next_project(connection, companion: dict, found: dict) -> dict:
    """The project that follows the running one, from the day after it is due. Seeded, so a late night or a day planned
    ahead can name it before it starts."""
    definition = companion['version']['definition']
    city = outings.city_data(connection, definition)
    start = date.fromisoformat(found['project']['due']) + timedelta(days=2)
    career = career_of(definition, city)
    return new_project(f"work:{companion['active_timeline_id']}:{found['career']}", found['project']['index'] + 1,
                       career, city, start, used_titles(found), field_of(definition, career))


def project_on(connection, companion: dict, found: dict, day: date) -> dict:
    """The project they are on that day: the running one until it is due, then the one after it."""
    return found['project'] if day.isoformat() <= found['project']['due'] else \
        next_project(connection, companion, found)


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
    text = 'laid off' if reason == 'laid-off' else 'quit the job'
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
    used = used_titles(found)
    career = career_of(definition, city)
    project = new_project(f'work:{timeline_id}:{found["career"]}:{day.isoformat()}', found['project']['index'] + 1,
                          career, city, day, used, field_of(definition, career))
    return {'status': 'working', 'hunt_until': None, 'hunt_reason': None, 'employer': employer, 'pay': pay,
            'started_on': day.isoformat(), 'review_on': day.strftime('%m-%d') if not rules(city).get('review_month')
            else found['review_on'], 'project': project, 'used': [*used, project['title']][-12:]}


def promoted_since(connection, timeline_id: str, since: date) -> bool:
    return optional(connection, "SELECT 1 FROM work_events WHERE timeline_id=? AND kind='promotion' AND local_date>=?",
                    (timeline_id, since.isoformat())) is not None


def storyline_promotions(connection, companion: dict, found: dict, today: date, now, paid: bool = True) -> float:
    """A promotion storyline that ended with the promotion (companion/life/storylines.py) raises their pay too, at
    most once a year: a second one within PROMOTION_GAP_DAYS is the storyline's alone."""
    pay = found['pay']
    for row in many(connection, "SELECT id, stages FROM storylines WHERE timeline_id=? AND story='promotion_chance'",
                    (companion['active_timeline_id'],)):
        for stage in decode(row['stages']):
            if stage.get('tone') == 'good' and 'got the promotion' in stage.get('text', '') and \
                    found['started_on'] <= stage['on'] <= today.isoformat():
                on = date.fromisoformat(stage['on'])
                if promoted_since(connection, companion['active_timeline_id'], on - timedelta(days=PROMOTION_GAP_DAYS)):
                    continue
                if not paid:
                    record(connection, companion['active_timeline_id'], f"storyline:{row['id']}", 'promotion', on,
                           'promoted at work', pay, 0, now)
                    continue
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
    rule = {**rules(city), 'paid': not city or city['currency']['code'] != 'none'}
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
            if chosen >= 3 and day.weekday() == 0 and current['kind'] != STUDY:  # A student isn't laid off.
                run = sum(workload(current, day - timedelta(weeks=back), chosen) == 'slammed' for back in (1, 2))
                if lost := lose_job(connection, companion, current, day, run, now):
                    changes.update(lost)
        day += timedelta(days=1)
    if chosen:
        changes['pay'] = storyline_promotions(connection, companion, {**found, **changes}, today, now, rule['paid'])
    update(connection, timeline_id, now, checked_through=today.isoformat(), **changes)
    return state(connection, timeline_id)


def plan_late_nights(connection, companion: dict, found: dict, today: date, chosen: int, now) -> int:
    """A slammed week's late nights on the shared calendar, right after work, on seeded workdays. They hold their
    time against plans with the user on True to life and up (admin.stands), and move for them on Light."""
    definition, timeline_id = companion['version']['definition'], companion['active_timeline_id']
    added = 0
    off = set(days_off(connection, companion, today, today + timedelta(days=AHEAD_DAYS + 7)))
    city = outings.city_data(connection, definition)
    if city:
        # No late night on a public holiday: there is no work to stay late at.
        off |= {item['date'] for item in generators.holidays(city, today, today + timedelta(days=AHEAD_DAYS + 7))
                if item['kind'] == 'public'}
    for week in range(0, AHEAD_DAYS // 7 + 1):
        monday = monday_of(today) + timedelta(weeks=week)
        if workload(found, monday, chosen) != 'slammed':
            # A week that is no longer slammed (the slider moved, the project is due another week) has no late nights.
            connection.execute("UPDATE life_admin SET status='removed', updated_at=? WHERE timeline_id=? AND "
                               "source='work' AND status='planned' AND key LIKE ? AND local_date>=?",
                               (stamp(now), timeline_id, f'work:late:{monday.isoformat()}:%', today.isoformat()))
            continue
        seed = f'work:{timeline_id}:late:{monday.isoformat()}'
        low, high = LATE_NIGHTS[chosen]
        count = low + int(generators.unit(seed, 'count') * (high - low + 1))
        # This week's workdays: a rota's shifts or a freelancer's gigs (companion/life/shifts.py) where they have them.
        options = [monday + timedelta(days=offset) for offset in range(7)
                   if work_block(definition, monday + timedelta(days=offset))
                   and (monday + timedelta(days=offset)).isoformat() not in off]
        due = date.fromisoformat(found['project']['due'])
        picks = sorted(options, key=lambda day: (day != due - timedelta(days=1), generators.unit(seed, 'day', day)))
        last = max(options, default=None)
        picks = [day for day in picks if (block := work_block(definition, day)) and after_work(definition, day, block)]
        for index, day in enumerate(picks[:count]):
            block = work_block(definition, day)
            if day < today:
                continue
            minutes = LATE_MINUTES[0] + int(generators.unit(seed, 'minutes', index) * 4) * 30
            title = project_on(connection, companion, found, day)['title']
            key = f'work:late:{monday.isoformat()}:{index}'
            # One taken off while Work life was Off comes back with it.
            connection.execute("UPDATE life_admin SET status='planned', updated_at=? WHERE timeline_id=? AND key=? "
                               "AND status='removed' AND local_date>=?", (stamp(now), timeline_id, key, today.isoformat()))
            added += bool(admin.add(
                connection, companion, key=key, source='work', kind='late-night',
                title=STUDY_LATE_TITLE if found['kind'] == STUDY else LATE_TITLE,
                done=f"{STUDY_LATE_DONE if found['kind'] == STUDY else LATE_DONE}{title}", day=day,
                at=after_work(definition, day, block), minutes=min(minutes, 180),
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
        return {'shifts': plan_shifts(connection, companion, now)}
    connection.execute("UPDATE life_admin SET fixed=? WHERE timeline_id=? AND source='work' AND status='planned'",
                       (int(chosen >= 2), timeline_id))
    if found['status'] == 'hunting':
        connection.execute("UPDATE life_admin SET status='removed', updated_at=? WHERE timeline_id=? AND "
                           "source='work' AND status='planned'", (stamp(now), timeline_id))
        return {'added': 0, 'shifts': plan_shifts(connection, companion, now)}
    moved = plan_shifts(connection, companion, now)
    if moved:
        companion = reread(connection, companion)
    return {'added': plan_late_nights(connection, companion, found, local_today(companion, now), chosen, now),
            'shifts': moved}


def reread(connection, companion: dict) -> dict:
    from companion.characters import by_id
    return by_id(connection, companion['id']) or companion


def plan_shifts(connection, companion: dict, now: datetime) -> bool:
    """This week's and the next few weeks' shifts or gigs written down (companion/life/shifts.py), and the agenda's
    upcoming work days brought in line when the week changed. True when it did, so the caller reads the companion
    again."""
    if not shifts.ACTIVE:
        return False
    added = shifts.plan_ahead(connection, companion, local_today(companion, now), now)
    return shifts.refresh_agenda(connection, reread(connection, companion), now) or bool(added)


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
GIG = ('{name} spent the day on a gig: {project}.', '{name} had a gig today and put it into {project}.',
       'A gig came through, and {name} spent the day on {project}.', '{name} worked a gig for a client: {project}.')
# Before the jazz age there are no gigs or clients (shifts.old_era).
GIG_OLD = ('{name} spent the day on an engagement: {project}.',
           '{name} had an engagement today and put it into {project}.',
           "Work came {name}'s way, and they spent the day on {project}.", '{name} worked for a patron: {project}.')
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
    label, project = routine_label(block), project_on(connection, companion, found, day)['title']
    if (gig := shifts.setup(connection, companion)) and gig['kind'] == 'freelance' and \
            generators.unit(seed, 'gig-line') < 0.5:
        lines = GIG_OLD if shifts.old_era(connection, companion) else GIG
        summary = generators.pick(seed, 'gig', list(lines)).format(name=name, project=project)
        return {**entry, 'summary': summary, 'mood': 'busy' if week == 'slammed' else entry.get('mood')}
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


def pay(connection, timeline_id: str, day: date, payday: date | None = None) -> dict | None:
    """Their pay as a share of the career's base, and whether they are between jobs (money.household). Shifts and
    gigs count from the last payday (`payday`, the start of this pay cycle), so the cycle's pay holds until the next."""
    if not ACTIVE:
        return None
    found = state(connection, timeline_id)
    if not found or not level(connection):
        return None
    hunting = found['status'] == 'hunting' and found['hunt_since'] <= day.isoformat()
    factor = found['pay'] * (HUNT_PAY.get(found['hunt_reason'] or '', 0.5) if hunting else 1)
    from companion.life import our_child
    factor *= our_child.pay(connection, timeline_id, day)  # Part-time or at home with the pair's children.
    if not hunting and shifts.ACTIVE:
        # Shifts worked and gigs landed lately, tips and all (companion/life/shifts.py).
        factor *= shifts.pay(connection, timeline_id, payday or day)
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


def study_year(found: dict, today: date, field: str) -> str:
    """"You are in your second year, studying photography." for a student's chat context."""
    year = YEARS[min(len(YEARS) - 1, max(0, (today - date.fromisoformat(found['started_on'])).days // 365))]
    program = 'of graduate school' if found['career'] == 'graduate-student' else 'of college'
    return f"You are in your {year} year {program}" + (f", studying {field}." if field else '.')


def vacation_line(days: list[str], today: date, studying: bool = False) -> str:
    """'You are off work Friday, October 30 (a vacation day).' or a run of days as one stretch; for a student, days
    with no classes."""
    if studying:
        return study_break_line(days, today)
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


def study_break_line(days: list[str], today: date) -> str:
    """'You have no classes Friday, November 6.' or a break from one day through another."""
    upcoming = sorted({day for day in days if today.isoformat() <= day <= (today + timedelta(days=21)).isoformat()})
    if not upcoming:
        return ''
    run = [upcoming[0]]
    for day in upcoming[1:]:
        if (date.fromisoformat(day) - date.fromisoformat(run[-1])).days <= 3:
            run.append(day)
    first = 'today' if run[0] == today.isoformat() else day_text(run[0])
    return f'You have no classes {first}.' if len(run) == 1 else \
        f'You have no classes from {first} through {day_text(run[-1])}.'


def phrased(project: dict) -> str:
    """The project as the sentences say it: "the reading list for ..." for one the user wrote without an article."""
    title = project['title']
    if not project.get('own') or OWN_ARTICLE.match(title):
        return title
    return 'the ' + (title[:1].lower() + title[1:] if title[1:2].islower() else title)


OWN_ARTICLE = re.compile(r"^(?:a|an|the|my|your|their|his|her|our|some|one|two|three|four|five)\b", re.IGNORECASE)


EVENT_LINES = {
    'raise': 'On {day} you got your yearly raise at work, about {change:g}%.',
    'promotion': 'On {day} you were {text}.',
    'freeze': 'At your review on {day} there was {text}: your pay stays as it is.',
    'project': 'On {day} you {text}.',
    'laid-off': 'On {day} you were laid off.',
    'quit': 'On {day} you quit your job.',
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
        studying = found['kind'] == STUDY
        lines.append(('week', (STUDY_WEEK_LINES if studying else WEEK_LINES)[week]))
        lines.append(('project', f"{'For your classes' if studying else 'At work'} you are in the middle of "
                                 f"{phrased(project)}.{due_text}"))
        lines.append(('tenure', study_year(found, today, project.get('field', '')) if studying else
                      f"You have been at this job for {tenure(found['started_on'], today)}."))
        if shifts.ACTIVE and (line := shifts.context_line(connection, companion, today)):
            lines.append(('shifts', line[2:]))
        if line := vacation_line(vacation_days(connection, companion, today.year, found)
                                 + vacation_days(connection, companion, today.year + 1, found), today, studying):
            lines.append(('vacation', line))
    for event in recent_events(connection, timeline_id, (today - timedelta(days=RECENT_DAYS)).isoformat())[-3:]:
        line = EVENT_LINES[event['kind']].format(day=short_day(event['local_date']), text=event['text'],
                                                 change=round(event['change'], 1))
        # "a new job at Coutts and Co." already ends the sentence.
        lines.append((f"event:{event['id']}", line[:-1] if line.endswith('..') and not line.endswith('...') else line))
    return [(f'work:{today.isoformat()}:{key}', f'- {line}') for key, line in lines]


def overview(connection, companion: dict, now: datetime, show_meter: bool = False) -> dict | None:
    """The Character page's Work life panel: plain words, the project, time off and what changed. Vacation counts and
    pay as a number only with Hidden values on. None without a job in their week."""
    timeline_id = companion['active_timeline_id']
    if not works(companion['version']['definition']):
        return None
    chosen = level(connection)
    # Made the first time, and a project that no longer fits a student replaced (refreshed).
    found = ensure(connection, companion, local_today(companion, now), now) if ACTIVE else None
    today = local_today(companion, now)
    if not found:
        return None
    week = workload(found, monday_of(today), chosen)
    days = vacation_days(connection, companion, today.year, found) if chosen else []
    late = [admin.item_view(item, companion['version']['definition'])
            for item in admin.upcoming(connection, timeline_id, today.isoformat())
            if item['source'] == 'work'][:4]
    state_lines, hours = [], 'staff'
    if not chosen:
        state_lines.append('Work life is off: their job stays as written.')
    elif found['status'] == 'hunting':
        state_lines.append('Between jobs and job hunting.')
    else:
        gigs = shifts.overview_line(connection, companion, today) if shifts.ACTIVE else ''
        hours = (shifts.setup(connection, companion) or {}).get('kind', 'staff') if gigs else 'staff'
        if hours == 'freelance':
            # A freelancer's gigs say how the week is going; with none this week there is no project to be on (Iris).
            state_lines.append(gigs)
        else:
            words = STUDY_WORKLOAD if found['kind'] == STUDY else WORKLOAD_WORDS
            state_lines += [words[week] + '.', *([gigs] if gigs else [])]
        if hours != 'freelance' or not gigs.startswith('No gigs'):
            state_lines.append(f"Working on {phrased(found['project'])}, due {day_text(found['project']['due'])}.")
        if line := vacation_line(days + vacation_days(connection, companion, today.year + 1, found), today,
                                 found['kind'] == STUDY):
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
            'level': chosen, 'meter': meter, 'hours': hours, 'studying': found['kind'] == STUDY,
            'field': found['project'].get('field', ''), 'own_project': bool(found['project'].get('own')),
            'own_due': bool(found['project'].get('own_due')), 'today': today.isoformat()}
