"""On a call (companion/life/calls.py): calls started either way, the call in the chat, and how it ends."""
import asyncio
import time
from datetime import timedelta

import pytest
from conftest import reconcile, send, set_life
from test_openers import check, history
from test_together import mira, notes, says, where
from test_voice_notes import speaker  # noqa: F401 - the fake built-in voice, used as a fixture.

from companion.characters import current
from companion.life import calls, openers, pacing


def test_asking_to_call_is_read_from_the_message():
    for text in ('can I call you?', 'call me?', 'wanna facetime?', "I'm calling you", 'give me a ring!',
                 'can you call me right now? I need to hear your voice'):
        assert calls.asked(text), text
    for text in ('call me tonight after work?', 'my mom called me yesterday', "don't call me", 'how was work?',
                 'can I call you tomorrow?'):
        assert not calls.asked(text), text
    assert calls.hanging_up('ok I gotta go, talk later!') and calls.hanging_up('bye!!')
    assert not calls.hanging_up('so how was your day?')


@pytest.fixture
def nearby(client, monkeypatch):
    mira(client, monkeypatch)


def press(client, path=''):
    response = client.post(f'/api/life/calls{path}')
    assert response.status_code == 200, response.text
    return response.json()


def test_at_work_they_cannot_talk_and_after_work_they_pick_up(client, nearby, provider, clock):
    says(provider)
    send(client, 'can I call you?', 'client-call-1')  # Monday 12:00, at work.
    assert "The user asked to talk on the phone now. You can't: you are at work until 17:00" in notes(provider)
    assert where(client)['state'] == 'apart'
    clock.advance(timedelta(hours=6))  # 18:00.
    says(provider, 'Hey you! Of course, hi.')
    send(client, 'can I call you?', 'client-call-2')
    found = where(client)
    assert (found['state'], found['kind'], found['text']) == ('call', 'call', 'On a call')
    assert found['call']['status'] == 'on' and found['call']['direction'] == 'you'
    assert 'You are on a phone call with the user right now. The user called you at 18:00' in notes(provider)
    assert 'this reply is the first thing you say on the call' in notes(provider)
    status = client.get('/api/chats').json()['chats'][0]['status']
    assert status['where'] == {'state': 'call', 'kind': 'call', 'text': 'On a call'}
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        assert openers.held(connection, companion, {'texts_first': True}, clock.now()) == 'call'
    # Saying goodbye ends it, and the reply to the goodbye is still said on the phone.
    clock.advance(timedelta(minutes=3))
    says(provider)
    send(client, 'okay I gotta go, talk later!', 'client-call-3')
    assert 'The user is saying goodbye to end the call' in notes(provider)
    assert where(client)['state'] == 'apart' and where(client)['call']['status'] == 'ended'
    clock.advance(timedelta(minutes=10))
    says(provider)
    send(client, 'that was nice', 'client-call-4')
    assert 'You and the user talked on the phone for about 3 minutes and hung up a little while ago' in notes(provider)
    assert where(client)['call'] is None


def test_the_call_button_and_end_call(client, nearby, provider, clock):
    clock.advance(timedelta(hours=7))  # 19:00, free.
    found = press(client)
    call_id = found['call']['id']
    assert found['state'] == 'call' and found['call']['until_at']
    assert client.post('/api/life/calls').status_code == 409  # One at a time.
    says(provider)
    send(client, 'hiii', 'client-call-5')
    assert 'The user called you at 19:00' in notes(provider)
    ended = press(client, f'/{call_id}/end')
    assert ended['state'] == 'apart' and ended['call']['status'] == 'ended'


def test_a_call_ends_on_its_own_when_the_line_goes_quiet(client, nearby, clock):
    clock.advance(timedelta(hours=7))
    press(client)
    clock.advance(calls.IDLE + timedelta(minutes=1))
    assert where(client)['state'] == 'apart'


def test_a_call_ends_before_they_have_to_sleep(client, nearby, provider, clock, monkeypatch):
    monkeypatch.setattr(calls, 'HOURS', (3.0, 3.0))
    clock.advance(timedelta(hours=10, minutes=20))  # Monday 22:20; up for work tomorrow, so done by 22:30.
    found = press(client)
    assert found['call']['until_at'].startswith('2026-10-05T22:30')
    clock.advance(timedelta(minutes=6))
    says(provider)
    send(client, 'tell me everything', 'client-call-6')
    assert 'You have to go in a few minutes: start wrapping up the call' in notes(provider)


