"""Ships and stations (Hit List #77): a city that is a ship or a station is `enclosed`, and the app makes the calls
that follow from that itself, with no step for the user.

A city sets `enclosed` in its file, or the app reads it from the city when it loads (`settle`): the era is `future`
and its country, region or name says ship or station ("Ship", "Orbital station"), or two or more of its
neighbourhoods are decks or rings. `"enclosed": false` keeps a future city that only sounds like one on the ground.

Aboard there is no weather and no Earth seasons (generators.conditions, the winter colds in life/body.py, the
wardrobe's coat shopping), a flat climate when the city gives none, so the wardrobe never buys for 45°F winters, no
cars (life/home.py, commutes) and no car bills (life/money.py), and no summer barbecues (life/network.py). Pictures
get ship lighting and indoor words for outdoor scenes (images/prompts.py), all fixed templates in visible words.

Travel within one made-up world: a city lists `neighbours` (other built-in, pack or user cities, ships or stations)
with a travel time in hours, and trips and postcards use them (life/trips.py). A listing works both ways. A ship or
station travels only to its neighbours, by shuttle unless the listing says otherwise, and nobody on the ground
visits one that does not list them.
"""
import re

from companion.world import catalog

SHIP_WORDS = re.compile(r'\b(?:ship|starship|spaceship|space\s+station|station|orbital|starbase|space\s+habitat|'
                        r'generation\s+ship|colony\s+ship|ark|vessel|freighter)\b', re.IGNORECASE)
DECK_WORDS = re.compile(r'\b(?:deck|decks|ring|module|spoke)\b', re.IGNORECASE)
DECKS = 2
FLAT_SOURCE = 'enclosed-climate'
FLAT_MONTH = {'high_f': 70, 'low_f': 66, 'rain_days': 0, 'note': 'Climate-controlled decks'}
# Ways to travel that a ship or station has no room for.
GROUNDED = ('car', 'rideshare', 'carriage', 'horse', 'stagecoach')
SHUTTLE = 'shuttle'
# How long a weekend trip may take to get there, each way, for two nights and for three.
REACH_HOURS = {2: 6, 3: 12}


def detected(data: dict) -> bool:
    """Whether the city reads as a ship or station: a future city named so, or with decks and rings for
    neighbourhoods."""
    if data.get('era') != 'future':
        return False
    words = ' '.join(data.get(key) or '' for key in ('country', 'region', 'name'))
    decks = sum(bool(DECK_WORDS.search(hood.get('name', ''))) for hood in data.get('neighborhoods', ()))
    return bool(SHIP_WORDS.search(words)) or decks >= DECKS


def settle(data: dict) -> list[str]:
    """Called as a city loads (catalog.prepare): decide `enclosed` when the city leaves it out, and give an
    enclosed city what follows from it. Notes say what the app decided, for a city someone wrote."""
    notes = []
    if data.get('enclosed') is None:
        data.pop('enclosed', None)
        if detected(data):
            data['enclosed'] = True
            notes.append(f'{data["name"]} reads as a ship or station, so it has no weather or Earth seasons and '
                         'nobody drives. Set "enclosed": false to change that.')
    if not data.get('enclosed'):
        return notes
    if not data.get('climate'):
        data['sources'][FLAT_SOURCE] = {
            'kind': 'curated', 'title': 'Climate-controlled decks, set by the app for a ship or station',
            'license': 'CC0-1.0', 'retrieved': '2026-10-20', 'url': '', 'attribution': '', 'note': ''}
        data['climate'] = {'summary': 'Climate-controlled decks: the same mild air all year.',
                           'months': [dict(FLAT_MONTH) for _ in range(12)], 'source': FLAT_SOURCE}
    data['speeds'] = {key: value for key, value in data['speeds'].items() if key not in GROUNDED} or {'walk': 4.5}
    return notes


def enclosed(data: dict | None) -> bool:
    return bool(data) and data.get('enclosed') is True


def home_of(connection, definition: dict) -> dict | None:
    """The character's home city (built in, a pack or the user's own), by their home city or location."""
    from companion.world import changes, custom
    extra = custom.all_cities(connection)
    for text in (definition.get('home_city'), definition.get('location')):
        if text and (found := changes.resolve(text, extra)):
            return found
    return None


def aboard(connection, definition: dict) -> bool:
    """Whether the character lives on a ship or station."""
    return enclosed(home_of(connection, definition))


# --- Travel between made-up places ---

def links(home: dict, known: dict[str, dict]) -> list[tuple[dict, dict]]:
    """(city, link) for each city `home` lists as a neighbour, or that lists `home`, among the `known` cities that
    load. A city's own listing wins over the other's. `link` has the hours and how people get there."""
    found = {}
    for link in home.get('neighbours') or ():
        if link['city'] in known and link['city'] != home['id']:
            found[link['city']] = link
    for other in known.values():
        if other['id'] in found or other['id'] == home['id']:
            continue
        back = next((link for link in other.get('neighbours') or () if link['city'] == home['id']), None)
        if back:
            found[other['id']] = {**back, 'city': other['id']}
    return [(known[key], found[key]) for key in sorted(found)]


def reachable(home: dict, known: dict[str, dict], nights: int) -> list[dict]:
    """The neighbours close enough for a weekend of `nights` nights."""
    limit = REACH_HOURS.get(nights, REACH_HOURS[2])
    return [city for city, link in links(home, known) if link['hours'] <= limit]


def linked(home: dict, other: dict) -> bool:
    return any(city['id'] == other['id'] for city, _link in links(home, {other['id']: other}))


def by(home: dict | None, other: dict | None) -> str:
    """How people travel between two cities: the listing's own word, a shuttle where a ship or station is at either
    end, else '' (the trip's usual words)."""
    if not home or not other:
        return ''
    link = next((link for city, link in links(home, {other['id']: other})), None)
    if link and link.get('by'):
        return re.sub(r'^(?:the|a|an)\s+', '', link['by'].strip(), flags=re.IGNORECASE)
    return SHUTTLE if enclosed(home) or enclosed(other) else ''


def known_cities(connection) -> dict[str, dict]:
    """Every city that loads: built in, packs and the user's own."""
    from companion.world import custom
    return catalog.cities() | custom.all_cities(connection)
