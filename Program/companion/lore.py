"""Lore from imported lorebooks (companion/imports/characters.py): what a companion or their world knows as fact.

A book belongs to one companion, or to the whole world (`companion_id` NULL, from a lorebook file imported on
its own). Each entry is plain text with keywords. Always-on entries sit in the system prompt with the rest of
what rarely changes; an entry with keywords joins the notes sent with a reply only while one of them is in the
last few messages, as a whole word in any letter case, like Prospero's Study's literal keyword matching
(server/lore/matching.py at bbcbde4), or while the moment fits its "when" (companion/lore_moments.py: rain, night,
a holiday, being at work...). No pattern runs and no model picks entries.

A city file's own lore (its `lore` block) is the world's too while the companion lives there: it is read from the
city each time, so it follows the city into every world, and `city_lore_choices` keeps what the user changed.
"""
import re
import sqlite3
from pathlib import Path

from companion import lore_moments as moments
from companion.characters import require_current
from companion.clock import parse
from companion.database import decode, encode, identifier, many, one
from companion.errors import require

# The messages a keyword is looked for in, counting the one being answered.
SCAN_MESSAGES = 4
# At most this many keyword entries join one reply, first by book then by their order in it.
MAX_TRIGGERED = 8
MACROS = ('{{char}}', '<BOT>', '{{user}}', '<USER>')
# A Marinara world map's lorebook (companion/world/marinara.py) and the source title its city carries.
MAP_FORMAT = 'Marinara world map'
MAP_TITLE = 'Marinara world map: '
# A city file's lore, as a book: `city:<city id>`, and its entries `city:<city id>:<entry id>`.
CITY = 'city:'
CITY_FORMAT = 'Comes with the city'


def books_for(connection, companion_id: str) -> list[dict]:
    return many(connection, 'SELECT * FROM lore_books WHERE companion_id=? OR companion_id IS NULL '
                'ORDER BY companion_id IS NULL, created_at', (companion_id,))


def companion_city(connection, companion: dict) -> dict | None:
    from companion.almanac.context import city_for
    return city_for(connection, companion['version']['definition'])


def when_of(row: dict, holidays: list[str]) -> tuple[list[str], bool]:
    """(the entry's "when", whether the app read it from its keywords). Always-on entries have none."""
    if row['always']:
        return [], False
    if row.get('moment') is not None:
        return decode(row['moment']), False
    found = moments.guessed(decode(row['keywords']), holidays)
    return found, bool(found)


def entry_view(row: dict, scene: dict) -> dict:
    when, guessed = when_of(row, scene['holidays'])
    return {'id': row['id'], 'title': row['title'], 'text': row['text'], 'keywords': decode(row['keywords']),
            'always': bool(row['always']), 'pattern': bool(row['pattern']), 'enabled': bool(row['enabled']),
            'when': [{'key': key, 'label': moments.label(key, scene['city'])} for key in when],
            'when_guessed': guessed, 'fits_now': bool(row['enabled']) and moments.matches(when, scene['now'])}


def scene_for(connection, companion: dict, now) -> dict:
    """The companion's city, its holidays and what holds right now, for listing entries."""
    city = companion_city(connection, companion)
    return {'city': city, 'holidays': moments.holiday_names(city), 'now': moments.now_keys(connection, companion, now)}


def listing(database) -> dict:
    """The open companion's books and the world's (with the lore of the city they live in), with their entries, and
    what the "when" pickers offer."""
    with database.connect() as connection:
        companion = require_current(connection)
        scene = scene_for(connection, companion, parse(database.now()))
        found = []
        for book in books_for(connection, companion['id']):
            entries = many(connection, 'SELECT * FROM lore_entries WHERE book_id=? ORDER BY position', (book['id'],))
            found.append({'id': book['id'], 'name': book['name'], 'description': book['description'],
                          'source_format': book['source_format'], 'source_file': book['source_file'],
                          'world': book['companion_id'] is None, 'enabled': bool(book['enabled']), 'city': False,
                          'created_at': book['created_at'], 'entries': [entry_view(row, scene) for row in entries]})
        own = city_book(connection, scene['city'])
        if own:
            found.append({**own, 'entries': [entry_view(row, scene) for row in own['entries']]})
        return {'books': found, 'choices': moments.choices(scene['city'])}


def visible_book(connection, book_id: str) -> dict:
    companion = require_current(connection)
    book = one(connection, 'SELECT * FROM lore_books WHERE id=?', (book_id,))
    require(book['companion_id'] in (None, companion['id']), 'That lorebook belongs to another companion.', 404)
    return book


def set_book(database, book_id: str, enabled: bool) -> dict:
    with database.connect(write=True) as connection:
        if book_id.startswith(CITY):
            choose(connection, own_city(connection, book_id[len(CITY):]), '', enabled=int(enabled))
        else:
            visible_book(connection, book_id)
            connection.execute('UPDATE lore_books SET enabled=? WHERE id=?', (int(enabled), book_id))
    return listing(database)


