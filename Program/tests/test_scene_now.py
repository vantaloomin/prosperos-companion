"""The scene keeps up (Hit List #100): where an in-person meetup is now, and what they have on, from the chat."""
import json
from datetime import timedelta

import pytest
from conftest import send, set_life

from companion.life import body, composer, onward, outings, scene_now
from companion.providers.chat import Chunk
from companion.world import catalog

EVENINGS = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00', 'days': [0, 1, 2, 3, 4]},
            {'key': 'evening', 'label': 'Evening', 'kind': 'leisure', 'start': '17:00', 'end': '23:00'},
            {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]
SETT = ('sett', 'he', 'him', 'his')
# Lines that only talk about going somewhere: plans, questions, wishes, the past, negations, looks and spots inside.
TALK = [
    "*we could walk to the riverwalk after this*", "\"Should we head to yours after?\"", "*I wonder if we should go to Navy Pier*",
    "*let's walk to the river later*", "\"Want to go to the Art Institute tomorrow?\"", "*maybe we head to my place after dessert*",
    "*I don't want to go to the pier tonight*", "*we never made it to Millennium Park last time*",
    "*we walked to the riverwalk last week*", "*remember when we went to Wrigley Field?*",
    "*he's thinking of taking the bus to Wicker Park someday*", "*how about we go to yours?*",
    "*if it stops raining we could walk to the lake*", "*we should catch the train to Evanston one day*",
    "\"Do you want to get on the bus or walk?\"", "*she suggests we head over to the bar on the corner*",
    "*I'd rather not go to the river*", "*once we finish here, we can head to Grant Park*",
    "*we used to walk to the Bean every Sunday*", "*I'm not going to your place tonight*", "*let us walk to the pier tomorrow*",
    "*he looks back at the water*", "*she glances over at the bar*", "*I point to the Water Tower across the street*",
    "*he tilts his head back to look at the sky*", "*we sit at the bar and talk*", "*she reaches over and squeezes my hand*",
    "*we walk over to the bench by the window*", "*I lean back against the wall*", "*he walks to the counter to order*",
    "\"Next time we'll take a cab to the theater.\"", "*we're about to head to the river*", "*I dream of going to Paris with you*",
    "*he wants to go to the Field Museum on Saturday*", "*we talk about going to the beach next summer*",
    "*I'd never walk to Pilsen at this hour*", "*she offers to drive to her place but I shake my head*",
    "*we plan to get the train to Hyde Park in the morning*", "*the walk to the river was nice the other day*",
    "*would you walk with me to the lake sometime?*",
]


def chicago():
    data = catalog.city('chicago')
    start = next(place for place in data['places'] if place['name'] == 'The Berghoff')
    return data, {'id': start['id'], 'name': start['name'], 'neighborhood': start['neighborhood']}


def lines(*texts, role='user'):
    return [{'id': str(index), 'role': role, 'text': text, 'created_at': f'2026-11-10T19:{index:02d}:00+00:00'}
            for index, text in enumerate(texts)]


def test_the_phrase_bank_holds_a_hundred_of_each_kind():
    found = json.loads((catalog.DATA / 'scene_moves.json').read_text(encoding='utf-8'))
    for kind in ('moves', 'arrivals', 'put_on', 'take_off'):
        assert len(found[kind]) >= 100 and len(set(found[kind])) == len(found[kind])
        assert all(text == text.lower().strip() for text in found[kind])


def test_moves_arrivals_rides_and_homes():
    data, start = chicago()
    read = lambda *texts, role='user': scene_now.read(lines(*texts, role=role), data, start, SETT)['move']  # noqa: E731
    river = read('*we pay and walk outside, then head down to the riverwalk*')
    assert river['kind'] == 'place' and river['item']['name'] == 'Chicago Riverwalk'
    assert read('*we ride back to my apartment*')['kind'] == 'yours'
    assert read('*he takes your hand and walks you back to his place*', role='companion')['kind'] == 'theirs'
    assert read('*we hop on the bus*')['label'] == 'on the bus'
    assert read('*we step outside*')['label'] == 'outside The Berghoff'
    assert read('*we arrive at a tiny bakery*')['label'] == 'outside a tiny bakery'
    assert read('*we stroll toward the old lighthouse*')['label'] == 'on the way to the old lighthouse'
    # Once the talk has gone on past it, they are there.
    there = read('*we stroll toward the old lighthouse*', 'This is lovely.', 'It is.')
    assert there['kind'] == 'there' and there['label'] == 'at the old lighthouse'
    # Somewhere the map knows but across town is on the way, not there.
    far = next(place for place in data['places'] if place['name'] == 'Wrigley Field')
    assert read(f"*we walk to {far['name']}*")['kind'] == 'way'
    # The last move wins.
    assert read('*we walk to the bus stop and ride back to my apartment, then we flop onto my couch*')['kind'] == 'yours'


