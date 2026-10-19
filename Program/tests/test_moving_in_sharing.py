"""Sharing a home (companion/life/moving_in.py, Vanta's item 1 for v0.13): another romance companion's moving-in step
reached while the user lives with someone. Everyone says whether they are open to sharing the home (moving_in:share);
all open, the newcomer moves into the same home, with the rent split and the chores taking turns among everyone;
anyone not, the move waits; Hidden values can change it; moving out keeps working with more than two at home."""
from datetime import date, timedelta

import pytest
from conftest import send
from test_moving_in import ask_to_move_in, moving_day, row
from test_together import EVENINGS, mira, says

from companion import cast, consequences
from companion.characters import by_id, create_in, current
from companion.database import many, optional
from companion.life import money, moving_in, rough_patches, steps
from companion.memory import context
from companion.models import CharacterDefinition


def theo(client, **values) -> str:
    """A second romance companion in the same city, Theo, who stays out of focus (Mira is the main character)."""
    database = client.app.state.database
    with database.connect(write=True) as connection:
        first = current(connection)
        connection.execute('UPDATE companions SET slot=NULL, stepped_back_at=? WHERE id=?', (database.now(), first['id']))
        made = create_in(connection, database.now(), CharacterDefinition(
            name='Theo Park', timezone='UTC', relationship='romance', home_city='Baltimore', schedule=EVENINGS,
            **values))
        cast.step_back(connection, database.now(), first['id'])
    return made['id']


def living_with_mira(client, provider, clock, monkeypatch):
    mira(client, monkeypatch, relationship='romance')
    ask_to_move_in(client, provider)
    moving_day(client, clock)
    assert row(client)['status'] == 'moved'


def theo_moves_in(client, theo_id, step='moving_in'):
    """Theo's moving-in step is set on the Character page (as steps_routes does), and where follows."""
    database = client.app.state.database
    with database.connect(write=True) as connection:
        found = by_id(connection, theo_id)
        steps.set_step(connection, found, step, database.clock.now())
        moving_in.follow_step(connection, found, database.clock.now())
        return moving_in.current(connection, found['active_timeline_id'])


def advance(client, companion_id, days, clock):
    clock.advance(timedelta(days=days))
    database = client.app.state.database
    with database.connect(write=True) as connection:
        moving_in.advance(connection, by_id(connection, companion_id), clock.now())
        return moving_in.current(connection, by_id(connection, companion_id)['active_timeline_id'])


def where_lines(client, companion_id, clock):
    with client.app.state.database.connect() as connection:
        return '\n'.join(text for _key, text in moving_in.context_lines(
            connection, by_id(connection, companion_id), clock.now(), set()))


def rolls(monkeypatch, closed: set[str]):
    """The engine lands on the first option, except that the companions in `closed` aren't open to sharing."""
    def roll(seed, found):
        return found[1 if 'moving_in:share' in seed and any(key in seed for key in closed) else 0]['option']
    monkeypatch.setattr(consequences, 'roll', roll)


@pytest.fixture
def open_to_it(monkeypatch):
    rolls(monkeypatch, set())


