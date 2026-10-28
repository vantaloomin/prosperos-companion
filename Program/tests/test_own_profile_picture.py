# ruff: noqa: F811 - the image test fixtures are reused by name.
"""The user's own picture as the profile picture, and pictures of the companion that follow it."""
from companion.images import sheet
from tests.test_images import add_backend, drain, generate, make_post, ok, png
from tests.test_lora import adapters, app, client  # noqa: F401
from tests.test_portraits import plan, wait_portraits

OWN = png(800, 1200)


def upload(client, data=OWN, name='me.png'):
    return client.post('/api/lora/portrait/upload', params={'name': name}, content=data)


def test_your_own_picture_becomes_the_profile_picture_and_joins_the_references(client, companion):
    first = ok(upload(client))
    assert ok(client.get('/api/companion'))['companion']['portrait_reference_id'] == first['portrait_reference_id']
    listed = ok(client.get('/api/lora/references'))['references']
    assert [item['original_name'] for item in listed] == ['me.png']
    # The same picture again is reused, not refused as a copy.
    assert ok(upload(client))['portrait_reference_id'] == first['portrait_reference_id']
    assert len(ok(client.get('/api/lora/references'))['references']) == 1
    assert upload(client, b'not a picture').status_code == 422


def test_pictures_of_them_follow_the_profile_picture_where_a_backend_takes_one(client, companion, clock, adapters):
    add_backend(client, kind='hosted', provider='openrouter', api_key='k', model='google/gemini-image')
    ok(upload(client))
    first = generate(client, make_post(client, clock))
    drain(client)
    sent = adapters['hosted'].requests[0]
    assert sent.reference == OWN and sent.prompt.endswith(sheet.FOLLOW_PROFILE)
    job = ok(client.get(f"/api/images/jobs/{first['id']}"))
    assert job['identity_method'] == 'text description and their profile picture'
    # The stored request stays the plain one, so a retry elsewhere starts clean.
    assert sheet.FOLLOW_PROFILE not in job['prompt']

    ok(client.put('/api/images/settings', json={'follow_profile_picture': False}))
    assert ok(client.get('/api/images/settings'))['follow_profile_picture'] is False
    generate(client, make_post(client, clock, key='event-0002'))
    drain(client)
    assert adapters['hosted'].requests[1].reference is None


def test_a_backend_without_references_or_a_companion_without_a_picture_sends_none(client, companion, clock, adapters):
    add_backend(client, kind='hosted', provider='google', api_key='k', model='imagen-4')
    ok(upload(client))
    generate(client, make_post(client, clock))
    drain(client)
    assert adapters['hosted'].requests[0].reference is None
    ok(client.put('/api/lora/portrait', json={'reference_id': None}))
    assert sheet.profile_reference(client.app.state.database, companion['active_version_id']) is None


def test_the_other_profile_pictures_are_made_from_your_own(client, companion, adapters):
    add_backend(client, kind='hosted', provider='openrouter', api_key='k', model='google/gemini-image')
    draft = ok(client.get('/api/lora/portraits/draft'))
    refused = client.post('/api/lora/portraits', json=plan(draft, own_picture=True))
    assert refused.status_code == 409 and 'Choose a picture' in str(refused.json())

    ok(upload(client))
    preview = ok(client.post('/api/lora/portraits/preview', json=plan(draft, own_picture=True)))['shots']
    assert preview[0]['own'] == 'own' and preview[0]['backend'] is None and preview[0]['refusal'] is None
    assert [shot['follows'] for shot in preview] == [None, 0, 0]
    adapters['hosted'].outcomes = [png(1024, 1536), png(1024, 1024)]
    ok(client.post('/api/lora/portraits', json=plan(draft, own_picture=True)))
    done = wait_portraits(client)
    assert [image['status'] for image in done['images']] == ['completed'] * 3
    assert done['images'][0]['label'] == 'Your picture' and done['images'][0]['decision'] == 'kept'
    assert [request.reference for request in adapters['hosted'].requests] == [OWN, OWN]

    adapters['hosted'].outcomes = [png(1000, 1500)]
    ok(client.post(f"/api/lora/portraits/{done['id']}/redo", params={'position': 1}))
    again = wait_portraits(client)
    assert again['images'][1]['status'] == 'completed' and adapters['hosted'].requests[2].reference == OWN
