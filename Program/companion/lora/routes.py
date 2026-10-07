"""LoRA maker API: references, adapters and appearance versions.

`router` is what profile pictures need (their pictures are references), so it is always served.
`maker_router` is the LoRA creator itself and is only served when it is switched on
(companion.lora.maker_enabled, docs/lora.md).
"""
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse

from companion.errors import DomainError
from companion.images.storage import TYPES
from companion.lora import appearance, evaluation, export, generation, portraits, references, training
from companion.lora.models import (
    Adopt,
    EvaluationCreate,
    GenerationCreate,
    GenerationPlan,
    KeepCheckpoint,
    LoraSettingsUpdate,
    Portrait,
    PortraitCreate,
    PortraitPlan,
    Rating,
    ReferenceUpdate,
    RunCreate,
)

router = APIRouter(prefix='/api/lora')
maker_router = APIRouter(prefix='/api/lora')


def db(request: Request):
    return request.app.state.database


@maker_router.get('/settings')
def read_settings(request: Request):
    return appearance.read_settings(db(request))


@maker_router.put('/settings')
def update_settings(request: Request, body: LoraSettingsUpdate):
    return appearance.update_settings(db(request), body)


@router.get('/references')
def list_references(request: Request):
    return references.listing(db(request))


@maker_router.post('/references')
async def add_reference(request: Request, name: str = Query('', max_length=200),
                        dhash: str | None = Query(None, max_length=16)):
    """The body is the picture itself."""
    data = await request.body()
    return references.add(db(request), data, name, dhash)


@maker_router.put('/references/{reference_id}')
def update_reference(request: Request, reference_id: str, body: ReferenceUpdate):
    return references.update(db(request), reference_id, body)


@maker_router.post('/references/{reference_id}/crop')
async def crop_reference(request: Request, reference_id: str, x: float = Query(ge=0, le=1),
                         y: float = Query(ge=0, le=1), width: float = Query(gt=0, le=1),
                         height: float = Query(gt=0, le=1)):
    """The body is the cropped copy drawn by the interface."""
    data = await request.body()
    crop = {'x': x, 'y': y, 'width': width, 'height': height}
    return references.set_crop(db(request), reference_id, crop, data)


@maker_router.delete('/references/{reference_id}/crop')
def clear_crop(request: Request, reference_id: str):
    return references.clear_crop(db(request), reference_id)


@maker_router.delete('/references/{reference_id}')
def remove_reference(request: Request, reference_id: str):
    return references.remove(db(request), reference_id)


@router.get('/references/{reference_id}/file')
def reference_file(request: Request, reference_id: str, cropped: bool = False):
    try:
        path, media_type = references.path_of(db(request), reference_id, cropped)
    except FileNotFoundError as error:
        raise DomainError('This picture is missing from the workspace.', 404) from error
    return FileResponse(path, media_type=media_type, headers={'Cache-Control': 'private, max-age=60'})


@maker_router.post('/references/captions')
def suggest_captions(request: Request):
    return references.suggest_captions(db(request))


@maker_router.get('/adapters')
def list_adapters(request: Request):
    return {'adapters': appearance.adapters(db(request))}


@maker_router.post('/adapters/import')
async def import_adapter(request: Request, name: str = Query(min_length=1, max_length=120),
                         base_model: str = Query(min_length=1, max_length=300),
                         trigger: str = Query('', max_length=100), note: str = Query('', max_length=500)):
    """The body is the .safetensors file."""
    return await appearance.import_adapter(db(request), request.stream(), name=name, base_model=base_model,
                                           trigger=trigger, note=note)


@maker_router.delete('/adapters/{adapter_id}')
def remove_adapter(request: Request, adapter_id: str):
    return {'adapters': appearance.remove_adapter(db(request), adapter_id)}


@maker_router.get('/appearance')
def read_appearance(request: Request):
    return appearance.versions(db(request))


@maker_router.post('/appearance')
def adopt(request: Request, body: Adopt):
    return appearance.adopt(db(request), body)


def runner(request: Request) -> training.TrainingRunner:
    return request.app.state.training


@maker_router.get('/trainer')
def describe_trainer(request: Request):
    return training.describe(db(request))


@maker_router.get('/runs')
def list_runs(request: Request):
    return {'runs': training.listing(db(request))}


@maker_router.post('/runs')
async def create_run(request: Request, body: RunCreate):
    run = training.create(db(request), body)
    runner(request).start(run['id'])
    return run


@maker_router.get('/runs/{run_id}')
def read_run(request: Request, run_id: str):
    return training.get(db(request), run_id)


@maker_router.get('/runs/{run_id}/log', response_class=PlainTextResponse)
def run_log(request: Request, run_id: str):
    with db(request).connect() as connection:
        run = training.get_row(connection, run_id)
    path = training.run_folder(db(request), run) / 'trainer.log'
    return path.read_text(encoding='utf-8', errors='replace')[-200_000:] if path.is_file() else ''


@maker_router.post('/runs/{run_id}/cancel')
async def cancel_run(request: Request, run_id: str):
    return await runner(request).cancel(run_id)


