"""Runs queued image jobs in this process (PRD F4–F8, compute and job control).

Admission: each backend runs at most its configured number of jobs, every Codex backend shares
one slot because the Codex path is strictly serial (F8), and a local ComfyUI job waits while a
conversation reply is being written so the two never compete for the GPU at the start.

Every dispatch re-checks the frozen request: the post must still exist, its events must not have
changed, the backend must still be enabled, and the request is classified again (F6).
"""
import asyncio
import contextlib

from companion.database import decode, encode, one, optional
from companion.images import backends, jobs, prompts, storage
from companion.images.adapters.base import AdapterError, ImageRequest, size_for
from companion.images.content import classify, stricter
from companion.images.routing import eligible

CANCEL_NOTES = {'hosted': 'Cancelled. The provider may still finish the request; its result will not be used.',
                'codex': 'Cancelled; the Codex request was stopped.',
                'comfyui': 'Cancelled; the request was removed from ComfyUI.'}


def identity(backend, inputs) -> str:
    """How this image draws the character, recorded on the job (PRD LoRA maker, F2)."""
    lora = inputs.get('lora')
    if not lora:
        return 'text description' if backend['kind'] == 'comfyui' else 'text description only'
    if backend['kind'] == 'comfyui':
        return f"LoRA {lora['name']} at strength {lora['strength']:g} (appearance version {inputs['appearance_version']})"
    return 'text description only; this backend cannot apply the adopted LoRA'


def default_adapters() -> dict:
    from companion.images.adapters.codex import CodexAdapter
    from companion.images.adapters.comfyui import ComfyAdapter
    from companion.images.adapters.hosted import HostedAdapter
    return {'comfyui': ComfyAdapter(), 'codex': CodexAdapter(), 'hosted': HostedAdapter()}