def test_everyone_open_the_newcomer_moves_into_the_same_home(client, provider, clock, monkeypatch, open_to_it):
    living_with_mira(client, provider, clock, monkeypatch)
    mira_row, theo_id = row(client), theo(client)
    found = theo_moves_in(client, theo_id)
    assert (found['status'], found['household'], found['plan']) == ('moving', mira_row['id'], 'yours')
    with client.app.state.database.connect() as connection:
        shares = many(connection, 'SELECT * FROM moving_in_shares WHERE moving_in_id=?', (found['id'],))
        assert sorted((share['newcomer'], share['open']) for share in shares) == [(0, 1), (1, 1)]
    # Mira, who lives with the user, hears about it and is asked to say how she feels; Theo knows who lives there.
    mira_id = current_id(client)
    told = where_lines(client, mira_id, clock)
    assert 'Theo, who the user is also seeing, is moving in with you and the user on' in told
    assert 'This is new: tell the user how you feel about it' in told
    assert "You're moving in with the user and Mira on" in where_lines(client, theo_id, clock)
    days = (date.fromisoformat(found['move_on']) - clock.now().date()).days
    assert advance(client, theo_id, days, clock)['status'] == 'moved'
    with client.app.state.database.connect() as connection:
        mira_now, theo_now = by_id(connection, mira_id), by_id(connection, theo_id)
        today = clock.now().date()
        hers, his = (moving_in.their_home(connection, item, today) for item in (mira_now, theo_now))
        assert his['description'] == hers['description'] and his['rent'] == hers['rent'] and his['shared']
        for item in (mira_now, theo_now):  # One home, the rent split three ways.
            costs = money.household(connection, item['active_timeline_id'], item['version']['definition'], today)
            assert costs['costs']['rent'] == round(hers['rent'] / 3, 2)
        assert [found['owner'] for found in moving_in.members(connection, mira_row['id'])] == [mira_id, theo_id]
        view = moving_in.view(connection, mira_now, clock.now(), False)
        assert view['with'] == ['Theo'] and view['newcomers'] == []
        assert moving_in.view(connection, theo_now, clock.now(), False)['with'] == ['Mira']
    told = where_lines(client, mira_id, clock)
    assert "You live with the user and Theo (also the user's partner)" in told
    assert 'The three of you split the rent and the bills.' in told and 'This is new' not in told


def current_id(client):
    with client.app.state.database.connect() as connection:
        return current(connection)['id']


def test_the_chores_take_turns_among_everyone_and_both_read_the_same_rota(client, monkeypatch):
    mira(client, monkeypatch, relationship='romance')
    theo_id = theo(client)
    with client.app.state.database.connect() as connection:
        mira_now, theo_now = current(connection), by_id(connection, theo_id)
    house = (mira_now['id'], theo_id)
    monday = date(2026, 10, 5)
    cooks = [moving_in.turn(mira_now, monday + timedelta(days=offset), 'cooking', house) for offset in range(3)]
    assert sorted(cooks) == sorted(['you', 'user', theo_id])  # Everyone cooks in turn.
    for offset in range(14):
        day = monday + timedelta(days=offset)
        assert moving_in.turn(mira_now, day, 'cooking', house) != moving_in.turn(mira_now, day, 'dishes', house)
        hers, his = moving_in.turn(mira_now, day, 'laundry', house), moving_in.turn(theo_now, day, 'laundry', house)
        assert (hers == 'you') == (his == mira_now['id']) and (hers == 'user') == (his == 'user')
    names = {mira_now['id']: 'Mira', theo_id: 'Theo'}
    texts = {moving_in.chores_text(mira_now, monday + timedelta(days=offset), house, names) for offset in range(3)}
    assert any("Theo's" in text for text in texts) and any('yours' in text for text in texts)


def test_someone_not_ready_keeps_the_newcomer_waiting_and_hidden_values_can_change_it(client, provider, clock,
                                                                                       monkeypatch):
    rolls(monkeypatch, set())
    living_with_mira(client, provider, clock, monkeypatch)
    mira_id, theo_id = current_id(client), theo(client)
    monkeypatch.setattr(rough_patches, 'ACTIVE', True)
    rolls(monkeypatch, {mira_id})
    monkeypatch.setattr(consequences, 'roll', lambda seed, found, real=consequences.roll: (
        found[1]['option'] if seed.endswith('user:rough_patch') and 'sharing' in seed else real(seed, found)))
    found = theo_moves_in(client, theo_id)
    assert (found['status'], found['move_on']) == ('waiting', None)
    assert "Mira is not ready to share it yet, so your move waits for now." in where_lines(client, theo_id, clock)
    told = where_lines(client, mira_id, clock)
    assert "You aren't ready to share your home with another of the user's partners, so the move waits." in told
    with client.app.state.database.connect() as connection:  # A small rough patch with Mira over it.
        patch = optional(connection, "SELECT * FROM rough_patches WHERE cause='sharing'")
        assert patch and patch['companion_id'] == mira_id and patch['shown'] == 'over Theo moving in'
    # Mira's Character page shows her answer with the odds; Make it go this way lets Theo move in.
    client.put('/api/settings', json={'show_odds': True})
    [newcomer] = client.get('/api/life/steps').json()['moving_in']['newcomers']
    assert (newcomer['name'], newcomer['status'], newcomer['open']) == ('Theo', 'waiting', False)
    odds = client.get(f"/api/life/consequences/{newcomer['consequence_id']}").json()
    assert odds['options'][1]['label'] == "Mira isn't ready to share a home with Theo"
    response = client.post(f"/api/life/consequences/{newcomer['consequence_id']}/change", json={'option': 0})
    assert response.status_code == 200, response.text
    with client.app.state.database.connect() as connection:
        found = moving_in.current(connection, by_id(connection, theo_id)['active_timeline_id'])
    assert found['status'] == 'moving' and found['move_on']


