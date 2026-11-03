"""Second location: a meetup in town moves on to a second place nearby when the first one ends."""
from datetime import date, timedelta

import pytest
from conftest import reconcile, send, set_life

from companion.life import body, composer, onward, outings
from companion.providers.chat import Chunk
from companion.world import catalog

EVENINGS = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00', 'days': [0, 1, 2, 3, 4]},
            {'key': 'evening', 'label': 'Evening', 'kind': 'leisure', 'start': '17:00', 'end': '23:00'},
            {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]


@pytest.fixture
def mira(client, monkeypatch, provider):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(composer, 'PLAN_SHARE', 0)
    monkeypatch.setattr(composer, 'THREAD_SHARE', 0)
    monkeypatch.setattr(onward, 'ACTIVE', True)
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC', 'schedule': EVENINGS,
                                                    'home_city': 'Baltimore', 'interests': ['seafood', 'jazz']})
    assert response.status_code == 200, response.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    set_life(client, automatic_events=True, phrase_with_model=False, catch_up_max_events=6,
             catch_up_lookback_hours=168)
    return response.json()


@pytest.fixture
def always(monkeypatch):
    """The dice always say it moves on."""
    monkeypatch.setattr(onward, 'CHANCE', (0.0, 1.0, 1.0, 1.0))


def listing(client):
    response = client.get('/api/life/outings')
    assert response.status_code == 200, response.text
    return response.json()['outings']


def stored(client, outing_id):
    with client.app.state.database.connect() as connection:
        return outings.get(connection, outing_id)


def preview(client):
    return client.get('/api/context/preview').json()['prompt']


def dinner_tonight(client, provider, key):
    provider.replies.append([Chunk('Yes!'), Chunk('', 'stop')])
    send(client, 'Dinner tonight?', key)
    [outing] = listing(client)
    return outing


def test_what_comes_next_follows_what_came_first_and_the_time_of_day():
    assert onward.options('dinner', '21:00') == ('drinks', 'walk')
    assert onward.options('walk', '15:00') == ('coffee', 'lunch-out')
    assert onward.options('walk', '18:00') == ('dinner', 'drinks')
    assert onward.options('coffee', '11:30') == ('walk', 'museum', 'market')
    # Only meetups out in town: not at either home, a drop-in, their family or a big day.
    out = {'activity': 'dinner', 'place': {'id': 'lupa', 'kind': 'restaurant'}}
    assert onward.qualifies(out)
    assert not onward.qualifies({**out, 'activity': 'dinner-in', 'place': {'id': '~home', 'kind': 'home'}})
    assert not onward.qualifies({**out, 'activity': 'meet-family'})
    assert not onward.qualifies({**out, 'place': {'id': 'lupa', 'kind': 'restaurant', 'knock': True}})


def test_the_next_place_is_open_then_and_close_by():
    data = catalog.city('baltimore')
    outing = {'id': 'x', 'local_date': '2026-10-05', 'activity': 'dinner',
              'place': outings.place_view(next(item for item in data['places'] if item['kind'] == 'restaurant'), data)}
    bars = onward.fitting(data, 'drinks', date(2026, 10, 5), '21:00', outing)
    assert bars and all(item['kind'] in outings.kinds('drinks') for item in bars)
    weights = onward.closeness(data, outing, bars)
    same = [item for item, weight in zip(bars, weights) if weight == onward.SAME]
    assert all(outings.place_view(item, data)['neighborhood'] == outing['place']['neighborhood'] for item in same)


def test_a_date_moves_on_to_a_second_place(client, mira, provider, clock, always):
    outing = dinner_tonight(client, provider, 'onward-1')
    # Today and the strip show the first place until 21:00; the second is a surprise until near the move.
    assert (outing['until_time'], outing['next'], outing['activity']) == ('21:00', None, 'dinner')
    saved = stored(client, outing['id'])
    stop = saved['onward']
    assert stop['activity'] == 'drinks' and stop['at'] == '21:00' and saved['until_time'] > '21:00'
    assert saved['cost'] >= outing['cost']
    clock.advance(timedelta(hours=7, minutes=30))  # 19:30.
    reconcile(client)
    assert 'feel like going on to' not in preview(client)
    clock.advance(timedelta(hours=1, minutes=15))  # 20:45: the move is near.
    [near] = listing(client)
    assert near['next']['place']['id'] == stop['place']['id'] and near['longer_ok']
    where = client.get('/api/life/where').json()
    assert where['outing']['next']['place']['name'] == stop['place']['name']
    assert "you feel like going on to" in preview(client) and stop['place']['name'] in preview(client)
    clock.advance(timedelta(minutes=16))  # 21:01: moved on.
    [there] = listing(client)
    assert there['place']['id'] == stop['place']['id'] and there['came_from']['name'] == outing['place']['name']
    assert there['state'] == 'now' and there['undo_move'] and there['moved_at'] == '21:00'
    where = client.get('/api/life/where').json()
    assert where['text'] == f"Together at {stop['place']['name']}"
    text = preview(client)
    assert f"You just came over here from {outing['place']['name']}" in text
    assert f"Right now you are out with the user, in person: {outings.ACTIVITIES[stop['activity']][5]} at " \
           f"{stop['place']['name']}" in text
    clock.advance(timedelta(hours=2))  # Over.
    reconcile(client)
    [done] = listing(client)
    assert done['status'] == 'done' and done['memory_id']
    with client.app.state.database.connect() as connection:
        memory = connection.execute('SELECT value FROM memories WHERE id=?', (done['memory_id'],)).fetchone()
    assert outing['place']['name'] in memory['value'] and "then on to" in memory['value']
    assert stop['place']['name'] in memory['value']


