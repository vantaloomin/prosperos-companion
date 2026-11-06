"""The companion by name in what the memory model saves from a message written to them (PRD M7).

A user's message speaks to the companion as "you", and the model reading it had no name for them, so it wrote one
of its own: "Trust in assistant: didn't feel afraid of the assistant as if it were dangerous" from a message to Sett.
Memories are the user's notes about their own life, where "you" is the user and the companion goes by their first
name (`records.as_told`), so the companion is named there: "Trust in Sett: didn't feel afraid of Sett".

A generic word is renamed only when the message itself never uses it: "my boss's assistant" stays an assistant.
"""
import json
import re

from companion.characters import by_id
from companion.database import bump_memory_revision, encode, many
from companion.memory import vectors
from companion.memory.extraction import subject_key

GENERIC = r"(?:AI\s+|virtual\s+|chat\s+)?(?:assistant|chat\s?bot|bot|AI|language\s+model|companion)"
# "the assistant", "your AI"; "in assistant", "with AI" (no article, as subjects are written); "Assistant's ...".
ARTICLE = re.compile(rf"\b(?:the|this|my|your|an?)\s+{GENERIC}\b", re.IGNORECASE)
BARE = re.compile(rf"\b(in|with|of|to|for|about|toward|towards|by|from|around|at)\s+{GENERIC}\b", re.IGNORECASE)
OPENING = re.compile(rf"^{GENERIC}\b", re.IGNORECASE)
SAID = re.compile(r"\b(?:assistant|chat\s?bot|bot|AI|language\s+model|companion)\b", re.IGNORECASE)
IT = re.compile(r"\bit (is|was|were|has|had|does|did|would|will|can|could)\b")
# The assistant's "it" as "they": "as if it were dangerous" -> "as if they were dangerous".
THEY = {'is': 'are', 'was': 'were', 'has': 'have', 'does': 'do'}
# The user's "you" in a message to the companion is the companion: "you're" -> "Sett is", "you make" -> "Sett makes".
YOUR = re.compile(r"\byour(s|self)?\b", re.IGNORECASE)
YOU = re.compile(r"\byou(?:['’](re|ve|ll|d))?\b(\s+(?:(?:never|always|also|just|really|still|often|usually|"
                 r"sometimes|actually|even)\s+)*)?([a-z']+)?", re.IGNORECASE)
CONTRACTED = {'re': 'is', 've': 'has', 'll': 'will', 'd': 'would'}
AGREES = {'are': 'is', 'were': 'was', 'have': 'has', 'do': 'does', "aren't": "isn't", "weren't": "wasn't",
          "haven't": "hasn't", "don't": "doesn't"}
# Words after a subject "you" that keep their form: modals, past tenses, words that are not verbs.
KEEP = {'can', 'could', 'will', 'would', 'should', 'might', 'must', 'may', "can't", "won't", "wouldn't", "couldn't",
        "shouldn't", "didn't", 'did', 'had', 'came', 'went', 'gave', 'made', 'took', 'saw', 'said', 'got', 'knew',
        'felt', 'left', 'brought', 'thought', 'told', 'kept', 'met', 'ran', 'sat', 'stood', 'bought', 'found',
        'held', 'heard', 'let', 'lost', 'meant', 'paid', 'put', 'read', 'sent', 'set', 'spent', 'taught', 'won',
        'wrote', 'drove', 'ate', 'drank', 'sang', 'began', 'became', 'chose', 'forgot', 'spoke', 'woke', 'wore',
        'understood', 'slept', 'caught', 'fought', 'built', 'lent', 'hid', 'rode', 'fell', 'flew', 'grew', 'threw',
        'drew', 'shook', 'broke', 'and', 'or', 'but', 'the', 'a', 'an', 'to', 'so', 'too', 'for', 'there', 'here',
        'all', 'both', 'more', 'guys', 'two', 'as', 'at', 'in', 'on', 'with', 'of', 'than', 'that', 'this', 'when',
        'if', 'because', 'about', 'around', 'again', 'today', 'tonight', 'now', 'back', 'up', 'out', 'me', 'my',
        'very', 'much', 'better', 'best', 'lots', 'less', 'most', 'anyway', 'either', 'enough', 'well', 'first',
        'ever'}
