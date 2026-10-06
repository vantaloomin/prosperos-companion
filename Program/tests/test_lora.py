"""LoRA maker: references, adapters and appearance versions (PRD "Character LoRA maker")."""
import asyncio
import json
import struct

import httpx
import pytest
from fastapi.testclient import TestClient

from companion.identity import CLIENT_HEADER
from companion.images.adapters.comfyui import ComfyAdapter, with_lora
from companion.main import create_app
from companion.providers.vault import MemoryVault
from tests.test_images import ComfyStandIn, FakeAdapter, add_backend, make_post, ok, request_for


@pytest.fixture
def adapters():
    return {'comfyui': FakeAdapter(), 'codex': FakeAdapter(), 'hosted': FakeAdapter()}


@pytest.fixture
def app(tmp_path, clock, provider, adapters):
    return create_app(tmp_path / 'workspace' / 'companion.sqlite3', clock=clock, vault=MemoryVault(),
                      provider=provider, life_tasks=False, image_adapters=adapters, lora_maker=True)


@pytest.fixture
def client(app):
    with TestClient(app, headers={CLIENT_HEADER: 'workspace'}) as test_client:
        yield test_client


def jpeg(width=640, height=480, salt=b'') -> bytes:
    frame = b'\xff\xc0\x00\x11\x08' + struct.pack('>HH', height, width) + b'\x03' + b'\x00' * 9
    return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00' + b'\x00' * 9 + frame + salt + b'\xff\xd9'


def picture(index: int) -> bytes:
    return jpeg(640 + index, 480, salt=bytes([index]))


def safetensors(names=('lora_unet_a.lora_down.weight', 'lora_unet_a.lora_up.weight'), metadata=None,
                truncate=0) -> bytes:
    header, offset = {}, 0
    for name in names:
        header[name] = {'dtype': 'F16', 'shape': [2, 2], 'data_offsets': [offset, offset + 8]}
        offset += 8
    if metadata:
        header['__metadata__'] = metadata
    encoded = json.dumps(header).encode()
    data = struct.pack('<Q', len(encoded)) + encoded + b'\x00' * offset
    return data[:len(data) - truncate] if truncate else data


def add_picture(client, data, name='a.jpg', dhash=None):
    params = {'name': name, **({'dhash': dhash} if dhash else {})}
    return client.post('/api/lora/references', content=data, params=params,
                       headers={'content-type': 'application/octet-stream'})


def import_adapter(client, data, name='Mira look', base_model='krea/Krea-2-Raw', trigger='m1ra'):
    return client.post('/api/lora/adapters/import', content=data,
                       params={'name': name, 'base_model': base_model, 'trigger': trigger},
                       headers={'content-type': 'application/octet-stream'})


def test_references_keep_originals_and_refuse_exact_duplicates(client, companion, app):
    first = ok(add_picture(client, picture(1), 'one.jpg'))
    assert first['role'] == 'train' and first['rights'] == 'unknown' and first['width'] == 641
    again = add_picture(client, picture(1), 'copy.jpg')
    assert again.status_code == 409 and again.json()['code'] == 'duplicate'
    webp = add_picture(client, b'RIFF\x00\x00\x00\x00WEBPVP8 ' + b'\x00' * 30)
    assert webp.status_code == 422
    original = client.get(f"/api/lora/references/{first['id']}/file").content
    cropped = ok(client.post(f"/api/lora/references/{first['id']}/crop", content=jpeg(320, 320),
                             params={'x': 0.1, 'y': 0, 'width': 0.5, 'height': 0.6}))
    assert cropped['has_crop'] and cropped['crop']['width'] == 0.5
    assert client.get(f"/api/lora/references/{first['id']}/file").content == original == picture(1)
    assert client.get(f"/api/lora/references/{first['id']}/file", params={'cropped': True}).content == jpeg(320, 320)
    folder = app.state.database.path.parent / 'lora' / 'references'
    assert len(list(folder.iterdir())) == 2
    ok(client.delete(f"/api/lora/references/{first['id']}"))
    assert list(folder.iterdir()) == []


