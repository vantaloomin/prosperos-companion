"""Away together (Hit List #86, v1.3): a trip the companion and the user take somewhere together.

Ask in the chat ("long weekend in Lisbon?", "let's go to Italy this summer", "we need a getaway") and the world goes
with you; now and then they plan one themselves. Rules decide, no model (Vanta approved the plan 2026-11-03):

- Where: a city the app ships that their world can travel to (companion/life/trips.py `fits`, or a ship's
  neighbours), else a destination of companion/world/destinations.py: a real one their year knew as a getaway, a
  getaway of their world's style (made-up worlds, ships and stations), or a place nobody knows ("the cabin by the
  lake"), stood in for by generic places of their era. A real place their world can't reach (Italy from Camelot, or
  from a ship) or that was no getaway yet in their year is turned down in the reply, in character. With no place
  named, the app picks one in season that fits what they like.
- How long: by the journey there (destinations.journey: plane, train, steamship, stagecoach, shuttle): a weekend
  or long weekend for somewhere close, five days or a week for somewhere far. A trip that takes workdays takes
  vacation days for them, moving planned ones (companion/life/work.py `moved`), as far as they have days to spare.
- When: the weekend asked ("next weekend", "in March", "this summer"), else the first that works from a few days
  ahead (two weeks for a week away), over about four months: free of work they can't take off, other trips,
  visits and outings, and affordable that pay period (companion/world/destinations.py `cost_share`; they pay their
  own share). When nothing works, the reply says why.
- Their own idea: weekends 8 to 22 days ahead (trips.plan_ahead), as often as the Getting together slider says, and
  only once they are close (closeness 4 and up). A first text tells the user (companion/life/long_distance.py
  `news_due`).

The trip is a trips row with visit 'together' (companion_id, dates, city, cost) and `away` saying how they travel
and what the place is like. It reads like the weekend visits of long_distance.py from there: the days are spent
there with the user (trips.block/entry), the chat is in person while it is under way, the status and Today show it,
and afterward it is a shared memory. The user can call it off before it starts (with Undo for 12 hours), change
where it goes, or head home early (with Undo for a few minutes).
"""
import re
from datetime import date, datetime, timedelta

from companion.clock import parse, stamp, zone
from companion.database import decode, encode, many, optional
from companion.errors import require
from companion.life import breakups, money, own_plans, routine, together, trips
from companion.world import catalog, destinations, generators, ships

ACTIVE = True
TOGETHER = 'together'
YOU = {'id': '~you', 'name': 'you', 'role': 'the user'}
# How many days a trip takes by the fewest nights the journey asks for (destinations.nights), and the spans around a
# Saturday that give them, in order of preference (offsets from the Saturday).
SPANS = {2: (range(0, 2),), 3: (range(-1, 2), range(0, 3)), 5: (range(0, 5), range(-2, 3)),
         7: (range(0, 7), range(-1, 6))}
# An ask is settled from this many days ahead (a week away from two weeks ahead), over this many weeks.
ASK_FROM, WEEK_FROM, ASK_WEEKS = 4, 14, 17
# Their own idea: days between trips together by the Getting together slider, the chance a free weekend brings one,
# more for a long weekend, and how close they must be.
GAP_DAYS = {1: 180, 2: 110, 3: 70}
CHANCE = {1: 0.05, 2: 0.1, 3: 0.18}
LONG = 1.6
PICKS = 4  # Places tried for their own idea before giving up on that weekend.
CLOSE = 4
SOON = 3  # Asked before closeness 3, it is a bit soon to go away together.
# A trip booked ahead is saved up for: this share of what they save each day until it starts.
SAVE_SHARE = 0.6
# Their own idea: they have been putting a little aside for a getaway for about this long.
FUND_DAYS = 60
# Heading home early can be undone for this long.
HOME_UNDO = timedelta(minutes=2)

# --- Reading the chat ---------------------------------------------------------------------------------------------

