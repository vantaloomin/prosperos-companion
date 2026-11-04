"""Owning their home: whether the companion rents, pays off a mortgage or owns their place outright, and what owning
costs (Vanta's tester, 2026-11-04: "they can't be owners? Only have a rent?").

No model call and no stored state beyond the home item: the app decides once, when their home is first assembled
(companion/life/home.py), from what their own words say ("owns a cottage", "inherited the family farm", "rents a
room"), else from their age, their pay and their world's era, the way people of that age and pay usually live there.
The user can change it afterwards with the Home picker in Work and money (MoneySetup.home), which always wins.

What it costs, per the city's rent period, as a share of the rent the same place would fetch (so it works in any
currency): a mortgage is paid instead of rent, and owners pay taxes, insurance and repairs on top (`share`). Owning
outright, only the taxes and repairs are left. A ship or station has cabins to rent, never to own.
"""
import random
import re

TENURES = ('rent', 'mortgage', 'owned')
# Taxes, insurance and repairs as a share of the place's rent, by money era (money.era_of), and a medieval kingdom's
# dues and repairs. A US owner pays about 1% of the price a year in property tax, a little insurance and about 1% in
# upkeep; with a price about twenty years of rent, that is about a third of a year's rent.
SHARE = {'modern': 0.35, 'jazz-age': 0.25, 'other': 0.2}
MEDIEVAL_SHARE = 0.15
# What those costs are called, by era: the card's line and the chat line both say it.
WORDS = {'modern': 'property tax, insurance and upkeep', 'jazz-age': 'property taxes and repairs',
         'other': 'rates and repairs'}
MEDIEVAL_WORDS = 'dues and repairs'
# A mortgage payment against the rent of the same place (big_turns.MORTGAGE): about the same.
MORTGAGE = (0.85, 1.15)
# Who owns their home, by age (US households, about 2024): under 25, 25-34, 35-44, 45-54, 55-64, 65 and over.
AGES = (25, 35, 45, 55, 65)
OWNS = (0.12, 0.38, 0.6, 0.7, 0.76, 0.8)
# Of the owners, who has paid it off by that age.
OUTRIGHT = (0.03, 0.06, 0.12, 0.25, 0.45, 0.65)
# How much likelier a pay tier is to own (money.PAY_TIERS order), and an era's: renting was the rule in a 1920s
# city, and most townsfolk of an older past rented their rooms; mortgages there were short, so more owned outright.
TIER = (0.45, 0.85, 1.1, 1.25)
ERA = {'modern': 1.0, 'jazz-age': 0.75, 'other': 0.45}
ERA_OUTRIGHT = {'modern': 0.0, 'jazz-age': 0.1, 'other': 0.25}
CEILING = 0.95

PLACES = (r'(?:house|home|flat|apartment|condo|cottage|place|farm|farmhouse|townhouse|rowhouse|bungalow|cabin|'
          r'manor|estate|homestead|cottage|croft|villa|loft|shop and the rooms above it)')
OWNER = r'(?:a|an|the|his|her|their|my|its)'
OUTRIGHT_WORDS = re.compile(rf'\b(?:inherited {OWNER} (?:own |family |old )?{PLACES}|paid off {OWNER} (?:{PLACES}|'
                            rf'mortgage)|owns? {OWNER} (?:own )?{PLACES} outright|owns? it outright|mortgage-free)\b',
                            re.IGNORECASE)
MORTGAGE_WORDS = re.compile(rf'\b(?:mortgage|bought {OWNER} (?:first |own )?{PLACES})\b', re.IGNORECASE)
OWN_WORDS = re.compile(rf'\b(?:homeowner|owns? {OWNER} (?:own |little |small |old )?{PLACES}|{PLACES} (?:that|which) '
                       rf'(?:he|she|they) owns?)\b', re.IGNORECASE)
RENT_WORDS = re.compile(r'\b(?:rents? (?:a|an|the)|renting|rented|tenant|lodger|lodgings|landlord|landlady|'
                        r'boarding house|room(?:mate|mates)|flatmates?|housemates?|lives with (?:his|her|their) '
                        r'parents)\b', re.IGNORECASE)


def share(era: str, medieval: bool) -> float:
    return MEDIEVAL_SHARE if medieval else SHARE.get(era, SHARE['other'])


def words(era: str, medieval: bool) -> str:
    return MEDIEVAL_WORDS if medieval else WORDS.get(era, WORDS['other'])


def costs(value: float, tenure: str, era: str, medieval: bool) -> tuple[float, float]:
    """(what they pay for the place, what owning it costs on top) per period, from `value`: the rent, or for a place
    with a mortgage the payment."""
    if tenure == 'rent':
        return value, 0.0
    extra = value * share(era, medieval)
    return (0.0 if tenure == 'owned' else value), extra


def said(definition: dict) -> str | None:
    """What their own words say about owning: 'owned', 'mortgage', 'rent', or None."""
    text = ' '.join(str(definition.get(key) or '') for key in ('identity', 'background', 'routine'))
    if OUTRIGHT_WORDS.search(text):
        return 'owned'
    if MORTGAGE_WORDS.search(text):
        return 'mortgage'
    if OWN_WORDS.search(text):
        return 'owns'
    if RENT_WORDS.search(text):
        return 'rent'
    return None


def band(age: int) -> int:
    return sum(age >= edge for edge in AGES)


def decide(definition: dict, era: str, tier: int, age: int | None, seed: str, shared: bool = False,
           aboard: bool = False) -> str:
    """Rent, a mortgage or owned outright, for a home assembled now: their words first, else the odds for their age,
    pay and era. Someone sharing a place, or living aboard a ship or station, rents."""
    if aboard:
        return 'rent'
    told = said(definition)
    rng = random.Random(f'{seed}:tenure')
    age = age or 30
    outright = min(OUTRIGHT[band(age)] + ERA_OUTRIGHT.get(era, ERA_OUTRIGHT['other']), CEILING)
    if told == 'owns':
        return 'owned' if rng.random() < outright else 'mortgage'
    if told:
        return told
    owns = min(OWNS[band(age)] * TIER[min(max(tier, 0), 3)] * ERA.get(era, ERA['other']), CEILING)
    if shared or rng.random() >= owns:
        return 'rent'
    return 'owned' if rng.random() < outright else 'mortgage'


def payment(rent: float, seed: str) -> float:
    """A mortgage payment for a place that would rent for `rent`."""
    return rent * random.Random(f'{seed}:mortgage').uniform(*MORTGAGE)


# Saving for a place to live means nothing to someone who owns one: those goals become an owner's (money.goals).
HOUSING_GOALS = {'a deposit on a nicer place', 'a down payment fund', 'a down payment', 'a better flat',
                 'a down payment on a house', 'a better room'}
OWNER_GOALS = {'modern': ('a new roof', 'a kitchen remodel', 'a new water heater', 'a bathroom redo'),
               'jazz-age': ('a new furnace', 'a screened-in porch', 'a new roof', 'an electric icebox'),
               'other': ('a new roof', 'a proper garden wall', 'new windows', 'a second room built on')}


def owner_goals(options: list[str], era: str, seed: str) -> list[str]:
    swaps = OWNER_GOALS.get(era, OWNER_GOALS['other'])
    start = random.Random(f'{seed}:owner-goal').randrange(len(swaps))
    found, index = [], start
    for option in options:
        if option in HOUSING_GOALS:
            option, index = swaps[index % len(swaps)], index + 1
        found.append(option)
    return found
