"""A picture a reply sent can be made again or taken out of the chat (tester ask, 2026-10-28)."""
import httpx
import pytest
from fastapi.testclient import TestClient

from companion.identity import CLIENT_HEADER
from companion.images import gifs
from companion.main import create_app
from companion.providers.vault import MemoryVault
from tests.test_chat_photos import ask, drain
from tests.test_images import FakeAdapter, local_comfy
from tests.test_memes import giphy_item


@pytest.fixture
def adapters():
    return {'comfyui': FakeAdapter(), 'codex': FakeAdapter(), 'hosted': FakeAdapter()}


@pytest.fixture
def client(tmp_path, clock, provider, adapters):
    app = create_app(tmp_path / 'workspace' / 'companion.sqlite3', clock=clock, vault=MemoryVault(),
                     provider=provider, life_tasks=False, image_adapters=adapters)
    with TestClient(app, headers={CLIENT_HEADER: 'workspace'}) as test_client:
        yield test_client


@pytest.fixture
def giphy(monkeypatch):
    """GIPHY answering every search with a few GIFs."""
    def get(url, params, timeout):
        return httpx.Response(200, json={'data': [giphy_item(index) for index in range(3)]},
                              request=httpx.Request('GET', url))
    monkeypatch.setattr(gifs, 'FETCH', True)
    monkeypatch.setattr(gifs, 'KEPT', {})
    monkeypatch.setattr(gifs.httpx, 'get', get)


def shown(client, message_id):
    return client.get(f'/api/images/photos/{message_id}').json()


def history_photo(client, message_id):
    return next(message for message in client.get('/api/conversation').json()['messages']
                if message['id'] == message_id)['photo']


def test_another_take_makes_a_new_picture_of_the_same_moment(client, life, adapters):
    local_comfy(client)
    reply = ask(client)
    drain(client)
    first = shown(client, reply['id'])
    assert first['status'] == 'completed'
    again = client.post(f"/api/images/photos/{reply['id']}/reroll")
    assert again.status_code == 200, again.text
    assert again.json()['status'] == 'queued' and again.json()['job_id'] != first['job_id']
    drain(client)
    second = shown(client, reply['id'])
    assert second['status'] == 'completed' and second['ref'] != first['ref']
    assert second['post_id'] == first['post_id'] and second['summary'] == first['summary']
    seeds = [request.seed for request in adapters['comfyui'].requests]
    assert len(seeds) == 2 and seeds[0] != seeds[1]
    assert [request.prompt for request in adapters['comfyui'].requests][0] == adapters['comfyui'].requests[1].prompt
    # The moment's feed post shows the new take too, and so does the chat after a reload.
    assert history_photo(client, reply['id'])['ref'] == second['ref']


def test_a_picture_still_coming_is_not_made_twice(client, life):
    local_comfy(client)
    reply = ask(client)
    assert client.post(f"/api/images/photos/{reply['id']}/reroll").status_code == 409


def test_a_template_meme_gets_another_picture_and_keeps_its_captions(client, life):
    reply = ask(client, 'send me a meme')
    photo = reply['photo']
    assert photo['source'] == 'template'
    again = client.post(f"/api/images/photos/{reply['id']}/reroll").json()
    assert again['src'] != photo['src'] and again['src'].startswith('/api/images/memes/pictures/')
    assert (again['top_text'], again['bottom_text']) == (photo['top_text'], photo['bottom_text'])


def test_a_gif_gets_another_one_for_the_same_search(client, life, giphy):
    client.put('/api/images/memes/gif-key', json={'key': 'abc123'})
    reply = ask(client, 'send me a gif')
    photo = reply['photo']
    assert photo['source'] == 'gif'
    again = client.post(f"/api/images/photos/{reply['id']}/reroll").json()
    assert again['source'] == 'gif' and again['src'] != photo['src']
    assert again['page'].startswith('https://giphy.com/')


def test_no_other_gif_says_so(client, life, giphy, monkeypatch):
    client.put('/api/images/memes/gif-key', json={'key': 'abc123'})
    reply = ask(client, 'send me a gif')
    only = [{**gif, 'url': reply['photo']['src']} for gif in gifs.KEPT[next(iter(gifs.KEPT))][1][:1]]
    monkeypatch.setattr(gifs, 'kept', lambda tag: only)
    monkeypatch.setattr(gifs, 'FETCH', False)
    response = client.post(f"/api/images/photos/{reply['id']}/reroll")
    assert response.status_code == 409 and 'No other GIF' in response.json()['detail']


def test_removing_takes_the_picture_out_of_the_chat_and_undo_brings_it_back(client, life):
    local_comfy(client)
    reply = ask(client)
    drain(client)
    removed = client.delete(f"/api/images/photos/{reply['id']}").json()
    assert removed['removed'] is True
    # The chat still hears of it, marked, so Undo can show while it is on screen; nothing else shows it.
    assert history_photo(client, reply['id'])['removed'] is True
    assert shown(client, reply['id'])['removed'] is True
    assert client.post(f"/api/images/photos/{reply['id']}/retry").status_code == 404
    back = client.post(f"/api/images/photos/{reply['id']}/restore").json()
    assert back['removed'] is False and history_photo(client, reply['id'])['ref'] == back['ref']


def test_removing_a_picture_that_is_not_there(client, life):
    assert client.delete('/api/images/photos/nope').status_code == 404
    assert client.post('/api/images/photos/nope/reroll').status_code == 404
