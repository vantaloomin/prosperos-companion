"""The built-in local pulse server: a read-only MCP server on stdio, needing no key (PRD X1-X3).

Run as `python companion/mcp/servers/pulse.py`; the app starts it for each lookup. Two tools:

- `get_local_news(location, topic?)`: headlines from Google News's public RSS search, for the topic
  when one is given, else for the place; without a topic it adds what people are reading on
  Wikipedia today and the hot posts in the city's subreddit.
- `get_local_happenings(location, latitude?, longitude?)`: pro games played in or near the city from
  yesterday through the next six days, with final scores for games already played (MLB's free stats
  API, and ESPN's public scoreboards for the NFL, NBA, WNBA, NHL and MLS), and today's air quality
  from Open-Meteo.

Only the place name, coordinates or topic leave the computer. ESPN's scoreboards are unofficial
and can change without notice; each source that fails is left out, and the lookup fails only when
every one does. `PROSPERO_PULSE_ENDPOINTS` (JSON) overrides the service addresses, for tests.
"""
import json
import os
import sys
import xml.etree.ElementTree as ElementTree
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

PROTOCOL_VERSIONS = ('2025-11-25', '2025-06-18', '2025-03-26')
VERSION = '1.0'
USER_AGENT = 'ProsperoCompanion/1.0 (built-in local pulse server)'
ENDPOINTS = {'news': 'https://news.google.com/rss/search',
             'wikipedia': 'https://api.wikimedia.org/feed/v1/wikipedia/en/featured',
             'reddit': 'https://www.reddit.com/r',
             'espn': 'https://site.api.espn.com/apis/site/v2/sports',
             'mlb': 'https://statsapi.mlb.com/api/v1/schedule',
             'geocoding': 'https://geocoding-api.open-meteo.com/v1/search',
             'air': 'https://air-quality-api.open-meteo.com/v1/air-quality'}
TIMEOUT = 6
HEADLINES = 6
READING = 5
POSTS = 5
DAYS_AHEAD = 6
# ESPN leagues by (sport, league), with the months each one plays in.
LEAGUES = {('football', 'nfl'): ('NFL', {9, 10, 11, 12, 1, 2}), ('basketball', 'nba'): ('NBA', {10, 11, 12, 1, 2, 3, 4, 5, 6}),
           ('basketball', 'wnba'): ('WNBA', {5, 6, 7, 8, 9, 10}), ('hockey', 'nhl'): ('NHL', {10, 11, 12, 1, 2, 3, 4, 5, 6}),
           ('soccer', 'usa.1'): ('MLS', {2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12})}
MLB_MONTHS = {3, 4, 5, 6, 7, 8, 9, 10, 11}
# Cities whose teams play in a neighboring town, and subreddits not named after the city.
METRO = {'new york': {'new york', 'bronx', 'queens', 'brooklyn', 'east rutherford', 'elmont', 'newark', 'harrison'},
         'miami': {'miami', 'miami gardens', 'sunrise', 'fort lauderdale'},
         'las vegas': {'las vegas', 'paradise', 'henderson'}, 'los angeles': {'los angeles', 'inglewood', 'carson',
                                                                             'anaheim'},
         'san francisco': {'san francisco', 'santa clara', 'san jose'}, 'dallas': {'dallas', 'arlington', 'frisco'},
         'washington': {'washington', 'landover'}, 'boston': {'boston', 'foxborough'}}
SUBREDDITS = {'new york': 'nyc', 'las vegas': 'vegas', 'san diego': 'sandiego', 'los angeles': 'LosAngeles',
              'san francisco': 'sanfrancisco', 'washington': 'washingtondc'}
AQI = ((50, 'good'), (100, 'moderate'), (150, 'unhealthy for sensitive groups'), (200, 'unhealthy'),
       (300, 'very unhealthy'), (10 ** 6, 'hazardous'))
SKIPPED_PAGES = ('Main_Page', 'Special:', 'Wikipedia:', 'Portal:', 'File:', 'Help:')

TOOLS = [
    {'name': 'get_local_news',
     'description': "Local headlines for a city or a topic; without a topic, also what people are reading on "
                    "Wikipedia today and the hot posts in the city's subreddit.",
     'inputSchema': {'type': 'object', 'properties': {
         'location': {'type': 'string', 'description': 'City or region, such as "Baltimore, MD".'},
         'topic': {'type': 'string', 'description': 'Optional; headlines about this instead of the place.'}},
         'required': ['location']},
     'annotations': {'readOnlyHint': True, 'openWorldHint': True}},
    {'name': 'get_local_happenings',
     'description': 'Pro sports games in or near a city from yesterday through the next six days, with final '
                    "scores, and today's air quality.",
     'inputSchema': {'type': 'object', 'properties': {
         'location': {'type': 'string', 'description': 'City or region, such as "Baltimore, MD".'},
         'latitude': {'type': 'number', 'description': 'Optional; used instead of looking up the place.'},
         'longitude': {'type': 'number', 'description': 'Optional; used with latitude.'}},
         'required': ['location']},
     'annotations': {'readOnlyHint': True, 'openWorldHint': True}},
]


