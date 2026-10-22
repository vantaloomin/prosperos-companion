"""Bring your Marinara world (companion/world/marinara.py): a Marinara Engine world map becomes a city and world lore,
with no review step. The sample is small and invented; real exports are private and stay out of the repo."""
import base64
import copy
import json

import pytest

from companion.world import catalog, marinara, naming

TODAY = '2026-10-12'


def place(id_, parent, name, kind, **extra) -> dict:
    return {'id': id_, 'parentId': parent, 'name': name, 'kind': kind, 'description': f'About {name}.',
            'modelMemory': '', 'awarenessSummary': '', 'icon': '', 'links': [], 'status': 'active',
            'sortOrder': 0, **extra}


def sample() -> dict:
    """Two top regions, districts, a street, a home with a room, a business with floors and rooms, an archived
    place, labelled and unlabelled links, carried lore and one picture."""
    locations = [
        place('city', None, 'Lisbon', 'region', awarenessSummary='A hilly harbour city.'),
        place('alder', 'city', 'Alder Quarter', 'region', placement={'x': 20, 'y': 30},
              links=[{'targetId': 'bright', 'label': 'Tram 4', 'bidirectional': True, 'state': 'available'},
                     {'targetId': 'bright', 'bidirectional': True, 'state': 'available'}]),
        place('lane', 'alder', 'Fennel Lane', 'region', modelMemory='Cobbled and steep.'),
        place('home', 'lane', "Mara's Apartment", 'building'),
        place('bedroom', 'home', "Mara's Bedroom", 'room', modelMemory='Postcards on every wall.'),
        place('kettle', 'alder', 'Copper Kettle', 'place', icon='☕', awarenessSummary='A tiny corner cafe.',
              modelMemory='The owner remembers every order.'),
        place('pier', 'alder', 'Old Pier', 'place', status='archived'),
        place('stall', 'pier', 'Lost Stall', 'place'),
        place('bright', 'city', 'Brightwater', 'region', placement={'x': 70, 'y': 70}),
        place('owl', 'bright', 'Night Owl', 'place', icon='🍸',
              links=[{'targetId': 'board', 'label': 'Hallway', 'bidirectional': True, 'state': 'available'},
                     {'targetId': 'kettle', 'label': 'Secret Tunnel', 'bidirectional': True, 'state': 'hidden'}]),
        place('hall', 'bright', 'Starlight Hall', 'building', icon='🎭'),
        place('tower', 'city', 'Gilded Tower', 'building', placement={'x': 75, 'y': 65}),
        place('floor', 'tower', 'Executive Floor', 'floor'),
        place('board', 'floor', 'Boardroom', 'room'),
        place('cafe', 'floor', 'Tower Cafe', 'place', icon='☕'),
        place('vale', None, 'Outer Vale', 'region', sortOrder=1),
        place('cabin', 'vale', "Wren's Cabin", 'building'),
        place('loft', 'cabin', 'Loft Room', 'room'),
    ]
    return {'format': 'marinara-hierarchical-map', 'formatVersion': 4, 'name': 'Harbourlight, chapter 3',
            'definition': {'schemaVersion': 1, 'locations': locations, 'startingLocationId': 'home'},
            'hierarchyProfile': {'types': [{'id': 'type_shop', 'label': 'Shop', 'baseKind': 'place'}],
                                 'locationTypeIds': {'kettle': 'type_shop', 'owl': 'type_shop'}},
            'portableLore': {'books': [{'entries': [{'keys': ['the Tide'], 'content': 'The tide turns at noon.',
                                                     'constant': False}]}], 'references': []},
            'artwork': [{'filename': 'a.png', 'data': ''}, {'filename': 'b.png', 'data': ''}]}


@pytest.fixture
def made() -> dict:
    return marinara.convert(sample(), TODAY)


def by_name(records: list[dict]) -> dict:
    return {record['name']: record for record in records}


def test_a_world_map_becomes_one_city_that_loads_without_mending(made):
    city = catalog.prepare(made['city'], mend=True)
    assert 'import_notes' not in city
    assert (city['name'], city['timezone'], city['setting'], city['era']) == ('Lisbon', 'Europe/Lisbon', 'original',
                                                                               'modern')
    # The second top region folds in as a neighbourhood; streets fold into theirs.
    assert [hood['name'] for hood in city['neighborhoods']] == ['Alder Quarter', 'Brightwater', 'Outer Vale']
    places = by_name(city['places'])
    assert {name: place['kind'] for name, place in places.items()} == {
        'Copper Kettle': 'cafe', 'Night Owl': 'bar', 'Starlight Hall': 'venue', 'Tower Cafe': 'cafe'}
    assert places['Copper Kettle']['summary'] == 'A tiny corner cafe.'
    assert places['Copper Kettle']['day_parts'] == ['morning', 'afternoon']
    assert places['Night Owl']['day_parts'] == ['evening', 'late']


