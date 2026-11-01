"""The social side of the feed: the companion's circle posting, liking and commenting.

Beside the companion's posts about life events (companion/life/feed.py), the feed carries posts
that are not life events, all assembled from data the simulation already has and fixed phrasing,
with no model:

- `friend`: a circle member shares one of their happened agenda entries (their diary).
- `status`: a passing thought of the companion's, from the day's weather, how they feel, the
  weekday or an interest. It never claims something happened.
- `birthday`: a shout-out on a circle member's birthday. `holiday`: a public holiday greeting.
- `city`: the companion passes on city news (an opening, a closing, road works, an annual event).
- `question`: a small either-or the user can answer; the answer goes to chat as a reply to it.

While grief is raw or heavy (companion/life/loss.py) the companion posts only a quiet status, if any.

Posts are written when the feed or Today is read, for the last few days up to now, under
idempotency keys seeded by the timeline and slot, so reading twice never posts twice. Likes and
comments are not stored: they follow from the post, the circle and the clock, so a comment shows
up some time after its post, a renamed friend comments under the new name and a removed one
leaves the conversation. The companion likes and comments on friends' posts the same way, and
other companions who know them (companion/memory/pairs.py) on the companion's own posts, by how
close they feel and how reserved or warm they are.

Who reacts follows how they know the poster (`stance`): on a friend's post, the rest of the circle by how they and
that friend know each other (circle.tie), and the companion by whether they know them (circle.knowing). Someone
who doesn't know the poster seldom even sees it and never comments; family and old friends join in most. A rival
(by their tie, or by the words of their role for the companion) keeps quiet or gets in a dig, as Settings > Realism
> "Trolls and snark on posts" (life_settings.trolls_realism, companion/life/post_snark.py) says.
"""
import json
import logging
import re
from datetime import date, datetime, time, timedelta

from companion.characters import require_current
from companion.clock import parse, stamp, zone
from companion.database import decode, encode, identifier, many, one, optional
from companion.errors import require
from companion.life import circle, composer, loss, love_life, post_snark, wedding
from companion.world import catalog
from companion.world.generators import pick, unit

KINDS = ('status', 'friend', 'birthday', 'holiday', 'city', 'question')
SOURCES = ('all', 'companion', 'circle')
COMPANION = 'companion'
LOOKBACK = timedelta(days=4)
# The chance a circle member shares a happened entry, by the kind of block it filled.
SHARE = {'social': 0.45, 'leisure': 0.4, 'rest': 0.15, 'errand': 0.12, 'work': 0.08, 'study': 0.08}
FRIEND_DAILY = 4
STATUS_CHANCE, QUESTION_CHANCE, HAPPENING_CHANCE, CITY_CHANCE = 0.55, 0.2, 0.5, 0.6
MAX_COMMENTS = 3
# Reactions and comments arrive within this long of the post.
REACTION_WINDOW = timedelta(hours=8)
HOT_F, COLD_F = 86, 40
SICK = {'sick', 'under the weather'}
LINES = json.loads((catalog.DATA / 'feed_lines.json').read_text(encoding='utf-8'))
DOWN = {'tired', 'hungover', 'worn out', 'sore', 'drained', 'sluggish'}

STATUS = {
    'rain': ('Rain all day. Tea and a blanket it is.', 'Forgot my umbrella. Of course I did.',
             'Love the sound of rain on the window.'),
    'hot': ('Way too hot to think today.', 'Iced coffee is my whole personality right now.'),
    'cold': ('Scarf weather. Finally.', 'My hands have not been warm since this morning.'),
    'mild': ('Gorgeous out today.', 'Took the long way just to be outside a bit longer.'),
    'tired': ('Running on very little sleep today.', 'Coffee first. Then everything else.'),
    'worn out': ('Completely drained. Couch, here I come.',),
    'hungover': ('Never drinking again (until the next time).', 'Water, toast and a dark room.'),
    'sick': ('Under a blanket with a cold. Send soup.', 'Tissues, tea and terrible daytime TV.'),
    'sore': ('Every muscle I own is complaining today.',),
    'monday': ('Monday again. Somehow.', 'New week, same coffee.'),
    'friday': ('Made it to Friday.', 'Friday feeling, finally.'),
    'interest': ("Can't stop thinking about {interest} lately.", 'Fell down a {interest} rabbit hole again.'),
    # From the daily culture digest, about the top item of a list; none claims she has seen it.
    'movies': ('Everyone keeps talking about {item}. Worth it?', 'Adding {item} to the watch list.'),
    'tv': ('Is anyone watching {item}?',),
    'music': ("Can't get {item} out of my head.",),
    'books': ('{item} keeps popping up everywhere. Has anyone read it?',),
    # While grief is raw or heavy (companion/life/loss.py): nothing playful, no questions.
    'grief': ('Quiet few days.', 'Taking things slowly this week.', 'Keeping to myself for a bit.'),
    # Passing thoughts for any day (companion/world/data/feed_lines.json).
    'any': tuple(LINES['status_any']),
}
# Small either-or questions the user can answer: (question, (option, option)).
QUESTIONS = tuple((row[0], tuple(row[1:])) for row in LINES['questions'])
# A day offers this many of the any-day thoughts beside the weather, weekday, charts and interests, so a bigger bank
# never crowds those out.
ANY_OFFERED = 4
# The companion never repeats a status line within this long, nor asks a question again until every other one that
# fits their world has been asked (then the one asked longest ago comes back first).
STATUS_GAP = timedelta(days=45)
# Lines that belong to today (and the near future): before about 1950 nobody watches episodes or orders tacos, and
# in a medieval or fantasy town nobody drinks coffee; aboard a ship or station there is no beach, sunrise or
# outdoors to linger in (companion/world/ships.py). The rest suit any world.
TODAYS = re.compile(r'\b(?:tv|episodes?|movies?|pizza|tacos|ramen|iced|couch|peanut|cereal|karaoke|popcorn|brownies|'
                    r'audio|shower|ice cream|order in)\b', re.IGNORECASE)
