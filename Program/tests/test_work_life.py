"""Work life: slammed, ordinary and slow weeks, a running project, a yearly raise, vacation days by country and era, and
late nights that clash with plans the way an appointment does."""
import re
from datetime import date, timedelta

import pytest
from conftest import reconcile, send, set_life

from companion.characters import require_current
from companion.database import decode
from companion.life import admin, body, composer, work
from companion.providers.chat import Chunk
from companion.world import catalog, wording

WEEKDAYS = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00', 'days': [0, 1, 2, 3, 4]},
            {'key': 'evening', 'label': 'Evening', 'kind': 'leisure', 'start': '17:00', 'end': '23:00'},
            {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]


def test_the_project_banks_are_big_specific_and_era_tagged():
    banks = work.data()['projects']
    assert set(banks) == {*work.KINDS, 'general', 'adult'}
    titles = [item['title'] for bank in banks.values() for item in bank]
    assert len(titles) == len(set(titles))
    for kind, bank in banks.items():
        assert len(bank) >= 100, kind
        groups = ('modern',) if kind == 'adult' else ('modern', 'jazz-age', 'industrial', 'old')
        for group in groups:
            assert len([item for item in bank if group in item['eras']]) >= 20, (kind, group)
        assert all(12 <= len(item['title']) <= 70 and not item['title'].endswith('.') for item in bank), kind


def test_kinds_of_work_and_rules_follow_the_career_and_country():
    careers = catalog.careers()
    assert work.kind_of(careers['registered-nurse']) == 'care'
    assert work.kind_of(careers['software-engineer']) == 'tech'
    assert work.kind_of(careers['barista']) == 'service'
    assert work.kind_of(careers['cam-model']) == 'adult'
    assert work.kind_of(None) == 'general'
    assert work.rules(catalog.city('baltimore'))['vacation'] == 11
    assert work.rules(catalog.city('london'))['vacation'] == 25
    assert work.rules(catalog.city('osaka'))['review_month'] == 4
    assert work.rules(catalog.city('london-1895'))['vacation'] == 0
    assert work.rules(catalog.city('camelot'))['vacation'] == 0


def test_vacation_days_are_workdays_and_seeded():
    plan = work.vacation_plan('seed', 2027, 11, frozenset(range(5)), (6, 7, 8), frozenset({'2027-07-05'}), '2020-01-01')
    assert plan == work.vacation_plan('seed', 2027, 11, frozenset(range(5)), (6, 7, 8), frozenset({'2027-07-05'}),
                                      '2020-01-01')
    assert 8 <= len(plan) <= 11 and len(set(plan)) == len(plan)
    assert all(date.fromisoformat(day).weekday() < 5 for day in plan) and '2027-07-05' not in plan
    # A week off in the summer.
    assert sum(day[5:7] in ('06', '07', '08', '09') for day in plan) >= 5
    assert work.vacation_plan('seed', 2027, 0, frozenset(range(5)), (), frozenset(), '2020-01-01') == ()


def test_the_week_the_project_is_due_is_slammed_and_off_means_ordinary():
    found = {'timeline_id': 't', 'status': 'working', 'project': {'due': '2026-10-15'}}
    assert work.workload(found, date(2026, 10, 12), 2) == 'slammed'
    assert work.workload(found, date(2026, 10, 12), 0) == 'normal'
    weeks = [work.workload(found, date(2026, 11, 2) + timedelta(weeks=week), 2) for week in range(200)]
    assert 20 <= weeks.count('slammed') <= 60 and 15 <= weeks.count('slow') <= 50
    assert work.workload({**found, 'status': 'hunting'}, date(2026, 10, 12), 3) == 'normal'


def test_steady_has_fewer_slammed_weeks_than_true_to_life():
    def slammed(chosen):
        return sum(work.workload({'timeline_id': f't{index}', 'status': 'working', 'project': {'due': '2026-10-15'}},
                                 date(2026, 10, 12) + timedelta(weeks=week), chosen) == 'slammed'
                   for index in range(40) for week in range(10))
    assert slammed(1) < slammed(2) / 2


