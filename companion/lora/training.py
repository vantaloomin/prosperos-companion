"""Training runs: the Configure and Train steps.

A run freezes the dataset (each picture's digest and caption), the options and the exact config
the trainer received. The trainer runs as a subprocess of this app. Progress is whatever the
trainer printed, never an estimate. Cancelling stops the process; checkpoints it already saved
stay. A run resumes only from checkpoints that pass the safetensors check; otherwise the user can
restart it explicitly. A failed or cancelled run never changes the adopted appearance.
"""
import asyncio
import contextlib
import os
import shutil
import signal
import sys
import time
from pathlib import Path

from companion.characters import require_current
from companion.database import decode, encode, identifier, many, one, optional
from companion.errors import DomainError, require
from companion.images.content import PROHIBITED, classify
from companion.lora import appearance, files, references, trainer

LOG_LINES = 60
STOP_GRACE_SECONDS = 20
RESUMABLE = ('failed', 'cancelled', 'interrupted')


def runs_directory(database) -> Path:
    return files.folder(database, 'runs')


def run_folder(database, run) -> Path:
    return runs_directory(database) / run['folder']


def view(run: dict) -> dict:
    checkpoints = decode(run['checkpoints'])
    resumable = run['status'] in RESUMABLE and any(item['verified'] and not item['final'] for item in checkpoints)
    return {**{key: value for key, value in run.items() if key not in ('trainer_config', 'pid')},
            'options': decode(run['options']), 'dataset': decode(run['dataset']), 'checkpoints': checkpoints,
            'trainer_config': decode(run['trainer_config']), 'resumable': resumable,
            'restartable': run['status'] in RESUMABLE, 'verified_on_hardware': trainer.VERIFIED}


def listing(database) -> list[dict]:
    with database.connect() as connection:
        companion = require_current(connection)
        return [view(run) for run in many(connection, 'SELECT * FROM lora_runs WHERE companion_id=? '
                                          'ORDER BY created_at DESC, rowid DESC', (companion['id'],))]


def get_row(connection, run_id) -> dict:
    companion = require_current(connection)
    return one(connection, 'SELECT * FROM lora_runs WHERE id=? AND companion_id=?', (run_id, companion['id']))


def get(database, run_id) -> dict:
    with database.connect() as connection:
        return view(get_row(connection, run_id))


def expand(caption: str, trigger: str) -> str:
    """Captions are written with the trigger word in place, since AI Toolkit does not add it when
    text embeddings are cached."""
    text = caption.replace('[trigger]', trigger).strip()
    if not text:
        return trigger
    return text if trigger.casefold() in text.casefold() else f'{trigger}, {text}'


def describe(database) -> dict:
    with database.connect() as connection:
        current = appearance.settings(connection)
    return {**trainer.describe(), 'check': trainer.check(current['python_path'], current['trainer_dir'])}


def alive(pid: int | None) -> bool:
    """Whether a recorded trainer process still exists, without touching it."""
    if not pid:
        return False
    if sys.platform == 'win32':
        import ctypes
        kernel = ctypes.windll.kernel32
        handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259  # STILL_ACTIVE
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def blocking_run(connection, companion_id) -> dict | None:
    for run in many(connection, "SELECT * FROM lora_runs WHERE companion_id=? AND (status='running' OR "
                    "(status='interrupted' AND pid IS NOT NULL))", (companion_id,)):
        if run['status'] == 'running' or alive(run['pid']):
            return run
    return None


def require_idle(connection, companion_id):
    busy = blocking_run(connection, companion_id)
    if busy and busy['status'] == 'running':
        raise DomainError('A training run is already going. Cancel it or let it finish first.', 409, 'busy')
    if busy:
        raise DomainError(f"The trainer from an earlier run (process {busy['pid']}) may still be running after the "
                          'app closed. Stop it before training again.', 409, 'busy_unknown')
    image = connection.execute("SELECT 1 FROM image_jobs WHERE status='running' AND backend_kind='comfyui'").fetchone()
    require(image is None, 'An image is being made on ComfyUI. Start training when it finishes.', 409)


