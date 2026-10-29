"""Comments on feed posts: the user writes under a post, and whoever posted it answers in the thread.

Beside the likes and comments the circle leaves on their own (companion/life/social.py, worked out and never
stored), the user can comment on any post that isn't their own. The comment is stored, and so is the answer it
gets: on the companion's posts the companion answers, written from their chat (the same character, memories and
day as a reply in chat, told it is a comment under their post); on a friend's post that friend answers, from the
short sheet a group-chat guest is written from (companion/group_guests.py), knowing the user only through the
companion. Every comment gets one answer; the user can keep the thread going.

Nobody answers the moment a comment lands. The answer is written at once but shows later: when the poster would
see it, by Settings > Realism > "How quickly they read your texts" (life/reading.py, a little slower than a text),
or once the companion's work, evening out or sleep is over (life/pacing.py), or a friend has woken up. Nothing
the user does waits on it. Without a chat model, or when the reply can't be used, the comment stays unanswered.

Taking the post to chat instead stays as it was: POST /api/feed/{id}/discuss.
"""
import asyncio
import logging
import random
from datetime import datetime, timedelta

from companion import in_character, prompt_library, texting
from companion.characters import require_current
from companion.clock import parse, stamp, zone
from companion.database import identifier, many, one, optional
from companion.errors import require
from companion.providers.chat import INCOMPLETE
from companion.providers.scheduling import Work
from companion.text_models import CHAT, key_for, reply_config

USER, POSTER = 'user', 'poster'
TEXT_LIMIT = 1000
REPLY_LIMIT = 500
# Asked for by the user but not waited on: after chat replies, ahead of background life and memory work.
COMMENTING = Work(10, 'comment reply')
# Minutes before the poster sees a comment, by read pace (life/reading.py: 1 quick, 2 natural, 3 slow); 0 is at once.
SEES = {1: (1, 6), 2: (4, 35), 3: (20, 120)}
# Busy or asleep, they see it when that is over, never later than this.
LONGEST = timedelta(hours=10)
# Local hours a friend with no plan of their own for the hour is asleep (as companion/group_guests.py).
MORNING = 7
# Earlier comments and answers the reply is told about, newest last.
EARLIER = 6
LOG = logging.getLogger(__name__)
# Answers being written, held so a task is not dropped before it finishes.
RUNNING: set = set()

COMPANION_REPLY = (
    'The user just commented on your post on the feed, your social media. Your post: «{post}» {earlier}'
    'Their comment: «{comment}» Write your answer as a comment under your own post, in your own voice: usually '
    'one short sentence, the way people answer comments, and others can read it too. Stay with what the post '
    'and their comment are about. Reply with the comment only.'
)
FRIEND_REPLY = """Who you are: {who}
{lines}
You posted on social media: «{post}» The user commented on it. You know the user only as someone close to \
{host}, so never claim history with them.
{earlier}Their comment: «{comment}»
Write your answer as a comment under your post, in your own voice: usually one short sentence, the way people \
answer comments. Reply with the comment only."""


# Finding the post and who answers -----------------------------------------------------------------------------

def target(connection, post_id: str) -> dict:
    """{post_id, timeline_id, kind, text, poster}: the post a comment goes under, with who posted it ('companion' or
    a circle person's id). The user's own posts and removed ones take no comments."""
    from companion.life import feed, social, user_posts
    require(user_posts.find(connection, post_id) is None, 'That is your own post.', 409)
    if row := social.find(connection, post_id):
        require(row['status'] != 'removed', 'This post was removed.', 409)
        # As the feed shows it: a friend's own post says "I".
        view = social.view(row, social.active_people(connection, row['timeline_id']), '') or {}
        parts = [view.get('text'), view.get('context') if view.get('context') != view.get('text') else '']
        return {'post_id': post_id, 'timeline_id': row['timeline_id'], 'kind': row['kind'],
                'text': ' '.join(part for part in parts if part), 'poster': row['author']}
    row = optional(connection, 'SELECT * FROM feed_posts WHERE id=?', (post_id,))
    require(row is not None, 'This item could not be found.', 404)
    require(row['status'] != 'removed', 'This post was removed.', 409)
    view = feed.post_view(connection, row)
    require(view is not None, 'This item could not be found.', 404)
    lines = [view['intro']] if view['intro'] else []
    lines += [(event['mine'] or event)['caption'] for event in view['events']]
    if view['image'] and view['image']['status'] == 'completed':
        lines.append('(with a photo)')
    return {'post_id': post_id, 'timeline_id': row['timeline_id'], 'kind': row['kind'], 'text': ' '.join(lines),
            'poster': social.COMPANION}


def friend(connection, companion: dict, person_id: str, now: datetime) -> dict | None:
    """The circle person who posted, as a group-chat guest is written: who they are, how they come across."""
    from companion import group_guests
    found = next((person for person in group_guests.known_by(connection, companion, now)
                  if person.get('person_id') == person_id), None)
    if found is None:
        return None
    lines = group_guests.lines(connection, found, companion)
    return {**found, 'who': group_guests.who(connection, found), 'public': lines['public'],
            'private': lines['private'], 'host_name': companion['version']['name'].split()[0],
            'doing': group_guests.doing(connection, found, companion, now)}


