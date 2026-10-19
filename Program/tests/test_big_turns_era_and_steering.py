"""Life's big turns, v0.15 follow-ups: era words in a medieval kingdom, the older past's own banks, dates said as a
friend would, gentler odds, and "Make it go this way" on how a stage went."""
from datetime import date, timedelta

import pytest
from conftest import reconcile
from test_big_turns import begun, details, make, next_stage
from test_big_turns_two import budget, land, parent
from test_chapters import arrange, current
from test_storylines import WORKDAY

from companion import consequences
from companion.life import admin, big_turns, body, business, chapters, health_turns, home, money, storylines
from companion.world import catalog


@pytest.fixture
def mira(client, monkeypatch):
    make(client, monkeypatch, 'Mira is 34, an accountant.')


@pytest.fixture
def older(client, monkeypatch):
    make(client, monkeypatch, 'Mira is 64, an accountant.')


@pytest.fixture
def elowen(client, monkeypatch):
    """A baker of 64 in Camelot."""
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    monkeypatch.setattr(storylines, 'STORIES', ())
    response = client.post('/api/companion', json={
        'name': 'Elowen Ashby', 'timezone': 'UTC', 'schedule': WORKDAY, 'home_city': 'camelot',
        'location': 'Woolston, Camelot', 'identity': 'Elowen is 64, a baker.', 'money': {'career': 'baker'}})
    assert response.status_code == 200, response.text


def prompt(client) -> str:
    return client.get('/api/context/preview').json()['prompt']


# Era words and banks ---------------------------------------------------------------------------------------------

def test_the_older_past_has_a_medieval_and_a_victorian_bank_for_courses_and_businesses():
    camelot, london, new_york = (catalog.cities()[key] for key in ('camelot', 'london-1895', 'new-york-1925'))
    for name, key in (('courses', 'course'), ('businesses', 'business')):
        medieval = {entry[key] for entry in big_turns.bank(name, camelot)}
        victorian = {entry[key] for entry in big_turns.bank(name, london)}
        assert medieval != victorian and big_turns.bank(name, new_york) == big_turns.data()[name]['jazz-age']
    courses = {entry['course'] for entry in big_turns.bank('courses', camelot)}
    assert 'lessons in illumination at the abbey' in courses and "the mechanics' institute lectures" not in courses
    shops = {entry['business'] for entry in big_turns.bank('businesses', catalog.cities()['london-1895'])}
    assert "a scribe's stall" not in shops and 'a print shop' in shops
    assert big_turns.bank('retirement', camelot) == big_turns.data()['retirement']['other']


def test_giving_up_work_in_camelot_has_no_pension_or_retiring(client, elowen, clock, monkeypatch):
    chapter = begun(client, monkeypatch, clock, 'retire')
    with client.app.state.database.connect() as connection:
        row = connection.execute('SELECT * FROM life_chapters WHERE id=?', (chapter['id'],)).fetchone()
    assert chapter['title'] == 'Elowen is giving up work' and 'retir' not in (row['told'] + row['share']).lower()
    assert 'Giving up work' in client.get('/api/life/chapters/lately').json()['now'][0]['line']
    next_stage(client, clock, chapter['id'])
    assert client.get('/api/life/chapters').json()[0]['title'] == 'Elowen gave up work'
    view = budget(client, clock)
    assert view['retired'] and view['medieval']
    text = prompt(client)
    assert 'what you put by' in text and 'pension' not in text


def test_a_health_turn_in_camelot_waits_on_the_healer(client, elowen, clock, monkeypatch):
    chapter = begun(client, monkeypatch, clock, 'health')
    assert chapter['title'] == "Elowen is waiting on the healer's word"
    assert health_turns.entry('health', details(client, chapter['id']))['title'] == "Healer's visit"
    assert "the healer's word" in client.get('/api/life/chapters/lately').json()['now'][0]['line']
    land(monkeypatch, health_turns.OUTLOOK, 0)
    next_stage(client, clock, chapter['id'])
    assert client.get('/api/life/chapters').json()[0]['title'].startswith('Elowen learned they have')
    with client.app.state.database.connect() as connection:
        row = connection.execute('SELECT told FROM life_chapters WHERE id=?', (chapter['id'],)).fetchone()
    assert row['told'].startswith('The healer told you') and 'diagnosed' not in row['told']


