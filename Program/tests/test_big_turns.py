"""Life's big turns: back to school, a career change, buying a place and retirement, each in stages over months."""
import json
from datetime import date, timedelta

import pytest
from conftest import reconcile
from test_chapters import arrange, current, items
from test_storylines import WORKDAY

from companion import consequences
from companion.life import admin, big_turns, chapters, money, storylines
from companion.world import turnover


def make(client, monkeypatch, identity: str):
    from companion.life import body
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    monkeypatch.setattr(storylines, 'STORIES', ())
    response = client.post('/api/companion', json={
        'name': 'Mira Lane', 'timezone': 'UTC', 'schedule': WORKDAY, 'location': 'Fells Point, Baltimore',
        'identity': identity, 'money': {'career': 'accountant'}})
    assert response.status_code == 200, response.text


@pytest.fixture
def mira(client, monkeypatch):
    make(client, monkeypatch, 'Mira is 34, an accountant.')


@pytest.fixture
def older(client, monkeypatch):
    make(client, monkeypatch, 'Mira is 64, an accountant.')


def begun(client, monkeypatch, clock, kind: str) -> dict:
    arrange(client, monkeypatch, clock, kind)
    reconcile(client)
    listed = [item for item in client.get('/api/life/chapters').json() if item['kind'] != 'move_in']
    assert [item['kind'] for item in listed] == [kind], listed
    return listed[0]


def details(client, chapter_id: str) -> dict:
    with client.app.state.database.connect() as connection:
        row = connection.execute('SELECT details FROM life_chapters WHERE id=?', (chapter_id,)).fetchone()
    return json.loads(row['details'])


def next_stage(client, clock, chapter_id: str):
    """Bring the next stage to tomorrow and let a day pass."""
    tomorrow = (clock.now() + timedelta(days=1)).date().isoformat()
    with client.app.state.database.connect(write=True) as connection:
        connection.execute("UPDATE life_chapters SET details=json_set(details, '$.next_on', ?) WHERE id=?",
                           (tomorrow, chapter_id))
    clock.advance(timedelta(days=1))
    reconcile(client)


def test_the_banks_have_a_hundred_of_each_for_every_era():
    for bank in ('courses', 'retirement'):
        for era in ('modern', 'jazz-age', 'other'):
            entries = big_turns.data()[bank][era]
            assert len(entries) >= 100 and len({json.dumps(entry) for entry in entries}) == len(entries)
    assert all(3 <= course['months'] <= 36 for era in big_turns.data()['courses'].values() for course in era)


def test_back_to_school_carves_a_class_out_of_their_evenings_until_they_graduate(client, mira, clock, monkeypatch):
    chapter = begun(client, monkeypatch, clock, 'school')
    found = details(client, chapter['id'])
    assert chapter['stage'] == 'enrolled' and found['course'] in chapter['title']
    assert not any(block['kind'] == 'study' for block in current(client)['version']['definition']['schedule'])
    assert 'Signed up for' in client.get('/api/life/chapters/lately').json()['now'][0]['line']

    next_stage(client, clock, chapter['id'])
    schedule = current(client)['version']['definition']['schedule']
    [study] = [block for block in schedule if block['kind'] == 'study']
    evening = next(block for block in schedule if block['key'] == 'evening')
    assert study['days'] == found['study']['days'] and not set(study['days']) & set(evening['days'])
    assert study['label'].endswith(' class') and study['start'] == '18:00'
    prompt = client.get('/api/context/preview').json()['prompt']
    assert f"You started {found['course']}: classes are on" in prompt
    with client.app.state.database.connect() as connection:
        days = big_turns.big_days(connection, current(client)['active_timeline_id'], '2000-01-01', '2100-01-01')
    assert [(day['kind'], day['on']) for day in days] == [('graduation', found['ends_on'])]

    next_stage(client, clock, chapter['id'])
    assert not any(block['kind'] == 'study' for block in current(client)['version']['definition']['schedule'])
    listed = client.get('/api/life/chapters').json()
    assert listed[0]['stage'] == 'graduated' and listed[0]['title'].endswith('and graduated')
    lately = client.get('/api/life/chapters/lately').json()
    assert lately['now'] == [] and lately['lately'][0]['title'] == listed[0]['title']


