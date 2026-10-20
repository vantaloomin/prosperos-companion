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


@pytest.mark.parametrize(('drama', 'expected'), [
    (0, (1, 1, 1, 0, 0)),  # An easy life: no breakups, no friends falling for the user.
    (1, (2, 2, 2, 1, 1)),  # A real life takes the defaults.
    (3, (3, 3, 3, 1, 1)),  # Bring on the drama.
])
def test_an_older_world_gets_the_new_realism_settings_of_its_preset(tmp_path, drama, expected):
    """A world from before v0.13 keeps the feel it was set to: on an easy life, breakups stay off."""
    from companion.database import add_columns, initialize
    connection = sqlite3.connect(tmp_path / 'old.sqlite3')
    initialize(connection, '2026-10-01T00:00:00Z')
    new = ('rough_patches_realism', 'steps_pace', 'love_life', 'friends_fall', 'breakups')
    for column in new:
        connection.execute(f'ALTER TABLE life_settings DROP COLUMN {column}')
    connection.execute('UPDATE life_settings SET drama=?', (drama,))
    add_columns(connection)
    assert connection.execute(f"SELECT {', '.join(new)} FROM life_settings").fetchone() == expected
    connection.close()


@pytest.mark.parametrize(('drama', 'paced', 'expected'), [
    (0, 0, (1, 1)),  # Easy: now and then, a few thoughts.
    (1, 1, (2, 2)),  # Real life takes the defaults.
    (3, 1, (3, 3)),  # Drama: often, everything on their mind.
    (1, 0, (2, 3)),  # I pull the strings hears everything on their mind.
])
def test_a_v015_world_gets_memes_and_inner_voice_by_its_preset(tmp_path, drama, paced, expected):
    """A world from before v0.16 keeps matching its preset on Settings > Realism (src/features/settings/presetChoices.ts)."""
    from companion.database import add_columns, initialize
    connection = sqlite3.connect(tmp_path / 'old.sqlite3')
    initialize(connection, '2026-10-01T00:00:00Z')
    for column in ('memes_realism', 'inner_voice'):
        connection.execute(f'ALTER TABLE life_settings DROP COLUMN {column}')
    connection.execute('UPDATE life_settings SET drama=?, paced_replies=?, day_shifts=?', (drama, paced, int(drama > 0)))
    add_columns(connection)
    assert connection.execute('SELECT memes_realism, inner_voice FROM life_settings').fetchone() == expected
    connection.close()


def test_a_new_world_starts_on_a_real_life(tmp_path):
    with Database(tmp_path / 'new.sqlite3').connect() as connection:
        row = connection.execute('SELECT drama, rough_patches_realism, steps_pace, love_life, friends_fall, breakups '
                                 'FROM life_settings').fetchone()
    assert tuple(row) == (1, 2, 2, 2, 1, 1)


def test_a_widened_table_keeps_the_columns_added_to_it_since(tmp_path):
    """A v0.14 workspace: circle_children with its older CHECK and without the later `whose` column. Widening the
    CHECK copies the table, so the column added just before must come along, with every row."""
    path = tmp_path / 'companion.sqlite3'
    older_workspace(path)
    connection = sqlite3.connect(path)
    connection.execute('DROP TABLE circle_children')
    connection.execute(
        "CREATE TABLE circle_children (id TEXT PRIMARY KEY, timeline_id TEXT NOT NULL, parent_id TEXT NOT NULL, "
        "storyline_id TEXT NOT NULL, name TEXT NOT NULL, pronouns TEXT NOT NULL CHECK (pronouns IN ('she/her', "
        "'he/him', 'they/them')), title TEXT NOT NULL CHECK (title IN ('family', 'godchild', 'friend')), "
        "born_on TEXT NOT NULL, status TEXT NOT NULL CHECK (status IN ('expected', 'born', 'ended')), "
        'created_at TEXT NOT NULL, updated_at TEXT NOT NULL)')
    connection.execute("INSERT INTO companions (id, created_at) VALUES ('k1', 'x')")
    connection.execute("INSERT INTO timelines (id, companion_id, status, created_at) VALUES ('t1', 'k1', 'active', 'x')")
    connection.execute("INSERT INTO circle_children VALUES ('c1', 't1', 'p1', 's1', 'Nova', 'she/her', 'family', "
                       "'2026-09-01', 'born', 'x', 'x')")
    connection.commit()
    connection.close()

    database = Database(path)

    with database.connect(write=True) as connection:
        row = connection.execute("SELECT name, title, whose FROM circle_children WHERE id='c1'").fetchone()
        assert tuple(row) == ('Nova', 'family', '')
        connection.execute("INSERT INTO circle_children (id, timeline_id, parent_id, storyline_id, name, pronouns, "
                           "title, born_on, status, created_at, updated_at, whose) VALUES ('c2', 't1', 'p1', 's2', "
                           "'Ivy', 'she/her', 'ours', '2027-01-01', 'born', 'x', 'x', 'companion')")
