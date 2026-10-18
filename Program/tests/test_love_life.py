"""Their own love life (companion/life/love_life.py) and townsfolk couples (companion/world/couples.py)."""
import re
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
    for line in bank['spotted']:
        line.format(name='Mira', place='the bakery')



def test_every_bank_line_says_the_partner_with_their_own_pronouns():
    # "It's Maud, and I'm seeing her", not "them" (she/her); a they/them partner keeps "they".
    bank = love_life.bank()
    lines = [*bank['met'], *bank['share_new'], *bank['dates'], *bank['splits'],
             *(line for step in bank['milestones'].values() for line in step)]
    wrong = re.compile(r"\b(?:she|he) (?:are|were|have|do|know|love|need|want|like)\b|\bthey (?:is|was|has|does)\b|"
                       r"\bthey's\b", re.IGNORECASE)
    for pronouns in ('she/her', 'he/him', 'they/them'):
        for template in lines:
            text = love_life.line(template, 'Maud', pronouns)
            assert '{' not in text and '}' not in text, text
            assert not wrong.search(text), text
    found = {'name': 'Maud Pike', 'details': {'pronouns': 'she/her'}}
    assert love_life.told("It's {partner}, and I'm seeing {them}. {They're} lovely.", found) == \
        "It's Maud, and I'm seeing her. She's lovely."
    assert love_life.line('{They} know{s} the stars; {they} {have} opinions.', 'Tom', 'he/him') == \
        'He knows the stars; he has opinions.'
    assert love_life.line('{They} know{s} the stars; {they} {were} kind.', 'Sam', 'they/them') == \
        'They know the stars; they were kind.'
    # With no pronouns known, the partner is "they".
    assert love_life.line('I like {them}.', 'Sam', None) == 'I like them.'
    # A partner who is she or he is never "they" in their own lines.
    for template in lines:
        for pronouns, word in (('she/her', 'she'), ('he/him', 'he')):
            text = love_life.line(template, 'Maud', pronouns)
            assert not re.search(r"\b(?:they|them|their|theirs|themselves)\b", text, re.IGNORECASE) or \
                template in THEY_ABOUT_OTHERS, (word, text)



def test_their_news_and_how_they_met_use_the_partners_pronouns(client, mira, clock, monkeypatch):  # noqa: F811
    real = love_life.bank()
    monkeypatch.setattr(love_life, 'bank', lambda: {
        **real, 'met': ['when {they} returned the scarf you left on a bench'],
        'share_new': ["It's {partner}, and I'm seeing {them}."],
        'milestones': {**real['milestones'], 'exclusive': ['{partner} is mine and I am {theirs}.']}})
    monkeypatch.setattr(love_life, 'FIRST_TEXTS', True)
    world = client.app.state.life.world
    with client.app.state.database.connect() as connection:
        companion = current(client)
        day = steps.local_today(companion, clock.now())
        planned = love_life.plan(connection, companion, world, day, 'test-seed')
    name, pronouns = planned['person']['name'].split()[0], planned['person']['details']['pronouns']
    forms = {'she/her': ('she', 'her', 'hers'), 'he/him': ('he', 'him', 'his'), 'they/them': ('they', 'them', 'theirs')}
    they, them, theirs = forms[pronouns]
    assert planned['share'] == f"It's {name}, and I'm seeing {them}."
    assert planned['told'].startswith(f"You started seeing {planned['person']['name']}; you met when {they} returned")
    found = begin_partner(client, clock)
    assert found['details']['met'] == f'when {they} returned the scarf you left on a bench'
    force(monkeypatch, 0)
    clock.advance(timedelta(days=40))
    with client.app.state.database.connect(write=True) as connection:
        love_life.advance(connection, current(client), world, clock.now())
        [step] = [row for row in steps.reached(connection, found['timeline_id'], 'romance', love_life.key_of(found))
                  if row['step'] == 'exclusive']
        posts = love_life.feed_posts(connection, current(client), [date.fromisoformat(step['reached_on'])], 'UTC')
    assert [post['content']['text'] for post in posts] == [f'{name} is mine and I am {theirs}.']


# Lines where "they" or "them" is someone else (friends, jars, keys, a saying), not the partner.
THEY_ABOUT_OTHERS = {
    "Supper with {partner}'s friends tonight. They're loud and lovely.",
    "Met {partner}'s friends at the dance. They already knew all about me.",
    'Off the market, as they say. {partner} and me.',
    'Introduced {partner} to my friends. They like {them} more than me now.',
    'when you knocked a row of jars off a shelf and {they} caught two of them',
    'Picked wildflowers with {partner} and pressed them in a book.',
    "Two keys on my ring now. One of them opens {partner}'s door.",
}


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


