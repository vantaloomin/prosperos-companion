"""Home and belongings API: what the companion lives with, and the user's edits to it."""
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import Field

from companion.characters import require_current
from companion.life import home
from companion.models import Input

router = APIRouter(prefix='/api/life/home')


class ItemUpdate(Input):
    name: str | None = Field(default=None, min_length=1, max_length=80, pattern=r'\S')
    description: str | None = Field(default=None, max_length=300)
    variety: str | None = Field(default=None, max_length=40)


class ItemCreate(Input):
    kind: Literal['pet', 'plant', 'vehicle', 'favorite']
    name: str = Field(min_length=1, max_length=80, pattern=r'\S')
    description: str = Field(default='', max_length=300)
    variety: str = Field(default='', max_length=40)


def change(request: Request, action, include_removed=False) -> dict:
    """Run `action(connection, timeline_id, today, now)` on the active timeline's home, then return it."""
    database, engine = request.app.state.database, request.app.state.life
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        timeline_id, version = companion['active_timeline_id'], companion['version']
        today = home.today_for(version, now)
        home.ensure(connection, timeline_id, version['definition'], engine.world, now)
        home.evolve(connection, timeline_id, today, now)
        if action:
            action(connection, timeline_id, today, now)
        return home.view(connection, timeline_id, today, include_removed)


@router.get('')
def read_home(request: Request, include_removed: bool = False):
    """Their home and belongings today, assembled the first time it is read."""
    return change(request, None, include_removed)


@router.post('/items')
def add_item(request: Request, body: ItemCreate):
    return change(request, lambda connection, timeline_id, today, now: home.add(
        connection, timeline_id, body.model_dump(), today, now), True)


@router.patch('/items/{item_id}')
def edit_item(request: Request, item_id: str, body: ItemUpdate):
    return change(request, lambda connection, timeline_id, today, now: home.edit(
        connection, timeline_id, item_id, body.model_dump(), today, now), True)


@router.post('/items/{item_id}/remove')
def remove_item(request: Request, item_id: str):
    return change(request, lambda connection, timeline_id, today, now: home.set_removed(
        connection, timeline_id, item_id, True, today, now), True)


@router.post('/items/{item_id}/restore')
def restore_item(request: Request, item_id: str):
    return change(request, lambda connection, timeline_id, today, now: home.set_removed(
        connection, timeline_id, item_id, False, today, now), True)
