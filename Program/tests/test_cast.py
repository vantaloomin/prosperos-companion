"""Switching the main character to a townsperson the companion has met, and back (companion/cast.py)."""
import json
from datetime import timedelta

import pytest
from conftest import send
from test_network import build
from test_social_circle import make

from companion.characters import require_current
from companion.life import body, encounters
from companion.models import CharacterDefinition


@pytest.fixture(autouse=True)
def steady(monkeypatch):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)


@pytest.fixture
def chatty(monkeypatch):
    monkeypatch.setattr(encounters, 'ACTIVE', True)
    monkeypatch.setattr(encounters, 'CHANCE', 1)
    monkeypatch.setattr(encounters, 'FAMILIAR_CHANCE', 1)


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def met_someone(client, clock):
    """Mira, who met townsfolk last week, and the first of them."""
    mira = make(client, 'Warm and curious.')
    build(client)
    clock.instant = clock.now() + timedelta(days=7)
    build(client)
    known = ok(client.get('/api/life/townsfolk'))
    assert known
    return mira, known[0]


def switch(client, key):
    drafted = ok(client.get('/api/companion/cast/draft', params={'key': key}))
    return drafted, ok(client.post('/api/companion/cast/switch', json={'key': key, 'definition': drafted['definition']}))


def test_a_townsperson_gets_a_full_profile_from_their_sheet(client, clock, chatty):
    _mira, person = met_someone(client, clock)
    drafted = ok(client.get('/api/companion/cast/draft', params={'key': person['key']}))
    definition = CharacterDefinition.model_validate(drafted['definition'])
    assert definition.name == person['full'] and definition.home_city == 'baltimore'
    assert definition.relationship == 'friendship' and drafted['stepping_back'] == 'Mira'
    assert definition.identity.startswith(str(person['age'])) and definition.personality and definition.voice
    assert definition.flaws and 'Mira' in definition.background and definition.routine
    assert {day for block in definition.schedule if block.kind == 'sleep' for day in block.days} == set(range(7))
    # They keep the face and build they had in town, so their pictures show the same person.
    assert definition.looks.age == person['age'] and definition.looks.height_cm and definition.looks.face
    # Staff work their shift; anyone else with a career works or studies (a graduate student has classes).
    assert any(block.kind in ('work', 'study') for block in definition.schedule) == (
        person['kind'] == 'staff' or bool(definition.money.career))
    # Only someone the companion has met can take over.
    assert client.get('/api/companion/cast/draft', params={'key': 'town:baltimore:national-aquarium:2'}) \
        .status_code in (200, 404)
    assert client.get('/api/companion/cast/draft', params={'key': 'town:baltimore:nowhere:0'}).status_code == 404
    refused = client.post('/api/companion/cast/switch', json={'key': 'town:baltimore:nowhere:0',
                                                              'definition': drafted['definition']})
    assert refused.status_code == 404


def test_switching_keeps_both_histories_and_they_meet_in_town(client, clock, chatty):
    mira, person = met_someone(client, clock)
    send(client, 'Morning, Mira!', 'client-0001')
    _drafted, new = switch(client, person['key'])
    assert new['version']['name'] == person['full'] and new['id'] != mira['id']
    assert ok(client.get('/api/companion'))['companion']['id'] == new['id']
    members = ok(client.get('/api/companion/cast'))['members']
    assert [(member['name'], member['main'], member['from_town']) for member in members] == \
        [(person['full'], True, True), ('Mira', False, False)]
    assert ok(client.get('/api/conversation'))['messages'] == []

    # The new main character already knows Mira from those meetings, and never meets themself.
    known = ok(client.get('/api/life/townsfolk'))
    mira_now = next(item for item in known if item['key'] == f"cast:{mira['id']}")
    assert mira_now['full'] == 'Mira' and mira_now['cast'] == mira['id'] and mira_now['times'] == person['times']
    assert all(item['key'] != person['key'] for item in known)
    assert ok(client.get('/api/life/townsfolk/person', params={'key': mira_now['key']}))['now']['doing']
    rows = [row for row in build(client) if row['timeline_id'] == new['active_timeline_id']]
    assert rows and all(row['entry']['townsfolk']['key'] != person['key'] for row in rows
                        if row['entry'] and row['entry'].get('townsfolk'))
    with client.app.state.database.connect() as connection:
        lines = dict(encounters.context_lines(connection, require_current(connection), clock.now()))
    assert 'They know the user well.' in lines[mira_now['key']]

    # Switching back: Mira's chat is as she left it, and the townsperson is now another companion to her.
    back = ok(client.post('/api/companion/cast/focus', json={'companion_id': mira['id']}))
    assert back['id'] == mira['id'] and back['active_timeline_id'] == mira['active_timeline_id']
    assert [message['text'] for message in ok(client.get('/api/conversation'))['messages']
            if message['role'] == 'user'] == ['Morning, Mira!']
    known = ok(client.get('/api/life/townsfolk'))
    them = next(item for item in known if item['key'] == f"cast:{new['id']}")
    assert them['full'] == person['full'] and them['times'] >= person['times']
    assert client.post('/api/companion/cast/focus', json={'companion_id': 'missing'}).status_code == 404


