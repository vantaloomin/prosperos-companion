"""Time reconciliation and bounded catch-up (PRD T3–T7).

Each timeline keeps a cursor: the real instant its fictional life has been simulated through.
Reconciling compares the cursor with now. A return after a long enough gap plans one batch of
routine slots that ended inside the window, capped by the user's limits however long the absence
was, and moves the cursor to now in the same transaction. The cursor never moves backward, so a
clock rollback, a restart or a second launch can never simulate the same real interval twice.
Every event's idempotency key is its timeline plus routine slot, so a batch resumed after a crash
only finishes what it had not committed.

Generation time (`created_at`), event time (`starts_at`/`ends_at`) and the window a batch covers
are stored separately: a catch-up synthesizes missed fiction now and never claims it ran while
the app was closed (T4).
"""
import asyncio
import random
from datetime import timedelta

from companion import events
from companion.characters import current
from companion.clock import parse, stamp
from companion.database import decode, encode, identifier, many, one, optional, settings
from companion.errors import DomainError
from companion.life import feed, routine
from companion.life.synthesis import SynthesisInvalid, synthesize
from companion.models import EventProposal
from companion.providers.scheduling import BackgroundInterrupted
from companion.providers.vault import credential_for
from companion.workspace import overlapping_pause

LEASE = timedelta(minutes=10)
MAX_ATTEMPTS = 3
FLAGS = ('automatic_events', 'catch_up_on_return')
UNFINISHED = ('planned', 'running', 'interrupted')


# Settings ---------------------------------------------------------------------------------------

def life_settings(connection) -> dict:
    return one(connection, 'SELECT * FROM life_settings WHERE id=1')


def settings_view(row: dict) -> dict:
    return {**row, **{flag: bool(row[flag]) for flag in FLAGS}}


def read_settings(database) -> dict:
    with database.connect() as connection:
        return settings_view(life_settings(connection))


def update_settings(database, body) -> dict:
    """Allowing or revoking automatic events advances the permission revision (T3, T7)."""
    changes = body.model_dump(exclude_none=True)
    with database.connect(write=True) as connection:
        row = life_settings(connection)
        changed = {key: int(value) if isinstance(value, bool) else value
                   for key, value in changes.items() if row[key] != value}
        if changed:
            timestamp = database.now()
            columns = ', '.join(f'{key}=?' for key in changed)
            connection.execute(f'UPDATE life_settings SET {columns}, updated_at=? WHERE id=1',
                               (*changed.values(), timestamp))
            if 'automatic_events' in changed:
                connection.execute('UPDATE workspace_settings SET permission_revision=permission_revision+1, '
                                   'updated_at=? WHERE id=1', (timestamp,))
        return settings_view(life_settings(connection))


# Cursor and runs --------------------------------------------------------------------------------

def cursor(connection, timeline_id) -> dict:
    """A new timeline's life starts when the timeline was created; nothing earlier is simulated."""
    row = optional(connection, 'SELECT * FROM life_cursors WHERE timeline_id=?', (timeline_id,))
    if row:
        return row
    timeline = one(connection, 'SELECT * FROM timelines WHERE id=?', (timeline_id,))
    return {'timeline_id': timeline_id, 'simulated_through': timeline['created_at'], 'last_reconciled_at': None,
            'updated_at': None, 'new': True}


def save_cursor(connection, timeline_id, through, timestamp):
    connection.execute(
        'INSERT INTO life_cursors (timeline_id, simulated_through, last_reconciled_at, updated_at) '
        'VALUES (?, ?, ?, ?) ON CONFLICT(timeline_id) DO UPDATE SET '
        'simulated_through=MAX(simulated_through, excluded.simulated_through), '
        'last_reconciled_at=excluded.last_reconciled_at, updated_at=excluded.updated_at',
        (timeline_id, through, timestamp, timestamp))


def touch_cursor(connection, timeline_id, timestamp):
    connection.execute('UPDATE life_cursors SET last_reconciled_at=?, updated_at=? WHERE timeline_id=?',
                       (timestamp, timestamp, timeline_id))


