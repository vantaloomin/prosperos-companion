"""Pluggable world data for the life simulation.

Events are assembled from the routine and real places, not invented by a model. A world source
answers "which places of these kinds are in this city", and the composer picks among them
deterministically. The city datasets live in their own modules; any object with a matching
`places` method can be passed to `create_app(world=...)`.

Place kinds the composer asks for: park, cafe, restaurant, bar, museum, attraction, market,
grocery, library, college, gym, beach, waterfront, venue, bookstore, shop.
"""
from dataclasses import dataclass, field
from typing import Protocol, Sequence


@dataclass(frozen=True)
class Place:
    id: str
    name: str
    kind: str
    city: str = ''
    neighborhood: str = ''
    tags: tuple[str, ...] = field(default_factory=tuple)

    def view(self) -> dict:
        return {'id': self.id, 'name': self.name, 'kind': self.kind, 'city': self.city,
                'neighborhood': self.neighborhood}


class WorldSource(Protocol):
    name: str

    def places(self, city: str, kinds: Sequence[str]) -> list[Place]:
        """Places of any of these kinds in the city, in a stable order. Unknown cities give []."""


class EmptyWorld:
    """Used until city data is installed: events are composed without named places."""
    name = 'none'

    def places(self, city: str, kinds: Sequence[str]) -> list[Place]:
        return []


class StaticWorld:
    """A fixed list of places, for tests and small hand-made worlds."""
    name = 'static'

    def __init__(self, places: Sequence[Place]):
        self.items = list(places)

    def places(self, city: str, kinds: Sequence[str]) -> list[Place]:
        wanted = set(kinds)
        return [place for place in self.items if place.city == city and place.kind in wanted]
