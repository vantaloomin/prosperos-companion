"""Saved conversation with idempotent sends, visible incomplete replies and alternatives (PRD C2, C4, M9).

A reply only becomes the active response when it completed against the memory revision and
character version it was built from. Otherwise it is kept as `withheld` so a correction made
while it was generating can never be contradicted by the stale reply.

A reply can be awaited in the sending request, or the request can return as soon as the attempt
is saved and the client follows its text with `events()`. Generation belongs to the app, not to
the request or the stream: closing a stream never stops a reply, only Stop does.
"""
import asyncio
from dataclasses import dataclass, field

from companion.characters import require_current
from companion.database import encode, identifier, many, one, optional, settings
from companion.errors import DomainError, require
from companion.memory import context, formation
from companion.providers.chat import INCOMPLETE, ChatProvider
from companion.providers.embeddings import QUERY_TIMEOUT, EmbeddingProvider
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
            'timeout_seconds, embedding_model, updated_at) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE '
            'SET base_url=excluded.base_url, model=excluded.model, credential_ref=excluded.credential_ref, '
            'max_output_tokens=excluded.max_output_tokens, context_tokens=excluded.context_tokens, '
            'timeout_seconds=excluded.timeout_seconds, embedding_model=excluded.embedding_model, '
            'updated_at=excluded.updated_at',
            (base_url, body.model, reference, body.max_output_tokens, body.context_tokens, body.timeout_seconds,
             body.embedding_model or None, database.now()))
        return connection_view(one(connection, 'SELECT * FROM connection WHERE id=1'))


def next_seq(connection, timeline_id) -> int:
    return one(connection, 'SELECT COALESCE(MAX(seq), 0) + 1 AS seq FROM messages WHERE timeline_id=?',
               (timeline_id,))['seq']


def record_user(database, body) -> dict:
    """Saving the user's text comes first and is idempotent on client_id (no duplicate on retry).

    With automatic memory on, the same write queues the message for extraction after the reply.
    """
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
        message = one(connection, 'SELECT * FROM messages WHERE id=?', (message_id,))
        formation.enqueue(connection, message, database.now())
        return message


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


SEARCH_LIMIT = 50


def search(database, query: str, limit=SEARCH_LIMIT) -> dict:
    """Newest-first matches in the active timeline, compared case-insensitively in Python so any script folds."""
    needle = query.strip().casefold()
    require(len(needle) >= 2, 'Search for at least two characters.', 422)
    with database.connect() as connection:
        companion = require_current(connection)
        rows = connection.execute(
            "SELECT id, seq, role, text, status, reply_to, created_at FROM messages WHERE timeline_id=? "
            "AND redacted_at IS NULL AND text<>'' ORDER BY seq DESC", (companion['active_timeline_id'],))
        results = []
        for row in rows:
            if needle in row['text'].casefold():
                results.append(dict(row))
                if len(results) == limit:
                    break
        return {'query': query.strip(), 'results': results, 'more': len(results) == limit}


def message_view(row: dict) -> dict:
    return {key: value for key, value in row.items() if key not in {'receipt', 'client_id'}} | {
        'active': bool(row['active']), 'redacted': row['redacted_at'] is not None}


def recover(database):
    """A reply interrupted by a crash stays visibly incomplete; it never becomes the active response."""
    with database.connect(write=True) as connection:
        connection.execute("UPDATE messages SET status='incomplete', active=0, error=COALESCE(error, ?), "
                           "completed_at=COALESCE(completed_at, ?) WHERE status='streaming'",
                           ('The app closed before this reply finished.', database.now()))


@dataclass
class LiveReply:
    """Text streamed so far for one attempt, fanned out to every open event stream."""
    task: asyncio.Task | None = None
    text: list[str] = field(default_factory=list)
    listeners: set[asyncio.Queue] = field(default_factory=set)

    def publish(self, text: str):
        if text:
            self.text.append(text)
            for queue in self.listeners:
                queue.put_nowait(text)


