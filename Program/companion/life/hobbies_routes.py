"""Pastimes API: the companion's hobbies as they progress, and the user's changes."""
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import Field

from companion.characters import require_current
from companion.database import optional
from companion.life import hobbies
from companion.models import Input

router = APIRouter(prefix='/api/life/hobbies')


class HobbyNew(Input):
    name: str = Field(min_length=1, max_length=40)
    level: int | None = Field(default=None, ge=0, le=4)


class HobbyUpdate(Input):
    """Only the fields sent change."""
    level: int | None = Field(default=None, ge=0, le=4)
    kept: bool | None = None
    status: Literal['active', 'dropped'] | None = None


def respond(request: Request, action=None) -> dict:
    database, engine = request.app.state.database, request.app.state.life
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        timeline_id, version = companion['active_timeline_id'], companion['version']
        if action:
            action(connection, timeline_id, version['definition'], engine.world, now, version['timezone'])
        shown = optional(connection, 'SELECT show_home_meters FROM workspace_settings WHERE id=1')
        return hobbies.view(connection, timeline_id, version['definition'], engine.world, now, version['timezone'],
                            bool(shown and shown['show_home_meters']))


@router.get('')
def read_hobbies(request: Request):
    """Their pastimes today, seeded the first time they are read."""
    return respond(request)


@router.post('')
def add_hobby(request: Request, body: HobbyNew):
    """A pastime the user gives them; it is never given up on its own."""
    return respond(request, lambda connection, timeline_id, definition, world, now, timezone: hobbies.add(
        connection, timeline_id, definition, world, now, timezone, body.name, body.level))


@router.patch('/{hobby_id}')
def change_hobby(request: Request, hobby_id: str, body: HobbyUpdate):
    changes = body.model_dump(exclude_unset=True)
    return respond(request, lambda connection, timeline_id, definition, world, now, timezone: hobbies.edit(
        connection, timeline_id, hobby_id, changes, definition, world, now, timezone))
