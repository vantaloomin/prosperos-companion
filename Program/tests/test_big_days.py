"""Big days in the circle (companion/life/big_days.py): where big days come from, the invitation, saying no, the day
itself and what it changes, the gift and a friend's own wedding."""
import re
import string
from datetime import date, datetime, timedelta

import pytest
from conftest import send

from companion.characters import current
from companion.database import decode, encode, one, optional
from companion.life import ages, big_days, circle, long_distance, love_life, money, outings, steps, trips
from companion.memory import context
from companion.providers.chat import Chunk

ROLES = ['mom', 'brother', 'close friend', 'friend', 'cousin']


@pytest.fixture(autouse=True)
def on(monkeypatch):
    monkeypatch.setattr(big_days, 'ACTIVE', True)
    monkeypatch.setattr(big_days, 'FIRST_TEXTS', True)


def make(client, relationship='romance', **values):
    response = client.post('/api/companion', json={'name': 'Mira Costa', 'timezone': 'UTC', 'home_city': 'Baltimore',
                                                     'relationship': relationship, **values})
    assert response.status_code == 200, response.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    assert client.get('/api/life/circle').status_code == 200
    with client.app.state.database.connect(write=True) as connection:
        rows = circle.people(connection, current(connection)['active_timeline_id'])
        for row, role in zip(rows, ROLES, strict=False):
            details = {**decode(row['details']), 'local': True}
            connection.execute('UPDATE circle_people SET role=?, details=? WHERE id=?', (role, encode(details), row['id']))
        for row in rows[len(ROLES):]:
            connection.execute("UPDATE circle_people SET status='removed' WHERE id=?", (row['id'],))


def person(client, role):
    with client.app.state.database.connect() as connection:
        return next(row for row in circle.people(connection, current(connection)['active_timeline_id'])
                    if row['role'] == role)


def set_details(client, person_id, **values):
    with client.app.state.database.connect(write=True) as connection:
        row = one(connection, 'SELECT details FROM circle_people WHERE id=?', (person_id,))
        connection.execute('UPDATE circle_people SET details=? WHERE id=?',
                           (encode({**decode(row['details']), **values}), person_id))


def guests(client, level):
    with client.app.state.database.connect(write=True) as connection:
        connection.execute('UPDATE life_settings SET guests_realism=? WHERE id=1', (level,))


def add(client, clock, kind='wedding', role='brother', days=30, source='test:1', **details):
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        row = person(client, role) if role else None
        day = clock.now().date() + timedelta(days=days)
        found = big_days.candidate(kind, source, row, day, **details)
        return big_days.add(connection, companion, found, clock.now())


def invite(client, clock, key='bigday-message', ask=True):
    """The invitation due now, saved the way openers.py saves it (ask: the engine's roll came out as asking you)."""
    from companion.life import openers
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        if ask:
            connection.execute("UPDATE big_days SET invite=1 WHERE status='planned'")
        found = [trigger for trigger in openers.candidates(connection, companion, clock.now())
                 if trigger.kind == 'big_day']
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
        outing = big_days.settle(connection, companion, {'id': key}, trigger, clock.now().isoformat())
        return trigger, outing


def advance(client, clock):
    with client.app.state.database.connect(write=True) as connection:
        big_days.advance(connection, current(connection), clock.now())


def row_of(client, row_id):
    with client.app.state.database.connect() as connection:
        return big_days.get(connection, row_id)


def lines(client, clock):
    with client.app.state.database.connect() as connection:
        return [text for _key, text in big_days.context_lines(connection, current(connection), clock.now())]


def at(clock, day: str, hour_minute: str):
    hours, minutes = map(int, hour_minute.split(':'))
    target = datetime.combine(date.fromisoformat(day), datetime.min.time(), clock.now().tzinfo)
    clock.advance(target + timedelta(hours=hours, minutes=minutes) - clock.now())


def prompt(provider):
    request = provider.requests[-1]
    return request['prompt'] + ''.join(message['content'] for message in request.get('messages', ()))


def says(provider, text='Okay!'):
    provider.replies.append([Chunk(text), Chunk('', 'stop')])


def test_the_banks_have_enough_lines_with_their_places():
    bank = big_days.bank()
    for kind in ('wedding', 'birthday', 'retirement', 'graduation', 'wedding_modern', 'birthday_modern'):
        gifts = bank['gifts'][kind]
        assert len(gifts) >= 100 and len(set(gifts)) == len(gifts)
        assert all(gift[:1].islower() and not gift.endswith('.') for gift in gifts), kind
    wanted = {'invite': {'event', 'day', 'time', 'place'}, 'stand_up': {'partner', 'day', 'place'},
              'buzz_before': {'event', 'host'}, 'buzz_after': {'event', 'host'}, 'captions': set()}
    for key, names in wanted.items():
        found = bank[key]
        assert len(found) >= 100 and len(set(found)) == len(found), key
        for line in found:
            assert {name for _text, name, _spec, _conv in string.Formatter().parse(line) if name} == names, line
            assert not re.search(r'\b(?:he|she|him|her|his|hers)\b', line, re.IGNORECASE), line
    assert all(kind.gift is None or kind.gift in bank['gifts'] for kind in big_days.KINDS.values())


