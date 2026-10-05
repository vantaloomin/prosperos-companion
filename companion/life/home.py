"""The companion's home and belongings: where they live and the things they live with.

Assembled once per timeline from the world data and a seed, without a model: a home from the
city's housing and rent data (companion/world/generators.home), sometimes a pet, a few plants, a
way to get around and a few favourite things suited to their interests and the city's era. It
changes slowly: every two weeks a seeded draw may bring home a plant, lose one, send the car to
the shop or add a favourite thing, each logged once on the day it happens.

Belongings show up in the companion's own agenda entries (`touch`, called once from
companion/life/agenda.py) as a plain sentence the model may rephrase, in image prompts for the
scenes they appear in (`image_hint`) and in chat context (`context_lines`). The user can rename,
redescribe, remove, restore or add belongings; upcoming entries that mention the home are then
rebuilt. Other modules read costs through `monthly_costs` and `purchases`, never these tables.
"""
import re
from datetime import date, timedelta

from companion.clock import stamp, zone
from companion.database import decode, encode, identifier, many, one, optional
from companion.errors import require
from companion.life import circle
from companion.world import catalog, generators

COMPANION = 'companion'
KINDS = ('home', 'pet', 'plant', 'vehicle', 'favorite')
PERIOD_DAYS = 14
CHANGE_SHARE = 0.45
MAX_PLANTS, MAX_FAVORITES = 4, 6
RECENT_DAYS = 21
MODERN = {'modern', 'future'}

# variety: (description choices, sentences while at home, sentences out walking). {pet} is its name.
PETS = {
    'cat': (('an orange tabby cat', 'a gray shorthair cat', 'a tuxedo cat', 'a calico cat', 'a sleek black cat'),
            ('{pet} stayed curled up nearby the whole time.', '{pet} supervised from the windowsill.',
             '{pet} knocked a pen off the table, as usual.'), ()),
    'dog': (('a scruffy terrier mix', 'a beagle mix', 'a lanky greyhound', 'a shaggy collie mix', 'a stocky pit mix'),
            ('{pet} stayed close the whole time.', '{pet} got a long belly rub.', '{pet} snored on the rug.'),
            ('{pet} came along and sniffed every tree.', '{pet} came along, tail going the whole way.')),
    'rabbit': (('a lop-eared rabbit', 'a brown dwarf rabbit'),
               ('{pet} hopped laps around the room.', '{pet} chewed on a cardboard box.'), ()),
    'bird': (('a chatty green budgie', 'a yellow canary'),
             ('{pet} chirped along in the background.', '{pet} sang from the cage by the window.'), ()),
}
PET_VARIETIES = {True: ('cat', 'dog', 'rabbit', 'bird'), False: ('cat', 'dog', 'bird')}
PET_WEIGHTS = {True: (5, 4, 1, 1), False: (5, 4, 1)}
PET_NAMES = {
    True: ('Biscuit', 'Pepper', 'Miso', 'Juniper', 'Olive', 'Mochi', 'Pickles', 'Moose', 'Clementine', 'Bean',
           'Waffles', 'Ziggy', 'Hazel', 'Basil', 'Nugget', 'Otis', 'Tofu', 'Maple', 'Pip', 'Sprout', 'Turnip',
           'Dumpling', 'Figaro', 'Nori', 'Fennel', 'Winnie'),
    False: ('Bramble', 'Tuppence', 'Barnaby', 'Patch', 'Captain', 'Duchess', 'Rags', 'Bess', 'Merlin', 'Hob',
            'Jasper', 'Thimble', 'Clover', 'Smudge'),
}
PLANTS = {
    True: ('monstera', 'pothos', 'snake plant', 'fiddle-leaf fig', 'spider plant', 'pot of basil', 'aloe',
           'peace lily', 'tray of succulents', 'rosemary bush'),
    False: ('window box of geraniums', 'pot of rosemary', 'trailing ivy', 'fern', 'pot of thyme', 'pot of lemon balm'),
}
SPOTS = ('windowsill', 'bookshelf', 'kitchen counter', 'corner by the door', 'nightstand', 'desk')
# variety: (descriptions, short name, its state while out of action, what went wrong as a phrase)
VEHICLES = {
    'car': (('an old silver hatchback', 'a secondhand blue sedan', 'a dented red compact', 'a beat-up pickup'),
            'the car', 'in the shop', 'took {name} into the shop'),
    'bike': (('a commuter bike with a squeaky brake', 'a secondhand road bike'), 'the bike', 'laid up with a flat',
             'got a flat on {name}'),
    'scooter': (('a secondhand moped',), 'the moped', 'in the shop', 'took {name} into the shop'),
    'horse': (('a patient bay mare', 'a stubborn gray gelding'), 'the horse', 'resting a sore hoof',
              'found {name} favouring a sore hoof'),
    'bicycle': (('a black safety bicycle',), 'the bicycle', 'waiting on a new wheel', 'bent a wheel on {name}'),
}
# name, what using it at home looks like, interest stems, modern only (None) or any era
FAVORITES = (
    ('a chipped green mug', 'had tea in the chipped green mug', (), False),
    ('a record player', 'had a record spinning on the record player', ('music', 'vinyl', 'record', 'jazz', 'band'),
     True),
    ('a secondhand guitar', 'played a few songs on the secondhand guitar', ('music', 'guitar', 'song'), True),
    ('a fiddle', 'played the fiddle for a while', ('music', 'song', 'dance'), False),
    ('an overflowing bookshelf', 'pulled something new off the overflowing bookshelf',
     ('read', 'book', 'novel', 'poetry', 'literature'), False),
    ('a cast-iron pan', 'got the cast-iron pan out', ('cook', 'baking', 'bake', 'recipe', 'food'), False),
    ('a sketchbook', 'filled a page of the sketchbook', ('art', 'draw', 'paint', 'sketch', 'illustrat'), False),
    ('an old patchwork quilt', 'curled up under the old patchwork quilt', (), False),
    ('a game console', 'played a round on the game console', ('game', 'gaming', 'video'), True),
    ('a battered chess set', 'set up the battered chess set', ('chess', 'game', 'puzzle', 'strategy'), False),
    ('a string of fairy lights', 'switched on the fairy lights', (), True),
    ('a good coffee grinder', 'ground fresh beans in the good coffee grinder', ('coffee',), True),
    ('a knitting basket', 'worked on something from the knitting basket', ('knit', 'sew', 'craft', 'crochet'), False),
    ('a telescope by the window', 'looked through the telescope for a while', ('astronom', 'star', 'space', 'science'),
     False),
)
FEATURES = {
    True: ('a bay window', 'a radiator that clanks in winter', 'a tiny balcony', 'exposed brick', 'a galley kitchen',
           'creaky floorboards', 'a clawfoot tub', 'a window that sticks', 'good afternoon light'),
    False: ('a smoky hearth', 'a window that sticks', 'low beams', 'a creaky stair', 'a little yard',
            'good morning light'),
}
SIZES = {'studio': 'a studio', 'one_bedroom': 'a one-bedroom', 'two_bedroom': 'a two-bedroom'}
HOUSING = {'single-family': 'single-family house', 'master-planned': 'house in a master-planned community',
           'two-family-house': 'two-family house', 'new-build': 'new building'}
