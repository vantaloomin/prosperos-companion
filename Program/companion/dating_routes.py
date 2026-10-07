"""Dating app API (companion/dating.py, docs/dating.md)."""
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from pydantic import Field

from companion import dating
from companion.images import storage
from companion.models import Input

router = APIRouter(prefix='/api/dating')
Gender = Literal['woman', 'man', 'nonbinary']


class DatingProfile(Input):
    name: str = Field('', max_length=80)
    age: int = Field(ge=18, le=120)
    gender: Gender
    interested_in: list[Gender] = Field(min_length=1, max_length=3)
    looking_for: Literal['serious', 'casual', 'friends']
    age_min: int = Field(ge=18, le=120)
    age_max: int = Field(ge=18, le=120)
    bio: str = Field('', max_length=1000)


class DatingCity(Input):
    city_id: str = Field(min_length=1, max_length=80)


class Swipe(Input):
    key: str = Field(min_length=1, max_length=200)
    like: bool


class PhotoRequest(Input):
    key: str = Field(min_length=1, max_length=200)


class DateRequest(Input):
    key: str = Field(min_length=1, max_length=200)
    place_id: str = Field(min_length=1, max_length=80)


@router.get('')
def read(request: Request):
    return dating.state(request.app.state.database)


@router.get('/status')
def status(request: Request):
    return dating.installed(request.app.state.database)


@router.delete('/profile')
def uninstall(request: Request):
    return dating.uninstall(request.app.state.database)


@router.put('/profile')
def save_profile(request: Request, body: DatingProfile):
    return dating.save_profile(request.app.state.database, body.model_dump())


@router.put('/city')
def look_in(request: Request, body: DatingCity):
    return dating.look_in(request.app.state.database, body.city_id)


@router.post('/swipes')
def swipe(request: Request, body: Swipe):
    return dating.swipe(request.app.state.database, body.key, body.like)


@router.delete('/swipes/passed')
def see_passed_again(request: Request):
    return dating.see_passed_again(request.app.state.database)


@router.delete('/matches/{key}')
def unmatch(request: Request, key: str):
    return dating.unmatch(request.app.state.database, key)


@router.post('/dates')
def go_on_date(request: Request, body: DateRequest):
    return dating.go_on_date(request.app.state.database, body.key, body.place_id)


@router.delete('/dates/current')
def end_date(request: Request):
    return dating.end_date(request.app.state.database)


@router.post('/photos')
def request_photo(request: Request, body: PhotoRequest):
    """Their photo: the saved one, or one made now (once) from their looks."""
    return request.app.state.dating_photos.request(body.key)


@router.get('/photos/{key}')
def photo(request: Request, key: str):
    return request.app.state.dating_photos.get(key)


@router.get('/photos/{key}/file')
def photo_file(request: Request, key: str):
    path = request.app.state.dating_photos.file(key)
    return FileResponse(path, media_type=storage.TYPES[path.suffix.lstrip('.')])
