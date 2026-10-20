"""FastAPI application. Middleware and error handlers follow prosperos-study server/main.py at bbcbde4."""
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from companion import (
    authors_note_routes,
    auto_backup,
    dating_routes,
    export_routes,
    group_routes,
    groups,
    local_zone,
    logs,
    story_routes,
    troubleshoot,
    workspace,
    worlds,
    worlds_routes,
)
from companion.conversation import Conversation, recover
from companion.database import Database
from companion.dating_photos import DatingPhotos
from companion.debug_routes import calls_router, matches_router, mix_router
from companion.debug_routes import router as debug_router
from companion.debug_time import DebugTime
from companion.errors import DomainError
from companion.hardware import Hardware
from companion.hardware_routes import router as hardware_router
from companion.identity import APP_NAME, CLIENT_HEADER, VERSION, WORLD_HEADER
from companion.images import jobs as image_jobs
from companion.images import routes as image_routes
from companion.images.photos import ChatPhotos
from companion.images.runner import ImageRunner
from companion.imports import file_routes
from companion.imports import routes as import_routes
from companion.launcher import Launcher
from companion.launcher_routes import router as launcher_router
from companion.life import (
    admin_routes,
    grooming_routes,
    hobbies_routes,
    home_routes,
    kitchen_routes,
    media_routes,
    outings,
    pets_routes,
    scrapbook_routes,
    status,
    steps_routes,
    traditions_routes,
    trips,
    upkeep_routes,
    wardrobe_routes,
    work_routes,
)
from companion.life import routes as life_routes
from companion.life.openers import Openers
from companion.life.simulation import LifeEngine
from companion.lora import evaluation as lora_evaluation
from companion.lora import generation as lora_generation
from companion.lora import maker_enabled as lora_maker_enabled
from companion.lora import routes as lora_routes
from companion.lora import training as lora_training
from companion.mcp import routes as context_routes
from companion.mcp import weather as observed_weather
from companion.mcp.lookups import Lookups
from companion.memory import closeness_routes, history_routes, people_routes
from companion.memory.worker import MemoryWorker
from companion.phone import access as phone_access
from companion.phone import lan as phone_lan
from companion.phone import push as phone_push
from companion.phone import routes as phone_routes
from companion.providers.builtin_chat import BuiltinChat
from companion.providers.builtin_recall import BuiltinRecall
from companion.providers.vault import SystemVault
from companion.ready import Ready, uses_builtin
from companion.ready_routes import router as ready_router
from companion.recall_routes import router as recall_router
from companion.routes import router
from companion.text_model_routes import router as model_router
from companion.voice.notes import VoiceNotes
from companion.voice_routes import router as voice_router
from companion.world import changes as city_changes
from companion.world import routes as world_routes
from companion.world.source import CatalogWorld

# The built interface (`npm run build`), served beside the API as prosperos-study server/main.py does.
FRONTEND = Path(__file__).parent.parent / 'dist'


async def guard_writes(request: Request, call_next):
    if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'} and request.headers.get(CLIENT_HEADER) != 'workspace':
        return JSONResponse({'detail': 'Use the local Companion app to make changes.'}, status_code=403)
    return await call_next(request)


async def stay_in_world(request: Request, call_next):
    """A request, and everything it starts, reads and writes the world open when it arrived
    (companion/database.py PINNED). A page opened in another world (a phone, when the PC switched) is told
    so instead of changing this one; it reloads into the world now open (src/api.ts)."""
    database = request.app.state.database
    opened = request.headers.get(WORLD_HEADER)
    if opened and database.world and opened != database.world:
        return JSONResponse({'detail': 'You moved to another world on another screen. Opening it here too.',
                             'code': 'world_changed'}, status_code=409)
    with database.pin():
        return await call_next(request)


async def domain_error(_request: Request, error: DomainError):
    return JSONResponse({'detail': error.message, 'code': error.code}, status_code=error.status)


async def unexpected_error(request: Request, error: Exception):
    """Anything else: the traceback goes to the log (companion/logs.py) and the page gets a message it can show,
    rather than a bare "Internal Server Error": what failed, the likely reason when it can be told, and a
    one-line detail for a bug report (companion/troubleshoot.py)."""
    logging.getLogger('companion').error('%s %s failed', request.method, request.url.path)
    log = logs.file_path()
    return JSONResponse({'detail': troubleshoot.for_request(request.method, request.url.path, error, str(log)),
                         'code': 'server_error', 'log': str(log)}, status_code=500)


