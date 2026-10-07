"""When lookups run, what they send and how their results are kept and labelled (PRD X2, X3).

The app decides when to look something up, with fixed rules on the user's message; the model is
never given tools. Each lookup sends only the mapped arguments, reuses a fresh result instead of
asking again, and is bounded: a deadline, at most one retry for a transport failure, hourly and
daily request limits per service, and a pause after a failure. Every attempt is recorded with
its tool, arguments, destination, location, time and freshness, whether it succeeded or not.

Results are external data. They are stored as plain text, quoted in the reply's context under a
heading that says so, and never parsed for instructions or used to call further tools.
"""
import asyncio
import json
import re
from datetime import timedelta

from companion.characters import current
from companion.clock import parse, stamp, zone
from companion.database import decode, encode, identifier, many, one, optional, settings
from companion.mcp import links
from companion.mcp.client import ToolFailure, open_session
from companion.mcp.servers.weather import US_STATES
from companion.mcp.services import CATEGORIES, active_mappings, destination, place_settings, transport_for

FRESH_FOR = {'weather': timedelta(hours=1), 'news': timedelta(hours=3), 'local_events': timedelta(hours=12),
             'link': timedelta(hours=6), 'web_search': timedelta(hours=1), 'culture': timedelta(hours=6)}
# The once-a-day culture digest counts for a day; after a failed try it waits an hour before the next.
FRESH_FOR_PURPOSE = {'ambient': timedelta(hours=24)}
AMBIENT_RETRY = timedelta(hours=1)
# How much of the digest goes into every reply's context, and how many items of each list.
AMBIENT_ITEMS = 2
AMBIENT_CHARS = 1400
HOURLY_LIMIT = 20
DAILY_LIMIT = 100
FAILURE_PAUSE = timedelta(minutes=5)
RETRYABLE = {'timeout', 'transport', 'start_failed'}
RETRY_DELAY = 0.5
CONVERSATION_DEADLINE = 5.0
BACKGROUND_DEADLINE = 20.0
SERVICES_PER_CATEGORY = 2
MAX_CONTENT = 2000
# A linked page is read in full enough to talk about; other lookups are short answers.
MAX_CONTENT_FOR = {'link': links.MAX_TEXT, 'web_search': 4000, 'culture': 3000}
LINK_DEADLINE = 10.0
LINKS_PER_HOUR = 30
# Links read on this computer have no MCP service; their records carry this name instead.
LINK_READER = {'id': None, 'name': 'This computer (link reader)'}
TOPIC_WORDS = 6
SEARCH_WORDS = 12

WEATHER = re.compile(r"\b(weather|forecast|raining|rainy|snowing|snowy|temperature|umbrella|stormy?|sunny|"
                     r"how (hot|cold|warm) is it|humid)\b", re.I)
NEWS = re.compile(r"\b(news|headlines?|current events|in the world today)\b", re.I)
EVENTS = re.compile(r"\b(things to do|what'?s on|concerts?|festivals?|events?|shows?|gigs?)\b", re.I)
NEARBY = re.compile(r"\b(near( me| here|by)?|around here|in town|local(ly)?|this weekend|tonight|today|tomorrow)\b",
                    re.I)
# "Are the Ravens playing this week?": a game word and a time soon, for the games listing of the events lookup.
SPORTS = re.compile(r"\b(games?|match(es)?|playing|kick-?off|first pitch|scores?)\b", re.I)
SOON = re.compile(r"\b(tonight|today|tomorrow|yesterday|last night|this week(end)?|next week|"
                  r"on (mon|tues|wednes|thurs|fri|satur|sun)day)\b", re.I)
