"""Story mode: a narrator for the user's own story around the cities, apart from the companion (companion/story.py)."""
from datetime import timedelta

from conftest import Chunk, send
from test_drafting import connect
from test_social_circle import make

from companion import story


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def say(client, text, client_id):
    return ok(client.post('/api/story/messages', json={'text': text, 'client_id': client_id}))


def busy_place(client, clock):
    """A Baltimore place with someone there now, moving the clock on by hours until there is one."""
    for _hour in range(48):
        with client.app.state.database.connect() as connection:
            data = story.city_data(connection, 'baltimore')
            moment = story.local_moment(data, clock.now())
            for place in data['places']:
                if people := story.present(connection, data, place['id'], moment):
                    return place, people
        clock.instant = clock.now() + timedelta(hours=1)
    raise AssertionError('Nobody is anywhere in Baltimore for two days.')


def test_the_story_starts_in_the_companions_city_and_needs_a_model(client, clock):
    make(client, 'Warm and curious.')
    opened = ok(client.get('/api/story'))
    assert opened['ready'] is False and opened['messages'] == []
    scene = opened['scene']
    assert scene['city']['name'] == 'Baltimore' and scene['place']['kind'] == 'cafe'
    assert scene['local_time'] and any(place['id'] == scene['place']['id'] for place in scene['places'])

    refused = client.post('/api/story/messages', json={'text': 'I look around.', 'client_id': 'story-0001'})
    assert refused.status_code == 409 and refused.json()['code'] == 'no_connection'
    # The message is kept, and is answered when it is sent again with a model connected.
    connect(client)
    sent = say(client, 'I look around.', 'story-0001')
    assert sent['reply']['role'] == 'narrator' and sent['reply']['status'] == 'complete'
    assert [message['role'] for message in ok(client.get('/api/story'))['messages']] == ['user', 'narrator']
    assert ok(client.get('/api/story'))['ready'] is True


def test_the_narrator_is_given_the_scene_and_the_companion_never_sees_the_story(client, clock, provider):
    make(client, 'Warm and curious.')
    connect(client)
    place, people = busy_place(client, clock)
    moved = ok(client.put('/api/story/scene', json={'city_id': 'baltimore', 'place_id': place['id']}))
    assert moved['scene']['place']['id'] == place['id'] and moved['messages'][-1]['role'] == 'scene'
    # The screen says who is around without names the user has not been given.
    around = moved['scene']['around']
    assert len(around) == len(people) and all(person['sheet']['full'] not in ' '.join(around) for person in people)

    provider.replies = [[Chunk('The door chimes behind you.'), Chunk('', 'stop')]]
    say(client, 'I order a coffee and the secret password is plum.', 'story-0001')
    request = provider.requests[-1]
    assert 'You are the narrator of an open-ended story' in request['system']
    assert f"Place: {place['name']}" in request['system'] and 'Weather:' in request['system']
    assert all(person['sheet']['full'] in request['system'] for person in people)
    assert request['messages'][0]['content'].startswith('[You arrive at')
    assert 'secret password is plum' in request['messages'][-1]['content']

    send(client, 'Hi Mira!', 'client-0001')
    chat = provider.requests[-1]
    assert 'plum' not in chat['system'] and all('plum' not in message['content'] for message in chat['messages'])
    assert 'narrator' not in chat['system']


def test_moving_to_another_city_and_unknown_places(client, clock):
    make(client, 'Warm and curious.')
    moved = ok(client.put('/api/story/scene', json={'city_id': 'new-york'}))
    assert moved['scene']['city']['name'] == 'New York' and moved['messages'][-1]['text'].endswith('New York.')
    # Choosing where the story already is adds nothing.
    again = ok(client.put('/api/story/scene', json={'city_id': 'new-york', 'place_id': moved['scene']['place']['id']}))
    assert len(again['messages']) == 1
    assert client.put('/api/story/scene', json={'city_id': 'new-york', 'place_id': 'nowhere'}).status_code == 404
    assert client.put('/api/story/scene', json={'city_id': 'atlantis'}).status_code == 404


def test_the_narrator_stays_in_the_story_unless_the_user_steps_out(client, clock, provider):
    connect(client)
    provider.replies = [[Chunk('As an AI language model, I cannot taste coffee. '), Chunk('The coffee is bitter.'),
                         Chunk('', 'stop')]]
    first = say(client, 'I taste the coffee.', 'story-0001')
    assert first['reply']['text'] == 'The coffee is bitter.'
    # Sending the same message again returns the same reply, without asking the model twice.
    count = len(provider.requests)
    assert say(client, 'I taste the coffee.', 'story-0001')['reply']['id'] == first['reply']['id']
    assert len(provider.requests) == count

    provider.replies = [[Chunk("I'm an AI language model writing the narrator."), Chunk('', 'stop')]]
    honest = say(client, 'OOC: what are you?', 'story-0002')
    assert 'AI language model' in honest['reply']['text']
    assert 'out of character' in provider.requests[-1]['system']


def test_a_failed_reply_can_be_told_again_and_a_new_story_started(client, clock, provider):
    connect(client)
    provider.replies = [[Chunk('', 'stop')]]
    failed = say(client, 'I wave at the barista.', 'story-0001')
    assert failed['reply']['status'] == 'failed' and failed['reply']['error']
    provider.replies = [[Chunk('The barista waves back.'), Chunk('', 'stop')]]
    retold = ok(client.post('/api/story/retry'))
    assert retold['reply']['text'] == 'The barista waves back.'
    roles = [(message['role'], message['status']) for message in ok(client.get('/api/story'))['messages']]
    assert roles == [('user', 'complete'), ('narrator', 'complete')]

    cleared = ok(client.delete('/api/story'))
    assert cleared['messages'] == [] and cleared['scene']['place']
    assert client.post('/api/story/retry').status_code == 409
