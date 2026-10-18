"""Life's big turns (Hit List #68, v0.14 Years Go By): back to school, a career change, buying a place, retirement,
and (part 2) starting a business, a health turn and caring for a parent.

They are life chapters like the others (companion/life/chapters.py picks them with the consequence engine, choice
`chapter:next`, from age, money, mood and the companion's own description), but each one takes months, so it runs in
stages kept on its row (`details`: the stage, the day the next one comes and the plan), moved on day by day by
`progress`. Nothing here calls a model; the companion tells the user as a friend or partner would, through the
chapter's `told` and `share` lines, which change with each stage.

- `school`: they sign up for a course from the bank (world/data/life_chapters.json, by era); classes start a week or
  two later, carved out of an evening of free time twice a week (the overlay's `study`, applied by
  companion/characters.py), fees are paid each term (`purchases`, through money.py), exams go on the calendar
  (companion/life/admin.py, source 'school') and on graduation day the class leaves their week.
- `career_change`: retraining the same way for a line of work in another sector of their city, then the new job (the
  career overlay), which Work life (companion/life/work.py) starts afresh.
- `buy_place`: the app picks a place their pay fits; house hunting until keys day, then the home is theirs, with a
  mortgage instead of rent and a deposit from savings. Living together it is a shared chapter: the companion raises it,
  the app picks a bigger place for both and the shared home moves there (companion/life/moving_in.py), the mortgage
  split like the rent was.
- `retire`: older characters only (their age from companion/life/ages.py). They hand in their notice; after their
  last day at work their working hours become time for a pursuit from the bank, and their pay a pension (`pay`).

- `business`, `health` and `caring`: part 2, in companion/life/business.py and companion/life/health_turns.py, which
  plug their plans, stages, costs and calendar entries in here.

Graduations and last days at work are the circle's big days to come (`big_days`, for Big days in the circle).
Life's big turns (Settings > Realism > Their days, life_settings.life_turns) sets how often any chapter begins; on
Gentle only good turns happen (Vanta 2026-10-18: "Good turns only" on an easy life), so the hard turns (`HARD`: a
health turn and caring for a parent) never come on it, and a business never folds. Undo on Today takes a turn back at
any stage, with the marks its outcomes left.
"""
import json
import random
from calendar import monthrange
from datetime import date, time, timedelta
from functools import cache

from companion import consequences
from companion.database import decode, encode, many, optional
from companion.life import ages, home, money, moving_in, routine
from companion.world import catalog, intimacy

KINDS = ('school', 'career_change', 'buy_place', 'retire', 'business', 'health', 'caring')
# Hard turns never happen on Gentle (good turns only); a business folding is ruled out there by its own odds
# (business:how in world/data/consequences.json).
HARD = frozenset({'health', 'caring'})
GENTLE = 1
# Life's big turns (0..3): how often a chapter begins, as a multiplier on the drama level's monthly chance.
TURNS = (0.0, 0.5, 1.0, 1.5)
USUAL_TURNS = 2
START_DAYS = (7, 21)  # From signing up until classes start.
TERM_MONTHS = 4
RETRAIN_MONTHS = (6, 18)
HUNT_DAYS = (30, 75)  # From deciding to buy until keys day.
NOTICE_DAYS = (21, 60)  # From handing in their notice until their last day at work.
ADULT, BUY_AGE, SWITCH_BEFORE, RETIRE_AGE = 18, 25, 58, 60
# A term's fees as a share of a month's take-home, by era; a deposit as months of take-home.
FEES = {'modern': 0.35, 'jazz-age': 0.2, 'other': 0.1}
DEPOSIT_MONTHS = 4
MORTGAGE = (0.85, 1.15)  # The monthly payment against the rent of the same place.
PENSION = {'modern': 0.6, 'jazz-age': 0.35, 'other': 0.25}  # A pension as a share of their pay.
EXAMS_AHEAD = 21  # Exams go on the calendar this many days ahead.
WEEKDAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
CLASS_THEMES = ['class', 'coursework', 'studying']
BUSY = {'work', 'study', 'sleep'}  # Time a class never comes out of.


@cache
def data() -> dict:
    return json.loads((catalog.DATA / 'life_chapters.json').read_text(encoding='utf-8'))


def era(city: dict | None) -> str:
    return money.era_of(city) if city and city.get('era') else 'modern'


def first(definition: dict) -> str:
    return definition['name'].split()[0]