THERE = re.compile(r"\b(where you (are|live)|your (city|town|place|end|neck of the woods)|over there|by you)\b", re.I)
TOPIC = re.compile(r"\bnews\s+(?:about|on|regarding|for|from)\s+([^?.!,;:\n]{2,80})", re.I)
# "search for X", "google X", "look up X", "search reddit for X", "search the web for X"
# Only as a request ("can you google…", "please search…", a sentence starting with it), so "I work at Google" or
# "look up at the stars" never searches.
# What's out and trending, by the section of the culture lookup each one asks for.
CULTURE = {
    'movies': re.compile(r"\b(movies?|films?|cinema|box office|in theaters?)\b", re.I),
    'tv': re.compile(r"\b(tv|television|series|netflix|hbo|hulu|disney\+|prime video|streaming|binge(?:-watch)?(?:ing)?|"
                     r"shows? (?:to watch|on))\b", re.I),
    'games': re.compile(r"\b(video ?games?|new games?|gaming|steam|playstation|ps5|xbox|nintendo|switch 2)\b", re.I),
    'music': re.compile(r"\b(albums?|new music|songs?|playlists?|the charts|spotify|apple music)\b", re.I),
    'books': re.compile(r"\b(new books?|good books?|bestsellers?|best-sellers?|reading list|novels?)\b", re.I),
    'trending': re.compile(r"\b(trending|viral|memes?|going on online|on the internet)\b", re.I),
}
SEARCH = re.compile(r"(?:^|[.!?]\s+|\b(?:can|could|would|will)\s+you\s+(?:please\s+)?|\bplease\s+|\b(?:go|to)\s+)"
                    r"(?:search|google|look\s+up(?!\s+(?:at|to|from|and)\b))\s+(?:(?:the\s+)?(?:web|internet|online)\s+)?"
                    r"(?:(reddit|twitter)\s+)?(?:for\s+|about\s+|on\s+)?([^?!.\n]{2,160})", re.I)


def triggers(text: str) -> list[dict]:
    """Which lookups a message asks for. Mentions of the companion's whereabouts target their city."""
    found = []
    purpose = 'companion_city' if THERE.search(text) else 'conversation'
    if WEATHER.search(text):
        found.append({'category': 'weather', 'purpose': purpose, 'topic': None})
    if NEWS.search(text):
        match = TOPIC.search(text)
        topic = ' '.join(match.group(1).split()[:TOPIC_WORDS]) if match else None
        found.append({'category': 'news', 'purpose': 'conversation', 'topic': topic})
    if (EVENTS.search(text) and (NEARBY.search(text) or purpose == 'companion_city')) or \
            (SPORTS.search(text) and SOON.search(text)):
        found.append({'category': 'local_events', 'purpose': purpose, 'topic': None})
    if topic := search_topic(text):
        found.append({'category': 'web_search', 'purpose': 'conversation', 'topic': topic})
    if sections := culture_topic(text):
        found.append({'category': 'culture', 'purpose': 'conversation', 'topic': sections})
    return found


def culture_topic(text: str) -> str | None:
    """Which culture sections a message is about ("movies, tv"), in a fixed order, or None."""
    text = links.URL.sub(' ', text)
    sections = [section for section, pattern in CULTURE.items() if pattern.search(text)]
    return ', '.join(sections) or None


def search_topic(text: str) -> str | None:
    """What the user asked to search for, up to twelve words, with the site they named (Reddit, Twitter)."""
    match = SEARCH.search(links.URL.sub(' ', text))
    if not match:
        return None
    words = match.group(2).split()[:SEARCH_WORDS]
    if not words:
        return None
    site = {'reddit': 'Reddit', 'twitter': 'X (Twitter)'}.get((match.group(1) or '').lower())
    return ' '.join(words) + (f' on {site}' if site else '')


def clean(text: str, limit: int = MAX_CONTENT) -> str:
    """Plain text only, bounded, with the quoting marks used in context replaced."""
    text = re.sub(r'[\x00-\x08\x0b-\x1f\x7f]', ' ', text).replace('«', '"').replace('»', '"')
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text if len(text) <= limit else text[:limit - 1].rstrip() + '…'


def place_key(label: str) -> tuple[str, str]:
    """(city, region) in lower case, with a US state abbreviation spelled out."""
    parts = [part.strip().lower() for part in (label or '').split(',')]
    region = parts[1] if len(parts) > 1 else ''
    return parts[0], US_STATES.get(region.upper(), region).lower()


