"""Meeting their people (companion/life/their_people.py): the meet-up, first impressions, and guests who have met you."""
from datetime import timedelta

import pytest
from conftest import send, show

from companion import consequences
from companion.characters import current
from companion.database import decode, encode, many, optional
from companion.life import circle, outings, their_people
from companion.providers.chat import Chunk

ROLES = ['mom', 'dad', 'brother', 'close friend', 'friend']


def make(client, relationship='romance', roles=ROLES, **values):
    response = client.post('/api/companion', json={'name': 'Mira Costa', 'timezone': 'UTC',
                                                     'relationship': relationship, **values})
    assert response.status_code == 200, response.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    assert client.get('/api/life/circle').status_code == 200
    with client.app.state.database.connect(write=True) as connection:
        rows = circle.people(connection, current(connection)['active_timeline_id'])
        for row, role in zip(rows, roles, strict=False):
            details = {**decode(row['details']), 'local': True}
            connection.execute('UPDATE circle_people SET role=?, details=? WHERE id=?', (role, encode(details), row['id']))
        for row in rows[len(roles):]:
            connection.execute("UPDATE circle_people SET status='removed' WHERE id=?", (row['id'],))


def set_step(client, step):
    response = client.put('/api/life/steps', json={'step': step})
    assert response.status_code == 200, response.text


def advance(client, clock):
    with client.app.state.database.connect(write=True) as connection:
        their_people.advance(connection, current(connection), clock.now())


def meetups(client):
    with client.app.state.database.connect() as connection:
        return their_people.meetups(connection, current(connection)['active_timeline_id'])


def invite(client, clock, key='meet-message'):
    """The invitation a meet-up due today would send, saved the way openers.py saves it."""
    from companion.life import openers
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        found = [trigger for trigger in openers.candidates(connection, companion, clock.now())
                 if trigger.kind == 'meet_people']
        if not found:
            return None, None
        trigger = found[0]
        connection.execute("INSERT INTO messages (id, timeline_id, seq, role, text, status, active, character_version_id, "
                           "memory_revision, created_at, completed_at) VALUES (?, ?, 99, 'companion', ?, 'complete', 1, ?, "
                           '0, ?, ?)', (key, companion['active_timeline_id'], trigger.template,
                                        companion['active_version_id'], clock.now().isoformat(), clock.now().isoformat()))
        connection.execute("INSERT INTO openers (id, timeline_id, trigger_key, kind, facts, message_id, wording, "
                           "created_at) VALUES (?, ?, ?, ?, '{}', ?, 'template', ?)",
                           (f'opener-{key}', companion['active_timeline_id'], trigger.key, trigger.kind, key,
                            clock.now().isoformat()))
        outing = their_people.settle(connection, companion, {'id': key}, trigger, clock.now().isoformat())
        return trigger, outing


def prompt(provider):
    request = provider.requests[-1]
    return request['prompt'] + ''.join(message['content'] for message in request.get('messages', ()))


def says(provider, text='Okay!'):
    provider.replies.append([Chunk(text), Chunk('', 'stop')])


def at(clock, outing, hour_minute):
    """Moves the clock to a time on the outing's day."""
    from datetime import date, datetime
    hours, minutes = map(int, hour_minute.split(':'))
    target = datetime.combine(date.fromisoformat(outing['local_date']), datetime.min.time(), clock.now().tzinfo)
    clock.advance(target + timedelta(hours=hours, minutes=minutes) - clock.now())


@pytest.fixture
def invites(monkeypatch):
    monkeypatch.setattr(their_people, 'FIRST_TEXTS', True)


def test_the_bank_has_enough_lines_and_each_names_who_where_and_when():
    for kind in ('family', 'friends'):
        lines = their_people.bank()[kind]
        assert len(lines) >= 100 and len(set(lines)) == len(lines)
        for line in lines:
            assert all(part in line for part in ('{people}', '{place}', '{day}', '{time}')), line
    assert their_people.agree('{people} are so excited', True) == '{people} is so excited'
    assert their_people.agree('{people} and I are going', True) == '{people} and I are going'
    assert their_people.agree('{people} are so excited', False) == '{people} are so excited'


