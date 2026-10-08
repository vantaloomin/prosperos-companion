"""Closeness stages API: see, set, hold, cap, cooling, nickname, running jokes and reset (PRD M3, M4)."""
from fastapi import APIRouter, Request
from pydantic import Field

from companion.memory import closeness
from companion.models import Input

router = APIRouter(prefix='/api/closeness')


class ClosenessUpdate(Input):
    """Only the fields sent change. set_level puts it at a stage and lets it keep growing; held_level keeps it
    there (null lets it grow again); ceiling_level caps it (null removes the cap); cooling turns gentle cooling
    after long silences on or off."""
    held_level: int | None = Field(default=None, ge=1, le=len(closeness.THRESHOLDS))
    set_level: int | None = Field(default=None, ge=1, le=len(closeness.THRESHOLDS))
    ceiling_level: int | None = Field(default=None, ge=1, le=len(closeness.THRESHOLDS))
    cooling: bool | None = None
    nickname: str | None = Field(default=None, max_length=closeness.NICKNAME_LIMIT)


class JokeChoice(Input):
    memory_id: str = Field(min_length=1, max_length=64)


def db(request: Request):
    return request.app.state.database


@router.get('')
def view(request: Request):
    return closeness.view(db(request))


@router.put('')
def update(request: Request, body: ClosenessUpdate):
    return closeness.update(db(request), body)


@router.post('/reset')
def reset(request: Request):
    return closeness.reset(db(request))


@router.post('/jokes')
def add_joke(request: Request, body: JokeChoice):
    return closeness.add_joke(db(request), body.memory_id)


@router.post('/jokes/{memory_id}/remove')
def remove_joke(request: Request, memory_id: str):
    return closeness.remove_joke(db(request), memory_id)
