"""Money for a city written without it: a currency, and rents to live on, picked by rule so the budget works.

A city pack, a user's own city or an imported world map often names its places and people but not what a room
costs. Money (companion/life/money.py) needs rents, so such a world would show no budget at all. Here, when a
city loads (catalog.prepare), what it leaves out is filled in, and what it gives is kept:

- Its currency: the one it names, else money its own words mention ("paid in gold crowns"), else its era's.
- Its rents: when no neighbourhood has one, each takes the rent of the same tier in the nearest built-in city
  (the same currency first, else its era's), in this city's money and rent period. Where both cities price the
  same everyday things (a bath, a meal, a drink), their prices set the rate between the two moneys.

Only a city whose currency is "none" (the Emerald City) has no money. To change what was picked, the city file's
own `currency` and neighbourhood `rent` win.
"""
import json
import re
from functools import cache
from pathlib import Path
from statistics import geometric_mean

DATA = Path(__file__).parent / 'data'
WEEKS_PER_MONTH = 52 / 12
# The money an era pays in when a city names none and its words mention none (modern cities: US dollars).
ERA_CURRENCY = {'medieval': {'code': 'penny', 'symbol': 'd.', 'name': 'silver pennies'},
                'fantasy': {'code': 'penny', 'symbol': 'd.', 'name': 'silver pennies'},
                'victorian': {'code': 'shilling', 'symbol': 's.', 'name': 'shillings'},
                'steampunk': {'code': 'shilling', 'symbol': 's.', 'name': 'shillings'},
                'future': {'code': 'CR', 'symbol': 'cr', 'name': 'credits'}}
# The built-in city whose rents an era borrows when no city with the same money has any (draft/brief.py DONORS).
ERA_DONORS = {'medieval': 'camelot', 'fantasy': 'ellerbruck', 'victorian': 'london-1895', 'steampunk': 'calderwick',
              'frontier': 'whitlock', 'jazz-age': 'pellmouth', 'future': 'port-vesper', 'modern': 'haddon-harbor',
              'other': 'haddon-harbor'}
# Money a world's own words may name, most specific first: (words, code, symbol, name). A word that also means
# something else (crowns on heads, galleons at sea, credits at the end of a film) counts only beside a word about
# money or a number (MONEY_CUE), in UNSURE.
LORE_MONEY = (
    (('gold crowns', 'golden crowns'), 'crown', 'cr.', 'gold crowns'),
    (('silver crowns',), 'crown', 'cr.', 'silver crowns'),
    (('crowns',), 'crown', 'cr.', 'crowns'),
    (('gold coins', 'gold coin', 'gold pieces', 'gold piece'), 'GLD', 'g', 'gold'),
    (('silver coins', 'silver coin', 'silver pieces', 'silver piece'), 'SLV', 's', 'silver'),
    (('copper coins', 'copper pieces', 'coppers'), 'CPR', 'c', 'coppers'),
    (('silver pennies',), 'penny', 'd.', 'silver pennies'),
    (('sovereigns',), 'sovereign', 'sov.', 'sovereigns'),
    (('ducats',), 'ducat', 'duc.', 'ducats'),
    (('florins',), 'florin', 'fl.', 'florins'),
    (('guilders',), 'guilder', 'gld.', 'guilders'),
    (('thalers',), 'thaler', 'th.', 'thalers'),
    (('marks',), 'mark', 'mk', 'marks'),
    (('drachmas', 'drachmae'), 'drachma', 'dr.', 'drachmas'),
    (('denarii',), 'denarius', 'den.', 'denarii'),
    (('dinars',), 'dinar', 'din.', 'dinars'),
    (('dubloons', 'doubloons'), 'doubloon', 'db.', 'doubloons'),
    (('pieces of eight',), 'eight', 'p8', 'pieces of eight'),
    (('krakens',), 'kraken', 'k', 'krakens'),
    (('septims',), 'septim', 'sep.', 'septims'),
    (('galleons',), 'galleon', 'gal.', 'galleons'),
    (('cowrie shells', 'cowries'), 'cowrie', 'cw.', 'cowrie shells'),
    (('shells',), 'shell', 'sh.', 'shells'),
    (('jade coins', 'jade pieces'), 'jade', 'jd.', 'jade coins'),
    (('trade bars', 'trade bar'), 'bar', 'bar', 'trade bars'),
    (('scrip',), 'scrip', 'sc.', 'scrip'),
    (('bottle caps',), 'cap', 'caps', 'bottle caps'),
    (('eurodollars', 'eddies'), 'eddie', 'eb', 'eddies'),
    (('credit chits', 'creds'), 'CR', 'cr', 'credits'),
    (('credits',), 'CR', 'cr', 'credits'),
    (('ration chits',), 'ration', 'rt.', 'ration chits'),
    (('shillings',), 'shilling', 's.', 'shillings'),
    (('groschen',), 'groschen', 'gr.', 'silver groschen'),
)
# Moneys counted in whole coins, as made-up worlds' gold and silver are (money.amount): never "1.46 g".
COIN_CODES = frozenset(code for _words, code, _symbol, _name in LORE_MONEY) - {'CR', 'eddie', 'scrip', 'ration'}
UNSURE = {'crowns', 'coppers', 'sovereigns', 'marks', 'krakens', 'galleons', 'shells', 'scrip', 'eddies', 'credits',
          'creds'}
