"""Debug API: Debug time (companion/debug_time.py) moves the app clock ahead or runs it faster, then goes back;
Record model calls (companion/model_calls.py) writes every model request and response down; Townsfolk mix
(companion/townsfolk_mix.py) shows what the town is made of and makes a new world with a changed mix. Changes are
PC only."""
from fastapi import APIRouter, Request
from fastapi.responses import Response
from pydantic import Field

from companion import debug_time, model_calls, townsfolk_mix
from companion.models import Input

router = APIRouter(prefix='/api/debug-time')
calls_router = APIRouter(prefix='/api/model-calls')
mix_router = APIRouter(prefix='/api/townsfolk-mix')


class SpeedChange(Input):
    speed: float = Field(ge=1, le=max(debug_time.SPEEDS))


class Jump(Input):
    hours: float | None = Field(default=None, gt=0, le=24 * 30)
    # A date and time without an offset is read in the user's own timezone.
    to: str | None = Field(default=None, max_length=40)


class Finish(Input):
    keep: bool = False


@router.get('')
def status(request: Request):
    return request.app.state.debug_time.status()


@router.post('/start')
def start(request: Request):
    """Takes a verified backup and a copy of the database before the clock moves."""
    debug_time.start(request.app.state.database)
    return request.app.state.debug_time.status()


@router.post('/speed')
def speed(request: Request, body: SpeedChange):
    debug_time.set_speed(request.app.state.database, body.speed)
    return request.app.state.debug_time.status()


@router.post('/jump')
async def jump(request: Request, body: Jump):
    return request.app.state.debug_time.jump(body.hours, body.to)


@router.post('/finish')
async def finish(request: Request, body: Finish):
    return await request.app.state.debug_time.finish(body.keep)


class Recording(Input):
    recording: bool


@calls_router.get('')
def calls(request: Request):
    """Whether model calls are being recorded, and how much is kept."""
    return model_calls.summary(request.app.state.database)


@calls_router.put('')
def record_calls(request: Request, body: Recording):
    database = request.app.state.database
    with database.connect(write=True) as connection:
        connection.execute('UPDATE workspace_settings SET record_model_calls=?, updated_at=? WHERE id=1',
                           (int(body.recording), database.now()))
    return model_calls.summary(database)


@calls_router.get('/download')
def download_calls(request: Request):
    """The recorded days as a zip, to send to whoever is helping."""
    name = f'model-calls-{request.app.state.database.clock.now().date().isoformat()}.zip'
    return Response(model_calls.bundle(request.app.state.database), media_type='application/zip',
                    headers={'Content-Disposition': f'attachment; filename="{name}"'})


@calls_router.delete('')
def clear_calls(request: Request):
    model_calls.clear(request.app.state.database)
    return model_calls.summary(request.app.state.database)


class MixChange(Input):
    """The mix for a new world; companion/world/mix.py holds every value inside its limits."""
    mix: dict[str, float] = Field(max_length=40)


@mix_router.get('')
def town_mix(request: Request):
    """The open world's mix, the built-in one, and what its town is made of, counted."""
    return townsfolk_mix.view(request.app.state.database)


@mix_router.post('/new-world')
async def new_world(request: Request, body: MixChange):
    """A new world made with this mix, switched to. Runs on the event loop, like a switch."""
    return townsfolk_mix.new_world(request.app.state, body.mix)
