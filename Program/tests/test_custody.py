"""When families change (companion/life/custody.py): custody after a breakup with children shared, long distance with
a child, a companion's own child after they split from their partner, and the parents loss spares."""
import re
from datetime import date, timedelta

import pytest
from conftest import intimate, reconcile, send
from test_expecting import likeliest, to  # noqa: F401 - likeliest is a fixture
from test_our_child import aged, born, connect, ours
from test_steps import prompt, says

from companion import consequences
from companion.characters import current
from companion.database import identifier
from companion.life import breakups, custody, loss, our_child, steps

pytestmark = pytest.mark.usefixtures('likeliest')


@pytest.fixture
def split(client, provider, clock, monkeypatch):
    """A child of the pair, two hundred days old, and the user ending it in the chat."""
    monkeypatch.setattr(breakups, 'ACTIVE', True)
    row, child = born(client, clock, monkeypatch)
    aged(client, child, 200)
    says(provider)
    send(client, "I'm breaking up with you.", 'client-custody-0')
    with connect(client) as connection:
        assert breakups.ended(connection, current(connection))
    return child


def state(client):
    with connect(client) as connection:
        return custody.found(connection, current(connection))


def test_the_odds_say_why_for_every_reason():
    table = consequences.tables()[custody.CHOICE]
    assert [option['label'] for option in table['options']] == [custody.LABELS[key] for key in custody.PATTERNS]
    for option in table['options']:
        assert all(rule['why'][0].islower() or rule['why'].startswith('{name}') for rule in option['rules'])


