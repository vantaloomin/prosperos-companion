"""Places to go away together (Hit List #86 Away together, v1.3): where a trip with the user can go, how it gets
there, and a stand-in city to spend the days in when the place is not a city the app ships.

Only a couple of dozen cities ship, so asking for "a long weekend in Lisbon" or "Italy this summer" needs more. Rules,
no model:

- The bank (data/destinations/destinations.json): real travel destinations, each with its rough location, a climate
  zone, its character (coast, old town, mountains, wine country...), the year it became a getaway (`since`) and a few
  real sights with their own years. Worlds in our world (a real or invented city of the modern day, the jazz age, the
  Victorian era or the frontier) can go to the ones that existed as getaways in their year.
- Getaways (data/destinations/getaways.json): places with no real name ("the lake country", "the garden deck") for
  worlds that cannot go to real ones: made-up worlds (Camelot, Oz, Grandport) and their eras, and ships and stations,
  which go only to the getaways aboard or a shuttle away, never to Earth places (Vanta, 2026-11-03: trips must fit
  both the era and the ship).
- A stand-in city (`city`) is built for a bank destination, a getaway or a place nobody knows ("the cabin by the
  lake") from generic places (data/destinations/places.json) that fit the visit's style: the era or setting of the
  world it is visited from (a 1925 trip gets grand hotels and supper clubs, a medieval one coaching inns and market
  days, a ship's garden decks and viewport bars) and the destination's character. Real sights come first.

A stand-in's id carries what builds it ('away:<style>:<year>:<key>'), so the life simulation's world source can
answer for it like any city (companion/world/source.py) and the same id always gives the same places.
"""
import json
import re
from functools import cache, lru_cache

from companion.world import catalog, decades, ships
from companion.world.generators import unit

DATA = catalog.DATA / 'destinations'
PREFIX = 'away'
STYLES = ('modern', 'interwar', 'victorian', 'frontier', 'medieval', 'fantasy', 'steampunk', 'future', 'ship')
# Shorthands the places file uses for several styles at once.
STYLE_GROUPS = {
    'real': ('modern', 'interwar', 'victorian', 'frontier'),
    'town': ('modern', 'interwar', 'victorian'),
    'old': ('victorian', 'frontier', 'medieval', 'fantasy', 'steampunk'),
    'tale': ('medieval', 'fantasy'),
    'earth': ('modern', 'interwar', 'victorian', 'frontier', 'medieval', 'fantasy', 'steampunk'),
    'space': ('future', 'ship'),
}
# Eras of our world, and the year a city of another era of it is in.
OUR_ERAS = ('modern', 'jazz-age', 'victorian', 'frontier')
ERA_YEARS = {'jazz-age': 1925, 'victorian': 1895, 'frontier': 1880}
# The era a stand-in visited in each style of our world is in, for the words and prices of its time.
STYLE_ERAS = {'modern': 'modern', 'interwar': 'jazz-age', 'victorian': 'victorian', 'frontier': 'frontier'}
ERA_STYLES = {'jazz-age': 'interwar', 'victorian': 'victorian', 'frontier': 'frontier', 'medieval': 'medieval',
              'fantasy': 'fantasy', 'steampunk': 'steampunk', 'future': 'future'}
# How many generic places of each category a stand-in gets, beside its real sights.
PER_CATEGORY = 8
CATEGORIES = ('sights', 'outdoors', 'food', 'evening')
DAY_PARTS = {
    'museum': ['morning', 'afternoon'], 'landmark': ['morning', 'afternoon', 'evening'],
    'attraction': ['morning', 'afternoon', 'evening'], 'park': ['morning', 'afternoon'],
    'garden': ['morning', 'afternoon'], 'trail': ['morning', 'afternoon'], 'beach': ['morning', 'afternoon'],
    'restaurant': ['afternoon', 'evening', 'late'], 'cafe': ['morning', 'afternoon'],
    'market': ['morning', 'afternoon'], 'bar': ['evening', 'late'], 'nightlife': ['evening', 'late'],
    'tavern': ['afternoon', 'evening', 'late'], 'inn': ['evening', 'late'], 'venue': ['evening'],
}
OUTDOOR = {'park', 'garden', 'trail', 'beach', 'landmark'}
# A destination's neighbourhoods by its character, after the centre every one has.
EDGES = (({'coast', 'islands', 'lakes'}, 'waterfront', 'the waterfront'),
         ({'mountains', 'countryside', 'wine', 'desert'}, 'outskirts', 'the outskirts'))
