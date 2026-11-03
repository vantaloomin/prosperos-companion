"""Worlds and personas (companion/worlds.py): /api/worlds."""
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from companion import back_when, persona_pictures, worlds
from companion.models import (
    BackWhen,
    Become,
    HomeChange,
    NewPersona,
    NewWorld,
    PersonaCopy,
    PersonaInput,
    PictureMake,
    WorldChange,
)

router = APIRouter(prefix='/api/worlds')


def db(request: Request):
    return request.app.state.database


@router.get('')
def listing(request: Request):
    """Every persona with their worlds, and which world the user is in."""
    return worlds.view(db(request))


@router.post('')
def create_world(request: Request, body: NewWorld):
    """A new world, ready at once, where the user makes its first companion. It does not switch to it."""
    return worlds.create_world(db(request), body.persona_id, body.name, body.city_id, watch=body.watch,
                               year=body.year)


@router.post('/become')
async def become(request: Request, body: Become):
    """Start a new life as a townsperson the user or their companion has met: a new world in the same town with
    them as the persona, and switch to it. Runs on the event loop, like a switch."""
    return worlds.become(request.app.state, body.key)


@router.get('/back-when')
def back_when_moments(request: Request, companion_id: str | None = None):
    """The Back when sheet: three moments the app picked, and the years the user can pick instead."""
    return back_when.moments(db(request), companion_id)


@router.post('/back-when')
async def back_when_world(request: Request, body: BackWhen):
    """Go back to that year with the companion: a new world in it, and switch to it. Runs on the event loop, like a
    switch."""
    return back_when.build(request.app.state, body.year, body.from_history, body.companion_id)


@router.patch('/{world_id}')
def change_world(request: Request, world_id: str, body: WorldChange):
    return worlds.update_world(db(request), world_id, body)


@router.get('/{world_id}/home')
def home(request: Request, world_id: str, city_id: str | None = None):
    """Where the persona lives in this world, the cities they can live in and the neighbourhoods of `city_id`."""
    return worlds.home_choices(db(request), world_id, city_id)


@router.put('/{world_id}/home')
def change_home(request: Request, world_id: str, body: HomeChange):
    return worlds.change_home(db(request), world_id, body)


@router.delete('/{world_id}')
def delete_world(request: Request, world_id: str):
    """The world and everything in it, after a backup kept in Settings > Backups."""
    return worlds.delete_world(db(request), world_id)


@router.post('/{world_id}/switch')
async def switch_world(request: Request, world_id: str):
    """Runs on the event loop, so nothing else the app does starts halfway through the switch."""
    return worlds.switch(request.app.state, world_id)


@router.post('/{world_id}/pause')
def pause_world(request: Request, world_id: str):
    """Pause any world, the one the user is in or one they left: it skips that time until resumed."""
    return worlds.set_paused(db(request), world_id, True)


@router.post('/{world_id}/resume')
def resume_world(request: Request, world_id: str):
    return worlds.set_paused(db(request), world_id, False)


@router.post('/personas')
def create_persona(request: Request, body: NewPersona):
    """A new persona with a world of their own, in the city they picked. It does not switch to them."""
    return worlds.create_persona(db(request), body)


@router.post('/personas/{persona_id}/copy')
def copy_persona(request: Request, persona_id: str, body: PersonaCopy):
    """A separate copy of the persona with a world of their own, in the city picked. It does not switch to them."""
    return worlds.copy_persona(db(request), persona_id, body.city_id)


@router.patch('/personas/{persona_id}')
def change_persona(request: Request, persona_id: str, body: PersonaInput):
    return worlds.update_persona(db(request), persona_id, body)


@router.delete('/personas/{persona_id}')
def delete_persona(request: Request, persona_id: str):
    return worlds.delete_persona(db(request), persona_id)


@router.post('/personas/{persona_id}/switch')
async def switch_persona(request: Request, persona_id: str):
    """Into the world the persona was last in."""
    return worlds.switch_persona(request.app.state, persona_id)


@router.post('/personas/{persona_id}/picture')
async def upload_picture(request: Request, persona_id: str):
    """The body is the user's own picture of this persona (companion/persona_pictures.py)."""
    return persona_pictures.upload(db(request), persona_id, await request.body())


@router.delete('/personas/{persona_id}/picture')
def remove_picture(request: Request, persona_id: str):
    return persona_pictures.remove(db(request), persona_id)


@router.get('/personas/{persona_id}/picture')
def picture(request: Request, persona_id: str):
    path = persona_pictures.file(db(request), persona_id)
    return FileResponse(path, media_type=persona_pictures.TYPES[path.suffix.lstrip('.')])


@router.post('/personas/{persona_id}/picture/make')
def make_picture(request: Request, persona_id: str, body: PictureMake):
    """Make one from How you look (`looks`, as typed, is saved first), with this world's image backends."""
    return request.app.state.persona_pictures.request(persona_id, body.looks)


@router.get('/personas/{persona_id}/picture/make')
def making(request: Request, persona_id: str):
    return request.app.state.persona_pictures.status(persona_id)
