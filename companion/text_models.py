"""Model profiles and which one does each job (Settings > Models).

Adapted from prosperos-study server/profiles.py, profile_routes.py and roles.py at bbcbde4. A
profile is one provider, model, address and saved key, as in the Study. Changes: profiles are
edited in place with a revision check instead of versioned (no Companion record needs an exact
earlier profile), and the Study's per-story step overrides become workspace job assignments. The
conversation profile plays the Study's Primary Writer: every other job uses it until the user
assigns another profile.

Saving a profile never contacts the service. A saved key stays with its provider and address:
changing either drops it, so a key is never sent somewhere it was not entered for.
"""
from urllib.parse import urlsplit

from companion.database import decode, encode, identifier, many, one, optional
from companion.errors import require
from companion.providers.config import (
    DEFAULT_URLS,
    PROVIDER_NAMES,
    ProfileConfig,
    ProfileCreate,
    ProfileUpdate,
    profile_ready,
)
from companion.providers.urls import is_loopback, validate_compatible_url
from companion.providers.vault import credential_for

CHAT = 'chat'
JOBS = [
    {'key': CHAT, 'name': 'Conversation', 'detail': 'Replies in chat. Every other job uses this profile '
     'unless you choose another.'},
    {'key': 'life', 'name': 'Life phrasing', 'detail': "Words the companion's day in the background, when model "
     'phrasing is on in Life settings.'},
    {'key': 'memory', 'name': 'Memory suggestions', 'detail': 'Suggests memories from your messages in the '
     'background, when model suggestions are on.'},
    {'key': 'drafting', 'name': 'Character drafting', 'detail': 'Quick start and Help me write on the character page.'},
    {'key': 'recall', 'name': 'Semantic recall', 'detail': "Embeddings that find related memories. Uses the profile's "
     'embedding model; without one, recall matches keywords only.'},
]
JOB_KEYS = {job['key'] for job in JOBS}


def same_connection(first: dict, second: dict) -> bool:
    return first['provider'] == second['provider'] and (first['base_url'] == second['base_url'] or not first['base_url'])


def profile_view(row: dict) -> dict:
    config = decode(row['config'])
    return {'id': row['id'], 'name': row['name'], 'revision': row['revision'], 'config': config,
            'provider_name': PROVIDER_NAMES[config['provider']], 'has_saved_key': bool(row['credential_ref']),
            'ready': profile_ready(config), 'updated_at': row['updated_at']}


def routes(connection) -> dict[str, str]:
    return {row['job']: row['profile_id'] for row in many(connection, 'SELECT job, profile_id FROM model_routes')}


def overview(connection) -> dict:
    rows = many(connection, 'SELECT * FROM model_profiles ORDER BY name COLLATE NOCASE, created_at')
    return {'profiles': [profile_view(row) for row in rows], 'routes': routes(connection), 'jobs': JOBS}


def profile_row(connection, profile_id: str) -> dict:
    return one(connection, 'SELECT * FROM model_profiles WHERE id=?', (profile_id,))


def assigned(connection, job: str) -> dict | None:
    """The profile row doing a job: its own assignment, else the conversation's."""
    assignments = routes(connection)
    profile_id = assignments.get(job) or assignments.get(CHAT)
    return optional(connection, 'SELECT * FROM model_profiles WHERE id=?', (profile_id,)) if profile_id else None


def config_for(connection, job: str) -> dict | None:
    """Settings for a job's model calls, or None when no finished profile does it.

    The result is the profile's settings plus `credential_ref`, `profile_id` and `profile_name`, so
    callers read it the way they read the single connection before profiles.
    """
    row = assigned(connection, job)
    if row is None:
        return None
    config = decode(row['config'])
    if not profile_ready(config):
        return None
    return {**config, 'credential_ref': row['credential_ref'], 'profile_id': row['id'], 'profile_name': row['name']}


def key_for(vault, config: dict) -> str | None:
    return credential_for(vault, config.get('credential_ref'), config.get('provider'))


def probe_key(database, vault, body) -> str | None:
    """The key a connection test uses: the one typed, else the profile's saved key if it still applies."""
    if body.api_key:
        return body.api_key
    config = body.config.model_dump()
    reference = None
    if body.profile_id:
        with database.connect() as connection:
            row = profile_row(connection, body.profile_id)
        if same_connection(decode(row['config']), config):
            reference = row['credential_ref']
    return credential_for(vault, reference, config['provider'])


