"""On a call (Hit List #59, v0.12 Where you are): talking on the phone, started by either side.

A call is the third state a companion can be in with the user, beside apart and together (companion/life/together.py).
Rules start and end it; the model never decides it.

The user calls them: the Call button in the chat header, or words like "can I call you?" and "call me?". They pick up
when they are free (not at work, out, or asleep); otherwise they don't, and the reply to those words says why, or for
the button, they text back once they are free ("sorry, missed your call, I was at work").

They call the user: now and then, as often as the Getting together slider says (more for someone far away, since calls
carry long distance), a companion who is comfortable with the user rings. The strip shows it for a few minutes with
Answer and Decline; writing in the chat answers it too. A call nobody answered becomes a first text later ("tried
calling you!"). Rings come with first texts (companion/life/openers.py), so quiet hours, their sleep and the gap after
the last message all hold them back.

On a call the same chat is the call: replies are written as spoken words, texting habits stop (no held replies, bursts
or typos) and, when a voice is set up for voice notes (companion/voice/notes.py), each reply is also read aloud. It
ends with End call, a goodbye in the chat, ten quiet minutes, or on its own when they have to go (work, class,
bedtime: together.end_of_visit), when they say so first.
"""
import random
import re
from datetime import datetime, timedelta

from companion.clock import parse, stamp, zone
from companion.database import decode, encode, identifier, many, one, optional
from companion.errors import require
from companion.life import own_plans, pacing, together, where

ACTIVE = True
# Rings and the texts after a missed call (first texts); off in most tests (tests/conftest.py).
FIRST_TEXTS = True
# How long a call rings, how long a quiet line stays open, and the shortest call worth picking up for.
RING = timedelta(minutes=5)
IDLE = timedelta(minutes=10)
SHORTEST = timedelta(minutes=10)
# How long a call lasts at most, rolled per call; it ends sooner at their next work, class or bedtime.
HOURS = (0.5, 1.25)
# When they start to wrap up before having to go, how long the strip shows a call that ended or went unanswered,
# and how long the chat context still mentions it.
WRAP_UP = timedelta(minutes=5)
SHOWN_FOR = timedelta(minutes=2)
TOLD_FOR = timedelta(hours=2)
# Ringing the user: the chance a day brings a call, by the slider; more for someone in another city. Only someone at
# least Comfortable (Friends) with the user rings (companion/memory/closeness.py).
RING_CHANCE = {1: 0.06, 2: 0.15, 3: 0.3}
FAR_TIMES = 2
RING_HOURS = (10, 22)
CLOSE = 3
# A call they missed from the user is answered with a text when they are next free, within this long.
CALL_BACK_WITHIN = timedelta(hours=12)
MISSED_TEXT_WITHIN = timedelta(hours=3)

# Asking to talk on the phone now: "can I call you?", "call me?", "facetime?", "I'm calling you".
ASKS = re.compile(r"\b(?:call me|(?:can|could|may|should) i (?:call|ring|phone|facetime)(?: you)?|(?:can|could|will) you "
                  r"(?:call|ring|phone|facetime) me|(?:wanna|want to|do you want to) (?:call|talk on the phone|"
                  r"facetime|video ?chat|hop on a call)|give (?:me|you) a (?:call|ring|bell)|ring me|phone me|"
                  r"facetime(?: me)?|video ?call|(?:i'?m|i am|im) calling you|calling you now|let'?s (?:call|talk on "
                  r"the phone|facetime|hop on a call))\b", re.IGNORECASE)
# A call for another time is talk, not a call now: "call me tonight after work".
LATER = re.compile(r"\b(?:later|tonight|tomorrow|after (?:work|class|dinner|school)|this (?:evening|weekend)|"
                   r"in (?:a bit|an hour|a few)|when (?:you'?re|you are|i'?m|i am) (?:free|off|home|done|back)|"
                   r"(?:mon|tues|wednes|thurs|fri|satur|sun)day)\b", re.IGNORECASE)
RIGHT_NOW = re.compile(r'\b(?:right now|now|rn)\b', re.IGNORECASE)
# Saying goodbye on the phone ends the call.
HANG_UP = re.compile(r"\b(?:(?:i'?ve |i have |i )?(?:gotta|got to|have to|need to|should) (?:go|run|hang up|get going)|"
                     r"talk (?:to you )?(?:later|soon|tomorrow)|bye+|goodbye|good ?night|night night|hanging up|"
                     r"(?:i'?ll|i will) let you go|ttyl)\b", re.IGNORECASE)

