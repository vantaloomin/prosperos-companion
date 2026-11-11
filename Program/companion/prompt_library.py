"""The core prompts a power user may reword in Settings > Advanced (docs/prompts.md).

Each prompt's default lives where it is used: a module constant written for `str.format`, or one of
the character drafting files in `companion/prompts/`. Here they are shown and stored in one form,
with `{{placeholder}}` marks the app fills in. A user's wording is stored in `prompt_overrides`
with the default it replaced, so an update that changes the default can say so without touching
their text. Wording is checked before it is saved: every placeholder the default uses must stay,
and no unknown one may be added, so a typo cannot break replies. A JSON example the wording keeps must be
one the app's own parser would accept (companion/prompt_examples.py), so the model is not taught a reply
that gets thrown away.

The picture prompts' pieces (the Pictures group) are the words the rule-based prompt builder
(companion/images/prompts.py) strings together, not a prompt sent whole: a plain line, or a list
with one "name: words" line per entry. Their defaults are the builder's own constants, so they
fill exactly as the code did until reworded.

Only the wording is editable. The in-character filter, OOC handling, the NSFW check and every
reply's validation are code (companion/in_character.py and the callers) and run whatever it says.
"""
import re
from contextlib import contextmanager
from contextvars import ContextVar
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


def to_format(text: str) -> str:
    """Back to a `str.format` template: `{{name}}` → `{name}`, any other brace doubled."""
    return re.sub(r'\{\{(\w+)\}\}|[{}]', lambda match: '{' + match[1] + '}' if match[1] else match[0] * 2, text)


def table(module: str, name: str, skip=()):
    """A dict constant shown as one "name: words" line per entry (a Pictures list); `skip` leaves out the entries
    that only copy another one."""
    return lambda: '\n'.join(f'{key}: {from_format(value)}' for key, value in getattr(import_module(module), name).items()
                             if key not in skip)


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
    # A list of "name: words" lines (`table`): every name stays, and a line may use any of the placeholders or none.
    lines: bool = False
    # A list the user may add their own names to (a mood the app has no line for), not only reword.
    more: bool = False
    # What one entry of a list is called in its error messages: (one, several).
    noun: tuple[str, str] = ('entry', 'entries')


