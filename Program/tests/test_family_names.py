"""Parents and siblings share the companion's family name unless a marriage explains a different one."""
from companion.database import decode, encode
from companion.life import circle
from companion.world.source import CatalogWorld

IMMEDIATE = ('mom', 'dad', 'parent', 'sister', 'brother', 'sibling')


def make(client, name, identity='Outgoing, the life of the party.'):
    response = client.post('/api/companion', json={'name': name, 'identity': identity, 'timezone': 'America/New_York',
                                                     'location': 'Fells Point, Baltimore'})
    assert response.status_code == 200, response.text


def family(client):
    return [person for person in client.get('/api/life/circle').json() if person['role'] in IMMEDIATE]


def surname(person):
    return person['full_name'].split()[-1]


def test_parents_and_siblings_carry_the_companions_last_name(client):
    make(client, 'Kimberly Smith')
    relatives = family(client)
    assert relatives
    for person in relatives:
        assert surname(person) == 'Smith' or (person['married'] and person['birth_family'] == 'Smith')


def test_only_a_recorded_marriage_gives_a_sibling_another_name():
    world, definition = CatalogWorld(), {'name': 'Kimberly Smith', 'home_city': 'baltimore', 'identity': 'outgoing'}
    married = renamed = 0
    for index in range(30):
        for person in circle.build(definition, world, f't{index}', 10):
            details = person['details']
            if person['role'] not in IMMEDIATE:
                continue
            if details['full_name'].split()[-1] != 'Smith':
                assert circle.role_kind(person['role']) == 'sibling' and details['married']
                assert details['birth_family'] == 'Smith' and details['full_name'] != f"{person['name']} Smith"
                renamed += 1
            married += bool(details.get('married'))
    assert married and renamed
    # The same timeline always gets the same answer.
    assert circle.build(definition, world, 't3', 10) == circle.build(definition, world, 't3', 10)


def test_family_name_takes_its_listed_form_and_reads_a_maiden_name():
    assert circle.family_name({'name': 'Anna Kowalska'}) == 'Kowalski'
    assert circle.family_form('Kowalski', 'she/her') == 'Kowalska'
    assert circle.family_form('Kowalski', 'he/him') == 'Kowalski'
    assert circle.family_name({'name': 'Joe Smith Jr.'}) == 'Smith'
    assert circle.family_name({'name': 'Mira'}) is None
    assert circle.family_name({'name': 'Kim Lee', 'background': 'Kim Lee, née Park, grew up in Ohio.'}) == 'Park'
    # A companion who married without naming a birth name: their family keeps a name of its own.
    assert circle.family_name({'name': 'Rosa Diaz', 'identity': 'She is happily married to Tom.'}) is None
    assert circle.family_name({'name': 'Rosa Diaz', 'identity': 'Her parents were married young.'}) == 'Diaz'


def test_relatives_named_before_get_the_family_name_unless_the_user_renamed_them(client):
    make(client, 'Kimberly Smith')
    relatives = family(client)
    assert len(relatives) >= 2
    first, second = relatives[0], relatives[1]
    with client.app.state.database.connect() as connection:
        for person in (first, second):
            row = dict(connection.execute('SELECT name, details FROM circle_people WHERE id=?',
                                          (person['id'],)).fetchone())
            details = {key: value for key, value in decode(row['details']).items()
                       if key not in ('married', 'birth_family')}
            # `name` is the full name when two people share a first name; build from the first name alone,
            # and give such a name the old surname too, as a circle from before family names would have it.
            details['full_name'] = f"{person['full_name'].split()[0]} Freeman"
            name = details['full_name'] if row['name'] == person['full_name'] else row['name']
            connection.execute('UPDATE circle_people SET name=?, details=? WHERE id=?',
                               (name, encode(details), person['id']))
    assert client.patch(f"/api/life/circle/{second['id']}", json={'name': 'Kaity'}).status_code == 200
    after = {person['id']: person for person in client.get('/api/life/circle').json()}
    assert after[first['id']]['full_name'] == first['full_name'] and after[first['id']]['name'] == first['name']
    assert after[second['id']]['name'] == 'Kaity' and after[second['id']]['full_name'].endswith(' Freeman')
