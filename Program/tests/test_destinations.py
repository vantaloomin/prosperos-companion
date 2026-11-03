"""Places to go away together (companion/world/destinations.py) and the next place to go (companion/life/next_place.py):
the banks are big enough and well formed, every destination fills a trip's days in the style it is visited in, and a
trip fits its era and its ship (Vanta, 2026-11-03)."""
from datetime import date
from zoneinfo import ZoneInfo

import pytest

from companion.life import next_place
from companion.life.world import Place, StaticWorld
from companion.world import catalog, destinations, source

PARTS = ('morning', 'afternoon', 'evening', 'late')
CHARACTERS = {'coast', 'islands', 'old-town', 'big-city', 'mountains', 'lakes', 'countryside', 'wine', 'desert',
              'space'}
# A city to leave from in each style of our world, and the year it is in.
REAL_HOMES = {'modern': 'chicago', 'interwar': 'new-york-1925', 'victorian': 'london-1895', 'frontier': 'whitlock'}
WORLD = source.CatalogWorld()


def home(city_id: str) -> dict:
    return catalog.city(city_id)


def summer_day(year: int | None) -> date:
    return date(year or 2026, 7, 11)


def fills_a_day(city_id: str, year: int | None) -> bool:
    day = summer_day(year)
    return all(WORLD.places(city_id, next_place.BY_PART[part], day_part=part, day=day) for part in PARTS)


# --- The banks ---

def test_banks_have_at_least_a_hundred_entries_per_category():
    assert len(destinations.bank()) >= 100
    for category, items in destinations.templates().items():
        assert len(items) >= 100, category


def test_bank_entries_are_well_formed():
    zones = destinations.climates()
    ids = [item['id'] for item in destinations.bank()]
    assert len(ids) == len(set(ids))
    for item in destinations.bank():
        ZoneInfo(item['timezone'])
        assert item['climate'] in zones, item['id']
        assert set(item['character']) <= CHARACTERS and item['character'], item['id']
        assert -90 <= item['lat'] <= 90 and -180 <= item['lon'] <= 180, item['id']
        assert item['sights'] and all(sight['kind'] in destinations.DAY_PARTS for sight in item['sights'])
        assert set(item['best_months']) <= set(range(1, 13)) and item['best_months'], item['id']


def test_climate_zones_have_twelve_months():
    for zone, data in destinations.climates().items():
        assert len(data['months']) == 12, zone


def test_place_templates_name_known_styles_kinds_and_characters():
    styles = set(destinations.STYLES)
    for category, items in destinations.templates().items():
        for item in items:
            assert destinations.styles_of(item['styles']) <= styles and item['styles'], item['name']
            assert set(item['where']) <= CHARACTERS, item['name']
            assert item['kind'] in destinations.DAY_PARTS, item['name']
            assert set(item.get('parts') or ()) <= set(PARTS), item['name']


def test_every_style_has_getaways():
    for style in destinations.STYLES:
        found = [item for item in destinations.getaways() if style in destinations.styles_of(item['styles'])]
        assert found or style in REAL_HOMES and style != 'frontier', style


# --- Eras and ships ---

@pytest.mark.parametrize('style, city_id', list(REAL_HOMES.items()))
def test_our_world_goes_to_real_places_that_were_getaways_then(style, city_id):
    start = home(city_id)
    year = destinations.year_of(start)
    assert destinations.style(start, year) == style
    found = [item for item in destinations.options(start, year) if item['key'].startswith('b-')]
    assert found
    for item in found:
        real = next(entry for entry in destinations.bank() if f'b-{entry["id"]}' == item['key'])
        assert real['since'] <= year


def test_a_1925_world_has_no_cancun_and_a_medieval_one_no_italy():
    assert destinations.lookup('a week in Cancún?', home('new-york-1925')) == {'options': [], 'why': 'not-yet'}
    assert destinations.lookup('take me to Italy', home('camelot')) == {'options': [], 'why': 'elsewhere'}
    assert destinations.lookup('take me to Italy', home('long-meridian')) == {'options': [], 'why': 'elsewhere'}


def test_a_country_names_every_destination_in_it_and_a_name_beats_it():
    italy = destinations.lookup('long weekend in Italy?', home('chicago'))['options']
    assert {'Rome', 'Florence', 'Venice', 'Tuscany'} <= {item['name'] for item in italy}
    assert [item['name'] for item in destinations.lookup('Rome, Italy!', home('chicago'))['options']] == ['Rome']
    assert destinations.lookup('how was your day', home('chicago')) == {'options': [], 'why': None}


def test_ships_only_go_to_ship_getaways():
    ship = home('long-meridian')
    found = destinations.options(ship)
    assert found and all(item['key'].startswith('g-') and 'lat' not in item for item in found)
    for item in found:
        city = destinations.city(destinations.stand_in_id(item, ship))
        assert city['enclosed'] is True and city['climate'] is None
        assert WORLD.weather(city['id'], date(2026, 1, 1)) is None
        names = {place['name'] for place in city['places']}
        assert names and not names & {'the beach', 'the old harbour', 'a seafood place by the harbour'}


def test_made_up_worlds_get_getaways_of_their_own_style():
    for city_id in ('camelot', 'grandport', 'calderwick'):
        start = home(city_id)
        found = destinations.options(start)
        assert found and all(item['key'].startswith('g-') for item in found)
        chosen = destinations.style(start)
        for item in found:
            getaway = next(entry for entry in destinations.getaways() if f'g-{entry["id"]}' == item['key'])
            assert chosen in destinations.styles_of(getaway['styles'])


