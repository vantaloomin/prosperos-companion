"""Trips and postcards (Hit List #12): now and then the companion gets out of town for a weekend.

Rules decide, seeded by the weekend, with no model. Two to three weeks ahead the app looks at each coming weekend:
a long weekend (a public holiday on the Friday or Monday) is likelier, there is a gap of several weeks between
trips, work or classes on those days rule it out, and it has to fit their budget this pay period. Where they go is
another city the app ships in the same era (a real city from a real one), within reach for the days they have and
leaning toward what they are interested in, or the city a relative who lives out of town is in. A city's
`neighbours` (companion/world/ships.py) are in reach by their journey time, and a ship or station goes only to those,
by shuttle. They go alone, with someone from their circle, or to stay with that relative.

The destination's city pack fills the days: in the companion's agenda (companion/life/agenda.py) each waking slot of
a trip day is spent at a real place there, with a landmark or two among them, the first slot is setting off and the
last is heading home, which can leave them tired or, after a sunny beach weekend, sunburnt (companion/life/body.py).
The trip's cost comes out of their budget on the day they leave (money.household). Their texts are a little slower
while they are away (their blocks are out-and-about time, companion/life/pacing.py) and their status says where they
are. On the first afternoon they send the user a postcard: a first text (companion/life/openers.py) with a picture
postcard of the landmark when pictures in chat are on.

Weekend visits with the user when they live in different cities (companion/life/long_distance.py) are trips too: a
row with `visit` set, 'to-you' when the companion comes to stay with the user, 'host' when the user comes to stay with
them. Their days are written here the same way, spent with the user, and the user can call one off before it starts.
"""
import re
from datetime import date, datetime, timedelta

from companion.clock import zone
from companion.database import decode, encode, identifier, many, optional
from companion.life import money, routine
from companion.world import catalog, generators, ships

# Off in tests unless a test turns it on, so other tests' agendas stay as they were.
ACTIVE = True
# Weekends whose Saturday falls this many days ahead are decided (after the agenda's week, so a trip is always in
# place before the days it covers are written).
AHEAD = (8, 22)
GAP_DAYS = 42
CHANCE = 0.12
LONG_CHANCE = 0.45
FAMILY_SHARE = 0.5
ALONE_SHARE = 0.4
# How far they go for two nights or three, and what that costs as a share of a month's take-home.
REACH_KM = {2: 1200, 3: 2500}
COST_SHARE = {2: 0.12, 3: 0.17}
SIGHTS = ('landmark', 'attraction')
BY_PART = {'morning': ('attraction', 'museum', 'park', 'market'),
           'afternoon': ('attraction', 'waterfront', 'beach', 'museum', 'park', 'shop'),
           'evening': ('restaurant', 'bar'), 'late': ('bar', 'restaurant')}
SUMMARIES = ('{name} spent the {part} at {place} in {city}{company}.',
             '{name} saw {place} in {city}{company} during the {part}.',
             'The {part} in {city} went to {place}{company}.')
# For a place named for what you do there ("Staten Island Ferry ride", "Brooklyn Bridge walk"): one line for
# each of SUMMARIES, so the seeded pick lands on the same slot.
OUTING_SUMMARIES = ('{name} took the {place} in {city}{company} during the {part}.',
                    '{name} went on the {place} in {city}{company} during the {part}.',
                    'The {part} in {city} went on the {place}{company}.')
OUTING_NAME = re.compile(r'\b(?:ride|walk|cruise|tour|crossing|hike)$', re.IGNORECASE)
CAPTIONS = ('Wish you were here.', 'Postcard weather.', 'Not ready to go home.', 'Walked about a hundred miles today.',
            'Tourist and proud.', 'Taking it all in.')
POSTCARDS = ('Greetings from {city}! {sight} today. Wish you were here.',
             'Hello from {city}! Saw {sight} and thought of you.',
             'A postcard from {city}, just for you. {sight} was even better in person.')
OUTING_POSTCARDS = ('Greetings from {city}! The {sight} today. Wish you were here.',
                    'Hello from {city}! Took the {sight} and thought of you.',
                    'A postcard from {city}, just for you. The {sight} was even better in person.')
