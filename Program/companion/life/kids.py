"""Companions who already have kids (Hit List #73, v0.15 Room to Grow): a single dad of two, a mom whose son Leo is
seven, a townsperson who had a baby with their partner. Children they had before the user came along.

The app decides, the user overrides ("the world exists outside of User", Vanta 2026-10-08):

- Their kids are read from their description (`described`): the ones it names ("her son Leo, 7", "Mia (4)") with
  their names and ages, and the ones it only counts ("single dad of two", "has three kids"), named and aged by seed.
  A son or daughter it calls grown, or 18 or over, stays an adult in their circle as before. A companion made from a
  townsperson who had a baby with their partner keeps that child (companion/world/couples.py `babies`). A new
  companion whose description says nothing either way may have kids anyway, at a low rate by age (the engine's
  kids:has, odds under Hidden values); never one whose description says they have none or never wanted any, never
  with Growing families at None (Vanta 2026-10-19), and never a companion who was already in the user's life before
  this came in (`settle`, `fresh`).
- Each child is a `circle_children` row with the companion as `parent_id` (so nothing that lists the circle's
  children under a circle person counts them as a niece or a friend's baby), `MARK` and the timeline as its storyline,
  aging with companion/life/ages.py. Words only, like every child in the circle (companion/life/families.py).
- Their other parent is someone in their circle: the ex the description names, the partner it names, the
  townsperson's partner, else a seeded co-parent; nobody when the description says they were widowed. Where the
  kids live (`PATTERNS`) is read from the description ("every other weekend", "shared custody", "single mom") or
  picked by the engine (kids:custody): with the companion and every other weekend at the other parent's, a week at
  each, or with the other parent and every other weekend with the companion. The weeks alternate the way a rota
  does (companion/life/shifts.py `monday_of`), from the week it was decided.
- Dating a parent: the kids are part of their life in the chat from the start ('kids' section), the user meets them
  with their people (companion/life/their_people.py, the "meeting their people" step), and once the two of them
  live together (companion/life/moving_in.py) the user is their step-parent.
- A circle parent the companion dates goes the same way (the v0.14 E2E note): a love-life partner past their
  twenties may come with kids of their own (`partner_kids`, companion/life/love_life.py; not with Growing families at
  None), listed under the partner,
  and once the companion lives with them the companion is the kids' step-parent.

The Character page's Family panel lists them, with where they live and the other parent; the user can change where
they live or take a child out of their life, add a child of theirs by hand the way a pet is added (`add`; whatever they
leave out the app picks), change a child's name, age or whether they're a son or daughter (`edit`), and change who
their other parent is (`set_other`): someone in their circle, someone new they name, or nobody (tester feedback,
2026-10-25). Children keep v0.14's limits: words only, and with the adult side of
life on nothing about them goes in a chat prompt (families.withheld). No model decides anything.
"""
import re
from datetime import date, timedelta

from companion import consequences
from companion.clock import stamp
from companion.database import decode, encode, identifier, many, one, optional
from companion.errors import require
from companion.life import ages, circle, families, named, shifts, steps
from companion.world import lifespans

ACTIVE = True
MOST = 4
GROWN = 18
MARK = 'kids:'  # circle_children.storyline_id of a companion's own child: MARK + timeline id.
PARTNER_MARK = 'kids:partner:'  # A love-life partner's child.
PATTERNS = ('together', 'with_them', 'shared', 'weekends', 'sole')
CUSTODY = ('with_them', 'shared', 'weekends')  # The kids:custody options, in order.
HOWS = ('description', 'town', 'seeded', 'none')
PATTERN_LABELS = {'together': 'With {name} and {other}', 'with_them': 'Mostly with {name}', 'shared': 'Half and half',
                  'weekends': 'Mostly with {other}', 'sole': 'With {name}'}
# The same, spelled out, for the hint under the pick.
PATTERN_DETAILS = {'together': 'with {name} and {other}', 'with_them': "with {name}, every other weekend at {other}'s",
                   'shared': "a week with {name}, a week at {other}'s",
                   'weekends': "with {other}, every other weekend with {name}", 'sole': 'with {name}'}
# A new companion past this age may have kids already (kids:has); how many: one below the first, two below the second.
SEED_FROM = 27
COUNTS = (0.62, 0.93)
# A love-life partner's chance of coming with kids, from this age on: (age, chance).
PARTNER_ODDS = ((35, 0.2), (27, 0.12))
# How old someone is at the earliest when their first child is born.
PARENT_FROM = 19
# Days at the least between the birthdays of a brother and sister who aren't twins.
SPACING = 300
# Children the user adds by hand (`add`): at most this many at once, and none who would make the companion a parent
# before this age.
BY_HAND_MOST = 8
PARENT_YOUNGEST = 16
# Who can be the kids' other parent (`others`): someone they had them with or are with now.
PARTNER_WORDS = ('partner', 'wife', 'husband', 'spouse', 'girlfriend', 'boyfriend', 'fiancée', 'fiancé')
OTHER_ROLES = ('co-parent', 'ex', 'ex-wife', 'ex-husband', 'ex-partner', *PARTNER_WORDS)

_KIDS = (r'(?:kids?|children|child|step-?(?:sons?|daughters?|kids?|children|child)|sons?|daughters?|boys?|girls?|'
         r'toddlers?|newborns?|teenagers?|teens?)')
COUNT_WORDS = {'a': 1, 'an': 1, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5}
_COUNT = '|'.join(COUNT_WORDS)
_PARENT = r'(?:step-?)?(?:mom|mum|mother|dad|father|parent)'
# The word before them that tells their age: "two teenage daughters", "a six-year-old son".
_YOUNG = (r'(?:young|little|small|school-age|teenage|teen|toddler|baby|newborn|'
          rf"(?:{named._AGE[1:-1]})[ -]years?[ -]old)")
_MOD = rf'(?:({_YOUNG}) )?'
# "single dad of two", "mother of three boys", "has two teenage daughters", "her three children", "raising a daughter",
# "her twins", "twin boys", "a stepson", and a count opening a clause ("Married, two teenage daughters.").
COUNTED = (re.compile(rf"\b{_PARENT} (?:of|to) ({_COUNT})\b(?! (?:grown|adult))(?: {_MOD}({_KIDS})\b)?", re.IGNORECASE),
           re.compile(rf"\b(?:has|have|raising|raises) ({_COUNT}) {_MOD}({_KIDS})\b", re.IGNORECASE),
           re.compile(rf"\b(?:her|his|their|my) ({_COUNT}) {_MOD}({_KIDS})\b", re.IGNORECASE),
           re.compile(rf"(?:^|[.;:,(]\s*|\band )((?-i:[Tt]wo|[Tt]hree|[Ff]our|[Ff]ive)) {_MOD}({_KIDS})\b(?!['’])",
                      re.IGNORECASE | re.MULTILINE),
           re.compile(r'\b(?:her|his|their|my|has|have) (?:(?:young|little|baby|toddler) )?(twin)s?(?: (boys|girls|sons|'
                      r'daughters))?\b', re.IGNORECASE),
           re.compile(rf"\b(?:has|have|raising|raises) (a|an|one) ((?:{named._AGE[1:-1]})[ -]years?[ -]old)()"
                      r"(?=\s*(?:[.,;!)]|$|and\b|who\b))", re.IGNORECASE | re.MULTILINE),
           re.compile(rf"\bsingle {_PARENT}\b()", re.IGNORECASE))
# Children the description names in a list or after "and": "her kids Leo and Mia", "mom of Leo (7) and Mia (4)",
# "her two teenage daughters, Ava and Zoe", "her son Leo and daughter Mia", "a daughter named Rosa".
_ONE = rf"{named._NAME}(?: \(\d{{1,2}}\))?"
_LIST = rf"({_ONE}(?:, {_ONE})*(?:,? (?:and|&) {_ONE})?)"
_OPENS = r'(?:^|[.;:,(]\s*|\band )(?-i:[Tt]wo|[Tt]hree|[Ff]our|[Ff]ive) '
LISTED = (re.compile(rf"(?:\b(?:her|his|their|my|has|have|of|to|raising) (?:(?:{_COUNT}) )?|{_OPENS}){_MOD}({_KIDS}),?:? "
                     rf"(?:(?:named|called) )?{_LIST}", re.IGNORECASE | re.MULTILINE),
          re.compile(rf"\b{_PARENT} (?:of|to) (?:(?:{_COUNT})[,:]? )?()(){_LIST}", re.IGNORECASE),
          re.compile(rf"\b(?:and|&) (?:(?:her|his|their|my) )?{_MOD}((?:step-?)?(?:sons?|daughters?)|boys?|girls?),? "
                     rf"(?:(?:named|called) )?{_LIST}", re.IGNORECASE))
