"""FastAPI application. Middleware and error handlers follow prosperos-study server/main.py at bbcbde4."""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from companion.conversation import Conversation, recover
from companion.database import Database
from companion.errors import DomainError
from companion.identity import APP_NAME, CLIENT_HEADER, VERSION
from companion.life import routes as life_routes
from companion.life.simulation import LifeEngine
from companion.providers.vault import SystemVault
from companion.routes import router


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
    task = asyncio.create_task(app.state.life.run_forever()) if app.state.life_tasks else None
    yield
    if task:
        task.cancel()


def create_app(database_path: str | Path | None = None, *, clock=None, vault=None, provider=None,
               life_tasks=True) -> FastAPI:
    app = FastAPI(title=APP_NAME, version=VERSION, lifespan=lifespan)
    app.state.database = Database(database_path, clock)
    app.state.vault = vault or SystemVault()
    app.state.conversation = Conversation(app.state.database, app.state.vault, provider)
    app.state.life = LifeEngine(app.state.database, app.state.vault, app.state.conversation.provider,
                                app.state.conversation.scheduler)
    app.state.life_tasks = life_tasks
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['localhost', '127.0.0.1', 'testserver'])
    app.middleware('http')(guard_writes)
    app.add_exception_handler(DomainError, domain_error)
    app.add_exception_handler(RequestValidationError, invalid_request)
    app.include_router(router)
    app.include_router(life_routes.router)
    return app
