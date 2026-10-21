"""A reference library (Hit List #83): long texts the user adds to a companion or to the world, such as a novel, a
script, transcripts or a wiki export (companion/library_readers.py).

A book is split into short passages, kept whole, and indexed for keyword recall (companion/memory/retrieval.py),
plus embeddings when a recall model is connected (`library_vectors`, made by companion/memory/worker.py). Each reply
gets at most MOST_PASSAGES passages that match the last few messages, in the reply's notes ('library'), skipping
what the last few replies were given. No model picks them and nothing is sent anywhere.

A world book with a `city_id` (the Neokosmos wiki, companion/library_online.py) joins replies only for companions
who live in that city, and comes along into a new world made in that city.
"""
import re
import sqlite3
from pathlib import Path

from companion.characters import require_current
from companion.database import decode, identifier, many, one
from companion.errors import require
from companion.library_readers import read
from companion.memory import vectors
from companion.memory.chunks import Chunk
from companion.memory.retrieval import Corpus, terms
from companion.world import newcomers

# A passage is a few sentences: cut at a paragraph, else a sentence, else a word, near this many characters.
PASSAGE_CHARS = 480
MOST_BOOK_PASSAGES = 30_000
# Per reply: at most this many passages, this many characters in all.
MOST_PASSAGES = 3
MOST_CHARS = 1200
# The messages matched, counting the one being answered.
SCAN_MESSAGES = 4
# A passage given to one of the last few replies waits before it comes again.
RECENT_REPLIES = 4
# How well a passage must match to be used: keyword score (0 to 1), or embedding similarity.
KEYWORD_FLOOR = 0.1
MEANING_FLOOR = 0.5
CANDIDATES = 12
RANK_OFFSET = 60
SHOWN_PASSAGES = 20
SENTENCE = re.compile(r'[.!?…]["\')\]’”]*\s')
# Everyday chat words, which would match any long text: a passage has to match something more particular, like a
# name, a place or a subject. A word also counts in these forms: -s, -es, -ed, -d, -ing, -ly, -er.
CHAT_WORDS = frozenset("""
able about actually after afternoon again ago agree ah all almost alone along already alright also always am amazing
any anything anyway anywhere around ask away awesome back bad bed being best better big bit bored both bring busy buy
call came can can't cant care cause chat check come cool could couldn't cute dad day days dear did didn't dinner do
does doesn't doing don't done down dream drink each early easy eat else end enough even evening ever every everyone
everything exactly fair far feel fine first food for forget found free friend fun funny get give glad go god going
gone gonna good got great guess guy had happen happy hard has hate have haven't he'd hear heard heart hello help hey hi
hmm home hope hour house how huh i'd i'll i'm i've idea just keep kind kinda know last late later laugh least leave
less let let's life like little live lol long look lot love lunch made make many maybe mean meet might mind miss mom
moment money more morning most move much must need never new next nice night nope nothing now ok okay old once one only
other out over own people pretty probably put quite rather read ready real really remember right said same saw say
see seem seen send should show since sleep small so some someone something sometimes soon sorry sound start stay still
stop story stuff such sure take talk tell than thank thanks that's thing things think though thought through time
tired today together told tomorrow tonight too took true try trying turn um understand until up very wait walk want
was watch way week weekend weird well went what's whatever while who's why wish without won't wonder work world worry
would wow write wrong yeah year yes yesterday yet you're you've yours""".split())


# Adding a book ------------------------------------------------------------------------------------------

def tidy(text: str) -> str:
    text = re.sub(r'[ \t ]+', ' ', text.replace('\r\n', '\n').replace('\r', '\n'))
    return re.sub(r'\n[ \n]*\n', '\n\n', re.sub(r' *\n *', '\n', text)).strip()


def cut(text: str, start: int, limit: int) -> int:
    """Where a passage starting at `start` ends: a paragraph, else a sentence, else a word, in its second half."""
    stop = min(start + limit, len(text))
    if stop == len(text):
        return stop
    least = start + limit // 2
    paragraph = text.rfind('\n\n', least, stop)
    if paragraph >= least:
        return paragraph + 2
    sentences = [match.end() for match in SENTENCE.finditer(text, least, stop)]
    if sentences:
        return sentences[-1]
    space = text.rfind(' ', least, stop)
    return space + 1 if space >= least else stop


