"""The social side of the feed: the circle's posts, likes and comments, and the companion's own non-event posts."""
from datetime import UTC, date, datetime, timedelta

import pytest
from conftest import life_reply, reconcile, set_life

from companion.clock import zone
from companion.life import body, circle, composer, social


@pytest.fixture
def city(client, provider, monkeypatch):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'America/New_York',
                                                     'location': 'Fells Point, Baltimore', 'interests': ['Jazz']})
    assert response.status_code == 200, response.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    provider.respond = life_reply
    set_life(client, automatic_events=True)
    return response.json()


def feed(client, **params):
    response = client.get('/api/feed', params={'limit': 100, **params})
    assert response.status_code == 200, response.text
    return response.json()


def live_days(client, clock, days=4):
    for _ in range(days):
        clock.advance(timedelta(days=1))
        reconcile(client)


def test_friends_post_from_their_diary_and_people_react(client, city, clock, monkeypatch):
    # Seeds depend on the random timeline id, so the chances are raised to make the counts certain.
    monkeypatch.setattr(social, 'COMMENT_CHANCE', 1)
    monkeypatch.setattr(social, 'COMPANION_LIKES', 1)
    live_days(client, clock)
    posts = feed(client)['posts']
    friends = [post for post in posts if post['kind'] == 'friend']
    assert friends and all(post['author']['kind'] == 'person' and post['text'] and post['context'] for post in friends)
    assert any(post['source'] == 'life' and post['author']['name'] == 'Mira' for post in posts)
    reactions = [post['audience'] for post in posts]
    assert any(item['likes'] for item in reactions) and any(item['comments'] for item in reactions)
    assert all(len(item['comments']) <= social.MAX_COMMENTS for item in reactions)
    # The companion joins in on friends' posts, and nobody comments on their own.
    assert any('Mira' in post['audience']['likes'] for post in friends)
    assert all(comment['name'] != post['author']['name'] for post in friends for comment in post['audience']['comments'])
    # Reading again posts nothing new.
    assert [post['id'] for post in feed(client)['posts']] == [post['id'] for post in posts]


def test_the_feed_can_show_only_the_companion_or_only_the_circle(client, city, clock):
    live_days(client, clock)
    everyone = feed(client)['posts']
    mine, theirs = feed(client, source='companion')['posts'], feed(client, source='circle')['posts']
    assert mine and theirs and len(mine) + len(theirs) == len(everyone)
    assert all(post['author']['kind'] == 'companion' for post in mine)
    assert all(post['author']['kind'] == 'person' for post in theirs)


def test_comments_arrive_after_the_post(client, city, clock):
    live_days(client, clock)
    for post in feed(client)['posts']:
        assert all(post['occurs_at'] <= comment['at'] <= client.get('/api/today').json()['now']
                   for comment in post['audience']['comments'])


def test_renamed_and_removed_friends(client, city, clock):
    live_days(client, clock)
    post = next(post for post in feed(client)['posts'] if post['kind'] == 'friend')
    person = post['author']['id']
    client.patch(f'/api/life/circle/{person}', json={'name': 'Renamed'})
    shown = next(item for item in feed(client)['posts'] if item['id'] == post['id'])
    assert shown['author']['name'] == 'Renamed'
    client.post(f'/api/life/circle/{person}/remove')
    posts = feed(client)['posts']
    assert all(item['author']['id'] != person for item in posts)
    assert all(comment['name'] != 'Renamed' for item in posts for comment in item['audience']['comments'])


def test_read_react_hide_and_remove_a_social_post(client, city, clock):
    live_days(client, clock)
    page = feed(client)
    post = next(post for post in page['posts'] if post['source'] == 'social')
    assert client.get('/api/today').json()['feed_unread'] == page['unread'] > 0
    assert client.post('/api/feed/read', json={'post_ids': [post['id']]}).json()['unread'] == page['unread'] - 1
    assert client.post(f"/api/feed/{post['id']}/reaction", json={'reaction': 'heart'}).json()['reaction'] == 'heart'
    client.post(f"/api/feed/{post['id']}/hide")
    assert post['id'] not in [item['id'] for item in feed(client)['posts']]
    assert post['id'] in [item['id'] for item in feed(client, hidden=True)['posts']]
    removed = client.post(f"/api/feed/{post['id']}/remove").json()
    assert removed['status'] == 'removed' and removed['text'] == ''
    assert client.post(f"/api/feed/{post['id']}/unhide").status_code == 409
    exported = client.get('/api/feed/export').json()
    assert any(item['source'] == 'social' for item in exported['posts'])


def test_answering_a_question_replies_in_chat(client, city, clock, provider, monkeypatch):
    monkeypatch.setattr(social, 'QUESTION_CHANCE', 1)
    live_days(client, clock, 1)
    question = next(post for post in feed(client)['posts'] if post['kind'] == 'question')
    assert len(question['options']) == 2
    assert client.post(f"/api/feed/{question['id']}/answer", json={'option': 'Nope', 'client_id': 'answer-001'}
                       ).status_code == 422
    option = question['options'][0]
    response = client.post(f"/api/feed/{question['id']}/answer", json={'option': option, 'client_id': 'answer-002'})
    assert response.status_code == 200, response.text
    assert next(post for post in feed(client)['posts'] if post['id'] == question['id'])['answer'] == option
    system = provider.requests[-1]['system']
    assert question['text'] in system and f'The user picked: {option}.' in system