def test_start_over_and_delete_only_touch_the_main_character(client, clock, chatty):
    mira, person = met_someone(client, clock)
    send(client, 'Morning, Mira!', 'client-0001')
    _drafted, new = switch(client, person['key'])
    send(client, 'Hi there.', 'client-0002')
    preview = ok(client.get('/api/companion/start-over'))
    assert preview['others'] == ['Mira'] and preview['messages'] == 1

    ok(client.post('/api/companion/start-over', json={'name': person['full']}))
    assert ok(client.get('/api/conversation'))['messages'] == []
    ok(client.post('/api/companion/delete', json={'name': person['full']}))

    companion = ok(client.get('/api/companion'))['companion']
    assert companion['id'] == mira['id']
    assert [member['name'] for member in ok(client.get('/api/companion/cast'))['members']] == ['Mira']
    assert [message['text'] for message in ok(client.get('/api/conversation'))['messages']
            if message['role'] == 'user'] == ['Morning, Mira!']
    with client.app.state.database.connect() as connection:
        assert connection.execute('PRAGMA foreign_key_check').fetchall() == []
        assert connection.execute('SELECT COUNT(*) FROM timelines WHERE companion_id=?', (new['id'],)).fetchone()[0] == 0


def test_the_text_model_can_write_the_profile_out(client, clock, chatty, provider):
    from test_drafting import GOOD, connect, replying
    _mira, person = met_someone(client, clock)
    connect(client)
    provider.respond = replying(json.dumps(GOOD))
    written = ok(client.post('/api/companion/cast/draft', json={'key': person['key']}))
    definition = written['definition']
    assert definition['name'] == person['full'] and definition['relationship'] == 'friendship'
    assert definition['identity'] == GOOD['identity'] and definition['home_city'] == 'baltimore'
    assert definition['location'].endswith('Baltimore, Maryland')
    assert definition['background'].startswith(GOOD['background']) and 'Has crossed paths with Mira' in \
        definition['background']


def test_new_townsfolk_can_be_seeded_for_one_companion(client, clock, chatty):
    """The city's townsfolk are shared until the user seeds a town of the companion's own."""
    mira, _person = met_someone(client, clock)
    shared = ok(client.get('/api/world/cities/baltimore/places/national-aquarium/people'))
    assert mira['town_seed'] == ''

    seeded = ok(client.post('/api/companion/town', json={'fresh': True}))
    assert seeded['town_seed']
    own = ok(client.get('/api/world/cities/baltimore/places/national-aquarium/people'))
    assert [p['full'] for p in own] != [p['full'] for p in shared]
    # Whoever Mira had met is a stranger in the new town.
    assert ok(client.get('/api/life/townsfolk')) == []
    for _week in range(2):
        clock.instant = clock.now() + timedelta(days=7)
        build(client)
    met = ok(client.get('/api/life/townsfolk'))
    with client.app.state.database.connect() as connection:
        data = encounters.network.city(connection, require_current(connection))
    assert met and all(item['full'] == encounters.townsfolk.find(data, item['key'])['full'] for item in met)

    back = ok(client.post('/api/companion/town', json={'fresh': False}))
    assert back['town_seed'] == ''
    assert [p['full'] for p in ok(client.get('/api/world/cities/baltimore/places/national-aquarium/people'))] == \
        [p['full'] for p in shared]

    # With a second companion, the town is shared between them and stays as it is.
    with client.app.state.database.connect(write=True) as connection:
        connection.execute("INSERT INTO companions (id, slot, created_at) VALUES ('other', NULL, 'x')")
    assert client.post('/api/companion/town', json={'fresh': True}).status_code == 409
