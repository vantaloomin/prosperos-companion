"""Townsfolk: seeded people at the city's places, run by rules, met by the companion while out."""
from datetime import date, datetime, timedelta

import pytest
from test_network import build
from test_social_circle import make

from companion.characters import require_current
from companion.life import body, encounters
from companion.world import catalog, naming, townsfolk


@pytest.fixture(autouse=True)
def steady(monkeypatch):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)


@pytest.fixture
def chatty(monkeypatch):
    monkeypatch.setattr(encounters, 'ACTIVE', True)
    monkeypatch.setattr(encounters, 'CHANCE', 1)
    monkeypatch.setattr(encounters, 'FAMILIAR_CHANCE', 1)


def test_every_place_has_its_own_people_rebuilt_the_same_from_their_key():
    for data in catalog.cities().values():
        for place in data['places']:
            people = townsfolk.at_place(data, place['id'])
            assert townsfolk.PEOPLE[0] <= len(people) <= townsfolk.PEOPLE[1]
            assert people == townsfolk.at_place(data, place['id'])
            for sheet in people:
                assert townsfolk.find(data, sheet['key']) == sheet
                assert not naming.is_invented(sheet['full'])
                assert sheet['flaw'] in townsfolk.FLAWS and sheet['desire'] in townsfolk.DESIRES
            if any(role[2] for role in townsfolk.ROLES.get(place['kind'], ())):
                assert people[0]['staff'] and people[0]['shifts']['days']
    data = catalog.city('baltimore')
    assert townsfolk.find(data, 'town:baltimore:nowhere:0') is None
    assert townsfolk.find(data, 'town:camelot:national-aquarium:0') is None
    assert townsfolk.at_place(data, 'nowhere') == []


def test_period_cities_get_period_jobs():
    data = catalog.city('camelot')
    roles = {sheet['role'] for place in data['places'] for sheet in townsfolk.at_place(data, place['id'])}
    assert 'barkeep' in roles and 'bartender' not in roles and 'barista' not in roles


def test_simple_rules_decide_where_they_are():
    data = catalog.city('baltimore')
    sheet = next(sheet for place in data['places'] for sheet in townsfolk.at_place(data, place['id'])
                 if sheet['staff'] and not sheet['night_owl'])
    day = date(2026, 10, 5)
    while day.weekday() not in sheet['shifts']['days']:
        day += timedelta(days=1)
    start = sheet['shifts']['window'][0]
    on_shift = townsfolk.whereabouts(sheet, data, datetime.combine(day, datetime.min.time())
                                     + timedelta(minutes=start + 30))
    assert on_shift['at_place'] and sheet['role'] in on_shift['doing']
    night = townsfolk.whereabouts(sheet, data, datetime(day.year, day.month, day.day, 3, 0))
    assert night == {'place': None, 'at_place': False, 'neighborhood': sheet['home'], 'doing': 'asleep',
                     'mood': night['mood']}
    regular = next(sheet for place in data['places'] for sheet in townsfolk.at_place(data, place['id'])
                   if not sheet['staff'] and sheet['visits']['part'] == 'afternoon')
    day = date(2026, 10, 5)
    while day.weekday() not in regular['visits']['days']:
        day += timedelta(days=1)
    visit = townsfolk.whereabouts(regular, data, datetime(day.year, day.month, day.day, 14, 0))
    assert visit['place']['id'] == regular['place']['id'] and 'usual spot' in visit['doing']


def test_goals_move_week_by_week_and_lead_to_the_next_one():
    data = catalog.city('baltimore')
    sheet = townsfolk.at_place(data, data['places'][0]['id'])[0]
    states = [townsfolk.story(sheet, data, townsfolk.EPOCH + timedelta(weeks=week)) for week in range(120)]
    assert states == [townsfolk.story(sheet, data, townsfolk.EPOCH + timedelta(weeks=week)) for week in range(120)]
    beats = {state['beat'] for state in states}
    assert {'progress', 'stall'} <= beats and 'achieved' in beats
    done = next(index for index, state in enumerate(states) if state['beat'] == 'achieved')
    assert states[done]['line'] and states[done]['reached'] and states[done]['goal'] != states[done - 1]['goal']
    assert townsfolk.story(sheet, data, date(2020, 1, 1))['beat'] == 'stall'


def test_the_city_view_lists_everyone_at_a_place(client):
    response = client.get('/api/world/cities/baltimore/places/national-aquarium/people', params={'at': '10:00'})
    assert response.status_code == 200, response.text
    people = response.json()
    assert people and all(person['story']['goal']['text'] and person['routine'] for person in people)
    assert client.get('/api/world/cities/baltimore/places/nowhere/people').status_code == 404


def test_the_companion_runs_into_townsfolk_and_learns_more_each_time(client, clock, chatty, monkeypatch):
    monkeypatch.setattr(encounters, 'KNOWS_HEART', 2)
    make(client, 'Warm and curious.')
    rows = build(client)
    met = [row for row in rows if row['entry'] and row['entry'].get('townsfolk')]
    assert met and 'Got talking with ' in met[0]['entry']['summary']
    assert len({row['local_date'] for row in met}) == len(met)
    assert client.get('/api/life/townsfolk').json() == []
    for _week in range(3):
        clock.instant = clock.now() + timedelta(days=7)
        build(client)
    known = client.get('/api/life/townsfolk').json()
    assert known and all(person['times'] >= 1 for person in known)
    often = max(known, key=lambda person: person['times'])
    assert often['times'] >= 2, known
    assert often['goal'] and often['flaw'] and often['desire'] and often['routine']
    once = [person for person in known if person['times'] == 1]
    assert all(person['goal'] is None and person['flaw'] is None for person in once)
    detail = client.get('/api/life/townsfolk/person', params={'key': often['key']})
    assert detail.status_code == 200 and detail.json()['now']['doing']
    assert client.get('/api/life/townsfolk/person', params={'key': 'town:baltimore:x:0'}).status_code == 404
    with client.app.state.database.connect() as connection:
        companion = require_current(connection)
        lines = encounters.context_lines(connection, companion, clock.now())
    recent = known[:encounters.CONTEXT_LIMIT]
    assert [key for key, _line in lines] == [person['key'] for person in recent]
    for (_key, line), person in zip(lines, recent, strict=True):
        assert person['full'] in line and ('trying to' in line) == bool(person['goal'])


def test_no_townsfolk_when_off(client):
    make(client, 'Warm and curious.')
    assert not any(row['entry'] and row['entry'].get('townsfolk') for row in build(client))
