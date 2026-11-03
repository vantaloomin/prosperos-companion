"""Surprise visits (companion/life/drop_by.py): dropping by their home or their work from the map, unannounced."""
from datetime import timedelta

import pytest
from conftest import reconcile, send, set_life
from test_together import mira, notes, says, where

from companion.characters import current
from companion.life import drop_by, rough_patches, together

SHIFTS = [{'key': 'work', 'label': 'Shift at Club Charles', 'kind': 'work', 'start': '09:00', 'end': '17:00',
           'days': [0, 1, 2, 3, 4]},
          {'key': 'evening', 'label': 'Evening', 'kind': 'leisure', 'start': '17:00', 'end': '23:00'},
          {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]


@pytest.fixture
def barkeep(client, monkeypatch):
    mira(client, monkeypatch, schedule=SHIFTS)


def go(client, place, status=200):
    response = client.post('/api/life/drop-by', json={'place': place})
    assert response.status_code == status, response.text
    return response.json()


def card(client, place_id):
    places = client.get('/api/life/map').json()['places']
    return next(place for place in places if place['id'] == place_id)


def test_nobody_is_home_while_they_are_at_work_and_they_hear_about_it(client, barkeep, provider, clock):
    found = go(client, 'home')  # Monday 12:00, at work.
    assert found['result'] == 'nobody' and found['outing'] is None
    assert found['reason'] == {'why': 'busy', 'label': 'work', 'until': '17:00'}
    assert found['text'] == "Nobody's home. Mira is at work until 17:00."
    assert where(client)['state'] == 'apart'
    says(provider)
    send(client, 'came by earlier, you were out!', 'client-drop-1')
    assert 'the user dropped by your place without telling you first, but you weren' in notes(provider)
    clock.advance(timedelta(hours=7))
    says(provider)
    send(client, 'hey', 'client-drop-2')
    assert 'dropped by your place without telling you first' not in notes(provider)  # Long ago now.


def test_home_and_free_they_let_you_in_and_say_hello_in_person(client, barkeep, provider, clock):
    clock.advance(timedelta(hours=7))  # 19:00, free.
    says(provider, 'Oh! Hi, come in!')
    found = go(client, 'home')
    assert found['result'] == 'in'
    asked = provider.requests[-1]['messages'][-1]['content']
    assert 'The user just turned up at your door, in person, without telling you first' in asked
    visit = found['outing']
    assert (visit['activity'], visit['at_time'], visit['place']['surprise']) == ('visit-in', '19:00', True)
    assert visit['until_time'] == '20:30'  # Not close yet: an hour and a half.
    assert found['where']['state'] == 'together' and found['where']['text'] == "At Mira's place"
    messages = client.get('/api/conversation').json()['messages']
    assert messages[-1]['role'] == 'companion' and messages[-1]['text'] == 'Oh! Hi, come in!'
    says(provider)
    send(client, 'surprise!', 'client-drop-3')
    assert 'they dropped by without telling you first' in notes(provider)
    assert 'face to face, not texting' in notes(provider)
    clock.advance(timedelta(hours=2))
    reconcile(client)
    [kept] = client.get('/api/life/outings').json()['outings']
    assert kept['status'] == 'done' and kept['memory_id']
    memories = client.get('/api/memories').json()
    assert any(memory['subject'] == "Dropped by Mira's place" for memory in memories)


def test_close_and_easy_life_runs_the_full_visit(client, barkeep, provider, clock, monkeypatch):
    monkeypatch.setattr(together, 'close', lambda *_args: True)
    clock.advance(timedelta(hours=7))
    says(provider)
    assert go(client, 'home')['outing']['until_time'] == '22:00'


def test_asleep_or_tense_or_late(client, barkeep, provider, clock, monkeypatch):
    clock.advance(timedelta(hours=12))  # Tuesday 00:00, asleep.
    found = go(client, 'home')
    assert found['result'] == 'asleep' and found['text'] == 'No answer. The lights are off; Mira is asleep.'
    clock.advance(timedelta(hours=19))  # Tuesday 19:00.
    monkeypatch.setattr(rough_patches, 'tension', lambda *_args: {'patch': 1, 'warning': 0})
    monkeypatch.setattr(drop_by, 'TENSE_TURN', 1.0)
    found = go(client, 'home')
    assert found['result'] == 'not-now' and found['text'] == "Mira comes to the door, but now isn't a good time."
    says(provider)
    send(client, 'sorry about earlier', 'client-drop-4')
    assert 'You came to the door but said now was not a good time (things are tense between you)' in notes(provider)
    set_life(client, together_realism=1)  # An easy life: always glad to see you.
    says(provider)
    assert go(client, 'home')['result'] == 'in'


def test_at_work_you_visit_them_on_shift_and_their_shift_stays(client, barkeep, provider, clock):
    reconcile(client)
    place = card(client, 'club-charles')
    assert 'work' in place['pins'] and place['drop_by'] == {'ok': True, 'note': '', 'shift_until': '17:00'}
    assert card(client, '~home')['drop_by'] == {'ok': True, 'note': '', 'shift_until': None}
    says(provider, 'Hey! What are you doing here?')
    found = go(client, 'work')
    visit = found['outing']
    assert (visit['activity'], visit['at_time'], visit['until_time']) == ('visit-work', '12:00', '12:30')
    asked = provider.requests[-1]['messages'][-1]['content']
    assert 'You are at work at Club Charles' in asked and 'You keep working' in asked
    assert found['where']['text'] == 'At Club Charles' and found['where']['kind'] == 'out'
    assert not found['where']['outing']['longer_ok']  # Their shift: no staying longer.
    assert card(client, 'club-charles')['drop_by'] == {'ok': False, 'note': "You're with Mira right now.",
                                                         'shift_until': '17:00'}  # Together now.
    says(provider)
    send(client, 'busy day?', 'client-drop-5')
    assert 'they dropped by your work without telling you first' in notes(provider)
    reply = client.get('/api/conversation').json()['messages'][-1]
    assert reply['role'] == 'companion' and not reply.get('held_until')  # Face to face: no waiting for a break.
    reconcile(client)
    with client.app.state.database.connect() as connection:
        entry = connection.execute("SELECT block FROM life_agenda WHERE slot_key LIKE 'work@2026-10-05%'").fetchone()
    assert '"with_user"' not in entry['block']  # Still at work.
    clock.advance(timedelta(hours=1))
    reconcile(client)
    [kept] = client.get('/api/life/outings').json()['outings']
    assert kept['status'] == 'done'
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        assert drop_by.on_shift(connection, companion, clock.now())  # Back at it, no trip home.
    clock.advance(timedelta(hours=6))  # 19:00, off shift.
    assert card(client, 'club-charles')['drop_by'] == {'ok': False, 'note': '', 'shift_until': None}
    go(client, 'work', 409)


def test_no_drop_by_from_another_city(client, monkeypatch, clock):
    mira(client, monkeypatch, home_city='Chicago')
    world = client.get('/api/worlds').json()['world']
    assert client.put(f"/api/worlds/{world['id']}/home", json={'city_id': 'baltimore'}).status_code == 200
    clock.advance(timedelta(hours=7))
    found = client.post('/api/life/drop-by', json={'place': 'home'})
    assert found.status_code == 409 and 'different cities' in found.text
