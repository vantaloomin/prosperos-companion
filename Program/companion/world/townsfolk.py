"""Townsfolk: the people who work at and hang around the city's places, run by simple rules.

Every place in a city has a few seeded people: staff (the barista, the barkeep, the librarian) and
regulars (the jogger in the park, the old man who reads the paper at the cafe). Each has a name that
fits the city and era, an age, a home neighborhood near the place, a temperament, a quirk, a flaw, a
desire and a goal they are working toward. Nobody is stored: a person is rebuilt from their key
(`town:<city>:<place>:<n>`) the same way every time, so a city of thousands costs nothing until someone
is asked about.

What they do is decided like an old video game's townsperson: a short list of if/then/else rules
(`whereabouts`) reads the hour, the weekday, their shifts and visits, their goal and their desire, and
says where they are and what they are doing. Their goal moves week by week (`story`): a roll each week,
nudged by their temperament and dragged by their flaw, makes progress, stalls or suffers a setback, and
once enough progress is made they reach it and move on to their next goal. No model is involved.
"""
import functools
from datetime import date, datetime

from companion.world import catalog, generators

MODERN = {'modern', 'future', 'other'}
EPOCH = date(2026, 1, 5)  # A Monday: goals start moving from here.
MAX_WEEKS = 520
PEOPLE = (2, 3)

# Who works at or hangs around each kind of place: (modern role, period role, staff?).
REGULAR = ('regular', 'regular', False)
ROLES = {
    'cafe': (('barista', 'counter hand', True), ('owner', 'proprietor', True), REGULAR),
    'restaurant': (('server', 'server', True), ('line cook', 'cook', True), ('owner', 'proprietor', True), REGULAR),
    'bar': (('bartender', 'barkeep', True), ('bouncer', 'doorman', True), REGULAR),
    'nightlife': (('bartender', 'barkeep', True), ('DJ', 'fiddler', True), REGULAR),
    'tavern': (('bartender', 'barkeep', True), ('cook', 'cook', True), REGULAR),
    'inn': (('front desk clerk', 'innkeeper', True), ('housekeeper', 'chambermaid', True), REGULAR),
    'market': (('stall vendor', 'stallholder', True), ('butcher', 'butcher', True), REGULAR),
    'library': (('librarian', 'librarian', True), ('library assistant', 'clerk', True), REGULAR),
    'fitness': (('personal trainer', 'trainer', True), ('front desk attendant', 'attendant', True), REGULAR),
    'museum': (('docent', 'guide', True), ('security guard', 'watchman', True), REGULAR),
    'venue': (('box office clerk', 'ticket seller', True), ('stagehand', 'stagehand', True), REGULAR),
    'stadium': (('concessions worker', 'vendor', True), ('groundskeeper', 'groundskeeper', True), REGULAR),
    'shopping': (('shop clerk', 'shop assistant', True), ('store manager', 'shopkeeper', True), REGULAR),
    'landmark': (('tour guide', 'guide', True), ('ticket taker', 'gatekeeper', True), REGULAR),
    'attraction': (('tour guide', 'guide', True), ('ticket taker', 'gatekeeper', True), REGULAR),
    'temple': (('caretaker', 'sexton', True), REGULAR),
    'workshop': (('craftsperson', 'artisan', True), ('apprentice', 'apprentice', True), REGULAR),
    'docks': (('dockworker', 'dockhand', True), ('harbor clerk', "harbormaster's clerk", True), REGULAR),
    'guildhall': (('clerk', 'guild clerk', True), REGULAR),
    'square': (('street vendor', 'hawker', True), ('street musician', 'street musician', False), REGULAR),
}
OUTDOOR = (('groundskeeper', 'groundskeeper', True), ('dog walker', 'dog walker', False),
           ('morning runner', 'early walker', False), ('street musician', 'street musician', False), REGULAR)
for _kind in ('park', 'garden', 'trail', 'beach'):
    ROLES[_kind] = OUTDOOR

# Shift windows by the part of the day a place is open, in minutes after midnight.
SHIFTS = {'morning': (6 * 60, 14 * 60), 'afternoon': (11 * 60, 19 * 60), 'evening': (16 * 60, 24 * 60),
          'late': (18 * 60, 24 * 60)}
