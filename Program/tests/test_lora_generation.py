# ruff: noqa: F811 - the image test fixtures are reused by name.
"""Generating candidate reference pictures in the Prepare step."""
import time

from companion.images.adapters.base import AdapterError
from tests.test_images import add_backend, ok, png
from tests.test_lora import adapters, app, client  # noqa: F401
from tests.test_lora_evaluation import appearance


def wait(client, generation_id, seconds=10):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        current = ok(client.get('/api/lora/generations'))['generations']
        found = next(item for item in current if item['id'] == generation_id)
        if found['status'] != 'running':
            return found
        time.sleep(0.02)
    raise AssertionError('generation kept running')


def plan(draft, shots=None, **extra):
    return {'base': draft['base'], 'seed': draft['seed'], 'shots': shots or draft['shots'][:3], **extra}


def test_the_draft_builds_a_varied_shot_list_from_the_appearance(client, companion):
    appearance(client, companion, 'Short silver hair, freckles, green coat.')
    draft = ok(client.get('/api/lora/generations/draft'))
    # Their looks sheet sits between the name and the description, leaving out the hair and freckles it already names.
    assert draft['base'].startswith('Mira, a') and draft['base'].endswith(', Short silver hair, freckles, green coat')
    assert ' skin, ' in draft['base'] and 'hair' not in draft['base'].split(', Short')[0]
    labels = [shot['label'] for shot in draft['shots']]
    assert len(labels) == 14 and sum(label.startswith('Full body') for label in labels) == 3
    assert {'Laughing', 'Profile', 'Light: night', 'Outfit: smart'} <= set(labels)
    assert 1 <= draft['seed'] < 2**31


def test_preview_shows_each_prompt_and_where_it_goes(client, companion):
    add_backend(client, kind='hosted', provider='openai', api_key='k', model='gpt-image-1')
    local = add_backend(client, kind='comfyui', base_url='http://127.0.0.1:8188')
    draft = ok(client.get('/api/lora/generations/draft'))
    shots = [draft['shots'][0], {'label': 'Beach', 'shot': 'topless at the beach', 'aspect': 'landscape'},
             {'label': 'Bad', 'shot': 'a 15 year old, nude', 'aspect': 'square'}]
    preview = ok(client.post('/api/lora/generations/preview', json=plan(draft, shots)))['shots']
    assert preview[0]['prompt'].startswith('Natural photograph. Mira') and preview[0]['tier'] == 'safe'
    assert preview[0]['backend']['label'] != local['label']
    assert preview[1]['tier'] == 'nsfw' and preview[1]['backend']['id'] == local['id']
    assert preview[2]['tier'] == 'prohibited' and preview[2]['backend'] is None and preview[2]['refusal']


def test_nsfw_without_a_local_backend_is_refused_and_recorded(client, companion, adapters):
    add_backend(client, kind='codex')
    draft = ok(client.get('/api/lora/generations/draft'))
    shots = [draft['shots'][0], {'label': 'Bath', 'shot': 'naked in the bath', 'aspect': 'square'}]
    created = ok(client.post('/api/lora/generations', json=plan(draft, shots)))
    done = wait(client, created['id'])
    refused = done['images'][1]
    assert refused['status'] == 'failed' and 'local backend' in refused['error'] and refused['backend_id'] is None
    assert done['images'][0]['status'] == 'completed' and done['images'][0]['backend_kind'] == 'codex'
    assert len(adapters['codex'].requests) == 1 and 'naked' not in adapters['codex'].requests[0].prompt


def test_marked_nsfw_stays_local(client, companion, adapters):
    add_backend(client, kind='hosted', provider='openai', api_key='k', model='gpt-image-1')
    draft = ok(client.get('/api/lora/generations/draft'))
    preview = ok(client.post('/api/lora/generations/preview', json=plan(draft, marked_nsfw=True)))['shots']
    assert all(shot['backend'] is None and shot['tier'] == 'nsfw' for shot in preview)


def test_pictures_share_one_seed_and_join_the_set_only_when_kept(client, companion, adapters):
    add_backend(client, kind='comfyui', base_url='http://127.0.0.1:8188')
    adapters['comfyui'].outcomes = [png(640, 800), AdapterError('failed', 'CUDA out of memory'), png(800, 640)]
    draft = ok(client.get('/api/lora/generations/draft'))
    created = ok(client.post('/api/lora/generations', json=plan(draft)))
    done = wait(client, created['id'])
    assert [image['status'] for image in done['images']] == ['completed', 'failed', 'completed']
    assert done['images'][1]['error'] == 'CUDA out of memory'
    assert {request.seed for request in adapters['comfyui'].requests} == {draft['seed']}
    assert all(request.lora is None for request in adapters['comfyui'].requests)
    assert ok(client.get('/api/lora/references'))['references'] == []

    first, _failed, third = done['images']
    assert client.get(f"/api/lora/generation-images/{first['id']}/file").content == png(640, 800)
    kept = ok(client.post(f"/api/lora/generation-images/{first['id']}/keep", params={'role': 'evaluation'}))
    assert kept['images'][0]['decision'] == 'kept' and kept['counts']['kept'] == 1
    reference = ok(client.get('/api/lora/references'))['references'][0]
    assert reference['rights'] == 'generated' and reference['role'] == 'evaluation'
    assert reference['source_note'].startswith('Generated by ') and 'Prompt: Natural photograph. Mira' in \
        reference['source_note']
    again = client.post(f"/api/lora/generation-images/{first['id']}/keep")
    assert again.status_code == 409

    discarded = ok(client.post(f"/api/lora/generation-images/{third['id']}/discard"))
    assert discarded['images'][2]['decision'] == 'discarded' and not discarded['images'][2]['has_image']
    assert len(ok(client.get('/api/lora/references'))['references']) == 1


