"""Saved conversation with idempotent sends, visible incomplete replies and alternatives (PRD C2, C4, M9).

A reply only becomes the active response when it completed against the memory revision and
character version it was built from. Otherwise it is kept as `withheld` so a correction made
while it was generating can never be contradicted by the stale reply.
"""
import asyncio

from companion.characters import require_current
from companion.database import encode, identifier, many, one, optional, settings
from companion.errors import DomainError, require
from companion.memory import context
from companion.providers.chat import INCOMPLETE, ChatProvider
from companion.providers.scheduling import CONVERSATION, RequestScheduler
from companion.providers.urls import validate_compatible_url
from companion.providers.vault import credential_for

CREDENTIAL_REF = 'text-connection'


def connection_view(row: dict | None) -> dict | None:
    if row is None:
        return None
    return {key: value for key, value in row.items() if key != 'credential_ref'} | {
        'has_key': bool(row['credential_ref'])}


def read_connection(database) -> dict | None:
    with database.connect() as connection:
        return connection_view(optional(connection, 'SELECT * FROM connection WHERE id=1'))


def save_connection(database, vault, body) -> dict:
    """Saving never contacts, loads or downloads a model."""
    base_url = body.base_url.rstrip('/')
    validate_compatible_url(base_url)
    reference = None
    if body.api_key:
        vault.put(CREDENTIAL_REF, body.api_key)
        reference = CREDENTIAL_REF
    with database.connect(write=True) as connection:
        previous = optional(connection, 'SELECT credential_ref FROM connection WHERE id=1')
        reference = reference or (previous or {}).get('credential_ref')
        connection.execute(
            'INSERT INTO connection (id, base_url, model, credential_ref, max_output_tokens, context_tokens, '
            'timeout_seconds, updated_at) VALUES (1, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET '
            'base_url=excluded.base_url, model=excluded.model, credential_ref=excluded.credential_ref, '
            'max_output_tokens=excluded.max_output_tokens, context_tokens=excluded.context_tokens, '
            'timeout_seconds=excluded.timeout_seconds, updated_at=excluded.updated_at',
            (base_url, body.model, reference, body.max_output_tokens, body.context_tokens, body.timeout_seconds,
             database.now()))
        return connection_view(one(connection, 'SELECT * FROM connection WHERE id=1'))


def next_seq(connection, timeline_id) -> int:
    return one(connection, 'SELECT COALESCE(MAX(seq), 0) + 1 AS seq FROM messages WHERE timeline_id=?',
               (timeline_id,))['seq']


def record_user(database, body) -> dict:
    """Saving the user's text comes first and is idempotent on client_id (no duplicate on retry)."""
    with database.connect(write=True) as connection:
        existing = optional(connection, 'SELECT * FROM messages WHERE client_id=?', (body.client_id,))
        if existing:
            return existing
        companion = require_current(connection)
        timeline_id, message_id = companion['active_timeline_id'], identifier()
        connection.execute(
            'INSERT INTO messages (id, timeline_id, seq, role, text, client_id, status, character_version_id, '
            "created_at, completed_at) VALUES (?, ?, ?, 'user', ?, ?, 'complete', ?, ?, ?)",
            (message_id, timeline_id, next_seq(connection, timeline_id), body.text, body.client_id,
             companion['active_version_id'], database.now(), database.now()))
        return one(connection, 'SELECT * FROM messages WHERE id=?', (message_id,))


def active_reply(connection, user_message_id) -> dict | None:
    return optional(connection, "SELECT * FROM messages WHERE reply_to=? AND active=1 AND status='complete'",
                    (user_message_id,))


def latest_user_message(connection, timeline_id) -> dict | None:
    return optional(connection, "SELECT * FROM messages WHERE timeline_id=? AND role='user' "
                    'ORDER BY seq DESC LIMIT 1', (timeline_id,))


def history(database, before_seq=None, limit=100) -> dict:
    with database.connect() as connection:
        companion = require_current(connection)
        rows = many(connection, 'SELECT * FROM messages WHERE timeline_id=? AND seq<? ORDER BY seq DESC LIMIT ?',
                    (companion['active_timeline_id'], before_seq or 2 ** 62, limit))
        return {'timeline_id': companion['active_timeline_id'], 'messages': [message_view(row) for row in reversed(rows)]}


def message_view(row: dict) -> dict:
    return {key: value for key, value in row.items() if key not in {'receipt', 'client_id'}} | {
        'active': bool(row['active']), 'redacted': row['redacted_at'] is not None}


def recover(database):
    """A reply interrupted by a crash stays visibly incomplete; it never becomes the active response."""
    with database.connect(write=True) as connection:
        connection.execute("UPDATE messages SET status='incomplete', active=0, error=COALESCE(error, ?), "
                           "completed_at=COALESCE(completed_at, ?) WHERE status='streaming'",
                           ('The app closed before this reply finished.', database.now()))


