"""Together or apart (Hit List #59, v0.12 Where you are): where each companion is with the user, always known.

Every companion is in one state with the user: Apart (texting, the default), Together (out somewhere, at their place
or at the user's) or, later, On a call. Rules set it from the agenda and the chat; the model never decides it. Being
together is an outing (companion/life/outings.py): going out, dinner at theirs, and the visits this module adds, so it
takes its slot in their day, holds no replies, ends with Head home and is kept as a memory like any other outing.

Visits come from the chat. "Come over?", "I'm at your door" and "can I come to yours?" become a visit by the same
rules as outings: the companion says yes when they are free and nearby, and otherwise the reply says why not (at work
until five, asleep, out, too far away). A visit with no day named starts now and ends on its own at a time the rules
pick (their bedtime, or early when they work the next morning), or when either side heads home.

Companions come to the user too, as often as the Getting together slider says (life_settings.together_realism:
0 never on their own, 1 light, 2 true to life, 3 often): they suggest meeting up or invite the user over (a first
text, companion/life/openers.py), and a close companion in the user's city sometimes knocks unannounced, never in the
user's quiet hours (openers.held) and never on an easy life (below level 2). "Not now" sends them home again.
"""
import random
import re
from datetime import date, datetime, timedelta

from companion.clock import parse, stamp, zone
from companion.database import encode, identifier, many, optional, settings
from companion.life import outings, own_plans, pacing, routine, trips, where

ACTIVE = True
# Knocks and suggestions to meet up (first texts); off in most tests (tests/conftest.py).
FIRST_TEXTS = True
DEFAULT_LEVEL = 2
# Knocking unannounced: from this level of the slider, and only for someone this close (companion/memory/closeness.py:
# Close, or Close friends).
KNOCK_FROM = 2
CLOSE = 4
# The chance a day brings a knock, and a suggestion to meet up, by the slider.
KNOCK_CHANCE = {2: 1 / 14, 3: 1 / 5}
SUGGEST_EVERY = 3  # days
SUGGEST_CHANCE = {1: 0.12, 2: 0.3, 3: 0.55}
KNOCK_HOURS = (10, 21)
SUGGEST_HOURS = (10, 21)
# How long a visit lasts at most, and the least time worth coming over for.
VISIT_HOURS = 3.0
KNOCK_HOURS_LONG = 2.0
SHORTEST = timedelta(minutes=45)
# Up early for work: a visit the night before ends by then.
EARLY_START = '10:00'
SCHOOL_NIGHT = '22:30'
# How long "not now" turns a knock away, and how long an ended visit is still told in the chat.
NOT_NOW_WINDOW = timedelta(minutes=30)
TOLD_FOR = timedelta(hours=2)

YOURS = '~yours'
SPOTS = ['on the couch', 'in the kitchen', 'at the kitchen table', 'by the window']
VISITS = ('visit-in', 'visit-yours', 'dinner-yours')
AT_YOURS = ('visit-yours', 'dinner-yours')

# The user asking the companion over: "come over?", "wanna come round tonight?", "come to mine Friday?".
COME_OVER = re.compile(r"\b(?:come (?:over|round|around|by)|swing by|pop (?:over|round|by)|"
                       r"come (?:to|over to|round to) (?:mine|my place|my apartment|my flat|my house)|"
                       r"(?:dinner|supper) at (?:mine|my place))\b", re.IGNORECASE)
# The user asking to come to the companion's: "can I come over?", "can I come to yours?".
COME_TO_YOURS = re.compile(r"\b(?:(?:can|could|may|should) i (?:come|pop|swing|head|stop|drop) (?:over|round|by|to "
                           r"(?:yours|your place|your apartment|your flat|your house))|(?:come|over) to (?:yours|your "
                           r"place)|i(?:'?ll| will) come (?:over|round|to yours|to your place)|mind if i (?:come|pop|"
                           r"swing|stop|drop) (?:over|round|by)|(?:want|like) me to come (?:over|round|by))\b",
                           re.IGNORECASE)
# The user already at the companion's door.
AT_DOOR = re.compile(r"\b(?:i'?m|i am|im) (?:at|outside|downstairs at|in front of) your (?:door|place|building|"
                     r"apartment|flat|house)|\blet me in\b|\bopen (?:the|your) door\b", re.IGNORECASE)
