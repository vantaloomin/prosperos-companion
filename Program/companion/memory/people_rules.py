"""Rule-based capture of the people in the user's life, with no model call.

"My sister Jo just got engaged", "Jo works at the library" (once Jo is known) and "She loves
climbing" (right after Jo in the same message) become facts about one person. Like the user's own
facts, only declarative statements count: `extraction.sentences` has already dropped questions,
hypotheticals, quotes and roleplay. A bare "my friend" or "my cousin" names nobody in particular,
so it needs a name; "my mum" or "my boss" is one person even without one.
"""
import re
from dataclasses import dataclass

# Relations that usually mean one person, so "my mum" is enough to know who.
SINGLE = ('mum', 'mom', 'mother', 'dad', 'father', 'wife', 'husband', 'partner', 'girlfriend', 'boyfriend',
          'fiancé', 'fiancée', 'fiance', 'fiancee', 'boss', 'manager', 'best friend', 'roommate', 'flatmate',
          'housemate', 'landlord', 'landlady', 'therapist', 'stepmom', 'stepdad', 'stepmother', 'stepfather',
          'grandma', 'grandpa', 'grandmother', 'grandfather', 'nan', 'gran', 'granny', 'grandad', 'mentor',
          'sister', 'brother', 'son', 'daughter', 'twin', 'ex', 'ex-girlfriend', 'ex-boyfriend', 'ex-wife',
          'ex-husband', 'sister-in-law', 'brother-in-law', 'mother-in-law', 'father-in-law')
# Relations most people have several of: only a name says which one.
NAMED_ONLY = ('friend', 'coworker', 'co-worker', 'colleague', 'cousin', 'aunt', 'auntie', 'uncle', 'niece', 'nephew',
              'neighbour', 'neighbor', 'classmate', 'teammate', 'client', 'teacher', 'professor', 'tutor', 'coach')
PETS = ('cat', 'dog', 'rabbit', 'parrot', 'hamster', 'puppy', 'kitten', 'horse', 'guinea pig', 'tortoise', 'turtle',
        'bird', 'lizard', 'snake', 'ferret')
RELATIONS = SINGLE + NAMED_ONLY + PETS
RELATION = '(' + '|'.join(re.escape(item) for item in sorted(RELATIONS, key=len, reverse=True)) + ')'
MODIFIER = r'(?:(?:older|younger|little|big|baby|twin|oldest|youngest|eldest|old|childhood|new|work) )?'
_WORD = r"[A-Z][\w-]*(?:['’](?!s\b)[\w-]+)?"
NAME = rf"(?-i:({_WORD}(?: (?!(?:I|And|But|Or|So|The|My)\b){_WORD})?))"
# Capitalised words that start a clause rather than name someone.
NOT_NAMES = {'i', 'and', 'but', 'or', 'so', 'the', 'a', 'an', 'he', 'she', 'they', 'it', 'this', 'that', 'there',
             'you', 'we', 'my', 'his', 'her', 'their', 'our', 'your', 'today', 'tonight', 'tomorrow', 'yesterday',
             'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'god', 'mom', 'mum',
             'dad', 'honestly', 'also', 'anyway', 'well', 'yeah', 'yes', 'no', 'oh', 'ok', 'okay', 'just', 'then'}
PRONOUN = re.compile(r'^(he|she|they)\b(?! (?:said|says|told|think|thinks|thought|asked|wants|want)\b)',
                     re.IGNORECASE)
POSSESSIVE_PRONOUN = re.compile(r'^(his|her|their) ', re.IGNORECASE)

THING = r"([^,.;!?]+)"
PLACE = r"(?-i:([A-Z][\w.'’-]*(?:[ -](?:(?:de|la|del|upon|of|on) )?[A-Z][\w.'’-]*)*))"
CLAUSE_END = re.compile(r'\s+(?:because|but|although|though|so|and i|and my|when|since|if|which|who)\b.*$',
                        re.IGNORECASE)
NOT_THINGS = {'me', 'us', 'you', 'it', 'that', 'this', 'them', 'him', 'her', 'those', 'these', 'everything',
              'nothing', 'something', 'anything', 'everyone', 'nobody', 'it all'}
# News that is about a loss: remembered (if allowed), but never something to ask about casually.
GRIEF = re.compile(r'\b(?:passed away|died|lost (?:his|her|their) (?:mum|mom|mother|dad|father|baby|husband|wife))\b',
                   re.IGNORECASE)

# Topics that hold one current value per person, like the user's own home city.
SINGLE_TOPICS = {'work', 'home_city', 'birthday', 'age'}
TOPIC_LABELS = {'who': 'Who they are', 'work': 'Work', 'home_city': 'Home city', 'birthday': 'Birthday', 'age': 'Age',
                'likes': 'Likes', 'dislikes': 'Dislikes', 'studies': 'Studies', 'has': 'Has', 'news': 'News'}

