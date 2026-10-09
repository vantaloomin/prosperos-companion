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

from companion.clock import AppClock, Clock, stamp
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
        # Tests hand in a FixedClock; debug time (companion/debug_time.py) shifts the app clock wrapped around it.
        self.clock = clock if isinstance(clock, AppClock) else AppClock(clock)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        inspect_existing(self.path)
        if upgrade_needed(self.path):
            from companion import upgrade
            upgrade.run(self.path, self.now())
        with self.connect(write=True) as connection:
            initialize(connection, self.now())
        from companion import debug_time
        debug_time.load(self)

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
    ('life_settings', 'texts_first', 'INTEGER NOT NULL DEFAULT 1 CHECK (texts_first IN (0, 1))'),
    ('life_settings', 'texts_daily', 'INTEGER NOT NULL DEFAULT 2'),
    ('life_settings', 'texts_gap_hours', 'INTEGER NOT NULL DEFAULT 3'),
    ('life_settings', 'circle_size', 'INTEGER NOT NULL DEFAULT 0'),
    ('life_settings', 'drama', 'INTEGER NOT NULL DEFAULT 1'),
    ('life_settings', 'user_birthday', "TEXT NOT NULL DEFAULT ''"),
    ('life_settings', 'paced_replies', 'INTEGER NOT NULL DEFAULT 1'),
    ('life_settings', 'day_shifts', 'INTEGER NOT NULL DEFAULT 1 CHECK (day_shifts IN (0, 1))'),
    # On her mind (companion/life/thoughts.py): one private thought a day, shown folded on Today.
    # Who passed a secret on (companion/secrets.py): a person key or 'user'; NULL for those it started with.
    ('knowledge_holders', 'told_by', 'TEXT'),
    # Group chat moods (companion/moods.py): whether someone furious may walk out of this group.
    ('group_chats', 'walk_out', 'INTEGER NOT NULL DEFAULT 0 CHECK (walk_out IN (0, 1))'),
    ('life_settings', 'on_her_mind', 'INTEGER NOT NULL DEFAULT 1 CHECK (on_her_mind IN (0, 1))'),
    ('messages', 'held_until', 'TEXT'),
    ('messages', 'held_line', 'TEXT'),
    ('messages', 'held_notified', 'TEXT'),
    ('image_settings', 'chat_photos', 'INTEGER NOT NULL DEFAULT 1 CHECK (chat_photos IN (0, 1))'),
    ('image_settings', 'unprompted_photos', 'INTEGER NOT NULL DEFAULT 1 CHECK (unprompted_photos IN (0, 1))'),
    ('memories', 'person_id', 'TEXT'),
    ('workspace_settings', 'ask_about_people', 'INTEGER NOT NULL DEFAULT 1 CHECK (ask_about_people IN (0, 1))'),
    # A full reply after a holding text, dropped unseen because the user wrote again first (life/pacing.py).
    ('messages', 'superseded_at', 'TEXT'),
    ('workspace_settings', 'chat_retro_dark', 'INTEGER NOT NULL DEFAULT 0 CHECK (chat_retro_dark IN (0, 1))'),
    ('workspace_settings', 'story_mode', 'INTEGER NOT NULL DEFAULT 0 CHECK (story_mode IN (0, 1))'),
    # Launch buttons (companion/launcher.py): start the local programs in use with the Companion.
    ('workspace_settings', 'auto_launch', 'INTEGER NOT NULL DEFAULT 0 CHECK (auto_launch IN (0, 1))'),
    # Onboarding portraits (lora/portraits.py): a set whose later pictures follow the profile picture,
    # and the kept picture shown as the companion's profile picture.
    ('lora_generations', 'kind', "TEXT NOT NULL DEFAULT 'dataset' CHECK (kind IN ('dataset', 'portraits'))"),
    ('lora_gen_images', 'follows', 'INTEGER'),
    ('companions', 'portrait_reference_id', 'TEXT'),
    # Texts first became on by default; a workspace from before that is switched on once (see initialize).
    ('life_settings', 'texts_first_on_by_default', 'INTEGER NOT NULL DEFAULT 0'),
    # Memory is opt-out: every workspace gets automatic, sensitive and model memory turned on once (Vanta,
    # 2026-10-07: users can't be relied on to approve suggestions); turning them off afterwards sticks.
    ('workspace_settings', 'memory_on_by_default', 'INTEGER NOT NULL DEFAULT 0'),
    # Switching the main character (companion/cast.py): the townsperson a companion was made from, and
    # when they last stepped back from slot 1.
    ('companions', 'townsfolk_key', 'TEXT'),
    ('companions', 'stepped_back_at', 'TEXT'),
    # Townsfolk of the companion's own, once the user seeds new ones (companion/cast.py); empty keeps the
    # city's shared townsfolk.
    ('companions', 'town_seed', "TEXT NOT NULL DEFAULT ''"),
    # The routine slot still going when the life cursor last moved (companion/life/simulation.py).
    ('life_cursors', 'open_slot', 'TEXT'),
    ('prompt_overrides', 'default_text', 'TEXT'),
    # The user switched an image API backend to take NSFW requests too (images/backends.py).
    ('image_backends', 'allows_nsfw', 'INTEGER NOT NULL DEFAULT 0 CHECK (allows_nsfw IN (0, 1))'),
    # A closeness stage the user set, a ceiling and opt-in gentle cooling (memory/closeness.py).
    ('closeness_settings', 'head_start', 'INTEGER'),
    ('closeness_settings', 'set_on', 'TEXT'),
    ('closeness_settings', 'ceiling_level', 'INTEGER CHECK (ceiling_level BETWEEN 1 AND 5)'),
    ('closeness_settings', 'cooling_since', 'TEXT'),
    ('phone_settings', 'lan_enabled', 'INTEGER NOT NULL DEFAULT 0 CHECK (lan_enabled IN (0, 1))'),
    # One shared allowance for messages sent while the user is away, across every companion (companion/away.py).
    ('life_settings', 'away_daily', 'INTEGER NOT NULL DEFAULT 6'),
    # A group reply a secret check touched (companion/secrets.py): 'redrafted', 'revealed' or 'held'.
    ('group_messages', 'guard', 'TEXT'),
    ('workspace_settings', 'show_secret_slips', 'INTEGER NOT NULL DEFAULT 1 CHECK (show_secret_slips IN (0, 1))'),
    # Hidden values: moods and who heard the news stay unseen unless the user turns them on.
    ('workspace_settings', 'show_moods', 'INTEGER NOT NULL DEFAULT 0 CHECK (show_moods IN (0, 1))'),
    ('workspace_settings', 'show_news', 'INTEGER NOT NULL DEFAULT 0 CHECK (show_news IN (0, 1))'),
    ('workspace_settings', 'show_odds', 'INTEGER NOT NULL DEFAULT 0 CHECK (show_odds IN (0, 1))'),
    # Everyday events became automatic ("the world exists outside of User", Vanta 2026-10-08); a workspace
    # from before that is switched on once (see initialize), and turning it off afterwards sticks.
    ('life_settings', 'events_on_by_default', 'INTEGER NOT NULL DEFAULT 0'),
    # A moment that keeps coming up becomes a running joke on its own; one the user removed stays out.
    ('closeness_jokes', 'removed', 'INTEGER NOT NULL DEFAULT 0 CHECK (removed IN (0, 1))'),
    # How a companion carries a mark about something the user did, told to them as "you" (companion/consequences.py).
    ('marks', 'told', 'TEXT'),
    # The names and mark holders an outcome was decided with, so changing how it went can redo its marks.
    ('consequences', 'names', 'TEXT'),
    ('consequences', 'holders', 'TEXT'),
    # When the user read the one-time notice that the characters are AI and confirmed they are 18 or older
    # (companion/workspace.py); the app asks once, before anything else, until then.
    ('workspace_settings', 'ai_notice_at', 'TEXT'),
)

