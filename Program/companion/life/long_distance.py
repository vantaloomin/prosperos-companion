"""Long distance (Hit List #59, v0.12 Where you are): a companion whose city isn't the user's.

Living in different cities (companion/life/where.py `between`), they can't just meet up or come over: drop-in visits,
outings and invitations over stay with companions in the user's city (companion/life/together.py, outings.py). Instead,
now and then, a weekend visit is planned the way their own trips are (companion/life/trips.py, a trip row with `visit`
set): they come to stay with the user ('to-you') or the user comes to stay with them ('host'), picked by money and
vacation days. Vacation days around the weekend mean they have the time to travel; otherwise the two take turns; and
when they can't afford the fare this pay period, the user comes to them. Cities beyond a trip's reach get rarer,
longer visits (Thursday to Monday, when they are off those days), and calls carry the rest (companion/life/calls.py
rings more for them). How often follows the Getting together slider (life_settings.together_realism): never on their
own at 0, and a visit asked for in the chat ("come visit me?", "can I come see you next weekend?") is settled the same
way at any level: the weekend asked, or the next free one, and when none works the reply says why.

They tell the user about a visit the app planned (a first text, companion/life/openers.py). While it is under way they
are together in person (together.state, 'staying' or 'hosting'): the chat writes face to face, nothing is held, nobody
texts first or rings. Afterwards it is kept as a shared memory. The user can call one off before it starts (Today).

The time difference shows in when they text: their days follow their own clock and the user's quiet hours hold their
first texts, and the 'where' section tells the model how far apart they are and how many hours.
"""
import re
from datetime import date, datetime, timedelta

from companion.clock import parse, stamp, zone
from companion.database import encode, many, optional, settings
from companion.errors import require
from companion.life import money, own_plans, together, trips, where
from companion.world import catalog, generators

ACTIVE = True
# The first text about a visit the app planned; off in most tests (tests/conftest.py).
FIRST_TEXTS = True
TO_YOU, HOST = 'to-you', 'host'
YOU = {'id': '~you', 'name': 'you', 'role': 'the user'}
# Days between weekend visits by the Getting together slider, and the chance a free weekend after that brings one
# (more for a long weekend). Beyond a trip's reach, FAR_GAP times as long between them.
GAP_DAYS = {1: 70, 2: 42, 3: 28}
FAR_GAP = 2
CHANCE = {1: 0.25, 2: 0.4, 3: 0.6}
LONG = 1.5
# What the fare costs as a share of a month's take-home, within a trip's reach and beyond it (no hotel: they stay with
# the user), and what having the user to stay costs.
FARE_SHARE = 0.06
FAR_SHARE = 0.2
HOST_SHARE = 0.04
# Rota and freelance work (companion/life/shifts.py) bends around a visit: shifts swapped, gigs turned down.
SWAPS = ('rota', 'freelance')
# When they arrive on the first day and leave on the last.
ARRIVE, LEAVE = '11:00', '16:00'
# A visit asked for in the chat: the weekend asked or the next free one, from ASK_FROM days ahead, within ASK_WEEKS.
ASK_FROM, ASK_WEEKS = 4, 6
# Beyond a trip's reach, the days a visit can take around a Saturday, as offsets from it, in order of preference: five
# days (Thursday to Monday, or beside a week's vacation), else a four-day weekend (Friday to Monday).
FAR_SPANS = (range(-2, 3), range(0, 5), range(-3, 2), range(-1, 3))
LATER_WEEKEND = re.compile(r'\b(?:next weekend|(?:the )?weekend after next)\b', re.IGNORECASE)
# How long a visit is talked about before it comes, after it, and after the user called it off; how long the news of
# one the app planned can wait; how long calling it off can be undone.
AHEAD_DAYS = 21
AFTER = timedelta(days=2)
CALLED_OFF = timedelta(days=3)
NEWS_WITHIN = timedelta(days=3)
UNDO = timedelta(hours=12)

# The user asking them to come and stay, and asking to come and stay with them.
COME_TO_YOU = re.compile(r"\b(?:(?:come|coming) (?:and |to )?(?:visit|see|stay with) me|visit me|(?:come|fly|drive|take the "
                         r"train) (?:out|up|down|over) (?:here|to (?:see|visit) me)|come (?:out|up|down) (?:here|for "
                         r"the weekend))\b", re.IGNORECASE)
