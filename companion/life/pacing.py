"""Replies at the companion's pace (realism: people answer slower at work and not at all asleep).

With the Life setting `paced_replies` on, a reply to a message sent while the companion is at work
or asleep is still written at once, but held: at work it shows a short holding line ("in a meeting,
give me a bit") and the full reply after a seeded 8 to 45 minutes, never past the end of the work
block; asleep it shows when they wake. It is never a lockout: the user can show it at once, sending
another message shows it, and Stop, settings, pause and export work as always. What counts is the
companion's precomputed day (a holiday or a sick day is not work), else their routine.
"""
import random
from datetime import timedelta

from companion.clock import parse, stamp
from companion.database import decode, optional
from companion.life import routine

WORK_DELAY = (8, 45)
SLEEP_CAP = timedelta(hours=10)
HOLDING = ('in a meeting, give me a bit', 'at work rn, will text you properly soon', 'brb, boss is here',
           'one sec, swamped at work', "can't talk yet, give me a few")


def block_now(connection, companion, now) -> tuple[dict, str] | None:
    """(block, ends_at) the companion is in right now: the agenda's when it has one, else the routine's."""
    row = optional(connection, "SELECT block, ends_at FROM life_agenda WHERE timeline_id=? AND subject='companion' "
                   'AND starts_at<=? AND ends_at>? ORDER BY starts_at DESC LIMIT 1',
                   (companion['active_timeline_id'], stamp(now), stamp(now)))
    if row:
        return decode(row['block']), row['ends_at']
    version = companion['version']
    slot, _next = routine.current_and_next(routine.blocks(version['definition'])[0], version['timezone'], now)
    return (slot.block.view(), stamp(slot.ends_at)) if slot else None


def hold(connection, companion, now, seed: str) -> dict:
    """{held_until, held_line} for a reply being written now; both None when it shows at once."""
    life = optional(connection, 'SELECT paced_replies FROM life_settings WHERE id=1')
    found = block_now(connection, companion, now) if life and life['paced_replies'] else None
    if not found:
        return {'held_until': None, 'held_line': None}
    block, ends_at = found
    rng = random.Random(f'pace:{seed}')
    if block['kind'] == 'work' and not block.get('sick_day') and not block.get('holiday'):
        until = min(parse(ends_at), now + timedelta(minutes=rng.randint(*WORK_DELAY)))
        return {'held_until': stamp(until), 'held_line': rng.choice(HOLDING)}
    if block['kind'] in routine.RESTING:
        return {'held_until': stamp(min(parse(ends_at), now + SLEEP_CAP)), 'held_line': None}
    return {'held_until': None, 'held_line': None}


def release(connection, timeline_id, timestamp):
    """Sending another message, or asking to see it, shows any held reply now."""
    connection.execute('UPDATE messages SET held_until=? WHERE timeline_id=? AND held_until>?',
                       (timestamp, timeline_id, timestamp))
