"""Expecting or adopting together (companion/life/expecting.py): once the pair decided to start a family, the child
comes by the route picked for them, through months in real time, and joins the circle's children as theirs."""
import re
from datetime import date, timedelta

import pytest
from conftest import reconcile, send, set_life
from test_parenthood import family, living_together, set_family
from test_steps import prompt, says

from companion import consequences
from companion.characters import current
from companion.database import decode
from companion.life import admin, big_days, breakups, expecting, families, money, openers, parenthood, rough_patches


@pytest.fixture
def likeliest(monkeypatch):
    """The engine lands on the likeliest option every time."""
    monkeypatch.setattr(consequences, 'roll', lambda _seed, found: max(found, key=lambda item: item['odds'])['option'])


def journey(client):
    with client.app.state.database.connect() as connection:
        return expecting.current(connection, current(connection)['active_timeline_id'])


def stage(row, key):
    return next(item for item in row['stages'] if item['key'] == key)


def to(client, clock, day: str):
    """Moves the clock to midday on that day (UTC companion) and runs the day."""
    target = date.fromisoformat(day)
    clock.advance(timedelta(days=(target - clock.now().date()).days))
    reconcile(client)


def started(client, monkeypatch, route='expecting_them', **values):
    living_together(client, monkeypatch, **values)
    set_family(client, route=route)
    set_family(client, decided=True)
    reconcile(client)
    found = journey(client)
    assert found and found['route'] == route and found['status'] == 'planned'
    return found


def triggers(client, clock):
    with client.app.state.database.connect() as connection:
        return [item for item in expecting.news_due(connection, current(connection), clock.now())]


def test_a_pregnancy_runs_nine_months_from_the_news_to_the_birth(client, provider, clock, monkeypatch, likeliest):
    monkeypatch.setattr(expecting, 'FIRST_TEXTS', True)
    row = started(client, monkeypatch, identity='She is a 31-year-old nurse.')
    keys = [item['key'] for item in row['stages'] if not item['key'].startswith('moment:')]
    assert keys[0] == 'news' and keys[-1] == 'born' and {'appointment', 'told', 'halfway', 'nursery', 'things',
                                                          'name', 'shower', 'soon'} <= set(keys)
    news, born = date.fromisoformat(stage(row, 'news')['on']), date.fromisoformat(stage(row, 'born')['on'])
    assert 230 <= (born - news).days <= 260 and row['details']['name'] and row['details']['turn'] == 'none'
    # Nothing in the chat before the news, nor on the Family panel's stages to come.
    assert family(client)['journey']['stages'] == [] and family(client)['can_decide']
    to(client, clock, stage(row, 'news')['on'])
    [trigger] = triggers(client, clock)
    assert 'just found out you are expecting a baby' in trigger.reason and 'you are the one carrying' in trigger.reason
    says(provider)
    send(client, 'I still cannot believe it', 'client-expecting-1')
    assert 'You and the user are expecting a baby, due in' in prompt(provider)
    assert 'You and the user have decided to start a family together' not in prompt(provider)
    panel = family(client)['journey']
    assert panel['status'] == 'running' and panel['due_on'] and panel['name'] is None
    assert [item['key'] for item in panel['stages']][0] == 'news'
    assert client.put('/api/life/steps/family', json={'decided': False}).status_code == 409
    # The scan is on the Life admin calendar.
    to(client, clock, stage(row, 'appointment')['on'])
    with client.app.state.database.connect() as connection:
        assert connection.execute("SELECT title FROM life_admin WHERE key LIKE 'journey:%'").fetchall()
    to(client, clock, stage(row, 'name')['on'])
    says(provider)
    send(client, 'thinking about the baby', 'client-expecting-2')
    assert f"settled on a name: {row['details']['name']}" in prompt(provider)
    to(client, clock, stage(row, 'born')['on'])
    says(provider)
    send(client, 'hi', 'client-expecting-3')
    assert f"Your baby was born today: a {expecting.girl(row)}, {row['details']['name']}" in prompt(provider)
    with client.app.state.database.connect() as connection:
        child = connection.execute("SELECT * FROM circle_children WHERE title='ours'").fetchone()
        assert child['name'] == row['details']['name'] and child['status'] == 'born'
        assert child['born_on'] == stage(row, 'born')['on']
    assert journey(client)['status'] == 'home' and family(client)['journey']['name'] == row['details']['name']


def test_the_shower_is_a_big_day_the_pair_goes_to_with_no_photo(client, clock, monkeypatch, likeliest):
    monkeypatch.setattr(big_days, 'ACTIVE', True)
    row = started(client, monkeypatch, identity='She is a 31-year-old nurse.', location='Baltimore')
    shower = date.fromisoformat(stage(row, 'shower')['on'])
    assert shower.weekday() == 5
    to(client, clock, (shower - timedelta(days=30)).isoformat())
    with client.app.state.database.connect() as connection:
        found = connection.execute("SELECT * FROM big_days WHERE kind='own_shower'").fetchone()
        assert found and found['local_date'] == shower.isoformat() and found['invite'] == 1
        assert big_days.title(big_days.view(found)).startswith('Baby shower at ')
    assert 'own_shower' in big_days.CHILDS and 'own_shower' in big_days.OWN


