"""Back when (Feature Hit List #79, 1.2 "The Dark Backward"): go back to when you and a companion were younger.

One button on a companion's Character page. The app offers three moments it picked from what's stored (`moments`):
when the two of you first met, the year before a big step (the wedding, moving in), a round age of theirs, the year
before a life chapter; the user can pick any other year back to 1990 instead. Picking one makes a new world named
"Back when · 2009" in the same city, with the same town, whose clock runs in that year at real speed
(companion/world_year.py), and opens it. The world the user leaves stays as it was, and switching between the two
works as for any worlds.

The new world is made from the companion's rows, the ones a saved companion carries (companion/carry.py), without
what happened between the two of you: no chats, memories, feed or pictures, so what happens there stays there. Who
they are comes along, with their circle, family, kids, home and love life, rolled back to that day by rules
(companion/back_when_rollback.py): everyone younger, later chapters undone, the two of you strangers, and work that
fits their age then (companion/back_when_careers.py); the town's people are younger too (companion/world/townsfolk.py).
"Work it out from our history" (off by default, Vanta 2026-10-28) keeps wherever the two of you were by then instead,
and strangers before the day you met. The persona is younger there too (the `back_when` row). Anything can be changed afterward, as
in any world.

It goes back only to years when both of them were grown up (18), and only from a world in the present. Nothing here
calls a model.
"""
import shutil
from datetime import date

from companion import back_when_careers as careers
from companion import back_when_rollback as rollback
from companion import carry, characters, world_year, worlds
from companion.clock import AppClock, stamp, zone
from companion.database import Database, decode, many, optional
from companion.errors import require
from companion.life import ages
from companion.models import CharacterDefinition
from companion.world import lifespans

NAME = 'Back when · {year}'
# Their rows that come along: who they are, their people, home and love life. The rest (chats, memories, the feed,
# pictures, and the simulation's cursors, which start again from the world's own today) stays behind.
KEPT = frozenset({
    'companions', 'character_versions', 'appearance_versions', 'appearance_current', 'lora_references',
    'character_sheets', 'companion_voices', 'study_imports', 'their_looks', 'step_settings', 'timelines',
    'birth_dates', 'circle_people', 'family_trees', 'circle_children', 'companion_kids', 'love_partners',
    'relationship_steps', 'life_chapters', 'losses', 'home_items', 'home_state',
})
# A moment's year before a step between the two of you.
BEFORE_STEP = {'married': 'Before the wedding', 'engaged': 'Before you got engaged', 'moving_in': 'Before you moved in',
               'key': 'Before you swapped keys', 'their_people': 'Before you met their people',
               'love': 'Before you said "I love you"', 'exclusive': 'Before you were together',
               'best_friends': 'Before you were best friends', 'trip': 'Before your first trip together',
               'wedding_party': 'Before their wedding'}
BEFORE_CHAPTER = {'new_job': 'Before the new job', 'move': 'Before the move', 'pet': 'Before the pet',
                  'school': 'Before going back to school', 'career_change': 'Before the career change',
                  'buy_place': 'Before buying their place', 'retire': 'Before retiring'}
# Round ages a moment can be, in the order offered.
ROUND_AGES = (25, 30, 21, 35, 40, 45, 50)
MOMENTS = 3
GROWN_UP = 'Back when only goes back to years when you were both grown up.'


# What the app knows -------------------------------------------------------------------------------------------------

def facts(database, companion_id: str | None = None) -> dict:
    """The companion, today where they live, their age and birth date, how the two of you stand and their chapters,
    read in the world the user is in now."""
    with database.connect() as connection:
        require(not world_year.past(connection), 'Back when starts from a world in the present.', 409)
        companion = characters.by_id(connection, companion_id) if companion_id else characters.require_current(connection)
        require(companion is not None, 'That companion is no longer in this world.', 404)
        definition = companion['version']['definition']
        today = database.clock.now().astimezone(zone(companion['version']['timezone'])).date()
        age = ages.companion_age(connection, companion['id'], definition, today)
        birthday = ages.own_birthday(companion['id'], definition)
        born = ages.born_from(age, birthday, today) if age is not None else None
        pair = rollback.pair_dates(connection, companion, today, born)
        later = many(connection, 'SELECT kind, started_on FROM life_chapters WHERE timeline_id=? AND undone_at IS NULL '
                     'ORDER BY started_on DESC', (companion['active_timeline_id'],))
    return {'companion': companion, 'today': today, 'age': age, 'born': born, 'birthday': birthday,
            'ageless': lifespans.ageless(definition), 'pair': pair, 'chapters': later}