def run_view(row: dict | None) -> dict | None:
    if row is None:
        return None
    return {key: value for key, value in row.items() if key not in {'owner', 'lease_until'}} | {
        'plan': decode(row['plan']), 'results': decode(row['results'])}


def runs(database, limit=20) -> list[dict]:
    with database.connect() as connection:
        companion = current(connection)
        if companion is None:
            return []
        return [run_view(row) for row in many(
            connection, 'SELECT * FROM life_runs WHERE timeline_id=? ORDER BY created_at DESC LIMIT ?',
            (companion['active_timeline_id'], limit))]


def event_key(timeline_id, slot_key) -> str:
    return f'life:{timeline_id}:{slot_key}'


# Planning ---------------------------------------------------------------------------------------

def background_used(connection, timeline_id, now) -> int:
    since = stamp(now - timedelta(days=1))
    return one(connection, "SELECT COUNT(*) AS n FROM life_events WHERE timeline_id=? AND created_at>? "
               "AND json_extract(inputs, '$.mode')='background'", (timeline_id, since))['n']


def candidates(connection, companion, through, now, lookback_hours) -> list[routine.Slot]:
    """Completed, simulatable slots that start after the cursor and inside the lookback."""
    version = companion['version']
    schedule, _default = routine.blocks(version['definition'])
    start = max(through, now - timedelta(hours=lookback_hours))
    result = []
    for slot in routine.slots(schedule, version['timezone'], start, now):
        if slot.block.kind in routine.RESTING or slot.starts_at < start or slot.ends_at > now:
            continue
        if overlapping_pause(connection, stamp(slot.starts_at), stamp(slot.ends_at)):
            continue
        if optional(connection, 'SELECT id FROM life_events WHERE idempotency_key=?',
                    (event_key(companion['active_timeline_id'], slot.key),)):
            continue
        result.append(slot)
    return result


def spread(slots: list, count: int, seed: str) -> list:
    """One slot from each of `count` consecutive groups, so a batch covers the window evenly."""
    if count <= 0 or not slots:
        return []
    if len(slots) <= count:
        return list(slots)
    chooser, size, chosen = random.Random(seed), len(slots) / count, []
    for index in range(count):
        group = slots[int(index * size):int((index + 1) * size)]
        chosen.append(chooser.choice(group))
    return chosen


def due_at(through, life, mode):
    if mode == 'background':
        return through + timedelta(minutes=life['background_interval_minutes'])
    return through + timedelta(hours=life['return_gap_hours'])


def blocked(workspace, life, mode) -> str | None:
    if workspace['paused_at'] is not None:
        return 'paused'
    if mode == 'background' and not workspace['background_activity']:
        return 'not_permitted'
    if mode == 'return' and not life['catch_up_on_return']:
        return 'disabled'
    return None


def decide(connection, owner, mode, now) -> dict:
    """Claim an unfinished batch or plan a new one. Runs inside one write transaction."""
    companion = current(connection)
    if companion is None:
        return {'state': 'no_companion'}
    workspace, life = settings(connection), life_settings(connection)
    timeline_id, timestamp = companion['active_timeline_id'], stamp(now)
    if state := blocked(workspace, life, mode):
        return {'state': state}
    for run in many(connection, f'SELECT * FROM life_runs WHERE timeline_id=? AND status IN {UNFINISHED} '
                    'ORDER BY created_at', (timeline_id,)):
        if run['status'] == 'running' and run['owner'] != owner and run['lease_until'] > timestamp:
            return {'state': 'in_progress', 'run_id': run['id']}
        claim(connection, run['id'], owner, now)
        return {'state': 'resumed', 'run_id': run['id']}
    position = cursor(connection, timeline_id)
    through = parse(position['simulated_through'])
    if now < through:
        return {'state': 'clock_behind', 'simulated_through': position['simulated_through']}
    if now < due_at(through, life, mode):
        if not position.get('new'):
            touch_cursor(connection, timeline_id, timestamp)
        return {'state': 'not_due', 'due_at': stamp(due_at(through, life, mode))}
    return {'state': 'started', 'run_id': plan_run(connection, owner, mode, now, companion, workspace, life, position)}


