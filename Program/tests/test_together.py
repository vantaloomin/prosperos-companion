"""Together or apart (companion/life/together.py): visits asked for in the chat, knocks at the door, and the state."""
from datetime import timedelta

import pytest
from conftest import reconcile, send, set_life

from companion.characters import current
from companion.life import body, composer, openers, outings, together
from companion.providers.chat import Chunk

EVENINGS = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00', 'days': [0, 1, 2, 3, 4]},
            {'key': 'evening', 'label': 'Evening', 'kind': 'leisure', 'start': '17:00', 'end': '23:00'},
            {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]


def test_visits_are_read_from_the_message():
    assert together.asked('wanna come over?') == 'visit-yours'
    assert together.asked('Come over tonight, I miss you') == 'visit-yours'
    assert together.asked('Can you come round tonight?') == 'visit-yours'
    assert together.asked("Come to mine for dinner Friday? I'll cook") == 'dinner-yours'
    assert together.asked('Can I come over?') == 'visit-in'
    assert together.asked('could i come to yours later?') == 'visit-in'
    assert together.asked("I'm outside your door, let me in") == 'door'
    for text in ('Dana came over yesterday', "I don't want you to come over", 'how was work?'):
        assert together.asked(text) is None, text


def test_more_ways_to_ask_for_a_visit():
    assert together.asked('dinner at mine tonight?') == 'dinner-yours'
    assert together.asked('want to come to mine for dinner?') == 'dinner-yours'
    assert together.asked('Do you want me to come over?') == 'visit-in'
    assert together.asked('Can I stop by?') == 'visit-in'
    assert together.asked('mind if I drop by later?') == 'visit-in'
    # Going to theirs for dinner is a visit, never a restaurant (companion/life/outings.py).
    from datetime import date
    assert outings.proposal("want to come to mine for dinner? I'll cook", date(2026, 10, 5), {}, None) is None


def mira(client, monkeypatch, **values):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    for name in ('QUIET_SHARE', 'PLAN_SHARE', 'THREAD_SHARE'):
        monkeypatch.setattr(composer, name, 0)
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC', 'schedule': EVENINGS,
                                                    'home_city': 'Baltimore', **values})
    assert response.status_code == 200, response.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    set_life(client, automatic_events=True, phrase_with_model=False, catch_up_max_events=6,
             catch_up_lookback_hours=168)


@pytest.fixture
def nearby(client, monkeypatch):
    mira(client, monkeypatch)


def says(provider, text='Okay!'):
    provider.replies.append([Chunk(text), Chunk('', 'stop')])


def where(client):
    response = client.get('/api/life/where')
    assert response.status_code == 200, response.text
    return response.json()


def notes(provider):
    return provider.requests[-1]['prompt']


def test_at_work_they_say_why_not_and_after_work_they_come_over(client, nearby, provider, clock):
    says(provider)
    send(client, 'wanna come over?', 'client-together-1')  # Monday 12:00, at work.
    assert client.get('/api/life/outings').json()['outings'] == []
    assert 'You can\'t: you are at work until 17:00' in notes(provider)
    assert where(client)['state'] == 'apart'
    clock.advance(timedelta(hours=6))  # 18:00.
    says(provider)
    send(client, 'wanna come over now?', 'client-together-2')
    [visit] = client.get('/api/life/outings').json()['outings']
    assert (visit['activity'], visit['at_time'], visit['until_time']) == ('visit-yours', '18:00', '21:00')
    assert visit['place']['id'] == together.YOURS and visit['state'] == 'now'
    found = where(client)
    assert found['state'] == 'together' and found['text'] == 'At your place' and found['outing']['id'] == visit['id']
    says(provider)
    send(client, 'so how was your day?', 'client-together-3')
    assert "Right now you are over at the user's place" in notes(provider)
    assert 'face to face, not texting' in notes(provider)
    status = client.get('/api/chats').json()['chats'][0]['status']
    assert status['where'] == {'state': 'together', 'kind': 'yours', 'text': 'At your place'}
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        assert openers.held(connection, companion, {'texts_first': True}, clock.now()) == 'together'
    # The user says goodbye, and they are apart again.
    says(provider)
    send(client, "it's late, you should head home", 'client-together-4')
    assert where(client)['state'] == 'apart'
    says(provider)
    send(client, 'thanks for coming over', 'client-together-5')
    assert "You left the user's place a little while ago" in notes(provider)
    clock.advance(timedelta(minutes=5))
    reconcile(client)
    [kept] = client.get('/api/life/outings').json()['outings']
    assert kept['status'] == 'done' and kept['memory_id']


