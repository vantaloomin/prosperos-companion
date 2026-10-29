"""Worlds and personas: more than one life for the user, each in its own world.

A persona is the user as someone in particular: a name, a gender, an age, a birthday and a few lines about them.
A world is everything that happened to one persona there: its companions, their lives and town, the chats,
memories, feed and pictures. Each persona has one or more worlds, and two worlds may share a city.

Each world is a workspace of its own, one database in its own folder (the first world keeps the data folder's
own database, `Database.root`), so nothing in one world can reach another. Which worlds and personas there are
lives in `worlds.json` beside the first world. Switching points the app's one Database at the other world's file
(`Database.use`); what belongs to the user rather than to a world (model connections, image backends, voices,
settings, their own cities, paired phones) is carried over from the world they leave, so it follows them.

"The world exists outside of User" (Vanta, 2026-10-08): nobody sets anything up. An existing workspace silently
becomes the first world, with a persona made from what the app already knows about the user; a new persona or
world arrives ready in the city the user picked (the form starts on a featured one the app picks), and the user
makes its first companion there, as on a first run (Vanta, 2026-10-12: a new world starts with a blank companion to
create, not a townsperson). Becoming a townsperson is the exception: that world starts with someone from their
circle.
"""
import json
import os
import re
import shutil
import sqlite3
from datetime import date
from pathlib import Path

from companion import backup, cast, characters, dating, library, lore, observer, restore, story, world_year
from companion.clock import AppClock, stamp, zone
from companion.database import Database, identifier, optional
from companion.errors import require
from companion.life import ages, narrator, pets, where
from companion.models import PERSONA_AGES, CharacterDefinition
from companion.world import catalog, changes, custom, generators, lifespans, mix, townsfolk

REGISTRY = 'worlds.json'
FOLDER = 'worlds'
DATABASE = 'companion.sqlite3'
GENDERS = ('woman', 'man', 'nonbinary')
# What belongs to the user rather than to a world: carried from the world they leave into the one they enter, as a
# restore keeps them (companion/restore.py). Debug time stays with its world; their own cities follow them.
SHARED = tuple(table for table in restore.KEPT_SETTINGS if table != 'debug_time') + ('world_cities',)
# Revisions only ever move forward in a world, so queued work there can tell it went stale.
REVISIONS = ('permission_revision', 'memory_revision')
# A starter companion is a grown-up townsperson who has a life of their own to bring.
STARTER_AGES = (21, 45)
# The city picker's "Somewhere new (picked for you)": a featured city other than the one the user is in.
SOMEWHERE_NEW = 'somewhere-new'


# The registry -------------------------------------------------------------------------------------------

def registry_path(root: Path) -> Path:
    return Path(root) / REGISTRY


