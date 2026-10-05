"""Memory formation: extraction, validation and commit as separate steps (PRD M7).

With automatic memory on, each user message queues one job under the current permission
revision. A job runs after the reply, never in front of it, and commits only if the permission
revision is unchanged at commit time, so turning automatic memory off stops queued work.
Explicitly stated ordinary facts commit directly; sensitive ones wait as suggestions unless the
user allowed sensitive memory. Remember this on a message is deliberate, so it commits what it
finds, sensitive or not. Every step leaves an activity record of identities and reason codes.
"""
import hashlib

from companion.characters import require_current
from companion.clock import parse, stamp
from companion.database import decode, encode, identifier, many, one, optional, settings
from companion.errors import require
from companion.memory import extraction, records

JOB_BATCH = 20
PENDING_LIMIT = 50


def log(connection, timestamp, action, *, memory_id=None, candidate_id=None, message_id=None, detail=None):
    connection.execute('INSERT INTO memory_activity (at, action, memory_id, candidate_id, message_id, detail) '
                       'VALUES (?, ?, ?, ?, ?, ?)', (timestamp, action, memory_id, candidate_id, message_id, detail))


def enqueue(connection, message, timestamp):
    """Called as the user's message is saved; nothing is queued while automatic memory is off."""
    row = settings(connection)
    if row['automatic_memory'] and message['role'] == 'user':
        connection.execute("INSERT OR IGNORE INTO memory_jobs (message_id, permission_revision, status, queued_at) "
                           "VALUES (?, ?, 'queued', ?)", (message['id'], row['permission_revision'], timestamp))


def fingerprint(candidate) -> str:
    text = f'{candidate.layer}|{candidate.subject_key}|{candidate.value.casefold()}|{candidate.plan_status or ""}'
    return hashlib.sha256(text.encode()).hexdigest()


def proposal(candidate, message) -> dict:
    return {'layer': candidate.layer, 'subject': candidate.subject, 'subject_key': candidate.subject_key,
            'value': candidate.value, 'boundary': candidate.boundary, 'sensitive': candidate.sensitive,
            'plan_status': candidate.plan_status, 'stated_at': message['created_at'],
            'applies_from': None if candidate.applies_from is None else stamp(candidate.applies_from),
            'applies_until': None if candidate.applies_until is None else stamp(candidate.applies_until),
            'dates_uncertain': candidate.dates_uncertain, 'target': candidate.target, 'excerpt': candidate.excerpt}


def candidates_for(connection, message) -> list:
    timezone = settings(connection)['user_timezone']
    return extraction.extract(message['text'], parse(message['created_at']), timezone)


def blocked(connection, message) -> str | None:
    if message['redacted_at'] is not None:
        return 'message_deleted'
    if optional(connection, 'SELECT 1 FROM memory_declines WHERE message_id=?', (message['id'],)):
        return 'declined_message'
    return None


def update_plan(connection, companion, fields, timestamp) -> dict | None:
    """"My interview got postponed" changes the open plan it names; with none, nothing is invented."""
    plans = many(connection, "SELECT * FROM memories WHERE companion_id=? AND status='active' AND layer='plan' "
                 "AND plan_status IN ('proposed','agreed','postponed') ORDER BY stated_at DESC", (companion['id'],))
    target = fields['target']
    plan = next((row for row in plans if target == row['subject_key'] or target in row['value'].casefold()), None)
    if plan is None:
        return None
    plan = records.get(connection, plan['id'])
    return records.revise(connection, plan, timestamp, value=plan['value'], plan_status=fields['plan_status'],
                          applies_from=fields['applies_from'], dates_uncertain=fields['dates_uncertain'] or None)


def commit(connection, companion, fields, sources, timestamp, origin, authority='stated') -> tuple[dict | None, str]:
    """Validate against current state and write. Returns (memory, outcome code)."""
    if fields.get('target') and fields['value'] == '':
        memory = update_plan(connection, companion, fields, timestamp)
        return memory, 'plan_updated' if memory else 'no_matching_plan'
    data = {key: value for key, value in fields.items() if key not in {'target', 'excerpt'}}
    memory, created = records.insert(connection, companion, data, now=timestamp, origin=origin, authority=authority,
                                     sources=sources)
    return memory, 'committed' if created else 'duplicate'


def record_candidate(connection, companion, message, candidate, timestamp) -> tuple[str, dict, bool]:
    """Store a candidate once per message; returns (id, fields, new)."""
    mark = fingerprint(candidate)
    existing = optional(connection, 'SELECT * FROM memory_candidates WHERE message_id=? AND fingerprint=?',
                        (message['id'], mark))
    if existing:
        return existing['id'], decode(existing['proposal']), False
    candidate_id, fields = identifier(), proposal(candidate, message)
    declined = optional(connection, "SELECT 1 FROM memory_candidates WHERE fingerprint=? AND status='declined' "
                        'AND companion_id=?', (mark, companion['id']))
    connection.execute(
        'INSERT INTO memory_candidates (id, companion_id, timeline_id, message_id, source, rule, proposal, '
        "fingerprint, status, reason, created_at) VALUES (?, ?, ?, ?, 'rule', ?, ?, ?, ?, ?, ?)",
        (candidate_id, companion['id'], message['timeline_id'], message['id'], candidate.rule, encode(fields), mark,
         'dismissed' if declined else 'pending', 'declined_before' if declined else None, timestamp))
    return candidate_id, fields, not declined


