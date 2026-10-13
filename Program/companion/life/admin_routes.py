"""Life admin API: the companion's appointments, errands and chores, and moving one to another day."""
from fastapi import APIRouter, Request

from companion.characters import require_current
from companion.database import settings
from companion.life import admin

router = APIRouter(prefix='/api/life/admin')


def overview(request: Request, entry_id: str | None = None) -> dict:
    """The Life admin panel, after moving an entry when one is named. The agenda picks the move up when it next
    extends; the meter shows only with Hidden values' home-life meters on."""
    database = request.app.state.database
    now = database.clock.now()
    with database.connect(write=bool(entry_id)) as connection:
        companion = require_current(connection)
        if entry_id:
            admin.user_move(connection, companion, entry_id, now)
        return admin.overview(connection, companion, now, bool(settings(connection).get('show_home_meters')))


@router.get('')
def read_admin(request: Request):
    return overview(request)


@router.post('/{entry_id}/move')
def move_entry(request: Request, entry_id: str):
    """Another day: the nearest free time from the next day on."""
    return overview(request, entry_id)
