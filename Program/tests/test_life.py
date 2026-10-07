"""Life simulation and time reconciliation (PRD T1–T7 and the time-reconciliation acceptance row).

Every case drives a substitute clock; the host clock is never changed.
"""
import asyncio
import time
from datetime import UTC, date, datetime, timedelta

import pytest
from conftest import life_reply, reconcile, set_life
from fastapi.testclient import TestClient

from companion import characters
from companion.clock import parse
from companion.identity import CLIENT_HEADER
from companion.life import composer, routine, synthesis
from companion.life.world import Place, StaticWorld
from companion.main import create_app
from companion.models import CharacterRevision
from companion.providers.chat import Chunk
from companion.providers.scheduling import BackgroundInterrupted
from companion.providers.vault import MemoryVault


def life_requests(provider):
    return [request for request in provider.requests if 'Rephrase one ordinary moment' in request['system']]


def all_events(client):
    return client.get('/api/events?history=true').json()


def revise_character(client, **changes):
    current = client.get('/api/companion').json()['companion']
    definition = {**current['version']['definition'], **changes}
    response = client.post('/api/companion/versions', json={'definition': definition,
                                                             'expected_version_id': current['active_version_id']})
    assert response.status_code == 200, response.text
    return response.json()


def test_return_after_a_day_proposes_capped_events_for_review(client, life, clock):
    clock.advance(timedelta(days=1))
    result = reconcile(client)
    assert result['state'] == 'started'
    run = result['run']
    assert run['status'] == 'completed' and run['mode'] == 'return'
    assert [item['outcome'] for item in run['results']] == ['proposed'] * 3
    proposed = all_events(client)
    assert len(proposed) == 3 and {event['status'] for event in proposed} == {'proposed'}
    assert client.get('/api/events').json() == []
    # Generation time is now; event time is when the routine slot happened (T1, T4).
    for event in proposed:
        assert parse(event['ends_at']) <= clock.now() and parse(event['created_at']) == clock.now()
        assert event['inputs']['mode'] == 'return' and event['inputs']['wording'] == 'model'
        assert event['summary'].startswith('Phrased: Mira') and event['details']['activity']


def test_automatic_events_commit_and_become_the_shared_account(client, life, clock):
    assert client.get('/api/settings').json()['permission_revision'] == 1
    set_life(client, automatic_events=True)
    assert client.get('/api/settings').json()['permission_revision'] == 2
    clock.advance(timedelta(days=1))
    run = reconcile(client)['run']
    assert [item['outcome'] for item in run['results']] == ['committed'] * 3
    assert 'Phrased: Mira' in client.get('/api/context/preview').json()['system']


def test_short_gaps_wait_and_repeated_returns_do_not_duplicate(client, life, clock):
    clock.advance(timedelta(hours=2))
    assert reconcile(client)['state'] == 'not_due'
    clock.advance(timedelta(days=1))
    assert reconcile(client)['state'] == 'started'
    assert reconcile(client)['state'] == 'not_due'
    assert len(all_events(client)) == 3


def test_restart_does_not_replay_a_finished_batch(tmp_path, client, life, clock, provider):
    clock.advance(timedelta(days=1))
    reconcile(client)
    reopened = create_app(tmp_path / 'workspace' / 'companion.sqlite3', clock=clock, vault=MemoryVault(),
                          provider=provider, life_tasks=False)
    assert asyncio.run(reopened.state.life.reconcile())['state'] == 'not_due'
    assert len(all_events(client)) == 3 and len(life_requests(provider)) == 3


def test_double_launch_runs_one_batch(tmp_path, client, life, clock, provider):
    clock.advance(timedelta(days=1))
    provider.delay = 0.01
    first = create_app(tmp_path / 'workspace' / 'companion.sqlite3', clock=clock, vault=MemoryVault(),
                       provider=provider, life_tasks=False)
    second = create_app(tmp_path / 'workspace' / 'companion.sqlite3', clock=clock, vault=MemoryVault(),
                        provider=provider, life_tasks=False)

    async def both():
        return await asyncio.gather(first.state.life.reconcile(), second.state.life.reconcile())

    states = sorted(result['state'] for result in asyncio.run(both()))
    assert states == ['in_progress', 'started']
    assert len(client.get('/api/life/runs').json()) == 1
    assert len(all_events(client)) == 3 and len(life_requests(provider)) == 3