PLURAL = {'rooms', 'lodgings', 'chambers', 'barracks', 'hotel', 'warehouse'}
# Favourite things that only suit some moments at home (the rest suit any).
FITS = {'a cast-iron pan': {'home-cooking'}, 'an overflowing bookshelf': {'reading', 'slow'},
        'a sketchbook': {'slow', 'reading'}, 'a game console': {'slow'}, 'a battered chess set': {'slow'},
        'a telescope by the window': {'slow'}, 'a knitting basket': {'slow', 'reading'},
        'a secondhand guitar': {'slow', 'chores'}, 'a fiddle': {'slow', 'chores'}}
# Activities that happen at home, where a belonging can come up.
AT_HOME = {'chores', 'home-cooking', 'reading', 'nap', 'slow'}
DRIVEN = {'groceries', 'browse'}
WORKING = {'work', 'study'}


# --- Assembly ---

def modern(data: dict | None) -> bool:
    return data is None or data['era'] in MODERN


def stems_match(definition: dict, stems) -> bool:
    words = {word.strip('.,;:!?()"\'').casefold() for phrase in [*definition.get('interests', ()),
             *definition.get('life_themes', ())] for word in phrase.split()}
    return any(word == stem or len(stem) > 3 and word.startswith(stem) for word in words for stem in stems)


def housing_text(housing: str) -> str:
    """Readable housing: "rooms-over-store" is "rooms over a store"."""
    text = HOUSING.get(housing, housing.replace('-', ' '))
    return re.sub(r' (over|behind|around|above) (?!a )', r' \1 a ', text)


def article(text: str) -> str:
    """"a" or "an" before a thing; none before plurals such as "rooms over a store" or "lodgings"."""
    if text.split(' ')[0] in PLURAL or text.endswith('quarters'):
        return text
    return f"{'an' if text[:1] in 'aeiou' else 'a'} {text}"


