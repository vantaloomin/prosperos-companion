from datetime import timedelta

from conftest import START


def proposal(key='outing-0001', hours_ago=3, kind='ordinary', summary='Walked to the harbour market'):
    return {'idempotency_key': key, 'kind': kind, 'summary': summary,
            'starts_at': (START - timedelta(hours=hours_ago)).isoformat(),
            'ends_at': (START - timedelta(hours=hours_ago - 1)).isoformat()}


def propose(client, **overrides):
    response = client.post('/api/events', json=proposal(**overrides))
    assert response.status_code == 200, response.text
    return response.json()


def test_commit_is_idempotent_and_shared_with_chat_context(client, companion):
    event = propose(client)
    assert propose(client)['id'] == event['id']
    assert client.post(f"/api/events/{event['id']}/commit").json()['status'] == 'committed'
    assert client.post(f"/api/events/{event['id']}/commit").json()['status'] == 'committed'
    assert len(client.get('/api/events').json()) == 1
    assert 'harbour market' in client.get('/api/context/preview').json()['system']


def test_event_prepared_before_a_character_change_is_rejected(client, companion):
    event = propose(client)
    definition = {**companion['version']['definition'], 'routine': 'Night shifts'}
    client.post('/api/companion/versions', json={'definition': definition,
                                                 'expected_version_id': companion['active_version_id']})
    committed = client.post(f"/api/events/{event['id']}/commit").json()
    assert committed['status'] == 'rejected'
    assert 'character changed' in committed['rejection']


def test_pause_rejects_commits_and_the_paused_interval(client, companion, clock):
    client.post('/api/pause')
    event = propose(client, hours_ago=-1)
    assert client.post(f"/api/events/{event['id']}/commit").json()['rejection'] == 'Activity is paused.'
    clock.advance(timedelta(hours=4))
    client.post('/api/resume')
    inside = propose(client, key='outing-0002', hours_ago=-1)
    result = client.post(f"/api/events/{inside['id']}/commit").json()
    assert result['status'] == 'rejected'
    assert 'paused interval' in result['rejection']


def test_unfinished_outing_cannot_be_committed_but_a_plan_can(client, companion):
    future = propose(client, hours_ago=-2)
    assert client.post(f"/api/events/{future['id']}/commit").json()['status'] == 'rejected'
    plan = propose(client, key='plan-0001', hours_ago=-2, kind='plan', summary='Plans to visit the aquarium')
    assert client.post(f"/api/events/{plan['id']}/commit").json()['status'] == 'committed'


def test_permission_change_makes_prepared_events_stale(client, companion):
    event = propose(client)
    client.put('/api/settings', json={'background_activity': True})
    assert client.post(f"/api/events/{event['id']}/commit").json()['status'] == 'rejected'


def test_correction_replaces_the_active_account_and_keeps_the_original(client, companion):
    event = propose(client)
    client.post(f"/api/events/{event['id']}/commit")
    corrected = client.post(f"/api/events/{event['id']}/correct",
                            json={'summary': 'Walked to the flower market'}).json()
    assert corrected['supersedes_id'] == event['id'] and corrected['revision'] == 2
    prompt = client.get('/api/context/preview').json()['system']
    assert 'flower market' in prompt and 'harbour' not in prompt
    statuses = {item['id']: item['status'] for item in client.get('/api/events?history=true').json()}
    assert statuses[event['id']] == 'superseded'


def test_rejected_event_never_enters_context(client, companion):
    event = propose(client)
    client.post(f"/api/events/{event['id']}/reject")
    assert client.post(f"/api/events/{event['id']}/commit").status_code == 409
    assert 'harbour' not in client.get('/api/context/preview').json()['system']
