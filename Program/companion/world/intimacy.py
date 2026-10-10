"""The adult side of life (Settings > Realism > Adult side of life, off by default): who someone is drawn to,
how adventurous they are, their drive and a few things they're into, rolled from their seed like the rest of
their sheet. Only ever for adults, and the bank (world/data/intimacy.json) only holds things between
consenting adults.

- Townsfolk: nothing is stored. Their orientation is Matchlight's own roll (world/dating.py), so their
  dating card and their adult side always agree. Companions who meet them learn their orientation once they
  know their heart (companion/life/encounters.py); the rest stays theirs.
- Companions: the same roll by companion id (or by their townsperson's seed when they came from town), with
  anything the user set on the form (`definition['intimacy']`) winning field by field. A romance companion
  has no rolled orientation: they are drawn to the user.
- It only ever goes in the person's own chat prompt (companion/memory/context.py), as private lines. Never
  in picture prompts, the town paper, the feed, notifications or what other people see.

Nobody under 18 ever gets it: every roll checks the age itself, and a companion whose sheet reads as younger
than 18 gets nothing. No model is involved.
"""
import json
import re
from functools import cache

from companion.database import optional, settings
from companion.world import catalog, dating, generators, newcomers, townsfolk

ADULT_AT = 18
# How many interests each level draws, and the boldest tier it reaches.
DRAWS = {'reserved': (0, 0), 'conventional': (1, 1), 'curious': (2, 2), 'adventurous': (2, 3), 'wild': (3, 3)}
DRIVES = {'low': 1, 'average': 2, 'high': 1}
# A companion whose own words say they're under 18 never gets an adult side (fail closed). Background is left
# out: "as a teen" there is a memory, not their age now.
MINOR = re.compile(r"\b(?:(?:1[0-7]|[1-9])[- ](?:years?[- ]old|y/?o)\b|aged? (?:1[0-7]|[1-9])\b|teen(?:age[dr]?|s)?\b|"
                   r"minor\b|under-?age|high[- ]school(?:er|\s+student)|middle[- ]school|school ?(?:girl|boy)\b)",
                   re.IGNORECASE)
AGE = re.compile(r"\b(\d{1,3})(?:[- ]years?[- ]old|\s*(?:yo|y/o)\b)|\bage[d]?[:\s]+(\d{1,3})\b", re.IGNORECASE)
PRIVATE = ('Your intimate side (private; you are an adult and so is anyone this involves; never recite it or bring '
           'it up out of nowhere; it only shapes you when romance or intimacy comes up and the moment fits):')
WHO = {'she': 'woman', 'he': 'man', 'they': 'nonbinary'}


@cache
def bank() -> dict:
    data = json.loads((catalog.DATA / 'intimacy.json').read_text(encoding='utf-8'))
    for kind in ('levels', 'drives', 'interests'):
        data[f'{kind}_by_id'] = {entry['id']: entry for entry in data[kind]}
    return data


def adult(age) -> bool:
    return isinstance(age, int) and not isinstance(age, bool) and age >= ADULT_AT


def roll(seed: str, age: int, who: str) -> dict | None:
    """An adult's rolled adult side; None for anyone under 18."""
    if not adult(age):
        return None
    levels = [level['id'] for level in bank()['levels']]
    # Two draws averaged lean towards the middle: most people are conventional or curious, few are at the ends.
    middle = (generators.unit(seed, 'intimacy-a') + generators.unit(seed, 'intimacy-b')) / 2
    level = levels[min(len(levels) - 1, int(middle * len(levels)))]
    count, boldest = DRAWS[level]
    if level == 'conventional' and generators.unit(seed, 'intimacy-count') < 0.5:
        count = 0
    options = sorted(entry['id'] for entry in bank()['interests'] if entry['tier'] <= boldest)
    interests = sorted(options, key=lambda entry: generators.unit(seed, 'intimacy-into', entry))[:count]
    return {'orientation': dating.orientation(seed, age, who)[0], 'level': level,
            'drive': dating.weighted(seed, 'intimacy-drive', DRIVES), 'interests': sorted(interests), 'note': ''}


def for_sheet(sheet: dict) -> dict | None:
    """A townsperson's adult side, from the seed and age on their sheet."""
    return roll(sheet['seed'], sheet.get('age'), dating.gender(sheet))


# Companions -----------------------------------------------------------------------------------------------

def reads_as_minor(definition: dict) -> bool:
    text = ' '.join(str(definition.get(key) or '') for key in ('name', 'identity', 'appearance', 'personality'))
    return bool(MINOR.search(text)) or any(age < ADULT_AT for age in stated_ages(definition))


