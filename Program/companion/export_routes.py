"""Export API: a chat or the story as a file to keep (companion/export.py). Plain GETs, so a link downloads it."""
from typing import Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from companion import export
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