GO_TO_THEM = re.compile(r"\b(?:(?:can|could|should|may) i (?:come |fly |drive )?(?:out |up |down |over )?(?:to )?"
                        r"(?:visit|see|stay with) you|i(?:'?ll| will| could| should) (?:come|fly|drive) (?:out |up |down "
                        r"|over )?(?:to )?(?:visit|see) you|(?:let me|i want to|i wanna|i'?d love to) come (?:and )?(?:visit|see|"
                        r"stay with) you|(?:let me|i want to|i wanna) (?:visit|see) you (?:there|in person))\b", re.IGNORECASE)


def far(connection, companion: dict) -> where.Between | None:
    """How far apart they are, when they live in different cities; None in the same city or when it can't be told."""
    between = where.between(connection, companion['version']['definition'])
    return between if between.known and between.long_distance else None


def reachable(between: where.Between) -> bool:
    """A weekend visit can get from one city to the other at all: the same era and the same world, as trips travel
    (trips.fits: our world's real and invented towns mix, a made-up world's cities only among themselves)."""
    yours, theirs = between.your_city, between.their_city
    return bool(yours and theirs) and (trips.fits(yours, theirs) or trips.fits(theirs, yours))


def settle_moves(connection, companion: dict, today: date, now: datetime | None = None) -> where.Between | None:
    """`far` when a visit can bridge it. Visits still to come that no longer fit where the two of them live (one of
    them moved: the same city now, another city, or one a visit can't reach) are called off, and plans to meet in
    person that a move made long distance go to the next visit there, or are called off (`far_plans`)."""
    between = far(connection, companion)
    if between:
        far_plans(connection, companion, today, now)
    usable = between if between and reachable(between) else None
    rows = many(connection, "SELECT id, visit, city_id FROM trips WHERE timeline_id=? AND visit!='' AND "
                "status='planned' AND start_date>?", (companion['active_timeline_id'], today.isoformat()))
    for row in rows:
        city = usable and (usable.your_city if row['visit'] == TO_YOU else usable.their_city)
        if not city or city['id'] != row['city_id']:
            connection.execute("UPDATE trips SET status='cancelled' WHERE id=?", (row['id'],))
    return usable


def far_plans(connection, companion: dict, today: date, now: datetime | None) -> None:
    """Plans to meet in person, now that they live in different cities: on the first full day of the user's next stay
    with them when there is one (their city's places still fit), else called off. The place remembers which ('far'),
    so the chat context can have them say so."""
    from companion.life import outings
    when = now or datetime.combine(today, datetime.min.time().replace(hour=12), zone(companion['version']['timezone']))
    timezone = companion['version']['timezone']
    visits = many(connection, "SELECT visit, start_date, end_date FROM trips WHERE timeline_id=? AND visit!='' AND "
                  "status='planned' AND end_date>=? ORDER BY start_date", (companion['active_timeline_id'],
                                                                         today.isoformat()))
    stays = [row for row in visits if row['visit'] == HOST and row['start_date'] >= today.isoformat()]
    for outing in outings.in_force(connection, companion['active_timeline_id'], today.isoformat()):
        during = any(row['start_date'] <= outing['local_date'] <= row['end_date'] for row in visits)
        if during or outings.state(outing, timezone, when) != 'planned' or outing['place'].get('far') or \
                outing['activity'] in (*together.AT_YOURS, 'wedding'):
            continue  # Plans made for a visit are the visit's own; the wedding is in their city, whoever travels.
        stay = stays[0] if stays else None
        place = {**outing['place'], 'far': 'moved' if stay else 'off', 'far_on': today.isoformat(),
                 'was': outing['local_date']}
        if stay:
            day = min(date.fromisoformat(stay['start_date']) + timedelta(days=1), date.fromisoformat(stay['end_date']))
            connection.execute('UPDATE outings SET local_date=?, place=? WHERE id=?',
                               (day.isoformat(), encode(place), outing['id']))
        else:
            connection.execute("UPDATE outings SET status='cancelled', cancelled_at=?, place=? WHERE id=?",
                               (stamp(when), encode(place), outing['id']))