CHAT, DRAFTING, SIDECAR, PICTURES = 'Chat and life', 'Character drafting', 'Sidecar', 'Pictures'
IMAGES = 'companion.images.prompts'
PRONOUN_HELP = {'subject': 'they, she or he', 'possessive': 'their, her or his', 'object': 'them, her or him'}
PROMPTS = {prompt.name: prompt for prompt in (
    Prompt('chat-character', CHAT, 'Who the companion is',
           'Opens every chat reply and first text, before the character sheet, memories and the day. '
           'Staying in character and OOC answers are also enforced by the app, so they keep working '
           'whatever this says.',
           constant('companion.memory.context', 'GUIDANCE'),
           {'name': "the companion's name", 'relationship': 'the relationship framing from the character'}),
    Prompt('chat-personality', CHAT, 'How the companion acts',
           "Follows the character sheet in every chat reply and first text: one line of behaviour for each of the "
           "companion's personality sliders that isn't in the middle (Character > Life details > Personality).",
           constant('companion.memory.context', 'PERSONALITY'),
           {'lines': 'what their personality sliders say, one behaviour per line'}),
    Prompt('our-history', CHAT, 'Your history together',
           'Opens the line-a-week (then a month, then a year) record of your whole time together in every chat reply. '
           'The lines come from what happened and your corrections in the scrapbook\'s "All of it" view.',
           constant('companion.memory.history', 'INTRO')),
    Prompt('voice', CHAT, 'How they sound',
           "Opens the few short excerpts of the companion's own earlier replies in every chat reply, so they keep "
           'sounding like themselves when the model changes. The app picks the excerpts from replies you kept, and '
           '"Pin their voice" in a reply\'s menu pins one.',
           constant('companion.memory.voice', 'INTRO')),
    Prompt('first-texts', CHAT, 'Texting first',
           'Added when the companion writes to you first, such as a check-in. The app picks the reason.',
           constant('companion.life.openers', 'INSTRUCTION'),
           {'reason': 'why the companion is writing, from the life sim'}),
    Prompt('feed-comment-reply', CHAT, 'Answering comments on their posts',
           'Added when the companion answers a comment you left under one of their posts on the feed. The app '
           'decides when the answer shows; staying in character is enforced as in chat.',
           constant('companion.life.post_comments', 'COMPANION_REPLY'),
           {'post': 'what their post says', 'comment': 'your comment',
            'earlier': 'the comments before it on the post, if any'}),
    Prompt('feed-comment-friend', CHAT, "Friends answering comments",
           "Who a friend is when they answer a comment you left under their post: someone from the companion's "
           'circle, who knows you only through the companion. The app writes the rest of their sheet.',
           constant('companion.life.post_comments', 'FRIEND_REPLY'),
           {'who': 'their name, who they are to the companion and their work', 'host': "the companion's first name",
            'lines': 'how others see them and how they see themselves', 'post': 'what their post says',
            'comment': 'your comment', 'earlier': 'the comments before it on the post, if any'}),
    Prompt('voice-notes', CHAT, 'Voice notes',
           'Added to a first text that the app decided to send as a voice note. The app picks when and the voice; '
           'emoji, links and *actions* are left out of what is read aloud whatever this says.',
           constant('companion.voice.notes', 'INSTRUCTION')),
    Prompt('life-phrasing', CHAT, 'Phrasing life events',
           'Turns a life sim moment into a sentence and a feed caption. A reply that changes the facts or '
           'breaks the JSON shape is thrown away and the template wording kept.',
           constant('companion.life.synthesis', 'RULES'),
           {'name': "the companion's name"}),
    Prompt('planned-week', CHAT, "What's on their mind this week",
           'With "Let the model add what\'s on their mind" on (Settings > Life), asks the life model once a week for a '
           "few lines on what is on the open companion's mind. The app checks each line and drops any that names a day, a time "
           'or a person the week does not have, or a big life event.',
           constant('companion.life.planned_week', 'FILL'),
           {'name': "the companion's name", 'card': 'who they are, from the character sheet',
            'facts': 'what the rules decided for the week: their day, work or classes, the job and plans'}),
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
    Prompt('story-narrator', CHAT, 'The Story narrator',
           'Opens every reply in the Story tab, before the scene: the place, the hour, the weather and who is '
           'there, which the app decides. OOC answers are also enforced by the app.',
           constant('companion.story', 'NARRATOR')),
    Prompt('authors-note', CHAT, "Author's note",
           "Goes right before your author's note, the last thing the model reads before your message in a chat "
           'that has a note switched on. Your note follows this line.',
           constant('companion.authors_note', 'HEADER')),
    Prompt('group-rules', CHAT, 'Group chats',
           'Opens every reply in a group chat, before who is in the group and the chat so far. Each person still '
           "answers only from what they know, which the app decides; staying in character is enforced as in 1:1 chats.",
           constant('companion.groups', 'RULES')),
    Prompt('group-first-texts', CHAT, 'Groups starting a conversation',
           'Added when someone in a group chat starts a conversation on their own. The app picks who speaks and '
           'what from their day they share; the others then answer as usual.',
           constant('companion.group_openers', 'INSTRUCTION'),
           {'name': "the member's name", 'news': 'what happened in their day, from the life sim'}),
    Prompt('group-guest', CHAT, 'Guests in group chats',
           "Who a guest is, in their own reply: someone from a member's circle or around town who joined the chat. "
           'The app picks who comes in and writes the rest of their sheet; the group rules and staying in '
           'character apply as for everyone.',
           constant('companion.group_guests', 'SHEET'),
           {'who': 'their name, who they are to the member who knows them, and their work',
            'host': 'the member who brought them in', 'lines': 'how others see them and how they see themselves'}),
    Prompt('character-rules.md', DRAFTING, 'What makes a character believable', 'Sent with every draft and rewrite.',
           drafting_file('character-rules.md')),
    Prompt('character-draft.md', DRAFTING, 'Drafting a whole character',
           'The quick start. Asks for the full character as JSON.', drafting_file('character-draft.md'),
           {'rules': 'the believable-character prompt', 'picks': 'your idea and choices',
            'city': 'the home city', 'careers': 'occupations to choose from', 'names': 'common names there',
            'emotional': 'whether emotional edges are allowed',
            'perception': 'the bank of how others see them and how they see themselves'}),
    Prompt('character-field.md', DRAFTING, 'Rewriting one field', 'The "Help me write" buttons in the character form.',
           drafting_file('character-field.md'),
           {'rules': 'the believable-character prompt', 'character': 'the character as it stands',
            'city': 'the home city', 'emotional': 'the emotional-edges rule', 'field': "the field's name",
            'field_guide': 'what that field is for', 'field_shape': "the field's JSON shape",
            'request': 'what you asked for, if anything'}),
    Prompt('character-split.md', DRAFTING, 'Splitting a character you paste in',
           'The paste box on the quick start and the character helper. Splits a whole character into the fields.',
           drafting_file('character-split.md'),
           {'rules': 'the believable-character prompt', 'pasted': 'the character you pasted', 'city': 'the home city',
            'careers': 'occupations to choose from', 'names': 'common names there',
            'emotional': 'whether emotional edges are allowed'}),
    Prompt('character-repair.md', DRAFTING, 'Retrying an unusable reply', 'Sent once when a reply could not be used.',
           drafting_file('character-repair.md'), {'problem': 'what was wrong with the reply'}),
    Prompt('sidecar.md', SIDECAR, 'The sidecar',
           'The chat beside the app that reads the character, the conversation and the memories and proposes '
           'changes you apply or dismiss. Only you see it; the companion never does.',
           drafting_file('sidecar.md'),
           {'name': "the companion's name", 'view': 'where you are in the app', 'character': 'the character',
            'city': 'the home city', 'conversation': 'the recent conversation', 'memories': 'the memories',
            'rules': 'the believable-character prompt', 'emotional': 'the emotional-edges rule',
            'fields': 'the character fields it may change', 'note': "the chat's author's note"}),
    Prompt('image-negative', PICTURES, 'What pictures leave out',
           'The negative prompt of every picture a model makes, on the backends that take one. A Booru model adds its '
           'own quality tags to it.',
           constant(IMAGES, 'NEGATIVE')),
    Prompt('image-openings', PICTURES, 'How a picture opens',
           'What follows the style line: a plain moment, a selfie, a view, or a moment with you (scene) and with you '
           'in it (scene_both). The names are fixed; change only the words.',
           table(IMAGES, 'OPENINGS'), PRONOUN_HELP, lines=True, noun=('opening', 'openings')),
    Prompt('image-cameras', PICTURES, 'Camera details',
           'The camera line that ends a photo-style picture, for each kind of shot. The names are fixed; change only '
           'the words.',
           table(IMAGES, 'CAMERAS', skip=('scene_both',)), lines=True, noun=('camera detail', 'camera details')),
    Prompt('image-moods', PICTURES, 'Faces for each mood',
           'How their face looks for each mood. A mood that isn\'t listed is drawn as "a (mood) expression". Add a line '
           'to give it its own.',
           table(IMAGES, 'EXPRESSIONS'), lines=True, more=True, noun=('mood', 'moods')),
    Prompt('image-activities', PICTURES, 'What each activity looks like',
           "What they're doing in a picture of their day. The place and the company are added for you. The names are "
           'fixed; change only the words.',
           table(IMAGES, 'PICTURES'), PRONOUN_HELP, lines=True, noun=('activity', 'activities')),
)}