def test_projects_fit_the_career_and_stay_in_their_world():
    careers, bank = catalog.careers(), work.data()['projects']
    fits = {item['title']: set(item.get('fits') or ()) for items in bank.values() for item in items}
    engineer = work.projects('tech', 'modern', work.trades_of(careers['software-engineer']))
    assert len(engineer) >= work.MIN_OPTIONS and all(not fits[title] or 'software' in fits[title] for title in engineer)
    worlds = {item['title']: item for items in bank.values() for item in items}
    for city_id in ('camelot', 'grandport', 'emerald-city', 'london-1895'):
        city = catalog.city(city_id)
        for career in catalog.careers_for(city).values():
            found = work.projects(work.kind_of(career), work.era_group(city), work.trades_of(career), city)
            assert len(found) >= work.MIN_OPTIONS, (city_id, career['id'])
            assert all(work.in_world(worlds[title], city) for title in found), (city_id, career['id'])
    assert not any('Emerald' in title or 'Grandport' in title for title in
                   work.projects('public', 'old', frozenset({'police'}), catalog.city('camelot')))
    assert not any(worlds[title].get('monarchy') for title in
                   work.projects('service', 'old', frozenset({'food'}), catalog.city('grandport')))
    # In a US city the titles are in American spelling.
    baltimore = catalog.city('baltimore')
    titles = {work.new_project('seed', index, careers['office-clerk'], baltimore, date(2026, 10, 5), [])['title']
              for index in range(80)}
    assert not any(word in title for title in titles for word in ('catalogue', 'organis', ' rota', 'lorry'))


def test_a_late_night_follows_the_work_day_and_skips_days_without_free_time():
    day = date(2026, 10, 7)
    plain = {'schedule': WEEKDAYS}
    assert work.after_work(plain, day, work.work_block(plain, day)) == '17:00'
    studies = {'schedule': [{**WEEKDAYS[0], 'end': '16:30'},
                            {'key': 'class', 'label': 'Night class', 'kind': 'study', 'start': '16:30', 'end': '17:30'},
                            {**WEEKDAYS[1], 'start': '17:30'}, WEEKDAYS[2]]}
    assert work.after_work(studies, day, work.work_block(studies, day)) == '17:30'
    long_shift = {'schedule': [{**WEEKDAYS[0], 'start': '07:00', 'end': '19:00'},
                               {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '19:00', 'end': '07:00'}]}
    assert work.after_work(long_shift, day, work.work_block(long_shift, day)) is None


def test_no_late_night_on_a_public_holiday(client, nell, monkeypatch):
    reconcile(client)
    make_slammed(client, nell)
    database = client.app.state.database
    monkeypatch.setattr(work.generators, 'holidays', lambda _city, start, end: [
        {'date': (start + timedelta(days=offset)).isoformat(), 'kind': 'public'} for offset in range((end - start).days + 1)])
    with connect(client) as connection:
        connection.execute("DELETE FROM life_admin WHERE source='work'")
        companion = require_current(connection)
        work.plan_ahead(connection, companion, None, database.clock.now())
        assert not [item for item in admin.upcoming(connection, nell['active_timeline_id'], '2026-10-05')
                    if item['source'] == 'work']


def test_a_job_named_for_its_hours_is_still_the_shift():
    assert composer.span({'label': 'Night-shift nurse', 'kind': 'work'}) == 'shift'
    assert composer.span({'label': 'Night shift', 'kind': 'work'}) == 'night shift'


def test_a_storyline_promotion_within_a_year_of_another_adds_no_pay(client, nell):
    reconcile(client)
    database = client.app.state.database
    stages = '[{"on": "%s", "text": "Nell got the promotion.", "tone": "good"}]'
    with connect(client) as connection:
        for story, day in (('s1', '2026-03-01'), ('s2', '2026-10-04')):
            connection.execute(
                "INSERT INTO storylines (id, timeline_id, story, level, cast_ids, stages, started_on, status, created_at) "
                "VALUES (?, ?, 'promotion_chance', 0, '[]', ?, ?, 'ended', ?)",
                (story, nell['active_timeline_id'], stages % day, day, day))
        connection.execute("UPDATE work_life SET started_on='2025-01-01' WHERE timeline_id=?",
                           (nell['active_timeline_id'],))
        companion = require_current(connection)
        found = work.advance(connection, companion, database.clock.now())
    assert 1.07 < found['pay'] <= 1.15


