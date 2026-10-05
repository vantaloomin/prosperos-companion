"""Character drafting: the configured text model helps write a character, once, at the user's request.

The quick start sends a short idea and a few picks; the model drafts the whole definition as JSON
following the editable prompts in `companion/prompts/`. The world stays the app's: the home city,
its occupations and its common names come from the static world data, and the model only chooses
among them. Every draft is normalised and validated here, retried once with the problem named, and
otherwise refused so the user can fill in the form themselves. Nothing is saved: the draft goes back
to the form for review. See docs/character-drafting.md.
"""
import json
import re
from pathlib import Path

from pydantic import ValidationError

from companion.database import identifier, optional
from companion.errors import DomainError
from companion.models import CharacterDefinition, EmotionalTrait, RoutineBlock
from companion.providers.scheduling import Work
from companion.providers.vault import credential_for
from companion.traits import ABSENCE_WORDS
from companion.world import catalog, custom, generators

PROMPT_VERSION = 'character-draft-1'
PROMPTS = Path(__file__).parent / 'prompts'
# Requested by the user and waited on, so it goes ahead of background life and memory work.
DRAFTING = Work(5, 'character drafting')
# A whole character is longer than a chat reply; the connection's own limit applies when it is higher.
DRAFT_TOKENS, FIELD_TOKENS = 4000, 1500
EDGE_WORDS = (*ABSENCE_WORDS, 'jealous', 'possessive', 'envious', 'clingy', 'needy')
TEXT_LIMITS = {'name': 120, 'identity': 4000, 'personality': 8000, 'voice': 4000, 'background': 12000,
               'appearance': 4000, 'routine': 8000, 'location': 200, 'absence_reaction': 2000}
LIST_LIMITS = {'skills': (20, 300), 'flaws': (20, 300), 'interests': (50, 120), 'life_themes': (20, 120)}
REQUIRED = ('name', 'identity', 'personality')
NO_EDGES = ('Leave "emotional_traits" as [] and "absence_reaction" as "". The user has not asked for jealousy, '
            'guilt over absence or similar traits, and the app adds none unless they do.')
EDGES = ('The user asked for emotional edges. You may add up to 3 "emotional_traits", each {"name": short name, '
         '"intensity": "mild" | "moderate" | "strong", "note": how it shows}, and an "absence_reaction" sentence, '
         'but only ones their idea supports.')
FIELD_EDGES = 'Do not add jealousy, guilt over absence, possessiveness or neediness unless the character already has them.'


class Unusable(Exception):
    """The model's reply could not become a definition; the message says why, for the one retry."""


# The prompts a user may reword in Settings; the field guides stay a shipped file.
EDITABLE = {
    'character-rules.md': ('What makes a character believable', 'Sent with every draft and rewrite.'),
    'character-draft.md': ('Drafting a whole character', 'The quick start. Asks for the full character as JSON.'),
    'character-field.md': ('Rewriting one field', 'The "Help me write" buttons in the character form.'),
    'character-repair.md': ('Retrying an unusable reply', 'Sent once when a reply could not be used.'),
}


def template(name: str, database=None) -> str:
    """The user's wording from Settings when there is one, otherwise the shipped file."""
    if database is not None and name in EDITABLE:
        with database.connect() as connection:
            row = optional(connection, 'SELECT text FROM prompt_overrides WHERE name=?', (name,))
        if row:
            return row['text']
    return (PROMPTS / name).read_text(encoding='utf-8')


def placeholders(text: str) -> list[str]:
    return sorted(set(re.findall(r'\{\{(\w+)\}\}', text)))


def prompt_view(database, name: str) -> dict:
    label, description = EDITABLE[name]
    default, text = template(name), template(name, database)
    return {'name': name, 'label': label, 'description': description, 'text': text, 'default': default,
            'customized': text != default, 'placeholders': placeholders(default)}


def prompts(database) -> list[dict]:
    return [prompt_view(database, name) for name in EDITABLE]


def require_editable(name: str):
    if name not in EDITABLE:
        raise DomainError(f'No editable prompt named {name!r}.', 404, 'unknown_prompt')


