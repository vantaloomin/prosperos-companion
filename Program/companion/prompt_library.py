"""The core prompts a power user may reword in Settings > Advanced (docs/prompts.md).

Each prompt's default lives where it is used: a module constant written for `str.format`, or one of
the character drafting files in `companion/prompts/`. Here they are shown and stored in one form,
with `{{placeholder}}` marks the app fills in. A user's wording is stored in `prompt_overrides`
with the default it replaced, so an update that changes the default can say so without touching
their text. Wording is checked before it is saved: every placeholder the default uses must stay,
and no unknown one may be added, so a typo cannot break replies.

Only the wording is editable. The in-character filter, OOC handling, the NSFW check and every
reply's validation are code (companion/in_character.py and the callers) and run whatever it says.
"""
import re
from dataclasses import dataclass, field
from importlib import import_module

from companion.database import optional
from companion.errors import DomainError

PLACEHOLDER = re.compile(r'\{\{(\w+)\}\}')
# `{name}` with single braces: almost certainly a placeholder typed the wrong way.
SINGLE = re.compile(r'(?<!\{)\{(\w+)\}(?!\})')
FORMAT_TOKEN = re.compile(r'\{\{|\}\}|\{(\w+)\}')


def from_format(text: str) -> str:
    """A `str.format` template in the `{{placeholder}}` form: `{name}` → `{{name}}`, `{{` → `{`."""
    return FORMAT_TOKEN.sub(lambda match: '{{' + match[1] + '}}' if match[1] else match[0][0], text)


def constant(module: str, name: str):
    """A module constant read when needed, so an update to the code is the new default at once."""
    return lambda: from_format(getattr(import_module(module), name))


def drafting_file(name: str):
    return lambda: (import_module('companion.drafting').PROMPTS / name).read_text(encoding='utf-8')


@dataclass(frozen=True)
class Prompt:
    name: str
    group: str
    label: str
    description: str
    default: object  # () -> str
    placeholders: dict[str, str] = field(default_factory=dict)


CHAT, DRAFTING = 'Chat and life', 'Character drafting'
PROMPTS = {prompt.name: prompt for prompt in (
    Prompt('chat-character', CHAT, 'Who the companion is',
           'Opens every chat reply and first text, before the character sheet, memories and the day. '
           'Staying in character and OOC answers are also enforced by the app, so they keep working '
           'whatever this says.',
           constant('companion.memory.context', 'GUIDANCE'),
           {'name': "the companion's name", 'relationship': 'the relationship framing from the character'}),
    Prompt('first-texts', CHAT, 'Texting first',
           'Added when the companion writes to you first, such as a check-in. The app picks the reason.',
           constant('companion.life.openers', 'INSTRUCTION'),
           {'reason': 'why the companion is writing, from the life sim'}),
    Prompt('life-phrasing', CHAT, 'Phrasing life events',
           'Turns a life sim moment into a sentence and a feed caption. A reply that changes the facts or '
           'breaks the JSON shape is thrown away and the template wording kept.',
           constant('companion.life.synthesis', 'RULES'),
           {'name': "the companion's name"}),
    Prompt('memory-suggestions', CHAT, 'Suggesting memories',
           'Asks the memory model which facts in your messages are worth remembering. What it finds is saved '
           'automatically and can be corrected on the Memories page; replies in the wrong shape are ignored.',
           constant('companion.memory.suggest', 'RULES')),
    Prompt('self-facts', CHAT, "Noting the companion's own facts",
           "Asks the memory model what the companion's replies say about their own life (people, pets, team, "
           'work), so later replies keep those the same. Answers must use the reply\'s own words.',
           constant('companion.memory.self_suggest', 'RULES'), {'name': "the companion's name"}),
    Prompt('picture-description', CHAT, 'Describing your pictures',
           'Sent with each picture you send, to the "Seeing pictures" model. The description is what the '
           'companion sees.',
           constant('companion.pictures', 'DESCRIBE')),
    Prompt('character-rules.md', DRAFTING, 'What makes a character believable', 'Sent with every draft and rewrite.',
           drafting_file('character-rules.md')),
    Prompt('character-draft.md', DRAFTING, 'Drafting a whole character',
           'The quick start. Asks for the full character as JSON.', drafting_file('character-draft.md'),
           {'rules': 'the believable-character prompt', 'picks': 'your idea and choices',
            'city': 'the home city', 'careers': 'occupations to choose from', 'names': 'common names there',
            'emotional': 'whether emotional edges are allowed'}),
    Prompt('character-field.md', DRAFTING, 'Rewriting one field', 'The "Help me write" buttons in the character form.',
           drafting_file('character-field.md'),
           {'rules': 'the believable-character prompt', 'character': 'the character as it stands',
            'city': 'the home city', 'emotional': 'the emotional-edges rule', 'field': "the field's name",
            'field_guide': 'what that field is for', 'field_shape': "the field's JSON shape",
            'request': 'what you asked for, if anything'}),
    Prompt('character-repair.md', DRAFTING, 'Retrying an unusable reply', 'Sent once when a reply could not be used.',
           drafting_file('character-repair.md'), {'problem': 'what was wrong with the reply'}),
)}