# Words that mean going away together, whatever place follows; and going somewhere, which counts only for a place
# the app knows (a destination or a city), so "go to the movies" stays an outing.
STRONG = re.compile(r"\b(?:get ?away|getaways?|vacation|vacay|holiday|weekend away|week away|long weekend|road ?trip|"
                    r"honeymoon|trip together|(?:go|run|get) away together|go on a trip|take a trip|travel together|"
                    r"little trip|weekend trip)\b", re.IGNORECASE)
GOING = re.compile(r"\b(?:trip|travel(?:l?ing)?|fly(?:ing)?|go(?:ing)?|head(?:ing)?|sail(?:ing)?|escape|"
                   r"take (?:me|you|us)|whisk (?:me|you)(?: away)?)\s+(?:away\s+|off\s+|abroad\s+|together\s+){0,2}"
                   r"(?:to|down to|up to|over to|out to)\s+", re.IGNORECASE)
# "A week in Cancún?": a stay somewhere, which counts like going (only for a place the app knows).
STAY = re.compile(r"\b(?:a|the)\s+(?:long\s+)?(?:week|weekend|few days|couple of days|night or two)\s+(?:in|on|at)\s+",
                  re.IGNORECASE)
PROPOSES = re.compile(r"\?|\b(?:let'?s|wanna|want to|we should|should we|how about|what about|can we|could we|"
                      r"i'?ll take you|take me|take you|plan|book|i want us|we could|would you|we need|i need)\b",
                      re.IGNORECASE)
PLACE = re.compile(r"\b(?:to|in|at|on)\s+([^,.!?;:()]+)", re.IGNORECASE)
STOP = re.compile(r"\s+\b(?:in|for|this|next|with|and|together|on|at|over|sometime|soon|someday|maybe|please|after|"
                  r"before|around|during|from|until|till|by (?:plane|train|car|boat|ship|bus|coach|air|sea|road|rail)|if|or|so|"
                  r"babe|baby|love|hun|honey|"
                  r"january|february|march|april|may|june|july|august|september|october|november|december|"
                  r"weekend|week|summer|winter|spring|fall|autumn|month|year|sometime)\b.*$", re.IGNORECASE)
LEAD = re.compile(r"^(?:(?:a|an)\s+)?(?:(?:little|long|quick|short)\s+)?(?:trip|weekend|week|getaway|vacation|holiday)"
                  r"(?:\s+(?:away|trip))?\s*", re.IGNORECASE)
MUNDANE = re.compile(r"^(?:the\s+|a\s+|my\s+|your\s+)?(?:store|shops?|supermarket|gym|office|work|school|class|"
                     r"bathroom|toilet|doctors?|dentist|hospital|mall|grocery|groceries|bank|post office|kitchen|bed|"
                     r"couch|dinner|lunch|breakfast|movies|cinema|bar|pub|club|party|sleep|it|that|this|you|me|"
                     r"there|here|town|place|house|home|yours|mine)\b", re.IGNORECASE)
SOMEWHERE = re.compile(r"\bsomewhere(?:\s+(\w+))?", re.IGNORECASE)
LEANINGS = {'warm': {'coast', 'islands'}, 'sunny': {'coast', 'islands'}, 'tropical': {'islands', 'coast'},
            'hot': {'coast', 'islands', 'desert'}, 'snowy': {'mountains'}, 'cold': {'mountains'},
            'quiet': {'countryside', 'lakes'}, 'romantic': {'old-town', 'wine', 'coast'}, 'new': set()}
MONTHS = ('january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october',
          'november', 'december')
SEASON_START = {'spring': (3, 15), 'summer': (6, 15), 'fall': (9, 15), 'autumn': (9, 15), 'winter': (12, 5)}
WHEN = re.compile(r"\b(?:in|this|next|over the|during|for)\s+(" + '|'.join(MONTHS) +
                  r"|spring|summer|fall|autumn|winter)\b", re.IGNORECASE)


