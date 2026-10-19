"""Companions who already have kids (companion/life/kids.py): children read from their description or kept from their
life as a townsperson or seeded for a new companion, their other parent and where they live, meeting them and the
user as their step-parent, a love-life partner's kids, and the limits children keep."""
from datetime import date, timedelta

import pytest
from conftest import intimate, reconcile, set_life

from companion import consequences
from companion.characters import current
from companion.database import decode
from companion.life import families, kids, love_life, steps, their_people
from companion.memory import pairs

DANA = {'name': 'Dana Reyes', 'timezone': 'UTC', 'location': 'Fells Point, Baltimore',
        'identity': '38. She/her. Nurse.', 'relationship': 'romance'}


@pytest.fixture(autouse=True)
def active(monkeypatch):
    monkeypatch.setattr(kids, 'ACTIVE', True)


def make(client, **values):
    response = client.post('/api/companion', json={**DANA, **values})
    assert response.status_code == 200, response.text
    assert client.get('/api/life/circle').status_code == 200
    return response.json()


def panel(client):
    response = client.get('/api/life/steps/kids')
    assert response.status_code == 200, response.text
    return response.json()


def set_kids(client, status=200, **values):
    response = client.put('/api/life/steps/kids', json=values)
    assert response.status_code == status, response.text
    return response.json()


def prompt(client) -> str:
    return client.get('/api/context/preview').json()['prompt']


def circle(client) -> list[dict]:
    return client.get('/api/life/circle').json()


def forced(monkeypatch, choice: str, option: int):
    """The engine lands on `option` for `choice`, and on the likeliest option for every other choice."""
    rolled = consequences.roll
    monkeypatch.setattr(consequences, 'roll', lambda seed, found: option if choice in seed else rolled(seed, found))


# Reading the description --------------------------------------------------------------------------------------------

@pytest.mark.parametrize(('text', 'expected'), [
    ('Single dad. His son Leo, 7, loves trains.', [('Leo', 'he/him', 7)]),
    ('Her daughter Mia (4) and her son Jonah is ten.', [('Mia', 'she/her', 4), ('Jonah', 'he/him', 10)]),
    ('Her 7-year-old son Leo keeps her busy.', [('Leo', 'he/him', 7)]),
    ('A mother of two who works nights.', [(None, None, None), (None, None, None)]),
    ('He has three daughters.', [(None, 'she/her', None)] * 3),
    ('Her twins keep her on her toes.', [(None, None, None)] * 2),
    ('Her grown son Mark lives in Ohio.', []),
    ('Her son Leo is seven and her daughter Ivy is 19.', [('Leo', 'he/him', 7)]),
    ('Dana is a nurse with a cat named Pickle.', []),
])
def test_kids_are_read_from_the_description(text, expected):
    found = kids.described({'name': 'Dana Reyes', 'identity': text})
    assert [(kid['name'], kid['pronouns'], kid['age']) for kid in found['kids']] == expected


@pytest.mark.parametrize(('text', 'expected'), [
    ('Her son Leo, 7, and daughter Mia, 4.', [('Leo', 'he/him', 7), ('Mia', 'she/her', 4)]),
    ('Proud mom of Leo (7) and Mia (4).', [('Leo', None, 7), ('Mia', None, 4)]),
    ('Her kids Leo and Mia keep her busy.', [('Leo', None, None), ('Mia', None, None)]),
    ('Mother of two, Leo and Mia.', [('Leo', None, None), ('Mia', None, None)]),
    ('Single mom of two: Theo (6) and Ivy (3).', [('Theo', None, 6), ('Ivy', None, 3)]),
    ('Single mom of a son, Theo, 6.', [('Theo', 'he/him', 6)]),
    ('She has a son, Theo, who is 6.', [('Theo', 'he/him', 6)]),
    ('Her two teenage daughters, Ava and Zoe.', [('Ava', 'she/her', None), ('Zoe', 'she/her', None)]),
    ('She has a daughter named Rosa who is 9.', [('Rosa', 'she/her', 9)]),
    ('Their kid Rowan is eight.', [('Rowan', None, 8)]),
    ('He has a stepson.', [(None, 'he/him', None)]),
    ('Divorced. Two teenage daughters.', [(None, 'she/her', None)] * 2),
    ('Mom of two boys.', [(None, 'he/him', None)] * 2),
    ('She has a six-year-old daughter.', [(None, 'she/her', None)]),
    ('Dog mom to Biscuit and Pip.', []),
    ('Cat dad of two.', []),
    ('Mom to a rescue dog named Biscuit.', []),
    ('Her two brothers, Tom and Ben.', []),
    ('Wants kids someday.', []),
])
def test_more_ways_a_description_names_or_counts_their_kids(text, expected):
    found = kids.described({'name': 'Dana Reyes', 'identity': f'38. {text}'})
    assert [(kid['name'], kid['pronouns'], kid['age']) for kid in found['kids']] == expected