def default_name(config: dict) -> str:
    return f"{PROVIDER_NAMES[config['provider']]} · {config['model']}" if config.get('model') else \
        f"{PROVIDER_NAMES[config['provider']]} connection"


def store_key(vault, body, reference: str | None) -> str | None:
    if not body.api_key:
        return reference
    require(body.config.provider != 'codex', 'Codex uses its own CLI login; do not enter a key here.', 422)
    reference = reference or identifier()
    vault.put(reference, body.api_key)
    return reference


def create(database, vault, body: ProfileCreate) -> dict:
    config = body.config.model_dump()
    profile_id = identifier()
    reference = store_key(vault, body, None)
    with database.connect(write=True) as connection:
        timestamp = database.now()
        connection.execute('INSERT INTO model_profiles (id, name, config, credential_ref, revision, created_at, '
                           'updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)',
                           (profile_id, body.name or default_name(config), encode(config), reference, timestamp,
                            timestamp))
        # The first finished profile answers in chat, so a new user is ready to talk after one form.
        if CHAT not in routes(connection) and profile_ready(config):
            assign(connection, CHAT, profile_id, timestamp)
        return profile_view(profile_row(connection, profile_id))


def update(database, vault, profile_id: str, body: ProfileUpdate) -> dict:
    config = body.config.model_dump()
    with database.connect() as connection:
        current = profile_row(connection, profile_id)
    require(current['revision'] == body.expected_revision, 'This profile changed. Reopen it and try again.', 409)
    kept = current['credential_ref'] if same_connection(decode(current['config']), config) else None
    reference = store_key(vault, body, kept)
    with database.connect(write=True) as connection:
        row = profile_row(connection, profile_id)
        require(row['revision'] == body.expected_revision, 'This profile changed. Reopen it and try again.', 409)
        connection.execute('UPDATE model_profiles SET name=?, config=?, credential_ref=?, revision=revision+1, '
                           'updated_at=? WHERE id=?',
                           (body.name or default_name(config), encode(config), reference, database.now(), profile_id))
        require_assignable(connection, profile_id)
        result = profile_view(profile_row(connection, profile_id))
    if current['credential_ref'] and current['credential_ref'] != reference:
        vault.delete(current['credential_ref'])
    return result


def require_assignable(connection, profile_id: str):
    """A profile doing a job must stay able to do it."""
    row = profile_row(connection, profile_id)
    jobs = [job for job, assigned_id in routes(connection).items() if assigned_id == profile_id]
    require(not jobs or profile_ready(decode(row['config'])),
            'This profile does a job in Settings > Models. Choose a model before saving it, or assign the job '
            'to another profile first.', 409)


def delete(database, vault, profile_id: str) -> dict:
    with database.connect(write=True) as connection:
        row = profile_row(connection, profile_id)
        # Jobs it did fall back to the conversation profile, or wait for one.
        connection.execute('DELETE FROM model_routes WHERE profile_id=?', (profile_id,))
        connection.execute('DELETE FROM model_profiles WHERE id=?', (profile_id,))
        result = overview(connection)
    if row['credential_ref']:
        vault.delete(row['credential_ref'])
    return result


def assign(connection, job: str, profile_id: str | None, timestamp: str):
    require(job in JOB_KEYS, 'Unknown model job.', 422)
    if profile_id is None:
        connection.execute('DELETE FROM model_routes WHERE job=?', (job,))
        return
    row = profile_row(connection, profile_id)
    config = decode(row['config'])
    require(profile_ready(config), 'Finish this profile: choose a model before giving it a job.', 409)
    if job == 'recall':
        require(bool(config.get('embedding_model')), 'Semantic recall needs a profile with an embedding model.', 409)
    connection.execute('INSERT INTO model_routes (job, profile_id, updated_at) VALUES (?, ?, ?) ON CONFLICT(job) '
                       'DO UPDATE SET profile_id=excluded.profile_id, updated_at=excluded.updated_at',
                       (job, profile_id, timestamp))


