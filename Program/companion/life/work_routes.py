"""Work life API: the companion's week at work, their project, time off and what changed lately."""
from fastapi import APIRouter, Request

from companion.characters import require_current
from companion.database import settings
from companion.life import work

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