# CHECK constraints widened after a table first shipped, as (table, text the current definition
# contains). SQLite cannot alter a CHECK, so an older table is copied into the current definition.
WIDENED_CHECKS = (
    ('notification_deliveries', "'message')"),
    ('memory_vectors', "'storyline'))"),
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
    from companion.text_models import adopt_legacy, split_recall
    adopt_legacy(connection, timestamp)
    split_recall(connection, timestamp)
    for table in ('workspace_settings', 'life_settings', 'image_settings', 'context_settings', 'lora_settings',
                  'notification_settings', 'phone_settings', 'builtin_recall', 'voice_settings'):
        connection.execute(f'INSERT OR IGNORE INTO {table} (id, updated_at) VALUES (1, ?)', (timestamp,))
    connection.execute('UPDATE life_settings SET texts_first=1, texts_first_on_by_default=1 '
                       'WHERE texts_first_on_by_default=0')
    connection.execute('UPDATE life_settings SET automatic_events=1, events_on_by_default=1 WHERE events_on_by_default=0')
    connection.execute('UPDATE workspace_settings SET automatic_memory=1, sensitive_memory=1, '
                       'model_memory_suggestions=1, memory_on_by_default=1 WHERE memory_on_by_default=0')
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


def free_companion_slot(connection):
    """Workspaces from before switching companions allowed only one companions row, by a CHECK that SQLite
    cannot alter. Other tables reference the table, so it is rebuilt with foreign keys off, outside any
    transaction, as SQLite's own procedure for table changes does; the caller turns them back on."""
    row = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='companions'").fetchone()
    if not row or 'NOT NULL UNIQUE DEFAULT 1' not in row[0]:
        return
    definition = re.search(r'CREATE TABLE IF NOT EXISTS companions \((.*?)\n\);', SCHEMA, re.S).group(1)
    columns = ', '.join(item[1] for item in connection.execute('PRAGMA table_info(companions)'))
    connection.execute('PRAGMA foreign_keys=OFF')
    connection.execute('BEGIN IMMEDIATE')
    try:
        connection.execute(f'CREATE TABLE companions_widened ({definition})')
        for table, column, added in ADDED_COLUMNS:
            if table == 'companions':
                connection.execute(f'ALTER TABLE companions_widened ADD COLUMN {column} {added}')
        connection.execute(f'INSERT INTO companions_widened ({columns}) SELECT {columns} FROM companions')
        connection.execute('DROP TABLE companions')
        connection.execute('ALTER TABLE companions_widened RENAME TO companions')
        if connection.execute('PRAGMA foreign_key_check').fetchone():
            raise DomainError('The companions table could not be upgraded.', 500)
        connection.execute('COMMIT')
    except BaseException:
        connection.execute('ROLLBACK')
        raise


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
