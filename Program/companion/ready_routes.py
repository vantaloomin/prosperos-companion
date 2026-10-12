"""The welcome screen and Settings > Models: "Set it up for me" (companion/ready.py)."""
from typing import Annotated, Literal

from fastapi import APIRouter, Request
from pydantic import Field

from companion import characters
from companion.models import CharacterDraftRequest, Input

router = APIRouter(prefix='/api/ready')


class ReadyStart(Input):
    """The model the user confirmed, with its size in front of them."""
    model: Annotated[str, Field(min_length=1, max_length=60)]


class ReadySeen(Input):
    what: Literal['notice', 'settings']


class ReadyQueue(Input):
    """The quick start's picks for the companion just saved, written up when the model is ready."""
    request: CharacterDraftRequest


@router.get('')
def show(request: Request):
    return request.app.state.ready.view()


@router.post('')
async def start(request: Request, body: ReadyStart):
    return request.app.state.ready.start(body.model)


@router.post('/pause')
async def pause(request: Request):
    return await request.app.state.ready.pause()


@router.post('/cancel')
async def cancel(request: Request):
    return await request.app.state.ready.cancel()


@router.delete('')
def discard(request: Request):
    return request.app.state.ready.discard()


@router.post('/use')
def use(request: Request):
    return request.app.state.ready.use()


@router.post('/seen')
def seen(request: Request, body: ReadySeen):
    return request.app.state.ready.seen(body.what)


@router.post('/queue')
async def queue(request: Request, body: ReadyQueue):
    with request.app.state.database.connect() as connection:
        companion = characters.require_current(connection)
    return request.app.state.ready.queue(companion['id'], companion['version']['definition']['name'],
                                         body.request.model_dump())