def test_a_not_yet_is_asked_again_some_weeks_later(client, provider, clock, monkeypatch):
    rolls(monkeypatch, set())
    living_with_mira(client, provider, clock, monkeypatch)
    mira_id, theo_id = current_id(client), theo(client)
    rolls(monkeypatch, {mira_id})
    theo_moves_in(client, theo_id)
    assert advance(client, theo_id, 10, clock)['status'] == 'waiting'
    rolls(monkeypatch, set())
    found = advance(client, theo_id, moving_in.SHARE_AGAIN, clock)
    assert found['status'] == 'moving'
    with client.app.state.database.connect() as connection:
        rounds = many(connection, 'SELECT companion_id, round FROM moving_in_shares ORDER BY round')
    assert [(item['companion_id'], item['round']) for item in rounds if item['round'] == 2] == [(mira_id, 2)]


def test_moving_out_of_a_home_shared_by_three(client, provider, clock, monkeypatch, open_to_it):
    living_with_mira(client, provider, clock, monkeypatch)
    mira_id, theo_id = current_id(client), theo(client)
    found = theo_moves_in(client, theo_id)
    advance(client, theo_id, (date.fromisoformat(found['move_on']) - clock.now().date()).days, clock)
    database = client.app.state.database
    with database.connect(write=True) as connection:  # Mira, who set the home up, breaks up: she leaves, Theo stays.
        out = moving_in.move_out(connection, by_id(connection, mira_id), clock.now())
        assert (out['status'], out['out_who']) == ('moved_out', 'them')
        theo_now = by_id(connection, theo_id)
        assert moving_in.living(connection, theo_now)
        shared = moving_in.their_home(connection, theo_now, clock.now().date())
        costs = money.household(connection, theo_now['active_timeline_id'], theo_now['version']['definition'],
                                clock.now().date())['costs']
        assert costs['rent'] == round(shared['rent'] / 2, 2)
        mine = moving_in.their_home(connection, by_id(connection, mira_id), clock.now().date())
        assert mine['description'] != shared['description']  # A place of her own.
    told = where_lines(client, theo_id, clock)
    assert 'You and the user live together' in told and 'Mira' not in told
    with database.connect(write=True) as connection:  # Theo leaving too.
        assert moving_in.move_out(connection, by_id(connection, theo_id), clock.now())['out_who'] == 'them'


def test_with_nobody_else_at_home_a_waiting_move_goes_ahead_like_any_other(client, provider, clock, monkeypatch):
    rolls(monkeypatch, set())
    living_with_mira(client, provider, clock, monkeypatch)
    mira_id, theo_id = current_id(client), theo(client)
    rolls(monkeypatch, {mira_id})
    waiting = theo_moves_in(client, theo_id)
    with client.app.state.database.connect(write=True) as connection:
        moving_in.move_out(connection, by_id(connection, mira_id), clock.now())
    found = advance(client, theo_id, 1, clock)
    assert found['id'] != waiting['id'] and not found['household'] and found['status'] == 'moving'
    assert found['plan'] in moving_in.PLACES