def test_a_batch_left_running_by_a_crash_resumes_without_duplicates(app, client, life, clock, provider):
    clock.advance(timedelta(days=1))
    calls = []

    def fail_second(system, messages):
        calls.append(1)
        if len(calls) == 2:
            raise BackgroundInterrupted()  # a conversation took priority
        return life_reply(system, messages)

    provider.respond = fail_second
    run = reconcile(client)['run']
    assert run['status'] == 'interrupted' and len(run['results']) == 1
    # Simulate a process that died mid-batch: its lease is held by an owner that no longer exists.
    with app.state.database.connect(write=True) as connection:
        connection.execute("UPDATE life_runs SET status='running', owner='gone', lease_until=?",
                           ((clock.now() + timedelta(minutes=5)).isoformat(),))
    assert reconcile(client)['state'] == 'in_progress'
    clock.advance(timedelta(minutes=11))
    resumed = reconcile(client)
    assert resumed['state'] == 'resumed' and resumed['run']['status'] == 'completed'
    assert resumed['run']['attempts'] == 2
    keys = [event['idempotency_key'] for event in all_events(client)]
    assert len(keys) == 3 == len(set(keys))


def test_clock_rollback_never_replays_simulated_time(client, life, clock):
    clock.advance(timedelta(days=1))
    first = reconcile(client)['run']
    clock.advance(timedelta(hours=-6))
    assert reconcile(client)['state'] == 'clock_behind'
    assert client.get('/api/life/routine').json()['clock_behind'] is True
    clock.advance(timedelta(hours=7))
    assert reconcile(client)['state'] == 'not_due'
    clock.advance(timedelta(hours=8))
    later = reconcile(client)['run']
    assert later['window_start'] == first['window_end']
    for slot in later['plan']:
        assert parse(slot['starts_at']) >= parse(first['window_end'])
    keys = [event['idempotency_key'] for event in all_events(client)]
    assert len(keys) == len(set(keys))


def test_fourteen_day_absence_is_one_capped_batch(client, life, clock, provider):
    clock.advance(timedelta(days=14))
    run = reconcile(client)['run']
    assert len(run['plan']) == 3 and len(life_requests(provider)) == 3
    lookback = clock.now() - timedelta(hours=48)
    assert all(parse(slot['starts_at']) >= lookback for slot in run['plan'])
    assert reconcile(client)['state'] == 'not_due'
    assert len(client.get('/api/life/runs').json()) == 1


def test_catch_up_limits_are_user_visible_and_bounded(client, life, clock):
    limits = client.get('/api/life/settings').json()
    assert limits['catch_up_max_events'] == 3 and limits['automatic_events'] is False
    assert client.put('/api/life/settings', json={'catch_up_max_events': 50}).status_code == 422
    set_life(client, catch_up_max_events=1)
    clock.advance(timedelta(days=2))
    assert len(reconcile(client)['run']['plan']) == 1


def test_pause_skips_the_paused_interval_and_re_anchors(client, life, clock):
    clock.advance(timedelta(hours=1))
    client.post('/api/pause')
    clock.advance(timedelta(days=2))
    assert reconcile(client)['state'] == 'paused'
    client.post('/api/resume')
    resumed_at = clock.now()
    run = reconcile(client)['run']
    assert run['plan'] == [] and run['status'] == 'completed'
    clock.advance(timedelta(days=1))
    later = reconcile(client)['run']
    assert later['plan'] and all(parse(slot['starts_at']) >= resumed_at for slot in later['plan'])


