"""Everyone gets older (companion/life/ages.py): one stored birth date each, ages that move on with birthdays."""
import re
from datetime import date, timedelta

import pytest
from conftest import reconcile

from companion.database import decode
from companion.images import content
from companion.life import ages, circle, composer, grooming, occasions, scrapbook
from companion.world import looks

DANA = {'name': 'Dana Reyes', 'identity': '34. Works as an ER nurse at Mercy. She/her.',
        'personality': 'Warm, dry sense of humour.', 'timezone': 'UTC'}


def connect(client, write=True):
    return client.app.state.database.connect(write=write)


def make(client, **changes) -> dict:
    response = client.post('/api/companion', json={**DANA, **changes})
    assert response.status_code == 200, response.text
    return response.json()


def link(client):
    response = client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                                   'api_key': 'secret-key'})
    assert response.status_code == 200, response.text


def revise(client, **changes) -> dict:
    version = client.get('/api/companion').json()['companion']['version']
    response = client.post('/api/companion/versions', json={'definition': {**version['definition'], **changes},
                                                             'expected_version_id': version['id']})
    assert response.status_code == 200, response.text
    return response.json()


def sync(client, clock):
    with connect(client) as connection:
        return ages.sync(connection, clock.now())


def age_of(client, day: date) -> int | None:
    companion = client.get('/api/companion').json()['companion']
    with connect(client, False) as connection:
        return ages.companion_age(connection, companion['id'], companion['version']['definition'], day)


def test_dates_ages_and_milestones_by_the_calendar():
    today = date(2026, 10, 18)
    assert ages.born_from(34, '10-19', today) == date(1991, 10, 19)
    assert ages.born_from(34, '10-18', today) == date(1992, 10, 18)
    born = ages.born_from(34, '02-29', today)
    assert ages.age_on(born, '02-29', date(2027, 2, 27)) == 34 and ages.age_on(born, '02-29', date(2027, 2, 28)) == 35
    assert ages.age_on(born, '02-29', date(2028, 2, 28)) == 35 and ages.age_on(born, '02-29', date(2028, 2, 29)) == 36
    assert [age for age in range(18, 101) if ages.milestone(age)] == [30, 40, 50, 60, 70, 80, 90, 100]
    assert [ages.ordinal(n) for n in (21, 22, 23, 40, 111, 112)] == ['21st', '22nd', '23rd', '40th', '111th', '112th']


def test_a_companion_gets_older_on_their_birthday_and_their_prompt_says_so(client, clock):
    birthday = (clock.now() + timedelta(days=2)).strftime('%m-%d')
    make(client, birthday=birthday)
    link(client)
    today = clock.now().date()
    assert age_of(client, today) == 34  # Nothing stored yet: the age written.
    sync(client, clock)
    assert age_of(client, today) == 34 and age_of(client, today + timedelta(days=2)) == 35
    reconcile(client)
    assert 'You are 35 now' not in client.get('/api/context/preview').json()['system']
    clock.advance(timedelta(days=3))
    reconcile(client)
    system = client.get('/api/context/preview').json()['system']
    turned = clock.now().date() - timedelta(days=1)
    assert 'Identity: 34. Works as an ER nurse' in system  # Their own words stay as written.
    assert 'Looks: 35 years old' in system
    assert f"You are 35 now; you turned 35 on {turned.day} {turned.strftime('%B')}." in system