VISITS = {'morning': (7 * 60 + 30, 10 * 60 + 30), 'afternoon': (12 * 60 + 30, 15 * 60 + 30), 'evening': (18 * 60, 21 * 60),
          'late': (21 * 60, 23 * 60 + 30)}
PARTS = (('morning', 5, 12), ('afternoon', 12, 17), ('evening', 17, 21), ('late', 21, 24))

TEMPERAMENTS = {
    'warm': ('warm', 'greeted everyone like an old friend', 0.0),
    'gruff': ('gruff', 'grunted a hello but softened after a minute', 0.0),
    'shy': ('shy', 'barely made eye contact at first', -0.05),
    'chatty': ('chatty', 'talked a mile a minute', 0.0),
    'deadpan': ('deadpan', 'had a bone-dry sense of humor', 0.0),
    'cheerful': ('cheerful', 'was cheerful in a way that was hard not to catch', 0.05),
    'anxious': ('anxious', 'seemed a little on edge', -0.05),
    'easygoing': ('easygoing', 'was completely unhurried about everything', 0.0),
    'driven': ('driven', 'had the look of someone with somewhere to be', 0.15),
    'dreamy': ('dreamy', 'kept drifting off mid-sentence', -0.05),
}
QUIRKS = (
    'remembers everyone\'s usual order', 'hums under their breath', 'wears the same green scarf every day',
    'carries a battered notebook everywhere', 'can\'t resist a terrible pun', 'knows every dog in the neighborhood '
    'by name', 'is always running five minutes late', 'collects odd little trinkets', 'names every plant they own',
    'has an opinion about everyone\'s shoes', 'talks to pigeons', 'sketches people when they think no one is looking',
    'whistles the same tune all day', 'keeps sweets in every pocket',
)
# Flaws: (text, slows their goal down, setback wording with {name}).
FLAWS = {
    'proud': ('too proud to ask for help', False, '{name} turned down help they needed and paid for it'),
    'procrastinator': ('puts everything off until the last minute', True, '{name} let a deadline slip right past'),
    'spender': ('spends money as fast as it comes in', True, '{name} blew their savings on something shiny'),
    'temper': ('has a short fuse', False, '{name} lost their temper with the wrong person'),
    'gossip': ('can\'t keep a secret', False, '{name} let something slip that wasn\'t theirs to tell'),
    'stubborn': ('stubborn to a fault', False, '{name} refused to change course when they should have'),
    'doubter': ('doubts themselves constantly', True, '{name} talked themselves out of it again'),
    'pleaser': ('can\'t say no to anyone', True, '{name} spent the week doing favors for everyone else'),
    'jealous': ('gets jealous easily', False, '{name} fell out with a friend over nothing much'),
    'scattered': ('forgetful and scattered', True, '{name} forgot something important'),
    'grudge': ('holds a grudge forever', False, '{name} let an old grudge get in the way'),
    'reckless': ('acts first and thinks later', False, '{name} jumped in without thinking and it backfired'),
}
DESIRES = {
    'respect': 'to be taken seriously', 'quiet': 'a quiet, settled life', 'company': 'someone to come home to',
    'adventure': 'a little adventure before it\'s too late', 'recognition': 'to be recognized for what they do',
    'needed': 'to be needed', 'security': 'never to worry about money again', 'belonging': 'to belong somewhere',
    'escape': 'to get out of this city someday', 'family': 'to make their family proud',
}
# Goals: id, wording (modern, period), steps to reach it, where they practise (place kind, part of day) or
# None, progress line, done line. Lines start with the person's given name.
GOALS = (
    ('own-place', ('save up to open a place of their own', 'save enough to open a shop of their own'), 6, None,
     '{name} put another chunk of pay into the savings', '{name} finally signed for a little place of their own'),
    ('race', ('run their first marathon', 'walk the long road to the coast and back'), 5, ('park', 'morning'),
     '{name} went further than ever on a long morning run', '{name} made it the whole way and has the blisters to prove it'),
    ('band', ('get their band a real gig', 'get their troupe a proper engagement'), 5, ('venue', 'evening'),
     '{name}\'s band finally sounded tight at practice', '{name}\'s band played its first real show'),
    ('exam', ('pass a licensing exam', 'earn their guild papers'), 4, ('library', 'evening'),
     '{name} got through another chapter of study', '{name} passed, and can\'t stop grinning about it'),
    ('novel', ('finish writing a novel', 'finish the book they have been writing for years'), 7, ('cafe', 'morning'),
     '{name} wrote another chapter', '{name} typed the last line of their novel'),
    ('reconcile', ('patch things up with an estranged sibling', 'make peace with a brother or sister they fell out '
     'with'), 4, None, '{name} sent their sibling a message and got an answer', '{name} and their sibling are speaking again'),
    ('move', ('save enough to move somewhere bigger', 'save enough to take better rooms'), 5, None,
     '{name} went to see a place they might be able to afford', '{name} moved into a bigger place'),
    ('language', ('learn a new language before a big trip', 'learn a foreign tongue'), 5, ('library', 'afternoon'),
     '{name} got through a whole conversation in their new language', '{name} can finally hold their own in it'),
    ('promotion', ('get promoted', 'be made head of the place they work'), 5, None,
     '{name} got trusted with something bigger at work', '{name} got the promotion'),
    ('art', ('get their paintings into a show', 'get their pictures hung in a proper gallery'), 5, ('park', 'afternoon'),
     '{name} finished a painting they are actually proud of', '{name} has their work hanging in a show'),
    ('dog', ('adopt a dog', 'take in a dog of their own'), 3, None,
     '{name} visited the shelter again and has a favorite', '{name} adopted a scruffy dog'),
    ('strong', ('get properly strong', 'win the strongman contest at the fair'), 5, ('gym', 'evening'),
     '{name} hit a new personal best', '{name} did it, and won\'t stop talking about it'),
    ('side', ('get a side business off the ground', 'build up a little trade on the side'), 6, None,
     '{name} landed another paying customer on the side', '{name}\'s side business is paying its own way now'),
)
GOAL_KINDS = {'park': ('park', 'garden', 'trail'), 'venue': ('venue', 'tavern', 'nightlife'),
              'library': ('library',), 'cafe': ('cafe',), 'gym': ('fitness',)}
