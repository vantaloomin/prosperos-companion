"""Image jobs, content routing and backend adapters (PRD F3–F9)."""
import asyncio
import base64
import json
import os
import struct
import sys
from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from companion.identity import CLIENT_HEADER
from companion.images import content
from companion.images.adapters.base import AdapterError, ImageRequest, ImageResult
from companion.images.adapters.codex import CodexAdapter
from companion.images.adapters.comfyui import ComfyAdapter
from companion.images.adapters.hosted import HostedAdapter
from companion.main import create_app
from companion.providers.vault import MemoryVault


def png(width=64, height=48) -> bytes:
    return b'\x89PNG\r\n\x1a\n' + b'\x00\x00\x00\rIHDR' + struct.pack('>II', width, height) + b'\x08\x02\x00\x00\x00'


class FakeAdapter:
    """Records requests; `outcomes` scripts results (bytes) or AdapterErrors in order."""

    def __init__(self):
        self.requests = []
        self.outcomes = []
        self.gate = None

    async def generate(self, request):
        self.requests.append(request)
        if self.gate:
            await self.gate.wait()
        outcome = self.outcomes.pop(0) if self.outcomes else png()
        if isinstance(outcome, Exception):
            raise outcome
        return ImageResult(outcome, model='fake-model', seed=request.seed)

    async def check(self, backend, config, key=None):
        from companion.images.adapters.base import Check
        return Check(True, 'fine')


@pytest.fixture
def adapters():
    return {'comfyui': FakeAdapter(), 'codex': FakeAdapter(), 'hosted': FakeAdapter()}


@pytest.fixture
def app(tmp_path, clock, provider, adapters):
    return create_app(tmp_path / 'workspace' / 'companion.sqlite3', clock=clock, vault=MemoryVault(),
                      provider=provider, life_tasks=False, image_adapters=adapters)


@pytest.fixture
def client(app):
    with TestClient(app, headers={CLIENT_HEADER: 'workspace'}) as test_client:
        yield test_client


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def make_post(client, clock, summary='Mira walked along the harbour at dusk.', key='event-0001'):
    clock.advance(timedelta(hours=2))
    start = clock.now() - timedelta(hours=1)
    event = ok(client.post('/api/events', json={
        'idempotency_key': key, 'kind': 'ordinary', 'summary': summary,
        'details': {'post': 'The water was so calm.', 'mood': 'content'},
        'starts_at': start.isoformat(), 'ends_at': (start + timedelta(minutes=30)).isoformat()}))
    ok(client.post(f"/api/events/{event['id']}/commit"))
    return ok(client.post('/api/feed/posts', json={'event_id': event['id']}))


def add_backend(client, **body):
    body.setdefault('accept_disclosure', True)
    return ok(client.post('/api/images/backends', json=body))


def local_comfy(client):
    return add_backend(client, kind='comfyui', base_url='http://127.0.0.1:8188')


def drain(client):
    asyncio.run(client.app.state.images.drain())


def generate(client, post, **body):
    return ok(client.post('/api/images/jobs', json={'post_id': post['id'], **body}))


def post_image(client, post):
    return ok(client.get(f"/api/feed/{post['id']}"))['image']


# Classification (F6) -------------------------------------------------------------------------

LABELLED = [
    ('Mira reads a novel at a quiet café by the window.', 'safe'),
    ('Mira jogs along the river at sunrise in running gear.', 'safe'),
    ('Mira laughs with friends at a crowded jazz bar.', 'safe'),
    ('Mira graduates magna cum laude in a cap and gown.', 'safe'),
    ('Mira swims at the beach in a swimsuit on a sunny day.', 'safe'),
    ('Mira posing nude on a bed.', 'nsfw'),
    ('An erotic scene in the bedroom.', 'nsfw'),
    ('Mira in lingerie by the mirror.', 'nsfw'),
    ('A seductive look over the shoulder.', 'nsfw'),
    ('A battlefield of dismembered bodies and gore.', 'nsfw'),
    ('Mira, t-o-p-l-e-s-s, at the lake.', 'nsfw'),
    ('Mira, n a k e d, in the rain.', 'nsfw'),
    ('A nude 16-year-old at the beach.', 'prohibited'),
    ('Sexual pose with a schoolgirl outfit on a teen.', 'prohibited'),
    ('Nude photo of a famous actress.', 'prohibited'),
    ('A rape scene.', 'prohibited'),
    ('Non-consensual encounter in an alley.', 'prohibited'),
]


@pytest.mark.parametrize(('prompt', 'expected'), LABELLED)
def test_labelled_prompts_classify_as_expected(prompt, expected):
    assert content.classify({'prompt': prompt}).tier == expected


def test_known_false_positives_are_recorded_not_tuned_away():
    """Fail-closed lists catch some harmless wording; these stay off hosted backends (F6)."""
    for prompt in ('Mira ordered chicken breasts at the diner.', 'Mira donated blood at the clinic.'):
        assert content.classify({'prompt': prompt}).tier == 'nsfw'


def test_a_safe_prompt_from_a_sexual_event_is_not_safe():
    request = {'prompt': 'Mira smiles in soft morning light.',
               'events': [{'summary': 'Mira and Dan had sex after the party.'}]}
    assert content.classify(request).tier == 'nsfw'


def test_classifier_errors_and_manual_marks_route_as_nsfw(monkeypatch):
    assert content.classify({'prompt': 'A park bench.', 'marked_nsfw': True}).tier == 'nsfw'

    def broken(_text):
        raise RuntimeError('boom')
    monkeypatch.setattr(content, 'matches', broken)
    result = content.classify({'prompt': 'A park bench.'})
    assert result.tier == 'nsfw' and 'classifier error' in result.reasons[0]


def test_composed_life_events_are_mostly_safe():
    """Every catalog caption and mood is classified, so a built-in event never needs a local
    backend because of the app's own wording."""
    from companion.life import composer
    activities = [item for group in composer.CATALOG.values() for item in group]
    texts = [text for item in activities for text in (*item.summaries, *item.captions, *item.moods)]
    texts += [text for thread in composer.THREADS for text in (thread.opening, *thread.endings)]
    flagged = [text for text in texts if content.classify({'prompt': text}).tier != 'safe']
    assert flagged == []


# Routing and jobs ----------------------------------------------------------------------------

def test_no_backend_refuses_with_an_explanation(client, companion, clock):
    post = make_post(client, clock)
    job = generate(client, post)
    assert job['status'] == 'failed' and job['error_code'] == 'no_backend'
    image = post_image(client, post)
    assert image['status'] == 'failed' and 'Settings' in image['error']