def test_a_visit_on_a_day_is_planned_like_an_outing(client, nearby, provider):
    reconcile(client)
    says(provider)
    send(client, 'come over Friday?', 'client-together-6')
    [visit] = client.get('/api/life/outings').json()['outings']
    assert (visit['activity'], visit['local_date'], visit['at_time']) == ('visit-yours', '2026-10-09', '19:00')
    assert "You agreed: a visit to the user's place" in notes(provider)
    reconcile(client)
    with client.app.state.database.connect() as connection:
        entry = connection.execute("SELECT entry FROM life_agenda WHERE slot_key='evening@2026-10-09'").fetchone()
    assert '"came over to your place' in entry['entry'] or 'came over to your place' in entry['entry']


def test_the_user_at_their_door_comes_in_when_they_are_home(client, nearby, provider, clock):
    clock.advance(timedelta(hours=7))  # 19:00.
    says(provider)
    send(client, "I'm outside your door!", 'client-together-7')
    [visit] = client.get('/api/life/outings').json()['outings']
    assert visit['activity'] == 'visit-in' and visit['place']['name'] == "Mira's place"
    assert where(client)['text'] == "At Mira's place"
    says(provider)
    send(client, 'hi!!', 'client-together-8')
    assert 'Right now the user is over at your place, in person' in notes(provider)


def test_long_distance_they_cannot_just_come_over(client, monkeypatch, provider, clock):
    mira(client, monkeypatch, home_city='Chicago')
    world = client.get('/api/worlds').json()['world']
    assert client.put(f"/api/worlds/{world['id']}/home", json={'city_id': 'baltimore'}).status_code == 200
    clock.advance(timedelta(hours=7))
    says(provider)
    send(client, 'come over?', 'client-together-9')
    assert client.get('/api/life/outings').json()['outings'] == []
    assert "you live in Chicago" in notes(provider) and "so you can't just come over" in notes(provider)
    assert where(client)['kind'] == 'long-distance' and where(client)['text'].startswith('Long distance, Chicago')
    with client.app.state.database.connect() as connection:
        assert not together.invites(connection, current(connection))  # No dinner or hobby invites either.


def knock(client, clock):
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        found = together.knock_due(connection, companion, clock.now())
        if not found:
            return None
        [trigger] = found
        connection.execute("INSERT INTO messages (id, timeline_id, seq, role, text, status, active, character_version_id, "
                           "memory_revision, created_at, completed_at) VALUES ('knock-message', ?, 99, 'companion', ?, "
                           "'complete', 1, ?, 0, ?, ?)", (companion['active_timeline_id'], trigger.template,
                                                         companion['active_version_id'], clock.now().isoformat(),
                                                         clock.now().isoformat()))
        together.settle(connection, companion, {'id': 'knock-message'}, trigger, clock.now().isoformat())
        return trigger


def test_a_close_companion_knocks_and_not_now_sends_them_home(client, nearby, provider, clock, monkeypatch):
    monkeypatch.setattr(together, 'FIRST_TEXTS', True)
    monkeypatch.setattr(together, 'KNOCK_CHANCE', {2: 1.0, 3: 1.0})
    monkeypatch.setattr(together, 'close', lambda *_args: True)
    clock.advance(timedelta(hours=8, minutes=50))  # 20:50, after any seeded minute.
    reconcile(client)
    trigger = knock(client, clock)
    assert trigger.kind == 'drop_in' and "standing at the user's door" in trigger.reason
    found = where(client)
    assert found['kind'] == 'knock' and found['outing']['not_now'] and found['outing']['until_time'] == '22:30'
    says(provider)
    send(client, 'oh! hi! um, not a good time actually', 'client-together-10')
    assert where(client)['state'] == 'apart'
    says(provider)
    send(client, 'sorry!', 'client-together-11')
    assert "they said now wasn't a good time" in notes(provider)
    clock.advance(timedelta(minutes=5))
    reconcile(client)
    [turned] = client.get('/api/life/outings').json()['outings']
    assert turned['status'] == 'done' and not turned['memory_id']


def test_no_knocks_on_an_easy_life_or_for_someone_not_yet_close(client, nearby, clock, monkeypatch):
    monkeypatch.setattr(together, 'FIRST_TEXTS', True)
    monkeypatch.setattr(together, 'KNOCK_CHANCE', {2: 1.0, 3: 1.0})
    clock.advance(timedelta(hours=8, minutes=50))
    assert knock(client, clock) is None  # Just met.
    monkeypatch.setattr(together, 'close', lambda *_args: True)
    set_life(client, together_realism=1)
    assert knock(client, clock) is None
    set_life(client, together_realism=2)
    assert knock(client, clock) is not None