def asked(text: str) -> dict | None:
    """A trip away together a user message proposes: {'place': the place words or '', 'strong': a word that means a
    trip}, from the first sentence that proposes one; None when none does."""
    text = own_plans.QUOTED.sub(' ', own_plans.ACTIONS.sub(' ', text)).replace('’', "'")
    for sentence in re.split(r'(?<=[.!?])\s+|\n+', text):
        if own_plans.PAST.search(sentence) or own_plans.NEGATED.search(sentence) or not PROPOSES.search(sentence):
            continue
        strong, going = STRONG.search(sentence), GOING.search(sentence) or STAY.search(sentence)
        if not strong and not going:
            continue
        start = min(found.start() for found in (strong, going) if found)
        return {'place': place_words(sentence[start:]), 'strong': bool(strong), 'sentence': sentence}
    return None


def place_words(text: str) -> str:
    """The place a trip ask names ("Lisbon" in "long weekend in Lisbon this spring?"), or ''."""
    for found in PLACE.finditer(text):
        words = LEAD.sub('', STOP.sub('', found.group(1).strip())).strip()
        words = ' '.join(words.split()[:5])
        if words and not MUNDANE.match(words) and not SOMEWHERE.match(words):
            return words
    return ''


def leaning(text: str) -> set[str]:
    """What kind of place "somewhere warm" asks for."""
    found = SOMEWHERE.search(text)
    return LEANINGS.get((found.group(1) or '').lower(), set()) if found else set()


def asked_day(text: str, today: date, holidays: dict) -> date | None:
    """The day a trip ask names: a date or weekend (long_distance.visit_day), else a month or season ("in March",
    "this summer"): its start, the next one to come."""
    from companion.life import long_distance
    found = long_distance.visit_day(text, today, holidays)
    if found:
        return found
    named = WHEN.search(text)
    if not named:
        return None
    word = named.group(1).lower()
    month, day = (MONTHS.index(word) + 1, 1) if word in MONTHS else SEASON_START[word]
    start = date(today.year, month, day)
    if word in MONTHS and today.month == month:
        return today
    if word in SEASON_START and today.month in season_months(word):
        return today
    return start if start >= today else date(today.year + 1, month, day)


def season_months(word: str) -> set[int]:
    return {'spring': {3, 4, 5}, 'summer': {6, 7, 8}, 'fall': {9, 10, 11}, 'autumn': {9, 10, 11},
            'winter': {12, 1, 2}}[word]


# --- Where to -----------------------------------------------------------------------------------------------------

def shipped(connection, home: dict, words: str) -> dict | None:
    """A city the app ships (or a pack or the user's own) that the words name and a trip from `home` reaches: the same
    world and era, or a ship's neighbour (trips.fits)."""
    known = ships.known_cities(connection)
    match = catalog.resolve(words, known) if words else None
    city = known.get(match['city']) if match else None
    if not city or city['id'] == home['id'] or not trips.fits(home, city):
        return None
    return city


def city_option(home: dict, city: dict) -> dict:
    """A shipped city as a destination option, with the way there."""
    link = next((link for found, link in ships.links(home, {city['id']: city})), None)
    option = {'key': None, 'name': city['name'], 'prep': 'in', 'character': character_of(city),
              'summary': city.get('summary', ''), 'best_months': list(range(1, 13)), 'city': city}
    if link:
        return option | {'by': ships.by(home, city) or link.get('by') or 'train', 'hours': link['hours']}
    if 'lat' in city and 'lat' in home:
        return option | {'lat': city['lat'], 'lon': city['lon']}
    return option | {'by': 'coach', 'hours': 8}


def character_of(city: dict) -> list[str]:
    tags = {tag for place in city.get('places', ()) for tag in place.get('tags', ())}
    kinds = {place['kind'] for place in city.get('places', ())}
    found = ['big-city'] + (['coast'] if 'beach' in kinds or tags & {'waterfront', 'harbor', 'harbour'} else [])
    return found


