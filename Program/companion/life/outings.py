"""Go somewhere together (Hit List #10): plans with the user play out at real places.

Rules decide and the model only phrases. When the user asks the companion out ("dinner Friday?", "want to go to
Lupa this weekend?", the map's "Suggest going together" line), the app settles it before the reply is written: the
companion says yes, on the day asked when they are free then and otherwise on the nearest free day, at the time
asked or a usual one for the outing, and picks a real place in their city that fits it, their tastes and what they
can spend this pay period. A place the user named is kept. A firm plan the companion makes in their own reply
("let's get drinks Saturday") is settled the same way when that day is free. Nothing asks the user first; Today's
"Out together" lets them call it off, send the companion's pick somewhere else, or head home early.

The plan takes its slot in the companion's agenda (companion/life/agenda.py) the way their own plans do, so their
day holds it and the life simulation tells it as an event. While it is under way the chat context says they are out
together in person, with the place, the spot inside it, dishes and prices from the city data and the weather (the
"together" section, shared with trips). When it ends the bill comes out of their budget (money.household), a memory
of it is kept, and with pictures in chat on a photo of it is made for the feed post its event joins.

An outing belongs to the message it came from, like a plan the companion made (companion/life/own_plans.py): it
holds on every timeline showing that message or a copy, and goes when the message does.
"""
import re
from datetime import date, datetime, timedelta

from companion import in_character
from companion.clock import parse, stamp, zone
from companion.database import decode, encode, identifier, many, optional
from companion.errors import require
from companion.life import composer, money, own_plans, routine
from companion.memory.extraction import SENTENCE
from companion.world import catalog, custom, generators, inside

# key: (words that name it, city place kinds, usual start, hours, money.COSTS key, how it reads)
ACTIVITIES = {
    'dinner': (r'dinner|supper|a bite|eat out|grab food', ('restaurant', 'tavern', 'inn'), '19:00', 2.0, 'dinner',
               'dinner'),
    'lunch-out': (r'lunch|brunch', ('cafe', 'restaurant', 'market'), '12:30', 1.5, 'lunch-out', 'lunch'),
    'coffee': (r'coffee|a cuppa|(?:get|grab|have|for) (?:a |some )?tea', ('cafe',), '10:30', 1.0, 'coffee', 'coffee'),
    'drinks': (r'drinks?|a beer|beers|cocktails?|a pint|some wine', ('bar', 'nightlife', 'tavern'), '20:00', 2.5,
               'drinks', 'drinks'),
    'show': (r'a show|concert|gig|a play|theat(?:er|re)|movies?|a film|the cinema|comedy', ('venue', 'stadium'),
             '19:30', 3.0, 'show', 'a show'),
    'museum': (r'museum|gallery|exhibit\w*|aquarium', ('museum', 'attraction', 'landmark'), '14:00', 2.5, 'museum',
               'a museum visit'),
    'walk': (r'walk|stroll|hike|picnic', ('park', 'garden', 'trail', 'beach', 'landmark'), '16:00', 1.5, 'walk',
             'a walk'),
    'market': (r'market|shopping', ('market', 'shopping'), '11:00', 1.5, 'market', 'a look around the shops'),
    # Dinner at the companion's place (companion/life/kitchen.py): found by HOSTED below, never by its own words.
    'dinner-in': (r'(?!x)x', ('home',), '19:00', 3.0, 'dinner-in', 'dinner at their place'),
    # One of their pastimes together (companion/life/hobbies.py): found by the words of the pastimes they have.
    'hobby': (r'(?!x)x', (), '18:30', 2.0, 'hobby', 'a pastime together'),
    # Visits (companion/life/together.py): found by its own words, never by these.
    'visit-in': (r'(?!x)x', ('home',), '19:00', 3.0, 'visit', 'time together at their place'),
    'visit-yours': (r'(?!x)x', ('your-home',), '19:00', 3.0, 'visit', "time together at the user's place"),
    'dinner-yours': (r'(?!x)x', ('your-home',), '19:00', 3.0, 'visit', "dinner at the user's place"),
    # Meeting their people (companion/life/their_people.py): planned by the app, never by these words.
    'meet-family': (r'(?!x)x', ('family-home',), '18:30', 3.0, 'dinner', 'dinner with their family'),
    'meet-friends': (r'(?!x)x', ('bar', 'nightlife', 'tavern'), '20:00', 3.0, 'drinks', 'drinks with their friends'),
    # Their wedding with the user (companion/life/wedding.py): planned by the app, never by these words. Its cost is
    # their share of the wedding, paid from savings.
    'wedding': (r'(?!x)x', ('venue', 'landmark', 'garden', 'park', 'restaurant', 'inn'), '15:00', 8.0, 'wedding',
                'your wedding'),
}
HOME = '~home'
FOOD = re.compile(r"\b(?:dinner|supper|eat|a meal|cook\w*|something to eat)\b", re.IGNORECASE)
# The user asking to come to theirs ("can I come over for dinner?", "dinner at your place Friday?", "cook for me?"),
# never the user having them over ("come to mine, I'll cook").
HOSTED_ASK = re.compile(r"\b(?:(?:at|to|over to|round to) (?:your place|yours|your apartment|your flat|your house)|"
                        r"(?:can|could|may|should|let) (?:i|me) (?:come|pop|swing|head)\b|"
                        r"cook (?:for me|me (?:dinner|something)|dinner for (?:me|us)|for us|together))", re.IGNORECASE)
USER_HOSTS = re.compile(r"\b(?:my place|to mine|at mine|my apartment|my flat|my house|i'?ll cook|i'?m cooking|"
                        r"i cook)\b", re.IGNORECASE)
# The companion having the user over ("come over for dinner Friday, I'll cook").
HOSTED_OFFER = re.compile(r"\b(?:come (?:over|round|by)|over to (?:my place|mine)|at my place|at mine|to my place|"
                          r"i'?ll cook (?:for you|you|dinner)|cook (?:for you|you dinner)|have you over)\b",
                          re.IGNORECASE)
# A plain "go out" or "a date" is dinner.
OUT = re.compile(r"\b(?:go out|hang out|get together|a date|date night|do something|meet up|grab something)\b",
                 re.IGNORECASE)
ASKING = re.compile(r"\b(?:let'?s|lets|we should|shall we|wanna|want to|would you like|do you want|you want to|"
                    r"how about|what about|are you free|you free|up for|care to|come with me|join me|"
                    r"go out with me|take you|treat you|can i come|could i come|can i join|could i join|tag along)\b", re.IGNORECASE)
TOGETHER = re.compile(r"\b(?:we|us|together|with me|you and me|you and i)\b", re.IGNORECASE)
# Staying in, a call or a story is not going out: "come over for dinner, I'll cook", "a movie on FaceTime", "want to
# hear about my coffee disaster?", "walk me through it".
STAY = re.compile(r"\b(?:my place|your place|my apartment|your apartment|at home|at mine|at yours|to mine|come over|stay in|"
                  r"i'?ll cook|cook(?:ing)? (?:for|dinner|together)|order in|takeout|take-out|facetime|video call|"
                  r"on (?:a )?call|stream (?:it|one|a)|netflix|walk (?:me|you|us) through|hear about|tell you about|"
                  r"what(?:'s| is) for (?:dinner|supper|lunch)|what (?:should|shall|do|can) we (?:have|eat|make|cook) "
                  r"for (?:dinner|supper|lunch|tonight))\b", re.IGNORECASE)