def test_timezone_change_never_simulates_the_same_time_twice(client, life, clock):
    clock.advance(timedelta(days=1))
    first = reconcile(client)['run']
    revise_character(client, timezone='Asia/Tokyo')
    clock.advance(timedelta(days=1))
    later = reconcile(client)['run']
    assert later['plan']
    for slot in later['plan']:
        assert parse(slot['starts_at']) >= parse(first['window_end'])
    keys = [event['idempotency_key'] for event in all_events(client)]
    assert len(keys) == len(set(keys))


def test_daylight_saving_changes_keep_one_slot_per_block_and_day():
    block = routine.Block('late', 'Late walk', 'leisure', tuple(range(7)), routine.clock_time('01:30'),
                          routine.clock_time('02:30'), ())
    fall = routine.slots([block], 'America/New_York', datetime(2026, 10, 31, tzinfo=UTC),
                         datetime(2026, 11, 3, tzinfo=UTC))
    dates = [slot.local_date for slot in fall]
    assert len(dates) == len(set(dates)) and date(2026, 11, 1) in dates
    repeated = next(slot for slot in fall if slot.local_date == date(2026, 11, 1))
    assert repeated.ends_at - repeated.starts_at == timedelta(hours=2)  # 01:30 EDT to 02:30 EST
    spring = routine.slots([block], 'America/New_York', datetime(2027, 3, 13, tzinfo=UTC),
                           datetime(2027, 3, 16, tzinfo=UTC))
    assert len({slot.local_date for slot in spring}) == len(spring)
    assert all(slot.ends_at > slot.starts_at for slot in spring)


def test_catch_up_across_a_dst_change_commits_each_slot_once(client, life, clock):
    revise_character(client, timezone='America/New_York')
    set_life(client, automatic_events=True, catch_up_max_events=6, catch_up_lookback_hours=72)
    clock.instant = datetime(2026, 11, 2, 16, 0, tzinfo=UTC)
    run = reconcile(client)['run']
    assert len(run['plan']) == 6
    keys = [slot['key'] for slot in run['plan']]
    assert len(keys) == len(set(keys))
    assert any(key.endswith('2026-11-01') for key in keys)


def test_character_change_while_writing_rejects_the_event(app, client, life, clock, provider, companion):
    clock.advance(timedelta(days=1))
    set_life(client, catch_up_max_events=1)

    def change_character():
        provider.before_finish = None
        with app.state.database.connect() as connection:
            current = characters.current(connection)
        definition = {**current['version']['definition'], 'routine': 'Night shifts'}
        characters.revise(app.state.database, CharacterRevision(definition=definition,
                                                     expected_version_id=current['active_version_id']))

    provider.before_finish = change_character
    run = reconcile(client)['run']
    assert run['results'][0]['outcome'] == 'rejected'
    assert 'character changed' in run['results'][0]['reason']
    assert client.get('/api/events').json() == []


def test_without_a_model_events_use_template_wording(client, companion, clock, provider, monkeypatch):
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(composer, 'PLAN_SHARE', 0)
    monkeypatch.setattr(composer, 'THREAD_SHARE', 0)
    clock.advance(timedelta(days=1))
    run = reconcile(client)['run']
    assert [item['outcome'] for item in run['results']] == ['proposed'] * 3
    assert provider.requests == []
    for event in all_events(client):
        assert event['inputs']['wording'] == 'template' and event['summary'] == event['inputs']['template']['summary']


def test_a_model_problem_keeps_the_template_wording(client, life, clock, provider):
    provider.respond = lambda system, messages: [Chunk('not json'), Chunk('', 'stop')]
    set_life(client, catch_up_max_events=1)
    clock.advance(timedelta(days=1))
    reconcile(client)
    event = all_events(client)[0]
    assert event['inputs']['wording'] == 'template' and 'phrasing_error' in event['inputs']
    assert event['summary'] == event['inputs']['template']['summary']


