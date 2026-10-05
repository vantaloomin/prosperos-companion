"""Export an adapter with what is needed to use and share it responsibly (PRD "Recover and export").

The archive holds the adapter, `adapter.json` (format, base model, trigger word, digest, trainer
and the frozen training options and dataset summary) and `LICENSE-NOTICE.txt`. Training pictures,
captions and local paths are left out. A Krea 2 derivative is named with the "Krea" prefix its
license asks of redistributed derivatives.
"""
import json
import tempfile
import zipfile
from pathlib import Path

from companion.database import decode, optional
from companion.lora import appearance

COMPATIBILITY = {
    'krea': 'Trained for Krea 2 (Raw). Intended for Krea 2 Turbo in ComfyUI through LoraLoaderModelOnly. '
            'Not verified on hardware.',
}


def file_name(adapter: dict) -> str:
    stem = appearance.slug(adapter['name'])
    if 'krea' in adapter['base_model'].lower() and not stem.startswith('krea'):
        stem = f'Krea-{stem}'
    return f'{stem}.safetensors'


def summary(connection, adapter: dict) -> dict:
    run = optional(connection, 'SELECT * FROM lora_runs WHERE id=?', (adapter['run_id'],)) if adapter['run_id'] else None
    if run is None:
        return {}
    dataset = decode(run['dataset'])
    rights = {}
    for picture in dataset.get('pictures', []):
        rights[picture['rights']] = rights.get(picture['rights'], 0) + 1
    return {'run': {'trainer': adapter['trainer'], 'options': decode(run['options']), 'attempts': run['attempt'],
                    'base_model': run['base_model']},
            'dataset': {'pictures': len(dataset.get('pictures', [])), 'rights': rights,
                        'sha256': [picture['sha256'] for picture in dataset.get('pictures', [])]}}


def build(database, adapter_id) -> tuple[Path, str]:
    path = appearance.adapter_path(database, adapter_id)
    with database.connect() as connection:
        adapter = appearance.get_adapter(connection, adapter_id)
        details = summary(connection, adapter)
    name = file_name(adapter)
    compatibility = next((text for key, text in COMPATIBILITY.items() if key in adapter['base_model'].lower()),
                         f"Trained for {adapter['base_model']}. Use it with that model family.")
    metadata = {'name': adapter['name'], 'file': name, 'format': adapter['format'], 'base_model': adapter['base_model'],
                'trigger': adapter['trigger'], 'sha256': adapter['sha256'], 'bytes': adapter['bytes'],
                'origin': adapter['origin'], 'step': adapter['step'], 'created_at': adapter['created_at'],
                'compatibility': compatibility, 'made_with': 'Prospero Companion', **details}
    notice = '\n\n'.join(part for part in (
        f"{adapter['name']} ({adapter['format']} adapter for {adapter['base_model']})",
        compatibility,
        adapter['license_note'] or 'Check the base model license before sharing this adapter.',
        'This adapter depicts a fictional character. Do not use it to depict real people.') if part)
    handle = tempfile.NamedTemporaryFile(prefix='lora-export-', suffix='.zip', delete=False)
    handle.close()
    archive_path = Path(handle.name)
    with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_STORED) as archive:
        archive.write(path, name)
        archive.writestr('adapter.json', json.dumps(metadata, indent=2))
        archive.writestr('LICENSE-NOTICE.txt', notice + '\n')
    return archive_path, f"{Path(name).stem}.zip"
