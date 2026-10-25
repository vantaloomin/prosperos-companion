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

Before anything is saved, `inspect` lists what the file holds: the character, their picture, their lorebook entry by
entry, and the parts left out. Everything is ticked, so one click imports it all; the user can untick parts, such as
importing only the lorebook, for the world or for a companion they already have. A character who is already one of
the user's companions (by name) starts unticked, with their lorebook going to them.
"""
import hashlib
import re

from companion import cast, characters, dating, worlds
from companion.clock import zone
from companion.database import decode, encode, identifier
from companion.errors import DomainError, require
from companion.images.adapters.base import AdapterError
from companion.images.storage import sniff
from companion.imports import formats
from companion.lora import references
from companion.models import CharacterDefinition, ImportPick
from companion.world import generators, personality, townsfolk

BACKGROUND = 12000
LIMITS = {'personality': 8000, 'voice': 4000, 'appearance': 4000, 'in_photos': 2000}
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


def texts(character: dict, name: str) -> tuple[dict, str]:
    """Their written fields with the card's macros spelled out, and the whole description."""
    description = spelled(character['description'], name)
    backstory = spelled(character.get('backstory', ''), name)
    if backstory:  # Marinara Engine keeps a backstory apart from the description.
        description = f'{description}\n\nBackstory:\n{backstory}'.strip()
    examples = spelled(character['mes_example'], name)
    return {'name': name, 'background': description[:BACKGROUND],
            'appearance': spelled(character.get('appearance', ''), name)[:LIMITS['appearance']],
            'in_photos': spelled(character.get('in_photos', ''), name)[:LIMITS['in_photos']],
            'personality': spelled(character['personality'], name)[:LIMITS['personality']],
            'voice': f'How they write, from their examples:\n{examples}'[:LIMITS['voice']] if examples else ''}, \
        description


def definition(connection, database, character: dict, focus: dict | None) -> tuple[CharacterDefinition, str]:
    """Their definition, and any description past the background's limit (kept as lore instead)."""
    name = character['name'].strip()[:120]
    values = life(connection, database, character, focus)
    fields, description = texts(character, name)
    made = characters.named(connection, CharacterDefinition.model_validate(values | fields))
    if not name:  # A nameless card's "{{char}} restores old boats" reads with the name they were given.
        fields, description = texts(character, made.name)
        made = CharacterDefinition.model_validate(values | fields)
    made = CharacterDefinition.model_validate({**made.model_dump(), 'personality_sliders': card_sliders(fields, description)})
    return made, description[BACKGROUND:].strip()


def card_sliders(fields: dict, description: str) -> dict | None:
    """The personality sliders a card's own words settle (companion/world/personality.py). Most cards say who
    {{char}} is in the description, which becomes the background, and the background is not read for sliders."""
    found = personality.from_words(f"{fields['personality']} {description}")
    return {key: {'level': level, 'source': 'idea'} for key, level in found.items()} or None


def card_sliders_upgrade(connection):
    """Companions imported before the card's description was read for their sliders (they have none stored) read it
    now, from the personality and background the import kept. Only sliders still Rolled change; From your idea stays.
    The active version is updated in place, since nothing the user said changed; once stored, it is never read again,
    and anyone whose card settles nothing is left as they were."""
    rows = connection.execute(
        "SELECT v.id, v.companion_id, v.definition FROM companions c JOIN character_versions v "
        "ON v.id = c.active_version_id WHERE EXISTS (SELECT 1 FROM character_versions f WHERE f.companion_id = c.id "
        "AND f.number = 1 AND f.note LIKE 'Imported from %' AND f.note NOT LIKE 'Imported from Prospero''s Study%')"
    ).fetchall()
    for version_id, companion_id, stored in rows:
        definition = decode(stored)
        sliders = None if definition.get('personality_sliders') else card_read(definition, companion_id)
        if sliders:
            connection.execute('UPDATE character_versions SET definition=? WHERE id=?',
                               (encode({**definition, 'personality_sliders': sliders}), version_id))


def card_read(definition: dict, seed: str) -> dict | None:
    """Their sliders with the Rolled ones the card's words settle now From your idea (even at the same stop), the rest rolled
    again around them by seed; None when the card's words change nothing."""
    current = personality.settle(definition, seed)
    words = card_sliders({'personality': definition.get('personality') or ''}, definition.get('background') or '') or {}
    read = {key: value for key, value in words.items() if current[key]['source'] == 'rolled'}
    if not read:
        return None
    kept = {key: value for key, value in current.items() if value['source'] != 'rolled'}
    return personality.settle({**definition, 'personality_sliders': {**kept, **read}}, seed)


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


def left_out(data: bytes | None, shape) -> str | None:
    """Why the file's picture did not come along, when it had one."""
    if not data or shape:
        return None
    try:
        kind = sniff(data)[0]
    except (AdapterError, ValueError):
        kind = None
    if kind == 'webp':
        return ("Their picture is a WebP image, which reference pictures can't use yet, so it was left out. Saved "
                'as PNG or JPEG, it can be added with their reference pictures.')
    return "Their picture couldn't be used, so it was left out."


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


def entry_view(entry: dict) -> dict:
    """One lorebook entry as the preview lists it: enough to tell it apart, not the whole text."""
    return {'title': entry['title'], 'keywords': entry['keywords'][:6], 'always': entry['always'],
            'enabled': entry['enabled'], 'pattern': entry['pattern'], 'text': entry['text'][:200]}


