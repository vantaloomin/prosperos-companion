"""Who in a companion's circle knows the user (companion/life/knows_you.py), on the web and the circle list."""
from datetime import timedelta

import pytest
from conftest import reconcile, set_life
from test_post_comments import answering, comment, feed

from companion.life import knows_you, social


def web(client):
    response = client.get('/api/life/web')
    assert response.status_code == 200, response.text
    return response.json()


def to_you(found, key):
    return next((link for link in found['links'] if {link['source'], link['target']} == {key, 'you'}), None)


def circle(client):
    response = client.get('/api/life/circle')
    assert response.status_code == 200, response.text
    return {person['id']: person for person in response.json() if not person.get('shared')}


def set_knows(client, person_id, how):
    response = client.put(f'/api/life/circle/{person_id}/knows-you', json={'how': how})
    assert response.status_code == 200, response.text
    return response.json()


def test_nobody_in_the_circle_knows_a_user_who_just_met_the_companion(client, companion):
    assert all(person['knows_you']['how'] == '' for person in circle(client).values())
    found = web(client)
    people = [node for node in found['nodes'] if node['kind'] == 'circle']
    assert people and not any(to_you(found, node['id']) for node in people)


def test_someone_the_companion_told_about_the_user_knows_of_them(client, companion, monkeypatch):
    monkeypatch.setattr(knows_you, 'HEARD_FROM', 0)
    people = circle(client)
    person = next(item for item in people.values() if item['knowing'] == 'both')
    tie = to_you(web(client), person['key'])
    assert tie['source'] == person['key'] and tie['kind'] == 'met'
    assert tie['label'] == 'Mira told them about you'
    assert people[person['id']]['knows_you'] == {'how': 'knows of you', 'why': 'Mira told them about you',
                                                  'set': False, 'key': person['key']}


def test_the_user_says_who_knows_them_and_can_hand_it_back(client, companion, monkeypatch):
    monkeypatch.setattr(knows_you, 'HEARD_FROM', 0)
    person = next(iter(circle(client).values()))
    assert set_knows(client, person['id'], '')['knows_you'] == {'how': '', 'why': '', 'set': True, 'key': person['key']}
    assert to_you(web(client), person['key']) is None
    set_knows(client, person['id'], 'knows you')
    tie = to_you(web(client), person['key'])
    assert tie['kind'] == 'you' and tie['label'] == 'knows you'
    assert set_knows(client, person['id'], None)['knows_you']['set'] is False
    bad = client.put(f"/api/life/circle/{person['id']}/knows-you", json={'how': 'best friends'})
    assert bad.status_code == 422


def test_a_friend_who_answered_the_users_comment_knows_them(client, life, clock, monkeypatch):
    monkeypatch.setattr(social, 'SHARE', {kind: 1 for kind in social.SHARE})
    set_life(client, automatic_events=True)
    for _ in range(3):
        clock.advance(timedelta(days=1))
        reconcile(client)
    friends = [post for post in feed(client) if post['kind'] == 'friend']
    if not friends:
        pytest.skip('No friend posted on this seed.')
    post = friends[0]
    person = next(item for item in circle(client).values() if item['name'] == post['author']['name'])
    life.respond = answering(f"{post['author']['name']}: Thanks, love!")
    comment(client, post['id'], 'Looks fun!')
    tie = to_you(web(client), person['key'])
    assert tie['kind'] == 'you' and tie['label'] == 'talked on their post'