# The climate of a place with no real location, by its character (the first that matches).
CHARACTER_CLIMATE = (('desert', 'desert'), ('mountains', 'alpine'), ('wine', 'mediterranean'),
                     ('islands', 'mediterranean'), ('big-city', 'continental'))
NO_SOUTHERN_TURN = {'tropical', 'highland'}
# Words in a place nobody knows that say what it is like.
CHARACTER_WORDS = (('coast', r'beach|coast|seaside|shore|bay|harbou?r|sea\b'), ('islands', r'island|isle|key\b|cay'),
                   ('lakes', r'lake|loch|lago'), ('mountains', r'mountain|cabin|alp|ski|peak|hills?\b|ridge|valley'),
                   ('wine', r'vineyard|winery|wine'), ('desert', r'desert|canyon|mesa|oasis'),
                   ('countryside', r'farm|village|country|cottage|ranch|forest|woods'))
# Travel: (way, km an hour, hours of getting to and from it) by style; the second way crosses an ocean.
OVERLAND = {'modern': ('car', 80, 0.5), 'interwar': ('train', 55, 1.0), 'victorian': ('train', 40, 1.0),
            'frontier': ('train', 35, 2.0)}
OVERSEAS = {'modern': ('plane', 750, 3.0), 'interwar': ('steamship', 30, 6.0), 'victorian': ('steamship', 25, 6.0),
            'frontier': ('steamship', 25, 6.0)}
DRIVE_KM = 500
STAGECOACH = ('stagecoach', 12, 0.5, 250)
# A place nobody knows, with no location: hours away by style.
UNKNOWN_HOURS = {'modern': ('plane', 9.0), 'interwar': ('train', 20.0), 'victorian': ('train', 20.0),
                 'frontier': ('stagecoach', 30.0), 'medieval': ('coach', 10.0), 'fantasy': ('coach', 10.0),
                 'steampunk': ('train', 8.0), 'future': ('shuttle', 6.0)}
# Nights a trip needs by hours of travel each way: a weekend for a short journey, a week for a long one.
NIGHTS = ((6, 2), (12, 3), (24, 5), (48, 7))
# A trip's cost as a share of a month's take-home: the stay by nights, and the fare by the way they travel.
STAY_SHARE = {2: 0.10, 3: 0.14, 5: 0.22, 7: 0.28}
FARE_SHARE = {'car': 0.02, 'train': 0.03, 'plane': 0.06, 'steamship': 0.25, 'stagecoach': 0.03, 'coach': 0.03,
              'shuttle': 0.03}
CHEAP_WAYS = {'tram', 'lift'}


def _load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding='utf-8'))


@cache
def bank() -> tuple[dict, ...]:
    return tuple(_load('destinations.json')['destinations'])


@cache
def getaways() -> tuple[dict, ...]:
    return tuple(_load('getaways.json')['getaways'])


@cache
def templates() -> dict[str, tuple[dict, ...]]:
    return {key: tuple(items) for key, items in _load('places.json')['categories'].items()}


@cache
def climates() -> dict[str, dict]:
    return _load('climates.json')['zones']


def styles_of(names) -> set[str]:
    """The styles a list of style names and shorthands covers."""
    return {style for name in names for style in STYLE_GROUPS.get(name, (name,))}


# --- The world a trip leaves from ---

def year_of(home: dict) -> int | None:
    """The year a city of our world is in (a past year for a modern city in Back when, else this year, or its era's
    year); None for a made-up world or a ship, where years do not apply."""
    era = home.get('era') or 'modern'
    if era in ERA_YEARS:
        return ERA_YEARS[era]
    if era != 'modern' or ships.enclosed(home):
        return None
    return decades.offered_year(home)


def style(home: dict, year: int | None = None) -> str:
    """The style of a trip from this city: a ship's, its era's, or modern by the year."""
    if ships.enclosed(home):
        return 'ship'
    era = home.get('era') or 'modern'
    if era != 'modern':
        return ERA_STYLES.get(era, 'fantasy')
    year = year or year_of(home)
    return 'modern' if not year or year >= 1950 else 'interwar' if year >= 1914 else 'victorian'


