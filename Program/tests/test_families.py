"""Births and growing families (companion/life/families.py): pregnancies in the circle run as storylines over months,
then the baby joins the circle as a child, in words only."""
import json
import string
from datetime import date, timedelta

import pytest
from conftest import reconcile, set_life

from companion.characters import require_current
from companion.database import decode, encode
from companion.life import body, families, storylines
from companion.world import couples

WORKDAY = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00', 'days': [0, 1, 2, 3, 4]},
           {'key': 'evening', 'label': 'Evening', 'kind': 'social', 'start': '18:00', 'end': '22:00'},
           {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]
ALLOWED = {'name', 'a', 'a_rel', 'child', 'they', 'them', 'their', 'theyre', 'are', 'were', 'They', 'Their', 'Theyre'}


@pytest.fixture(autouse=True)
def active(monkeypatch):
    monkeypatch.setattr(families, 'ACTIVE', True)
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)


@pytest.fixture
def mira(client):
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC', 'schedule': WORKDAY,
                                                     'location': 'Fells Point, Baltimore', 'identity': '33. She/her.',
                                                     'personality': 'Outgoing, a social butterfly.'})
    assert response.status_code == 200, response.text
    assert client.get('/api/life/circle').status_code == 200
    return response.json()


def sister(client, role='sister', married=True) -> dict:
    """Makes the first circle member Mira's married sister of 32 and everyone else too old to be expecting."""
    with client.app.state.database.connect(write=True) as connection:
        rows = [dict(row) for row in connection.execute('SELECT * FROM circle_people ORDER BY ordinal')]
        for index, row in enumerate(rows):
            details = decode(row['details'])
            if index == 0:
                details |= {'age': 32, 'married': married, 'local': True, 'pronouns': 'she/her'}
            else:
                details |= {'age': 70}
            connection.execute('UPDATE circle_people SET role=?, details=? WHERE id=?',
                               (role if index == 0 else row['role'], encode(details), row['id']))
        return {**rows[0], 'role': role}


def sure(monkeypatch):
    monkeypatch.setattr(families, 'YEARLY', {key: 52.0 for key in families.YEARLY})


def stories(client, story=None):
    with client.app.state.database.connect() as connection:
        rows = [dict(row) for row in connection.execute('SELECT * FROM storylines ORDER BY started_on')]
    return [row for row in rows if story is None or row['story'] == story]


def children(client):
    with client.app.state.database.connect() as connection:
        return [dict(row) for row in connection.execute('SELECT * FROM circle_children')]


def prompt(client) -> str:
    return client.get('/api/context/preview').json()['prompt']


def test_the_bank_has_enough_lines_and_every_one_fills_in():
    bank = families.bank()
    for key in ('pregnancy', 'baby_update', 'toddler_update', 'child_update', 'babysit_baby', 'babysit_toddler',
                'babysit_child'):
        assert len(bank[key]) >= 100, key
        assert len({line['text'] for line in bank[key]}) == len(bank[key]), key
        for line in bank[key]:
            fields = {field for text in (line['text'], line['share'])
                      for _literal, field, _spec, _conversion in string.Formatter().parse(text) if field}
            assert fields <= ALLOWED, line
            assert line['text'].endswith('.') and '{name} was' not in line['text'], line
    for pronouns in ('she', 'he'):
        assert len(set(bank['names'][pronouns])) >= 100
    row, names = {'cast_ids': '["p1"]'}, {'p1': {'name': 'Ana', 'role': 'sister'}}
    child = {'name': 'Leo', 'pronouns': 'he/him'}
    for key in ('baby_update', 'babysit_toddler', 'child_update'):
        for line in bank[key]:
            for you in (False, True):
                text = storylines.fill(families.fill_child(line['text'], child), row, names, {'name': 'Mira'}, you)
                assert '{' not in text and (not you or 'Mira' not in text), text


