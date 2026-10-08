"""Closeness stages: visible familiarity that grows with shared history (PRD M3, M4).

The stage is worked out from the active timeline's history every time it is needed, never stored as
a score. It counts the days the user talked (a quick hello and a long talk count the same, so more
messages never earn more) and the shared moments remembered, which can never outrun those days.
Time apart never lowers it unless the user turns on gentle cooling for this companion. The user sees the stage
and why it changed, can set it to any stage (or a step closer or further) and let it keep growing from there,
hold it, cap it, give a nickname, pick running jokes from shared moments and restart the count. A new
companion can start at any stage (the character's `starting_closeness`).

The stage changes how open the companion is: what they share, nicknames and in-jokes. It follows
the relationship style the user chose, never makes emotional traits stronger, and is never used to
pressure the user or to reward time spent.
"""
from datetime import date

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
# Gentle cooling (opt-in per companion): a silence this many days long cools it by one step, the longer one
# by two. Never more than two steps, never below the second stage, and every WARM_DAYS days talked after a
# silence bring one step back.
COOL_AFTER = (21, 60)
COOL_FLOOR = 2
WARM_DAYS = 2

NAMES = ('Just met', 'Getting to know each other', 'Comfortable', 'Close', 'Deeply close')
FRIEND_NAMES = ('Just met', 'Getting to know each other', 'Friends', 'Close friends', 'Like old friends')

OPENNESS = (
    'You have only just started talking. Be friendly but a little reserved: share everyday things about your '
    'day and interests, not private worries or old wounds, and do not act as if you share a history.',
    'You are getting to know each other. Share opinions, small frustrations and the kind of stories from your '
    'past you would tell someone new.',
    'You are at ease together. Share personal stories, hopes and worries, tease lightly and refer '
    'back to things you have talked about.',
    'You know each other well. Be open about what matters to you, including fears and vulnerable moments, and bring up '
    'shared moments and running jokes when they fit.',
    'You have shared a lot over a long time. Talk with the ease of long familiarity: shorthand, in-jokes and honesty, including '
    'about hard things.',
)
RULES = ('The user sees this stage and sets it. Never mention it, never ask for more time or attention, and '
         'never suggest the user owes you anything for being close.')
STEADY_TRAITS = 'Being close never makes your emotional traits stronger.'
NOT_ROMANTIC = 'Closeness here stays {relationship}: it never turns romantic.'
COINED = 'If it suits your voice, a nickname for the user may come up naturally; drop it if they seem not to like it.'
COOLED = ('You two have not talked in a while, so things feel a little less familiar than they did. Warm back up '
          'naturally. Never blame the user for the gap or ask where they were unless they bring it up.')
NO_NICKNAME = 'Do not give the user a nickname or pet name yet.'
CHOSEN = 'The user is happy for you to call them “{nickname}”; use it now and then, naturally.'
JOKES = 'Running jokes you share (bring one up only when it fits, never every reply):'


def stage_names(relationship: str) -> tuple[str, ...]:
    return FRIEND_NAMES if relationship == 'friendship' else NAMES


def points(days: int, moments: int) -> int:
    return days + min(moments, days)


def level_for(score: int) -> int:
    return max(1, sum(1 for threshold in THRESHOLDS if score >= threshold))


def start_offset(definition: dict) -> int:
    """The head start a new companion has: the points that put them at the stage chosen when they were made."""
    return THRESHOLDS[min(max(int(definition.get('starting_closeness') or 1), 1), len(THRESHOLDS)) - 1]


def local_day(instant: str, timezone) -> str:
    return parse(instant).astimezone(timezone).date().isoformat()


def options(connection, timeline_id) -> dict:
    row = optional(connection, 'SELECT * FROM closeness_settings WHERE timeline_id=?', (timeline_id,))
    return row or {'timeline_id': timeline_id, 'counted_from': None, 'held_level': None, 'nickname': '',
                   'head_start': None, 'set_on': None, 'ceiling_level': None, 'cooling_since': None}


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


def offset_on(day: str, start: int, chosen: int | None, set_day: str | None) -> int:
    """The head start counted on a day: the user's own choice from the day they made it, the starting one before."""
    return chosen if chosen is not None and (set_day is None or day >= set_day) else start


def milestones(days: list[str], moment_days: list[str], start: int = 0, chosen: int | None = None,
               set_day: str | None = None) -> list[dict]:
    """How the stage got where it is, walking the shared history in order: where it started, each stage reached
    and the day the user set it themselves."""
    level = level_for(offset_on('', start, chosen, set_day))
    reached = [{'kind': 'start', 'level': level, 'on': None}] if level > 1 else []
    day_count, moment_count = 0, 0
    for day in sorted(set(days) | set(moment_days) | ({set_day} if set_day else set())):
        day_count += day in days
        moment_count += moment_days.count(day)
        grown = level_for(points(day_count, moment_count) + offset_on(day, start, chosen, set_day))
        if day == set_day:
            reached.append({'kind': 'set', 'level': grown, 'on': day})
        else:
            reached += [{'level': step, 'on': day, 'days': day_count, 'moments': min(moment_count, day_count)}
                        for step in range(level + 1, grown + 1)]
        level = grown
    return reached


def cool_steps(gap: int) -> int:
    return sum(1 for days in COOL_AFTER if gap >= days)


