"""A reference library (companion/library.py): long texts read into passages, a few of which join a reply."""
import base64
import html
import io
import json
import zipfile

import pytest

from companion import library, library_online
from companion.database import Database
from companion.errors import DomainError
from companion.library_readers import read, wikitext
from companion.memory.context import LIBRARY_HEADING
from tests.conftest import send

NOVEL = ('The Lighthouse Keeper\n\n'
         'Chapter 1\n\nThe lighthouse at Gull Point had been dark since the storm of 1998. Nobody in the village '
         'would say who had put the lamp out.\n\n'
         'Chapter 2\n\nMarguerite Fenwick kept bees on the cliff above the harbour, and every spring she sold '
         'heather honey at the market in Saltcombe.\n')


def encoded(data: bytes) -> str:
    return base64.b64encode(data).decode('ascii')


def add(client, filename, data: bytes, world=False, status=200):
    response = client.post('/api/library/books', json={'filename': filename, 'data': encoded(data), 'world': world})
    assert response.status_code == status, response.text
    return response.json()


def tiddlywiki(tiddlers, title='Harbor Wiki') -> bytes:
    store = json.dumps([{'title': '$:/SiteTitle', 'text': title}, *tiddlers]).replace('<', '\\u003C')
    return ('<!doctype html><html><head><meta name="application-name" content="TiddlyWiki" /></head><body>'
            f'<script class="tiddlywiki-tiddler-store" type="application/json">{store}</script></body></html>').encode()


WIKI = tiddlywiki([
    {'title': 'Edgar', 'text': "!! Edgar Grandeholm\n''Merchant lord'' of [[Grandport|Grandport]]. "
                               '<<tag Merchants>> He built the <span style="color:red">tall tower</span>.'},
    {'title': '$:/state/sidebar', 'text': 'open'},
    {'title': 'Draft of Edgar', 'text': 'unfinished', 'draft.of': 'Edgar'},
    {'title': 'Edgar.mp4', 'text': '<video src="edgar.mp4"></video>'},
    {'title': 'Banner.png', 'type': 'image/png', 'text': 'iVBORw0KGgo='},
    {'title': 'Leylines', 'text': 'The leylines carry mana under the sea. {{Leylines/Footer}}'},
])


# Reading files ------------------------------------------------------------------------------------------

def test_a_novel_splits_at_its_chapters():
    found = read('keeper.txt', NOVEL.encode())
    assert found['format'] == 'Plain text' and found['name'] == 'keeper'
    assert [title for title, _text in found['sections']] == ['keeper', 'Chapter 1', 'Chapter 2']


def test_markdown_and_web_pages_keep_their_headings():
    found = read('notes.md', b'Intro words.\n\n# The Docks\n\nShips come in at dawn.\n\n## Fish market\n\nCod.')
    assert [title for title, _text in found['sections']] == ['notes', 'The Docks', 'Fish market']
    page = read('page.html', b'<html><head><title>Harbor guide</title><style>p{color:red}</style></head><body>'
                             b'<h1>The Docks</h1><p>Ships &amp; boats.</p><script>alert(1)</script><h2>Market</h2>'
                             b'<p>Cod.</p></body></html>')
    assert page['name'] == 'Harbor guide' and page['format'] == 'Web page'
    assert [(title, ' '.join(text.split())) for title, text in page['sections']] == [('The Docks', 'Ships & boats.'),
                                                                                    ('Market', 'Cod.')]


def test_an_epub_is_read_in_spine_order():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('mimetype', 'application/epub+zip')
        archive.writestr('META-INF/container.xml', '<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:'
                         'opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/book.opf"/></rootfiles>'
                         '</container>')
        archive.writestr('OEBPS/book.opf', '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" '
                         'xmlns:dc="http://purl.org/dc/elements/1.1/"><metadata><dc:title>Saltcombe Tales</dc:title>'
                         '</metadata><manifest><item id="b" href="two.xhtml"/><item id="a" href="one.xhtml"/>'
                         '</manifest><spine><itemref idref="a"/><itemref idref="b"/></spine></package>')
        archive.writestr('OEBPS/one.xhtml', '<html><body><h1>One</h1><p>Bees on the cliff.</p></body></html>')
        archive.writestr('OEBPS/two.xhtml', '<html><body><h1>Two</h1><p>Honey at market.</p></body></html>')
    found = read('tales.epub', buffer.getvalue())
    assert found['name'] == 'Saltcombe Tales' and [title for title, _ in found['sections']] == ['One', 'Two']


def test_a_tiddlywiki_gives_one_section_per_tiddler_with_its_title():
    found = read('wiki.html', WIKI)
    assert found['format'] == 'TiddlyWiki' and found['name'] == 'Harbor Wiki'
    sections = dict(found['sections'])
    assert list(sections) == ['Edgar', 'Leylines']
    edgar = ' '.join(sections['Edgar'].split())
    assert edgar == 'Edgar Grandeholm Merchant lord of Grandport. He built the tall tower .'
    assert ' '.join(sections['Leylines'].split()) == 'The leylines carry mana under the sea.'