def test_nsfw_goes_only_to_a_local_backend(client, companion, clock, adapters):
    codex = add_backend(client, kind='codex')
    google = add_backend(client, kind='hosted', provider='google', model='imagen-4', api_key='k')
    post = make_post(client, clock, summary='Mira posed nude for a life drawing class.')
    refused = generate(client, post)
    assert refused['status'] == 'failed' and refused['error_code'] == 'no_local_backend'
    assert 'local' in refused['error'] and refused['classification'] == 'nsfw'
    pinned = ok(client.post('/api/images/jobs', json={'post_id': post['id'], 'backend_id': codex['id']}))
    assert pinned['error_code'] == 'not_eligible'
    comfy = local_comfy(client)
    job = generate(client, post)
    assert job['status'] == 'queued' and job['backend_id'] == comfy['id']
    drain(client)
    assert adapters['codex'].requests == [] and adapters['hosted'].requests == []
    assert len(adapters['comfyui'].requests) == 1
    assert google['accepts_nsfw'] is False


def test_a_remote_comfyui_counts_as_hosted_unless_marked_controlled(client, companion, clock):
    remote = add_backend(client, kind='comfyui', base_url='https://gpu.example.com')
    assert remote['local'] is False and remote['accepts_nsfw'] is False
    marked = ok(client.put(f"/api/images/backends/{remote['id']}", json={'controlled_machine': True,
                                                                          'accept_disclosure': True}))
    assert marked['local'] is True


def test_prohibited_is_refused_even_locally(client, companion, clock, adapters):
    local_comfy(client)
    post = make_post(client, clock, summary='A nude 15-year-old at the lake.')
    job = generate(client, post)
    assert job['status'] == 'failed' and job['error_code'] == 'prohibited'
    drain(client)
    assert adapters['comfyui'].requests == []


def test_safe_follows_the_users_order_and_records_provenance(client, companion, clock, adapters):
    local_comfy(client)
    hosted = add_backend(client, kind='hosted', provider='openrouter', model='google/gemini-image', api_key='k')
    ok(client.post(f"/api/images/backends/{hosted['id']}/move", json={'position': 0}))
    post = make_post(client, clock)
    job = generate(client, post)
    drain(client)
    done = ok(client.get(f"/api/images/jobs/{job['id']}"))
    assert done['status'] == 'completed' and done['backend_kind'] == 'hosted' and done['provider'] == 'openrouter'
    assert done['classification'] == 'safe' and 'any enabled backend' in done['routing_reason']
    assert done['identity_method'] == 'text description only' and done['current']
    assert 'harbour' in done['prompt'] and done['width'] == 64
    assert adapters['hosted'].requests[0].key == 'k'
    image = post_image(client, post)
    assert image['status'] == 'completed' and image['ref'] == job['id']
    file = client.get(f"/api/images/jobs/{job['id']}/file")
    assert file.status_code == 200 and file.headers['content-type'] == 'image/png'


def test_hosted_backends_need_the_disclosure_accepted(client, companion):
    response = client.post('/api/images/backends', json={'kind': 'hosted', 'provider': 'openai', 'model': 'gpt-image-1'})
    assert response.status_code == 409 and response.json()['code'] == 'disclosure_required'
    off = ok(client.post('/api/images/backends', json={'kind': 'hosted', 'provider': 'openai', 'model': 'gpt-image-1',
                                                       'enabled': False}))
    assert 'retention' in off['disclosure'] and not off['has_key']
    assert local_comfy(client)['disclosure'] is None


def test_a_late_result_never_replaces_a_newer_selection(client, companion, clock, adapters):
    local_comfy(client)
    post = make_post(client, clock)
    first = generate(client, post)
    drain(client)
    adapters['comfyui'].gate = asyncio.Event()

    async def scenario():
        second = generate(client, post)
        client.app.state.images.dispatch()
        await asyncio.sleep(0)
        ok(client.post(f"/api/images/jobs/{first['id']}/select"))
        adapters['comfyui'].gate.set()
        await client.app.state.images.drain()
        return second
    second = asyncio.run(scenario())
    image = post_image(client, post)
    assert image['ref'] == first['id'] and image['job_id'] == first['id']
    late = ok(client.get(f"/api/images/jobs/{second['id']}"))
    assert late['status'] == 'completed' and not late['current']
    ok(client.post(f"/api/images/jobs/{second['id']}/select"))
    assert post_image(client, post)['ref'] == second['id']
    assert [job['id'] for job in ok(client.get('/api/images/jobs', params={'post_id': post['id']}))['jobs']] == \
        [second['id'], first['id']]


def test_retry_keeps_original_inputs_unless_current_settings(client, companion, clock, adapters):
    local_comfy(client)
    post = make_post(client, clock)
    adapters['comfyui'].outcomes = [AdapterError('failed', 'GPU out of memory')]
    job = generate(client, post)
    drain(client)
    failed = ok(client.get(f"/api/images/jobs/{job['id']}"))
    assert failed['status'] == 'failed' and failed['error'] == 'GPU out of memory'
    ok(client.put('/api/images/settings', json={'style': 'Watercolour sketch'}))
    again = ok(client.post(f"/api/images/jobs/{job['id']}/retry"))
    assert again['prompt'] == failed['prompt'] and again['retry_of'] == job['id']
    current = ok(client.post(f"/api/images/jobs/{job['id']}/retry", json={'current_settings': True}))
    assert current['prompt'].startswith('Watercolour sketch')
    drain(client)
    assert adapters['comfyui'].requests[1].seed == adapters['comfyui'].requests[0].seed


def test_a_corrected_event_makes_queued_work_stale(client, companion, clock, adapters):
    local_comfy(client)
    post = make_post(client, clock)
    job = generate(client, post)
    ok(client.post(f"/api/events/{post['events'][0]['id']}/correct",
                   json={'summary': 'Mira walked the dog instead.', 'details': {}}))
    drain(client)
    stale = ok(client.get(f"/api/images/jobs/{job['id']}"))
    assert stale['status'] == 'cancelled' and stale['error_code'] == 'stale_inputs'
    assert adapters['comfyui'].requests == [] and not stale['retry_original_available']
    refused = client.post(f"/api/images/jobs/{job['id']}/retry")
    assert refused.status_code == 409
    fresh = ok(client.post(f"/api/images/jobs/{job['id']}/retry", json={'current_settings': True}))
    assert 'dog' in fresh['prompt']


def test_a_finished_image_of_a_corrected_event_is_marked_outdated(client, companion, clock, adapters):
    """One event through post, image and correction (acceptance: chat and feed coherence)."""
    local_comfy(client)
    clock.advance(timedelta(hours=2))
    start = clock.now() - timedelta(hours=1)
    event = ok(client.post('/api/events', json={
        'idempotency_key': 'event-place', 'kind': 'ordinary', 'summary': 'Mira had a coffee at The Charmery.',
        'details': {'post': 'Quiet corner.', 'place': {'id': 'the-charmery', 'name': 'The Charmery', 'kind': 'cafe'}},
        'starts_at': start.isoformat(), 'ends_at': (start + timedelta(minutes=30)).isoformat()}))
    ok(client.post(f"/api/events/{event['id']}/commit"))
    post = ok(client.post('/api/feed/posts', json={'event_id': event['id']}))
    generate(client, post)
    drain(client)
    assert post_image(client, post)['outdated'] is False
    ok(client.post(f"/api/events/{event['id']}/correct",
                   json={'summary': 'Mira had a coffee at Artifact Coffee.', 'details': event['details']}))
    image = post_image(client, post)
    assert image['status'] == 'completed' and image['outdated'] is True
    preview = ok(client.post('/api/images/preview', json={'post_id': post['id']}))
    assert 'Artifact Coffee' in preview['prompt'] and 'Charmery' not in preview['prompt']
    generate(client, post)
    drain(client)
    assert post_image(client, post)['outdated'] is False


