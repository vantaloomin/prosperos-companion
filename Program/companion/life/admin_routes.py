"""Life admin API: the companion's appointments, errands and chores, and moving one to another day; the wedding being
planned (companion/life/wedding.py), which the user can move, send elsewhere, resize or trim."""
from datetime import date

from fastapi import APIRouter, Request
from pydantic import Field

from companion.characters import require_current
from companion.database import settings
from companion.life import admin, wedding
from companion.models import Input

router = APIRouter(prefix='/api/life/admin')


def overview(request: Request, entry_id: str | None = None, change: 'WeddingChange | None' = None) -> dict:
    """The Life admin panel, after moving an entry when one is named. The agenda picks the move up when it next
    extends; the meter shows only with Hidden values' home-life meters on. The wedding plan is part of it."""
    database = request.app.state.database
    now = database.clock.now()
    with database.connect(write=bool(entry_id or change)) as connection:
        companion = require_current(connection)
        if entry_id:
            admin.user_move(connection, companion, entry_id, now)
        if change:
            wedding.change(connection, companion, now, day=change.day, venue=change.venue, size=change.size,
                           guest=change.guest, invited=change.invited)
        found = settings(connection)
        return {**admin.overview(connection, companion, now, bool(found.get('show_home_meters'))),
                'wedding': wedding.panel(connection, companion, now, bool(found.get('show_odds')))}


@router.get('')
def read_admin(request: Request):
    return overview(request)


class WeddingChange(Input):
    """One change to the wedding plan: another day, another venue, another size, or a guest left off or back on."""
    day: date | None = None
    venue: bool = False
    size: str | None = Field(default=None, max_length=10)
    guest: str | None = Field(default=None, max_length=80)
    invited: bool | None = None


@router.put('/wedding')
def change_wedding(request: Request, body: WeddingChange):
    return overview(request, change=body)


@router.post('/{entry_id}/move')
def move_entry(request: Request, entry_id: str):
    """Another day: the nearest free time from the next day on."""
    return overview(request, entry_id)
