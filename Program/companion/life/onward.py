"""Second location (Hit List #87, v1.3): a meetup in town moves on to a second place nearby when the first one ends.

Rules decide, no model. When an outing is made, fixed dice (seeded on the outing, so a reload never changes it) say
whether it will move on at its end time, as often as the Moving on slider says (life_settings.onward_realism: 0
never, 1 now and then, 2 true to life, 3 often), likelier when the first place closes by its kind at that hour (a park
at dusk) and when the first place is a date spot. It only can for a meetup out in town (not at either home, not a time
other people set), when they have the time after it (no work, study, sleep or appointment starting) and a fitting place
is open then and in season. The next place follows what came first and the part of the day (a walk, then dinner;
dinner, then drinks), is picked from the city data the outing used (so it fits the era and the world), around the
corner rather than across town (the weights of companion/life/next_place.py), toward their likes, within their money.

The user overrides afterward, never before: Stay longer keeps them where they are; Somewhere else (Today) has them
pick another next place; Undo, just after the move, goes back; Head home ends it. Asking in the chat while out
together ("a drink after this?", "let's get out of here") moves them on, after this place or now, instead of booking a
new outing for another day.

Kept on the outing as `onward` (JSON):
- NULL: not decided yet (an outing from before 1.3; decided the next time the agenda extends).
- {'none': True}: it ends where it is ('stayed' when the user kept them there).
- {'place', 'activity', 'at', 'cost', 'rolls', 'asked', 'message_id', 'before'}: at `at` they move on to `place` for
  `activity`. The outing's until_time is then the end of the second place and its cost includes the second bill;
  `before` lists earlier places when the user asked to move on again after the move.
"""
import re
from datetime import date, datetime, timedelta

from companion.clock import parse, zone
from companion.database import encode, optional
from companion.errors import require
from companion.life import composer, money, routine
from companion.world import catalog, generators

ACTIVE = True  # Off in tests that are not about it (tests/conftest.py).
DEFAULT_LEVEL = 2
CHANCE = (0.0, 0.2, 0.4, 0.65)  # By the Moving on slider.
CLOSING = 0.25  # The first place closes by its kind at that hour.
DATE_SPOT = 0.1  # The first place is good for a date.
NONE = {'none': True}
# Outings that can move on: out in town. Not visits, dinner at their place, their people, a big day or the wedding.
GOES_ON = ('dinner', 'lunch-out', 'coffee', 'drinks', 'show', 'museum', 'walk', 'market', 'hobby')
# What comes next, by what came first: in the day, and of an evening.
DAYTIME = {'walk': ('coffee', 'lunch-out'), 'museum': ('coffee', 'lunch-out'), 'market': ('coffee', 'lunch-out'),
           'coffee': ('walk', 'museum', 'market'), 'lunch-out': ('walk', 'museum', 'market'),
           'hobby': ('coffee', 'lunch-out'), 'dinner': ('walk', 'coffee'), 'drinks': ('walk', 'coffee'),
           'show': ('coffee', 'walk')}
EVENING = {'dinner': ('drinks', 'walk'), 'show': ('drinks', 'dinner'), 'drinks': ('drinks', 'dinner'),
           'walk': ('dinner', 'drinks'), 'museum': ('dinner', 'drinks'), 'market': ('dinner', 'drinks'),
           'coffee': ('dinner', 'drinks'), 'lunch-out': ('drinks', 'walk'), 'hobby': ('drinks', 'dinner')}
# How long the second place lasts: shorter than a whole outing.
HOURS = {'dinner': 1.5, 'lunch-out': 1.0, 'coffee': 1.0, 'drinks': 1.5, 'show': 2.0, 'museum': 1.5, 'walk': 1.0,
         'market': 1.0}