def test_a_friends_birthday_gets_a_shout_out(client, city, clock, monkeypatch):
    today = clock.now().astimezone(zone('America/New_York')).date() + timedelta(days=1)
    monkeypatch.setattr(circle, 'birthday', lambda _person_id: today.strftime('%m-%d'))
    reconcile(client)
    clock.instant = datetime.combine(today, datetime.min.time(), tzinfo=UTC) + timedelta(hours=23)
    shout_outs = [post for post in feed(client)['posts'] if post['kind'] == 'birthday']
    people = client.get('/api/life/circle').json()
    assert len(shout_outs) == len(people)
    assert all(any(person['name'] in post['text'] for person in people) for post in shout_outs)


def test_status_posts_fit_the_day_and_claim_nothing():
    rainy = {'weather': {'high_f': 60, 'rain': True}, 'body': None}
    assert all(social.status_text(f'seed-{n}', date(2026, 10, 7), rainy, {})[0] in
               (*social.STATUS['rain'], *social.STATUS['any']) for n in range(20))
    text, tone = social.status_text('seed', date(2026, 10, 7), {'weather': None, 'body': {'state': 'sick'}}, {})
    assert text in social.STATUS['sick'] and tone == 'sick'
    assert social.comment_pool('status', {'tone': 'sick'}, 'someone', False) == social.COMMENTS['sick']


def test_city_news_reads_naturally():
    today = date(2026, 10, 7)
    opening = {'kind': 'opening', 'name': 'Bloom Cafe', 'summary': '', 'starts': '2026-10-10'}
    assert social.change_text(opening, 'Fells Point', today) == \
        "Bloom Cafe is opening in Fells Point on Saturday 10 October. Who's coming with me?"
    assert social.change_text({**opening, 'starts': '2026-10-01'}, '', today) == \
        'Bloom Cafe just opened. Who wants to try it?'


def test_a_branch_keeps_the_social_posts_from_before_it_split_off(client, city, clock, monkeypatch):
    monkeypatch.setattr(social, 'QUESTION_CHANCE', 1)
    live_days(client, clock, 2)
    sent = client.post('/api/conversation/messages', json={'text': 'Hi', 'client_id': 'branch-0001'}).json()['message']
    before = [post for post in feed(client)['posts'] if post['source'] == 'social']
    # Friends can post the same words at the same moment, so a post is found again on the branch by its
    # kind, words and moment together: react to one whose key no other post shares.
    keys = [(post['kind'], post['text'], post['occurs_at']) for post in before]
    question = next(post for post in before if post['kind'] == 'question')
    reacted = next(post for post, key in zip(before, keys) if keys.count(key) == 1 and post is not question)
    client.post(f"/api/feed/{question['id']}/answer", json={'option': question['options'][1], 'client_id': 'branch-0002'})
    client.post(f"/api/feed/{reacted['id']}/reaction", json={'reaction': 'wow'})
    live_days(client, clock, 2)
    after = {(post['kind'], post['text'], post['occurs_at']) for post in feed(client)['posts']
             if post['source'] == 'social' and post['occurs_at'] > sent['created_at']}
    branch = client.post('/api/timelines', json={'message_id': sent['id'], 'text': 'Hello'}).json()
    client.post(f"/api/timelines/{branch['id']}/activate")
    copied = [post for post in feed(client)['posts'] if post['source'] == 'social']
    # Posts at the same moment are ordered by id, and the copies have new ids, so compare them sorted.
    assert sorted((post['kind'], post['text'], post['occurs_at']) for post in copied
                  if post['occurs_at'] <= sent['created_at']) \
        == sorted((post['kind'], post['text'], post['occurs_at']) for post in before)
    # What the parent posted after the split stays on the parent.
    assert after and not after & {(post['kind'], post['text'], post['occurs_at']) for post in copied
                                  if post['occurs_at'] > sent['created_at']}
    shown = {(post['kind'], post['text'], post['occurs_at']): post for post in copied}
    assert shown[(question['kind'], question['text'], question['occurs_at'])]['answer'] == question['options'][1]
    assert shown[(reacted['kind'], reacted['text'], reacted['occurs_at'])]['reaction'] == 'wow'
    # Reading again on the branch does not post the copied ones a second time.
    assert len([post for post in feed(client)['posts'] if post['source'] == 'social']) == len(copied)


def test_no_comment_repeats_on_a_post_or_the_posts_just_before(client, city, clock, monkeypatch):
    monkeypatch.setattr(social, 'COMMENT_CHANCE', 1)
    live_days(client, clock)
    posts = list(reversed(feed(client)['posts']))
    said = [[comment['text'] for comment in post['audience']['comments']] for post in posts]
    assert any(said)
    for index, lines in enumerate(said):
        assert len(lines) == len(set(lines))
        earlier = {line for before in said[max(0, index - social.NEARBY):index] for line in before}
        assert not earlier & set(lines)
    # A filter shows the same comments the full feed does.
    everyone = {post['id']: post['audience'] for post in posts}
    assert all(post['audience'] == everyone[post['id']] for post in feed(client, source='circle')['posts'])


def test_reacting_returns_the_post_as_the_feed_shows_it(client, city, clock):
    live_days(client, clock)
    for post in feed(client)['posts'][:4]:
        reacted = client.post(f"/api/feed/{post['id']}/reaction", json={'reaction': 'hug'}).json()
        assert reacted['author'] == post['author'] and reacted['audience'] == post['audience']


def test_an_interest_reads_naturally_mid_sentence():
    """A long run posted "Fell down a the history of medicine museum rabbit hole again."""
    assert social.interest_text('the History of Medicine museum') == 'History of Medicine museum'
    assert social.interest_text('Roller derby matches') == 'roller derby matches'
    assert social.interest_text('Baltimore Orioles games') == 'Baltimore Orioles games'
    assert social.interest_text('a good thriller') == 'good thriller'
