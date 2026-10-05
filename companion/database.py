"""SQLite access adapted from prosperos-study server/database.py at bbcbde4.

Opening a database checks the Companion identity marker first: a Study database or any
other non-empty SQLite file is refused rather than silently gaining Companion tables.
"""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from companion.clock import Clock, stamp
from companion.errors import DomainError, require
from companion.identity import APP_ID, SCHEMA_VERSION, database_path

SCHEMA = Path(__file__).with_name('schema.sql').read_text(encoding='utf-8')


def identifier() -> str:
    return uuid4().hex


def encode(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def decode(value: str | None):
    return None if value is None else json.loads(value)


class Database:
    def __init__(self, path: str | Path | None = None, clock: Clock | None = None):
        self.path = Path(path or database_path())
        self.clock = clock or Clock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        inspect_existing(self.path)
        with self.connect(write=True) as connection:
            claim_identity(connection)
            connection.executescript(SCHEMA)
            connection.execute('INSERT OR IGNORE INTO workspace_settings (id, updated_at) VALUES (1, ?)',
                               (self.now(),))

    def now(self) -> str:
        return stamp(self.clock.now())

    @contextmanager
    def connect(self, write: bool = False):
        connection = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA journal_mode=WAL')
        try:
            connection.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()


FOREIGN = 'This database belongs to another application. Choose a Companion workspace.'


def inspect_existing(path: Path):
    """Read-only check, so a foreign file is refused before any pragma can change it."""
    if not path.exists() or path.stat().st_size == 0:
        return
    try:
        connection = sqlite3.connect(f'{path.resolve().as_uri()}?mode=ro', uri=True)
        try:
            validate_identity(connection)
        finally:
            connection.close()
    except sqlite3.DatabaseError as error:
        raise DomainError(FOREIGN, 409) from error


def validate_identity(connection):
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'app_identity' not in tables:
        require(not tables, FOREIGN, 409)
        return
    marker = dict(connection.execute('SELECT key, value FROM app_identity').fetchall())
    require(marker.get('app_id') == APP_ID, FOREIGN, 409)
    require(int(marker.get('schema_version', 0)) <= SCHEMA_VERSION,
            'This workspace was created by a newer Companion version.', 409)


def claim_identity(connection):
    validate_identity(connection)
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'app_identity' not in tables:
        connection.execute('CREATE TABLE app_identity (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        connection.executemany('INSERT INTO app_identity (key, value) VALUES (?, ?)',
                               (('app_id', APP_ID), ('schema_version', str(SCHEMA_VERSION))))


def one(connection, sql: str, values=()) -> dict:
    row = connection.execute(sql, values).fetchone()
    require(row is not None, 'This item could not be found.', 404)
    return dict(row)


def optional(connection, sql: str, values=()) -> dict | None:
    row = connection.execute(sql, values).fetchone()
    return None if row is None else dict(row)


def many(connection, sql: str, values=()) -> list[dict]:
    return [dict(row) for row in connection.execute(sql, values).fetchall()]


def settings(connection) -> dict:
    return one(connection, 'SELECT * FROM workspace_settings WHERE id=1')


def bump_memory_revision(connection, timestamp) -> int:
    connection.execute('UPDATE workspace_settings SET memory_revision=memory_revision+1, updated_at=? '
                       'WHERE id=1', (timestamp,))
    return settings(connection)['memory_revision']
