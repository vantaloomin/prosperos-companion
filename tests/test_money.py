from datetime import date, timedelta

from companion.life import composer, money
from companion.life.world import Place, StaticWorld

NURSE = {'name': 'Mara', 'home_city': 'baltimore', 'identity': 'A registered nurse at Hopkins.'}


def days(start='2026-10-01', count=120):
    first = date.fromisoformat(start)
    return [(first + timedelta(days=offset)).isoformat() for offset in range(count)]


def test_budget_comes_from_career_pay_and_city_rent():
    view = money.snapshot(NURSE, '2026-10-05')
    assert view['available'] and view['career']['id'] == 'registered-nurse' and view['career']['guessed']
    budget = view['budget']
    assert budget['rent'] < budget['income'] * money.RENT_CEILING
    assert round(budget['income'] - budget['rent'] - budget['essentials'] - budget['fun'] - budget['saving'], 1) == 0
    assert view['text']['income'].startswith('$')
    # Same character, same date: the same budget.
    assert money.snapshot(dict(NURSE), '2026-10-05') == view


def test_a_chosen_career_wins_over_the_guess_and_better_pay_means_more_money():
    engineer = {**NURSE, 'money': {'career': 'software-engineer'}}
    chosen = money.snapshot(engineer, '2026-10-05')
    assert chosen['career'] == {'id': 'software-engineer', 'name': 'Software engineer', 'pay': '$$$', 'guessed': False}
    assert chosen['budget']['income'] > money.snapshot(NURSE, '2026-10-05')['budget']['income']


def test_expensive_rent_means_sharing_a_place():
    barista = money.snapshot({'name': 'Jo', 'home_city': 'new-york', 'identity': 'Works as a barista.'}, '2026-10-05')
    assert barista['housing']['unit'] == 'shared'
    assert barista['budget']['rent'] <= barista['budget']['income'] * 0.5


def test_paydays_are_every_other_friday_and_money_runs_low_before_them():
    seen = {money.snapshot(NURSE, day)['payday']['next'] for day in days()}
    assert all(date.fromisoformat(day).weekday() == 4 for day in seen)
    assert {(date.fromisoformat(b) - date.fromisoformat(a)).days for a, b in zip(sorted(seen), sorted(seen)[1:])} == {14}
    spender = {**NURSE, 'money': {'style': 'spender'}}
    tight = [day for day in days() if money.snapshot(spender, day)['tight']]
    assert tight and len(tight) < 100
    # Can't-afford moments happen, but only some of the time.
    blocked = [day for day in days() if not money.affordable(spender, 'dinner', day)]
    assert 0 < len(blocked) < 120
    assert all(money.affordable(spender, 'walk', day) for day in days())


def test_splurges_and_surprise_bills_are_seeded_and_dated():
    spender = {**NURSE, 'money': {'style': 'spender'}}
    views = {day: money.snapshot(spender, day) for day in days(count=365)}
    assert any(view['splurge'] for view in views.values()) and any(view['surprise'] for view in views.values())
    for day, view in views.items():
        for happening in (view['splurge'], view['surprise']):
            assert happening is None or view['payday']['last'] <= happening['on'] <= day


def test_saving_goals_grow_and_a_custom_goal_is_used():
    auto = [money.snapshot(NURSE, day)['goal'] for day in ('2026-07-03', '2026-12-28')]
    assert auto[0]['label'] == auto[1]['label'] and not auto[0]['custom']
    assert auto[1]['saved'] > auto[0]['saved']
    custom = money.snapshot({**NURSE, 'money': {'saving_for': 'a trip to Lisbon', 'goal': 3000,
                                               'goal_since': '2026-09-01'}}, '2026-10-05')['goal']
    assert custom['label'] == 'a trip to Lisbon' and custom['amount'] == 3000 and 0 < custom['share'] < 1


def test_historic_cities_use_their_own_currency_and_weekly_pay():
    view = money.snapshot({'name': 'Ada', 'home_city': 'calderwick'}, '2026-10-05')
    assert view['period'] == 'week' and view['payday']['cycle_days'] == 7
    assert date.fromisoformat(view['payday']['next']).weekday() == 5
    assert view['text']['income'].endswith(view['currency']['symbol'])
    assert view['housing']['label'] == 'a rented room'


def test_no_money_or_no_city_leaves_everything_affordable():
    oz = {'name': 'Dot', 'home_city': 'emerald-city'}
    assert money.snapshot(oz, '2026-10-05') == {'available': False, 'reason': 'There is no money in The Emerald City.'}
    assert money.context_lines(oz, '2026-10-05') == []
    nowhere = {'name': 'Dot'}
    assert not money.snapshot(nowhere, '2026-10-05')['available']
    assert all(money.affordable(definition, 'dinner', day) for definition in (oz, nowhere) for day in days(count=30))