ON_CALL = ('This is a voice call, not texting: write only the words you say out loud, the way people talk on the phone, '
           'in short turns. No emoji, no *actions*, no typos. You can hear each other but not see each other.')
WHY = ('you just finished your day and wanted to talk it through', 'you wanted to hear their voice',
       'you were bored and thought of them', 'you had a quiet moment and missed talking to them properly')
WHY_FAR = ('you miss them and texting is not the same', 'you wanted to hear their voice, from so far away')


def level(connection) -> int:
    return together.level(connection)


# --- Reading the chat -------------------------------------------------------------------------------------------

def asked(text: str) -> bool:
    """Whether a user message asks to talk on the phone now."""
    text = own_plans.QUOTED.sub(' ', own_plans.ACTIONS.sub(' ', text)).replace('’', "'")
    for sentence in re.split(r'(?<=[.!?])\s+|\n+', text):
        if own_plans.PAST.search(sentence) or own_plans.NEGATED.search(sentence) or not ASKS.search(sentence):
            continue
        if LATER.search(sentence) and not RIGHT_NOW.search(sentence):
            continue
        return True
    return False


def hanging_up(text: str) -> bool:
    return bool(HANG_UP.search(text.replace('’', "'")))


# --- The call's state ---------------------------------------------------------------------------------------------

def get(connection, call_id: str) -> dict | None:
    row = optional(connection, 'SELECT * FROM calls WHERE id=?', (call_id,))
    return {**row, 'reason': decode(row['reason'])} if row else None


def latest(connection, timeline_id: str) -> dict | None:
    row = optional(connection, 'SELECT * FROM calls WHERE timeline_id=? ORDER BY created_at DESC, rowid DESC LIMIT 1',
                   (timeline_id,))
    return {**row, 'reason': decode(row['reason'])} if row else None


def last_said(connection, call: dict) -> datetime:
    """The last thing said on the line: the latest message since it was picked up, or the pick-up itself."""
    row = one(connection, 'SELECT MAX(created_at) AS at FROM messages WHERE timeline_id=? AND created_at>=?',
              (call['timeline_id'], call['started_at']))
    return max(parse(call['started_at']), parse(row['at'])) if row['at'] else parse(call['started_at'])


def effective(connection, call: dict | None, now: datetime) -> dict | None:
    """The call as it stands now: a ring nobody answered is missed, and a call ends on its own at its time or after
    IDLE minutes of quiet. Worked out when read, so nothing has to run for a call to end."""
    if call is None:
        return None
    if call['status'] == 'ringing':
        if now - parse(call['created_at']) >= RING:
            return {**call, 'status': 'missed', 'ended_at': stamp(parse(call['created_at']) + RING)}
        return call
    if call['status'] == 'on':
        end = min(parse(call['until_at']), last_said(connection, call) + IDLE)
        if now >= end:
            return {**call, 'status': 'ended', 'ended_at': stamp(end)}
    return call


def now_for(connection, companion: dict, now: datetime) -> dict | None:
    """The newest call on their chat, as it stands now."""
    return effective(connection, latest(connection, companion['active_timeline_id']), now)


def on_call(connection, companion: dict, now: datetime) -> dict | None:
    found = now_for(connection, companion, now)
    return found if found and found['status'] == 'on' else None


def ringing(connection, companion: dict, now: datetime) -> dict | None:
    found = now_for(connection, companion, now)
    return found if found and found['status'] == 'ringing' else None


def speaking(connection, companion: dict, now: datetime, message_id: str | None) -> bool:
    """Whether a reply to this message is said on the phone: the call is on, or this message just said goodbye."""
    found = now_for(connection, companion, now)
    return bool(found and (found['status'] == 'on' or (message_id and found['ended_by'] == message_id)))


# --- When they can pick up -----------------------------------------------------------------------------------------

def why_not(connection, companion: dict, now: datetime) -> dict | None:
    """Why they can't talk on the phone right now ({why, ...}), or None when they can. Far away is no reason, and a
    trip is none either: a call is how people keep up from anywhere."""
    found = pacing.block_now(connection, companion, now)
    block = found[0] if found else None
    kind = together.busy_kind(block)
    if kind and kind != 'away':
        until = parse(found[1]).astimezone(zone(companion['version']['timezone'])).strftime('%H:%M')
        return {'why': kind, 'label': (block.get('label') or block['kind']).lower(), 'until': until}
    if until_at(companion, now, 1.0) - now < SHORTEST:
        return {'why': 'late'}
    return None