# How old a child is from the word before them: (youngest, oldest).
YOUNG_AGES = {**named.YOUNG_WORDS, 'teen': (13, 17), 'teenager': (13, 17), 'toddler': (1, 3), 'newborn': (0, 0),
              'small': (2, 8), 'school-age': (5, 12)}
# A pet's or a plant's "mom": "dog mom to Biscuit", "cat dad of two", "mom to a rescue dog".
PET_PARENT = re.compile(rf"\b(?:dog|cat|plant|pet|fur|puppy|kitty|bird|horse|chicken|bunny|fish)[- ]?{_PARENT}\b[^.;]*|"
                        rf"\b{_PARENT} (?:of|to) (?:(?:{_COUNT}) )?(?:[\w'-]+ ){{0,2}}?{named.SPECIES_WORD}s?\b",
                        re.IGNORECASE)
NOUN_AGES = ('baby', 'toddler', 'newborn', 'teen', 'teenager')
# Grown children the description mentions: no young kids are seeded beside them.
GROWN_KIDS = re.compile(rf"\b(?:grown|adult|grown-up) ({_KIDS})\b", re.IGNORECASE)
NONE = re.compile(r"\b(?:no (?:kids|children)|childless|child[- ]?free|never had (?:kids|children)|(?:doesn'?t|does "
                  r"not|don'?t|do not) have (?:any )?(?:kids|children)|never (?:wanted|wants) (?:kids|children))\b",
                  re.IGNORECASE)
WIDOWED = re.compile(r'\b(?:widow|widower|widowed|(?:her|his|their|my) late (?:wife|husband|partner|spouse))\b',
                     re.IGNORECASE)
EX = re.compile(rf"\b(?:her|his|their|my) ex(?:-| )?(wife|husband|partner|girlfriend|boyfriend|spouse)?,? "
                rf"(?:(?:named|called) )?{named.NAME}", re.IGNORECASE)
EX_WORDS = {'wife': ('she/her', 'ex-wife'), 'husband': ('he/him', 'ex-husband'), 'girlfriend': ('she/her', 'ex'),
            'boyfriend': ('he/him', 'ex'), 'partner': ('', 'ex'), 'spouse': ('', 'ex'), None: ('', 'ex')}
# Where the kids live, said outright: most telling first.
CUES = (('weekends', re.compile(r'\bevery other weekend with (?:her|him|them|me|us)\b|\bweekend (?:dad|mom|mum|'
                                r'parent)\b|\b(?:sees|has) (?:them|him|her|the kids|the children) (?:on|at) weekends\b',
                                re.IGNORECASE)),
        ('shared', re.compile(r'\b(?:shared|joint|split) custody\b|\bco-?parent\w*|\bweek on,? week off\b|'
                              r'\bevery other week\b|\b50/50\b', re.IGNORECASE)),
        # "Her ex has Leo every other weekend": the kids live with them.
        ('with_them', re.compile(rf'\bsingle {_PARENT}\b|\bfull custody\b|\bsolo parent\b|\braising (?:them|him|her|'
                                 r"\w+) (?:alone|on (?:her|his|their) own)\b|\bevery other weekend\b", re.IGNORECASE)))
OTHER_WORDS = {'she/her': 'mom', 'he/him': 'dad'}
OLD_OTHER_WORDS = {'she/her': 'mother', 'he/him': 'father'}


def first(name: str) -> str:
    return name.split()[0] if name.split() else name


def record(connection, timeline_id: str) -> dict | None:
    return optional(connection, 'SELECT * FROM companion_kids WHERE timeline_id=?', (timeline_id,))


# What their description says ---------------------------------------------------------------------------------------

def sex_of(noun: str) -> str | None:
    noun = noun.casefold().removeprefix('step').lstrip('-')
    return 'he/him' if noun.startswith(('son', 'boy')) else 'she/her' if noun.startswith(('daughter', 'girl')) else None


def young_word(modifier: str, noun: str = '') -> str:
    """'teenage' for "teenage" or "teenagers", '6-year-old' as written: the word `age_for` reads an age from."""
    word, noun = (modifier or '').casefold(), (noun or '').casefold().rstrip('s')
    if word in YOUNG_AGES or named.AGE_BEFORE.search(word):
        return word
    return noun if noun in NOUN_AGES else ''


def kid_words(definition: dict) -> str:
    """The description without its pets' and plants' "moms" and "dads"."""
    return PET_PARENT.sub('', named.text_of(definition))


def counted(text: str) -> tuple[int, list[dict]]:
    """(how many children the description counts, each as {pronouns, modifier}): 'two sons' are he/him, 'two
    teenage daughters' teenage."""
    count, found = 0, []
    for pattern in COUNTED:
        for match in pattern.finditer(text):
            groups = list(match.groups())
            word = (groups[0] or 'a').casefold()
            number = 2 if word == 'twin' else COUNT_WORDS.get(word, 1)
            modifier = groups[1] if len(groups) > 2 else ''
            noun = groups[-1] if len(groups) > 1 and groups[-1] else ''
            if number > count:
                count = number
                found = [{'pronouns': sex_of(noun), 'modifier': 'twin' if word == 'twin' else young_word(modifier, noun)}] * number
    return min(count, MOST), found


def listed(definition: dict) -> list[dict]:
    """Children the description names in a list ("her kids Leo and Mia", "mom of Leo (7) and Mia (4)") or after "and"
    ("her son Leo and daughter Mia"), as {name, pronouns, age, modifier, grown}."""
    text, result = kid_words(definition), {}
    for pattern in LISTED:
        for match in pattern.finditer(text):
            modifier, noun, names = match.groups()
            for raw in re.findall(named._NAME, names or ''):
                name = named.clean(raw, definition)
                if not name or name in result:
                    continue
                found = named.child_age(text, name, '')
                word = young_word(modifier or '', noun or '')
                result[name] = {'name': name, 'kind': 'child', 'pronouns': sex_of(noun or ''), 'age': found['age'], 'modifier': word,
                                'grown': found['grown'] or bool(named.GROWN.search(modifier or ''))}
    return list(result.values())


def other_named(text: str) -> dict | None:
    """The ex the description names as {name, pronouns, role}: "her ex-husband Mark"."""
    match = EX.search(text)
    if not match:
        return None
    pronouns_, role = EX_WORDS[match[1].casefold() if match[1] else None]
    return {'name': match[2], 'pronouns': pronouns_, 'role': role}


def cue(text: str) -> str | None:
    return next((pattern for pattern, found in CUES if found.search(text)), None)


def described(definition: dict) -> dict:
    """{kids: [{name, pronouns, age, modifier}], none, widowed, other, pattern}: the children the description names
    (not grown ones) and as many more as it counts, unnamed."""
    text = kid_words(definition)
    sheet = [person for person in named.people(definition) if person['kind'] == 'child']
    seen = {person['name'] for person in sheet}
    sheet += [person for person in listed(definition) if person['name'] not in seen]
    count, more = counted(text)
    kids = [{'name': person['name'], 'pronouns': person['pronouns'] or None, 'age': person['age'],
             'modifier': young_word(person['modifier'])} for person in sheet if named.minor(person)]
    kids += [{'name': None, 'pronouns': item['pronouns'], 'age': None, 'modifier': item['modifier']}
             for item in more[len(sheet):]]
    none = bool(NONE.search(text) or GROWN_KIDS.search(text)) and not kids
    return {'kids': kids[:MOST], 'none': none, 'widowed': bool(WIDOWED.search(text)), 'other': other_named(text),
            'pattern': cue(text)}


def may_have(definition: dict) -> bool:
    """A companion who reads as an adult, or gives an adult age of their own ("Dana, 38, and her 7-year-old son")."""
    from companion.world import intimacy
    return not intimacy.reads_as_minor(definition) or (intimacy.own_age(definition) or 0) >= intimacy.ADULT_AT


