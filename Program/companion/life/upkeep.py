"""Home upkeep: the laundry, the dishes and the clutter, and the big clean on a day off (v0.10 #25).

Three kinds of mess build up day by day from the companion's week, without a model: more laundry and clutter on
work days, dishes from the meals they cook at home (`meals_cooked`), a little extra from each pet (`pets_at_home`),
nothing while they are away on a trip and a suitcase of laundry when they get back. Each companion has a seeded habit
from the words that describe them (neat, average or messy) that sets how much they let build up before dealing with
it, and how often they deal with it on a work day. Once the mess passes their habit's limit, a day off brings a big
clean, never on a day with a plan with the user (it waits for the next day off).

Each day is walked from the one before with seeded dice, and days before their today are kept once walked
(upkeep_days), so what already happened never changes and the days ahead follow from it. The user can set how tidy
the place is today ("Set it"); the walk starts again from there and drifts with their week. The realism slider
(life_settings.upkeep_realism) turns it off, or makes mess lighter or heavier.

What happened shows up as one sentence woven onto an at-home agenda entry (`touch`, called once from
companion/life/agenda.py), as plain lines in the chat's home section (`context_lines`), in pictures at home when an
area is a real mess (`image_hint`) and on the Character page's Home panel (`view`). Life admin reads the big cleans
and wash days ahead through `chores_between`.
"""
from datetime import date, timedelta

from companion.clock import stamp, zone
from companion.database import decode, encode, many, one, optional
from companion.errors import require
from companion.life import routine, upkeep_bank
from companion.world import generators

COMPANION = 'companion'
AREAS = ('laundry', 'dishes', 'clutter')
HABITS = ('neat', 'average', 'messy')
# Realism slider: 0 off, 1 light (I want an easy life), 2 true to life, 3 messy (Bring on the drama).
SCALE = {1: 0.6, 2: 1.0, 3: 1.4}
KEEN = {1: 1.2, 2: 1.0, 3: 0.75}
# How much they let build up before dealing with it: sooner in an easy life, later with drama.
PATIENCE = {1: 0.7, 2: 1.0, 3: 1.3}
# Per habit: when each area gets dealt with, the total that calls for a big clean, the chance of dealing with an area
# past its limit on a day off and on a work day, and where a new home starts.
LIMITS = {'neat': {'laundry': 30, 'dishes': 20, 'clutter': 25},
          'average': {'laundry': 50, 'dishes': 40, 'clutter': 45},
          'messy': {'laundry': 75, 'dishes': 65, 'clutter': 70}}
BIG = {'neat': 70, 'average': 120, 'messy': 175}
CHANCE = {'neat': (0.95, 0.75), 'average': (0.8, 0.45), 'messy': (0.55, 0.2)}
SETTLE = {'neat': 10, 'average': 28, 'messy': 48}
# After dealing with an area, and after a big clean.
CLEANED = {'laundry': 5, 'dishes': 4, 'clutter': 10}
FRESH = 3
# Daily build-up before the slider: (work day, day off). Dishes come per meal cooked at home.
BUILD = {'laundry': (8, 6), 'clutter': (5, 3)}
PER_MEAL = 9
TRIP_LAUNDRY = 30
# Agreed with Pets (v0.10 #15): fish, reptiles and a horse at a stable make no mess at home; unknown kinds a little.
PET_MESS = {'dog': 3, 'cat': 2, 'ferret': 1, 'rabbit': 1, 'guinea-pig': 1, 'hamster': 1, 'parrot': 1, 'bird': 1,
            'chickens': 1, 'fish': 0, 'lizard': 0, 'snake': 0, 'tortoise': 0, 'horse': 0}
PILING = 70
BUSY_KINDS = {'work', 'study'}
MODERN = {'modern', 'future'}
# Set it: how tidy the place is, from spotless to a disaster, and the mess each level stands for.
TIDINESS = ('Spotless', 'Tidy', 'Lived-in', 'Messy', 'A disaster')
SET_TO = (3, 20, 45, 72, 95)
TIDY_BANDS = (12, 35, 58, 82)