MONEY_CUE = re.compile(r'\b(?:pay|pays|paid|paying|cost|costs|price|prices|priced|coin|coins|money|currency|spend|'
                       r'spent|earn|earns|earned|wage|wages|buy|buys|bought|sell|sells|sold|purse|worth|fee|fees|'
                       r'rent|tax|taxes|change|cheap|dear|a few|handful)\b|\d')
CUE_REACH = 40

# Everyday prices that mean the same thing under different names, so two cities' prices can be compared.
SAME_PRICES = (('meal', 'dinner', 'inn-meal', 'eating-house', 'chophouse', 'noodles', 'cheap-lunch', 'pie'),
               ('beer', 'ale', 'wine', 'plum-wine', 'cider', 'mead'),
               ('bath', 'baths', 'bathhouse'), ('inn', 'room', 'inn-room', 'lodging'), ('loaf', 'bread'),
               ('coffee', 'tea', 'coffee-stall', 'tea-house'), ('tram', 'bus', 'ferry', 'rickshaw', 'cab', 'lift'),
               ('newspaper', 'paper', 'broadsheet'), ('tobacco', 'pipe-tobacco'))


def settle(data: dict, given: set[str]) -> list[str]:
    """Fill in the currency and rents `data` leaves out (`given` is the fields it named); notes say what was
    picked."""
    notes = currency(data, given)
    if data['currency']['code'] == 'none' or any(hood.get('rent') for hood in data['neighborhoods']):
        return notes
    return notes + rents(data)


def currency(data: dict, given: set[str]) -> list[str]:
    if 'currency' in given:
        return []
    found = from_words(words_of(data))
    if found:
        data['currency'] = found
        return [f'No currency was given, so money is in {found["name"]}, as its own words say.']
    if data['era'] in ERA_CURRENCY:
        data['currency'] = dict(ERA_CURRENCY[data['era']])
        return [f'No currency was given, so money is in {data["currency"]["name"]}, as in its era.']
    return []


def words_of(data: dict) -> str:
    """What the city says about itself: its summary, its local colour and its lore."""
    texts = [data.get('summary') or '', *(item.get('summary') or '' for item in data.get('local_color') or ())]
    lore = data.get('lore') if isinstance(data.get('lore'), dict) else {}
    texts += [entry.get('text') or '' for entry in lore.get('entries') or () if isinstance(entry, dict)]
    return ' '.join(text for text in texts if isinstance(text, str)).casefold()


def from_words(text: str) -> dict | None:
    """The money a city's words name most often (the first listed on a tie), or None. Words already counted for a
    more specific money ("gold crowns") are not counted again for a plainer one ("crowns")."""
    counts = []
    for index, (words, *_rest) in enumerate(LORE_MONEY):
        found = 0
        for word in words:
            found += hits(text, word)
            text = re.sub(rf'\b{re.escape(word)}\b', ' ', text)
        counts.append((found, -index))
    best = max(counts)
    if not best[0]:
        return None
    _words, code, symbol, name = LORE_MONEY[-best[1]]
    return {'code': code, 'symbol': symbol, 'name': name}


