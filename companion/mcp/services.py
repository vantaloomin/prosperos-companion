"""Configured MCP services, the user's location, tool mappings and disclosure (PRD X1, X2).

A service is only an address until the user maps one of its tools to a category and confirms the
disclosure: exactly which arguments go to which destination, and when. The confirmation stores a
digest of that disclosure, so any later change to the destination, tool, arguments or timing
needs a new confirmation before a lookup can run.
"""
import hashlib
import json
import re

from companion.database import decode, encode, identifier, many, one, optional
from companion.errors import DomainError, require
from companion.mcp.client import HttpTransport, StdioTransport, ToolFailure, check_url, open_session

CATEGORIES = {
    'weather': {'label': 'Weather', 'keywords': ('weather', 'forecast', 'conditions', 'temperature'),
                'purposes': ('conversation', 'companion_city')},
    'news': {'label': 'News and recent events', 'keywords': ('news', 'headline', 'article', 'current'),
             'purposes': ('conversation',)},
    'local_events': {'label': 'Local events', 'keywords': ('event', 'concert', 'festival', 'things to do', 'happening'),
                     'purposes': ('conversation', 'companion_city')},
}
PURPOSES = {
    'conversation': 'When you ask about it in chat, for your location (or the topic you name)',
    'companion_city': "For the companion's city, when it is a real place: in chat when you ask about where "
                      'they are, and for their simulated day',
}
SOURCES = {
    'place': 'Your city or region as you typed it (the companion\'s city for companion lookups)',
    'latitude': 'The latitude you entered (or the centre of the companion\'s city)',
    'longitude': 'The longitude you entered (or the centre of the companion\'s city)',
    'topic': 'Up to six words naming what you asked about, taken from your message',
    'date': 'Today\'s date where the lookup applies',
    'literal': 'A fixed value you chose',
}
# Schema property names that each source can fill, best first.
FILLS = {
    'place': ('location', 'city', 'place', 'locality', 'address', 'region', 'area', 'where'),
    'latitude': ('latitude', 'lat'),
    'longitude': ('longitude', 'lon', 'lng', 'long'),
    'topic': ('topic', 'query', 'q', 'keywords', 'keyword', 'search', 'term', 'subject'),
    'date': ('date', 'day', 'start_date', 'startdate', 'from'),
}
NEVER_SENT = ('your conversation', 'your memories', 'your name', 'the companion\'s character',
              'API keys of other services')
SERVICE_LIMIT = 12
CHECK_TIMEOUT = 15


def service_view(row: dict, tools: list[dict] | None = None) -> dict:
    return {'id': row['id'], 'name': row['name'], 'transport': row['transport'], 'command': decode(row['command']),
            'url': row['url'], 'has_key': bool(row['credential_ref']), 'secret_name': row['secret_name'],
            'tools': decode(row['tools']), 'server_info': decode(row['server_info']), 'checked_at': row['checked_at'],
            'check_error': row['check_error'], 'cooldown_until': row['cooldown_until'],
            'mappings': tools if tools is not None else []}


def mapping_view(row: dict, service: dict, place: dict) -> dict:
    current = disclosure(service, row, place)
    return {'category': row['category'], 'tool': row['tool'], 'arguments': decode(row['arguments']),
            'run_in': decode(row['run_in']), 'enabled': bool(row['enabled']),
            'approved': row['approved'] is not None and row['approved'] == current['digest'],
            'disclosure': current}


def place_settings(connection) -> dict:
    return one(connection, 'SELECT user_place, user_latitude, user_longitude, updated_at FROM context_settings '
               'WHERE id=1')


def overview(database) -> dict:
    with database.connect() as connection:
        place = place_settings(connection)
        services = []
        for row in many(connection, 'SELECT * FROM context_services ORDER BY created_at'):
            mappings = [mapping_view(item, row, place) for item in
                        many(connection, 'SELECT * FROM context_tools WHERE service_id=? ORDER BY category', (row['id'],))]
            services.append(service_view(row, mappings))
        return {'location': place, 'services': services,
                'categories': {key: {'label': value['label'], 'purposes': list(value['purposes'])}
                               for key, value in CATEGORIES.items()},
                'purposes': PURPOSES, 'sources': SOURCES, 'never_sent': list(NEVER_SENT)}


def update_location(database, body) -> dict:
    """Manual city or region, optionally coordinates; never detected. Kept apart from the companion's location."""
    require((body.user_latitude is None) == (body.user_longitude is None),
            'Enter both latitude and longitude, or neither.', 422)
    with database.connect(write=True) as connection:
        connection.execute('UPDATE context_settings SET user_place=?, user_latitude=?, user_longitude=?, updated_at=? '
                           'WHERE id=1', (body.user_place, body.user_latitude, body.user_longitude, database.now()))
        return place_settings(connection)