# A question or an ask, not a story: "they came over yesterday" is no invitation.
ASKS = re.compile(r"\?|\b(?:wanna|want to|do you want|can you|could you|come over|let'?s|you should|feel like|mind if)\b",
                  re.IGNORECASE)
RIGHT_NOW = re.compile(r"\b(?:now|right now|rn|right away|asap)\b", re.IGNORECASE)
# Tonight, asked while it is still the afternoon, or later on: a visit this evening, not one from now.
EVENING = re.compile(r"\b(?:tonight|this evening|later(?: on| tonight)?|after (?:work|dinner))\b", re.IGNORECASE)
EVENING_FROM = '17:00'
# No day at all ("come over sometime next week?"): a wish for another time, so no visit is settled now.
SOMEDAY = re.compile(r"\b(?:some ?time|one of these days|some ?day|at some point|soon|next (?:week|month)|this week|"
                     r"whenever|another (?:day|time))\b", re.IGNORECASE)
# The user ending it in the chat while together, and turning a knock away.
LEAVING = re.compile(r"\b(?:i should (?:head|get going|go|get home)|i(?:'?m| am|m) (?:gonna |going to )?(?:head(?:ing)? "
                     r"(?:home|out|off)|leav(?:e|ing) now|off now)|i(?:'?d| had) better (?:go|get going|head)|time for "
                     r"(?:me|you) to (?:go|head)|you should (?:head|go) home|i'?ll let you go)\b", re.IGNORECASE)
NOT_NOW = re.compile(r"\b(?:not now|not a good time|bad time|not right now|can'?t (?:right )?now|another time|"
                     r"not today)\b", re.IGNORECASE)


def level(connection) -> int:
    row = optional(connection, 'SELECT together_realism FROM life_settings WHERE id=1')
    return row['together_realism'] if row and row['together_realism'] in range(4) else DEFAULT_LEVEL


def invites(connection, companion: dict) -> bool:
    """Whether they may ask the user over or along on their own (kitchen.py, hobbies.py): the slider is not off, and
    they live in the user's city (long distance gets weekend visits instead)."""
    from companion.life import moving_in
    return bool(level(connection)) and not where.between(connection, companion['version']['definition']).long_distance \
        and not moving_in.living(connection, companion)


# --- Places -----------------------------------------------------------------------------------------------------

def your_place(connection) -> dict:
    """The user's home as an outing's place (where.py keeps it)."""
    found = where.your_home(connection)
    city, hood = found if found else (None, None)
    return {'id': YOURS, 'name': 'Your place', 'kind': 'your-home', 'neighborhood': hood['name'] if hood else '',
            'summary': '', 'cost': '', 'cuisine': '', 'city': city['name'] if city else '',
            'city_id': city['id'] if city else '', 'spots': list(SPOTS)}


def their_place(connection, companion: dict) -> dict:
    """Their home as an outing's place, without a dinner menu (a visit, not dinner)."""
    from companion.life import money
    definition = companion['version']['definition']
    budget = money.profile(definition)
    data = outings.city_data(connection, definition)
    return {'id': outings.HOME, 'name': f"{definition['name']}'s place", 'kind': 'home',
            'neighborhood': budget.neighborhood if budget else '', 'summary': '', 'cost': '', 'cuisine': '',
            'city': data['name'] if data else '', 'city_id': data['id'] if data else '', 'spots': list(SPOTS)}


# --- Reading the chat -------------------------------------------------------------------------------------------

def asked(text: str) -> str | None:
    """The visit a user message asks for: 'visit-yours' (they come to the user), 'dinner-yours' (the user cooks),
    'visit-in' (the user comes to theirs), 'door' (the user is at their door), else None."""
    text = own_plans.QUOTED.sub(' ', own_plans.ACTIONS.sub(' ', text)).replace('’', "'")
    for sentence in re.split(r'(?<=[.!?])\s+|\n+', text):
        if own_plans.PAST.search(sentence) or own_plans.NEGATED.search(sentence):
            continue
        if AT_DOOR.search(sentence):
            return 'door'
        if COME_TO_YOURS.search(sentence) and ASKS.search(sentence):
            return 'visit-in'
        if COME_OVER.search(sentence) and ASKS.search(sentence):
            return 'dinner-yours' if outings.FOOD.search(text) and outings.USER_HOSTS.search(text) else 'visit-yours'
    return None


