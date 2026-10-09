"""The dating app: the user's profile, the swipe deck of townsfolk, matches, and new companions (docs/dating.md).

Who is on the app, what they are like and whether they like the user back are townsfolk rules
(companion/world/dating.py); this module keeps what the user did: their own profile and the city they are
looking in, who they swiped on, and any dates played out in Story mode. A match can become a companion
through the same path as switching to a townsperson (companion/cast.py), and is then chatted with like any
companion. No companion prompt reads the app itself: a companion never knows who else the user swiped on.

Modern and future cities have a dating app. Older eras have the same thing in period form: a personal
column in the paper (Victorian, steampunk, frontier) or the town matchmaker (medieval and fantasy).
"""
from companion import story, story_people
from companion.characters import current
from companion.database import decode, encode, identifier, many, optional, settings
from companion.errors import DomainError, require
from companion.images import backends
from companion.life import encounters
from companion.world import catalog, dating, townsfolk

# The app's name in modern and future cities: made up, so it is nobody's real app.
APP_NAME = 'Matchlight'
DECK_SIZE = 5
DATE_KINDS = ('cafe', 'restaurant', 'bar', 'tavern', 'nightlife', 'park', 'garden', 'museum', 'venue', 'beach',
              'market', 'landmark', 'attraction', 'square', 'trail', 'inn')
COLUMN_ERAS = ('victorian', 'steampunk', 'frontier')
# What the user sees, by the kind of matchmaking the city's era has.
SURFACES = {
    'app': {'title': APP_NAME, 'noun': 'a dating app', 'like': 'Like', 'pass': 'Pass',
            'matched': "It's a match", 'empty': 'Nobody new around here right now. Try another city.',
            'tagline': 'Meet people around town.', 'get': 'Get', 'getting': 'Installing…'},
    'column': {'title': 'Personal column', 'noun': 'the personal column in the paper', 'like': 'Write to them',
               'pass': 'Turn the page', 'matched': 'A letter came back',
               'empty': 'No new notices in the paper. Try another city.',
               'tagline': 'Lonely hearts, answered in confidence.', 'get': 'Buy the paper',
               'getting': 'Fetching the paper…'},
    'matchmaker': {'title': 'The matchmaker', 'noun': 'the town matchmaker', 'like': 'Ask for an introduction',
                   'pass': 'Not this one', 'matched': 'They agreed to meet you',
                   'empty': 'The matchmaker knows nobody else for you here. Try another city.',
                   'tagline': 'She knows everyone worth knowing.', 'get': 'Call on the matchmaker',
                   'getting': 'Knocking at her door…'},
}


def surface(data: dict) -> str:
    if townsfolk.modern(data):
        return 'app'
    return 'column' if data.get('era') in COLUMN_ERAS else 'matchmaker'


# The user's profile ------------------------------------------------------------------------------------

def profile(connection) -> dict | None:
    row = optional(connection, 'SELECT * FROM dating_profile WHERE id=1')
    return row and {**row, 'interested_in': decode(row['interested_in'])}


def persona(connection) -> dict | None:
    """Who the user is in this world (companion/worlds.py), so the profile starts filled in."""
    return optional(connection, 'SELECT name, gender, age, about FROM persona WHERE id=1')


def default_city(connection) -> str:
    return story.default_city(connection)


def looking_in(connection, mine: dict | None) -> dict:
    """The city the user is looking in: the one on their profile, else the companion's, else Baltimore."""
    city_id = (mine or {}).get('city_id') or default_city(connection)
    try:
        return story.city_data(connection, city_id)
    except DomainError:
        return story.city_data(connection, default_city(connection))


def save_profile(database, body: dict) -> dict:
    require(body['age'] >= 18, 'The dating app is for adults: your age must be 18 or more.', 422)
    require(18 <= body['age_min'] <= body['age_max'], 'The ages you are looking for start at 18 at the youngest.', 422)
    with database.connect(write=True) as connection:
        old = profile(connection)
        connection.execute(
            'INSERT INTO dating_profile (id, name, age, gender, interested_in, looking_for, age_min, age_max, bio, '
            'city_id, seed, updated_at) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET '
            'name=excluded.name, age=excluded.age, gender=excluded.gender, interested_in=excluded.interested_in, '
            'looking_for=excluded.looking_for, age_min=excluded.age_min, age_max=excluded.age_max, bio=excluded.bio, '
            'updated_at=excluded.updated_at',
            (body['name'], body['age'], body['gender'], encode(sorted(set(body['interested_in']))),
             body['looking_for'], body['age_min'], body['age_max'], body['bio'],
             old['city_id'] if old else default_city(connection), old['seed'] if old else identifier(),
             database.now()))
    return state(database)


