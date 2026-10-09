"""The consequence engine: how a turning in the world goes is worked out from state, with odds and reasons."""
from datetime import timedelta

import pytest
from conftest import reconcile, send, set_life
from test_storylines import WORKDAY, stored

from companion import consequences
from companion.life import storylines

ALL_STORIES = storylines.STORIES


def test_every_turning_has_a_table_with_one_option_per_way():
    turnings = {storylines.choice_key(story, index): len(stage)
                for story in storylines.STORIES for index, stage in enumerate(story.stages) if len(stage) > 1}
    tables = consequences.tables()
    assert set(turnings) == {key for key in tables if key.startswith('storyline:')}
    for key, count in turnings.items():
        assert len(tables[key]['options']) == count, key
        for option in tables[key]['options']:
            for rule in option.get('rules', ()):
                rule['why'].format(name='Mira', a='Ana', b='Rui')


def test_state_moves_the_odds_and_says_why():
    names = {'name': 'Mira', 'a': 'Ana', 'b': 'Rui'}
    plain = consequences.odds('storyline:friends_feud:1', {'drama': 1}, names)
    assert [item['odds'] for item in plain] == [0.5, 0.5] and not plain[0]['reasons']
    old = consequences.odds('storyline:friends_feud:1', {'drama': 1, 'tie': 'old friends', 'closeness_a': 5}, names)
    assert old[0]['odds'] > 0.7 and abs(sum(item['odds'] for item in old) - 1) < 0.01
    assert 'Ana and Rui go way back' in old[0]['reasons'] and 'Mira is close to Ana and can talk them round' in old[0]['reasons']


def test_the_dice_follow_the_odds_and_repeat_for_the_same_seed():
    found = [{'option': 0, 'odds': 0.8}, {'option': 1, 'odds': 0.2}]
    rolls = [consequences.roll(f'seed-{index}', found) for index in range(400)]
    assert 0.7 < rolls.count(0) / len(rolls) < 0.9
    assert rolls == [consequences.roll(f'seed-{index}', found) for index in range(400)]


def test_the_companion_description_counts_unless_it_says_not():
    assert consequences.sheet_has({'personality': 'Ambitious and blunt.'}, 'driven')
    assert consequences.sheet_has({'personality': 'Ambitious and blunt.'}, 'assertive')
    assert not consequences.sheet_has({'personality': 'Not shy at all.'}, 'shy')
    assert consequences.sheet_has({'flaws': ['Holds grudges']}, 'stubborn')


@pytest.fixture
def driven(client, monkeypatch):
    from companion.life import body
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC', 'schedule': WORKDAY,
                                                     'location': 'Fells Point, Baltimore',
                                                     'personality': 'Driven and ambitious, a workaholic.'})
    assert response.status_code == 200, response.text
    monkeypatch.setattr(storylines, 'START', (1, 1, 1, 1))
    monkeypatch.setattr(storylines, 'STORIES', (storylines.find_story('promotion_chance'),))
    return response.json()


def test_a_turning_waits_for_its_day_then_the_engine_decides_it(client, driven, clock):
    reconcile(client)
    item = client.get('/api/life/storylines').json()[0]
    assert len(item['beats']) == 1 and item['unfolding']
    assert 'pending' in storylines_stage(client, 1)

    clock.advance(timedelta(days=30))
    reconcile(client)
    item = client.get('/api/life/storylines?include_ended=true').json()[0]
    assert len(item['beats']) == 2 and not item['unfolding'] and item['beats'][1]['consequence']
    outcome = client.get(f"/api/life/consequences/{item['beats'][1]['consequence']}").json()
    assert outcome['label'] == 'Whether Mira gets the promotion' and outcome['picked_by'] == 'dice'
    assert [option['label'] for option in outcome['options']] == ['Mira got the promotion.',
                                                                  'Mira did not get the promotion; it went to someone else.']
    assert outcome['options'][0]['odds'] > 0.6 and outcome['options'][0]['reasons'] == ['Mira is driven and it shows at work']
    assert item['beats'][1]['text'] == outcome['options'][outcome['picked']]['label']

    # Settling again changes nothing.
    reconcile(client)
    assert client.get('/api/life/storylines?include_ended=true').json()[0]['beats'] == item['beats']


def test_the_user_can_change_how_it_went(client, driven, clock):
    reconcile(client)
    clock.advance(timedelta(days=30))
    reconcile(client)
    beat = client.get('/api/life/storylines?include_ended=true').json()[0]['beats'][1]
    outcome = client.get(f"/api/life/consequences/{beat['consequence']}").json()
    other = 1 - outcome['picked']
    changed = client.post(f"/api/life/consequences/{beat['consequence']}/change", json={'option': other}).json()
    assert changed['picked'] == other and changed['picked_by'] == 'user'
    beat = client.get('/api/life/storylines?include_ended=true').json()[0]['beats'][1]
    assert beat['text'] == outcome['options'][other]['label']
    assert client.post(f"/api/life/consequences/{beat['consequence']}/change", json={'option': 5}).status_code == 422
    assert client.get('/api/life/consequences/nope').status_code == 404