def test_the_form_always_wins_and_keeping_their_age_holds_the_age_they_are(client, clock):
    make(client, birthday=(clock.now() + timedelta(days=1)).strftime('%m-%d'))
    sync(client, clock)
    later = clock.now().date() + timedelta(days=200)
    assert age_of(client, later) == 35
    revise(client, identity='40. Works as an ER nurse at Mercy. She/her.')
    sync(client, clock)
    assert age_of(client, clock.now().date()) == 40 and age_of(client, later) == 41
    clock.advance(timedelta(days=30))  # They turned 41.
    revise(client, keeps_age=True)
    sync(client, clock)
    # Held at the age they are, not sent back to the 40 written (Iris, v0.14).
    assert age_of(client, clock.now().date()) == 41 and age_of(client, later + timedelta(days=400)) == 41
    with connect(client, False) as connection:
        companion = client.get('/api/companion').json()['companion']
        assert ages.turns_on(connection, companion['id'], companion['version']['definition'], later) is None
        line = ages.age_line(connection, companion['id'], companion['version']['definition'],
                             clock.now().date() + timedelta(days=400))
    turned = clock.now().date() - timedelta(days=29)
    assert line == f"You are 41 now; you turned 41 on {turned.day} {turned.strftime('%B')}."
    clock.advance(timedelta(days=500))
    sync(client, clock)
    revise(client, keeps_age=False)  # Let go, they carry on from 41 with no jump.
    assert age_of(client, clock.now().date()) == 41
    sync(client, clock)
    today = clock.now().date()
    assert age_of(client, today) == 41 and age_of(client, today + timedelta(days=366)) == 42


def test_only_the_birthday_changing_keeps_the_age_they_are(client, clock):
    make(client, birthday=(clock.now() + timedelta(days=1)).strftime('%m-%d'))
    sync(client, clock)
    clock.advance(timedelta(days=5))  # They turned 35.
    sync(client, clock)
    revise(client, birthday=(clock.now() + timedelta(days=10)).strftime('%m-%d'))
    sync(client, clock)
    assert age_of(client, clock.now().date()) == 35 and age_of(client, clock.now().date() + timedelta(days=10)) == 36


def test_someone_who_reads_as_under_18_never_gets_a_date(client, clock):
    make(client, identity='17. Still in school.')
    sync(client, clock)
    with connect(client, False) as connection:
        assert connection.execute("SELECT COUNT(*) FROM birth_dates WHERE kind='companion'").fetchone()[0] == 0
    assert age_of(client, clock.now().date()) is None


