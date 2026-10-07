"""The character helper: a sidecar beside the character form, after the Collaborator in Prospero's Study.

Two requests, both made only when the user asks and both returning proposals that nothing saves:

- `split`: a whole character the user already has (pasted, or read from a character card) is split
  into the form's fields by one model call. Their text wins over the drafting guidance; fields it says
  nothing about are filled in and named, so the form can show which ones to check.
- `chat`: one message in the helper's conversation, with the form as it stands. The reply says what
  changed and proposes new values for named fields, which the user applies or dismisses one by one.

Both reuse the drafting checks in companion/drafting.py: the same model job (Character drafting),
the same one-retry repair, the same field shaping and the same invented-name check. The world stays
the app's: a city is only ever one from the catalogue that the pasted text names. See
docs/character-drafting.md.
"""
import re
from dataclasses import dataclass

from companion import drafting
from companion.database import identifier
from companion.errors import DomainError
from companion.world import catalog, custom, naming

HELPER_TOKENS = 3000
# Fields the helper may change. Relationship, home city and emotional traits are the user's own picks.
HELPER_FIELDS = ('name', 'identity', 'personality', 'voice', 'skills', 'flaws', 'interests', 'background',
                 'appearance', 'routine', 'location', 'life_themes', 'schedule')
EXTRA_GUIDES = {'name': ('their full name.', 'a string'), 'location': ('where they live, in general terms.', 'a string')}
SPLIT_FIELDS = set(HELPER_FIELDS) - {'name', 'location'}
# Aliases shorter than this ("LV", "SD") match too much ordinary text.
ALIAS_LENGTH = 4


@dataclass
class SplitBody:
    """The parts of a quick-start request `drafting.Draft` reads, for a pasted character."""
    idea: str
    relationship: str
    timezone: str
    emotional_edges: bool
    name: str = ''
    vibe: str = ''


def mentioned_city(text: str, cities: dict[str, dict]) -> dict | None:
    """The catalogue city the text names first, by name or a distinctive alias, if any."""
    found = []
    for data in cities.values():
        for word in {data['name'], *[alias for alias in data.get('aliases', []) if len(alias) >= ALIAS_LENGTH]}:
            if match := re.search(rf'(?<!\w){re.escape(word)}(?!\w)', text):
                found.append((match.start(), data['id'], data))
    return min(found)[2] if found else None


class Split(drafting.Draft):
    """A pasted character shaped like a quick-start draft, plus which fields the model had to fill in."""

    def __call__(self, raw: dict, final: bool) -> dict:
        if raw.get('under_18') is True:
            raise DomainError('Companions are always adults, and this character reads as younger than 18. '
                              'Change their age in the text, or start from the quick start.', 422, 'under_18')
        result = super().__call__(raw, final)
        filled = raw.get('filled_in') if isinstance(raw.get('filled_in'), list) else []
        result['filled_in'] = [key for key in dict.fromkeys(filled) if key in SPLIT_FIELDS]
        return result


async def split(state, body) -> dict:
    """A whole pasted character split into the form's fields, for review; nothing is saved."""
    config = drafting.connection_config(state.database)
    data = mentioned_city(body.text, catalog.cities() | custom.read(state.database))
    seed = identifier()
    offered = drafting.careers(data)
    request = SplitBody(idea=body.text, relationship=body.relationship, timezone=body.timezone,
                        emotional_edges=body.emotional_edges)
    system = drafting.fill(
        drafting.template('character-split.md', state.database),
        rules=drafting.template('character-rules.md', state.database),
        city=drafting.city_text(data), careers=drafting.careers_text(offered), names=drafting.names_text(data, seed),
        emotional=drafting.EDGES if drafting.edges_allowed(request) else drafting.NO_EDGES,
        # Last, so braces in the user's own text are never read as placeholders.
        pasted=body.text)
    result = await drafting.ask(state, config, system, drafting.DRAFT_TOKENS, Split(request, data, offered, seed))
    return result | {'home_city': data['name'] if data else ''}


# --- The conversation -------------------------------------------------------------------------

def fields_text() -> str:
    guides = drafting.field_guides() | {key: {'guide': guide, 'shape': shape} for key, (guide, shape) in EXTRA_GUIDES.items()}
    return '\n'.join(f"- {key} ({guides[key]['shape']}): {guides[key]['guide']}" for key in HELPER_FIELDS)


def helper_value(field: str, value, final: bool):
    if field in ('name', 'location'):
        found = drafting.text_value(value, drafting.TEXT_LIMITS[field])
        if not found:
            raise drafting.Unusable(f'"{field}" was empty.')
        return found
    return drafting.field_value(field, {'value': value}, final)


class Reply:
    """The helper's reply and proposed field changes; a change it cannot use is refused once, then dropped."""

    def __init__(self, allowed: str, data: dict | None, seed: str, schedule: list[dict]):
        self.allowed, self.data, self.seed, self.schedule = allowed, data, seed, schedule

    def __call__(self, raw: dict, final: bool) -> dict:
        reply = drafting.text_value(raw.get('reply'), 2000)
        proposed = raw.get('changes') if isinstance(raw.get('changes'), dict) else {}
        changes = {}
        for field, value in proposed.items():
            if field not in HELPER_FIELDS:
                if not final:
                    raise drafting.Unusable(f'it changed "{field}", which the helper may not change. '
                                            f'Change only: {", ".join(HELPER_FIELDS)}.')
                continue
            try:
                changes[field] = drafting.checked_names(helper_value(field, value, final), self.allowed, self.data,
                                                        self.seed, final)
            except drafting.Unusable as problem:
                if not final:
                    raise drafting.Unusable(f'the change to "{field}" could not be used: {problem}') from problem
        if 'routine' in changes:
            # The routine prose must agree with the week the form will have, as in a draft.
            week = changes.get('schedule') or self.schedule
            changes['routine'] = drafting.agreeing_routine(changes['routine'], week)[:drafting.TEXT_LIMITS['routine']]
        if not reply:
            if not final:
                raise drafting.Unusable('"reply" was empty.')
            reply = 'Here is what I would change.' if changes else 'I could not find anything to change.'
        return {'reply': reply, 'changes': changes, 'prompt_version': drafting.PROMPT_VERSION}


async def chat(state, body) -> dict:
    """One helper message: a short reply and proposed changes to named fields of the form as it stands."""
    config = drafting.connection_config(state.database)
    city_id = body.definition.get('home_city')
    try:
        data = drafting.home(state.database, city_id if isinstance(city_id, str) else '')
    except DomainError:
        data = None
    character = drafting.character_json(body.definition)
    system = drafting.fill(drafting.template('character-helper.md', state.database),
                           rules=drafting.template('character-rules.md', state.database), character=character,
                           city=drafting.city_text(data), emotional=drafting.FIELD_EDGES, fields=fields_text())
    messages = [{'role': turn.role, 'content': turn.content} for turn in body.history]
    messages.append({'role': 'user', 'content': body.message})
    # A conversation must open with the user; a dangling reply at the start is dropped.
    while messages and messages[0]['role'] != 'user':
        messages.pop(0)
    allowed = naming.allowed_words(character, *(turn['content'] for turn in messages), data)
    schedule = drafting.schedule_value(body.definition.get('schedule'))
    return await drafting.ask(state, config, system, HELPER_TOKENS, Reply(allowed, data, identifier(), schedule), messages)

