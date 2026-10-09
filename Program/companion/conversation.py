"""Saved conversation with idempotent sends, visible incomplete replies and alternatives (PRD C2, C4, M9).

A reply only becomes the active response when it completed against the memory revision and
character version it was built from. Otherwise it is kept as `withheld` so a correction made
while it was generating can never be contradicted by the stale reply.

A reply can be awaited in the sending request, or the request can return as soon as the attempt
is saved and the client follows its text with `events()`. Generation belongs to the app, not to
the request or the stream: closing a stream never stops a reply, only Stop does.
"""
import asyncio
import logging
from dataclasses import dataclass, field

from companion import (
    in_character,
    logs,
    model_calls,
    moods,
    pictures,
    safety,
    self_checks,
    self_facts,
    texting,
    troubleshoot,
)
from companion.characters import by_id, for_timeline, require_current
from companion.database import encode, identifier, many, one, optional, settings
from companion.errors import DomainError, require
from companion.images import photos
from companion.life import occasions, own_plans, pacing, recommendations
from companion.memory import context, formation, look_back
from companion.providers.chat import INCOMPLETE, ChatProvider
from companion.providers.embeddings import QUERY_TIMEOUT, EmbeddingProvider, as_query, vector_model
from companion.providers.scheduling import CONVERSATION, RequestScheduler
from companion.text_models import CHAT, config_for, default_name, key_for
from companion.voice import notes as voice_notes

LOG = logging.getLogger(__name__)


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
        companion = in_focus(connection, body.companion_id, database.now())
        timeline_id, message_id = companion['active_timeline_id'], identifier()
        connection.execute(
            'INSERT INTO messages (id, timeline_id, seq, role, text, client_id, status, character_version_id, '
            "created_at, completed_at) VALUES (?, ?, ?, 'user', ?, ?, 'complete', ?, ?, ?)",
            (message_id, timeline_id, next_seq(connection, timeline_id), body.text, body.client_id,
             companion['active_version_id'], database.now(), database.now()))
        pictures.attach(connection, message_id, body.picture_ids)
        # Sending on a timeline made by a historical edit uses up its waiting draft (C4).
        connection.execute('UPDATE timelines SET draft=NULL WHERE id=?', (timeline_id,))
        message = one(connection, 'SELECT * FROM messages WHERE id=?', (message_id,))
        formation.enqueue(connection, message, database.now())
        recommendations.note(connection, message, database.now())
        occasions.note(connection, message, database.now())
        self_checks.heed(connection, message, database.now())
        moods.from_user(connection, f"companion:{companion['id']}", body.text, database.clock.now())
        return message


def in_focus(connection, companion_id: str | None, timestamp: str) -> dict:
    """The companion a new message is for. A window still showing another companion's chat (focus moved in a
    second window or on a phone) brings that companion back into focus, so the message lands in the chat on screen
    and never in someone else's."""
    companion = require_current(connection)
    if companion_id and companion_id != companion['id']:
        require(by_id(connection, companion_id) is not None,
                'That companion is no longer in this workspace, so the message was not sent. Pick a chat in Chats.',
                404)
        from companion.cast import step_back
        step_back(connection, timestamp, companion_id)
        companion = require_current(connection)
    return companion


def active_reply(connection, user_message_id) -> dict | None:
    return optional(connection, "SELECT * FROM messages WHERE reply_to=? AND active=1 AND status='complete'",
                    (user_message_id,))


def latest_user_message(connection, timeline_id) -> dict | None:
    return optional(connection, "SELECT * FROM messages WHERE timeline_id=? AND role='user' "
                    'ORDER BY seq DESC LIMIT 1', (timeline_id,))


def history(database, before_seq=None, limit=100) -> dict:
    with database.connect() as connection:
        companion = require_current(connection)
        rows = many(connection, 'SELECT * FROM messages WHERE timeline_id=? AND seq<? AND superseded_at IS NULL '
                    'ORDER BY seq DESC LIMIT ?',
                    (companion['active_timeline_id'], before_seq or 2 ** 62, limit))
        return {'timeline_id': companion['active_timeline_id'],
                'messages': voice_notes.decorate(connection, pictures.decorate(connection, photos.decorate(
                    connection, [message_view(row) for row in reversed(rows)])))}


