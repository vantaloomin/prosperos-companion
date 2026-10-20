"""Image backends, settings and jobs API (PRD F3–F9)."""
import json
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from companion.data_folder import open_folder
from companion.database import decode
from companion.errors import DomainError
from companion.images import backends, gifs, jobs, meme_pictures, node_packs, photos, storage
from companion.images.adapters.base import AdapterError
from companion.images.adapters.comfyui import (
    FAMILIES,
    SAMPLER_LISTS,
    built_in,
    default_files,
    default_sampler,
    family_first,
    family_of,
)
from companion.images.adapters.hosted import api_base
from companion.images.models import (
    BackendCreate,
    BackendFields,
    BackendMove,
    GifKey,
    ImageSettingsUpdate,
    JobCreate,
    JobRetry,
    ModelProbe,
    Preview,
)
from companion.lora.appearance import current_for_images
from companion.phone.access import via_lan
from companion.providers.urls import is_loopback, validate_compatible_url

router = APIRouter(prefix='/api/images')
MODEL_LINKS = Path(__file__).parent / 'model_links.json'


def db(request: Request):
    return request.app.state.database


def runner(request: Request):
    return request.app.state.images


@router.get('/settings')
def read_settings(request: Request):
    return jobs.read_settings(db(request))


@router.put('/settings')
def update_settings(request: Request, body: ImageSettingsUpdate):
    result = jobs.update_settings(db(request), body)
    runner(request).wake()
    return result


@router.get('/backends')
def list_backends(request: Request):
    return {'backends': backends.listing(db(request))}


# What a paired phone may not set on an image backend: an address the PC sends requests (and a saved key) to,
# a program the PC runs, a workflow the PC hands to ComfyUI, or which machine counts as yours for NSFW.
PHONE_FIELDS = ('base_url', 'cli_path', 'workflow', 'reference_workflow', 'controlled_machine')
ON_THE_PC = 'on your PC, in Settings > Images'


def from_phone(request: Request, body: BackendFields, creating=False) -> None:
    """A paired phone adds and manages image APIs at their providers' own addresses; the rest stays on the PC
    (companion/phone/access.py)."""
    if getattr(request.state, 'device', None) is None:
        return
    if creating and (body.kind != 'hosted' or body.provider in (None, 'other')):
        raise DomainError('On a phone you can add OpenRouter, Google, the OpenAI API or NanoGPT. ComfyUI, Codex and '
                          f'image APIs at an address of your own are added {ON_THE_PC}.', 403)
    if any(getattr(body, field) is not None for field in PHONE_FIELDS):
        raise DomainError(f'Addresses, programs and workflows of image backends are changed {ON_THE_PC}.', 403)
    if body.api_key and via_lan(request):
        raise DomainError('Home Wi-Fi access is not encrypted, so API keys are not sent over it. Add the key over '
                          f'Tailscale, or {ON_THE_PC}.', 403)


@router.post('/backends')
def create_backend(request: Request, body: BackendCreate):
    from_phone(request, body, creating=True)
    return backends.create(db(request), request.app.state.vault, body)


@router.put('/backends/{backend_id}')
def update_backend(request: Request, backend_id: str, body: BackendFields):
    from_phone(request, body)
    result = backends.update(db(request), request.app.state.vault, backend_id, body)
    runner(request).wake()
    return result


@router.get('/backends/{backend_id}/workflows')
def backend_workflows(request: Request, backend_id: str):
    """A ComfyUI backend's saved workflows, for editing on the PC. The listing says only whether each is set."""
    if getattr(request.state, 'device', None) is not None:
        raise DomainError(f'Workflows of image backends are changed {ON_THE_PC}.', 403)
    with db(request).connect() as connection:
        config = decode(backends.get(connection, backend_id)['config'])
    return {**{key: config.get(key) or '' for key in ('workflow', 'reference_workflow')},
            'built_in': json.dumps(built_in(config)),
            # Empty for a family with no built-in reference workflow (Anima, Booru models).
            'built_in_reference': json.dumps(reference) if (reference := built_in(config, reference=True)) else ''}


@router.post('/backends/{backend_id}/move')
def move_backend(request: Request, backend_id: str, body: BackendMove):
    return {'backends': backends.move(db(request), backend_id, body.position)}


@router.delete('/backends/{backend_id}')
def delete_backend(request: Request, backend_id: str):
    return {'backends': backends.delete(db(request), backend_id)}


