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
    # In the user's city: a companion in another time zone with no city is long distance (Time zone decides).
    response = client.post('/api/companion', json={'name': 'Mira Costa', 'timezone': 'UTC', 'home_city': 'Baltimore',
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
    for kind in ('family', 'friends', 'home'):
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


def test_a_parent_with_no_family_in_town_has_their_friends_to_dinner_with_the_kids(client, provider, clock, invites,
                                                                                    monkeypatch):
    from companion.life import kids
    monkeypatch.setattr(kids, 'ACTIVE', True)
    make(client, roles=['close friend', 'friend', 'coworker'], background='Her son Leo, 7, and daughter Mia, 4.')
    set_step(client, 'their_people')
    advance(client, clock)
    assert meetups(client)[0]['kind'] == 'family'
    clock.advance(timedelta(days=7))
    trigger, outing = invite(client, clock)
    assert 'dinner at my place' in trigger.reason and 'my place' in trigger.template and '{' not in trigger.template
    assert ' (Leo and Mia will be there too): dinner at my place' in trigger.reason
    assert outing['activity'] == their_people.AT_FAMILY and outing['place']['own']
    assert outing['place']['name'] == "Mira Costa's place"
    assert [person['role'] for person in outing['place']['people']] == ['close friend', 'friend']
    at(clock, outing, '19:30')
    says(provider)
    send(client, 'hi everyone!', 'client-people-home')
    assert 'and your kids Leo and Mia. Nobody else is there.' in prompt(provider)
    clock.advance(timedelta(days=1))
    advance(client, clock)
    with client.app.state.database.connect() as connection:
        assert kids.met(connection, current(connection))


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
    # It waits as long as they live apart, never lapsing, and is sent once they live in one city.
    for _week in range(20):
        clock.advance(timedelta(days=7))
        advance(client, clock)
    assert [row['status'] for row in meetups(client)] == ['planned']
    monkeypatch.setattr(long_distance, 'far', lambda _connection, _companion: None)
    advance(client, clock)
    trigger, _outing = invite(client, clock)
    assert trigger is not None


def host_visit(client, clock, days_ahead=10, length=2):
    """The user's stay with them in their city, `days_ahead` days on."""
    from companion.life import long_distance, trips
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        today = their_people.local_today(companion, clock.now())
        start = today + timedelta(days=days_ahead)
        trips.insert(connection, companion, {
            'start_date': start.isoformat(), 'end_date': (start + timedelta(days=length)).isoformat(),
            'city_id': 'baltimore', 'city_name': 'Baltimore', 'kind': 'getaway', 'company': dict(long_distance.YOU),
            'landmark': None, 'sunny': False, 'cost': 0.0, 'visit': long_distance.HOST}, clock.now())
    return start


def test_far_apart_the_dinner_is_on_the_users_stay_with_them(client, clock, invites, monkeypatch):
    make(client)
    set_step(client, 'their_people')
    advance(client, clock)
    clock.advance(timedelta(days=7))
    from companion.life import long_distance
    monkeypatch.setattr(long_distance, 'far', lambda _connection, _companion: object())
    assert invite(client, clock) == (None, None)
    start = host_visit(client, clock)
    # Asked as soon as the stay is agreed, for its first full day.
    trigger, outing = invite(client, clock)
    assert trigger is not None and outing is not None
    assert outing['local_date'] == (start + timedelta(days=1)).isoformat()
    assert outing['activity'] == their_people.AT_FAMILY
    assert meetups(client)[0]['status'] == 'booked'


def test_family_dinner_cannot_move_elsewhere(client, clock, invites):
    make(client)
    set_step(client, 'their_people')
    advance(client, clock)
    clock.advance(timedelta(days=7))
    _trigger, outing = invite(client, clock)
    response = client.post(f"/api/life/outings/{outing['id']}/elsewhere", json={})
    assert response.status_code == 409
    assert outings.what(outing).startswith('dinner at ')


def test_a_branch_after_the_dinner_does_not_plan_it_again(client, provider, clock, invites):
    make(client)
    set_step(client, 'their_people')
    advance(client, clock)
    clock.advance(timedelta(days=7))
    _trigger, outing = invite(client, clock)
    at(clock, outing, '23:00')
    advance(client, clock)
    says(provider)
    sent = send(client, 'that was a lovely evening', 'client-people-branch')
    fork = client.post('/api/timelines', json={'message_id': sent['message']['id'], 'text': 'that was a great night'})
    assert fork.status_code == 200, fork.text
    assert client.post(f"/api/timelines/{fork.json()['id']}/activate").status_code == 200
    advance(client, clock)
    clock.advance(timedelta(days=10))
    advance(client, clock)
    # They have met everyone already: no second "first time" dinner, and where they met still reads.
    found = meetups(client)
    assert [row['status'] for row in found] == ['done']
    with client.app.state.database.connect() as connection:
        lines = their_people.context_lines(connection, current(connection), clock.now())
    assert lines and all("at dinner at " in text for _identity, text in lines)


def test_nothing_is_planned_or_sent_while_apart(client, provider, clock, invites, monkeypatch):
    from companion.life import breakups
    monkeypatch.setattr(breakups, 'ACTIVE', True)
    make(client)
    set_step(client, 'their_people')
    says(provider)
    send(client, "I'm sorry but I'm breaking up with you.", 'client-people-end')
    advance(client, clock)
    clock.advance(timedelta(days=7))
    advance(client, clock)
    # No family dinner for an ex: nothing planned, and no invitation.
    assert meetups(client) == []
    assert invite(client, clock) == (None, None)


def test_a_planned_dinner_is_not_sent_once_they_break_up(client, provider, clock, invites, monkeypatch):
    from companion.life import breakups
    monkeypatch.setattr(breakups, 'ACTIVE', True)
    make(client)
    set_step(client, 'their_people')
    advance(client, clock)
    assert len(meetups(client)) == 1
    says(provider)
    send(client, "I'm sorry but I'm breaking up with you.", 'client-people-end-2')
    clock.advance(timedelta(days=7))
    assert invite(client, clock) == (None, None)


def test_an_invitation_a_week_ahead_says_next_saturday():
    from datetime import date
    saturday, next_saturday = date(2026, 10, 31), date(2026, 11, 7)
    people = [{'name': 'Muriel', 'role': 'sister'}]
    for index in range(40):
        row = {'id': f'meetup-{index}', 'kind': 'family'}
        text = their_people.invitation(row, people, next_saturday, saturday, '6:30', "my sister's place")
        assert 'next saturday' in text.lower() and 'this next' not in text.lower() and text[0].isupper(), text
        near = their_people.invitation(row, people, next_saturday, date(2026, 11, 3), '6:30', "my sister's place")
        assert 'Saturday' in near and 'next Saturday' not in near


def test_rough_patches_over_the_same_thing_weigh_less_for_their_people(client, clock, monkeypatch):
    """Two stinging messages in a row count as one and a half, as Breaks and breakups weighs them; one the dice let go
    doesn't count."""
    from companion.life import rough_patches
    monkeypatch.setattr(rough_patches, 'ACTIVE', True)
    make(client)
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        since = (clock.now().date() - timedelta(days=1)).isoformat()
        today = clock.now().date().isoformat()
        monkeypatch.setattr(consequences, 'roll', lambda _seed, found: found[-1]['option'])
        for index in range(2):
            rough_patches.consider(connection, companion, 'words', f'words:a{index}', 'the user said: "go away"',
                                   clock.now() + timedelta(minutes=index))
        assert their_people.since_then(connection, companion, since, today)['patches'] == 1.5
        monkeypatch.setattr(consequences, 'roll', lambda _seed, found: found[0]['option'])
        rough_patches.consider(connection, companion, 'missed_plan', 'plan:b', 'the plan came and went', clock.now())
        assert their_people.since_then(connection, companion, since, today)['patches'] == 1.5


def test_after_a_breakup_their_people_cool_on_you_once(client, provider, clock, invites, monkeypatch):
    from companion.life import breakups
    monkeypatch.setattr(breakups, 'ACTIVE', True)
    make(client)
    set_step(client, 'their_people')
    advance(client, clock)
    clock.advance(timedelta(days=7))
    _trigger, outing = invite(client, clock)
    at(clock, outing, '23:00')
    advance(client, clock)
    with client.app.state.database.connect(write=True) as connection:
        connection.execute('UPDATE people_impressions SET impression=?, warmth=2', ('warm',))
    says(provider)
    send(client, "I'm sorry but I'm breaking up with you.", 'client-people-cool-1')

    def warmth():
        with client.app.state.database.connect() as connection:
            return {row['person_id']: row['warmth'] for row in many(connection, 'SELECT * FROM people_impressions')}
    for _day in range(3):
        clock.advance(timedelta(days=1))
        advance(client, clock)
    # Family cools more, and only once for the breakup.
    assert set(warmth().values()) == {0}
    labels = {person['met']['label'] for person in client.get('/api/life/circle').json() if person['met']}
    assert labels == {'Cooled on you'}
    with client.app.state.database.connect() as connection:
        assert their_people.met_people(connection, current(connection)) == {}


def test_a_pair_that_starts_at_the_step_has_met_everyone(client, clock):
    make(client)
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        from companion.life import steps
        steps.insert_step(connection, companion['active_timeline_id'], 'romance', 'their_people',
                          clock.now().date(), 'start', clock.now().isoformat())
    advance(client, clock)
    assert meetups(client) == []
    people = client.get('/api/life/circle').json()
    assert [person for person in people if person['met']] and \
        all(person['met']['before'] for person in people if person['met'])


def test_after_the_evening_it_is_told_as_over_and_a_protective_mom_keeps_her_edge(client, provider, clock, invites):
    make(client)
    set_step(client, 'their_people')
    advance(client, clock)
    clock.advance(timedelta(days=7))
    _trigger, outing = invite(client, clock)
    at(clock, outing, '22:30')
    advance(client, clock)
    with client.app.state.database.connect(write=True) as connection:
        connection.execute("UPDATE people_impressions SET impression='protective', warmth=0")
    says(provider)
    send(client, 'what did your mom think of me?', 'client-people-after-1')
    text = prompt(provider)
    assert 'so the user could meet them; it is over now' in text and 'so the user can meet them' not in text
    assert 'was polite but protective of you, and is still watching how the user treats you; pass that on ' \
        "honestly, even if it isn't all glowing" in text


def test_in_a_group_another_companion_knows_they_were_not_at_the_dinner(client, provider, clock, invites):
    from test_groups import companion_named

    from companion import groups
    make(client)
    set_step(client, 'their_people')
    advance(client, clock)
    clock.advance(timedelta(days=7))
    _trigger, outing = invite(client, clock)
    at(clock, outing, '23:00')
    advance(client, clock)
    elaine = companion_named(client, 'Elaine Brooks')
    with client.app.state.database.connect() as connection:
        mira = current(connection)
    group = client.post('/api/groups', json={'companion_ids': [mira['id'], elaine]}).json()
    with client.app.state.database.connect() as connection:
        members = groups.current_members(connection, group['id'])
        stay = next(item for item in members if item['member'] == groups.member_key(elaine))
        lines = [text for _key, text in groups.group_lines(connection, group, stay, clock.now())]
        mira_stay = next(item for item in members if item['member'] == groups.member_key(mira['id']))
        own = [text for _key, text in groups.group_lines(connection, group, mira_stay, clock.now())]
    [line] = [text for text in lines if "you weren't there" in text]
    assert line.startswith("Mira took the user to dinner at ") and 'their mom' in line
    assert not any("you weren't there" in text for text in own)


def test_the_invitation_to_the_family_dinner_names_their_kids_but_not_with_the_adult_side_on(client, clock, invites,
                                                                                               monkeypatch):
    from companion.life import kids
    monkeypatch.setattr(kids, 'ACTIVE', True)
    make(client, background='Her son Leo, 7.')
    set_step(client, 'their_people')
    advance(client, clock)
    clock.advance(timedelta(days=7))
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        assert their_people.kids_coming(connection, companion) == ' (Leo will be there too)'
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    with client.app.state.database.connect(write=True) as connection:
        assert their_people.kids_coming(connection, current(connection)) == ''
    trigger, _outing = invite(client, clock)
    assert 'Leo' not in trigger.reason
