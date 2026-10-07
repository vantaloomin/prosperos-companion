"""Birthdays and anniversaries: from the calendar and what the user said, never guessed."""
from datetime import date, timedelta

import pytest
from conftest import reconcile, send, set_life

from companion.clock import zone
from companion.database import decode
from companion.life import body, circle, composer, occasions


def test_a_birthday_is_heard_only_when_said_plainly():
    today = date(2026, 10, 5)
    assert occasions.said_birthday('my birthday is March 3rd, by the way', today) == '03-03'
    assert occasions.said_birthday("My bday's on the 14th of Feb", today) == '02-14'
    assert occasions.said_birthday("it's my birthday today!", today) == '10-05'
    assert occasions.said_birthday('my birthday is tomorrow', today) == '10-06'
    assert occasions.said_birthday('When is your birthday?', today) is None
    assert occasions.said_birthday('if my birthday is in June we should party', today) is None
    assert occasions.said_birthday('my birthday is February 30', today) is None


def test_milestones_count_from_the_first_conversation():
    first = date(2026, 1, 31)
    assert occasions.milestone(first, date(2026, 2, 28)) == 'a month'
    assert occasions.milestone(first, date(2026, 4, 30)) == 'three months'
    assert occasions.milestone(first, first + timedelta(days=100)) == '100 days'
    assert occasions.milestone(first, date(2027, 1, 31)) == 'a year'
    assert occasions.milestone(first, date(2028, 1, 31)) == '2 years'
    assert occasions.milestone(first, date(2026, 3, 31)) is None
    assert occasions.on(date(2027, 2, 28), '02-29') and not occasions.on(date(2028, 2, 28), '02-29')


def test_the_users_birthday_is_noticed_kept_and_wished(client, connected, clock, provider):
    send(client, 'Fun fact: my birthday is October 7th.', 'client-bday-01')
    assert client.get('/api/life/settings').json()['user_birthday'] == '10-07'
    send(client, 'Actually my birthday is May 1', 'client-bday-02')
    assert client.get('/api/life/settings').json()['user_birthday'] == '10-07'
    system = client.get('/api/context/preview').json()['system']
    assert 'Birthdays and anniversaries' in system and "In 2 days (Wednesday 07 October) is the user's birthday." in system
    assert client.get('/api/today').json()['occasions'][0]['kind'] == 'user_birthday'
    clock.advance(timedelta(days=2))
    clock.instant = clock.now().replace(hour=13)
    set_life(client, texts_first=True)
    result = client.post('/api/life/texts/check').json()
    assert result['kind'] == 'occasion'
    assert "Today is the user's birthday" in provider.requests[-1]['messages'][-1]['content']
    set_life(client, user_birthday='')
    assert "the user's birthday" not in client.get('/api/context/preview').json()['system']


def test_a_bad_birthday_is_refused(client, companion):
    assert client.put('/api/life/settings', json={'user_birthday': '13-01'}).status_code == 422


def test_the_companions_birthday_is_a_celebration(client, monkeypatch, clock):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    tomorrow = (clock.now() + timedelta(days=1)).strftime('%m-%d')
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC', 'birthday': tomorrow})
    assert response.status_code == 200, response.text
    set_life(client, automatic_events=True)
    system = client.get('/api/context/preview').json()['system']
    assert '- Tomorrow is your birthday.' in system
    reconcile(client)
    with client.app.state.database.connect() as connection:
        entries = [decode(row['entry']) for row in connection.execute(
            "SELECT entry FROM life_agenda WHERE subject='companion' AND local_date=? AND entry IS NOT NULL "
            'ORDER BY starts_at', ((clock.now() + timedelta(days=1)).date().isoformat(),))]
    birthday = [entry for entry in entries if entry['activity'] == 'own-birthday']
    assert len(birthday) == 1 and 'birthday' in birthday[0]['summary']
    assert client.post('/api/companion', json={'name': 'Ana', 'birthday': '7-4'}).status_code == 422


@pytest.mark.parametrize('relationship, words', [('friendship', 'since you and the user first talked'),
                                                 ('romance', 'your anniversary')])
def test_talking_milestones_reach_the_context(client, connected, clock, relationship, words):
    version = client.get('/api/companion').json()['companion']['version']
    revised = client.post('/api/companion/versions', json={
        'definition': {**version['definition'], 'relationship': relationship}, 'expected_version_id': version['id']})
    assert revised.status_code == 200, revised.text
    send(client, 'Hi there', 'client-anniv-01')
    clock.advance(timedelta(days=100))
    system = client.get('/api/context/preview').json()['system']
    assert words in system and '100 days' in system


def test_circle_birthdays_reach_the_context_but_open_no_conversation(client, connected, clock, monkeypatch):
    people = client.get('/api/life/circle').json()
    first, second = people[0], people[1]
    today = clock.now().astimezone(zone('Europe/Lisbon')).date()
    dates = {first['id']: today, second['id']: today + timedelta(days=3)}
    monkeypatch.setattr(occasions, 'SEEDED', True)
    monkeypatch.setattr(occasions, 'own_birthday', lambda _companion: None)
    monkeypatch.setattr(circle, 'birthday', lambda person_id: dates.get(
        person_id, today + timedelta(days=30)).strftime('%m-%d'))
    system = client.get('/api/context/preview').json()['system']
    assert f"- Today is your {first['role']} {first['name']}'s birthday." in system
    later = (today + timedelta(days=3)).strftime('%A %d %B')
    assert f"- In 3 days ({later}) is your {second['role']} {second['name']}'s birthday." in system
    assert 'Wish them' not in system
    found = [item for item in client.get('/api/today').json()['occasions'] if item['kind'] == 'circle_birthday']
    assert [(item['person'], item['days']) for item in found] == [(first['name'], 0), (second['name'], 3)]
    set_life(client, texts_first=True)
    assert client.post('/api/life/texts/check').json()['state'] == 'nothing'
