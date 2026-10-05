"""Writing one routine slot as an ordinary fictional event (PRD T2, T3).

The model sees the character, the routine block and the latest committed events for continuity.
It never sees the user's memories: a life event is the companion's own fiction and must not
describe what the user did. Output that is not a usable event leaves the slot uneventful.
"""
import json

from companion.memory.context import character_text
from companion.providers.chat import INCOMPLETE
from companion.providers.scheduling import LIFE_SYNTHESIS, BackgroundInterrupted

PROMPT_VERSION = 'life-slot-1'
RULES = (
    "Write one ordinary moment from {name}'s own fictional life during the routine block the user message "
    'describes. Reply with JSON only, in this shape: {{"quiet": false, "summary": "...", "post": "...", '
    '"mood": "..."}}. "summary" is one or two plain past-tense sentences in the third person about what {name} '
    'did. "post" is an optional short private caption in {name}\'s own voice, as for a personal photo feed. '
    '"mood" is one or two words. Keep it ordinary and consistent with the recent events listed. A quiet, '
    'uneventful stretch is fine: then reply {{"quiet": true}}. Never include the user or describe anything the '
    'user did, said or felt. No promises, no major life changes (moving, new partners, a new job, illness, '
    'breakups) and no claims about real-world news.'
)
LIMITS = {'summary': 400, 'post': 400, 'mood': 40}
UNUSABLE = 'The model reply was not a usable event.'


class SynthesisInvalid(Exception):
    pass


def slot_text(slot, recent) -> str:
    block = slot['block']
    lines = [f"Routine block: {block['label']} ({block['kind']}), {block['start']}–{block['end']} "
             f"on {slot['local_date']}, your local time."]
    if block['themes']:
        lines.append('Themes you may draw on: ' + ', '.join(block['themes']) + '.')
    if recent:
        lines.append('Recent events in your life, oldest first:')
        lines.extend(f"- {event['starts_at'][:10]}: {event['summary']}" for event in recent)
    return '\n'.join(lines)


def system_text(version) -> str:
    definition = version['definition']
    lines = [character_text(version), RULES.format(name=definition['name'])]
    if definition.get('life_themes'):
        lines.append('Themes the user chose for your everyday life: ' + ', '.join(definition['life_themes']) + '.')
    return '\n\n'.join(lines)


def parse_reply(text: str) -> dict | None:
    start, end = text.find('{'), text.rfind('}')
    if start < 0 or end <= start:
        raise SynthesisInvalid(UNUSABLE)
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError as error:
        raise SynthesisInvalid(UNUSABLE) from error
    if not isinstance(data, dict):
        raise SynthesisInvalid(UNUSABLE)
    if data.get('quiet') is True:
        return None
    result = {}
    for field, limit in LIMITS.items():
        value = data.get(field, '')
        if not isinstance(value, str) or len(value.strip()) > limit:
            raise SynthesisInvalid(UNUSABLE)
        result[field] = value.strip()
    if not result['summary']:
        raise SynthesisInvalid(UNUSABLE)
    return result | {'prompt_version': PROMPT_VERSION}


async def synthesize(provider, scheduler, config, key, version, slot, recent) -> dict | None:
    """Background priority: a conversation request interrupts this and the batch resumes later."""
    text = []
    async with scheduler.reserve(config, LIFE_SYNTHESIS) as lease:
        async for chunk in provider.stream(config, key, system_text(version),
                                           [{'role': 'user', 'content': slot_text(slot, recent)}]):
            if lease.stop.is_set():
                raise BackgroundInterrupted()
            text.append(chunk.text)
            if chunk.finish_reason in INCOMPLETE:
                raise SynthesisInvalid(INCOMPLETE[chunk.finish_reason])
    return parse_reply(''.join(text))
