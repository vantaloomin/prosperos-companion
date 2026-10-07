"""Storylines unfold over days in the companion's and the circle's lives, seeded, at the chosen drama level."""
import json
from datetime import date, timedelta

import pytest
from conftest import reconcile, send, set_life

from companion.life import body, circle, storylines

WORKDAY = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00', 'days': [0, 1, 2, 3, 4]},
           {'key': 'evening', 'label': 'Evening', 'kind': 'social', 'start': '18:00', 'end': '22:00'},
           {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]


@pytest.fixture
def social(client, monkeypatch):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC', 'schedule': WORKDAY,
                                                     'location': 'Fells Point, Baltimore',
                                                     'personality': 'Outgoing, a social butterfly.'})
    assert response.status_code == 200, response.text
    return response.json()


def stored(client):
    with client.app.state.database.connect() as connection:
        return [dict(row) for row in connection.execute('SELECT * FROM storylines ORDER BY started_on')]


def test_every_beat_fills_in():
    names = {'p1': {'name': 'Ana', 'role': 'mom'}, 'p2': {'name': 'Rui', 'role': 'dad'}}
    row = {'cast_ids': '["p1", "p2"]'}
    for story in storylines.STORIES:
        for stage in story.stages:
            for beat in stage:
                for text in (beat.text, beat.share):
                    filled = storylines.fill(text, row, names, {'name': 'Mira'})
                    assert '{' not in filled and filled[0] == filled[0].upper()
                assert beat.tone in ('good', 'bad', 'mixed')


def test_the_context_tells_every_beat_to_the_companion_as_you():
    names = {'p1': {'name': 'Cathy', 'role': 'mom'}, 'p2': {'name': 'Rui', 'role': 'dad'}}
    row = {'cast_ids': '["p1", "p2"]'}
    told = set()
    for story in storylines.STORIES:
        for stage in story.stages:
            for beat in stage:
                text = storylines.fill(beat.text, row, names, {'name': 'Mya Freeman'}, you=True)
                assert 'Mya' not in text and 'Freeman' not in text and '{' not in text
                told.add(text)
    assert 'You heard you are being considered for a promotion.' in told
    assert 'You got the promotion.' in told
    assert 'Your mom Cathy got engaged.' in told and 'Cathy, your mom, got a promotion at work.' in told
    assert 'A new guy at your work keeps hitting on you, and it is getting uncomfortable.' in told
    assert 'There are rumors of layoffs at your work.' in told
    assert "Cathy and Rui still aren't speaking; you are seeing them separately." in told
    assert 'Your mom Cathy let slip that you have a half-sibling you never knew about.' in told
    assert 'You looked the half-sibling up online but have not reached out.' in told
    # Today keeps the third person.
    third = storylines.fill('{name} got the promotion.', row, names, {'name': 'Mya Freeman'})
    assert third == 'Mya Freeman got the promotion.'


def test_only_an_unmarried_sibling_gets_engaged():
    engaged = storylines.find_story('sibling_engaged')
    people = [{'id': 'jo', 'role': 'sister', 'details': json.dumps({'married': True})},
              {'id': 'al', 'role': 'brother', 'details': json.dumps({})}]
    assert storylines.casts(engaged, people, {}) == [('al',)]


def test_drama_sets_what_can_happen(client, social, monkeypatch):
    monkeypatch.setattr(storylines, 'START', storylines.CHANCES)
    with client.app.state.database.connect() as connection:
        from companion.characters import require_current
        companion = require_current(connection)
        people = circle.ensure(connection, companion, client.app.state.life.world,
                               client.app.state.database.clock.now())
        definition = companion['version']['definition']
        drunk = storylines.find_story('drunk_kiss')
        assert storylines.casts(drunk, people, definition)
        assert storylines.casts(drunk, people, {**definition, 'relationship': 'romance'}) == []
        levels = {0: set(), 3: set()}
        for level in levels:
            for offset in range(400):
                found = storylines.start(connection, companion, people, date(2026, 1, 1) + timedelta(days=offset), level)
                if found:
                    levels[level].add(found['level'])
                    first = storylines.start(connection, companion, people,
                                             date(2026, 1, 1) + timedelta(days=offset), level)
                    assert first == found
        assert levels[0] == {0} and 3 in levels[3]


def test_beats_stay_hidden_until_their_day_and_reach_the_context(client, social, clock, monkeypatch):
    monkeypatch.setattr(storylines, 'START', (1, 1, 1, 1))
    monkeypatch.setattr(storylines, 'STORIES', tuple(story for story in storylines.STORIES if len(story.stages) > 1))
    set_life(client, drama=2)
    reconcile(client)
    rows = stored(client)
    assert len(rows) == 1 and rows[0]['started_on'] == clock.now().date().isoformat()
    listed = client.get('/api/life/storylines').json()
    assert len(listed) == 1 and len(listed[0]['beats']) == 1 and listed[0]['unfolding']
    first = listed[0]['beats'][0]['text']
    system = client.get('/api/context/preview').json()['system']
    assert "What is going on in your life and your people's lives" in system
    section = system.split('## What is going on')[1].split('\n## ')[0]
    assert 'Still unfolding' in section and 'Mira' not in section
    clock.advance(timedelta(days=30))
    reconcile(client)
    item = next(item for item in client.get('/api/life/storylines?include_ended=true').json() if item['id'] == listed[0]['id'])
    assert not item['unfolding'] and len(item['beats']) >= 2 and item['beats'][0]['text'] == first


