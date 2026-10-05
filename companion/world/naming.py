"""Given names grounded in what babies were actually called in the year a person was born.

The data (given_names.json, written by scripts/world/given_names.py) holds each culture's most popular
given names per birth year or cohort and its common family names. A name group in names.json links to
cultures with weights, so a 58-year-old in Baltimore is more likely a Lisa or a Kevin and a 24-year-old a
Brianna or a Tyler. The same data lists names that read as invented by a language model (Elara, Voss, Vex);
nothing here produces them, and any name a model writes is checked against them.
"""
import json
import re
from functools import cache

from companion.world import catalog
from companion.world.schema import GivenNames

# Where no city is known, names come from the modern bank as an American city would mix them.
DEFAULT_CITY = {'id': '', 'era': 'modern', 'country': 'United States', 'names': None}
# Eras whose people were born in years the lists cover (later years use the latest cohort).
COHORT_ERAS = ('modern', 'future', 'other')
# How far either side of the target birth year a name may come from, so peers don't all share one year's list.
SPREAD = 3
WORD = re.compile(r"[A-Z][A-Za-z'’-]+")


@cache
def data() -> dict:
    text = (catalog.DATA / 'given_names.json').read_text(encoding='utf-8')
    return GivenNames.model_validate_json(text).model_dump()


def present_year() -> int:
    return data()['present_year']


def culture(key: str) -> dict:
    return data()['cultures'][key]


def local_culture(country: str | None) -> str:
    """The culture whose names are local in this country; the United States lists where none fits."""
    return data()['countries'].get((country or '').strip().lower(), 'us')


def links(group: dict, city: dict) -> dict[str, float]:
    """The cultures a name group draws given names from in this city, with weights. Empty outside modern eras."""
    if city.get('era', 'modern') not in COHORT_ERAS:
        return {}
    local, known = local_culture(city.get('country')), data()['cultures']
    weights: dict[str, float] = {}
    for key, weight in (group.get('cultures') or {}).items():
        key = local if key == 'local' else key
        if key in known and weight > 0:
            weights[key] = weights.get(key, 0) + weight
    return weights


def cohort(key: str, year: int) -> dict:
    """The cohort covering a birth year, else the nearest one."""
    cohorts = culture(key)['cohorts']
    return min(cohorts, key=lambda item: (0 if item['start'] <= year <= item['end'] else
                                          min(abs(year - item['start']), abs(year - item['end'])), -item['start']))


def rank_weights(names: list) -> list[float]:
    """Popular names come up more often: the first is about ten times as likely as the hundredth."""
    return [1 / (rank + 10) for rank in range(len(names))]


# --- Invented-sounding names --------------------------------------------------------------------

@cache
def invented() -> frozenset[str]:
    names = data()['invented']
    return frozenset(word.casefold() for word in [*names['given'], *names['family']])


def is_invented(name: str) -> bool:
    """Whether any word of a name reads as invented (Elara, Voss, Vex)."""
    return any(word.casefold() in invented() for word in WORD.findall(name or ''))


def invented_in(text: str, allowed: str = '') -> list[str]:
    """Capitalised words in a model's text that read as invented names, except ones in `allowed` (what the
    user typed and the world data), in order of first use."""
    permitted = {word.casefold() for word in WORD.findall(allowed or '')}
    found = [word for word in WORD.findall(text or '')
             if word.casefold() in invented() and word.casefold() not in permitted]
    return list(dict.fromkeys(found))


def allowed_words(*parts) -> str:
    """Text to pass as `allowed`: anything the user typed or the world data contains (as JSON)."""
    return ' '.join(part if isinstance(part, str) else json.dumps(part, ensure_ascii=False) for part in parts if part)


# --- Family names that change with gender ---------------------------------------------------------

# Polish and Russian family names take a feminine ending for women (Kowalski → Kowalska, Ivanov → Ivanova).
FEMININE_ENDINGS = {'poland': (('dzki', 'dzka'), ('cki', 'cka'), ('ski', 'ska')),
                    'russia': (('skiy', 'skaya'), ('sky', 'skaya'), ('ov', 'ova'), ('ev', 'eva'), ('in', 'ina'))}


def gendered(culture: str | None, family: str, pronouns: str) -> str:
    """The form of a family name a woman of this culture would use."""
    if pronouns != 'she':
        return family
    for ending, feminine in FEMININE_ENDINGS.get(culture or '', ()):
        if family.endswith(ending):
            return family[:-len(ending)] + feminine
    return family


def base_family(culture: str | None, family: str) -> str:
    """The listed (masculine) form of a family name, so a woman's relatives share the same name."""
    for ending, feminine in FEMININE_ENDINGS.get(culture or '', ()):
        if family.endswith(feminine) and family[:-len(feminine)] + ending in culture_surnames(culture):
            return family[:-len(feminine)] + ending
    return family


@cache
def culture_surnames(key: str) -> frozenset[str]:
    return frozenset(culture(key)['surnames'])
