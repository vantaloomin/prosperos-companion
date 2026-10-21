"""Observer mode API (companion/observer.py, companion/life/narrator.py): /api/observer."""
from fastapi import APIRouter, Request
from pydantic import Field

from companion import observer
from companion.errors import require
from companion.life import narrator
from companion.models import Input

router = APIRouter(prefix='/api/observer')


class Watching(Input):
    watching: bool | None = None
    # Whose day the Watching page follows: 'companion:<id>' or a townsperson's key.
    focus: str | None = Field(None, min_length=1, max_length=200)


@router.get('')
def read(request: Request):
    """Whether the user is just watching, who the page follows (the app's pick until they choose) and who else
    they could follow."""
    database = request.app.state.database
    with database.connect(write=True) as connection:
        return narrator.state(connection, database.clock.now(), write=observer.watching(connection))


@router.put('')
def change(request: Request, body: Watching):
    database = request.app.state.database
    now = database.clock.now()
    with database.connect(write=True) as connection:
        if body.focus is not None:
            require(narrator.resolve(connection, body.focus) is not None, "They can't be watched any more.", 404)
            observer.follow(connection, body.focus, database.now())
        if body.watching is not None:
            observer.watch(connection, body.watching, database.now())
        return narrator.state(connection, now, write=observer.watching(connection))


@router.get('/feed')
def feed(request: Request, focus: str | None = None):
    """The last week of the focus's days as the narrator tells them, newest day first."""
    database = request.app.state.database
    now = database.clock.now()
    with database.connect(write=True) as connection:
        found = narrator.resolve(connection, focus) if focus else narrator.focus_now(connection, now, write=True)
        require(found is not None, 'There is nobody to watch here yet.', 404)
        return narrator.feed(connection, found, now)