COFFEE = re.compile(r'\bcoffee\b', re.IGNORECASE)
NO_COFFEE_ERAS = {'medieval', 'fantasy'}
TODAYS_ERAS = {'modern', 'future'}
GROUNDED = re.compile(r'\b(?:beach|sunrise|sunset|outside|umbrella|rain|lake|sea|snow|park|garden|hiking|swimming|'
                      r'camping|countryside|walk|stars|window|bird|picnic|balcony|trip|weekend away)\b', re.IGNORECASE)
BIRTHDAY = ('Happy birthday, {name}! 🎂', 'Happy birthday to {name}, who makes everything more fun. 🎉',
            'Another year of {name}. Lucky us. Happy birthday! 🎂')
FAMILY_BIRTHDAY = 'Happy birthday to my favorite {role}, {name}! 🎂'
HOLIDAY = ('Happy {holiday}, everyone!', '{holiday} and a day off. Perfect.', 'Happy {holiday}! Taking it easy today.')
# Worded so the verb never has to agree with the event's name ("Halloween parties", "Mardi Gras").
HAPPENING = ('{event} today{where}. Anyone going?', "Don't forget, {event} today{where}.")

COMMENTS = {
    'general': ('Love this!', 'This is so you.', 'Jealous.', 'Save me a spot next time.', 'Wait, I need details.',
                '😂', 'Looks like a good day.', 'Same, honestly.', 'Call me later?', 'Okay, this is cute.',
                'Living vicariously.', 'Ha, classic.', 'Need this energy.', 'Iconic.', 'Where is this?',
                'Proud of you.', 'Yes!!'),
    'sick': ('Feel better!', 'Sending soup.', 'Oh no. Need anything?'),
    'down': ('Rest up!', 'Hang in there.', 'You deserve a nap.', 'Big hug.'),
    # On a quiet status while grief is raw or heavy.
    'grief': ('Thinking of you.', 'Here if you need anything.', 'Sending love.', 'Big hug.'),
    'birthday': ('Happy birthday, {name}! 🎉', 'Happy birthday!! 🥳', 'Have the best day, {name}!'),
    'birthday_self': ('Thank you!! ❤️', 'You are the sweetest.', 'Love you for this.'),
    'opening': ("Ooh, I'm in.", 'Count me in.', 'Saturday?'),
    'closing': ('Noooo.', 'End of an era.', 'Wait, really?'),
    'city': ('Good to know.', 'Thanks for the heads up.', 'Ugh.'),
    'question': ('{option}, obviously.', '{option}. No contest.', 'Team {option}.'),
    'from_companion': ("Wish I'd been there.", 'Look at you!', 'Okay, I need the full story.',
                       "Next time I'm coming.", 'This made my day.', 'Obsessed with this.', 'Stop, this is great.',
                       'Tell me everything later.'),
}
LIKELY = {'close friend': 0.85, 'sibling': 0.7, 'roommate from years ago': 0.55}
COMMENT_CHANCE, COMPANION_LIKES = 0.22, 0.7
# Other companions who know this one (companion/memory/pairs.py) join in on the companion's own posts: the closer
# they feel to them, the likelier (by stage, "Just met" first), and by their manner. Someone reserved (a Vulcan,
# a loner) likes now and then and seldom says a word, in a few dry words when they do; someone warm joins in more.
KNOWN_LIKES = (0.15, 0.3, 0.5, 0.65, 0.75)
KNOWN_COMMENTS = (0.04, 0.08, 0.14, 0.2, 0.25)
MANNERS = {'warm': (1.2, 1.5), 'usual': (1.0, 1.0), 'reserved': (0.5, 0.3)}
# However close and warm, nobody likes or comments on every single post.
KNOWN_MOST = (0.9, 0.5)
RESERVED_WORDS = re.compile(r"\b(?:reserved|stoic\w*|reticent|taciturn|aloof|restrained|impassive|unemotional|"
                            r"emotionless|logical|of few words|keeps (?:his|her|their) (?:emotions|feelings) "
                            r"(?:in check|hidden|to (?:himself|herself|themselves|themself))|"
                            r"(?:controls?|suppress\w*|hides?) (?:his|her|their) (?:emotions|feelings))\b",
                            re.IGNORECASE)
WARM_WORDS = re.compile(r"\b(?:warm|affectionate|bubbly|chatty|talkative|effusive|enthusiastic|cheerful|"
                        r"expressive|gushing|wears (?:his|her|their) heart on (?:his|her|their) sleeve)\b",
                        re.IGNORECASE)
RESERVED_COMMENTS = {
    'general': ('Well done.', 'Noted.', 'Interesting.', 'A good use of the day.', 'Agreeable.', 'Sensible.',
                'I approve.', 'Pleasing.'),
    'down': ('Rest well.', 'I hope you recover quickly.', 'Take the time you need.'),
    'grief': ('I am here, should you need anything.', 'My thoughts are with you.'),
    'question': ('{option}.', '{option}, logically.'),
}
# How someone stands with the poster (`stance`) scales their chance to like and to comment (the usual chances
# LIKELY and COMMENT_CHANCE). Someone who doesn't know the poster sees a friend-of-a-friend's post now and then
# and leaves it at that; family and old friends join in most.
STANCES = {'close': (1.3, 1.2), 'friendly': (1.0, 1.0), 'coworkers': (0.7, 0.5), 'cool': (0.2, 0.0),
           'knows of': (0.25, 0.0), 'stranger': (0.08, 0.0), 'rival': (0.1, 0.0), 'usual': (1.0, 1.0)}
