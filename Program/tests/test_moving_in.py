"""Moving in together (companion/life/moving_in.py): whose place or who moves, moving day, the shared home and rent,
evenings at home, moving out, a different time zone counting as long distance, and plans a move made long distance."""
from datetime import date, timedelta

import pytest
from conftest import reconcile, send, show
from test_long_distance import apart_from
from test_together import mira, notes, says, where

from companion import consequences
from companion.characters import current
from companion.database import optional
from companion.life import home, money, moving_in, steps
from companion.life import where as where_module


def test_moving_in_and_being_out_are_read_from_the_message():
    assert steps.raised('Should we move in together?', ['moving_in']) == 'moving_in'
    assert steps.raised('can we get a place together?', ['moving_in']) == 'moving_in'
    assert steps.raised("I don't want to live together yet", ['moving_in']) is None
    assert steps.raised('they live together now?', ['moving_in']) == 'moving_in'
    assert moving_in.OUT.search("I'm out with Sam, back later")
    assert moving_in.OUT.search('heading out for drinks')
    assert moving_in.HOME.search("I'm home!")
    assert moving_in.HOME.search('just got home')
    assert not moving_in.OUT.search('how was your day?')


@pytest.fixture
def always(monkeypatch):
    """The engine lands on the first option every time."""
    monkeypatch.setattr(consequences, 'roll', lambda _seed, found: found[0]['option'])


def pick(monkeypatch, choice: str, option: int):
    """The engine lands on `option` for `choice`, and on the first option for everything else."""
    real = consequences.decide

    def decide(connection, **values):
        if values['choice'] == choice:
            monkeypatch.setattr(consequences, 'roll', lambda _seed, found: found[option]['option'])
        else:
            monkeypatch.setattr(consequences, 'roll', lambda _seed, found: found[0]['option'])
        return real(connection, **values)
    monkeypatch.setattr(consequences, 'decide', decide)


def set_step(client, step):
    response = client.put('/api/life/steps', json={'step': step})
    assert response.status_code == 200, response.text
    return response.json()


def row(client):
    with client.app.state.database.connect() as connection:
        return moving_in.current(connection, current(connection)['active_timeline_id'])


def ask_to_move_in(client, provider, client_id='client-move-1'):
    set_step(client, 'key')
    says(provider)
    send(client, 'Should we move in together?', client_id)


def moving_day(client, clock):
    found = row(client)
    days = (date.fromisoformat(found['move_on']) - clock.now().date()).days
    clock.advance(timedelta(days=days, hours=1))
    reconcile(client)


def test_asked_in_the_same_city_they_move_into_your_place(client, provider, clock, monkeypatch, always):
    mira(client, monkeypatch, relationship='romance')
    ask_to_move_in(client, provider)
    found = row(client)
    assert (found['plan'], found['status'], found['city_id']) == ('yours', 'moving', 'baltimore')
    assert 10 <= (date.fromisoformat(found['move_on']) - date(2026, 10, 5)).days <= 28
    assert "You're moving into the user's place in" in notes(provider)
    assert 'You just agreed to live together' in notes(provider)
    assert client.get('/api/life/steps').json()['moving_in']['plan'] == 'yours'
    moving_day(client, clock)
    found = row(client)
    assert found['status'] == 'moved'
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        yours = where_module.your_home(connection)[1]
        assert companion['version']['definition']['location'].startswith(yours['name'])
        shared = moving_in.their_home(connection, companion, clock.now().date())
        assert shared['shared'] and shared['neighborhood'] == yours['name']
        costs = money.household(connection, companion['active_timeline_id'], companion['version']['definition'],
                                clock.now().date())['costs']
        assert costs['shared'] and costs['rent'] == round(shared['rent'] / 2, 2)
    view = client.get('/api/life/steps').json()
    assert view['step'] == 'moving_in' and view['moving_in']['status'] == 'moved' and view['moving_in']['home']


