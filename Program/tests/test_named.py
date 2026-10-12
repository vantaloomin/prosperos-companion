"""People and pets the character sheet names stay theirs in the circle and the home (companion/life/named.py)."""
from companion.life import circle, home, named
from companion.world.source import CatalogWorld

DANA = {'name': 'Dana', 'home_city': 'baltimore',
        'identity': 'Dana Okafor is 34 and works night shifts as an ER nurse. She lives alone in a rowhouse in '
                    'Hampden with a one-eyed cat named Pickle.',
        'background': 'Her father still brings up pre-med every Christmas. Her younger brother Tunde lives in Atlanta '
                      'and calls her when he needs money.'}
THEO = {'name': 'Theo', 'home_city': 'chicago',
        'identity': 'Theo Lindqvist is 29 and tends bar. He lives with his sister Annika in a two-flat in Avondale.'}
ROZ = {'name': 'Roz', 'home_city': 'new-orleans',
       'identity': 'Roz lives in a shotgun house with their partner Marguerite and an elderly beagle named Hush Puppy.'}


def names(people):
    return [(person['name'], person['relation']) for person in people]


def test_the_sheet_names_people_and_pets():
    assert names(named.people(DANA)) == [('Tunde', 'brother')]
    assert named.people(DANA)[0]['local'] is False
    assert named.pets_of(DANA) == [{'name': 'Pickle', 'variety': 'cat', 'description': 'a one-eyed cat'}]
    assert names(named.people(THEO)) == [('Annika', 'sister')] and named.people(THEO)[0]['local']
    assert names(named.people(ROZ)) == [('Marguerite', 'partner')]
    assert named.pets_of(ROZ) == [{'name': 'Hush Puppy', 'variety': 'dog', 'description': 'an elderly beagle'}]
    # In first person too, and with the name before the relation.
    sheet = {'name': 'Kai', 'routine': 'I walk my dog Rufus every morning. Grace, my older sister, comes on Sundays.'}
    assert names(named.people(sheet)) == [('Grace', 'sister')]
    assert [pet['name'] for pet in named.pets_of(sheet)] == ['Rufus']


def test_only_a_name_counts_and_exes_and_the_late_are_left_out():
    sheet = {'name': 'Kai', 'background': 'Her father still brings it up. Her sister In Seoul is fine. Mira, his '
                                          "ex-wife, still calls. His late father Bob was a cop. Kai's mom Linda "
                                          'lives in Chicago.'}
    assert named.people(sheet) == []
    assert names(named.people({'name': 'Kai', 'identity': 'Her mother Linda lives in Chicago.'})) == [
        ('Linda', 'mother')]
    # The companion's own name is never someone else.
    assert named.people({'name': 'Kai Moana', 'identity': 'His brother Kai Moana Jr.'}) == []


def test_a_named_relative_takes_the_seeded_ones_place_with_the_family_name():
    world = CatalogWorld()
    people = circle.build(DANA, world, 't1', 5)
    siblings = [person for person in people if circle.role_kind(person['role']) == 'sibling']
    assert [(person['name'], person['role']) for person in siblings] == [('Tunde', 'brother')]
    tunde = siblings[0]
    assert tunde['details']['full_name'] == 'Tunde Okafor' and tunde['details']['local'] is False
    assert tunde['schedule'] == [] and len(people) == 5
    # Other relatives carry the family name the sheet spells out.
    assert all(person['details']['full_name'].endswith('Okafor') for person in people
               if circle.role_kind(person['role']) in ('parent', 'sibling'))
    assert circle.build(DANA, world, 't1', 5) == people


def test_a_named_partner_joins_the_circle_and_lives_here():
    people = circle.build(ROZ, CatalogWorld(), 't1', 5)
    partner = next(person for person in people if person['name'] == 'Marguerite')
    assert partner['role'] == 'partner' and partner['details']['local'] and partner['schedule']
    assert len(people) == 6
    theo = circle.build(THEO, CatalogWorld(), 't1', 5)
    assert [person['name'] for person in theo if circle.role_kind(person['role']) == 'sibling'] == ['Annika']


def test_without_city_data_the_named_people_are_there_too():
    sheet = {**DANA, 'home_city': ''}
    people = circle.build(sheet, None, 't1', 5)
    tunde = next(person for person in people if person['name'] == 'Tunde')
    assert tunde['role'] == 'brother' and tunde['schedule'] == [] and not tunde['details']['local']


def test_the_sheets_pets_are_the_homes_pets():
    data = CatalogWorld().find('baltimore')
    for seed in range(12):
        pets = [item for item in home.assemble(f'home:{seed}', DANA, data) if item['kind'] == 'pet']
        assert [(pet['name'], pet['variety']) for pet in pets] == [('Pickle', 'cat')]


def test_an_edited_sheet_adds_its_people_and_pets_to_an_existing_world(client):
    response = client.post('/api/companion', json={'name': 'Dana', 'timezone': 'America/New_York',
                                                    'home_city': 'baltimore'})
    assert response.status_code == 200, response.text
    companion = response.json()
    before = client.get('/api/life/circle').json()
    client.get('/api/life/home')
    definition = {**companion['version']['definition'], 'identity': DANA['identity'],
                  'background': DANA['background']}
    response = client.post('/api/companion/versions', json={'definition': definition,
                                                             'expected_version_id': companion['active_version_id']})
    assert response.status_code == 200, response.text
    after = client.get('/api/life/circle').json()
    assert [person['id'] for person in after[:len(before)]] == [person['id'] for person in before]
    assert [(person['name'], person['role']) for person in after[len(before):]] == [('Tunde', 'brother')]
    pets = [item['name'] for item in client.get('/api/life/home').json()['items'] if item['kind'] == 'pet']
    assert 'Pickle' in pets
    # Read again: nothing is added twice, and a renamed Pickle still counts.
    pickle = next(item for item in client.get('/api/life/home').json()['items'] if item['name'] == 'Pickle')
    assert client.patch(f"/api/life/home/items/{pickle['id']}", json={'name': 'Pickles'}).status_code == 200
    assert len(client.get('/api/life/circle').json()) == len(after)
    pets = [item['name'] for item in client.get('/api/life/home').json()['items'] if item['kind'] == 'pet']
    assert pets.count('Pickles') == 1 and 'Pickle' not in pets