def test_a_carried_over_image_is_not_marked_outdated(client, companion, clock, adapters):
    local_comfy(client)
    post = make_post(client, clock)
    generate(client, post)
    drain(client)
    clock.advance(timedelta(hours=1))
    message = ok(client.post('/api/conversation/messages', json={'text': 'Hi', 'client_id': 'client-0001'}))['message']
    created = ok(client.post('/api/timelines', json={'message_id': message['id'], 'text': 'Hello'}))
    ok(client.post(f"/api/timelines/{created['id']}/activate"))
    [copy] = ok(client.get('/api/feed'))['posts']
    assert copy['id'] != post['id'] and copy['image']['status'] == 'completed'
    assert copy['image']['outdated'] is False


def test_rechecked_at_dispatch_when_the_request_becomes_nsfw(client, companion, clock, adapters):
    hosted = add_backend(client, kind='hosted', provider='openai', model='gpt-image-1', api_key='k')
    post = make_post(client, clock)
    job = generate(client, post)
    database = client.app.state.database
    with database.connect(write=True) as connection:
        inputs = json.loads(connection.execute('SELECT inputs FROM image_jobs WHERE id=?', (job['id'],)).fetchone()[0])
        inputs['prompt'] += ' Topless.'
        connection.execute('UPDATE image_jobs SET inputs=? WHERE id=?', (json.dumps(inputs), job['id']))
    drain(client)
    assert adapters['hosted'].requests == []
    assert ok(client.get(f"/api/images/jobs/{job['id']}"))['error_code'] == 'not_eligible'
    assert hosted['accepts_nsfw'] is False


def test_provider_refusal_reclassifies_and_falls_back_only_to_local(client, companion, clock, adapters):
    hosted = add_backend(client, kind='hosted', provider='openrouter', model='m', api_key='k')
    second_hosted = add_backend(client, kind='hosted', provider='openai', model='gpt-image-1', api_key='k')
    local = local_comfy(client)
    ok(client.put('/api/images/settings', json={'fallback': True}))
    adapters['hosted'].outcomes = [AdapterError('refused', 'refused')]
    post = make_post(client, clock)
    job = generate(client, post)
    drain(client)
    refused = ok(client.get(f"/api/images/jobs/{job['id']}"))
    assert refused['classification'] == 'nsfw' and 'refused by the provider' in refused['classification_reasons']
    assert len(adapters['hosted'].requests) == 1 and adapters['hosted'].requests[0].backend['id'] == hosted['id']
    jobs = ok(client.get('/api/images/jobs', params={'post_id': post['id']}))['jobs']
    assert jobs[0]['backend_id'] == local['id'] and jobs[0]['trigger'] == 'fallback' and jobs[0]['current']
    assert jobs[0]['status'] == 'completed' and second_hosted['id'] not in {job['backend_id'] for job in jobs}


def test_failure_without_fallback_does_not_move_on(client, companion, clock, adapters):
    add_backend(client, kind='codex')
    local_comfy(client)
    adapters['codex'].outcomes = [AdapterError('timeout', 'timed out')]
    post = make_post(client, clock)
    generate(client, post)
    drain(client)
    assert adapters['comfyui'].requests == []
    assert post_image(client, post)['status'] == 'failed'


def test_codex_auth_error_stops_its_queue_until_sign_in(client, companion, clock, adapters):
    codex = add_backend(client, kind='codex')
    adapters['codex'].outcomes = [AdapterError('auth', 'Run codex login.')]
    posts = [make_post(client, clock, key=f'event-000{index}') for index in range(3)]
    ids = [generate(client, post)['id'] for post in posts]
    drain(client)
    assert len(adapters['codex'].requests) == 1
    states = [ok(client.get(f'/api/images/jobs/{job_id}')) for job_id in ids]
    assert states[0]['status'] == 'failed' and states[0]['error_code'] == 'auth'
    assert [state['status'] for state in states[1:]] == ['queued', 'queued']
    assert states[1]['waiting_for'] == 'Run codex login.'
    ok(client.post(f"/api/images/backends/{codex['id']}/unblock"))
    drain(client)
    assert len(adapters['codex'].requests) == 3


def test_codex_runs_one_at_a_time_across_backends(client, companion, clock, adapters):
    add_backend(client, kind='codex')
    add_backend(client, kind='codex', label='Second login')
    posts = [make_post(client, clock, key=f'event-000{index}') for index in range(2)]
    for post in posts:
        generate(client, post)

    async def scenario():
        adapters['codex'].gate = asyncio.Event()
        started = client.app.state.images.dispatch()
        await asyncio.sleep(0)
        running = len(adapters['codex'].requests)
        adapters['codex'].gate.set()
        await client.app.state.images.drain()
        return len(started), running
    assert asyncio.run(scenario()) == (1, 1)
    assert len(adapters['codex'].requests) == 2


def test_cancel_and_restart_recovery(client, companion, clock, adapters, app):
    local_comfy(client)
    post = make_post(client, clock)
    job = generate(client, post)
    cancelled = ok(client.post(f"/api/images/jobs/{job['id']}/cancel"))
    assert cancelled['status'] == 'cancelled'
    queued = generate(client, post)
    from companion.images import jobs as jobs_module
    jobs_module.recover(app.state.database)
    interrupted = ok(client.get(f"/api/images/jobs/{queued['id']}"))
    assert interrupted['status'] == 'interrupted' and post_image(client, post)['status'] == 'interrupted'
    drain(client)
    assert adapters['comfyui'].requests == []


def test_cancel_a_running_job(client, companion, clock, adapters):
    local_comfy(client)
    post = make_post(client, clock)
    job = generate(client, post)
    adapters['comfyui'].gate = asyncio.Event()

    async def scenario():
        client.app.state.images.dispatch()
        await asyncio.sleep(0)
        return await client.app.state.images.cancel(job['id'])
    result = asyncio.run(scenario())
    assert result['status'] == 'cancelled' and 'removed from ComfyUI' in result['error']


def test_invalid_output_is_not_an_image(client, companion, clock, adapters):
    local_comfy(client)
    adapters['comfyui'].outcomes = [b'<html>error</html>']
    post = make_post(client, clock)
    job = generate(client, post)
    drain(client)
    assert ok(client.get(f"/api/images/jobs/{job['id']}"))['error_code'] == 'invalid_output'


def test_automatic_cadence_is_bounded_and_skips_digests(client, companion, clock, adapters):
    local_comfy(client)
    ok(client.put('/api/settings', json={'background_activity': True}))
    early = make_post(client, clock, key='event-early')
    ok(client.put('/api/images/settings', json={'automatic_images': True, 'daily_limit': 1}))
    runner = client.app.state.images
    runner.automatic()
    assert post_image(client, early)['status'] == 'none'
    later = make_post(client, clock, key='event-later')
    runner.automatic()
    runner.automatic()
    third = make_post(client, clock, key='event-third')
    runner.automatic()
    assert post_image(client, later)['status'] == 'queued' and post_image(client, third)['status'] == 'none'
    ok(client.post('/api/pause'))
    clock.advance(timedelta(days=2))
    runner.automatic()
    assert post_image(client, third)['status'] == 'none'


