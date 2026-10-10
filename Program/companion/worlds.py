"""Worlds and personas: more than one life for the user, each in its own world.

A persona is the user as someone in particular: a name, a gender, an age, a birthday and a few lines about them.
A world is everything that happened to one persona there: its companions, their lives and town, the chats,
memories, feed and pictures. Each persona has one or more worlds, and two worlds may share a city: each world
seeds its own townsfolk, so the same streets hold different people.

Each world is a workspace of its own, one database in its own folder (the first world keeps the data folder's
own database, `Database.root`), so nothing in one world can reach another. Which worlds and personas there are
lives in `worlds.json` beside the first world. Switching points the app's one Database at the other world's file
(`Database.use`); what belongs to the user rather than to a world (model connections, image backends, voices,
settings, their own cities, paired phones) is carried over from the world they leave, so it follows them.

"The world exists outside of User" (Vanta, 2026-10-08): nobody sets anything up. An existing workspace silently
becomes the first world, with a persona made from what the app already knows about the user; a new persona or
world arrives ready, in the current city with fresh townsfolk and a starter companion drawn from them, and the
user changes whatever they like afterwards.
"""
import json
import os
import shutil
import sqlite3
from datetime import date
from pathlib import Path

from companion import backup, cast, characters, dating, restore, story
from companion.clock import AppClock, zone
from companion.database import Database, identifier, optional
from companion.errors import require
from companion.models import CharacterDefinition
from companion.world import generators, townsfolk

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
    return {'version': 1, 'active': world['id'], 'personas': [persona], 'worlds': [world]}


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
    with database.connect(write=True) as connection:
        write_persona(connection, found(data['personas'], world['persona_id'], 'persona'), database.now())


# Personas in a world ------------------------------------------------------------------------------------

def write_persona(connection, persona: dict, timestamp: str):
    """Who the user is in this world, for the prompt (companion/memory/context.py) and Matchlight."""
    connection.execute('INSERT OR REPLACE INTO persona (id, persona_id, name, gender, age, about, updated_at) '
                       'VALUES (1, ?, ?, ?, ?, ?, ?)', (persona['id'], persona['name'], persona['gender'],
                                                        persona['age'], persona['about'], timestamp))
    connection.execute('UPDATE life_settings SET user_birthday=? WHERE id=1', (persona.get('birthday') or '',))


def read_back(database: Database, data: dict):
    """A birthday the user mentioned in chat was saved in the world; the persona keeps it when they leave."""
    world = found(data['worlds'], data['active'], 'world')
    persona = found(data['personas'], world['persona_id'], 'persona')
    with database.connect() as connection:
        life = optional(connection, 'SELECT user_birthday FROM life_settings WHERE id=1')
    if life and life['user_birthday']:
        persona['birthday'] = life['user_birthday']


# Views ----------------------------------------------------------------------------------------------------

def companions_in(path: Path) -> list[str]:
    """The names of a world's companions, main character first, read without opening it for writing."""
    if not path.exists():
        return []
    try:
        connection = sqlite3.connect(f'{path.resolve().as_uri()}?mode=ro', uri=True)
        try:
            rows = connection.execute('SELECT v.name FROM companions c JOIN character_versions v '
                                      'ON v.id=c.active_version_id ORDER BY c.slot IS NULL, c.stepped_back_at DESC')
            return [row[0] for row in rows]
        finally:
            connection.close()
    except sqlite3.DatabaseError:
        return []


def world_view(database: Database, data: dict, world: dict) -> dict:
    return {**world, 'active': world['id'] == data['active'], 'first': not world['folder'],
            'companions': companions_in(world_path(database.home, world))}


