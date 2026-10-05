"""Texting style and pacing: bursts, lowercase, the odd *correction, and replies at the companion's pace."""
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
def office(client, provider, monkeypatch):
    monkeypatch.setattr(pacing, 'ACTIVE', True)
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC', 'schedule': OFFICE,
                                                     'texting': {'bursts': True, 'lowercase': True}})
    assert response.status_code == 200, response.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    return response.json()


def way(monkeypatch, name):
    monkeypatch.setattr(pacing, 'WAYS', ((name, 1),))


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


def test_at_work_a_reply_can_come_later_with_a_holding_text(client, office, provider, clock, monkeypatch):
    way(monkeypatch, 'line')
    clock.instant = clock.now().replace(hour=10)
    says(provider, 'Okay so here is my full answer.')
    reply = send(client, 'Quick question', 'client-text-02')['reply']
    assert reply['text'] == 'okay so here is my full answer.'
    waits = parse(reply['held_until']) - clock.now()
    assert reply['held_line'] in pacing.LINES['work'] and timedelta(minutes=8) <= waits <= timedelta(minutes=45)


def test_at_work_a_reply_can_be_a_quick_note_now(client, office, provider, clock, monkeypatch):
    way(monkeypatch, 'quick')
    clock.instant = clock.now().replace(hour=10)
    says(provider, 'busy, tell you later!')
    reply = send(client, 'How is your day?', 'client-text-03')['reply']
    assert reply['held_until'] is None and 'Reply with a quick short note' in provider.requests[-1]['system']
    assert 'office' in provider.requests[-1]['system']


def test_asleep_it_waits_until_morning_and_later_replies_keep_their_order(client, office, provider, clock, monkeypatch):
    clock.instant = clock.now().replace(hour=2)
    says(provider, 'mm, sleepy reply')
    first = send(client, 'You up?', 'client-text-04')['reply']
    assert first['held_line'] is None and first['held_until'].startswith(clock.now().date().isoformat() + 'T07:00')
    clock.advance(timedelta(hours=8))
    way(monkeypatch, 'later')
    says(provider, 'morning!')
    second = send(client, 'Hello??', 'client-text-05')['reply']
    assert second['held_until'] >= first['held_until']
    clock.advance(timedelta(hours=9))
    says(provider, 'free now')
    assert send(client, 'Evening', 'client-text-06')['reply']['held_until'] is None


def test_a_reply_shown_at_once_shows_earlier_held_ones(client, office, provider, clock, monkeypatch):
    way(monkeypatch, 'later')
    clock.instant = clock.now().replace(hour=16, minute=50)
    says(provider, 'at work reply')
    held = send(client, 'Ping', 'client-text-07')['reply']
    assert parse(held['held_until']) > clock.now()
    clock.instant = clock.now().replace(hour=16, minute=55)
    set_life(client, paced_replies=False)
    says(provider, 'here')
    send(client, 'Ping again', 'client-text-08')
    messages = client.get('/api/conversation').json()['messages']
    first = next(message for message in messages if message['id'] == held['id'])
    assert parse(first['held_until']) <= clock.now()


def test_a_held_reply_is_announced_when_it_shows(client, office, provider, clock, monkeypatch):
    way(monkeypatch, 'later')
    client.put('/api/notifications/settings', json={'enabled': True, 'preview': 'full', 'quiet_start': '00:00',
                                                    'quiet_end': '00:00'})
    clock.instant = clock.now().replace(hour=10)
    says(provider, 'Sorry, here now.')
    send(client, 'Ping', 'client-text-09')
    assert client.post('/api/notifications/next', json={'focused': False}).json()['notification'] is None
    clock.advance(timedelta(hours=1))
    shown = client.post('/api/notifications/next', json={'focused': False}).json()['notification']
    assert shown['kind'] == 'message' and shown['body'] == 'sorry, here now.'
    assert client.post('/api/notifications/next', json={'focused': False}).json()['notification'] is None


def test_paced_replies_are_on_by_default_and_can_be_turned_off(client, office, provider, clock):
    assert client.get('/api/life/settings').json()['paced_replies'] is True
    set_life(client, paced_replies=False)
    clock.instant = clock.now().replace(hour=10)
    says(provider, 'right here')
    assert send(client, 'Hi', 'client-text-10')['reply']['held_until'] is None
