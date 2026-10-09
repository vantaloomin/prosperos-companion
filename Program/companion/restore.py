"""Replace the active workspace with a backup (PRD persistence section and M5).

The current workspace is never overwritten: its database, images and adapters move to
`replaced-<time>/` beside it first, and move back if the restore fails. A backup can be older
than deletions made since, so the deletion records the current workspace keeps are applied to
the restored one: deleted memories stay deleted and redacted messages stay redacted. Settings are not rolled
back either (Vanta, 2026-10-08): the current workspace's settings, model connections, image backends, lookups and
paired phones carry over, so nothing is switched off or paused. Restoring with no current workspace (a new
computer) still holds the restored one for review, since its connections belonged to another machine
(backup.hold_for_review).
"""
import json
import re
import shutil
import sqlite3
import zipfile
from pathlib import Path

from companion import backup
from companion.clock import Clock, stamp
from companion.database import Database, many
from companion.errors import DomainError, require
from companion.memory import records

MOVED = ('images', 'lora')
# What "settings" means for a restore, parents before the tables that refer to them.
KEPT_SETTINGS = ('workspace_settings', 'connection', 'model_profiles', 'model_routes', 'life_settings',
                 'image_settings', 'image_backends', 'context_settings', 'context_services', 'context_tools',
                 'lora_settings', 'notification_settings', 'phone_settings', 'phone_devices', 'phone_push',
                 'builtin_recall', 'voice_settings', 'prompt_overrides', 'debug_time')


def database_files(path: Path) -> list[Path]:
    return [path, path.with_name(path.name + '-wal'), path.with_name(path.name + '-shm')]


def settle(path: Path):
    connection = sqlite3.connect(path)
    try:
        connection.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    finally:
        connection.close()


def set_aside(database_path: Path, aside: Path) -> list[tuple[Path, Path]]:
    moves = [(item, aside / item.name) for item in database_files(database_path) if item.exists()]
    moves += [(database_path.parent / name, aside / name) for name in MOVED if (database_path.parent / name).exists()]
    aside.mkdir(parents=True)
    done = []
    try:
        for source, target in moves:
            shutil.move(source, target)
            done.append((source, target))
    except OSError as error:
        put_back(done)
        raise DomainError('The current workspace could not be moved aside; it is in use or locked. '
                          'Nothing was restored.', 409) from error
    return done


def put_back(moves: list[tuple[Path, Path]]):
    for source, target in reversed(moves):
        shutil.move(target, source)


def retained_deletions(previous: Path) -> dict:
    connection = sqlite3.connect(f'{previous.resolve().as_uri()}?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        return {'markers': [dict(row) for row in connection.execute('SELECT * FROM deletion_markers')],
                'declines': [dict(row) for row in connection.execute('SELECT * FROM memory_declines')]}
    finally:
        connection.close()


def apply_deletions(database: Database, retained: dict) -> dict:
    """Deletions made after the backup was taken still apply to what it brings back."""
    memories = sorted({item['target_id'] for item in retained['markers'] if item['kind'] == 'memory'})
    messages = sorted({item['target_id'] for item in retained['markers'] if item['kind'] == 'message'})
    with database.connect() as connection:
        present = {row['id'] for row in many(connection, 'SELECT id FROM memories')}
    deleted = []
    for memory_id in memories:
        if memory_id in present:
            deleted += records.delete(database, memory_id)['deleted_memory_ids']
            present -= set(deleted)
    with database.connect(write=True) as connection:
        timestamp = database.now()
        known = {row['id'] for row in many(connection, 'SELECT id FROM messages')}
        redacted = [identity for identity in messages if identity in known]
        records.redact_messages(connection, redacted, timestamp)
        connection.executemany('INSERT OR IGNORE INTO deletion_markers (target_id, kind, deleted_at) VALUES (?, ?, ?)',
                               [(item['target_id'], item['kind'], item['deleted_at']) for item in retained['markers']])
        connection.executemany('INSERT OR IGNORE INTO memory_declines (message_id, created_at) VALUES (?, ?)',
                               [(item['message_id'], item['created_at']) for item in retained['declines']
                                if item['message_id'] in known])
    return {'memories_deleted': len(set(deleted)), 'messages_redacted': len(redacted)}


def keep_settings(database: Database, previous: Path):
    """The settings of the workspace being replaced, instead of the backup's (or the hold a restore starts with)."""
    copy_settings(database.path, previous, KEPT_SETTINGS, database.now())