def test_the_newcomer_asks_knowing_who_lives_there_and_the_one_at_home_texts(client, provider, clock, monkeypatch,
                                                                            open_to_it):
    living_with_mira(client, provider, clock, monkeypatch)
    mira_id, theo_id = current_id(client), theo(client)
    with client.app.state.database.connect() as connection:
        reason = steps.reason_for(connection, by_id(connection, theo_id), 'moving_in')
        assert 'They share a home with Mira, who is also their partner' in reason
        assert steps.reason_for(connection, current(connection), 'moving_in') == steps.REASONS['moving_in']
    theo_moves_in(client, theo_id)
    monkeypatch.setattr(moving_in, 'FIRST_TEXTS', True)
    with client.app.state.database.connect() as connection:
        [trigger] = moving_in.share_due(connection, by_id(connection, mira_id), clock.now())
    assert trigger.kind == 'move_share' and 'Theo, who the user is also seeing' in trigger.reason
    assert 'Theo' in trigger.template and 'the user' not in trigger.template


def test_heading_out_counts_for_everyone_at_home(client, provider, clock, monkeypatch, open_to_it):
    living_with_mira(client, provider, clock, monkeypatch)
    mira_id, theo_id = current_id(client), theo(client)
    found = theo_moves_in(client, theo_id)
    advance(client, theo_id, (date.fromisoformat(found['move_on']) - clock.now().date()).days, clock)
    assert client.post('/api/life/living/out', json={}).status_code == 200
    with client.app.state.database.connect() as connection:
        rows = [moving_in.living(connection, by_id(connection, key)) for key in (mira_id, theo_id)]
    assert all(item['out_until'] for item in rows)


def test_the_odds_read_what_the_app_knows():
    def opening(**values):
        found = {'raised': 0, 'open': 0, 'minds': 0, 'upset': 0, 'social': 1, 'warmth': 1, 'drama': 1, 'others': 1,
                 'sheet': set(), **values}
        return consequences.odds(moving_in.SHARE, found, {'name': 'Mira', 'a': 'Theo', 'b': '', 'trait': 'jealous'})[0]
    plain = opening()['odds']
    assert 0.2 < plain < 0.35
    assert opening(open=1)['odds'] > 0.55 and opening(raised=1)['odds'] > 0.55
    assert opening(minds=1)['odds'] < plain and opening(upset=1)['odds'] < plain and opening(drama=3)['odds'] < plain
    assert 'Mira is into open relationships' in opening(open=1)['reasons']


def test_the_context_packet_tells_the_one_at_home(client, provider, clock, monkeypatch, open_to_it):
    living_with_mira(client, provider, clock, monkeypatch)
    theo_moves_in(client, theo(client))
    says(provider)
    with client.app.state.database.connect() as connection:
        built = context.build(connection, current(connection), clock.now(), 24000)
    assert 'Theo, who the user is also seeing, is moving in with you and the user' in built['note']


def test_the_newcomers_page_waits_for_moving_day_and_shows_who_holds_it_up(client, provider, clock, monkeypatch):
    """Iris's review: not "living together" before moving day, and the answer holding it up shows (and changes) on the
    newcomer's own page, each labelled by name."""
    rolls(monkeypatch, set())
    living_with_mira(client, provider, clock, monkeypatch)
    mira_id, theo_id = current_id(client), theo(client)
    rolls(monkeypatch, {mira_id})
    theo_moves_in(client, theo_id)
    client.put('/api/settings', json={'show_odds': True})
    assert client.post('/api/companion/cast/focus', json={'companion_id': theo_id}).status_code == 200
    view = client.get('/api/life/steps').json()
    assert view['text'].endswith(', waiting to move in') and 'living together' not in view['text']
    assert view['moving_in']['consequence_id'] is None
    assert [(item['name'], item['open']) for item in view['moving_in']['rolls']] == [('Theo', True), ('Mira', False)]
    blocking = view['moving_in']['rolls'][1]['consequence_id']
    assert client.get(f'/api/life/consequences/{blocking}').status_code == 200  # Mira's, shown on Theo's page.
    response = client.post(f'/api/life/consequences/{blocking}/change', json={'option': 0})
    assert response.status_code == 200, response.text
    view = client.get('/api/life/steps').json()
    assert view['text'].endswith(', moving in soon') and view['moving_in']['status'] == 'moving'
    advance(client, theo_id, (date.fromisoformat(view['moving_in']['move_on']) - clock.now().date()).days, clock)
    view = client.get('/api/life/steps').json()
    assert view['text'].endswith(', living together') and view['moving_in']['rolls'] == []
    # Someone else's outcome stays out of reach.
    with client.app.state.database.connect() as connection:
        other = optional(connection, "SELECT id FROM consequences WHERE timeline_id=(SELECT active_timeline_id FROM "
                         "companions WHERE id=?) AND choice='moving_in:where'", (mira_id,))
    assert client.get(f"/api/life/consequences/{other['id']}").status_code == 404


