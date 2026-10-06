"""Friends of friends: seeded layers around the circle, met at gatherings and run into later."""
from datetime import timedelta

import pytest
from test_social_circle import make

from companion.characters import require_current
from companion.database import decode
from companion.life import agenda, body, network
from companion.memory import context
from companion.world import naming


@pytest.fixture(autouse=True)
def steady(monkeypatch):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)


@pytest.fixture
def parties(monkeypatch):
    monkeypatch.setattr(network, 'ACTIVE', True)
    monkeypatch.setattr(network, 'HOST_CHANCE', 1)


def people(client, key):
    response = client.get('/api/life/network', params={'key': key})
    assert response.status_code == 200, response.text
    return response.json()


def test_everyone_has_their_own_people_a_few_layers_out(client):
    make(client, 'Outgoing, the life of the party.')
    becca = client.get('/api/life/circle').json()[0]
    first = people(client, becca['key'])
    assert first == people(client, becca['key'])
    assert network.SIZE[0] <= len(first['people']) <= network.SIZE[1] and first['deeper']
    for person in first['people']:
        assert person['how'].startswith(f"{becca['name']}'s ") and person['depth'] == 2
        assert not naming.is_invented(person['full']) and person['met'] is None
    family = becca['full_name'].split()[-1]
    assert all(person['full'].endswith(family) or person['full'].endswith(family[:-1] + 'a')
               for person in first['people'] if person['relation'] in ('sister', 'brother', 'sibling'))
    key = first['people'][0]['key']
    second = people(client, key)
    assert second['person']['key'] == key and all(item['depth'] == 3 for item in second['people'])
    third = people(client, second['people'][0]['key'])
    assert all(item['depth'] == 4 for item in third['people']) and not third['deeper']
    assert people(client, third['people'][0]['key'])['people'] == []
    assert client.get('/api/life/network', params={'key': 'circle:nobody:0'}).status_code == 404


def build(client):
    with client.app.state.database.connect() as connection:
        companion = require_current(connection)
        agenda.extend(connection, companion, client.app.state.life.world, client.app.state.database.clock.now())
        rows = connection.execute("SELECT * FROM life_agenda WHERE subject='companion' ORDER BY starts_at").fetchall()
    return [{**dict(row), 'entry': decode(row['entry']) if row['entry'] else None} for row in rows]


def test_a_friends_gathering_introduces_their_people(client, parties, clock):
    make(client, 'Outgoing, the life of the party.')
    rows = build(client)
    party = next(row for row in rows if row['entry'] and row['entry']['activity'] == 'gathering')
    gathering = party['entry']['gathering']
    assert 2 <= len(gathering['met']) <= 4 and party['entry']['summary'].startswith('Mira went to ')
    assert party['entry']['with']['name'] in gathering['occasion']
    assert client.get('/api/life/acquaintances').json() == []
    clock.instant = clock.now() + timedelta(days=7)
    build(client)
    met = client.get('/api/life/acquaintances').json()
    assert gathering['met'][0] in {person['key'] for person in met}
    first = next(person for person in met if person['key'] == gathering['met'][0])
    assert first['occasion'] == gathering['occasion'] and first['full'] in party['entry']['summary']
    host_key = gathering['met'][0].split('/')[0]
    listed = people(client, host_key)['people']
    assert next(item for item in listed if item['key'] == first['key'])['met'] == gathering['occasion']
    with client.app.state.database.connect() as connection:
        companion = require_current(connection)
        lines = network.context_lines(connection, companion['active_timeline_id'], clock.now())
    assert any(f"you met at {gathering['occasion']}" in line for _key, line in lines)
    assert 'acquaintances' in context.HEADINGS


def test_someone_met_before_can_be_run_into(client, parties, clock, monkeypatch):
    make(client, 'Outgoing, the life of the party.')
    build(client)
    monkeypatch.setattr(network, 'RUN_IN_CHANCE', 1)
    clock.instant = clock.now() + timedelta(days=7)
    rows = build(client)
    ran = [row for row in rows if row['entry'] and row['entry'].get('ran_into')]
    assert ran and 'Ran into ' in ran[0]['entry']['summary']


def test_no_gatherings_when_off(client, clock):
    make(client, 'Outgoing, the life of the party.')
    assert not any(row['entry'] and row['entry']['activity'] == 'gathering' for row in build(client))
