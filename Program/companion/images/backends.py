"""Configured image backends (PRD F5–F9).

Three classes: a ComfyUI instance, the Codex/ChatGPT subscription CLI and hosted image APIs.
Every backend is off until configured, and the user orders them. What a backend may receive
follows F6: a local ComfyUI instance takes NSFW requests; Codex, Google and the OpenAI API take
Safe requests only; any other image API takes Safe requests unless the user switches it to NSFW too
(Vanta, 2026-10-07: a provider like NovelAI accepts NSFW prompts under its own terms).
"""
from urllib.parse import urlsplit

from companion.database import decode, encode, identifier, many, one
from companion.errors import DomainError, require
from companion.images import content
from companion.images.adapters.comfyui import SAMPLER_INPUTS, default_sampler
from companion.providers.urls import is_loopback, validate_compatible_url

HOSTED_DEFAULTS = {
    'openrouter': {'base_url': 'https://openrouter.ai/api/v1', 'api_style': 'chat', 'label': 'OpenRouter'},
    'google': {'base_url': 'https://generativelanguage.googleapis.com/v1beta/openai', 'api_style': 'images',
               'label': 'Google'},
    'openai': {'base_url': 'https://api.openai.com/v1', 'api_style': 'images', 'label': 'OpenAI API'},
    'other': {'base_url': '', 'api_style': 'images', 'label': 'Image API'},
}
# Hosted providers the NSFW switch is offered for. Google and OpenAI's own API stay safe-only, like Codex.
NSFW_PROVIDERS = {'openrouter', 'other'}
KIND_LABELS = {'comfyui': 'ComfyUI', 'codex': 'Codex (ChatGPT subscription)'}
CONFIG_KEYS = ('base_url', 'model', 'workflow', 'reference_workflow', 'cli_path', 'api_style')
# ComfyUI only: the files chosen for the built-in workflow's loaders (see adapters/comfyui.py).
FILE_KEYS = ('unet_name', 'clip_name', 'clip_type', 'vae_name')


def credential_ref(backend_id: str) -> str:
    return f'image-backend:{backend_id}'


def is_local(backend: dict) -> bool:
    """F6: a ComfyUI instance on this computer is local; elsewhere only if the user marked it as a
    machine they control. Codex and hosted APIs are never local."""
    if backend['kind'] != 'comfyui':
        return False
    host = urlsplit(decode(backend['config']).get('base_url', '')).hostname
    return is_loopback(host) or bool(backend['controlled_machine'])


def can_allow_nsfw(kind, provider) -> bool:
    """Whether the user may switch this backend to take NSFW requests: image APIs other than Google
    and OpenAI. A local ComfyUI takes them anyway; Codex, Google and OpenAI never do."""
    return kind == 'hosted' and provider in NSFW_PROVIDERS


def accepts_nsfw(backend: dict) -> bool:
    return is_local(backend) or (can_allow_nsfw(backend['kind'], backend['provider'])
                                 and bool(backend.get('allows_nsfw')))


def takes_reference(backend: dict) -> bool:
    """Whether this backend can make a picture that follows an earlier one (the onboarding
    portraits): Codex attaches it to the prompt, chat-style APIs and OpenAI's image edits read it,
    and ComfyUI needs the user's own reference workflow."""
    config = decode(backend['config'])
    if backend['kind'] == 'codex':
        return True
    if backend['kind'] == 'comfyui':
        return bool(config.get('reference_workflow'))
    from companion.images.adapters.hosted import takes_reference as hosted_takes
    return hosted_takes(config, backend['provider'])


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
    text = (f'Each image request sends its prompt (built from the event and the character\'s appearance '
            f'description) to {destination}. Their retention rules apply. Conversation and memories are '
            f'not sent. Reference pictures are sent only when you make profile pictures: the first one goes '
            f'along with the other two.')
    if accepts_nsfw(backend) and not is_local(backend):
        text += (' NSFW requests go there too, so their terms decide what they will make and keep. '
                 'Prohibited requests are still never sent.')
    return text