# --- When they can come ------------------------------------------------------------------------------------------

def busy_kind(block: dict | None) -> str | None:
    if not block:
        return None
    if block.get('trip'):
        return 'away'
    if block['kind'] in routine.RESTING:
        return 'asleep'
    if block.get('sick_day') or block.get('holiday') or block.get('with_user'):
        return None
    if block['kind'] in outings.NOT_BUSY:
        return 'busy'
    return 'out' if block['kind'] in ('social', 'errand') else None


def end_of_visit(definition: dict, local_now: datetime, hours: float) -> str:
    """When a visit starting now ends on its own: after `hours`, or earlier at their next work, class or bedtime, and
    by SCHOOL_NIGHT when they start early the next morning. Never past midnight."""
    schedule = routine.blocks(definition)[0]
    end = local_now + timedelta(hours=hours)
    step = local_now
    while step < end:
        step += timedelta(minutes=15)
        if outings.busy_at(schedule, step.date(), step.strftime('%H:%M')):
            end = step
            break
    midnight = datetime.combine(local_now.date(), datetime.max.time(), local_now.tzinfo).replace(second=0,
                                                                                                microsecond=0)
    end = min(end, midnight)
    tomorrow = local_now.date() + timedelta(days=1)
    early = any(block.on(tomorrow) and block.view()['kind'] in ('work', 'study')
                and '04:00' <= block.view()['start'] < EARLY_START for block in schedule)
    if early:
        end = min(end, datetime.combine(local_now.date(), datetime.strptime(SCHOOL_NIGHT, '%H:%M').time(),
                                        local_now.tzinfo))
    return end.strftime('%H:%M')


def why_not(connection, companion: dict, now: datetime, hours: float = VISIT_HOURS) -> dict | None:
    """Why they can't get together right now ({why, ...}), or None when they can: free, nearby, and with long enough
    before their next work, class or bedtime."""
    version = companion['version']
    definition = version['definition']
    between = where.between(connection, definition)
    if between.long_distance:
        return {'why': 'far', 'city': between.their_city['name'], 'km': between.km}
    local = now.astimezone(zone(version['timezone']))
    if trips.away_on(connection, companion['id'], local.date()):
        return {'why': 'away'}
    found = pacing.block_now(connection, companion, now)
    block = found[0] if found else None
    kind = busy_kind(block)
    if kind:
        until = parse(found[1]).astimezone(zone(version['timezone'])).strftime('%H:%M')
        return {'why': kind, 'label': (block.get('label') or block['kind']).lower(), 'until': until}
    if together_now(connection, companion, now) or outing_today(connection, companion, local.date(), now):
        return {'why': 'plans'}
    end = end_of_visit(definition, local, hours)
    if datetime.combine(local.date(), datetime.strptime(end, '%H:%M').time(), local.tzinfo) - local < SHORTEST:
        return {'why': 'late'}
    return None


def together_now(connection, companion: dict, now: datetime) -> dict | None:
    """The outing or visit under way with the user right now, if there is one."""
    timezone = companion['version']['timezone']
    since = (now.astimezone(zone(timezone)).date() - timedelta(days=1)).isoformat()
    return next((outing for outing in outings.in_force(connection, companion['active_timeline_id'], since)
                 if outings.state(outing, timezone, now) == 'now'), None)


def in_person(connection, companion: dict, now: datetime) -> bool:
    """Together right now: out, at one of their places, on a weekend visit (companion/life/long_distance.py), or home
    together of an evening when they live together (companion/life/moving_in.py)."""
    from companion.life import long_distance, moving_in
    return bool(together_now(connection, companion, now) or long_distance.visiting(connection, companion, now)
                or moving_in.home_state(connection, companion, now))


def outing_today(connection, companion: dict, day: date, now: datetime) -> bool:
    """Plans with the user still to come today (a visit now would run into them)."""
    timezone = companion['version']['timezone']
    return any(outing['local_date'] == day.isoformat() and outings.state(outing, timezone, now) == 'planned'
               for outing in outings.in_force(connection, companion['active_timeline_id'], day.isoformat()))


# --- Settling a visit ------------------------------------------------------------------------------------------

