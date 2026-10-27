"""A companion's own family, made before the rest of their circle (Vanta, 2026-10-27).

Seeded once per timeline from the city's era (world/data/family_shapes.json, or the city's own `family` rates), the
companion's age and what their sheet says: their parents' story (together, split, a parent married again, single
from the start, adopted, raised by two moms or two dads, or a parent who later married someone of the same sex), how
many brothers and sisters they have (full, half or step), who has died before now and who they no longer talk to.

The plan is words and numbers only; companion/life/circle.py makes the people. Living family they are in touch with
join the circle first; family who died before the story starts are listed as Remembered, with no funeral; family
they no longer talk to are kept out of their days (removed, marked `estranged`). Anything the sheet says wins: an
only child, an orphan, two dads, a late mother, parents who divorced, and the parents and siblings it names.
Settings > Realism > Family shapes (`family_shapes`): 0 simple (parents together, everyone alive), 1 gentle, 2 true
to life, 3 more drama. Only circles made from now on get one; families already met stay as they are.
"""
import json
import re
from functools import cache

from companion.world import catalog, generators

ACTIVE = True
ADULT = 18
# Brothers and sisters who join the circle; any more are mentioned in words.
MOST_SIBLINGS = 5
STEP_KIDS = 0.4  # A stepparent brings a grown child of their own.
HALF = 0.5  # A sibling born after a parent remarried is a half sibling.
NEW_FAMILY = 0.5  # A parent who remarried has a child with their new partner.
BOTH_REMARRIED = 0.35
# How each Family shapes level moves the rates: splits and singles, deaths, estrangement.
LEVELS = {0: (0.0, 0.0, 0.0), 1: (0.5, 0.5, 0.5), 2: (1.0, 1.0, 1.0), 3: (1.5, 1.5, 2.0)}
DEFAULT_LEVEL = 2
STORIES = ('together', 'split', 'single', 'adopted', 'same_sex')
CUES = {
    'only_child': r'\bonly child\b',
    'orphan': r'\borphan(?:ed|s)?\b|\b(?:both )?(?:her|his|their|my) parents (?:both )?(?:died|passed away|are dead)\b',
    'split': r'\bparents (?:are |got |were )?(?:divorced|separated|split(?: up)?)\b|\bchild of divorce\b',
    'adopted': r'\badopted\b',
    'two_moms': r'\btwo (?:moms|mums|mothers)\b',
    'two_dads': r'\btwo (?:dads|fathers)\b',
    'single': r'\b(?:raised|brought up) by (?:a |her |his |their )?single (?:mom|mum|mother|dad|father|parent)\b|'
              r'\bsingle[- ](?:mom|mum|mother|dad|father|parent) raised\b',
    'mom_died': r'\b(?:late|dead|deceased) (?:mom|mum|mother)\b|\b(?:mom|mum|mother) (?:died|passed away)\b',
    'dad_died': r'\b(?:late|dead|deceased) (?:dad|father)\b|\b(?:dad|father) (?:died|passed away)\b',
}


@cache
def shapes() -> dict:
    return json.loads((catalog.DATA / 'family_shapes.json').read_text(encoding='utf-8'))


def rates(data: dict | None) -> dict:
    """The era's rates, with the city's own `family` rates over them."""
    era = shapes()['eras'].get((data or {}).get('era') or 'modern', 'today')
    found = shapes()['rates'][era]
    return found | {key: value for key, value in ((data or {}).get('family') or {}).items()
                    if key in found and value is not None}


def cues(definition: dict) -> set[str]:
    """What the sheet's own words say about their family."""
    from companion.life import named
    text = named.text_of(definition)
    return {key for key, pattern in CUES.items() if re.search(pattern, text, re.IGNORECASE)}


def death_factor(age: int) -> float:
    return next(factor for until, factor in shapes()['parent_death_by_age'] if age <= until)


def plan(definition: dict, data: dict | None, seed: str, age: int | None, level: int = DEFAULT_LEVEL,
         named_parents: tuple[str, ...] = (), named_siblings: int = 0) -> dict:
    """The family, the same every time for the same seed. `age` is the companion's in human terms (30 when not
    known); `named_parents` the pronouns of the parents the sheet names, `named_siblings` how many siblings it names."""
    age = age or 30
    found, said = rates(data), cues(definition)
    splits, deaths, rifts = LEVELS.get(level, LEVELS[DEFAULT_LEVEL])
    tree = {'age': age, 'people': [], 'minors': 0, 'more': 0, 'absent': None, 'adopted': False, 'split_at': None}
    story(tree, seed, found, said, splits, named_parents)
    siblings(tree, seed, found, said, named_siblings)
    passed(tree, seed, found, said, deaths)
    estranged(tree, seed, found, rifts)
    return tree


def person(tree: dict, key: str, role: str, pronouns: str, **extra) -> dict:
    made = {'id': key, 'role': role, 'pronouns': pronouns, 'step': False, 'died_at': None, 'estranged': False} | extra
    tree['people'].append(made)
    return made


