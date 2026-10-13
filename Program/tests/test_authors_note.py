"""Author's note: one note per chat, sent last before the user's words with every reply while it is on, and never part
of the story (companion/authors_note.py)."""
import json

import pytest
from conftest import send
from test_groups import cast, say, start  # noqa: F401 - the cast fixture
from test_sidecar import answers, ask

from companion import authors_note
from companion.memory import context

NOTE = "Mira's exhausted from the commute. Keep it short tonight."


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def put(client, chat, text, enabled=True):
    return ok(client.put(f'/api/authors-notes/{chat}', json={'text': text, 'enabled': enabled}))


def test_a_chat_starts_with_an_empty_note_that_is_on(client, companion):
    chat = f"companion:{companion['id']}"
    assert ok(client.get(f'/api/authors-notes/{chat}')) == {'chat': chat, 'text': '', 'enabled': True,
                                                            'updated_at': None}
    saved = put(client, chat, f'{NOTE} ', enabled=False)
    assert saved['text'] == f'{NOTE} ' and saved['enabled'] is False and saved['updated_at']
    assert ok(client.get(f'/api/authors-notes/{chat}'))['text'] == f'{NOTE} '
    assert put(client, chat, '   ')['text'] == ''


def test_only_real_chats_take_a_note_and_it_stays_short(client, companion):
    assert client.get('/api/authors-notes/companion:nobody').status_code == 404
    assert client.get('/api/authors-notes/somewhere').status_code == 404
    assert client.put('/api/authors-notes/group:gone', json={'text': 'x'}).status_code == 404
    assert ok(client.get('/api/authors-notes/story'))['text'] == ''
    too_long = client.put(f"/api/authors-notes/companion:{companion['id']}",
                          json={'text': 'x' * (authors_note.LIMIT + 1)})
    assert too_long.status_code == 422


def test_the_note_is_the_last_thing_before_the_users_words(client, connected, provider):
    put(client, f'companion:{current(client)}', NOTE)
    send(client, 'Want takeout later?', 'note-client-01')
    latest = provider.requests[-1]['messages'][-1]['content']
    header = authors_note.HEADER
    assert latest.index('[Notes from the app') < latest.index(header) < latest.index(NOTE)
    assert latest.endswith(f"{NOTE}\n[End of notes. The user's message:]\nWant takeout later?")
    # Not in the system prompt, so the cached part of the prompt is untouched.
    assert NOTE not in provider.requests[-1]['system']
    # Never a message: the transcript holds only what was said.
    history = ok(client.get('/api/conversation'))['messages']
    assert all(NOTE not in message['text'] for message in history)


def current(client) -> str:
    return ok(client.get('/api/companion'))['companion']['id']


def test_switched_off_or_out_of_character_the_note_stays_out(client, connected, provider):
    chat = f'companion:{current(client)}'
    put(client, chat, NOTE, enabled=False)
    send(client, 'Hi there.', 'note-client-02')
    assert NOTE not in provider.requests[-1]['messages'][-1]['content']
    put(client, chat, NOTE)
    send(client, 'OOC: which model are you?', 'note-client-03')
    assert NOTE not in provider.requests[-1]['messages'][-1]['content']
    send(client, 'Hi again.', 'note-client-04')
    assert NOTE in provider.requests[-1]['messages'][-1]['content']


def test_later_notes_still_come_before_the_authors_note():
    packet = {'note': 'Right now: noon', 'history': [{'role': 'user', 'content': 'Hello'}]}
    packet = context.steer(packet, 'STEER')
    packet = context.add_note(packet, 'A reminder')
    content = packet['messages'][-1]['content']
    assert content.index('Right now') < content.index('A reminder') < content.index('STEER') < content.index('Hello')


def test_a_group_chat_has_its_own_note(client, cast, provider):  # noqa: F811
    group = start(client, [cast['Mira'], cast['Billy']])
    put(client, f"group:{group['id']}", 'Keep the banter going.')
    put(client, f"companion:{cast['Mira']}", NOTE)
    say(client, group['id'], 'What are we doing Friday?', 'group-note-01')
    replies = [request for request in provider.requests if "'s next message" in request['messages'][-1]['content']]
    assert replies
    for request in replies:
        content = request['messages'][-1]['content']
        assert 'Keep the banter going.' in content and NOTE not in content
        assert content.index('Keep the banter going.') < content.index("'s next message")


@pytest.mark.parametrize('enabled', [True, False])
def test_the_story_narrator_reads_the_story_note(client, connected, provider, enabled):
    assert ok(client.put('/api/settings', json={'story_mode': True}))['story_mode'] is True
    put(client, 'story', 'Make it rain all evening.', enabled=enabled)
    ok(client.post('/api/story/messages', json={'text': 'I step outside.', 'client_id': 'story-note-1'}))
    latest = provider.requests[-1]['messages'][-1]['content']
    assert ('Make it rain all evening.' in latest) is enabled
    assert latest.endswith('I step outside.')


def test_the_sidecar_can_propose_a_note(client, connected, provider):
    chat = f'companion:{current(client)}'
    put(client, chat, 'Old note.', enabled=False)
    answers(provider, json.dumps({'reply': 'Here is a note for tonight.', 'changes': [
        {'kind': 'authors_note', 'text': NOTE}]}))
    result = ask(client, 'She should be tired tonight.', view='conversation')
    assert result['changes'] == [{'kind': 'authors_note', 'chat': chat, 'before': 'Old note.', 'enabled': False,
                                  'text': NOTE}]
    assert '(written but switched off) Old note.' in provider.requests[-1]['system']
