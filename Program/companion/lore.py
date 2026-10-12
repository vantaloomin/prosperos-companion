"""Lore from imported lorebooks (companion/imports/characters.py): what a companion or their world knows as fact.

A book belongs to one companion, or to the whole world (`companion_id` NULL, from a lorebook file imported on
its own). Each entry is plain text with keywords. Always-on entries sit in the system prompt with the rest of
what rarely changes; an entry with keywords joins the notes sent with a reply only while one of them is in the
last few messages, as a whole word in any letter case, like Prospero's Study's literal keyword matching
(server/lore/matching.py at bbcbde4). No pattern runs and no model picks entries.
"""
import re
import sqlite3
from pathlib import Path

from companion.characters import require_current
from companion.database import decode, identifier, many, one
from companion.errors import require

# The messages a keyword is looked for in, counting the one being answered.
SCAN_MESSAGES = 4
# At most this many keyword entries join one reply, first by book then by their order in it.
MAX_TRIGGERED = 8
MACROS = ('{{char}}', '<BOT>', '{{user}}', '<USER>')
# A Marinara world map's lorebook (companion/world/marinara.py) and the source title its city carries.
MAP_FORMAT = 'Marinara world map'
MAP_TITLE = 'Marinara world map: '


def books_for(connection, companion_id: str) -> list[dict]:
    return many(connection, 'SELECT * FROM lore_books WHERE companion_id=? OR companion_id IS NULL '
                'ORDER BY companion_id IS NULL, created_at', (companion_id,))


def entry_view(row: dict) -> dict:
    return {'id': row['id'], 'title': row['title'], 'text': row['text'], 'keywords': decode(row['keywords']),
            'always': bool(row['always']), 'pattern': bool(row['pattern']), 'enabled': bool(row['enabled'])}


def listing(database) -> dict:
    """The open companion's books and the world's, with their entries."""
    with database.connect() as connection:
        companion = require_current(connection)
        found = []
        for book in books_for(connection, companion['id']):
            entries = many(connection, 'SELECT * FROM lore_entries WHERE book_id=? ORDER BY position', (book['id'],))
            found.append({'id': book['id'], 'name': book['name'], 'description': book['description'],
                          'source_format': book['source_format'], 'source_file': book['source_file'],
                          'world': book['companion_id'] is None, 'enabled': bool(book['enabled']),
                          'created_at': book['created_at'], 'entries': [entry_view(row) for row in entries]})
        return {'books': found}


def visible_book(connection, book_id: str) -> dict:
    companion = require_current(connection)
    book = one(connection, 'SELECT * FROM lore_books WHERE id=?', (book_id,))
    require(book['companion_id'] in (None, companion['id']), 'That lorebook belongs to another companion.', 404)
    return book


def set_book(database, book_id: str, enabled: bool) -> dict:
    with database.connect(write=True) as connection:
        visible_book(connection, book_id)
        connection.execute('UPDATE lore_books SET enabled=? WHERE id=?', (int(enabled), book_id))
    return listing(database)


def set_entry(database, entry_id: str, enabled: bool) -> dict:
    with database.connect(write=True) as connection:
        entry = one(connection, 'SELECT * FROM lore_entries WHERE id=?', (entry_id,))
        visible_book(connection, entry['book_id'])
        require(not (enabled and entry['pattern']), 'This entry finds its moment with a search pattern, which the '
                'Companion cannot match, so it stays off. Copy what matters into an entry of your own.', 422)
        connection.execute('UPDATE lore_entries SET enabled=? WHERE id=?', (int(enabled), entry_id))
    return listing(database)


def remove_book(database, book_id: str) -> dict:
    with database.connect(write=True) as connection:
        visible_book(connection, book_id)
        connection.execute('DELETE FROM lore_books WHERE id=?', (book_id,))
    return listing(database)


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


def active_entries(connection, companion_id: str) -> list[dict]:
    return many(connection, 'SELECT e.*, b.name AS book FROM lore_entries e JOIN lore_books b ON b.id=e.book_id '
                'WHERE e.enabled=1 AND b.enabled=1 AND (b.companion_id=? OR b.companion_id IS NULL) '
                'ORDER BY b.companion_id IS NULL, b.created_at, e.position', (companion_id,))


def offer(packet, connection, companion: dict, recent: list[dict], query: str = ''):
    """Always-on entries for the system prompt ('lore'); keyword entries mentioned lately for this reply's notes
    ('lore_now'). {{char}} and {{user}} become the companion's and the persona's names."""
    entries = active_entries(connection, companion['id'])
    if not entries:
        return
    persona = connection.execute('SELECT name FROM persona WHERE id=1').fetchone()
    user = persona['name'].strip() if persona and persona['name'].strip() else 'the user'
    name = companion['version']['name']
    scanned = '\n'.join([*(message['text'] for message in recent[-SCAN_MESSAGES:]), query]).casefold()
    triggered = 0
    for entry in entries:
        line = spelled(f"- {entry['title']}: {entry['text']}", name, user)
        if entry['always']:
            packet.offer('lore', entry['id'], line)
        elif triggered < MAX_TRIGGERED and any(mentioned(word, scanned) for word in decode(entry['keywords'])):
            triggered += packet.offer('lore_now', entry['id'], line)