def pick_story(seed: str, found: dict, said: set[str], splits: float, named: tuple[str, ...]) -> str:
    if said & {'two_moms', 'two_dads'}:
        return 'same_sex'
    for cue, chosen in (('adopted', 'adopted'), ('split', 'split'), ('single', 'single')):
        if cue in said:
            return chosen
    weights = [found['together'], found['split'] * splits, found['single'] * splits, found['adopted'],
               found['same_sex']]
    if len(set(named)) == 2:  # The sheet names a mom and a dad.
        weights[4] = 0.0
    if len(named) >= 2:
        weights[2] = 0.0
    weights[0] += sum(found[key] for key in ('split', 'single')) * (1 - splits)
    return generators.pick(seed, 'family:story', list(STORIES), weights)


def story(tree: dict, seed: str, found: dict, said: set[str], splits: float, named: tuple[str, ...]):
    """The parents: who raised them and how the two of them stand."""
    tree['story'] = chosen = pick_story(seed, found, said, splits, named)
    if chosen == 'same_sex':
        word = 'she/her' if 'two_moms' in said else 'he/him' if 'two_dads' in said else \
            named[0] if named else generators.pick(seed, 'family:pair', ['she/her', 'he/him'])
        person(tree, 'p1', 'parent', word, partner='p2', how='married')
        person(tree, 'p2', 'parent', word, partner='p1', how='married')
        tree['adopted'] = generators.unit(seed, 'family:adopted') < 0.6 or 'adopted' in said
        return
    first = named[0] if named else 'she/her'
    other = 'he/him' if first == 'she/her' else 'she/her'
    if chosen == 'single':
        alone = first if named else generators.pick(seed, 'family:single', ['she/her', 'he/him'], [0.8, 0.2])
        person(tree, 'p1', 'parent', alone)
        tree['absent'] = 'he/him' if alone == 'she/her' else 'she/her'
        return
    how = 'divorced' if chosen == 'split' else 'married'
    person(tree, 'p1', 'parent', first, partner='p2', how=how)
    person(tree, 'p2', 'parent', named[1] if len(named) > 1 else other, partner='p1', how=how)
    tree['adopted'] = chosen == 'adopted'
    if chosen == 'split':
        split(tree, seed, found)


def split(tree: dict, seed: str, found: dict):
    """How old they were when their parents parted, and who married again (sometimes someone of the same sex)."""
    tree['split_at'] = 2 + int(generators.unit(seed, 'family:split-at') * min(16, tree['age'] - 2))
    if generators.unit(seed, 'family:remarried') >= found['remarried']:
        return
    married = ['p1', 'p2'] if generators.unit(seed, 'family:both') < BOTH_REMARRIED else \
        [generators.pick(seed, 'family:who', ['p1', 'p2'])]
    same = found['same_sex_step'] / max(found['split'] * found['remarried'], 0.01)
    for index, key in enumerate(married):
        parent = next(item for item in tree['people'] if item['id'] == key)
        alike = generators.unit(seed, 'family:same-step', key) < same
        words = parent['pronouns'] if alike else 'he/him' if parent['pronouns'] == 'she/her' else 'she/her'
        step = person(tree, f'p{3 + index}', 'parent', words, step=True, partner=key, how='married')
        step['remarried_at'] = min(tree['age'], tree['split_at'] + 1 + int(generators.unit(seed, 'family:wed', key) * 6))
        parent['remarried'] = step['id']


def sibling_count(seed: str, found: dict, said: set[str], named: int) -> int:
    if 'only_child' in said:
        return 0
    count = generators.pick(seed, 'family:siblings', [0, 1, 2, 3], found['siblings'])
    while count >= 3 and count < 10 and generators.unit(seed, 'family:more', count) < found['more_siblings']:
        count += 1
    return max(count, named)


def siblings(tree: dict, seed: str, found: dict, said: set[str], named: int):
    """Brothers and sisters: their ages around the companion's, half siblings born after a remarriage, a
    stepparent's own grown child. Anyone under 18 is only counted (children are words only)."""
    remarried = [item for item in tree['people'] if item['step']]
    for index in range(sibling_count(seed, found, said, named)):
        key = f'sibling:{index}'
        offset = round((generators.unit(seed, key, 'a') + generators.unit(seed, key, 'b') - 1) * 10)
        extra = {'kind': 'full', 'offset': offset}
        if remarried and offset < -(tree['split_at'] + 1) and generators.unit(seed, key, 'half') < HALF:
            extra |= {'kind': 'half', 'via': remarried[0]['partner'], 'with': remarried[0]['id']}
        add_sibling(tree, seed, key, extra, named > index)
    for step in remarried:
        if generators.unit(seed, 'family:new-kid', step['id']) < NEW_FAMILY:  # A baby with the new partner.
            offset = -(step['remarried_at'] + 1 + int(generators.unit(seed, step['id'], 'born') * 8))
            add_sibling(tree, seed, f"half:{step['id']}", {'kind': 'half', 'offset': offset, 'via': step['partner'],
                                                           'with': step['id']}, False)
        if generators.unit(seed, 'family:step-kid', step['id']) < STEP_KIDS:
            offset = round((generators.unit(seed, step['id'], 'kid') * 2 - 1) * 8)
            add_sibling(tree, seed, f"step:{step['id']}", {'kind': 'step', 'offset': offset, 'via': step['id']}, False)


