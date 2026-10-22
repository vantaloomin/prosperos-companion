"""Books the app can download into the world's library from their author's own site (companion/library.py).

Only the Neokosmos wiki for now: Grandport's card in Settings > Cities offers "Add the Neokosmos wiki", which
downloads Oak's TiddlyWiki into this world's library as Grandport's book, and once added "Get the latest from
Oak's wiki", which downloads it again and replaces the old passages, so Grandport keeps up with Oak's edits.
Nothing of the wiki ships with the app; the book's page credits Oak and the licence.
"""
import httpx

from companion import library
from companion.database import identifier, many, optional
from companion.errors import DomainError, require
from companion.identity import VERSION

ONLINE = {
    'neokosmos': {
        'name': 'Neokosmos wiki', 'city_id': 'grandport', 'city_name': 'Grandport', 'url': 'https://quietoak.github.io/NeokosmosWiki/',
        'author': 'Oak', 'licence': 'CC BY-NC-SA 4.0', 'licence_url': 'https://creativecommons.org/licenses/by-nc-sa/4.0/',
        'file': 'NeokosmosWiki.html',
    },
}
MOST_BYTES = 40 * 1024 * 1024
TIMEOUT = 60
USER_AGENT = f'ProsperoCompanion/{VERSION} (adds a wiki to the library when the user asks)'


def offers(database) -> dict:
    """Each downloadable book, and its book in this world's library once added."""
    with database.connect() as connection:
        books = {row['online']: row for row in many(connection, "SELECT id, online, updated_at FROM library_books WHERE "
                                                                "online<>'' AND companion_id IS NULL")}
    return {'books': [{'key': key, **{field: entry[field] for field in ('name', 'city_id', 'city_name', 'url', 'author', 'licence',
                                                                         'licence_url')},
                       'book_id': books[key]['id'] if key in books else None,
                       'updated_at': books[key]['updated_at'] if key in books else None}
                      for key, entry in ONLINE.items()]}


def fetch(url: str) -> bytes:
    """The file at `url`, refused past MOST_BYTES."""
    try:
        with httpx.Client(timeout=TIMEOUT, headers={'User-Agent': USER_AGENT}, follow_redirects=True) as client:
            with client.stream('GET', url) as response:
                require(response.status_code == 200, f'The wiki did not download (the site answered '
                        f'{response.status_code}). Try again later.', 502)
                data = bytearray()
                for part in response.iter_bytes():
                    data += part
                    require(len(data) <= MOST_BYTES, 'The wiki is larger than the library takes.', 502)
                return bytes(data)
    except httpx.HTTPError as error:
        raise DomainError('The wiki did not download. Check the internet connection and try again.', 502) from error


def add(database, key: str) -> dict:
    """Download the book and add it to this world's library, or replace the passages of the copy already there."""
    entry = ONLINE.get(key)
    require(entry is not None, 'There is no such book to download.', 404)
    found = library.read(entry['file'], fetch(entry['url']))
    pieces = library.passages(found['sections'])
    timestamp = database.now()
    with database.connect(write=True) as connection:
        book = optional(connection, 'SELECT id FROM library_books WHERE online=? AND companion_id IS NULL', (key,))
        if book:
            library.drop_passages(connection, book['id'])
            connection.execute('UPDATE library_books SET updated_at=? WHERE id=?', (timestamp, book['id']))
            book_id = book['id']
        else:
            book_id = identifier()
            connection.execute('INSERT INTO library_books (id, companion_id, name, source_format, source_file, online, '
                               'city_id, created_at, updated_at) VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?)',
                               (book_id, entry['name'], found['format'], entry['url'], key, entry['city_id'],
                                timestamp, timestamp))
        library.store_passages(connection, book_id, pieces)
    return {**offers(database), 'added': {'id': book_id, 'name': entry['name'], 'passages': len(pieces),
                                          'replaced': bool(book)}}
