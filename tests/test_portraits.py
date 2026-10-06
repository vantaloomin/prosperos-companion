# ruff: noqa: F811 - the image test fixtures are reused by name.
"""Profile pictures made while setting up a companion: three pictures, each following the one before."""
import asyncio
import base64
import json
import time

import httpx
import pytest

from companion.images.adapters.base import AdapterError
from companion.images.adapters.codex import CodexAdapter
from companion.images.adapters.comfyui import ComfyAdapter
from companion.images.adapters.hosted import HostedAdapter
from companion.lora.portraits import expression_for, outfits_for
from tests.test_images import ComfyStandIn, add_backend, fake_codex, hosted_server, ok, png, request_for  # noqa: F401
from tests.test_lora import adapters, app, client  # noqa: F401

REFERENCE_WORKFLOW = json.dumps({
    '1': {'class_type': 'LoadImage', 'inputs': {'image': '{{reference_image}}'}},
    '2': {'class_type': 'CLIPTextEncode', 'inputs': {'text': '{{prompt}}'}},
    '9': {'class_type': 'SaveImage', 'inputs': {'images': ['1', 0]}}})


def plan(draft, **extra):
    return {'base': draft['base'], 'seed': draft['seed'], 'shots': draft['shots'], **extra}


def portraits(client):
    return ok(client.get('/api/lora/portraits'))['portraits']


def wait_portraits(client, seconds=10):

    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        current = portraits(client)
        if current['status'] != 'running':
            return current
        time.sleep(0.02)
    raise AssertionError('portraits kept running')


def test_the_draft_picks_an_expression_and_two_everyday_outfits(client, companion):
    draft = ok(client.get('/api/lora/portraits/draft'))
    profile, turned, close = draft['shots']
    assert [shot['label'] for shot in draft['shots']] == ['Profile picture', 'Three-quarter view', 'Face close-up']
    assert 'waist-up' in profile['shot'] and 'facing the camera' in profile['shot']
    assert 'three-quarter view' in turned['shot'] and 'close-up of the face' in close['shot']
    first, second = outfits_for(companion['id'])
    assert first != second and first in profile['shot'] and second in turned['shot']
    assert draft['any_backend'] is False and draft['reference_backend'] is None
    assert expression_for({'personality': 'Dry, sarcastic and loyal.'}) == 'a wry half-smile'
    assert expression_for({'personality': 'Shy at first, then very warm.'}).startswith('a small, slightly shy')
    assert expression_for({}) == 'a relaxed, natural smile'


def test_each_picture_follows_the_one_before_on_one_backend(client, companion, adapters):
    add_backend(client, kind='hosted', provider='google', api_key='k', model='imagen-4')
    codex = add_backend(client, kind='codex')
    adapters['codex'].outcomes = [png(1024, 1536), png(1024, 1535), png(1024, 1024)]
    draft = ok(client.get('/api/lora/portraits/draft'))
    assert draft['reference_backend']['id'] == codex['id']
    preview = ok(client.post('/api/lora/portraits/preview', json=plan(draft)))['shots']
    assert [shot['backend']['id'] for shot in preview] == [codex['id']] * 3
    assert [shot['follows'] for shot in preview] == [None, 0, 1]
    assert 'reference picture' not in preview[0]['prompt'] and 'reference picture' in preview[1]['prompt']

    ok(client.post('/api/lora/portraits', json=plan(draft)))
    done = wait_portraits(client)
    assert [image['status'] for image in done['images']] == ['completed'] * 3
    sent = adapters['codex'].requests
    assert sent[0].reference is None and sent[1].reference == png(1024, 1536) and sent[2].reference == png(1024, 1535)
    assert adapters['hosted'].requests == []
    # Portrait sets stay out of the LoRA maker's own list of generated sets.
    assert ok(client.get('/api/lora/generations'))['generations'] == []


def test_without_a_reference_backend_nothing_is_sent_unless_asked(client, companion, adapters):
    add_backend(client, kind='hosted', provider='google', api_key='k', model='imagen-4')
    draft = ok(client.get('/api/lora/portraits/draft'))
    assert draft['any_backend'] is True and draft['reference_backend'] is None
    refused = client.post('/api/lora/portraits', json=plan(draft))
    assert refused.status_code == 409 and refused.json()['code'] == 'no_reference_backend'
    assert adapters['hosted'].requests == []

    ok(client.post('/api/lora/portraits', json=plan(draft, without_reference=True)))
    done = wait_portraits(client)
    assert [image['status'] for image in done['images']] == ['completed'] * 3
    assert all(request.reference is None for request in adapters['hosted'].requests)
    assert all('reference picture' not in request.prompt for request in adapters['hosted'].requests)


