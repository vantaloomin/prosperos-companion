"""The next place to go (shared by Away together and Second location, v1.3): a place for this part of the day, near
where they just were, that they have not been to yet today.

Rules, no model: the places of the kinds that suit the part of the day (sights and parks in the morning, the water
in the afternoon, dinner and drinks in the evening) that are open then and in season, in a city the world source
answers for (a shipped city or a stand-in, companion/world/destinations.py). Places already visited are left out
while others remain; one in the same neighbourhood as the last place is three times as likely, one a short walk
away twice, so a day moves on around the corner instead of across town.
"""
from datetime import date

from companion.world import catalog, generators

# The composer's place kinds for each part of the day (companion/life/world.py).
BY_PART = {'morning': ('attraction', 'museum', 'park', 'market'),
           'afternoon': ('attraction', 'waterfront', 'beach', 'museum', 'park', 'shop'),
           'evening': ('restaurant', 'bar'), 'late': ('bar', 'restaurant')}
SAME, CLOSE, ELSEWHERE = 3.0, 2.0, 1.0
NEAR_KM = 1.5


def pick(world, city: str, part: str, day: date, seed: str, *, after=None, used=(), kinds=None):
    """A Place for `part` of `day` in `city`, or None when the city has none. `after` is the Place they were just
    at, `used` the ids of places already visited."""
    places = world.places(city, kinds or BY_PART[part], day_part=part, day=day)
    fresh = [place for place in places if place.id not in set(used)] or places
    if not fresh:
        return None
    weights = closeness(world, city, after, fresh) if after else None
    return generators.pick(seed, 'next-place', fresh, weights)


def closeness(world, city: str, after, places: list) -> list[float]:
    """A weight for each place by how close its neighbourhood is to the one `after` is in."""
    find = getattr(world, 'find', None)
    data = find(city) if find else None
    hoods = {hood['name']: hood for hood in (data or {}).get('neighborhoods', ()) if 'lat' in hood}
    start = hoods.get(after.neighborhood)
    weights = []
    for place in places:
        if place.neighborhood == after.neighborhood:
            weights.append(SAME)
        elif start and place.neighborhood in hoods and catalog.distance_km(start, hoods[place.neighborhood]) <= NEAR_KM:
            weights.append(CLOSE)
        else:
            weights.append(ELSEWHERE)
    return weights
