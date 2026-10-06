"""The companion acts on what the user recommends: sessions in free time, a seeded verdict, no invented details."""
from datetime import timedelta

import pytest
from conftest import reconcile, send, set_life

from companion.database import decode
from companion.life import body, composer, recommendations

EVENINGS = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00', 'days': [0, 1, 2, 3, 4]},
            {'key': 'evening', 'label': 'Evening', 'kind': 'leisure', 'start': '19:00', 'end': '22:00'},
            {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]


@pytest.fixture
def mira(client, monkeypatch):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(composer, 'PLAN_SHARE', 0)
    monkeypatch.setattr(composer, 'THREAD_SHARE', 0)
    monkeypatch.setattr(recommendations, 'SESSION_SHARE', 1)
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC', 'schedule': EVENINGS,
                                                     'interests': ['science fiction']})
    assert response.status_code == 200, response.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    set_life(client, automatic_events=True, phrase_with_model=False, catch_up_max_events=6,
             catch_up_lookback_hours=168)
    return response.json()


def test_recommendations_are_found_in_the_users_words():
    assert recommendations.find('You should watch Severance sometime! And you have to read Piranesi.') == [
        ('show', 'Severance'), ('book', 'Piranesi')]
    assert recommendations.find('you gotta try the pho place on Charles St') == [('outing', 'the pho place on Charles St')]
    assert recommendations.find('You should watch the movie Arrival') == [('movie', 'the movie Arrival')]
    assert recommendations.find('You should get some sleep. Should you watch it? You should go to bed.') == []
    assert recommendations.find('Hypothetically, you should watch Cats.') == []


def test_a_recommendation_gets_sessions_a_verdict_and_reaches_the_chat(client, mira, clock):
    send(client, 'You should watch Severance, it is great', 'client-rec-01')
    waiting = client.get('/api/life/recommendations').json()
    assert [(item['title'], item['kind'], item['state']) for item in waiting] == [('Severance', 'show', 'waiting')]
    assert '- Severance (show): you have not started it yet' in client.get('/api/context/preview').json()['system']
    clock.advance(timedelta(days=6))
    reconcile(client)
    with client.app.state.database.connect() as connection:
        entries = [decode(row['entry']) for row in connection.execute(
            "SELECT entry FROM life_agenda WHERE subject='companion' AND entry IS NOT NULL ORDER BY starts_at")]
    sessions = [entry['recommendation'] for entry in entries if entry.get('recommendation')]
    total = waiting and sessions[0]['of']
    assert [item['session'] for item in sessions] == list(range(1, total + 1))
    assert all(item['verdict'] is None for item in sessions[:-1]) and sessions[-1]['verdict']
    assert all(entry['activity'] == 'recommendation' and 'Severance' in entry['summary'] for entry in entries
               if entry.get('recommendation'))
    item = client.get('/api/life/recommendations').json()[0]
    assert item['state'] == 'finished' and item['verdict'] == sessions[-1]['verdict']
    system = client.get('/api/context/preview').json()['system']
    assert f"- Severance (show): you finished it. Your verdict: {item['verdict']}." in system
    assert 'never invent plot' in system


def test_finishing_one_can_open_a_conversation(client, mira, clock, provider):
    set_life(client, texts_first=True)
    send(client, 'You should read Piranesi', 'client-rec-02')
    clock.advance(timedelta(days=7))
    reconcile(client)
    events = client.get('/api/events').json()
    finished = [event for event in events if (event['details'].get('recommendation') or {}).get('verdict')]
    assert finished
    clock.instant = clock.now().replace(hour=13)
    result = client.post('/api/life/texts/check').json()
    assert result['kind'] == 'recommendation' and 'Piranesi' in provider.requests[-1]['messages'][-1]['content']
    assert 'do not describe plot' in provider.requests[-1]['messages'][-1]['content']


def test_taking_it_back_clears_upcoming_sessions(client, mira, clock):
    send(client, 'You should play Hades', 'client-rec-03')
    clock.advance(timedelta(hours=13))
    reconcile(client)
    rec = client.get('/api/life/recommendations').json()[0]
    assert client.post(f"/api/life/recommendations/{rec['id']}/drop").json() == []
    reconcile(client)
    with client.app.state.database.connect() as connection:
        left = connection.execute("SELECT COUNT(*) FROM life_agenda WHERE status='upcoming' AND "
                                  "json_extract(entry, '$.recommendation.id')=?", (rec['id'],)).fetchone()[0]
    assert left == 0


def test_interests_tip_the_verdict_warmer():
    rec = {'id': 'r', 'title': 'a science fiction show'}
    warm = [recommendations.verdict({**rec, 'id': f'r{index}'}, {'interests': ['science fiction']})
            for index in range(300)]
    cold = [recommendations.verdict({**rec, 'id': f'r{index}'}, {}) for index in range(300)]
    assert warm.count('loved it') > cold.count('loved it')
