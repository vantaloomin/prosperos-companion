"""Kitchen and food (Hit List #19): what the companion eats, cooks and runs out of.

A light pantry, not an inventory. Once per timeline, without a model, the companion gets a seeded way of eating from
who they are: a diet (most eat everything; some are vegetarian, vegan or pescatarian, always when their description
says so), things they avoid (an allergy or not eating pork, only from their description or the user), a cooking
skill (from can't really cook to a serious cook: a line cook or someone who loves cooking is a good one), whether they
love baking, and a few dishes they make a lot. Dishes come from banks per era and cuisine
(companion/world/data/kitchen/*.json, 110+ specific dishes each): their city decides which.

Each evening's meal is drawn, not stored: the same timeline, date, day and settings always give the same dinner, so
the agenda, the chat, the panel and the budget agree. A seeded weekly rhythm (cook, leftovers from a big batch,
takeout, keeping it simple) leans on their skill, how busy the day is (a long shift means takeout or something
quick), how they feel (a cold means something simple), what money is left this pay period (tight means cooking) and
the season. What their day already holds wins: a "cooked at home" entry is a cooking night, dinner out with a friend
or with the user is dinner out, and dinner at their place with the user (outings.py, `dinner-in`) is them cooking
for you. A few staples (coffee, eggs, milk; tea and bread in London; ale in Camelot) last a seeded number of days
after each grocery run and run out until the next one.

The Realism tab's kitchen slider (life_settings.kitchen_realism: 0 off, 1 light, 2 true to life, 3 dramatic) scales the
ups and downs: off, staples never run out and nothing goes wrong; light (I want an easy life) never runs out either
and a dinner rarely goes wrong; higher settings make staples run out sooner and now and then a dinner goes sideways
(and they order in instead).

Other modules read it through `touch` (the agenda), `context_lines` (the chat's "kitchen" section), `purchases`
(takeout counts as spending in money.household), `cooked` (Home upkeep's dishes), `grocery_runs` (Life admin's
Today), `hosting` (dinner at their place) and `invite_due` (they ask the user over). The user can change the diet,
what they avoid, the skill, baking and favourite dishes on the Character page; the days ahead follow.
"""
import json
import re
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

from companion.clock import stamp, zone
from companion.database import decode, encode, many, optional
from companion.errors import require
from companion.life import circle, money, routine
from companion.world import generators

COMPANION = 'companion'
BANKS = Path(__file__).resolve().parents[1] / 'world' / 'data' / 'kitchen'
DIETS = ('omnivore', 'pescatarian', 'vegetarian', 'vegan')
AVOIDS = ('nuts', 'shellfish', 'dairy', 'gluten', 'pork')
SKILLS = ("can't really cook", 'keeps it simple', 'a good home cook', 'a serious cook')
# The same, said to them in the chat's kitchen section.
YOUR_SKILLS = ("you can't really cook", 'you keep it simple', 'you are a good home cook', 'you are a serious cook')
# New dinners and grocery runs are woven into the companion's agenda entries, and now and then they ask the user over;
# tests turn these off.
WEAVE = True
INVITES = True

# Diets and things avoided named in who they are; first match wins for the diet.
DIET_WORDS = (('vegan', re.compile(r'\bvegan\b', re.I)),
              ('vegetarian', re.compile(r"\bvegetarian\b|\bdoesn'?t eat meat\b|\bno meat\b", re.I)),
              ('pescatarian', re.compile(r'\bpescatarian\b|\bpescetarian\b', re.I)))
AVOID_WORDS = {
    'nuts': re.compile(r'\b(?:peanut|nut|tree[- ]nut)s?\b[^.]{0,20}\ballerg|\ballerg\w*\b[^.]{0,30}\b(?:peanut|nut)s?\b',
                       re.I),
    'shellfish': re.compile(r'\bshellfish\b[^.]{0,20}\ballerg|\ballerg\w*\b[^.]{0,30}\bshellfish\b', re.I),
    'dairy': re.compile(r'\blactose\b|\bdairy[- ]free\b|\ballerg\w*\b[^.]{0,30}\b(?:dairy|milk)\b', re.I),
    'gluten': re.compile(r'\bcoeliac\b|\bceliac\b|\bgluten[- ]free\b|\bgluten intoleran', re.I),
    'pork': re.compile(r"\bhalal\b|\bkosher\b|\b(?:doesn'?t|does not|never) eat pork\b|\bno pork\b", re.I),
}
KOSHER = re.compile(r'\bkosher\b', re.I)
COOK_WORDS = ('cook', 'cooking', 'chef', 'foodie', 'recipe', 'kitchen', 'baker', 'baking', 'gourmet', 'culinary',
              'food')
NO_COOK = re.compile(r"\bcan'?t cook\b|\bcannot cook\b|\btakeout\b|\btake-out\b|\bmicrowave\b|\bburns? water\b", re.I)
BAKE_WORDS = ('bake', 'baking', 'baker', 'bakes', 'pastry', 'pastries', 'sourdough', 'cake', 'cakes')
COOK_CAREERS = ('line-cook', 'chef', 'cook', 'baker', 'caterer', 'pastry')
# Their skill by era: in the past nearly everyone cooked.
SKILL_ODDS = {True: (0.12, 0.33, 0.4, 0.15), False: (0.03, 0.3, 0.5, 0.17)}
DIET_ODDS = {True: (('vegan', 0.03), ('vegetarian', 0.08), ('pescatarian', 0.04)), False: ()}
ALLERGY_SHARE = 0.06

# A night's dinner, before what the day holds: weights by skill.
RHYTHM = {0: {'cook': 0.15, 'takeout': 0.45, 'simple': 0.4}, 1: {'cook': 0.45, 'takeout': 0.3, 'simple': 0.25},
          2: {'cook': 0.65, 'takeout': 0.2, 'simple': 0.15}, 3: {'cook': 0.78, 'takeout': 0.12, 'simple': 0.1}}
LEFTOVERS = 0.6
BAKE_SHARE = 0.3
# Ups and downs by the kitchen slider (off, light, true to life, dramatic): a dinner that goes sideways, and how long
# staples last (off and light, the easy life: never out).
MISHAP = (0.0, 0.02, 0.04, 0.1)
STAPLE_PACE = (None, None, 1.0, 0.75)
MISHAPS = ('the rice stuck to the bottom of the pot', 'the recipe took twice as long as it said',
           'they were out of a key ingredient halfway through', 'the sauce never came together',
           'they forgot the pot on the stove and it boiled dry', 'the dough refused to rise')
DINNER_AT = '19:00'
EVENING_OVER = 21  # the hour after which tonight's dinner reads as done on the panel
OUT_ACTIVITIES = {'dinner', 'birthday', 'own-birthday', 'gathering', 'tradition', 'drinks'}
EVENING = {'reading', 'slow', 'nap', 'chores', 'sick-day', 'home-cooking', 'groceries', None}
TAKEOUT_PRICES = ('takeout', 'pizza', 'cheap-lunch', 'lunch-counter', 'meal', 'inn-meal', 'eating-house',
                  'pie-and-peas', 'pie', 'chophouse')