def test_a_failed_picture_stops_the_ones_that_follow_and_can_be_made_again(client, companion, adapters):
    add_backend(client, kind='hosted', provider='openrouter', api_key='k', model='google/gemini-image')
    adapters['hosted'].outcomes = [png(1024, 1536), AdapterError('failed', 'Provider hiccup')]
    draft = ok(client.get('/api/lora/portraits/draft'))
    ok(client.post('/api/lora/portraits', json=plan(draft)))
    done = wait_portraits(client)
    assert [image['status'] for image in done['images']] == ['completed', 'failed', 'failed']
    assert 'Picture 2 did not finish' in done['images'][2]['error']
    assert len(adapters['hosted'].requests) == 2

    adapters['hosted'].outcomes = [png(1000, 1500), png(900, 900)]
    ok(client.post(f"/api/lora/portraits/{done['id']}/redo", params={'position': 1}))
    again = wait_portraits(client)
    assert [image['status'] for image in again['images']] == ['completed'] * 3
    assert again['images'][1]['seed'] != draft['seed'] and again['images'][0]['seed'] == draft['seed']
    assert adapters['hosted'].requests[2].reference == png(1024, 1536)
    assert adapters['hosted'].requests[3].reference == png(1000, 1500)


def test_nsfw_and_prohibited_pictures_keep_the_usual_routing(client, companion, adapters):
    add_backend(client, kind='codex')
    draft = ok(client.get('/api/lora/portraits/draft'))
    shots = [draft['shots'][0], {**draft['shots'][1], 'shot': 'topless at the beach'}, draft['shots'][2]]
    ok(client.post('/api/lora/portraits', json=plan(draft, shots=shots)))
    done = wait_portraits(client)
    assert [image['status'] for image in done['images']] == ['completed', 'failed', 'failed']
    assert done['images'][1]['backend_id'] is None and 'topless' not in ''.join(
        request.prompt for request in adapters['codex'].requests)
    bad = [{**draft['shots'][0], 'shot': 'a 15 year old, nude'}]
    refused = client.post('/api/lora/portraits', json=plan(draft, shots=bad))
    assert refused.status_code == 409 and refused.json()['code'] == 'refused'


def test_kept_profile_picture_becomes_the_companions_picture(client, companion, adapters):
    add_backend(client, kind='codex')
    adapters['codex'].outcomes = [png(1024, 1536), png(1024, 1535), png(1024, 1024)]
    draft = ok(client.get('/api/lora/portraits/draft'))
    ok(client.post('/api/lora/portraits', json=plan(draft)))
    done = wait_portraits(client)
    kept = [ok(client.post(f"/api/lora/generation-images/{image['id']}/keep")) for image in done['images']]
    reference_ids = [item['images'][index]['reference_id'] for index, item in enumerate(kept)]
    assert len(ok(client.get('/api/lora/references'))['references']) == 3
    ok(client.put('/api/lora/portrait', json={'reference_id': reference_ids[0]}))
    assert ok(client.get('/api/companion'))['companion']['portrait_reference_id'] == reference_ids[0]
    redo = client.post(f"/api/lora/portraits/{done['id']}/redo", params={'position': 2})
    assert redo.status_code == 409
    ok(client.delete(f'/api/lora/references/{reference_ids[0]}'))
    assert ok(client.get('/api/companion'))['companion']['portrait_reference_id'] is None
    missing = client.put('/api/lora/portrait', json={'reference_id': 'nope'})
    assert missing.status_code == 404


def test_reference_capability_per_backend(client, companion):
    assert add_backend(client, kind='codex')['takes_reference'] is True
    assert add_backend(client, kind='hosted', provider='openrouter', api_key='k', model='m')['takes_reference'] is True
    assert add_backend(client, kind='hosted', provider='openai', api_key='k', model='gpt-image-1')['takes_reference']
    assert add_backend(client, kind='hosted', provider='google', api_key='k', model='m')['takes_reference'] is False
    comfy = add_backend(client, kind='comfyui', base_url='http://127.0.0.1:8188')
    assert comfy['takes_reference'] is False
    bad = client.put(f"/api/images/backends/{comfy['id']}", json={'reference_workflow': json.dumps(
        {'1': {'class_type': 'CLIPTextEncode', 'inputs': {'text': '{{prompt}}'}}})})
    assert bad.status_code == 422 and 'reference_image' in bad.json()['detail']
    updated = ok(client.put(f"/api/images/backends/{comfy['id']}", json={'reference_workflow': REFERENCE_WORKFLOW}))
    assert updated['takes_reference'] is True and updated['reference_workflow'] is True