def test_their_people_hear_and_react_and_the_news_travels(client, provider, clock, monkeypatch, likeliest):
    row = started(client, monkeypatch, identity='She is a 31-year-old nurse.')
    to(client, clock, stage(row, 'told')['on'])
    says(provider)
    send(client, 'what did everyone say?', 'client-expecting-4')
    assert 'You two told your people about the baby on' in prompt(provider)
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        today = clock.now().date().isoformat()
        items = expecting.news_items(connection, companion, '2000-01-01', today)
        assert [item['text'] for item in items] == ['Mira and the user are expecting a baby']
        full = {**companion, 'version': {**companion['version'], 'definition': {
            **companion['version']['definition'], 'name': 'Mira Reyes'}}}
        assert [item['text'] for item in expecting.news_items(connection, full, '2000-01-01', today)] == [
            'Mira and the user are expecting a baby']  # The first name, as a love life's news has it.


def test_adopting_waits_for_a_match_and_the_child_comes_home(client, provider, clock, monkeypatch, likeliest):
    monkeypatch.setattr(expecting, 'FIRST_TEXTS', True)
    row = started(client, monkeypatch, route='adoption')
    keys = [item['key'] for item in row['stages'] if not item['key'].startswith('moment:')]
    assert keys == ['agency', 'home_study', 'match', 'things', 'home']  # A baby (the likeliest match) needs things.
    to(client, clock, stage(row, 'agency')['on'])
    says(provider)
    send(client, 'any news from the agency?', 'client-expecting-5')
    assert 'You are waiting to be matched with a child; nothing is known about who yet.' in prompt(provider)
    # The match to come is on the panel, without the day the engine picked.
    assert [(item['key'], item['date']) for item in family(client)['journey']['stages']][-1] == ('match', None)
    assert 'things' not in [item['key'] for item in family(client)['journey']['stages']]
    to(client, clock, stage(row, 'match')['on'])
    [trigger] = triggers(client, clock)
    assert row['details']['name'] in trigger.reason and 'matched' in trigger.reason
    to(client, clock, stage(row, 'home')['on'])
    says(provider)
    send(client, 'welcome home', 'client-expecting-6')
    assert f"{row['details']['name']} came home to you and the user today." in prompt(provider)
    assert "yours and the user's, adopted" in prompt(provider)


def test_an_older_city_takes_in_a_child(client, monkeypatch, likeliest):
    row = started(client, monkeypatch, route='ward')
    assert [item['key'] for item in row['stages']] == ['need', 'home']
    assert 0 <= row['details']['years'] <= 12


def test_a_hard_turn_only_on_real_life_and_drama(client, monkeypatch):
    living_together(client, monkeypatch)
    found = {}
    for level in (1, 2):
        set_life(client, life_turns=level)
        with client.app.state.database.connect() as connection:
            found[level] = expecting.facts(connection, current(connection), None)
    names = {'name': 'Mira', 'a': 'someone', 'b': ''}
    assert [item['odds'] > 0 for item in consequences.odds('family:turn', found[1], names)] == [True, False, False]
    assert all(item['odds'] > 0 for item in consequences.odds('family:turn', found[2], names))


def test_an_early_arrival_made_under_hidden_values_reads_calmly(client, provider, clock, monkeypatch, likeliest):
    row = started(client, monkeypatch, identity='She is a 31-year-old nurse.')
    turn = decode(journey(client)['consequences'])['turn']
    assert client.post(f'/api/life/consequences/{turn}/change', json={'option': 2}).status_code == 200
    row = journey(client)
    assert row['details']['turn'] == 'early' and 'soon' not in [item['key'] for item in row['stages']]
    born = date.fromisoformat(stage(row, 'born')['on'])
    assert 21 <= (date.fromisoformat(row['due_on']) - born).days <= 35
    to(client, clock, born.isoformat())
    says(provider)
    send(client, 'hi', 'client-expecting-7')
    assert 'a few weeks early and doing well' in prompt(provider)


def test_the_user_can_rename_the_child(client, clock, monkeypatch, likeliest):
    row = started(client, monkeypatch, route='adoption')
    assert set_family(client, name='  Juniper   Rose ')['journey'] is not None
    assert journey(client)['details']['name'] == 'Juniper Rose' and journey(client)['details']['renamed']
    to(client, clock, stage(row, 'home')['on'])
    with client.app.state.database.connect() as connection:
        assert connection.execute("SELECT name FROM circle_children WHERE title='ours'").fetchone()['name'] == \
            'Juniper Rose'
    assert client.put('/api/life/steps/family', json={'name': ' '}).status_code == 422


def test_taking_the_step_back_before_anything_happened_calls_it_off(client, monkeypatch, likeliest):
    started(client, monkeypatch, route='adoption')
    set_family(client, decided=False)
    reconcile(client)
    assert journey(client) is None
    set_family(client, route='fostering')
    set_family(client, decided=True)
    reconcile(client)
    assert journey(client)['route'] == 'fostering'


def test_a_new_route_before_anything_happened_plans_it_again(client, monkeypatch, likeliest):
    started(client, monkeypatch, route='adoption')
    set_family(client, route='surrogacy')
    reconcile(client)
    reconcile(client)
    found = journey(client)
    assert found['route'] == 'surrogacy' and found['details']['surrogate']