# "you'd been": "had", not "would", before a past participle.
PARTICIPLES = {'been', 'gone', 'had', 'done', 'seen'}
# What comes right before a "you" that is the subject: nothing, punctuation, or a word that opens a clause.
CLAUSE = {'and', 'but', 'or', 'that', 'because', 'when', 'if', 'so', 'how', 'why', 'what', 'since', 'while', 'as',
          'whenever', 'where', 'until', 'though', 'although', 'like', 'glad', 'love', 'think', 'know', 'before', 'after',
          'unless', 'once', 'till', 'then'}


def third_person(verb: str) -> str:
    """'make' -> 'makes', 'watch' -> 'watches', 'carry' -> 'carries'; a word that is not a base verb stays."""
    low = verb.casefold()
    if low in AGREES:
        return AGREES[low]
    if low in KEEP or low.endswith(('ed', 'ing', "n't")) or (low.endswith('s') and not low.endswith('ss')):
        return verb
    if low.endswith(('ss', 'sh', 'ch', 'x', 'z', 'o')):
        return f'{verb}es'
    if len(low) > 1 and low.endswith('y') and low[-2] not in 'aeiou':
        return f'{verb[:-1]}ies'
    return f'{verb}s'


def subject(text: str, start: int) -> bool:
    """Whether the "you" at start opens a clause (the subject), not an object ("with you", "thank you")."""
    words = re.findall(r"[\w']+|[^\w\s]", text[:start])
    return not words or not words[-1][0].isalnum() or words[-1].casefold() in CLAUSE


def you(match, text: str, name: str) -> str:
    contraction, gap, verb = match[1], match[2] or '', match[3] or ''
    if contraction:
        short = contraction.casefold()
        if short == 'd' and (verb.casefold() in PARTICIPLES or verb.casefold().endswith(('ed', 'en'))):
            short = 'had'
        return f'{name} {CONTRACTED.get(short, short)}{gap}{verb}'
    if verb and gap and subject(text, match.start()):
        return f'{name}{gap}{third_person(verb)}'
    return f'{name}{gap}{verb}'


def addressed_you(text: str, name: str) -> str:
    text = re.sub(r"\byou\s+yourself\b", 'you', text, flags=re.IGNORECASE)  # "you yourself said"
    text = YOUR.sub(lambda match: name if (match[1] or '').casefold() == 'self' else f"{name}'s", text)
    return YOU.sub(lambda match: you(match, text, name), text)


# Who did it, in a memory with two people in it: the model drops the user's "I" ("I won't text you first" gave "won't
# text tomorrow before you text first"), which reads fine under About you ("Lives in Baltimore") but not in a plan or
# about the two of them, so those say "You" (the user, as on Memories; `records.as_told` turns it to "The user").
VOICED = {'plan', 'relationship', 'shared_experience'}
SAID_I = re.compile(r"\bI(?:\s*['’]\s*(ll|m|ve|d))?\s+(?:(?:really|just|also|still|never|always|already|probably|"
                    r"definitely|actually|kinda|totally|honestly)\s+)*([\w'’]+)", re.IGNORECASE)
SAID_AUX = {'ll': 'will', 'm': 'am', 've': 'have', 'd': 'would'}
# A value opening on one of these has lost its subject: no noun phrase starts with "will" or "has".
AUXILIARIES = {'will', "won't", 'would', "wouldn't", 'can', "can't", 'could', "couldn't", 'should', "shouldn't",
               'must', 'might', 'has', 'have', "hasn't", "haven't", 'had', "hadn't", 'is', "isn't", 'am', 'was',
               "wasn't", 'does', "doesn't", 'did', "didn't", 'wants', 'needs', 'plans', 'promised', 'agreed',
               'decided', 'feels', 'felt', 'trusts', 'likes', 'loves', 'hates', 'misses', 'wishes', 'hopes'}