def test_a_fork_keeps_decided_outcomes(client, driven, clock, provider):
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    reconcile(client)
    clock.advance(timedelta(days=30))
    reconcile(client)
    sent = send(client, 'How was work?', 'client-consequence-01')['message']
    response = client.post('/api/timelines', json={'message_id': sent['id'], 'text': 'How was your week?'})
    assert response.status_code == 200, response.text
    item = client.get('/api/life/storylines?include_ended=true').json()[0]
    outcome = client.get(f"/api/life/consequences/{item['beats'][1]['consequence']}").json()
    assert outcome['subject'] == f"storyline:{item['id']}"
    assert len({row['timeline_id'] for row in stored(client)}) == 2


def storylines_stage(client, index):
    import json
    return json.loads(stored(client)[0]['stages'])[index]


def settled_promotion(client, clock):
    reconcile(client)
    clock.advance(timedelta(days=30))
    reconcile(client)
    return client.get('/api/life/storylines?include_ended=true').json()[0]['beats'][1]['consequence']


def change(client, consequence_id, option):
    response = client.post(f'/api/life/consequences/{consequence_id}/change', json={'option': option})
    assert response.status_code == 200, response.text
    return response.json()


def test_an_outcome_leaves_marks_that_tilt_later_odds(client, driven, clock):
    consequence_id = settled_promotion(client, clock)
    missed = change(client, consequence_id, 1)
    assert [(mark['kind'], mark['amount'], mark['ripple']) for mark in missed['marks']] == [('mood', -1, False)]
    assert missed['marks'][0]['note'] == 'Mira is low after missing out on the promotion'
    got = change(client, consequence_id, 0)
    assert [(mark['kind'], mark['amount']) for mark in got['marks']] == [('money', 1)]
    assert 'a little more room in your budget' in client.get('/api/context/preview').json()['prompt']

    change(client, consequence_id, 1)
    with client.app.state.database.connect() as connection:
        from companion.characters import require_current
        companion = require_current(connection)
        row = stored(client)[0]
        found = storylines.facts(connection, companion, row, clock.now())
    assert found['mood'] == -1 and found['money'] == 0
    names = {'name': 'Mira', 'a': 'someone', 'b': 'someone'}
    low = consequences.odds('storyline:promotion_chance:1', found, names)
    assert 'Mira has had a rough few weeks' in low[0]['reasons']
    assert low[0]['odds'] < consequences.odds('storyline:promotion_chance:1', {**found, 'mood': 0}, names)[0]['odds']


def test_marks_wear_off(client, driven, clock):
    change(client, settled_promotion(client, clock), 1)
    with client.app.state.database.connect() as connection:
        timeline_id = stored(client)[0]['timeline_id']
        holder = f"companion:{driven['id']}"
        today = clock.now().date()
        assert consequences.total(connection, timeline_id, holder, 'mood', today.isoformat()) == -1
        later = (today + timedelta(days=30)).isoformat()
        assert consequences.total(connection, timeline_id, holder, 'mood', later) == 0


def test_a_mark_ripples_to_a_close_companion(client, driven, clock, monkeypatch):
    from test_small_world import neighbor

    from companion.memory import pairs
    other = {'id': neighbor(client, 'Sam')}
    monkeypatch.setattr(pairs, 'closeness', lambda connection, a, b, now: 5)
    missed = change(client, settled_promotion(client, clock), 1)
    ripple = next(mark for mark in missed['marks'] if mark['ripple'])
    assert ripple['holder'] == f"companion:{other['id']}" and ripple['who'] == 'Sam' and ripple['amount'] == -1


def test_keeping_away_leaves_someone_out_of_company(client, driven, clock, monkeypatch):
    monkeypatch.setattr(storylines, 'START', (1, 1, 1, 1))
    monkeypatch.setattr(storylines, 'STORIES', tuple(story for story in ALL_STORIES if story.key == 'friend_fight'))
    set_life(client, drama=3)
    reconcile(client)
    clock.advance(timedelta(days=30))
    reconcile(client)
    item = client.get('/api/life/storylines?include_ended=true').json()[0]
    friend = item['cast'][0]['id']
    cold = change(client, item['beats'][1]['consequence'], 1)
    assert cold['marks'][0]['kind'] == 'avoid'
    with client.app.state.database.connect() as connection:
        day = clock.now().date().isoformat()
        assert consequences.avoided(connection, item_timeline(client), day) == {friend}
    assert change(client, item['beats'][1]['consequence'], 0)['marks'] == []


def test_low_spirits_and_tight_money_tilt_the_day():
    from companion.life import disruptions
    rows = disruptions.TABLES['social']
    weights = {row['id']: row['high'] - row['low'] + 1 for row in disruptions.tilted(rows, {'cancelled': 2})}
    assert weights['cancelled'] == 22 and weights['none'] == 76
    assert disruptions.tilted(rows, {})[-1]['high'] == rows[-1]['high']


def test_a_gossip_is_likelier_to_pass_a_secret_on_the_closer_they_feel():
    names = {'name': 'they', 'a': 'them', 'b': ''}
    passing = [consequences.odds('secret:pass_on', {'closeness_a': level}, names)[0]['odds'] for level in (2, 3, 4)]
    assert passing[0] == 0 and 0.1 < passing[1] < 0.3 and passing[2] > 0.8


def item_timeline(client):
    return stored(client)[0]['timeline_id']
