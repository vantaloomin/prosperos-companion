"""Memes without a picture model (Hit List #50): templates on this computer, classic formats, the user's own
folder, reaction GIFs with the user's own GIPHY key, and the "Memes and GIFs" slider."""
import json
import shutil

import httpx
import pytest
from fastapi.testclient import TestClient

from companion.identity import CLIENT_HEADER
from companion.images import content, gifs, meme_pictures, memes, photos
from companion.main import create_app
from companion.providers.vault import MemoryVault
from tests.conftest import set_life
from tests.test_chat_photos import ask, photo_section
from tests.test_images import FakeAdapter, drain, local_comfy

DATA = memes.DATA


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
def unasked(monkeypatch):
    """Unasked pictures on and room for them; each test sets the chances it is about."""
    monkeypatch.setattr(photos, 'UNASKED', True)
    return photos


def root(client):
    return client.app.state.database.root


def meme(client, text='send me a meme', client_id='ask-0001'):
    return ask(client, text, client_id)['photo']


# The banks --------------------------------------------------------------------------------------------------

def test_every_situation_has_at_least_a_hundred_captions():
    bank = memes.bank()
    assert set(bank['situations']) == {'work', 'study', 'errand', 'social', 'leisure', 'rain', 'night', 'morning',
                                       'anytime'}
    for name, rows in bank['situations'].items():
        assert len(rows) >= 100, name
        assert len({row[0] + row[1] for row in rows}) == len(rows), name
        assert {row[2] for row in rows} <= set(bank['moods']), name
    assert len(bank['choice']) >= 100


def test_captions_keep_to_plain_words():
    bank = memes.bank()
    lines = [line for rows in bank['situations'].values() for row in rows for line in row[:2]]
    lines += [line for pair in bank['choice'] for line in pair]
    for line in lines:
        assert '—' not in line and '–' not in line, line
        assert not content.matches(content.normalize(line.format(where='the park'))) & photos.NOT_FOR_MEMES, line


def test_every_mood_has_pictures_in_the_starter_pack():
    pack = meme_pictures.pack()
    assert len(pack) >= 50
    for mood in memes.bank()['moods']:
        assert len([picture for picture in pack if mood in picture.moods]) >= 3, mood


def test_the_starter_pack_names_where_each_picture_came_from():
    entries = json.loads((DATA / 'pack.json').read_text(encoding='utf-8'))['pictures']
    for entry in entries:
        assert (DATA / 'pack' / entry['file']).is_file(), entry['id']
        assert entry['licence'] in ('CC0', 'Public Domain Mark'), entry['id']
        assert entry['source'].startswith('https://') and entry['title'] and entry['from'], entry['id']
    assert sorted(path.name for path in (DATA / 'pack').iterdir()) == sorted(entry['file'] for entry in entries)


def test_classic_formats_take_a_mood_or_the_choice():
    moods = set(memes.bank()['moods']) | {'choice'}
    formats = meme_pictures.formats()['formats']
    assert len(formats) >= 30
    for entry in formats:
        assert entry['moods'] and set(entry['moods']) <= moods, entry['id']


# Sending one ------------------------------------------------------------------------------------------------

def test_a_meme_needs_no_image_backend(client, life, provider):
    photo = meme(client)
    assert photo['kind'] == 'meme' and photo['source'] == 'template' and photo['status'] == 'completed'
    assert photo['src'].startswith('/api/images/memes/pictures/pack:') and photo['width'] and photo['height']
    assert photo['top_text'] in photo_section(provider) and photo['summary'] in photo_section(provider)
    picture = client.get(photo['src'])
    assert picture.status_code == 200 and picture.headers['content-type'] == 'image/jpeg'
    # It is the same when the chat asks for it again.
    assert client.get(f"/api/images/photos/{photo['message_id']}").json()['src'] == photo['src']


def test_with_an_image_model_a_share_of_memes_are_still_templates(client, life, adapters, monkeypatch):
    monkeypatch.setattr(photos, 'MODEL_SHARE', 0)
    local_comfy(client)
    photo = meme(client)
    drain(client)
    assert photo['source'] == 'template' and photo['job_id'] is None
    assert adapters['comfyui'].requests == []


def test_a_template_meme_never_reaches_the_feed(client, life):
    photo = meme(client)
    assert all(post['id'] != photo['post_id'] for post in client.get('/api/feed').json()['posts'])


def test_memes_can_be_turned_off_on_the_realism_tab(client, life):
    set_life(client, memes_realism=0)
    assert meme(client) is None
    set_life(client, memes_realism=2)
    assert meme(client, client_id='ask-0002')['kind'] == 'meme'


def test_older_cities_send_no_memes(client, life, monkeypatch):
    monkeypatch.setattr('companion.life.families.era_of', lambda _connection, _definition: 'victorian')
    assert meme(client) is None
    monkeypatch.setattr('companion.life.families.era_of', lambda _connection, _definition: 'future')
    assert meme(client, client_id='ask-0002') is not None


