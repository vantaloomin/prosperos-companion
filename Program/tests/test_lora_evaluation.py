# ruff: noqa: F811 - the image test fixtures are reused by name.
"""LoRA evaluation sets, export and backup of adapters."""
import io
import json
import time
import zipfile
from pathlib import Path

from companion import backup
from companion.images.adapters.base import AdapterError
from tests.test_images import add_backend, ok
from tests.test_lora import adapters, add_picture, app, client, import_adapter, picture, safetensors  # noqa: F401


def wait(client, evaluation_id, seconds=10):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        current = ok(client.get(f'/api/lora/evaluations/{evaluation_id}'))
        if current['status'] != 'running':
            return current
        time.sleep(0.02)
    raise AssertionError('evaluation kept running')


def appearance(client, companion, text):
    ok(client.post('/api/companion/versions', json={
        'definition': {**companion['version']['definition'], 'appearance': text}, 'note': '',
        'expected_version_id': companion['active_version_id']}))


def test_evaluation_needs_a_local_comfyui(client, companion):
    adapter = ok(import_adapter(client, safetensors()))
    refused = client.post('/api/lora/evaluations', json={'adapter_id': adapter['id']})
    assert refused.status_code == 409 and 'ComfyUI server on this computer' in refused.json()['detail']


def test_the_fixed_set_renders_with_and_without_the_adapter_and_keeps_failures(client, companion, adapters):
    appearance(client, companion, 'Short silver hair, freckles, green coat.')
    add_backend(client, kind='comfyui', base_url='http://127.0.0.1:8188')
    held = ok(add_picture(client, picture(1)))
    ok(client.put(f"/api/lora/references/{held['id']}", json={'role': 'evaluation'}))
    adapter = ok(import_adapter(client, safetensors()))
    adapters['comfyui'].outcomes = [AdapterError('failed', 'CUDA out of memory')]
    created = ok(client.post('/api/lora/evaluations', json={'adapter_id': adapter['id'], 'strength': 0.9}))
    assert created['held_out'] == [held['id']] and len(created['images']) == 16
    done = wait(client, created['id'])
    assert done['status'] == 'completed' and done['counts']['completed'] == 15 and done['counts']['failed'] == 1
    first = done['images'][0]
    assert first['status'] == 'failed' and first['error'] == 'CUDA out of memory' and first['label'] == 'Portrait'
    requests = adapters['comfyui'].requests
    with_adapter = [request for request in requests if request.lora]
    assert len(with_adapter) == 8 and with_adapter[0].lora['strength'] == 0.9
    assert with_adapter[0].lora['comfy_name'].startswith('prospero-mira-look-')
    assert 'm1ra, Mira' in with_adapter[0].prompt and 'silver hair' not in with_adapter[0].prompt
    text_only = [request for request in requests if not request.lora]
    assert len(text_only) == 8 and 'Short silver hair, freckles, green coat' in text_only[0].prompt
    assert sorted({request.seed for request in requests}) == list(range(1101, 1109))
    traits = next(image for image in done['images'] if image['prompt_key'] == 'traits' and image['variant'] == 'lora')
    assert 'close-up showing Short silver hair, freckles, green coat' in traits['prompt']
    finished = next(image for image in done['images'] if image['status'] == 'completed')
    assert client.get(f"/api/lora/evaluation-images/{finished['id']}/file").content.startswith(b'\x89PNG')
    rated = ok(client.put(f"/api/lora/evaluation-images/{finished['id']}/rating", json={'rating': 'weak'}))
    assert next(image for image in rated['images'] if image['id'] == finished['id'])['rating'] == 'weak'
    assert client.put(f"/api/lora/evaluation-images/{first['id']}/rating", json={'rating': 'good'}).status_code == 409
    assert len(ok(client.get('/api/lora/evaluations', params={'adapter_id': adapter['id']}))['evaluations']) == 1


def test_prohibited_requests_are_refused_and_recorded(client, companion, adapters):
    appearance(client, companion, 'A nude schoolgirl')
    add_backend(client, kind='comfyui', base_url='http://127.0.0.1:8188')
    adapter = ok(import_adapter(client, safetensors()))
    created = ok(client.post('/api/lora/evaluations', json={'adapter_id': adapter['id'], 'include_baseline': False}))
    done = wait(client, created['id'])
    assert len(done['images']) == 8 and all(image['status'] == 'failed' for image in done['images'])
    assert done['images'][0]['error'].startswith('Refused: sexual or nude content with a minor')
    assert adapters['comfyui'].requests == []


def test_export_carries_metadata_and_the_license_notice_but_no_pictures(client, companion):
    ok(add_picture(client, picture(1)))
    adapter = ok(import_adapter(client, safetensors(), name='Mira look'))
    response = client.get(f"/api/lora/adapters/{adapter['id']}/export")
    assert response.status_code == 200
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    assert sorted(archive.namelist()) == ['Krea-mira-look.safetensors', 'LICENSE-NOTICE.txt', 'adapter.json']
    assert archive.read('Krea-mira-look.safetensors') == safetensors()
    metadata = json.loads(archive.read('adapter.json'))
    assert metadata['base_model'] == 'krea/Krea-2-Raw' and metadata['trigger'] == 'm1ra'
    assert 'Not verified on hardware' in metadata['compatibility']
    assert 'Krea 2 Community License' in archive.read('LICENSE-NOTICE.txt').decode()


def test_backups_keep_adapters_and_restore_them(client, companion, app, tmp_path, clock):
    ok(add_picture(client, picture(1)))
    adapter = ok(import_adapter(client, safetensors()))
    removed = ok(import_adapter(client, safetensors(metadata={'x': '1'}), name='Old'))
    ok(client.delete(f"/api/lora/adapters/{removed['id']}"))
    created = backup.create(app.state.database, tmp_path / 'archives')
    assert [item['path'] for item in created['files']] == [f"lora/adapters/{adapter['file']}"]
    with zipfile.ZipFile(created['path']) as archive:
        assert not any(name.startswith('lora/references') for name in archive.namelist())
    target = tmp_path / 'restored' / 'companion.sqlite3'
    backup.restore(Path(created['path']), target, clock)
    assert (target.parent / 'lora' / 'adapters' / adapter['file']).read_bytes() == safetensors()


def test_evaluation_waits_while_a_chat_reply_is_written(client, companion, app, adapters):
    add_backend(client, kind='comfyui', base_url='http://127.0.0.1:8188')
    adapter = ok(import_adapter(client, safetensors()))
    scheduler = app.state.images.scheduler
    with scheduler.foreground_work():
        created = ok(client.post('/api/lora/evaluations', json={'adapter_id': adapter['id'], 'include_baseline': False}))
        time.sleep(0.3)
        assert adapters['comfyui'].requests == []
    done = wait(client, created['id'])
    assert done['status'] == 'completed' and len(adapters['comfyui'].requests) == 8