PREDICATES = (
    ('birthday', re.compile(r"^(?:'s|’s) birthday is (?:on )?" + THING, re.IGNORECASE)),
    ('work', re.compile(r'^(?:just |recently |now )?(?:works|is working|started working|started a (?:new )?job|got a '
                        rf'(?:new )?job) (?:as an? {THING}|at (?:the )?{PLACE}|for (?:the )?{PLACE}|in {THING})', re.IGNORECASE)),
    ('home_city', re.compile(rf'^(?:still |now )?(?:lives|is living|is based) in {PLACE}', re.IGNORECASE)),
    ('moved', re.compile(rf'^(?:just |finally |recently )?(?:moved|relocated) (?:to|into) {PLACE}', re.IGNORECASE)),
    ('age', re.compile(r"^(?:is|'s|’s|just turned|turned|is turning) (\d{1,3})(?: years old| years| now)?$",
                       re.IGNORECASE)),
    ('likes', re.compile(r'^(?:really |absolutely )?(?:loves|likes|enjoys|adores|is (?:really |super )?into|'
                         r'is obsessed with) ' + THING, re.IGNORECASE)),
    ('dislikes', re.compile(r"^(?:really )?(?:hates|dislikes|can't stand|cannot stand|doesn't like|does not like) "
                            + THING, re.IGNORECASE)),
    ('studies', re.compile(r'^(?:is )?(?:studying|studies|is doing a degree in|is at (?:uni|university|college) '
                           r'studying) ' + THING, re.IGNORECASE)),
    ('has', re.compile(r'^has (an? (?:new )?(?:dog|cat|puppy|kitten|baby|son|daughter|kid|boyfriend|girlfriend|'
                       r'husband|wife|partner|rabbit|horse|bird|parrot|hamster)' + r"(?: (?:named|called) [A-Z][\w'’-]+)?"
                       r'|(?:two|three|four|\d) (?:kids|children|dogs|cats|sons|daughters))', re.IGNORECASE)),
    ('news', re.compile(
        r'^(?:just |finally |recently |also |actually )?('
        r'got (?:engaged|married|divorced|promoted|fired|laid off|dumped|into \w+(?: \w+)?|a (?:new )?(?:car|house|flat|'
        r'apartment|puppy|kitten|dog|cat|tattoo|job offer|scholarship|place at \w+(?: \w+)?))'
        r'|is (?:getting (?:married|divorced|engaged)|pregnant|expecting|having a baby|in (?:the )?hospital|'
        r'(?:really )?sick|ill|retiring|graduating|moving (?:out|house|abroad|to [A-Z]\w+)|starting (?:a new job|uni|'
        r'university|college|school))'
        r'|had (?:a baby|twins|surgery|an operation|a (?:big )?(?:fight|argument) with \w+)'
        r'|broke up with \w+|split up with \w+|passed (?:her|his|their) \w+(?: test| exams?)?|failed (?:her|his|their) '
        r'\w+(?: test| exams?)?|graduated(?: from \w+(?: \w+)?)?|retired|quit (?:her|his|their) job|lost (?:her|his|'
        r'their) (?:job|mum|mom|mother|dad|father)|passed away|died|bought (?:a|an|the) (?:house|flat|car|apartment)'
        r'|adopted (?:a|an) \w+|won \w+(?: \w+)?|ran (?:a|the) (?:marathon|half marathon)|finished (?:her|his|their) '
        r'\w+(?: \w+)?)', re.IGNORECASE)),
)


@dataclass(frozen=True)
class Reference:
    """Who a sentence is about: a name, a relation or both, as the user said them."""
    name: str | None
    relation: str | None

    @property
    def key(self) -> str:
        """A provisional identity until formation matches it to a stored person."""
        basis = self.name.casefold() if self.name else f'my-{self.relation}'
        return re.sub(r'[^\w-]+', '_', basis).strip('_')

    @property
    def label(self) -> str:
        return self.name or f'Your {self.relation}'

    def as_dict(self) -> dict:
        return {'name': self.name, 'relation': self.relation}


def is_name(text: str | None, exclude=()) -> bool:
    if not text:
        return False
    first = text.split()[0].casefold().rstrip("'’s")
    return first not in NOT_NAMES and text.casefold() not in exclude and not first.startswith(("i'", 'i’'))


def clean(text: str) -> str | None:
    text = CLAUSE_END.sub('', text).strip(' \'"')
    text = re.sub(r'\s+(?:now|these days|nowadays|any ?more|lately|again|too)$', '', text, flags=re.IGNORECASE)
    if not text or text.casefold() in NOT_THINGS or len(text.split()) > 8:
        return None
    return text


def relation_word(match_text: str) -> str:
    return ' '.join(match_text.casefold().split())


