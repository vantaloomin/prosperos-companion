"""Backups carry images, reference pictures and adapters, and restore checks them (PRD recovery rows)."""
import asyncio
import json
import zipfile
from pathlib import Path

import pytest

from companion import backup
from companion.errors import DomainError
from tests.test_images import add_backend, make_post, ok
from tests.test_lora import adapters, add_picture, app, client, import_adapter, picture, safetensors  # noqa: F401


@pytest.fixture
def workspace(client, companion, clock, app):  # noqa: F811
    add_backend(client, kind='comfyui', base_url='http://127.0.0.1:8188')
    post = make_post(client, clock, key='event-photo')
    ok(client.post('/api/images/jobs', json={'post_id': post['id']}))
    asyncio.run(app.state.images.drain())
    reference = ok(add_picture(client, picture(1)))
    adapter = ok(import_adapter(client, safetensors()))
    ok(client.post('/api/lora/appearance', json={'method': 'lora', 'adapter_id': adapter['id']}))
    queued = make_post(client, clock, key='event-queued')
    ok(client.post('/api/images/jobs', json={'post_id': queued['id']}))
    return {'reference': reference, 'adapter': adapter}


def test_restore_brings_back_history_images_and_the_selected_adapter(client, app, workspace, tmp_path):  # noqa: F811
    created = ok(client.post('/api/backups', params={'include_datasets': 'true'}))
    assert created['format_version'] == 2 and len(created['files']) >= 3 and created['datasets_included']
    restored = backup.restore(Path(created['path']), tmp_path / 'restored' / 'companion.sqlite3')
    report = restored.restored_assets
    assert report['missing'] == [] and report['excluded'] == [] and report['checked'] >= 3
    assert report['selected_appearance_intact']
    with restored.connect() as connection:
        statuses = {row[0] for row in connection.execute('SELECT status FROM image_jobs')}
        current = connection.execute('SELECT v.adapter_id FROM appearance_current c '
                                     'JOIN appearance_versions v ON v.id=c.version_id').fetchone()[0]
    # The image queued at backup time does not run on its own after the restore.
    assert statuses == {'completed', 'interrupted'}
    assert current == workspace['adapter']['id']
    adapter_file = tmp_path / 'restored' / 'lora' / 'adapters' / f"{workspace['adapter']['id']}.safetensors"
    assert adapter_file.read_bytes() == safetensors()


def test_datasets_are_left_out_by_default_and_reported_as_excluded(client, workspace, tmp_path):  # noqa: F811
    created = ok(client.post('/api/backups'))
    with zipfile.ZipFile(created['path']) as handle:
        assert not [name for name in handle.namelist() if name.startswith('lora/references/')]
    restored = backup.restore(Path(created['path']), tmp_path / 'restored' / 'companion.sqlite3')
    report = restored.restored_assets
    assert report['missing'] == [] and report['selected_appearance_intact']
    assert report['excluded'] == [{'kind': 'reference', 'id': workspace['reference']['id']}]


def test_a_damaged_asset_refuses_the_whole_restore(client, workspace, tmp_path):  # noqa: F811
    created = ok(client.post('/api/backups'))
    damaged = tmp_path / 'damaged.zip'
    with zipfile.ZipFile(created['path']) as source, zipfile.ZipFile(damaged, 'w') as target:
        for item in source.infolist():
            data = source.read(item)
            if item.filename.startswith('lora/adapters/'):
                data = data[:-1] + b'\x01'
            target.writestr(item, data)
    target = tmp_path / 'restored' / 'companion.sqlite3'
    with pytest.raises(DomainError) as error:
        backup.restore(damaged, target)
    assert 'damaged' in error.value.message
    assert not target.exists() and not (tmp_path / 'restored' / 'lora').exists()


def test_archives_cannot_write_outside_the_workspace(client, workspace, tmp_path):  # noqa: F811
    created = ok(client.post('/api/backups'))
    hostile = tmp_path / 'hostile.zip'
    with zipfile.ZipFile(created['path']) as source, zipfile.ZipFile(hostile, 'w') as target:
        manifest = json.loads(source.read('manifest.json'))
        manifest['files'].append({'path': 'images/../../escape.txt', 'sha256': '0' * 64, 'bytes': 1})
        for item in source.infolist():
            if item.filename != 'manifest.json':
                target.writestr(item, source.read(item))
        target.writestr('images/../../escape.txt', b'x')
        target.writestr('manifest.json', json.dumps(manifest))
    with pytest.raises(DomainError):
        backup.restore(hostile, tmp_path / 'restored' / 'companion.sqlite3')
    assert not (tmp_path / 'escape.txt').exists()


def test_older_archives_without_files_still_restore(client, workspace, tmp_path):  # noqa: F811
    database = client.app.state.database
    created = backup.archive(database.path, tmp_path / 'old.zip', database.now(), assets=False)
    restored = backup.restore(Path(created['path']), tmp_path / 'restored' / 'companion.sqlite3')
    kinds = {item['kind'] for item in restored.restored_assets['missing']}
    assert kinds == {'image', 'reference', 'adapter'}
    assert not restored.restored_assets['selected_appearance_intact']
