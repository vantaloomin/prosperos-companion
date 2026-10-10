"""Who knows who: the web of everyone the user has met or heard about (companion/life/web.py, Hit List #44)."""
from datetime import timedelta

import pytest
from test_network import build
from test_social_circle import make

from companion.life import body, encounters, network, web


@pytest.fixture(autouse=True)
def lively(monkeypatch):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    monkeypatch.setattr(network, 'ACTIVE', True)
    monkeypatch.setattr(network, 'HOST_CHANCE', 1)
    monkeypatch.setattr(encounters, 'ACTIVE', True)
    monkeypatch.setattr(encounters, 'CHANCE', 1)


def read(client):
    response = client.get('/api/life/web')
    assert response.status_code == 200, response.text
    found = response.json()
    nodes = {node['id']: node for node in found['nodes']}
    assert all(link['source'] in nodes and link['target'] in nodes for link in found['links'])
    pairs = [tuple(sorted((link['source'], link['target']))) for link in found['links']]
    assert len(pairs) == len(set(pairs))
    return nodes, found['links']


def tied(links, a, b):
    return next((link for link in links if {link['source'], link['target']} == {a, b}), None)


def test_the_web_needs_a_companion(client):
    assert client.get('/api/life/web').status_code == 409


def test_everyone_met_or_heard_about_is_in_the_web_with_how_they_are_tied(client, clock):
    mira = make(client, 'Warm and curious, a social butterfly.')
    build(client)
    clock.instant = clock.now() + timedelta(days=8)
    build(client)
    nodes, links = read(client)
    me, companion = nodes['you'], nodes[f"companion:{mira['id']}"]
    assert me['kind'] == 'you' and companion['main'] and tied(links, 'you', companion['id'])['kind'] == 'you'
    circle = [node for node in nodes.values() if node['kind'] == 'circle']
    assert circle and all(tied(links, companion['id'], node['id']) for node in circle)
    assert any(tied(links, companion['id'], node['id'])['label'] == node['detail'] for node in circle)
    met = [node for node in nodes.values() if node['kind'] == 'acquaintance']
    assert met, 'a gathering every Friday should introduce someone'
    for node in met:
        assert tied(links, node['id'], node['id'].rsplit('/', 1)[0]), node
        assert tied(links, companion['id'], node['id'])['label'].startswith('met at ')
    town = [node for node in nodes.values() if node['kind'] == 'townsperson']
    assert town and all(tied(links, companion['id'], node['id'])['kind'] == 'met' for node in town)
    # Nothing secret or hidden rides along: only names, roles and how people are tied.
    assert all(set(node) <= {'id', 'name', 'kind', 'detail', 'hood', 'companion_id', 'main'} for node in nodes.values())


def test_the_users_own_people_and_matches_hang_off_the_user(client, clock):
    mira = make(client, 'Warm and curious.')
    now = clock.now().isoformat()
    with client.app.state.database.connect(write=True) as connection:
        for person_id, name in (('p1', 'Jo'), ('p2', 'Jo')):
            connection.execute('INSERT INTO user_people (id, companion_id, name, relation, created_at, updated_at) '
                               'VALUES (?, ?, ?, ?, ?, ?)', (person_id, mira['id'], name, 'sister', now, now))
        # A match whose place has gone from the city is left out rather than breaking the web.
        connection.execute("INSERT INTO dating_swipes (person_key, city_id, town, liked, matched, created_at) "
                           "VALUES ('town:baltimore:gone-place:0', 'baltimore', '', 1, 1, ?)", (now,))
    nodes, links = read(client)
    sisters = [node for node in nodes.values() if node['kind'] == 'yours']
    assert len(sisters) == 1 and tied(links, 'you', sisters[0]['id'])['kind'] == 'family'
    assert 'town:baltimore:gone-place:0' not in nodes


def test_relation_words_read_as_kinds_of_tie():
    assert [web.kind_of(word) for word in ('sister', 'girlfriend', 'coworkers', 'roommate', 'ex', 'gym buddy',
                                           'close friend', 'met at the market')] == \
        ['family', 'partner', 'work', 'neighbor', 'ex', 'friend', 'friend', 'met']