def place_item(seed: str, definition: dict, data: dict | None) -> dict:
    """The home: from the city's housing and rents when the world knows the city, else a plain apartment."""
    features = sorted({generators.pick(seed, f'feature{index}', list(FEATURES[modern(data)])) for index in range(2)})
    if not data:
        return {'kind': 'home', 'name': 'an apartment', 'variety': 'apartment',
                'details': {'description': 'an apartment', 'features': features, 'city': definition.get('location', '')}}
    match = catalog.resolve(definition.get('location') or '')
    near = match['neighborhood'] if match and match['city'] == data['id'] else None
    bedrooms = generators.pick(seed, 'bedrooms', list(SIZES), [3, 5, 2])
    found = generators.home(data, seed=seed, bedrooms=bedrooms, near=near)
    housing = housing_text(found['housing'])
    name = f'{SIZES[bedrooms]} in {article(housing)}' if modern(data) else article(housing)
    hood = found['neighborhood']['name']
    return {'kind': 'home', 'name': name, 'variety': found['housing'], 'details': {
        'description': f'{name} in {hood}', 'neighborhood': hood, 'city': data['name'], 'bedrooms': bedrooms,
        'rent': found['rent'], 'rent_range': found['rent_range'], 'currency': found['currency'],
        'rent_period': found['rent_period'], 'estimate': True, 'features': features, 'refs': found['refs'],
        'sources': found['sources'], 'data_version': found['data_version']}}


def pet_item(seed: str, era_modern: bool, label: str = 'pet') -> dict:
    variety = generators.pick(seed, f'{label}:kind', list(PET_VARIETIES[era_modern]), list(PET_WEIGHTS[era_modern]))
    description = generators.pick(seed, f'{label}:look', list(PETS[variety][0]))
    age = 1 + int(generators.unit(seed, label, 'age') * 9)
    return {'kind': 'pet', 'name': generators.pick(seed, f'{label}:name', list(PET_NAMES[era_modern])),
            'variety': variety, 'details': {'description': f'{description}, about {age} years old'}}


def plant_item(seed: str, era_modern: bool, label: str, taken=()) -> dict | None:
    choices = [plant for plant in PLANTS[era_modern] if f'the {plant}' not in taken]
    plant = generators.pick(seed, f'{label}:plant', choices)
    if plant is None:
        return None
    spot = generators.pick(seed, f'{label}:spot', list(SPOTS))
    return {'kind': 'plant', 'name': f'the {plant}', 'variety': plant,
            'details': {'description': f'{article(plant)} on the {spot}', 'spot': spot}}


def vehicle_item(seed: str, data: dict | None) -> dict | None:
    """A way to get around: a car is likelier where there is no subway; earlier eras ride or cycle."""
    if modern(data):
        speeds = data['speeds'] if data else {}
        car = 0.5 if not data else 0.3 if 'subway' in speeds else 0.65
        roll = generators.unit(seed, 'vehicle')
        variety = 'car' if roll < car else 'bike' if roll < car + 0.2 else 'scooter' if roll < car + 0.25 else None
    else:
        riding = 'horse' in data['speeds']
        variety = ('horse' if riding else 'bicycle') if generators.unit(seed, 'vehicle') < 0.35 else None
    if variety is None:
        return None
    descriptions, short, _repair, _modern = VEHICLES[variety]
    return {'kind': 'vehicle', 'name': short, 'variety': variety,
            'details': {'description': generators.pick(seed, 'vehicle:look', list(descriptions))}}


def favorite_item(seed: str, definition: dict, era_modern: bool, label: str, taken=()) -> dict | None:
    """A favourite thing, three times likelier when it suits their interests."""
    choices = [item for item in FAVORITES if (era_modern or not item[3]) and item[0] not in taken]
    weights = [3.0 if item[2] and stems_match(definition, item[2]) else 1.0 for item in choices]
    chosen = generators.pick(seed, f'{label}:favorite', choices, weights)
    if chosen is None:
        return None
    return {'kind': 'favorite', 'name': chosen[0], 'variety': chosen[0], 'details': {'description': chosen[0]}}


def assemble(seed: str, definition: dict, data: dict | None) -> list[dict]:
    """Everything they start with: the same for the same seed, definition and city data."""
    era_modern = modern(data)
    items = [place_item(seed, definition, data)]
    if generators.unit(seed, 'has-pet') < 0.55:
        items.append(pet_item(seed, era_modern))
    names: list[str] = []
    for index in range(int(generators.unit(seed, 'plants') * 4)):
        if plant := plant_item(seed, era_modern, f'plant{index}', names):
            names.append(plant['name'])
            items.append(plant)
    items.append(vehicle_item(seed, data))
    for index in range(2 + int(generators.unit(seed, 'favorites') * 2)):
        if favorite := favorite_item(seed, definition, era_modern, f'favorite{index}', names):
            names.append(favorite['name'])
            items.append(favorite)
    return [item for item in items if item]


def started_on(connection, timeline_id) -> date:
    row = one(connection, 'SELECT created_at FROM timelines WHERE id=?', (timeline_id,))
    return date.fromisoformat(row['created_at'][:10])