NEAT_WORDS = ('neat', 'tidy', 'organized', 'organised', 'meticulous', 'orderly', 'fastidious', 'perfectionist',
              'methodical', 'disciplined', 'precise', 'minimalist', 'particular', 'fussy', 'clean', 'spotless',
              'punctual', 'careful', 'structured', 'efficient')
MESSY_WORDS = ('messy', 'chaotic', 'disorganized', 'disorganised', 'scatterbrained', 'scattered', 'untidy', 'sloppy',
               'slob', 'lazy', 'carefree', 'absent-minded', 'forgetful', 'spontaneous', 'laid-back', 'easygoing',
               'procrastinator', 'procrastinates', 'hoarder', 'cluttered', 'impulsive', 'distracted', 'free-spirited')
HABIT_WORDS = {'neat': 'keeps things neat and deals with mess as it comes',
               'average': 'keeps on top of things most weeks',
               'messy': 'lets things pile up and catches up in one go on a day off'}
DONE_WORDS = {'laundry': 'caught up on the {wash}', 'dishes': 'did the dishes', 'clutter': 'tidied up',
              'big-clean': 'did a big clean'}

# Moments at home where housework can come up, and where something can get done.
AT_HOME = {'chores', 'home-cooking', 'reading', 'nap', 'slow', 'sick-day'}
DOING = {'chores', 'slow', 'reading', 'home-cooking'}
WORKING = {'steady-shift', 'busy-shift', 'library', 'study-cafe'}


# --- Settings and state ---

def level(connection) -> int:
    row = optional(connection, 'SELECT upkeep_realism FROM life_settings WHERE id=1')
    return int(row['upkeep_realism']) if row else 2


def words_of(definition: dict) -> set[str]:
    phrases = [definition.get(key) or '' for key in ('personality', 'identity', 'voice', 'background')]
    phrases += [*definition.get('interests', ()), *definition.get('life_themes', ())]
    return {word.strip('.,;:!?()"\'').casefold() for phrase in phrases for word in phrase.split()}


def seeded_habit(seed: str, definition: dict) -> str:
    """Neat, average or messy: the words that describe them lean it, a seeded roll decides."""
    words = words_of(definition)
    neat = sum(word in words for word in NEAT_WORDS)
    messy = sum(word in words for word in MESSY_WORDS)
    weights = [1.0 + 2.5 * neat, 2.0, 1.0 + 2.5 * messy]
    return generators.pick(seed, 'habit', list(HABITS), weights)


def ensure(connection, timeline_id: str, definition: dict, world, now) -> dict:
    """The timeline's upkeep state, made the first time it is needed."""
    state = optional(connection, 'SELECT * FROM upkeep_state WHERE timeline_id=?', (timeline_id,))
    if state:
        return state
    from companion.life import circle, home  # home reads the agenda's day; import late
    seed = f'upkeep:{timeline_id}'
    data = circle.city_data(definition, world)
    era = 'modern' if data is None or data['era'] in MODERN else data['era']
    start = home.started_on(connection, timeline_id, definition.get('timezone'))
    connection.execute('INSERT INTO upkeep_state (timeline_id, seed, habit, started, era, created_at, updated_at) '
                       'VALUES (?, ?, ?, ?, ?, ?, ?)', (timeline_id, seed, seeded_habit(seed, definition),
                                                        start.isoformat(), era, stamp(now), stamp(now)))
    return one(connection, 'SELECT * FROM upkeep_state WHERE timeline_id=?', (timeline_id,))


def state_of(connection, timeline_id: str) -> dict | None:
    return optional(connection, 'SELECT * FROM upkeep_state WHERE timeline_id=?', (timeline_id,))


def habit(state: dict) -> str:
    return state['habit_set'] or state['habit']


# --- Hooks other features fill in (Pets, Kitchen) ---

def pets_at_home(connection, timeline_id: str, day: date) -> list[dict]:
    """The companion's pets on this date, [{name, variety}]. Pets (v0.10 #15) owns where pets live."""
    from companion.life import home
    return [{'name': item['name'], 'variety': item['variety']} for item in home.items_on(connection, timeline_id, day)
            if item['kind'] == 'pet']