def test_children_keep_their_limits(client, provider, clock, monkeypatch, likeliest):
    """Words only, and nothing with the adult side on, even after the news."""
    monkeypatch.setattr(expecting, 'FIRST_TEXTS', True)
    monkeypatch.setattr(big_days, 'ACTIVE', True)
    row = started(client, monkeypatch, identity='She is a 31-year-old nurse.')
    name = row['details']['name']
    with client.app.state.database.connect() as connection:
        timeline_id = current(connection)['active_timeline_id']
        assert families.pictured(connection, timeline_id, [f'Painting the nursery for {name}'])
    to(client, clock, stage(row, 'news')['on'])
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    assert triggers(client, clock) == []
    says(provider)
    send(client, 'hey you, come to bed', 'client-expecting-8')
    assert 'expecting a baby' not in prompt(provider)
    to(client, clock, (date.fromisoformat(stage(row, 'shower')['on']) - timedelta(days=20)).isoformat())
    with client.app.state.database.connect() as connection:
        assert not connection.execute("SELECT id FROM big_days WHERE kind='own_shower' AND status!='called_off'"
                                      ).fetchall()
        assert not connection.execute("SELECT id FROM life_admin WHERE key LIKE 'journey:%' AND status='planned'"
                                      ).fetchall()
        companion = current(connection)
        assert expecting.news_items(connection, companion, '2000-01-01', '2100-01-01') == []
    assert family(client)['journey']['status'] == 'running'  # Still on the screens.


def test_a_branch_keeps_what_happened_by_then(client, clock, monkeypatch, likeliest):
    row = started(client, monkeypatch, route='adoption')
    to(client, clock, stage(row, 'home')['on'])
    sent = send(client, 'welcome home', 'client-expecting-9')['message']
    assert client.post('/api/timelines', json={'message_id': sent['id'], 'text': 'hello'}).status_code == 200
    with client.app.state.database.connect() as connection:
        rows = connection.execute("SELECT * FROM circle_children WHERE title='ours'").fetchall()
        assert len(rows) == 2 and {item['name'] for item in rows} == {row['details']['name']}
        assert journey(client)['status'] == 'home'


def test_the_news_goes_out_as_a_first_text_only_once_it_happens(client, clock, monkeypatch, likeliest):
    monkeypatch.setattr(expecting, 'FIRST_TEXTS', True)
    row = started(client, monkeypatch, route='adoption')
    assert triggers(client, clock) == []
    to(client, clock, stage(row, 'match')['on'])
    with client.app.state.database.connect() as connection:
        found = [item.key for item in openers.candidates(connection, current(connection), clock.now())]
    assert f"journey:{row['id']}:match" in found


def test_the_bank_has_enough_lines_for_every_era():
    bank = expecting.bank()
    for key in ('reactions', 'pregnancy', 'waiting', 'names_talk'):
        assert len(bank[key]) >= 100 and len({line['text'] for line in bank[key]}) == len(bank[key]), key
        for era, unfit in families.UNFIT.items():  # What an older city or a ship keeps (expecting.fitting): 100 still.
            assert sum((line['era'] == 'any' or not families.older(era)) and not unfit.search(line['text'])
                       for line in bank[key]) >= 100, (key, era)
    assert len(expecting.suggested()) >= 100
    assert all(line['text'].startswith('{who}') for line in bank['reactions'])
    assert all('{name}' in line['text'] for line in bank['names_talk'])
    assert len(big_days.bank()['invite_shower']) >= 100


def test_a_branch_made_while_expecting_still_has_the_baby(client, provider, clock, monkeypatch, likeliest):
    row = started(client, monkeypatch, identity='She is a 31-year-old nurse.')
    to(client, clock, stage(row, 'halfway')['on'])
    says(provider)
    sent = send(client, 'how are you feeling', 'client-expecting-10')['message']
    fork = client.post('/api/timelines', json={'message_id': sent['id']})
    assert fork.status_code == 200, fork.text
    assert client.post(f"/api/timelines/{fork.json()['id']}/activate").status_code == 200
    copy = journey(client)
    assert copy['id'] != row['id'] and copy['due_on'] == row['due_on']
    assert stage(copy, 'born')['on'] == stage(row, 'born')['on']
    # Its outcomes are the copy's own, for Hidden values there.
    with client.app.state.database.connect() as connection:
        for key, consequence_id in decode(copy['consequences']).items():
            found = consequences.by_id(connection, consequence_id)
            assert found['timeline_id'] == copy['timeline_id'] and found['subject'] == f"family:{key}:{copy['id']}"
    to(client, clock, (date.fromisoformat(stage(row, 'born')['on']) + timedelta(days=1)).isoformat())
    assert journey(client)['status'] == 'home'
    with client.app.state.database.connect() as connection:
        kids = connection.execute("SELECT * FROM circle_children WHERE title='ours' AND timeline_id=?",
                                  (copy['timeline_id'],)).fetchall()
        assert [kid['name'] for kid in kids] == [row['details']['name']]