def test_on_drama_a_secret_starts_in_about_one_month_in_fifty():
    # Vanta (2026-10-17): about 2% a month on Drama, not 55 to 80% of years. Below soap opera there is no roll at all
    # (love_life.mode); the love life slider, the Life deck's card and their description still move it.
    names = {'name': 'Rae', 'a': 'someone', 'b': ''}

    def starts(**facts):
        found = consequences.odds(love_life.SECRET, {'love_life': 2, 'drama': 3, 'card': 0, 'closeness': 3,
                                                     'mood': 0, 'sheet': set()} | facts, names)
        return found[1]

    plain = starts()
    assert plain['odds'] == 0.02
    assert plain['reasons'] == ['the drama level is soap opera, and you two are exclusive']
    assert plain['moves'] == ['possible']
    assert starts(love_life=1)['odds'] == 0.01 and starts(love_life=3)['odds'] == 0.03
    assert 0.05 < starts(card=1)['odds'] < 0.06 and "someone caught Rae's eye lately" in starts(card=1)['reasons']
    assert starts(closeness=5)['odds'] < plain['odds'] < starts(sheet={'restless'})['odds']
    # Over a year of monthly rolls, about one in five on true to life (it was over half).
    assert 0.18 < 1 - (1 - plain['odds']) ** 12 < 0.25


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


def test_what_a_friend_saw_comes_only_from_the_branch_being_lived(client, mira, clock, monkeypatch):  # noqa: F811
    # A fork copies a secret that came out (love_life.copy); the timeline left behind keeps its own row. The friend
    # who saw them hears about it once, from the companion's active timeline only.
    monkeypatch.setattr(love_life, 'FIRST_TEXTS', True)
    companion = current(client)
    today = steps.local_today(companion, clock.now()).isoformat()
    with client.app.state.database.connect(write=True) as connection:
        connection.execute("INSERT INTO timelines (id, companion_id, status, created_at) VALUES ('left', ?, "
                           "'frozen', ?)", (companion['id'], clock.now().isoformat()))
        for timeline_id in ('left', companion['active_timeline_id']):
            connection.execute(
                "INSERT INTO love_partners (id, timeline_id, companion_id, name, secret, met_on, ended_on, ended_how, "
                "out_via, witness_id, place, created_at) VALUES (?, ?, ?, 'Jonathan Hale', 1, ?, ?, 'came_out', "
                "'small_world', ?, 'the market', ?)",
                (f'secret-{timeline_id}', timeline_id, companion['id'], today, today, companion['id'],
                 clock.now().isoformat()))
        assert len(love_life.saw_lines(connection, companion, steps.local_today(companion, clock.now()))) == 1
        assert len(love_life.spotted_due(connection, companion, clock.now())) == 1


def test_a_secret_that_came_out_while_the_user_was_away_still_reaches_them(client, romance, clock, monkeypatch):
    # The weekly roll that brings it out is in the past when the app catches up after days away; it comes out the
    # day the app notices (when the rough patch opens too), so the owning-up text is not already stale.
    monkeypatch.setattr(love_life, 'FIRST_TEXTS', True)
    set_life(client, drama=3)
    force(monkeypatch, 1)
    monkeypatch.setattr(love_life, 'OUT_CHANCE', 0)
    with client.app.state.database.connect(write=True) as connection:
        love_life.maybe_secret(connection, current(client), client.app.state.life.world, clock.now())
    monkeypatch.setattr(love_life, 'OUT_CHANCE', 1)
    clock.advance(timedelta(days=12))
    with client.app.state.database.connect(write=True) as connection:
        companion = current(client)
        love_life.advance(connection, companion, client.app.state.life.world, clock.now())
        [after] = love_life.partners(connection, companion['active_timeline_id'], active=False)
        assert after['ended_how'] == 'came_out' and after['ended_on'] == steps.local_today(companion, clock.now()).isoformat()
        assert len(love_life.came_out_due(connection, companion, clock.now())) == 1


