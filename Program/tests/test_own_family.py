"""Companions' own babies (companion/life/own_family.py): a friend and their own partner start a family, in words
only."""
import re
import string
from datetime import date, timedelta

import pytest
from conftest import intimate, reconcile, set_life

from companion.characters import require_current
from companion.database import decode, encode
from companion.life import big_days, body, families, love_life, own_family, steps, storylines, work
from companion.life.openers import Trigger

WORKDAY = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00', 'days': [0, 1, 2, 3, 4]},
           {'key': 'evening', 'label': 'Evening', 'kind': 'social', 'start': '18:00', 'end': '22:00'},
           {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]
CHILD_FIELDS = {'name', 'a', 'child', 'they', 'them', 'their', 'theyre', 'are', 'were', 'They', 'Their', 'Theyre'}


@pytest.fixture(autouse=True)
def active(monkeypatch):
    monkeypatch.setattr(families, 'ACTIVE', True)
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    monkeypatch.setattr(storylines, 'STORIES', tuple(story for story in storylines.STORIES if story.own))
    monkeypatch.setattr(own_family, 'wants', lambda *_args: 'yes')
    monkeypatch.setattr(love_life, 'ACTIVE', False)  # The pair stays at the step each test puts them on.


@pytest.fixture
def mira(client):
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC', 'schedule': WORKDAY,
                                                     'location': 'Fells Point, Baltimore', 'identity': '33. She/her.',
                                                     'personality': 'Outgoing, a social butterfly.'})
    assert response.status_code == 200, response.text
    assert client.get('/api/life/circle').status_code == 200
    return response.json()


def current(client):
    with client.app.state.database.connect() as connection:
        return require_current(connection)


def partnered(client, clock, step='moving_in', pronouns='he/him') -> dict:
    """Mira starts seeing someone and they reach `step`; everyone else in her circle is too old for a baby, and past retiring or a round birthday."""
    companion = current(client)
    world = client.app.state.life.world
    with client.app.state.database.connect(write=True) as connection:
        for row in connection.execute('SELECT id, details FROM circle_people').fetchall():
            connection.execute('UPDATE circle_people SET details=? WHERE id=?',
                               (encode({**decode(row['details']), 'age': 73, 'career': 'Retired'}), row['id']))
        day = steps.local_today(companion, clock.now()) - timedelta(days=400)
        found = love_life.plan(connection, companion, world, day, 'test-seed')
        found['person']['details'] |= {'pronouns': pronouns, 'age': 34}
        love_life.begin(connection, companion, world, day, found, clock.now())
        [partner] = love_life.partners(connection, companion['active_timeline_id'])
        for key in ('moving_in', 'married') if step == 'married' else (step,):
            love_life.step_up(connection, partner, key, day + timedelta(days=200), clock.now().isoformat())
    return partner


def sure(monkeypatch):
    monkeypatch.setattr(own_family, 'YEARLY', {key: 52.0 for key in own_family.YEARLY})
    monkeypatch.setattr(own_family, 'ADOPT', 0.0)


def children(client):
    with client.app.state.database.connect() as connection:
        return [dict(row) for row in connection.execute('SELECT * FROM circle_children')]


def stories(client, story):
    with client.app.state.database.connect() as connection:
        return [dict(row) for row in connection.execute('SELECT * FROM storylines WHERE story=?', (story,))]


def prompt(client) -> str:
    return client.get('/api/context/preview').json()['prompt']


def born(client, clock, child):
    clock.advance(date.fromisoformat(child['born_on']) - clock.now().date() + timedelta(days=1))
    reconcile(client)


