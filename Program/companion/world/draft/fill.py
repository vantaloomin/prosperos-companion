"""Fill a drafted place's neighbourhoods with places, employers, career hubs, a college, transit, yearly events,
local colour and weather, every choice from the banks and the seed."""
from companion.world import generators
from companion.world.draft import banks

SOURCE = 'draft-table'
FOOD = ('restaurant', 'cafe', 'bar', 'tavern', 'inn', 'market', 'nightlife')
# Places each neighbourhood starts with, by the size of the place.
PER_HOOD = {'tiny': 4, 'small': 5, 'town': 6, 'large': 6, 'huge': 7}
EMPLOYER_ROLES = {'works': 2, 'centre': 2, 'harbour': 1, 'learning': 1, 'wealthy': 1, 'market': 1, 'riverside': 1,
                  'green': 1, 'outskirts': 1, 'nightlife': 1, 'homes': 1, 'temple': 1, 'poor': 1, 'old-quarter': 1,
                  'lakeside': 1}
HUB_ROLES = ('works', 'centre', 'harbour', 'learning', 'market', 'riverside')
HUB_WORDS = {'old': 'workshops', '1800s': 'works', '1920s': 'district', 'modern': 'business district',
             'future': 'work decks'}
COLLEGES = {
    'old': ('guild-school', '{city} grammar school', ['latin', 'reckoning', 'letters']),
    '1800s': ('technical-institute', '{city} Mechanics\' Institute', ['engineering', 'evening-classes', 'drawing']),
    '1920s': ('liberal-arts-college', '{city} College', ['liberal-arts', 'football', 'teaching']),
    'modern': ('public-university', '{city} State University', ['nursing', 'business', 'marine-science']),
    'future': ('academy', 'The {city} Academy', ['engineering', 'navigation', 'life-sciences']),
}
# Twelve months of high and low (°F) and rain days for each climate, northern hemisphere.
CLIMATES = {
    'temperate': ([40, 43, 51, 62, 72, 80, 85, 83, 76, 64, 53, 43], [25, 27, 34, 43, 53, 62, 67, 66, 58, 47, 38, 29],
                  [11, 10, 11, 11, 12, 10, 9, 9, 9, 9, 10, 11],
                  'Four real seasons: cold winters with some snow, a green wet spring, warm summers and a long golden fall.'),
    'cold': ([22, 26, 35, 48, 61, 70, 75, 72, 63, 50, 37, 26], [5, 8, 18, 31, 42, 51, 57, 55, 46, 35, 24, 11],
             [12, 10, 11, 11, 12, 11, 11, 11, 11, 12, 13, 13],
             'Long hard winters of snow and ice, a short bright summer and dark afternoons from November to March.'),
    'desert': ([64, 68, 74, 82, 91, 100, 101, 99, 95, 85, 73, 64], [38, 41, 46, 52, 61, 70, 76, 75, 69, 57, 45, 38],
               [3, 3, 3, 1, 1, 1, 8, 8, 4, 3, 2, 3],
               'Dry and sunny all year, blazing summers with thunderstorms in July and August, cold clear desert nights.'),
    'tropical': ([83, 84, 85, 87, 88, 89, 90, 90, 89, 88, 86, 84], [72, 72, 73, 74, 76, 77, 77, 77, 77, 76, 74, 73],
                 [8, 7, 7, 8, 14, 17, 16, 17, 18, 15, 10, 8],
                 'Hot and humid all year, a dry season of blue skies and a wet season of afternoon downpours.'),
    'warm': ([57, 60, 63, 68, 74, 81, 87, 87, 82, 73, 64, 58], [42, 43, 46, 50, 56, 62, 66, 66, 62, 55, 48, 43],
             [9, 8, 8, 6, 4, 2, 1, 1, 3, 6, 8, 9],
             'Mild wet winters and long hot dry summers, the kind of weather people move to.'),
    'highland': ([33, 36, 43, 53, 63, 71, 77, 75, 67, 56, 43, 35], [15, 17, 24, 32, 41, 48, 53, 52, 44, 34, 25, 18],
                 [10, 10, 12, 13, 14, 13, 12, 12, 11, 10, 10, 10],
                 'Mountain weather: snowy winters, sudden storms, cool summer nights and air like cold water.'),
}