def insert(connection, companion: dict, message_id: str, activity: str, place: dict, day: date, at: str, until: str,
           asked_day: date | None, timestamp: str) -> dict:
    outing_id = identifier()
    connection.execute(
        'INSERT INTO outings (id, companion_id, message_id, local_date, at_time, until_time, activity, asked_date, '
        'place, named, cost, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?)',
        (outing_id, companion['id'], message_id, day.isoformat(), at, until, activity,
         asked_day.isoformat() if asked_day else None, encode(place), timestamp))
    from companion.life import admin
    admin.make_room(connection, companion, day, at, parse(timestamp))
    return outings.get(connection, outing_id)


def place_for(connection, companion: dict, activity: str) -> dict:
    return your_place(connection) if activity in AT_YOURS else their_place(connection, companion)


def visit_now(connection, companion: dict, message_id: str, activity: str, now: datetime, timestamp: str,
              hours: float = VISIT_HOURS, knock: bool = False) -> dict:
    local = now.astimezone(zone(companion['version']['timezone']))
    place = {**place_for(connection, companion, activity), **({'knock': True} if knock else {})}
    return insert(connection, companion, message_id, activity, place, local.date(), local.strftime('%H:%M'),
                  end_of_visit(companion['version']['definition'], local, hours), None, timestamp)


def visit_later(connection, companion: dict, message: dict, activity: str, day: date | None, at: str | None,
                timestamp: str) -> dict | None:
    """A visit on a day named ("come over Friday?"): that day when they are free, else the nearest free one, the way
    outings move."""
    local_now = parse(message['created_at']).astimezone(zone(companion['version']['timezone']))
    found = outings.when_free(connection, companion, {'activity': activity, 'day': day, 'at': at, 'firm': False},
                              local_now)
    if not found:
        return None
    on, start = found
    return insert(connection, companion, message['id'], activity, place_for(connection, companion, activity), on,
                  start, outings.until(start, activity), day, timestamp)


def note(connection, message: dict, companion: dict, timestamp: str) -> bool:
    """A user message that asks for a visit, or ends the time together: settled before the reply is written (outings.py
    calls this for a message that is not asking to go out). True when it was one of those."""
    if not ACTIVE or message['role'] != 'user':
        return False
    now = parse(message['created_at'])
    if ended_by_words(connection, companion, message, now):
        return True
    from companion.life import long_distance
    if long_distance.note(connection, message, companion, timestamp):
        return True  # A weekend visit across the distance, or anything about visiting while one is under way.
    kind = asked(message['text'])
    from companion.life import moving_in
    if kind is not None and moving_in.living(connection, companion):
        return True  # Living together, nobody comes over: the 'where' section says they share a home.
    if kind is None or optional(connection, 'SELECT id FROM outings WHERE message_id=?', (message['id'],)) or \
            optional(connection, 'SELECT id FROM together_asks WHERE message_id=?', (message['id'],)):
        return kind is not None
    if together_now(connection, companion, now):
        return True
    return settle_ask(connection, companion, message, kind, now, timestamp)


def timing(text: str, local: datetime, day: date | None, at: str | None) -> str:
    """'now', 'later' (a day or a time named, or tonight asked in the afternoon) or 'someday' (no day at all)."""
    if (day and day != local.date()) or (at and at > (local + timedelta(hours=1)).strftime('%H:%M')):
        return 'later'
    if at or RIGHT_NOW.search(text):
        return 'now'
    if day is None and SOMEDAY.search(text):
        return 'someday'
    return 'later' if EVENING.search(text) and local.strftime('%H:%M') < EVENING_FROM else 'now'


def settle_ask(connection, companion: dict, message: dict, kind: str, now: datetime, timestamp: str) -> bool:
    """A visit asked for: now when they can, later on the day or time it names, or nothing yet for "sometime"."""
    from companion.life import long_distance
    activity = 'visit-in' if kind == 'door' else kind
    version = companion['version']
    local = now.astimezone(zone(version['timezone']))
    day = outings.day_in(message['text'], local.date(), own_plans.holiday_dates(connection, version['definition'],
                                                                                 local.date()))
    at, _said = own_plans.clock(message['text'])
    when = 'now' if kind == 'door' else timing(message['text'], local, day, at)
    far = long_distance.far(connection, companion)
    if when == 'someday' and not far:
        return True  # "Come over sometime next week?": the reply is free to say when; nothing is settled yet.
    if when == 'later' and far and (day or at):
        # "Come over Saturday?" from another city: a weekend visit, when one works.
        return long_distance.request(connection, companion, message, long_distance.HOST if activity == 'visit-in'
                                     else long_distance.TO_YOU, day or local.date(), timestamp)
    if when == 'later' and not far:
        visit_later(connection, companion, message, activity, day or local.date(), at, timestamp)
        return True
    reason = why_not(connection, companion, now)
    if reason:
        return record(connection, companion, message, kind, reason, timestamp)
    visit_now(connection, companion, message['id'], activity, now, timestamp)
    return True