def load(root: Path) -> dict | None:
    try:
        data = json.loads(registry_path(root).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not data.get('worlds') or not data.get('personas'):
        return None
    return data


def save(root: Path, data: dict):
    """Written whole and swapped in, so a crash never leaves half a registry."""
    path = registry_path(root)
    partial = path.with_name(path.name + '.partial')
    partial.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    os.replace(partial, path)


def world_path(home: Path, world: dict) -> Path:
    """The first world keeps the database the app was opened with; every other world has its own folder."""
    return Path(home).parent / world['folder'] / DATABASE if world['folder'] else Path(home)


def active_path(home: Path) -> Path:
    """The active world's database, read without opening anything (the launcher applies a restore there)."""
    data = load(Path(home).parent)
    world = data and find(data['worlds'], data.get('active'))
    path = world_path(home, world) if world else Path(home)
    return path if path.exists() else Path(home)


def find(items: list[dict], item_id: str | None) -> dict | None:
    return next((item for item in items if item['id'] == item_id), None)


def found(items: list[dict], item_id: str, what: str) -> dict:
    item = find(items, item_id)
    require(item is not None, f'That {what} is no longer here.', 404)
    return item


def registry(database: Database) -> dict:
    data = load(database.root)
    require(data is not None, 'The list of worlds could not be read. Restart the Companion.', 409)
    return data


# The first world ----------------------------------------------------------------------------------------

def persona_from(connection, timestamp: str) -> dict:
    """The user as the workspace already knows them: their Matchlight profile and the birthday they mentioned."""
    profile = dating.profile(connection) or {}
    life = optional(connection, 'SELECT user_birthday FROM life_settings WHERE id=1') or {}
    return {'id': identifier(), 'name': profile.get('name', ''), 'gender': profile.get('gender', ''),
            'age': profile.get('age'), 'about': profile.get('bio', ''), 'birthday': life.get('user_birthday', ''),
            'created_at': timestamp}


def city_of(connection) -> dict:
    """The city a world takes place in: its main character's, else the default one."""
    return story.city_data(connection, story.default_city(connection))


def first_registry(database: Database) -> dict:
    """Everything already here becomes the first world, with a persona made from what the app knows."""
    timestamp = database.now()
    with database.connect() as connection:
        persona = persona_from(connection, timestamp)
        city = city_of(connection)
    world = {'id': identifier(), 'name': city['name'], 'persona_id': persona['id'], 'folder': '',
             'city_id': city['id'], 'created_at': timestamp, 'used_at': timestamp}
    world['home'] = where.picked(city, world['id'])
    return {'version': 1, 'active': world['id'], 'personas': [persona], 'worlds': [world]}


def follow_first_companion(database: Database):
    """A world named for the default city before anyone lived in it takes the city of its first companion (a world
    started in Baltimore whose first companion lives in Haddon Harbor becomes "Haddon Harbor"). A name the user gave
    it stays."""
    data = load(database.root)
    world = data and find(data['worlds'], data.get('active'))
    if not world:
        return
    with database.connect() as connection:
        count = connection.execute('SELECT COUNT(*) FROM companions').fetchone()[0]
        city = city_of(connection)
        known = changes.resolve(world.get('city_id') or '', custom.all_cities(connection))
    named = known and re.fullmatch(rf"{re.escape(known['name'])}(?: \d+)?", world['name'])
    if count != 1 or not named or city['id'] == world.get('city_id'):
        return
    others = {**data, 'worlds': [item for item in data['worlds'] if item['id'] != world['id']]}
    world |= {'name': unique_name(others, city['name']), 'city_id': city['id']}
    with database.connect(write=True) as connection:
        # A home the app picked moves with the world's city; one the user picked stays.
        if settle_home(connection, world):
            write_persona(connection, found(data['personas'], world['persona_id'], 'persona'), database.now(),
                          world['home'])
    save(database.root, data)


def start(database: Database):
    """At startup: the registry (made on the first run of this version) and the world the user was last in."""
    data = load(database.root)
    if data is None:
        data = first_registry(database)
        save(database.root, data)
    world = find(data['worlds'], data.get('active')) or next(item for item in data['worlds'] if not item['folder'])
    path = world_path(database.home, world)
    if not path.exists():  # A world folder removed by hand: back to the first world.
        world = next(item for item in data['worlds'] if not item['folder'])
        path = database.home
    data['active'] = database.world = world['id']
    save(database.root, data)
    if path != database.path:
        database.use(path)
    mix.load(database)
    with database.connect(write=True) as connection:
        if restored_home(connection, world) | settle_home(connection, world):
            save(database.root, data)
        write_persona(connection, found(data['personas'], world['persona_id'], 'persona'), database.now(),
                      world['home'])


# Personas in a world ------------------------------------------------------------------------------------

def write_persona(connection, persona: dict, timestamp: str, home: dict | None = None):
    """Who the user is in this world, and where they live in it (`home`, the world's), for the prompt
    (companion/memory/context.py), Matchlight and Where you are (companion/life/where.py)."""
    home = home or {}
    before = optional(connection, 'SELECT home_city_id FROM persona WHERE id=1')
    age = age_here(connection, persona.get('age'))
    dating.follow_home(connection, before['home_city_id'] if before else '', home.get('city_id', ''))
    connection.execute('INSERT OR REPLACE INTO persona (id, persona_id, name, gender, age, about, updated_at, '
                       'townsfolk_key, town_seed, pets, home_city_id, home_neighbourhood, kind, lifespan) '
                       'VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                       (persona['id'], persona['name'], persona['gender'], age, persona['about'],
                        timestamp, persona.get('townsfolk_key', ''), persona.get('town_seed', ''),
                        json.dumps(persona.get('pets') or []), home.get('city_id', ''), home.get('neighbourhood', ''),
                        persona.get('kind') or '', persona.get('lifespan')))
    connection.execute('UPDATE life_settings SET user_birthday=? WHERE id=1', (persona.get('birthday') or '',))


def age_here(connection, age: int | None) -> int | None:
    """The persona's age in this world: younger by the years a Back when world goes back (companion/back_when.py),
    never under 18."""
    row = optional(connection, 'SELECT persona_years FROM back_when WHERE id=1')
    return max(age - row['persona_years'], ages.ADULT) if row and age else age


