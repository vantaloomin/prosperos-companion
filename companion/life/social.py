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

Posts are written when the feed or Today is read, for the last few days up to now, under
idempotency keys seeded by the timeline and slot, so reading twice never posts twice. Likes and
comments are not stored: they follow from the post, the circle and the clock, so a comment shows
up some time after its post, a renamed friend comments under the new name and a removed one
leaves the conversation. The companion likes and comments on friends' posts the same way.
"""
from datetime import date, datetime, time, timedelta

from companion.characters import require_current
from companion.clock import parse, stamp, zone
from companion.database import decode, encode, identifier, many, one, optional
from companion.errors import require
from companion.life import circle
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
    'any': ('Small wins today.', "Some days are just quiet, and that's fine.", 'Good music, good mood.',
            'Note to self: drink more water.'),
}
QUESTIONS = (
    ('Dinner tonight?', ('Tacos', 'Ramen')),
    ('Movie night: something scary or something cozy?', ('Scary', 'Cozy')),
    ('Coffee or tea this morning?', ('Coffee', 'Tea')),
    ('Thinking about cutting my hair short. Yes or no?', ('Do it', "Don't you dare")),
    ('Early night or one more episode?', ('Early night', 'One more episode')),
    ('Beach or mountains?', ('Beach', 'Mountains')),
    ('Is pineapple on pizza okay?', ('Yes', 'Absolutely not')),
    ('Sunrise or sunset?', ('Sunrise', 'Sunset')),
)
BIRTHDAY = ('Happy birthday, {name}! 🎂', 'Happy birthday to {name}, who makes everything more fun. 🎉',
            'Another year of {name}. Lucky us. Happy birthday! 🎂')
FAMILY_BIRTHDAY = 'Happy birthday to my favorite {role}, {name}! 🎂'
HOLIDAY = ('Happy {holiday}, everyone!', '{holiday} and a day off. Perfect.', 'Happy {holiday}! Taking it easy today.')
HAPPENING = ('{event} is on today{where}. Anyone going?', 'Reminder that {event} is today{where}.')

COMMENTS = {
    'general': ('Love this!', 'This is so you.', 'Jealous.', 'Save me a spot next time.', 'Wait, I need details.',
                '😂', 'Looks like a good day.', 'Same, honestly.', 'Call me later?'),
    'sick': ('Feel better!', 'Sending soup.', 'Oh no. Need anything?'),
    'down': ('Rest up!', 'Hang in there.', 'You deserve a nap.', 'Big hug.'),
    'birthday': ('Happy birthday, {name}! 🎉', 'Happy birthday!! 🥳', 'Have the best day, {name}!'),
    'birthday_self': ('Thank you!! ❤️', 'You are the sweetest.', 'Love you for this.'),
    'opening': ("Ooh, I'm in.", 'Count me in.', 'Saturday?'),
    'closing': ('Noooo.', 'End of an era.', 'Wait, really?'),
    'city': ('Good to know.', 'Thanks for the heads up.', 'Ugh.'),
    'question': ('{option}, obviously.', '{option}. No contest.', 'Team {option}.'),
    'from_companion': ('Love this!', "Wish I'd been there.", 'Look at you!', 'Okay, I need the full story.',
                       "Next time I'm coming.", 'This made my day.'),
}
LIKELY = {'close friend': 0.85, 'sibling': 0.7, 'roommate from years ago': 0.55}
COMMENT_CHANCE, COMPANION_LIKES = 0.22, 0.7


# Writing posts ----------------------------------------------------------------------------------

def refresh(database) -> None:
    """Write the social posts that are due on the active timeline. Cheap and idempotent."""
    now = database.clock.now()
    with database.connect(write=True) as connection:
        write(connection, require_current(connection), now)


def write(connection, companion, now: datetime) -> int:
    timeline_id = companion['active_timeline_id']
    # A branch shares its parent's history up to where it split off (copied in by `copy`).
    started = parse(one(connection, 'SELECT COALESCE(forked_at, created_at) AS started FROM timelines WHERE id=?',
                        (timeline_id,))['started'])
    since = max(now - LOOKBACK, started)
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
    return {row['id']: {'id': row['id'], 'name': row['name'], 'role': row['role']}
            for row in many(connection, "SELECT id, name, role FROM circle_people WHERE timeline_id=? "
                            "AND status='active' ORDER BY ordinal", (timeline_id,))}


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


def day_posts(connection, companion, people, since, now) -> list[dict]:
    timeline_id, version = companion['active_timeline_id'], companion['version']
    timezone, definition = version['timezone'], version['definition']
    result = []
    for day in local_dates(since, now, timezone):
        local_date, prefix = day.isoformat(), f'{timeline_id}:{day.isoformat()}'
        facts = day_facts(connection, timeline_id, local_date)
        if unit(prefix, 'status') < STATUS_CHANCE:
            text, tone = status_text(prefix, day, facts, definition)
            result.append(own('status', f'status:{prefix}', at(day, timezone, f'status:{prefix}', 8, 22),
                              {'text': text, 'tone': tone}))
        if unit(prefix, 'question') < QUESTION_CHANCE:
            question, options = pick(prefix, 'question', list(QUESTIONS))
            result.append(own('question', f'question:{prefix}', at(day, timezone, f'question:{prefix}', 12, 21),
                              {'text': question, 'options': list(options)}))
        result += celebrations(prefix, day, timezone, facts, people)
    return result


def own(kind, key, occurs_at, content) -> dict:
    return {'kind': kind, 'author': COMPANION, 'key': key, 'occurs_at': occurs_at, 'content': content}


def status_text(seed: str, day: date, facts: dict, definition: dict) -> tuple[str, str]:
    """A thought that fits the day and claims nothing happened. Returns the text and its tone."""
    state = (facts['body'] or {}).get('state')
    if state in STATUS:
        return pick(seed, 'line', list(STATUS[state])), 'sick' if state == 'sick' else 'down'
    choices = [*STATUS['any']]
    weather = facts['weather'] or {}
    if weather:
        hot, cold = weather.get('high_f', 60) >= HOT_F, weather.get('high_f', 60) <= COLD_F
        choices += STATUS['rain' if weather.get('rain') else 'hot' if hot else 'cold' if cold else 'mild'] * 2
    choices += {0: STATUS['monday'], 4: STATUS['friday']}.get(day.weekday(), ())
    interests = [text for text in definition.get('interests', ()) if text and len(text) <= 40]
    if interests:
        interest = pick(seed, 'interest', interests)
        choices += [line.format(interest=interest.lower()) for line in STATUS['interest']]
    return pick(seed, 'line', choices), ''


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
        if heard < days[0] or change['kind'] == 'news' or unit(key, 'share') >= CITY_CHANCE:
            continue
        text = change_text(change, hoods.get(change['neighborhood'], ''), days[-1])
        result.append(own('city', key, at(heard, timezone, key, 8, 21), {'text': text, 'change': change['kind']}))
    return result


def change_text(change: dict, where: str, today: date) -> str:
    name, summary, starts = change['name'], change['summary'], date.fromisoformat(change['starts'])
    soon = starts > today
    when = f'{starts:%A} {starts.day} {starts:%B}'
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


def comment_pool(kind: str, content: dict, commenter: str, by_companion: bool) -> tuple[str, ...]:
    if by_companion:
        return COMMENTS['from_companion']
    if kind == 'birthday':
        return COMMENTS['birthday_self'] if commenter == content.get('person') else COMMENTS['birthday']
    if kind == 'city':
        return COMMENTS.get(content.get('change'), COMMENTS['city'])
    if content.get('tone') == 'sick' or content.get('mood') in SICK:
        return COMMENTS['sick']
    if content.get('tone') == 'down' or content.get('mood') in DOWN:
        return COMMENTS['down']
    return COMMENTS['question'] if kind == 'question' else COMMENTS['general']


def audience(post_id: str, kind: str, author: str, content: dict, occurs_at: str, now: str, people: dict,
             companion_name: str, avoid: frozenset[str] = frozenset()) -> dict:
    """Who liked and commented by `now`, from the post and the circle alone. The companion joins in
    on friends' posts; friends join in on everyone's. No line is said twice on a post, and lines in
    `avoid` (said on the posts just before) are left for later."""
    occurred = parse(occurs_at)
    crowd = [(person_id, person['name'], LIKELY.get(person['role'], 0.45)) for person_id, person in people.items()]
    if author != COMPANION:
        crowd.append((COMPANION, companion_name, COMPANION_LIKES))
    likes, speakers = [], []
    for who, name, chance in crowd:
        if who == author and kind != 'birthday':
            continue
        seed = f'{post_id}:{who}'
        liked_at = stamp(occurred + REACTION_WINDOW * unit(seed, 'like-at'))
        thanked = kind == 'birthday' and who == content.get('person')
        if (unit(seed, 'like') < chance or thanked) and liked_at <= now:
            likes.append(name)
        said = stamp(occurred + REACTION_WINDOW * unit(seed, 'comment-at'))
        if (unit(seed, 'comment') < COMMENT_CHANCE or thanked) and said <= now:
            speakers.append((said, who, name, seed))
    comments, used = [], set(avoid)
    for said, who, name, seed in sorted(speakers)[:MAX_COMMENTS]:
        option = pick(seed, 'option', content.get('options') or [''])
        lines = [line.format(name=people.get(content.get('person'), {}).get('name', ''), option=option)
                 for line in comment_pool(kind, content, who, who == COMPANION)]
        fresh = [line for line in lines if line not in used]
        if not fresh:
            continue  # Everything this person would say was just said.
        text = pick(seed, 'comment', fresh)
        used.add(text)
        comments.append({'author': 'companion' if who == COMPANION else 'person', 'name': name, 'at': said,
                         'text': text})
    return {'likes': likes, 'comments': comments}


# How many earlier posts a comment line is not repeated across.
NEARBY = 4


def add_audiences(posts: list[dict], now: str, people: dict, companion_name: str) -> None:
    """Fill in each post's likes and comments, oldest first, so a line said on one post is not said
    again on the next few. Posts carry their basis as `_basis` (author, content); it is removed here."""
    recent: list[set[str]] = []
    for post in sorted(posts, key=lambda post: (post['occurs_at'], post['id'])):
        basis = post.pop('_basis', None)
        if basis is None:
            post['audience'] = {'likes': [], 'comments': []}
            continue
        post['audience'] = audience(post['id'], post['kind'], basis[0], basis[1], post['occurs_at'], now, people,
                                    companion_name, frozenset().union(*recent[-NEARBY:]))
        recent.append({comment['text'] for comment in post['audience']['comments']})


def view(row: dict, people: dict, companion_name: str) -> dict | None:
    """A social post shaped like a feed post: no events and no image, with its own text. Its likes and
    comments are added by `add_audiences` from `_basis`."""
    author = author_view(row['author'], people, companion_name)
    removed = row['status'] == 'removed'
    if author is None and not removed:
        return None  # Its author left the circle.
    content = {} if removed else decode(row['content'])
    return {'id': row['id'], 'kind': row['kind'], 'source': 'social', 'author': author,
            'intro': '', 'events': [], 'text': content.get('text', ''), 'context': content.get('context', ''),
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