# Adapters ------------------------------------------------------------------------------------

def test_hosted_chat_style_sends_the_reference_in_the_message():
    seen = []
    url = 'data:image/png;base64,' + base64.b64encode(png()).decode()
    body = {'choices': [{'message': {'images': [{'image_url': {'url': url}}]}}]}
    adapter = HostedAdapter(hosted_server([httpx.Response(200, json=body)], seen))
    request = request_for('hosted', {'base_url': 'https://openrouter.ai/api/v1', 'model': 'm', 'api_style': 'chat'},
                          provider='openrouter', key='k', reference=png(10, 12))
    asyncio.run(adapter.generate(request))
    content = json.loads(seen[0].content)['messages'][0]['content']
    assert content[0] == {'type': 'text', 'text': 'A café\nAvoid: text'}
    assert content[1]['image_url']['url'] == 'data:image/png;base64,' + base64.b64encode(png(10, 12)).decode()


def test_openai_uses_image_edits_for_a_reference_and_google_refuses_one():
    seen = []
    body = {'data': [{'b64_json': base64.b64encode(png()).decode()}]}
    adapter = HostedAdapter(hosted_server([httpx.Response(200, json=body)], seen))
    request = request_for('hosted', {'base_url': 'https://api.openai.com/v1', 'model': 'gpt-image-1',
                                     'api_style': 'images'}, provider='openai', key='k', reference=png(10, 12))
    asyncio.run(adapter.generate(request))
    assert seen[0].url.path.endswith('/images/edits')
    assert seen[0].headers['content-type'].startswith('multipart/form-data')
    assert b'name="image"; filename="reference.png"' in seen[0].content and png(10, 12) in seen[0].content
    google = request_for('hosted', {'base_url': 'https://generativelanguage.googleapis.com/v1beta/openai',
                                    'model': 'imagen-4', 'api_style': 'images'}, provider='google', key='k',
                         reference=png())
    with pytest.raises(AdapterError) as error:
        asyncio.run(HostedAdapter(hosted_server([], [])).generate(google))
    assert error.value.code == 'incompatible'


def test_codex_attaches_the_reference_picture(fake_codex):
    request = request_for('codex', {'cli_path': str(fake_codex['codex'])}, width=1024, height=1536,
                          raw_dir=fake_codex['raw'], reference=png(10, 12))
    asyncio.run(CodexAdapter().generate(request))
    args = fake_codex['log'].read_text(encoding='utf-8').split('\n', 1)[0]
    assert args.startswith('exec --image ') and 'reference.png --json ' in args and args.endswith(' -')


class ComfyWithUpload(ComfyStandIn):
    def __init__(self):
        super().__init__()
        self.uploads = []

    def __call__(self, request: httpx.Request):
        if request.url.path == '/upload/image':
            self.uploads.append(request.content)
            return httpx.Response(200, json={'name': 'prospero-job1.png', 'subfolder': '', 'type': 'input'})
        return super().__call__(request)


def test_comfyui_uploads_the_reference_into_its_own_workflow():
    server = ComfyWithUpload()
    adapter = ComfyAdapter(httpx.MockTransport(server), poll_seconds=0)
    config = {'base_url': 'http://127.0.0.1:8188', 'reference_workflow': REFERENCE_WORKFLOW}
    result = asyncio.run(adapter.generate(request_for('comfyui', config, reference=png(10, 12))))
    graph = server.prompts[0]
    assert graph['1']['inputs']['image'] == 'prospero-job1.png' and graph['2']['inputs']['text'] == 'A café'
    assert png(10, 12) in server.uploads[0] and result.workflow == 'custom reference'
    with pytest.raises(AdapterError) as error:
        asyncio.run(adapter.generate(request_for('comfyui', {'base_url': 'http://127.0.0.1:8188'}, reference=png())))
    assert error.value.code == 'incompatible'