async def invalid_request(_request: Request, error: RequestValidationError):
    details = [{'loc': issue['loc'], 'msg': issue['msg'], 'type': issue['type']} for issue in error.errors()]
    return JSONResponse({'detail': details}, status_code=422)


async def start_lan(app):
    """Home Wi-Fi access stays on across restarts (companion/phone/lan.py); a busy port is logged, not fatal."""
    with app.state.database.connect() as connection:
        wanted = phone_access.phone_settings(connection)['lan_enabled']
    if wanted and app.state.life_tasks:
        try:
            await app.state.lan.start(phone_lan.port())
        except DomainError as error:
            logging.getLogger('companion').warning('%s', error.message)


@asynccontextmanager
async def lifespan(app):
    recover(app.state.database)
    status.lyrics_template(app.state.database.root)
    groups.recover(app.state.database)
    image_jobs.recover(app.state.database)
    lora_training.recover(app.state.database)
    lora_evaluation.recover(app.state.database)
    lora_generation.recover(app.state.database)
    app.state.dating_photos.recover()
    tasks = [asyncio.create_task(app.state.life.run_forever()),
             asyncio.create_task(app.state.images.run_forever()),
             asyncio.create_task(app.state.push.run_forever()),
             asyncio.create_task(auto_backup.run_forever(app.state))] if app.state.life_tasks else []
    if app.state.life_tasks:
        # Built-in recall loads its model now, so the first reply does not wait for it; so does the built-in chat
        # model while it does the chat job, and a confirmed download carries on.
        app.state.builtin_recall.kick()
        app.state.ready.recover()
        if uses_builtin(app.state.database):
            app.state.builtin_chat.kick()
        # The built-in voice is a big download, so it waits for the press in Settings > Models (docs/voice-notes.md).
        # Local programs the user asked to start with the Companion (off until turned on).
        tasks.append(asyncio.create_task(app.state.launcher.launch_all()))
    app.state.memory.kick()
    await start_lan(app)
    yield
    await app.state.lan.stop()
    app.state.builtin_recall.shutdown()
    app.state.builtin_chat.shutdown()
    app.state.training.shutdown()
    for task in tasks:
        task.cancel()


