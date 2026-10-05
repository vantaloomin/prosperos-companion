"""Private feed and Today view (PRD F1, F2, F4, Today, C5)."""
import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from conftest import reconcile, set_life

from companion.errors import DomainError
from companion.life import feed as feed_module


def feed(client, **params):
    response = client.get('/api/feed', params=params)
    assert response.status_code == 200, response.text
    return response.json()


def commit_all(client):
    for event in client.get('/api/events?history=true').json():
        if event['status'] == 'proposed':
            client.post(f"/api/events/{event['id']}/commit")


def test_a_return_batch_makes_one_digest_that_waits_for_review(client, life, clock):
    clock.advance(timedelta(days=1))
    reconcile(client)
    assert feed(client)['posts'] == [] and feed(client)['unread'] == 0
    proposed = client.get('/api/events?history=true').json()
    client.post(f"/api/events/{proposed[0]['id']}/commit")
    client.post(f"/api/events/{proposed[1]['id']}/reject")
    page = feed(client)
    assert len(page['posts']) == 1 and page['unread'] == 1
    digest = page['posts'][0]
    assert digest['kind'] == 'digest' and [event['id'] for event in digest['events']] == [proposed[0]['id']]
    assert digest['events'][0]['caption'] == 'Lovely light today.'
    assert digest['image']['status'] == 'none'
    commit_all(client)
    assert len(feed(client)['posts'][0]['events']) == 2


def test_a_corrected_event_changes_its_post(client, life, clock):
    set_life(client, automatic_events=True)
    clock.advance(timedelta(days=1))
    reconcile(client)
    event = feed(client)['posts'][0]['events'][0]
    corrected = client.post(f"/api/events/{event['id']}/correct", json={'summary': 'Painted by the river'}).json()
    shown = feed(client)['posts'][0]['events'][0]
    assert shown['id'] == corrected['id'] and shown['summary'] == 'Painted by the river' and shown['revision'] == 2


def test_background_batches_post_each_event(app, client, life, clock):
    client.put('/api/settings', json={'background_activity': True})
    set_life(client, automatic_events=True)
    clock.advance(timedelta(hours=20))
    asyncio.run(app.state.life.reconcile('background'))
    posts = feed(client)['posts']
    assert len(posts) == 1 and posts[0]['kind'] == 'event'


def test_read_hide_remove_and_export(client, life, clock):
    set_life(client, automatic_events=True)
    clock.advance(timedelta(days=1))
    reconcile(client)
    clock.advance(timedelta(days=1))
    reconcile(client)
    posts = feed(client)['posts']
    assert len(posts) == 2 and posts[0]['occurs_at'] > posts[1]['occurs_at']
    assert client.post('/api/feed/read', json={'post_ids': [posts[0]['id']]}).json()['unread'] == 1
    assert client.post('/api/feed/read').json()['unread'] == 0
    client.post(f"/api/feed/{posts[0]['id']}/hide")
    assert [post['id'] for post in feed(client)['posts']] == [posts[1]['id']]
    assert len(feed(client, hidden=True)['posts']) == 2
    client.post(f"/api/feed/{posts[0]['id']}/unhide")
    removed = client.post(f"/api/feed/{posts[1]['id']}/remove").json()
    assert removed['status'] == 'removed' and removed['events'] == []
    assert client.post(f"/api/feed/{posts[1]['id']}/unhide").status_code == 409
    # The events stay part of the companion's life after their post is removed.
    assert len(client.get('/api/events').json()) == 6
    exported = client.get('/api/feed/export').json()
    assert exported['format'] == 'prospero-companion-feed' and len(exported['posts']) == 1


def test_pagination_is_finite_and_chronological(client, life, clock):
    set_life(client, automatic_events=True)
    for _ in range(3):
        clock.advance(timedelta(days=1))
        reconcile(client)
    first = feed(client, limit=2)
    assert len(first['posts']) == 2 and first['next_before']
    second = feed(client, limit=2, before=first['next_before'])
    assert len(second['posts']) == 1 and second['next_before'] is None


