"""Their look in chat API (companion/their_look.py): the open chat's colours and name font, the Character page's
"Their look", and the looks of a group chat's members."""
from fastapi import APIRouter, Query, Request
from pydantic import Field

from companion import their_look
from companion.characters import by_id, require_current
from companion.models import Input

router = APIRouter(prefix='/api/their-look')


class LookChange(Input):
    # '' hands it back to the app's pick.
    family: str | None = Field(default=None, max_length=40)
    font: str | None = Field(default=None, max_length=40)
    steady: bool | None = None
    use_mine: bool | None = None


@router.get('')
def read_look(request: Request):
    database = request.app.state.database
    with database.connect(write=True) as connection:
        return their_look.view(connection, require_current(connection), database.clock.now())


@router.put('')
def change_look(request: Request, body: LookChange):
    database = request.app.state.database
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        their_look.change(connection, companion, now, **body.model_dump())
        return their_look.view(connection, companion, now)


@router.get('/group')
def group_looks(request: Request, ids: str = Query(default='', max_length=2000)):
    """Members' looks by companion id, in the order given: who joined first keeps theirs."""
    database = request.app.state.database
    with database.connect() as connection:
        found = [companion for item in ids.split(',') if item and (companion := by_id(connection, item))]
        return {'looks': their_look.group(connection, found, database.clock.now())}