SEARCH_LIMIT = 50


def search(database, query: str, limit=SEARCH_LIMIT) -> dict:
    """Newest-first matches in the active timeline, compared case-insensitively in Python so any script folds."""
    needle = query.strip().casefold()
    require(len(needle) >= 2, 'Search for at least two characters.', 422)
    with database.connect() as connection:
        companion = require_current(connection)
        # A reply to a deleted message usually repeats it, so search leaves it out with it (M12).
        rows = connection.execute(
            "SELECT message.id, message.seq, message.role, message.text, message.status, message.reply_to, "
            "message.created_at FROM messages message LEFT JOIN messages parent ON parent.id=message.reply_to "
            "WHERE message.timeline_id=? AND message.redacted_at IS NULL AND message.text<>'' "
            "AND message.superseded_at IS NULL "
            "AND parent.redacted_at IS NULL ORDER BY message.seq DESC", (companion['active_timeline_id'],))
        results = []
        for row in rows:
            if needle in row['text'].casefold():
                results.append(dict(row))
                if len(results) == limit:
                    break
        return {'query': query.strip(), 'results': results, 'more': len(results) == limit}


def message_view(row: dict) -> dict:
    """A message for the interface. A user's message that sounds like self-harm carries `crisis_help`, so the chat
    shows the app's note with places to get help under it (companion/safety.py)."""
    return {key: value for key, value in row.items() if key not in {'receipt', 'client_id'}} | {
        'active': bool(row['active']), 'redacted': row['redacted_at'] is not None,
        'crisis_help': row['role'] == 'user' and row['redacted_at'] is None and safety.crisis(row['text'])}


def recover(database):
    """A reply interrupted by a crash stays visibly incomplete; it never becomes the active response."""
    with database.connect(write=True) as connection:
        connection.execute("UPDATE messages SET status='incomplete', active=0, error=COALESCE(error, ?), "
                           "completed_at=COALESCE(completed_at, ?) WHERE status='streaming'",
                           ('The app closed before this reply finished.', database.now()))


# What the app is doing for a reply before its text arrives, so the chat can always say (never the companion's presence).
PHASES = ('preparing', 'looking', 'waiting', 'remembering', 'writing')


@dataclass
class LiveReply:
    """Text streamed so far for one attempt and what the app is doing for it, fanned out to every open event stream."""
    task: asyncio.Task | None = None
    text: list[str] = field(default_factory=list)
    listeners: set[asyncio.Queue] = field(default_factory=set)
    phase: str = 'preparing'

    def publish(self, text: str):
        if text:
            self.text.append(text)
            for queue in self.listeners:
                queue.put_nowait(('delta', {'text': text}))

    def step(self, phase: str):
        if phase != self.phase:
            self.phase = phase
            for queue in self.listeners:
                queue.put_nowait(('phase', {'phase': phase}))


# Failures that come from the model service, which Settings > Models can test.
MODEL_FAILURES = {'provider', 'timeout', 'connection'}


def model_failure(config: dict, failure: DomainError) -> str:
    """A model service's failure names the profile that made the call and where to test it."""
    if failure.code not in MODEL_FAILURES:
        return failure.message
    name = config.get('profile_name') or default_name(config)
    return f'{name}: {failure.message} Test connection in Settings > Models checks this profile.'


