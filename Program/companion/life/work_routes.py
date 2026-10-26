"""Work life API: the companion's week at work, their project, time off and what changed lately."""
from fastapi import APIRouter, Request
from pydantic import Field

from companion.characters import require_current
from companion.database import settings
from companion.errors import require
from companion.life import work
from companion.models import Input

router = APIRouter(prefix='/api/life/work')


@router.get('')
def read_work(request: Request):
    """The Work life panel; vacation counts and pay only with Hidden values' home-life meters on. Null without a job
    in their week."""
    database = request.app.state.database
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        return {'work': work.overview(connection, companion, now, bool(settings(connection).get('show_home_meters')))}


class ProjectChange(Input):
    """What they are working on, in the user's words; empty gives the app's pick back."""
    title: str = Field(max_length=120)


@router.put('/project')
def change_project(request: Request, body: ProjectChange):
    database = request.app.state.database
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        require(work.set_project(connection, companion, body.title, now) is not None, 'They have no job in their week.', 409)
        return {'work': work.overview(connection, companion, now, bool(settings(connection).get('show_home_meters')))}
