"""The built-in culture pulse server: a read-only MCP server on stdio for what's out and what people are into.

Run as `python companion/mcp/servers/culture.py`; the app starts it for each lookup. One tool,
`get_culture_pulse(topic?)`, where the topic names the sections wanted ("movies", "tv, games"); without
one it returns a short digest of every section. Sources need no key:

- movies: the iTunes top movies chart, and the latest movie review and box office headlines (Google News);
  with a TMDB key (`TMDB_API_KEY`, optional), also what's in theaters and coming soon with ratings
- tv: today's US episodes and premieres, broadcast and streaming (TVmaze)
- games: Steam's new releases, top sellers and coming soon, and the latest game review headlines
- music: Apple Music's most-played songs and albums in the US
- books: Open Library's trending books today
- trending: Google Trends' daily searches in the US, English Wikipedia's most-read articles and
  Reddit's r/popular

Nothing about the user is sent: only the fixed queries above. Each source that fails is left out, and
the lookup fails only when every one does. `PROSPERO_CULTURE_ENDPOINTS` (JSON) overrides the service
addresses, for tests.
"""
import json
import os
import sys
import xml.etree.ElementTree as ElementTree
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

PROTOCOL_VERSIONS = ('2025-11-25', '2025-06-18', '2025-03-26')
VERSION = '1.0'
USER_AGENT = 'ProsperoCompanion/1.0 (built-in culture pulse server)'
ENDPOINTS = {'news': 'https://news.google.com/rss/search',
             'itunes_movies': 'https://itunes.apple.com/us/rss/topmovies/limit=10/json',
             'tmdb': 'https://api.themoviedb.org/3',
             'tvmaze': 'https://api.tvmaze.com',
             'steam': 'https://store.steampowered.com/api/featuredcategories',
             'apple_music': 'https://rss.applemarketingtools.com/api/v2/us/music/most-played/10',
             'openlibrary': 'https://openlibrary.org/trending/daily.json',
             'trends': 'https://trends.google.com/trending/rss',
             'wikipedia': 'https://api.wikimedia.org/feed/v1/wikipedia/en/featured',
             'reddit': 'https://www.reddit.com/r/popular/hot.json'}
TIMEOUT = 6
LIMIT = 6
DIGEST_LIMIT = 3
SECTIONS = ('movies', 'tv', 'games', 'music', 'books', 'trending')
ALIASES = {'movie': 'movies', 'film': 'movies', 'films': 'movies', 'cinema': 'movies', 'shows': 'tv',
           'show': 'tv', 'television': 'tv', 'streaming': 'tv', 'game': 'games', 'gaming': 'games',
           'songs': 'music', 'albums': 'music', 'book': 'books', 'reading': 'books', 'internet': 'trending',
           'viral': 'trending', 'online': 'trending'}
SKIPPED_PAGES = ('Main_Page', 'Special:', 'Wikipedia:', 'Portal:', 'File:', 'Help:')
TRENDS = '{https://trends.google.com/trending/rss}'

TOOL = {
    'name': 'get_culture_pulse',
    'description': "What's out and what people are into right now: movie releases and reviews, TV premieres, "
                   'new and top-selling games, the music charts, trending books, and trending searches.',
    'inputSchema': {'type': 'object', 'properties': {
        'topic': {'type': 'string', 'description': 'Optional; the sections wanted, from movies, tv, games, music, '
                                                   'books and trending (such as "movies, tv").'}}},
    'annotations': {'readOnlyHint': True, 'openWorldHint': True},
}


class CultureError(Exception):
    pass


def endpoints() -> dict:
    return ENDPOINTS | json.loads(os.environ.get('PROSPERO_CULTURE_ENDPOINTS') or '{}')


def fetch(client, url, params=None, headers=None) -> httpx.Response:
    try:
        response = client.get(url, params=params, headers=headers)
    except httpx.HTTPError as error:
        raise CultureError(f'{httpx.URL(url).host} could not be reached.') from error
    if response.status_code != 200:
        raise CultureError(f'{httpx.URL(url).host} answered with HTTP {response.status_code}.')
    return response


def get_json(client, url, params=None, headers=None):
    try:
        return fetch(client, url, params, headers).json()
    except ValueError as error:
        raise CultureError(f'{httpx.URL(url).host} sent an unreadable answer.') from error


def get_xml(client, url, params=None):
    try:
        return ElementTree.fromstring(fetch(client, url, params).content)
    except ElementTree.ParseError as error:
        raise CultureError(f'{httpx.URL(url).host} sent an unreadable answer.') from error


def text_of(value) -> str:
    return ' '.join(str(value or '').split())


def sections_for(topic: str) -> list[str]:
    words = [ALIASES.get(word, word) for word in topic.lower().replace(',', ' ').split()]
    return [section for section in SECTIONS if section in words] or list(SECTIONS)


