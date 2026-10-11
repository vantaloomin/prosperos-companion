"""Money and budget: what the companion earns, what rent takes, and what is left until payday.

Everything is computed from static data, with no model call and no stored state: the career's pay
tier (companion/world/data/careers.json), the home city's rents, prices and currency, and the
character's own money setup. The same character and date always give the same budget, splurge,
surprise bill and savings progress. The model only phrases what is listed here.

`affordable(definition, activity_key, local_date)` is the composer's one hook: on a tight day an
outing that costs money gives way to a free one. Settings with no money (Oz) or no known city
leave every activity affordable.
"""
import random
import re
from dataclasses import dataclass, replace
from datetime import date, timedelta
from functools import lru_cache

from companion.characters import require_current
from companion.clock import zone
from companion.world import catalog
from companion.world.source import CatalogWorld

PAY_TIERS = {'$': 0, '$$': 1, '$$$': 2, '$$$$': 3}
DEFAULT_TIER = 1
# Monthly take-home in US dollars for a city with typical rents, by pay tier; dearer cities pay a
# little more, but not as much more as their rents.
US_TAKE_HOME = (2600, 4300, 6900, 11500)
US_BASE_RENT = 1900
COST_EXPONENT = 0.3
# Elsewhere: take-home as a multiple of a labourer's wage, or of a typical one-bedroom rent.
WAGE_MULTIPLE = (1.0, 1.7, 2.8, 5.0)
RENT_MULTIPLE = (2.4, 3.4, 5.0, 8.0)
WORK_DAYS = {'month': 22, 'week': 6}
ESSENTIALS = {'modern': 0.3, 'jazz-age': 0.35, 'other': 0.4}
# Share of what is left after rent and essentials that goes on fun; the rest is saved.
STYLES = {'careful': 0.45, 'balanced': 0.65, 'spender': 0.9}
# How fast the fun money goes through a pay cycle; spenders run dry before payday.
PACE = {'careful': 0.65, 'balanced': 0.8, 'spender': 1.15}
SPLURGE_CHANCE = {'careful': 0.15, 'balanced': 0.3, 'spender': 0.55}
SPLURGE_SHARE = 0.25
# Better-paid people can dip into savings for an outing: this share of a cycle's savings, by pay tier.
CUSHION = (0, 0.15, 0.4, 0.8)
SURPRISE_CHANCE = 0.12
SURPRISE_SHARE = 0.4
TIGHT = 0.15
# The place each pay tier looks for first, then smaller ones.
UNITS = (('studio',), ('studio',), ('one_bedroom', 'studio'), ('two_bedroom', 'one_bedroom', 'studio'))
UNIT_LABELS = {
    'modern': {'studio': 'a studio', 'one_bedroom': 'a one-bedroom', 'two_bedroom': 'a two-bedroom',
               'shared': 'a room in a shared place'},
    'jazz-age': {'studio': 'a furnished room', 'one_bedroom': 'a two-room flat', 'two_bedroom': 'a four-room flat',
                 'shared': 'a room in a boarding house'},
    'other': {'studio': 'a rented room', 'one_bedroom': 'a couple of rented rooms', 'two_bedroom': 'a small house',
              'shared': 'a shared room'},
}
RENT_CEILING = 0.45
HOOD_TIERS = (('low', 'mid'), ('mid', 'low'), ('mid', 'high'), ('high', 'very-high'))
FIRST_FRIDAY = date(2026, 1, 2)