def test_review_blocks_unknown_rights_and_evaluation_copies(client, companion):
    ids = [ok(add_picture(client, picture(index), f'{index}.jpg', dhash=f'{index:016x}'))['id'] for index in range(5)]
    review = ok(client.get('/api/lora/references'))['review']
    assert not review['ready'] and any('came from' in line for line in review['blocking'])
    for reference_id in ids:
        ok(client.put(f'/api/lora/references/{reference_id}', json={'rights': 'own_work', 'source_note': 'My sketch'}))
    listing = ok(client.get('/api/lora/references'))
    # Hashes 0..4 are within a few bits of each other, so they are flagged as near duplicates.
    assert listing['review']['ready'] and listing['references'][1]['similar_to'] == ids[0]
    ok(client.put(f'/api/lora/references/{ids[1]}', json={'role': 'evaluation'}))
    review = ok(client.get('/api/lora/references'))['review']
    assert not review['ready'] and any('must not be a copy' in line for line in review['blocking'])
    refused = client.put(f'/api/lora/references/{ids[2]}', json={'role': 'excluded'})
    assert refused.status_code == 400
    excluded = ok(client.put(f'/api/lora/references/{ids[2]}', json={'role': 'excluded',
                                                                     'exclusion_reason': 'Wrong outfit'}))
    assert excluded['exclusion_reason'] == 'Wrong outfit'


def test_caption_suggestions_never_overwrite_the_users_words(client, companion):
    ok(client.post('/api/companion/versions', json={
        'definition': {**companion['version']['definition'], 'appearance': 'Short silver hair, green coat.'},
        'note': '', 'expected_version_id': companion['active_version_id']}))
    first = ok(add_picture(client, picture(1)))['id']
    second = ok(add_picture(client, picture(2)))['id']
    ok(client.put(f'/api/lora/references/{second}', json={'caption': 'm1ra laughing in the rain'}))
    listing = ok(client.post('/api/lora/references/captions'))
    captions = {item['id']: (item['caption'], item['caption_origin']) for item in listing['references']}
    assert captions[first] == ('[trigger], Short silver hair, green coat', 'suggested')
    assert captions[second] == ('m1ra laughing in the rain', 'edited')


def test_imported_adapters_are_checked_before_they_count(client, companion, app):
    bad = import_adapter(client, safetensors(truncate=4))
    assert bad.status_code == 422 and 'incomplete' in bad.json()['detail']
    assert list((app.state.database.path.parent / 'lora' / 'adapters').iterdir()) == []
    adapter = ok(import_adapter(client, safetensors(metadata={'ss_base_model': 'krea2'})))
    assert adapter['format'] == 'lora' and adapter['origin'] == 'imported' and 'Krea' in adapter['license_note']
    assert adapter['metadata'] == {'ss_base_model': 'krea2'}
    lokr = ok(import_adapter(client, safetensors(names=('a.lokr_w1', 'a.lokr_w2')), name='LoKr'))
    assert lokr['format'] == 'lokr'
    assert import_adapter(client, safetensors(metadata={'ss_base_model': 'krea2'})).status_code == 409