def test_the_word_before_unnamed_kids_sets_their_age(monkeypatch):
    monkeypatch.setattr(kids, 'companion_age', lambda *_args: 41)
    companion = {'active_timeline_id': 't', 'id': 'c', 'version': {'definition': {'name': 'Dana'}}}
    found = kids.described({'name': 'Dana', 'identity': '41. She has two teenage daughters and a 6-year-old.'})
    assert [kid['modifier'] for kid in found['kids']] == ['teenage', 'teenage']
    today = date(2026, 10, 19)
    for index, kid in enumerate(found['kids']):
        assert 13 <= kids.age_for(None, {**companion, 'id': f'c{index}'}, kid, f'seed{index}', today) <= 17
    assert kids.age_for(None, companion, {'modifier': 'six-year-old'}, 's', today) == 6


def test_the_description_says_where_they_live_and_who_the_other_parent_is():
    assert kids.described({'name': 'Dana', 'background': 'Her son Leo spends every other weekend with her.'})['pattern'] == 'weekends'
    assert kids.described({'name': 'Dana', 'background': 'They share custody of Leo.'})['pattern'] is None
    assert kids.described({'name': 'Dana', 'background': 'Joint custody of her son Leo.'})['pattern'] == 'shared'
    assert kids.described({'name': 'Dana', 'identity': 'A single mom; her son Leo is 7.'})['pattern'] == 'with_them'
    found = kids.described({'name': 'Dana', 'background': 'Her ex-husband Mark Lowe still lives nearby. Her son Leo, 7.'})
    assert found['other'] == {'name': 'Mark Lowe', 'pronouns': 'he/him', 'role': 'ex-husband'}
    assert kids.described({'name': 'Dana', 'background': 'Widowed young, she raises her son Leo, 7.'})['widowed']
    assert kids.described({'name': 'Dana', 'background': 'No kids, and happy that way.'})['none']


def test_alternate_weeks_follow_the_pattern():
    since = date(2026, 10, 19)  # A Monday.
    saturday, next_saturday, tuesday = date(2026, 10, 24), date(2026, 10, 31), date(2026, 10, 27)
    assert kids.with_them('with_them', since, saturday) and not kids.with_them('with_them', since, next_saturday)
    assert kids.with_them('weekends', since, saturday) and not kids.with_them('weekends', since, tuesday)
    assert kids.with_them('shared', since, saturday) and not kids.with_them('shared', since, tuesday)
    assert kids.with_them('sole', since, next_saturday) and kids.with_them('together', since, next_saturday)


# A companion who has kids -----------------------------------------------------------------------------------------

def test_kids_from_the_description_are_children_in_words_never_circle_people(client):
    make(client, background='Her son Leo, 7, and her daughter Mia (4) are her whole world.')
    view = panel(client)
    assert [(kid['name'], kid['age'], kid['relation']) for kid in view['kids']] == [('Leo', 7, 'son'), ('Mia', 4, 'daughter')]
    people = circle(client)
    assert not {'Leo', 'Mia'} & {person['name'] for person in people}
    [other] = [person for person in people if person['role'] == 'co-parent']
    assert view['other']['name'] == other['name']
    assert view['pattern'] in kids.CUSTODY and view['pattern_how'] == 'seeded'
    text = prompt(client)
    assert 'Your children' in text and 'Leo (7, your son)' in text and 'Mia (4, your daughter)' in text
    assert "hasn't met them yet" in text