def installed(database) -> dict:
    """Whether the user has set the app up yet, for the sidebar's download badge."""
    with database.connect() as connection:
        return {'installed': profile(connection) is not None, 'name': APP_NAME}


def uninstall(database) -> dict:
    """Delete the user's profile and every swipe; companions made from matches stay companions."""
    with database.connect(write=True) as connection:
        connection.execute('DELETE FROM dating_swipes')
        connection.execute('DELETE FROM dating_profile')
    return state(database)


def look_in(database, city_id: str) -> dict:
    """Look for people in another city."""
    with database.connect(write=True) as connection:
        require(profile(connection) is not None, 'Set up your profile first.', 409)
        story.city_data(connection, city_id)  # 404 for an unknown city.
        connection.execute('UPDATE dating_profile SET city_id=?, updated_at=? WHERE id=1', (city_id, database.now()))
    return state(database)


# Who is on the app ---------------------------------------------------------------------------------------

_POOLS: dict[tuple, list[tuple[dict, dict]]] = {}


def pool(data: dict) -> list[tuple[dict, dict]]:
    """Everyone in the city who is on the app, with their dating details: people at its places, its residents and
    the neighbors who only turn up on the app (townsfolk.APP_MEMBERS). Several thousand people, so it is worked
    out once per city and town; only those looking are named."""
    key = (data['id'], data.get('town', ''), tuple(data.get('kin', ())), tuple(place['id'] for place in data['places']),
           tuple(hood['id'] for hood in data['neighborhoods']))
    if key not in _POOLS:
        found = [sheet for place in data['places'] for sheet in townsfolk.at_place(data, place['id'])
                 if dating.on_app(sheet, data)]
        for hood in data['neighborhoods']:
            where = townsfolk.area(data, hood['id'])
            total = townsfolk.resident_count(data, hood['id']) + townsfolk.APP_MEMBERS
            found += [townsfolk.resident(data, hood['id'], index, where) for index in range(total)
                      if dating.on_app(townsfolk.resident(data, hood['id'], index, where, named=False), data)]
        if len(_POOLS) > 16:
            _POOLS.clear()
        _POOLS[key] = [(sheet, dating.details(sheet, data)) for sheet in found]
    return _POOLS[key]


def people(connection, data: dict) -> list[tuple[dict, dict]]:
    """Who is on the app in this city, never a companion."""
    companion = current(connection)
    cast = encounters.town_cast(connection, companion, data) if companion else encounters.NO_CAST
    skip = set(cast['aliases']) | set(cast['own'])
    return [item for item in pool(data) if item[0]['key'] not in skip]


def deck(connection, data: dict, mine: dict) -> tuple[list[dict], int]:
    """The next few people for the user to swipe on, in an order fixed for this user, and how many are left."""
    swiped = {row['person_key'] for row in many(connection, 'SELECT person_key FROM dating_swipes')}
    candidates = [(sheet, found) for sheet, found in people(connection, data)
                  if sheet['key'] not in swiped and dating.suits(sheet, found, mine)]
    candidates.sort(key=lambda item: townsfolk.generators.unit(item[0]['key'], 'deck', mine['seed']))
    return candidates[:DECK_SIZE], len(candidates)


def city_for(connection, city_id: str, town: str) -> dict:
    """The city as the story has it, with the town the person was met in: a different main character's town
    would make a different person of the same key."""
    from companion.life import network
    data = story.city_data(connection, city_id)
    return data if data.get('town', '') == town else data | {'town': town, 'you': network.you(connection, town)}


def person(connection, key: str, town: str) -> tuple[dict, dict]:
    parts = key.split(':')
    require(len(parts) == 4 and parts[0] == 'town', 'No such person.', 404)
    data = city_for(connection, parts[1], town)
    sheet = townsfolk.find(data, key)
    require(sheet is not None, 'No such person.', 404)
    return sheet, data


# Swipes and matches --------------------------------------------------------------------------------------

