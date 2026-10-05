"""SQLite access adapted from prosperos-study server/database.py at bbcbde4.

Opening a database checks the Companion identity marker first: a Study database or any
other non-empty SQLite file is refused rather than silently gaining Companion tables.
"""
import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from companion.clock import Clock, stamp
from companion.errors import DomainError, require
from companion.identity import APP_ID, SCHEMA_VERSION, VERSION, database_path

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
        if upgrade_needed(self.path):
            from companion import upgrade
            upgrade.run(self.path, self.now())
        with self.connect(write=True) as connection:
            initialize(connection, self.now())

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


# Columns added after a table first shipped. CREATE TABLE IF NOT EXISTS leaves an existing table
# alone, so a workspace created earlier gains them here.
ADDED_COLUMNS = (
    ('life_settings', 'phrase_with_model', 'INTEGER NOT NULL DEFAULT 1 CHECK (phrase_with_model IN (0, 1))'),
    ('connection', 'embedding_model', 'TEXT'),
    ('memory_jobs', 'model_status', 'TEXT'),
    ('workspace_settings', 'model_memory_suggestions',
     'INTEGER NOT NULL DEFAULT 0 CHECK (model_memory_suggestions IN (0, 1))'),
    ('memories', 'subject_key', "TEXT NOT NULL DEFAULT ''"),
    ('memories', 'origin', "TEXT NOT NULL DEFAULT 'user' CHECK (origin IN ('user', 'automatic', 'suggestion'))"),
    ('memories', 'ended_by_id', 'TEXT'),
    ('memories', 'merged_into_id', 'TEXT'),
    ('memories', 'dates_uncertain', 'INTEGER NOT NULL DEFAULT 0 CHECK (dates_uncertain IN (0, 1))'),
    ('timelines', 'label', "TEXT NOT NULL DEFAULT ''"),
    ('timelines', 'fork_message_id', 'TEXT'),
    ('timelines', 'forked_at', 'TEXT'),
    ('timelines', 'draft', 'TEXT'),
    ('timelines', 'activated_at', 'TEXT'),
    ('messages', 'origin_id', 'TEXT'),
    ('workspace_settings', 'user_timezone_source',
     "TEXT NOT NULL DEFAULT 'default' CHECK (user_timezone_source IN ('default', 'pc', 'chosen'))"),
    ('context_settings', 'read_links', 'INTEGER NOT NULL DEFAULT 1 CHECK (read_links IN (0, 1))'),
    ('workspace_settings', 'chat_style',
     "TEXT NOT NULL DEFAULT 'feed' CHECK (chat_style IN ('feed', 'bubbles', 'community', 'retro', 'novel'))"),
    ('workspace_settings', 'chat_sounds', 'INTEGER NOT NULL DEFAULT 0 CHECK (chat_sounds IN (0, 1))'),
    ('life_settings', 'texts_first', 'INTEGER NOT NULL DEFAULT 0 CHECK (texts_first IN (0, 1))'),
    ('life_settings', 'texts_daily', 'INTEGER NOT NULL DEFAULT 2'),
    ('life_settings', 'texts_gap_hours', 'INTEGER NOT NULL DEFAULT 3'),
    ('image_settings', 'chat_photos', 'INTEGER NOT NULL DEFAULT 1 CHECK (chat_photos IN (0, 1))'),
    ('image_settings', 'unprompted_photos', 'INTEGER NOT NULL DEFAULT 1 CHECK (unprompted_photos IN (0, 1))'),
    ('memories', 'person_id', 'TEXT'),
    ('workspace_settings', 'ask_about_people', 'INTEGER NOT NULL DEFAULT 1 CHECK (ask_about_people IN (0, 1))'),
)

# CHECK constraints widened after a table first shipped, as (table, text the current definition
# contains). SQLite cannot alter a CHECK, so an older table is copied into the current definition.
WIDENED_CHECKS = (
    ('notification_deliveries', "'message')"),
)