# "Sometime", "next time": a wish, not a plan for a day.
VAGUE = re.compile(r"\b(?:sometime|some time|soon|next time|one day|someday|one of these days|when you'?re back|"
                   r"at some point|again sometime)\b", re.IGNORECASE)
# A plan the companion makes in their own reply counts only when it is firm.
FIRM = re.compile(r"\b(?:let'?s|we should|we're going|we are going|i'll take you|i'm taking you)\b", re.IGNORECASE)
STARTS = re.compile(rf"^(?:{'|'.join(value[0] for value in ACTIVITIES.values())})\b", re.IGNORECASE)
SHORT = 6
# Run-on messages join an ask to other news with "also", "btw" or "anyway".
ASIDE = re.compile(r"\s+(?:also|btw|anyway|plus|oh and|and also)\s+", re.IGNORECASE)
WEEKEND = re.compile(r'\b(?:this|the) weekend\b', re.IGNORECASE)
NOT_BUSY = {'work', 'study', 'sleep'}
LOOK_DAYS = 7
RECENT = timedelta(hours=18)
CHEAP = {'', 'free', '$'}
UNDO = timedelta(minutes=2)  # How long heading home early can be taken back; nothing is kept until then.
SPOT = 'outing-spot'
# Meeting their people (companion/life/their_people.py): dinner with their family, drinks with their friends.
MEETUPS = ('meet-family', 'meet-friends')


def kinds(activity: str) -> tuple[str, ...]:
    return ACTIVITIES[activity][1]


def activity_for_place(place: dict) -> str:
    """What going to a named place means: dinner at a restaurant, drinks at a bar, a walk in a park."""
    return next((key for key, value in ACTIVITIES.items() if place['kind'] in value[1]), 'walk')


def city_data(connection, definition: dict) -> dict | None:
    extra = custom.all_cities(connection)
    for text in (definition.get('home_city'), definition.get('location')):
        if text and (found := catalog.resolve(text, extra)):
            return catalog.city(found['city'], extra)
    return None


def named_place(sentence: str, data: dict | None) -> dict | None:
    """A place in the companion's city the sentence names, longest name first."""
    if not data:
        return None
    for item in sorted(data['places'], key=lambda place: -len(place['name'])):
        if len(item['name']) >= 4 and re.search(rf"\b{re.escape(item['name'])}\b", sentence, re.IGNORECASE):
            return item
    return None


def asked(sentence: str, firm: bool, day: date | None) -> bool:
    """Whether a sentence asks to go somewhere together (or, from the companion, firmly says they will). A short
    question that starts with the outing and names a day ("Drinks Friday?") asks too."""
    if own_plans.PAST.search(sentence) or own_plans.NEGATED.search(sentence) or STAY.search(sentence):
        return False
    question = sentence.rstrip().endswith('?')
    if firm:
        return bool(FIRM.search(sentence)) and not question
    short = question and day is not None and len(sentence.split()) <= SHORT and bool(STARTS.match(sentence))
    return bool(ASKING.search(sentence)) or question and bool(TOGETHER.search(sentence)) or short


def which(sentence: str, place: dict | None) -> str | None:
    for key, value in ACTIVITIES.items():
        if re.search(rf'\b(?:{value[0]})\b', sentence, re.IGNORECASE):
            return key
    if place:
        return activity_for_place(place)
    return 'dinner' if OUT.search(sentence) else None


def word_for(sentence: str, activity: str) -> str:
    """The word that named the outing ("the aquarium", "a movie"), so the companion's pick can fit it."""
    found = re.search(rf'\b(?:{ACTIVITIES[activity][0]})\b', sentence, re.IGNORECASE)
    return found.group(0).lower() if found else ''


# What a place's name, summary or tags should say for the word asked; and places nobody goes out to.
WANTS = {'aquarium': r'aquarium', 'movie': r'cinema|film|movie|picture house|theat', 'film': r'cinema|film|movie|theat',
         'cinema': r'cinema|film|movie', 'concert': r'music|concert|hall|jazz|orchestra|symphony|band', 'gig': r'music|club|band',
         'play': r'theat|play|stage|playhouse', 'theat': r'theat|play|stage', 'comedy': r'comedy|club', 'gallery': r'gallery|art',
         'hike': r'trail|hike|hill|mountain', 'picnic': r'park|lawn|garden', 'brunch': r'brunch|breakfast|cafe|diner'}
# "By the harbor", "on the water": somewhere on the waterfront, going by the place's tags and its neighborhood
# (never a name that happens to say "Harbor", like Golden Harbor Chinese up in the plaza).
WATERSIDE = re.compile(r"\b(?:by|on|along|near|at|beside|overlooking) the (?:harbou?r|water(?:front)?|beach|sea|seaside|"
                       r"ocean|shore|bay|river|lake|wharf|pier|docks?|marina|coast|cove)\b", re.IGNORECASE)
WATER_WORDS = re.compile(r'water|harbou?r|beach|ocean|seaside|shore|river|lake|wharf|pier|^docks?$|marina|coast|cove|'
                         r'pond|marsh|island|lighthouse|^sea$|boats?$', re.IGNORECASE)
WATER_KINDS = {'beach', 'docks'}
NOT_OUTINGS = re.compile(r'\b(?:station|hospital|clinic|church|cathedral|chapel|campus|university|transit|airport|'
                         r'terminal|ship|cemetery)\b', re.IGNORECASE)


def described(item: dict) -> str:
    return ' '.join([item['name'], item.get('summary', ''), *item.get('tags', ())])


def day_in(text: str, today: date, holidays: dict) -> date | None:
    if WEEKEND.search(text):
        return today if today.weekday() >= 5 else today + timedelta(days=5 - today.weekday())
    found = own_plans.when(text, today, holidays)
    return found[0] if found and found[0] >= today else None


def asking_clause(sentence: str) -> str | None:
    """The clause that asks to go out, when the sentence has others ("a walk Sunday also my sister ...")."""
    parts = [part for clause in own_plans.CLAUSES.split(sentence) for part in ASIDE.split(clause or '') if part]
    if len(parts) < 2:
        return None
    return next((part for part in parts if ASKING.search(part) or OUT.search(part) or any(
        re.search(rf'\b(?:{value[0]})\b', part, re.IGNORECASE) for value in ACTIVITIES.values())), None)


def day_asked(sentence: str, today: date, holidays: dict) -> date | None:
    """The day the ask names. A holiday named only outside the clause that asks ("a walk Sunday also my sister
    texted a seating chart for thanksgiving") sets the day only when nothing else does."""
    clause = asking_clause(sentence)
    if clause:
        near = {name: day for name, day in holidays.items()
                if re.search(rf"\b{re.escape(name)}\b", clause.replace("'", ''), re.IGNORECASE)}
        if found := day_in(sentence, today, near):
            return found
    return day_in(sentence, today, holidays)