def plan_run(connection, owner, mode, now, companion, workspace, life, position) -> str:
    """Fix the batch's slots and move the cursor to now in the same transaction."""
    timeline_id, timestamp = companion['active_timeline_id'], stamp(now)
    run_key = f"{timeline_id}:{position['simulated_through']}"
    if mode == 'background':
        limit = min(1, max(0, life['background_daily_events'] - background_used(connection, timeline_id, now)))
    else:
        limit = life['catch_up_max_events']
    through = parse(position['simulated_through'])
    plan = spread(candidates(connection, companion, through, now, life['catch_up_lookback_hours']), limit, run_key)
    run_id = identifier()
    connection.execute(
        'INSERT INTO life_runs (id, timeline_id, run_key, mode, status, window_start, window_end, plan, '
        'character_version_id, permission_revision, owner, lease_until, attempts, created_at, started_at) '
        "VALUES (?, ?, ?, ?, 'running', ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
        (run_id, timeline_id, run_key, mode, position['simulated_through'], timestamp,
         encode([slot.view() for slot in plan]), companion['active_version_id'], workspace['permission_revision'],
         owner, stamp(now + LEASE), timestamp, timestamp))
    save_cursor(connection, timeline_id, timestamp, timestamp)
    return run_id


def claim(connection, run_id, owner, now):
    connection.execute("UPDATE life_runs SET status='running', owner=?, lease_until=?, attempts=attempts+1, "
                       'started_at=COALESCE(started_at, ?) WHERE id=?',
                       (owner, stamp(now + LEASE), stamp(now), run_id))


# Execution --------------------------------------------------------------------------------------