@pytest.mark.parametrize('text', ['send me a meme about my nude photos', 'send me a meme of a toddler'])
def test_some_words_never_get_a_meme(client, life, text):
    assert meme(client, text) is None


def test_how_often_memes_come_unasked_follows_the_slider(client, life, unasked, monkeypatch):
    monkeypatch.setattr(unasked, 'UNASKED_CHANCE', 0)
    monkeypatch.setattr(unasked, 'UNASKED_MEME_CHANCE', 0.9)
    set_life(client, memes_realism=0)
    assert ask(client, 'ugh, such a rough day', 'say-0001')['photo'] is None
    set_life(client, memes_realism=2)
    assert ask(client, 'ugh, such a rough day', 'say-0002')['photo']['unasked'] is True


def test_often_sends_one_now_and_then_out_of_the_blue(client, life, unasked, monkeypatch):
    monkeypatch.setattr(unasked, 'UNASKED_CHANCE', 0)
    monkeypatch.setattr(unasked, 'OFTEN_CHANCE', 1)
    assert ask(client, 'Just got home.', 'say-0001')['photo'] is None
    set_life(client, memes_realism=3)
    assert ask(client, 'Just got home.', 'say-0002')['photo']['kind'] == 'meme'


# Classic formats and the user's own folder --------------------------------------------------------------------

class FakeMemegen:
    """Answers memegen.link's blank pictures with a JPEG from the starter pack."""

    def __init__(self):
        self.asked = []

    def get(self, url):
        self.asked.append(url)
        return httpx.Response(200, content=(DATA / 'pack' / 'frog-stone.jpg').read_bytes())

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


def test_classic_formats_are_downloaded_in_the_background_once(tmp_path, monkeypatch):
    fake = FakeMemegen()
    monkeypatch.setattr(meme_pictures, 'FETCH', True)
    monkeypatch.setattr(meme_pictures.httpx, 'Client', lambda **_options: fake)
    meme_pictures.warm(tmp_path).join()
    total = len(meme_pictures.formats()['formats'])
    assert len(fake.asked) == total and all(url.startswith('https://api.memegen.link/images/') for url in fake.asked)
    assert len(meme_pictures.classic(tmp_path)) == total and meme_pictures.has_choice(tmp_path, True)
    assert not meme_pictures.has_choice(tmp_path, False)
    assert meme_pictures.warm(tmp_path) is None  # Nothing left to fetch.
    choice = {'top': 'Tea', 'bottom': 'Also tea', 'mood': 'choice'}
    assert meme_pictures.pick(choice, 'seed', tmp_path, True).id == 'classic:drake'


def test_a_failed_download_is_kept_out_and_tried_later(tmp_path, monkeypatch):
    class Broken(FakeMemegen):
        def get(self, url):
            self.asked.append(url)
            return httpx.Response(200, content=b'<html>not a picture</html>')
    monkeypatch.setattr(meme_pictures, 'FETCH', True)
    monkeypatch.setattr(meme_pictures, 'FAILED', {})
    monkeypatch.setattr(meme_pictures.httpx, 'Client', lambda **_options: Broken())
    meme_pictures.warm(tmp_path).join()
    assert meme_pictures.classic(tmp_path) == [] and meme_pictures.missing(tmp_path) == []


def test_the_users_own_templates_are_used_with_their_boxes(client, life, monkeypatch):
    folder = meme_pictures.folder(root(client))
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy(DATA / 'pack' / 'cat-statue.jpg', folder / 'my cat.jpg')
    (folder / 'my cat.json').write_text(json.dumps({'about': 'my cat looking regal', 'moods': list(memes.bank()['moods']),
                                                    'boxes': [{'x': 0, 'y': 0.1, 'w': 0.5, 'h': 0.2},
                                                              {'x': 0.5, 'y': 0.7, 'w': 0.5, 'h': 0.2}]}))
    pictures = [picture for picture in meme_pictures.mine(root(client))]
    assert [picture.id for picture in pictures] == ['mine:my cat.jpg'] and len(pictures[0].boxes) == 2
    # Only the user's picture to pick from, so the test does not hang on a seeded draw.
    monkeypatch.setattr(meme_pictures, 'pack', lambda: ())
    monkeypatch.setattr(memes, 'CHOICE_SHARE', 0)
    monkeypatch.setattr(photos, 'MODEL_SHARE', 0)
    sent = [meme(client, client_id=f'ask-{index:04}') for index in range(2)]
    own = [photo for photo in sent if photo['src'].endswith('mine:my%20cat.jpg')]
    assert own and own[0]['boxes'][1] == {'x': 0.5, 'y': 0.7, 'w': 0.5, 'h': 0.2}
    assert own[0]['summary'] == 'my cat looking regal'
    assert client.get(own[0]['src']).status_code == 200
    assert client.get('/api/images/memes').json()['mine'] == 1


