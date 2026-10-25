"""Read one line ("a cold fishing town on a northern coast, 1920s") into what the builder needs: era, size, climate,
water, whether it is a ship, a name if the line gives one, and the built-in city it sits near.

Rules only, no model: words the line uses pick each choice, and whatever the line leaves out is picked for the
user from the seed, so any line (even an empty one) builds a place.
"""
import re

from companion.world import catalog, generators, ships

ERA_WORDS = {
    'future': ('future', 'futuristic', 'outer space', 'in space', 'spaceship', 'starship', 'orbital', 'colony', 'cyberpunk', 'sci-fi',
               'scifi', 'mars', 'martian', 'lunar', 'moonbase', 'moon base', 'android', 'androids', 'robot', 'robots', 'galactic',
               'interstellar', 'starbase', 'asteroid'),
    'steampunk': ('steampunk', 'clockwork', 'airship', 'airships', 'brass', 'steam-powered', 'dirigible', 'automaton'),
    'frontier': ('frontier', 'wild west', 'old west', 'western', 'cowboy', 'cowboys', 'gold rush', 'prairie',
                 'boomtown', 'saloon', 'homestead', 'homesteaders', 'ranch', 'territory', 'outlaw', 'outlaws'),
    'jazz-age': ('jazz', 'twenties', 'prohibition', 'speakeasy', 'speakeasies', 'roaring', 'flapper', 'gatsby'),
    'victorian': ('victorian', 'gaslight', 'gaslit', 'dickensian', 'regency', 'edwardian'),
    'fantasy': ('fantasy', 'elf', 'elves', 'elven', 'dwarf', 'dwarves', 'dwarven', 'wizard', 'wizards', 'magic',
                'magical', 'dragon', 'dragons', 'fairy', 'fairies', 'fae', 'enchanted', 'realm', 'orc', 'orcs',
                'halfling', 'halflings', 'sorcery', 'witch', 'witches', 'fairytale', 'fairy-tale'),
    'medieval': ('medieval', 'middle ages', 'castle', 'knight', 'knights', 'feudal', 'manor', 'abbey', 'monastery',
                 'crusade', 'viking', 'vikings', 'norman', 'saxon'),
    'modern': ('modern', 'today', 'present-day', 'present day', 'contemporary', 'nowadays', 'suburb', 'suburban'),
}
# A year or decade in the line ("1920s", "1895", "2150"): the era it falls in, by the first year of each.
YEARS = ((2040, 'future'), (1940, 'modern'), (1910, 'jazz-age'), (1650, 'victorian'), (0, 'medieval'))
YEAR = re.compile(r'\b(\d{3,4})(?:s|\'s)?\b')
WESTERN = ('west', 'western', 'frontier', 'prairie', 'territory', 'cowboy', 'ranch')
SIZES = {
    'tiny': ('hamlet', 'tiny', 'village', 'outpost', 'hideaway'),
    'small': ('small', 'little', 'quiet', 'sleepy'),
    'large': ('city', 'big', 'busy', 'bustling', 'large'),
    'huge': ('metropolis', 'capital', 'megacity', 'sprawling', 'huge', 'vast'),
}
# Neighbourhoods (decks aboard) each size starts with.
SIZE_HOODS = {'tiny': 4, 'small': 6, 'town': 7, 'large': 10, 'huge': 13}
WATER_WORDS = {
    'sea': ('sea', 'coast', 'coastal', 'harbour', 'harbor', 'port', 'bay', 'seaside', 'beach', 'island', 'fishing',
            'cove', 'shore', 'ocean', 'seafront', 'whaling', 'lighthouse', 'cliff', 'cliffs', 'docks'),
    'river': ('river', 'riverside', 'canal', 'mill', 'mills', 'ford', 'bridge', 'bridges', 'valley', 'delta'),
    'lake': ('lake', 'lakeside', 'loch', 'lakeshore', 'mere'),
}
BIOME_WORDS = {
    'cold': ('cold', 'northern', 'snow', 'snowy', 'arctic', 'frozen', 'icy', 'fjord', 'tundra', 'frosty', 'polar',
             'boreal', 'winter'),
    'desert': ('desert', 'dry', 'dusty', 'arid', 'sand', 'sandy', 'canyon', 'mesa', 'dune', 'dunes', 'oasis'),
    'tropical': ('tropical', 'jungle', 'caribbean', 'humid', 'palm', 'palms', 'rainforest', 'monsoon', 'equatorial'),
    'warm': ('southern', 'sunny', 'mediterranean', 'warm', 'vineyard', 'vineyards', 'olive', 'citrus', 'balmy'),
    'highland': ('mountain', 'mountains', 'alpine', 'highland', 'highlands', 'peak', 'peaks', 'hill', 'hills',
                 'moor', 'moorland'),
}
# Climates picked when the line names none: mostly temperate, out west mostly dry.
BIOMES = {'temperate': 6, 'cold': 1, 'warm': 1}
ERA_BIOMES = {'frontier': {'desert': 3, 'temperate': 1}}
SURPRISE = {'modern': 4, 'jazz-age': 1, 'victorian': 1, 'steampunk': 1, 'frontier': 1, 'medieval': 1, 'fantasy': 2,
            'future': 2}