def world_city(connection, world: dict, cities: dict[str, dict]) -> dict:
    """The city the world is in: the one it was made in, else (a city since deleted) its companion's."""
    return cities.get(world.get('city_id') or '') or city_of(connection)


def restored_home(connection, world: dict) -> bool:
    """A world restored from a backup (or brought from another install) remembers where the user lived in it; a home
    the app picked in this registry gives way to it. True when the home changed."""
    row = optional(connection, 'SELECT home_city_id, home_neighbourhood FROM persona WHERE id=1')
    home = world.get('home') or {}
    if not row or not row['home_city_id'] or home.get('set_by') == where.YOURS or \
            (row['home_city_id'], row['home_neighbourhood']) == (home.get('city_id'), home.get('neighbourhood')):
        return False
    world['home'] = {'city_id': row['home_city_id'], 'neighbourhood': row['home_neighbourhood'], 'set_by': where.YOURS}
    return True


def settle_home(connection, world: dict) -> bool:
    """The world's home for its persona, picked when it has none (companion/life/where.py). True when it changed."""
    cities = where.known_cities(connection)
    return where.settle(world, world_city(connection, world, cities), cities)


def read_back(database: Database, data: dict):
    """A birthday the user mentioned in chat was saved in the world; the persona keeps it when they leave."""
    world = found(data['worlds'], data['active'], 'world')
    persona = found(data['personas'], world['persona_id'], 'persona')
    with database.connect() as connection:
        life = optional(connection, 'SELECT user_birthday FROM life_settings WHERE id=1')
    if life and life['user_birthday']:
        persona['birthday'] = life['user_birthday']


# Views ----------------------------------------------------------------------------------------------------

def read_only(path: Path, query: str) -> list[tuple]:
    """Rows from a world's database, read without opening it for writing; none when it can't be read."""
    if not path.exists():
        return []
    try:
        connection = sqlite3.connect(f'{path.resolve().as_uri()}?mode=ro', uri=True)
        try:
            return connection.execute(query).fetchall()
        finally:
            connection.close()
    except sqlite3.DatabaseError:
        return []


def companions_in(path: Path) -> list[str]:
    """The names of a world's companions, main character first."""
    return [row[0] for row in read_only(path, 'SELECT v.name FROM companions c JOIN character_versions v ON '
                                              'v.id=c.active_version_id ORDER BY c.slot IS NULL, c.stepped_back_at DESC')]


def watching_in(path: Path) -> bool:
    """Whether the user is just watching that world (companion/observer.py)."""
    return bool(read_only(path, 'SELECT watching FROM observer WHERE id=1 AND watching=1'))


def back_when_in(path: Path) -> dict | None:
    """A Back when world's year and who it was made for (companion/back_when.py); None for any other world."""
    rows = read_only(path, 'SELECT year, name, companion_id FROM back_when WHERE id=1')
    return {'year': rows[0][0], 'name': rows[0][1], 'companion_id': rows[0][2]} if rows else None


def world_view(database: Database, data: dict, world: dict, cities: dict[str, dict] | None = None) -> dict:
    if cities is None:
        with database.connect() as connection:
            cities = where.known_cities(connection)
    return {**world, 'active': world['id'] == data['active'], 'first': not world['folder'],
            'companions': companions_in(world_path(database.home, world)),
            'watching': watching_in(world_path(database.home, world)),
            'year': world_year.year_in(world_path(database.home, world), database.clock.real()),
            'back_when': back_when_in(world_path(database.home, world)),
            'home': where.view(world.get('home'), cities)}


def view(database: Database) -> dict:
    data = registry(database)
    active = found(data['worlds'], data['active'], 'world')
    with database.connect() as connection:
        cities = where.known_cities(connection)
        here = city_of(connection)
    personas = [{**persona, 'active': persona['id'] == active['persona_id'], 'kind_shown': kind_shown(persona, here),
                 'worlds': [world_view(database, data, world, cities) for world in
                            sorted(data['worlds'], key=lambda item: item['used_at'], reverse=True)
                            if world['persona_id'] == persona['id']]}
                for persona in data['personas']]
    return {'active_world_id': active['id'], 'active_persona_id': active['persona_id'],
            'world': world_view(database, data, active, cities),
            'persona': find(personas, active['persona_id']), 'personas': personas, 'genders': list(GENDERS)}


# Switching ------------------------------------------------------------------------------------------------

def busy(state) -> str | None:
    """Why the app cannot leave its world right now, if it cannot."""
    if state.conversation.running or state.groups.rounds:
        return 'A reply is still being written. Switch when it has finished.'
    if getattr(state.training, 'active', False):
        return 'A LoRA is training in this world. Switch when it has finished.'
    with state.database.connect() as connection:
        if optional(connection, 'SELECT id FROM debug_time WHERE id=1'):
            return 'Debug time is on in this world. Return to real time in Settings > Debug first.'
    return None


