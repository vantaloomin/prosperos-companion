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

from companion import prompt_library, texting
from companion.database import identifier
from companion.errors import DomainError
from companion.models import CharacterDefinition, EmotionalTrait, RoutineBlock
from companion.providers.scheduling import Work
from companion.text_models import config_for, key_for
from companion.traits import ABSENCE_WORDS
from companion.world import catalog, custom, generators, naming

PROMPT_VERSION = 'character-draft-3'
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

    def __init__(self, problem: str, reply: str = ''):
        super().__init__(problem)
        self.reply = reply


def template(name: str, database=None) -> str:
    """The user's wording from Settings > Advanced when there is one, otherwise the shipped file.

    The four `.md` prompts are editable (companion/prompt_library.py); the field guides stay a shipped file.
    """
    if database is not None and name in prompt_library.PROMPTS:
        with database.connect() as connection:
            return prompt_library.text(connection, name)
    return (PROMPTS / name).read_text(encoding='utf-8')


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


NO_CITY = naming.DEFAULT_CITY
DECADES = {'twent': 25, 'thirt': 35, 'fort': 45, 'fift': 55, 'sixt': 65, 'sevent': 75}


def age_value(text: str) -> int | None:
    """The age a quick-start pick means ("thirties", "34", "sixty or older"), if any."""
    text = (text or '').lower()
    if found := re.search(r'\d{2}', text):
        return int(found[0])
    return next((age for stem, age in DECADES.items() if stem in text), None)


def names_text(data: dict | None, seed: str, age: str = '') -> str:
    """Names drawn from what people of their age and city were actually called, for the model to choose from."""
    data, wanted = data or NO_CITY, age_value(age)
    ages = [wanted + offset for offset in (-3, 0, 2, -1, 3, 1, -2, 0)] if wanted else [26, 31, 36, 41, 46, 51, 56, 29]
    names = {generators.name(data, seed=f'{seed}-{index}', age=max(18, value))['full']: value
             for index, value in enumerate(ages)}
    listed = ', '.join(names) if wanted else ', '.join(f'{full} (about {value})' for full, value in names.items())
    others = ', '.join(dict.fromkeys(
        generators.name(data, seed=f'{seed}-other-{index}', age=max(18, (wanted or 38) + offset))['given']
        for index, offset in enumerate((28, 26, -2, 3, -5, 30))))
    return ('Unless the user named them, choose one of these names, which people their age commonly have where '
            f'they live: {listed}. For family and friends their background mentions, use ordinary given names '
            f'such as {others}.')


def invented_problem(found: list[str], data: dict | None, seed: str) -> str:
    spare = ', '.join(generators.name(data or NO_CITY, seed=f'{seed}-spare-{index}')['given'] for index in range(4))
    return (f'it used names that read as made up ({", ".join(found)}). Real people are rarely called that; use '
            f'ordinary names such as {spare}.')


def replace_invented(value, found: list[str], data: dict | None, seed: str):
    """The text with each invented-sounding name swapped for an ordinary one, the same one each time."""
    if not found:
        return value
    swaps = {word: generators.name(data or NO_CITY, seed=f'{seed}-swap-{word.casefold()}')[
        'family' if word.casefold() in {item.casefold() for item in naming.data()['invented']['family']} else 'given']
        for word in found}
    pattern = re.compile(r'\b(' + '|'.join(map(re.escape, swaps)) + r')\b')
    if isinstance(value, str):
        return pattern.sub(lambda match: swaps[match[0]], value)
    if isinstance(value, list):
        return [replace_invented(item, found, data, seed) for item in value]
    if isinstance(value, dict):
        return {key: replace_invented(item, found, data, seed) for key, item in value.items()}
    return value


def checked_names(value, allowed: str, data: dict | None, seed: str, final: bool):
    """A model's text with no invented-sounding names: refused on the first reply, swapped out on the retry.

    Names the user typed or the world data contains are allowed (a user may want an Elara)."""
    found = naming.invented_in(json.dumps(value, ensure_ascii=False), allowed)
    if found and not final:
        raise Unusable(invented_problem(found, data, seed))
    return replace_invented(value, found, data, seed)


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
        config = config_for(connection, 'drafting')
    if config is None:
        raise DomainError('Add a text model in Settings > Models to draft a character.', 409, 'no_connection')
    return config


def draft_tokens(config: dict, tokens: int) -> int:
    """Room for a whole character, within what the model reports it can write."""
    ceiling = (config.get('reported_capabilities') or {}).get('max_output_tokens')
    wanted = max(config['max_output_tokens'], tokens)
    return min(wanted, ceiling) if ceiling else wanted