def test_where_there_is_no_money_a_review_never_changes_pay(client, nell):
    reconcile(client)
    database = client.app.state.database
    with connect(client) as connection:
        companion = require_current(connection)
        found = work.state(connection, nell['active_timeline_id'])
        for year in range(2027, 2047):
            assert work.review(connection, companion, found, date(year, 6, 1), 3, {'paid': False},
                               database.clock.now()) == found['pay']
    kinds = {event['kind'] for event in client.get('/api/life/work').json()['work']['events']}
    assert kinds <= {'promotion', 'project'}


def test_a_review_months_away_is_still_held(client, nell, clock):
    reconcile(client)
    with connect(client) as connection:
        connection.execute("UPDATE work_life SET review_on='03-10', started_on='2020-01-01', checked_through='2026-02-01' "
                           "WHERE timeline_id=?", (nell['active_timeline_id'],))
    clock.advance(timedelta(days=1))
    reconcile(client)
    events = client.get('/api/life/work').json()['work']['events']
    assert any(event['kind'] in ('raise', 'promotion', 'freeze') and event['local_date'] == '2026-03-10'
               for event in events)


@pytest.fixture
def nell(client, monkeypatch, provider):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(work, 'ACTIVE', True)
    response = client.post('/api/companion', json={
        'name': 'Nell', 'timezone': 'UTC', 'schedule': WEEKDAYS, 'home_city': 'Baltimore',
        'identity': 'Nell is a registered nurse in Baltimore.', 'personality': 'Steady and kind'})
    assert response.status_code == 200, response.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    set_life(client, automatic_events=True, phrase_with_model=False, catch_up_max_events=6,
             catch_up_lookback_hours=168)
    return response.json()


def connect(client, write=True):
    return client.app.state.database.connect(write=write)


def test_work_life_starts_with_a_project_and_shows_on_the_character_page(client, nell):
    reconcile(client)
    view = client.get('/api/life/work').json()['work']
    assert view['status'] == 'working' and view['project']['title']
    titles = [wording.americanize(item['title']) for item in work.data()['projects']['care']]
    assert wording.americanize(view['project']['title']) in titles
    assert view['workload'] in ('slammed', 'normal', 'slow') and view['meter'] is None
    assert view['state'][0] in ('Slammed this week.', 'An ordinary week at work.', 'A slow week at work.')
    client.put('/api/settings', json={'show_home_meters': True})
    meter = client.get('/api/life/work').json()['work']['meter']
    assert meter['allowance'] == 11 and meter['pay_percent'] == 100


def make_slammed(client, nell, due='2026-10-08'):
    with connect(client) as connection:
        connection.execute("UPDATE work_life SET project=json_set(project, '$.due', ?) WHERE timeline_id=?",
                           (due, nell['active_timeline_id']))


def test_a_slammed_week_puts_late_nights_on_the_calendar_that_hold_against_dinner(client, nell, provider):
    reconcile(client)
    make_slammed(client, nell)
    reconcile(client)
    late = [item for item in client.get('/api/life/admin').json()['upcoming'] if item['source'] == 'work']
    assert 1 <= len([item for item in late if item['local_date'] <= '2026-10-11']) <= 2
    first = late[0]
    assert first['title'] == 'Staying late at work' and first['detail'] and first['at_time'] == '17:00' and first['fixed']
    # Dinner asked for that evening goes to another day, and the reply names the late night.
    provider.replies.append([Chunk("I'm stuck at work then, how about another night?"), Chunk('', 'stop')])
    day = 'tonight' if first['local_date'] == '2026-10-05' else date.fromisoformat(first['local_date']).strftime('%A')
    send(client, f'Dinner {day} at 7?', 'client-work-01')
    outings = client.get('/api/life/outings').json()['outings']
    assert outings and outings[0]['local_date'] != first['local_date']
    assert f"something is already booked then ({first['title']})" in provider.requests[-1]['prompt']
    # The work slot's account is the long day.
    with connect(client, write=False) as connection:
        row = connection.execute("SELECT entry FROM life_agenda WHERE subject='companion' AND slot_key=?",
                                 (f"work@{first['local_date']}",)).fetchone()
    assert row and 'Nell' in decode(row['entry'])['summary']


