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
    assert 'import_notes' not in data  # picked quietly
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


def test_a_modern_world_outside_the_us_pays_in_its_countrys_money():
    city = world(era='modern', prices=[], country='Portugal')
    del city['currency']
    data = catalog.prepare(city, mend=True)
    assert data['currency'] == {'code': 'EUR', 'symbol': '€', 'name': 'euros'}
    assert data['import_notes'] == ['No currency was given, so money is in euros, as in Portugal.']
    # A money the app has a city for borrows that city's rents; another goes by rough exchange rates.
    city = world(era='modern', prices=[], country='Britain')
    del city['currency']
    london = catalog.prepare(city, mend=True)
    assert london['currency']['code'] == 'GBP' and london['neighborhoods'][1]['rent']['one_bedroom'][0] > 500
    city = world(era='modern', prices=[], country='Country', timezone='Asia/Kolkata')
    del city['currency']
    india = catalog.prepare(city, mend=True)
    assert india['currency']['name'] == 'rupees'
    assert india['neighborhoods'][1]['rent']['one_bedroom'][0] > 20_000
    assert money.amount(45_000, india['currency']) == '₹45,000'


def test_the_budget_works_in_a_city_written_in_the_app(tmp_path):
    from companion.database import Database
    database = Database(tmp_path / 'companion.sqlite3')
    city = world()
    del city['prices']
    custom.create(database, city)
    wren = {'name': 'Wren', 'home_city': 'thornmere'}
    view = money.snapshot(wren, TODAY)
    assert view['available'] and view['text']['income'].endswith(' gold')
    assert money.profile(wren).city['neighborhoods'][0]['rent']['studio'] != [900, 900]
    # New rents written into the city are read afresh, not kept from before.
    saved = custom.read(database)['thornmere']
    rents = copy.deepcopy(saved['neighborhoods'])
    for hood in rents:
        hood['rent'] = {'studio': [900, 900], 'one_bedroom': [900, 900], 'two_bedroom': [900, 900]}
    custom.update(database, 'thornmere', custom._definition(saved) | {'neighborhoods': rents}, saved['revision'])
    assert money.profile(wren).city['neighborhoods'][0]['rent']['studio'] == [900, 900]


def test_the_budget_works_in_a_city_brought_from_a_world_map(tmp_path):
    from companion.database import Database
    from companion.world import marinara
    from tests.test_marinara_world import sample
    database = Database(tmp_path / 'companion.sqlite3')
    made = marinara.bring(database, sample())
    view = money.snapshot({'name': 'Ines', 'home_city': made['id']}, TODAY)
    assert view['available'] and view['currency']['code'] == 'EUR'