# Deciding, once per timeline -----------------------------------------------------------------------------------------

def settle(connection, companion: dict, world, now, fresh: bool = False) -> dict | None:
    """Their kids, decided the first time (`fresh`: with a circle just assembled, so a companion new to the user, who
    may be seeded some), and afterwards the children a changed description names that aren't there yet. A son or
    daughter of theirs who was made a circle person before (a v0.14 circle) leaves the circle for `circle_children`."""
    timeline_id = companion.get('active_timeline_id')
    if not ACTIVE or not timeline_id:
        return None
    row = record(connection, timeline_id)
    if row is None and not fresh and not circle.people(connection, timeline_id, include_removed=True):
        circle.ensure(connection, companion, world, now)  # Assembles the circle, which decides (fresh).
        return record(connection, timeline_id)
    if row is None:
        row = decide(connection, companion, world, now, fresh)
    else:
        reseed(connection, companion, world, row, now)
        add_described(connection, companion, world, row, now)
        grow_up(connection, companion, world, now)
    retire_circle_kids(connection, companion, now)
    return row


def decide(connection, companion: dict, world, now, fresh: bool) -> dict:
    definition, today = companion['version']['definition'], steps.local_today(companion, now)
    found = described(definition) if may_have(definition) else {'kids': [], 'none': True}
    town = [] if found['kids'] or found['none'] else town_kids(connection, companion, today)
    how, outcome = ('description' if found['kids'] else 'town' if town else 'none'), None
    if how == 'none' and fresh and not found['none'] and may_have(definition) and not still_to_come(definition):
        outcome = has_outcome(connection, companion, now)
        how = 'seeded' if outcome['picked'] == 1 else 'none'
    kids = found['kids'] or [{'name': None, 'pronouns': item['pronouns'], 'born_on': item['day'], 'modifier': ''}
                             for item in town] or (seeded(companion) if how == 'seeded' else [])
    other = other_for(connection, companion, world, found, town, now) if kids else None
    connection.execute(
        'INSERT INTO companion_kids (timeline_id, companion_id, how, other_id, pattern, consequence_id, since, '
        'created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (companion['active_timeline_id'], companion['id'], how, other['id'] if other else None,
         first_pattern(found, other), outcome['id'] if outcome else None, shifts.monday_of(today).isoformat(),
         stamp(now), stamp(now)))
    for index, kid in enumerate(kids):
        add_kid(connection, companion, world, kid, index, now)
    row = record(connection, companion['active_timeline_id'])
    if other and not row_pattern_fixed(found, other):
        custody_outcome(connection, companion, row, now)
    return record(connection, companion['active_timeline_id'])


def first_pattern(found: dict, other: dict | None) -> str:
    if other is None:
        return 'sole'
    if other.get('together'):
        return 'together'
    return found.get('pattern') or 'with_them'


def row_pattern_fixed(found: dict, other: dict) -> bool:
    """Whether the description (or a partner the kids live with) already says where they live."""
    return bool(other.get('together') or found.get('pattern'))


def still_to_come(definition: dict) -> bool:
    """Whether their description says children are still to come ("wants kids someday", "would love a family"): no
    kids are seeded for them."""
    from companion.life import parenthood
    return parenthood.described(definition) in ('yes', 'someday')


def has_facts(connection, companion: dict, now) -> dict:
    from companion.life import parenthood
    definition = companion['version']['definition']
    return {'age': parenthood.age_of(connection, companion, now), 'said_no': int(parenthood.described(definition) == 'no'),
            'sheet': {group for group in consequences.WORDS if consequences.sheet_has(definition, group)},
            'growing': families.level(connection)}


def has_outcome(connection, companion: dict, now) -> dict:
    """The engine's kids:has for a companion new to the user: none, or a child or two already."""
    return decide_choice(connection, companion, 'kids:has', f"kids:has:{companion['active_timeline_id']}",
                         has_facts(connection, companion, now), {}, now)


def decide_choice(connection, companion: dict, choice: str, subject: str, facts: dict, extra: dict, now) -> dict:
    labels = {'name': first(companion['version']['definition']['name']), **extra}
    table = consequences.tables()[choice]
    return consequences.decide(connection, timeline_id=companion['active_timeline_id'], choice=choice, subject=subject,
                               facts=facts, names=labels,
                               labels=[option['label'].format(**labels) for option in table['options']],
                               day=steps.local_today(companion, now).isoformat(), timestamp=stamp(now))


def custody_outcome(connection, companion: dict, row: dict, now) -> dict:
    """The engine's kids:custody: where the kids live, from whether their other parent lives in town."""
    other = circle.person(connection, row['other_id'])
    details = decode(other['details'])
    outcome = decide_choice(connection, companion, 'kids:custody', f"kids:custody:{row['timeline_id']}",
                            {'away': int(not details.get('local', True))}, {'other': first(other['name'])}, now)
    connection.execute('UPDATE companion_kids SET pattern=?, pattern_consequence_id=?, updated_at=? WHERE timeline_id=?',
                       (CUSTODY[outcome['picked']], outcome['id'], stamp(now), row['timeline_id']))
    return outcome


def seeded(companion: dict) -> list[dict]:
    """One child, or two or three, for a companion the engine gave kids."""
    seed = f"kids:{companion['active_timeline_id']}"
    draw = generators().unit(seed, 'count')
    count = 1 if draw < COUNTS[0] else 2 if draw < COUNTS[1] else 3
    return [{'name': None, 'pronouns': None, 'age': None, 'modifier': ''} for _ in range(count)]


def generators():
    from companion.world import generators as found
    return found


# The children -------------------------------------------------------------------------------------------------------

def companion_age(connection, companion: dict, today: date) -> int:
    return ages.companion_age(connection, companion['id'], companion['version']['definition'], today) or 30


def age_for(connection, companion: dict, kid: dict, seed: str, today: date) -> int:
    """Their age as the description gives it, else seeded: from the word before them ("baby", "teenage"), else
    anywhere from a newborn to as old as the companion's age allows."""
    if isinstance(kid.get('age'), int):
        return kid['age']
    oldest = max(0, min(GROWN - 1, companion_age(connection, companion, today) - PARENT_FROM))
    modifier = kid.get('modifier') or ''
    told = named.AGE_BEFORE.search(modifier)
    if told:
        return int(told[1]) if told[1].isdigit() else named.NUMBERS[told[1].casefold()]
    low, high = YOUNG_AGES.get(modifier, (0, oldest))
    low, high = min(low, oldest), min(high, oldest)
    return low + int(generators().unit(seed, 'age') * (high - low + 1))


def born_on(age: int, seed: str, today: date) -> date:
    """A birthday that makes them `age` today."""
    turned = ages.birthday_in(today.year - age, today.strftime('%m-%d'))
    return turned - timedelta(days=1 + int(generators().unit(seed, 'born') * 363))


def add_kid(connection, companion: dict, world, kid: dict, index: int, now, parent_id: str | None = None,
            mark: str | None = None, by_hand: bool = False) -> None:
    """One child into `circle_children`: the companion's own (`parent_id` None), or a partner's; `by_hand` one the
    user added."""
    timeline_id, today = companion['active_timeline_id'], steps.local_today(companion, now)
    seed = f"kids:{timeline_id}:{parent_id or companion['id']}:{index}"
    sex = kid.get('pronouns') or ('she/her' if generators().unit(seed, 'sex') < 0.49 else 'he/him')
    kept = None if kid.get('born_on') else circle_birthday(connection, timeline_id, kid.get('name'))
    born = kid.get('born_on') or (ages.born_from(age_for(connection, companion, kid, seed, today), kept, today) if kept
                                  else apart(connection, companion, kid, seed, today, parent_id or companion['id'],
                                             mark or f'{MARK}{timeline_id}'))
    name = kid.get('name') or families.baby_name(companion['version']['definition'], world, seed, sex,
                                                 families.taken_names(connection, companion))
    connection.execute(
        'INSERT INTO circle_children (id, timeline_id, parent_id, storyline_id, name, pronouns, title, born_on, status, '
        "by_hand, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'born', ?, ?, ?)",
        (identifier(), timeline_id, parent_id or companion['id'], mark or f'{MARK}{timeline_id}', name, sex,
         'friend' if parent_id else 'family', born.isoformat() if isinstance(born, date) else born, int(by_hand),
         stamp(now), stamp(now)))


