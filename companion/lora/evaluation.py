"""The Evaluate step: a fixed set of prompts rendered with an adapter on local ComfyUI.

The set covers a portrait, a full-body shot, everyday settings, two lighting conditions, an
expression and the key traits from the appearance description. Each prompt has a fixed seed and
is rendered twice: with the adapter, and from the text description alone for comparison. Every
output, setting and failure is kept and shown; held-out evaluation references are shown beside
them and are never used as prompts or inputs. Requests are classified like any image request:
Prohibited is refused and NSFW is fine because only a local ComfyUI backend is used.
"""
import asyncio
import contextlib

from companion.characters import require_current
from companion.database import decode, encode, identifier, many, one
from companion.errors import DomainError, require
from companion.images import backends
from companion.images.adapters.base import AdapterError, ImageRequest, size_for
from companion.images.content import PROHIBITED, classify
from companion.images.prompts import NEGATIVE
from companion.images.routing import eligible
from companion.images.storage import sniff
from companion.lora import appearance, files, references

SET_VERSION = 1
# (key, label, prompt template, seed, aspect). `{who}` is the subject; `{traits}` the appearance text.
PROMPTS = (
    ('portrait', 'Portrait', '{who}, head and shoulders portrait, plain background, soft even light', 1101,
     'portrait'),
    ('full_body', 'Full body', '{who}, full-body photo standing in a plain studio, whole outfit visible', 1102,
     'portrait'),
    ('cafe', 'Everyday: café', '{who} reading at a small café table, candid photograph', 1103, 'landscape'),
    ('street', 'Everyday: street', '{who} walking along a city street in the afternoon', 1104, 'landscape'),
    ('golden_hour', 'Lighting: golden hour', '{who} outdoors at golden hour, warm backlight', 1105, 'square'),
    ('night_lamp', 'Lighting: night', '{who} indoors at night lit by a single table lamp', 1106, 'square'),
    ('expression', 'Expression', '{who} laughing, close-up of the face', 1107, 'square'),
    ('traits', 'Key traits', '{who}, close-up showing {traits}', 1108, 'portrait'),
)
LABELS = {key: label for key, label, *_rest in PROMPTS}
STYLE = 'Natural photograph.'


def directory(database):
    return files.folder(database, 'evaluations')


def subject(name, trigger, appearance_text, variant) -> str:
    if variant == 'lora':
        return f'{trigger}, {name}' if trigger else name
    text = appearance_text.strip().rstrip('.')
    return f'{name}, {text}' if text else name


def build(name, trigger, appearance_text, variant) -> list[dict]:
    traits = appearance_text.strip().rstrip('.') or 'their face and hair'
    who = subject(name, trigger, appearance_text, variant)
    return [{'prompt_key': key, 'prompt': f"{STYLE} {template.format(who=who, traits=traits)}.", 'seed': seed,
             'aspect': aspect, 'variant': variant} for key, _label, template, seed, aspect in PROMPTS]


def local_comfy(connection) -> list[dict]:
    return [backend for backend in backends.ordered(connection, enabled_only=True)
            if backend['kind'] == 'comfyui' and backends.is_local(backend)]


def image_view(row) -> dict:
    return {**{key: value for key, value in row.items() if key != 'output_file'},
            'label': LABELS.get(row['prompt_key'], row['prompt_key']), 'has_image': row['output_file'] is not None}


def view(connection, evaluation) -> dict:
    images = many(connection, 'SELECT * FROM lora_eval_images WHERE evaluation_id=? ORDER BY position',
                  (evaluation['id'],))
    adapter = one(connection, 'SELECT name, format, trigger FROM lora_adapters WHERE id=?', (evaluation['adapter_id'],))
    counts = {status: sum(image['status'] == status for image in images)
              for status in ('queued', 'running', 'completed', 'failed', 'cancelled', 'interrupted')}
    return {**evaluation, 'held_out': decode(evaluation['held_out']), 'adapter': adapter, 'counts': counts,
            'images': [image_view(image) for image in images]}