class ImageRunner:
    def __init__(self, database, vault, adapters=None, scheduler=None):
        self.database = database
        self.vault = vault
        self.adapters = adapters if adapters is not None else default_adapters()
        self.scheduler = scheduler
        self.tasks: dict[str, tuple[asyncio.Task, dict]] = {}
        self.wakeup: asyncio.Event | None = None
        # Set by the app: true while a LoRA trainer holds the local GPU.
        self.gpu_busy = lambda: False
        # Other runners that send to the same backends (LoRA reference generation) report what
        # they are running, so backend limits and the single Codex slot hold across both.
        self.sharing: list = []

    def wake(self):
        if self.wakeup:
            self.wakeup.set()

    async def run_forever(self, tick_seconds=30):
        self.wakeup = asyncio.Event()
        while True:
            with contextlib.suppress(Exception):
                self.automatic()
                self.dispatch()
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self.wakeup.wait(), tick_seconds)
            self.wakeup.clear()

    def automatic(self):
        post_id = jobs.automatic_candidate(self.database)
        if post_id:
            jobs.enqueue(self.database, post_id, 'automatic')

    def busy(self, backend) -> bool:
        running = [meta for _task, meta in self.tasks.values()] + [meta for report in self.sharing for meta in report()]
        if backend['kind'] == 'codex':
            return any(meta['kind'] == 'codex' for meta in running)
        if backend['kind'] == 'comfyui' and self.scheduler is not None and self.scheduler.foreground:
            return True
        if backend['kind'] == 'comfyui' and backends.is_local(backend) and self.gpu_busy():
            return True
        return sum(meta['id'] == backend['id'] for meta in running) >= backend['concurrency']

    def dispatch(self) -> list[asyncio.Task]:
        started = []
        with self.database.connect() as connection:
            queued = connection.execute("SELECT id, backend_id FROM image_jobs WHERE status='queued' "
                                        'ORDER BY created_at, rowid').fetchall()
            for job in queued:
                if job['id'] in self.tasks:
                    continue
                backend = optional(connection, 'SELECT * FROM image_backends WHERE id=?', (job['backend_id'],))
                if backend and (backend['blocked_reason'] or self.busy(backend)):
                    continue
                meta = {'id': job['backend_id'], 'kind': backend['kind'] if backend else None}
                task = asyncio.create_task(self.run(job['id']))
                self.tasks[job['id']] = (task, meta)
                started.append(task)
        return started

    async def run(self, job_id):
        try:
            await self.execute(job_id)
        finally:
            self.tasks.pop(job_id, None)
            asyncio.get_running_loop().call_soon(self.redispatch)

    def redispatch(self):
        with contextlib.suppress(Exception):
            self.dispatch()

    async def drain(self):
        """Run until nothing more can start; tests use it in place of the background loop."""
        while True:
            started = self.dispatch()
            pending = [task for task, _meta in list(self.tasks.values()) if not task.done()]
            if not started and not pending:
                return
            await asyncio.gather(*pending, return_exceptions=True)

    def claim(self, job_id):
        """Re-validate and mark running. Returns (job, backend, inputs) or None when it ended here."""
        with self.database.connect() as connection:
            job = one(connection, 'SELECT * FROM image_jobs WHERE id=?', (job_id,))
            inputs = decode(job['inputs'])
            backend = optional(connection, 'SELECT * FROM image_backends WHERE id=?', (job['backend_id'],))
            post = optional(connection, 'SELECT status FROM feed_posts WHERE id=?', (job['post_id'],))
            stale = prompts.stale(connection, inputs)
        if job['status'] != 'queued':
            return None
        problem = self.problem(job, backend, post, stale, inputs)
        if problem:
            jobs.finish(self.database, job_id, problem[0], error=problem[1], code=problem[2])
            return None
        adapter_config = decode(backend['config'])
        with self.database.connect(write=True) as connection:
            timestamp = self.database.now()
            current = one(connection, 'SELECT status FROM image_jobs WHERE id=?', (job_id,))
            if current['status'] != 'queued':
                return None
            connection.execute("UPDATE image_jobs SET status='running', started_at=?, backend_kind=?, provider=?, "
                               'model=?, identity_method=? WHERE id=?',
                               (timestamp, backend['kind'], backend['provider'], adapter_config.get('model'),
                                identity(backend, inputs), job_id))
            from companion.life import feed
            feed.apply_image(connection, job['post_id'], job_id, 'running', timestamp)
        return job, backend, inputs

    def problem(self, job, backend, post, stale, inputs):
        if post is None or post['status'] == 'removed':
            return 'cancelled', 'The post was removed.', 'post_removed'
        if stale:
            return 'cancelled', 'The event changed after this image was requested.', 'stale_inputs'
        if backend is None or not backend['enabled']:
            return 'failed', 'The backend this image was routed to is no longer enabled.', 'backend_unavailable'
        classification = classify(inputs)
        classification.tier = stricter(classification.tier, job['classification'])
        if not eligible(classification, backend):
            reasons = ', '.join(classification.reasons) or classification.tier
            return 'failed', f'This request is now classified {classification.tier} ({reasons}) and cannot ' \
                             f'go to {backend["label"]}.', 'not_eligible'
        return None

    async def execute(self, job_id):
        try:
            claimed = self.claim(job_id)
        except Exception as error:  # noqa: BLE001 - a job that cannot start must not stay queued forever.
            jobs.finish(self.database, job_id, 'failed', error=f'This image could not start ({error}).',
                        code='failed')
            return
        if claimed is None:
            return
        job, backend, inputs = claimed
        width, height = size_for(backend['kind'], inputs['aspect'])
        key = self.vault.get(backend['credential_ref']) if backend['credential_ref'] else None
        request = ImageRequest(job_id, inputs['prompt'], inputs['negative'], inputs['seed'], width, height,
                               backend, decode(backend['config']), key, storage.raw_directory(self.database),
                               inputs.get('lora') if backend['kind'] == 'comfyui' else None)
        result = None
        try:
            result = await self.adapters[backend['kind']].generate(request)
            stored = storage.store(self.database, job_id, result.data)
        except asyncio.CancelledError:
            jobs.finish(self.database, job_id, 'cancelled', error=CANCEL_NOTES[backend['kind']], code='cancelled')
            raise
        except AdapterError as error:
            # A rejected output stays on disk; quota was spent on it (F8).
            raw = result.raw_path.name if result and result.raw_path else None
            self.failed(job, backend, inputs, error, raw)
            return
        except Exception as error:  # noqa: BLE001 - an adapter bug fails the job, not the runner.
            self.failed(job, backend, inputs, AdapterError('failed', f'The image backend failed ({error}).'))
            return
        if result.raw_path:
            with contextlib.suppress(OSError):
                result.raw_path.unlink()
        jobs.finish(self.database, job_id, 'completed', fields={
            'output_file': stored['file'], 'width': stored['width'], 'height': stored['height'],
            'seed': result.seed, 'model': result.model or decode(backend['config']).get('model'),
            'workflow': result.workflow, 'remote_id': result.remote_id,
            'usage': None if result.usage is None else encode(result.usage)})

    def failed(self, job, backend, inputs, error: AdapterError, raw=None):
        fields = {key: value for key, value in (('remote_id', error.remote_id), ('raw_file', raw)) if value}
        if error.code == 'auth':
            backends.block(self.database, backend['id'], error.message)
        was_current = jobs.is_current(self.database, job['id'])
        jobs.finish(self.database, job['id'], 'failed', error=error.message, code=error.code, fields=fields)
        if error.code == 'auth' or not was_current:
            return
        with self.database.connect() as connection:
            fallback = jobs.image_settings(connection)['fallback']
        after = backend['id']
        if error.code == 'refused':
            inputs, after = jobs.reclassify_refused(self.database, job['id'], ['refused by the provider']), None
        # Fallback is opt-in and only to a backend the request is eligible for (F5, F6).
        if fallback and jobs.routable(self.database, inputs, after):
            jobs.enqueue(self.database, job['post_id'], 'fallback', inputs=inputs, retry_of=job['id'],
                         after_id=after)
            self.wake()

    async def cancel(self, job_id) -> dict:
        if jobs.cancel_queued(self.database, job_id):
            return jobs.get(self.database, job_id)
        entry = self.tasks.get(job_id)
        if entry:
            entry[0].cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await entry[0]
        return jobs.get(self.database, job_id)
