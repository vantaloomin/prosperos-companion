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
          'whenever', 'where', 'until', 'though', 'although', 'like', 'glad', 'love', 'how', 'think', 'know'}


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


def pronoun_of(companion) -> str:
    """He, she or they: the companion's pronouns as their description speaks of them."""
    from companion.world.looks import pronouns_of
    definition = ((companion or {}).get('version') or {}).get('definition') or {}
    return pronouns_of(definition).split('/')[0] if definition else 'they'


def first_name(companion) -> str:
    definition = ((companion or {}).get('version') or {}).get('definition') or {}
    return (definition.get('name') or '').strip().split(' ')[0]


def named(text: str, name: str, message: str, pronoun: str = 'they') -> str:
    """The text with the companion called by name wherever the model called them something else."""
    if not name or not text:
        return text
    if not SAID.search(message):
        before = text
        text = ARTICLE.sub(name, text)
        text = BARE.sub(lambda match: f'{match[1]} {name}', text)
        text = OPENING.sub(name, text)
        if text != before:  # "afraid of the assistant as if it were dangerous": "it" was the assistant too
            text = IT.sub(lambda match: f"{pronoun} {THEY.get(match[1], match[1]) if pronoun == 'they' else match[1]}",
                          text)
    return addressed_you(text, name)


def fields(subject: str, value: str, name: str, message: str, pronoun: str = 'they') -> tuple[str, str]:
    return named(subject, name, message, pronoun), named(value, name, message, pronoun)


def older(connection, version: str) -> list[dict]:
    """Memories and waiting suggestions an older memory prompt found in the user's messages, with the companion."""
    memories = many(connection, 'SELECT memories.id, memories.subject, memories.value, memories.companion_id, '
                    "messages.text, 'memory' AS kind FROM memories "
                    'JOIN memory_candidates ON memory_candidates.memory_id=memories.id '
                    'JOIN messages ON messages.id=memory_candidates.message_id '
                    "WHERE memories.origin='automatic' AND memory_candidates.source='model' "
                    'AND memory_candidates.rule<>?', (version,))
    waiting = many(connection, "SELECT memory_candidates.id, memory_candidates.proposal, "
                   "memory_candidates.companion_id, messages.text, 'candidate' AS kind FROM memory_candidates "
                   'JOIN messages ON messages.id=memory_candidates.message_id '
                   "WHERE memory_candidates.source='model' AND memory_candidates.status='pending' "
                   'AND memory_candidates.rule<>?', (version,))
    return memories + [{**row, **{key: json.loads(row['proposal']).get(key) or '' for key in ('subject', 'value')}}
                       for row in waiting]


def rename(connection, row, subject, value):
    if row['kind'] == 'memory':
        connection.execute('UPDATE memories SET subject=?, subject_key=?, value=? WHERE id=?',
                           (subject, subject_key(subject), value, row['id']))
        vectors.forget(connection, 'memory', [row['id']])
        return
    proposal = json.loads(row['proposal'])
    proposal.update(subject=subject, subject_key=subject_key(subject), value=value)
    connection.execute('UPDATE memory_candidates SET proposal=? WHERE id=?', (encode(proposal), row['id']))


def tidy(database, version: str) -> int:
    """Older prompts' "Trust in assistant" saved from a message to Sett becomes "Trust in Sett". Returns how many
    changed; a renamed one never matches again, so this runs once in effect."""
    with database.connect(write=True) as connection:
        companions, changed = {}, 0
        for row in older(connection, version):
            if row['companion_id'] not in companions:
                companion = by_id(connection, row['companion_id'])
                companions[row['companion_id']] = (first_name(companion), pronoun_of(companion))
            name, pronoun = companions[row['companion_id']]
            subject, value = fields(row['subject'], row['value'], name, row['text'], pronoun)
            if (subject, value) != (row['subject'], row['value']):
                rename(connection, row, subject, value)
                changed += 1
        if changed:
            bump_memory_revision(connection, database.now())
        return changed
