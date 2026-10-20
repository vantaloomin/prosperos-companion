"""Visits with the other parent (companion/life/stays.py): planned stays for every co-parenting case, on the calendar
and Today with Move and Skip, in the chat context, across cities and asked for in the chat."""
from datetime import date, timedelta

import pytest
from conftest import intimate, send
from test_expecting import likeliest  # noqa: F401 - a fixture
from test_kids import make
from test_our_child import aged, born, connect, ours
from test_steps import prompt, says

from companion.characters import current
from companion.life import breakups, custody, kids, stays, steps, together

pytestmark = pytest.mark.usefixtures('likeliest')


@pytest.fixture
def split(client, provider, clock, monkeypatch):
    """A child of the pair, two hundred days old, and the user ending it in the chat (as tests/test_custody.py)."""
    monkeypatch.setattr(breakups, 'ACTIVE', True)
    _row, child = born(client, clock, monkeypatch)
    aged(client, child, 1500)  # Past three: weekends away (a younger child has a day, `daytime`).
    says(provider)
    send(client, "I'm breaking up with you.", 'client-stays-split')
    return child


def plan(client) -> list[dict]:
    """Plan the stays now, and every stay there is."""
    database = client.app.state.database
    with database.connect(write=True) as connection:
        stays.plan_ahead(connection, current(connection), database.clock.now())
    return rows(client)


def rows(client) -> list[dict]:
    with connect(client) as connection:
        return [dict(row) for row in connection.execute('SELECT * FROM family_stays ORDER BY start_date')]


def today(client) -> date:
    with connect(client) as connection:
        return steps.local_today(current(connection), client.app.state.database.clock.now())


def act(client, stay_id: str, action: str, status: int = 200) -> dict:
    response = client.post(f'/api/life/admin/stays/{stay_id}/{action}')
    assert response.status_code == status, response.text
    return response.json()


def level(client, value: int) -> None:
    with client.app.state.database.connect(write=True) as connection:
        connection.execute('UPDATE life_settings SET together_realism=? WHERE id=1', (value,))


# The user and a companion who split up ---------------------------------------------------------------------------------

def test_every_other_weekend_with_the_user_is_planned_by_the_custody_pattern(client, split):
    ours(client, custody='with_them')
    found = plan(client)
    weekends = [row for row in found if row['reason'] == 'rota']
    assert weekends and all(row['host'] == 'you' and row['family'] == 'ours' for row in weekends)
    with connect(client) as connection:
        state = {**custody.found(connection, current(connection)), 'stays': None}
    for row in weekends:
        start, end = date.fromisoformat(row['start_date']), date.fromisoformat(row['end_date'])
        assert start.weekday() == 5 and end == start + timedelta(days=1)
        assert not custody.with_them(state, start) and not custody.with_them(state, end)
    assert len({row['start_date'] for row in weekends}) == len(weekends)
    assert plan(client) == found  # Planned once.


def test_a_child_under_three_has_a_day_with_the_other_parent_and_the_rest_at_home(client, split):
    aged(client, split, 600)
    ours(client, custody='with_them')
    days = [row for row in plan(client) if row['reason'] == 'rota']
    assert days and all(row['start_date'] == row['end_date'] and row['first_end'] > row['start_date'] for row in days)
    with connect(client) as connection:
        companion = current(connection)
        assert not custody.here(connection, companion, date.fromisoformat(days[0]['start_date']))
        assert custody.here(connection, companion, date.fromisoformat(days[0]['first_end']))
    name = split['name'].split()[0]
    titles = [item['title'] for item in client.get('/api/life/admin').json()['upcoming'] if item['source'] == 'family']
    assert titles[0] == f"{name}'s Saturday with you"


def test_half_and_half_is_a_week_at_a_time_and_has_no_summer_week(client, split):
    ours(client, custody='shared')
    level(client, 3)
    found = plan(client)
    weeks = [row for row in found if row['reason'] == 'rota']
    assert weeks and all((date.fromisoformat(row['end_date']) - date.fromisoformat(row['start_date'])).days == 6
                         for row in weeks)
    assert not [row for row in found if row['reason'] == 'summer']


def test_where_they_live_changing_replans_the_stays(client, split):
    ours(client, custody='with_them')
    assert {row['host'] for row in plan(client)} == {'you'}
    ours(client, custody='with_you')
    found = [row for row in plan(client) if row['start_date'] > today(client).isoformat()]
    assert found and {row['host'] for row in found} == {'companion'}