def test_homes_rooms_and_archived_places_are_never_public_places(made):
    names = {place['name'] for place in made['city']['places']}
    assert not names & {"Mara's Apartment", "Mara's Bedroom", "Wren's Cabin", 'Loft Room', 'Old Pier', 'Lost Stall'}
    assert any("Mara's Apartment (Alder Quarter)" in note for note in made['notes'])
    assert '1 archived place left out.' in made['notes']
    assert '2 pictures not imported.' in made['notes']


def test_a_building_with_rooms_is_an_employer_in_the_nearest_neighbourhood(made):
    employer = by_name(made['city']['employers'])['Gilded Tower']
    assert employer['neighborhood'] == 'brightwater'
    # Mostly offices, with a café on one floor: office work first, the café's too.
    assert employer['careers'] == ['marketing-coordinator', 'barista'] and employer['sector'] == 'business'
    assert 'Inside: Executive Floor, Boardroom.' in employer['summary']
    assert by_name(made['city']['places'])['Tower Cafe']['neighborhood'] == 'brightwater'


def test_labelled_links_between_places_become_transit(made):
    lines = made['city']['transit']
    assert [(line['name'], line['kind']) for line in lines] == [('Tram 4', 'tram')]
    hoods = by_name(made['city']['neighborhoods'])
    assert hoods['Alder Quarter']['transit'] == hoods['Brightwater']['transit'] == ['tram-4']
    assert any('links without a label, hidden, blocked or between rooms' in note for note in made['notes'])


def test_map_positions_become_small_offsets_from_the_centre(made):
    hoods = by_name(made['city']['neighborhoods'])
    alder, bright = hoods['Alder Quarter'], hoods['Brightwater']
    # Up and left on the map is north and west; the two sit about 14 km apart.
    assert alder['lat'] > 0 > alder['lon'] and bright['lat'] < 0 < bright['lon']
    assert 10 < catalog.distance_km(alder, bright) < 20
    assert (hoods['Outer Vale']['lat'], hoods['Outer Vale']['lon']) == (0.0, 0.0)


def test_notes_become_one_world_lorebook_keyed_by_place_names(made):
    book = made['book']
    assert book['name'] == 'Harbourlight, chapter 3' and book['format'] == 'Marinara world map'
    entries = {entry['title']: entry for entry in book['entries']}
    assert entries['Copper Kettle']['keywords'] == ['Copper Kettle']
    assert 'The owner remembers every order.' in entries['Copper Kettle']['text']
    assert entries["Mara's Bedroom"]['text'].startswith("A room in Mara's Apartment, in Alder Quarter.")
    tide = next(entry for entry in book['entries'] if entry['keywords'] == ['the Tide'])
    assert tide['text'] == 'The tide turns at noon.' and tide['enabled']
    assert 'Lost Stall' not in entries


def test_older_bare_definitions_are_read_and_other_files_are_not():
    bare = {'locations': sample()['definition']['locations']}
    assert marinara.detect(bare) and marinara.detect(sample())
    assert not marinara.detect({'locations': [{'id': 'x', 'name': 'X'}]}) and not marinara.detect([])
    made = marinara.convert(bare, TODAY)
    assert made['city']['name'] == 'Lisbon' and not any('pictures' in note for note in made['notes'])


def test_a_city_name_no_zone_knows_keeps_utc():
    value = sample()
    value['definition']['locations'][0]['name'] = 'Port Ellery'
    made = marinara.convert(value, TODAY)
    assert made['city']['timezone'] == 'UTC' and made['city']['id'] == 'port-ellery'
    assert any('uses UTC' in note for note in made['notes'])