def test_a_sister_expects_a_baby_who_joins_the_circle_as_a_niece(client, mira, clock, monkeypatch):
    sure(monkeypatch)
    sister(client)
    reconcile(client)
    [story] = stories(client, 'expecting')
    stages = json.loads(story['stages'])
    assert len(stages) == 4 and stages[0]['text'].startswith("{name}'s {a_rel} {a} is expecting a baby, due in ")
    assert 'I am going to be an aunt' in stages[0]['share']  # Mira's own words, by her pronouns.
    [child] = children(client)
    assert child['status'] == 'expected' and child['title'] == 'family'
    listed = client.get('/api/life/storylines').json()
    assert any(item['story'] == 'expecting' for item in listed)
    person = next(person for person in client.get('/api/life/circle').json() if person['id'] == story['cast_ids'][2:-2])
    assert person['expecting'] and person['children'] == []

    clock.advance(date.fromisoformat(child['born_on']) - clock.now().date() + timedelta(days=1))
    reconcile(client)
    [child] = children(client)
    assert child['status'] == 'born'
    person = next(person for person in client.get('/api/life/circle').json() if person['id'] == child['parent_id'])
    assert person['expecting'] is None
    [shown] = person['children']
    assert shown['name'] == child['name'] and shown['relation'] in ('niece', 'nephew') and shown['age'] == 0
    text = prompt(client)
    assert f"- {child['name']} (your {shown['relation']}, a newborn): your sister {person['name']}'s " in text
    assert 'had the baby' in text  # The birth, told as a storyline beat.
    with client.app.state.database.connect() as connection:  # Never a circle member: nothing else reads them.
        assert child['name'] not in {row['name'] for row in connection.execute('SELECT name FROM circle_people')}


def test_with_the_adult_side_on_children_stay_out_of_the_chat_prompt(client, mira, clock, monkeypatch):
    sure(monkeypatch)
    sister(client)
    reconcile(client)
    [child] = children(client)
    clock.advance(date.fromisoformat(child['born_on']) - clock.now().date() + timedelta(days=1))
    reconcile(client)
    assert child['name'] in prompt(client)
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    text = prompt(client)
    assert child['name'] not in text and 'expecting a baby' not in text
    # The screens still show them.
    assert any(item['story'] == 'expecting' for item in client.get('/api/life/storylines').json())
    assert any(person['children'] for person in client.get('/api/life/circle').json())


def test_growing_families_off_means_nobody_new_is_expecting(client, mira, monkeypatch):
    sure(monkeypatch)
    sister(client)
    assert set_life(client, growing_families=0)['growing_families'] == 0
    reconcile(client)
    assert stories(client, 'expecting') == [] and children(client) == []


@pytest.mark.parametrize('role', ['wife', 'mom'])
def test_their_own_partner_and_their_parents_are_never_expecting(client, mira, monkeypatch, role):
    sure(monkeypatch)
    sister(client, role=role)
    reconcile(client)
    assert stories(client, 'expecting') == []


def test_someone_they_are_dating_is_never_expecting(client, mira, monkeypatch):
    sure(monkeypatch)
    person = sister(client)
    with client.app.state.database.connect(write=True) as connection:
        companion = require_current(connection)
        connection.execute("INSERT INTO love_partners (id, timeline_id, companion_id, person_id, name, met_on, "
                           "created_at) VALUES ('lp', ?, ?, ?, 'Ana', '2026-09-01', '')",
                           (companion['active_timeline_id'], companion['id'], person['id']))
    reconcile(client)
    assert stories(client, 'expecting') == []


def test_ending_the_storyline_means_the_baby_never_arrives(client, mira, clock, monkeypatch):
    sure(monkeypatch)
    sister(client)
    reconcile(client)
    [story] = stories(client, 'expecting')
    assert client.post(f"/api/life/storylines/{story['id']}/end").status_code == 200
    [child] = children(client)
    clock.advance(date.fromisoformat(child['born_on']) - clock.now().date() + timedelta(days=1))
    reconcile(client)
    assert children(client)[0]['status'] == 'ended'
    assert all(not person['children'] for person in client.get('/api/life/circle').json())