def test_on_light_a_late_night_moves_for_dinner_and_off_takes_them_away(client, nell, provider):
    set_life(client, work_realism=1)
    reconcile(client)
    make_slammed(client, nell)
    database = client.app.state.database
    with connect(client) as connection:
        companion = require_current(connection)
        work.plan_ahead(connection, companion, None, database.clock.now())
        late = [item for item in admin.upcoming(connection, nell['active_timeline_id'], '2026-10-05')
                if item['source'] == 'work']
        assert all(not item['fixed'] for item in late)
        assert all(not admin.stands(item, 3) for item in late)
    set_life(client, work_realism=0)
    with connect(client) as connection:
        companion = require_current(connection)
        work.plan_ahead(connection, companion, None, database.clock.now())
        assert not [item for item in admin.upcoming(connection, nell['active_timeline_id'], '2026-10-05')
                    if item['source'] == 'work']
        assert work.context_lines(connection, companion, database.clock.now()) == []
    # Back on, the late nights come back.
    set_life(client, work_realism=1)
    with connect(client) as connection:
        companion = require_current(connection)
        work.plan_ahead(connection, companion, None, database.clock.now())
        again = [item for item in admin.upcoming(connection, nell['active_timeline_id'], '2026-10-05')
                 if item['source'] == 'work']
    assert [item['key'] for item in again] == [item['key'] for item in late]


def test_a_yearly_review_raises_pay_and_the_budget_follows(client, nell, clock):
    reconcile(client)
    before = client.get('/api/today/money').json()
    with connect(client) as connection:
        connection.execute("UPDATE work_life SET review_on='10-06', started_on='2023-01-01' WHERE timeline_id=?",
                           (nell['active_timeline_id'],))
    clock.advance(timedelta(days=1))
    reconcile(client)
    events = client.get('/api/life/work').json()['work']['events']
    [review] = [event for event in events if event['kind'] in ('raise', 'promotion', 'freeze')]
    after = client.get('/api/today/money').json()
    if review['kind'] == 'freeze':
        assert after['budget']['income'] == pytest.approx(before['budget']['income'])
    else:
        assert after['budget']['income'] > before['budget']['income']
    with connect(client, write=False) as connection:
        companion = require_current(connection)
        lines = [text for _key, text in work.context_lines(connection, companion, client.app.state.database.clock.now())]
    assert any('October 6' in line for line in lines)
    if review['kind'] == 'raise':
        assert any(re.fullmatch(r'- On (Tuesday, )?October 6 you got your yearly raise at work, about \d+(\.\d)?%\.', line)
                   for line in lines)
    assert any(line.startswith('- At work you are in the middle of ') for line in lines)
    # Reconciling again records nothing new.
    reconcile(client)
    assert len(client.get('/api/life/work').json()['work']['events']) == len(events)


def test_a_day_after_the_due_date_names_the_project_that_follows(client, nell, clock):
    reconcile(client)
    make_slammed(client, nell, '2026-10-06')
    with connect(client) as connection:
        companion = require_current(connection)
        found = work.state(connection, nell['active_timeline_id'])
        assert work.project_on(connection, companion, found, date(2026, 10, 6)) == found['project']
        following = work.project_on(connection, companion, found, date(2026, 10, 8))
    clock.advance(timedelta(days=2))
    reconcile(client)
    assert client.get('/api/life/work').json()['work']['project']['title'] == following['title']