def carry_settings(target: Path, source: Path, timestamp: str):
    """What follows the user, from the world they leave into `target`; its revisions keep moving forward."""
    connection = sqlite3.connect(target, isolation_level=None)
    try:
        before = connection.execute(f"SELECT {', '.join(REVISIONS)} FROM workspace_settings WHERE id=1").fetchone()
    finally:
        connection.close()
    restore.copy_settings(target, source, SHARED, timestamp)
    connection = sqlite3.connect(target, isolation_level=None)
    try:
        # Lore of a city deleted in another world goes with it (companion/lore.py).
        lore.drop_orphaned(connection)
        assignments = ', '.join(f'{column}=MAX({column}, ?) + 1' for column in REVISIONS)
        connection.execute(f'UPDATE workspace_settings SET {assignments} WHERE id=1', tuple(before or (0, 0)))
        # Memories still waiting from the world's last visit were queued under its own settings; they stay due, and
        # forming one still checks automatic memory is on (companion/memory/formation.py).
        if before:
            connection.execute("UPDATE memory_jobs SET permission_revision=(SELECT permission_revision FROM "
                               "workspace_settings WHERE id=1) WHERE status='queued' AND permission_revision=?",
                               (before[0],))
    finally:
        connection.close()


def recover(state):
    """Work the world left half done when it was last open, as a start does (companion/main.py lifespan)."""
    from companion import conversation, groups
    from companion.images import jobs as image_jobs
    conversation.recover(state.database)
    groups.recover(state.database)
    image_jobs.recover(state.database)
    state.memory.kick()
    state.images.wake()


def switch(state, world_id: str) -> dict:
    database = state.database
    data = registry(database)
    world = found(data['worlds'], world_id, 'world')
    if world['id'] == data['active']:
        return view(database)
    reason = busy(state)
    require(reason is None, reason or '', 409)
    target = world_path(database.home, world)
    require(target.exists(), "That world's folder is missing from the data folder.", 404)
    read_back(database, data)
    previous = database.path
    restore.settle(previous)
    database.use(target)
    mix.load(database)
    carry_settings(target, previous, database.now())
    # The registry orders worlds by real time: a world in a past year would otherwise sort as used long ago.
    data['active'], world['used_at'] = world['id'], stamp(database.clock.real())
    database.world = world['id']
    with database.connect(write=True) as connection:
        settle_home(connection, world)
        write_persona(connection, found(data['personas'], world['persona_id'], 'persona'), database.now(),
                      world['home'])
    save(database.root, data)
    recover(state)
    return view(database)


def switch_persona(state, persona_id: str) -> dict:
    """A persona's world is the one they were last in."""
    data = registry(state.database)
    found(data['personas'], persona_id, 'persona')
    theirs = [world for world in data['worlds'] if world['persona_id'] == persona_id]
    require(bool(theirs), 'That persona has no world yet.', 409)
    return switch(state, max(theirs, key=lambda item: item['used_at'])['id'])


# New worlds -----------------------------------------------------------------------------------------------

def starter_sheet(data: dict, seed: str) -> dict | None:
    """A grown-up townsperson to be the new world's first companion, the same one for the same world. Never one of a
    pack's own named characters: they belong to the setting's author."""
    people = [sheet for place in data['places'] for sheet in townsfolk.at_place(data, place['id'])
              if STARTER_AGES[0] <= sheet['age'] <= STARTER_AGES[1] and not sheet.get('notable')]
    return min(people, key=lambda sheet: generators.unit(sheet['key'], 'starter', seed), default=None)


def starter(connection, data: dict, seed: str, timestamp: str, today: date, persona: dict | None = None):
    """Their profile from their town sheet, no model involved (companion/cast.py): a friend the user knows from
    around town, or, when the user became a townsperson, someone from that person's own circle. The user can change
    them, find someone on Matchlight or make their own afterwards."""
    you = (persona or {}).get('townsfolk_key')
    sheet = circle_sheet(data, you, seed) if you else starter_sheet(data, seed)
    if sheet is None:
        return
    met = {'match': None, 'meetings': [], 'focus': None, 'in_story': None}
    definition = cast.profile(data, sheet, met, today) | {'starting_closeness': 2}
    if you:
        definition |= {'starting_closeness': 3,
                       'history_together': known_from(data, sheet, you, persona['name']) or definition['history_together']}
    made = characters.create_in(connection, timestamp, CharacterDefinition.model_validate(definition),
                                'The first companion of a new world.')
    connection.execute('UPDATE companions SET townsfolk_key=?, town_seed=? WHERE id=?',
                       (sheet['key'], data.get('town', ''), made['id']))