def test_a_big_day_gets_a_place_a_gift_an_outfit_and_the_engine_decides_whether_you_come(client, clock):
    make(client)
    guests(client, 3)
    row = add(client, clock)
    assert row['kind'] == 'wedding' and row['status'] == 'planned' and row['details']['role'] == 'brother'
    assert row['place']['name'] and not row['place']['id'].startswith('~')
    assert row['gift'] in big_days.bank()['gifts']['wedding_modern'] and row['gift_cost'] > 0
    assert row['gift_on'] == (date.fromisoformat(row['local_date']) - timedelta(days=7)).isoformat()
    assert row['invite'] in (0, 1) and row['consequence_id']  # The engine's roll.
    assert date.fromisoformat(row['invite_on']) <= date.fromisoformat(row['local_date']) - timedelta(days=14)
    assert add(client, clock) is None  # Once per source.
    with client.app.state.database.connect() as connection:
        outcome = optional(connection, 'SELECT * FROM consequences WHERE id=?', (row['consequence_id'],))
    assert outcome['choice'] == big_days.INVITE and 'often' in outcome['options']
    [line] = lines(client, clock)
    assert "your brother" in line.lower() and "wedding is on" in line and "You're bringing" in line


def test_with_guests_set_to_never_they_go_on_their_own(client, clock):
    make(client)
    guests(client, 0)
    row = add(client, clock)
    assert row['invite'] == 0
    clock.advance(timedelta(days=20))
    assert invite(client, clock, ask=False) == (None, None)
    assert "You're going on your own." in lines(client, clock)[0]


def test_the_invitation_books_the_day_with_you_as_their_plus_one(client, clock, provider):
    make(client)
    guests(client, 3)
    row = add(client, clock)
    at(clock, row['invite_on'], '12:00')
    trigger, outing = invite(client, clock)
    assert trigger and 'plus-one' in trigger.reason and row['place']['name'] in trigger.template
    assert '{' not in trigger.template and 'my brother' in trigger.template.lower()
    assert outing['activity'] == big_days.ACTIVITY and outing['place']['big_day'] == row['id']
    assert outing['place']['title'].endswith("'s wedding") and outing['cost'] == 0
    booked = row_of(client, row['id'])
    assert booked['status'] == 'invited' and booked['outing_id'] == outing['id']
    assert 'The user is coming with you as your plus-one.' in lines(client, clock)[0]
    says(provider)
    send(client, 'I would love to come!', 'client-bigday-1')
    assert row_of(client, row['id'])['status'] == 'invited'
    assert 'Big days in your circle' in prompt(provider)


def test_saying_no_is_fine_and_remembered(client, clock, provider):
    make(client)
    guests(client, 3)
    row = add(client, clock)
    at(clock, row['invite_on'], '12:00')
    _trigger, outing = invite(client, clock)
    says(provider)
    send(client, "No, sorry, I can't make it that day.", 'client-bigday-no')
    found = row_of(client, row['id'])
    assert found['status'] == 'declined' and found['answered_at']
    with client.app.state.database.connect() as connection:
        assert outings.get(connection, outing['id'])['status'] == 'cancelled'
    assert "can't make it, and that's completely fine" in lines(client, clock)[0]
    at(clock, row['local_date'], '12:00')
    clock.advance(timedelta(days=1))
    advance(client, clock)
    done = row_of(client, row['id'])
    assert done['status'] == 'done' and done['with_user'] == 0
    assert "on your own; the user couldn't make it, and that was fine" in lines(client, clock)[0]
    with client.app.state.database.connect() as connection:
        assert decode(one(connection, 'SELECT details FROM circle_people WHERE id=?',
                          (row['person_id'],))['details'])['married'] is True


def test_calling_it_off_on_today_is_a_no_too(client, clock):
    make(client)
    guests(client, 3)
    row = add(client, clock)
    at(clock, row['invite_on'], '12:00')
    _trigger, outing = invite(client, clock)
    response = client.post(f"/api/life/outings/{outing['id']}/cancel", json={})
    assert response.status_code == 200, response.text
    advance(client, clock)
    assert row_of(client, row['id'])['status'] == 'declined'
    elsewhere = client.post(f"/api/life/outings/{outing['id']}/elsewhere", json={})
    assert elsewhere.status_code == 409


def test_the_day_itself_is_in_person_and_afterwards_it_is_kept(client, clock, provider):
    make(client)
    guests(client, 3)
    row = add(client, clock, kind='retirement', role='mom')
    at(clock, row['invite_on'], '12:00')
    _trigger, outing = invite(client, clock)
    at(clock, row['local_date'], '19:30')
    says(provider)
    send(client, 'this is such a nice party', 'client-bigday-there')
    text = prompt(provider)
    assert "your mom" in text.lower() and 'retirement party' in text and 'The user is here with you, your plus-one.' in text
    with client.app.state.database.connect() as connection:
        assert row['person_id'] in big_days.people_there(connection, row['timeline_id'], clock.now())
    at(clock, row['local_date'], '23:00')
    with client.app.state.database.connect(write=True) as connection:
        outings.finish_due(connection, current(connection), clock.now())
    advance(client, clock)
    done = row_of(client, row['id'])
    assert done['status'] == 'done' and done['with_user'] == 1
    with client.app.state.database.connect() as connection:
        details = decode(one(connection, 'SELECT details FROM circle_people WHERE id=?', (row['person_id'],))['details'])
        memory = optional(connection, 'SELECT * FROM memories WHERE id=(SELECT memory_id FROM outings WHERE id=?)',
                          (outing['id'],))
    assert details['career'] == 'Retired'
    assert memory and 'retirement party' in memory['subject']
    assert 'you and the user went to' in lines(client, clock)[0]