# What the builder fills an era with: its bank group (several eras share one) and the built-in city whose careers,
# money, holidays and names it starts from, when no city of the era is named in the line.
GROUPS = {'medieval': 'old', 'fantasy': 'old', 'victorian': '1800s', 'steampunk': '1800s', 'frontier': '1800s',
          'jazz-age': '1920s', 'modern': 'modern', 'other': 'modern', 'future': 'future'}
DONORS = {'medieval': 'camelot', 'fantasy': 'ellerbruck', 'victorian': 'london-1895', 'steampunk': 'calderwick',
          'frontier': 'whitlock', 'jazz-age': 'pellmouth', 'future': 'port-vesper', 'aboard': 'long-meridian'}
NAMED = re.compile(r'\b(?:called|named)\s+["“]?([A-Z][\w\'’-]*(?:\s+[A-Z][\w\'’-]*){0,3})')
QUOTED = re.compile(r'["“]([^"”]{2,40})["”]')


def words_in(text: str, words: tuple) -> bool:
    return any(re.search(rf'\b{re.escape(word)}\b', text) for word in words)


def year_of(text: str) -> int | None:
    years = [int(found) for found in YEAR.findall(text) if 400 <= int(found) <= 3000]
    return years[0] if years else None


def said_era(text: str) -> str | None:
    """The era the line names by its words or a year in it, if any."""
    for era, words in ERA_WORDS.items():
        if words_in(text, words):
            return era
    year = year_of(text)
    if year:
        era = next(era for start, era in YEARS if year >= start)
        return 'frontier' if era == 'victorian' and 1840 <= year < 1910 and words_in(text, WESTERN) else era
    return None


def era_of(text: str, seed: str) -> str:
    """The era the line names; a line that names none is set today, and an empty line ("Surprise me") gets an era
    picked."""
    if text:
        return said_era(text) or 'modern'
    return generators.pick(seed, 'era', list(SURPRISE), list(SURPRISE.values()))


def first_match(text: str, table: dict, default):
    return next((key for key, words in table.items() if words_in(text, words)), default)


def name_of(line: str) -> str | None:
    found = NAMED.search(line) or QUOTED.search(line)
    return found.group(1).strip() if found else None


def anchor_of(text: str, era: str, aboard: bool, seed: str) -> str:
    """The built-in city of the same era the place sits near: one the line names (by city, region or country),
    else the era's usual one, else one picked from the era's cities."""
    if aboard:
        return DONORS['aboard']
    same = {key: city for key, city in catalog.cities().items()
            if city['era'] == era and not ships.enclosed(city) and city.get('distribution', 'public') == 'public'}
    for key, city in sorted(same.items()):
        names = (city['name'], city['region'], city['country'], *city.get('aliases', ()))
        if words_in(text, tuple(name.lower() for name in names if len(name) > 3)):
            return key
    if era in DONORS:
        return DONORS[era]
    return generators.pick(seed, 'anchor', sorted(same)) or 'haddon-harbor'


def biome_for(era: str, seed: str) -> str:
    weights = ERA_BIOMES.get(era, BIOMES)
    return generators.pick(seed, 'biome', list(weights), list(weights.values()))


def read(line: str, seed: str) -> dict:
    """What the line asks for, with every gap filled from the seed."""
    text = ' '.join(line.lower().split())
    # A ship or station only in the future: a railway station town in 1880 or a fishing ship stays on the ground.
    aboard = bool(ships.SHIP_WORDS.search(text)) and said_era(text) in (None, 'future') \
        and not words_in(text, ('fishing', 'pirate', 'sailing', 'railway', 'train', 'bus', 'gas', 'petrol'))
    era = 'future' if aboard else era_of(text, seed)
    water = first_match(text, WATER_WORDS, None)
    if water is None and not aboard:
        water = generators.pick(seed, 'water', ['sea', 'river', 'lake', None], [3, 3, 1, 2])
    biome = first_match(text, BIOME_WORDS, None) or biome_for(era, seed)
    size = first_match(text, SIZES, 'town')
    return {'line': line.strip(), 'era': era, 'group': 'future' if aboard else GROUPS[era], 'aboard': aboard,
            'water': None if aboard else water, 'biome': biome, 'size': size, 'hoods': SIZE_HOODS[size],
            'year': year_of(text), 'name': name_of(line), 'anchor': anchor_of(text, era, aboard, seed),
            'donor': DONORS['aboard'] if aboard else DONORS.get(era, 'haddon-harbor')}