def apart(connection, companion: dict, kid: dict, seed: str, today: date, parent_id: str, mark: str) -> date:
    """A birthday for a child whose day nobody gave: twins share their twin's, and any other child is born at least
    `SPACING` days from a brother or sister (the nearest age that allows it), unless their age was given."""
    siblings = [date.fromisoformat(row['born_on']) for row in many(
        connection, 'SELECT born_on FROM circle_children WHERE timeline_id=? AND parent_id=? AND storyline_id=?',
        (companion['active_timeline_id'], parent_id, mark))]
    if kid.get('modifier') == 'twin' and siblings:
        return siblings[-1]
    first_age = age_for(connection, companion, kid, seed, today)
    if isinstance(kid.get('age'), int) or named.AGE_BEFORE.search(kid.get('modifier') or ''):
        return born_on(first_age, seed, today)
    oldest = max(0, min(GROWN - 1, companion_age(connection, companion, today) - PARENT_FROM))
    for step in range(GROWN * 2):
        age = first_age + (step + 1) // 2 * (1 if step % 2 else -1)
        born = born_on(age, seed, today) if 0 <= age <= oldest else None
        if born and born <= today and all(abs((born - other).days) >= SPACING for other in siblings):
            return born
    return born_on(first_age, seed, today)


def circle_birthday(connection, timeline_id: str, name: str | None) -> str | None:
    """The birthday ('MM-DD') a circle from before v0.15 gave a son or daughter of this name, kept when they become
    a child of the companion's (their birthday was already told, in chat and on Today)."""
    if not name:
        return None
    for person in circle.people(connection, timeline_id, include_removed=True):
        if person['role'] in ('son', 'daughter') and decode(person['details']).get('sheet') == name:
            found = ages.stored(connection, 'circle', person['id'])
            return (found or {}).get('birthday') or decode(person['details']).get('birthday')
    return None


def own(connection, timeline_id: str, include_ended: bool = False) -> list[dict]:
    """The companion's own children on this timeline, oldest first."""
    status = '' if include_ended else " AND status='born'"
    return many(connection, f'SELECT * FROM circle_children WHERE timeline_id=? AND storyline_id=?{status} '
                'ORDER BY born_on, id', (timeline_id, f'{MARK}{timeline_id}'))


def add_described(connection, companion: dict, world, row: dict, now) -> None:
    """Children a changed description names who aren't there yet (and weren't taken out by the user)."""
    definition = companion['version']['definition']
    if not may_have(definition):
        return
    there = {first(kid['name']) for kid in own(connection, row['timeline_id'], include_ended=True)}
    removed = set(decode(row['removed']))
    found = described(definition)
    new = [kid for kid in found['kids'] if kid['name'] and first(kid['name']) not in there | removed]
    for index, kid in enumerate(new, start=len(there)):
        add_kid(connection, companion, world, kid, index, now)
    if new and not row['other_id'] and not found['widowed']:
        other = other_for(connection, companion, world, found, [], now)
        connection.execute("UPDATE companion_kids SET other_id=?, how='description', pattern=?, updated_at=? "
                           'WHERE timeline_id=?', (other['id'], first_pattern(found, other), stamp(now),
                                                   row['timeline_id']))


def grow_up(connection, companion: dict, world, now) -> None:
    """A child of theirs who has turned 18 is a grown son or daughter in their circle, living in town, and no longer
    one of the kids (companion/life/our_child.py does the same for the pair's own)."""
    timeline_id, today = companion['active_timeline_id'], steps.local_today(companion, now)
    for kid in own(connection, timeline_id):
        age = families.age_of(kid, today)
        if age < GROWN:
            continue
        rows = circle.people(connection, timeline_id, include_removed=True)
        person = circle.build(companion['version']['definition'], world, timeline_id, 1, f"kids:{kid['id']}:grown",
                              {row['name'] for row in rows}, sheet=False)[0]
        person |= {'name': first(kid['name']), 'role': {'she/her': 'daughter', 'he/him': 'son'}.get(kid['pronouns'], 'child'),
                   'details': person['details'] | {'pronouns': kid['pronouns'], 'age': age, 'local': True,
                                                   'grown_kid': kid['id']}}
        kind = grown_kind(connection, companion, timeline_id)
        person['details'] = {key: value for key, value in person['details'].items() if key != 'folk'} | \
            ({'folk': kind} if kind != lifespans.HUMAN else {})
        ordinal = max((row['ordinal'] for row in rows), default=-1) + 1
        circle.insert(connection, timeline_id, [person], ordinal, now)
        person_id = one(connection, 'SELECT id FROM circle_people WHERE timeline_id=? AND ordinal=?',
                        (timeline_id, ordinal))['id']
        ages.keep(connection, 'circle', person_id, age, date.fromisoformat(kid['born_on']).strftime('%m-%d'), today, now)
        connection.execute("UPDATE circle_children SET status='ended', updated_at=? WHERE id=?", (stamp(now), kid['id']))


def grown_kind(connection, companion: dict, timeline_id: str) -> str:
    """A kid of theirs' kind once grown (companion/world/lifespans.py): from the companion and their other parent
    (an elf and a human have a half-elf)."""
    definition = companion['version']['definition']
    data = ages.city_of(connection, definition)
    row = optional(connection, 'SELECT other_id FROM companion_kids WHERE timeline_id=?', (timeline_id,))
    other = optional(connection, 'SELECT details FROM circle_people WHERE id=?', (row['other_id'],)) \
        if row and row['other_id'] else None
    found = decode(other['details']) if other else {}
    return lifespans.blend(lifespans.sheet_kind(definition, data), found.get('own_kind') or found.get('folk'), data)


def retire_circle_kids(connection, companion: dict, now) -> None:
    """A son or daughter the description names who a circle from before v0.15 holds as a person (grown-up, with a
    job): out of the circle, since they are a child (`circle_children` holds them now)."""
    names = {person['name'] for person in named.people(companion['version']['definition']) if named.minor(person)}
    if not names:
        return
    for person in circle.people(connection, companion['active_timeline_id']):
        if decode(person['details']).get('sheet') in names and person['role'] in ('son', 'daughter'):
            connection.execute("UPDATE circle_people SET status='removed', updated_at=? WHERE id=?",
                               (stamp(now), person['id']))


# Their other parent -----------------------------------------------------------------------------------------------

def other_for(connection, companion: dict, world, found: dict, town: list[dict], now) -> dict | None:
    """The kids' other parent in their circle, as {id, together}: none when the description says they were widowed."""
    if found.get('widowed'):
        return None
    partner = sheet_partner(connection, companion)
    if partner and not found.get('other'):
        return {'id': partner['id'], 'together': True}
    wanted = found.get('other') or (town_other(town) if town else None) or {}
    if not wanted and not found.get('pattern') and older(connection, companion):
        return None  # In an older city a parent raising kids on their own had most often lost their other parent.
    return {'id': add_other(connection, companion, world, wanted, now), 'together': False}


def older(connection, companion: dict) -> bool:
    """An older city (New York 1925, London 1895, Camelot), where kids did not go between two homes by a rota."""
    return families.older(families.era_of(connection, companion['version']['definition']))


def sheet_partner(connection, companion: dict) -> dict | None:
    """A partner the description names, in their circle (companion/life/named.py)."""
    names = {person['name'] for person in named.people(companion['version']['definition'])
             if person['kind'] == 'partner'}
    return next((person for person in circle.people(connection, companion['active_timeline_id'])
                 if decode(person['details']).get('sheet') in names), None) if names else None


def town_other(town: list[dict]) -> dict | None:
    partner = town[-1].get('partner')
    return {'name': partner['full'], 'pronouns': partner['pronouns'], 'role': 'co-parent'} if partner else None