def build(database: Database, path: Path, persona: dict, city_id: str, seed: str, town: str | None = None,
          town_mix: dict | None = None, home: dict | None = None, watch: bool = False, year: int | None = None):
    """A new world's database: the user's settings and the persona; when the user became one of a town's people
    (`town`), also a starter companion from that person's circle. Its townsfolk mix (companion/world/mix.py) is
    `town_mix`, else the one of the world it was made from. `year` starts it in a past year (companion/world_year.py)."""
    restore.settle(database.path)
    if town_mix is None:
        with database.connect() as connection:
            town_mix = mix.read(connection)
    try:
        made = Database(path, AppClock(database.clock.base), year)
        fill(made, database.path, persona, city_id, seed, town, town_mix, home, watch)
    finally:
        # Opening it pointed the app-wide clocks at the new world; the user is still in this one.
        database.follow()


def fill(made: Database, source: Path, persona: dict, city_id: str, seed: str, town: str | None, town_mix: dict,
         home: dict | None, watch: bool):
    path = made.path
    carry_settings(path, source, made.now())
    with made.connect(write=True) as connection, mix.using(town_mix):
        if town_mix != mix.DEFAULTS:
            mix.write(connection, town_mix, made.now())
        write_persona(connection, persona, made.now(), home)
        observer.watch(connection, watch, made.now())  # "Watch a city": the new world starts just watching.
        data = dating.city_for(connection, city_id, seed[:16] if town is None else town)
        if town is not None:
            today = made.clock.now().astimezone(zone(data['timezone'])).date()
            starter(connection, data, seed, made.now(), today, persona)
    lore.carry_city_lore(path, source, data)
    library.carry_city_books(path, source, data)


def somewhere_new(connection, here: str, seed: str, now=None) -> str:
    """A featured city other than `here`, the same one for the same world; `here` when nothing else is featured. It
    leans toward cities within NEAR_HOURS of the user's clock, so the companion found there is awake on the user's
    evenings more often (companion/life/their_hours.py), without ruling the far ones out."""
    from companion.life import their_hours
    others = [city for city in catalog.featured(custom.all_cities(connection))['cities'] if city['id'] != here]
    mine = their_hours.user_zone(connection) if their_hours.known(connection) else None

    def weight(city: dict) -> float:
        if mine is None or not now or not city.get('timezone'):
            return 1.0
        return NEAR_WEIGHT if abs(their_hours.gap(city['timezone'], mine, now)) <= NEAR_HOURS * 60 else 1.0
    # A weighted draw with one roll per city: the highest roll ** (1 / weight) wins.
    picked = max(others, key=lambda city: generators.unit(city['id'], 'somewhere-new', seed) ** (1 / weight(city)),
                 default=None)
    return picked['id'] if picked else here


# "Somewhere new" leans this many times toward a featured city within NEAR_HOURS of the user's clock.
NEAR_HOURS = 4
NEAR_WEIGHT = 4.0


def unique_name(data: dict, wanted: str) -> str:
    taken = {world['name'] for world in data['worlds']}
    if wanted not in taken:
        return wanted
    return next(f'{wanted} {number}' for number in range(2, 1000) if f'{wanted} {number}' not in taken)


def create_world(database: Database, persona_id: str | None = None, name: str | None = None,
                 city_id: str | None = None, town: str | None = None, town_mix: dict | None = None,
                 watch: bool = False, year: int | None = None) -> dict:
    """A new world for a persona (the active one by default), in the current city unless another is named. `town`
    reuses a town's people instead of seeding new ones (Become a townsperson). `SOMEWHERE_NEW` lets the app pick.
    `town_mix` is its townsfolk mix (Settings > Debug), else the current world's. `watch` starts it just watching
    (Watch a city, companion/observer.py). `year` starts it in a past year (Back when, companion/world_year.py)."""
    if year is not None:
        world_year.check(year, database.clock.real().date())
    data = registry(database)
    active = found(data['worlds'], data['active'], 'world')
    persona = found(data['personas'], persona_id or active['persona_id'], 'persona')
    world_id = identifier()
    with database.connect() as connection:
        if city_id == SOMEWHERE_NEW:
            city_id = somewhere_new(connection, city_of(connection)['id'], world_id, database.clock.now())
        city = story.city_data(connection, city_id) if city_id else city_of(connection)
    folder = f'{FOLDER}/{world_id}'
    path = database.root / folder / DATABASE
    home = where.picked(city, world_id)
    try:
        build(database, path, persona, city['id'], world_id, town, town_mix, home, watch, year)
    except BaseException:
        shutil.rmtree(path.parent, ignore_errors=True)
        raise
    timestamp = database.now()
    world = {'id': world_id, 'name': (name or '').strip()[:80] or unique_name(data, city['name']),
             'persona_id': persona['id'], 'folder': folder, 'city_id': city['id'], 'home': home,
             'created_at': timestamp, 'used_at': timestamp}
    data['worlds'].append(world)
    save(database.root, data)
    return world_view(database, data, world)