def test_a_birth_while_long_distance_says_the_user_was_away(client, provider, clock, monkeypatch, likeliest):
    monkeypatch.setattr(expecting, 'FIRST_TEXTS', True)
    row = started(client, monkeypatch, identity='She is a 31-year-old nurse.', home_city='baltimore')
    to(client, clock, stage(row, 'halfway')['on'])
    world = client.get('/api/worlds').json()['world']
    assert client.put(f"/api/worlds/{world['id']}/home", json={'city_id': 'chicago'}).status_code == 200
    to(client, clock, stage(row, 'born')['on'])
    [trigger] = triggers(client, clock)
    assert 'The user is away' in trigger.reason
    says(provider)
    send(client, 'hi', 'client-expecting-11')
    assert "The user lives away and couldn't be there" in prompt(provider)
    assert 'with the user there with you' not in prompt(provider)


def test_a_breakup_while_expecting_keeps_the_baby_in_the_chat(client, provider, clock, monkeypatch, likeliest):
    monkeypatch.setattr(rough_patches, 'ACTIVE', True)
    monkeypatch.setattr(breakups, 'ACTIVE', True)
    row = started(client, monkeypatch, identity='She is a 31-year-old nurse.')
    to(client, clock, stage(row, 'halfway')['on'])
    says(provider)
    send(client, "I'm sorry but I'm breaking up with you.", 'client-expecting-12')
    assert client.get('/api/life/breakup').json()['stage'] == 'ended'
    says(provider)
    send(client, 'hi', 'client-expecting-13')
    assert 'You and the user broke up on' in prompt(provider)
    assert 'You and the user are expecting a baby, due in' in prompt(provider)
    to(client, clock, stage(row, 'born')['on'])
    assert journey(client)['status'] == 'home'
    says(provider)
    send(client, 'hi', 'client-expecting-14')
    assert f"Your baby was born today: a {expecting.girl(row)}, {row['details']['name']}" in prompt(provider)


def test_an_early_arrival_keeps_the_shower_before_the_birth(client, clock, monkeypatch, likeliest):
    monkeypatch.setattr(big_days, 'ACTIVE', True)
    row = started(client, monkeypatch, identity='She is a 31-year-old nurse.', location='Baltimore')
    early = {'soon': {'picked': 0}, 'turn': {'picked': expecting.TURNS.index('early')}}
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        for index in range(300):  # Every seed: the shower is a Saturday at least a week before an early birth.
            stages, _ = expecting.pregnancy(connection, companion, row, date(2027, 1, 1), f'journey:{index}', early)
            shower, born = (date.fromisoformat(stage({'stages': stages}, key)['on']) for key in ('shower', 'born'))
            assert shower.weekday() == 5 and (born - shower).days >= expecting.SHOWER_BEFORE
    # A shower planned when the child comes first is called off.
    to(client, clock, (date.fromisoformat(stage(row, 'shower')['on']) - timedelta(days=20)).isoformat())
    with client.app.state.database.connect(write=True) as connection:
        assert connection.execute("SELECT status FROM big_days WHERE kind='own_shower'").fetchone()['status'] != \
            'called_off'
        connection.execute("UPDATE family_journeys SET status='home'")
        big_days.follow(connection, current(connection), clock.now())
        assert connection.execute("SELECT status FROM big_days WHERE kind='own_shower'").fetchone()['status'] == \
            'called_off'


def test_a_jazz_age_city_has_no_scans_car_seats_or_surrogates(client, monkeypatch, likeliest):
    living_together(client, monkeypatch, home_city='new-york-1925', identity='She is a 31-year-old nurse.')
    found = family(client)
    assert 'surrogacy' not in [item['key'] for item in found['routes']] and 'adoption' in [
        item['key'] for item in found['routes']]
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        facts = parenthood.route_facts(connection, companion, None)
        assert facts['surrogate'] == 0 and facts['old'] == 0
        options = consequences.odds('family:route', {**facts, 'can_carry': 0}, {'name': 'Mira', 'a': '', 'b': ''})
        assert options[parenthood.ROUTES.index('surrogacy')]['odds'] == 0
        assert expecting.era_group(connection, companion) == 'jazz'
        # Adopting through a charity: no agency fee, only a lawyer's and the court's, well under a month's pay.
        adopting = {'id': 'j1', 'route': 'adoption'}
        assert expecting.fee(connection, companion, adopting, 'agency') is None
        cost, what = expecting.fee(connection, companion, adopting, 'match')
        assert 0 < cost < money.typical_month(money.city_for(companion['version']['definition'])) / 2
        assert what == "the lawyer's and the court's fees for the adoption"
        words = expecting.ERA_WORDS['jazz']
        assert 'scan' not in words['appointment'] + words['halfway']
        assert not {'a car seat', 'a stroller', 'a baby monitor'} & set(words['things'])
    for group in ('old', 'jazz', 'modern'):
        assert len(expecting.ERA_WORDS[group]['things']) >= 2
    assert 'a pram' not in expecting.ERA_WORDS['old']['things']  # Camelot has none.


def test_word_getting_around_reads_you_and_them_on_today():
    from companion import news
    assert news.on_screen('Mira and the user are expecting a baby') == 'You and Mira are expecting a baby'
    assert news.on_screen('Mira and the user welcomed a child home') == 'You and Mira welcomed a child home'
    assert news.on_screen('the user') == 'You' and news.on_screen('Mira got a promotion') == 'Mira got a promotion'


