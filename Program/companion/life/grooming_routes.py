"""Looks that change API: how the companion looks lately, and whether their looks may change at all."""
from fastapi import APIRouter, Request

from companion.characters import require_current
from companion.database import settings
from companion.life import grooming, wardrobe
from companion.models import Input

router = APIRouter(prefix='/api/life/grooming')


class Kept(Input):
    kept: bool


def answer(request: Request, kept: bool | None = None) -> dict:
    """Bring their looks up to today (set up the first time they are read), optionally keep them as they are, and
    return how they look lately."""
    database, engine = request.app.state.database, request.app.state.life
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        timeline_id, version = companion['active_timeline_id'], companion['version']
        today = wardrobe.today_for(version, now)
        grooming.ensure(connection, timeline_id, version['definition'], engine.world, now)
        grooming.evolve(connection, timeline_id, version['definition'], today, now)
        if kept is not None:
            grooming.set_kept(connection, timeline_id, kept, now)
        return grooming.view(connection, companion, today, bool(settings(connection)['show_home_meters']))


@router.get('')
def read_looks(request: Request):
    return answer(request)


@router.put('')
def keep_looks(request: Request, body: Kept):
    """Keep their looks as they are (no more changes, and the ones made are set aside), or let them change again."""
    return answer(request, body.kept)