def credential_name(service_id: str) -> str:
    return f'context-service:{service_id}'


def check_definition(body):
    if body.transport == 'stdio':
        require(bool(body.command) and bool(body.command[0].strip()), 'Choose the program that runs the server.', 422)
    else:
        require(bool(body.url), 'Enter the server address.', 422)
        try:
            check_url(body.url)
        except ToolFailure as failure:
            raise DomainError(failure.message, 422) from failure
    if body.secret_name:
        pattern = r'^[A-Za-z_][A-Za-z0-9_]*$' if body.transport == 'stdio' else r'^[A-Za-z0-9-]+$'
        require(re.match(pattern, body.secret_name) is not None,
                'Use a valid environment variable name.' if body.transport == 'stdio' else 'Use a valid header name.',
                422)


def create_service(database, vault, body) -> dict:
    check_definition(body)
    service_id, now = identifier(), database.now()
    reference = None
    if body.secret:
        vault.put(credential_name(service_id), body.secret)
        reference = credential_name(service_id)
    with database.connect(write=True) as connection:
        count = one(connection, 'SELECT COUNT(*) AS n FROM context_services')['n']
        require(count < SERVICE_LIMIT, f'Up to {SERVICE_LIMIT} services can be configured.', 409)
        connection.execute(
            'INSERT INTO context_services (id, name, transport, command, url, credential_ref, secret_name, created_at, '
            'updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (service_id, body.name, body.transport, encode(body.command) if body.transport == 'stdio' else None,
             body.url if body.transport == 'http' else None, reference, body.secret_name, now, now))
    return read_service(database, service_id)


def update_service(database, vault, service_id, body) -> dict:
    """A new address, program or key needs the tools checked and each mapping confirmed again."""
    check_definition(body)
    with database.connect() as connection:
        existing = one(connection, 'SELECT * FROM context_services WHERE id=?', (service_id,))
    reference = existing['credential_ref']
    if body.secret:
        vault.put(credential_name(service_id), body.secret)
        reference = credential_name(service_id)
    elif body.clear_secret:
        reference = None
    with database.connect(write=True) as connection:
        now = database.now()
        connection.execute(
            'UPDATE context_services SET name=?, transport=?, command=?, url=?, credential_ref=?, secret_name=?, '
            'updated_at=? WHERE id=?',
            (body.name, body.transport, encode(body.command) if body.transport == 'stdio' else None,
             body.url if body.transport == 'http' else None, reference, body.secret_name, now, service_id))
        changed = (existing['transport'], existing['command'], existing['url'], existing['secret_name'],
                   existing['credential_ref']) != (body.transport, encode(body.command) if body.transport == 'stdio'
                                                   else None, body.url if body.transport == 'http' else None,
                                                   body.secret_name, reference)
        if changed:
            connection.execute('UPDATE context_tools SET enabled=0, approved=NULL, updated_at=? WHERE service_id=?',
                               (now, service_id))
    return read_service(database, service_id)


def delete_service(database, service_id) -> dict:
    """Earlier observations stay inspectable under the service's name."""
    with database.connect(write=True) as connection:
        one(connection, 'SELECT id FROM context_services WHERE id=?', (service_id,))
        connection.execute('DELETE FROM context_services WHERE id=?', (service_id,))
    return {'deleted': service_id}


def read_service(database, service_id) -> dict:
    return next(service for service in overview(database)['services'] if service['id'] == service_id)


def transport_for(service: dict, vault):
    """Build the transport, adding the service's own key only. The key never reaches a lookup record."""
    secret = vault.get(service['credential_ref']) if service['credential_ref'] else None
    if service['transport'] == 'stdio':
        env = {service['secret_name'] or 'API_KEY': secret} if secret else {}
        return StdioTransport(decode(service['command']), env)
    headers = {}
    if secret:
        name = service['secret_name'] or 'Authorization'
        headers[name] = f'Bearer {secret}' if name.lower() == 'authorization' and ' ' not in secret else secret
    return HttpTransport(service['url'], headers)


