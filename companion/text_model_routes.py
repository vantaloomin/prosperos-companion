"""Settings > Models: profiles, the connection test and job assignments.

Routes adapted from prosperos-study server/profile_routes.py at bbcbde4.
"""
from fastapi import APIRouter, Request

from companion import text_models
from companion.database import decode
from companion.providers.config import ConnectionProbe, ProfileCreate, ProfileUpdate, RouteUpdate

router = APIRouter(prefix='/api/models')


def db(request: Request):
    return request.app.state.database


@router.get('')
def overview(request: Request):
    with db(request).connect() as connection:
        return text_models.overview(connection)


@router.post('/profiles', status_code=201)
def create_profile(body: ProfileCreate, request: Request):
    return text_models.create(db(request), request.app.state.vault, body)


@router.put('/profiles/{profile_id}')
def update_profile(profile_id: str, body: ProfileUpdate, request: Request):
    return text_models.update(db(request), request.app.state.vault, profile_id, body)


@router.delete('/profiles/{profile_id}')
def delete_profile(profile_id: str, request: Request):
    return text_models.delete(db(request), request.app.state.vault, profile_id)


@router.post('/discover')
async def discover(body: ConnectionProbe, request: Request):
    """Test an unsaved form: list the service's models without generating anything."""
    key = text_models.probe_key(db(request), request.app.state.vault, body)
    return await request.app.state.conversation.provider.check(body.config.model_dump(), key)


@router.post('/profiles/{profile_id}/check')
async def check_profile(profile_id: str, request: Request):
    with db(request).connect() as connection:
        row = text_models.profile_row(connection, profile_id)
    config = {**decode(row['config']), 'credential_ref': row['credential_ref']}
    return await request.app.state.conversation.provider.check(config, text_models.key_for(request.app.state.vault,
                                                                                            config))


@router.put('/routes')
def set_route(body: RouteUpdate, request: Request):
    return text_models.set_route(db(request), body.job, body.profile_id)