def test_together_under_one_roof_there_is_no_custody(client, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    assert state(client) is None and ours(client)['custody'] is None
    with connect(client) as connection:
        assert custody.here(connection, current(connection), date(2030, 1, 5))


def test_a_breakup_shares_the_children_and_the_app_picks_where_they_live(client, split, provider, clock):
    found = state(client)
    assert found['split'] and found['pattern'] in custody.PATTERNS and found['how'] == 'seeded'
    reconcile(client)  # The daily pass records the pick.
    with connect(client) as connection:
        companion = current(connection)
        recorded = consequences.recorded(connection, custody.subject(companion, custody.ended(connection, companion)),
                                         custody.CHOICE)
    assert recorded and custody.PATTERNS[recorded['picked']] == state(client)['pattern']
    view = ours(client)
    assert view['custody']['split'] and len(view['custody']['patterns']) == 3 and view['care_now'] is False
    says(provider)
    send(client, 'how is the little one?', 'client-custody-1')
    text = prompt(provider)
    first = split['name'].split()[0]
    assert f'- Since you and the user split up, {first} ' in text
    assert "yours and the user's" in text  # Still both of theirs.


def test_the_user_sets_where_they_live_and_the_weeks_alternate(client, split, provider, clock):
    view = ours(client, custody='shared')
    assert view['custody']['pattern'] == 'shared' and view['custody']['how'] == 'set'
    with connect(client) as connection:
        companion = current(connection)
        found = custody.found(connection, companion)
        monday = found['since']
        assert custody.with_them(found, monday) and not custody.with_them(found, monday + timedelta(days=7))
        assert custody.with_them(found, monday + timedelta(days=14))
        # Only their weeks bring broken nights, and their pay is a full one: no one stays home now.
        nights = [monday + timedelta(days=offset) for offset in range(8, 13)]
        assert not any(our_child.broken_night(connection, companion['active_timeline_id'], day) for day in nights)
        assert our_child.pay(connection, companion['active_timeline_id'], monday) == 1.0
    ours(client, custody='with_you')
    with connect(client) as connection:
        companion = current(connection)
        found = custody.found(connection, companion)
        weekdays = [found['since'] + timedelta(days=offset) for offset in range(5)]
        assert not any(custody.with_them(found, day) for day in weekdays)
        assert our_child.caring(connection, companion, weekdays[0]) is None
    assert ours(client, custody='auto')['custody']['how'] == 'seeded'


def test_whose_day_it_is_shows_on_today_and_in_the_chat(client, split, provider, clock):
    ours(client, custody='shared')
    with connect(client) as connection:
        companion = current(connection)
        found = custody.found(connection, companion)
        today = steps.local_today(companion, clock.now())
        here = custody.with_them(found, today)
    family = client.get('/api/today').json()['family']
    assert family[0]['where_today'] == ('With Mira today' if here else 'With you today') or \
        family[0]['where_today'].endswith(' today')
    says(provider)
    send(client, 'morning', 'client-custody-2')
    assert ('is with you.' if here else 'is with the user.') in prompt(provider)


def test_with_the_adult_side_on_an_intimate_reply_carries_no_child(client, split, provider):
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    intimate(client)
    says(provider)
    send(client, 'come here you', 'client-custody-3')
    text = prompt(provider)
    first = split['name'].split()[0]
    assert not re.search(rf'\b{re.escape(first)}\b', text) and 'split up, ' not in text.split('kids')[-1]


def test_setting_where_they_live_needs_a_breakup(client, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    response = client.put('/api/life/steps/ours', json={'custody': 'shared'})
    assert response.status_code == 409


def test_long_distance_the_child_stays_and_visits_are_when_the_user_sees_them(client, clock, monkeypatch, provider):
    row, child = born(client, clock, monkeypatch)
    world = client.get('/api/worlds').json()['world']
    with connect(client) as connection:
        city = custody.far(connection, current(connection))
    assert city is None
    assert client.put(f"/api/worlds/{world['id']}/home", json={'city_id': 'chicago'}).status_code == 200
    found = state(client)
    if found is None:
        pytest.skip('The companion lives in Chicago in this world.')
    assert found['far'] and not found['split'] and found['pattern'] == 'with_them'
    view = ours(client)['custody']
    assert view['far'] and view['patterns'] == []
    says(provider)
    send(client, 'hey you', 'client-custody-4')
    assert f"{child['name'].split()[0]} lives with you; the user lives in " in prompt(provider)


def test_across_cities_a_week_each_cannot_work(client, split):
    ours(client, custody='shared')
    found = {**state(client), 'far': object()}
    assert custody.with_them(found, date(2030, 1, 7)) and custody.with_them(found, date(2030, 1, 14))


def test_loss_spares_a_parent_with_a_baby_under_one_and_the_pairs_grown_child(client, clock, monkeypatch):
    row, child = born(client, clock, monkeypatch)
    with connect(client) as connection:
        companion = current(connection)
        timeline_id = companion['active_timeline_id']
        today = steps.local_today(companion, clock.now())
        person = dict(connection.execute("SELECT * FROM circle_people WHERE timeline_id=? AND status='active' "
                                         'LIMIT 1', (timeline_id,)).fetchone())
        assert not custody.spared(connection, person, today)
        connection.execute(
            'INSERT INTO circle_children (id, timeline_id, parent_id, storyline_id, name, pronouns, title, born_on, '
            "status, created_at, updated_at) VALUES (?, ?, ?, 'test', 'Ivy', 'she/her', 'family', ?, 'born', ?, ?)",
            (identifier(), timeline_id, person['id'], (today - timedelta(days=100)).isoformat(), 'x', 'x'))
        assert custody.spared(connection, person, today)
        assert not custody.spared(connection, person, today + timedelta(days=300))
        grown = {**person, 'id': 'nobody', 'details': '{"our_child": "abc"}'}
        assert custody.spared(connection, grown, today)
        assert loss.spared(connection, timeline_id, person, today)


def test_where_the_user_set_them_to_live_holds_for_that_breakup_only(client, split, provider, clock, monkeypatch):
    ours(client, custody='with_you')
    clock.advance(timedelta(days=20))
    monkeypatch.setattr(consequences, 'roll', lambda seed, found: found[-1]['option'])  # They want that too.
    says(provider)
    send(client, 'can we try again?', 'client-custody-5')
    assert state(client) is None
    clock.advance(timedelta(days=40))
    says(provider)
    send(client, "I'm breaking up with you.", 'client-custody-6')
    assert state(client)['how'] == 'seeded'  # A second breakup: the app picks afresh, and the user can set it again.


def test_undoing_getting_back_together_keeps_where_the_user_set_them_to_live(client, split):
    ours(client, custody='with_you')
    row = client.get('/api/life/breakup').json()
    assert client.post(f"/api/life/breakup/{row['id']}/mend").status_code == 200
    assert state(client) is None
    assert client.post(f"/api/life/breakup/{row['id']}/undo").status_code == 200
    assert (state(client)['pattern'], state(client)['how']) == ('with_you', 'set')


def branched(client, text='hello'):
    sent = send(client, 'hi', f'client-custody-{text}')['message']
    fork = client.post('/api/timelines', json={'message_id': sent['id'], 'text': text})
    assert fork.status_code == 200, fork.text
    assert client.post(f"/api/timelines/{fork.json()['id']}/activate").status_code == 200


def test_a_branch_after_the_breakup_keeps_where_they_live(client, split, provider, monkeypatch):
    reconcile(client)  # The app's pick, recorded.
    before = state(client)
    roll = consequences.roll

    def again(seed, found):
        assert custody.CHOICE not in seed, 'where they live was picked again'
        return roll(seed, found)
    monkeypatch.setattr(consequences, 'roll', again)
    says(provider)
    branched(client)
    after = state(client)
    assert (after['pattern'], after['how'], after['since']) == (before['pattern'], 'seeded', before['since'])
    ours(client, custody='shared')
    says(provider)
    branched(client, 'again')
    assert state(client)['pattern'] == 'shared' and state(client)['how'] == 'set'


def test_a_branch_from_before_the_breakup_forgets_where_they_were_set_to_live(client, clock, monkeypatch, provider):
    monkeypatch.setattr(breakups, 'ACTIVE', True)
    row, child = born(client, clock, monkeypatch)
    says(provider)
    sent = send(client, 'good morning', 'client-custody-7')['message']
    clock.advance(timedelta(hours=2))
    says(provider)
    send(client, "I'm breaking up with you.", 'client-custody-8')
    ours(client, custody='with_you')
    fork = client.post('/api/timelines', json={'message_id': sent['id'], 'text': 'good morning!'})
    assert fork.status_code == 200, fork.text
    client.post(f"/api/timelines/{fork.json()['id']}/activate")
    assert state(client) is None
    with connect(client) as connection:
        assert our_child.family_row(connection, current(connection)['active_timeline_id'])['custody'] is None
    says(provider)
    send(client, "I'm breaking up with you.", 'client-custody-9')
    assert state(client)['how'] == 'seeded'


def test_across_cities_the_user_is_not_the_one_home_with_them(client, clock, monkeypatch, provider):
    row, child = born(client, clock, monkeypatch)
    aged(client, child, 500)
    ours(client, care='you_home')
    world = client.get('/api/worlds').json()['world']
    assert client.put(f"/api/worlds/{world['id']}/home", json={'city_id': 'chicago'}).status_code == 200
    if state(client) is None:
        pytest.skip('The companion lives in Chicago in this world.')
    view = ours(client)
    assert view['care'] == 'both_work' and 'you_home' not in [item['key'] for item in view['cares']]
    says(provider)
    send(client, 'how is she?', 'client-custody-far-care')
    assert 'the user stays home with' not in prompt(provider)
    with connect(client) as connection:
        companion = current(connection)
        today = steps.local_today(companion, clock.now())
        assert our_child.caring(connection, companion, today) == 'both_work'


def test_across_cities_no_family_day_out_in_their_city(client, clock, monkeypatch, provider):
    """Planned, then called off by the move, then planned again, day after day: no more."""
    row, child = born(client, clock, monkeypatch)
    says(provider)
    send(client, 'hi', 'client-custody-day-out')
    aged(client, child, 500)
    for _ in range(21):  # A day whose week has a family day out that fits.
        with client.app.state.database.connect(write=True) as connection:
            companion = current(connection)
            today = steps.local_today(companion, clock.now())
            could = our_child.plan_outing(connection, companion, today, clock.now())
            connection.rollback()
        if could:
            break
        clock.advance(timedelta(days=1))
    if could is None:
        pytest.skip('No family day out fits in this world.')
    world = client.get('/api/worlds').json()['world']
    assert client.put(f"/api/worlds/{world['id']}/home", json={'city_id': 'chicago'}).status_code == 200
    if state(client) is None:
        pytest.skip('The companion lives in Chicago in this world.')
    with client.app.state.database.connect(write=True) as connection:
        assert our_child.plan_outing(connection, current(connection), today, clock.now()) is None


def test_loss_spares_the_other_parent_of_any_child_under_18_the_companion_shares(client, clock, monkeypatch):
    born(client, clock, monkeypatch)
    with connect(client) as connection:
        companion = current(connection)
        timeline_id = companion['active_timeline_id']
        today = steps.local_today(companion, clock.now())
        people = [dict(row) for row in connection.execute(
            "SELECT * FROM circle_people WHERE timeline_id=? AND status='active' LIMIT 2", (timeline_id,))]
        if len(people) == 1:  # A seeded circle can be this small (seen on Windows CI): a second person, copied.
            ordinal = connection.execute('SELECT MAX(ordinal) + 1 FROM circle_people WHERE timeline_id=?',
                                         (timeline_id,)).fetchone()[0]
            people.append({**people[0], 'id': identifier(), 'name': f"{people[0]['name']} Two", 'ordinal': ordinal})
            connection.execute(f"INSERT INTO circle_people ({', '.join(people[1])}) VALUES "
                               f"({', '.join('?' * len(people[1]))})", tuple(people[1].values()))
        ex, other = people
        assert not custody.spared(connection, ex, today) and not custody.spared(connection, other, today)
        child = (identifier(), timeline_id, ex['id'], 'own', 'Ivy', 'she/her', 'family',
                 (today - timedelta(days=10 * 365)).isoformat(), 'x', 'x')
        connection.execute(
            'INSERT INTO circle_children (id, timeline_id, parent_id, storyline_id, name, pronouns, title, born_on, '
            "status, whose, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'born', 'companion', ?, ?)", child)
        assert custody.spared(connection, ex, today)  # Their own child with an ex, ten years old.
        assert custody.spared(connection, ex, today + timedelta(days=7 * 365))
        assert not custody.spared(connection, ex, today + timedelta(days=8 * 365 + 5))  # Grown: no longer spared.
        connection.execute(
            "INSERT INTO companion_kids (timeline_id, companion_id, how, other_id, pattern, since, created_at, "
            "updated_at) VALUES (?, ?, 'seeded', ?, 'with_them', ?, 'x', 'x')",
            (timeline_id, companion['id'], other['id'], today.isoformat()))
        connection.execute(
            'INSERT INTO circle_children (id, timeline_id, parent_id, storyline_id, name, pronouns, title, born_on, '
            "status, created_at, updated_at) VALUES (?, ?, ?, ?, 'Leo', 'he/him', 'family', ?, 'born', 'x', 'x')",
            (identifier(), timeline_id, companion['id'], f'kids:{timeline_id}',
             (today - timedelta(days=12 * 365)).isoformat()))
        assert custody.spared(connection, other, today)  # The other parent of the kids they had before, Leo at 12.
        assert loss.spared(connection, timeline_id, other, today)
        assert not custody.spared(connection, other, today + timedelta(days=6 * 365 + 10))


@pytest.mark.parametrize('lives', ['with_them', 'with_you'])
def test_split_up_across_cities_a_visit_asked_for_is_to_see_the_child(client, split, provider, lives):
    ours(client, custody=lives)
    world = client.get('/api/worlds').json()['world']
    assert client.put(f"/api/worlds/{world['id']}/home", json={'city_id': 'chicago'}).status_code == 200
    if state(client) is None or not state(client)['far']:
        pytest.skip('The companion lives in Chicago in this world.')
    says(provider)
    send(client, 'can I come see you next weekend?', f'client-custody-see-{lives}')
    text, first = prompt(provider), split['name'].split()[0]
    who = 'the user coming to ' if lives == 'with_them' else 'you going to Chicago'
    assert "You are not together any more, so it isn't a stay with you: it is settled as " + who in text
    assert f'to see {first}.' in text
    with connect(client) as connection:
        assert not connection.execute("SELECT id FROM trips WHERE visit!='' AND status='planned'").fetchall()


def test_the_visit_line_keeps_to_one_side(monkeypatch):
    from companion.life import families, together
    reason = {'why': 'child', 'names': ['Ivy'], 'lives': 'them', 'city': 'Baltimore', 'saturday': '2030-01-05'}
    monkeypatch.setattr(families, 'withheld', lambda _connection: True)
    line = together.child_line(None, 'weekend-host', reason)
    assert 'Ivy' not in line and "it isn't a stay with you" in line
    monkeypatch.setattr(families, 'withheld', lambda _connection: False)
    assert 'the user coming to Baltimore the weekend of Saturday January 5 to see Ivy.' in \
        together.child_line(None, 'weekend-host', reason)


@pytest.mark.parametrize('lives', ['with_them', 'with_you'])
def test_exes_across_cities_hear_nothing_of_visiting_each_other(client, split, provider, lives):
    ours(client, custody=lives)
    world = client.get('/api/worlds').json()['world']
    assert client.put(f"/api/worlds/{world['id']}/home", json={'city_id': 'chicago'}).status_code == 200
    if state(client) is None or not state(client)['far']:
        pytest.skip('The companion lives in Chicago in this world.')
    says(provider)
    send(client, 'hi', f'client-custody-exes-far-{lives}')
    text = prompt(provider)
    assert 'visit each other' not in text and 'weekend visits now and then' not in text
    assert ('the user lives in Chicago and comes to ' if lives == 'with_them' else
            '; you go to Chicago to see ') in text
    assert ' and the user lives in Chicago, about ' in text
