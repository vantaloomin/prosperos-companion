"""Image jobs (PRD F3, F4, F6).

A job freezes its inputs, its classification and the reason it was routed where it was. The
post records which job is current. A result only lands on the post while its job is still
current, so a late result never overwrites a newer selection; it stays a version the user can
pick. A refused request is recorded as a failed job, so the post shows why.
"""
from datetime import timedelta

from companion.clock import parse, stamp
from companion.database import decode, encode, identifier, many, one, optional, settings
from companion.errors import DomainError, require
from companion.images import backends, prompts
from companion.images.content import NSFW, classify
from companion.images.routing import route
from companion.life import feed

ACTIVE = ('queued', 'running')
FINISHED = ('completed', 'failed', 'cancelled', 'interrupted')
SETTING_FLAGS = ('automatic_images', 'fallback')


def settings_view(row) -> dict:
    return {**row, **{flag: bool(row[flag]) for flag in SETTING_FLAGS}}


def image_settings(connection) -> dict:
    return one(connection, 'SELECT * FROM image_settings WHERE id=1')


def read_settings(database) -> dict:
    with database.connect() as connection:
        return settings_view(image_settings(connection))


def update_settings(database, body) -> dict:
    changes = body.model_dump(exclude_none=True)
    with database.connect(write=True) as connection:
        row = image_settings(connection)
        timestamp = database.now()
        if changes.get('automatic_images') and not row['automatic_images']:
            # The cadence covers posts from now on; it never backfills older ones (T5).
            changes['automatic_since'] = timestamp
        assignments = {**{key: int(value) if isinstance(value, bool) else value for key, value in changes.items()},
                       'updated_at': timestamp}
        columns = ', '.join(f'{key}=?' for key in assignments)
        connection.execute(f'UPDATE image_settings SET {columns} WHERE id=1', tuple(assignments.values()))
        return settings_view(image_settings(connection))


def view(connection, job) -> dict:
    inputs = decode(job['inputs'])
    post = optional(connection, 'SELECT image_job_id, status FROM feed_posts WHERE id=?', (job['post_id'],))
    backend = optional(connection, 'SELECT label, blocked_reason FROM image_backends WHERE id=?',
                       (job['backend_id'],)) if job['backend_id'] else None
    waiting = backend['blocked_reason'] if backend and job['status'] == 'queued' else None
    return {'id': job['id'], 'post_id': job['post_id'], 'status': job['status'], 'trigger': job['trigger'],
            'retry_of': job['retry_of'], 'classification': job['classification'],
            'classification_reasons': decode(job['classification_reasons']), 'classifier': job['classifier'],
            'routing_reason': job['routing_reason'], 'backend_id': job['backend_id'],
            'backend_label': backend['label'] if backend else None, 'backend_kind': job['backend_kind'],
            'provider': job['provider'], 'model': job['model'], 'workflow': job['workflow'],
            'identity_method': job['identity_method'], 'seed': job['seed'], 'width': job['width'],
            'height': job['height'], 'usage': decode(job['usage']), 'error': job['error'],
            'error_code': job['error_code'], 'waiting_for': waiting, 'has_image': job['output_file'] is not None,
            'prompt': inputs['prompt'], 'negative': inputs['negative'], 'aspect': inputs['aspect'],
            'character_version_id': job['character_version_id'], 'marked_nsfw': inputs.get('marked_nsfw', False),
            'current': bool(post and post['image_job_id'] == job['id']),
            'retry_original_available': not prompts.stale(connection, inputs),
            'created_at': job['created_at'], 'started_at': job['started_at'], 'finished_at': job['finished_at']}


def get(database, job_id) -> dict:
    with database.connect() as connection:
        return view(connection, one(connection, 'SELECT * FROM image_jobs WHERE id=?', (job_id,)))


def for_post(database, post_id) -> list[dict]:
    """Every request for a post, newest first: the current image, earlier versions and failures."""
    with database.connect() as connection:
        one(connection, 'SELECT id FROM feed_posts WHERE id=?', (post_id,))
        return [view(connection, job) for job in many(connection, 'SELECT * FROM image_jobs WHERE post_id=? '
                                                      'ORDER BY created_at DESC, rowid DESC', (post_id,))]