TAKEOUT_SHARE = 0.006
MODERN = {'modern', 'future'}
# Nights are drawn in runs of four weeks from a fixed Monday, so no dish comes round twice within six nights.
RUN_FROM = date(2000, 1, 3)
RUN_DAYS = 28
# Other words a city's places use for a takeout cuisine, so a real place is named as often in every city.
CUISINE_WORDS = {'mexican': ('mexican', 'tex mex', 'tacos'), 'burgers': ('burger', 'diner'),
                 'chophouse': ('chop',), 'eel-pie': ('eel',), 'fried-fish': ('fried fish', 'fish and chips'),
                 'pie-shop': ('pie',), 'cookshop': ('cookshop', 'dining', 'dinners'), 'coffee-stall': ('coffee',)}
INVITE_EVERY = 14
RUNS_A_WEEK = 2
INVITE_CHANCE = 0.45
INVITE_AHEAD = (2, 5)


# --- Banks ---

@lru_cache(maxsize=16)
def bank(bank_id: str) -> dict:
    """One dish bank, with its dishes as {name, skill, tags} and takeout as {dish, cuisine, source, tags}."""
    raw = json.loads((BANKS / f'{bank_id}.json').read_text(encoding='utf-8'))
    return {'id': raw['id'], 'label': raw['label'], 'staples': raw['staples'],
            'dishes': tuple({'name': name, 'skill': skill, 'tags': frozenset(tags.split())}
                            for name, skill, tags in raw['dishes']),
            'takeout': tuple({'dish': dish, 'cuisine': cuisine, 'source': source, 'tags': frozenset(tags.split())}
                             for dish, cuisine, source, tags in raw['takeout'])}


COUNTRY_BANKS = (('modern-us', ('us', 'usa', 'united states', 'united states of america')),
                 ('modern-uk', ('uk', 'united kingdom', 'england', 'scotland', 'wales', 'britain')),
                 ('modern-japan', ('japan',)), ('modern-korea', ('korea', 'south korea')))
ERA_BANKS = {'jazz-age': 'jazz-age-us', 'victorian': 'victorian-uk', 'steampunk': 'victorian-uk',
             'edwardian': 'victorian-uk', 'medieval': 'medieval', 'frontier': 'frontier-us', 'western': 'frontier-us'}


def bank_for(data: dict | None) -> str:
    """The bank for the city's era and country: modern cities by country, past ones by era."""
    if not data:
        return 'modern-us'
    era, country = (data.get('era') or 'modern'), (data.get('country') or '').casefold()
    if era not in MODERN:
        return ERA_BANKS.get(era, 'old-world')
    return next((bank_id for bank_id, names in COUNTRY_BANKS
                 if country in names or any(len(name) > 3 and name in country for name in names)), 'modern-world')


def modern_bank(bank_id: str) -> bool:
    return bank_id.startswith('modern')


# --- Who they are in the kitchen ---

def words_of(definition: dict) -> str:
    parts = [definition.get(key) or '' for key in ('identity', 'personality', 'background', 'voice', 'routine')]
    return ' '.join([*parts, *definition.get('interests', ()), *definition.get('life_themes', ())])


def stems(text: str, wanted) -> int:
    words = {word.strip('.,;:!?()"\'').casefold() for word in text.split()}
    return sum(any(word == stem or len(stem) > 4 and word.startswith(stem) for word in words) for stem in wanted)


def career_id(definition: dict, data: dict | None) -> str:
    budget = money.profile(definition) if data else None
    if budget and budget.career:
        return budget.career['id']
    return (definition.get('money') or {}).get('career') or ''


def allowed(tags: frozenset, diet: str, avoids) -> bool:
    """Whether a dish fits their diet and what they avoid."""
    if diet == 'vegan' and 'vegan' not in tags:
        return False
    if diet == 'vegetarian' and not tags & {'vegan', 'veg'}:
        return False
    if diet == 'pescatarian' and not tags & {'vegan', 'veg', 'fish', 'shellfish'}:
        return False
    return not set(avoids) & tags


def profile(seed: str, definition: dict, data: dict | None) -> dict:
    """Their way of eating: the same for the same seed, definition and city."""
    bank_id = bank_for(data)
    era_modern = modern_bank(bank_id)
    text = words_of(definition)
    diet = next((name for name, pattern in DIET_WORDS if pattern.search(text)), None)
    if diet is None:
        roll, diet = generators.unit(seed, 'diet'), 'omnivore'
        for name, share in DIET_ODDS[era_modern]:
            if roll < share:
                diet = name
                break
            roll -= share
    avoids = [name for name, pattern in AVOID_WORDS.items() if pattern.search(text)]
    if KOSHER.search(text) and 'shellfish' not in avoids:
        avoids.append('shellfish')
    if not avoids and era_modern and generators.unit(seed, 'allergy') < ALLERGY_SHARE:
        avoids = [generators.pick(seed, 'allergy-kind', ['nuts', 'shellfish', 'dairy', 'gluten'], [4, 3, 2, 1])]
    career = career_id(definition, data)
    keen = stems(text, COOK_WORDS) + 2 * any(word in career for word in COOK_CAREERS)
    if NO_COOK.search(text) and keen < 2:
        skill = 0
    elif keen >= 2:
        skill = 3
    else:
        odds = SKILL_ODDS[era_modern]
        skill = generators.pick(seed, 'skill', [0, 1, 2, 3], list(odds))
        skill = min(3, skill + keen)
    bakes = stems(text, BAKE_WORDS) > 0 or 'baker' in career or generators.unit(seed, 'bakes') < 0.2
    found = {'bank': bank_id, 'diet': diet, 'avoids': avoids, 'skill': skill, 'bakes': bakes}
    found['favorites'] = favorites(seed, found)
    return found


def dishes_for(found: dict, *, skill: int | None = None, tag: str | None = None) -> list[dict]:
    """Dishes in their bank that fit their diet and what they avoid, up to a skill."""
    ceiling = max(1, found['skill'] if skill is None else skill)
    return [dish for dish in bank(found['bank'])['dishes'] if dish['skill'] <= ceiling
            and allowed(dish['tags'], found['diet'], found['avoids']) and (tag is None or tag in dish['tags'])]


def favorites(seed: str, found: dict) -> list[str]:
    """Two or three dishes they make a lot, leaning to ones good enough for company."""
    options = [dish for dish in dishes_for(found) if 'bake' not in dish['tags']]
    weights = [2.0 if 'treat' in dish['tags'] else 1.0 for dish in options]
    picked = []
    for index in range(3 if found['skill'] >= 2 else 2):
        dish = generators.pick(seed, f'favorite{index}', options, weights)
        if dish and dish['name'] not in picked:
            picked.append(dish['name'])
    return picked