def test_queue_limit(client, companion, clock):
    local_comfy(client)
    ok(client.put('/api/images/settings', json={'queue_limit': 1}))
    post = make_post(client, clock)
    generate(client, post)
    assert client.post('/api/images/jobs', json={'post_id': post['id']}).status_code == 409


def test_preview_shows_prompt_and_route_without_queuing(client, companion, clock):
    local_comfy(client)
    post = make_post(client, clock)
    preview = ok(client.post('/api/images/preview', json={'post_id': post['id'], 'marked_nsfw': True}))
    assert preview['classification']['tier'] == 'nsfw' and preview['refusal'] is None
    assert ok(client.get('/api/images/jobs', params={'post_id': post['id']}))['jobs'] == []


def test_saved_keys_stay_out_of_the_api(client, companion):
    backend = add_backend(client, kind='hosted', provider='openrouter', model='m', api_key='sk-secret')
    assert 'sk-secret' not in json.dumps(ok(client.get('/api/images/backends')))
    assert backend['has_key'] and client.app.state.vault.get(f"image-backend:{backend['id']}") == 'sk-secret'


# Adapters against stand-in servers --------------------------------------------------------------

def request_for(kind, config, **values) -> ImageRequest:
    base = {'job_id': 'job1', 'prompt': 'A café', 'negative': 'text', 'seed': 7, 'width': 1024, 'height': 1024,
            'backend': {'kind': kind, 'provider': values.pop('provider', kind)}, 'config': config}
    return ImageRequest(**{**base, **values})


class ComfyStandIn:
    def __init__(self, history_status='success'):
        self.prompts = []
        self.deleted = []
        self.interrupted = []
        self.history_calls = 0
        self.history_status = history_status
        self.pending = True
        self.info_calls = []

    def __call__(self, request: httpx.Request):
        path = request.url.path
        if path == '/prompt':
            self.prompts.append(json.loads(request.content)['prompt'])
            return httpx.Response(200, json={'prompt_id': 'p1', 'number': 1, 'node_errors': {}})
        if path == '/history/p1':
            self.history_calls += 1
            if self.history_calls < 2 or self.history_status == 'never':
                return httpx.Response(200, json={})
            if self.history_status == 'error':
                return httpx.Response(200, json={'p1': {'status': {'status_str': 'error', 'messages': [
                    ['execution_error', {'exception_message': 'CUDA out of memory'}]]}, 'outputs': {}}})
            return httpx.Response(200, json={'p1': {'status': {'status_str': 'success', 'completed': True},
                                                    'outputs': {'9': {'images': [{'filename': 'a.png', 'subfolder': '',
                                                                                  'type': 'output'}]}}}})
        if path == '/view':
            return httpx.Response(200, content=png(1024, 1024))
        if path == '/queue' and request.method == 'GET':
            return httpx.Response(200, json={'queue_running': [] if self.pending else [[1, 'p1', {}, {}, []]],
                                             'queue_pending': [[1, 'p1', {}, {}, []]] if self.pending else []})
        if path == '/queue':
            self.deleted.append(json.loads(request.content))
            return httpx.Response(200)
        if path == '/interrupt':
            self.interrupted.append(json.loads(request.content))
            return httpx.Response(200)
        if path.startswith('/object_info'):
            return self.object_info(request)
        return httpx.Response(404)

    def object_info(self, request: httpx.Request):
        """The whole node list for the check; one node's entry, from the user's files, for a listing."""
        if request.url.path == '/object_info':
            return httpx.Response(200, json={
                'UNETLoader': {'input': {'required': {'unet_name': [['other.safetensors'], {}],
                                                      'weight_dtype': [['default'], {}]}}},
                'CLIPTextEncode': {'input': {'required': {'text': ['STRING', {}], 'clip': ['CLIP']}}}})
        self.info_calls.append(str(request.url))
        return httpx.Response(200, json={key: value for key, value in USER_FILES.items()
                                         if request.url.path == f'/object_info/{key}'})


# A real Windows ComfyUI 0.39.0 lists files in subfolders with backslashes; they are kept exactly.
MODEL = 'Krea 2\\Muse by Stable Yogi Krea2 V3.5 Civ NVFP4 C84.safetensors'
ENCODER = 'LLM\\qwen3-vl-4b-heretic_nvfp4.safetensors'
VAE = 'Qwen\\qwenImageVAESharpKrea2_bf16.safetensors'
PHONE = 'Krea 2\\phone_photography_2025_krea2.safetensors'
# The user's own files, in both of ComfyUI's combo formats (the newer one is ["COMBO", {"options": [...]}]).
USER_FILES = {
    'UNETLoader': {'input': {'required': {
        'unet_name': [[MODEL, 'krea2_turbo_fp8_scaled.safetensors']],
        'weight_dtype': [['default', 'fp8_e4m3fn']]}}},
    'CLIPLoader': {'input': {'required': {
        'clip_name': ['COMBO', {'options': [ENCODER]}],
        'type': ['COMBO', {'options': ['stable_diffusion', 'krea2']}]}, 'optional': {'device': [['default', 'cpu']]}}},
    'VAELoader': {'input': {'required': {'vae_name': [[VAE, 'pixel_space']]}}},
    'LoraLoaderModelOnly': {'input': {'required': {'lora_name': [[PHONE, 'sdxl\\detail.safetensors', 'prospero-x.safetensors']],
                                                   'strength_model': ['FLOAT', {}]}}},
}
CHOSEN = {'unet_name': MODEL, 'clip_name': ENCODER, 'vae_name': VAE}


def test_comfyui_fills_the_krea2_template_and_fetches_the_output():
    server = ComfyStandIn()
    adapter = ComfyAdapter(httpx.MockTransport(server), poll_seconds=0)
    result = asyncio.run(adapter.generate(request_for('comfyui', {'base_url': 'http://127.0.0.1:8188'})))
    graph = server.prompts[0]
    assert graph['4']['inputs']['text'] == 'A café' and graph['5']['inputs']['text'] == 'text'
    assert graph['7']['inputs']['seed'] == 7 and graph['6']['inputs']['width'] == 1024
    assert result.data.startswith(b'\x89PNG') and result.model == 'krea2_turbo_fp8_scaled.safetensors'
    assert result.workflow == 'krea2-turbo' and result.remote_id == 'p1'


