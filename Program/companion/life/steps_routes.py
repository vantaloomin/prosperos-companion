"""Next steps API (companion/life/steps.py): where the user and the open companion stand, setting the step and the
"just friends" lock, and the Family panel (companion/life/parenthood.py)."""
from fastapi import APIRouter, Request
from pydantic import Field

from companion.characters import require_current
from companion.database import settings
from companion.life import kids, moving_in, our_child, parenthood, steps
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


class FamilyUpdate(Input):
    wants: str | None = Field(default=None, max_length=20, pattern=r'^[a-z_]+$')
    route: str | None = Field(default=None, max_length=20, pattern=r'^[a-z_]+$')
    decided: bool | None = None
    name: str | None = Field(default=None, max_length=60)
    another: bool | None = None


def read_family_view(connection, companion, now) -> dict:
    return parenthood.view(connection, companion, now, bool(settings(connection).get('show_odds')))


@router.get('/family')
def read_family(request: Request):
    """The Family panel on the Character page: whether they want children, how a child would come for you two, and
    whether you have decided to start a family; the odds only with Hidden values' odds on."""
    database = request.app.state.database
    now = database.clock.now()
    with database.connect(write=True) as connection:
        return read_family_view(connection, require_current(connection), now)


@router.put('/family')
def update_family(request: Request, body: FamilyUpdate):
    """Set whether they want children ('auto' lets the app decide), how a child would come, or the step."""
    database = request.app.state.database
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        parenthood.update(connection, companion, now, body.wants, body.route, body.decided, body.name,
                          body.another)
        return read_family_view(connection, companion, now)


class KidsUpdate(Input):
    pattern: str | None = Field(default=None, max_length=20, pattern=r'^[a-z_]+$')
    remove: str | None = Field(default=None, max_length=64, pattern=r'^[0-9a-f]+$')
    restore: str | None = Field(default=None, max_length=64, pattern=r'^[0-9a-f]+$')


def read_kids_view(connection, companion, world, now) -> dict:
    return kids.view(connection, companion, world, now, bool(settings(connection).get('show_odds')))


@router.get('/kids')
def read_kids(request: Request):
    """The Family panel's kids (companion/life/kids.py): their children, where they live and their other parent."""
    database = request.app.state.database
    now = database.clock.now()
    with database.connect(write=True) as connection:
        return read_kids_view(connection, require_current(connection), request.app.state.life.world, now)


@router.put('/kids')
def update_kids(request: Request, body: KidsUpdate):
    """Set where the kids live ('auto' lets the app decide), or take a child out of their life."""
    database = request.app.state.database
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        kids.update(connection, companion, now, body.pattern, body.remove, body.restore)
        return read_kids_view(connection, companion, request.app.state.life.world, now)


class OursUpdate(Input):
    care: str | None = Field(default=None, max_length=20, pattern=r'^[a-z_]+$')
    child: str | None = Field(default=None, max_length=64, pattern=r'^[0-9a-f]+$')
    name: str | None = Field(default=None, max_length=60)


def read_ours_view(connection, companion, now) -> dict:
    return our_child.view(connection, companion, now, bool(settings(connection).get('show_odds')))


@router.get('/ours')
def read_ours(request: Request):
    """The Family panel's children of yours (companion/life/our_child.py): each child and who looks after them."""
    database = request.app.state.database
    now = database.clock.now()
    with database.connect() as connection:
        return read_ours_view(connection, require_current(connection), now)


@router.put('/ours')
def update_ours(request: Request, body: OursUpdate):
    """Set who looks after them ('auto' lets the app decide), or rename a child."""
    database = request.app.state.database
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        our_child.update(connection, companion, now, body.care, body.child, body.name)
        return read_ours_view(connection, companion, now)