# Becoming a townsperson (Feature Hit List #43) -------------------------------------------------------------
# The user picks someone they or their companion met around town and starts a new life as them: a new world in the
# same city with the same town's people, where that person is the user's persona. They never play two people in
# one world, nothing carries over from the world they left (it waits as it was), and their persona text starts
# from the person's town sheet, drafted by rules (companion/cast.py), for them to change like any persona.

PRONOUN_GENDERS = {'she': 'woman', 'he': 'man', 'they': 'nonbinary'}


def gender_of(sheet: dict) -> str:
    """A townsperson's pronouns ("she/her") as a persona gender."""
    return PRONOUN_GENDERS.get(str(sheet.get('pronouns') or '').split('/')[0].strip().casefold(), '')


def circle_sheet(data: dict, you: str, seed: str) -> dict | None:
    """Someone from the person's own circle at their usual place: a coworker, or a regular they see there."""
    sheet = townsfolk.find(data, you)
    if sheet is None:
        return starter_sheet(data, seed)
    around = [other for other in townsfolk.at_place(data, sheet['place']['id'])
              if other['key'] != you and other['age'] >= STARTER_AGES[0]]
    grown = [other for other in around if other['age'] <= STARTER_AGES[1]] or around
    pick = min(grown, key=lambda other: generators.unit(other['key'], 'starter', seed), default=None)
    return pick or next((other for other in [starter_sheet(data, seed)] if other and other['key'] != you), None)


def known_from(data: dict, sheet: dict, you: str, name: str) -> str:
    """How the starter companion knows the user, from where the two of them are in town."""
    person = townsfolk.find(data, you)
    if person is None:
        return ''
    first = name.split()[0] if name.split() else name
    place = person['place']['name']
    together = 'they work together' if person['staff'] and sheet['staff'] else \
        'the user works' if person['staff'] else 'they are both regulars'
    return f'Knows the user, {first}, from {place}, where {together}.'


def sheet_text(definition: dict) -> str:
    """The persona's starting text from the person's drafted profile, without how a companion met them."""
    parts = (definition['identity'], definition['personality'], definition['background'], f"Usually: {definition['routine']}",
             definition.get('seen_as') and f"Comes across as: {definition['seen_as']}")
    return '\n'.join(part for part in parts if part)


def persona_for(data: dict, sheet: dict, today: date, timestamp: str) -> dict:
    met = {'match': None, 'meetings': [], 'focus': None, 'in_story': None}
    definition = cast.profile(data, sheet, met, today)
    return {'id': identifier(), 'name': sheet['full'], 'gender': gender_of(sheet),
            'age': sheet['age'], 'about': sheet_text(definition)[:2000], 'birthday': '', 'created_at': timestamp,
            'townsfolk_key': sheet['key'], 'town_seed': data.get('town', ''),
            # Their kind comes with them: an elven townsperson is an elf of their real age (companion/cast.py).
            'kind': definition.get('kind') or '', 'lifespan': None}


def become(state, key: str) -> dict:
    """Start a new life as a townsperson the user or their companion has met, and switch to it."""
    database = state.database
    now = database.clock.now()
    with database.connect() as connection:
        already = optional(connection, 'SELECT id FROM companions WHERE townsfolk_key=?', (key,))
        name = already and characters.by_id(connection, already['id'])['version']['name']
        require(not name, f"{name} is already one of your companions, so you can't become them.", 409)
        # Someone the user is just watching (companion/observer.py) can be stepped into without having been met.
        place_data, sheet = narrator.watched_person(connection, key) or \
            cast.townsperson(connection, characters.require_current(connection), key, now)[:2]
        cast.still_here(place_data, sheet, now, "you can't become them")
        today = now.astimezone(zone(place_data['timezone'])).date()
        sheet = {**sheet, 'age': ages.town_age(connection, sheet, today)}  # Birthdays since the town began count.
    town = place_data.get('town', '')
    persona = persona_for(place_data, sheet, today, database.now())
    data = registry(database)
    data['personas'].append(persona)
    save(database.root, data)
    try:
        world = create_world(database, persona['id'], sheet['full'], place_data['id'], town)
    except BaseException:
        data = registry(database)
        data['personas'] = [item for item in data['personas'] if item['id'] != persona['id']]
        save(database.root, data)
        raise
    return switch(state, world['id'])


