"""Settings > Models: built-in recall and the recall test (companion/providers/builtin_recall.py)."""
import os
import subprocess
import sys
import time

from fastapi import APIRouter, Request

from companion.errors import require
from companion.memory.vectors import cosine
from companion.models import Input
from companion.providers import builtin_recall
from companion.providers.embeddings import as_documents, as_query
from companion.providers.scheduling import CONVERSATION
from companion.text_models import config_for, key_for

router = APIRouter(prefix='/api/models')
TEST_QUERY = "What's my sister's name?"
TEST_DOCUMENTS = ['My sister Lena lives in Ohio.', 'I had pasta for dinner.']
TEST_SECONDS = 150


class BuiltinRecallUpdate(Input):
    enabled: bool
    model_path: str = ''


def overview(request: Request) -> dict:
    builtin = request.app.state.builtin_recall
    with request.app.state.database.connect() as connection:
        current = builtin_recall.read(connection)
    return {**current, **builtin.status(), 'runtime': builtin.runtime(), 'models': builtin_recall.find_models(
        builtin.folder), 'models_folder': str(builtin.folder / 'models'), 'suggested': builtin_recall.SUGGESTED}


@router.get('/builtin-recall')
def show(request: Request):
    return overview(request)


@router.put('/builtin-recall')
async def change(body: BuiltinRecallUpdate, request: Request):
    builtin = request.app.state.builtin_recall
    path = body.model_path.strip().strip('"')
    if path or body.enabled:
        builtin_recall.check_model(path)
    require(not body.enabled or builtin.server(), 'Download llama.cpp first.', 409)
    database = request.app.state.database
    with database.connect(write=True) as connection:
        connection.execute('UPDATE builtin_recall SET enabled=?, model_path=?, updated_at=? WHERE id=1',
                           (int(body.enabled), path, database.now()))
    await builtin.stop()
    builtin.kick()
    # A new model means new vectors; the memory worker makes them in the background.
    request.app.state.memory.kick()
    return overview(request)


@router.post('/builtin-recall/runtime')
async def install(request: Request):
    await request.app.state.builtin_recall.install()
    return overview(request)


@router.post('/builtin-recall/open-folder')
def open_folder(request: Request):
    folder = request.app.state.builtin_recall.folder / 'models'
    folder.mkdir(parents=True, exist_ok=True)
    if sys.platform == 'win32':
        os.startfile(folder)  # noqa: S606 - opens the user's own folder in Explorer.
    else:
        subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', str(folder)])
    return {'folder': str(folder)}


@router.post('/recall-test')
async def test(request: Request):
    """Embed a question and two memories with whatever does recall now, and say whether the right one won."""
    state = request.app.state
    with state.database.connect() as connection:
        config = config_for(connection, 'recall')
    require(config is not None and bool(config.get('embedding_model')),
            'Nothing does semantic recall yet: turn on built-in recall, or give a profile an embedding model.', 409)
    texts = [as_query(config, TEST_QUERY), *as_documents(config, TEST_DOCUMENTS)]
    started = time.perf_counter()
    async with state.conversation.scheduler.reserve(config, CONVERSATION):
        vectors = await state.conversation.embedder.embed(config, key_for(state.vault, config), texts, TEST_SECONDS)
    scores = [round(cosine(vectors[0], vector), 3) for vector in vectors[1:]]
    return {'model': config['embedding_model'], 'dimensions': len(vectors[0]), 'scores': scores,
            'milliseconds': round((time.perf_counter() - started) * 1000), 'found_related': scores[0] > scores[1]}
