"""Observer mode (Feature Hit List #49, v0.16 "Such Stuff as Dreams"): just watch.

"Just watch" is a switch on any world (on Worlds, or "Watch a city" when making a new one). While it is on, the user's
persona sits out: nobody texts them first (companion/life/openers.py, companion/group_openers.py), no big day weighs
asking them along (companion/life/big_days.py), Matchlight waits (companion/dating.py), and a long silence leaves nobody
upset when they come back (companion/life/mood.py). Everyone else's lives go on at their usual pace: real time, with
Debug time for going faster (Vanta, 2026-10-20).

The Watching page follows one person at a time, the focus, whose day companion/life/narrator.py tells. The app picks
the first one (the companion the user talks to most, else a lively townsperson) and the user switches whenever they
like. Writing to anyone, or "Step in", turns watching off and picks up where things are.

The switch is kept in the world's own database (`observer`), so it stays with that world rather than following the
user into the next one.
"""
from companion.database import optional

WATCHING = 'SELECT * FROM observer WHERE id=1'
DEFAULT = {'watching': 0, 'focus': '', 'started_at': None, 'ended_at': None}


def row(connection) -> dict:
    found = optional(connection, WATCHING)
    return dict(found) if found else dict(DEFAULT)


def watching(connection) -> bool:
    return bool(row(connection)['watching'])


def save(connection, timestamp: str, **changes):
    current = {**row(connection), **changes, 'updated_at': timestamp}
    connection.execute('INSERT OR REPLACE INTO observer (id, watching, focus, started_at, ended_at, updated_at) '
                       'VALUES (1, ?, ?, ?, ?, ?)', (int(current['watching']), current['focus'] or '',
                                                     current['started_at'], current['ended_at'], timestamp))


def watch(connection, on: bool, timestamp: str):
    """Turns watching on or off; turning it off leaves the focus, so the next watch starts where this one stopped."""
    if on == watching(connection):
        return
    if on:
        save(connection, timestamp, watching=1, started_at=timestamp, ended_at=None)
    else:
        save(connection, timestamp, watching=0, ended_at=timestamp)


def follow(connection, focus: str, timestamp: str):
    save(connection, timestamp, focus=focus)


def step_in(connection, timestamp: str):
    """The user writes to someone: they are back in the world."""
    watch(connection, False, timestamp)


def watched_since(connection, since: str) -> bool:
    """Whether the user was watching at any point after `since`: time spent watching is not time away."""
    found = row(connection)
    return bool(found['watching'] or (found['ended_at'] and found['ended_at'] > since))