def resolve(connection, home: dict, ask: dict, year: int | None, seed: str, month: int,
            likes: set[str]) -> tuple[dict | None, str | None]:
    """(destination option, None) for an ask, or (None, why it can't be): 'elsewhere' a real place their world can't
    reach, 'not-yet' one that was no getaway yet in their year, 'nowhere' nothing to go to at all."""
    words = ask['place']
    city = shipped(connection, home, words)
    if city:
        return city_option(home, city), None
    if words:
        found = destinations.lookup(words, home, year)
        if found['why']:
            return None, found['why']
        if found['options']:
            return destinations.best_for(found['options'], month, seed, likes), None
        if ask['strong'] and not ships.enclosed(home):
            return destinations.unknown(words), None
        if not ask['strong']:
            return None, 'not-a-trip'
    leaning_to = leaning(ask['sentence']) or likes
    options = [item for item in reachable(home, year) if not leaning(ask['sentence'])
               or set(item['character']) & leaning_to]
    choice = destinations.best_for(options, month, seed, leaning_to)
    return (choice, None) if choice else (None, 'nowhere')


def reachable(home: dict, year: int | None, most: int = 7) -> list[dict]:
    """Destination options a trip of at most `most` days reaches from `home`."""
    return [item for item in destinations.options(home, year)
            if (nights := destinations.nights(destinations.journey(home, item, year))) and nights <= most]


def way_there(home: dict, option: dict, year: int | None) -> dict:
    return destinations.journey(home, option, year)


def city_id_of(home: dict, option: dict, year: int | None) -> str:
    return option['city']['id'] if option.get('city') else destinations.stand_in_id(option, home, year)


def prep_of(option: dict) -> str:
    """'on' for a coast, islands or a deck; else the option's own."""
    if option.get('prep') and option['prep'] != 'in':
        return option['prep']
    return 'on' if re.search(r'\b(?:coast|islands|riviera|banks|keys|deck|ring)\b', option['name'], re.I) else 'in'


# --- When ---------------------------------------------------------------------------------------------------------

def saturdays(first: date, weeks: int = ASK_WEEKS) -> list[date]:
    if first.weekday() == 6:
        first -= timedelta(days=1)
    first += timedelta(days=(5 - first.weekday()) % 7)
    return [first + timedelta(days=7 * week) for week in range(weeks)]


def span_for(connection, companion: dict, home: dict, saturday: date, count: int, today: date) -> list[date] | None:
    """The days of a trip of `count` days around `saturday` they can take: free of anything else, with the workdays
    among them covered by vacation days they have (planned ones, or ones a trip can move)."""
    from companion.life import long_distance, work
    definition = companion['version']['definition']
    if (definition.get('rota') or {}).get('kind') in long_distance.SWAPS:
        definition = {**definition, 'rota': None}  # Shifts are swapped and gigs turned down for a trip.
    for offsets in SPANS.get(count, SPANS[2]):
        days = [saturday + timedelta(days=offset) for offset in offsets]
        if days[0] <= today or trips.booked(connection, companion, days) or \
                long_distance.overlaps(connection, companion, days):
            continue
        if count == 2:
            vacation = work.vacation_dates(connection, companion, days[0] - timedelta(days=1),
                                           days[-1] + timedelta(days=1))
            days = trips.days_off(home, saturday, vacation)
            if trips.booked(connection, companion, days) or long_distance.overlaps(connection, companion, days):
                continue
        if takes_off(connection, companion, home, definition, days, today) is not None:
            return days
    return None


def takes_off(connection, companion: dict, home: dict, definition: dict, days: list[date],
              today: date) -> set[str] | None:
    """The workdays among `days` that need vacation days, or None when they don't have that many to spare."""
    from companion.life import work
    holidays = trips.public_holidays(home, days[0], days[-1])
    planned = work.vacation_dates(connection, companion, days[0], days[-1])
    schedule, _default = routine.blocks(definition)
    needed = {day.isoformat() for day in days for block in schedule if block.on(day) and block.kind in ('work', 'study')
              and day.isoformat() not in holidays and day.isoformat() not in planned}
    if any(block.kind == 'study' and block.on(date.fromisoformat(day)) for day in needed for block in schedule):
        return None  # Classes can't be taken off.
    for year in {date.fromisoformat(day).year for day in needed}:
        if sum(1 for day in needed if day.startswith(str(year))) > work.spare_vacation(connection, companion, year,
                                                                                         today):
            return None
    return needed