def record(connection, companion: dict, message: dict, kind: str, reason: dict, timestamp: str) -> bool:
    """A visit they had to say no to, so the reply says why."""
    connection.execute('INSERT INTO together_asks (id, companion_id, message_id, kind, reason, created_at) '
                       'VALUES (?, ?, ?, ?, ?, ?)', (identifier(), companion['id'], message['id'], kind,
                                                     encode(reason), timestamp))
    return True


def ended_by_words(connection, companion: dict, message: dict, now: datetime) -> bool:
    """The user saying goodbye while together ("I should head home"), or "not now" to a knock, ends it then."""
    found = together_now(connection, companion, now)
    if not found or found['ended_at']:
        return False
    knocked = found['place'].get('knock') and now - started(found, companion) < NOT_NOW_WINDOW
    if LEAVING.search(message['text']) or (knocked and NOT_NOW.search(message['text'])):
        connection.execute('UPDATE outings SET ended_at=? WHERE id=?', (stamp(now), found['id']))
        return True
    return False


def started(outing: dict, companion: dict) -> datetime:
    return outings.window(outing, companion['version']['timezone'])[0]


def turned_away(outing: dict, timezone: str) -> bool:
    """A knock sent home at once: nothing to remember together."""
    if not outing['place'].get('knock') or not outing['ended_at']:
        return False
    return parse(outing['ended_at']) - outings.window({**outing, 'ended_at': None}, timezone)[0] < NOT_NOW_WINDOW


# --- What the chat context says ---------------------------------------------------------------------------------

ASKED = {'visit-yours': 'you to come over to their place now', 'dinner-yours': 'you to come over to theirs for dinner',
         'visit-in': 'to come over to your place now', 'door': 'to be let in: they say they are at your door',
         'call': 'to talk on the phone now',  # On a call (companion/life/calls.py).
         # Long distance (companion/life/long_distance.py) and going out (outings.py) from another city.
         'weekend-to-you': 'you to come and stay with them for a weekend',
         'weekend-host': 'to come and stay with you for a weekend', 'out': 'to meet up and go out together'}


def reason_text(reason: dict) -> str:
    why = reason['why']
    if why == 'far':
        far = f", about {round(reason['km']):,} km away" if reason.get('km') else ''
        return f"you live in {reason['city']}{far}, so you can't just {'meet up' if reason.get('out') else 'come over'}"
    if why == 'busy':
        return f"you are at {reason['label']} until {reason['until']}"
    if why == 'asleep':
        return 'you were asleep when they asked'
    if why == 'away':
        return 'you are away on a trip'
    if why == 'out':
        return f"you are out ({reason['label']}) until about {reason['until']}"
    if why == 'plans':
        return 'you already have plans with them'
    if why in FAR_REASONS:
        return FAR_REASONS[why]
    return 'it is getting late for you, and you have an early night or work soon'


def context_lines(connection, companion: dict, now: datetime, fresh_ids: set[str]) -> list[tuple[str, str]]:
    """(identity, line) for the 'where' section: a visit they had to turn down in the turn being answered, and the
    time together the user just ended."""
    result = []
    if fresh_ids:
        marks = ','.join('?' * len(fresh_ids))
        for row in many(connection, f'SELECT * FROM together_asks WHERE message_id IN ({marks})', tuple(fresh_ids)):
            from companion.database import decode
            reason = decode(row['reason'])
            result.append((f"together-ask:{row['id']}",
                           f"- The user asked {ASKED[row['kind']]}. You can't: {reason_text(reason)}. Say so kindly in "
                           f"your own words, and suggest {'a weekend visit instead' if reason['why'] == 'far' else 'another time'}"
                           ' if you like. You are apart, texting.'))
    timezone = companion['version']['timezone']
    since = (now.astimezone(zone(timezone)).date() - timedelta(days=1)).isoformat()
    for outing in outings.in_force(connection, companion['active_timeline_id'], since):
        if not outing['ended_at'] or not timedelta(0) <= now - parse(outing['ended_at']) < TOLD_FOR:
            continue
        if turned_away(outing, timezone):
            line = ("- You dropped by the user's place, but they said now wasn't a good time, so you headed off. "
                    'Take it in stride. You are apart again, texting.')
        else:
            line = f"- {ENDED.get(outing['activity'], ENDED['out'])} You are apart again, texting."
        result.append((f"together-ended:{outing['id']}", line))
    return result