def test_a_single_dad_of_two_gets_two_kids_named_by_the_app(client):
    make(client, name='Sam Ortiz', identity='41. He/him. A single dad of two.')
    view = panel(client)
    assert len(view['kids']) == 2 and view['pattern'] == 'with_them' and view['pattern_how'] == 'fixed'
    assert all(kid['age'] <= 17 for kid in view['kids'])
    names = {kid['name'] for kid in view['kids']}
    assert not names & {person['name'].split()[0] for person in circle(client)} and 'Sam' not in names


def test_a_widowed_parent_has_no_other_parent(client):
    make(client, background='Widowed three years ago, she is raising her son Leo, 9.')
    view = panel(client)
    assert view['other'] is None and view['pattern'] == 'sole'
    assert [item['key'] for item in view['patterns']] == ['sole']
    assert not [person for person in circle(client) if person['role'] == 'co-parent']
    assert 'their other parent is not in the picture' in prompt(client)


def test_the_ex_the_description_names_is_the_other_parent(client, clock):
    make(client, background='Her ex-husband Mark Lowe has their son Leo, 7, every other weekend.')
    view = panel(client)
    assert view['other'] == {'name': 'Mark', 'role': 'ex-husband'} and view['pattern'] == 'with_them'
    assert 'every other weekend with their dad Mark' in prompt(client)
    assert view['detail'] == "with Dana, every other weekend at Mark's"
    assert [item['label'] for item in view['patterns']] == ['Mostly with Dana', 'Half and half', 'Mostly with Mark']
    # Someone they share kids with starts where any co-parent does, not as an ex they barely know.
    mark = next(person for person in circle(client) if person['name'].startswith('Mark'))
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        seed = connection.execute('SELECT seed FROM circle_people WHERE id=?', (mark['id'],)).fetchone()[0]
        found = pairs.pair(connection, pairs.companion_key(companion['id']), seed, clock.now())
    assert found['start'] >= pairs.ROLE_DEFAULTS['co-parent'][0]  # The nudge only ever goes up.


def test_a_grown_son_stays_in_the_circle_and_nobody_else_counts(client, monkeypatch):
    forced(monkeypatch, 'kids:has', 0)
    make(client, background='Her grown son Mark Reyes lives in Ohio.')
    assert not panel(client)['shown']
    assert any(person['name'] == 'Mark' and person['role'] == 'son' for person in circle(client))


def test_the_user_can_change_where_they_live_or_take_a_child_out(client):
    make(client, background='Her son Leo, 7, and her daughter Mia (4).')
    view = set_kids(client, pattern='shared')
    assert view['pattern'] == 'shared' and view['pattern_how'] == 'set'
    set_kids(client, 422, pattern='sole')
    set_kids(client, 422, pattern='nonsense')
    leo = next(kid for kid in view['kids'] if kid['name'] == 'Leo')
    view = set_kids(client, remove=leo['id'])
    assert [kid['name'] for kid in view['kids']] == ['Mia']
    reconcile(client)
    assert [kid['name'] for kid in panel(client)['kids']] == ['Mia'] and 'Leo (7' not in prompt(client)
    view = set_kids(client, restore=leo['id'])
    assert sorted(kid['name'] for kid in view['kids']) == ['Leo', 'Mia']
    reconcile(client)
    assert sorted(kid['name'] for kid in panel(client)['kids']) == ['Leo', 'Mia'] and 'Leo (7' in prompt(client)
    set_kids(client, 404, restore=leo['id'])
    assert set_kids(client, pattern='auto')['pattern_how'] == 'seeded'


def test_a_child_of_theirs_who_turns_18_joins_their_circle_as_a_grown_son(client, clock):
    make(client, background='Her son Leo, 17, and her daughter Mia, 4.')
    clock.advance(timedelta(days=370))
    reconcile(client)
    assert [kid['name'] for kid in panel(client)['kids']] == ['Mia']
    grown = [person for person in circle(client) if person['name'] == 'Leo']
    assert len(grown) == 1 and grown[0]['role'] == 'son'
    text = prompt(client)
    assert 'your son)' not in text and '- Leo (son)' in text
    reconcile(client)
    assert len([person for person in circle(client) if person['name'] == 'Leo']) == 1


