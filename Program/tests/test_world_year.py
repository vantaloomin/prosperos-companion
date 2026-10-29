"""The year a world runs in (companion/world_year.py): Back when's past-year clock, per world."""
import importlib
import json
import re
import time
from datetime import date, timedelta
from pathlib import Path

import pytest
from conftest import START

from companion import world_year, worlds
from companion.characters import require_current
from companion.clock import parse
from companion.mcp import lookups
from companion.memory import context
from companion.world import catalog, generators

# Every seeded part of a companion's life that conftest turns off for unrelated tests, as this module found them.
LIFE = ('life.storylines.START', 'life.occasions.SEEDED', 'life.disruptions.ACTIVE', 'life.network.ACTIVE',
        'life.encounters.ACTIVE', 'life.openers.CHECK_INS', 'life.wardrobe.WEAVE', 'life.grooming.WEAVE',
        'life.kitchen.WEAVE', 'life.media.WEAVE', 'life.hobbies.WEAVE', 'life.hobbies.NEWS', 'life.deck.ACTIVE',
        'life.dreams.ACTIVE', 'world.turnover.ACTIVE', 'life.circle.ELDERS', 'life.families.ACTIVE',
        'life.kids.ACTIVE', 'life.family_tree.ACTIVE', 'life.big_days.ACTIVE', 'life.trips.ACTIVE',
        'life.work.ACTIVE', 'life.shifts.ACTIVE', 'life.admin.ACTIVE', 'life.rough_patches.ACTIVE',
        'life.breakups.ACTIVE')
ORIGINAL = {name: getattr(importlib.import_module('companion.' + name.rsplit('.', 1)[0]), name.rsplit('.', 1)[1])
            for name in LIFE}
# The world runs 17 years back: START (5 October 2026) is 5 October 2009 there.
YEAR = 2009
THEN = START - timedelta(days=(date(2026, 10, 5) - date(2009, 10, 5)).days)


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def past_world(client, year=YEAR) -> dict:
    return ok(client.post('/api/worlds', json={'year': year}))


def enter(client, world: dict):
    ok(client.post(f"/api/worlds/{world['id']}/switch"))


def test_a_past_year_is_the_same_day_then():
    assert world_year.same_day(date(2026, 10, 28), 2009) == date(2009, 10, 28)
    assert world_year.same_day(date(2028, 2, 29), 2009) == date(2009, 2, 28)
    assert world_year.offset_days(2009, date(2026, 10, 5)) == (date(2026, 10, 5) - date(2009, 10, 5)).days


@pytest.mark.parametrize('year', [1989, 2026, 2030])
def test_a_past_year_runs_from_1990_to_last_year(client, companion, year):
    assert client.post('/api/worlds', json={'year': year}).status_code == 422
    assert len(ok(client.get('/api/worlds'))['personas'][0]['worlds']) == 1


def test_a_world_started_in_a_past_year_runs_there_at_real_speed(client, companion, clock, app):
    world = past_world(client)
    assert world['year'] == YEAR and not world['active']
    assert ok(client.get('/api/worlds'))['world']['year'] is None  # The world the user is in stays in the present.
    assert parse(ok(client.get('/api/debug-time'))['now']) == START
    enter(client, world)
    status = ok(client.get('/api/debug-time'))
    assert parse(status['now']) == THEN and status['years_back'] == 17 and status['active'] is False
    assert parse(status['real_now']) == START
    clock.advance(timedelta(hours=5))
    database = app.state.database
    assert database.clock.now() == THEN + timedelta(hours=5)
    assert world_year.world_year(database) == YEAR and world_year.view(database)['started_year'] == YEAR
    # Its own stamps are from then: the persona written on entering, the world's settings.
    with database.connect() as connection:
        assert connection.execute('SELECT updated_at FROM persona WHERE id=1').fetchone()[0].startswith('2009-10-05')
        assert connection.execute('SELECT created_at FROM world_year').fetchone()[0].startswith('2009-10-05')
    first = next(item for item in ok(client.get('/api/worlds'))['personas'][0]['worlds'] if item['first'])
    enter(client, first)
    assert database.clock.now() == START + timedelta(hours=5)


def test_work_pinned_to_a_world_keeps_its_year(client, companion, app):
    database = app.state.database
    first = database.path
    world = past_world(client)
    with database.pin():
        enter(client, world)  # The switch follows the user; work pinned before it stays where it began.
    assert database.clock.now() == THEN
    with database.pin():
        assert database.clock.now() == THEN
    database.use(first)
    assert database.clock.now() == START


def test_debug_time_runs_on_top_of_the_year(client, companion, app):
    enter(client, past_world(client))
    ok(client.post('/api/debug-time/start', json={}))
    ok(client.post('/api/debug-time/jump', json={'hours': 3}))
    deadline = time.monotonic() + 60
    while ok(client.get('/api/debug-time'))['jumping'] and time.monotonic() < deadline:
        time.sleep(0.05)
    assert parse(ok(client.get('/api/debug-time'))['now']) == THEN + timedelta(hours=3)
    ok(client.post('/api/debug-time/finish', json={}))
    assert parse(ok(client.get('/api/debug-time'))['now']) == THEN


def test_real_world_lookups_stay_off_in_a_past_year(client, companion, app):
    database = app.state.database
    with database.connect() as connection:
        assert lookups.target(connection, 'conversation', None, database.clock.now()) is not None
    enter(client, past_world(client))
    with database.connect() as connection:
        for purpose in ('conversation', 'ambient', 'companion_city'):
            assert lookups.target(connection, purpose, None, database.clock.now()) is None
        assert world_year.past(connection)


