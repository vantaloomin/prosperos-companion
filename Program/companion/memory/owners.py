"""Whose fact a model-found memory is, checked against the message it came from (PRD M7).

A model answer whose subject belongs to someone ("Mom's home", "Jo's job") is kept only when the message
shows that someone is a person or pet in the user's life: a relation word, a name the app already knows,
"my dog", a capitalised name mid-sentence, or a name opening a sentence about one person ("Jo works at the
library"). Small talk about the world ("bats eat mosquitoes and flies, they live in the attic") turned the
common noun "bats" into "Bats' diet" and "Bats' home": a plural noun has no "my", is not capitalised
mid-sentence and takes a plural verb ("Bats eat"), so it fails every check.
"""
import re

from companion.memory import people_rules

POSSESSIVE = re.compile(r"^(?P<owner>[^'’]+?)['’]s?\s+\S")
LEADING = re.compile(r'^(?:my|your|our|the|user)\s+', re.IGNORECASE)
USER = {'user', "user's", 'me', 'my', 'i', 'mine', 'your', 'you'}
PEOPLE = {word for word in people_rules.SINGLE + people_rules.NAMED_ONLY} | {
    'mom', 'mum', 'parents', 'kids', 'children', 'siblings', 'grandparents', 'in-laws', 'family', 'folks', 'friends',
    'cousins', 'sisters', 'brothers', 'sons', 'daughters', 'neighbours', 'neighbors', 'coworkers', 'colleagues', 'aunt',
    'uncle', 'baby', 'child', 'kid', 'stepson', 'stepdaughter', 'godson', 'goddaughter', 'grandson', 'granddaughter'}
# What a sentence about one person says next: "Jo works", "Jo is", "Jo's", "Jo just got".
SINGULAR = re.compile(r"^(?:(?:just|also|really|still|finally|never|always|now|recently|actually|usually)\s+)?"
                      r"(?:is|was|has|does|doesn't|isn't|wasn't|hasn't|(?!\w*ss\b)\w+s\b)|^['’]s\b", re.IGNORECASE)
SENTENCE_START = re.compile(r'(?:^|[.!?\n]["”’)]*\s*)$')
# Plurals without an s, which would otherwise pass as a name opening a sentence ("Mice nest in the shed").
PLURALS = {'people', 'mice', 'geese', 'sheep', 'deer', 'fish', 'men', 'women', 'feet', 'teeth', 'wolves', 'oxen',
           'cattle', 'police', 'lice', 'moose', 'salmon', 'trout', 'bison', 'elk', 'swine', 'fungi', 'cacti'}


def owner(subject: str) -> str | None:
    """Whose fact a subject names, or None when it is the user's own ("Hobby", "Work")."""
    match = POSSESSIVE.match(subject.strip())
    if not match:
        return None
    who = LEADING.sub('', match['owner'].strip())
    return None if who.casefold() in USER else who


def stated_as_someone(word: str, text: str) -> bool:
    """Whether the message uses the word as someone in the user's life rather than a kind of thing."""
    escaped = re.escape(word)
    if re.search(rf"\b(?:my|our)\s+(?:[\w-]+\s+)?{escaped}\b", text, re.IGNORECASE):
        return True
    if not word[:1].isupper():
        return False
    for match in re.finditer(rf"(?<![\w'’]){escaped}(?![\w-])", text):
        if not SENTENCE_START.search(text[:match.start()]) or SINGULAR.match(text[match.end():].lstrip(' ,')):
            return True
        # A name opening a sentence: a plural like "Bats" or "Owls" needs a verb that says it is one ("Bats eat").
        if not word.casefold().endswith('s') and word.casefold() not in PLURALS:
            return True
    return False


def belongs(subject: str, text: str, names=()) -> bool:
    """Whether a model answer's subject is the user's own or someone the message shows is in their life."""
    who = owner(subject)
    if who is None:
        return True
    known = {name.casefold() for name in names if name}
    words = re.findall(r"[\w-]+", who)
    if who.casefold() in known or any(word.casefold() in known or word.casefold() in PEOPLE for word in words):
        return True
    return any(stated_as_someone(word, text) for word in words)