def test_the_banks_have_enough_lines_and_every_one_fills_in():
    bank = families.bank()
    for key in ('own_expecting', 'own_adopting', 'own_baby', 'own_toddler', 'own_child'):
        assert len(bank[key]) >= 100, key
        assert len({line['text'] for line in bank[key]}) == len(bank[key]), key
        for line in bank[key]:
            fields = {field for text in (line['text'], line['share'])
                      for _literal, field, _spec, _conversion in string.Formatter().parse(text) if field}
            assert fields <= CHILD_FIELDS, line
            assert line['text'].endswith('.') and '{name} was' not in line['text'], line
    assert {line.get('carrying') for line in bank['own_expecting']} == {None, 'me', 'them'}
    for key, fields in (('babysit_ask', {'child', 'partner', 'day', 'time'}),):
        assert len(set(bank[key])) >= 100
        for line in bank[key]:
            assert {field for _l, field, _s, _c in string.Formatter().parse(line) if field} == fields, line
    godparent = big_days.bank()['godparent']
    assert len(set(godparent)) >= 100
    for line in godparent:
        line.format(child='Mia', partner='Dan', day='Saturday', time='11')
    row, names = {'cast_ids': '["p1"]'}, {'p1': {'name': 'Dan', 'role': 'husband'}}
    for key in ('own_expecting', 'own_baby', 'own_child'):
        for line in bank[key]:
            for you in (False, True):
                text = storylines.fill(families.fill_child(line['text'], {'name': 'Leo', 'pronouns': 'he/him'}),
                                       row, names, {'name': 'Mira'}, you)
                assert '{' not in text and (not you or 'Mira' not in text), text


def test_a_friend_living_with_their_partner_has_a_baby_of_their_own(client, mira, clock, monkeypatch):
    sure(monkeypatch)
    partner = partnered(client, clock)
    reconcile(client)
    [story] = stories(client, 'expecting')
    stages = decode(story['stages'])
    # She/her with a he/him partner: Mira is the one expecting.
    assert stages[0]['route'] == 'carrying' and stages[0]['text'].startswith('{name} and {a} are expecting')
    assert "I'm pregnant" in stages[0]['share']
    [child] = children(client)
    assert child['whose'] == 'companion' and child['parent_id'] == partner['person_id'] and child['status'] == 'expected'
    person = next(row for row in client.get('/api/life/circle').json() if row['id'] == partner['person_id'])
    assert person['expecting'] and not person['adopting']

    born(client, clock, child)
    [child] = children(client)
    assert child['status'] == 'born'
    person = next(row for row in client.get('/api/life/circle').json() if row['id'] == partner['person_id'])
    [shown] = person['children']
    assert shown['relation'] in ('daughter', 'son') and shown['own']
    text = prompt(client)
    assert f"- {child['name']} (your {shown['relation']}, a newborn): yours and your " in text
    assert 'had the baby' in text
    # Weeks of parental leave from work, and the baby things out of their money.
    companion = current(client)
    today = clock.now().date()
    with client.app.state.database.connect() as connection:
        off = work.days_off(connection, companion, today, today + timedelta(days=7))
        bought = own_family.purchases(connection, companion['active_timeline_id'], today - timedelta(days=60), today)
    assert set(off.values()) == {own_family.LEAVE}
    assert any(item['for'] == 'baby' for item in bought)


def test_a_romance_never_has_a_baby_with_someone_else(client, mira, clock, monkeypatch):
    sure(monkeypatch)
    partnered(client, clock, 'married')
    with client.app.state.database.connect() as connection:
        companion = current(client)
        assert own_family.pair(connection, companion)['how'] == 'married'
        romance = {**companion, 'version': {**companion['version'], 'definition': {
            **companion['version']['definition'], 'relationship': 'romance'}}}
        assert own_family.pair(connection, romance) is None


def test_only_a_pair_who_lives_together_and_wants_children(client, mira, clock, monkeypatch):
    sure(monkeypatch)
    partnered(client, clock, 'love')
    reconcile(client)
    assert children(client) == []  # Dating, not living together.


def test_who_carries_or_whether_they_adopt_is_decided_from_the_pair(client, mira, clock):
    partner = partnered(client, clock, pronouns='he/him')
    with client.app.state.database.connect() as connection:
        companion = current(client)
        person = dict(connection.execute('SELECT * FROM circle_people WHERE id=?', (partner['person_id'],)).fetchone())
        found = {own_family.route(connection, companion, person, f'seed{n}', 'modern', clock.now().date())
                 for n in range(60)}
        assert found == {'carrying', 'adopting'}
        assert {own_family.route(connection, companion, person, f'seed{n}', 'victorian', clock.now().date())
                for n in range(20)} == {'carrying'}
        him = {**companion, 'version': {**companion['version'], 'definition': {
            **companion['version']['definition'], 'identity': '33. He/him.'}}}
        assert {own_family.route(connection, him, person, f'seed{n}', 'modern', clock.now().date())
                for n in range(10)} == {'adopting'}
    assert own_family.news('adopting', 'March', 'victorian')[0].startswith('{name} and {a} will take in a baby')
    assert all('agency' not in line['text'] for line in own_family.middle_lines('adopting', 'medieval'))
    assert all(line.get('carrying') != 'them' for line in own_family.middle_lines('carrying', 'modern'))