def article(text: str) -> str:
    return f"{'an' if text[:1] in 'aeiou' else 'a'} {text}"


def later(day: date, months: int) -> date:
    """The same day of the month `months` on (the last day of a shorter month)."""
    month = day.month - 1 + months
    year, month = day.year + month // 12, month % 12 + 1
    return date(year, month, min(day.day, monthrange(year, month)[1]))


def day_text(day: str | date) -> str:
    found = date.fromisoformat(day) if isinstance(day, str) else day
    return found.strftime('%B %d, %Y').replace(' 0', ' ')


def short_day(day: str) -> str:
    """'Feb 11, 2027', for the Character page."""
    return date.fromisoformat(day).strftime('%b %d, %Y').replace(' 0', ' ')


def days_text(days: list[int]) -> str:
    """'Mondays and Thursdays'."""
    return ' and '.join(f'{WEEKDAYS[day]}s' for day in days)


# Who can take a turn ------------------------------------------------------------------------------------------

def age_of(connection, companion: dict, day: date) -> int | None:
    """Their age, None for a sheet that reads as under 18 (big turns are for adults only) or with no age known."""
    definition = companion['version']['definition']
    if intimacy.reads_as_minor(definition):
        return None
    return ages.companion_age(connection, companion['id'], definition, day)


def running(connection, timeline_id: str) -> list[dict]:
    """Big turns still on their way (a stage to come), oldest first."""
    return many(connection, "SELECT * FROM life_chapters WHERE timeline_id=? AND undone_at IS NULL AND "
                "json_extract(details, '$.next_on') IS NOT NULL ORDER BY started_on, created_at", (timeline_id,))


def finished(connection, timeline_id: str, kind: str, stage: str) -> dict | None:
    return optional(connection, "SELECT * FROM life_chapters WHERE timeline_id=? AND kind=? AND undone_at IS NULL AND "
                    "json_extract(details, '$.stage')=? ORDER BY started_on DESC LIMIT 1", (timeline_id, kind, stage))


def free(connection, companion: dict, day: date) -> int | None:
    """Their age when a big turn could start (one at a time, adults only), else None."""
    if running(connection, companion['active_timeline_id']):
        return None
    found = age_of(connection, companion, day)
    return found if found is not None and found >= ADULT else None


def facts(connection, companion: dict, day: date) -> dict:
    """What the engine reads for big turns."""
    return {'age': age_of(connection, companion, day), 'turns': level(connection),
            'together': int(bool(moving_in.living(connection, companion, day))),
            **health_turns.facts(connection, companion, day)}


def level(connection) -> int:
    row = optional(connection, 'SELECT * FROM life_settings WHERE id=1') or {}
    found = row.get('life_turns', USUAL_TURNS)
    return found if found in range(4) else USUAL_TURNS


def allowed(connection, kind: str) -> bool:
    """On Gentle only good turns happen."""
    return kind not in HARD or level(connection) > GENTLE


# Planning each turn -------------------------------------------------------------------------------------------

def class_slot(definition: dict, seed: str, evenings: bool = True) -> dict | None:
    """Two weekday evenings of their own time (else, or without `evenings`, a Saturday) for classes: the block they come
    out of and the days."""
    rota = bool(definition.get('rota'))
    blocks = [block for block in routine.blocks(definition)[0] if block.kind not in BUSY
              and not (rota and block.key in ('after-work', 'day-off')) and 'caring' not in block.themes]
    rng = random.Random(f'{seed}:class')
    for block in blocks if evenings else ():
        weekdays = [day for day in block.days if day < 5]
        if block.start >= time(17) and len(weekdays) >= 2:
            return slot(block, sorted(rng.sample(weekdays, 2)))
    for block in blocks:
        if time(8) <= block.start < time(17) and 5 in block.days:
            return slot(block, [5])
    return None


def slot(block, days: list[int]) -> dict:
    return {'from': block.key, 'days': days, 'start': block.start.strftime('%H:%M'), 'end': block.end.strftime('%H:%M')}


def fees(definition: dict, city: dict | None, start: date, months: int) -> list[dict]:
    """A term's fees on the first day of each term, in the city's money; none where there is no money."""
    found = money.profile(definition)
    if not found:
        return []
    cost = round(money.monthly_share(found) * FEES[era(city)], 2)
    return [{'on': later(start, term).isoformat(), 'cost': cost} for term in range(0, months, TERM_MONTHS)]