def meals_cooked(context: dict, connection, timeline_id: str, day: date) -> int:
    """Meals they cook at home on this date (0 to 2), from their dinners in Kitchen and food (companion/life/kitchen.py),
    read once per walk."""
    from companion.life import kitchen  # kitchen reads the agenda, which touches upkeep, so import late
    if 'kitchen' not in context:
        context['kitchen'] = kitchen.peek(connection, timeline_id, context['definition'])
    return kitchen.cooked_on(context['kitchen'], day)


# --- The walk ---

def busy_days(definition: dict) -> set[int]:
    """Weekdays with work or study in their routine."""
    schedule, _default = routine.blocks(definition)
    return {weekday for block in schedule if block.kind in BUSY_KINDS for weekday in block.days}


def user_plan_days(connection, timeline_id: str, since: date) -> set[str]:
    """Local dates with a plan with the user (Go somewhere together)."""
    from companion.life import outings
    return {outing['local_date'] for outing in outings.in_force(connection, timeline_id, since.isoformat())}


def away_days(connection, timeline_id: str, since: date) -> set[str]:
    from companion.life import trips
    return set(trips.by_date(connection, timeline_id, since.isoformat()))


def pet_mess(pets: list[dict]) -> float:
    return sum(PET_MESS.get(pet['variety'], 1) for pet in pets)


def stored(connection, timeline_id: str, since: date, through: date) -> list[dict]:
    rows = many(connection, 'SELECT * FROM upkeep_days WHERE timeline_id=? AND local_date>=? AND local_date<=? '
                'ORDER BY local_date', (timeline_id, since.isoformat(), through.isoformat()))
    return [{'date': row['local_date'], 'mess': decode(row['mess']), 'done': decode(row['done']),
             'away': bool(row['away']), 'busy': bool(row['busy']), 'since_big': row['since_big']} for row in rows]


def starting(connection, state: dict, through: date) -> dict:
    """The day the walk to `through` begins from: the day the user set it, else the last day already kept, else the
    timeline's first day with a seeded start near their habit's usual."""
    timeline_id = state['timeline_id']
    if state['set_on'] and state['set_on'] <= through.isoformat():
        kept = optional(connection, 'SELECT MAX(local_date) AS day FROM upkeep_days WHERE timeline_id=? '
                        'AND local_date>=? AND local_date<=?', (timeline_id, state['set_on'], through.isoformat()))
        if not kept['day']:
            mess = float(SET_TO[state['set_level']])
            return {'date': state['set_on'], 'mess': {area: mess for area in AREAS}, 'done': [], 'away': False,
                    'busy': False, 'since_big': 0}
    last = optional(connection, 'SELECT MAX(local_date) AS day FROM upkeep_days WHERE timeline_id=? AND local_date<=?',
                    (timeline_id, through.isoformat()))
    if last['day']:
        return stored(connection, timeline_id, date.fromisoformat(last['day']), date.fromisoformat(last['day']))[0]
    base = SETTLE[habit(state)]
    return {'date': state['started'], 'done': [], 'away': False, 'busy': False, 'since_big': 0,
            'mess': {area: base * (0.6 + 0.8 * generators.unit(state['seed'], 'start', area)) for area in AREAS}}


def walk(connection, timeline_id: str, definition: dict, through: date, slider: int | None = None,
         since: date | None = None, keep_before: date | None = None) -> list[dict]:
    """Each day from `since` (default `through`) to `through`: {date, mess {area: 0-100}, done [areas or
    'big-clean'], away, busy, since_big}. Days before `keep_before` (their today) are kept once walked, so what
    already happened never changes; days after are walked from the last kept one. Empty when upkeep is off or the
    state was never made."""
    state = state_of(connection, timeline_id)
    slider = level(connection) if slider is None else slider
    if not state or not slider:
        return []
    since = since or through
    begin = starting(connection, state, through)
    first = date.fromisoformat(begin['date'])
    days = [*stored(connection, timeline_id, since, first - timedelta(days=1)), begin]
    context = {'kind': habit(state), 'busy': busy_days(definition), 'scale': SCALE[slider], 'keen': KEEN[slider],
               'patience': PATIENCE[slider],
               'planned': user_plan_days(connection, timeline_id, first), 'seed': state['seed'],
               'away': away_days(connection, timeline_id, first), 'definition': definition}
    day = first
    while day < through:
        day += timedelta(days=1)
        days.append(step(connection, timeline_id, days[-1], day, context))
    if keep_before:
        keep(connection, timeline_id, [found for found in days if first.isoformat() < found['date'] <
                                       keep_before.isoformat()])
    return [found for found in days if found['date'] >= since.isoformat()]


