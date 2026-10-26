"""Export API: a chat or the story as a file to keep (companion/export.py), and a companion saved to take to another
world (companion/carry.py). Plain GETs, so a link downloads it."""
from typing import Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, Response
from starlette.background import BackgroundTask

from companion import carry, export
from companion.story_routes import switched_on

router = APIRouter(prefix='/api/export')
Format = Literal['html', 'md']


def attachment(transcript: export.Transcript, kind: str) -> Response:
    body, media_type, disposition = export.download(transcript, kind)
    return Response(body, media_type=media_type,
                    headers={'Content-Disposition': disposition, 'Cache-Control': 'no-store'})


@router.get('/chat/{thread_id}')
def export_chat(request: Request, thread_id: str, format: Format = 'html'):
    """A companion's chat (by the timeline on screen) or a group chat (by its id), as on screen."""
    return attachment(export.chat(request.app.state.database, thread_id), format)


@router.get('/story', dependencies=[Depends(switched_on)])
def export_story(request: Request, format: Format = 'html'):
    return attachment(export.story(request.app.state.database), format)


@router.get('/companion/{companion_id}')
def save_companion(request: Request, companion_id: str):
    """A companion with everything that happened, as a file another world can open (companion/carry.py)."""
    path, name = carry.save(request.app.state.database, companion_id)
    return FileResponse(path, media_type='application/zip', filename=name, headers={'Cache-Control': 'no-store'},
                        background=BackgroundTask(path.unlink, missing_ok=True))


@router.post('/companion')
async def open_companion(request: Request):
    """The body is a saved companion's file; they arrive in this world with their history."""
    return await carry.receive(request.app.state.database, request.stream())
