"""The shipped city data as the life simulation's world source (see companion/life/world.py)."""
from datetime import date
from typing import Sequence

from companion.life.world import Place
from companion.world import catalog, custom
from companion.world.generators import SEASONS, conditions

# The composer's place kinds, answered from this data's place kinds (and tags, for waterfronts and books).
KINDS = {
    'park': ('park', 'garden', 'trail'), 'cafe': ('cafe',), 'restaurant': ('restaurant', 'tavern', 'inn'),
    'bar': ('bar', 'nightlife', 'tavern'), 'museum': ('museum',), 'attraction': ('attraction', 'landmark'),
    'market': ('market',), 'grocery': ('market',), 'library': ('library',), 'gym': ('fitness',),
    'beach': ('beach',), 'venue': ('venue', 'stadium'), 'shop': ('shopping',),
}
TAGGED = {'waterfront': {'waterfront', 'harbour', 'harbor', 'docks', 'beach'}, 'bookstore': {'books', 'bookshop'}}


class CatalogWorld:
    """Built-in cities, plus the user's own when given the workspace database."""
    name = 'catalog'

    def __init__(self, database=None):
        self.database = database

    def find(self, city: str) -> dict | None:
        extra = custom.read(self.database) if self.database else {}
        if city in catalog.cities() or city in extra:
            return catalog.city(city, extra)
        match = catalog.resolve(city, extra)
        return catalog.city(match['city'], extra) if match else None

    def weather(self, city: str, day: date) -> dict | None:
        """Typical weather for the date from the city's monthly climate, the same for everyone there."""
        data = self.find(city)
        return conditions(data, day) if data else None

    def places(self, city: str, kinds: Sequence[str], *, day_part: str | None = None,
               day: date | None = None) -> list[Place]:
        """Places of these kinds, open at `day_part` (morning, afternoon, evening, late) and in season on `day`."""
        data = self.find(city)
        if not data:
            return []
        season = SEASONS[day.month] if day else None
        hoods = {hood['id']: hood['name'] for hood in data['neighborhoods']}
        result, seen = [], set()
        for kind in kinds:
            matches = [item for item in data['places'] if (item['kind'] in KINDS.get(kind, ())
                       or set(item['tags']) & TAGGED.get(kind, set()))
                       and (day_part is None or day_part in item['day_parts'])
                       and (season is None or not item['seasons'] or season in item['seasons'])]
            if kind == 'college':
                matches = data['colleges']
            for item in matches:
                if item['id'] not in seen:
                    seen.add(item['id'])
                    result.append(Place(item['id'], item['name'], kind, data['name'], hoods[item['neighborhood']],
                                        tuple(item.get('tags', ()))))
        return result