def test_until_moving_day_the_panel_stands_at_the_key_and_living_together_moves_them_in(client, provider, clock,
                                                                                         monkeypatch):
    """Iris's review: "Where things stand" shows A key to their place while the move waits; picking Living together
    there is the user's override, and they move in today."""
    rolls(monkeypatch, set())
    living_with_mira(client, provider, clock, monkeypatch)
    mira_id, theo_id = current_id(client), theo(client)
    rolls(monkeypatch, {mira_id})
    theo_moves_in(client, theo_id)
    assert client.post('/api/companion/cast/focus', json={'companion_id': theo_id}).status_code == 200
    view = client.get('/api/life/steps').json()
    assert (view['step'], view['next']) == ('key', 'moving_in')
    assert [item['step'] for item in view['steps']][-1] == 'moving_in'  # Still listed, muted on the page.
    view = client.put('/api/life/steps', json={'step': 'moving_in'}).json()
    assert view['step'] == 'moving_in' and view['moving_in']['status'] == 'moved'
    assert view['moving_in']['with'] == ['Mira'] and view['text'].endswith(', living together')
    with client.app.state.database.connect() as connection:
        assert all(share['open'] for share in many(connection, 'SELECT open FROM moving_in_shares'))


def three_at_home(client, provider, clock, monkeypatch):
    """Mira set the home up; Theo moved in with the two of them."""
    living_with_mira(client, provider, clock, monkeypatch)
    mira_id, theo_id = current_id(client), theo(client)
    found = theo_moves_in(client, theo_id)
    advance(client, theo_id, (date.fromisoformat(found['move_on']) - clock.now().date()).days, clock)
    return mira_id, theo_id


def homes(client, *companion_ids):
    with client.app.state.database.connect() as connection:
        return [moving_in.their_home(connection, by_id(connection, key), moving_in.local_today(
            by_id(connection, key), client.app.state.database.clock.now())) for key in companion_ids]


def rent_paid(client, companion_id):
    with client.app.state.database.connect() as connection:
        found = by_id(connection, companion_id)
        return money.household(connection, found['active_timeline_id'], found['version']['definition'],
                               client.app.state.database.clock.now().date())['costs']['rent']


def test_the_shared_home_grows_with_the_household(client, provider, clock, monkeypatch, open_to_it):
    living_with_mira(client, provider, clock, monkeypatch)
    [before] = homes(client, current_id(client))
    assert before['bedrooms'] == 'one_bedroom'
    mira_id, theo_id = current_id(client), theo(client)
    found = theo_moves_in(client, theo_id)
    advance(client, theo_id, (date.fromisoformat(found['move_on']) - clock.now().date()).days, clock)
    hers, his = homes(client, mira_id, theo_id)
    assert hers['bedrooms'] == his['bedrooms'] == 'two_bedroom'  # Room for three, on both copies of it.
    assert hers['description'] == his['description'] and hers['description'].startswith('a two-bedroom')
    assert hers['rent'] == his['rent'] and hers['id'] == before['id']  # The same place, at a two-bedroom's rent.
    assert rent_paid(client, mira_id) == rent_paid(client, theo_id) == round(hers['rent'] / 3, 2)
    assert moving_in.size_for(2) == 'one_bedroom' and moving_in.size_for(4) == 'two_bedroom'


