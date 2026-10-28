"""The city map: their home, usual and recent places, Story mode's scene and every place to click
(companion/life/citymap.py, Hit List #40)."""
from datetime import timedelta

import pytest
from test_network import build
from test_social_circle import make

from companion.characters import require_current
from companion.database import encode
from companion.life import body, citymap
from companion.world import catalog


@pytest.fixture(autouse=True)
def steady(monkeypatch):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)


def read(client):
    response = client.get('/api/life/map')
    assert response.status_code == 200, response.text
    return response.json()


def test_the_map_shows_every_place_in_their_city_near_its_neighbourhood(client):
    assert client.get('/api/life/map').status_code == 409
    make(client, 'Warm and curious.')
    found = read(client)
    assert found['city']['id'] == 'baltimore' and found['city']['real'] is True and found['story'] is False
    hoods = {hood['id']: hood for hood in found['hoods']}
    assert all(len(hood['next']) == citymap.NEXT_TO and hood['id'] not in hood['next'] for hood in hoods.values())
    places = [place for place in found['places'] if not place['id'].startswith('~')]
    assert len(places) > 100 and all(place['approx'] for place in places)
    for place in places:
        hood = hoods[place['hood_id']]
        assert abs(place['lat'] - hood['lat']) <= citymap.SPREAD and abs(place['lon'] - hood['lon']) <= citymap.SPREAD
        assert 2 <= len(place['spots']) <= 4
    assert read(client)['places'] == found['places']


def test_their_home_and_the_places_they_go_are_marked_with_what_happened_there(client, clock):
    make(client, 'Warm and curious.')
    build(client)
    with client.app.state.database.connect(write=True) as connection:
        companion = require_current(connection)
        for index, days in enumerate((1, 9, 40)):
            at = (clock.now() - timedelta(days=days)).isoformat()
            connection.execute(
                'INSERT INTO life_events (id, companion_id, timeline_id, idempotency_key, kind, status, summary, details, '
                "starts_at, ends_at, character_version_id, permission_revision, created_at) VALUES (?, ?, ?, ?, 'routine', "
                "'committed', ?, ?, ?, ?, ?, 0, ?)",
                (f'e{index}', companion['id'], companion['active_timeline_id'], f'k{index}', f'Coffee number {index}.',
                 encode({'place': {'id': 'vaccaros', 'name': "Vaccaro's"}, 'block_kind': 'leisure'}), at, at,
                 companion['active_version_id'], at))
    found = read(client)
    homes = [place for place in found['places'] if place['id'] == '~home']
    assert homes and homes[0]['pins'] == ['home'] and homes[0]['name'] == "Mira's home" and homes[0]['spots']
    cafe = next(place for place in found['places'] if place['id'] == 'vaccaros')
    assert cafe['pins'] == ['recent', 'usual']
    assert [event['summary'] for event in cafe['history']] == ['Coffee number 0.', 'Coffee number 1.', 'Coffee number 2.']


def test_story_mode_marks_the_scene_and_fictional_cities_get_a_sketch(client):
    make(client, 'Warm and curious.')
    assert client.put('/api/settings', json={'story_mode': True}).status_code == 200
    scene = client.get('/api/story').json()['scene']
    found = read(client)
    assert found['story'] is True and isinstance(found['water'], list)
    assert [place['id'] for place in found['places'] if 'scene' in place['pins']] == [scene['place']['id']]
    assert citymap.real({'setting': 'fictional'}) is False and citymap.real({'distribution': 'private'}) is False
    assert citymap.real({'setting': 'real'}) is True


def test_usual_and_recent_places_come_from_their_events_and_a_lunch_break_is_not_work(clock):
    now = clock.now()
    events = [{'id': '1', 'place': 'cafe', 'summary': '', 'at': (now - timedelta(days=2)).isoformat(), 'block': 'leisure'},
              {'id': '2', 'place': 'cafe', 'summary': '', 'at': (now - timedelta(days=30)).isoformat(), 'block': 'leisure'},
              {'id': '3', 'place': 'museum', 'summary': '', 'at': (now - timedelta(days=50)).isoformat(), 'block': 'leisure'},
              {'id': '4', 'place': 'office', 'summary': '', 'at': (now - timedelta(days=90)).isoformat(), 'block': 'work'}]
    marked = citymap.marks(events, now)
    assert marked == {'cafe': {'usual', 'recent'}}


def test_a_city_can_name_its_sea_rivers_and_lakes_for_the_drawn_map():
    from pydantic import ValidationError

    from companion.world import catalog
    from companion.world.schema import Water
    london = catalog.city('london-1895')
    assert london['water'][0]['kind'] == 'river' and len(london['water'][0]['points']) >= 2
    assert Water(kind='sea', name='Grey Sea', side='south').side == 'south'
    for bad in ({'kind': 'sea'}, {'kind': 'river', 'points': [(1.0, 2.0)]}, {'kind': 'lake', 'points': []}):
        with pytest.raises(ValidationError):
            Water(**bad)


def test_only_real_cities_of_today_get_a_street_map():
    assert citymap.real(catalog.city('baltimore'))
    assert not citymap.real(catalog.city('new-york-1925'))
    assert not citymap.real(catalog.city('grandport'))


