"""Family traditions API: the holidays the companion's family keeps, and the user's edits to them."""
from fastapi import APIRouter, Request
from pydantic import Field

from companion.almanac.context import city_for
from companion.characters import require_current
from companion.life import circle, traditions
from companion.models import Input

router = APIRouter(prefix='/api/life/traditions')


class TraditionText(Input):
    text: str = Field(min_length=1, max_length=traditions.TEXT_LIMIT, pattern=r'\S')


class TraditionCreate(TraditionText):
    holiday: str = Field(min_length=1, max_length=60)


def change(request: Request, action=None) -> dict:
    """Run `action(connection, companion, now)` on the active timeline's traditions, then return the panel. The
    traditions are seeded the first time they are read, once the circle exists."""
    database, engine = request.app.state.database, request.app.state.life
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        circle.ensure(connection, companion, engine.world, now)
        traditions.ensure(connection, companion, city_for(connection, companion['version']['definition']), now)
        if action:
            holiday = action(connection, companion, now)
            traditions.rebuild(connection, companion, holiday, now)
        return traditions.view(connection, companion, now)


def holiday_of(connection, companion, tradition_id) -> str:
    return traditions.row(connection, companion['active_timeline_id'], tradition_id)['holiday']


@router.get('')
def read_traditions(request: Request):
    return change(request)


@router.post('')
def add_tradition(request: Request, body: TraditionCreate):
    def add(connection, companion, now):
        traditions.add(connection, companion, body.holiday, body.text, now)
        return body.holiday
    return change(request, add)


@router.patch('/{tradition_id}')
def edit_tradition(request: Request, tradition_id: str, body: TraditionText):
    def edit(connection, companion, now):
        traditions.edit(connection, companion['active_timeline_id'], tradition_id, body.text, now)
        return holiday_of(connection, companion, tradition_id)
    return change(request, edit)


@router.post('/{tradition_id}/remove')
def remove_tradition(request: Request, tradition_id: str):
    def remove(connection, companion, now):
        traditions.set_removed(connection, companion['active_timeline_id'], tradition_id, True, now)
        return holiday_of(connection, companion, tradition_id)
    return change(request, remove)


@router.post('/{tradition_id}/restore')
def restore_tradition(request: Request, tradition_id: str):
    def restore(connection, companion, now):
        traditions.set_removed(connection, companion['active_timeline_id'], tradition_id, False, now)
        return holiday_of(connection, companion, tradition_id)
    return change(request, restore)
