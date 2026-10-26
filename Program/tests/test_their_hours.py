"""Their hours and yours (companion/life/their_hours.py): a new companion's week fits the user's evenings, an older
world's companions are fitted once, Live on my clock moves their week onto the user's time and keeps it in step, and
"Somewhere new" leans toward cities near the user's clock."""
from datetime import UTC, date, datetime, timedelta

from conftest import send
from test_texting import says
from test_together import notes

from companion import worlds
from companion.characters import current
from companion.life import their_hours
from companion.world import generators

WORK = [{'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'},
        {'key': 'work', 'label': 'Studio', 'kind': 'work', 'days': [0, 1, 2, 3, 4], 'start': '09:00', 'end': '17:00'},
        {'key': 'evening', 'label': 'Evening', 'kind': 'leisure', 'start': '18:00', 'end': '22:00'}]


def my_zone(client, name='America/New_York'):
    response = client.put('/api/settings', json={'user_timezone': name, 'user_timezone_source': 'chosen'})
    assert response.status_code == 200, response.text


def make(client, **values):
    response = client.post('/api/companion', json={'name': 'Mei', **values})
    assert response.status_code == 200, response.text
    return response.json()


def week(companion):
    return {block['key']: (block['start'], block['end'], block['days'])
            for block in companion['version']['definition']['schedule']}


def revise(client, companion, mode):
    definition = {**companion['version']['definition'], 'their_hours': {
        **(companion['version']['definition'].get('their_hours') or {}), 'mode': mode}}
    response = client.post('/api/companion/versions', json={'definition': definition, 'note': '',
                                                            'expected_version_id': companion['active_version_id']})
    assert response.status_code == 200, response.text
    return response.json()


def test_a_week_moves_with_its_days():
    moved = their_hours.shifted([{'key': 'work', 'label': 'Work', 'kind': 'work', 'days': [0, 6], 'start': '09:00',
                                  'end': '17:00'}], 16 * 60)
    assert moved[0] | {} == {'key': 'work', 'label': 'Work', 'kind': 'work', 'days': [0, 1], 'start': '01:00',
                             'end': '09:00'}
    assert their_hours.shifted([{'key': 'a', 'label': 'A', 'kind': 'sleep', 'days': [0], 'start': '01:00',
                                 'end': '09:00'}], -120)[0]['days'] == [6]
    assert their_hours.gap('Asia/Tokyo', 'America/New_York', datetime(2026, 10, 5, tzinfo=UTC)) == 13 * 60
    assert their_hours.gap('Asia/Tokyo', 'America/New_York', datetime(2026, 12, 5, tzinfo=UTC)) == 14 * 60


def test_a_new_companion_far_away_gets_hours_that_fit_your_evenings(client):
    my_zone(client)
    day = date(2026, 10, 5)
    # Asleep through a New York evening in London (a night owl now); at work through it in Tokyo (odd hours).
    for zone, why in (('Europe/London', 'night_owl'), ('Asia/Tokyo', 'remote')):
        assert their_hours.covered(their_hours.written({'schedule': WORK}), zone, 'America/New_York', day) > \
            their_hours.CLASH
        made = client.post('/api/companion' if zone == 'Europe/London' else '/api/companion/another',
                           json={'name': 'Mei', 'timezone': zone, 'schedule': WORK}).json()
        hours = made['version']['definition']['their_hours']
        assert (hours['mode'], hours['why']) == ('fit', why) and hours['shift'] == hours['fit'] != 0
        schedule = made['version']['definition']['schedule']
        assert their_hours.covered(schedule, zone, 'America/New_York', day) <= 1 - their_hours.FREE + 1e-9
    # A companion in the user's own zone keeps their week.
    same = client.post('/api/companion/another', json={'name': 'Sam', 'timezone': 'America/New_York', 'schedule': WORK})
    assert same.json()['version']['definition'].get('their_hours') is None


def test_with_your_zone_unknown_nothing_moves(client):
    made = make(client, timezone='Europe/London', schedule=WORK)  # The zone is still the default: nothing to fit to.
    assert made['version']['definition'].get('their_hours') is None


def test_live_on_my_clock_moves_their_week_and_back(client, clock):
    my_zone(client)
    made = make(client, timezone='Asia/Tokyo', schedule=WORK)
    fit = made['version']['definition']['their_hours']['fit']
    mine = revise(client, made, 'mine')
    hours = mine['version']['definition']['their_hours']
    assert (hours['mode'], hours['shift'], hours['zone'], hours['why']) == ('mine', 13 * 60, 'America/New_York',
                                                                          'mine')
    assert week(mine)['night'][:2] == ('12:00', '20:00')  # 23:00 to 07:00 in New York.
    back = revise(client, mine, 'fit')
    assert back['version']['definition']['their_hours']['shift'] == fit
    assert week(back) == week(made)
    city = revise(client, back, 'city')
    assert week(city)['night'][:2] == ('23:00', '07:00')
    assert city['version']['definition']['their_hours']['mode'] == 'city'


def test_on_my_clock_keeps_in_step_with_daylight_saving(client, clock):
    my_zone(client)
    mine = revise(client, make(client, timezone='Asia/Tokyo', schedule=WORK), 'mine')
    with client.app.state.database.connect(write=True) as connection:
        assert their_hours.settle_all(connection, clock.now()) == 0
        later = clock.now() + timedelta(days=40)  # New York is off daylight saving; Tokyo never has it.
        assert their_hours.settle_all(connection, later) == 1
        moved = current(connection)
    assert moved['version']['definition']['their_hours']['shift'] == 14 * 60
    assert moved['version']['note'] == their_hours.NOTE['step']
    assert {block['key']: block['start'] for block in moved['version']['definition']['schedule']}['night'] == '13:00'
    assert week(mine)['night'][0] == '12:00'


def test_an_older_world_is_fitted_once(client, clock):
    made = make(client, timezone='Europe/London')  # The gentle default day, asleep through New York's evenings.
    assert made['version']['definition'].get('their_hours') is None
    my_zone(client)
    with client.app.state.database.connect(write=True) as connection:
        assert their_hours.settle_all(connection, clock.now()) == 1
        fitted = current(connection)
        assert fitted['version']['definition']['their_hours']['mode'] == 'fit'
        assert fitted['version']['note'] == their_hours.NOTE['fit']
        assert their_hours.settle_all(connection, clock.now()) == 0


def test_their_chat_knows_why_their_hours_are_odd(client, provider):
    my_zone(client)
    make(client, timezone='Asia/Tokyo', home_city='osaka', schedule=WORK)
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    says(provider, 'hey')
    send(client, 'hi', 'client-hours-1')
    hours = None
    with client.app.state.database.connect() as connection:
        hours = current(connection)['version']['definition']['their_hours']
    assert their_hours.WHY[hours['why']].format(city='Osaka')[:30] in notes(provider)


def test_somewhere_new_leans_toward_cities_near_your_clock(client, monkeypatch):
    my_zone(client)
    rolls = {'osaka': 0.8, 'long-meridian': 0.5, 'grandport': 0.4}
    monkeypatch.setattr(generators, 'unit', lambda city_id, *_args: rolls[city_id])
    with client.app.state.database.connect() as connection:
        picked = worlds.somewhere_new(connection, 'baltimore', 'seed', datetime(2026, 10, 5, tzinfo=UTC))
        # Osaka rolled highest, but The Long Meridian is four hours from New York and Osaka thirteen.
        assert picked == 'long-meridian'
        assert worlds.somewhere_new(connection, 'baltimore', 'seed') == 'osaka'  # Without a clock, no lean.
