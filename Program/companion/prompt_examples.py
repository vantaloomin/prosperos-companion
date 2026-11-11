"""A reworded prompt's own JSON examples must be ones the app can read (docs/model-bounds.md).

The model copies a prompt's example replies, so an edit in Settings > Advanced whose example the app's parser
throws away teaches the model to write replies that get dropped. Before an edit is saved, each example it still
has is read by the same code that reads the model's real reply. Taking an example out is fine; only an example
the app could not use is refused. The shipped defaults are guarded the same way by tests/test_bounds_audit.py.
"""
import json
import re

# `"what was said" [with "key": value] [answering "question"] gives [the reply]`, one per line.
EXAMPLE = re.compile(r'^"(?P<said>.*?)"(?: with "(?P<key>\w+)": (?P<given>\[.*?\]|".*?"))?'
                     r'(?: answering "(?P<answering>.*)")? gives (?P<reply>\[.*\])$', re.MULTILINE)
# Filled in for the placeholders an example may use, as the tests do.
STAND_INS = {'name': 'Rae'}
FIX = 'Fix it or take it out.'


def filled(text: str) -> str:
    return re.sub(r'\{\{(\w+)\}\}', lambda match: STAND_INS.get(match[1], ''), text)


def short(said: str) -> str:
    return said if len(said) <= 60 else said[:57] + '...'


def unreadable(said: str) -> str:
    return f'The example answer for "{short(said)}" is not JSON the app can read. {FIX}'


def dropped(said: str) -> str:
    return (f'The example answer for "{short(said)}" is one the app would throw away, so the model would learn to '
            f'write answers that get dropped. {FIX}')


def memory_batch(example) -> list[dict]:
    to = example['given'].strip('"') if example['key'] == 'to' else ''
    return [{'text': example['said'], 'to': to, 'names': [], 'known': []}]


def self_batch(example) -> list[dict]:
    return [{'text': example['said'], 'answering': example['answering'] or ''}]


def memory_kept(item, batch) -> bool:
    from companion.memory import suggest
    item = {key: value for key, value in item.items() if key != 'corrects'}  # Named against rows in the database.
    return suggest.candidate(item, batch) is not None


def self_kept(item, batch) -> bool:
    from companion.memory import self_suggest
    return self_suggest.fact(item, batch) is not None


def answers(batch_for, kept):
    """A check for a prompt whose examples are `"..." gives [...]` lines read by the memory parsers."""
    def check(text: str) -> str | None:
        from companion.memory import suggest
        for example in EXAMPLE.finditer(text):
            try:
                items = suggest.parse(example['reply'])
            except suggest.SuggestionsInvalid:
                return unreadable(example['said'])
            if not all(kept(item, batch_for(example)) for item in items):
                return dropped(example['said'])
        return None
    return check


def life_phrasing(text: str) -> str | None:
    from companion.life import synthesis
    for found in re.findall(r'\{"summary".*?\}', text):
        try:
            shape = json.loads(found)
        except json.JSONDecodeError:
            return f'The example reply {found} is not JSON the app can read. {FIX}'
        if set(shape) != set(synthesis.LIMITS):
            return f'The example reply must have exactly "summary" and "post"; {found} does not. {FIX}'
    return None


def schedule_problem(shape: dict) -> str | None:
    if not {'name', 'identity', 'schedule'} <= set(shape):
        return 'The example character must keep "name", "identity" and "schedule". ' + FIX
    blocks = shape['schedule'] if isinstance(shape['schedule'], list) else [None]
    for block in blocks:
        days = block.get('days') if isinstance(block, dict) else None
        if not isinstance(days, list) or not all(type(day) is int and 0 <= day <= 6 for day in days):
            return ('Each schedule block in the example character needs "days" as numbers 0 (Monday) to 6 (Sunday). '
                    + FIX)
    return None


def character(text: str) -> str | None:
    from companion import drafting
    start, end = text.find('\n{\n'), text.find('\n}\n')
    if start < 0 or end < start:
        return None
    try:
        shape = drafting.parse_object(text[start:end + 2])
    except drafting.Unusable as problem:
        return f'The example character cannot be read: {problem}'.rstrip('.') + f'. {FIX}'
    return schedule_problem(shape)


SIDECAR_KINDS = ('field', 'reply', 'memory', 'new_memory', 'forget_memory', 'authors_note')


def sidecar(text: str) -> str | None:
    for line in re.findall(r'^- (\{"kind".*\})$', text, re.MULTILINE):
        kind = re.search(r'"kind": "(\w*)"', line)
        if not kind or kind[1] not in SIDECAR_KINDS:
            return f'An example change has a kind the app does not take. Use one of {", ".join(SIDECAR_KINDS)}. {FIX}'
        if '"value": the' in line:  # The field example's value stands for any shape.
            continue
        try:
            json.loads(line)
        except json.JSONDecodeError:
            return f'The example change {line[:80]} is not JSON the app can read. {FIX}'
    return None


CHECKS = {'memory-suggestions': answers(memory_batch, memory_kept), 'self-facts': answers(self_batch, self_kept),
          'life-phrasing': life_phrasing,
          'character-draft.md': character, 'character-split.md': character, 'sidecar.md': sidecar}


def problems(name: str, wording: str) -> str | None:
    """Why an example in this wording would be thrown away by the app, or None."""
    check = CHECKS.get(name)
    return check(filled(wording)) if check else None