def resolve(connection, candidate_id, status, memory=None, reason=None, timestamp=None):
    connection.execute('UPDATE memory_candidates SET status=?, memory_id=?, reason=COALESCE(?, reason), '
                       'resolved_at=? WHERE id=?',
                       (status, memory and memory['id'], reason, timestamp, candidate_id))


def form(connection, companion, message, timestamp, *, deliberate: bool) -> list[dict]:
    """Extract, validate and commit from one message. Returns the memories written or matched."""
    allowed_sensitive = deliberate or bool(settings(connection)['sensitive_memory'])
    written = []
    for candidate in candidates_for(connection, message):
        candidate_id, fields, new = record_candidate(connection, companion, message, candidate, timestamp)
        if not new and not deliberate:
            continue
        log(connection, timestamp, 'extracted', candidate_id=candidate_id, message_id=message['id'],
            detail=candidate.rule)
        if fields['sensitive'] and not allowed_sensitive:
            resolve(connection, candidate_id, 'pending', reason='sensitive', timestamp=None)
            log(connection, timestamp, 'suggested', candidate_id=candidate_id, message_id=message['id'],
                detail='sensitive')
            continue
        memory, outcome = commit(connection, companion, fields, [message['id']], timestamp,
                                 'user' if deliberate else 'automatic')
        resolve(connection, candidate_id, 'committed' if memory else 'dismissed', memory, outcome, timestamp)
        log(connection, timestamp, outcome, memory_id=memory and memory['id'], candidate_id=candidate_id,
            message_id=message['id'])
        if memory:
            written.append(memory)
    return written


def run_job(connection, job, timestamp):
    row = settings(connection)
    message = one(connection, 'SELECT * FROM messages WHERE id=?', (job['message_id'],))
    companion = require_current(connection)
    if not row['automatic_memory'] or row['permission_revision'] != job['permission_revision']:
        status, reason = 'stale', 'permission_changed'
    elif message['timeline_id'] != companion['active_timeline_id']:
        status, reason = 'skipped', 'inactive_timeline'
    else:
        reason = blocked(connection, message)
        status = 'skipped' if reason else 'done'
    if status == 'done':
        form(connection, companion, message, timestamp, deliberate=False)
    else:
        log(connection, timestamp, f'job_{status}', message_id=message['id'], detail=reason)
    connection.execute('UPDATE memory_jobs SET status=?, error=?, finished_at=? WHERE message_id=?',
                       (status, reason if status != 'done' else None, timestamp, job['message_id']))
    return status


def run_pending(database, limit=JOB_BATCH) -> dict:
    """Process queued jobs oldest first, each in its own transaction so one failure stays contained."""
    counts = {}
    with database.connect() as connection:
        jobs = many(connection, "SELECT * FROM memory_jobs WHERE status='queued' ORDER BY queued_at, message_id "
                    'LIMIT ?', (limit,))
    for job in jobs:
        try:
            with database.connect(write=True) as connection:
                current = one(connection, 'SELECT * FROM memory_jobs WHERE message_id=?', (job['message_id'],))
                status = run_job(connection, current, database.now()) if current['status'] == 'queued' else None
        except Exception as error:  # noqa: BLE001 - a failed extraction leaves the conversation intact.
            status = 'failed'
            with database.connect(write=True) as connection:
                connection.execute("UPDATE memory_jobs SET status='failed', error=?, finished_at=? WHERE message_id=?",
                                   (type(error).__name__, database.now(), job['message_id']))
                log(connection, database.now(), 'job_failed', message_id=job['message_id'])
        if status:
            counts[status] = counts.get(status, 0) + 1
    return {'processed': sum(counts.values()), **counts}


def remember_message(database, message_id) -> dict:
    """Remember this on a user message: commit what the rules find, or offer a draft to fill in."""
    with database.connect(write=True) as connection:
        message = one(connection, 'SELECT * FROM messages WHERE id=?', (message_id,))
        require(message['role'] == 'user', 'Only your own messages can be remembered this way.', 422)
        require(message['redacted_at'] is None, 'This message was deleted.', 409)
        companion = require_current(connection)
        require(message['timeline_id'] == companion['active_timeline_id'], 'This message is on an inactive timeline.',
                409)
        timestamp = database.now()
        if connection.execute('DELETE FROM memory_declines WHERE message_id=?', (message_id,)).rowcount:
            log(connection, timestamp, 'decline_lifted', message_id=message_id)
        memories = form(connection, companion, message, timestamp, deliberate=True)
        draft = None if memories else {'layer': 'shared_experience', 'subject': 'Something you told me',
                                       'value': message['text'][:4000], 'source_message_ids': [message_id]}
        return {'memories': memories, 'draft': draft}