def test_the_gift_is_paid_from_their_money(client, clock):
    make(client)
    client.get('/api/life/home')
    row = add(client, clock)
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        day = date.fromisoformat(row['gift_on'])
        bought = big_days.purchases(connection, companion['active_timeline_id'], day - timedelta(days=1), day)
        home = money.household(connection, companion['active_timeline_id'], companion['version']['definition'], day)
    assert bought == [{'text': f"bought {row['gift']} as a gift", 'date': row['gift_on'], 'spend': '',
                       'cost': row['gift_cost'], 'for': 'gift'}]
    assert any(item['for'] == 'gift' for item in home['purchases'])


def test_a_person_who_leaves_the_circle_calls_it_off(client, clock):
    make(client)
    row = add(client, clock)
    with client.app.state.database.connect(write=True) as connection:
        connection.execute("UPDATE circle_people SET status='removed' WHERE id=?", (row['person_id'],))
    advance(client, clock)
    assert row_of(client, row['id'])['status'] == 'called_off'


def test_a_siblings_engagement_storyline_becomes_a_wedding_next_year(client, clock):
    make(client)
    brother = person(client, 'brother')
    today = clock.now().date()
    stages = [{'on': (today - timedelta(days=20)).isoformat(), 'text': 'engaged', 'share': '', 'tone': 'good'},
              {'on': (today - timedelta(days=5)).isoformat(), 'text': 'a date', 'share': '', 'tone': 'good'}]
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        connection.execute("INSERT INTO storylines (id, timeline_id, story, level, cast_ids, stages, started_on, status, "
                           "created_at) VALUES ('story-1', ?, 'sibling_engaged', 0, ?, ?, ?, 'ended', ?)",
                           (companion['active_timeline_id'], encode([brother['id']]), encode(stages), stages[0]['on'],
                            clock.now().isoformat()))
        people = {row['id']: row for row in circle.people(connection, companion['active_timeline_id'])}
        [found] = big_days.sibling_weddings(connection, companion, today, people, clock.now())
    assert found['kind'] == 'wedding' and found['person_id'] == brother['id']
    assert found['day'].year == today.year + 1 and found['day'].weekday() == 5 and 4 <= found['day'].month <= 9


def test_milestone_birthdays_retirements_and_graduations_come_from_the_circle(client, clock):
    make(client)
    today = clock.now().date()
    mom, cousin, friend = person(client, 'mom'), person(client, 'cousin'), person(client, 'friend')
    set_details(client, mom['id'], career='Nurse')
    set_details(client, friend['id'], career='College student')
    with client.app.state.database.connect(write=True) as connection:
        for row, age in ((mom, 70), (cousin, 40), (friend, 23)):
            birthday = big_days.next_birthday(row['id'], today)
            connection.execute("INSERT INTO birth_dates (kind, person_key, born_on, birthday, from_age, anchored_on, "
                               "created_at, updated_at) VALUES ('circle', ?, ?, ?, 18, ?, ?, ?)",
                               (row['id'], ages.birthday_in(birthday.year - age, circle.birthday(row['id'])).isoformat(),
                                circle.birthday(row['id']), today.isoformat(), clock.now().isoformat(),
                                clock.now().isoformat()))
        companion = current(connection)
        people = {row['id']: row for row in circle.people(connection, companion['active_timeline_id'])}
        birthdays = big_days.milestone_birthdays(connection, companion, today, people, clock.now())
        retiring = big_days.retirements(connection, companion, today, people, clock.now())
        graduating = big_days.graduations(connection, companion, today, people, clock.now())
    by_person = {found['person_id']: found for found in birthdays}
    assert by_person[mom['id']]['details']['age'] == 70 and by_person[cousin['id']]['details']['age'] == 40
    assert by_person[cousin['id']]['day'].weekday() >= 4
    # The rest of the circle is seeded at random, so only the people set up here are checked.
    retired = {found['person_id']: found for found in retiring}
    assert mom['id'] in retired and retired[mom['id']]['day'].weekday() == 4
    graduate = {found['person_id']: found for found in graduating}
    assert friend['id'] in graduate and mom['id'] not in graduate
    assert graduate[friend['id']]['day'].month in (5, 6) and graduate[friend['id']]['day'].weekday() == 5


def test_friends_marry_by_their_love_life(client, clock, monkeypatch):
    make(client)
    friend = person(client, 'close friend')
    set_details(client, friend['id'], age=30)
    monkeypatch.setattr(big_days, 'FRIEND_RATE', (0.0, 1.0, 1.0, 1.0))
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        people = {row['id']: row for row in circle.people(connection, companion['active_timeline_id'])}
        found = big_days.friend_weddings(connection, companion, clock.now().date(), people, clock.now())
        connection.execute('UPDATE life_settings SET love_life=0 WHERE id=1')
        none = big_days.friend_weddings(connection, companion, clock.now().date(), people, clock.now())
    mine = [item for item in found if item['person_id'] == friend['id']]
    assert mine and all(item['details']['engaged_on'] <= clock.now().date().isoformat() for item in mine)
    assert none == []


