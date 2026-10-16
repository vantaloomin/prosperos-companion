"""Their own love life (companion/life/love_life.py) and townsfolk couples (companion/world/couples.py)."""
from datetime import date, timedelta

import pytest
from conftest import reconcile, set_life
from test_chapters import arrange, current, mira  # noqa: F401 - the fixture is used by name
from test_consequences import change

from companion import consequences
from companion.life import chapters, circle, love_life, rough_patches, steps
from companion.world import catalog, couples, paper, townsfolk


def test_the_banks_hold_enough_lines_for_every_step():
    bank = love_life.bank()
    for name in ('met', 'share_new', 'dates', 'splits', 'spotted'):
        assert len(bank[name]) >= 100, name
        assert len(set(bank[name])) == len(bank[name]), name
    assert set(bank['milestones']) == {step.key for step in steps.ROMANCE[1:]}
    assert sum(len(lines) for lines in bank['milestones'].values()) >= 100
    for line in [*bank['share_new'], *bank['dates'], *bank['splits']]:
        assert line.count('{partner}') == 1, line
        line.format(partner='Sam')
    for line in bank['spotted']:
        line.format(name='Mira', place='the bakery')


def test_the_odds_tables_say_what_moved_them():
    names = {'name': 'Mira', 'partner': 'Sam', 'a': 'Sam', 'b': '', 'step': 'being exclusive'}
    for choice in (love_life.NEXT, love_life.SECRET):
        for option in consequences.tables()[choice]['options']:
            option['label'].format(**names)
            for rule in option['rules']:
                rule['why'].format(**names)
    quiet = consequences.odds(love_life.NEXT, {'love_life': 1, 'drama': 0, 'step': 2, 'can_up': 1}, names)
    stormy = consequences.odds(love_life.NEXT, {'love_life': 3, 'drama': 3, 'step': 0, 'can_up': 1}, names)
    assert stormy[2]['odds'] > quiet[2]['odds'] and 'the drama level is high' in stormy[2]['reasons']
    married = consequences.odds(love_life.NEXT, {'love_life': 2, 'drama': 1, 'step': 7, 'can_up': 0}, names)
    assert married[0]['odds'] == 0


def test_who_has_a_love_life_of_their_own(client, mira):  # noqa: F811
    with client.app.state.database.connect() as connection:
        companion = current(client)
        assert love_life.mode(connection, companion) == 'free'
        romance = {**companion, 'version': {**companion['version'], 'definition': {
            **companion['version']['definition'], 'relationship': 'romance'}}}
        assert love_life.mode(connection, romance) is None
        open_one = {**romance, 'version': {**romance['version'], 'definition': {
            **romance['version']['definition'], 'interests': ['an open relationship', 'jazz']}}}
        assert love_life.mode(connection, open_one) == 'open'
    assert love_life.is_open({'identity': 'Happily polyamorous.'}) and not love_life.is_open({'identity': 'Shy.'})


def partner_row(client):
    with client.app.state.database.connect() as connection:
        return love_life.partners(connection, current(client)['active_timeline_id'], active=False)


def test_a_friend_meets_someone_who_joins_their_circle(client, mira, clock, monkeypatch):  # noqa: F811
    monkeypatch.setattr(love_life, 'FIRST_TEXTS', True)
    arrange(client, monkeypatch, clock, 'relationship')
    reconcile(client)
    listed = client.get('/api/life/chapters').json()
    assert [item['kind'] for item in listed] == ['relationship'] and listed[0]['title'].startswith('Mira started seeing ')
    [found] = partner_row(client)
    assert not found['secret'] and found['ended_on'] is None
    people = {person['id']: person for person in client.get('/api/life/circle').json()}
    person = people[found['person_id']]
    assert person['role'] in love_life.PARTNER_ROLES and person['love'].startswith('Dating')
    assert person['age'] >= 18
    prompt = client.get('/api/context/preview').json()['prompt']
    assert f"You are seeing {found['name']}" in prompt and 'dating' in prompt
    # The chapter's first text tells the user, from the bank.
    with client.app.state.database.connect() as connection:
        row = chapters.fresh(connection, current(client), clock.now())[0]
    assert found['name'].split()[0] in row['share']

    client.post(f"/api/life/chapters/{listed[0]['id']}/undo")
    [found] = partner_row(client)
    assert found['ended_how'] == 'undone'
    assert found['person_id'] not in {person['id'] for person in client.get('/api/life/circle').json()}
    assert 'You are seeing' not in client.get('/api/context/preview').json()['prompt']


def force(monkeypatch, picked: int):
    """Every love:* roll lands on `picked`; anything else takes its likeliest option."""
    real = consequences.roll

    def roll(seed, found):
        if ':love:' in seed:
            return picked
        return real(seed, found)
    monkeypatch.setattr(consequences, 'roll', roll)


