"""Long distance (companion/life/long_distance.py): weekend visits both ways, the time difference, and no drop-ins
across cities."""
from datetime import timedelta

import pytest
from conftest import reconcile, send
from test_together import mira, notes, says, where

from companion.characters import current
from companion.database import decode
from companion.life import long_distance, openers, trips

FREE_WEEK = [{'key': 'day', 'label': 'Day', 'kind': 'leisure', 'start': '07:00', 'end': '23:00'},
             {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]


def test_visits_across_the_distance_are_read_from_the_message():
    assert long_distance.asked('come visit me?') == long_distance.TO_YOU
    assert long_distance.asked('You should come stay with me for the weekend') == long_distance.TO_YOU
    assert long_distance.asked('Can I come see you this weekend?') == long_distance.HOST
    assert long_distance.asked('could i fly out to visit you?') == long_distance.HOST
    for text in ('I visited my mom last weekend', 'I wish I could see you', 'how was work?',
                 "don't come visit me yet"):
        assert long_distance.asked(text) is None, text


def apart_from(client, monkeypatch, city='Chicago', timezone='America/Chicago', **values):
    mira(client, monkeypatch, home_city=city, timezone=timezone, **values)
    world = client.get('/api/worlds').json()['world']
    assert client.put(f"/api/worlds/{world['id']}/home", json={'city_id': 'baltimore'}).status_code == 200
    return world


@pytest.fixture
def apart(client, monkeypatch):
    return apart_from(client, monkeypatch)


@pytest.fixture
def visits(monkeypatch):
    """Weekends are decided (companion/life/trips.py), with no trips of their own and every free one a visit."""
    monkeypatch.setattr(trips, 'ACTIVE', True)
    monkeypatch.setattr(trips, 'CHANCE', 0.0)
    monkeypatch.setattr(trips, 'LONG_CHANCE', 0.0)
    monkeypatch.setattr(long_distance, 'CHANCE', {1: 1.0, 2: 1.0, 3: 1.0})


def planned(client):
    response = client.get('/api/life/outings')
    assert response.status_code == 200, response.text
    return [trip for trip in response.json()['trips'] if trip['visit']]


def agenda(client, local_date):
    with client.app.state.database.connect() as connection:
        rows = connection.execute("SELECT block, entry FROM life_agenda WHERE subject='companion' AND local_date=? "
                                  'ORDER BY starts_at', (local_date,)).fetchall()
    return [(decode(row['block']), decode(row['entry']) if row['entry'] else None) for row in rows]


def test_the_long_distance_line_says_how_far_and_the_time_difference(client, apart, provider):
    says(provider)
    send(client, 'hey you, how was your day?', 'client-far-1')
    assert 'You live in Chicago and the user lives in Baltimore, about ' in notes(provider)
    assert 'you are long distance and you are 5 hours behind the user' in notes(provider)
    assert "You can't just meet up or come over" in notes(provider)
    assert where(client)['text'] == 'Long distance, Chicago, 5 hours behind'


def test_they_come_to_stay_for_a_weekend(client, apart, visits, provider, clock, monkeypatch):
    monkeypatch.setattr(long_distance, 'turn', lambda *_args: long_distance.TO_YOU)
    reconcile(client)
    [visit] = planned(client)
    assert (visit['visit'], visit['city_id'], visit['start_date'], visit['end_date']) == \
        (long_distance.TO_YOU, 'baltimore', '2026-10-17', '2026-10-18')
    assert visit['state'] == 'planned' and not visit['landmark']  # No postcard of the user's own city.
    monkeypatch.setattr(long_distance, 'FIRST_TEXTS', True)
    with client.app.state.database.connect() as connection:
        [trigger] = long_distance.news_due(connection, current(connection), clock.now())
    assert trigger.kind == 'visit_news' and 'Saturday October 17 to Sunday October 18' in trigger.reason
    says(provider)
    send(client, 'what are you up to?', 'client-far-2')
    assert 'Saturday October 17 to Sunday October 18: you are going to Baltimore to stay with the user for the ' \
        'weekend. It is booked.' in notes(provider)
    # Saturday noon in Chicago: they have arrived.
    clock.advance(timedelta(days=12, hours=5))
    reconcile(client)
    found = where(client)
    assert (found['state'], found['kind'], found['text']) == ('together', 'staying', 'Staying with you until Sunday')
    assert found['visit']['direction'] == long_distance.TO_YOU and found['visit']['end_date'] == '2026-10-18'
    says(provider)
    send(client, 'so glad you are here', 'client-far-3')
    assert 'Right now you are in Baltimore, staying with the user at their place' in notes(provider)
    assert 'It is 17:00 there.' in notes(provider) and 'face to face, not texting' in notes(provider)
    assert 'You live in Chicago' not in notes(provider)
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        assert openers.held(connection, companion, {'texts_first': True}, clock.now()) == 'together'
    waking = [item for item in agenda(client, '2026-10-17') if item[0]['kind'] != 'sleep']
    assert waking and all(block['with_user'] for block, _entry in waking)
    assert any('with you' in entry['summary'] or 'to see you' in entry['summary'] for _block, entry in waking)
    # Monday: over, and kept as a memory.
    clock.advance(timedelta(days=2))
    reconcile(client)
    assert where(client)['state'] == 'apart'
    with client.app.state.database.connect() as connection:
        row = connection.execute('SELECT memory_id FROM trips WHERE id=?', (visit['id'],)).fetchone()
        memory = connection.execute('SELECT subject FROM memories WHERE id=?', (row['memory_id'],)).fetchone()
    assert memory['subject'] == 'You stayed with the user in Baltimore'
    says(provider)
    send(client, 'miss you already', 'client-far-4')
    assert 'You just spent a weekend together: you went to stay with the user in Baltimore' in notes(provider)


def test_the_user_comes_to_them_and_can_call_it_off(client, apart, visits, provider, clock, monkeypatch):
    monkeypatch.setattr(long_distance, 'turn', lambda *_args: long_distance.HOST)
    reconcile(client)
    [visit] = planned(client)
    assert (visit['visit'], visit['city_id']) == (long_distance.HOST, 'chicago')
    response = client.post(f"/api/life/trips/{visit['id']}/cancel")
    assert response.status_code == 200, response.text
    [called_off] = planned(client)
    assert called_off['state'] == 'cancelled' and called_off['undo']
    assert client.post(f"/api/life/trips/{visit['id']}/undo").status_code == 200
    assert planned(client)[0]['state'] == 'planned'
    clock.advance(timedelta(days=12, hours=5))
    reconcile(client)
    assert where(client)['text'] == "You're staying in Chicago until Sunday"
    says(provider)
    send(client, 'your place is so cozy', 'client-far-5')
    assert 'Right now the user is here in Chicago, staying with you at your place for the weekend' in notes(provider)
    assert client.post(f"/api/life/trips/{visit['id']}/cancel").status_code == 409  # Under way.


def test_calling_a_visit_off_is_told(client, apart, visits, provider, monkeypatch):
    monkeypatch.setattr(long_distance, 'turn', lambda *_args: long_distance.HOST)
    reconcile(client)
    [visit] = planned(client)
    assert client.post(f"/api/life/trips/{visit['id']}/cancel").status_code == 200
    says(provider)
    send(client, 'sorry about the weekend', 'client-far-6')
    assert 'The user called off the weekend visit' in notes(provider)


def test_they_come_only_when_they_can_afford_the_fare(client, apart, visits, monkeypatch):
    monkeypatch.setattr(long_distance, 'turn', lambda *_args: long_distance.TO_YOU)
    monkeypatch.setattr(trips, 'price', lambda _definition, share, *_args: 20.0 if share == long_distance.HOST_SHARE
                        else None)
    reconcile(client)
    [visit] = planned(client)
    assert visit['visit'] == long_distance.HOST and visit['city_id'] == 'chicago'


def test_no_visits_on_their_own_when_the_slider_is_off(client, apart, visits):
    client.put('/api/life/settings', json={'together_realism': 0})
    reconcile(client)
    assert planned(client) == []


def test_asking_for_a_visit_in_the_chat(client, apart, provider):
    says(provider)
    send(client, 'come visit me this weekend?', 'client-far-7')
    [visit] = planned(client)
    assert (visit['visit'], visit['start_date'], visit['end_date']) == (long_distance.TO_YOU, '2026-10-10',
                                                                       '2026-10-11')
    assert 'You agreed to a weekend visit: you are going to Baltimore to stay with the user, Saturday October 10 to ' \
        'Sunday October 11. Confirm the dates' in notes(provider)
    says(provider)
    send(client, 'can I come see you sometime?', 'client-far-8')
    second = [trip for trip in planned(client) if trip['id'] != visit['id']]
    assert second[0]['visit'] == long_distance.HOST and second[0]['start_date'] == '2026-10-17'
    # "Come over Saturday?" from another city is a weekend visit too.
    says(provider)
    send(client, 'can you come over Saturday the 31st?', 'client-far-9')
    assert len(planned(client)) == 3


def test_a_visit_they_cannot_afford_says_why(client, apart, provider, monkeypatch):
    monkeypatch.setattr(trips, 'price', lambda *_args: None)
    says(provider)
    send(client, 'come visit me?', 'client-far-10')
    assert planned(client) == []
    assert "you to come and stay with them for a weekend. You can't: you can't afford the trip" in notes(provider)


def test_no_outings_across_the_distance(client, apart, provider):
    says(provider)
    send(client, 'dinner Friday?', 'client-far-11')
    assert client.get('/api/life/outings').json()['outings'] == []
    assert "The user asked to meet up and go out together. You can't: you live in Chicago" in notes(provider)
    assert "so you can't just meet up" in notes(provider)


def test_beyond_a_trips_reach_visits_are_longer_on_days_off(client, monkeypatch, visits):
    apart_from(client, monkeypatch, city='Osaka', timezone='Asia/Tokyo', schedule=FREE_WEEK)
    monkeypatch.setattr(long_distance, 'turn', lambda *_args: long_distance.TO_YOU)
    reconcile(client)
    [visit] = planned(client)
    assert (visit['start_date'], visit['end_date']) == ('2026-10-15', '2026-10-19')  # Thursday to Monday.
    with client.app.state.database.connect() as connection:
        between = long_distance.far(connection, current(connection))
    assert not between.within_reach and long_distance.gap(2, between) == 84


def test_working_weekdays_beyond_reach_means_no_weekend_visit(client, monkeypatch, visits):
    apart_from(client, monkeypatch, city='Osaka', timezone='Asia/Tokyo')
    reconcile(client)
    assert planned(client) == []


def test_moving_to_their_city_calls_off_visits_to_come(client, apart, visits, monkeypatch):
    monkeypatch.setattr(long_distance, 'turn', lambda *_args: long_distance.TO_YOU)
    reconcile(client)
    assert planned(client)[0]['state'] == 'planned'
    assert client.put(f"/api/worlds/{apart['id']}/home", json={'city_id': 'chicago'}).status_code == 200
    reconcile(client)
    assert planned(client)[0]['state'] == 'cancelled'
