"""The shipped city data as the life simulation's world source (see companion/life/world.py)."""
from typing import Sequence

from companion.life.world import Place
from companion.world import catalog, custom

# The composer's place kinds, answered from this data's place kinds (and tags, for waterfronts and books).
KINDS = {
    'park': ('park', 'garden'), 'cafe': ('cafe',), 'restaurant': ('restaurant', 'tavern', 'inn'),
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

    def places(self, city: str, kinds: Sequence[str]) -> list[Place]:
        data = self.find(city)
        if not data:
            return []
        hoods = {hood['id']: hood['name'] for hood in data['neighborhoods']}
        result, seen = [], set()
        for kind in kinds:
            matches = [item for item in data['places'] if item['kind'] in KINDS.get(kind, ())
                       or set(item['tags']) & TAGGED.get(kind, set())]
            if kind == 'college':
                matches = data['colleges']
            for item in matches:
                if item['id'] not in seen:
                    seen.add(item['id'])
                    result.append(Place(item['id'], item['name'], kind, data['name'], hoods[item['neighborhood']],
                                        tuple(item.get('tags', ()))))
        return result
