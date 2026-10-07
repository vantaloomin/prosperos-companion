"""Checks on what the companion says about themselves, against what the user says and the character definition.

A slip in one reply ("my sister Jo", "i work at Starbucks") would otherwise be noted as a self fact and
offered in every later context, so the model repeats it. Two rule-based checks hold such a fact as a
`conflict` in Character Studio instead, where the user keeps or removes it:

- The user corrects the companion in chat: "your sister is Ashley, not Jo", "you don't have a brother",
  "you don't work at Starbucks", "you didn't grow up in Ohio". The facts that sentence contradicts stop
  applying at once, so the very next reply no longer sees them, and the same value said again later
  waits too. Questions, hypotheticals, quoted text and *actions* are skipped.
- The definition names where the companion grew up or works ("grew up in Duluth", "works at Mercy"),
  and a reply names somewhere else.

`conflicts_with` says why: `user:<message id>` or `definition:<what it says>`. No model is used.
"""
import re

from companion.database import optional

USER = 'user:'
DEFINITION = 'definition:'
ACTIONS = re.compile(r'\*[^*\n]+\*')
QUOTED = re.compile(r'"[^"]*"|“[^”]*”')
SENTENCES = re.compile(r'[^.!?\n]+[.!?]*')
SKIP = re.compile(r"\b(?:if|maybe|might|what if|imagine|pretend|suppose|would|could)\b|\?$", re.IGNORECASE)
NAME = r"(?-i:([A-Z][\w'’-]+))"
PLACE = r"(?-i:([A-Z][\w&'’-]*(?: (?:of |the |de )?[A-Z][\w&'’-]*)*))"
KIN = (r'(older brother|younger brother|little brother|big brother|older sister|younger sister|little sister|'
       r'big sister|brother|sister|mom|mother|dad|father|grandma|grandmother|grandpa|grandfather|aunt|uncle|'
       r'cousin|best friend|roommate|boss|stepmom|stepdad|son|daughter|cat|dog|kitten|puppy|rabbit|bunny|parrot|'
       r'hamster|turtle|tortoise|snake|fish|lizard|ferret|horse)')
SAME = {'mother': 'mom', 'father': 'dad'}
# One of each: naming a different one says the noted name is wrong. Anyone else needs "not Jo".
ONE_OF = {'mom', 'dad', 'stepmom', 'stepdad', 'boss'}
PETS = {'cat', 'dog', 'kitten', 'puppy', 'rabbit', 'bunny', 'parrot', 'hamster', 'turtle', 'tortoise', 'snake', 'fish',
        'lizard', 'ferret', 'horse'}
NOT = r"(?:don['’]?t|do not|didn['’]?t|did not|never)"
# (category, pattern, negated): group 1 is the relation or nothing, the last group the value.
USER_RULES = (
    ('kin', re.compile(rf"\byour {KIN}(?:['’]s name)? (?:is|was|'s|’s) (?:actually |really )?(?:called |named )?{NAME}",
                       re.IGNORECASE), False),
    ('kin', re.compile(rf"\byou {NOT} (?:even )?have an? {KIN}\b", re.IGNORECASE), True),
    ('siblings', re.compile(r"\byou(?:['’]re| are) an only child\b", re.IGNORECASE), True),
    ('works_at', re.compile(rf"\byou {NOT} work (?:at|for) (?:the )?{PLACE}", re.IGNORECASE), True),
    ('works_at', re.compile(rf"\byou work (?:at|for) (?:the )?{PLACE},? not\b", re.IGNORECASE), False),
    ('grew_up', re.compile(rf"\byou {NOT} grow up (?:in|on|near) {PLACE}", re.IGNORECASE), True),
    ('grew_up', re.compile(rf"\byou grew up (?:in|on|near) {PLACE},? not\b", re.IGNORECASE), False),
)
DEFINITION_RULES = (
    ('grew_up', re.compile(rf"\bgrew up (?:in|on|near|outside(?: of)?) {PLACE}", re.IGNORECASE)),
    ('grew_up', re.compile(rf"\b(?:born and raised|raised) in {PLACE}", re.IGNORECASE)),
    ('works_at', re.compile(rf"\bworks? (?:as an? [^.,;]{{1,40}}? )?(?:at|for) (?:the )?{PLACE}", re.IGNORECASE)),
)


def relation(word: str) -> str:
    word = word.lower()
    return SAME.get(word, word)