def test_adopting_a_lora_changes_only_later_images(client, companion, clock, adapters, app, tmp_path):
    add_backend(client, kind='comfyui', base_url='http://127.0.0.1:8188')
    before = make_post(client, clock, key='event-before')
    ok(client.post('/api/images/jobs', json={'post_id': before['id']}))
    loras = tmp_path / 'comfy-loras'
    loras.mkdir()
    ok(client.put('/api/lora/settings', json={'comfy_lora_dir': str(loras)}))
    adapter = ok(import_adapter(client, safetensors()))
    adopted = ok(client.post('/api/lora/appearance', json={'method': 'lora', 'adapter_id': adapter['id'],
                                                           'strength': 0.8}))
    name = adopted['install']['comfy_name']
    assert adopted['install']['installed'] and (loras / name).read_bytes() == safetensors()
    assert adopted['current']['number'] == 1 and adopted['current']['adapter']['id'] == adapter['id']
    after = make_post(client, clock, key='event-after')
    ok(client.post('/api/images/jobs', json={'post_id': after['id']}))
    asyncio.run(app.state.images.drain())
    old, new = adapters['comfyui'].requests
    assert old.lora is None and new.lora['comfy_name'] == name and new.lora['strength'] == 0.8
    old_job = ok(client.get('/api/images/jobs', params={'post_id': before['id']}))['jobs'][0]
    new_job = ok(client.get('/api/images/jobs', params={'post_id': after['id']}))['jobs'][0]
    assert old_job['appearance_version'] == 0 and old_job['identity_method'] == 'text description'
    assert new_job['appearance_version'] == 1 and new_job['identity_method'].startswith('LoRA Mira look')
    assert client.delete(f"/api/lora/adapters/{adapter['id']}").status_code == 409
    ok(client.post('/api/lora/appearance', json={'method': 'text', 'note': 'Back to the description'}))
    removed = ok(client.delete(f"/api/lora/adapters/{adapter['id']}"))['adapters'][0]
    assert not removed['available']
    history = ok(client.get('/api/lora/appearance'))
    assert [version['number'] for version in history['versions']] == [2, 1]
    assert history['versions'][1]['adapter']['name'] == 'Mira look'


def test_hosted_backends_record_that_they_cannot_apply_the_lora(client, companion, clock, adapters, app):
    add_backend(client, kind='hosted', provider='openai', model='gpt-image-1', api_key='k', accept_disclosure=True)
    adapter = ok(import_adapter(client, safetensors()))
    ok(client.post('/api/lora/appearance', json={'method': 'lora', 'adapter_id': adapter['id']}))
    post = make_post(client, clock)
    ok(client.post('/api/images/jobs', json={'post_id': post['id']}))
    asyncio.run(app.state.images.drain())
    assert adapters['hosted'].requests[0].lora is None
    job = ok(client.get('/api/images/jobs', params={'post_id': post['id']}))['jobs'][0]
    assert job['identity_method'] == 'text description only; this backend cannot apply the adopted LoRA'


def test_comfyui_inserts_the_lora_after_the_model_loader():
    graph = {'1': {'class_type': 'UNETLoader', 'inputs': {'unet_name': 'krea2.safetensors'}},
             '2': {'class_type': 'KSampler', 'inputs': {'model': ['1', 0], 'seed': 1}},
             '3': {'class_type': 'ModelSamplingAuraFlow', 'inputs': {'model': ['1', 0]}}}
    wired = with_lora(graph, {'comfy_name': 'prospero-x.safetensors', 'strength': 0.7})
    assert wired['2']['inputs']['model'] == ['prospero-lora', 0] and wired['3']['inputs']['model'] == ['prospero-lora', 0]
    assert wired['prospero-lora']['inputs'] == {'model': ['1', 0], 'lora_name': 'prospero-x.safetensors',
                                                'strength_model': 0.7}
    server = ComfyStandIn()
    adapter = ComfyAdapter(httpx.MockTransport(server), poll_seconds=0)
    lora = {'comfy_name': 'prospero-x.safetensors', 'strength': 1.0, 'trigger': 'm1ra'}
    result = asyncio.run(adapter.generate(request_for('comfyui', {'base_url': 'http://127.0.0.1:8188'}, lora=lora)))
    sent = server.prompts[0]
    assert sent['4']['inputs']['text'] == 'm1ra, A café' and 'prospero-lora' in sent
    assert result.workflow.endswith('+ LoRA prospero-x.safetensors')
    report = asyncio.run(adapter.check({}, {'base_url': 'http://127.0.0.1:8188', 'lora_name': 'prospero-x.safetensors'}))
    assert any('LoraLoaderModelOnly' in line for line in report.details)