def chat_prompt(app) -> str:
    database = app.state.database
    with database.connect() as connection:
        packet = context.build(connection, require_current(connection), database.clock.now(), 6000)
    return packet['system'] + '\n' + packet['note']


def test_a_chat_in_a_past_year_says_the_year_and_how_people_keep_in_touch(client, companion, app):
    assert '## The year' not in chat_prompt(app)  # Nothing changes in a present world's chats.
    enter(client, past_world(client))
    ok(client.post('/api/companion', json={'name': 'Dana', 'personality': 'Warm', 'timezone': 'America/New_York'}))
    prompt = chat_prompt(app)
    section = prompt.split('## The year', 1)[1].split('\n## ', 1)[0]
    assert "It's October 2009." in section and 'flip phone' in section and world_year.UNHEARD in section
    assert not [year for year in re.findall(r'\b(?:19|20)\d\d\b', prompt) if int(year) > YEAR]


def test_the_year_stays_out_of_a_city_of_another_era(client, companion, app):
    enter(client, past_world(client))
    ok(client.post('/api/companion', json={'name': 'Rosa', 'personality': 'Warm', 'timezone': 'America/New_York',
                                           'home_city': 'new-york-1925'}))
    assert '## The year' not in chat_prompt(app)


def test_every_year_back_to_1990_says_how_people_keep_in_touch():
    for year in range(world_year.EARLIEST, 2026):
        assert world_year.keeping_in_touch(year), year
    spans = world_year.spans()
    assert all(left['to'] + 1 == right['from'] for left, right in zip(spans, spans[1:]))


def test_making_a_past_world_leaves_the_present_ones_clocks_alone(client, companion, app):
    from companion.clock import app_now
    from companion.world import turnover
    past_world(client)
    assert app_now() == START and turnover.STATE.clock.now() == START


def test_lunar_and_equinox_holidays_are_listed_back_to_1990():
    years = {str(year) for year in range(world_year.EARLIEST, 2041)}
    calendars = json.loads((Path(catalog.__file__).parent / 'data' / 'holidays.json').read_text('utf-8'))['calendars']
    for holiday in calendars['south-korea']['holidays'] + calendars['japan']['holidays']:
        if 'dates' in holiday and holiday['id'] != 'citizens-holiday':
            assert years <= set(holiday['dates']), holiday['id']
    chuseok = next(item for item in calendars['south-korea']['holidays'] if item['id'] == 'chuseok')
    assert generators.holiday_date(chuseok, 2009) == date(2009, 10, 3)
    silver = next(item for item in calendars['japan']['holidays'] if item['id'] == 'citizens-holiday')
    assert {'2009', '2015'} <= set(silver['dates'])


def test_moon_and_feast_observances_are_listed_back_to_1990():
    from companion.almanac import days
    for item in days.data()['days']:
        table = item['on'].get('dates')
        if table and item['id'] != 'election-day':
            assert {str(year) for year in range(1990, 2031)} <= set(table), item['id']
    assert {str(year) for year in range(1990, 2031, 2)} <= set(
        next(item for item in days.data()['days'] if item['id'] == 'election-day')['on']['dates'])


# Any date from the year after the world's own on. A month in October 2009 plans into 2010 at most (a wedding, a
# lease); a date from 2011 on came from real time, not the world's.
LEAK = re.compile(r'\b(20[1-9]\d)-\d\d-\d\d')


# What follows the user from world to world keeps the stamps of the world it was set in (companion/worlds.py SHARED),
# and debug time records real time on purpose.
FROM_ELSEWHERE = {*worlds.SHARED, 'debug_time'}


def leaks(connection, after: int) -> list[str]:
    found = []
    tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    for table in (name for name in tables if name not in FROM_ELSEWHERE):
        columns = [row[1] for row in connection.execute(f'PRAGMA table_info({table})')]
        for row in connection.execute(f'SELECT * FROM {table}'):  # noqa: S608
            for column, value in zip(columns, row, strict=True):
                if isinstance(value, str):
                    years = [int(year) for year in LEAK.findall(value)]
                    if any(year > after for year in years):
                        found.append(f'{table}.{column}: {value[:160]}')
    return found


def test_a_month_in_2009_never_stamps_a_later_date(client, life, app, monkeypatch):
    """Item 1's guard (1.2 plan, risks): walk a 2009 world for a month with its whole life on, and fail on any
    stored date the world could not know yet."""
    for name, value in ORIGINAL.items():
        module, attribute = name.rsplit('.', 1)
        monkeypatch.setattr(f'companion.{module}.{attribute}', value)
    from companion import debug_time
    monkeypatch.setattr(debug_time, 'STEP', timedelta(hours=2))
    world = past_world(client)
    enter(client, world)
    ok(client.post('/api/companion', json={'name': 'Mira', 'personality': 'Warm and curious',
                                           'timezone': 'America/New_York'}))
    ok(client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                           'api_key': 'secret-key'}))
    ok(client.put('/api/settings', json={'background_activity': True}))
    ok(client.post('/api/conversation/messages', json={'text': 'Hi! What are you up to?', 'client_id': 'client-0001'}))
    ok(client.post('/api/debug-time/start', json={}))
    ok(client.post('/api/debug-time/jump', json={'hours': 24 * 30}))
    deadline = time.monotonic() + 900
    while ok(client.get('/api/debug-time'))['jumping'] and time.monotonic() < deadline:
        time.sleep(0.2)
    status = ok(client.get('/api/debug-time'))
    assert status['jumping'] is None and parse(status['now']) == THEN + timedelta(days=30)
    with app.state.database.connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM life_events').fetchone()[0] > 0
        found = leaks(connection, YEAR + 1)
    assert not found, '\n'.join(found[:40])
