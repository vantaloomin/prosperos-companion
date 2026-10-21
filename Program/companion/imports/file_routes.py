"""Bring your characters (companion/imports/characters.py), the lore it brings (companion/lore.py) and old chats
(companion/imports/chats.py)."""
from fastapi import APIRouter, Request

from companion import lore
from companion.imports import characters, chats
from companion.models import CharacterCardFile, ChatFile, LoreSwitch, LoreWhen

router = APIRouter(prefix='/api')


def db(request: Request):
    return request.app.state.database


@router.post('/import/character')
def import_character(request: Request, body: CharacterCardFile):
    """A character card, CHARX, BYAF or lorebook file, imported straight away."""
    return characters.bring(db(request), body.filename, body.data)


@router.post('/import/chat')
def import_chat(request: Request, body: ChatFile):
    """A SillyTavern chat or a role/content transcript, brought in as older history straight away."""
    return chats.bring(db(request), body.filename, body.data, body.companion_id)


@router.get('/lore')
def list_lore(request: Request):
    return lore.listing(db(request))


@router.put('/lore/books/{book_id}')
def switch_book(request: Request, book_id: str, body: LoreSwitch):
    return lore.set_book(db(request), book_id, body.enabled)


@router.delete('/lore/books/{book_id}')
def delete_book(request: Request, book_id: str):
    return lore.remove_book(db(request), book_id)


@router.put('/lore/entries/{entry_id}')
def switch_entry(request: Request, entry_id: str, body: LoreSwitch):
    return lore.set_entry(db(request), entry_id, body.enabled)


@router.put('/lore/entries/{entry_id}/when')
def entry_when(request: Request, entry_id: str, body: LoreWhen):
    return lore.set_when(db(request), entry_id, body.when)