def test_importing_adds_the_city_and_its_lore_at_once(client, companion):
    response = client.post('/api/world/import/marinara', json=sample())
    assert response.status_code == 200, response.text
    made = response.json()
    assert (made['id'], made['origin'], made['category']) == ('lisbon', 'user', 'custom')
    assert made['book']['world'] is True and made['book']['entries'] == len(marinara.convert(sample(), TODAY)['book']
                                                                            ['entries'])
    assert any('Timezone set to Europe/Lisbon.' == note for note in made['import_notes'])
    assert 'lisbon' in {city['id'] for city in client.get('/api/world/cities').json()}
    books = client.get('/api/lore').json()['books']
    books = [book for book in books if not book['city']]
    assert [book['name'] for book in books if book['world']] == ['Harbourlight, chapter 3']
    # The same map again is refused, so its lore is never offered twice; a changed map is a second city.
    again = client.post('/api/world/import/marinara', json=sample())
    assert again.status_code == 409 and 'already came in as Lisbon' in again.text
    changed = copy.deepcopy(sample())
    changed['definition']['locations'].append(place('extra', changed['definition']['locations'][0]['id'],
                                                    'Tram Museum', 'building'))
    assert client.post('/api/world/import/marinara', json=changed).json()['id'] == 'lisbon-2'


@pytest.mark.parametrize('broken', [{'name': 123}, {'icon': 7}, {'links': 5}])
def test_odd_field_types_are_a_plain_refusal(client, companion, broken):
    value = copy.deepcopy(sample())
    value['definition']['locations'][1].update(broken)
    response = client.post('/api/world/import/marinara', json=value)
    assert response.status_code in (200, 422), response.text


def test_a_chain_of_places_nested_past_any_real_map_is_refused(client, companion):
    value = copy.deepcopy(sample())
    locations = value['definition']['locations']
    parent = locations[0]['id']
    for number in range(1500):
        locations.append(place(f'deep{number}', parent, f'Room {number}', 'room'))
        parent = f'deep{number}'
    response = client.post('/api/world/import/marinara', json=value)
    assert response.status_code in (200, 422), response.text


def test_a_map_that_cannot_become_a_city_adds_no_lore(client, companion):
    value = copy.deepcopy(sample())
    value['definition']['locations'] = []
    response = client.post('/api/world/import/marinara', json=value)
    assert response.status_code == 422
    assert not [book for book in client.get('/api/lore').json()['books'] if book['world'] and not book['city']]


def test_bring_your_characters_points_a_world_map_to_cities(client, companion):
    data = base64.b64encode(json.dumps(sample()).encode()).decode()
    response = client.post('/api/import/character', json={'filename': 'harbour.world-map.json', 'data': data})
    assert response.status_code == 422 and 'Marinara world map' in response.text


def world_books(client) -> list[str]:
    return [book['name'] for book in client.get('/api/lore').json()['books'] if book['world'] and not book['city']]


def settle_in(client, world_id: str, city_id: str):
    """Switch to a new world and make its first companion there, as the user does (it starts with none)."""
    assert client.post(f"/api/worlds/{world_id}/switch").status_code == 200
    made = client.post('/api/companion', json={'name': 'Wren', 'timezone': 'Europe/Lisbon', 'home_city': city_id})
    assert made.status_code == 200, made.text


def test_the_lore_follows_the_city_into_a_new_world(client, companion):
    assert client.post('/api/world/import/marinara', json=sample()).status_code == 200
    made = client.post('/api/worlds', json={'city_id': 'lisbon'})
    assert made.status_code == 200, made.text
    elsewhere = client.post('/api/worlds', json={})
    settle_in(client, made.json()['id'], 'lisbon')
    assert world_books(client) == ['Harbourlight, chapter 3']
    [book] = [book for book in client.get('/api/lore').json()['books'] if book['world'] and not book['city']]
    assert any(entry['title'] == 'Copper Kettle' for entry in book['entries'])
    settle_in(client, elsewhere.json()['id'], 'baltimore')
    assert world_books(client) == [], 'a world in another city does not get it'


def test_deleting_the_city_deletes_its_lore_in_every_world(client, companion):
    assert client.post('/api/world/import/marinara', json=sample()).status_code == 200
    made = client.post('/api/worlds', json={'city_id': 'lisbon'}).json()
    response = client.delete('/api/world/cities/lisbon')
    assert response.status_code in (200, 204), response.text
    assert world_books(client) == []
    settle_in(client, made['id'], 'baltimore')
    assert world_books(client) == [], 'the copy in the world made there goes too'


def test_a_city_with_no_country_takes_it_from_its_time_zone_so_names_are_local():
    value = copy.deepcopy(sample())
    value['definition']['locations'][0]['name'] = 'Seoul'
    made = marinara.convert(value, TODAY)
    assert (made['city']['country'], made['city']['timezone']) == ('South Korea', 'Asia/Seoul')
    assert any('so it is South Korea' in note for note in made['notes'])
    assert naming.local_culture(made['city']['country']) == 'korea'