def exams(start: date, end: date, days: list[int]) -> list[str]:
    """Exams at the end of each term and a final one a week and a half before graduating, each on a class day."""
    found = [later(start, term) - timedelta(days=3) for term in range(TERM_MONTHS, (end - start).days // 28,
                                                                        TERM_MONTHS)]
    found = [day for day in found if day < end - timedelta(days=20)]
    return [class_day(day, days).isoformat() for day in [*found, end - timedelta(days=10)]]


def class_day(day: date, days: list[int]) -> date:
    """The class day on or before this one."""
    while day.weekday() not in days:
        day -= timedelta(days=1)
    return day


def course_plan(definition: dict, city: dict | None, day: date, seed: str, course: dict) -> dict | None:
    """When classes start and end, the class in their week, the exams and the fees."""
    found = class_slot(definition, seed)
    if not found:
        return None
    start = day + timedelta(days=random.Random(f'{seed}:start').randint(*START_DAYS))
    end = later(start, course['months'])
    return {'course': course['course'], 'starts_on': start.isoformat(), 'ends_on': end.isoformat(),
            'study': {**found, 'label': f"{course['short']} class"}, 'exams': exams(start, end, found['days']),
            'fees': fees(definition, city, start, course['months']), 'next_on': start.isoformat()}


def plan_school(connection, companion, world, day, seed) -> dict | None:
    if free(connection, companion, day) is None:
        return None
    definition = companion['version']['definition']
    city = city_of(definition, world)
    course = random.Random(f'{seed}:course').choice(data()['courses'][era(city)])
    details = course_plan(definition, city, day, seed, course)
    if not details:
        return None
    name, start = first(definition), day_text(details['starts_on'])
    return {'title': f"{name} went back to school for {course['course']}",
            'told': f"You signed up for {course['course']}; classes start {start}, on "
                    f"{days_text(details['study']['days'])}.",
            'share': f"Okay, I did it: I signed up for {course['course']}. Classes start {start}!",
            'details': {**details, 'stage': 'enrolled'}}


def city_of(definition: dict, world) -> dict | None:
    from companion.life import circle
    return circle.city_data(definition, world)


def new_line(definition: dict, seed: str) -> dict | None:
    """Another line of work in their city: another sector, the same kind of hours, an everyday job."""
    city = money.city_for(definition)
    if not city or not money.has_money(city):
        return None
    current, _guessed = money.career_for(definition, city)
    if not current:
        return None
    options = sorted(career['id'] for career in catalog.everyday(catalog.careers_for(city)).values()
                     if career.get('sector') != current.get('sector') and career['schedule'] == current['schedule'])
    return catalog.careers_for(city)[random.Random(f'{seed}:career').choice(options)] if options else None


def plan_career(connection, companion, world, day, seed) -> dict | None:
    age = free(connection, companion, day)
    definition = companion['version']['definition']
    if age is None or age >= SWITCH_BEFORE or not works(definition):
        return None
    career = new_line(definition, seed)
    if not career:
        return None
    title = career['name'].lower()
    months = random.Random(f'{seed}:months').randint(*RETRAIN_MONTHS)
    course = {'course': f'retraining as {article(title)}', 'short': career['name'], 'months': months}
    details = course_plan(definition, city_of(definition, world), day, seed, course)
    if not details:
        return None
    name, start = first(definition), day_text(details['starts_on'])
    return {'title': f'{name} decided to change careers and retrain as {article(title)}',
            'told': f'You decided to change careers and retrain as {article(title)}; the course starts {start}, on '
                    f"{days_text(details['study']['days'])}, and you keep your job until it ends.",
            'share': f"Big decision: I'm retraining as {article(title)}. Course starts {start}!",
            'details': {**details, 'stage': 'enrolled', 'career': career['id'], 'job': title}}


def job_free(connection, timeline_id: str) -> bool:
    """Whether a new job of the ordinary kind (chapters.py `new_job`) can come: not once retired, and not while they
    hand in their notice, retrain for another line or run a business of their own (planning, open or established)."""
    if finished(connection, timeline_id, 'retire', 'retired'):
        return False
    if any(row['kind'] in ('retire', 'career_change', 'business') for row in running(connection, timeline_id)):
        return False
    return not finished(connection, timeline_id, 'business', 'established')


def works(definition: dict) -> bool:
    return any(block.kind == 'work' for block in routine.blocks(definition)[0])


def owns(connection, timeline_id: str, day: date) -> bool:
    return any(item['kind'] == 'home' and item.get('owned') for item in home.items_on(connection, timeline_id, day))