def test_the_small_moments_of_one_journey_never_repeat():
    lines = [line for line in expecting.bank()['pregnancy'] if line['era'] == 'any']
    for index in range(300):
        row = {'id': f'journey-{index}'}
        texts = [expecting.moment_text(row, moment, lines) for moment in range(expecting.MOMENTS)]
        assert len(set(texts)) == expecting.MOMENTS
    # The first moment is the line it always was.
    assert expecting.moment_text({'id': 'x'}, 0, lines) == expecting.generators.pick('journey:x', 'moment:0', lines)['text']


def test_an_older_citys_lines_name_nothing_the_era_lacks(client, monkeypatch):
    living_together(client, monkeypatch, home_city='camelot')
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        for key in ('reactions', 'pregnancy', 'waiting'):
            kept = expecting.fitting(expecting.bank()[key], connection, companion)
            assert len(kept) >= 50 and not any(families.UNFIT['medieval'].search(line['text']) for line in kept), key


def test_the_companion_suggested_the_name_as_the_character_page_says():
    for index in range(200):
        row = {'id': f'j{index}', 'details': {'name': 'Maya'}}
        assert not expecting.named(row).startswith('the user ')
    assert len(expecting.suggested()) >= 30


def test_bed_rest_keeps_the_companion_carrying_the_baby_home_from_work(client, monkeypatch, likeliest):
    from companion.life import work
    started(client, monkeypatch, identity='She is a 31-year-old nurse.')
    turn = decode(journey(client)['consequences'])['turn']
    assert client.post(f'/api/life/consequences/{turn}/change', json={'option': 1}).status_code == 200
    row = journey(client)
    rest, born = (date.fromisoformat(stage(row, key)['on']) for key in ('bed_rest', 'born'))
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        found = work.days_off(connection, companion, rest - timedelta(days=3), born + timedelta(days=3))
        assert found[rest.isoformat()] == 'Bed rest' and found[born.isoformat()] == 'Bed rest'
        assert (rest - timedelta(days=1)).isoformat() not in found
        assert work.LABELS['Bed rest'] == 'On bed rest at home'
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    with client.app.state.database.connect() as connection:
        assert set(expecting.days_off(connection, current(connection), rest, born).values()) == {'Home day'}


def test_news_on_a_day_the_user_was_away_still_comes(client, provider, clock, monkeypatch, likeliest):
    monkeypatch.setattr(expecting, 'FIRST_TEXTS', True)
    row = started(client, monkeypatch, route='adoption')
    match = date.fromisoformat(stage(row, 'match')['on'])
    to(client, clock, (match - timedelta(days=2)).isoformat())
    says(provider)
    send(client, 'see you in a few days', 'client-expecting-15')
    to(client, clock, (match + timedelta(days=3)).isoformat())
    [trigger] = triggers(client, clock)
    assert trigger.key == f"journey:{row['id']}:match" and 'matched with' in trigger.reason
    to(client, clock, (match + timedelta(days=30)).isoformat())  # Long after, and nothing new: no text.
    says(provider)
    send(client, 'hi', 'client-expecting-16')
    clock.advance(timedelta(days=1))
    assert triggers(client, clock) == []


def test_the_panel_names_each_outcome_under_hidden_values(client, monkeypatch, likeliest):
    started(client, monkeypatch, route='adoption')
    assert client.put('/api/settings', json={'show_odds': True}).status_code == 200
    found = family(client)['journey']
    assert [item['key'] for item in found['outcomes']] == ['wait', 'match']
    assert [item['id'] for item in found['outcomes']] == found['consequences']
    assert client.put('/api/settings', json={'show_odds': False}).status_code == 200
    assert family(client)['journey']['outcomes'] == []


def day_of(client, local_date):
    """The companion's waking blocks on a day (written once automatic events are on and the day has come)."""
    with client.app.state.database.connect() as connection:
        rows = connection.execute("SELECT block, entry FROM life_agenda WHERE subject='companion' AND local_date=? "
                                  "AND json_extract(block, '$.kind')!='sleep' ORDER BY starts_at",
                                  (local_date,)).fetchall()
    return [(decode(row['block']), decode(row['entry']) if row['entry'] else None) for row in rows]


def test_the_birth_takes_the_whole_day_with_the_user_there(client, provider, clock, monkeypatch, likeliest):
    row = started(client, monkeypatch, identity='She is a 31-year-old nurse.', home_city='baltimore')
    set_life(client, automatic_events=True, phrase_with_model=False)
    born = stage(row, 'born')['on']
    to(client, clock, (date.fromisoformat(born) + timedelta(days=1)).isoformat())
    found = day_of(client, born)
    assert found and all(block['arrival'] == row['id'] and block['with_user'] for block, _entry in found)
    assert {block['label'] for block, _entry in found} == {'Having the baby at the hospital, together'}
    name = row['details']['name']
    summaries = [entry['summary'] for _block, entry in found]
    assert f'Mira gave birth to {name} at the hospital, with you there.' in summaries
    assert all('the user' not in text for text in summaries)


