"""Photos in chat: a photo of the companion's current moment, shared with the feed (realism ideas)."""
import asyncio
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from companion.identity import CLIENT_HEADER
from companion.images import memes
from companion.images.photos import asked_kind, asks_for_photo
from companion.main import create_app
from companion.providers.vault import MemoryVault
from tests.conftest import reconcile, send, set_life
from tests.test_images import FakeAdapter, add_backend, local_comfy


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


def drain(client):
    asyncio.run(client.app.state.images.drain())


def ask(client, text='what are you up to?', client_id='ask-0001'):
    return send(client, text, client_id)['reply']


def photo_section(provider) -> str:
    system = provider.requests[-1]['prompt']
    return system.split('## A picture you are sending', 1)[1].split('##', 1)[0] if \
        '## A picture you are sending' in system else ''


def set_appearance(client, appearance):
    current = client.get('/api/companion').json()['companion']
    definition = {**current['version']['definition'], 'appearance': appearance}
    response = client.post('/api/companion/versions', json={'definition': definition,
                                                            'expected_version_id': current['active_version_id']})
    assert response.status_code == 200, response.text


@pytest.mark.parametrize('text', ["What are you up to?", 'whatcha doing', 'wyd', "what're you doing right now",
                                  'send me a pic!', 'Show me a selfie', 'where are you right now?',
                                  'pics or it didn\'t happen'])
def test_asking_what_they_are_up_to_asks_for_a_photo(text):
    assert asks_for_photo(text)


@pytest.mark.parametrize('text', ['What are you doing tomorrow?', 'what have you been up to', 'Where are you from?',
                                  'I sent a picture to my mum', 'Good morning!', 'What are you up to tonight?'])
def test_other_questions_do_not(text):
    assert not asks_for_photo(text)


def test_the_pictured_moment_is_the_one_the_agenda_holds(client, life, app):
    """A photo composes the slot from the agenda, so the event written later (a birthday outing
    with a friend, say) is the same moment the picture shows."""
    local_comfy(client)
    photo = ask(client)['photo']
    with app.state.database.connect() as connection:
        rows = connection.execute("SELECT entry FROM life_agenda WHERE subject='companion' AND entry IS NOT NULL "
                                  'AND starts_at<=? AND ends_at>?', (app.state.database.now(),) * 2).fetchall()
    assert rows and photo['summary']


def test_a_photo_of_the_current_moment_becomes_the_feed_image(client, life, clock, provider, adapters, monkeypatch):
    # A cold seeded by the companion's random id would turn the pictured moment into a sick day.
    monkeypatch.setattr('companion.life.body.COLD_CHANCE', {'winter': 0, 'other': 0})
    local_comfy(client)
    reply = ask(client)
    photo = reply['photo']
    assert photo['status'] == 'queued' and photo['in_feed'] is False
    # The reply knew what it was sending.
    assert photo['summary'] in photo_section(provider)
    drain(client)
    shown = client.get(f"/api/images/photos/{reply['id']}").json()
    assert shown['status'] == 'completed' and shown['ref']
    assert len(adapters['comfyui'].requests) == 1
    # Not in the feed until the moment is an event. (A seeded status post can land on this very minute.)
    assert [post for post in client.get('/api/feed').json()['posts'] if post['source'] != 'social'] == []
    # Asking again in the same moment shows the same photo, without making another.
    again = ask(client, 'wyd', 'ask-0002')['photo']
    assert again['post_id'] == photo['post_id'] and again['ref'] == shown['ref']
    assert len(adapters['comfyui'].requests) == 1

    set_life(client, automatic_events=True)
    clock.advance(timedelta(days=1))
    reconcile(client)
    posts = client.get('/api/feed').json()['posts']
    pictured = [post for post in posts if post['id'] == photo['post_id']]
    assert pictured and pictured[0]['image']['ref'] == shown['ref']
    # The same moment; only a model's later rephrasing can change its words.
    assert photo['summary'] in pictured[0]['events'][0]['summary']
    # The event is told once: the digest leaves it to the photo's post.
    event_id = pictured[0]['events'][0]['id']
    assert all(event['id'] != event_id for post in posts if post['id'] != photo['post_id'] for event in post['events'])
    assert client.get(f"/api/images/photos/{reply['id']}").json()['in_feed'] is True
    history = client.get('/api/conversation').json()['messages']
    assert next(message for message in history if message['id'] == reply['id'])['photo']['ref'] == shown['ref']