async def complete(state, config: dict, system: str, messages: list[dict], tokens: int) -> str:
    config = {**config, 'max_output_tokens': draft_tokens(config, tokens)}
    key = key_for(state.vault, config)
    conversation, text = state.conversation, []
    async with conversation.scheduler.reserve(config, DRAFTING):
        async for chunk in conversation.provider.stream(config, key, system, messages):
            text.append(chunk.text)
            if chunk.finish_reason == 'content_filter':
                raise DomainError("The provider's content filter stopped the draft.", 502, 'provider')
            if chunk.finish_reason == 'length':
                raise Unusable('it stopped at the output token limit before the JSON was complete. Write less.',
                               ''.join(text))
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


async def ask(state, config, system: str, tokens: int, shape, messages: list[dict] | None = None):
    """One request and, if the reply cannot be used, one retry that names the problem.

    `shape(raw, final)` is strict on the first reply; on the retry it makes do where it can.
    `messages` is a conversation to answer (the character helper); otherwise the model is asked for the JSON.
    """
    messages = messages or [{'role': 'user', 'content': 'Write the JSON now.'}]
    reply = ''
    try:
        reply = await complete(state, config, system, messages, tokens)
        return shape(parse_object(reply), False)
    except Unusable as problem:
        # A reply cut off at the output limit arrives with the problem rather than as a return value.
        reply = reply or problem.reply
        retry = [*messages, *([{'role': 'assistant', 'content': reply[:6000]}] if reply.strip() else []),
                 {'role': 'user', 'content': fill(template('character-repair.md', state.database), problem=str(problem))}]
    try:
        return shape(parse_object(await complete(state, config, system, retry, tokens)), True)
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


DAY_NAMES = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')
DAY_WORDS = {name.lower(): (index,) for index, name in enumerate(DAY_NAMES)} | {
    'weekday': tuple(range(5)), 'weeknight': tuple(range(5)), 'weekend': (5, 6)}
DAY = '(' + '|'.join(DAY_WORDS) + ')s?'
DAY_SPAN = re.compile(rf"\b{DAY}(?:\s*(?:to|through|thru|-|–)\s*{DAY})?(?:'s)?\b", re.IGNORECASE)
BUSY_KINDS = {'work', 'study'}
BUSY_WORDS = re.compile(r'\b(?:work\w*|shifts?|office|job|class(?:es)?|lectures?)\b', re.IGNORECASE)
OFF_WORDS = re.compile(r"\b(?:off|free|no|not|never|don'?t|doesn'?t|sleeps? in|lie-?ins?|rest\w*)\b", re.IGNORECASE)
WORD = re.compile(r'[a-z]{3,}')
FILLER = {'and', 'the', 'for', 'are', 'with', 'her', 'his', 'their', 'she', 'him', 'they', 'mine', 'every', 'usually',
          'spend', 'spends', 'spent', 'always', 'most', 'some', 'its', 'that', 'this', 'then', 'when', 'all', 'day',
          'days', 'morning', 'mornings', 'afternoon', 'afternoons', 'evening', 'evenings', 'night', 'nights', 'goes',
          'going', 'out', 'what', 'from', 'into', 'over', 'about', 'like', 'just', 'get', 'gets', 'has', 'have', 'was'}


def named_days(text: str) -> set[int]:
    """The weekdays a phrase names: "Saturdays", "weekends", "Monday to Thursday"."""
    days = set()
    for match in DAY_SPAN.finditer(text):
        first, last = DAY_WORDS[match[1].lower()], DAY_WORDS[(match[2] or match[1]).lower()]
        if match[2] and len(first) == len(last) == 1:
            days.update((first[0] + step) % 7 for step in range((last[0] - first[0]) % 7 + 1))
        else:
            days.update(first + last)
    return days


def stems(text: str) -> set[str]:
    return {word[:5] for word in WORD.findall(DAY_SPAN.sub(' ', text.lower())) if word not in FILLER}


def clause_agrees(clause: str, blocks: list[dict]) -> bool:
    """Whether a clause's weekday claim fits the schedule: work on work days, time off on days off, and a
    named activity ("Saturdays at the rink") on a day with a block that shares a word with it."""
    days = named_days(clause)
    if not days:
        return True
    busy = {day for item in blocks if item['kind'] in BUSY_KINDS for day in item['days']}
    if OFF_WORDS.search(clause):
        return not days & busy
    if BUSY_WORDS.search(clause):
        return days <= busy
    words = stems(clause)
    return all(any(day in item['days'] and words & stems(' '.join([item['label'], *item['themes']]))
                   for item in blocks if item['kind'] != 'sleep') for day in days)