def test_a_friends_own_wedding_has_you_standing_up_and_makes_them_married(client, clock, provider, monkeypatch):
    make(client, relationship='friendship')
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        today = clock.now().date()
        steps.insert_step(connection, companion['active_timeline_id'], 'friendship', 'best_friends', today, 'set',
                          clock.now().isoformat())
        partner_id = love_life.insert(connection, companion, 'Sam Reyes', {'pronouns': 'they/them'}, today,
                                      clock.now())
        for step in ('exclusive', 'love', 'their_people', 'key', 'moving_in', 'engaged'):
            steps.insert_step(connection, companion['active_timeline_id'], 'romance', step, today, 'them',
                              clock.now().isoformat(), other=f'love:{partner_id}')
        partner = love_life.partner(connection, partner_id)
        assert big_days.own_wedding(connection, companion, partner, today, clock.now())
        assert big_days.waiting(connection, partner)
        [row] = big_days.rows(connection, companion['active_timeline_id'])
    assert row['kind'] == 'own_wedding' and row['invite'] == 1 and row['gift'] == ''
    from companion.life import wedding
    assert row['outfit'] == wedding.attire(companion['version']['definition'], 'us')  # Their own wedding's attire.
    assert date.fromisoformat(row['local_date']) >= today + timedelta(days=30)
    at(clock, row['invite_on'], '12:00')
    trigger, outing = invite(client, clock)
    assert 'stand up with you' in trigger.reason and 'Sam' in trigger.template
    assert outing['place']['standing_up'] is True and outing['place']['title'] == "Mira's wedding"
    at(clock, row['local_date'], '23:00')
    with client.app.state.database.connect(write=True) as connection:
        outings.finish_due(connection, current(connection), clock.now())
    advance(client, clock)
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        reached = steps.reached(connection, companion['active_timeline_id'], 'romance', f'love:{partner_id}')
        found = steps.state(connection, companion, clock.now(), write=False)
        assert not big_days.waiting(connection, love_life.partner(connection, partner_id))
    assert 'married' in {item['step'] for item in reached}
    assert found['step'] == 'wedding_party'


def test_the_users_romance_never_has_a_big_day_wedding_of_their_own(client, clock):
    make(client)
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        assert not big_days.own_wedding(connection, companion, {'id': 'x', 'name': 'Sam'}, clock.now().date(),
                                        clock.now())


def test_buzz_comes_the_week_before_and_the_section_is_offered(client, clock):
    make(client)
    row = add(client, clock, days=10)
    clock.advance(timedelta(days=5))
    found = lines(client, clock)
    assert any(line.startswith('- Group chat buzz you could pass on:') and 'wedding' in line for line in found)
    with client.app.state.database.connect() as connection:
        assert 'big_days' in context.HEADINGS
        assert big_days.dressed(connection, row['timeline_id'], row['local_date']) == row['outfit']


def test_their_own_graduation_and_retirement_party_come_from_their_life_chapters(client, clock):
    make(client)
    guests(client, 3)
    today = clock.now().date()
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        for chapter_id, kind, details in (('ch-school', 'school', {'ends_on': (today + timedelta(days=20)).isoformat()}),
                                          ('ch-retire', 'retire', {'last_day': (today + timedelta(days=30)).isoformat()})):
            connection.execute("INSERT INTO life_chapters (id, timeline_id, kind, started_on, title, told, share, details, "
                               "created_at) VALUES (?, ?, ?, ?, 'A chapter', '', '', ?, ?)",
                               (chapter_id, companion['active_timeline_id'], kind, today.isoformat(), encode(details),
                                clock.now().isoformat()))
    advance(client, clock)
    with client.app.state.database.connect() as connection:
        found = {row['kind']: row for row in big_days.rows(connection, current(connection)['active_timeline_id'],
                                                           ('planned',))}
    assert {'own_graduation', 'own_retirement'} <= set(found)  # The circle's own big days may be found too.
    graduation = found['own_graduation']
    assert graduation['source'] == 'chapter:ch-school' and graduation['gift'] == '' and graduation['at_time'] == '10:00'
    assert big_days.title(graduation, 'Mira Costa') == "Mira's graduation"
    assert big_days.said(found['own_retirement']) == 'your retirement party'
    assert not any('buzz' in line and 'graduation' in line for line in lines(client, clock))
    graduation['invite'] = 1
    assert 'there with you' in big_days.reason_for(graduation, date.fromisoformat(graduation['local_date']))


def test_after_a_breakup_they_no_longer_mean_to_ask_the_user_along(client, clock, monkeypatch):
    from companion.life import breakups
    monkeypatch.setattr(breakups, 'ACTIVE', True)
    make(client)
    guests(client, 3)
    row = add(client, clock)
    with client.app.state.database.connect(write=True) as connection:
        connection.execute('UPDATE big_days SET invite=1 WHERE id=?', (row['id'],))
    assert "You mean to ask the user to come with you as your plus-one" in lines(client, clock)[0]
    send(client, "I'm sorry, I think we should break up.", 'client-bigday-breakup')
    [line] = lines(client, clock)
    assert 'mean to ask the user' not in line and "You're going on your own." in line


def test_taking_back_cant_make_it_on_today_means_you_are_coming_after_all(client, clock):
    make(client)
    guests(client, 3)
    row = add(client, clock)
    at(clock, row['invite_on'], '12:00')
    _trigger, outing = invite(client, clock)
    assert client.post(f"/api/life/outings/{outing['id']}/cancel", json={}).status_code == 200
    assert row_of(client, row['id'])['status'] == 'declined'
    assert client.post(f"/api/life/outings/{outing['id']}/undo", json={}).status_code == 200
    advance(client, clock)
    found = row_of(client, row['id'])
    assert found['status'] == 'invited' and found['answered_at'] is None
    # The circle's own big days may come first: find this one's line.
    assert any(found['place']['name'] in line and 'The user is coming with you as your plus-one.' in line
               for line in lines(client, clock))