COMPANY_SPOTS = ('bar', 'tavern', 'nightlife')
BASE_PROGRESS = 0.4
SETBACK = 0.88
DRAG = 0.15


# Who they are ------------------------------------------------------------------------------------

def modern(data: dict) -> bool:
    return data.get('era', 'modern') in MODERN


def at_place(data: dict, place_id: str) -> list[dict]:
    """Everyone seeded at this place, the same every time for the same city, but for the townsperson the user became
    in this world (`data['you']`, companion/worlds.py)."""
    place = catalog.find(data, place_id)
    if not place or place not in data['places']:
        return []
    found = [person(data, place, index) for index in range(count(data, place))]
    return [sheet for sheet in found if sheet['key'] != data.get('you')] if data.get('you') else found


def seed_for(data: dict, key: str) -> str:
    """What a person is drawn from: their key, mixed with the companion's own town (`data['town']`, set by
    companion/life/network.py) so two companions in one city meet different people. Companions from before
    towns were their own have none and keep the people they already knew."""
    return f"{key}|{data['town']}" if data.get('town') else key


def drawn(sheet: dict) -> str:
    return sheet.get('seed', sheet['key'])


def count(data: dict, place: dict) -> int:
    seed = seed_for(data, f"town:{data['id']}:{place['id']}")
    return PEOPLE[0] + int(generators.unit(seed, 'count') * (PEOPLE[1] - PEOPLE[0] + 1))


def find(data: dict, key: str) -> dict | None:
    """The person a key names in this city, or None."""
    parts = key.split(':')
    if len(parts) != 4 or parts[0] != 'town' or parts[1] != data['id'] or not parts[3].isdigit():
        return None
    if parts[2].startswith('~'):
        hood_id, index = parts[2][1:], int(parts[3])
        if not any(hood['id'] == hood_id for hood in data['neighborhoods']) or \
                index >= resident_count(data, hood_id) + APP_MEMBERS:
            return None
        return resident(data, hood_id, index)
    place = catalog.find(data, parts[2])
    index = int(parts[3])
    if not place or place not in data['places'] or index >= count(data, place):
        return None
    return person(data, place, index)


@generators.detached
def person(data: dict, place: dict, index: int) -> dict:
    return _build(data, place['id'], index)