# --- Booking ------------------------------------------------------------------------------------------------------

def saved_by(definition: dict, today: date, first: date) -> float:
    """What they put aside for a trip between booking it and the day it starts."""
    found = money.profile(definition)
    if not found:
        return 0.0
    per_day = found.saving * (12 / 365 if found.period == 'month' else 1 / 7)
    return SAVE_SHARE * per_day * max(0, (first - today).days)


def plan(connection, companion: dict, home: dict, option: dict, days: list[date], year: int | None,
         message_id: str | None, seed: str, saved_from: date, credit: float = 0.0) -> dict | None:
    """The trip as a trips row, or None when they can't afford it then, with what they save up for it from
    `saved_from` (the day it is booked, or their getaway fund's start for their own idea), and `credit` back (the
    cost of the trip it replaces)."""
    definition = companion['version']['definition']
    way = way_there(home, option, year)
    share = destinations.cost_share(way, len(days))
    left = money.spendable(connection, companion['active_timeline_id'], definition, days[0]) + \
        saved_by(definition, saved_from, days[0]) + credit
    cost = trips.price(definition, share, days[0], left)
    if cost is None:
        return None
    city_id = city_id_of(home, option, year)
    city = option.get('city') or destinations.city(city_id)
    return {'start_date': days[0].isoformat(), 'end_date': days[-1].isoformat(), 'city_id': city_id,
            'city_name': option['name'], 'kind': 'getaway', 'company': dict(YOU),
            'landmark': trips.sight(city, seed) if city and city.get('places') else None,
            'sunny': bool(city and city.get('places')) and trips.sunny(city, days[min(1, len(days) - 1)]),
            'cost': cost, 'visit': TOGETHER, 'message_id': message_id,
            'away': {'prep': prep_of(option), 'by': way['by'], 'hours': way['hours'], 'key': option.get('key'),
                     'character': option['character'], 'country': option.get('country', '')}}


def book(connection, companion: dict, home: dict, option: dict, first: date, now: datetime, year: int | None,
         message_id: str | None, seed: str, weeks: int = ASK_WEEKS) -> tuple[dict | None, str]:
    """(trip, '') booked the first weekend from `first` that works, or (None, why not): 'too-far', 'no-time',
    'money'."""
    count = destinations.nights(way_there(home, option, year))
    if count is None:
        return None, 'too-far'
    today = now.astimezone(zone(companion['version']['timezone'])).date()
    why = 'no-time' if count > 3 else 'weekends'
    first = max(first, today + timedelta(days=WEEK_FROM if count > 3 else ASK_FROM))
    for saturday in saturdays(first, weeks):
        days = span_for(connection, companion, home, saturday, count, today)
        if not days:
            continue
        trip = plan(connection, companion, home, option, days, year, message_id, seed, today)
        if trip is None:
            why = 'money'
            continue
        trips.insert(connection, companion, trip, now)
        return trip, ''
    return None, why


def home_city(connection, companion: dict) -> dict | None:
    from companion.life import outings
    return outings.city_data(connection, companion['version']['definition'])


