"""People and pets the character sheet names, found by rules (no model).

"Her younger brother Tunde lives in Atlanta", "He lives with his sister Annika", "their partner Marguerite and an
elderly beagle named Hush Puppy", "a one-eyed cat named Pickle": the circle (companion/life/circle.py) and the
home (companion/life/home.py) are seeded, so without this they would invent a brother Darrell or a cat Maple
beside the ones the user wrote. Only a relation followed by a capitalised name counts ("her father still brings
it up" names nobody), in the sheet's own third person or in a first-person field like the routine.
"""
import re

TEXT_FIELDS = ('identity', 'background', 'routine', 'personality', 'location')
OWNER = r'(?:my|her|his|their)'
# Relation word: (circle role kind, pronouns, generator role).
RELATIONS = {
    'mom': ('parent', 'she/her', 'parent'), 'mother': ('parent', 'she/her', 'parent'),
    'mum': ('parent', 'she/her', 'parent'), 'dad': ('parent', 'he/him', 'parent'),
    'father': ('parent', 'he/him', 'parent'), 'sister': ('sibling', 'she/her', 'sibling'),
    'brother': ('sibling', 'he/him', 'sibling'), 'twin': ('sibling', '', 'sibling'),
    'cousin': ('cousin', '', 'cousin'), 'partner': ('partner', '', 'close-friend'),
    'wife': ('partner', 'she/her', 'close-friend'), 'husband': ('partner', 'he/him', 'close-friend'),
    'girlfriend': ('partner', 'she/her', 'close-friend'), 'boyfriend': ('partner', 'he/him', 'close-friend'),
    'fiancée': ('partner', 'she/her', 'close-friend'), 'fiancé': ('partner', 'he/him', 'close-friend'),
    'fiancee': ('partner', 'she/her', 'close-friend'), 'fiance': ('partner', 'he/him', 'close-friend'),
    'son': ('child', 'he/him', 'friend'), 'daughter': ('child', 'she/her', 'friend'),
    'best friend': ('close friend', '', 'close-friend'), 'friend': ('friend', '', 'friend'),
    'roommate': ('roommate', '', 'friend'), 'flatmate': ('roommate', '', 'friend'),
    'housemate': ('roommate', '', 'friend'), 'neighbor': ('neighbor', '', 'neighbor'),
    'neighbour': ('neighbor', '', 'neighbor'), 'coworker': ('coworker', '', 'coworker'),
    'co-worker': ('coworker', '', 'coworker'), 'colleague': ('coworker', '', 'coworker'),
    'boss': ('boss', '', 'mentor'), 'mentor': ('mentor', '', 'mentor'),
    'aunt': ('aunt', 'she/her', 'cousin'), 'uncle': ('uncle', 'he/him', 'cousin'),
    'grandmother': ('grandparent', 'she/her', 'parent'), 'grandma': ('grandparent', 'she/her', 'parent'),
    'grandfather': ('grandparent', 'he/him', 'parent'), 'grandpa': ('grandparent', 'he/him', 'parent'),
}
# The circle's own roles each relation can stand in for, closest first.
SLOTS = {'parent': ('parent', 'mom', 'dad'), 'sibling': ('sibling', 'sister', 'brother'), 'cousin': ('cousin',),
         'close friend': ('close friend', 'longtime friend'),
         'friend': ('friend', 'new friend', 'longtime friend', 'old friend from school', 'old classmate'),
         'roommate': ('roommate from years ago',), 'neighbor': ('neighbor',), 'coworker': ('coworker',),
         'mentor': ('mentor',), 'boss': ('mentor',)}
MODIFIER = (r'(?:(?:older|younger|little|big|baby|twin|oldest|youngest|eldest|late|ex-|childhood|new|old|'
            r'elderly|kid|teenage|adult|grown|step|(?:\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|'
            r'twelve|thirteen|fourteen|fifteen|sixteen|seventeen)[ -]years?[ -]old)[ -]?)*')
