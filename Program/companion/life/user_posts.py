"""The user's own posts on the feed, seen by every companion in the world and by their circles.

A post belongs to the world rather than to one companion's timeline, so it shows on the feed whichever companion
is open, with the same likes and comments. Nobody is asked anything (Vanta, 2026-10-08: the world exists outside
of the user); who joins in, and when, follows from the post, the people and the clock, never stored:

- each companion, main or stepped back, the likelier the closer the user is to them (memory/closeness.py), and
  by their manner (life/social.py `manner`): someone reserved seldom comments, and in few, dry words;
- each companion's circle, friends of friends: they know the user through that companion, so the closer the
  user and the companion, the more their circle notices. Their likes and comments come more slowly.

That is how the user gets to know friends of friends: by posting, and by being close to the people who know them.
"""
import logging
import re
from datetime import datetime, timedelta

from companion.clock import parse, stamp
from companion.database import identifier, many, one, optional
from companion.errors import require
from companion.life import social
from companion.world.generators import pick, unit

USER = 'user'
TEXT_LIMIT = 1000
# By the user's closeness stage with the companion, "Just met" first.
LIKES = (0.4, 0.55, 0.7, 0.8, 0.9)
COMMENTS = (0.12, 0.2, 0.3, 0.4, 0.5)
# How much of a companion's circle notices the user's posts, by the user's stage with that companion.
REACH = (0.1, 0.2, 0.35, 0.5, 0.65)
COMPANION_WINDOW, CIRCLE_WINDOW = timedelta(hours=4), timedelta(hours=24)
MAX_COMMENTS = 4
SICK = re.compile(r'\b(?:sick|ill|flu|fever|migraine|throwing up|hospital)\b', re.IGNORECASE)
DOWN = re.compile(r'\b(?:sad|tired|exhausted|rough|awful|terrible|stressed|lonely|miss(?:ing)?|worst|crying|'
                  r'hard day|bad day|ugh)\b', re.IGNORECASE)
LINES = {
    'close': ('Love this.', 'Look at you!', 'Tell me everything later.', 'This made my day.',
              'Okay, I need the full story.', 'Stop, this is great.', 'Ha! Of course.', 'Proud of you.',
              'This is so you.', 'Save me a spot next time.'),
    # Friends of friends, who know the user through {friend}.
    'friendly': ('Love this!', 'Ha, same.', 'Nice!', 'Good to see you on here.', 'This is great.',
                 "Any friend of {friend}'s is a friend of mine.", 'Okay, this is cute.', 'Yes!!', '😂',
                 '{friend} has told me about you.'),
    'question': ('Good question.', 'Following. I want to know too.', 'Ooh. Tell us what you pick.', 'Hmm, hard one.',
                 'Asking the real questions.'),
    'sick': social.COMMENTS['sick'],
    'down': social.COMMENTS['down'],
}
LOG = logging.getLogger(__name__)


# Writing ----------------------------------------------------------------------------------------

def create(database, text: str) -> dict:
    text = text.strip()
    require(0 < len(text) <= TEXT_LIMIT, f'A post is 1 to {TEXT_LIMIT} characters.', 422)
    from companion.life import feed
    with database.connect(write=True) as connection:
        timestamp, post_id = database.now(), identifier()
        connection.execute('INSERT INTO user_posts (id, text, occurs_at, created_at) VALUES (?, ?, ?, ?)',
                           (post_id, text, timestamp, timestamp))
        return feed.shown(connection, post_id, timestamp)


def find(connection, post_id) -> dict | None:
    return optional(connection, 'SELECT * FROM user_posts WHERE id=?', (post_id,))


def set_status(connection, row, status, timestamp):
    require(row['status'] != 'removed', 'This post was removed.', 409)
    if status == 'removed':
        connection.execute("UPDATE user_posts SET status='removed', text='', removed_at=? WHERE id=?",
                           (timestamp, row['id']))
    else:
        connection.execute('UPDATE user_posts SET status=? WHERE id=?', (status, row['id']))


# Reading ----------------------------------------------------------------------------------------

def view(row: dict) -> dict:
    """A post of the user's shaped like a feed post. Always read: the user wrote it."""
    removed = row['status'] == 'removed'
    return {'id': row['id'], 'kind': USER, 'source': USER,
            'author': {'kind': USER, 'id': None, 'name': 'You', 'role': ''},
            'intro': '', 'events': [], 'text': row['text'], 'context': '', 'place': '', 'options': [],
            'answer': None, 'status': row['status'], 'read': True, 'read_at': row['created_at'], 'reaction': None,
            'occurs_at': row['occurs_at'], 'created_at': row['created_at'], 'image': None,
            '_basis': None if removed else (USER, {'text': row['text']})}


