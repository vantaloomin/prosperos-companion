"""The shipped city data as the life simulation's world source (see companion/life/world.py)."""
from typing import Sequence

from companion.life.world import Place
from companion.world import catalog

# The composer's place kinds, answered from this data's place kinds (and tags, for waterfronts and books).
KINDS = {
    'park': ('park', 'garden'), 'cafe': ('cafe',), 'restaurant': ('restaurant', 'tavern', 'inn'),
    'bar': ('bar', 'nightlife', 'tavern'), 'museum': ('museum',), 'attraction': ('attraction', 'landmark'),
    'market': ('market',), 'grocery': ('market',), 'library': ('library',), 'gym': ('fitness',),
    'beach': ('beach',), 'venue': ('venue', 'stadium'), 'shop': ('shopping',),
}
TAGGED = {'waterfront': {'waterfront', 'harbour', 'harbor', 'docks', 'beach'}, 'bookstore': {'books', 'bookshop'}}


class CatalogWorld:
    name = 'catalog'

    def city_id(self, city: str) -> str | None:
        if city in catalog.cities():
            return city
        match = catalog.resolve(city)
        return match['city'] if match else None

    def places(self, city: str, kinds: Sequence[str]) -> list[Place]:
        city_id = self.city_id(city)
        if not city_id:
            return []
        data = catalog.city(city_id)
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
