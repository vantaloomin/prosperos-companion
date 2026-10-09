"""Bring your characters: a character file from another app becomes a companion living in this world.

The file (companion/imports/formats.py) gives who they are: name, description, personality and how they write.
The world gives the rest, the way it does for a world's first companion (companion/worlds.py `starter`): a
grown-up townsperson's sheet, picked by the character's name, lends a job, a neighborhood, a routine and the
city's timezone (companion/cast.py `profile`), so they have a life from the first day. The town keeps that
townsperson; the sheet is only a template. No model is asked and there is no review step: the user changes
anything afterwards on the Character page ("The world exists outside of User").

The character's own lorebook becomes theirs, a lorebook file on its own becomes the world's
(companion/lore.py), and a card's picture is kept with their reference pictures, marked "Not stated" until
the user says where it came from (as the Study import does, companion/imports/study.py). A scenario, greetings
and creator's notes set up someone else's story, so they are not used: the companion's life starts here.
"""
import hashlib
import re

from companion import cast, characters, dating, worlds
from companion.clock import zone
from companion.database import encode, identifier
from companion.errors import DomainError
from companion.imports import formats
from companion.lora import references
from companion.models import CharacterDefinition
from companion.world import generators, townsfolk

BACKGROUND = 12000
LIMITS = {'personality': 8000, 'voice': 4000}
MACROS = (('{{char}}', None), ('<BOT>', None), ('{{user}}', 'the user'), ('<USER>', 'the user'))


def spelled(text: str, name: str) -> str:
    for macro, value in MACROS:
        text = text.replace(macro, value or name or 'they')
    return text.strip()


def pronouns_of(character: dict) -> str | None:
    words = re.findall(r'[a-z]+', f"{character['description']} {character['personality']}".lower())
    she, he = (sum(word in group for word in words) for group in (('she', 'her', 'hers'), ('he', 'him', 'his')))
    return 'she' if she > he else 'he' if he > she else None


def template(data: dict, character: dict) -> dict | None:
    """A grown-up townsperson whose life they borrow: the same one for the same name, matching pronouns when the
    description makes them clear."""
    people = [sheet for place in data['places'] for sheet in townsfolk.at_place(data, place['id'])
              if worlds.STARTER_AGES[0] <= sheet['age'] <= worlds.STARTER_AGES[1]]
    wanted = pronouns_of(character)
    if wanted:
        people = [sheet for sheet in people if (sheet.get('pronouns') or '').startswith(f'{wanted}/')] or people
    seed = character['name'].strip().casefold() or character['description'][:200]
    return min(people, key=lambda sheet: generators.unit(sheet['key'], 'imported', seed), default=None)


def life(connection, database, character: dict, focus: dict | None) -> dict:
    """Their job, home, routine and city, from the town; empty when the city has no one to borrow from."""
    data = worlds.city_of(connection)
    if focus and focus.get('town_seed'):
        data = dating.city_for(connection, data['id'], focus['town_seed'])
    sheet = template(data, character)
    if sheet is None:
        return {'home_city': data['id'], 'timezone': data['timezone']}
    today = database.clock.now().astimezone(zone(data['timezone'])).date()
    met = {'match': None, 'meetings': [], 'focus': None, 'in_story': None}
    made = cast.profile(data, sheet, met, today)
    keep = ('skills', 'interests', 'routine', 'location', 'home_city', 'timezone', 'schedule', 'life_themes', 'money')
    # "34. Works as a nurse. Lives in Fells Point." without the townsperson's age.
    return {key: made[key] for key in keep} | {'identity': made['identity'].split('. ', 1)[-1]}


def definition(connection, database, character: dict, focus: dict | None) -> tuple[CharacterDefinition, str]:
    """Their definition, and any description past the background's limit (kept as lore instead)."""
    name = character['name'].strip()[:120]
    description = spelled(character['description'], name)
    examples = spelled(character['mes_example'], name)
    values = life(connection, database, character, focus) | {
        'name': name, 'background': description[:BACKGROUND],
        'personality': spelled(character['personality'], name)[:LIMITS['personality']],
        'voice': f'How they write, from their examples:\n{examples}'[:LIMITS['voice']] if examples else ''}
    made = characters.named(connection, CharacterDefinition.model_validate(values))
    return made, description[BACKGROUND:].strip()