FAR_REASONS = {'money': "you can't afford the trip this pay period",
               'weekends': 'you have no free weekend in the next few weeks',
               'no-time': 'it is too far for just a weekend, and you have no time off coming up'}

ENDED = {'visit-yours': "You left the user's place a little while ago.", 'dinner-yours':
         "You left the user's place after dinner a little while ago.",
         'visit-in': 'The user headed home from your place a little while ago.',
         'dinner-in': 'The user headed home from your place a little while ago.',
         'out': 'You and the user said goodbye and headed home a little while ago.'}


# --- The state, in plain words ------------------------------------------------------------------------------------

def state(connection, companion: dict, now: datetime) -> dict:
    """{state: 'together'|'apart'|'call', kind, text, outing}: what the chat strip, the chat list and the Character page
    show. Apart in the same city says nothing; long distance says where and the time difference. On a call, or
    ringing, says so (companion/life/calls.py)."""
    from companion.life import calls, long_distance
    on_phone = calls.state(connection, companion, now)
    if on_phone:
        return {**on_phone, 'outing': None}
    weekend = long_distance.state(connection, companion, now)
    if weekend:
        return {**weekend, 'outing': None}  # A weekend visit across the distance, under way.
    found = together_now(connection, companion, now)
    if found and not found['ended_at']:
        return {'state': 'together', 'kind': kind_of(found), 'text': together_text(found, companion), 'outing': found}
    from companion.life import moving_in
    if at_home := moving_in.home_state(connection, companion, now):
        return {**at_home, 'outing': None}  # Both home of an evening, living together.
    between = where.between(connection, companion['version']['definition'])
    if between.known and between.long_distance:
        return {'state': 'apart', 'kind': 'long-distance', 'outing': None,
                'text': f"Long distance, {between.their_city['name']}{hours_apart(connection, companion, now)}"}
    return {'state': 'apart', 'kind': 'apart', 'text': '', 'outing': None}


def kind_of(outing: dict) -> str:
    if outing['place'].get('knock'):
        return 'knock'
    if outing['activity'] in AT_YOURS:
        return 'yours'
    return 'theirs' if outing['place']['kind'] == 'home' else 'out'


def together_text(outing: dict, companion: dict) -> str:
    """'Together at Lupa', 'At your place', "At Mira's place"."""
    place = outing['place']
    if outing['activity'] in AT_YOURS:
        return 'At your place'
    if place['kind'] == 'home':
        return f"At {companion['version']['definition']['name']}'s place"
    if outing['activity'] == 'wedding':
        return f"Your wedding at {place['name']}"
    if place.get('big_day') and place.get('title'):  # companion/life/big_days.py
        return f"At {place['title']} at {place['name']}"
    return f"Together at {place['name']}"


def hours_apart(connection, companion: dict, now: datetime) -> str:
    """', 5 hours ahead', ', 3 hours behind', or '' in the same time zone."""
    yours = now.astimezone(zone(settings(connection)['user_timezone'])).utcoffset()
    theirs = now.astimezone(zone(companion['version']['timezone'])).utcoffset()
    minutes = round((theirs - yours).total_seconds() / 60)
    if not minutes:
        return ''
    return f", {span_text(abs(minutes))} {'ahead' if minutes > 0 else 'behind'}"


def span_text(minutes: int) -> str:
    """'5 hours', '1 hour', '9½ hours' (India), '5 hours 45 minutes' (Nepal), '30 minutes'."""
    hours, rest = divmod(minutes, 60)
    if not hours:
        return f'{rest} minutes'
    if rest == 30:
        return f'{hours}½ hours'
    whole = f"{hours} hour{'s' if hours != 1 else ''}"
    return f'{whole} {rest} minutes' if rest else whole


