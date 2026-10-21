"""Ships and stations (companion/world/ships.py): a city that is a ship or a station has no weather, Earth seasons or
cars, its pictures are lit by the ship, the future era has its own work, food, pastimes and savings, and made-up
places travel to each other."""
import copy
from datetime import date
from types import SimpleNamespace

import pytest

from companion.images import prompts
from companion.life import body, hobbies, home, kitchen, money, network, trips, wardrobe
from companion.world import catalog, check, generators, mend, ships

# The built-in ship and the station it flies beside: the only built-in cities that are enclosed.
BUILT_IN_AFLOAT = {'long-meridian', 'port-vesper'}


def city_from(city_id: str, **extra) -> dict:
    """Baltimore's places and people under another name, with `extra` on top, loaded like a city pack."""
    data = {key: value for key, value in copy.deepcopy(catalog.city('baltimore')).items()
            if key not in ('data_version', 'builtin', 'origin', 'pack_file', 'import_notes')}
    return catalog.prepare(data | {'id': city_id, 'name': city_id.replace('-', ' ').title(), 'aliases': [],
                                   'names': None, 'employers': [], 'careers': [], 'notables': []} | extra,
                           mend=True) | {'origin': 'pack'}


def ship(**extra) -> dict:
    return city_from('test-ark', era='future', country='Generation ship', climate=None, setting='original',
                     calendar='none', **extra)


def test_a_future_city_named_as_a_ship_is_enclosed_and_says_so():
    found = ship()
    assert ships.enclosed(found)
    assert any('reads as a ship or station' in note for note in found['import_notes'])
    # Decks or rings for neighbourhoods tell it too.
    hoods = [hood | {'name': f'Deck {index}'} for index, hood in enumerate(catalog.city('baltimore')['neighborhoods'])]
    assert ships.enclosed(city_from('deck-city', era='future', neighborhoods=hoods))
    # The city's own word wins, and today's cities never read as one.
    assert not ships.enclosed(ship(enclosed=False))
    assert not ships.enclosed(city_from('station-town', country='Station'))
    assert {key for key, data in catalog.cities().items() if ships.enclosed(data)} == BUILT_IN_AFLOAT


def test_aboard_there_is_no_weather_season_or_car():
    found = ship()
    # A flat climate stands in, so the wardrobe never shops for an Earth winter, but no day has weather.
    assert {month['high_f'] for month in found['climate']['months']} == {70}
    assert found['climate']['source'] in found['sources']
    assert generators.conditions(found, date(2027, 1, 15)) is None
    assert not set(found['speeds']) & {'car', 'rideshare'}
    assert all(home.vehicle_item(f'seed-{index}', found) is None for index in range(20))
    look = wardrobe.profile('seed', {'name': 'Mira'}, found)
    assert look['aboard'] and look['coldest_f'] == 70
    assert wardrobe.season_need(look, date(2026, 10, 1)) == []
    assert 'aboard' not in wardrobe.profile('seed', {'name': 'Mira'}, catalog.city('baltimore'))

    class World:
        def find(self, _text, _day=None):
            return found

    assert not body.winter(World(), {'home_city': 'Test Ark'}, date(2027, 1, 15))
    assert all(network.occasion_for(f'seed-{index}', date(2026, 7, 4), aboard=True)[0] != 'barbecue'
               for index in range(40))


def test_a_city_that_names_itself_enclosed_keeps_its_own_climate():
    own = {'summary': 'Cold decks.', 'months': [{'high_f': 55, 'low_f': 50, 'rain_days': 0}] * 12,
           'source': 'baltimore-climate'}
    found = city_from('cold-ship', enclosed=True, climate=own | {'source': next(iter(catalog.city('baltimore')[
        'sources']))})
    assert ships.enclosed(found) and found['climate']['months'][0]['high_f'] == 55
    assert generators.conditions(found, date(2027, 1, 15)) is None


def test_the_future_has_a_hundred_careers_of_its_own():
    offered = catalog.careers_for(ship(), needs_met=False)
    assert len(offered) >= 100 and all(career['eras'] == ['future'] for career in offered.values())
    assert not set(offered) & {key for key, career in catalog.careers().items() if 'future' not in career['eras']}
    assert {'hydroponics-technician', 'shuttle-pilot', 'quartermaster', 'clinic-nurse'} <= set(offered)
    # Today's cities offer what they always did.
    assert not {key for key, career in catalog.careers_for(catalog.city('baltimore')).items()
                if 'future' in career['eras']}