def next_stay(connection, companion: dict, today: date) -> date | None:
    """The first full day of the user's next stay with them in their city (a visit agreed and still to come), for a
    plan only their city has: meeting their people, the evening they propose. None when no stay is planned."""
    row = optional(connection, "SELECT start_date, end_date FROM trips WHERE timeline_id=? AND visit=? AND "
                   "status='planned' AND start_date>? ORDER BY start_date LIMIT 1",
                   (companion['active_timeline_id'], HOST, today.isoformat()))
    if row is None:
        return None
    return min(date.fromisoformat(row['start_date']) + timedelta(days=1), date.fromisoformat(row['end_date']))


def staying_on(connection, companion: dict, day: date) -> bool:
    """The user is staying with them in their city that day."""
    return bool(optional(connection, "SELECT id FROM trips WHERE timeline_id=? AND visit=? AND status='planned' AND "
                         'start_date<=? AND end_date>=?', (companion['active_timeline_id'], HOST, day.isoformat(),
                                                          day.isoformat())))


def free_during_stay(connection, companion: dict, day: date) -> bool:
    """Nothing else is planned with the user that day of their stay (the stay itself is no clash)."""
    return not optional(connection, "SELECT id FROM outings WHERE companion_id=? AND local_date=? AND status!='cancelled'",
                        (companion['id'], day.isoformat()))


def far_lines(connection, companion: dict, today: date) -> list[tuple[str, str]]:
    """Plans a move made long distance, for a few days: moved to the user's next stay, or off."""
    from companion.life import outings
    result = []
    for outing in outings.in_force(connection, companion['active_timeline_id'], (today - AFTER).isoformat(), True):
        place = outing['place']
        if not place.get('far') or (today - date.fromisoformat(place['far_on'])).days > CALLED_OFF.days:
            continue
        what = f"{outings.ACTIVITIES.get(outing['activity'], ('', '', '', '', '', 'meeting up'))[5]} at {place['name']}"
        was = trips.day_text(place['was'])
        if place['far'] == 'moved':
            line = (f"- You had planned {what} with the user on {was}. Now that you live in different cities, it has "
                    f"moved to {trips.day_text(outing['local_date'])}, while they stay with you. Mention it in your own "
                    'words if it comes up.')
        else:
            line = (f"- You had planned {what} with the user on {was}, but now that you live in different cities it "
                    "can't happen and is called off. Mention it kindly in your own words, without blame.")
        result.append((f"far-plan:{outing['id']}", line))
    return result


def settle_all(connection, now: datetime):
    """Right after the user or a companion moves: every companion's visits that no longer fit are called off."""
    from companion.characters import by_id
    for row in many(connection, 'SELECT id FROM companions'):
        companion = by_id(connection, row['id'])
        if companion and companion.get('version'):
            settle_moves(connection, companion, now.astimezone(zone(companion['version']['timezone'])).date(), now)


# --- Planning a visit -------------------------------------------------------------------------------------------

def decide(connection, companion: dict, home: dict, between: where.Between, saturday: date) -> dict | None:
    """Whether they plan a weekend visit with the user that weekend (trips.plan_ahead asks, weekends 8 to 22 days
    ahead), and which way; the same answer for the same weekend."""
    chosen = together.level(connection)
    if not ACTIVE or not chosen or recent(connection, companion, saturday, gap(chosen, between)):
        return None
    found = weekend(connection, companion, home, between, saturday)
    if not found:
        return None
    days, vacation = found
    seed = f"visit:{companion['active_timeline_id']}:{saturday.isoformat()}"
    if generators.unit(seed, 'go') >= CHANCE[chosen] * (LONG if len(days) > 2 else 1):
        return None
    direction = TO_YOU if vacation else turn(connection, companion, saturday, seed)
    return plan(connection, companion, home, between, days, direction) or \
        (plan(connection, companion, home, between, days, HOST) if direction == TO_YOU else None)


def gap(chosen: int, between: where.Between) -> int:
    return GAP_DAYS[chosen] * (1 if between.within_reach else FAR_GAP)