SAME, CLOSE, ELSEWHERE = 3.0, 2.0, 1.0  # As companion/life/next_place.py.
NEAR_KM = 1.5
WARM = ('spring', 'summer')  # Seasons for a walk after dark.
SHOWN = timedelta(minutes=20)  # How long before the move the strip, Today and the companion know of it.
JUST = timedelta(minutes=30)  # How long after the move the scene says where they came from.
UNDO = timedelta(minutes=2)  # How long the move can be taken back.
LONGER = timedelta(hours=1)  # Staying on instead: an hour more where they are.
# Asking to move on now, not after this place.
NOW_WORDS = re.compile(r"\b(?:now|right now|instead|get out of here|somewhere else|move on|go on somewhere|"
                       r"head (?:somewhere|out))\b", re.IGNORECASE)
# Asking to move on without saying where to.
MOVE = re.compile(r"\b(?:get out of here|(?:go|head|move) (?:on )?(?:to )?somewhere else|somewhere else|move on|"
                  r"go on somewhere|head somewhere)\b", re.IGNORECASE)
NOT_OUTINGS = re.compile(r'\b(?:station|hospital|clinic|church|cathedral|chapel|campus|university|transit|airport|'
                         r'cemetery|school)\b', re.IGNORECASE)


def level(connection) -> int:
    row = optional(connection, 'SELECT onward_realism FROM life_settings WHERE id=1')
    return row['onward_realism'] if row and row['onward_realism'] in range(4) else DEFAULT_LEVEL


def hhmm(moment: datetime) -> str:
    return moment.strftime('%H:%M')


def plus(at: str, hours: float) -> str | None:
    """'21:00' plus 1.5 hours, or None past midnight."""
    end = datetime.combine(date(2000, 1, 1), datetime.strptime(at, '%H:%M').time()) + timedelta(hours=hours)
    return None if end.date() > date(2000, 1, 1) else hhmm(end)


# --- Reading it ---------------------------------------------------------------------------------------------------

def stop_of(outing: dict) -> dict | None:
    """The next place, when there is one (moved to or still to come)."""
    found = outing.get('onward') or {}
    return found if found.get('place') else None


def move_time(outing: dict, timezone: str) -> datetime:
    day = date.fromisoformat(outing['local_date'])
    return datetime.combine(day, datetime.strptime(stop_of(outing)['at'], '%H:%M').time(), zone(timezone))


def cut_off(outing: dict, timezone: str) -> bool:
    """They headed home before the move."""
    return bool(outing['ended_at']) and parse(outing['ended_at']) <= move_time(outing, timezone)


def moved(outing: dict, timezone: str, now: datetime) -> bool:
    return bool(stop_of(outing)) and not cut_off(outing, timezone) and now >= move_time(outing, timezone)


def here(outing: dict, timezone: str, now: datetime) -> dict:
    """The outing as it stands at `now`: before the move, at the first place until it ends there, with `next` once
    the move is near (SHOWN); after it, at the second place, with `came_from`."""
    stop = stop_of(outing)
    if not stop:
        return {**outing, 'next': None, 'came_from': None}
    if moved(outing, timezone, now):
        return {**outing, 'place': stop['place'], 'activity': stop['activity'], 'next': None,
                'came_from': {'name': outing['place']['name'], 'activity': outing['activity'],
                              'neighborhood': outing['place'].get('neighborhood', '')}, 'moved_at': stop['at']}
    soon = not cut_off(outing, timezone) and now >= move_time(outing, timezone) - SHOWN
    return {**outing, 'until_time': stop['at'], 'came_from': None,
            'next': {key: stop[key] for key in ('place', 'activity', 'at')} | {'asked': bool(stop.get('asked'))}
            if soon else None}


def final(outing: dict, timezone: str) -> dict:
    """Where the outing ended up: the second place once they moved on, else the first."""
    stop = stop_of(outing)
    if not stop or cut_off(outing, timezone):
        return outing
    return {**outing, 'place': stop['place'], 'activity': stop['activity']}


def undoable(outing: dict, timezone: str, now: datetime) -> bool:
    """Just moved on (UNDO), and not by the user's own ask."""
    stop = stop_of(outing)
    return bool(stop) and not stop.get('asked') and moved(outing, timezone, now) and \
        now - move_time(outing, timezone) < UNDO and outing['status'] == 'planned'


def then_text(outing: dict) -> str:
    """', then on to drinks at The Owl Bar' for an outing that moves on, else ''."""
    from companion.life import outings
    stop = stop_of(outing)
    if not stop:
        return ''
    return f", then on to {outings.ACTIVITIES[stop['activity']][5]} at {stop['place']['name']}"