def ensure(connection, timeline_id: str, definition: dict, world, now) -> dict:
    """The timeline's home state, assembling the home the first time it is needed."""
    state = optional(connection, 'SELECT * FROM home_state WHERE timeline_id=?', (timeline_id,))
    if state:
        return state
    seed, start = f'home:{timeline_id}', started_on(connection, timeline_id)
    data = circle.city_data(definition, world)
    for item in assemble(seed, definition, data):
        insert_item(connection, timeline_id, item, 'generated', start, now)
    connection.execute('INSERT INTO home_state (timeline_id, seed, started, era, next_period, created_at, updated_at) '
                       'VALUES (?, ?, ?, ?, 1, ?, ?)', (timeline_id, seed, start.isoformat(),
                                                        'modern' if modern(data) else data['era'], stamp(now),
                                                        stamp(now)))
    return one(connection, 'SELECT * FROM home_state WHERE timeline_id=?', (timeline_id,))


def insert_item(connection, timeline_id, item: dict, origin: str, since: date, now) -> str:
    item_id = identifier()
    connection.execute(
        'INSERT INTO home_items (id, timeline_id, kind, name, variety, details, origin, since, created_at, updated_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (item_id, timeline_id, item['kind'], item['name'], item['variety'], encode(item['details']), origin,
         since.isoformat(), stamp(now), stamp(now)))
    return item_id


# --- Inventory on a date ---

def items_on(connection, timeline_id, day: date) -> list[dict]:
    """What they have on this local date, in kind order."""
    rows = many(connection, 'SELECT * FROM home_items WHERE timeline_id=? AND since<=? AND (until IS NULL OR until>?) '
                'ORDER BY since, created_at', (timeline_id, day.isoformat(), day.isoformat()))
    return sorted((item_view(row) for row in rows), key=lambda item: KINDS.index(item['kind']))


def item_view(row: dict) -> dict:
    return {'id': row['id'], 'kind': row['kind'], 'name': row['name'], 'variety': row['variety'],
            **decode(row['details']), 'origin': row['origin'], 'since': row['since'], 'until': row['until'],
            'edited': bool(row['edited']), 'revision': row['revision']}


def repairs_on(connection, timeline_id, day: date) -> dict[str, dict]:
    """Belongings out of action on this date, by item id."""
    rows = many(connection, "SELECT * FROM home_log WHERE timeline_id=? AND kind='repair' AND local_date<=? "
                'AND until>?', (timeline_id, day.isoformat(), day.isoformat()))
    return {row['item_id']: row for row in rows}


# --- Slow change ---

def change_day(state: dict, period: int) -> date:
    start = date.fromisoformat(state['started']) + timedelta(days=PERIOD_DAYS * period)
    return start + timedelta(days=int(generators.unit(state['seed'], 'change-day', period) * PERIOD_DAYS))


def evolve(connection, timeline_id: str, through: date, now) -> int:
    """Apply the seeded changes due on or before `through`. Each two-week period has at most one,
    recorded once, so evolving in steps or all at once gives the same home."""
    state = one(connection, 'SELECT * FROM home_state WHERE timeline_id=?', (timeline_id,))
    period, applied = state['next_period'], 0
    while (day := change_day(state, period)) <= through:
        done = optional(connection, 'SELECT id FROM home_log WHERE timeline_id=? AND period=?', (timeline_id, period))
        if not done and generators.unit(state['seed'], 'change', period) < CHANGE_SHARE:
            applied += apply_change(connection, state, period, day, now)
        period += 1
    connection.execute('UPDATE home_state SET next_period=?, updated_at=? WHERE timeline_id=?',
                       (period, stamp(now), timeline_id))
    return applied


def options(items: list[dict], repairs: dict, era_modern: bool) -> list[tuple[str, float]]:
    """The changes that make sense for what they have now, with weights."""
    kinds = [item['kind'] for item in items]
    choices = [('rearrange', 1.0)]
    if kinds.count('plant') < MAX_PLANTS:
        choices.append(('new-plant', 3.0))
    if 'plant' in kinds:
        choices.append(('plant-lost', 1.5))
    if kinds.count('favorite') < MAX_FAVORITES:
        choices.append(('new-favorite', 2.0))
    if any(item['kind'] == 'vehicle' and item['id'] not in repairs for item in items):
        choices.append(('repair', 2.0))
    if 'pet' in kinds and era_modern:
        choices.append(('vet', 1.5))
    if 'pet' not in kinds:
        choices.append(('new-pet', 0.5))
    return choices