def proposal(text: str, today: date, holidays: dict, data: dict | None, firm: bool = False,
             pastimes=()) -> dict | None:
    """{activity, day, at, place} for the first sentence of a message that asks to go out together. `pastimes` are
    the companion's own (companion/life/hobbies.py `patterns`): "want to go climbing Saturday?" is one of them."""
    text = own_plans.QUOTED.sub(' ', own_plans.ACTIONS.sub(' ', text)).replace('’', "'")
    sentences = [part.strip() for part in SENTENCE.findall(text)]
    for index, sentence in enumerate(sentences):
        day = day_asked(sentence, today, holidays) if sentence else None
        if sentence and (found := hosted(with_food(sentences, index, day), firm, day)):
            return found
        if not sentence or not asked(sentence, firm, day):
            continue
        place = named_place(sentence, data)
        pastime = next((found['id'] for found in pastimes if found['pattern'].search(sentence)), None)
        activity = 'hobby' if pastime else which(sentence, place)
        if activity is None:
            continue
        # "We should grab coffee sometime" is a wish; "How about a date sometime?" asks, and the companion picks the day.
        if day is None and (firm or VAGUE.search(sentence) and not sentence.rstrip().endswith('?')):
            return None
        at, _said = own_plans.clock(sentence)
        return {'activity': activity, 'day': day, 'at': at, 'place': None if pastime else place,
                'word': word_for(sentence, activity), 'waterside': bool(WATERSIDE.search(sentence)),
                'sentence': sentence[:300], 'hobby': pastime}
    return None


def with_food(sentences: list[str], index: int, day: date | None) -> str:
    """The sentence, read together with the next one when it names the day and the next one the food: "Want to come
    over Saturday? I'll cook." is one invitation."""
    sentence = sentences[index]
    after = sentences[index + 1] if index + 1 < len(sentences) else ''
    if day and after and not FOOD.search(sentence) and FOOD.search(after):
        return f'{sentence} {after}'
    return sentence


def hosted(sentence: str, firm: bool, day: date | None) -> dict | None:
    """Dinner at the companion's place: the user asking to come over, or the companion having them over on a named
    day (a question counts: it is an invitation)."""
    if own_plans.PAST.search(sentence) or own_plans.NEGATED.search(sentence) or not FOOD.search(sentence):
        return None
    if firm:
        if day is None or not HOSTED_OFFER.search(sentence):
            return None
    elif not HOSTED_ASK.search(sentence) or USER_HOSTS.search(sentence) or not (
            sentence.rstrip().endswith('?') or ASKING.search(sentence)):
        return None
    at, _said = own_plans.clock(sentence)
    return {'activity': 'dinner-in', 'day': day, 'at': at, 'place': None, 'word': '', 'waterside': False,
            'sentence': sentence[:300]}


def home_view(connection, companion: dict, day: date, outing_key: str, timestamp: str) -> dict:
    """Their place as an outing's place, with what they will make (companion/life/kitchen.py)."""
    from companion.life import home, kitchen
    definition, timeline_id = companion['version']['definition'], companion['active_timeline_id']
    now = parse(timestamp)
    kitchen.ensure(connection, timeline_id, definition, None, now)
    found = next((item for item in home.items_on(connection, timeline_id, day) if item['kind'] == 'home'), None)
    budget = money.profile(definition)
    data = city_data(connection, definition)
    return {'id': HOME, 'name': f"{definition['name']}'s place", 'kind': 'home',
            'neighborhood': budget.neighborhood if budget else '', 'summary': found['description'] if found else '',
            'cost': '', 'cuisine': '', 'city': data['name'] if data else '', 'city_id': data['id'] if data else '',
            'spots': ['at the kitchen table', 'in the kitchen'],
            'menu': kitchen.hosting(connection, timeline_id, definition, None, now, day, {'id': outing_key})}


def busy_at(schedule, day: date, at: str) -> bool:
    """Work, study or sleep holds this time of day in the routine."""
    for block in schedule:
        view = block.view()
        start_day = day - timedelta(days=1) if view['start'] > view['end'] and at < view['end'] else day
        if block.on(start_day) and view['kind'] in NOT_BUSY and own_plans.holds(view, at):
            return True
    return False


def cut_short(schedule, day: date, at: str, end: str) -> bool:
    """Work, study or sleep starts before the outing would be over (a shift at 3 for a museum at 2)."""
    return any(block.on(day) and block.view()['kind'] in NOT_BUSY and at < block.view()['start'] < end
               for block in schedule)


def taken(connection, companion: dict, day: date) -> bool:
    """Another outing, a trip away or a family tradition already has this day."""
    from companion.life import traditions, trips
    return bool(optional(connection, "SELECT id FROM outings WHERE companion_id=? AND local_date=? AND status!="
                         "'cancelled'", (companion['id'], day.isoformat()))) or \
        trips.away_on(connection, companion['id'], day) or traditions.busy(connection, companion, day, day)


def booked(connection, companion: dict, day: date, at: str) -> bool:
    """An appointment booked with someone else (the dentist, the vet) has that part of the day
    (companion/life/admin.py); chores and errands move out of the way instead."""
    from companion.life import admin
    return admin.holds(connection, companion, day, at)


def first_day(local_now: datetime, at: str) -> date:
    """Today when the time is still a while off, else tomorrow."""
    later = local_now + timedelta(hours=1)
    return local_now.date() if later.date() == local_now.date() and later.strftime('%H:%M') <= at else \
        local_now.date() + timedelta(days=1)


def when_free(connection, companion: dict, wanted: dict, local_now: datetime) -> tuple[date, str] | None:
    """The asked day and time when the companion is free then, else the nearest free day within a week, trying the
    asked time first and then the usual time for the outing."""
    schedule, _default = routine.blocks(companion['version']['definition'])
    usual = ACTIVITIES[wanted['activity']][2]
    for at in dict.fromkeys(filter(None, (wanted['at'], usual))):
        start = wanted['day'] or first_day(local_now, at)
        if start == local_now.date() and at <= local_now.strftime('%H:%M'):
            start += timedelta(days=1)
        for offset in range(LOOK_DAYS):
            day = start + timedelta(days=offset)
            if wanted['firm'] and offset:
                return None
            if not busy_at(schedule, day, at) and not cut_short(schedule, day, at, until(at, wanted['activity'])) \
                    and not taken(connection, companion, day) and not booked(connection, companion, day, at):
                return day, at
    return None


def fits(item: dict, day: date, at: str) -> bool:
    part = composer.day_part(at)
    parts = set(item.get('day_parts') or ()) | ({'evening'} if part == 'late' else set())
    season = generators.SEASONS[day.month]
    return (not item.get('day_parts') or part in parts) and (not item.get('seasons') or season in item['seasons'])


def leaning(item: dict, likes: set[str]) -> float:
    """Dates count double, and a place matching something they like counts three times."""
    words = set(re.findall(r'[a-z]+', ' '.join([item.get('cuisine', ''), item.get('summary', ''),
                                                 *item.get('tags', ())]).lower()))
    return (2.0 if 'date' in item.get('good_for', ()) else 1.0) * (3.0 if words & likes else 1.0)


def likes_of(definition: dict) -> set[str]:
    tastes = definition.get('self_tastes') or {}
    words = ' '.join([*definition.get('interests', ()), *tastes.get('likes', ())]).lower()
    return {word for word in re.findall(r'[a-z]+', words) if len(word) > 3}