def persona_of(database) -> dict:
    data = worlds.registry(database)
    world = worlds.found(data['worlds'], data['active'], 'world')
    return worlds.found(data['personas'], world['persona_id'], 'persona')


def age_then(found: dict, year: int) -> int | None:
    """Their age on today's date in `year`; None when it can't be told (they don't age, or have no adult age)."""
    if found['ageless'] or found['born'] is None:
        return None
    return ages.age_on(found['born'], found['birthday'], world_year.same_day(found['today'], year))


def grown(age: int | None) -> bool:
    return age is None or age >= ages.ADULT


def earliest(found: dict, persona: dict) -> int:
    """The first year both of them were grown up, and never before 1990."""
    latest = found['today'].year - 1
    if found['age'] is None and not found['ageless']:
        return latest + 1  # No adult age to count back from.
    year = world_year.EARLIEST
    while year <= latest and not grown(age_then(found, year)):
        year += 1
    if persona.get('age'):
        year = max(year, found['today'].year - persona['age'] + ages.ADULT)
    return year


# Moments ------------------------------------------------------------------------------------------------------------

def year_from(today: date, day: date) -> int:
    """The first year whose today falls on or after `day`."""
    return day.year if world_year.same_day(today, day.year) >= day else day.year + 1


def year_before(today: date, day: date) -> int:
    """The last year whose today falls before `day`."""
    return day.year if world_year.same_day(today, day.year) < day else day.year - 1


def candidates(found: dict) -> list[dict]:
    """Every moment worth offering, best first."""
    today, pair, first = found['today'], found['pair'], found['companion']['version']['name'].split()[0]
    found_moments = []
    if pair['met']:
        found_moments.append({'key': 'met', 'label': 'When you first met', 'year': year_from(today, pair['met'])})
    for item in reversed(pair['steps'][1:]):
        if item['step'] in BEFORE_STEP:
            found_moments.append({'key': f"before:{item['step']}", 'label': BEFORE_STEP[item['step']],
                                  'year': year_before(today, item['on'])})
            break
    for chapter in found['chapters']:
        if chapter['kind'] in BEFORE_CHAPTER:
            found_moments.append({'key': f"chapter:{chapter['kind']}", 'label': BEFORE_CHAPTER[chapter['kind']],
                                  'year': year_before(today, date.fromisoformat(chapter['started_on']))})
    for age in ROUND_AGES if found['born'] and not found['ageless'] else ():
        year = found['born'].year + age
        year += age_then(found, year) < age
        found_moments.append({'key': f'age:{age}', 'label': f'When {first} was {age}', 'year': year})
    return found_moments


def moments(database, companion_id: str | None = None) -> dict:
    """The Back when sheet: three moments the app picked, the years the user can pick instead, and the "Work it out
    from our history" switch, off."""
    found, persona = facts(database, companion_id), persona_of(database)
    low, high = earliest(found, persona), found['today'].year - 1
    picked = []
    for moment in candidates(found):
        if low <= moment['year'] <= high and moment['year'] not in {item['year'] for item in picked}:
            picked.append(moment | {'name': NAME.format(year=moment['year']), 'age': age_then(found, moment['year'])})
        if len(picked) == MOMENTS:
            break
    companion = found['companion']
    return {'companion_id': companion['id'], 'name': companion['version']['name'], 'moments': picked,
            'earliest': low, 'latest': high, 'available': low <= high, 'from_history': False,
            'reason': None if low <= high else GROWN_UP}


# Making the world ---------------------------------------------------------------------------------------------------

def their_rows(connection, companion: dict) -> dict[str, dict]:
    """Their rows that come along, from their active timeline only."""
    timeline_id = companion['active_timeline_id']
    rows = {}
    for table, data in carry.gathered(connection, companion['id']).items():
        if table not in KEPT:
            continue
        columns = data['columns']
        key = 'id' if table == 'timelines' else 'timeline_id' if 'timeline_id' in columns else None
        kept = [row for row in data['rows'] if key is None or row[columns.index(key)] == timeline_id]
        rows[table] = {'columns': columns, 'rows': kept}
    return carry.pruned(connection, rows)


def file_names(connection, companion_id: str) -> list[str]:
    """Their reference pictures and character sheets: how they look comes along; chat pictures stay."""
    return [name for name in carry.file_names(connection, companion_id)
            if name.startswith(('lora/references/', 'images/sheets/'))]


