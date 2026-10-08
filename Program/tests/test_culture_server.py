"""The built-in culture pulse server (companion/mcp/servers/culture.py), against recorded answers."""
import asyncio
import json
import os
import sys
import threading
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from companion.mcp import client as mcp
from companion.mcp import lookups
from companion.mcp.servers import culture

TODAY = date(2026, 10, 6)
REVIEWS = b"""<?xml version="1.0"?><rss><channel>
<item><title>'Big Movie' review: a slow burn - Variety</title><source>Variety</source>
<pubDate>Tue, 06 Oct 2026 09:00:00 GMT</pubDate></item></channel></rss>"""
TRENDS = b"""<?xml version="1.0"?><rss xmlns:ht="https://trends.google.com/trending/rss"><channel>
<item><title>ravens</title><ht:approx_traffic>200K+</ht:approx_traffic></item></channel></rss>"""
ITUNES = {'feed': {'entry': [{'im:name': {'label': 'Big Movie'}}, {'im:name': {'label': 'Small Movie'}}]}}
TMDB = {'results': [{'title': 'Theater Movie', 'release_date': '2026-10-02', 'vote_average': 7.84, 'vote_count': 120},
                    {'title': 'Brand New', 'release_date': '2026-10-09', 'vote_average': 0, 'vote_count': 0}]}
TV_WEB = [{'number': 1, 'season': 2, '_embedded': {'show': {'name': 'Stream Show', 'weight': 90,
                                                            'webChannel': {'name': 'Netflix'}}}}]
TV = [{'number': 5, 'season': 30, 'show': {'name': 'Network Show', 'weight': 99, 'network': {'name': 'NBC'}}},
      {'number': 6, 'season': 30, 'show': {'name': 'Network Show', 'weight': 99, 'network': {'name': 'NBC'}}}]
STEAM = {'new_releases': {'items': [{'name': 'Space Farm'}, {'name': 'Space Farm'}]},
         'top_sellers': {'items': [{'name': 'Big Shooter'}]}, 'coming_soon': {'items': []}}
SONGS = {'feed': {'results': [{'name': 'Song A', 'artistName': 'Artist A'}]}}
BOOKS = {'works': [{'title': 'A Novel', 'author_name': ['Writer']}]}
FEATURED = {'mostread': {'articles': [{'title': 'Main_Page'}, {'title': 'Big_Movie', 'normalizedtitle': 'Big Movie'}]}}
POPULAR = {'data': {'children': [{'data': {'title': 'A cat', 'subreddit': 'aww'}},
                                 {'data': {'title': 'Adult', 'subreddit': 'x', 'over_18': True}}]}}


