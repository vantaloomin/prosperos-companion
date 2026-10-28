"""Local politics API: Talk of the town on Today, and the user's changes to the city's issues and factions
(companion/life/politics.py)."""
from fastapi import APIRouter, Request
from pydantic import Field

from companion.characters import require_current
from companion.errors import require
from companion.life import network, storylines
from companion.life import politics as town_politics
from companion.models import Input

router = APIRouter(prefix='/api/life/politics')
Name = Field(min_length=1, max_length=80)


class IssueNew(Input):
    title: str = Name
    question: str = Field(default='', max_length=200)
    sides: list[str] = Field(min_length=2, max_length=2)
    stands: list[str] = Field(default_factory=lambda: ['', ''], min_length=2, max_length=2)


class IssueChange(Input):
    """Only the fields sent change. `outcome`: 0 or 1 for the side that won, 2 for fizzled out, null undoes it."""
    title: str | None = Field(default=None, min_length=1, max_length=80)
    question: str | None = Field(default=None, max_length=200)
    sides: list[str] | None = Field(default=None, min_length=2, max_length=2)
    outcome: int | None = Field(default=None, ge=0, le=2)
    ended: bool | None = None


class ViewChange(Input):
    issue: str = Field(min_length=1, max_length=120)
    person: str = Field(min_length=1, max_length=200)
    view: int | None = Field(default=None, ge=-2, le=2)


class FactionNew(Input):
    name: str = Name
    kind: str = Field(default='', max_length=40)
    about: str = Field(default='', max_length=400)
    pull: int = Field(default=2, ge=1, le=5)


class FactionChange(Input):
    """Only the fields sent change. `issue` with `side` (0, 1 or null for its own) says which side it takes."""
    name: str | None = Field(default=None, min_length=1, max_length=80)
    kind: str | None = Field(default=None, max_length=40)
    about: str | None = Field(default=None, max_length=400)
    pull: int | None = Field(default=None, ge=1, le=5)
    add_member: str | None = Field(default=None, max_length=200)
    remove_member: str | None = Field(default=None, max_length=200)
    issue: str | None = Field(default=None, max_length=120)
    side: int | None = Field(default=None, ge=0, le=1)


class RelationChange(Input):
    a: str = Field(min_length=1, max_length=120)
    b: str = Field(min_length=1, max_length=120)
    stance: int | None = Field(default=None, ge=-2, le=2)


def respond(request: Request, action=None) -> dict:
    """Run `action(connection, city, day, timestamp)` if given, then Talk of the town as it now stands."""
    database = request.app.state.database
    now = database.clock.now()
    with database.connect(write=action is not None) as connection:
        companion = require_current(connection)
        data = network.city(connection, companion)
        if action:
            require(bool(data.get('neighborhoods')), 'Pick a home city for the companion first.', 404)
            action(connection, data, storylines.local_today(companion, now), database.now())
        return town_politics.today_view(connection, companion, data, now)


@router.get('')
def read_politics(request: Request):
    return respond(request)


@router.post('/issues')
def add_issue(request: Request, body: IssueNew):
    return respond(request, lambda connection, data, day, timestamp: town_politics.add_issue(
        connection, data, body.model_dump(), day, timestamp))


@router.patch('/issues/{issue_id}')
def change_issue(request: Request, issue_id: str, body: IssueChange):
    changes = body.model_dump(exclude_unset=True)
    return respond(request, lambda connection, data, day, timestamp: town_politics.change_issue(
        connection, data, issue_id, changes, day, timestamp))


@router.delete('/issues/{issue_id}')
def remove_issue(request: Request, issue_id: str):
    return respond(request, lambda connection, data, day, timestamp: town_politics.remove_issue(
        connection, data, issue_id, day, timestamp))


@router.put('/views')
def change_view(request: Request, body: ViewChange):
    return respond(request, lambda connection, data, day, timestamp: town_politics.set_view(
        connection, data['id'], body.issue, body.person, body.view, timestamp))


@router.post('/factions')
def add_faction(request: Request, body: FactionNew):
    return respond(request, lambda connection, data, day, timestamp: town_politics.add_faction(
        connection, data, body.model_dump(), timestamp))


@router.patch('/factions/{faction_id}')
def change_faction(request: Request, faction_id: str, body: FactionChange):
    changes = body.model_dump(exclude_unset=True)
    return respond(request, lambda connection, data, day, timestamp: town_politics.change_faction(
        connection, data, faction_id, changes, timestamp))


@router.delete('/factions/{faction_id}')
def remove_faction(request: Request, faction_id: str):
    return respond(request, lambda connection, data, day, timestamp: town_politics.remove_faction(
        connection, data, faction_id, timestamp))


@router.put('/relations')
def change_relation(request: Request, body: RelationChange):
    return respond(request, lambda connection, data, day, timestamp: town_politics.set_relation(
        connection, data['id'], body.a, body.b, body.stance, timestamp))