def plan_buy(connection, companion, world, day, seed) -> dict | None:
    age, timeline_id = free(connection, companion, day), companion['active_timeline_id']
    definition = companion['version']['definition']
    found, city = money.profile(definition), money.city_for(definition)
    if age is None or age < BUY_AGE or not found or found.tier < 1 or owns(connection, timeline_id, day):
        return None
    together = moving_in.current(connection, timeline_id)
    if together and (together['status'] != 'moved' or together['city_id'] != city['id']):
        return None  # A move in together still to come, or a shared home in another city.
    place = place_to_buy(companion, city, found, together, seed)
    if not place:
        return None
    keys = day + timedelta(days=random.Random(f'{seed}:keys').randint(*HUNT_DAYS))
    deposit = money.monthly_share(found) * DEPOSIT_MONTHS / (2 if together else 1)
    details = {'stage': 'hunting', 'next_on': keys.isoformat(), 'keys_on': keys.isoformat(), 'place': place,
               'deposit': {'on': keys.isoformat(), 'cost': round(deposit, 2)}, 'shared': bool(together)}
    return {**buy_words(definition, place, keys, bool(together)), 'details': details}


def place_to_buy(companion: dict, city: dict, found, together: dict | None, seed: str) -> dict | None:
    """A place their pay fits (living together, a two-bedroom near the home they share), owned with a mortgage."""
    hoods = sorted((hood for hood in city['neighborhoods'] if hood.get('rent')
                    and hood['rent_tier'] in money.HOOD_TIERS[found.tier]), key=lambda hood: hood['name'])
    shared = moving_in.hood_named(city, together['neighbourhood']) if together else None
    hood = shared if shared and shared.get('rent') else random.Random(f'{seed}:hood').choice(hoods) if hoods else None
    if not hood:
        return None
    unit = 'two_bedroom' if together or found.tier >= 2 else 'one_bedroom'
    place = moving_in.shared_place(f'{seed}:place', companion, city, hood, unit)
    payment = place['details'].get('rent') or 0
    # To the ten, as money.amount says it, so the Home card and the budget show the same number.
    payment = int(round(payment * random.Random(f'{seed}:mortgage').uniform(*MORTGAGE), -1))
    return {**place, 'details': {**place['details'], 'owned': True, 'shared': bool(together), 'rent': payment,
                                 'rent_from': 'mortgage', 'estimate': True, 'city': city['name']}}


def buy_words(definition: dict, place: dict, keys: date, together: bool) -> dict:
    name, where = first(definition), place['details']['description']
    if together:
        return {'title': f'{name} and you are buying a place together',
                'told': f'You brought up buying a place together with the user, and you found {where}; you get the '
                        f'keys on {day_text(keys)}.',
                'share': f"Hear me out: what if we stopped renting? I found a place, {where}. I think it's the one."}
    return {'title': f'{name} is buying a place of their own',
            'told': f'You decided to buy a place of your own and found {where}; you get the keys on {day_text(keys)}.',
            'share': f'I put in an offer on a place, {where}, and they said yes! I get the keys {day_text(keys)}.'}


def plan_retire(connection, companion, world, day, seed) -> dict | None:
    age = free(connection, companion, day)
    definition = companion['version']['definition']
    if age is None or age < RETIRE_AGE or not works(definition):
        return None
    city = city_of(definition, world)
    pursuit = random.Random(f'{seed}:pursuit').choice(data()['retirement'][era(city)])
    last = day + timedelta(days=random.Random(f'{seed}:notice').randint(*NOTICE_DAYS))
    job = job_of(definition)
    name = first(definition)
    return {'title': f'{name} is retiring', 'told': f'You handed in your notice: you are retiring{job}, and your last '
            f'day at work is {day_text(last)}.',
            'share': f"I did it, I handed in my notice. {day_text(last)} is my last day. I'm retiring!",
            'details': {'stage': 'leaving', 'next_on': (last + timedelta(days=1)).isoformat(),
                        'last_day': last.isoformat(), 'pursuit': pursuit, 'pension': PENSION[era(city)]}}


def job_of(definition: dict) -> str:
    """' from your job as a registered nurse', or nothing when their job is not known."""
    city = money.city_for(definition)
    career = money.career_for(definition, city)[0] if city else None
    return f" from your job as {article(career['name'].lower())}" if career else ''


PLANS = {'school': plan_school, 'career_change': plan_career, 'buy_place': plan_buy, 'retire': plan_retire}  # + part 2