def recent(connection, companion: dict, saturday: date, days: int) -> bool:
    """A visit within `days` of that weekend, one the user called off included (they don't plan another at once)."""
    return bool(optional(connection, "SELECT id FROM trips WHERE timeline_id=? AND visit!='' AND start_date>? AND "
                         "start_date<? AND (status='planned' OR cancelled_at IS NOT NULL)",
                         (companion['active_timeline_id'],
                                                           (saturday - timedelta(days=days)).isoformat(),
                                                           (saturday + timedelta(days=days)).isoformat())))


def weekend(connection, companion: dict, home: dict, between: where.Between,
            saturday: date) -> tuple[list[date], set[str]] | None:
    """(days, vacation days among them) when they are free for a visit that weekend: the weekend with a holiday or
    vacation day beside it, or beyond a trip's reach five days around it (Thursday to Monday, or the weekend and the
    three days after or before it, which is how a week's vacation meets a weekend), else Friday to Monday."""
    from companion.life import work
    vacation = work.vacation_dates(connection, companion, saturday - timedelta(days=3), saturday + timedelta(days=4))
    if between.within_reach:
        days = trips.days_off(home, saturday, vacation)
        if between.km and between.km > trips.REACH_KM[min(len(days), 3)]:
            return None  # Too far for two days: only a long weekend reaches it.
        spans = [days]
    else:
        spans = [[saturday + timedelta(days=offset) for offset in offsets] for offsets in FAR_SPANS]
    for days in spans:
        if free_for(connection, companion, home, days, vacation):
            return days, vacation & {day.isoformat() for day in days}
    return None


def free_for(connection, companion: dict, home: dict, days: list[date], vacation: set[str]) -> bool:
    """No work or classes those days (holidays and vacation days off), and nothing else has them."""
    definition = companion['version']['definition']
    holidays = trips.public_holidays(home, days[0], days[-1]) | vacation
    if (definition.get('rota') or {}).get('kind') in SWAPS:
        # Shifts are swapped and gigs turned down for a visit: their usual week decides (companion/life/shifts.py).
        definition = {**definition, 'rota': None}
    return trips.free(definition, days, holidays) and not trips.booked(connection, companion, days) and \
        not overlaps(connection, companion, days)


def turn(connection, companion: dict, saturday: date, seed: str) -> str:
    """Whose turn it is to travel: the other way from the last visit, the first one seeded."""
    last = optional(connection, "SELECT visit FROM trips WHERE timeline_id=? AND visit!='' AND status='planned' AND "
                    'start_date<? ORDER BY start_date DESC LIMIT 1', (companion['active_timeline_id'],
                                                                      saturday.isoformat()))
    if last:
        return HOST if last['visit'] == TO_YOU else TO_YOU
    return TO_YOU if generators.unit(seed, 'way') < 0.5 else HOST


def plan(connection, companion: dict, home: dict, between: where.Between, days: list[date], direction: str,
         message_id: str | None = None) -> dict | None:
    """The visit as a trip row, or None when it is their turn to travel and they can't afford the fare."""
    definition = companion['version']['definition']
    left = money.spendable(connection, companion['active_timeline_id'], definition, days[0])
    if direction == TO_YOU:
        share = FARE_SHARE if between.within_reach else FAR_SHARE
        cost = trips.price(definition, share, days[0], left)
        if cost is None:
            return None
        city = between.your_city
    else:
        cost, city = trips.price(definition, HOST_SHARE, days[0], left) or 0.0, home
    return {'start_date': days[0].isoformat(), 'end_date': days[-1].isoformat(), 'city_id': city['id'],
            'city_name': city['name'], 'kind': 'getaway', 'company': dict(YOU), 'landmark': None,
            'sunny': bool(city.get('places')) and trips.sunny(city, days[1]), 'cost': cost, 'visit': direction,
            'message_id': message_id}


# --- Asked for in the chat --------------------------------------------------------------------------------------

def asked(text: str) -> str | None:
    """The visit a user message asks for across the distance: TO_YOU ("come visit me?"), HOST ("can I come see
    you?"), else None."""
    text = own_plans.QUOTED.sub(' ', own_plans.ACTIONS.sub(' ', text)).replace('’', "'")
    for sentence in re.split(r'(?<=[.!?])\s+|\n+', text):
        if own_plans.PAST.search(sentence) or own_plans.NEGATED.search(sentence) or \
                not together.ASKS.search(sentence):
            continue
        if GO_TO_THEM.search(sentence):
            return HOST
        if COME_TO_YOU.search(sentence):
            return TO_YOU
    return None


