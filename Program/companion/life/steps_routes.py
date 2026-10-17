"""Next steps API (companion/life/steps.py): where the user and the open companion stand, setting the step and the
"just friends" lock."""
from fastapi import APIRouter, Request
from pydantic import Field

from companion.characters import require_current
from companion.database import settings
from companion.life import moving_in, steps
from companion.models import Input

router = APIRouter(prefix='/api/life/steps')


class StepsUpdate(Input):
    step: str | None = Field(default=None, max_length=40, pattern=r'^[a-z_]+$')
    just_friends: bool | None = None


def read(connection, companion, now) -> dict:
    return steps.view(connection, companion, now, bool(settings(connection).get('show_odds')))


@router.get('')
def read_steps(request: Request):
    """The steps panel on the Character page; what is planned and the odds only with Hidden values' odds on."""
    database = request.app.state.database
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        steps.ensure(connection, companion, now)
        return read(connection, companion, now)


@router.put('')
def update_steps(request: Request, body: StepsUpdate):
    """Set the step (further along or further back) or the "just friends" lock."""
    database = request.app.state.database
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        if body.step is not None:
            steps.set_step(connection, companion, body.step, now)
            moving_in.follow_step(connection, companion, now)  # Where they live follows (companion/life/moving_in.py).
            if body.step == moving_in.STEP:
                moving_in.move_in_now(connection, companion, now)  # A move into a shared home not made yet.
        if body.just_friends is not None:
            steps.set_lock(connection, companion, body.just_friends, database.now())
        return read(connection, companion, now)