def waterside(item: dict, data: dict) -> bool:
    """On the water, by its kind, its tags or its neighborhood's feel."""
    hood = next((hood for hood in data['neighborhoods'] if hood['id'] == item.get('neighborhood')), {})
    words = [*item.get('tags', ()), *hood.get('vibe', ())]
    return item['kind'] in WATER_KINDS or any(WATER_WORDS.search(token) for word in words for token in word.split('-'))


def pick_place(data: dict, activity: str, day: date, at: str, definition: dict, seed: str,
               cheap: bool, word: str = '', by_water: bool = False) -> dict | None:
    """The companion's pick: a place for this outing open at that time and in season, within budget, that fits the
    word asked ("the aquarium") and is on the water when asked ("by the harbor"), when one does."""
    options = [item for item in data['places'] if item['kind'] in kinds(activity) and fits(item, day, at)]
    if by_water:
        options = [item for item in options if waterside(item, data)] or options
    if activity in ('museum', 'walk', 'show'):
        options = [item for item in options if not NOT_OUTINGS.search(item['name'])] or options
    wants = next((pattern for stem, pattern in WANTS.items() if stem in word), None)
    if wants:
        options = [item for item in options if re.search(wants, described(item), re.IGNORECASE)] or options
    options = [item for item in options if not cheap or item.get('cost', '') in CHEAP] or options
    if not options:
        return None
    likes = likes_of(definition)
    return generators.pick(seed, 'outing-place', options, [leaning(item, likes) for item in options])


def place_view(item: dict, data: dict) -> dict:
    hoods = {hood['id']: hood['name'] for hood in data['neighborhoods']}
    return {'id': item['id'], 'name': item['name'], 'kind': item['kind'], 'neighborhood': hoods.get(
            item['neighborhood'], ''), 'summary': item.get('summary', ''), 'cost': item.get('cost', ''),
            'cuisine': item.get('cuisine', ''), 'city': data['name'], 'city_id': data['id'],
            'spots': inside.for_place(item, data.get('era'))}


def bill(definition: dict, activity: str, day: date, left: float | None = None) -> tuple[float, bool]:
    """(their share of the bill, whether it fits what they have `left` that day, else their bare budget); nothing
    where money does not apply."""
    found = money.profile(definition)
    if not found:
        return 0.0, True
    cost = money.cost(found, ACTIVITIES[activity][4])
    return round(cost, 2), cost <= (money.left_on(found, day) if left is None else left)


def until(at: str, activity: str) -> str:
    end = datetime.combine(date(2000, 1, 1), datetime.strptime(at, '%H:%M').time()) + \
        timedelta(hours=ACTIVITIES[activity][3])
    return '23:59' if end.date() > date(2000, 1, 1) else end.strftime('%H:%M')


def note(connection, message: dict, companion: dict, timestamp: str) -> dict | None:
    """Settle the outing a user message asks for, or that a completed companion reply firmly makes. Idempotent per
    message; the agenda picks it up the next time it extends."""
    firm = message['role'] == 'companion'
    if message['status'] != 'complete' or in_character.out_of_character(message['text']) or optional(
            connection, 'SELECT id FROM outings WHERE message_id=?', (message['id'],)):
        return None
    version = companion['version']
    definition = version['definition']
    local_now = parse(message['created_at']).astimezone(zone(version['timezone']))
    data = city_data(connection, definition)
    from companion.life import hobbies
    wanted = proposal(message['text'], local_now.date(), own_plans.holiday_dates(
        connection, definition, local_now.date()), data, firm, hobbies.patterns(connection, companion['active_timeline_id']))
    if not wanted:
        # Not going out: maybe a visit, or saying goodbye while together (companion/life/together.py).
        from companion.life import together
        together.note(connection, message, companion, timestamp)
        return None
    if not data or across_distance(connection, message, companion, wanted, timestamp):
        return None
    if wanted['activity'] == 'hobby' and not wanted['at']:
        wanted = {**wanted, 'at': hobbies.usual_at(connection, wanted['hobby'], wanted['day'] or local_now.date())}
    found = when_free(connection, companion, {**wanted, 'firm': firm}, local_now)
    if not found:
        return None
    day, at = found
    return save(connection, companion, message, wanted, data, day, at, timestamp)


def across_distance(connection, message: dict, companion: dict, wanted: dict, timestamp: str) -> bool:
    """Living in different cities, nothing is booked (companion/life/long_distance.py): while a weekend visit is under
    way they are already together, and otherwise the reply to the user's ask says why they can't just meet up."""
    from companion.life import long_distance, together
    if long_distance.visiting(connection, companion, parse(message['created_at'])):
        return True
    between = long_distance.far(connection, companion)
    if between is None:
        return False
    if message['role'] == 'user' and not optional(connection, 'SELECT id FROM together_asks WHERE message_id=?',
                                                  (message['id'],)):
        kind = 'visit-in' if wanted['activity'] == 'dinner-in' else 'out'
        together.record(connection, companion, message, kind, {'why': 'far', 'city': between.their_city['name'],
                                                               'km': between.km, 'out': kind == 'out'}, timestamp)
    return True


def save(connection, companion, message, wanted, data, day: date, at: str, timestamp: str) -> dict | None:
    definition = companion['version']['definition']
    if wanted['activity'] == 'dinner-in':
        place = home_view(connection, companion, day, message['id'], timestamp)
        outing_id = identifier()
        connection.execute(
            'INSERT INTO outings (id, companion_id, message_id, local_date, at_time, until_time, activity, asked_date, '
            'place, named, cost, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?)',
            (outing_id, companion['id'], message['id'], day.isoformat(), at, until(at, 'dinner-in'), 'dinner-in',
             wanted['day'].isoformat() if wanted['day'] else None, encode(place), timestamp))
        from companion.life import admin
        admin.make_room(connection, companion, day, at, parse(timestamp))
        return get(connection, outing_id)
    cost, affordable = bill(definition, wanted['activity'], day,
                            money.spendable(connection, companion['active_timeline_id'], definition, day))
    if wanted['activity'] == 'hobby':
        return save_pastime(connection, companion, message, wanted, data, day, at, timestamp, cost)
    item = wanted['place'] or pick_place(data, wanted['activity'], day, at, definition, f"outing:{message['id']}",
                                         not affordable, wanted.get('word', ''), wanted.get('waterside', False))
    if item is None:
        return None
    if item.get('cost') == 'free':
        cost, affordable = 0.0, True
    outing_id = identifier()
    connection.execute(
        'INSERT INTO outings (id, companion_id, message_id, local_date, at_time, until_time, activity, asked_date, '
        'place, named, cost, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (outing_id, companion['id'], message['id'], day.isoformat(), at, until(at, wanted['activity']),
         wanted['activity'], wanted['day'].isoformat() if wanted['day'] else None, encode(place_view(item, data)),
         int(wanted['place'] is not None), cost if affordable else round(cost * 0.6, 2), timestamp))
    from companion.life import admin
    admin.make_room(connection, companion, day, at, parse(timestamp))
    return get(connection, outing_id)