def test_future_food_savings_and_pastimes():
    found = ship()
    assert kitchen.bank_for(found) == 'future' and kitchen.modern_bank('future')
    assert len(kitchen.bank('future')['dishes']) >= 100
    assert kitchen.bank_for(catalog.city('baltimore')) == 'modern-us'
    for tier in range(4):
        aboard = SimpleNamespace(city=found, era='modern', tier=tier)
        assert len(money.goals(aboard)) >= 25 and 'a used car' not in money.goals(aboard)
    assert sum(len(tier) for tier in money.ship_goals()) >= 100
    assert not set(money.surprises(SimpleNamespace(city=found, era='modern'))) & money.CAR_BILLS
    assert money.goals(SimpleNamespace(city=catalog.city('baltimore'), era='modern', tier=1)) == \
        money.GOALS['modern'][1]
    # A ship's pastimes: today's and the future's, never one that needs open country or sea.
    offered = [item for item in hobbies.catalogue()['hobbies'] if hobbies.in_era(item['eras'], hobbies.era_of(found))
               and hobbies.fits_city(item, found)]
    assert len(offered) >= 100 and not {item['id'] for item in offered} & hobbies.EARTHBOUND
    picked = {hobbies.choose_new(f'seed-{index}', 'new', {'name': 'Mira'}, found, [])['id'] for index in range(60)}
    assert not picked & hobbies.EARTHBOUND
    assert picked & {item['id'] for item in hobbies.catalogue()['hobbies'] if item['eras'] == ['future']}
    # Today's cities never get the future's pastimes.
    modern = {hobbies.choose_new(f'seed-{index}', 'new', {'name': 'Mira'}, catalog.city('baltimore'), [])['id']
              for index in range(60)}
    assert not modern & {item['id'] for item in hobbies.catalogue()['hobbies'] if item['eras'] == ['future']}


def test_pictures_aboard_are_lit_by_the_ship_and_kept_indoors():
    event = {'summary': 'Mira went for a walk.', 'place': '', 'activity': 'walk', 'hour': 22, 'weather': {'rain': True}}
    aboard = prompts.compose('Mira', 'Short dark hair.', [event], 'Candid photograph', aboard=True)
    assert "ship's night" in aboard and "ship's corridor" in aboard
    assert not any(word in aboard.lower() for word in ('outdoors', 'streetlights', 'rain'))
    ground = prompts.compose('Mira', 'Short dark hair.', [event], 'Candid photograph')
    assert 'outdoors' in ground and 'streetlights' in ground
    assert prompts.ship_light(3).startswith('Corridor lights dimmed') and prompts.ship_light(None) == ''
    assert 'viewport full of stars' in prompts.aboard_words('looking up at a clear night sky full of stars')


@pytest.fixture
def pair():
    """A ship and the station it docks at, which the ship lists; the station lists nothing."""
    station = city_from('test-station', era='future', country='Orbital station', climate=None, calendar='none',
                        setting='original', lat=10.0, lon=-140.0)
    ark = ship(neighbours=[{'city': 'test-station', 'hours': 4}, {'city': 'nowhere', 'hours': 2}])
    return ark, station, {item['id']: item for item in (ark, station)} | catalog.cities()


def test_neighbours_travel_both_ways_and_ships_go_nowhere_else(pair):
    ark, station, known = pair
    assert [city['id'] for city in trips.destinations(ark, 2, known)] == ['test-station']
    assert [city['id'] for city in trips.destinations(station, 2, known)] == ['test-ark']
    assert trips.fits(ark, station) and trips.fits(station, ark)
    # The ship sits by Baltimore on the map, but nobody drives over.
    baltimore = catalog.city('baltimore')
    assert not trips.fits(baltimore, ark) and not trips.fits(ark, baltimore)
    assert 'test-ark' not in {city['id'] for city in trips.destinations(baltimore, 3, known)}
    # Too far for a weekend: no trip.
    far = ship(neighbours=[{'city': 'test-station', 'hours': 30}])
    assert not trips.destinations(far, 3, known)
    assert ships.by(ark, station) == 'shuttle' and ships.by(station, ark) == 'shuttle'


