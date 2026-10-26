"""Prospero's Draft Table: build a whole place (a town, a city, a ship or station, a fantasy realm) from one line.

`build("a cold fishing town on a northern coast, 1920s")` reads the line (brief.py), lays out neighbourhoods
(layout.py) and fills them (fill.py) from the data banks in world/data/draft, then takes what the era's built-in
city knows (its careers, money, prices, holidays and names) so the place lives by the same rules as the shipped
ones. Rules and seeds only, no model: the same line and seed always give the same place, and a different seed
gives another. `rolls` redraws one section (say {"employers": 1}) and leaves the rest as they were. The result is
an ordinary city file (schema.City) that Companion opens like any other, and the user changes whatever they like.
"""
import copy
import datetime

from companion.world import catalog, generators
from companion.world.draft import banks, fill, layout
from companion.world.draft import brief as briefs
from companion.world.draft.naming import Namer

SECTIONS = ('name', 'hoods', 'places', 'employers', 'transit', 'events', 'colour')
SIZE_WORDS = {'tiny': 'village', 'small': 'small town', 'town': 'town', 'large': 'city', 'huge': 'great city'}
SHIP_WORDS = {'station': 'Orbital station', 'starbase': 'Starbase', 'colony': 'Colony ship'}
WATER_WORDS = {'sea': 'on the sea', 'river': 'on a river', 'lake': 'by a lake'}
BIOME_WORDS = {'temperate': '', 'cold': 'cold, northern ', 'desert': 'dry, sun-baked ', 'tropical': 'tropical ',
               'warm': 'sunny southern ', 'highland': 'mountain '}
# How far from the era's built-in city a new place sits, in km.
NEAR_KM = (40, 150)


class Draft:
    """One build: the brief, a seed per section and the shared namer."""

    def __init__(self, line: str, seed: str, rolls: dict | None):
        self.line = line
        self.base = f'{" ".join(line.lower().split())}|{seed}'
        self.rolls = rolls or {}
        self.brief = briefs.read(line, self.base)
        self.anchor = catalog.city(self.brief['anchor'])
        self.donor = catalog.city(self.brief['donor'])
        self.namer = Namer(self.seed('names'), self.brief['era'], self.anchor.get('names'), self.brief['group'])

    def seed(self, section: str) -> str:
        return f'{self.base}|{section}|{self.rolls.get(section, 0)}'


def careers(donor: dict) -> list[dict]:
    """The era city's own careers, without the adult ones (the app offers its shared adult careers by itself)."""
    return [copy.deepcopy(career) for career in donor.get('careers', []) if not career.get('adult')]


def offered(data: dict) -> dict:
    return catalog.everyday(catalog.careers_for(data, needs_met=False))


def where(draft: Draft) -> dict:
    """Region, country, time zone and position: near the era's city for a place in our world, a made-up realm or
    colony otherwise, and between the stars for a ship."""
    brief, anchor, seed = draft.brief, draft.anchor, draft.seed('where')
    namer = draft.namer.section(seed)
    if brief['aboard']:
        word = next((label for key, label in SHIP_WORDS.items() if key in brief['line'].lower()), 'Generation ship')
        region = namer.fill(generators.pick(seed, 'region', banks.words()['regions']['future']))
        return {'region': region, 'country': word, 'timezone': 'UTC', 'lat': 0.0,
                'lon': round(-120 + generators.unit(seed, 'lon') * 60, 4)}
    lat, lon = layout.offset(anchor['lat'], anchor['lon'],
                             NEAR_KM[0] + generators.unit(seed, 'km') * (NEAR_KM[1] - NEAR_KM[0]),
                             generators.unit(seed, 'bearing') * 360)
    found = {'region': anchor['region'], 'country': anchor['country'], 'timezone': anchor['timezone'],
             'lat': lat, 'lon': lon}
    if anchor.get('setting') == 'fictional' or brief['group'] == 'future':
        group = 'future' if brief['group'] == 'future' else 'old'
        found['region'] = namer.fill(generators.pick(seed, 'region', banks.words()['regions'][group]), group=group)
        found['country'] = namer.fill(generators.pick(seed, 'realm', banks.words()['realms']), group='old') \
            if group == 'old' else namer.fill('the {star} colony')
    return found


def hoods(draft: Draft, city: str) -> list[dict]:
    brief, seed = draft.brief, draft.seed('hoods')
    namer = draft.namer.section(seed)
    chosen = layout.choose(brief, seed)
    side = generators.pick(seed, 'side', list(layout.SIDES))
    centre = (draft.position['lat'], draft.position['lon'])
    found = []
    for entry, (lat, lon) in zip(chosen, layout.spots(brief, chosen, centre, side, seed)):
        name = namer.name(entry['names'], city=city)
        found.append({'id': namer.id(name), 'name': name, 'summary': namer.fill(entry['summary'], city=city),
                      'vibe': entry['vibe'][:8], 'lat': lat, 'lon': lon, 'rent_tier': entry['rent_tier'],
                      'housing': entry['housing'][:6], 'walkability': entry['walkability'], 'transit': [],
                      'source': fill.SOURCE, 'role': entry['role'], 'entry': entry})
    draft.side = side
    return found


def rents(anchor: dict) -> dict[str, dict]:
    """The era city's typical rent for each tier, so a new place's rents are in the same money and period."""
    found = {}
    for hood in anchor['neighborhoods']:
        if hood.get('rent') and hood['rent_tier'] not in found:
            found[hood['rent_tier']] = hood['rent']
    return found


