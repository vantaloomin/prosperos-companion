"""Group chats start conversations on their own (Everyone keeps living).

Now and then someone in a group shares something from their own day, and the others answer it the way they
answer the user (companion/groups.py: who answers, the pace, secrets). Rules decide everything: which group, who
speaks and what about (a committed event from their own life in the last day that this group hasn't heard, and
that gives away no secret someone there must not find out); the model only writes the lines.

It follows the holds of one-to-one first messages (companion/life/openers.py): the texts_first setting, pause,
quiet hours, the speaker's sleep and the shared away allowance (companion/away.py), which the opening line draws
from. And per group: never while the user is in the middle of a chat, never within `texts_gap_hours` of the
group's last message, never twice without the user answering, and at most once every `EVERY`.
"""
import random
from datetime import timedelta

from companion import away, notifications, secrets
from companion.characters import by_id
from companion.clock import parse, stamp
from companion.database import many, one, optional, settings
from companion.life import routine
from companion.text_models import CHAT, config_for

EVERY = timedelta(days=2)
NEWS_WITHIN = timedelta(hours=24)
# The user wrote anywhere this recently: they are mid-chat, and a group starting up would interrupt.
BUSY = timedelta(minutes=15)
INSTRUCTION = (
    'Nobody has written in the group for a while. Write {name}\'s message starting a new conversation in the group: '
    'share this from your own day, the way friends drop news into a group text: {news} Keep to these facts: do not '
    'add events, places or people, and never claim to know what anyone else did. One to three sentences, with no '
    'name in front.'
)


def news_key(group_id: str, event_id: str) -> str:
    """The opening line's `client_id`: one event is shared in a group once."""
    return f'news:{group_id}:{event_id}'


def last_user_at(connection) -> str | None:
    row = one(connection, "SELECT MAX(at) AS at FROM (SELECT MAX(created_at) AS at FROM messages WHERE role='user' "
              "UNION ALL SELECT MAX(created_at) FROM group_messages WHERE author='user')")
    return row['at']


def workspace_held(connection, life, now) -> str | None:
    """Why no group should start a conversation right now, or None."""
    workspace = settings(connection)
    if not life['texts_first']:
        return 'off'
    if workspace['paused_at'] is not None:
        return 'paused'
    quiet = notifications.notification_settings(connection)
    if notifications.in_quiet_hours(now.astimezone(notifications.zone(workspace['user_timezone'])),
                                    quiet['quiet_start'], quiet['quiet_end']):
        return 'quiet_hours'
    latest = last_user_at(connection)
    if latest and now - parse(latest) < BUSY:
        return 'busy'
    if config_for(connection, CHAT) is None:
        return 'no_model'
    return None if away.allowed(connection, now) else 'away_cap'


def group_held(connection, group_id: str, life, now) -> str | None:
    """Why this group should not start a conversation now, or None. An opening line is a member's message that
    answers nobody (`reply_to` NULL)."""
    last = optional(connection, "SELECT author, created_at FROM group_messages WHERE group_id=? AND status='complete' "
                    'ORDER BY seq DESC LIMIT 1', (group_id,))
    if last is None or now - parse(last['created_at']) < timedelta(hours=life['texts_gap_hours']):
        return 'recent'
    opened = optional(connection, "SELECT seq, created_at FROM group_messages WHERE group_id=? AND status='complete' "
                      "AND reply_to IS NULL AND author LIKE 'companion:%' ORDER BY seq DESC LIMIT 1", (group_id,))
    if opened is None:
        return None
    if now - parse(opened['created_at']) < EVERY:
        return 'too_soon'
    answered = optional(connection, "SELECT id FROM group_messages WHERE group_id=? AND author='user' AND seq>?",
                        (group_id, opened['seq']))
    return None if answered else 'waiting_for_answer'


def awake(companion: dict, now) -> bool:
    version = companion['version']
    schedule, _default = routine.blocks(version['definition'])
    slot, _next = routine.current_and_next(schedule, version['timezone'], now)
    return not (slot and slot.block.kind in routine.RESTING)


def gives_away(connection, member: str, present: list[str], text: str) -> bool:
    return any(secrets.hits(secret, text, member) for secret in secrets.watched(connection, member, present))


def member_news(connection, group_id: str, stay: dict, present: list[str], now, skip=frozenset()) -> list[dict]:
    """Things from this member's own day the group could hear about now, leaving out the news keys in `skip`."""
    companion = by_id(connection, (stay['member'].split(':', 1) + [''])[1])
    if companion is None or not awake(companion, now):
        return []
    rows = many(connection, "SELECT * FROM life_events WHERE timeline_id=? AND kind='ordinary' AND status='committed' "
                'AND ends_at<=? AND ends_at>? ORDER BY ends_at DESC',
                (companion['active_timeline_id'], stamp(now), stamp(now - NEWS_WITHIN)))
    return [{'stay': stay, 'event': row} for row in rows
            if news_key(group_id, row['id']) not in skip
            and not optional(connection, 'SELECT id FROM group_messages WHERE client_id=?', (news_key(group_id, row['id']),))
            and not gives_away(connection, stay['member'], present, row['summary'])]


def pick(connection, group_id: str, members: list[dict], now, skip=frozenset()) -> dict | None:
    """Who shares what: one of the members with fresh news, seeded by the group and the day."""
    present = [stay['member'] for stay in members]
    found = [item for stay in members for item in member_news(connection, group_id, stay, present, now, skip)]
    if not found:
        return None
    return random.Random(f'group-news:{group_id}:{now.date().isoformat()}').choice(found)


def due(connection, now, skip=frozenset()) -> list[tuple[str, dict]]:
    """Groups that may start a conversation now, with who shares what, quietest first. News keys in `skip`
    were tried already."""
    life = one(connection, 'SELECT * FROM life_settings WHERE id=1')
    if workspace_held(connection, life, now):
        return []
    result = []
    for group in many(connection, 'SELECT id FROM group_chats ORDER BY updated_at'):
        if group_held(connection, group['id'], life, now):
            continue
        members = many(connection, 'SELECT * FROM group_members WHERE group_id=? AND left_at IS NULL '
                       'ORDER BY joined_at, rowid', (group['id'],))
        if len(members) >= 2 and (chosen := pick(connection, group['id'], members, now, skip)):
            result.append((group['id'], chosen))
    return result