def save_pastime(connection, companion, message, wanted, data, day: date, at: str, timestamp: str, cost: float):
    """One of their pastimes with the user, at their usual spot for it (companion/life/hobbies.py)."""
    from companion.life import admin, hobbies
    place = hobbies.outing_place(connection, companion['active_timeline_id'], wanted['hobby'],
                                 companion['version']['definition'], data)
    if place is None:
        return None
    if place.get('cost') == 'free' or place.get('kind') == 'home':
        cost = 0.0
    outing_id = identifier()
    connection.execute(
        'INSERT INTO outings (id, companion_id, message_id, local_date, at_time, until_time, activity, asked_date, '
        'place, named, cost, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)',
        (outing_id, companion['id'], message['id'], day.isoformat(), at, until(at, 'hobby'), 'hobby',
         wanted['day'].isoformat() if wanted['day'] else None, encode(place), cost, timestamp))
    admin.make_room(connection, companion, day, at, parse(timestamp))
    hobbies.outing_added(connection, companion, parse(timestamp))
    return get(connection, outing_id)


def view(row: dict) -> dict:
    return {**row, 'place': decode(row['place']), 'named': bool(row['named'])}


def get(connection, outing_id: str) -> dict:
    row = optional(connection, 'SELECT * FROM outings WHERE id=?', (outing_id,))
    require(row is not None, 'That outing could not be found.', 404)
    return view(row)


def in_force(connection, timeline_id: str, since: str = '', include_cancelled: bool = False) -> list[dict]:
    """Outings whose message, or a copy of it, is shown on this timeline, from `since` (a local date) on."""
    from companion.self_facts import shown
    status = '' if include_cancelled else "AND outings.status!='cancelled' "
    rows = many(connection, 'SELECT outings.*, messages.reply_to AS reply_to, messages.id AS shown_id FROM outings '
                'JOIN messages ON (messages.id=outings.message_id OR messages.origin_id=outings.message_id) '
                "WHERE messages.timeline_id=? AND messages.active=1 AND messages.status='complete' AND "
                f'messages.redacted_at IS NULL AND outings.local_date>=? {status}'
                'ORDER BY outings.local_date, outings.at_time', (timeline_id, since))
    return [view(row) for row in shown(connection, timeline_id, rows)]


def window(outing: dict, timezone: str) -> tuple[datetime, datetime]:
    """When it starts and ends, in UTC; heading home early ends it then."""
    tz = zone(timezone)
    day = date.fromisoformat(outing['local_date'])
    start = datetime.combine(day, datetime.strptime(outing['at_time'], '%H:%M').time(), tz)
    end = datetime.combine(day, datetime.strptime(outing['until_time'], '%H:%M').time(), tz)
    if outing['ended_at']:
        end = min(end, parse(outing['ended_at']))
    return start, end


def state(outing: dict, timezone: str, now: datetime) -> str:
    """'cancelled', 'planned', 'now' (under way) or 'done'."""
    if outing['status'] == 'cancelled':
        return 'cancelled'
    start, end = window(outing, timezone)
    return 'done' if outing['status'] == 'done' or now >= end else 'now' if now >= start else 'planned'


# --- The agenda ---

def as_plans(connection, timeline_id: str, since: str) -> dict[str, list[dict]]:
    """Outings by local date in the shape own_plans.assign takes. The id changes when the place does, so the agenda
    composes the slot again."""
    result = {}
    for outing in in_force(connection, timeline_id, since):
        result.setdefault(outing['local_date'], []).append(
            {'id': f"outing:{outing['id']}:{outing['rolls']}", 'at_time': outing['at_time'], 'outing': outing})
    return result


def doing(outing: dict) -> str:
    """'went to dinner at Lupa', 'went for a walk in Patterson Park'."""
    place, activity = outing['place']['name'], outing['activity']
    if activity in MEETUPS:
        from companion.life import their_people
        return their_people.doing(outing)
    if activity == 'wedding':
        from companion.life import wedding
        return wedding.doing(outing)
    if activity == 'dinner-in':
        return f"had you over for {menu_text(outing['place'].get('menu') or {})} at home"
    if activity in VISIT_DOING:
        return VISIT_DOING['knock' if place_knock(outing) else activity]
    if activity == 'hobby':
        hobby = outing['place']['hobby']
        if hobby.get('event'):
            return f"had {hobby['event']} at {place}, and you came to watch"
        return f"{hobby['session']} at {place}"
    if activity == 'walk':
        return f'went for a walk at {place}'
    if activity in ('dinner', 'lunch-out', 'coffee', 'drinks'):
        return f"went out for {ACTIVITIES[activity][5]} at {place}"
    if activity == 'show':
        return f'went to see a show at {place}'
    return f'spent a few hours at {place}' if activity == 'museum' else f'browsed around {place}'


# Visits (companion/life/together.py), as their day tells them.
VISIT_DOING = {'visit-in': 'had you over at home', 'visit-yours': 'came over to your place',
               'dinner-yours': 'came over to your place for dinner', 'knock': 'dropped by your place'}


# A visit as an image prompt says it (images/prompts.py), apart from VISIT_DOING, which the chat and the feed read:
# the image model can't place "you" or "Your place", and a "you" in the words draws a second person.
PHOTO_DOING = {'had you over at home': 'had a friend over at home{area}',
               'came over to your place for dinner': "came over to a friend's apartment{area} for dinner",
               'came over to your place': "came over to a friend's apartment{area}",
               'dropped by your place': "dropped by a friend's apartment{area}"}


def photo_words(summary: str, activity: str, neighborhood: str | None) -> dict:
    """A visit's summary and place for a picture: "came over to a friend's apartment in Hampden", not "came over to
    your place ... at Your place". A summary phrased some other way keeps its words; only the place changes."""
    area = f' in {neighborhood}' if neighborhood else ''
    place = f'home{area}' if activity == 'visit-in' else f"a friend's apartment{area}"
    for said, shown in PHOTO_DOING.items():
        if f' {said}.' in summary:
            return {'summary': summary.replace(f' {said}.', f' {shown.format(area=area)}.', 1), 'place': place}
    return {'summary': summary, 'place': place}


def place_knock(outing: dict) -> bool:
    return bool(outing['place'].get('knock'))


def menu_text(menu: dict) -> str:
    """'dinner (they cooked mushroom risotto, with lemon bars for dessert)'."""
    if menu.get('takeout'):
        return f"dinner ({menu['takeout']['dish']} from {menu['takeout']['source']})"
    if not menu.get('dish'):
        return 'dinner'
    return f"dinner, {menu['dish']}" + (f", with {menu['bake']} for dessert" if menu.get('bake') else '')


def entry(plan: dict, block: dict, definition: dict) -> dict:
    """The agenda entry for the slot an outing takes: it happening, with the user."""
    outing = plan['outing']
    place = outing['place']
    area = f" in {place['neighborhood']}" if place['neighborhood'] and place['neighborhood'] not in place['name'] \
        and place['kind'] not in ('home', 'your-home', 'family-home') else ''
    alone = outing['activity'] in ('dinner-in', 'wedding', *VISIT_DOING, *MEETUPS) or (place.get('hobby') or {}).get(
        'event')
    summary = f"{definition['name']} {doing(outing)}{area}" + ('.' if alone else ' with you.')
    seed = f"outing:{outing['id']}:{outing['rolls']}"
    spot = generators.pick(seed, SPOT, place.get('spots') or [])
    if spot:
        summary += f' {generators.pick(seed, "outing-line", list(inside.SENTENCES)).format(where=spot)}'
    if outing['activity'] == 'wedding':
        from companion.life import wedding
        post = wedding.caption(outing)
    else:
        post = generators.pick(seed, 'outing-post', list(CAPTIONS))
    return {'summary': summary, 'post': post, 'mood': 'happy',
            'activity': outing['activity'], 'place': {key: place[key] for key in ('id', 'name', 'kind', 'city',
                                                                                'neighborhood')},
            'with': None, 'weather': block.get('weather'), 'inside': spot or None,
            'outing': {'id': outing['id'], 'message_id': outing['message_id'], 'at': outing['at_time'],
                       'until': outing['until_time']}, 'hobby': place.get('hobby'), 'composer_version': 'outing-1'}


