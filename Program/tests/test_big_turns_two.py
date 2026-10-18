"""Life's big turns, part 2: starting a business, a health turn and caring for a parent."""
import json
from datetime import date, timedelta

import pytest
from conftest import reconcile
from test_big_turns import begun, details, make, next_stage
from test_chapters import arrange, current

from companion import consequences
from companion.life import big_turns, business, chapters, circle, health_turns, kitchen, money


@pytest.fixture
def mira(client, monkeypatch):
    make(client, monkeypatch, 'Mira is 34, an accountant.')


@pytest.fixture
def older(client, monkeypatch):
    make(client, monkeypatch, 'Mira is 58, an accountant.')


def land(monkeypatch, choice: str, option: int):
    """The engine's dice land on `option` for `choice`, and on the likeliest option elsewhere (chapter:next keeps
    what arrange set)."""
    earlier = consequences.roll
    count = len(consequences.tables()[choice]['options'])

    def roll(seed, found):
        return option if seed.endswith(f':{choice}') and len(found) == count else earlier(seed, found)
    monkeypatch.setattr(consequences, 'roll', roll)


def parent(client, age: int = 72) -> dict:
    """Their mom in the circle, local and getting on."""
    companion = current(client)
    with client.app.state.database.connect(write=True) as connection:
        people = circle.people(connection, companion['active_timeline_id'])
        person = people[0]
        found = json.loads(person['details'])
        connection.execute("UPDATE circle_people SET role='mom', details=? WHERE id=?",
                           (json.dumps({**found, 'age': age, 'local': True}), person['id']))
        for other in people[1:]:
            if circle.role_kind(other['role']) == 'parent':
                connection.execute("UPDATE circle_people SET role='friend' WHERE id=?", (other['id'],))
    return person


def budget(client, clock) -> dict:
    with client.app.state.database.connect() as connection:
        companion = current(client)
        definition = companion['version']['definition']
        today = clock.now().date()
        return money.snapshot(definition, today.isoformat(),
                              money.household(connection, companion['active_timeline_id'], definition, today))


def test_the_new_banks_have_a_hundred_of_each_for_every_era():
    for bank in ('businesses', 'conditions'):
        for era in ('modern', 'jazz-age', 'other'):
            entries = big_turns.data()[bank][era]
            assert len(entries) >= 100 and len({json.dumps(entry) for entry in entries}) == len(entries)
    for era in big_turns.data()['businesses'].values():
        assert all(entry['label'].startswith('Running the ') and 1 <= entry['cost'] <= 6 for entry in era)
    for era in big_turns.data()['conditions'].values():
        assert all(entry['avoid'] in (None, *kitchen.AVOIDS) and 2 <= entry['every'] <= 26 for entry in era)


def test_a_business_opens_runs_their_week_and_pays_what_it_makes(client, mira, clock, monkeypatch):
    chapter = begun(client, monkeypatch, clock, 'business')
    found = details(client, chapter['id'])
    assert chapter['stage'] == 'planning' and found['business']['business'] in chapter['title']
    assert 'Starting ' in client.get('/api/life/chapters/lately').json()['now'][0]['line']

    next_stage(client, clock, chapter['id'])
    definition = current(client)['version']['definition']
    work = [block for block in definition['schedule'] if block['kind'] == 'work']
    assert work and all(block['label'] == found['business']['label'] for block in work)
    view = budget(client, clock)
    assert view['business'] == business.noun(found['business'])
    assert any(item['for'] == 'business' and item['savings'] for item in view['bought'])
    with client.app.state.database.connect() as connection:
        pay = big_turns.pay(connection, current(client)['active_timeline_id'], clock.now().date(), {'factor': 1})
    assert pay['factor'] == business.START
    assert f"- Your {view['business']} brings in about" in client.get('/api/context/preview').json()['prompt']

    from test_big_turns import plannable
    assert not plannable(client, 'new_job')  # Running a business of their own.
    land(monkeypatch, business.CHOICE, 0)
    next_stage(client, clock, chapter['id'])
    found = details(client, chapter['id'])
    assert found['how'] == 'grows' and found['factor'] == business.START + business.GROW
    assert client.get('/api/life/chapters').json()[0]['title'].endswith('is growing')