def test_they_suggest_getting_together_by_the_slider(client, nearby, clock, monkeypatch):
    monkeypatch.setattr(together, 'FIRST_TEXTS', True)
    monkeypatch.setattr(together, 'SUGGEST_CHANCE', {1: 1.0, 2: 1.0, 3: 1.0})
    reconcile(client)
    set_life(client, together_realism=0)
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        assert together.suggest_due(connection, companion, clock.now()) == []
    set_life(client, together_realism=2)
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        [trigger] = together.suggest_due(connection, companion, clock.now())
        assert trigger.kind == 'get_together'
        connection.execute("INSERT INTO messages (id, timeline_id, seq, role, text, status, active, character_version_id, "
                           "memory_revision, created_at, completed_at) VALUES ('suggest-message', ?, 99, 'companion', ?, "
                           "'complete', 1, ?, 0, ?, ?)", (companion['active_timeline_id'], trigger.template,
                                                         companion['active_version_id'], clock.now().isoformat(),
                                                         clock.now().isoformat()))
        outing = together.settle(connection, companion, {'id': 'suggest-message', 'created_at': clock.now().isoformat()},
                                 trigger, clock.now().isoformat())
    assert outing and outing['activity'] == trigger.sources[0] and outing['local_date'] == trigger.sources[1]


def test_a_visit_ends_before_bed_and_early_on_a_work_night():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    monday = datetime(2026, 10, 5, 21, 0, tzinfo=ZoneInfo('UTC'))
    assert together.end_of_visit({'name': 'Mira', 'schedule': EVENINGS}, monday, 3.0) == '22:30'
    friday = datetime(2026, 10, 9, 21, 0, tzinfo=ZoneInfo('UTC'))
    assert together.end_of_visit({'name': 'Mira', 'schedule': EVENINGS}, friday, 3.0) == '23:00'
    assert outings.ACTIVITIES['visit-yours'][3] == 3.0


def test_tonight_asked_at_work_is_a_visit_this_evening_and_sometime_settles_nothing(client, nearby, provider):
    says(provider)
    send(client, 'come over tonight?', 'client-together-20')  # Monday 12:00, at work until 17:00.
    [visit] = client.get('/api/life/outings').json()['outings']
    assert (visit['activity'], visit['local_date'], visit['at_time'], visit['state']) == (
        'visit-yours', '2026-10-05', '19:00', 'planned')
    assert "You can't" not in notes(provider) and where(client)['state'] == 'apart'
    says(provider)
    send(client, 'can I come over sometime next week?', 'client-together-21')
    assert len(client.get('/api/life/outings').json()['outings']) == 1
    assert 'The user asked' not in notes(provider)


def test_sometime_in_the_evening_is_not_a_visit_from_now(client, nearby, provider, clock):
    clock.advance(timedelta(hours=7))  # 19:00, free.
    says(provider)
    send(client, 'come over sometime next week?', 'client-together-22')
    assert client.get('/api/life/outings').json()['outings'] == [] and where(client)['state'] == 'apart'
    says(provider)
    send(client, 'come over later?', 'client-together-23')  # In the evening, later is now.
    assert where(client)['state'] == 'together'


def test_their_texting_style_stays_out_of_the_prompt_while_together(client, monkeypatch, provider, clock):
    mira(client, monkeypatch, texting={'bursts': True, 'lowercase': True, 'typos': True})
    says(provider)
    send(client, 'hi', 'client-together-24')
    assert 'How you text:' in provider.requests[-1]['system']
    clock.advance(timedelta(hours=7))
    says(provider)
    send(client, 'come over?', 'client-together-25')
    assert where(client)['state'] == 'together'
    says(provider)
    send(client, 'nice to see you', 'client-together-26')
    assert 'How you text:' not in provider.requests[-1]['system']


def test_nobody_knocks_while_the_user_is_with_someone(client, nearby, provider, clock, monkeypatch):
    monkeypatch.setattr(together, 'FIRST_TEXTS', True)
    monkeypatch.setattr(together, 'KNOCK_CHANCE', {2: 1.0, 3: 1.0})
    monkeypatch.setattr(together, 'close', lambda *_args: True)
    clock.advance(timedelta(hours=8, minutes=50))  # 20:50, after any seeded minute.
    with client.app.state.database.connect() as connection:
        assert together.knock_due(connection, current(connection), clock.now())
    says(provider)
    send(client, 'can I come to yours?', 'client-together-27')  # The user goes over to Mira's.
    assert where(client)['kind'] == 'theirs'
    with client.app.state.database.connect() as connection:
        assert together.with_someone(connection, clock.now())
        assert together.knock_due(connection, current(connection), clock.now()) == []