def test_a_close_friend_may_ask_them_to_be_godparent_and_a_cousins_baby_is_theirs():
    seeds = [f'seed-{number}' for number in range(400)]
    asked = sum(families.title('close friend', seed) == 'godchild' for seed in seeds) / len(seeds)
    assert 0.35 < asked < 0.55
    assert {families.title('cousin', seed) for seed in seeds} == {'friend'}
    assert families.relation('family', 'she/her') == 'niece' and families.relation('godchild', 'he/him') == 'godson'
    text, share = families.arrived({'name': 'Ivy', 'pronouns': 'she/her'}, 'godchild', {'name': 'Sam'})
    assert "asked {name} to be Ivy's godparent" in text and 'godparent' in share
    _text, share = families.announced('sibling', date(2027, 3, 1), 'family', {'name': 'Sam', 'identity': ''})
    assert 'aunt' not in share.split('. or')[0] or 'or uncle' in share  # They/them: never guessed.


def test_babysitting_and_updates_follow_their_age_and_stop_at_thirteen():
    child = {'id': 'c1', 'born_on': '2026-01-10', 'title': 'family', 'name': 'Leo', 'pronouns': 'he/him'}
    days = [date(2026, 4, 1) + timedelta(days=offset) for offset in range(365)]
    found = [news for day in days if (news := families.news_on(child, day, 1.0, True))]
    kinds = {news[0] for news in found}
    assert {'babysat', 'baby_update'} <= kinds and 'first_birthday' not in kinds  # A big day of its own now.
    assert 6 < len(found) < 80
    grown = [families.news_on(child, day + timedelta(days=365 * 13), 1.0, True) for day in days]
    assert not any(grown)
    friend = {**child, 'title': 'friend'}
    assert not any(families.news_on(friend, day, 1.0, True) and families.news_on(friend, day, 1.0, True)[0] == 'babysat'
                   for day in days)


def test_a_fork_keeps_the_children_born_by_then(client, mira, clock, monkeypatch, provider):
    from conftest import send
    sure(monkeypatch)
    sister(client)
    reconcile(client)
    [child] = children(client)
    clock.advance(date.fromisoformat(child['born_on']) - clock.now().date() + timedelta(days=1))
    reconcile(client)
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    sent = send(client, 'How is the baby?', 'client-family-01')['message']
    response = client.post('/api/timelines', json={'message_id': sent['id'], 'text': 'How is everyone?'})
    assert response.status_code == 200, response.text
    copies = children(client)
    assert len(copies) == 2 and len({row['timeline_id'] for row in copies}) == 2
    assert copies[0]['name'] == copies[1]['name'] and copies[0]['parent_id'] != copies[1]['parent_id']


def test_town_couples_are_expecting_before_their_baby_arrives(monkeypatch):
    item = {'partner': {'name': 'Dana'}, 'day': date(2027, 3, 4)}
    monkeypatch.setattr(couples, 'babies', lambda *_args: [item])
    assert couples.family_news({}, {}, date(2026, 11, 1)) == 'expecting a baby with Dana around March'
    assert couples.family_news({}, {}, date(2027, 5, 1)) == 'had a baby with Dana in March'
    monkeypatch.setattr(couples, 'babies', lambda *_args: [])
    assert couples.family_news({}, {}, date(2027, 5, 1)) is None


@pytest.mark.parametrize(('drama', 'expected'), [(0, 1), (1, 2), (3, 3)])
def test_an_older_world_gets_growing_families_by_its_preset(tmp_path, drama, expected):
    import sqlite3

    from companion.database import add_columns, initialize
    connection = sqlite3.connect(tmp_path / 'old.sqlite3')
    initialize(connection, '2026-10-01T00:00:00Z')
    connection.execute('ALTER TABLE life_settings DROP COLUMN growing_families')
    connection.execute('UPDATE life_settings SET drama=?', (drama,))
    add_columns(connection)
    assert connection.execute('SELECT growing_families FROM life_settings').fetchone() == (expected,)
    connection.close()


