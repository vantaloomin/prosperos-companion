"""Story mode API (companion/story.py, docs/story.md)."""
from fastapi import APIRouter, Request
from pydantic import Field

from companion import story
from companion.models import Input

router = APIRouter(prefix='/api/story')


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


@router.post('/messages')
async def send(request: Request, body: StoryMessage):
    return await story.send(request.app.state, body.text, body.client_id)


@router.post('/retry')
async def retry(request: Request):
    return await story.retry(request.app.state)


@router.delete('')
def clear(request: Request):
    return story.clear(request.app.state.database)
