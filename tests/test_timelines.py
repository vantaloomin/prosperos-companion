"""Alternative timelines: historical edits, switching and freezing (PRD C4, T7, M6, M12)."""
from datetime import timedelta

from conftest import reconcile, send, set_life

from companion import timelines
from companion.clock import parse


def fork(client, message_id, text='Actually, I went to the coast.', **extra):
    response = client.post('/api/timelines', json={'message_id': message_id, 'text': text, **extra})
    assert response.status_code == 200, response.text
    return response.json()


def activate(client, timeline_id):
    response = client.post(f'/api/timelines/{timeline_id}/activate')
    assert response.status_code == 200, response.text
    return response.json()


def texts(client):
    return [message['text'] for message in client.get('/api/conversation').json()['messages']]


def conversation(client, clock, lines):
    sent = []
    for index, line in enumerate(lines):
        sent.append(send(client, line, f'client-{index:04d}')['message'])
        clock.advance(timedelta(minutes=5))
    return sent


def remember(client, **fields):
    response = client.post('/api/memories', json={'layer': 'shared_experience', 'subject': 'Moment', **fields})
    assert response.status_code == 200, response.text
    return response.json()


def test_editing_an_earlier_message_creates_an_inactive_timeline(client, connected, clock):
    first, second, _third = conversation(client, clock, ['Morning!', 'I went hiking today.', 'It rained.'])
    created = fork(client, second['id'], label='The coast')
    assert created['status'] == 'frozen' and not created['active'] and created['label'] == 'The coast'
    assert created['draft'] == 'Actually, I went to the coast.'
    assert created['forked_at'] == second['created_at'] and created['messages'] == 2
    # The live relationship is untouched until the user chooses the new timeline.
    assert texts(client) == ['Morning!', 'Hello again.', 'I went hiking today.', 'Hello again.', 'It rained.',
                             'Hello again.']
    listing = client.get('/api/timelines').json()
    assert [item['label'] for item in listing['timelines']] == ['Original', 'The coast']
    assert listing['active_id'] == listing['timelines'][0]['id']

    switched = activate(client, created['id'])
    assert switched['active_id'] == created['id']
    original = switched['timelines'][0]
    assert original['status'] == 'frozen' and original['frozen_at'] is not None
    assert texts(client) == ['Morning!', 'Hello again.']
    copied = client.get('/api/conversation').json()['messages'][0]
    assert copied['id'] != first['id'] and copied['origin_id'] == first['id']

    send(client, 'Actually, I went to the coast.', 'client-edit')
    assert texts(client)[-2:] == ['Actually, I went to the coast.', 'Hello again.']
    assert client.get('/api/timelines').json()['timelines'][1]['draft'] is None

    # Switching back finds the original exactly as it was.
    activate(client, original['id'])
    assert texts(client)[-2:] == ['It rained.', 'Hello again.']


def test_only_your_own_messages_can_be_edited(client, connected, clock):
    sent = send(client, 'Hello there', 'client-0001')
    response = client.post('/api/timelines', json={'message_id': sent['reply']['id'], 'text': 'Changed'})
    assert response.status_code == 422


def test_a_reply_finishing_after_a_switch_is_withheld(app, client, connected, clock, provider):
    first = send(client, 'Hello', 'client-0001')['message']
    later = send(client, 'Tell me about your day', 'client-0002')['message']
    created = fork(client, later['id'])
    provider.before_finish = lambda: timelines.activate(app.state.database, created['id'])
    reply = client.post(f"/api/conversation/messages/{later['id']}/alternatives").json()['reply']
    assert reply['status'] == 'withheld' and not reply['active']
    assert client.get('/api/conversation').json()['messages'][0]['origin_id'] == first['id']


def test_switching_freezes_pending_events_and_late_work_cannot_commit(client, companion, clock):
    start = clock.now()
    proposal = {'idempotency_key': 'outing-0001', 'kind': 'ordinary', 'summary': 'Walked to the market',
                'starts_at': (start - timedelta(hours=3)).isoformat(), 'ends_at': (start - timedelta(hours=2)).isoformat()}
    pending = client.post('/api/events', json=proposal).json()
    message = send(client, 'Hi', 'client-0001')['message']
    created = fork(client, message['id'])
    activate(client, created['id'])
    history = client.get('/api/events?history=true').json()
    assert history == []  # The event belonged to the frozen timeline, not this one.
    original = client.get('/api/timelines').json()['timelines'][0]
    activate(client, original['id'])
    frozen = next(event for event in client.get('/api/events?history=true').json() if event['id'] == pending['id'])
    assert frozen['status'] == 'rejected' and 'frozen' in frozen['rejection']