def test_context_lines_state_the_facts_for_the_model_to_phrase():
    lines = dict(money.context_lines(NURSE, '2026-10-05'))
    assert 'take home about $' in lines['money:2026-10-05:budget']
    assert 'registered nurse' in lines['money:2026-10-05:budget']
    assert 'payday' in lines['money:2026-10-05:payday'].lower()
    assert lines['money:2026-10-05:goal'].startswith('- Saving for ')


def test_the_composer_skips_outings_they_cannot_afford(monkeypatch):
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    world = StaticWorld([Place('r', 'Thames Street Oyster House', 'restaurant', 'baltimore', 'Fells Point'),
                         Place('b', 'The Owl Bar', 'bar', 'baltimore', 'Mount Vernon'),
                         Place('v', 'Ottobar', 'venue', 'baltimore', 'Remington')])
    monkeypatch.setattr(money, 'affordable', lambda definition, key, local_date: key not in ('dinner', 'show'))
    slot = {'local_date': '2026-10-08', 'block': {'kind': 'social', 'label': 'Evening', 'start': '19:00'}}
    chosen = {composer.compose(slot, NURSE, world, f'seed-{index}')['activity'] for index in range(40)}
    assert chosen == {'drinks'}
    # When nothing is affordable the routine still happens as before.
    monkeypatch.setattr(money, 'affordable', lambda definition, key, local_date: False)
    assert composer.compose(slot, NURSE, world, 'seed-1')['activity'] in {'dinner', 'drinks', 'show'}


def test_money_endpoint_and_character_setup(client):
    created = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'America/New_York',
                                                  'home_city': 'baltimore',
                                                  'money': {'career': 'teacher', 'style': 'careful',
                                                            'saving_for': 'a new bike', 'goal': 900}})
    assert created.status_code == 200, created.text
    assert created.json()['version']['definition']['money']['career'] == 'teacher'
    view = client.get('/api/today/money').json()
    assert view['available'] and view['date'] == '2026-10-05'
    assert view['career']['name'] == 'Public school teacher' and view['style'] == 'careful'
    assert view['goal']['label'] == 'a new bike'
    bad = client.post('/api/companion/versions', json={'definition': {'name': 'Mira', 'money': {'style': 'lavish'}}})
    assert bad.status_code == 422


def test_money_endpoint_without_a_city(client, companion):
    view = client.get('/api/today/money').json()
    assert view['available'] is False and 'home city' in view['reason']


def home_costs(**overrides):
    budget = money.profile(NURSE)
    return {'rent': 1500, 'rent_period': 'month', 'currency': budget.city['currency'], 'estimate': True,
            'pets': [], 'vehicles': [], **overrides}


def test_rent_and_upkeep_come_from_the_home_when_there_is_one():
    plain = money.snapshot(NURSE, '2026-10-05')
    housed = money.snapshot(NURSE, '2026-10-05', {'costs': home_costs(pets=['dog'], vehicles=['car']),
                                                  'purchases': []})
    assert housed['rent_from'] == 'home' and housed['budget']['rent'] == 1500
    assert housed['budget']['upkeep'] > 0 and housed['budget']['fun'] < plain['budget']['fun']
    assert plain['rent_from'] == 'budget' and plain['budget']['upkeep'] == 0
    lines = dict(money.context_lines(NURSE, '2026-10-05', {'costs': home_costs(pets=['cat']), 'purchases': []}))
    assert 'for your home' in lines['money:2026-10-05:budget']
    assert 'pets and getting around' in lines['money:2026-10-05:upkeep']
    # A home with no rent of its own (or in another currency) keeps the budget's.
    other = money.snapshot(NURSE, '2026-10-05', {'costs': home_costs(rent=None), 'purchases': []})
    assert other['rent_from'] == 'budget' and other['budget']['rent'] == plain['budget']['rent']


def test_home_purchases_count_as_spending_this_pay_period():
    bought = [{'date': '2026-10-03', 'kind': 'new-pet', 'text': 'adopted Biscuit, a beagle mix', 'spend': '$$'},
              {'date': '2026-10-04', 'kind': 'rearrange', 'text': 'rearranged the furniture', 'spend': ''}]
    before = money.snapshot(NURSE, '2026-10-05', {'costs': home_costs(), 'purchases': []})
    after = money.snapshot(NURSE, '2026-10-05', {'costs': home_costs(), 'purchases': bought})
    assert [item['label'] for item in after['bought']] == ['adopted Biscuit, a beagle mix']
    assert after['left'] == round(before['left'] - after['bought'][0]['cost'], 2)
    lines = dict(money.context_lines(NURSE, '2026-10-05', {'costs': home_costs(), 'purchases': bought}))
    assert lines['money:2026-10-05:bought:2026-10-03'].endswith('you adopted Biscuit, a beagle mix.')


def test_the_money_endpoint_reads_the_home(client):
    client.post('/api/companion', json={**NURSE, 'timezone': 'America/New_York'})
    assert client.get('/api/today/money').json()['rent_from'] == 'budget'
    costs = client.get('/api/life/home').json()['costs']
    view = client.get('/api/today/money').json()
    assert view['rent_from'] == 'home' and view['budget']['rent'] == costs['rent']