@router.post('/backends/{backend_id}/check')
async def check_backend(request: Request, backend_id: str):
    with db(request).connect() as connection:
        backend = backends.get(connection, backend_id)
        lora = current_for_images(connection)['lora'] if backend['kind'] == 'comfyui' and \
            connection.execute('SELECT 1 FROM companions').fetchone() else None
    key = request.app.state.vault.get(backend['credential_ref']) if backend['credential_ref'] else None
    adapter = runner(request).adapters[backend['kind']]
    config = {**decode(backend['config']), **({'lora_name': lora['comfy_name']} if lora else {})}
    return (await adapter.check(backend, config, key)).view()


@router.post('/backends/{backend_id}/install-nodes/{pack_id}')
async def install_nodes(request: Request, backend_id: str, pack_id: str):
    """Put a listed node pack into the custom_nodes folder of a ComfyUI server on this computer, at the
    user's press (node_packs). ComfyUI loads it when it next starts."""
    if getattr(request.state, 'device', None) is not None:
        raise DomainError(f'ComfyUI nodes are installed {ON_THE_PC}.', 403)
    with db(request).connect() as connection:
        backend = backends.get(connection, backend_id)
    config = decode(backend['config'])
    if backend['kind'] != 'comfyui' or not is_loopback(urlsplit(config.get('base_url', '')).hostname):
        raise DomainError('Nodes can only be installed into a ComfyUI running on this computer.', 409)
    try:
        folders = await runner(request).adapters['comfyui'].folder_paths(config)
    except AdapterError as error:
        raise DomainError(error.message, 502) from error
    target = await node_packs.install(pack_id, folders)
    return {'installed': node_packs.PACKS[pack_id]['label'], 'folder': str(target)}


@router.post('/models')
async def list_models(request: Request, body: ModelProbe):
    """The image models a hosted provider lists, for the add form or a saved backend's connection, so the model
    can be picked rather than typed. Lists only: nothing is made. An unreachable list is not an error: the page
    then takes a typed name."""
    provider = backends.provider_for('hosted', body.provider)
    base_url = api_base(body.base_url) if provider == 'other' else backends.HOSTED_DEFAULTS[provider]['base_url']
    key = body.api_key or None
    if body.backend_id:
        with db(request).connect() as connection:
            backend = backends.get(connection, body.backend_id)
        saved = api_base(decode(backend['config']).get('base_url') or '')
        base_url = base_url or saved
        if not key and backend['credential_ref'] and backend['provider'] == provider and base_url == saved:
            key = request.app.state.vault.get(backend['credential_ref'])
    if not base_url:
        raise DomainError('Enter the API base URL.', 422)
    validate_compatible_url(base_url)
    try:
        models = await runner(request).adapters['hosted'].models(provider, {'base_url': base_url}, key)
    except AdapterError as error:
        return {'ok': False, 'error': error.message, 'models': []}
    return {'ok': True, 'error': None, 'models': models}


@router.get('/backends/{backend_id}/files')
async def backend_files(request: Request, backend_id: str):
    """The model files and LoRAs a ComfyUI server offers the built-in workflow, from the address the
    user entered, the backend's model family's first (`matching` lists those). The character's own LoRA
    is left out of the LoRA list: it is applied by itself (Krea 2 only). An unreachable server is not an error: the page then takes
    typed names."""
    with db(request).connect() as connection:
        backend = backends.get(connection, backend_id)
        character = current_for_images(connection)['lora'] if connection.execute(
            'SELECT 1 FROM companions').fetchone() else None
    if backend['kind'] != 'comfyui':
        raise DomainError('Only a ComfyUI server lists its model files.', 422)
    config = decode(backend['config'])
    family = family_of(config)
    if not FAMILIES[family].character_lora:
        character = None
    keys = [*FAMILIES[family].files, 'lora', *SAMPLER_LISTS]
    result = {'ok': True, 'error': None, 'family': family, 'defaults': default_files(family),
              'sampler_defaults': default_sampler(family), 'options': {key: [] for key in keys},
              'matching': {key: [] for key in keys}, 'character_lora': character['comfy_name'] if character else None}
    try:
        found = await runner(request).adapters['comfyui'].files(config)
    except AdapterError as error:
        result.update(ok=False, error=error.message)
        return result
    for key in keys:
        options = [name for name in found.get(key, []) if not (key == 'lora' and character and name == character['comfy_name'])]
        result['options'][key], result['matching'][key] = family_first(key, options, family)
    return result


@router.get('/model-links')
def model_links():
    """Pages where the built-in workflow's model files can be downloaded (checked by hand)."""
    return {'links': json.loads(MODEL_LINKS.read_text(encoding='utf-8'))}