def references(sentence: str, known: dict, exclude=()) -> list[tuple[int, Reference]]:
    """Each place the sentence names someone, as (end offset, reference), in order of appearance."""
    found = []
    for match in re.finditer(rf'\bmy {MODIFIER}{RELATION}(?:,? {NAME})?', sentence, re.IGNORECASE):
        relation = relation_word(match.group(1))
        name = match.group(2) if is_name(match.group(2), exclude) else None
        if name is None and relation in NAMED_ONLY:
            continue
        end = match.end() if name else match.end(1)
        if name and match.group(0).rstrip().endswith(','):
            end = match.end()
        found.append((match.start(), end, Reference(name, relation)))
    for name, relation in known.items():
        for match in re.finditer(rf"(?<![\w'’]){re.escape(name)}(?![\w-])", sentence):
            if not any(start <= match.start() < end for start, end, _ref in found):
                found.append((match.start(), match.end(), Reference(name, relation)))
    found.sort(key=lambda item: item[0])
    return [(end, reference) for _start, end, reference in found]


def introductions(sentence: str, exclude=()):
    """"My sister is called Ana", "My sister Jo", "Jo is my best friend", "I have a dog called Rex"."""
    if match := re.search(rf"\bmy {MODIFIER}{RELATION}(?:'s name| name)? is (?:called |named )?{NAME}", sentence,
                          re.IGNORECASE):
        if is_name(match.group(2), exclude):
            yield Reference(match.group(2), relation_word(match.group(1)))
            return
    if match := re.search(rf"^{NAME},? (?:is|'s|’s) (?:also )?my {MODIFIER}{RELATION}\b", sentence, re.IGNORECASE):
        if is_name(match.group(1), exclude):
            yield Reference(match.group(1), relation_word(match.group(2)))
            return
    if match := re.search(rf"\bi(?:'ve| have)(?: got)? an? {MODIFIER}{RELATION}(?: (?:named|called) {NAME})?", sentence,
                          re.IGNORECASE):
        relation, name = relation_word(match.group(1)), match.group(2)
        if name and is_name(name, exclude):
            yield Reference(name, relation)
        elif relation not in NAMED_ONLY:
            yield Reference(None, relation)
        return
    for match in re.finditer(rf'\bmy {MODIFIER}{RELATION},? {NAME}', sentence, re.IGNORECASE):
        if is_name(match.group(2), exclude):
            yield Reference(match.group(2), relation_word(match.group(1)))


def predicate(rest: str):
    """The fact a sentence states about the person it starts with: (topic, value) or None."""
    rest = rest.lstrip(' ,')
    for topic, pattern in PREDICATES:
        if match := pattern.search(rest):
            value = next((group for group in match.groups() if group), None)
            value = clean(value) if value else None
            if value:
                return ('home_city' if topic == 'moved' else topic), value, topic == 'moved'
    return None


@dataclass
class Found:
    """One captured statement about a person."""
    reference: Reference
    topic: str
    value: str
    changed: bool = False

    @property
    def grief(self) -> bool:
        return self.topic == 'news' and bool(GRIEF.search(self.value))


def scan(sentence: str, known: dict, previous: Reference | None, exclude=()) -> tuple[list[Found], Reference | None]:
    """Facts about people in one sentence, and who the next sentence's "she" or "he" would be."""
    found = [Found(reference, 'who', reference.name or f'Has a {reference.relation}')
             for reference in introductions(sentence, exclude)]
    named = {item.reference.name: item.reference.relation for item in found if item.reference.name}
    candidates = [(sentence[end:], reference) for end, reference in references(sentence, {**known, **named}, exclude)]
    # "My sister is called Ana" names one person twice: the bare relation is the named sister.
    by_relation = {}
    for _rest, reference in candidates:
        if reference.name and reference.relation:
            by_relation.setdefault(reference.relation, reference)
    candidates = [(rest, by_relation.get(reference.relation, reference) if not reference.name else reference)
                  for rest, reference in candidates]
    if previous and (match := PRONOUN.match(sentence)):
        candidates.insert(0, (sentence[match.end():], previous))
    elif previous and (match := POSSESSIVE_PRONOUN.match(sentence)):
        candidates.insert(0, ("'s " + sentence[match.end():], previous))
    for rest, reference in candidates:
        if result := predicate(rest):
            topic, value, changed = result
            found.append(Found(reference, topic, value, changed))
            break
    people = {item.reference for item in found} | {reference for _rest, reference in candidates}
    return found, next(iter(people)) if len(people) == 1 else None


def mentioned(text: str, people: list[dict]) -> list[str]:
    """Ids of stored people the text refers to by name or as "my <relation>", for when they last came up."""
    folded = text.casefold()
    return [person['id'] for person in people
            if (person['name'] and re.search(rf"(?<![\w'’]){re.escape(person['name'])}(?![\w-])", text))
            or (person['relation'] and re.search(rf"\bmy {MODIFIER}{re.escape(person['relation'])}\b", folded))]