def test_exact_copies_are_refused_when_kept(client, companion, adapters):
    add_backend(client, kind='comfyui', base_url='http://127.0.0.1:8188')
    adapters['comfyui'].outcomes = [png(640, 800)] * 3
    draft = ok(client.get('/api/lora/generations/draft'))
    done = wait(client, ok(client.post('/api/lora/generations', json=plan(draft)))['id'])
    first, second, _third = done['images']
    ok(client.post(f"/api/lora/generation-images/{first['id']}/keep"))
    copy = client.post(f"/api/lora/generation-images/{second['id']}/keep")
    assert copy.status_code == 409 and copy.json()['code'] == 'duplicate'
    assert next(image for image in wait(client, done['id'])['images'] if image['id'] == second['id'])['decision'] \
        is None


def test_webp_outputs_are_kept_from_the_interface_png_copy(client, companion, adapters):
    add_backend(client, kind='comfyui', base_url='http://127.0.0.1:8188')
    webp = b'RIFF\x00\x00\x00\x00WEBPVP8X' + b'\x00' * 8 + (99).to_bytes(3, 'little') + (79).to_bytes(3, 'little')
    adapters['comfyui'].outcomes = [webp]
    draft = ok(client.get('/api/lora/generations/draft'))
    done = wait(client, ok(client.post('/api/lora/generations', json=plan(draft, draft['shots'][:1])))['id'])
    image = done['images'][0]
    refused = client.post(f"/api/lora/generation-images/{image['id']}/keep")
    assert refused.status_code == 422 and refused.json()['code'] == 'convert'
    wrong = client.post(f"/api/lora/generation-images/{image['id']}/keep", content=png(10, 10),
                        headers={'content-type': 'application/octet-stream'})
    assert wrong.status_code == 422
    ok(client.post(f"/api/lora/generation-images/{image['id']}/keep", content=png(100, 80),
                   headers={'content-type': 'application/octet-stream'}))
    assert ok(client.get('/api/lora/references'))['references'][0]['media_type'] == 'image/png'


def test_generation_waits_while_a_chat_reply_is_written(client, companion, app, adapters):
    add_backend(client, kind='comfyui', base_url='http://127.0.0.1:8188')
    app.state.generations.pause = 0.02
    draft = ok(client.get('/api/lora/generations/draft'))
    with app.state.images.scheduler.foreground_work():
        created = ok(client.post('/api/lora/generations', json=plan(draft)))
        time.sleep(0.3)
        assert adapters['comfyui'].requests == []
    assert wait(client, created['id'])['counts']['completed'] == 3


def test_an_auth_error_stops_that_backend(client, companion, adapters):
    codex = add_backend(client, kind='codex')
    adapters['codex'].outcomes = [AdapterError('auth', 'Sign in to Codex again.')]
    draft = ok(client.get('/api/lora/generations/draft'))
    done = wait(client, ok(client.post('/api/lora/generations', json=plan(draft)))['id'])
    assert [image['status'] for image in done['images']] == ['failed'] * 3
    assert 'stopped' in done['images'][1]['error'] and len(adapters['codex'].requests) == 1
    backend = next(item for item in ok(client.get('/api/images/backends'))['backends'] if item['id'] == codex['id'])
    assert backend['blocked_reason'] == 'Sign in to Codex again.'


def test_stopping_cancels_what_is_left(client, companion, app, adapters):
    import asyncio
    add_backend(client, kind='comfyui', base_url='http://127.0.0.1:8188')
    adapters['comfyui'].gate = asyncio.Event()
    draft = ok(client.get('/api/lora/generations/draft'))
    created = ok(client.post('/api/lora/generations', json=plan(draft)))
    stopped = ok(client.post(f"/api/lora/generations/{created['id']}/cancel"))
    assert stopped['status'] == 'cancelled' and stopped['counts']['completed'] == 0
    assert client.post('/api/lora/generations', json=plan(draft)).status_code == 200


def test_the_image_runner_counts_a_picture_being_generated(client, companion, app):
    codex = add_backend(client, kind='codex')
    backend = {'id': codex['id'], 'kind': 'codex', 'concurrency': 1}
    assert not app.state.images.busy(backend)
    app.state.generations.current = {'id': codex['id'], 'kind': 'codex'}
    assert app.state.images.busy(backend)