def test_no_backend_means_no_photo_and_no_promise(client, life, provider):
    reply = ask(client)
    assert reply['status'] == 'complete' and reply['photo'] is None
    assert photo_section(provider) == ''


def test_other_messages_and_other_times_send_no_photo(client, life, provider):
    local_comfy(client)
    assert ask(client, 'Good morning!')['photo'] is None
    assert ask(client, 'What are you doing tomorrow?', 'ask-0002')['photo'] is None


def test_chat_photos_can_be_turned_off(client, life):
    local_comfy(client)
    assert client.put('/api/images/settings', json={'chat_photos': False}).json()['chat_photos'] is False
    assert ask(client)['photo'] is None


def test_paused_life_sends_no_photo(client, life):
    local_comfy(client)
    client.post('/api/pause')
    assert ask(client)['photo'] is None


def test_an_nsfw_moment_goes_to_a_local_backend_only(client, life, adapters):
    set_appearance(client, 'Tall, in lingerie')
    add_backend(client, kind='hosted', provider='google', base_url='https://example.test/v1', model='image',
                api_key='key')
    assert ask(client)['photo'] is None
    assert adapters['hosted'].requests == []
    local_comfy(client)
    photo = ask(client, 'send me a pic', 'ask-0002')['photo']
    drain(client)
    assert adapters['comfyui'].requests and adapters['hosted'].requests == []
    job = client.get(f"/api/images/jobs?post_id={photo['post_id']}").json()['jobs'][0]
    assert job['classification'] == 'nsfw' and job['backend_kind'] == 'comfyui'


def test_a_prohibited_moment_is_refused_everywhere(client, life, adapters):
    set_appearance(client, 'A nude teen')
    local_comfy(client)
    assert ask(client)['photo'] is None
    drain(client)
    assert adapters['comfyui'].requests == []


def test_a_fork_keeps_the_photo_on_the_copied_reply(client, life):
    local_comfy(client)
    reply = ask(client)
    drain(client)
    later = send(client, 'Lovely.', 'later-0001')['message']
    fork = client.post('/api/timelines', json={'message_id': later['id'], 'text': 'Nice!'})
    assert fork.status_code == 200, fork.text
    activated = client.post(f"/api/timelines/{fork.json()['id']}/activate")
    assert activated.status_code == 200, activated.text
    history = client.get('/api/conversation').json()['messages']
    copied = next(message for message in history if message['role'] == 'companion' and message['photo'])
    assert copied['id'] != reply['id'] and copied['photo']['status'] == 'completed'


@pytest.mark.parametrize(('text', 'kind'), [
    ('send me a selfie', 'selfie'), ('can I see your face?', 'selfie'), ('pic of you rn?', 'selfie'),
    ('send me a pic of the view', 'view'), ("show me what you're seeing", 'view'),
    ('send me a meme', 'meme'), ('got any memes?', 'meme'), ('cheer me up', 'meme'), ('make me laugh', 'meme'),
    ('wyd', 'moment'), ('send me a selfie tomorrow', None)])
def test_which_picture_a_message_asks_for(text, kind):
    assert asked_kind(text) == kind


def jobs_for(client, photo):
    return client.get(f"/api/images/jobs?post_id={photo['post_id']}").json()['jobs']


def test_a_selfie_is_a_new_version_of_the_moment_and_each_reply_keeps_its_own(client, life, adapters):
    local_comfy(client)
    plain = ask(client)
    drain(client)
    selfie = ask(client, 'send me a selfie!', 'ask-0002')
    drain(client)
    assert selfie['photo']['post_id'] == plain['photo']['post_id'] and selfie['photo']['kind'] == 'selfie'
    prompt = adapters['comfyui'].requests[-1].prompt
    assert 'fictional selfie' in prompt.split('.')[0] and 'Mira' not in prompt
    first = client.get(f"/api/images/photos/{plain['id']}").json()
    second = client.get(f"/api/images/photos/{selfie['id']}").json()
    assert first['ref'] and second['ref'] and first['ref'] != second['ref']
    # Asking for a selfie again in the same moment shows the same one.
    again = ask(client, 'another selfie?', 'ask-0003')['photo']
    assert again['job_id'] == second['job_id'] and len(adapters['comfyui'].requests) == 2