def schema_digest() -> str:
    """Changes whenever schema.sql or ADDED_COLUMNS does, so an upgrade is noticed without a version bump."""
    return hashlib.sha256((SCHEMA + repr(ADDED_COLUMNS) + repr(WIDENED_CHECKS)).encode('utf-8')).hexdigest()


def initialize(connection, timestamp: str):
    claim_identity(connection)
    connection.executescript(SCHEMA)
    add_columns(connection)
    widen_context_categories(connection)
    widen_checks(connection)
    connection.execute('CREATE INDEX IF NOT EXISTS messages_origin ON messages(origin_id)')
    connection.execute('CREATE INDEX IF NOT EXISTS memories_person ON memories(person_id)')
    backfill_subject_keys(connection)
    from companion.text_models import adopt_legacy
    adopt_legacy(connection, timestamp)
    for table in ('workspace_settings', 'life_settings', 'image_settings', 'context_settings', 'lora_settings',
                  'notification_settings'):
        connection.execute(f'INSERT OR IGNORE INTO {table} (id, updated_at) VALUES (1, ?)', (timestamp,))
    connection.executemany('INSERT OR REPLACE INTO app_identity (key, value) VALUES (?, ?)',
                           (('schema_version', str(SCHEMA_VERSION)), ('schema_digest', schema_digest()),
                            ('app_version', VERSION)))


def stored_identity(path: Path) -> dict:
    connection = sqlite3.connect(f'{path.resolve().as_uri()}?mode=ro', uri=True)
    try:
        return dict(connection.execute('SELECT key, value FROM app_identity').fetchall())
    finally:
        connection.close()


def upgrade_needed(path: Path) -> bool:
    """An existing workspace whose schema differs from this version's goes through the safe upgrade."""
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        return stored_identity(path).get('schema_digest') != schema_digest()
    except sqlite3.DatabaseError:
        return False  # An empty database without an identity yet.


def add_columns(connection):
    for table, column, definition in ADDED_COLUMNS:
        existing = {row[1] for row in connection.execute(f'PRAGMA table_info({table})')}
        if column not in existing:
            connection.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')


def widen_context_categories(connection):
    """Workspaces from before link reading limited lookup categories with a CHECK, which SQLite cannot alter:
    the table is copied into the current definition, keeping every mapping."""
    row = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='context_tools'").fetchone()
    if not row or "'local_events')" not in row[0]:
        return
    definition = re.search(r'CREATE TABLE IF NOT EXISTS context_tools \((.*?)\n\);', SCHEMA, re.S).group(1)
    columns = 'service_id, category, tool, arguments, run_in, enabled, approved, updated_at'
    connection.execute(f'CREATE TABLE context_tools_widened ({definition})')
    connection.execute(f'INSERT INTO context_tools_widened ({columns}) SELECT {columns} FROM context_tools')
    connection.execute('DROP TABLE context_tools')
    connection.execute('ALTER TABLE context_tools_widened RENAME TO context_tools')


def widen_checks(connection):
    for table, marker in WIDENED_CHECKS:
        row = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
        if not row or marker in row[0]:
            continue
        definition = re.search(rf'CREATE TABLE IF NOT EXISTS {table} \((.*?)\n\);', SCHEMA, re.S).group(1)
        columns = ', '.join(item[1] for item in connection.execute(f'PRAGMA table_info({table})'))
        connection.execute(f'CREATE TABLE {table}_widened ({definition})')
        connection.execute(f'INSERT INTO {table}_widened ({columns}) SELECT {columns} FROM {table}')
        connection.execute(f'DROP TABLE {table}')
        connection.execute(f'ALTER TABLE {table}_widened RENAME TO {table}')


def backfill_subject_keys(connection):
    from companion.memory.extraction import subject_key
    rows = connection.execute("SELECT id, subject FROM memories WHERE subject_key=''").fetchall()
    connection.executemany('UPDATE memories SET subject_key=? WHERE id=?',
                           [(subject_key(row[1]), row[0]) for row in rows])


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
