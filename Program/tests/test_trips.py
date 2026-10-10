"""Trips and postcards: now and then a weekend away in another city, with a postcard for the user."""
from datetime import date, timedelta

import pytest
from conftest import reconcile, set_life

from companion.database import decode
from companion.life import body, composer, trips
from companion.world import catalog

WEEKDAYS = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00', 'days': [0, 1, 2, 3, 4]},
            {'key': 'morning', 'label': 'Morning', 'kind': 'leisure', 'start': '07:00', 'end': '09:00'},
            {'key': 'evening', 'label': 'Evening', 'kind': 'leisure', 'start': '17:00', 'end': '23:00'},
            {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]


@pytest.fixture
def away(monkeypatch):
    monkeypatch.setattr(trips, 'ACTIVE', True)
    monkeypatch.setattr(trips, 'CHANCE', 1.0)
    monkeypatch.setattr(trips, 'FAMILY_SHARE', 0.0)
    monkeypatch.setattr(trips, 'cost', lambda *_args: 180.0)


@pytest.fixture
def mira(client, monkeypatch, away):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC', 'schedule': WEEKDAYS,
                                                    'home_city': 'Baltimore'})
    assert response.status_code == 200, response.text
    set_life(client, automatic_events=True, phrase_with_model=False, catch_up_max_events=6,
             catch_up_lookback_hours=168)
    return response.json()


def listing(client):
    response = client.get('/api/life/outings')
    assert response.status_code == 200, response.text
    return response.json()['trips']


def agenda(client, local_date):
    with client.app.state.database.connect() as connection:
        rows = connection.execute("SELECT slot_key, block, entry FROM life_agenda WHERE subject='companion' AND "
                                  'local_date=? ORDER BY starts_at', (local_date,)).fetchall()
    return [(row['slot_key'], decode(row['block']), decode(row['entry']) if row['entry'] else None) for row in rows]


def test_destinations_are_same_era_real_cities_within_reach():
    baltimore = catalog.city('baltimore')
    near = trips.destinations(baltimore, trips.REACH_KM[2])
    assert near and all(catalog.category(city) == 'real' and city.get('era', 'modern') == 'modern' and
                        catalog.distance_km(baltimore, city) <= 1200 for city in near)
    assert 'new-york' in {city['id'] for city in near} and 'london' not in {city['id'] for city in near}
    # A Victorian London companion only goes somewhere of their own era.
    old = catalog.city('london-1895')
    assert all(city.get('era') == old.get('era') for city in trips.destinations(old, trips.REACH_KM[3]))


def test_a_long_weekend_takes_the_holiday_too():
    baltimore = catalog.city('baltimore')
    # Labor Day 2026 is Monday September 7.
    assert trips.days_off(baltimore, date(2026, 9, 5)) == [date(2026, 9, 5), date(2026, 9, 6), date(2026, 9, 7)]
    assert trips.days_off(baltimore, date(2026, 9, 12)) == [date(2026, 9, 12), date(2026, 9, 13)]


def test_a_weekend_away_fills_their_days_in_the_other_city(client, mira, clock):
    reconcile(client)
    [trip] = listing(client)
    assert (trip['start_date'], trip['end_date'], trip['state']) == ('2026-10-17', '2026-10-18', 'planned')
    assert trip['city_id'] != 'baltimore' and trip['landmark']['name']
    clock.advance(timedelta(days=8))
    reconcile(client)
    saturday, sunday = agenda(client, '2026-10-17'), agenda(client, '2026-10-18')
    waking = [item for item in saturday + sunday if item[1]['kind'] != 'sleep']
    assert all(block['trip'] == trip['id'] and block['label'] == f"Away in {trip['city_name']}"
               for _key, block, _entry in waking)
    assert waking[0][2]['activity'] == 'trip-travel' and waking[0][2]['summary'].startswith(
        f"Mira set off for {trip['city_name']}")
    assert waking[-1][2]['activity'] in {'trip-home', 'trip-home-sun'}
    middle = [entry for _key, _block, entry in waking[1:-1]]
    assert middle and all(entry['activity'] == 'trip' and (entry['place'] is None or entry['place']['city'] ==
                                                           trip['city_name']) for entry in middle)
    clock.advance(timedelta(days=4, hours=8))  # Saturday 20:00.
    preview = client.get('/api/context/preview').json()['prompt']
    assert f"Right now you are away in {trip['city_name']}" in preview
    status = client.get('/api/chats').json()
    assert trip['city_name'] in str(status)


def test_the_postcard_comes_on_the_first_afternoon(client, mira, clock):
    from companion.characters import current
    reconcile(client)
    [trip] = listing(client)
    clock.advance(timedelta(days=12))  # Saturday noon: too early.
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        assert trips.postcard_due(connection, companion, clock.now()) == []
        later = clock.now() + timedelta(hours=4)
        [card] = trips.postcard_due(connection, companion, later)
    assert card.key == f"postcard:{trip['id']}" and card.kind == 'postcard'
    assert trip['city_name'] in card.template and trip['landmark']['name'] in card.template


def test_a_sunny_weekend_can_leave_them_sunburnt():
    entry = {'activity': 'trip-home-sun', 'place': None, 'trip': {'city': 'Miami'}}
    found = [body.after(f'seed-{index}', date(2026, 7, 6), [entry]) for index in range(40)]
    assert any(item and item['state'] == 'sunburnt' and item['because'] == 'after a sunny weekend in Miami'
               for item in found)
