"""Back when (companion/back_when.py): go back to a past year with a companion, in a world of its own."""
import json
from datetime import date

import pytest
from conftest import send
from test_world_year import leaks

from companion import back_when, back_when_careers, back_when_rollback
from companion.database import decode
from companion.life import steps

MARRIED = 'Married to the user for ten years; they met at college.'


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def companion(client):
    return ok(client.post('/api/companion', json={
        'name': 'Mira Costa', 'identity': 'A 34-year-old nurse.', 'personality': 'Warm and curious',
        'timezone': 'America/New_York', 'home_city': 'baltimore', 'location': 'Fells Point, Baltimore',
        'relationship': 'romance', 'history_together': MARRIED, 'looks': {'age': 34}, 'birthday': '03-14'}))


def persona_age(client, age):
    world = ok(client.get('/api/worlds'))
    ok(client.patch(f"/api/worlds/personas/{world['active_persona_id']}", json={'age': age}))


def main(app) -> dict:
    with app.state.database.connect() as connection:
        from companion import characters
        return characters.require_current(connection)


def test_the_sheet_offers_three_moments_from_what_is_stored(client, companion):
    persona_age(client, 36)
    sheet = ok(client.get('/api/worlds/back-when'))
    assert sheet['available'] and not sheet['from_history'] and sheet['latest'] == 2025
    # Mira is 34 on 5 October 2026 with a March birthday: 18 in October 2010. The user, 36, was 18 in 2008.
    assert sheet['earliest'] == 2010
    labels = {moment['key']: moment for moment in sheet['moments']}
    assert len(sheet['moments']) == 3
    # Married ten years: the wedding in 2016, so the year before it is 2016 (5 October falls before the wedding day).
    assert labels['before:married']['year'] in (2015, 2016) and labels['before:married']['label'] == 'Before the wedding'
    assert labels['age:25'] == labels['age:25'] | {'label': 'When Mira was 25', 'year': 2017, 'age': 25,
                                                    'name': 'Back when · 2017'}
    # They met at college, at 19: 2011.
    assert labels['met']['year'] == 2011


def test_going_back_makes_a_world_in_that_year_with_everyone_younger(client, companion, app):
    persona_age(client, 36)
    circle = ok(client.get('/api/life/circle'))
    before = {person['id']: person['age'] for person in circle}
    view = ok(client.post('/api/worlds/back-when', json={'year': 2012}))
    world = view['world']
    assert world['name'] == 'Back when · 2012' and world['year'] == 2012 and world['active']
    assert world['used_at'].startswith('2026-10-05')  # Worlds are listed by when they were last used, in real time.
    assert world['back_when'] == {'year': 2012, 'name': 'Mira Costa', 'companion_id': companion['id']}
    database = app.state.database
    assert database.clock.now().year == 2012
    mira = main(app)
    definition = mira['version']['definition']
    assert mira['id'] == companion['id'] and definition['looks']['age'] == 20
    assert definition['identity'] == 'A 20-year-old nurse.'
    # Strangers, by default: nothing between the two of them yet.
    assert definition['relationship'] == 'friendship' and definition['starting_closeness'] == 1
    assert definition['history_together'] == back_when_rollback.STRANGERS
    with database.connect() as connection:
        assert not connection.execute("SELECT COUNT(*) FROM relationship_steps WHERE other='user'").fetchone()[0]
        assert connection.execute('SELECT age FROM persona').fetchone()[0] == 22
        assert not connection.execute('SELECT COUNT(*) FROM messages').fetchone()[0]
        people = {row['id']: decode(row['details']).get('age') for row in connection.execute(
            'SELECT id, details FROM circle_people')}
    for person_id, age in before.items():
        if person_id in people and isinstance(age, int):
            assert people[person_id] in (age - 15, age - 14, 0) or people[person_id] < 18
    # The world they left is as it was.
    first = next(item for item in view['personas'][0]['worlds'] if item['first'])
    ok(client.post(f"/api/worlds/{first['id']}/switch"))
    assert main(app)['version']['definition']['looks']['age'] == 34


def test_nothing_in_the_new_world_knows_a_later_date(client, companion, app):
    send(client, 'Morning!', 'client-0001')
    ok(client.get('/api/life/circle'))
    ok(client.post('/api/worlds/back-when', json={'year': 2012}))
    ok(client.get('/api/life/circle'))
    ok(client.get('/api/companion'))
    with app.state.database.connect() as connection:
        found = leaks(connection, 2013)
    assert not found, '\n'.join(found[:40])


