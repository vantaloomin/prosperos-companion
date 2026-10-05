"""Current-context services, the user's location, mappings and lookup records (PRD X1-X3)."""
from fastapi import APIRouter, Request

from companion.mcp import lookups, services
from companion.mcp.lookups import BACKGROUND_DEADLINE
from companion.models import ContextLocation, ContextLookup, ContextService, ToolApproval, ToolMapping

router = APIRouter(prefix='/api/context')


def db(request: Request):
    return request.app.state.database


@router.get('')
def overview(request: Request):
    return services.overview(db(request))


@router.put('/location')
def update_location(request: Request, body: ContextLocation):
    return services.update_location(db(request), body)


@router.post('/services')
def create_service(request: Request, body: ContextService):
    return services.create_service(db(request), request.app.state.vault, body)


@router.put('/services/{service_id}')
def update_service(request: Request, service_id: str, body: ContextService):
    return services.update_service(db(request), request.app.state.vault, service_id, body)


@router.delete('/services/{service_id}')
def delete_service(request: Request, service_id: str):
    return services.delete_service(db(request), service_id)


@router.post('/services/{service_id}/check')
async def check_service(request: Request, service_id: str):
    """Connect and list the server's tools. Nothing is enabled or looked up."""
    factory = request.app.state.lookups.transport_factory
    with db(request).connect() as connection:
        row = services.service_row(connection, service_id)
    return await services.check_service(db(request), request.app.state.vault, service_id,
                                        factory(row) if row else None)


@router.put('/services/{service_id}/tools/{category}')
def save_mapping(request: Request, service_id: str, category: str, body: ToolMapping):
    return services.save_mapping(db(request), service_id, category, body)


@router.delete('/services/{service_id}/tools/{category}')
def remove_mapping(request: Request, service_id: str, category: str):
    return services.remove_mapping(db(request), service_id, category)


@router.post('/services/{service_id}/tools/{category}/enable')
def enable_mapping(request: Request, service_id: str, category: str, body: ToolApproval):
    return services.enable_mapping(db(request), service_id, category, body.digest)


@router.post('/services/{service_id}/tools/{category}/disable')
def disable_mapping(request: Request, service_id: str, category: str):
    return services.disable_mapping(db(request), service_id, category)


@router.post('/lookup')
async def lookup(request: Request, body: ContextLookup):
    """Try an enabled lookup now, under the same limits as any other."""
    found = await request.app.state.lookups.run(body.category, body.purpose, body.topic or None, BACKGROUND_DEADLINE)
    return {'observations': found}


@router.get('/observations')
def observations(request: Request, limit: int = 100):
    return lookups.listing(db(request), min(max(limit, 1), 500))


@router.get('/messages/{message_id}/observations')
def message_observations(request: Request, message_id: str):
    return lookups.for_reply(db(request), message_id)


@router.delete('/observations/{observation_id}')
def delete_observation(request: Request, observation_id: str):
    return lookups.delete(db(request), observation_id)


@router.post('/observations/clear')
def clear_observations(request: Request):
    return lookups.clear(db(request))