def test_a_first_birthday_is_a_big_day_at_their_parents_told_in_words_only(client, mira, clock, monkeypatch):
    from companion.characters import current
    from companion.images import content, prompts
    from companion.life import big_days
    monkeypatch.setattr(big_days, 'ACTIVE', True)
    person = sister(client)
    birthday = clock.now().date() + timedelta(days=20)
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        timeline_id, now = companion['active_timeline_id'], clock.now().isoformat()
        connection.execute("INSERT INTO circle_children (id, timeline_id, parent_id, storyline_id, name, pronouns, title, "
                           "born_on, status, created_at, updated_at) VALUES ('ivy', ?, ?, 'story', 'Ivy', 'she/her', "
                           "'family', ?, 'born', ?, ?)", (timeline_id, person['id'],
                                                          birthday.replace(year=birthday.year - 1).isoformat(), now, now))
        big_days.advance(connection, companion, clock.now())
        [row] = [row for row in big_days.rows(connection, timeline_id) if row['kind'] == 'first_birthday']
        assert big_days.title(row) == "Ivy's first birthday" and big_days.said(row) == "your niece Ivy's first birthday party"
        assert row['place']['name'] == f"{person['name'].split()[0]}'s place" and row['gift']
        assert date.fromisoformat(row['local_date']).weekday() == 5 and date.fromisoformat(row['local_date']) >= birthday
        assert big_days.host(row) == {'id': person['id'], 'name': person['name'], 'role': 'sister'}  # Their parent.
        assert big_days.buzz_line(row, date.fromisoformat(row['local_date']) - timedelta(days=2)) == ''
        assert any('first birthday' in text for _key, text in big_days.context_lines(connection, companion, clock.now()))
        # Nothing pictures them: words naming the child or a first birthday are refused.
        assert families.pictured(connection, timeline_id, ['Out at the park with Ivy'])
        assert families.pictured(connection, timeline_id, ["At Sam's first birthday"])
        assert not families.pictured(connection, timeline_id, ['Out at the park'])
        refused = content.classify(prompts.children(connection, timeline_id, ["Ivy's first birthday at Ana's place"]))
        assert refused.tier == content.PROHIBITED
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        assert not any('Ivy' in text for _key, text in big_days.context_lines(connection, companion, clock.now()))
        big_days.advance(connection, companion, clock.now())
        assert big_days.get(connection, row['id'])['status'] == 'called_off'


def a_childs_big_day(client, clock, monkeypatch, provider, invite=False):
    """A sister's baby Ivy turning one in 20 days: the party planned as a big day, and (unless `invite`, which
    leaves the invitation still to go out) booked as an outing with the user. Returns (big day row, outing)."""
    from conftest import send

    from companion.characters import current
    from companion.life import big_days
    from companion.life.openers import Trigger
    monkeypatch.setattr(big_days, 'ACTIVE', True)
    monkeypatch.setattr(big_days, 'FIRST_TEXTS', True)
    person = sister(client)
    birthday = clock.now().date() + timedelta(days=20)
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    message = send(client, 'Hi!', 'client-family-02')['message']
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        timeline_id, now = companion['active_timeline_id'], clock.now().isoformat()
        connection.execute("INSERT INTO circle_children (id, timeline_id, parent_id, storyline_id, name, pronouns, title, "
                           "born_on, status, created_at, updated_at) VALUES ('ivy', ?, ?, 'story', 'Ivy', 'she/her', "
                           "'family', ?, 'born', ?, ?)", (timeline_id, person['id'],
                                                          birthday.replace(year=birthday.year - 1).isoformat(), now, now))
        big_days.advance(connection, companion, clock.now())
        [row] = [row for row in big_days.rows(connection, timeline_id) if row['kind'] == 'first_birthday']
        connection.execute("UPDATE big_days SET invite=(id=?), invite_on=?", (row['id'], clock.now().date().isoformat()))
        if invite:
            return big_days.get(connection, row['id']), None
        outing = big_days.settle(connection, companion, message, Trigger('bigday', 'big_day', '', None, (row['id'],)),
                                 now)
        return big_days.get(connection, row['id']), outing