# --- Sources ---

def headlines(client, query: str) -> list[str]:
    """Google News's newest results for a fixed query, as "title (source, Mon D)"."""
    found = []
    for item in get_xml(client, endpoints()['news'], {'q': query, 'hl': 'en-US', 'gl': 'US',
                                                      'ceid': 'US:en'}).iter('item'):
        title, source = text_of(item.findtext('title')), text_of(item.findtext('source'))
        if source and title.endswith(f' - {source}'):
            title = title[:-len(source) - 3]
        try:
            published = parsedate_to_datetime(item.findtext('pubDate') or '')
        except (TypeError, ValueError):
            published = datetime.min.replace(tzinfo=timezone.utc)
        found.append((published, title, source))
    found.sort(key=lambda item: item[0], reverse=True)
    return [f"{title} ({', '.join(part for part in (source, short_date(published)) if part)})"
            for published, title, source in found if title]


def short_date(moment: datetime) -> str:
    return '' if moment.year == 1 else f'{moment:%b} {moment.day}'


def itunes_movies(client) -> list[str]:
    entries = ((get_json(client, endpoints()['itunes_movies']).get('feed') or {}).get('entry')) or []
    return [text_of((entry.get('im:name') or {}).get('label')) for entry in entries
            if (entry.get('im:name') or {}).get('label')]


def tmdb(client, path: str) -> list[str]:
    """Movies from TMDB with their release dates and ratings. Only runs with a key."""
    key = os.environ.get('TMDB_API_KEY', '').strip()
    bearer = key.startswith('eyJ')  # A v4 read access token; otherwise a v3 API key.
    data = get_json(client, f"{endpoints()['tmdb']}{path}", {'region': 'US', 'language': 'en-US',
                                                            **({} if bearer else {'api_key': key})},
                    {'Authorization': f'Bearer {key}'} if bearer else None)
    lines = []
    for movie in data.get('results') or []:
        rating = movie.get('vote_average')
        votes = movie.get('vote_count') or 0
        detail = [part for part in (text_of(movie.get('release_date')),
                                    f'rated {rating:.1f}/10' if rating and votes >= 20 else '') if part]
        lines.append(text_of(movie.get('title')) + (f" ({', '.join(detail)})" if detail else ''))
    return [line for line in lines if line]


def tv_today(client, today: date) -> list[str]:
    """Today's US episodes, streaming and broadcast, premieres first, then the most-followed shows."""
    episodes = []
    for path in ('/schedule/web', '/schedule'):
        episodes += get_json(client, f"{endpoints()['tvmaze']}{path}", {'date': today.isoformat(),
                                                                        'country': 'US'}) or []
    seen, ranked = set(), []
    for episode in episodes:
        show = episode.get('show') or (episode.get('_embedded') or {}).get('show') or {}
        name = text_of(show.get('name'))
        if not name or name in seen:
            continue
        seen.add(name)
        network = text_of((show.get('webChannel') or {}).get('name') or (show.get('network') or {}).get('name'))
        premiere = episode.get('number') == 1
        label = f"season {episode.get('season')} premiere" if premiere and episode.get('season') else ''
        what = ', '.join(part for part in (network, label) if part)
        ranked.append((not premiere, -(show.get('weight') or 0), name + (f' ({what})' if what else '')))
    return [line for _, _, line in sorted(ranked)]


def steam(client) -> dict:
    data = get_json(client, endpoints()['steam'], {'cc': 'us', 'l': 'english'})

    def names(key):
        items = (data.get(key) or {}).get('items') or []
        unique = []
        for item in items:
            name = text_of(item.get('name'))
            if name and name not in unique:
                unique.append(name)
        return unique
    return {'new': names('new_releases'), 'top': names('top_sellers'), 'soon': names('coming_soon')}


def apple_music(client, kind: str) -> list[str]:
    results = ((get_json(client, f"{endpoints()['apple_music']}/{kind}.json").get('feed') or {}).get('results')) or []
    return [f"{text_of(item.get('name'))} by {text_of(item.get('artistName'))}" for item in results
            if item.get('name')]


def books(client) -> list[str]:
    works = get_json(client, endpoints()['openlibrary'], {'limit': 10}).get('works') or []
    return [text_of(work.get('title')) + (f" by {text_of((work.get('author_name') or [''])[0])}"
                                          if work.get('author_name') else '') for work in works if work.get('title')]


def google_trends(client) -> list[str]:
    found = []
    for item in get_xml(client, endpoints()['trends'], {'geo': 'US'}).iter('item'):
        title = text_of(item.findtext('title'))
        traffic = text_of(item.findtext(f'{TRENDS}approx_traffic'))
        if title:
            found.append(title + (f' ({traffic} searches)' if traffic else ''))
    return found


