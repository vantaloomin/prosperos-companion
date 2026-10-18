"""The town changes hands, seen from the app (companion/world/turnover.py): someone who has left is nowhere in town,
can't take over or be become, a match who left can't be met on a date, a newcomer is their age from the day they
arrived, and the paper and a companion's losses read the companion's own town."""
from datetime import UTC, date, datetime, time, timedelta

import pytest
from test_cast import chatty, met_someone, ok, steady  # noqa: F401 (fixtures)
from test_dating import PROFILE
from test_drafting import connect

from companion import dating as matchlight
from companion.characters import require_current
from companion.life import ages, citymap, encounters, network, web
from companion.world import paper, townsfolk, turnover


@pytest.fixture(autouse=True)
def active(monkeypatch):
    monkeypatch.setattr(turnover, 'ACTIVE', True)


def town(client) -> dict:
    with client.app.state.database.connect() as connection:
        return network.city(connection, require_current(connection))


def after(clock, found: dict):
    """Moves the app clock to a week after they left."""
    clock.instant = datetime.combine(date.fromisoformat(found['day']) + timedelta(days=7), time(12), UTC)


def test_someone_who_left_is_nowhere_in_town_and_cant_take_over(client, clock, chatty):  # noqa: F811
    _mira, person = met_someone(client, clock)
    data = town(client)
    found = townsfolk.gone(townsfolk.find(data, person['key']), data, clock.now().date() + timedelta(days=36500))
    assert found
    after(clock, found)
    seen = ok(client.get('/api/life/townsfolk/person', params={'key': person['key']}))
    assert seen['now'] is None
    known = next(item for item in ok(client.get('/api/life/townsfolk')) if item['key'] == person['key'])
    assert known['left'] is None or known['left']['day'] == found['day']
    for response in (client.get('/api/companion/cast/draft', params={'key': person['key']}),
                     client.post('/api/worlds/become', json={'key': person['key']})):
        assert response.status_code == 409 and 'has ' in response.json()['detail'], response.text


def test_the_map_and_who_knows_who_leave_out_where_someone_used_to_be(monkeypatch):
    regular = {'key': 'town:x:bar:2', 'name': 'Dana', 'full': 'Dana Ruiz', 'kind': 'regular', 'staff': False,
               'role': 'regular', 'place': {'id': 'bar', 'name': 'The Bar'}, 'neighborhood': 'Canton'}
    staff = [{**regular, 'key': f'town:x:bar:{n}', 'name': f'Sam{n}', 'staff': True, 'role': 'barkeep',
              'first_place': 'The Bar'} for n in (0, 1)]
    left = {'why': 'moved', 'day': '2028-01-03', 'text': 'moved away'}
    graph = web.Web()
    graph.add('companion:1', 'Mira', 'companion')
    web.add_townsfolk(graph, 'companion:1', [staff[0] | {'left': left}, staff[1]])
    assert not [link for link in graph.links.values() if link['kind'] == 'work']
    assert graph.nodes[staff[0]['key']]['detail'] == 'barkeep at The Bar; has since moved away'
    monkeypatch.setattr(encounters, 'known', lambda *_args: [regular, regular | {'key': 'town:x:bar:3', 'name': 'Lee',
                                                                                  'left': left}])
    assert citymap.regulars(None, {}, None) == {'bar': ['Dana']}


def test_a_match_who_left_town_cant_be_met_on_a_date(client, clock):
    connect(client)
    ok(client.put('/api/debug-matches', json={'on': True}))
    ok(client.put('/api/settings', json={'story_mode': True}))
    state = ok(client.put('/api/dating/profile', json=PROFILE))
    leaving = None
    while state['deck'] and leaving is None:
        key = state['deck'][0]['key']
        state = ok(client.post('/api/dating/swipes', json={'key': key, 'like': True}))
        with client.app.state.database.connect() as connection:
            sheet, data = matchlight.person(connection, key, '')
        found = townsfolk.gone(sheet, data, clock.now().date() + timedelta(days=36500))
        leaving = (key, found) if found else None
    assert leaving
    key, found = leaving
    match = next(item for item in ok(client.get('/api/dating'))['matches'] if item['key'] == key)
    assert match['left'] is None
    after(clock, found)
    match = next(item for item in ok(client.get('/api/dating'))['matches'] if item['key'] == key)
    assert match['left']['day'] == found['day']
    refused = client.post('/api/dating/dates', json={'key': key, 'place_id': match['places'][0]['id']})
    assert refused.status_code == 409 and 'has ' in refused.json()['detail']
    assert client.get('/api/companion/cast/draft', params={'key': key}).status_code == 409


