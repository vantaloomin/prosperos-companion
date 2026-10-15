"""Shifts and gigs: a weekly rota for service jobs, freelance gigs in busy and dry spells, and the same days every week
for staff, through everything that reads the routine."""
from datetime import UTC, date, datetime, timedelta

import pytest
from conftest import reconcile, send, set_life

from companion.characters import require_current
from companion.database import decode
from companion.life import body, composer, outings, routine, shifts, work
from companion.providers.chat import Chunk
from companion.world import catalog, generators, mend

MONDAY = date(2026, 10, 5)


def test_every_career_is_tagged():
    tagged = [*catalog.careers().values()]
    for city in catalog.cities().values():
        if city.get('builtin', True):
            tagged += city['careers']
    assert tagged and all(career['employment'] in shifts.KINDS for career in tagged)
    careers = catalog.careers()
    assert careers['bartender']['employment'] == 'rota' and careers['registered-nurse']['employment'] == 'rota'
    assert careers['graphic-designer']['employment'] == 'freelance'
    assert careers['tour-guide']['employment'] == 'freelance'
    assert careers['software-engineer']['employment'] == 'staff'


def test_a_career_without_a_tag_is_read_from_its_words():
    def career(**fields):
        return {'id': 'x', 'name': 'X', 'summary': '', 'sector': 'general', 'schedule': 'office', **fields}
    assert shifts.employment_of(career(name='Cocktail waitress')) == 'rota'
    assert shifts.employment_of(career(summary='Freelance work for local papers.')) == 'freelance'
    assert shifts.employment_of(career(schedule='evening', sector='hospitality')) == 'rota'
    assert shifts.employment_of(career(schedule='flexible', sector='arts')) == 'freelance'
    assert shifts.employment_of(career()) == 'staff'
    # A job the user wrote: their own words, the way "freelance" already reads as flexible hours.
    assert shifts.employment_of(None, 'Sam is a self-employed illustrator.') == 'freelance'
    assert shifts.employment({'identity': 'A freelance photographer.'}, catalog.careers()['software-engineer']) \
        == 'freelance'
    assert shifts.employment({'money': {'employment': 'staff'}}, catalog.careers()['bartender']) == 'staff'


def test_a_user_city_can_say_how_a_job_works():
    city = catalog.city('whitlock')
    raw = {**city, 'id': 'my-town', 'careers': [{**city['careers'][0], 'id': 'gig-worker', 'employment': 'gigs'}]}
    mended, _notes = mend.mend(raw)
    assert mended['careers'][0]['employment'] == 'freelance'


def test_a_rota_follows_the_pattern_and_the_week_at_work():
    base = [1, 2, 3, 4, 5]
    weeks = [shifts.roll('seed', MONDAY + timedelta(weeks=index), 'rota', base, '16:00', '23:30', 'normal', 2)
             for index in range(60)]
    assert len({tuple(week['days']) for week in weeks}) > 10
    assert all(4 <= len(week['days']) <= 6 for week in weeks)
    # Evening work leans to Fridays and Saturdays.
    fridays = sum(4 in week['days'] for week in weeks)
    mondays = sum(0 in week['days'] for week in weeks)
    assert fridays > mondays
    slammed = shifts.roll('seed', MONDAY, 'rota', base, '16:00', '23:30', 'slammed', 2)
    slow = shifts.roll('seed', MONDAY, 'rota', base, '16:00', '23:30', 'slow', 2)
    assert len(slammed['days']) == 6 and len(slow['days']) == 4 and slow['pay'] == pytest.approx(0.8)
    assert shifts.roll('seed', MONDAY, 'rota', base, '16:00', '23:30', 'normal', 2) == weeks[0]
    tipped = [shifts.roll('seed', MONDAY + timedelta(weeks=index), 'rota', base, '16:00', '23:30', 'normal', 2,
                          tipped=True)['pay'] for index in range(30)]
    assert len(set(tipped)) > 5


