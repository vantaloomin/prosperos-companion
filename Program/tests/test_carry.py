"""Taking a companion to another world (companion/carry.py): saved to a file with their history, opened elsewhere."""
import io
import json
import zipfile

import pytest
from conftest import send
from test_lora import add_picture, picture

from companion import carry
from companion.main import create_app
from companion.providers.vault import MemoryVault


@pytest.fixture
def app(tmp_path, clock, provider):
    return create_app(tmp_path / 'workspace' / 'companion.sqlite3', clock=clock, vault=MemoryVault(),
                      provider=provider, life_tasks=False, lora_maker=True)


@pytest.fixture
def companion(client):
    return ok(client.post('/api/companion', json={'name': 'Mira', 'personality': 'Warm and curious',
                                                   'timezone': 'America/New_York', 'home_city': 'baltimore'}))


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def saved(client, companion_id: str) -> bytes:
    response = client.get(f'/api/export/companion/{companion_id}')
    assert response.status_code == 200, response.text
    assert 'Mira.companion' in response.headers['content-disposition']
    return response.content


def opened(client, data: bytes):
    return client.post('/api/export/companion', content=data, headers={'content-type': 'application/octet-stream'})


def switch_to_new_world(client, **body) -> dict:
    made = ok(client.post('/api/worlds', json=body))
    ok(client.post(f"/api/worlds/{made['id']}/switch"))
    return made


def lived(client, companion):
    send(client, 'My sister Ana is visiting this weekend.', 'client-0001')
    ok(client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Sister', 'value': 'Ana'}))
    return ok(add_picture(client, picture(1), 'mira.jpg'))


def test_a_companion_comes_to_another_world_with_their_history(client, connected, companion, app):
    reference = lived(client, companion)
    data = saved(client, companion['id'])
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        manifest = json.loads(archive.read(carry.MANIFEST))
        names = archive.namelist()
    assert manifest['format'] == carry.FORMAT and manifest['name'] == 'Mira'
    assert manifest['counts']['messages'] >= 2 and manifest['counts']['memories'] >= 1
    assert f"files/lora/references/{reference['file']}" in names

    switch_to_new_world(client, city_id='grandport')
    assert ok(client.get('/api/companion'))['companion'] is None
    arrived = ok(opened(client, data))
    assert arrived['name'] == 'Mira' and arrived['moved_to'] == 'Grandport' and arrived['stepped_back'] is None
    here = ok(client.get('/api/companion'))['companion']
    assert here['id'] == companion['id'] and here['version']['definition']['home_city'] == 'grandport'
    assert here['version']['note'].startswith('Moved to Grandport')
    texts = [message['text'] for message in ok(client.get('/api/conversation'))['messages']]
    assert 'My sister Ana is visiting this weekend.' in texts
    memories = ok(client.get('/api/memories'))
    assert any(memory['value'] == 'Ana' for memory in memories)
    assert (app.state.database.path.parent / 'lora' / 'references' / reference['file']).is_file()

    # Once here, the same file is turned away.
    again = opened(client, data)
    assert again.status_code == 409 and 'already live in this world' in again.json()['detail']


def test_they_become_the_main_character_beside_whoever_is_here(client, connected, companion):
    lived(client, companion)
    data = saved(client, companion['id'])
    switch_to_new_world(client)
    ok(client.post('/api/companion', json={'name': 'Theo', 'timezone': 'UTC'}))
    arrived = ok(opened(client, data))
    assert arrived['stepped_back'] == 'Theo' and arrived['moved_to'] is None
    assert ok(client.get('/api/companion'))['companion']['version']['name'] == 'Mira'
    names = {member['name'] for member in ok(client.get('/api/companion/cast'))['members']}
    assert names >= {'Mira', 'Theo'}


def test_a_file_that_is_not_a_saved_companion_is_refused(client, companion):
    assert opened(client, b'not a zip').status_code == 422
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr(carry.MANIFEST, json.dumps({'format': 'something-else'}))
    assert opened(client, buffer.getvalue()).status_code == 422


def test_files_outside_their_folders_are_never_written(client, connected, companion, tmp_path, app):
    data = saved(client, companion['id'])
    buffer = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as source, zipfile.ZipFile(buffer, 'w') as archive:
        for entry in source.infolist():
            archive.writestr(entry, source.read(entry))
        archive.writestr('files/../escaped.txt', 'no')
        archive.writestr('files/settings/evil.txt', 'no')
    switch_to_new_world(client)
    ok(opened(client, buffer.getvalue()))
    workspace = app.state.database.path.parent
    assert not (workspace.parent / 'escaped.txt').exists() and not (workspace / 'settings' / 'evil.txt').exists()


def test_every_carried_table_is_one_of_a_companions():
    from companion import start_over
    assert set(carry.TABLES) <= set(start_over.HISTORY + start_over.CHARACTER)
    assert carry.STAYS <= set(start_over.HISTORY + start_over.CHARACTER)


def test_a_lived_life_comes_along_whole(client, life, companion, clock, monkeypatch):
    """Days of life (agenda, feed, circle, home, kids) all go back in, and their life goes on in the new city."""
    from datetime import timedelta

    from conftest import reconcile
    monkeypatch.setattr('companion.life.kids.ACTIVE', True)
    monkeypatch.setattr('companion.life.admin.ACTIVE', True, raising=False)
    send(client, 'Good morning!', 'client-0001')
    for _day in range(3):
        clock.advance(timedelta(hours=20))
        reconcile(client)
    data = saved(client, companion['id'])
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        rows = json.loads(archive.read(carry.ROWS))
    assert {'timelines', 'messages', 'circle_people', 'life_events'} <= set(rows)
    switch_to_new_world(client, city_id='grandport')
    arrived = ok(opened(client, data))
    assert arrived['moved_to'] == 'Grandport' and arrived['left_out'] == []
    clock.advance(timedelta(hours=20))
    reconcile(client)
    assert ok(client.get('/api/companion'))['companion']['version']['definition']['timezone'] != 'America/New_York'


def test_moving_keeps_who_they_are_and_gives_them_a_home_there(client, connected, companion, app):
    data = saved(client, companion['id'])
    switch_to_new_world(client, city_id='grandport')
    ok(opened(client, data))
    definition = ok(client.get('/api/companion'))['companion']['version']['definition']
    assert definition['identity'] == companion['version']['definition']['identity']
    assert definition['timezone'] == 'Atlantic/Azores' and 'Grandport' in definition['location']
    with app.state.database.connect() as connection:
        homes = connection.execute("SELECT details, until FROM home_items WHERE kind='home' ORDER BY since").fetchall()
    assert homes and homes[-1]['until'] is None
