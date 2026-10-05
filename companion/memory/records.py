"""Typed, scoped personal memories with supersession, exclusion and deletion (PRD M6–M12).

Every change advances the workspace memory revision so in-flight replies built from an older
revision are withheld instead of reaching the active conversation (M9).
"""
from companion.characters import require_current
from companion.clock import parse, stamp
from companion.database import bump_memory_revision, identifier, many, one, optional, settings
from companion.errors import require

OPEN_PLANS = ('proposed', 'agreed', 'postponed')


def normalized_time(value):
    return None if value is None else stamp(parse(value))


def with_sources(connection, row: dict) -> dict:
    sources = [item['message_id'] for item in many(
        connection, 'SELECT message_id FROM memory_sources WHERE memory_id=? ORDER BY message_id', (row['id'],))]
    return {**row, 'boundary': bool(row['boundary']), 'pinned': bool(row['pinned']),
            'sensitive': bool(row['sensitive']), 'source_message_ids': sources}


def get(connection, memory_id) -> dict:
    return with_sources(connection, one(connection, 'SELECT * FROM memories WHERE id=?', (memory_id,)))


def validate_sources(connection, timeline_id, message_ids):
    for message_id in message_ids:
        message = one(connection, 'SELECT * FROM messages WHERE id=?', (message_id,))
        require(message['timeline_id'] == timeline_id, 'A source message belongs to another timeline.', 422)
        require(message['redacted_at'] is None, 'A source message was deleted.', 422)
        declined = optional(connection, 'SELECT 1 FROM memory_declines WHERE message_id=?', (message_id,))
        require(declined is None, 'You asked not to remember that message.', 409)


def remember(database, body) -> dict:
    """Direct Remember this. Automatic extraction is a separate, permission-checked path."""
    require((body.layer == 'companion_life') == (body.reality == 'fiction'),
            'Only companion-life memories are fictional; personal memories describe real life.', 422)
    require(body.plan_status is None or body.layer == 'plan', 'Only plans have a plan status.', 422)
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        timeline_id = companion['active_timeline_id']
        validate_sources(connection, timeline_id, body.source_message_ids)
        duplicate = optional(connection, "SELECT * FROM memories WHERE companion_id=? AND status='active' AND layer=? "
                             'AND subject=? AND value=? AND timeline_id=?',
                             (companion['id'], body.layer, body.subject, body.value, timeline_id))
        if duplicate:
            return with_sources(connection, duplicate)
        timestamp, memory_id = database.now(), identifier()
        plan_status = body.plan_status or ('proposed' if body.layer == 'plan' else None)
        connection.execute(
            'INSERT INTO memories (id, companion_id, timeline_id, layer, subject, value, reality, authority, status, '
            'boundary, sensitive, plan_status, stated_at, applies_from, applies_until, created_at, updated_at) '
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?, ?, ?)",
            (memory_id, companion['id'], timeline_id, body.layer, body.subject, body.value, body.reality,
             'tentative' if body.tentative else 'stated', int(body.boundary), int(body.sensitive), plan_status,
             timestamp, normalized_time(body.applies_from), normalized_time(body.applies_until),
             timestamp, timestamp))
        connection.executemany('INSERT INTO memory_sources (memory_id, message_id) VALUES (?, ?)',
                               [(memory_id, message_id) for message_id in body.source_message_ids])
        bump_memory_revision(connection, timestamp)
        return get(connection, memory_id)


def confirm(database, memory_id) -> dict:
    with database.connect(write=True) as connection:
        memory = get(connection, memory_id)
        require(memory['status'] == 'active', 'Only an active memory can be confirmed.', 409)
        if memory['authority'] == 'tentative':
            timestamp = database.now()
            connection.execute("UPDATE memories SET authority='confirmed', updated_at=? WHERE id=?",
                               (timestamp, memory_id))
            bump_memory_revision(connection, timestamp)
        return get(connection, memory_id)


def correct(database, memory_id, body) -> dict:
    """The correction supersedes the old value atomically; the old value stays as history."""
    with database.connect(write=True) as connection:
        memory = get(connection, memory_id)
        require(memory['status'] == 'active', 'Only the current value of a memory can be corrected.', 409)
        require(memory['revision'] == body.expected_revision,
                'This memory changed since you opened it. Review the latest value.', 409)
        require(body.plan_status is None or memory['layer'] == 'plan', 'Only plans have a plan status.', 422)
        timestamp, new_id = database.now(), identifier()
        connection.execute("UPDATE memories SET status='superseded', updated_at=? WHERE id=?", (timestamp, memory_id))
        connection.execute(
            'INSERT INTO memories (id, companion_id, timeline_id, layer, subject, value, reality, authority, status, '
            'boundary, pinned, sensitive, plan_status, event_id, stated_at, applies_from, applies_until, revision, '
            "supersedes_id, created_at, updated_at) SELECT ?, companion_id, timeline_id, layer, subject, ?, reality, "
            "'stated', 'active', boundary, pinned, sensitive, ?, event_id, ?, ?, ?, revision+1, id, ?, ? "
            'FROM memories WHERE id=?',
            (new_id, body.value, body.plan_status or memory['plan_status'], timestamp,
             normalized_time(body.applies_from) or memory['applies_from'],
             normalized_time(body.applies_until) if body.applies_until else memory['applies_until'],
             timestamp, timestamp, memory_id))
        connection.execute('INSERT INTO memory_sources (memory_id, message_id) '
                           'SELECT ?, message_id FROM memory_sources WHERE memory_id=?', (new_id, memory_id))
        bump_memory_revision(connection, timestamp)
        return get(connection, new_id)