def test_stand_in_places_fit_their_year():
    modern_only = {item['name'] for items in destinations.templates().values() for item in items
                   if destinations.styles_of(item['styles']) <= {'modern'}}
    start = home('new-york-1925')
    for item in destinations.options(start)[:40]:
        city = destinations.city(destinations.stand_in_id(item, start))
        assert not {place['name'] for place in city['places']} & modern_only, item['name']
    later = [template for items in destinations.templates().values() for template in items
             if (template.get('since') or 0) > 1925]
    city = destinations.city(destinations.stand_in_id(destinations.lookup('Atlantic City', start)['options'][0],
                                                      start))
    assert not {place['name'] for place in city['places']} & {template['name'] for template in later}


# --- Every destination fills a trip's days ---

@pytest.mark.parametrize('style, city_id', list(REAL_HOMES.items()))
def test_every_real_destination_fills_each_part_of_the_day(style, city_id):
    start = home(city_id)
    year = destinations.year_of(start)
    for item in destinations.options(start, year):
        assert fills_a_day(destinations.stand_in_id(item, start, year), year), (style, item['name'])


@pytest.mark.parametrize('city_id', ['camelot', 'grandport', 'calderwick', 'long-meridian'])
def test_every_getaway_fills_each_part_of_the_day(city_id):
    start = home(city_id)
    for item in destinations.options(start):
        assert fills_a_day(destinations.stand_in_id(item, start), None), item['name']


def test_a_place_nobody_knows_still_makes_a_trip():
    item = destinations.unknown('the cabin by the lake')
    assert item['character'] == ['lakes', 'mountains']
    city_id = destinations.stand_in_id(item, home('chicago'))
    assert destinations.city(city_id)['name'] == 'the cabin by the lake'
    assert fills_a_day(city_id, 2026)
    assert destinations.journey(home('chicago'), item) == {'by': 'plane', 'hours': 9.0}


# --- Stand-ins as cities ---

def test_a_stand_in_id_always_gives_the_same_city():
    start = home('chicago')
    item = destinations.lookup('Lisbon', start)['options'][0]
    city_id = destinations.stand_in_id(item, start)
    assert city_id.startswith('away:modern:') and city_id.endswith(':b-lisbon')
    destinations.city.cache_clear()
    first = destinations.city(city_id)
    destinations.city.cache_clear()
    assert destinations.city(city_id) == first
    assert first['name'] == 'Lisbon' and first['timezone'] == 'Europe/Lisbon'
    assert {'Belém Tower', 'the Tram 28 ride'} <= {place['name'] for place in first['places']}
    assert destinations.city('away:modern:2026:b-nowhere') is None
    assert destinations.city('away:sideways:2026:b-lisbon') is None


def test_the_world_source_answers_for_a_stand_in():
    start = home('london-1895')
    city_id = destinations.stand_in_id(destinations.lookup('Bath', start)['options'][0], start)
    assert WORLD.find(city_id)['name'] == 'Bath'
    assert WORLD.happenings(city_id, date(1895, 7, 6)) == [] and WORLD.changes(city_id, date(1895, 7, 6)) == []
    weather = WORLD.weather(city_id, date(1895, 7, 6))
    assert weather['season'] == 'summer' and weather['high_f'] > 60
    museums = WORLD.places(city_id, ['museum'], day_part='morning', day=date(1895, 7, 6))
    assert 'the Roman Baths' in {place.name for place in museums}


def test_south_of_the_equator_the_seasons_turn():
    start = home('chicago')
    sydney = destinations.city(destinations.stand_in_id(destinations.lookup('Sydney', start)['options'][0], start))
    assert sydney['climate']['months'][0]['high_f'] > sydney['climate']['months'][6]['high_f']


# --- Getting there ---

def test_journeys_follow_the_era():
    chicago, new_york, london = home('chicago'), home('new-york-1925'), home('london-1895')
    rome = destinations.journey(chicago, destinations.lookup('Rome', chicago)['options'][0])
    assert rome['by'] == 'plane' and destinations.nights(rome) == 5
    paris = destinations.journey(new_york, destinations.lookup('Paris', new_york)['options'][0])
    assert paris['by'] == 'steamship' and destinations.nights(paris) is None
    bath = destinations.journey(london, destinations.lookup('Bath', london)['options'][0])
    assert bath['by'] == 'train' and destinations.nights(bath) == 2
    deck = destinations.journey(home('long-meridian'), destinations.options(home('long-meridian'))[0])
    assert deck['by'] in ('tram', 'lift') and destinations.nights(deck) == 2


def test_a_week_abroad_costs_more_than_a_weekend_drive():
    weekend = destinations.cost_share({'by': 'car', 'hours': 3}, 2)
    week = destinations.cost_share({'by': 'plane', 'hours': 10}, 7)
    assert 0 < weekend < week < 0.5
    assert destinations.cost_share({'by': 'tram', 'hours': 1}, 2) == destinations.STAY_SHARE[2]


# --- The next place ---

def place(ident: str, kind: str, hood: str) -> Place:
    return Place(ident, ident, kind, 'town', hood)


def test_the_next_place_is_new_and_close_by():
    world = StaticWorld([place('a', 'bar', 'north'), place('b', 'bar', 'south'), place('c', 'bar', 'north')])
    day = date(2026, 7, 11)
    picks = [next_place.pick(world, 'town', 'evening', day, f'seed-{n}', after=place('x', 'park', 'north'),
                             used=['a']).id for n in range(60)]
    assert 'a' not in picks
    assert picks.count('c') > picks.count('b')
    assert next_place.pick(world, 'town', 'evening', day, 's', used=['a', 'b', 'c']) is not None
    assert next_place.pick(world, 'elsewhere', 'evening', day, 's') is None