def test_talk_about_going_somewhere_is_no_move():
    data, start = chicago()
    for text in TALK:
        for role in ('user', 'companion'):
            assert scene_now.read(lines(text, role=role), data, start, SETT)['move'] is None, text
    assert scene_now.read(lines(*TALK), data, start, SETT)['move'] is None


def test_clothes_put_on_and_taken_off():
    data, start = chicago()
    worn = scene_now.read(lines('*I take off my jacket and put it around your shoulders*'), data, start, SETT)['wearing']
    assert worn['companion']['on'] == [{'item': 'jacket', 'owner': 'user', 'since': '2026-11-10T19:00:00+00:00'}]
    assert worn['user']['off'] == ['jacket']
    worn = scene_now.read(lines('Sett shrugs off his scarf and loops it around her neck. "There."',
                                '*He kicks his boots off by the door.*', role='companion'), data, start, SETT)['wearing']
    assert worn['user']['on'][0]['item'] == 'scarf' and worn['user']['on'][0]['owner'] == 'companion'
    assert worn['companion']['off'] == ['scarf', 'boots']
    # Handing it back; and adjusting their own scarf, or a coat off the back of a chair, changes nothing.
    worn = scene_now.read(lines('*I put my jacket around your shoulders*', '*hands back your jacket*'), data, start,
                          SETT)['wearing']
    assert worn['companion']['on'] == []
    still = scene_now.read(lines('*pulls the scarf up over his chin and shrugs the coat off the back of the chair*',
                                 role='companion'), data, start, SETT)['wearing']
    assert still == {'companion': {'on': [], 'off': []}, 'user': {'on': [], 'off': []}}
    text = ' '.join(line for _key, line in scene_now.wearing_lines({'id': 'o'}, {'wearing': worn}, 'UTC'))
    assert text == ''
    found = {'wearing': scene_now.read(lines('*I take off my jacket and put it around your shoulders*'), data, start,
                                       SETT)['wearing']}
    text = ' '.join(line for _key, line in scene_now.wearing_lines({'id': 'o'}, found, 'UTC'))
    assert "wearing the user's jacket since 19:00 (not the user)" in text
    assert 'took off their jacket (you are wearing it now)' in text
    assert scene_now.wearing_hint(found) == 'A borrowed jacket on.'


def test_story_mode_follows_its_own_lines_since_the_last_place_picked():
    data, start = chicago()
    place = next(item for item in data['places'] if item['id'] == start['id'])
    rows = [{'id': 's1', 'role': 'scene', 'text': 'You arrive.', 'created_at': '1'},
            {'id': 's2', 'role': 'user', 'text': 'I head down to the riverwalk.', 'created_at': '2'},
            {'id': 's3', 'role': 'narrator', 'text': 'You walk along the water.', 'created_at': '3'}]
    assert scene_now.story_place(data, place, rows)['name'] == 'Chicago Riverwalk'
    assert scene_now.story_place(data, place, [*rows, {'id': 's4', 'role': 'scene', 'text': 'You arrive.', 'created_at': '4'}]) is place


# --- In the app ----------------------------------------------------------------------------------------------------

@pytest.fixture
def mira(client, monkeypatch, provider):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(composer, 'PLAN_SHARE', 0)
    monkeypatch.setattr(composer, 'THREAD_SHARE', 0)
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC', 'schedule': EVENINGS,
                                                    'home_city': 'Baltimore', 'interests': ['seafood', 'jazz']})
    assert response.status_code == 200, response.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    set_life(client, automatic_events=True, phrase_with_model=False, catch_up_max_events=6,
             catch_up_lookback_hours=168, onward_realism=0)
    return response.json()


def dinner_tonight(client, provider, key):
    provider.replies.append([Chunk('Yes!'), Chunk('', 'stop')])
    send(client, 'Dinner tonight?', key)
    [outing] = client.get('/api/life/outings').json()['outings']
    return outing


def neighbour(outing):
    """A place the map knows a short walk from the restaurant."""
    data = catalog.city('baltimore')
    hood = next(item['neighborhood'] for item in data['places'] if item['id'] == outing['place']['id'])
    return next(item for item in data['places'] if item['neighborhood'] == hood and item['id'] != outing['place']['id']
                and item['kind'] in ('park', 'landmark', 'bar', 'cafe') and len(item['name']) >= 6)


