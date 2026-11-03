"""Away together (companion/life/away_together.py, Hit List #86): trips the companion and the user take together,
asked in the chat or planned by them, that fit their era and their ship (Vanta, 2026-11-03)."""
from datetime import date, timedelta

import pytest
from conftest import reconcile, send
from test_long_distance import FREE_WEEK, agenda, planned
from test_together import mira, notes, says, where

from companion.characters import current
from companion.life import away_together, long_distance, trips


def test_trip_asks_are_read_from_the_message():
    assert away_together.asked('long weekend in Lisbon this spring?')['place'] == 'Lisbon'
    assert away_together.asked("let's go to Italy this summer")['place'] == 'Italy'
    found = away_together.asked('we need a getaway, somewhere warm')
    assert found['strong'] and found['place'] == ''
    assert away_together.asked('wanna take a trip to the cabin by the lake?')['place'] == 'the cabin by the lake'
    for text in ('I went to Lisbon last year', 'how was work?', "let's not go on vacation", 'I love Italy'):
        assert away_together.asked(text) is None, text


@pytest.fixture
def couple(client, monkeypatch):
    """Mira in Chicago, free every day, and close enough to go away together."""
    mira(client, monkeypatch, home_city='Chicago', timezone='America/Chicago', schedule=FREE_WEEK)
    monkeypatch.setattr(trips, 'ACTIVE', True)
    monkeypatch.setattr(trips, 'CHANCE', 0.0)
    monkeypatch.setattr(trips, 'LONG_CHANCE', 0.0)
    monkeypatch.setattr(away_together, 'SOON', 0)


def together_trips(client):
    return [trip for trip in planned(client) if trip['visit'] == away_together.TOGETHER]


def test_asking_for_a_weekend_away_books_one(client, couple, provider):
    says(provider)
    send(client, 'long weekend in Lisbon? I could use a break with you', 'client-away-1')
    [trip] = together_trips(client)
    assert trip['city_name'] == 'Lisbon' and trip['city_id'].endswith(':b-lisbon')
    assert trip['away']['by'] == 'plane'
    assert 'You agreed to go away together' in notes(provider)


def test_a_place_too_soon_or_out_of_their_world_is_turned_down(client, couple, provider, monkeypatch):
    monkeypatch.setattr(away_together, 'SOON', 9)
    says(provider)
    send(client, 'weekend away in Lisbon?', 'client-away-2')
    assert not together_trips(client)
    assert "you don't know each other well enough yet" in notes(provider)


def test_a_1925_world_cannot_go_to_cancun_but_goes_to_atlantic_city(client, monkeypatch, provider):
    mira(client, monkeypatch, home_city='new-york-1925', timezone='America/New_York', schedule=FREE_WEEK)
    monkeypatch.setattr(away_together, 'SOON', 0)
    says(provider)
    send(client, 'a week in Cancún?', 'client-away-3')
    assert not together_trips(client)
    assert 'no place for a holiday in your day' in notes(provider)
    says(provider)
    send(client, "let's take a trip to Atlantic City", 'client-away-4')
    [trip] = together_trips(client)
    assert trip['city_name'] == 'Atlantic City' and trip['away']['by'] == 'train'
    assert trip['city_id'].startswith('away:interwar:1925:')


def test_a_ship_goes_to_its_own_decks_and_not_to_italy(client, monkeypatch, provider):
    mira(client, monkeypatch, home_city='long-meridian', schedule=FREE_WEEK)
    monkeypatch.setattr(away_together, 'SOON', 0)
    says(provider)
    send(client, 'take me to Italy?', 'client-away-5')
    assert not together_trips(client)
    assert 'Italy is out of reach: you live aboard ship' in notes(provider)
    says(provider)
    send(client, 'we need a weekend away, just us', 'client-away-6')
    [trip] = together_trips(client)
    assert trip['away']['by'] in ('tram', 'lift', 'shuttle') and trip['city_id'].startswith('away:ship:')


def test_a_week_away_takes_vacation_days(client, monkeypatch, provider):
    mira(client, monkeypatch, home_city='Chicago', timezone='America/Chicago')
    monkeypatch.setattr(away_together, 'SOON', 0)
    from companion.life import work
    monkeypatch.setattr(work, 'ACTIVE', True)
    reconcile(client)  # Work life starts.
    says(provider)
    send(client, "let's go to Rome in January", 'client-away-7')
    [trip] = together_trips(client)
    assert trip['start_date'] >= '2027-01-01' and trip['away']['by'] == 'plane'
    days = (date.fromisoformat(trip['end_date']) - date.fromisoformat(trip['start_date'])).days + 1
    assert days == 5
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        off = work.vacation_dates(connection, companion, date.fromisoformat(trip['start_date']),
                                  date.fromisoformat(trip['end_date']))
    weekdays = {day for offset in range(days) if (day := date.fromisoformat(trip['start_date']) +
                                                  timedelta(days=offset)).weekday() < 5}
    assert {day.isoformat() for day in weekdays} <= set(off)