YOU_FORMS = {'is': 'are', 'am': 'are', 'was': 'were', 'has': 'have', 'does': 'do', "doesn't": "don't",
             "isn't": "aren't", "wasn't": "weren't", "hasn't": "haven't"}


def base_form(word: str) -> str:
    """'trusts' -> 'trust', 'misses' -> 'miss', 'carries' -> 'carry'; other words as they are."""
    low = word.casefold()
    if low in YOU_FORMS:
        return YOU_FORMS[low]
    if low.endswith('ies') and len(low) > 4:
        return f'{low[:-3]}y'
    if low.endswith(('sses', 'shes', 'ches', 'xes', 'zes', 'oes')):
        return low[:-2]
    if low.endswith('s') and not low.endswith(('ss', 'us', 'is')):
        return low[:-1]
    return low


def said_by_user(message: str) -> set[str]:
    """The words the user put after "I" in the message: "I'll delete" gives {"will", "delete"}."""
    found = set()
    for match in SAID_I.finditer(message):
        if match[1]:
            found.add(SAID_AUX[match[1].casefold()])
        found.add(match[2].casefold().replace('’', "'"))
    return found


def voiced(layer: str, value: str, message: str) -> str:
    """A plan or a moment the two of them share with the user's dropped "I" back as "You": "won't text tomorrow
    before Sett texts first" -> "You won't text tomorrow before Sett texts first"."""
    first, _, rest = value.partition(' ')
    word = first.casefold().replace('’', "'")
    if layer not in VOICED or not word:
        return value
    if word in {'you', "you're", "you've", "you'll", "you'd"}:
        return f'{first} {also(rest, message)}'.rstrip()
    said = said_by_user(message)
    if word not in AUXILIARIES and word not in said and base_form(word) not in said:
        return value
    return f"You {base_form(word)} {also(rest, message)}".rstrip()


# A second verb with no subject of its own after "You": "You like having Sett around and doesn't need gifts" ->
# "and don't need gifts". Only a verb the message itself has in the "you" form, so "and Sett is" stays.
ALSO = re.compile(r"((?:,|\band\b|\bbut\b)\s+(?:just\s+|still\s+|also\s+|always\s+)?)([a-z']+)")


def also(rest: str, message: str) -> str:
    words = {word.casefold().replace('’', "'") for word in re.findall(r"[\w'’]+", message)}

    def agree(match):
        verb = match[2]
        mine = base_form(verb)
        return f'{match[1]}{mine}' if mine != verb.casefold() and mine in words else match[0]
    return ALSO.sub(agree, rest)


# "not contact them" about Sett, who is he/him: "not contact him". Only when the companion is the one person named,
# since "them" may be someone else ("Mom" or "Jo").
SET_PRONOUNS = {'he': {'they': 'he', 'them': 'him', 'their': 'his', 'theirs': 'his', 'themselves': 'himself',
                       'themself': 'himself'},
                'she': {'they': 'she', 'them': 'her', 'their': 'her', 'theirs': 'hers', 'themselves': 'herself',
                        'themself': 'herself'}}
THEY_VERB = re.compile(r"\bthey(?:['’](re|ve|d|ll))?\b(\s+[a-z']+)?", re.IGNORECASE)
THEY_AGREES = {'are': 'is', 'were': 'was', 'have': 'has', 'do': 'does', "don't": "doesn't", "aren't": "isn't",
               "weren't": "wasn't", "haven't": "hasn't"}
THEY_SHORT = {'re': "'s", 've': "'s", 'd': "'d", 'll': "'ll"}
CAPITALISED = re.compile(r"(?<=\w\s)([A-Z][a-z'’]+)")


