"""Versions of a reply: the one the user pages back to sticks, and Another reply is never held by pacing."""
from datetime import timedelta

import pytest
from conftest import send

from companion.clock import parse
from companion.life import pacing
from companion.providers.chat import Chunk

OFFICE = [{'key': 'work', 'label': 'Office', 'kind': 'work', 'start': '09:00', 'end': '17:00'},
          {'key': 'evening', 'label': 'Evening', 'kind': 'leisure', 'start': '17:00', 'end': '23:00'},
          {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]


def says(provider, *texts):
    provider.replies.extend([[Chunk(text), Chunk('', 'stop')] for text in texts])


@pytest.fixture
def office(client, provider, monkeypatch):
    monkeypatch.setattr(pacing, 'ACTIVE', True)
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC', 'schedule': OFFICE})
    assert response.status_code == 200, response.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    return response.json()


def messages(client) -> dict:
    return {message['id']: message for message in client.get('/api/conversation').json()['messages']}


def again(client, message_id) -> dict:
    response = client.post(f'/api/conversation/messages/{message_id}/alternatives')
    assert response.status_code == 200, response.text
    return response.json()


def test_the_version_paged_back_to_sticks_and_the_next_reply_hears_it(client, connected, provider):
    provider.replies = [[Chunk('First take.')], [Chunk('Second take.')], [Chunk('Glad you liked the first.')]]
    first = send(client, 'Hi', 'client-0001')
    second = again(client, first['message']['id'])
    response = client.post(f"/api/conversation/replies/{first['reply']['id']}/choose")
    assert response.status_code == 200, response.text
    shown = messages(client)
    assert shown[first['reply']['id']]['active'] is True and shown[second['reply']['id']]['active'] is False
    send(client, 'I like that one', 'client-0002')
    sent = [message['content'] for message in provider.requests[-1]['messages']]
    assert 'First take.' in sent and 'Second take.' not in sent
    shown = messages(client)
    assert shown[first['reply']['id']]['active'] is True and shown[second['reply']['id']]['active'] is False


def test_only_a_finished_reply_can_be_chosen(client, connected, provider):
    provider.replies = [[Chunk('Well, I was going to'), Chunk('', 'length')]]
    reply = send(client, 'Tell me a story', 'client-0001')['reply']
    assert client.post(f"/api/conversation/replies/{reply['id']}/choose").status_code == 409


def test_another_reply_while_busy_is_written_now_not_a_holding_text(client, office, provider, clock, monkeypatch):
    monkeypatch.setattr(pacing, 'WAYS', (('line', 1),))
    clock.instant = clock.now().replace(hour=20)
    says(provider, 'Free tonight, so: hi!', 'Another take, still at my desk.')
    first = send(client, 'Hey', 'client-0001')
    assert first['reply']['held_line'] is None
    clock.instant = clock.instant.replace(hour=10) + timedelta(days=1)  # At work now.
    second = again(client, first['message']['id'])
    reply = second['reply']
    assert 'follow_up' not in second and reply['reply_to'] == first['message']['id']
    assert reply['text'] == 'Another take, still at my desk.' and reply['held_until'] is None and reply['active']
    assert 'only sent them a quick text' not in provider.requests[-1]['prompt']


def test_the_full_reply_after_a_holding_text_has_versions(client, office, provider, clock, monkeypatch):
    monkeypatch.setattr(pacing, 'WAYS', (('line', 1),))
    clock.instant = clock.now().replace(hour=10)
    says(provider, 'Okay, my full answer.', 'Okay, a better full answer.')
    result = send(client, 'Quick question', 'client-0001')
    note, full = result['reply'], result['follow_up']
    clock.advance(parse_wait(full, clock))
    version = again(client, full['id'])['reply']
    assert version['reply_to'] is None and version['version_of'] == full['id'] and version['held_until'] is None
    assert version['held_line'] == note['text'] and f'"{note["text"]}"' in provider.requests[-1]['prompt']
    shown = messages(client)
    assert shown[version['id']]['active'] is True and shown[full['id']]['active'] is False
    assert shown[note['id']]['active'] is True  # The holding text stays.
    # Paging back to the first full reply keeps it, and a third version is another version of the same reply.
    assert client.post(f"/api/conversation/replies/{full['id']}/choose").status_code == 200
    shown = messages(client)
    assert shown[full['id']]['active'] is True and shown[version['id']]['active'] is False
    says(provider, 'Third go.')
    third = again(client, version['id'])['reply']
    assert third['version_of'] == full['id']


def test_another_reply_to_a_holding_text_drops_the_promised_reply(client, office, provider, clock, monkeypatch):
    monkeypatch.setattr(pacing, 'WAYS', (('line', 1),))
    clock.instant = clock.now().replace(hour=10)
    says(provider, 'Promised full answer.', 'A real answer right away.')
    result = send(client, 'Quick question', 'client-0001')
    second = again(client, result['message']['id'])
    assert second['dropped'] == [result['follow_up']['id']]
    reply = second['reply']
    assert reply['reply_to'] == result['message']['id'] and reply['held_until'] is None and reply['active']
    assert result['follow_up']['id'] not in messages(client)


def test_only_a_full_reply_after_a_holding_text_has_versions_of_its_own(client, connected, provider):
    reply = send(client, 'Hi', 'client-0001')['reply']
    assert client.post(f"/api/conversation/messages/{reply['id']}/alternatives").status_code == 409


def parse_wait(message, clock):
    return parse(message['held_until']) - clock.now()
