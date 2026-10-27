"""Books, shows and songs of the companion's own made-up world (companion/life/media_world.py)."""
import pytest

from companion.database import decode
from companion.life import body, media, media_world
from companion.world import catalog
from companion.world.source import CatalogWorld

WORLD = CatalogWorld()
SHARED = {kind: {item['title'] for item in media.bank('tales')[kind]} for kind in media.KINDS}


def made_up(city_id: str, **extra) -> tuple[dict, dict]:
    data = {**WORLD.find(city_id), **extra}
    me = {**media.place_of(data), 'reader': 1, 'watcher': 1, 'library': False}
    return data, me


@pytest.mark.parametrize('city_id', ['camelot', 'grandport', 'emerald-city', 'ellerbruck'])
def test_a_made_up_city_builds_titles_from_its_own_places_people_and_festivals(city_id):
    data, me = made_up(city_id)
    assert me['world'] == 'built'
    found = media.world_titles(me, data)
    own_words = {data['name'], *(hood['name'] for hood in data['neighborhoods']),
                 *(place['name'] for place in data['places']), *(person['name'] for person in data['notables']),
                 *(day['name'] for day in data['holidays']), *(event['name'] for event in data['annual_events']),
                 *(entry['title'] for entry in (data.get('lore') or {}).get('entries', ())),
                 *(entry['name'] for entry in data['local_color'])}
    for kind in media.KINDS:
        assert len(found['built'][kind]) >= 20, kind
        for item in found['built'][kind]:
            assert item['title'] not in SHARED[kind] and len(item['title']) <= 120
            assert ' The ' not in item['title'] and item['tags'] and item['year'] == 0
            assert any(word.casefold().removeprefix('the ') in item['title'].casefold() for word in own_words), item
        if kind == 'show':
            assert {item['format'] for item in found['built'][kind]} <= {'play', 'serial', 'cycle'}
    assert media_world.build(data, me['bank']) == found['built']  # seeded: the same every time


def test_cities_of_our_world_keep_the_real_banks():
    for city_id in ('baltimore', 'new-york-1925', 'london-1895'):
        data = WORLD.find(city_id)
        me = media.place_of(data)
        assert me['world'] == '' and media.world_titles(me, data) is None


def test_a_made_up_world_mostly_picks_its_own_titles_and_sometimes_a_shared_one():
    data, me = made_up('camelot')
    titles = media.world_titles(me, data)
    built = {item['title'] for kind in media.KINDS for item in titles['built'][kind]}
    picks = [media.choose(f's{n}', 'book:0', me, 'book', {'interests': ['history']}, set(), titles) for n in range(200)]
    share = sum(item['title'] in built for item in picks) / len(picks)
    assert 0.45 < share < 0.75
    assert all(item['title'] in built or item['title'] in SHARED['book'] for item in picks)


def test_a_city_with_its_own_list_reads_from_it_and_never_the_shared_bank():
    block = {'credit': 'A friend', 'book': [['The Placidium Accords', 'Sona Buvelle', 0, 'history'],
                                            {'title': 'Pit Fighter', 'by': '', 'tags': ['sports']}, ['', 'x', 0, 'x'],
                                            ['Pit Fighter', '', 0, 'sports']],
             'show': [['The Kinkou Players at Midsummer', 'the Kinkou Players', 0, 'play comedy']],
             'music': 'not a list'}
    data = {**WORLD.find('grandport'), 'media': block}
    notes = media_world.clean(data)
    assert notes == ['Left out 2 book entries with no title or a repeated one.',
                     'Left out the music entries: they need to be a list.']
    assert data['media']['book'] == [['The Placidium Accords', 'Sona Buvelle', 0, 'history'],
                                     ['Pit Fighter', '', 0, 'sports']]
    assert 'music' not in data['media'] and data['media']['credit'] == 'A friend'
    data, me = made_up('grandport', media=data['media'])
    titles = media.world_titles(me, data)
    assert me['world'] == 'own' and titles['own']['show'][0]['format'] == 'play'
    built = {item['title'] for item in titles['built']['book']}
    picks = [media.choose(f's{n}', 'book:0', me, 'book', {}, set(), titles)['title'] for n in range(200)]
    assert 0.7 < sum(title in {'The Placidium Accords', 'Pit Fighter'} for title in picks) / len(picks) < 0.9
    assert all(title in built or title in {'The Placidium Accords', 'Pit Fighter'} for title in picks)
    # Once their own and the built titles have all been had, the shared bank fills in.
    taken = {title.casefold() for title in [*built, 'The Placidium Accords', 'Pit Fighter']}
    assert media.choose('x', 'book:9', me, 'book', {}, taken, titles)['title'] in SHARED['book']


def test_a_bad_block_is_dropped_and_the_city_still_loads():
    raw = catalog.city('grandport')
    data = catalog.prepare({key: value for key, value in raw.items()
                            if key not in ('data_version', 'builtin', 'origin', 'import_notes')} | {'media': [1, 2]},
                           mend=True)
    assert 'media' not in data
    assert 'Dropped the books, shows and songs: they need lists named book, show or music.' in data['import_notes']
    assert data['data_version'] == raw['data_version']


@pytest.fixture
def ines(client, monkeypatch, provider):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    response = client.post('/api/companion', json={'name': 'Ines', 'timezone': 'UTC', 'home_city': 'grandport',
                                                    'interests': ['history']})
    assert response.status_code == 200, response.text
    return response.json()


def test_picks_saved_before_the_world_had_its_own_titles_are_drawn_again(client, ines):
    client.get('/api/life/media')
    database = client.app.state.database
    shared = sorted(SHARED['book'])[0]
    with database.connect(write=True) as connection:
        assert decode(connection.execute('SELECT profile FROM media_state').fetchone()[0])['world'] == 'built'
        connection.execute("UPDATE media_state SET profile=json_remove(profile, '$.world')")
        connection.execute("UPDATE media_items SET title=? WHERE kind='book' AND status='current'", (shared,))
    view = client.get('/api/life/media').json()
    assert [item['kind'] for item in view['now']] == ['book', 'show', 'music']
    assert all(item['title'] != shared for item in view['now'])
    with database.connect() as connection:
        assert decode(connection.execute('SELECT profile FROM media_state').fetchone()[0])['world'] == 'built'
