"""Wardrobe API: the companion's clothes, what they have on now, and the user's edits to them."""
from fastapi import APIRouter, Request
from pydantic import Field

from companion.characters import require_current
from companion.life import wardrobe
from companion.models import Input

router = APIRouter(prefix='/api/life/wardrobe')


class PieceUpdate(Input):
    name: str | None = Field(default=None, min_length=1, max_length=120, pattern=r'\S')
    description: str | None = Field(default=None, max_length=300)
    category: str | None = Field(default=None, max_length=20)
    favorite: bool | None = None


class PieceCreate(Input):
    category: str = Field(max_length=20)
    name: str = Field(min_length=1, max_length=120, pattern=r'\S')
    description: str = Field(default='', max_length=300)
    favorite: bool = False


def change(request: Request, action, include_removed=False) -> dict:
    """Run `action(connection, timeline_id, today, now)` on the active timeline's wardrobe, then return it."""
    database, engine = request.app.state.database, request.app.state.life
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        timeline_id, version = companion['active_timeline_id'], companion['version']
        today = wardrobe.today_for(version, now)
        wardrobe.ensure(connection, timeline_id, version['definition'], engine.world, now)
        wardrobe.evolve(connection, timeline_id, version['definition'], today, now)
        if action:
            action(connection, timeline_id, today, now)
        return wardrobe.view(connection, timeline_id, today, now, include_removed)


@router.get('')
def read_wardrobe(request: Request, include_removed: bool = False):
    """Their clothes today, assembled the first time they are read."""
    return change(request, None, include_removed)


@router.post('/items')
def add_piece(request: Request, body: PieceCreate):
    return change(request, lambda connection, timeline_id, today, now: wardrobe.add(
        connection, timeline_id, body.model_dump(), today, now), True)


@router.patch('/items/{item_id}')
def edit_piece(request: Request, item_id: str, body: PieceUpdate):
    return change(request, lambda connection, timeline_id, today, now: wardrobe.edit(
        connection, timeline_id, item_id, body.model_dump(), today, now), True)


@router.post('/items/{item_id}/remove')
def remove_piece(request: Request, item_id: str):
    return change(request, lambda connection, timeline_id, today, now: wardrobe.set_removed(
        connection, timeline_id, item_id, True, today, now), True)


@router.post('/items/{item_id}/restore')
def restore_piece(request: Request, item_id: str):
    return change(request, lambda connection, timeline_id, today, now: wardrobe.set_removed(
        connection, timeline_id, item_id, False, today, now), True)
