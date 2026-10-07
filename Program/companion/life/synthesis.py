"""Optional model phrasing of a composed event (PRD T2, T3).

The composer has already decided what happened and where. The model only rewrites the wording
in the character's voice; it is told not to add places, people, prices or events, and a reply
that drops the named place or breaks the format is discarded in favour of the template text.
It never sees the user's memories: a life event is the companion's own fiction.
"""
import json
import re

from companion.memory.context import character_text
from companion.providers.chat import INCOMPLETE
from companion.providers.scheduling import LIFE_SYNTHESIS, BackgroundInterrupted

PROMPT_VERSION = 'life-phrase-2'
RULES = (
    "Rephrase one ordinary moment from {name}'s fictional life, described as facts in the user message. Reply "
    'with JSON only: {{"summary": "...", "post": "..."}}. "summary" is one or two plain past-tense sentences in '
    'the third person. "post" is a short private caption in {name}\'s own voice, as for a personal photo feed. '
    'Keep exactly the given facts: do not add or change places, people, prices, times or events, and keep any '
    'place name exactly as written. The time is only context: never write clock times. Never include the user or '
    'anything the user did.'
)
# A clock time ("17:30-19:30 on the medians") is the routine block's, never something a person would write.
CLOCK = re.compile(r'\b\d{1,2}:\d{2}\b')
LIMITS = {'summary': 400, 'post': 300}
UNUSABLE = 'The model reply was not usable wording, so the template wording was kept.'


class SynthesisInvalid(Exception):
    pass


def facts_text(slot, composed) -> str:
    block, place = slot['block'], composed['place']
    facts = {'routine_block': block['label'], 'local_date': slot['local_date'],
             'time': f"{block['start']}–{block['end']}", 'activity': composed['activity'],
             'summary': composed['summary'], 'caption': composed['post'], 'mood': composed['mood']}
    if place:
        facts['place'] = place['name']
        if place['neighborhood']:
            facts['neighborhood'] = place['neighborhood']
    return json.dumps(facts, ensure_ascii=False)


def parse_reply(text: str, composed) -> dict:
    start, end = text.find('{'), text.rfind('}')
    if start < 0 or end <= start:
        raise SynthesisInvalid(UNUSABLE)
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError as error:
        raise SynthesisInvalid(UNUSABLE) from error
    if not isinstance(data, dict):
        raise SynthesisInvalid(UNUSABLE)
    result = {}
    for field, limit in LIMITS.items():
        value = data.get(field)
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit or CLOCK.search(value):
            raise SynthesisInvalid(UNUSABLE)
        result[field] = value.strip()
    if composed['place'] and composed['place']['name'] not in result['summary']:
        raise SynthesisInvalid(UNUSABLE)
    return result


async def phrase(provider, scheduler, config, key, version, slot, composed) -> dict:
    """Background priority: a conversation request interrupts this and the batch resumes later."""
    text = []
    system = character_text(version) + '\n\n' + RULES.format(name=version['definition']['name'])
    async with scheduler.reserve(config, LIFE_SYNTHESIS) as lease:
        async for chunk in provider.stream(config, key, system, [{'role': 'user',
                                                                 'content': facts_text(slot, composed)}]):
            if lease.stop.is_set():
                raise BackgroundInterrupted()
            text.append(chunk.text)
            if chunk.finish_reason in INCOMPLETE:
                raise SynthesisInvalid(UNUSABLE)
    return parse_reply(''.join(text), composed)