def test_comfyui_reports_execution_errors_and_timeouts():
    adapter = ComfyAdapter(httpx.MockTransport(ComfyStandIn('error')), poll_seconds=0)
    with pytest.raises(AdapterError) as error:
        asyncio.run(adapter.generate(request_for('comfyui', {'base_url': 'http://127.0.0.1:8188'})))
    assert 'CUDA out of memory' in error.value.message
    server = ComfyStandIn('never')
    adapter = ComfyAdapter(httpx.MockTransport(server), poll_seconds=0.001, timeout_seconds=0.05)
    with pytest.raises(AdapterError) as timeout:
        asyncio.run(adapter.generate(request_for('comfyui', {'base_url': 'http://127.0.0.1:8188'})))
    assert timeout.value.code == 'timeout' and server.deleted == [{'delete': ['p1']}] and server.interrupted == []


def test_comfyui_cancel_interrupts_only_its_own_running_prompt():
    server = ComfyStandIn('never')
    server.pending = False
    adapter = ComfyAdapter(httpx.MockTransport(server), poll_seconds=0.001)

    async def scenario():
        task = asyncio.create_task(adapter.generate(request_for('comfyui', {'base_url': 'http://127.0.0.1:8188'})))
        await asyncio.sleep(0.02)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(scenario())
    assert server.interrupted == [{'prompt_id': 'p1'}] and server.deleted == []


def test_comfyui_check_lists_missing_nodes_and_models():
    adapter = ComfyAdapter(httpx.MockTransport(ComfyStandIn()))
    report = asyncio.run(adapter.check({}, {'base_url': 'http://127.0.0.1:8188'}))
    assert not report.ok
    assert any('krea2_turbo_fp8_scaled.safetensors' in line for line in report.details)
    assert any('Missing node: CLIPLoader' in line for line in report.details)


def test_comfyui_custom_workflow_needs_a_prompt_marker(client, companion):
    bad = client.post('/api/images/backends', json={'kind': 'comfyui', 'base_url': 'http://127.0.0.1:8188',
                                                     'workflow': json.dumps({'1': {'class_type': 'X', 'inputs': {}}})})
    assert bad.status_code == 422 and '{{prompt}}' in bad.json()['detail']


def test_comfyui_lists_the_servers_files_for_each_loader():
    server = ComfyStandIn()
    adapter = ComfyAdapter(httpx.MockTransport(server))
    files = asyncio.run(adapter.files({'base_url': 'http://127.0.0.1:8188'}))
    assert files == {'unet_name': [MODEL, 'krea2_turbo_fp8_scaled.safetensors'], 'clip_name': [ENCODER],
                     'clip_type': ['stable_diffusion', 'krea2'], 'vae_name': [VAE, 'pixel_space'],
                     'lora': [PHONE, 'sdxl\\detail.safetensors', 'prospero-x.safetensors']}
    assert server.info_calls == [f'http://127.0.0.1:8188/object_info/{name}'
                                 for name in ('UNETLoader', 'CLIPLoader', 'VAELoader', 'LoraLoaderModelOnly')]


def test_comfyui_puts_chosen_files_in_the_built_in_workflow_only():
    server = ComfyStandIn()
    adapter = ComfyAdapter(httpx.MockTransport(server), poll_seconds=0)
    config = {'base_url': 'http://127.0.0.1:8188', **CHOSEN}
    result = asyncio.run(adapter.generate(request_for('comfyui', config)))
    graph = server.prompts[0]
    assert graph['1']['inputs']['unet_name'] == CHOSEN['unet_name'] and result.model == CHOSEN['unet_name']
    assert graph['2']['inputs'] == {'clip_name': CHOSEN['clip_name'], 'type': 'krea2'}
    assert graph['3']['inputs']['vae_name'] == CHOSEN['vae_name']
    custom = {'1': {'class_type': 'UNETLoader', 'inputs': {'unet_name': 'mine.safetensors'}},
              '2': {'class_type': 'CLIPTextEncode', 'inputs': {'text': '{{prompt}}'}}}
    asyncio.run(adapter.generate(request_for('comfyui', {**config, 'workflow': json.dumps(custom)})))
    assert server.prompts[1]['1']['inputs']['unet_name'] == 'mine.safetensors'


def test_comfyui_check_reports_the_chosen_files():
    def server(request):
        if request.url.path == '/object_info':
            return httpx.Response(200, json={**USER_FILES, **{name: {'input': {'required': {}}} for name in (
                'CLIPTextEncode', 'EmptyLatentImage', 'KSampler', 'VAEDecode', 'SaveImage')}})
        return httpx.Response(404)
    adapter = ComfyAdapter(httpx.MockTransport(server))
    defaults = asyncio.run(adapter.check({}, {'base_url': 'http://127.0.0.1:8188'}))
    assert not defaults.ok and any('qwen_image_vae.safetensors' in line for line in defaults.details)
    chosen = asyncio.run(adapter.check({}, {'base_url': 'http://127.0.0.1:8188', **CHOSEN}))
    assert chosen.ok, chosen.details
    missing = asyncio.run(adapter.check({}, {'base_url': 'http://127.0.0.1:8188', **CHOSEN, 'vae_name': 'gone.safetensors'}))
    assert missing.details == ['Missing file or option for VAELoader.vae_name: gone.safetensors.']
    # The subfolder is part of the name: the bare file name is not the server's file.
    bare = asyncio.run(adapter.check({}, {'base_url': 'http://127.0.0.1:8188', **CHOSEN,
                                          'clip_name': 'qwen3-vl-4b-heretic_nvfp4.safetensors'}))
    assert bare.details == ['Missing file or option for CLIPLoader.clip_name: qwen3-vl-4b-heretic_nvfp4.safetensors.']


@pytest.fixture
def comfy_client(tmp_path, clock, provider):
    def handler(request):
        if request.url.host == 'down.example':
            raise httpx.ConnectError('refused')
        return stand_in(request)
    stand_in = ComfyStandIn()
    adapters = {'comfyui': ComfyAdapter(httpx.MockTransport(handler)), 'codex': FakeAdapter(), 'hosted': FakeAdapter()}
    app = create_app(tmp_path / 'workspace' / 'companion.sqlite3', clock=clock, vault=MemoryVault(),
                     provider=provider, life_tasks=False, image_adapters=adapters)
    with TestClient(app, headers={CLIENT_HEADER: 'workspace'}) as test_client:
        yield test_client


def test_backend_model_files_are_saved_listed_and_cleared(comfy_client):
    backend = local_comfy(comfy_client)
    assert backend['model_files'] == {'unet_name': '', 'clip_name': '', 'clip_type': '', 'vae_name': ''}
    listed = ok(comfy_client.get(f"/api/images/backends/{backend['id']}/files"))
    assert listed['ok'] and listed['options']['clip_name'] == [ENCODER]
    assert listed['defaults'] == {'unet_name': 'krea2_turbo_fp8_scaled.safetensors',
                                  'clip_name': 'qwen3vl_4b_fp8_scaled.safetensors', 'clip_type': 'krea2',
                                  'vae_name': 'qwen_image_vae.safetensors'}
    saved = ok(comfy_client.put(f"/api/images/backends/{backend['id']}", json={**CHOSEN, 'clip_type': 'krea2'}))
    assert saved['model_files'] == {**CHOSEN, 'clip_type': 'krea2'}
    details = ok(comfy_client.post(f"/api/images/backends/{backend['id']}/check"))['details']
    assert f"Missing file or option for UNETLoader.unet_name: {CHOSEN['unet_name']}." in details
    assert not any('krea2_turbo_fp8_scaled' in line for line in details)
    cleared = ok(comfy_client.put(f"/api/images/backends/{backend['id']}", json={'unet_name': '', 'label': 'GPU'}))
    assert cleared['model_files'] == {**CHOSEN, 'unet_name': '', 'clip_type': 'krea2'}
    bad = comfy_client.put(f"/api/images/backends/{backend['id']}", json={'vae_name': 'a\nb.safetensors'})
    assert bad.status_code == 422


