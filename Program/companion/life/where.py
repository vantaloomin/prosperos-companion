"""Where you are (Hit List #59): the user's own home, and how far it is from each companion's.

Every persona has a home in each of their worlds: a city and a neighbourhood, kept on the world in worlds.json
(companion/worlds.py) and copied into the world's persona row for the prompt. The app picks it and the user can change
it on the persona form: a world's home starts in the world's city, in a neighbourhood picked the way a companion's is
(seeded, from the rent tiers, companion/life/money.py), and a city the user picks follows the same travel rules as
trips (companion/life/trips.py fits: a made-up world's persona lives in that world).

`between` is the helper the rest of Where you are builds on (together or apart, calls, long distance): whether a
companion lives in the user's city or is long distance, and how far apart the two of them are. A companion whose city
can't be told but whose time zone differs from the user's city's is long distance too (Vanta's decision "Time zone
decides", v0.13), placed by their own words for where they live, else by their time zone's city.
"""
import random
from dataclasses import dataclass
from datetime import datetime

from companion.clock import zone
from companion.database import optional
from companion.errors import DomainError, require
from companion.life import money, trips
from companion.world import catalog, changes, custom

# Who picked the home: the app (it follows the world's city while the user has not changed it) or the user.
PICKED, YOURS = 'app', 'you'
# A city of another era this close to the user's is the same place (London and London, 1895 are 1 km apart).
SAME_PLACE_KM = 30


def known_cities(connection) -> dict[str, dict]:
    """Every city by id, a built-in one winning over a user's city with the same id (as catalog.city has it)."""
    return {**custom.all_cities(connection), **catalog.cities()}


def neighbourhood_for(city: dict, seed: str) -> str:
    """The app's pick: a neighbourhood with ordinary rents (money.py's middle pay tier), seeded by the world; any
    neighbourhood in a city without rents, and none in a city that has no neighbourhoods."""
    hoods = city.get('neighborhoods') or []
    priced = [hood for hood in hoods if hood.get('rent')]
    fitting = [hood for hood in priced if hood.get('rent_tier') in money.HOOD_TIERS[money.DEFAULT_TIER]] or priced or hoods
    return random.Random(f'{seed}:your-hood').choice(sorted(fitting, key=lambda hood: hood['id']))['id'] if fitting else ''


def picked(city: dict, seed: str) -> dict:
    return {'city_id': city['id'], 'neighbourhood': neighbourhood_for(city, seed), 'set_by': PICKED}


def hood_named(city: dict, hood_id: str) -> dict | None:
    return next((hood for hood in city.get('neighborhoods') or [] if hood['id'] == hood_id), None)


def allowed(world_city: dict, city: dict) -> bool:
    """A home in the world's own city, or in one a trip from it could reach (same era and the same world)."""
    return city['id'] == world_city['id'] or trips.fits(world_city, city)


def choices(world_city: dict, cities: dict[str, dict]) -> list[dict]:
    """The cities the persona can live in, the world's own first."""
    others = sorted((city for city in cities.values() if city['id'] != world_city['id'] and allowed(world_city, city)),
                    key=lambda city: city['name'])
    return [world_city, *others]


def settle(world: dict, world_city: dict, cities: dict[str, dict]) -> bool:
    """Gives `world` its home when it has none (an upgrade, a new world), and moves an app-picked home along with the
    world's city. A home whose city has gone, or that the world's city can no longer reach (a world that became Camelot
    when its first companion lives there), goes back to the world's city. True when the home changed."""
    home = world.get('home') or {}
    city = cities.get(home.get('city_id', ''))
    if home and city and (city['id'] == world_city['id'] or (home.get('set_by') == YOURS and allowed(world_city, city))):
        if home.get('neighbourhood') and not hood_named(city, home['neighbourhood']):
            home['neighbourhood'] = neighbourhood_for(city, world['id'])
            return True
        return False
    world['home'] = picked(world_city, world['id'])
    return True


def change(world: dict, world_city: dict, city: dict, neighbourhood: str):
    """The user's own pick. A blank neighbourhood, or one from another city, lets the app pick one there."""
    require(allowed(world_city, city), f"You can't live in {city['name']} in this world.", 422)
    hood = neighbourhood if hood_named(city, neighbourhood) else neighbourhood_for(city, world['id'])
    world['home'] = {'city_id': city['id'], 'neighbourhood': hood, 'set_by': YOURS}


