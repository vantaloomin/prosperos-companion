import json
import zipfile

import pytest

from companion import backup
from companion.errors import DomainError


def test_backup_round_trip_restores_paused_for_review(client, app, connected, tmp_path, clock):
    client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Pet', 'value': 'Biscuit'})
    created = client.post('/api/backups').json()
    assert created['format'] == 'prospero-companion-archive'
    restored = backup.restore(backup.Path(created['path']), tmp_path / 'restored' / 'companion.sqlite3', clock)
    with restored.connect() as connection:
        settings = dict(connection.execute('SELECT * FROM workspace_settings').fetchone())
        memory = connection.execute('SELECT value FROM memories').fetchone()[0]
        reference = connection.execute('SELECT credential_ref FROM connection').fetchone()[0]
    assert memory == 'Biscuit'
    assert settings['paused_at'] and settings['review_required'] == 1 and settings['automatic_memory'] == 0
    assert reference is None


def test_restored_workspace_needs_review_before_enabling_memory(tmp_path, app, client, companion, clock):
    created = backup.create(app.state.database, tmp_path / 'archives')
    restored = backup.restore(backup.Path(created['path']), tmp_path / 'fresh.sqlite3', clock)
    from companion import workspace
    from companion.models import SettingsUpdate
    with pytest.raises(DomainError):
        workspace.update(restored, SettingsUpdate(automatic_memory=True))
    updated = workspace.update(restored, SettingsUpdate(automatic_memory=True, review_complete=True))
    assert updated['automatic_memory'] is True and updated['review_required'] is False


def test_restore_refuses_an_existing_target(tmp_path, app, companion):
    created = backup.create(app.state.database, tmp_path / 'archives')
    with pytest.raises(DomainError):
        backup.restore(backup.Path(created['path']), app.state.database.path)


def test_foreign_and_damaged_archives_are_rejected(tmp_path, app, companion):
    foreign = tmp_path / 'study.zip'
    with zipfile.ZipFile(foreign, 'w') as archive:
        archive.writestr('manifest.json', json.dumps({'format': 'roleplay-archive'}))
        archive.writestr('companion.sqlite3', b'')
    with pytest.raises(DomainError):
        backup.inspect(foreign)
    created = backup.create(app.state.database, tmp_path / 'archives')
    damaged = tmp_path / 'damaged.zip'
    with zipfile.ZipFile(created['path']) as source, zipfile.ZipFile(damaged, 'w') as target:
        target.writestr('manifest.json', source.read('manifest.json'))
        target.writestr('companion.sqlite3', source.read('companion.sqlite3') + b'x')
    with pytest.raises(DomainError):
        backup.inspect(damaged)
