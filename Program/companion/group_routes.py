"""Group chats and secrets API (companion/groups.py, companion/secrets.py, docs/group-chat.md)."""
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import Field

from companion import groups, secrets
from companion.memory import pairs
from companion.models import Input

router = APIRouter(prefix='/api/groups')


class Backstory(Input):
    """How two companions know each other, told once when they first share a group: a starting stage, a line."""
    a: str = Field(min_length=1, max_length=100)
    b: str = Field(min_length=1, max_length=100)
    level: int | None = Field(None, ge=1, le=pairs.STAGES)
    how: str = Field('', max_length=pairs.HOW_LIMIT)


class NewGroup(Input):
    companion_ids: list[str] = Field(min_length=2, max_length=50)
    name: str | None = Field(None, max_length=200)
    ties: list[Backstory] = Field(default_factory=list, max_length=200)


class Untold(Input):
    companion_ids: list[str] = Field(min_length=2, max_length=50)


class Moment(Input):
    kept: bool = True


class GroupChange(Input):
    name: str | None = Field(None, max_length=200)
    reply_cap: int | None = Field(None, ge=1, le=groups.MAX_CAP)


class NewMember(Input):
    companion_id: str = Field(min_length=1, max_length=100)
    # What they can see: the chat from when they join (the default), or all of it so far.
    history: Literal['from_now', 'everything'] = 'from_now'
    ties: list[Backstory] = Field(default_factory=list, max_length=50)


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
    return groups.create(request.app.state.database, body.companion_ids, body.name, body.ties)


@router.post('/untold')
def untold(request: Request, body: Untold):
    """Pairs among these companions who would meet in a group for the first time: their backstory can be told."""
    return {'pairs': groups.untold(request.app.state.database, body.companion_ids)}


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
    return groups.add(request.app.state.database, group_id, body.companion_id, body.history == 'everything',
                      body.ties)


@router.delete('/{group_id}/members/{companion_id}')
def remove(request: Request, group_id: str, companion_id: str):
    return groups.remove(request.app.state.database, group_id, companion_id)


@router.post('/{group_id}/copy')
def copy(request: Request, group_id: str):
    return groups.copy(request.app.state.database, group_id)


@router.post('/{group_id}/messages/{message_id}/moment')
def keep_moment(request: Request, group_id: str, message_id: str, body: Moment):
    return groups.keep_moment(request.app.state.database, group_id, message_id, body.kept)


@router.post('/{group_id}/messages')
async def send(request: Request, group_id: str, body: GroupMessage, wait: bool = True):
    return await chats(request).send(group_id, body.text, body.client_id, wait)


@router.post('/{group_id}/retry')
async def retry(request: Request, group_id: str, wait: bool = True):
    return await chats(request).retry(group_id, wait)


@router.post('/{group_id}/stop')
def stop(request: Request, group_id: str):
    return {'stopped': chats(request).stop(group_id)}


# Secrets (companion/secrets.py): who knows what, and who must not find out.

secrets_router = APIRouter(prefix='/api/secrets')


class NewSecret(Input):
    statement: str = Field(min_length=1, max_length=secrets.STATEMENT_LIMIT)
    # Who it's about, by name: a companion's name links to them; anyone else stays as typed.
    about: list[str] = Field(default_factory=list, max_length=10)
    knows: list[str] = Field(min_length=1, max_length=50)
    kept_from: list[str] = Field(default_factory=list, max_length=50)
    keep_from_everyone: bool = False
    key_words: list[str] = Field(default_factory=list, max_length=30)


class SecretChange(Input):
    statement: str | None = Field(None, min_length=1, max_length=secrets.STATEMENT_LIMIT)
    about: list[str] | None = Field(None, max_length=10)
    knows: list[str] | None = Field(None, max_length=50)
    kept_from: list[str] | None = Field(None, max_length=50)
    keep_from_everyone: bool | None = None
    key_words: list[str] | None = Field(None, max_length=30)


class Person(Input):
    companion_id: str = Field(min_length=1, max_length=100)


@secrets_router.get('')
def secret_listing(request: Request):
    return secrets.listing(request.app.state.database)


@secrets_router.post('')
def secret_create(request: Request, body: NewSecret):
    return secrets.create(request.app.state.database, body)


@secrets_router.patch('/{secret_id}')
def secret_change(request: Request, secret_id: str, body: SecretChange):
    return secrets.update(request.app.state.database, secret_id, body)


@secrets_router.delete('/{secret_id}')
def secret_end(request: Request, secret_id: str):
    return secrets.end(request.app.state.database, secret_id)


@secrets_router.post('/{secret_id}/reveal')
def secret_reveal(request: Request, secret_id: str, body: Person):
    return secrets.reveal(request.app.state.database, secret_id, body.companion_id)


@secrets_router.post('/{secret_id}/forget')
def secret_forget(request: Request, secret_id: str, body: Person):
    return secrets.forget(request.app.state.database, secret_id, body.companion_id)
