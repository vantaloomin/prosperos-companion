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
from companion.mcp.client import ToolFailure, open_session
from companion.mcp.services import CATEGORIES, active_mappings, destination, place_settings, transport_for

FRESH_FOR = {'weather': timedelta(hours=1), 'news': timedelta(hours=3), 'local_events': timedelta(hours=12)}
HOURLY_LIMIT = 20
DAILY_LIMIT = 100
FAILURE_PAUSE = timedelta(minutes=5)
RETRYABLE = {'timeout', 'transport', 'start_failed'}
RETRY_DELAY = 0.5
CONVERSATION_DEADLINE = 5.0
BACKGROUND_DEADLINE = 20.0
SERVICES_PER_CATEGORY = 2
MAX_CONTENT = 2000
TOPIC_WORDS = 6

WEATHER = re.compile(r"\b(weather|forecast|raining|rainy|snowing|snowy|temperature|umbrella|stormy?|sunny|"
                     r"how (hot|cold|warm) is it|humid)\b", re.I)
NEWS = re.compile(r"\b(news|headlines?|current events|in the world today)\b", re.I)
EVENTS = re.compile(r"\b(things to do|what'?s on|concerts?|festivals?|events?|shows?|gigs?)\b", re.I)
NEARBY = re.compile(r"\b(near( me| here|by)?|around here|in town|local(ly)?|this weekend|tonight|today|tomorrow)\b",
                    re.I)
THERE = re.compile(r"\b(where you (are|live)|your (city|town|place|end|neck of the woods)|over there|by you)\b", re.I)
TOPIC = re.compile(r"\bnews\s+(?:about|on|regarding|for|from)\s+([^?.!,;:\n]{2,80})", re.I)


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
    if EVENTS.search(text) and (NEARBY.search(text) or purpose == 'companion_city'):
        found.append({'category': 'local_events', 'purpose': purpose, 'topic': None})
    return found


def clean(text: str) -> str:
    """Plain text only, bounded, with the quoting marks used in context replaced."""
    text = re.sub(r'[\x00-\x08\x0b-\x1f\x7f]', ' ', text).replace('«', '"').replace('»', '"')
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text if len(text) <= MAX_CONTENT else text[:MAX_CONTENT - 1].rstrip() + '…'


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


def target(connection, purpose: str, world, now) -> dict | None:
    """Where a lookup applies: the user's own location, or the companion's real city (None if it has none)."""
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
    found = city_target(world, companion['version']['definition']) if companion else None
    if found is None:
        return None
    local = now.astimezone(zone(companion['version']['timezone']))
    return {**found, 'date': local.date().isoformat(), 'whose': 'companion'}


def arguments_for(mapping: dict, tools: list[dict], where: dict, topic: str | None) -> dict | None:
    """The mapped arguments with today's values. None when a required value is unavailable."""
    schema = next((tool['input_schema'] for tool in tools if tool['name'] == mapping['tool']), {})
    required = set(schema.get('required') or [])
    values = {'place': where['place'], 'latitude': where['latitude'], 'longitude': where['longitude'],
              'topic': topic, 'date': where['date']}
    arguments = {}
    for name, argument in decode(mapping['arguments']).items():
        value = argument.get('value') if argument['source'] == 'literal' else values.get(argument['source'])
        if value is None or value == '':
            if name in required:
                return None
            continue
        arguments[name] = value
    return arguments


def observation_view(row: dict, now=None) -> dict:
    view = {**row, 'arguments': decode(row['arguments']), 'location': decode(row['location']),
            'structured': decode(row['structured'])}
    view['fresh'] = bool(row['status'] == 'ok' and now and row['fresh_until'] and parse(row['fresh_until']) > now)
    return view


class Lookups:
    def __init__(self, database, vault, world=None, transport_factory=None):
        self.database = database
        self.vault = vault
        self.world = world
        self.transport_factory = transport_factory or (lambda service: transport_for(service, vault))
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
        if not wanted:
            return []
        try:
            batches = await asyncio.wait_for(asyncio.gather(*(
                self.run(item['category'], item['purpose'], item['topic'], CONVERSATION_DEADLINE) for item in wanted)),
                CONVERSATION_DEADLINE + 3)
        except TimeoutError:
            return []
        found = [item for batch in batches for item in batch]
        with self.database.connect(write=True) as connection:
            connection.executemany('INSERT OR IGNORE INTO context_uses (message_id, observation_id) VALUES (?, ?)',
                                   [(user['id'], item['id']) for item in found])
        return found

    async def run(self, category: str, purpose: str, topic: str | None = None,
                  deadline: float = CONVERSATION_DEADLINE) -> list[dict]:
        """Look up one category with each enabled service for it (at most two)."""
        with self.database.connect() as connection:
            mappings = active_mappings(connection, category, purpose)[:SERVICES_PER_CATEGORY]
            where = target(connection, purpose, self.world, self.now()) if mappings else None
        if not mappings or where is None:
            return []
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
                refusal = self.limited(connection, service['id'])
                previous = self.latest(connection, service['id'], mapping['tool'], arguments)
            record = {'service': service, 'category': mapping['category'], 'purpose': purpose, 'tool': mapping['tool'],
                      'arguments': arguments, 'location': where}
            if refusal:
                refused = self.record(**record, status='refused', error_code=refusal[0], error=refusal[1])
                return [refused] + ([observation_view(previous, self.now())] if previous else [])
            return [await self.call(record, deadline)]

    def cached(self, connection, service_id, tool, arguments) -> dict | None:
        return optional(connection, "SELECT * FROM context_observations WHERE service_id=? AND tool=? AND arguments=? "
                        "AND status='ok' AND fresh_until>? ORDER BY retrieved_at DESC LIMIT 1",
                        (service_id, tool, encode(arguments), stamp(self.now())))

    def latest(self, connection, service_id, tool, arguments) -> dict | None:
        return optional(connection, "SELECT * FROM context_observations WHERE service_id=? AND tool=? AND arguments=? "
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
                                                   if result['structured'] else ''))
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
               error_code=None, error=None, attempts=0) -> dict:
        now, observation_id = self.now(), identifier()
        with self.database.connect(write=True) as connection:
            connection.execute(
                'INSERT INTO context_observations (id, service_id, service_name, category, purpose, tool, arguments, '
                'destination, location, status, content, structured, error_code, error, attempts, requested_at, '
                'retrieved_at, fresh_until) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (observation_id, service['id'], service['name'], category, purpose, tool, encode(arguments),
                 destination(service), encode(location), status, content, encode(structured) if structured else None,
                 error_code, error, attempts, stamp(now), stamp(now) if status == 'ok' else None,
                 stamp(now + FRESH_FOR[category]) if status == 'ok' else None))
            if status == 'failed':
                connection.execute('UPDATE context_services SET cooldown_until=? WHERE id=?',
                                   (stamp(now + FAILURE_PAUSE), service['id']))
            return observation_view(one(connection, 'SELECT * FROM context_observations WHERE id=?',
                                        (observation_id,)), now)


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


def context_lines(observations: list[dict], now, user_timezone: str) -> list[tuple[str, str]]:
    """(identity, text) for the reply's context. Stale and failed lookups say what is not known."""
    lines, seen, ok_by_category = [], set(), {}
    for item in observations:
        if item['id'] in seen:
            continue
        seen.add(item['id'])
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