def test_a_listing_can_name_how_people_travel():
    data = {key: value for key, value in copy.deepcopy(catalog.city('grandport')).items()
            if key not in ('data_version', 'builtin', 'origin', 'pack_file', 'import_notes')}
    town = catalog.prepare(data | {'neighbours': [{'city': 'camelot', 'hours': 5, 'by': 'The night train'}]})
    assert ships.by(town, catalog.city('camelot')) == 'night train'
    assert 'camelot' in {city['id'] for city in trips.destinations(town, 2)}


def test_setting_off_and_coming_home_by_shuttle(pair):
    ark, station, known = pair

    class World:
        def find(self, text, _day=None):
            return known.get(text) or {'Test Ark': ark}.get(text)

        def places(self, *_args, **_kwargs):
            return []

    trip = {'id': 't1', 'city_name': station['name'], 'city_id': station['id'], 'kind': 'getaway',
            'company': {'name': 'Sam'}, 'sunny': False}
    slot = {'local_date': '2026-10-17', 'block': {'start': '09:00'}}
    definition = {'name': 'Mira', 'home_city': 'Test Ark'}
    first = trips.entry(trip, slot, definition, World(), 's', 'first')
    last = trips.entry(trip, slot, definition, World(), 's', 'last')
    assert first['summary'] == 'Mira caught the shuttle and docked at Test Station with Sam.'
    assert first['post'] == 'Docking soon!'
    assert last['summary'] == 'Mira caught the shuttle home from Test Station with Sam.'
    # On the ground, trips read as they always did.
    trip_out = trip | {'city_name': 'New York', 'city_id': 'new-york'}
    plain = trips.entry(trip_out, slot, {'name': 'Mira', 'home_city': 'Baltimore'}, World(), 's', 'first')
    assert plain['summary'] == 'Mira set off for New York with Sam.' and plain['post'] == 'Off to New York!'


def test_mending_reads_neighbors_as_neighbours():
    mended, _notes = mend.mend({'neighbors': [{'city': 'camelot', 'hours': 3}]})
    assert mended['neighbours'] == [{'city': 'camelot', 'hours': 3}] and 'neighbors' not in mended


def raw_city(city_id: str, **extra) -> dict:
    data = {key: value for key, value in copy.deepcopy(catalog.city('baltimore')).items()
            if key not in ('data_version', 'builtin', 'origin', 'pack_file', 'import_notes')}
    return data | {'id': city_id, 'name': city_id.replace('-', ' ').title(), 'aliases': [], 'names': None,
                   'employers': [], 'careers': [], 'notables': [], 'era': 'future', 'climate': None,
                   'calendar': 'none', 'setting': 'original'} | extra


def test_a_companion_aboard_a_users_ship_visits_its_station(client, monkeypatch):
    from conftest import reconcile, set_life
    from test_trips import WEEKDAYS
    monkeypatch.setattr(trips, 'ACTIVE', True)
    monkeypatch.setattr(trips, 'CHANCE', 1.0)
    monkeypatch.setattr(trips, 'FAMILY_SHARE', 0.0)
    monkeypatch.setattr(trips, 'cost', lambda *_args: 0.0)
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    for raw in (raw_city('ark-one', country='Generation ship', neighbours=[{'city': 'halcyon-station', 'hours': 3}]),
                raw_city('halcyon-station', country='Orbital station', lat=10.0, lon=-140.0)):
        assert client.post('/api/world/cities', json=raw).status_code == 200
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC', 'schedule': WEEKDAYS,
                                                    'home_city': 'Ark One'})
    assert response.status_code == 200, response.text
    set_life(client, automatic_events=True, phrase_with_model=False, catch_up_max_events=6,
             catch_up_lookback_hours=168)
    reconcile(client)
    found = client.get('/api/life/outings').json()['trips']
    assert found and {trip['city_id'] for trip in found} == {'halcyon-station'}
    preview = client.get('/api/context/preview').json()['prompt']
    assert 'typical weather' not in preview.lower()


