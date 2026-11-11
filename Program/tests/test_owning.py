"""Owning their home: renting, a mortgage or owned outright (companion/life/owning.py, money.py, home.py)."""
import pytest

from companion.life import money, owning

NURSE = {'name': 'Mara', 'home_city': 'baltimore', 'identity': 'A registered nurse at Hopkins.'}
ADA = {'name': 'Ada', 'home_city': 'camelot'}


@pytest.fixture
def odds(monkeypatch):
    """The real odds of owning by age, which tests/conftest.py turns off for every other test."""
    monkeypatch.setattr(owning, 'OWNS', (0.12, 0.38, 0.6, 0.7, 0.76, 0.8))


def test_their_own_words_say_how_they_hold_their_home():
    said = lambda identity: owning.said({'identity': identity})  # noqa: E731
    assert said('She inherited the family farm from her aunt.') == 'owned'
    assert said('He finally paid off the mortgage last spring.') == 'owned'
    assert said('They bought a house in Canton two years ago.') == 'mortgage'
    assert said('Owns a little cottage by the mill.') == 'owns'
    assert said('Rents a room above the bakery from a grumpy landlady.') == 'rent'
    assert said('A nurse who loves jazz.') is None


def test_older_and_better_paid_people_own_more_often(odds):
    def owners(age, tier, era='modern'):
        return sum(owning.decide({}, era, tier, age, f'seed{n}') != 'rent' for n in range(400)) / 400
    assert owners(23, 1) < owners(40, 1) < owners(70, 1)
    assert owners(40, 0) < owners(40, 3)
    assert owners(40, 2, 'other') < owners(40, 2)
    outright = [owning.decide({}, 'modern', 2, age, f'seed{n}') for age in (30, 70) for n in range(400)]
    assert outright[400:].count('owned') > outright[:400].count('owned')
    # A shared room, or a cabin aboard a ship, is always rented; their words win over the odds.
    assert {owning.decide({}, 'modern', 3, 70, f's{n}', shared=True) for n in range(50)} == {'rent'}
    assert {owning.decide({}, 'modern', 3, 70, f's{n}', aboard=True) for n in range(50)} == {'rent'}
    renter = {'identity': 'Rents a flat with two roommates.'}
    assert {owning.decide(renter, 'modern', 3, 70, f's{n}') for n in range(50)} == {'rent'}


def test_what_owning_costs():
    assert owning.costs(1000, 'rent', 'modern', False) == (1000, 0)
    assert owning.costs(1000, 'mortgage', 'modern', False) == (1000, 350)
    assert owning.costs(1000, 'owned', 'modern', False) == (0, 350)
    assert owning.costs(10, 'owned', 'other', True) == (0, 1.5)
    assert owning.words('jazz-age', False) == 'property taxes and repairs'
    assert owning.words('other', True) == 'dues and repairs'


def test_the_home_they_set_changes_the_budget():
    renting = money.snapshot(NURSE, '2026-10-05')
    owned = money.snapshot({**NURSE, 'money': {'home': 'owned'}}, '2026-10-05')
    mortgage = money.snapshot({**NURSE, 'money': {'home': 'mortgage'}}, '2026-10-05')
    assert renting['tenure'] == 'rent' and not renting['owned'] and renting['budget']['owner_costs'] == 0
    assert owned['tenure'] == 'owned' and owned['budget']['rent'] == 0 and owned['budget']['owner_costs'] > 0
    assert owned['budget']['saving'] > renting['budget']['saving'] > mortgage['budget']['saving']
    assert mortgage['tenure'] == 'mortgage' and mortgage['budget']['rent'] > 0
    assert owned['housing']['label'] != renting['housing']['label'] or owned['housing']['unit'] == 'studio'
    lines = dict(money.context_lines({**NURSE, 'money': {'home': 'owned'}}, '2026-10-05'))
    assert 'outright and pay about' in lines['money:2026-10-05:budget']
    assert 'property tax, insurance and upkeep' in lines['money:2026-10-05:budget']


def test_a_home_owned_outright_pays_no_rent_and_the_users_pick_wins():
    costs = {'rent': 1500, 'rent_period': 'month', 'currency': money.profile(NURSE).city['currency'],
             'tenure': 'owned', 'owned': True, 'pets': [], 'vehicles': []}
    home = {'costs': costs, 'purchases': []}
    view = money.snapshot(NURSE, '2026-10-05', home)
    assert view['tenure'] == 'owned' and view['budget']['rent'] == 0
    assert view['budget']['owner_costs'] == pytest.approx(1500 * owning.SHARE['modern'])
    renting = money.snapshot({**NURSE, 'money': {'home': 'rent'}}, '2026-10-05', home)
    assert renting['tenure'] == 'rent' and renting['budget']['rent'] == 1500
    # A place bought on a big turn says only `owned`: a mortgage.
    bought = money.snapshot(NURSE, '2026-10-05', {**home, 'costs': {**costs, 'tenure': None}})
    assert bought['tenure'] == 'mortgage' and bought['budget']['rent'] == 1500


def test_owners_save_for_their_house_not_for_a_better_room():
    room = money.profile({**ADA, 'money': {}})
    assert any(goal in owning.HOUSING_GOALS for goal in money.goals(room)) or room.tier != 1
    owner = money.profile({**ADA, 'money': {'home': 'owned'}})
    assert not any(goal in owning.HOUSING_GOALS for goal in money.goals(owner))
    assert any(goal in owning.OWNER_GOALS['other'] for goal in money.goals(owner)) or owner.tier != 1


def test_a_cottage_their_words_own_is_theirs_from_the_start(client):
    created = client.post('/api/companion', json={
        'name': 'Ada', 'timezone': 'UTC', 'home_city': 'camelot',
        'identity': 'A weaver of 58 who inherited the family cottage from her mother.'})
    assert created.status_code == 200, created.text
    item = client.get('/api/life/home').json()['items'][0]
    assert item['tenure'] == 'owned' and item['owned']
    view = client.get('/api/today/money').json()
    assert view['tenure'] == 'owned' and view['budget']['rent'] == 0 and view['budget']['owner_costs'] > 0
