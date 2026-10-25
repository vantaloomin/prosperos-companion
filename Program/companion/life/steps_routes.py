"""Next steps API (companion/life/steps.py): where the user and the open companion stand, setting the step and the
"just friends" lock, and the Family panel (companion/life/parenthood.py)."""
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import Field

from companion.characters import require_current
from companion.database import settings
from companion.life import expecting, kids, moving_in, our_child, parenthood, steps
from companion.models import Input, KindChange

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


@router.get('/family/turns')
def read_family_turns(request: Request):
    """The pregnancy's hard turn once it has come (bed rest, an early arrival), for Today with an Undo
    (companion/life/expecting.py); an empty list when there is none."""
    database = request.app.state.database
    with database.connect() as connection:
        found = expecting.turn_shown(connection, require_current(connection), database.clock.now())
        return [found] if found else []


@router.post('/family/turns/{journey_id}/undo')
def undo_family_turn(request: Request, journey_id: str):
    """Take the hard turn back; returns the turns still shown (none)."""
    database = request.app.state.database
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        expecting.undo_turn(connection, companion, journey_id, now)
        found = expecting.turn_shown(connection, companion, now)
        return [found] if found else []


class KidsUpdate(Input):
    pattern: str | None = Field(default=None, max_length=20, pattern=r'^[a-z_]+$')
    remove: str | None = Field(default=None, max_length=64, pattern=r'^[0-9a-f]+$')
    restore: str | None = Field(default=None, max_length=64, pattern=r'^[0-9a-f]+$')
    # Their other parent: a circle person's id, 'new' (named by other_name) or 'none'.
    other: str | None = Field(default=None, max_length=64, pattern=r'^(?:[0-9a-f]+|new|none)$')
    other_name: str | None = Field(default=None, max_length=80)
    other_pronouns: Literal['she/her', 'he/him', 'they/them'] | None = None


class KidChange(Input):
    """A child of theirs added by hand or changed: anything left out the app picks (or keeps)."""
    name: str | None = Field(default=None, max_length=60)
    age: int | None = Field(default=None, ge=0, le=17)
    pronouns: Literal['she/her', 'he/him', 'they/them'] | None = None


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
        if body.other is not None:
            kids.set_other(connection, companion, request.app.state.life.world, now, body.other, body.other_name,
                           body.other_pronouns)
        kids.update(connection, companion, now, body.pattern, body.remove, body.restore)
        return read_kids_view(connection, companion, request.app.state.life.world, now)


@router.post('/kids')
def add_kid(request: Request, body: KidChange):
    """Add a child of theirs by hand, the way a pet is added."""
    database = request.app.state.database
    now = database.clock.now()
    world = request.app.state.life.world
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        kids.add(connection, companion, world, now, body.name, body.age, body.pronouns)
        return read_kids_view(connection, companion, world, now)


@router.patch('/kids/{kid_id}')
def edit_kid(request: Request, kid_id: str, body: KidChange):
    """Change a child's name, age or whether they're a son or daughter."""
    database = request.app.state.database
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        kids.edit(connection, companion, kid_id, now, body.name, body.age, body.pronouns)
        return read_kids_view(connection, companion, request.app.state.life.world, now)


class OursUpdate(Input):
    care: str | None = Field(default=None, max_length=20, pattern=r'^[a-z_]+$')
    child: str | None = Field(default=None, max_length=64, pattern=r'^[0-9a-f]+$')
    name: str | None = Field(default=None, max_length=60)
    custody: str | None = Field(default=None, max_length=20, pattern=r'^[a-z_]+$')


def read_ours_view(connection, companion, now) -> dict:
    return our_child.view(connection, companion, now, bool(settings(connection).get('show_odds')))


@router.put('/ours/{child_id}/kind')
def update_child_kind(request: Request, child_id: str, body: KindChange):
    """A child's kind and How long they live, from their card (companion/world/lifespans.py)."""
    database = request.app.state.database
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        our_child.set_kind(connection, companion, child_id, body.kind, body.lifespan, now)
        return read_ours_view(connection, companion, now)


@router.get('/ours')
def read_ours(request: Request):
    """The Family panel's children of yours (companion/life/our_child.py): each child and who looks after them."""
    database = request.app.state.database
    now = database.clock.now()
    with database.connect() as connection:
        return read_ours_view(connection, require_current(connection), now)


@router.put('/ours')
def update_ours(request: Request, body: OursUpdate):
    """Set who looks after them or where they live after a breakup ('auto' lets the app decide), or rename a child."""
    database = request.app.state.database
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        our_child.update(connection, companion, now, body.care, body.child, body.name, body.custody)
        return read_ours_view(connection, companion, now)