def test_backend_files_from_an_unreachable_server_or_another_kind(comfy_client):
    down = add_backend(comfy_client, kind='comfyui', base_url='http://down.example:8188', controlled_machine=True)
    listed = ok(comfy_client.get(f"/api/images/backends/{down['id']}/files"))
    assert not listed['ok'] and 'Cannot reach' in listed['error'] and listed['options']['unet_name'] == []
    assert listed['defaults']['vae_name'] == 'qwen_image_vae.safetensors'
    codex = add_backend(comfy_client, kind='codex')
    assert comfy_client.get(f"/api/images/backends/{codex['id']}/files").status_code == 422
    assert codex['model_files'] is None
    assert ok(comfy_client.put(f"/api/images/backends/{codex['id']}", json={'unet_name': 'x'}))['model_files'] is None


def test_backend_files_put_krea_2_files_first_and_style_loras_are_saved(comfy_client):
    """The lists only sort: Krea 2's files (by name or folder, or the Qwen encoder and VAE it uses)
    come first and are named in `krea`; nothing is hidden for not matching."""
    backend = local_comfy(comfy_client)
    listed = ok(comfy_client.get(f"/api/images/backends/{backend['id']}/files"))
    assert listed['options']['unet_name'] == [MODEL, 'krea2_turbo_fp8_scaled.safetensors']
    assert listed['krea']['clip_name'] == [ENCODER] and listed['krea']['vae_name'] == [VAE]
    assert listed['options']['lora'][0] == PHONE and listed['krea']['lora'] == [PHONE]
    assert 'sdxl\\detail.safetensors' in listed['options']['lora'] and listed['character_lora'] is None
    assert backend['style_loras'] == []
    style = {'name': PHONE, 'strength': 0.7, 'trigger': 'phone photo'}
    saved = ok(comfy_client.put(f"/api/images/backends/{backend['id']}", json={'style_loras': [style]}))
    assert saved['style_loras'] == [style]
    details = ok(comfy_client.post(f"/api/images/backends/{backend['id']}/check"))['details']
    assert 'Missing node: LoraLoaderModelOnly, which applies LoRAs.' in details  # This stand-in has no LoRA node.
    info = {'LoraLoaderModelOnly': USER_FILES['LoraLoaderModelOnly']}
    assert ComfyAdapter.lora_problems(info, None, [style]) == []
    assert ComfyAdapter.lora_problems(info, 'prospero-x.safetensors', [{'name': 'gone.safetensors'}]) == [
        "The style LoRA gone.safetensors is not in ComfyUI's loras folder."]
    assert ok(comfy_client.put(f"/api/images/backends/{backend['id']}", json={'style_loras': []}))['style_loras'] == []
    too_many = comfy_client.put(f"/api/images/backends/{backend['id']}", json={'style_loras': [style] * 4})
    assert too_many.status_code == 422


def test_a_style_lora_never_makes_a_server_less_strict(comfy_client):
    """A LoRA whose name or trigger reads as adult content only goes on a server that accepts NSFW
    requests: one on this computer or one the user controls (F6)."""
    nsfw = {'name': 'nsfw_nude_krea2.safetensors', 'strength': 0.8, 'trigger': ''}
    remote = add_backend(comfy_client, kind='comfyui', base_url='http://gpu.example:8188')
    refused = comfy_client.put(f"/api/images/backends/{remote['id']}", json={'style_loras': [nsfw]})
    assert refused.status_code == 422 and 'this computer' in refused.json()['detail']
    safe = {'name': PHONE, 'strength': 0.7, 'trigger': 'phone photo'}
    assert ok(comfy_client.put(f"/api/images/backends/{remote['id']}", json={'style_loras': [safe]}))['style_loras'] == [safe]
    local = local_comfy(comfy_client)
    assert ok(comfy_client.put(f"/api/images/backends/{local['id']}", json={'style_loras': [nsfw]}))['style_loras'] == [nsfw]
    created = comfy_client.post('/api/images/backends', json={'kind': 'comfyui', 'base_url': 'http://gpu.example:8188',
                                                             'style_loras': [nsfw]})
    assert created.status_code == 422


def test_model_links_are_pages_with_a_licence_note(client):
    links = ok(client.get('/api/images/model-links'))['links']
    assert {link['role'] for link in links} == {'model', 'clip', 'vae'}
    for link in links:
        assert link['url'].startswith('https://huggingface.co/') and '/resolve/' not in link['url']
        assert link['name'] and link['licence']
    assert any('Gated' in link['licence'] for link in links if link['url'].endswith('krea/Krea-2-Turbo'))


FAKE_CODEX = '''
import json, os, pathlib, sys
args = sys.argv[1:]
mode = os.environ.get("FAKE_CODEX_MODE", "ok")
if args == ["--version"]:
    print("codex-cli 0.160.1"); sys.exit(0)
if args == ["login", "status"]:
    print({"apikey": "Logged in using an API key - sk-***", "out": "Not logged in"}.get(mode, "Logged in using ChatGPT"))
    sys.exit(0)
# Codex reads its prompt as UTF-8 whatever the console code page is.
pathlib.Path(os.environ["FAKE_CLI_LOG"]).write_text(" ".join(args) + "\\n" + sys.stdin.buffer.read().decode("utf-8"),
                                                    encoding="utf-8")
emit = lambda event: print(json.dumps(event), flush=True)
emit({"type": "thread.started", "thread_id": "thread-1"})
emit({"type": "turn.started"})
if mode == "slow":
    import time; time.sleep(3)  # short: on Windows only the .cmd wrapper is killed
emit({"type": "error", "message": "Reconnecting... 1/5"})
if mode == "auth":
    emit({"type": "turn.failed", "error": {"message": "unexpected status 401 Unauthorized: token expired"}})
    sys.exit(1)
if mode == "refused":
    emit({"type": "turn.failed", "error": {"message": "Your request was rejected by the safety system"}})
    sys.exit(1)
if mode != "none":
    folder = pathlib.Path(os.environ["CODEX_HOME"]) / "generated_images" / "thread-1"
    folder.mkdir(parents=True, exist_ok=True)
    image = folder / "ig_1.png"
    image.write_bytes(bytes.fromhex(os.environ["FAKE_PNG"]))
    if mode == "ok":
        emit({"type": "item.completed", "item": {"type": "image_generation", "saved_path": str(image)}})
emit({"type": "item.completed", "item": {"type": "agent_message", "text": "DONE"}})
emit({"type": "turn.completed", "usage": {}})
'''


