"""Storylines unfold over days in the companion's and the circle's lives, seeded, at the chosen drama level."""
import json
import re
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
    system = client.get('/api/context/preview').json()['prompt']
    assert "What is going on in your life and your people's lives" in system
    section = system.split('## What is going on')[1].split('\n## ')[0]
    # Mira is the companion; a relative's random name can contain it ("Miranda"), so match the whole word.
    assert 'Still unfolding' in section and not re.search(r'\bMira\b', section)
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
    assert item['beats'][0]['text'] not in client.get('/api/context/preview').json()['prompt']


def test_removing_someone_ends_their_storylines(client, social, monkeypatch):
    monkeypatch.setattr(storylines, 'START', (1, 1, 1, 1))
    monkeypatch.setattr(storylines, 'STORIES', tuple(story for story in storylines.STORIES if story.cast == 'friend'))
    reconcile(client)
    item = client.get('/api/life/storylines').json()[0]
    client.post(f"/api/life/circle/{item['cast'][0]['id']}/remove")
    reconcile(client)
    assert all(row['status'] == 'ended' for row in stored(client) if row['id'] == item['id'])


def test_someone_leaving_after_a_storyline_settled_keeps_it(client, social, clock, monkeypatch):
    monkeypatch.setattr(storylines, 'START', (1, 1, 1, 1))
    monkeypatch.setattr(storylines, 'STORIES', (storylines.find_story('friend_new_job'),))
    reconcile(client)
    item = client.get('/api/life/storylines').json()[0]
    clock.advance(timedelta(days=30))
    reconcile(client)
    client.post(f"/api/life/circle/{item['cast'][0]['id']}/remove")
    reconcile(client)
    assert [row['status'] for row in stored(client) if row['id'] == item['id']] == ['running']


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
    system = client.get('/api/context/preview').json()['prompt']
    section = system.split('## What is going on')[1].split('\n## ')[0]
    assert '- Settled on ' in section and friend in section
    assert 'keeps asking you' not in section and 'Still unfolding' not in section

    clock.advance(timedelta(days=40))
    reconcile(client)
    # A life chapter may share the section by now, so look for the storyline's own line.
    assert '- Settled on ' not in client.get('/api/context/preview').json()['prompt']
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
    system = provider.requests[-1]['prompt']
    assert 'Something that happened in your life, settled on' in system and friend in system


def test_template_lines_use_the_companions_own_pronouns_when_known():
    row = {'cast_ids': '[]'}
    she = {'name': 'Mira', 'identity': 'She is a nurse; her friends call her Mir.'}
    unknown = {'name': 'Sam', 'identity': 'A nurse.'}
    text = "{name} heard they are being considered for a promotion."
    assert storylines.fill(text, row, {}, she) == 'Mira heard she is being considered for a promotion.'
    assert storylines.fill(text, row, {}, unknown) == 'Sam heard they are being considered for a promotion.'
    kiss = '{name} got drunk and kissed {a}, their best friend.'
    assert storylines.fill(kiss, {'cast_ids': '["p"]'}, {'p': {'name': 'Jo', 'role': 'friend'}}, she) == \
        'Mira got drunk and kissed Jo, her best friend.'
    # A "they" about someone else stays.
    assert storylines.fill('{a} told {name} they are quitting.', {'cast_ids': '["p"]'},
                           {'p': {'name': 'Jo', 'role': 'friend'}}, she) == 'Jo told Mira they are quitting.'
    assert storylines.fill(kiss, {'cast_ids': '["p"]'}, {'p': {'name': 'Jo', 'role': 'friend'}}, she, you=True) == \
        'You got drunk and kissed Jo, your best friend.'



def test_a_drunk_kiss_never_comes_to_someone_seeing_someone():
    # The drunk kiss ignored a partner of six months (v0.13 run). With a partner in their circle it never rolls.
    people = [{'id': 'bf', 'role': 'close friend', 'details': '{}'}, {'id': 'gf', 'role': 'girlfriend', 'details': '{}'},
              {'id': 'co', 'role': 'coworker', 'details': '{}'}]
    single = storylines.find_story('drunk_kiss')
    assert storylines.casts(single, people, {}) == []
    assert storylines.casts(single, [people[0], people[2]], {}) == [('bf',)]
    for role in ('wife', 'fiancé', 'partner'):
        assert storylines.casts(single, [people[0], {**people[1], 'role': role}], {}) == []


def test_a_city_of_another_era_has_no_phones_or_internet_in_its_storylines():
    row = {'cast_ids': json.dumps(['p1'])}
    names = {'p1': {'name': 'Eunice', 'role': 'friend'}}
    beat_text = storylines.find_story('friend_breakup').stages[0][0].text
    modern = storylines.fill(beat_text, row, names, {'name': 'Wren', 'home_city': 'baltimore'})
    camelot = storylines.fill(beat_text, row, names, {'name': 'Wren', 'home_city': 'camelot'})
    assert 'on the phone' in modern
    assert camelot == 'Eunice went through a breakup, and Wren spent the evening sitting up with them.'
    for story in storylines.STORIES:
        for stage in story.stages:
            for found in stage:
                for said in (found.text, found.share):
                    period = storylines.fill(said, row, names, {'name': 'Wren', 'home_city': 'camelot'})
                    assert not re.search(r'\b(phone|online|texted|internet|messaged)\b', period), period


def test_each_beat_has_its_own_time_of_day(monkeypatch):
    """Tester, 2026-10-31: Sarek's and Spock's storylines both landed at 13:13. Beats get seeded times in waking hours."""
    from datetime import time
    monkeypatch.setattr(storylines, 'BEAT_HOURS', (time(8, 30), time(21, 0)))
    times = {storylines.beat_time(f'story-{number}', 0) for number in range(200)}
    assert len(times) > 100 and min(times) >= '08:30' and max(times) <= '21:00'
    assert storylines.beat_time('story-1', 0) == storylines.beat_time('story-1', 0)


def test_a_beat_today_waits_for_its_time(client, social, clock, monkeypatch):
    from datetime import time
    monkeypatch.setattr(storylines, 'BEAT_HOURS', (time(8, 30), time(21, 0)))
    monkeypatch.setattr(storylines, 'START', (1, 1, 1, 1))
    clock.instant = clock.now().replace(hour=7, minute=0)
    reconcile(client)
    assert len(stored(client)) == 1 and client.get('/api/life/storylines').json() == []
    when = storylines.beat_time(stored(client)[0]['id'], 0)
    clock.instant = clock.now().replace(hour=int(when[:2]), minute=int(when[3:]))
    listed = client.get('/api/life/storylines').json()
    assert len(listed) == 1 and listed[0]['beats'][0]['time'] == when
    # The narrator (Just watching) tells it at that time, not at one time shared by everyone.
    from companion.characters import require_current
    from companion.life import narrator
    with client.app.state.database.connect() as connection:
        lines = narrator.companion_lines(connection, require_current(connection), clock.now())
    told = [line for line in lines if line['kind'] == 'story']
    assert told and all(line['at'][11:16] == when for line in told)
