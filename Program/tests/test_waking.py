"""Waking them (companion/life/waking.py): a second text, "wake up" or a call wakes a sleeping companion, groggy, at a
small cost that wears thinner night after night, and they may bring it up the morning after."""
from datetime import timedelta

import pytest
from conftest import send, set_life
from test_texting import OFFICE, says
from test_together import notes

from companion import moods
from companion.characters import current
from companion.clock import parse
from companion.life import pacing, waking


@pytest.fixture
def mira(client, provider, monkeypatch, clock):
    monkeypatch.setattr(pacing, 'ACTIVE', True)
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC', 'schedule': OFFICE})
    assert response.status_code == 200, response.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    clock.instant = clock.now().replace(hour=2, minute=0)
    return response.json()


def mood(client, clock):
    with client.app.state.database.connect() as connection:
        return moods.current(connection, f"companion:{current(connection)['id']}", clock.now())


def messages(client):
    return client.get('/api/conversation').json()['messages']


def test_one_text_waits_for_morning_and_a_second_wakes_them(client, mira, provider, clock):
    says(provider, 'reply for the morning')
    first = send(client, 'hey', 'client-wake-1')['reply']
    assert first['held_until'].startswith(clock.now().date().isoformat() + 'T07:00')
    assert 'just woke you up' not in notes(provider)
    clock.advance(timedelta(minutes=2))
    says(provider, 'mm.. wha. you ok?')
    sent = send(client, 'you up? cant sleep', 'client-wake-2')
    second = sent['reply']
    assert second['held_until'] is None and sent['dropped'] == [first['id']]
    assert "Their texts just woke you up. It's 02:02 for you" in notes(provider)
    # The reply that was waiting for morning is gone; the groggy one answers both.
    assert first['id'] not in {message['id'] for message in messages(client)}
    found = mood(client, clock)
    assert (found['feeling'], found['intensity'], found['target']) == ('annoyed', 1, 'user')


def test_wake_up_words_wake_them_with_one_text(client, mira, provider, clock):
    says(provider, 'whaa? what happened')
    reply = send(client, 'WAKE UP i have news!!', 'client-wake-3')['reply']
    assert reply['held_until'] is None
    assert 'just woke you up' in notes(provider)


def test_still_up_for_a_while_then_back_asleep(client, mira, provider, clock):
    says(provider, 'mm?')
    send(client, 'wake up', 'client-wake-4')
    clock.advance(timedelta(minutes=5))
    says(provider, 'mhm')
    assert send(client, 'sorry, just missed you', 'client-wake-5')['reply']['held_until'] is None
    assert "You're still half-awake after they woke you at 02:00" in notes(provider)
    clock.advance(waking.AWAKE_FOR + timedelta(minutes=1))
    says(provider, 'morning reply')
    assert send(client, 'night!', 'client-wake-6')['reply']['held_until'] is not None  # Dropped off again.
    with client.app.state.database.connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM wakes').fetchone()[0] == 1


def test_it_wears_thinner_night_after_night(client, mira, provider, clock):
    for night in range(4):
        says(provider, 'mm')
        send(client, 'wake up', f'client-wake-night-{night}')
        if night < 3:
            clock.advance(timedelta(days=1))
    with client.app.state.database.connect() as connection:
        levels = [row[0] for row in connection.execute('SELECT level FROM wakes ORDER BY woken_at')]
    assert levels == ['first', 'again', 'again', 'thin']
    assert "they've woken you most nights lately (4 nights). It's wearing thin" in notes(provider)
    found = mood(client, clock)
    assert (found['feeling'], found['intensity']) == ('annoyed', 2)


def test_they_never_mind_when_realism_says_so(client, mira, provider, clock):
    set_life(client, waking_realism=0)
    assert client.get('/api/life/settings').json()['waking_realism'] == 0
    for night in range(4):
        says(provider, 'mm')
        send(client, 'wake up', f'client-wake-mind-{night}')
        clock.advance(timedelta(days=1))
    assert 'wearing thin' not in notes(provider) and 'night lately' not in notes(provider)
    clock.advance(timedelta(hours=-24))
    assert mood(client, clock) is None


def test_they_bring_it_up_once_in_the_morning(client, mira, provider, clock):
    says(provider, 'mm?')
    send(client, 'wake up', 'client-wake-7')
    clock.instant = clock.now().replace(hour=8)  # Up, and not at work until 09:00.
    says(provider, 'morning! you woke me up last night lol')
    send(client, 'good morning!!', 'client-wake-8')
    assert 'Last night around 02:00 they woke you up (texts)' in notes(provider)
    says(provider, 'anyway')
    send(client, 'how did you sleep?', 'client-wake-9')
    assert 'Last night around' not in notes(provider)


def test_a_call_wakes_them_and_they_pick_up_groggy(client, mira, provider, clock):
    response = client.post('/api/life/calls')
    assert response.status_code == 200, response.text
    found = response.json()
    assert found['state'] == 'call' and found['call']['status'] == 'on'
    assert parse(found['call']['until_at']) - clock.now() <= timedelta(minutes=30)
    says(provider, 'mm.. hello?')
    send(client, 'hi, sorry, did i wake you?', 'client-wake-10')
    assert "Their call just woke you up. It's 02:00 for you" in notes(provider)


def test_without_paced_replies_they_answer_at_once_and_nothing_is_counted(client, mira, provider, clock):
    set_life(client, paced_replies=False)
    says(provider, 'hey')
    assert send(client, 'hey', 'client-wake-11')['reply']['held_until'] is None
    assert 'just woke you up' not in notes(provider)
    with client.app.state.database.connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM wakes').fetchone()[0] == 0