def note(connection, message: dict, companion: dict, timestamp: str) -> bool:
    """A user message proposing a trip away together, settled before the reply is written (together.note asks
    first): booked, or turned down with a reason the reply gives (together_asks). True when it was one."""
    if not ACTIVE or message['role'] != 'user':
        return False
    ask = asked(message['text'])
    if ask is None:
        return False
    if optional(connection, 'SELECT id FROM trips WHERE message_id=?', (message['id'],)) or \
            optional(connection, 'SELECT id FROM together_asks WHERE message_id=?', (message['id'],)):
        return True
    home = home_city(connection, companion)
    if home is None:
        return False
    now = parse(message['created_at'])
    today = now.astimezone(zone(companion['version']['timezone'])).date()
    year = destinations.year_of(home)
    definition = companion['version']['definition']
    first = asked_day(message['text'], today, own_plans.holiday_dates(connection, definition, today)) or today
    seed = f"away:{companion['active_timeline_id']}:{message['id']}"
    option, why = resolve(connection, home, ask, year, seed, first.month, likes(definition))
    if why == 'not-a-trip':
        return False  # "Go to <somewhere in town>": an outing, not a trip (outings.py).
    if why is None:
        why = refusal(connection, companion, now)
    if why is None:
        from companion.life import rough_patches
        if rough_patches.turned_down(connection, companion, message, 'trip', now):
            return True
        trip, why = book(connection, companion, home, option, first, now, year, message['id'], seed)
        if trip:
            return True
    # A real place out of reach aboard ship is said so (together.TRIP_REASONS 'aboard').
    reason = {'why': why, 'place': option['name'] if option else ask['place'],
              'aboard': why == 'elsewhere' and ships.enclosed(home)}
    return together.record(connection, companion, message, 'trip', reason, timestamp)


def refusal(connection, companion: dict, now: datetime) -> str | None:
    """Why they won't go away together at all for now: apart (a break, or exes), or too soon to know each other."""
    if breakups.apart(connection, companion):
        return 'apart'
    from companion.memory import closeness
    return 'too-soon' if closeness.state(connection, companion, now)['level'] < SOON else None


def likes(definition: dict) -> set[str]:
    """Kinds of place their interests lean to."""
    words = ' '.join(definition.get('interests') or ()).lower()
    found = set()
    for character, pattern in (('coast', r'beach|surf|swim|sail|ocean|sea'), ('mountains', r'hik|ski|climb|mountain'),
                               ('wine', r'wine|food|cook'), ('old-town', r'histor|art|museum|architect'),
                               ('big-city', r'music|club|theat|shop|fashion'), ('lakes', r'fish|kayak|canoe|row'),
                               ('countryside', r'garden|horse|farm|bird')):
        if re.search(pattern, words):
            found.add(character)
    return found


# --- Their own idea (trips.plan_ahead) ----------------------------------------------------------------------------

def decide(connection, companion: dict, home: dict, saturday: date, now: datetime) -> dict | None:
    """Whether they plan a trip away together that weekend, and where: the same answer for the same weekend."""
    chosen = together.level(connection)
    if not ACTIVE or not chosen or recent(connection, companion, saturday, GAP_DAYS[chosen]) or \
            refusal(connection, companion, now) or not together.close(connection, companion, now):
        return None
    timeline_id = companion['active_timeline_id']
    seed = f'away-plan:{timeline_id}:{saturday.isoformat()}'
    today = now.astimezone(zone(companion['version']['timezone'])).date()
    from companion.life import work
    vacation = work.vacation_dates(connection, companion, saturday - timedelta(days=1), saturday + timedelta(days=6))
    long_weekend = len(trips.days_off(home, saturday, vacation)) > 2
    if generators.unit(seed, 'go') >= CHANCE[chosen] * (LONG if long_weekend else 1):
        return None
    year = destinations.year_of(home)
    # A week away when their vacation week starts that Saturday, else a weekend somewhere close.
    week = sum(1 for offset in range(2, 7) if (saturday + timedelta(days=offset)).isoformat() in vacation) >= 4
    fund = min(today, saturday - timedelta(days=FUND_DAYS))
    options = affordable(connection, companion, home, reachable(home, year, 7 if week else 3), year, saturday, fund)
    for attempt in range(PICKS):
        # The place they like best that they can afford then: a few tries, cheapest last.
        option = destinations.best_for(options, saturday.month, f'{seed}:{attempt}',
                                       likes(companion['version']['definition']))
        if option is None:
            return None
        options = [item for item in options if item is not option]
        count = destinations.nights(way_there(home, option, year))
        days = span_for(connection, companion, home, saturday, count, today) if count else None
        trip = plan(connection, companion, home, option, days, year, None, seed, fund) if days else None
        if trip:
            return trip
    return None


