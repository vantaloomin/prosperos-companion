"""Reading links the user pastes (companion/mcp/links.py), against recorded site answers."""
import asyncio
import json
import sqlite3
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from companion.database import initialize
from companion.identity import CLIENT_HEADER
from companion.main import create_app
from companion.mcp import links, lookups
from companion.mcp.client import ToolFailure
from companion.providers.vault import MemoryVault

STANDIN = str(Path(__file__).with_name('mcp_standin.py'))
PUBLIC = lambda host, port: ['93.184.216.34']  # noqa: E731 - a public address for every host

ARTICLE = """<html><head><title>Bridge reopens | Harbor Times</title>
<meta name="description" content="The harbor bridge is open again.">
<meta property="og:site_name" content="Harbor Times"></head>
<body><nav><a>Home</a><a>Sports</a></nav><script>track()</script>
<article><h1>Harbor bridge reopens after repairs</h1>
<p>The bridge reopened on Monday after six months of repairs, the city said.</p>
<p>Traffic is expected to return to normal by the weekend, officials added in a statement.</p></article>
<footer>Copyright</footer></body></html>"""
REDDIT = [{'data': {'children': [{'kind': 't3', 'data': {
    'title': 'The bridge is finally open', 'subreddit_name_prefixed': 'r/baltimore', 'author': 'crabcake',
    'selftext': 'Drove over it this morning.', 'score': 412, 'num_comments': 38, 'is_self': True}}]}},
    {'data': {'children': [{'kind': 't1', 'data': {'author': 'oldbay', 'score': 90, 'body': 'Took long enough.'}},
                           {'kind': 'more', 'data': {}}]}}]
OEMBED_X = {'author_name': 'NASA', 'author_url': 'https://twitter.com/NASA', 'html':
            '<blockquote class="twitter-tweet"><p lang="en" dir="ltr">Liftoff! &amp; on our way.<br>'
            '<a href="https://t.co/x">pic.twitter.com/x</a></p>&mdash; NASA (@NASA) '
            '<a href="https://twitter.com/NASA/status/123">October 5, 2026</a></blockquote>'}


def reader(answers: dict, seen: list | None = None, resolver=PUBLIC) -> links.Reader:
    """A reader whose requests get the answer for the first matching URL fragment: (status, body, headers)."""
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(str(request.url))
        for fragment, (status, body, headers) in answers.items():
            if fragment in str(request.url):
                content = body if isinstance(body, (str, bytes)) else json.dumps(body)
                return httpx.Response(status, content=content, headers=headers)
        return httpx.Response(404)
    return links.Reader(httpx.AsyncClient(transport=httpx.MockTransport(handler)), resolver)


HTML = {'content-type': 'text/html; charset=utf-8'}
JSON = {'content-type': 'application/json'}


def read(found: links.Reader, url: str) -> dict:
    return asyncio.run(found.read(url))


def failure(found: links.Reader, url: str) -> ToolFailure:
    with pytest.raises(ToolFailure) as error:
        read(found, url)
    return error.value


def test_finding_links_in_a_message():
    text = ('Look (https://en.wikipedia.org/wiki/Bridge_(structure)) and https://example.com/a?b=1, '
            'also https://example.com/a?b=1. and https://third.example.com and https://fourth.example.com')
    assert links.find(text) == ['https://en.wikipedia.org/wiki/Bridge_(structure)', 'https://example.com/a?b=1']
    assert links.find('no links here, just example.com') == []


def test_private_addresses_are_never_opened():
    for address in ('127.0.0.1', '10.0.0.5', '192.168.1.1', '169.254.169.254', '::1', '::ffff:127.0.0.1'):
        assert failure(reader({}, resolver=lambda host, port, a=address: [a]), 'https://sneaky.example').code == \
            'private'
    assert failure(reader({}), 'ftp://example.com/file').code == 'address'
    assert failure(reader({}), 'https://user:pw@example.com/').code == 'address'

    def by_host(host, port):
        return ['127.0.0.1'] if host == 'localhost' else ['93.184.216.34']
    redirected = reader({'example.com': (302, '', {'location': 'http://localhost:8775/api/memories'})},
                        resolver=by_host)
    assert failure(redirected, 'https://example.com/go').code == 'private'


