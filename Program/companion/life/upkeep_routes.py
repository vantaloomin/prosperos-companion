"""Home upkeep API: how tidy the companion's place is, Set it, and their habit (companion/life/upkeep.py)."""
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import Field

from companion.characters import require_current
from companion.life import home, upkeep
from companion.models import Input

router = APIRouter(prefix='/api/life/upkeep')


class UpkeepUpdate(Input):
    # Set it: 0 spotless to 4 a disaster, from today on; it drifts with their week after that.
    tidiness: int | None = Field(default=None, ge=0, le=4)
    # Their habit, or 'auto' to go back to the one the app picked.
    habit: Literal['neat', 'average', 'messy', 'auto'] | None = None


def change(request: Request, body: UpkeepUpdate | None = None) -> dict:
    database, engine = request.app.state.database, request.app.state.life
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        timeline_id, version = companion['active_timeline_id'], companion['version']
        today = home.today_for(version, now)
        upkeep.ensure(connection, timeline_id, version['definition'], engine.world, now)
        if body and body.habit:
            upkeep.set_habit(connection, timeline_id, None if body.habit == 'auto' else body.habit, now)
        if body and body.tidiness is not None:
            upkeep.set_tidiness(connection, timeline_id, body.tidiness, today, now)
        return upkeep.view(connection, timeline_id, version['definition'], today)


@router.get('')
def read_upkeep(request: Request):
    """How the place is today, their habit and recent housework."""
    return change(request)


@router.put('')
def update_upkeep(request: Request, body: UpkeepUpdate):
    return change(request, body)
