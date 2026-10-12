"""Bring your old chats (companion/imports/chats.py): SillyTavern and role/content files as older history."""
import base64
import json
from datetime import UTC, date, datetime

import pytest
from conftest import START, send

from companion import group_openers, recap
from companion.characters import require_current
from companion.clock import parse
from companion.imports import chats
from companion.life import occasions, openers, reactions, usual_hours
from companion.life.mood import last_presence
from companion.memory.records import from_old_chats

HEADER = {'user_name': 'Sam', 'character_name': 'Mira', 'create_date': '2024-3-1 @14h 00m 00s 000ms',
          'chat_metadata': {'note_prompt': ''}}


def tavern(*rows, header=True) -> bytes:
    return '\n'.join(json.dumps(row) for row in ([HEADER] if header else []) + list(rows)).encode()


def line(text, user=True, date=None, **extra) -> dict:
    row = {'name': 'Sam' if user else 'Mira', 'is_user': user, 'is_system': False, 'mes': text, 'extra': {}}
    return row | ({'send_date': date} if date is not None else {}) | extra


def bring(client, raw: bytes, filename='chat.jsonl', expect=200, **body):
    response = client.post('/api/import/chat', json={'filename': filename, 'data': base64.b64encode(raw).decode(),
                                                     **body})
    assert response.status_code == expect, response.text
    return response.json()


def history(client) -> list[dict]:
    return client.get('/api/conversation', params={'limit': 500}).json()['messages']


def remember_automatically(client):
    response = client.put('/api/settings', json={'automatic_memory': True})
    assert response.status_code == 200, response.text


def test_a_sillytavern_chat_comes_in_dated_with_the_chosen_swipe_and_no_system_lines(client, companion):
    raw = tavern(
        line('Hi Sam, good to see you.', user=False, date='March 1, 2024 2:05pm'),
        line('Hey! Long week.', date='2024-3-1 @14h 06m 30s 120ms'),
        line('Tell me everything.', user=False, date=1709302080000,
             swipes=['Tell me everything.', 'Oh no, what happened?'], swipe_id=1),
        line('[The story pauses]', user=False, is_system=True, date='2024-3-1 @14h 09m 00s'),
        line('Night falls over the city.', user=False, extra={'type': 'narrator'}),
        line('   ', date='2024-3-1 @14h 10m 00s'),
        line('Work was a mess, but I survived.', date='2024-03-01T14:12:00Z'),
    )
    result = bring(client, raw)
    assert (result['format'], result['messages'], result['skipped'], result['dated']) == ('sillytavern', 4, 3, True)
    messages = history(client)
    assert [(item['role'], item['text']) for item in messages] == [
        ('companion', 'Hi Sam, good to see you.'), ('user', 'Hey! Long week.'),
        ('companion', 'Oh no, what happened?'), ('user', 'Work was a mess, but I survived.')]
    assert [item['created_at'][:19] for item in messages] == [
        '2024-03-01T14:05:00', '2024-03-01T14:06:30', '2024-03-01T14:08:00', '2024-03-01T14:12:00']
    assert all(item['import_id'] == result['id'] and item['seq'] < 0 for item in messages)
    assert messages[2]['reply_to'] == messages[1]['id'] and messages[0]['reply_to'] is None
    assert (result['first_at'][:16], result['last_at'][:16]) == ('2024-03-01T14:05', '2024-03-01T14:12')


