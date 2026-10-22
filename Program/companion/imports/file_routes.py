"""Bring your characters (companion/imports/characters.py), the lore it brings (companion/lore.py), old chats
(companion/imports/chats.py) and long texts for the reference library (companion/library.py)."""
import base64
import binascii

from fastapi import APIRouter, Request

from companion import library, library_online, lore
from companion.errors import DomainError
from companion.imports import characters, chats
from companion.models import CharacterCardFile, ChatFile, LibraryFile, LoreSwitch, LoreWhen

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


@router.get('/library')
def list_library(request: Request):
    return library.listing(db(request))


@router.post('/library/books')
def add_book(request: Request, body: LibraryFile):
    try:
        source = base64.b64decode(body.data, validate=True)
    except (ValueError, binascii.Error) as error:
        raise DomainError('Choose the file again; it did not arrive whole.', 422) from error
    return library.add(db(request), body.filename, source, body.world)


@router.put('/library/books/{book_id}')
def switch_library_book(request: Request, book_id: str, body: LoreSwitch):
    return library.set_book(db(request), book_id, body.enabled)


@router.delete('/library/books/{book_id}')
def delete_library_book(request: Request, book_id: str):
    return library.remove_book(db(request), book_id)


@router.get('/library/books/{book_id}/passages')
def book_passages(request: Request, book_id: str, q: str = ''):
    return library.browse(db(request), book_id, q[:500])


@router.get('/library/online')
def online_books(request: Request):
    return library_online.offers(db(request))


@router.post('/library/online/{key}')
def download_book(request: Request, key: str):
    """Add the book from its author's site, or get the latest copy (the Neokosmos wiki on Grandport's card)."""
    return library_online.add(db(request), key)