def until_at(companion: dict, now: datetime, hours: float) -> datetime:
    """When a call picked up now ends on its own (together.end_of_visit: their next work, class or bedtime)."""
    local = now.astimezone(zone(companion['version']['timezone']))
    end = together.end_of_visit(companion['version']['definition'], local, hours)
    found = datetime.combine(local.date(), datetime.strptime(end, '%H:%M').time(), local.tzinfo)
    return max(found, local)


def length(call_id: str) -> float:
    return random.Random(f'call:{call_id}').uniform(*HOURS)


# --- Starting and ending ---------------------------------------------------------------------------------------

def insert(connection, companion: dict, direction: str, status: str, now: datetime, message_id: str | None = None,
           reason: dict | None = None, trigger_key: str | None = None) -> dict:
    call_id = identifier()
    started = stamp(now) if status == 'on' else None
    until = stamp(until_at(companion, now, length(call_id))) if status == 'on' else None
    connection.execute('INSERT INTO calls (id, companion_id, timeline_id, direction, status, message_id, trigger_key, '
                       'reason, started_at, until_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                       (call_id, companion['id'], companion['active_timeline_id'], direction, status, message_id,
                        trigger_key, encode(reason or {}), started, until, stamp(now)))
    return get(connection, call_id)


def blocked(connection, companion: dict, now: datetime) -> str | None:
    """Why no call can start at all: they are together already, or a call is on or ringing."""
    if not ACTIVE:
        return 'off'
    if together.together_now(connection, companion, now):
        return 'together'
    found = now_for(connection, companion, now)
    return found['status'] if found and found['status'] in ('on', 'ringing') else None


def call(connection, companion: dict, now: datetime) -> dict:
    """The user calls them (the Call button): they pick up when free, else it is a missed call they text back about."""
    require(blocked(connection, companion, now) is None, 'You are already together or on a call.', 409)
    reason = why_not(connection, companion, now)
    if reason:
        return insert(connection, companion, 'you', 'missed', now, reason=reason)
    return insert(connection, companion, 'you', 'on', now)


def answer(connection, found: dict, now: datetime) -> dict:
    from companion.characters import by_id
    companion = by_id(connection, found['companion_id'])
    connection.execute("UPDATE calls SET status='on', started_at=?, until_at=? WHERE id=?",
                       (stamp(now), stamp(until_at(companion, now, length(found['id']))), found['id']))
    return get(connection, found['id'])


def end(connection, found: dict, now: datetime, message_id: str | None = None):
    connection.execute("UPDATE calls SET status='ended', ended_at=?, ended_by=? WHERE id=?",
                       (stamp(now), message_id, found['id']))


def act(connection, companion: dict, call_id: str, action: str, now: datetime) -> dict:
    """Answer or Decline a ring, or End call (the strip's buttons)."""
    found = effective(connection, get(connection, call_id), now)
    require(found is not None and found['timeline_id'] == companion['active_timeline_id'], 'That call was not found.',
            404)
    if action == 'end':
        require(found['status'] == 'on', 'That call has already ended.', 409)
        end(connection, found, now)
    else:
        require(found['status'] == 'ringing', 'That call is no longer ringing.', 409)
        if action == 'answer':
            answer(connection, found, now)
        else:
            connection.execute("UPDATE calls SET status='declined', ended_at=? WHERE id=?", (stamp(now), found['id']))
    return together.view(connection, companion, now)


def note(connection, message: dict, companion: dict, timestamp: str) -> bool:
    """A user message on the phone or about it, settled before the reply is written: writing while it rings answers,
    a goodbye on the line hangs up, and asking to call starts one when they can pick up (else the reply says why)."""
    if not ACTIVE or message['role'] != 'user' or message['status'] != 'complete':
        return False
    now = parse(message['created_at'])
    found = now_for(connection, companion, now)
    if found and found['status'] == 'ringing':
        answer(connection, found, now)
        return True
    if found and found['status'] == 'on':
        if hanging_up(message['text']):
            end(connection, found, now, message['id'])
        return True
    if not asked(message['text']) or blocked(connection, companion, now):
        return False
    if optional(connection, 'SELECT id FROM together_asks WHERE message_id=?', (message['id'],)) or \
            optional(connection, 'SELECT id FROM calls WHERE message_id=?', (message['id'],)):
        return True
    reason = why_not(connection, companion, now)
    if reason:
        return together.record(connection, companion, message, 'call', reason, timestamp)
    insert(connection, companion, 'you', 'on', now, message['id'])
    return True