def test_reading_an_article_leaves_out_navigation():
    page = read(reader({'harbortimes.example': (200, ARTICLE, HTML)}), 'https://harbortimes.example/bridge')
    assert page['title'] == 'Bridge reopens | Harbor Times'
    assert page['text'].startswith('Page: Bridge reopens | Harbor Times (Harbor Times)\nDescription: The harbor '
                                   'bridge is open again.\n\nHarbor bridge reopens after repairs\nThe bridge reopened')
    assert 'Sports' not in page['text'] and 'track()' not in page['text'] and 'Copyright' not in page['text']


def test_pages_that_cannot_be_read():
    shell = '<html><head><title>App</title></head><body><div id="root"></div><script>boot()</script></body></html>'
    assert failure(reader({'app.example': (200, shell, HTML)}), 'https://app.example/').code == 'needs_browser'
    pdf = reader({'docs.example': (200, b'%PDF-1.7', {'content-type': 'application/pdf'})})
    assert failure(pdf, 'https://docs.example/report.pdf').message == 'PDFs are not read on this computer.'
    assert failure(reader({'paywall.example': (403, '', HTML)}), 'https://paywall.example/').code == 'refused'
    assert failure(reader({}), 'https://gone.example/').code == 'not_found'
    loop = reader({'loop.example': (302, '', {'location': 'https://loop.example/again'})})
    assert failure(loop, 'https://loop.example/').code == 'redirects'


def test_large_pages_are_cut_off():
    big = '<html><body><article>' + '<p>' + 'word ' * 400 + '</p>' * 1 + '</article></body></html>'
    page = read(reader({'big.example': (200, big * 20, HTML)}), 'https://big.example/')
    assert len(page['text']) <= links.MAX_TEXT


def test_reddit_posts_use_the_public_json_view():
    seen = []
    found = reader({'/r/baltimore/s/AbC': (301, '', {'location': '/r/baltimore/comments/abc123/the_bridge/'}),
                    'comments/abc123/the_bridge.json': (200, REDDIT, JSON)}, seen)
    page = read(found, 'https://www.reddit.com/r/baltimore/s/AbC')
    assert seen[-1] == 'https://www.reddit.com/r/baltimore/comments/abc123/the_bridge.json?limit=8&depth=1&raw_json=1'
    assert page['kind'] == 'reddit'
    assert page['text'] == ('Reddit post in r/baltimore by u/crabcake (412 points, 38 comments): The bridge is '
                            'finally open\nDrove over it this morning.\nTop comments:\n- u/oldbay (90 points): Took '
                            'long enough.')


def test_x_posts_use_oembed_and_profiles_are_explained():
    seen = []
    page = read(reader({'publish.twitter.com/oembed': (200, OEMBED_X, JSON)}, seen),
                'https://x.com/NASA/status/123?s=20')
    assert 'url=https%3A%2F%2Ftwitter.com%2FNASA%2Fstatus%2F123' in seen[0]
    assert page['text'] == ('Post on X by NASA (@NASA), October 5, 2026:\nLiftoff! & on our way.\npic.twitter.com/x\n'
                            'Only the post itself is available, not replies or images.')
    assert failure(reader({}), 'https://x.com/NASA').code == 'sign_in'
    assert failure(reader({'publish.twitter.com': (404, '', JSON)}), 'https://twitter.com/a/status/9').code == \
        'not_found'


def test_youtube_videos_use_oembed():
    found = reader({'youtube.com/oembed': (200, {'title': 'Bridge timelapse', 'author_name': 'City'}, JSON)})
    page = read(found, 'https://youtu.be/dQw4w9WgXcQ')
    assert page['text'] == ('YouTube video "Bridge timelapse" by City. Only the title and channel are available, '
                            'not the video itself.')