# What an outing costs: the city's price items to look for (first found wins, times a count), else
# a share of a month's take-home. Activities not listed cost nothing extra (home, work, walks, or a
# gym membership already in the essentials).
COSTS = {
    'dinner': (('dinner', 'inn-meal', 'chophouse', 'eating-house', 'meal'), 1, 0.012),
    'drinks': (('cocktail', 'beer', 'ale', 'wine', 'whiskey'), 3, 0.008),
    'show': (('show', 'theatre', 'music-hall', 'opera-house', 'movie'), 2, 0.012),
    'museum': ((), 1, 0.005),
    'lunch-out': (('cheap-lunch', 'pie-and-peas', 'pie', 'meal'), 1, 0.004),
    'coffee': (('latte', 'coffee', 'coffee-stall'), 1, 0.0015),
    'study-cafe': (('latte', 'coffee', 'coffee-stall'), 2, 0.003),
    'market': ((), 1, 0.006),
    'browse': ((), 1, 0.008),
    'festival': ((), 1, 0.008),
    'birthday': (('dinner', 'inn-meal', 'chophouse', 'eating-house', 'meal'), 2, 0.02),
}
OUTING_NAMES = {'dinner': 'dinner out', 'drinks': 'a night out for drinks', 'show': 'tickets to a show',
                'museum': 'museum tickets', 'lunch-out': 'lunch out', 'coffee': 'café coffee',
                'study-cafe': 'an afternoon at a café', 'market': 'a browse at the market',
                'browse': 'a bit of shopping', 'festival': 'a day at a festival', 'birthday': 'a birthday dinner'}

SPLURGES = {
    'modern': ('new running shoes', 'a really nice dinner out', 'concert tickets', 'an impulse-buy jacket',
               'a stack of new books', 'a fancy coffee machine', 'takeout three nights in a row'),
    'jazz-age': ('a new cloche hat', 'a steak dinner downtown', 'a night at a speakeasy', 'a stack of phonograph '
                 'records', 'orchestra seats at a revue', 'silk stockings', 'a new radio set on the installment plan'),
    'other': ('a new hat', 'a good meal at the inn', 'a bottle of something fine', 'ribbon and lace',
              'a seat at the theatre', 'a pair of fine gloves'),
}
SURPRISES = {
    'modern': ('a vet bill', 'a cracked phone screen', 'a parking ticket', 'a dentist visit', 'new tyres',
               'a broken laptop charger', 'an overdue utility bill'),
    'jazz-age': ('a doctor\'s house call', 'a resoled pair of shoes', 'a dentist\'s bill', 'a cracked window',
                 'a coal delivery', 'a fine from the magistrate', 'a coat that needed mending'),
    'other': ('a doctor\'s visit', 'a broken boot heel', 'a fine from the watch', 'a cracked window',
              'a lame horse\'s shoeing', 'a coat that needed mending'),
}
GOALS = {
    'modern': (('an emergency fund', 'a new phone', 'a weekend away', 'summer concert tickets'),
               ('a trip abroad', 'a used car', 'a new laptop', 'a deposit on a nicer place'),
               ('a trip abroad', 'a down payment fund', 'a new car', 'a sabbatical fund'),
               ('a down payment', 'a long trip abroad', 'a small investment portfolio', 'a renovation')),
    'jazz-age': (('a good winter coat', 'a radio set', 'a little nest egg', 'a trip to visit family'),
                 ('a phonograph', 'a week at the shore', 'a nest egg in the savings bank', 'a better flat'),
                 ('a secondhand Ford', 'a few shares of stock', 'a trip to Europe', 'a down payment on a house'),
                 ('a new motorcar', 'a summer place', 'a portfolio of stocks', 'a trip to Europe')),
    'other': (('a good winter coat', 'new boots', 'a little nest egg', 'a trip to visit family'),
              ('a good winter coat', 'a trip to the seaside', 'a nest egg', 'a better room')),
}


@dataclass(frozen=True)
class Profile:
    """A character's budget per pay cycle and per budget period, in the city's currency."""
    city: dict
    era: str
    career: dict | None
    guessed: bool
    tier: int
    style: str
    period: str
    cycle_days: int
    income: float
    rent: float
    unit: str
    neighborhood: str
    essentials: float
    fun: float
    saving: float
    seed: str
    # Pets and vehicles from their home (companion/life/home.py), per budget period.
    upkeep: float = 0

    @property
    def per_cycle(self) -> float:
        """Budget-period amounts times this give one pay cycle's."""
        return self.cycle_days * 12 / 365 if self.period == 'month' else self.cycle_days / 7

    @property
    def fun_cycle(self) -> float:
        return self.fun * self.per_cycle