def test_working_it_out_from_our_history_keeps_where_you_were(client, companion, app):
    ok(client.post('/api/worlds/back-when', json={'year': 2015, 'from_history': True}))
    definition = main(app)['version']['definition']
    assert definition['relationship'] == 'romance' and definition['history_together'] == 'You and the user met in 2011.'
    with app.state.database.connect() as connection:
        reached = [row['step'] for row in connection.execute(
            "SELECT step FROM relationship_steps WHERE other='user' ORDER BY reached_on")]
    assert reached and 'married' not in reached and reached[0] == 'dating'


def test_before_you_met_you_are_strangers_even_from_history(client, companion, app):
    ok(client.post('/api/worlds/back-when', json={'year': 2010, 'from_history': True}))
    assert main(app)['version']['definition']['history_together'] == back_when_rollback.STRANGERS


def test_it_goes_back_only_to_years_when_both_were_grown_up(client, companion):
    persona_age(client, 36)
    assert client.post('/api/worlds/back-when', json={'year': 2009}).status_code == 422
    persona_age(client, 20)
    sheet = ok(client.get('/api/worlds/back-when'))
    assert sheet['earliest'] == 2024
    assert client.post('/api/worlds/back-when', json={'year': 2020}).status_code == 422
    assert len(ok(client.get('/api/worlds'))['personas'][0]['worlds']) == 1


def test_it_starts_only_from_a_world_in_the_present(client, companion):
    ok(client.post('/api/worlds/back-when', json={'year': 2015}))
    assert client.get('/api/worlds/back-when').status_code == 409


def test_dates_written_as_history_are_worked_out_from_the_words():
    rows = [{'step': key, 'how': 'history', 'reached_on': '2026-10-05'} for key in ('dating', 'exclusive', 'love')]
    dated = back_when_rollback.written_dates('romance', rows, 'Together for 3 years.', date(2026, 10, 5))
    assert [item['step'] for item in dated] == ['dating', 'exclusive', 'love']
    assert dated[-1]['on'] == date(2023, 10, 5)
    assert dated[0]['on'] < dated[1]['on'] < dated[2]['on']
    assert back_when_rollback.years_in('married a decade') == 10
    assert back_when_rollback.years_in('best friends for a couple of years') == 2
    since = back_when_rollback.written_dates('friendship', [{'step': 'friends', 'how': 'history',
                                                             'reached_on': '2026-10-05'}], 'Friends since 2012.',
                                             date(2026, 10, 5))
    assert since[0]['on'] == date(2012, 10, 5)


def test_their_own_words_say_the_age_they_were():
    definition = {'identity': 'Mira, 34, a nurse. Aged 34 and 34 years old.', 'background': 'Born 1992; 34 cats.'}
    younger = back_when_rollback.younger_words(definition, 34, 25)
    assert younger['identity'] == 'Mira, 25, a nurse. Aged 25 and 25 years old.'
    assert younger['background'] == 'Born 1992; 34 cats.'


def test_steps_and_moments_name_every_step():
    for ladder in steps.LADDERS.values():
        assert {step.key for step in ladder[1:]} <= set(back_when.BEFORE_STEP)


def test_their_life_rolls_back_to_that_day(client, companion, app):
    """A chapter, a loss, a child and a partner from later: undone, alive, not born and not met yet."""
    people = ok(client.get('/api/life/circle'))
    dad = people[0]
    timeline = companion['active_timeline_id']
    stamp_ = '2025-01-01T12:00:00.000000+00:00'
    with app.state.database.connect(write=True) as connection:
        connection.execute("INSERT INTO life_chapters (id, timeline_id, kind, started_on, title, told, share, changes, "
                           "undo, created_at) VALUES ('chapter-1', ?, 'new_job', '2025-01-01', 'Mira started a new job', "
                           "'', '', '{\"career\": \"barista\"}', '{}', ?)", (timeline, stamp_))
        connection.execute("UPDATE circle_people SET status='removed', role='dad', details=json_set(details, '$.late', "
                           "'2024-05-01', '$.age', 60) WHERE id=?", (dad['id'],))
        connection.execute("INSERT INTO losses (id, timeline_id, kind, person_id, name, role, died_on, happened, "
                           "created_at, updated_at) VALUES ('loss-1', ?, 'circle', ?, 'Dad', 'dad', '2024-05-01', 1, ?, ?)",
                           (timeline, dad['id'], stamp_, stamp_))
        connection.execute("INSERT INTO circle_children (id, timeline_id, parent_id, storyline_id, name, pronouns, "
                           "title, born_on, status, created_at, updated_at) VALUES ('kid-1', ?, ?, ?, 'Leo', 'he/him', "
                           "'family', '2020-02-02', 'born', ?, ?)", (timeline, companion['id'], f'kids:{timeline}',
                                                                      stamp_, stamp_))
        connection.execute("INSERT INTO love_partners (id, timeline_id, companion_id, name, met_on, created_at) VALUES "
                           "('partner-1', ?, ?, 'Sam', '2024-03-03', ?)", (timeline, companion['id'], stamp_))
    ok(client.post('/api/worlds/back-when', json={'year': 2012}))
    with app.state.database.connect() as connection:
        for table in ('life_chapters', 'losses', 'circle_children', 'love_partners'):
            assert not connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0], table  # noqa: S608
        row = connection.execute('SELECT status, details FROM circle_people WHERE id=?', (dad['id'],)).fetchone()
    assert row['status'] == 'active' and 'late' not in decode(row['details'])
    assert main(app)['version']['definition'].get('money', {}).get('career') != 'barista'


