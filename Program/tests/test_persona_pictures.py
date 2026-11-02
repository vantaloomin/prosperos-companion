# ruff: noqa: F811 - the image test fixtures are reused by name.
"""Your picture: how the user's persona looks, and pictures of moments they share with a companion showing them
(companion/persona_pictures.py)."""
import asyncio
import json
from datetime import timedelta
from pathlib import Path

from companion import persona_pictures
from companion.images import runner, sheet
from companion.images.adapters.base import ImageRequest
from companion.images.adapters.comfyui import stitched, stitches
from companion.images.adapters.hosted import openrouter_body
from tests.test_images import add_backend, drain, generate, ok, png
from tests.test_lora import adapters, app, client  # noqa: F401

COMPANION = png(800, 1200)
YOU = png(900, 1200)
WORKFLOWS = Path(__file__).resolve().parent.parent / 'companion' / 'images' / 'workflows'


def persona(client) -> dict:
    return ok(client.get('/api/worlds'))['persona']


def upload(client, data=YOU):
    return client.post(f"/api/worlds/personas/{persona(client)['id']}/picture", content=data)


def shared_post(client, clock, key='event-0001', summary='Mira went to dinner at Lupa with you.'):
    """A feed post of an outing with the user."""
    clock.advance(timedelta(hours=2))
    start = clock.now() - timedelta(hours=1)
    event = ok(client.post('/api/events', json={
        'idempotency_key': key, 'kind': 'ordinary', 'summary': summary,
        'details': {'post': 'Best pasta in town.', 'mood': 'happy', 'outing': {'id': 'outing-1'}},
        'starts_at': start.isoformat(), 'ends_at': (start + timedelta(minutes=30)).isoformat()}))
    ok(client.post(f"/api/events/{event['id']}/commit"))
    return ok(client.post('/api/feed/posts', json={'event_id': event['id']}))


def test_your_picture_and_looks_belong_to_the_persona(client, companion):
    me = persona(client)
    assert not me.get('picture')
    ok(client.patch(f"/api/worlds/personas/{me['id']}", json={'looks': 'short dark curls, freckles, round glasses'}))
    shown = ok(upload(client))['persona']
    assert shown['picture'] and shown['looks'] == 'short dark curls, freckles, round glasses'
    assert client.get(f"/api/worlds/personas/{me['id']}/picture").content == YOU
    with client.app.state.database.connect() as connection:
        row = connection.execute('SELECT looks, picture FROM persona WHERE id=1').fetchone()
    assert (row['looks'], row['picture']) == (shown['looks'], shown['picture'])
    assert upload(client, b'not a picture').status_code == 422
    # A copy of the persona keeps how they look and their picture.
    copy = ok(client.post(f"/api/worlds/personas/{me['id']}/copy", json={'city_id': 'grandport'}))
    assert copy['looks'] == shown['looks'] and copy['picture'] == shown['picture']
    assert not ok(client.delete(f"/api/worlds/personas/{me['id']}/picture"))['persona']['picture']
    assert client.get(f"/api/worlds/personas/{me['id']}/picture").status_code == 404


def test_a_shared_moment_shows_you_beside_them_following_both_pictures(client, companion, clock, adapters):
    add_backend(client, kind='hosted', provider='openrouter', api_key='k', model='google/gemini-image')
    ok(client.post('/api/lora/portrait/upload', params={'name': 'them.png'}, content=COMPANION))
    ok(client.patch(f"/api/worlds/personas/{persona(client)['id']}", json={'gender': 'woman', 'age': 32,
                                                                           'looks': 'short dark curls, freckles'}))
    ok(upload(client))
    job = generate(client, shared_post(client, clock))
    drain(client)
    sent = adapters['hosted'].requests[0]
    assert 'Beside them is one other person, a woman in her early thirties, short dark curls, freckles.' in sent.prompt
    assert 'only person in the picture' not in sent.prompt and 'with you' not in sent.prompt
    assert sent.reference == COMPANION and sent.others == [YOU]
    assert sheet.FOLLOW_PROFILE not in sent.prompt and sent.prompt.endswith(runner.FOLLOW_USER)
    done = ok(client.get(f"/api/images/jobs/{job['id']}"))
    assert done['identity_method'] == 'text description and their profile picture, and your picture'

    # Off in Settings > Images: the moment is theirs alone again.
    ok(client.put('/api/images/settings', json={'show_me': False}))
    generate(client, shared_post(client, clock, key='event-0002'))
    drain(client)
    alone = adapters['hosted'].requests[1]
    assert 'one other person' not in alone.prompt and alone.others == []