def set_entry(database, entry_id: str, enabled: bool) -> dict:
    with database.connect(write=True) as connection:
        if entry_id.startswith(CITY):
            city_id, entry = city_entry(connection, entry_id)
            choose(connection, city_id, entry['key'], enabled=int(enabled))
        else:
            entry = one(connection, 'SELECT * FROM lore_entries WHERE id=?', (entry_id,))
            visible_book(connection, entry['book_id'])
            require(not (enabled and entry['pattern']), 'This entry finds its moment with a search pattern, which '
                    'the Companion cannot match, so it stays off. Copy what matters into an entry of your own.', 422)
            connection.execute('UPDATE lore_entries SET enabled=? WHERE id=?', (int(enabled), entry_id))
    return listing(database)


def set_when(database, entry_id: str, when: list[str]) -> dict:
    """The user's own "when" for an entry: it replaces the one the app read from its keywords or the city's."""
    kept = encode(moments.tidy(when))
    with database.connect(write=True) as connection:
        if entry_id.startswith(CITY):
            city_id, entry = city_entry(connection, entry_id)
            choose(connection, city_id, entry['key'], moment=kept)
        else:
            entry = one(connection, 'SELECT * FROM lore_entries WHERE id=?', (entry_id,))
            visible_book(connection, entry['book_id'])
            require(not entry['always'], 'An always-on entry is part of every reply, so it has no "when".', 422)
            connection.execute('UPDATE lore_entries SET moment=? WHERE id=?', (kept, entry_id))
    return listing(database)


def remove_book(database, book_id: str) -> dict:
    require(not book_id.startswith(CITY), 'This lore comes with the city, so it stays; switch it off instead.', 422)
    with database.connect(write=True) as connection:
        visible_book(connection, book_id)
        connection.execute('DELETE FROM lore_books WHERE id=?', (book_id,))
    return listing(database)


# A city file's own lore ---------------------------------------------------------------------------------------

def city_book(connection, city: dict | None) -> dict | None:
    """The lore block of the companion's city as a world book, with the user's changes in this world."""
    if not city or not city.get('lore'):
        return None
    chosen = {row['entry_id']: row for row in many(connection, 'SELECT * FROM city_lore_choices WHERE city_id=?',
                                                   (city['id'],))}
    book = chosen.get('')
    entries = []
    for item in city['lore']['entries']:
        mine = chosen.get(item['id']) or {}
        entries.append({'id': f"{CITY}{city['id']}:{item['id']}", 'key': item['id'], 'title': item['title'],
                        'text': item['text'], 'keywords': encode(item['keywords']), 'always': 0, 'pattern': 0,
                        'enabled': 1 if mine.get('enabled') is None else mine['enabled'],
                        'moment': mine.get('moment') if mine.get('moment') is not None else encode(item['when'])})
    return {'id': f"{CITY}{city['id']}", 'name': f"{city['name']} lore", 'description': city['lore']['credit'],
            'source_format': CITY_FORMAT, 'source_file': '', 'world': True, 'city': True, 'created_at': '',
            'enabled': not book or book['enabled'] is None or bool(book['enabled']), 'entries': entries}


def own_city(connection, city_id: str) -> str:
    city = companion_city(connection, require_current(connection))
    require(bool(city) and city['id'] == city_id and bool(city.get('lore')),
            'That lore belongs to a city the companion does not live in.', 404)
    return city_id


def city_entry(connection, entry_id: str) -> tuple[str, dict]:
    city_id, _, key = entry_id[len(CITY):].partition(':')
    own_city(connection, city_id)
    book = city_book(connection, companion_city(connection, require_current(connection)))
    entry = next((item for item in book['entries'] if item['key'] == key), None)
    require(entry is not None, 'There is no such lore entry.', 404)
    return city_id, entry


def choose(connection, city_id: str, entry_id: str, **change) -> None:
    connection.execute('INSERT OR IGNORE INTO city_lore_choices (city_id, entry_id) VALUES (?, ?)', (city_id, entry_id))
    for column, value in change.items():
        connection.execute(f'UPDATE city_lore_choices SET {column}=? WHERE city_id=? AND entry_id=?',
                           (value, city_id, entry_id))


# Lore that belongs to a city ------------------------------------------------------------------------------
# A world map's notes describe its city's places, so they follow the city: a new world in that city gets them too
# (companion/worlds.py), and deleting the city deletes them. Books from before `city_id` are known by the map's name.

def city_book_ids(connection, city: dict, schema: str = 'main') -> list[str]:
    title = ((city.get('sources') or {}).get('marinara') or {}).get('title') or ''
    name = title[len(MAP_TITLE):] if title.startswith(MAP_TITLE) else None
    rows = connection.execute(f'SELECT id FROM {schema}.lore_books WHERE companion_id IS NULL AND (city_id=? OR '
                              '(city_id IS NULL AND source_format=? AND name=?)) ORDER BY created_at',
                              (city['id'], MAP_FORMAT, name)).fetchall()
    return [row[0] for row in rows]