def do_plan(connection, companion, world, day, plan, now) -> dict:
    """Nothing changes on the day a big turn begins; its stages make the changes."""
    return {}


# The stages ---------------------------------------------------------------------------------------------------

def progress(connection, companion: dict, world, day: date, now) -> int:
    """Move each big turn whose next stage is due on this day. Returns how many moved."""
    rows = many(connection, "SELECT * FROM life_chapters WHERE timeline_id=? AND undone_at IS NULL AND "
                "json_extract(details, '$.next_on')<=? ORDER BY started_on", (companion['active_timeline_id'],
                                                                              day.isoformat()))
    for row in rows:
        details = decode(row['details'])
        update = STAGES[row['kind'], details['stage']](connection, companion, row, details, day, now)
        save_stage(connection, row, update, day)
    return len(rows)


def save_stage(connection, row: dict, update: dict, day: date):
    """The stage's words, changes and details on the row, keeping the row as it stood before (`before`), so a fork from
    an earlier day can take the turn back to how it was then (`fork_row`)."""
    earlier = decode(row['details'])
    snapshot = {'title': row['title'], 'told': row['told'], 'share': row['share'], 'changes': decode(row['changes']),
                'undo': decode(row['undo']), 'details': {key: value for key, value in earlier.items() if key != 'before'}}
    details = {**earlier, **update['details'], 'stage_on': day.isoformat(),
               'before': [*earlier.get('before', []), snapshot]}
    undo = decode(row['undo'])
    for key, value in update.get('undo', {}).items():
        undo[key] = [*undo.get(key, []), *value] if isinstance(value, list) else value
    connection.execute('UPDATE life_chapters SET title=?, told=?, share=?, changes=?, undo=?, details=? WHERE id=?',
                       (update['title'], update['told'], update['share'], encode(update['changes']), encode(undo),
                        encode(details), row['id']))


def classes_start(connection, companion, row, details, day, now) -> dict:
    name = first(companion['version']['definition'])
    study = details['study']
    what = details['course']
    retrain = row['kind'] == 'career_change'
    return {'title': row['title'] if retrain else f'{name} is taking {what}', 'changes': {'study': study},
            'told': f"You started {what}: classes are on {days_text(study['days'])}, and you finish on "
                    f"{day_text(details['ends_on'])}." + (' You keep your job until then.' if retrain else ''),
            'share': "First class done. I'm a student again!" if not retrain else
                     'First class of my retraining done. This is really happening.',
            'details': {'stage': 'retraining' if retrain else 'studying', 'next_on': details['ends_on']}}


def graduate(connection, companion, row, details, day, now) -> dict:
    name = first(companion['version']['definition'])
    return {'title': f"{name} finished {details['course']} and graduated", 'changes': {},
            'told': f"You finished {details['course']} and graduated on {day_text(day)}.",
            'share': 'I graduated!! It is actually done.', 'details': {'stage': 'graduated', 'next_on': None}}


def switch(connection, companion, row, details, day, now) -> dict:
    name, job = first(companion['version']['definition']), details['job']
    return {'title': f'{name} changed careers and started as {article(job)}', 'changes': {'career': details['career']},
            'told': f"You finished retraining and started your new job as {article(job)} on {day_text(day)}.",
            'share': f'First day as {article(job)} today. New chapter, for real.',
            'details': {'stage': 'switched', 'next_on': None}}


