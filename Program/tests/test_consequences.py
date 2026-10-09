"""The consequence engine: how a turning in the world goes is worked out from state, with odds and reasons."""
from datetime import timedelta

import pytest
from conftest import reconcile, send
from test_storylines import WORKDAY, stored

from companion import consequences
from companion.life import storylines


def test_every_turning_has_a_table_with_one_option_per_way():
    turnings = {storylines.choice_key(story, index): len(stage)
                for story in storylines.STORIES for index, stage in enumerate(story.stages) if len(stage) > 1}
    tables = consequences.tables()
    assert set(turnings) == set(tables)
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
