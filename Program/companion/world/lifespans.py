"""Lifespans for elves and other long-lived people (Hit List #76, v0.15): each person has a kind, and each kind an
average lifespan. Nothing here calls a model.

Everyone keeps their real age (the one they say, the one the calendar moves, companion/life/ages.py). Beside it each
person has a life age: how far through life they are in human terms. Childhood runs at human pace for every kind,
and only adulthood is stretched to the kind's lifespan, so an elf (600 years) of 300 has a life age of 48. Every rule
that asks how old someone is for odds, life stages, retiring, health or passing away reads the life age; a human's
life age is their real age, so nothing changes for them.

The kinds are rule data (world/data/lifespans.json). A city file may carry its own `kinds` block, which changes a
built-in kind's lifespan for that city or adds the city's own kind, and a name group ties to a kind with
`"kind": "<key>"` (`clean` checks both when a city loads). Who gets which kind is decided by the app: a companion
or the user from what their own words say about them (`from_words`), a townsperson from their name group (`of_group`),
a circle relative from the companion. The user's own pick on their page wins over both (`lifespan_of`).
"""
import json
import re
from functools import cache

from companion.models import LIFESPANS
from companion.world import catalog

HUMAN = 'human'
AGELESS = 'ageless'
ADULT = 18
HUMAN_LIFESPAN = 80
CITY_YEARS = (40, 5000)  # The whole years a city file may give a kind.
LONG_LIVED = 150  # Past this, milestone birthdays are round 50s and 100s of real years, and an age past 120 can be theirs.
WORD_FIELDS = ('identity', 'appearance')
NEGATED = re.compile(r"\b(?:not|never|isn't|no)\s+(?:\w+\s+)?(?:an?\s+)?$", re.IGNORECASE)


@cache
def table() -> dict:
    return json.loads((catalog.DATA / 'lifespans.json').read_text(encoding='utf-8'))


def kinds(data: dict | None = None) -> dict[str, dict]:
    """Every kind and its lifespan where this city is (built-in ones, with the city file's changes and its own)."""
    found = {key: dict(value) for key, value in table()['kinds'].items()}
    for key, value in ((data or {}).get('kinds') or {}).items():
        found[key] = {**found.get(key, {}), **value}
    return found


def lifespan_of(kind: str | None, data: dict | None = None, own: int | None = None) -> int | None:
    """How long someone lives on average: the user's own pick (0: they don't age), else their kind's where they are.
    None: they don't age."""
    if own == 0:
        return None
    if own:
        return own
    found = kinds(data).get(kind or HUMAN) or kinds(data)[HUMAN]
    return found['lifespan']


def life_age(real: int | None, lifespan: int | None) -> int | None:
    """How far through life someone is in human terms: their real age through childhood, then adulthood stretched
    from their kind's lifespan to a human's. Someone who doesn't age is the age they are."""
    if real is None or lifespan is None or real <= ADULT or lifespan == HUMAN_LIFESPAN:
        return real
    return round(ADULT + (real - ADULT) * (HUMAN_LIFESPAN - ADULT) / (lifespan - ADULT))


def real_age(life: int, lifespan: int | None) -> int:
    """The other way round (`life_age`), for seeding: the real age that is this life age for this lifespan."""
    if lifespan is None or life <= ADULT or lifespan == HUMAN_LIFESPAN:
        return life
    return round(ADULT + (life - ADULT) * (lifespan - ADULT) / (HUMAN_LIFESPAN - ADULT))


def of_group(data: dict | None, group: str | None) -> str:
    """The kind a city's name group ties to, else human."""
    if not data or not group:
        return HUMAN
    groups, _mix = catalog.name_groups(data)
    kind = (groups.get(group) or {}).get('kind')
    return kind if kind and kind in kinds(data) else HUMAN


def from_words(text: str, data: dict | None = None) -> str:
    """The kind someone's own words say they are ("a half-elf ranger", not "not an elf"), else human. The longest
    word wins where two overlap, so "half-elf" is never read as "elf"."""
    words = {word.lower(): key for key, value in kinds(data).items() for word in value.get('words') or ()}
    if not words or not text:
        return HUMAN
    pattern = '|'.join(re.escape(word) for word in sorted(words, key=len, reverse=True))
    for found in re.finditer(rf'\b(?:{pattern})\b', text, re.IGNORECASE):
        if not NEGATED.search(text[:found.start()]):
            return words[found[0].lower()]
    return HUMAN


def sheet_kind(definition: dict, data: dict | None = None) -> str:
    """A companion's kind: the one picked on their Character page, else what their identity and appearance say."""
    own = definition.get('kind')
    if own and own in kinds(data):
        return own
    return from_words(' '.join(str(definition.get(field) or '') for field in WORD_FIELDS), data)


def sheet_lifespan(definition: dict, data: dict | None = None) -> int | None:
    return lifespan_of(sheet_kind(definition, data), data, definition.get('lifespan'))


def persona_kind(persona: dict, data: dict | None = None) -> str:
    """The user's kind: the one picked on the Persona page, else what their own words (About you) say."""
    own = persona.get('kind')
    if own and own in kinds(data):
        return own
    return from_words(persona.get('about') or '', data)


def persona_lifespan(persona: dict, data: dict | None = None) -> int | None:
    return lifespan_of(persona_kind(persona, data), data, persona.get('lifespan'))


def long_lived(lifespan: int | None) -> bool:
    """A kind that lives well past a hundred (or doesn't age), so a three-digit age can be theirs."""
    return lifespan is None or lifespan > LONG_LIVED