def forget_city(connection, city: dict) -> None:
    for book_id in city_book_ids(connection, city):
        connection.execute('DELETE FROM lore_books WHERE id=?', (book_id,))


def carry_city_lore(target: Path, source: Path, city: dict) -> None:
    """A new world in `city` gets the city's lore from the world it was made from."""
    connection = sqlite3.connect(target, isolation_level=None)
    try:
        connection.execute('ATTACH DATABASE ? AS kept', (str(Path(source).resolve()),))
        connection.execute('BEGIN IMMEDIATE')
        for book_id in [] if city_book_ids(connection, city) else city_book_ids(connection, city, 'kept'):
            new_id = identifier()
            connection.execute(
                'INSERT INTO main.lore_books (id, companion_id, name, description, source_format, source_file, '
                'enabled, created_at, city_id) SELECT ?, NULL, name, description, source_format, source_file, enabled, '
                'created_at, ? FROM kept.lore_books WHERE id=?', (new_id, city['id'], book_id))
            connection.execute(
                'INSERT INTO main.lore_entries (id, book_id, position, title, text, keywords, always, pattern, enabled) '
                'SELECT lower(hex(randomblob(16))), ?, position, title, text, keywords, always, pattern, enabled '
                'FROM kept.lore_entries WHERE book_id=?', (new_id, book_id))
        connection.execute('COMMIT')
    except BaseException:
        if connection.in_transaction:
            connection.execute('ROLLBACK')
        raise
    finally:
        connection.close()


def drop_orphaned(connection) -> None:
    """City lore whose city is gone (deleted in another world, `world_cities` follows the user)."""
    connection.execute('DELETE FROM lore_entries WHERE book_id IN (SELECT id FROM lore_books WHERE city_id IS NOT NULL '
                       'AND city_id NOT IN (SELECT id FROM world_cities))')
    connection.execute('DELETE FROM lore_books WHERE city_id IS NOT NULL AND city_id NOT IN (SELECT id FROM '
                       'world_cities)')


# In the prompt ------------------------------------------------------------------------------------------

def spelled(text: str, name: str, user: str) -> str:
    for macro, value in zip(MACROS, (name, name, user, user)):
        text = text.replace(macro, value)
    return text


def mentioned(keyword: str, text: str) -> bool:
    return re.search(r'(?<!\w)' + re.escape(keyword.casefold()) + r'(?!\w)', text) is not None


def active_entries(connection, companion: dict, city: dict | None) -> list[dict]:
    """Entries switched on, in their books' order, then the city's own."""
    found = many(connection, 'SELECT e.*, b.name AS book FROM lore_entries e JOIN lore_books b ON b.id=e.book_id '
                 'WHERE e.enabled=1 AND b.enabled=1 AND (b.companion_id=? OR b.companion_id IS NULL) '
                 'ORDER BY b.companion_id IS NULL, b.created_at, e.position', (companion['id'],))
    own = city_book(connection, city)
    if own and own['enabled']:
        found += [entry for entry in own['entries'] if entry['enabled']]
    return found


def offer(packet, connection, companion: dict, recent: list[dict], query: str = '', now=None):
    """Always-on entries for the system prompt ('lore'); for this reply's notes ('lore_now'), entries mentioned lately,
    then those whose "when" fits the moment, at most MAX_TRIGGERED in all. {{char}} and {{user}} become the
    companion's and the persona's names."""
    city = companion_city(connection, companion)
    entries = active_entries(connection, companion, city)
    if not entries:
        return
    persona = connection.execute('SELECT name FROM persona WHERE id=1').fetchone()
    user = persona['name'].strip() if persona and persona['name'].strip() else 'the user'
    name = companion['version']['name']
    scanned = '\n'.join([*(message['text'] for message in recent[-SCAN_MESSAGES:]), query]).casefold()
    holidays, keys = moments.holiday_names(city), None
    mentioned_now, fitting = [], []
    for entry in entries:
        line = (entry['id'], spelled(f"- {entry['title']}: {entry['text']}", name, user))
        when = when_of(entry, holidays)[0]
        if entry['always']:
            packet.offer('lore', *line)
        elif any(mentioned(word, scanned) for word in decode(entry['keywords'])):
            mentioned_now.append(line)
        elif when and now is not None:
            keys = moments.now_keys(connection, companion, now) if keys is None else keys
            fitting += [line] if moments.matches(when, keys) else []
    triggered = 0
    for identity, text in [*mentioned_now, *fitting]:
        if triggered >= MAX_TRIGGERED:
            break
        triggered += packet.offer('lore_now', identity, text)