def before_text(outing: dict) -> str:
    """The places before the first one, when the user moved them on again after the move ('dinner at Lupa, ')."""
    from companion.life import outings
    stop = stop_of(outing) or {}
    return ''.join(f"{outings.ACTIVITIES[item['activity']][5]} at {item['name']}, then "
                   for item in stop.get('before') or ())


# --- Deciding it ---------------------------------------------------------------------------------------------------

def qualifies(outing: dict) -> bool:
    place = outing['place']
    return outing['activity'] in GOES_ON and not place['id'].startswith('~') and not any(
        place.get(key) for key in ('knock', 'family', 'quiet', 'big_day')) and place.get('kind') not in (
        'home', 'your-home', 'family-home')


def options(activity: str, at: str, day: date | None = None) -> tuple[str, ...]:
    """What could come next; of an evening a walk only on a warm one (late spring and summer)."""
    evening = composer.day_part(at) in ('evening', 'late')
    found = (EVENING if evening else DAYTIME).get(activity, ('coffee', 'walk'))
    if evening and day and generators.SEASONS[day.month] not in WARM:
        found = tuple(name for name in found if name != 'walk') or ('drinks',)
    return found


def item_of(data: dict, place_id: str) -> dict | None:
    return next((item for item in data['places'] if item['id'] == place_id), None)


def closes(data: dict, outing: dict, day: date, at: str) -> bool:
    """The first place is not open at `at` by its kind (a park at dusk, a cafe of an evening)."""
    from companion.life import outings
    item = item_of(data, outing['place']['id'])
    return bool(item) and not outings.fits(item, day, at)


def chance(connection, data: dict, outing: dict) -> float:
    found = CHANCE[level(connection)]
    if not found:
        return 0.0
    day, at = date.fromisoformat(outing['local_date']), outing['until_time']
    item = item_of(data, outing['place']['id']) or {}
    return found + (CLOSING if closes(data, outing, day, at) else 0.0) + (
        DATE_SPOT if 'date' in item.get('good_for', ()) else 0.0)


def free(connection, companion: dict, day: date, at: str, end: str) -> bool:
    """Nothing of theirs (work, study, sleep, an appointment) holds `at` or starts before `end`."""
    from companion.life import outings
    schedule = routine.blocks(companion['version']['definition'])[0]
    return not outings.busy_at(schedule, day, at) and not outings.cut_short(schedule, day, at, end) and \
        not outings.booked(connection, companion, day, at)


def fitting(data: dict, activity: str, day: date, at: str, outing: dict) -> list[dict]:
    """Places for `activity` open at `at` and in season, other than where they are."""
    from companion.life import outings
    found = [item for item in data['places'] if item['kind'] in outings.kinds(activity) and
             outings.fits(item, day, at) and item['id'] != outing['place']['id']]
    if activity in ('museum', 'walk', 'show'):
        found = [item for item in found if not NOT_OUTINGS.search(item['name'])] or found
    return found


def closeness(data: dict, outing: dict, items: list[dict]) -> list[float]:
    """Three times as likely in the same neighbourhood, twice a short walk away (companion/life/next_place.py)."""
    hoods = {hood['id']: hood for hood in data['neighborhoods']}
    by_name = {hood['name']: hood for hood in data['neighborhoods']}
    start = by_name.get(outing['place'].get('neighborhood'))
    weights = []
    for item in items:
        hood = hoods.get(item.get('neighborhood'))
        if start and hood and hood['id'] == start['id']:
            weights.append(SAME)
        elif start and hood and 'lat' in start and 'lat' in hood and catalog.distance_km(start, hood) <= NEAR_KM:
            weights.append(CLOSE)
        else:
            weights.append(ELSEWHERE)
    return weights


def nearby(data: dict, outing: dict, activity: str, items: list[dict]) -> list[dict]:
    """Only the places in the same neighbourhood or a short walk away, when there are any, so the evening moves around
    the corner rather than across town; a walk is only ever nearby."""
    close = [item for item, weight in zip(items, closeness(data, outing, items)) if weight > ELSEWHERE]
    return close or ([] if activity == 'walk' else items)


