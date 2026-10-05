"""The companion texts first: fixed triggers, the model only phrases, and the gates that hold it back."""
from datetime import timedelta

from conftest import send, set_life

from companion.life import openers
from companion.providers.chat import Chunk


def check(client):
    response = client.post('/api/life/texts/check')
    assert response.status_code == 200, response.text
    return response.json()


def remember(client, **body):
    response = client.post('/api/memories', json=body)
    assert response.status_code == 200, response.text
    return response.json()


def interview(client):
    return remember(client, layer='plan', subject='Job interview', value='Interview at the bank on Sunday',
                    plan_status='agreed', applies_from='2026-10-04T09:00:00+00:00',
                    applies_until='2026-10-05T00:00:00+00:00')


def history(client):
    return client.get('/api/conversation').json()['messages']


def test_it_is_off_until_the_user_turns_it_on(client, companion):
    interview(client)
    assert check(client) == {'state': 'off', 'message': None}
    assert history(client) == []


def test_a_plan_whose_day_passed_gets_a_follow_up_without_a_model(client, companion, clock):
    set_life(client, texts_first=True)
    interview(client)
    result = check(client)
    assert result['state'] == 'sent' and result['kind'] == 'follow_up'
    message = result['message']
    assert message['text'] == 'Hey! How did the job interview go?'
    assert message['role'] == 'companion' and message['reply_to'] is None and message['status'] == 'complete'
    assert [item['id'] for item in history(client)] == [message['id']]
    # Never twice in a row without an answer, and each trigger only once.
    clock.advance(timedelta(hours=5))
    assert check(client)['state'] == 'waiting_for_answer'
    assert client.get('/api/context/preview').json()['messages'][-1]['content'] == message['text']


def test_the_model_phrases_it_from_the_trigger(client, connected, provider, clock):
    set_life(client, texts_first=True)
    interview(client)
    provider.replies = [[Chunk('"So?? How did the bank interview go?"'), Chunk('', 'stop')]]
    message = check(client)['message']
    assert message['text'] == 'So?? How did the bank interview go?'
    request = provider.requests[-1]
    assert 'Mira' in request['system']
    assert 'Job interview: Interview at the bank on Sunday' in request['messages'][-1]['content']
    assert 'never claim to know what the user did' in request['messages'][-1]['content']


def test_an_unusable_model_reply_falls_back_to_the_template(client, connected, provider):
    set_life(client, texts_first=True)
    interview(client)
    provider.replies = [[Chunk('x' * (openers.MAX_LENGTH + 1)), Chunk('', 'stop')]]
    assert check(client)['message']['text'] == 'Hey! How did the job interview go?'


def test_quiet_hours_sleep_recent_talk_and_the_daily_cap_hold_it(client, companion, clock):
    set_life(client, texts_first=True, texts_daily=1)
    interview(client)
    clock.instant = clock.now().replace(hour=23)
    assert check(client)['state'] == 'quiet_hours'
    client.put('/api/notifications/settings', json={'quiet_start': '00:00', 'quiet_end': '00:00'})
    assert check(client)['state'] == 'asleep'  # 23:00 UTC is midnight in Lisbon.
    clock.instant = clock.now().replace(hour=12) + timedelta(days=1)
    send(client, 'Hi!', 'client-open-01')
    assert check(client)['state'] == 'recent_conversation'
    clock.advance(timedelta(hours=4))
    assert check(client)['state'] == 'sent'
    remember(client, layer='plan', subject='Dentist', value='Dentist this morning', plan_status='agreed',
             applies_from=(clock.now() - timedelta(hours=6)).isoformat(),
             applies_until=(clock.now() - timedelta(hours=2)).isoformat())
    send(client, 'Fine thanks', 'client-open-02')
    clock.advance(timedelta(hours=4))
    assert check(client)['state'] == 'daily_cap'