def test_freelance_comes_in_busy_and_dry_spells():
    weeks = [shifts.roll('seed', MONDAY + timedelta(weeks=index), 'freelance', [0, 1, 2, 3, 4], '10:00', '16:00',
                         'normal', 3) for index in range(120)]
    spells = [week['spell'] for week in weeks]
    assert {'busy', 'steady', 'dry'} <= set(spells)
    # A spell lasts a few weeks.
    assert sum(spells[index] == spells[index + 1] for index in range(len(spells) - 1)) > len(spells) / 2
    assert all(len(week['days']) <= 1 for week in weeks if week['spell'] == 'dry')
    assert all(3 <= len(week['days']) for week in weeks if week['spell'] == 'busy')
    pays = [week['pay'] for week in weeks]
    assert min(pays) == 0 and max(pays) > 1.5 and 0.7 < sum(pays) / len(pays) < 1.4


def test_routine_blocks_follow_the_week_on_the_definition():
    definition = {'schedule': generators.week('Bartender', 'work', [1, 2, 3, 4, 5], '16:00', '23:30', '01:30', '09:30',
                                              []),
                  'rota': {'weeks': {MONDAY.isoformat(): [0, 4, 5]}}}
    schedule = {block.key: block for block in routine.blocks(definition)[0]}
    assert schedule['work'].on(MONDAY) and not schedule['work'].on(MONDAY + timedelta(days=1))
    assert schedule['day-off'].on(MONDAY + timedelta(days=1)) and not schedule['day-off'].on(MONDAY + timedelta(days=4))
    # A week without its own days keeps the written ones.
    assert schedule['work'].on(MONDAY + timedelta(days=8))
    slots = routine.slots(list(schedule.values()), 'UTC', datetime(2026, 10, 5, tzinfo=UTC),
                          datetime(2026, 10, 12, tzinfo=UTC))
    assert sorted({slot.local_date.weekday() for slot in slots if slot.block.key == 'work'}) == [0, 4, 5]


BARTENDER = generators.week('Bartender', 'work', [1, 2, 3, 4, 5], '16:00', '23:30', '01:30', '09:30', ['regulars'])


@pytest.fixture
def ines(client, monkeypatch, provider):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(work, 'ACTIVE', True)
    monkeypatch.setattr(shifts, 'ACTIVE', True)
    response = client.post('/api/companion', json={
        'name': 'Ines', 'timezone': 'UTC', 'schedule': BARTENDER, 'home_city': 'Baltimore',
        'identity': 'Ines is a bartender in Fells Point.', 'personality': 'Quick and warm',
        'money': {'career': 'bartender'}})
    assert response.status_code == 200, response.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    set_life(client, automatic_events=True, phrase_with_model=False, catch_up_max_events=6,
             catch_up_lookback_hours=168)
    return response.json()


def revise(client, change):
    companion = client.get('/api/companion').json()['companion']
    definition = companion['version']['definition']
    return client.post('/api/companion/versions', json={'definition': {**definition, **change(definition)},
                                                         'expected_version_id': companion['version']['id']})


def connect(client, write=True):
    return client.app.state.database.connect(write=write)


def work_days(client, timeline_id):
    with connect(client, write=False) as connection:
        rows = connection.execute("SELECT slot_key FROM life_agenda WHERE timeline_id=? AND subject='companion' AND "
                                  "slot_key LIKE 'work@%'", (timeline_id,)).fetchall()
    return {row['slot_key'].split('@')[1] for row in rows}