async def check_service(database, vault, service_id, transport=None) -> dict:
    """Connect, list the tools and suggest a mapping for each category. Nothing is enabled."""
    with database.connect() as connection:
        service = one(connection, 'SELECT * FROM context_services WHERE id=?', (service_id,))
    tools, info, error = [], None, None
    try:
        async with open_session(transport or transport_for(service, vault), CHECK_TIMEOUT) as session:
            tools = await session.list_tools()
            info = session.server
    except ToolFailure as failure:
        error = failure.message
    with database.connect(write=True) as connection:
        now = database.now()
        if error is None:
            connection.execute('UPDATE context_services SET tools=?, server_info=?, checked_at=?, check_error=NULL, '
                               'updated_at=? WHERE id=?', (encode(tools), encode(info), now, now, service_id))
        else:
            connection.execute('UPDATE context_services SET checked_at=?, check_error=?, updated_at=? WHERE id=?',
                               (now, error, now, service_id))
    result = read_service(database, service_id)
    return {**result, 'suggestions': suggestions(result['tools']) if error is None else {}}


def suggestions(tools: list[dict]) -> dict:
    """The tool whose name and description best match each category, with arguments filled from its schema."""
    found = {}
    for category, spec in CATEGORIES.items():
        scored = []
        for tool in tools:
            name, description = tool['name'].lower().replace('_', ' '), tool['description'].lower()
            score = sum(3 for word in spec['keywords'] if word in name) + sum(1 for word in spec['keywords']
                                                                              if word in description)
            if score:
                scored.append((score, tool['name']))
        if scored:
            best = max(scored)[1]
            tool = next(item for item in tools if item['name'] == best)
            arguments, missing = infer_arguments(category, tool['input_schema'])
            found[category] = {'tool': best, 'arguments': arguments, 'missing': missing}
    return found


def schema_properties(schema: dict) -> tuple[dict, list[str]]:
    properties = schema.get('properties') if isinstance(schema.get('properties'), dict) else {}
    required = [name for name in schema.get('required') or [] if isinstance(name, str)]
    return properties, required


def infer_arguments(category: str, schema: dict) -> tuple[dict, list[str]]:
    """Fill only properties a known source matches. Optional unmatched ones are left out (minimal disclosure)."""
    properties, required = schema_properties(schema)
    wanted = ['place', 'latitude', 'longitude', 'date'] + (['topic'] if category == 'news' else [])
    arguments = {}
    for source in wanted:
        for name in properties:
            if name in arguments:
                continue
            if name.lower() in FILLS[source]:
                # A weather or events tool may call its location field "query"; news queries are topics.
                arguments[name] = {'source': source}
                break
    if category != 'news':
        for name in required:
            if name not in arguments and name.lower() in FILLS['topic']:
                arguments[name] = {'source': 'place'}
    if any(item['source'] == 'place' for item in arguments.values()):
        # With a place to send, coordinates go only to a tool that requires them.
        for name in [name for name, item in arguments.items()
                     if item['source'] in {'latitude', 'longitude'} and name not in required]:
            del arguments[name]
    missing = [name for name in required if name not in arguments]
    return arguments, missing


def check_mapping(service: dict, category: str, body):
    require(category in CATEGORIES, 'Unknown category.', 404)
    tools = {tool['name']: tool for tool in decode(service['tools'])}
    require(body.tool in tools, 'Check the service and choose one of its tools.', 422)
    allowed = CATEGORIES[category]['purposes']
    require(bool(body.run_in) and all(purpose in allowed for purpose in body.run_in),
            f"{CATEGORIES[category]['label']} can run: {', '.join(allowed)}.", 422)
    properties, required = schema_properties(tools[body.tool]['input_schema'])
    for name, argument in body.arguments.items():
        require(name in properties or not properties, f'The tool has no argument called {name}.', 422)
        require(argument.source in SOURCES, f'Unknown source for {name}.', 422)
        require(argument.source != 'literal' or argument.value is not None, f'Choose a value for {name}.', 422)
        require(argument.source != 'topic' or category in {'news', 'local_events'},
                'Only news and event lookups can send a topic.', 422)
    missing = [name for name in required if name not in body.arguments]
    require(not missing, f"The tool requires {', '.join(missing)}.", 422)


def save_mapping(database, service_id, category, body) -> dict:
    """Saving leaves the mapping off until its disclosure is confirmed."""
    with database.connect(write=True) as connection:
        service = one(connection, 'SELECT * FROM context_services WHERE id=?', (service_id,))
        check_mapping(service, category, body)
        arguments = {name: argument.model_dump(exclude_none=True) for name, argument in body.arguments.items()}
        connection.execute(
            'INSERT INTO context_tools (service_id, category, tool, arguments, run_in, enabled, approved, updated_at) '
            'VALUES (?, ?, ?, ?, ?, 0, NULL, ?) ON CONFLICT(service_id, category) DO UPDATE SET tool=excluded.tool, '
            'arguments=excluded.arguments, run_in=excluded.run_in, enabled=0, approved=NULL, '
            'updated_at=excluded.updated_at',
            (service_id, category, body.tool, encode(arguments), encode(sorted(set(body.run_in))), database.now()))
    return read_service(database, service_id)