def test_only_a_character_with_an_absence_trait_reaches_out_about_silence(client, companion, clock):
    set_life(client, texts_first=True)
    send(client, 'Talk soon', 'client-silence-01')
    clock.advance(timedelta(days=3))
    assert check(client)['state'] == 'nothing'
    current = client.get('/api/companion').json()['companion']
    definition = {**current['version']['definition'],
                  'emotional_traits': [{'name': 'guilt over absence', 'intensity': 'moderate'}]}
    client.post('/api/companion/versions', json={'definition': definition,
                                                 'expected_version_id': current['active_version_id']})
    result = check(client)
    assert result['kind'] == 'silence' and result['message']['text'] == openers.VOICE['moderate']


def test_settled_news_needs_a_model_and_is_told_once(client, connected, provider, clock):
    set_life(client, texts_first=True)
    database = client.app.state.database
    from companion import events
    from companion.models import EventProposal
    with database.connect() as connection:
        timeline_id = connection.execute('SELECT active_timeline_id FROM companions').fetchone()[0]
    event = events.propose(database, EventProposal(
        idempotency_key='settled:test', kind='thread', summary="Mira's record player arrived, and it works.",
        details={'state': 'settled', 'thread': 'parcel', 'thread_key': 'test'},
        starts_at=(clock.now() - timedelta(hours=3)).isoformat(), ends_at=(clock.now() - timedelta(hours=2)).isoformat(),
        inputs={}), timeline_id)
    events.commit(database, event['id'])
    provider.replies = [[Chunk('My record player finally came and it WORKS.'), Chunk('', 'stop')]]
    result = check(client)
    assert result['kind'] == 'news' and 'record player' in provider.requests[-1]['messages'][-1]['content']
    send(client, 'Nice!', 'client-news-01')
    clock.advance(timedelta(hours=5))
    assert check(client)['state'] == 'nothing'


def test_a_first_message_is_announced_when_notifications_are_on(client, companion):
    client.put('/api/notifications/settings', json={'enabled': True, 'preview': 'full', 'quiet_start': '00:00',
                                                    'quiet_end': '00:00'})
    set_life(client, texts_first=True)
    interview(client)
    sent = check(client)['message']
    shown = client.post('/api/notifications/next', json={'focused': False}).json()['notification']
    assert shown['kind'] == 'message' and shown['message_id'] == sent['id']
    assert shown['title'] == 'Mira' and shown['body'] == sent['text']
    assert client.post('/api/notifications/next', json={'focused': False}).json()['notification'] is None


def test_a_fork_keeps_the_triggers_already_used(client, companion, clock):
    set_life(client, texts_first=True)
    interview(client)
    check(client)
    clock.advance(timedelta(hours=1))
    user = send(client, 'It went great', 'client-fork-01')
    response = client.post('/api/timelines', json={'message_id': user['message']['id'], 'text': 'It went badly'})
    assert response.status_code == 200, response.text
    timeline = response.json()
    client.post(f"/api/timelines/{timeline['id']}/activate", json={})
    clock.advance(timedelta(hours=5))
    assert check(client)['state'] in {'waiting_for_answer', 'nothing'}


def test_an_older_workspace_gains_the_message_delivery_kind(tmp_path, clock):
    from companion.database import Database
    path = tmp_path / 'old.sqlite3'
    Database(path, clock)
    import sqlite3
    connection = sqlite3.connect(path)
    connection.executescript("""
        DROP TABLE notification_deliveries;
        CREATE TABLE notification_deliveries (id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK (kind IN ('post', 'digest')),
          post_count INTEGER NOT NULL, delivered_at TEXT NOT NULL);
        INSERT INTO notification_deliveries VALUES ('old', 'post', 1, '2026-10-01T00:00:00+00:00');
        UPDATE app_identity SET value='stale' WHERE key='schema_digest';
    """)
    connection.close()
    database = Database(path, clock)
    with database.connect(write=True) as connection:
        connection.execute("INSERT INTO notification_deliveries VALUES ('new', 'message', 0, '2026-10-05T00:00:00+00:00')")
        assert [row[0] for row in connection.execute('SELECT id FROM notification_deliveries ORDER BY id')] == ['new', 'old']
