"""Configured image backends (PRD F5–F9).

Three classes: a ComfyUI instance, the Codex/ChatGPT subscription CLI and hosted image APIs.
Every backend is off until configured, and the user orders them. What a backend may receive
follows F6: only a local ComfyUI instance takes NSFW requests; Codex, Google and, in the first
release, every other hosted API take Safe requests only.
"""
from urllib.parse import urlsplit

from companion.database import decode, encode, identifier, many, one
from companion.errors import DomainError, require
from companion.images.adapters.codex import method_of as codex_method
from companion.providers.urls import is_loopback, validate_compatible_url

HOSTED_DEFAULTS = {
    'openrouter': {'base_url': 'https://openrouter.ai/api/v1', 'api_style': 'chat', 'label': 'OpenRouter'},
    'google': {'base_url': 'https://generativelanguage.googleapis.com/v1beta/openai', 'api_style': 'images',
               'label': 'Google'},
    'openai': {'base_url': 'https://api.openai.com/v1', 'api_style': 'images', 'label': 'OpenAI API'},
    'other': {'base_url': '', 'api_style': 'images', 'label': 'Image API'},
}
KIND_LABELS = {'comfyui': 'ComfyUI', 'codex': 'Codex (ChatGPT subscription)'}
CONFIG_KEYS = ('base_url', 'model', 'workflow', 'cli_path', 'api_style', 'method')


def credential_ref(backend_id: str) -> str:
    return f'image-backend:{backend_id}'


def is_local(backend: dict) -> bool:
    """F6: a ComfyUI instance on this computer is local; elsewhere only if the user marked it as a
    machine they control. Codex and hosted APIs are never local."""
    if backend['kind'] != 'comfyui':
        return False
    host = urlsplit(decode(backend['config']).get('base_url', '')).hostname
    return is_loopback(host) or bool(backend['controlled_machine'])


def accepts_nsfw(backend: dict) -> bool:
    return is_local(backend)


def disclosure(backend: dict) -> str | None:
    """What a hosted request sends, shown before the provider is enabled (F9)."""
    if backend['kind'] == 'comfyui' and is_local(backend):
        return None
    if backend['kind'] == 'codex':
        destination = 'OpenAI, through the Codex CLI under your own codex login (your ChatGPT plan, or the API key ' \
            'Codex is signed in with)'
    elif backend['kind'] == 'comfyui':
        destination = 'the ComfyUI server at this address, which is not on this computer'
    else:
        destination = HOSTED_DEFAULTS[backend['provider']]['label'] if backend['provider'] != 'other' \
            else 'this image service'
    return (f'Each image request sends its prompt (built from the event and the character\'s appearance '
            f'description) to {destination}. Their retention rules apply. Conversation, memories and '
            f'reference images are not sent.')


def view(backend: dict) -> dict:
    config = decode(backend['config'])
    return {'id': backend['id'], 'kind': backend['kind'], 'provider': backend['provider'], 'label': backend['label'],
            'enabled': bool(backend['enabled']), 'position': backend['position'],
            'base_url': config.get('base_url', ''), 'model': config.get('model', ''),
            'api_style': config.get('api_style'), 'cli_path': config.get('cli_path', ''),
            'method': codex_method(config) if backend['kind'] == 'codex' else None,
            'custom_workflow': bool(config.get('workflow')),
            'has_key': backend['credential_ref'] is not None,
            'controlled_machine': bool(backend['controlled_machine']), 'concurrency': backend['concurrency'],
            'local': is_local(backend), 'accepts_nsfw': accepts_nsfw(backend),
            'blocked_reason': backend['blocked_reason'], 'disclosure': disclosure(backend),
            'disclosure_accepted': backend['disclosure_accepted_at'] is not None,
            'experimental': backend['kind'] == 'codex'}


def ordered(connection, enabled_only=False) -> list[dict]:
    where = 'WHERE enabled=1 ' if enabled_only else ''
    return many(connection, f'SELECT * FROM image_backends {where}ORDER BY position, created_at')


def listing(database) -> list[dict]:
    with database.connect() as connection:
        return [view(backend) for backend in ordered(connection)]


def get(connection, backend_id) -> dict:
    return one(connection, 'SELECT * FROM image_backends WHERE id=?', (backend_id,))


def validate(kind, provider, config, controlled_machine):
    if kind == 'comfyui':
        require(config.get('base_url'), 'Enter the address of your ComfyUI server.', 422)
        url = config['base_url']
        parts = urlsplit(url)
        require(parts.scheme in {'http', 'https'} and parts.hostname, 'Enter an http or https ComfyUI address.', 422)
        require(not any((parts.username, parts.password, parts.query, parts.fragment)),
                'Use a plain server address without credentials or query text.', 422)
        if config.get('workflow'):
            from companion.images.adapters.comfyui import parse_workflow
            parse_workflow(config['workflow'])
    elif kind == 'hosted':
        require(config.get('base_url'), 'Enter the API base URL.', 422)
        validate_compatible_url(config['base_url'])
        require(config.get('model'), 'Choose the image model to use.', 422)
    require(not (controlled_machine and kind != 'comfyui'),
            'Only a ComfyUI server can be marked as a machine you control.', 422)


