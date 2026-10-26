"""Lay a drafted place out: which neighbourhoods it has, where each sits, and its sea, river or lake.

The heart of the place comes first, then the waterside quarter its water calls for, then a mix of what towns
have (a market, homes, works, the well-off and the poor, green edges, learning, nightlife) until the size the line
asked for. Ships and stations get decks in a line from bow to stern."""
import math

from companion.world import generators
from companion.world.draft import banks

WATER_ROLES = {'sea': 'harbour', 'river': 'riverside', 'lake': 'lakeside'}
ROLES = ('market', 'homes', 'works', 'wealthy', 'green', 'learning', 'nightlife', 'poor', 'old-quarter', 'homes',
         'temple', 'outskirts', 'works', 'homes', 'harbour', 'green')
SIDES = {'north': 0, 'east': 90, 'south': 180, 'west': 270}
# How far apart neighbourhoods sit, in km, and how far apart decks sit, in degrees of longitude.
SPACING_KM = 1.3
DECK_STEP = 0.003
KM_PER_DEGREE = 111.0


def roles(brief: dict) -> list[str]:
    first = ['centre']
    if brief['water']:
        first.append(WATER_ROLES[brief['water']])
    return first + list(ROLES)


def choose(brief: dict, seed: str) -> list[dict]:
    """The neighbourhood entries, one per role in turn, none twice, up to the size asked for."""
    pool = banks.hoods(brief)
    chosen = []
    for role in roles(brief):
        if len(chosen) == brief['hoods']:
            break
        options = [entry for entry in pool if entry['role'] == role and entry not in chosen]
        if options:
            chosen.append(generators.pick(seed, f'hood:{role}:{len(chosen)}', options))
    spare = [entry for entry in pool if entry not in chosen]
    while len(chosen) < brief['hoods'] and spare:
        chosen.append(spare.pop(int(generators.unit(seed, 'spare', len(chosen)) * len(spare))))
    return chosen


def offset(lat: float, lon: float, km: float, bearing: float) -> tuple[float, float]:
    """The point `km` from (lat, lon) on a compass bearing, near enough for a town."""
    rad = math.radians(bearing)
    dlat = km * math.cos(rad) / KM_PER_DEGREE
    dlon = km * math.sin(rad) / (KM_PER_DEGREE * max(math.cos(math.radians(lat)), 0.2))
    return round(lat + dlat, 4), round(lon + dlon, 4)


def spots(brief: dict, chosen: list[dict], centre: tuple[float, float], side: str | None, seed: str) -> list:
    """Where each neighbourhood sits: the centre in the middle, the waterside quarter towards the water, the rest
    in rings round them, away from the sea."""
    if brief['aboard']:
        return [(0.0, round(centre[1] + DECK_STEP * index, 4)) for index in range(len(chosen))]
    facing = SIDES.get(side or '', generators.unit(seed, 'facing') * 360)
    found = []
    for index, entry in enumerate(chosen):
        if index == 0:
            found.append(centre)
            continue
        ring = 1 + (index - 1) // 6
        if entry['role'] == WATER_ROLES.get(brief['water'] or ''):
            bearing = facing + (index % 3 - 1) * 25
        else:
            spread = 270 if brief['water'] == 'sea' else 360
            bearing = facing + 45 + spread * ((index * 0.381966) % 1) + (90 if spread < 360 else 0)
        found.append(offset(*centre, SPACING_KM * ring + generators.unit(seed, 'jitter', index) * 0.4, bearing))
    return found


def water(brief: dict, centre: tuple[float, float], side: str | None, name: str) -> list[dict]:
    """The place's sea, river or lake, for the drawn map."""
    kind = brief['water']
    if kind == 'sea':
        return [{'kind': 'sea', 'name': name, 'side': side}]
    if kind == 'river':
        bearing = SIDES.get(side, 0)
        return [{'kind': 'river', 'name': name, 'width_km': 0.15,
                 'points': [list(offset(*centre, 6, bearing)), list(centre), list(offset(*centre, 6, bearing + 180))]}]
    if kind == 'lake':
        return [{'kind': 'lake', 'name': name, 'width_km': 1.5, 'points': [list(offset(*centre, 2.2, SIDES[side]))]}]
    return []