class Conversation:
    def __init__(self, database, vault, provider=None, scheduler=None, after_turn=lambda: None, embedder=None,
                 lookups=None):
        self.database = database
        self.vault = vault
        self.provider = provider or ChatProvider()
        self.embedder = embedder or EmbeddingProvider()
        self.scheduler = scheduler or RequestScheduler()
        # Current-context lookups the user enabled (PRD X1-X3); the app, not the model, decides when they run.
        self.lookups = lookups
        self.running: dict[str, LiveReply] = {}
        # Called once a turn needs nothing more from the model, so memory work never runs ahead of a reply.
        self.after_turn = after_turn

    async def send(self, body, wait: bool = True) -> dict:
        user = record_user(self.database, body)
        with self.database.connect() as connection:
            reply = active_reply(connection, user['id']) or self.in_progress(connection, user['id'])
        if reply:
            return {'message': message_view(user), 'reply': message_view(reply), 'connection': 'ready'}
        return await self.respond(user, wait)

    def in_progress(self, connection, user_message_id) -> dict | None:
        """A retried send while its reply is still being written follows that reply instead of starting another."""
        rows = many(connection, "SELECT * FROM messages WHERE reply_to=? AND status='streaming'", (user_message_id,))
        return next((row for row in rows if row['id'] in self.running), None)

    async def alternative(self, user_message_id, wait: bool = True) -> dict:
        with self.database.connect() as connection:
            user = one(connection, "SELECT * FROM messages WHERE id=? AND role='user'", (user_message_id,))
            latest = latest_user_message(connection, user['timeline_id'])
            require(latest['id'] == user['id'], 'Alternatives are available for the latest message only.', 409)
        return await self.respond(user, wait)

    def stop(self, attempt_id) -> bool:
        live = self.running.get(attempt_id)
        if live is None:
            return False
        live.task.cancel()
        return True

    async def query_vector(self, user) -> dict | None:
        """Embed the message being answered for semantic recall; any failure means keyword recall only."""
        with self.database.connect() as connection:
            config = optional(connection, 'SELECT * FROM connection WHERE id=1')
        if not config or not config.get('embedding_model'):
            return None
        try:
            key = credential_for(self.vault, config['credential_ref'])
            async with self.scheduler.reserve(config, CONVERSATION):
                [vector] = await self.embedder.embed(config, key, [user['text']], QUERY_TIMEOUT)
        except Exception:  # noqa: BLE001 - semantic recall is optional; the reply goes ahead without it.
            return None
        return {'model': config['embedding_model'], 'vector': vector}

    async def outside(self, user) -> list[dict]:
        """Lookups the message asks for; a failure of the lookup machinery never blocks the reply."""
        if self.lookups is None:
            return []
        try:
            return await self.lookups.for_message(user)
        except Exception:  # noqa: BLE001 - the companion continues without tools (X3).
            return []

    async def respond(self, user, wait: bool = True) -> dict:
        semantic, outside = await asyncio.gather(self.query_vector(user), self.outside(user))
        prepared = self.prepare(user, semantic, outside)
        if prepared['connection'] != 'ready':
            self.after_turn()
            return {'message': message_view(user), 'reply': None, 'connection': prepared['connection']}
        live = self.start(prepared)
        if wait:
            try:
                await asyncio.shield(live.task)
            except asyncio.CancelledError:
                if not live.task.done():
                    raise
        return {'message': message_view(user), 'reply': self.reply(prepared['attempt_id']),
                'connection': 'ready'}

    def start(self, prepared) -> LiveReply:
        attempt_id, live = prepared['attempt_id'], LiveReply()
        live.task = asyncio.create_task(self.generate(prepared, live.publish))
        self.running[attempt_id] = live
        live.task.add_done_callback(lambda _task: self.close(attempt_id))
        return live

    def close(self, attempt_id):
        """The attempt is saved in its final state before its streams are told it ended."""
        live = self.running.pop(attempt_id, None)
        for queue in live.listeners if live else ():
            queue.put_nowait(None)
        self.after_turn()

    def reply(self, attempt_id) -> dict:
        with self.database.connect() as connection:
            return message_view(one(connection, "SELECT * FROM messages WHERE id=? AND role='companion'",
                                    (attempt_id,)))

    async def events(self, attempt_id):
        """Yield (event, data): a snapshot of the text so far, each new piece of text, then the saved reply."""
        live = self.running.get(attempt_id)
        if live is not None:
            queue = asyncio.Queue()
            live.listeners.add(queue)
            try:
                yield 'snapshot', {'id': attempt_id, 'text': ''.join(live.text)}
                while (text := await queue.get()) is not None:
                    yield 'delta', {'id': attempt_id, 'text': text}
            finally:
                live.listeners.discard(queue)
        yield 'done', self.reply(attempt_id)

    def prepare(self, user, semantic=None, outside=None) -> dict:
        with self.database.connect(write=True) as connection:
            config = optional(connection, 'SELECT * FROM connection WHERE id=1')
            if config is None:
                return {'connection': 'not_configured'}
            companion = require_current(connection)
            require(user['timeline_id'] == companion['active_timeline_id'], 'This message is on an inactive timeline.',
                    409)
            packet = context.build(connection, companion, self.database.clock.now(),
                                   config['context_tokens'] - config['max_output_tokens'], user['seq'], semantic,
                                   outside)
            attempt_id = identifier()
            connection.execute(
                'INSERT INTO messages (id, timeline_id, seq, role, text, reply_to, status, active, '
                'character_version_id, memory_revision, receipt, created_at) '
                "VALUES (?, ?, ?, 'companion', '', ?, 'streaming', 0, ?, ?, ?, ?)",
                (attempt_id, user['timeline_id'], next_seq(connection, user['timeline_id']), user['id'],
                 companion['active_version_id'], settings(connection)['memory_revision'], encode(packet['receipt']),
                 self.database.now()))
        return {'connection': 'ready', 'attempt_id': attempt_id, 'config': config, 'packet': packet}

    async def generate(self, prepared, publish=lambda _text: None):
        text, status, error = [], 'complete', None
        try:
            key = credential_for(self.vault, prepared['config']['credential_ref'])
            with self.scheduler.foreground_work():
                async with self.scheduler.reserve(prepared['config'], CONVERSATION):
                    async for chunk in self.provider.stream(prepared['config'], key, prepared['packet']['system'],
                                                            prepared['packet']['messages']):
                        text.append(chunk.text)
                        publish(chunk.text)
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