def test_a_view_leaves_the_companion_out(client, life, adapters):
    set_appearance(client, 'Freckles and a red scarf')
    local_comfy(client)
    photo = ask(client, 'send me a pic of the view', 'ask-0001')['photo']
    assert photo['kind'] == 'view'
    drain(client)
    assert 'red scarf' not in adapters['comfyui'].requests[-1].prompt


def test_a_meme_is_a_joke_that_never_reaches_the_feed(client, life, clock, provider, adapters):
    local_comfy(client)
    reply = ask(client, 'send me a meme', 'ask-0001')
    photo = reply['photo']
    assert photo['kind'] == 'meme' and photo['top_text'] and photo['bottom_text']
    assert photo['top_text'] in photo_section(provider)
    drain(client)
    assert client.get(f"/api/images/photos/{reply['id']}").json()['status'] == 'completed'
    request = adapters['comfyui'].requests[-1]
    assert photo['top_text'] not in request.prompt  # Captions are drawn by the interface.
    set_life(client, automatic_events=True)
    clock.advance(timedelta(days=1))
    reconcile(client)
    assert all(post['id'] != photo['post_id'] for post in client.get('/api/feed').json()['posts'])
    # Another meme is a new one, not a repeat.
    other = ask(client, 'another meme pls', 'ask-0002')['photo']
    assert other['post_id'] != photo['post_id'] and other['top_text'] != photo['top_text']


def test_memes_are_classified_like_any_picture(client, life, adapters):
    set_appearance(client, 'Tall, in lingerie')
    add_backend(client, kind='hosted', provider='google', base_url='https://example.test/v1', model='image',
                api_key='key')
    reply = ask(client, 'send me a meme', 'ask-0001')
    # Either a scene meme with no likeness, safe for the hosted backend, or none at all: never NSFW to Google.
    drain(client)
    for request in adapters['hosted'].requests:
        assert 'lingerie' not in request.prompt
    if reply['photo']:
        assert reply['photo']['kind'] == 'meme'


def test_meme_templates_fit_the_day_and_vary():
    work = {'kind': 'work', 'label': 'Work', 'place': 'the office', 'rain': False}
    chosen = {memes.choose(work, 14, f'seed-{index}')['top'] for index in range(30)}
    assert len(chosen) > 3
    assert memes.choose(None, 3, 'x')['top']
    recent = [template.top for template in memes.SITUATIONS['work'] + memes.ANYTIME]
    assert memes.choose(work, 14, 'y', recent)['top']


@pytest.fixture
def unasked(monkeypatch):
    """Unasked pictures on, with every chance certain so the rules around them are what is tested."""
    from companion.images import photos
    monkeypatch.setattr(photos, 'UNASKED', True)
    monkeypatch.setattr(photos, 'UNASKED_CHANCE', 1)
    monkeypatch.setattr(photos, 'UNASKED_MEME_CHANCE', 1)
    monkeypatch.setattr(photos, 'UNASKED_SELFIE_SHARE', 0)
    monkeypatch.setattr(photos, 'SHARE_CHANCE', 1)
    monkeypatch.setattr(photos, 'SHARE_SELFIE_SHARE', 0)
    monkeypatch.setattr(photos, 'SHARE_KINDS', {'work', 'study', 'errand', 'social', 'leisure'})
    # A cold turns the slot into rest at home, which is never shared; the companion's seed decides it.
    monkeypatch.setattr('companion.life.body.COLD_CHANCE', {'winter': 0, 'other': 0})
    return photos


def test_a_reply_can_come_with_a_photo_nobody_asked_for(client, life, clock, provider, unasked):
    local_comfy(client)
    reply = ask(client, 'Just got home.', 'say-0001')
    photo = reply['photo']
    assert photo['unasked'] is True and photo['kind'] == 'moment'
    assert 'the user did not ask for it' in photo_section(provider)
    # Not again so soon, and never the same moment twice unasked.
    assert ask(client, 'Nice.', 'say-0002')['photo'] is None
    clock.advance(unasked.UNASKED_GAP)
    later = ask(client, 'Back again.', 'say-0003')['photo']
    assert later is None or later['post_id'] != photo['post_id']
    # Asking still works whatever the unasked limits say.
    assert ask(client, 'wyd', 'ask-0004')['photo'] is not None