@pytest.fixture
def fake_codex(tmp_path, monkeypatch):
    """A stand-in `codex` launcher: a .cmd wrapper on Windows, a script with a shebang elsewhere."""
    home = tmp_path / 'codex-home'
    home.mkdir()
    (home / 'auth.json').write_text('{}')
    monkeypatch.setenv('CODEX_HOME', str(home))
    monkeypatch.setenv('FAKE_CLI_LOG', str(tmp_path / 'cli.log'))
    monkeypatch.setenv('FAKE_PNG', png(1024, 1536).hex())
    raw = tmp_path / 'raw'
    raw.mkdir()
    script = tmp_path / 'fake_codex.py'
    script.write_text(FAKE_CODEX)
    if os.name == 'nt':
        launcher = tmp_path / 'codex.cmd'
        launcher.write_text(f'@"{sys.executable}" "{script}" %*\n')
    else:
        launcher = tmp_path / 'codex'
        launcher.write_text(f'#!{sys.executable}\n{FAKE_CODEX}')
        launcher.chmod(0o755)
    return {'codex': launcher, 'home': home, 'log': tmp_path / 'cli.log', 'raw': raw}


def native_request(fake_codex, **values):
    return request_for('codex', {'cli_path': str(fake_codex['codex'])}, **{'width': 1024, 'height': 1536,
                       'raw_dir': fake_codex['raw'], **values})


def test_codex_native_runs_one_exec_turn_and_copies_the_saved_image(fake_codex):
    result = asyncio.run(CodexAdapter().generate(native_request(fake_codex)))
    args, prompt = fake_codex['log'].read_text(encoding='utf-8').split('\n', 1)
    assert args.startswith('exec --json --skip-git-repo-check --ephemeral --ignore-user-config --ignore-rules '
                           '--sandbox read-only --cd ') and args.endswith(' -')
    assert '1024x1536' in prompt and 'A café' in prompt and 'Avoid: text' in prompt
    assert result.raw_path == fake_codex['raw'] / 'job1.png' and result.data[:4] == b'\x89PNG'
    assert result.remote_id == 'thread-1' and result.workflow == 'codex exec' and result.seed is None


def test_codex_native_finds_the_image_in_the_thread_folder(fake_codex, monkeypatch):
    monkeypatch.setenv('FAKE_CODEX_MODE', 'folder')
    result = asyncio.run(CodexAdapter().generate(native_request(fake_codex)))
    assert result.raw_path.exists()


@pytest.mark.parametrize(('mode', 'code'), [('auth', 'auth'), ('refused', 'refused'), ('none', 'failed')])
def test_codex_native_failures(fake_codex, monkeypatch, mode, code):
    monkeypatch.setenv('FAKE_CODEX_MODE', mode)
    with pytest.raises(AdapterError) as error:
        asyncio.run(CodexAdapter().generate(native_request(fake_codex)))
    assert error.value.code == code and 'Reconnecting' not in error.value.message


@pytest.mark.parametrize(('mode', 'ok', 'words'), [('ok', True, 'experimental'), ('apikey', True, 'API key'),
                                                   ('out', False, 'not signed in')])
def test_codex_native_check_reads_the_login_state(fake_codex, monkeypatch, mode, ok, words):
    monkeypatch.setenv('FAKE_CODEX_MODE', mode)
    report = asyncio.run(CodexAdapter().check({}, {'cli_path': str(fake_codex['codex'])}))
    assert report.ok is ok and words in report.summary and any('0.160.1' in line for line in report.details)


def hosted_server(responses, seen):
    def handler(request: httpx.Request):
        seen.append(request)
        return responses.pop(0)
    return httpx.MockTransport(handler)


def test_hosted_images_style_sends_only_the_prompt():
    seen = []
    body = {'data': [{'b64_json': base64.b64encode(png()).decode()}], 'usage': {'total_tokens': 10}}
    adapter = HostedAdapter(hosted_server([httpx.Response(200, json=body)], seen))
    request = request_for('hosted', {'base_url': 'https://generativelanguage.googleapis.com/v1beta/openai',
                                     'model': 'imagen-4', 'api_style': 'images'}, provider='google', key='g-key')
    result = asyncio.run(adapter.generate(request))
    sent = json.loads(seen[0].content)
    assert seen[0].url.path.endswith('/images/generations') and seen[0].headers['authorization'] == 'Bearer g-key'
    assert set(sent) == {'model', 'prompt', 'n', 'size', 'response_format'} and sent['size'] == '1024x1024'
    assert result.usage == {'total_tokens': 10} and result.data.startswith(b'\x89PNG')


def test_hosted_chat_style_reads_openrouter_images():
    seen = []
    url = 'data:image/png;base64,' + base64.b64encode(png()).decode()
    body = {'id': 'gen-1', 'choices': [{'message': {'content': '', 'images': [{'image_url': {'url': url}}]}}],
            'usage': {'cost': 0.04}}
    adapter = HostedAdapter(hosted_server([httpx.Response(200, json=body)], seen))
    request = request_for('hosted', {'base_url': 'https://openrouter.ai/api/v1', 'model': 'google/gemini-image',
                                     'api_style': 'chat'}, provider='openrouter', key='k')
    result = asyncio.run(adapter.generate(request))
    assert json.loads(seen[0].content)['modalities'] == ['image', 'text']
    assert result.usage == {'cost': 0.04} and result.remote_id == 'gen-1'


@pytest.mark.parametrize(('response', 'code'), [
    (httpx.Response(401, json={}), 'auth'),
    (httpx.Response(429, json={}), 'rate_limited'),
    (httpx.Response(400, json={'error': {'code': 'content_policy_violation'}}), 'refused'),
    (httpx.Response(500, json={}), 'failed'),
    (httpx.Response(200, json={'choices': [{'finish_reason': 'content_filter', 'message': {}}]}), 'refused'),
    (httpx.Response(200, json={'choices': [{'message': {'content': 'Here you go'}}]}), 'invalid_output'),
])
def test_hosted_errors_are_typed(response, code):
    adapter = HostedAdapter(hosted_server([response], []))
    request = request_for('hosted', {'base_url': 'https://openrouter.ai/api/v1', 'model': 'm', 'api_style': 'chat'},
                          provider='openrouter', key='k')
    with pytest.raises(AdapterError) as error:
        asyncio.run(adapter.generate(request))
    assert error.value.code == code


def test_storage_reads_jpeg_and_webp_headers():
    from companion.images import storage
    jpeg = b'\xff\xd8\xff\xe0' + struct.pack('>H', 16) + b'\x00' * 14 + b'\xff\xc0' + struct.pack('>HBHH', 17, 8, 600,
                                                                                                    800)
    assert storage.sniff(jpeg) == ('jpg', 800, 600)
    webp = b'RIFF' + b'\x00' * 4 + b'WEBPVP8X' + b'\x00' * 8 + (99).to_bytes(3, 'little') + (49).to_bytes(3, 'little')
    assert storage.sniff(webp) == ('webp', 100, 50)