# --- State ---

def ensure(connection, timeline_id: str, definition: dict, world, now) -> dict:
    """The timeline's kitchen state, seeding their way of eating the first time it is needed."""
    state = optional(connection, 'SELECT * FROM kitchen_state WHERE timeline_id=?', (timeline_id,))
    if state:
        return state
    seed = f'kitchen:{timeline_id}'
    found = profile(seed, definition, circle.city_data(definition, world))
    connection.execute('INSERT INTO kitchen_state (timeline_id, seed, profile, overrides, created_at, updated_at) '
                       "VALUES (?, ?, ?, '{}', ?, ?)", (timeline_id, seed, encode(found), stamp(now), stamp(now)))
    return optional(connection, 'SELECT * FROM kitchen_state WHERE timeline_id=?', (timeline_id,))


def settled(state: dict) -> dict:
    """Their way of eating with the user's changes on top."""
    return {**decode(state['profile']), **decode(state['overrides'] or '{}')}


def realism(connection) -> int:
    row = optional(connection, 'SELECT kitchen_realism FROM life_settings WHERE id=1')
    return row['kitchen_realism'] if row and row['kitchen_realism'] is not None else 2


# --- One day ---

class Day:
    """What a day's dinner draws on, read once: their state, schedule, budget, weather and what the day holds."""

    def __init__(self, connection, timeline_id: str, definition: dict, world, state: dict):
        if world is None:
            from companion.world.source import CatalogWorld
            world = CatalogWorld()
        self.connection, self.timeline_id, self.definition, self.world = connection, timeline_id, definition, world
        self.memo: dict = {}
        self.seed, self.found = state['seed'], settled(state)
        self.level = realism(connection)
        self.schedule = routine.blocks(definition)[0]
        self.budget = money.profile(definition)
        self.data = circle.city_data(definition, world)
        row = optional(connection, 'SELECT companion_id FROM timelines WHERE id=?', (timeline_id,))
        self.companion_id = row['companion_id'] if row else None

    # What the day holds

    def remember(self, key, make):
        if key not in self.memo:
            self.memo[key] = make()
        return self.memo[key]

    def entries(self, day: date) -> list[dict]:
        return self.remember(('entries', day), lambda: self.read_entries(day))

    def read_entries(self, day: date) -> list[dict]:
        rows = many(self.connection, 'SELECT block, entry FROM life_agenda WHERE timeline_id=? AND subject=? AND '
                    'local_date=? ORDER BY starts_at', (self.timeline_id, COMPANION, day.isoformat()))
        return [{**(decode(row['entry']) if row['entry'] else {}), '_block': decode(row['block'])} for row in rows]

    def outing(self, day: date) -> dict | None:
        """Dinner with the user that day: out, or at their place."""
        from companion.life import outings
        for outing in outings.in_force(self.connection, self.timeline_id, day.isoformat()):
            if outing['local_date'] == day.isoformat() and outing['activity'] in ('dinner', 'dinner-in'):
                return outing
        return None

    def away(self, day: date) -> bool:
        from companion.life import trips
        return self.remember(('away', day), lambda: bool(self.companion_id) and trips.away_on(
            self.connection, self.companion_id, day))

    def work_hours(self, day: date) -> float:
        total = 0.0
        for block in self.schedule:
            if block.on(day) and block.kind in ('work', 'study'):
                start = block.start.hour + block.start.minute / 60
                end = block.end.hour + block.end.minute / 60
                total += end - start if end > start else end + 24 - start
        return total

    def late(self, day: date) -> bool:
        return any(block.on(day) and block.kind == 'work' and
                   (block.end.hour >= 18 or block.end < block.start) for block in self.schedule)

    def weather(self, day: date) -> dict | None:
        from companion.life import composer
        return self.remember(('weather', day), lambda: composer.weather(self.world, self.definition, day.isoformat()))

    def sick(self, day: date) -> bool:
        from companion.life import body
        return self.remember(('sick', day), lambda: body.sick(f'{self.timeline_id}:{COMPANION}', day, self.world, self.definition))

    def tight(self, day: date) -> bool | None:
        if not self.budget:
            return None
        left = money.left_on(self.budget, day)
        return left < self.budget.fun_cycle * money.TIGHT

    # The rhythm

    def base(self, day: date) -> str:
        """The night's seeded kind before what the day holds: 'cook', 'takeout' or 'simple'."""
        weights = dict(RHYTHM[self.found['skill']])
        hours = self.work_hours(day)
        if hours >= 8 or self.late(day):
            weights['takeout'] *= 1.6
            weights['simple'] *= 1.3
            weights['cook'] *= 0.7
        elif hours == 0:
            weights['cook'] *= 1.25
        if not modern_bank(self.found['bank']):
            weights['takeout'] *= 0.6
        tight = self.tight(day)
        if tight:
            weights['takeout'] *= 0.25
        elif tight is False and self.budget.style == 'spender':
            weights['takeout'] *= 1.25
        elif tight is False and self.budget.style == 'careful':
            weights['takeout'] *= 0.7
        if self.sick(day):
            weights = {'cook': 0.05, 'takeout': weights['takeout'] + 0.3, 'simple': 0.65}
        keys = list(weights)
        return generators.pick(self.seed, f'night:{day.isoformat()}', keys, [weights[key] for key in keys])

    def dish(self, day: date, label: str = 'dish', exclude=()) -> dict | None:
        """The night's dish: their season, a busy day's quick one, a day off's batch or treat, and favourites."""
        return self.remember(('dish', day, label, frozenset(exclude)), lambda: self.pick_dish(day, label, exclude))

    def own_dishes(self) -> list[dict]:
        """Favourites the user wrote that the bank does not have: cooked as they are, good enough for company."""
        known = {dish['name'] for dish in bank(self.found['bank'])['dishes']}
        return [{'name': name, 'skill': 1, 'tags': frozenset({'treat'})}
                for name in self.found.get('favorites') or () if name not in known]

    def pick_dish(self, day: date, label: str, exclude) -> dict | None:
        options = [dish for dish in [*dishes_for(self.found), *self.own_dishes()] if 'bake' not in dish['tags'] and
                   dish['name'] not in exclude]
        conditions = self.weather(day) or {}
        high = conditions.get('high_f')
        busy, off = self.work_hours(day) >= 8 or self.late(day), self.work_hours(day) == 0
        favourite = set(self.found.get('favorites') or ())

        def weight(dish: dict) -> float:
            tags, value = dish['tags'], 1.0
            if high is not None and high < 55:
                value *= 2.0 if 'warm' in tags else 0.3 if 'cold' in tags else 1.0
            elif high is not None and high > 78:
                value *= 2.0 if 'cold' in tags else 0.4 if 'warm' in tags else 1.0
            if busy:
                value *= 3.0 if 'quick' in tags else 0.5 if 'big' in tags else 1.0
            if off:
                value *= 1.5 if tags & {'big', 'treat'} else 0.7 if 'quick' in tags else 1.0
            if dish['skill'] == self.found['skill'] or self.found['skill'] == 0 and dish['skill'] == 1:
                value *= 1.5
            return value * (4.0 if dish['name'] in favourite else 1.0)

        return generators.pick(self.seed, f'{label}:{day.isoformat()}', options, [weight(dish) for dish in options])

    def recent_dishes(self, day: date) -> frozenset[str]:
        """What they ate the six nights before (cooked, simple, leftovers or ordered in), so a dish does not come
        round again within a week. Nights are worked out in four-week runs from a fixed date, so a day never needs
        more than the run it is in: before the run starts, the night's plain pick stands in."""
        return self.remember(('recent', day), lambda: frozenset(self.eaten_before(day)))

    def eaten_before(self, day: date) -> set[str]:
        start, names = run_start(day), set()
        for back in range(1, 7):
            earlier = day - timedelta(days=back)
            if earlier >= start:
                names |= eaten(self.meal(earlier))
            else:
                names |= {item['name'] for item in (self.dish(earlier), self.simple(earlier, False)) if item}
                names |= {(self.takeout(earlier, fresh=False) or {}).get('dish')} - {None}
        return names

    def simple(self, day: date, fresh: bool = True) -> dict | None:
        """Something quick and easy (soup and toast when they are ill), not the same as the last few simple nights."""
        return self.remember(('simple', day, fresh), lambda: self.pick_simple(day, fresh))

    def pick_simple(self, day: date, fresh: bool) -> dict | None:
        options = [dish for dish in dishes_for(self.found, skill=1) if 'bake' not in dish['tags'] and
                   ('quick' in dish['tags'] or self.sick(day) and 'warm' in dish['tags'])]
        if fresh:
            recent = self.recent_dishes(day)
            options = [dish for dish in options if dish['name'] not in recent] or options
        return generators.pick(self.seed, f'simple:{day.isoformat()}', options or dishes_for(self.found, skill=1))

    def takeout(self, day: date, label: str = 'takeout', fresh: bool = True) -> dict | None:
        """What they order and where from: a real restaurant in their city with that cuisine when there is one."""
        options = [item for item in bank(self.found['bank'])['takeout']
                   if allowed(item['tags'], self.found['diet'], self.found['avoids'])]
        if label == 'takeout' and fresh:
            recent = self.recent_dishes(day)
            options = [item for item in options if item['dish'] not in recent] or options
        item = generators.pick(self.seed, f'{label}:{day.isoformat()}', options)
        if not item:
            return None
        place = self.restaurant(item['cuisine'], f'{label}:{day.isoformat()}')
        return {'dish': item['dish'], 'source': place['name'] if place else item['source'], 'cuisine': item['cuisine'],
                'place': {'id': place['id'], 'name': place['name']} if place else None}

    def restaurant(self, cuisine: str, label: str) -> dict | None:
        if not self.data:
            return None
        words = CUISINE_WORDS.get(cuisine, (cuisine.replace('-', ' '),))
        places = [place for place in self.data.get('places', ()) if place.get('kind') in
                  ('restaurant', 'cafe', 'tavern', 'inn', 'market') and place.get('cost', '$') in ('', '$', '$$') and
                  any(word in ' '.join([place.get('cuisine', ''), *place.get('tags', ())]).replace('-', ' ').casefold()
                      for word in words)]
        return generators.pick(self.seed, f'{label}:place', places)

    def bake(self, day: date) -> dict | None:
        if not self.found.get('bakes') or self.work_hours(day) >= 8:
            return None
        if generators.unit(self.seed, 'bake?', day.isoformat()) >= BAKE_SHARE * (1.6 if self.work_hours(day) == 0
                                                                                 else 0.5):
            return None
        return generators.pick(self.seed, f'bake:{day.isoformat()}', self.bakes())

    def bakes(self) -> list[dict]:
        """Baking projects beside dinner: bread, cakes and sweets, not a savoury pie that would be dinner itself."""
        return [dish for dish in dishes_for(self.found, skill=max(2, self.found['skill']), tag='bake')
                if dish['tags'] & {'vegan', 'veg'}]

    def mishap(self, day: date) -> str | None:
        if generators.unit(self.seed, 'mishap?', day.isoformat()) >= MISHAP[self.level]:
            return None
        return generators.pick(self.seed, f'mishap:{day.isoformat()}', list(MISHAPS))

    def cost(self) -> float:
        """One takeout dinner in the city's money, from its prices."""
        if not self.budget:
            return 0.0
        city = self.budget.city
        dinner = money.price(city, ('dinner', 'dinner-out'))
        unit = dinner * 0.6 if dinner else money.price(city, TAKEOUT_PRICES)
        if unit is None:
            unit = money.monthly_share(self.budget) * TAKEOUT_SHARE
        return round(unit, 2)

    # The meal

    def meal(self, day: date) -> dict:
        """The evening meal on this local date."""
        return self.remember(('meal', day), lambda: self.draw_meal(day))

    def draw_meal(self, day: date) -> dict:
        result = {'date': day.isoformat(), 'kind': 'cook', 'dish': None, 'takeout': None, 'bake': None, 'mishap': None,
                  'with_user': False, 'place': None, 'cost': 0.0, 'groceries': self.grocery_day(day)}
        held = self.held(day)
        if held:
            return {**result, **held}
        cooked = any(entry.get('activity') == 'home-cooking' for entry in self.entries(day))
        kind = 'cook' if cooked else self.base(day)
        if not cooked and kind != 'takeout' and (yesterday := self.leftovers_from(day)):
            if generators.unit(self.seed, 'leftovers?', day.isoformat()) < LEFTOVERS:
                return {**result, 'kind': 'leftovers', 'dish': yesterday}
        if kind == 'cook':
            kind = self.cooking(day, result, cooked)
        if kind == 'simple':
            dish = self.simple(day)
            result.update(kind='simple', dish=dish['name'] if dish else None)
        if kind == 'takeout':
            result.update(kind='takeout', takeout=self.takeout(day), cost=self.cost(), bake=None)
            if not result['takeout']:
                result['kind'] = 'simple'
        return result

    def held(self, day: date) -> dict | None:
        """What the day already holds for dinner: away, the user over, or dinner out (with the user or not)."""
        if self.away(day):
            return {'kind': 'away', 'groceries': False}
        outing = self.outing(day)
        if outing and outing['activity'] == 'dinner-in':
            menu = (outing['place'] or {}).get('menu') or self.hosted(day, outing)
            return {**menu, 'kind': 'hosting', 'with_user': True}
        if outing:
            return {'kind': 'out', 'with_user': True, 'place': outing['place']['name']}
        out = next((entry for entry in self.entries(day) if entry.get('activity') in OUT_ACTIVITIES and
                    entry['_block'].get('start', '00:00') >= '16:00'), None)
        return {'kind': 'out', 'place': (out.get('place') or {}).get('name')} if out else None

    def cooking(self, day: date, result: dict, cooked: bool) -> str:
        """A cooking night's dish and maybe baking; now and then it goes sideways and they order in."""
        dish = self.dish(day, exclude=self.recent_dishes(day)) or self.dish(day)
        result.update(kind='cook', dish=dish['name'] if dish else None, bake=(self.bake(day) or {}).get('name'))
        if (mishap := self.mishap(day)) and not cooked:
            result['mishap'] = mishap
            if generators.unit(self.seed, 'rescue', day.isoformat()) < 0.5:
                return 'takeout'
        return 'cook'

    def leftovers_from(self, day: date) -> str | None:
        """Yesterday's dish when it was a big batch they cooked. Yesterday's actual dinner, so leftovers follow a
        cooking night and never a night of leftovers or takeout; on the first night of a run (`recent_dishes`) the
        plain rhythm stands in."""
        yesterday = day - timedelta(days=1)
        if yesterday < run_start(day):
            if self.away(yesterday) or self.base(yesterday) != 'cook':
                return None
            dish = self.dish(yesterday)
            return dish['name'] if dish and 'big' in dish['tags'] else None
        meal = self.meal(yesterday)
        if meal['kind'] != 'cook' or not meal['dish']:
            return None
        return meal['dish'] if 'big' in self.tags_of(meal['dish']) else None

    def tags_of(self, name: str) -> frozenset:
        return next((dish['tags'] for dish in bank(self.found['bank'])['dishes'] if dish['name'] == name), frozenset())

    def hosted(self, day: date, outing: dict | None = None) -> dict:
        """What they cook when the user comes over: a dish for company within their skill (a favourite when it is
        one), dessert when they bake; someone who can't cook orders in and sets the table."""
        label = f"hosting:{outing['id']}" if outing else 'hosting'
        if self.found['skill'] == 0:
            return {'takeout': self.takeout(day, label), 'dish': None, 'bake': None}
        options = [dish for dish in [*dishes_for(self.found), *self.own_dishes()] if 'treat' in dish['tags'] and
                   'bake' not in dish['tags']]
        favourite = set(self.found.get('favorites') or ())
        dish = generators.pick(self.seed, f'{label}:dish', options, [4.0 if item['name'] in favourite else 1.0
                                                                      for item in options]) or self.dish(day)
        bake = None
        if self.found.get('bakes'):
            bake = generators.pick(self.seed, f'{label}:dessert', self.bakes())
        return {'dish': dish['name'] if dish else None, 'bake': bake['name'] if bake else None, 'takeout': None}

    # Groceries and staples

    def grocery_day(self, day: date) -> bool:
        """A run is seeded once or twice a week on lighter days, or it is in the day's own agenda."""
        return self.remember(('grocery', day), lambda: self.shops(day))

    def shops(self, day: date) -> bool:
        monday = day - timedelta(days=day.weekday())
        return day in self.remember(('runs', monday), lambda: self.week_runs(monday))

    def week_runs(self, monday: date) -> set[date]:
        """At most two runs a week: the days their agenda has them shopping first, then the seeded ones."""
        days = [monday + timedelta(days=offset) for offset in range(7)]
        shopping = [day for day in days if not self.away(day)
                    and any(entry.get('activity') == 'groceries' for entry in self.entries(day))]
        seeded = sorted(day for day in self.planned_runs(monday) if not self.away(day) and day not in shopping)
        return set((shopping + seeded)[:RUNS_A_WEEK])

    def planned_runs(self, day: date) -> set[date]:
        monday = day - timedelta(days=day.weekday())
        week = monday.isoformat()
        days = [monday + timedelta(days=offset) for offset in range(7)]
        weights = [3.0 if self.work_hours(item) == 0 else 0.6 if self.work_hours(item) >= 8 else 1.0 for item in days]
        first = generators.pick(self.seed, f'run1:{week}', days, weights)
        runs = {first}
        if generators.unit(self.seed, 'run2?', week) < 0.45:
            later = [item for item in days if abs((item - first).days) >= 3]
            if later:
                runs.add(generators.pick(self.seed, f'run2:{week}', later))
        return runs

    def last_run(self, day: date, limit: int = 35) -> date | None:
        for back in range(limit):
            candidate = day - timedelta(days=back)
            if self.grocery_day(candidate):
                return candidate
        return None

    def staples(self) -> list[dict]:
        """The bank's staples their diet keeps: a vegan buys the swap, or goes without."""
        result = []
        for staple in bank(self.found['bank'])['staples']:
            tags = set(staple.get('tags', '').split())
            avoided = self.found['diet'] == 'vegan' and 'vegan' not in tags or tags & set(self.found['avoids'])
            if avoided and staple.get('swap'):
                result.append({**staple, 'name': staple['swap'], 'tags': 'vegan'})
            elif not avoided:
                result.append(staple)
        return result

    def pantry(self, day: date) -> list[dict]:
        """Each staple on this day: {name, state ('stocked', 'low', 'out'), since, days_left}. On the easy setting
        nothing runs out."""
        pace = STAPLE_PACE[self.level]
        run = self.last_run(day)
        result = []
        for staple in self.staples():
            if pace is None or run is None:
                result.append({'name': staple['name'], 'state': 'stocked', 'since': None, 'days_left': None})
                continue
            stretch = 0.7 + 0.6 * generators.unit(self.seed, 'lasts', staple['name'], run.isoformat())
            lasts = max(2, round(staple.get('days', 7) * stretch * pace))
            empty = run + timedelta(days=lasts)
            left = (empty - day).days
            state = 'out' if left <= 0 else 'low' if left == 1 else 'stocked'
            result.append({'name': staple['name'], 'state': state, 'since': empty.isoformat() if state == 'out' else
                           None, 'days_left': max(left, 0)})
        return result

    def restocked(self, day: date) -> list[str]:
        """Staples a grocery run on this day brings back: the ones out or nearly out the day before."""
        if not self.grocery_day(day):
            return []
        return [item['name'] for item in self.pantry(day - timedelta(days=1)) if item['state'] != 'stocked']


