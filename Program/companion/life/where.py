"""Where you are (Hit List #59): the user's own home, and how far it is from each companion's.

Every persona has a home in each of their worlds: a city and a neighbourhood, kept on the world in worlds.json
(companion/worlds.py) and copied into the world's persona row for the prompt. The app picks it and the user can change
it on the persona form: a world's home starts in the world's city, in a neighbourhood picked the way a companion's is
(seeded, from the rent tiers, companion/life/money.py), and a city the user picks follows the same travel rules as
trips (companion/life/trips.py fits: a made-up world's persona lives in that world).

`between` is the helper the rest of Where you are builds on (together or apart, calls, long distance): whether a
companion lives in the user's city or is long distance, and how far apart the two of them are.
"""
import random
from dataclasses import dataclass

from companion.database import optional
from companion.errors import require
from companion.life import money, trips
from companion.world import catalog, changes, custom

# Who picked the home: the app (it follows the world's city while the user has not changed it) or the user.
PICKED, YOURS = 'app', 'you'


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
    world's city. A home whose city has gone goes back to the world's city. True when the home changed."""
    home = world.get('home') or {}
    city = cities.get(home.get('city_id', ''))
    if home and city and (home.get('set_by') == YOURS or city['id'] == world_city['id']):
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
    return city, hood_named(city, row['home_neighbourhood'])


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


def between(connection, definition: dict) -> Between:
    """The user's home against the companion's city (their home_city, else their location)."""
    yours = your_home(connection)
    theirs = their_city(connection, definition)
    if not yours or not theirs:
        return Between(False, True, yours and yours[0], theirs, None, True)
    city = yours[0]
    if city['id'] == theirs['id']:
        return Between(True, True, city, theirs, 0.0, True)
    km = catalog.distance_km(city, theirs) if 'lat' in city and 'lat' in theirs else None
    return Between(True, False, city, theirs, km, km is not None and km <= trips.REACH_KM[3])