RELATION_WORDS = '|'.join(re.escape(word) for word in sorted(RELATIONS, key=len, reverse=True))
# How the circle lists them when the relation is not a parent or sibling (those follow their pronouns).
ROLE_WORDS = {'best friend': 'close friend', 'flatmate': 'roommate', 'housemate': 'roommate', 'neighbour': 'neighbor',
              'co-worker': 'coworker', 'colleague': 'coworker', 'fiancee': 'fiancée', 'fiance': 'fiancé',
              'grandma': 'grandmother', 'grandpa': 'grandfather'}
_WORD = r"[A-Z][a-zà-ÿ'’-]+"
_NAME = rf"(?-i:{_WORD}(?: (?!(?:And|But|Or|The|In|On|At|Of)\b){_WORD})?)"
NAME = f'({_NAME})'
NOT_NAMES = {'I', 'And', 'But', 'Or', 'So', 'The', 'A', 'An', 'He', 'She', 'They', 'It', 'This', 'That', 'There',
             'We', 'My', 'His', 'Her', 'Their', 'Our', 'Your', 'Today', 'Tonight', 'Tomorrow', 'Yesterday', 'Monday',
             'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday', 'Mondays', 'Tuesdays',
             'Wednesdays', 'Thursdays', 'Fridays', 'Saturdays', 'Sundays', 'Christmas', 'Easter', 'Thanksgiving',
             'God', 'Mom', 'Dad', 'Mum', 'In', 'On', 'At', 'Of', 'To', 'For', 'From', 'With', 'By', 'When', 'While', 'After', 'Before', 'Since', 'Who', 'Which', 'Also', 'Still'}
PERSON = (re.compile(rf"\b{OWNER} (?P<modifier>{MODIFIER})(?P<relation>{RELATION_WORDS}),? (?:(?:named|called) )?"
                     rf"(?P<name>{_NAME})", re.IGNORECASE),
          re.compile(rf"(?P<name>{_NAME}), {OWNER} (?P<modifier>{MODIFIER})(?P<relation>{RELATION_WORDS})\b",
                     re.IGNORECASE))
# Someone who is no longer in their life: an ex, or a relative who has died.
GONE = re.compile(r'\b(?:ex|late)\b', re.IGNORECASE)
# Pet word: the home's own variety (companion/life/home.py PETS).
SPECIES = {
    'cat': 'cat', 'kitten': 'cat', 'tabby': 'cat', 'tomcat': 'cat',
    'dog': 'dog', 'puppy': 'dog', 'pup': 'dog', 'mutt': 'dog', 'beagle': 'dog', 'terrier': 'dog', 'retriever': 'dog',
    'labrador': 'dog', 'lab': 'dog', 'poodle': 'dog', 'pug': 'dog', 'corgi': 'dog', 'husky': 'dog', 'collie': 'dog',
    'greyhound': 'dog', 'dachshund': 'dog', 'bulldog': 'dog', 'shepherd': 'dog', 'spaniel': 'dog',
    'chihuahua': 'dog', 'boxer': 'dog', 'pit bull': 'dog', 'pitbull': 'dog', 'rottweiler': 'dog', 'schnauzer': 'dog',
    'rabbit': 'rabbit', 'bunny': 'rabbit',
    'bird': 'bird', 'parrot': 'parrot', 'budgie': 'bird', 'parakeet': 'bird', 'canary': 'bird', 'cockatiel': 'bird',
    'macaw': 'parrot', 'cockatoo': 'parrot', 'hamster': 'hamster', 'guinea pig': 'guinea-pig', 'ferret': 'ferret',
    'tortoise': 'tortoise', 'turtle': 'tortoise', 'snake': 'snake', 'lizard': 'lizard',
    'gecko': 'lizard', 'bearded dragon': 'lizard', 'goldfish': 'fish', 'betta': 'fish', 'horse': 'horse',
    'pony': 'horse', 'mare': 'horse', 'hen': 'chickens', 'chicken': 'chickens',
}
SPECIES_WORD = '(' + '|'.join(re.escape(word) for word in sorted(SPECIES, key=len, reverse=True)) + ')'
LOOK = r"((?:[\w'’-]+ ){0,3}?)"
PET = (re.compile(rf"\b(?:a|an|the|{OWNER}) {LOOK}{SPECIES_WORD}s?,? (?:(?:named|called) ){NAME}", re.IGNORECASE),
       re.compile(rf"\b{OWNER} {LOOK}{SPECIES_WORD},? {NAME}", re.IGNORECASE),
       re.compile(rf"{NAME}, {OWNER} {LOOK}{SPECIES_WORD}\b", re.IGNORECASE))