def test_the_birth_day_while_long_distance_and_a_homecoming(client, provider, clock, monkeypatch, likeliest):
    row = started(client, monkeypatch, identity='She is a 31-year-old nurse.', home_city='baltimore')
    set_life(client, automatic_events=True, phrase_with_model=False)
    world = client.get('/api/worlds').json()['world']
    assert client.put(f"/api/worlds/{world['id']}/home", json={'city_id': 'chicago'}).status_code == 200
    born = stage(row, 'born')['on']
    to(client, clock, (date.fromisoformat(born) + timedelta(days=1)).isoformat())
    found = day_of(client, born)
    assert {block['label'] for block, _entry in found} == {'Having the baby at the hospital'}
    assert not any(block['with_user'] for block, _entry in found)
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        home = {'id': 'j', 'key': 'home', 'birth': False, 'name': 'Ciro Rossi', 'surrogate': '', 'far': False,
                'at': 'at the hospital'}
        assert expecting.arrival_block({'start': '09:00'}, home)['label'] == 'Bringing Ciro home, together'
        assert expecting.arrival_entry(home, {'start': '09:00'}, companion['version']['definition'])['summary'] == \
            'Mira brought Ciro home with you.'


def test_after_a_breakup_the_birth_day_is_without_the_user(client, provider, clock, monkeypatch, likeliest):
    monkeypatch.setattr(rough_patches, 'ACTIVE', True)
    monkeypatch.setattr(breakups, 'ACTIVE', True)
    row = started(client, monkeypatch, identity='She is a 31-year-old nurse.', home_city='baltimore')
    set_life(client, automatic_events=True, phrase_with_model=False)
    to(client, clock, stage(row, 'halfway')['on'])
    says(provider)
    send(client, "I'm sorry but I'm breaking up with you.", 'client-expecting-40')
    assert client.get('/api/life/breakup').json()['stage'] == 'ended'
    born = stage(row, 'born')['on']
    to(client, clock, (date.fromisoformat(born) + timedelta(days=1)).isoformat())
    found = day_of(client, born)
    assert {block['label'] for block, _entry in found} == {'Having the baby at the hospital'}
    assert not any(block['with_user'] for block, _entry in found)
    name = row['details']['name'].split()[0]
    assert f'Mira gave birth to {name} at the hospital.' in {entry['summary'] for _block, entry in found}


def test_with_the_adult_side_on_the_birth_day_is_an_ordinary_one(client, clock, monkeypatch, likeliest):
    row = started(client, monkeypatch, identity='She is a 31-year-old nurse.')
    set_life(client, automatic_events=True, phrase_with_model=False)
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    born = stage(row, 'born')['on']
    to(client, clock, (date.fromisoformat(born) + timedelta(days=1)).isoformat())
    found = day_of(client, born)
    assert found and not any(block.get('arrival') for block, _entry in found)


def test_bed_rest_shows_on_today_and_undo_ends_it(client, clock, monkeypatch, likeliest):
    started(client, monkeypatch, identity='She is a 31-year-old nurse.')
    turn = decode(journey(client)['consequences'])['turn']
    assert client.post(f'/api/life/consequences/{turn}/change', json={'option': 1}).status_code == 200
    row = journey(client)
    rest = date.fromisoformat(stage(row, 'bed_rest')['on'])
    to(client, clock, (rest - timedelta(days=1)).isoformat())
    assert client.get('/api/life/steps/family/turns').json() == []  # Nothing before it comes.
    to(client, clock, (rest + timedelta(days=2)).isoformat())
    [shown] = client.get('/api/life/steps/family/turns').json()
    assert shown['kind'] == 'bed_rest' and shown['on'] == rest.isoformat() and shown['consequence'] == turn
    assert shown['title'].startswith('Mira went on bed rest') and 'the user' not in shown['title']
    assert client.post(f"/api/life/steps/family/turns/{row['id']}/undo").json() == []
    after = journey(client)
    assert 'bed_rest' not in {item['key'] for item in after['stages']} and after['details']['turn'] == 'none'
    assert stage(after, 'born')['on'] > (rest + timedelta(days=2)).isoformat()
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        assert expecting.days_off(connection, companion, rest, rest + timedelta(days=60)) == {}
        assert not any('bed rest' in line for _key, line in expecting.context_lines(connection, companion, clock.now()))
        assert consequences.by_id(connection, turn)['picked'] == 0
    assert client.post(f"/api/life/steps/family/turns/{row['id']}/undo").status_code == 409