def apply_change(connection, state, period, day: date, now) -> int:
    timeline_id, seed = state['timeline_id'], f"{state['seed']}:{period}"
    items = items_on(connection, timeline_id, day)
    era_modern = state['era'] == 'modern'
    choices = options(items, repairs_on(connection, timeline_id, day), era_modern)
    kind = generators.pick(seed, 'kind', [key for key, _ in choices], [weight for _, weight in choices])
    made = CHANGES[kind](connection, state, seed, day, items, era_modern, now)
    if made is None:
        return 0
    item_id, text, until, spend = made
    connection.execute('INSERT INTO home_log (id, timeline_id, period, local_date, kind, item_id, until, text, spend, '
                       'created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                       (identifier(), timeline_id, period, day.isoformat(), kind, item_id,
                        until.isoformat() if until else None, text, spend, stamp(now)))
    return 1


def new_plant(connection, state, seed, day, items, era_modern, now):
    plant = plant_item(seed, era_modern, 'new', [item['name'] for item in items])
    if plant is None:
        return None
    item_id = insert_item(connection, state['timeline_id'], plant, 'change', day, now)
    return item_id, f"brought home {article(plant['variety'])} for the {plant['details']['spot']}", None, '$'


def plant_lost(connection, state, seed, day, items, era_modern, now):
    plant = generators.pick(seed, 'lost', [item for item in items if item['kind'] == 'plant'])
    connection.execute('UPDATE home_items SET until=?, updated_at=? WHERE id=?', (day.isoformat(), stamp(now),
                                                                                  plant['id']))
    return plant['id'], f"lost {plant['name']}: it finally gave up", None, ''


def new_favorite(connection, state, seed, day, items, era_modern, now):
    definition = {'interests': [], 'life_themes': []}
    favorite = favorite_item(seed, definition, era_modern, 'new', [item['name'] for item in items])
    if favorite is None:
        return None
    item_id = insert_item(connection, state['timeline_id'], favorite, 'change', day, now)
    return item_id, f"picked up {favorite['name']}", None, '$$'


def repair(connection, state, seed, day, items, era_modern, now):
    repairs = repairs_on(connection, state['timeline_id'], day)
    vehicle = next(item for item in items if item['kind'] == 'vehicle' and item['id'] not in repairs)
    phrase = VEHICLES.get(vehicle['variety'], VEHICLES['car'])[3]
    until = day + timedelta(days=3 + int(generators.unit(seed, 'repair') * 6))
    return vehicle['id'], phrase.format(name=vehicle['name']), until, '$$'


def vet(connection, state, seed, day, items, era_modern, now):
    pet = next(item for item in items if item['kind'] == 'pet')
    return pet['id'], f"took {pet['name']} to the vet for a checkup", None, '$$'


def new_pet(connection, state, seed, day, items, era_modern, now):
    pet = pet_item(seed, era_modern, 'adopted')
    item_id = insert_item(connection, state['timeline_id'], pet, 'change', day, now)
    return item_id, f"adopted {pet['name']}, {pet['details']['description']}", None, '$$'


def rearrange(connection, state, seed, day, items, era_modern, now):
    return None, 'rearranged the furniture', None, ''


CHANGES = {'new-plant': new_plant, 'plant-lost': plant_lost, 'new-favorite': new_favorite, 'repair': repair,
           'vet': vet, 'new-pet': new_pet, 'rearrange': rearrange}


# --- Events ---

def touch(connection, timeline_id: str, subject: str, entry: dict | None, local_date: str, seed: str,
          definition: dict, world, now) -> dict | None:
    """The companion's agenda entry with their home woven in: a change that happens that day, or now
    and then a belonging that fits the activity. Circle members' entries pass through unchanged."""
    if subject != COMPANION or not entry or entry.get('activity') in WORKING_ACTIVITIES:
        return entry
    day = date.fromisoformat(local_date)
    ensure(connection, timeline_id, definition, world, now)
    evolve(connection, timeline_id, day, now)
    change = untold_change(connection, timeline_id, day)
    if change:
        sentence = f"{definition['name']} {change['text']}."
        return woven(entry, sentence, [change['item_id']] if change['item_id'] else [], change['id'])
    found = belonging(connection, timeline_id, entry, day, seed)
    return woven(entry, found[1], found[0], None) if found else entry


WORKING_ACTIVITIES = {'steady-shift', 'busy-shift', 'library', 'study-cafe'}


def untold_change(connection, timeline_id, day: date) -> dict | None:
    """A change logged for this date that no agenda entry mentions yet."""
    for row in many(connection, 'SELECT * FROM home_log WHERE timeline_id=? AND local_date=?',
                    (timeline_id, day.isoformat())):
        told = optional(connection, "SELECT id FROM life_agenda WHERE timeline_id=? AND subject=? "
                        "AND json_extract(entry, '$.home.change')=?", (timeline_id, COMPANION, row['id']))
        if not told:
            return row
    return None