def save_prompt(database, name: str, text: str) -> dict:
    """A rewording must keep every placeholder the app fills in, or drafts would lose their inputs."""
    require_editable(name)
    missing = [key for key in placeholders(template(name)) if '{{' + key + '}}' not in text]
    if missing:
        raise DomainError('Keep these placeholders in the prompt: ' + ', '.join('{{' + key + '}}' for key in missing)
                          + '.', 422, 'missing_placeholders')
    with database.connect(write=True) as connection:
        connection.execute('INSERT INTO prompt_overrides (name, text, updated_at) VALUES (?, ?, ?) ON CONFLICT(name) '
                           'DO UPDATE SET text=excluded.text, updated_at=excluded.updated_at',
                           (name, text, database.now()))
    return prompt_view(database, name)


def reset_prompt(database, name: str) -> dict:
    require_editable(name)
    with database.connect(write=True) as connection:
        connection.execute('DELETE FROM prompt_overrides WHERE name=?', (name,))
    return prompt_view(database, name)


def fill(text: str, **values: str) -> str:
    for key, value in values.items():
        text = text.replace('{{' + key + '}}', value)
    return text


def field_guides() -> dict[str, dict]:
    return json.loads(template('character-fields.json'))


# --- World context from the static data -------------------------------------------------------

def home(database, city_id: str) -> dict | None:
    return catalog.city(city_id, custom.read(database)) if city_id else None


def city_text(data: dict | None) -> str:
    if data is None:
        return 'No home city is set. Keep where they live general: a region or a kind of place is fine.'
    return (f"{data['name']}, {data['region']}, {data['country']} (setting: {data['setting']}, era: {data['era']}). "
            f"{data['summary']} The app supplies its neighbourhoods and places.")


def careers(data: dict | None) -> dict[str, dict]:
    if data:
        return catalog.careers_for(data)
    return {key: career for key, career in catalog.careers().items() if 'modern' in career['eras']}


def careers_text(offered: dict[str, dict]) -> str:
    return '\n'.join(f"- {key}: {career['name']} ({career['schedule']} hours). {career['summary']}"
                     for key, career in sorted(offered.items()))


def names_text(data: dict | None, seed: str) -> str:
    if data is None:
        return 'Unless the user named them, choose a plain name that fits their age and background.'
    names = dict.fromkeys(generators.name(data, seed=f'{seed}-{index}')['full'] for index in range(8))
    return ('Unless the user named them, choose one of these names, which are common where they live, or a '
            'similar one: ' + ', '.join(names) + '.')


def edges_allowed(body) -> bool:
    words = f'{body.idea} {body.vibe}'.lower()
    return body.emotional_edges or any(word in words for word in EDGE_WORDS)


def picks_text(body) -> str:
    picks = [('Idea', body.idea or 'None given. Surprise them with someone ordinary and specific.'),
             ('Name', body.name), ('Relationship to the user', body.relationship), ('Age', body.age),
             ('Vibe', body.vibe)]
    return '\n'.join(f'- {label}: {value}' for label, value in picks if value)


# --- Calling the model ------------------------------------------------------------------------

def connection_config(database) -> dict:
    with database.connect() as connection:
        config = optional(connection, 'SELECT * FROM connection WHERE id=1')
    if config is None:
        raise DomainError('Connect a text model in Settings to draft a character.', 409, 'no_connection')
    return config


async def complete(state, config: dict, system: str, messages: list[dict], tokens: int) -> str:
    config = {**config, 'max_output_tokens': max(config['max_output_tokens'], tokens)}
    key = credential_for(state.vault, config['credential_ref'])
    conversation, text = state.conversation, []
    async with conversation.scheduler.reserve(config, DRAFTING):
        async for chunk in conversation.provider.stream(config, key, system, messages):
            text.append(chunk.text)
            if chunk.finish_reason == 'content_filter':
                raise DomainError("The provider's content filter stopped the draft.", 502, 'provider')
            if chunk.finish_reason == 'length':
                raise Unusable('it stopped at the output token limit before the JSON was complete. Write less.')
    return ''.join(text)