def preview(client):
    return client.get('/api/context/preview').json()['prompt']


def where(client):
    return client.get('/api/life/where').json()


def test_walking_somewhere_in_the_chat_moves_the_scene_and_back_at_undoes_it(client, mira, provider, clock):
    outing = dinner_tonight(client, provider, 'scene-0001')
    next_door = neighbour(outing)
    clock.advance(timedelta(hours=7, minutes=30))  # 19:30, at dinner.
    assert where(client)['text'] == f"Together at {outing['place']['name']}"
    provider.replies.append([Chunk('*laughs and takes your arm*'), Chunk('', 'stop')])
    send(client, f"*we pay and walk over to {next_door['name']}*", 'scene-0002')
    found = where(client)
    assert found['text'] == f"Together at {next_door['name']}"
    assert found['outing']['scene'] == {'back': True, 'to': outing['place']['name'], 'kind': 'place'}
    text = preview(client)
    assert f"at {next_door['name']}" in text.split('Right now you are out with the user, in person:')[1][:200]
    assert f"Right now you are: with the user, at {next_door['name']} (since 19:30, after {outing['place']['name']})" \
        in text
    # Back to the restaurant, for two minutes after.
    back = client.post(f"/api/life/outings/{outing['id']}/scene-back")
    assert back.status_code == 200, back.text
    assert where(client)['text'] == f"Together at {outing['place']['name']}"
    assert client.post(f"/api/life/outings/{outing['id']}/scene-back").status_code == 409
    # A later move still counts; the undo runs out after two minutes.
    clock.advance(timedelta(minutes=1))
    provider.replies.append([Chunk('Sure.'), Chunk('', 'stop')])
    send(client, '*we hop on the bus*', 'scene-0003')
    assert where(client)['text'] == 'On the bus'
    clock.advance(timedelta(minutes=3))
    assert where(client)['outing']['scene']['back'] is False
    assert client.post(f"/api/life/outings/{outing['id']}/scene-back").status_code == 409
    assert 'Right now you and the user are on the bus, together in person' in preview(client)
    # When the meetup ends, everything goes back to normal.
    clock.advance(timedelta(hours=3))
    assert where(client)['state'] == 'apart' and 'on the bus' not in preview(client)


def test_their_own_words_move_it_and_an_edit_takes_it_back(client, mira, provider, clock):
    outing = dinner_tonight(client, provider, 'scene-0004')
    clock.advance(timedelta(hours=7, minutes=30))
    provider.replies.append([Chunk('*takes your hand and we head back to my place*'), Chunk('', 'stop')])
    sent = send(client, 'Shall we go?', 'scene-0005')
    assert where(client)['text'] == "At Mira's place"
    assert 'Right now the user is over at your place, in person' in preview(client)
    reply = sent['reply']
    edited = client.post(f"/api/conversation/messages/{reply['id']}/edit",
                         json={'text': '*takes your hand*', 'expected_text': reply['text']})
    assert edited.status_code == 200, edited.text
    assert where(client)['text'] == f"Together at {outing['place']['name']}"


def test_a_jacket_round_their_shoulders_reaches_the_notes(client, mira, provider, clock):
    dinner_tonight(client, provider, 'scene-0006')
    clock.advance(timedelta(hours=7, minutes=30))
    provider.replies.append([Chunk('*smiles*'), Chunk('', 'stop')])
    send(client, '*I take off my jacket and put it around your shoulders*', 'scene-0007')
    text = preview(client)
    assert "Your clothes since you met up, on top of today's outfit: wearing the user's jacket since 19:30" in text
    assert "The user's clothes since you met up: took off their jacket (you are wearing it now)." in text


def test_the_app_s_own_move_wins_when_it_fires(client, mira, provider, clock, monkeypatch):
    monkeypatch.setattr(onward, 'ACTIVE', True)
    monkeypatch.setattr(onward, 'CHANCE', (0.0, 1.0, 1.0, 1.0))
    set_life(client, onward_realism=2)
    outing = dinner_tonight(client, provider, 'scene-0008')
    with client.app.state.database.connect() as connection:
        stop = outings.get(connection, outing['id'])['onward']
    clock.advance(timedelta(hours=7, minutes=30))
    provider.replies.append([Chunk('Okay.'), Chunk('', 'stop')])
    send(client, '*we step outside*', 'scene-0009')
    assert where(client)['text'] == f"Outside {outing['place']['name']}"
    clock.advance(timedelta(hours=1, minutes=31))  # 21:01: Second location moved them on.
    assert where(client)['text'] == f"Together at {stop['place']['name']}"