def affordable(connection, companion: dict, home: dict, options: list[dict], year: int | None, saturday: date,
               fund: date, credit: float = 0.0) -> list[dict]:
    """The options they could pay their share of that weekend, with what they put aside from `fund` on."""
    definition = companion['version']['definition']
    left = money.spendable(connection, companion['active_timeline_id'], definition, saturday) + \
        saved_by(definition, fund, saturday) + credit
    found = []
    for item in options:
        way = way_there(home, item, year)
        count = destinations.nights(way)
        if count and trips.price(definition, destinations.cost_share(way, count), saturday, left) is not None:
            found.append(item)
    return found


def recent(connection, companion: dict, saturday: date, days: int) -> bool:
    """A trip together within `days` of that weekend, one the user called off included."""
    return bool(optional(connection, "SELECT id FROM trips WHERE timeline_id=? AND visit=? AND start_date>? AND "
                         "start_date<? AND (status='planned' OR cancelled_at IS NOT NULL)",
                         (companion['active_timeline_id'], TOGETHER, (saturday - timedelta(days=days)).isoformat(),
                          (saturday + timedelta(days=days)).isoformat())))


# --- Words for the rest of the app ---------------------------------------------------------------------------------

def away_of(trip: dict) -> dict:
    found = trip.get('away')
    return (decode(found) if isinstance(found, str) else found) or {}


def where_text(trip: dict) -> str:
    """'in Lisbon', 'on the Amalfi Coast', 'at the observation dome'."""
    return f"{away_of(trip).get('prep') or 'in'} {trip['city_name']}"


def travel_words(trip: dict) -> str:
    """' by plane', ' by steamship', or '' for a short way (a tram, a lift)."""
    by = away_of(trip).get('by') or ''
    return '' if not by or by in destinations.CHEAP_WAYS else f' by {by}'


def day_slots(connection, companion: dict, slots: list[dict]) -> list[dict]:
    """Today's day strip (life/routes.py `read_routine`): on a day away together, their waking hours are one block,
    "Away in Lisbon", in place of the routine (Iris 2026-11-03)."""
    if not slots:
        return slots
    rows = many(connection, "SELECT * FROM trips WHERE timeline_id=? AND visit=? AND status='planned' AND start_date<=? "
                'AND end_date>=?', (companion['active_timeline_id'], TOGETHER, slots[-1]['local_date'],
                                    slots[0]['local_date']))
    result = []
    for slot in slots:
        trip = next((row for row in rows if row['start_date'] <= slot['local_date'] <= row['end_date']), None)
        if trip is None or slot['block']['kind'] == 'sleep':
            result.append(slot)
            continue
        if result and result[-1]['block'].get('trip') == trip['id'] and result[-1]['ends_at'] == slot['starts_at']:
            result[-1] = {**result[-1], 'ends_at': slot['ends_at']}
            continue
        block = {**slot['block'], 'key': 'away', 'label': f'Away {where_text(trips.view(trip))}', 'kind': 'away',
                 'trip': trip['id']}
        result.append({**slot, 'key': f"away@{slot['local_date']}", 'block': block})
    return result


# --- What the user can change (Today) -------------------------------------------------------------------------------

def owned(connection, companion: dict, trip_id: str) -> dict:
    row = optional(connection, 'SELECT * FROM trips WHERE id=? AND visit=?', (trip_id, TOGETHER))
    require(row is not None and row['timeline_id'] == companion['active_timeline_id'], 'That trip was not found.', 404)
    return row


