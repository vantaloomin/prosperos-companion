"""Shifts and gigs: a weekly rota for service jobs, freelance gigs in busy and dry spells, and the same days every week
for staff, through everything that reads the routine."""
import re
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
    assert ' Days off: ' in line and 'Next week: ' in line and '16:00 to 23:30' in line
    assert 'Any other day' not in line


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
    # Thanksgiving is named only as a day off, by date like the shifts (the A/B in
    # /mnt/project-files/companion-e2e-v12/ab/shifts/results.md).
    worked, days_off = line.split(' Days off: ')
    assert 'Wednesday 25, Friday 27 and Saturday 28' in worked and 'Thursday 26' not in worked
    assert overview == 'This week: Mon, Tue, Wed, Fri and Sat evenings.'
    assert 'Next week: Monday 30, Tuesday 1, Wednesday 2, Thursday 3 and Saturday 5.' in worked
    assert days_off == 'Thursday 26 and Sunday 29 this week; Friday 4 and Sunday 6 next week.'
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


def test_a_clock_moved_back_rewrites_no_past_days(client, ines, clock):
    """With the clock behind what has already happened, the week is not brought in line again: that would write a
    day off next to a shift that already happened."""
    reconcile(client)
    for _ in range(13):
        clock.advance(timedelta(days=7))
        reconcile(client)
    clock.advance(timedelta(days=-88))
    reconcile(client)
    with connect(client, write=False) as connection:
        rows = connection.execute("SELECT local_date, slot_key FROM life_agenda WHERE timeline_id=? AND "
                                  "subject='companion'", (ines['active_timeline_id'],)).fetchall()
    keys = {}
    for row in rows:
        keys.setdefault(row['local_date'], set()).add(row['slot_key'].split('@')[0])
    assert not [day for day, found in keys.items() if {'work', 'day-off'} <= found]


def test_weeks_before_the_first_one_written_stay_as_they_were_lived(client, ines):
    # An upgrade from before shifts and gigs: the weeks already lived were the written pattern, and stay so.
    reconcile(client)
    timeline_id = ines['active_timeline_id']
    with connect(client, write=False) as connection:
        companion = require_current(connection)
        found = shifts.setup(connection, companion)
        first = shifts.first_written(connection, timeline_id)
        span = shifts.weeks(connection, companion, MONDAY - timedelta(weeks=4), MONDAY, found)
    assert first == MONDAY.isoformat()
    written = sorted(next(block for block in BARTENDER if block['kind'] == 'work')['days'])
    for monday, week in span.items():
        if monday < first:
            assert week['days'] == written and week['pay'] == 1.0
    assert span[MONDAY.isoformat()]['days'] == companion['version']['definition']['rota']['weeks'][MONDAY.isoformat()]
    rota = companion['version']['definition']['rota']['weeks']
    assert rota[(MONDAY - timedelta(weeks=3)).isoformat()] == written


def test_a_branch_keeps_the_weeks_planned_before_it(client, ines, provider):
    reconcile(client)
    provider.replies.append([Chunk('Busy night.'), Chunk('', 'stop')])
    sent = send(client, 'How was the bar?', 'client-shift-fork')
    fork = client.post('/api/timelines', json={'message_id': sent['message']['id'], 'text': 'How was work?'})
    assert fork.status_code == 200, fork.text
    timeline_id, fork_id = ines['active_timeline_id'], fork.json()['id']
    with connect(client, write=False) as connection:
        weeks = {row['timeline_id']: {r['monday']: r['days'] for r in connection.execute(
            'SELECT monday, days FROM work_weeks WHERE timeline_id=? AND monday<=?', (row['timeline_id'], MONDAY.isoformat()))}
            for row in connection.execute('SELECT ? AS timeline_id UNION ALL SELECT ?', (timeline_id, fork_id))}
    assert weeks[timeline_id] and weeks[fork_id] == weeks[timeline_id]


def test_a_holiday_or_day_off_on_a_rolled_shift_is_not_named_as_a_shift(client, ines, monkeypatch):
    # The agenda makes a public holiday, a tradition day or a vacation day a day off (agenda.holiday_block), so
    # the shift lines leave it out ("Thursday 26" listed on Thanksgiving, when they are at their dad's).
    reconcile(client)
    with connect(client, write=False) as connection:
        companion = require_current(connection)
        following = MONDAY + timedelta(weeks=1)
        rolled = shifts.weeks(connection, companion, following, following)[following.isoformat()]['days']
        assert rolled
        days = {(following + timedelta(days=day)).isoformat(): 'Vacation' for day in rolled}
        monkeypatch.setattr(work, 'days_off', lambda *_args: days)
        line = shifts.context_line(connection, companion, MONDAY)
        assert 'No shifts next week.' in line
        assert set(days) <= shifts.off_days(connection, companion, MONDAY, following + timedelta(days=6))
        thanksgiving = date(2026, 11, 26)
        assert thanksgiving.isoformat() in shifts.off_days(connection, companion, thanksgiving, thanksgiving)