def test_an_early_arrival_shows_on_today_and_undo_puts_the_baby_back_on_the_way(client, clock, monkeypatch,
                                                                                likeliest):
    started(client, monkeypatch, identity='She is a 31-year-old nurse.')
    turn = decode(journey(client)['consequences'])['turn']
    assert client.post(f'/api/life/consequences/{turn}/change', json={'option': 2}).status_code == 200
    row = journey(client)
    born = date.fromisoformat(stage(row, 'born')['on'])
    to(client, clock, (born + timedelta(days=1)).isoformat())
    home = journey(client)
    assert home['status'] == 'home' and home['child_id']
    [shown] = client.get('/api/life/steps/family/turns').json()
    weeks = round((date.fromisoformat(home['due_on']) - born).days / 7)
    assert shown['kind'] == 'early' and shown['title'] == f"{home['details']['name']} was born {weeks} weeks early, " \
        'and is doing well'
    assert client.post(f"/api/life/steps/family/turns/{row['id']}/undo").json() == []
    after = journey(client)
    assert after['status'] == 'running' and after['child_id'] is None and after['details']['turn'] == 'none'
    assert stage(after, 'born')['on'] > (born + timedelta(days=1)).isoformat()
    assert after['details']['name'] == home['details']['name']
    with client.app.state.database.connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM circle_children WHERE id=?',
                                  (home['child_id'],)).fetchone()[0] == 0
    to(client, clock, stage(after, 'born')['on'])  # The baby still comes, at term.
    assert journey(client)['status'] == 'home'
    # Long after an early arrival there is nothing to undo on Today.
    assert client.get('/api/life/steps/family/turns').json() == []


def test_a_hard_turn_on_today_keeps_the_same_hold_as_the_news(client, clock, monkeypatch, likeliest):
    started(client, monkeypatch, identity='She is a 31-year-old nurse.')
    turn = decode(journey(client)['consequences'])['turn']
    assert client.post(f'/api/life/consequences/{turn}/change', json={'option': 1}).status_code == 200
    to(client, clock, (date.fromisoformat(stage(journey(client), 'bed_rest')['on']) + timedelta(days=1)).isoformat())
    assert len(client.get('/api/life/steps/family/turns').json()) == 1
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    assert client.get('/api/life/steps/family/turns').json() == []


def test_on_the_day_the_name_comes_up_they_text_to_suggest_it(client, clock, monkeypatch, likeliest):
    monkeypatch.setattr(expecting, 'FIRST_TEXTS', True)
    row = started(client, monkeypatch, identity='She is a 31-year-old nurse.', location='Baltimore')
    to(client, clock, stage(row, 'name')['on'])
    [trigger] = triggers(client, clock)
    name = journey(client)['details']['name']
    assert trigger.key == f"journey:{row['id']}:name"
    assert trigger.reason == (f"You've been thinking about names for the baby, and one keeps coming back to you: {name}. "
                              'Suggest it to the user in your own words, and leave them room to say no.')
    # Once the user has named the child themselves, nothing is suggested.
    with client.app.state.database.connect(write=True) as connection:
        expecting.rename(connection, current(connection), 'Juniper', clock.now())
    assert triggers(client, clock) == []


def test_their_people_react_with_their_own_pronouns():
    lines = [line['text'] for line in expecting.bank()['reactions']]
    for pronouns in ('he/him', 'she/her', 'they/them', None):
        for line in lines:
            said = expecting.reaction(line, 'your dad Johnny', pronouns)
            assert '{' not in said and '}' not in said, (line, pronouns)
    happy = next(line for line in lines if 'forgot what' in line)
    assert expecting.reaction(happy, 'your dad Johnny', 'he/him') == \
        'your dad Johnny was so happy he forgot what he had come over to say.'
    proud = next(line for line in lines if 'proud of you two' in line)
    assert expecting.reaction(proud, 'your mom Ann', 'she/her') == \
        'your mom Ann said she was proud of you two, which she does not often say.'
    assert expecting.reaction(proud, 'your friend Sam', 'they/them') == \
        'your friend Sam said they were proud of you two, which they do not often say.'
    # A "them" that is about something else (the questions they asked) stays.
    questions = next(line for line in lines if 'practical questions' in line)
    assert expecting.reaction(questions, 'your sister Kim', 'she/her').endswith('write them down.')
    he = [expecting.reaction(line, 'your dad Johnny', 'he/him') for line in lines]
    assert not any(re.search(r'\b(?:they|their|themself|themselves)\b', said) for said in he)


def money_view(client):
    response = client.get('/api/today/money')
    assert response.status_code == 200, response.text
    return response.json()


def test_a_child_costs_what_it_would_in_a_modern_us_city(client, monkeypatch, likeliest):
    """Vanta 2026-10-20: a nursery and baby things come to a few thousand dollars, an agency adoption to tens of
    thousands; the companion pays half of each (the pair's), as other big costs are paid."""
    row = started(client, monkeypatch, route='adoption', identity='She is a 31-year-old nurse.', home_city='Baltimore')
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        adopting = sum(expecting.fee(connection, companion, row, key)[0] for key in ('agency', 'match')) * 2
        assert 25000 <= adopting <= 55000
        assert expecting.fee(connection, companion, row, 'home_study') is None
        assert expecting.fee(connection, companion, row, 'nursery') is None  # Only when expecting.
        expecting_row = {**row, 'route': 'expecting_them'}
        baby = sum(expecting.fee(connection, companion, expecting_row, key)[0] for key in ('nursery', 'things')) * 2
        assert 2000 <= baby <= 6000
        surrogate = {**row, 'route': 'surrogacy'}
        assert sum(expecting.fee(connection, companion, surrogate, key)[0] for key in ('agency', 'news')) * 2 > 90000
        for route in ('fostering', 'ward', 'foundling', 'relative'):
            assert not any(expecting.fee(connection, companion, {**row, 'route': route}, key) for key in
                           ('training', 'agency', 'match', 'home', 'need', 'adopted', 'nursery'))