@maker_router.post('/runs/{run_id}/resume')
async def resume_run(request: Request, run_id: str):
    return runner(request).resume(run_id)


@maker_router.post('/runs/{run_id}/restart')
async def restart_run(request: Request, run_id: str):
    return runner(request).restart(run_id)


@maker_router.post('/runs/{run_id}/keep')
def keep_checkpoint(request: Request, run_id: str, body: KeepCheckpoint):
    """Make a verified intermediate checkpoint an adapter, to evaluate or adopt."""
    return training.keep(db(request), run_id, body.step)


@maker_router.get('/evaluations')
def list_evaluations(request: Request, adapter_id: str | None = None):
    return {'evaluations': evaluation.listing(db(request), adapter_id), 'prompts': [
        {'key': key, 'label': label} for key, label, *_rest in evaluation.PROMPTS]}


@maker_router.post('/evaluations')
async def create_evaluation(request: Request, body: EvaluationCreate):
    created = evaluation.create(db(request), body, runner(request).active)
    request.app.state.evaluations.start(created['id'])
    return created


@maker_router.get('/evaluations/{evaluation_id}')
def read_evaluation(request: Request, evaluation_id: str):
    return evaluation.get(db(request), evaluation_id)


@maker_router.post('/evaluations/{evaluation_id}/cancel')
async def cancel_evaluation(request: Request, evaluation_id: str):
    return await request.app.state.evaluations.cancel(evaluation_id)


@maker_router.put('/evaluation-images/{image_id}/rating')
def rate_image(request: Request, image_id: str, body: Rating):
    return evaluation.rate(db(request), image_id, body.rating)


@maker_router.get('/evaluation-images/{image_id}/file')
def evaluation_file(request: Request, image_id: str):
    try:
        path = evaluation.file_of(db(request), image_id)
    except FileNotFoundError as error:
        raise DomainError('This image file is missing from the workspace.', 404) from error
    return FileResponse(path, media_type=TYPES[path.suffix.lstrip('.')],
                        headers={'Cache-Control': 'private, max-age=31536000, immutable'})


@maker_router.get('/adapters/{adapter_id}/export')
def export_adapter(request: Request, adapter_id: str, background: BackgroundTasks):
    """A zip with the adapter, its metadata and license notice; never the training pictures."""
    path, name = export.build(db(request), adapter_id)
    background.add_task(path.unlink, missing_ok=True)
    return FileResponse(path, media_type='application/zip', filename=name)


@maker_router.get('/generations/draft')
def draft_generation(request: Request):
    return generation.draft(db(request))


@maker_router.post('/generations/preview')
def preview_generation(request: Request, body: GenerationPlan):
    return generation.preview(db(request), body)


@maker_router.get('/generations')
def list_generations(request: Request):
    return {'generations': generation.listing(db(request))}


@maker_router.post('/generations')
async def create_generation(request: Request, body: GenerationCreate):
    created = generation.create(db(request), body)
    request.app.state.generations.start(created['id'])
    return created


@router.post('/generations/{generation_id}/cancel')
async def cancel_generation(request: Request, generation_id: str):
    return await request.app.state.generations.cancel(generation_id)


@router.get('/generation-images/{image_id}/file')
def generation_file(request: Request, image_id: str):
    try:
        path = generation.file_of(db(request), image_id)
    except FileNotFoundError as error:
        raise DomainError('This picture file is missing.', 404) from error
    return FileResponse(path, media_type=TYPES.get(path.suffix.lstrip('.'), 'application/octet-stream'))


@router.post('/generation-images/{image_id}/keep')
async def keep_generated(request: Request, image_id: str, role: Literal['train', 'evaluation'] = 'train',
                         dhash: str | None = Query(None, max_length=16)):
    """An optional body is the interface's PNG copy of a WebP output."""
    converted = await request.body()
    return generation.keep(db(request), image_id, role, dhash, converted or None)


@maker_router.post('/generation-images/{image_id}/discard')
def discard_generated(request: Request, image_id: str):
    return generation.discard(db(request), image_id)


@router.get('/portraits/draft')
def draft_portraits(request: Request):
    return portraits.draft(db(request))


@router.post('/portraits/preview')
def preview_portraits(request: Request, body: PortraitPlan):
    return portraits.preview(db(request), body)


@router.get('/portraits')
def latest_portraits(request: Request):
    return {'portraits': portraits.latest(db(request))}


@router.post('/portraits')
async def create_portraits(request: Request, body: PortraitCreate):
    created = portraits.create(db(request), body)
    request.app.state.generations.start(created['id'])
    return created


@router.post('/portraits/{generation_id}/redo')
async def redo_portrait(request: Request, generation_id: str, position: int = Query(ge=0, le=2)):
    again = portraits.redo(db(request), generation_id, position)
    request.app.state.generations.start(generation_id)
    return again


@router.put('/portrait')
def set_portrait(request: Request, body: Portrait):
    return portraits.set_portrait(db(request), body.reference_id)
