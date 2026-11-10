"""Keep model numbers in bounds (Feature Hit List #98, docs/model-bounds.md).

Two halves. Each number a model, a service or old data hands the world gets a floor, a cap or a fallback, tested
here with the garbage that broke it. And every JSON prompt's own example reply is read by the code that reads the
model's real reply, so a prompt edit can't ship an example the app throws away (Cairn idea 7).
"""
import json
import re
from datetime import date

import pytest

from companion import drafting, prompt_library, sidecar
from companion.life import ages, pets, synthesis
from companion.mcp import weather
from companion.memory import dates, self_suggest, suggest
from companion.world.draft import polish


def default(prompt: str, /, **values: str) -> str:
    return prompt_library.fill(prompt_library.PROMPTS[prompt].default(), **values)


# --- Floors, caps and fallbacks ---------------------------------------------------------------------------------

@pytest.mark.parametrize(('today', 'past', 'expected'), [
    (date(2028, 3, 1), False, date(2029, 2, 28)),  # next February 29 is in a year without one
    (date(2028, 2, 28), True, date(2027, 2, 28)),  # last one too
    (date(2028, 2, 1), False, date(2028, 2, 29)),  # this year has one
])
def test_february_29_never_breaks_a_date(today, past, expected):
    span = dates.month_day('february', 29, today, past)
    assert span.start == expected
    assert span.certain is (expected.day == 29)


def test_a_day_no_month_has_is_still_no_date():
    assert dates.month_day('april', 31, date(2026, 11, 4), False) is None


def test_leap_day_in_a_message_resolves():
    from datetime import UTC, datetime
    span = dates.resolve('my birthday is February 29', datetime(2028, 3, 1, 12, tzinfo=UTC), 'UTC')
    assert span is not None and span.start == date(2029, 2, 28)


@pytest.mark.parametrize('structured', [
    {'high_f': 9999}, {'high_f': float('inf')}, {'temp_c': float('nan')}, {'low_f': -400},
])
def test_weather_service_garbage_is_no_reading(structured):
    assert weather.readings('', structured) == []
    assert weather.conditions_from('', structured) is None


def test_weather_garbage_falls_back_to_the_text():
    assert weather.readings('High 72°F, low 58°F', {'high_f': float('inf')}) == [72, 58]


def test_weather_structured_reading_still_counts():
    assert weather.readings('', {'high_c': 20.0, 'low_c': 10}) == [68, 50]


def test_json_infinity_from_a_service_is_no_reading():
    structured = json.loads('{"high_f": Infinity, "low_f": NaN}')
    assert weather.readings('', structured) == []


def test_an_age_older_than_the_calendar_is_born_in_year_1():
    """A drafted elf "3000 years old" in 2026: birth dates no longer fall before year 1."""
    born = ages.born_from(3000, '05-04', date(2026, 11, 4))
    assert born == date(1, 5, 4)
    row = {'from_age': 3000, 'born_on': born.isoformat(), 'birthday': '05-04'}
    assert ages.age_from(row, date(2027, 6, 1)) == 3000


def test_ordinary_ages_are_unchanged():
    assert ages.born_from(34, '05-04', date(2026, 11, 4)) == date(1992, 5, 4)


def test_a_pet_described_as_ancient_still_has_a_birth_date():
    item = {'id': 'p1', 'name': 'Rex', 'variety': 'dog', 'since': '2026-01-01',
            'description': 'a scruffy terrier, about 99999 years old'}
    found = pets.from_home_item(item, 'modern', date(2026, 1, 1))
    assert found['born'].year == 2026 - pets.OLDEST_LEGACY


@pytest.mark.parametrize('index', [True, False, 1.0, '1', 0, 2, None])
def test_model_memory_answers_name_a_real_message(index):
    batch = [{'text': "I'm Sam, I teach 8th grade science", 'to': 'Mira', 'names': [], 'known': []}]
    item = {'message': index, 'layer': 'user_fact', 'subject': 'Name', 'value': 'Sam'}
    assert suggest.candidate(item, batch) is None
    assert self_suggest.fact({'message': index, 'category': 'pet', 'subject': 'dog', 'value': 'Sam'},
                             [{'text': 'my dog is called Sam'}]) is None


# --- Each JSON prompt's own example is one the app can read -----------------------------------------------------

EXAMPLE = re.compile(r'^"(?P<said>.*?)"(?: with "(?P<key>\w+)": (?P<given>\[.*?\]|".*?"))?'
                     r'(?: answering "(?P<answering>.*)")? gives (?P<reply>\[.*\])$', re.MULTILINE)


def examples(text: str) -> list[re.Match]:
    found = list(EXAMPLE.finditer(text))
    assert len(found) == text.count(' gives '), 'an example the test cannot read'
    return found


def test_memory_suggestion_examples_are_kept_by_the_app():
    for example in examples(default('memory-suggestions')):
        to = example['given'].strip('"') if example['key'] == 'to' else ''
        batch = [{'text': example['said'], 'to': to, 'names': [], 'known': []}]
        for item in suggest.parse(example['reply']):
            item.pop('corrects', None)  # Named against the message's "known" rows, which need a database.
            assert suggest.candidate(item, batch) is not None, f"{example['said']!r} -> {item}"


def test_self_fact_examples_are_kept_by_the_app():
    for example in examples(default('self-facts', name='Rae')):
        batch = [{'text': example['said'], 'answering': example['answering'] or ''}]
        for item in self_suggest.parse(example['reply']):
            assert self_suggest.fact(item, batch) is not None, f"{example['said']!r} -> {item}"


def test_life_phrasing_example_has_the_fields_the_app_reads():
    shape = json.loads(re.search(r'\{"summary".*?\}', default('life-phrasing', name='Rae'))[0])
    assert set(shape) == set(synthesis.LIMITS)


@pytest.mark.parametrize('name', ['character-draft.md', 'character-split.md'])
def test_character_draft_examples_parse(name):
    text = prompt_library.PROMPTS[name].default()
    shape = drafting.parse_object(text[text.index('\n{\n'):text.index('\n}\n') + 2])
    assert {'name', 'identity', 'schedule'} <= set(shape)
    for block in shape['schedule']:
        assert all(type(day) is int and 0 <= day <= 6 for day in block['days'])


def test_sidecar_example_changes_are_kinds_the_app_takes():
    text = prompt_library.PROMPTS['sidecar.md'].default()
    kinds = set()
    for line in re.findall(r'^- (\{"kind".*\})$', text, re.MULTILINE):
        kinds.add(re.search(r'"kind": "(\w+)"', line)[1])
        if '"value": the' not in line:  # The field example's value is a placeholder for any shape.
            json.loads(line)
    assert kinds == {'field', 'reply', 'memory', 'new_memory', 'forget_memory', 'authors_note'}
    proposals = sidecar.Proposals.__new__(sidecar.Proposals)
    with pytest.raises(drafting.Unusable, match='use one of field, reply, memory, new_memory, forget_memory, '
                       'authors_note'):
        proposals.change({'kind': 'nothing'}, False)


def test_polish_example_reply_changes_the_item_it_names():
    text = polish.PROMPT.format(about='', what_line='', what='places', name='Port', kind='town', when='now', items='')
    reply = drafting.parse_object(text[text.rindex('{"items"'):])
    definition = {'places': [{'id': '...', 'name': 'Old', 'summary': 'Old.'}]}
    polished, changed = polish.apply(definition, 'places', reply)
    assert changed == ['...']
