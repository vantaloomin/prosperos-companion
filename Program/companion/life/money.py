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
from companion.world import catalog, intimacy
from companion.world.source import CatalogWorld

PAY_TIERS = {'$': 0, '$$': 1, '$$$': 2, '$$$$': 3}
DEFAULT_TIER = 1
# Monthly take-home in US dollars for a city with typical rents, by pay tier; dearer cities pay a
# little more, but not as much more as their rents.
US_TAKE_HOME = (2600, 4300, 6900, 11500)
US_BASE_RENT = 1900
COST_EXPONENT = 0.3
# Elsewhere: take-home as a multiple of a labourer's wage, or of a typical one-bedroom rent. A modern city's wage is
# already an ordinary job's take-home, and pay spreads less there: a London pharmacist takes home about 1.5 times a
# low-paid job, not 2.8 times (E2E v0.13 found GBP 7,546 a month).
WAGE_MULTIPLE = (1.0, 1.7, 2.8, 5.0)
MODERN_WAGE_MULTIPLE = (1.0, 1.25, 1.5, 2.4)
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
    # A pastime with the user (companion/life/hobbies.py): a day pass, a class or a lane for two.
    'hobby': ((), 1, 0.004),
}
OUTING_NAMES = {'dinner': 'dinner out', 'drinks': 'a night out for drinks', 'show': 'tickets to a show',
                'museum': 'museum tickets', 'lunch-out': 'lunch out', 'coffee': 'café coffee',
                'study-cafe': 'an afternoon at a café', 'market': 'a browse at the market',
                'browse': 'a bit of shopping', 'festival': 'a day at a festival', 'birthday': 'a birthday dinner',
                'hobby': 'a pastime together'}

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
    if intimacy.reads_as_minor(definition):
        # Adult work is only ever an adult's (companion/world/intimacy.py makes the same check).
        offered = catalog.everyday(offered)
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
        multiple = MODERN_WAGE_MULTIPLE if era_of(city) == 'modern' else WAGE_MULTIPLE
        return wage * WORK_DAYS[city['rent_period']] * multiple[tier]
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


def goal_since(setup: dict, day: date) -> date:
    """When saving for the goal began: their own goal's start, else the start of this half of the year."""
    half = date(day.year, 1 if day.month <= 6 else 7, 1)
    try:
        since = date.fromisoformat(setup.get('goal_since') or '') if setup.get('saving_for') else half
    except ValueError:
        since = date(day.year, day.month, 1)
    return min(since, day)


def goal(found: Profile, setup: dict, day: date, drawn: float = 0.0) -> dict:
    """What they are saving for and how far along they are, less what big buys took from savings meanwhile
    (`drawn`: an engagement ring, their share of a wedding). Without a goal of their own, one is seeded for each half
    of the year, sized so steady saving just about reaches it."""
    half = date(day.year, 1 if day.month <= 6 else 7, 1)
    custom = bool(setup.get('saving_for'))
    since = goal_since(setup, day)
    rng = random.Random(f'{found.seed}:goal:{half.isoformat()}')
    options = GOALS[found.era][min(found.tier, len(GOALS[found.era]) - 1)]
    label = setup['saving_for'] if custom else rng.choice(options)
    cycles = 26 if found.cycle_days == 14 else 52
    amount = float(setup.get('goal') or 0) if custom else 0
    amount = amount or found.saving * found.per_cycle * cycles / 2 * rng.uniform(0.8, 1.3)
    saved = max(saved_since(found, since, day) - drawn, 0)
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
# Coins counted whole: silver pennies, groschen, silver weights (a part of one rounds up to one).
COINS = {'penny', 'groschen', 'sw'}
# Shillings, said in shillings and pence (twelve pence to the shilling): 4s. 1d., 2d.
SHILLINGS = {'shilling', 's'}
# Shillings of the pound sterling (London 1895), twenty to the pound.
STERLING = {'shilling'}
PREFIXES = ('$', '£', '€', '¥', '₩', '₹')


def shillings(value: float, symbol: str, pounds: bool = False) -> str:
    """'4s. 1d.', '2d.' or '15s.': whole shillings and pence, never a decimal. With `pounds` (sterling), a pound or
    more reads as pounds and shillings: '£36 16s.' for 736 shillings."""
    dot = '.' if symbol.endswith('.') else ''
    if pounds and value >= 20:
        whole, rest = divmod(round(value), 20)
        return f'£{whole:,}' + (f' {rest}s{dot}' if rest else '')
    if value >= 20:
        return f'{round(value):,}s{dot}'
    whole, pence = divmod(max(1, round(value * 12)), 12)
    return ' '.join(part for part in (f'{whole}s{dot}' if whole else '', f'{pence}d{dot}' if pence else '') if part)