def belonging(connection, timeline_id, entry, day, seed) -> tuple[list[str], str] | None:
    """(item ids, sentence) for a belonging that fits this activity, or None most of the time."""
    items = items_on(connection, timeline_id, day)
    roll = generators.unit(seed, 'home')
    activity = entry.get('activity')
    if activity in AT_HOME and roll < 0.45:
        return at_home(items, seed, activity)
    if activity == 'walk' and roll < 0.7:
        return walked(items, seed)
    if activity in DRIVEN and roll < 0.3:
        return driven(items, repairs_on(connection, timeline_id, day), seed)
    return None


def at_home(items, seed, activity=None) -> tuple[list[str], str] | None:
    usable = [item for item in items if item['kind'] in ('pet', 'plant', 'favorite')
              and (activity is None or item['kind'] != 'favorite' or activity in FITS.get(item['variety'], {activity}))]
    item = generators.pick(seed, 'belonging', usable)
    if item is None:
        return None
    if item['kind'] == 'pet':
        lines = PETS.get(item['variety'], PETS['cat'])[1]
        return [item['id']], generators.pick(seed, 'pet-line', list(lines)).format(pet=item['name'])
    if item['kind'] == 'plant':
        return [item['id']], f"Watered {item['name']} while at it."
    use = next((favorite[1] for favorite in FAVORITES if favorite[0] == item['variety']), None)
    return [item['id']], f'{use}.' if use else f"Made good use of {item['name']}."


def walked(items, seed) -> tuple[list[str], str] | None:
    dogs = [item for item in items if item['kind'] == 'pet' and PETS.get(item['variety'], PETS['cat'])[2]]
    if not dogs:
        return None
    dog = dogs[0]
    return [dog['id']], generators.pick(seed, 'walk-line', list(PETS[dog['variety']][2])).format(pet=dog['name'])


def driven(items, repairs, seed) -> tuple[list[str], str] | None:
    vehicle = next((item for item in items if item['kind'] == 'vehicle'), None)
    if vehicle is None:
        return None
    if vehicle['id'] in repairs:
        status = VEHICLES.get(vehicle['variety'], VEHICLES['car'])[2]
        return [vehicle['id']], f"With {vehicle['name']} still {status}, it took longer than usual."
    verb = 'Rode' if vehicle['variety'] in ('horse', 'bike', 'bicycle', 'scooter') else 'Drove'
    return [vehicle['id']], f"{verb} {vehicle['name']} there."


def woven(entry: dict, sentence: str, item_ids: list[str], change_id: str | None) -> dict:
    sentence = sentence[0].upper() + sentence[1:]
    return {**entry, 'summary': f"{entry['summary'].rstrip()} {sentence}",
            'home': {'items': item_ids, 'change': change_id, 'sentence': sentence}}


# --- Images and chat ---

def mentioned(items: list[dict], text: str) -> list[dict]:
    """Belongings named in the text. A capitalised name (a pet's) must match its case, so "Bean" is
    not found in "beans" or "a bean salad"."""
    return [item for item in items if item['kind'] != 'home' and re.search(
        rf'(?<!\w){re.escape(item["name"])}(?!\w)', text, 0 if item['name'][:1].isupper() else re.IGNORECASE)]


def image_hint(connection, timeline_id: str, event: dict) -> str:
    """What the picture should show of their home: the room for a moment at home, and how any
    belonging the event names looks. Empty when the home was never assembled."""
    rows = many(connection, 'SELECT * FROM home_items WHERE timeline_id=?', (timeline_id,))
    if not rows:
        return ''
    items = [item_view(row) for row in rows]
    parts = []
    home = next((item for item in items if item['kind'] == 'home' and not item['until']), None)
    if home and not event.get('place'):
        features = home.get('features') or []
        parts.append(f"At home: {home['description']}" + (f", with {' and '.join(features)}" if features else '') + '.')
    parts += [f"{item['name'][:1].upper()}{item['name'][1:]} is {item['description']}." for item in
              mentioned(items, event.get('summary', '')) if item['description'] != item['name']]
    return ' '.join(parts)


def money_text(home: dict) -> str:
    if not home.get('rent'):
        return ''
    currency = home.get('currency') or {}
    symbol = currency.get('symbol', '$') if isinstance(currency, dict) else '$'
    return f" Rent is about {symbol}{home['rent']:,} a {home.get('rent_period', 'month')} (an estimate)."


def context_lines(connection, timeline_id: str, day: date) -> list[tuple[str, str]]:
    """(identity, line) pairs describing their home today, for the chat context."""
    items = items_on(connection, timeline_id, day)
    if not items:
        return []
    repairs = repairs_on(connection, timeline_id, day)
    lines = []
    for item in items:
        text = item_line(item)
        if item['id'] in repairs:
            text += f" Right now it is {repair_status(item)} (back {repairs[item['id']]['until']})."
        lines.append((item['id'], text))
    since = (day - timedelta(days=RECENT_DAYS)).isoformat()
    for row in many(connection, 'SELECT * FROM home_log WHERE timeline_id=? AND local_date>? AND local_date<=? '
                    'ORDER BY local_date', (timeline_id, since, day.isoformat())):
        lines.append((row['id'], f"- Recently ({row['local_date']}): you {row['text']}."))
    return lines