def note(connection, message: dict, companion: dict, timestamp: str) -> bool:
    """A user message asking for a weekend visit while they live apart, or anything about visiting while one is under
    way (nothing to settle then): settled before the reply is written (together.note asks first). True when it was."""
    if not ACTIVE:
        return False
    now = parse(message['created_at'])
    direction = asked(message['text'])
    if visiting(connection, companion, now):
        return bool(direction or together.asked(message['text']))
    if direction is None or far(connection, companion) is None:
        return False
    if optional(connection, 'SELECT id FROM trips WHERE message_id=?', (message['id'],)) or \
            optional(connection, 'SELECT id FROM together_asks WHERE message_id=?', (message['id'],)):
        return True
    local = now.astimezone(zone(companion['version']['timezone'])).date()
    day = visit_day(message['text'], local, own_plans.holiday_dates(connection, companion['version']['definition'],
                                                                    local))
    return request(connection, companion, message, direction, day, timestamp)


def visit_day(text: str, today: date, holidays: dict) -> date | None:
    """The day a visit ask names: a date ("the weekend of December 12", "in three weeks"), next weekend or the one
    after, this weekend; None when it names none."""
    from companion.life import outings
    found = own_plans.when(text, today, holidays)
    if found and found[0] >= today:
        return found[0]
    later = LATER_WEEKEND.search(text)
    if later:
        saturday = today - timedelta(days=1) if today.weekday() == 6 else today + timedelta(days=5 - today.weekday())
        return saturday + timedelta(days=14 if 'after' in later.group(0).lower() else 7)
    return outings.day_in(text, today, holidays)


def request(connection, companion: dict, message: dict, direction: str, day: date | None, timestamp: str) -> bool:
    """Book the visit the user asked for: the weekend of `day`, else the next free one they can afford within
    ASK_WEEKS. When none works the reply says why (together_asks)."""
    from companion.life import outings
    between = far(connection, companion)
    home = outings.city_data(connection, companion['version']['definition'])
    kind = f'weekend-{direction}'
    if between is None or home is None:
        return together.record(connection, companion, message, kind, {'why': 'weekends'}, timestamp)
    if not reachable(between):
        # No way between their worlds or eras (trips.fits): as far as any visit goes.
        return together.record(connection, companion, message, kind, {'why': 'far', 'city': between.their_city['name'],
                                                                      'km': between.km}, timestamp)
    local = parse(message['created_at']).astimezone(zone(companion['version']['timezone'])).date()
    why = 'weekends' if between.within_reach else 'no-time'
    for saturday in weekends(local, day):
        found = weekend(connection, companion, home, between, saturday)
        if not found or overlaps(connection, companion, found[0]):
            continue
        visit = plan(connection, companion, home, between, found[0], direction, message['id'])
        if visit is None:
            why = 'money'  # Not this pay period; maybe a later weekend.
            continue
        trips.insert(connection, companion, visit, parse(timestamp))
        return True
    return together.record(connection, companion, message, kind, {'why': why}, timestamp)


def weekends(today: date, day: date | None) -> list[date]:
    """The Saturdays to try: the weekend of the day asked (or the first far enough off) and the ones after it."""
    first = max(day or today, today + timedelta(days=ASK_FROM))
    if first.weekday() == 6:
        first -= timedelta(days=1)
    first += timedelta(days=(5 - first.weekday()) % 7)
    return [first + timedelta(days=7 * week) for week in range(ASK_WEEKS)]


def overlaps(connection, companion: dict, days: list[date]) -> bool:
    return bool(optional(connection, "SELECT id FROM trips WHERE timeline_id=? AND status='planned' AND start_date<=? "
                         'AND end_date>=?', (companion['active_timeline_id'], days[-1].isoformat(),
                                             days[0].isoformat())))


# --- Under way ------------------------------------------------------------------------------------------------