def test_a_business_that_folds_sends_them_back_to_work_and_never_folds_on_gentle(client, mira, clock, monkeypatch):
    chapter = begun(client, monkeypatch, clock, 'business')
    next_stage(client, clock, chapter['id'])
    land(monkeypatch, business.CHOICE, 3)
    next_stage(client, clock, chapter['id'])
    found = details(client, chapter['id'])
    assert found['stage'] == 'folded'
    definition = current(client)['version']['definition']
    assert not definition.get('business') and not any(block['label'].startswith('Running the')
                                                     for block in definition['schedule'])
    assert budget(client, clock)['between_jobs']
    next_stage(client, clock, chapter['id'])
    assert details(client, chapter['id'])['stage'] == 'back'
    assert not budget(client, clock)['between_jobs']

    names = {'name': 'Mira', 'a': 'bakery', 'b': ''}
    gentle = consequences.odds(business.CHOICE, {'turns': 1, 'checks': 1, 'factor': 4}, names)
    assert gentle[3]['odds'] == 0


def test_a_health_turn_brings_check_ups_a_diet_and_marks_that_undo_takes_back(client, older, clock, monkeypatch):
    chapter = begun(client, monkeypatch, clock, 'health')
    found = details(client, chapter['id'])
    assert chapter['title'] == 'Mira is waiting on test results'
    with client.app.state.database.connect() as connection:
        results = connection.execute("SELECT * FROM life_admin WHERE source='health'").fetchall()
    assert [(row['kind'], row['title']) for row in results] == [('results', 'Test results')]

    condition = {**found['condition'], 'avoid': 'gluten', 'every': 4}
    with client.app.state.database.connect(write=True) as connection:
        connection.execute("UPDATE life_chapters SET details=json_set(details, '$.condition', json(?)) WHERE id=?",
                           (json.dumps(condition), chapter['id']))
    land(monkeypatch, health_turns.OUTLOOK, 1)
    next_stage(client, clock, chapter['id'])
    found = details(client, chapter['id'])
    assert found['stage'] == 'managing' and found['outlook'] == 'harder' and found['every'] == 2
    definition = current(client)['version']['definition']
    assert definition['health']['avoid'] == 'gluten'
    assert 'gluten' in kitchen.with_health({'avoids': []}, definition)['avoids']
    with client.app.state.database.connect() as connection:
        checkups = connection.execute("SELECT * FROM life_admin WHERE source='health' AND kind='checkup'").fetchall()
        assert checkups and checkups[0]['title'] == condition['checkup']
        assert consequences.total(connection, current(client)['active_timeline_id'],
                                  f"companion:{current(client)['id']}", 'mood', clock.now().date().isoformat()) < 0
    assert 'Living with' in client.get('/api/life/chapters/lately').json()['now'][0]['line']

    client.post(f"/api/life/chapters/{chapter['id']}/undo")
    assert not current(client)['version']['definition'].get('health')
    with client.app.state.database.connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM marks').fetchone()[0] == 0
        assert {row['status'] for row in connection.execute("SELECT status FROM life_admin WHERE source='health' AND "
                                                            "local_date>?", (clock.now().date().isoformat(),))} \
            <= {'removed'}