def same_place(left: str, right: str) -> bool:
    """"Mercy" and "Mercy Hospital" are one place; "Duluth" and "Duluth, Minnesota" too."""
    a, b = left.casefold().strip(' .,'), right.casefold().strip(' .,')
    return bool(a and b) and (a in b or b in a)


def disputed(rows: list[dict], sentence: str) -> list[dict]:
    """The facts in force that one sentence of the user's says are wrong."""
    found = []
    for category, pattern, negated in USER_RULES:
        for match in pattern.finditer(sentence):
            if category == 'siblings':
                found += [row for row in rows if row['category'] == 'person'
                          and row['subject'].split()[-1] in {'sister', 'brother'}]
            elif category == 'kin':
                kind = relation(match.group(1).split()[-1])
                family = [row for row in rows if row['category'] in {'person', 'pet'}
                          and relation(row['subject'].split()[-1]) == kind]
                if negated:
                    found += family
                else:
                    named = match.group(2).casefold()
                    found += [row for row in family if row['value'].casefold() != named and (
                        kind in ONE_OF or re.search(rf"\bnot {re.escape(row['value'])}\b", sentence, re.IGNORECASE))]
            else:
                value = match.groups()[-1]
                found += [row for row in rows if row['category'] == category
                          and (same_place(row['value'], value) if negated else not same_place(row['value'], value))]
    return found


def sentences(text: str) -> list[str]:
    plain = QUOTED.sub(' ', ACTIONS.sub(' ', text))
    return [part.strip() for part in SENTENCES.findall(plain) if part.strip() and not SKIP.search(part.strip())]


def heed(connection, message: dict, timestamp: str) -> list[str]:
    """A user message that says something the companion said about themselves is wrong: those facts wait as
    conflicts from now on. Returns their ids."""
    from companion.self_facts import in_force
    if message['role'] != 'user':
        return []
    rows = in_force(connection, message['timeline_id'])
    found = {row['id'] for sentence in sentences(message['text']) for row in disputed(rows, sentence)}
    for fact_id in sorted(found):
        connection.execute("UPDATE self_facts SET status='conflict', conflicts_with=?, decided_at=NULL WHERE id=?",
                           (f'{USER}{message["id"]}', fact_id))
    if found:
        from companion.self_facts import stamp_change
        stamp_change(connection, timestamp)
    return sorted(found)


def earlier_dispute(connection, timeline_id, key: str, value: str) -> str | None:
    """The user's correction of this same fact, when the companion says it again."""
    row = optional(connection, "SELECT self_facts.conflicts_with FROM self_facts JOIN messages ON "
                   "messages.id=self_facts.message_id WHERE self_facts.status IN ('conflict', 'rejected') "
                   "AND self_facts.conflicts_with LIKE 'user:%' AND self_facts.key=? AND lower(self_facts.value)=? "
                   'AND messages.timeline_id=? ORDER BY self_facts.created_at DESC LIMIT 1',
                   (key, value.casefold(), timeline_id))
    return row['conflicts_with'] if row else None


def stated(definition: dict) -> dict[str, list[str]]:
    """Where the definition says the companion grew up and works, from its prose and work blocks."""
    text = ' '.join(str(definition.get(key) or '') for key in ('identity', 'background', 'routine'))
    text += ' ' + ' '.join(f"works at {match.group(1)}." for block in definition.get('schedule') or []
                           if block.get('kind') == 'work'
                           for match in [re.search(rf"\bat {PLACE}", block.get('label') or '')] if match)
    found: dict[str, list[str]] = {}
    for category, pattern in DEFINITION_RULES:
        for match in pattern.finditer(text):
            found.setdefault(category, []).append(match.group(1))
    return found


def definition_clash(fact, definition: dict) -> str | None:
    """`definition:<place>` when the definition names where they grew up or work and this says elsewhere."""
    places = stated(definition).get(fact.category)
    if not places or any(same_place(place, fact.value) for place in places):
        return None
    return f'{DEFINITION}{places[0]}'


def reason(connection, conflicts_with: str | None) -> dict:
    """What a conflict is with, for Character Studio."""
    if not conflicts_with:
        return {}
    if conflicts_with.startswith(USER):
        message = optional(connection, 'SELECT text, redacted_at FROM messages WHERE id=?',
                           (conflicts_with.removeprefix(USER),))
        said = message['text'][:160] if message and not message['redacted_at'] else ''
        return {'user_said': said}
    if conflicts_with.startswith(DEFINITION):
        return {'definition_says': conflicts_with.removeprefix(DEFINITION)}
    return {}