def same_place(first: str, second: str) -> bool:
    """Whether two typed places name the same city and region ("Paris" and "Paris, Texas" do not)."""
    (city, region), (other_city, other_region) = place_key(first), place_key(second)
    return bool(city) and city == other_city and region == other_region


def city_target(world, definition: dict) -> dict | None:
    """A built-in or user city the companion lives in, when it is a real, modern place."""
    city = definition.get('home_city') or definition.get('location') or ''
    finder = getattr(world, 'find', None)
    data = finder(city) if finder and city else None
    if not data or data.get('setting') != 'real' or data.get('era', 'modern') != 'modern':
        return None
    hoods = data.get('neighborhoods') or []
    latitude = round(sum(hood['lat'] for hood in hoods) / len(hoods), 3) if hoods else None
    longitude = round(sum(hood['lon'] for hood in hoods) / len(hoods), 3) if hoods else None
    return {'label': f"{data['name']}, {data['region']}", 'place': f"{data['name']}, {data['region']}",
            'latitude': latitude, 'longitude': longitude, 'city': data['id']}


def present_day(world, definition: dict) -> bool:
    """Whether the companion lives now: a modern city, or one the world data does not know (written in by hand).
    A companion in 1920s Chicago or a far future has no use for today's charts."""
    city = definition.get('home_city') or definition.get('location') or ''
    finder = getattr(world, 'find', None)
    return modern(finder(city) if finder and city else None)


def modern(data: dict | None) -> bool:
    return not data or data.get('era', 'modern') == 'modern'


def target(connection, purpose: str, world, now) -> dict | None:
    """Where a lookup applies: the user's own location, the companion's real city (None if it has none), or,
    for the daily culture digest, nowhere at all (None when the companion does not live in the present day)."""
    if purpose == 'conversation':
        # Without a location only lookups that send none (such as general news) can run.
        place = place_settings(connection)
        local = now.astimezone(zone(settings(connection)['user_timezone']))
        coordinates = f"{place['user_latitude']}, {place['user_longitude']}" if place['user_latitude'] is not None \
            else None
        label = place['user_place'] or coordinates or ''
        return {'label': label, 'place': label or None, 'latitude': place['user_latitude'],
                'longitude': place['user_longitude'], 'date': local.date().isoformat(), 'whose': 'user'}
    companion = current(connection)
    if purpose == 'ambient':
        if not companion or not present_day(world, companion['version']['definition']):
            return None
        local = now.astimezone(zone(companion['version']['timezone']))
        return {'label': '', 'place': None, 'latitude': None, 'longitude': None, 'date': local.date().isoformat(),
                'whose': None}
    found = city_target(world, companion['version']['definition']) if companion else None
    if found is None:
        return None
    local = now.astimezone(zone(companion['version']['timezone']))
    return {**found, 'date': local.date().isoformat(), 'whose': 'companion'}


def arguments_for(mapping: dict, tools: list[dict], where: dict, topic: str | None) -> dict | None:
    """The mapped arguments with today's values. None when a required value is unavailable."""
    schema = next((tool['input_schema'] for tool in tools if tool['name'] == mapping['tool']), {})
    required = set(schema.get('required') or [])
    properties = schema.get('properties') if isinstance(schema.get('properties'), dict) else {}
    values = {'place': where['place'], 'latitude': where['latitude'], 'longitude': where['longitude'],
              'topic': topic, 'date': where['date'], 'url': where.get('url')}
    arguments = {}
    for name, argument in decode(mapping['arguments']).items():
        value = argument.get('value') if argument['source'] == 'literal' else values.get(argument['source'])
        if value is None or value == '':
            if name in required:
                return None
            continue
        # A tool that takes a list (such as `urls` or `search_queries`) gets a list of one.
        wants_list = isinstance(properties.get(name), dict) and properties[name].get('type') == 'array'
        arguments[name] = [value] if wants_list and argument['source'] != 'literal' else value
    return arguments