class PulseError(Exception):
    pass


def endpoints() -> dict:
    return ENDPOINTS | json.loads(os.environ.get('PROSPERO_PULSE_ENDPOINTS') or '{}')


def fetch(client, url, params=None) -> httpx.Response:
    try:
        response = client.get(url, params=params)
    except httpx.HTTPError as error:
        raise PulseError(f'{httpx.URL(url).host} could not be reached.') from error
    if response.status_code != 200:
        raise PulseError(f'{httpx.URL(url).host} answered with HTTP {response.status_code}.')
    return response


def get_json(client, url, params=None) -> dict:
    try:
        return fetch(client, url, params).json()
    except ValueError as error:
        raise PulseError(f'{httpx.URL(url).host} sent an unreadable answer.') from error


def city_of(location: str) -> str:
    return location.split(',')[0].strip()


def text_of(value) -> str:
    return ' '.join(str(value or '').split())


# --- News ---

def headlines(client, query: str) -> list[str]:
    """Google News's top results for a query, newest first, as "title (source, Mon D)"."""
    try:
        root = ElementTree.fromstring(fetch(client, endpoints()['news'], {
            'q': query, 'hl': 'en-US', 'gl': 'US', 'ceid': 'US:en'}).content)
    except ElementTree.ParseError as error:
        raise PulseError('Google News sent an unreadable answer.') from error
    found = []
    for item in root.iter('item'):
        title, source = text_of(item.findtext('title')), text_of(item.findtext('source'))
        if source and title.endswith(f' - {source}'):
            title = title[:-len(source) - 3]
        try:
            published = parsedate_to_datetime(item.findtext('pubDate') or '')
        except (TypeError, ValueError):
            published = None
        found.append((published or datetime.min.replace(tzinfo=timezone.utc), title, source))
    found.sort(key=lambda item: item[0], reverse=True)
    return [f"{title} ({', '.join(part for part in (source, short_date(published)) if part)})"
            for published, title, source in found[:HEADLINES] if title]


def short_date(moment: datetime) -> str:
    return '' if moment.year == 1 else f'{moment:%b} {moment.day}'


def most_read(client, day: date) -> list[str]:
    """English Wikipedia's most-read articles from the day's featured feed, which lists the day before's."""
    data = get_json(client, f"{endpoints()['wikipedia']}/{day:%Y/%m/%d}")
    articles = (data.get('mostread') or {}).get('articles') or []
    titles = [text_of(item.get('normalizedtitle') or item.get('title')) for item in articles
              if not str(item.get('title') or '').startswith(SKIPPED_PAGES)]
    return [title for title in titles if title][:READING]


def subreddit_posts(client, location: str) -> tuple[str, list[str]]:
    city = city_of(location).lower()
    name = SUBREDDITS.get(city, city.replace(' ', ''))
    data = get_json(client, f"{endpoints()['reddit']}/{name}/hot.json", {'limit': 12, 'raw_json': 1})
    posts = [child.get('data') or {} for child in (data.get('data') or {}).get('children') or []]
    return name, [text_of(post.get('title')) for post in posts if not post.get('stickied') and not post.get('over_18')
                  and post.get('title')][:POSTS]


def news(arguments: dict, client, today: date) -> dict:
    location = str(arguments.get('location') or '').strip()[:120]
    topic = str(arguments.get('topic') or '').strip()[:120]
    if not location and not topic:
        raise PulseError('Give a location or a topic.')
    parts, sources, errors = [], [], []

    def attempt(label, run):
        try:
            return run()
        except PulseError as error:
            errors.append(f'{label}: {error}')
            return None

    jobs = {'news': lambda: headlines(client, topic or city_of(location))}
    if not topic:
        jobs['reading'] = lambda: most_read(client, today)
        jobs['reddit'] = lambda: subreddit_posts(client, location)
    with ThreadPoolExecutor(len(jobs)) as pool:
        futures = {key: pool.submit(attempt, key, job) for key, job in jobs.items()}
        found = {key: future.result() for key, future in futures.items()}
    if found['news']:
        parts.append(f"Headlines about {topic or city_of(location)} (Google News):\n" +
                     '\n'.join(f'- {line}' for line in found['news']))
        sources.append('Google News')
    if found.get('reading'):
        parts.append('Most read on English Wikipedia yesterday: ' + '; '.join(found['reading']) + '.')
        sources.append('Wikipedia')
    if found.get('reddit') and found['reddit'][1]:
        name, posts = found['reddit']
        parts.append(f'Hot on r/{name}:\n' + '\n'.join(f'- {post}' for post in posts))
        sources.append('Reddit')
    if not parts:
        raise PulseError('No headlines could be found. ' + ' '.join(errors))
    return {'text': '\n\n'.join(parts), 'structured': {'location': location, 'topic': topic or None,
                                                       'headlines': found['news'] or [],
                                                       'most_read': found.get('reading') or [],
                                                       'subreddit_posts': (found.get('reddit') or ('', []))[1],
                                                       'sources': sources}}