def test_an_undated_transcript_lands_just_before_the_first_message_already_there(client, connected):
    first = send(client, 'Morning!', 'client-0001')['message']
    raw = json.dumps({'messages': [
        {'role': 'system', 'content': 'You are Mira.'},
        {'role': 'user', 'content': 'Do you like rain?'},
        {'role': 'assistant', 'content': [{'type': 'text', 'text': 'I love it.'}]},
        {'role': 'tool', 'content': '{}'},
        {'role': 'user', 'content': 'Me too.'},
    ]}).encode()
    result = bring(client, raw, filename='C:\\Users\\sam\\old chat.json')
    assert (result['format'], result['messages'], result['skipped'], result['dated']) == ('messages', 3, 2, False)
    assert result['filename'] == 'old chat.json'
    messages = history(client)
    assert [item['text'] for item in messages] == ['Do you like rain?', 'I love it.', 'Me too.', 'Morning!',
                                                   'Hello again.']
    times = [parse(item['created_at']) for item in messages[:3]]
    assert times == sorted(times) and times[-1] < parse(first['created_at'])
    assert (parse(first['created_at']) - times[-1]).total_seconds() == 3600
    # Sending carries on after the history, and paging back reaches the imported lines.
    assert send(client, 'Still there?', 'client-0002')['message']['seq'] > first['seq']
    oldest = client.get('/api/conversation', params={'limit': 2, 'before_seq': messages[3]['seq']}).json()
    assert [item['text'] for item in oldest['messages']] == ['I love it.', 'Me too.']


def test_long_undated_chats_are_spread_over_sittings_a_day_apart(client, companion):
    rows = [{'role': 'user' if index % 2 == 0 else 'assistant', 'content': f'Line {index}'} for index in range(130)]
    bring(client, json.dumps(rows).encode(), filename='long.json')
    times = [parse(item['created_at']) for item in history(client)]
    assert times[-1] == START - chats.BEFORE_FIRST
    assert times[-1] - times[-2] == chats.STEP
    assert times[-chats.SITTING] - times[-chats.SITTING - 1] > chats.BETWEEN - chats.STEP * chats.SITTING


def test_gaps_in_the_file_dates_are_filled_and_never_run_backwards(client, companion):
    rows = [{'role': 'user', 'content': 'One'},
            {'role': 'assistant', 'content': 'Two', 'timestamp': '2024-05-09T10:00:00+00:00'},
            {'role': 'user', 'content': 'Three'},
            {'role': 'assistant', 'content': 'Four', 'timestamp': '2024-05-01T10:00:00+00:00'},
            {'role': 'user', 'content': 'Five', 'create_time': 1715250000}]
    bring(client, json.dumps(rows).encode(), filename='gaps.json')
    times = [item['created_at'][:19] for item in history(client)]
    assert times == ['2024-05-09T09:58:00', '2024-05-09T10:00:00', '2024-05-09T10:02:00', '2024-05-09T10:02:00',
                     '2024-05-09T10:20:00']


@pytest.mark.parametrize(('value', 'expected'), [
    ('2024-3-1 @14h 05m 09s 120ms', '2024-03-01T14:05:09.120000'),
    ('2024-3-1@9h 5m 9s', '2024-03-01T09:05:09'),
    ('March 1, 2024 2:05pm', '2024-03-01T14:05:00'),
    ('Mar 1, 2024 2:05 PM', '2024-03-01T14:05:00'),
    ('2024-03-01T14:05:00Z', '2024-03-01T14:05:00'),
    ('2024-03-01T14:05:00+02:00', '2024-03-01T12:05:00'),
    (1709301900000, '2024-03-01T14:05:00'),
    (1709301900, '2024-03-01T14:05:00'),
    ('1709301900000', '2024-03-01T14:05:00'),
])
def test_dates_are_read_in_each_format(value, expected):
    assert chats.when(value, 'UTC').replace(tzinfo=None).isoformat() == expected


@pytest.mark.parametrize('value', [None, True, '', 'yesterday', 'Not a date', 0, '1999-13-40', [], {}])
def test_unreadable_dates_are_left_out(value):
    assert chats.when(value, 'UTC') is None


def test_a_local_date_is_read_in_the_users_timezone(client, companion):
    client.put('/api/settings', json={'user_timezone': 'America/Chicago'})
    bring(client, tavern(line('Hello', date='March 1, 2024 2:05pm')))
    assert history(client)[0]['created_at'][:19] == '2024-03-01T20:05:00'