def observation_view(row: dict, now=None) -> dict:
    view = {**row, 'arguments': decode(row['arguments']), 'location': decode(row['location']),
            'structured': decode(row['structured'])}
    view['fresh'] = bool(row['status'] == 'ok' and now and row['fresh_until'] and parse(row['fresh_until']) > now)
    return view


class Lookups:
    def __init__(self, database, vault, world=None, transport_factory=None, reader=None):
        self.database = database
        self.vault = vault
        self.world = world
        self.transport_factory = transport_factory or (lambda service: transport_for(service, vault))
        self.reader = reader or links.Reader()
        self.locks: dict[str, asyncio.Lock] = {}
        # Called with each successful observation, such as to give the simulated day real weather.
        self.listeners = []

    def now(self):
        return self.database.clock.now()

    async def for_message(self, user) -> list[dict]:
        """Lookups a user message asks for, once: a retry or an alternative reuses the same results."""
        with self.database.connect() as connection:
            linked = many(connection, 'SELECT o.* FROM context_observations o JOIN context_uses u '
                          'ON u.observation_id=o.id WHERE u.message_id=? ORDER BY o.requested_at, o.rowid', (user['id'],))
        if linked:
            return [observation_view(row, self.now()) for row in linked]
        wanted = triggers(user['text'])
        with self.database.connect() as connection:
            reading = bool(place_settings(connection)['read_links'])
        urls = links.find(user['text']) if reading else []
        if not wanted and not urls:
            return []
        batches = await asyncio.gather(self.bounded(wanted), self.bounded_links(urls))
        found = [item for batch in batches for item in batch]
        with self.database.connect(write=True) as connection:
            connection.executemany('INSERT OR IGNORE INTO context_uses (message_id, observation_id) VALUES (?, ?)',
                                   [(user['id'], item['id']) for item in found])
        return found

    async def bounded(self, wanted: list[dict]) -> list[dict]:
        if not wanted:
            return []
        try:
            batches = await asyncio.wait_for(asyncio.gather(*(
                self.run(item['category'], item['purpose'], item['topic'], CONVERSATION_DEADLINE) for item in wanted)),
                CONVERSATION_DEADLINE + 3)
        except TimeoutError:
            return []
        return [item for batch in batches for item in batch]

    async def bounded_links(self, urls: list[str]) -> list[dict]:
        if not urls:
            return []
        results = await asyncio.gather(*(self.read_link(url) for url in urls))
        return [item for item in results if item]

    async def read_link(self, url: str, deadline: float = LINK_DEADLINE) -> dict | None:
        """One observation for a pasted link: read on this computer, else by an enabled fetch service, else the
        reason it could not be read (the companion then says so in character, without guessing the content)."""
        loop = asyncio.get_running_loop()
        ends = loop.time() + deadline
        arguments = {'url': url}
        with self.database.connect() as connection:
            cached = self.cached(connection, None, 'read_link', arguments)
            if cached:
                return observation_view(cached, self.now())
            limited = self.links_limited(connection)
            fetchers = active_mappings(connection, 'link', 'conversation')[:SERVICES_PER_CATEGORY]
        where = {'label': links.host_of(url), 'place': None, 'latitude': None, 'longitude': None,
                 'date': self.now().date().isoformat(), 'whose': 'user', 'url': url}
        record = {'service': LINK_READER, 'category': 'link', 'purpose': 'conversation', 'tool': 'read_link',
                  'arguments': arguments, 'location': where, 'where_to': links.host_of(url)}
        if limited:
            local = self.record(**record, status='refused', error_code='rate_limited',
                                error='Too many links were read in the last hour.')
        else:
            try:
                page = await asyncio.wait_for(self.reader.read(url), max(ends - loop.time(), 0.1))
                content = clean(page['text'], MAX_CONTENT_FOR['link'])
                return self.record(**record, status='ok', content=content, attempts=1,
                                   structured={'title': page['title'], 'kind': page['kind'], 'url': page['url']})
            except (ToolFailure, TimeoutError) as error:
                failure = error if isinstance(error, ToolFailure) else ToolFailure('timeout', 'The page took too long.')
                local = self.record(**record, status='failed', error_code=failure.code, error=failure.message,
                                    attempts=1)
        for item in fetchers:
            remaining = ends - loop.time()
            if remaining < 1:
                break
            found = await self.one(item['service'], item['mapping'], where, 'conversation', None, remaining)
            good = next((observation for observation in found if observation['status'] == 'ok'), None)
            if good:
                return good
        return local

    async def ambient(self, deadline: float = BACKGROUND_DEADLINE) -> list[dict]:
        """The daily culture digest, when the user turned it on: asked at most once a day, and after a failed
        or refused try, not again for an hour."""
        with self.database.connect() as connection:
            last = optional(connection, "SELECT status, requested_at, fresh_until FROM context_observations WHERE "
                            "category='culture' AND purpose='ambient' ORDER BY requested_at DESC, rowid DESC LIMIT 1")
        now = self.now()
        if last and (last['status'] == 'ok' and parse(last['fresh_until']) > now
                     or last['status'] != 'ok' and parse(last['requested_at']) > now - AMBIENT_RETRY):
            return []
        return await self.run('culture', 'ambient', None, deadline)

    def links_limited(self, connection) -> bool:
        count = one(connection, "SELECT COUNT(*) AS n FROM context_observations WHERE service_id IS NULL AND "
                    "category='link' AND status<>'refused' AND requested_at>?",
                    (stamp(self.now() - timedelta(hours=1)),))['n']
        return count >= LINKS_PER_HOUR

    async def run(self, category: str, purpose: str, topic: str | None = None,
                  deadline: float = CONVERSATION_DEADLINE) -> list[dict]:
        """Look up one category with each enabled service for it (at most two)."""
        with self.database.connect() as connection:
            mappings = active_mappings(connection, category, purpose)[:SERVICES_PER_CATEGORY]
            where = target(connection, purpose, self.world, self.now()) if mappings else None
        if not mappings or where is None:
            return []
        if category in {'web_search', 'culture'}:
            where = {**where, 'label': topic or ''}  # About what was asked, not where the user is.
        results = await asyncio.gather(*(self.one(item['service'], item['mapping'], where, purpose, topic, deadline)
                                         for item in mappings))
        return [item for batch in results for item in batch]

    async def one(self, service, mapping, where, purpose, topic, deadline) -> list[dict]:
        arguments = arguments_for(mapping, decode(service['tools']), where, topic)
        if arguments is None:
            return []
        key = json.dumps([service['id'], mapping['tool'], arguments], sort_keys=True)
        lock = self.locks.setdefault(key, asyncio.Lock())
        async with lock:
            with self.database.connect() as connection:
                cached = self.cached(connection, service['id'], mapping['tool'], arguments)
                if cached:
                    return [observation_view(cached, self.now())]
                twin = self.same_place(connection, service['id'], mapping, where) if mapping['category'] == 'weather' \
                    else None
                refusal = self.limited(connection, service['id'])
                previous = self.latest(connection, service['id'], mapping['tool'], arguments)
            record = {'service': service, 'category': mapping['category'], 'purpose': purpose, 'tool': mapping['tool'],
                      'arguments': arguments, 'location': where}
            if twin:
                # The user and the companion are in the same place: one lookup serves both.
                shared = self.record(**record, status='ok', content=twin['content'],
                                     structured=decode(twin['structured']), copied_from=twin)
                self.notify(shared)
                return [shared]
            if refusal:
                refused = self.record(**record, status='refused', error_code=refusal[0], error=refusal[1])
                return [refused] + ([observation_view(previous, self.now())] if previous else [])
            return [await self.call(record, deadline)]

    def same_place(self, connection, service_id, mapping, where) -> dict | None:
        """A fresh weather result from the same service and tool for the same place under its other name, such as
        the user's "Baltimore, MD" and the companion's "Baltimore, Maryland"."""
        rows = many(connection, "SELECT * FROM context_observations WHERE service_id IS ? AND tool=? AND "
                    "category='weather' AND status='ok' AND fresh_until>? ORDER BY retrieved_at DESC, rowid DESC LIMIT 10",
                    (service_id, mapping['tool'], stamp(self.now())))
        return next((row for row in rows if same_place((decode(row['location']) or {}).get('label', ''),
                                                       where.get('label', ''))), None)

    def cached(self, connection, service_id, tool, arguments) -> dict | None:
        return optional(connection, "SELECT * FROM context_observations WHERE service_id IS ? AND tool=? AND arguments=? "
                        "AND status='ok' AND fresh_until>? ORDER BY retrieved_at DESC LIMIT 1",
                        (service_id, tool, encode(arguments), stamp(self.now())))

    def latest(self, connection, service_id, tool, arguments) -> dict | None:
        return optional(connection, "SELECT * FROM context_observations WHERE service_id IS ? AND tool=? AND arguments=? "
                        "AND status='ok' ORDER BY retrieved_at DESC LIMIT 1", (service_id, tool, encode(arguments)))

    def limited(self, connection, service_id) -> tuple[str, str] | None:
        now = self.now()
        service = one(connection, 'SELECT cooldown_until FROM context_services WHERE id=?', (service_id,))
        if service['cooldown_until'] and parse(service['cooldown_until']) > now:
            return 'cooling_down', 'Paused after a failed lookup; it will be tried again a little later.'
        counts = one(connection, "SELECT COALESCE(SUM(CASE WHEN requested_at>? THEN attempts END), 0) AS hour, "
                     "COALESCE(SUM(attempts), 0) AS day FROM context_observations WHERE service_id=? AND status<>'refused' "
                     "AND requested_at>?", (stamp(now - timedelta(hours=1)), service_id, stamp(now - timedelta(days=1))))
        if counts['hour'] >= HOURLY_LIMIT or counts['day'] >= DAILY_LIMIT:
            return 'rate_limited', 'The request limit for this service was reached.'
        return None

    async def call(self, record, deadline) -> dict:
        loop = asyncio.get_running_loop()
        ends, attempts = loop.time() + deadline, 0
        while True:
            attempts += 1
            try:
                remaining = max(ends - loop.time(), 0.1)
                async with open_session(self.transport_factory(record['service']), remaining) as session:
                    result = await asyncio.wait_for(session.call_tool(record['tool'], record['arguments']), remaining)
                content = clean(result['text'] or (json.dumps(result['structured'], ensure_ascii=False)
                                                   if result['structured'] else ''),
                                MAX_CONTENT_FOR.get(record['category'], MAX_CONTENT))
                if not content:
                    raise ToolFailure('empty', 'The tool returned nothing usable.')
                observation = self.record(**record, status='ok', content=content, structured=result['structured'],
                                          attempts=attempts)
                self.notify(observation)
                return observation
            except (ToolFailure, TimeoutError) as error:
                failure = error if isinstance(error, ToolFailure) else ToolFailure('timeout', 'The lookup took too long.')
                if failure.code in RETRYABLE and attempts < 2 and ends - loop.time() > RETRY_DELAY + 0.5:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                return self.record(**record, status='failed', error_code=failure.code, error=failure.message,
                                   attempts=attempts)

    def notify(self, observation):
        for listener in self.listeners:
            try:
                listener(observation)
            except Exception:  # noqa: BLE001 - a listener never turns a good lookup into a failure.
                pass

    def record(self, service, category, purpose, tool, arguments, location, status, content='', structured=None,
               error_code=None, error=None, attempts=0, where_to=None, copied_from=None) -> dict:
        """Store one attempt. `copied_from` reuses another result without asking again: it keeps that result's
        retrieval time and freshness and counts as no request."""
        now, observation_id = self.now(), identifier()
        retrieved = copied_from['retrieved_at'] if copied_from else stamp(now) if status == 'ok' else None
        fresh = copied_from['fresh_until'] if copied_from else \
            stamp(now + FRESH_FOR_PURPOSE.get(purpose, FRESH_FOR[category])) if status == 'ok' else None
        with self.database.connect(write=True) as connection:
            connection.execute(
                'INSERT INTO context_observations (id, service_id, service_name, category, purpose, tool, arguments, '
                'destination, location, status, content, structured, error_code, error, attempts, requested_at, '
                'retrieved_at, fresh_until) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (observation_id, service['id'], service['name'], category, purpose, tool, encode(arguments),
                 where_to or destination(service), encode(location), status, content, encode(structured) if structured else None,
                 error_code, error, attempts, stamp(now), retrieved, fresh))
            if status == 'failed' and service['id']:
                connection.execute('UPDATE context_services SET cooldown_until=? WHERE id=?',
                                   (stamp(now + FAILURE_PAUSE), service['id']))
            return observation_view(one(connection, 'SELECT * FROM context_observations WHERE id=?',
                                        (observation_id,)), now)