LINE = re.compile(r'^\s*([\w][\w -]*?)\s*:\s?(.*)$')


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


def entries(text: str) -> tuple[dict[str, str], list[tuple[int, str]]]:
    """A list prompt's "name: words" lines as a dict, with the lines that are not one or repeat a name: (line number,
    the name, or '' for a line with no colon)."""
    found, bad = {}, []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        match = LINE.match(line)
        if match and match[1] not in found:
            found[match[1]] = match[2].strip()
        else:
            bad.append((number, match[1] if match else ''))
    return found, bad


def quoted(names: list[str]) -> str:
    marks = [f'"{name}"' for name in names]
    return marks[0] if len(marks) == 1 else f"{', '.join(marks[:-1])} and {marks[-1]}"


# The connection the picture prompt builder reads its pieces with (`reading`); without one they are the defaults.
READING: ContextVar = ContextVar('picture_words', default=None)


@contextmanager
def reading(connection):
    """Picture pieces (`words`, `line`) read with the user's wording while the block runs."""
    token = READING.set(connection)
    try:
        yield
    finally:
        READING.reset(token)


def line(name: str) -> str:
    """A plain Pictures piece in use, as written."""
    return text(READING.get(), name)


def words(name: str) -> dict[str, str]:
    """A Pictures list in use as `str.format` templates: the user's lines, with the default's for any name a newer
    default added since they saved."""
    default = entries(PROMPTS[name].default())[0]
    found = entries(text(READING.get(), name))[0]
    extra = {key: value for key, value in found.items() if key not in default} if PROMPTS[name].more else {}
    return {key: to_format(value) for key, value in (default | {key: found.get(key, value) for key, value in
                                                                default.items()} | extra).items()}


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
            'placeholders': keys, 'lines': prompt.lines, 'more': prompt.more,
            'placeholder_help': {key: prompt.placeholders.get(key, '') for key in keys}}


