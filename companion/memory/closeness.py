"""Closeness stages: visible familiarity that grows with shared history (PRD M3, M4).

The stage is worked out from the active timeline's history every time it is needed, never stored as
a score. It counts the days the user talked (a quick hello and a long talk count the same, so more
messages never earn more) and the shared moments remembered, which can never outrun those days.
Time apart never lowers it. The user sees the stage and why it changed, can hold it at any stage,
give a nickname, pick running jokes from shared moments and restart the count.

The stage changes how open the companion is: what they share, nicknames and in-jokes. It follows
the relationship style the user chose, never makes emotional traits stronger, and is never used to
pressure the user or to reward time spent.
"""
from companion.characters import require_current
from companion.clock import parse, stamp, zone
from companion.database import decode, many, optional, settings
from companion.errors import require
from companion.memory.records import eligible

SHARED_LAYERS = ('shared_experience', 'relationship')
# Points to reach each stage: one per day talked, plus one per shared moment up to the days talked.
THRESHOLDS = (0, 3, 8, 16, 30)
JOKE_DAYS = 3
JOKE_LIMIT = 5
NICKNAME_LIMIT = 40

NAMES = ('Just met', 'Getting to know each other', 'Comfortable', 'Close', 'Deeply close')
FRIEND_NAMES = ('Just met', 'Getting to know each other', 'Friends', 'Close friends', 'Like old friends')

OPENNESS = (
    'You have only just started talking. Be friendly but a little reserved: share everyday things about your '
    'day and interests, not private worries or old wounds, and do not act as if you share a history.',
    'You are getting to know each other. Share opinions, small frustrations and the kind of stories from your '
    'past you would tell someone new.',
    'You are comfortable with each other. Share personal stories, hopes and worries, tease lightly and refer '
    'back to things you have talked about.',
    'You are close. Be open about what matters to you, including fears and vulnerable moments, and bring up '
    'shared moments and running jokes when they fit.',
    'You are deeply close. Talk with the ease of long familiarity: shorthand, in-jokes and honesty, including '
    'about hard things.',
)
RULES = ('The user sees this stage and sets it. Never mention it, never ask for more time or attention, and '
         'never suggest the user owes you anything for being close.')
STEADY_TRAITS = 'Being close never makes your emotional traits stronger.'
NOT_ROMANTIC = 'Closeness here stays {relationship}: it never turns romantic.'
COINED = 'If it suits your voice, a nickname for the user may come up naturally; drop it if they seem not to like it.'
NO_NICKNAME = 'Do not give the user a nickname or pet name yet.'
CHOSEN = 'The user is happy for you to call them “{nickname}”; use it now and then, naturally.'
JOKES = 'Running jokes you share (bring one up only when it fits, never every reply):'


def stage_names(relationship: str) -> tuple[str, ...]:
    return FRIEND_NAMES if relationship == 'friendship' else NAMES


def points(days: int, moments: int) -> int:
    return days + min(moments, days)


def level_for(score: int) -> int:
    return sum(1 for threshold in THRESHOLDS if score >= threshold)


def local_day(instant: str, timezone) -> str:
    return parse(instant).astimezone(timezone).date().isoformat()


def options(connection, timeline_id) -> dict:
    row = optional(connection, 'SELECT * FROM closeness_settings WHERE timeline_id=?', (timeline_id,))
    return row or {'timeline_id': timeline_id, 'counted_from': None, 'held_level': None, 'nickname': ''}


def talk_days(connection, timeline_id, since, timezone) -> list[str]:
    """Distinct local dates the user wrote on, in order. Deleted and inactive messages do not count."""
    rows = many(connection, "SELECT created_at FROM messages WHERE timeline_id=? AND role='user' AND active=1 "
                "AND status='complete' AND redacted_at IS NULL AND created_at>=?", (timeline_id, since or ''))
    return sorted({local_day(row['created_at'], timezone) for row in rows})


def shared_moments(connection, companion, timeline_id, now, since) -> list[dict]:
    """Eligible shared moments, so excluded, corrected-away or deleted memories never count."""
    return sorted((memory for memory in eligible(connection, companion, timeline_id, stamp(now))
                   if memory['layer'] in SHARED_LAYERS and memory['created_at'] >= (since or '')),
                  key=lambda memory: memory['created_at'])


def milestones(days: list[str], moment_days: list[str]) -> list[dict]:
    """The date each stage above the first was reached, walking the shared history in order."""
    reached, day_count, moment_count = [], 0, 0
    for day in sorted(set(days) | set(moment_days)):
        day_count += day in days
        moment_count += moment_days.count(day)
        level = level_for(points(day_count, moment_count))
        while len(reached) + 1 < level:
            reached.append({'level': len(reached) + 2, 'on': day, 'days': day_count,
                            'moments': min(moment_count, day_count)})
    return reached


def joke_candidates(connection, timeline_id, moments, chosen, since, timezone) -> list[dict]:
    """Shared moments that came up in replies on several separate days. Only the user makes them running jokes."""
    days = {}
    for row in many(connection, "SELECT receipt, created_at FROM messages WHERE timeline_id=? AND role='companion' "
                    'AND receipt IS NOT NULL AND active=1 AND created_at>=?', (timeline_id, since or '')):
        for identity in set((decode(row['receipt']).get('included') or {}).get('recalled', [])):
            days.setdefault(identity, set()).add(local_day(row['created_at'], timezone))
    return [{'memory_id': memory['id'], 'subject': memory['subject'], 'value': memory['value'],
             'days': len(days[memory['id']])} for memory in moments
            if memory['id'] not in chosen and len(days.get(memory['id'], ())) >= JOKE_DAYS]