def test_stay_longer_keeps_them_where_they_are(client, mira, provider, clock, always):
    outing = dinner_tonight(client, provider, 'onward-2')
    second = stored(client, outing['id'])['onward']['cost']  # The bill counts both places until they stay.
    clock.advance(timedelta(hours=8, minutes=45))  # 20:45.
    stayed = client.post(f"/api/life/outings/{outing['id']}/longer").json()
    assert stayed['until_time'] == '22:00' and stayed['onward'] == {'none': True, 'stayed': True}
    assert stayed['cost'] == round(outing['cost'] - second, 2)
    clock.advance(timedelta(minutes=30))  # 21:15: still at the first place.
    [still] = listing(client)
    assert still['place']['id'] == outing['place']['id'] and still['state'] == 'now'


def test_undo_just_after_the_move_and_somewhere_else_before_it(client, mira, provider, clock, always):
    outing = dinner_tonight(client, provider, 'onward-3')
    stop = stored(client, outing['id'])['onward']
    clock.advance(timedelta(hours=8, minutes=45))  # 20:45.
    other = client.post(f"/api/life/outings/{outing['id']}/next")
    if other.status_code == 200:  # Baltimore has more than one place open then.
        assert other.json()['onward']['place']['id'] != stop['place']['id']
    clock.advance(timedelta(minutes=16))  # 21:01: just moved on.
    assert listing(client)[0]['undo_move']
    back = client.post(f"/api/life/outings/{outing['id']}/back").json()
    assert back['until_time'] == '22:00' and back['onward']['none']
    [here] = listing(client)
    assert here['place']['id'] == outing['place']['id'] and not here['undo_move']
    clock.advance(timedelta(minutes=5))
    assert client.post(f"/api/life/outings/{outing['id']}/back").status_code == 409


def test_heading_home_before_the_move_keeps_one_place_and_one_bill(client, mira, provider, clock, always):
    outing = dinner_tonight(client, provider, 'onward-4')
    second = stored(client, outing['id'])['onward']['cost']
    clock.advance(timedelta(hours=8))  # 20:00.
    client.post(f"/api/life/outings/{outing['id']}/home")
    clock.advance(timedelta(minutes=3))
    reconcile(client)
    saved = stored(client, outing['id'])
    assert saved['status'] == 'done' and saved['onward'] == {'none': True} and \
        saved['cost'] == round(outing['cost'] - second, 2)
    with client.app.state.database.connect() as connection:
        memory = connection.execute('SELECT value FROM memories WHERE id=?', (saved['memory_id'],)).fetchone()
    assert 'then on to' not in memory['value']


def test_never_on_the_slider(client, mira, provider, clock):
    set_life(client, onward_realism=0)
    outing = dinner_tonight(client, provider, 'onward-5')
    assert stored(client, outing['id'])['onward'] == {'none': True}


def test_asking_while_out_moves_on_instead_of_booking_another_day(client, mira, provider, clock):
    set_life(client, onward_realism=0)
    outing = dinner_tonight(client, provider, 'onward-6')
    clock.advance(timedelta(hours=7, minutes=30))  # 19:30, at dinner.
    provider.replies.append([Chunk('Love that.'), Chunk('', 'stop')])
    send(client, 'Want to grab a drink after this?', 'onward-7')
    [saved] = [stored(client, item['id']) for item in listing(client)]  # No second outing.
    stop = saved['onward']
    assert stop['asked'] and stop['activity'] == 'drinks' and stop['at'] == '21:00'
    assert 'The user asked to go on somewhere and you agreed' in provider.requests[-1]['prompt']
    # "Let's get out of here" moves them on now.
    provider.replies.append([Chunk('Yes, lets.'), Chunk('', 'stop')])
    send(client, "Honestly, let's get out of here", 'onward-8')
    now = stored(client, outing['id'])['onward']
    assert now['at'] == '19:30' and now['asked']
    [there] = listing(client)
    assert there['place']['id'] == now['place']['id'] and not there['undo_move']


def test_a_walk_after_dark_only_on_a_warm_evening():
    assert onward.options('dinner', '21:00', date(2026, 10, 5)) == ('drinks',)
    assert onward.options('dinner', '21:00', date(2026, 7, 5)) == ('drinks', 'walk')
    assert onward.options('walk', '15:00', date(2026, 1, 5)) == ('coffee', 'lunch-out')