def item_line(item: dict) -> str:
    if item['kind'] == 'home':
        features = item.get('features') or []
        return (f"- Home: {item['description']}" + (f", {item['city']}" if item.get('city') else '') + '.'
                + (f" It has {' and '.join(features)}." if features else '') + money_text(item))
    label = {'pet': 'Pet', 'plant': 'Plant', 'vehicle': 'Getting around', 'favorite': 'A favourite thing'}[item['kind']]
    detail = f" ({item['description']})" if item['description'] != item['name'] else ''
    return f"- {label}: {item['name']}{detail}."


def repair_status(item: dict) -> str:
    return VEHICLES.get(item['variety'], VEHICLES['car'])[2]


# --- For other modules (money) ---

def monthly_costs(connection, timeline_id: str, day: date) -> dict | None:
    """Rent and what they keep that costs money each month, for the budget. None before the home exists."""
    items = items_on(connection, timeline_id, day)
    home = next((item for item in items if item['kind'] == 'home'), None)
    if home is None:
        return None
    return {'rent': home.get('rent'), 'rent_period': home.get('rent_period', 'month'),
            'currency': home.get('currency'), 'estimate': True,
            'pets': [item['variety'] for item in items if item['kind'] == 'pet'],
            'vehicles': [item['variety'] for item in items if item['kind'] == 'vehicle']}


def purchases(connection, timeline_id: str, start: date, end: date) -> list[dict]:
    """Home changes that cost something, between two local dates inclusive: {date, kind, text, spend}."""
    rows = many(connection, "SELECT * FROM home_log WHERE timeline_id=? AND spend!='' AND local_date>=? "
                'AND local_date<=? ORDER BY local_date', (timeline_id, start.isoformat(), end.isoformat()))
    return [{'date': row['local_date'], 'kind': row['kind'], 'text': row['text'], 'spend': row['spend']}
            for row in rows]


# --- Edits ---

def today_for(version: dict, now) -> date:
    return now.astimezone(zone(version['timezone'])).date()


def view(connection, timeline_id: str, day: date, include_removed=False) -> dict:
    items = items_on(connection, timeline_id, day)
    removed = []
    if include_removed:
        removed = [item_view(row) for row in many(
            connection, 'SELECT * FROM home_items WHERE timeline_id=? AND until IS NOT NULL AND until<=? '
            'ORDER BY until DESC', (timeline_id, day.isoformat()))]
    repairs = repairs_on(connection, timeline_id, day)
    for item in items:
        item['out_of_action'] = (f"{repair_status(item)} until {repairs[item['id']]['until']}"
                                 if item['id'] in repairs else None)
    since = (day - timedelta(days=60)).isoformat()
    changes = many(connection, 'SELECT local_date, kind, text FROM home_log WHERE timeline_id=? AND local_date>? '
                   'AND local_date<=? ORDER BY local_date DESC', (timeline_id, since, day.isoformat()))
    return {'today': day.isoformat(), 'items': items, 'removed': removed, 'changes': changes,
            'costs': monthly_costs(connection, timeline_id, day),
            'varieties': {'pet': list(PETS), 'vehicle': list(VEHICLES)}}


def item(connection, timeline_id: str, item_id: str) -> dict:
    row = optional(connection, 'SELECT * FROM home_items WHERE id=? AND timeline_id=?', (item_id, timeline_id))
    require(row is not None, 'That belonging is not in their home.', 404)
    return row


def edit(connection, timeline_id: str, item_id: str, change: dict, day: date, now):
    """Rename or redescribe a belonging (and, for a pet or a vehicle, change what kind it is)."""
    row = item(connection, timeline_id, item_id)
    details = decode(row['details'])
    if change.get('description') is not None:
        details['description'] = change['description']
    variety = change.get('variety') or row['variety']
    allowed = {'pet': PETS, 'vehicle': VEHICLES}.get(row['kind'])
    require(variety == row['variety'] or (allowed is not None and variety in allowed), 'Pick one of the listed kinds.',
            422)
    connection.execute('UPDATE home_items SET name=?, variety=?, details=?, edited=1, revision=revision+1, '
                       'updated_at=? WHERE id=?', (change.get('name') or row['name'], variety, encode(details),
                                                   stamp(now), item_id))
    rebuild(connection, timeline_id, day, now)


