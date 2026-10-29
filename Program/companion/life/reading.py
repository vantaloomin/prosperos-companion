"""How long before they read a text while they are free (realism: nobody starts answering the moment a text lands).

Pacing (companion/life/pacing.py) holds replies while the companion is busy. When they are free, Settings > Realism >
"How quickly they read your texts" (`life_settings.read_pace`: 0 off, 1 quick, 2 natural, the default, 3 slow) holds
the reply a seeded little while before the model starts on it, shown only as "Delivered" like any held reply. A
companion's own "Quick to reply" (the definition's `texting.quick`) uses the quick pace whatever the setting, unless it
is off. Picking up the phone after a while takes longer than answering in a conversation that is going; now and then
they happen to have it in hand. Out and about takes longer than at home, and closer companions read a little sooner.

Texts in a row: while a reply waits to be read, the user can keep writing. Each new text drops the waiting reply,
which the model never started, and pushes the wait back by a short quiet spell, never past a cap counted from the
first unanswered text, so one reply answers them all. Nothing here asks the model; in person, on the phone or
out of character, replies start at once.
"""
import random
from datetime import timedelta

from companion.clock import parse, stamp
from companion.database import optional

# Off in tests unless a test turns it on, so replies arrive at once like they used to.
ACTIVE = True
QUICK, NATURAL = 1, 2
# Seconds before they read it, by pace: picking the phone up after a while, and in a conversation that is going.
PICK_UP = {1: (5, 20), 2: (20, 120), 3: (60, 300)}
GOING = {1: (2, 6), 2: (6, 25), 3: (15, 60)}
# A conversation is going while their last text came this recently.
GOING_FOR = timedelta(minutes=10)
# The chance a picked-up phone was already in their hand, so it reads like a conversation that is going.
IN_HAND = 0.2
# Another text pushes the wait back this many seconds, never past CAP seconds from the first unanswered text.
QUIET = {1: 8, 2: 20, 3: 30}
CAP = {1: 45, 2: 180, 3: 420}
# Out and about (anything but free time at home) reads slower; closeness 1 to 5 reads up to a fifth sooner.
AT_HOME = {'leisure', 'home', 'rest'}
AWAY = 1.5
CLOSER = 0.05
# How often a reply waiting to be read checks the time (seconds of real time).
POLL_SECONDS = 0.5
# What the model is told when it answers several texts at once.
SEVERAL = ('They sent you several texts in a row before you read them. Answer them together in one reply, not just '
           'the last one: take up each text. If one seems to answer something you never said, ask what they mean.')


def pace(connection, companion) -> int:
    """0 off to 3 slow: the world's setting, or quick for a companion who is quick to reply."""
    row = optional(connection, 'SELECT read_pace FROM life_settings WHERE id=1')
    setting = NATURAL if row is None else int(row['read_pace'])
    quick = ((companion['version']['definition'].get('texting') or {}).get('quick'))
    return min(setting, QUICK) if quick else setting


def reads_later(connection, companion) -> bool:
    """Whether a reply to a text may wait to be read at all, checked before anything costlier."""
    return ACTIVE and pace(connection, companion) > 0


def first_wait(connection, companion, now, seed: str, setting: int) -> float:
    """Seconds before they read a text when no reply is waiting to be read."""
    rng = random.Random(f'read:{seed}')
    last = optional(connection, "SELECT MAX(created_at) AS at FROM messages WHERE timeline_id=? AND role='companion' "
                    'AND superseded_at IS NULL', (companion['active_timeline_id'],))
    going = bool(last and last['at'] and parse(last['at']) > now - GOING_FOR) or rng.random() < IN_HAND
    seconds = rng.uniform(*(GOING if going else PICK_UP)[setting])
    from companion.life import pacing
    found = pacing.block_now(connection, companion, now)
    if found and found[0]['kind'] not in AT_HOME:
        seconds *= AWAY
    from companion.memory import closeness
    return seconds * (1 - CLOSER * (closeness.state(connection, companion, now)['level'] - 1))


def wait(connection, companion, now, seed: str, waiting: list[dict]) -> dict | None:
    """{held_until, instruction} for a reply to be read later, or None to start it at once. `waiting` are the
    replies still waiting to be read in this chat ({held_until, since}); the caller drops them."""
    setting = pace(connection, companion) if ACTIVE else 0
    if not setting:
        return None
    if not waiting:
        return {'held_until': stamp(now + timedelta(seconds=first_wait(connection, companion, now, seed, setting))),
                'instruction': None, 'since': stamp(now)}
    since = min(item['since'] for item in waiting)
    until = max([parse(item['held_until']) for item in waiting] + [now + timedelta(seconds=QUIET[setting])])
    until = min(until, parse(since) + timedelta(seconds=CAP[setting]))
    return {'held_until': stamp(max(until, now)), 'instruction': SEVERAL, 'since': since}