def our_world(home: dict) -> bool:
    """A city of our world, on the ground, in an era real places can be visited from."""
    if ships.enclosed(home) or (home.get('era') or 'modern') not in OUR_ERAS:
        return False
    return home.get('setting', 'real') in ('real', 'original') or catalog.category(home) in ('real', 'other-eras')


def landmass(lon: float) -> str:
    """Roughly which side of an ocean a place is on, by its longitude."""
    return 'americas' if lon < -25 else 'asia-oceania' if lon > 60 else 'europe-africa'


# --- Where a trip can go ---

def in_year(item: dict, year: int | None) -> bool:
    """Whether something with optional `since` and `until` exists in `year` (always, where years do not apply)."""
    return year is None or (item.get('since') or 0) <= year <= (item.get('until') or 9999)


def option(item: dict, kind: str) -> dict:
    """A destination as trips use it: 'b' a bank destination, 'g' a getaway."""
    found = {'key': f'{kind}-{item["id"]}', 'name': item['name'], 'prep': item.get('prep', 'in'),
             'character': list(item['character']), 'summary': item.get('summary', ''),
             'best_months': list(item.get('best_months') or range(1, 13))}
    if kind == 'b':
        found |= {'country': item['country'], 'lat': item['lat'], 'lon': item['lon'], 'timezone': item['timezone']}
    else:
        found |= {'by': item['by'], 'hours': item['hours']}
    return found


def options(home: dict, year: int | None = None) -> list[dict]:
    """Every destination a trip from `home` can go to: real ones that were getaways by then (not the home city
    itself), and the getaways that fit its style."""
    year = year if year is not None else year_of(home)
    chosen = style(home, year)
    found = []
    if our_world(home):
        found = [option(item, 'b') for item in bank() if in_year(item, year) and not same_place(home, item)]
    return found + [option(item, 'g') for item in getaways() if chosen in styles_of(item['styles'])]


def same_place(home: dict, item: dict) -> bool:
    names = {words(name) for name in (home.get('name', ''), home.get('id', '').replace('-', ' '),
                                      *(home.get('aliases') or ()))}
    if words(item['name']) in names:
        return True
    return 'lat' in home and 'lon' in home and catalog.distance_km(home, item) < 30


def words(text: str) -> str:
    return ' '.join(re.findall(r'[a-z0-9]+', text.lower()))


def names_of(item: dict) -> list[str]:
    name = re.sub(r'^the\s+', '', item['name'], flags=re.IGNORECASE)
    return [item['name'], name, *item.get('aliases', ())]


def mentioned(text: str, names) -> bool:
    said = f' {words(text)} '
    return any(f' {words(name)} ' in said for name in names if words(name))


def lookup(text: str, home: dict, year: int | None = None) -> dict:
    """What a message names as a place to go: {'options': [...], 'why': None} with the destinations it names
    (by name or alias first, else every one in a country it names), or no options and why: 'elsewhere' when it
    names a real place a made-up world or a ship cannot go to, 'not-yet' when the place was no getaway yet in the
    world's year. {'options': [], 'why': None} when it names none."""
    year = year if year is not None else year_of(home)
    usable = {item['key']: item for item in options(home, year)}
    named = [item for item in bank() if mentioned(text, names_of(item))]
    named += [item for item in getaways() if mentioned(text, [item['name']])]
    if not named:
        named = [item for item in bank() if mentioned(text, [item['country']])]
    found = [usable[key] for key in (f'{"b" if "country" in item else "g"}-{item["id"]}' for item in named)
             if key in usable]
    if found or not named:
        return {'options': found, 'why': None}
    real = [item for item in named if 'country' in item]
    if real and our_world(home):
        return {'options': [], 'why': 'not-yet'}
    return {'options': [], 'why': 'elsewhere' if real else None}


def unknown(name: str) -> dict:
    """A place nobody knows ("the cabin by the lake"): a stand-in with that name, its character read from its words,
    and no location."""
    character = [key for key, pattern in CHARACTER_WORDS if re.search(pattern, name, re.IGNORECASE)]
    return {'key': f'x-{slug(name)}', 'name': name.strip(), 'prep': 'in',
            'character': character or ['countryside', 'old-town'], 'summary': '', 'best_months': list(range(1, 13))}