# When the poster sees it ----------------------------------------------------------------------------------------

def shows_at(connection, companion: dict, poster: str, now: datetime, seed: str) -> str:
    """When the answer shows: a little after the poster sees the comment, once they're free and awake."""
    from companion.life import pacing, reading
    setting = reading.pace(connection, companion) if reading.ACTIVE else 0
    if not setting:
        return stamp(now)
    free = now
    if poster == 'companion':
        found = pacing.block_now(connection, companion, now) if pacing.ACTIVE else None
        if found and pacing.busy_kind(found[0]):
            free = max(now, min(parse(found[1]), now + LONGEST))
    elif awake := morning(connection, companion, poster, now):
        free = awake
    minutes = random.Random(f'comment:{seed}').uniform(*SEES[setting])
    return stamp(free + timedelta(minutes=minutes))


def morning(connection, companion: dict, person_id: str, now: datetime) -> datetime | None:
    """When a friend who is asleep now wakes up; None when they're awake."""
    found = friend(connection, companion, person_id, now)
    if not found or found['doing'] != 'asleep':
        return None
    local = now.astimezone(zone(companion['version']['timezone']))
    wake = local.replace(hour=MORNING, minute=0, second=0, microsecond=0)
    if wake <= local:
        wake += timedelta(days=1)
    return min(wake, now + LONGEST)


# Writing ---------------------------------------------------------------------------------------------------------

def add(database, post_id: str, text: str) -> dict:
    """The user's comment, saved with a place held for the answer; returns {comment_id, reply_id}."""
    text = ' '.join(text.split()) if '\n' not in text else text.strip()
    require(0 < len(text) <= TEXT_LIMIT, f'A comment is 1 to {TEXT_LIMIT} characters.', 422)
    now, timestamp = database.clock.now(), database.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        found = target(connection, post_id)
        require(found['timeline_id'] == companion['active_timeline_id'], 'This post is not on this timeline.', 409)
        comment_id, reply_id = identifier(), identifier()
        connection.execute('INSERT INTO post_comments (id, post_id, timeline_id, author, text, status, shows_at, '
                           "created_at) VALUES (?, ?, ?, 'user', ?, 'shown', ?, ?)",
                           (comment_id, post_id, found['timeline_id'], text, timestamp, timestamp))
        connection.execute('INSERT INTO post_comments (id, post_id, timeline_id, author, text, reply_to, status, '
                           "shows_at, created_at) VALUES (?, ?, ?, 'poster', '', ?, 'writing', ?, ?)",
                           (reply_id, post_id, found['timeline_id'], comment_id,
                            shows_at(connection, companion, found['poster'], now, reply_id), timestamp))
        # Commenting reads the post, as replying to it in chat does.
        connection.execute('UPDATE feed_posts SET read_at=COALESCE(read_at, ?) WHERE id=?', (timestamp, post_id))
        connection.execute('UPDATE social_posts SET read_at=COALESCE(read_at, ?) WHERE id=?', (timestamp, post_id))
    return {'comment_id': comment_id, 'reply_id': reply_id}


def earlier_text(rows: list[dict], name: str) -> str:
    """The thread so far, for the reply's prompt."""
    if not rows:
        return ''
    said = [f"{'The user' if row['author'] == USER else name}: «{row['text']}»" for row in rows[-EARLIER:]]
    return 'Earlier in the comments: ' + ' '.join(said) + ' '


def thread_before(connection, post_id: str, comment: dict) -> list[dict]:
    return many(connection, "SELECT author, text FROM post_comments WHERE post_id=? AND status='shown' "
                "AND created_at<=? AND id!=? AND text!='' ORDER BY shows_at, rowid",
                (post_id, comment['created_at'], comment['id']))


def companion_packet(connection, companion: dict, config: dict, now: datetime, found: dict, comment: dict,
                     earlier: list[dict]) -> dict:
    """Their chat (character, memories, the day and the latest messages) with the ask added, as a first text is."""
    from companion.memory import context
    packet = context.build(connection, companion, now, config['context_tokens'] - config['max_output_tokens'])
    ask = '(' + prompt_library.text(connection, 'feed-comment-reply', post=found['text'], comment=comment['text'],
                                    earlier=earlier_text(earlier, 'You')) + ')'
    messages = list(packet['messages'])
    if messages and messages[-1]['role'] == 'user':
        messages[-1] = {'role': 'user', 'content': messages[-1]['content'] + '\n\n' + ask}
    else:
        messages.append({'role': 'user', 'content': ask})
    return {'system': packet['system'], 'messages': messages}


def friend_packet(connection, person: dict, found: dict, comment: dict, earlier: list[dict]) -> dict:
    from companion.world import perception
    system = prompt_library.text(connection, 'feed-comment-friend', who=person['who'], host=person['host_name'],
                                 lines=perception.own_text(person['public'], person['private']), post=found['text'],
                                 comment=comment['text'], earlier=earlier_text(earlier, 'You'))
    return {'system': system, 'messages': [{'role': 'user', 'content': comment['text']}]}


