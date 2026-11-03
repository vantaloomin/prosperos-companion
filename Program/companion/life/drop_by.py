"""Surprise visits (v1.3.1, tester 2026-11-03: "no way of going for a surprise visit ... in the pits"): the user drops by
the companion's home, or where they work, without asking first (the map's Drop by buttons).

Rules decide what happens, never the user and never the model, the way visits asked for in the chat are settled
(companion/life/together.py):
- Their home. Home and free, they open the door and it is a visit from now: an outing at their place, so the chat
  strip, Head home, the in-person scene and a shared memory work as for any meetup. How long it runs follows how close
  they are and their mood. Not home (at work, out, away on a trip) or asleep, nobody answers: the map card says so, and
  for a while their chat context knows the user came by. Home but with an early night or plans with the user later,
  or with things tense between them (companion/life/rough_patches.py, never on an easy life), they come to the door
  and say now isn't a good time.
- Their work: a place in their city that their job or routine names (companion/images/places.py `workplace`), only
  while they are on shift. They keep working while the user is there (`WORK`, a short outing that leaves their shift
  as it is), or step outside for a few minutes at places where visitors don't hang around (`STEP_OUT`).
They say the first words themselves, in person, as they open the door or look up from work: the model phrases it
from the facts given (as a knock at the user's door does, together.knock_due), with a fixed line when no model is set.
The Getting together slider (together.level) sets how much closeness and mood count: on an easy life (below 2) they
are always glad to see the user and it runs the full time.
"""
import random
from datetime import datetime, timedelta

from companion.clock import parse, stamp, zone
from companion.database import decode, encode, identifier, many, settings
from companion.errors import require
from companion.life import outings, pacing, routine, together, where

ACTIVE = True
WORK = 'visit-work'
HOME = 'home'
AT_WORK = 'work'
# Work places where visitors don't hang around the floor: they step outside for a few minutes instead.
STEP_OUT = ('workshop', 'docks', 'guildhall', 'vet')
# How long a visit at their place runs at most, by how it goes: close and glad, less close, or in a low mood.
HOME_HOURS = {'close': 3.0, 'warm': 1.5, 'low': 1.0}
# How long they can talk at work, in minutes: close, less close, a slammed week or a low mood, stepping out.
WORK_MINUTES = {'close': 45, 'warm': 30, 'short': 15, 'step-out': 15}
LEAST_WORK = timedelta(minutes=10)
# The chance they say not now at the door while things are tense (not on an easy life).
TENSE_TURN = 0.5
LOW = {'annoyed', 'hurt', 'angry', 'sad', 'anxious'}
# How long their chat context knows the user came by when it came to nothing.
TOLD_FOR = timedelta(hours=6)
# What the user may have found, for the map card and the chat context.
RESULTS = ('in', 'work', 'nobody', 'asleep', 'not-now')

GLAD = ('Oh! Hey, you. Come in, come in.', 'Well, look who it is. Get in here.',
        "You're here! What a nice surprise. Come on in.")
CAUGHT = ("Oh! Hi. I wasn't expecting anyone. Come in, excuse the mess.", 'Hey... this is a surprise. Come on in.')
AT_WORK_LINES = ("Hey! What are you doing here? Give me a sec, I'm in the middle of something.",
                 "Look who turned up. I can't stop, but stick around a bit.")
STEPPING_OUT = ("Hey! I can only step out for a few minutes, but hi.", "You came all the way here? I've got five "
                                                                         'minutes. Come on, outside.')


# --- Where they work --------------------------------------------------------------------------------------------

def workplace(connection, companion: dict) -> dict | None:
    """The city place they work at: the one their work block or the words of who they are name (images/places.py),
    else their employer by name (companion/life/work.py). None when nothing names one, or they have no job."""
    from companion.images import places
    from companion.life import work
    definition = companion['version']['definition']
    city = outings.city_data(connection, definition)
    if not city or not work.works(definition):
        return None
    label = next((block.label for block in routine.blocks(definition)[0] if block.kind == 'work'), '')
    if place := places.workplace(definition, city, label):
        return place  # Their own words first: the work block's label, or who they are.
    found = work.state(connection, companion['active_timeline_id'])
    return places.city_place(city, None, found['employer']) if found and found.get('employer') else None


