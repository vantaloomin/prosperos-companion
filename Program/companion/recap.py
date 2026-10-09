"""While you were away: a short catch-up when the user comes back to a companion after a few days.

Shown once in the chat when the user's last message to this companion is at least `life_settings.recap_after_days`
old (3 by default, 0 turns it off), folded away once they have read it, and gone as soon as they write again.
It only summarizes what the world already decided while they were gone, so it never calls a model: chapters of
the companion's life, storylines that moved on, the biggest things they did, how many townsfolk they ran into and
the town paper issues that came out. Nothing from the secrets ledger, and nothing the companion would not share:
the same life the Today view shows. Templates pick the few biggest items; it is a summary, not a replay.
"""
from datetime import date, datetime, timedelta

from companion.characters import require_current
from companion.clock import parse, stamp, zone
from companion.database import many, one, optional
from companion.life import network, storylines
from companion.world import paper

MOST = 6
MOST_EVENTS = 3


def last_from_user(connection, timeline_id: str) -> str | None:
    row = optional(connection, "SELECT MAX(created_at) AS at FROM messages WHERE timeline_id=? AND role='user' "
                   'AND active=1', (timeline_id,))
    return row and row['at']


def chapters(connection, timeline_id: str, since: str) -> list[str]:
    rows = many(connection, 'SELECT title FROM life_chapters WHERE timeline_id=? AND created_at>? AND undone_at IS NULL '
                'ORDER BY started_on', (timeline_id, since))
    return [f"{row['title']}." for row in rows]


def stories(connection, companion: dict, now: datetime, since_day: str) -> list[str]:
    """The latest beat of each storyline that moved on while the user was away."""
    lines = []
    for item in storylines.visible(connection, companion, now, include_ended=True):
        moved = [beat for beat in item['beats'] if beat['on'] > since_day]
        if moved:
            lines.append(sentence(moved[-1]['text']))
    return lines


def events(connection, timeline_id: str, since: str, now: str) -> list[str]:
    """The biggest things they did: plans and threads before ordinary days, newest first."""
    rows = many(connection, "SELECT summary FROM life_events WHERE timeline_id=? AND status='committed' "
                "AND kind!='routine' AND starts_at>? AND starts_at<=? ORDER BY kind='ordinary', starts_at DESC LIMIT ?",
                (timeline_id, since, now, MOST_EVENTS))
    return [sentence(row['summary']) for row in rows]


def townsfolk(connection, timeline_id: str, since: str, name: str) -> list[str]:
    met = one(connection, 'SELECT COUNT(DISTINCT key) AS n FROM townsfolk_encounters WHERE timeline_id=? AND met_at>?',
              (timeline_id, since))['n']
    if not met:
        return []
    return [f"{name} ran into {'someone' if met == 1 else f'{met} people'} around town."]


def issues(connection, companion: dict, since_day: date, today: date) -> list[str]:
    """Town paper issues out since: it comes out every Sunday (companion/world/paper.py)."""
    data = network.city(connection, companion)
    if not data.get('neighborhoods'):
        return []
    count, sunday = 0, paper.issue_date(today)
    while sunday > since_day:
        count, sunday = count + 1, sunday - timedelta(days=7)
    if not count:
        return []
    return [f"{'A new issue' if count == 1 else f'{count} issues'} of {paper.title(data)} came out."]


def sentence(text: str) -> str:
    text = text.strip()
    return text if not text or text[-1] in '.!?' else f'{text}.'


def gap_days(connection) -> int:
    return one(connection, 'SELECT recap_after_days FROM life_settings WHERE id=1')['recap_after_days']


def build(connection, companion: dict, now: datetime) -> dict | None:
    timeline_id, version = companion['active_timeline_id'], companion['version']
    days, since = gap_days(connection), last_from_user(connection, timeline_id)
    if not days or not since or now - parse(since) < timedelta(days=days):
        return None
    if optional(connection, 'SELECT 1 FROM away_recaps WHERE timeline_id=? AND since=?', (timeline_id, since)):
        return None
    local = zone(version['timezone'])
    since_day, today = parse(since).astimezone(local).date(), now.astimezone(local).date()
    name = version['name'].split()[0] if version['name'].strip() else 'They'
    items = [*chapters(connection, timeline_id, since), *stories(connection, companion, now, since_day.isoformat()),
             *events(connection, timeline_id, since, stamp(now)), *townsfolk(connection, timeline_id, since, name),
             *issues(connection, companion, since_day, today)]
    if not items:
        return None
    return {'since': since, 'days': (now - parse(since)).days, 'items': items[:MOST]}


def read(database) -> dict:
    with database.connect() as connection:
        return {'recap': build(connection, require_current(connection), database.clock.now())}


def dismiss(database, since: str) -> dict:
    """Read: it stays folded away until the user is gone for a while again."""
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        connection.execute('INSERT OR REPLACE INTO away_recaps (timeline_id, since, dismissed_at) VALUES (?, ?, ?)',
                           (companion['active_timeline_id'], since, database.now()))
    return {'recap': None}