def test_phrasing_that_copies_the_block_times_is_not_used():
    composed = {'place': {'name': 'Federal Hill Park'}}
    good = '{"summary": "He walked at Federal Hill Park.", "post": "needed that air."}'
    assert synthesis.parse_reply(good, composed)['post'] == 'needed that air.'
    with pytest.raises(synthesis.SynthesisInvalid):
        synthesis.parse_reply(good.replace('needed that air.', 'needed that air. 17:30-19:30 at the park.'), composed)


def test_model_phrasing_can_be_turned_off(client, life, clock, provider):
    set_life(client, phrase_with_model=False)
    clock.advance(timedelta(days=1))
    reconcile(client)
    assert life_requests(provider) == [] and len(all_events(client)) == 3


def test_places_come_from_the_world_source(tmp_path, clock, provider, monkeypatch):
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(composer, 'PLAN_SHARE', 0)
    monkeypatch.setattr(composer, 'THREAD_SHARE', 0)
    world = StaticWorld([Place('patterson', 'Patterson Park', 'park', 'baltimore', 'Highlandtown'),
                         Place('artifact', 'Artifact Coffee', 'cafe', 'baltimore', 'Hampden'),
                         Place('walters', 'The Walters Art Museum', 'museum', 'baltimore', 'Mount Vernon'),
                         Place('lexington', 'Lexington Market', 'market', 'baltimore', 'Downtown'),
                         Place('y', 'Central YMCA', 'gym', 'baltimore', 'Mount Vernon')])
    app = create_app(tmp_path / 'world.sqlite3', clock=clock, vault=MemoryVault(), provider=provider,
                     life_tasks=False, world=world)
    with TestClient(app, headers={CLIENT_HEADER: 'workspace'}) as client:
        client.post('/api/companion', json={'name': 'Mira', 'timezone': 'America/New_York',
                                            'home_city': 'baltimore'})
        set_life(client, catch_up_max_events=6, catch_up_lookback_hours=96)
        clock.advance(timedelta(days=4))
        reconcile(client)
        placed = [event for event in all_events(client) if event['details']['place']]
        assert placed
        for event in placed:
            assert event['details']['place']['name'] in event['summary']
            assert event['inputs']['world'] == 'static'


def test_background_needs_permission_and_respects_the_daily_cap(app, client, life, clock):
    engine = app.state.life
    assert asyncio.run(engine.reconcile('background'))['state'] == 'not_permitted'
    client.put('/api/settings', json={'background_activity': True})
    set_life(client, background_daily_events=1, automatic_events=True)
    clock.advance(timedelta(hours=20))
    first = asyncio.run(engine.reconcile('background'))
    assert first['state'] == 'started' and len(first['run']['plan']) == 1
    clock.advance(timedelta(minutes=30))
    assert asyncio.run(engine.reconcile('background'))['state'] == 'not_due'
    clock.advance(timedelta(hours=5))
    assert asyncio.run(engine.reconcile('background'))['run']['plan'] == []


def test_today_routine_reports_the_current_block(client, companion, clock):
    clock.instant = datetime(2026, 10, 6, 10, 0, tzinfo=UTC)  # 11:00 in Lisbon
    view = client.get('/api/life/routine').json()
    assert view['default_schedule'] is True
    assert view['current']['block']['key'] == 'morning'
    assert view['next']['block']['key'] == 'afternoon'


def test_schedule_validation(client, companion):
    current = client.get('/api/companion').json()['companion']
    definition = {**current['version']['definition'],
                  'schedule': [{'label': 'Bakery shift', 'kind': 'work', 'start': '06:00', 'end': '06:00'}]}
    response = client.post('/api/companion/versions', json={'definition': definition,
                                                            'expected_version_id': current['active_version_id']})
    assert response.status_code == 422