def amount(value: float, currency: dict) -> str:
    """A rough amount as people say it: $1,240, £85, $5.50, ¥68,000, ₩1,250,000, 4s. 1d., 3 d."""
    code = currency.get('code')
    if code in SHILLINGS and value > 0:
        return shillings(value, currency['symbol'], code in STERLING)
    if code in COINS and 0 < value < 1:
        value = 1
    if value >= 100_000:
        rounded = round(value, -3)
    elif value >= 200:
        rounded = round(value, -1)
    else:
        rounded = round(value) if value >= 10 or code in WHOLE | COINS else round(value, 2)
    # Whole amounts without cents, the rest with both cent digits: $5, $5.50, never $5.5.
    number = f'{rounded:,.0f}' if rounded == int(rounded) else f'{rounded:,.2f}'
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
UPKEEP = {'dog': 0.025, 'cat': 0.015, 'rabbit': 0.01, 'bird': 0.005, 'parrot': 0.01, 'fish': 0.004, 'hamster': 0.004,
          'guinea-pig': 0.006, 'lizard': 0.008, 'snake': 0.006, 'tortoise': 0.005, 'ferret': 0.012, 'chickens': 0.006,
          'car': 0.08, 'motorcar': 0.08, 'scooter': 0.02, 'horse': 0.06, 'bike': 0.003, 'bicycle': 0.003}
PURCHASES = {'$': 0.01, '$$': 0.04, '$$$': 0.1, '$$$$': 0.25}


def household(connection, timeline_id: str, definition: dict, day: date) -> dict | None:
    """The home's rent, pets and vehicles, and what home changes, new clothes, looks, takeout, pastimes, outings with the
    user and trips cost this pay cycle, read through home.py's `monthly_costs` and `purchases`, wardrobe.py's, grooming.py's,
    kitchen.py's, media.py's, hobbies.py's, outings.py's, trips.py's and admin.py's
    `purchases`. None before the home exists or where money does not apply."""
    from companion.life import (  # all build from this budget, so import late
        admin,
        big_turns,
        grooming,
        hobbies,
        home,
        kitchen,
        media,
        outings,
        trips,
        wardrobe,
        wedding,
        work,
    )

    found = profile(definition)
    from companion.life import moving_in
    # Living together, the rent is split (companion/life/moving_in.py).
    costs = moving_in.split(connection, timeline_id, home.monthly_costs(connection, timeline_id, day), day) \
        if found else None
    if not costs:
        return None
    start = cycle_start(found, day)
    bought = [*home.purchases(connection, timeline_id, start, day), *wardrobe.purchases(connection, timeline_id, start, day),
              *grooming.purchases(connection, timeline_id, start, day),
              *outings.purchases(connection, timeline_id, start, day), *trips.purchases(connection, timeline_id, start, day),
              *kitchen.purchases(connection, timeline_id, start, day, definition, None, None),
              *media.purchases(connection, timeline_id, start, day, definition),
              *admin.purchases(connection, timeline_id, start, day),
              *hobbies.purchases(connection, timeline_id, start, day),
              *wedding.purchases(connection, timeline_id, start, day),
              *big_turns.purchases(connection, timeline_id, start, day)]
    # Raises, promotions and time between jobs (companion/life/work.py), or a pension once retired (big_turns.py);
    # what big buys took from savings since the goal began.
    since = goal_since(definition.get('money') or {}, day)
    drawn = drawn_since(connection, timeline_id, since, day)
    return {'costs': costs, 'purchases': sorted(bought, key=lambda item: item['date']),
            'pay': big_turns.pay(connection, timeline_id, day, work.pay(connection, timeline_id, day, start)),
            'drawn': drawn}


def drawn_since(connection, timeline_id: str, since: date, day: date) -> float:
    """What big buys took from savings between two dates: a ring or a wedding, or a deposit on a place."""
    from companion.life import big_turns, wedding
    deposits = [item for item in big_turns.purchases(connection, timeline_id, since, day) if item.get('savings')]
    return sum(item['cost'] for item in [*wedding.purchases(connection, timeline_id, since, day), *deposits])


# How far back savings on hand reach: what they put by in this long, less what came out of it.
SAVED_DAYS = 365


