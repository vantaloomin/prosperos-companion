"""Adapters and appearance versions: the Adopt step, and imports that skip training.

Images draw the character from the current appearance version. A text version uses only the
appearance description; a LoRA version adds an adapter on the local ComfyUI backend. Image jobs
freeze the version they used, so adopting another one changes only images requested afterwards,
and a failed or cancelled training run never touches what is adopted.
"""
import re
from pathlib import Path

from companion.characters import require_current
from companion.database import decode, encode, identifier, many, one, optional
from companion.errors import DomainError, require
from companion.lora import files

MAX_ADAPTER = 4 * 1024 * 1024 * 1024
KREA_NOTE = ('Krea 2 Community License: check the full terms before sharing. Redistributed derivatives must carry '
             'the license and a name starting with "Krea". https://www.krea.ai/krea-2-licensing')
TEXT_ONLY = {'id': None, 'number': 0, 'method': 'text', 'adapter_id': None, 'strength': 1.0, 'comfy_name': None,
             'note': 'The appearance description (no adapter adopted)', 'adopted_at': None}


def adapters_directory(database) -> Path:
    return files.folder(database, 'adapters')


def settings(connection) -> dict:
    return one(connection, 'SELECT * FROM lora_settings WHERE id=1')


def read_settings(database) -> dict:
    with database.connect() as connection:
        return settings(connection)


def update_settings(database, body) -> dict:
    changes = body.model_dump(exclude_none=True)
    for key in ('python_path', 'trainer_dir', 'comfy_lora_dir'):
        if changes.get(key):
            path = Path(changes[key]).expanduser()
            require(path.is_absolute(), 'Use a full path.', 422)
            changes[key] = str(path)
    with database.connect(write=True) as connection:
        if changes:
            assignments = {**changes, 'updated_at': database.now()}
            columns = ', '.join(f'{key}=?' for key in assignments)
            connection.execute(f'UPDATE lora_settings SET {columns} WHERE id=1', tuple(assignments.values()))
        return settings(connection)


def license_note(base_model: str) -> str:
    return KREA_NOTE if 'krea' in base_model.lower() else ''


def adapter_view(row: dict) -> dict:
    return {**row, 'metadata': decode(row['metadata']), 'available': row['removed_at'] is None}


def adapters(database) -> list[dict]:
    with database.connect() as connection:
        companion = require_current(connection)
        return [adapter_view(row) for row in many(
            connection, 'SELECT * FROM lora_adapters WHERE companion_id=? ORDER BY created_at DESC, rowid DESC',
            (companion['id'],))]


def get_adapter(connection, adapter_id) -> dict:
    companion = require_current(connection)
    return one(connection, 'SELECT * FROM lora_adapters WHERE id=? AND companion_id=?', (adapter_id, companion['id']))


def record_adapter(connection, timestamp, companion_id, path: Path, inspected: dict, digest: str, *, origin, name,
                   base_model, trainer='', trigger='', run_id=None, step=None, note='') -> str:
    adapter_id = path.stem
    connection.execute(
        'INSERT INTO lora_adapters (id, companion_id, origin, run_id, step, name, file, sha256, bytes, format, '
        'base_model, trainer, trigger, license_note, metadata, note, created_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (adapter_id, companion_id, origin, run_id, step, name, path.name, digest, inspected['bytes'],
         inspected['format'], base_model, trainer, trigger, license_note(base_model), encode(inspected['metadata']),
         note, timestamp))
    return adapter_id


async def import_adapter(database, stream, *, name, base_model, trigger='', note='') -> dict:
    """Bring in an adapter trained elsewhere, so training is never required (PRD)."""
    with database.connect() as connection:
        companion = require_current(connection)
    adapter_id = identifier()
    target = adapters_directory(database) / f'{adapter_id}.safetensors'
    _size, digest = await files.receive(stream, target, MAX_ADAPTER)
    try:
        inspected = files.require_adapter(target)
        with database.connect(write=True) as connection:
            duplicate = optional(connection, 'SELECT name FROM lora_adapters WHERE companion_id=? AND sha256=? '
                                 'AND removed_at IS NULL', (companion['id'], digest))
            if duplicate:
                raise DomainError(f'This adapter is already here as "{duplicate["name"]}".', 409, 'duplicate')
            record_adapter(connection, database.now(), companion['id'], target, inspected, digest, origin='imported',
                           name=name, base_model=base_model, trigger=trigger, note=note)
            return adapter_view(get_adapter(connection, adapter_id))
    except BaseException:
        target.unlink(missing_ok=True)
        raise


def remove_adapter(database, adapter_id) -> list[dict]:
    with database.connect(write=True) as connection:
        row = get_adapter(connection, adapter_id)
        current = current_version(connection, row['companion_id'])
        require(current['adapter_id'] != adapter_id,
                'Images use this adapter now. Adopt another appearance first.', 409)
        connection.execute('UPDATE lora_adapters SET removed_at=? WHERE id=?', (database.now(), adapter_id))
    (adapters_directory(database) / row['file']).unlink(missing_ok=True)
    return adapters(database)