def elsewhere(connection, companion: dict, trip_id: str, now: datetime) -> dict:
    """Somewhere else, the same days: another place the same journey reaches in that time, picked by the app."""
    row = owned(connection, companion, trip_id)
    today = now.astimezone(zone(companion['version']['timezone'])).date()
    require(row['status'] == 'planned' and row['start_date'] > today.isoformat(),
            'Only a trip still to come can go somewhere else.', 409)
    home = home_city(connection, companion)
    require(home is not None, 'There is nowhere else to go from here.', 409)
    year = destinations.year_of(home)
    days = (date.fromisoformat(row['end_date']) - date.fromisoformat(row['start_date'])).days + 1
    start = date.fromisoformat(row['start_date'])
    options = affordable(connection, companion, home, [
        item for item in reachable(home, year, max(days, 2)) if item['name'] != row['city_name']
        and (destinations.nights(way_there(home, item, year)) or 99) <= days], year, start, today, row['cost'] or 0.0)
    seed = f"away-elsewhere:{row['id']}:{row['city_name']}"
    option = destinations.best_for(options, date.fromisoformat(row['start_date']).month, seed,
                                   likes(companion['version']['definition']))
    require(option is not None, 'There is nowhere else that fits those days.', 409)
    span = [date.fromisoformat(row['start_date']) + timedelta(days=offset) for offset in range(days)]
    trip = plan(connection, companion, home, option, span, year, row['message_id'], seed, today, row['cost'] or 0.0)
    require(trip is not None, "They can't afford anywhere else for those days.", 409)
    connection.execute('UPDATE trips SET city_id=?, city_name=?, landmark=?, sunny=?, cost=?, away=? WHERE id=?',
                       (trip['city_id'], trip['city_name'], encode(trip['landmark']), int(trip['sunny']), trip['cost'],
                        encode(trip['away']), trip_id))
    # Its days are written again, in the new place (agenda.py).
    connection.execute("DELETE FROM life_agenda WHERE timeline_id=? AND status='upcoming' AND "
                       "json_extract(block, '$.trip')=?", (row['timeline_id'], trip_id))
    return trips.view(optional(connection, 'SELECT * FROM trips WHERE id=?', (trip_id,)))


def head_home(connection, companion: dict, trip_id: str, now: datetime) -> dict:
    """Cut a trip under way short: it ends today. Undone within HOME_UNDO."""
    row = owned(connection, companion, trip_id)
    today = now.astimezone(zone(companion['version']['timezone'])).date().isoformat()
    require(row['status'] == 'planned' and row['start_date'] <= today < row['end_date'],
            'Only a trip under way can end early.', 409)
    away = away_of(row) | {'was_end': row['end_date'], 'home_at': stamp(now)}
    connection.execute('UPDATE trips SET end_date=?, away=? WHERE id=?', (today, encode(away), trip_id))
    return trips.view(optional(connection, 'SELECT * FROM trips WHERE id=?', (trip_id,)))


def home_undoable(row: dict, now: datetime) -> bool:
    away = away_of(row)
    return bool(away.get('home_at')) and now - parse(away['home_at']) < HOME_UNDO


def stay_on(connection, companion: dict, trip_id: str, now: datetime) -> dict:
    """Take back heading home early."""
    row = owned(connection, companion, trip_id)
    require(home_undoable(row, now), 'That can no longer be undone.', 409)
    away = away_of(row)
    end = away.pop('was_end')
    away.pop('home_at', None)
    connection.execute('UPDATE trips SET end_date=?, away=? WHERE id=?', (end, encode(away), trip_id))
    return trips.view(optional(connection, 'SELECT * FROM trips WHERE id=?', (trip_id,)))


def settle_planned(connection, companion: dict, today: date) -> int:
    """Trips together still to come that can't happen any more (a breakup): called off."""
    if not breakups.apart(connection, companion):
        return 0
    rows = many(connection, "SELECT id FROM trips WHERE timeline_id=? AND visit=? AND status='planned' AND "
                'start_date>?', (companion['active_timeline_id'], TOGETHER, today.isoformat()))
    for row in rows:
        connection.execute("UPDATE trips SET status='cancelled' WHERE id=?", (row['id'],))
    return len(rows)