def fresh_city_events(connection, now) -> dict | None:
    """The latest fresh local-events lookup for the companion's city, for imagining an outing."""
    row = optional(connection, "SELECT * FROM context_observations WHERE category='local_events' AND "
                   "purpose='companion_city' AND status='ok' AND fresh_until>? ORDER BY retrieved_at DESC, rowid DESC "
                   'LIMIT 1', (stamp(now),))
    return observation_view(row, now) if row else None


def fresh_culture(connection, now, definition: dict) -> dict | None:
    """Today's culture digest, while it is fresh: what's out and trending, for the companion to bring up. None
    for a companion who does not live in the present day, even when one asked earlier still is."""
    from companion.life.social import city_data
    if not modern(city_data(connection, definition)):
        return None
    row = optional(connection, "SELECT * FROM context_observations WHERE category='culture' AND purpose='ambient' "
                   "AND status='ok' AND fresh_until>? ORDER BY retrieved_at DESC, rowid DESC LIMIT 1", (stamp(now),))
    return observation_view(row, now) if row else None


def culture_lists(observation: dict) -> dict[str, list[str]]:
    """The digest's lists by title ("Most-played songs on Apple Music in the US": [...]), from its structured part."""
    found = (observation.get('structured') or {}).get('found')
    if not isinstance(found, dict):
        return {}
    lists = {}
    for section in found.values():
        for title, items in (section.items() if isinstance(section, dict) else ()):
            names = [clean(str(item), 160) for item in items if isinstance(item, str) and item.strip()] \
                if isinstance(items, list) else []
            if names:
                lists[clean(str(title), 120)] = names
    return lists


