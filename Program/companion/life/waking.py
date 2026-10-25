"""Waking them (v1.1.0, time zones): a sleeping companion can always be woken, at a small cost.

With "Reply at their own pace" on, a message sent while they sleep is answered when they wake (companion/life/pacing.py).
Three things wake them instead, by rule: a second text while the reply to the first is still waiting for morning, words
like "wake up", or a call (companion/life/calls.py). Then:

- the reply comes now, groggy and short (`lines`, in their chat context), and so does each reply while they are still
  up; AWAKE_FOR after the last message they have dropped off again, and the next text waits for morning (a second one
  wakes them again, the same night, at no further cost);
- the reply that was waiting for morning is dropped unseen, and the groggy one answers everything they were sent;
- they are a little annoyed with the user (companion/moods.py), more on later nights;
- after their sleep they may bring it up, once: the line stays until they have answered once after waking.

It wears thinner night after night: the nights they were woken in the last WINDOW decide how they take it (first,
again, thin), and Settings > Realism > Waking them (`life_settings.waking_realism`) sets how fast, from 0 (they never
mind) to 3 (it wears thin fast). Closeness softens it: someone Close takes it more kindly.
"""
import re
from datetime import datetime, timedelta

from companion.clock import parse, stamp, zone
from companion.database import identifier, many, optional

AWAKE_FOR = timedelta(minutes=20)
WINDOW = timedelta(days=14)
MORNING_FOR = timedelta(hours=14)
# Nights woken in WINDOW (this one included) for 'again' and 'thin', by waking_realism; 0 never wears thin.
NIGHTS = {0: (99, 99), 1: (3, 6), 2: (2, 4), 3: (2, 3)}
# How annoyed with the user it leaves them (companion/moods.py), by waking_realism and level.
ANNOYED = {0: {}, 1: {'thin': 1}, 2: {'first': 1, 'again': 1, 'thin': 2}, 3: {'first': 1, 'again': 2, 'thin': 2}}
CLOSE = 4
WORDS = re.compile(r"\b(?:wake (?:up|up please|up pls|please)|wakey|wakeup|get up|it'?s (?:an )?(?:urgent|emergency)|"
                   r"(?:this is|it'?s) urgent|emergency)\b", re.IGNORECASE)
HOW = {'texts': 'texts', 'words': 'texts', 'call': 'call'}
NTH = {2: 'second', 3: 'third', 4: 'fourth', 5: 'fifth', 6: 'sixth', 7: 'seventh'}

# The groggy lines, A/B tested on 11 models (2026-10-25): they fit the night's mood 115 times in 119.
GROGGY = {
    'first': "Their {how} just woke you up. It's {time} for you and you were fast asleep. Answer the way someone "
             "half-awake does: a few short words, sleepy, a little muddled. Check they're okay. Don't act wide awake "
             "and don't write a long reply.",
    'again': "Their {how} just woke you up. It's {time} for you and you were fast asleep, and this is the {nth} night "
             "lately they've woken you, so you're less patient than you'd like: still sleepy, a bit short with them. "
             'Keep it brief.',
    'thin': "Their {how} just woke you up. It's {time} for you, and they've woken you most nights lately ({nights} "
            "nights). It's wearing thin: you're tired and a little fed up. Say so plainly, in your own way, and ask "
            "them to let you sleep unless something's wrong. Keep it brief.",
}
KIND = {True: " You're close, so it comes out softer than it might.",
        False: " You don't know them that well yet, so it's a bit awkward."}
STILL_UP = ("You're still half-awake after they woke you at {time}. Keep it short and sleepy; you'd like to get back "
            'to sleep soon.')
MORNING = ('Last night around {time} they woke you up ({how}). If it fits, bring it up once, briefly, the way you would '
           '(teasing, curious, a little put out), then let it go.')
MORNING_THIN = " It's the {nth} night lately, and you'd like it to stop."


def realism(connection) -> int:
    row = optional(connection, 'SELECT waking_realism FROM life_settings WHERE id=1')
    return 2 if row is None else int(row['waking_realism'])


def level_for(nights: int, setting: int) -> str:
    again, thin = NIGHTS[setting]
    return 'thin' if nights >= thin else 'again' if nights >= again else 'first'


def this_night(connection, companion: dict, sleep_ends_at: str) -> dict | None:
    return optional(connection, 'SELECT * FROM wakes WHERE timeline_id=? AND sleep_ends_at=?',
                    (companion['active_timeline_id'], sleep_ends_at))


def waiting(connection, timeline_id: str, now: datetime) -> list[str]:
    """Replies still waiting for them to wake (held, companion/life/pacing.py)."""
    return [row['id'] for row in many(connection, "SELECT id FROM messages WHERE timeline_id=? AND role='companion' "
                                      'AND held_until>? AND superseded_at IS NULL', (timeline_id, stamp(now)))]


def nights_woken(connection, companion: dict, now: datetime) -> int:
    row = optional(connection, 'SELECT COUNT(*) AS n FROM wakes WHERE companion_id=? AND woken_at>? AND woken_at<=?',
                   (companion['id'], stamp(now - WINDOW), stamp(now)))
    return row['n'] if row else 0