def test_caring_for_a_parent_takes_evenings_and_money_until_they_are_better(client, mira, clock, monkeypatch):
    reconcile(client)
    mom = parent(client)
    chapter = begun(client, monkeypatch, clock, 'caring')
    found = details(client, chapter['id'])
    assert found['parent'] == mom['id'] and found['caring']['label'] == "Evening at Mom's"
    assert 'mom' in chapter['title']

    next_stage(client, clock, chapter['id'])
    schedule = current(client)['version']['definition']['schedule']
    [care] = [block for block in schedule if 'caring' in block.get('themes', ())]
    assert care['kind'] == 'errand' and care['days'] == found['caring']['days']
    with client.app.state.database.connect() as connection:
        timeline = current(client)['active_timeline_id']
        costs = health_turns.purchases(connection, timeline, clock.now().date() - timedelta(days=2),
                                       clock.now().date() + timedelta(days=40))
        assert costs and costs[0]['for'] == 'care'
        assert consequences.total(connection, timeline, f"companion:{current(client)['id']}", 'money',
                                  clock.now().date().isoformat()) < 0

    land(monkeypatch, health_turns.HOW, 2)
    next_stage(client, clock, chapter['id'])
    assert details(client, chapter['id'])['outlook'] == 'declining'
    with client.app.state.database.connect() as connection:
        assert [item['person_id'] for item in health_turns.frail(connection, timeline)] == [mom['id']]

    land(monkeypatch, health_turns.HOW, 0)
    next_stage(client, clock, chapter['id'])
    assert details(client, chapter['id'])['stage'] == 'eased'
    assert not any('caring' in block.get('themes', ()) for block in current(client)['version']['definition']['schedule'])


def test_no_parent_who_needs_care_means_no_caring(client, mira, clock, monkeypatch):
    reconcile(client)
    parent(client, age=50)
    arrange(client, monkeypatch, clock, 'caring')
    reconcile(client)
    assert client.get('/api/life/chapters').json() == []


def test_the_odds_read_age_and_a_parent_in_treatment():
    names = {'name': 'Mira', 'a': 'someone', 'b': ''}
    every = {f'can_{kind}': 1 for kind in chapters.KINDS}
    young = consequences.odds(chapters.CHOICE, {'drama': 1, 'friends': 4, 'age': 25, **every}, names)
    old = consequences.odds(chapters.CHOICE, {'drama': 1, 'friends': 4, 'age': 66, **every}, names)
    health = chapters.KINDS.index('health')
    assert old[health]['odds'] > young[health]['odds']
    ill = consequences.odds(chapters.CHOICE, {'drama': 1, 'friends': 4, 'parent_ill': 1, **every}, names)
    caring = chapters.KINDS.index('caring')
    assert ill[caring]['odds'] > young[caring]['odds'] and "Mira's parent just started treatment" in ill[caring]['reasons']


def test_gentle_keeps_health_turns_and_caring_away(client, mira):
    client.put('/api/life/settings', json={'life_turns': 1})
    with client.app.state.database.connect() as connection:
        assert not big_turns.allowed(connection, 'health') and not big_turns.allowed(connection, 'caring')
        assert big_turns.allowed(connection, 'business')


def test_make_it_go_this_way_reaches_the_part_two_turns(client, older, clock, monkeypatch):
    reconcile(client)
    parent(client, 78)
    chapter = begun(client, monkeypatch, clock, 'hobby')
    for kind in ('business', 'health', 'caring'):
        response = client.post(f"/api/life/consequences/{chapter['consequence']}/change",
                               json={'option': chapters.KINDS.index(kind)})
        assert response.status_code == 200, response.text
        assert client.get('/api/life/chapters').json()[0]['kind'] == kind
    assert client.post(f"/api/life/consequences/{chapter['consequence']}/change",
                       json={'option': len(chapters.KINDS)}).status_code == 422


def test_a_saturday_at_a_parents_out_of_town_is_a_day_not_an_evening():
    companion = {'version': {'definition': {'name': 'Mira Lane'}}}
    slot = {'from': 'saturday', 'days': [5], 'start': '10:00', 'end': '17:00', 'label': "Day at Mom's"}
    details = {'role': 'mom', 'name': 'Ana', 'caring': slot}
    found = health_turns.care_begins(None, companion, {}, details, date(2027, 1, 2), None)
    assert found['share'].startswith("First day at my mom's")
    evening = health_turns.care_begins(None, companion, {}, {**details, 'caring': {**slot, 'start': '18:00'}},
                                       date(2027, 1, 2), None)
    assert evening['share'].startswith("First evening at my mom's")