def add(connection, timeline_id: str, body: dict, day: date, now) -> str:
    require(body['kind'] in KINDS[1:], 'Add a pet, a plant, a vehicle or a favourite thing.', 422)
    variety = body.get('variety') or ''
    if body['kind'] in ('pet', 'vehicle'):
        variety = variety or ('cat' if body['kind'] == 'pet' else 'car')
        require(variety in (PETS if body['kind'] == 'pet' else VEHICLES), 'Pick one of the listed kinds.', 422)
    item_id = insert_item(connection, timeline_id, {
        'kind': body['kind'], 'name': body['name'], 'variety': variety or body['name'],
        'details': {'description': body.get('description') or body['name']}}, 'user', day, now)
    connection.execute('UPDATE home_items SET edited=1 WHERE id=?', (item_id,))
    rebuild(connection, timeline_id, day, now)
    return item_id


def set_removed(connection, timeline_id: str, item_id: str, removed: bool, day: date, now):
    row = item(connection, timeline_id, item_id)
    require(row['kind'] != 'home', 'Their home can be described differently, not removed.', 422)
    connection.execute('UPDATE home_items SET until=?, edited=1, revision=revision+1, updated_at=? WHERE id=?',
                       (day.isoformat() if removed else None, stamp(now), item_id))
    rebuild(connection, timeline_id, day, now)


def rebuild(connection, timeline_id: str, day: date, now):
    """After an edit: forget seeded changes still ahead (they were drawn from the old home) and the
    upcoming agenda entries that mention the home, so both are drawn again from what is there now."""
    ahead = many(connection, 'SELECT * FROM home_log WHERE timeline_id=? AND local_date>?', (timeline_id,
                                                                                              day.isoformat()))
    for row in ahead:
        if row['kind'] == 'plant-lost':
            connection.execute('UPDATE home_items SET until=NULL WHERE id=? AND until=?', (row['item_id'],
                                                                                         row['local_date']))
    connection.execute("DELETE FROM home_items WHERE timeline_id=? AND origin='change' AND since>?",
                       (timeline_id, day.isoformat()))
    connection.execute('DELETE FROM home_log WHERE timeline_id=? AND local_date>?', (timeline_id, day.isoformat()))
    state = one(connection, 'SELECT * FROM home_state WHERE timeline_id=?', (timeline_id,))
    elapsed = (day - date.fromisoformat(state['started'])).days
    connection.execute('UPDATE home_state SET next_period=MIN(next_period, ?) WHERE timeline_id=?',
                       (max(1, elapsed // PERIOD_DAYS), timeline_id))
    removed = connection.execute(
        "DELETE FROM life_agenda WHERE timeline_id=? AND subject=? AND status='upcoming' "
        "AND json_extract(entry, '$.home') IS NOT NULL", (timeline_id, COMPANION)).rowcount
    if removed:
        connection.execute('UPDATE agenda_cursors SET through=MIN(through, ?) WHERE timeline_id=? AND subject=?',
                           (stamp(now), timeline_id, COMPANION))


# --- Timelines ---

def copy(connection, parent_id: str, new_id: str, cutoff: str, ids: dict):
    """A fork keeps the home as it was at the fork point; what changes after that is drawn again."""
    state = optional(connection, 'SELECT * FROM home_state WHERE timeline_id=?', (parent_id,))
    if not state:
        return
    day = cutoff[:10]
    rows = many(connection, 'SELECT * FROM home_items WHERE timeline_id=? AND since<=?', (parent_id, day))
    logged = many(connection, 'SELECT * FROM home_log WHERE timeline_id=? AND local_date<=?', (parent_id, day))
    for row in logged:
        ids[row['id']] = identifier()
    for row in rows:
        ids[row['id']] = identifier()
        until = row['until'] if row['until'] and row['until'] <= day else None
        connection.execute(
            'INSERT INTO home_items (id, timeline_id, kind, name, variety, details, origin, since, until, edited, '
            'revision, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (ids[row['id']], new_id, row['kind'], row['name'], row['variety'], row['details'], row['origin'],
             row['since'], until, row['edited'], row['revision'], row['created_at'], row['updated_at']))
    for row in logged:
        connection.execute(
            'INSERT INTO home_log (id, timeline_id, period, local_date, kind, item_id, until, text, spend, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (ids[row['id']], new_id, row['period'], row['local_date'], row['kind'], ids.get(row['item_id']),
             row['until'], row['text'], row['spend'], row['created_at']))
    elapsed = (date.fromisoformat(day) - date.fromisoformat(state['started'])).days
    connection.execute('INSERT INTO home_state (timeline_id, seed, started, era, next_period, created_at, updated_at) '
                       'VALUES (?, ?, ?, ?, ?, ?, ?)', (new_id, state['seed'], state['started'], state['era'],
                                                        max(1, elapsed // PERIOD_DAYS), state['created_at'], cutoff))