def test_today_says_where_the_kids_are(client, clock):
    make(client, background='Her son Leo, 7, lives with his dad and spends every other weekend with her.')
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        line = kids.today_line(connection, companion, clock.now())
        row = kids.record(connection, companion['active_timeline_id'])
        them, _name = kids.other_text(connection, companion, row)
    here = kids.with_them('weekends', date.fromisoformat(row['since']), clock.now().date())
    assert line[1] == ('- Today Leo is with you.' if here else f'- Today Leo is with {them}.')


# Seeded for a new companion ---------------------------------------------------------------------------------------

def test_on_the_day_of_the_family_dinner_the_kids_are_with_them_whatever_the_rota(client, clock, monkeypatch):
    make(client, background='Her son Leo, 7, lives with his dad and spends every other weekend with her.')
    monkeypatch.setattr(kids, 'with_them', lambda *_args: False)
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        assert kids.today_line(connection, companion, clock.now())[1].startswith('- Today Leo is with their')
        dinner = {'activity': their_people.AT_FAMILY, 'local_date': steps.local_today(companion, clock.now()).isoformat(),
                  'place': {'first': True}}
        monkeypatch.setattr('companion.life.outings.in_force', lambda *_args: [dinner])
        assert kids.today_line(connection, companion, clock.now())[1] == '- Today Leo is with you.'


def test_a_new_companion_may_be_given_kids_by_the_engine(client, monkeypatch):
    forced(monkeypatch, 'kids:has', 1)
    make(client)
    view = panel(client)
    assert view['how'] == 'seeded' and 1 <= len(view['kids']) <= 3 and view['other']
    assert client.put('/api/settings', json={'show_odds': True}).status_code == 200
    consequence_id = panel(client)['consequence_id']
    response = client.post(f'/api/life/consequences/{consequence_id}/change', json={'option': 0})
    assert response.status_code == 200, response.text
    assert not panel(client)['shown']
    assert client.post(f'/api/life/consequences/{consequence_id}/change', json={'option': 1}).status_code == 200
    assert [kid['name'] for kid in panel(client)['kids']] == [kid['name'] for kid in view['kids']]


@pytest.mark.parametrize('city', ['london-1895', 'camelot', 'new-york-1925'])
def test_in_an_older_city_seeded_kids_live_with_them_and_no_rota(client, monkeypatch, city):
    forced(monkeypatch, 'kids:has', 1)
    make(client, home_city=city, location='')
    view = panel(client)
    assert view['how'] == 'seeded' and view['kids'] and view['other'] is None and view['pattern'] == 'sole'
    assert view['pattern_how'] == 'seeded'  # Not "Read from their description".
    assert 'weekend' not in prompt(client) and 'a week with' not in prompt(client)


def test_in_an_older_city_the_ex_the_description_names_is_still_the_other_parent(client):
    make(client, home_city='london-1895', location='', background='Her son Leo, 7. Her ex-husband Mark Lowe lives nearby.')
    assert panel(client)['other']['name'] == 'Mark'


def test_no_kids_are_seeded_against_the_description(client, monkeypatch):
    forced(monkeypatch, 'kids:has', 1)
    make(client, background='She never wanted kids.')
    assert not panel(client)['shown']


@pytest.mark.parametrize('background', ['She wants kids someday.', "She'd love kids one day.", 'Her two grown sons live in Ohio.'])
def test_no_kids_are_seeded_when_the_description_says_they_are_still_to_come_or_grown(client, monkeypatch, background):
    forced(monkeypatch, 'kids:has', 1)
    make(client, background=background)
    assert not panel(client)['shown']


def test_no_kids_are_seeded_for_someone_already_in_your_life(client, monkeypatch):
    forced(monkeypatch, 'kids:has', 1)
    monkeypatch.setattr(kids, 'ACTIVE', False)
    make(client)  # Their circle was assembled before kids came in.
    monkeypatch.setattr(kids, 'ACTIVE', True)
    reconcile(client)
    assert not panel(client)['shown']


def test_a_companion_who_reads_as_under_18_has_no_kids(client, monkeypatch):
    forced(monkeypatch, 'kids:has', 1)
    make(client, identity='16. A high school student.', background='Her son Leo, 2.', relationship='friendship')
    assert not panel(client)['shown']


# The user, the kids and a partner's kids --------------------------------------------------------------------------