def test_regulars_leave_out_the_staff(monkeypatch):
    from companion.life import encounters
    people = [{'key': 'town:x:cafe:0', 'name': 'Ana', 'kind': 'staff', 'staff': True, 'place': {'id': 'cafe'}},
              {'key': 'town:x:cafe:2', 'name': 'Ben', 'kind': 'regular', 'staff': False, 'place': {'id': 'cafe'}}]
    monkeypatch.setattr(encounters, 'known', lambda *_args: people)
    assert citymap.regulars(None, {}, None) == {'cafe': ['Ben']}


def home_on(found, place_id='~home'):
    return next((place for place in found['places'] if place['id'] == place_id), None)


def test_their_home_follows_where_its_description_and_their_words_put_it_and_the_user_can_move_it(client):
    from companion.life import money
    pits = {'neighborhoods': [{'id': 'wuju-hills', 'name': 'Wuju Hills'}, {'id': 'the-pits', 'name': 'The Pits'}],
            'places': [{'id': 'great-pit', 'name': 'The Great Pit', 'neighborhood': 'the-pits'}]}
    assert money.named_hood({'identity': 'He runs the underground fighting pits of Navori.'}, pits)['id'] == 'the-pits'
    assert money.named_hood({'identity': 'He runs the underground fighting pits.'}, pits, loose=False) is None
    assert money.named_hood({}, pits, ('an apartment above the Great Pit',))['id'] == 'the-pits'
    assert money.named_hood({'routine': 'Works in Wuju Hills. Lives above the Great Pit.'}, pits)['id'] == 'the-pits'
    make(client, 'Warm and curious.')
    item = client.get('/api/life/home').json()['items'][0]
    # The user rewrites their home as being in Canton: the map (and the home) follow.
    assert client.patch(f"/api/life/home/items/{item['id']}", json={'description': 'a rowhouse in Canton'}).status_code == 200
    found = read(client)
    assert home_on(found)['hood'] == 'Canton' and home_on(found)['about'] == 'a rowhouse in Canton'
    assert client.get('/api/life/home').json()['items'][0]['neighborhood'] == 'Canton'
    # Moved on the map, it stays where the user put it, and the description says so.
    hampden = next(hood['id'] for hood in found['hoods'] if hood['name'] == 'Hampden')
    moved = client.put('/api/life/map/home', json={'neighborhood': hampden})
    assert moved.status_code == 200 and home_on(moved.json())['hood'] == 'Hampden'
    assert home_on(read(client))['about'] == 'a rowhouse in Hampden'
    assert client.put('/api/life/map/home', json={'neighborhood': 'nowhere'}).status_code == 422


def test_a_home_whose_neighbourhood_is_not_in_their_city_is_placed_again(client):
    make(client, 'Warm and curious.')
    item = client.get('/api/life/home').json()['items'][0]
    with client.app.state.database.connect(write=True) as connection:
        connection.execute('UPDATE home_items SET details=json_set(details, "$.city", "Somewhere Else", '
                           '"$.neighborhood", "Deck 9") WHERE id=?', (item['id'],))
    home = home_on(read(client))
    assert home and home['hood'] in {hood['name'] for hood in read(client)['hoods']}


def test_rooms_and_what_is_inside_a_place_are_the_users_to_rewrite(client):
    make(client, 'Warm and curious.')
    found = read(client)
    item_id = home_on(found)['item_id']
    assert client.patch(f'/api/life/home/items/{item_id}', json={'rooms': ['the den', 'in the loft']}).status_code == 200
    home = home_on(read(client))
    assert home['spots'] == ['the den', 'the loft'] and home['rooms_set'] is True
    assert client.patch(f'/api/life/home/items/{item_id}', json={'rooms': []}).status_code == 200
    assert home_on(read(client))['rooms_set'] is False
    place = next(place for place in found['places'] if place['id'] == 'vaccaros')
    changed = client.put('/api/life/map/places/vaccaros/inside', json={'spots': ['the pastry case', 'the back room']})
    assert changed.status_code == 200
    assert home_on(changed.json(), 'vaccaros')['spots'] == ['the pastry case', 'the back room']
    assert home_on(changed.json(), 'vaccaros')['spots_set'] is True
    back = client.put('/api/life/map/places/vaccaros/inside', json={'spots': []}).json()
    assert home_on(back, 'vaccaros')['spots'] == place['spots']
    assert client.put('/api/life/map/places/nowhere/inside', json={'spots': ['x']}).status_code == 404


def test_everyone_who_lives_in_the_city_is_on_the_map_the_user_too(client):
    make(client, 'Outgoing, the life of the party.')
    build(client)
    found = read(client)
    hood = found['hoods'][0]
    with client.app.state.database.connect(write=True) as connection:
        connection.execute('UPDATE persona SET home_city_id=?, home_neighbourhood=? WHERE id=1', ('baltimore', hood['id']))
    found = read(client)
    yours = home_on(found, '~you')
    assert yours and yours['name'] == 'Your home' and yours['pins'] == ['yours'] and yours['hood'] == hood['name']
    known = [place for place in found['places'] if 'known' in place['pins']]
    locals_ = [person for person in client.get('/api/life/circle').json() if person.get('city') == 'Baltimore']
    assert known and len(known) == len({place['name'] for place in known})
    assert {place['name'] for place in known} <= {f"{person['name']}'s home" for person in locals_}