def test_a_fork_of_the_one_who_set_the_home_up_still_shares_it(client, provider, clock, monkeypatch, open_to_it):
    mira_id, theo_id = three_at_home(client, provider, clock, monkeypatch)
    says(provider)
    send(client, 'so glad we are all under one roof', 'client-share-fork-1')
    sent = client.get('/api/conversation').json()['messages'][-1]
    fork = client.post('/api/timelines', json={'message_id': sent['id']}).json()
    assert client.post(f"/api/timelines/{fork['id']}/activate").status_code == 200
    with client.app.state.database.connect() as connection:
        copied = moving_in.living(connection, by_id(connection, mira_id))
        assert copied['timeline_id'] == fork['id'] and copied['origin']
        assert [found['owner'] for found in moving_in.members(connection, moving_in.household(copied))] == \
            [mira_id, theo_id]
    [shared] = homes(client, mira_id)
    assert rent_paid(client, mira_id) == round(shared['rent'] / 3, 2)  # Still split three ways, not halved.
    assert "You live with the user and Theo (also the user's partner)" in where_lines(client, mira_id, clock)


def test_the_user_moving_city_leaves_one_home_not_a_copy_each(client, provider, clock, monkeypatch, open_to_it):
    mira_id, theo_id = three_at_home(client, provider, clock, monkeypatch)
    with client.app.state.database.connect(write=True) as connection:
        connection.execute("UPDATE persona SET home_city_id='chicago' WHERE id=1")
    mira_now, theo_now = advance(client, mira_id, 1, clock), advance(client, theo_id, 0, clock)
    assert (mira_now, theo_now) == (None, None)
    with client.app.state.database.connect() as connection:
        rows = [moving_in.latest(connection, by_id(connection, key)['active_timeline_id']) for key in (mira_id, theo_id)]
    assert [found['out_who'] for found in rows] == ['you', 'them']  # Mira keeps the home; Theo takes a place.
    hers, his = homes(client, mira_id, theo_id)
    assert not hers['shared'] and his['description'] != hers['description']
    with client.app.state.database.connect() as connection:  # Iris: the step no longer reads "living together".
        texts = [steps.view(connection, by_id(connection, key), clock.now(), False)['text'] for key in (mira_id, theo_id)]
    assert all(text.endswith('living apart for now') or text == 'Living apart for now' for text in texts), texts


def test_whoever_kept_a_home_grown_for_three_moves_somewhere_smaller_months_on(client, provider, clock, monkeypatch,
                                                                                 open_to_it):
    mira_id, theo_id = three_at_home(client, provider, clock, monkeypatch)
    with client.app.state.database.connect(write=True) as connection:
        connection.execute("UPDATE persona SET home_city_id='chicago' WHERE id=1")
    advance(client, mira_id, 1, clock)
    [kept] = homes(client, mira_id)
    assert kept['bedrooms'] == 'two_bedroom'
    advance(client, mira_id, moving_in.DOWNSIZE_AFTER[0] - 2, clock)
    assert homes(client, mira_id)[0]['id'] == kept['id']  # Not yet: she stays a few months.
    advance(client, mira_id, moving_in.DOWNSIZE_AFTER[1] - moving_in.DOWNSIZE_AFTER[0] + 2, clock)
    [smaller] = homes(client, mira_id)
    assert smaller['bedrooms'] == 'one_bedroom' and smaller['rent'] < kept['rent'] and not smaller.get('shared')
    assert smaller['neighborhood'] == kept['neighborhood']
    with client.app.state.database.connect() as connection:
        chapters = many(connection, "SELECT * FROM life_chapters WHERE timeline_id=? AND kind='move'",
                        (by_id(connection, mira_id)['active_timeline_id'],))
    assert len(chapters) == 1 and 'one-bedroom' in chapters[0]['told'] and chapters[0]['title'].startswith('Mira moved')
    advance(client, mira_id, 3, clock)
    with client.app.state.database.connect() as connection:
        assert len(many(connection, "SELECT id FROM life_chapters WHERE kind='move'")) == 1  # Once.