def test_owning_a_place_lessons_and_tests_of_skill_in_era_words():
    camelot = catalog.cities()['camelot']
    definition = {'name': 'Elowen Ashby', 'home_city': 'camelot', 'location': 'Woolston, Camelot',
                  'money': {'career': 'baker'}, 'identity': 'Elowen is 40.'}
    place = big_turns.place_to_buy({'id': 'c', 'version': {'definition': definition}}, camelot,
                                   money.profile(definition), None, 'seed')
    assert place['details']['medieval']
    said = big_turns.buy_words(definition, place, date(2027, 3, 5), False, date(2027, 1, 10))
    assert 'struck a bargain' in said['share'] and said['share'].endswith('I get the keys March 5.')
    assert home.money_text({**place['details'], 'rent_from': 'home'}).startswith(' Payments on it are about')
    row = {'kind': 'buy_place', 'title': '', 'details': big_turns.encode(
        {'stage': 'hunting', 'place': place, 'keys_on': '2027-03-05', 'medieval': True})}
    assert 'Payments on it will be about' in big_turns.line(row)
    companion = {'version': {'definition': definition}}
    lessons = {'course': 'lessons in calligraphy from a scribe', 'medieval': True}
    finished = big_turns.graduate(None, companion, {}, lessons, date(2027, 6, 1), None)
    assert 'graduat' not in (finished['title'] + finished['told'] + finished['share']).lower()
    studying = {'kind': 'school', 'title': '', 'details': big_turns.encode({
        'stage': 'studying', 'course': lessons['course'], 'exams': ['2027-04-01'], 'stage_on': '2027-01-01',
        'study': {'days': [1, 3]}, 'ends_on': '2027-06-01', 'medieval': True})}
    assert 'Next test of skill Apr 1, 2027.' in big_turns.line(studying)
    # 1895 keeps the words that fit it.
    london = {**definition, 'home_city': 'london-1895', 'location': 'Lambeth, London', 'money': {'career': 'clerk'}}
    place = big_turns.place_to_buy({'id': 'c', 'version': {'definition': london}}, catalog.cities()['london-1895'],
                                   money.profile(london), None, 'seed')
    assert not place['details'].get('medieval')
    assert home.money_text({**place['details'], 'rent_from': 'home'}).startswith(' The mortgage is about')


# Dates and wordings ----------------------------------------------------------------------------------------------

def test_a_date_within_a_year_is_said_without_the_year():
    today = date(2027, 1, 10)
    assert big_turns.soon_text(date(2027, 2, 5), today) == 'February 5'
    assert big_turns.soon_text('2027-12-20', today) == 'December 20'
    assert big_turns.soon_text(date(2028, 1, 11), today) == 'January 11, 2028'


def test_shares_leave_the_year_out_and_a_career_change_says_they_switch(client, mira, clock, monkeypatch):
    chapter = begun(client, monkeypatch, clock, 'career_change')
    with client.app.state.database.connect() as connection:
        row = connection.execute('SELECT * FROM life_chapters WHERE id=?', (chapter['id'],)).fetchone()
    assert ', 20' not in row['share'] and 'then you switch to working as' in row['told']
    next_stage(client, clock, chapter['id'])
    with client.app.state.database.connect() as connection:
        row = connection.execute('SELECT told FROM life_chapters WHERE id=?', (chapter['id'],)).fetchone()
    assert 'keep your current job until then, and then you switch to working as' in row['told']