def city_for(definition: dict) -> dict | None:
    world = CatalogWorld()
    for text in (definition.get('home_city'), definition.get('location')):
        if text and (found := world.find(text)):
            return found
    return None


def era_of(city: dict) -> str:
    """The era's wording for money: modern, the 1920s, or any other past."""
    return 'modern' if city['era'] in ('modern', 'future') else city['era'] if city['era'] in ESSENTIALS else 'other'


def has_money(city: dict) -> bool:
    return city['currency']['code'] != 'none' and any(hood.get('rent') for hood in city['neighborhoods'])


def guess_career(definition: dict, offered: dict[str, dict]) -> dict | None:
    """The career named in who they are, their background or routine, by its name or its id's words
    ("teacher" finds "Public school teacher"); the first one mentioned, the longest name on a tie."""
    text = ' '.join(definition.get(key) or '' for key in ('identity', 'background', 'routine'))
    words = f' {plain(text)} '
    found = [(words.find(f' {name} '), -len(name), career['id'])
             for career in offered.values() for name in {plain(career['name']), plain(career['id'])}
             if f' {name} ' in words]
    return offered[min(found)[2]] if found else None


def plain(text: str) -> str:
    return ' '.join(re.findall(r'[a-z]+', text.casefold()))


def career_for(definition: dict, city: dict) -> tuple[dict | None, bool]:
    offered = catalog.careers_for(city)
    chosen = (definition.get('money') or {}).get('career') or ''
    if chosen in offered:
        return offered[chosen], False
    return guess_career(definition, offered), True


def price(city: dict, ids) -> float | None:
    found = {item['id']: item for item in city.get('prices', [])}
    for key in ids:
        if key in found:
            return (found[key]['low'] + found[key]['high']) / 2
    return None


def typical_rent(city: dict, unit: str = 'one_bedroom') -> float:
    rents = [sum(hood['rent'][unit]) / 2 for hood in city['neighborhoods'] if hood.get('rent')]
    return sum(rents) / len(rents)


def take_home(city: dict, tier: int) -> float:
    """Income per budget period (the city's rent period)."""
    if city['currency']['code'] == 'USD' and era_of(city) == 'modern':
        return US_TAKE_HOME[tier] * (typical_rent(city) / US_BASE_RENT) ** COST_EXPONENT
    wage = price(city, ('wage',))
    if wage:
        return wage * WORK_DAYS[city['rent_period']] * WAGE_MULTIPLE[tier]
    return typical_rent(city) * RENT_MULTIPLE[tier]


LIVES = re.compile(r'\b(lives?|living|home|apartment|flat|house|rowhouse|condo)\b', re.IGNORECASE)


def where_they_live(definition: dict) -> str:
    """The sentences of who they are (and their routine) that say where they live, such as "He lives
    alone in a small rowhouse in Canton." Their background is left out: it is where they grew up."""
    text = ' '.join(definition.get(key) or '' for key in ('identity', 'routine'))
    return ' '.join(sentence for sentence in re.split(r'(?<=[.!?])\s+', text) if LIVES.search(sentence))


def home_hood(definition: dict, city: dict, tier: int, seed: str) -> dict:
    """Their neighbourhood: one named in their location, else in the draft's own words about where
    they live, else one with rents that fit their pay."""
    hoods = [hood for hood in city['neighborhoods'] if hood.get('rent')]
    text = ' '.join(definition.get(key) or '' for key in ('near', 'location')).casefold()
    named = [hood for hood in hoods if hood['name'].casefold() in text or hood['id'] == text]
    if named:
        return named[0]
    lived = where_they_live(definition)
    named = [hood for hood in hoods if re.search(rf"\b{re.escape(hood['name'])}\b", lived, re.IGNORECASE)]
    if named:
        return named[0]
    fitting = [hood for hood in hoods if hood['rent_tier'] in HOOD_TIERS[tier]] or hoods
    return random.Random(f'{seed}:hood').choice(fitting)