def test_ending_one_takes_it_out_of_today_and_the_context(client, social, monkeypatch):
    monkeypatch.setattr(storylines, 'START', (1, 1, 1, 1))
    reconcile(client)
    item = client.get('/api/life/storylines').json()[0]
    assert client.post(f"/api/life/storylines/{item['id']}/end").json() == []
    assert client.post(f"/api/life/storylines/{item['id']}/end").status_code == 409
    assert item['beats'][0]['text'] not in client.get('/api/context/preview').json()['system']


def test_removing_someone_ends_their_storylines(client, social, monkeypatch):
    monkeypatch.setattr(storylines, 'START', (1, 1, 1, 1))
    monkeypatch.setattr(storylines, 'STORIES', tuple(story for story in storylines.STORIES if story.cast == 'friend'))
    reconcile(client)
    item = client.get('/api/life/storylines').json()[0]
    client.post(f"/api/life/circle/{item['cast'][0]['id']}/remove")
    reconcile(client)
    assert all(row['status'] == 'ended' for row in stored(client) if row['id'] == item['id'])


def test_a_new_beat_can_open_a_conversation(client, social, clock, monkeypatch):
    monkeypatch.setattr(storylines, 'START', (1, 1, 1, 1))
    monkeypatch.setattr(storylines, 'STORIES', (storylines.find_story('work_creep'),))
    set_life(client, texts_first=True)
    reconcile(client)
    clock.instant = clock.now().replace(hour=19)
    result = client.post('/api/life/texts/check').json()
    assert result['kind'] == 'storyline'
    messages = client.get('/api/conversation').json()['messages']
    assert messages[-1]['text'] == 'I hate the new guy at work. He keeps hitting on me.'


def test_a_fork_keeps_storylines_that_had_started(client, social, clock, monkeypatch, provider):
    monkeypatch.setattr(storylines, 'START', (1, 1, 1, 1))
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    reconcile(client)
    clock.advance(timedelta(hours=1))
    sent = send(client, 'How was your day?', 'client-story-01')['message']
    response = client.post('/api/timelines', json={'message_id': sent['id'], 'text': 'How was work?'})
    assert response.status_code == 200, response.text
    rows = stored(client)
    assert len({row['timeline_id'] for row in rows}) == 2
    original, copy = rows[0], rows[1]
    assert original['story'] == copy['story'] and original['stages'] == copy['stages']
    cast, copied = json.loads(original['cast_ids']), json.loads(copy['cast_ids'])
    assert len(cast) == len(copied) and not set(cast) & set(copied)


def test_a_settled_storyline_stays_by_its_outcome_then_goes_to_recall(client, social, clock, monkeypatch, provider):
    from companion.characters import require_current
    from companion.memory import vectors
    monkeypatch.setattr(storylines, 'START', (1, 1, 1, 1))
    monkeypatch.setattr(storylines, 'STORIES', (storylines.find_story('friend_new_job'),))
    reconcile(client)
    item = client.get('/api/life/storylines').json()[0]
    friend = item['cast'][0]['name']
    clock.advance(timedelta(days=30))
    reconcile(client)
    system = client.get('/api/context/preview').json()['system']
    section = system.split('## What is going on')[1].split('\n## ')[0]
    assert '- Settled on ' in section and friend in section
    assert 'keeps asking you' not in section and 'Still unfolding' not in section

    clock.advance(timedelta(days=40))
    reconcile(client)
    assert '## What is going on' not in client.get('/api/context/preview').json()['system']
    with client.app.state.database.connect(write=True) as connection:
        companion = require_current(connection)
        assert storylines.context_lines(connection, companion, clock.now()) == []
        stories = storylines.recall_items(connection, companion, clock.now())
        assert [story['id'] for story in stories] == [item['id']] and friend in stories[0]['text']
        owner = ('storyline', item['id'], stories[0]['text'])
        timeline_id = companion['active_timeline_id']
        assert owner in vectors.missing(connection, 'model', timeline_id, stories=stories)
        assert vectors.store(connection, 'model', [owner], [[1.0, 0.0]], '2026-12-14T12:00:00Z') == 1
        assert owner not in vectors.missing(connection, 'model', timeline_id, stories=stories)

    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    send(client, f'Did {friend} ever take that job?', 'client-story-recall')
    system = provider.requests[-1]['system']
    assert 'Something that happened in your life, settled on' in system and friend in system
