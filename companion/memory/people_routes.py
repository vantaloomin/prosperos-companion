"""The people in the user's life the companion has heard about: see, add, rename and forget (PRD M6, M12)."""
from fastapi import APIRouter, Request
from pydantic import Field

from companion.memory import people
from companion.models import Input

router = APIRouter(prefix='/api/people')


class PersonCreate(Input):
    name: str = Field(default='', max_length=80)
    relation: str = Field(default='', max_length=40)


class PersonUpdate(Input):
    """Only the fields sent change."""
    name: str | None = Field(default=None, max_length=80)
    relation: str | None = Field(default=None, max_length=40)


def db(request: Request):
    return request.app.state.database


@router.get('')
def listing(request: Request):
    return people.listing(db(request))


@router.post('')
def add(request: Request, body: PersonCreate):
    return people.add(db(request), body)


@router.put('/{person_id}')
def update(request: Request, person_id: str, body: PersonUpdate):
    return people.update(db(request), person_id, body)


@router.post('/{person_id}/delete')
def delete(request: Request, person_id: str):
    return people.delete(db(request), person_id)