def ageless(definition: dict, data: dict | None = None) -> bool:
    """Whether a companion stays the age they are: "Keeps their age", or a kind that doesn't age."""
    return bool(definition.get('keeps_age')) or sheet_lifespan(definition, data) is None


def blend(one: str | None, other: str | None, data: dict | None = None) -> str:
    """The kind of a child of two kinds: a listed pair's (elf and human: half-elf), else the longer-lived parent's."""
    one, other = one or HUMAN, other or HUMAN
    if one == other:
        return one
    for item in table()['blends']:
        if sorted(item['parents']) == sorted((one, other)):
            return item['child']
    spans = {kind: lifespan_of(kind, data) for kind in (one, other)}
    return max((one, other), key=lambda kind: (spans[kind] is None, spans[kind] or 0, kind))


# Pickers and milestones ------------------------------------------------------------------------------------------

SPANS = LIFESPANS  # "How long they live": never free text, so these and "As their kind" (companion/models.py).


def choices(data: dict | None = None) -> dict:
    """What the Kind and How long they live pickers offer where someone lives."""
    return {'kinds': [{'id': key, 'label': value['label'], 'lifespan': value['lifespan']}
                      for key, value in kinds(data).items() if value.get('label')],
            'spans': list(SPANS)}


def described(kind: str, own: int | None, real: int | None, data: dict | None = None) -> dict:
    """A person's kind for their page: {kind, label, own (their own How long they live, None as their kind, 0 doesn't
    age), years (what applies, None doesn't age), kind_years (their kind's), life_age (None for a human)}."""
    found = kinds(data).get(kind) or kinds(data)[HUMAN]
    years = lifespan_of(kind, data, own)
    return {'kind': kind if kind in kinds(data) else HUMAN, 'label': found['label'], 'own': own, 'years': years,
            'kind_years': found['lifespan'],
            'life_age': None if years == HUMAN_LIFESPAN else life_age(real, years)}


def milestone(age: int | None, lifespan: int | None = HUMAN_LIFESPAN) -> bool:
    """A birthday that is a bigger occasion: 30, 40, 50 ... for most, and 100, 150, 200 ... for a kind that lives
    longer than LONG_LIVED years (an elf's 40th is nothing much)."""
    if not age or age < 30:
        return False
    if lifespan is None or lifespan > LONG_LIVED:
        return age >= 100 and age % 50 == 0
    return age % 10 == 0


# A city file's kinds ---------------------------------------------------------------------------------------------

def clean(data: dict) -> list[str]:
    """Check a city's `kinds` block and its name groups' kinds in place: a bad entry is dropped, with a note saying
    why, and the city still loads. Childhood and the age of 18 are not the city's to change: only how long adulthood
    lasts."""
    block = data.get('kinds') or {}
    if not isinstance(block, dict):
        notes, own = ['Dropped the kinds block: it needs to name each kind with its lifespan.'], {}
    else:
        notes, own = clean_kinds(block)
    if own:
        data['kinds'] = own
    else:
        data.pop('kinds', None)
    known = set(table()['kinds']) | set(own)
    for key, group in ((data.get('names') or {}).get('groups') or {}).items():
        if group.get('kind') and group['kind'] not in known:
            notes.append(f'The name group "{key}" names the kind "{group["kind"]}", which isn\'t known, so its people '
                         'are human.')
        if not group.get('kind') or group['kind'] not in known:
            group.pop('kind', None)  # Humans, as before kinds: a city without them keeps its data_version.
    for notable in data.get('notables') or ():
        if notable.get('kind') and notable['kind'] not in known:
            notes.append(f'{notable["name"]} names the kind "{notable["kind"]}", which isn\'t known, so they are '
                         'human.')
            notable.pop('kind')
    return notes


def clean_kinds(block: dict) -> tuple[list[str], dict]:
    """(notes, the kinds kept) for a city's `kinds` block."""
    notes, own = [], {}
    builtin = table()['kinds']
    for key, value in block.items():
        if not isinstance(value, dict) or not re.fullmatch(r'[a-z0-9][a-z0-9-]*', str(key)):
            notes.append(f'Dropped the kind "{key}": it needs a lowercase key and a lifespan.')
            continue
        span = value.get('lifespan', 'missing')
        if span is not None and (isinstance(span, bool) or not isinstance(span, int)
                                 or not CITY_YEARS[0] <= span <= CITY_YEARS[1]):
            notes.append(f'Dropped the kind "{key}": its lifespan must be a whole number of years from '
                         f'{CITY_YEARS[0]} to {CITY_YEARS[1]}, or null for a kind that doesn\'t age.')
            continue
        if key in (HUMAN, AGELESS):
            notes.append(f'Dropped the kind "{key}": ' + ('humans live 80 years everywhere, the measure for every '
                                                         'other kind.' if key == HUMAN else "it doesn't age anywhere."))
            continue
        if key in builtin:
            own[key] = {'lifespan': span}  # A built-in kind: only its lifespan changes here.
            continue
        label, words = value.get('label'), value.get('words')
        if not isinstance(label, str) or not label.strip() or not isinstance(words, list) or not words or \
                not all(isinstance(word, str) and word.strip() for word in words):
            notes.append(f'Dropped the kind "{key}": a kind of the city\'s own needs a label and some words.')
            continue
        own[key] = {'label': label.strip()[:40], 'lifespan': span, 'words': [word.strip()[:40] for word in words]}
    return notes, own