def book_view(book: dict | None) -> dict | None:
    return book and {'name': book['name'], 'format': book['format'],
                     'entries': [entry_view(entry) for entry in book['entries']]}


def same_named(companions: list[dict], name: str) -> dict | None:
    wanted = name.strip().casefold()
    return next((member for member in companions if wanted and member['name'].strip().casefold() == wanted), None)


def inspect(database, filename: str, encoded: str) -> dict:
    """What one file holds, for the page to list with everything ticked; nothing is saved. `already` names a
    companion the character already is, whose lorebook it then is by default."""
    found = formats.read(filename, encoded)
    companions = [{'id': member['id'], 'name': member['name']} for member in cast.members(database)]
    character = found['character']
    picture = None
    if found['picture']:
        shape = checked_picture(found['picture'])
        picture = {'usable': bool(shape), 'note': left_out(found['picture'], shape),
                   'portrait': bool(found.get('portrait'))}
    view, already = None, None
    if character is not None:
        name = character['name'].strip()[:120]
        description = texts(character, name)[1]
        view = {'name': name, 'about': description[:300], 'more_about': len(description) > BACKGROUND}
        already = same_named(companions, name)
    return {'format': found['format'], 'character': view, 'picture': picture, 'book': book_view(found['book']),
            'unused': found.get('unused', []), 'companions': companions, 'already': already}


def chosen(book: dict | None, pick: ImportPick) -> dict | None:
    """The file's lorebook with only the ticked entries, or None when none are."""
    if not book or not pick.book:
        return None
    if pick.entries is not None:
        wanted = sorted({number for number in pick.entries if 0 <= number < len(book['entries'])})
        book = {**book, 'entries': [book['entries'][number] for number in wanted]}
    return book if book['entries'] else None


def owner(connection, lore_for: str, new_id: str | None) -> dict | None:
    """Whose the lorebook becomes: {id, name} for a companion, or None for everyone in the world."""
    if lore_for == 'world' or (lore_for in ('', 'new') and new_id is None):
        return None
    found = characters.by_id(connection, new_id if lore_for in ('', 'new') else lore_for)
    require(found is not None, 'That companion is no longer here. Choose whose lore it is again.', 404)
    return {'id': found['id'], 'name': found['version']['name']}


def bring(database, filename: str, encoded: str, pick: ImportPick | None = None) -> dict:
    """Import the ticked parts of one character or lorebook file (all of it by default). Returns what was made, for
    the page to say so."""
    pick = pick or ImportPick()
    found = formats.read(filename, encoded)
    book = chosen(found['book'], pick)
    if found['character'] is None or not pick.character:
        require(book is not None, 'Tick something to import.', 422)
        with database.connect(write=True) as connection:
            mine = owner(connection, pick.lore_for, None)
            added = add_book(connection, database.now(), book, mine and mine['id'], filename)
        return {'format': found['format'], 'companion': None, 'book': added | {'owner': mine and mine['name']},
                'picture': False}
    found = {**found, 'book': book, 'picture': found['picture'] if pick.picture else None}
    shape = checked_picture(found['picture'])
    stored = store_picture(database, found['picture'], shape[0]) if shape else None
    try:
        return bring_character(database, filename, found, stored, shape, pick.lore_for) | {
            'picture_note': left_out(found['picture'], shape)}
    except BaseException:
        if stored:
            (references.directory(database) / stored[1]).unlink(missing_ok=True)
        raise


def add_lore(connection, timestamp: str, book: dict | None, made: CharacterDefinition, new: tuple[str, str],
             lore_for: str, filename: str) -> dict | None:
    """Their lorebook, for them or whoever the user chose. What did not fit their background (`new` holds their id
    and that text) is about them, so it stays theirs either way."""
    companion_id, overflow = new
    mine = owner(connection, lore_for, companion_id)
    theirs = mine is not None and mine['id'] == companion_id
    if overflow and not theirs:
        add_book(connection, timestamp, with_overflow(None, made.name, overflow), companion_id, filename)
    book = with_overflow(book, made.name, overflow) if theirs else book
    if not book:
        return None
    return add_book(connection, timestamp, book, mine and mine['id'], filename) | {'owner': mine and mine['name']}


def bring_character(database, filename: str, found: dict, stored, shape, lore_for: str = '') -> dict:
    timestamp = database.now()
    with database.connect(write=True) as connection:
        focus = characters.current(connection)
        made, overflow = definition(connection, database, found['character'], focus)
        companion_id = add_companion(connection, timestamp, made, f"Imported from {filename} ({found['format']})"[:500],
                                     focus)
        added = add_lore(connection, timestamp, found['book'], made, (companion_id, overflow), lore_for, filename)
        if stored:
            add_picture(connection, timestamp, companion_id, stored, found['picture'], shape, filename)
            if found.get('portrait'):  # An app's own avatar is already their profile picture there.
                connection.execute('UPDATE companions SET portrait_reference_id=? WHERE id=?',
                                   (stored[0], companion_id))
        return {'format': found['format'], 'companion': characters.current(connection), 'book': added,
                'picture': bool(stored), 'portrait': bool(stored and found.get('portrait')),
                'stepped_back': focus['version']['name'] if focus else None}
