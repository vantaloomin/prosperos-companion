"""FastAPI application. Middleware and error handlers follow prosperos-study server/main.py at bbcbde4."""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from companion.conversation import Conversation, recover
from companion.database import Database
from companion.errors import DomainError
from companion.identity import APP_NAME, CLIENT_HEADER, VERSION
from companion.images import jobs as image_jobs
from companion.images import routes as image_routes
from companion.images.runner import ImageRunner
from companion.life import routes as life_routes
from companion.life.simulation import LifeEngine
from companion.lora import routes as lora_routes
from companion.mcp import routes as context_routes
from companion.mcp import weather as observed_weather
from companion.mcp.lookups import Lookups
from companion.memory.worker import MemoryWorker
from companion.providers.vault import SystemVault
from companion.routes import router
from companion.world import routes as world_routes
from companion.world.source import CatalogWorld

# The built interface (`npm run build`), served beside the API as prosperos-study server/main.py does.
FRONTEND = Path(__file__).parent.parent / 'dist'


async def guard_writes(request: Request, call_next):
    if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'} and request.headers.get(CLIENT_HEADER) != 'workspace':
        return JSONResponse({'detail': 'Use the local Companion app to make changes.'}, status_code=403)
    return await call_next(request)


async def domain_error(_request: Request, error: DomainError):
    return JSONResponse({'detail': error.message, 'code': error.code}, status_code=error.status)


async def invalid_request(_request: Request, error: RequestValidationError):
    details = [{'loc': issue['loc'], 'msg': issue['msg'], 'type': issue['type']} for issue in error.errors()]
    return JSONResponse({'detail': details}, status_code=422)


@asynccontextmanager
async def lifespan(app):
    recover(app.state.database)
    image_jobs.recover(app.state.database)
    tasks = [asyncio.create_task(app.state.life.run_forever()),
             asyncio.create_task(app.state.images.run_forever())] if app.state.life_tasks else []
    app.state.memory.kick()
    yield
    for task in tasks:
        task.cancel()


def create_app(database_path: str | Path | None = None, *, clock=None, vault=None, provider=None,
               life_tasks=True, world=None, embedder=None, image_adapters=None,
               context_transports=None) -> FastAPI:
    app = FastAPI(title=APP_NAME, version=VERSION, lifespan=lifespan)
    app.state.database = Database(database_path, clock)
    app.state.vault = vault or SystemVault()
    world = observed_weather.ObservedWorld(world or CatalogWorld(app.state.database), app.state.database)
    app.state.lookups = Lookups(app.state.database, app.state.vault, world, context_transports)
    app.state.lookups.listeners.append(lambda observation: observed_weather.apply(app.state.database, observation))
    app.state.conversation = Conversation(app.state.database, app.state.vault, provider, embedder=embedder,
                                          lookups=app.state.lookups)
    app.state.memory = MemoryWorker(app.state.database, app.state.conversation.scheduler, app.state.vault,
                                    app.state.conversation.embedder, enabled=life_tasks,
                                    provider=app.state.conversation.provider)
    app.state.conversation.after_turn = app.state.memory.kick
    app.state.life = LifeEngine(app.state.database, app.state.vault, app.state.conversation.provider,
                                app.state.conversation.scheduler, world)
    app.state.life.lookups = app.state.lookups
    app.state.images = ImageRunner(app.state.database, app.state.vault, image_adapters,
                                   app.state.conversation.scheduler)
    app.state.life_tasks = life_tasks
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['localhost', '127.0.0.1', 'testserver'])
    app.middleware('http')(guard_writes)
    app.add_exception_handler(DomainError, domain_error)
    app.add_exception_handler(RequestValidationError, invalid_request)
    app.include_router(router)
    app.include_router(life_routes.router)
    app.include_router(life_routes.today_router)
    app.include_router(life_routes.feed_router)
    app.include_router(world_routes.router)
    app.include_router(image_routes.router)
    app.include_router(context_routes.router)
    app.include_router(lora_routes.router)
    if FRONTEND.exists():
        app.mount('/', StaticFiles(directory=FRONTEND, html=True), name='frontend')
    return app