def parse_object(text: str) -> dict:
    """The JSON object in a reply, ignoring a reasoning block, a Markdown fence or a sentence around it."""
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    start, end = text.find('{'), text.rfind('}')
    if start < 0 or end < start:
        raise Unusable('it did not contain a JSON object.')
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError as error:
        raise Unusable(f'the JSON was malformed ({error.msg}).') from error
    if not isinstance(data, dict):
        raise Unusable('it was not a JSON object.')
    return data


async def ask(state, config, system: str, tokens: int, shape):
    """One request and, if the reply cannot be used, one retry that names the problem.

    `shape(raw, final)` is strict on the first reply; on the retry it makes do where it can.
    """
    messages = [{'role': 'user', 'content': 'Write the JSON now.'}]
    reply = await complete(state, config, system, messages, tokens)
    try:
        return shape(parse_object(reply), False)
    except Unusable as problem:
        retry = [*messages, {'role': 'assistant', 'content': reply[:6000]},
                 {'role': 'user', 'content': fill(template('character-repair.md', state.database), problem=str(problem))}]
        reply = await complete(state, config, system, retry, tokens)
    try:
        return shape(parse_object(reply), True)
    except Unusable as problem:
        raise DomainError(f"The model's draft could not be used: {problem} Try again, or fill in the form yourself.",
                          502, 'draft_unusable') from problem


# --- Normalising what came back ---------------------------------------------------------------

def text_value(value, limit: int) -> str:
    return value.strip()[:limit] if isinstance(value, str) else ''


def list_value(value, count: int, limit: int) -> list[str]:
    items = value if isinstance(value, list) else [value] if isinstance(value, str) else []
    seen, result = set(), []
    for item in items:
        text = item.strip()[:limit] if isinstance(item, str) else ''
        if text and text.lower() not in seen:
            seen.add(text.lower())
            result.append(text)
    return result[:count]


def block(item) -> dict | None:
    if not isinstance(item, dict):
        return None
    days = item.get('days')
    try:
        return RoutineBlock.model_validate({
            'label': text_value(item.get('label'), 120), 'kind': item.get('kind') or 'leisure',
            'days': sorted({day for day in days if isinstance(day, int)}) if isinstance(days, list) else days,
            'start': item.get('start'), 'end': item.get('end'),
            'themes': list_value(item.get('themes'), 10, 120)}).model_dump()
    except (ValidationError, TypeError):
        return None


def schedule_value(value) -> list[dict]:
    return [found for found in map(block, value if isinstance(value, list) else []) if found][:24]


def traits_value(value) -> list[dict]:
    traits = []
    for item in value if isinstance(value, list) else []:
        try:
            traits.append(EmotionalTrait.model_validate({
                'name': text_value(item.get('name'), 60), 'intensity': item.get('intensity') or 'mild',
                'note': text_value(item.get('note'), 500)}).model_dump())
        except (ValidationError, AttributeError):
            continue
    return traits[:3]


SLEEP_PROBLEM = 'the schedule needs sleep blocks that cover every day, 0 to 6.'


def sleeps_every_day(blocks: list[dict]) -> bool:
    return {day for item in blocks if item['kind'] == 'sleep' for day in item['days']} == set(range(7))


def life(raw: dict, career: dict | None, seed: str, final: bool) -> dict:
    """The routine and themes the life simulation follows; the career's own pattern when the draft's won't do."""
    blocks, themes = schedule_value(raw.get('schedule')), list_value(raw.get('life_themes'), *LIST_LIMITS['life_themes'])
    if not sleeps_every_day(blocks):
        if not final:
            raise Unusable(SLEEP_PROBLEM)
        blocks = generators.schedule(career, seed) if career else blocks
    if not themes and career:
        themes = list(career['themes'])
    return {'schedule': blocks, 'life_themes': themes}