def recorded(answers: dict, seen: list | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        for fragment, body in answers.items():
            if fragment in str(request.url):
                return httpx.Response(200, content=body) if isinstance(body, bytes) else httpx.Response(200, json=body)
        return httpx.Response(404, json={})
    return httpx.Client(transport=httpx.MockTransport(handler))


ALL = {'news.google.com': REVIEWS, 'itunes.apple.com': ITUNES, 'tvmaze.com/schedule/web': TV_WEB,
       'tvmaze.com/schedule': TV, 'steampowered.com': STEAM, 'most-played/10/songs': SONGS,
       'most-played/10/albums': {'feed': {'results': []}}, 'openlibrary.org': BOOKS, 'trends.google.com': TRENDS,
       'wikimedia.org': FEATURED, 'reddit.com/r/popular': POPULAR, 'themoviedb.org': TMDB}


def test_sections_come_from_the_topic():
    assert culture.sections_for('movies, tv') == ['movies', 'tv']
    assert culture.sections_for('gaming') == ['games']
    assert culture.sections_for('') == list(culture.SECTIONS)


def test_movies_and_tv(monkeypatch):
    monkeypatch.delenv('TMDB_API_KEY', raising=False)
    seen = []
    result = culture.pulse({'topic': 'movies, tv'}, recorded(ALL, seen), TODAY)
    assert result['text'] == ('Top movies on iTunes (new home releases):\n- Big Movie\n- Small Movie\n\n'
                              "Latest movie reviews and box office (Google News):\n- 'Big Movie' review: a slow burn "
                              '(Variety, Oct 6)\n\n'
                              'On TV and streaming today (TVmaze):\n- Stream Show (Netflix, season 2 premiere)\n'
                              '- Network Show (NBC)')
    assert not any('themoviedb' in str(request.url) for request in seen)
    tv = next(request for request in seen if '/schedule/web' in str(request.url))
    assert parse_qs(tv.url.query.decode()) == {'date': ['2026-10-06'], 'country': ['US']}


def test_a_tmdb_key_adds_theaters_with_ratings(monkeypatch):
    monkeypatch.setenv('TMDB_API_KEY', 'v3key')
    seen = []
    text = culture.pulse({'topic': 'movies'}, recorded(ALL, seen), TODAY)['text']
    assert 'In theaters now (TMDB):\n- Theater Movie (2026-10-02, rated 7.8/10)\n- Brand New (2026-10-09)' in text
    asked = next(request for request in seen if 'now_playing' in str(request.url))
    assert parse_qs(asked.url.query.decode())['api_key'] == ['v3key']
    monkeypatch.setenv('TMDB_API_KEY', 'eyJtoken')
    seen.clear()
    culture.pulse({'topic': 'movies'}, recorded(ALL, seen), TODAY)
    asked = next(request for request in seen if 'now_playing' in str(request.url))
    assert asked.headers['Authorization'] == 'Bearer eyJtoken' and 'api_key' not in str(asked.url)


def test_the_digest_covers_every_section_briefly(monkeypatch):
    monkeypatch.delenv('TMDB_API_KEY', raising=False)
    result = culture.pulse({}, recorded(ALL, None), TODAY)
    for line in ('New on Steam:\n- Space Farm\n\n', 'Top sellers on Steam:\n- Big Shooter',
                 'Most-played songs on Apple Music in the US:\n- Song A by Artist A',
                 'Trending books today (Open Library):\n- A Novel by Writer',
                 'Trending searches in the US (Google Trends):\n- ravens (200K+ searches)',
                 'Most read on English Wikipedia yesterday:\n- Big Movie', 'Hot on Reddit (r/popular):\n- A cat (r/aww)'):
        assert line in result['text']
    assert 'Adult' not in result['text'] and 'Coming soon on Steam' not in result['text']
    assert culture.call('get_culture_pulse', {}, recorded({}), TODAY)['isError'] is True
    assert culture.call('other', {}, recorded({}), TODAY)['isError'] is True


@pytest.mark.parametrize('text, topic', [
    ('Seen any good movies lately?', 'movies'),
    ('What should I binge on Netflix tonight, or play on Steam?', 'tv, games'),
    ("What's trending today?", 'trending'),
    ('I booked a table for us', None),
    ('Read this https://example.com/movies/review', None),
])
def test_chat_triggers(text, topic):
    assert lookups.culture_topic(text) == topic


class Recorded(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        body = {'/itunes': ITUNES, '/news': REVIEWS, '/apple_music/songs.json': SONGS, '/openlibrary': BOOKS}.get(path, {})
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else json.dumps(body).encode())

    def log_message(self, *args):
        pass


@pytest.fixture
def services(monkeypatch):
    server = ThreadingHTTPServer(('127.0.0.1', 0), Recorded)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    monkeypatch.setenv('PROSPERO_CULTURE_ENDPOINTS', json.dumps(
        {'itunes_movies': f'{base}/itunes', 'news': f'{base}/news', 'tmdb': f'{base}/tmdb'}))
    monkeypatch.setenv('NO_PROXY', '127.0.0.1')
    yield
    server.shutdown()


def test_runs_as_a_program_over_stdio(services):
    env = {key: os.environ[key] for key in ('PROSPERO_CULTURE_ENDPOINTS', 'NO_PROXY')}

    async def scenario():
        async with mcp.open_session(mcp.StdioTransport([sys.executable, '-I', culture.__file__], env)) as session:
            return await session.list_tools(), await session.call_tool('get_culture_pulse', {'topic': 'movies'})

    tools, result = asyncio.run(scenario())
    assert [tool['name'] for tool in tools] == ['get_culture_pulse']
    assert result['text'].startswith('Top movies on iTunes (new home releases):\n- Big Movie')


def test_built_in_culture_in_the_app_and_in_chat(client, connected, provider, services):
    created = client.post('/api/context/services/builtin', json={'kind': 'culture'}).json()
    assert (created['name'], created['builtin']) == ('Built-in culture pulse', 'culture')
    checked = client.post(f"/api/context/services/{created['id']}/check").json()
    assert checked['suggestions']['culture'] == {'tool': 'get_culture_pulse', 'arguments': {'topic': {'source': 'topic'}},
                                                 'missing': []}
    path = f"/api/context/services/{created['id']}/tools/culture"
    placed = client.put(path, json={'tool': 'get_culture_pulse', 'arguments': {'topic': {'source': 'place'}},
                                    'run_in': ['conversation']})
    assert placed.status_code == 422
    saved = client.put(path, json={'tool': 'get_culture_pulse', 'arguments': {'topic': {'source': 'topic'}},
                                   'run_in': ['conversation']}).json()
    disclosure = saved['mappings'][0]['disclosure']
    assert 'TVmaze' in disclosure['destination'] and 'TMDB key' in disclosure['destination']
    client.post(f'{path}/enable', json={'digest': disclosure['digest']})
    sent = client.post('/api/conversation/messages', json={'text': 'Seen any good movies lately?',
                                                           'client_id': 'culture-1'}).json()
    [observation] = client.get(f"/api/context/messages/{sent['message']['id']}/observations").json()['observations']
    assert observation['status'] == 'ok', observation
    assert observation['arguments'] == {'topic': 'movies'}
    system = provider.requests[-1]['prompt']
    assert "- Movies, shows, games and what's trending for movies from Built-in culture pulse" in system
    assert 'Big Movie' in system
    # A saved TMDB key reaches only this server, as TMDB_API_KEY, and asks for the lookup to be confirmed again.
    keyed = client.put(f"/api/context/services/{created['id']}", json={
        'name': created['name'], 'transport': 'stdio', 'command': created['command'], 'secret': 'v3key'}).json()
    assert keyed['has_key'] and not keyed['mappings'][0]['enabled']
    from companion.mcp import services as context_services
    with client.app.state.database.connect() as connection:
        row = connection.execute('SELECT * FROM context_services WHERE id=?', (created['id'],)).fetchone()
    transport = context_services.transport_for(dict(row), client.app.state.vault)
    assert transport.env['TMDB_API_KEY'] == 'v3key'


@pytest.fixture
def offline(monkeypatch):
    """Every source on the recorded server, so the digest of every section needs no network."""
    server = ThreadingHTTPServer(('127.0.0.1', 0), Recorded)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    monkeypatch.setenv('PROSPERO_CULTURE_ENDPOINTS', json.dumps({key: f'{base}/{key}' for key in culture.ENDPOINTS}
                                                                | {'itunes_movies': f'{base}/itunes',
                                                                   'news': f'{base}/news'}))
    monkeypatch.setenv('NO_PROXY', '127.0.0.1')
    yield
    server.shutdown()


def builtin_culture(client, run_in, service_id=None):
    if service_id is None:
        service_id = client.post('/api/context/services/builtin', json={'kind': 'culture'}).json()['id']
        client.post(f'/api/context/services/{service_id}/check')
    path = f'/api/context/services/{service_id}/tools/culture'
    saved = client.put(path, json={'tool': 'get_culture_pulse', 'arguments': {'topic': {'source': 'topic'}},
                                   'run_in': run_in})
    assert saved.status_code == 200, saved.text
    disclosure = saved.json()['mappings'][0]['disclosure']
    assert client.post(f'{path}/enable', json={'digest': disclosure['digest']}).status_code == 200
    return disclosure


def ambient_observations(client):
    return [item for item in client.get('/api/context/observations').json()['observations']
            if item['purpose'] == 'ambient']


def test_a_daily_digest_gives_a_sense_of_whats_out(client, app, connected, provider, clock, offline):
    disclosure = builtin_culture(client, ['conversation', 'ambient'])
    assert any('once a day in the background' in line and 'with no topic' in line for line in disclosure['summary'])
    asyncio.run(app.state.life.quietly_observe())
    asyncio.run(app.state.life.quietly_observe())  # asked once a day, not on every tick
    [observation] = ambient_observations(client)
    assert observation['status'] == 'ok', observation
    assert observation['arguments'] == {}  # nothing about the user, not even a topic
    client.post('/api/conversation/messages', json={'text': 'Hey, how was work?', 'client_id': 'ambient-1'})
    system = provider.requests[-1]['prompt']
    assert "## What's out and trending right now" in system
    assert 'you have not watched, played, read or heard any of them' in system
    assert 'Top movies on iTunes (new home releases): Big Movie, Small Movie' in system
    assert 'Most-played songs on Apple Music in the US: Song A by Artist A' in system
    # Lines of the feed can come from it, for today only.
    from companion.life import social
    with app.state.database.connect() as connection:
        companion = client.get('/api/companion').json()['companion']
        assert social.culture_picks(connection, clock.now(), companion['version']['definition']) == {
            'movies': 'Big Movie', 'music': 'Song A by Artist A', 'books': 'A Novel by Writer'}
    facts = {'weather': None, 'body': None, 'culture': {'music': 'Song A by Artist A'}}
    lines = {social.status_text(f'seed-{n}', date(2026, 10, 7), facts, {})[0] for n in range(200)}
    assert "Can't get Song A by Artist A out of my head." in lines
    clock.advance(timedelta(hours=25))
    asyncio.run(app.state.life.quietly_observe())
    assert len(ambient_observations(client)) == 2


def test_no_digest_without_its_switch_or_outside_the_present_day(client, app, connected, provider, offline):
    builtin_culture(client, ['conversation'])
    asyncio.run(app.state.life.quietly_observe())
    assert ambient_observations(client) == []
    builtin_culture(client, ['ambient'], client.get('/api/context').json()['services'][0]['id'])
    companion = client.get('/api/companion').json()['companion']
    definition = {**companion['version']['definition'], 'home_city': 'london-1895', 'timezone': 'Europe/London'}
    client.post('/api/companion/versions', json={'definition': definition,
                                                 'expected_version_id': companion['active_version_id']})
    asyncio.run(app.state.life.quietly_observe())
    assert ambient_observations(client) == []
