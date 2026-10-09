"""The consequence engine: how a choice in the world turns out, from everything the app knows (2026-10-09).

Some things in the world have more than one way to go: whether two feuding friends make up, whether the
companion gets the promotion. Before, a blind coin flip picked when the storyline started. Now, when the
day comes, the engine reads the state that bears on it (how close the people are, how they know each other,
the companion's own description, the drama level), turns it into odds from a small table per choice
(world/data/consequences.json), rolls seeded dice against those odds and records the outcome with its odds
and reasons. Today shows them under "Why it went this way", and the user can change how it went.

No model decides anything and the model never sees the odds: the companion only hears what happened. Emotional
reactions come only from traits written into a character; the readers here look at words the user wrote.
Odds come from the tables alone, so the same world and seed always give the same result.
"""
import json
import random
import re
from functools import cache

from companion.database import decode, encode, identifier, optional
from companion.errors import require
from companion.world import catalog

# Words in the companion's own description that the tables' `sheet` rules look for.
WORDS = {
    'driven': r'driven|ambitious|hard[- ]working|workaholic|go-getter|career[- ]focused',
    'unfocused': r'lazy|procrastinat\w*|disorganized|scatterbrained|easily distracted|unmotivated',
    'assertive': r'assertive|blunt|outspoken|direct|confident|no-nonsense|fearless',
    'shy': r'shy|timid|introvert\w*|conflict[- ]avoidant|avoids conflict|quiet',
    'forgiving': r'forgiving|easygoing|easy-going|laid[- ]back|kind-hearted|peacemaker',
    'stubborn': r'stubborn|proud|grudges?|hot[- ]headed|short temper|temper|unforgiving',
}
SHEET_FIELDS = ('identity', 'personality', 'voice', 'background', 'flaws')
NEGATED = re.compile(r"\b(?:not|never|isn't|hardly|no)\s+(?:\w+\s+)?$", re.IGNORECASE)


@cache
def tables() -> dict:
    return json.loads((catalog.DATA / 'consequences.json').read_text(encoding='utf-8'))['choices']


def has_choice(choice: str) -> bool:
    return choice in tables()


# Reading the state ----------------------------------------------------------------------------------

def sheet_text(definition: dict) -> str:
    parts = []
    for field in SHEET_FIELDS:
        value = definition.get(field) or ''
        parts.append(' '.join(value) if isinstance(value, list) else value)
    return ' '.join(parts)


def sheet_has(definition: dict, group: str) -> bool:
    """Whether the companion's own description says this about them, not negated ("not shy")."""
    text = sheet_text(definition)
    for found in re.finditer(rf"\b(?:{WORDS[group]})\b", text, re.IGNORECASE):
        if not NEGATED.search(text[:found.start()]):
            return True
    return False


def matches(rule: dict, facts: dict) -> bool:
    if rule['reader'] == 'sheet':
        return rule['has'] in facts.get('sheet', ())
    value = facts.get(rule['reader'])
    if value is None:
        return False
    if 'is' in rule:
        return value == rule['is']
    return ('at_least' not in rule or value >= rule['at_least']) and ('at_most' not in rule or value <= rule['at_most'])


def odds(choice: str, facts: dict, names: dict) -> list[dict]:
    """Each option's odds (0 to 1, summing to 1) with the reasons that moved it: [{option, odds, reasons}]."""
    weights, reasons = [], []
    for option in tables()[choice]['options']:
        weight, why = option['weight'], []
        for rule in option.get('rules', ()):
            if matches(rule, facts):
                weight *= rule['times']
                why.append(rule['why'].format(**names))
        weights.append(weight)
        reasons.append(why)
    total = sum(weights) or 1
    return [{'option': index, 'odds': round(weight / total, 3), 'reasons': why}
            for index, (weight, why) in enumerate(zip(weights, reasons, strict=True))]


def roll(seed: str, found: list[dict]) -> int:
    """The option the seeded dice land on, using the odds as they are."""
    point, running = random.Random(f'consequence:{seed}').random(), 0.0
    for item in found:
        running += item['odds']
        if point < running:
            return item['option']
    return found[-1]['option']


# Recording outcomes ---------------------------------------------------------------------------------

def decide(connection, *, timeline_id: str, choice: str, subject: str, facts: dict, names: dict,
           labels: list[str], day: str, timestamp: str) -> dict:
    """Work out the odds, roll and record the outcome once; a second call returns the recorded one."""
    found = recorded(connection, subject, choice)
    if found:
        return found
    options = odds(choice, facts, names)
    picked = roll(f'{timeline_id}:{subject}:{choice}', options)
    for item, label in zip(options, labels, strict=True):
        item['label'] = label
    row_id = identifier()
    connection.execute(
        'INSERT INTO consequences (id, timeline_id, choice, subject, label, decided_on, options, picked, '
        "picked_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'dice', ?)",
        (row_id, timeline_id, choice, subject, tables()[choice]['label'].format(**names), day, encode(options), picked,
         timestamp))
    return recorded(connection, subject, choice)


def view(row) -> dict:
    return {'id': row['id'], 'timeline_id': row['timeline_id'], 'choice': row['choice'], 'subject': row['subject'], 'label': row['label'],
            'decided_on': row['decided_on'], 'options': decode(row['options']), 'picked': row['picked'],
            'picked_by': row['picked_by']}


def recorded(connection, subject: str, choice: str) -> dict | None:
    row = optional(connection, 'SELECT * FROM consequences WHERE subject=? AND choice=?', (subject, choice))
    return view(row) if row else None


def by_id(connection, consequence_id: str) -> dict:
    row = optional(connection, 'SELECT * FROM consequences WHERE id=?', (consequence_id,))
    require(row is not None, 'That outcome is not in this workspace.', 404)
    return view(row)


def change(connection, consequence_id: str, option: int, timestamp: str) -> dict:
    """The user picks how it went instead: the outcome keeps its odds, and says the user chose it."""
    found = by_id(connection, consequence_id)
    require(0 <= option < len(found['options']), 'Pick one of the ways it could have gone.', 422)
    connection.execute("UPDATE consequences SET picked=?, picked_by=?, changed_at=? WHERE id=?",
                       (option, 'dice' if option == found['picked'] and found['picked_by'] == 'dice' else 'user',
                        timestamp, consequence_id))
    return by_id(connection, consequence_id)


def copy(connection, consequence_id: str, timeline_id: str, subject: str) -> str:
    """An outcome carried onto a new timeline (a fork) with its odds and who picked it. Returns the copy's id."""
    row = dict(optional(connection, 'SELECT * FROM consequences WHERE id=?', (consequence_id,)))
    row.update(id=identifier(), timeline_id=timeline_id, subject=subject)
    connection.execute(f"INSERT INTO consequences ({', '.join(row)}) VALUES ({', '.join('?' for _ in row)})",
                       tuple(row.values()))
    return row['id']