def wake(connection, companion: dict, now: datetime, sleep_ends_at: str, how: str) -> dict:
    """They are woken now (`how`: texts, words or call). The first time this sleep it counts as a night and costs a
    little mood; once they've dropped off again, waking them again the same night only keeps them up."""
    timeline_id, timestamp = companion['active_timeline_id'], stamp(now)
    found = this_night(connection, companion, sleep_ends_at)
    if found:
        connection.execute('UPDATE wakes SET last_at=? WHERE id=?', (timestamp, found['id']))
        return {**found, 'last_at': timestamp}
    setting = realism(connection)
    nights = nights_woken(connection, companion, now) + 1
    level = level_for(nights, setting)
    connection.execute('INSERT INTO wakes (id, companion_id, timeline_id, sleep_ends_at, how, level, nights, woken_at, '
                       'last_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                       (identifier(), companion['id'], timeline_id, sleep_ends_at, how, level, nights, timestamp,
                        timestamp))
    if amount := ANNOYED[setting].get(level):
        from companion import moods
        moods.save(connection, f"companion:{companion['id']}", 'annoyed', amount, moods.USER,
                   'you woke them up in the night', now)
    return this_night(connection, companion, sleep_ends_at)


def by_text(connection, companion: dict, now: datetime, text: str, sleep_ends_at: str) -> list[str] | None:
    """A message sent while they sleep: the replies it drops when it wakes them (or finds them still up), so the reply
    comes now, else None. A reply that was waiting for morning is dropped unseen; the groggy one answers everything."""
    found = this_night(connection, companion, sleep_ends_at)
    if found and now - parse(found['last_at']) < AWAKE_FOR:
        wake(connection, companion, now, sleep_ends_at, found['how'])
        return []
    held = waiting(connection, companion['active_timeline_id'], now)
    how = 'words' if WORDS.search(text or '') else 'texts' if held else None
    if how is None:
        return None
    if held:
        connection.execute(f"UPDATE messages SET superseded_at=?, active=0, held_until=NULL "
                           f"WHERE id IN ({', '.join('?' * len(held))})", (stamp(now), *held))
    wake(connection, companion, now, sleep_ends_at, how)
    return held


def asleep(connection, companion: dict, now: datetime) -> str | None:
    """When the sleep they are in now ends, None when they aren't asleep."""
    from companion.life import pacing
    found = pacing.block_now(connection, companion, now)
    return found[1] if found and pacing.busy_kind(found[0]) == 'sleep' else None


def local_clock(companion: dict, instant: datetime) -> str:
    return instant.astimezone(zone(companion['version']['timezone'])).strftime('%H:%M')


def kindly(connection, companion: dict, now: datetime) -> str:
    from companion.memory import closeness
    level = closeness.state(connection, companion, now)['level']
    return KIND[level >= CLOSE] if level >= CLOSE or level <= 2 else ''


def replied(connection, companion: dict, since: str, now: datetime) -> bool:
    """Whether they have answered since then (a reply now, or one that was held and has shown)."""
    return optional(connection, "SELECT 1 FROM messages WHERE timeline_id=? AND role='companion' AND status='complete' "
                    'AND active=1 AND created_at>=? AND (held_until IS NULL OR held_until<=?)',
                    (companion['active_timeline_id'], since, stamp(now))) is not None


def lines(connection, companion: dict, now: datetime) -> list[tuple[str, str]]:
    """Their chat context's line about being woken: groggy while they are up, or the morning after, to bring up once."""
    from companion.life import calls
    ends_at = asleep(connection, companion, now)
    if ends_at:
        found = this_night(connection, companion, ends_at)
        if not found:
            return []
        on_call = calls.on_call(connection, companion, now)
        if not on_call and now - parse(found['last_at']) >= AWAKE_FOR:
            return []
        if replied(connection, companion, found['woken_at'], now):
            return [(f"woken:{found['id']}:up", STILL_UP.format(time=local_clock(companion, parse(found['woken_at']))))]
        text = GROGGY[found['level']].format(how=HOW[found['how']], time=local_clock(companion, now),
                                             nth=NTH.get(found['nights'], f"{found['nights']}th"), nights=found['nights'])
        return [(f"woken:{found['id']}", text + kindly(connection, companion, now))]
    found = optional(connection, 'SELECT * FROM wakes WHERE timeline_id=? AND sleep_ends_at<=? AND sleep_ends_at>? '
                     'ORDER BY sleep_ends_at DESC LIMIT 1',
                     (companion['active_timeline_id'], stamp(now), stamp(now - MORNING_FOR)))
    if not found or replied(connection, companion, found['sleep_ends_at'], now):
        return []
    text = MORNING.format(time=local_clock(companion, parse(found['woken_at'])), how=HOW[found['how']])
    if found['level'] == 'thin':
        text += MORNING_THIN.format(nth=NTH.get(found['nights'], f"{found['nights']}th"))
    return [(f"woken:{found['id']}:morning", text)]
