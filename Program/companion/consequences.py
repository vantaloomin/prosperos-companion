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
from datetime import date, timedelta
from functools import cache

from companion.clock import stamp
from companion.database import decode, encode, identifier, many, optional
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
    'restless': r'restless|adventurous|wanderlust|spontaneous|free[- ]spirited|thrill[- ]seek\w*',
    'homebody': r'homebody|home-loving|nester|cozy|cosy|settled|creature of habit',
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
           labels: list[str], day: str, timestamp: str, holders: dict | None = None, now=None) -> dict:
    """Work out the odds, roll and record the outcome once, with the marks it leaves on `holders`; a second call
    returns the recorded one."""
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
        "picked_by, created_at, names, holders) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'dice', ?, ?, ?)",
        (row_id, timeline_id, choice, subject, tables()[choice]['label'].format(**names), day, encode(options), picked,
         timestamp, encode(names), encode(holders or {})))
    if holders:
        leave_marks(connection, recorded(connection, subject, choice), holders, names, timestamp, now)
    return recorded(connection, subject, choice)


def view(row, connection=None) -> dict:
    found = {'id': row['id'], 'timeline_id': row['timeline_id'], 'choice': row['choice'], 'subject': row['subject'],
             'label': row['label'], 'decided_on': row['decided_on'], 'options': decode(row['options']),
             'picked': row['picked'], 'picked_by': row['picked_by']}
    if connection is not None:
        found['marks'] = marks_of(connection, row['id'])
    return found


def recorded(connection, subject: str, choice: str) -> dict | None:
    row = optional(connection, 'SELECT * FROM consequences WHERE subject=? AND choice=?', (subject, choice))
    return view(row, connection) if row else None


def by_id(connection, consequence_id: str) -> dict:
    row = optional(connection, 'SELECT * FROM consequences WHERE id=?', (consequence_id,))
    require(row is not None, 'That outcome is not in this workspace.', 404)
    return view(row, connection)


def change(connection, consequence_id: str, option: int, timestamp: str) -> dict:
    """The user picks how it went instead: the outcome keeps its odds, and says the user chose it."""
    found = by_id(connection, consequence_id)
    require(0 <= option < len(found['options']), 'Pick one of the ways it could have gone.', 422)
    connection.execute("UPDATE consequences SET picked=?, picked_by=?, changed_at=? WHERE id=?",
                       (option, 'dice' if option == found['picked'] and found['picked_by'] == 'dice' else 'user',
                        timestamp, consequence_id))
    return by_id(connection, consequence_id)


def redo(connection, consequence_id: str, option: int, now, since: date, holders=None, names=None) -> dict:
    """Change how it went and redo the marks it left, from `since` (the day it was changed). `holders` and `names`
    stand in for an outcome recorded before they were kept."""
    outcome = change(connection, consequence_id, option, stamp(now))
    row = optional(connection, 'SELECT names, holders FROM consequences WHERE id=?', (consequence_id,))
    clear_marks(connection, consequence_id)
    leave_marks(connection, outcome, decode(row['holders']) or holders or {}, decode(row['names']) or names or {},
                stamp(now), now, since=since)
    return by_id(connection, consequence_id)


def recent(connection, timeline_id: str, prefix: str, since: str) -> list[dict]:
    """Outcomes whose choice starts with `prefix`, decided on or after `since`, newest first."""
    rows = many(connection, 'SELECT * FROM consequences WHERE timeline_id=? AND choice LIKE ? AND decided_on>=? '
                'ORDER BY decided_on DESC, created_at DESC', (timeline_id, f'{prefix}%', since))
    return [view(row, connection) for row in rows]


def copy(connection, consequence_id: str, timeline_id: str, subject: str) -> str:
    """An outcome carried onto a new timeline (a fork) with its odds, who picked it and the marks it left on this
    timeline (ripples stay with the companions they reached). Returns the copy's id."""
    row = dict(optional(connection, 'SELECT * FROM consequences WHERE id=?', (consequence_id,)))
    old_timeline = row['timeline_id']
    row.update(id=identifier(), timeline_id=timeline_id, subject=subject)
    insert_row(connection, 'consequences', row)
    for mark in many(connection, 'SELECT * FROM marks WHERE consequence_id=? AND timeline_id=?',
                     (consequence_id, old_timeline)):
        insert_row(connection, 'marks', {**dict(mark), 'id': identifier(), 'timeline_id': timeline_id,
                                         'consequence_id': row['id']})
    return row['id']


def insert_row(connection, table: str, row: dict):
    connection.execute(f"INSERT INTO {table} ({', '.join(row)}) VALUES ({', '.join('?' for _ in row)})",  # noqa: S608
                       tuple(row.values()))


# Marks ----------------------------------------------------------------------------------------------
# An outcome can leave marks (the option's `marks` in the table): hidden state that tilts later odds for a while.
# `mood` and `money` add up per holder (readers `mood` and `money`); `avoid` keeps the holder away from someone
# (they are left out of company and gatherings). A mark with `ripple` also reaches the companions who feel Close
# or closer to the holder (memory/pairs.py: backstories, groups, Small world meetings), as a lighter mood mark.