def test_the_circle_ages_in_their_rows_and_milestones_reach_the_occasions(client, clock, monkeypatch):
    make(client, home_city='baltimore', location='Hampden, Baltimore')  # A circle from the city's people has ages.
    client.get('/api/life/circle')
    with connect(client, False) as connection:
        person = next(dict(row) for row in connection.execute('SELECT * FROM circle_people')
                      if isinstance(decode(row['details']).get('age'), int))
    sync(client, clock)
    with connect(client, False) as connection:
        before = decode(connection.execute('SELECT details FROM circle_people WHERE id=?', (person['id'],))
                        .fetchone()[0])['age']
        row = ages.stored(connection, 'circle', person['id'])
    assert row['from_age'] == before and row['birthday'] == circle.birthday(person['id'])
    clock.advance(timedelta(days=366))
    assert sync(client, clock) >= 1
    with connect(client, False) as connection:
        after = decode(connection.execute('SELECT details FROM circle_people WHERE id=?', (person['id'],))
                       .fetchone()[0])['age']
    assert after == before + 1
    # A birthday that is a milestone is named: theirs is moved to two days from now and turns them a round number.
    target = 10 * (after // 10 + 1)
    monkeypatch.setattr(occasions, 'SEEDED', True)
    monkeypatch.setattr(occasions, 'own_birthday', lambda _companion: None)
    today = clock.now().date()
    monkeypatch.setattr(circle, 'birthday', lambda person_id: (today + timedelta(days=2) if person_id == person['id']
                                                               else today + timedelta(days=40)).strftime('%m-%d'))
    with connect(client) as connection:
        connection.execute('UPDATE birth_dates SET born_on=?, birthday=? WHERE kind=? AND person_key=?',
                           (ages.born_from(target - 1, circle.birthday(person['id']), today).isoformat(),
                            circle.birthday(person['id']), 'circle', person['id']))
    found = client.get('/api/today').json()['occasions']
    item = next(item for item in found if item['kind'] == 'circle_birthday')
    assert item['turns'] == target and f"{ages.ordinal(target)} birthday" in item['text']


def test_a_milestone_birthday_is_a_party_in_the_occasions_the_day_and_the_scrapbook(client, clock):
    birthday = (clock.now() + timedelta(days=1)).strftime('%m-%d')
    make(client, identity='39. Works as an ER nurse at Mercy. She/her.', birthday=birthday)
    sync(client, clock)
    found = client.get('/api/today').json()['occasions']
    own = next(item for item in found if item['kind'] == 'own_birthday')
    assert own['turns'] == 40 and 'your 40th birthday, a big one' in own['text']
    clock.advance(timedelta(days=1))
    own = next(item for item in client.get('/api/today').json()['occasions'] if item['kind'] == 'own_birthday')
    assert own['template'] == "Guess who's 40 today."
    slot = {'local_date': clock.now().date().isoformat(),
            'block': {'kind': 'social', 'start': '19:00', 'end': '23:00', 'key': 'evening', 'label': 'Evening'}}
    definition = {'name': 'Dana', 'own_birthday': birthday, 'milestones': {slot['local_date']: 40}}
    party = composer.own_birthday(slot, definition, None, 'seed', (), [{'id': 'p1', 'name': 'Jo'}], None)
    assert 'turning 40' in party['summary'] and '{' not in party['post']
    plain = composer.own_birthday(slot, {**definition, 'milestones': {}}, None, 'seed', (), [], None)
    assert 'turning' not in plain['summary']
    companion = client.get('/api/companion').json()['companion']
    with connect(client, False) as connection:
        items = ages.milestones_between(connection, companion, clock.now().date() - timedelta(days=5),
                                        clock.now().date())
    assert {'date': clock.now().date().isoformat(), 'text': 'Dana Reyes turned 40'} in items
    period = {'start': clock.now().date() - timedelta(days=5), 'end': clock.now().date()}
    with connect(client, False) as connection:
        page = scrapbook.their_year(connection, companion, period, 'Dana Reyes')
    assert {'date': clock.now().date().isoformat(), 'text': 'Dana Reyes turned 40'} in page['items']


def test_townsfolk_turn_a_year_older_on_their_seeded_birthdays(client, companion, clock):
    sheet = {'key': 'town:testtown:cafe:0', 'seed': 'seed-a', 'age': 40}
    with connect(client) as connection:
        connection.execute("DELETE FROM birth_dates WHERE kind='town'")  # Making a companion started it.
        assert ages.town_age(connection, sheet, clock.now().date() + timedelta(days=800)) == 40  # Not started yet.
        ages.sync(connection, clock.now())
        start = ages.town_began(connection)
        assert ages.town_age(connection, sheet, start) == 40
        assert ages.town_age(connection, sheet, start + timedelta(days=366)) == 41
        assert ages.town_age(connection, sheet, start + timedelta(days=365 * 3 + 2)) == 43


def test_the_age_bank_is_big_specific_and_safe():
    bank = grooming.ageing_bank()
    for kind in ('grey', 'lines', 'reading'):
        texts = [entry['text'] for entry in bank[kind]]
        assert len(texts) >= 100 and len(set(texts)) == len(texts), kind
        assert {entry['stage'] for entry in bank[kind]} <= {1, 2, 3}
        for text in texts:
            assert not re.search(r'\b(?:she|he|her|his|him|they)\b', text), text
            assert content.classify({'prompt': f'A woman with {text}.'}).tier == content.SAFE, text


def test_looks_drift_with_age_only_after_their_date_and_never_over_what_the_user_wrote(client, clock, monkeypatch):
    monkeypatch.setattr(grooming, 'AGE_SIGNS', {'grey': (36, 36), 'lines': (36, 36), 'reading': (36, 36)})
    # A seeded dye job or new glasses would keep a sign out.
    monkeypatch.setattr(grooming.Draw, 'bold', lambda *args: None)
    make(client, birthday=(clock.now() + timedelta(days=1)).strftime('%m-%d'))
    sync(client, clock)
    companion = client.get('/api/companion').json()['companion']
    definition = companion['version']['definition']
    with connect(client) as connection:
        grooming.ensure(connection, companion['active_timeline_id'], definition, None, clock.now())
        at_35 = grooming.sheet(connection, companion['id'], definition, clock.now().date() + timedelta(days=30))
        at_36 = grooming.sheet(connection, companion['id'], definition, clock.now().date() + timedelta(days=400))
        written = {**definition, 'appearance': 'Long black hair and laugh lines she earned.'}
        own = grooming.sheet(connection, companion['id'], written, clock.now().date() + timedelta(days=400))
    assert at_35['age'] == 35 and not at_35.get('age_signs')
    # Reading glasses never come to someone whose seeded looks already have glasses, nor lines to seeded laugh lines.
    feature = at_35.get('feature') or ''
    kinds = ('grey',) + (() if grooming.LINES_WORDS.search(feature) else ('lines',)) + \
        (() if 'glasses' in feature else ('reading',))
    # Bank lines can hold commas, so each kind is looked for rather than counted.
    assert at_36['age'] == 36 and all(any(entry['text'] in at_36['age_signs'] for entry in grooming.ageing_bank()[kind])
                                      for kind in kinds)
    assert at_36['age_signs'] in looks.text(at_36) and at_36['age_signs'].split(', ')[0] in looks.picture(at_36, 'she')
    lines = {entry['text'] for entry in grooming.ageing_bank()['lines']}
    grey = {entry['text'] for entry in grooming.ageing_bank()['grey']}
    assert not set(own.get('age_signs', '').split(', ')) & (lines | grey)


def test_starting_over_forgets_their_dates(client, companion, clock):
    client.get('/api/life/circle')
    sync(client, clock)
    with connect(client, False) as connection:
        assert connection.execute("SELECT COUNT(*) FROM birth_dates WHERE kind IN ('companion', 'circle')").fetchone()[0]
    response = client.post('/api/companion/start-over', json={'name': 'Mira'})
    assert response.status_code == 200, response.text
    with connect(client, False) as connection:
        assert connection.execute('SELECT COUNT(*) FROM birth_dates').fetchone()[0] == 0


@pytest.mark.parametrize('identity, expected', [('34. A nurse.', 34), ('In her thirties, a nurse.', 35)])
def test_the_age_written_is_where_their_date_starts(identity, expected):
    assert ages.written_age('c1', {'name': 'Dana', 'identity': identity}) == expected


def test_signs_settled_in_for_years_keep_their_latest_stage(client, clock, monkeypatch):
    # Reading glasses have one stage in the bank; years after they came, the sheet still builds and keeps them.
    monkeypatch.setattr(grooming, 'AGE_SIGNS', {'reading': (36, 36)})
    monkeypatch.setattr(grooming.Draw, 'bold', lambda *args: None)
    make(client, birthday=(clock.now() + timedelta(days=1)).strftime('%m-%d'))
    sync(client, clock)
    companion = client.get('/api/companion').json()['companion']
    definition = companion['version']['definition']
    readers = {entry['text'] for entry in grooming.ageing_bank()['reading']}
    drawn = looks.for_companion
    monkeypatch.setattr(looks, 'for_companion', lambda *args: {**drawn(*args), 'feature': 'dimples'})
    with connect(client) as connection:
        grooming.ensure(connection, companion['active_timeline_id'], definition, None, clock.now())
        later = [grooming.sheet(connection, companion['id'], definition, clock.now().date() + timedelta(days=365 * years))
                 for years in (2, 9, 20)]
    assert [sheet['age'] for sheet in later] == [36, 43, 54]
    assert all(sheet['age_signs'] in readers for sheet in later) and len({sheet['age_signs'] for sheet in later}) == 1


def test_no_grey_coming_in_on_a_shaved_head_or_hair_already_grey(client, clock, monkeypatch):
    monkeypatch.setattr(grooming, 'AGE_SIGNS', {'grey': (36, 36), 'reading': (36, 36), 'lines': (36, 36)})
    monkeypatch.setattr(grooming.Draw, 'bold', lambda *args: None)
    make(client, birthday=(clock.now() + timedelta(days=1)).strftime('%m-%d'))
    sync(client, clock)
    companion = client.get('/api/companion').json()['companion']
    definition = companion['version']['definition']
    drawn = looks.for_companion
    grey = {entry['text'] for entry in grooming.ageing_bank()['grey']}
    lines = {entry['text'] for entry in grooming.ageing_bank()['lines']}
    found = {}
    for hair, feature in (('a shaved head', 'dimples'), ('greying brown hair, short', 'laugh lines')):
        monkeypatch.setattr(looks, 'for_companion', lambda *args, hair=hair, feature=feature: {
            **drawn(*args), 'hair': hair, 'feature': feature})
        with connect(client) as connection:
            grooming.ensure(connection, companion['active_timeline_id'], definition, None, clock.now())
            found[hair] = grooming.sheet(connection, companion['id'], definition,
                                         clock.now().date() + timedelta(days=400))['age_signs'].split(', ')
    assert not set(found['a shaved head']) & grey and not any('hair' in sign for sign in found['a shaved head'])
    assert set(found['a shaved head']) & lines  # Lines and readers still come.
    assert not set(found['greying brown hair, short']) & (grey | lines)  # Laugh lines drawn already: not twice.


def test_a_birthday_soon_after_they_were_made_is_not_lost_before_a_tick(client, clock):
    # No background tick here (life_tasks off): making them and the user coming back are enough to age them.
    make(client, birthday=(clock.now() + timedelta(days=2)).strftime('%m-%d'))
    link(client)
    with connect(client, False) as connection:
        assert connection.execute("SELECT from_age FROM birth_dates WHERE kind='companion'").fetchone()[0] == 34
    clock.advance(timedelta(days=3))
    reconcile(client)
    assert 'You are 35 now' in client.get('/api/context/preview').json()['system']


def test_someone_who_keeps_their_age_is_not_a_year_older_on_their_birthday(client, clock):
    make(client, birthday=clock.now().strftime('%m-%d'), keeps_age=True)
    companion = client.get('/api/companion').json()['companion']
    with connect(client, False) as connection:
        own = next(item for item in occasions.occasions(connection, companion, clock.now()) if item['kind'] == 'own_birthday')
    assert own['days'] == 0 and own['template'] == occasions.KEPT_TEMPLATE and 'older' not in own['template']
    revise(client, keeps_age=False)
    companion = client.get('/api/companion').json()['companion']
    with connect(client, False) as connection:
        own = next(item for item in occasions.occasions(connection, companion, clock.now()) if item['kind'] == 'own_birthday')
    assert own['template'] == "Guess who's a year older today."


def test_a_townsperson_is_their_age_now_on_matchlight_and_when_they_become_a_companion(client, clock, monkeypatch):
    from test_cast import met_someone

    from companion import dating as app
    from companion.life import encounters
    from companion.world import townsfolk
    monkeypatch.setattr(encounters, 'ACTIVE', True)
    monkeypatch.setattr(encounters, 'CHANCE', 1)
    monkeypatch.setattr(encounters, 'FAMILIAR_CHANCE', 1)
    _mira, person = met_someone(client, clock)
    seeded = person['age']
    sync(client, clock)
    clock.instant = clock.now() + timedelta(days=365 * 3 + 2)
    known = next(found for found in client.get('/api/life/townsfolk').json() if found['key'] == person['key'])
    assert known['age'] == seeded + 3
    drafted = client.get('/api/companion/cast/draft', params={'key': person['key']}).json()
    assert drafted['person']['age'] == seeded + 3 and drafted['definition']['identity'].startswith(str(seeded + 3))
    assert drafted['definition']['looks']['age'] == seeded + 3
    client.put('/api/dating/profile', json={'name': 'Sam', 'age': 30, 'gender': 'man', 'interested_in': ['woman', 'man'],
                                            'looking_for': 'serious', 'age_min': 18, 'age_max': 90, 'bio': ''})
    deck = client.get('/api/dating').json()['deck']
    with connect(client, False) as connection:
        data = app.looking_in(connection, app.profile(connection))
        for card in deck:
            sheet = townsfolk.find(data, card['key'])
            assert card['age'] == ages.town_age(connection, sheet, clock.now().date()) > sheet['age'] - 1
    assert any(card['age'] > townsfolk.find(data, card['key'])['age'] for card in deck)