def test_the_user_meets_the_kids_with_their_people_and_becomes_a_step_parent(client, clock, monkeypatch):
    make(client, background='Her son Leo, 7.')
    assert "hasn't met" in prompt(client)
    assert panel(client)['meeting'] == 'unmet'
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        timeline_id = companion['active_timeline_id']
        connection.execute("INSERT INTO people_meetups (id, timeline_id, kind, why, due_on, status, created_at) VALUES "
                           "('m1', ?, 'family', 'step', ?, 'planned', ?)", (timeline_id, clock.now().date().isoformat(),
                                                                           clock.now().isoformat()))
    assert 'meeting Leo at the family dinner' in prompt(client)
    with client.app.state.database.connect(write=True) as connection:
        connection.execute("UPDATE people_meetups SET status='done'")
    assert 'The user has met Leo.' in prompt(client)
    assert panel(client)['meeting'] == 'met'
    monkeypatch.setattr(kids, 'living_together', lambda *_args: True)
    assert "the user is Leo's step-parent" in prompt(client)
    assert panel(client)['step_parent'] and panel(client)['meeting'] is None


def test_drinks_with_their_friends_is_not_meeting_the_kids_and_the_family_dinner_has_them_there(client, clock):
    make(client, background='Her son Leo, 7, and her daughter Mia, 4.')
    with client.app.state.database.connect(write=True) as connection:
        timeline_id = current(connection)['active_timeline_id']
        connection.execute("INSERT INTO people_meetups (id, timeline_id, kind, why, due_on, status, created_at) VALUES "
                           "('m1', ?, 'friends', 'step', ?, 'done', ?)", (timeline_id, clock.now().date().isoformat(),
                                                                         clock.now().isoformat()))
    assert "hasn't met them yet" in prompt(client) and panel(client)['meeting'] == 'unmet'
    outing = {'activity': their_people.AT_FAMILY, 'until_time': '21:30',
              'place': {'name': "Rosa's place", 'first': True, 'people': [{'id': 'p', 'name': 'Rosa', 'role': 'mom'}]}}
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        line = their_people.scene(connection, companion, outing, None)
        assert 'Here with you: your mom Rosa, and your kids Leo and Mia. Nobody else is there.' in line
        assert 'Leo' not in their_people.scene(connection, companion, {**outing, 'activity': their_people.OUT_WITH_FRIENDS,
                                                                          'place': {**outing['place'], 'kind': 'bar'}}, None)
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    with client.app.state.database.connect(write=True) as connection:
        assert 'Leo' not in their_people.scene(connection, current(connection), outing, None)


def test_a_love_life_partner_may_come_with_kids_and_the_companion_becomes_their_step_parent(client, clock, monkeypatch):
    monkeypatch.setattr(kids, 'PARTNER_ODDS', ((0, 1.0),))
    make(client, relationship='friendship')
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        timeline_id = companion['active_timeline_id']
        person = connection.execute('SELECT * FROM circle_people ORDER BY ordinal LIMIT 1').fetchone()
        connection.execute("UPDATE circle_people SET details=json_set(details, '$.age', 40) WHERE id=?", (person['id'],))
        person = dict(connection.execute('SELECT * FROM circle_people WHERE id=?', (person['id'],)).fetchone())
        partner_id = love_life.insert(connection, companion, person['name'], decode(person['details']),
                                      clock.now().date(), clock.now(), person_id=person['id'])
        assert kids.partner_kids(connection, companion, None, person, clock.now()) >= 1
        found = kids.partners_kids(connection, timeline_id)
        assert all(kid['title'] == 'friend' and kid['parent_id'] == person['id'] for kid in found)
        assert not kids.step_lines(connection, companion, clock.now().date())
        steps.insert_step(connection, timeline_id, 'romance', 'moving_in', clock.now().date(), 'start',
                          clock.now().isoformat(), other=f'love:{partner_id}')
        [(_identity, line)] = kids.step_lines(connection, companion, clock.now().date())
    assert f"You live with {person['name']}" in line and 'step-parent' in line
    assert any(person_row['children'] for person_row in circle(client))


