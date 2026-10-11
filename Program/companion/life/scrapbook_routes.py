"""Our year so far API: the scrapbooks there are, and one scrapbook's pages."""
from fastapi import APIRouter, Request

from companion.characters import require_current
from companion.life import scrapbook

router = APIRouter(prefix='/api/life/year')


@router.get('')
def list_scrapbooks(request: Request):
    """The year so far, each full year and each calendar year, with the one Today points to."""
    database = request.app.state.database
    with database.connect() as connection:
        return scrapbook.listing(connection, require_current(connection), database.clock.now())


@router.get('/{key}')
def read_scrapbook(request: Request, key: str):
    database = request.app.state.database
    with database.connect() as connection:
        return scrapbook.build(connection, require_current(connection), key, database.clock.now())


@router.post('/{key}/seen')
def mark_seen(request: Request, key: str):
    """Today's scrapbook card was opened or put away; it stays away."""
    database = request.app.state.database
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        scrapbook.seen(connection, companion, key, database.clock.now())
        return scrapbook.listing(connection, companion, database.clock.now())
