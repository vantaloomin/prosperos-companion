"""Reading, watching and listening API: what the companion is on now and lately, and the user's changes."""
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import Field

from companion.characters import require_current
from companion.database import optional
from companion.life import media
from companion.models import Input

router = APIRouter(prefix='/api/life/media')


class MediaUpdate(Input):
    """Sets what they are on now for one kind; `reset` goes back to a pick of their own."""
    kind: Literal['book', 'show', 'music']
    title: str = Field(default='', max_length=120)
    by: str = Field(default='', max_length=80)
    reset: bool = False


def respond(request: Request, changes: dict | None = None) -> dict:
    database, engine = request.app.state.database, request.app.state.life
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        timeline_id, version = companion['active_timeline_id'], companion['version']
        if changes:
            media.change(connection, timeline_id, changes, version['definition'], engine.world, now,
                         version['timezone'])
        shown = optional(connection, 'SELECT show_home_meters FROM workspace_settings WHERE id=1')
        return media.view(connection, timeline_id, version['definition'], engine.world, now, version['timezone'],
                          bool(shown and shown['show_home_meters']))


@router.get('')
def read_media(request: Request):
    """What they are reading, watching and have on repeat, picked the first time it is read."""
    return respond(request)


@router.patch('')
def change_media(request: Request, body: MediaUpdate):
    return respond(request, body.model_dump())