def _build(data: dict, place_id: str, index: int) -> dict:
    place = catalog.find(data, place_id)
    key = f"town:{data['id']}:{place['id']}:{index}"
    seed = seed_for(data, key)
    roles = ROLES.get(place['kind'], (REGULAR,))
    # The first person at a staffed place runs it day to day; the second is another role there or a regular,
    # the rest are regulars or anyone else the place draws.
    staffed = [role for role in roles if role[2]]
    others = [role for role in roles if not staffed or role != staffed[0]] or list(roles)
    if index == 0 and staffed:
        role = staffed[0]
    elif index == 1:
        role = generators.pick(seed, 'role', others)
    else:
        role = generators.pick(seed, 'role', [role for role in others if not role[2]] or others)
    title = role[0] if modern(data) else role[1]
    age = 19 + round((generators.unit(seed, 'age-a') + generators.unit(seed, 'age-b')) / 2 * 52)
    name = generators.name(data, seed=seed, age=age)
    hoods = [place['neighborhood']] + [hood['id'] for hood in catalog.nearby(data, place['neighborhood'], 3)]
    order = sorted(GOALS, key=lambda goal: generators.unit(seed, 'goal', goal[0]))
    sheet = {
        'key': key, 'seed': seed, 'name': name['given'], 'full': name['full'], 'pronouns': name['pronouns'], 'age': age,
        'heritage': name['culture'] or name['group'],
        'role': title, 'kind': 'staff' if role[2] else 'regular', 'staff': role[2], 'place': {'id': place['id'], 'name': place['name'], 'kind': place['kind'],
                                                   'neighborhood': place['neighborhood']},
        'home': generators.pick(seed, 'home', hoods, [3, 1, 1, 1][:len(hoods)]),
        'occupation': title if role[2] else _occupation(data, seed, age),
        'temperament': generators.pick(seed, 'temperament', sorted(TEMPERAMENTS)),
        'quirk': generators.pick(seed, 'quirk', list(QUIRKS)),
        'flaw': generators.pick(seed, 'flaw', sorted(FLAWS)),
        'desire': generators.pick(seed, 'desire', sorted(DESIRES)),
        'goals': [goal[0] for goal in order],
        'night_owl': generators.unit(seed, 'owl') < 0.25,
    }
    parts = place.get('day_parts') or ['afternoon']
    if role[2]:
        off = sorted(generators.pick(seed, f'off-{n}', list(range(7))) for n in range(2))
        part = generators.pick(seed, 'shift', parts)
        sheet['shifts'] = {'days': [day for day in range(7) if day not in off] or [0, 1, 2], 'part': part,
                           'window': list(SHIFTS[part])}
    else:
        days = sorted({generators.pick(seed, f'visit-{n}', list(range(7))) for n in range(3)})
        part = generators.pick(seed, 'visit', parts)
        sheet['visits'] = {'days': days, 'part': part, 'window': list(VISITS[part])}
    return sheet


def _occupation(data: dict, key: str, age: int) -> str:
    if age >= generators.RETIRED_AT:
        return 'retired'
    # Picked from every career of the era first, so leaving one out of a city (a surf instructor in
    # Baltimore) moves only the residents who had it, not everyone after it in the list.
    offered = {career['name'] for career in catalog.careers_for(data).values()}
    options = sorted(career['name'] for career in catalog.careers_for(data, needs_met=False).values())
    chosen = generators.pick(key, 'career', options)
    if chosen not in offered:
        chosen = generators.pick(key, 'career-here', sorted(offered))
    return chosen.lower() if chosen else ''


def goal(sheet: dict, data_or_modern, number: int) -> dict:
    """Their `number`th goal (0 is the first), with its wording for the era."""
    is_modern = data_or_modern if isinstance(data_or_modern, bool) else modern(data_or_modern)
    found = {item[0]: item for item in GOALS}[sheet['goals'][number % len(sheet['goals'])]]
    goal_id, wording, steps, practice, progress, done = found
    return {'id': goal_id, 'text': wording[0] if is_modern else wording[1], 'steps': steps, 'practice': practice,
            'progress': progress.format(name=sheet['name']), 'done': done.format(name=sheet['name'])}


# How their goal goes, week by week -------------------------------------------------------------------

def week_of(day: date) -> int:
    return (day - EPOCH).days // 7