def add_other(connection, companion: dict, world, wanted: dict, now) -> str:
    """A circle person for the kids' other parent: who the description or the town names, else seeded, near the
    companion's age and living in town."""
    definition, timeline_id = companion['version']['definition'], companion['active_timeline_id']
    rows = circle.people(connection, timeline_id, include_removed=True)
    taken = {row['name'] for row in rows} | families.taken_names(connection, companion)
    person = circle.build(definition, world, timeline_id, 1, f'kids:{timeline_id}:other', taken, sheet=False)[0]
    details = person['details']
    pronouns_ = wanted.get('pronouns') or details.get('pronouns') or 'they/them'
    # Near the companion's age in human terms: a human, so an elf of 312 has a co-parent in their forties.
    life = ages.companion_life_age(connection, companion['id'], definition, steps.local_today(companion, now)) or 30
    age = life + int(generators().unit(timeline_id, 'other-age') * 7) - 3
    if wanted.get('name'):
        person['name'] = first(wanted['name'])
        details = details | ({'full_name': wanted['name']} if ' ' in wanted['name'] else {}) | {'sheet': wanted['name']}
    person |= {'role': wanted.get('role') or 'co-parent',
               'details': details | {'pronouns': pronouns_, 'age': max(age, PARENT_FROM + 1), 'local': True,
                                     'co_parent': True}}
    ordinal = max((row['ordinal'] for row in rows), default=-1) + 1
    circle.insert(connection, timeline_id, [person], ordinal, now)
    added = one(connection, 'SELECT id FROM circle_people WHERE timeline_id=? AND ordinal=?', (timeline_id, ordinal))['id']
    # Their days start now, as a grandparent's do (circle.add_grandparent): nothing is written for them before they
    # joined, such as two weeks of a circle from v0.14.
    connection.execute('INSERT OR IGNORE INTO agenda_cursors (timeline_id, subject, through) VALUES (?, ?, ?)',
                       (timeline_id, added, stamp(now)))
    return added


# A townsperson's own --------------------------------------------------------------------------------------------------

def town_kids(connection, companion: dict, today: date) -> list[dict]:
    """Babies a companion made from a townsperson had with their partner while still one of the town's people:
    [{pronouns, day, partner}] (companion/world/couples.py, which leaves a companion's own out from then on)."""
    if not companion.get('townsfolk_key'):
        return []
    from companion.life import network
    from companion.world import couples, townsfolk
    data = network.city(connection, companion)
    sheet = townsfolk.find({**data, 'companions': ()}, companion['townsfolk_key'])
    if not sheet:
        return []
    town = {key: value for key, value in sheet.items() if key != 'cast'}
    found = couples.babies(town, {**data, 'companions': ()}, (townsfolk.EPOCH, today))
    return [{'pronouns': None, 'day': item['day'], 'partner': item['partner']} for item in found[:MOST]]


# A love-life partner's kids -------------------------------------------------------------------------------------------

def partner_kids(connection, companion: dict, world, person: dict, now) -> int:
    """A new love-life partner (companion/life/love_life.py) past their twenties may have kids of their own, a child
    or two, under them in the circle. Returns how many."""
    if not ACTIVE or not families.level(connection):  # Growing families at None: nobody new comes with kids.
        return 0
    details = decode(person['details'])
    age = details.get('age') if isinstance(details.get('age'), int) else 0
    chance = next((odds for least, odds in PARTNER_ODDS if age >= least), 0)
    seed = f"kids:partner:{person['id']}"
    if generators().unit(seed, 'has') >= chance:
        return 0
    count = 1 if generators().unit(seed, 'count') < COUNTS[0] else 2
    oldest = max(0, min(GROWN - 1, age - PARENT_FROM))
    for index in range(count):
        kid = {'name': None, 'pronouns': None, 'age': int(generators().unit(seed, 'age', index) * (oldest + 1)),
               'modifier': ''}
        add_kid(connection, companion, world, kid, index, now, person['id'], f"{PARTNER_MARK}{companion['active_timeline_id']}")
    return count


def partners_kids(connection, timeline_id: str) -> list[dict]:
    """Children of a love-life partner still in the circle, with the partner's name."""
    return many(connection, 'SELECT c.*, p.name AS parent_name, p.id AS person_id FROM circle_children c JOIN '
                "circle_people p ON p.id=c.parent_id WHERE c.timeline_id=? AND c.storyline_id=? AND c.status='born' "
                "AND p.status='active' ORDER BY c.born_on", (timeline_id, f'{PARTNER_MARK}{timeline_id}'))


# Where the kids are ---------------------------------------------------------------------------------------------------

def pattern_of(connection, row: dict) -> tuple[str, str]:
    """(where the kids live, how it was decided: 'set', 'seeded' or 'fixed' by the description or the household)."""
    if row['chosen']:
        return row['chosen'], 'set'
    if row['pattern_consequence_id']:
        found = consequences.by_id(connection, row['pattern_consequence_id'])
        return CUSTODY[found['picked']], 'seeded'
    return row['pattern'], 'fixed' if row['how'] == 'description' else 'seeded'