def test_the_town_is_younger_and_only_the_grown_up_are_in_it(client, companion, app):
    """Townsfolk are 14 years younger in 2012: whoever wasn't 18 yet isn't in town, and a retiree was working."""
    hood = 'fells-point'
    now = {person['key']: person for person in ok(client.get(f'/api/world/cities/baltimore/neighborhoods/{hood}/people'))}
    ok(client.post('/api/worlds/back-when', json={'year': 2012}))
    then = {person['key']: person for person in ok(client.get(f'/api/world/cities/baltimore/neighborhoods/{hood}/people'))}
    assert then and set(then) < set(now)
    assert all(now[key]['age'] - person['age'] == 14 and person['age'] >= 18 for key, person in then.items())
    assert {key for key, person in now.items() if person['age'] < 32} == set(now) - set(then)
    retirees = [key for key, person in now.items() if person['occupation'] == 'retired' and key in then]
    assert retirees and any(then[key]['occupation'] != 'retired' for key in retirees)
    place = ok(client.get('/api/world/cities/baltimore'))['places'][0]['id']
    assert all(person['age'] >= 18 for person in ok(client.get(f'/api/world/cities/baltimore/places/{place}/people')))


def test_work_fits_their_age_and_the_year(client, companion, app):
    """A banker at 34 was at college at 20; a job from 2016 on wasn't there in 2012; a retired parent still worked."""
    people = ok(client.get('/api/life/circle'))
    with app.state.database.connect(write=True) as connection:
        version = connection.execute('SELECT id, definition FROM character_versions WHERE id=?',
                                     (main(app)['active_version_id'],)).fetchone()
        definition = decode(version['definition'])
        definition['money'] = {**(definition.get('money') or {}), 'career': 'finance-banker'}
        connection.execute('UPDATE character_versions SET definition=? WHERE id=?',
                           (json.dumps(definition), version['id']))
        details = decode(connection.execute('SELECT details FROM circle_people WHERE id=?',
                                            (people[0]['id'],)).fetchone()[0])
        connection.execute("UPDATE circle_people SET career='', details=? WHERE id=?",
                           (json.dumps(details | {'career': 'Retired', 'age': 68, 'local': True}), people[0]['id']))
        connection.execute("UPDATE circle_people SET career='subscription-creator', details=? WHERE id=?",
                           (json.dumps(decode(connection.execute('SELECT details FROM circle_people WHERE id=?',
                                                                 (people[1]['id'],)).fetchone()[0]) | {'age': 40}),
                            people[1]['id']))
    ok(client.post('/api/worlds/back-when', json={'year': 2012}))
    assert main(app)['version']['definition']['money']['career'] == 'undergraduate'
    with app.state.database.connect() as connection:
        rows = {row['id']: row for row in connection.execute('SELECT id, career, details FROM circle_people')}
    dad, other = rows[people[0]['id']], rows[people[1]['id']]
    assert dad['career'] and decode(dad['details'])['career'] != 'Retired' and decode(dad['details'])['age'] == 54
    assert other['career'] and other['career'] != 'subscription-creator'


def test_jobs_that_fit_stay_and_degree_work_waits():
    banker = {'id': 'finance-banker', 'pay': '$$$$'}
    assert back_when_careers.fits(banker, 30) and not back_when_careers.fits(banker, 20)
    assert not back_when_careers.fits(None, 30)
    assert not back_when_careers.fits({'id': 'undergraduate', 'pay': '$', 'ages': (18, 22)}, 30)