def test_a_bartender_s_week_is_rolled_and_the_agenda_follows_it(client, ines):
    reconcile(client)
    timeline_id = ines['active_timeline_id']
    with connect(client, write=False) as connection:
        stored = {row['monday']: decode(row['days']) for row in connection.execute(
            'SELECT monday, days FROM work_weeks WHERE timeline_id=?', (timeline_id,))}
        companion = require_current(connection)
    assert MONDAY.isoformat() in stored and len(stored) >= shifts.PLAN_WEEKS
    rota = companion['version']['definition']['rota']
    assert rota['kind'] == 'rota' and rota['weeks'][MONDAY.isoformat()] == stored[MONDAY.isoformat()]
    following = (MONDAY + timedelta(weeks=1)).isoformat()
    expected = {(date.fromisoformat(monday) + timedelta(days=day)).isoformat() for monday in (MONDAY.isoformat(),
                following) for day in stored[monday]}
    upcoming = {day for day in work_days(client, timeline_id) if day >= MONDAY.isoformat()}
    assert upcoming and upcoming <= expected
    # The saved version never carries the weeks, and the form can send them back.
    with connect(client, write=False) as connection:
        saved = connection.execute('SELECT definition FROM character_versions WHERE companion_id=?',
                                   (ines['id'],)).fetchone()
    assert 'rota' not in decode(saved['definition'])
    definition = client.get('/api/companion').json()['companion']['version']['definition']
    assert definition['rota']['weeks']
    response = revise(client, lambda _definition: {'personality': 'Quick, warm, wry'})
    assert response.status_code == 200, response.text


def test_the_character_page_and_the_chat_name_this_week(client, ines):
    reconcile(client)
    view = client.get('/api/life/work').json()['work']
    line = next(line for line in view['state'] if line.startswith('This week: '))
    assert line.endswith(' nights.') or line.endswith(' evenings.')
    with connect(client, write=False) as connection:
        companion = require_current(connection)
        lines = [text for _key, text in work.context_lines(connection, companion, client.app.state.database.clock.now())]
    [line] = [text for text in lines if text.startswith('- Your shifts change every week. ')]
    assert line.endswith(' Any other day is a day off.') and 'Next week: ' in line and '16:00 to 23:30' in line


def test_a_shift_holds_against_dinner_like_work_always_has(client, ines, provider):
    reconcile(client)
    with connect(client, write=False) as connection:
        companion = require_current(connection)
    schedule = routine.blocks(companion['version']['definition'])[0]
    shift = next(MONDAY + timedelta(days=offset) for offset in range(1, 7)
                 if next(block for block in schedule if block.key == 'work').on(MONDAY + timedelta(days=offset)))
    provider.replies.append([Chunk("I'm behind the bar then, another night?"), Chunk('', 'stop')])
    send(client, f"Dinner {shift.strftime('%A')} at 7?", 'client-shift-01')
    found = client.get('/api/life/outings').json()['outings']
    work_block = next(block for block in schedule if block.key == 'work')
    if all(work_block.on(shift + timedelta(days=offset)) for offset in range(7)):
        assert not found  # a full week of shifts: no free evening to move dinner to
        return
    assert found and found[0]['local_date'] != shift.isoformat()
    assert not outings.busy_at(schedule, date.fromisoformat(found[0]['local_date']), found[0]['at_time'] or '19:00')


def test_hours_pinned_on_the_form_keep_the_written_week(client, ines):
    reconcile(client)
    response = revise(client, lambda definition: {'money': {**definition['money'], 'employment': 'staff'}})
    assert response.status_code == 200, response.text
    reconcile(client)
    with connect(client, write=False) as connection:
        companion = require_current(connection)
    assert 'rota' not in companion['version']['definition']
    upcoming = {date.fromisoformat(day).weekday() for day in work_days(client, ines['active_timeline_id'])
                if day > '2026-10-06'}
    assert upcoming <= {1, 2, 3, 4, 5}
    assert not any(line.startswith('This week') for line in client.get('/api/life/work').json()['work']['state'])


def test_work_life_off_keeps_the_written_week(client, ines):
    set_life(client, work_realism=0)
    reconcile(client)
    with connect(client, write=False) as connection:
        companion = require_current(connection)
        assert shifts.setup(connection, companion) is None
    assert 'rota' not in companion['version']['definition']