def add_companion(connection, timestamp: str, made: CharacterDefinition, note: str, focus: dict | None) -> str:
    """The new companion, who becomes the one the app is about; whoever was steps back with everything they have."""
    if focus is None:
        return characters.create_in(connection, timestamp, made, note)['id']
    companion_id, timeline_id = identifier(), identifier()
    connection.execute('INSERT INTO companions (id, slot, town_seed, created_at) VALUES (?, NULL, ?, ?)',
                       (companion_id, focus.get('town_seed') or '', timestamp))
    version_id = characters.insert_version(connection, companion_id, 1, made, note, timestamp)
    connection.execute("INSERT INTO timelines (id, companion_id, status, created_at) VALUES (?, ?, 'active', ?)",
                       (timeline_id, companion_id, timestamp))
    connection.execute('UPDATE companions SET active_version_id=?, active_timeline_id=? WHERE id=?',
                       (version_id, timeline_id, companion_id))
    cast.step_back(connection, timestamp, companion_id)
    return companion_id


def add_book(connection, timestamp: str, book: dict, companion_id: str | None, filename: str) -> dict:
    book_id = identifier()
    connection.execute('INSERT INTO lore_books (id, companion_id, name, description, source_format, source_file, '
                       'created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                       (book_id, companion_id, book['name'], book['description'], book['format'], filename[:260],
                        timestamp))
    for position, entry in enumerate(book['entries']):
        connection.execute('INSERT INTO lore_entries (id, book_id, position, title, text, keywords, always, pattern, '
                           'enabled) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                           (identifier(), book_id, position, entry['title'], entry['text'], encode(entry['keywords']),
                            int(entry['always']), int(entry['pattern']), int(entry['enabled'])))
    return {'id': book_id, 'name': book['name'], 'world': companion_id is None, 'entries': len(book['entries']),
            'off': sum(not entry['enabled'] for entry in book['entries'])}


def with_overflow(book: dict | None, name: str, overflow: str) -> dict | None:
    """Their book, with any description that did not fit the background as an always-on entry."""
    if not overflow:
        return book
    entry = {'title': f'More about {name}', 'text': overflow[:20000], 'keywords': [], 'always': True,
             'enabled': True, 'pattern': False}
    book = book or {'name': f'{name} lore', 'description': '', 'format': 'Character card', 'entries': []}
    return {**book, 'entries': [entry, *book['entries']]}


def checked_picture(data: bytes | None) -> tuple[str, int, int] | None:
    if not data or len(data) > references.MAX_BYTES:
        return None
    try:
        return references.checked_image(data)
    except DomainError:
        return None


def store_picture(database, data: bytes, kind: str) -> tuple[str, str]:
    reference_id = identifier()
    name = f'{reference_id}.{kind}'
    target = references.directory(database) / name
    partial = target.with_name(name + '.partial')
    partial.write_bytes(data)
    partial.replace(target)
    return reference_id, name


def add_picture(connection, timestamp, companion_id, stored, data, shape, filename) -> None:
    (reference_id, file), (kind, width, height) = stored, shape
    connection.execute(
        'INSERT INTO lora_references (id, companion_id, file, original_name, media_type, sha256, width, height, '
        'bytes, source_note, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (reference_id, companion_id, file, filename[:260], references.TYPES[kind], hashlib.sha256(data).hexdigest(),
         width, height, len(data), f'The picture in {filename}'[:1000], timestamp, timestamp))


def bring(database, filename: str, encoded: str) -> dict:
    """Import one character or lorebook file. Returns what was made, for the page to say so."""
    found = formats.read(filename, encoded)
    if found['character'] is None:
        with database.connect(write=True) as connection:
            book = add_book(connection, database.now(), found['book'], None, filename)
        return {'format': found['format'], 'companion': None, 'book': book, 'picture': False}
    shape = checked_picture(found['picture'])
    stored = store_picture(database, found['picture'], shape[0]) if shape else None
    try:
        return bring_character(database, filename, found, stored, shape)
    except BaseException:
        if stored:
            (references.directory(database) / stored[1]).unlink(missing_ok=True)
        raise


def bring_character(database, filename: str, found: dict, stored, shape) -> dict:
    timestamp = database.now()
    with database.connect(write=True) as connection:
        focus = characters.current(connection)
        made, overflow = definition(connection, database, found['character'], focus)
        companion_id = add_companion(connection, timestamp, made, f"Imported from {filename} ({found['format']})"[:500],
                                     focus)
        book = with_overflow(found['book'], made.name, overflow)
        added = add_book(connection, timestamp, book, companion_id, filename) if book else None
        if stored:
            add_picture(connection, timestamp, companion_id, stored, found['picture'], shape, filename)
        return {'format': found['format'], 'companion': characters.current(connection), 'book': added,
                'picture': bool(stored), 'stepped_back': focus['version']['name'] if focus else None}