def test_restored_workspaces_drop_image_keys(client, companion, tmp_path):
    from companion import backup
    add_backend(client, kind='hosted', provider='openrouter', model='m', api_key='k')
    ok(client.put('/api/images/settings', json={'automatic_images': True}))
    archive = backup.create(client.app.state.database, tmp_path / 'backups')
    restored = backup.restore(Path(archive['path']), tmp_path / 'restored' / 'companion.sqlite3')
    with restored.connect() as connection:
        row = connection.execute('SELECT credential_ref, enabled FROM image_backends').fetchone()
        settings = connection.execute('SELECT automatic_images FROM image_settings').fetchone()
    assert row['credential_ref'] is None and settings['automatic_images'] == 0


def test_switching_timelines_cancels_images_not_started(client, companion, clock, adapters):
    local_comfy(client)
    post = make_post(client, clock)
    job = generate(client, post)
    message = ok(client.post('/api/conversation/messages', json={'text': 'Hi', 'client_id': 'client-image-01'}))['message']
    fork = ok(client.post('/api/timelines', json={'message_id': message['id'], 'text': 'Hello'}))
    ok(client.post(f"/api/timelines/{fork['id']}/activate"))
    drain(client)
    cancelled = ok(client.get(f"/api/images/jobs/{job['id']}"))
    assert cancelled['status'] == 'cancelled' and 'set aside' in cancelled['error']
    assert adapters['comfyui'].requests == []


def test_codex_missing_login_unverified_size_and_old_imagegen_location(fake_codex, monkeypatch):
    with pytest.raises(AdapterError) as size:
        asyncio.run(CodexAdapter().generate(native_request(fake_codex, width=1216, height=832)))
    assert size.value.code == 'incompatible'
    # A location saved for the retired chatgpt-imagegen method falls back to codex on PATH.
    monkeypatch.setenv('PATH', '')
    old = request_for('codex', {'cli_path': str(fake_codex['codex'].with_name('chatgpt-imagegen'))},
                      raw_dir=fake_codex['raw'])
    with pytest.raises(AdapterError) as missing_cli:
        asyncio.run(CodexAdapter().generate(old))
    assert missing_cli.value.code == 'unavailable' and 'Codex CLI' in missing_cli.value.message
    (fake_codex['home'] / 'auth.json').unlink()
    with pytest.raises(AdapterError) as signed_out:
        asyncio.run(CodexAdapter().generate(native_request(fake_codex)))
    assert signed_out.value.code == 'auth' and 'codex login' in signed_out.value.message


def test_codex_timeout_stops_the_process(fake_codex, monkeypatch):
    monkeypatch.setenv('FAKE_CODEX_MODE', 'slow')

    async def scenario():
        task = asyncio.create_task(CodexAdapter(timeout_seconds=1).generate(native_request(fake_codex)))
        await asyncio.sleep(0.5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(scenario())


def test_a_moment_with_its_own_outfit_leaves_the_usual_clothes_out():
    """A Krea picture showed one black flat and one white sneaker: the appearance's usual work shoes and
    the moment's outfit were both in the prompt."""
    from companion.images import prompts
    appearance = ('Shoulder-length honey-blonde hair with dark roots, freckles, and wire glasses. Usually wears '
                  'black flats and a blazer to work, with a silver ring.')
    kept = prompts.without_clothes(appearance)
    assert 'flats' not in kept and 'blazer' not in kept
    assert 'honey-blonde hair' in kept and 'freckles' in kept and 'glasses' in kept and 'silver ring' in kept
    event = {'summary': 'Studied at the library', 'place': '', 'caption': '', 'mood': ''}
    dressed = prompts.compose('Kim', appearance, [event], 'Candid phone photo, natural light.',
                              'Wearing white sneakers and a green sweater.', dressed=True)
    assert 'flats' not in dressed and 'white sneakers' in dressed and '..' not in dressed
    plain = prompts.compose('Kim', appearance, [event], 'Candid phone photo, natural light.')
    assert 'black flats' in plain and '..' not in plain


def test_the_prompt_is_one_krea_style_paragraph_of_what_a_camera_can_see():
    """Krea 2's guide (docs/prompting.md): medium first, the subject with what can be seen of them and what
    they do, then the light and the camera. A name, backstory, caption or bare mood word gives it nothing to draw."""
    from companion.images import prompts
    appearance = ("Kimberly is a 32-year-old woman with long auburn hair, thin eyebrows she overplucked in college, "
                  "and freckles. She has a faint scar on her chin from a derby fall. She looks like someone who never "
                  "sleeps enough. Kimberly's smile is lopsided.")
    event = {'summary': 'Kimberly studied at the library.', 'place': 'Enoch Pratt Library',
             'caption': 'I am literally so locked in right now', 'mood': 'focused', 'hour': 16,
             'weather': {'rain': True, 'high_f': 60}}
    prompt = prompts.compose('Kimberly Smith', appearance, [event], 'Candid, natural-light photograph',
                             'Wearing a grey hoodie.', dressed=True)
    assert prompt.startswith('Candid, natural-light photograph of a fictional everyday moment.')
    assert 'Kimberly' not in prompt and 'locked in' not in prompt and 'Mood:' not in prompt
    assert 'in college' not in prompt and 'derby' not in prompt and 'looks like someone' not in prompt
    assert 'faint scar on her chin' in prompt and 'Her smile is lopsided' in prompt
    assert 'She is wearing a grey hoodie.' in prompt and 'She studied at the library at Enoch Pratt Library.' in prompt
    assert 'focused, concentrating expression' in prompt and 'late-afternoon light' in prompt and 'rainy' in prompt
    assert prompt.endswith('shallow depth of field.') and '..' not in prompt
    painted = prompts.compose('Kimberly Smith', appearance, [event], 'Watercolour sketch')
    assert 'phone camera' not in painted
    assert prompts.pronoun('') == 'they' and prompts.pronoun('He has a beard.') == 'he'


def test_the_action_is_the_activitys_present_tense_picture_line():
    """A past-tense summary ("studied at the library") drew a selfie in the stacks; each activity has a
    fixed line of what it looks like now. A corrected event keeps its own words."""
    from companion.images import prompts
    from companion.life import composer
    event = {'summary': 'Kim studied at the library.', 'place': 'Enoch Pratt Library', 'caption': '', 'mood': '',
             'activity': 'library', 'with': None}
    prompt = prompts.compose('Kim', 'A woman with short hair.', [event], 'Candid photograph')
    assert 'She is studying at a library table' in prompt and 'at Enoch Pratt Library.' in prompt
    assert 'studied' not in prompt
    dinner = prompts.compose('Kim', '', [{**event, 'activity': 'dinner', 'with': {'name': 'Tasha'}}], 'Candid photograph')
    assert 'They are sitting at a restaurant table' in dinner and ', with a friend.' in dinner and 'Tasha' not in dinner
    corrected = prompts.compose('Kim', '', [{**event, 'summary': 'Kim walked the dog instead.', 'revision': 2}], 'Photo')
    assert 'walked the dog' in corrected
    assert set(prompts.PICTURES) >= {item.key for group in composer.CATALOG.values() for item in group}
