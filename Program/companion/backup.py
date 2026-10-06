"""Workspace backup archives with a Companion format marker.

An archive is a zip holding `manifest.json`, a consistent SQLite snapshot taken with the online
backup API, and the files its records name: finished images, adapters that have not been removed
and, when chosen, the reference pictures (PRD "selective dataset inclusion"). Each file sits at its
workspace-relative path, stored uncompressed and listed with its SHA-256. Training folders are
never included; a chosen checkpoint is already copied into `lora/adapters/`.

Restore only targets a new workspace path, validates the marker and every digest before writing
anything, checks the files the restored records name, and leaves the workspace paused for review:
automatic memory, background activity and automatic images off, keys and tool approvals dropped,
queued images and running training interrupted. Saved API keys are never in the database.
"""
import hashlib
import json
import sqlite3
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from companion.database import Database
from companion.errors import DomainError, require
from companion.identity import APP_ID, ARCHIVE_FORMAT, ARCHIVE_VERSION, SCHEMA_VERSION, VERSION

DATABASE_ENTRY = 'companion.sqlite3'
MANIFEST_ENTRY = 'manifest.json'
# Folders whose files an archive may carry, with the records that name them.
FOLDERS = {
    'images': "SELECT output_file FROM image_jobs WHERE status='completed' AND output_file IS NOT NULL",
    'images/raw': 'SELECT raw_file FROM image_jobs WHERE raw_file IS NOT NULL',
    'lora/adapters': 'SELECT file FROM lora_adapters WHERE removed_at IS NULL',
    'lora/references': 'SELECT file FROM lora_references UNION SELECT crop_file FROM lora_references '
                       'WHERE crop_file IS NOT NULL',
}
DATASET_FOLDERS = ('lora/references',)
DAMAGED = 'This backup is damaged: {} does not match its recorded digest.'


def snapshot(source_path: Path, target: Path):
    source = sqlite3.connect(source_path)
    destination = sqlite3.connect(target)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()


def file_digest(handle) -> tuple[str, int]:
    sha, size = hashlib.sha256(), 0
    for block in iter(lambda: handle.read(1 << 20), b''):
        sha.update(block)
        size += len(block)
    return sha.hexdigest(), size


def named_files(copy: Path, workspace: Path, include_datasets: bool) -> list[tuple[str, Path]]:
    """Files the snapshot's records name that exist in the workspace, by archive entry."""
    connection = sqlite3.connect(copy)
    try:
        found = {}
        for folder, query in FOLDERS.items():
            if folder in DATASET_FOLDERS and not include_datasets:
                continue
            for (name,) in connection.execute(query):
                source = workspace / folder / name
                if name and Path(name).name == name and source.is_file():
                    found[f'{folder}/{name}'] = source
        return sorted(found.items())
    finally:
        connection.close()