def test_the_paper_reads_the_companions_own_town(client, clock, chatty, monkeypatch):  # noqa: F811
    mira, person = met_someone(client, clock)
    ok(client.post('/api/companion/town', json={'fresh': True}))
    seen = {}

    def issue(_connection, data, _world, day):
        seen.update(data)
        return {'townsfolk': []}
    monkeypatch.setattr(paper, 'issue', issue)
    ok(client.get('/api/life/paper'))
    assert seen['town'] and 'kept' in seen and seen['town'] == town(client)['town']


def test_a_companion_hears_of_a_loss_in_their_own_town(client, clock, chatty, monkeypatch):  # noqa: F811
    from companion.life import loss
    met_someone(client, clock)
    ok(client.post('/api/companion/town', json={'fresh': True}))
    towns = []
    monkeypatch.setattr(encounters, 'history_for', lambda _c, _companion, _cast, _now: towns.append(_cast) or {})
    resolved = []
    real = encounters.town_cast

    def cast(connection, companion, data):
        resolved.append(data.get('town'))
        return real(connection, companion, data)
    monkeypatch.setattr(encounters, 'town_cast', cast)
    with client.app.state.database.connect(write=True) as connection:
        companion = require_current(connection)
        loss.town(connection, companion, clock.now().date(), clock.now())
    assert resolved == [companion['town_seed']] and resolved[0]


def test_a_newcomer_is_their_age_from_the_day_they_arrived(monkeypatch):
    monkeypatch.setattr(ages, 'stored', lambda *_args: None)
    monkeypatch.setattr(ages, 'town_began', lambda _connection: date(2026, 10, 19))
    sheet = {'key': 'town:x:bar:1001', 'seed': 'x', 'age': 30, 'arrived': '2034-03-06'}
    assert ages.town_age(None, sheet, date(2034, 3, 6)) == 30
    assert ages.town_age(None, sheet, date(2036, 3, 6)) in (31, 32)
    assert ages.town_age(None, sheet | {'arrived': None}, date(2034, 3, 6)) >= 37


def test_changing_the_sliders_moves_the_town_on_from_then_and_keeps_its_past(client, clock, chatty):  # noqa: F811
    met_someone(client, clock)
    data = town(client)
    first = [sheet for place in data['places'] for sheet in townsfolk.at_place(data, place['id'], turnover.START)]
    clock.instant = datetime.combine(turnover.START + timedelta(days=3 * 365), time(12), UTC)
    today = clock.now().date()

    def departures(until):
        return {sheet['key']: found['day'] for sheet in first
                if (found := townsfolk.gone(sheet, data, until))}
    past, future = departures(today), departures(today + timedelta(days=30 * 365))
    staff_now = {place['id']: [sheet['key'] for sheet in townsfolk.at_place(data, place['id'], today)]
                 for place in data['places']}
    for body in ({'life_turns': 3}, {'people_pass_away': True, 'loss': 3}, {'life_turns': 0, 'people_pass_away': False}):
        ok(client.put('/api/life/settings', json=body))
        assert departures(today) == past
        assert {place['id']: [sheet['key'] for sheet in townsfolk.at_place(data, place['id'], today)]
                for place in data['places']} == staff_now
    # With Life's big turns at none nobody else leaves, once the year of their stay under way has run out.
    assert departures(today + timedelta(days=30 * 365)) != future
    assert all(day <= (today + timedelta(days=372)).isoformat()
               for day in departures(today + timedelta(days=30 * 365)).values())