def on_hand(connection, timeline_id: str, definition: dict, day: date) -> float | None:
    """The savings they have to draw on for a big buy (a ring, their share of a wedding): what they put by in the
    last year at their pay and rent now, less what big buys took from it. None where money does not apply."""
    found = profile(definition)
    if not found:
        return None
    home = household(connection, timeline_id, definition, day)
    if home:
        found = with_home(found, home['costs'], home.get('pay'))
    since = day - timedelta(days=SAVED_DAYS)
    drawn = drawn_since(connection, timeline_id, since, day)
    return max(saved_since(found, since, day) - drawn, 0.0)


def monthly_share(found: Profile) -> float:
    """A month's take-home in this budget's period: shares of it become amounts per period."""
    return found.income if found.period == 'month' else found.income * 52 / 12


def with_home(found: Profile, costs: dict, pay: dict | None = None) -> Profile:
    """The budget with the home's rent (when it names one in this city's money) and its upkeep, and their pay after
    raises, or what they live on between jobs (`pay`, from work.pay)."""
    if pay and pay.get('factor'):
        found = replace(found, income=found.income * pay['factor'])
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
    trips carry their own cost; `shown` is the screen's wording when it differs from the model's. An engagement ring and their share of the wedding come from savings
    (`savings`), so they leave this cycle's money alone."""
    month = monthly_share(found)
    return [{'label': item['text'], 'on': item['date'],
             'cost': round(item.get('cost') or PURCHASES.get(item['spend'], 0) * month, 2),
             'for': item.get('for', 'home'), **({'savings': True} if item.get('savings') else {}),
             **({'shown': item['shown']} if item.get('shown') else {})}
            for item in purchases if item.get('cost') or PURCHASES.get(item['spend'])]


def spendable(connection, timeline_id: str, definition: dict, day: date) -> float:
    """What is left to spend on this day once the home's rent and this cycle's outings, trips, clothes and home
    purchases are counted, as the Today panel shows it."""
    found = snapshot(definition, day.isoformat(), household(connection, timeline_id, definition, day))
    return found['left'] if found['available'] else 0.0


def snapshot(definition: dict, local_date: str, home: dict | None = None) -> dict:
    """The budget as the Today panel and chat context see it on this local date. `home` is from
    `household`: with it, rent and upkeep come from their home and its purchases count as spending."""
    found = profile(definition)
    if found and home:
        found = with_home(found, home['costs'], home.get('pay'))
    if not found:
        city = city_for(definition)
        reason = f"There is no money in {city['name']}." if city else \
            'Money follows a home city with rents and prices. Pick one in Character.'
        return {'available': False, 'reason': reason}
    day = date.fromisoformat(local_date)
    start = cycle_start(found, day)
    bought = spent_at_home(found, home['purchases']) if home else []
    current = cycle(found, start)
    left = left_on(found, day) - sum(item['cost'] for item in bought if not item.get('savings'))
    setup = definition.get('money') or {}
    currency = found.city['currency']
    payday = start + timedelta(days=found.cycle_days)
    return {
        'available': True, 'currency': currency, 'period': found.period, 'style': found.style,
        'career': {'id': found.career['id'], 'name': found.career['name'], 'pay': found.career['pay'],
                   'guessed': found.guessed} if found.career else None,
        'between_jobs': bool(home and (home.get('pay') or {}).get('between_jobs')),
        'retired': bool(home and (home.get('pay') or {}).get('retired')),
        'owned': bool(home and home['costs'].get('owned')),
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
        'goal': goal(found, setup, day, home.get('drawn', 0.0) if home else 0.0),
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
    # A place they bought has a mortgage instead of rent (companion/life/big_turns.py).
    housing = f"the mortgage on {place} is about {text['rent']}" if view.get('owned') else \
        f"rent is about {text['rent']} for {place}"
    lines = [('budget', f"- You take home about {text['income']} {per}{work}; {housing}.")]
    if view.get('between_jobs'):
        lines = [('budget', f"- Between jobs, you have about {text['income']} {per} to live on; {housing}.")]
    if view.get('retired'):
        lines = [('budget', f"- Retired, you live on a pension of about {text['income']} {per}; {housing}.")]
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


SPENT_ON = {'clothes': 'on clothes', 'outing': 'going out', 'trip': 'on a trip', 'food': 'on takeout',
            'hobby': 'on your pastimes', 'ring': 'from your savings', 'wedding': 'from your savings',
            'school': 'on your course', 'deposit': 'from your savings'}


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