def most_read(client, today: date) -> list[str]:
    data = get_json(client, f"{endpoints()['wikipedia']}/{today:%Y/%m/%d}")
    articles = (data.get('mostread') or {}).get('articles') or []
    return [text_of(item.get('normalizedtitle') or item.get('title')) for item in articles
            if not str(item.get('title') or '').startswith(SKIPPED_PAGES)]


def popular(client) -> list[str]:
    data = get_json(client, endpoints()['reddit'], {'limit': 15, 'raw_json': 1})
    posts = [child.get('data') or {} for child in (data.get('data') or {}).get('children') or []]
    return [f"{text_of(post.get('title'))} (r/{post.get('subreddit')})" for post in posts
            if post.get('title') and not post.get('stickied') and not post.get('over_18')]


# --- Sections ---

def jobs_for(section: str, client, today: date) -> dict:
    """The source calls a section needs, by the line each one fills."""
    if section == 'movies':
        found = {'Top movies on iTunes (new home releases)': lambda: itunes_movies(client),
                 'Latest movie reviews and box office (Google News)':
                     lambda: headlines(client, '"movie review" OR "box office"')}
        if os.environ.get('TMDB_API_KEY', '').strip():
            found['In theaters now (TMDB)'] = lambda: tmdb(client, '/movie/now_playing')
            found['Coming soon to theaters (TMDB)'] = lambda: tmdb(client, '/movie/upcoming')
        return found
    if section == 'tv':
        return {'On TV and streaming today (TVmaze)': lambda: tv_today(client, today)}
    if section == 'games':
        return {'Steam': lambda: steam(client),
                'Latest game reviews (Google News)': lambda: headlines(client, '"game review" OR "video game"')}
    if section == 'music':
        return {'Most-played songs on Apple Music in the US': lambda: apple_music(client, 'songs'),
                'Most-played albums on Apple Music in the US': lambda: apple_music(client, 'albums')}
    if section == 'books':
        return {'Trending books today (Open Library)': lambda: books(client)}
    return {'Trending searches in the US (Google Trends)': lambda: google_trends(client),
            'Most read on English Wikipedia yesterday': lambda: most_read(client, today),
            'Hot on Reddit (r/popular)': lambda: popular(client)}


def lines_for(label: str, value, limit: int) -> list[tuple[str, list[str]]]:
    if label == 'Steam':
        return [(name, items[:limit]) for name, items in (('New on Steam', value['new']),
                                                          ('Top sellers on Steam', value['top']),
                                                          ('Coming soon on Steam', value['soon'])) if items]
    return [(label, value[:limit])] if value else []


def pulse(arguments: dict, client, today: date) -> dict:
    wanted = sections_for(str(arguments.get('topic') or '')[:120])
    limit = LIMIT if len(wanted) <= 2 else DIGEST_LIMIT
    jobs = {(section, label): job for section in wanted for label, job in jobs_for(section, client, today).items()}
    errors = []

    def attempt(key, run):
        try:
            return run()
        except CultureError as error:
            errors.append(f'{key[1]}: {error}')
            return None

    with ThreadPoolExecutor(min(len(jobs), 12)) as pool:
        futures = {key: pool.submit(attempt, key, job) for key, job in jobs.items()}
        found = {key: future.result() for key, future in futures.items()}
    parts, structured = [], {}
    for (section, label), value in found.items():
        for title, items in lines_for(label, value, limit) if value else []:
            parts.append(f'{title}:\n' + '\n'.join(f'- {item}' for item in items))
            structured.setdefault(section, {})[title] = items
    if not parts:
        raise CultureError('Nothing could be looked up. ' + ' '.join(errors))
    return {'text': '\n\n'.join(parts), 'structured': {'sections': wanted, 'found': structured}}


# --- MCP over stdio ---

def call(name: str, arguments: dict, client, today: date | None = None) -> dict:
    if name != TOOL['name']:
        return {'content': [{'type': 'text', 'text': f'Unknown tool {name}.'}], 'isError': True}
    try:
        result = pulse(arguments, client, today or date.today())
    except CultureError as error:
        return {'content': [{'type': 'text', 'text': str(error)}], 'isError': True}
    return {'content': [{'type': 'text', 'text': result['text']}], 'structuredContent': result['structured']}


def handle(message: dict, client) -> dict | None:
    if 'id' not in message or 'method' not in message:
        return None
    method, params = message['method'], message.get('params') or {}
    if method == 'initialize':
        asked = params.get('protocolVersion')
        result = {'protocolVersion': asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
                  'capabilities': {'tools': {}}, 'serverInfo': {'name': 'prospero-culture', 'version': VERSION}}
    elif method == 'ping':
        result = {}
    elif method == 'tools/list':
        result = {'tools': [TOOL]}
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
