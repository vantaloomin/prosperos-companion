"""Closeness stages: visible, explained, resettable and never a reward for time spent (PRD M3, M4)."""
from datetime import timedelta
from uuid import uuid4

from conftest import send

from companion.memory import closeness


def view(client):
    response = client.get('/api/closeness')
    assert response.status_code == 200, response.text
    return response.json()


def system(client):
    return client.get('/api/context/preview').json()['system']


def talk_on_days(client, clock, days, per_day=1):
    for day in range(days):
        for turn in range(per_day):
            send(client, f'Hello {day}-{turn}', f'client-{uuid4().hex}')
        clock.advance(timedelta(days=1))


def remember_moment(client, subject, value='We laughed about it for ages'):
    response = client.post('/api/memories', json={'layer': 'shared_experience', 'subject': subject, 'value': value})
    assert response.status_code == 200, response.text
    return response.json()


def test_a_new_companion_has_just_met_and_holds_back(client, connected):
    state = view(client)
    assert state['level'] == 1 and state['name'] == 'Just met' and state['days_talked'] == 0
    assert state['stages'][2] == 'Friends'  # friendship is the default relationship
    prompt = system(client)
    assert 'How close you two are' in prompt and closeness.NO_NICKNAME in prompt
    assert 'stays friendship' in prompt and 'never ask for more time' in prompt


def test_days_talked_count_not_messages(client, connected, clock):
    talk_on_days(client, clock, 1, per_day=12)
    assert view(client)['days_talked'] == 1 and view(client)['level'] == 1
    talk_on_days(client, clock, 2)
    state = view(client)
    assert state['days_talked'] == 3 and state['level'] == 2 and state['name'] == 'Getting to know each other'
    assert state['history'] == [{'level': 2, 'on': '2026-10-07', 'days': 3, 'moments': 0}]


def test_shared_moments_help_but_never_outrun_the_days_talked(client, connected, clock):
    for index in range(6):
        remember_moment(client, f'Moment {index}')
    talk_on_days(client, clock, 1)
    state = view(client)
    assert state['shared_moments'] == 6 and state['counted_moments'] == 1 and state['level'] == 1
    talk_on_days(client, clock, 3)
    assert view(client)['level'] == 3  # 4 days + 4 counted moments = 8


def test_time_apart_never_lowers_closeness(client, connected, clock):
    talk_on_days(client, clock, 3)
    clock.advance(timedelta(days=90))
    assert view(client)['level'] == 2


def test_hold_reset_and_nickname(client, connected, clock):
    talk_on_days(client, clock, 3)
    held = client.put('/api/closeness', json={'held_level': 4, 'nickname': '  Sunny  '}).json()
    assert held['level'] == 4 and held['grown_level'] == 2 and held['nickname'] == 'Sunny'
    prompt = system(client)
    assert 'Close friends.' in prompt and '“Sunny”' in prompt
    grown = client.put('/api/closeness', json={'held_level': None}).json()
    assert grown['level'] == 2 and grown['nickname'] == 'Sunny'
    reset = client.post('/api/closeness/reset').json()
    assert reset['level'] == 1 and reset['days_talked'] == 0 and reset['counted_from'] and reset['nickname'] == 'Sunny'
    assert client.put('/api/closeness', json={'held_level': 9}).status_code == 422


def test_romance_is_followed_and_traits_stay_steady(client, connected):
    current = client.get('/api/companion').json()['companion']
    definition = {**current['version']['definition'], 'relationship': 'romance',
                  'emotional_traits': [{'name': 'jealousy', 'intensity': 'mild'}]}
    client.post('/api/companion/versions', json={'definition': definition,
                                                 'expected_version_id': current['active_version_id']})
    state = view(client)
    assert state['stages'][2] == 'Comfortable'
    prompt = system(client)
    assert 'never turns romantic' not in prompt and closeness.STEADY_TRAITS in prompt


def test_running_jokes_come_from_shared_moments_and_follow_memory_changes(client, connected):
    moment = remember_moment(client, 'The goose incident')
    fact = client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Pet', 'value': 'A cat'}).json()
    assert client.post('/api/closeness/jokes', json={'memory_id': fact['id']}).status_code == 422
    state = client.post('/api/closeness/jokes', json={'memory_id': moment['id']}).json()
    assert [joke['subject'] for joke in state['jokes']] == ['The goose incident']
    preview = client.get('/api/context/preview').json()
    assert 'Running jokes' in preview['system'] and moment['id'] in preview['receipt']['included']['closeness']
    corrected = client.post(f"/api/memories/{moment['id']}/correct",
                            json={'value': 'The goose stole a sandwich', 'expected_revision': 1}).json()
    assert view(client)['jokes'][0]['memory_id'] == corrected['id']
    client.post(f"/api/memories/{corrected['id']}/exclude")
    assert view(client)['jokes'] == []
    client.post(f"/api/memories/{corrected['id']}/include")
    assert len(view(client)['jokes']) == 1
    client.post(f"/api/memories/{corrected['id']}/delete", json={'delete_sources': False})
    assert view(client)['jokes'] == [] and 'Running jokes' not in system(client)


def test_removing_a_joke_and_reset_clear_it(client, connected):
    moment = remember_moment(client, 'Karaoke night')
    client.post('/api/closeness/jokes', json={'memory_id': moment['id']})
    assert client.post(f"/api/closeness/jokes/{moment['id']}/remove").json()['jokes'] == []
    client.post('/api/closeness/jokes', json={'memory_id': moment['id']})
    client.post('/api/closeness/reset')
    assert view(client)['jokes'] == []


def test_milestones_walk_the_history_in_order():
    days = ['2026-10-01', '2026-10-02', '2026-10-03', '2026-10-04']
    reached = closeness.milestones(days, ['2026-10-01', '2026-10-01', '2026-10-04', '2026-10-04'])
    assert [(item['level'], item['on']) for item in reached] == [(2, '2026-10-02'), (3, '2026-10-04')]


def test_moments_that_keep_coming_up_are_offered_as_running_jokes(client, connected, clock):
    moment = remember_moment(client, 'The goose incident', 'A goose chased us across the park')
    for _ in range(closeness.JOKE_DAYS):
        send(client, 'Remember the goose that chased us across the park?', f'client-{uuid4().hex}')
        clock.advance(timedelta(days=1))
    candidates = view(client)['joke_candidates']
    assert [(item['memory_id'], item['days']) for item in candidates] == [(moment['id'], closeness.JOKE_DAYS)]
    chosen = client.post('/api/closeness/jokes', json={'memory_id': moment['id']}).json()
    assert chosen['joke_candidates'] == [] and len(chosen['jokes']) == 1