def view(connection, companion: dict, now: datetime) -> dict:
    """The strip's state with what it can do: the outing (for Head home and Undo) under way, or just ended, and the
    call on, ringing or just over (companion/life/calls.py)."""
    found = state(connection, companion, now)
    outing = found.pop('outing')
    if outing is None:
        timezone = companion['version']['timezone']
        since = (now.astimezone(zone(timezone)).date() - timedelta(days=1)).isoformat()
        found_in = outings.in_force(connection, companion['active_timeline_id'], since)
        outing = next((item for item in found_in if outings.undoable_home(item, now)), None)
        if outing is None and found['state'] == 'apart':
            # Your wedding stays on the strip ("Married today at ...") for the rest of its day.
            today = now.astimezone(zone(timezone)).date().isoformat()
            outing = next((item for item in found_in if item['activity'] == 'wedding' and item['local_date'] == today
                           and outings.state(item, timezone, now) == 'done'), None)
        if outing:
            found = {**found, 'kind': kind_of(outing), 'text': together_text(outing, companion)}
    if outing:
        timezone = companion['version']['timezone']
        found['outing'] = {**outing, 'state': outings.state(outing, timezone, now),
                           'undo': outings.undoable_home(outing, now),
                           'not_now': bool(outing['place'].get('knock')) and now - started(outing, companion)
                           < NOT_NOW_WINDOW}
    else:
        found['outing'] = None
    from companion.life import calls, long_distance
    found['call'] = calls.view(connection, companion, now)
    found['visit'] = long_distance.view(connection, companion, now)
    from companion.life import moving_in
    found['home'] = moving_in.view_strip(connection, companion, now)  # Living together: home, or the user out.
    return found


# --- They come to you (first texts, companion/life/openers.py) ------------------------------------------------

def free_for(connection, companion: dict, now: datetime, hours: float) -> bool:
    return why_not(connection, companion, now, hours) is None


def close(connection, companion: dict, now: datetime) -> bool:
    from companion.memory import closeness
    return closeness.state(connection, companion, now)['level'] >= CLOSE


def knock_due(connection, companion: dict, now: datetime) -> list:
    """Now and then a close companion in the user's city turns up at their door unannounced, at a seeded minute on a
    seeded day, when they are free for a while. Saving the text starts the visit (`settle`)."""
    from companion.life.openers import Trigger
    chance = KNOCK_CHANCE.get(level(connection)) if ACTIVE and FIRST_TEXTS else None
    local = now.astimezone(zone(companion['version']['timezone']))
    if not chance or not KNOCK_HOURS[0] <= local.hour < KNOCK_HOURS[1]:
        return []
    key = f'knock:{local.date().isoformat()}'
    rng = random.Random(f"{companion['id']}:{key}")
    if rng.random() >= chance or local.hour * 60 + local.minute < rng.randint(KNOCK_HOURS[0] * 60,
                                                                              KNOCK_HOURS[1] * 60 - 30):
        return []
    found = where.your_home(connection)
    if not found or not free_for(connection, companion, now, KNOCK_HOURS_LONG) or not close(connection, companion, now) \
            or with_someone(connection, now) or lives_with_you(connection, companion):
        return []
    city, hood = found
    area = hood['name'] if hood else city['name']
    reason = (f"This is not a text. You are standing at the user's door right now, in person: you were out near "
              f"{area} with some time free and dropped by their place without telling them first. Write what you say "
              "when they open the door, spoken in person, short and warm, and leave them an easy way to say now isn't "
              'a good time.')
    template = rng.choice(KNOCKS)
    return [Trigger(key, 'drop_in', reason, template, ())]


def lives_with_you(connection, companion: dict) -> bool:
    """Living together (companion/life/moving_in.py): nobody knocks at their own door or asks to come over."""
    from companion.life import moving_in
    return bool(moving_in.living(connection, companion))


def with_someone(connection, now: datetime) -> bool:
    """The user is with a companion in person right now (out, at their place or at the user's, or staying with them):
    nobody knocks at a door the user is not behind, or turns up in the middle of someone else's visit."""
    from companion.characters import by_id
    for row in many(connection, 'SELECT id FROM companions'):
        other = by_id(connection, row['id'])
        if other and in_person(connection, other, now):
            return True
    return False