def test_with_the_adult_side_on_their_own_child_stays_out_of_chat(client, mira, clock, monkeypatch):
    sure(monkeypatch)
    partnered(client, clock)
    reconcile(client)
    [child] = children(client)
    born(client, clock, child)
    assert child['name'] in prompt(client)
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    intimate(client)
    text = prompt(client)
    assert not re.search(rf"\b{child['name']}\b", text) and 'expecting a baby' not in text
    assert any(person['children'] for person in client.get('/api/life/circle').json())
    with client.app.state.database.connect(write=True) as connection:
        companion = current(client)
        assert own_family.plan_asks(connection, companion, date(2030, 1, 7), 1.0, clock.now()) == 0
        assert big_days.namings(connection, companion, clock.now().date(), {}, clock.now()) == []


def test_a_best_friend_is_asked_to_be_godparent_at_the_naming_day(client, mira, clock, monkeypatch):
    sure(monkeypatch)
    monkeypatch.setattr(big_days, 'ACTIVE', True)
    partnered(client, clock)
    reconcile(client)
    [child] = children(client)
    with client.app.state.database.connect(write=True) as connection:
        companion = current(client)
        steps.insert_step(connection, companion['active_timeline_id'], 'friendship', 'best_friends',
                          clock.now().date(), 'them', clock.now().isoformat())
    born(client, clock, child)
    rows = []
    while not any(row['kind'] == 'naming' for row in rows):  # Six to twelve weeks on, found six weeks ahead.
        clock.advance(timedelta(days=1))
        reconcile(client)
        with client.app.state.database.connect() as connection:
            rows = big_days.rows(connection, current(client)['active_timeline_id'])
    [row] = [row for row in rows if row['kind'] == 'naming']
    assert row['invite'] == 1 and row['details']['name'] == child['name'] and row['place']['name'].startswith('Mira and ')
    assert row['details']['pronouns'] == child['pronouns']  # The baby's, not their partner's.
    assert date.fromisoformat(row['local_date']).weekday() == 5
    text = big_days.invitation(row, 'Saturday', '11')
    assert child['name'] in text and 'Saturday' in text
    assert 'godparent' in big_days.reason_for(row, date.fromisoformat(row['local_date']))
    assert 'to be the godparent' in prompt(client)


def test_the_user_is_asked_to_babysit_now_and_then(client, mira, clock, monkeypatch):
    sure(monkeypatch)
    monkeypatch.setattr(own_family, 'BABYSIT', 10.0)
    partnered(client, clock)
    reconcile(client)
    [child] = children(client)
    born(client, clock, child)
    monkeypatch.setattr(own_family, 'YEARLY', {key: 0.0 for key in own_family.YEARLY})
    clock.advance(timedelta(days=100 + (7 - (clock.now().date() + timedelta(days=100)).weekday()) % 7))
    clock.advance(timedelta(hours=12 - clock.now().hour))
    reconcile(client)
    database = client.app.state.database
    with database.connect(write=True) as connection:
        companion = current(client)
        [trigger] = own_family.ask_due(connection, companion, clock.now())
        assert trigger.kind == 'babysit_ask' and child['name'] in trigger.template
        [row] = own_family.rows(connection, companion['active_timeline_id'])
        connection.execute("INSERT INTO messages (id, timeline_id, seq, role, text, status, created_at) VALUES "
                           "('m1', ?, 1, 'companion', ?, 'complete', ?)",
                           (companion['active_timeline_id'], trigger.template, clock.now().isoformat()))
        own_family.settle(connection, companion, {'id': 'm1'}, Trigger(trigger.key, trigger.kind, '', None,
                                                                       trigger.sources), clock.now().isoformat())
        assert own_family.ask_due(connection, companion, clock.now()) == []
        reply = {'id': 'm2', 'timeline_id': companion['active_timeline_id'], 'seq': 2, 'role': 'user',
                 'text': 'yes of course!', 'created_at': clock.now().isoformat()}
        connection.execute("INSERT INTO messages (id, timeline_id, seq, role, text, status, created_at) VALUES "
                           "(?, ?, 2, 'user', ?, 'complete', ?)", (reply['id'], reply['timeline_id'], reply['text'],
                                                                   reply['created_at']))
        assert own_family.note(connection, reply, companion, clock.now().isoformat())
        [row] = own_family.rows(connection, companion['active_timeline_id'])
        assert row['status'] == 'yes'
    assert f"The user is babysitting {child['name']} at your place" in prompt(client)
    clock.advance(date.fromisoformat(row['local_date']) - clock.now().date() + timedelta(days=1))
    reconcile(client)
    with database.connect() as connection:
        [row] = own_family.rows(connection, current(client)['active_timeline_id'], ('done',))
    assert f"the user babysat {child['name']}" in prompt(client)


