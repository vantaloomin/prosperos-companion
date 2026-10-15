"""Where you are (companion/life/where.py): the user's own home in each world, and how far it is from a companion's."""
import json

from conftest import send

from companion import worlds
from companion.life import where
from companion.world import catalog


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def listing(client):
    return ok(client.get('/api/worlds'))


def test_the_app_picks_a_home_in_the_worlds_city(client, companion):
    home = listing(client)['world']['home']
    assert home['city_id'] == 'baltimore' and home['set_by'] == 'app'
    hood = where.hood_named(catalog.cities()['baltimore'], home['neighbourhood'])
    assert hood and hood['name'] == home['neighbourhood_name']


def test_an_upgraded_world_gets_a_home_and_keeps_it(client, companion, app):
    database = app.state.database
    data = worlds.load(database.root)
    del data['worlds'][0]['home']  # As before this version.
    worlds.save(database.root, data)
    worlds.start(database)
    first = worlds.load(database.root)['worlds'][0]['home']
    assert first['city_id'] == 'baltimore' and first['neighbourhood']
    worlds.start(database)
    assert worlds.load(database.root)['worlds'][0]['home'] == first
    with database.connect() as connection:
        assert where.your_home(connection)[1]['id'] == first['neighbourhood']


def test_the_neighbourhood_pick_is_seeded_and_ordinary():
    city = catalog.cities()['new-york']
    picks = {where.neighbourhood_for(city, f'world-{index}') for index in range(30)}
    assert where.neighbourhood_for(city, 'world-1') == where.neighbourhood_for(city, 'world-1')
    assert len(picks) > 1
    assert all(where.hood_named(city, hood)['rent_tier'] in ('low', 'mid') for hood in picks)


def test_the_user_can_move_within_the_rules_of_trips(client, companion):
    world = listing(client)['world']
    choices = ok(client.get(f"/api/worlds/{world['id']}/home"))
    ids = [city['id'] for city in choices['cities']]
    assert ids[0] == 'baltimore' and 'london' in ids and 'haddon-harbor' in ids
    # A made-up world's city or another era is out of reach from Baltimore.
    assert 'grandport' not in ids and 'new-york-1925' not in ids
    assert ok(client.get(f"/api/worlds/{world['id']}/home", params={'city_id': 'london'}))['neighbourhoods']
    refused = client.put(f"/api/worlds/{world['id']}/home", json={'city_id': 'grandport'})
    assert refused.status_code == 422
    hood = catalog.cities()['london']['neighborhoods'][2]
    moved = ok(client.put(f"/api/worlds/{world['id']}/home", json={'city_id': 'london', 'neighbourhood': hood['id']}))
    assert moved['world']['home'] == {'city_id': 'london', 'city': 'London', 'region': moved['world']['home']['region'],
                                           'neighbourhood': hood['id'], 'neighbourhood_name': hood['name'],
                                           'set_by': 'you'}
    # A blank neighbourhood is the app's to pick.
    again = ok(client.put(f"/api/worlds/{world['id']}/home", json={'city_id': 'chicago'}))['world']['home']
    assert again['city_id'] == 'chicago' and again['neighbourhood'] and again['set_by'] == 'you'


def test_a_home_the_user_picked_stays_when_the_world_starts_again(client, companion, app):
    world = listing(client)['world']
    ok(client.put(f"/api/worlds/{world['id']}/home", json={'city_id': 'miami'}))
    worlds.start(app.state.database)
    assert listing(client)['world']['home']['city_id'] == 'miami'


def test_the_companion_knows_where_the_user_lives(client, connected, provider):
    world = listing(client)['world']
    hood = catalog.cities()['baltimore']['neighborhoods'][0]
    ok(client.put(f"/api/worlds/{world['id']}/home", json={'city_id': 'baltimore', 'neighbourhood': hood['id']}))
    send(client, 'Hey!', 'first-message')
    assert f"- Lives in: {hood['name']}, Baltimore" in provider.requests[-1]['prompt']


def test_matchlight_looks_where_the_user_lives(client, companion):
    world = listing(client)['world']
    ok(client.put(f"/api/worlds/{world['id']}/home", json={'city_id': 'chicago'}))
    ok(client.put('/api/dating/profile', json={'name': 'Sam', 'age': 31, 'gender': 'man', 'interested_in': ['woman'],
                                              'looking_for': 'serious', 'age_min': 25, 'age_max': 40, 'bio': ''}))
    assert ok(client.get('/api/dating'))['city']['id'] == 'chicago'


def test_a_new_world_has_its_own_home(client, companion, app):
    made = ok(client.post('/api/worlds', json={'city_id': 'osaka'}))
    assert made['home']['city_id'] == 'osaka' and made['home']['set_by'] == 'app'
    switched = ok(client.post(f"/api/worlds/{made['id']}/switch"))
    assert switched['world']['home']['city_id'] == 'osaka'
    with app.state.database.connect() as connection:
        assert where.your_home(connection)[0]['id'] == 'osaka'


def definition(**values):
    return {'name': 'Mira', **values}


def test_same_city_or_long_distance(client, companion, app):
    with app.state.database.connect() as connection:
        same = where.between(connection, definition(location='Fells Point, Baltimore'))
        assert same.known and same.same_city and not same.long_distance and same.km == 0
        apart = where.between(connection, definition(home_city='chicago'))
        assert apart.long_distance and 900 < apart.km < 1100 and apart.within_reach
        far = where.between(connection, definition(home_city='osaka'))
        assert far.long_distance and not far.within_reach
        # A city that can't be told counts as the same one, as before Where you are.
        unknown = where.between(connection, definition(location='somewhere by the sea'))
        assert not unknown.known and unknown.same_city


def test_the_registry_keeps_the_home(client, companion, app):
    registry = json.loads((app.state.database.root / worlds.REGISTRY).read_text(encoding='utf-8'))
    assert registry['worlds'][0]['home']['city_id'] == 'baltimore'


def test_a_home_the_world_can_no_longer_reach_goes_back_to_its_city():
    cities = catalog.cities()
    world = {'id': 'w1', 'home': {'city_id': 'new-york', 'neighbourhood': '', 'set_by': where.YOURS}}
    # The world followed its first companion to Camelot: a New York home is out of its reach.
    assert where.settle(world, cities['camelot'], cities)
    assert world['home']['city_id'] == 'camelot' and world['home']['set_by'] == where.PICKED
    # One a trip could reach stays the user's.
    world['home'] = {'city_id': 'new-york', 'neighbourhood': '', 'set_by': where.YOURS}
    assert not where.settle(world, cities['haddon-harbor'], cities)
    assert world['home']['city_id'] == 'new-york'