def test_reactions_and_discussing_a_post_in_chat(client, life, clock, provider):
    set_life(client, automatic_events=True)
    clock.advance(timedelta(days=1))
    reconcile(client)
    post = feed(client)['posts'][0]
    reacted = client.post(f"/api/feed/{post['id']}/reaction", json={'reaction': 'heart'}).json()
    assert reacted['reaction'] == 'heart' and reacted['read'] is True
    assert client.post(f"/api/feed/{post['id']}/reaction", json={'reaction': 'angry'}).status_code == 422
    result = client.post(f"/api/feed/{post['id']}/discuss", json={'text': 'That looks lovely!',
                                                                   'client_id': 'discuss-0001'})
    assert result.status_code == 200, result.text
    assert result.json()['reply']['status'] == 'complete'
    system = provider.requests[-1]['system']
    assert 'feed post the user is replying to' in system and post['events'][0]['summary'] in system


def test_image_hook_ignores_a_late_result(client, life, clock):
    set_life(client, automatic_events=True)
    clock.advance(timedelta(days=1))
    reconcile(client)
    post = feed(client)['posts'][0]
    database = client.app.state.database
    feed_module.set_image(database, post['id'], 'job-1', 'queued')
    feed_module.set_image(database, post['id'], 'job-2', 'queued')
    with pytest.raises(DomainError) as late:
        feed_module.set_image(database, post['id'], 'job-1', 'completed', ref='old.png')
    assert late.value.status == 409
    done = feed_module.set_image(database, post['id'], 'job-2', 'completed', ref='new.png')
    assert done['image'] == {**done['image'], 'status': 'completed', 'ref': 'new.png', 'job_id': 'job-2'}


def test_explicit_post_for_a_committed_event(client, companion, clock):
    event = client.post('/api/events', json={
        'idempotency_key': 'manual-0001', 'kind': 'ordinary', 'summary': 'Baked bread',
        'starts_at': (clock.now() - timedelta(hours=2)).isoformat(),
        'ends_at': (clock.now() - timedelta(hours=1)).isoformat()}).json()
    assert client.post('/api/feed/posts', json={'event_id': event['id']}).status_code == 409
    client.post(f"/api/events/{event['id']}/commit")
    post = client.post('/api/feed/posts', json={'event_id': event['id'], 'intro': 'Fresh out.'}).json()
    again = client.post('/api/feed/posts', json={'event_id': event['id']}).json()
    assert post['id'] == again['id'] and post['intro'] == 'Fresh out.'


def test_today_shows_routine_review_changes_and_availability(client, life, clock):
    clock.instant = datetime(2026, 10, 6, 10, 0, tzinfo=UTC)
    reconcile(client)
    view = client.get('/api/today').json()
    assert view['availability']['state'] == 'free' and view['routine']['current']['block']['key'] == 'morning'
    assert len(view['review']) == 2 and view['changes'] == [] and view['last_seen_at'] is None
    assert view['last_run']['status'] == 'completed' and view['limits']['catch_up_max_events'] == 3
    for event in view['review']:
        client.post(f"/api/events/{event['id']}/commit")
    seen = client.post('/api/today/seen').json()['last_seen_at']
    assert client.get('/api/today').json()['changes'] == []
    clock.instant = datetime(2026, 10, 6, 23, 30, tzinfo=UTC)  # 00:30 in Lisbon
    view = client.get('/api/today').json()
    assert view['availability']['state'] == 'asleep' and view['last_seen_at'] == seen
    clock.instant = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)  # clock moved backward
    assert client.post('/api/today/seen').json()['last_seen_at'] == seen


def test_discussing_a_post_can_return_before_the_reply_finishes(client, life, clock, provider):
    set_life(client, automatic_events=True)
    clock.advance(timedelta(days=1))
    reconcile(client)
    post = feed(client)['posts'][0]
    result = client.post(f"/api/feed/{post['id']}/discuss?wait=false", json={'text': 'Tell me more!',
                                                                              'client_id': 'discuss-0002'})
    assert result.status_code == 200, result.text
    reply = result.json()['reply']
    events = client.get(f"/api/conversation/replies/{reply['id']}/events").text
    assert '"status": "complete"' in events
    assert 'feed post the user is replying to' in provider.requests[-1]['system']