def culture_text(observation: dict) -> str:
    """A short form of the digest for every reply: the top few of each list, or the start of its text."""
    lists = culture_lists(observation)
    if not lists:
        return clean(observation['content'], AMBIENT_CHARS)
    text = '; '.join(f"{title}: {', '.join(items[:AMBIENT_ITEMS])}" for title, items in lists.items())
    return clean(text, AMBIENT_CHARS)


def listing(database, limit=100) -> dict:
    now = database.clock.now()
    with database.connect() as connection:
        rows = many(connection, 'SELECT * FROM context_observations ORDER BY requested_at DESC, rowid DESC LIMIT ?', (limit,))
        return {'observations': [observation_view(row, now) for row in rows]}


def for_reply(database, message_id) -> dict:
    """The observations a user message's reply was given, for the memory details view."""
    now = database.clock.now()
    with database.connect() as connection:
        rows = many(connection, 'SELECT o.* FROM context_observations o JOIN context_uses u ON u.observation_id=o.id '
                    'WHERE u.message_id=? ORDER BY o.requested_at, o.rowid', (message_id,))
        return {'observations': [observation_view(row, now) for row in rows]}


def delete(database, observation_id) -> dict:
    with database.connect(write=True) as connection:
        one(connection, 'SELECT id FROM context_observations WHERE id=?', (observation_id,))
        connection.execute('DELETE FROM context_observations WHERE id=?', (observation_id,))
    return {'deleted': observation_id}