def step(connection, timeline_id: str, before: dict, day: date, context: dict) -> dict:
    """One day on from `before`: the mess builds up, then maybe a big clean on a free day or a chore or two."""
    key, seed, kind, scale = day.isoformat(), context['seed'], context['kind'], context['scale']
    busy = day.weekday() in context['busy']
    mess, since_big = dict(before['mess']), before['since_big'] + 1
    if key in context['away']:
        return {'date': key, 'mess': mess, 'done': [], 'away': True, 'busy': busy, 'since_big': since_big}

    def jitter(area):
        return scale * (0.7 + 0.6 * generators.unit(seed, 'build', key, area))
    meals = meals_cooked(context, connection, timeline_id, day)
    pets = pet_mess(pets_at_home(connection, timeline_id, day))
    mess['laundry'] += (TRIP_LAUNDRY if before['away'] else 0) + BUILD['laundry'][not busy] * jitter('laundry')
    mess['dishes'] += PER_MEAL * meals * jitter('dishes')
    mess['clutter'] += (BUILD['clutter'][not busy] + pets) * jitter('clutter')
    mess = {area: min(100.0, value) for area, value in mess.items()}
    free = not busy and key not in context['planned']
    weekly = kind == 'neat' and since_big >= 7 and sum(mess.values()) >= 40
    if free and (sum(mess.values()) >= BIG[kind] * context['patience'] or weekly):
        return {'date': key, 'mess': {area: float(FRESH) for area in AREAS}, 'done': ['big-clean'], 'away': False,
                'busy': busy, 'since_big': 0}
    done = []
    for area in AREAS:
        chance = 1.0 if mess[area] >= 100 and not busy else min(0.97, CHANCE[kind][busy] * context['keen'])
        if mess[area] >= LIMITS[kind][area] * context['patience'] and generators.unit(seed, 'deal', key, area) < chance:
            mess[area] = float(CLEANED[area])
            done.append(area)
    return {'date': key, 'mess': mess, 'done': done, 'away': False, 'busy': busy, 'since_big': since_big}


def keep(connection, timeline_id: str, days: list[dict]):
    connection.executemany(
        'INSERT OR IGNORE INTO upkeep_days (timeline_id, local_date, mess, done, away, busy, since_big) '
        'VALUES (?, ?, ?, ?, ?, ?, ?)',
        [(timeline_id, day['date'], encode(day['mess']), encode(day['done']), int(day['away']), int(day['busy']),
          day['since_big']) for day in days])


def on(connection, timeline_id: str, definition: dict, day: date, slider: int | None = None,
       keep_before: date | None = None) -> dict | None:
    days = walk(connection, timeline_id, definition, day, slider, keep_before=keep_before)
    return days[-1] if days else None


# --- Words ---

def wash_word(state: dict) -> str:
    return 'laundry' if state['era'] in MODERN or state['era'] == 'jazz-age' else 'washing'


def band(value: float, bands=upkeep_bank.STATE_BANDS) -> int:
    return sum(value >= edge for edge in bands)


def area_text(state: dict, area: str, value: float) -> str:
    return upkeep_bank.STATES[area][band(value)].format(wash=wash_word(state))


def tidiness(mess: dict) -> int:
    """0 (spotless) to 4 (a disaster), from the average mess."""
    return band(sum(mess.values()) / len(AREAS), TIDY_BANDS)