def test_freelance_gigs_show_and_pay_unevenly(client, ines, clock):
    assert revise(client, lambda definition: {'money': {**definition['money'], 'employment': 'freelance'}}
                  ).status_code == 200
    reconcile(client)
    view = client.get('/api/life/work').json()['work']
    assert view['hours'] == 'freelance' and 'gig' in view['state'][0] and 'spell' in view['state'][0]
    # The gigs say how the week goes; a week without them has no project line (Iris).
    assert not any(line.endswith('this week.') and 'week at work' in line for line in view['state'])
    assert any(line.startswith('Working on ') for line in view['state']) != view['state'][0].startswith('No gigs')
    with connect(client) as connection:
        connection.execute("UPDATE work_weeks SET pay=0 WHERE timeline_id=?", (ines['active_timeline_id'],))
        connection.execute("INSERT OR REPLACE INTO work_weeks (timeline_id, monday, kind, career, days, pay, created_at) "
                           "VALUES (?, '2026-09-28', 'freelance', 'bartender', '[]', 0, '2026-09-28')",
                           (ines['active_timeline_id'],))
        connection.execute("INSERT OR REPLACE INTO work_weeks (timeline_id, monday, kind, career, days, pay, created_at) "
                           "VALUES (?, '2026-09-21', 'freelance', 'bartender', '[]', 0, '2026-09-21')",
                           (ines['active_timeline_id'],))
        assert work.pay(connection, ines['active_timeline_id'], MONDAY)['factor'] == 0


def test_pay_lands_on_payday_and_holds_until_the_next(client, ines):
    """Shifts worked count from the last payday: what is left to spend never jumps on a Monday between paydays."""
    from companion.life import money
    reconcile(client)
    timeline_id = ines['active_timeline_id']
    with connect(client) as connection:
        for index in range(-6, 5):
            connection.execute("INSERT OR REPLACE INTO work_weeks (timeline_id, monday, kind, career, days, pay, "
                               "created_at) VALUES (?, ?, 'rota', 'bartender', '[1,2,3]', ?, '2026-09-01')",
                               (timeline_id, (MONDAY + timedelta(weeks=index)).isoformat(), 0.6 + 0.1 * (index % 3)))
        companion = require_current(connection)
        definition = companion['version']['definition']
        found = money.profile(definition)
        start = money.cycle_start(found, MONDAY + timedelta(days=17))
        days = [start + timedelta(days=offset) for offset in range(found.cycle_days)]
        assert any(day.weekday() == 0 for day in days[1:])
        pays = {money.household(connection, timeline_id, definition, day)['pay']['factor'] for day in days}
    assert len(pays) == 1


def test_a_rota_never_runs_past_six_days_in_a_row_across_weeks():
    """Each week starts from where the last one ended: six days in a row at most, four of twelve-hour nights."""
    for base, start, end, most in (([1, 2, 3, 4, 5], '16:00', '23:30', 6), ([0, 1, 2], '19:00', '07:30', 4)):
        worked, previous = [], []
        for index in range(104):
            load = ('normal', 'slammed', 'slammed', 'slow')[index % 4]
            previous = shifts.roll('seed', MONDAY + timedelta(weeks=index), 'rota', base, start, end, load, 3,
                                   before=shifts.trailing(previous))['days']
            worked += [day in previous for day in range(7)]
        runs = ''.join('x' if day else '.' for day in worked).split('.')
        assert max(len(run) for run in runs) <= most


