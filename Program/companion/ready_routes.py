"""The welcome screen and Settings > Models: "Set it up for me" (companion/ready.py)."""
from typing import Annotated

from fastapi import APIRouter, Request
from pydantic import Field

from companion.models import Input

router = APIRouter(prefix='/api/ready')


class ReadyStart(Input):
    """The model the user confirmed, with its size in front of them."""
    model: Annotated[str, Field(min_length=1, max_length=60)]


@router.get('')
def show(request: Request):
    return request.app.state.ready.view()


@router.post('')
async def start(request: Request, body: ReadyStart):
    return request.app.state.ready.start(body.model)


@router.post('/pause')
async def pause(request: Request):
    return await request.app.state.ready.pause()
