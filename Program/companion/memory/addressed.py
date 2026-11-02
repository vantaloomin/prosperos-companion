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
# The user's "you" in a message to the companion is the companion.
YOU = ((re.compile(r"\byours\b", re.IGNORECASE), "{name}'s"), (re.compile(r"\byour\b", re.IGNORECASE), "{name}'s"),
       (re.compile(r"\byou\b", re.IGNORECASE), '{name}'))


def first_name(companion) -> str:
    definition = ((companion or {}).get('version') or {}).get('definition') or {}
    return (definition.get('name') or '').strip().split(' ')[0]


def named(text: str, name: str, message: str) -> str:
    """The text with the companion called by name wherever the model called them something else."""
    if not name or not text:
        return text
    if not SAID.search(message):
        before = text
        text = ARTICLE.sub(name, text)
        text = BARE.sub(lambda match: f'{match[1]} {name}', text)
        text = OPENING.sub(name, text)
        if text != before:  # "afraid of the assistant as if it were dangerous": "it" was the assistant too
            text = IT.sub(lambda match: f'{name} {match[1]}', text)
    for pattern, replacement in YOU:
        text = pattern.sub(replacement.format(name=name), text)
    return text


def fields(subject: str, value: str, name: str, message: str) -> tuple[str, str]:
    return named(subject, name, message), named(value, name, message)


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
                companions[row['companion_id']] = first_name(by_id(connection, row['companion_id']))
            subject, value = fields(row['subject'], row['value'], companions[row['companion_id']], row['text'])
            if (subject, value) != (row['subject'], row['value']):
                rename(connection, row, subject, value)
                changed += 1
        if changed:
            bump_memory_revision(connection, database.now())
        return changed