class Conversation:
    def __init__(self, database, vault, provider=None, scheduler=None):
        self.database = database
        self.vault = vault
        self.provider = provider or ChatProvider()
        self.scheduler = scheduler or RequestScheduler()
        self.running: dict[str, asyncio.Task] = {}

    async def send(self, body) -> dict:
        user = record_user(self.database, body)
        with self.database.connect() as connection:
            reply = active_reply(connection, user['id'])
        if reply:
            return {'message': message_view(user), 'reply': message_view(reply), 'connection': 'ready'}
        return await self.respond(user)

    async def alternative(self, user_message_id) -> dict:
        with self.database.connect() as connection:
            user = one(connection, "SELECT * FROM messages WHERE id=? AND role='user'", (user_message_id,))
            latest = latest_user_message(connection, user['timeline_id'])
            require(latest['id'] == user['id'], 'Alternatives are available for the latest message only.', 409)
        return await self.respond(user)

    def stop(self, attempt_id) -> bool:
        task = self.running.get(attempt_id)
        if task is None:
            return False
        task.cancel()
        return True

    async def respond(self, user) -> dict:
        prepared = self.prepare(user)
        if prepared['connection'] != 'ready':
            return {'message': message_view(user), 'reply': None, 'connection': prepared['connection']}
        task = asyncio.create_task(self.generate(prepared))
        self.running[prepared['attempt_id']] = task
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            if not task.done():
                raise
        finally:
            self.running.pop(prepared['attempt_id'], None)
        with self.database.connect() as connection:
            reply = one(connection, 'SELECT * FROM messages WHERE id=?', (prepared['attempt_id'],))
        return {'message': message_view(user), 'reply': message_view(reply), 'connection': 'ready'}

    def prepare(self, user) -> dict:
        with self.database.connect(write=True) as connection:
            config = optional(connection, 'SELECT * FROM connection WHERE id=1')
            if config is None:
                return {'connection': 'not_configured'}
            companion = require_current(connection)
            require(user['timeline_id'] == companion['active_timeline_id'], 'This message is on an inactive timeline.',
                    409)
            packet = context.build(connection, companion, self.database.clock.now(),
                                   config['context_tokens'] - config['max_output_tokens'])
            attempt_id = identifier()
            connection.execute(
                'INSERT INTO messages (id, timeline_id, seq, role, text, reply_to, status, active, '
                'character_version_id, memory_revision, receipt, created_at) '
                "VALUES (?, ?, ?, 'companion', '', ?, 'streaming', 0, ?, ?, ?, ?)",
                (attempt_id, user['timeline_id'], next_seq(connection, user['timeline_id']), user['id'],
                 companion['active_version_id'], settings(connection)['memory_revision'], encode(packet['receipt']),
                 self.database.now()))
        return {'connection': 'ready', 'attempt_id': attempt_id, 'config': config, 'packet': packet}

    async def generate(self, prepared):
        text, status, error = [], 'complete', None
        try:
            key = credential_for(self.vault, prepared['config']['credential_ref'])
            with self.scheduler.foreground_work():
                async with self.scheduler.reserve(prepared['config'], CONVERSATION):
                    async for chunk in self.provider.stream(prepared['config'], key, prepared['packet']['system'],
                                                            prepared['packet']['messages']):
                        text.append(chunk.text)
                        if chunk.finish_reason in INCOMPLETE:
                            status, error = 'incomplete', INCOMPLETE[chunk.finish_reason]
        except asyncio.CancelledError:
            status, error = 'cancelled', 'Stopped.'
        except DomainError as failure:
            status, error = ('incomplete' if ''.join(text) else 'failed'), failure.message
        except Exception:  # noqa: BLE001 - an unexpected failure must still leave a visible state.
            status, error = ('incomplete' if ''.join(text) else 'failed'), 'The reply failed unexpectedly.'
        if status == 'complete' and not ''.join(text).strip():
            status, error = 'failed', 'The model returned no reply text.'
        self.finish(prepared['attempt_id'], ''.join(text), status, error)

    def finish(self, attempt_id, text, status, error):
        with self.database.connect(write=True) as connection:
            attempt = one(connection, 'SELECT * FROM messages WHERE id=?', (attempt_id,))
            companion = require_current(connection)
            if status == 'complete' and not still_current(connection, attempt, companion):
                status, error = 'withheld', 'Memories or the character changed while this reply was written.'
            connection.execute('UPDATE messages SET text=?, status=?, error=?, completed_at=? WHERE id=?',
                               (text, status, error, self.database.now(), attempt_id))
            if status == 'complete':
                connection.execute('UPDATE messages SET active=0 WHERE reply_to=?', (attempt['reply_to'],))
                connection.execute('UPDATE messages SET active=1 WHERE id=?', (attempt_id,))


def still_current(connection, attempt, companion) -> bool:
    return (attempt['memory_revision'] == settings(connection)['memory_revision']
            and attempt['character_version_id'] == companion['active_version_id']
            and attempt['timeline_id'] == companion['active_timeline_id'])


def context_preview(database) -> dict:
    """What the next reply would be built from, for the memory details view."""
    with database.connect() as connection:
        config = optional(connection, 'SELECT * FROM connection WHERE id=1')
        budget = (config['context_tokens'] - config['max_output_tokens']) if config else 16000
        return context.build(connection, require_current(connection), database.clock.now(), budget)