@router.post('/backends/{backend_id}/unblock')
def unblock_backend(request: Request, backend_id: str):
    """The user says they signed in again (F8); waiting jobs then run."""
    result = backends.unblock(db(request), backend_id)
    runner(request).wake()
    return result


@router.post('/preview')
def preview(request: Request, body: Preview):
    return jobs.preview(db(request), body.post_id, body.marked_nsfw)


@router.post('/jobs')
def create_job(request: Request, body: JobCreate):
    job = jobs.enqueue(db(request), body.post_id, 'manual', backend_id=body.backend_id,
                       marked_nsfw=body.marked_nsfw)
    runner(request).wake()
    return job


@router.get('/jobs')
def list_jobs(request: Request, post_id: str):
    return {'jobs': jobs.for_post(db(request), post_id)}


@router.get('/jobs/{job_id}')
def read_job(request: Request, job_id: str):
    return jobs.get(db(request), job_id)


@router.post('/jobs/{job_id}/cancel')
async def cancel_job(request: Request, job_id: str):
    return await runner(request).cancel(job_id)


@router.post('/jobs/{job_id}/retry')
def retry_job(request: Request, job_id: str, body: JobRetry | None = None):
    body = body or JobRetry()
    job = jobs.retry(db(request), job_id, body.current_settings, body.backend_id)
    runner(request).wake()
    return job


@router.post('/jobs/{job_id}/select')
def select_job(request: Request, job_id: str):
    return jobs.select(db(request), job_id)


@router.get('/jobs/{job_id}/file')
def job_file(request: Request, job_id: str):
    with db(request).connect() as connection:
        row = connection.execute('SELECT output_file FROM image_jobs WHERE id=?', (job_id,)).fetchone()
    if row is None or row['output_file'] is None:
        raise DomainError('This image could not be found.', 404)
    try:
        path = storage.path_of(db(request), row['output_file'])
    except FileNotFoundError as error:
        raise DomainError('This image file is missing from the workspace.', 404) from error
    return FileResponse(path, media_type=storage.TYPES[path.suffix.lstrip('.')],
                        headers={'Cache-Control': 'private, max-age=31536000, immutable'})


@router.get('/photos/{message_id}')
def read_photo(request: Request, message_id: str):
    """The photo a chat reply sent, with its image's current state."""
    photo = photos.get(db(request), message_id)
    if photo is None:
        raise DomainError('This photo could not be found.', 404)
    return photo


@router.post('/photos/{message_id}/retry')
def retry_photo(request: Request, message_id: str):
    """Try a chat photo that failed again; it shows as on its way until the new attempt ends."""
    photo = photos.retry(db(request), message_id)
    runner(request).wake()
    return photo


# Memes without a picture model (companion/images/meme_pictures.py, gifs.py) ----------------------------

@router.get('/memes')
def read_memes(request: Request):
    """Where meme pictures come from: the user's own templates folder, the classic formats on this computer
    and whether a GIPHY key is saved (never the key itself)."""
    root = db(request).root
    with db(request).connect() as connection:
        classics = bool(jobs.image_settings(connection)['meme_formats'])
    return {'folder': str(meme_pictures.folder(root)), 'mine': len(meme_pictures.mine(root)),
            'pack': len(meme_pictures.pack()), 'formats_on': classics,
            'formats_here': len(meme_pictures.classic(root)), 'formats_total': len(meme_pictures.formats()['formats']),
            'gif_key': gifs.key(request.app.state.vault) is not None, 'key_here': not via_lan(request)}


@router.post('/memes/folder/open')
def open_memes_folder(request: Request):
    """Open the user's meme templates folder on the PC (phones are refused in companion/phone/access.py)."""
    return open_folder(meme_pictures.folder(db(request).root))


@router.put('/memes/gif-key')
def save_gif_key(request: Request, body: GifKey):
    if body.key and via_lan(request):
        raise DomainError('Home Wi-Fi access is not encrypted, so API keys are not sent over it. Add the key over '
                          f'Tailscale, or {ON_THE_PC}.', 403)
    gifs.save_key(request.app.state.vault, body.key)
    return read_memes(request)


@router.get('/memes/pictures/{picture_id}')
def meme_picture(request: Request, picture_id: str):
    path = meme_pictures.path_of(db(request).root, picture_id)
    if path is None:
        raise DomainError('This meme picture could not be found.', 404)
    return FileResponse(path, media_type=meme_pictures.media_type(path), headers={'Cache-Control': 'private, max-age=86400'})