def test_evenings_at_home_are_together_and_texting_while_you_are_out(client, provider, clock, monkeypatch, always):
    mira(client, monkeypatch, relationship='romance')
    ask_to_move_in(client, provider)
    moving_day(client, clock)
    clock.advance(timedelta(hours=-clock.now().hour + 12))
    assert where(client)['state'] == 'apart'  # Midday: at work.
    clock.advance(timedelta(hours=7))  # 19:00.
    found = where(client)
    assert (found['state'], found['kind'], found['text']) == ('together', 'home', 'Home together')
    assert found['home'] == {'status': 'home'}
    says(provider)
    send(client, 'what should we have for dinner?', 'client-move-2')
    assert 'You and the user live together, ' in notes(provider)
    assert 'you are both home, together in person' in notes(provider)
    assert 'You split the rent and the bills.' in notes(provider)
    says(provider)
    send(client, "I'm out with Sam for a bit", 'client-move-3')
    assert where(client)['state'] == 'apart' and where(client)['home']['status'] == 'out'
    says(provider)
    send(client, "ok I'm home!", 'client-move-4')
    assert where(client)['kind'] == 'home'
    response = client.post('/api/life/living/out', json={})
    assert response.status_code == 200 and response.json()['home']['status'] == 'out'
    # Living together, nobody knocks or comes over.
    with client.app.state.database.connect() as connection:
        from companion.life import together
        assert together.lives_with_you(connection, current(connection))
        assert not together.invites(connection, current(connection))


def test_chores_go_by_turns(client, monkeypatch):
    mira(client, monkeypatch, relationship='romance')
    with client.app.state.database.connect() as connection:
        companion = current(connection)
    monday, saturday = date(2026, 10, 5), date(2026, 10, 10)
    assert moving_in.turn(companion, monday, 'cooking') == 'user'  # A work day for them.
    assert moving_in.turn(companion, monday, 'dishes') == 'you'
    week = {moving_in.turn(companion, saturday + timedelta(days=offset), 'cooking') for offset in range(2)}
    assert week == {'you', 'user'}
    assert moving_in.turn(companion, monday, 'laundry') != moving_in.turn(companion, monday + timedelta(days=7),
                                                                         'laundry')


def test_a_different_place_can_be_picked_under_hidden_values(client, provider, clock, monkeypatch, always):
    mira(client, monkeypatch, relationship='romance')
    show(client, show_odds=True)
    ask_to_move_in(client, provider)
    consequence = client.get('/api/life/steps').json()['moving_in']['consequence_id']
    response = client.post(f'/api/life/consequences/{consequence}/change', json={'option': 1})
    assert response.status_code == 200, response.text
    assert row(client)['plan'] == 'theirs'
    moving_day(client, clock)
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        theirs = moving_in.their_home(connection, companion, clock.now().date())
        assert where_module.your_home(connection)[1]['name'] == theirs['neighborhood']
    response = client.post(f'/api/life/consequences/{consequence}/change', json={'option': 2})
    assert response.status_code == 409


def test_across_the_distance_they_move_to_your_city(client, provider, clock, monkeypatch, always):
    apart_from(client, monkeypatch, relationship='romance')
    reconcile(client)
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        connection.execute("UPDATE circle_people SET id='cw1', role='coworker' WHERE timeline_id=? AND ordinal=("
                           'SELECT MIN(ordinal) FROM circle_people WHERE timeline_id=?)',
                           (companion['active_timeline_id'], companion['active_timeline_id']))
    ask_to_move_in(client, provider)
    found = row(client)
    assert (found['plan'], found['status'], found['city_id']) == ('them', 'moving', 'baltimore')
    assert "You're moving to Baltimore to live with the user" in notes(provider)
    assert where(client)['kind'] == 'long-distance'
    moving_day(client, clock)
    assert row(client)['status'] == 'moved'
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        assert companion['version']['timezone'] == 'America/New_York'
        assert companion['version']['definition']['home_city'] == 'Baltimore'
        assert not where_module.between(connection, companion['version']['definition']).long_distance
        assert optional(connection, "SELECT status FROM circle_people WHERE id='cw1'")['status'] == 'removed'
        chapter = optional(connection, "SELECT * FROM life_chapters WHERE kind='move_in'")
        assert chapter['title'] == 'Mira moved to Baltimore to live with you'
    assert where(client)['kind'] != 'long-distance'