def weights(data: dict, outing: dict, items: list[dict], definition: dict) -> list[float]:
    from companion.life import outings
    likes = outings.likes_of(definition)
    return [near * outings.leaning(item, likes) for near, item in zip(closeness(data, outing, items), items)]


def stop(connection, companion: dict, outing: dict, data: dict, at: str, *, activity: str | None = None,
         rolls: int = 0, place: dict | None = None, avoid: str = '') -> dict | None:
    """The next place from `at`: {'place', 'activity', 'at', 'until', 'cost', 'rolls'}, or None when nowhere fits or
    they have no time after."""
    from companion.life import outings
    day = date.fromisoformat(outing['local_date'])
    seed = f"onward:{outing['id']}:{rolls}"
    if place:
        activity = activity or outings.activity_for_place(place)
        items = [place]
    else:
        found = [(name, nearby(data, outing, name, [item for item in fitting(data, name, day, at, outing)
                                                    if item['id'] != avoid]))
                 for name in ((activity,) if activity else options(outing['activity'], at, day))]
        found = [(name, items) for name, items in found if items]
        if not found:
            return None
        # The first idea for that time of day is twice as likely as the next (dinner, then drinks before a walk).
        activity, items = generators.pick(seed, 'onward-activity', found, [2.0 if index == 0 else 1.0 for index in
                                                                            range(len(found))])
    return priced(connection, companion, outing, data, at, activity, items, seed, rolls)


def priced(connection, companion, outing, data, at, activity, items, seed, rolls) -> dict | None:
    """The pick among `items`, within their money, with its bill; None without the time for it."""
    from companion.life import outings
    definition = companion['version']['definition']
    day = date.fromisoformat(outing['local_date'])
    end = plus(at, HOURS.get(activity, 1.0))
    if end is None or not free(connection, companion, day, at, end):
        return None
    cost, affordable = outings.bill(definition, activity, day,
                                    money.spendable(connection, companion['active_timeline_id'], definition, day))
    if not affordable:
        items = [item for item in items if item.get('cost', '') in outings.CHEAP] or items
    item = generators.pick(seed, 'onward-place', items, weights(data, outing, items, definition))
    if item.get('cost') == 'free':
        cost = 0.0
    return {'place': outings.place_view(item, data), 'activity': activity, 'at': at, 'until': end, 'rolls': rolls,
            'cost': round(cost if affordable else cost * 0.6, 2)}


def decide(connection, companion: dict, outing: dict) -> dict:
    """Whether and where an outing moves on at its end: the onward JSON."""
    from companion.life import outings
    if not ACTIVE or not qualifies(outing):
        return NONE
    data = outings.city_data(connection, companion['version']['definition'])
    if not data or generators.unit(f"onward:{outing['id']}") >= chance(connection, data, outing):
        return NONE
    return stop(connection, companion, outing, data, outing['until_time']) or NONE


# --- Writing it ----------------------------------------------------------------------------------------------------

def write(connection, outing: dict, found: dict, *, until: str | None = None, longer: int = 0) -> None:
    """Keep `found` as the outing's onward, its end and bill following it."""
    old = stop_of(outing)
    cost = outing['cost'] - (old['cost'] if old else 0.0) + (found.get('cost') or 0.0)
    end = until or found.get('until') or (old['at'] if old else outing['until_time'])
    kept = {key: value for key, value in found.items() if key != 'until'}
    connection.execute('UPDATE outings SET onward=?, until_time=?, cost=?, longer=longer+? WHERE id=?',
                       (encode(kept), end, round(max(cost, 0.0), 2), longer, outing['id']))


def plan(connection, companion: dict, outing_id: str) -> None:
    """Decide a new outing's next place (companion/life/outings.py save)."""
    from companion.life import outings
    outing = outings.get(connection, outing_id)
    if outing['onward'] is None:
        write(connection, outing, decide(connection, companion, outing))