class Draft:
    """Turns the quick start's model reply into a definition the app accepts."""

    def __init__(self, body, data: dict | None, offered: dict[str, dict], seed: str):
        self.body, self.data, self.offered, self.seed = body, data, offered, seed

    def __call__(self, raw: dict, final: bool) -> dict:
        definition = {key: text_value(raw.get(key), limit) for key, limit in TEXT_LIMITS.items()}
        definition |= {key: list_value(raw.get(key), *limits) for key, limits in LIST_LIMITS.items()}
        definition['name'] = self.body.name.strip() or definition['name']
        missing = [key for key in REQUIRED if not definition[key]]
        if missing:
            raise Unusable(f"it left out {', '.join(missing)}.")
        career_id = raw.get('career') if raw.get('career') in self.offered else ''
        career = self.offered.get(career_id)
        definition |= life(raw, career, self.seed, final) | self.placed()
        if edges_allowed(self.body):
            definition['emotional_traits'] = traits_value(raw.get('emotional_traits'))
        else:
            definition['absence_reaction'] = ''
        try:
            valid = CharacterDefinition.model_validate(definition).model_dump()
        except ValidationError as error:
            raise Unusable(f"it did not fit the character format ({error.errors()[0]['msg']}).") from error
        return {'definition': valid, 'career': career, 'prompt_version': PROMPT_VERSION}

    def placed(self) -> dict:
        """Where they live, their clock and the relationship are the user's picks, never the model's."""
        picked = {'relationship': self.body.relationship, 'home_city': self.data['id'] if self.data else '',
                  'timezone': self.data['timezone'] if self.data else self.body.timezone}
        if self.data:
            picked['location'] = f"{self.data['name']}, {self.data['region']}"
        return picked


async def draft(state, body) -> dict:
    """The quick start: a whole character drafted from a short idea and the user's picks."""
    config = connection_config(state.database)
    data, seed = home(state.database, body.home_city), identifier()
    offered = careers(data)
    system = fill(template('character-draft.md', state.database), rules=template('character-rules.md', state.database),
                  picks=picks_text(body),
                  city=city_text(data), careers=careers_text(offered), names=names_text(data, seed),
                  emotional=EDGES if edges_allowed(body) else NO_EDGES)
    return await ask(state, config, system, DRAFT_TOKENS, Draft(body, data, offered, seed))


# --- One field --------------------------------------------------------------------------------

def field_value(field: str, raw: dict, final: bool):
    value = raw.get('value')
    if field == 'schedule':
        found = schedule_value(value)
        if not found:
            raise Unusable('the schedule had no usable blocks.')
        if not final and not sleeps_every_day(found):
            raise Unusable(SLEEP_PROBLEM)
        return found
    found = list_value(value, *LIST_LIMITS[field]) if field in LIST_LIMITS else text_value(value, TEXT_LIMITS[field])
    if not found:
        raise Unusable('"value" was empty or the wrong type.')
    return found


def character_json(definition: dict) -> str:
    keys = ('name', 'relationship', 'identity', 'personality', 'voice', 'skills', 'flaws', 'interests', 'background',
            'appearance', 'routine', 'location', 'life_themes', 'schedule', 'emotional_traits', 'absence_reaction')
    return json.dumps({key: definition[key] for key in keys if definition.get(key)}, ensure_ascii=False, indent=1)


async def redo_field(state, body) -> dict:
    """A new version of one field, in keeping with the rest of the character as it stands in the form."""
    config = connection_config(state.database)
    city_id = body.definition.get('home_city')
    try:
        data = home(state.database, city_id if isinstance(city_id, str) else '')
    except DomainError:
        data = None
    guide = field_guides()[body.field]
    request = f'What the user wants from it: {body.request}' if body.request else ''
    system = fill(template('character-field.md', state.database), rules=template('character-rules.md', state.database),
                  character=character_json(body.definition), city=city_text(data), emotional=FIELD_EDGES,
                  field=body.field, field_guide=guide['guide'], request=request, field_shape=guide['shape'])
    value = await ask(state, config, system, FIELD_TOKENS, lambda raw, final: field_value(body.field, raw, final))
    return {'field': body.field, 'value': value, 'prompt_version': PROMPT_VERSION}