def add_sibling(tree: dict, seed: str, key: str, extra: dict, named: bool):
    if tree['age'] + extra['offset'] < ADULT and not named:
        tree['minors'] += 1
        return
    if sum(item['role'] == 'sibling' for item in tree['people']) >= MOST_SIBLINGS and not named:
        tree['more'] += 1
        return
    pronouns = generators.pick(seed, f'{key}:pronouns', ['she/her', 'he/him'])
    person(tree, f"s{sum(item['role'] == 'sibling' for item in tree['people']) + 1}", 'sibling', pronouns, **extra)


def passed(tree: dict, seed: str, found: dict, said: set[str], deaths: float):
    """Who died before now, and at what age of the companion's. The sheet's late mother or orphan always is."""
    factor = death_factor(tree['age'])
    for parent in [item for item in tree['people'] if item['role'] == 'parent' and not item['step']]:
        rate = found['mother_died'] if parent['pronouns'] == 'she/her' else found['father_died']
        forced = 'orphan' in said or (parent['pronouns'] == 'she/her' and 'mom_died' in said) or \
            (parent['pronouns'] == 'he/him' and 'dad_died' in said)
        if forced or generators.unit(seed, 'family:died', parent['id']) < min(0.92, rate * factor * deaths):
            # Later in life is likelier: the square root leans the age towards now.
            parent['died_at'] = max(1, round(tree['age'] * generators.unit(seed, 'family:when', parent['id']) ** 0.5))
    kin = [item for item in tree['people'] if item['role'] == 'sibling']
    if kin and generators.unit(seed, 'family:sibling-died') < found['sibling_died'] * deaths:
        gone = generators.pick(seed, 'family:which-sibling', kin)
        gone['died_at'] = max(1, round(tree['age'] * generators.unit(seed, 'family:sibling-when')))


def estranged(tree: dict, seed: str, found: dict, rifts: float):
    """Someone living they no longer talk to: a parent, or a brother or sister."""
    for role, rate in (('parent', found['estranged_parent']), ('sibling', found['estranged_sibling'])):
        living = [item for item in tree['people'] if item['role'] == role and item['died_at'] is None]
        if living and generators.unit(seed, 'family:rift', role) < rate * rifts:
            generators.pick(seed, f'family:rift-who:{role}', living)['estranged'] = True


# Saving and the chat line -----------------------------------------------------------------------------------------

def level(connection) -> int:
    from companion.database import optional
    row = optional(connection, 'SELECT family_shapes FROM life_settings WHERE id=1')
    return DEFAULT_LEVEL if row is None else int(row['family_shapes'])


def start(connection, companion: dict, data: dict | None, now) -> dict | None:
    """The family plan for a circle made now, kept with the timeline; None where the world doesn't know their city
    (or in tests that keep the older circles: ACTIVE)."""
    if not ACTIVE or not data:
        return None
    from companion.clock import stamp, zone
    from companion.database import encode
    from companion.life import ages, family_circle
    definition = companion['version']['definition']
    today = now.astimezone(zone(companion['version']['timezone'])).date()
    life = ages.companion_life_age(connection, companion['id'], definition, today)
    tree = family_circle.plan_for(definition, data, companion['active_timeline_id'], life, level(connection), today)
    connection.execute('INSERT OR REPLACE INTO family_trees (timeline_id, tree, created_at) VALUES (?, ?, ?)',
                       (companion['active_timeline_id'], encode(tree), stamp(now)))
    return tree


def stored(connection, timeline_id: str) -> dict | None:
    from companion.database import decode, optional
    row = optional(connection, 'SELECT tree FROM family_trees WHERE timeline_id=?', (timeline_id,))
    return decode(row['tree']) if row else None


def context_lines(connection, companion: dict) -> list[tuple[str, str]]:
    """The family line for the 'circle' section (companion/life/family_words.py); none for a circle with no plan."""
    from companion.life import family_words
    timeline_id = companion['active_timeline_id']
    if not (tree := stored(connection, timeline_id)):
        return []
    text = family_words.line(tree, family_words.rows_by_plan(connection, timeline_id),
                             companion['version']['definition'])
    return [(f'family:{timeline_id}', text)] if text else []


def copy(connection, parent_id: str, new_id: str):
    """A timeline branched from another (companion/timelines.py) keeps the family it was planned with."""
    connection.execute('INSERT OR IGNORE INTO family_trees (timeline_id, tree, created_at) SELECT ?, tree, created_at '
                       'FROM family_trees WHERE timeline_id=?', (new_id, parent_id))