def build(state, year: int, from_history: bool = False, companion_id: str | None = None) -> dict:
    """Make the Back when world for `year` and open it."""
    database = state.database
    found, persona = facts(database, companion_id), persona_of(database)
    low, high = earliest(found, persona), found['today'].year - 1
    require(low <= high, GROWN_UP, 409)
    require(low <= year <= high, f'Pick a year from {low} to {high}.', 422)
    companion = found['companion']
    with database.connect() as connection:
        rows = their_rows(connection, companion)
        names = file_names(connection, companion['id'])
    data = worlds.registry(database)
    active = worlds.found(data['worlds'], data['active'], 'world')
    world = worlds.create_world(database, persona['id'], worlds.unique_name(data, NAME.format(year=year)),
                                active.get('city_id'), year=year)
    try:
        path = worlds.world_path(database.home, world)
        copy_files(database.path.parent, path.parent, names)
        made = Database(path, AppClock(database.clock.base))
        settle(made, found, rows, year, from_history, data['active'])
    except BaseException:
        discard(database, world)
        raise
    finally:
        database.follow()  # Opening it pointed the app-wide clocks at the new world.
    return worlds.switch(state, world['id'])


def copy_files(source, target, names: list[str]):
    for name in names:
        if (source / name).is_file():
            (target / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / name, target / name)


def discard(database, world: dict):
    """A Back when world that could not be made goes, with its folder."""
    shutil.rmtree(worlds.world_path(database.home, world).parent, ignore_errors=True)
    data = worlds.registry(database)
    data['worlds'] = [item for item in data['worlds'] if item['id'] != world['id']]
    worlds.save(database.root, data)


def settle(made: Database, found: dict, rows: dict, year: int, from_history: bool, from_world: str):
    """Their rows in the new world, rolled back to its today."""
    now, companion = made.clock.now(), found['companion']
    day = world_year.same_day(found['today'], year)
    mine = rows['companions']
    for row in mine['rows']:  # The main character there, whoever they were here.
        for column, value in (('slot', 1), ('stepped_back_at', None)):
            if column in mine['columns']:
                row[mine['columns'].index(column)] = value
    with made.connect(write=True) as connection:
        connection.execute('PRAGMA defer_foreign_keys=ON')  # Checked at commit, once every row is in.
        carry.insert(connection, rows)
        stand = rollback.roll_back(connection, companion['id'], day, found['today'],
                                   found['pair'] if from_history else None, now)
        younger(connection, found, year, stand, now)
        careers.circle_then(connection, companion['active_timeline_id'], companion['version']['definition'], year,
                            stamp(now))
        restamp(connection, now)
        connection.execute('INSERT INTO back_when (id, companion_id, name, from_world_id, year, from_history, '
                           'persona_years, created_at) VALUES (1, ?, ?, ?, ?, ?, ?, ?)',
                           (companion['id'], companion['version']['name'], from_world, year, int(from_history),
                            found['today'].year - year, stamp(now)))


def younger(connection, found: dict, year: int, stand: dict, now):
    """A new character version for that year: their age then, the age in their own words, and how the two of them
    stand. Their stored birth date is worked out again from it (companion/life/ages.py)."""
    companion = found['companion']
    row = optional(connection, 'SELECT definition, number FROM character_versions WHERE id=?',
                   (companion['active_version_id'],))
    definition = decode(row['definition'])
    then = age_then(found, year)
    if then is not None and found['age'] is not None and ages.ADULT <= then <= 120:
        definition = rollback.younger_words(definition, found['age'], then)
        definition['looks'] = {**(definition.get('looks') or {}), 'age': then}
        connection.execute("DELETE FROM birth_dates WHERE kind='companion' AND person_key=?", (companion['id'],))
    definition = rollback.relationship_then(definition, stand)
    definition = careers.companion_then(connection, definition, then, f"{companion['id']}|back-when:{year}")
    top = max((number[0] for number in connection.execute(
        'SELECT number FROM character_versions WHERE companion_id=?', (companion['id'],))), default=row['number'])
    version_id = characters.insert_version(connection, companion['id'], top + 1,
                                           CharacterDefinition.model_validate(definition), f'Back when: {year}.',
                                           stamp(now))
    connection.execute('UPDATE companions SET active_version_id=? WHERE id=?', (version_id, companion['id']))


def restamp(connection, now):
    """Bookkeeping stamps from later (when a row was made or changed in the present) become the world's now."""
    moment = stamp(now)
    for table in sorted(KEPT):
        for column in (item[1] for item in connection.execute(f'PRAGMA table_info({table})')):
            if column.endswith('_at'):
                connection.execute(f'UPDATE {table} SET {column}=? WHERE {column}>?',  # noqa: S608 - names from KEPT
                                   (moment, moment))
    day = now.date().isoformat()
    connection.execute('UPDATE companion_kids SET since=? WHERE since>?', (day, day))
    connection.execute('UPDATE home_state SET started=? WHERE started>?', (day, day))