def swipe(database, key: str, like: bool) -> dict:
    """Pass or like someone in the deck. A like is a match only if their rules like the user back; a like that
    is not returned simply never comes back, as on a real app."""
    with database.connect(write=True) as connection:
        mine = profile(connection)
        require(mine is not None, 'Set up your profile first.', 409)
        require(optional(connection, 'SELECT 1 FROM dating_swipes WHERE person_key=?', (key,)) is None,
                'You already answered this one.', 409)
        town = story.city_data(connection, key.split(':')[1] if key.count(':') == 3 else '').get('town', '')
        sheet, data = person(connection, key, town)
        found = dating.details(sheet, data)
        require(dating.suits(sheet, found, mine), 'This person is not in your deck.', 409)
        matched = like and dating.says_yes(sheet, found, mine)
        connection.execute(
            'INSERT INTO dating_swipes (person_key, city_id, town, liked, matched, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            (key, data['id'], town, int(like), int(matched), database.now()))
    return state(database) | {'matched': card(sheet, data, database) if matched else None}


def see_passed_again(database) -> dict:
    with database.connect(write=True) as connection:
        connection.execute('DELETE FROM dating_swipes WHERE liked=0')
    return state(database)


def unmatch(database, key: str) -> dict:
    with database.connect(write=True) as connection:
        connection.execute('DELETE FROM dating_swipes WHERE person_key=? AND matched=1', (key,))
    return state(database)


def card(sheet: dict, data: dict, database) -> dict:
    return dating.card(sheet, data, database.clock.now().date())


def matches(connection, database) -> list[dict]:
    found = []
    for row in many(connection, 'SELECT * FROM dating_swipes WHERE matched=1 ORDER BY created_at DESC'):
        try:
            sheet, data = person(connection, row['person_key'], row['town'])
        except DomainError:
            continue  # Their city or place has gone.
        companion = optional(connection, 'SELECT id FROM companions WHERE townsfolk_key=?', (row['person_key'],))
        found.append(card(sheet, data, database) | {'city': {'id': data['id'], 'name': data['name']},
                                                     'companion_id': companion and companion['id'],
                                                     'places': date_places(data, sheet)})
    return found


def date_places(data: dict, sheet: dict) -> list[dict]:
    """Where a date can be in their city: their usual spot first, then the rest by neighborhood."""
    places = [place for place in data['places'] if place['kind'] in DATE_KINDS]
    places.sort(key=lambda place: (place['id'] != sheet['place']['id'],
                                   townsfolk.neighborhood_name(data, place['neighborhood']), place['name']))
    return [{'id': place['id'], 'name': place['name'], 'kind': place['kind'],
             'neighborhood': townsfolk.neighborhood_name(data, place['neighborhood']),
             'theirs': place['id'] == sheet['place']['id']} for place in places]


def match(connection, key: str) -> dict | None:
    """The user's match with this person (companion/cast.py makes a match a companion), or None."""
    row = optional(connection, 'SELECT * FROM dating_swipes WHERE person_key=? AND matched=1', (key,))
    if row is None:
        return None
    sheet, data = person(connection, key, row['town'])
    return {'sheet': sheet, 'data': data, 'town': row['town'], 'details': dating.details(sheet, data),
            'noun': SURFACES[surface(data)]['noun']}


# Dates in Story mode -------------------------------------------------------------------------------------------------

def story_on(connection) -> bool:
    """Whether Story mode is switched on (Settings), so a match can be met in the story."""
    return bool(settings(connection).get('story_mode'))


def active(connection) -> dict | None:
    """The date going on now: one that was not ended, while the story is still where it began (the latest
    scene line is its arrival; going somewhere else or starting a new story ends it)."""
    row = optional(connection, 'SELECT * FROM dating_dates WHERE ended_at IS NULL ORDER BY started_at DESC LIMIT 1')
    if row is None:
        return None
    latest = optional(connection, "SELECT id FROM story_messages WHERE role='scene' ORDER BY seq DESC LIMIT 1")
    return row if latest and latest['id'] == row['arrival_id'] else None


def go_on_date(database, key: str, place_id: str) -> dict:
    """Meet a match at a place in their city: the story moves there and they are in the scene."""
    with database.connect() as connection:
        row = optional(connection, 'SELECT * FROM dating_swipes WHERE person_key=? AND matched=1', (key,))
        require(row is not None, 'You can only ask out someone you matched with.', 409)
        require(story_on(connection), 'Turn on Story mode in Settings to meet them in a story.', 409)
        sheet, data = person(connection, key, row['town'])
        place = catalog.find(data, place_id)
        require(place is not None and place['kind'] in DATE_KINDS and place in data['places'],
                'Pick somewhere in their city to meet.', 404)
    story.move(database, data['id'], place['id'])
    with database.connect(write=True) as connection:
        connection.execute('UPDATE dating_dates SET ended_at=? WHERE ended_at IS NULL', (database.now(),))
        where = {'city_id': data['id'], 'place_id': place['id']}
        arrival = story.add(connection, database.now(), 'scene',
                            f"You meet {sheet['name']} at {place['name']} for your date.", where)
        # A date counts as meeting them in the story, so they join the user's people-met list.
        day = story.local_moment(data, database.clock.now()).date()
        story_people.meet(connection, sheet, data['id'], database.now(), day,
                          (f"Went on a date at {place['name']} after matching on {SURFACES[surface(data)]['noun']}.",))
        connection.execute('INSERT INTO dating_dates (id, person_key, town, city_id, place_id, arrival_id, '
                           'started_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                           (identifier(), key, row['town'], data['id'], place['id'], arrival['id'], database.now()))
    return story.story(database)


def end_date(database) -> dict:
    with database.connect(write=True) as connection:
        row = active(connection)
        require(row is not None, 'There is no date going on.', 409)
        sheet, _data = person(connection, row['person_key'], row['town'])
        connection.execute('UPDATE dating_dates SET ended_at=? WHERE id=?', (database.now(), row['id']))
        story.add(connection, database.now(), 'scene', f"Your date with {sheet['name']} is over.",
                  {'city_id': row['city_id'], 'place_id': row['place_id']})
    return story.story(database)


def with_date(connection, data: dict, place_id: str, moment, present: list[dict]) -> list[dict]:
    """Story's people at a place, with the user's date among them while one is going on there
    (the entry point story.present calls)."""
    row = active(connection)
    if row is None or row['city_id'] != data['id'] or row['place_id'] != place_id:
        return present
    try:
        sheet, _data = person(connection, row['person_key'], row['town'])
    except DomainError:
        return present
    found = dating.details(sheet, data)
    mine = profile(connection) or {}
    noun = SURFACES[surface(data)]['noun']
    looks = dating.looks_text(found['looks'], data)
    you = f"the user ({mine['name']})" if mine.get('name') else 'the user'
    note = (f" On a date with {you}: they matched through {noun} and know each other's first names, nothing more "
            f"yet. {sheet['name']} is looking for {dating.LOOKING_TEXT.get(found['looking'], 'company')}. "
            f"Looks: {looks}.")
    mood = townsfolk.whereabouts(sheet, data, moment)['mood']
    date = {'sheet': sheet, 'place': None, 'at_place': True, 'doing': 'here on a date with the user', 'mood': mood,
            'note': note, 'shown': f"your date, {sheet['name']}"}
    return [item for item in present if item['sheet']['key'] != sheet['key']] + [date]


# The screen ----------------------------------------------------------------------------------------------

def state(database) -> dict:
    """The dating screen: the user's profile, the deck for the city they are looking in, matches and any date."""
    with database.connect() as connection:
        mine = profile(connection)
        data = looking_in(connection, mine)
        kind = surface(data)
        shown, left = deck(connection, data, mine) if mine else ([], 0)
        row = active(connection)
        date = None
        if row:
            sheet, _data = person(connection, row['person_key'], row['town'])
            date = {'key': row['person_key'], 'name': sheet['name'], 'place_id': row['place_id']}
        return {'surface': kind, 'words': SURFACES[kind], 'city': {'id': data['id'], 'name': data['name']},
                'profile': mine and {key: mine[key] for key in ('name', 'age', 'gender', 'interested_in', 'looking_for',
                                                                 'age_min', 'age_max', 'bio')},
                'persona': persona(connection), 'story': story_on(connection), 'photos': bool(backends.ordered(connection, enabled_only=True)),
                'deck': [dating.card(sheet, data, database.clock.now().date(), found) for sheet, found in shown],
                'remaining': left, 'matches': matches(connection, database), 'date': date}
