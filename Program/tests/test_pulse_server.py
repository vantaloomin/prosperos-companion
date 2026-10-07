"""The built-in local pulse server (companion/mcp/servers/pulse.py), against recorded answers."""
import asyncio
import json
import os
import sys
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from companion.mcp import client as mcp
from companion.mcp.servers import pulse

TODAY = date(2026, 10, 5)
RSS = b"""<?xml version="1.0"?><rss><channel>
<item><title>Older story - The Baltimore Banner</title><source>The Baltimore Banner</source>
<pubDate>Sat, 03 Oct 2026 12:00:00 GMT</pubDate></item>
<item><title>Harbor bridge reopens - The Baltimore Sun</title><source>The Baltimore Sun</source>
<pubDate>Mon, 05 Oct 2026 09:00:00 GMT</pubDate></item>
</channel></rss>"""
FEATURED = {'mostread': {'articles': [{'title': 'Main_Page'}, {'title': 'Taylor_Swift', 'normalizedtitle': 'Taylor Swift'},
                                      {'title': 'Special:Search'}, {'title': 'Baltimore_Ravens',
                                                                    'normalizedtitle': 'Baltimore Ravens'}]}}
HOT = {'data': {'children': [{'data': {'title': 'Welcome thread', 'stickied': True}},
                             {'data': {'title': 'Best crab cakes this fall?'}},
                             {'data': {'title': 'Not for work', 'over_18': True}}]}}
PLACES = {'results': [{'name': 'Baltimore', 'latitude': 39.29, 'longitude': -76.61, 'country_code': 'US',
                       'admin1': 'Maryland', 'timezone': 'America/New_York'}]}
AIR = {'current': {'us_aqi': 42.4}, 'timezone': 'America/New_York'}
NFL = {'events': [
    {'date': '2026-10-04T17:00Z', 'status': {'type': {'completed': True}}, 'competitions': [{
        'venue': {'fullName': 'M&T Bank Stadium', 'address': {'city': 'Baltimore', 'state': 'MD'}},
        'competitors': [{'homeAway': 'home', 'score': '24', 'team': {'displayName': 'Baltimore Ravens'}},
                        {'homeAway': 'away', 'score': '17', 'team': {'displayName': 'Los Angeles Rams'}}]}]},
    {'date': '2026-10-11T17:00Z', 'status': {'type': {'completed': False}}, 'competitions': [{
        'venue': {'fullName': 'Acrisure Stadium', 'address': {'city': 'Pittsburgh', 'state': 'PA'}},
        'competitors': [{'homeAway': 'home', 'team': {'displayName': 'Pittsburgh Steelers'}},
                        {'homeAway': 'away', 'team': {'displayName': 'Baltimore Ravens'}}]}]}]}
MLB = {'dates': [{'games': [{'gameDate': '2026-10-06T23:08:00Z', 'status': {'abstractGameState': 'Preview'},
                             'venue': {'name': 'Oriole Park at Camden Yards', 'location': {'city': 'Baltimore'}},
                             'teams': {'home': {'team': {'name': 'Baltimore Orioles'}},
                                       'away': {'team': {'name': 'New York Yankees'}}}}]}]}


def recorded(answers: dict, seen: list | None = None):
    """A client whose requests get the answer for the first matching URL fragment."""
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        for fragment, answer in answers.items():
            if fragment in str(request.url):
                status, body = answer if isinstance(answer, tuple) else (200, answer)
                return httpx.Response(status, content=body) if isinstance(body, bytes) else \
                    httpx.Response(status, json=body)
        return httpx.Response(404, json={})
    return httpx.Client(transport=httpx.MockTransport(handler))


NEWS_ANSWERS = {'news.google.com': RSS, 'wikimedia.org': FEATURED, 'reddit.com/r/baltimore': HOT}


def test_news_for_a_place_brings_headlines_reading_and_the_city_subreddit():
    seen = []
    result = pulse.news({'location': 'Baltimore, MD'}, recorded(NEWS_ANSWERS, seen), TODAY)
    assert result['text'] == ('Headlines about Baltimore (Google News):\n'
                              '- Harbor bridge reopens (The Baltimore Sun, Oct 5)\n'
                              '- Older story (The Baltimore Banner, Oct 3)\n\n'
                              'Most read on English Wikipedia yesterday: Taylor Swift; Baltimore Ravens.\n\n'
                              'Hot on r/baltimore:\n- Best crab cakes this fall?')
    assert result['structured']['sources'] == ['Google News', 'Wikipedia', 'Reddit']
    google = next(request for request in seen if request.url.host == 'news.google.com')
    assert parse_qs(google.url.query.decode())['q'] == ['Baltimore']
    assert any('/2026/10/05' in str(request.url) for request in seen)