def stated_ages(definition: dict) -> list[int]:
    return [int(found[0] or found[1]) for found in AGE.findall(str(definition.get('identity') or ''))]


def who(definition: dict) -> str:
    """She, he or they as their appearance and identity speak of them, as a dating gender."""
    words = re.findall(r'[a-z]+', f"{definition.get('appearance', '')} {definition.get('identity', '')}".lower())
    counts = {'she': sum(word in ('she', 'her', 'hers', 'woman') for word in words),
              'he': sum(word in ('he', 'him', 'his', 'man') for word in words)}
    best = max(counts, key=counts.get)
    return WHO[best if counts[best] and counts['she'] != counts['he'] else 'they']


def rolled_for_companion(connection, companion_id: str, townsfolk_key: str | None, definition: dict) -> dict | None:
    """What the seed gives a companion before anything the user set; None when their sheet reads as under 18."""
    if reads_as_minor(definition):
        return None
    if townsfolk_key and connection is not None:
        sheet = townsfolk.find(newcomers.city_for(connection, definition), townsfolk_key)
        if sheet:
            return for_sheet(sheet)
    ages = [age for age in stated_ages(definition) if age >= ADULT_AT]
    found = roll(companion_id, ages[0] if ages else 30, who(definition))
    if found and definition.get('relationship') == 'romance':
        found['orientation'] = ''
    return found


def merged(rolled: dict | None, chosen: dict | None) -> dict | None:
    """The rolled side with what the user set on the form winning field by field."""
    if rolled is None:
        return None
    chosen, found = chosen or {}, dict(rolled)
    for key in ('orientation', 'level', 'drive', 'note'):
        if chosen.get(key):
            found[key] = chosen[key]
    if chosen.get('interests'):
        found['interests'] = [entry for entry in chosen['interests'] if entry in bank()['interests_by_id']]
    return found


def turned_on(connection) -> bool:
    return bool((settings(connection) or {}).get('adult_side'))


def for_companion(connection, companion_id: str, definition: dict) -> dict | None:
    row = optional(connection, 'SELECT townsfolk_key FROM companions WHERE id=?', (companion_id,)) \
        if connection is not None else None
    rolled = rolled_for_companion(connection, companion_id, (row or {}).get('townsfolk_key'), definition)
    return merged(rolled, definition.get('intimacy'))


def own_text(found: dict | None) -> str:
    """The lines for their own prompt."""
    if not found:
        return ''
    levels, drives, interests = bank()['levels_by_id'], bank()['drives_by_id'], bank()['interests_by_id']
    lines = [PRIVATE]
    if found.get('orientation'):
        lines.append(f"- Orientation: {found['orientation']}.")
    if found.get('level') in levels:
        lines.append(f"- How adventurous: {levels[found['level']]['label'].lower()}; "
                     f"{levels[found['level']]['text']}.")
    if found.get('drive') in drives:
        lines.append(f"- You have {drives[found['drive']]['text']}.")
    into = [interests[entry]['text'] for entry in found.get('interests') or [] if entry in interests]
    if into:
        lines.append('- Into: ' + '; '.join(into) + '.')
    if found.get('note'):
        lines.append(f"- {found['note'].strip()}")
    return '\n'.join(lines)


def prompt_text(connection, version: dict) -> str:
    """Their own private lines when the switch is on, else ''."""
    if connection is None or not version.get('companion_id') or not turned_on(connection):
        return ''
    return own_text(for_companion(connection, version['companion_id'], version['definition']))


def view(found: dict | None) -> dict | None:
    """Labels for the interface."""
    if not found:
        return None
    levels, drives, interests = bank()['levels_by_id'], bank()['drives_by_id'], bank()['interests_by_id']
    return {**found, 'level_label': levels.get(found.get('level'), {}).get('label', ''),
            'drive_label': drives.get(found.get('drive'), {}).get('label', ''),
            'interest_labels': [interests[entry]['label'] for entry in found.get('interests') or []
                                if entry in interests]}


def options() -> dict:
    """What the character form offers."""
    return {'orientations': bank()['orientations'],
            'levels': [{'id': entry['id'], 'label': entry['label'], 'text': entry['text']} for entry in bank()['levels']],
            'drives': [{'id': entry['id'], 'label': entry['label']} for entry in bank()['drives']],
            'interests': [{'id': entry['id'], 'label': entry['label'], 'tier': entry['tier']}
                          for entry in bank()['interests']]}
