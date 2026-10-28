"""Local politics (companion/world/politics.py, companion/life/politics.py): issues people argue about, their views
and the factions behind them, all seeded, with the user's changes on top."""
from datetime import date, timedelta

import pytest
from test_social_circle import make

from companion.world import catalog, politics

DAY = date(2026, 12, 10)


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture(autouse=True)
def politics_on(monkeypatch):
    monkeypatch.setattr('companion.life.politics.ACTIVE', True)


# --- The banks ---

def test_the_banks_hold_enough_and_every_blank_can_be_filled():
    data = politics.bank()
    assert len(data['local']) >= 100
    assert set(data['eras'].values()) == set(data['styles']) == set(data['questions']) == set(data['factions'])
    assert set(data['eras']) == {'modern', 'victorian', 'medieval', 'fantasy', 'steampunk', 'frontier', 'jazz-age',
                                 'future', 'other'}
    tags = {tag for group in data['factions'].values() for faction in group for tag in faction['tags']}
    for template in data['local']:
        assert len(template['sides']) == 2 and template['styles'], template['id']
        assert set(template['beats']) == {'whispers', 'open', 'heated', 'won', 'lost', 'fizzled'}, template['id']
        assert politics.needs(template) <= {'office', 'office2', 'institution', 'trade', 'place', 'hood', 'person'}
        for side in template['sides']:
            assert set(side.get('jobs', [])) <= set(data['jobs']), template['id']
            assert set(side.get('words', [])) <= set(data['words']), template['id']
            assert set(side.get('backers', [])) <= tags, template['id']
    for style, questions in data['questions'].items():
        assert questions and all(len(item['sides']) == 2 for item in questions), style


def test_built_in_cities_politics_name_their_own_people_and_places():
    for city_id in ('grandport', 'new-york-1925'):
        data = catalog.city(city_id, {})
        own = politics.own(data)
        places = {place['id'] for place in data['places']}
        notables = {notable['id'] for notable in data.get('notables', [])}
        ids = {faction['id'] for faction in own['factions']}
        for faction in own['factions']:
            assert set(faction.get('places', [])) <= places, faction['id']
            assert set(faction.get('members', [])) <= notables, faction['id']
            assert set(faction.get('allies', [])) | set(faction.get('rivals', [])) <= ids, faction['id']
        assert politics.factions(data) == [{**item, 'origin': 'city'} for item in own['factions']]


def test_a_packs_politics_block_drops_what_is_broken_and_keeps_the_rest():
    data = {'politics': {'factions': [{'id': 'reds', 'name': 'The Reds', 'pull': 9}, {'name': 'no id'}],
                         'questions': [{'id': 'q', 'title': 'Q', 'sides': [{'name': 'Yes'}]}],
                         'issues': [{'id': 'i', 'title': 'The well', 'sides': [{'name': 'Dig'}, {'name': 'Wait'}],
                                     'beats': {'whispers': 'Dry again.'}}]}}
    notes = politics.clean(data)
    assert [faction['pull'] for faction in data['politics']['factions']] == [5]
    assert data['politics']['questions'] == [] and len(data['politics']['issues']) == 1
    assert len(notes) == 2
    assert politics.clean({'politics': 'nonsense'}) and politics.clean({}) == []


# --- Issues ---

def test_issues_are_seeded_the_same_way_every_time():
    data = catalog.city('chicago', {})
    first = politics.seeded_locals(data, DAY, 2, 1)
    politics._SEEDED.clear()
    assert politics.seeded_locals(data, DAY, 2, 1) == first
    assert first and all(issue['dates']['whispers'] < issue['dates']['open'] < issue['dates']['heated']
                         < issue['dates']['settled'] for issue in first)
    assert all('{' not in issue['title'] + issue['question'] for issue in first)