def test_a_holiday_is_off_in_the_week_s_lines_as_on_the_calendar(client, ines, monkeypatch):
    """Thanksgiving is a day off on their calendar (agenda.holiday_block), so the chat and the Character page never
    name it as a shift; nor a vacation day."""
    reconcile(client)
    monkeypatch.setattr(work, 'days_off', lambda *_args: {'2026-12-04': 'Vacation'})
    timeline_id, thanksgiving = ines['active_timeline_id'], date(2026, 11, 26)
    with connect(client) as connection:
        for monday in ('2026-11-23', '2026-11-30'):
            connection.execute("INSERT OR REPLACE INTO work_weeks (timeline_id, monday, kind, career, days, pay, "
                               "created_at) VALUES (?, ?, 'rota', 'bartender', '[0,1,2,3,4,5]', 1, '2026-10-01')",
                               (timeline_id, monday))
        companion = require_current(connection)
        line = shifts.context_line(connection, companion, date(2026, 11, 24))
        overview = shifts.overview_line(connection, companion, date(2026, 11, 24))
    assert 'Wednesday 25, Friday 27 and Saturday 28' in line and 'Thursday 26' not in line
    assert overview == 'This week: Mon, Tue, Wed, Fri and Sat evenings.'
    assert 'Next week: Monday 30, Tuesday 1, Wednesday 2, Thursday 3 and Saturday 5.' in line
    assert thanksgiving.weekday() == 3


def test_daytime_gigs_lean_to_weekdays_and_performers_to_the_weekend():
    def share(start, end, performer):
        weeks = [shifts.roll('seed', MONDAY + timedelta(weeks=index), 'freelance', [0, 1, 2, 3, 4], start, end,
                             'normal', 2, performer=performer) for index in range(200)]
        days = [day for week in weeks for day in week['days']]
        return sum(day >= 5 for day in days) / len(days)
    assert share('10:00', '16:00', False) < 0.15
    assert share('10:00', '16:00', True) > 0.3 and share('19:00', '23:00', False) > 0.3


def test_a_job_the_user_wrote_is_read_from_its_own_sentence():
    def kind(identity):
        return shifts.employment({'identity': identity}, None)
    # A hobby is not a job.
    assert kind('Mara is a beekeeper. She loves pub quizzes and to cook for friends.') == 'staff'
    assert kind('Mara is a podcast host.') == 'staff'
    for identity in ('Mara is an on-call IT technician.', 'Mara works the overnight shift at a gas station.',
                     'Mara is a sous chef at a bistro.', 'Mara is a firefighter.'):
        assert kind(identity) == 'rota', identity
    for identity in ('Mara is a wedding photographer.', 'Mara drives for a rideshare app.',
                     'Mara is a DJ who plays weekends.', 'Mara picks up gig work as a delivery driver.'):
        assert kind(identity) == 'freelance', identity


def test_shifts_written_later_keep_off_a_dinner_already_settled(client, ines, provider, monkeypatch):
    """Dinner settled on a day off while Work life was Off: once it is on, the new week's shift moves off that day
    instead of landing on top of it, as Life admin keeps out of the way of plans with the user."""
    set_life(client, work_realism=0)
    reconcile(client)
    following = MONDAY + timedelta(weeks=1)
    provider.replies.append([Chunk('Monday works!'), Chunk('', 'stop')])
    send(client, 'Dinner next Monday at 7?', 'client-shift-later-01')
    [outing] = client.get('/api/life/outings').json()['outings']
    assert outing['local_date'] == following.isoformat()
    monkeypatch.setattr(shifts, 'roll', lambda *_args, **_kwargs: {'days': [0, 1, 2, 3, 4], 'spell': '', 'pay': 1.0})
    set_life(client, work_realism=2)
    reconcile(client)
    with connect(client, write=False) as connection:
        row = connection.execute('SELECT days FROM work_weeks WHERE timeline_id=? AND monday=?',
                                 (ines['active_timeline_id'], following.isoformat())).fetchone()
    assert decode(row['days']) == [1, 2, 3, 4, 5]
    assert following.isoformat() not in work_days(client, ines['active_timeline_id'])
    assert shifts.clear_of_plans([0, 1, 2, 3, 4, 5, 6], '16:00', '23:30', [(19 * 60, 21 * 60)]) == [1, 2, 3, 4, 5, 6]