def test_stays_show_on_the_calendar_and_today(client, split):
    ours(client, custody='with_them')
    plan(client)
    name = split['name'].split()[0]
    upcoming = [item for item in client.get('/api/life/admin').json()['upcoming'] if item['source'] == 'family']
    assert upcoming and upcoming[0]['title'] == f"{name}'s weekend with you"
    assert upcoming[0]['end_date'] > upcoming[0]['local_date'] and upcoming[0]['stay']['can_change']
    shown = client.get('/api/today').json()['plans']['stays']
    assert shown and all(item['local_date'] <= (today(client) + timedelta(days=stays.SHOWN)).isoformat()
                         for item in shown)


def test_moving_a_stay_takes_it_to_the_next_free_weekend_and_the_child_stays_home(client, split):
    ours(client, custody='with_them')
    row = [row for row in plan(client) if row['reason'] == 'rota'][0]
    act(client, row['id'], 'move')
    [moved] = [found for found in rows(client) if found['id'] == row['id']]
    assert moved['start_date'] == (date.fromisoformat(row['start_date']) + timedelta(days=7)).isoformat()
    assert moved['first_start'] == row['start_date'] and moved['moved_reason'] == 'user'
    with connect(client) as connection:
        companion = current(connection)
        assert custody.here(connection, companion, date.fromisoformat(row['start_date']))
        assert not custody.here(connection, companion, date.fromisoformat(moved['start_date']))
    item = next(item for item in client.get('/api/life/admin').json()['upcoming'] if item['id'] == f"stay:{row['id']}")
    assert item['moved_reason'] == 'moved by you' and item['moved_from'] == row['start_date']
    assert plan(client) and len([found for found in rows(client) if found['first_start'] == row['start_date']]) == 1


def test_skipping_a_stay_plans_a_make_up_and_undo_takes_it_back(client, split, provider):
    ours(client, custody='with_them')
    row = [row for row in plan(client) if row['reason'] == 'rota'][0]
    act(client, row['id'], 'skip')
    found = rows(client)
    assert next(item for item in found if item['id'] == row['id'])['status'] == 'skipped'
    [made] = [item for item in found if item['reason'] == 'make-up']
    assert made['extra'] == row['id'] and made['start_date'] == \
        (date.fromisoformat(row['start_date']) + timedelta(days=7)).isoformat()
    item = next(item for item in client.get('/api/life/admin').json()['upcoming'] if item['id'] == f"stay:{row['id']}")
    assert item['status'] == 'skipped' and item['stay']['undo'] and item['stay']['made_up'] == made['start_date']
    with connect(client) as connection:
        assert custody.here(connection, current(connection), date.fromisoformat(row['start_date']))
    says(provider)
    send(client, 'hey', 'client-stays-0')
    assert 'is off this time;' in prompt(provider) and 'It is made up ' in prompt(provider)
    act(client, row['id'], 'undo')
    found = rows(client)
    assert next(item for item in found if item['id'] == row['id'])['status'] == 'planned'
    assert not [item for item in found if item['reason'] == 'make-up']
    act(client, row['id'], 'undo', 409)


def test_a_stay_under_way_or_past_cannot_be_changed(client, split, clock):
    ours(client, custody='with_them')
    row = [row for row in plan(client) if row['reason'] == 'rota'][0]
    clock.advance(timedelta(days=(date.fromisoformat(row['start_date']) - today(client)).days))
    act(client, row['id'], 'move', 409)
    act(client, row['id'], 'skip', 409)


def test_the_chat_says_whose_weekend_is_coming(client, split, provider, clock):
    ours(client, custody='with_them')
    row = [row for row in plan(client) if row['reason'] == 'rota'][0]
    gap = (date.fromisoformat(row['start_date']) - today(client)).days
    if gap > 7:
        clock.advance(timedelta(days=gap - 3))
    name = split['name'].split()[0]
    says(provider)
    send(client, 'morning', 'client-stays-1')
    assert f"{name}'s weekend with the user." in prompt(provider)


def test_with_the_adult_side_on_an_intimate_reply_says_nothing_of_a_stay(client, split, provider):
    ours(client, custody='with_them')
    plan(client)
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    intimate(client)
    says(provider)
    send(client, 'come here you', 'client-stays-2')
    text = prompt(provider)
    assert "weekend with the user" not in text and split['name'].split()[0] not in text
    with connect(client) as connection:
        assert stays.context_lines(connection, current(connection), client.app.state.database.clock.now()) == []


def test_getting_back_together_takes_the_stays_off(client, split, monkeypatch):
    ours(client, custody='with_them')
    assert plan(client)
    monkeypatch.setattr(custody, 'found', lambda *_args, **_kwargs: None)
    plan(client)
    assert not [row for row in rows(client) if row['start_date'] > today(client).isoformat()]


# The Getting together slider's extras ----------------------------------------------------------------------------------