def forget_message(database, message_id) -> dict:
    """Don't remember this: block extraction from the message and remove what was extracted from it
    automatically. The visible transcript stays; deleting it is a separate action (M12)."""
    with database.connect(write=True) as connection:
        message = one(connection, 'SELECT * FROM messages WHERE id=?', (message_id,))
        require(message['role'] == 'user', 'Only your own messages can be marked.', 422)
        timestamp = database.now()
        connection.execute('INSERT OR IGNORE INTO memory_declines (message_id, created_at) VALUES (?, ?)',
                           (message_id, timestamp))
        connection.execute("UPDATE memory_jobs SET status='skipped', error='declined_message', finished_at=? "
                           "WHERE message_id=? AND status='queued'", (timestamp, message_id))
        connection.execute("UPDATE memory_candidates SET status='declined', resolved_at=? WHERE message_id=? "
                           "AND status='pending'", (timestamp, message_id))
        automatic = [row['id'] for row in many(
            connection, "SELECT memories.id FROM memories JOIN memory_sources ON memory_sources.memory_id=memories.id "
            "WHERE memory_sources.message_id=? AND memories.origin='automatic' AND memories.status<>'superseded' "
            'AND NOT EXISTS (SELECT 1 FROM memory_sources other WHERE other.memory_id=memories.id '
            'AND other.message_id<>?)', (message_id, message_id))]
    removed = []
    for memory_id in automatic:
        removed += records.delete(database, memory_id)['deleted_memory_ids']
    with database.connect(write=True) as connection:
        log(connection, database.now(), 'declined_message', message_id=message_id)
    return {'message_id': message_id, 'declined': True, 'removed_memory_ids': sorted(set(removed))}


def suggestion_view(row) -> dict:
    fields = decode(row['proposal'])
    return {'id': row['id'], 'message_id': row['message_id'], 'source': row['source'], 'rule': row['rule'],
            'reason': row['reason'], 'created_at': row['created_at'], **fields}


def suggestions(database) -> list[dict]:
    with database.connect() as connection:
        companion = require_current(connection)
        rows = many(connection, "SELECT * FROM memory_candidates WHERE companion_id=? AND status='pending' "
                    'ORDER BY created_at DESC LIMIT ?', (companion['id'], PENDING_LIMIT))
        return [suggestion_view(row) for row in rows]


def accept(database, candidate_id) -> dict:
    """Accepting is the user's deliberate permission, including for sensitive suggestions."""
    with database.connect(write=True) as connection:
        row = one(connection, 'SELECT * FROM memory_candidates WHERE id=?', (candidate_id,))
        require(row['status'] == 'pending', 'This suggestion was already handled.', 409)
        message = one(connection, 'SELECT * FROM messages WHERE id=?', (row['message_id'],))
        require(blocked(connection, message) is None, 'The message behind this suggestion was deleted or declined.',
                409)
        companion = require_current(connection)
        timestamp = database.now()
        fields = decode(row['proposal'])
        authority = 'confirmed' if row['source'] == 'model' else 'stated'
        memory, outcome = commit(connection, companion, fields, [message['id']], timestamp, 'suggestion', authority)
        resolve(connection, candidate_id, 'committed' if memory else 'dismissed', memory, outcome, timestamp)
        log(connection, timestamp, 'accepted', memory_id=memory and memory['id'], candidate_id=candidate_id,
            message_id=message['id'], detail=outcome)
        return {'memory': memory, 'outcome': outcome}


def decline(database, candidate_id) -> dict:
    """A declined suggestion is not offered again, from this message or any later one."""
    with database.connect(write=True) as connection:
        row = one(connection, 'SELECT * FROM memory_candidates WHERE id=?', (candidate_id,))
        require(row['status'] == 'pending', 'This suggestion was already handled.', 409)
        timestamp = database.now()
        resolve(connection, candidate_id, 'declined', timestamp=timestamp)
        log(connection, timestamp, 'declined', candidate_id=candidate_id, message_id=row['message_id'])
        return {'id': candidate_id, 'status': 'declined'}


def activity(database, limit=100) -> list[dict]:
    with database.connect() as connection:
        return many(connection, 'SELECT * FROM memory_activity ORDER BY id DESC LIMIT ?', (limit,))


def status(database) -> dict:
    with database.connect() as connection:
        counts = {row['status']: row['count'] for row in many(
            connection, 'SELECT status, COUNT(*) AS count FROM memory_jobs GROUP BY status')}
        pending = one(connection, "SELECT COUNT(*) AS count FROM memory_candidates WHERE status='pending'")['count']
        return {'automatic_memory': bool(settings(connection)['automatic_memory']), 'jobs': counts,
                'suggestions': pending}