# --- Happenings ---

def place_for(client, arguments: dict) -> dict:
    location = str(arguments.get('location') or '').strip()[:120]
    latitude, longitude = arguments.get('latitude'), arguments.get('longitude')
    if isinstance(latitude, (int, float)) and isinstance(longitude, (int, float)):
        return {'label': location or f'{latitude}, {longitude}', 'city': city_of(location).lower(),
                'latitude': float(latitude), 'longitude': float(longitude), 'timezone': None}
    if not location:
        raise PulseError('Give a location.')
    name, _, qualifier = location.partition(',')
    results = get_json(client, endpoints()['geocoding'], {'name': name.strip(), 'count': 10,
                                                         'format': 'json'}).get('results') or []
    if not results:
        raise PulseError(f'No place called {name.strip()} was found.')
    wanted = qualifier.strip().lower()
    chosen = next((item for item in results if wanted and any(
        wanted == str(item.get(key) or '').lower() or (len(wanted) > 2 and wanted in str(item.get(key) or '').lower())
        for key in ('admin1', 'country', 'country_code'))), results[0])
    return {'label': location, 'city': name.strip().lower(), 'latitude': chosen['latitude'],
            'longitude': chosen['longitude'], 'timezone': chosen.get('timezone')}


def air_quality(client, place: dict) -> tuple[str, str | None]:
    data = get_json(client, endpoints()['air'], {'latitude': place['latitude'], 'longitude': place['longitude'],
                                                 'current': 'us_aqi', 'timezone': 'auto'})
    value = (data.get('current') or {}).get('us_aqi')
    if value is None:
        raise PulseError('Open-Meteo sent no air quality for this place.')
    value = round(value)
    return f"Air quality now: {next(label for limit, label in AQI if value <= limit)} (US AQI {value}). " \
           'Air quality data by Open-Meteo.com (CC BY 4.0).', data.get('timezone')


def local_cities(place: dict) -> set[str]:
    return METRO.get(place['city'], {place['city']})


def espn_games(client, league: tuple, start: date, end: date, cities: set[str]) -> list[dict]:
    sport, code = league
    data = get_json(client, f"{endpoints()['espn']}/{sport}/{code}/scoreboard",
                    {'dates': f'{start:%Y%m%d}-{end:%Y%m%d}', 'limit': 300})
    found = []
    for event in data.get('events') or []:
        competition = (event.get('competitions') or [{}])[0]
        venue = competition.get('venue') or {}
        if str((venue.get('address') or {}).get('city') or '').lower() not in cities:
            continue
        sides = {item.get('homeAway'): item for item in competition.get('competitors') or []}
        home, away = sides.get('home') or {}, sides.get('away') or {}
        finished = bool(((event.get('status') or {}).get('type') or {}).get('completed'))
        found.append({'league': LEAGUES[league][0], 'start': event.get('date'), 'venue': text_of(venue.get('fullName')),
                      'home': text_of((home.get('team') or {}).get('displayName')),
                      'away': text_of((away.get('team') or {}).get('displayName')), 'final': finished,
                      'home_score': home.get('score') if finished else None,
                      'away_score': away.get('score') if finished else None})
    return found


def mlb_games(client, start: date, end: date, cities: set[str]) -> list[dict]:
    data = get_json(client, endpoints()['mlb'], {'sportId': 1, 'startDate': start.isoformat(),
                                                'endDate': end.isoformat(), 'hydrate': 'venue(location)'})
    found = []
    for day in data.get('dates') or []:
        for game in day.get('games') or []:
            venue = game.get('venue') or {}
            if str((venue.get('location') or {}).get('city') or '').lower() not in cities:
                continue
            teams = game.get('teams') or {}
            finished = ((game.get('status') or {}).get('abstractGameState')) == 'Final'
            found.append({'league': 'MLB', 'start': game.get('gameDate'), 'venue': text_of(venue.get('name')),
                          'home': text_of(((teams.get('home') or {}).get('team') or {}).get('name')),
                          'away': text_of(((teams.get('away') or {}).get('team') or {}).get('name')),
                          'final': finished,
                          'home_score': (teams.get('home') or {}).get('score') if finished else None,
                          'away_score': (teams.get('away') or {}).get('score') if finished else None})
    return found