def test_a_childs_big_day_is_never_pictured_however_it_is_worded(client, mira, clock, monkeypatch, provider):
    from companion.characters import current
    from companion.database import encode
    from companion.images import content, prompts
    _row, outing = a_childs_big_day(client, clock, monkeypatch, provider)
    with client.app.state.database.connect() as connection:
        timeline_id = current(connection)['active_timeline_id']
        # A model's phrasing of the afternoon that names neither the child nor the birthday.
        words = ["Mira went to my niece's big day at Ana's place with you.", 'cake everywhere, so cute']
        assert not families.pictured(connection, timeline_id, words)
        assert families.childs_day(connection, [outing['id']]) and not families.childs_day(connection, [None, 'x'])
        refused = content.classify(prompts.children(connection, timeline_id, words, [outing['id']]))
        assert refused.tier == content.PROHIBITED
        assert prompts.children(connection, timeline_id, words, [None]) == {}
    assert prompts.when({'details': encode({'outing': {'id': outing['id']}})})['outing']['id'] == outing['id']
    assert families.pictured(None, '', ["Ivy's 1st bday!"]) and families.pictured(None, '', ['her first bday'])


@pytest.mark.parametrize('when', ['planned', 'under way'])
def test_with_the_adult_side_on_no_context_line_names_a_child_even_before_the_next_pass(client, mira, clock,
                                                                                       monkeypatch, provider, when):
    row, outing = a_childs_big_day(client, clock, monkeypatch, provider)
    if when == 'under way':
        day = date.fromisoformat(row['local_date'])
        clock.advance(day - clock.now().date() + timedelta(hours=15))
    text = prompt(client)
    assert 'Ivy' in text and 'first birthday' in text
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    text = prompt(client)  # Before any reconcile has called the party off.
    assert 'Ivy' not in text and 'first birthday' not in text.lower()


def test_with_the_adult_side_on_a_childs_big_day_is_never_asked_to(client, mira, clock, monkeypatch, provider):
    from companion.characters import current
    from companion.life import big_days
    row, _outing = a_childs_big_day(client, clock, monkeypatch, provider, invite=True)
    clock.advance(timedelta(hours=12 - clock.now().hour + 24))
    with client.app.state.database.connect() as connection:
        assert [trigger.sources for trigger in big_days.invite_due(connection, current(connection), clock.now())] == \
            [(row['id'],)]
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    with client.app.state.database.connect() as connection:
        assert big_days.invite_due(connection, current(connection), clock.now()) == []


def test_bank_lines_fit_the_citys_era_and_who_is_carrying_the_baby():
    import re
    bank = families.bank()
    older = set(bank['tags']['older'])
    assert families.fitting(bank['babysit_toddler'], 'modern') == [
        line for line in bank['babysit_toddler'] if line['text'] not in older]
    for era, words in (('jazz-age', r'\b(scan|daycare|television)\b'), ('victorian', r'\b(phones?|cars?|daycare)\b'),
                       ('medieval', r'\b(phones?|cars?|trains?|strollers?|bananas?)\b')):
        for key in ('pregnancy', 'baby_update', 'toddler_update', 'babysit_toddler', 'babysit_child'):
            found = families.fitting(bank[key], era)
            assert len(found) >= 80 and not any(re.search(words, f"{line['text']} {line['share']}", re.I)
                                                for line in found), (era, key)
    assert not any('crav' in line['text'] for line in families.fitting(bank['pregnancy'], 'modern', carrying=False))
    child = {'id': 'c1', 'born_on': '2026-01-10', 'title': 'family', 'name': 'Leo', 'pronouns': 'he/him'}
    days = [date(2027, 1, 1) + timedelta(days=offset) for offset in range(730)]
    told = ' '.join(news[2] for day in days if (news := families.news_on(child, day, 1.7, True, 'medieval')))
    assert told and not re.search(r'\b(cars?|trains?|phones?|strollers?)\b', told, re.I)