TIE_STANCES = {'family': 'close', 'married': 'close', 'partners': 'close', 'old friends': 'close',
               'known for years': 'friendly', 'friends': 'friendly', 'coworkers': 'coworkers', 'rivals': 'rival',
               'divorced': 'cool', 'separated': 'cool', 'knows of': 'knows of', 'known by': 'stranger'}
# Someone the role or the note calls the companion's rival (Kaito, Sett's rival).
RIVAL_WORDS = re.compile(r"\b(?:arch-?)?(?:rival|nemesis|enemy|enemies|foe|adversary|nemeses)s?\b", re.IGNORECASE)
# Trolls and snark on posts (life_settings.trolls_realism): 0 off, 1 rivals only (the default), 2 snarky, 3 trolls.
# How likely a rival is to comment, times COMMENT_CHANCE; at 3 someone parted from the poster snipes too.
TROLL_LEVELS, DEFAULT_TROLLS = 4, 1
RIVAL_TALKS = (0.0, 0.3, 0.7, 1.2)
COOL_TALKS = (0.0, 0.0, 0.0, 0.4)
LOG = logging.getLogger(__name__)


# Writing posts ----------------------------------------------------------------------------------

def refresh(database) -> None:
    """Write the social posts that are due on the active timeline. Cheap and idempotent. If writing them
    fails, the error is logged and the feed and Today still open with the posts already there."""
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        try:
            write(connection, companion, now)
        except Exception:
            connection.rollback()
            LOG.exception('Could not write new feed posts; showing the ones already there.')


def write(connection, companion, now: datetime) -> int:
    timeline_id = companion['active_timeline_id']
    # A branch shares its parent's history up to where it split off (copied in by `copy`).
    started = parse(one(connection, 'SELECT COALESCE(forked_at, created_at) AS started FROM timelines WHERE id=?',
                        (timeline_id,))['started'])
    since = max(now - LOOKBACK, started)
    if since > now:
        return 0  # The timeline starts later than now, as after Debug time's "keep what happened".
    people = active_people(connection, timeline_id)
    found = [*friend_posts(connection, timeline_id, people, since, now),
             *day_posts(connection, companion, people, since, now),
             *city_posts(connection, companion, since, now)]
    timestamp, written = stamp(now), 0
    for post in found:
        if not stamp(since) <= post['occurs_at'] <= timestamp:
            continue
        written += connection.execute(
            'INSERT OR IGNORE INTO social_posts (id, timeline_id, kind, author, idempotency_key, content, occurs_at, '
            'created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (identifier(), timeline_id, post['kind'], post['author'], post['key'], encode(post['content']),
             post['occurs_at'], timestamp)).rowcount
    return written


def active_people(connection, timeline_id) -> dict[str, dict]:
    """The circle as the posts show them: the role in their era's words ('mother' in 1895, circle.era_word), with
    how each knows the rest (`ties`, circle.ties: {other id: how}), whether they and the companion know each other
    (`knowing`, circle.knowing) and whether they are the companion's rival (`rival`)."""
    older = circle.voice_of(connection, timeline_id)
    rows = many(connection, "SELECT * FROM circle_people WHERE timeline_id=? AND status='active' ORDER BY ordinal",
                (timeline_id,))
    known = circle.ties(rows)
    return {row['id']: {'id': row['id'], 'name': row['name'], 'role': circle.era_word(row['role'], older),
                        'ties': {item['id']: item['how'] for item in known[row['id']]},
                        'knowing': circle.knowing(row), 'rival': rival_of_companion(row)}
            for row in rows}


def rival_of_companion(row: dict) -> bool:
    """Their role or note calls them the companion's rival (or nemesis, or enemy)."""
    return bool(RIVAL_WORDS.search(f"{row.get('role') or ''}. {circle.details_of(row).get('note') or ''}"))


def trolls(connection) -> int:
    """Settings > Realism > Trolls and snark on posts: 0 off ... 3 trolls."""
    row = optional(connection, 'SELECT trolls_realism FROM life_settings WHERE id=1')
    level = row['trolls_realism'] if row else None
    return level if level in range(TROLL_LEVELS) else DEFAULT_TROLLS


def place_name(place) -> str:
    if isinstance(place, dict):
        return place.get('name') or ''
    return place or ''


def friend_posts(connection, timeline_id, people, since, now) -> list[dict]:
    """At most one shared entry per person a day, and a few a day across the circle."""
    rows = many(connection, "SELECT * FROM life_agenda WHERE timeline_id=? AND subject!=? AND status='happened' "
                'AND entry IS NOT NULL AND ends_at>? AND ends_at<=? ORDER BY starts_at',
                (timeline_id, COMPANION, stamp(since), stamp(now)))
    result, posted, daily = [], set(), {}
    for row in rows:
        entry, block = decode(row['entry']), decode(row['block'])
        key = f"friend:{timeline_id}:{row['subject']}:{row['slot_key']}"
        day = (row['subject'], row['local_date'])
        if row['subject'] not in people or day in posted or daily.get(row['local_date'], 0) >= FRIEND_DAILY:
            continue
        if unit(key, 'share') >= SHARE.get(block.get('kind'), 0.1) or not isinstance(entry.get('post'), str):
            continue
        posted.add(day)
        daily[row['local_date']] = daily.get(row['local_date'], 0) + 1
        result.append({'kind': 'friend', 'author': row['subject'], 'key': key, 'occurs_at': row['ends_at'],
                       'content': {'text': entry['post'] or entry['summary'], 'context': entry['summary'],
                                   'place': place_name(entry.get('place')), 'mood': entry.get('mood') or ''}})
    return result


