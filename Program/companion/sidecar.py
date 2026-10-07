"""The sidecar: an out-of-context chat beside the app, after the Collaborator in Prospero's Study.

It sees the context (the character, the recent conversation and the memories) but is never part of it:
what is said in the sidecar is not stored, never reaches the companion and never becomes a memory. It can
evaluate, explain and suggest, and it can propose changes the user applies one by one:

- a character field (applied to the character form while it is open, otherwise saved as a new version),
- the wording of one of the companion's replies (companion/message_edits.py),
- a memory's value, a new memory, or setting a memory aside, all through the Memories paths
  (companion/memory/records.py), so corrections reach every copy of a fact the usual way.

The model only proposes. Every proposal is checked here against the context it was shown: it may only name
messages and memories it was given, by the short references it was given. Nothing is applied by this module.
See docs/sidecar.md.
"""
from datetime import datetime

from companion import drafting
from companion.character_helper import HELPER_FIELDS, fields_text, helper_value
from companion.characters import require_current
from companion.database import identifier, many, optional
from companion.errors import DomainError
from companion.memory import records
from companion.text_models import config_for
from companion.world import naming

JOB = 'sidecar'
SIDECAR_TOKENS = 3000
RECENT_MESSAGES = 30
MESSAGE_CHARS = 1500
MEMORY_LIMIT = 150
NEW_MEMORY_LAYERS = ('user_fact', 'shared_experience', 'plan', 'temporary', 'relationship')
VIEW_NAMES = {'conversation': 'the chat', 'feed': 'her posts', 'character': 'the character form',
              'memories': 'Memories', 'today': 'Today', 'settings': 'Settings', 'story': 'the Story tab'}


def connection_config(database) -> dict:
    with database.connect() as connection:
        config = config_for(connection, JOB)
    if config is None:
        raise DomainError('Add a text model in Settings > Models to use the sidecar.', 409, 'no_connection')
    return config


# --- What the sidecar is shown ----------------------------------------------------------------