class Conversation:
    def __init__(self, database, vault, provider=None, scheduler=None, after_turn=lambda: None, embedder=None,
                 lookups=None):
        self.database = database
        self.vault = vault
        # Every chat model call goes through here, written down in full while Record model calls is on.
        self.provider = model_calls.Recording(provider or ChatProvider(), database)
        self.embedder = embedder or EmbeddingProvider()
        self.scheduler = scheduler or RequestScheduler()
        # Current-context lookups the user enabled (PRD X1-X3); the app, not the model, decides when they run.
        self.lookups = lookups
        # Photos in chat (companion/images/photos.py); the app, not the model, decides when one is sent.
        self.photos = None
        # Pictures the user sends, described once before the reply (companion/pictures.py).
        self.seer = pictures.Seer(database, vault, self.provider, self.scheduler)
        self.running: dict[str, LiveReply] = {}
        # Called once a turn needs nothing more from the model, so memory work never runs ahead of a reply.
        self.after_turn = after_turn

    def user_view(self, user) -> dict:
        with self.database.connect() as connection:
            [view] = pictures.decorate(connection, [message_view(user)])
            return view

    async def send(self, body, wait: bool = True) -> dict:
        user = record_user(self.database, body)
        with self.database.connect() as connection:
            reply = active_reply(connection, user['id']) or self.in_progress(connection, user['id'])
        if reply:
            return {'message': self.user_view(user), 'reply': message_view(reply), 'connection': 'ready'}
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
            config = config_for(connection, 'recall')
        if not config or not config.get('embedding_model'):
            return None
        try:
            key = key_for(self.vault, config)
            async with self.scheduler.reserve(config, CONVERSATION):
                [vector] = await self.embedder.embed(config, key, [as_query(config, user['text'])], QUERY_TIMEOUT)
        except Exception:  # noqa: BLE001 - semantic recall is optional; the reply goes ahead without it.
            return None
        return {'model': vector_model(config), 'vector': vector}

    async def outside(self, user) -> list[dict]:
        """Lookups the message asks for; a failure of the lookup machinery never blocks the reply."""
        if self.lookups is None:
            return []
        with self.database.connect() as connection:
            if config_for(connection, CHAT) is None:
                return []  # No reply will be written, so nothing is sent out.
        try:
            return await self.lookups.for_message(user)
        except Exception:  # noqa: BLE001 - the companion continues without tools (X3).
            return []

    async def respond(self, user, wait: bool = True) -> dict:
        """The attempt is saved before anything waits on a model service, so `wait=false` returns at once;
        recall and lookups for the reply happen in its own task (PRD responsiveness target)."""
        prepared = self.prepare(user)
        if prepared['connection'] != 'ready':
            self.after_turn()
            return {'message': self.user_view(user), 'reply': None, 'connection': prepared['connection']}
        live = self.start(prepared)
        if wait:
            try:
                await asyncio.shield(live.task)
            except asyncio.CancelledError:
                if not live.task.done():
                    raise
        reply = self.reply(prepared['attempt_id'])
        if prepared['note'] is None:
            return {'message': self.user_view(user), 'reply': reply, 'connection': 'ready',
                    'dropped': prepared['dropped']}
        # A holding text answers the message now; the full reply follows as a message of its own.
        return {'message': self.user_view(user), 'reply': self.reply(prepared['note']), 'follow_up': reply,
                'connection': 'ready', 'dropped': prepared['dropped']}

    def start(self, prepared) -> LiveReply:
        attempt_id, live = prepared['attempt_id'], LiveReply()
        live.task = asyncio.create_task(self.generate(prepared, live.publish, live.step))
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
            [view] = photos.decorate(connection, [message_view(one(
                connection, "SELECT * FROM messages WHERE id=? AND role='companion'", (attempt_id,)))])
            return view

    async def events(self, attempt_id):
        """Yield (event, data): a snapshot of the text so far, each new piece of text, then the saved reply."""
        live = self.running.get(attempt_id)
        if live is not None:
            queue = asyncio.Queue()
            live.listeners.add(queue)
            try:
                yield 'snapshot', {'id': attempt_id, 'text': ''.join(live.text), 'phase': live.phase}
                while (item := await queue.get()) is not None:
                    yield item[0], {'id': attempt_id, **item[1]}
            finally:
                live.listeners.discard(queue)
        yield 'done', self.reply(attempt_id)

    def prepare(self, user) -> dict:
        with self.database.connect(write=True) as connection:
            config = config_for(connection, CHAT)
            if config is None:
                return {'connection': 'not_configured'}
            companion = chat_owner(connection, user['timeline_id'])
            attempt_id, now = identifier(), self.database.now()
            held, dropped = pacing.take_over(connection, user['timeline_id'],
                                             pacing.hold(connection, companion, self.database.clock.now(), attempt_id),
                                             now)
            held = pacing.join(connection, user['timeline_id'], held, now)
            note = None
            if held['held_line']:
                # Busy: a holding text now, which stays, and the full reply later as a message of its own.
                note = identifier()
                connection.execute(
                    'INSERT INTO messages (id, timeline_id, seq, role, text, reply_to, status, active, '
                    'character_version_id, memory_revision, created_at, completed_at) '
                    "VALUES (?, ?, ?, 'companion', ?, ?, 'complete', 1, ?, ?, ?, ?)",
                    (note, user['timeline_id'], next_seq(connection, user['timeline_id']), held['held_line'],
                     user['id'], companion['active_version_id'], settings(connection)['memory_revision'], now, now))
            connection.execute(
                'INSERT INTO messages (id, timeline_id, seq, role, text, reply_to, status, active, '
                'character_version_id, memory_revision, created_at, held_until, held_line) '
                "VALUES (?, ?, ?, 'companion', '', ?, 'streaming', 0, ?, ?, ?, ?, ?)",
                (attempt_id, user['timeline_id'], next_seq(connection, user['timeline_id']),
                 None if note else user['id'], companion['active_version_id'], settings(connection)['memory_revision'],
                 now, held['held_until'], held['held_line']))
        return {'connection': 'ready', 'attempt_id': attempt_id, 'config': config, 'user': user,
                'instruction': held['instruction'], 'note': note, 'dropped': dropped,
                'definition': companion['version']['definition']}

    async def assemble(self, prepared, step=lambda _phase: None) -> dict:
        """Build the reply's inputs and record the memory revision and character version they reflect,
        so a change made after this point withholds the reply (M9)."""
        user = prepared['user']
        photo = self.photos.for_message(user, prepared['attempt_id']) if self.photos else None
        shown = await self.seer.look(user, lambda: step('looking'))
        step('preparing')
        # Recall also looks for what the pictures show; lookups answer only what the user wrote.
        seen = {**user, 'text': pictures.with_pictures(user['text'], shown)} if shown else user
        semantic, outside = await asyncio.gather(self.query_vector(seen), self.outside(user))
        return await asyncio.to_thread(self.build_packet, prepared, semantic, outside, photo)

    def build_packet(self, prepared, semantic, outside, photo=None) -> dict:
        """Runs off the event loop: at 10,000 messages the build takes a few hundred milliseconds and
        would otherwise hold every other request. The read is one snapshot, so the recorded revision
        is the one the packet reflects; a change committed after it withholds the reply."""
        user, config = prepared['user'], prepared['config']
        with self.database.connect() as connection:
            companion = chat_owner(connection, user['timeline_id'])
            packet = context.build(connection, companion, self.database.clock.now(),
                                   config['context_tokens'] - config['max_output_tokens'], user['seq'], semantic,
                                   outside, photo)
            revision = settings(connection)['memory_revision']
        with self.database.connect(write=True) as connection:
            connection.execute('UPDATE messages SET memory_revision=?, character_version_id=?, receipt=? WHERE id=?',
                               (revision, companion['active_version_id'], encode(packet['receipt']),
                                prepared['attempt_id']))
        return packet

    async def generate(self, prepared, publish=lambda _text: None, step=lambda _phase: None):
        text, status, error = [], 'complete', None
        definition = prepared.get('definition') or {}
        active = in_character.applies(prepared['user']['text'], definition)
        try:
            key = key_for(self.vault, prepared['config'])
            with self.scheduler.foreground_work():
                packet = await self.assemble(prepared, step)
                if prepared.get('instruction'):
                    # Busy: a quick note now, or the full reply after a holding text (companion/life/pacing.py).
                    packet = context.add_note(packet, prepared['instruction'])
                if in_character.out_of_character(prepared['user']['text']):
                    note = in_character.OUT_OF_CHARACTER_NOTE.format(
                        name=definition.get('name', 'the character'), model=default_name(prepared['config']))
                    what_if = self.what_if(prepared['user']['timeline_id'])
                    packet = context.add_note(packet, '\n\n'.join(filter(None, (note, what_if))))
                status, error, dropped, packet = await self.compose(prepared, key, packet, text, publish, active,
                                                                    step)
                if dropped and not ''.join(text).strip():
                    # The reply only stepped out of character: written once more with a reminder.
                    reminder = in_character.REMINDER.format(name=definition.get('name', 'yourself'))
                    status, error, dropped, _asked = await self.write(
                        prepared, key, context.add_note(packet, reminder), text, publish, active, step)
                    if dropped and not ''.join(text).strip():
                        error = 'Every line of the reply stepped out of character, so it was hidden.'
        except asyncio.CancelledError:
            status, error = 'cancelled', 'Stopped.'
        except DomainError as failure:
            status, error = ('incomplete' if ''.join(text) else 'failed'), model_failure(prepared['config'], failure)
        except Exception as failure:  # noqa: BLE001 - an unexpected failure must still leave a visible state.
            LOG.exception('A reply failed unexpectedly.')
            status = 'incomplete' if ''.join(text) else 'failed'
            error = troubleshoot.describe("Couldn't finish", 'the reply', failure, str(logs.file_path()))
        if status == 'complete' and not ''.join(text).strip():
            status, error = 'failed', error or 'The model returned no reply text.'
        self.finish(prepared['attempt_id'], ''.join(text), status, error)

    async def compose(self, prepared, key, packet, text, publish, active, step) -> tuple[str, str | None, int, dict]:
        """The reply, with one chance to ask to remember more first (companion/memory/look_back.py): returns the
        status, error, dropped sentences and the packet the reply was written from."""
        if not self.may_look_back(prepared):
            return (*(await self.write(prepared, key, packet, text, publish, active, step))[:3], packet)
        asking = context.add_note(packet, look_back.ASK)
        status, error, dropped, query = await self.write(prepared, key, asking, text, publish, active, step,
                                                         look_back.Lookout())
        look_back.RATES.count(model_of(prepared), query is not None)
        if query is None:
            return status, error, dropped, asking
        # "Checking older memories…" only once the second look has taken a second, until the reply starts.
        later = asyncio.get_running_loop().call_later(look_back.SHOW_AFTER, step, 'remembering')
        lines = await asyncio.to_thread(self.look_back, prepared, query, packet)
        packet = context.add_note(packet, look_back.found_note(query, lines))
        try:
            status, error, dropped, _query = await self.write(prepared, key, packet, text, publish, active,
                                                              lambda phase: later.cancelled() and step(phase),
                                                              started=lambda: later.cancel() or step('writing'))
        finally:
            later.cancel()
        return status, error, dropped, packet

    def may_look_back(self, prepared) -> bool:
        user_text = prepared['user']['text']
        if in_character.out_of_character(user_text) or not look_back.points_back(user_text) or \
                not look_back.RATES.allowed(model_of(prepared)):
            return False
        with self.database.connect() as connection:
            return bool(settings(connection)['recall_more'])

    def look_back(self, prepared, query: str, packet: dict) -> list[str]:
        user = prepared['user']
        with self.database.connect() as connection:
            companion = chat_owner(connection, user['timeline_id'])
            return context.looked_back(connection, companion, self.database.clock.now(), query, user['seq'],
                                       frozenset(packet['receipt']['included'].get('recalled', ())))

    async def write(self, prepared, key, packet, text, publish, active, step=lambda _phase: None, lookout=None,
                    started=lambda: None) -> tuple[str, str | None, int, str | None]:
        """One pass at the reply. Sentences that say the companion is an AI or not real are dropped before
        they are shown (companion/in_character.py); a reply that asks to remember more is held back and cut short
        (`lookout`, companion/memory/look_back.py; otherwise such a request is only dropped). Returns the status, error, how many sentences were dropped and
        what it asked to remember, if it did. Waiting for the model is capped at the reply's time limit, so a reply
        never waits unseen forever."""
        status, error, guard = 'complete', None, in_character.Guard(active)
        lookout = lookout or look_back.Lookout(strip=True)
        text.clear()

        def keep(piece):
            if piece:
                if not text:
                    started()
                text.append(piece)
                publish(piece)

        step('waiting')
        try:
            async with self.scheduler.reserve(prepared['config'], CONVERSATION, prepared['config']['timeout_seconds']):
                step('writing')
                async for chunk in self.provider.stream(prepared['config'], key, packet['system'],
                                                        packet['messages']):
                    keep(guard.feed(lookout.feed(chunk.text)))
                    if lookout.query:
                        break
                    if chunk.finish_reason in INCOMPLETE:
                        status, error = 'incomplete', INCOMPLETE[chunk.finish_reason]
        finally:
            keep(guard.feed(lookout.flush()))
            keep(guard.flush())  # A stopped or failed reply keeps the text it had, still checked.
        return status, error, guard.dropped, lookout.query

    def what_if(self, timeline_id) -> str:
        """The odds the consequence engine sees for what could happen, for an out-of-character answer."""
        from companion.life import reactions
        with self.database.connect() as connection:
            return reactions.what_if_note(connection, chat_owner(connection, timeline_id), self.database.clock.now())

    def finish(self, attempt_id, text, status, error):
        with self.database.connect(write=True) as connection:
            attempt = one(connection, 'SELECT * FROM messages WHERE id=?', (attempt_id,))
            # The companion whose chat this is: switching to another chat meanwhile doesn't withhold the reply.
            companion = for_timeline(connection, attempt['timeline_id']) or require_current(connection)
            if attempt['superseded_at']:
                # The user wrote again first and a newer reply took its place (companion/life/pacing.py).
                connection.execute('UPDATE messages SET text=?, status=?, error=?, completed_at=? WHERE id=?',
                                   (text, status, error, self.database.now(), attempt_id))
                return
            if status == 'complete' and not still_current(connection, attempt, companion):
                status, error = 'withheld', 'Memories or the character changed while this reply was written.'
            if status == 'complete':
                text = texting.restyle(text, companion['version']['definition'], attempt_id)
            connection.execute('UPDATE messages SET text=?, status=?, error=?, completed_at=? WHERE id=?',
                               (text, status, error, self.database.now(), attempt_id))
            if status == 'complete':
                connection.execute('UPDATE messages SET active=0 WHERE reply_to=?', (attempt['reply_to'],))
                connection.execute('UPDATE messages SET active=1 WHERE id=?', (attempt_id,))
                finished = one(connection, 'SELECT * FROM messages WHERE id=?', (attempt_id,))
                self_facts.note(connection, finished, self.database.now())
                own_plans.note(connection, finished, companion, self.database.now())


def model_of(prepared) -> str:
    return str(prepared['config'].get('model') or '')


def chat_owner(connection, timeline_id) -> dict:
    """The companion a reply is for. The reply keeps being written when the user opens another chat meanwhile,
    but not once its chat moved to another timeline (an edit or a branch)."""
    companion = for_timeline(connection, timeline_id)
    require(companion is not None and timeline_id == companion['active_timeline_id'],
            'This message is on an inactive timeline.', 409)
    return companion


def still_current(connection, attempt, companion) -> bool:
    return (attempt['memory_revision'] == settings(connection)['memory_revision']
            and attempt['character_version_id'] == companion['active_version_id']
            and attempt['timeline_id'] == companion['active_timeline_id'])


def context_preview(database) -> dict:
    """What the next reply would be built from, for the memory details view."""
    with database.connect() as connection:
        config = config_for(connection, CHAT)
        budget = (config['context_tokens'] - config['max_output_tokens']) if config else 16000
        packet = context.build(connection, require_current(connection), database.clock.now(), budget)
    # `prompt` is everything the reply is told besides the conversation: the system prompt and this reply's notes.
    return {**packet, 'prompt': f"{packet['system']}\n\n{packet['note']}"}