def passages(sections: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """(title, text) passages of a book's sections, in order; every word kept once."""
    found = []
    for title, body in sections:
        text, start = tidy(body), 0
        while start < len(text):
            stop = cut(text, start, PASSAGE_CHARS)
            if piece := text[start:stop].strip():
                found.append((title[:200], piece))
            start = stop
    require(found, 'There are no words to read in this file.', 422)
    require(len(found) <= MOST_BOOK_PASSAGES, 'This text is longer than the library takes (about 14 MB of words). '
            'Split it into parts and add each one.', 422)
    return found


def store_passages(connection, book_id: str, found: list[tuple[str, str]]) -> None:
    connection.executemany('INSERT INTO library_passages (id, book_id, position, title, text) VALUES (?, ?, ?, ?, ?)',
                           [(identifier(), book_id, index, title, text) for index, (title, text) in enumerate(found)])


def drop_passages(connection, book_id: str) -> None:
    connection.execute('DELETE FROM library_passages WHERE book_id=?', (book_id,))


def add(database, filename: str, source: bytes, world: bool) -> dict:
    """A file as a new book of the open companion's library, or of the world's."""
    found = read(filename, source)
    pieces = passages(found['sections'])
    timestamp = database.now()
    with database.connect(write=True) as connection:
        owner = None if world else require_current(connection)['id']
        book_id = identifier()
        connection.execute('INSERT INTO library_books (id, companion_id, name, source_format, source_file, created_at, '
                           'updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                           (book_id, owner, found['name'][:200], found['format'], filename[:260], timestamp, timestamp))
        store_passages(connection, book_id, pieces)
    return {**listing(database), 'added': {'id': book_id, 'name': found['name'][:200], 'passages': len(pieces)}}


# The books on the page ----------------------------------------------------------------------------------

def book_view(book: dict, count: int) -> dict:
    return {'id': book['id'], 'name': book['name'], 'world': book['companion_id'] is None,
            'source_format': book['source_format'], 'source_file': book['source_file'], 'online': book['online'],
            'city_id': book['city_id'], 'enabled': bool(book['enabled']), 'passages': count,
            'created_at': book['created_at'], 'updated_at': book['updated_at']}


def listing(database) -> dict:
    """The open companion's books and the world's, with how many passages each has."""
    with database.connect() as connection:
        companion = require_current(connection)
        counts = dict(connection.execute('SELECT book_id, COUNT(*) FROM library_passages GROUP BY book_id').fetchall())
        books = many(connection, 'SELECT * FROM library_books WHERE companion_id=? OR companion_id IS NULL '
                     'ORDER BY companion_id IS NULL, created_at', (companion['id'],))
        return {'books': [book_view(book, counts.get(book['id'], 0)) for book in books]}


def visible_book(connection, book_id: str) -> dict:
    companion = require_current(connection)
    book = one(connection, 'SELECT * FROM library_books WHERE id=?', (book_id,))
    require(book['companion_id'] in (None, companion['id']), 'That book belongs to another companion.', 404)
    return book


def set_book(database, book_id: str, enabled: bool) -> dict:
    with database.connect(write=True) as connection:
        visible_book(connection, book_id)
        connection.execute('UPDATE library_books SET enabled=? WHERE id=?', (int(enabled), book_id))
    return listing(database)


def remove_book(database, book_id: str) -> dict:
    with database.connect(write=True) as connection:
        visible_book(connection, book_id)
        drop_passages(connection, book_id)
        connection.execute('DELETE FROM library_books WHERE id=?', (book_id,))
    return listing(database)


def browse(database, book_id: str, query: str = '') -> dict:
    """A book's passages, so the user can see what it draws from: the first few, or the best matches for `query`."""
    with database.connect() as connection:
        visible_book(connection, book_id)
        rows = many(connection, 'SELECT id, title, text FROM library_passages WHERE book_id=? ORDER BY position',
                    (book_id,))
    if query.strip():
        found = corpus_of(rows).search(query, limit=SHOWN_PASSAGES)
        shown = [{'id': hit.chunk.id, 'title': hit.chunk.title, 'text': hit.chunk.text} for hit in found]
    else:
        shown = rows[:SHOWN_PASSAGES]
    return {'total': len(rows), 'passages': shown}


# In the prompt ------------------------------------------------------------------------------------------

CORPORA: dict[tuple, Corpus] = {}


def corpus_of(rows: list[dict], key: tuple | None = None) -> Corpus:
    """Keyword statistics over passages; kept for the same books at the same revision (`key`)."""
    if key is not None and key in CORPORA:
        return CORPORA[key]
    corpus = Corpus([Chunk(row['id'], row.get('book_id', ''), row['title'], row['text'], 0, len(row['text']), '',
                           'passage') for row in rows])
    if key is not None:
        if len(CORPORA) >= 4:
            CORPORA.pop(next(iter(CORPORA)))
        CORPORA[key] = corpus
    return corpus


def usable_books(connection, companion: dict) -> list[dict]:
    """Switched-on books of the companion and of the world; a city's book only where the companion lives there."""
    books = many(connection, 'SELECT * FROM library_books WHERE enabled=1 AND (companion_id=? OR companion_id IS NULL) '
                 'ORDER BY id', (companion['id'],))
    if any(book['city_id'] for book in books):
        home = newcomers.city_for(connection, companion['version']['definition']).get('id')
        books = [book for book in books if not book['city_id'] or book['city_id'] == home]
    return books


def passage_rows(connection, books: list[dict]) -> list[dict]:
    marks = ','.join('?' * len(books))
    return many(connection, f'SELECT id, book_id, title, text FROM library_passages WHERE book_id IN ({marks}) '
                'ORDER BY book_id, position', tuple(book['id'] for book in books))


def passage_text(row: dict) -> str:
    return f"{row['title']}: {row['text']}" if row['title'] else row['text']


def recently_given(connection, timeline_id: str) -> set[str]:
    given = set()
    for row in many(connection, "SELECT receipt FROM messages WHERE timeline_id=? AND role='companion' "
                    'AND receipt IS NOT NULL ORDER BY seq DESC LIMIT ?', (timeline_id, RECENT_REPLIES)):
        given.update((decode(row['receipt']).get('included') or {}).get('library', []))
    return given


def by_meaning(connection, semantic: dict | None, rows: list[dict]) -> list[str]:
    """Passage ids whose embedding is close to the message's, best first."""
    if not semantic or not semantic.get('vector'):
        return []
    texts = {row['id']: passage_text(row) for row in rows}
    stored = many(connection, 'SELECT passage_id, digest, vector FROM library_vectors WHERE model=?',
                  (semantic['model'],))
    scored = [(score, row['passage_id']) for row in stored if row['passage_id'] in texts
              and vectors.digest(texts[row['passage_id']]) == row['digest']
              and (score := vectors.cosine(semantic['vector'], vectors.unpack(row['vector']))) >= MEANING_FLOOR]
    return [identity for _score, identity in sorted(scored, key=lambda item: (-item[0], item[1]))[:CANDIDATES]]


def everyday(word: str) -> bool:
    return word in CHAT_WORDS or word.isdigit() or any(
        word.endswith(ending) and word[:-len(ending)] in CHAT_WORDS for ending in ('s', 'es', 'ed', 'd', 'ing', 'ly', 'er'))


def particular(text: str, known=None) -> str:
    """The words of `text` that could pick out a passage: not stopwords, not everyday chat, and (with `known`, the
    words of the books) in the books at all, so a word they never use doesn't water down the ones they do."""
    return ' '.join(word for word in terms(text) if not everyday(word) and (known is None or word in known))


def ranked(corpus: Corpus, queries: list[str], meaning: list[str]) -> list[str]:
    """Passage ids that match the conversation by keywords or by meaning, fused by rank, best first."""
    rankings = [[hit.chunk.id for hit in corpus.search(words, limit=CANDIDATES, threshold=KEYWORD_FLOOR)]
                for query in queries if (words := particular(query, corpus.df))] + [meaning]
    totals = {}
    for ranking in rankings:
        for rank, identity in enumerate(ranking, 1):
            totals[identity] = totals.get(identity, 0) + 1 / (RANK_OFFSET + rank)
    return sorted(totals, key=lambda identity: (-totals[identity], identity))


def offer(packet, connection, companion: dict, recent: list[dict], query: str, semantic: dict | None = None):
    """Up to MOST_PASSAGES passages that fit the last few messages, for this reply's notes ('library')."""
    books = usable_books(connection, companion)
    if not books:
        return
    rows = passage_rows(connection, books)
    corpus = corpus_of(rows, tuple((book['id'], book['updated_at']) for book in books))
    latest = '\n'.join(message['text'] for message in recent[-SCAN_MESSAGES:])
    texts = {row['id']: row for row in rows}
    skip = recently_given(connection, companion['active_timeline_id'])
    used = given = 0
    for identity in ranked(corpus, [query, latest], by_meaning(connection, semantic, rows)):
        row = texts[identity]
        if identity in skip or used + len(row['text']) > MOST_CHARS:
            continue
        if packet.offer('library', identity, f'- {passage_text(row)}'):
            used, given = used + len(row['text']), given + 1
        if given >= MOST_PASSAGES:
            return


# Embeddings ---------------------------------------------------------------------------------------------

def unindexed(connection, model: str, companion: dict, limit: int) -> list[tuple[str, str, str]]:
    """(kind, id, text) for passages of the companion's usable books without a vector from `model`."""
    books = usable_books(connection, companion)
    if not books or limit <= 0:
        return []
    marks = ','.join('?' * len(books))
    rows = many(connection, 'SELECT p.id, p.title, p.text FROM library_passages p LEFT JOIN library_vectors v ON '
                f'v.passage_id=p.id AND v.model=? WHERE p.book_id IN ({marks}) AND v.passage_id IS NULL '
                'ORDER BY p.book_id, p.position LIMIT ?', (model, *(book['id'] for book in books), limit))
    return [('passage', row['id'], passage_text(row)) for row in rows]


def store_vectors(connection, model: str, items, found, timestamp: str) -> int:
    """Save the vectors of passages still in the library (a book can be replaced or removed meanwhile)."""
    saved = 0
    for (_kind, passage_id, text), vector in zip(items, found):
        if connection.execute('SELECT 1 FROM library_passages WHERE id=?', (passage_id,)).fetchone():
            connection.execute('INSERT OR REPLACE INTO library_vectors (passage_id, model, digest, vector, created_at) '
                               'VALUES (?, ?, ?, ?, ?)', (passage_id, model, vectors.digest(text), vectors.pack(vector),
                                                          timestamp))
            saved += 1
    return saved


# A city's books in a new world --------------------------------------------------------------------------

BOOK_COLUMNS = 'id, companion_id, name, source_format, source_file, online, city_id, enabled, created_at, updated_at'
PASSAGE_COLUMNS = 'id, book_id, position, title, text'


def carry_city_books(target: Path, source: Path, city: dict) -> None:
    """A new world in `city` gets the city's books (the Neokosmos wiki in Grandport) from the world it was made from."""
    connection = sqlite3.connect(target, isolation_level=None)
    try:
        connection.execute('ATTACH DATABASE ? AS kept', (str(Path(source).resolve()),))
        books = [row[0] for row in connection.execute('SELECT id FROM kept.library_books WHERE companion_id IS NULL '
                                                      'AND city_id=? ORDER BY created_at', (city['id'],))]
        connection.execute('BEGIN IMMEDIATE')
        for book_id in books:
            connection.execute(f'INSERT INTO main.library_books ({BOOK_COLUMNS}) SELECT {BOOK_COLUMNS} FROM '
                               'kept.library_books WHERE id=?', (book_id,))
            connection.execute(f'INSERT INTO main.library_passages ({PASSAGE_COLUMNS}) SELECT {PASSAGE_COLUMNS} FROM '
                               'kept.library_passages WHERE book_id=?', (book_id,))
        connection.execute('COMMIT')
    except BaseException:
        if connection.in_transaction:
            connection.execute('ROLLBACK')
        raise
    finally:
        connection.close()