def dataset_for(connection) -> list[dict]:
    items = references.rows(connection)
    review = references.review(items)
    if not review['ready']:
        raise DomainError(' '.join(review['blocking']), 409, 'dataset_not_ready')
    return [item for item in items if item['role'] == 'train']


def check_content(appearance_text: str, captions: list[str]):
    """Training is local, so NSFW captions may train; Prohibited content never does (F6)."""
    result = classify({'appearance': appearance_text, 'captions': captions})
    if result.tier == PROHIBITED:
        raise DomainError(f"This dataset cannot be trained: {', '.join(result.reasons)}.", 422, 'prohibited')
    return result


def create(database, body) -> dict:
    """Configure: freeze the dataset and the trainer config, then hand the run to the runner."""
    require(body.accept_disclosure, 'Read and accept what training uses and downloads first.', 422)
    require(body.attest_fictional_adult, 'Confirm the pictures show a fictional adult character.', 422)
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        current = appearance.settings(connection)
        status = trainer.check(current['python_path'], current['trainer_dir'])
        if not status['ok']:
            raise DomainError(' '.join(status['problems']), 409, 'trainer_not_ready')
        require_idle(connection, companion['id'])
        pictures = dataset_for(connection)
        captions = [expand(item['caption'], body.trigger) for item in pictures]
        classification = check_content(companion['version']['definition'].get('appearance', ''), captions)
        run_id = identifier()
        run_name = f"{appearance.slug(body.name)}-{run_id[:6]}"
        folder = runs_directory(database) / run_name
        base_model = current['base_model'] or trainer.DEFAULT_BASE
        options = {**trainer.DEFAULTS, **body.options()}
        config = trainer.config(run_name, folder / 'dataset', folder / 'output', options, base_model)
        dataset = {'pictures': [{'reference_id': item['id'], 'sha256': item['sha256'], 'cropped': bool(item['crop_file']),
                                 'caption': caption, 'rights': item['rights'], 'source_note': item['source_note']}
                                for item, caption in zip(pictures, captions, strict=True)],
                   'classification': classification.view(), 'character_version_id': companion['version']['id']}
        timestamp = database.now()
        connection.execute(
            'INSERT INTO lora_runs (id, companion_id, name, status, trainer, trainer_tested, base_model, trigger, '
            'options, trainer_config, dataset, folder, disclosure_accepted_at, created_at) '
            "VALUES (?, ?, ?, 'running', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, companion['id'], body.name, trainer.KEY, trainer.TESTED, base_model, body.trigger,
             encode(options), encode(config), encode(dataset), run_name, timestamp, timestamp))
        reference_files = {item['id']: item['crop_file'] or item['file'] for item in pictures}
    prepare(database, run_id, reference_files, run_name)
    return get(database, run_id)


def prepare(database, run_id, reference_files, run_name):
    """Copy the training pictures and their captions where the trainer reads them."""
    folder = runs_directory(database) / run_name
    target = folder / 'dataset'
    target.mkdir(parents=True, exist_ok=True)
    (folder / 'output').mkdir(exist_ok=True)
    with database.connect() as connection:
        run = get_row(connection, run_id)
    source = references.directory(database)
    for index, picture in enumerate(decode(run['dataset'])['pictures'], start=1):
        name = reference_files[picture['reference_id']]
        stem = f'{index:03d}'
        shutil.copyfile(source / name, target / f'{stem}{Path(name).suffix}')
        (target / f'{stem}.txt').write_text(picture['caption'], encoding='utf-8')
    (folder / 'config.json').write_text(run['trainer_config'], encoding='utf-8')