def housing(hood: dict, tier: int, income: float, seed: str) -> tuple[str, float]:
    """The place they can manage: a smaller one, or a shared one, when rent would take too much."""
    point = random.Random(f'{seed}:rent').random()
    rent = hood['rent']
    for unit in UNITS[tier]:
        low, high = rent[unit]
        amount = low + (high - low) * point
        if amount <= income * RENT_CEILING:
            return unit, amount
    low, _high = rent['two_bedroom']
    return 'shared', min(low / 2, income * 0.5)


def build(definition: dict) -> Profile | None:
    city = city_for(definition)
    if not city or not has_money(city):
        return None
    setup = definition.get('money') or {}
    career, guessed = career_for(definition, city)
    tier = PAY_TIERS.get(career['pay'], DEFAULT_TIER) if career else DEFAULT_TIER
    style = setup.get('style') if setup.get('style') in STYLES else 'balanced'
    seed = f"money:{definition.get('name', '')}:{city['id']}"
    income = take_home(city, tier)
    hood = home_hood(definition, city, tier, seed)
    unit, rent = housing(hood, tier, income, seed)
    era = era_of(city)
    essentials = income * ESSENTIALS[era]
    spare = max(income - rent - essentials, 0)
    weekly = city['rent_period'] == 'week'
    return Profile(city=city, era=era, career=career, guessed=guessed, tier=tier, style=style,
                   period=city['rent_period'], cycle_days=7 if weekly else 14, income=income, rent=rent, unit=unit,
                   neighborhood=hood['name'], essentials=essentials, fun=spare * STYLES[style],
                   saving=spare * (1 - STYLES[style]), seed=seed)


@lru_cache(maxsize=256)
def cached(key: tuple) -> Profile | None:
    definition = dict(key)
    return build({**definition, 'money': dict(definition['money'])})


PROFILE_KEYS = ('name', 'home_city', 'location', 'near', 'identity', 'background', 'routine')


def profile(definition: dict) -> Profile | None:
    """The budget for this definition (cached: the composer asks once per option per slot)."""
    setup = definition.get('money') or {}
    key = tuple((name, definition.get(name) or '') for name in PROFILE_KEYS)
    key += (('money', tuple(sorted((name, str(value)) for name, value in setup.items()))),)
    return cached(key)


# Pay cycles: every other Friday where rent is monthly, every Saturday where it is weekly.
def cycle_start(found: Profile, day: date) -> date:
    if found.cycle_days == 7:
        return day - timedelta(days=(day.weekday() - 5) % 7)
    offset = 7 * (random.Random(f'{found.seed}:payweek').random() < 0.5)
    anchor = FIRST_FRIDAY + timedelta(days=offset)
    return day - timedelta(days=(day - anchor).days % 14)


@dataclass(frozen=True)
class Cycle:
    start: date
    splurge: tuple[str, date, float] | None
    surprise: tuple[str, date, float] | None


def cycle(found: Profile, start: date) -> Cycle:
    """One pay cycle's seeded splurge (on or just after payday) and surprise bill (any day)."""
    rng = random.Random(f'{found.seed}:{start.isoformat()}')
    splurge = surprise = None
    if rng.random() < SPLURGE_CHANCE[found.style] and found.fun > 0:
        splurge = (rng.choice(SPLURGES[found.era]), start + timedelta(days=rng.randint(0, 1)),
                   found.fun_cycle * SPLURGE_SHARE)
    if rng.random() < SURPRISE_CHANCE:
        surprise = (rng.choice(SURPRISES[found.era]), start + timedelta(days=rng.randint(0, found.cycle_days - 1)),
                    found.income * found.per_cycle * SURPRISE_SHARE)
    return Cycle(start, splurge, surprise)


def left_on(found: Profile, day: date) -> float:
    """Money they can spend at the start of this day until the next payday: what is left of the fun
    money, plus what they would dip into savings for. Negative when overspent."""
    current = cycle(found, cycle_start(found, day))
    elapsed = (day - current.start).days
    left = found.fun_cycle * (1 - PACE[found.style] * elapsed / found.cycle_days)
    for happening in (current.splurge, current.surprise):
        if happening and happening[1] <= day:
            # A surprise bill is half covered from savings.
            left -= happening[2] if happening is current.splurge else happening[2] / 2
    return left + found.saving * found.per_cycle * CUSHION[found.tier]