def summary(draft: Draft, city: str, hood_list: list[dict]) -> str:
    brief = draft.brief
    if brief['aboard']:
        kind = draft.position['country'].lower()
        start = f'{city} is {"an" if kind[0] in "aeiou" else "a"} {kind} of {len(hood_list)} decks'
    else:
        start = f'{city} is a {BIOME_WORDS[brief["biome"]]}{SIZE_WORDS[brief["size"]]}'
        start += f' {WATER_WORDS[brief["water"]]}' if brief['water'] else ''
    names = [running(hood['name']) for hood in hood_list[:4]]
    others = ', '.join(names[1:-1]) + f' and {names[-1]}' if len(names) > 2 else names[-1]
    return f'{start}, with {names[0]} at its heart and {others} round about.'


def running(name: str) -> str:
    """A name as it reads mid-sentence: "the Waterfront", not "The Waterfront"."""
    return 'the' + name[3:] if name.startswith('The ') else name


def city_name(draft: Draft) -> str:
    if draft.brief['name']:
        return draft.brief['name']
    namer = Namer(draft.seed('name'), draft.brief['era'], None)
    return namer.town_name(draft.brief['group'], draft.brief['era'])


def money(data: dict, draft: Draft) -> None:
    """Money, prices, holidays and names from the city the place sits near, careers from the era's city."""
    for key in ('currency', 'rent_period', 'prices', 'calendar', 'holidays', 'names', 'work_by_gender', 'words',
                'kinds'):
        if draft.anchor.get(key) not in (None, [], {}):
            data[key] = copy.deepcopy(draft.anchor[key])
    data['careers'] = careers(draft.donor)
    cited = {item['source'] for item in data.get('prices', [])}
    data['sources'] |= {key: copy.deepcopy(value) for key, value in draft.anchor['sources'].items() if key in cited}


def place(data: dict, draft: Draft, hood_list: list[dict], city: str) -> None:
    brief, namer, seed = draft.brief, draft.namer, draft.seed
    data['places'] = fill.places(hood_list, brief, namer.section(seed('places')), city, seed('places'))
    namer.section(seed('employers'))
    data['employers'] = fill.employers(hood_list, brief, namer, city, offered(data), seed('employers'))
    data['career_hubs'] = fill.hubs(hood_list, data['employers'], brief, namer)
    data['colleges'] = fill.colleges(hood_list, brief, namer, city)
    data['transit'], data['speeds'] = fill.transit(brief, namer.section(seed('transit')), city)
    data['annual_events'] = fill.events(hood_list, brief, namer.section(seed('events')), city, seed('events'))
    data['local_color'] = fill.colour(hood_list, brief, namer.section(seed('colour')), city, seed('colour'))
    data['climate'] = fill.climate(brief)


def finish(data: dict, draft: Draft, hood_list: list[dict]) -> None:
    tiers = rents(draft.anchor)
    for hood in hood_list:
        hood['transit'] = fill.lines_for(hood, data['transit'])
        if hood['rent_tier'] in tiers:
            hood['rent'] = copy.deepcopy(tiers[hood['rent_tier']])
        hood.pop('role')
        hood.pop('entry')
    data['neighborhoods'] = hood_list
    data['water'] = layout.water(draft.brief, (data['lat'], data['lon']), draft.side,
                                 draft.namer.section(draft.seed('hoods') + ':water').fill('the {town} ' + {'sea': 'Sea', 'river': 'River', 'lake': 'Water'}
                                                  .get(draft.brief['water'] or '', ''), group='old'))
    data['enclosed'] = draft.brief['aboard']
    if draft.brief['aboard']:
        hours = 2 + round(generators.unit(draft.seed('where'), 'hours') * 4)
        data['neighbours'] = [{'city': 'port-vesper', 'hours': hours}]
        data['calendar'] = 'none'


def build(line: str, seed: str = '', rolls: dict | None = None, today: str | None = None) -> dict:
    """A whole city definition from one line, plus the brief it was read as."""
    draft = Draft(line, seed, rolls)
    city = city_name(draft)
    draft.position = where(draft)
    hood_list = hoods(draft, city)
    data = {'schema_version': 1, 'id': draft.namer.id(city), 'name': city, 'setting': 'original',
            'era': draft.brief['era'], 'basis': f'Made with Prospero\'s Draft Table from "{line.strip()[:300]}".',
            **{key: draft.position[key] for key in ('region', 'country', 'timezone')},
            'summary': summary(draft, city, hood_list), 'lat': draft.position['lat'], 'lon': draft.position['lon'],
            'sources': {fill.SOURCE: {'kind': 'user', 'title': "Made with Prospero's Draft Table",
                                      'license': 'User content',
                                      'retrieved': today or datetime.date.today().isoformat()}}}
    money(data, draft)
    place(data, draft, hood_list, city)
    finish(data, draft, hood_list)
    data['enclosed'] = draft.brief['aboard'] or (False if draft.brief['era'] == 'future' else None)
    if data['enclosed'] is None:
        data.pop('enclosed')
    return {'city': data, 'brief': {key: value for key, value in draft.brief.items()}}


__all__ = ['build', 'SECTIONS']


def weather_for(city: dict) -> tuple[dict, str]:
    """(the city with weather, what it is called) for a place opened without any: from the words in its name,
    region, realm and summary, then its era, then Mild."""
    if city.get('climate'):
        return city, 'its own weather'
    text = ' '.join(str(city.get(key) or '') for key in ('name', 'region', 'country', 'summary')).lower()
    by_era = briefs.ERA_BIOMES.get(str(city.get('era') or ''), {})
    biome = (briefs.first_match(text, briefs.BIOME_WORDS, None)
             or (max(by_era, key=by_era.get) if by_era else 'temperate'))
    # Cited to the file's own source, so the city's sources list stays as it was.
    source = next(iter(city.get('sources') or {}), fill.SOURCE)
    return {**city, 'climate': {**fill.climate({'aboard': False, 'biome': biome}), 'source': source}}, fill.WEATHER_NAMES[biome]
