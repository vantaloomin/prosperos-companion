"""Debug time API (companion/debug_time.py): move the app clock ahead or run it faster, then go back."""
from fastapi import APIRouter, Request
from pydantic import Field

from companion import debug_time
from companion.models import Input

router = APIRouter(prefix='/api/debug-time')


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