def clauses(sentence: str) -> list[str]:
    """A sentence's clauses; a list of days ("Wednesday, Friday and Sunday") stays with the clause it ends."""
    result, waiting = [], ''
    for part in re.split(r'[,;:]|\bbut\b', sentence):
        if not stems(part):
            if result:
                result[-1] += f',{part}'
            else:
                waiting += f'{part},'
        else:
            result.append(waiting + part)
            waiting = ''
    return result or [waiting]


def minutes(value: str) -> int:
    hours, rest = value.split(':')
    return int(hours) * 60 + int(rest)


def days_text(days: list[int]) -> str:
    if len(days) > 2 and days == list(range(days[0], days[-1] + 1)):
        return f'{DAY_NAMES[days[0]]} to {DAY_NAMES[days[-1]]}'
    names = [DAY_NAMES[day] for day in days]
    return ' and '.join(names) if len(names) < 3 else f"{', '.join(names[:-1])} and {names[-1]}"


def schedule_text(blocks: list[dict]) -> str:
    """The week the schedule sets: "Works 12-hour shifts Wednesday, Friday and Sunday, 07:00-19:30."."""
    lines = []
    for item in blocks:
        when = f"{days_text(item['days'])}, {item['start']}-{item['end']}."
        if item['kind'] in BUSY_KINDS:
            hours = (minutes(item['end']) - minutes(item['start'])) % 1440 // 60
            verb = 'Works' if item['kind'] == 'work' else 'Studies'
            lines.append(f'{verb} {hours}-hour shifts {when}' if hours >= 10 else f'{verb} {when}')
        elif item['kind'] not in {'sleep', 'rest'} and len(item['days']) < 5:
            lines.append(f"{item['label']}: {when}")
    return ' '.join(lines)


def agreeing_routine(text: str, blocks: list[dict]) -> str:
    """The routine prose without the sentences whose weekdays the schedule contradicts, with the schedule's own
    week said in their place, so the chat context never names work days or standing plans the life lacks."""
    if not text or not blocks:
        return text
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    kept = [sentence for sentence in sentences if all(clause_agrees(clause, blocks) for clause in clauses(sentence))]
    if len(kept) == len(sentences):
        return text
    return ' '.join([*kept, schedule_text(blocks)]).strip()


class Draft:
    """Turns the quick start's model reply into a definition the app accepts."""

    def __init__(self, body, data: dict | None, offered: dict[str, dict], seed: str):
        self.body, self.data, self.offered, self.seed = body, data, offered, seed

    def __call__(self, raw: dict, final: bool) -> dict:
        definition = {key: text_value(raw.get(key), limit) for key, limit in TEXT_LIMITS.items()}
        definition |= {key: list_value(raw.get(key), *limits) for key, limits in LIST_LIMITS.items()}
        allowed = naming.allowed_words(self.body.name, self.body.idea, self.body.vibe, self.data)
        definition = checked_names(definition, allowed, self.data, self.seed, final)
        definition['name'] = self.body.name.strip() or definition['name']
        missing = [key for key in REQUIRED if not definition[key]]
        if missing:
            raise Unusable(f"it left out {', '.join(missing)}.")
        career_id = raw.get('career') if raw.get('career') in self.offered else ''
        career = self.offered.get(career_id)
        definition |= life(raw, career, self.seed, final) | self.placed()
        definition['routine'] = agreeing_routine(definition['routine'], definition['schedule'])[:TEXT_LIMITS['routine']]
        if texting.LOWERCASE.search(definition['voice']):
            definition['texting'] = {'lowercase': True}
        definition['money'] = {'career': career_id}
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
                  city=city_text(data), careers=careers_text(offered), names=names_text(data, seed, body.age),
                  emotional=EDGES if edges_allowed(body) else NO_EDGES)
    return await ask(state, config, system, DRAFT_TOKENS, Draft(body, data, offered, seed))


# --- One field --------------------------------------------------------------------------------

def unwrapped(field: str, value):
    """The field itself when a model nested JSON in "value": the whole character, or `"voice": "..."`."""
    if not isinstance(value, str):
        return value
    text = value.strip()
    if text.startswith(f'"{field}"'):
        text = '{' + text.rstrip(',') + '}'
    if not text.startswith('{'):
        return value
    try:
        inner = json.loads(text)
    except json.JSONDecodeError:
        return value
    return inner.get(field, inner.get('value', value)) if isinstance(inner, dict) else value


def field_value(field: str, raw: dict, final: bool):
    value = unwrapped(field, raw.get('value'))
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
    allowed = naming.allowed_words(character_json(body.definition), body.request, data)
    seed = identifier()

    def shape(raw, final):
        return checked_names(field_value(body.field, raw, final), allowed, data, seed, final)

    value = await ask(state, config, system, FIELD_TOKENS, shape)
    return {'field': body.field, 'value': value, 'prompt_version': PROMPT_VERSION}