def scan(database, run) -> list[dict]:
    """Every checkpoint the trainer left, each checked as safetensors."""
    folder = run_folder(database, run)
    found = []
    for checkpoint in trainer.checkpoints(folder / 'output', run['folder'], decode(run['options'])['steps']):
        entry = {'step': checkpoint.step, 'final': checkpoint.final,
                 'file': str(checkpoint.path.relative_to(folder)), 'bytes': checkpoint.path.stat().st_size}
        try:
            inspected = files.inspect_adapter(checkpoint.path)
            entry.update(verified=True, format=inspected['format'], sha256=files.sha256_of(checkpoint.path),
                         problem=None)
        except (files.InvalidAdapter, OSError) as error:
            entry.update(verified=False, format=None, sha256=None, problem=str(error))
        found.append(entry)
    return found


def keep(database, run_id, step: int, final=False) -> dict:
    """Turn a verified checkpoint into an adapter that can be evaluated and adopted."""
    with database.connect() as connection:
        run = get_row(connection, run_id)
    entry = next((item for item in decode(run['checkpoints'])
                  if item['step'] == step and item['final'] == final and item['verified']), None)
    require(entry is not None, 'There is no verified checkpoint at that step.', 404)
    existing = None
    with database.connect() as connection:
        existing = optional(connection, 'SELECT * FROM lora_adapters WHERE run_id=? AND step=? AND removed_at IS NULL',
                            (run_id, step))
    if existing:
        return appearance.adapter_view(existing)
    source = run_folder(database, run) / entry['file']
    adapter_id = identifier()
    target = appearance.adapters_directory(database) / f'{adapter_id}.safetensors'
    files.copy_verified(source, target)
    inspected = files.require_adapter(target)
    digest = files.sha256_of(target)
    require(digest == entry['sha256'], 'The checkpoint changed since it was checked. Check it again.', 409)
    label = run['name'] if final else f"{run['name']} (step {step})"
    with database.connect(write=True) as connection:
        appearance.record_adapter(connection, database.now(), run['companion_id'], target, inspected, digest,
                                  origin='trained', name=label, base_model=run['base_model'],
                                  trainer=f'{trainer.NAME}, {trainer.TESTED}', trigger=run['trigger'],
                                  run_id=run_id, step=step)
        if final:
            connection.execute('UPDATE lora_runs SET adapter_id=? WHERE id=?', (adapter_id, run_id))
        return appearance.adapter_view(appearance.get_adapter(connection, adapter_id))


def recover(database):
    """After a restart nothing resumes by itself. A trainer that outlived the app keeps its pid, so
    no new run starts until it is gone."""
    with database.connect(write=True) as connection:
        timestamp = database.now()
        for run in many(connection, "SELECT id, pid FROM lora_runs WHERE status='running'"):
            still = alive(run['pid'])
            message = (f"The app closed while training; the trainer (process {run['pid']}) may still be running. "
                       'Stop it before resuming.') if still else \
                'The app closed while training. Resume from a verified checkpoint or restart.'
            connection.execute("UPDATE lora_runs SET status='interrupted', error=?, error_code='interrupted', "
                               'finished_at=?, pid=? WHERE id=?',
                               (message, timestamp, run['pid'] if still else None, run['id']))