def test_the_news_of_a_condition_is_weighed_by_how_it_looks():
    condition = {'condition': 'teeth grinding', 'advice': 'wear the night guard', 'checkup': 'Dentist check',
                 'every': 26}
    light = health_turns.news('Mira', {}, {**condition, 'light': True}, date(2027, 1, 5), 26, False)
    usual = health_turns.news('Mira', {}, condition, date(2027, 1, 5), 26, False)
    harder = health_turns.news('Mira', {}, {**condition, 'light': True}, date(2027, 1, 5), 13, True)
    assert 'a lot to take in' not in light['share'] and 'nuisance' in light['told']
    assert "Not the end of the world, but it's a lot to take in." in usual['share']
    assert harder['share'] == "Got my results. It's teeth grinding, and it's a lot to take in."
    assert any(entry.get('light') for entry in big_turns.data()['conditions']['modern'])


def test_later_caring_stages_keep_the_routine(client, mira, clock, monkeypatch):
    reconcile(client)
    parent(client)
    chapter = begun(client, monkeypatch, clock, 'caring')
    next_stage(client, clock, chapter['id'])
    land(monkeypatch, health_turns.HOW, 1)
    next_stage(client, clock, chapter['id'])
    with client.app.state.database.connect() as connection:
        row = connection.execute('SELECT told FROM life_chapters WHERE id=?', (chapter['id'],)).fetchone()
    assert row['told'].startswith('Caring for your mom') and 'at their place, take them to their appointments' in \
        row['told']


def test_the_new_job_reason_names_retiring_and_a_business():
    found = consequences.odds(chapters.CHOICE, {'can_new_job': 0}, {'name': 'Mira', 'a': '', 'b': ''})
    assert 'has retired, runs a business of their own' in found[0]['reasons'][0]


# Odds ------------------------------------------------------------------------------------------------------------

def test_soap_opera_drama_makes_a_health_turn_no_likelier():
    names = {'name': 'Mira', 'a': 'someone', 'b': ''}
    every = {f'can_{kind}': 1 for kind in chapters.KINDS}
    health = chapters.KINDS.index('health')
    real = consequences.odds(chapters.CHOICE, {'drama': 2, 'friends': 4, 'age': 45, **every}, names)[health]['odds']
    drama = consequences.odds(chapters.CHOICE, {'drama': 3, 'friends': 4, 'age': 45, **every}, names)[health]['odds']
    assert drama < real


def test_a_business_never_stalls_on_gentle():
    names = {'name': 'Mira', 'a': 'bakery', 'b': ''}
    gentle = consequences.odds(business.CHOICE, {'turns': 1, 'checks': 1, 'factor': 4}, names)
    assert gentle[2]['odds'] == 0 and gentle[3]['odds'] == 0
    assert consequences.odds(business.CHOICE, {'turns': 2, 'checks': 1, 'factor': 4}, names)[2]['odds'] > 0


def test_the_side_business_registration_is_only_for_a_business_they_run(client, mira, clock):
    [entry] = [item for item in admin.data()['paperwork'] + admin.data()['errands']
               if item['id'] == 'file-business-registration']
    assert entry['needs'] == 'business'
    companion = current(client)
    with client.app.state.database.connect() as connection:
        definition = companion['version']['definition']
        args = (connection, companion['active_timeline_id'], clock.now().date())
        assert 'business' not in admin.owns(definition, *args)
        assert 'business' in admin.owns({**definition, 'business': {'label': 'Running the bakery'}}, *args)


# Make it go this way ---------------------------------------------------------------------------------------------

def change(client, consequence_id: str, option: int):
    return client.post(f'/api/life/consequences/{consequence_id}/change', json={'option': option})