def visiting(connection, companion: dict, now: datetime) -> dict | None:
    """The weekend visit under way now: from their arrival on the first day until they leave on the last, by the clock
    of the city the visit is in (the user's when they come to stay, their own when the user does)."""
    if not ACTIVE:
        return None
    near = now.astimezone(zone(companion['version']['timezone'])).date()
    rows = many(connection, "SELECT * FROM trips WHERE timeline_id=? AND visit!='' AND status='planned' AND "
                'start_date<=? AND end_date>=? ORDER BY start_date', (companion['active_timeline_id'],
                                                                      (near + timedelta(days=1)).isoformat(),
                                                                      (near - timedelta(days=1)).isoformat()))
    for row in rows:
        local = now.astimezone(visit_zone(companion, row))
        today, clock = local.date().isoformat(), local.strftime('%H:%M')
        if row['start_date'] <= today <= row['end_date'] and not (today == row['start_date'] and clock < ARRIVE) \
                and not (today == row['end_date'] and clock >= LEAVE):
            return trips.view(row)
    return None


def visit_zone(companion: dict, trip: dict):
    """The time zone of the city a visit is in, else the companion's own."""
    city = catalog.cities().get(trip['city_id'])
    try:
        return zone(city['timezone']) if city and city.get('timezone') else zone(companion['version']['timezone'])
    except ValueError:
        return zone(companion['version']['timezone'])


def state(connection, companion: dict, now: datetime) -> dict | None:
    """{state, kind, text} while a visit is under way (together.state reads this), else None."""
    found = visiting(connection, companion, now)
    if not found:
        return None
    until = date.fromisoformat(found['end_date']).strftime('%A')
    if found['visit'] == TO_YOU:
        return {'state': 'together', 'kind': 'staying', 'text': f'Staying with you until {until}'}
    return {'state': 'together', 'kind': 'hosting', 'text': f"You're staying in {found['city_name']} until {until}"}


def view(connection, companion: dict, now: datetime) -> dict | None:
    """The visit the chat strip shows while it is under way."""
    found = visiting(connection, companion, now)
    if not found:
        return None
    return {'id': found['id'], 'direction': found['visit'], 'city_name': found['city_name'],
            'start_date': found['start_date'], 'end_date': found['end_date'], 'leave_at': LEAVE}


# --- What the chat context says -----------------------------------------------------------------------------------

def span(trip: dict) -> str:
    return f"{trips.day_text(trip['start_date'])} to {trips.day_text(trip['end_date'])}"


def what(trip: dict) -> str:
    if trip['visit'] == TO_YOU:
        return f"you are going to {trip['city_name']} to stay with the user"
    return f"the user is coming to {trip['city_name']} to stay with you"


def context_lines(connection, companion: dict, now: datetime, fresh_ids: set[str]) -> list[tuple[str, str]]:
    """(identity, line) for the 'where' section: the visit under way, or how far apart they live, the visits coming
    up (the one just agreed in the turn being answered first), one just over, and one the user called off."""
    found = visiting(connection, companion, now)
    if found:
        return [(f"visit:{found['id']}:now", scene(connection, companion, found, now))]
    between = far(connection, companion)
    result = [('long-distance', distance_line(connection, companion, between, now))] if between else []
    today = now.astimezone(zone(companion['version']['timezone'])).date()
    result.extend(far_lines(connection, companion, today))
    for trip in visits(connection, companion, today - AFTER, now):
        result.extend(visit_lines(trip, today, now, fresh_ids))
    return result


def visits(connection, companion: dict, since: date, now: datetime) -> list[dict]:
    rows = many(connection, "SELECT * FROM trips WHERE timeline_id=? AND visit!='' AND end_date>=? AND (status='planned' "
                'OR cancelled_at>?) ORDER BY start_date', (companion['active_timeline_id'], since.isoformat(),
                                                           stamp(now - CALLED_OFF)))
    return [trips.view(row) for row in rows]


def visit_lines(trip: dict, today: date, now: datetime, fresh_ids: set[str]) -> list[tuple[str, str]]:
    start, end = date.fromisoformat(trip['start_date']), date.fromisoformat(trip['end_date'])
    if trip['status'] == 'cancelled':
        return [(f"visit:{trip['id']}:off", f"- The user called off the weekend visit {span(trip)} ({what(trip)}). "
                 'Take it in stride.')]
    if end < today or (end == today and start < today):
        went = 'you went to stay with the user in' if trip['visit'] == TO_YOU else 'the user came to stay with you in'
        return [(f"visit:{trip['id']}:done", f"- You just spent a weekend together: {went} {trip['city_name']} "
                 f"({span(trip)}). You are apart again, texting.")]
    if start > today + timedelta(days=AHEAD_DAYS):
        return []
    lines = [(f"visit:{trip['id']}", f"- {span(trip)}: {what(trip)} for the weekend. It is booked.")]
    if trip['message_id'] in fresh_ids:
        lines.append((f"visit:{trip['id']}:booked", f"- You agreed to a weekend visit: {what(trip)}, {span(trip)}. "
                      'Confirm the dates in this reply, in your own words.'))
    return lines