def test_they_can_ask_you_to_move_and_it_waits_for_you(client, provider, clock, monkeypatch):
    world = apart_from(client, monkeypatch, relationship='romance')
    pick(monkeypatch, 'moving_in:who', 1)
    ask_to_move_in(client, provider)
    found = row(client)
    assert (found['plan'], found['status']) == ('you', 'waiting')
    assert 'You asked the user to move to Chicago to live with you' in notes(provider)
    clock.advance(timedelta(days=40))
    reconcile(client)
    assert row(client)['status'] == 'waiting'  # Never forced: it waits for the user's own move.
    assert client.put(f"/api/worlds/{world['id']}/home", json={'city_id': 'chicago'}).status_code == 200
    reconcile(client)
    assert row(client)['status'] == 'moved'
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        theirs = moving_in.their_home(connection, companion, clock.now().astimezone(
            where_module.zone(companion['version']['timezone'])).date())
        assert where_module.your_home(connection)[1]['name'] == theirs['neighborhood']


def test_taking_the_step_back_moves_out(client, provider, clock, monkeypatch, always):
    mira(client, monkeypatch, relationship='romance')
    ask_to_move_in(client, provider)
    moving_day(client, clock)
    set_step(client, 'key')
    found = None
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        found = moving_in.latest(connection, companion['active_timeline_id'])
        assert (found['status'], found['out_who']) == ('moved_out', 'them')
        assert optional(connection, "SELECT title FROM life_chapters WHERE kind='move_out'")['title'].startswith(
            'Mira moved out, to ')
        assert not home.items_on(connection, companion['active_timeline_id'], clock.now().date())[0].get('shared')
    says(provider)
    send(client, 'hey', 'client-move-5')
    assert 'You moved out of the place you shared' in notes(provider)


def test_a_plan_not_yet_carried_out_is_dropped(client, provider, monkeypatch, always):
    mira(client, monkeypatch, relationship='romance')
    ask_to_move_in(client, provider)
    set_step(client, 'key')
    with client.app.state.database.connect() as connection:
        found = moving_in.latest(connection, current(connection)['active_timeline_id'])
    assert found['status'] == 'moved_out' and found['out_who'] is None


def test_another_time_zone_counts_as_long_distance(client, provider, monkeypatch):
    mira(client, monkeypatch, relationship='romance', home_city='', location='', timezone='Asia/Tokyo')
    found = where(client)
    assert found['kind'] == 'long-distance' and found['text'].startswith('Long distance, Tokyo, ')
    says(provider)
    send(client, 'come over?', 'client-move-6')
    assert "you live in Tokyo, so you can't just come over" in notes(provider)


def test_the_same_time_zone_with_no_city_stays_nearby(client, monkeypatch):
    mira(client, monkeypatch, relationship='romance', home_city='', location='', timezone='America/Detroit')
    assert where(client)['kind'] == 'apart'


def test_plans_a_move_made_long_distance_are_called_off(client, provider, clock, monkeypatch):
    world = apart_from(client, monkeypatch, city='Baltimore', timezone='America/New_York', relationship='romance')
    assert client.put(f"/api/worlds/{world['id']}/home", json={'city_id': 'baltimore'}).status_code == 200
    says(provider)
    send(client, 'dinner on Thursday at 7?', 'client-move-7')
    [outing] = client.get('/api/life/outings').json()['outings']
    assert outing['status'] == 'planned'
    assert client.put(f"/api/worlds/{world['id']}/home", json={'city_id': 'chicago'}).status_code == 200
    [outing] = client.get('/api/life/outings').json()['outings']
    assert (outing['status'], outing['place']['far']) == ('cancelled', 'off'), outing
    says(provider)
    send(client, 'hey, so I moved', 'client-move-8')
    assert "can't happen and is called off" in notes(provider)