def test_a_finished_project_is_recorded_and_the_next_starts(client, nell, clock):
    reconcile(client)
    first = client.get('/api/life/work').json()['work']['project']
    make_slammed(client, nell, '2026-10-06')
    clock.advance(timedelta(days=2))
    reconcile(client)
    view = client.get('/api/life/work').json()['work']
    assert view['project']['title'] != first['title'] or view['project']['index'] == first['index'] + 1
    assert any(event['kind'] == 'project' and event['text'].startswith('wrapped up ') for event in view['events'])


def test_between_jobs_the_week_is_job_hunting_and_money_is_tighter(client, nell, clock):
    reconcile(client)
    with connect(client) as connection:
        connection.execute("UPDATE work_life SET status='hunting', hunt_since='2026-10-05', hunt_until='2026-10-20', "
                           "hunt_reason='laid-off' WHERE timeline_id=?", (nell['active_timeline_id'],))
        connection.execute("DELETE FROM life_agenda WHERE status='upcoming'")
        connection.execute('DELETE FROM agenda_cursors')
    reconcile(client)
    with connect(client, write=False) as connection:
        row = connection.execute("SELECT block, entry FROM life_agenda WHERE subject='companion' AND "
                                 "slot_key='work@2026-10-07'").fetchone()
        companion = require_current(connection)
        lines = [text for _key, text in work.context_lines(connection, companion, client.app.state.database.clock.now())]
    assert decode(row['block'])['label'] == 'Job hunting' and decode(row['entry'])['activity'] == 'job-hunting'
    assert lines[0] == '- You are between jobs and looking for work; nothing is lined up yet.'
    money = client.get('/api/today/money').json()
    assert money['between_jobs']
    clock.advance(timedelta(days=16))
    reconcile(client)
    view = client.get('/api/life/work').json()['work']
    assert view['status'] == 'working' and view['events'][0]['kind'] == 'new-job'


def test_vacation_days_are_days_off_in_the_agenda(client, nell, monkeypatch):
    monkeypatch.setattr(work, 'vacation_days', lambda *_args: ['2026-10-07'])
    reconcile(client)
    with connect(client, write=False) as connection:
        row = connection.execute("SELECT block FROM life_agenda WHERE subject='companion' AND "
                                 "slot_key='work@2026-10-07'").fetchone()
        companion = require_current(connection)
        lines = [text for _key, text in work.context_lines(connection, companion, client.app.state.database.clock.now())]
    assert decode(row['block'])['label'] == 'Vacation day' and decode(row['block'])['kind'] == 'leisure'
    assert '- You have Wednesday, October 7 off work (a vacation day).' in lines


def test_the_level_setting_is_saved(client, nell):
    assert client.get('/api/life/settings').json()['work_realism'] == 2
    assert set_life(client, work_realism=3)['work_realism'] == 3
    assert client.put('/api/life/settings', json={'work_realism': 4}).status_code == 422


def test_a_storyline_promotion_raises_pay(client, nell):
    reconcile(client)
    database = client.app.state.database
    with connect(client) as connection:
        connection.execute(
            "INSERT INTO storylines (id, timeline_id, story, level, cast_ids, stages, started_on, status, created_at) "
            "VALUES ('s1', ?, 'promotion_chance', 0, '[]', ?, '2026-10-01', 'ended', '2026-10-01')",
            (nell['active_timeline_id'], '[{"on": "2026-10-04", "text": "Nell got the promotion.", "tone": "good"}]'))
        connection.execute("UPDATE work_life SET started_on='2025-01-01' WHERE timeline_id=?",
                           (nell['active_timeline_id'],))
        companion = require_current(connection)
        found = work.advance(connection, companion, database.clock.now())
    assert found['pay'] > 1.07


def test_a_new_job_at_an_employer_ending_in_a_full_stop_ends_its_line_once(client, nell, clock):
    reconcile(client)
    with connect(client) as connection:
        companion = require_current(connection)
        today = clock.now().date()
        work.record(connection, nell['active_timeline_id'], 'job:test', 'new-job', today,
                    'started a new job at Coutts and Co.', 1000, 5, clock.now())
        lines = [text for _key, text in work.context_lines(connection, companion, clock.now())]
    [line] = [text for text in lines if 'Coutts' in text]
    assert line.endswith('you started a new job at Coutts and Co.'), line