def test_long_distance_the_day_is_a_stay_and_undoing_the_no_brings_it_back(client, clock, monkeypatch):
    monkeypatch.setattr(trips, 'ACTIVE', True)
    for name in ('CHANCE', 'LONG_CHANCE'):
        monkeypatch.setattr(trips, name, 0.0)
    monkeypatch.setattr(long_distance, 'CHANCE', {1: 0.0, 2: 0.0, 3: 0.0})
    make(client, home_city='Chicago', timezone='America/Chicago')
    world = client.get('/api/worlds').json()['world']
    assert client.put(f"/api/worlds/{world['id']}/home", json={'city_id': 'baltimore'}).status_code == 200
    guests(client, 3)
    row = add(client, clock)
    at(clock, row['invite_on'], '18:00')
    _trigger, outing = invite(client, clock)

    def stays():
        return [trip['status'] for trip in client.get('/api/life/outings').json()['trips'] if trip['visit'] == 'host']
    assert stays() == ['planned']
    assert client.post(f"/api/life/outings/{outing['id']}/cancel", json={}).status_code == 200
    assert stays() == ['cancelled'] and row_of(client, row['id'])['status'] == 'declined'
    assert client.post(f"/api/life/outings/{outing['id']}/undo", json={}).status_code == 200
    advance(client, clock)
    assert stays() == ['planned'] and row_of(client, row['id'])['status'] == 'invited'


def test_moving_apart_after_saying_yes_plans_a_stay_and_keeps_the_day(client, clock, monkeypatch):
    monkeypatch.setattr(trips, 'ACTIVE', True)
    for name in ('CHANCE', 'LONG_CHANCE'):
        monkeypatch.setattr(trips, name, 0.0)
    monkeypatch.setattr(long_distance, 'CHANCE', {1: 1.0, 2: 1.0, 3: 1.0})
    make(client, home_city='Chicago', timezone='America/Chicago')
    guests(client, 3)
    row = add(client, clock)
    at(clock, row['invite_on'], '18:00')
    _trigger, outing = invite(client, clock)
    world = client.get('/api/worlds').json()['world']
    assert client.put(f"/api/worlds/{world['id']}/home", json={'city_id': 'baltimore'}).status_code == 200
    with client.app.state.database.connect(write=True) as connection:
        long_distance.settle_moves(connection, current(connection), clock.now().date(), clock.now())
    advance(client, clock)
    found = row_of(client, row['id'])
    with client.app.state.database.connect() as connection:
        kept = outings.get(connection, outing['id'])
        stay = one(connection, 'SELECT * FROM trips WHERE id=?', (found['trip_id'],))
    assert found['status'] == 'invited' and kept['status'] == 'planned' and kept['local_date'] == row['local_date']
    assert stay['status'] == 'planned' and stay['start_date'] <= row['local_date'] <= stay['end_date']


def branch_at(client, message_id, **body):
    branch = client.post('/api/timelines', json={'message_id': message_id, **body}).json()
    assert client.post(f"/api/timelines/{branch['id']}/activate").status_code == 200
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        return companion, big_days.rows(connection, branch['id'])


def test_a_branch_keeps_whose_day_it_is_and_what_you_said_and_never_plans_it_twice(client, clock, provider):
    from companion.life import openers
    make(client)
    guests(client, 3)
    mom = person(client, 'mom')
    row = add(client, clock, kind='birthday', role='mom', source=f"birthday:{mom['id']}:2099", age=60)
    at(clock, row['invite_on'], '12:00')
    _trigger, outing = invite(client, clock)
    says(provider)
    yes = send(client, 'Yes! I would love to come', 'client-bigday-branch-yes')
    companion, copies = branch_at(client, yes['message']['id'] if 'message' in yes else yes['id'])
    [copied] = [item for item in copies if item['local_date'] == row['local_date'] and item['kind'] == 'birthday']
    with client.app.state.database.connect(write=True) as connection:
        mine = optional(connection, "SELECT * FROM circle_people WHERE timeline_id=? AND role='mom'",
                        (companion['active_timeline_id'],))
        assert copied['person_id'] == mine['id'] and copied['source'] == f"birthday:{mine['id']}:2099"
        assert copied['status'] == 'invited' and copied['outing_id'] == outing['id']
        assert not [item for item in openers.candidates(connection, companion, clock.now()) if item.kind == 'big_day']
        again = big_days.candidate('birthday', f"birthday:{mine['id']}:2099", mine, date.fromisoformat(row['local_date']))
        assert big_days.add(connection, companion, again, clock.now()) is None


def test_a_branch_from_before_your_no_has_you_coming(client, clock, provider):
    make(client)
    guests(client, 3)
    row = add(client, clock)
    at(clock, row['invite_on'], '12:00')
    _trigger, outing = invite(client, clock)
    says(provider)
    no = send(client, "No, sorry, I can't make it that day.", 'client-bigday-branch-no')
    assert row_of(client, row['id'])['status'] == 'declined'
    companion, copies = branch_at(client, no['message']['id'] if 'message' in no else no['id'],
                                  text='Yes! I would love to come')
    [copied] = [item for item in copies if item['source'] == row['source']]
    assert copied['status'] == 'invited' and copied['outing_id'] != outing['id']
    advance(client, clock)
    with client.app.state.database.connect() as connection:
        mine = outings.get(connection, big_days.get(connection, copied['id'])['outing_id'])
        assert big_days.get(connection, copied['id'])['status'] == 'invited' and mine['status'] == 'planned'
        assert mine['place']['big_day'] == copied['id']
        assert outings.get(connection, outing['id'])['status'] == 'cancelled'  # The parent keeps its no.


