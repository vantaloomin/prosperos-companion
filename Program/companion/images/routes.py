"""Image backends, settings and jobs API (PRD F3–F9)."""
import json
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from companion.database import decode
from companion.errors import DomainError
from companion.images import backends, jobs, photos, storage
from companion.images.adapters.base import AdapterError
from companion.images.adapters.comfyui import FILE_INPUTS, default_files, krea_first
from companion.images.models import (
    BackendCreate,
    BackendFields,
    BackendMove,
    ImageSettingsUpdate,
    JobCreate,
    JobRetry,
    Preview,
)
from companion.lora.appearance import current_for_images

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


@router.post('/backends')
def create_backend(request: Request, body: BackendCreate):
    return backends.create(db(request), request.app.state.vault, body)


@router.put('/backends/{backend_id}')
def update_backend(request: Request, backend_id: str, body: BackendFields):
    result = backends.update(db(request), request.app.state.vault, backend_id, body)
    runner(request).wake()
    return result


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


@router.get('/backends/{backend_id}/files')
async def backend_files(request: Request, backend_id: str):
    """The model files and LoRAs a ComfyUI server offers the built-in workflow, from the address the
    user entered, Krea 2's first (`krea` lists those). The character's own LoRA is left out of the
    LoRA list: it is applied by itself. An unreachable server is not an error: the page then takes
    typed names."""
    with db(request).connect() as connection:
        backend = backends.get(connection, backend_id)
        character = current_for_images(connection)['lora'] if connection.execute(
            'SELECT 1 FROM companions').fetchone() else None
    if backend['kind'] != 'comfyui':
        raise DomainError('Only a ComfyUI server lists its model files.', 422)
    config = decode(backend['config'])
    keys = [*FILE_INPUTS, 'lora']
    result = {'ok': True, 'error': None, 'defaults': default_files(), 'options': {key: [] for key in keys},
              'krea': {key: [] for key in keys}, 'character_lora': character['comfy_name'] if character else None}
    try:
        found = await runner(request).adapters['comfyui'].files(config)
    except AdapterError as error:
        result.update(ok=False, error=error.message)
        return result
    for key in keys:
        options = [name for name in found.get(key, []) if not (key == 'lora' and character and name == character['comfy_name'])]
        result['options'][key], result['krea'][key] = krea_first(key, options)
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