RIPPLE_LEVEL = 4


def leave_marks(connection, outcome: dict, holders: dict, names: dict, timestamp: str, now=None,
                since: date | None = None):
    """Write the marks the picked option leaves, from the day it was decided or `since` when later (the day the
    user changed how it went). `holders` maps the table's `on` names (me, a, b) to keys."""
    option = tables()[outcome['choice']]['options'][outcome['picked']]
    start = max(date.fromisoformat(outcome['decided_on']), since or date.min)
    for mark in option.get('marks', ()):
        holder = holders.get(mark['on'])
        if holder is None:
            continue
        row = {'timeline_id': outcome['timeline_id'], 'consequence_id': outcome['id'], 'holder': holder,
               'kind': mark['kind'], 'amount': mark.get('amount', 0), 'about': holders.get(mark.get('about')),
               'note': mark['note'].format(**names), 'told': mark['told'].format(**names) if 'told' in mark else None,
               'starts_on': start.isoformat(),
               'ends_on': (start + timedelta(days=mark['days'])).isoformat()}
        add_mark(connection, row, timestamp)
        if mark.get('ripple') and now is not None:
            ripple(connection, row, timestamp, now)


def add_mark(connection, row: dict, timestamp: str, ripple_of=False):
    insert_row(connection, 'marks', {'id': identifier(), **row, 'ripple': int(ripple_of), 'created_at': timestamp})


def ripple(connection, row: dict, timestamp: str, now):
    """The mark reaches companions who feel close to its holder, on their own active timeline."""
    from companion.memory import pairs
    if not row['holder'].startswith('companion:'):
        return
    for other in many(connection, 'SELECT id, active_timeline_id FROM companions WHERE id!=? AND '
                      'active_version_id IS NOT NULL AND active_timeline_id IS NOT NULL',
                      (pairs.companion_id(row['holder']),)):
        key = pairs.companion_key(other['id'])
        if (pairs.closeness(connection, key, row['holder'], now) or 0) >= RIPPLE_LEVEL:
            add_mark(connection, {**row, 'timeline_id': other['active_timeline_id'], 'holder': key,
                                  'kind': 'mood', 'amount': (row['amount'] > 0) - (row['amount'] < 0),
                                  'about': row['holder'], 'told': None}, timestamp, ripple_of=True)


def clear_marks(connection, consequence_id: str):
    connection.execute('DELETE FROM marks WHERE consequence_id=?', (consequence_id,))


def marks_of(connection, consequence_id: str) -> list[dict]:
    """The marks an outcome left, for "Why it went this way": {kind, amount, note, until, ripple, holder}."""
    return [{'kind': row['kind'], 'amount': row['amount'], 'note': row['note'], 'until': row['ends_on'],
             'ripple': bool(row['ripple']), 'holder': row['holder'],
             'who': holder_name(connection, row['holder']) if row['ripple'] else None}
            for row in many(connection, 'SELECT * FROM marks WHERE consequence_id=? ORDER BY ripple, created_at',
                            (consequence_id,))]


def holder_name(connection, holder: str) -> str | None:
    from companion.characters import by_id as companion_by_id
    found = companion_by_id(connection, holder.removeprefix('companion:'))
    return found['version']['name'] if found else None


def active(connection, timeline_id: str, day: str, kind: str, holder: str | None = None) -> list[dict]:
    query = 'SELECT * FROM marks WHERE timeline_id=? AND kind=? AND starts_on<=? AND ends_on>?'
    values = (timeline_id, kind, day, day)
    if holder is not None:
        query, values = query + ' AND holder=?', (*values, holder)
    return many(connection, query, values)


def total(connection, timeline_id: str, holder: str, kind: str, day: str) -> int:
    return sum(row['amount'] for row in active(connection, timeline_id, day, kind, holder))


def avoided(connection, timeline_id: str, day: str) -> set[str]:
    """Who the companion on this timeline keeps away from on `day`."""
    return {row['about'] for row in active(connection, timeline_id, day, 'avoid') if row['about']}


def money_line(connection, timeline_id: str, holder: str, day: str) -> list[tuple[str, str]]:
    """A line for the chat context's money section when an outcome left money tighter or easier."""
    amount = total(connection, timeline_id, holder, 'money', day)
    if amount < 0:
        return [(f'marks:money:{day}', '- Money has felt tighter than usual lately.')]
    if amount > 0:
        return [(f'marks:money:{day}', '- You have a little more room in your budget lately.')]
    return []


def lately_lines(connection, timeline_id: str, holder: str, day: str) -> list[tuple[str, str]]:
    """How the companion is carrying something the user did, while its mark lasts, for the chat context."""
    return [(f"mark:{row['id']}", f"- {row['told']}") for row in active(connection, timeline_id, day, 'mood', holder)
            if row['told']]