def cost(found: Profile, activity_key: str) -> float:
    if activity_key not in COSTS:
        return 0
    ids, count, share = COSTS[activity_key]
    unit = price(found.city, ids)
    return unit * count if unit else found.income * share * (1 if found.period == 'month' else 52 / 12)


def affordable(definition: dict, activity_key: str, local_date: str) -> bool:
    """Whether the character can pay for this activity on this local date. Free ones always are."""
    found = profile(definition)
    if not found or activity_key not in COSTS:
        return True
    return cost(found, activity_key) <= left_on(found, date.fromisoformat(local_date))


def goal(found: Profile, setup: dict, day: date) -> dict:
    """What they are saving for and how far along they are. Without a goal of their own, one is
    seeded for each half of the year, sized so steady saving just about reaches it."""
    half = date(day.year, 1 if day.month <= 6 else 7, 1)
    custom = bool(setup.get('saving_for'))
    try:
        since = date.fromisoformat(setup.get('goal_since') or '') if custom else half
    except ValueError:
        since = date(day.year, day.month, 1)
    since = min(since, day)
    rng = random.Random(f'{found.seed}:goal:{half.isoformat()}')
    options = GOALS[found.era][min(found.tier, len(GOALS[found.era]) - 1)]
    label = setup['saving_for'] if custom else rng.choice(options)
    cycles = 26 if found.cycle_days == 14 else 52
    amount = float(setup.get('goal') or 0) if custom else 0
    amount = amount or found.saving * found.per_cycle * cycles / 2 * rng.uniform(0.8, 1.3)
    saved = saved_since(found, since, day)
    return {'label': label, 'amount': round(amount, 2), 'saved': round(min(saved, amount), 2),
            'share': round(min(saved / amount, 1), 2) if amount else 0, 'custom': custom,
            'since': since.isoformat(), 'stalled': found.saving <= 0}


def saved_since(found: Profile, since: date, day: date) -> float:
    """Savings put by from `since` up to `day`, less the half of each surprise bill they covered."""
    total, start = 0.0, cycle_start(found, since)
    for _ in range(260):
        if start > day:
            break
        if start >= since:
            total += found.saving * found.per_cycle
        current = cycle(found, start)
        if current.surprise and since <= current.surprise[1] <= day:
            total -= current.surprise[2] / 2
        start += timedelta(days=found.cycle_days)
    return max(total, 0)


# Currencies without minor units, and symbols written before the number.
WHOLE = {'JPY', 'KRW'}
PREFIXES = ('$', '£', '€', '¥', '₩', '₹')


def amount(value: float, currency: dict) -> str:
    """A rough amount as people say it: $1,240, £85, ¥68,000, ₩1,250,000."""
    if value >= 100_000:
        rounded = round(value, -3)
    elif value >= 200:
        rounded = round(value, -1)
    else:
        rounded = round(value) if value >= 10 or currency.get('code') in WHOLE else round(value, 1)
    number = f'{rounded:,.0f}' if rounded == int(rounded) else f'{rounded:,.1f}'
    symbol = currency['symbol']
    if symbol in PREFIXES:
        return f'{symbol}{number}'
    return f'{number} {symbol or currency["name"]}'.strip()


def happened(item, day: date) -> dict | None:
    if not item or item[1] > day:
        return None
    return {'label': item[0], 'on': item[1].isoformat(), 'cost': round(item[2], 2)}


# What their home costs to keep, as shares of a month's take-home (so it works in any currency), and
# what a home change costs by its spend tier.
UPKEEP = {'dog': 0.025, 'cat': 0.015, 'rabbit': 0.01, 'bird': 0.005,
          'car': 0.08, 'motorcar': 0.08, 'scooter': 0.02, 'horse': 0.06, 'bike': 0.003, 'bicycle': 0.003}