def preview(database, post_id, marked_nsfw=False) -> dict:
    """What a request would send and where it would go, without queuing anything."""
    with database.connect() as connection:
        inputs = prompts.build(connection, post_id, image_settings(connection), marked_nsfw)
        classification = classify(inputs)
        decision = route(classification, backends.ordered(connection, enabled_only=True))
        return {'prompt': inputs['prompt'], 'negative': inputs['negative'], 'classification': classification.view(),
                'backends': [backend['id'] for backend in decision.backends], 'routing_reason': decision.reason,
                'refusal': decision.refusal}


def enqueue(database, post_id, trigger, *, backend_id=None, marked_nsfw=False, inputs=None, retry_of=None,
            after_id=None) -> dict:
    """Classify, route and queue one request. A refusal is stored as a failed job and returned;
    it never reaches a backend."""
    with database.connect(write=True) as connection:
        current = image_settings(connection)
        active = one(connection, "SELECT COUNT(*) AS n FROM image_jobs WHERE status IN ('queued', 'running')")['n']
        require(active < current['queue_limit'] or trigger == 'fallback',
                f"{active} images are already waiting. Let them finish or cancel some first.", 409)
        inputs = inputs or prompts.build(connection, post_id, current, marked_nsfw)
        classification = classify(inputs)
        decision = route(classification, backends.ordered(connection, enabled_only=True), backend_id, after_id)
        job_id = insert(connection, database.now(), post_id, trigger, retry_of, inputs, classification, decision)
        return view(connection, one(connection, 'SELECT * FROM image_jobs WHERE id=?', (job_id,)))


def insert(connection, timestamp, post_id, trigger, retry_of, inputs, classification, decision) -> str:
    job_id = identifier()
    post = one(connection, 'SELECT timeline_id FROM feed_posts WHERE id=?', (post_id,))
    target = decision.target
    status = 'failed' if decision.refusal else 'queued'
    connection.execute(
        'INSERT INTO image_jobs (id, post_id, timeline_id, status, trigger, retry_of, inputs, character_version_id, '
        'classification, classification_reasons, classifier, routing_reason, backend_id, backend_kind, provider, '
        'error, error_code, created_at, finished_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (job_id, post_id, post['timeline_id'], status, trigger, retry_of, encode(inputs),
         inputs['character_version_id'], classification.tier, encode(classification.reasons),
         classification.classifier, decision.reason, target and target['id'], target and target['kind'],
         target and target['provider'], decision.refusal, decision.code, timestamp,
         timestamp if decision.refusal else None))
    feed.apply_image(connection, post_id, job_id, status, timestamp, error=decision.refusal, replace=True)
    return job_id


def retry(database, job_id, current_settings=False, backend_id=None) -> dict:
    """Retry keeps the original inputs; choosing current settings or another backend rebuilds
    them (F4, F5). Either way the request is classified again before dispatch (F6)."""
    with database.connect() as connection:
        job = one(connection, 'SELECT * FROM image_jobs WHERE id=?', (job_id,))
        inputs = decode(job['inputs'])
        stale = prompts.stale(connection, inputs)
    require(job['status'] not in ACTIVE, 'This image is still being made.', 409)
    if backend_id and backend_id != job['backend_id']:
        current_settings = True
    if current_settings:
        return enqueue(database, job['post_id'], 'retry', backend_id=backend_id, retry_of=job_id,
                       marked_nsfw=inputs.get('marked_nsfw', False))
    if stale:
        raise DomainError('The event changed after this image was requested, so the original request no longer '
                          'matches it. Retry with current settings instead.', 409, 'stale_inputs')
    return enqueue(database, job['post_id'], 'retry', backend_id=job['backend_id'], inputs=inputs, retry_of=job_id)


def select(database, job_id) -> dict:
    """Make a finished version the post's image. A job still running for the post then lands as
    another version instead of replacing this choice."""
    with database.connect(write=True) as connection:
        job = one(connection, 'SELECT * FROM image_jobs WHERE id=?', (job_id,))
        require(job['status'] == 'completed' and job['output_file'], 'Only a finished image can be chosen.', 409)
        applied = feed.apply_image(connection, job['post_id'], job_id, 'completed', database.now(), ref=job_id,
                                   replace=True)
        require(applied, 'This post was removed.', 409)
        return feed.post_view(connection, one(connection, 'SELECT * FROM feed_posts WHERE id=?', (job['post_id'],)))


