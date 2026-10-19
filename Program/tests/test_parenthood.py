"""Wanting children and the family step (companion/life/parenthood.py): what a companion wants, how a child would come
for the pair, starting a family brought up either way, and the limits children keep."""
from datetime import timedelta

import pytest
from conftest import reconcile, send, set_life
from test_steps import close, first_text, make, prompt, says, view

from companion import consequences
from companion.characters import current
from companion.life import parenthood, rough_patches, steps


@pytest.fixture
def likeliest(monkeypatch):
    """The engine lands on the likeliest option every time."""
    monkeypatch.setattr(consequences, 'roll', lambda _seed, found: max(found, key=lambda item: item['odds'])['option'])


def family(client):
    response = client.get('/api/life/steps/family')
    assert response.status_code == 200, response.text
    return response.json()


def set_family(client, **values):
    response = client.put('/api/life/steps/family', json=values)
    assert response.status_code == 200, response.text
    return response.json()


def living_together(client, monkeypatch, wants='yes', **values):
    """A romance that has just decided to live together, close enough for the family step, wanting children."""
    make(client, monkeypatch, **values)
    monkeypatch.setattr(steps, 'FIRST_TEXTS', True)
    assert client.put('/api/life/steps', json={'step': 'moving_in'}).status_code == 200
    close(client, 4)
    if wants:
        set_family(client, wants=wants)


def planned(client):
    with client.app.state.database.connect() as connection:
        return [row for row in steps.asks(connection, current(connection)['active_timeline_id'], ('planned', 'open'))
                if row['ladder'] == parenthood.LADDER]


def test_their_description_says_whether_they_want_children():
    assert parenthood.described({'personality': 'Never wanted kids, and happy that way.'}) == 'no'
    assert parenthood.described({'background': "She doesn't want children."}) == 'no'
    assert parenthood.described({'identity': 'Child-free and proud of it.'}) == 'no'
    assert parenthood.described({'background': 'Has always wanted a big family.'}) == 'yes'
    assert parenthood.described({'personality': 'Warm, family-oriented.'}) == 'yes'
    assert parenthood.described({'background': 'Wants kids someday, once the bakery is on its feet.'}) == 'someday'
    assert parenthood.described({'personality': 'Driven and funny.'}) is None


@pytest.mark.parametrize('text, wants', [
    ('She never wanted to be a mother.', 'no'), ("He doesn't want to have kids.", 'no'), ('She doesn\u2019t want kids.', 'no'),
    ('Kids aren\u2019t for her.', 'no'), ('She has decided against having children.', 'no'),
    ('Not a kid person.', 'no'), ("They'd rather not have children.", 'no'), ('Never saw herself as a mom.', 'no'),
    ("He can't wait to be a dad.", 'yes'), ('She wants to start a family.', 'yes'), ('Wants three kids.', 'yes'),
    ('She hopes to have children.', 'yes'), ("She's always pictured herself with kids.", 'yes'),
    ('Not ready for kids yet.', 'someday'), ('She never wanted kids to see her cry.', None),
    ('She works with children at the hospital.', None),
])
def test_their_description_is_read_in_other_words_too(text, wants):
    assert parenthood.described({'identity': text}) == wants


def test_the_app_picks_what_they_want_and_the_user_can_change_it(client, monkeypatch):
    make(client, monkeypatch, background='Has always wanted a big family.')
    found = family(client)
    assert found['wants'] == 'yes' and found['wants_how'] == 'description' and found['romance']
    assert set_family(client, wants='no')['wants'] == 'no'
    assert family(client)['wants_how'] == 'set'
    back = set_family(client, wants='auto')
    assert back['wants'] == 'yes' and back['wants_how'] == 'description'
    assert client.put('/api/life/steps/family', json={'wants': 'maybe'}).status_code == 422