PURCHASES = {'$': 0.01, '$$': 0.04, '$$$': 0.1, '$$$$': 0.25}


def household(connection, timeline_id: str, definition: dict, day: date) -> dict | None:
    """The home's rent, pets and vehicles, and what home changes, new clothes, outings with the user and trips cost
    this pay cycle, read through home.py's `monthly_costs` and `purchases`, wardrobe.py's, outings.py's and trips.py's
    `purchases`. None before the home exists or where money does not apply."""
    from companion.life import home, outings, trips, wardrobe  # all build from this budget, so import late

    found = profile(definition)
    costs = home.monthly_costs(connection, timeline_id, day) if found else None
    if not costs:
        return None
    start = cycle_start(found, day)
    bought = [*home.purchases(connection, timeline_id, start, day), *wardrobe.purchases(connection, timeline_id, start, day),
              *outings.purchases(connection, timeline_id, start, day), *trips.purchases(connection, timeline_id, start, day)]
    return {'costs': costs, 'purchases': sorted(bought, key=lambda item: item['date'])}


def monthly_share(found: Profile) -> float:
    """A month's take-home in this budget's period: shares of it become amounts per period."""
    return found.income if found.period == 'month' else found.income * 52 / 12


def with_home(found: Profile, costs: dict) -> Profile:
    """The budget with the home's rent (when it names one in this city's money) and its upkeep."""
    rent = found.rent
    if costs.get('rent') and (costs.get('currency') or found.city['currency']) == found.city['currency']:
        rent = costs['rent'] if costs.get('rent_period', 'month') == found.period else \
            costs['rent'] * (12 / 52 if found.period == 'week' else 52 / 12)
    month = monthly_share(found)
    upkeep = sum(UPKEEP.get(kind, 0) for kind in [*costs.get('pets', ()), *costs.get('vehicles', ())]) * month
    upkeep *= 1 if found.period == 'month' else 12 / 52
    spare = max(found.income - rent - found.essentials - upkeep, 0)
    share = STYLES[found.style]
    return replace(found, rent=rent, upkeep=upkeep, fun=spare * share, saving=spare * (1 - share))


def spent_at_home(found: Profile, purchases: list[dict]) -> list[dict]:
    """Home changes, clothes, outings and trips this cycle with what they cost ({label, on, cost, for}). Outings and
    trips carry their own cost."""
    month = monthly_share(found)
    return [{'label': item['text'], 'on': item['date'],
             'cost': round(item.get('cost') or PURCHASES.get(item['spend'], 0) * month, 2),
             'for': item.get('for', 'home')} for item in purchases if item.get('cost') or PURCHASES.get(item['spend'])]


def snapshot(definition: dict, local_date: str, home: dict | None = None) -> dict:
    """The budget as the Today panel and chat context see it on this local date. `home` is from
    `household`: with it, rent and upkeep come from their home and its purchases count as spending."""
    found = profile(definition)
    if found and home:
        found = with_home(found, home['costs'])
    if not found:
        city = city_for(definition)
        reason = f"There is no money in {city['name']}." if city else \
            'Money follows a home city with rents and prices. Pick one in Character.'
        return {'available': False, 'reason': reason}
    day = date.fromisoformat(local_date)
    start = cycle_start(found, day)
    bought = spent_at_home(found, home['purchases']) if home else []
    current, left = cycle(found, start), left_on(found, day) - sum(item['cost'] for item in bought)
    setup = definition.get('money') or {}
    currency = found.city['currency']
    payday = start + timedelta(days=found.cycle_days)
    return {
        'available': True, 'currency': currency, 'period': found.period, 'style': found.style,
        'career': {'id': found.career['id'], 'name': found.career['name'], 'pay': found.career['pay'],
                   'guessed': found.guessed} if found.career else None,
        'housing': {'unit': found.unit, 'label': UNIT_LABELS[found.era][found.unit], 'neighborhood': found.neighborhood},
        'budget': {key: round(getattr(found, key), 2) for key in ('income', 'rent', 'upkeep', 'essentials', 'fun',
                                                                  'saving')},
        'rent_from': 'home' if home and home['costs'].get('rent') else 'budget', 'bought': bought,
        'payday': {'last': start.isoformat(), 'next': payday.isoformat(), 'cycle_days': found.cycle_days,
                   'today': day == start},
        'left': round(left, 2), 'fun_cycle': round(found.fun_cycle, 2),
        'tight': left < found.fun_cycle * TIGHT, 'flush': left > found.fun_cycle * 0.75,
        'splurge': happened(current.splurge, day), 'surprise': happened(current.surprise, day),
        'cant_afford': [OUTING_NAMES[key] for key in COSTS if cost(found, key) > left and key != 'birthday'],
        'goal': goal(found, setup, day),
        'text': {'income': amount(found.income, currency), 'rent': amount(found.rent, currency),
                 'essentials': amount(found.essentials, currency), 'fun': amount(found.fun, currency),
                 'upkeep': amount(found.upkeep, currency),
                 'saving': amount(found.saving, currency), 'left': amount(max(left, 0), currency)},
    }