def slug(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:40] or 'somewhere'


def best_for(found: list[dict], month: int, seed: str, likes: set[str] = frozenset()) -> dict | None:
    """One of `found` for a trip in `month`: in season is likelier, and one whose character they like."""
    from companion.world.generators import pick
    weights = [(3.0 if month in item['best_months'] else 1.0) * (1 + len(likes & set(item['character'])))
               for item in found]
    return pick(seed, 'destination', found, weights)


# --- Getting there ---

def journey(home: dict, place: dict, year: int | None = None) -> dict:
    """{'by': how they travel, 'hours': each way} for a trip from `home` to `place` (an option)."""
    year = year if year is not None else year_of(home)
    chosen = style(home, year)
    if 'hours' in place:
        return {'by': place['by'], 'hours': float(place['hours'])}
    if 'lat' not in place or 'lat' not in home or chosen not in OVERLAND:
        by, hours = UNKNOWN_HOURS.get(chosen, ('coach', 10.0))
        return {'by': by, 'hours': hours}
    km = catalog.distance_km(home, place)
    overseas = landmass(place['lon']) != landmass(home['lon']) or ('islands' in place['character'] and km > 150)
    if overseas:
        by, speed, extra = OVERSEAS[chosen]
    elif chosen == 'modern' and km > DRIVE_KM:
        by, speed, extra = OVERSEAS['modern']
    elif chosen == 'frontier' and km <= STAGECOACH[3]:
        by, speed, extra = STAGECOACH[:3]
    else:
        by, speed, extra = OVERLAND[chosen]
    return {'by': by, 'hours': round(km / speed + extra, 1)}


def nights(way: dict) -> int | None:
    """The fewest nights a trip there makes sense for, or None when it is too far for a week away."""
    return next((count for hours, count in NIGHTS if way['hours'] <= hours), None)


def cost_share(way: dict, count: int) -> float:
    """What a trip costs as a share of a month's take-home: the stay for `count` nights and the fare."""
    stay = STAY_SHARE.get(count) or STAY_SHARE[max(key for key in STAY_SHARE if key <= count)]
    fare = 0.0 if way['by'] in CHEAP_WAYS else FARE_SHARE.get(way['by'], 0.03)
    if way['by'] == 'plane':
        fare += 0.004 * way['hours']
    return round(stay + fare, 3)


# --- A stand-in city ---

def stand_in_id(place: dict, home: dict, year: int | None = None) -> str:
    """The id of the stand-in for `place` visited from `home`."""
    year = year if year is not None else year_of(home)
    return f'{PREFIX}:{style(home, year)}:{year or 0}:{place["key"]}'


def is_stand_in(city_id: str | None) -> bool:
    return bool(city_id) and city_id.startswith(f'{PREFIX}:')


def parse(city_id: str) -> tuple[str, int | None, dict] | None:
    """(style, year, option) from a stand-in's id, or None when it names nothing."""
    parts = city_id.split(':', 3)
    if len(parts) != 4 or parts[1] not in STYLES or not parts[2].isdigit():
        return None
    _prefix, chosen, year, key = parts
    kind, _dash, ident = key.partition('-')
    if kind == 'b':
        found = next((option(item, 'b') for item in bank() if item['id'] == ident), None)
    elif kind == 'g':
        found = next((option(item, 'g') for item in getaways() if item['id'] == ident), None)
    else:
        found = unknown(ident.replace('-', ' ')) if kind == 'x' and ident else None
    return (chosen, int(year) or None, found) if found else None


@lru_cache(maxsize=256)
def city(city_id: str) -> dict | None:
    """The stand-in city a stand-in id names, shaped like a city pack so the world source can use it."""
    parsed = parse(city_id)
    if not parsed:
        return None
    chosen, year, place = parsed
    space = chosen in STYLE_GROUPS['space']
    real = next((item for item in bank() if f'b-{item["id"]}' == place['key']), None)
    hoods = neighbourhoods(place, space)
    places = [*sights(real, year, hoods), *generic(city_id, place, chosen, year, hoods)]
    return {
        'id': city_id, 'name': place['name'], 'setting': 'real' if real else 'original',
        'era': 'future' if space else STYLE_ERAS.get(chosen, chosen),
        'distribution': 'public', 'category': 'real' if real else 'fictional', 'origin': 'stand-in',
        'region': '', 'country': place.get('country', ''), 'timezone': place.get('timezone', ''),
        'aliases': [], 'summary': place['summary'], 'lat': place.get('lat', 0.0), 'lon': place.get('lon', 0.0),
        'neighborhoods': hoods, 'places': places, 'colleges': [], 'employers': [], 'annual_events': [],
        'climate': None if space else climate(place), 'enclosed': space or None, 'prep': place['prep'],
        'sources': {}, 'builtin': False, 'stand_in': True}