def test_an_older_tiddlywiki_store_is_read_too():
    body = html.escape("Ships ''dock'' at [[the pier]].")
    page = ('<html><head><meta name="generator" content="TiddlyWiki" /></head><body><div id="storeArea">'
            f'<div title="Pier" modifier="Oak"><pre>{body}</pre></div>'
            '<div title="$:/core"><pre>x</pre></div></div></body></html>')
    assert read('old.html', page.encode())['sections'] == [('Pier', 'Ships dock at the pier.')]


def test_wikitext_keeps_urls_and_tables_readable():
    assert wikitext('See https://example.org //now//.') == 'See https://example.org now.'
    assert wikitext('|!Name|!Age|\n|Edgar|60|') == 'Name; Age\nEdgar; 60'


def test_other_files_are_turned_down():
    with pytest.raises(DomainError, match='.txt, .md'):
        read('cover.png', b'\x89PNG\r\n')


def test_passages_are_short_and_keep_every_word():
    text = ' '.join(f'Sentence number {index} is about the harbour.' for index in range(200))
    found = library.passages([('Book', text)])
    assert all(len(piece) <= library.PASSAGE_CHARS + library.SCRAP_CHARS for _title, piece in found)
    assert ' '.join(piece for _title, piece in found).split() == text.split()
    assert all(piece.endswith('.') for _title, piece in found)


def test_a_scrap_at_the_end_of_a_section_joins_the_passage_before_it():
    chapter = ' '.join(f'Sentence number {index} is about the harbour.' for index in range(11))
    found = library.passages([('Chapter I', f'{chapter}\n\nContinue to Chapter II'), ('Chapter II', 'Short.')])
    assert [title for title, _piece in found] == ['Chapter I', 'Chapter II']
    assert found[0][1].endswith('harbour.\n\nContinue to Chapter II'), 'no passage of its own'
    assert found[1] == ('Chapter II', 'Short.'), 'a short section is still a passage'


def test_everyday_chat_picks_out_no_passage():
    assert library.particular("How was your day? I'm tired, work was long.") == ''
    assert library.particular('Have you ever been to the Admiralty?') == 'admiralty'


# The library on the page ----------------------------------------------------------------------------------

def test_books_are_added_listed_browsed_switched_off_and_removed(client, companion):
    made = add(client, 'keeper.txt', NOVEL.encode())
    assert made['added']['passages'] == 3
    add(client, 'wiki.html', WIKI, world=True)
    books = client.get('/api/library').json()['books']
    assert [(book['name'], book['world'], book['passages']) for book in books] == [
        ('keeper', False, 3), ('Harbor Wiki', True, 2)]
    book = books[0]
    listed = client.get(f"/api/library/books/{book['id']}/passages").json()
    assert listed['total'] == 3 and listed['passages'][0]['title'] == 'keeper'
    found = client.get(f"/api/library/books/{book['id']}/passages", params={'q': 'honey'}).json()
    assert [item['title'] for item in found['passages']] == ['Chapter 2']
    assert client.put(f"/api/library/books/{book['id']}", json={'enabled': False}).json()['books'][0]['enabled'] is False
    assert [item['name'] for item in client.delete(f"/api/library/books/{book['id']}").json()['books']] == ['Harbor Wiki']


def test_an_empty_or_broken_file_says_so(client, companion):
    assert 'no words' in add(client, 'empty.txt', b'   \n', status=422)['detail']
    response = client.post('/api/library/books', json={'filename': 'a.txt', 'data': 'not base64!'})
    assert response.status_code == 422 and 'did not arrive whole' in response.json()['detail']


# In the reply -------------------------------------------------------------------------------------------

def test_matching_passages_join_the_reply_notes(client, connected, provider):
    add(client, 'keeper.txt', NOVEL.encode())
    send(client, 'How was your day?', 'message-one')
    assert LIBRARY_HEADING not in provider.requests[-1]['prompt']
    send(client, 'Did Marguerite Fenwick sell honey this spring?', 'message-two')
    request = provider.requests[-1]
    assert LIBRARY_HEADING in request['prompt'] and LIBRARY_HEADING not in request['system']
    assert '- Chapter 2: Marguerite Fenwick kept bees' in request['prompt']
    assert 'Gull Point' not in request['prompt']
    # Just given: the next reply leaves it out rather than repeat it.
    send(client, 'Tell me more about Marguerite Fenwick and her honey.', 'message-three')
    assert 'Marguerite Fenwick kept bees' not in provider.requests[-1]['prompt']


def test_a_switched_off_book_stays_out(client, connected, provider):
    book = add(client, 'keeper.txt', NOVEL.encode())['added']
    client.put(f"/api/library/books/{book['id']}", json={'enabled': False})
    send(client, 'Who put out the lighthouse at Gull Point?', 'message-one')
    assert LIBRARY_HEADING not in provider.requests[-1]['prompt']