def archive(source_path: Path, path: Path, created_at: str, schema_version: int = SCHEMA_VERSION,
            app_version: str = VERSION, *, assets: bool = True, include_datasets: bool = False) -> dict:
    """Write a verified archive of the workspace at source_path, whatever schema it has."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as scratch:
        copy = Path(scratch) / DATABASE_ENTRY
        snapshot(source_path, copy)
        content = copy.read_bytes()
        files = named_files(copy, source_path.parent, include_datasets) if assets else []
    manifest = {'format': ARCHIVE_FORMAT, 'format_version': ARCHIVE_VERSION, 'app_id': APP_ID,
                'app_version': app_version, 'schema_version': schema_version, 'created_at': created_at,
                'database_sha256': hashlib.sha256(content).hexdigest(), 'database_bytes': len(content),
                'assets_included': assets, 'datasets_included': assets and include_datasets, 'files': []}
    try:
        with zipfile.ZipFile(path, 'x', compression=zipfile.ZIP_DEFLATED) as handle:
            handle.writestr(DATABASE_ENTRY, content)
            for entry, source in files:
                with source.open('rb') as stream:
                    sha, size = file_digest(stream)
                # Images and adapters are already compressed; storing them keeps backups fast.
                handle.write(source, entry, compress_type=zipfile.ZIP_STORED)
                manifest['files'].append({'path': entry, 'sha256': sha, 'bytes': size})
            handle.writestr(MANIFEST_ENTRY, json.dumps(manifest, indent=2))
        inspect(path)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return {**manifest, 'path': str(path)}


def create(database: Database, directory: Path, include_datasets: bool = False) -> dict:
    created_at = database.now()
    name = f"companion-{created_at[:19].replace(':', '').replace('-', '')}.zip"
    return archive(database.path, directory / name, created_at, include_datasets=include_datasets)


def valid_entry(name) -> bool:
    if not isinstance(name, str):
        return False
    path = PurePosixPath(name)
    return (not path.is_absolute() and '\\' not in name and ':' not in name
            and str(path.parent) in FOLDERS and path.name not in ('', '.', '..'))


def inspect(path: Path) -> dict:
    """Validate an archive, including every file digest, without restoring it."""
    try:
        with zipfile.ZipFile(path) as handle:
            manifest = json.loads(handle.read(MANIFEST_ENTRY))
            require(isinstance(manifest, dict) and manifest.get('format') == ARCHIVE_FORMAT
                    and manifest.get('app_id') == APP_ID, 'This file is not a Companion backup.', 422)
            require(manifest.get('format_version', 0) <= ARCHIVE_VERSION
                    and manifest.get('schema_version', 0) <= SCHEMA_VERSION,
                    'This backup was made by a newer Companion version.', 409)
            content = handle.read(DATABASE_ENTRY)
            require(hashlib.sha256(content).hexdigest() == manifest.get('database_sha256'),
                    DAMAGED.format('its database'), 422)
            files = manifest.get('files', [])
            require(isinstance(files, list) and all(isinstance(item, dict) and valid_entry(item.get('path'))
                                                    for item in files),
                    'This backup lists a file outside the workspace folders.', 422)
            for item in files:
                with handle.open(item['path']) as stream:
                    sha, size = file_digest(stream)
                require(sha == item.get('sha256') and size == item.get('bytes', size), DAMAGED.format(item['path']),
                        422)
    except (zipfile.BadZipFile, KeyError, ValueError) as error:
        raise DomainError('This file is not a Companion backup.', 422) from error
    return {'manifest': manifest, 'content': content}


def restore(path: Path, target: Path, clock=None) -> Database:
    require(not target.exists(), 'Restore into a new workspace; the target already exists.', 409)
    checked = inspect(path)
    workspace = target.parent
    files = [item['path'] for item in checked['manifest'].get('files', [])]
    require(not any((workspace / name).exists() for name in files),
            'Restore into a new workspace; its files already exist there.', 409)
    workspace.mkdir(parents=True, exist_ok=True)
    target.write_bytes(checked['content'])
    written = []
    try:
        with zipfile.ZipFile(path) as handle:
            for name in files:
                destination = workspace / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                with handle.open(name) as source, destination.open('xb') as output:
                    written.append(destination)
                    while chunk := source.read(1 << 20):
                        output.write(chunk)
        database = Database(target, clock)
        hold_for_review(database)
        database.restored_assets = check_assets(database, checked['manifest'])
    except BaseException:
        target.unlink(missing_ok=True)
        for item in written:
            item.unlink(missing_ok=True)
        raise
    return database


def present(folder: Path, name: str | None, sha256: str | None = None) -> bool:
    if not name or Path(name).name != name or not (folder / name).is_file():
        return False
    if sha256 is None:
        return True
    with (folder / name).open('rb') as stream:
        return file_digest(stream)[0] == sha256


def check_assets(database: Database, manifest: dict) -> dict:
    """Which files the restored records name are present and intact, and which are not."""
    workspace = database.path.parent
    # Reference pictures deliberately left out are excluded, not missing.
    left_out = manifest.get('assets_included', True) and not manifest.get('datasets_included', False)
    with database.connect() as connection:
        rows = [('image', row['id'], workspace / 'images', row['output_file'], None) for row in connection.execute(
            "SELECT id, output_file FROM image_jobs WHERE status='completed' AND output_file IS NOT NULL")]
        rows += [('reference', row['id'], workspace / 'lora/references', row['file'], row['sha256'])
                 for row in connection.execute('SELECT id, file, sha256 FROM lora_references')]
        rows += [('adapter', row['id'], workspace / 'lora/adapters', row['file'], row['sha256'])
                 for row in connection.execute('SELECT id, file, sha256 FROM lora_adapters WHERE removed_at IS NULL')]
        selected = {row[0] for row in connection.execute(
            'SELECT v.adapter_id FROM appearance_current c JOIN appearance_versions v ON v.id=c.version_id '
            'WHERE v.adapter_id IS NOT NULL')}
    missing, excluded = [], []
    for kind, record_id, folder, name, sha256 in rows:
        if not present(folder, name, sha256):
            (excluded if kind == 'reference' and left_out else missing).append({'kind': kind, 'id': record_id})
    missing_ids = {item['id'] for item in missing}
    return {'checked': len(rows), 'missing': missing, 'excluded': excluded,
            'selected_appearance_intact': not (selected & missing_ids)}


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
        connection.execute('UPDATE model_profiles SET credential_ref=NULL')
        connection.execute('UPDATE image_backends SET credential_ref=NULL')
        connection.execute('UPDATE image_settings SET automatic_images=0')
        connection.execute('UPDATE notification_settings SET enabled=0')
        # Phones paired with the restored copy sign in again, and phone access waits to be turned back on.
        connection.execute('UPDATE phone_settings SET enabled=0')
        connection.execute('UPDATE phone_devices SET revoked_at=COALESCE(revoked_at, ?)', (timestamp,))
        connection.execute('DELETE FROM phone_push')
        connection.execute("UPDATE notifications SET status='cancelled', reason='Restored from a backup.' "
                           "WHERE status='queued'")
        # Context lookups send data out, so a restored workspace asks again before any run.
        connection.execute('UPDATE context_services SET credential_ref=NULL')
        connection.execute('UPDATE context_tools SET enabled=0, approved=NULL')
        connection.execute("UPDATE messages SET status='incomplete', active=0 WHERE status='streaming'")
        # Training in progress when the backup was taken never resumes on its own. Its process id
        # belonged to the machine that made the backup, so it is dropped rather than checked.
        connection.execute("UPDATE lora_runs SET status='interrupted', pid=NULL, error_code='interrupted', "
                           "error='Restored from a backup. Resume from a verified checkpoint or restart.', "
                           "finished_at=COALESCE(finished_at, ?) WHERE status='running'", (timestamp,))
    # Queued and running images, evaluations and generated pictures become interrupted, as after a restart.
    from companion.images import jobs
    from companion.lora import evaluation, generation
    jobs.recover(database)
    evaluation.recover(database)
    generation.recover(database)
