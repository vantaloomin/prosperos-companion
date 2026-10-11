# ruff: noqa: F811 - the image test fixtures are reused by name.
"""A character reference sheet made on Codex before any other picture of a companion, which later pictures follow."""
import pytest

from companion.images import sheet
from companion.images.adapters.base import AdapterError
from companion.images.content import SAFE, classify
from tests.test_images import add_backend, drain, generate, make_post, ok, png
from tests.test_lora import adapters, app, client  # noqa: F401
from tests.test_portraits import plan, wait_portraits

SHEET = png(1536, 1024)


@pytest.fixture(autouse=True)
def sheets_on(monkeypatch):
    monkeypatch.setattr('companion.images.sheet.ENABLED', True)


def test_the_first_codex_picture_is_made_after_a_sheet_and_every_later_one_follows_it(client, companion, clock,
                                                                                       adapters):
    add_backend(client, kind='codex')
    adapters['codex'].outcomes = [SHEET, png(1536, 1024), png(1536, 1023)]
    first = generate(client, make_post(client, clock))
    drain(client)
    made, picture = adapters['codex'].requests
    assert 'CHARACTER REFERENCE SHEET' in made.prompt and (made.width, made.height) == (1536, 1024)
    assert sheet.FROM_WORDS in made.prompt and made.reference is None
    assert 'Candid, natural-light photograph' in made.prompt
    assert picture.reference == SHEET and picture.prompt.endswith(sheet.FOLLOW)
    job = ok(client.get(f"/api/images/jobs/{first['id']}"))
    assert job['status'] == 'completed' and job['identity_method'] == 'text description and their character sheet'
    # The stored request stays the plain one, so a retry elsewhere starts clean.
    assert sheet.FOLLOW not in job['prompt']

    generate(client, make_post(client, clock, key='event-0002'))
    drain(client)
    assert len(adapters['codex'].requests) == 3 and adapters['codex'].requests[2].reference == SHEET
    folder = client.app.state.database.path.parent / 'images' / 'sheets'
    assert [path.read_bytes() for path in folder.iterdir()] == [SHEET]


def test_other_backends_and_pictures_without_the_companion_make_no_sheet(client, companion, clock, adapters):
    add_backend(client, kind='hosted', provider='openrouter', api_key='k', model='m')
    generate(client, make_post(client, clock))
    drain(client)
    assert len(adapters['hosted'].requests) == 1 and adapters['hosted'].requests[0].reference is None
    assert not sheet.depicts_companion({'framing': 'view'})
    assert not sheet.depicts_companion({'framing': 'meme', 'meme': {'subject': 'a cat in a box'}})
    assert sheet.depicts_companion({'framing': 'selfie'}) and sheet.depicts_companion({})


def test_a_failed_sheet_still_makes_the_picture_but_a_sign_in_error_stops_codex(client, companion, clock, adapters):
    codex = add_backend(client, kind='codex')
    adapters['codex'].outcomes = [AdapterError('failed', 'Busy'), png(1536, 1024)]
    first = generate(client, make_post(client, clock))
    drain(client)
    assert ok(client.get(f"/api/images/jobs/{first['id']}"))['status'] == 'completed'
    assert adapters['codex'].requests[1].reference is None

    adapters['codex'].outcomes = [AdapterError('auth', 'Run codex login.')]
    second = generate(client, make_post(client, clock, key='event-0002'))
    drain(client)
    assert len(adapters['codex'].requests) == 3
    assert ok(client.get(f"/api/images/jobs/{second['id']}"))['error_code'] == 'auth'
    with client.app.state.database.connect() as connection:
        blocked = connection.execute('SELECT blocked_reason FROM image_backends WHERE id=?', (codex['id'],)).fetchone()
    assert blocked['blocked_reason'] == 'Run codex login.'


def test_new_looks_make_a_new_sheet(client, companion, clock, adapters):
    add_backend(client, kind='codex')
    generate(client, make_post(client, clock))
    drain(client)
    definition = {**companion['version']['definition'], 'appearance': 'Short silver hair and a wide, crooked smile.'}
    ok(client.post('/api/companion/versions', json={'definition': definition, 'note': 'New hair',
                                                    'expected_version_id': companion['active_version_id']}))
    generate(client, make_post(client, clock, key='event-0002'))
    drain(client)
    prompts = [request.prompt for request in adapters['codex'].requests]
    assert len(prompts) == 4 and 'CHARACTER REFERENCE SHEET' in prompts[2] and 'silver hair' in prompts[2]


def test_the_profile_picture_is_made_from_the_sheet_and_later_sheets_follow_it(client, companion, adapters):
    add_backend(client, kind='codex')
    profile = png(1024, 1536)
    adapters['codex'].outcomes = [SHEET, profile, png(1024, 1535), png(1024, 1024)]
    draft = ok(client.get('/api/lora/portraits/draft'))
    ok(client.post('/api/lora/portraits', json=plan(draft)))
    done = wait_portraits(client)
    assert [image['status'] for image in done['images']] == ['completed'] * 3
    made, first, second, third = adapters['codex'].requests
    assert 'CHARACTER REFERENCE SHEET' in made.prompt
    assert first.reference == SHEET and first.prompt.endswith(sheet.FOLLOW)
    assert second.reference == third.reference == profile and sheet.FOLLOW not in second.prompt



def test_a_new_sheet_follows_the_profile_picture(client, companion, clock, adapters):
    add_backend(client, kind='codex')
    profile = png(1024, 1536)
    adapters['codex'].outcomes = [SHEET, profile]
    draft = ok(client.get('/api/lora/portraits/draft'))
    ok(client.post('/api/lora/portraits', json=plan(draft)))
    done = wait_portraits(client)
    kept = ok(client.post(f"/api/lora/generation-images/{done['images'][0]['id']}/keep"))
    reference_id = next(image['reference_id'] for image in kept['images'] if image['reference_id'])
    ok(client.put('/api/lora/portrait', json={'reference_id': reference_id}))
    definition = {**companion['version']['definition'], 'appearance': 'Short silver hair and a wide, crooked smile.'}
    ok(client.post('/api/companion/versions', json={'definition': definition, 'note': 'New hair',
                                                    'expected_version_id': companion['active_version_id']}))
    count = len(adapters['codex'].requests)
    generate(client, make_post(client, clock))
    drain(client)
    made, picture = adapters['codex'].requests[count:]
    assert sheet.FROM_PICTURE in made.prompt and made.reference == profile
    assert picture.reference == png() and picture.prompt.endswith(sheet.FOLLOW)


def test_the_sheet_prompt_is_safe_and_uses_the_profile_picture_when_there_is_one(client, companion):
    prompt = sheet.compose('A tall woman in her early thirties with short dark hair.', None, True)
    assert sheet.FROM_PICTURE in prompt and '1536 × 1024' in prompt and '16K' not in prompt
    assert classify({'prompt': prompt, 'negative': '', 'appearance': ''}).tier == SAFE