CAPTIONS = ('Good company.', 'One of the good evenings.', 'Would do this again.', 'Worth getting dressed for.',
            'Still smiling about it.')


def marked(block: dict, plan: dict | None) -> dict:
    """The block an outing takes, marked as time with the user: replies are not held while they are together."""
    return {**block, 'with_user': True} if plan and 'outing' in plan else block


# --- The chat context (the "together" section) ---

def day_text(local_date: str) -> str:
    return date.fromisoformat(local_date).strftime('%A %B %d').replace(' 0', ' ')


def what(outing: dict) -> str:
    """'dinner at Lupa, a restaurant in Little Italy'; dinner at their place with what they are making."""
    place = outing['place']
    if outing['activity'] in MEETUPS:
        from companion.life import their_people
        return their_people.what(outing)
    if outing['activity'] == 'wedding':
        from companion.life import wedding
        return wedding.what(outing)
    if outing['activity'] == 'dinner-in':
        return f"{menu_text(place.get('menu') or {})} at your place"
    if outing['activity'] in VISIT_DOING:
        area = f" in {place['neighborhood']}" if place.get('neighborhood') else ''
        return {'visit-in': 'time together at your place', 'visit-yours': f"a visit to the user's place{area}",
                'dinner-yours': f"dinner at the user's place{area} (they are cooking)"}[outing['activity']]
    if outing['activity'] == 'hobby':
        hobby = place['hobby']
        return f"{hobby.get('event') or hobby['together']} at {place['name']}"
    kind = f"{place['cuisine']} {place['kind']}".strip() if place.get('cuisine') else place['kind']
    area = f" in {place['neighborhood']}" if place['neighborhood'] else ''
    return f"{ACTIVITIES[outing['activity']][5]} at {place['name']} ({kind}{area})"


def menu(data: dict | None, outing: dict) -> str:
    """Dishes the city data ties to this place, else ones that fit its cuisine, and the price of the outing."""
    if not data:
        return ''
    place = outing['place']
    dishes = [item['name'] for item in data.get('local_color', ()) if item.get('kind') == 'dish'
              and place['id'] in item.get('places', ())]
    cuisine = (place.get('cuisine') or '').lower()
    if not dishes and cuisine:
        dishes = [item['name'] for item in data.get('local_color', ()) if item.get('kind') == 'dish'
                  and cuisine in item.get('summary', '').lower()]
    ids = money.COSTS[ACTIVITIES[outing['activity']][4]][0] if ACTIVITIES[outing['activity']][4] in money.COSTS \
        else ()
    prices = [item for wanted in ids for item in data.get('prices', ()) if item['id'] == wanted][:1]
    parts = [f"On the menu: {', '.join(dishes[:3])}." if dishes and outing['activity'] in ('dinner', 'lunch-out')
             else '']
    for item in prices:
        span = f"{money.amount(item['low'], data['currency'])} to {money.amount(item['high'], data['currency'])}"
        parts.append(f"{item['item']}: {span}{' ' + item['per'] if item.get('per') else ''}.")
    return ' '.join(part for part in parts if part)


def scene(connection, companion: dict, outing: dict, now: datetime | None = None) -> str:
    """What being there together looks like, from the city data."""
    from companion.life import agenda
    definition = companion['version']['definition']
    data = city_data(connection, definition)
    place = outing['place']
    seed = f"outing:{outing['id']}:{outing['rolls']}"
    spot = generators.pick(seed, SPOT, place.get('spots') or [])
    conditions = generators.conditions(data, date.fromisoformat(outing['local_date'])) if data else None
    if outing['activity'] in VISIT_DOING:
        return visit_scene(outing, spot, conditions, here_too(connection, companion, outing, now) if now else ())
    if outing['activity'] in MEETUPS:
        from companion.life import their_people
        return their_people.scene(connection, companion, outing, spot)
    if outing['activity'] == 'wedding':
        from companion.life import wedding
        return wedding.scene(connection, companion, outing, now)
    if outing['activity'] == 'dinner-in':
        spot = generators.pick(seed, SPOT, place.get('spots') or [])
        return '- ' + ' '.join(part for part in (
            f"Right now the user is over at your place, in person, for {what(outing).replace(' at your place', '')}, "
            f"until about {outing['until_time']}.", f'You are {spot}.' if spot else '',
            'You cooked it yourself.' if (place.get('menu') or {}).get('dish') else '',
            'Talk as if you are there together, face to face, not texting.') if part)
    parts = [f"Right now you are out with the user, in person: {what(outing)}, until about {outing['until_time']}.",
             f'You are {spot}.' if spot else '', place.get('summary', ''), menu(data, outing),
             f'Weather: {agenda.weather_text(conditions)}' if conditions else '',
             'Talk as if you are there together, face to face, not texting.']
    if place.get('proposal'):
        from companion.life import wedding
        parts.append(wedding.proposal_lines(connection, outing))
    return '- ' + ' '.join(part.strip() for part in parts if part.strip())


IN_PERSON = ('Talk as if you are there together, face to face, not texting: what you say and do in the room, no '
             'separate texts, no typos.')


def here_too(connection, companion: dict, outing: dict, now: datetime) -> list[str]:
    """The other companions in person at the same place right now (two visits at the user's place at once)."""
    from companion.characters import by_id
    from companion.life import together
    names = []
    for row in many(connection, 'SELECT id FROM companions WHERE id!=? ORDER BY created_at', (companion['id'],)):
        other = by_id(connection, row['id'])
        found = other and together.together_now(connection, other, now)
        if found and found['place']['id'] == outing['place']['id'] and found['activity'] in together.AT_YOURS:
            names.append(other['version']['definition']['name'])
    return names


def visit_scene(outing: dict, spot: str | None, conditions, others=()) -> str:
    """Being at the user's place, or having them at yours, in person."""
    from companion.life import agenda
    place = outing['place']
    area = f" in {place['neighborhood']}" if place.get('neighborhood') else ''
    if outing['activity'] == 'visit-in':
        first = f"Right now the user is over at your place, in person, until about {outing['until_time']}."
    elif place.get('knock'):
        first = (f"Right now you are at the user's place{area}, in person: you dropped by without telling them first, "
                 f"and you can stay until about {outing['until_time']}.")
    else:
        food = ' for dinner, which they are cooking' if outing['activity'] == 'dinner-yours' else ''
        first = f"Right now you are over at the user's place{area}{food}, in person, until about {outing['until_time']}."
    spot = None if place.get('knock') else spot  # Just in from the door, not settled anywhere yet.
    weather = f'Weather outside: {agenda.weather_text(conditions)}' if conditions else ''
    company = ' '.join(f'{name}, also visiting the user, is here too, in person.' for name in others)
    return '- ' + ' '.join(part for part in (first, company, f'You are {spot}.' if spot else '', weather, IN_PERSON)
                           if part)


