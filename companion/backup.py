"""Workspace backup archives with a Companion format marker.

An archive is a zip holding `manifest.json` and a consistent SQLite snapshot taken with the
online backup API. Restore only targets a new workspace path, validates the marker and digest,
and leaves the restored workspace paused with automatic memory and background activity off
until the user reviews it. Saved API keys are never in the database, so nothing carries over.
"""
import hashlib
import json
import sqlite3
import tempfile
import zipfile
from pathlib import Path

from companion.database import Database
from companion.errors import DomainError, require
from companion.identity import APP_ID, ARCHIVE_FORMAT, ARCHIVE_VERSION, SCHEMA_VERSION, VERSION

DATABASE_ENTRY = 'companion.sqlite3'
MANIFEST_ENTRY = 'manifest.json'


def snapshot(database: Database, target: Path):
    source = sqlite3.connect(database.path)
    destination = sqlite3.connect(target)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()


def create(database: Database, directory: Path) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    created_at = database.now()
    name = f"companion-{created_at[:19].replace(':', '').replace('-', '')}.zip"
    with tempfile.TemporaryDirectory() as scratch:
        copy = Path(scratch) / DATABASE_ENTRY
        snapshot(database, copy)
        content = copy.read_bytes()
    manifest = {'format': ARCHIVE_FORMAT, 'format_version': ARCHIVE_VERSION, 'app_id': APP_ID,
                'app_version': VERSION, 'schema_version': SCHEMA_VERSION, 'created_at': created_at,
                'database_sha256': hashlib.sha256(content).hexdigest(), 'database_bytes': len(content)}
    path = directory / name
    with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(MANIFEST_ENTRY, json.dumps(manifest, indent=2))
        archive.writestr(DATABASE_ENTRY, content)
    return {**manifest, 'path': str(path)}


def inspect(path: Path) -> dict:
    """Validate an archive without restoring it."""
    try:
        with zipfile.ZipFile(path) as archive:
            manifest = json.loads(archive.read(MANIFEST_ENTRY))
            content = archive.read(DATABASE_ENTRY)
    except (zipfile.BadZipFile, KeyError, ValueError) as error:
        raise DomainError('This file is not a Companion backup.', 422) from error
    require(isinstance(manifest, dict) and manifest.get('format') == ARCHIVE_FORMAT
            and manifest.get('app_id') == APP_ID, 'This file is not a Companion backup.', 422)
    require(manifest.get('format_version', 0) <= ARCHIVE_VERSION
            and manifest.get('schema_version', 0) <= SCHEMA_VERSION,
            'This backup was made by a newer Companion version.', 409)
    require(hashlib.sha256(content).hexdigest() == manifest.get('database_sha256'),
            'This backup is damaged: its database does not match the recorded digest.', 422)
    return {'manifest': manifest, 'content': content}


def restore(path: Path, target: Path, clock=None) -> Database:
    require(not target.exists(), 'Restore into a new workspace; the target already exists.', 409)
    checked = inspect(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(checked['content'])
    try:
        database = Database(target, clock)
        hold_for_review(database)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return database


def hold_for_review(database: Database):
    """A restore may hold memories forgotten after the backup was made; the user reviews first."""
    with database.connect(write=True) as connection:
        timestamp = database.now()
        connection.execute(
            'UPDATE workspace_settings SET automatic_memory=0, background_activity=0, review_required=1, '
            'paused_at=COALESCE(paused_at, ?), permission_revision=permission_revision+1, updated_at=? WHERE id=1',
            (timestamp, timestamp))
        connection.execute("INSERT INTO pauses (id, started_at) SELECT lower(hex(randomblob(16))), ? "
                           'WHERE NOT EXISTS (SELECT 1 FROM pauses WHERE ended_at IS NULL)', (timestamp,))
        connection.execute('UPDATE connection SET credential_ref=NULL')
        connection.execute('UPDATE image_backends SET credential_ref=NULL')
        connection.execute('UPDATE image_settings SET automatic_images=0')
        connection.execute("UPDATE messages SET status='incomplete', active=0 WHERE status='streaming'")