class LifeEngine:
    """Runs batches for one process. The lock keeps this process to one batch at a time; across
    processes the cursor transaction and event idempotency keys keep work unique."""

    def __init__(self, database, vault, provider, scheduler):
        self.database = database
        self.vault = vault
        self.provider = provider
        self.scheduler = scheduler
        self.owner = identifier()
        self.lock = asyncio.Lock()

    def now(self):
        return self.database.clock.now()

    async def reconcile(self, mode='return') -> dict:
        async with self.lock:
            with self.database.connect(write=True) as connection:
                decision = decide(connection, self.owner, mode, self.now())
            if decision['state'] in {'started', 'resumed'}:
                await self.execute(decision['run_id'])
            return self.outcome(decision)

    def outcome(self, decision) -> dict:
        run = None
        if decision.get('run_id'):
            with self.database.connect() as connection:
                run = run_view(one(connection, 'SELECT * FROM life_runs WHERE id=?', (decision['run_id'],)))
        return {**{key: value for key, value in decision.items() if key != 'run_id'}, 'run': run}

    async def execute(self, run_id):
        with self.database.connect() as connection:
            run = one(connection, 'SELECT * FROM life_runs WHERE id=?', (run_id,))
        results = {result['slot']: result for result in decode(run['results'])}
        try:
            for slot in decode(run['plan']):
                if slot['key'] in results:
                    continue
                results[slot['key']] = await self.simulate(run, slot)
                self.save(run_id, results, 'running')
            self.save(run_id, results, 'completed')
        except BackgroundInterrupted:
            self.save(run_id, results, 'interrupted', 'Paused for the conversation; it resumes on the next visit.')
        except DomainError as error:
            # A model outage leaves the batch resumable a few times before it is given up.
            self.save(run_id, results, 'interrupted' if run['attempts'] < MAX_ATTEMPTS else 'failed', error.message)
        except Exception:  # noqa: BLE001 - a failed batch must still leave a visible state.
            self.save(run_id, results, 'failed', 'The batch failed unexpectedly.')

    def save(self, run_id, results, status, error=None):
        with self.database.connect(write=True) as connection:
            finished = stamp(self.now()) if status != 'running' else None
            connection.execute('UPDATE life_runs SET results=?, status=?, error=?, lease_until=?, finished_at=? '
                               'WHERE id=?', (encode(list(results.values())), status, error,
                                              stamp(self.now() + LEASE), finished, run_id))
            if status == 'completed':
                feed.publish_run(connection, one(connection, 'SELECT * FROM life_runs WHERE id=?', (run_id,)),
                                 list(results.values()), stamp(self.now()))

    async def simulate(self, run, slot) -> dict:
        """One routine slot: write it, record it as a proposal, and commit it if permitted."""
        key = event_key(run['timeline_id'], slot['key'])
        with self.database.connect() as connection:
            companion = current(connection)
            workspace, life = settings(connection), life_settings(connection)
            config = optional(connection, 'SELECT * FROM connection WHERE id=1')
            existing = optional(connection, 'SELECT * FROM life_events WHERE idempotency_key=?', (key,))
            recent = events.committed(connection, run['timeline_id'])[-5:]
        if existing:
            return self.settle(events.view(existing), life)
        if workspace['permission_revision'] != run['permission_revision'] or workspace['paused_at']:
            return {'slot': slot['key'], 'outcome': 'skipped', 'reason': 'Activity permissions changed.'}
        if companion['active_timeline_id'] != run['timeline_id']:
            return {'slot': slot['key'], 'outcome': 'skipped', 'reason': 'The timeline is no longer active.'}
        if config is None:
            return {'slot': slot['key'], 'outcome': 'quiet', 'reason': 'No model connection, so it stayed uneventful.'}
        version = companion['version']
        try:
            written = await synthesize(self.provider, self.scheduler, config,
                                       credential_for(self.vault, config['credential_ref']), version, slot, recent)
        except SynthesisInvalid as invalid:
            return {'slot': slot['key'], 'outcome': 'quiet', 'reason': str(invalid)}
        if written is None:
            return {'slot': slot['key'], 'outcome': 'quiet', 'reason': 'Nothing notable happened.'}
        block = slot['block']
        event = events.propose(self.database, EventProposal(
            idempotency_key=key, kind='ordinary', summary=written['summary'],
            details={'slot': slot['key'], 'block': block['key'], 'label': block['label'], 'activity': block['kind'],
                     'local_date': slot['local_date'], 'timezone': version['timezone'],
                     'post': written.get('post', ''), 'mood': written.get('mood', '')},
            starts_at=slot['starts_at'], ends_at=slot['ends_at'],
            inputs={'run_id': run['id'], 'mode': run['mode'], 'slot': slot, 'synthesis': 'model',
                    'model': config['model'], 'base_url': config['base_url'],
                    'prompt_version': written['prompt_version'], 'character_version_id': version['id']}))
        if event['character_version_id'] != version['id']:
            events.reject(self.database, event['id'])
            return {'slot': slot['key'], 'outcome': 'rejected', 'event_id': event['id'],
                    'reason': 'The character changed while this event was written.'}
        return self.settle(event, life)

    def settle(self, event, life) -> dict:
        if event['status'] == 'proposed' and life['automatic_events']:
            event = events.commit(self.database, event['id'])
        outcome = {'proposed': 'proposed', 'committed': 'committed', 'superseded': 'committed'}.get(
            event['status'], 'rejected')
        result = {'slot': event['details'].get('slot'), 'outcome': outcome, 'event_id': event['id']}
        if event.get('rejection'):
            result['reason'] = event['rejection']
        return result

    async def run_forever(self, tick_seconds=60):
        """Catch up once on open, then tick while the process runs. Ticks use the event loop's
        monotonic timer; background batches only start when the user enabled them (T4)."""
        await self.quietly('return')
        while True:
            await asyncio.sleep(tick_seconds)
            await self.quietly('background')

    async def quietly(self, mode):
        try:
            await self.reconcile(mode)
        except Exception:  # noqa: BLE001 - one failed tick must not stop later ones.
            pass
