"""LoRA maker API: references, adapters and appearance versions."""
from fastapi import APIRouter, BackgroundTasks, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse

from companion.errors import DomainError
from companion.images.storage import TYPES
from companion.lora import appearance, evaluation, export, references, training
from companion.lora.models import (
    Adopt,
    EvaluationCreate,
    KeepCheckpoint,
    LoraSettingsUpdate,
    Rating,
    ReferenceUpdate,
    RunCreate,
)

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


def runner(request: Request) -> training.TrainingRunner:
    return request.app.state.training


@router.get('/trainer')
def describe_trainer(request: Request):
    return training.describe(db(request))


@router.get('/runs')
def list_runs(request: Request):
    return {'runs': training.listing(db(request))}


@router.post('/runs')
async def create_run(request: Request, body: RunCreate):
    run = training.create(db(request), body)
    runner(request).start(run['id'])
    return run


@router.get('/runs/{run_id}')
def read_run(request: Request, run_id: str):
    return training.get(db(request), run_id)


@router.get('/runs/{run_id}/log', response_class=PlainTextResponse)
def run_log(request: Request, run_id: str):
    with db(request).connect() as connection:
        run = training.get_row(connection, run_id)
    path = training.run_folder(db(request), run) / 'trainer.log'
    return path.read_text(encoding='utf-8', errors='replace')[-200_000:] if path.is_file() else ''


@router.post('/runs/{run_id}/cancel')
async def cancel_run(request: Request, run_id: str):
    return await runner(request).cancel(run_id)


@router.post('/runs/{run_id}/resume')
async def resume_run(request: Request, run_id: str):
    return runner(request).resume(run_id)


@router.post('/runs/{run_id}/restart')
async def restart_run(request: Request, run_id: str):
    return runner(request).restart(run_id)


@router.post('/runs/{run_id}/keep')
def keep_checkpoint(request: Request, run_id: str, body: KeepCheckpoint):
    """Make a verified intermediate checkpoint an adapter, to evaluate or adopt."""
    return training.keep(db(request), run_id, body.step)


@router.get('/evaluations')
def list_evaluations(request: Request, adapter_id: str | None = None):
    return {'evaluations': evaluation.listing(db(request), adapter_id), 'prompts': [
        {'key': key, 'label': label} for key, label, *_rest in evaluation.PROMPTS]}


@router.post('/evaluations')
async def create_evaluation(request: Request, body: EvaluationCreate):
    created = evaluation.create(db(request), body, runner(request).active)
    request.app.state.evaluations.start(created['id'])
    return created


@router.get('/evaluations/{evaluation_id}')
def read_evaluation(request: Request, evaluation_id: str):
    return evaluation.get(db(request), evaluation_id)


@router.post('/evaluations/{evaluation_id}/cancel')
async def cancel_evaluation(request: Request, evaluation_id: str):
    return await request.app.state.evaluations.cancel(evaluation_id)


@router.put('/evaluation-images/{image_id}/rating')
def rate_image(request: Request, image_id: str, body: Rating):
    return evaluation.rate(db(request), image_id, body.rating)


@router.get('/evaluation-images/{image_id}/file')
def evaluation_file(request: Request, image_id: str):
    try:
        path = evaluation.file_of(db(request), image_id)
    except FileNotFoundError as error:
        raise DomainError('This image file is missing from the workspace.', 404) from error
    return FileResponse(path, media_type=TYPES[path.suffix.lstrip('.')],
                        headers={'Cache-Control': 'private, max-age=31536000, immutable'})


@router.get('/adapters/{adapter_id}/export')
def export_adapter(request: Request, adapter_id: str, background: BackgroundTasks):
    """A zip with the adapter, its metadata and license notice; never the training pictures."""
    path, name = export.build(db(request), adapter_id)
    background.add_task(path.unlink, missing_ok=True)
    return FileResponse(path, media_type='application/zip', filename=name)