def copy_settings(target: Path, source: Path, tables: tuple[str, ...], timestamp: str):
    """`tables` in the workspace at `target` become those of the one at `source`: a restore keeps the current
    settings, and switching worlds carries them along (companion/worlds.py). `tables` lists parents first."""
    connection = sqlite3.connect(target, isolation_level=None)
    try:
        # A plain path: URI filenames in ATTACH need SQLite built with them on, which Windows' is not.
        connection.execute('ATTACH DATABASE ? AS kept', (str(Path(source).resolve()),))
        connection.execute('BEGIN IMMEDIATE')
        for table in reversed(tables):
            connection.execute(f'DELETE FROM main.{table}')
        for table in tables:
            ours = {row[1] for row in connection.execute(f'PRAGMA main.table_info({table})')}
            columns = ', '.join(row[1] for row in connection.execute(f'PRAGMA kept.table_info({table})')
                                if row[1] in ours)
            if columns:
                connection.execute(f'INSERT INTO main.{table} ({columns}) SELECT {columns} FROM kept.{table}')
        if connection.execute('SELECT paused_at FROM main.workspace_settings').fetchone()[0] is None:
            connection.execute('UPDATE main.pauses SET ended_at=? WHERE ended_at IS NULL', (timestamp,))
        connection.execute('COMMIT')
    except BaseException:
        if connection.in_transaction:
            connection.execute('ROLLBACK')
        raise
    finally:
        connection.close()


def replace_workspace(archive: Path, database_path: Path, clock=None) -> dict:
    backup.inspect(archive)  # Refuse a damaged or foreign archive before anything moves.
    previous = None
    moves = []
    if database_path.exists():
        settle(database_path)
        moment = stamp((clock or Clock()).now())
        aside = database_path.parent / f"replaced-{moment[:19].replace(':', '').replace('-', '')}"
        require(not aside.exists(), 'A workspace was already set aside this second; try again.', 409)
        moves = set_aside(database_path, aside)
        previous = aside / database_path.name
    try:
        restored = backup.restore(archive, database_path, clock)
    except BaseException:
        put_back(moves)
        if previous:
            previous.parent.rmdir()
        raise
    applied = apply_deletions(restored, retained_deletions(previous)) if previous else \
        {'memories_deleted': 0, 'messages_redacted': 0}
    if previous:
        keep_settings(restored, previous)
    return {'restored': str(database_path), 'previous': str(previous.parent) if previous else None,
            'assets': restored.restored_assets, 'deletions': applied}


# Restoring from the interface: the running app cannot replace its own open workspace, so it
# records the choice and the launcher applies it on the next start, before anything opens it.
PENDING = 'pending-restore.json'
BACKUP_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*\.zip$')


def backups_folder(workspace: Path) -> Path:
    return workspace / 'backups'


def archive_path(workspace: Path, name: str) -> Path:
    require(bool(BACKUP_NAME.match(name)), 'Choose a backup from the list.', 404)
    path = backups_folder(workspace) / name
    require(path.is_file(), 'That backup is no longer in the backups folder.', 404)
    return path


# Backups the app makes on its own, named for what they came before (companion/start_over.py, upgrade.py), and
# the automatic ones (companion/auto_backup.py).
KINDS = ('pre-upgrade', 'before-reset', 'before-delete', 'before-debug', 'auto')


def kind(name: str) -> str:
    return next((item for item in KINDS if name.startswith(item + '-')), 'backup')


def listing(workspace: Path) -> dict:
    """Backups in the workspace's folder, newest first, read from their manifests only."""
    items = []
    folder = backups_folder(workspace)
    found = [path for path in folder.glob('*.zip') if not path.name.startswith('.')] if folder.is_dir() else []
    for path in sorted(found, key=lambda item: item.name, reverse=True):  # Not macOS's `._` Finder files.
        entry = {'name': path.name, 'bytes': path.stat().st_size, 'kind': kind(path.name), 'readable': False}
        try:
            with zipfile.ZipFile(path) as handle:
                manifest = json.loads(handle.read(backup.MANIFEST_ENTRY))
            entry.update(readable=manifest.get('format') == backup.ARCHIVE_FORMAT,
                         created_at=manifest.get('created_at'), app_version=manifest.get('app_version'),
                         files=len(manifest.get('files', [])),
                         datasets_included=bool(manifest.get('datasets_included')))
        except (OSError, zipfile.BadZipFile, KeyError, ValueError):
            pass
        items.append(entry)
    return {'backups': items, 'pending': pending(workspace)}


def pending(workspace: Path) -> dict | None:
    try:
        value = json.loads((workspace / PENDING).read_text(encoding='utf-8'))
        return value if isinstance(value, dict) and BACKUP_NAME.match(str(value.get('name', ''))) else None
    except (OSError, ValueError):
        return None


def schedule(workspace: Path, name: str, timestamp: str) -> dict:
    """Checked in full now, so a damaged backup is refused while the user is still here."""
    backup.inspect(archive_path(workspace, name))
    (workspace / PENDING).write_text(json.dumps({'name': name, 'requested_at': timestamp}), encoding='utf-8')
    return listing(workspace)


def cancel(workspace: Path) -> dict:
    (workspace / PENDING).unlink(missing_ok=True)
    return listing(workspace)


def apply_pending(database_path: Path) -> tuple[str, dict | DomainError] | None:
    """Run a restore chosen in the interface. The request is consumed either way, so a restore that
    fails is reported once and never retried on every start."""
    workspace = database_path.parent
    chosen = pending(workspace)
    (workspace / PENDING).unlink(missing_ok=True)
    if not chosen:
        return None
    try:
        return chosen['name'], replace_workspace(archive_path(workspace, chosen['name']), database_path)
    except DomainError as error:
        return chosen['name'], error