SUNNY_TAGS = {'beach', 'waterfront', 'boardwalk'}
WARM_F = 75
POSTCARD_HOUR = 15
FAMILY = ('mom', 'dad', 'mother', 'father', 'parent', 'sister', 'brother', 'sibling', 'cousin', 'aunt', 'uncle',
          'grand')


def saturdays(today: date) -> list[date]:
    first = today + timedelta(days=AHEAD[0])
    first += timedelta(days=(5 - first.weekday()) % 7)
    return [first + timedelta(days=7 * week) for week in range((AHEAD[1] - AHEAD[0]) // 7 + 1)
            if first + timedelta(days=7 * week) <= today + timedelta(days=AHEAD[1])]


def public_holidays(data: dict, start: date, end: date) -> set[str]:
    return {item['date'] for item in generators.holidays(data, start, end) if item['kind'] == 'public'}


def days_off(data: dict, saturday: date, vacation: set[str] = frozenset()) -> list[date]:
    """The weekend, with the Friday or Monday when it is a public holiday or a vacation day (companion/life/work.py)."""
    holidays = public_holidays(data, saturday - timedelta(days=1), saturday + timedelta(days=2)) | vacation
    friday, monday = saturday - timedelta(days=1), saturday + timedelta(days=2)
    if friday.isoformat() in holidays:
        return [friday, saturday, saturday + timedelta(days=1)]
    if monday.isoformat() in holidays:
        return [saturday, saturday + timedelta(days=1), monday]
    return [saturday, saturday + timedelta(days=1)]


def free(definition: dict, days: list[date], holidays: set[str]) -> bool:
    """No work or classes on these days (a public holiday is a day off)."""
    schedule, _default = routine.blocks(definition)
    return not any(block.on(day) and block.kind in {'work', 'study'} and day.isoformat() not in holidays
                   for day in days for block in schedule)


def fits(home: dict, other: dict) -> bool:
    """Same era and the same world: real cities and towns invented in our world (Haddon Harbor in Maine, Pellmouth)
    mix, as do the cities of a made-up world (Camelot, Oz, Grandport); a user's own city visits real ones. Cities that
    list each other as neighbours always do, and a ship or station only those (companion/world/ships.py)."""
    if other['id'] == home['id']:
        return False
    if ships.linked(home, other):
        return True
    if ships.enclosed(home) or ships.enclosed(other) or other.get('era', 'modern') != home.get('era', 'modern'):
        return False
    if 'lat' not in other or 'lat' not in home or other.get('distribution', 'public') != 'public':
        return False
    mine, theirs = catalog.category(home), catalog.category(other)
    if theirs == 'custom':
        return False
    if mine == 'custom':
        return theirs == 'real'
    return ours(home) == ours(other)


def ours(city: dict) -> bool:
    """A real city, or one invented in our world ('original'), rather than a city of a made-up world."""
    return city.get('setting') in ('real', 'original')


def destinations(home: dict, nights: int, known: dict[str, dict] | None = None) -> list[dict]:
    """Cities a weekend of `nights` nights reaches: others of its world within REACH_KM, and its neighbours (among
    the `known` cities, the built-in ones by default) within their journey time (companion/world/ships.py)."""
    known = known if known is not None else catalog.cities()
    found = {city['id']: city for city in catalog.cities().values() if fits(home, city) and not ships.linked(home, city)
             and catalog.distance_km(home, city) <= REACH_KM[nights]}
    found |= {city['id']: city for city in ships.reachable(home, known, nights)}
    return sorted(found.values(), key=lambda city: city['id'])


def in_reach(home: dict, city: dict, nights: int) -> bool:
    """Whether a weekend of `nights` nights gets from `home` to `city`."""
    return any(item['id'] == city['id'] for item in destinations(home, nights, {city['id']: city}))


def interest_weight(city: dict, definition: dict) -> float:
    """One, plus one for each of their interests the city's places speak to (up to four)."""
    likes = {word for word in re.findall(r'[a-z]+', ' '.join(definition.get('interests') or ()).lower())
             if len(word) > 3}
    if not likes:
        return 1.0
    words = {word for place in city['places'] for word in [*place.get('tags', ()), *re.findall(
        r'[a-z]+', place.get('summary', '').lower())]}
    return 1.0 + min(len(likes & words), 4)


def away_people(connection, timeline_id: str) -> list[dict]:
    """Relatives in the circle who live out of town (they have no routine here)."""
    rows = many(connection, "SELECT id, name, role, schedule FROM circle_people WHERE timeline_id=? AND "
                "status='active' ORDER BY ordinal", (timeline_id,))
    return [row for row in rows if not decode(row['schedule']) and any(word in row['role'].lower() for word in FAMILY)]


def local_people(connection, timeline_id: str) -> list[dict]:
    rows = many(connection, "SELECT id, name, role, schedule FROM circle_people WHERE timeline_id=? AND "
                "status='active' ORDER BY ordinal", (timeline_id,))
    return [row for row in rows if decode(row['schedule'])]


def hometown(person_id: str, home: dict, known: dict[str, dict] | None = None) -> dict | None:
    """The city a relative who lives out of town is in, the same every time."""
    options = destinations(home, 3, known)
    return generators.pick(f'{person_id}:hometown', 'city', options) if options else None


def where(connection, timeline_id: str, home: dict, definition: dict, nights: int, seed: str):
    """(destination, kind, company): a visit to a relative, or a getaway alone or with someone local."""
    from companion.life import circle
    relatives = away_people(connection, timeline_id)
    known = ships.known_cities(connection)
    if relatives and generators.unit(seed, 'family') < FAMILY_SHARE:
        relative = generators.pick(seed, 'relative', relatives)
        city = hometown(relative['id'], home, known)
        if city and in_reach(home, city, nights):
            # As they say it: 'mother' in 1895 (circle.said).
            return city, 'family', {'id': relative['id'], 'name': relative['name'],
                                    'role': circle.said(relative['role'], definition)}
    options = destinations(home, nights, known)
    if not options:
        return None
    city = generators.pick(seed, 'city', options, [interest_weight(item, definition) for item in options])
    people = local_people(connection, timeline_id)
    company = None
    if people and generators.unit(seed, 'alone') >= ALONE_SHARE:
        person = generators.pick(seed, 'company', people)
        company = {'id': person['id'], 'name': person['name'], 'role': circle.said(person['role'], definition)}
    return city, 'getaway', company


def sight(city: dict, seed: str) -> dict | None:
    """The landmark on the postcard: an iconic one when the city has it."""
    options = [place for place in city['places'] if place['kind'] in SIGHTS]
    iconic = [place for place in options if 'iconic' in place.get('tags', ())]
    found = generators.pick(seed, 'sight', iconic or options)
    return found and {'id': found['id'], 'name': found['name'], 'summary': found.get('summary', '')}


def sunny(city: dict, day: date) -> bool:
    """A beach or waterfront city on a warm, dry day."""
    weather = generators.conditions(city, day)
    by_water = any(place['kind'] == 'beach' or set(place.get('tags', ())) & SUNNY_TAGS for place in city['places'])
    return bool(weather) and by_water and weather['high_f'] >= WARM_F and not weather['rain']


def cost(definition: dict, nights: int, day: date, left: float | None = None) -> float | None:
    """What the trip costs, or None when they cannot afford it with what is `left` then (else their bare budget); 0
    where money does not apply."""
    return price(definition, COST_SHARE[nights], day, left)


def price(definition: dict, share: float, day: date, left: float | None = None) -> float | None:
    """`share` of a month's take-home, or None when that is more than is `left` then; 0 where money does not apply."""
    found = money.profile(definition)
    if not found:
        return 0.0
    amount = money.monthly_share(found) * share * (1 if found.period == 'month' else 12 / 52)
    return round(amount, 2) if amount <= (money.left_on(found, day) if left is None else left) else None


def booked(connection, companion: dict, days: list[date]) -> bool:
    """An outing with the user or a family tradition already has one of these days."""
    from companion.life import traditions
    return bool(optional(connection, "SELECT id FROM outings WHERE companion_id=? AND local_date>=? AND local_date<=? "
                         "AND status!='cancelled'", (companion['id'], days[0].isoformat(), days[-1].isoformat()))) or \
        traditions.busy(connection, companion, days[0], days[-1])


def decide(connection, companion: dict, home: dict, saturday: date) -> dict | None:
    """Whether they go away that weekend, and where; the same answer for the same weekend."""
    definition, timeline_id = companion['version']['definition'], companion['active_timeline_id']
    seed = f'trip:{timeline_id}:{saturday.isoformat()}'
    from companion.life import work
    vacation = work.vacation_dates(connection, companion, saturday - timedelta(days=1), saturday + timedelta(days=2))
    days = days_off(home, saturday, vacation)
    holidays = public_holidays(home, days[0], days[-1]) | vacation
    if not free(definition, days, holidays) or booked(connection, companion, days):
        return None
    if generators.unit(seed, 'go') >= (LONG_CHANCE if len(days) == 3 else CHANCE):
        return None
    nights = len(days)
    picked = where(connection, timeline_id, home, definition, nights, seed)
    price = cost(definition, nights, days[0], money.spendable(connection, timeline_id, definition, days[0]))
    if not picked or price is None:
        return None
    city, kind, company = picked
    return {'start_date': days[0].isoformat(), 'end_date': days[-1].isoformat(), 'city_id': city['id'],
            'city_name': city['name'], 'kind': kind, 'company': company, 'landmark': sight(city, seed),
            'sunny': sunny(city, days[1]), 'cost': price}


def too_soon(rows: list[dict], saturday: date) -> bool:
    return any(abs((date.fromisoformat(row['start_date']) - saturday).days) < GAP_DAYS for row in rows)


def plan_ahead(connection, companion: dict, world, now: datetime) -> int:
    """Decide the weekends that just came into view. Cheap: no model."""
    if not ACTIVE:
        return 0
    from companion.life import circle
    home = circle.city_data(companion['version']['definition'], world)
    if not home:
        return 0
    timeline_id = companion['active_timeline_id']
    today = now.astimezone(zone(companion['version']['timezone'])).date()
    from companion.life import long_distance
    far = long_distance.settle_moves(connection, companion, today)
    rows = many(connection, "SELECT start_date FROM trips WHERE timeline_id=? AND status='planned'", (timeline_id,))
    written = 0
    for saturday in saturdays(today):
        # Any trip or visit around that weekend, planned or called off, settles it.
        if optional(connection, 'SELECT id FROM trips WHERE timeline_id=? AND start_date<=? AND end_date>=?',
                    (timeline_id, (saturday + timedelta(days=2)).isoformat(),
                     (saturday - timedelta(days=2)).isoformat())):
            continue
        # Living apart, a weekend visit with the user comes before a trip of their own.
        visit = far and long_distance.decide(connection, companion, home, far, saturday)
        if visit:
            insert(connection, companion, visit, now)
            rows.append(visit)
            written += 1
            continue
        if too_soon(rows, saturday):
            continue
        trip = decide(connection, companion, home, saturday)
        if trip:
            insert(connection, companion, trip, now)
            rows.append(trip)
            written += 1
    return written


def insert(connection, companion: dict, trip: dict, now: datetime) -> str:
    trip_id = identifier()
    connection.execute(
        'INSERT OR IGNORE INTO trips (id, companion_id, timeline_id, start_date, end_date, city_id, city_name, kind, '
        'company, landmark, sunny, cost, visit, message_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?)',
        (trip_id, companion['id'], companion['active_timeline_id'], trip['start_date'], trip['end_date'],
         trip['city_id'], trip['city_name'], trip['kind'], encode(trip['company']), encode(trip['landmark']),
         int(trip['sunny']), trip['cost'], trip.get('visit', ''), trip.get('message_id'), now.isoformat()))
    return trip_id


def view(row: dict) -> dict:
    return {**row, 'company': decode(row['company']) if row['company'] else None,
            'landmark': decode(row['landmark']) if row['landmark'] else None, 'sunny': bool(row['sunny'])}


def planned(connection, timeline_id: str, since: str) -> list[dict]:
    return [view(row) for row in many(connection, "SELECT * FROM trips WHERE timeline_id=? AND status='planned' AND "
                                      'end_date>=? ORDER BY start_date', (timeline_id, since))]


def away_on(connection, companion_id: str, day: date) -> bool:
    return bool(optional(connection, "SELECT trips.id FROM trips JOIN companions ON companions.id=trips.companion_id "
                         "AND companions.active_timeline_id=trips.timeline_id WHERE trips.companion_id=? AND "
                         "trips.status='planned' AND start_date<=? AND end_date>=?",
                         (companion_id, day.isoformat(), day.isoformat())))


def by_date(connection, timeline_id: str, since: str) -> dict[str, dict]:
    """Each local date a planned trip covers, with the trip."""
    result = {}
    for trip in planned(connection, timeline_id, since):
        day = date.fromisoformat(trip['start_date'])
        while day.isoformat() <= trip['end_date']:
            result[day.isoformat()] = trip
            day += timedelta(days=1)
    return result


def repin(connection, timeline_id: str, away: dict[str, dict]) -> int:
    """Remove upcoming companion entries whose trip is not the one now planned for their date (a trip was planned
    or called off), so they are composed again."""
    removed = 0
    for row in many(connection, "SELECT id, local_date, json_extract(block, '$.trip') AS trip FROM life_agenda "
                    "WHERE timeline_id=? AND subject='companion' AND status='upcoming'", (timeline_id,)):
        wanted = (away.get(row['local_date']) or {}).get('id')
        if row['trip'] != wanted and (row['trip'] or wanted):
            connection.execute('DELETE FROM life_agenda WHERE id=?', (row['id'],))
            removed += 1
    return removed


# --- A day away, in the agenda ---

def with_text(trip: dict) -> str:
    company = trip['company']
    if not company:
        return ''
    return f" with {company['name']}" if trip['kind'] == 'getaway' else f", staying with {company['name']}"


def block(view: dict, trip: dict) -> dict:
    """A waking block on a trip day: out and about in the other city. On a weekend visit it is time with the user,
    so replies are not held (companion/life/pacing.py)."""
    if trip.get('visit'):
        return {**view, 'kind': 'social', 'label': f"With you in {trip['city_name']}", 'trip': trip['id'],
                'holiday': None, 'sick_day': False, 'with_user': True}
    return {**view, 'kind': 'social', 'label': f"Away in {trip['city_name']}", 'trip': trip['id'],
            'holiday': None, 'sick_day': False}


def outing_name(name: str) -> str:
    """'Staten Island Ferry ride' for 'took the …': no leading article of its own."""
    return re.sub(r'^the\s+', '', name, flags=re.IGNORECASE)


def travel_by(trip: dict, definition: dict, world) -> str:
    """How they travel on a trip: by shuttle to or from a ship or station, else the neighbour listing's own word, or
    '' for the usual wording (companion/world/ships.py)."""
    find = getattr(world, 'find', None)
    if trip.get('visit') or not find:
        return ''
    from companion.life import circle
    return ships.by(circle.city_data(definition, world), find(trip['city_id']))


# Setting off and heading home by shuttle, or by the way a neighbour listing names ("the night train").
SHUTTLE_LINES = {'first': ('{name} caught the shuttle and docked at {city}{company}.', 'Docking soon!'),
                 'last': ('{name} caught the shuttle home from {city}{company}.', 'Docked and home.')}
BY_LINES = {'first': ('{name} took the {by} to {city}{company}.', None),
            'last': ('{name} took the {by} home from {city}{company}.', None)}


def travel_line(ends: str, by: str, words: dict, post: str) -> tuple[str, str]:
    """(summary, post) for setting off or heading home by `by`; `post` unless the way has its own."""
    summary, own = (SHUTTLE_LINES if by == ships.SHUTTLE else BY_LINES)[ends]
    return summary.format(**words, by=by), own or post


def entry(trip: dict, slot_view: dict, definition: dict, world, seed: str, ends: str | None) -> dict:
    """What a waking slot of a trip day holds: setting off, heading home ('first' or 'last'), or a place there."""
    name, city, company = definition['name'], trip['city_name'], with_text(trip)
    by = travel_by(trip, definition, world) if ends else ''
    common = {'mood': 'happy', 'with': None, 'trip': {'id': trip['id'], 'city': city, 'city_id': trip['city_id']},
              'composer_version': 'trip-1',
              'weather': (getattr(world, 'weather', None) or (lambda *_args: None))(
                  trip['city_id'], date.fromisoformat(slot_view['local_date']))}
    if ends == 'first':
        summary = {'to-you': f'{name} set off to see you in {city}.', 'host': f'{name} welcomed you to {city}.'}.get(
            trip.get('visit'), f'{name} set off for {city}{company}.')
        post = f'Off to {city}!' if trip.get('visit') != 'host' else 'Best kind of weekend.'
        if by:
            summary, post = travel_line('first', by, {'name': name, 'city': city, 'company': company}, post)
        return {**common, 'summary': summary, 'post': post, 'activity': 'trip-travel', 'place': None,
                'mood': 'excited'}
    if ends == 'last':
        summary = {'to-you': f'{name} said goodbye to you and headed home from {city}.',
                   'host': f'{name} saw you off home from {city}.'}.get(trip.get('visit'),
                                                                        f'{name} headed home from {city}{company}.')
        post = 'Home again.' if trip.get('visit') != 'host' else 'Already miss it.'
        if by:
            summary, post = travel_line('last', by, {'name': name, 'city': city, 'company': company}, post)
        return {**common, 'summary': summary, 'post': post,
                'activity': 'trip-home-sun' if trip['sunny'] else 'trip-home', 'place': None, 'mood': 'content'}
    from companion.life import composer
    part = composer.day_part(slot_view['block']['start'])
    places = world.places(trip['city_id'], BY_PART[part], day_part=part, day=date.fromisoformat(slot_view['local_date']))
    sights = [place for place in places if place.kind in {'attraction', 'museum'}]
    place = generators.pick(seed, 'trip-place', sights or places) if part in ('morning', 'afternoon') else \
        generators.pick(seed, 'trip-place', places)
    outing = bool(place) and bool(OUTING_NAME.search(place.name))
    words = {'name': name, 'part': part if part != 'late' else 'night', 'city': city, 'company': company,
             'place': outing_name(place.name) if outing else place.name if place else 'the sights'}
    summary = generators.pick(seed, 'trip-summary', list(OUTING_SUMMARIES if outing else SUMMARIES)).format(**words)
    return {**common, 'summary': summary[0].upper() + summary[1:],
            'post': generators.pick(seed, 'trip-post', list(CAPTIONS)), 'activity': 'trip',
            'place': place.view() if place else None}


def ends(schedule, day: date, trip: dict, block_key: str) -> str | None:
    """'first' for the first waking block of the first day, 'last' for the last of the last day."""
    keys = [block.key for block in schedule if block.on(day) and block.kind not in routine.RESTING]
    if not keys:
        return None
    if day.isoformat() == trip['start_date'] and block_key == keys[0]:
        return 'first'
    return 'last' if day.isoformat() == trip['end_date'] and block_key == keys[-1] else None


# --- What the companion knows, and the budget ---

def day_text(value: str) -> str:
    return date.fromisoformat(value).strftime('%A %B %d').replace(' 0', ' ')


def company_text(trip: dict) -> str:
    company = trip['company']
    if not company:
        return ' on your own'
    return f" with {company['name']} ({company['role']})" if trip['kind'] == 'getaway' else \
        f" to see {company['name']} ({company['role']}), staying with them"


def context_lines(connection, companion: dict, now: datetime) -> list[tuple[str, str]]:
    """(identity, line) for a trip coming up in the next two weeks, under way, or just over."""
    today = now.astimezone(zone(companion['version']['timezone'])).date()
    result = []
    for trip in planned(connection, companion['active_timeline_id'], (today - timedelta(days=2)).isoformat()):
        if trip['visit']:
            continue  # Weekend visits with the user say their own lines (companion/life/long_distance.py).
        start, end = date.fromisoformat(trip['start_date']), date.fromisoformat(trip['end_date'])
        span = f"{day_text(trip['start_date'])} to {day_text(trip['end_date'])}"
        if start <= today <= end:
            line = f"- Right now you are away in {trip['city_name']}{company_text(trip)}, until {end:%A}; you head " \
                   'home on the last day.'
        elif today < start <= today + timedelta(days=14):
            line = f"- {span}: a trip to {trip['city_name']}{company_text(trip)}. It is booked."
        elif end < today:
            line = f"- You just got back from {trip['city_name']} ({span})."
        else:
            continue
        result.append((f"trip:{trip['id']}", line))
        if care := care_text(pet_care(connection, companion['active_timeline_id'], trip, start, ahead=today < start)):
            result.append((f"trip:{trip['id']}:pets", f'- While you are away: {care}.'))
    return result


def pet_care(connection, timeline_id: str, trip: dict, day: date, ahead=False) -> list[dict]:
    """Who looks after each of the companion's pets on this trip (companion/life/pets.py `minder`): {pet, how,
    who, text}, worded for a trip still to come when `ahead`. Someone travelling with them can't, so they are left
    out."""
    from companion.life import pets
    company = (trip.get('company') or {}).get('id')
    local = [person for person in local_people(connection, timeline_id) if person['id'] != company]
    return [{'pet': found['name'], **pets.minder(found, trip, local, ahead)}
            for found in pets.of_home(connection, timeline_id, day)]


def care_text(care: list[dict]) -> str:
    return '; '.join(item['text'] for item in care if item['text'])


def purchases(connection, timeline_id: str, start: date, day: date) -> list[dict]:
    """Trips that set off this pay period, as money.household purchases with their own cost, and a sitter for the
    pets even on a trip that cost nothing itself."""
    rows = many(connection, "SELECT * FROM trips WHERE timeline_id=? AND status='planned' AND start_date>=? AND "
                'start_date<=?', (timeline_id, start.isoformat(), day.isoformat()))
    found = [{'text': "spent a bit extra having you to stay" if row['visit'] == 'host' else
              f"paid for the trip to {row['city_name']}", 'date': row['start_date'], 'spend': '', 'cost': row['cost'],
              'for': 'trip'} for row in rows if row['cost'] > 0]
    for row in rows:
        start_day = date.fromisoformat(row['start_date'])
        found += [{'text': f"paid someone to look after {item['pet']} during the trip", 'date': row['start_date'],
                   'spend': '$$', 'for': 'trip'} for item in pet_care(connection, timeline_id, view(row), start_day)
                  if item['how'] == 'sitter']
    return found


def away_status(connection, block: dict, seed: str) -> dict | None:
    """The status line's away message while on a trip: where they are and when they are back."""
    row = optional(connection, 'SELECT city_id, city_name, end_date, visit FROM trips WHERE id=?',
                   (block.get('trip'),)) if block.get('trip') else None
    if not row or row['visit'] == 'host':
        return None  # Home, with the user staying over.
    city, back = row['city_name'], date.fromisoformat(row['end_date'])
    # A ship or station is reached by shuttle (companion/world/ships.py).
    flown = '🚀' if ships.enclosed(ships.known_cities(connection).get(row['city_id'])) else '✈️'
    lines = (f'in {city} {flown}', f'away in {city} till {back:%A}', f'{city} mode, back {back:%A}')
    return {'text': generators.pick(seed, 'trip-away', list(lines)), 'glyph': 'pin'}


# --- Postcards ---

def postcard_due(connection, companion: dict, now: datetime) -> list:
    """A first text with a postcard on the first afternoon away (companion/life/openers.py)."""
    from companion.life.openers import Trigger
    local = now.astimezone(zone(companion['version']['timezone']))
    if local.hour < POSTCARD_HOUR:
        return []
    today = local.date().isoformat()
    result = []
    for trip in planned(connection, companion['active_timeline_id'], today):
        if not trip['start_date'] <= today <= trip['end_date'] or not trip['landmark']:
            continue
        sight_name, city = trip['landmark']['name'], trip['city_name']
        outing = bool(OUTING_NAME.search(sight_name))
        template = generators.pick(f"postcard:{trip['id']}", 'postcard', list(OUTING_POSTCARDS if outing else POSTCARDS)
                                   ).format(city=city, sight=outing_name(sight_name) if outing else sight_name)
        result.append(Trigger(
            f"postcard:{trip['id']}", 'postcard',
            f"You are away in {city}{company_text(trip)} and you are sending the user a picture postcard of "
            f"{sight_name}. Write the few lines on the back of it: short and warm, like a real postcard.",
            template, (trip['id'],)))
    return result


def unpictured(connection, now: datetime) -> list[dict]:
    """Postcards sent in the last day that have no picture yet."""
    return many(connection, "SELECT openers.message_id, openers.trigger_key, openers.timeline_id FROM openers "
                "LEFT JOIN chat_photos ON chat_photos.message_id=openers.message_id WHERE openers.kind='postcard' AND "
                'chat_photos.message_id IS NULL AND openers.created_at>?',
                ((now - timedelta(days=1)).isoformat(),))


def postcard_inputs(connection, companion: dict, trip: dict, settings: dict) -> dict:
    """A fixed template: a picture postcard of the landmark, nobody in it."""
    from companion.images import prompts
    from companion.lora.appearance import current_for_images
    sight_item, city = trip['landmark'], trip['city_name']
    prompt = (f"A vintage picture postcard of {sight_item['name']} in {city}. {sight_item['summary']} Bright printed "
              f"colours and a white border, with 'Greetings from {city}' in bold retro lettering across the top. "
              'Nobody in focus.')
    return {**prompts.base_inputs(companion, companion['version']['definition'], settings), 'prompt': prompt,
            'framing': 'view', 'captions': [f'A postcard from {city}', sight_item['name'], sight_item['summary']],
            **current_for_images(connection), 'lora': None}


def picture_postcards(database) -> None:
    """With pictures in chat on, the postcard's picture on the postcard text. Called by the image runner each
    tick; a postcard whose picture cannot be made anywhere stays a text."""
    from companion.characters import current
    from companion.images import jobs
    from companion.life import feed
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = current(connection)
        settings = jobs.image_settings(connection)
        found = [row for row in unpictured(connection, now) if companion
                 and row['timeline_id'] == companion['active_timeline_id']]
        if not found or not settings['chat_photos']:
            return
        trip = optional(connection, 'SELECT * FROM trips WHERE id=?', (found[0]['trigger_key'].removeprefix(
            'postcard:'),))
        if not trip or not trip['landmark']:
            return
        trip = view(trip)
        inputs = postcard_inputs(connection, companion, trip, settings)
        post_id = feed.create(connection, trip['timeline_id'], 'event', f"postcard:{trip['id']}", [], now.isoformat(),
                              now.isoformat())
    if not jobs.routable(database, inputs):
        return
    job = jobs.enqueue(database, post_id, 'manual', inputs=inputs)
    with database.connect(write=True) as connection:
        connection.execute('INSERT OR IGNORE INTO chat_photos (message_id, post_id, job_id, kind, event_key, summary, '
                           "unasked, created_at) VALUES (?, ?, ?, 'view', '', ?, 1, ?)",
                           (found[0]['message_id'], post_id, job['id'], f"a postcard from {trip['city_name']}",
                            now.isoformat()))


# --- What Today shows ---

def listing(connection, companion: dict, now: datetime) -> list[dict]:
    """Trips from the last two weeks on, with their state and postcard message, for Today."""
    from companion.life import long_distance
    today = now.astimezone(zone(companion['version']['timezone'])).date()
    rows = many(connection, 'SELECT * FROM trips WHERE timeline_id=? AND end_date>=? ORDER BY start_date',
                (companion['active_timeline_id'], (today - timedelta(days=14)).isoformat()))
    result = []
    under_way = long_distance.visiting(connection, companion, now)
    for row in map(view, rows):
        found = 'cancelled' if row['status'] == 'cancelled' else 'done' if row['end_date'] < today.isoformat() else \
            'now' if row['start_date'] <= today.isoformat() else 'planned'
        if row['visit'] and found == 'now' and not (under_way and under_way['id'] == row['id']):
            # A visit is together from arrival to leaving, not all day (companion/life/long_distance.py).
            found = 'planned' if row['start_date'] >= today.isoformat() else 'done'
        card = optional(connection, "SELECT message_id FROM openers WHERE timeline_id=? AND trigger_key=?",
                        (row['timeline_id'], f"postcard:{row['id']}"))
        found_cost = money.profile(companion['version']['definition'])
        cost_text = money.amount(row['cost'], found_cost.city['currency']) if found_cost and row['cost'] else ''
        result.append({**row, 'state': found, 'postcard_message_id': card['message_id'] if card else None,
                       'cost_text': cost_text, 'undo': long_distance.undoable(row, today, now)})
    return result