def test_a_big_day_held_after_the_fork_is_still_to_come_on_the_copy():
    row = {'status': 'done', 'local_date': '2027-05-01', 'message_id': None, 'answered_at': None}
    assert big_days.copied_status(row, {}, '2027-04-20T10:00:00+00:00') == ('planned', None)
    assert big_days.copied_status(row, {}, '2027-05-02T10:00:00+00:00') == ('done', None)
    asked = {**row, 'message_id': 'm', 'answered_at': '2027-04-25T10:00:00+00:00'}
    assert big_days.copied_status(asked, {'m': 'm2'}, '2027-04-20T10:00:00+00:00') == ('invited', 'm2')
    assert big_days.copied_status(asked, {'m': 'm2'}, '2027-04-26T10:00:00+00:00') == ('declined', 'm2')


def agenda_at(client, clock):
    from companion.life import agenda
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        agenda.extend(connection, companion, client.app.state.life.world, clock.now())
        found = optional(connection, "SELECT block, entry FROM life_agenda WHERE timeline_id=? AND subject='companion' "
                         'AND starts_at<=? AND ends_at>?', (companion['active_timeline_id'], clock.now().isoformat(),
                                                           clock.now().isoformat()))
    return decode(found['block']), decode(found['entry']) if found['entry'] else None


def test_going_on_their_own_is_in_their_day(client, clock):
    make(client)
    guests(client, 0)
    row = add(client, clock)
    at(clock, row['local_date'], '16:00')
    _block, entry = agenda_at(client, clock)
    assert entry['activity'] == big_days.ACTIVITY and entry['big_day']['id'] == row['id']
    assert f"went to {big_days.title(row)} at {row['place']['name']}" in entry['summary']


WORK = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00', 'days': [0, 1, 2, 3, 4, 5, 6]},
        {'key': 'evening', 'label': 'Evening', 'kind': 'leisure', 'start': '17:00', 'end': '23:00'},
        {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'},
        {'key': 'morning', 'label': 'Morning', 'kind': 'leisure', 'start': '07:00', 'end': '09:00'}]


def test_a_big_day_in_working_hours_is_a_day_off_for_it(client, clock, monkeypatch):
    from companion.life import body
    monkeypatch.setattr(body, 'sick', lambda *args: False)  # A seeded cold (by the random timeline id) would keep them home.
    make(client, schedule=WORK)
    guests(client, 3)
    row = add(client, clock)  # 15:00 to 22:00, in the middle of their shift.
    party = add(client, clock, kind='birthday', role='mom', source='test:2', days=60, age=60)  # 19:00: after work.
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        off = big_days.days_off(connection, companion, clock.now().date(), clock.now().date() + timedelta(days=90))
    assert off == {row['local_date']: big_days.title(row)}
    at(clock, row['invite_on'], '12:00')
    _trigger, outing = invite(client, clock)
    at(clock, row['local_date'], '15:30')
    block, entry = agenda_at(client, clock)
    assert block['kind'] == 'leisure' and block['label'] == f"{big_days.title(row)} (day off)"
    assert entry['outing']['id'] == outing['id']
    assert party['local_date'] not in off


def test_in_an_old_city_the_invitation_and_caption_have_no_cars_texts_or_photos(client, clock):
    client.post('/api/companion', json={'name': 'Elayne', 'timezone': 'Europe/London', 'home_city': 'Camelot'})
    client.get('/api/life/circle')
    row = add(client, clock, role=None, source='test:camelot', name='Cynan Ap Rhys')
    assert row['place']['modern'] is False
    for number in range(200):
        found = {**row, 'id': f'seed-{number}'}
        for kind in ('wedding', 'own_wedding', 'funeral'):
            text = big_days.invitation({**found, 'kind': kind}, 'Saturday', '3')
            assert not big_days.MODERN_ONLY.search(text), text
        assert not big_days.MODERN_ONLY.search(big_days.caption({'id': f'o-{number}', 'place': row['place']}))
    modern = {**row['place'], 'modern': True}
    assert any(big_days.MODERN_ONLY.search(big_days.caption({'id': f'o-{number}', 'place': modern}))
               for number in range(400))


def test_a_party_is_somewhere_open_at_its_hour(client, clock):
    make(client)
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        data = outings.city_data(connection, companion['version']['definition'])
        day = clock.now().date() + timedelta(days=30)
        for key, part in (('birthday', 'evening'), ('retirement', 'evening'), ('graduation', 'morning')):
            for number in range(60):
                found = big_days.place_for(connection, companion, big_days.KINDS[key], day, f'seed-{number}', {})
                place = next(item for item in data['places'] if item['id'] == found['id'])
                assert part in place['day_parts'], (key, place['name'], place['day_parts'])


def test_the_invitation_names_a_day_weeks_off_by_its_date():
    tuesday = date(2026, 10, 20)
    assert big_days.when_text(date(2026, 10, 24), tuesday) == 'Saturday'
    assert big_days.when_text(date(2026, 10, 31), tuesday) == 'next Saturday'
    assert big_days.when_text(date(2026, 11, 14), tuesday) == 'Saturday, November 14'


def test_next_saturday_starting_a_sentence_has_a_capital():
    for kind in ('birthday', 'own_wedding'):
        for number in range(100):
            row = {'id': f'row-{number}', 'kind': kind, 'place': {'name': 'Ouzo Bay', 'modern': True},
                   'details': {'name': 'James Hill', 'role': 'dad', 'age': 60}, 'title': "James's 60th birthday party"}
            line = big_days.invitation(row, 'next Saturday', '7')
            assert not re.search(r'(^|[.?!] )next Saturday', line), line


