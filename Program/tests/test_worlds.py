"""Worlds and personas (companion/worlds.py): more than one life for the user, each in its own world."""
import json

import pytest
from conftest import send

from companion import worlds


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def listing(client):
    return ok(client.get('/api/worlds'))


def test_an_existing_workspace_quietly_becomes_the_first_world(client, companion, app):
    data = listing(client)
    assert len(data['personas']) == 1 and len(data['personas'][0]['worlds']) == 1
    world = data['world']
    assert world['first'] and world['active'] and world['companions'] == ['Mira']
    assert (app.state.database.root / worlds.REGISTRY).is_file()


def test_the_persona_starts_from_what_matchlight_knows(client, companion, app):
    ok(client.put('/api/dating/profile', json={'name': 'Sam', 'age': 31, 'gender': 'man', 'interested_in': ['woman'],
                                              'looking_for': 'serious', 'age_min': 25, 'age_max': 40, 'bio': ''}))
    database = app.state.database
    (database.root / worlds.REGISTRY).unlink()  # As before this version: no worlds yet.
    worlds.start(database)
    persona = listing(client)['persona']
    assert (persona['name'], persona['age'], persona['gender']) == ('Sam', 31, 'man')
    assert ok(client.get('/api/dating'))['persona']['name'] == 'Sam'


def test_the_companion_knows_who_the_user_is(client, connected, provider):
    persona = listing(client)['persona']
    ok(client.patch(f"/api/worlds/personas/{persona['id']}", json={'name': 'Sam', 'age': 31,
                                                                 'about': 'Works nights as a paramedic.'}))
    send(client, 'Hey!', 'first-message')
    prompt = provider.requests[-1]['prompt']
    assert '## Who the user is' in prompt and '- Name: Sam' in prompt and 'paramedic' in prompt


def test_a_new_world_is_ready_with_its_own_townsfolk_and_a_starter_companion(client, companion, app):
    made = ok(client.post('/api/worlds', json={}))
    assert not made['active'] and not made['first'] and len(made['companions']) == 1
    assert made['name'] == 'Baltimore 2' or made['name'] != listing(client)['world']['name']
    path = app.state.database.root / made['folder'] / worlds.DATABASE
    assert path.is_file()
    # The same world draws the same starter; the user is still where they were.
    assert listing(client)['world']['companions'] == ['Mira']


def test_switching_worlds_changes_everything_and_settings_follow(client, connected, app):
    ok(client.put('/api/settings', json={'chat_style': 'retro', 'show_moods': True}))
    send(client, 'Hello there', 'hello-message')
    made = ok(client.post('/api/worlds', json={'name': 'Somewhere else'}))
    switched = ok(client.post(f"/api/worlds/{made['id']}/switch"))
    assert switched['world']['id'] == made['id'] and switched['world']['name'] == 'Somewhere else'
    starter = ok(client.get('/api/companion'))['companion']
    assert starter['version']['name'] == made['companions'][0]
    assert ok(client.get('/api/conversation'))['messages'] == []
    settings = ok(client.get('/api/settings'))
    assert settings['chat_style'] == 'retro' and settings['show_moods']
    assert ok(client.get('/api/connection'))['connection']['model'] == 'local-model'
    # And back: Mira and the chat are as they were.
    first = next(world for world in listing(client)['personas'][0]['worlds'] if world['first'])
    ok(client.post(f"/api/worlds/{first['id']}/switch"))
    assert ok(client.get('/api/companion'))['companion']['version']['name'] == 'Mira'
    assert any(message['text'] == 'Hello there' for message in ok(client.get('/api/conversation'))['messages'])


def test_a_new_persona_has_a_world_of_their_own(client, companion):
    # Who the user is stays theirs: a name is needed, and nothing they left blank is made up.
    assert client.post('/api/worlds/personas', json={}).status_code == 422
    made = ok(client.post('/api/worlds/personas', json={'name': 'Jordan'}))
    assert made['name'] == 'Jordan' and len(made['worlds']) == 1
    assert (made['gender'], made['age'], made['about'], made['birthday']) == ('', None, '', '')
    switched = ok(client.post(f"/api/worlds/personas/{made['id']}/switch"))
    assert switched['persona']['id'] == made['id'] and switched['world']['id'] == made['worlds'][0]['id']
    data = listing(client)
    assert [persona['active'] for persona in data['personas']] == [False, True]