def done_text(state: dict, kind: str) -> str:
    return DONE_WORDS[kind].format(wash=wash_word(state))


def lines_for(state: dict, bank) -> list[str]:
    """The bank's lines that suit their era, without the era mark."""
    modern = state['era'] in MODERN
    return [line[2:] if line.startswith('m|') else line for line in bank if modern or not line.startswith('m|')]


DONE_BANKS = {'laundry': upkeep_bank.LAUNDRY_DONE, 'dishes': upkeep_bank.DISHES_DONE,
              'clutter': upkeep_bank.CLUTTER_DONE, 'big-clean': upkeep_bank.BIG_CLEAN}
PILING_BANKS = {'laundry': upkeep_bank.LAUNDRY_PILING, 'dishes': upkeep_bank.DISHES_PILING,
                'clutter': upkeep_bank.CLUTTER_PILING}


def pet_line(state: dict, seed: str, pets: list[dict]) -> str | None:
    pet = generators.pick(seed, 'pet', pets)
    if pet is None:
        return None
    kind = 'dog' if 'dog' in pet['variety'] else 'cat' if 'cat' in pet['variety'] else ''
    fitting = [line.split('|', 1)[-1] for line in lines_for(state, upkeep_bank.PET_MESS)
               if '|' not in line or line.startswith(f'{kind}|')]
    return generators.pick(seed, 'pet-line', fitting).format(pet=pet['name'])


# --- Their agenda ---

def big_clean_key(local_date: str) -> str:
    """The week's big clean on Life admin's calendar (companion/life/admin.py). Keyed by week, not day: the walk ahead
    can settle a big clean on a different day once more of the week is planned, and it is still the same one."""
    return f"upkeep:big-clean:{date.fromisoformat(local_date).strftime('%G-W%V')}"


def told(connection, timeline_id: str, local_date: str, kind: str) -> bool:
    """Whether the day's agenda already tells this; the week's big clean on Life admin's calendar is told there, in
    its own slot."""
    if kind == 'big-clean' and optional(connection, "SELECT id FROM life_admin WHERE timeline_id=? AND key=? AND "
                                        "status!='removed'", (timeline_id, big_clean_key(local_date))):
        return True
    return bool(optional(connection, "SELECT id FROM life_agenda WHERE timeline_id=? AND subject=? AND local_date=? "
                         "AND json_extract(entry, '$.upkeep.kind')=? LIMIT 1",
                         (timeline_id, COMPANION, local_date, kind)))


def touch(connection, timeline_id: str, subject: str, entry: dict | None, local_date: str, seed: str,
          definition: dict, world, now) -> dict | None:
    """The companion's agenda entry with housework woven in: the day's big clean or a chore they did, once each, or
    now and then the mess they are living with. Circle members' entries, work and away moments pass through."""
    activity = (entry or {}).get('activity')
    if subject != COMPANION or not entry or activity not in AT_HOME or entry.get('home') or not level(connection):
        return entry
    ensure(connection, timeline_id, definition, world, now)
    state = state_of(connection, timeline_id)
    today = now.astimezone(zone(definition.get('timezone') or 'UTC')).date()
    # Keep only days before the one being drawn: its dinners (companion/life/kitchen.py) follow its agenda, which is
    # still being written, so it is walked again once drawn.
    drawing = date.fromisoformat(local_date)
    day = on(connection, timeline_id, definition, drawing, keep_before=min(today, drawing))
    if not day or day['away']:
        return entry
    found = pick_moment(connection, timeline_id, state, day, activity, seed)
    if not found:
        return entry
    kind, sentence = found
    return {**entry, 'summary': f"{entry['summary'].rstrip()} {sentence}", 'upkeep': {'kind': kind,
                                                                                      'sentence': sentence}}