def view(backend: dict) -> dict:
    config = decode(backend['config'])
    return {'id': backend['id'], 'kind': backend['kind'], 'provider': backend['provider'], 'label': backend['label'],
            'enabled': bool(backend['enabled']), 'position': backend['position'],
            'base_url': config.get('base_url', ''), 'model': config.get('model', ''),
            'api_style': config.get('api_style'), 'cli_path': config.get('cli_path', ''),
            'custom_workflow': bool(config.get('workflow')),
            'model_files': {key: config.get(key, '') for key in FILE_KEYS} if backend['kind'] == 'comfyui' else None,
            'style_loras': config.get('style_loras', []) if backend['kind'] == 'comfyui' else None,
            'sampler': {key: config.get(key) for key in SAMPLER_INPUTS} if backend['kind'] == 'comfyui' else None,
            'reference_workflow': bool(config.get('reference_workflow')), 'takes_reference': takes_reference(backend),
            'has_key': backend['credential_ref'] is not None,
            'controlled_machine': bool(backend['controlled_machine']), 'concurrency': backend['concurrency'],
            'local': is_local(backend), 'accepts_nsfw': accepts_nsfw(backend),
            'allows_nsfw': bool(backend.get('allows_nsfw')),
            'nsfw_switch': can_allow_nsfw(backend['kind'], backend['provider']),
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


def validate(kind, provider, config, controlled_machine, allows_nsfw=False):
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
        if config.get('reference_workflow'):
            from companion.images.adapters.comfyui import parse_workflow
            parse_workflow(config['reference_workflow'], reference=True)
    elif kind == 'hosted':
        require(config.get('base_url'), 'Enter the API base URL.', 422)
        validate_compatible_url(config['base_url'])
        require(config.get('model'), 'Choose the image model to use.', 422)
    require(not (controlled_machine and kind != 'comfyui'),
            'Only a ComfyUI server can be marked as a machine you control.', 422)
    require(not allows_nsfw or can_allow_nsfw(kind, provider),
            'Only an image API other than Google or OpenAI can take NSFW requests; '
            'for NSFW images on this computer, use a local ComfyUI server.', 422)


def merged_config(kind, provider, previous: dict, body) -> dict:
    config = dict(previous)
    if not previous and kind == 'hosted':
        defaults = HOSTED_DEFAULTS[provider]
        config.update({'base_url': defaults['base_url'], 'api_style': defaults['api_style']})
    for key in CONFIG_KEYS:
        value = getattr(body, key)
        if value is not None:
            config[key] = value.rstrip('/') if key == 'base_url' else value
    for key in FILE_KEYS:
        value = getattr(body, key)
        if value is not None:
            config[key] = value.strip()
        if kind != 'comfyui' or not config.get(key):
            config.pop(key, None)
    comfy_settings(config, kind, body)
    if kind != 'hosted':
        config.pop('api_style', None)
    return config


def comfy_settings(config: dict, kind, body):
    """The built-in workflow's sampler (a value equal to the workflow's own is stored as unset) and
    the style LoRAs, for ComfyUI only."""
    defaults = default_sampler()
    for key in SAMPLER_INPUTS:
        value = getattr(body, key)
        if value is not None:
            config[key] = value.strip() if isinstance(value, str) else value
        if kind != 'comfyui' or config.get(key) in (None, '') or config.get(key) == defaults[key]:
            config.pop(key, None)
    if body.style_loras is not None:
        config['style_loras'] = [{'name': lora.name.strip(), 'strength': lora.strength, 'trigger': lora.trigger.strip()}
                                 for lora in body.style_loras]
    if kind != 'comfyui' or not config.get('style_loras'):
        config.pop('style_loras', None)


def require_safe_loras(backend: dict):
    """A style LoRA never makes a server less strict: one whose name or trigger words are not plainly
    safe needs a server that accepts NSFW requests (F6), so it is refused anywhere else."""
    if accepts_nsfw(backend):
        return
    for lora in decode(backend['config']).get('style_loras') or []:
        found = content.classify({'prompt': f"{lora['name']}\n{lora['trigger']}"})
        require(found.tier == content.SAFE, f"The LoRA {lora['name']} reads as {', '.join(found.reasons) or 'not safe'}; "
                'it can only be used on a ComfyUI server on this computer or one you control.', 422)


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
    allows = int(bool(body.allows_nsfw))
    validate(body.kind, provider, config, body.controlled_machine, allows)
    require_safe_loras({'kind': body.kind, 'provider': provider, 'config': encode(config),
                        'controlled_machine': int(bool(body.controlled_machine)), 'allows_nsfw': allows})
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
               'provider': provider, 'allows_nsfw': allows, 'blocked_reason': None, 'disclosure_accepted_at': None}
        accepted = timestamp if body.accept_disclosure else None
        enabled = body.enabled if body.enabled is not None else True
        require_disclosure(row, enabled, accepted)
        connection.execute(
            'INSERT INTO image_backends (id, kind, provider, label, enabled, position, config, credential_ref, '
            'controlled_machine, allows_nsfw, concurrency, disclosure_accepted_at, created_at, updated_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (backend_id, body.kind, provider, label, int(enabled), position, encode(config), reference,
             int(bool(body.controlled_machine)), allows, concurrency_for(body.kind, body.concurrency), accepted,
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
        allows = backend['allows_nsfw'] if body.allows_nsfw is None else int(body.allows_nsfw)
        validate(backend['kind'], backend['provider'], config, controlled, allows)
        timestamp = database.now()
        accepted = timestamp if body.accept_disclosure else backend['disclosure_accepted_at']
        # Sending NSFW requests somewhere new is a new destination for them, so it is accepted again.
        changed_destination = config.get('base_url') != decode(backend['config']).get('base_url') \
            or controlled != backend['controlled_machine'] or allows > backend['allows_nsfw']
        if changed_destination and not body.accept_disclosure:
            accepted = None
        enabled = backend['enabled'] if body.enabled is None else int(body.enabled)
        candidate = {**backend, 'config': encode(config), 'controlled_machine': controlled, 'allows_nsfw': allows}
        require_disclosure(candidate, enabled, accepted)
        require_safe_loras(candidate)
        reference = backend['credential_ref']
        if body.api_key:
            vault.put(credential_ref(backend_id), body.api_key)
            reference = credential_ref(backend_id)
        connection.execute(
            'UPDATE image_backends SET label=?, enabled=?, config=?, credential_ref=?, controlled_machine=?, '
            'allows_nsfw=?, concurrency=?, disclosure_accepted_at=?, blocked_reason=?, updated_at=? WHERE id=?',
            (body.label or backend['label'], enabled, encode(config), reference, controlled, allows,
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