def test_growing_families_off_means_no_baby_of_their_own(client, mira, clock, monkeypatch):
    sure(monkeypatch)
    set_life(client, growing_families=0)
    partnered(client, clock)
    reconcile(client)
    assert children(client) == []


def test_split_up_with_a_child_the_ex_stays_as_the_other_parent(client, mira, clock, monkeypatch):
    sure(monkeypatch)
    partner = partnered(client, clock)
    reconcile(client)
    [child] = children(client)
    born(client, clock, child)
    companion = current(client)
    with client.app.state.database.connect(write=True) as connection:
        found = love_life.partners(connection, companion['active_timeline_id'])[0]
        love_life.end(connection, found, 'split', steps.local_today(companion, clock.now()))
        person = connection.execute('SELECT * FROM circle_people WHERE id=?', (partner['person_id'],)).fetchone()
        connection.commit()
    assert person['status'] == 'active' and person['role'] == 'ex' and decode(person['details'])['co_parent']
    reconcile(client)  # The daily pass decides where the child lives.
    first = person['name'].split()[0]
    assert f'- Since you and {first} split up, {child["name"].split()[0]} ' in prompt(client)
    with client.app.state.database.connect() as connection:
        assert connection.execute("SELECT id FROM consequences WHERE choice='kids:custody'").fetchone()


def test_after_a_split_nobody_is_asked_to_babysit_for_an_evening_out_with_the_ex(client, mira, clock, monkeypatch):
    sure(monkeypatch)
    monkeypatch.setattr(own_family, 'BABYSIT', 10.0)
    partnered(client, clock)
    reconcile(client)
    [child] = children(client)
    born(client, clock, child)
    monkeypatch.setattr(own_family, 'YEARLY', {key: 0.0 for key in own_family.YEARLY})
    clock.advance(timedelta(days=100 + (7 - (clock.now().date() + timedelta(days=100)).weekday()) % 7))
    clock.advance(timedelta(hours=12 - clock.now().hour))
    reconcile(client)
    companion = current(client)
    with client.app.state.database.connect(write=True) as connection:
        assert own_family.rows(connection, companion['active_timeline_id'], ('planned',))  # Asked while together.
        found = love_life.partners(connection, companion['active_timeline_id'])[0]
        love_life.end(connection, found, 'split', steps.local_today(companion, clock.now()))
    reconcile(client)
    with client.app.state.database.connect() as connection:
        assert own_family.ask_due(connection, companion, clock.now()) == []
        assert not own_family.rows(connection, companion['active_timeline_id'], ('planned', 'asked', 'yes'))
    for _week in range(4):
        clock.advance(timedelta(days=7))
        reconcile(client)
    with client.app.state.database.connect() as connection:
        assert not own_family.rows(connection, companion['active_timeline_id'], ('planned', 'asked', 'yes'))