def test_memories_come_from_the_old_chat_by_the_rules_alone(client, connected, provider):
    remember_automatically(client)
    raw = tavern(line('I live in Chicago. My favourite tea is genmaicha.', date='2024-3-1 @14h 06m 30s'),
                 line('Chicago! Lovely.', user=False, date='2024-3-1 @14h 07m 00s'))
    result = bring(client, raw)
    assert result['memories'] == 2 and result['automatic_memory'] is True
    assert provider.requests == []
    found = {item['subject']: item for item in client.get('/api/memories').json()}
    user_line = history(client)[0]
    assert found['Home city']['value'] == 'Chicago'
    assert found['Home city']['source_message_ids'] == [user_line['id']]
    assert found['Home city']['stated_at'][:16] == '2024-03-01T14:06'
    status = client.get('/api/memory/status').json()
    assert status['jobs'] == {'done': 1}
    with client.app.state.database.connect() as connection:
        assert connection.execute('SELECT model_status FROM memory_jobs').fetchone()[0] == 'skipped'


def test_with_automatic_memory_off_the_history_still_comes_in_without_memories(client, companion):
    assert client.put('/api/settings', json={'automatic_memory': False}).status_code == 200
    result = bring(client, tavern(line('I live in Chicago.', date='2024-3-1 @14h 06m 30s')))
    assert (result['messages'], result['memories'], result['automatic_memory']) == (1, 0, False)
    assert client.get('/api/memories').json() == []


def test_an_older_fact_from_the_old_chat_is_history_not_a_conflict(client, connected):
    remember_automatically(client)
    send(client, 'I live in Denver.', 'client-0001')
    assert client.post('/api/memory/run').json()['done'] == 1
    bring(client, tavern(line('I live in Chicago.', date='2024-3-1 @14h 06m 30s')))
    rows = {item['value']: item for item in client.get('/api/memories', params={'history': True}).json()}
    assert rows['Denver']['applies_until'] is None
    assert rows['Chicago']['applies_until'] is not None and rows['Chicago']['ended_by_id'] == rows['Denver']['id']
    assert client.get('/api/memory/suggestions').json() == []


def test_old_chats_never_count_as_being_here_or_growing_closer(client, companion):
    days = [line(f'Day {day}, I made soup.', date=f'2024-3-{day} @14h 00m 00s') for day in range(1, 21)]
    bring(client, tavern(*days))
    stage = client.get('/api/closeness').json()
    assert (stage['level'], stage['days_talked']) == (1, 0)
    with client.app.state.database.connect() as connection:
        assert last_presence(connection, companion['active_timeline_id']) == companion_activation(connection)


def companion_activation(connection):
    return connection.execute('SELECT activated_at FROM timelines').fetchone()[0]


def test_an_undated_old_chat_just_before_now_leaves_every_sign_of_the_user_untouched(client, companion):
    rows = [{'role': 'user' if index % 2 == 0 else 'assistant', 'content': f'Hello {index}, happy birthday!'}
            for index in range(20)]
    bring(client, json.dumps(rows).encode(), filename='recent.json')
    listed = client.get('/api/chats').json()
    assert listed['unread'] == 0
    timeline_id = companion['active_timeline_id']
    with client.app.state.database.connect() as connection:
        assert usual_hours.starts(connection, START) == []
        assert recap.last_from_user(connection, timeline_id) is None
        assert group_openers.last_user_at(connection) is None
        assert occasions.first_talk(connection, timeline_id, UTC) is None
        assert reactions.user_messages(connection, timeline_id, START.date(), UTC) == []
        assert openers.held(connection, require_current(connection), life_settings(connection), START) \
            != 'recent_conversation'


def life_settings(connection):
    return dict(connection.execute('SELECT * FROM life_settings').fetchone())