def begin_partner(client, clock):
    companion = current(client)
    world = client.app.state.life.world
    with client.app.state.database.connect(write=True) as connection:
        day = steps.local_today(companion, clock.now())
        found = love_life.plan(connection, companion, world, day, 'test-seed')
        love_life.begin(connection, companion, world, day, found, clock.now())
    return partner_row(client)[0]


def test_they_move_up_the_steps_and_can_split_up(client, mira, clock, monkeypatch):  # noqa: F811
    monkeypatch.setattr(love_life, 'FIRST_TEXTS', True)
    found = begin_partner(client, clock)
    force(monkeypatch, 0)
    clock.advance(timedelta(days=40))
    with client.app.state.database.connect(write=True) as connection:
        love_life.advance(connection, current(client), client.app.state.life.world, clock.now())
        reached = [row['step'] for row in steps.reached(connection, found['timeline_id'], 'romance',
                                                        love_life.key_of(found))]
    assert reached[:2] == ['dating', 'exclusive']
    # A step is news, and a first text to the user.
    with client.app.state.database.connect() as connection:
        items = love_life.news_items(connection, current(client), '2000-01-01', '2100-01-01')
        assert any(item['text'].startswith(f"Mira and {found['name'].split()[0]} became exclusive") for item in items)

    clock.advance(timedelta(days=900))
    with client.app.state.database.connect(write=True) as connection:
        love_life.advance(connection, current(client), client.app.state.life.world, clock.now())
        person = circle.person(connection, found['person_id'])
        reached = [row['step'] for row in steps.reached(connection, found['timeline_id'], 'romance',
                                                        love_life.key_of(found))]
    assert reached[-1] == 'married' and person['role'] in ('wife', 'husband', 'spouse')

    force(monkeypatch, 2)
    clock.advance(timedelta(days=400))
    with client.app.state.database.connect(write=True) as connection:
        love_life.advance(connection, current(client), client.app.state.life.world, clock.now())
        person = circle.person(connection, found['person_id'])
    [after] = partner_row(client)
    assert after['ended_how'] == 'split' and person['role'] == 'ex' and person['status'] == 'removed'
    with client.app.state.database.connect() as connection:
        items = love_life.news_items(connection, current(client), '2000-01-01', '2100-01-01')
    assert any(item['text'].startswith(f"Mira and {found['name'].split()[0]} broke up") for item in items)


def test_the_user_can_make_it_go_another_way(client, mira, clock, monkeypatch):  # noqa: F811
    found = begin_partner(client, clock)
    force(monkeypatch, 2)
    clock.advance(timedelta(days=40))
    with client.app.state.database.connect(write=True) as connection:
        love_life.advance(connection, current(client), client.app.state.life.world, clock.now())
        outcome = consequences.recorded(connection, f"love:{found['id']}:exclusive:1", love_life.NEXT)
    assert partner_row(client)[0]['ended_how'] == 'split'
    # Every reason says which way it pushed ("More likely because…").
    assert all(len(item['moves']) == len(item['reasons']) for item in outcome['options'])
    changed = change(client, outcome['id'], 0)
    assert changed['picked'] == 0
    [after] = partner_row(client)
    assert after['ended_on'] is None
    with client.app.state.database.connect() as connection:
        reached = [row['step'] for row in steps.reached(connection, found['timeline_id'], 'romance',
                                                        love_life.key_of(found))]
        assert circle.person(connection, found['person_id'])['status'] == 'active'
    assert reached == ['dating', 'exclusive']


def test_nothing_new_leaves_them_where_they_are(client, mira, clock, monkeypatch):  # noqa: F811
    set_life(client, love_life=0)
    with client.app.state.database.connect() as connection:
        companion = current(client)
        assert love_life.plan(connection, companion, client.app.state.life.world,
                              steps.local_today(companion, clock.now()), 'seed') is None


@pytest.fixture
def romance(client, clock, monkeypatch):
    from companion.life import body
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    response = client.post('/api/companion', json={'name': 'Rae Okafor', 'timezone': 'UTC', 'relationship': 'romance',
                                                     'location': 'Fells Point, Baltimore'})
    assert response.status_code == 200, response.text
    client.put('/api/life/steps', json={'step': 'exclusive'})
    return response.json()