class TrainingRunner:
    """Runs at most one trainer process at a time and records what it reports."""

    def __init__(self, database, spawn=None):
        self.database = database
        self.spawn = spawn or asyncio.create_subprocess_exec
        self.tasks: dict[str, asyncio.Task] = {}
        self.processes: dict[str, asyncio.subprocess.Process] = {}
        self.cancelling: set[str] = set()

    @property
    def active(self) -> bool:
        return bool(self.tasks)

    def start(self, run_id) -> asyncio.Task:
        task = asyncio.get_running_loop().create_task(self.run(run_id))
        self.tasks[run_id] = task
        task.add_done_callback(lambda _task: self.tasks.pop(run_id, None))
        return task

    async def run(self, run_id):
        try:
            await self.execute(run_id)
        except Exception as error:  # noqa: BLE001 - a broken run must not stay "running".
            self.finish(run_id, 'failed', f'Training could not run ({error}).', 'failed')

    async def execute(self, run_id):
        with self.database.connect() as connection:
            run = get_row(connection, run_id)
            current = appearance.settings(connection)
        folder = run_folder(self.database, run)
        log = folder / 'trainer.log'
        flags = {'creationflags': 0x00000200} if sys.platform == 'win32' else {'start_new_session': True}
        try:
            process = await self.spawn(*trainer.command(current['python_path'], folder / 'config.json'),
                                       cwd=current['trainer_dir'], stdout=asyncio.subprocess.PIPE,
                                       stderr=asyncio.subprocess.STDOUT, **flags)
        except OSError as error:
            self.finish(run_id, 'failed', f'The trainer could not start: {error}.', 'not_started')
            return
        self.processes[run_id] = process
        with self.database.connect(write=True) as connection:
            connection.execute('UPDATE lora_runs SET pid=?, started_at=COALESCE(started_at, ?) WHERE id=?',
                               (process.pid, self.database.now(), run_id))
        try:
            tail = await self.follow(run_id, process, log)
            code = await process.wait()
        except asyncio.CancelledError:
            await self.stop(process)
            raise
        finally:
            self.processes.pop(run_id, None)
        await self.close(run_id, code, tail)

    async def follow(self, run_id, process, log: Path) -> list[str]:
        lines: list[str] = []
        partial, last_write, reported = '', 0.0, None
        with log.open('a', encoding='utf-8', errors='replace') as handle:
            while chunk := await process.stdout.read(4096):
                text = chunk.decode('utf-8', errors='replace')
                handle.write(text)
                handle.flush()
                pieces = (partial + text).replace('\r', '\n').split('\n')
                partial = pieces.pop()
                lines = (lines + [piece for piece in pieces if piece.strip()])[-LOG_LINES:]
                found = trainer.progress(text) or reported
                if found != reported or time.monotonic() - last_write > 5:
                    reported, last_write = found, time.monotonic()
                    self.report(run_id, found, lines)
        if partial.strip():
            lines = (lines + [partial])[-LOG_LINES:]
        self.report(run_id, trainer.progress(partial) or reported, lines)
        return lines

    def report(self, run_id, found, lines):
        with self.database.connect(write=True) as connection:
            if found:
                connection.execute('UPDATE lora_runs SET progress_step=?, progress_total=?, progress_at=?, log_tail=? '
                                   'WHERE id=?', (*found, self.database.now(), '\n'.join(lines), run_id))
            else:
                connection.execute('UPDATE lora_runs SET log_tail=? WHERE id=?', ('\n'.join(lines), run_id))

    async def close(self, run_id, code, tail):
        with self.database.connect() as connection:
            run = get_row(connection, run_id)
        found = await asyncio.to_thread(scan, self.database, run)
        with self.database.connect(write=True) as connection:
            connection.execute('UPDATE lora_runs SET checkpoints=?, exit_code=? WHERE id=?',
                               (encode(found), code, run_id))
        final = next((item for item in found if item['final'] and item['verified']), None)
        if run_id in self.cancelling:
            self.cancelling.discard(run_id)
            saved = sum(item['verified'] and not item['final'] for item in found)
            self.finish(run_id, 'cancelled', f'Cancelled; the trainer was stopped. {saved} verified checkpoint(s) kept.',
                        'cancelled')
        elif code == 0 and final:
            await asyncio.to_thread(keep, self.database, run_id, final['step'], True)
            self.finish(run_id, 'completed', None, None)
        elif code == 0:
            self.finish(run_id, 'failed', 'The trainer finished but left no valid adapter file.', 'no_output')
        else:
            last = tail[-1] if tail else 'no output'
            self.finish(run_id, 'failed', f'The trainer stopped with exit code {code}: {last}', 'trainer_error')

    def finish(self, run_id, status, error, code):
        with self.database.connect(write=True) as connection:
            connection.execute('UPDATE lora_runs SET status=?, error=?, error_code=?, finished_at=?, pid=NULL '
                               'WHERE id=?', (status, error, code, self.database.now(), run_id))

    async def stop(self, process):
        """Ask the trainer to stop, then end it if it does not. On Windows this ends the trainer
        process; worker processes it started may need closing by hand."""
        if process.returncode is not None:
            return
        with contextlib.suppress(ProcessLookupError, OSError):
            if sys.platform == 'win32':
                process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                os.killpg(process.pid, signal.SIGINT)
        try:
            await asyncio.wait_for(process.wait(), STOP_GRACE_SECONDS)
        except TimeoutError:
            with contextlib.suppress(ProcessLookupError, OSError):
                if sys.platform == 'win32':
                    process.kill()
                else:
                    os.killpg(process.pid, signal.SIGKILL)
            await process.wait()

    async def cancel(self, run_id) -> dict:
        with self.database.connect() as connection:
            run = get_row(connection, run_id)
        require(run['status'] == 'running', 'This run is not training.', 409)
        process = self.processes.get(run_id)
        if process is None:
            self.finish(run_id, 'cancelled', 'Cancelled before the trainer started.', 'cancelled')
            return get(self.database, run_id)
        self.cancelling.add(run_id)
        await self.stop(process)
        task = self.tasks.get(run_id)
        if task:
            with contextlib.suppress(Exception):
                await task
        return get(self.database, run_id)

    def resume(self, run_id) -> dict:
        """Run the same config again; AI Toolkit continues from the newest checkpoint in its folder,
        so anything that failed the check is moved aside first."""
        with self.database.connect(write=True) as connection:
            run = get_row(connection, run_id)
            require(view(run)['resumable'], 'This run has no verified checkpoint to resume from. Restart it instead.',
                    409)
            require_idle(connection, run['companion_id'])
            folder = run_folder(self.database, run)
            aside = folder / 'set-aside'
            for item in decode(run['checkpoints']):
                if not item['verified'] and (folder / item['file']).exists():
                    aside.mkdir(exist_ok=True)
                    (folder / item['file']).replace(aside / Path(item['file']).name)
            step = max(item['step'] for item in decode(run['checkpoints']) if item['verified'] and not item['final'])
            connection.execute("UPDATE lora_runs SET status='running', attempt=attempt+1, resumed_from_step=?, "
                               'error=NULL, error_code=NULL, exit_code=NULL, finished_at=NULL WHERE id=?',
                               (step, run_id))
        self.start(run_id)
        return get(self.database, run_id)

    def restart(self, run_id) -> dict:
        """Start again from step 0. Earlier checkpoints are moved aside, not deleted."""
        with self.database.connect(write=True) as connection:
            run = get_row(connection, run_id)
            require(run['status'] in RESUMABLE, 'Only a stopped run can be restarted.', 409)
            require_idle(connection, run['companion_id'])
            output = run_folder(self.database, run) / 'output' / run['folder']
            if output.exists():
                output.replace(output.with_name(f"discarded-attempt-{run['attempt']}"))
            connection.execute("UPDATE lora_runs SET status='running', attempt=attempt+1, resumed_from_step=NULL, "
                               "checkpoints='[]', progress_step=NULL, progress_total=NULL, progress_at=NULL, "
                               'error=NULL, error_code=NULL, exit_code=NULL, finished_at=NULL WHERE id=?', (run_id,))
        self.start(run_id)
        return get(self.database, run_id)

    def shutdown(self):
        """The app is closing: stop the trainer rather than leave it running unattended."""
        for process in list(self.processes.values()):
            with contextlib.suppress(ProcessLookupError, OSError):
                if sys.platform == 'win32':
                    process.kill()
                else:
                    os.killpg(process.pid, signal.SIGKILL)