# A child's age the sheet gives: "her son Leo, 7", "Leo (7)", "Leo is seven", "her 7-year-old son Leo".
NUMBERS = {word: value for value, word in enumerate(
    'zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen '
    'eighteen nineteen twenty'.split())}
_AGE = rf"(\d{{1,2}}|{'|'.join(NUMBERS)})"
AGE_AFTER = rf"\b(?:NAME)\b(?:,? (?:who is |who's |aged |is )?| \(){_AGE}\)?(?:[ -]years?[ -]old)?(?![\w-])"
AGE_BEFORE = re.compile(rf"\b{_AGE}[ -]years?[ -]old\b", re.IGNORECASE)
# How old a child is likely to be from the word before them, when no age is given: (youngest, oldest).
YOUNG_WORDS = {'baby': (0, 1), 'little': (2, 8), 'kid': (4, 11), 'teenage': (13, 17), 'young': (2, 9)}
GROWN = re.compile(r'\b(?:grown|adult)\b', re.IGNORECASE)
# A job the sheet gives someone: "Tunde, a nurse at Mercy", "Tunde works as a paralegal", "Tunde is a teacher".
# `sure` patterns say it is a job; the others count only when the words name a career the app knows
# (companion/life/circle_edit.py `career_match`), so "Tunde, a quiet man" gives Tunde no job.
_JOB = r"(?P<job>[a-z][a-z'’ -]{1,40}?)"
_AT = r"(?: (?:at|for) (?-i:(?P<at>(?:the )?[A-Z][\w&'’.-]*(?: (?:of |and |& )?[A-Z][\w&'’.-]*)*)))?"
_STOP = r"(?=[,.;:!?)]|$| (?:who|and|but|in|on|with|since|for|at|from|there|now|again|downtown|nearby)\b)"
JOBS = ((True, r"\bNAME(?: [A-Z][\w'’-]+)?,? (?:who )?(?:works|worked|is working|is employed|has a job) as (?:a |an )?"
         + _JOB + _AT + _STOP),
        (False, r"\bNAME(?: [A-Z][\w'’-]+)?(?:, | \()(?:a |an )" + _JOB + _AT + _STOP),
        (False, r"\bNAME(?: [A-Z][\w'’-]+)?(?: who)? (?:is|was) (?:now )?(?:a |an )" + _JOB + _AT + _STOP))
ELSEWHERE = r"\b{name}\b[^.;]*?\blives? (?:in|out in|over in|back in|down in|up in) (?-i:([A-Z][\w.'’-]*(?: [A-Z][\w.'’-]*)*))"


def text_of(definition: dict) -> str:
    return '\n'.join(str(definition.get(key) or '') for key in TEXT_FIELDS)


def clean(name: str, definition: dict) -> str | None:
    """The name without a trailing non-name word, or None when it is no name at all."""
    words = name.split()
    while words and words[-1] in NOT_NAMES:
        words.pop()
    if not words or words[0] in NOT_NAMES:
        return None
    own = set((definition.get('name') or '').split())
    if words[0] in own:
        return None
    return ' '.join(words)


