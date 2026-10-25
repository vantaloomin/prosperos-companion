"""Names for a drafted place: patterns from the banks ("The {emblem}", "{surname}'s forge") filled from the word
banks and the place's own name groups, each draw seeded and labelled so the same line always names the same."""
import re

from companion.world import catalog, generators
from companion.world.draft import banks
from companion.world.mend import slug

SLOT = re.compile(r'\{(\w+)\}')
WORD_SLOTS = {'emblem': 'emblems', 'stem': 'stems', 'saint': 'saints', 'star': 'stars'}


class Namer:
    """Fills name patterns for one place, never giving two records the same name or id."""

    def __init__(self, seed: str, era: str, names: dict | None, group: str = ''):
        self.seed = seed
        self.group = group
        self.count = 0
        self.names = set()
        self.ids = {}
        self.groups, self.mix = catalog.name_groups({'era': era, 'names': names})
        self.town = ''

    def section(self, seed: str) -> 'Namer':
        """Start drawing for one section with its own seed and count, so redrawing a section leaves the names of
        the others as they were."""
        self.seed, self.count = seed, 0
        return self

    def draw(self, label: str, items: list):
        self.count += 1
        return generators.pick(self.seed, f'{label}:{self.count}', items)

    def person(self) -> dict:
        key = generators.pick(self.seed, f'group:{self.count}', sorted(self.mix), [self.mix[k] for k in sorted(self.mix)])
        return self.groups[key]

    def surname(self) -> str:
        return self.draw('surname', self.person()['family'])

    def given(self) -> str:
        group = self.person()
        return self.draw('given', [*group.get('feminine', ()), *group.get('masculine', ()), *group.get('neutral', ())])

    def town_name(self, group: str, era: str) -> str:
        """A made-up name for a town: two parts in the old style, a frontier ending out west, a star name ahead."""
        bank = banks.words()
        if group == 'future':
            return self.draw('star', bank['stars'])
        start = self.draw('start', bank['town_starts'])
        ends = bank['frontier_ends'] if era == 'frontier' and self.draw('west', [0, 1]) else bank['town_ends']
        end = self.draw('end', [end for end in ends if end.strip().lower() not in start.lower()])
        return start + end

    def slot(self, key: str, slots: dict) -> str:
        if key in slots:
            return slots[key]
        if key == 'stem' and self.group == 'future':
            # Ahead, street and place words are star names, not mills and churches.
            return self.draw(key, banks.words()['stars'])
        if key in WORD_SLOTS:
            return self.draw(key, banks.words()[WORD_SLOTS[key]])
        if key == 'town':
            return self.town_name(slots.get('group', 'old'), slots.get('era', ''))
        if key == 'surname':
            return self.surname()
        if key == 'given':
            return self.given()
        return key

    def fill(self, pattern: str, **slots) -> str:
        return SLOT.sub(lambda found: self.slot(found.group(1), slots), pattern)

    def name(self, patterns: list[str], **slots) -> str:
        """A name from the patterns that no other record of the place has, trying a few draws before giving the
        neighbourhood's name to tell two apart."""
        for _ in range(6):
            name = self.fill(self.draw('pattern', patterns), **slots)
            if name.lower() not in self.names:
                break
        else:
            name = f'{name}, {slots["hood"]}' if slots.get('hood') else f'{name} {self.count}'
        self.names.add(name.lower())
        return name

    def id(self, name: str, space: str = 'records') -> str:
        """An id for the name, unique among the place's records (or among its local colour, which has its own)."""
        taken = self.ids.setdefault(space, set())
        base = slug(name) or 'place'
        key, n = base, 2
        while key in taken:
            key, n = f'{base}-{n}', n + 1
        taken.add(key)
        return key