def distance_line(connection, companion: dict, between: where.Between, now: datetime) -> str:
    """How far apart they live and the time difference."""
    km = f", about {round(between.km):,} km apart" if between.km else ''
    hours = offset(connection, companion, now)
    clock = f' and you are {together.span_text(round(abs(hours) * 60))} {"ahead of" if hours > 0 else "behind"} ' \
        'the user, so mind what time of day it is for each of you' if hours else ''
    keep = "you see each other on weekend visits now and then, and talk on the phone in between" if reachable(between) \
        else 'and no trip reaches that far; you keep in touch by phone and letters'
    joint = '; ' if reachable(between) else ', '
    return (f"- You live in {between.their_city['name']} and the user lives in {between.your_city['name']}{km}: you are "
            f"long distance{clock}. You can't just meet up or come over{joint}{keep}.")


def offset(connection, companion: dict, now: datetime) -> float:
    """Hours their clock is ahead of the user's (negative when behind)."""
    yours = now.astimezone(zone(settings(connection)['user_timezone'])).utcoffset()
    theirs = now.astimezone(zone(companion['version']['timezone'])).utcoffset()
    return (theirs - yours).total_seconds() / 3600


def scene(connection, companion: dict, trip: dict, now: datetime) -> str:
    """Being together for the weekend, in person."""
    from companion.life import outings
    until = f"{date.fromisoformat(trip['end_date']):%A} afternoon"
    if trip['visit'] == TO_YOU:
        home = where.your_home(connection)
        area = f" in {home[1]['name']}" if home and home[1] else ''
        there = now.astimezone(zone(settings(connection)['user_timezone'])).strftime('%H:%M')
        clock = f" It is {there} there." if offset(connection, companion, now) else ''
        first = (f"Right now you are in {trip['city_name']}, staying with the user at their place{area} for the "
                 f"weekend, until {until}.{clock}")
    else:
        first = (f"Right now the user is here in {trip['city_name']}, staying with you at your place for the weekend, "
                 f"until {until}.")
    return f'- {first} You are together, in person. {outings.IN_PERSON}'


# --- Telling the user (a first text, companion/life/openers.py) -------------------------------------------------

NEWS = {TO_YOU: ("Guess what, I'm coming to see you! {span}. I already booked it.",
                 "I'm coming to {city}! {span}, if that works for you. I can't wait."),
        HOST: ("Come stay with me {span}? I cleared the weekend, I'll show you around {city}.",
               "I want you here. {span}, come stay with me? I already have plans for us in {city}.")}


def news_due(connection, companion: dict, now: datetime) -> list:
    """A visit the app planned, told to the user soon after: what was booked, in their own words."""
    from companion.life.openers import Trigger
    if not ACTIVE or not FIRST_TEXTS:
        return []
    today = now.astimezone(zone(companion['version']['timezone'])).date()
    rows = many(connection, "SELECT * FROM trips WHERE timeline_id=? AND visit!='' AND status='planned' AND "
                'message_id IS NULL AND created_at>? AND start_date>? ORDER BY start_date LIMIT 1',
                (companion['active_timeline_id'], stamp(now - NEWS_WITHIN), today.isoformat()))
    if not rows:
        return []
    trip = trips.view(rows[0])
    days = f"{date.fromisoformat(trip['start_date']):%A %B} {date.fromisoformat(trip['start_date']).day} to " \
        f"{date.fromisoformat(trip['end_date']):%A %B} {date.fromisoformat(trip['end_date']).day}"
    if trip['visit'] == TO_YOU:
        reason = (f"You just booked a weekend visit: you are going to {trip['city_name']} to stay with the user, "
                  f"{days}. Tell them, glad about it, naming the days.")
    else:
        reason = (f"You'd love the user to come and stay with you in {trip['city_name']}, {days}, and you have kept "
                  'that weekend free. Invite them, naming the days.')
    template = generators.pick(f"visit-news:{trip['id']}", 'news', list(NEWS[trip['visit']])).format(
        span=days, city=trip['city_name'])
    return [Trigger(f"visit-news:{trip['id']}", 'visit_news', reason, template[0].upper() + template[1:],
                    (trip['id'],))]