def merged_config(kind, provider, previous: dict, body) -> dict:
    config = dict(previous)
    if not previous and kind == 'hosted':
        defaults = HOSTED_DEFAULTS[provider]
        config.update({'base_url': defaults['base_url'], 'api_style': defaults['api_style']})
    for key in CONFIG_KEYS:
        value = getattr(body, key)
        if value is not None:
            config[key] = value.rstrip('/') if key == 'base_url' else value
    if kind != 'hosted':
        config.pop('api_style', None)
    return config


def provider_for(kind, provider) -> str:
    if kind in {'comfyui', 'codex'}:
        return kind
    require(provider in HOSTED_DEFAULTS, 'Choose a hosted provider: OpenRouter, Google, OpenAI or other.', 422)
    return provider


def concurrency_for(kind, requested) -> int:
    """Codex is strictly serial (F8) and a local GPU runs one job at a time."""
    if kind in {'comfyui', 'codex'}:
        return 1
    return requested or 2


def create(database, vault, body) -> dict:
    provider = provider_for(body.kind, body.provider)
    config = merged_config(body.kind, provider, {}, body)
    validate(body.kind, provider, config, body.controlled_machine)
    backend_id = identifier()
    label = body.label or KIND_LABELS.get(body.kind) or HOSTED_DEFAULTS[provider]['label']
    reference = None
    if body.api_key:
        vault.put(credential_ref(backend_id), body.api_key)
        reference = credential_ref(backend_id)
    with database.connect(write=True) as connection:
        timestamp = database.now()
        position = len(ordered(connection))
        row = {'kind': body.kind, 'config': encode(config), 'controlled_machine': int(bool(body.controlled_machine)),
               'provider': provider, 'blocked_reason': None, 'disclosure_accepted_at': None}
        accepted = timestamp if body.accept_disclosure else None
        enabled = body.enabled if body.enabled is not None else True
        require_disclosure(row, enabled, accepted)
        connection.execute(
            'INSERT INTO image_backends (id, kind, provider, label, enabled, position, config, credential_ref, '
            'controlled_machine, concurrency, disclosure_accepted_at, created_at, updated_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (backend_id, body.kind, provider, label, int(enabled), position, encode(config), reference,
             int(bool(body.controlled_machine)), concurrency_for(body.kind, body.concurrency), accepted,
             timestamp, timestamp))
        return view(get(connection, backend_id))


def require_disclosure(backend, enabled, accepted_at):
    if enabled and disclosure(backend) and not accepted_at:
        raise DomainError('Review what this backend receives and accept it before enabling it.', 409,
                          'disclosure_required')


def update(database, vault, backend_id, body) -> dict:
    with database.connect(write=True) as connection:
        backend = get(connection, backend_id)
        config = merged_config(backend['kind'], backend['provider'], decode(backend['config']), body)
        controlled = backend['controlled_machine'] if body.controlled_machine is None else int(body.controlled_machine)
        validate(backend['kind'], backend['provider'], config, controlled)
        timestamp = database.now()
        accepted = timestamp if body.accept_disclosure else backend['disclosure_accepted_at']
        changed_destination = config.get('base_url') != decode(backend['config']).get('base_url') \
            or controlled != backend['controlled_machine']
        if changed_destination and not body.accept_disclosure:
            accepted = None
        enabled = backend['enabled'] if body.enabled is None else int(body.enabled)
        candidate = {**backend, 'config': encode(config), 'controlled_machine': controlled}
        require_disclosure(candidate, enabled, accepted)
        reference = backend['credential_ref']
        if body.api_key:
            vault.put(credential_ref(backend_id), body.api_key)
            reference = credential_ref(backend_id)
        connection.execute(
            'UPDATE image_backends SET label=?, enabled=?, config=?, credential_ref=?, controlled_machine=?, '
            'concurrency=?, disclosure_accepted_at=?, blocked_reason=?, updated_at=? WHERE id=?',
            (body.label or backend['label'], enabled, encode(config), reference, controlled,
             concurrency_for(backend['kind'], body.concurrency or backend['concurrency']), accepted,
             None if body.api_key else backend['blocked_reason'], timestamp, backend_id))
        return view(get(connection, backend_id))


def move(database, backend_id, position) -> list[dict]:
    with database.connect(write=True) as connection:
        rows = ordered(connection)
        moving = next((row for row in rows if row['id'] == backend_id), None)
        require(moving is not None, 'This item could not be found.', 404)
        rows.remove(moving)
        rows.insert(min(position, len(rows)), moving)
        connection.executemany('UPDATE image_backends SET position=? WHERE id=?',
                               [(index, row['id']) for index, row in enumerate(rows)])
        return [view(row) for row in ordered(connection)]


def delete(database, backend_id) -> list[dict]:
    """Jobs keep their recorded backend details; queued ones fail at dispatch."""
    with database.connect(write=True) as connection:
        get(connection, backend_id)
        connection.execute('DELETE FROM image_backends WHERE id=?', (backend_id,))
        return [view(row) for row in ordered(connection)]


def block(database, backend_id, reason):
    with database.connect(write=True) as connection:
        connection.execute('UPDATE image_backends SET blocked_reason=?, updated_at=? WHERE id=?',
                           (reason, database.now(), backend_id))


def unblock(database, backend_id) -> dict:
    with database.connect(write=True) as connection:
        get(connection, backend_id)
        connection.execute('UPDATE image_backends SET blocked_reason=NULL, updated_at=? WHERE id=?',
                           (database.now(), backend_id))
        return view(get(connection, backend_id))