# --- What the chat context says ---------------------------------------------------------------------------------

def context_lines(connection, companion: dict, now: datetime, fresh_ids: set[str]) -> list[tuple[str, str]]:
    """(identity, line) for the 'where' section: the call under way and how it started, a goodbye on the line, a
    call that ended a little while ago, and a call one of you missed."""
    found = now_for(connection, companion, now)
    if found is None:
        return []
    timezone = companion['version']['timezone']
    if found['status'] == 'on' or (found['status'] == 'ended' and found['ended_by'] in fresh_ids):
        return on_lines(connection, companion, found, now, fresh_ids)
    ended = parse(found['ended_at']) if found['ended_at'] else parse(found['created_at'])
    if not timedelta(0) <= now - ended < TOLD_FOR:
        return []
    at = parse(found['created_at']).astimezone(zone(timezone)).strftime('%H:%M')
    if found['status'] == 'ended':
        minutes = max(1, round((ended - parse(found['started_at'])).total_seconds() / 60))
        return [(f"call-ended:{found['id']}", f'- You and the user talked on the phone for about {minutes} minutes '
                 'and hung up a little while ago. You are texting again.')]
    if found['direction'] == 'you':
        why = together.reason_text(found['reason']) if found['reason'] else 'you were busy'
        return [(f"call-missed:{found['id']}", f"- The user tried to call you at {at} and you didn't pick up: {why}. "
                 'You are texting.')]
    answered = 'declined' if found['status'] == 'declined' else "didn't pick up"
    return [(f"call-missed:{found['id']}", f'- You tried to call the user at {at} and they {answered}. You are '
             'texting.')]


def on_lines(connection, companion: dict, found: dict, now: datetime, fresh_ids: set[str]) -> list[tuple[str, str]]:
    local = parse(found['started_at']).astimezone(zone(companion['version']['timezone']))
    who = 'You called the user' if found['direction'] == 'them' else 'The user called you'
    lines = [(f"call:{found['id']}", f'- You are on a phone call with the user right now. {who} at {local:%H:%M}. '
              f'{ON_CALL}')]
    if found['ended_by'] in fresh_ids:
        lines.append((f"call-goodbye:{found['id']}", '- The user is saying goodbye to end the call. Say goodbye back, '
                      'out loud; the call ends after this.'))
        return lines
    if found['message_id'] in fresh_ids:
        lines.append((f"call-picked-up:{found['id']}", '- The user asked to talk on the phone and you picked up: this '
                      'reply is the first thing you say on the call.'))
    elif found['direction'] == 'them' and not said_since(connection, found, 'companion'):
        why = found['reason'].get('why_called') or WHY[1]
        lines.append((f"call-answered:{found['id']}", f'- They just picked up. You called because {why}: tell them, '
                      'in your own words.'))
    if parse(found['until_at']) - now <= WRAP_UP:
        lines.append((f"call-wrap-up:{found['id']}", '- You have to go in a few minutes: start wrapping up the call, '
                      'kindly.'))
    return lines


def said_since(connection, found: dict, role: str) -> bool:
    return bool(optional(connection, "SELECT id FROM messages WHERE timeline_id=? AND role=? AND status='complete' "
                         'AND created_at>=? LIMIT 1', (found['timeline_id'], role, found['started_at'])))


# --- The state, in plain words ------------------------------------------------------------------------------------

def state(connection, companion: dict, now: datetime) -> dict | None:
    """{state, kind, text} while a call is on or ringing, else None (together.state reads this first)."""
    found = now_for(connection, companion, now)
    if found and found['status'] == 'on':
        return {'state': 'call', 'kind': 'call', 'text': 'On a call'}
    if found and found['status'] == 'ringing':
        return {'state': 'apart', 'kind': 'ringing', 'text': 'Calling you'}
    return None