def planned_line(outing: dict) -> str:
    if outing['activity'] == 'wedding':
        return f"- {day_text(outing['local_date'])} at {outing['at_time']}: {what(outing)}."
    line = f"- {day_text(outing['local_date'])} at {outing['at_time']}: {what(outing)}, with the user."
    if outing['activity'] == 'dinner-in':
        return line + ' You are cooking.'
    if outing['activity'] in VISIT_DOING:
        return line
    if outing['activity'] in MEETUPS:
        return line + ' You arranged it and invited the user.'
    return line + (' They picked the place.' if outing['named'] else ' You picked the place.')


def booked_line(outing: dict, holding: dict | None = None) -> str:
    """The outing settled for the turn being answered, as what the reply says (first in its notes)."""
    if outing['activity'] == 'dinner-in':
        line = f"- You are having the user over: {what(outing)}, {day_text(outing['local_date'])} at " \
            f"{outing['at_time']}. Confirm when and what you will make in this reply, in your own words."
    elif outing['activity'] in VISIT_DOING:
        line = f"- You agreed: {what(outing)}, {day_text(outing['local_date'])} at {outing['at_time']}. " \
            'Confirm when in this reply, in your own words.'
    else:
        line = f"- You agreed to go: {what(outing)}, {day_text(outing['local_date'])} at {outing['at_time']}. " \
            'Confirm where and when in this reply, in your own words.'
    if outing['asked_date'] and outing['asked_date'] != outing['local_date']:
        why = f"something is already booked then ({holding['title']}), so name it, say you can't make that day " \
            "and" if holding else "you can't make that day, so say so and"
        line += f" They asked for {day_text(outing['asked_date'])}, but {why} that it is " \
                f"{day_text(outing['local_date'])} instead."
    return line


def holding_for(connection, companion: dict, outing: dict) -> dict | None:
    """The appointment that kept the day the user asked for (companion/life/admin.py), so the reply can name it."""
    if not outing['asked_date'] or outing['asked_date'] == outing['local_date']:
        return None
    from companion.life import admin
    return admin.holding(connection, companion, date.fromisoformat(outing['asked_date']), outing['at_time'])


def context_lines(connection, companion: dict, now: datetime, fresh_ids: set[str]) -> list[tuple[str, str]]:
    """(identity, line) for plans with the user: coming up, under way, or just over. `fresh_ids` are the messages
    of the turn being answered, whose outing the reply should announce."""
    version = companion['version']
    today = now.astimezone(zone(version['timezone'])).date()
    result = []
    for outing in in_force(connection, companion['active_timeline_id'], (today - timedelta(days=1)).isoformat()):
        found = state(outing, version['timezone'], now)
        if found == 'now':
            result.append((f"outing:{outing['id']}:now", scene(connection, companion, outing, now)))
        elif found == 'planned':
            result.append((f"outing:{outing['id']}", planned_line(outing)))
            if outing['message_id'] in fresh_ids:
                result.append((f"outing:{outing['id']}:booked",
                               booked_line(outing, holding_for(connection, companion, outing))))
        elif now - window(outing, version['timezone'])[1] < RECENT and outing['activity'] == 'wedding':
            result.append((f"outing:{outing['id']}:done",
                           f"- Earlier today you and the user got married at {outing['place']['name']}; the wedding "
                           'is over now.'))
        elif now - window(outing, version['timezone'])[1] < RECENT:
            paid = money_text(companion, outing)
            result.append((f"outing:{outing['id']}:done",
                           f"- Earlier you and the user had {what(outing)}; it is over now.{paid}"))
    return result


def money_text(companion: dict, outing: dict) -> str:
    found = money.profile(companion['version']['definition'])
    return f" You paid about {money.amount(outing['cost'], found.city['currency'])}." if found and outing['cost'] \
        else ''


# --- When it ends ---

def finish_due(connection, companion: dict, now: datetime) -> int:
    """Outings on this timeline that have ended: kept as a memory, and marked done (the bill is read from the
    outing by money.household). Cheap: no model."""
    from companion.life import together
    from companion.memory import records
    timezone = companion['version']['timezone']
    # From the oldest one still planned, however long ago: after a long absence it still finishes.
    oldest = optional(connection, "SELECT MIN(local_date) AS since FROM outings WHERE companion_id=? AND status='planned'",
                      (companion['id'],))
    if not oldest or not oldest['since']:
        return 0
    done = 0
    for outing in in_force(connection, companion['active_timeline_id'], oldest['since']):
        if outing['status'] != 'planned' or state(outing, timezone, now) != 'done' or undoable_home(outing, now):
            continue
        if together.turned_away(outing, timezone):
            connection.execute("UPDATE outings SET status='done' WHERE id=?", (outing['id'],))
            continue
        fields = {**memory_text(outing), 'layer': 'shared_experience',
                  'stated_at': stamp(min(now, window(outing, timezone)[1])), 'applies_from': None, 'applies_until': None}
        memory, _created = records.insert(connection, companion, fields, now=stamp(now), origin='automatic',
                                          sources=(outing['message_id'],))
        connection.execute("UPDATE outings SET status='done', memory_id=? WHERE id=?", (memory['id'], outing['id']))
        done += 1
    return done


def memory_text(outing: dict) -> dict:
    """{subject, value} of the shared memory an outing leaves."""
    day = date.fromisoformat(outing['local_date'])
    place = outing['place']
    on = f"on {day:%A, %B} {day.day}"
    if outing['activity'] in MEETUPS:
        from companion.life import their_people
        return their_people.memory_text(outing)
    if outing['activity'] == 'wedding':
        from companion.life import wedding
        return wedding.memory_text(outing)
    if outing['activity'] in VISIT_DOING:
        subject = {'visit-in': 'The user came over to your place', 'visit-yours': "You went over to the user's place",
                   'dinner-yours': "Dinner at the user's place"}[outing['activity']]
        if place_knock(outing):
            subject = "You dropped by the user's place"
        return {'subject': subject, 'value': f'{subject} {on}.'}
    pastime = (place.get('hobby') or {}).get('label') if outing['activity'] == 'hobby' else None
    return {'subject': f"{pastime or ACTIVITIES[outing['activity']][5].capitalize()} together at {place['name']}",
            'value': f"Went out together for {what(outing)} {on}."}


def purchases(connection, timeline_id: str, start: date, day: date) -> list[dict]:
    """Outings that ended this pay period, as money.household purchases with their own cost."""
    return [{'text': f"paid for {ACTIVITIES[outing['activity']][5]} at {outing['place']['name']}",
             'date': outing['local_date'], 'spend': '', 'cost': outing['cost'], 'for': 'outing'}
            for outing in in_force(connection, timeline_id, start.isoformat())
            if outing['status'] == 'done' and outing['local_date'] <= day.isoformat() and outing['cost']
            and outing['activity'] != 'wedding']


# --- What the user can change ---

def owned(connection, companion: dict, outing_id: str) -> dict:
    outing = get(connection, outing_id)
    require(outing['companion_id'] == companion['id'], 'That outing belongs to another companion.', 404)
    return outing