def test_the_day_with_you_reads_with_you_last(client, clock):
    make(client)
    guests(client, 3)
    row = add(client, clock, kind='retirement', role='mom')
    at(clock, row['invite_on'], '12:00')
    _trigger, outing = invite(client, clock)
    outing = {**outing, 'place': {**outing['place'], 'neighborhood': 'Fells Point'}}
    found = outings.entry({'outing': outing}, {}, {'name': 'Mira'})
    assert found['summary'].startswith(f"Mira went to {outing['place']['title']} at {outing['place']['name']} with you")
    assert 'Fells Point' not in found['summary']


def test_in_1895_a_parent_is_mother_or_father(client, clock):
    client.post('/api/companion', json={'name': 'Ada Lowe', 'timezone': 'Europe/London', 'home_city': 'london-1895'})
    client.get('/api/life/circle')
    with client.app.state.database.connect(write=True) as connection:
        row = circle.people(connection, current(connection)['active_timeline_id'])[0]
        connection.execute("UPDATE circle_people SET role='mom' WHERE id=?", (row['id'],))
    found = add(client, clock, kind='birthday', role='mom', age=60)
    assert found['details']['role'] == 'mother' and 'your mother' in big_days.said(found)


def test_a_parent_is_mom_or_dad_on_the_day_like_everyone_else(client, clock):
    make(client)
    with client.app.state.database.connect(write=True) as connection:
        row = circle.people(connection, current(connection)['active_timeline_id'])[0]
        details = decode(row['details']) or {}
        connection.execute("UPDATE circle_people SET role='parent', details=? WHERE id=?",
                           (encode({**details, 'pronouns': 'she/her'}), row['id']))
    found = add(client, clock, kind='birthday', role='parent', age=60)
    assert found['details']['role'] == 'mom' and 'your mom' in big_days.said(found)
    assert big_days.host(found)['role'] == 'mom'  # Today's "With Tracy (mom)".


def test_before_asking_their_own_day_is_never_a_plus_one():
    row = {'kind': 'own_wedding', 'status': 'planned', 'invite': 1, 'local_date': '2027-02-20', 'at_time': '15:00',
           'place': {'name': 'Royal Observatory'}, 'details': {'name': 'Sam Okafor'}, 'gift': '', 'outfit': ''}
    assert 'to stand up with you at your wedding' in big_days.coming_line(row, date(2027, 2, 1))
    for kind in ('own_graduation', 'own_retirement', 'funeral'):
        assert 'plus-one' not in big_days.coming_line({**row, 'kind': kind}, date(2027, 2, 1))
    assert 'as your plus-one' in big_days.coming_line({**row, 'kind': 'wedding', 'details': {'name': 'Leo'}},
                                                       date(2027, 2, 1))


def test_a_no_to_one_big_day_lets_the_next_one_close_by_be_asked(client, clock):
    make(client)
    guests(client, 3)
    first = add(client, clock, days=30)
    with client.app.state.database.connect(write=True) as connection:
        connection.execute('UPDATE big_days SET invite=1 WHERE id=?', (first['id'],))
    second = add(client, clock, kind='birthday', role='mom', days=36, source='test:2', age=60)
    assert second['invite'] == 0 and second['consequence_id'] is None  # Held back by the first, still to be asked.
    advance(client, clock)
    assert row_of(client, second['id'])['consequence_id'] is None
    with client.app.state.database.connect(write=True) as connection:
        connection.execute("UPDATE big_days SET status='declined' WHERE id=?", (first['id'],))
    advance(client, clock)
    assert row_of(client, second['id'])['consequence_id']  # The no doesn't hide it: the engine decides now.


def test_a_day_the_user_went_to_still_holds_the_next_back_but_not_a_funeral_in_the_family(client, clock):
    make(client)
    first = add(client, clock, days=30)
    with client.app.state.database.connect(write=True) as connection:
        connection.execute("UPDATE big_days SET invite=1, status='done', with_user=1 WHERE id=?", (first['id'],))
        near = {'id': 'near', 'timeline_id': first['timeline_id'], 'kind': 'birthday', 'details': {},
                'local_date': (date.fromisoformat(first['local_date']) + timedelta(days=5)).isoformat()}
        assert big_days.crowded(connection, near)
        assert not big_days.crowded(connection, {**near, 'kind': 'funeral', 'details': {'family': True}})
        connection.execute("UPDATE big_days SET with_user=0 WHERE id=?", (first['id'],))
        assert not big_days.crowded(connection, near)


def test_an_out_of_town_relatives_wedding_is_a_trip_you_can_come_along_to(client, clock, monkeypatch):
    make(client)
    client.get('/api/life/home')
    set_details(client, person(client, 'brother')['id'], local=False, city='')
    row = add(client, clock)
    details = row['details']
    assert details['city'] and details['city_id'] and row['place']['name'] == f"a venue in {details['city']}"
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        assert big_days.invitable(connection, companion, row)
        set_off = date.fromisoformat(row['local_date']) - timedelta(days=1)
        fares = [item for item in big_days.purchases(connection, companion['active_timeline_id'], set_off, set_off)
                 if item['for'] == 'trip']
        assert details['fare'] > 0 and fares == [{'text': f"travelled to {details['city']} for {big_days.title(row)}",
                                                  'date': set_off.isoformat(), 'spend': '', 'cost': details['fare'],
                                                  'for': 'trip'}]
        monkeypatch.setattr(long_distance, 'far', lambda *_args: object())
        assert not big_days.invitable(connection, companion, row)  # The user lives elsewhere: they go on their own.
    line = next(text for text in lines(client, clock) if 'wedding is on' in text)
    assert f"It's out of town, in {details['city']}: you travel there for it." in line
    assert "It's out of town" in big_days.coming_line({**row, 'status': 'invited'}, clock.now().date())
    assert 'the two of you together' in big_days.coming_line({**row, 'status': 'invited'}, clock.now().date())