def cooling(days: list[str], since: str, today: str) -> dict:
    """Steps lost to long silences since cooling was turned on (or the stage was last set), and talk days still
    needed to win the next one back. Worked out from the days talked, so nothing is stored or decays in the
    background."""
    cooled, warm, previous = 0, 0, date.fromisoformat(since)
    for day in (date.fromisoformat(item) for item in days if item >= since):
        lost = cool_steps((day - previous).days)
        if lost:
            cooled, warm = min(len(COOL_AFTER), cooled + lost), 0
        if cooled:
            warm += 1
            if warm >= WARM_DAYS:
                cooled, warm = cooled - 1, 0
        previous = day
    silent = (date.fromisoformat(today) - previous).days
    if cool_steps(silent):
        cooled, warm = min(len(COOL_AFTER), cooled + cool_steps(silent)), 0
    return {'steps': cooled, 'warm_days_left': WARM_DAYS - warm if cooled else 0, 'silent_days': silent}


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
    since, today = chosen['counted_from'], local_day(stamp(now), timezone)
    days = talk_days(connection, timeline_id, since, timezone)
    moments = shared_moments(connection, companion, timeline_id, now, since)
    start, set_day = start_offset(definition), chosen['set_on'] and local_day(chosen['set_on'], timezone)
    offset = offset_on(today, start, chosen['head_start'], set_day)
    earned = level_for(points(len(days), len(moments)) + offset)
    ceiling = chosen['ceiling_level']
    capped = min(earned, ceiling) if ceiling else earned
    cooled = cooled_state(chosen, days, set_day, today, timezone)
    grown = max(capped - cooled['steps'], min(capped, COOL_FLOOR))
    level = chosen['held_level'] or grown
    names = stage_names(definition['relationship'])
    running = jokes(connection, timeline_id, moments)
    return {'level': level, 'name': names[level - 1], 'grown_level': grown, 'held_level': chosen['held_level'],
            'earned_level': earned, 'ceiling_level': ceiling, 'starting_level': level_for(start),
            'cooling': chosen['cooling_since'] is not None, 'cooled_steps': capped - grown,
            'warm_days_left': cooled['warm_days_left'] if grown < capped else 0,
            'silent_days': cooled['silent_days'],
            'relationship': definition['relationship'], 'stages': list(names),
            'days_talked': len(days), 'shared_moments': len(moments),
            'counted_moments': min(len(moments), len(days)), 'first_day': days[0] if days else None,
            'counted_from': since, 'set_on': set_day, 'nickname': chosen['nickname'],
            'history': milestones(days, [local_day(memory['created_at'], timezone) for memory in moments],
                                  start, chosen['head_start'], set_day),
            'jokes': running,
            'joke_candidates': joke_candidates(connection, timeline_id, moments,
                                               {joke['memory_id'] for joke in running}, since, timezone)}


def cooled_state(chosen, days, set_day, today, timezone) -> dict:
    """Cooling counts only silences after it was turned on and after the user last set the stage."""
    if chosen['cooling_since'] is None:
        return {'steps': 0, 'warm_days_left': 0, 'silent_days': 0}
    since = max(local_day(chosen['cooling_since'], timezone), set_day or '')
    return cooling(days, since, today)


def nickname_line(current) -> str:
    if current['nickname']:
        return CHOSEN.format(nickname=current['nickname'])
    return COINED if current['level'] >= 3 else NO_NICKNAME


def context_text(current, definition) -> str:
    """The chat-context guidance for the current stage, within the relationship and traits the user chose."""
    lines = [f"{current['name']}. {OPENNESS[current['level'] - 1]}", nickname_line(current), RULES]
    if current['cooled_steps'] and not current['held_level']:
        lines.insert(1, COOLED)
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

COLUMNS = ('counted_from', 'held_level', 'nickname', 'head_start', 'set_on', 'ceiling_level', 'cooling_since')


def save(connection, timeline_id, timestamp, **values):
    current = options(connection, timeline_id) | values
    connection.execute(
        f"INSERT INTO closeness_settings (timeline_id, {', '.join(COLUMNS)}, updated_at) "
        f"VALUES (?, {', '.join('?' for _ in COLUMNS)}, ?) ON CONFLICT(timeline_id) DO UPDATE SET "
        + ', '.join(f'{column}=excluded.{column}' for column in (*COLUMNS, 'updated_at')),
        (timeline_id, *(current[column] for column in COLUMNS), timestamp))


def set_to(current: dict, level: int, timestamp: str) -> dict:
    """The head start that puts closeness exactly at `level` today, so it keeps growing from there. Setting it
    also lets go of a hold, lifts a ceiling below it and starts any cooling afresh."""
    earned = current['days_talked'] + current['counted_moments']
    values = {'head_start': THRESHOLDS[level - 1] - earned, 'set_on': timestamp, 'held_level': None}
    if current['ceiling_level'] and current['ceiling_level'] < level:
        values['ceiling_level'] = None
    return values


def view(database) -> dict:
    with database.connect() as connection:
        return state(connection, require_current(connection), database.clock.now())


def update(database, body) -> dict:
    """Set the stage (it keeps growing from there), hold it (or let it grow again with null), cap it, turn
    gentle cooling on or off and set the nickname, as given."""
    values = {key: getattr(body, key) for key in body.model_fields_set}
    if 'nickname' in values:
        values['nickname'] = (values['nickname'] or '').strip()[:NICKNAME_LIMIT]
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        timestamp, now = database.now(), database.clock.now()
        level = values.pop('set_level', None)
        if level:
            values |= set_to(state(connection, companion, now), level, timestamp)
        if 'cooling' in values:
            values['cooling_since'] = timestamp if values.pop('cooling') else None
        save(connection, companion['active_timeline_id'], timestamp, **values)
        return state(connection, companion, now)


def reset(database) -> dict:
    """Start counting again from now: the stage returns to the first (whatever it started at), a hold, a set
    stage and running jokes are cleared. The nickname, a ceiling and cooling are the user's own choices and stay."""
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        timeline_id = companion['active_timeline_id']
        save(connection, timeline_id, database.now(), counted_from=database.now(), held_level=None, head_start=0,
             set_on=None)
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