def test_a_townsperson_who_had_a_baby_keeps_them(client, clock, monkeypatch):
    from companion.world import couples, townsfolk
    born = clock.now().date() - timedelta(days=200)
    monkeypatch.setattr(townsfolk, 'find', lambda _data, key: {'key': key, 'cast': True} if key == 'town-1' else None)
    monkeypatch.setattr(couples, 'babies', lambda sheet, _data, _span: [
        {'partner': {'name': 'Rosa', 'full': 'Rosa Diaz', 'pronouns': 'she/her', 'age': 36}, 'day': born}]
        if not sheet.get('cast') else [])
    response = client.post('/api/companion', json=DANA)
    with client.app.state.database.connect(write=True) as connection:
        connection.execute("UPDATE companions SET townsfolk_key='town-1' WHERE id=?", (response.json()['id'],))
    view = panel(client)
    assert view['how'] == 'town' and [kid['born_on'] for kid in view['kids']] == [born.isoformat()]
    assert view['other']['name'] == 'Rosa'


# Limits children keep ---------------------------------------------------------------------------------------------

def test_with_the_adult_side_on_their_kids_stay_out_of_the_chat_and_are_never_pictured(client, clock):
    make(client, background='Her son Leo, 7.')
    assert 'Leo' in prompt(client)
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    intimate(client)
    text = prompt(client)
    assert 'Leo (7' not in text and 'Your children' not in text
    assert panel(client)['shown']
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        assert families.pictured(connection, companion['active_timeline_id'], ['At the park with Leo'])
        assert kids.today_line(connection, companion, clock.now()) is None


def test_their_kids_never_count_as_someone_elses_child(client, clock):
    make(client, background='Her son Leo, 7.')
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        assert not families.born(connection, companion['active_timeline_id'], clock.now().date())
        assert not families.context_lines(connection, companion, clock.now())


def test_a_v014_circle_with_their_son_in_it_hands_him_to_the_kids(client, monkeypatch):
    from companion.life import named
    monkeypatch.setattr(kids, 'ACTIVE', False)
    monkeypatch.setattr(named, 'in_circle', named.people)  # The circle as v0.14 assembled it.
    make(client, background='Her son Leo, 7.')
    assert any(person['name'] == 'Leo' for person in circle(client))
    monkeypatch.undo()
    monkeypatch.setattr(kids, 'ACTIVE', True)
    reconcile(client)
    assert not any(person['name'] == 'Leo' for person in circle(client))
    assert [kid['name'] for kid in panel(client)['kids']] == ['Leo']


def test_a_fork_keeps_their_kids(client, provider):
    from conftest import send
    make(client, background='Her son Leo, 7.')
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    sent = send(client, 'How is Leo?', 'client-kids-01')['message']
    response = client.post('/api/timelines', json={'message_id': sent['id'], 'text': 'How are the kids?'})
    assert response.status_code == 200, response.text
    view = panel(client)
    assert [kid['name'] for kid in view['kids']] == ['Leo'] and view['other']


def test_a_fork_has_its_own_copy_of_where_the_kids_live(client, provider):
    from conftest import send
    make(client, background='Her son Leo, 7.')
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    sent = send(client, 'How is Leo?', 'client-kids-02')['message']
    with client.app.state.database.connect() as connection:
        parent = kids.record(connection, current(connection)['active_timeline_id'])
        before = consequences.by_id(connection, parent['pattern_consequence_id'])['picked']
    fork_id = client.post('/api/timelines', json={'message_id': sent['id']}).json()['id']
    assert client.post(f'/api/timelines/{fork_id}/activate').status_code == 200
    with client.app.state.database.connect() as connection:
        fork = kids.record(connection, current(connection)['active_timeline_id'])
        copied = consequences.by_id(connection, fork['pattern_consequence_id'])
    assert fork['timeline_id'] == fork_id
    assert fork['pattern_consequence_id'] != parent['pattern_consequence_id'] and copied['picked'] == before
    response = client.post(f"/api/life/consequences/{fork['pattern_consequence_id']}/change",
                           json={'option': (before + 1) % 3})
    assert response.status_code == 200, response.text
    with client.app.state.database.connect() as connection:
        assert consequences.by_id(connection, parent['pattern_consequence_id'])['picked'] == before
    assert panel(client)['pattern'] == kids.CUSTODY[(before + 1) % 3]


@pytest.mark.parametrize('background', ['Parent of two; their daughter Elspeth is six.', 'A single dad of three.'])
def test_brothers_and_sisters_the_app_ages_are_born_far_enough_apart(client, background):
    make(client, identity='36. They/them.', background=background)
    born = sorted(date.fromisoformat(kid['born_on']) for kid in panel(client)['kids'])
    assert len(born) >= 2 and all((later - earlier).days >= kids.SPACING for earlier, later in zip(born, born[1:]))