def coffee(client, clock, day, key):
    """An outing with the user booked for that day."""
    from companion.life import together
    place = {'id': 'cafe', 'name': 'Daily Grind', 'kind': 'cafe', 'neighborhood': ''}
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        connection.execute("INSERT INTO messages (id, timeline_id, seq, role, text, status, active, character_version_id, "
                           "memory_revision, created_at, completed_at) VALUES (?, ?, ?, 'companion', 'Coffee?', "
                           "'complete', 1, ?, 0, ?, ?)", (key, companion['active_timeline_id'], 90 + len(key),
                                                          companion['active_version_id'], clock.now().isoformat(),
                                                          clock.now().isoformat()))
        together.insert(connection, companion, key, 'coffee', place, day, '11:00', '12:00', None,
                        clock.now().isoformat())


def test_a_big_day_moves_off_a_day_an_outing_with_you_has(client, clock):
    make(client)
    guests(client, 3)
    day = clock.now().date() + timedelta(days=30)
    coffee(client, clock, day, 'm-1')
    party = add(client, clock, kind='birthday', role='mom', source='test:party', age=60)
    assert party['local_date'] == (day + timedelta(days=7)).isoformat()  # The host picked the next weekend.
    graduation = add(client, clock, kind='graduation', role='cousin', source='test:graduation')
    assert graduation['local_date'] == day.isoformat()  # Its day is its own.
    with client.app.state.database.connect(write=True) as connection:
        connection.execute('UPDATE big_days SET invite=(id=?)', (graduation['id'],))
    at(clock, graduation['invite_on'], '12:00')
    with client.app.state.database.connect() as connection:
        assert not big_days.invite_due(connection, current(connection), clock.now())  # Never to a day already taken.
    later = add(client, clock, kind='wedding', role='brother', days=60, source='test:later')
    with client.app.state.database.connect(write=True) as connection:
        connection.execute('UPDATE big_days SET invite=1 WHERE id=?', (later['id'],))
    coffee(client, clock, date.fromisoformat(later['local_date']), 'm-22')
    advance(client, clock)
    assert row_of(client, later['id'])['local_date'] == (date.fromisoformat(later['local_date']) +
                                                          timedelta(days=7)).isoformat()


def test_camelot_has_its_own_gifts_and_1895_keeps_the_timeless_ones(client, clock):
    gifts = big_days.bank()['gifts']
    for kind in ('wedding', 'birthday', 'first_birthday'):
        found = gifts[f'{kind}_old']
        assert len(found) >= 25 and len(set(found)) == len(found)
        assert not any(re.search(r'\b(?:tea|teacup|sparkling|champagne|whisky|printed|framed)\b', gift) for gift in found)
    client.post('/api/companion', json={'name': 'Elayne', 'timezone': 'Europe/London', 'home_city': 'Camelot'})
    client.get('/api/life/circle')
    row = add(client, clock, role=None, source='test:camelot', name='Cynan Ap Rhys')
    assert row['gift'] in gifts['wedding_old']
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        for number in range(40):
            gift, _cost = big_days.gift_for(connection, companion, big_days.KINDS['birthday'], f'seed-{number}')
            assert gift in gifts['birthday_old'], gift
        definition = {**companion['version']['definition'], 'home_city': 'london-1895'}
        victorian = {**companion, 'version': {**companion['version'], 'definition': definition}}
        assert {big_days.gift_for(connection, victorian, big_days.KINDS['birthday'], f'seed-{number}')[0]
                for number in range(40)} <= set(gifts['birthday'])


def test_a_friends_own_wedding_photo_has_them_in_wedding_clothes():
    from companion.images import prompts
    line = prompts.doing({'activity': big_days.PICTURED, 'summary': 'Priya got married.', 'place': 'Royal Observatory'},
                         'Priya', 'her', 'she')
    assert line == 'Priya is smiling in wedding clothes at her own wedding at Royal Observatory.'


def test_a_wedding_a_friend_went_to_is_a_big_day_not_their_own_wedding(client, clock, monkeypatch):
    from companion.life import wedding

    class Packet:
        def __init__(self):
            self.offered = []

        def offer(self, section, identity, text):
            self.offered.append((section, identity))

    make(client, 'friendship')
    monkeypatch.setattr(wedding, 'context_lines', lambda *_args: [('wedding:w1:done', '- You married the user.'),
                                                                  ('wedding-guest:w2:done:2026-10-10', '- The user '
                                                                   'married Mira on 10 October; you were there.')])
    packet = Packet()
    with client.app.state.database.connect() as connection:
        wedding.offer(packet, connection, current(connection), clock.now())
    assert packet.offered == [('wedding', 'wedding:w1:done'), ('big_days', 'wedding-guest:w2:done:2026-10-10')]


def test_the_feed_rephrase_keeps_the_user_on_a_day_together():
    from companion.life import synthesis
    assert 'when the facts say "with you", keep "with you"' in synthesis.RULES
    assert 'Never add the user' in synthesis.RULES
