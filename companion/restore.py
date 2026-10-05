"""Replace the active workspace with a backup (PRD persistence section and M5).

The current workspace is never overwritten: its database, images and adapters move to
`replaced-<time>/` beside it first, and move back if the restore fails. A backup can be older
than deletions made since, so the deletion records the current workspace keeps are applied to
the restored one: deleted memories stay deleted and redacted messages stay redacted. The restored
workspace then waits for the user's review like any restore (backup.hold_for_review).
"""
import shutil
import sqlite3
from pathlib import Path

from companion import backup
from companion.clock import Clock, stamp
from companion.database import Database, many
from companion.errors import DomainError, require
from companion.memory import records

MOVED = ('images', 'lora')


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
    return {'restored': str(database_path), 'previous': str(previous.parent) if previous else None,
            'assets': restored.restored_assets, 'deletions': applied}