def run_start(day: date) -> date:
    """The first night of the four-week run a night belongs to (see `Day.recent_dishes`)."""
    return day - timedelta(days=(day - RUN_FROM).days % RUN_DAYS)


def eaten(meal: dict) -> set[str]:
    """The dishes a night's dinner was."""
    return {name for name in (meal.get('dish'), (meal.get('takeout') or {}).get('dish')) if name}


def run_label(bank_id: str) -> str:
    """What a shopping trip is called: a grocery run now, food shopping from the 1880s to the 1920s, and market day
    in medieval and older-world towns."""
    if modern_bank(bank_id):
        return 'Grocery run'
    return 'Market day' if bank_id in ('medieval', 'old-world') else 'Food shopping'


def day_for(connection, timeline_id: str, definition: dict, world, now) -> Day:
    return Day(connection, timeline_id, definition, world, ensure(connection, timeline_id, definition, world, now))


# --- Words ---

def listing(names: list[str]) -> str:
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}" if names else ''


def ordered(item: dict, era_modern: bool) -> str:
    verb = 'ordered' if era_modern else 'picked up'
    return f"{verb} {item['dish']} from {item['source']}"


def meal_text(meal: dict, era_modern: bool = True) -> str:
    """'made black bean chili', 'had leftover lasagna', 'ordered pad thai from Thai Landing': past tense, no
    subject; '' for a day away."""
    kind = meal['kind']
    if kind == 'away':
        return ''
    if kind == 'hosting':
        what = ordered(meal['takeout'], era_modern) if meal.get('takeout') else f"cooked {meal['dish']}"
        text = f'{what} for you at their place'
    elif kind == 'out':
        text = f"had dinner out{' at ' + meal['place'] if meal.get('place') else ''}" + \
            (' with you' if meal.get('with_user') else '')
    elif kind == 'leftovers':
        text = f"had leftover {meal['dish']}"
    elif kind == 'takeout':
        text = ordered(meal['takeout'], era_modern)
        if meal.get('mishap'):
            text = f"gave up on cooking when {meal['mishap']} and {text}"
    elif kind == 'simple':
        text = f"kept dinner simple with {meal['dish']}"
    else:
        text = f"made {meal['dish']}"
        if meal.get('mishap'):
            text += f", though {meal['mishap']}"
    if meal.get('bake') and kind in ('cook', 'hosting'):
        text += f", and baked {meal['bake']}" if kind == 'cook' else f", with {meal['bake']} for dessert"
    return text