def gig_weeks(client, timeline_id, this, following):
    with connect(client) as connection:
        for monday, (days, spell) in (('2026-10-05', this), ('2026-10-12', following)):
            connection.execute("INSERT OR REPLACE INTO work_weeks (timeline_id, monday, kind, career, days, spell, "
                               "pay, created_at) VALUES (?, ?, 'freelance', 'bartender', ?, ?, 1, '2026-10-01')",
                               (timeline_id, monday, str(days), spell))
        return shifts.context_line(connection, require_current(connection), MONDAY + timedelta(days=2))


def test_a_freelancer_s_line_names_next_week_s_gigs_and_free_days_and_its_own_spell(client, ines, monkeypatch):
    # A dry week then a busy one: next week's spell is said apart ("no more gigs this week and four booked so far
    # next week" read as a dry next week), with its gigs and the free days by date.
    assert revise(client, lambda definition: {'money': {**definition['money'], 'employment': 'freelance'}}
                  ).status_code == 200
    reconcile(client)
    monkeypatch.setattr(work, 'days_off', lambda *_args: {})  # no vacation day drawn into these two weeks
    line = gig_weeks(client, ines['active_timeline_id'], ([0], 'dry'), ([0, 1, 3, 4], 'busy'))
    assert line == ('- You freelance, so work comes in spells, and lately it is a dry spell: no more gigs this '
                    'week and next week picks up: gigs Monday 12, Tuesday 13, Thursday 15 and Friday 16 booked so '
                    'far. Free days: Wednesday 7, Thursday 8, Friday 9, Saturday 10 and Sunday 11 this week; '
                    'Wednesday 14, Saturday 17 and Sunday 18 next week.')
    line = gig_weeks(client, ines['active_timeline_id'], ([3], 'steady'), ([2], 'steady'))
    assert 'gigs Thursday 8 this week and gigs Wednesday 14 booked so far next week.' in line


def test_an_old_era_takes_engagements_not_gigs(client, ines, monkeypatch):
    """Camelot, London 1895, Oz or Grandport: no "freelance", "gigs" or "booked" in the chat, on the Character page
    or in the day's account; New York 1925 and modern cities keep them (findings/shifts.md F8)."""
    from companion.life import outings
    assert revise(client, lambda definition: {'money': {**definition['money'], 'employment': 'freelance'}}
                  ).status_code == 200
    reconcile(client)
    monkeypatch.setattr(work, 'days_off', lambda *_args: {})
    with connect(client, write=False) as connection:
        companion = require_current(connection)
        city = outings.city_data(connection, companion['version']['definition'])
        for era, old in (('medieval', True), ('victorian', True), ('fantasy', True), ('jazz-age', False),
                         ('modern', False)):
            with monkeypatch.context() as patch:
                patch.setattr(outings, 'city_data', lambda *_args, era=era: {**city, 'era': era})
                assert shifts.old_era(connection, companion) == old, era
    for old in (True, False):
        # The city's era stays Baltimore's here, so the career and its weeks stay the same.
        monkeypatch.setattr(shifts, 'old_era', lambda *_args, old=old: old)
        line = gig_weeks(client, ines['active_timeline_id'], ([2, 4], 'steady'), ([1, 3], 'steady'))
        with connect(client, write=False) as connection:
            overview = shifts.overview_line(connection, require_current(connection), MONDAY + timedelta(days=2))
        if old:
            assert not re.findall(r'\b(?:freelance|gigs?|booked)\b', line + overview), (line, overview)
            assert line.startswith('- You take work where it comes, so it comes in spells')
            assert 'engagements Wednesday 7 and Friday 9 this week and engagements Tuesday 13 and Thursday 15 ' \
                   'arranged so far next week.' in line
            assert overview == 'Two engagements this week (Wed and Fri), a steady spell.'
        else:
            assert line.startswith('- You freelance,') and overview.startswith('Two gigs this week')
    assert all(not re.search(r'\bgigs?\b|client', text) for text in work.GIG_OLD)