@functools.lru_cache(maxsize=2048)
def _weeks(key: str, temperament: str, flaw: str, weeks: int, steps_key: tuple) -> tuple:
    """Each week's (goal number, progress, beat) from the epoch through `weeks`."""
    lift = TEMPERAMENTS[temperament][2] - (DRAG if FLAWS[flaw][1] else 0.0)
    number, progress, result = 0, 0, []
    for week in range(weeks + 1):
        roll = generators.unit(key, 'week', week)
        steps = steps_key[number % len(steps_key)]
        if roll < BASE_PROGRESS + lift:
            progress, beat = progress + 1, 'progress'
        elif roll >= SETBACK:
            progress, beat = max(0, progress - 1), 'setback'
        else:
            beat = 'stall'
        if progress >= steps:
            result.append((number, steps, 'achieved'))
            number, progress = number + 1, 0
            continue
        result.append((number, progress, beat))
    return tuple(result)


def story(sheet: dict, data: dict, day: date) -> dict:
    """Where their goals stand on `day`: the current goal, progress, this week's beat and goals reached."""
    weeks = min(max(week_of(day), 0), MAX_WEEKS)
    steps = tuple({item[0]: item[2] for item in GOALS}[goal_id] for goal_id in sheet['goals'])
    history = _weeks(drawn(sheet), sheet['temperament'], sheet['flaw'], weeks, steps)
    number, progress, beat = history[-1] if week_of(day) >= 0 else (0, 0, 'stall')
    reached = [goal(sheet, data, n)['text'] for n in range(number)][-3:]
    if beat == 'achieved':
        finished = goal(sheet, data, number)
        return {'goal': goal(sheet, data, number + 1), 'progress': 0, 'beat': 'achieved', 'line': finished['done'],
                'reached': [*reached, finished['text']][-3:]}
    current = goal(sheet, data, number)
    line = current['progress'] if beat == 'progress' else \
        FLAWS[sheet['flaw']][2].format(name=sheet['name']) if beat == 'setback' else ''
    return {'goal': current, 'progress': progress, 'beat': beat, 'line': line, 'reached': reached}


# Where they are, by rule ---------------------------------------------------------------------------

def part_of_day(minute: int) -> str:
    hour = minute // 60
    return next((part for part, start, end in PARTS if start <= hour < end), 'late')


def inside(window, minute: int) -> bool:
    return window[0] <= minute < window[1]


def asleep(sheet: dict, minute: int) -> bool:
    bed, wake = (60, 9 * 60) if sheet['night_owl'] else (23 * 60, 6 * 60 + 30)
    return minute >= bed or minute < wake if bed > wake else bed <= minute < wake


def spot_near(data: dict, sheet: dict, kinds) -> dict | None:
    hood = sheet['home']
    near = [hood] + [item['id'] for item in catalog.nearby(data, hood, 3)]
    for place in data['places']:
        if place['kind'] in kinds and place['neighborhood'] in near:
            return place
    return None


def whereabouts(sheet: dict, data: dict, moment: datetime) -> dict:
    """Where they are and what they are doing at a local moment, decided by plain rules in order."""
    if sheet.get('kind') == 'resident':
        return resident_whereabouts(sheet, data, moment)
    minute, weekday, day = moment.hour * 60 + moment.minute, moment.weekday(), moment.date()
    here = {'place': sheet['place'], 'at_place': True}
    home = {'place': None, 'at_place': False, 'neighborhood': sheet['home']}
    shifts, visits = sheet.get('shifts'), sheet.get('visits')
    state = story(sheet, data, day)
    mood = mood_for(sheet, state)
    # 1. On shift: they are at work, whatever else they would rather do.
    if shifts and weekday in shifts['days'] and inside(shifts['window'], minute):
        busy = 'run off their feet' if part_of_day(minute) in ('evening',) and weekday >= 4 else 'working'
        return {**here, 'doing': f"{busy} as the {sheet['role']}", 'mood': mood}
    # 2. Asleep.
    if asleep(sheet, minute):
        return {**home, 'doing': 'asleep', 'mood': mood}
    # 3. A regular's usual visit.
    if visits and weekday in visits['days'] and inside(visits['window'], minute):
        return {**here, 'doing': f"at their usual spot at {sheet['place']['name']}", 'mood': mood}
    # 4. Working toward their goal, where it takes them.
    practice = state['goal']['practice']
    if practice and part_of_day(minute) == practice[1] and generators.unit(drawn(sheet), 'practice', day) < 0.5:
        spot = spot_near(data, sheet, GOAL_KINDS[practice[0]])
        if spot:
            return {'place': view(spot), 'at_place': spot['id'] == sheet['place']['id'],
                    'doing': f"working on their goal: {state['goal']['text']}", 'mood': mood}
    # 5. Lonely on a weekend evening: out where people are.
    if sheet['desire'] == 'company' and weekday >= 4 and part_of_day(minute) in ('evening', 'late'):
        spot = spot_near(data, sheet, COMPANY_SPOTS)
        if spot:
            return {'place': view(spot), 'at_place': spot['id'] == sheet['place']['id'],
                    'doing': 'out, hoping to meet someone', 'mood': mood}
    # 6. Otherwise at home, or out at work if they have a job somewhere else.
    if not sheet['staff'] and sheet['occupation'] not in ('', 'retired') and weekday < 5 \
            and 9 * 60 <= minute < 17 * 60:
        return {**home, 'doing': f"at work ({sheet['occupation']})", 'mood': mood}
    return {**home, 'doing': 'at home', 'mood': mood}