def test_at_the_step_a_family_dinner_is_planned_and_the_invitation_books_it(client, provider, clock, invites):
    make(client)
    set_step(client, 'their_people')
    advance(client, clock)
    [planned] = meetups(client)
    assert planned['kind'] == 'family' and planned['why'] == 'step' and planned['status'] == 'planned'
    advance(client, clock)
    assert len(meetups(client)) == 1  # Planned once.
    clock.advance(timedelta(days=7))
    trigger, outing = invite(client, clock)
    assert trigger and 'meet' in trigger.reason and 'your mom' in trigger.reason
    assert "my parents' place" in trigger.template and '{' not in trigger.template
    assert outing['activity'] == 'meet-family' and outing['place']['kind'] == 'family-home'
    assert [person['role'] for person in outing['place']['people']] == ['mom', 'dad', 'brother']
    assert outing['cost'] == 0
    [booked] = meetups(client)
    assert booked['status'] == 'booked' and booked['outing_id'] == outing['id']
    with client.app.state.database.connect() as connection:
        rows = many(connection, 'SELECT * FROM people_impressions')
    assert len(rows) == 3 and all(row['met_on'] is None for row in rows)
    assert {row['impression'] for row in rows} <= set(their_people.IMPRESSIONS)


def test_the_meetup_is_in_person_with_their_people_and_afterwards_they_have_an_opinion(client, provider, clock,
                                                                                      invites):
    make(client)
    set_step(client, 'their_people')
    advance(client, clock)
    clock.advance(timedelta(days=7))
    _trigger, outing = invite(client, clock)
    says(provider)
    send(client, 'see you there!', 'client-people-1')
    assert 'so the user can meet them' in prompt(provider)
    at(clock, outing, '19:30')
    says(provider)
    send(client, 'this is lovely', 'client-people-2')
    text = prompt(provider)
    assert 'Here with you: your mom' in text and 'It is the first time they are meeting the user.' in text
    assert 'How it is going:' in text and 'you speak only as yourself' in text
    clock.advance(timedelta(days=1))
    advance(client, clock)
    assert meetups(client)[0]['status'] == 'done'
    says(provider)
    send(client, 'what did your family think of me?', 'client-people-3')
    text = prompt(provider)
    assert 'What your people think of the user' in text
    assert 'met the user on' in text and 'your mom' in text
    people = client.get('/api/life/circle').json()
    met = [person['met'] for person in people if person['met']]
    assert len(met) == 3 and all(item['met_on'] == outing['local_date'] and item['label'] for item in met)
    assert all(item['consequence_id'] is None for item in met)  # Odds only with Hidden values on.


def test_with_no_family_in_town_they_go_out_with_friends(client, clock, invites):
    make(client, roles=['close friend', 'friend', 'coworker'])
    set_step(client, 'their_people')
    advance(client, clock)
    assert meetups(client)[0]['kind'] == 'friends'


def test_called_off_it_comes_round_again_later(client, clock, invites):
    make(client)
    set_step(client, 'their_people')
    advance(client, clock)
    clock.advance(timedelta(days=7))
    _trigger, outing = invite(client, clock)
    response = client.post(f"/api/life/outings/{outing['id']}/cancel", json={})
    assert response.status_code == 200, response.text
    advance(client, clock)
    found = meetups(client)
    assert [row['status'] for row in found] == ['dropped', 'planned']
    assert found[1]['due_on'] == (clock.now().date() + timedelta(days=their_people.AGAIN_AFTER)).isoformat()
    with client.app.state.database.connect() as connection:
        assert many(connection, 'SELECT * FROM people_impressions') == []


def test_together_for_years_everyone_knows_you_already(client, provider, clock):
    make(client, history_together='We have been married for ten years.')
    advance(client, clock)
    assert meetups(client) == []
    with client.app.state.database.connect() as connection:
        rows = many(connection, 'SELECT * FROM people_impressions')
    assert rows and all(row['met_on'] == 'before' for row in rows)
    says(provider)
    send(client, 'hey', 'client-people-4')
    assert 'has known the user for a long time' in prompt(provider)


def test_a_best_friend_has_you_out_with_their_friends_now_and_then(client, clock, invites, monkeypatch):
    make(client, relationship='friendship', roles=['close friend', 'friend', 'mom'], starting_closeness=5,
         home_city='Baltimore')
    set_step(client, 'best_friends')
    monkeypatch.setattr(consequences, 'roll', lambda _seed, found: found[-1]['option'])
    advance(client, clock)
    [planned] = meetups(client)
    assert planned['kind'] == 'friends' and planned['why'] == 'friends' and planned['consequence_id']
    clock.advance(timedelta(days=11))
    trigger, outing = invite(client, clock)
    assert 'come out with your close friend' in trigger.reason
    assert outing['activity'] == 'meet-friends' and outing['place']['kind'] in ('bar', 'nightlife', 'tavern')
    assert [person['role'] for person in outing['place']['people']] == ['close friend', 'friend']
    assert not outing['place']['first']