# Personas -------------------------------------------------------------------------------------------------

def kind_shown(persona: dict, data: dict | None) -> dict:
    """The Persona page's Kind and How long they live (companion/world/lifespans.py): what applies, the app's pick from
    their words, and what the pickers offer where they are."""
    found = lifespans.from_words(persona.get('about') or '', data)
    shown = lifespans.described(lifespans.persona_kind(persona, data), persona.get('lifespan'), persona.get('age'), data)
    return shown | {'found': found, 'found_label': lifespans.kinds(data)[found]['label'],
                    'picked': persona.get('kind') or '', **lifespans.choices(data)}


def check_kind(database: Database, persona: dict):
    """A kind picked must be one listed where they are; an age past 120 is only for a long-lived kind, picked or read
    from their words."""
    with database.connect() as connection:
        data = city_of(connection)
    require(not persona.get('kind') or persona['kind'] in lifespans.kinds(data), 'Pick one of the kinds listed.', 422)
    require((persona.get('age') or 0) <= PERSONA_AGES[0] or lifespans.long_lived(lifespans.persona_lifespan(persona, data)),
            f'An age past {PERSONA_AGES[0]} is only for a long-lived kind: pick one under Kind.', 422)


def create_persona(database: Database, body) -> dict:
    """A new persona with a world of their own. Who the user is stays theirs to say (Vanta, 2026-10-09): the name
    they typed, and nothing the app makes up; what they leave blank stays blank. Where they live is theirs to pick
    too (the form starts on somewhere new, picked for them); everyone in it is decided for them."""
    name = (body.name or '').strip()
    require(bool(name), 'Give the new persona a name.', 422)
    persona = {'id': identifier(), 'name': name, 'gender': body.gender or '', 'age': body.age,
               'about': (body.about or '').strip(), 'birthday': body.birthday or '', 'created_at': database.now(),
               'pets': pets.persona_entries([], [pet.model_dump() for pet in body.pets or []],
                                            database.clock.now().date()),
               'kind': body.kind or '', 'lifespan': body.lifespan}
    check_kind(database, persona)
    return with_world(database, persona, getattr(body, 'city_id', None))


def with_world(database: Database, persona: dict, city_id: str | None) -> dict:
    """A persona joins the list with a new world of their own in `city_id`; neither stays if the world fails."""
    data = registry(database)
    data['personas'].append(persona)
    save(database.root, data)
    try:
        world = create_world(database, persona['id'], city_id=city_id)
    except BaseException:
        data = registry(database)
        data['personas'] = [item for item in data['personas'] if item['id'] != persona['id']]
        save(database.root, data)
        raise
    return {**persona, 'worlds': [world]}


# What a copy of a persona takes from them: who they are, never what belongs to their worlds (where they live there,
# or the townsperson they became in one).
COPIED = ('name', 'gender', 'age', 'about', 'birthday', 'pets', 'kind', 'lifespan')


def copy_persona(database: Database, persona_id: str, city_id: str | None) -> dict:
    """A separate persona made from this one, with a world of their own where everyone is new, so the user need not
    type them again. Changing either one later leaves the other as it was; the app picks their home as in any new
    world."""
    persona = found(registry(database)['personas'], persona_id, 'persona')
    copy = json.loads(json.dumps({key: persona.get(key) for key in COPIED}))
    return with_world(database, {**copy, 'id': identifier(), 'created_at': database.now()}, city_id)


def update_persona(database: Database, persona_id: str, body) -> dict:
    data = registry(database)
    persona = found(data['personas'], persona_id, 'persona')
    changes = body.model_dump(exclude_unset=True)
    if 'name' in changes:
        changes['name'] = (changes['name'] or '').strip()
    if 'pets' in changes:
        changes['pets'] = pets.persona_entries(persona.get('pets') or [], changes['pets'] or [],
                                               database.clock.now().date())
    persona.update({key: '' if value is None and key not in ('age', 'lifespan') else value
                    for key, value in changes.items()})
    check_kind(database, persona)
    save(database.root, data)
    active = found(data['worlds'], data['active'], 'world')
    if active['persona_id'] == persona_id:
        with database.connect(write=True) as connection:
            write_persona(connection, persona, database.now(), active.get('home'))
    return view(database)