def view(place: dict) -> dict:
    return {'id': place['id'], 'name': place['name'], 'kind': place['kind'], 'neighborhood': place['neighborhood']}


def mood_for(sheet: dict, state: dict) -> str:
    if state['beat'] == 'achieved':
        return 'over the moon'
    if state['beat'] == 'setback':
        return 'frustrated' if sheet['flaw'] in ('temper', 'stubborn', 'proud') else 'down'
    if state['beat'] == 'progress':
        return 'upbeat'
    return TEMPERAMENTS[sheet['temperament']][0]


def present(data: dict, place_id: str, moment: datetime) -> list[dict]:
    """The people seeded at a place who are there at this local moment."""
    return [sheet for sheet in at_place(data, place_id) if whereabouts(sheet, data, moment)['at_place']]


def first_impression(sheet: dict) -> str:
    return TEMPERAMENTS[sheet['temperament']][1]


def neighborhood_name(data: dict, hood_id: str) -> str:
    return next((hood['name'] for hood in data['neighborhoods'] if hood['id'] == hood_id), '')


def window_text(window) -> str:
    def clock(minute):
        return f'{minute // 60 % 24:02d}:{minute % 60:02d}'
    return f'{clock(window[0])}–{clock(window[1])}'


DAY_NAMES = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')


def routine_text(sheet: dict) -> str:
    plan = sheet.get('shifts') or sheet.get('visits')
    days = ', '.join(DAY_NAMES[day] for day in plan['days'])
    if sheet.get('kind') == 'resident':
        visits = f"drops in at {sheet['place']['name']} {days}, {window_text(plan['window'])}"
        commute = sheet.get('commute')
        if not commute:
            return visits
        leaves = window_text((commute['leave'], commute['leave']))[:5]
        return f"heads out to work around {leaves} on weekdays; {visits}"
    verb = 'works' if sheet.get('shifts') else 'drops in'
    return f"{verb} {days}, {window_text(plan['window'])}"


# Ordinary residents -------------------------------------------------------------------------------
#
# Every neighborhood also has its own residents: neighbors, commuters at the stop, people walking the
# dog. Like the people at places they are rebuilt from a key (`town:<city>:~<neighborhood>:<n>`) and
# never stored. Their rules: asleep, waiting at the stop on the way to work, at work, walking home, a
# regular stop at a nearby spot, working on their goal, out looking for company, the weekly shop, out
# front on a fine evening, else at home. A resident only ever goes to the few places in their `reach`,
# so finding who is at a place looks at the residents of the neighborhoods around it, not the whole city.

RESIDENTS = (40, 80)
# People living in each neighborhood beyond the residents the town simulates, who only turn up on the dating
# app (companion/world/dating.py): a city has far more singles than the few dozen neighbors anyone runs into.
# They take the indexes after the residents', so they are rebuilt from a key like any resident.
APP_MEMBERS = 500
HAUNT_KINDS = ('cafe', 'bar', 'tavern', 'restaurant', 'park', 'library', 'fitness', 'market', 'garden', 'square')
# When people leave for work (earliest, latest) and how long they are out, by the career's schedule.
COMMUTES = {'early': ((4 * 60 + 30, 6 * 60), 8 * 60 + 30), 'evening': ((15 * 60, 16 * 60 + 30), 9 * 60),
            'shift-night': ((18 * 60, 19 * 60 + 30), 12 * 60)}
COMMUTE = ((7 * 60, 8 * 60 + 45), 9 * 60 + 30)
STREET_EVENING = (17 * 60 + 30, 20 * 60)


