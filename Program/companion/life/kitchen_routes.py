"""Kitchen API: how the companion cooks and eats, their week of dinners and pantry, and the user's changes."""
from fastapi import APIRouter, Request
from pydantic import Field

from companion.characters import require_current
from companion.database import optional
from companion.life import kitchen
from companion.models import Input

router = APIRouter(prefix='/api/life/kitchen')


class KitchenUpdate(Input):
    """Each field the user sets wins over the app's pick; `reset` puts all of them back."""
    diet: str | None = Field(default=None, max_length=20)
    avoids: list[str] | None = Field(default=None, max_length=5)
    skill: int | None = Field(default=None, ge=0, le=3)
    bakes: bool | None = None
    favorites: list[str] | None = Field(default=None, max_length=5)
    reset: bool = False


def respond(request: Request, action=None) -> dict:
    database, engine = request.app.state.database, request.app.state.life
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        timeline_id, version = companion['active_timeline_id'], companion['version']
        if action:
            action(connection, timeline_id, version['definition'], engine.world, now)
        shown = optional(connection, 'SELECT show_home_meters FROM workspace_settings WHERE id=1')
        return kitchen.view(connection, timeline_id, version['definition'], engine.world, now, version['timezone'],
                            bool(shown and shown['show_home_meters']))


@router.get('')
def read_kitchen(request: Request):
    """Their kitchen today, seeded the first time it is read."""
    return respond(request)


@router.patch('')
def change_kitchen(request: Request, body: KitchenUpdate):
    """Only the fields sent change; a field sent as null goes back to the app's own pick."""
    changes = body.model_dump(exclude_unset=True)
    return respond(request, lambda connection, timeline_id, definition, world, now: kitchen.change(
        connection, timeline_id, changes, definition, world, now))