def people(definition: dict) -> list[dict]:
    """[{name, relation, kind, pronouns, role, generator_role, local}] in the order the sheet names them, one per name.
    `local` is False when the sheet says they live in another city."""
    text, found = text_of(definition), {}
    pets = {pet['name'] for pet in pets_of(definition)}
    hits = []
    for pattern in PERSON:
        hits += [(match.start(), match['relation'].casefold(), match['name'], match['modifier'])
                 for match in pattern.finditer(text)]
    for _start, relation, raw, modifier in sorted(hits):
        name = clean(raw, definition)
        if not name or name in found or name in pets or GONE.search(modifier):
            continue
        kind, pronouns, role = RELATIONS[relation]
        elsewhere = re.search(ELSEWHERE.format(name=re.escape(name)), text)
        home = (definition.get('home_city') or '').replace('-', ' ').casefold()
        local = not elsewhere or (bool(home) and home in elsewhere.group(1).casefold())
        found[name] = {'name': name, 'relation': relation, 'kind': kind, 'pronouns': pronouns,
                       'role': ROLE_WORDS.get(relation, relation),
                       'generator_role': role, 'local': local, 'modifier': modifier.strip(' -').casefold()}
        if kind == 'child':
            found[name] |= child_age(text, name, modifier)
        else:
            found[name] |= job_of(text, name) | adult_age(text, name, modifier)
    return list(found.values())


def job_of(text: str, name: str) -> dict:
    """{job, employer, sure} for a grown-up the sheet gives a job, the first way it says it; {} for none."""
    hits = []
    for sure, pattern in JOBS:
        match = re.search(pattern.replace("NAME", re.escape(name)), text, re.IGNORECASE)
        if match:
            hits.append((match.start(), not sure, match))
    if not hits:
        return {}
    _start, unsure, match = min(hits, key=lambda hit: (hit[0], hit[1]))
    return {'job': match['job'].strip(" -'’"), 'employer': (match['at'] or '').strip(), 'sure': not unsure}


def adult_age(text: str, name: str, modifier: str) -> dict:
    """{age} for a grown-up the sheet gives an age ("her 61-year-old mom Ana", "Ana, 61"); {} for none."""
    found = child_age(text, name, modifier)['age']
    return {'age': found} if found is not None and found >= 16 else {}


def child_age(text: str, name: str, modifier: str) -> dict:
    """{age (None when the sheet gives none), grown} for a son or daughter the sheet names: grown when the sheet says
    "grown" or "adult", or gives an age of 18 or more."""
    for match in (AGE_BEFORE.search(modifier), re.search(AGE_AFTER.replace('NAME', re.escape(name)), text, re.IGNORECASE)):
        if match:
            value = match[1]
            age = int(value) if value.isdigit() else NUMBERS[value.casefold()]
            return {'age': age, 'grown': age >= 18}
    return {'age': None, 'grown': bool(GROWN.search(modifier))}


def in_circle(definition: dict) -> list[dict]:
    """The people the sheet names who join the circle: everyone but a child (`minor`)."""
    return [person for person in people(definition) if not minor(person)]


def minor(person: dict) -> bool:
    """A son or daughter the sheet names who isn't said to be grown: a child, so words only (companion/life/kids.py),
    never someone in the circle. Unsure reads as a child."""
    return person['kind'] == 'child' and not person.get('grown')


def pets_of(definition: dict) -> list[dict]:
    """[{name, variety, description}] for each named pet: "a one-eyed cat named Pickle" -> Pickle, cat."""
    text, found = text_of(definition), {}
    hits = []
    for pattern in PET:
        for match in pattern.finditer(text):
            groups = match.groups()
            look, species, name = groups if pattern is not PET[2] else (groups[1], groups[2], groups[0])
            hits.append((match.start(), look, species, name))
    for _start, look, species, raw in sorted(hits):
        name = clean(raw, definition)
        if not name or name in found:
            continue
        words = f'{look}{species}'.strip()
        vowel = words[:1].lower() in 'aeiou' and not words.lower().startswith(('one', 'uni', 'use', 'eu'))
        description = f"{'an' if vowel else 'a'} {words}"
        found[name] = {'name': name, 'variety': SPECIES[species.casefold()], 'description': description}
    return list(found.values())
