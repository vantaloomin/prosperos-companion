"""Who in a companion's circle knows the user (tester, 2026-11-18): Sett told his mom about the user, and she answered
the user's comment on her post, yet the web (companion/life/web.py) showed her knowing only Sett.

Nothing new is stored or asked of a model; the app reads it from what already happened, best reason first:

- they met the user in person (companion/life/their_people.py),
- they answered the user's comment on one of their posts (companion/life/post_comments.py),
- they were in a group chat with the user (companion/group_guests.py),
- the companion has talked about the user to them: someone the companion is close to, once the user is close enough to
  the companion, by the same numbers that decide whether they notice the user's posts (companion/life/user_posts.py).

The first three mean they know the user; the last that they know of the user, who hasn't met them. The user overrides
on the person's card (`details.knows_you`: 'knows you', 'knows of you', or '' for not at all; gone hands it back).
"""
from companion.clock import stamp
from companion.database import encode, many
from companion.errors import require
from companion.life import circle, user_posts

KNOWS, KNOWS_OF = 'knows you', 'knows of you'
WORDS = (KNOWS, KNOWS_OF, '')
# How much of their posts' reach (user_posts.REACH x TIE) someone needs before the companion has told them about the
# user: a close friend or family once the two of them are friends, anyone the companion is fond of once close.
HEARD_FROM = 0.35


def first(name: str) -> str:
    return name.strip().split()[0] if name.strip() else name


def met(connection, timeline_id: str) -> dict[str, str]:
    """{person id: why} for everyone who has met the user in person."""
    from companion.life import their_people
    return {row['person_id']: 'met in person' for row in their_people.met(connection, timeline_id)}


def answered(connection, timeline_id: str) -> dict[str, str]:
    """{person id: why} for everyone who answered the user's comment on their own post."""
    rows = many(connection, "SELECT DISTINCT post.author FROM post_comments reply JOIN social_posts post ON "
                "post.id=reply.post_id JOIN post_comments asked ON asked.id=reply.reply_to AND asked.author='user' "
                "WHERE reply.timeline_id=? AND reply.author='poster' AND reply.status='shown' AND post.kind='friend'",
                (timeline_id,))
    return {row['author']: 'talked on their post' for row in rows}


def chatted(connection) -> set[str]:
    """Person keys of every guest who has been in a group chat with the user."""
    return {row['member'] for row in many(connection, "SELECT DISTINCT member FROM group_members "
                                          "WHERE member NOT LIKE 'companion:%'")}


def heard(connection, companion: dict, rows: list[dict], now) -> dict[str, str]:
    """{person id: why} for the people the companion has told about the user."""
    level = user_posts.stage(connection, companion, now)
    name = first(companion['version']['name'])
    return {row['id']: f'{name} told them about you' for row in rows if circle.knowing(row) == 'both'
            and user_posts.REACH[level - 1] * user_posts.TIE[user_posts.tie(connection, companion, row, now) - 1]
            >= HEARD_FROM}


def app_pick(connection, companion: dict, rows: list[dict], now) -> dict[str, tuple[str, str]]:
    """{person id: (how, why)} as the app works it out."""
    timeline_id = companion['active_timeline_id']
    found = {person: (KNOWS_OF, why) for person, why in heard(connection, companion, rows, now).items()}
    guests = chatted(connection)
    found |= {row['id']: (KNOWS, 'in a group chat together') for row in rows if row['seed'] in guests}
    found |= {person: (KNOWS, why) for person, why in answered(connection, timeline_id).items()}
    return found | {person: (KNOWS, why) for person, why in met(connection, timeline_id).items()}


def for_circle(connection, companion: dict, now) -> dict[str, dict]:
    """{person id: {how, why, set}} for the active circle; `how` '' where they don't know the user."""
    if not companion.get('active_timeline_id'):
        return {}
    rows = circle.people(connection, companion['active_timeline_id'])
    picked = app_pick(connection, companion, rows, now)
    result = {}
    for row in rows:
        told = circle.details_of(row).get('knows_you')
        how, why = picked.get(row['id'], ('', ''))
        if told in WORDS:
            how, why = told, ''
        result[row['id']] = {'how': how, 'why': why, 'set': told in WORDS, 'key': row['seed']}
    return result


def label(found: dict) -> str:
    """The web's words for the tie, from their side."""
    return found['why'] or found['how']


def set_knows_you(connection, person_id: str, how: str | None, now) -> dict:
    """The user's word on whether someone knows them; None hands it back to the app."""
    row = circle.person(connection, person_id)
    require(how is None or how in WORDS, 'Pick one of the ways listed.', 422)
    details = {key: value for key, value in circle.details_of(row).items() if key != 'knows_you'}
    details |= {} if how is None else {'knows_you': how}
    connection.execute('UPDATE circle_people SET details=?, revision=revision+1, updated_at=? WHERE id=?',
                       (encode(details), stamp(now), person_id))
    return row