def test_a_seeded_wish_has_its_odds_and_someday_turns_to_yes_when_a_baby_comes(client, clock, monkeypatch):
    make(client, monkeypatch, relationship='friendship', identity='A 24-year-old barista.')
    client.put('/api/settings', json={'show_odds': True})
    monkeypatch.setattr(consequences, 'roll', lambda _seed, found: 1)  # Someday.
    found = family(client)
    assert found['wants'] == 'someday' and found['wants_how'] == 'seeded' and found['wants_consequence_id']
    assert not found['romance'] and 'route' not in found
    outcome = client.get(f"/api/life/consequences/{found['wants_consequence_id']}").json()
    assert outcome['label'] == 'Whether Mira wants children' and 'Mira is still young' in outcome['options'][1]['reasons']
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        connection.execute("INSERT INTO circle_children (id, timeline_id, parent_id, storyline_id, name, pronouns, title, "
                           "born_on, status, created_at, updated_at) VALUES ('kid', ?, 'p', 's', 'Wren', 'she/her', "
                           "'family', ?, 'born', ?, ?)", (companion['active_timeline_id'],
                                                          (clock.now() + timedelta(days=3)).date().isoformat(),
                                                          clock.now().isoformat(), clock.now().isoformat()))
    found = family(client)
    assert found['wants'] == 'yes' and found['wants_how'] == 'nudged' and found['nudged_by'] == 'Wren'
    # Hidden values: making it go another way sticks.
    assert client.post(f"/api/life/consequences/{found['wants_consequence_id']}/change",
                       json={'option': 2}).status_code == 200
    assert family(client)['wants'] == 'no'


def test_how_a_child_comes_is_picked_from_the_pair(client, monkeypatch, likeliest):
    make(client, monkeypatch, identity='She is a 31-year-old nurse.')
    persona = client.get('/api/worlds').json()['persona']
    client.patch(f"/api/worlds/personas/{persona['id']}", json={'gender': 'man', 'age': 33}).raise_for_status()
    found = family(client)
    assert found['route'] == 'expecting_them' and found['route_how'] == 'seeded'
    assert [item['key'] for item in found['routes']] == list(parenthood.MODERN_ROUTES)
    assert found['routes'][0]['label'] == 'Mira carries the baby'
    assert set_family(client, route='adoption')['route'] == 'adoption'
    assert set_family(client, route='auto')['route'] == 'expecting_them'


def test_two_who_cannot_carry_adopt_or_foster_and_old_cities_take_in_a_ward(client, monkeypatch, likeliest):
    make(client, monkeypatch, identity='He is a 35-year-old carpenter.')
    persona = client.get('/api/worlds').json()['persona']
    client.patch(f"/api/worlds/personas/{persona['id']}", json={'gender': 'man'}).raise_for_status()
    assert family(client)['route'] in ('adoption', 'fostering', 'surrogacy')
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        facts = {**parenthood.route_facts(connection, companion, None), 'old': 1}
    odds = consequences.odds('family:route', facts, {'name': 'Mira', 'a': 'someone', 'b': ''})
    possible = {parenthood.ROUTES[item['option']] for item in odds if item['odds'] > 0}
    assert possible == {'ward', 'foundling', 'relative'}


def test_they_bring_up_starting_a_family_after_living_together_and_yes_starts_it(client, provider, clock, monkeypatch,
                                                                                 likeliest):
    living_together(client, monkeypatch)
    clock.advance(timedelta(days=100))
    reconcile(client)
    assert planned(client) == []  # Not yet: they have lived together for 100 days, and it takes 180.
    clock.advance(timedelta(days=85))
    reconcile(client)
    [row] = planned(client)
    assert row['step'] == 'family' and row['status'] == 'planned'
    clock.advance(timedelta(days=8))
    trigger = first_text(client, clock)
    assert trigger and 'start a family' in trigger.reason and trigger.template in steps.bank()['family']
    says(provider)
    send(client, 'yes. I want that so much', 'client-family-1')
    assert 'The user just said yes to starting a family.' in prompt(provider)
    found = family(client)
    assert found['decided_on'] and found['decided_how'] == 'them'
    steps_view = view(client)
    assert steps_view['steps'][-1]['step'] == 'family' and steps_view['step'] == 'moving_in'
    assert steps_view['text'].endswith('living together, starting a family')
    says(provider)
    send(client, 'what are you thinking about tonight?', 'client-family-2')
    assert 'You and the user have decided to start a family together' in prompt(provider)
    assert 'On children: you would like to have children one day.' in prompt(provider)


