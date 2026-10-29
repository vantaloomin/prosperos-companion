"""Comments on feed posts (companion/life/post_comments.py): the user comments, whoever posted answers in the thread."""
from datetime import timedelta

import pytest
from conftest import life_reply, reconcile, set_life

from companion.life import post_comments, reading, social
from companion.providers.chat import Chunk


def feed(client, **params):
    response = client.get('/api/feed', params={'limit': 100, **params})
    assert response.status_code == 200, response.text
    return response.json()['posts']


def answering(text):
    """Life wording as usual; a comment's answer is `text`."""
    def respond(system, messages):
        if 'commented' in system or 'commented' in str(messages[-1]['content']):
            return [Chunk(text), Chunk('', 'stop')]
        return life_reply(system, messages)
    return respond


def comment(client, post_id, text, wait='true'):
    response = client.post(f'/api/feed/{post_id}/comments', params={'wait': wait}, json={'text': text})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def posts(client, life, clock):
    set_life(client, automatic_events=True)
    clock.advance(timedelta(days=1))
    reconcile(client)
    found = feed(client)
    assert found
    return found


def own_post(posts):
    return next(post for post in posts if post['author']['kind'] == 'companion')


def test_the_companion_answers_a_comment_on_their_post(client, posts, life):
    life.respond = answering('Mira: "Thank you! It was such a calm morning."')
    post = own_post(posts)
    shown = comment(client, post['id'], 'Love this one!')
    comments = shown['thread']['comments']
    assert [(item['author'], item['text']) for item in comments] == [
        ('user', 'Love this one!'), ('poster', 'Thank you! It was such a calm morning.')]
    assert comments[1]['name'] == 'Mira' and comments[1]['reply_to'] == comments[0]['id']
    assert shown['thread']['waiting'] is False
    # Written from their chat, told it is a comment under their own post and what the post said.
    asked = life.requests[-1]
    assert 'Love this one!' in asked['messages'][-1]['content'] and 'Mira' in asked['system']
    caption = (post['events'][0].get('mine') or post['events'][0])['caption']
    assert caption in asked['messages'][-1]['content']
    # The feed shows the thread too, and the post counts as read.
    again = next(item for item in feed(client) if item['id'] == post['id'])
    assert again['thread'] == shown['thread'] and again['read']


def test_a_second_comment_carries_the_thread_so_far(client, posts, life):
    life.respond = answering('Glad you like it.')
    post = own_post(posts)
    comment(client, post['id'], 'Love this one!')
    life.respond = answering('Every Sunday, yes.')
    shown = comment(client, post['id'], 'Do you go there often?')
    assert [item['text'] for item in shown['thread']['comments']] == [
        'Love this one!', 'Glad you like it.', 'Do you go there often?', 'Every Sunday, yes.']
    ask = life.requests[-1]['messages'][-1]['content']
    assert 'Earlier in the comments' in ask and 'Glad you like it.' in ask


def test_the_answer_shows_once_they_would_have_seen_it(client, posts, life, clock, monkeypatch):
    monkeypatch.setattr(reading, 'ACTIVE', True)
    life.respond = answering('Thanks!')
    post = own_post(posts)
    shown = comment(client, post['id'], 'So good')
    assert [item['author'] for item in shown['thread']['comments']] == ['user'] and shown['thread']['waiting']
    clock.advance(timedelta(minutes=max(post_comments.SEES[reading.NATURAL]) + 1))
    shown = client.get(f"/api/feed/{post['id']}").json()
    assert [item['text'] for item in shown['thread']['comments']] == ['So good', 'Thanks!']
    assert not shown['thread']['waiting']


def test_a_comment_without_a_usable_answer_stays_unanswered(client, posts, life):
    life.respond = answering('')
    post = own_post(posts)
    shown = comment(client, post['id'], 'Hello?')
    assert [item['author'] for item in shown['thread']['comments']] == ['user']
    assert shown['thread']['waiting'] is False


def test_a_friend_answers_on_their_own_post(client, life, clock, monkeypatch):
    monkeypatch.setattr(social, 'SHARE', {kind: 1 for kind in social.SHARE})
    set_life(client, automatic_events=True)
    for _ in range(3):
        clock.advance(timedelta(days=1))
        reconcile(client)
    friends = [post for post in feed(client) if post['kind'] == 'friend']
    if not friends:
        pytest.skip('No friend posted on this seed.')
    post = friends[0]
    life.respond = answering(f"{post['author']['name']}: Ha, you should come next time!")
    shown = comment(client, post['id'], 'Looks fun!')
    answer = shown['thread']['comments'][-1]
    assert answer['author'] == 'poster' and answer['name'] == post['author']['name']
    assert answer['text'] == 'Ha, you should come next time!'
    system = life.requests[-1]['system']
    assert post['author']['name'] in system and 'Looks fun!' in system and 'never claim history' in system


def test_no_comments_on_own_or_removed_posts(client, posts, life):
    mine = client.post('/api/feed/mine', json={'text': 'Sunny out'}).json()
    response = client.post(f"/api/feed/{mine['id']}/comments", json={'text': 'hi'})
    assert response.status_code == 409
    post = own_post(posts)
    life.respond = answering('Thanks!')
    comment(client, post['id'], 'Nice')
    client.post(f"/api/feed/{post['id']}/remove")
    response = client.post(f"/api/feed/{post['id']}/comments", json={'text': 'hi'})
    assert response.status_code == 409
    assert client.get(f"/api/feed/{post['id']}").json()['thread']['comments'] == []


def test_comments_without_a_model_wait_for_nothing(client, companion, clock):
    set_life(client, automatic_events=True)
    clock.advance(timedelta(days=1))
    reconcile(client)
    posts = feed(client)
    if not posts:
        pytest.skip('Nothing posted without a model on this seed.')
    shown = comment(client, posts[0]['id'], 'Nice')
    assert [item['author'] for item in shown['thread']['comments']] == ['user']
    assert shown['thread']['waiting'] is False