def only_them(text: str, name: str) -> bool:
    """Whether the companion is the one person the text names."""
    from companion.memory.owners import PEOPLE
    words = {word.casefold() for word in re.findall(r"[\w']+", text)}
    others = {word for word in CAPITALISED.findall(text) if word.split("'")[0] not in {name, 'I'}}
    return name in text and not others and not words & PEOPLE


def with_pronouns(text: str, name: str, pronoun: str) -> str:
    """They/them/their as the companion's own pronouns when the companion is the one person in the text."""
    forms = SET_PRONOUNS.get(pronoun)
    if not forms or not only_them(text, name):
        return text

    def they(match):
        short, verb = match[1], match[2] or ''
        if short:
            return f'{forms["they"]}{THEY_SHORT[short.casefold()]}{verb}'
        word = verb.strip()
        if not word:
            return forms['they']
        agreed = THEY_AGREES.get(word.casefold()) or third_person(word)
        return f'{forms["they"]}{verb[:len(verb) - len(word)]}{agreed}'
    text = THEY_VERB.sub(they, text)
    return re.sub(r"\b(them|their|theirs|themselves|themself)\b", lambda match: forms[match[1].casefold()], text,
                  flags=re.IGNORECASE)


# The user, in a memory found in their own message, is "you", as everywhere on Memories (memory-suggest-8 keeps the
# message's own "I", "me" and "my"). Older answers wrote "the user" ("helping the user feel comfortable") or a
# pronoun for them ("short replies from Sett make him wonder if Sett is mad at him", Vanta on 1.3.2).
THE_USER = re.compile(r"\bthe user(?:(['’]s)|(\s+[a-z']+))?", re.IGNORECASE)
I_SAID = re.compile(r"\b[Ii](?:['’](m|ve|ll|d)|(\s+(?:am|was)\b))?(?![\w.'’])")
I_FORMS = {'m': "you're", 've': "you've", 'll': "you'll", 'd': "you'd", 'am': 'you are', 'was': 'you were'}
MINE = {'me': 'you', 'my': 'your', 'mine': 'yours', 'myself': 'yourself'}
MINE_WORDS = re.compile(r"\b(me|my|mine|myself)\b", re.IGNORECASE)
THIRD = re.compile(r"\b(?:he|him|his|she|her|hers|they|them|their|theirs|himself|herself|themselves|themself)\b",
                   re.IGNORECASE)
USER_WORDS = re.compile(r"\b(?:i|me|my|mine|myself|you|your|yours|yourself|the user)\b", re.IGNORECASE)
# Object and possessive pronouns only: "won't text before they text first" may well be the companion.
STANDS_IN = re.compile(r"\b(him|them|her|his|their|himself|herself|themselves|themself)\b(\s+[\w'’]+)?",
                       re.IGNORECASE)
POSSESSIVE = {'his', 'their'}


def cased(found: str, word: str) -> str:
    return word[:1].upper() + word[1:] if found[:1].isupper() else word


def the_user(match, text: str) -> str:
    if match[1]:
        return cased(match[0], 'your')
    after = match[2] or ''
    word = after.strip()
    low = word.casefold()
    if word and subject(text, match.start()) and (low in YOU_FORMS or (low.endswith('s') and not low.endswith(
            ('ss', 'us', "'s")) and low not in KEEP)):
        word = base_form(word)
    return cased(match[0], f"you{after[:len(after) - len(after.lstrip())]}{word}")


def as_yours(text: str) -> str:
    """The user's own words about themselves as "you": "Mira makes me laugh" -> "Mira makes you laugh", "helping the
    user feel comfortable" -> "helping you feel comfortable"."""
    text = THE_USER.sub(lambda match: the_user(match, text), text)
    text = I_SAID.sub(lambda match: (cased if match.start() == 0 else lambda _found, word: word)(
        match[0], I_FORMS.get((match[1] or match[2] or '').strip().casefold(), 'you')), text)
    return MINE_WORDS.sub(lambda match: cased(match[0], MINE[match[1].casefold()]), text)