def pick(seed: str, label: str, items: list):
    return generators.pick(seed, label, items)


def kinds_for(entry: dict, size: str) -> list[str]:
    wanted, count = list(entry['places']), PER_HOOD[size]
    while len(wanted) < count:
        wanted.append(entry['places'][len(wanted) % len(entry['places'])])
    wanted = wanted[:count]
    if not set(wanted) & set(FOOD):
        wanted[-1] = next((kind for kind in entry['places'] if kind in FOOD), 'restaurant')
    return wanted


def place_record(entry: dict, hood: dict, namer, city: str) -> dict:
    defaults = banks.kinds().get(entry['kind'], banks.kinds()['attraction'])
    name = namer.name(entry['names'], hood=hood['name'], city=city)
    record = {'id': namer.id(name), 'name': name, 'kind': entry['kind'], 'neighborhood': hood['id'],
              'summary': namer.fill(entry['summary'], hood=hood['name'], city=city), 'tags': entry.get('tags', [])[:10]}
    for key in ('cost', 'setting', 'good_for', 'day_parts'):
        record[key] = entry.get(key, defaults[key])
    record['seasons'] = entry.get('seasons', [])
    record['cuisine'] = entry.get('cuisine', '')
    return record | {'source': SOURCE}


def places(hoods: list[dict], brief: dict, namer, city: str, seed: str) -> list[dict]:
    """Each neighbourhood's places, by the kinds its bank entry lists; a kind the era lacks is swapped for a place
    to eat or drink, and no bank entry is used twice while another of its kind is left."""
    pool, used, found = banks.places(brief), set(), []
    for hood in hoods:
        for slot, kind in enumerate(kinds_for(hood['entry'], brief['size'])):
            options = [entry for entry in pool if entry['kind'] == kind] or \
                [entry for entry in pool if entry['kind'] in FOOD]
            fresh = [entry for entry in options if id(entry) not in used] or options
            entry = pick(seed, f'place:{hood["id"]}:{slot}', fresh)
            used.add(id(entry))
            found.append(place_record(entry, hood, namer, city))
    return found


def hired(entry: dict, offered: dict, seed: str) -> list[str]:
    jobs = sorted(key for key, career in offered.items() if career['sector'] in entry['sectors'])
    weights = dict.fromkeys(jobs, 1.0)
    chosen = []
    while weights and len(chosen) < 4:
        key = generators.rank_pick(seed, f'career:{len(chosen)}', weights)
        chosen.append(key)
        weights.pop(key)
    return sorted(chosen)


def employers(hoods: list[dict], brief: dict, namer, city: str, offered: dict, seed: str) -> list[dict]:
    """Employers for each neighbourhood its role calls for, each hiring the place's careers of its sectors."""
    pool = [entry for entry in banks.entries('employers', brief) if hired(entry, offered, seed)]
    used, found = set(), []
    for hood in hoods:
        for slot in range(EMPLOYER_ROLES.get(hood['role'], 1)):
            options = [entry for entry in pool if hood['role'] in entry['roles'] and id(entry) not in used]
            if not options:
                break
            entry = pick(seed, f'employer:{hood["id"]}:{slot}', options)
            used.add(id(entry))
            name = namer.name(entry['names'], hood=hood['name'], city=city)
            found.append({'id': namer.id(name), 'name': name, 'sector': entry['sectors'][0],
                          'neighborhood': hood['id'], 'size': entry['size'],
                          'summary': namer.fill(entry['summary'], hood=hood['name'], city=city),
                          'careers': hired(entry, offered, f'{seed}:{name}'), 'source': SOURCE})
    return found


