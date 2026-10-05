"""Committed fictional events: the single shared account for chat, feed and recall (PRD T2–T3, T7, F1).

A proposal records the character version, timeline and permission revision it was made under.
Commit revalidates all three, so work that finishes after a pause, correction or timeline switch
cannot affect the active companion. The idempotency key makes a repeated commit a no-op.
"""
from companion.characters import require_current
from companion.clock import parse, stamp
from companion.database import bump_memory_revision, decode, encode, identifier, many, one, optional, settings
from companion.errors import require
from companion.workspace import overlapping_pause


def view(row: dict) -> dict:
    return {**row, 'details': decode(row['details']), 'inputs': decode(row['inputs'])}


def propose(database, body) -> dict:
    starts_at, ends_at = stamp(parse(body.starts_at)), stamp(parse(body.ends_at))
    require(starts_at <= ends_at, 'An event must end after it starts.', 422)
    with database.connect(write=True) as connection:
        existing = optional(connection, 'SELECT * FROM life_events WHERE idempotency_key=?', (body.idempotency_key,))
        if existing:
            return view(existing)
        companion = require_current(connection)
        event_id = identifier()
        connection.execute(
            'INSERT INTO life_events (id, companion_id, timeline_id, idempotency_key, kind, status, summary, details, '
            "starts_at, ends_at, character_version_id, permission_revision, inputs, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'proposed', ?, ?, ?, ?, ?, ?, ?, ?)",
            (event_id, companion['id'], companion['active_timeline_id'], body.idempotency_key, body.kind,
             body.summary, encode(body.details), starts_at, ends_at, companion['active_version_id'],
             settings(connection)['permission_revision'], encode(body.inputs), database.now()))
        return view(one(connection, 'SELECT * FROM life_events WHERE id=?', (event_id,)))


def stale_reason(connection, event, companion, now) -> str | None:
    workspace = settings(connection)
    checks = (
        (workspace['paused_at'] is not None, 'Activity is paused.'),
        (event['timeline_id'] != companion['active_timeline_id'], 'The event belongs to an inactive timeline.'),
        (event['character_version_id'] != companion['active_version_id'],
         'The character changed after this event was prepared.'),
        (event['permission_revision'] != workspace['permission_revision'],
         'Activity permissions changed after this event was prepared.'),
        (event['kind'] != 'plan' and event['ends_at'] > now, 'An event cannot be completed before it ends.'),
        (overlapping_pause(connection, event['starts_at'], event['ends_at']) is not None,
         'The event falls inside a paused interval.'),
    )
    return next((message for failed, message in checks if failed), None)


def commit(database, event_id) -> dict:
    with database.connect(write=True) as connection:
        event = one(connection, 'SELECT * FROM life_events WHERE id=?', (event_id,))
        if event['status'] != 'proposed':
            require(event['status'] in {'committed', 'superseded'}, 'This event was rejected.', 409)
            return view(event)
        timestamp = database.now()
        reason = stale_reason(connection, event, require_current(connection), timestamp)
        status = 'rejected' if reason else 'committed'
        connection.execute('UPDATE life_events SET status=?, rejection=?, decided_at=? WHERE id=?',
                           (status, reason, timestamp, event_id))
        return view(one(connection, 'SELECT * FROM life_events WHERE id=?', (event_id,)))


def reject(database, event_id) -> dict:
    with database.connect(write=True) as connection:
        event = one(connection, 'SELECT * FROM life_events WHERE id=?', (event_id,))
        require(event['status'] in {'proposed', 'rejected'}, 'Only a proposed event can be rejected.', 409)
        connection.execute("UPDATE life_events SET status='rejected', rejection=COALESCE(rejection, ?), "
                           'decided_at=COALESCE(decided_at, ?) WHERE id=?',
                           ('Rejected by the user.', database.now(), event_id))
        return view(one(connection, 'SELECT * FROM life_events WHERE id=?', (event_id,)))


def correct(database, event_id, body) -> dict:
    """A correction becomes the active account; the earlier version stays recoverable (PRD Returning)."""
    with database.connect(write=True) as connection:
        event = one(connection, 'SELECT * FROM life_events WHERE id=?', (event_id,))
        require(event['status'] == 'committed', 'Only the active version of a committed event can be corrected.', 409)
        timestamp, new_id = database.now(), identifier()
        revision = event['revision'] + 1
        connection.execute("UPDATE life_events SET status='superseded' WHERE id=?", (event_id,))
        connection.execute(
            'INSERT INTO life_events (id, companion_id, timeline_id, idempotency_key, kind, status, summary, details, '
            'starts_at, ends_at, character_version_id, permission_revision, inputs, revision, supersedes_id, '
            "created_at, decided_at) VALUES (?, ?, ?, ?, ?, 'committed', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id, event['companion_id'], event['timeline_id'], f"{event['idempotency_key']}#r{revision}",
             event['kind'], body.summary, encode(body.details), event['starts_at'], event['ends_at'],
             event['character_version_id'], event['permission_revision'], event['inputs'], revision, event_id,
             timestamp, timestamp))
        bump_memory_revision(connection, timestamp)
        return view(one(connection, 'SELECT * FROM life_events WHERE id=?', (new_id,)))


def listing(database, include_history=False) -> list[dict]:
    with database.connect() as connection:
        companion = require_current(connection)
        statuses = "('proposed','committed','rejected','superseded')" if include_history else "('committed')"
        return [view(row) for row in many(
            connection, f'SELECT * FROM life_events WHERE timeline_id=? AND status IN {statuses} '
            'ORDER BY starts_at, created_at', (companion['active_timeline_id'],))]


def committed(connection, timeline_id) -> list[dict]:
    return many(connection, "SELECT * FROM life_events WHERE timeline_id=? AND status='committed' "
                'ORDER BY starts_at', (timeline_id,))