def keys_day(connection, companion, row, details, day, now) -> dict:
    """The old home ends the day before and the bought one begins; a shared home moves with them."""
    timeline_id = companion['active_timeline_id']
    # Every home still in place ends: one set up after this day (a catch-up from long ago) the day it began.
    old = many(connection, "SELECT id, since FROM home_items WHERE timeline_id=? AND kind='home' AND (until IS NULL OR "
               'until>?)', (timeline_id, day.isoformat()))
    for item in old:
        connection.execute('UPDATE home_items SET until=? WHERE id=?', (max(day.isoformat(), item['since']), item['id']))
    added = home.insert_item(connection, timeline_id, details['place'], 'change', day, now)
    # No lease to renew on a place they own (companion/life/admin.py).
    connection.execute("UPDATE life_admin SET status='removed' WHERE timeline_id=? AND key LIKE 'admin:lease:%' AND "
                       "status='planned'", (timeline_id,))
    undo = {'ended': [item['id'] for item in old], 'added': [added]}
    together = moving_in.living(connection, companion, day) if details.get('shared') else None
    if together:
        undo['moving_in'] = {'id': together['id'], 'neighbourhood': together['neighbourhood'],
                             'home_item_id': together['home_item_id']}
        connection.execute('UPDATE moving_in SET neighbourhood=?, home_item_id=? WHERE id=?',
                           (details['place']['details']['neighborhood'], added, together['id']))
    place = details['place']['details']
    name = first(companion['version']['definition'])
    ours = 'you and the user own' if together else 'you own'
    return {'title': f"{name} bought {place['description']}" + (' with you' if together else ''),
            'changes': {'location': f"{place['neighborhood']}, {place['city']}"},
            'told': f"You got the keys and moved into {place['description']}, which {ours} now, with a mortgage "
                    'instead of rent.',
            'share': 'We got the keys!! Our own place.' if together else 'I got the keys!! My own place.',
            'undo': undo, 'details': {'stage': 'moved', 'next_on': None, 'keys_on': day.isoformat(),
                                      'deposit': {**details['deposit'], 'on': day.isoformat()}}}


def retire(connection, companion, row, details, day, now) -> dict:
    name, pursuit = first(companion['version']['definition']), details['pursuit']
    return {'title': f'{name} retired', 'changes': {'retired': {'label': pursuit['label']},
                                                    'interest': pursuit['pursuit']},
            'told': f"You retired after your last day at work on {day_text(details['last_day'])}; your days are your own "
                    f"now, and you spend a lot of them {pursuit['pursuit']}.",
            'share': 'First morning of retirement. No alarm clock!', 'details': {'stage': 'retired', 'next_on': None}}


STAGES = {('school', 'enrolled'): classes_start, ('school', 'studying'): graduate,
          ('career_change', 'enrolled'): classes_start, ('career_change', 'retraining'): switch,
          ('buy_place', 'hunting'): keys_day, ('retire', 'leaving'): retire}  # + part 2, below


def fork_row(connection, row: dict, copy_id: str, timeline_id: str, cutoff: str) -> dict:
    """A big turn copied onto a fork (timelines.py) as it stood on the fork's day: stages that came later are taken back
    (the fork's own days bring them again), and the outcomes its stages rolled by then are copied to the fork, so an
    undo there never touches the timeline it came from."""
    found, details = dict(row), decode(row['details'])
    while details.get('before') and details.get('stage_on', '') > cutoff:
        snapshot = details['before'][-1]
        details = {**snapshot['details'], 'before': details['before'][:-1]}
        found.update(title=snapshot['title'], told=snapshot['told'], share=snapshot['share'],
                     changes=encode(snapshot['changes']), undo=encode(snapshot['undo']))
    undo = decode(found['undo'])
    if undo.get('decided'):
        undo['decided'] = [forked_outcome(connection, consequence_id, row['id'], copy_id, timeline_id)
                           for consequence_id in undo['decided'] if decided_by(connection, consequence_id, cutoff)]
    if undo.get('moving_in'):  # The fork's own shared home, the copy of this one (moving_in.copy keeps `origin`).
        home = optional(connection, 'SELECT id, origin FROM moving_in WHERE id=?', (undo['moving_in']['id'],))
        undo['moving_in'] = {**undo['moving_in'], 'timeline_id': timeline_id,
                             'origin': (home['origin'] or home['id']) if home else undo['moving_in']['id']}
    return {**found, 'id': copy_id, 'timeline_id': timeline_id, 'undo': encode(undo), 'details': encode(details)}


def decided_by(connection, consequence_id: str, cutoff: str) -> bool:
    found = optional(connection, 'SELECT decided_on FROM consequences WHERE id=?', (consequence_id,))
    return bool(found and found['decided_on'] <= cutoff)


def forked_outcome(connection, consequence_id: str, row_id: str, copy_id: str, timeline_id: str) -> str:
    subject = optional(connection, 'SELECT subject FROM consequences WHERE id=?', (consequence_id,))['subject']
    return consequences.copy(connection, consequence_id, timeline_id, subject.replace(row_id, copy_id))


