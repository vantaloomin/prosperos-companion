"""Image jobs, content routing and backend adapters (PRD F3–F9)."""
import asyncio
import base64
import json
import struct
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
        if path == '/object_info':
            return httpx.Response(200, json={
                'UNETLoader': {'input': {'required': {'unet_name': [['other.safetensors'], {}],
                                                      'weight_dtype': [['default'], {}]}}},
                'CLIPTextEncode': {'input': {'required': {'text': ['STRING', {}], 'clip': ['CLIP']}}}})
        return httpx.Response(404)


def test_comfyui_fills_the_krea2_template_and_fetches_the_output():
    server = ComfyStandIn()
    adapter = ComfyAdapter(httpx.MockTransport(server), poll_seconds=0)
    result = asyncio.run(adapter.generate(request_for('comfyui', {'base_url': 'http://127.0.0.1:8188'})))
    graph = server.prompts[0]
    assert graph['4']['inputs']['text'] == 'A café' and graph['5']['inputs']['text'] == 'text'
    assert graph['7']['inputs']['seed'] == 7 and graph['6']['inputs']['width'] == 1024
    assert result.data.startswith(b'\x89PNG') and result.model == 'krea2_turbo_fp8_scaled.safetensors'
    assert result.workflow == 'krea2-turbo (unverified)' and result.remote_id == 'p1'


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


FAKE_CLI = '''
import sys, pathlib, os
args = sys.argv[1:]
log = pathlib.Path(os.environ["FAKE_CLI_LOG"])
log.write_text(log.read_text() + " ".join(args) + "\\n" if log.exists() else " ".join(args) + "\\n")
if args == ["--version"]:
    print("chatgpt-imagegen 9.9"); sys.exit(0)
mode = os.environ.get("FAKE_CLI_MODE", "ok")
if mode == "auth":
    sys.exit("refresh_token is no longer valid - run codex login again")
if mode == "slow":
    import time; time.sleep(30)
out = pathlib.Path(args[args.index("-o") + 1])
out.write_bytes(bytes.fromhex(os.environ["FAKE_PNG"]))
print(out)
'''


@pytest.fixture
def fake_cli(tmp_path, monkeypatch):
    script = tmp_path / 'chatgpt-imagegen'
    script.write_text(FAKE_CLI)
    home = tmp_path / 'codex-home'
    home.mkdir()
    (home / 'auth.json').write_text('{}')
    monkeypatch.setenv('CODEX_HOME', str(home))
    monkeypatch.setenv('FAKE_CLI_LOG', str(tmp_path / 'cli.log'))
    monkeypatch.setenv('FAKE_PNG', png(1024, 1536).hex())
    raw = tmp_path / 'raw'
    raw.mkdir()
    return {'script': script, 'home': home, 'log': tmp_path / 'cli.log', 'raw': raw}


def codex_request(fake_cli, **values):
    return request_for('codex', {'cli_path': str(fake_cli['script'])}, width=1024, height=1536,
                       raw_dir=fake_cli['raw'], **values)


def test_codex_calls_the_cli_with_a_verified_size_and_keeps_the_raw_file(fake_cli):
    result = asyncio.run(CodexAdapter().generate(codex_request(fake_cli)))
    line = fake_cli['log'].read_text()
    assert 'A café -o' in line and '--size 1024x1536' in line and '--timeout 300' in line
    assert result.raw_path == fake_cli['raw'] / 'job1.png' and result.raw_path.exists()
    assert result.data[:4] == b'\x89PNG' and result.seed is None


def test_codex_auth_errors_and_missing_login(fake_cli, monkeypatch):
    monkeypatch.setenv('FAKE_CLI_MODE', 'auth')
    with pytest.raises(AdapterError) as error:
        asyncio.run(CodexAdapter().generate(codex_request(fake_cli)))
    assert error.value.code == 'auth' and 'codex login' in error.value.message
    (fake_cli['home'] / 'auth.json').unlink()
    with pytest.raises(AdapterError) as missing:
        asyncio.run(CodexAdapter().generate(codex_request(fake_cli)))
    assert missing.value.code == 'auth'
    report = asyncio.run(CodexAdapter().check({}, {'cli_path': str(fake_cli['script'])}))
    assert not report.ok and 'not signed in' in report.summary


def test_codex_timeout_stops_the_process(fake_cli, monkeypatch):
    monkeypatch.setenv('FAKE_CLI_MODE', 'slow')
    adapter = CodexAdapter(timeout_seconds=1)
    adapter_timeout = 0.5

    async def scenario():
        task = asyncio.create_task(adapter.generate(codex_request(fake_cli)))
        await asyncio.sleep(adapter_timeout)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(scenario())


def test_codex_rejects_unverified_sizes(fake_cli):
    with pytest.raises(AdapterError) as error:
        asyncio.run(CodexAdapter().generate(request_for('codex', {'cli_path': str(fake_cli['script'])},
                                                        width=1216, height=832, raw_dir=fake_cli['raw'])))
    assert error.value.code == 'incompatible'


def test_codex_check_reports_version(fake_cli):
    report = asyncio.run(CodexAdapter().check({}, {'cli_path': str(fake_cli['script'])}))
    assert report.ok and any('9.9' in line for line in report.details)


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