def adapter_path(database, adapter_id) -> Path:
    with database.connect() as connection:
        row = get_adapter(connection, adapter_id)
    require(row['removed_at'] is None, 'This adapter was removed.', 410)
    try:
        return files.inside(adapters_directory(database), row['file'])
    except FileNotFoundError as error:
        raise DomainError('This adapter file is missing from the workspace.', 404) from error


def slug(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:40] or 'adapter'


def comfy_file_name(adapter: dict) -> str:
    """A flat, unique name in ComfyUI's loras folder (subfolder separators differ by platform)."""
    return f"prospero-{slug(adapter['name'])}-{adapter['sha256'][:8]}.safetensors"


def install(database, adapter_id) -> dict:
    """Copy the adapter into ComfyUI's loras folder when the user has named it. Returns the name
    ComfyUI will list and whether the file is there."""
    with database.connect() as connection:
        adapter = get_adapter(connection, adapter_id)
        folder = settings(connection)['comfy_lora_dir']
    name = comfy_file_name(adapter)
    if not folder:
        return {'comfy_name': name, 'installed': False,
                'note': f'Copy the adapter into ComfyUI\'s models/loras folder as {name}, or name that folder in '
                        'the LoRA settings so the app copies it.'}
    target_dir = Path(folder)
    require(target_dir.is_dir(), f'The ComfyUI loras folder {folder} does not exist.', 409)
    target = target_dir / name
    if not (target.is_file() and files.sha256_of(target) == adapter['sha256']):
        files.copy_verified(adapter_path(database, adapter_id), target)
    return {'comfy_name': name, 'installed': True, 'note': f'Copied to {target}.'}


def version_view(row: dict, adapter: dict | None = None) -> dict:
    return {**row, 'adapter': adapter_view(adapter) if adapter else None}


def current_version(connection, companion_id) -> dict:
    row = optional(connection, 'SELECT v.* FROM appearance_current c JOIN appearance_versions v ON v.id=c.version_id '
                   'WHERE c.companion_id=?', (companion_id,))
    return row or dict(TEXT_ONLY)


def current_for_images(connection) -> dict:
    """The appearance an image request freezes (PRD F2, F4)."""
    companion = require_current(connection)
    version = current_version(connection, companion['id'])
    frozen = {'appearance_version_id': version['id'], 'appearance_version': version['number'],
              'identity': version['method'], 'lora': None}
    if version['method'] == 'lora':
        adapter = one(connection, 'SELECT * FROM lora_adapters WHERE id=?', (version['adapter_id'],))
        frozen['lora'] = {'adapter_id': adapter['id'], 'name': adapter['name'], 'comfy_name': version['comfy_name'],
                          'strength': version['strength'], 'trigger': adapter['trigger'], 'sha256': adapter['sha256'],
                          'base_model': adapter['base_model'], 'format': adapter['format']}
    return frozen


def versions(database) -> dict:
    with database.connect() as connection:
        companion = require_current(connection)
        current = current_version(connection, companion['id'])
        rows = many(connection, 'SELECT * FROM appearance_versions WHERE companion_id=? ORDER BY number DESC',
                    (companion['id'],))
        listed = []
        for row in rows:
            adapter = optional(connection, 'SELECT * FROM lora_adapters WHERE id=?', (row['adapter_id'],)) \
                if row['adapter_id'] else None
            listed.append({**version_view(row, adapter), 'current': row['id'] == current['id']})
        return {'current': version_view(current, optional(connection, 'SELECT * FROM lora_adapters WHERE id=?',
                                                          (current['adapter_id'],)) if current['adapter_id'] else None),
                'versions': listed}


def adopt(database, body) -> dict:
    """Deliberately choose how future images draw the character."""
    installed = None
    if body.method == 'lora':
        require(body.adapter_id, 'Choose an adapter to adopt.', 422)
        adapter_path(database, body.adapter_id)
        installed = install(database, body.adapter_id)
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        if body.method == 'lora':
            adapter = get_adapter(connection, body.adapter_id)
            require(adapter['removed_at'] is None, 'This adapter was removed.', 410)
        number = (optional(connection, 'SELECT MAX(number) AS n FROM appearance_versions WHERE companion_id=?',
                           (companion['id'],)) or {}).get('n') or 0
        version_id = identifier()
        connection.execute(
            'INSERT INTO appearance_versions (id, companion_id, number, method, adapter_id, strength, comfy_name, '
            'note, adopted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (version_id, companion['id'], number + 1, body.method, body.adapter_id if body.method == 'lora' else None,
             body.strength, installed['comfy_name'] if installed else None, body.note, database.now()))
        connection.execute('INSERT INTO appearance_current (companion_id, version_id) VALUES (?, ?) '
                           'ON CONFLICT(companion_id) DO UPDATE SET version_id=excluded.version_id',
                           (companion['id'], version_id))
    return {**versions(database), 'install': installed}