def test_a_paused_interval_can_be_caught_up_once_on_request(client, life, clock):
    set_life(client, automatic_events=True)
    client.post('/api/pause')
    clock.advance(timedelta(days=2))
    assert client.post(f"/api/life/pauses/{client.get('/api/life/pauses').json()[0]['id']}/catch-up").status_code == 409
    client.post('/api/resume')
    pause = client.get('/api/life/pauses').json()[0]
    assert reconcile(client)['run']['plan'] == []
    first = client.post(f"/api/life/pauses/{pause['id']}/catch-up").json()
    assert first['state'] == 'started' and len(first['run']['plan']) == 3
    assert {item['outcome'] for item in first['run']['results']} == {'committed'}
    for slot in first['run']['plan']:
        assert pause['started_at'] <= slot['starts_at'] and slot['ends_at'] <= pause['ended_at']
    again = client.post(f"/api/life/pauses/{pause['id']}/catch-up").json()
    assert again['state'] == 'already_done' and again['run']['id'] == first['run']['id']
    assert client.get('/api/life/pauses').json()[0]['catch_up_run_id'] == first['run']['id']
    assert len(client.get('/api/events').json()) == 3


def test_a_plan_is_not_an_outing_until_its_slot_happens(client, life, clock, monkeypatch):
    monkeypatch.setattr(composer, 'PLAN_SHARE', 1)
    set_life(client, automatic_events=True, catch_up_max_events=1)
    clock.advance(timedelta(days=1))
    result = reconcile(client)['run']['results'][0]
    assert result['plan_outcome'] == 'committed'
    plan = next(event for event in all_events(client) if event['id'] == result['plan_event_id'])
    assert plan['kind'] == 'plan' and 'is planning to' in plan['summary']
    assert parse(plan['starts_at']) > clock.now()
    today = client.get('/api/today').json()
    assert [item['id'] for item in today['plans']['companion']] == [plan['id']]
    # Nothing has happened yet: the only ordinary event is the one the plan was made during.
    assert len([event for event in all_events(client) if event['kind'] == 'ordinary']) == 1
    monkeypatch.setattr(composer, 'PLAN_SHARE', 0)
    monkeypatch.setattr(composer, 'THREAD_SHARE', 0)
    clock.instant = parse(plan['ends_at']) + timedelta(hours=5)
    reconcile(client)
    fulfilled = [event for event in all_events(client) if event['details'].get('fulfils') == plan['id']]
    assert len(fulfilled) == 1 and fulfilled[0]['summary'].endswith('as planned.')
    assert fulfilled[0]['details']['slot'] == plan['details']['target_slot']
    assert client.get('/api/today').json()['plans']['companion'] == []


def test_the_shipped_city_data_is_the_default_world(tmp_path, clock, provider, monkeypatch):
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(composer, 'PLAN_SHARE', 0)
    monkeypatch.setattr(composer, 'THREAD_SHARE', 0)
    app = create_app(tmp_path / 'city.sqlite3', clock=clock, vault=MemoryVault(), provider=provider,
                     life_tasks=False)
    with TestClient(app, headers={CLIENT_HEADER: 'workspace'}) as client:
        # No home_city: the free-text location is enough to find the city.
        client.post('/api/companion', json={'name': 'Mira', 'timezone': 'America/New_York',
                                            'location': 'Fells Point, Baltimore'})
        set_life(client, catch_up_max_events=6, catch_up_lookback_hours=96, phrase_with_model=False)
        clock.advance(timedelta(days=4))
        reconcile(client)
        placed = [event for event in all_events(client) if event['details']['place']]
        assert placed
        for event in placed:
            assert event['details']['place']['city'] == 'Baltimore'
            assert event['details']['place']['name'] in event['summary']
            assert event['inputs']['world'] == 'catalog'


