"""The companion's home and belongings (companion/life/home.py)."""
from datetime import date, timedelta

import pytest
from conftest import reconcile

from companion.database import decode
from companion.life import composer, home, money
from companion.world.source import CatalogWorld

DAYS = [{'key': 'day', 'label': 'Day', 'kind': 'leisure', 'start': '09:00', 'end': '17:00'},
        {'key': 'chores', 'label': 'Chores', 'kind': 'errand', 'start': '18:00', 'end': '20:00'},
        {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]
MIRA = {'name': 'Mira', 'interests': ['vinyl records', 'cooking'], 'location': 'Fells Point, Baltimore'}


@pytest.fixture
def baltimore(client, monkeypatch):
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(composer, 'PLAN_SHARE', 0)
    monkeypatch.setattr(composer, 'THREAD_SHARE', 0)
    response = client.post('/api/companion', json={**MIRA, 'timezone': 'America/New_York', 'schedule': DAYS})
    assert response.status_code == 200, response.text
    return response.json()


def connect(client, write=True):
    return client.app.state.database.connect(write=write)


def timeline(client) -> str:
    with connect(client, False) as connection:
        return connection.execute('SELECT active_timeline_id FROM companions').fetchone()[0]


def test_assembly_is_deterministic_and_uses_the_city_data():
    data = CatalogWorld().find('baltimore')
    first = home.assemble('home:t1', MIRA, data)
    assert home.assemble('home:t1', MIRA, data) == first
    assert any(home.assemble(f'home:t{n}', MIRA, data) != first for n in range(2, 6))
    place = first[0]
    assert place['kind'] == 'home' and place['details']['city'] == 'Baltimore'
    # The budget already pays rent on a home, so this is that home: same neighbourhood, size and rent.
    budget = money.profile(MIRA)
    assert place['details']['rent_from'] == 'budget' and place['details']['neighborhood'] == budget.neighborhood
    assert place['details']['bedrooms'] == budget.unit and abs(place['details']['rent'] - budget.rent) <= 13
    assert {item['kind'] for item in first} <= set(home.KINDS)
    assert sum(item['kind'] == 'favorite' for item in first) >= 2


def test_interests_lean_the_favourite_things():
    data = CatalogWorld().find('baltimore')
    musical = sum(item['name'] in ('a record player', 'a secondhand guitar') for n in range(40)
                  for item in home.assemble(f'home:{n}', MIRA, data))
    plain = sum(item['name'] in ('a record player', 'a secondhand guitar') for n in range(40)
                for item in home.assemble(f'home:{n}', {'name': 'Mira'}, data))
    assert musical > plain


def test_earlier_eras_get_no_cars_or_consoles():
    data = CatalogWorld().find('camelot')
    for n in range(30):
        items = home.assemble(f'home:{n}', {'name': 'Gwen', 'location': 'Camelot'}, data)
        assert 'bedroom' not in items[0]['name']
        assert all(item['variety'] in ('horse', 'bicycle') for item in items if item['kind'] == 'vehicle')
        assert not {'a game console', 'a record player'} & {item['name'] for item in items}


def test_reading_the_home_assembles_it_once(client, baltimore):
    first = client.get('/api/life/home').json()
    kinds = [item['kind'] for item in first['items']]
    assert kinds[0] == 'home' and first['costs']['rent'] > 0
    assert first['items'][0]['city'] == 'Baltimore'
    again = client.get('/api/life/home').json()
    assert [item['id'] for item in again['items']] == [item['id'] for item in first['items']]


def test_the_home_changes_slowly_and_the_same_in_steps_or_at_once(client, baltimore, clock):
    client.get('/api/life/home')
    tid = timeline(client)
    end = date(2027, 6, 1)
    with connect(client) as connection:
        # A fixed seed: with a random one, a run of quiet periods now and then left fewer than three changes.
        connection.execute("UPDATE home_state SET seed='steady-home' WHERE timeline_id=?", (tid,))
        for step in range(1, 235, 9):
            home.evolve(connection, tid, date(2026, 10, 5) + timedelta(days=step), clock.now())
        home.evolve(connection, tid, end, clock.now())
        stepped = [(row['local_date'], row['kind'], row['text']) for row in connection.execute(
            'SELECT * FROM home_log WHERE timeline_id=? ORDER BY local_date', (tid,)).fetchall()]
        connection.execute("DELETE FROM home_items WHERE origin='change'")
        connection.execute('UPDATE home_items SET until=NULL')
        connection.execute('DELETE FROM home_log')
        connection.execute('UPDATE home_state SET next_period=1')
        home.evolve(connection, tid, end, clock.now())
        once = [(row['local_date'], row['kind'], row['text']) for row in connection.execute(
            'SELECT * FROM home_log WHERE timeline_id=? ORDER BY local_date', (tid,)).fetchall()]
    assert stepped == once
    # At most one change every two weeks, and some do happen over eight months.
    assert 3 <= len(once) <= (end - date(2026, 10, 5)).days // home.PERIOD_DAYS + 1
    assert len({row[0] for row in once}) == len(once)


def test_a_change_is_told_once_in_the_companions_day(client, baltimore, clock):
    client.get('/api/life/home')
    tid = timeline(client)
    with connect(client) as connection:
        connection.execute("INSERT INTO home_log (id, timeline_id, period, local_date, kind, item_id, text, spend, "
                           "created_at) VALUES ('c1', ?, 99, '2026-10-06', 'rearrange', NULL, "
                           "'rearranged the furniture', '', '2026-10-05')", (tid,))
    reconcile(client)
    with connect(client, False) as connection:
        told = [decode(row[0]) for row in connection.execute(
            "SELECT entry FROM life_agenda WHERE subject='companion' AND json_extract(entry, '$.home.change')='c1'")]
        circle = connection.execute("SELECT COUNT(*) FROM life_agenda WHERE subject!='companion' "
                                    "AND json_extract(entry, '$.home') IS NOT NULL").fetchone()[0]
    assert len(told) == 1 and told[0]['summary'].endswith('Mira rearranged the furniture.')
    assert circle == 0


def test_belongings_come_up_in_ordinary_moments():
    items = [{'id': 'p', 'kind': 'pet', 'name': 'Biscuit', 'variety': 'dog'},
             {'id': 'c', 'kind': 'vehicle', 'name': 'the car', 'variety': 'car'}]
    homey = [home.at_home(items, f's{n}') for n in range(10)]
    assert all(found and 'Biscuit' in found[1] for found in homey)
    assert home.walked(items, 's')[0] == ['p']
    assert home.driven(items, {}, 's') == (['c'], 'Drove the car there.')
    assert 'still in the shop' in home.driven(items, {'c': {}}, 's')[1]
    assert home.walked([items[1]], 's') is None
    entry = home.woven({'summary': 'Mira went for a walk.', 'activity': 'walk'}, 'biscuit came along.', ['p'], None)
    assert entry['summary'] == 'Mira went for a walk. Biscuit came along.' and entry['home']['items'] == ['p']


def test_edits_rebuild_upcoming_moments_and_show_in_context(client, baltimore, clock):
    view = client.get('/api/life/home').json()
    added = client.post('/api/life/home/items', json={'kind': 'pet', 'name': 'Pickle', 'variety': 'dog',
                                                      'description': 'a three-legged corgi'})
    assert added.status_code == 200, added.text
    pet = next(item for item in added.json()['items'] if item['name'] == 'Pickle')
    assert pet['origin'] == 'user' and pet['edited']
    renamed = client.patch(f"/api/life/home/items/{pet['id']}", json={'name': 'Pickles'}).json()
    assert any(item['name'] == 'Pickles' for item in renamed['items'])
    assert client.patch(f"/api/life/home/items/{pet['id']}", json={'variety': 'dragon'}).status_code == 422
    assert client.post(f"/api/life/home/items/{view['items'][0]['id']}/remove").status_code == 422
    system = client.get('/api/context/preview').json()['system']
    assert '## Your home and belongings' in system and 'Pickles (a three-legged corgi)' in system
    removed = client.post(f"/api/life/home/items/{pet['id']}/remove").json()
    assert pet['id'] not in [item['id'] for item in removed['items']]
    assert pet['id'] in [item['id'] for item in removed['removed']]
    restored = client.post(f"/api/life/home/items/{pet['id']}/restore").json()
    assert pet['id'] in [item['id'] for item in restored['items']]


def test_edits_forget_changes_still_ahead(client, baltimore, clock):
    client.get('/api/life/home')
    tid = timeline(client)
    with connect(client) as connection:
        home.evolve(connection, tid, date(2029, 1, 1), clock.now())  # long enough that some seeded change is due
        ahead = connection.execute("SELECT COUNT(*) FROM home_log WHERE local_date>'2026-10-05'").fetchone()[0]
    assert ahead > 0
    item = client.get('/api/life/home').json()['items'][0]
    client.patch(f"/api/life/home/items/{item['id']}", json={'description': 'a tiny attic flat'})
    with connect(client, False) as connection:
        assert connection.execute("SELECT COUNT(*) FROM home_log WHERE local_date>'2026-10-05'").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM home_items WHERE origin='change' "
                                  "AND since>'2026-10-05'").fetchone()[0] == 0