def test_a_missed_call_from_you_is_texted_back_once_they_are_free(client, nearby, clock, monkeypatch):
    monkeypatch.setattr(calls, 'FIRST_TEXTS', True)
    found = press(client)  # 12:00, at work: no answer.
    assert found['state'] == 'apart' and found['call']['status'] == 'missed'
    with client.app.state.database.connect() as connection:
        assert calls.missed_due(connection, current(connection), clock.now()) == []  # Still at work.
    clock.advance(timedelta(hours=5, minutes=30))  # 17:30.
    with client.app.state.database.connect() as connection:
        [trigger] = calls.missed_due(connection, current(connection), clock.now())
    assert trigger.kind == 'call_back' and 'because you are at work until 17:00' in trigger.reason


def test_they_ring_and_writing_answers(client, nearby, provider, clock, monkeypatch):
    monkeypatch.setattr(calls, 'FIRST_TEXTS', True)
    monkeypatch.setattr(calls, 'RING_CHANCE', {1: 1.0, 2: 1.0, 3: 1.0})
    monkeypatch.setattr(calls, 'close', lambda *_args: True)
    monkeypatch.setattr(calls, 'why_not', lambda *_args: None)  # Free, whatever the seeded evening holds.
    set_life(client, texts_first=True)
    clock.advance(timedelta(hours=9, minutes=50))  # 21:50, after any seeded minute.
    reconcile(client)
    result = check(client)
    assert (result['state'], result['kind'], result['message']) == ('sent', 'call', None)
    found = where(client)
    assert found['kind'] == 'ringing' and found['text'] == 'Calling you' and found['call']['direction'] == 'them'
    assert check(client)['state'] == 'call'  # Nothing else while it rings.
    says(provider, 'Hey! Sorry, random, I just wanted to hear your voice.')
    send(client, 'hello?', 'client-call-7')
    assert where(client)['state'] == 'call'
    assert 'You called the user at 21:50' in notes(provider) and 'They just picked up. You called because' in \
        notes(provider)
    with client.app.state.database.connect() as connection:
        assert calls.ring_due(connection, current(connection), clock.now()) == []  # One a day.


def test_a_ring_nobody_answers_is_missed_and_they_text_about_it(client, nearby, clock, monkeypatch):
    monkeypatch.setattr(calls, 'FIRST_TEXTS', True)
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        calls.insert(connection, companion, 'them', 'ringing', clock.now(), reason={'why_called': 'you missed them'})
    assert where(client)['kind'] == 'ringing'
    clock.advance(calls.RING)
    found = where(client)
    assert found['state'] == 'apart' and found['call']['status'] == 'missed'
    with client.app.state.database.connect() as connection:
        [trigger] = calls.missed_due(connection, current(connection), clock.now())
    assert "You tried to call the user at 12:00 and they didn't pick up" in trigger.reason


def test_decline_and_no_calls_while_together(client, nearby, clock):
    with client.app.state.database.connect(write=True) as connection:
        found = calls.insert(connection, current(connection), 'them', 'ringing', clock.now())
    assert press(client, f"/{found['id']}/decline")['call']['status'] == 'declined'
    clock.advance(timedelta(hours=7))
    send(client, 'wanna come over now?', 'client-call-8')
    assert where(client)['state'] == 'together'
    assert client.post('/api/life/calls').status_code == 409
    send(client, 'can I call you?', 'client-call-9')  # Beside each other: no call.
    assert where(client)['state'] == 'together'


def test_replies_on_a_call_are_not_held_and_keep_no_texting_habits(client, monkeypatch, provider, clock):
    mira(client, monkeypatch, texting={'bursts': False, 'lowercase': True, 'typos': False})
    monkeypatch.setattr(pacing, 'ACTIVE', True)
    clock.advance(timedelta(hours=7))
    press(client)
    with client.app.state.database.connect() as connection:
        assert pacing.hold(connection, current(connection), clock.now(), 'x')['held_until'] is None
    says(provider, 'Hi! So Good To Hear You.')
    reply = send(client, 'hey', 'client-call-10')['reply']
    assert reply['text'] == 'Hi! So Good To Hear You.'