def test_an_open_thread_settles_a_few_days_later(client, life, clock, monkeypatch):
    monkeypatch.setattr(composer, 'THREAD_SHARE', 1)
    set_life(client, catch_up_max_events=1)
    clock.advance(timedelta(days=1))
    result = reconcile(client)['run']['results'][0]
    opened = next(event for event in all_events(client) if event['id'] == result['thread_event_id'])
    assert opened['kind'] == 'thread' and opened['details']['state'] == 'open'
    assert result['thread_outcome'] == 'proposed'
    # Only committed threads are on the companion's mind, and only one thread is open at a time.
    assert client.get('/api/today').json()['plans']['threads'] == []
    client.post(f"/api/events/{opened['id']}/commit")
    assert [item['id'] for item in client.get('/api/today').json()['plans']['threads']] == [opened['id']]
    set_life(client, automatic_events=True)
    settled = None
    for _ in range(6):
        clock.advance(timedelta(days=1))
        for item in reconcile(client)['run']['results']:
            if item.get('thread_event_id') and item['thread_event_id'] != opened['id']:
                settled = next(event for event in all_events(client) if event['id'] == item['thread_event_id'])
        if settled:
            break
    assert settled and settled['details'] == {**settled['details'], 'state': 'settled',
                                              'thread_key': opened['details']['thread_key']}
    assert settled['details']['local_date'] >= opened['details']['settles_on']
    ending = composer.find_thread(opened['details']['thread']).endings
    assert settled['summary'] in [text.format(name='Mira') for text in ending]
    assert client.get('/api/today').json()['plans']['threads'] == []


def test_interests_make_matching_activities_more_likely(monkeypatch):
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    block = {'key': 'free', 'label': 'Free time', 'kind': 'leisure', 'start': '13:00', 'end': '17:00'}
    world = StaticWorld([])

    def share(definition):
        picks = [composer.compose({'key': f'free@{n}', 'local_date': '2026-10-05', 'block': block}, definition, world,
                                  f'seed-{n}')['activity'] for n in range(400)]
        return picks.count('reading') / len(picks)

    plain, bookish = share({'name': 'Mira'}), share({'name': 'Mira', 'interests': ['Books and old novels']})
    assert bookish > plain * 1.8
    assert composer.leanings({'interests': ['party planning', 'artichokes'], 'life_themes': ['team building']}) == set()
    assert composer.leanings({'interests': ['art'], 'life_themes': ['learning to bake']}) == {'museum', 'home-cooking'}


def test_catch_up_work_leaves_the_event_loop_free_for_chat(app, life, clock, monkeypatch):
    """Database work and composition run on a worker thread, so a slow catch-up never stalls a streaming reply."""
    from companion.life import agenda
    extend = agenda.extend

    def slow_extend(*args, **kwargs):
        time.sleep(0.3)  # a large circle's agenda, standing in
        return extend(*args, **kwargs)

    monkeypatch.setattr(agenda, 'extend', slow_extend)
    clock.advance(timedelta(days=1))

    async def main():
        ticks = 0

        async def ticker():
            nonlocal ticks
            while True:
                await asyncio.sleep(0.01)
                ticks += 1

        task = asyncio.create_task(ticker())
        result = await app.state.life.reconcile('return')
        task.cancel()
        return result, ticks

    result, ticks = asyncio.run(main())
    assert result['run']['status'] == 'completed'
    assert ticks >= 10


def test_a_block_named_for_an_activity_reads_as_a_time_of_day():
    assert composer.span({'label': 'Solo gaming', 'kind': 'leisure', 'start': '20:00'}) == 'evening'
    assert composer.span({'label': 'Stage performer', 'kind': 'work', 'start': '16:00'}) == 'shift'
    assert composer.span({'label': 'Free time after work', 'kind': 'leisure'}) == 'free time after work'
    assert composer.span({'label': 'Day off', 'kind': 'leisure'}) == 'day off'


def test_background_ticks_catch_blocks_that_were_still_going(app, client, life, clock):
    """The cursor moves every hour while most blocks last longer; a block in progress is not lost."""
    client.put('/api/settings', json={'background_activity': True})
    set_life(client, background_daily_events=8, automatic_events=True)
    asyncio.run(app.state.life.reconcile('background'))
    for _hour in range(24):
        clock.advance(timedelta(hours=1))
        asyncio.run(app.state.life.reconcile('background'))
    keys = [event['idempotency_key'] for event in all_events(client)]
    assert len(keys) >= 3 and len(keys) == len(set(keys))