def test_image_hints_describe_the_room_and_named_belongings(client, baltimore):
    view = client.get('/api/life/home').json()
    tid = timeline(client)
    client.post('/api/life/home/items', json={'kind': 'pet', 'name': 'Bean', 'description': 'a fat orange cat'})
    with connect(client, False) as connection:
        at_home = home.image_hint(connection, tid, {'summary': 'Mira read all evening. Bean slept nearby.', 'place': ''})
        out = home.image_hint(connection, tid, {'summary': 'Mira ate a bean salad.', 'place': 'Cafe'})
    assert at_home.startswith(f"At home: {view['items'][0]['description']}")
    assert 'Bean is a fat orange cat.' in at_home
    assert out == ''


def test_a_fork_keeps_the_home_as_it_was(client, baltimore, clock):
    client.get('/api/life/home')
    tid = timeline(client)
    with connect(client) as connection:
        home.evolve(connection, tid, date(2027, 1, 1), clock.now())
        connection.execute("INSERT INTO timelines (id, companion_id, status, created_at) "
                           "SELECT 'fork', companion_id, 'frozen', created_at FROM timelines WHERE id=?", (tid,))
        ids = {}
        home.copy(connection, tid, 'fork', '2026-11-15T12:00:00Z', ids)
        parent = {row[0] for row in connection.execute(
            "SELECT name FROM home_items WHERE timeline_id=? AND since<='2026-11-15'", (tid,))}
        forked = {row[0] for row in connection.execute("SELECT name FROM home_items WHERE timeline_id='fork'")}
        logged = connection.execute("SELECT MAX(local_date) FROM home_log WHERE timeline_id='fork'").fetchone()[0]
    assert forked == parent
    assert logged is None or logged <= '2026-11-15'
