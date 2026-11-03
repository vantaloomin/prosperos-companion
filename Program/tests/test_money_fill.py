"""Worlds written without money still get a currency and rents (companion/world/money_fill.py)."""
import copy

from companion.life import money
from companion.world import catalog, custom, money_fill

TODAY = '2026-11-03'


def world(**overrides) -> dict:
    """A small made-up fantasy town with prices in its own coin and no rents, like a hand-written city pack."""
    city = copy.deepcopy(custom.template(TODAY))
    source = next(iter(city['sources']))
    city.update(id='thornmere', name='Thornmere', era='fantasy', summary='A lakeside town of reed roofs and ferries.')
    city['neighborhoods'] = [
        {**city['neighborhoods'][0], 'id': 'reedside', 'name': 'Reedside', 'rent_tier': 'low'},
        {**city['neighborhoods'][0], 'id': 'high-street', 'name': 'High Street', 'rent_tier': 'mid'},
        {**city['neighborhoods'][0], 'id': 'lords-hill', 'name': "Lord's Hill", 'rent_tier': 'very-high'},
    ]
    city['places'][0]['neighborhood'] = 'reedside'
    city['currency'] = {'code': 'GLD', 'symbol': 'g', 'name': 'gold'}
    city['prices'] = [{'id': 'bath', 'item': 'A hot bath', 'low': 6, 'high': 12, 'source': source},
                      {'id': 'dinner', 'item': 'Dinner at an inn', 'low': 18, 'high': 36, 'source': source}]
    city.update(overrides)
    return city


def test_a_world_with_its_own_coin_but_no_rents_gets_rents_in_that_coin():
    data = catalog.prepare(world(), mend=True)
    assert data['currency']['name'] == 'gold'
    assert all(hood['rent'] for hood in data['neighborhoods'])
    low, mid, dear = (hood['rent']['one_bedroom'] for hood in data['neighborhoods'])
    assert low[0] < mid[0] < dear[0]
    assert any("follow Ellerbrück's, in gold" in note for note in data['import_notes'])
    # Prices both towns have (a bath, a meal) set the rate: Thornmere's coin buys about a sixth of a groschen.
    ellerbruck = next(city for city in money_fill.builtins() if city['id'] == 'ellerbruck')
    mid_there = next(hood['rent'] for hood in ellerbruck['neighborhoods'] if hood['rent_tier'] == 'mid')
    assert mid[0] > mid_there['one_bedroom'][0] * 10


def test_rents_a_world_gives_are_kept():
    city = world()
    city['neighborhoods'][0]['rent'] = {'studio': [5, 6], 'one_bedroom': [7, 8], 'two_bedroom': [9, 10]}
    data = catalog.prepare(city, mend=True)
    assert data['neighborhoods'][0]['rent'] == {'studio': [5, 6], 'one_bedroom': [7, 8], 'two_bedroom': [9, 10]}
    assert data['neighborhoods'][1].get('rent') is None
    assert not any('No rents' in note for note in data.get('import_notes', []))


def test_a_priced_rent_sets_what_a_place_costs():
    city = world()
    city['prices'].append({'id': 'rent', 'item': 'A room by the month', 'low': 80, 'high': 120,
                           'source': city['prices'][0]['source']})
    data = catalog.prepare(city, mend=True)
    mid = data['neighborhoods'][1]['rent']['one_bedroom']
    assert 70 <= sum(mid) / 2 <= 130


def test_a_world_without_a_currency_takes_one_from_its_words_then_its_era():
    city = world(summary='A lakeside town where ferrymen are paid in gold crowns and a bath costs two crowns.')
    del city['currency']
    data = catalog.prepare(city, mend=True)
    assert data['currency']['name'] == 'gold crowns'
    assert 'as its own words say' in ' '.join(data['import_notes'])

    city = world(summary='A town where the queen wears three crowns.')
    del city['currency']
    assert catalog.prepare(city, mend=True)['currency']['name'] == 'silver pennies'  # the era's, not the queen's

    city = world(era='future', summary='A mining colony.')
    del city['currency']
    assert catalog.prepare(city, mend=True)['currency']['code'] == 'CR'


def test_a_modern_world_map_with_no_money_pays_in_dollars_at_us_rents():
    city = world(era='modern', prices=[])
    del city['currency']
    data = catalog.prepare(city, mend=True)
    assert data['currency']['code'] == 'USD'
    assert data['neighborhoods'][1]['rent']['one_bedroom'][0] > 500


def test_only_a_world_with_no_currency_has_no_money():
    data = catalog.prepare(world(currency={'code': 'none', 'symbol': '', 'name': 'no money'}), mend=True)
    assert all(hood.get('rent') is None for hood in data['neighborhoods'])


def test_the_budget_works_in_a_world_pack_with_no_rents(tmp_path, monkeypatch):
    import json
    (tmp_path / 'thornmere.json').write_text(json.dumps(world()), encoding='utf-8')
    monkeypatch.setenv(catalog.PACKS_ENV, str(tmp_path))
    catalog.reload()
    money.cached.cache_clear()
    try:
        view = money.snapshot({'name': 'Wren', 'home_city': 'thornmere'}, TODAY)
        assert view['available'] and view['text']['income'].endswith(' gold')
        assert money.context_lines({'name': 'Wren', 'home_city': 'thornmere'}, TODAY)
    finally:
        monkeypatch.delenv(catalog.PACKS_ENV)
        catalog.reload()
        money.cached.cache_clear()


def test_the_emerald_city_still_has_no_money():
    view = money.snapshot({'name': 'Dot', 'home_city': 'emerald-city'}, TODAY)
    assert view == {'available': False, 'reason': 'There is no money in The Emerald City.'}


def test_a_worlds_own_coin_is_said_by_name_and_counted_whole():
    # "28 g" could read as grams: sentences say the coin, only a tight chip keeps its symbol (Iris, PR #538).
    gold = {'code': 'GLD', 'symbol': 'g', 'name': 'gold'}
    assert money.amount(28.4, gold) == '28 gold'
    assert money.amount(1.46, gold, short=True) == '1 g'
    assert money.amount(0.3, gold) == '1 gold'
    assert money.amount(1, {'code': 'KRK', 'symbol': 'k', 'name': 'krakens'}) == '1 kraken'
    # The app's own moneys keep their symbols.
    assert money.amount(4.2, {'code': 'CR', 'symbol': 'cr', 'name': 'credits'}) == '4.20 cr'
    assert money.amount(3, {'code': 'groschen', 'symbol': 'gr.', 'name': 'silver groschen'}) == '3 gr.'