def on_shift(connection, companion: dict, now: datetime) -> tuple[dict, str] | None:
    """(work block, until 'HH:MM' their time) while they are at work right now, not off sick or on a holiday."""
    found = pacing.block_now(connection, companion, now)
    if not found:
        return None
    block, ends_at = found
    if block['kind'] != 'work' or block.get('sick_day') or block.get('holiday') or block.get('with_user'):
        return None
    return block, parse(ends_at).astimezone(zone(companion['version']['timezone'])).strftime('%H:%M')


# --- What the map offers ------------------------------------------------------------------------------------------

def blocked(connection, companion: dict, now: datetime) -> str | None:
    """Why the user can't drop by anywhere of theirs right now, in the map card's words, or None."""
    from companion.life import calls, moving_in
    name = companion['version']['definition']['name']
    if where.between(connection, companion['version']['definition']).long_distance:
        return f'You live in different cities. A weekend visit is the way to see {name}.'
    if together.in_person(connection, companion, now):
        return f"You're with {name} right now."
    if calls.on_call(connection, companion, now):
        return f"You're on a call with {name}."
    if together.with_someone(connection, now):
        return "You're with someone else right now."
    if moving_in.living(connection, companion):
        return 'You live together.'
    return None


def offer(connection, companion: dict, now: datetime, at: str) -> dict:
    """{'ok', 'note', 'shift_until'} for the map card: whether Drop by is on offer, why not when nothing of theirs can
    be visited now (`note`), and at work the end of the shift they are on ('23:00', None off shift; the card says it in
    the user's clock style). At their home it is always on offer: whether they are in is found out by going."""
    if not ACTIVE:
        return {'ok': False, 'note': '', 'shift_until': None}
    reason = blocked(connection, companion, now)
    shift = on_shift(connection, companion, now) if at == AT_WORK else None
    return {'ok': reason is None and (at == HOME or shift is not None), 'note': reason or '',
            'shift_until': shift[1] if shift else None}


# --- Going -----------------------------------------------------------------------------------------------------

def tone(connection, companion: dict, now: datetime) -> str:
    """'close' (glad), 'warm' (a surprise, they let the user in), 'low' (a low mood shows) or 'tense'. Always 'close' on
    an easy life."""
    from companion import moods
    from companion.life import rough_patches
    if together.level(connection) < 2:
        return 'close'
    if rough_patches.tension(connection, companion, now):
        return 'tense'
    mood = moods.current(connection, f"companion:{companion['id']}", now)
    if mood and mood['feeling'] in LOW and mood['intensity'] >= 2:
        return 'low'
    return 'close' if together.close(connection, companion, now) else 'warm'


def roll(companion: dict, local: datetime, at: str) -> random.Random:
    """Seeded by the hour, so going again straight away finds the same thing."""
    return random.Random(f"{companion['id']}:drop-by:{at}:{local:%Y-%m-%dT%H}")


def decide(connection, companion: dict, at: str, now: datetime) -> dict:
    """What dropping by finds: {'result', 'text', 'place', 'until', 'tone', 'reason'} (RESULTS). Nothing is saved."""
    require(ACTIVE, 'Surprise visits are off.', 409)
    require(blocked(connection, companion, now) is None, blocked(connection, companion, now) or '', 409)
    local = now.astimezone(zone(companion['version']['timezone']))
    return home_visit(connection, companion, local, now) if at == HOME else work_visit(connection, companion, local, now)


def home_visit(connection, companion: dict, local: datetime, now: datetime) -> dict:
    name = companion['version']['definition']['name']
    reason = together.why_not(connection, companion, now)
    if reason and reason['why'] == 'busy' and on_shift(connection, companion, now):
        reason = {**reason, 'label': 'work'}  # "At work", not the block's own name ("Shift at Club Charles").
    if reason and reason['why'] in ('busy', 'out', 'away'):
        return {'result': 'nobody', 'reason': reason, 'text': nobody_text(name, reason)}
    if reason and reason['why'] == 'asleep':
        return {'result': 'asleep', 'reason': reason, 'text': f"No answer. The lights are off; {name} is asleep."}
    feeling = tone(connection, companion, now)
    if feeling == 'tense' and roll(companion, local, HOME).random() < TENSE_TURN:
        reason = {'why': 'tense'}
    if reason:  # 'plans', 'late' or 'tense': they come to the door.
        return {'result': 'not-now', 'reason': reason, 'text': not_now_text(name, reason)}
    hours = HOME_HOURS['close' if feeling == 'close' else 'low' if feeling in ('low', 'tense') else 'warm']
    until = together.end_of_visit(companion['version']['definition'], local, hours)
    return {'result': 'in', 'reason': None, 'tone': feeling, 'until': until, 'text': '',
            'place': {**together.their_place(connection, companion), 'surprise': True}}


