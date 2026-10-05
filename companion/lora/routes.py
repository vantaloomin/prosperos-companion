"""LoRA maker API: references, adapters and appearance versions."""
from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse

from companion.errors import DomainError
from companion.lora import appearance, references
from companion.lora.models import Adopt, LoraSettingsUpdate, ReferenceUpdate

router = APIRouter(prefix='/api/lora')


def db(request: Request):
    return request.app.state.database


@router.get('/settings')
def read_settings(request: Request):
    return appearance.read_settings(db(request))


@router.put('/settings')
def update_settings(request: Request, body: LoraSettingsUpdate):
    return appearance.update_settings(db(request), body)


@router.get('/references')
def list_references(request: Request):
    return references.listing(db(request))


@router.post('/references')
async def add_reference(request: Request, name: str = Query('', max_length=200),
                        dhash: str | None = Query(None, max_length=16)):
    """The body is the picture itself."""
    data = await request.body()
    return references.add(db(request), data, name, dhash)


@router.put('/references/{reference_id}')
def update_reference(request: Request, reference_id: str, body: ReferenceUpdate):
    return references.update(db(request), reference_id, body)


@router.post('/references/{reference_id}/crop')
async def crop_reference(request: Request, reference_id: str, x: float = Query(ge=0, le=1),
                         y: float = Query(ge=0, le=1), width: float = Query(gt=0, le=1),
                         height: float = Query(gt=0, le=1)):
    """The body is the cropped copy drawn by the interface."""
    data = await request.body()
    crop = {'x': x, 'y': y, 'width': width, 'height': height}
    return references.set_crop(db(request), reference_id, crop, data)


@router.delete('/references/{reference_id}/crop')
def clear_crop(request: Request, reference_id: str):
    return references.clear_crop(db(request), reference_id)


@router.delete('/references/{reference_id}')
def remove_reference(request: Request, reference_id: str):
    return references.remove(db(request), reference_id)


@router.get('/references/{reference_id}/file')
def reference_file(request: Request, reference_id: str, cropped: bool = False):
    try:
        path, media_type = references.path_of(db(request), reference_id, cropped)
    except FileNotFoundError as error:
        raise DomainError('This picture is missing from the workspace.', 404) from error
    return FileResponse(path, media_type=media_type, headers={'Cache-Control': 'private, max-age=60'})


@router.post('/references/captions')
def suggest_captions(request: Request):
    return references.suggest_captions(db(request))


@router.get('/adapters')
def list_adapters(request: Request):
    return {'adapters': appearance.adapters(db(request))}


@router.post('/adapters/import')
async def import_adapter(request: Request, name: str = Query(min_length=1, max_length=120),
                         base_model: str = Query(min_length=1, max_length=300),
                         trigger: str = Query('', max_length=100), note: str = Query('', max_length=500)):
    """The body is the .safetensors file."""
    return await appearance.import_adapter(db(request), request.stream(), name=name, base_model=base_model,
                                           trigger=trigger, note=note)


@router.delete('/adapters/{adapter_id}')
def remove_adapter(request: Request, adapter_id: str):
    return {'adapters': appearance.remove_adapter(db(request), adapter_id)}


@router.get('/appearance')
def read_appearance(request: Request):
    return appearance.versions(db(request))


@router.post('/appearance')
def adopt(request: Request, body: Adopt):
    return appearance.adopt(db(request), body)