KNOCKS = ("Surprise! I was in the neighborhood and thought I'd knock. Is now okay, or is it a bad time?",
          "Hi! I was passing by and couldn't not knock. Got a minute, or should I come back another time?",
          "Knock knock. I was nearby and figured I'd say hi in person. Is this a good time?")


def suggest_due(connection, companion: dict, now: datetime) -> list:
    """Now and then, by the slider, a first text suggesting they get together: coming over to theirs tonight, or going
    out somewhere in their city on a free day soon. Saving the text settles the plan (`settle`)."""
    from companion.life.openers import Trigger
    chance = SUGGEST_CHANCE.get(level(connection)) if ACTIVE and FIRST_TEXTS else None
    version = companion['version']
    local = now.astimezone(zone(version['timezone']))
    if not chance or not SUGGEST_HOURS[0] <= local.hour < SUGGEST_HOURS[1]:
        return []
    window = local.date().toordinal() // SUGGEST_EVERY
    key = f'get-together:{window}'
    rng = random.Random(f"{companion['id']}:{key}")
    if rng.random() >= chance or where.between(connection, version['definition']).long_distance or \
            lives_with_you(connection, companion):
        return []
    if local.hour < 17 and rng.random() < 0.4:
        evening = local.replace(hour=19, minute=30, second=0, microsecond=0)
        if why_not(connection, companion, evening) is None:
            return [Trigger(key, 'get_together',
                            "You'd like to have the user over at your place tonight around 7:30, just to hang out. "
                            'Invite them in your own words.', 'Want to come over tonight? Nothing fancy, just hang out.',
                            ('visit-in', local.date().isoformat(), '19:30'))]
    return outing_suggestion(connection, companion, local, key, rng)


SUGGESTIONS = ('coffee', 'drinks', 'walk', 'dinner', 'lunch-out')


def outing_suggestion(connection, companion: dict, local: datetime, key: str, rng: random.Random) -> list:
    from companion.life.openers import Trigger
    definition = companion['version']['definition']
    data = outings.city_data(connection, definition)
    if not data:
        return []
    activity = rng.choice(SUGGESTIONS)
    wanted = {'activity': activity, 'day': local.date() + timedelta(days=rng.randint(1, 4)), 'at': None, 'firm': False}
    found = outings.when_free(connection, companion, wanted, local)
    if not found:
        return []
    day, at = found
    place = outings.pick_place(data, activity, day, at, definition, key, False)
    if not place:
        return []
    thing = outings.ACTIVITIES[activity][5]
    return [Trigger(key, 'get_together',
                    f"You'd like to see the user: suggest {thing} at {place['name']} on {day:%A} at {at}. Suggest it in "
                    'your own words, naming the place and the day.',
                    f"Want to {'go for' if activity == 'walk' else 'get'} {thing} at {place['name']} {day:%A}?",
                    (activity, day.isoformat(), at, place['id']))]


def settle(connection, companion: dict, message: dict, trigger, timestamp: str) -> dict | None:
    """The time together a first text started: a knock (a visit at the user's place from now), an invitation over
    tonight, or an outing it suggested."""
    now = parse(timestamp)
    if trigger.kind == 'drop_in':
        return visit_now(connection, companion, message['id'], 'visit-yours', now, timestamp, KNOCK_HOURS_LONG, True)
    activity, day, at = trigger.sources[0], date.fromisoformat(trigger.sources[1]), trigger.sources[2]
    if activity == 'visit-in':
        return insert(connection, companion, message['id'], activity, their_place(connection, companion), day, at,
                      outings.until(at, activity), None, timestamp)
    data = outings.city_data(connection, companion['version']['definition'])
    item = next((place for place in (data or {}).get('places', ()) if place['id'] == trigger.sources[3]), None)
    if not item or outings.taken(connection, companion, day):
        return None
    wanted = {'activity': activity, 'day': day, 'at': at, 'place': item, 'word': '', 'waterside': False}
    found = outings.save(connection, companion, message, wanted, data, day, at, timestamp)
    if found:
        connection.execute('UPDATE outings SET named=0 WHERE id=?', (found['id'],))
    return found


SETTLES = ('drop_in', 'get_together')