def test_a_moment_of_their_own_never_shows_you(client, companion, clock, adapters):
    add_backend(client, kind='hosted', provider='openrouter', api_key='k', model='google/gemini-image')
    ok(client.patch(f"/api/worlds/personas/{persona(client)['id']}", json={'looks': 'tall, a shaved head'}))
    ok(upload(client))
    from tests.test_images import make_post
    generate(client, make_post(client, clock))
    drain(client)
    sent = adapters['hosted'].requests[0]
    assert 'tall, a shaved head' not in sent.prompt and sent.reference is None and sent.others == []


def test_without_a_picture_of_them_yours_is_the_one_reference(client, companion, clock, adapters):
    add_backend(client, kind='hosted', provider='openrouter', api_key='k', model='google/gemini-image')
    ok(upload(client))
    generate(client, shared_post(client, clock))
    drain(client)
    sent = adapters['hosted'].requests[0]
    assert sent.reference == YOU and sent.others == [] and sent.prompt.endswith(runner.FOLLOW_USER_ONLY)
    # With nothing said and no picture, nobody else is drawn in.
    ok(client.delete(f"/api/worlds/personas/{persona(client)['id']}/picture"))
    generate(client, shared_post(client, clock, key='event-0002'))
    drain(client)
    assert 'one other person' not in adapters['hosted'].requests[1].prompt


def test_a_backend_without_references_draws_you_from_words_only(client, companion, clock, adapters):
    add_backend(client, kind='hosted', provider='google', api_key='k', model='imagen-4')
    ok(client.patch(f"/api/worlds/personas/{persona(client)['id']}", json={'looks': 'a red beard'}))
    ok(upload(client))
    generate(client, shared_post(client, clock))
    drain(client)
    sent = adapters['hosted'].requests[0]
    assert 'a red beard' in sent.prompt and sent.reference is None and sent.others == []


def test_make_one_draws_you_from_how_you_look(client, companion, adapters):
    me = persona(client)
    add_backend(client, kind='hosted', provider='openrouter', api_key='k', model='google/gemini-image')
    refused = client.post(f"/api/worlds/personas/{me['id']}/picture/make")
    assert refused.status_code == 422 and persona_pictures.NO_LOOKS in str(refused.json())
    ok(client.patch(f"/api/worlds/personas/{me['id']}", json={'gender': 'man', 'age': 45, 'looks': 'grey stubble'}))
    adapters['hosted'].outcomes = [png(1024, 1536)]
    assert ok(client.post(f"/api/worlds/personas/{me['id']}/picture/make"))['status'] == 'queued'
    asyncio.run(client.app.state.persona_pictures.drain())
    assert ok(client.get(f"/api/worlds/personas/{me['id']}/picture/make"))['status'] == 'completed'
    sent = adapters['hosted'].requests[0]
    assert 'A man in his mid forties, grey stubble, waist-up portrait' in sent.prompt and sent.reference is None
    assert persona(client)['picture'] and client.get(f"/api/worlds/personas/{me['id']}/picture").content == \
        png(1024, 1536)


def test_make_one_is_refused_where_no_backend_may_draw_it(client, companion):
    me = persona(client)
    ok(client.patch(f"/api/worlds/personas/{me['id']}", json={'looks': 'grey stubble'}))
    assert client.post(f"/api/worlds/personas/{me['id']}/picture/make").status_code == 409


def test_comfyui_follows_both_pictures_side_by_side_unless_its_picture_starts_from_the_reference():
    assert {name: stitches(json.loads((WORKFLOWS / f'{name}-reference.json').read_text())) for name in
            ('krea2-turbo', 'qwen-image-2.1', 'booru-sdxl', 'z-image-turbo', 'anima')} == {
        'krea2-turbo': True, 'qwen-image-2.1': True, 'booru-sdxl': True, 'z-image-turbo': False, 'anima': False}
    graph = {'4': {'class_type': 'LoadImage', 'inputs': {'image': 'them.png'}},
             '5': {'class_type': 'ImageScaleToTotalPixels', 'inputs': {'image': ['4', 0], 'megapixels': 1.0}}}
    pair = stitched(graph, 'them.png', 'you.png')
    assert pair['5']['inputs']['image'] == ['7', 0]
    assert pair['6'] == {'class_type': 'LoadImage', 'inputs': {'image': 'you.png'}}
    assert pair['7']['class_type'] == 'ImageStitch' and pair['7']['inputs']['image1'] == ['4', 0] and \
        pair['7']['inputs']['image2'] == ['6', 0]


def test_openrouter_gets_every_picture_to_follow():
    request = ImageRequest('j', 'p', '', 1, 1024, 1024, {}, {}, reference=COMPANION, others=[YOU])
    body = openrouter_body({'model': 'm'}, 'p', request)
    assert len(body['input_references']) == 2