def test_older_cities_speak_in_their_own_voice_and_today_in_a_texting_one():
    bank = families.bank()
    texts = {line['text'] for key, lines in bank.items() if key not in ('names', 'tags') for line in lines}
    assert set(bank['tags']['older']) <= texts and set(bank['tags']['modern']) <= texts
    for key in ('pregnancy', 'baby_update', 'toddler_update', 'child_update', 'babysit_baby', 'babysit_toddler',
                'babysit_child'):
        old, new = families.fitting(bank[key], 'victorian'), families.fitting(bank[key], 'modern')
        assert not {line['text'] for line in old} & set(bank['tags']['modern']), key
        assert not {line['text'] for line in new} & set(bank['tags']['older']), key
        assert {line['text'] for line in old} & set(bank['tags']['older']), key
        assert not any('gonna' in line['share'] or 'honestly' in line['share'] for line in old), key
    due = date(2027, 3, 1)
    assert families.announced('friend', due, 'friend', {'name': 'Ada'}, True)[1].endswith('I confess I cried a little')
    assert families.announced('friend', due, 'friend', {'name': 'Ada'})[1].endswith('not gonna lie')
    assert families.announced('coworker', due, 'friend', {'name': 'Ada'}, True)[1].endswith(
        'everyone at work is already knitting something')


def test_a_they_them_companion_is_the_cool_relative_and_a_father_has_the_baby_with_their_partner():
    due = date(2027, 3, 1)
    assert families.announced('sibling', due, 'family', {'name': 'Rowan', 'pronouns': 'they/them'})[1] == \
        "{a} is having a baby!!! due in March. I'm going to be the cool relative"
    assert families.announced('sibling', due, 'family', {'name': 'Mira', 'identity': 'She is 30.'})[1].endswith(
        'I am going to be an aunt')
    child = {'name': 'Nova', 'pronouns': 'she/her', 'title': 'friend'}
    assert families.arrived(child, 'friend', {}, 'he/him') == (
        '{a} and their partner had the baby: a girl named Nova.', "{a}'s baby is here! a girl, Nova. everyone's doing great")
    assert families.arrived(child, 'friend', {}, 'she/her')[0] == '{a} had the baby: a girl named Nova.'
    assert families.arrived(child, 'godchild', {}, 'he/him')[1].startswith("{a}'s baby is here! a girl, Nova, and {a} asked")
    assert 'crying' not in families.arrived(child, 'family', {}, 'she/her', True)[1]


def test_a_baby_is_never_given_the_companions_own_name(client, mira):
    from companion.characters import current
    with client.app.state.database.connect() as connection:
        taken = families.taken_names(connection, current(connection))
    assert 'Mira' in taken
    assert families.baby_name({}, None, 'seed', 'she/her', taken) != 'Mira'


def test_a_companion_living_in_town_never_has_a_town_baby(monkeypatch):
    from companion.life import encounters
    from companion.world import catalog, paper, townsfolk, turnover
    monkeypatch.setattr(turnover, 'ACTIVE', True)
    data, span = catalog.city('baltimore'), (date(2026, 10, 19), date(2029, 10, 19))
    sheet, found = next((sheet, found) for hood in data['neighborhoods'] for slot in range(8)
                        if (found := couples.babies(sheet := townsfolk.resident(data, hood['id'], slot), data, span)))
    day = found[0]['day']
    assert couples.family_news(sheet, data, day - timedelta(days=30)).startswith('expecting a baby')
    stand_in = encounters.stand_in(data, 'c1', sheet['key'], {'name': 'Alex Moore', 'identity': '30.'})
    assert couples.babies(stand_in, data, span) == [] and couples.family_news(stand_in, data, day) is None
    week = (day - timedelta(days=day.weekday()), day + timedelta(days=6 - day.weekday()))
    key = f"{sheet['key']}:baby:{day.isoformat()}"
    if sheet in paper.sample(data, week[1]):
        assert key in {item['key'] for item in paper.comings_and_goings(data, week)}
    assert key not in {item['key'] for item in paper.comings_and_goings({**data, 'companions': (sheet['key'],)}, week)}