def plan_text(meal: dict, era_modern: bool = True) -> str:
    """The same meal as a plan for later today: 'making black bean chili'."""
    swaps = (('made ', 'making '), ('had leftover ', 'having leftover '), ('ordered ', 'ordering '),
             ('picked up ', 'picking up '), ('kept dinner simple', 'keeping dinner simple'),
             ('had dinner out', 'having dinner out'), ('cooked ', 'cooking '), ('and baked ', 'and baking '))
    text = meal_text({**meal, 'mishap': None}, era_modern)
    for old, new in swaps:
        text = text.replace(old, new, 1) if text.startswith(old) or old.startswith('and') else text
    return text


def dinner_text(meal: dict) -> str:
    """Tonight's dinner as the chat context says it all day long: 'black bean chili, which you are cooking'."""
    kind = meal['kind']
    if kind == 'hosting':
        if meal.get('takeout'):
            return f"{meal['takeout']['dish']} from {meal['takeout']['source']}, with the user at your place"
        dessert = f", with {meal['bake']} for dessert" if meal.get('bake') else ''
        return f"{meal['dish']}, which you are cooking for the user at your place{dessert}"
    if kind == 'out':
        return f"out{' at ' + meal['place'] if meal.get('place') else ''}" + (' with the user' if meal.get('with_user')
                                                                               else '')
    if kind == 'leftovers':
        return f"leftover {meal['dish']}"
    if kind == 'takeout':
        return f"takeout, {meal['takeout']['dish']} from {meal['takeout']['source']}"
    if kind == 'simple':
        return f"something simple, {meal['dish']}"
    baking = f"; you are also baking {meal['bake']}" if meal.get('bake') else ''
    return f"{meal['dish']}, which you are cooking{baking}"