def pick_moment(connection, timeline_id, state, day, activity, seed) -> tuple[str, str] | None:
    roll = generators.unit(seed, 'upkeep')
    local_date = day['date']
    if activity in DOING:
        for kind in day['done']:
            if not told(connection, timeline_id, local_date, kind) and (activity == 'chores' or roll < 0.5):
                return kind, done_line(connection, timeline_id, state, kind, day, seed)
        if activity == 'chores':
            # A chores slot always does something, even on a day the walk has nothing due.
            worst = max(AREAS, key=lambda area: day['mess'][area])
            return f'small-{worst}', done_line(connection, timeline_id, state, worst, day, seed)
    worst = max(AREAS, key=lambda area: day['mess'][area])
    if day['mess'][worst] >= PILING and roll < 0.3 and not told(connection, timeline_id, local_date, 'piling'):
        return 'piling', generators.pick(seed, 'piling-line', lines_for(state, PILING_BANKS[worst]))
    return None


def done_line(connection, timeline_id, state, kind, day, seed) -> str:
    if kind in ('clutter', 'big-clean') and generators.unit(seed, 'pet-mess') < 0.35:
        pets = pets_at_home(connection, timeline_id, date.fromisoformat(day['date']))
        if line := pet_line(state, seed, pets):
            return line
    return generators.pick(seed, f'{kind}-line', lines_for(state, DONE_BANKS[kind]))


def rebuild(connection, timeline_id: str, now):
    """After Set it or a habit change: forget upcoming agenda entries that mention housework, so they are drawn again."""
    removed = connection.execute(
        "DELETE FROM life_agenda WHERE timeline_id=? AND subject=? AND status='upcoming' "
        "AND json_extract(entry, '$.upkeep') IS NOT NULL", (timeline_id, COMPANION)).rowcount
    if removed:
        connection.execute('UPDATE agenda_cursors SET through=MIN(through, ?) WHERE timeline_id=? AND subject=?',
                           (stamp(now), timeline_id, COMPANION))


def settings_changed(connection, now):
    """The Housework slider changed: upcoming moments that mention housework are drawn again under it (none when it
    is off). Days already kept stay as they were."""
    for row in many(connection, 'SELECT active_timeline_id AS timeline_id FROM companions'):
        rebuild(connection, row['timeline_id'], now)


# --- Chat, pictures and Life admin ---

def last_big_clean(days: list[dict], state: dict | None = None) -> str | None:
    """The last big clean in these days; one from before the user last set how tidy the place is does not count."""
    since = (state or {}).get('set_on') or ''
    return next((day['date'] for day in reversed(days) if 'big-clean' in day['done'] and day['date'] >= since), None)


def context_lines(connection, timeline_id: str, definition: dict, day: date) -> list[tuple[str, str]]:
    """(identity, line) pairs for the chat's home section: how the place is today, their habit and a recent big clean."""
    state = state_of(connection, timeline_id)
    days = walk(connection, timeline_id, definition, day, since=day - timedelta(days=9)) if state else []
    if not days:
        return []
    today = days[-1]
    if today['away']:
        return []
    words = ' '.join(area_text(state, area, today['mess'][area]) for area in AREAS)
    lines = [(f'upkeep:{today["date"]}', f'- Housework today: {words}'),
             (f'upkeep:habit:{habit(state)}', f'- Your habit: you {you_habit(habit(state))}.')]
    cleaned = last_big_clean(days, state)
    if cleaned:
        lines.append((f'upkeep:big:{cleaned}', f'- Recently ({days_ago(date.fromisoformat(cleaned), day)}): you did a '
                      'big clean.'))
    return lines


def days_ago(then: date, today: date) -> str:
    """"today", "yesterday" or "Sunday, 3 days ago": models misread a bare date as yesterday (A/B, 2026-10-13)."""
    gap = (today - then).days
    return 'today' if gap <= 0 else 'yesterday' if gap == 1 else f"{then.strftime('%A')}, {gap} days ago"


def you_habit(kind: str) -> str:
    return {'neat': 'keep things neat and deal with mess as it comes', 'average': 'keep on top of things most weeks',
            'messy': 'let things pile up and catch up in one go on a day off'}[kind]