def test_not_for_them_they_never_bring_it_up_and_answer_no_when_you_do(client, provider, clock, monkeypatch,
                                                                       likeliest):
    living_together(client, monkeypatch, wants='no')
    clock.advance(timedelta(days=400))
    reconcile(client)
    assert planned(client) == []
    says(provider)
    send(client, 'do you think we should start a family?', 'client-family-3')
    assert "Your answer is no (you don't want children)" in prompt(provider)
    assert family(client)['decided_on'] is None


def test_you_bring_it_up_and_a_yes_starts_it(client, provider, clock, monkeypatch, likeliest):
    living_together(client, monkeypatch)
    clock.advance(timedelta(days=200))
    says(provider)
    send(client, "I've been thinking... can we start a family?", 'client-family-4')
    assert 'Your answer is yes' in prompt(provider)
    assert family(client)['decided_how'] == 'you'


def test_before_living_together_asking_is_not_the_family_step(client, provider, monkeypatch):
    make(client, monkeypatch)
    says(provider)
    send(client, 'should we start a family one day?', 'client-family-5')
    assert 'starting a family' not in prompt(provider)


def test_saying_no_to_one_who_wants_children_can_start_a_rough_patch_but_not_on_an_easy_life(
        client, provider, clock, monkeypatch, likeliest):
    monkeypatch.setattr(rough_patches, 'ACTIVE', True)
    monkeypatch.setattr(consequences, 'roll', lambda _seed, found: found[-1]['option'])
    living_together(client, monkeypatch)
    set_life(client, rough_patches_realism=1)
    clock.advance(timedelta(days=185))
    reconcile(client)
    clock.advance(timedelta(days=80))
    assert first_text(client, clock)
    says(provider)
    send(client, "no, I don't want kids", 'client-family-6')
    with client.app.state.database.connect() as connection:
        assert not connection.execute("SELECT id FROM rough_patches WHERE cause='family_no'").fetchall()
        ask = connection.execute("SELECT * FROM step_asks WHERE step='family' AND status='no'").fetchone()
        companion = current(connection)
    set_life(client, rough_patches_realism=2)
    with client.app.state.database.connect(write=True) as connection:
        parenthood.answered(connection, companion, dict(ask), 'no', clock.now())
        assert connection.execute("SELECT id FROM rough_patches WHERE cause='family_no'").fetchall()


def test_with_the_adult_side_on_none_of_it_is_in_the_chat(client, provider, clock, monkeypatch, likeliest):
    living_together(client, monkeypatch)
    client.put('/api/settings', json={'adult_side': True})
    clock.advance(timedelta(days=200))
    reconcile(client)
    assert planned(client) == []
    set_family(client, decided=True)
    says(provider)
    send(client, 'hey you', 'client-family-7')
    assert 'start a family' not in prompt(provider) and 'On children' not in prompt(provider)
    assert family(client)['decided_on']  # Still on the screens.


def test_setting_the_romance_back_before_living_together_takes_the_family_step_back(client, monkeypatch):
    living_together(client, monkeypatch)
    assert set_family(client, decided=True)['decided_how'] == 'set'
    client.put('/api/life/steps', json={'step': 'key'})
    found = family(client)
    assert found['decided_on'] is None and not found['can_decide']


def test_one_who_reads_as_a_minor_has_no_family_panel(client, monkeypatch):
    make(client, monkeypatch, relationship='friendship', identity='A 16-year-old student.')
    assert family(client) == {'shown': False}


def test_a_no_is_never_put_as_too_soon(client, monkeypatch):
    make(client, monkeypatch)
    with client.app.state.database.connect() as connection:
        assert steps.reason(connection, {'status': 'no', 'consequence_id': None}) == "you don't want children"