# --- Afterwards ---------------------------------------------------------------------------------------------------

def stay_text(trip: dict, companion: dict) -> dict:
    """{subject, value} of the memory a visit leaves, as the user reads it on Memories and the scrapbook ("Mira came to
    stay with you in Baltimore"); the companion reads it the other way round (records.as_told)."""
    name, city = companion['version']['definition']['name'].split()[0], trip['city_name']
    start, end = date.fromisoformat(trip['start_date']), date.fromisoformat(trip['end_date'])
    span = f'{start:%A %B} {start.day} to {end:%A %B} {end.day}'
    if trip['visit'] == TO_YOU:
        return {'subject': f"{name}'s visit to {city}", 'value': f'{name} came to stay with you in {city}, {span}.'}
    return {'subject': f'Staying with {name} in {city}', 'value': f'You came to stay with {name} in {city}, {span}.'}


def finish_due(connection, companion: dict, now: datetime) -> int:
    """Visits that are over, kept as a shared memory. Cheap: no model."""
    from companion.memory import records
    today = now.astimezone(zone(companion['version']['timezone'])).date().isoformat()
    rows = many(connection, "SELECT * FROM trips WHERE timeline_id=? AND visit!='' AND status='planned' AND "
                'memory_id IS NULL AND end_date<?', (companion['active_timeline_id'], today))
    for trip in rows:
        fields = {**stay_text(trip, companion), 'layer': 'shared_experience', 'stated_at': stamp(now), 'applies_from': None, 'applies_until': None}
        memory, _created = records.insert(connection, companion, fields, now=stamp(now), origin='automatic')
        connection.execute('UPDATE trips SET memory_id=? WHERE id=?', (memory['id'], trip['id']))
    return len(rows)


# --- What the user can change (Today) -------------------------------------------------------------------------

def owned(connection, companion: dict, trip_id: str) -> dict:
    row = optional(connection, "SELECT * FROM trips WHERE id=? AND visit!=''", (trip_id,))
    require(row is not None and row['timeline_id'] == companion['active_timeline_id'], 'That visit was not found.', 404)
    return row


def cancel(connection, companion: dict, trip_id: str, now: datetime) -> dict:
    """Call off a weekend visit that has not started."""
    row = owned(connection, companion, trip_id)
    today = now.astimezone(zone(companion['version']['timezone'])).date().isoformat()
    require(row['status'] == 'planned' and row['start_date'] > today, 'Only a visit still to come can be called off.',
            409)
    connection.execute("UPDATE trips SET status='cancelled', cancelled_at=? WHERE id=?", (stamp(now), trip_id))
    return trips.view(optional(connection, 'SELECT * FROM trips WHERE id=?', (trip_id,)))


def undoable(row: dict, today: date, now: datetime) -> bool:
    """Called off a little while ago, and it has not come yet."""
    return bool(row.get('visit')) and row['status'] == 'cancelled' and bool(row.get('cancelled_at')) and \
        now - parse(row['cancelled_at']) < UNDO and row['start_date'] > today.isoformat()


def undo(connection, companion: dict, trip_id: str, now: datetime) -> dict:
    """Take back calling it off, while nothing else has taken those days."""
    row = owned(connection, companion, trip_id)
    today = now.astimezone(zone(companion['version']['timezone'])).date()
    require(undoable(row, today, now), 'That can no longer be undone.', 409)
    days = [date.fromisoformat(row['start_date']), date.fromisoformat(row['end_date'])]
    require(not overlaps(connection, companion, days) and not trips.booked(connection, companion, days),
            'Another plan has those days now.', 409)
    connection.execute("UPDATE trips SET status='planned', cancelled_at=NULL WHERE id=?", (trip_id,))
    return trips.view(optional(connection, 'SELECT * FROM trips WHERE id=?', (trip_id,)))