def test_exams_go_on_the_calendar_and_fees_into_the_budget(client, mira, clock, monkeypatch):
    chapter = begun(client, monkeypatch, clock, 'school')
    found = details(client, chapter['id'])
    assert found['fees'] and found['exams'][-1] < found['ends_on']
    with client.app.state.database.connect(write=True) as connection:
        soon = (clock.now() + timedelta(days=10)).date().isoformat()
        connection.execute("UPDATE life_chapters SET details=json_set(details, '$.exams', json_array(?)) WHERE id=?",
                           (soon, chapter['id']))
    next_stage(client, clock, chapter['id'])
    with client.app.state.database.connect() as connection:
        exams = connection.execute("SELECT * FROM life_admin WHERE source='school'").fetchall()
        assert [(row['kind'], row['fixed']) for row in exams] == [('exam', 1)]
        assert soon <= exams[0]['local_date'] <= (date.fromisoformat(soon) + timedelta(days=3)).isoformat()
        timeline = current(client)['active_timeline_id']
        fee = found['fees'][0]
        bought = big_turns.purchases(connection, timeline, date.fromisoformat(fee['on']),
                                     date.fromisoformat(fee['on']))
    assert bought[0]['cost'] == fee['cost'] and bought[0]['for'] == 'school'
    client.post(f"/api/life/chapters/{chapter['id']}/undo")
    with client.app.state.database.connect() as connection:
        assert connection.execute("SELECT status FROM life_admin WHERE source='school'").fetchone()['status'] == 'removed'
    assert not any(block['kind'] == 'study' for block in current(client)['version']['definition']['schedule'])


def test_an_exam_on_a_class_day_keeps_its_day_and_the_class_hour(client, mira, clock, monkeypatch):
    chapter = begun(client, monkeypatch, clock, 'school')
    found = details(client, chapter['id'])
    next_stage(client, clock, chapter['id'])  # Classes start.
    day = clock.now().date() + timedelta(days=5)
    while day.weekday() not in found['study']['days']:
        day += timedelta(days=1)
    with client.app.state.database.connect(write=True) as connection:
        connection.execute("UPDATE life_chapters SET details=json_set(details, '$.exams', json_array(?)) WHERE id=?",
                           (day.isoformat(), chapter['id']))
    clock.advance(timedelta(days=1))
    reconcile(client)
    with client.app.state.database.connect() as connection:
        exam = connection.execute("SELECT * FROM life_admin WHERE source='school'").fetchone()
    assert (exam['local_date'], exam['at_time']) == (day.isoformat(), found['study']['start'])
    assert f"Next exam {big_turns.short_day(day.isoformat())}" in \
        client.get('/api/life/chapters/lately').json()['now'][0]['line']


def test_a_course_stays_in_the_chat_context_while_it_runs(client, mira, clock, monkeypatch):
    chapter = begun(client, monkeypatch, clock, 'school')
    next_stage(client, clock, chapter['id'])  # Classes start.
    with client.app.state.database.connect(write=True) as connection:
        connection.execute("UPDATE life_chapters SET details=json_set(details, '$.next_on', '2099-01-01') WHERE id=?",
                           (chapter['id'],))
    clock.advance(timedelta(days=chapters.TOLD_DAYS + 30))
    reconcile(client)
    assert 'You started ' in client.get('/api/context/preview').json()['prompt']


def test_a_career_change_retrains_then_starts_the_new_job(client, mira, clock, monkeypatch):
    chapter = begun(client, monkeypatch, clock, 'career_change')
    found = details(client, chapter['id'])
    assert found['career'] != 'accountant' and 'retrain as' in chapter['title']
    next_stage(client, clock, chapter['id'])
    definition = current(client)['version']['definition']
    assert definition['money']['career'] == 'accountant'
    [study] = [block for block in definition['schedule'] if block['kind'] == 'study']
    assert study['label'].lower() == f"{found['job']} class"  # 'Financial analyst class', not 'Financial class'.
    next_stage(client, clock, chapter['id'])
    definition = current(client)['version']['definition']
    assert definition['money']['career'] == found['career']
    assert not any(block['kind'] == 'study' for block in definition['schedule'])
    assert client.get('/api/life/chapters').json()[0]['title'].startswith('Mira changed careers and started as')