def plan_due(connection, companion: dict, now: datetime) -> int:
    """Each time the agenda extends: decide outings not decided yet (from before 1.3), and let one go that no longer
    has the time after it (a shift was added). Cheap: no model."""
    from companion.life import outings
    if not ACTIVE:
        return 0
    timezone = companion['version']['timezone']
    since = (now.astimezone(zone(timezone)).date() - timedelta(days=1)).isoformat()
    changed = 0
    for outing in outings.in_force(connection, companion['active_timeline_id'], since):
        if outing['status'] != 'planned' or outings.state(outing, timezone, now) == 'done':
            continue
        if outing['onward'] is None:
            write(connection, outing, decide(connection, companion, outing))
            changed += 1
        elif (found := stop_of(outing)) and not found.get('asked') and outings.state(outing, timezone, now) == \
                'planned' and not free(connection, companion, date.fromisoformat(outing['local_date']), found['at'],
                                       outing['until_time']):
            write(connection, outing, NONE)
            changed += 1
    return changed


def replan(connection, companion: dict, outing_id: str) -> None:
    """The first place changed (Somewhere else before it starts): the next place is picked again near the new one."""
    from companion.life import outings
    outing = outings.get(connection, outing_id)
    found = stop_of(outing)
    if not found or found.get('asked'):
        return
    data = outings.city_data(connection, companion['version']['definition'])
    again = data and stop(connection, companion, outing, data, found['at'], activity=found['activity'],
                          rolls=found.get('rolls', 0))
    write(connection, outing, again or NONE)


def settle(connection, outing: dict, timezone: str) -> dict:
    """An outing that is over: headed home before the move, the second bill is not paid and nothing moved."""
    from companion.life import outings
    if stop_of(outing) and cut_off(outing, timezone):
        write(connection, outing, NONE, until=outing['until_time'])
        return outings.get(connection, outing['id'])
    return outing


# --- The user's overrides ------------------------------------------------------------------------------------------

def pending(outing: dict, timezone: str, now: datetime) -> bool:
    """A next place still to come."""
    return bool(stop_of(outing)) and not cut_off(outing, timezone) and now < move_time(outing, timezone)


def stay(connection, companion: dict, outing_id: str, now: datetime) -> dict:
    """Stay where they are instead (Stay longer before the move, or Undo just after it): an hour more there."""
    from companion.life import outings
    outing = outings.owned(connection, companion, outing_id)
    timezone = companion['version']['timezone']
    require(pending(outing, timezone, now) or undoable(outing, timezone, now),
            'They have already moved on.', 409)
    end = plus(stop_of(outing)['at'], LONGER.total_seconds() / 3600) or '23:59'
    write(connection, outing, {'none': True, 'stayed': True}, until=end, longer=1)
    return outings.get(connection, outing_id)


def elsewhere(connection, companion: dict, outing_id: str, now: datetime) -> dict:
    """The companion picks another next place before they move on."""
    from companion.life import outings
    outing = outings.owned(connection, companion, outing_id)
    found = stop_of(outing)
    require(pending(outing, companion['version']['timezone'], now), 'They have already moved on.', 409)
    data = outings.city_data(connection, companion['version']['definition'])
    require(data is not None, "Their city isn't known, so there is nowhere else to go.", 409)
    again = stop(connection, companion, outing, data, found['at'], rolls=found.get('rolls', 0) + 1,
                 avoid=found['place']['id'])
    require(again is not None, 'There is nowhere else open nearby.', 409)
    write(connection, outing, {**again, **{key: found[key] for key in ('asked', 'message_id', 'before')
                                           if key in found}})
    return outings.get(connection, outing_id)


def asked(connection, companion: dict, message: dict, wanted: dict | None, now: datetime) -> bool:
    """While out together, the user asks to go on somewhere ("a drink after this?", "let's get out of here"): they
    move on after this place, or now. True when it was such an ask (handled, even if there is no time for it), so no
    new outing is booked for another day."""
    from companion.life import together
    timezone = companion['version']['timezone']
    outing = together.together_now(connection, companion, now)
    today = now.astimezone(zone(timezone)).date()
    if not ACTIVE or not outing or outing['ended_at'] or not qualifies(here(outing, timezone, now)):
        return False
    if wanted is None and not MOVE.search(message['text']):
        return False
    if wanted and (wanted['day'] not in (None, today) or wanted['activity'] not in HOURS):
        return False
    move_on(connection, companion, outing, message, wanted, now)
    return True