def test_committed_history_before_the_edit_carries_over(client, companion, clock):
    early = {'idempotency_key': 'outing-early', 'kind': 'ordinary', 'summary': 'Visited the lighthouse',
             'starts_at': (clock.now() - timedelta(hours=3)).isoformat(),
             'ends_at': (clock.now() - timedelta(hours=2)).isoformat()}
    event = client.post('/api/events', json=early).json()
    assert client.post(f"/api/events/{event['id']}/commit").json()['status'] == 'committed'
    post = client.post('/api/feed/posts', json={'event_id': event['id']})
    assert post.status_code == 200, post.text
    clock.advance(timedelta(hours=1))
    message = send(client, 'Hi', 'client-0001')['message']
    clock.advance(timedelta(hours=3))
    late = {**early, 'idempotency_key': 'outing-late', 'summary': 'Bought a kite',
            'starts_at': (clock.now() - timedelta(hours=2)).isoformat(),
            'ends_at': (clock.now() - timedelta(hours=1)).isoformat()}
    later = client.post('/api/events', json=late).json()
    client.post(f"/api/events/{later['id']}/commit")
    created = fork(client, message['id'])
    activate(client, created['id'])
    carried = client.get('/api/events').json()
    assert [item['summary'] for item in carried] == ['Visited the lighthouse']
    assert carried[0]['id'] != event['id'] and carried[0]['timeline_id'] == created['id']
    posts = client.get('/api/feed').json()['posts']
    assert len(posts) == 1 and posts[0]['events'][0]['id'] == carried[0]['id']
    preview = client.get('/api/context/preview').json()['system']
    assert 'lighthouse' in preview and 'kite' not in preview


def test_relationship_memories_before_the_edit_carry_over_and_later_ones_do_not(client, connected, clock):
    first = send(client, 'We watched the meteor shower', 'client-0001')['message']
    remember(client, subject='Meteor shower', value='Watched the meteor shower together')
    clock.advance(timedelta(minutes=5))
    second = send(client, 'Then we argued about the map', 'client-0002')['message']
    clock.advance(timedelta(minutes=5))
    remember(client, subject='Map argument', value='Argued about the map')
    created = fork(client, second['id'])
    activate(client, created['id'])
    system = client.get('/api/context/preview').json()['system']
    assert 'meteor shower together' in system
    assert 'Argued about the map' not in system
    assert first['id'] in client.get('/api/conversation').json()['messages'][0]['origin_id']


def test_profile_sharing_across_timelines_is_a_visible_setting(client, connected, clock):
    first = send(client, 'Hello', 'client-0001')['message']
    created = fork(client, first['id'])
    remember(client, layer='user_fact', subject='Favourite tea', value='Oolong')
    activate(client, created['id'])
    assert client.get('/api/settings').json()['share_profile_across_timelines'] is True
    assert 'Oolong' in client.get('/api/context/preview').json()['system']
    before = client.get('/api/settings').json()['memory_revision']
    updated = client.put('/api/settings', json={'share_profile_across_timelines': False}).json()
    assert updated['memory_revision'] == before + 1
    assert 'Oolong' not in client.get('/api/context/preview').json()['system']


def test_excluding_a_memory_blocks_every_copy_of_its_source(client, connected, clock, provider):
    secret = send(client, 'My locker code is 4417', 'client-0001')['message']
    clock.advance(timedelta(minutes=5))
    later = send(client, 'Anyway, how are you?', 'client-0002')['message']
    memory = remember(client, layer='user_fact', subject='Locker code', value='4417',
                      source_message_ids=[secret['id']])
    created = fork(client, later['id'])
    activate(client, created['id'])
    assert '4417' in str(client.get('/api/context/preview').json()['messages'])
    client.post(f"/api/memories/{memory['id']}/exclude")
    preview = client.get('/api/context/preview').json()
    assert '4417' not in str(preview['messages']) and '4417' not in preview['system']


def test_deleting_a_source_message_redacts_its_copies(client, connected, clock):
    secret = send(client, 'My locker code is 4417', 'client-0001')['message']
    clock.advance(timedelta(minutes=5))
    later = send(client, 'Anyway', 'client-0002')['message']
    memory = remember(client, layer='user_fact', subject='Locker code', value='4417',
                      source_message_ids=[secret['id']])
    created = fork(client, later['id'])
    deleted = client.post(f"/api/memories/{memory['id']}/delete", json={'delete_sources': True})
    assert deleted.status_code == 200, deleted.text
    activate(client, created['id'])
    copy = client.get('/api/conversation').json()['messages'][0]
    assert copy['redacted'] and copy['text'] == ''


