"""Become a townsperson (companion/worlds.py, Feature Hit List #43): a new life as someone met around town."""
import pytest
from test_cast import chatty, met_someone, ok, steady, switch  # noqa: F401 - fixtures

from companion.characters import require_current
from companion.life import network
from companion.world import townsfolk


@pytest.fixture
def met(client, clock, chatty):  # noqa: F811
    mira, person = met_someone(client, clock)
    with client.app.state.database.connect() as connection:
        town = require_current(connection)['town_seed']
    return mira, person, town


def test_becoming_them_starts_a_new_world_as_them(client, met, app):
    _mira, person, town = met
    before = ok(client.get('/api/worlds'))
    after = ok(client.post('/api/worlds/become', json={'key': person['key']}))
    persona, world = after['persona'], after['world']
    assert persona['name'] == person['full'] and persona['age'] == person['age']
    assert persona['gender'] == {'she': 'woman', 'he': 'man', 'they': 'nonbinary'}[person['pronouns'].split('/')[0]]
    assert persona['townsfolk_key'] == person['key'] and persona['town_seed'] == town
    assert str(person['age']) in persona['about'] and 'Usually:' in persona['about']
    assert 'Has met the user' not in persona['about']
    assert world['active'] and world['name'] == person['full'] and world['companions'] != ['Mira']
    # The world they left waits as it was.
    assert before['world']['id'] in {item['id'] for entry in after['personas'] for item in entry['worlds']}
    assert before['world']['companions'] == ['Mira']


def test_their_circle_is_there_and_they_are_not_a_stranger_in_it(client, met):
    _mira, person, town = met
    ok(client.post('/api/worlds/become', json={'key': person['key']}))
    with client.app.state.database.connect() as connection:
        starter = require_current(connection)
        data = network.city(connection, starter)
    # Same town, same people: the starter companion is from their place, and they know the user.
    assert starter['town_seed'] == town and data['you'] == person['key']
    sheet = townsfolk.find(data, starter['townsfolk_key'])
    assert sheet['place']['id'] == person['place']['id']
    background = starter['version']['definition']['background']
    assert f"Knows the user, {person['full'].split()[0]}," in background and ' there.' not in background
    # They are the user here, so nobody runs into them around town.
    assert person['key'] not in {other['key'] for other in townsfolk.at_place(data, person['place']['id'])}


def test_only_someone_met_can_be_become(client, met):
    _mira, person, _town = met
    response = client.post('/api/worlds/become', json={'key': person['key'].rsplit(':', 1)[0] + ':99'})
    assert response.status_code == 404
    assert len(ok(client.get('/api/worlds'))['personas']) == 1


def test_someone_who_became_a_companion_is_already_one(client, met):
    _mira, person, _town = met
    switch(client, person['key'])
    response = client.post('/api/worlds/become', json={'key': person['key']})
    assert response.status_code == 409 and 'already one of your companions' in response.json()['detail']


def test_the_persona_text_is_theirs_to_change(client, met):
    _mira, person, _town = met
    after = ok(client.post('/api/worlds/become', json={'key': person['key']}))
    persona = after['persona']
    changed = ok(client.patch(f"/api/worlds/personas/{persona['id']}", json={'about': 'Just me.'}))
    assert changed['persona']['about'] == 'Just me.' and changed['persona']['townsfolk_key'] == person['key']


def test_nobody_anywhere_in_town_is_them(client, met):
    """Townsfolk are worked out from the seed, never stored, so every list of them must leave the user out."""
    from companion import dating
    from companion.world import paper
    _mira, person, _town = met
    ok(client.post('/api/worlds/become', json={'key': person['key']}))
    with client.app.state.database.connect() as connection:
        data = network.city(connection, require_current(connection))
    hoods = [hood['id'] for hood in data['neighborhoods']]
    everyone = [sheet for place in data['places'] for sheet in townsfolk.at_place(data, place['id'])]
    everyone += [sheet for hood in hoods for sheet in townsfolk.residents(data, hood)]
    everyone += [sheet for place in data['places'] for sheet in townsfolk.reaching(data, place['id'])]
    everyone += [sheet for sheet, _details in dating.pool(data)] + paper.sample(data)
    assert everyone and person['key'] not in {sheet['key'] for sheet in everyone}
    shown = ok(client.get(f"/api/world/cities/{data['id']}/places/{person['place']['id']}/people"))
    assert person['key'] not in {sheet['key'] for sheet in shown}
    # A resident the user became is left out of their street the same way.
    resident = townsfolk.residents(data, hoods[0])[0]
    assert resident['key'] not in {sheet['key'] for sheet in townsfolk.residents(data | {'you': resident['key']}, hoods[0])}


def test_a_new_life_is_always_a_grown_up(client, met):
    _mira, person, _town = met
    assert ok(client.post('/api/worlds/become', json={'key': person['key']}))['persona']['age'] >= 18