def test_a_couple_who_already_live_together_share_their_place(client, provider, monkeypatch):
    mira(client, monkeypatch, relationship='romance', history_together='We have been married for ten years.')
    reconcile(client)
    found = row(client)
    assert (found['plan'], found['status']) == ('theirs', 'moved')
    says(provider)
    send(client, 'hey love', 'client-move-9')
    assert 'You and the user live together, ' in notes(provider)
    assert 'You have decided to live together' not in notes(provider)  # Married: the steps line says so.


def test_a_chore_left_undone_on_your_turn_can_start_a_small_rough_patch(client, provider, clock, monkeypatch, always):
    from companion.life import rough_patches
    mira(client, monkeypatch, relationship='romance')
    ask_to_move_in(client, provider)
    moving_day(client, clock)
    seen = []
    monkeypatch.setattr(rough_patches, 'friction', lambda connection, companion, cause, subject, about, now, shown='':
                        seen.append((cause, subject, about, shown)))
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        today = moving_in.local_today(companion, clock.now())
        living = moving_in.living(connection, companion, today)
        mine = next(task for task in moving_in.TASKS if moving_in.turn(companion, today, task) == 'user')
        theirs = next(task for task in moving_in.TASKS if moving_in.turn(companion, today, task) == 'you')
        words = {'cooking': 'cook', 'dishes': 'dishes', 'laundry': 'laundry', 'tidying': 'tidy up'}
        moving_in.skipped(connection, companion, living, f"ugh I forgot to do the {words[theirs]}", clock.now())
        assert seen == []  # Their turn, not the user's.
        moving_in.skipped(connection, companion, living, f"sorry, I totally forgot the {words[mine]}", clock.now())
    assert seen and seen[0][0] == 'chore' and moving_in.CHORES[mine] in seen[0][3]
    assert moving_in.SKIPPED.search("I didn't get round to the washing up") and not moving_in.SKIPPED.search('dinner was great')


def test_the_dishes_go_to_whoever_did_not_cook_every_day(client, monkeypatch):
    mira(client, monkeypatch, relationship='romance')
    with client.app.state.database.connect() as connection:
        companion = current(connection)
    for timeline in range(8):  # The turns are seeded by the timeline: a few of them.
        other = {**companion, 'active_timeline_id': f'timeline-{timeline}'}
        for offset in range(14):
            day = date(2026, 10, 5) + timedelta(days=offset)
            assert moving_in.turn(other, day, 'cooking') != moving_in.turn(other, day, 'dishes'), (timeline, day)


def test_a_fork_from_before_moving_day_moves_in_again_on_its_own(client, provider, clock, monkeypatch, always):
    mira(client, monkeypatch, relationship='romance')
    ask_to_move_in(client, provider)
    sent = client.get('/api/conversation').json()['messages'][-1]
    clock.advance(timedelta(days=1))
    says(provider)
    send(client, 'packing tomorrow', 'client-move-fork-1')  # The fork point is before moving day.
    moving_day(client, clock)
    assert row(client)['status'] == 'moved'
    fork = client.post('/api/timelines', json={'message_id': sent['id']}).json()
    assert client.post(f"/api/timelines/{fork['id']}/activate").status_code == 200
    found = row(client)
    assert (found['timeline_id'], found['status'], found['moved_on']) == (fork['id'], 'moving', None)
    consequence = client.get(f"/api/life/consequences/{found['consequence_id']}").json()
    assert consequence['timeline_id'] == fork['id']
    reconcile(client)
    assert row(client)['status'] == 'moved'
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        shared = moving_in.their_home(connection, companion, clock.now().date())
        assert shared['shared'] and optional(connection, "SELECT id FROM life_chapters WHERE kind='move_in' AND "
                                             'timeline_id=?', (fork['id'],))


def test_asking_what_to_have_for_dinner_at_home_is_not_going_out(client, provider, clock, monkeypatch, always):
    mira(client, monkeypatch, relationship='romance')
    ask_to_move_in(client, provider)
    moving_day(client, clock)
    says(provider)
    send(client, 'what should we have for dinner?', 'client-move-dinner-1')
    assert client.get('/api/life/outings').json()['outings'] == []
