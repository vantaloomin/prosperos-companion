"""The user's pick for a circle person's love life (companion/life/love_pick.py, Edit person "Their love life")."""
import pytest

from companion.life import casting, circle, circle_love, happenings, network
from companion.life.circle import details_of


@pytest.fixture
def database(app):
    return app.state.database


def companion(client):
    response = client.post('/api/companion', json={'name': 'Dana', 'timezone': 'America/New_York',
                                                    'home_city': 'baltimore'})
    assert response.status_code == 200, response.text
    return response.json()


def adults(client):
    return [person for person in client.get('/api/life/circle').json()
            if (person.get('age') or 30) >= 18 and person['role'] not in circle_love.PARTNER_ROLES]


def love(client, person_id):
    response = client.get(f'/api/life/circle/{person_id}/love')
    assert response.status_code == 200, response.text
    return response.json()


def put(client, person_id, **change):
    response = client.put(f'/api/life/circle/{person_id}/about', json=change)
    assert response.status_code == 200, response.text
    return response.json()


def row_of(database, person_id):
    with database.connect() as connection:
        return circle.person(connection, person_id)


def their_people(database, person_id):
    with database.connect() as connection:
        from companion.characters import require_current
        current = require_current(connection)
        return network.people_of(connection, current, row_of(database, person_id)['seed'])


def test_the_app_decides_until_the_user_picks(client, database):
    companion(client)
    person = adults(client)[0]
    found = love(client, person['id'])
    assert found['editable'] and not found['set'] and found['state'] in circle_love.STATES
    assert all(item['id'] != person['id'] for item in found['people'])
    # Married to someone the user names: their people list a spouse by that name, and no event changes it.
    put(client, person['id'], love='married', partner_name='Ren Ito')
    found = love(client, person['id'])
    assert (found['state'], found['partner'], found['set']) == ('married', 'Ren', True)
    row = row_of(database, person['id'])
    assert 'partner' in details_of(row)['edited'] and details_of(row)['married'] is True
    assert not casting.love_is_apps(row) and not happenings.apps(row, 'love')
    people = their_people(database, person['id'])
    current = [item for item in people if item['name'] == 'Ren' and not item.get('ex')]
    assert len(current) == 1 and current[0]['relation'] in ('wife', 'husband', 'spouse')
    # Single: nobody is their partner, and no one became an ex by the user's word.
    put(client, person['id'], love='single')
    assert love(client, person['id'])['state'] == 'single'
    assert not any(item['relation'] in network.PARTNERS or item.get('ex') for item in their_people(database, person['id']))
    # Back to the app: what it had, byte for byte in the parts it reads.
    before = details_of(row_of(database, person['id']))['partner_before']
    put(client, person['id'], love='')
    details = details_of(row_of(database, person['id']))
    assert details.get('partner') == before['partner'] and details.get('married') == before['married']
    assert 'partner_before' not in details and 'partner' not in details.get('edited', ())
    assert not love(client, person['id'])['set']


def test_seeing_with_no_name_keeps_or_makes_a_partner(client):
    companion(client)
    person = adults(client)[0]
    put(client, person['id'], love='seeing')
    first = love(client, person['id'])
    assert first['state'] == 'seeing' and first['partner']
    # Engaged, still no name: the same partner.
    put(client, person['id'], love='engaged')
    assert love(client, person['id'])['partner'] == first['partner']


def test_picking_someone_in_the_circle_links_both_and_leaves_their_partner(client, database):
    companion(client)
    first, second, third = adults(client)[:3]
    put(client, second['id'], love='married', partner_name=third['name'])
    assert love(client, third['id'])['partner'] == second['name'].split()[0]
    stands = {item['id']: item['stands'] for item in love(client, first['id'])['people']}
    assert stands[second['id']] == f"married to {third['name'].split()[0]}"
    # The user picks the taken one for someone else: they are linked both ways, and the one left is single.
    put(client, first['id'], love='seeing', partner_name=second['name'])
    assert love(client, first['id'])['partner'] == second['name'].split()[0]
    assert love(client, second['id'])['state'] == 'seeing'
    assert love(client, second['id'])['partner'] == first['name'].split()[0]
    assert love(client, third['id'])['state'] == 'single'
    with database.connect() as connection:
        rows = circle.people(connection, row_of(database, first['id'])['timeline_id'])
        by_id = {row['id']: row for row in rows}
        assert circle.tie(by_id[first['id']], by_id[second['id']]) == 'partners'
    # Handing the first back to the app hands back the link too.
    put(client, first['id'], love='')
    assert not love(client, second['id'])['set']


def test_the_companions_partner_and_children_have_no_pick():
    assert not circle_love_editable({'role': 'girlfriend', 'details': {}})
    assert not circle_love_editable({'role': 'friend', 'details': {'love': True}})
    assert not circle_love_editable({'role': 'nephew', 'details': {'age': 9}})
    assert circle_love_editable({'role': 'friend', 'details': {'age': 30}})


def circle_love_editable(row):
    from companion.life import love_pick
    return love_pick.editable(row)