def test_a_plan_only_an_old_chat_mentioned_is_never_followed_up_or_missed(client, connected):
    remember_automatically(client)
    bring(client, tavern(line('My sister Jo is visiting tomorrow.', date='2026-10-3 @09h 00m 00s')))
    with client.app.state.database.connect() as connection:
        companion = require_current(connection)
        plans = connection.execute("SELECT id, plan_status, applies_from FROM memories WHERE layer='plan'").fetchall()
        assert [(row[1], row[2][:10]) for row in plans] == [('agreed', '2026-10-04')]
        assert {row[0] for row in plans} <= from_old_chats(connection, companion['active_timeline_id'])
        assert openers.plan_follow_ups(connection, companion, START) == []
        assert reactions.agreed_plans(connection, companion, date(2026, 10, 4)) == []


def test_an_old_chat_never_corrects_what_the_user_said_since(client, connected):
    remember_automatically(client)
    send(client, 'I live in Denver.', 'client-0001')
    assert client.post('/api/memory/run').json()['done'] == 1
    bring(client, tavern(line("No, I don't live in Denver.", date='2024-3-1 @14h 06m 30s')))
    current = [item for item in client.get('/api/memories').json() if item['subject_key'] == 'home_city']
    assert [item['value'] for item in current] == ['Denver'] and current[0]['applies_until'] is None


def test_the_same_file_does_not_come_in_twice_and_a_second_file_goes_further_back(client, companion):
    first = tavern(line('Second chat', date='2024-5-1 @10h 00m 00s'))
    bring(client, first)
    assert bring(client, first, expect=409)['detail'] == 'This chat already came in.'
    bring(client, json.dumps([{'role': 'user', 'content': 'First chat'}]).encode(), filename='older.json')
    assert [item['text'] for item in history(client)] == ['First chat', 'Second chat']


@pytest.mark.parametrize(('raw', 'status'), [
    (b'\xff\xfe\x00binary', 422),
    (b'just some words', 422),
    (b'{"name": "a character card"}', 422),
    (json.dumps(HEADER).encode(), 422),
    (json.dumps([{'role': 'system', 'content': 'Only rules here.'}]).encode(), 422),
    (b'[]', 422),
])
def test_files_that_are_not_chats_are_refused(client, companion, raw, status):
    bring(client, raw, expect=status)
    assert history(client) == []


def test_limits_and_a_broken_upload_are_refused(client, companion, monkeypatch):
    response = client.post('/api/import/chat', json={'filename': 'chat.jsonl', 'data': 'not base64!'})
    assert response.status_code == 422
    monkeypatch.setattr(chats, 'MAX_BYTES', 100)
    bring(client, tavern(*[line('x' * 20)] * 10), expect=413)
    monkeypatch.setattr(chats, 'MAX_BYTES', 10 * 1024 * 1024)
    monkeypatch.setattr(chats, 'MAX_LINES', 3)
    bring(client, tavern(*[line('Hello')] * 5), expect=413)
    bring(client, json.dumps([{'role': 'user', 'content': 'Hello'}] * 5).encode(), filename='a.json', expect=413)
    assert history(client) == []


def test_a_chat_can_come_in_for_a_companion_by_id_and_needs_one(client):
    assert bring(client, tavern(line('Hello')), expect=409)['detail'] == 'Create a companion first.'
    created = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC'}).json()
    assert bring(client, tavern(line('Hello')), companion_id=created['id'])['companion_id'] == created['id']
    assert bring(client, tavern(line('Hi')), companion_id='missing', expect=404)


def test_an_old_chat_is_never_answered_again(client, connected, provider):
    bring(client, tavern(line('Are you there?', date='2024-3-1 @14h 00m 00s')))
    latest = history(client)[-1]
    response = client.post(f"/api/conversation/messages/{latest['id']}/alternatives")
    assert response.status_code == 409 and response.json()['detail'] == 'This message came in from an old chat.'
    assert provider.requests == []


def test_header_less_sillytavern_lines_are_read_too(client, companion):
    result = bring(client, tavern(line('Hello', date=datetime(2024, 3, 1, tzinfo=UTC).isoformat()), header=False))
    assert (result['format'], result['messages']) == ('sillytavern', 1)