def test_context_lines_for_links():
    ok = {'id': 'o1', 'category': 'link', 'status': 'ok', 'service_id': None, 'service_name': 'x',
          'arguments': {'url': 'https://harbortimes.example/bridge'}, 'content': 'Page: Bridge',
          'retrieved_at': '2026-10-05T14:00:00Z'}
    failed = {**ok, 'id': 'o2', 'status': 'failed', 'retrieved_at': None, 'content': '', 'error': 'HTTP 403'}
    [(_, read_line), (_, failed_line)] = lookups.context_lines([ok, failed], None, 'America/New_York',
                                                              'At work at the bakery')
    assert read_line == ('- The link the user sent (https://harbortimes.example/bridge), opened at 05 Oct 10:00. You '
                         'have looked at it and can talk about it: «Page: Bridge»')
    assert 'harbortimes.example) that would not open for you' in failed_line
    assert 'do not guess, summarise or pretend to know it' in failed_line
    assert 'that fits what you are doing right now (At work at the bakery)' in failed_line
    assert 'HTTP 403' not in failed_line


# In the app


class FakeReader:
    def __init__(self):
        self.pages = {}
        self.calls = []

    async def read(self, url):
        self.calls.append(url)
        answer = self.pages.get(url, ToolFailure('refused', 'The site refused to show the page (HTTP 403).'))
        if isinstance(answer, ToolFailure):
            raise answer
        return {'url': url, 'kind': 'page', 'title': 'T', 'text': answer}


@pytest.fixture
def fake_reader():
    return FakeReader()


@pytest.fixture
def app(tmp_path, clock, provider, fake_reader):
    return create_app(tmp_path / 'workspace' / 'companion.sqlite3', clock=clock, vault=MemoryVault(),
                      provider=provider, life_tasks=False, link_reader=fake_reader)


@pytest.fixture
def client(app):
    with TestClient(app, headers={CLIENT_HEADER: 'workspace'}) as test_client:
        yield test_client


def send(client, text, client_id):
    response = client.post('/api/conversation/messages', json={'text': text, 'client_id': f'client-{client_id}'})
    assert response.status_code == 200, response.text
    return response.json()


def link_observations(client, message_id):
    return client.get(f'/api/context/messages/{message_id}/observations').json()['observations']


def test_a_pasted_link_is_read_and_quoted(client, connected, provider, fake_reader):
    url = 'https://harbortimes.example/bridge'
    fake_reader.pages[url] = 'Page: Bridge reopens\n\nThe bridge reopened on Monday.'
    sent = send(client, f'Did you see this? {url}', 'l1')
    system = provider.requests[-1]['system']
    assert f'The link the user sent ({url}), opened at' in system
    assert '«Page: Bridge reopens\n\nThe bridge reopened on Monday.»' in system
    [observation] = link_observations(client, sent['message']['id'])
    assert (observation['category'], observation['status'], observation['service_name'], observation['destination']) \
        == ('link', 'ok', 'This computer (link reader)', 'harbortimes.example')
    send(client, f'What did you think of {url} ?', 'l2')
    assert fake_reader.calls == [url]  # the fresh result is reused


def test_an_unreadable_link_gets_an_in_character_reason(client, connected, provider, fake_reader):
    sent = send(client, 'lol https://www.reddit.com/r/baltimore/comments/abc/x/', 'l3')
    system = provider.requests[-1]['system']
    assert 'The user sent a link (www.reddit.com) that would not open for you' in system
    assert 'HTTP 403' not in system
    [observation] = link_observations(client, sent['message']['id'])
    assert observation['status'] == 'failed' and observation['error'] == 'The site refused to show the page (HTTP 403).'


