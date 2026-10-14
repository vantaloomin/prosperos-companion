"""Our history at a glance API: the "All of it" lines, and the user's own words for one of them."""
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from companion.characters import require_current
from companion.memory import history

router = APIRouter(prefix='/api/life/history')


class Correction(BaseModel):
    # Empty text leaves the line out of what they remember.
    text: str = Field(max_length=2000)


@router.get('')
def read_history(request: Request):
    """Every line of the whole time together, oldest first."""
    database = request.app.state.database
    with database.connect() as connection:
        return history.view(connection, require_current(connection), database.clock.now())


@router.put('/{key}')
def correct_line(request: Request, key: str, body: Correction):
    database = request.app.state.database
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        history.correct(connection, companion, key, body.text, database.now(), database.clock.now())
        return history.view(connection, companion, database.clock.now())


@router.delete('/{key}')
def restore_line(request: Request, key: str):
    """Put the app's own line back."""
    database = request.app.state.database
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        history.correct(connection, companion, key, None, database.now(), database.clock.now())
        return history.view(connection, companion, database.clock.now())