def move_on(connection, companion: dict, outing: dict, message: dict, wanted: dict | None, now: datetime) -> None:
    from companion.life import outings
    timezone = companion['version']['timezone']
    data = outings.city_data(connection, companion['version']['definition'])
    if not data:
        return
    current = here(outing, timezone, now)
    if moved(outing, timezone, now):  # A third place: the second becomes where they are.
        outing = shift(connection, outing)
    local = now.astimezone(zone(timezone))
    at = hhmm(local) if NOW_WORDS.search(message['text']) else current['until_time']
    named = wanted.get('place') if wanted else None
    found = stop(connection, companion, outing, data, max(at, hhmm(local)),
                 activity=wanted['activity'] if wanted else None, place=named,
                 rolls=(stop_of(outing) or {}).get('rolls', 0) + 1)
    if found:
        write(connection, outing, {**found, 'asked': True, 'message_id': message['id'],
                                   'before': (outing.get('onward') or {}).get('before') or []})


def shift(connection, outing: dict) -> dict:
    """Make the place they moved on to the outing's own, keeping the first in `before`."""
    from companion.life import outings
    found = stop_of(outing)
    before = [*(found.get('before') or []), {'name': outing['place']['name'], 'activity': outing['activity']}]
    connection.execute('UPDATE outings SET place=?, activity=?, onward=? WHERE id=?',
                       (encode(found['place']), found['activity'], encode({'none': True, 'before': before}),
                        outing['id']))
    return outings.get(connection, outing['id'])


# --- What the companion knows (the "together" section) --------------------------------------------------------------

def walk_text(outing: dict, place: dict, connection, companion: dict) -> str:
    """'just around the corner', 'a short walk away', 'a short ride across town'."""
    from companion.life import outings
    if place.get('neighborhood') and place.get('neighborhood') == outing['place'].get('neighborhood'):
        return 'just around the corner'
    data = outings.city_data(connection, companion['version']['definition']) or {}
    hoods = {hood['name']: hood for hood in data.get('neighborhoods', ()) if 'lat' in hood}
    start, end = hoods.get(outing['place'].get('neighborhood')), hoods.get(place.get('neighborhood'))
    if start and end and catalog.distance_km(start, end) <= NEAR_KM:
        return 'a short walk away'
    return 'a short ride across town'


def lines(connection, companion: dict, outing: dict, now: datetime, fresh_ids: set[str]) -> list[tuple[str, str]]:
    """The chat context while out together: the next place coming up, the user's ask just settled, or having just
    moved on."""
    from companion.life import outings
    timezone = companion['version']['timezone']
    stop_found, result = stop_of(outing), []
    if not stop_found or cut_off(outing, timezone):
        return result
    shown = here(outing, timezone, now)
    what = outings.what({**outing, 'place': stop_found['place'], 'activity': stop_found['activity']})
    away = walk_text(outing, stop_found['place'], connection, companion)
    if stop_found.get('asked') and stop_found.get('message_id') in fresh_ids:
        when = 'now' if now >= move_time(outing, timezone) else f"after this, around {stop_found['at']}"
        result.append((f"outing:{outing['id']}:onward-asked",
                       f"- The user asked to go on somewhere and you agreed: {what}, {away}, {when}. Say so in this "
                       'reply, in your own words.'))
    elif shown['next'] and not stop_found.get('asked'):
        result.append((f"outing:{outing['id']}:onward",
                       f"- When you finish here around {stop_found['at']}, you feel like going on to {what}, {away}. "
                       'Bring it up yourself when it fits, as your own idea. If the user would rather stay, or go '
                       'home, that is fine.'))
    elif shown['came_from'] and now - move_time(outing, timezone) < JUST:
        result.append((f"outing:{outing['id']}:onward-moved",
                       f"- You just came over here from {shown['came_from']['name']} together, {away}."))
    return result