def street(data: dict, hood_id: str) -> dict:
    """A neighborhood's streets as a place: where neighbors run into each other."""
    return {'id': f'~{hood_id}', 'name': neighborhood_name(data, hood_id), 'kind': 'street', 'neighborhood': hood_id}


def resident_count(data: dict, hood_id: str) -> int:
    return RESIDENTS[0] + int(generators.unit(seed_for(data, f"town:{data['id']}:~{hood_id}"), 'count') * (RESIDENTS[1] - RESIDENTS[0] + 1))


def area(data: dict, hood_id: str) -> dict:
    """What residents of one neighborhood have within reach: everyday spots, goal spots and the stop."""
    near = [hood_id] + [hood['id'] for hood in catalog.nearby(data, hood_id, 3)]
    local = [place for place in data['places'] if place['neighborhood'] in near]
    haunts = [place for place in local if place['kind'] in HAUNT_KINDS and place.get('cost', '$') in ('free', '$', '$$')]
    spots = {key: [view(place) for place in local if place['kind'] in kinds] for key, kinds in GOAL_KINDS.items()}
    spots['company'] = [view(place) for place in local if place['kind'] in COMPANY_SPOTS]
    spots['market'] = [view(place) for place in local if place['kind'] == 'market']
    hood = catalog.neighborhood(data, hood_id)
    lines = {item['id']: item['name'] for item in data.get('transit', [])}
    stops = [lines[item] for item in hood.get('transit', []) if item in lines]
    return {'near': near, 'haunts': haunts or local[:3], 'spots': spots, 'stops': stops}


def residents(data: dict, hood_id: str, named: bool = True) -> list[dict]:
    """A neighborhood's residents; `named=False` skips their names, for quickly checking where they are."""
    where = area(data, hood_id)
    return [resident(data, hood_id, index, where, named) for index in range(resident_count(data, hood_id))]


def resident(data: dict, hood_id: str, index: int, where: dict | None = None, named: bool = True,
             key: str = '') -> dict:
    """A resident by their place in the neighborhood; `key` seeds someone else living there instead (a companion
    who stepped back, companion/life/encounters.py)."""
    where = where or area(data, hood_id)
    key = key or f"town:{data['id']}:~{hood_id}:{index}"
    seed = seed_for(data, key)
    age = 18 + round((generators.unit(seed, 'age-a') + generators.unit(seed, 'age-b')) / 2 * 66)
    occupation = _occupation(data, seed, age)
    haunt = generators.pick(seed, 'haunt', where['haunts']) if where['haunts'] else None
    place = view(haunt) if haunt else street(data, hood_id)
    order = sorted(GOALS, key=lambda goal: generators.unit(seed, 'goal', goal[0]))
    sheet = {
        'key': key, 'seed': seed, 'name': '', 'full': '', 'pronouns': '', 'age': age, 'kind': 'resident',
        'role': occupation or 'local', 'staff': False, 'place': place, 'home': hood_id, 'occupation': occupation,
        'street': street(data, hood_id),
        'spots': {kind: generators.pick(seed, f'spot-{kind}', options) for kind, options in where['spots'].items()},
        'temperament': generators.pick(seed, 'temperament', sorted(TEMPERAMENTS)),
        'quirk': generators.pick(seed, 'quirk', list(QUIRKS)),
        'flaw': generators.pick(seed, 'flaw', sorted(FLAWS)),
        'desire': generators.pick(seed, 'desire', sorted(DESIRES)),
        'goals': [goal[0] for goal in order],
        'night_owl': generators.unit(seed, 'owl') < 0.2,
        'errand_day': int(generators.unit(seed, 'errand') * 7),
    }
    parts = (haunt or {}).get('day_parts') or ['afternoon']
    part = generators.pick(seed, 'visit', parts)
    working = occupation not in ('', 'retired')
    # Someone with a weekday job drops in on weekends, unless their spot is an evening one.
    days = [5, 6] if working and part in ('morning', 'afternoon') else list(range(7))
    sheet['visits'] = {'days': sorted({generators.pick(seed, f'visit-{n}', days) for n in range(2)}), 'part': part,
                       'window': list(VISITS[part])}
    if working:
        schedule = next((career['schedule'] for career in catalog.careers_for(data).values()
                         if career['name'].lower() == occupation), 'office')
        (earliest, latest), hours = COMMUTES.get(schedule, COMMUTE)
        leave = earliest + round(generators.unit(seed, 'leave') * (latest - earliest) / 15) * 15
        stop = generators.pick(seed, 'stop', where['stops']) if where['stops'] else None
        sheet['commute'] = {'days': [0, 1, 2, 3, 4], 'leave': leave, 'back': min(leave + hours, 24 * 60 - 20),
                            'stop': stop}
    sheet['reach'] = sorted({place['id'], sheet['street']['id'],
                             *(spot['id'] for spot in sheet['spots'].values() if spot)})
    if named:
        name = generators.name(data, seed=seed, age=age)
        sheet |= {'name': name['given'], 'full': name['full'], 'pronouns': name['pronouns'], 'heritage': name['culture'] or name['group']}
    return sheet


