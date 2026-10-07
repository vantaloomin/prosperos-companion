"""Story mode API (companion/story.py, docs/story.md)."""
from fastapi import APIRouter, Depends, Request
from pydantic import Field

from companion import story
from companion.database import settings
from companion.errors import DomainError
from companion.models import Input


def switched_on(request: Request):
    """Story mode is opt-in (Settings > Advanced > Story mode); while it is off the API is not there either."""
    with request.app.state.database.connect() as connection:
        if not settings(connection)['story_mode']:
            raise DomainError('Story mode is off. Turn it on in Settings > Advanced.', 404, 'story_off')


router = APIRouter(prefix='/api/story', dependencies=[Depends(switched_on)])


class StoryMessage(Input):
    text: str = Field(min_length=1, max_length=40000)
    client_id: str = Field(min_length=8, max_length=100)


class StoryScene(Input):
    city_id: str = Field(min_length=1, max_length=80)
    place_id: str | None = Field(None, min_length=1, max_length=80)


@router.get('')
def read(request: Request):
    return story.story(request.app.state.database)


@router.put('/scene')
def move(request: Request, body: StoryScene):
    return story.move(request.app.state.database, body.city_id, body.place_id)


class StoryPerson(Input):
    key: str = Field(min_length=1, max_length=200)


@router.post('/find')
def find(request: Request, body: StoryPerson):
    return story.find(request.app.state.database, body.key)


@router.post('/messages')
async def send(request: Request, body: StoryMessage):
    return await story.send(request.app.state, body.text, body.client_id)


@router.post('/retry')
async def retry(request: Request):
    return await story.retry(request.app.state)


@router.delete('')
def clear(request: Request):
    return story.clear(request.app.state.database)
