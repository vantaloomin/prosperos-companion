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
        review = connection.execute('SELECT review_required, paused_at FROM workspace_settings').fetchone()
    assert kept['id'] in ids and forgotten['id'] not in ids
    assert marker[0] == 'memory'
    assert review[0] == 1 and review[1]


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