def test_more_drama_and_livelier_politics_start_more_local_issues():
    data = catalog.city('london', {})
    later = DAY + timedelta(days=600)
    quiet = len(politics.seeded_locals(data, later, 1, 0))
    lively = len(politics.seeded_locals(data, later, 3, 3))
    assert lively > quiet * 2
    assert politics.era_issues(data, DAY, 0) == [] and len(politics.era_issues(data, DAY, 3)) == 3


def test_a_real_city_keeps_the_questions_of_its_year_and_prohibition_never_settles():
    data = catalog.city('new-york-1925', {})
    titles = [issue['title'] for issue in politics.era_issues(data, DAY, 2)]
    assert titles == ['Walker or Hylan', 'Prohibition']
    assert politics.era_issues(data, DAY, 2)[1]['real']
    made_up = catalog.city('pellmouth', {})
    assert 'Prohibition' not in [question['title'] for question in politics.era_questions(made_up, DAY)]


def test_a_stage_the_user_picks_holds_and_pushes_later_stages_back():
    from companion.life.politics import staged
    dates = {'whispers': '2026-10-01', 'open': '2026-10-10', 'heated': '2026-11-01', 'settled': '2026-11-20'}
    found = staged(dates, 'heated', DAY.replace(month=10, day=12))
    assert found == {'whispers': '2026-10-01', 'open': '2026-10-10', 'heated': '2026-10-12', 'settled': '2026-11-20'}
    found = staged(dates, 'whispers', DAY.replace(month=10, day=15))
    assert found['open'] == '2026-10-16' and found['heated'] == '2026-11-07' and found['settled'] == '2026-11-26'


# --- Views ---

def test_views_follow_work_and_character():
    issue = politics.era_issue(catalog.city('new-york-1925', {}), next(
        item for item in politics.bank()['questions']['jazz'] if item['id'] == 'prohibition'), DAY)

    def person(key, job):
        return {'key': key, 'jobs': politics.jobs_of(job), 'groups': set(), 'age': 40}
    police = [politics.view_of(person(f'p{n}', 'police officer'), issue, [], []) for n in range(80)]
    barkeeps = [politics.view_of(person(f'b{n}', 'bartender'), issue, [], []) for n in range(80)]
    assert sum(view < 0 for view in police) > 50  # Dry is the second side.
    assert sum(view > 0 for view in barkeeps) > 50
    devout = [politics.view_of({'key': f'c{n}', 'jobs': set(), 'groups': {'devout'}, 'kind': 'companion'}, issue, [], [])
              for n in range(80)]
    assert sum(view < 0 for view in devout) > 60  # Their own card's words count double.
    assert politics.view_text(2, issue) == 'wants to see Prohibition repealed, and says so'
    assert politics.view_label(-1, issue) == 'Leans: Dry'


# --- The API, Today and chat ---

@pytest.fixture
def jazz(client):
    found = make(client, 'Stubborn and devout.', home_city='new-york-1925', location='Greenwich Village, New York')
    ok(client.get('/api/life/circle'))
    return found


def test_talk_of_the_town_shows_the_issues_and_where_people_stand(client, jazz):
    found = ok(client.get('/api/life/politics'))
    assert found['city']['id'] == 'new-york-1925' and found['level'] == 2
    titles = [issue['title'] for issue in found['issues']]
    assert titles[:2] == ['Walker or Hylan', 'Prohibition']
    prohibition = found['issues'][1]
    assert sum(prohibition['split'].values()) > 50
    assert prohibition['id'] in found['companion']['views']
    assert {faction['name'] for faction in found['factions']} >= {'Tammany Hall', 'The Anti-Saloon League'}
    assert found['people'] and all(prohibition['id'] in person['views'] for person in found['people'])
    assert ok(client.get('/api/life/politics')) == found