def skill_text(found: dict) -> str:
    return SKILLS[found['skill']]


def diet_text(found: dict, person: str = 'they') -> str:
    """'eat everything', 'are vegetarian and allergic to nuts'."""
    verb, be = ('eat', 'are') if person in ('they', 'you') else ('eats', 'is')
    parts = [f'{verb} everything' if found['diet'] == 'omnivore' else f"{be} {found['diet']}"]
    allergies = [name for name in found['avoids'] if name in ('nuts', 'shellfish', 'dairy', 'gluten')]
    if allergies:
        parts.append(f"{'avoid' if person in ('they', 'you') else 'avoids'} {listing(allergies)}")
    if 'pork' in found['avoids']:
        parts.append(f"{'don’t' if person in ('they', 'you') else 'doesn’t'} eat pork")
    return listing(parts)


def pantry_text(pantry: list[dict]) -> str:
    """'Out of eggs since Tuesday; coffee is running low.' or ''."""
    out = [item for item in pantry if item['state'] == 'out']
    low = [item['name'] for item in pantry if item['state'] == 'low']
    parts = []
    if out:
        since = min(item['since'] for item in out)
        parts.append(f"Out of {listing([item['name'] for item in out])} since {date.fromisoformat(since):%A}")
    if low:
        parts.append(f"{listing(low)} {'is' if len(low) == 1 else 'are'} running low")
    text = '; '.join(parts)
    return text[:1].upper() + text[1:] + '.' if text else ''


# --- Agenda ---

def touch(connection, timeline_id: str, subject: str, entry: dict | None, block: dict, local_date: str,
          definition: dict, world, now) -> dict | None:
    """The companion's agenda entry with the kitchen woven in, once a day each: the dish on a cooking night, what a
    grocery run brought back, and dinner on the evening at home that holds dinner time."""
    if subject != COMPANION or not entry or entry.get('kitchen') or not WEAVE:
        return entry
    day = date.fromisoformat(local_date)
    found = day_for(connection, timeline_id, definition, world, now)
    era_modern = modern_bank(found.found['bank'])
    name = definition['name']
    activity = entry.get('activity')
    if activity == 'groceries':
        back = found.restocked(day)
        if back:
            return woven(entry, f"{name} restocked {listing(back)}.", {'groceries': back})
        return {**entry, 'kitchen': {'groceries': []}}
    if activity == 'home-cooking':
        return cooked_entry(found, entry, day, name)
    if activity not in EVENING or told(connection, timeline_id, day):
        return entry
    meal = found.meal(day)
    if meal['kind'] in ('away', 'out', 'hosting') or not holds_dinner(entry, block):
        return entry
    return woven(entry, f"{name} {meal_text(meal, era_modern)}.", {'meal': meal['kind']})


def cooked_entry(found: Day, entry: dict, day: date, name: str) -> dict:
    """A cooking slot names the dish: that night's dinner when they cook it, else another from their bank."""
    meal = found.meal(day)
    dish = meal['dish'] if meal['kind'] == 'cook' and meal.get('dish') else \
        (found.dish(day, exclude=found.recent_dishes(day)) or found.dish(day) or {}).get('name')
    if not dish:
        return entry
    _first, _, rest = entry['summary'].partition('. ')
    summary = f"{name} cooked {dish} at home." + (f' {rest}' if rest else '')
    return {**entry, 'summary': summary, 'kitchen': {'dish': dish}}


def holds_dinner(entry: dict, block: dict) -> bool:
    start, end = block.get('start') or '', block.get('end') or ''
    return bool(start) and start <= DINNER_AT and (end > DINNER_AT or end < start)