def reverse(connection, found: dict):
    """What an undone big turn changed beyond home items: the shared home goes back where it was, and the marks its
    stages' outcomes left (a business's months, how caring goes) come off."""
    for consequence_id in found.get('decided', ()):
        consequences.clear_marks(connection, consequence_id)
    if found.get('moving_in'):
        back = found['moving_in']
        if back.get('timeline_id'):  # Undone on a fork: the fork's copy of the shared home (fork_row).
            connection.execute('UPDATE moving_in SET neighbourhood=?, home_item_id=? WHERE timeline_id=? AND '
                               '(origin=? OR id=?)', (back['neighbourhood'], back['home_item_id'], back['timeline_id'],
                                                      back['origin'], back['origin']))
            return
        connection.execute('UPDATE moving_in SET neighbourhood=?, home_item_id=? WHERE id=?',
                           (back['neighbourhood'], back['home_item_id'], back['id']))


def undone(connection, row: dict):
    """Exams, check-ups and a parent's appointments still to come leave the calendar."""
    for source in ('school', 'health'):
        connection.execute("UPDATE life_admin SET status='removed' WHERE timeline_id=? AND source=? AND key LIKE ? "
                           "AND status='planned'", (row['timeline_id'], source, f"{source}:{row['id']}:%"))


# The week, the calendar and money ---------------------------------------------------------------------------------

def reshaped(definition: dict, changes: dict) -> list[dict]:
    """Their schedule with work turned into time of their own (retired) or their own business's hours, a class carved
    out of free time, and evenings at a parent's they care for (companion/life/health_turns.py)."""
    schedule = [{**item, 'key': item.get('key') or routine.slug(item['label'])}
                for item in definition.get('schedule') or routine.DEFAULT_SCHEDULE]
    if changes.get('retired'):
        schedule = [{**item, 'kind': 'leisure', 'label': changes['retired']['label'], 'themes': []}
                    if item.get('kind') == 'work' else item for item in schedule]
    if changes.get('business'):
        schedule = [{**item, 'label': changes['business']['label']} if item.get('kind') == 'work' else item
                    for item in schedule]
    if changes.get('study'):
        schedule = carved(schedule, changes['study'], {'key': 'class', 'kind': 'study', 'themes': CLASS_THEMES})
    if changes.get('caring'):
        schedule = carved(schedule, changes['caring'], {'key': 'caring', 'kind': 'errand', 'themes': ['caring']})
    return schedule


def carved(schedule: list[dict], taken: dict, block: dict) -> list[dict]:
    """The schedule with some days of one block (`taken['from']`) given to another."""
    result = []
    for item in schedule:
        if item['key'] != taken['from']:
            result.append(item)
            continue
        rest = [day for day in item.get('days', range(7)) if day not in taken['days']]
        result += [{**item, 'days': rest}] if rest else []
        result.append({**block, 'label': taken['label'], 'days': taken['days'], 'start': item['start'],
                       'end': item['end']})
    return result


def calendar(connection, companion: dict, today: date, now) -> int:
    """Exams coming up in the next three weeks go on the shared calendar, held like an appointment."""
    from companion.life import admin
    added = 0
    for row in running(connection, companion['active_timeline_id']):
        details = decode(row['details'])
        if details.get('stage') not in ('studying', 'retraining'):
            continue
        for day in details.get('exams', ()):
            when = date.fromisoformat(day)
            if today <= when <= today + timedelta(days=EXAMS_AHEAD):
                added += bool(admin.add(connection, companion, key=f"school:{row['id']}:exam:{day}", source='school',
                                        kind='exam', title='Exam', done=f"sat an exam for {details['course']}",
                                        day=when, at=details['study']['start'], minutes=120, fixed=True, out=True,
                                        now=now, study=True))  # In the class's own time, on the day it says.
    return added + health_turns.calendar(connection, companion, today, now)


def purchases(connection, timeline_id: str, start: date, end: date) -> list[dict]:
    """Course fees, a deposit on a place, what opening a business took and a parent's care between two local dates, as
    money.household purchases. A deposit and a business's start-up come from savings."""
    found = [*business.purchases(connection, timeline_id, start, end),
             *health_turns.purchases(connection, timeline_id, start, end)]
    for row in many(connection, "SELECT kind, details FROM life_chapters WHERE timeline_id=? AND undone_at IS NULL AND "
                    'kind IN (?, ?, ?)', (timeline_id, 'school', 'career_change', 'buy_place')):
        details = decode(row['details'])
        for fee in details.get('fees', ()):
            if start.isoformat() <= fee['on'] <= end.isoformat():
                found.append({'text': f"paid the term's fees for {details['course']}", 'date': fee['on'],
                              'cost': fee['cost'], 'spend': '', 'for': 'school'})
        deposit = details.get('deposit')
        if deposit and details.get('stage') == 'moved' and start.isoformat() <= deposit['on'] <= end.isoformat():
            found.append({'text': 'put down a deposit on a place of your own', 'date': deposit['on'],
                          'cost': deposit['cost'], 'spend': '', 'for': 'deposit', 'savings': True})
    return found