def update_world(database: Database, world_id: str, body) -> dict:
    """Rename a world, or give it to another persona."""
    data = registry(database)
    world = found(data['worlds'], world_id, 'world')
    if body.name is not None:
        require(body.name.strip(), 'Give the world a name.', 422)
        world['name'] = body.name.strip()[:80]
    if body.persona_id is not None:
        persona = found(data['personas'], body.persona_id, 'persona')
        world['persona_id'] = persona['id']
        if world['id'] == data['active']:
            with database.connect(write=True) as connection:
                write_persona(connection, persona, database.now(), world.get('home'))
    save(database.root, data)
    return view(database)


def home_choices(database: Database, world_id: str, city_id: str | None = None) -> dict:
    """Where the persona can live in a world (companion/life/where.py): its home, the cities they can pick and the
    neighbourhoods of `city_id` (else of their home's city)."""
    data = registry(database)
    world = found(data['worlds'], world_id, 'world')
    with database.connect() as connection:
        cities = where.known_cities(connection)
        here = world_city(connection, world, cities)
    listed = where.choices(here, cities)
    shown = cities.get(city_id or (world.get('home') or {}).get('city_id') or '') or here
    return {'home': where.view(world.get('home'), cities),
            'cities': [{'id': city['id'], 'name': city['name'], 'region': city.get('region', ''),
                        'country': city.get('country', ''), 'category': catalog.category(city)} for city in listed],
            'city_id': shown['id'],
            'neighbourhoods': [{'id': hood['id'], 'name': hood['name']}
                               for hood in sorted(shown.get('neighborhoods') or [], key=lambda hood: hood['name'])]}


def change_home(database: Database, world_id: str, body) -> dict:
    """The user moves: a city they can live in from this world and a neighbourhood there (blank lets the app pick)."""
    data = registry(database)
    world = found(data['worlds'], world_id, 'world')
    with database.connect(write=True) as connection:
        cities = where.known_cities(connection)
        city = cities.get(body.city_id)
        require(city is not None, 'That city is no longer here.', 404)
        where.change(world, world_city(connection, world, cities), city, body.neighbourhood or '')
        if world['id'] == data['active']:
            write_persona(connection, found(data['personas'], world['persona_id'], 'persona'), database.now(),
                          world['home'])
            from companion.life import long_distance
            long_distance.settle_all(connection, database.clock.now())  # Visits planned for the old home.
    save(database.root, data)
    return view(database)


def set_aside(database: Database, world: dict) -> str:
    """A verified backup of a world about to be deleted, in the data folder's backups/deleted-worlds; it is not
    listed in Settings > Backups, where restoring it would replace the world the user is in."""
    created_at = database.now()
    name = f"before-delete-world-{created_at[:19].replace(':', '').replace('-', '')}-{world['id'][:6]}.zip"
    path = world_path(database.home, world)
    backup.archive(path, database.root / 'backups' / 'deleted-worlds' / name, created_at, include_datasets=True)
    return name


def delete_world(database: Database, world_id: str) -> dict:
    """A world goes with everything in it, after a backup. Not the one the user is in, nor the first world, whose
    folder holds all the others (Start over empties it instead)."""
    data = registry(database)
    world = found(data['worlds'], world_id, 'world')
    require(world['id'] != data['active'], 'Switch to another world before deleting this one.', 409)
    require(bool(world['folder']), 'The first world holds the others, so it stays. Settings > Start over can empty '
            'it instead.', 409)
    if world_path(database.home, world).exists():
        set_aside(database, world)
    shutil.rmtree(database.root / world['folder'], ignore_errors=True)
    data['worlds'].remove(world)
    save(database.root, data)
    return view(database)


def delete_persona(database: Database, persona_id: str) -> dict:
    data = registry(database)
    persona = found(data['personas'], persona_id, 'persona')
    theirs = [world for world in data['worlds'] if world['persona_id'] == persona_id]
    require(all(world['id'] != data['active'] for world in theirs),
            'Switch to another persona before deleting this one.', 409)
    require(all(world['folder'] for world in theirs), 'This persona lives in the first world, so they stay. '
            'Give that world to another persona first.', 409)
    for world in theirs:
        delete_world(database, world['id'])
    data = registry(database)
    data['personas'] = [item for item in data['personas'] if item['id'] != persona['id']]
    save(database.root, data)
    return view(database)
