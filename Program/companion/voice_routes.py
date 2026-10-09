"""Settings > Models > Voice notes, and the voice notes themselves (companion/voice/)."""
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, Response
from pydantic import Field

from companion.characters import by_id
from companion.database import many
from companion.errors import DomainError, require
from companion.models import Input
from companion.voice import hosted, notes, voices

router = APIRouter(prefix='/api/voice')
Engine = Literal['builtin', 'openai', 'elevenlabs', 'google']


class VoiceUpdate(Input):
    voice_notes: bool | None = None
    engine: Engine | None = None
    daily_limit: int | None = Field(default=None, ge=1, le=20)


class VoiceKey(Input):
    engine: Literal['openai', 'elevenlabs', 'google']
    # Empty removes the saved key.
    api_key: str = Field(default='', max_length=500)


class CompanionVoice(Input):
    engine: Engine
    # Empty goes back to the voice the app picks.
    voice: str = Field(default='', max_length=200)


class Preview(Input):
    companion_id: str
    engine: Engine | None = None
    voice: str = Field(default='', max_length=200)


def overview(request: Request) -> dict:
    service = request.app.state.voice
    with request.app.state.database.connect() as connection:
        current = notes.read(connection)
    keys = {engine: service.key(engine)[1] for engine in notes.HOSTED}
    return {**current, 'keys': keys, 'builtin': service.kokoro.status(),
            'ready': service.can_speak(current['engine'])}


@router.get('')
def show(request: Request):
    return overview(request)


@router.put('')
def change(body: VoiceUpdate, request: Request):
    database = request.app.state.database
    values = body.model_dump(exclude_none=True)
    with database.connect(write=True) as connection:
        for column, value in values.items():
            connection.execute(f'UPDATE voice_settings SET {column}=?, updated_at=? WHERE id=1',  # noqa: S608
                               (int(value) if isinstance(value, bool) else value, database.now()))
    return overview(request)


@router.put('/key')
def save_key(body: VoiceKey, request: Request):
    vault = request.app.state.vault
    if body.api_key:
        vault.put(notes.key_ref(body.engine), body.api_key)
    else:
        vault.delete(notes.key_ref(body.engine))
    return overview(request)


@router.post('/builtin/download')
async def download(request: Request):
    await request.app.state.voice.kokoro.install()
    return overview(request)


@router.get('/companions')
async def companion_voices(request: Request, engine: Engine | None = None):
    """Each companion's voice on an engine (the current one by default) and the voices to choose from."""
    service = request.app.state.voice
    with request.app.state.database.connect() as connection:
        engine = engine or notes.read(connection)['engine']
        companions = [by_id(connection, row['id']) for row in many(
            connection, 'SELECT id FROM companions ORDER BY slot IS NULL, slot, created_at')]
    if not service.can_speak(engine) and engine != 'builtin':
        return {'engine': engine, 'voices': [], 'companions': [], 'message': f'Add a {hosted.ENGINE_NAMES[engine]} key first.'}
    try:
        options = await service.catalog(engine)
        found = [(companion, *(await service.voice_for(companion, engine))) for companion in companions if companion]
    except DomainError as error:
        return {'engine': engine, 'voices': [], 'companions': [], 'message': error.message}
    return {'engine': engine, 'voices': options, 'message': '', 'companions': [
        {'id': companion['id'], 'name': companion['version']['name'], 'voice': voice, 'chosen_by': who}
        for companion, voice, who in found]}


@router.put('/companions/{companion_id}')
def choose(companion_id: str, body: CompanionVoice, request: Request):
    database = request.app.state.database
    with database.connect(write=True) as connection:
        require(by_id(connection, companion_id) is not None, 'That companion was not found.', 404)
        if body.voice:
            connection.execute('INSERT INTO companion_voices (companion_id, engine, voice, updated_at) VALUES (?, ?, ?, ?) '
                               'ON CONFLICT (companion_id, engine) DO UPDATE SET voice=excluded.voice, '
                               'updated_at=excluded.updated_at', (companion_id, body.engine, body.voice, database.now()))
        else:
            connection.execute('DELETE FROM companion_voices WHERE companion_id=? AND engine=?', (companion_id, body.engine))
        return {'companion_id': companion_id, 'engine': body.engine,
                'voice': voices.chosen(connection, companion_id, body.engine)}


@router.post('/preview')
async def preview(body: Preview, request: Request):
    data, media_type = await request.app.state.voice.preview(body.companion_id, body.voice or None, body.engine)
    return Response(data, media_type=media_type, headers={'Cache-Control': 'no-store'})


@router.get('/notes/{message_id}')
def note(message_id: str, request: Request):
    path, media_type = request.app.state.voice.file(message_id)
    return FileResponse(path, media_type=media_type, headers={'Cache-Control': 'private, max-age=31536000'})