def test_the_user_can_change_views_issues_and_factions(client, jazz):
    found = ok(client.get('/api/life/politics'))
    issue = found['issues'][1]['id']
    me = found['companion']['key']
    found = ok(client.put('/api/life/politics/views', json={'issue': issue, 'person': me, 'view': -2}))
    assert found['companion']['views'][issue] == {'view': -2, 'by': 'you'}
    found = ok(client.put('/api/life/politics/views', json={'issue': issue, 'person': me, 'view': None}))
    assert found['companion']['views'][issue]['by'] == 'world'

    found = ok(client.post('/api/life/politics/issues', json={'title': 'The new pier', 'sides': ['Build it', 'No pier'],
                                                              'stands': ['build the pier', '']}))
    mine = next(item for item in found['issues'] if item['title'] == 'The new pier')
    assert mine['origin'] == 'user' and mine['stage'] == 'open' and mine['sides'][1]['stand'] == 'side with No pier'
    found = ok(client.patch(f"/api/life/politics/issues/{mine['id']}", json={'stage': 'heated', 'question': 'A pier?'}))
    assert next(item for item in found['issues'] if item['id'] == mine['id'])['stage'] == 'heated'
    found = ok(client.patch(f"/api/life/politics/issues/{mine['id']}", json={'outcome': 0}))
    assert next(item for item in found['issues'] if item['id'] == mine['id'])['stage'] == 'settled'
    found = ok(client.delete(f"/api/life/politics/issues/{mine['id']}"))
    assert mine['id'] not in [item['id'] for item in found['issues']]

    assert client.patch(f'/api/life/politics/issues/{issue}', json={'outcome': 0}).status_code == 422
    assert client.patch(f'/api/life/politics/issues/{issue}', json={'stage': 'heated'}).status_code == 422
    found = ok(client.patch(f'/api/life/politics/issues/{issue}', json={'sides': ['Wets', 'Drys']}))
    assert [side['name'] for side in found['issues'][1]['sides']] == ['Wets', 'Drys']
    found = ok(client.delete(f'/api/life/politics/issues/{issue}'))
    assert issue not in [item['id'] for item in found['issues']]

    found = ok(client.post('/api/life/politics/factions', json={'name': 'The Village poets', 'pull': 1}))
    poets = next(item for item in found['factions'] if item['name'] == 'The Village poets')
    found = ok(client.patch(f"/api/life/politics/factions/{poets['id']}", json={'add_member': me, 'pull': 3}))
    poets = next(item for item in found['factions'] if item['id'] == poets['id'])
    assert poets['members'] == [me] and poets['pull'] == 3 and poets['id'] in found['companion']['factions']
    found = ok(client.put('/api/life/politics/relations', json={'a': 'tammany', 'b': poets['id'], 'stance': 2}))
    assert any({link['a'], link['b']} == {'tammany', poets['id']} and link['stance'] == 2 and link['by'] == 'you'
               for link in found['relations'])
    found = ok(client.patch('/api/life/politics/factions/tammany', json={'name': 'The Hall'}))
    assert 'The Hall' in [item['name'] for item in found['factions']]
    found = ok(client.delete('/api/life/politics/factions/tammany'))
    assert 'tammany' not in [item['id'] for item in found['factions']]
    assert client.patch('/api/life/politics/factions/nobody', json={'name': 'X'}).status_code == 404


def test_turning_local_politics_off_empties_talk_of_the_town(client, jazz):
    ok(client.put('/api/life/settings', json={'politics_realism': 0}))
    found = ok(client.get('/api/life/politics'))
    assert found['level'] == 0 and found['issues'] == [] and found['factions'] == []


def test_the_chat_hears_what_people_are_arguing_about(client, jazz, provider):
    from conftest import send
    ok(client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                           'api_key': 'secret-key'}))
    send(client, 'What is everyone talking about?', 'politics-1')
    prompt = provider.requests[-1]['prompt']
    assert 'Local politics people are arguing about' in prompt
    assert 'Prohibition' in prompt and ('You want to' in prompt or 'You would rather' in prompt
                                        or "You don't much care" in prompt)