def set_flag(database, memory_id, *, status=None, pinned=None) -> dict:
    with database.connect(write=True) as connection:
        memory = get(connection, memory_id)
        require(memory['status'] in {'active', 'excluded'}, 'A superseded memory cannot be changed.', 409)
        timestamp = database.now()
        connection.execute('UPDATE memories SET status=COALESCE(?, status), pinned=COALESCE(?, pinned), updated_at=? '
                           'WHERE id=?', (status, None if pinned is None else int(pinned), timestamp, memory_id))
        bump_memory_revision(connection, timestamp)
        return get(connection, memory_id)


def chain(connection, memory_id) -> list[str]:
    """Every version linked to this memory, so deletion cannot leave history readable."""
    found, frontier = set(), [memory_id]
    while frontier:
        current = frontier.pop()
        if current in found:
            continue
        found.add(current)
        row = one(connection, 'SELECT supersedes_id FROM memories WHERE id=?', (current,))
        frontier += [row['supersedes_id']] if row['supersedes_id'] else []
        frontier += [item['id'] for item in many(connection, 'SELECT id FROM memories WHERE supersedes_id=?',
                                                 (current,))]
    return sorted(found)


def delete(database, memory_id, delete_sources=False) -> dict:
    with database.connect(write=True) as connection:
        get(connection, memory_id)
        versions = chain(connection, memory_id)
        marks = ','.join('?' * len(versions))
        sources = sorted({row['message_id'] for row in many(
            connection, f'SELECT message_id FROM memory_sources WHERE memory_id IN ({marks})', versions)})
        timestamp = database.now()
        connection.execute(f'UPDATE memories SET supersedes_id=NULL WHERE supersedes_id IN ({marks})', versions)
        connection.execute(f'DELETE FROM memories WHERE id IN ({marks})', versions)
        markers = [(identity, 'memory', timestamp) for identity in versions]
        if delete_sources:
            redact_messages(connection, sources, timestamp)
            markers += [(identity, 'message', timestamp) for identity in sources]
        connection.executemany('INSERT OR IGNORE INTO deletion_markers (target_id, kind, deleted_at) VALUES (?, ?, ?)',
                               markers)
        bump_memory_revision(connection, timestamp)
        return {'deleted_memory_ids': versions, 'redacted_message_ids': sources if delete_sources else [],
                'linked_memory_ids': linked_memories(connection, sources)}


def redact_messages(connection, message_ids, timestamp):
    connection.executemany("UPDATE messages SET text='', receipt=NULL, redacted_at=? WHERE id=?",
                           [(timestamp, identity) for identity in message_ids])


def linked_memories(connection, message_ids) -> list[str]:
    if not message_ids:
        return []
    marks = ','.join('?' * len(message_ids))
    return [row['memory_id'] for row in many(
        connection, f'SELECT DISTINCT memory_id FROM memory_sources WHERE message_id IN ({marks}) '
        'ORDER BY memory_id', message_ids)]


def decline(database, message_id) -> dict:
    """Don't remember this: blocks structured extraction; the transcript itself stays visible."""
    with database.connect(write=True) as connection:
        message = one(connection, 'SELECT * FROM messages WHERE id=?', (message_id,))
        require(message['role'] == 'user', 'Only your own messages can be marked.', 422)
        connection.execute('INSERT OR IGNORE INTO memory_declines (message_id, created_at) VALUES (?, ?)',
                           (message_id, database.now()))
        return {'message_id': message_id, 'declined': True}


def listing(database, include_history=False) -> list[dict]:
    with database.connect() as connection:
        companion = require_current(connection)
        statuses = "('active','excluded','superseded')" if include_history else "('active','excluded')"
        rows = many(connection, f'SELECT * FROM memories WHERE companion_id=? AND status IN {statuses} '
                    'ORDER BY layer, subject, revision', (companion['id'],))
        return [with_sources(connection, row) for row in rows]


def in_scope(memory, timeline_id, share_profile) -> bool:
    if memory['reality'] == 'fiction' or not share_profile:
        return memory['timeline_id'] == timeline_id
    return True


def current_at(memory, now) -> bool:
    started = memory['applies_from'] is None or memory['applies_from'] <= now
    ended = memory['applies_until'] is not None and memory['applies_until'] < now
    return started and not ended


def eligible(connection, companion, timeline_id, now) -> list[dict]:
    """Authority, scope, exclusion and time rules applied before any ranking (M10)."""
    share = bool(settings(connection)['share_profile_across_timelines'])
    rows = many(connection, "SELECT * FROM memories WHERE companion_id=? AND status='active' "
                "AND authority IN ('stated','confirmed') AND COALESCE(plan_status, '') != 'cancelled'",
                (companion['id'],))
    return [with_sources(connection, row) for row in rows
            if in_scope(row, timeline_id, share) and current_at(row, now)]


def blocked_messages(connection, companion_id) -> set[str]:
    """Source messages of excluded memories are blocked from raw transcript recall too (M12)."""
    return {row['message_id'] for row in many(
        connection, 'SELECT memory_sources.message_id FROM memory_sources JOIN memories '
        "ON memories.id=memory_sources.memory_id WHERE memories.companion_id=? AND memories.status='excluded'",
        (companion_id,))}