def test_a_new_baby_of_their_own_means_broken_nights_now_and_then(client, mira, clock, monkeypatch):
    sure(monkeypatch)
    partnered(client, clock)
    reconcile(client)
    [child] = children(client)
    born(client, clock, child)
    companion = current(client)
    timeline_id, first = companion['active_timeline_id'], clock.now().date()
    with client.app.state.database.connect(write=True) as connection:
        nights = [own_family.broken_night(connection, timeline_id, first + timedelta(days=n)) for n in range(1, 61)]
        tired = [night for night in nights if night]
        assert 5 < len(tired) < 55 and tired[0] == {'state': 'tired', 'because': 'after a broken night'}
        later = [own_family.broken_night(connection, timeline_id, first + timedelta(days=n)) for n in range(1200, 1260)]
        assert not any(later)  # Three and over: they sleep.
    set_life(client, family_life=0)
    with client.app.state.database.connect() as connection:
        assert not any(own_family.broken_night(connection, timeline_id, first + timedelta(days=n)) for n in range(1, 61))


@pytest.mark.parametrize('era', ['jazz-age', 'victorian', 'medieval', 'fantasy'])
def test_an_older_city_hears_their_news_in_its_own_voice(era):
    bank, tags = families.bank(), families.tags()
    modern = re.compile(r"\b(?:match|agency|bag|hospital|honestly|okay)\b|!!", re.IGNORECASE)
    for how in ('carrying', 'partner', 'adopting'):
        lines = [own_family.news(how, 'May', era), own_family.any_day(how, era),
                 own_family.arrived(how, {'name': 'Ivy', 'pronouns': 'she/her'}, era)]
        for text, share in lines:
            assert not modern.search(text) and not modern.search(share) and not re.match('[a-z]', share), (text, share)
        # Every middle beat in an older city fits it, and there are still plenty to pick from.
        middle = own_family.middle_lines(how, era)
        assert len(middle) >= 90 and not any('modern' in tags.get(line['text'], ()) for line in middle)
    for key in ('own_baby', 'own_toddler', 'own_child'):
        found = families.fitting(bank[key], era)
        assert len(found) >= 100 and not any('modern' in tags.get(line['text'], ()) for line in found), key
        assert any('older' in tags.get(line['text'], ()) for line in found)
    assert len(own_family.middle_lines('adopting', era)) >= 100


def test_babysitting_asks_fit_the_citys_era(client, mira):
    tags = families.tags()
    with client.app.state.database.connect() as connection:
        companion = current(client)
        today = own_family.fitting_asks(connection, companion)
        assert len(today) >= 100 and not any('older' in tags.get(line, ()) for line in today)
        old = {**companion, 'version': {**companion['version'], 'definition': {
            **companion['version']['definition'], 'home_city': 'london-1895', 'location': 'Marylebone, London'}}}
        assert families.era_of(connection, old['version']['definition']) == 'victorian'
        older = own_family.fitting_asks(connection, old)
    assert len(older) >= 100 and not any('modern' in tags.get(line, ()) or 'izza' in line for line in older)
    assert any('older' in tags.get(line, ()) for line in older)


def test_a_young_baby_of_theirs_does_not_walk_sit_up_or_eat_yet():
    from companion.life import our_child
    lines = families.fitting(families.bank()['own_baby'], 'modern')
    young = own_family.for_age(lines, 40)
    assert len(young) >= 50
    for line in young:
        said = f"{line['text']} {line['share']}"
        assert not our_child.MOVING.search(said) and not our_child.FOOD.search(said) and \
            not own_family.SITTING.search(said), line
    assert len(own_family.for_age(lines, 330)) == len(lines)
    child = {'id': 'c1', 'born_on': '2027-01-04', 'pronouns': 'she/her', 'name': 'Ivy'}
    for offset in range(0, 140):
        found = own_family.news_on(child, date(2027, 1, 4) + timedelta(days=offset), 3.0, 'modern')
        if found:
            assert found[1] in {line['text'] for line in own_family.for_age(lines, offset)}


def test_an_ask_for_next_saturday_does_not_say_on_next_saturday():
    assert big_days.on_next('Could you mind Ivy on next Saturday from 7?') == 'Could you mind Ivy next Saturday from 7?'
    assert big_days.on_next('on Saturday, November 21') == 'on Saturday, November 21'
    row = {'id': 'b1', 'kind': 'naming', 'details': {'name': 'Ivy', 'partner': 'Dan'}, 'place': {'modern': True}}
    for seed in range(40):
        assert 'on next' not in big_days.invitation({**row, 'id': f'b{seed}'}, 'next Saturday', '11').lower()