def stands_for_user(text: str, name: str, message: str) -> bool:
    """Whether a "him", "them" or "their" in the text is the user: the text names the companion and no one says
    "you" or "I" for the user, while the message speaks of "me" or "my" and of nobody else."""
    return bool(name and name in text and MINE_WORDS.search(message) and not THIRD.search(message)
                and not USER_WORDS.search(text))


def user_pronouns(text: str, message: str) -> str:
    """'make him wonder if Sett is mad at him' -> 'make you wonder if Sett is mad at you'. A possessive turns only
    when the message said "my" before the same word ("his sister" for "my sister")."""
    said = message.casefold().replace('’', "'")

    def turn(match):
        word, after = match[1].casefold(), match[2] or ''
        following = after.strip().casefold()
        mine = bool(following) and f'my {following}' in said
        if word.endswith(('self', 'selves')):
            return cased(match[0], 'yourself') + after
        if word in POSSESSIVE or (word == 'her' and mine):
            return cased(match[0], 'your') + after if mine else match[0]
        return cased(match[0], 'you') + after if re.search(r'\bme\b', said) else match[0]
    return STANDS_IN.sub(turn, text)


def yours(text: str, name: str, message: str) -> str:
    """The user as "you" in a memory found in their message, where the companion already goes by name."""
    if stands_for_user(text, name, message):
        text = user_pronouns(text, message)
    return as_yours(text)


def pronoun_of(companion) -> str:
    """He, she or they: the companion's pronouns as their description speaks of them."""
    from companion.world.looks import pronouns_of
    definition = ((companion or {}).get('version') or {}).get('definition') or {}
    return pronouns_of(definition).split('/')[0] if definition else 'they'


def first_name(companion) -> str:
    definition = ((companion or {}).get('version') or {}).get('definition') or {}
    return (definition.get('name') or '').strip().split(' ')[0]


def named(text: str, name: str, message: str, pronoun: str = 'they') -> str:
    """The text with the companion called by name wherever the model called them something else, and the user as
    "you"."""
    if not text:
        return text
    if not name:
        return as_yours(text)
    if not SAID.search(message):
        before = text
        text = ARTICLE.sub(name, text)
        text = BARE.sub(lambda match: f'{match[1]} {name}', text)
        text = OPENING.sub(name, text)
        if text != before:  # "afraid of the assistant as if it were dangerous": "it" was the assistant too
            text = IT.sub(lambda match: f"{pronoun} {THEY.get(match[1], match[1]) if pronoun == 'they' else match[1]}",
                          text)
    text = addressed_you(text, name)
    if stands_for_user(text, name, message):
        text = user_pronouns(text, message)  # "him" was the user; a "they" left is still the companion
    return as_yours(with_pronouns(text, name, pronoun))


def fields(subject: str, value: str, name: str, message: str, pronoun: str = 'they') -> tuple[str, str]:
    return named(subject, name, message, pronoun), named(value, name, message, pronoun)


# The prompts before memory-suggest-6, which saved answers as the model wrote them; each candidate is tidied once
# ("named" in its proposal), as "You will ..." must not turn into "Sett will ..." on the next pass.
OLD_PROMPTS = ('memory-suggest-1', 'memory-suggest-2', 'memory-suggest-3', 'memory-suggest-4', 'memory-suggest-5')
UNTIDIED = (f"memory_candidates.source='model' AND memory_candidates.rule IN ({', '.join('?' * len(OLD_PROMPTS))}) "
            "AND json_extract(memory_candidates.proposal, '$.named') IS NULL")


# Every model answer once more, after the companion is named, with the user as "you" (Vanta on 1.3.2: "short replies
# from Sett make him wonder if Sett is mad at him", "helping the user feel comfortable"); "yours" marks it done. A
# value the user already corrected is history and stays as it was.
UNYOURS = ("memory_candidates.source='model' AND json_extract(memory_candidates.proposal, '$.yours') IS NULL AND "
           "NOT EXISTS (SELECT 1 FROM memories AS was WHERE was.id=memory_candidates.memory_id AND "
           "was.status='superseded') AND "
           f"(memory_candidates.rule NOT IN ({', '.join('?' * len(OLD_PROMPTS))}) OR "
           "json_extract(memory_candidates.proposal, '$.named') IS NOT NULL)")