def clear(database) -> dict:
    with database.connect(write=True) as connection:
        count = one(connection, 'SELECT COUNT(*) AS n FROM context_observations')['n']
        connection.execute('DELETE FROM context_observations')
    return {'deleted': count}


def age_text(seconds: float) -> str:
    minutes = int(seconds // 60)
    if minutes < 90:
        return f'{max(minutes, 1)} minutes'
    hours = round(minutes / 60)
    return f'{hours} hours' if hours < 48 else f'{round(hours / 24)} days'


def link_line(item: dict, local: str | None, doing: str | None) -> str:
    """A pasted link: its text when it was read, else what to say, in character, without guessing what it holds."""
    url = (item.get('location') or {}).get('url') or item['arguments'].get('url', '')
    if item['status'] == 'ok':
        how = '' if item['service_id'] is None else f" through {item['service_name']}"
        return (f'- The link the user sent ({url}), opened{how} at {local}. You have looked at it and can talk '
                f"about it: «{item['content']}»")
    fits = f' that fits what you are doing right now ({doing})' if doing else ''
    return (f'- The user sent a link ({links.host_of(url) or url}) that would not open for you. You have not seen '
            'what it contains: do not guess, summarise or pretend to know it. In character, give a brief, natural '
            f'reason it would not load{fits}, such as the site being blocked on a work network, bad signal while '
            'out, or the page just not loading, and ask what it says or for them to paste the text. Never mention '
            'the app, lookups or error codes.')


def context_lines(observations: list[dict], now, user_timezone: str, doing: str | None = None) -> list[tuple[str, str]]:
    """(identity, text) for the reply's context. Stale and failed lookups say what is not known."""
    lines, seen, ok_by_category = [], set(), {}
    for item in observations:
        if item['id'] in seen:
            continue
        seen.add(item['id'])
        if item['category'] == 'link':
            local = parse(item['retrieved_at']).astimezone(zone(user_timezone)).strftime('%d %b %H:%M') \
                if item['retrieved_at'] else None
            lines.append((item['id'], link_line(item, local, doing)))
            continue
        label = CATEGORIES[item['category']]['label'].lower()
        where = (item['location'] or {}).get('label', '')
        whose = ' (the companion\'s real-world city)' if (item['location'] or {}).get('whose') == 'companion' else ''
        place = f' for {where}{whose}' if where else ''
        if item['status'] == 'ok':
            when = parse(item['retrieved_at'])
            local = when.astimezone(zone(user_timezone)).strftime('%d %b %H:%M')
            source = f"{item['service_name']}, tool {item['tool']}"
            quoted = f"«{item['content']}»"
            if parse(item['fresh_until']) > now:
                ok_by_category.setdefault(item['category'], set()).add(item['service_name'])
                lines.append((item['id'], f"- {label.capitalize()}{place} from {source}, retrieved {local}: "
                                          f'{quoted}'))
            else:
                age = age_text((now - when).total_seconds())
                lines.append((item['id'], f'- Out of date: the latest {label} lookup{place} is from {age} ago '
                                          f'({source}). Do not describe it as current: {quoted}'))
        elif item['category'] == 'web_search':
            lines.append((item['id'], f'- The web search{place} did not work, so you have seen no results: do not '
                                      'invent any. Say, in character, that you could not look it up just now, '
                                      'and carry on.'))
        else:
            reason = item['error'] or 'it did not complete'
            lines.append((item['id'], f'- The {label} lookup{place} did not succeed ({reason}). You do not '
                                      f'know the current {label}; say so if it matters, and carry on.'))
    for category, sources in ok_by_category.items():
        if len(sources) > 1:
            label = CATEGORIES[category]['label'].lower()
            lines.append((f'disagree:{category}', f'- These {label} results come from different services and may '
                                                  'disagree; if they do, say you are not sure rather than pick one.'))
    return lines
