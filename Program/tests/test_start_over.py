"""Starting the companion over, or deleting them, after a verified backup."""
import sqlite3
from pathlib import Path

import pytest
from conftest import reconcile, send
from fastapi.testclient import TestClient
from test_images import FakeAdapter, drain, generate, local_comfy, make_post
from test_lora import add_picture, picture

from companion import backup, restore, start_over
from companion.database import SCHEMA
from companion.identity import CLIENT_HEADER
from companion.main import create_app
from companion.providers.vault import MemoryVault


@pytest.fixture
def adapters():
    return {'comfyui': FakeAdapter(), 'codex': FakeAdapter(), 'hosted': FakeAdapter()}


@pytest.fixture
def app(tmp_path, clock, provider, adapters):
    return create_app(tmp_path / 'workspace' / 'companion.sqlite3', clock=clock, vault=MemoryVault(),
                      provider=provider, life_tasks=False, image_adapters=adapters, lora_maker=True)


@pytest.fixture
def client(app):
    with TestClient(app, headers={CLIENT_HEADER: 'workspace'}) as test_client:
        yield test_client


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def lived(client, clock):
    """A companion with a conversation, a memory, a life, a picture in the feed and a reference picture."""
    send(client, 'Morning! My sister Ana is visiting.', 'client-0001')
    ok(client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Pet', 'value': 'Biscuit'}))
    reconcile(client)
    local_comfy(client)
    job = generate(client, make_post(client, clock))
    drain(client)
    reference = ok(add_picture(client, picture(1), 'one.jpg'))
    return job, reference


def count(app, table) -> int:
    with app.state.database.connect() as connection:
        return connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]  # noqa: S608


def test_every_table_is_either_kept_or_cleared():
    connection = sqlite3.connect(':memory:')
    connection.executescript(SCHEMA)
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    groups = start_over.WORKSPACE + start_over.CHARACTER + start_over.HISTORY
    assert len(groups) == len(set(groups))
    assert tables - {'sqlite_sequence'} == set(groups) - {'sqlite_sequence'}


def test_the_confirmation_needs_the_companions_name(client, connected):
    preview = ok(client.get('/api/companion/start-over'))
    assert preview['name'] == 'Mira' and preview['timelines'] == 1
    response = client.post('/api/companion/start-over', json={'name': 'Someone else'})
    assert response.status_code == 422 and 'Type Mira' in response.json()['detail']
    assert client.post('/api/companion/delete', json={'name': ''}).status_code == 422
    # Nothing was backed up or removed.
    assert not (client.app.state.database.path.parent / 'backups').exists()


def test_starting_over_keeps_the_character_and_clears_their_history(client, app, life, clock):
    _job, reference = lived(client, clock)
    before = ok(client.get('/api/companion'))['companion']
    image = app.state.database.path.parent / 'images'
    assert any(image.iterdir())
    assert count(app, 'messages') and count(app, 'memories') and count(app, 'life_events') and count(app, 'feed_posts')

    result = ok(client.post('/api/companion/start-over', json={'name': ' mira '}))

    after = ok(client.get('/api/companion'))['companion']
    assert after['id'] == before['id'] and after['active_version_id'] == before['active_version_id']
    assert after['active_timeline_id'] != before['active_timeline_id']
    for table in start_over.HISTORY:
        assert count(app, table) == (1 if table == 'timelines' else 0), table
    assert ok(client.get('/api/conversation'))['messages'] == []
    assert not any(path.is_file() for path in image.rglob('*'))
    # Their look stays: the reference picture and its file.
    assert client.get(f"/api/lora/references/{reference['id']}/file").status_code == 200
    # The backup came first, carries everything, and is listed as made before starting over.
    archive = Path(result['backup']['path'])
    assert archive.name.startswith('before-reset-') and backup.inspect(archive)['manifest']['datasets_included']
    listed = ok(client.get('/api/backups'))['backups']
    assert [entry['kind'] for entry in listed] == ['before-reset']
    # The fresh timeline talks and lives from now on.
    send(client, 'Hi again.', 'client-0002')
    assert len(ok(client.get('/api/conversation'))['messages']) == 2


