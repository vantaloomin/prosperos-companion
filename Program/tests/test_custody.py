"""When families change (companion/life/custody.py): custody after a breakup with children shared, long distance with
a child, a companion's own child after they split from their partner, and the parents loss spares."""
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
    assert split['name'].split()[0] not in text and 'split up, ' not in text.split('kids')[-1]


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

