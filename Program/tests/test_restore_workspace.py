"""Replacing the active workspace with a backup keeps later deletions (PRD M5, persistence section)."""
from pathlib import Path

import pytest

from companion import backup, restore
from companion.errors import DomainError


def remember(client, subject, value):
    response = client.post('/api/memories', json={'layer': 'user_fact', 'subject': subject, 'value': value})
    assert response.status_code == 200, response.text
    return response.json()


def test_restore_sets_the_current_workspace_aside_and_keeps_later_deletions(client, app, companion, clock):
    kept = remember(client, 'Pet', 'Biscuit')
    forgotten = remember(client, 'Old job', 'Night shifts at the bakery')
    archive = Path(client.post('/api/backups').json()['path'])
    assert client.post(f"/api/memories/{forgotten['id']}/delete", json={}).status_code == 200
    # A setting changed after the backup is kept, not rolled back.
    assert client.put('/api/life/settings', json={'texts_first': False}).status_code == 200
    path = app.state.database.path
    client.close()

    result = restore.replace_workspace(archive, path, clock)

    assert result['deletions']['memories_deleted'] == 1
    previous = Path(result['previous'])
    assert (previous / 'companion.sqlite3').exists() and previous.parent == path.parent
    restored = app.state.database.__class__(path, clock)
    with restored.connect() as connection:
        ids = {row[0] for row in connection.execute('SELECT id FROM memories')}
        marker = connection.execute('SELECT kind FROM deletion_markers WHERE target_id=?',
                                    (forgotten['id'],)).fetchone()
        review = connection.execute('SELECT review_required, paused_at, automatic_memory FROM workspace_settings').fetchone()
        texts_first = connection.execute('SELECT texts_first FROM life_settings').fetchone()[0]
        open_pauses = connection.execute('SELECT COUNT(*) FROM pauses WHERE ended_at IS NULL').fetchone()[0]
    assert kept['id'] in ids and forgotten['id'] not in ids
    assert marker[0] == 'memory'
    # The current settings carry over: nothing is switched off, paused or held for review.
    assert tuple(review) == (0, None, 1) and texts_first == 0 and open_pauses == 0


def test_a_refused_restore_leaves_the_current_workspace_in_place(client, app, companion, tmp_path, clock):
    remember(client, 'Pet', 'Biscuit')
    damaged = tmp_path / 'damaged.zip'
    damaged.write_bytes(b'not a backup')
    path = app.state.database.path
    before = sorted(item.name for item in path.parent.iterdir())
    with pytest.raises(DomainError):
        restore.replace_workspace(damaged, path, clock)
    assert sorted(item.name for item in path.parent.iterdir()) == before


def test_a_failed_restore_moves_the_workspace_back(client, app, companion, clock, monkeypatch):
    remember(client, 'Pet', 'Biscuit')
    archive = Path(client.post('/api/backups').json()['path'])
    path = app.state.database.path
    client.close()

    def broken(*args, **kwargs):
        raise DomainError('boom', 500)

    monkeypatch.setattr(backup, 'restore', broken)
    with pytest.raises(DomainError):
        restore.replace_workspace(archive, path, clock)
    assert path.exists() and not list(path.parent.glob('replaced-*'))
    with app.state.database.connect() as connection:
        assert connection.execute('SELECT value FROM memories').fetchone()[0] == 'Biscuit'


def test_the_launcher_restores_a_backup_and_exits(client, app, companion, monkeypatch, capsys, tmp_path):
    import socket

    from companion import launch
    remember(client, 'Pet', 'Biscuit')
    archive = Path(client.post('/api/backups').json()['path'])
    path = app.state.database.path
    client.close()
    monkeypatch.setenv('COMPANION_DATA_DIR', str(path.parent))
    monkeypatch.delenv('COMPANION_DB', raising=False)
    monkeypatch.chdir(tmp_path)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    assert launch.main(['--restore', str(archive.relative_to(tmp_path)), '--port', str(port)]) == 0
    output = capsys.readouterr().out
    assert 'Restored' in output and 'moved to' in output
    assert list(path.parent.glob('replaced-*/companion.sqlite3'))


def test_a_restore_chosen_in_settings_runs_on_the_next_start(client, app, companion, clock):
    remember(client, 'Pet', 'Biscuit')
    name = Path(client.post('/api/backups').json()['path']).name
    remember(client, 'Car', 'A green van')
    listed = client.get('/api/backups').json()
    assert [item['name'] for item in listed['backups']] == [name] and listed['pending'] is None
    assert listed['backups'][0]['readable'] and listed['backups'][0]['kind'] == 'backup'
    with pytest.raises(DomainError):
        restore.archive_path(app.state.database.path.parent, '../escape.zip')
    assert client.post('/api/backups/..%2Fescape.zip/restore').status_code in (404, 405)
    assert client.post('/api/backups/missing.zip/restore').status_code == 404
    scheduled = client.post(f'/api/backups/{name}/restore').json()
    assert scheduled['pending']['name'] == name
    assert client.delete('/api/backups/restore').json()['pending'] is None
    client.post(f'/api/backups/{name}/restore')
    path = app.state.database.path
    client.close()

    chosen = restore.apply_pending(path)

    assert chosen[0] == name and chosen[1]['previous']
    assert restore.apply_pending(path) is None  # Consumed: never repeated on later starts.
    restored = app.state.database.__class__(path, clock)
    with restored.connect() as connection:
        values = {row[0] for row in connection.execute('SELECT value FROM memories')}
    assert values == {'Biscuit'}


def test_a_damaged_backup_cannot_be_chosen(client, app, companion):
    folder = app.state.database.path.parent / 'backups'
    folder.mkdir(exist_ok=True)
    (folder / 'broken.zip').write_bytes(b'not a zip')
    assert client.get('/api/backups').json()['backups'][0]['readable'] is False
    assert client.post('/api/backups/broken.zip/restore').status_code == 422
    assert client.get('/api/backups').json()['pending'] is None


def test_the_launcher_restores_the_world_you_are_in(client, app, companion, monkeypatch, capsys, tmp_path):
    import socket

    from companion import launch
    made = client.post('/api/worlds', json={}).json()
    assert client.post(f"/api/worlds/{made['id']}/switch").status_code == 200
    archive = Path(client.post('/api/backups').json()['path'])
    first = app.state.database.home
    client.close()
    monkeypatch.setenv('COMPANION_DATA_DIR', str(first.parent))
    monkeypatch.delenv('COMPANION_DB', raising=False)
    monkeypatch.chdir(tmp_path)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    assert launch.main(['--restore', str(archive), '--port', str(port)]) == 0
    assert list((first.parent / made['folder']).glob('replaced-*/companion.sqlite3'))
    assert not list(first.parent.glob('replaced-*'))