def test_deleting_removes_the_companion_and_keeps_the_workspace_setup(client, app, life, clock):
    lived(client, clock)
    backends = ok(client.get('/api/images/backends'))

    result = ok(client.post('/api/companion/delete', json={'name': 'Mira'}))

    assert ok(client.get('/api/companion'))['companion'] is None
    for table in start_over.CHARACTER + start_over.HISTORY:
        assert count(app, table) == 0, table
    workspace = app.state.database.path.parent
    assert not (workspace / 'images').exists() and not (workspace / 'lora' / 'references').exists()
    # The model connection and image backends are still set up for the next companion.
    assert ok(client.get('/api/connection'))['connection']['model'] == 'local-model'
    assert ok(client.get('/api/images/backends')) == backends
    assert Path(result['backup']['path']).name.startswith('before-delete-')
    created = client.post('/api/companion', json={'name': 'Tess', 'timezone': 'Europe/Lisbon'})
    assert created.status_code == 200, created.text


def test_a_delete_can_be_undone_by_restoring_its_backup(client, app, life, clock):
    lived(client, clock)
    messages = count(app, 'messages')
    result = ok(client.post('/api/companion/delete', json={'name': 'Mira'}))
    path = app.state.database.path
    client.close()

    restored = restore.replace_workspace(Path(result['backup']['path']), path, clock)

    assert not restored['assets']['missing']
    database = app.state.database.__class__(path, clock)
    with database.connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM messages').fetchone()[0] == messages
        assert connection.execute('SELECT COUNT(*) FROM lora_references').fetchone()[0] == 1


def test_deleting_waits_for_training_to_stop(client, app, companion):
    with app.state.database.connect(write=True) as connection:
        connection.execute("INSERT INTO lora_runs (id, companion_id, name, status, trainer, trainer_tested, base_model, trigger, "
                           "options, trainer_config, dataset, folder, disclosure_accepted_at, created_at) "
                           "VALUES ('run', ?, 'Run', 'running', 'ai-toolkit', 'x', 'base', 'm1ra', '{}', '{}', '[]', "
                           "'run', '2026-10-05T12:00:00Z', '2026-10-05T12:00:00Z')", (companion['id'],))
    response = client.post('/api/companion/delete', json={'name': 'Mira'})
    assert response.status_code == 409 and 'training' in response.json()['detail']
    assert ok(client.get('/api/companion'))['companion'] is not None


def test_lookups_and_the_city_news_from_them_go_with_the_companion(client, app, companion):
    """Weather and local events looked up for the old companion's city never show for the next one."""
    with app.state.database.connect(write=True) as connection:
        connection.execute(
            "INSERT INTO context_observations (id, service_name, category, purpose, tool, arguments, destination, "
            "location, status, content, requested_at, fresh_until) VALUES ('obs', 'Built-in weather', 'weather', "
            "'companion_city', 'get_forecast', '{}', 'this computer', '{}', 'ok', 'New York, clear', "
            "'2026-10-05T12:00:00Z', '2026-10-06T12:00:00Z')")
        for change_id, origin, observation in (('news', 'real', 'obs'), ('mine', 'user', None)):
            connection.execute(
                'INSERT INTO world_changes (id, city_id, kind, origin, name, announced_on, starts_on, observation_id, '
                "created_at) VALUES (?, 'new-york', 'news', ?, 'Headline', '2026-10-05', '2026-10-05', ?, "
                "'2026-10-05T12:00:00Z')", (change_id, origin, observation))

    ok(client.post('/api/companion/delete', json={'name': 'Mira'}))

    assert ok(client.get('/api/context/observations'))['observations'] == []
    with app.state.database.connect() as connection:
        kept = [row[0] for row in connection.execute('SELECT id FROM world_changes')]
    assert kept == ['mine']
