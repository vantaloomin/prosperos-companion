"""A body that carries one day into the next: tiredness, hangovers, soreness and colds."""
from datetime import date, timedelta

import pytest
from conftest import reconcile

from companion.clock import parse
from companion.database import decode, encode
from companion.life import agenda, body, composer, routine
from companion.world.source import CatalogWorld

DAY = date(2026, 10, 7)
DEFINITION = {'name': 'Mira', 'location': 'Fells Point, Baltimore'}
SCHEDULE = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00', 'days': [0, 1, 2, 3, 4]},
            {'key': 'out', 'label': 'Evening', 'kind': 'social', 'start': '19:00', 'end': '22:00'},
            {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]


@pytest.fixture
def baltimore(client, monkeypatch):
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(composer, 'PLAN_SHARE', 0)
    monkeypatch.setattr(composer, 'THREAD_SHARE', 0)
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'America/New_York',
                                                     'location': 'Fells Point, Baltimore', 'schedule': SCHEDULE})
    assert response.status_code == 200, response.text
    return response.json()


def test_the_day_before_leaves_its_mark_deterministically():
    drinks = {'activity': 'drinks', 'place': {'name': 'The Owl Bar'}}
    states = [body.after(f'seed-{index}', DAY, [drinks]) for index in range(200)]
    assert states == [body.after(f'seed-{index}', DAY, [drinks]) for index in range(200)]
    found = {state['state'] for state in states if state}
    assert found == {'hungover', 'tired'}
    assert all(state['because'] == 'after drinks at The Owl Bar last night' for state in states if state)
    assert None in states
    # A quiet day leaves nothing behind.
    assert body.after('seed', DAY, [{'activity': 'reading', 'place': None}]) is None


def test_a_cold_lasts_a_few_days_and_comes_more_often_in_winter():
    world = CatalogWorld()
    january, july = date(2027, 1, 1), date(2027, 7, 1)
    def sick_days(start, seeds):
        return sum(body.sick(seed, start + timedelta(days=offset), world, DEFINITION)
                   for seed in seeds for offset in range(56))
    seeds = [f'subject-{index}' for index in range(60)]
    assert sick_days(january, seeds) > sick_days(july, seeds) > 0
    for seed in seeds:
        days = [offset for offset in range(120) if body.sick(seed, january + timedelta(days=offset), world, DEFINITION)]
        runs, previous = [], None
        for offset in days:
            if previous is not None and offset == previous + 1:
                runs[-1] += 1
            else:
                runs.append(1)
            previous = offset
        # A run cut off by the window's edges can look shorter.
        inner = runs[1:-1] if days and (days[0] == 0 or days[-1] == 119) else runs
        assert all(run in {2, 3, 4, 5, 6} for run in inner)


def test_a_sick_day_stays_home_and_a_low_evening_stays_small():
    sick = body.apply({'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00'},
                      {'state': 'sick', 'because': 'came down with a cold'})
    assert sick['kind'] == 'rest' and sick['sick_day'] and sick['label'] == 'Sick day (no work)'
    slot = {'key': 'work@2026-10-07', 'local_date': '2026-10-07', 'block': sick}
    event = composer.compose(slot, DEFINITION, CatalogWorld(), 'seed-1')
    assert event['activity'] == 'sick-day' and 'cold' in event['summary'] and event['place'] is None
    tired = {'key': 'out', 'label': 'Evening', 'kind': 'social', 'start': '19:00', 'end': '22:00',
             'body': {'state': 'tired', 'because': 'after a late show'}}
    for index in range(40):
        found = composer.compose({'key': f'out@{index}', 'local_date': '2026-10-07', 'block': tired}, DEFINITION,
                                 CatalogWorld(), f'seed-{index}')
        assert found is None or found['activity'] in composer.CALM


def test_the_agenda_carries_the_state_into_the_day_and_the_chat(client, baltimore, clock, monkeypatch):
    monkeypatch.setattr(body, 'AFTER', {key: (('tired', 1.0),) for key in body.AFTER})
    monkeypatch.setattr(body, 'COLD_CHANCE', {'winter': 0, 'other': 0})
    # How they feel is a hidden value; Today shows it only with moods shown.
    assert client.put('/api/settings', json={'show_moods': True}).status_code == 200
    clock.advance(timedelta(days=3))
    reconcile(client)
    with client.app.state.database.connect() as connection:
        rows = [dict(row) for row in connection.execute(
            "SELECT * FROM life_agenda WHERE subject='companion' AND entry IS NOT NULL ORDER BY starts_at")]
    marked = [row for row in rows if decode(row['block']).get('body')]
    assert marked
    for row in marked:
        previous = [decode(other['entry'])['activity'] for other in rows
                    if other['local_date'] == (date.fromisoformat(row['local_date']) - timedelta(days=1)).isoformat()]
        assert set(previous) & set(body.AFTER)
    today = client.get('/api/today').json()
    with client.app.state.database.connect() as connection:
        expected = agenda.day_on(connection, baltimore['active_timeline_id'], today['day']['date'])['body']
    assert today['day']['body'] == expected
    if expected:
        assert body.text(expected) in client.get('/api/context/preview').json()['system']


def test_a_sick_friend_is_not_free(client, baltimore, clock):
    clock.advance(timedelta(days=1))
    reconcile(client)
    with client.app.state.database.connect(write=True) as connection:
        person = dict(connection.execute("SELECT * FROM life_agenda WHERE subject!='companion' LIMIT 1").fetchone())
        block = {**decode(person['block']), 'kind': 'rest', 'sick_day': True}
        connection.execute('UPDATE life_agenda SET block=? WHERE timeline_id=? AND subject=?',
                           (encode(block), person['timeline_id'], person['subject']))
        slot = routine.Slot(routine.Block('x', 'X', 'social', tuple(range(7)), parse(person['starts_at']).time(),
                                          parse(person['ends_at']).time(), ()), date.today(),
                            parse(person['starts_at']), parse(person['ends_at']))
        assert person['subject'] not in {free['id'] for free in agenda.free_people(connection, person['timeline_id'], slot)}
