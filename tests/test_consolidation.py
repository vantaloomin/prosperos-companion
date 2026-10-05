"""Bounded consolidation: episode summaries, merge proposals and limited resurfacing (PRD M10, M11)."""
from datetime import timedelta

from conftest import send

from companion.memory import consolidation, context
from companion.memory.chunks import compile_chunks

DAY_ONE = ['We finally went to the lighthouse at Cape Ann today',
           'The lighthouse keeper told us stories about shipwrecks',
           'Afterwards we ate clam chowder by the harbour',
           'I want to go back to the lighthouse in spring']


def chat_day(client, prefix='day'):
    return [send(client, text, f'{prefix}-{index:04d}')['message'] for index, text in enumerate(DAY_ONE)]


def consolidate(client):
    response = client.post('/api/memory/consolidate')
    assert response.status_code == 200, response.text
    return response.json()


def summary_rows(app):
    with app.state.database.connect() as connection:
        return [dict(row) for row in connection.execute('SELECT * FROM memory_summaries')]


def test_a_finished_day_gets_a_summary_quoting_the_user(client, app, connected, clock):
    chat_day(client)
    assert consolidate(client)['summaries'] == 0, 'today is not finished yet'
    clock.advance(timedelta(days=1))
    assert consolidate(client)['summaries'] == 1
    [summary] = summary_rows(app)
    assert '“The lighthouse keeper told us stories about shipwrecks”' in summary['text']
    assert consolidate(client)['summaries'] == 0, 'an unchanged day is not summarised again'
    assert client.get('/api/memories').json() == [], 'a summary never becomes a memory'


def test_summaries_are_recalled_and_labelled_as_reminders(client, app, connected, clock, provider):
    chat_day(client)
    for index in range(12):
        send(client, f'Small talk number {index}', f'filler-{index:04d}')
    clock.advance(timedelta(days=1))
    consolidate(client)
    send(client, 'Tell me about that lighthouse keeper and the shipwrecks', 'query-0001')
    assert 'a reminder, not confirmation' in provider.requests[-1]['system']


def test_deleting_or_excluding_a_source_drops_the_summary(client, app, connected, clock):
    messages = chat_day(client)
    clock.advance(timedelta(days=1))
    consolidate(client)
    [summary] = summary_rows(app)
    keeper = next(message for message in messages if 'keeper' in message['text'])
    memory = client.post('/api/memories', json={'layer': 'shared_experience', 'subject': 'Lighthouse',
                                                'value': 'Keeper stories', 'source_message_ids': [keeper['id']]}).json()
    client.post(f"/api/memories/{memory['id']}/exclude")
    with app.state.database.connect() as connection:
        companion = connection.execute('SELECT * FROM companions').fetchone()
        blocked = consolidation.excluded_sources(connection, companion['id'])
        assert consolidation.usable_summaries(connection, summary['timeline_id'], blocked) == []
    client.post(f"/api/memories/{memory['id']}/include")
    client.post(f"/api/memories/{memory['id']}/delete", json={'delete_sources': True})
    assert summary_rows(app) == []


def test_a_run_that_overlaps_a_change_commits_nothing(client, app, connected, clock, monkeypatch):
    chat_day(client)
    clock.advance(timedelta(days=1))
    original = consolidation.quotes

    def change_meanwhile(messages):
        client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Home city', 'value': 'Salem'})
        return original(messages)

    monkeypatch.setattr(consolidation, 'quotes', change_meanwhile)
    assert consolidation.summarize(app.state.database) == {'summaries': 0, 'stale': True}
    assert summary_rows(app) == []


def test_near_duplicates_are_proposed_and_merged_only_when_accepted(client, companion):
    older = client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Likes',
                                               'value': 'genmaicha green tea'}).json()
    newer = client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Likes',
                                               'value': 'genmaicha green tea leaves'}).json()
    client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Likes', 'value': 'sea swimming'})
    assert consolidate(client)['proposed'] == 1
    assert consolidate(client)['proposed'] == 0
    [proposal] = client.get('/api/memory/proposals').json()
    assert (proposal['keep']['id'], proposal['merge']['id']) == (newer['id'], older['id'])
    assert len([item for item in client.get('/api/memories').json() if 'genmaicha' in item['value']]) == 2
    client.post(f"/api/memory/proposals/{proposal['id']}/accept")
    current = [item['id'] for item in client.get('/api/memories').json() if 'genmaicha' in item['value']]
    assert current == [newer['id']]
    result = client.post(f"/api/memories/{newer['id']}/delete", json={'delete_sources': False}).json()
    assert sorted(result['deleted_memory_ids']) == sorted([older['id'], newer['id']])


def test_a_declined_merge_is_not_proposed_again(client, companion):
    for value in ('genmaicha green tea', 'genmaicha green tea leaves'):
        client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Likes', 'value': value})
    consolidate(client)
    [proposal] = client.get('/api/memory/proposals').json()
    client.post(f"/api/memory/proposals/{proposal['id']}/decline")
    consolidate(client)
    assert client.get('/api/memory/proposals').json() == []


def memory(identity, value):
    return {'id': identity, 'subject': 'Beach', 'value': value, 'layer': 'shared_experience', 'boundary': False,
            'pinned': False, 'plan_status': None, 'applies_from': None, 'applies_until': None,
            'stated_at': '2026-10-05T12:00:00+00:00'}


def test_a_resurfacing_anecdote_needs_the_users_own_words():
    beach = memory('beach', 'The day we got sunburnt at the beach')
    [chunk] = compile_chunks('memory:beach', 'Beach', 'Beach: The day we got sunburnt at the beach', 'memory')
    assert [item[0] for item in context.recalled([beach], [], 'any plans this weekend', [chunk.id])] == ['beach']
    assert context.recalled([beach], [], 'any plans this weekend', [chunk.id], surfaced={'beach'}) == []
    asked = context.recalled([beach], [], 'remember the beach sunburn?', [chunk.id], surfaced={'beach'})
    assert [item[0] for item in asked] == ['beach'], 'asking directly still recalls it'