def placeholders(text: str) -> list[str]:
    return sorted(set(PLACEHOLDER.findall(text)))


def fill(text: str, /, **values: str) -> str:
    for key, value in values.items():
        text = text.replace('{{' + key + '}}', value)
    return text


def require(name: str) -> Prompt:
    if name not in PROMPTS:
        raise DomainError(f'No editable prompt named {name!r}.', 404, 'unknown_prompt')
    return PROMPTS[name]


def override(connection, name: str) -> dict | None:
    return optional(connection, 'SELECT text, default_text FROM prompt_overrides WHERE name=?', (name,))


def text(connection, name: str, /, **values: str) -> str:
    """The wording in use, the user's when they reworded it, with `values` filled in."""
    row = override(connection, name) if connection is not None else None
    return fill(row['text'] if row else PROMPTS[name].default(), **values)


def view(connection, name: str) -> dict:
    prompt = PROMPTS[name]
    default, row = prompt.default(), override(connection, name)
    keys = placeholders(default)
    return {'name': name, 'group': prompt.group, 'label': prompt.label, 'description': prompt.description,
            'text': row['text'] if row else default, 'default': default, 'customized': row is not None,
            # Saved against an older default: the user's wording stays, with a note that a newer one exists.
            'outdated': bool(row and row['default_text'] is not None and row['default_text'] != default),
            'placeholders': keys,
            'placeholder_help': {key: prompt.placeholders.get(key, '') for key in keys}}


def views(database) -> list[dict]:
    with database.connect() as connection:
        return [view(connection, name) for name in PROMPTS]


def problems(default: str, wording: str) -> str | None:
    """Why the wording would break the prompt, in words the user can act on, or None."""
    allowed = set(placeholders(default))
    missing = [key for key in sorted(allowed) if '{{' + key + '}}' not in wording]
    unknown = [key for key in placeholders(wording) if key not in allowed]
    single = [key for key in sorted(set(SINGLE.findall(wording))) if key in allowed]
    marks = lambda keys: ', '.join('{{' + key + '}}' for key in keys)  # noqa: E731
    if single:
        return f'Use double braces for the parts the app fills in: write {marks(single)}.'
    if missing:
        return f'Keep these placeholders in the prompt: {marks(missing)}.'
    if unknown:
        known = f' It can fill in {marks(sorted(allowed))}.' if allowed else ' This prompt has none.'
        return f'The app does not fill in {marks(unknown)}, so it would be sent as written.{known}'
    return None


def save(database, name: str, wording: str) -> dict:
    require(name)
    default = PROMPTS[name].default()
    if problem := problems(default, wording):
        raise DomainError(problem, 422, 'prompt_placeholders')
    with database.connect(write=True) as connection:
        if wording == default:
            connection.execute('DELETE FROM prompt_overrides WHERE name=?', (name,))
        else:
            connection.execute(
                'INSERT INTO prompt_overrides (name, text, default_text, updated_at) VALUES (?, ?, ?, ?) '
                'ON CONFLICT(name) DO UPDATE SET text=excluded.text, default_text=excluded.default_text, '
                'updated_at=excluded.updated_at', (name, wording, default, database.now()))
        return view(connection, name)


def reset(database, name: str) -> dict:
    require(name)
    with database.connect(write=True) as connection:
        connection.execute('DELETE FROM prompt_overrides WHERE name=?', (name,))
        return view(connection, name)
