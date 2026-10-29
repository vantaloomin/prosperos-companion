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
from companion.world import decades

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
    'came-up-why': reasons('a leak under the sink needed fixing', 'a package had to be picked up', 'the phone screen cracked',
                           'a friend needed a favor', 'the laundry could not wait any longer',
                           'a bill turned out to be overdue'),
}
# Aboard a ship or station (companion/world/ships.py) there are no buses or traffic.
AFLOAT = {'missed the bus': 'missed the tram', 'traffic was a mess': 'the lifts were packed'}
# Before phones in every pocket (the 1920s on), and before buses, phones and plumbing (the older eras).
BEFORE_SCREENS = {'the phone screen cracked': 'a boot heel came off',
                  'the system went down right before the end': 'the ledgers would not balance right before the end'}
BEFORE_PHONES = BEFORE_SCREENS | {
    'missed the bus': 'the road was blocked', 'traffic was a mess': 'the streets were jammed with carts',
    'got stuck on a long phone call': 'got caught in a long conversation',
    'a leak under the sink needed fixing': 'the roof started leaking',
    'the reservation got lost': 'the innkeeper gave the table away'}
# A modern city's world in a past year from before phones had screens to crack (decades.py).
SCREENS_FROM = 2008
BEFORE_SMARTPHONES = {'the phone screen cracked': 'the car battery died'}
ERAS = {'jazz-age': BEFORE_SCREENS, **{era: BEFORE_PHONES for era in ('medieval', 'fantasy', 'frontier', 'victorian',
                                                                       'steampunk')}}
CHANGES = {'cancelled': {'kind': 'leisure', 'label': 'Quiet night in'},
           'came_up': {'kind': 'errand', 'label': 'Something came up'},
           'drop_by': {'kind': 'social', 'label': 'Company'}}


def enabled(connection) -> bool:
    row = optional(connection, 'SELECT day_shifts FROM life_settings WHERE id=1')
    return ACTIVE and bool(row and row['day_shifts'])


def roll(seed: str, block: dict, company=(), tilt: dict | None = None, aboard: bool = False,
         era: str = 'modern') -> dict | None:
    """The shift for one slot ({key, minutes, reason, friend, text}), or None for a day as planned. `tilt`
    multiplies rows' weights (see `tilts`); `aboard` a ship or station, or in a city of another `era`, the reasons
    fit it."""
    if block['kind'] not in TABLES or block.get('holiday') or block.get('sick_day'):
        return None
    draws = Draws(seed)
    tables = {**TABLES, block['kind']: tilted(TABLES[block['kind']], tilt)} if tilt else TABLES
    chain = resolve(tables, block['kind'], draws, 'shift')
    if not chain or (chain[0]['id'] == 'drop_by' and not company):
        return None
    key = chain[0]['id']
    low, high = MINUTES.get(key, (0, 0))
    minutes = low + draws.die(high - low + 1, 'shift', 'minutes') - 1 if key in MINUTES else 0
    friend = company[draws.die(len(company), 'shift', 'friend') - 1] if key == 'drop_by' else None
    reason = chain[1]['text'] if len(chain) > 1 else ''
    reason = AFLOAT.get(reason, reason) if aboard else ERAS.get(era, {}).get(reason, reason)
    if era == 'modern' and (decades.world_year() or SCREENS_FROM) < SCREENS_FROM:
        reason = BEFORE_SMARTPHONES.get(reason, reason)
    text = chain[0]['text'].format(minutes=minutes, reason=reason, friend=friend['name'] if friend else '')
    return {'key': key, 'minutes': minutes, 'reason': reason, 'friend': friend, 'text': text}


def tilted(rows: list[dict], factors: dict) -> list[dict]:
    """The rows with their weights multiplied by `factors` ({row id: factor}), as ranges on one die again."""
    result, low = [], 1
    for row in rows:
        weight = max(1, round((row['high'] - row['low'] + 1) * factors.get(row['id'], 1)))
        result.append({**row, 'low': low, 'high': low + weight - 1})
        low += weight
    return result


def tilts(connection, timeline_id: str, holder: str, day: str) -> dict:
    """How the marks earlier outcomes left tilt the day (companion/consequences.py): low spirits mean more quiet
    nights in; tight money means more plans falling through and more things coming up."""
    from companion import consequences
    factors = {}
    if consequences.total(connection, timeline_id, holder, 'mood', day) < 0:
        factors['cancelled'] = 1.5
    if consequences.total(connection, timeline_id, holder, 'money', day) < 0:
        factors['cancelled'] = factors.get('cancelled', 1) * 1.5
        factors['came_up'] = 1.3
    return factors


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