def image_hint(connection, timeline_id: str, event: dict) -> str:
    """A real mess where the picture is at home: what can be seen of it, or ''."""
    moment = event.get('moment') or {}
    if event.get('place') or moment.get('activity') not in AT_HOME or not moment.get('local_date'):
        return ''
    from companion.characters import definition_for_timeline
    day = on(connection, timeline_id, definition_for_timeline(connection, timeline_id),
             date.fromisoformat(moment['local_date']))
    if not day or day['away']:
        return ''
    worst = max(AREAS, key=lambda area: day['mess'][area])
    return f"In view: {upkeep_bank.PICTURE[worst]}." if day['mess'][worst] >= PILING else ''


def chores_between(connection, timeline_id: str, definition: dict, start: date, end: date) -> list[dict]:
    """Big cleans and wash days from `start` to `end` inclusive (they can be ahead): [{date, kind, text}]."""
    state = state_of(connection, timeline_id)
    if not state:
        return []
    return [{'date': day['date'], 'kind': kind, 'text': done_text(state, kind)}
            for day in walk(connection, timeline_id, definition, end, since=start) for kind in day['done'] if kind in ('big-clean', 'laundry')]


# --- The Home panel ---

def view(connection, timeline_id: str, definition: dict, day: date) -> dict:
    slider = level(connection)
    state = state_of(connection, timeline_id)
    days = walk(connection, timeline_id, definition, day, slider or 2, since=day - timedelta(days=13),
                keep_before=day)
    today = days[-1]
    recent = [{'date': entry['date'], 'kind': kind, 'text': done_text(state, kind)}
              for entry in reversed(days) for kind in entry['done']]
    return {'on': bool(slider), 'level': slider, 'today': day.isoformat(), 'away': today['away'],
            'habit': habit(state), 'habit_set': bool(state['habit_set']), 'habit_text': HABIT_WORDS[habit(state)],
            'tidiness': tidiness(today['mess']), 'tidiness_label': TIDINESS[tidiness(today['mess'])],
            'set_on': state['set_on'], 'levels': list(TIDINESS),
            'areas': [{'area': area, 'text': area_text(state, area, today['mess'][area]),
                       'value': round(today['mess'][area])} for area in AREAS],
            'last_big_clean': last_big_clean(days, state), 'recent': recent[:6]}


def set_tidiness(connection, timeline_id: str, index: int, day: date, now):
    require(0 <= index < len(TIDINESS), 'Pick one of the listed levels.', 422)
    connection.execute('UPDATE upkeep_state SET set_on=?, set_level=?, updated_at=? WHERE timeline_id=?',
                       (day.isoformat(), index, stamp(now), timeline_id))
    connection.execute('DELETE FROM upkeep_days WHERE timeline_id=? AND local_date>=?', (timeline_id, day.isoformat()))
    rebuild(connection, timeline_id, now)


def set_habit(connection, timeline_id: str, kind: str | None, now):
    require(kind is None or kind in HABITS, 'Pick neat, average or messy.', 422)
    connection.execute('UPDATE upkeep_state SET habit_set=?, updated_at=? WHERE timeline_id=?',
                       (kind, stamp(now), timeline_id))
    rebuild(connection, timeline_id, now)


# --- Timelines ---

def copy(connection, parent_id: str, new_id: str, cutoff: str):
    """A fork keeps their habit, the days already walked and a tidiness set before the fork; after that it is walked
    again."""
    state = optional(connection, 'SELECT * FROM upkeep_state WHERE timeline_id=?', (parent_id,))
    if not state:
        return
    kept = state['set_on'] and state['set_on'] <= cutoff[:10]
    connection.execute(
        'INSERT INTO upkeep_state (timeline_id, seed, habit, habit_set, started, era, set_on, set_level, created_at, '
        'updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (new_id, state['seed'], state['habit'], state['habit_set'], state['started'], state['era'],
         state['set_on'] if kept else None, state['set_level'] if kept else None, state['created_at'], cutoff))
    connection.execute('INSERT INTO upkeep_days (timeline_id, local_date, mess, done, away, busy, since_big) '
                       'SELECT ?, local_date, mess, done, away, busy, since_big FROM upkeep_days '
                       'WHERE timeline_id=? AND local_date<=?', (new_id, parent_id, cutoff[:10]))

