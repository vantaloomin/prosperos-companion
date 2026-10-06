"""Replies at the companion's pace (realism: people answer later, or briefly, when they are busy).

The companion decides, not the user: the app never says whether they are free. With the Life
setting `paced_replies` on (the default), a reply to a message sent while they are at work or out
is, by a seeded choice, one of: written now but shown later (8 to 45 minutes at work, 5 to 25 out,
never past the end of the block), a quick holding text now ("in a meeting, give me a bit") with the
full reply later as a message of its own, or a quick short note now instead of a real conversation.
The holding text stays in the conversation. If the user writes again before the full reply shows,
that reply is dropped unseen and the answer to the new message becomes the full reply, at the same
time, so it takes in everything they said meanwhile. Asleep, the reply shows
when they wake. A reply that shows at once also shows any earlier one still held, and a reply held
while an earlier one is waiting shows no sooner than it. What counts is the companion's precomputed
day (a holiday or a sick day is not work), else their routine. A held reply that shows while the app
is in the background is announced like a first message.
"""
import random
from datetime import timedelta

from companion.clock import parse, stamp
from companion.database import decode, many, optional
from companion.life import routine

# Off in tests unless a test turns it on, so replies arrive at once like they used to.
ACTIVE = True
DELAYS = {'work': (8, 45), 'social': (5, 25)}
SLEEP_CAP = timedelta(hours=10)
# How they answer while busy: later, a holding text then later, or a quick note now.
WAYS = (('later', 45), ('line', 25), ('quick', 30))
LINES = {'work': ('in a meeting, give me a bit', 'at work rn, will text you properly soon', 'brb, boss is here',
                  'one sec, swamped at work', "can't talk yet, give me a few"),
         'social': ('out rn, text you in a bit', "with friends, I'll reply properly soon", 'one sec!')}
QUICK = ('You are busy right now ({label}). Reply with a quick short note, one or two lines, not a real '
         'conversation; you can pick it up properly later. Do not explain your schedule at length.')
# What the model is told when it writes the full reply after a holding text.
FOLLOW_UP = ('Earlier you were busy and only sent them a quick text: "{line}". This is the proper reply you '
             'promised; write it now that you are free.')
CATCH_UP = ('Earlier you were busy and only sent them a quick text saying you would reply properly later. This is '
            'that proper reply: answer everything they have said since.')
NOT_HELD = {'held_until': None, 'held_line': None, 'instruction': None}


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


def busy_kind(block: dict) -> str | None:
    if block['kind'] in routine.RESTING:
        return 'sleep'
    if block.get('sick_day') or block.get('holiday'):
        return None
    return block['kind'] if block['kind'] in DELAYS else None


def hold(connection, companion, now, seed: str) -> dict:
    """{held_until, held_line, instruction} for a reply being written now. `held_line` is a holding text
    sent now, `instruction` what the model is told; all None when the reply is an ordinary one shown at once."""
    life = optional(connection, 'SELECT paced_replies FROM life_settings WHERE id=1')
    found = block_now(connection, companion, now) if ACTIVE and life and life['paced_replies'] else None
    kind = busy_kind(found[0]) if found else None
    if kind is None:
        return dict(NOT_HELD)
    block, ends_at = found
    if kind == 'sleep':
        return {**NOT_HELD, 'held_until': stamp(min(parse(ends_at), now + SLEEP_CAP))}
    rng = random.Random(f'pace:{seed}')
    way = rng.choices([name for name, _weight in WAYS], [weight for _name, weight in WAYS])[0]
    if way == 'quick':
        return {**NOT_HELD, 'instruction': QUICK.format(label=block['label'].lower() or kind)}
    until = stamp(min(parse(ends_at), now + timedelta(minutes=rng.randint(*DELAYS[kind]))))
    if way == 'line':
        line = rng.choice(LINES[kind])
        return {'held_until': until, 'held_line': line, 'instruction': FOLLOW_UP.format(line=line)}
    return {**NOT_HELD, 'held_until': until}


def take_over(connection, timeline_id, held: dict, timestamp: str) -> tuple[dict, list[str]]:
    """The user wrote again after a holding text, before the full reply showed: that reply was written
    without their new words, so it is dropped unseen and this one takes its place and shows when it would have."""
    rows = many(connection, "SELECT id, held_until FROM messages WHERE timeline_id=? AND role='companion' "
                'AND reply_to IS NULL AND held_until>? AND superseded_at IS NULL', (timeline_id, timestamp))
    if not rows:
        return held, []
    dropped = [row['id'] for row in rows]
    connection.execute(f"UPDATE messages SET superseded_at=?, active=0, held_until=NULL "
                       f"WHERE id IN ({', '.join('?' * len(dropped))})", (timestamp, *dropped))
    return {'held_until': max(row['held_until'] for row in rows), 'held_line': None, 'instruction': CATCH_UP}, dropped


def join(connection, timeline_id, held: dict, timestamp: str) -> dict:
    """Keep replies in order: one shown now shows any held before it; one held waits for those too."""
    waiting = optional(connection, 'SELECT MAX(held_until) AS until FROM messages WHERE timeline_id=? '
                       'AND held_until>?', (timeline_id, timestamp))
    latest = waiting['until'] if waiting else None
    if not latest:
        return held
    if held['held_until'] is None:
        connection.execute('UPDATE messages SET held_until=? WHERE timeline_id=? AND held_until>?',
                           (timestamp, timeline_id, timestamp))
        return held
    return {**held, 'held_until': max(held['held_until'], latest)}