def test_buying_a_place_brings_a_mortgage_until_undone(client, mira, clock, monkeypatch):
    chapter = begun(client, monkeypatch, clock, 'buy_place')
    found = details(client, chapter['id'])
    old = items(client, 'home')
    assert chapter['stage'] == 'hunting' and found['place']['details']['owned']
    with client.app.state.database.connect(write=True) as connection:
        companion = current(client)
        admin.add(connection, companion, key='admin:lease:2099-01-01', source='admin', kind='lease',
                  title='Lease renewal', done='signed the lease', day=clock.now().date() + timedelta(days=20),
                  now=clock.now())
    assert 'keys on' in client.get('/api/life/chapters/lately').json()['now'][0]['line']
    next_stage(client, clock, chapter['id'])
    [place] = items(client, 'home')
    assert place['owned'] and place['rent'] == found['place']['details']['rent'] and place['id'] != old[0]['id']
    definition = current(client)['version']['definition']
    assert definition['location'] == f"{place['neighborhood']}, Baltimore"
    with client.app.state.database.connect() as connection:
        companion = current(client)
        today = clock.now().date()
        budget = money.snapshot(definition, today.isoformat(),
                                money.household(connection, companion['active_timeline_id'], definition, today))
    assert budget['owned'] and any(item['for'] == 'deposit' and item['savings'] for item in budget['bought'])
    prompt = client.get('/api/context/preview').json()['prompt']
    assert 'the mortgage on your home is about' in prompt and 'as an accountant' in prompt
    assert ' Rent is about' not in prompt  # The Home line says mortgage too.
    with client.app.state.database.connect() as connection:
        has = admin.owns(definition, connection, companion['active_timeline_id'], today)
        assert connection.execute("SELECT status FROM life_admin WHERE key='admin:lease:2099-01-01'").fetchone()[0] \
            == 'removed'
    assert 'rent' not in has  # No lease to renew on a place they own.
    client.post(f"/api/life/chapters/{chapter['id']}/undo")
    assert [item['id'] for item in items(client, 'home')] == [old[0]['id']]


def test_retirement_turns_work_into_their_own_time_and_pay_into_a_pension(client, older, clock, monkeypatch):
    chapter = begun(client, monkeypatch, clock, 'retire')
    found = details(client, chapter['id'])
    assert chapter['title'] == 'Mira is retiring' and found['last_day'] > chapter['started_on']
    next_stage(client, clock, chapter['id'])
    definition = current(client)['version']['definition']
    assert not any(block['kind'] == 'work' for block in definition['schedule'])
    assert next(block for block in definition['schedule'] if block['key'] == 'work')['label'] == \
        found['pursuit']['label']
    with client.app.state.database.connect() as connection:
        pay = big_turns.pay(connection, current(client)['active_timeline_id'], clock.now().date(), {'factor': 1})
    assert pay == {'factor': big_turns.PENSION['modern'], 'between_jobs': False, 'retired': True}
    assert 'Retired, you live on a pension of about' in client.get('/api/context/preview').json()['prompt']


def plannable(client, kind: str) -> bool:
    """Whether the chapter could happen today."""
    with client.app.state.database.connect() as connection:
        companion = current(client)
        today = storylines.local_today(companion, client.app.state.database.clock.now())
        return chapters.PLANS[kind](connection, companion, client.app.state.life.world, today, 'seed') is not None


def test_once_retired_no_ordinary_new_job_comes(client, older, clock, monkeypatch):
    assert plannable(client, 'new_job')
    chapter = begun(client, monkeypatch, clock, 'retire')
    assert not plannable(client, 'new_job')  # They handed in their notice.
    next_stage(client, clock, chapter['id'])
    assert not plannable(client, 'new_job')