def zone_of(name: str | None):
    try:
        return ZoneInfo(name) if name else timezone.utc
    except (ZoneInfoNotFoundError, ValueError):
        return timezone.utc


def game_line(game: dict, zone) -> str:
    try:
        start = datetime.fromisoformat(str(game['start']).replace('Z', '+00:00')).astimezone(zone)
        when = f"{start:%a %b} {start.day}, {start.hour % 12 or 12}:{start:%M} {'AM' if start.hour < 12 else 'PM'}"
    except ValueError:
        when = 'Date unknown'
    at = f" at {game['venue']}" if game['venue'] else ''
    if game['final'] and game['home_score'] is not None:
        return (f"{when}: final, {game['away']} {game['away_score']}, {game['home']} {game['home_score']}{at} "
                f"({game['league']})")
    return f"{when}: {game['away']} at {game['home']}{at} ({game['league']})"


def happenings(arguments: dict, client, today: date) -> dict:
    place = place_for(client, arguments)
    start, end = today - timedelta(days=1), today + timedelta(days=DAYS_AHEAD)
    cities, errors = local_cities(place), []
    jobs = {'air': lambda: air_quality(client, place)}
    if today.month in MLB_MONTHS:
        jobs['MLB'] = lambda: mlb_games(client, start, end, cities)
    for league, (label, months) in LEAGUES.items():
        if today.month in months:
            jobs[label] = lambda league=league: espn_games(client, league, start, end, cities)

    def attempt(label, run):
        try:
            return run()
        except PulseError as error:
            errors.append(f'{label}: {error}')
            return None

    with ThreadPoolExecutor(len(jobs)) as pool:
        futures = {key: pool.submit(attempt, key, job) for key, job in jobs.items()}
        found = {key: future.result() for key, future in futures.items()}
    air, zone_name = found.pop('air') or (None, None)
    zone = zone_of(place['timezone'] or zone_name)
    games = sorted((game for key, value in found.items() for game in value or []), key=lambda game: str(game['start']))
    if not air and all(value is None for value in found.values()):
        raise PulseError('Nothing could be looked up. ' + ' '.join(errors))
    checked = [key for key, value in found.items() if value is not None]
    parts = []
    if games:
        parts.append(f"Pro games in and around {place['label']} from yesterday through next week:\n" +
                     '\n'.join(f'- {game_line(game, zone)}' for game in games))
    elif checked:
        parts.append(f"No {', '.join(checked)} games in {place['label']} from yesterday through next week.")
    if air:
        parts.append(air)
    return {'text': '\n'.join(parts), 'structured': {'location': place['label'], 'games': games,
                                                     'leagues_checked': checked, 'air_quality': air}}


# --- MCP over stdio ---

def call(name: str, arguments: dict, client, today: date | None = None) -> dict:
    run = {'get_local_news': news, 'get_local_happenings': happenings}.get(name)
    if not run:
        return {'content': [{'type': 'text', 'text': f'Unknown tool {name}.'}], 'isError': True}
    try:
        result = run(arguments, client, today or date.today())
    except PulseError as error:
        return {'content': [{'type': 'text', 'text': str(error)}], 'isError': True}
    return {'content': [{'type': 'text', 'text': result['text']}], 'structuredContent': result['structured']}


def handle(message: dict, client) -> dict | None:
    if 'id' not in message or 'method' not in message:
        return None
    method, params = message['method'], message.get('params') or {}
    if method == 'initialize':
        asked = params.get('protocolVersion')
        result = {'protocolVersion': asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
                  'capabilities': {'tools': {}}, 'serverInfo': {'name': 'prospero-pulse', 'version': VERSION}}
    elif method == 'ping':
        result = {}
    elif method == 'tools/list':
        result = {'tools': TOOLS}
    elif method == 'tools/call':
        result = call(params.get('name'), params.get('arguments') or {}, client)
    else:
        return {'jsonrpc': '2.0', 'id': message['id'], 'error': {'code': -32601, 'message': 'Method not found'}}
    return {'jsonrpc': '2.0', 'id': message['id'], 'result': result}


def main():
    with httpx.Client(timeout=TIMEOUT, headers={'User-Agent': USER_AGENT}, follow_redirects=True) as client:
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                message = json.loads(line)
            except ValueError:
                continue
            response = handle(message, client) if isinstance(message, dict) else None
            if response is not None:
                sys.stdout.write(json.dumps(response) + '\n')
                sys.stdout.flush()


if __name__ == '__main__':
    main()