def view(home: dict | None, cities: dict[str, dict]) -> dict | None:
    """The home as the persona form shows it."""
    city = home and cities.get(home.get('city_id', ''))
    if not city:
        return None
    hood = hood_named(city, home.get('neighbourhood', ''))
    return {'city_id': city['id'], 'city': city['name'], 'region': city.get('region', ''),
            'neighbourhood': hood['id'] if hood else '', 'neighbourhood_name': hood['name'] if hood else '',
            'set_by': home.get('set_by', PICKED)}


# In a world ---------------------------------------------------------------------------------------------------

def your_home(connection) -> tuple[dict, dict | None] | None:
    """The user's city in this world and their neighbourhood in it, from the persona row; None before there is one."""
    row = optional(connection, 'SELECT home_city_id, home_neighbourhood FROM persona WHERE id=1')
    city = row and row['home_city_id'] and changes.resolve(row['home_city_id'], custom.all_cities(connection))
    if not city:
        return None
    # Living with a companion in this city, home is the place they share (companion/life/moving_in.py).
    from companion.life import moving_in
    return city, hood_named(city, moving_in.shared_home(connection, city['id']) or row['home_neighbourhood'])


def home_text(connection) -> str:
    """"Canton, Baltimore", or just the city when there is no neighbourhood; '' before there is a home."""
    found = your_home(connection)
    if not found:
        return ''
    city, hood = found
    return f"{hood['name']}, {city['name']}" if hood else city['name']


@dataclass(frozen=True)
class Between:
    """How far a companion lives from the user. `known` is False when either city can't be told, and then they count
    as the same city, as they always did before Where you are."""
    known: bool
    same_city: bool
    your_city: dict | None
    their_city: dict | None
    km: float | None
    # Within a trip's reach (trips.REACH_KM, three nights), so a weekend visit can bridge it.
    within_reach: bool

    @property
    def long_distance(self) -> bool:
        return not self.same_city


def their_city(connection, definition: dict) -> dict | None:
    cities = custom.all_cities(connection)
    for text in (definition.get('home_city'), definition.get('location')):
        if text and (found := changes.resolve(text, cities)):
            return found
    return None


def same_place(yours: dict, theirs: dict) -> bool:
    """The same city in another era: "Harlem, New York" read as today's New York for a user in New York, 1925.
    Nobody lives across eras, so a companion's city there is the user's own."""
    return (theirs.get('era', 'modern') != yours.get('era', 'modern') and 'lat' in yours and 'lat' in theirs
            and catalog.distance_km(yours, theirs) <= SAME_PLACE_KM)


# Two time zones are the same one when they keep the same clock in winter and in summer.
SEASONS = (datetime(2026, 1, 15, 12), datetime(2026, 7, 15, 12))


def other_zone(city: dict, timezone: str | None) -> bool:
    """Whether a companion's time zone keeps another clock than the user's city: either one unknown counts as the
    same."""
    try:
        mine, theirs = zone(city.get('timezone') or ''), zone(timezone or '')
    except DomainError:
        return False
    return any(day.replace(tzinfo=mine).utcoffset() != day.replace(tzinfo=theirs).utcoffset() for day in SEASONS)


def zone_place(definition: dict) -> dict:
    """Where a companion in another time zone lives, when no city is known: their own words ("a cabin outside
    Anchorage"), else their time zone's city ("America/Los_Angeles" is Los Angeles). No trip reaches it (no lat)."""
    timezone = definition.get('timezone') or ''
    name = (definition.get('home_city') or definition.get('location') or '').strip()
    return {'id': f'~zone:{timezone}', 'name': name or timezone.rsplit('/', 1)[-1].replace('_', ' '),
            'timezone': timezone}


def between(connection, definition: dict) -> Between:
    """The user's home against the companion's city (their home_city, else their location), else their time zone."""
    yours = your_home(connection)
    theirs = their_city(connection, definition)
    if yours and not theirs and other_zone(yours[0], definition.get('timezone')):
        return Between(True, False, yours[0], zone_place(definition), None, False)
    if not yours or not theirs:
        return Between(False, True, yours and yours[0], theirs, None, True)
    city = yours[0]
    if same_place(city, theirs):
        theirs = city
    if city['id'] == theirs['id']:
        return Between(True, True, city, theirs, 0.0, True)
    km = catalog.distance_km(city, theirs) if 'lat' in city and 'lat' in theirs else None
    return Between(True, False, city, theirs, km, km is not None and km <= trips.REACH_KM[3])