def stamp(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime('%a %d %b %H:%M')
    except (TypeError, ValueError):
        return ''


def recent_messages(connection, timeline_id: str, focus: str | None) -> list[dict]:
    rows = many(connection, "SELECT * FROM messages WHERE timeline_id=? AND active=1 AND status='complete' "
                'AND redacted_at IS NULL AND superseded_at IS NULL ORDER BY seq DESC LIMIT ?',
                (timeline_id, RECENT_MESSAGES))
    if focus and all(row['id'] != focus for row in rows):
        found = optional(connection, "SELECT * FROM messages WHERE id=? AND timeline_id=? AND redacted_at IS NULL",
                         (focus, timeline_id))
        rows += [found] if found else []
    return sorted(rows, key=lambda row: row['seq'])


class Context:
    """The character, recent messages and memories, each message and memory under a short reference."""

    def __init__(self, database, body):
        self.messages, self.memories, self.focus = {}, {}, None
        with database.connect() as connection:
            companion = self.current(connection)
            if body.definition is not None:
                self.definition, self.saved = body.definition, False
            else:
                self.definition = companion['version']['definition'] if companion else None
                self.saved = companion is not None
            self.name = (self.definition or {}).get('name') or 'the companion'
            if companion:
                for index, row in enumerate(recent_messages(connection, companion['active_timeline_id'],
                                                            body.focus_message_id), 1):
                    self.messages[f'm{index}'] = row
                    if row['id'] == body.focus_message_id:
                        self.focus = f'm{index}'
        if companion:
            listed = [item for item in records.listing(database) if item['status'] == 'active' and item['in_timeline']]
            self.memories = {f'k{index}': item for index, item in enumerate(listed[:MEMORY_LIMIT], 1)}

    @staticmethod
    def current(connection):
        try:
            return require_current(connection)
        except DomainError:
            return None

    def character_text(self) -> str:
        if not self.definition:
            return 'There is no character yet.'
        state = 'as it stands in the open character form (not saved yet)' if not self.saved else 'as saved'
        return f'{state}:\n{drafting.character_json(self.definition)}'

    def conversation_text(self) -> str:
        if not self.messages:
            return 'No messages yet.'
        lines = []
        for ref, row in self.messages.items():
            speaker = self.name if row['role'] == 'companion' else 'The user'
            text = row['text'] if len(row['text']) <= MESSAGE_CHARS else row['text'][:MESSAGE_CHARS] + '…'
            lines.append(f'[{ref}] {speaker} ({stamp(row["created_at"])}): {text}')
        return '\n'.join(lines)

    def memories_text(self) -> str:
        if not self.memories:
            return 'No memories yet.'
        return '\n'.join(f"[{ref}] {item['layer']} · {item['subject']}: {item['value']}" for ref, item in self.memories.items())

    def city(self, database) -> dict | None:
        city_id = (self.definition or {}).get('home_city')
        try:
            return drafting.home(database, city_id if isinstance(city_id, str) else '')
        except DomainError:
            return None


def focus_text(context: Context, view: str) -> str:
    where = VIEW_NAMES.get(view.split('/')[0], 'the app')
    focus = f' They pointed you at [{context.focus}].' if context.focus else ''
    return f'The user is looking at {where}.{focus}'


def memory_value(raw, layer, subject) -> str:
    """A memory's new wording, without the "layer · subject:" label models copy from the list they were shown."""
    value = drafting.text_value(raw, 4000)
    for label in (f'{layer} · {subject}:', f'{subject}:'):
        if isinstance(layer, str) and isinstance(subject, str) and value.lower().startswith(label.lower()):
            value = value[len(label):].strip()
    return value


# --- What it may propose ----------------------------------------------------------------------

class Proposals:
    """The reply and its proposed changes, each checked against the context; one unusable change is sent
    back once, then dropped."""

    def __init__(self, context: Context, allowed: str, data: dict | None, seed: str):
        self.context, self.allowed, self.data, self.seed = context, allowed, data, seed

    def __call__(self, raw: dict, final: bool) -> dict:
        reply = drafting.text_value(raw.get('reply'), 3000)
        changes = []
        for item in raw.get('changes') if isinstance(raw.get('changes'), list) else []:
            try:
                changes.append(self.change(item, final))
            except drafting.Unusable:
                if not final:
                    raise
        if not reply:
            if not final:
                raise drafting.Unusable('"reply" was empty.')
            reply = 'Here is what I would change.' if changes else 'I have nothing to change.'
        return {'reply': reply, 'changes': changes, 'prompt_version': drafting.PROMPT_VERSION}

    def change(self, item, final: bool) -> dict:
        if not isinstance(item, dict):
            raise drafting.Unusable('each change must be an object.')
        kind = item.get('kind')
        handlers = {'field': self.field, 'reply': self.reply, 'memory': self.memory, 'new_memory': self.new_memory,
                    'forget_memory': self.forget}
        if kind not in handlers:
            raise drafting.Unusable(f'a change had kind {kind!r}; use one of {", ".join(handlers)}.')
        return handlers[kind](item, final)

    def named(self, value, final):
        return drafting.checked_names(value, self.allowed, self.data, self.seed, final)

    def field(self, item, final):
        field = item.get('field')
        if field not in HELPER_FIELDS:
            raise drafting.Unusable(f'"{field}" is not a field you may change. Change only: {", ".join(HELPER_FIELDS)}.')
        if not self.context.definition:
            raise drafting.Unusable('there is no character to change yet.')
        value = self.named(helper_value(field, item.get('value'), final), final)
        if field == 'routine':
            week = drafting.schedule_value(self.context.definition.get('schedule'))
            value = drafting.agreeing_routine(value, week)[:drafting.TEXT_LIMITS['routine']]
        return {'kind': 'field', 'field': field, 'value': value}

    def message(self, item) -> dict:
        row = self.context.messages.get(item.get('ref'))
        if row is None:
            raise drafting.Unusable(f'{item.get("ref")!r} is not one of the messages you were shown.')
        return row

    def reply(self, item, final):
        row = self.message(item)
        if row['role'] != 'companion':
            raise drafting.Unusable(f"[{item.get('ref')}] is the user's own message; only {self.context.name}'s "
                                    'replies can be edited.')
        text = drafting.text_value(item.get('text'), 8000)
        if not text:
            raise drafting.Unusable('a reply edit had no "text".')
        return {'kind': 'reply', 'message_id': row['id'], 'before': row['text'], 'text': self.named(text, final),
                'created_at': row['created_at']}

    def remembered(self, item) -> dict:
        memory = self.context.memories.get(item.get('ref'))
        if memory is None:
            raise drafting.Unusable(f'{item.get("ref")!r} is not one of the memories you were shown.')
        return memory

    def memory(self, item, _final):
        memory = self.remembered(item)
        value = memory_value(item.get('value'), memory['layer'], memory['subject'])
        if not value:
            raise drafting.Unusable('a memory change had no "value".')
        return {'kind': 'memory', 'memory_id': memory['id'], 'revision': memory['revision'], 'layer': memory['layer'],
                'subject': memory['subject'], 'before': memory['value'], 'value': value}

    def new_memory(self, item, _final):
        layer, subject = item.get('layer'), drafting.text_value(item.get('subject'), 200)
        value = memory_value(item.get('value'), layer, subject)
        if layer not in NEW_MEMORY_LAYERS or not subject or not value:
            raise drafting.Unusable(f'a new memory needs "layer" (one of {", ".join(NEW_MEMORY_LAYERS)}), '
                                    '"subject" and "value".')
        return {'kind': 'new_memory', 'layer': layer, 'subject': subject, 'value': value}

    def forget(self, item, _final):
        memory = self.remembered(item)
        return {'kind': 'forget_memory', 'memory_id': memory['id'], 'layer': memory['layer'],
                'subject': memory['subject'], 'before': memory['value']}


async def chat(state, body) -> dict:
    """One sidecar message: a reply, and proposed changes the user reviews. Nothing is stored or applied."""
    config = connection_config(state.database)
    context = Context(state.database, body)
    data = context.city(state.database)
    system = drafting.fill(
        drafting.template('sidecar.md', state.database), rules=drafting.template('character-rules.md', state.database),
        city=drafting.city_text(data), emotional=drafting.FIELD_EDGES, fields=fields_text(), name=context.name,
        view=focus_text(context, body.view), character=context.character_text(),
        conversation=context.conversation_text(), memories=context.memories_text())
    messages = [{'role': turn.role, 'content': turn.content} for turn in body.history]
    messages.append({'role': 'user', 'content': body.message})
    while messages and messages[0]['role'] != 'user':
        messages.pop(0)
    allowed = naming.allowed_words(context.character_text(), context.conversation_text(), context.memories_text(),
                                   *(turn['content'] for turn in messages), data)
    proposals = Proposals(context, allowed, data, identifier())
    return await drafting.ask(state, config, system, SIDECAR_TOKENS, proposals, messages)