def test_declining_a_copy_declines_the_original(client, connected, clock):
    first = send(client, 'I live in Porto', 'client-0001')['message']
    clock.advance(timedelta(minutes=5))
    later = send(client, 'Anyway', 'client-0002')['message']
    created = fork(client, later['id'])
    activate(client, created['id'])
    copy = client.get('/api/conversation').json()['messages'][0]
    assert client.post(f"/api/conversation/messages/{copy['id']}/decline-memory").status_code == 200
    original = client.get('/api/timelines').json()['timelines'][0]
    activate(client, original['id'])
    response = client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Home', 'value': 'Porto',
                                                  'source_message_ids': [first['id']]})
    assert response.status_code == 409


def test_frozen_time_is_never_simulated(client, life, clock):
    set_life(client, automatic_events=True)
    message = send(client, 'Good morning', 'client-0001')['message']
    created = fork(client, message['id'])
    switched_at = clock.now()
    activate(client, created['id'])
    original = client.get('/api/timelines').json()['timelines'][0]
    clock.advance(timedelta(days=3))
    activate(client, original['id'])
    returned_at = clock.now()
    clock.advance(timedelta(days=1))
    run = reconcile(client)['run']
    assert run and run['results']
    for event in client.get('/api/events').json():
        assert not (switched_at < parse(event['starts_at']) < returned_at)
    entries = client.get('/api/today').json()
    assert entries  # Today still assembles on the returned timeline.


def test_the_circle_and_its_diary_carry_over(client, life, clock):
    send(client, 'Good morning', 'client-0001')
    clock.advance(timedelta(days=2))
    reconcile(client)
    original = client.get('/api/life/circle').json()
    friend = next(person for person in original if person['schedule'])
    diary = client.get(f"/api/life/circle/{friend['id']}/diary").json()
    assert diary
    later = send(client, 'Back again', 'client-0002')['message']
    created = fork(client, later['id'])
    activate(client, created['id'])
    copied = client.get('/api/life/circle').json()
    assert [person['name'] for person in copied] == [person['name'] for person in original]
    twin = next(person for person in copied if person['name'] == friend['name'])
    assert twin['id'] != friend['id']
    copied_diary = client.get(f"/api/life/circle/{twin['id']}/diary").json()
    assert {entry['subject'] for entry in copied_diary} == {twin['id']}
    assert [entry['entry'] for entry in copied_diary] == [entry['entry'] for entry in diary]


def test_memories_from_another_timeline_are_marked(client, connected, clock):
    first = send(client, 'Hello', 'client-0001')['message']
    clock.advance(timedelta(minutes=5))
    remember(client, subject='Kite day', value='Flew a kite together')
    remember(client, layer='user_fact', subject='Favourite tea', value='Oolong')
    created = fork(client, first['id'])
    activate(client, created['id'])
    marks = {memory['subject']: memory['in_timeline'] for memory in client.get('/api/memories').json()}
    assert marks == {'Kite day': False, 'Favourite tea': True}


def test_a_corrected_events_post_carries_over_showing_the_correction(client, companion, clock):
    early = {'idempotency_key': 'outing-early', 'kind': 'ordinary', 'summary': 'Visited the lighthouse',
             'starts_at': (clock.now() - timedelta(hours=3)).isoformat(),
             'ends_at': (clock.now() - timedelta(hours=2)).isoformat()}
    event = client.post('/api/events', json=early).json()
    client.post(f"/api/events/{event['id']}/commit")
    client.post('/api/feed/posts', json={'event_id': event['id']})
    client.post(f"/api/events/{event['id']}/correct", json={'summary': 'Visited the harbour'})
    clock.advance(timedelta(hours=1))
    message = send(client, 'Hi', 'client-0001')['message']
    activate(client, fork(client, message['id'])['id'])
    carried = client.get('/api/events').json()
    posts = client.get('/api/feed').json()['posts']
    assert [item['summary'] for item in carried] == ['Visited the harbour']
    assert len(posts) == 1 and posts[0]['events'][0]['id'] == carried[0]['id']
    assert posts[0]['events'][0]['summary'] == 'Visited the harbour'