def set_route(database, job: str, profile_id: str | None) -> dict:
    with database.connect(write=True) as connection:
        assign(connection, job, profile_id, database.now())
        return overview(connection)


# --- The single connection from before profiles -------------------------------------------------

def legacy_provider(base_url: str) -> str:
    return 'local' if is_loopback(urlsplit(base_url).hostname) else 'compatible'


def adopt_legacy(connection, timestamp: str):
    """Turn the pre-profile connection into the conversation profile, once, keeping its saved key.

    Both kinds of address it accepted keep working unchanged: a loopback server becomes a Local
    profile and anything else an OpenAI-compatible one, so requests still use Chat Completions.
    The old row is removed so a later upgrade never adopts it twice.
    """
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'connection' not in tables:
        return
    cursor = connection.execute('SELECT * FROM connection WHERE id=1')
    values = cursor.fetchone()
    if values is None:
        return
    row = dict(zip([column[0] for column in cursor.description], values))
    if not connection.execute('SELECT 1 FROM model_profiles LIMIT 1').fetchone():
        settings = {'provider': legacy_provider(row['base_url']), 'model': row['model'], 'base_url': row['base_url'],
                    'max_output_tokens': row['max_output_tokens'], 'context_tokens': row['context_tokens'],
                    'timeout_seconds': row['timeout_seconds'], 'embedding_model': row.get('embedding_model') or ''}
        # Not re-validated: the old form accepted settings a profile now questions, and an upgrade
        # must never fail over them. Editing the profile later checks them.
        config = ProfileConfig.model_construct(**settings).model_dump()
        profile_id = identifier()
        connection.execute('INSERT INTO model_profiles (id, name, config, credential_ref, revision, created_at, '
                           'updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)',
                           (profile_id, 'Text model', encode(config), row['credential_ref'], timestamp, timestamp))
        connection.execute('INSERT OR IGNORE INTO model_routes (job, profile_id, updated_at) VALUES (?, ?, ?)',
                           (CHAT, profile_id, timestamp))
    connection.execute('DELETE FROM connection')


def connection_summary(connection) -> dict | None:
    """The conversation profile in the shape of the old single connection (setup checklist, scripts)."""
    row = assigned(connection, CHAT)
    if row is None:
        return None
    config = decode(row['config'])
    return {'profile_id': row['id'], 'name': row['name'], 'provider': config['provider'],
            'provider_name': PROVIDER_NAMES[config['provider']], 'base_url': config['base_url'],
            'model': config['model'], 'has_key': bool(row['credential_ref']), 'ready': profile_ready(config),
            'max_output_tokens': config['max_output_tokens'], 'context_tokens': config['context_tokens'],
            'timeout_seconds': config['timeout_seconds'], 'embedding_model': config.get('embedding_model') or None}


def quick_save(database, vault, body) -> dict:
    """`PUT /api/connection`: set the conversation to an OpenAI-compatible or local server in one call.

    Updates the conversation profile when it is already such a profile, otherwise adds one.
    """
    base_url = body.base_url.rstrip('/')
    validate_compatible_url(base_url)
    settings = {'provider': legacy_provider(base_url), 'model': body.model, 'base_url': base_url,
                'max_output_tokens': body.max_output_tokens, 'context_tokens': body.context_tokens,
                'timeout_seconds': body.timeout_seconds, 'embedding_model': body.embedding_model or ''}
    with database.connect() as connection:
        current = assigned(connection, CHAT)
    if current and decode(current['config'])['provider'] in {'local', 'compatible'}:
        update(database, vault, current['id'], ProfileUpdate(name=current['name'], config=settings,
                                                             api_key=body.api_key, expected_revision=current['revision']))
        profile_id = current['id']
    else:
        profile_id = create(database, vault, ProfileCreate(name='Text model', config=settings,
                                                           api_key=body.api_key))['id']
    with database.connect(write=True) as connection:
        assign(connection, CHAT, profile_id, database.now())
        return connection_summary(connection)


__all__ = ['CHAT', 'DEFAULT_URLS', 'JOBS', 'adopt_legacy', 'config_for', 'connection_summary', 'create', 'delete',
           'key_for', 'overview', 'probe_key', 'quick_save', 'set_route', 'update']