def pay(connection, timeline_id: str, day: date, found: dict | None) -> dict | None:
    """Retired, they live on a pension (a share of their pay); running a business, on what it makes
    (companion/life/business.py); otherwise their pay as Work life has it."""
    row = finished(connection, timeline_id, 'retire', 'retired')
    if not row or decode(row['details'])['stage_on'] > day.isoformat():
        return business.pay(connection, timeline_id, day, found)
    return {'factor': decode(row['details'])['pension'], 'between_jobs': False, 'retired': True}


# Reading -------------------------------------------------------------------------------------------------------

def big_days(connection, timeline_id: str, since: str, until: str) -> list[dict]:
    """Graduations and last days at work between two local dates, for Big days in the circle:
    [{kind: 'graduation' | 'retirement', on, chapter_id, title}]."""
    found = []
    for row in many(connection, 'SELECT * FROM life_chapters WHERE timeline_id=? AND undone_at IS NULL AND kind IN '
                    "('school', 'career_change', 'retire')", (timeline_id,)):
        details = decode(row['details'])
        kind, on = ('retirement', details.get('last_day')) if row['kind'] == 'retire' else \
            ('graduation', details.get('ends_on'))
        if on and since <= on <= until:
            found.append({'kind': kind, 'on': on, 'chapter_id': row['id'], 'title': row['title']})
    return sorted(found, key=lambda item: item['on'])


def line(row: dict) -> str:
    """Where a big turn stands, in a line for the Character page."""
    details = decode(row['details'])
    stage = details.get('stage')
    if stage == 'enrolled':
        return f"Signed up for {details['course']}; classes start {short_day(details['starts_on'])}."
    if stage in ('studying', 'retraining'):
        upcoming = [day for day in details.get('exams', ()) if day >= details.get('stage_on', '')]
        exam = f" Next exam {short_day(upcoming[0])}." if upcoming else ''
        what = f"Retraining as {article(details['job'])}" if stage == 'retraining' else f"Taking {details['course']}"
        return (f"{what} on {days_text(details['study']['days'])}.{exam} Finishes {short_day(details['ends_on'])}" +
                (', then starts the new job.' if stage == 'retraining' else '.'))
    if stage == 'hunting':
        place = details['place']['details']
        currency = place.get('currency') or {}
        mortgage = money.amount(place['rent'], currency) if currency and place.get('rent') else ''
        return (f"Buying {place['description']}" + (' with you' if details.get('shared') else '') +
                f"; keys on {short_day(details['keys_on'])}." +
                (f' The mortgage will be about {mortgage} a month.' if mortgage else ''))
    if stage == 'leaving':
        return f"Retiring; their last day at work is {short_day(details['last_day'])}."
    if row['kind'] in LINES:
        return LINES[row['kind']](row, details)
    return row['title'] + '.'


def lately(connection, companion: dict) -> dict:
    """The Character page's view: big turns on their way, and the latest chapters that already happened."""
    timeline_id = companion['active_timeline_id']
    now = [{'id': row['id'], 'kind': row['kind'], 'started_on': row['started_on'], 'line': line(row)}
           for row in running(connection, timeline_id)]
    done = many(connection, "SELECT * FROM life_chapters WHERE timeline_id=? AND undone_at IS NULL AND "
                "json_extract(details, '$.next_on') IS NULL ORDER BY COALESCE(json_extract(details, '$.stage_on'), "
                'started_on) DESC, created_at DESC LIMIT 3', (timeline_id,))
    return {'now': now, 'lately': [{'id': row['id'], 'kind': row['kind'],
                                    'on': decode(row['details']).get('stage_on') or row['started_on'],
                                    'title': row['title']} for row in done]}


# Part 2 ---------------------------------------------------------------------------------------------------------
# Starting a business, a health turn and caring for a parent live in their own modules, which build on the helpers
# above; they join the plans, stages and Character page lines here.

from companion.life import business, health_turns  # noqa: E402

PLANS.update(business.PLANS)
PLANS.update(health_turns.PLANS)
STAGES.update(business.STAGES)
STAGES.update(health_turns.STAGES)
LINES = {**business.LINES, **health_turns.LINES}