def views(database) -> list[dict]:
    with database.connect() as connection:
        return [view(connection, name) for name in PROMPTS]


def list_problems(prompt: Prompt, default: str, wording: str) -> str | None:
    """Why a list's wording cannot be used, naming only the lines at fault (the full list is its default wording): a
    line with no colon, a name twice, a name left out, or one the app has no line for."""
    known, _ = entries(default)
    found, bad = entries(wording)
    one, several = prompt.noun
    if bad:
        number, name = bad[0]
        return f'"{name}" is listed twice. Keep one line for it.' if name else \
            f'Line {number} needs a colon after the name.'
    if missing := [key for key in known if key not in found]:
        verb = 'is' if len(missing) == 1 else 'are'
        return f'{quoted(missing)} {verb} missing. Keep every name, and leave its words empty to say nothing.'
    if not prompt.more and (unknown := [key for key in found if key not in known]):
        what = f"isn't {'an' if one[0] in 'aeiou' else 'a'} {one}" if len(unknown) == 1 else f"aren't {several}"
        return (f"{quoted(unknown)} {what} the app draws, and new ones can't be added here. Change only the words "
                'after each name. Default wording lists every name.')
    return placeholder_problems(default, wording, required=False)


def problems(default: str, wording: str) -> str | None:
    """Why the wording would break the prompt, in words the user can act on, or None."""
    return placeholder_problems(default, wording)


def placeholder_problems(default: str, wording: str, required=True) -> str | None:
    allowed = set(placeholders(default))
    missing = [key for key in sorted(allowed) if required and '{{' + key + '}}' not in wording]
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
    prompt = PROMPTS[name]
    if problem := (list_problems(prompt, default, wording) if prompt.lines else problems(default, wording)):
        raise DomainError(problem, 422, 'prompt_placeholders')
    if problem := import_module('companion.prompt_examples').problems(name, wording):
        raise DomainError(problem, 422, 'prompt_example')
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