def jokes(connection, timeline_id, moments) -> list[dict]:
    chosen = {row['memory_id'] for row in many(connection, 'SELECT memory_id FROM closeness_jokes WHERE timeline_id=?',
                                               (timeline_id,))}
    return [{'memory_id': memory['id'], 'subject': memory['subject'], 'value': memory['value']}
            for memory in moments if memory['id'] in chosen]


def state(connection, companion, now) -> dict:
    """Everything the panel and the chat context need, computed from the timeline's history."""
    timeline_id, definition = companion['active_timeline_id'], companion['version']['definition']
    chosen = options(connection, timeline_id)
    timezone = zone(settings(connection)['user_timezone'])
    since = chosen['counted_from']
    days = talk_days(connection, timeline_id, since, timezone)
    moments = shared_moments(connection, companion, timeline_id, now, since)
    grown = level_for(points(len(days), len(moments)))
    level = chosen['held_level'] or grown
    names = stage_names(definition['relationship'])
    running = jokes(connection, timeline_id, moments)
    return {'level': level, 'name': names[level - 1], 'grown_level': grown, 'held_level': chosen['held_level'],
            'relationship': definition['relationship'], 'stages': list(names),
            'days_talked': len(days), 'shared_moments': len(moments),
            'counted_moments': min(len(moments), len(days)), 'first_day': days[0] if days else None,
            'counted_from': since, 'nickname': chosen['nickname'],
            'history': milestones(days, [local_day(memory['created_at'], timezone) for memory in moments]),
            'jokes': running,
            'joke_candidates': joke_candidates(connection, timeline_id, moments,
                                               {joke['memory_id'] for joke in running}, since, timezone)}


def nickname_line(current) -> str:
    if current['nickname']:
        return CHOSEN.format(nickname=current['nickname'])
    return COINED if current['level'] >= 3 else NO_NICKNAME


def context_text(current, definition) -> str:
    """The chat-context guidance for the current stage, within the relationship and traits the user chose."""
    lines = [f"{current['name']}. {OPENNESS[current['level'] - 1]}", nickname_line(current), RULES]
    if definition['relationship'] != 'romance':
        lines.append(NOT_ROMANTIC.format(relationship=definition['relationship']))
    if definition.get('emotional_traits'):
        lines.append(STEADY_TRAITS)
    return '\n'.join(lines)


def joke_text(joke) -> str:
    return f"- {joke['subject']}: {joke['value']}"


def offer(packet, connection, companion, now):
    """Adds the 'closeness' section: the stage's guidance, then each running joke the user picked."""
    current = state(connection, companion, now)
    packet.offer('closeness', f"stage:{current['level']}", context_text(current, companion['version']['definition']))
    for index, joke in enumerate(current['jokes'][:JOKE_LIMIT]):
        packet.offer('closeness', joke['memory_id'], (JOKES + '\n' if index == 0 else '') + joke_text(joke))


# Changes the user makes ---------------------------------------------------------------------------

def save(connection, timeline_id, timestamp, **values):
    current = options(connection, timeline_id) | values
    connection.execute(
        'INSERT INTO closeness_settings (timeline_id, counted_from, held_level, nickname, updated_at) '
        'VALUES (?, ?, ?, ?, ?) ON CONFLICT(timeline_id) DO UPDATE SET counted_from=excluded.counted_from, '
        'held_level=excluded.held_level, nickname=excluded.nickname, updated_at=excluded.updated_at',
        (timeline_id, current['counted_from'], current['held_level'], current['nickname'], timestamp))


def view(database) -> dict:
    with database.connect() as connection:
        return state(connection, require_current(connection), database.clock.now())


def update(database, body) -> dict:
    """Hold the stage (or let it grow again with null) and set the nickname, as given."""
    values = {key: getattr(body, key) for key in body.model_fields_set}
    if 'nickname' in values:
        values['nickname'] = (values['nickname'] or '').strip()[:NICKNAME_LIMIT]
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        save(connection, companion['active_timeline_id'], database.now(), **values)
        return state(connection, companion, database.clock.now())


def reset(database) -> dict:
    """Start counting again from now: the stage returns to the first, a hold and running jokes are cleared.
    The nickname is the user's own choice and stays."""
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        timeline_id = companion['active_timeline_id']
        save(connection, timeline_id, database.now(), counted_from=database.now(), held_level=None)
        connection.execute('DELETE FROM closeness_jokes WHERE timeline_id=?', (timeline_id,))
        return state(connection, companion, database.clock.now())


def add_joke(database, memory_id) -> dict:
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        timeline_id, now = companion['active_timeline_id'], database.clock.now()
        moments = shared_moments(connection, companion, timeline_id, now, options(connection, timeline_id)['counted_from'])
        require(any(memory['id'] == memory_id for memory in moments),
                'Only a shared moment that is used in conversation can become a running joke.', 422)
        connection.execute('INSERT OR IGNORE INTO closeness_jokes (timeline_id, memory_id, created_at) VALUES (?, ?, ?)',
                           (timeline_id, memory_id, database.now()))
        return state(connection, companion, now)


def remove_joke(database, memory_id) -> dict:
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        connection.execute('DELETE FROM closeness_jokes WHERE timeline_id=? AND memory_id=?',
                           (companion['active_timeline_id'], memory_id))
        return state(connection, companion, database.clock.now())