def create_app(database_path: str | Path | None = None, *, clock=None, vault=None, provider=None,
               life_tasks=True, world=None, embedder=None, image_adapters=None,
               context_transports=None, trainer_spawn=None, link_reader=None, push_transport=None,
               lora_maker=None, builtin_spawn=None, builtin_transport=None, hardware=None, voice_transport=None,
               voice_runner=None, launcher=None) -> FastAPI:
    app = FastAPI(title=APP_NAME, version=VERSION, lifespan=lifespan)
    app.state.database = Database(database_path, clock)
    worlds.start(app.state.database)  # The world the user was last in; the first run makes the first world.
    workspace.adopt_pc_timezone(app.state.database, local_zone.detect())
    app.state.vault = vault or SystemVault()
    world = observed_weather.ObservedWorld(world or CatalogWorld(app.state.database), app.state.database)
    app.state.lookups = Lookups(app.state.database, app.state.vault, world, context_transports, link_reader)
    app.state.lookups.listeners.append(lambda observation: observed_weather.apply(app.state.database, observation))
    app.state.lookups.listeners.append(lambda observation: city_changes.remember(app.state.database, observation))
    app.state.conversation = Conversation(app.state.database, app.state.vault, provider, embedder=embedder,
                                          lookups=app.state.lookups)
    app.state.builtin_recall = BuiltinRecall(app.state.database, builtin_spawn, builtin_transport)
    app.state.launcher = launcher or Launcher(app.state.database)
    app.state.conversation.embedder.builtin = app.state.builtin_recall
    app.state.hardware = hardware or Hardware()
    app.state.builtin_chat = BuiltinChat(app.state.database, builtin_spawn, builtin_transport)
    app.state.conversation.provider.inner.builtin_chat = app.state.builtin_chat
    app.state.ready = Ready(app.state.database, app.state.builtin_chat,
                            lambda: app.state.hardware.report(app.state.database), builtin_transport)
    app.state.ready.state_of_app = app.state
    app.state.memory = MemoryWorker(app.state.database, app.state.conversation.scheduler, app.state.vault,
                                    app.state.conversation.embedder, enabled=life_tasks,
                                    provider=app.state.conversation.provider)
    app.state.life = LifeEngine(app.state.database, app.state.vault, app.state.conversation.provider,
                                app.state.conversation.scheduler, world)
    app.state.life.lookups = app.state.lookups
    app.state.openers = Openers(app.state.database, app.state.vault, app.state.conversation.provider,
                                app.state.conversation.scheduler)
    app.state.life.openers = app.state.openers
    app.state.voice = VoiceNotes(app.state.database, app.state.vault, voice_transport, voice_runner)
    app.state.openers.voice = app.state.voice
    app.state.conversation.voice = app.state.voice
    app.state.debug_time = DebugTime(app.state.database, app.state.life)
    app.state.images = ImageRunner(app.state.database, app.state.vault, image_adapters,
                                   app.state.conversation.scheduler)
    app.state.conversation.photos = ChatPhotos(app.state.database, app.state.images, app.state.life,
                                               app.state.openers, app.state.vault)
    app.state.images.share = app.state.conversation.photos.share
    app.state.dating_photos = DatingPhotos(app.state.database, app.state.vault, app.state.images)
    # The photo of a finished outing with the user and the picture on a postcard from a trip.
    app.state.images.others += [lambda: outings.photograph(app.state.database),
                                lambda: trips.picture_postcards(app.state.database)]

    def after_turn():
        # A local image waits while a reply is written (compute and job control); a finished turn lets it start.
        app.state.memory.kick()
        app.state.images.wake()

    app.state.conversation.after_turn = after_turn
    app.state.groups = groups.GroupChats(app.state)
    app.state.life.groups = app.state.groups
    app.state.training = lora_training.TrainingRunner(app.state.database, trainer_spawn)
    app.state.evaluations = lora_evaluation.EvaluationRunner(app.state.database, app.state.vault, app.state.images)
    app.state.generations = lora_generation.GenerationRunner(app.state.database, app.state.vault, app.state.images)
    # Local ComfyUI images wait while a trainer holds the GPU (compute and job control).
    app.state.images.gpu_busy = lambda: app.state.training.active
    app.state.life_tasks = life_tasks
    # The LoRA creator is hidden unless switched on; profile pictures and an adopted adapter keep working.
    app.state.lora_maker = lora_maker_enabled() if lora_maker is None else lora_maker
    app.middleware('http')(stay_in_world)
    app.middleware('http')(guard_writes)
    # Outermost: only this PC, or a paired phone through Tailscale, gets further (companion/phone/access.py).
    app.state.phone = phone_access.Gate(app.state.database)
    app.state.push = phone_push.Pusher(app.state.database, app.state.vault, push_transport)
    app.middleware('http')(app.state.phone)
    app.state.lan = phone_lan.LanServer(app)
    app.add_exception_handler(DomainError, domain_error)
    app.add_exception_handler(RequestValidationError, invalid_request)
    app.add_exception_handler(Exception, unexpected_error)
    app.include_router(router)
    app.include_router(model_router)
    app.include_router(launcher_router)
    app.include_router(recall_router)
    app.include_router(voice_router)
    app.include_router(hardware_router)
    app.include_router(ready_router)
    app.include_router(life_routes.router)
    app.include_router(home_routes.router)
    app.include_router(pets_routes.router)
    app.include_router(wardrobe_routes.router)
    app.include_router(upkeep_routes.router)
    app.include_router(grooming_routes.router)
    app.include_router(kitchen_routes.router)
    app.include_router(media_routes.router)
    app.include_router(hobbies_routes.router)
    app.include_router(admin_routes.router)
    app.include_router(work_routes.router)
    app.include_router(steps_routes.router)
    app.include_router(traditions_routes.router)
    app.include_router(scrapbook_routes.router)
    app.include_router(history_routes.router)
    app.include_router(life_routes.today_router)
    app.include_router(life_routes.feed_router)
    app.include_router(world_routes.router)
    app.include_router(image_routes.router)
    app.include_router(context_routes.router)
    app.include_router(story_routes.router)
    app.include_router(authors_note_routes.router)
    app.include_router(group_routes.router)
    app.include_router(group_routes.secrets_router)
    app.include_router(dating_routes.router)
    app.include_router(export_routes.router)
    app.include_router(lora_routes.router)
    if app.state.lora_maker:
        app.include_router(lora_routes.maker_router)
    app.include_router(import_routes.router)
    app.include_router(file_routes.router)
    app.include_router(closeness_routes.router)
    app.include_router(phone_routes.router)
    app.include_router(people_routes.router)
    app.include_router(debug_router)
    app.include_router(worlds_routes.router)
    app.include_router(calls_router)
    app.include_router(mix_router)
    app.include_router(matches_router)
    if FRONTEND.exists():
        app.mount('/', StaticFiles(directory=FRONTEND, html=True), name='frontend')
    return app