def view(database: Database) -> dict:
    data = registry(database)
    active = found(data['worlds'], data['active'], 'world')
    personas = [{**persona, 'active': persona['id'] == active['persona_id'],
                 'worlds': [world_view(database, data, world) for world in
                            sorted(data['worlds'], key=lambda item: item['used_at'], reverse=True)
                            if world['persona_id'] == persona['id']]}
                for persona in data['personas']]
    return {'active_world_id': active['id'], 'active_persona_id': active['persona_id'],
            'world': world_view(database, data, active),
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
    carry_settings(target, previous, database.now())
    data['active'], world['used_at'] = world['id'], database.now()
    database.world = world['id']
    save(database.root, data)
    with database.connect(write=True) as connection:
        write_persona(connection, found(data['personas'], world['persona_id'], 'persona'), database.now())
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
    """A grown-up townsperson to be the new world's first companion, the same one for the same world."""
    people = [sheet for place in data['places'] for sheet in townsfolk.at_place(data, place['id'])
              if STARTER_AGES[0] <= sheet['age'] <= STARTER_AGES[1]]
    return min(people, key=lambda sheet: generators.unit(sheet['key'], 'starter', seed), default=None)


def starter(connection, data: dict, seed: str, timestamp: str, today: date):
    """Their profile from their town sheet, no model involved (companion/cast.py): a friend the user knows from
    around town. The user can change them, find someone on Matchlight or make their own afterwards."""
    sheet = starter_sheet(data, seed)
    if sheet is None:
        return
    met = {'match': None, 'meetings': [], 'focus': None, 'in_story': None}
    definition = cast.profile(data, sheet, met, today) | {'starting_closeness': 2}
    made = characters.create_in(connection, timestamp, CharacterDefinition.model_validate(definition),
                                'The first companion of a new world.')
    connection.execute('UPDATE companions SET townsfolk_key=?, town_seed=? WHERE id=?',
                       (sheet['key'], data.get('town', ''), made['id']))


def build(database: Database, path: Path, persona: dict, city_id: str, seed: str):
    """A new world's database: the user's settings, the persona, its own townsfolk and a starter companion."""
    restore.settle(database.path)
    made = Database(path, AppClock(database.clock.base))
    carry_settings(path, database.path, made.now())
    with made.connect(write=True) as connection:
        write_persona(connection, persona, made.now())
        data = dating.city_for(connection, city_id, seed[:16])
        today = made.clock.now().astimezone(zone(data['timezone'])).date()
        starter(connection, data, seed, made.now(), today)


def unique_name(data: dict, wanted: str) -> str:
    taken = {world['name'] for world in data['worlds']}
    if wanted not in taken:
        return wanted
    return next(f'{wanted} {number}' for number in range(2, 1000) if f'{wanted} {number}' not in taken)


def create_world(database: Database, persona_id: str | None = None, name: str | None = None,
                 city_id: str | None = None) -> dict:
    """A new world for a persona (the active one by default), in the current city unless another is named."""
    data = registry(database)
    active = found(data['worlds'], data['active'], 'world')
    persona = found(data['personas'], persona_id or active['persona_id'], 'persona')
    with database.connect() as connection:
        city = story.city_data(connection, city_id) if city_id else city_of(connection)
    world_id = identifier()
    folder = f'{FOLDER}/{world_id}'
    path = database.root / folder / DATABASE
    try:
        build(database, path, persona, city['id'], world_id)
    except BaseException:
        shutil.rmtree(path.parent, ignore_errors=True)
        raise
    timestamp = database.now()
    world = {'id': world_id, 'name': (name or '').strip()[:80] or unique_name(data, city['name']),
             'persona_id': persona['id'], 'folder': folder, 'city_id': city['id'],
             'created_at': timestamp, 'used_at': timestamp}
    data['worlds'].append(world)
    save(database.root, data)
    return world_view(database, data, world)


# Personas -------------------------------------------------------------------------------------------------

def create_persona(database: Database, body) -> dict:
    """A new persona with a world of their own. Who the user is stays theirs to say (Vanta, 2026-10-09): the name
    they typed, and nothing the app makes up; what they leave blank stays blank. The world is decided for them."""
    name = (body.name or '').strip()
    require(bool(name), 'Give the new persona a name.', 422)
    data = registry(database)
    persona_id = identifier()
    persona = {'id': persona_id, 'name': name, 'gender': body.gender or '', 'age': body.age,
               'about': (body.about or '').strip(), 'birthday': body.birthday or '', 'created_at': database.now()}
    data['personas'].append(persona)
    save(database.root, data)
    world = create_world(database, persona_id)
    return {**persona, 'worlds': [world]}


def update_persona(database: Database, persona_id: str, body) -> dict:
    data = registry(database)
    persona = found(data['personas'], persona_id, 'persona')
    changes = body.model_dump(exclude_unset=True)
    if 'name' in changes:
        changes['name'] = (changes['name'] or '').strip()
    persona.update({key: '' if value is None and key != 'age' else value for key, value in changes.items()})
    save(database.root, data)
    active = found(data['worlds'], data['active'], 'world')
    if active['persona_id'] == persona_id:
        with database.connect(write=True) as connection:
            write_persona(connection, persona, database.now())
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
                write_persona(connection, persona, database.now())
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