def test_unasked_pictures_stop_at_the_daily_limit(client, life, clock, unasked, monkeypatch):
    monkeypatch.setattr(unasked, 'UNASKED_GAP', timedelta(0))
    local_comfy(client)
    sent = [ask(client, 'hmm.', f'say-{index:04}')['photo'] for index in range(8)]
    # One per moment, at most three a day.
    assert 0 < len([photo for photo in sent if photo]) <= unasked.UNASKED_DAILY


def test_sounding_down_can_get_a_meme(client, life, provider, unasked):
    local_comfy(client)
    photo = ask(client, 'ugh, such a rough day', 'say-0001')['photo']
    assert photo['kind'] == 'meme' and photo['unasked'] is True
    assert 'unasked, to cheer them up' in photo_section(provider)


def test_unasked_pictures_can_be_turned_off(client, life, unasked):
    local_comfy(client)
    client.put('/api/images/settings', json={'unprompted_photos': False})
    assert ask(client, 'Just got home.', 'say-0001')['photo'] is None
    assert ask(client, 'wyd', 'ask-0002')['photo'] is not None


def test_no_chance_means_no_unasked_picture(client, life, unasked, monkeypatch):
    monkeypatch.setattr(unasked, 'UNASKED_CHANCE', 0)
    local_comfy(client)
    assert ask(client, 'Just got home.', 'say-0001')['photo'] is None


def share(client):
    return client.app.state.conversation.photos.share()


def test_a_photo_text_waits_until_they_may_text_first(client, life, unasked):
    local_comfy(client)
    set_life(client, texts_first=False)
    assert share(client) is None
    set_life(client, texts_first=True)
    sent = share(client)
    assert sent and sent['role'] == 'companion' and sent['reply_to'] is None
    assert sent['photo']['unasked'] is True and sent['text']
    history = client.get('/api/conversation').json()['messages']
    assert next(message for message in history if message['id'] == sent['id'])['photo']['post_id'] == \
        sent['photo']['post_id']
    # Once a day, and never twice without an answer.
    assert share(client) is None


def test_photo_texts_count_as_first_messages(client, life, unasked):
    local_comfy(client)
    set_life(client, texts_first=True)
    sent = share(client)
    with client.app.state.database.connect() as connection:
        opener = connection.execute('SELECT kind, wording FROM openers WHERE message_id=?', (sent['id'],)).fetchone()
    assert tuple(opener) == ('photo', 'template')


def test_no_photo_text_without_a_backend_or_with_unasked_pictures_off(client, life, unasked):
    set_life(client, texts_first=True)
    assert share(client) is None
    local_comfy(client)
    client.put('/api/images/settings', json={'unprompted_photos': False})
    assert share(client) is None
    assert client.get('/api/conversation').json()['messages'] == []


def test_a_photo_that_failed_can_be_tried_again_from_the_chat(client, life, adapters, monkeypatch):
    """A failed or timed-out photo says so with a reason, and Retry makes it again in the same place."""
    monkeypatch.setattr('companion.life.body.COLD_CHANCE', {'winter': 0, 'other': 0})
    from companion.images.adapters.base import AdapterError
    local_comfy(client)
    adapters['comfyui'].outcomes = [AdapterError('timeout', 'The provider did not answer within the time limit.')]
    reply = ask(client)
    drain(client)
    failed = client.get(f"/api/images/photos/{reply['id']}").json()
    assert failed['status'] == 'failed' and 'time limit' in failed['error']
    retried = client.post(f"/api/images/photos/{reply['id']}/retry")
    assert retried.status_code == 200, retried.text
    assert retried.json()['status'] == 'queued' and retried.json()['job_id'] != failed['job_id']
    drain(client)
    shown = client.get(f"/api/images/photos/{reply['id']}").json()
    assert shown['status'] == 'completed' and shown['ref'] == shown['job_id']
    history = client.get('/api/conversation').json()['messages']
    assert next(message for message in history if message['id'] == reply['id'])['photo']['ref'] == shown['ref']
    assert client.post(f"/api/images/photos/{reply['id']}/retry").status_code == 409