def test_the_built_in_ship_flies_beside_its_station_and_is_featured():
    ship_data, station = catalog.city('long-meridian'), catalog.city('port-vesper')
    for data in (ship_data, station):
        assert ships.enclosed(data) and data['era'] == 'future' and catalog.category(data) == 'fictional'
        assert generators.conditions(data, date(2027, 1, 15)) is None
        assert not set(data['speeds']) & set(ships.GROUNDED)
        # Built to the size of the other built-in cities, with somewhere to eat on every deck.
        assert not check.warnings(data)
    assert len(ship_data['places']) >= 80 and len(ship_data['neighborhoods']) >= 12
    # The ship and the station visit each other by shuttle, and nobody else.
    assert [city['id'] for city in trips.destinations(ship_data, 2)] == ['port-vesper']
    assert [city['id'] for city in trips.destinations(station, 2)] == ['long-meridian']
    assert ships.by(ship_data, station) == 'shuttle' and ships.by(station, ship_data) == 'shuttle'
    # Its own work beside the shared future careers, and pastimes and food of the future.
    offered = catalog.careers_for(ship_data, needs_met=False)
    assert {'arboretum-ranger', 'tank-diver', 'hydroponics-technician'} <= set(offered)
    assert kitchen.bank_for(ship_data) == 'future'
    featured = catalog._featured()
    assert featured['cities'][0] == 'long-meridian' and featured['new_cities'] == ['long-meridian']
    assert 'port-vesper' not in featured['cities'] and 'pellmouth' not in featured['cities']


def test_start_from_a_ship_saves_a_ship_that_docks_at_port_vesper(app, client):
    from companion.world import custom
    template = client.get('/api/world/template', params={'kind': 'ship'}).json()
    assert template['enclosed'] is True and template['era'] == 'future'
    checked = client.post('/api/world/validate', json=template).json()
    assert checked['valid'] and not checked['summary'].get('import_notes')
    saved = client.post('/api/world/cities', json=template)
    assert saved.status_code == 200, saved.text
    with app.state.database.connect() as connection:
        known = catalog.cities() | custom.all_cities(connection)
    mine = known['my-ship']
    assert ships.enclosed(mine) and generators.conditions(mine, date(2027, 1, 15)) is None
    assert [city['id'] for city in trips.destinations(mine, 2, known)] == ['port-vesper']
    assert 'my-ship' in {city['id'] for city in trips.destinations(known['port-vesper'], 2, known)}
    listed = {item['id']: item for item in client.get('/api/world/cities').json()}
    assert listed['my-ship']['category'] == 'custom'
    # The plain template stays a city on the ground.
    assert 'enclosed' not in client.get('/api/world/template').json()
    assert client.get('/api/world/template', params={'kind': 'castle'}).status_code == 422


def test_aboard_nobody_misses_the_bus():
    from companion.life import disruptions
    block = {'kind': 'work'}
    found = [disruptions.roll(f'late:{number}', block, aboard=True) for number in range(400)]
    reasons = {shift['reason'] for shift in found if shift and shift['key'] == 'late'}
    assert 'missed the tram' in reasons and not reasons & {'missed the bus', 'traffic was a mess'}


def test_a_pet_aboard_never_sits_in_the_sun_or_by_the_fire():
    from companion.life import pets
    found = {'kind': 'dog', 'era': 'modern', 'name': 'Radish', 'aboard': True}
    told = {pets.moment(found, f'pet:{n}', walking=n % 2 == 0) for n in range(300)}
    told |= {(pets.photo(found, f'pet:{n}') or {}).get('shows') for n in range(300)}
    assert told and not any(pets.EARTHBOUND.search(text or '') for text in told)
    assert any(pets.EARTHBOUND.search(pets.moment({**found, 'aboard': False}, f'pet:{n}', walking=True) or '')
               for n in range(300))


def test_a_family_aboard_hears_nothing_of_snow_beaches_or_car_seats():
    from companion.life import families
    unfit = families.UNFIT['future']
    for key in ('baby_update', 'toddler_update', 'child_update', 'babysit_toddler', 'own_toddler'):
        kept = families.fitting(families.bank()[key], 'future')
        assert len(kept) >= 100 and not any(unfit.search(f"{line['text']} {line['share']}") for line in kept), key
    assert unfit.search('built a snowman in the yard') and not unfit.search('played in the arboretum')