def test_news_on_a_topic_sends_only_the_topic():
    seen = []
    result = pulse.news({'location': 'Baltimore, MD', 'topic': 'bridge'}, recorded(NEWS_ANSWERS, seen), TODAY)
    assert result['text'].startswith('Headlines about bridge (Google News):')
    assert [request.url.host for request in seen] == ['news.google.com']
    assert parse_qs(seen[0].url.query.decode())['q'] == ['bridge']


def test_news_keeps_what_worked_and_fails_only_when_nothing_did():
    partial = pulse.news({'location': 'New York, NY'}, recorded({'news.google.com': RSS, 'wikimedia.org': (503, {})}),
                         TODAY)
    assert partial['structured']['sources'] == ['Google News']
    with pytest.raises(pulse.PulseError, match='No headlines could be found'):
        pulse.news({'location': 'Baltimore'}, recorded({}), TODAY)


def test_happenings_list_local_games_with_scores_and_air_quality():
    seen = []
    client = recorded({'geocoding': PLACES, 'air-quality': AIR, 'football/nfl': NFL, 'statsapi.mlb.com': MLB,
                       'espn.com': {'events': []}}, seen)
    result = pulse.happenings({'location': 'Baltimore, MD'}, client, TODAY)
    assert result['text'] == (
        'Pro games in and around Baltimore, MD from yesterday through next week:\n'
        '- Sun Oct 4, 1:00 PM: final, Los Angeles Rams 17, Baltimore Ravens 24 at M&T Bank Stadium (NFL)\n'
        '- Tue Oct 6, 7:08 PM: New York Yankees at Baltimore Orioles at Oriole Park at Camden Yards (MLB)\n'
        'Air quality now: good (US AQI 42). Air quality data by Open-Meteo.com (CC BY 4.0).')
    assert set(result['structured']['leagues_checked']) == {'MLB', 'NFL', 'NBA', 'WNBA', 'NHL', 'MLS'}
    espn = next(request for request in seen if 'football/nfl' in str(request.url))
    assert parse_qs(espn.url.query.decode())['dates'] == ['202610']


def test_a_week_across_two_months_asks_for_both_and_keeps_only_that_week():
    def game(day, home):
        return {'date': f'{day}T17:00Z', 'status': {'type': {'completed': False}}, 'competitions': [{
            'venue': {'fullName': 'M&T Bank Stadium', 'address': {'city': 'Baltimore', 'state': 'MD'}},
            'competitors': [{'homeAway': 'home', 'team': {'displayName': home}},
                            {'homeAway': 'away', 'team': {'displayName': 'Visitors'}}]}]}
    october = {'events': [game('2026-10-01', 'Too early'), game('2026-10-30', 'Ravens in October')]}
    november = {'events': [game('2026-11-03', 'Ravens in November'), game('2026-11-20', 'Too late')]}
    seen = []
    client = recorded({'air-quality': AIR, 'football/nfl/scoreboard?dates=202610': october,
                       'football/nfl/scoreboard?dates=202611': november, 'espn.com': {'events': []},
                       'statsapi': {'dates': []}}, seen)
    found = pulse.happenings({'location': 'Baltimore', 'latitude': 39.3, 'longitude': -76.6}, client, date(2026, 10, 29))
    assert 'Ravens in October' in found['text'] and 'Ravens in November' in found['text']
    assert 'Too early' not in found['text'] and 'Too late' not in found['text']
    nfl = [parse_qs(request.url.query.decode())['dates'] for request in seen if 'football/nfl' in str(request.url)]
    assert nfl == [['202610'], ['202611']]


def test_metro_venues_count_and_no_games_is_said_plainly():
    giants = {'events': [{'date': '2026-10-05T23:15Z', 'status': {'type': {'completed': False}}, 'competitions': [{
        'venue': {'fullName': 'MetLife Stadium', 'address': {'city': 'East Rutherford', 'state': 'NJ'}},
        'competitors': [{'homeAway': 'home', 'team': {'displayName': 'New York Giants'}},
                        {'homeAway': 'away', 'team': {'displayName': 'Dallas Cowboys'}}]}]}]}
    found = pulse.happenings({'location': 'New York', 'latitude': 40.7, 'longitude': -74.0},
                             recorded({'air-quality': AIR, 'football/nfl': giants, 'espn.com': {'events': []},
                                       'statsapi': {'dates': []}}), TODAY)
    assert 'Dallas Cowboys at New York Giants at MetLife Stadium (NFL)' in found['text']
    quiet = pulse.happenings({'location': 'Boise', 'latitude': 43.6, 'longitude': -116.2},
                             recorded({'air-quality': AIR, 'espn.com': {'events': []}, 'statsapi': {'dates': []}}),
                             date(2026, 7, 1))
    assert quiet['text'].startswith('No MLB, WNBA, MLS games in Boise from yesterday through next week.')