def test_an_owner_stays_put(client, mira, clock, monkeypatch):
    assert plannable(client, 'move')
    chapter = begun(client, monkeypatch, clock, 'buy_place')
    assert not plannable(client, 'move')  # House hunting.
    next_stage(client, clock, chapter['id'])
    assert not plannable(client, 'move')


def test_retirement_is_for_older_characters_only(client, mira, clock, monkeypatch):
    arrange(client, monkeypatch, clock, 'retire')
    reconcile(client)
    assert client.get('/api/life/chapters').json() == []


def test_the_odds_read_age_and_living_together():
    names = {'name': 'Mira', 'a': 'someone', 'b': ''}
    every = {f'can_{kind}': 1 for kind in chapters.KINDS}
    young = consequences.odds(chapters.CHOICE, {'drama': 1, 'friends': 4, 'age': 40, **every}, names)
    old = consequences.odds(chapters.CHOICE, {'drama': 1, 'friends': 4, 'age': 71, **every}, names)
    retire = chapters.KINDS.index('retire')
    assert old[retire]['odds'] > young[retire]['odds'] and 'Mira is past seventy' in old[retire]['reasons']
    together = consequences.odds(chapters.CHOICE, {'drama': 1, 'friends': 4, 'together': 1, **every}, names)
    buy = chapters.KINDS.index('buy_place')
    assert together[buy]['odds'] > young[buy]['odds'] and 'you and Mira live together' in together[buy]['reasons']


def test_lifes_big_turns_off_means_nothing_begins(client, mira, clock, monkeypatch):
    assert client.put('/api/life/settings', json={'life_turns': 0}).json()['life_turns'] == 0
    assert turnover.STATE.pace == 0
    arrange(client, monkeypatch, clock, 'hobby')
    reconcile(client)
    assert client.get('/api/life/chapters').json() == []
    client.put('/api/life/settings', json={'life_turns': 2})
    assert turnover.STATE.pace == 2


def test_gentle_keeps_hard_turns_away(client, mira, monkeypatch):
    monkeypatch.setattr(big_turns, 'HARD', frozenset({'school'}))
    client.put('/api/life/settings', json={'life_turns': 1})
    with client.app.state.database.connect() as connection:
        assert not big_turns.allowed(connection, 'school') and big_turns.allowed(connection, 'retire')
    client.put('/api/life/settings', json={'life_turns': 2})
    with client.app.state.database.connect() as connection:
        assert big_turns.allowed(connection, 'school')


def test_living_together_they_buy_a_place_for_both(client, provider, clock, monkeypatch):
    from test_moving_in import ask_to_move_in, moving_day
    from test_together import mira as together

    from companion.life import moving_in
    monkeypatch.setattr(consequences, 'roll', lambda _seed, found: found[0]['option'])
    together(client, monkeypatch, relationship='romance', identity='Mira is 33, an accountant.',
             money={'career': 'accountant'})
    ask_to_move_in(client, provider)
    moving_day(client, clock)
    monkeypatch.setattr(chapters, 'GAP', timedelta(0))
    chapter = begun(client, monkeypatch, clock, 'buy_place')
    found = details(client, chapter['id'])
    assert found['shared'] and chapter['title'] == 'Mira and you are buying a place together'
    assert found['place']['details']['bedrooms'] == 'two_bedroom'
    next_stage(client, clock, chapter['id'])
    [place] = items(client, 'home')
    with client.app.state.database.connect() as connection:
        companion = current(client)
        shared = moving_in.current(connection, companion['active_timeline_id'])
        costs = money.household(connection, companion['active_timeline_id'], companion['version']['definition'],
                                clock.now().date())['costs']
    assert shared['home_item_id'] == place['id'] and shared['neighbourhood'] == place['neighborhood']
    assert costs['owned'] and costs['shared'] and costs['rent'] == round(place['rent'] / 2, 2)
    client.post(f"/api/life/chapters/{chapter['id']}/undo")
    with client.app.state.database.connect() as connection:
        assert moving_in.current(connection, companion['active_timeline_id'])['home_item_id'] != place['id']