def work_visit(connection, companion: dict, local: datetime, now: datetime) -> dict:
    from companion.life import work
    place = workplace(connection, companion)
    shift = on_shift(connection, companion, now)
    require(place is not None, 'They have no workplace on the map.', 404)
    require(shift is not None, "They're not at work right now.", 409)
    ends = shift[1]
    feeling = tone(connection, companion, now)
    step_out = place['kind'] in STEP_OUT
    slammed = work.week_of(connection, companion, local.date()) == 'slammed'
    minutes = WORK_MINUTES['step-out' if step_out else 'short' if slammed or feeling in ('low', 'tense') else
                           'close' if feeling == 'close' else 'warm']
    end = local + timedelta(minutes=minutes)
    shift_end = datetime.combine(local.date(), datetime.strptime(ends, '%H:%M').time(), local.tzinfo)
    if shift_end > local:
        end = min(end, shift_end)
    require(end - local >= LEAST_WORK, 'Their shift is nearly over.', 409)
    until = '23:59' if end.date() > local.date() else end.strftime('%H:%M')
    data = outings.city_data(connection, companion['version']['definition'])
    view = {**outings.place_view(place, data), 'surprise': True, 'step_out': step_out, 'slammed': slammed}
    return {'result': 'work', 'reason': None, 'tone': feeling, 'until': until, 'text': '', 'place': view}


def nobody_text(name: str, reason: dict) -> str:
    if reason['why'] == 'away':
        return f"Nobody's home. {name} is away on a trip."
    if reason['why'] == 'busy':
        return f"Nobody's home. {name} is at {reason['label']} until {reason['until']}."
    return f"Nobody's home. {name} is out until about {reason['until']}."


def not_now_text(name: str, reason: dict) -> str:
    why = {'plans': "they're getting ready for your plans later",
           'late': "it's late for them, and they have an early start",
           'tense': "now isn't a good time"}[reason['why']]
    return f'{name} comes to the door, but {why}.'


# --- What they say -------------------------------------------------------------------------------------------------

def trigger(companion: dict, found: dict, now: datetime):
    """The first words, for the model to phrase (companion/life/openers.py Openers.write), with a fixed line."""
    from companion.life.openers import Trigger
    local = now.astimezone(zone(companion['version']['timezone']))
    seed = roll(companion, local, found['result'])
    place, feeling = found['place'], found['tone']
    if found['result'] == 'in':
        mood = {'close': "You're glad to see them.", 'warm': "It's a surprise and you're a little caught off guard, "
                'but you let them in.', 'low': "You're not at your best right now, and it shows a little, but you let "
                'them in.', 'tense': 'Things are still a bit tense between you, but you let them in.'}[feeling]
        reason = (f"This is not a text. The user just turned up at your door, in person, without telling you first, "
                  f"and you opened it. {mood} They can stay until about {found['until']}. Write what you say as you "
                  'let them in, spoken in person, short.')
        return Trigger(f"drop-by:{local:%Y-%m-%dT%H:%M}", 'dropped_by', reason,
                       seed.choice(GLAD if feeling == 'close' else CAUGHT))
    if place['step_out']:
        how = (f"You can't have them inside, so you step out of {place['name']} for a few minutes to see them, and "
               f"you have to be back by {found['until']}.")
    else:
        how = f"You keep working while you talk; you can chat until about {found['until']}, then you get back to it."
    mood = {'close': "You're glad to see them.", 'warm': "It's a surprise.", 'low': "You're not at your best today.",
            'tense': 'Things are still a bit tense between you.'}[feeling]
    busy = ' It is a slammed week, so you are busier than usual.' if place['slammed'] else ''
    reason = (f"This is not a text. You are at work at {place['name']}, and the user just turned up "
              f"there, in person, without telling you first. {mood}{busy} {how} Write what you say when you see them, "
              'spoken in person, short.')
    return Trigger(f"drop-by:{local:%Y-%m-%dT%H:%M}", 'dropped_by', reason,
                   seed.choice(STEPPING_OUT if place['step_out'] else AT_WORK_LINES))