def test_the_world_the_user_was_in_opens_on_the_next_start(tmp_path, clock, provider, companion, client, app):
    from companion.main import create_app
    from companion.providers.vault import MemoryVault
    made = ok(client.post('/api/worlds', json={}))
    ok(client.post(f"/api/worlds/{made['id']}/switch"))
    again = create_app(app.state.database.home, clock=clock, vault=MemoryVault(), provider=provider, life_tasks=False)
    assert again.state.database.path == app.state.database.path
    assert worlds.active_path(app.state.database.home) == app.state.database.path


def test_nothing_switches_while_debug_time_is_on(client, companion, app):
    made = ok(client.post('/api/worlds', json={}))
    with app.state.database.connect(write=True) as connection:
        connection.execute("INSERT INTO debug_time (id, app_anchor, real_anchor, speed, started_at, app_started_at, "
                           "snapshot, backup) VALUES (1, 'a', 'b', 1, 'c', 'd', 'e', 'f')")
    response = client.post(f"/api/worlds/{made['id']}/switch")
    assert response.status_code == 409 and 'Debug time' in response.json()['detail']


def test_deleting_a_world_keeps_a_backup_and_never_the_one_in_use(client, companion, app):
    data = listing(client)
    response = client.delete(f"/api/worlds/{data['world']['id']}")
    assert response.status_code == 409
    made = ok(client.post('/api/worlds', json={}))
    ok(client.delete(f"/api/worlds/{made['id']}"))
    assert len(listing(client)['personas'][0]['worlds']) == 1
    assert not (app.state.database.root / made['folder']).exists()
    assert list((app.state.database.root / 'backups' / 'deleted-worlds').glob('*.zip'))


def test_a_world_can_move_to_another_persona(client, companion):
    persona = ok(client.post('/api/worlds/personas', json={'name': 'Riley'}))
    first = listing(client)['world']
    moved = ok(client.patch(f"/api/worlds/{first['id']}", json={'persona_id': persona['id'], 'name': 'Home'}))
    assert moved['persona']['id'] == persona['id'] and moved['world']['name'] == 'Home'


def test_a_damaged_registry_is_not_trusted(tmp_path):
    (tmp_path / worlds.REGISTRY).write_text('{not json', encoding='utf-8')
    assert worlds.load(tmp_path) is None
    (tmp_path / worlds.REGISTRY).write_text(json.dumps({'worlds': []}), encoding='utf-8')
    assert worlds.load(tmp_path) is None


@pytest.mark.parametrize('name', ['', '  '])
def test_a_world_needs_a_name(client, companion, name):
    world = listing(client)['world']
    assert client.patch(f"/api/worlds/{world['id']}", json={'name': name}).status_code == 422


def test_a_page_left_open_in_another_world_is_told_to_reload(client, companion):
    made = ok(client.post('/api/worlds', json={}))
    first = ok(client.get('/api/worlds'))['active_world_id']
    assert client.get('/api/companion', headers={'X-Companion-World': first}).status_code == 200
    ok(client.post(f"/api/worlds/{made['id']}/switch", headers={'X-Companion-World': first}))
    # The phone still shows the first world: it changes nothing here and is told to open this one.
    stale = client.post('/api/conversation/recap/read', json={'since': 'x'}, headers={'X-Companion-World': first})
    assert stale.status_code == 409 and stale.json()['code'] == 'world_changed'
    assert client.get('/api/companion', headers={'X-Companion-World': made['id']}).status_code == 200


def test_memories_still_queued_in_a_world_left_behind_are_formed_on_return(client, connected, app):
    from companion.memory.formation import run_pending
    send(client, 'My neighbour is called Oskar.', 'oskar-message')
    database = app.state.database
    with database.connect(write=True) as connection:  # As if the memory model had not got to it yet.
        connection.execute("UPDATE memory_jobs SET status='queued', finished_at=NULL")
    first = listing(client)['world']['id']
    made = ok(client.post('/api/worlds', json={}))
    ok(client.post(f"/api/worlds/{made['id']}/switch"))
    ok(client.post(f"/api/worlds/{first}/switch"))
    run_pending(database)
    with database.connect() as connection:
        assert {row['status'] for row in connection.execute('SELECT status FROM memory_jobs')} == {'done'}