def listing(database, adapter_id=None) -> list[dict]:
    with database.connect() as connection:
        companion = require_current(connection)
        sql, values = 'SELECT * FROM lora_evaluations WHERE companion_id=?', [companion['id']]
        if adapter_id:
            sql, values = sql + ' AND adapter_id=?', [*values, adapter_id]
        return [view(connection, row) for row in many(connection, sql + ' ORDER BY created_at DESC, rowid DESC',
                                                       tuple(values))]


def get(database, evaluation_id) -> dict:
    with database.connect() as connection:
        companion = require_current(connection)
        return view(connection, one(connection, 'SELECT * FROM lora_evaluations WHERE id=? AND companion_id=?',
                                    (evaluation_id, companion['id'])))


def create(database, body, training_active=False) -> dict:
    require(not training_active, 'Training is using the GPU. Evaluate when it finishes.', 409)
    with database.connect() as connection:
        adapter = appearance.get_adapter(connection, body.adapter_id)
        require(adapter['removed_at'] is None, 'This adapter was removed.', 410)
        targets = local_comfy(connection)
        require(targets, 'Evaluation needs an enabled ComfyUI server on this computer, because only ComfyUI applies '
                'the adapter.', 409)
        busy = connection.execute("SELECT 1 FROM lora_evaluations WHERE status='running'").fetchone()
        require(busy is None, 'An evaluation is already running.', 409)
    installed = appearance.install(database, body.adapter_id)
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        definition = companion['version']['definition']
        held_out = [item['id'] for item in references.rows(connection) if item['role'] == 'evaluation']
        variants = ['lora', 'text'] if body.include_baseline else ['lora']
        planned = [item for variant in variants
                   for item in build(definition['name'], adapter['trigger'], definition.get('appearance', ''), variant)]
        evaluation_id = identifier()
        timestamp = database.now()
        connection.execute(
            'INSERT INTO lora_evaluations (id, companion_id, adapter_id, set_version, strength, comfy_name, backend_id, '
            "held_out, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'running', ?)",
            (evaluation_id, companion['id'], adapter['id'], SET_VERSION, body.strength, installed['comfy_name'],
             targets[0]['id'], encode(held_out), timestamp))
        for position, item in enumerate(planned):
            classification = classify({'prompt': item['prompt'], 'negative': NEGATIVE,
                                       'appearance': definition.get('appearance', '')})
            refused = classification.tier == PROHIBITED or not eligible(classification, targets[0])
            width, height = size_for('comfyui', item['aspect'])
            connection.execute(
                'INSERT INTO lora_eval_images (id, evaluation_id, position, prompt_key, variant, prompt, negative, '
                'seed, width, height, status, classification, error, finished_at) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (identifier(), evaluation_id, position, item['prompt_key'], item['variant'], item['prompt'], NEGATIVE,
                 item['seed'], width, height, 'failed' if refused else 'queued', classification.tier,
                 f"Refused: {', '.join(classification.reasons)}." if refused else None,
                 timestamp if refused else None))
    return {**get(database, evaluation_id), 'install': installed}


def rate(database, image_id, rating) -> dict:
    with database.connect(write=True) as connection:
        image = one(connection, 'SELECT * FROM lora_eval_images WHERE id=?', (image_id,))
        require(image['status'] == 'completed', 'Only a finished image can be rated.', 409)
        connection.execute('UPDATE lora_eval_images SET rating=? WHERE id=?', (rating, image_id))
    return get(database, image['evaluation_id'])


def recover(database):
    with database.connect(write=True) as connection:
        timestamp = database.now()
        connection.execute("UPDATE lora_eval_images SET status='interrupted', error='The app closed first.', "
                           "finished_at=? WHERE status IN ('queued', 'running')", (timestamp,))
        connection.execute("UPDATE lora_evaluations SET status='interrupted', finished_at=? WHERE status='running'",
                           (timestamp,))


def file_of(database, image_id):
    with database.connect() as connection:
        row = one(connection, 'SELECT output_file FROM lora_eval_images WHERE id=?', (image_id,))
    require(row['output_file'] is not None, 'This image has no file.', 404)
    return files.inside(directory(database), row['output_file'])


