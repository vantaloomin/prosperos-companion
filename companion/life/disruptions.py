"""Days that do not go to plan (realism: nobody's schedule is perfectly mapped out).

When a slot is written to the agenda, a seeded roll on the tables below can shift it: running late
(the slot starts later and the one before, often sleep, runs on), staying late (the slot ends later
and the next one starts later), plans falling through (a night out becomes a night in), something
coming up (free time goes to an errand) or a friend dropping by (free time becomes company, with a
circle member who is free). Most rolls are no event. The dice and tables come from Prospero's Study
(companion/life/chance.py), so the same slot always shifts the same way; no model is involved, and
the shift's wording is fixed text the model only phrases from.

The Life setting `day_shifts` (on by default) turns it off for new slots.
"""
from datetime import timedelta

from companion.clock import parse, stamp
from companion.database import decode, many, optional
from companion.life.chance import Draws, resolve

# Off in tests unless a test turns it on, so schedules stay as written.
ACTIVE = True
MIN_LEFT = timedelta(minutes=15)
MINUTES = {'late': (10, 45), 'over': (15, 60)}


def table(*rows) -> list[dict]:
    """Rows from (id, weight, child, text): consecutive ranges on one die, like Study's tables."""
    result, low = [], 1
    for row_id, weight, child, text in rows:
        result.append({'id': row_id, 'low': low, 'high': low + weight - 1, 'kind': 'no_event' if row_id == 'none'
                       else 'event', 'child': child, 'text': text})
        low += weight
    return result


def reasons(*texts) -> list[dict]:
    return table(*((f'reason-{index}', 1, None, text) for index, text in enumerate(texts)))


WORKING = (('none', 84, None, ''), ('late', 9, 'late-why', 'ran {minutes} minutes late ({reason})'),
           ('over', 7, 'over-why', 'stayed {minutes} minutes late ({reason})'))
TABLES = {
    'work': table(*WORKING),
    'study': table(*WORKING),
    'social': table(('none', 76, None, ''), ('late', 8, 'late-why', 'ran {minutes} minutes late ({reason})'),
                    ('cancelled', 11, 'cancel-why', 'had plans fall through ({reason}), so it was a quiet night in'),
                    ('came_up', 5, 'came-up-why', 'had something come up ({reason})')),
    'leisure': table(('none', 84, None, ''), ('came_up', 7, 'came-up-why', 'had something come up ({reason})'),
                     ('drop_by', 9, None, 'had {friend} drop by unannounced')),
    'late-why': reasons('overslept', 'missed the bus', "couldn't find the keys", 'traffic was a mess',
                        'spilled coffee and had to change', 'got stuck on a long phone call'),
    'over-why': reasons('a meeting ran long', 'a last-minute request landed', 'helping a coworker with a problem',
                        'a deadline moved up', 'the system went down right before the end'),
    'cancel-why': reasons('a friend cancelled last minute', 'the reservation got lost', 'everyone was too tired',
                          'the place was unexpectedly closed', 'the plan never quite came together'),
    'came-up-why': reasons('a leaky tap needed fixing', 'a package had to be picked up', 'the phone screen cracked',
                           'a friend needed a favor', 'the laundry could not wait any longer',
                           'a bill turned out to be overdue'),
}
CHANGES = {'cancelled': {'kind': 'leisure', 'label': 'Quiet night in'},
           'came_up': {'kind': 'errand', 'label': 'Something came up'},
           'drop_by': {'kind': 'social', 'label': 'Company'}}


def enabled(connection) -> bool:
    row = optional(connection, 'SELECT day_shifts FROM life_settings WHERE id=1')
    return ACTIVE and bool(row and row['day_shifts'])


def roll(seed: str, block: dict, company=()) -> dict | None:
    """The shift for one slot ({key, minutes, reason, friend, text}), or None for a day as planned."""
    if block['kind'] not in TABLES or block.get('holiday') or block.get('sick_day'):
        return None
    draws = Draws(seed)
    chain = resolve(TABLES, block['kind'], draws, 'shift')
    if not chain or (chain[0]['id'] == 'drop_by' and not company):
        return None
    key = chain[0]['id']
    low, high = MINUTES.get(key, (0, 0))
    minutes = low + draws.die(high - low + 1, 'shift', 'minutes') - 1 if key in MINUTES else 0
    friend = company[draws.die(len(company), 'shift', 'friend') - 1] if key == 'drop_by' else None
    reason = chain[1]['text'] if len(chain) > 1 else ''
    text = chain[0]['text'].format(minutes=minutes, reason=reason, friend=friend['name'] if friend else '')
    return {'key': key, 'minutes': minutes, 'reason': reason, 'friend': friend, 'text': text}


def shifted(block: dict, shift: dict | None) -> dict:
    """The block as it turned out; a changed one keeps what was planned."""
    if not shift:
        return block
    change = CHANGES.get(shift['key'], {})
    if shift['key'] == 'drop_by':
        change = {**change, 'label': f"{shift['friend']['name']} dropped by"}
    return {**block, **change, 'shift': shift, **({'planned': block['label']} if change else {})}


def place(connection, timeline_id, subject, starts_at, ends_at, shift: dict | None):
    """(starts_at, ends_at, shift) after the shift and any overrun from the slot before. Running late
    moves this start and stretches the slot that ended there; a slot that ran over pushes this one."""
    latest = ends_at - MIN_LEFT
    before = optional(connection, 'SELECT ends_at FROM life_agenda WHERE timeline_id=? AND subject=? AND starts_at<? '
                      'AND ends_at>? ORDER BY starts_at DESC LIMIT 1', (timeline_id, subject, stamp(starts_at),
                                                                       stamp(starts_at)))
    if before:
        starts_at = max(starts_at, min(parse(before['ends_at']), latest))
        shift = None if shift and shift['key'] == 'late' else shift
    elif shift and shift['key'] == 'late':
        moved = min(starts_at + timedelta(minutes=shift['minutes']), latest)
        connection.execute('UPDATE life_agenda SET ends_at=? WHERE timeline_id=? AND subject=? AND ends_at=?',
                           (stamp(moved), timeline_id, subject, stamp(starts_at)))
        starts_at = moved
    if shift and shift['key'] == 'over':
        ends_at += timedelta(minutes=shift['minutes'])
    return starts_at, ends_at, shift


def entry_with(entry: dict | None, shift: dict | None, name: str) -> dict | None:
    """The composed entry with the shift told first, so the day's account says what changed."""
    if not entry or not shift:
        return entry
    summary = f"{name} {shift['text']}. {entry['summary']}"
    return {**entry, 'summary': summary, 'shift': shift['key'], 'with': entry.get('with') or shift['friend']}


def context_lines(connection, timeline_id, subject, local_date, now) -> list[tuple[str, str]]:
    """Today's shifts so far, for the chat context: the companion knows why they were late."""
    rows = many(connection, 'SELECT id, block FROM life_agenda WHERE timeline_id=? AND subject=? AND local_date=? '
                'AND starts_at<=? ORDER BY starts_at', (timeline_id, subject, local_date, stamp(now)))
    lines = []
    for row in rows:
        block = decode(row['block'])
        if shift := block.get('shift'):
            planned = block.get('planned') or block['label']
            lines.append((row['id'], f"- Today, {planned.lower()}: you {shift['text']}."))
    return lines
