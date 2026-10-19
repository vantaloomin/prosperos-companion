"""Expecting or adopting together (companion/life/expecting.py): once the pair decided to start a family, the child
comes by the route picked for them, through months in real time, and joins the circle's children as theirs."""
from datetime import date, timedelta

import pytest
from conftest import reconcile, send, set_life
from test_parenthood import family, living_together, set_family
from test_steps import prompt, says

from companion import consequences
from companion.characters import current
from companion.database import decode
from companion.life import big_days, breakups, expecting, families, openers, parenthood, rough_patches


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


def test_adopting_waits_for_a_match_and_the_child_comes_home(client, provider, clock, monkeypatch, likeliest):
    monkeypatch.setattr(expecting, 'FIRST_TEXTS', True)
    row = started(client, monkeypatch, route='adoption')
    keys = [item['key'] for item in row['stages'] if not item['key'].startswith('moment:')]
    assert keys == ['agency', 'home_study', 'match', 'home']
    to(client, clock, stage(row, 'agency')['on'])
    says(provider)
    send(client, 'any news from the agency?', 'client-expecting-5')
    assert 'You are waiting to be matched with a child; nothing is known about who yet.' in prompt(provider)
    # The match to come is on the panel, without the day the engine picked.
    assert [(item['key'], item['date']) for item in family(client)['journey']['stages']][-1] == ('match', None)
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
    for key in ('reactions', 'pregnancy', 'waiting'):
        assert len(bank[key]) >= 100 and len({line['text'] for line in bank[key]}) == len(bank[key]), key
        assert sum(line['era'] == 'any' for line in bank[key]) >= 30, key
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
        assert facts['jazz'] == 1 and facts['old'] == 0
        options = consequences.odds('family:route', {**facts, 'can_carry': 0}, {'name': 'Mira', 'a': '', 'b': ''})
        assert options[parenthood.ROUTES.index('surrogacy')]['odds'] == 0
        assert expecting.era_group(connection, companion) == 'jazz'
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