def test_a_reply_gets_at_most_three_passages(client, connected, provider):
    lens = 'The lighthouse keeper polished lamp lens number {index} at dusk, humming as the gulls circled.'
    bees = 'Marguerite kept her bees in hive number {index} on the cliff and sold the honey in town.'
    text = '\n\n'.join(f'Chapter {index}\n\n' + (lens if index % 2 else bees).format(index=index) for index in range(16))
    add(client, 'lamps.txt', text.encode())
    send(client, 'Tell me about the lighthouse keeper and the lamp lens', 'message-one')
    notes = provider.requests[-1]['prompt'].split(LIBRARY_HEADING)[1]
    lines = [line for line in notes.splitlines() if line.startswith('- Chapter')]
    assert len(lines) == library.MOST_PASSAGES and sum(len(line) for line in lines) <= library.MOST_CHARS + 60


# The Neokosmos wiki ---------------------------------------------------------------------------------------

def test_the_neokosmos_wiki_is_added_and_kept_up_to_date(client, companion, monkeypatch):
    offered = client.get('/api/library/online').json()['books']
    assert [(item['key'], item['city_name'], item['author'], item['licence'], item['book_id']) for item in offered] == [
        ('neokosmos', 'Grandport', 'Oak', 'CC BY-NC-SA 4.0', None)]
    monkeypatch.setattr(library_online, 'fetch', lambda url: WIKI)
    added = client.post('/api/library/online/neokosmos').json()
    assert added['added']['passages'] == 2 and added['added']['replaced'] is False
    book = client.get('/api/library').json()['books'][0]
    assert (book['name'], book['world'], book['online'], book['city_id']) == ('Neokosmos wiki', True, 'neokosmos',
                                                                                'grandport')
    client.put(f"/api/library/books/{book['id']}", json={'enabled': False})
    newer = tiddlywiki([{'title': 'Edgar', 'text': 'Edgar now rules the docks.'},
                        {'title': 'Nomion', 'text': 'A god of the sea.'}, {'title': 'Thalassar', 'text': 'Another.'}])
    monkeypatch.setattr(library_online, 'fetch', lambda url: newer)
    again = client.post('/api/library/online/neokosmos').json()
    assert again['added'] == {'id': book['id'], 'name': 'Neokosmos wiki', 'passages': 3, 'replaced': True}
    kept = client.get('/api/library').json()['books'][0]
    assert kept['passages'] == 3 and kept['enabled'] is False
    assert client.post('/api/library/online/elsewhere').status_code == 404


def test_a_city_book_is_read_only_where_the_companion_lives(client, companion, monkeypatch):
    monkeypatch.setattr(library_online, 'fetch', lambda url: WIKI)
    client.post('/api/library/online/neokosmos')
    database = client.app.state.database
    with database.connect() as connection:
        mira = {'id': companion['id'], 'version': {'definition': {'home_city': 'Lisbon'}}}
        assert library.usable_books(connection, mira) == []
        mira['version']['definition']['home_city'] = 'Grandport'
        assert [book['name'] for book in library.usable_books(connection, mira)] == ['Neokosmos wiki']


def test_a_new_world_in_the_city_gets_its_book(tmp_path, client, companion, monkeypatch):
    monkeypatch.setattr(library_online, 'fetch', lambda url: WIKI)
    client.post('/api/library/online/neokosmos')
    source = client.app.state.database.path
    target = Database(tmp_path / 'new.sqlite3')
    with target.connect():
        pass
    library.carry_city_books(target.path, source, {'id': 'grandport'})
    with target.connect() as connection:
        assert connection.execute('SELECT name FROM library_books').fetchall()[0][0] == 'Neokosmos wiki'
        assert connection.execute('SELECT COUNT(*) FROM library_passages').fetchone()[0] == 2


# Embeddings ---------------------------------------------------------------------------------------------

def test_passages_get_vectors_and_match_by_meaning(client, companion):
    add(client, 'keeper.txt', NOVEL.encode())
    database = client.app.state.database
    with database.connect(write=True) as connection:
        mira = dict(companion, version={'definition': {}})
        items = library.unindexed(connection, 'embed', mira, 10)
        assert [kind for kind, _id, _text in items] == ['passage'] * 3
        vectors = [[1.0, 0.0], [0.0, 1.0], [0.7, 0.7]]
        assert library.store_vectors(connection, 'embed', items, vectors, database.now()) == 3
        assert library.unindexed(connection, 'embed', mira, 10) == []
        rows = library.passage_rows(connection, library.usable_books(connection, mira))
        found = library.by_meaning(connection, {'model': 'embed', 'vector': [0.0, 1.0]}, rows)
    assert found == [items[1][1], items[2][1]]
