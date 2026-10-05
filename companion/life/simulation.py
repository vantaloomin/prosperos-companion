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

from companion import events, notifications
from companion.characters import current
from companion.clock import parse, stamp
from companion.database import decode, encode, identifier, many, one, optional, settings
from companion.errors import DomainError, require
from companion.life import agenda, composer, feed, mood, routine
from companion.life.synthesis import PROMPT_VERSION, SynthesisInvalid, phrase
from companion.life.world import EmptyWorld
from companion.models import EventProposal
from companion.providers.scheduling import BackgroundInterrupted
from companion.text_models import config_for, key_for
from companion.workspace import overlapping_pause

LEASE = timedelta(minutes=10)
MAX_ATTEMPTS = 3
BACKGROUND_LOOKUP_DEADLINE = 20.0
FLAGS = ('automatic_events', 'catch_up_on_return', 'phrase_with_model')
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
    """A timeline's life starts when it was created or last chosen; nothing earlier is simulated."""
    row = optional(connection, 'SELECT * FROM life_cursors WHERE timeline_id=?', (timeline_id,))
    if row:
        return row
    timeline = one(connection, 'SELECT COALESCE(activated_at, created_at) AS since FROM timelines WHERE id=?',
                   (timeline_id,))
    return {'timeline_id': timeline_id, 'simulated_through': timeline['since'], 'last_reconciled_at': None,
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


def plan_for(connection, timeline_id, slot_key) -> dict | None:
    return optional(connection, "SELECT * FROM life_events WHERE timeline_id=? AND kind='plan' AND status='committed' "
                    "AND json_extract(details, '$.target_slot')=? ORDER BY revision DESC LIMIT 1",
                    (timeline_id, slot_key))


def settle_key(thread_key: str) -> str:
    return f'settled:{thread_key}'


OPEN_THREADS = ("SELECT * FROM life_events WHERE timeline_id=? AND kind='thread' AND status IN ({statuses}) "
                "AND json_extract(details, '$.state')='open' AND NOT EXISTS (SELECT 1 FROM life_events settled "
                "WHERE settled.idempotency_key='settled:' || json_extract(life_events.details, '$.thread_key'))")


def due_thread(connection, timeline_id, local_date) -> dict | None:
    """A committed open thread that may settle on this local date."""
    row = optional(connection, OPEN_THREADS.format(statuses="'committed'") +
                   " AND json_extract(details, '$.settles_on')<=? ORDER BY starts_at LIMIT 1",
                   (timeline_id, local_date))
    return events.view(row) if row else None


def unsettled_thread(connection, timeline_id) -> dict | None:
    return optional(connection, OPEN_THREADS.format(statuses="'proposed','committed'") + ' LIMIT 1', (timeline_id,))


def recent_threads(connection, timeline_id) -> list[str]:
    rows = many(connection, "SELECT details FROM life_events WHERE timeline_id=? AND kind='thread' "
                "AND json_extract(details, '$.state')='open' ORDER BY starts_at DESC LIMIT 3", (timeline_id,))
    return [decode(row['details']).get('thread') for row in rows]


def choose(connection, timeline_id, slots: list, count: int, seed: str) -> list:
    """Slots a committed plan names come first, so a plan happens when its time comes."""
    planned = [slot for slot in slots if plan_for(connection, timeline_id, slot.key)][:count]
    rest = spread([slot for slot in slots if slot not in planned], count - len(planned), seed)
    return sorted(planned + rest, key=lambda slot: slot.starts_at)


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


PREPARE_AHEAD = 2


def may_extend(workspace, mode) -> bool:
    """Precomputing the agenda is cheap and needs no model, but still respects pause and, while the
    app is only running in the background, the background permission (T4, T6)."""
    return workspace['paused_at'] is None and (mode == 'return' or bool(workspace['background_activity']))


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
    plan = choose(connection, timeline_id, candidates(connection, companion, through, now,
                                                      life['catch_up_lookback_hours']), limit, run_key)
    run_id = insert_run(connection, owner, companion, workspace, mode, run_key, position['simulated_through'],
                        timestamp, plan, now)
    save_cursor(connection, timeline_id, timestamp, timestamp)
    return run_id


def insert_run(connection, owner, companion, workspace, mode, run_key, window_start, window_end, plan, now) -> str:
    run_id, timestamp = identifier(), stamp(now)
    connection.execute(
        'INSERT INTO life_runs (id, timeline_id, run_key, mode, status, window_start, window_end, plan, '
        'character_version_id, permission_revision, owner, lease_until, attempts, created_at, started_at) '
        "VALUES (?, ?, ?, ?, 'running', ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
        (run_id, companion['active_timeline_id'], run_key, mode, window_start, window_end,
         encode([slot.view() for slot in plan]), companion['active_version_id'], workspace['permission_revision'],
         owner, stamp(now + LEASE), timestamp, timestamp))
    return run_id


def plan_pause(connection, owner, pause_id, now) -> dict:
    """Catching up a paused interval is a separate, deliberate action (T6). It runs once per pause,
    within the same caps as a return, and marks the pause so its events pass the commit check."""
    companion = current(connection)
    require(companion is not None, 'Create a companion first.', 409)
    workspace, life = settings(connection), life_settings(connection)
    require(workspace['paused_at'] is None, 'Resume before catching up a paused interval.', 409)
    pause = one(connection, 'SELECT * FROM pauses WHERE id=?', (pause_id,))
    require(pause['ended_at'] is not None, 'This pause has not ended.', 409)
    run_key = f'pause:{pause_id}'
    existing = optional(connection, 'SELECT id FROM life_runs WHERE run_key=?', (run_key,))
    if existing:
        return {'state': 'already_done', 'run_id': existing['id']}
    connection.execute('INSERT OR IGNORE INTO pause_catch_ups (pause_id, requested_at) VALUES (?, ?)',
                       (pause_id, stamp(now)))
    start, end = parse(pause['started_at']), parse(pause['ended_at'])
    plan = choose(connection, companion['active_timeline_id'], candidates(
        connection, companion, start, end, life['catch_up_lookback_hours']), life['catch_up_max_events'], run_key)
    run_id = insert_run(connection, owner, companion, workspace, 'return', run_key, pause['started_at'],
                        pause['ended_at'], plan, now)
    return {'state': 'started', 'run_id': run_id}


def pauses(database) -> list[dict]:
    with database.connect() as connection:
        rows = many(connection, 'SELECT pauses.*, pause_catch_ups.requested_at AS catch_up_requested_at, '
                    "life_runs.id AS catch_up_run_id FROM pauses LEFT JOIN pause_catch_ups ON pause_id=pauses.id "
                    "LEFT JOIN life_runs ON run_key='pause:' || pauses.id ORDER BY started_at DESC")
        return rows


def claim(connection, run_id, owner, now):
    connection.execute("UPDATE life_runs SET status='running', owner=?, lease_until=?, attempts=attempts+1, "
                       'started_at=COALESCE(started_at, ?) WHERE id=?',
                       (owner, stamp(now + LEASE), stamp(now), run_id))


# Execution --------------------------------------------------------------------------------------

class LifeEngine:
    """Runs batches for one process. The lock keeps this process to one batch at a time; across
    processes the cursor transaction and event idempotency keys keep work unique."""

    def __init__(self, database, vault, provider, scheduler, world=None):
        self.database = database
        self.world = world or EmptyWorld()
        self.vault = vault
        self.provider = provider
        self.scheduler = scheduler
        self.owner = identifier()
        self.lock = asyncio.Lock()
        self.preparing = None
        # Current-context lookups (companion/mcp); set by the app.
        self.lookups = None

    def now(self):
        return self.database.clock.now()

    async def reconcile(self, mode='return') -> dict:
        async with self.lock:
            with self.database.connect(write=True) as connection:
                companion = current(connection)
                if mode == 'return' and companion:
                    mood.note_return(connection, self.now())
                if companion and may_extend(settings(connection), mode):
                    agenda.extend(connection, companion, self.world, self.now())
                decision = decide(connection, self.owner, mode, self.now())
            if decision['state'] in {'started', 'resumed'}:
                await self.execute(decision['run_id'])
            return self.outcome(decision)

    async def catch_up_pause(self, pause_id) -> dict:
        async with self.lock:
            with self.database.connect(write=True) as connection:
                decision = plan_pause(connection, self.owner, pause_id, self.now())
            if decision['state'] == 'started':
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
                posts = feed.publish_run(connection, one(connection, 'SELECT * FROM life_runs WHERE id=?',
                                                         (run_id,)), list(results.values()), stamp(self.now()))
                notifications.enqueue_posts(connection, posts, stamp(self.now()))

    async def simulate(self, run, slot) -> dict:
        """One routine slot: compose it, record it as a proposal, and commit it if permitted."""
        key = event_key(run['timeline_id'], slot['key'])
        with self.database.connect() as connection:
            companion = current(connection)
            workspace, life = settings(connection), life_settings(connection)
            config = config_for(connection, 'life')
            existing = optional(connection, 'SELECT * FROM life_events WHERE idempotency_key=?', (key,))
            recent = events.committed(connection, run['timeline_id'])[-5:]
            plan = plan_for(connection, run['timeline_id'], slot['key'])
            precomputed = agenda.companion_entry(connection, run['timeline_id'], slot['key'],
                                                 companion['version']['id'])
        if existing:
            return self.settle(events.view(existing), life)
        if workspace['permission_revision'] != run['permission_revision'] or workspace['paused_at']:
            return {'slot': slot['key'], 'outcome': 'skipped', 'reason': 'Activity permissions changed.'}
        if companion['active_timeline_id'] != run['timeline_id']:
            return {'slot': slot['key'], 'outcome': 'skipped', 'reason': 'The timeline is no longer active.'}
        version = companion['version']
        composed, slot, prepared = self.compose_slot(slot, version, key, plan, precomputed, recent)
        if composed is None:
            return {'slot': slot['key'], 'outcome': 'quiet', 'reason': 'Nothing notable happened.',
                    **self.follow_threads(run, slot, version, life, key)}
        written, phrasing = await self.phrase(config, life, version, slot, composed, prepared)
        block = slot['block']
        event = events.propose(self.database, EventProposal(
            idempotency_key=key, kind='ordinary', summary=written['summary'],
            details={'slot': slot['key'], 'block': block['key'], 'label': block['label'],
                     'block_kind': block['kind'], 'activity': composed['activity'], 'place': composed['place'],
                     'local_date': slot['local_date'], 'timezone': version['timezone'],
                     'post': written['post'], 'mood': composed['mood'], 'with': composed.get('with'),
                     'fulfils': composed.get('fulfils'), 'weather': composed.get('weather')},
            starts_at=slot['starts_at'], ends_at=slot['ends_at'],
            inputs={'run_id': run['id'], 'mode': run['mode'], 'slot': slot, 'world': self.world.name,
                    'composer_version': composed['composer_version'], 'template': {
                        'summary': composed['summary'], 'post': composed['post']},
                    'character_version_id': version['id'], **phrasing}), run['timeline_id'])
        if event['character_version_id'] != version['id']:
            events.reject(self.database, event['id'])
            return {'slot': slot['key'], 'outcome': 'rejected', 'event_id': event['id'],
                    'reason': 'The character changed while this event was written.'}
        result = self.settle(event, life)
        if result['outcome'] in {'proposed', 'committed'} and not plan:
            result.update(self.plan_ahead(run, slot, version, life, key))
        if result['outcome'] in {'proposed', 'committed'}:
            result.update(self.follow_threads(run, slot, version, life, key))
        return result

    def compose_slot(self, slot, version, key, plan, precomputed, recent) -> tuple:
        """(composed, slot, prepared wording): a committed plan's outing, else the precomputed entry,
        else a fresh composition. The precomputed block can differ from the routine's, for example
        a work block that became a day off on a public holiday."""
        if plan:
            return composer.fulfil(events.view(plan), version['definition']), slot, None
        if precomputed:
            return precomputed['entry'], {**slot, 'block': decode(precomputed['block'])}, precomputed['prepared']
        recent_keys = [decode(event['details']).get('activity') for event in recent]
        return composer.compose(slot, version['definition'], self.world, key, recent_keys), slot, None

    def follow_threads(self, run, slot, version, life, key) -> dict:
        """Settle an open thread whose day has come, or now and then open one (PRD T2). At most one
        thread is open at a time, and each waits for review like any event."""
        timeline_id = run['timeline_id']
        with self.database.connect() as connection:
            due = due_thread(connection, timeline_id, slot['local_date'])
            busy = due or unsettled_thread(connection, timeline_id)
            used = [] if busy else recent_threads(connection, timeline_id)
        common = {'slot': slot['key'], 'local_date': slot['local_date'], 'timezone': version['timezone'],
                  'post': '', 'mood': ''}
        if due:
            settled = composer.settle_thread(due, version['definition'])
            proposal = EventProposal(
                idempotency_key=settle_key(due['details']['thread_key']), kind='thread', summary=settled['summary'],
                details={**common, 'state': 'settled', 'thread': settled['thread'],
                         'thread_key': due['details']['thread_key']},
                starts_at=slot['starts_at'], ends_at=slot['ends_at'],
                inputs={'run_id': run['id'], 'mode': run['mode'], 'settles': due['id'],
                        'composer_version': settled['composer_version'], 'character_version_id': version['id']})
        elif not busy and (opened := composer.open_thread(version['definition'], key, slot['local_date'], used)):
            thread_key = f"thread:{timeline_id}:{slot['key']}"
            proposal = EventProposal(
                idempotency_key=thread_key, kind='thread', summary=opened['summary'],
                details={**common, 'state': 'open', 'thread': opened['thread'], 'thread_key': thread_key,
                         'settles_on': opened['settles_on']},
                starts_at=slot['starts_at'], ends_at=slot['ends_at'],
                inputs={'run_id': run['id'], 'mode': run['mode'], 'composer_version': opened['composer_version'],
                        'character_version_id': version['id']})
        else:
            return {}
        settled = self.settle(events.propose(self.database, proposal, run['timeline_id']), life)
        return {'thread_event_id': settled['event_id'], 'thread_outcome': settled['outcome']}

    def plan_ahead(self, run, slot, version, life, key) -> dict:
        """At most one plan per event, for an upcoming slot; it waits for review like any event."""
        now = self.now()
        schedule, _default = routine.blocks(version['definition'])
        future = [item.view() for item in routine.slots(schedule, version['timezone'], now + timedelta(days=1),
                                                        now + timedelta(days=7))]
        with self.database.connect() as connection:
            upcoming = {row['slot_key']: decode(row['entry']) if row['entry'] else None for row in many(
                connection, "SELECT slot_key, entry FROM life_agenda WHERE timeline_id=? AND subject=? "
                "AND status='upcoming' AND basis=?", (run['timeline_id'], agenda.COMPANION, version['id']))}
        planned = composer.plan_ahead(version['definition'], self.world, key, future, upcoming)
        if planned is None:
            return {}
        target = planned['target']
        event = events.propose(self.database, EventProposal(
            idempotency_key=f"plan:{run['timeline_id']}:{slot['key']}", kind='plan', summary=planned['summary'],
            details={'target_slot': target['key'], 'label': target['block']['label'], 'activity': planned['activity'],
                     'place': planned['place'], 'with': planned['with'], 'local_date': target['local_date'],
                     'timezone': version['timezone'], 'post': '', 'mood': ''},
            starts_at=target['starts_at'], ends_at=target['ends_at'],
            inputs={'run_id': run['id'], 'mode': run['mode'], 'made_during': slot['key'], 'world': self.world.name,
                    'composer_version': planned['composer_version'], 'character_version_id': version['id']}), run['timeline_id'])
        settled = self.settle(event, life)
        return {'plan_event_id': event['id'], 'plan_outcome': settled['outcome']}

    async def phrase(self, config, life, version, slot, composed, prepared=None) -> tuple[dict, dict]:
        """Template wording unless the user allows model phrasing and a model is connected. Any
        model problem keeps the template wording; only a conversation interrupts the batch. Wording
        prepared earlier for this entry is used when it came from the same model and prompt."""
        template = {'summary': composed['summary'], 'post': composed['post']}
        if config is None or not life['phrase_with_model']:
            return template, {'wording': 'template'}
        record = {'wording': 'model', 'model': config['model'], 'base_url': config['base_url'],
                  'prompt_version': PROMPT_VERSION}
        if prepared and all(prepared.get(key) == record[key] for key in ('model', 'base_url', 'prompt_version')):
            return {'summary': prepared['summary'], 'post': prepared['post']}, {**record, 'prepared': True}
        try:
            return await phrase(self.provider, self.scheduler, config, key_for(self.vault, config), version, slot,
                                composed), record
        except BackgroundInterrupted:
            raise
        except (SynthesisInvalid, DomainError) as problem:
            reason = str(problem) if isinstance(problem, SynthesisInvalid) else problem.message
            return template, {**record, 'wording': 'template', 'phrasing_error': reason}

    def prepare(self) -> dict:
        """Start preparing likely work while the user types or idles (T9), without waiting for it."""
        if self.preparing and not self.preparing.done():
            return {'state': 'in_progress'}
        self.preparing = asyncio.get_running_loop().create_task(self.prepare_now())
        return {'state': 'started'}

    async def prepare_now(self, limit=PREPARE_AHEAD) -> dict:
        """Bring the agenda up to date, then phrase the companion's next few entries at background
        priority. A conversation interrupts this; the rest waits for the next call."""
        with self.database.connect(write=True) as connection:
            companion = current(connection)
            workspace, life = settings(connection), life_settings(connection)
            if companion is None or not may_extend(workspace, 'return'):
                return {'prepared': 0}
            agenda.extend(connection, companion, self.world, self.now())
            config = config_for(connection, 'life')
            version = companion['version']
            due = agenda.unprepared(connection, companion['active_timeline_id'], version['id'], self.now(), limit)
        if config is None or not life['phrase_with_model']:
            return {'prepared': 0}
        key, count = key_for(self.vault, config), 0
        for row in due:
            slot = {'key': row['slot_key'], 'block': row['block'], 'local_date': row['local_date'],
                    'starts_at': row['starts_at'], 'ends_at': row['ends_at']}
            try:
                written = await phrase(self.provider, self.scheduler, config, key, version, slot, row['entry'])
            except BackgroundInterrupted:
                break
            except (SynthesisInvalid, DomainError):
                continue
            with self.database.connect(write=True) as connection:
                agenda.save_prepared(connection, row['id'], {
                    **written, 'model': config['model'], 'base_url': config['base_url'],
                    'prompt_version': PROMPT_VERSION, 'prepared_at': stamp(self.now())})
            count += 1
        return {'prepared': count}

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
            with self.database.connect() as connection:
                background = settings(connection)['background_activity']
            if background:
                await self.quietly_observe()
                await self.quietly_prepare()

    async def quietly_observe(self):
        """Real weather and local events for the companion's city, when the user allowed lookups for their
        simulated day. Fresh results are reused (an hour for weather, twelve for events); never while paused."""
        if self.lookups is None:
            return
        with self.database.connect() as connection:
            if settings(connection)['paused_at'] is not None:
                return
        for category in ('weather', 'local_events'):
            try:
                await self.lookups.run(category, 'companion_city', None, BACKGROUND_LOOKUP_DEADLINE)
            except Exception:  # noqa: BLE001 - the day keeps its typical weather and its own plans.
                pass

    async def quietly_prepare(self):
        try:
            await self.prepare_now()
        except Exception:  # noqa: BLE001 - preparation is optional work.
            pass

    async def quietly(self, mode):
        try:
            await self.reconcile(mode)
        except Exception:  # noqa: BLE001 - one failed tick must not stop later ones.
            pass
