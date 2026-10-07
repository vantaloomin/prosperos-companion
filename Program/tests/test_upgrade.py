import sqlite3

import pytest

from companion import backup, upgrade
from companion.database import Database, schema_digest
from companion.errors import DomainError


def older_workspace(path):
    """A workspace as an earlier version left it: an older digest and a column it did not have yet."""
    database = Database(path)
    with database.connect(write=True) as connection:
        connection.execute("INSERT INTO workspace_settings (id, updated_at) VALUES (1, 'x') ON CONFLICT DO NOTHING")
        connection.execute("DELETE FROM app_identity WHERE key IN ('schema_digest', 'app_version')")
        connection.execute('ALTER TABLE memories DROP COLUMN dates_uncertain')
    return database


def columns(path, table):
    connection = sqlite3.connect(path)
    try:
        return {row[1] for row in connection.execute(f'PRAGMA table_info({table})')}
    finally:
        connection.close()


def test_upgrade_backs_up_first_then_migrates(tmp_path):
    path = tmp_path / 'companion.sqlite3'
    older_workspace(path)
    assert 'dates_uncertain' not in columns(path, 'memories')

    database = Database(path)

    assert 'dates_uncertain' in columns(path, 'memories')
    with database.connect() as connection:
        marker = dict(connection.execute('SELECT key, value FROM app_identity').fetchall())
    assert marker['schema_digest'] == schema_digest()
    saved = list((tmp_path / 'backups').glob('pre-upgrade-*.zip'))
    assert len(saved) == 1
    checked = backup.inspect(saved[0])
    assert checked['manifest']['app_version'] == 'unknown'
    # The backup holds the workspace as it was, and restores through the normal path.
    restored = backup.restore(saved[0], tmp_path / 'restored' / 'companion.sqlite3')
    assert 'dates_uncertain' in columns(restored.path, 'memories')
    assert not (tmp_path / 'companion.sqlite3.upgrading').exists()


def test_current_workspace_opens_without_an_upgrade(tmp_path):
    path = tmp_path / 'companion.sqlite3'
    Database(path)
    Database(path)
    assert not (tmp_path / 'backups').exists()


def test_failed_upgrade_leaves_the_workspace_untouched(tmp_path, monkeypatch):
    path = tmp_path / 'companion.sqlite3'
    older_workspace(path)
    connection = sqlite3.connect(path)
    connection.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    connection.close()
    before = path.read_bytes()

    def broken(staging, timestamp):
        raise sqlite3.OperationalError('disk I/O error')

    monkeypatch.setattr(upgrade, 'migrate', broken)
    with pytest.raises(DomainError) as error:
        Database(path)
    assert 'was not changed' in error.value.message and 'pre-upgrade-' in error.value.message
    assert path.read_bytes() == before
    assert not (tmp_path / 'companion.sqlite3.upgrading').exists()
    assert 'dates_uncertain' not in columns(path, 'memories')


def test_newer_workspace_is_refused_before_any_backup(tmp_path):
    path = tmp_path / 'companion.sqlite3'
    database = Database(path)
    with database.connect(write=True) as connection:
        connection.execute("UPDATE app_identity SET value='999' WHERE key='schema_version'")
    with pytest.raises(DomainError) as error:
        Database(path)
    assert error.value.status == 409
    assert not (tmp_path / 'backups').exists()


def test_only_recent_pre_upgrade_backups_are_kept(tmp_path):
    directory = tmp_path / 'backups'
    directory.mkdir()
    for day in range(1, 6):
        (directory / f'pre-upgrade-2026100{day}T000000.zip').write_bytes(b'')
    upgrade.prune(directory)
    assert sorted(item.name for item in directory.iterdir()) == [
        'pre-upgrade-20261003T000000.zip', 'pre-upgrade-20261004T000000.zip', 'pre-upgrade-20261005T000000.zip']


def test_upgrade_frees_the_companion_slot_and_keeps_everything(tmp_path):
    """Before switching companions, a CHECK allowed one companions row; the upgrade rebuilds the table
    without it and keeps the companion and everything pointing at them."""
    from companion.characters import create
    from companion.models import CharacterDefinition

    path = tmp_path / 'companion.sqlite3'
    database = Database(path)
    made = create(database, CharacterDefinition(name='Ada', timezone='UTC'))
    connection = sqlite3.connect(path, isolation_level=None)
    try:
        connection.execute('PRAGMA foreign_keys=OFF')
        connection.execute('BEGIN')
        connection.execute('CREATE TABLE companions_old (id TEXT PRIMARY KEY, slot INTEGER NOT NULL UNIQUE DEFAULT 1 '
                           'CHECK (slot = 1), active_version_id TEXT, active_timeline_id TEXT, created_at TEXT NOT NULL, '
                           'portrait_reference_id TEXT)')
        connection.execute('INSERT INTO companions_old SELECT id, slot, active_version_id, active_timeline_id, '
                           'created_at, portrait_reference_id FROM companions')
        connection.execute('DROP TABLE companions')
        connection.execute('ALTER TABLE companions_old RENAME TO companions')
        connection.execute("DELETE FROM app_identity WHERE key='schema_digest'")
        connection.execute('COMMIT')
    finally:
        connection.close()

    database = Database(path)

    with database.connect() as connection:
        sql = connection.execute("SELECT sql FROM sqlite_master WHERE name='companions'").fetchone()[0]
        assert 'NOT NULL UNIQUE' not in sql
        row = dict(connection.execute('SELECT * FROM companions').fetchone())
        assert row['id'] == made['id'] and row['active_timeline_id'] == made['active_timeline_id']
        assert 'townsfolk_key' in row and 'stepped_back_at' in row
        assert connection.execute('PRAGMA foreign_key_check').fetchall() == []
        # A second companion row can exist now, without a slot.
        connection.execute("INSERT INTO companions (id, slot, created_at) VALUES ('other', NULL, 'x')")