def test_their_own_idea_comes_as_news_and_runs_like_a_visit(client, couple, provider, clock, monkeypatch):
    monkeypatch.setattr(away_together, 'CHANCE', {1: 1.0, 2: 1.0, 3: 1.0})
    monkeypatch.setattr(away_together.together, 'close', lambda *_args: True)
    monkeypatch.setattr(long_distance, 'FIRST_TEXTS', True)
    reconcile(client)
    [trip] = together_trips(client)
    assert trip['company']['name'] == 'you'
    with client.app.state.database.connect() as connection:
        [trigger] = long_distance.news_due(connection, current(connection), clock.now())
    assert trigger.kind == 'visit_news' and 'You just booked a trip away for the two of you' in trigger.reason
    assert trigger.template[0].isupper() and trip['city_name'] in trigger.template
    start = date.fromisoformat(trip['start_date'])
    clock.advance(timedelta(days=(start - clock.now().date()).days, hours=4))  # 16:00 UTC, morning in Chicago.
    reconcile(client)
    found = where(client)
    assert found['state'] == 'together' and found['kind'] == 'away'
    assert found['text'] == f"Away {trip['away']['prep']} {trip['city_name']}"
    blocks = agenda(client, start.isoformat())
    assert any(block.get('trip') == trip['id'] for block, _entry in blocks)
    says(provider)
    send(client, 'this place is amazing', 'client-away-8')
    assert 'You and the user are away together' in notes(provider) and 'day 1 of' in notes(provider)
    end = date.fromisoformat(trip['end_date'])
    clock.advance(timedelta(days=(end - start).days + 1))
    reconcile(client)
    memories = client.get('/api/memories').json()
    found = [memory for memory in (memories if isinstance(memories, list) else memories.get('memories', []))
             if memory['subject'].startswith('Away together')]
    assert found and 'went away together' in found[0]['value']


def act(client, trip_id, action):
    return client.post(f'/api/life/trips/{trip_id}/{action}')


def test_somewhere_else_head_home_and_stay_on(client, couple, provider, clock):
    says(provider)
    send(client, 'weekend getaway somewhere by the sea?', 'client-away-9')
    [trip] = together_trips(client)
    moved = act(client, trip['id'], 'elsewhere')
    assert moved.status_code == 200, moved.text
    assert moved.json()['city_name'] != trip['city_name']
    start = date.fromisoformat(trip['start_date'])
    clock.advance(timedelta(days=(start - clock.now().date()).days, hours=4))
    assert act(client, trip['id'], 'elsewhere').status_code == 409
    home = act(client, trip['id'], 'home')
    assert home.status_code == 200, home.text
    assert home.json()['end_date'] == start.isoformat()
    stay = act(client, trip['id'], 'stay')
    assert stay.status_code == 200 and stay.json()['end_date'] == trip['end_date']
    act(client, trip['id'], 'home')
    clock.advance(timedelta(minutes=3))
    assert act(client, trip['id'], 'stay').status_code == 409


def test_cancel_and_undo_a_trip_together(client, couple, provider):
    says(provider)
    send(client, 'weekend away in Milwaukee?', 'client-away-10')
    [trip] = together_trips(client)
    assert act(client, trip['id'], 'cancel').status_code == 200
    assert [found['status'] for found in together_trips(client)] == ['cancelled']
    assert act(client, trip['id'], 'undo').status_code == 200
    assert [found['status'] for found in together_trips(client)] == ['planned']


def test_a_trip_moves_planned_vacation_days_rather_than_adding_more():
    from companion.life import work
    july = [f'2027-07-0{day}' for day in range(5, 10)]
    january = ['2027-01-04', '2027-01-05', '2027-01-06']
    found = work.moved(july, [('2026-10-05', january)])
    assert len(found) == len(july) and set(january) <= set(found)
    assert found[-2:] == july[-2:]
    assert work.moved(july, [('2027-08-01', january)]) == sorted(july + january)  # Booked after July: nothing to move.