def woven(entry: dict, sentence: str, details: dict) -> dict:
    sentence = sentence[0].upper() + sentence[1:]
    return {**entry, 'summary': f"{entry['summary'].rstrip()} {sentence}", 'kitchen': {**details, 'sentence': sentence}}


def told(connection, timeline_id: str, day: date) -> bool:
    return bool(optional(connection, "SELECT id FROM life_agenda WHERE timeline_id=? AND subject=? AND local_date=? "
                         "AND (json_extract(entry, '$.kitchen.meal') IS NOT NULL "
                         "OR json_extract(entry, '$.kitchen.dish') IS NOT NULL)",
                         (timeline_id, COMPANION, day.isoformat())))


# --- Chat ---

def context_lines(connection, timeline_id: str, definition: dict, world, now, timezone: str) -> list[tuple[str, str]]:
    """(identity, line) pairs for the chat's kitchen section: how they cook and eat, last night's and tonight's
    dinner, and anything out in the kitchen."""
    state = optional(connection, 'SELECT * FROM kitchen_state WHERE timeline_id=?', (timeline_id,))
    if not state:
        return []
    found = Day(connection, timeline_id, definition, world, state)
    local = now.astimezone(zone(timezone))
    today, era_modern = local.date(), modern_bank(found.found['bank'])
    me = found.found
    baking = ' and you love baking' if me.get('bakes') else ''
    lines = [(f'kitchen:{timeline_id}:you', f"- In the kitchen {YOUR_SKILLS[me['skill']]}{baking}; you "
                                            f"{diet_text(me, 'you')}.")]
    if me.get('favorites'):
        lines.append((f'kitchen:{timeline_id}:favorites', f"- Dishes you make a lot: {listing(me['favorites'])}."))
    yesterday = found.meal(today - timedelta(days=1))
    if text := meal_text(yesterday, era_modern):
        lines.append((f'kitchen:{timeline_id}:{yesterday["date"]}', f"- Last night you {you(text)}."))
    tonight = found.meal(today)
    if tonight['kind'] != 'away':
        lines.append((f"kitchen:{timeline_id}:{tonight['date']}", f'- Dinner tonight: {dinner_text(tonight)}.'))
    if pantry := pantry_text(found.pantry(today)):
        lines.append((f'kitchen:{timeline_id}:pantry:{today.isoformat()}', f'- At home: {pantry}'))
    return lines


def you(text: str) -> str:
    return text.replace(' for you at their place', ' for the user at your place').replace(' with you', ' with the user')


# --- For other modules ---

def cooked(connection, timeline_id: str, day: date, definition: dict, world, now) -> int:
    """Meals cooked at home that local day (Home upkeep's dishes): see `cooked_on`."""
    return cooked_on(day_for(connection, timeline_id, definition, world, now), day)


def peek(connection, timeline_id: str, definition: dict, world=None) -> Day:
    """Their kitchen for reading only: the stored state, or the one `ensure` would seed, without writing it."""
    state = optional(connection, 'SELECT * FROM kitchen_state WHERE timeline_id=?', (timeline_id,))
    if not state:
        seed = f'kitchen:{timeline_id}'
        state = {'timeline_id': timeline_id, 'seed': seed, 'overrides': '{}',
                 'profile': encode(profile(seed, definition, circle.city_data(definition, world)))}
    return Day(connection, timeline_id, definition, world, state)


def cooked_on(found: Day, day: date) -> int:
    """0 to 2: a cooked dinner 1 (2 with baking), leftovers or a simple dinner 1, cooking for the user at their place
    2, takeout, eating out or away 0."""
    meal = found.meal(day)
    if meal['kind'] == 'hosting':
        return 1 if meal.get('takeout') else 2
    if meal['kind'] == 'cook':
        return 1 + bool(meal.get('bake'))
    return 1 if meal['kind'] in ('leftovers', 'simple') else 0


def grocery_runs(connection, timeline_id: str, start: date, end: date, definition: dict, world, now) -> list[dict]:
    """Grocery runs between two local dates inclusive, for Life admin's Today: {date, text, staples}."""
    found = day_for(connection, timeline_id, definition, world, now)
    result, day, label = [], start, run_label(found.found['bank'])
    while day <= end:
        if found.grocery_day(day):
            back = found.restocked(day)
            text = f"{label} (out of {listing(back)})" if back else label
            result.append({'date': day.isoformat(), 'text': text, 'staples': back})
        day += timedelta(days=1)
    return result


def purchases(connection, timeline_id: str, start: date, end: date, definition: dict, world, now) -> list[dict]:
    """Takeout this pay period, as one money.household purchase with its own cost: {text, date, spend, cost, for}."""
    if not optional(connection, 'SELECT seed FROM kitchen_state WHERE timeline_id=?', (timeline_id,)):
        return []
    found = day_for(connection, timeline_id, definition, world, now)
    nights, day = [], start
    while day <= end:
        meal = found.meal(day)
        if meal['kind'] == 'takeout' and meal['cost']:
            nights.append(meal)
        day += timedelta(days=1)
    if not nights:
        return []
    what = listing(list(dict.fromkeys(meal['takeout']['dish'] for meal in nights))[:3])
    times = 'once' if len(nights) == 1 else 'twice' if len(nights) == 2 else f'{len(nights)} times'
    return [{'text': f'ordered takeout {times} ({what})', 'date': nights[-1]['date'], 'spend': '',
             'cost': round(sum(meal['cost'] for meal in nights), 2), 'for': 'food'}]


def hosting(connection, timeline_id: str, definition: dict, world, now, day: date, outing: dict | None = None) -> dict:
    """What they make when the user comes over on this day: {dish, bake, takeout}."""
    return day_for(connection, timeline_id, definition, world, now).hosted(day, outing)


def hosting_text(menu: dict, era_modern: bool = True) -> str:
    """'You are cooking mushroom risotto, with lemon bars for dessert.'"""
    if menu.get('takeout'):
        return f"You {ordered(menu['takeout'], era_modern)} and set the table."
    text = f"You are cooking {menu['dish']}" if menu.get('dish') else 'You are cooking'
    return text + (f", with {menu['bake']} for dessert." if menu.get('bake') else '.')


# --- Inviting the user over ---

def planned_menu(menu: dict, era_modern: bool = True) -> str:
    """The menu for a dinner still ahead: 'You plan to cook mushroom risotto, with lemon bars for dessert.' or 'You plan
    to order pad thai from Thai Landing and set the table.'"""
    if menu.get('takeout'):
        item, verb = menu['takeout'], 'order' if era_modern else 'pick up'
        return f"You plan to {verb} {item['dish']} from {item['source']} and set the table."
    return hosting_text(menu, era_modern).replace('You are cooking', 'You plan to cook')


