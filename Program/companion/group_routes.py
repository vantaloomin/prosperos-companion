"""Group chats API (companion/groups.py, docs/group-chat.md)."""
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import Field

from companion import groups
from companion.models import Input

router = APIRouter(prefix='/api/groups')


class NewGroup(Input):
    companion_ids: list[str] = Field(min_length=2, max_length=50)
    name: str | None = Field(None, max_length=200)


class GroupChange(Input):
    name: str | None = Field(None, max_length=200)
    reply_cap: int | None = Field(None, ge=1, le=groups.MAX_CAP)


class NewMember(Input):
    companion_id: str = Field(min_length=1, max_length=100)
    # What they can see: the chat from when they join (the default), or all of it so far.
    history: Literal['from_now', 'everything'] = 'from_now'


class GroupMessage(Input):
    text: str = Field(min_length=1, max_length=40000)
    client_id: str = Field(min_length=8, max_length=100)


def chats(request: Request) -> groups.GroupChats:
    return request.app.state.groups


@router.get('')
def listing(request: Request):
    return {'groups': groups.listing(request.app.state.database)}


@router.post('')
def create(request: Request, body: NewGroup):
    return groups.create(request.app.state.database, body.companion_ids, body.name)


@router.get('/{group_id}')
def read(request: Request, group_id: str, after_seq: int = 0):
    return chats(request).view(group_id, after_seq)


@router.patch('/{group_id}')
def change(request: Request, group_id: str, body: GroupChange):
    return groups.update(request.app.state.database, group_id, body.name, body.reply_cap)


@router.delete('/{group_id}')
def delete(request: Request, group_id: str):
    chats(request).stop(group_id)
    return groups.delete(request.app.state.database, group_id)


@router.post('/{group_id}/members')
def add(request: Request, group_id: str, body: NewMember):
    return groups.add(request.app.state.database, group_id, body.companion_id, body.history == 'everything')


@router.delete('/{group_id}/members/{companion_id}')
def remove(request: Request, group_id: str, companion_id: str):
    return groups.remove(request.app.state.database, group_id, companion_id)


@router.post('/{group_id}/copy')
def copy(request: Request, group_id: str):
    return groups.copy(request.app.state.database, group_id)


@router.post('/{group_id}/messages')
async def send(request: Request, group_id: str, body: GroupMessage, wait: bool = True):
    return await chats(request).send(group_id, body.text, body.client_id, wait)


@router.post('/{group_id}/retry')
async def retry(request: Request, group_id: str, wait: bool = True):
    return await chats(request).retry(group_id, wait)


@router.post('/{group_id}/stop')
def stop(request: Request, group_id: str):
    return {'stopped': chats(request).stop(group_id)}
