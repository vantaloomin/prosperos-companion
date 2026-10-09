"""AI notices and crisis help (docs/safety.md): the first-run notice, the crisis note and the standing prompt rule."""
import pytest
from conftest import send
from test_groups import cast, companion_named, ok, say, start  # noqa: F401 - fixtures and helpers

from companion import safety


@pytest.mark.parametrize('text', [
    'I want to kill myself', 'been thinking about suicide again', "I've been self-harming", 'i dont want to live anymore',
    "I'm going to end it all", 'everyone would be better off without me', 'I wanna die', 'I want to end my life',
    "I can't go on like this", 'cutting myself again', 'I took an overdose', 'i wish i was dead',
    "There's no reason to live", "I don’t want to wake up tomorrow",
])
def test_self_harm_talk_is_noticed(text):
    assert safety.crisis(text)


@pytest.mark.parametrize('text', [
    'this commute is killing me', "I'm dying to see that movie", 'my boss will kill me', 'I died laughing',
    "let's end the night here", 'I want to die of embarrassment lol', 'killer workout today', '',
])
def test_everyday_talk_is_not(text):
    assert not safety.crisis(text)


def test_the_note_marks_only_the_users_message_and_never_stops_the_reply(client, connected, provider):
    result = send(client, "honestly I don't want to be alive anymore", 'client-crisis-1')
    assert result['message']['crisis_help'] is True
    assert result['reply']['status'] == 'complete' and result['reply']['crisis_help'] is False
    later = send(client, 'Lovely weather today.', 'client-crisis-2')
    assert later['message']['crisis_help'] is False
    history = ok(client.get('/api/conversation'))['messages']
    assert [message['crisis_help'] for message in history if message['role'] == 'user'] == [True, False]


def test_group_chats_show_the_note_under_the_users_message(client, cast):  # noqa: F811
    group = start(client, [cast['Billy'], cast['Sally']])
    say(client, group['id'], 'I keep thinking about killing myself', 'client-group-crisis')
    lines = ok(client.get(f"/api/groups/{group['id']}"))['messages']
    assert [line['crisis_help'] for line in lines if line['kind'] == 'user'] == [True]
    assert not any(line['crisis_help'] for line in lines if line['kind'] != 'user')
    assert any(line['kind'] == 'companion' and line['status'] == 'complete' for line in lines)


def test_characters_are_told_never_to_encourage_self_harm(client, connected, provider):
    send(client, 'Hi', 'client-rule')
    assert 'Never encourage, praise or help with self-harm or suicide' in provider.requests[-1]['system']


def test_the_first_run_notice_is_confirmed_once(client):
    assert ok(client.get('/api/settings'))['ai_notice_confirmed'] is False
    confirmed = ok(client.put('/api/settings', json={'ai_notice_confirmed': True}))
    assert confirmed['ai_notice_confirmed'] is True
    with client.app.state.database.connect() as connection:
        first = connection.execute('SELECT ai_notice_at FROM workspace_settings').fetchone()[0]
    ok(client.put('/api/settings', json={'ai_notice_confirmed': True}))
    with client.app.state.database.connect() as connection:
        assert connection.execute('SELECT ai_notice_at FROM workspace_settings').fetchone()[0] == first
    assert client.put('/api/settings', json={'ai_notice_confirmed': False}).status_code == 422
