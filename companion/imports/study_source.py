"""Read-only access to a Prospero's Study workspace.

The Study database is opened with `mode=ro` and `query_only`, so nothing here can write to it,
and only the library tables a character needs are read: `assets`, `asset_versions` and
`library_media` (shape as of prosperos-study server/schema.sql at bbcbde4). The Study keeps no
identity marker in its database, so a file counts as a Study workspace when it has those tables
with the Study's columns and no Companion marker.
"""
import base64
import hashlib
import json
import sqlite3
import tomllib
from contextlib import contextmanager
from pathlib import Path

from companion.errors import DomainError, require
from companion.identity import APP_ID

DATABASE_NAMES = (Path('data') / 'roleplay.sqlite3', Path('roleplay.sqlite3'))
STUDY_PACKAGE = 'roleplay-interface'
# Tables and columns read here; a database without them is not a Study workspace this version understands.
REQUIRED = {
    'assets': {'id', 'kind', 'latest_version_id', 'created_at'},
    'asset_versions': {'id', 'asset_id', 'number', 'name', 'content', 'note', 'created_at'},
    'library_media': {'sha256', 'source_base64', 'thumbnail_base64', 'width', 'height'},
}
# Tables only a Study workspace has; at least two must be present beside the library tables.
STUDY_MARKERS = ('stories', 'nodes', 'branches', 'side_threads', 'manifests')
NOT_STUDY = "This is not a Prospero's Study workspace. Choose the Study folder or its roleplay.sqlite3 file."


def locate(path_text: str, own_database: Path) -> tuple[Path, Path]:
    """The workspace folder and database file a user's path names."""
    path = Path(path_text).expanduser()
    require(path.is_absolute(), 'Use the full path to the Study folder or its database file.', 422)
    if path.is_dir():
        database = next((path / name for name in DATABASE_NAMES if (path / name).is_file()), None)
        require(database is not None, 'No Study database was found in this folder (looked for '
                'data/roleplay.sqlite3 and roleplay.sqlite3).', 404)
        workspace = path
    else:
        require(path.is_file(), 'Nothing exists at this path.', 404)
        database, workspace = path, path.parent.parent if path.parent.name == 'data' else path.parent
    require(database.resolve() != own_database.resolve(),
            "This is the Companion's own workspace. Choose a Prospero's Study workspace.", 409)
    return workspace, database


@contextmanager
def open_readonly(database: Path):
    try:
        connection = sqlite3.connect(f'{database.resolve().as_uri()}?mode=ro', uri=True, timeout=5)
    except sqlite3.Error as error:
        raise DomainError('The Study database could not be opened.', 409) from error
    connection.row_factory = sqlite3.Row
    try:
        connection.execute('PRAGMA query_only=ON')
        verify(connection)
        connection.execute('BEGIN')
        yield connection
    except sqlite3.DatabaseError as error:
        raise DomainError(NOT_STUDY, 422) from error
    finally:
        connection.close()


def tables(connection) -> set[str]:
    return {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def columns(connection, table) -> set[str]:
    return {row[1] for row in connection.execute(f'PRAGMA table_info({table})')}


def verify(connection):
    present = tables(connection)
    if 'app_identity' in present:
        marker = dict(connection.execute('SELECT key, value FROM app_identity').fetchall())
        require(marker.get('app_id') != APP_ID,
                "This is a Companion workspace, not a Prospero's Study workspace.", 409)
        raise DomainError(NOT_STUDY, 422)
    require(sum(name in present for name in STUDY_MARKERS) >= 2, NOT_STUDY, 422)
    for table, needed in REQUIRED.items():
        require(table in present and needed <= columns(connection, table), NOT_STUDY, 422)


def fingerprint(connection) -> str:
    """The Study has no schema version, so attribution records the shape of the tables read."""
    shape = {table: sorted(columns(connection, table)) for table in sorted(REQUIRED)}
    return hashlib.sha256(json.dumps(shape, sort_keys=True).encode()).hexdigest()[:16]


def app_version(workspace: Path, database: Path) -> str:
    """The Study version, when the workspace is the Study's own folder; the database records none."""
    for folder in dict.fromkeys((workspace, database.parent, database.parent.parent)):
        try:
            project = tomllib.loads((folder / 'pyproject.toml').read_text(encoding='utf-8')).get('project', {})
        except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
            continue
        if project.get('name') == STUDY_PACKAGE and isinstance(project.get('version'), str):
            return project['version']
    return ''


def count(connection, sql) -> int:
    try:
        return connection.execute(sql).fetchone()[0]
    except sqlite3.OperationalError:
        return 0


def characters(connection) -> list[dict]:
    rows = connection.execute(
        "SELECT a.id, v.id AS version_id, v.number, v.name, v.content, v.created_at, "
        "(SELECT COUNT(*) FROM asset_versions x WHERE x.asset_id=a.id) AS versions "
        "FROM assets a JOIN asset_versions v ON v.id=a.latest_version_id "
        "WHERE a.kind='character' ORDER BY v.name COLLATE NOCASE, a.id").fetchall()
    return [{'id': row['id'], 'name': row['name'], 'version_id': row['version_id'], 'version_number': row['number'],
             'versions': row['versions'], 'updated_at': row['created_at'],
             'has_artwork': bool(content(row['content']).get('artwork_sha256'))} for row in rows]


def content(text) -> dict:
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def character(connection, character_id) -> dict:
    row = connection.execute(
        "SELECT a.id, v.id AS version_id, v.number, v.name, v.content, v.created_at, "
        "(SELECT COUNT(*) FROM asset_versions x WHERE x.asset_id=a.id) AS versions "
        "FROM assets a JOIN asset_versions v ON v.id=a.latest_version_id "
        "WHERE a.id=? AND a.kind='character'", (character_id,)).fetchone()
    require(row is not None, 'This character is not in the Study workspace.', 404)
    return {**dict(row), 'content': content(row['content'])}


def artwork(connection, digest) -> dict | None:
    row = connection.execute('SELECT sha256, source_base64, thumbnail_base64, width, height FROM library_media '
                             'WHERE sha256=?', (digest,)).fetchone()
    if row is None:
        return None
    try:
        data = base64.b64decode(row['source_base64'], validate=True)
    except (ValueError, TypeError):
        data = b''
    return {'sha256': row['sha256'], 'data': data, 'thumbnail': row['thumbnail_base64'],
            'width': row['width'], 'height': row['height']}