def test_failures_are_tool_errors():
    def unreachable(request):
        raise httpx.ConnectError('down')
    down = httpx.Client(transport=httpx.MockTransport(unreachable))
    result = pulse.call('get_local_happenings', {'location': 'Baltimore', 'latitude': 1, 'longitude': 2}, down, TODAY)
    assert result['isError'] is True and result['content'][0]['text'].startswith('Nothing could be looked up.')
    assert pulse.call('get_local_news', {}, down, TODAY)['isError'] is True
    assert pulse.call('send_email', {}, down, TODAY)['isError'] is True


def todays_nfl():
    """The recorded game moved to today, since the program filters games by its own date."""
    return {'events': [{**NFL['events'][0], 'date': f'{date.today():%Y-%m-%d}T17:00Z'}]}


class Recorded(BaseHTTPRequestHandler):
    """The pulse's services on 127.0.0.1, for the server run as a real program."""
    requests: list = []

    def do_GET(self):
        url = urlparse(self.path)
        Recorded.requests.append(url.path)
        bodies = {'/news': RSS, '/geocoding': PLACES, '/air': AIR, '/mlb': MLB}
        body = bodies.get(url.path) or (todays_nfl() if 'football' in url.path else FEATURED if url.path.startswith('/wiki')
                                       else HOT if url.path.startswith('/r/') else {'events': []})
        self.send_response(200)
        self.send_header('Content-Type', 'application/xml' if isinstance(body, bytes) else 'application/json')
        self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else json.dumps(body).encode())

    def log_message(self, *args):
        pass


@pytest.fixture
def services(monkeypatch):
    server = ThreadingHTTPServer(('127.0.0.1', 0), Recorded)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    monkeypatch.setenv('PROSPERO_PULSE_ENDPOINTS', json.dumps(
        {'news': f'{base}/news', 'wikipedia': f'{base}/wiki', 'reddit': f'{base}/r', 'espn': f'{base}/espn',
         'mlb': f'{base}/mlb', 'geocoding': f'{base}/geocoding', 'air': f'{base}/air'}))
    monkeypatch.setenv('NO_PROXY', '127.0.0.1')
    Recorded.requests = []
    yield Recorded.requests
    server.shutdown()


def test_runs_as_a_program_over_stdio(services):
    env = {key: os.environ[key] for key in ('PROSPERO_PULSE_ENDPOINTS', 'NO_PROXY')}

    async def scenario():
        transport = mcp.StdioTransport([sys.executable, '-I', pulse.__file__], env)
        async with mcp.open_session(transport) as session:
            return session.server, await session.list_tools(), await session.call_tool(
                'get_local_news', {'location': 'Baltimore, MD', 'topic': 'bridge'})

    server, tools, result = asyncio.run(scenario())
    assert server['name'] == 'prospero-pulse'
    assert [(tool['name'], tool['read_only']) for tool in tools] == [('get_local_news', True),
                                                                     ('get_local_happenings', True)]
    assert result['text'].startswith('Headlines about bridge (Google News):\n- Harbor bridge reopens')
    assert services == ['/news']


def test_built_in_pulse_in_the_app(client, companion, services):
    client.put('/api/context/location', json={'user_place': 'Baltimore, MD'})
    created = client.post('/api/context/services/builtin', json={'kind': 'pulse'})
    assert created.status_code == 200, created.text
    service = created.json()
    assert (service['name'], service['builtin']) == ('Built-in local pulse', 'pulse')
    checked = client.post(f"/api/context/services/{service['id']}/check").json()
    assert checked['check_error'] is None
    assert checked['suggestions']['news']['tool'] == 'get_local_news'
    assert checked['suggestions']['local_events'] == {'tool': 'get_local_happenings',
                                                      'arguments': {'location': {'source': 'place'}}, 'missing': []}
    path = f"/api/context/services/{service['id']}/tools/local_events"
    saved = client.put(path, json={'tool': 'get_local_happenings', 'arguments': {'location': {'source': 'place'}},
                                   'run_in': ['conversation']}).json()
    disclosure = next(item for item in saved['mappings'] if item['category'] == 'local_events')['disclosure']
    assert 'Google News' in disclosure['destination'] and 'ESPN' in disclosure['destination']
    assert client.post(f'{path}/enable', json={'digest': disclosure['digest']}).status_code == 200
    found = client.post('/api/context/lookup', json={'category': 'local_events'}).json()['observations']
    assert found[0]['status'] == 'ok', found[0]
    assert found[0]['arguments'] == {'location': 'Baltimore, MD'}
    assert 'Baltimore Ravens 24 at M&T Bank Stadium (NFL)' in found[0]['content']