def test_impressions_move_with_what_happens(client, clock, invites, monkeypatch):
    make(client)
    set_step(client, 'their_people')
    advance(client, clock)
    clock.advance(timedelta(days=7))
    _trigger, outing = invite(client, clock)
    at(clock, outing, '23:00')
    advance(client, clock)

    def warmth():
        with client.app.state.database.connect() as connection:
            return {row['person_id']: row['warmth'] for row in many(connection, 'SELECT * FROM people_impressions')}
    before = warmth()
    monkeypatch.setattr(their_people, 'since_then', lambda *_args: {'kept': 2, 'called_off': 0, 'patches': 0})
    clock.advance(timedelta(days=3))
    advance(client, clock)
    assert warmth() == before  # Checked once a week.
    clock.advance(timedelta(days=5))
    advance(client, clock)
    assert warmth() == {key: min(value + 1, their_people.HIGH) for key, value in before.items()}
    monkeypatch.setattr(their_people, 'since_then', lambda *_args: {'kept': 0, 'called_off': 0, 'patches': 1})
    clock.advance(timedelta(days=8))
    advance(client, clock)
    # A rough patch cools family, who are touchy about it.
    assert warmth() == {key: max(min(value + 1, their_people.HIGH) - 1, their_people.LOW) for key, value in before.items()}
    with client.app.state.database.connect() as connection:
        row = optional(connection, 'SELECT * FROM people_impressions LIMIT 1')
    assert [move['why'] for move in decode(row['moves'])][-1] == 'a rough patch'


def test_the_user_can_change_a_first_impression(client, clock, invites):
    make(client)
    show(client, show_odds=True)
    set_step(client, 'their_people')
    advance(client, clock)
    clock.advance(timedelta(days=7))
    invite(client, clock)
    person = next(person for person in client.get('/api/life/circle').json() if person['met'])
    consequence_id = person['met']['consequence_id']
    assert consequence_id
    response = client.post(f'/api/life/consequences/{consequence_id}/change', json={'option': 4})
    assert response.status_code == 200, response.text
    person = next(item for item in client.get('/api/life/circle').json() if item['id'] == person['id'])
    assert person['met']['impression'] == 'wary' and person['met']['label'] == 'Not sure about you yet'


def test_someone_who_met_you_knows_it_as_a_guest(client, clock, invites):
    make(client)
    set_step(client, 'their_people')
    advance(client, clock)
    clock.advance(timedelta(days=7))
    _trigger, outing = invite(client, clock)
    at(clock, outing, '23:00')
    advance(client, clock)
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        connection.execute('UPDATE people_impressions SET impression=?, warmth=2', ('warm',))
        person_id = outing['place']['people'][0]['id']
        line = their_people.guest_line(connection, person_id, companion['active_timeline_id'])
        assert line.startswith('You have met the user in person, on ') and 'You liked them right away.' in line
        assert set(their_people.met_people(connection, companion)) == {item['id'] for item in outing['place']['people']}
        from companion import group_guests
        found = {'kind': 'circle', 'person_id': person_id, 'timeline_id': companion['active_timeline_id']}
        assert group_guests.history_line(connection, found) == line
        assert group_guests.history_line(connection, {'kind': 'town'}) == group_guests.NO_HISTORY


def test_far_apart_nothing_is_sent_and_it_stays_planned(client, clock, invites, monkeypatch):
    make(client)
    set_step(client, 'their_people')
    advance(client, clock)
    clock.advance(timedelta(days=7))
    from companion.life import long_distance
    monkeypatch.setattr(long_distance, 'far', lambda _connection, _companion: object())
    assert invite(client, clock) == (None, None)
    assert meetups(client)[0]['status'] == 'planned'


def test_family_dinner_cannot_move_elsewhere(client, clock, invites):
    make(client)
    set_step(client, 'their_people')
    advance(client, clock)
    clock.advance(timedelta(days=7))
    _trigger, outing = invite(client, clock)
    response = client.post(f"/api/life/outings/{outing['id']}/elsewhere", json={})
    assert response.status_code == 409
    assert outings.what(outing).startswith('dinner at ')