def test_on_a_call_replies_are_read_aloud_when_a_voice_is_set_up(client, nearby, provider, clock, speaker):  # noqa: F811
    clock.advance(timedelta(hours=7))
    press(client)
    says(provider, 'Hey, you. I was just thinking about you.')
    reply = send(client, 'hey you', 'client-call-11')['reply']
    assert reply['voice'] and reply['voice']['url'] == f"/api/voice/notes/{reply['id']}"
    assert history(client)[-1]['voice']
    press(client, f"/{where(client)['call']['id']}/end")
    says(provider, 'night!')
    reply = send(client, 'night', 'client-call-12')['reply']
    assert not reply['voice']  # Texting again.


def test_a_slow_voice_leaves_a_call_reply_as_text(client, nearby, provider, clock, speaker, monkeypatch):  # noqa: F811
    from companion import conversation
    from companion.voice.notes import VoiceNotes

    async def stuck(*_args, **_kwargs):
        await asyncio.sleep(5)

    monkeypatch.setattr(conversation, 'CALL_VOICE_SECONDS', 0.05)
    monkeypatch.setattr(VoiceNotes, 'record', stuck)
    clock.advance(timedelta(hours=7))
    press(client)
    says(provider, 'Hey, you.')
    started = time.monotonic()
    reply = send(client, 'hey you', 'client-call-slow')['reply']
    assert reply['status'] == 'complete' and not reply['voice'] and time.monotonic() - started < 4


def test_coming_over_during_a_call_ends_it(client, nearby, provider, clock):
    clock.advance(timedelta(hours=7))  # 19:00, free.
    press(client)
    says(provider, 'On my way!')
    send(client, 'wanna come over now?', 'client-call-13')
    found = where(client)
    assert (found['state'], found['kind']) == ('together', 'yours') and found['call'] is None
    assert 'You are on a phone call' not in notes(provider) and 'talked on the phone' not in notes(provider)
    with client.app.state.database.connect() as connection:
        assert calls.latest(connection, current(connection)['active_timeline_id'], clock.now())['status'] == 'ended'


def test_one_call_at_a_time_across_companions(client, nearby, clock, monkeypatch):
    from test_groups import companion_named

    from companion.characters import by_id
    clock.advance(timedelta(hours=7))
    mira_id = current_id(client)
    press(client)  # On with Mira.
    dana_id = companion_named(client, 'Dana')
    with client.app.state.database.connect(write=True) as connection:
        dana = by_id(connection, dana_id)
        assert calls.line_busy(connection, dana, clock.now())  # Dana can't ring through.
        assert calls.ring(connection, dana, openers.Trigger('call:x', 'call', 'why'), clock.now()) is None
    assert client.post('/api/companion/cast/focus', json={'companion_id': dana_id}).status_code == 200
    monkeypatch.setattr(calls, 'why_not', lambda *_args: None)
    assert press(client)['call']['status'] == 'on'  # Calling Dana hangs up on Mira.
    with client.app.state.database.connect() as connection:
        assert calls.on_call(connection, by_id(connection, mira_id), clock.now()) is None


def current_id(client):
    with client.app.state.database.connect() as connection:
        return current(connection)['id']


def test_a_clock_moved_back_hides_a_call_not_yet_made(client, nearby, clock):
    clock.advance(timedelta(hours=7))
    press(client)
    clock.advance(timedelta(hours=-1))
    assert where(client)['call'] is None and where(client)['state'] == 'apart'


def test_what_is_not_asking_to_call_or_hanging_up():
    for text in ('you can call me Sam', 'call me crazy but I love it', 'they call me the boss', 'call me old fashioned'):
        assert not calls.asked(text), text
    for text in ('can we talk on the phone?', 'call?', 'free for a call?', "I'll call you in a sec", 'call me rn please',
                 'call me, I miss you'):
        assert calls.asked(text), text
    for text in ('we need to go to that place sometime', 'i have to go to the bathroom brb',
                 'i gotta run to the store later haha but anyway'):
        assert not calls.hanging_up(text), text
    for text in ('I gotta go to bed', 'have to go now babe', 'I should go, it is late', 'gotta go'):
        assert calls.hanging_up(text), text