def older(connection, where=UNTIDIED) -> list[dict]:
    """Memories and waiting suggestions an older memory prompt found in the user's messages, with the companion."""
    memories = many(connection, 'SELECT memories.id, memories.subject, memories.value, memories.layer, '
                    'memories.companion_id, messages.text, memory_candidates.id AS candidate_id, '
                    "memory_candidates.proposal, 'memory' AS kind FROM memories "
                    'JOIN memory_candidates ON memory_candidates.memory_id=memories.id '
                    'JOIN messages ON messages.id=memory_candidates.message_id '
                    f"WHERE memories.origin='automatic' AND {where}", OLD_PROMPTS)
    waiting = many(connection, 'SELECT memory_candidates.id, memory_candidates.id AS candidate_id, '
                   'memory_candidates.proposal, memory_candidates.companion_id, messages.text, '
                   "'candidate' AS kind FROM memory_candidates "
                   'JOIN messages ON messages.id=memory_candidates.message_id '
                   f"WHERE memory_candidates.status='pending' AND {where}", OLD_PROMPTS)
    rows = [{**row, 'proposal': json.loads(row['proposal'])} for row in memories + waiting]
    return [row if row['kind'] == 'memory' else
            {**row, **{key: row['proposal'].get(key) or '' for key in ('subject', 'value', 'layer')}} for row in rows]


def rename(connection, row, subject, value, done='named'):
    proposal = {**row['proposal'], done: True}
    if row['kind'] == 'memory' and (subject, value) != (row['subject'], row['value']):
        connection.execute('UPDATE memories SET subject=?, subject_key=?, value=? WHERE id=?',
                           (subject, subject_key(subject), value, row['id']))
        vectors.forget(connection, 'memory', [row['id']])
    elif row['kind'] == 'candidate':
        proposal.update(subject=subject, subject_key=subject_key(subject), value=value)
    connection.execute('UPDATE memory_candidates SET proposal=? WHERE id=?', (encode(proposal), row['candidate_id']))


def tidy(database) -> int:
    """Older prompts' "Trust in assistant" saved from a message to Sett becomes "Trust in Sett", and "won't text
    first" becomes "You won't text first". Returns how many changed; each is tidied once."""
    with database.connect(write=True) as connection:
        companions, changed = {}, 0
        for row in older(connection):
            if row['companion_id'] not in companions:
                companion = by_id(connection, row['companion_id'])
                companions[row['companion_id']] = (first_name(companion), pronoun_of(companion))
            name, pronoun = companions[row['companion_id']]
            subject, value = fields(row['subject'], row['value'], name, row['text'], pronoun)
            value = voiced(row['layer'], value, row['text'])
            rename(connection, row, subject, value)
            changed += (subject, value) != (row['subject'], row['value'])
        if changed:
            bump_memory_revision(connection, database.now())
        return changed


def tidy_yours(database) -> int:
    """"short replies from Sett make him wonder if Sett is mad at him" becomes "... make you wonder if Sett is mad at
    you", and "helping the user feel comfortable" "helping you feel comfortable". Returns how many changed."""
    with database.connect(write=True) as connection:
        names, changed = {}, 0
        for row in older(connection, UNYOURS):
            if row['companion_id'] not in names:
                names[row['companion_id']] = first_name(by_id(connection, row['companion_id']))
            name = names[row['companion_id']]
            subject = yours(row['subject'], name, row['text'])
            value = voiced(row['layer'], yours(row['value'], name, row['text']), row['text'])
            rename(connection, row, subject, value, 'yours')
            changed += (subject, value) != (row['subject'], row['value'])
        if changed:
            bump_memory_revision(connection, database.now())
        return changed