def prepare(database, reply_id: str) -> dict | None:
    """What writing the answer needs, or None when it can't be written (no chat model, the poster gone)."""
    now = database.clock.now()
    with database.connect(write=True) as connection:
        reply = optional(connection, "SELECT * FROM post_comments WHERE id=? AND status='writing'", (reply_id,))
        if reply is None:
            return None
        comment = one(connection, 'SELECT * FROM post_comments WHERE id=?', (reply['reply_to'],))
        companion = require_current(connection)
        config = reply_config(connection, CHAT)
        found = target(connection, reply['post_id'])
        if config is None or found['timeline_id'] != companion['active_timeline_id']:
            return None
        earlier = thread_before(connection, reply['post_id'], comment)
        definition = companion['version']['definition']
        if found['poster'] == 'companion':
            packet = companion_packet(connection, companion, config, now, found, comment, earlier)
            return {'packet': packet, 'config': config, 'definition': definition, 'name': companion['version']['name']}
        person = friend(connection, companion, found['poster'], now)
        if person is None:
            return None
        return {'packet': friend_packet(connection, person, found, comment, earlier), 'config': config,
                'definition': None, 'name': person['name']}


async def write(state, reply_id: str) -> dict | None:
    """Write the answer to a comment. On any trouble the place held for it goes, and the comment stays unanswered."""
    database = state.database
    try:
        ready = prepare(database, reply_id)
        text = await complete(state, ready) if ready else None
    except Exception:  # noqa: BLE001 - a comment never fails because its answer could not be written.
        LOG.exception('Could not write the answer to comment %s', reply_id)
        text = None
    with database.connect(write=True) as connection:
        if not text:
            connection.execute("DELETE FROM post_comments WHERE id=? AND status='writing'", (reply_id,))
            return None
        connection.execute("UPDATE post_comments SET text=?, name=?, status='shown' WHERE id=? AND status='writing'",
                           (text, ready['name'], reply_id))
        return optional(connection, 'SELECT * FROM post_comments WHERE id=?', (reply_id,))


def start(state, reply_id: str) -> None:
    """Write the answer after the request returns."""
    task = asyncio.create_task(write(state, reply_id))
    RUNNING.add(task)
    task.add_done_callback(RUNNING.discard)


async def complete(state, ready: dict) -> str | None:
    config, packet, pieces = ready['config'], ready['packet'], []
    conversation = state.conversation
    async with conversation.scheduler.reserve(config, COMMENTING, config.get('timeout_seconds')):
        async for chunk in conversation.provider.stream(config, key_for(state.vault, config), packet['system'],
                                                        packet['messages']):
            pieces.append(chunk.text)
            if chunk.finish_reason in INCOMPLETE:
                return None
    return usable(''.join(pieces), ready['definition'], ready['name'])


def usable(text: str, definition: dict | None, name: str) -> str | None:
    """The answer as it shows: no quotes or name label around it, in character, in the companion's texting style."""
    text = text.strip()
    for label in (f'{name}:', f"{name.split()[0]}:" if name.split() else ''):
        if label and text.startswith(label):
            text = text[len(label):]
    text = text.strip().strip('"«»').strip()
    if in_character.applies('', definition or {}):
        text = in_character.clean(text)
    if definition:
        text = texting.restyle(text, definition, name)
    return text if text and len(text) <= REPLY_LIMIT else None


# Reading -----------------------------------------------------------------------------------------------------------

def threads(connection, post_ids: list[str], now: str) -> dict[str, dict]:
    """{post_id: {comments, waiting}} for the posts that have any: the user's comments and the answers that show by
    now, oldest first; `waiting` while an answer is still to show."""
    found: dict[str, dict] = {}
    for start in range(0, len(post_ids), 500):
        chunk = post_ids[start:start + 500]
        rows = many(connection, f"SELECT * FROM post_comments WHERE post_id IN ({','.join('?' * len(chunk))}) "
                    'ORDER BY shows_at, rowid', tuple(chunk))
        for row in rows:
            thread = found.setdefault(row['post_id'], {'comments': [], 'waiting': False})
            if row['status'] == 'shown' and row['shows_at'] <= now:
                thread['comments'].append({'id': row['id'], 'author': row['author'], 'name': row['name'],
                                           'text': row['text'], 'reply_to': row['reply_to'],
                                           'at': row['shows_at']})
            else:
                thread['waiting'] = True
    return found


def attach(connection, posts: list[dict], now: str) -> list[dict]:
    """Each post with its `thread` ({comments, waiting}); the user's own posts take none."""
    found = threads(connection, [post['id'] for post in posts], now)
    for post in posts:
        post['thread'] = found.get(post['id'], {'comments': [], 'waiting': False})
    return posts


def forget(connection, post_id: str) -> None:
    """A removed post loses its comments."""
    connection.execute('DELETE FROM post_comments WHERE post_id=?', (post_id,))