def neighbourhoods(place: dict, space: bool) -> list[dict]:
    lat, lon = place.get('lat', 0.0), place.get('lon', 0.0)
    hoods = [{'id': 'centre', 'name': 'the main deck' if space else 'the centre', 'lat': lat, 'lon': lon}]
    for offset, (characters, ident, name) in enumerate(EDGES, start=1):
        if not space and set(place['character']) & characters:
            hoods.append({'id': ident, 'name': name, 'lat': lat + 0.01 * offset, 'lon': lon + 0.01 * offset})
    return hoods


def climate(place: dict) -> dict:
    """Typical months for the place's zone, half a year on south of the equator; by character without a zone."""
    real = next((item for item in bank() if f'b-{item["id"]}' == place['key']), None)
    zone = real['climate'] if real else next((zone for key, zone in CHARACTER_CLIMATE
                                              if key in place['character']), 'oceanic')
    months = climates()[zone]['months']
    if place.get('lat', 0.0) < 0 and zone not in NO_SOUTHERN_TURN:
        months = months[6:] + months[:6]
    return {'summary': '', 'months': [dict(month) for month in months], 'source': f'destinations-{zone}'}


def record(ident: str, name: str, kind: str, hood: str, *, summary: str = '', tags=(), parts=None,
           seasons=()) -> dict:
    return {'id': ident, 'name': name, 'kind': kind, 'neighborhood': hood, 'summary': summary or name,
            'tags': list(tags), 'cost': '$$', 'setting': 'outdoor' if kind in OUTDOOR else 'indoor',
            'good_for': ['date', 'friends', 'solo'], 'day_parts': list(parts or DAY_PARTS.get(kind, ['afternoon'])),
            'seasons': list(seasons), 'cuisine': '', 'spots': [], 'source': 'destinations'}


def sights(real: dict | None, year: int | None, hoods: list[dict]) -> list[dict]:
    """A bank destination's own sights that stand in its year, each an iconic place."""
    if not real:
        return []
    return [record(f'sight-{slug(item["name"])}', item['name'], item['kind'], hoods[0]['id'],
                   tags=('iconic',)) for item in real['sights'] if in_year(item, year)]


def fits(template: dict, chosen: str, year: int | None, character: set[str]) -> bool:
    if chosen not in styles_of(template['styles']) or not in_year(template, year):
        return False
    where = set(template['where'])
    return not where or bool(where & character)


def generic(city_id: str, place: dict, chosen: str, year: int | None, hoods: list[dict]) -> list[dict]:
    """PER_CATEGORY generic places of each category that fit the style, the year and the place's character: those
    made for its character first, then ones that suit anywhere, in an order seeded by the stand-in."""
    character = {'space'} if chosen in STYLE_GROUPS['space'] else set(place['character'])
    hood_ids = {hood['id'] for hood in hoods}
    found = []
    for category in CATEGORIES:
        fitting = [item for item in templates()[category] if fits(item, chosen, year, character)]
        fitting.sort(key=lambda item: (not item['where'], unit(city_id, category, item['name'])))
        for item in fitting[:PER_CATEGORY]:
            found.append(record(f'{category}-{slug(item["name"])}', item['name'], item['kind'],
                                hood_for(item, hood_ids), summary=item.get('summary', ''),
                                tags=item.get('tags', ()), parts=item.get('parts'), seasons=item.get('seasons', ())))
    return found


def hood_for(item: dict, hood_ids: set[str]) -> str:
    if 'waterfront' in hood_ids and (item['kind'] == 'beach' or 'waterfront' in item.get('tags', ())):
        return 'waterfront'
    if 'outskirts' in hood_ids and item['kind'] in ('trail', 'park'):
        return 'outskirts'
    return 'centre'