def remove_mapping(database, service_id, category) -> dict:
    with database.connect(write=True) as connection:
        connection.execute('DELETE FROM context_tools WHERE service_id=? AND category=?', (service_id, category))
    return read_service(database, service_id)


def destination(service: dict) -> str:
    if service['transport'] == 'http':
        return service['url']
    return 'Local program: ' + ' '.join(decode(service['command']) or [])


def disclosure(service: dict, mapping: dict, place: dict) -> dict:
    """What a lookup sends, to where and when, with today's values as examples, plus its digest."""
    arguments, run_in = decode(mapping['arguments']), decode(mapping['run_in'])
    examples = {'place': place['user_place'] or '(not set)', 'latitude': place['user_latitude'],
                'longitude': place['user_longitude'], 'topic': 'for example "the Orioles"', 'date': 'today'}
    sends = []
    for name, argument in sorted(arguments.items()):
        source = argument['source']
        example = argument.get('value') if source == 'literal' else examples.get(source)
        sends.append({'argument': name, 'source': source, 'description': SOURCES[source], 'example': example})
    basis = {'destination': destination(service), 'tool': mapping['tool'], 'arguments': arguments,
             'run_in': sorted(run_in), 'category': mapping['category']}
    digest = hashlib.sha256(json.dumps(basis, sort_keys=True).encode()).hexdigest()
    lines = [f"{CATEGORIES[mapping['category']]['label']} lookups call the tool \"{mapping['tool']}\" at "
             f"{basis['destination']}."]
    lines += [f"It sends {item['argument']}: {item['description'].lower()} (now: {item['example']})." for item in sends]
    if not sends:
        lines.append('It sends no arguments.')
    lines += [f'It runs {PURPOSES[purpose][0].lower()}{PURPOSES[purpose][1:]}.' for purpose in sorted(run_in)]
    lines.append('It never sends ' + ', '.join(NEVER_SENT) + '. The service\'s own terms and retention apply.')
    return {'digest': digest, 'destination': basis['destination'], 'transport': service['transport'],
            'tool': mapping['tool'], 'category': mapping['category'], 'sends': sends, 'run_in': sorted(run_in),
            'never_sent': list(NEVER_SENT), 'summary': lines}


def enable_mapping(database, service_id, category, digest: str) -> dict:
    """Enabling requires the digest of the disclosure the user was shown, so a changed mapping can't slip by."""
    with database.connect(write=True) as connection:
        service = one(connection, 'SELECT * FROM context_services WHERE id=?', (service_id,))
        mapping = one(connection, 'SELECT * FROM context_tools WHERE service_id=? AND category=?',
                      (service_id, category))
        current = disclosure(service, mapping, place_settings(connection))
        require(digest == current['digest'], 'What this lookup sends has changed. Review it again before enabling.',
                409)
        connection.execute('UPDATE context_tools SET enabled=1, approved=?, updated_at=? WHERE service_id=? '
                           'AND category=?', (digest, database.now(), service_id, category))
    return read_service(database, service_id)


def disable_mapping(database, service_id, category) -> dict:
    with database.connect(write=True) as connection:
        connection.execute('UPDATE context_tools SET enabled=0, updated_at=? WHERE service_id=? AND category=?',
                           (database.now(), service_id, category))
    return read_service(database, service_id)


def active_mappings(connection, category: str, purpose: str) -> list[dict]:
    """Enabled mappings whose confirmed disclosure still matches, for this category and purpose."""
    place = place_settings(connection)
    found = []
    for row in many(connection, 'SELECT t.*, s.name, s.transport, s.command, s.url, s.credential_ref, s.secret_name, '
                    's.tools, s.cooldown_until, s.id AS sid FROM context_tools t JOIN context_services s '
                    'ON s.id = t.service_id WHERE t.category=? AND t.enabled=1 ORDER BY s.created_at',
                    (category,)):
        service = {**row, 'id': row['sid']}
        if purpose in decode(row['run_in']) and row['approved'] == disclosure(service, row, place)['digest']:
            found.append({'service': service, 'mapping': row})
    return found


def service_row(connection, service_id) -> dict | None:
    return optional(connection, 'SELECT * FROM context_services WHERE id=?', (service_id,))