def with_them(pattern: str, since: date, day: date) -> bool:
    """Whether the kids are with the companion on this day: alternate weekends or weeks count from `since`."""
    odd = ((shifts.monday_of(day) - shifts.monday_of(since)).days // 7) % 2 == 1
    weekend = day.weekday() >= 5
    if pattern == 'with_them':
        return not (weekend and odd)
    if pattern == 'shared':
        return not odd
    if pattern == 'weekends':
        return weekend and not odd
    return True


# The chat context -------------------------------------------------------------------------------------------------

def kid_text(kid: dict, today: date) -> str:
    """'Leo (7, your son)', 'Ivy (a baby, 7 months old, your daughter)'."""
    word = {'she/her': 'daughter', 'he/him': 'son'}.get(kid['pronouns'], 'child')
    years = families.age_text(kid, today)
    told = families.how_old(kid, today) if not years.isdigit() else years
    return f"{kid['name']} ({told}, your {word})"


def other_text(connection, companion: dict, row: dict) -> tuple[str, str]:
    """('their dad Sam', 'Sam'), with the role the companion knows them by."""
    other = circle.person(connection, row['other_id'])
    found = decode(other['details']).get('pronouns', '')
    words = OLD_OTHER_WORDS if not modern(companion) else OTHER_WORDS
    word = circle.said(words.get(found, 'other parent'), companion['version']['definition'])  # 'mum' in London.
    return f"their {word} {other['name']}", first(other['name'])


def modern(companion: dict) -> bool:
    from companion.world import perception
    return perception.era_modern(companion['version']['definition'])


def where_line(connection, companion: dict, row: dict, pattern: str, kids: list[dict] | None = None) -> str:
    """'- They live with you and spend every other weekend with their dad Mark.'; for one child, by name ('- Leo lives
    with you and spends every other weekend with his dad Mark.', A/B 2026-10-19: as clear, 5/5 each)."""
    one = kids[0] if kids and len(kids) == 1 else None
    who = first(one['name']) if one else 'They'
    s = 's' if one else ''
    if pattern == 'sole' or not row['other_id']:
        whose = families.fill_child('{their}', one) if one else 'their'
        return f'- {who} live{s} with you; {whose} other parent is not in the picture.'
    them, _name = other_text(connection, companion, row)
    if one:
        them = families.fill_child('{their}', one) + them.removeprefix('their')
    return {'together': f'- {who} live{s} with you and {them}.',
            'with_them': f'- {who} live{s} with you and spend{s} every other weekend with {them}.',
            'shared': f'- {who} spend{s} a week with you, then a week with {them}, turn and turn about.',
            'weekends': f'- {who} live{s} with {them} and spend{s} every other weekend with you.'}[pattern]


def user_line(connection, companion: dict, kids: list[dict], now) -> str | None:
    """For a romance: what the user knows of the kids, met them, or is their step-parent."""
    if companion['version']['definition'].get('relationship') != 'romance':
        return None
    names = steps.names_text([first(kid['name']) for kid in kids])
    if living_together(connection, companion):
        return f'- You and the user live together, so the user is {names}\'s step-parent now.'
    if met(connection, companion):
        return f'- The user has met {names}.'
    if dinner := meeting_soon(connection, companion):
        return f'- The user is meeting {names} at the {dinner} you planned, along with your people.'
    return (f"- The user knows you have {'a child' if len(kids) == 1 else 'kids'} but hasn't met "
            f"{'them' if len(kids) > 1 else names} yet; you'd introduce them once things are serious.")


def living_together(connection, companion: dict) -> bool:
    """Whether the user lives with this romance companion (companion/life/moving_in.py): their step-parent then."""
    from companion.life import moving_in
    return companion['version']['definition'].get('relationship') == 'romance' and bool(moving_in.living(connection,
                                                                                                         companion))


def met(connection, companion: dict) -> bool:
    """Whether the user has met their kids: at the family dinner for the "meeting their people" step (not drinks with
    their friends), or by knowing their people already (a pair from way back)."""
    timeline_id = companion['active_timeline_id']
    if optional(connection, "SELECT id FROM people_meetups WHERE timeline_id=? AND why='step' AND kind='family' AND "
                "status='done'", (timeline_id,)):
        return True
    return bool(optional(connection, "SELECT id FROM people_impressions WHERE timeline_id=? LIMIT 1", (timeline_id,))) \
        and not optional(connection, "SELECT id FROM people_meetups WHERE timeline_id=? AND why='step'", (timeline_id,))


def meeting_soon(connection, companion: dict) -> str | None:
    row = optional(connection, "SELECT kind FROM people_meetups WHERE timeline_id=? AND why='step' AND kind='family' "
                   "AND status IN ('planned', 'booked')", (companion['active_timeline_id'],))
    return 'family dinner' if row else None


def at_dinner_on(connection, companion: dict, day: date) -> bool:
    """Whether the family dinner where the user first meets their people (and their kids) is on this day: the kids are
    with them that day, whatever the rota says."""
    from companion.life import outings, their_people
    return any(row['activity'] == their_people.AT_FAMILY and row['local_date'] == day.isoformat() and
               (row['place'] if isinstance(row['place'], dict) else decode(row['place'])).get('first')
               for row in outings.in_force(connection, companion['active_timeline_id'], day.isoformat()))


def at_dinner(connection, companion: dict) -> str:
    """', and your kids Leo and Mia' (', and your son Leo') for the family dinner's scene; '' with none, or with the
    adult side on."""
    found = own(connection, companion['active_timeline_id']) if ACTIVE and companion.get('active_timeline_id') else []
    if not found or families.withheld(connection):
        return ''
    if len(found) == 1:
        word = {'she/her': 'daughter', 'he/him': 'son'}.get(found[0]['pronouns'], 'child')
        return f", and your {word} {first(found[0]['name'])}"
    return f", and your kids {steps.names_text([first(kid['name']) for kid in found])}"


def at_dinner_guests(connection, companion: dict, day: date) -> list[dict]:
    """The kids at the family dinner, for Today's guest line: [{'name': 'Leo', 'role': 'son, 6'}]; none with the
    adult side on."""
    found = own(connection, companion['active_timeline_id']) if ACTIVE and companion.get('active_timeline_id') else []
    if not found or families.withheld(connection):
        return []
    result = []
    for kid in found:
        born = date.fromisoformat(kid['born_on'])
        age = day.year - born.year - ((day.month, day.day) < (born.month, born.day))
        word = {'she/her': 'daughter', 'he/him': 'son'}.get(kid['pronouns'], 'child')
        result.append({'name': first(kid['name']), 'role': f"{word}, {age}" if age else f"{word}, a baby"})
    return result


def context_lines(connection, companion: dict, now) -> list[tuple[str, str]]:
    """(identity, line) for the 'kids' section: their children, where they live, and where the user stands with them;
    and the step-children of a love-life partner they live with. None with the adult side on."""
    timeline_id = companion.get('active_timeline_id')
    if not ACTIVE or not timeline_id or families.withheld(connection):
        return []
    today = steps.local_today(companion, now)
    result = own_lines(connection, companion, now, today)
    return result + step_lines(connection, companion, today)


def own_lines(connection, companion: dict, now, today: date) -> list[tuple[str, str]]:
    row, kids = record(connection, companion['active_timeline_id']), own(connection, companion['active_timeline_id'])
    if not row or not kids:
        return []
    listed = steps.names_text([kid_text(kid, today) for kid in kids])
    result = [('kids:who', f"- You have {'a child' if len(kids) == 1 else f'{len(kids)} children'}: {listed}.")]
    pattern, _how = pattern_of(connection, row)
    result.append((f'kids:where:{pattern}', where_line(connection, companion, row, pattern, kids)))
    if line := user_line(connection, companion, kids, now):
        result.append(('kids:user', line))
    return result


def step_lines(connection, companion: dict, today: date) -> list[tuple[str, str]]:
    """A love-life partner's kids, once the companion lives with the partner: their step-children."""
    from companion.life import love_life
    result = []
    for found in love_life.partners(connection, companion['active_timeline_id']):
        if found['secret'] or 'living together' not in love_life.lived(connection, companion, found):
            continue
        kids = [kid for kid in partners_kids(connection, companion['active_timeline_id'])
                if kid['person_id'] == found['person_id'] and families.age_of(kid, today) < GROWN]
        if kids:
            listed = steps.names_text([kid_text(kid, today).replace('your ', f"{first(found['name'])}'s ") for kid in kids])
            result.append((f"kids:step:{found['id']}", f"- You live with {found['name']} and {listed}: you are "
                                                        f"{'their' if len(kids) > 1 else 'a'} step-parent."))
    return result


def today_line(connection, companion: dict, now) -> tuple[str, str] | None:
    """Where the kids are today, for 'circle_now', when they don't always live with the companion."""
    timeline_id = companion.get('active_timeline_id')
    row = record(connection, timeline_id) if ACTIVE and timeline_id else None
    kids = own(connection, timeline_id) if row else []
    if not kids or families.withheld(connection):
        return None
    pattern, _how = pattern_of(connection, row)
    if pattern in ('together', 'sole') or not row['other_id']:
        return None
    today = steps.local_today(companion, now)
    them, _name = other_text(connection, companion, row)
    who = 'the kids' if len(kids) > 1 else first(kids[0]['name'])
    since = date.fromisoformat(row['since'])
    here = here_on(connection, row, pattern, since, today) or at_dinner_on(connection, companion, today)
    where = 'with you' if here else f'with {them}'
    line = f"- Today {who} {'are' if len(kids) > 1 else 'is'} {where}."
    if not here and (coming := next_weekend(pattern, since, today,
                                            lambda day: here_on(connection, row, pattern, since, day))):
        _them, name = other_text(connection, companion, row)
        whom = 'them' if len(kids) > 1 else first(kids[0]['name'])
        has = 'them' if len(kids) > 1 else families.fill_child('{them}', kids[0])
        line += f' {coming} are your weekend with {whom}; {name} has {has} until then.'
    return f'kids:today:{here}', line


def here_on(connection, row: dict, pattern: str, since: date, day: date) -> bool:
    """Whether the kids are with the companion on this day: as the stays with their other parent say
    (companion/life/stays.py), else by the pattern."""
    from companion.life import stays
    return stays.with_companion(stays.rows_for(connection, row['timeline_id'], stays.KIDS, row['other_id']), day,
                                with_them(pattern, since, day))


def next_weekend(pattern: str, since: date, today: date, here=None) -> str | None:
    """'This Saturday and Sunday (10 and 11 October)': the next weekend the kids spend with them, when they live with
    the other parent (A/B 2026-10-19: 6/6 said whose weekend it is, 0/6 without)."""
    if pattern != 'weekends':
        return None
    here = here or (lambda day: with_them(pattern, since, day))
    saturday = next((day for day in (today + timedelta(days=offset) for offset in range(1, 15))
                     if day.weekday() == 5 and here(day)), None)
    if saturday is None:
        return None
    sunday = saturday + timedelta(days=1)
    days = f'{saturday.day} and {sunday.day} {sunday:%B}' if saturday.month == sunday.month else \
        f'{saturday.day} {saturday:%B} and {sunday.day} {sunday:%B}'
    return f"{'This ' if (saturday - today).days < 7 else ''}Saturday and Sunday ({days})"


# The Character page -------------------------------------------------------------------------------------------------

def view(connection, companion: dict, world, now, show_odds: bool) -> dict:
    """The kids part of the Family panel: each child, where they live, their other parent, and the user as their
    step-parent once they live together. `shown` False with none."""
    row = settle(connection, companion, world, now)
    kids = own(connection, companion['active_timeline_id']) if row else []
    if not row or not kids:
        return {'shown': False, 'can_add': bool(row) and can_add(companion)}
    today = steps.local_today(companion, now)
    pattern, how = pattern_of(connection, row)
    other = circle.person(connection, row['other_id']) if row['other_id'] else None
    labels = {'name': first(companion['version']['definition']['name']), 'other': first(other['name']) if other else ''}
    keys = [key for key in PATTERNS if fits(row, key)]
    return {'shown': True, 'how': row['how'], 'kids': [kid_view(kid, today) for kid in kids],
            'can_add': can_add(companion) and len(kids) < BY_HAND_MOST,
            'other': other_view(other) if other else None,
            'others': [other_view(person) for person in others(connection, row)],
            'pattern': pattern, 'pattern_how': how,
            'patterns': [{'key': key, 'label': PATTERN_LABELS[key].format(**labels)} for key in keys],
            'pattern_consequence_id': row['pattern_consequence_id'] if show_odds else None,
            'consequence_id': row['consequence_id'] if show_odds and row['how'] == 'seeded' else None,
            'detail': PATTERN_DETAILS[pattern].format(**labels), 'step_parent': living_together(connection, companion),
            'meeting': meeting(connection, companion)}


def meeting(connection, companion: dict) -> str | None:
    """For a romance not living together: whether the user has met the kids ('met'), is about to ('soon'), or not
    yet ('unmet')."""
    if companion['version']['definition'].get('relationship') != 'romance' or living_together(connection, companion):
        return None
    return 'met' if met(connection, companion) else 'soon' if meeting_soon(connection, companion) else 'unmet'


def kid_view(kid: dict, today: date) -> dict:
    return {'id': kid['id'], 'name': kid['name'], 'pronouns': kid['pronouns'], 'born_on': kid['born_on'],
            'age': families.age_of(kid, today), 'age_text': families.age_text(kid, today),
            'relation': {'she/her': 'daughter', 'he/him': 'son'}.get(kid['pronouns'], 'child'),
            'by_hand': bool(kid['by_hand'])}


def other_view(person: dict) -> dict:
    """Their other parent, or someone who could be: `made` when the app made them for the kids (renamed in place when
    the user names someone else, `set_other`), `made_up` when nobody named them either."""
    details = decode(person['details'])
    return {'id': person['id'], 'name': person['name'], 'role': person['role'], 'made': bool(details.get('co_parent')),
            'made_up': bool(details.get('co_parent')) and not details.get('sheet') and not details.get('by_hand')}


def others(connection, row: dict) -> list[dict]:
    """Who in their circle could be the kids' other parent: the one who is, then an ex, a co-parent or a partner."""
    people = circle.people(connection, row['timeline_id'])
    fit = [person for person in people if person['id'] != row['other_id'] and
           (person['role'] in OTHER_ROLES or decode(person['details']).get('co_parent'))]
    return [person for person in people if person['id'] == row['other_id']] + fit


def fits(row: dict, pattern: str) -> bool:
    """Whether a pattern fits who the kids live with: alone only with no other parent, all together only in one home."""
    return (pattern == 'sole') == (row['other_id'] is None) and (pattern == 'together') == (row['pattern'] == 'together')


def update(connection, companion: dict, now, pattern: str | None = None, remove: str | None = None,
           restore: str | None = None) -> None:
    """The user sets where the kids live ('auto' gives it back to the app), takes a child out of their life, or
    undoes that."""
    row = record(connection, companion['active_timeline_id'])
    require(row is not None, 'They have no children to change.', 404)
    if pattern is not None:
        require(pattern in ('auto', *PATTERNS), 'Pick where the kids live.', 422)
        require(pattern == 'auto' or fits(row, pattern), "That doesn't fit who the kids live with.", 422)
        connection.execute('UPDATE companion_kids SET chosen=?, updated_at=? WHERE timeline_id=?',
                           (None if pattern == 'auto' else pattern, stamp(now), row['timeline_id']))
    if remove is not None:
        kid = optional(connection, "SELECT * FROM circle_children WHERE id=? AND storyline_id=? AND status='born'",
                       (remove, f"{MARK}{row['timeline_id']}"))
        require(kid is not None, 'That child is not one of theirs.', 404)
        connection.execute("UPDATE circle_children SET status='ended', updated_at=? WHERE id=?", (stamp(now), kid['id']))
        removed = [*decode(row['removed']), first(kid['name'])]
        connection.execute('UPDATE companion_kids SET removed=?, updated_at=? WHERE timeline_id=?',
                           (encode(removed), stamp(now), row['timeline_id']))
    if restore is not None:
        bring_back(connection, row, restore, now)


def bring_back(connection, row: dict, kid_id: str, now) -> None:
    """Undo taking a child out of their life."""
    kid = optional(connection, "SELECT * FROM circle_children WHERE id=? AND storyline_id=? AND status='ended'",
                   (kid_id, f"{MARK}{row['timeline_id']}"))
    require(kid is not None, 'That child is not one of theirs.', 404)
    connection.execute("UPDATE circle_children SET status='born', updated_at=? WHERE id=?", (stamp(now), kid['id']))
    removed = [name for name in decode(row['removed']) if name != first(kid['name'])]
    connection.execute('UPDATE companion_kids SET removed=?, updated_at=? WHERE timeline_id=?',
                       (encode(removed), stamp(now), row['timeline_id']))


# By hand ------------------------------------------------------------------------------------------------------------

def can_add(companion: dict) -> bool:
    """Whether the user can add a child of theirs: never for a companion who reads as under 18 (`may_have`)."""
    return ACTIVE and bool(companion.get('active_timeline_id')) and may_have(companion['version']['definition'])


def add(connection, companion: dict, world, now, name: str | None = None, age: int | None = None,
        pronouns: str | None = None) -> None:
    """A child of theirs the user adds by hand, the way a pet is added: the name, age and whether they're a son or
    daughter the app picks when left out, as for any child of theirs (`add_kid`). The first child of someone with
    none gets an other parent the way kids from their description do (`other_for`: the ex or partner it names, else
    someone seeded; nobody when it says they were widowed), and the engine says where they live."""
    require(can_add(companion), "They can't have children of their own.", 422)
    row = settle(connection, companion, world, now)
    require(row is not None, "They can't have children of their own.", 422)
    timeline_id, today = row['timeline_id'], steps.local_today(companion, now)
    require(len(own(connection, timeline_id)) < BY_HAND_MOST, f'They have {BY_HAND_MOST} children already.', 422)
    kid = {'name': kid_name(connection, timeline_id, name), 'pronouns': pronouns,
           'age': kid_age(connection, companion, age, today)}
    every = own(connection, timeline_id, include_ended=True)
    if not every and not row['other_id']:
        found = described(companion['version']['definition'])
        if other := other_for(connection, companion, world, found, [], now):
            connection.execute('UPDATE companion_kids SET other_id=?, pattern=?, chosen=NULL, updated_at=? '
                               'WHERE timeline_id=?', (other['id'], first_pattern(found, other), stamp(now), timeline_id))
            if not row_pattern_fixed(found, other):
                custody_outcome(connection, companion, record(connection, timeline_id), now)
    add_kid(connection, companion, world, kid, len(every), now, by_hand=True)


def edit(connection, companion: dict, kid_id: str, now, name: str | None = None, age: int | None = None,
         pronouns: str | None = None) -> None:
    """The user changes a child's name, age (their birthday stays the same day of the year) or whether they're a son
    or daughter. A child renamed from the name their description gives isn't brought back under the old one
    (`add_described`)."""
    row = record(connection, companion['active_timeline_id'])
    require(row is not None, 'They have no children to change.', 404)
    kid = optional(connection, "SELECT * FROM circle_children WHERE id=? AND storyline_id=? AND status='born'",
                   (kid_id, f"{MARK}{row['timeline_id']}"))
    require(kid is not None, 'That child is not one of theirs.', 404)
    today = steps.local_today(companion, now)
    renamed = kid_name(connection, row['timeline_id'], name, kid['id']) or kid['name']
    if first(renamed) != first(kid['name']) and first(kid['name']) not in decode(row['removed']):
        connection.execute('UPDATE companion_kids SET removed=?, updated_at=? WHERE timeline_id=?',
                           (encode([*decode(row['removed']), first(kid['name'])]), stamp(now), row['timeline_id']))
    born = date.fromisoformat(kid['born_on'])
    if (aged := kid_age(connection, companion, age, today)) is not None and aged != families.age_of(kid, today):
        born = ages.born_from(aged, born.strftime('%m-%d'), today)
    connection.execute('UPDATE circle_children SET name=?, pronouns=?, born_on=?, updated_at=? WHERE id=?',
                       (renamed, pronouns or kid['pronouns'], born.isoformat(), stamp(now), kid['id']))


def kid_name(connection, timeline_id: str, name: str | None, kid_id: str | None = None) -> str | None:
    """A name the user gave, tidied; None when they left it empty. Never one a brother or sister of theirs has."""
    name = ' '.join((name or '').split())
    if not name:
        return None
    taken = {first(kid['name']).casefold() for kid in own(connection, timeline_id) if kid['id'] != kid_id}
    require(first(name).casefold() not in taken, f'They already have a child called {first(name)}.', 409)
    return name


def kid_age(connection, companion: dict, age: int | None, today: date) -> int | None:
    if age is None:
        return None
    require(0 <= age < GROWN, 'A child of theirs is 17 or under. Add a grown son or daughter to their circle.', 422)
    require(companion_age(connection, companion, today) - age >= PARENT_YOUNGEST,
            f"That's older than a child of {first(companion['version']['definition']['name'])}'s could be.", 422)
    return age


def set_other(connection, companion: dict, world, now, other: str, name: str | None = None,
              pronouns: str | None = None) -> None:
    """Who the kids' other parent is: 'none' (raising them on their own), someone in their circle (`others`), or
    'new', someone the user names. Someone the app made for the kids is renamed in place for 'new' rather than a
    second person made, and leaves their circle when someone already in it is picked instead."""
    row = record(connection, companion['active_timeline_id'])
    require(row is not None, 'They have no children to change.', 404)
    current = circle.person(connection, row['other_id']) if row['other_id'] else None
    made = current is not None and bool(decode(current['details']).get('co_parent'))
    if other == 'new':
        name = ' '.join((name or '').split())
        require(bool(name), 'Give their other parent a name.', 422)
        person_id = rename_other(connection, current, name, pronouns, now) if made else \
            add_other(connection, companion, world, {'name': name, 'pronouns': pronouns}, now)
    elif other == 'none':
        person_id = None
    else:
        require(other in {person['id'] for person in others(connection, row)},
                'Pick someone in their circle, someone new or nobody.', 422)
        person_id = other
    if made and person_id != current['id'] and current['role'] == 'co-parent':
        circle.set_status(connection, current['id'], 'removed', now)
    place_kids(connection, companion, row, person_id, now)


def rename_other(connection, person: dict, name: str, pronouns: str | None, now) -> str:
    details = {key: value for key, value in decode(person['details']).items() if key not in ('full_name', 'sheet')}
    details |= ({'full_name': name} if ' ' in name else {}) | ({'pronouns': pronouns} if pronouns else {}) | {'by_hand': True}
    connection.execute('UPDATE circle_people SET name=?, details=?, revision=revision+1, updated_at=? WHERE id=?',
                       (first(name), encode(details), stamp(now), person['id']))
    return person['id']


def place_kids(connection, companion: dict, row: dict, person_id: str | None, now) -> None:
    """Where the kids live once their other parent changed: on their own with nobody; all together with a partner;
    else as before, or as the engine picks (kids:custody) when it hadn't."""
    if person_id is None:
        connection.execute("UPDATE companion_kids SET other_id=NULL, pattern='sole', chosen=NULL, "
                           'pattern_consequence_id=NULL, updated_at=? WHERE timeline_id=?', (stamp(now), row['timeline_id']))
        return
    together = circle.person(connection, person_id)['role'] in PARTNER_WORDS
    pattern = 'together' if together else row['pattern'] if row['pattern'] not in ('sole', 'together') else 'with_them'
    chosen = row['chosen'] if row['chosen'] not in ('sole', 'together') and not together else None
    connection.execute('UPDATE companion_kids SET other_id=?, pattern=?, chosen=?, pattern_consequence_id=?, '
                       'updated_at=? WHERE timeline_id=?',
                       (person_id, pattern, chosen, None if together else row['pattern_consequence_id'], stamp(now),
                        row['timeline_id']))
    if not together and not row['pattern_consequence_id'] and row['pattern'] in ('sole', 'together'):
        custody_outcome(connection, companion, record(connection, row['timeline_id']), now)


def change(connection, companion: dict, consequence_id: str, option: int, now) -> dict:
    """The user makes a decision go another way (Hidden values): where the kids live follows the pick (`pattern_of`);
    kids:has taken back to none takes away the children the engine gave them, and turned to kids gives them some the next
    time their life is read (`settle`)."""
    outcome = consequences.change(connection, consequence_id, option, stamp(now))
    row = optional(connection, 'SELECT * FROM companion_kids WHERE consequence_id=?', (consequence_id,))
    if outcome['choice'] == 'kids:has' and row:
        # The kids the user added by hand are theirs to keep or take out, whatever the engine's pick.
        connection.execute('DELETE FROM circle_children WHERE storyline_id=? AND by_hand=0',
                           (f"{MARK}{row['timeline_id']}",))
        connection.execute('UPDATE companion_kids SET how=?, removed=?, updated_at=? WHERE timeline_id=?',
                           ('seeded' if option == 1 else 'none', encode([]), stamp(now), row['timeline_id']))
    return consequences.by_id(connection, consequence_id)


def reseed(connection, companion: dict, world, row: dict, now) -> None:
    """Kids for a companion whose kids:has was changed to kids (`change`), made with the world for their names."""
    if row['how'] != 'seeded' or own(connection, row['timeline_id'], include_ended=True):
        return
    for index, kid in enumerate(seeded(companion)):
        add_kid(connection, companion, world, kid, index, now)
    if not row['other_id'] and not older(connection, companion):
        other_id = add_other(connection, companion, world, {}, now)
        connection.execute("UPDATE companion_kids SET other_id=?, pattern='with_them', updated_at=? WHERE timeline_id=?",
                           (other_id, stamp(now), row['timeline_id']))
        custody_outcome(connection, companion, record(connection, row['timeline_id']), now)


# Forks ------------------------------------------------------------------------------------------------------------

def copy(connection, parent_id: str, new_id: str, ids: dict) -> None:
    """A fork keeps their kids, where they live and a partner's kids, with the circle people remapped."""
    companion_id = one(connection, 'SELECT companion_id FROM timelines WHERE id=?', (parent_id,))['companion_id']
    row = record(connection, parent_id)
    if row:
        # The engine's picks come along as the fork's own (not the parent timeline's rows, which a change there would
        # move), so the fork keeps where the kids live and can change it without touching the parent.
        has, where = (row[key] and consequences.copy(connection, row[key], new_id, f'{label}{new_id}')
                      for key, label in (('consequence_id', 'kids:has:'), ('pattern_consequence_id', 'kids:custody:')))
        connection.execute(
            'INSERT INTO companion_kids (timeline_id, companion_id, how, other_id, pattern, chosen, consequence_id, '
            'pattern_consequence_id, since, removed, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (new_id, row['companion_id'], row['how'], ids.get(row['other_id']), row['pattern'], row['chosen'],
             has, where, row['since'], row['removed'], row['created_at'], row['updated_at']))
    for mark, new_mark in ((f'{MARK}{parent_id}', f'{MARK}{new_id}'),
                           (f'{PARTNER_MARK}{parent_id}', f'{PARTNER_MARK}{new_id}')):
        for kid in many(connection, 'SELECT * FROM circle_children WHERE timeline_id=? AND storyline_id=?',
                        (parent_id, mark)):
            parent = companion_id if mark.startswith(f'{MARK}{parent_id}') else ids.get(kid['parent_id'])
            if parent:
                connection.execute(
                    'INSERT INTO circle_children (id, timeline_id, parent_id, storyline_id, name, pronouns, title, '
                    'born_on, status, by_hand, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (identifier(), new_id, parent, new_mark, kid['name'], kid['pronouns'], kid['title'], kid['born_on'],
                     kid['status'], kid['by_hand'], kid['created_at'], kid['updated_at']))