def view(connection, companion: dict, now: datetime) -> dict | None:
    """The call the strip shows: one on or ringing, or one that ended or went unanswered a moment ago."""
    found = now_for(connection, companion, now)
    if found is None:
        return None
    done = found['status'] not in ('on', 'ringing')
    if done and now - parse(found['ended_at'] or found['created_at']) >= SHOWN_FOR:
        return None
    return {'id': found['id'], 'direction': found['direction'], 'status': found['status'],
            'started_at': found['started_at'], 'until_at': found['until_at'], 'ended_at': found['ended_at']}


# --- They call the user (with first texts, companion/life/openers.py) ---------------------------------------------

def ring_due(connection, companion: dict, now: datetime) -> list:
    """Now and then, at a seeded minute on a seeded day, a companion who is comfortable with the user rings them,
    when they are free to talk. Saving it (`ring`) starts the ring; no text is written."""
    from companion.life.openers import Trigger
    chance = RING_CHANCE.get(level(connection)) if ACTIVE and FIRST_TEXTS else None
    version = companion['version']
    local = now.astimezone(zone(version['timezone']))
    if not chance or not RING_HOURS[0] <= local.hour < RING_HOURS[1]:
        return []
    key = f'call:{local.date().isoformat()}'
    if optional(connection, 'SELECT id FROM calls WHERE timeline_id=? AND trigger_key=?',
                (companion['active_timeline_id'], key)):
        return []
    far = where.between(connection, version['definition']).long_distance
    rng = random.Random(f"{companion['id']}:{key}")
    if rng.random() >= min(0.6, chance * (FAR_TIMES if far else 1)) or \
            local.hour * 60 + local.minute < rng.randint(RING_HOURS[0] * 60, RING_HOURS[1] * 60 - 30):
        return []
    if blocked(connection, companion, now) or why_not(connection, companion, now) or not close(connection, companion,
                                                                                               now):
        return []
    return [Trigger(key, 'call', rng.choice(WHY_FAR if far else WHY))]


def close(connection, companion: dict, now: datetime) -> bool:
    from companion.memory import closeness
    return closeness.state(connection, companion, now)['level'] >= CLOSE


def ring(connection, companion: dict, trigger, now: datetime) -> dict | None:
    """Start the ring a first-text check found; None when it can't ring after all."""
    if blocked(connection, companion, now) or optional(
            connection, 'SELECT id FROM calls WHERE timeline_id=? AND trigger_key=?',
            (companion['active_timeline_id'], trigger.key)):
        return None
    return insert(connection, companion, 'them', 'ringing', now, reason={'why_called': trigger.reason},
                  trigger_key=trigger.key)


def missed_due(connection, companion: dict, now: datetime) -> list:
    """After a call: a text about one they missed from the user, once they are free again ("sorry, I was at work"),
    or about one the user didn't pick up ("tried calling you!")."""
    from companion.life.openers import Trigger
    if not ACTIVE or not FIRST_TEXTS:
        return []
    timeline_id = companion['active_timeline_id']
    rows = many(connection, "SELECT * FROM calls WHERE timeline_id=? AND created_at>=? AND status IN "
                "('missed', 'ringing', 'declined') ORDER BY created_at DESC LIMIT 1",
                (timeline_id, stamp(now - CALL_BACK_WITHIN)))
    found = effective(connection, {**rows[0], 'reason': decode(rows[0]['reason'])}, now) if rows else None
    if not found or found['status'] not in ('missed', 'declined') or later_call(connection, found):
        return []
    at = parse(found['created_at']).astimezone(zone(companion['version']['timezone'])).strftime('%H:%M')
    key = f"call-back:{found['id']}"
    if found['direction'] == 'you':
        if why_not(connection, companion, now):
            return []
        why = together.reason_text(found['reason']) if found['reason'] else 'you were busy'
        return [Trigger(key, 'call_back', f"The user tried to call you at {at} and you couldn't pick up because {why}. "
                        "You are free now: say sorry you missed it and ask what's up, or offer to call back.",
                        'Sorry I missed your call! What’s up?')]
    if now - parse(found['ended_at']) > MISSED_TEXT_WITHIN or found['status'] == 'declined':
        return []
    return [Trigger(key, 'call_back', f"You tried to call the user at {at} and they didn't pick up. Text them about it "
                    'lightly, no guilt: they can call you back when they are free.',
                    'Tried calling you! Call me back when you’re free?')]


def later_call(connection, found: dict) -> bool:
    return bool(optional(connection, 'SELECT id FROM calls WHERE timeline_id=? AND created_at>? LIMIT 1',
                         (found['timeline_id'], found['created_at'])))