def case(rhythm=lambda day: day.weekday() >= 5 and day.isocalendar().week % 2 == 1, far=False, at_level=2):
    found = stays.Case('ours', 'b1', [{'id': 'c1', 'name': 'Ivy Moss', 'born_on': '2022-07-20', 'pronouns': 'she/her',
                                       'status': 'born'}], 'you', 'the user', rhythm, far, None, date(2026, 6, 1))
    found.level = at_level
    return found


def test_a_summer_week_comes_from_the_slider_and_never_at_none():
    day = date(2026, 6, 25)
    summer = stays.summer(case(at_level=1), {'lat': 39.3}, day)
    assert summer and summer[0]['start_date'][:7] == '2026-07' and date.fromisoformat(summer[0]['start_date']).weekday() == 0
    assert stays.summer(case(at_level=0), {'lat': 39.3}, day) == []
    south = stays.summer(case(at_level=1), {'lat': -33.9}, date(2026, 12, 25))
    assert not south or south[0]['start_date'][:7] == '2027-01'


def test_a_birthday_is_split_and_holidays_alternate_at_the_top_of_the_slider():
    day = date(2026, 7, 5)
    assert [item['start_date'] for item in stays.birthdays(case(at_level=2), day)] == ['2026-07-20']
    assert stays.birthdays(case(at_level=1), day) == []
    assert stays.birthdays(case(at_level=3, far=True), day) == []
    assert stays.holidays(case(at_level=2), {'id': 'x'}, day) == []


def test_across_cities_a_weekend_every_few_weeks_by_the_slider():
    often = stays.far_spans(case(rhythm=None, far=True, at_level=3), {}, date(2026, 6, 1))
    rarely = stays.far_spans(case(rhythm=None, far=True, at_level=0), {}, date(2026, 6, 1))
    assert len(often) >= len(rarely) and all(date.fromisoformat(item['start_date']).weekday() == 5 for item in often)


def test_the_extras_never_double_up_with_the_rhythm():
    found = case()
    found.level = 3
    wanted = stays.rota_spans(found, date(2026, 6, 25)) + stays.summer(found, {'lat': 39.3}, date(2026, 6, 25))
    assert wanted


# A companion's own kids with their ex --------------------------------------------------------------------------------

def test_kids_who_live_with_their_other_parent_come_for_every_other_weekend(client, clock, monkeypatch):
    monkeypatch.setattr(kids, 'ACTIVE', True)
    make(client, background='Her son Leo, 7, lives with his dad and spends every other weekend with her.')
    found = plan(client)
    weekends = [row for row in found if row['reason'] == 'rota']
    assert weekends and all(row['family'] == 'kids' and row['host'] == 'companion' for row in weekends)
    with connect(client) as connection:
        companion = current(connection)
        row = kids.record(connection, companion['active_timeline_id'])
        since = date.fromisoformat(row['since'])
        assert all(kids.with_them('weekends', since, date.fromisoformat(item['start_date'])) for item in weekends)
    items = [item for item in client.get('/api/life/admin').json()['upcoming'] if item['source'] == 'family']
    assert items[0]['title'].startswith("Leo's weekend with ")
    act(client, weekends[0]['id'], 'skip')
    with connect(client) as connection:
        companion = current(connection)
        assert not kids.here_on(connection, row, 'weekends', since, date.fromisoformat(weekends[0]['start_date']))


def test_own_rhythm_matches_the_words_for_where_they_live():
    saturday_odd = next(date(2026, 10, 3) + timedelta(days=7 * week) for week in range(2)
                        if (date(2026, 10, 3) + timedelta(days=7 * week)).isocalendar().week % 2 == 1)
    assert not stays.own_rhythm('with_them', saturday_odd)  # Every other weekend at the ex's.
    assert stays.own_rhythm('with_them', saturday_odd + timedelta(days=7))
    assert stays.own_rhythm('weekends', saturday_odd + timedelta(days=7))
    assert not stays.own_rhythm('weekends', saturday_odd + timedelta(days=9))


# Asked for in the chat ---------------------------------------------------------------------------------------------------

def test_a_visit_asked_for_across_cities_books_a_stay(client, split, provider, monkeypatch):
    world = client.get('/api/worlds').json()['world']
    assert client.put(f"/api/worlds/{world['id']}/home", json={'city_id': 'chicago'}).status_code == 200
    with connect(client) as connection:
        state = custody.found(connection, current(connection))
    if not state or not state['far']:
        pytest.skip('The companion lives in Chicago in this world.')
    monkeypatch.setattr(together, 'level', lambda *_args: 2)
    says(provider)
    send(client, 'Can I come see you next weekend?', 'client-stays-3')
    asked = [row for row in rows(client) if row['reason'] == 'asked']
    assert len(asked) == 1 and asked[0]['message_id'] and asked[0]['travels'] in ('you', 'companion')
    assert date.fromisoformat(asked[0]['start_date']).weekday() == 5
    assert 'it is settled as' in prompt(provider)