def test_links_are_not_opened_when_turned_off(client, connected, provider, fake_reader):
    response = client.put('/api/context/links', json={'read_links': False})
    assert response.json()['read_links'] is False
    assert client.get('/api/context').json()['location']['read_links'] is False
    send(client, 'https://harbortimes.example/bridge', 'l4')
    assert fake_reader.calls == []
    assert 'The link the user sent' not in provider.requests[-1]['system']


def test_a_fetch_service_reads_what_this_computer_cannot(client, connected, provider, fake_reader):
    created = client.post('/api/context/services', json={'name': 'Fetcher', 'transport': 'stdio',
                                                          'command': [sys.executable, STANDIN]}).json()
    service = client.post(f"/api/context/services/{created['id']}/check").json()
    assert service['suggestions']['link'] == {'tool': 'fetch_page', 'arguments': {'urls': {'source': 'url'}},
                                              'missing': []}
    wrong = client.put(f"/api/context/services/{created['id']}/tools/link",
                       json={'tool': 'fetch_page', 'arguments': {'urls': {'source': 'place'}}, 'run_in': ['conversation']})
    assert wrong.status_code == 422
    saved = client.put(f"/api/context/services/{created['id']}/tools/link",
                       json={'tool': 'fetch_page', 'arguments': {'urls': {'source': 'url'}},
                             'run_in': ['conversation']}).json()
    disclosure = saved['mappings'][0]['disclosure']
    assert 'It runs when a link you paste in chat cannot be read on this computer.' in disclosure['summary']
    client.post(f"/api/context/services/{created['id']}/tools/link/enable", json={'digest': disclosure['digest']})
    url = 'https://app.example/story'
    sent = send(client, f'read this {url}', 'l5')
    observations = link_observations(client, sent['message']['id'])
    assert [(item['service_name'], item['status'], item['arguments']) for item in observations] == [
        ('Fetcher', 'ok', {'urls': [url]})]
    system = provider.requests[-1]['system']
    assert f'The link the user sent ({url}), opened through Fetcher at' in system
    assert 'The harbor bridge reopened on Monday after repairs.' in system


def test_old_workspaces_accept_the_new_category(tmp_path):
    path = tmp_path / 'old.sqlite3'
    connection = sqlite3.connect(path, isolation_level=None)
    connection.execute('PRAGMA foreign_keys=ON')
    initialize(connection, '2026-10-05T00:00:00Z')
    connection.execute('DROP TABLE context_tools')
    connection.execute("""CREATE TABLE context_tools (
  service_id TEXT NOT NULL REFERENCES context_services(id) ON DELETE CASCADE,
  category TEXT NOT NULL CHECK (category IN ('weather', 'news', 'local_events')),
  tool TEXT NOT NULL, arguments TEXT NOT NULL, run_in TEXT NOT NULL DEFAULT '["conversation"]',
  enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)), approved TEXT, updated_at TEXT NOT NULL,
  PRIMARY KEY (service_id, category))""")
    connection.execute("INSERT INTO context_services (id, name, transport, created_at, updated_at) "
                       "VALUES ('s1', 'Old', 'http', 'now', 'now')")
    connection.execute("INSERT INTO context_tools (service_id, category, tool, arguments, enabled, approved, "
                       "updated_at) VALUES ('s1', 'weather', 'w', '{}', 1, 'digest', 'now')")
    initialize(connection, '2026-10-05T00:00:01Z')
    connection.execute("INSERT INTO context_tools (service_id, category, tool, arguments, updated_at) "
                       "VALUES ('s1', 'link', 'fetch', '{}', 'now')")
    assert connection.execute('SELECT category, enabled, approved FROM context_tools ORDER BY category').fetchall() == \
        [('link', 0, None), ('weather', 1, 'digest')]
    connection.execute("DELETE FROM context_services WHERE id='s1'")
    assert connection.execute('SELECT COUNT(*) FROM context_tools').fetchone()[0] == 0
    connection.close()