def test_adopting_or_fostering_a_baby_buys_baby_things_once_the_baby_is_known(client, clock, monkeypatch, likeliest):
    row = started(client, monkeypatch, route='adoption', identity='She is a 31-year-old nurse.', home_city='Baltimore')
    match, things, home = (date.fromisoformat(stage(row, key)['on']) for key in ('match', 'things', 'home'))
    assert match < things < home
    with client.app.state.database.connect() as connection:
        cost, what = expecting.fee(connection, current(connection), row, 'things')
    assert 600 <= cost * 2 <= 3000 and what == 'the baby things'
    # Before the match, neither the calendar nor the panel gives it away.
    to(client, clock, (match - timedelta(days=1)).isoformat())
    with client.app.state.database.connect() as connection:
        assert not connection.execute("SELECT 1 FROM life_admin WHERE key LIKE 'journey:%:things'").fetchall()
    assert 'things' not in [item['key'] for item in family(client)['journey']['stages']]
    # From the match it goes on the calendar as it comes within Life admin's weeks ahead.
    to(client, clock, max(match, things - timedelta(days=admin.AHEAD)).isoformat())
    with client.app.state.database.connect() as connection:
        entry = connection.execute("SELECT title, cost FROM life_admin WHERE key LIKE 'journey:%:things'").fetchone()
    assert entry['title'] == 'Buy baby things' and entry['cost'] == cost
    assert 'things' in [item['key'] for item in family(client)['journey']['stages']]
    # An older child needs none.
    choice = decode(journey(client)['consequences'])['match']
    assert client.post(f'/api/life/consequences/{choice}/change', json={'option': 2}).status_code == 200
    assert 'things' not in [item['key'] for item in journey(client)['stages'] if item['on'] > clock.now().date().isoformat()]


def test_fostering_a_baby_buys_baby_things_after_the_placement(client, monkeypatch, likeliest):
    started(client, monkeypatch, route='fostering', identity='She is a 31-year-old nurse.', home_city='Baltimore')
    choice = decode(journey(client)['consequences'])['match']
    assert client.post(f'/api/life/consequences/{choice}/change', json={'option': 0}).status_code == 200
    row = journey(client)
    home, things = (date.fromisoformat(stage(row, key)['on']) for key in ('home', 'things'))
    assert 1 <= (things - home).days <= 4
    with client.app.state.database.connect() as connection:
        assert expecting.fee(connection, current(connection), row, 'things')
        assert not expecting.fee(connection, current(connection), row, 'training')


def test_an_adoption_is_paid_from_savings_then_month_by_month(client, provider, clock, monkeypatch, likeliest):
    row = started(client, monkeypatch, route='adoption', identity='She is a 31-year-old nurse.', home_city='Baltimore')
    to(client, clock, stage(row, 'agency')['on'])
    with client.app.state.database.connect() as connection:
        entry = connection.execute("SELECT cost FROM life_admin WHERE key LIKE 'journey:%:agency'").fetchone()
    paid = journey(client)['details']['paid']['agency']
    assert entry['cost'] == paid['cost'] > 1000  # The calendar shows their half; savings pay what they cover.
    assert paid['saved'] + paid['monthly'] * paid['months'] == pytest.approx(paid['cost'], abs=1)
    bought = [item for item in money_view(client)['bought'] if item['for'] in ('family', 'admin')]
    assert [item['for'] for item in bought] == (['family'] if paid['saved'] else [])
    to(client, clock, stage(row, 'match')['on'])
    paid = journey(client)['details']['paid']['match']
    assert paid['months'] >= 1  # A placement fee their savings can't cover all at once.
    first = date.fromisoformat(paid['on']) + timedelta(days=30)
    to(client, clock, first.isoformat())
    owed = [item for item in money_view(client)['bought'] if item['for'] == 'owed']
    assert owed and owed[0]['cost'] == paid['monthly']
    assert owed[0]['shown'] == "paid an installment on their share of the adoption agency's placement fee"
    says(provider)
    send(client, 'how are we doing for money?', 'client-expecting-money')
    assert ("you spent money on what you still owe: you paid an installment on your share of the adoption "
            "agency's placement fee.") in prompt(provider)
    # Savings went to it, so a big buy now finds less put by.
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        drawn = money.drawn_since(connection, companion['active_timeline_id'], date(2000, 1, 1), first)
    assert drawn == pytest.approx(sum(item['saved'] for item in journey(client)['details']['paid'].values()))


def test_a_withheld_family_bill_reads_plainly(client, clock, monkeypatch, likeliest):
    row = started(client, monkeypatch, route='adoption', identity='She is a 31-year-old nurse.', home_city='Baltimore')
    to(client, clock, stage(row, 'match')['on'])
    assert client.put('/api/settings', json={'adult_side': True}).status_code == 200
    with client.app.state.database.connect() as connection:
        found = expecting.purchases(connection, current(connection)['active_timeline_id'], date(2000, 1, 1),
                                    date(2100, 1, 1))
    assert found and all(item['text'] in ('paid a big bill', 'paid an installment on a big bill') for item in found)
    assert all('adoption' in item['shown'] for item in found)  # The screen still says what for.