class EvaluationRunner:
    """Renders one evaluation's images one at a time through the ComfyUI adapter."""

    def __init__(self, database, vault, images):
        self.database = database
        self.vault = vault
        self.images = images
        self.tasks: dict[str, asyncio.Task] = {}

    @property
    def active(self) -> bool:
        return bool(self.tasks)

    def start(self, evaluation_id) -> asyncio.Task:
        task = asyncio.get_running_loop().create_task(self.run(evaluation_id))
        self.tasks[evaluation_id] = task
        task.add_done_callback(lambda _task: self.tasks.pop(evaluation_id, None))
        return task

    async def run(self, evaluation_id):
        try:
            while (image := self.next_image(evaluation_id)) is not None:
                await self.yield_to_chat()
                await self.render(image)
            self.close(evaluation_id, 'completed')
        except asyncio.CancelledError:
            self.close(evaluation_id, 'cancelled')
            raise

    async def yield_to_chat(self, pause=0.5):
        """Waits while a chat reply is being written, as image jobs on local ComfyUI do."""
        scheduler = getattr(self.images, 'scheduler', None)
        while scheduler is not None and scheduler.foreground:
            await asyncio.sleep(pause)

    def next_image(self, evaluation_id):
        with self.database.connect() as connection:
            evaluation = one(connection, 'SELECT * FROM lora_evaluations WHERE id=?', (evaluation_id,))
            if evaluation['status'] != 'running':
                return None
            image = connection.execute("SELECT * FROM lora_eval_images WHERE evaluation_id=? AND status='queued' "
                                       'ORDER BY position LIMIT 1', (evaluation_id,)).fetchone()
            return None if image is None else {**dict(image), 'evaluation': evaluation}

    def mark(self, image_id, **fields):
        columns = ', '.join(f'{key}=?' for key in fields)
        with self.database.connect(write=True) as connection:
            connection.execute(f'UPDATE lora_eval_images SET {columns} WHERE id=?', (*fields.values(), image_id))

    async def render(self, image):
        evaluation = image['evaluation']
        with self.database.connect() as connection:
            backend = connection.execute('SELECT * FROM image_backends WHERE id=?',
                                         (evaluation['backend_id'],)).fetchone()
        if backend is None or not backend['enabled']:
            self.mark(image['id'], status='failed', error='The ComfyUI backend is no longer enabled.',
                      finished_at=self.database.now())
            return
        backend = dict(backend)
        lora = {'comfy_name': evaluation['comfy_name'], 'strength': evaluation['strength'], 'trigger': ''} \
            if image['variant'] == 'lora' else None
        self.mark(image['id'], status='running', started_at=self.database.now())
        request = ImageRequest(image['id'], image['prompt'], image['negative'], image['seed'], image['width'],
                               image['height'], backend, decode(backend['config']), None, None, lora)
        try:
            result = await self.images.adapters['comfyui'].generate(request)
            kind, _width, _height = sniff(result.data)
            name = f"{image['id']}.{kind}"
            (directory(self.database) / name).write_bytes(result.data)
        except asyncio.CancelledError:
            self.mark(image['id'], status='cancelled', error='Cancelled.', finished_at=self.database.now())
            raise
        except AdapterError as error:
            self.mark(image['id'], status='failed', error=error.message, finished_at=self.database.now())
            return
        except Exception as error:  # noqa: BLE001 - one failed image is recorded, not hidden.
            self.mark(image['id'], status='failed', error=f'The image failed ({error}).',
                      finished_at=self.database.now())
            return
        self.mark(image['id'], status='completed', output_file=name, workflow=result.workflow, model=result.model,
                  finished_at=self.database.now())

    def close(self, evaluation_id, status):
        with self.database.connect(write=True) as connection:
            timestamp = self.database.now()
            if status != 'completed':
                connection.execute("UPDATE lora_eval_images SET status='cancelled', error='Cancelled.', finished_at=? "
                                   "WHERE evaluation_id=? AND status IN ('queued', 'running')",
                                   (timestamp, evaluation_id))
            connection.execute("UPDATE lora_evaluations SET status=?, finished_at=? WHERE id=? AND status='running'",
                               (status, timestamp, evaluation_id))

    async def cancel(self, evaluation_id) -> dict:
        task = self.tasks.get(evaluation_id)
        if task is None:
            self.close(evaluation_id, 'cancelled')
        else:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, DomainError):
                await task
        return get(self.database, evaluation_id)
