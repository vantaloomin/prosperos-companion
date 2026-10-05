"""Texting style and pacing: bursts, lowercase, the odd *correction, and replies held while busy."""
from datetime import timedelta

import pytest
from conftest import send, set_life

from companion import texting
from companion.clock import parse
from companion.life import pacing
from companion.providers.chat import Chunk

OFFICE = [{'key': 'work', 'label': 'Office', 'kind': 'work', 'start': '09:00', 'end': '17:00'},
          {'key': 'evening', 'label': 'Evening', 'kind': 'leisure', 'start': '17:00', 'end': '23:00'},
          {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]


def says(provider, text):
    provider.replies.append([Chunk(text), Chunk('', 'stop')])


@pytest.fixture
def office(client, provider):
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC', 'schedule': OFFICE,
                                                     'texting': {'bursts': True, 'lowercase': True}})
    assert response.status_code == 200, response.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    return response.json()


def test_lowercase_keeps_links_and_typos_are_corrected():
    assert texting.lowercase('Saw THEO at https://Example.com/A today') == 'saw theo at https://Example.com/A today'
    changed = [texting.typo('I absolutely loved the restaurant tonight', f'seed-{index}') for index in range(200)]
    fixed = [text for text in changed if '\n\n*' in text]
    assert 5 < len(fixed) < 60
    for text in fixed:
        wrong, correction = text.split('\n\n*')
        assert correction in 'I absolutely loved the restaurant tonight' and correction not in wrong


def test_the_style_reaches_the_model_and_the_saved_reply(client, office, provider, clock):
    clock.instant = clock.now().replace(hour=19)
    says(provider, 'Hey! That sounds GREAT.\n\nTell me more about Theo.')
    reply = send(client, 'Guess what happened', 'client-text-01')['reply']
    assert reply['text'] == 'hey! that sounds great.\n\ntell me more about theo.'
    assert 'How you text: send several short texts' in provider.requests[-1]['system']
    assert reply['held_until'] is None


def test_a_reply_at_work_waits_with_a_holding_line(client, office, provider, clock):
    set_life(client, paced_replies=True)
    clock.instant = clock.now().replace(hour=10)
    says(provider, 'Okay so here is my full answer.')
    reply = send(client, 'Quick question', 'client-text-02')['reply']
    assert reply['text'] == 'okay so here is my full answer.'
    waits = parse(reply['held_until']) - clock.now()
    assert reply['held_line'] in pacing.HOLDING and timedelta(minutes=8) <= waits <= timedelta(minutes=45)
    shown = client.post(f"/api/conversation/messages/{reply['id']}/show").json()
    assert shown['held_until'] <= client.app.state.database.now()


def test_asleep_it_waits_until_morning_and_another_message_shows_it(client, office, provider, clock):
    set_life(client, paced_replies=True)
    clock.instant = clock.now().replace(hour=2)
    says(provider, 'mm, sleepy reply')
    reply = send(client, 'You up?', 'client-text-03')['reply']
    assert reply['held_line'] is None and reply['held_until'].startswith(clock.now().date().isoformat() + 'T07:00')
    says(provider, 'okay now I am up')
    send(client, 'Hello??', 'client-text-04')
    messages = client.get('/api/conversation').json()['messages']
    first = next(message for message in messages if message['id'] == reply['id'])
    assert first['held_until'] <= client.app.state.database.now()


def test_a_held_reply_is_announced_when_it_shows(client, office, provider, clock):
    set_life(client, paced_replies=True)
    client.put('/api/notifications/settings', json={'enabled': True, 'preview': 'full', 'quiet_start': '00:00',
                                                    'quiet_end': '00:00'})
    clock.instant = clock.now().replace(hour=10)
    says(provider, 'Sorry, here now.')
    send(client, 'Ping', 'client-text-05')
    assert client.post('/api/notifications/next', json={'focused': False}).json()['notification'] is None
    clock.advance(timedelta(hours=1))
    shown = client.post('/api/notifications/next', json={'focused': False}).json()['notification']
    assert shown['kind'] == 'message' and shown['body'] == 'sorry, here now.'
    assert client.post('/api/notifications/next', json={'focused': False}).json()['notification'] is None


def test_unpaced_replies_never_wait(client, office, provider, clock):
    clock.instant = clock.now().replace(hour=10)
    says(provider, 'right here')
    assert send(client, 'Hi', 'client-text-06')['reply']['held_until'] is None