def cancel(connection, companion: dict, outing_id: str, now: datetime) -> dict:
    outing = owned(connection, companion, outing_id)
    require(outing['activity'] != 'wedding', 'The wedding is planned in Life admin, on their Character page.', 409)
    require(state(outing, companion['version']['timezone'], now) == 'planned',
            'Only an outing that has not started can be called off.', 409)
    connection.execute("UPDATE outings SET status='cancelled', cancelled_at=? WHERE id=?", (stamp(now), outing_id))
    return get(connection, outing_id)


def head_home(connection, companion: dict, outing_id: str, now: datetime) -> dict:
    """End an outing under way now. It is kept (memory, bill, photo) once UNDO has passed, like one that ran its
    course."""
    outing = owned(connection, companion, outing_id)
    require(state(outing, companion['version']['timezone'], now) == 'now', 'Only an outing under way can end now.',
            409)
    connection.execute('UPDATE outings SET ended_at=? WHERE id=?', (stamp(now), outing_id))
    return get(connection, outing_id)


def undoable_home(outing: dict, now: datetime) -> bool:
    return outing['status'] == 'planned' and bool(outing['ended_at']) and now - parse(outing['ended_at']) < UNDO


def undoable_cancel(outing: dict, timezone: str, now: datetime) -> bool:
    """Called off today, and it would not have started yet."""
    if outing['status'] != 'cancelled' or not outing['cancelled_at']:
        return False
    tz = zone(timezone)
    return parse(outing['cancelled_at']).astimezone(tz).date() == now.astimezone(tz).date() and \
        window(outing, timezone)[0] > now


def undo(connection, companion: dict, outing_id: str, now: datetime) -> dict:
    """Take back calling it off (the rest of that day) or heading home (for UNDO)."""
    outing = owned(connection, companion, outing_id)
    if undoable_home(outing, now):
        connection.execute('UPDATE outings SET ended_at=NULL WHERE id=?', (outing_id,))
    else:
        require(undoable_cancel(outing, companion['version']['timezone'], now), 'That can no longer be undone.', 409)
        require(not taken(connection, companion, date.fromisoformat(outing['local_date'])),
                'Another plan has that day now.', 409)
        connection.execute("UPDATE outings SET status='planned', cancelled_at=NULL WHERE id=?", (outing_id,))
    return get(connection, outing_id)


def elsewhere(connection, companion: dict, outing_id: str, now: datetime) -> dict:
    """The companion picks another place for an outing that has not started."""
    outing = owned(connection, companion, outing_id)
    require(state(outing, companion['version']['timezone'], now) == 'planned',
            'Only an outing that has not started can move.', 409)
    require(outing['activity'] != 'dinner-in', 'Dinner at their place stays at their place.', 409)
    require(outing['activity'] != 'wedding', 'The wedding is planned in Life admin, on their Character page.', 409)
    require(outing['activity'] != 'meet-family', 'Dinner with their family stays at their family\'s place.', 409)
    data = city_data(connection, companion['version']['definition'])
    require(data is not None, "Their city isn't known, so there is nowhere else to go.", 409)
    day = date.fromisoformat(outing['local_date'])
    rolls = outing['rolls'] + 1
    cheap = outing['cost'] < bill(companion['version']['definition'], outing['activity'], day)[0]
    item = pick_place({**data, 'places': [place for place in data['places'] if place['id'] != outing['place']['id']]},
                      outing['activity'], day, outing['at_time'], companion['version']['definition'],
                      f"outing:{outing['message_id']}:{rolls}", cheap)
    require(item is not None, 'There is nowhere else like it in their city.', 409)
    connection.execute('UPDATE outings SET place=?, named=0, rolls=? WHERE id=?',
                       (encode(place_view(item, data)), rolls, outing_id))
    return get(connection, outing_id)


def listing(connection, companion: dict, now: datetime) -> list[dict]:
    """Outings from the last two weeks on, each with its state, for Today."""
    version = companion['version']
    since = (now.astimezone(zone(version['timezone'])).date() - timedelta(days=14)).isoformat()
    found = in_force(connection, companion['active_timeline_id'], since, include_cancelled=True)
    return [{**outing, 'state': state(outing, version['timezone'], now),
             'undo': undoable_home(outing, now) or undoable_cancel(outing, version['timezone'], now),
             'cost_text': money_text(companion, outing).strip()} for outing in found]


def photo_ready(connection, now: datetime) -> list[dict]:
    """Done outings of the companion in focus from the last day with no photo tried yet."""
    return many(connection, "SELECT * FROM outings WHERE status='done' AND photo_post_id IS NULL AND photo_tried=0 "
                'AND local_date>=?', ((now - timedelta(days=1)).date().isoformat(),))


def photograph(database) -> None:
    """With pictures in chat on, a photo of a finished outing for the feed post its event is told in. Called by the
    image runner each tick; at most one try per outing."""
    from companion.characters import current
    from companion.images import jobs, prompts
    from companion.life import feed, simulation
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = current(connection)
        ready = [row for row in photo_ready(connection, now) if companion and row['companion_id'] == companion['id']]
        if not ready or not jobs.image_settings(connection)['chat_photos']:
            return
        outing = view(ready[0])
        connection.execute('UPDATE outings SET photo_tried=1 WHERE id=?', (outing['id'],))
        slot = optional(connection, "SELECT slot_key, ends_at, entry FROM life_agenda WHERE timeline_id=? AND "
                        "subject='companion' AND json_extract(entry, '$.outing.id')=?",
                        (companion['active_timeline_id'], outing['id']))
        if not slot:
            return
        key = simulation.event_key(companion['active_timeline_id'], slot['slot_key'])
        told = optional(connection, 'SELECT post.id FROM feed_posts post JOIN feed_post_events link ON '
                        'link.post_id=post.id JOIN life_events event ON event.id=link.event_id WHERE '
                        'event.idempotency_key=?', (key,))
        post_id = told['id'] if told else feed.create(connection, companion['active_timeline_id'], 'event',
                                                       feed.PHOTO_KEY + key, [], slot['ends_at'], stamp(now))
        found = moment(companion, outing, decode(slot['entry']), key)
        if outing['activity'] == 'wedding':
            from companion.life import wedding
            found = {**found, 'wearing': wedding.photo_wearing(connection, companion, outing),
                     'label': 'Your wedding day'}
        inputs = prompts.build_moment(connection, found, jobs.image_settings(connection), 'moment')
        connection.execute('UPDATE outings SET photo_post_id=? WHERE id=?', (post_id, outing['id']))
    if jobs.routable(database, inputs):
        jobs.enqueue(database, post_id, 'manual', inputs=inputs)


def moment(companion: dict, outing: dict, composed: dict, key: str) -> dict:
    """The outing as images/prompts.build_moment reads a chat photo's moment."""
    hour = int(outing['at_time'][:2]) + 1
    return {'event_key': key, 'summary': composed['summary'], 'caption': composed['post'], 'mood': 'happy',
            'place': outing['place']['name'], 'neighborhood': outing['place'].get('neighborhood'),
            'label': f"Out with you at {outing['place']['name']}", 'kind': 'social',
            'hour': hour, 'weather': composed.get('weather'), 'activity': outing['activity'], 'with': None,
            'timeline_id': companion['active_timeline_id'], 'local_date': outing['local_date']}