@pytest.mark.parametrize('picture_id', ['mine:../companion.sqlite3', 'mine:', 'classic:../../x', 'classic:drake',
                                        'pack:nope', 'other:thing', 'mine:notes.txt'])
def test_only_listed_pictures_are_served(client, picture_id):
    assert client.get(f'/api/images/memes/pictures/{picture_id}').status_code == 404


def test_classic_formats_can_be_turned_off(client):
    assert client.put('/api/images/settings', json={'meme_formats': False}).json()['meme_formats'] is False
    assert client.get('/api/images/memes').json()['formats_on'] is False


# Reaction GIFs --------------------------------------------------------------------------------------------

def giphy_item(index, rating='g', title='Happy Cat GIF', url=None):
    return {'rating': rating, 'title': title, 'slug': title.lower().replace(' ', '-'), 'url': f'https://giphy.com/gifs/{index}',
            'images': {'fixed_width': {'url': url or f'https://media1.giphy.com/media/{index}/200w.gif',
                                       'width': '200', 'height': '150'},
                       'fixed_width_still': {'url': f'https://media1.giphy.com/media/{index}/200w_s.gif'}}}


@pytest.fixture
def giphy(monkeypatch):
    """GIPHY answering every search with a few GIFs; records the search words sent."""
    searched = []

    def get(url, params, timeout):
        searched.append(params['q'])
        assert params['rating'] == 'pg' and 'api_key' in params
        return httpx.Response(200, json={'data': [giphy_item(index) for index in range(3)]},
                              request=httpx.Request('GET', url))
    monkeypatch.setattr(gifs, 'FETCH', True)
    monkeypatch.setattr(gifs, 'KEPT', {})
    monkeypatch.setattr(gifs.httpx, 'get', get)
    return searched


def test_gifs_need_the_users_own_key(client, life, giphy):
    assert meme(client, 'send me a gif')['source'] == 'template'
    assert giphy == []
    saved = client.put('/api/images/memes/gif-key', json={'key': 'abc123'}).json()
    assert saved['gif_key'] is True and 'abc123' not in json.dumps(saved)
    photo = meme(client, 'send me a gif', 'ask-0002')
    assert photo['source'] == 'gif' and photo['src'].startswith('https://media1.giphy.com/')
    assert photo['page'].startswith('https://giphy.com/') and photo['top_text'] == ''
    # A still frame for reduced motion, and GIPHY's title to describe it.
    assert photo['still'].endswith('200w_s.gif') and photo['summary'] == 'Happy Cat GIF'
    # Only a word from the fixed list went to GIPHY.
    assert giphy and set(giphy) <= {tag for tags in gifs.TAGS.values() for tag in tags}
    assert client.put('/api/images/memes/gif-key', json={'key': ''}).json()['gif_key'] is False


def test_unasked_gifs_come_only_from_searches_already_made(client, life, giphy, monkeypatch):
    client.put('/api/images/memes/gif-key', json={'key': 'abc123'})
    started = []
    monkeypatch.setattr(gifs, 'fetch_later', lambda key, tag: started.append(tag))
    assert gifs.pick(client.app.state.vault, 'tired', 'seed') is None and started
    gifs.search('abc123', started[0], 1)
    assert gifs.pick(client.app.state.vault, 'tired', 'seed')['url'].startswith('https://media1.giphy.com/')


@pytest.mark.parametrize('item', [giphy_item(1, rating='r'), giphy_item(2, rating='pg-13'),
                                  giphy_item(3, title='Baby Laughing GIF'), giphy_item(4, title='Sexy Dance GIF'),
                                  giphy_item(5, url='https://example.com/cat.gif')])
def test_gifs_that_do_not_fit_are_dropped(item):
    assert gifs.shown(item) is None


def test_a_good_gif_is_kept():
    assert gifs.shown(giphy_item(1))['url'] == 'https://media1.giphy.com/media/1/200w.gif'


def test_a_still_frame_from_anywhere_but_giphy_drops_the_gif():
    item = giphy_item(1)
    item['images']['fixed_width_still']['url'] = 'https://example.com/still.gif'
    assert gifs.shown(item) is None


def test_the_gif_key_is_never_sent_over_home_wifi(client, monkeypatch):
    monkeypatch.setattr('companion.images.routes.via_lan', lambda _request: True)
    response = client.put('/api/images/memes/gif-key', json={'key': 'abc123'})
    assert response.status_code == 403 and 'Wi-Fi' in response.json()['detail']
    assert client.get('/api/images/memes').json()['key_here'] is False


def test_a_meme_asked_for_by_someones_name_is_held_to_the_stricter_check(client, life, monkeypatch):
    monkeypatch.setattr('companion.life.families.every_name', lambda _connection: {'Ivy'})
    assert meme(client, 'send me a meme about ivy') is None
    assert meme(client, 'send me a meme', client_id='ask-0002')['kind'] == 'meme'