def local_dates(since: datetime, now: datetime, timezone: str) -> list[date]:
    first, last = since.astimezone(zone(timezone)).date(), now.astimezone(zone(timezone)).date()
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


def at(day: date, timezone: str, seed: str, earliest: int, latest: int) -> str:
    """A seeded moment between two local hours on a local date."""
    minutes = earliest * 60 + int(unit(seed, 'time') * (latest - earliest) * 60)
    moment = datetime.combine(day, time(minutes // 60, minutes % 60), zone(timezone))
    return stamp(moment)


def day_facts(connection, timeline_id, local_date: str) -> dict:
    """What the companion's agenda knows about one local day: weather, holiday, annual events, body."""
    facts = {'weather': None, 'holiday': None, 'happenings': [], 'body': None}
    for row in many(connection, 'SELECT block FROM life_agenda WHERE timeline_id=? AND subject=? AND local_date=? '
                    'ORDER BY starts_at', (timeline_id, COMPANION, local_date)):
        block = decode(row['block'])
        for name in facts:
            facts[name] = facts[name] or block.get(name)
    return facts


def culture_picks(connection, now, definition) -> dict[str, str]:
    """The top movie, show, song and book of today's culture digest, by section, when there is a fresh one."""
    from companion.mcp.lookups import fresh_culture
    digest = fresh_culture(connection, now, definition)
    found = ((digest or {}).get('structured') or {}).get('found')
    picks = {}
    for section in ('movies', 'tv', 'music', 'books') if isinstance(found, dict) else ():
        lists = found.get(section) if isinstance(found.get(section), dict) else {}
        # Songs read better than albums ("Can't get Song A by Artist A out of my head").
        items = next((value for title, value in lists.items() if isinstance(value, list) and value
                      and (section != 'music' or 'songs' in title)), None)
        name = re.sub(r'\s*\([^)]*\)$', '', str(items[0])).strip()[:80] if items else ''
        if name:
            picks[section] = name
    return picks


def day_posts(connection, companion, people, since, now) -> list[dict]:
    timeline_id, version = companion['active_timeline_id'], companion['version']
    timezone, definition = version['timezone'], version['definition']
    result = []
    days = local_dates(since, now, timezone)
    fits = fits_world(connection, definition)
    said = Said(connection, timeline_id)
    for day in days:
        local_date, prefix = day.isoformat(), f'{timeline_id}:{day.isoformat()}'
        facts = day_facts(connection, timeline_id, local_date)
        # Today's charts only for today: a day being caught up on never borrows them.
        facts['culture'] = culture_picks(connection, now, definition) if day == days[-1] else {}
        grieving = loss.raw_or_heavy(connection, timeline_id, day)
        if unit(prefix, 'status') < STATUS_CHANCE:
            occurs_at = at(day, timezone, f'status:{prefix}', 8, 22)
            result.append(said.post('status', f'status:{prefix}', occurs_at, lambda recent: (
                {'text': pick(prefix, 'line', list(STATUS['grief'])), 'tone': 'down'} if grieving else
                dict(zip(('text', 'tone'), status_text(prefix, day, facts, definition, fits, recent),
                         strict=True)))))
        if grieving:
            continue  # Only a quiet status while grief is raw or heavy.
        if unit(prefix, 'question') < QUESTION_CHANCE:
            occurs_at = at(day, timezone, f'question:{prefix}', 12, 21)
            result.append(said.post('question', f'question:{prefix}', occurs_at, lambda _recent: question_content(
                prefix, [item for item in QUESTIONS if fits(' '.join([item[0], *item[1]]))], said.asked)))
        result += celebrations(prefix, day, timezone, facts, people)
    # Date nights and steps with someone they are seeing (companion/life/love_life.py).
    # The day they got engaged to the user (companion/life/wedding.py).
    return result + love_life.feed_posts(connection, companion, days, timezone) + \
        wedding.feed_posts(connection, companion, days, timezone)


class Said:
    """What the companion already said in status and question posts on this timeline, so the feed doesn't repeat
    itself: a day already posted keeps what it said, a new status skips lines used within STATUS_GAP and a new
    question skips every question asked before, answered or not, until all that fit have been asked."""

    def __init__(self, connection, timeline_id):
        rows = many(connection, "SELECT idempotency_key, kind, content, occurs_at FROM social_posts WHERE timeline_id=? "
                    "AND author=? AND kind IN ('status', 'question') ORDER BY occurs_at", (timeline_id, COMPANION))
        self.stored = {row['idempotency_key']: decode(row['content']) for row in rows}
        self.lines: dict[str, str] = {}
        self.asked: dict[str, str] = {}
        for row in rows:
            self.note(row['kind'], self.stored[row['idempotency_key']].get('text'), row['occurs_at'])

    def note(self, kind, text, occurs_at):
        if isinstance(text, str):
            (self.asked if kind == 'question' else self.lines)[text] = occurs_at

    def recent(self, occurs_at) -> set[str]:
        moment = parse(occurs_at)
        since, until = stamp(moment - STATUS_GAP), stamp(moment + STATUS_GAP)
        return {text for text, said_at in self.lines.items() if since <= said_at <= until}

    def post(self, kind, key, occurs_at, content) -> dict:
        """The post under `key`: as already written, or new from `content(recent lines)`."""
        found = self.stored.get(key) or content(self.recent(occurs_at))
        if key not in self.stored:
            self.note(kind, found.get('text'), occurs_at)
        return own(kind, key, occurs_at, found)


def question_content(seed: str, questions: list, asked: dict[str, str]) -> dict:
    """A question not asked before; once all have been, one of the half asked longest ago."""
    fresh = [item for item in questions if item[0] not in asked]
    if not fresh:
        oldest = sorted(questions, key=lambda item: asked.get(item[0], ''))
        fresh = oldest[:max(1, len(oldest) // 2)]
    question, options = pick(seed, 'question', fresh)
    return {'text': question, 'options': list(options)}


def own(kind, key, occurs_at, content) -> dict:
    return {'kind': kind, 'author': COMPANION, 'key': key, 'occurs_at': occurs_at, 'content': content}


def fits_world(connection, definition: dict):
    """Whether a status or question line suits the companion's world: its era (TODAYS, COFFEE) and whether they
    live aboard (GROUNDED)."""
    from companion.world import ships
    data = city_data(connection, definition)
    era = (data or {}).get('era', 'modern')
    aboard = bool(data) and ships.enclosed(data)

    def fits(text: str) -> bool:
        return not ((era not in TODAYS_ERAS and TODAYS.search(text)) or (era in NO_COFFEE_ERAS and COFFEE.search(text))
                    or (aboard and GROUNDED.search(text)))
    return fits


def status_text(seed: str, day: date, facts: dict, definition: dict, fits=lambda _text: True,
                recent: set[str] = frozenset()) -> tuple[str, str]:
    """A thought that fits the day and the world (`fits`) and claims nothing happened, and that isn't one of the
    `recent` lines when another will do. Returns the text and its tone."""
    def fresh(lines):
        lines = [line for line in lines if fits(line)]
        return [line for line in lines if line not in recent] or lines
    state = (facts['body'] or {}).get('state')
    if state in STATUS and (lines := fresh(STATUS[state])):
        return pick(seed, 'line', lines), 'sick' if state == 'sick' else 'down'
    offered = fresh(STATUS['any'])
    choices = [pick(seed, f'any:{n}', offered) for n in range(ANY_OFFERED)]
    weather = facts['weather'] or {}
    if weather:
        hot, cold = weather.get('high_f', 60) >= HOT_F, weather.get('high_f', 60) <= COLD_F
        choices += STATUS['rain' if weather.get('rain') else 'hot' if hot else 'cold' if cold else 'mild'] * 2
    choices += {0: STATUS['monday'], 4: STATUS['friday']}.get(day.weekday(), ())
    for section, item in (facts.get('culture') or {}).items():
        choices += [line.format(item=item) for line in STATUS[section]]
    interests = [text for text in definition.get('interests', ()) if text and len(text) <= 40]
    if interests:
        interest = pick(seed, 'interest', interests)
        choices += [line.format(interest=interest_text(interest)) for line in STATUS['interest']]
    return pick(seed, 'line', fresh(choices) or offered or list(STATUS['any'])), ''


def interest_text(interest: str) -> str:
    """An interest as it reads mid-sentence: "Fell down a History of Medicine museum rabbit hole", never
    "a the history of medicine museum"; names keep their capitals, a capitalised first word alone does not."""
    text = re.sub(r'^(?:the|a|an)\s+', '', interest.strip(), flags=re.IGNORECASE)
    words = text.split()
    if words and all(word == word.lower() for word in words[1:]):
        text = text[:1].lower() + text[1:]
    return text


def celebrations(prefix, day, timezone, facts, people) -> list[dict]:
    result = []
    for person in people.values():
        if circle.birthday(person['id']) != day.isoformat()[5:]:
            continue
        key = f"birthday:{prefix}:{person['id']}"
        family = person['role'] in {'sibling', 'cousin'}
        text = FAMILY_BIRTHDAY if family else pick(key, 'line', list(BIRTHDAY))
        result.append(own('birthday', key, at(day, timezone, key, 9, 11),
                          {'text': text.format(name=person['name'], role=person['role']), 'person': person['id']}))
    if facts['holiday']:
        key = f'holiday:{prefix}'
        result.append(own('holiday', key, at(day, timezone, key, 9, 12),
                          {'text': pick(key, 'line', list(HOLIDAY)).format(holiday=facts['holiday'])}))
    for event in (facts['happenings'] or [])[:1]:
        key = f"happening:{prefix}:{event['name']}"
        if unit(key, 'share') < HAPPENING_CHANCE:
            where = f" in {event['neighborhood']}" if event.get('neighborhood') else ''
            result.append(own('city', key, at(day, timezone, key, 8, 11),
                              {'text': pick(key, 'line', list(HAPPENING)).format(event=event['name'], where=where),
                               'change': 'happening'}))
    return result


def city_data(connection, definition):
    from companion.world import changes, custom
    extra = custom.all_cities(connection)
    for text in (definition.get('home_city'), definition.get('location')):
        if text and (data := changes.resolve(text, extra)):
            return data
    return None


def city_posts(connection, companion, since, now) -> list[dict]:
    """City news the companion passes on the day people hear of it."""
    from companion.world import changes
    timeline_id, version = companion['active_timeline_id'], companion['version']
    data = city_data(connection, version['definition'])
    if not data:
        return []
    timezone = version['timezone']
    days = local_dates(since, now, timezone)
    hoods = {hood['id']: hood['name'] for hood in data['neighborhoods']}
    result = []
    for change in changes.known(data, days[-1], changes.stored(connection, data['id'])):
        heard = date.fromisoformat(change['announced'] or change['starts'])
        key = f"city:{timeline_id}:{change['id']}"
        if heard < days[0] or change['kind'] == 'news' or unit(key, 'share') >= CITY_CHANCE or \
                loss.raw_or_heavy(connection, timeline_id, heard):
            continue
        text = change_text(change, hoods.get(change['neighborhood'], ''), days[-1])
        result.append(own('city', key, at(heard, timezone, key, 8, 21), {'text': text, 'change': change['kind']}))
    return result


def change_text(change: dict, where: str, today: date) -> str:
    name, summary, starts = change['name'], change['summary'], date.fromisoformat(change['starts'])
    soon = starts > today
    when = f'{starts:%A}, {starts:%B} {starts.day}'
    place = f' in {where}' if where else ''
    if change['kind'] == 'opening':
        return f"{name} is opening{place} on {when}. Who's coming with me?" if soon \
            else f'{name} just opened{place}. Who wants to try it?'
    if change['kind'] == 'closing':
        return f'{name} is closing. {summary.capitalize()}. End of an era.' if summary else f'{name} is closing.'
    if change['kind'] == 'roadworks':
        return f'Road works{place} again. Leave extra time if you are going that way.'
    return f'{name}{place}: {summary}.' if summary else f'{name}{place} is changing.'


# Reading posts ----------------------------------------------------------------------------------

def author_view(author: str, people: dict, name: str) -> dict | None:
    if author == COMPANION:
        return {'kind': 'companion', 'id': None, 'name': name, 'role': ''}
    person = people.get(author)
    return person and {'kind': 'person', 'id': person['id'], 'name': person['name'], 'role': person['role']}


def manner(definition: dict) -> str:
    """'reserved', 'warm' or 'usual', from words in their sheet and how sociable they are (companion/life/circle.py)."""
    text = ' '.join(definition.get(field) or '' for field in ('identity', 'personality', 'voice'))
    sociable = circle.sociability(definition)
    reserved = len(RESERVED_WORDS.findall(text)) + (sociable == 'quiet')
    warm = len(WARM_WORDS.findall(text)) + (sociable == 'social')
    return 'reserved' if reserved > warm else 'warm' if warm > reserved else 'usual'


def known_audience(connection, companion: dict, now: datetime) -> list[dict]:
    """The other companions who know this one, each with their chances to like and comment on its own posts."""
    from companion.characters import by_id
    from companion.memory import pairs
    key, result = pairs.companion_key(companion['id']), []
    try:
        for other in pairs.known_companions(connection, companion, now):
            found, them = pairs.closeness(connection, other, key, now), by_id(connection, pairs.companion_id(other))
            if not found or them is None:
                continue
            likes, comments = MANNERS[style := manner(them['version']['definition'])]
            result.append({'key': other, 'name': them['version']['name'], 'manner': style,
                           'since': them['created_at'],
                           'like': min(KNOWN_LIKES[found - 1] * likes, KNOWN_MOST[0]),
                           'comment': min(KNOWN_COMMENTS[found - 1] * comments, KNOWN_MOST[1])})
    except Exception:  # noqa: BLE001 - who else knows them never keeps the feed from opening.
        LOG.exception('Could not work out which companions know %s', companion['id'])
        return []
    return result


# What a dig sounds like at each level of trolls (`chances`): dry at 1, snarkier at 2, rude at 3.
SNARK = {'rival': post_snark.RIVAL, 'snark': post_snark.RIVAL + post_snark.TROLL, 'troll': post_snark.TROLL}
SNARK_STYLES = ('', 'rival', 'snark', 'troll')


def comment_pool(kind: str, content: dict, commenter: str, by_companion: bool, style: str = '') -> tuple[str, ...]:
    if by_companion:
        return COMMENTS['from_companion']
    if style == 'reserved':
        if content.get('text') in STATUS['grief']:
            return RESERVED_COMMENTS['grief']
        if content.get('tone') in ('sick', 'down') or content.get('mood') in SICK | DOWN:
            return RESERVED_COMMENTS['down']
        return RESERVED_COMMENTS['question'] if kind == 'question' else RESERVED_COMMENTS['general']
    if kind == 'birthday':
        return COMMENTS['birthday_self'] if commenter == content.get('person') else COMMENTS['birthday']
    if kind == 'city':
        return COMMENTS.get(content.get('change'), COMMENTS['city'])
    if content.get('text') in STATUS['grief']:
        return COMMENTS['grief']
    if content.get('tone') == 'sick' or content.get('mood') in SICK:
        return COMMENTS['sick']
    if content.get('tone') == 'down' or content.get('mood') in DOWN:
        return COMMENTS['down']
    return COMMENTS['question'] if kind == 'question' else COMMENTS['general']


def stance(who: str, author: str, people: dict) -> str:
    """How `who` (a circle person's id, or COMPANION) stands with the post's author: a STANCES key."""
    if author == COMPANION:  # A circle person on the companion's own post.
        person = people.get(who, {})
        return 'stranger' if person.get('knowing') == 'companion' else 'rival' if person.get('rival') else 'usual'
    poster = people.get(author, {})
    if who == COMPANION:
        if poster.get('knowing') == 'they':  # They know the companion; the companion doesn't know them.
            return 'stranger'
        return 'knows of' if poster.get('knowing') == 'companion' else 'rival' if poster.get('rival') else 'usual'
    how = people.get(who, {}).get('ties', {}).get(author)
    return TIE_STANCES.get(how, 'friendly') if how else 'stranger'


def sensitive(kind: str, content: dict) -> bool:
    """A post nobody snipes at: a birthday, a question, city news, or someone sick, down or grieving."""
    return kind in ('birthday', 'question', 'city') or content.get('text') in STATUS['grief'] or \
        content.get('tone') in ('sick', 'down') or content.get('mood') in SICK | DOWN


def chances(found: str, like: float, talks: float, level: int, touchy: bool) -> tuple[float, float, str]:
    """Like and comment chances for someone of stance `found` whose usual chances are `like` and `talks`, and the
    style their comment takes (SNARK_STYLES for a dig)."""
    if found == 'rival' or (found == 'cool' and COOL_TALKS[level]):
        snipes = 0.0 if touchy else (RIVAL_TALKS if found == 'rival' else COOL_TALKS)[level] * COMMENT_CHANCE
        return (0.0 if level == 0 else like * STANCES[found][0]), snipes, SNARK_STYLES[level]
    scale_like, scale_talk = STANCES[found]
    return min(like * scale_like, 1), min(talks * scale_talk, 1), ''


def crowd_of(author: str, kind: str, content: dict, occurs_at: str, people: dict, companion_name: str,
             known: tuple, level: int) -> list[tuple]:
    """Everyone who might react: (who, name, like chance, comment chance, style)."""
    touchy, crowd = sensitive(kind, content), []
    for person_id, person in people.items():
        found = stance(person_id, author, people)
        crowd.append((person_id, person['name'],
                      *chances(found, LIKELY.get(person['role'], 0.45), COMMENT_CHANCE, level, touchy)))
    if author != COMPANION:
        found = stance(COMPANION, author, people)
        like, talks, style = chances(found, COMPANION_LIKES, COMMENT_CHANCE, level, touchy)
        crowd.append((COMPANION, companion_name, like, talks, style))
    else:
        crowd += [(other['key'], other['name'], other['like'], other['comment'], other['manner'])
                  for other in known if other['since'] <= occurs_at]
    return crowd


def audience(post_id: str, kind: str, author: str, content: dict, occurs_at: str, now: str, people: dict,
             companion_name: str, avoid: frozenset[str] = frozenset(), known: tuple = (),
             level: int = DEFAULT_TROLLS) -> dict:
    """Who liked and commented by `now`, from the post and the circle alone. The companion joins in
    on friends' posts; friends join in on everyone's; other companions who know the companion
    (`known_audience`) join in on the companion's own posts, if they were around when it went up.
    How each stands with the poster (`stance`) sets their chances, and `level` (trolls) what a rival
    says. No line is said twice on a post, and lines in `avoid` (said on the posts just before) are
    left for later."""
    occurred = parse(occurs_at)
    crowd = crowd_of(author, kind, content, occurs_at, people, companion_name, known, level)
    likes, speakers = [], []
    for who, name, chance, talks, style in crowd:
        if who == author and kind != 'birthday':
            continue
        seed = f'{post_id}:{who}'
        liked_at = stamp(occurred + REACTION_WINDOW * unit(seed, 'like-at'))
        thanked = kind == 'birthday' and who == content.get('person')
        if (unit(seed, 'like') < chance or thanked) and liked_at <= now:
            likes.append(name)
        said = stamp(occurred + REACTION_WINDOW * unit(seed, 'comment-at'))
        if (unit(seed, 'comment') < talks or thanked) and said <= now:
            speakers.append((said, who, name, seed, style))
    comments, used = [], set(avoid)
    for said, who, name, seed, style in sorted(speakers)[:MAX_COMMENTS]:
        option = pick(seed, 'option', content.get('options') or [''])
        lines = [line.format(name=people.get(content.get('person'), {}).get('name', ''), option=option)
                 for line in SNARK.get(style) or comment_pool(kind, content, who, who == COMPANION, style)]
        fresh = [line for line in lines if line not in used]
        if not fresh:
            continue  # Everything this person would say was just said.
        text = pick(seed, 'comment', fresh)
        used.add(text)
        comments.append({'author': 'companion' if who == COMPANION or who.startswith('companion:') else 'person',
                         'name': name, 'at': said, 'text': text})
    return {'likes': likes, 'comments': comments}


# How many earlier posts a comment line is not repeated across.
NEARBY = 10


def add_audiences(posts: list[dict], now: str, people: dict, companion_name: str, known: tuple = (),
                  everyone: tuple = (), level: int = DEFAULT_TROLLS) -> None:
    """Fill in each post's likes and comments, oldest first, so a line said on one post is not said
    again on the next few. Posts carry their basis as `_basis` (author, content); it is removed here.
    The user's own posts (companion/life/user_posts.py) go to `everyone` who can see them."""
    from companion.life import user_posts
    recent: list[set[str]] = []
    for post in sorted(posts, key=lambda post: (post['occurs_at'], post['id'])):
        basis = post.pop('_basis', None)
        avoid = frozenset().union(*recent[-NEARBY:])
        if basis is None:
            post['audience'] = {'likes': [], 'comments': []}
            continue
        if basis[0] == user_posts.USER:
            post['audience'] = user_posts.audience(post['id'], basis[1], post['occurs_at'], now, list(everyone), avoid)
        else:
            post['audience'] = audience(post['id'], post['kind'], basis[0], basis[1], post['occurs_at'], now, people,
                                        companion_name, avoid, known, level)
        recent.append({comment['text'] for comment in post['audience']['comments']})


def view(row: dict, people: dict, companion_name: str) -> dict | None:
    """A social post shaped like a feed post: no events and no image, with its own text. Its likes and
    comments are added by `add_audiences` from `_basis`."""
    author = author_view(row['author'], people, companion_name)
    removed = row['status'] == 'removed'
    if author is None and not removed:
        return None  # Its author left the circle.
    content = {} if removed else decode(row['content'])
    text, context = content.get('text', ''), content.get('context', '')
    if row['kind'] == 'friend' and author:
        # A friend's entry names them in the third person; on their own post they say it as "I".
        text, context = (composer.mine(text, author['name']) if text == context else text), \
            composer.mine(context, author['name'])
    return {'id': row['id'], 'kind': row['kind'], 'source': 'social', 'author': author,
            'intro': '', 'events': [], 'text': text, 'context': context,
            'place': content.get('place', ''), 'options': content.get('options', []), 'answer': row['answer'],
            'status': row['status'], 'read': row['read_at'] is not None, 'read_at': row['read_at'],
            'reaction': row['reaction'], 'occurs_at': row['occurs_at'], 'created_at': row['created_at'],
            'image': None, '_basis': None if removed else (row['author'], content)}


def visible(connection, companion, include_hidden=False) -> list[dict]:
    timeline_id = companion['active_timeline_id']
    statuses = "('visible','hidden')" if include_hidden else "('visible')"
    people = active_people(connection, timeline_id)
    rows = many(connection, f'SELECT * FROM social_posts WHERE timeline_id=? AND status IN {statuses} '
                'ORDER BY occurs_at DESC, id DESC', (timeline_id,))
    return [shown for shown in (view(row, people, companion['version']['name']) for row in rows) if shown]


def find(connection, post_id) -> dict | None:
    return optional(connection, 'SELECT * FROM social_posts WHERE id=?', (post_id,))


def unread(connection, timeline_id) -> int:
    """Unread visible posts whose author is the companion or still in the circle."""
    return one(connection, "SELECT COUNT(*) AS count FROM social_posts WHERE timeline_id=? AND status='visible' "
               "AND read_at IS NULL AND (author=? OR author IN (SELECT id FROM circle_people WHERE timeline_id=? "
               "AND status='active'))", (timeline_id, COMPANION, timeline_id))['count']


# Changing posts ---------------------------------------------------------------------------------

def mark_read(connection, timeline_id, timestamp, post_ids=None):
    if post_ids is None:
        connection.execute('UPDATE social_posts SET read_at=? WHERE timeline_id=? AND read_at IS NULL',
                           (timestamp, timeline_id))
    else:
        connection.executemany('UPDATE social_posts SET read_at=? WHERE id=? AND timeline_id=? AND read_at IS NULL',
                               [(timestamp, post_id, timeline_id) for post_id in post_ids])


def set_status(connection, row, status, timestamp):
    require(row['status'] != 'removed', 'This post was removed.', 409)
    if status == 'removed':
        connection.execute("UPDATE social_posts SET status='removed', content='{}', reaction=NULL, answer=NULL, "
                           'removed_at=? WHERE id=?', (timestamp, row['id']))
    else:
        connection.execute('UPDATE social_posts SET status=? WHERE id=?', (status, row['id']))


def react(connection, row, reaction, timestamp):
    require(row['status'] != 'removed', 'This post was removed.', 409)
    connection.execute('UPDATE social_posts SET reaction=?, read_at=COALESCE(read_at, ?) WHERE id=?',
                       (reaction, timestamp, row['id']))


def link_message(connection, row, message_id, timestamp):
    require(row['status'] != 'removed', 'This post was removed.', 409)
    connection.execute('INSERT OR IGNORE INTO message_social_links (message_id, post_id) VALUES (?, ?)',
                       (message_id, row['id']))
    connection.execute('UPDATE social_posts SET read_at=COALESCE(read_at, ?) WHERE id=?', (timestamp, row['id']))


def answer(database, post_id, option: str) -> None:
    """The user's pick on a question post. It is sent to chat as a reply to the post as well."""
    with database.connect(write=True) as connection:
        row = find(connection, post_id)
        require(row is not None, 'This item could not be found.', 404)
        require(row['kind'] == 'question' and row['status'] != 'removed', 'Only a question can be answered.', 409)
        require(option in decode(row['content']).get('options', []), 'That is not one of the choices.', 422)
        connection.execute('UPDATE social_posts SET answer=?, read_at=COALESCE(read_at, ?) WHERE id=?',
                           (option, database.now(), post_id))


def linked(connection, message_id) -> dict | None:
    """The social post a chat message replies to, shaped for the chat context's feed reference:
    an intro saying whose post it is and what it said, and no events."""
    link = optional(connection, 'SELECT post_id FROM message_social_links WHERE message_id=?', (message_id,))
    row = link and find(connection, link['post_id'])
    if not row or row['status'] == 'removed':
        return None
    return {'id': row['id'], 'intro': reference_text(connection, row), 'events': []}


def reference_text(connection, row) -> str:
    content = decode(row['content'])
    if row['author'] == COMPANION:
        text = f"The user is replying to your own {row['kind']} post on the feed: «{content.get('text', '')}»."
    else:
        person = optional(connection, 'SELECT name FROM circle_people WHERE id=?', (row['author'],))
        name = person['name'] if person else 'A friend'
        text = (f"The user is replying to a post by {name} from your circle: «{content.get('text', '')}» "
                f"({content.get('context', '')}).")
    if content.get('options'):
        text += f" Choices: {' / '.join(content['options'])}."
    if row['answer']:
        text += f" The user picked: {row['answer']}."
    return text


def copy(connection, parent_id, new_id, cutoff: str, ids: dict, remap) -> None:
    """A branch keeps the social posts its parent had by the time it split off, with their read,
    reaction and answer state, and the chat replies to them. `ids` maps the parent's identities
    (timeline, circle people, messages) to the copies; `remap` rewrites them inside stored text."""
    rows = many(connection, 'SELECT * FROM social_posts WHERE timeline_id=? AND occurs_at<=?', (parent_id, cutoff))
    copies = {row['id']: identifier() for row in rows}
    connection.executemany(
        'INSERT OR IGNORE INTO social_posts (id, timeline_id, kind, author, idempotency_key, content, answer, status, '
        'reaction, occurs_at, created_at, read_at, removed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [(copies[row['id']], new_id, row['kind'], ids.get(row['author'], row['author']),
          remap(row['idempotency_key'], ids), remap(row['content'], ids), row['answer'], row['status'],
          row['reaction'], row['occurs_at'], row['created_at'], row['read_at'], row['removed_at']) for row in rows])
    links = many(connection, 'SELECT * FROM message_social_links WHERE post_id IN (SELECT id FROM social_posts '
                 'WHERE timeline_id=?)', (parent_id,))
    connection.executemany('INSERT OR IGNORE INTO message_social_links (message_id, post_id) VALUES (?, ?)',
                           [(ids[link['message_id']], copies[link['post_id']]) for link in links
                            if link['message_id'] in ids and link['post_id'] in copies])