def test_on_drama_a_secret_stays_hidden_until_it_comes_out(client, romance, clock, monkeypatch):
    monkeypatch.setattr(love_life, 'FIRST_TEXTS', True)
    with client.app.state.database.connect() as connection:
        assert love_life.mode(connection, current(client)) is None
    set_life(client, drama=3)
    force(monkeypatch, 1)
    monkeypatch.setattr(love_life, 'OUT_CHANCE', 0)
    monkeypatch.setattr(love_life, 'FIZZLE_CHANCE', 0)
    with client.app.state.database.connect(write=True) as connection:
        companion = current(client)
        assert love_life.mode(connection, companion) == 'secret'
        found = love_life.maybe_secret(connection, companion, client.app.state.life.world, clock.now())
    assert found['secret'] and found['person_id'] is None
    assert found['name'] not in {person['name'] for person in client.get('/api/life/circle').json()}
    prompt = client.get('/api/context/preview').json()['prompt']
    assert f"secretly seeing {found['name']}" in prompt and 'The user does not know' in prompt
    with client.app.state.database.connect() as connection:
        assert love_life.news_items(connection, current(client), '2000-01-01', '2100-01-01') == []

    monkeypatch.setattr(love_life, 'OUT_CHANCE', 1)
    monkeypatch.setattr(rough_patches, 'ACTIVE', True)
    monkeypatch.setattr(rough_patches, 'FIRST_TEXTS', True)
    clock.advance(timedelta(days=8))
    with client.app.state.database.connect(write=True) as connection:
        love_life.advance(connection, current(client), client.app.state.life.world, clock.now())
        [after] = love_life.partners(connection, current(client)['active_timeline_id'], active=False)
        patch = rough_patches.current(connection, current(client), clock.now())
        triggers = love_life.came_out_due(connection, current(client), clock.now()) + \
            rough_patches.apology_due(connection, current(client), clock.now())
    # With no other companion in town to see them, word got around; they own up first, in one text, and a rough
    # patch opens over it (companion/life/rough_patches.py).
    assert after['ended_how'] == 'came_out' and after['out_via'] == 'news'
    assert patch and patch['cause'] == 'hidden_partner' and patch['fault'] == 'companion'
    assert len(triggers) == 1 and found['name'].split()[0] in triggers[0].reason
    prompt = client.get('/api/context/preview').json()['prompt']
    assert 'behind their back (word got around and reached them)' in prompt


def test_townsfolk_couples_move_on_week_by_week():
    data = catalog.city('baltimore') if hasattr(catalog, 'city') else next(iter(catalog.cities().values()))
    hood = data['neighborhoods'][0]['id']
    found = []
    for sheet in townsfolk.residents(data, hood)[:60]:
        state = couples.couple(sheet, data, date(2027, 6, 1))
        if state:
            found.append((sheet, state))
    assert found, 'some residents have partners'
    for sheet, state in found:
        assert state == couples.couple(sheet, data, date(2027, 6, 1))  # The same every time.
        assert state['status'] in ('seeing someone', 'engaged', 'married', 'single')
        if state['partner']:
            assert state['partner']['age'] >= 18 and couples.text(state)
    # Over a few years, someone gets engaged or married, and the paper reports it that week.
    events = [(sheet, item) for sheet in townsfolk.residents(data, hood)[:60]
              for item in couples.events(sheet, data, (date(2026, 1, 5), date(2030, 1, 5)))]
    assert events
    sheet, item = events[0]
    week = (item['day'] - timedelta(days=item['day'].weekday() + 1) + timedelta(days=1), item['day'] + timedelta(days=1))
    assert any(item['partner']['full'] in entry['text'] for entry in paper.couples_news(
        {**data, 'neighborhoods': [data['neighborhoods'][0]]}, week)) or len(events) > paper.MOST_COUPLES


def test_an_ex_seeing_someone_new_is_not_told_it_is_an_open_relationship(client, romance, clock, monkeypatch):
    # After a breakup (companion/life/breakups.py) the user's ex is free to date, and their sheet still says romance.
    monkeypatch.setattr(steps, 'apart', lambda *_args: 'ended')
    found = begin_partner(client, clock)
    prompt = client.get('/api/context/preview').json()['prompt']
    assert f"You are seeing {found['name']}" in prompt and 'open relationship' not in prompt


def test_a_new_partner_never_shares_a_first_name_with_someone_already_in_their_life(client, clock):
    client.post('/api/companion', json={'name': 'Sarah Wells', 'timezone': 'UTC', 'home_city': 'baltimore'})
    world = client.app.state.life.world
    with client.app.state.database.connect(write=True) as connection:
        companion = current(client)
        circle.ensure(connection, companion, world, clock.now())
        people = [row['name'] for row in circle.people(connection, companion['active_timeline_id'])]
        assert 'Sarah' not in people  # Nor in the circle: someone called Sarah there goes by their full name.
        used = {name.split()[0] for name in people} | {'Sarah'}
        found = [love_life.new_person(connection, companion, world, f'seed:{n}')['name'] for n in range(150)]
    assert not [name for name in found if name.split()[0] in used]