def test_how_a_business_goes_can_be_changed_while_it_is_the_latest(client, mira, clock, monkeypatch):
    chapter = begun(client, monkeypatch, clock, 'business')
    next_stage(client, clock, chapter['id'])  # Open.
    land(monkeypatch, business.CHOICE, 2)
    next_stage(client, clock, chapter['id'])  # A slow quarter.
    [listed] = [item for item in client.get('/api/life/chapters').json() if item['id'] == chapter['id']]
    assert details(client, chapter['id'])['how'] == 'stalls' and listed['outcome']
    response = change(client, listed['outcome'], 0)
    assert response.status_code == 200, response.text
    assert response.json()['picked'] == 0 and response.json()['picked_by'] == 'user'
    found = details(client, chapter['id'])
    assert found['how'] == 'grows' and found['factor'] == round(business.START + business.GROW, 2)
    assert found['checks'] == 1 and len(found['before']) == 2
    assert 'growing' in client.get('/api/life/chapters').json()[0]['title']
    with client.app.state.database.connect() as connection:
        marks = connection.execute('SELECT note FROM marks WHERE consequence_id=?', (listed['outcome'],)).fetchall()
    assert all('slow' not in mark['note'] for mark in marks)

    first = listed['outcome']
    assert client.get(f'/api/life/consequences/{first}').json()['settled'] == ''
    land(monkeypatch, business.CHOICE, 1)
    next_stage(client, clock, chapter['id'])
    response = change(client, first, 3)
    assert response.status_code == 409 and 'most recently' in response.json()['detail']
    # Read again, it says so up front, so the page shows the reason in place of "Make it go this way".
    assert client.get(f'/api/life/consequences/{first}').json()['settled'] == response.json()['detail']


def test_how_a_health_turn_looks_can_be_changed_after_it_settled(client, older, clock, monkeypatch):
    chapter = begun(client, monkeypatch, clock, 'health')
    land(monkeypatch, health_turns.OUTLOOK, 1)
    next_stage(client, clock, chapter['id'])
    next_stage(client, clock, chapter['id'])  # Living with it.
    found = details(client, chapter['id'])
    assert found['stage'] == 'living_with' and found['outlook'] == 'harder'
    outcome = client.get('/api/life/chapters').json()[0]['outcome']
    assert change(client, outcome, 0).status_code == 200
    found = details(client, chapter['id'])
    assert found['outlook'] == 'manageable' and found['every'] == found['condition']['every']
    # Settling in comes again on its own day, months after the diagnosis.
    assert found['stage'] == 'managing' and found['next_on'] > clock.now().date().isoformat()
    with client.app.state.database.connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM marks WHERE consequence_id=?', (outcome,)).fetchone()[0] == 0


def test_caring_that_eased_can_go_on_instead(client, mira, clock, monkeypatch):
    reconcile(client)
    parent(client)
    chapter = begun(client, monkeypatch, clock, 'caring')
    next_stage(client, clock, chapter['id'])
    land(monkeypatch, health_turns.HOW, 0)
    next_stage(client, clock, chapter['id'])
    assert details(client, chapter['id'])['stage'] == 'eased'
    outcome = client.get('/api/life/chapters').json()[0]['outcome']
    assert change(client, outcome, 1).status_code == 200
    assert details(client, chapter['id'])['stage'] == 'caring'
    assert any('caring' in block.get('themes', ()) for block in current(client)['version']['definition']['schedule'])


def test_a_big_turn_for_an_older_chapter_says_why_it_cannot_happen(client, mira, clock, monkeypatch):
    hobby = begun(client, monkeypatch, clock, 'hobby')
    clock.advance(chapters.GAP + timedelta(days=5))
    monkeypatch.setattr(chapters, 'CHANCE', (0, 0, 0, 0))  # Nothing in between; arrange opens the way again.
    arrange(client, monkeypatch, clock, 'business')
    reconcile(client)
    assert [item['kind'] for item in client.get('/api/life/chapters').json()][:1] == ['business']
    response = change(client, hobby['consequence'], chapters.KINDS.index('school'))
    assert response.status_code == 409
    assert 'another big turn is under way' in response.json()['detail'] and 'starting' in response.json()['detail']