def visible(connection, now: str, include_hidden=False) -> list[dict]:
    """Up to now only: after Debug time goes back, a post from later is not there yet."""
    statuses = "('visible','hidden')" if include_hidden else "('visible')"
    return [view(row) for row in many(connection, f'SELECT * FROM user_posts WHERE status IN {statuses} '
                                      'AND occurs_at<=? ORDER BY occurs_at DESC, id DESC', (now,))]


def any_posts(connection) -> bool:
    return one(connection, "SELECT COUNT(*) AS count FROM user_posts WHERE status!='removed'")['count'] > 0


# Who joins in ----------------------------------------------------------------------------------

def crowd(connection, now: datetime) -> list[dict]:
    """Everyone who can see the user's posts, with their chances to like and comment: every companion, and every
    companion's circle. Someone in two circles (a shared person) joins in once."""
    from companion.characters import by_id
    result, seen = [], set()
    for row in many(connection, 'SELECT id FROM companions WHERE active_version_id IS NOT NULL ORDER BY created_at'):
        companion = by_id(connection, row['id'])
        if companion is None:
            continue
        level = stage(connection, companion, now)
        name, since = companion['version']['name'], companion['created_at']
        style = social.manner(companion['version']['definition'])
        likes, comments = social.MANNERS[style]
        result.append({'key': f"companion:{companion['id']}", 'name': name, 'kind': 'companion', 'role': '',
                       'style': style, 'friend': '', 'since': since, 'window': COMPANION_WINDOW,
                       'like': min(LIKES[level - 1] * likes, social.KNOWN_MOST[0]),
                       'comment': min(COMMENTS[level - 1] * comments, social.KNOWN_MOST[1])})
        seen.add(name)
        result += circle_crowd(connection, companion, level, seen)
    return result


def circle_crowd(connection, companion: dict, level: int, seen: set[str]) -> list[dict]:
    first = companion['version']['name'].strip().split()[0] if companion['version']['name'].strip() else ''
    found = []
    for person in social.active_people(connection, companion['active_timeline_id']).values():
        if person['name'] in seen:
            continue
        seen.add(person['name'])
        reach = REACH[level - 1]
        found.append({'key': person['id'], 'name': person['name'], 'kind': 'person', 'style': '',
                      'role': f"{first}'s {person['role']}" if first and person['role'] else '', 'friend': first,
                      'since': companion['created_at'], 'window': CIRCLE_WINDOW,
                      'like': social.LIKELY.get(person['role'], 0.45) * reach,
                      'comment': social.COMMENT_CHANCE * reach})
    return found


def stage(connection, companion: dict, now: datetime) -> int:
    """The user's closeness stage with a companion, 1 when it cannot be worked out."""
    from companion.memory import closeness
    try:
        return closeness.state(connection, companion, now)['level']
    except Exception:  # noqa: BLE001 - one companion's closeness never keeps the feed from opening.
        LOG.exception('Could not work out closeness with %s for the feed', companion['id'])
        return 1


def pool(text: str, who: dict) -> tuple[str, ...]:
    tone = 'sick' if SICK.search(text) else 'down' if DOWN.search(text) else ''
    if who['style'] == 'reserved':
        return social.RESERVED_COMMENTS['down' if tone else 'general']
    if tone:
        return LINES[tone]
    if text.rstrip().endswith('?'):
        return LINES['question']
    return LINES['close' if who['kind'] == 'companion' else 'friendly']


def audience(post_id: str, content: dict, occurs_at: str, now: str, people: list[dict],
             avoid: frozenset[str] = frozenset()) -> dict:
    """Who liked and commented on one of the user's posts by `now`. Only people who were around when it went up
    join in; no line is said twice on a post, and lines in `avoid` (said on the posts just before) wait."""
    occurred, text = parse(occurs_at), content.get('text', '')
    likes, speakers = [], []
    for who in people:
        if who['since'] > occurs_at:
            continue
        seed = f"{post_id}:{who['key']}"
        if unit(seed, 'like') < who['like'] and stamp(occurred + who['window'] * unit(seed, 'like-at')) <= now:
            likes.append(who['name'])
        said = stamp(occurred + who['window'] * unit(seed, 'comment-at'))
        if unit(seed, 'comment') < who['comment'] and said <= now:
            speakers.append((said, who['key'], who, seed))
    comments, used = [], set(avoid)
    for said, _key, who, seed in sorted(speakers, key=lambda item: item[:2])[:MAX_COMMENTS]:
        fresh = [line for line in (line.format(friend=who['friend']) for line in pool(text, who)) if line not in used]
        if not fresh:
            continue
        line = pick(seed, 'comment', fresh)
        used.add(line)
        comments.append({'author': who['kind'], 'name': who['name'], 'role': who['role'], 'at': said, 'text': line})
    return {'likes': likes, 'comments': comments}