def reaching(data: dict, place_id: str) -> list[dict]:
    """Unnamed residents who might be at this place (or, for '~<neighborhood>', on its streets)."""
    if place_id.startswith('~'):
        hood_id = place_id[1:]
        return residents(data, hood_id, named=False) if any(h['id'] == hood_id for h in data['neighborhoods']) else []
    place = catalog.find(data, place_id)
    if not place or place not in data['places']:
        return []
    hoods = [place['neighborhood']] + [hood['id'] for hood in catalog.nearby(data, place['neighborhood'], 3)]
    return [sheet for hood_id in hoods for sheet in residents(data, hood_id, named=False) if place_id in sheet['reach']]


def working(sheet: dict, minute: int, weekday: int) -> str | None:
    """On a workday: what they are doing on their street on the way out or back, 'away' while at work, else None."""
    commute = sheet.get('commute')
    if not commute or weekday not in commute['days']:
        return None
    if commute['leave'] - 20 <= minute < commute['leave']:
        return f"waiting for the {commute['stop']}" if commute['stop'] else 'heading out to work'
    if commute['leave'] <= minute < commute['back']:
        return 'away'
    if commute['back'] <= minute < commute['back'] + 20:
        return 'walking home from work'
    return None


def resident_whereabouts(sheet: dict, data: dict, moment: datetime) -> dict:
    """A resident's rules, in order."""
    minute, weekday, day = moment.hour * 60 + moment.minute, moment.weekday(), moment.date()
    state = story(sheet, data, day)
    mood = mood_for(sheet, state)

    def at(place, doing):
        return {'place': place, 'at_place': place['id'] == sheet['place']['id'], 'doing': doing, 'mood': mood}

    home = {'place': None, 'at_place': False, 'neighborhood': sheet['home'], 'mood': mood}
    # 1. Asleep.
    if asleep(sheet, minute):
        return {**home, 'doing': 'asleep'}
    # 2. On the way to work, at work, on the way home.
    workday = working(sheet, minute, weekday)
    if workday == 'away':
        return {**home, 'doing': f"at work ({sheet['occupation']})"}
    if workday:
        return at(sheet['street'], workday)
    # 3. Their usual spot.
    visits = sheet['visits']
    if weekday in visits['days'] and inside(visits['window'], minute):
        return at(sheet['place'], f"at their usual spot at {sheet['place']['name']}")
    # 4. Their goal, where it takes them.
    practice = state['goal']['practice']
    spot = sheet['spots'].get(practice[0]) if practice else None
    if spot and part_of_day(minute) == practice[1] and generators.unit(drawn(sheet), 'practice', day) < 0.5:
        return at(spot, f"working on their goal: {state['goal']['text']}")
    # 5. Lonely on a weekend evening.
    spot = sheet['spots'].get('company')
    if spot and sheet['desire'] == 'company' and weekday >= 4 and part_of_day(minute) in ('evening', 'late'):
        return at(spot, 'out, hoping to meet someone')
    # 6. The weekly shop.
    spot = sheet['spots'].get('market')
    if spot and weekday == sheet['errand_day'] and 10 * 60 <= minute < 12 * 60:
        return at(spot, 'doing the weekly shop')
    # 7. Out front on an evening, else at home.
    if inside(STREET_EVENING, minute) and generators.unit(drawn(sheet), 'out front', day) < 0.3:
        doing = 'walking the dog' if 'dog' in sheet['quirk'] else 'out front, chatting with whoever passes'
        return at(sheet['street'], doing)
    return {**home, 'doing': 'at home'}