def invite_due(connection, companion: dict, now: datetime) -> list:
    """Now and then, a first text asking the user over for dinner on a free evening a few days off, with what they
    will make (companion/life/openers.py). Saving the text settles the plan (`settle_invite`)."""
    from companion.life import outings
    from companion.life.openers import Trigger
    version = companion['version']
    definition, timeline_id = version['definition'], companion['active_timeline_id']
    local = now.astimezone(zone(version['timezone']))
    if not INVITES or not 10 <= local.hour < 21:
        return []
    state = optional(connection, 'SELECT * FROM kitchen_state WHERE timeline_id=?', (timeline_id,))
    if not state:
        return []
    window = local.date().toordinal() // INVITE_EVERY
    if generators.unit(state['seed'], 'invite?', window) >= INVITE_CHANCE:
        return []
    key = f'dinner-invite:{timeline_id}:{window}'
    schedule = routine.blocks(definition)[0]
    for ahead in range(*INVITE_AHEAD):
        day = local.date() + timedelta(days=ahead)
        if outings.busy_at(schedule, day, DINNER_AT) or outings.cut_short(schedule, day, DINNER_AT, '22:00') or \
                outings.taken(connection, companion, day):
            continue
        menu = hosting(connection, timeline_id, definition, None, now, day)
        era_modern = modern_bank(settled(state)['bank'])
        dish = menu['dish'] or (menu['takeout'] or {}).get('dish') or 'dinner'
        when = f'{day:%A}'
        what = f"I'll make {dish}" if menu['dish'] else f"I'll get {dish} from {menu['takeout']['source']}"
        reason = (f'You want to have the user over for dinner at your place on {day:%A, %B} {day.day} at 7 PM. '
                  f'{planned_menu(menu, era_modern)} '
                  f"Invite them in your own words, naming the day and what you will {'make' if menu['dish'] else 'get'}.")
        return [Trigger(key, 'dinner_invite', reason, f'Come over for dinner {when}? {what}.',
                        (day.isoformat(),))]
    return []


def settle_invite(connection, companion: dict, message: dict, trigger, timestamp: str) -> dict | None:
    """The invitation a first text made, as a dinner-in plan on its day (the user can call it off on Today)."""
    from companion.life import outings
    day = date.fromisoformat(trigger.sources[0])
    wanted = {'activity': 'dinner-in', 'day': day, 'at': DINNER_AT, 'place': None, 'word': '', 'waterside': False}
    return outings.save(connection, companion, message, wanted, outings.city_data(
        connection, companion['version']['definition']), day, DINNER_AT, timestamp)


# --- View and edits ---

def view(connection, timeline_id: str, definition: dict, world, now, timezone: str, show_odds: bool = False) -> dict:
    """The Character page's Kitchen panel: their way of eating, the last week of dinners and tonight's, and the
    pantry, in words; the numbers only when hidden values are shown."""
    state = ensure(connection, timeline_id, definition, world, now)
    found = Day(connection, timeline_id, definition, world, state)
    local = now.astimezone(zone(timezone))
    today = local.date()
    me, era_modern = found.found, modern_bank(found.found['bank'])
    week = []
    for back in range(6, -2, -1):
        day = today - timedelta(days=back)
        meal = found.meal(day)
        ahead = day > today or (day == today and local.hour < EVENING_OVER)  # tonight's dinner is a plan until then
        text = plan_text(meal, era_modern) if ahead else meal_text(meal, era_modern)
        week.append({'date': day.isoformat(), 'kind': meal['kind'], 'text': text, 'groceries': meal['groceries'],
                     'today': day == today})
    pantry = found.pantry(today)
    overrides = decode(state['overrides'] or '{}')
    result = {'today': today.isoformat(), 'diet': me['diet'], 'avoids': me['avoids'], 'skill': me['skill'],
              'skill_text': skill_text(me), 'bakes': bool(me.get('bakes')), 'favorites': me.get('favorites') or [],
              'summary': f"{skill_text(me)[:1].upper()}{skill_text(me)[1:]}"
                         f"{' who loves baking' if me.get('bakes') else ''}; they {diet_text(me)}.",
              'cuisine': bank(me['bank'])['label'], 'week': week, 'run_label': run_label(me['bank']),
              'pantry': [{'name': item['name'], 'state': item['state']} for item in pantry],
              'pantry_text': pantry_text(pantry) or 'The basics are stocked.',
              'changed': sorted(overrides), 'diets': list(DIETS), 'avoid_choices': list(AVOIDS), 'skills': list(SKILLS),
              'realism': found.level}
    if show_odds:
        weights = dict(RHYTHM[me['skill']])
        total = sum(weights.values())
        result['numbers'] = {'rhythm': {key: round(value / total * 100) for key, value in weights.items()},
                             'days_left': {item['name']: item['days_left'] for item in pantry}}
    return result


def change(connection, timeline_id: str, body: dict, definition: dict, world, now):
    """The user's changes to their way of eating; None for a field puts back the app's own pick."""
    state = ensure(connection, timeline_id, definition, world, now)
    overrides = decode(state['overrides'] or '{}')
    for key, value in body.items():
        if key == 'reset':
            continue
        if value is None:
            overrides.pop(key, None)
            continue
        if key == 'diet':
            require(value in DIETS, 'Pick one of the listed diets.', 422)
        if key == 'avoids':
            require(set(value) <= set(AVOIDS), 'Pick from the listed things to avoid.', 422)
            value = [name for name in AVOIDS if name in value]
        if key == 'skill':
            require(value in range(len(SKILLS)), 'Pick one of the listed cooking skills.', 422)
        if key == 'favorites':
            value = [name.strip() for name in value if name.strip()][:5]
        overrides[key] = value
    if body.get('reset'):
        overrides = {}
    connection.execute('UPDATE kitchen_state SET overrides=?, updated_at=? WHERE timeline_id=?',
                       (encode(overrides), stamp(now), timeline_id))
    # Upcoming entries that mention dinner are drawn again from the new settings.
    removed = connection.execute(
        "DELETE FROM life_agenda WHERE timeline_id=? AND subject=? AND status='upcoming' "
        "AND json_extract(entry, '$.kitchen') IS NOT NULL", (timeline_id, COMPANION)).rowcount
    if removed:
        connection.execute('UPDATE agenda_cursors SET through=MIN(through, ?) WHERE timeline_id=? AND subject=?',
                           (stamp(now), timeline_id, COMPANION))


# --- Timelines ---

def copy(connection, parent_id: str, new_id: str, cutoff: str):
    """A fork keeps their way of eating and the user's changes; meals are drawn, so nothing else is copied."""
    state = optional(connection, 'SELECT * FROM kitchen_state WHERE timeline_id=?', (parent_id,))
    if state:
        connection.execute('INSERT INTO kitchen_state (timeline_id, seed, profile, overrides, created_at, updated_at) '
                           'VALUES (?, ?, ?, ?, ?, ?)', (new_id, state['seed'], state['profile'], state['overrides'],
                                                         state['created_at'], cutoff))