# --- Saving ------------------------------------------------------------------------------------------------------

def record(connection, companion: dict, at: str, found: dict, now: datetime, outing_id: str | None = None):
    connection.execute('INSERT INTO drop_bys (id, companion_id, timeline_id, place, result, reason, outing_id, '
                       'created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                       (identifier(), companion['id'], companion['active_timeline_id'], at, found['result'],
                        encode(found.get('reason') or {}), outing_id, stamp(now)))


def arrive(connection, companion: dict, at: str, found: dict, text: str | None, now: datetime) -> dict:
    """Save what dropping by found. Going in: their first words as a chat message in person, and the time together
    from now (an outing that message holds). Otherwise only the record their chat context reads."""
    if found['result'] not in ('in', 'work'):
        record(connection, companion, at, found, now)
        return {'result': found['result'], 'reason': found['reason'], 'text': found['text'], 'outing': None}
    from companion.life.openers import voiced
    text = text or voiced(trigger(companion, found, now).template, companion['version']['definition'])
    from companion.conversation import next_seq
    timestamp = stamp(now)
    timeline_id = companion['active_timeline_id']
    message_id = identifier()
    connection.execute(
        'INSERT INTO messages (id, timeline_id, seq, role, text, reply_to, status, active, character_version_id, '
        "memory_revision, created_at, completed_at) VALUES (?, ?, ?, 'companion', ?, NULL, 'complete', 1, ?, ?, ?, ?)",
        (message_id, timeline_id, next_seq(connection, timeline_id), text, companion['active_version_id'],
         settings(connection)['memory_revision'], timestamp, timestamp))
    local = now.astimezone(zone(companion['version']['timezone']))
    activity = 'visit-in' if found['result'] == 'in' else WORK
    outing = together.insert(connection, companion, message_id, activity, found['place'], local.date(),
                             local.strftime('%H:%M'), found['until'], None, timestamp) if activity == 'visit-in' else \
        work_outing(connection, companion, message_id, found, local, timestamp)
    record(connection, companion, at, found, now, outing['id'])
    return {'result': found['result'], 'text': '', 'outing': outing, 'message_id': message_id}


def work_outing(connection, companion: dict, message_id: str, found: dict, local: datetime, timestamp: str) -> dict:
    """At work: their shift stays as it is (no room made, and the agenda leaves it alone, outings.as_plans)."""
    outing_id = identifier()
    connection.execute(
        'INSERT INTO outings (id, companion_id, message_id, local_date, at_time, until_time, activity, asked_date, '
        'place, named, cost, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, 0, 0, ?)',
        (outing_id, companion['id'], message_id, local.date().isoformat(), local.strftime('%H:%M'), found['until'],
         WORK, encode(found['place']), timestamp))
    return outings.get(connection, outing_id)


# --- The chat context ----------------------------------------------------------------------------------------------

def context_lines(connection, companion: dict, now: datetime) -> list[tuple[str, str]]:
    """(identity, line) for the 'where' section: the user came by lately and found nobody in, or was turned away."""
    rows = many(connection, "SELECT * FROM drop_bys WHERE timeline_id=? AND result IN ('nobody', 'asleep', 'not-now') "
                'AND created_at>=? ORDER BY created_at', (companion['active_timeline_id'], stamp(now - TOLD_FOR)))
    timezone = companion['version']['timezone']
    result = []
    for row in rows[-2:]:
        at = parse(row['created_at']).astimezone(zone(timezone)).strftime('%H:%M')
        reason = decode(row['reason']) or {}
        if row['result'] == 'not-now':
            why = {'plans': 'you were getting ready for your plans with them later', 'late': 'it was late and you '
                   'have an early start', 'tense': 'things are tense between you'}.get(reason.get('why'), 'it was not '
                                                                                         'a good time')
            line = (f"- At {at} the user turned up at your door without telling you first. You came to the door but "
                    f'said now was not a good time ({why}), and they left. You are apart, texting.')
        else:
            away = 'you were asleep and did not hear the door' if row['result'] == 'asleep' else \
                f"you weren't home ({together.reason_text(reason)})"
            line = (f"- At {at} the user dropped by your place without telling you first, but {away}. You only know "
                    'if they tell you; if they do, react the way you would.')
        result.append((f"drop-by:{row['id']}", line))
    return result