def hits(text: str, word: str) -> int:
    """How often the word stands for money in the text."""
    found = list(re.finditer(rf'\b{re.escape(word)}\b', text))
    if word not in UNSURE:
        return len(found)
    return sum(1 for match in found
               if MONEY_CUE.search(text[max(0, match.start() - CUE_REACH):match.end() + CUE_REACH]))


@cache
def builtins() -> tuple[dict, ...]:
    """The built-in cities with rents, read from their files (catalog's library may still be loading)."""
    found = []
    for path in sorted((DATA / 'cities').glob('*.json')):
        city = json.loads(path.read_text(encoding='utf-8'))
        if any(hood.get('rent') for hood in city.get('neighborhoods') or ()):
            found.append(city)
    return tuple(found)


@cache
def shipped_codes() -> frozenset[str]:
    """The moneys the app's own cities pay in, said by their symbols (gr., d., cr); any other is a world's own."""
    return frozenset(code_of(city) for city in builtins()) | {'USD', 'none'}


def code_of(city: dict) -> str:
    return (city.get('currency') or {}).get('code') or 'USD'


def donor(data: dict) -> dict | None:
    """The built-in city to borrow rents from: one of the same era and money, then of the same money, then the
    era's own."""
    cities = builtins()
    same = [city for city in cities if code_of(city) == code_of(data)]
    era = [city for city in same if city.get('era', 'modern') == data['era']]
    named = ERA_DONORS.get(data['era'], 'haddon-harbor')
    fallback = [city for city in cities if city['id'] == named]
    return (era or same or fallback or [None])[0]


def rate(data: dict, other: dict) -> float:
    """How many of this city's money one of `other`'s is worth: 1 for the same money, else from prices both
    cities have under the same or a like name, else 1."""
    if code_of(data) == code_of(other):
        return 1.0
    mine, theirs = mids(data), mids(other)
    ratios = []
    for group in SAME_PRICES:
        a = next((mine[key] for key in group if mine.get(key)), None)
        b = next((theirs[key] for key in group if theirs.get(key)), None)
        if a and b:
            ratios.append(a / b)
    return geometric_mean(ratios) if ratios else 1.0


def mids(city: dict) -> dict[str, float]:
    return {item['id']: (item['low'] + item['high']) / 2 for item in city.get('prices') or ()}


def rents(data: dict) -> list[str]:
    """Each neighbourhood's rent, borrowed by tier from the donor city in this city's money and period."""
    other = donor(data)
    if not other:
        return []
    tiers = {}
    for hood in other['neighborhoods']:
        if hood.get('rent'):
            tiers.setdefault(hood.get('rent_tier', 'mid'), hood['rent'])
    scale = period_scale(other.get('rent_period', 'month'), data.get('rent_period', 'month'))
    asked = mids(data).get('rent')
    # A city that prices "rent" as an everyday thing says what a place costs there: the borrowed rents are set so
    # a typical one-bedroom asks that much. Otherwise the two moneys are compared by their prices.
    scale *= asked / (typical(tiers) * scale) if asked else rate(data, other)
    for hood in data['neighborhoods']:
        found = tiers.get(hood.get('rent_tier', 'mid')) or nearest(tiers, hood.get('rent_tier', 'mid'))
        hood['rent'] = {unit: scaled(found[unit], scale) for unit in ('studio', 'one_bedroom', 'two_bedroom')}
    # Picked quietly, as the app picks for its world: a note on every save of a city written without rents (a ship
    # from the template, an imported map) would only be noise. The city file's own rents win when written.
    return []


def typical(tiers: dict) -> float:
    found = tiers.get('mid') or next(iter(tiers.values()))
    return sum(found['one_bedroom']) / 2


TIER_ORDER = ('low', 'mid', 'high', 'very-high')


def nearest(tiers: dict, tier: str) -> dict:
    place = TIER_ORDER.index(tier) if tier in TIER_ORDER else 1
    return min(tiers.items(), key=lambda item: abs((TIER_ORDER.index(item[0]) if item[0] in TIER_ORDER else 1)
                                                   - place))[1]


def period_scale(source: str, target: str) -> float:
    if source == target:
        return 1.0
    return WEEKS_PER_MONTH if source == 'week' else 1 / WEEKS_PER_MONTH


def scaled(pair, scale: float) -> list[int]:
    low, high = (max(1, round(value * scale)) for value in pair)
    return [low, max(low, high)]