def test_a_fork_keeps_how_their_rolls_went_before_it(client, mira, clock, monkeypatch, provider):  # noqa: F811
    from conftest import send
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    found = begin_partner(client, clock)
    force(monkeypatch, 1)  # Not yet: exclusive is rolled again some weeks later.
    clock.advance(timedelta(days=40))
    with client.app.state.database.connect(write=True) as connection:
        love_life.advance(connection, current(client), client.app.state.life.world, clock.now())
    sent = send(client, 'How are things with them?', 'client-love-01')['message']
    fork = client.post('/api/timelines', json={'message_id': sent['id'], 'text': 'How are you two?'}).json()['id']
    assert client.post(f'/api/timelines/{fork}/activate').status_code == 200
    force(monkeypatch, 2)  # Any roll made again on the fork would split them up, in the past.
    with client.app.state.database.connect(write=True) as connection:
        companion = current(client)
        assert companion['active_timeline_id'] == fork
        love_life.advance(connection, companion, client.app.state.life.world, clock.now())
        [copied] = love_life.partners(connection, fork, active=False)
        assert copied['ended_on'] is None
        assert consequences.recorded(connection, f"love:{copied['id']}:exclusive:1", love_life.NEXT)['picked'] == 1
    assert found['name'] == copied['name']


def test_undoing_the_chapter_on_a_fork_takes_back_only_its_own_partner(client, mira, clock, monkeypatch, provider):  # noqa: F811
    from conftest import send
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    arrange(client, monkeypatch, clock, 'relationship')
    reconcile(client)
    parent = current(client)['active_timeline_id']
    sent = send(client, 'Tell me about them.', 'client-love-02')['message']
    fork = client.post('/api/timelines', json={'message_id': sent['id']}).json()['id']
    assert client.post(f'/api/timelines/{fork}/activate').status_code == 200
    [chapter] = client.get('/api/life/chapters').json()
    assert client.post(f"/api/life/chapters/{chapter['id']}/undo").status_code == 200
    with client.app.state.database.connect() as connection:
        [kept] = love_life.partners(connection, parent, active=False)
        [taken] = love_life.partners(connection, fork, active=False)
    assert kept['ended_how'] is None and taken['ended_how'] == 'undone'


def test_after_a_secret_comes_out_they_hold_back_casual_texts(client, romance, clock, monkeypatch):
    # Hours after owning up to seeing someone behind the user's back, a breezy "how's your afternoon going?" check-in
    # went out (seen with the real model). While that rough patch is open they give the user room.
    set_life(client, drama=3)
    force(monkeypatch, 1)
    monkeypatch.setattr(rough_patches, 'ACTIVE', True)
    monkeypatch.setattr(love_life, 'OUT_CHANCE', 0)
    with client.app.state.database.connect(write=True) as connection:
        love_life.maybe_secret(connection, current(client), client.app.state.life.world, clock.now())
    monkeypatch.setattr(love_life, 'OUT_CHANCE', 1)
    clock.advance(timedelta(days=8))
    with client.app.state.database.connect(write=True) as connection:
        love_life.advance(connection, current(client), client.app.state.life.world, clock.now())
        assert rough_patches.current(connection, current(client), clock.now())['cause'] == 'hidden_partner'
        assert rough_patches.cool(connection, current(client), clock.now())


def test_news_from_days_away_is_still_texted_once_and_says_when(client, mira, clock, monkeypatch):  # noqa: F811
    """E2E v0.13: a step reached in a catch-up after days away was never texted (only yesterday and today were
    looked at). Now the news since the user's last visit goes out, up to two weeks back, newest per partner."""
    from companion.life import mood
    monkeypatch.setattr(love_life, 'FIRST_TEXTS', True)
    found = begin_partner(client, clock)
    them = found['name'].split()[0]
    force(monkeypatch, 0)
    start = clock.now()
    clock.advance(timedelta(days=40))  # Exclusive on day 35 and nothing since: five days ago.
    with client.app.state.database.connect(write=True) as connection:
        love_life.advance(connection, current(client), client.app.state.life.world, clock.now())

    def due(last_seen):
        monkeypatch.setattr(mood, 'last_presence', lambda *_args: last_seen.isoformat())
        with client.app.state.database.connect() as connection:
            return love_life.news_due(connection, current(client), clock.now())
    [trigger] = due(start)
    assert trigger.reason.startswith(f'Since you last talked with the user, you and {them} became exclusive on ')
    assert '5 days ago' in trigger.reason and 'catching them up' in trigger.reason
    assert trigger.template == f'So much to catch you up on: {them} and I became exclusive!'
    # The user was here three days ago: they were told then, or it waited for them; nothing from before.
    assert due(clock.now() - timedelta(days=3)) == []
    # Nothing from further back than two weeks.
    clock.advance(timedelta(days=10))
    assert due(start) == []
    # Several things in one jump: only the newest about each partner goes out.
    sam, ali = {'id': 'sam'}, {'id': 'ali'}
    items = [{'key': 'a', 'partner': sam}, {'key': 'b', 'partner': ali}, {'key': 'c', 'partner': sam}]
    assert [item['key'] for item in love_life.latest_each(items)] == ['b', 'c']