def hubs(hoods: list[dict], jobs: list[dict], brief: dict, namer) -> list[dict]:
    """A career hub for each working neighbourhood with employers, naming the sectors found there."""
    word, found = HUB_WORDS[brief['group']], []
    for hood in hoods:
        here = [job for job in jobs if job['neighborhood'] == hood['id']]
        if not here or (hood['role'] not in HUB_ROLES and found):
            continue
        name = f'{hood["name"]} {word}'
        found.append({'id': namer.id(name), 'name': name, 'neighborhoods': [hood['id']],
                      'sectors': sorted({job['sector'] for job in here}),
                      'summary': f'Where people work in {hood["name"]}: ' + ', '.join(job['name'] for job in here[:3]) + '.',
                      'source': SOURCE})
    return found


def colleges(hoods: list[dict], brief: dict, namer, city: str) -> list[dict]:
    learning = next((hood for hood in hoods if hood['role'] == 'learning'), None)
    if not learning:
        return []
    kind, pattern, known = COLLEGES[brief['group']]
    name = namer.name([pattern], city=city)
    size = 'large' if brief['size'] in ('large', 'huge') else 'small'
    return [{'id': namer.id(name), 'name': name, 'type': kind, 'neighborhood': learning['id'], 'size': size,
             'known_for': known, 'source': SOURCE}]


def transit(brief: dict, namer, city: str) -> tuple[list[dict], dict[str, float]]:
    """The ways of getting about the era allows, one of each kind, with the city's speeds."""
    lines, speeds, kinds = [], {}, set()
    for entry in banks.entries('transit', brief):
        if entry['kind'] in kinds or brief['hoods'] < entry.get('min_hoods', 0):
            continue
        kinds.add(entry['kind'])
        name = namer.name(entry['names'], city=city)
        lines.append({'id': namer.id(name), 'name': name, 'kind': entry['kind'],
                      'summary': namer.fill(entry['summary'], city=city), 'source': SOURCE})
        speeds[entry['kind']] = entry['speed']
    return lines, speeds


def lines_for(hood: dict, lines: list[dict]) -> list[str]:
    """Walking everywhere, and every line but the boats and ferries, which serve only the waterside."""
    water = hood['role'] in ('harbour', 'riverside', 'lakeside')
    return [line['id'] for line in lines
            if water or line['kind'] not in ('boat', 'ferry', 'water-taxi')][:8]


def where(entry: dict, hoods: list[dict]) -> dict | None:
    return next((hood for hood in hoods if hood['role'] in entry.get('roles', ())), None)


def events(hoods: list[dict], brief: dict, namer, city: str, seed: str) -> list[dict]:
    pool = banks.entries('events', brief)
    count = min(len(pool), brief['hoods'] + 5)
    chosen = sorted(pool, key=lambda entry: generators.unit(seed, 'event', entry['names'][0]))[:count]
    found = []
    for entry in sorted(chosen, key=lambda entry: entry['months'][0]):
        hood = where(entry, hoods)
        name = namer.name(entry['names'], city=city)
        found.append({'id': namer.id(name), 'name': name, 'months': entry['months'],
                      'neighborhood': hood['id'] if hood else None,
                      'summary': namer.fill(entry['summary'], city=city), 'source': SOURCE})
    return found


def colour(hoods: list[dict], brief: dict, namer, city: str, seed: str) -> list[dict]:
    pool = banks.entries('colour', brief)
    chosen = sorted(pool, key=lambda entry: generators.unit(seed, 'colour', entry['names'][0]))[:16]
    found = []
    for entry in chosen:
        hood = where(entry, hoods)
        name = namer.fill(entry['names'][0], city=city)
        found.append({'id': namer.id(name, 'colour'), 'name': name, 'kind': entry['kind'],
                      'summary': namer.fill(entry['summary'], city=city, hood=hood['name'] if hood else city),
                      'places': [hood['id']] if hood else [], 'seasons': entry.get('seasons', []), 'source': SOURCE})
    return found


def climate(brief: dict) -> dict | None:
    """Weather for the place's climate, none aboard (the app gives a ship its own steady climate)."""
    if brief['aboard']:
        return None
    highs, lows, rain, summary = CLIMATES[brief['biome']]
    months = [{'high_f': high, 'low_f': low, 'rain_days': days} for high, low, days in zip(highs, lows, rain)]
    return {'summary': summary, 'months': months, 'source': SOURCE}