def test_twins_share_a_birthday(client):
    make(client, background='Her twins keep her on her toes.')
    assert len({kid['born_on'] for kid in panel(client)['kids']}) == 1


def test_a_name_from_their_description_still_counts_once_the_child_is_out_of_the_circle(client, clock):
    make(client, background='Her son Leo, 7.')
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        connection.execute("UPDATE circle_children SET status='ended' WHERE timeline_id=?",
                           (companion['active_timeline_id'],))
        connection.commit()
        assert families.pictured(connection, companion['active_timeline_id'], ['At the park with Leo'])
        assert 'Leo' in families.every_name(connection)
        assert 'Leo' not in families.names(connection, companion['active_timeline_id'])


def test_an_other_parent_added_to_an_existing_circle_has_no_days_before_then(client, clock, monkeypatch):
    """A v0.14 circle gains the kids' other parent at the upgrade: their days start then, none written before."""
    from companion.clock import parse
    monkeypatch.setattr(kids, 'ACTIVE', False)
    make(client, identity='38. A single dad of two. He/him.')
    circle(client)
    clock.advance(timedelta(days=10))
    monkeypatch.setattr(kids, 'ACTIVE', True)
    reconcile(client)
    other = next(person for person in circle(client) if person['role'] == 'co-parent')
    with client.app.state.database.connect() as connection:
        cursor = connection.execute('SELECT through FROM agenda_cursors WHERE subject=?', (other['id'],)).fetchone()
        written = connection.execute('SELECT starts_at FROM life_agenda WHERE subject=?', (other['id'],)).fetchall()
    assert cursor and parse(cursor['through']) >= clock.now() - timedelta(hours=1)
    assert all(parse(row['starts_at']) >= clock.now() - timedelta(hours=1) for row in written)


def test_a_v014_son_handed_to_the_kids_keeps_his_birthday(client, monkeypatch):
    from companion.life import named
    monkeypatch.setattr(kids, 'ACTIVE', False)
    monkeypatch.setattr(named, 'in_circle', named.people)  # The circle as v0.14 assembled it.
    make(client, background='Her son Leo, 7.')
    [leo] = [person for person in circle(client) if person['name'] == 'Leo']
    birthday = leo['birthday']
    monkeypatch.undo()
    monkeypatch.setattr(kids, 'ACTIVE', True)
    reconcile(client)
    with client.app.state.database.connect() as connection:
        [kid] = [dict(row) for row in connection.execute("SELECT * FROM circle_children WHERE name='Leo'")]
    assert kid['born_on'][5:] == birthday, (kid, birthday)
    assert [item['age'] for item in panel(client)['kids']] == [7]


def test_growing_families_at_none_means_no_seeded_kids_and_no_partner_with_kids(client, clock, monkeypatch):
    set_life(client, growing_families=0)
    found = consequences.odds('kids:has', {'age': 40, 'growing': 0, 'said_no': 0, 'sheet': set()}, {'name': 'Dana'})
    assert found[1]['odds'] == 0 and 'Growing families is set to None' in found[1]['reasons']
    monkeypatch.setattr(kids, 'PARTNER_ODDS', ((0, 1.0),))
    make(client, relationship='friendship', identity='44. She/her. Nurse.')
    assert not panel(client)['shown']
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        assert kids.record(connection, companion['active_timeline_id'])['how'] == 'none'
        person = dict(connection.execute('SELECT * FROM circle_people ORDER BY ordinal LIMIT 1').fetchone())
        connection.execute("UPDATE circle_people SET details=json_set(details, '$.age', 40) WHERE id=?", (person['id'],))
        person = dict(connection.execute('SELECT * FROM circle_people WHERE id=?', (person['id'],)).fetchone())
        assert kids.partner_kids(connection, companion, None, person, clock.now()) == 0


def test_growing_families_at_none_keeps_the_kids_a_description_names(client):
    set_life(client, growing_families=0)
    make(client, background='Her son Leo, 7, and daughter Mia, 4.')
    assert [kid['name'].split()[0] for kid in panel(client)['kids']] == ['Leo', 'Mia']
