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


def test_moments_that_keep_coming_up_become_running_jokes_on_their_own(client, connected, clock):
    moment = remember_moment(client, 'The goose incident', 'A goose chased us across the park')
    for _ in range(closeness.JOKE_DAYS):
        send(client, 'Remember the goose that chased us across the park?', f'client-{uuid4().hex}')
        clock.advance(timedelta(days=1))
    state = view(client)
    assert [joke['memory_id'] for joke in state['jokes']] == [moment['id']] and state['joke_candidates'] == []
    # Removed, it stays out and is offered back; added again, it is a running joke again.
    removed = client.post(f"/api/closeness/jokes/{moment['id']}/remove").json()
    assert removed['jokes'] == []
    assert [(item['memory_id'], item['days']) for item in removed['joke_candidates']] == [(moment['id'], closeness.JOKE_DAYS)]
    chosen = client.post('/api/closeness/jokes', json={'memory_id': moment['id']}).json()
    assert chosen['joke_candidates'] == [] and len(chosen['jokes']) == 1


def revise(client, **changes):
    current = client.get('/api/companion').json()['companion']
    response = client.post('/api/companion/versions', json={'definition': {**current['version']['definition'], **changes},
                                                             'expected_version_id': current['active_version_id']})
    assert response.status_code == 200, response.text


def test_a_set_stage_keeps_growing_from_there(client, connected, clock):
    talk_on_days(client, clock, 3)
    state = client.put('/api/closeness', json={'set_level': 4}).json()
    assert state['level'] == 4 and state['held_level'] is None and state['history'][-1]['kind'] == 'set'
    assert 'Close friends.' in system(client)
    talk_on_days(client, clock, 13)
    assert view(client)['level'] == 4
    talk_on_days(client, clock, 1)
    assert view(client)['level'] == 5  # 17 days talked + the 13 points the set stage added = 30


def test_a_step_back_lowers_it_and_it_grows_again(client, connected, clock):
    talk_on_days(client, clock, 8)
    assert view(client)['level'] == 3
    state = client.put('/api/closeness', json={'set_level': 2}).json()
    assert state['level'] == 2 and state['earned_level'] == 2
    talk_on_days(client, clock, 5)
    assert view(client)['level'] == 3  # 3 points from the set stage + 5 days = 8


def test_a_ceiling_caps_growth_and_setting_above_it_lifts_it(client, connected, clock):
    assert client.put('/api/closeness', json={'ceiling_level': 2}).json()['ceiling_level'] == 2
    talk_on_days(client, clock, 8)
    state = view(client)
    assert state['level'] == 2 and state['earned_level'] == 3
    state = client.put('/api/closeness', json={'set_level': 4}).json()
    assert state['level'] == 4 and state['ceiling_level'] is None
    assert client.put('/api/closeness', json={'ceiling_level': 6}).status_code == 422


def test_a_new_companion_can_start_close_with_a_shared_history(client, connected, clock):
    revise(client, starting_closeness=3, history_together='Roommates all through college.')
    state = view(client)
    assert state['level'] == 3 and state['starting_level'] == 3 and state['history'][0]['kind'] == 'start'
    prompt = system(client)
    assert 'Friends.' in prompt and 'How you and the user know each other: Roommates all through college.' in prompt
    talk_on_days(client, clock, 8)
    assert view(client)['level'] == 4  # 8 starting points + 8 days = 16
    assert client.post('/api/closeness/reset').json()['level'] == 1


def test_gentle_cooling_is_opt_in_and_warms_back_up(client, connected, clock):
    talk_on_days(client, clock, 3)
    client.put('/api/closeness', json={'set_level': 4, 'cooling': True})
    clock.advance(timedelta(days=closeness.COOL_AFTER[0]))
    state = view(client)
    assert state['cooling'] and state['level'] == 3 and state['cooled_steps'] == 1
    assert closeness.COOLED in system(client)
    clock.advance(timedelta(days=closeness.COOL_AFTER[1]))
    state = view(client)
    assert state['level'] == closeness.COOL_FLOOR and state['cooled_steps'] == 2
    talk_on_days(client, clock, closeness.WARM_DAYS)
    assert view(client)['level'] == 3
    talk_on_days(client, clock, closeness.WARM_DAYS)
    state = view(client)
    assert state['level'] == 4 and state['cooled_steps'] == 0 and closeness.COOLED not in system(client)
    held = client.put('/api/closeness', json={'held_level': 4}).json()
    clock.advance(timedelta(days=90))
    assert view(client)['level'] == 4 and held['level'] == 4
    client.put('/api/closeness', json={'held_level': None, 'cooling': False})
    assert view(client)['level'] == 4 and view(client)['cooling'] is False


def test_cooling_never_goes_below_the_floor_or_starts_before_it_was_turned_on():
    assert closeness.cooling(['2026-01-01'], '2026-03-01', '2026-03-10')['steps'] == 0
    assert closeness.cooling([], '2026-01-01', '2026-12-31')['steps'] == len(closeness.COOL_AFTER)
    warming = closeness.cooling(['2026-02-01'], '2026-01-01', '2026-02-01')
    assert warming == {'steps': 1, 'warm_days_left': 1, 'silent_days': 0}


def test_townsfolk_start_as_close_as_their_meetings_make_them():
    from companion.cast import starting_closeness
    meet = lambda count: {'match': None, 'meetings': [{}] * count, 'in_story': None}  # noqa: E731
    assert [starting_closeness(meet(count)) for count in (0, 2, 3, 5, 6, 20)] == [1, 1, 2, 2, 3, 3]
    assert starting_closeness({'match': {'noun': 'match'}, 'meetings': [{}] * 9, 'in_story': None}) == 1
    assert starting_closeness({'match': None, 'meetings': [{}] * 2, 'in_story': {'meetings': 4}}) == 3


def test_settings_can_change_a_companion_who_is_not_open(client, companion):
    from test_bring_characters import CARD, as_json, bring
    mira = companion['id']
    bring(client, 'dana.json', as_json(CARD))
    capped = client.put('/api/closeness', params={'companion': mira}, json={'ceiling_level': 2, 'set_level': 2}).json()
    assert capped['ceiling_level'] == 2 and capped['level'] == 2
    assert client.get('/api/closeness', params={'companion': mira}).json()['ceiling_level'] == 2
    # The open companion, Dana, is untouched.
    assert view(client)['ceiling_level'] is None and view(client)['level'] == 1
    assert client.get('/api/closeness', params={'companion': 'nobody'}).status_code == 404