def finish(database, job_id, status, *, error=None, code=None, fields=None) -> bool:
    """Close a job and, while it is current, its post. Returns whether the job was still open."""
    with database.connect(write=True) as connection:
        job = one(connection, 'SELECT * FROM image_jobs WHERE id=?', (job_id,))
        if job['status'] not in ACTIVE:
            return False
        timestamp = database.now()
        assignments = {'status': status, 'error': error, 'error_code': code, 'finished_at': timestamp,
                       **(fields or {})}
        columns = ', '.join(f'{key}=?' for key in assignments)
        connection.execute(f'UPDATE image_jobs SET {columns} WHERE id=?', (*assignments.values(), job_id))
        ref = job_id if status == 'completed' else None
        feed.apply_image(connection, job['post_id'], job_id, status, timestamp, ref=ref, error=error)
        return True


def reclassify_refused(database, job_id, reasons):
    """A hosted provider's own refusal makes the request NSFW from then on (F6)."""
    with database.connect(write=True) as connection:
        job = one(connection, 'SELECT * FROM image_jobs WHERE id=?', (job_id,))
        inputs = {**decode(job['inputs']), 'marked_nsfw': True}
        connection.execute('UPDATE image_jobs SET classification=?, classification_reasons=?, inputs=? WHERE id=?',
                           (NSFW, encode([*decode(job['classification_reasons']), *reasons]), encode(inputs),
                            job_id))
        return inputs


def is_current(database, job_id) -> bool:
    with database.connect() as connection:
        job = one(connection, 'SELECT post_id FROM image_jobs WHERE id=?', (job_id,))
        post = one(connection, 'SELECT image_job_id FROM feed_posts WHERE id=?', (job['post_id'],))
        return post['image_job_id'] == job_id


def cancel_queued(database, job_id) -> bool:
    return finish(database, job_id, 'cancelled', error='Cancelled before it started.', code='cancelled') \
        if status_of(database, job_id) == 'queued' else False


def status_of(database, job_id) -> str:
    with database.connect() as connection:
        return one(connection, 'SELECT status FROM image_jobs WHERE id=?', (job_id,))['status']


def recover(database):
    """Nothing resumes by itself after a restart: queued and running jobs become interrupted and
    the user can retry them."""
    with database.connect(write=True) as connection:
        timestamp = database.now()
        for job in many(connection, "SELECT id, post_id, status FROM image_jobs WHERE status IN ('queued', 'running')"):
            message = 'The app closed before this image was made.' if job['status'] == 'queued' else \
                'The app closed while this image was being made; any result was discarded.'
            connection.execute("UPDATE image_jobs SET status='interrupted', error=?, error_code='interrupted', "
                               'finished_at=? WHERE id=?', (message, timestamp, job['id']))
            feed.apply_image(connection, job['post_id'], job['id'], 'interrupted', timestamp, error=message)


def automatic_candidate(database) -> str | None:
    """The next post the automatic cadence may illustrate, if any (F3). It needs the cadence and
    background activity on, no pause, room under the daily limit, and covers only single-event
    posts made since the cadence was turned on: catch-up digests never get images (T5)."""
    with database.connect() as connection:
        current, workspace = image_settings(connection), settings(connection)
        if not current['automatic_images'] or not workspace['background_activity'] or workspace['paused_at']:
            return None
        since = stamp(parse(database.now()) - timedelta(days=1))
        used = one(connection, "SELECT COUNT(*) AS n FROM image_jobs WHERE trigger='automatic' AND created_at>=?",
                   (since,))['n']
        if used >= current['daily_limit']:
            return None
        companion = optional(connection, 'SELECT active_timeline_id FROM companions WHERE slot=1')
        if companion is None:
            return None
        rows = many(connection, "SELECT * FROM feed_posts WHERE timeline_id=? AND kind='event' AND status='visible' "
                    "AND image_status='none' AND created_at>? ORDER BY occurs_at DESC",
                    (companion['active_timeline_id'], current['automatic_since']))
        return next((row['id'] for row in rows if feed.post_view(connection, row)), None)


def routable(database, inputs, after_id=None) -> bool:
    with database.connect() as connection:
        return route(classify(inputs), backends.ordered(connection, enabled_only=True), after_id=after_id).target \
            is not None