def context_lines(definition: dict, local_date: str, home: dict | None = None) -> list[tuple[str, str]]:
    """(identity, line) pairs for the chat context's money section; [] where money does not apply."""
    view = snapshot(definition, local_date, home)
    if not view['available']:
        return []
    text, per = view['text'], 'a month' if view['period'] == 'month' else 'a week'
    work = f" as a {view['career']['name'].lower()}" if view['career'] else ''
    place = 'your home' if view['rent_from'] == 'home' else \
        f"{view['housing']['label']} in {view['housing']['neighborhood']}"
    lines = [('budget', f"- You take home about {text['income']} {per}{work}; rent is about {text['rent']} for {place}.")]
    if view['budget']['upkeep']:
        lines.append(('upkeep', f"- Your pets and getting around cost about {text['upkeep']} {per}."))
    for item in view['bought']:
        where = SPENT_ON.get(item['for'], 'at home')
        lines.append((f"bought:{item['on']}" + (f":{item['for']}" if item['for'] != 'home' else ''), f"- This pay period you spent money {where}: you {item['label']}."))
    lines.append(('payday', '- ' + payday_text(view, local_date)))
    if view['splurge']:
        lines.append(('splurge', f"- This pay period you splurged on {view['splurge']['label']}."))
    if view['surprise']:
        lines.append(('surprise', f"- An unexpected expense hit this pay period: {view['surprise']['label']}."))
    if view['cant_afford']:
        lines.append(('cant', f"- Right now you can't really afford {', '.join(view['cant_afford'][:4])}."))
    found = view['goal']
    progress = 'saving has stalled for now' if found['stalled'] else f"about {round(found['share'] * 100)}% there"
    lines.append(('goal', f"- Saving for {found['label']}: {progress}."))
    return [(f'money:{local_date}:{key}', line) for key, line in lines]


SPENT_ON = {'clothes': 'on clothes', 'outing': 'going out', 'trip': 'on a trip'}


def payday_text(view: dict, local_date: str) -> str:
    days = (date.fromisoformat(view['payday']['next']) - date.fromisoformat(local_date)).days
    payday = date.fromisoformat(view['payday']['next'])
    when = 'tomorrow' if days == 1 else f'on {payday:%A, %B} {payday.day} (in {days} days)'
    if view['payday']['today']:
        head = 'Payday was today.'
    else:
        head = f'Next payday is {when}.'
    if view['tight']:
        return f'{head} Money is tight until then.'
    if view['flush']:
        return f"{head} You have some spending money (about {view['text']['left']})."
    return f"{head} About {view['text']['left']} left to spend until then."


def view(database) -> dict:
    """The current companion's budget on their local today (GET /api/today/money)."""
    with database.connect() as connection:
        companion = require_current(connection)
        version = companion['version']
        day = database.clock.now().astimezone(zone(version['timezone'])).date()
        home = household(connection, companion['active_timeline_id'], version['definition'], day)
    return {'date': day.isoformat(), **snapshot(version['definition'], day.isoformat(), home)}