def test_a_companion_made_from_a_townsperson_drops_their_town_love_life():
    from companion.life import encounters
    from companion.world import catalog, paper, townsfolk
    data, span = catalog.city('baltimore'), (date(2026, 10, 19), date(2029, 10, 19))
    sheet, found = next((sheet, found) for hood in data['neighborhoods'] for slot in range(12)
                        if (found := couples.events(sheet := townsfolk.resident(data, hood['id'], slot), data, span)))
    assert couples.couple(sheet, data, span[1]) is not None
    stand_in = encounters.stand_in(data, 'c1', sheet['key'], {'name': 'Alex Moore', 'identity': '30.'})
    assert couples.events(stand_in, data, span) == [] and couples.couple(stand_in, data, span[1]) is None
    kept = {**data, 'companions': (sheet['key'],)}
    assert couples.events(sheet, kept, span) == [] and couples.couple(sheet, kept, span[1]) is None
    day = found[0]['day']
    week = (day - timedelta(days=day.weekday()), day + timedelta(days=6 - day.weekday()))
    keys = {f"{sheet['key']}:{item['what']}" for item in found if week[0] <= item['day'] <= week[1]}
    assert not keys & {item['key'] for item in paper.couples_news(kept, week)}


def test_a_baby_is_never_named_after_a_word_in_one_of_the_citys_places():
    from companion.world import catalog
    data = catalog.city('baltimore')
    assert 'Emma' in families.place_words(data)  # Red Emma's
    world = type('World', (), {'find': staticmethod(lambda _text: data)})()
    names = {families.baby_name({'home_city': 'Baltimore'}, world, f'seed-{n}', 'she/her', set()) for n in range(300)}
    assert len(names) > 20 and not names & families.place_words(data)


def test_a_first_birthday_gift_fits_an_older_city(monkeypatch):
    import re

    from companion.life import big_days
    gifts = big_days.bank()['gifts']
    assert set(gifts['first_birthday']) < set(gifts['first_birthday_modern'])
    assert not any(re.search(r'\b(telephone|crayons?|cars?)\b', gift) for gift in gifts['first_birthday'])
    companion = {'version': {'definition': {'name': 'Mira'}}}
    for modern, key in ((True, 'first_birthday_modern'), (False, 'first_birthday')):
        monkeypatch.setattr(big_days, 'modern_city', lambda _connection, _companion, modern=modern: modern)
        found = {big_days.gift_for(None, companion, big_days.KINDS['first_birthday'], f'seed-{n}')[0] for n in range(60)}
        assert found <= set(gifts[key])


def test_every_pregnancy_line_reads_right_told_to_the_companion():
    row, names = {'cast_ids': '["p1"]'}, {'p1': {'name': 'Ana', 'role': 'sister'}}
    stages = [families.stage(date(2027, 1, 1), *families.announced('sibling', date(2027, 5, 1), 'family', {'name': 'Mira'})),
              families.stage(date(2027, 4, 1), "{a}'s baby is due any day now, and {name} keeps checking for news.", ''),
              families.stage(date(2027, 5, 1), *families.arrived({'name': 'Ivy', 'pronouns': 'she/her'}, 'godchild', {}))]
    told = ' '.join(storylines.fill(stage['text'], row, names, {'name': 'Mira'}, True) for stage in stages)
    assert 'you keep checking' in told and 'you keeps' not in told and 'Mira' not in told
