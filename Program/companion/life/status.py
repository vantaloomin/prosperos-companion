"""Status messages (Hit List #51): a line the companion "sets" for themselves, like an old AIM away message.

The app writes it from their life with rules and templates, and no model: a new chapter or a storyline
beat they would share, payday, how they feel, a plan coming up, else an everyday line drawn from who
they are. It is drawn once per half day (local morning and afternoon), so it changes at most twice a day,
except when something big happens.

While they are asleep, at work or out, a short in-character away line from the block they are in shows
instead ("at work till 6", "zzz"), with a glyph for the kind of block. It never locks the chat and never
reflects the user: it is only a hint, like a real person's away message (presence rule, Vanta 2026-10-10).
There are still no online or idle dots, read receipts or typing indicators.

The user can set the status. Their line stays until something big happens in the companion's life (a new
chapter or a storyline beat after it was set); a cleared line lets the app pick again. Lines only use what
the companion would share, so a secret never shows.
"""
from datetime import timedelta

from companion.clock import parse, stamp, zone
from companion.database import many, optional
from companion.life import chapters, money, pacing, storylines
from companion.world import generators

LIMIT = 120
MOODS = {'happy': ('good day ☀️', 'in a good mood, ask me anything', 'today was kind to me'),
         'excited': ("can't wait!!", 'buzzing', 'something good is coming ✨'),
         'annoyed': ('ugh.', 'one of those days', 'need a minute'),
         'hurt': ('…', 'quiet day', 'thinking'),
         'angry': ('do not.', 'not today', 'deep breaths'),
         'anxious': ('overthinking again', 'brain on spin cycle', 'one thing at a time'),
         'sad': ('rainy brain 🌧️', 'low key day', 'could use a hug')}
PAYDAY = ('payday 💸', 'treat yourself day', 'rich (for about a day)')
PLANS = ('plans {day} 🗓️', 'looking forward to {day}', '{day} cannot come soon enough')
EVERYDAY = ('coffee first ☕', 'living the dream', 'currently: {interest}', 'thinking about {interest} again',
            'ask me about {interest}', 'just vibing', 'one day at a time', 'brb, life')
SICK = ('home sick 🤒', 'tea, blankets, tissues', 'down for the count today')
HOLIDAY = ('day off 🎉', 'no alarms today', 'holiday mode')
AWAY = {'sleep': ('zzz', 'asleep, text you in the morning', 'lights out 😴'),
        'work': ('at work till {until}', 'working, back at {until}', 'on the clock till {until}'),
        'study': ('in class till {until}', 'studying till {until}', 'books till {until}'),
        'social': ('out with friends, back later', 'out and about', 'out, phone in pocket'),
        'errand': ('running errands', 'out for a bit', 'out, back soon')}
GLYPHS = {'sleep': 'moon', 'work': 'briefcase', 'study': 'briefcase', 'social': 'pin', 'errand': 'pin'}
PLAN_DAYS = 3


def local(companion: dict, now):
    return now.astimezone(zone(companion['version']['timezone']))


def window(companion: dict, now) -> str:
    """'2026-10-10:am' or ':pm' in their time: the status is drawn once per window."""
    moment = local(companion, now)
    return f"{moment.date().isoformat()}:{'am' if moment.hour < 12 else 'pm'}"


def clock_text(moment) -> str:
    """'6', '6:30': an away message's time, the way people write it."""
    hour = moment.hour % 12 or 12
    return f'{hour}' if moment.minute == 0 else f'{hour}:{moment.minute:02d}'


def away(connection, companion: dict, now) -> dict | None:
    """{text, glyph} while they are in a sleep, work, study, errand or social block, else None."""
    found = pacing.block_now(connection, companion, now)
    if not found:
        return None
    block, ends_at = found
    kind = 'sleep' if block['kind'] == 'sleep' else block['kind']
    if kind not in AWAY or block.get('sick_day') or block.get('holiday'):
        return None
    until = clock_text(local(companion, parse(ends_at)))
    seed = f"{companion['id']}:{window(companion, now)}:{kind}"
    return {'text': generators.pick(seed, 'away', list(AWAY[kind])).format(until=until), 'glyph': GLYPHS[kind]}


def big_events(connection, companion: dict, now) -> list[tuple[str, str]]:
    """(local date, line) for chapters and storyline beats they would share, from the last two days, newest first."""
    found = [(row['started_on'], row['share']) for row in chapters.fresh(connection, companion, now) if row['share']]
    found += [(beat['on'], beat['share']) for _key, beat in storylines.fresh_beats(connection, companion, now)
              if beat.get('share')]
    return sorted(found, reverse=True)


def mood_line(connection, companion: dict, now, seed: str) -> str:
    from companion import moods
    mood = moods.current(connection, f"companion:{companion['id']}", now)
    feeling = mood and mood['feeling']
    return generators.pick(seed, 'mood', list(MOODS[feeling])) if feeling in MOODS else ''


def plan_line(connection, companion: dict, now, seed: str) -> str:
    row = optional(connection, "SELECT starts_at FROM life_events WHERE timeline_id=? AND status='committed' "
                   "AND kind='plan' AND starts_at>? AND starts_at<=? ORDER BY starts_at LIMIT 1",
                   (companion['active_timeline_id'], stamp(now), stamp(now + timedelta(days=PLAN_DAYS))))
    if not row:
        return ''
    day = local(companion, parse(row['starts_at']))
    word = 'tonight' if day.date() == local(companion, now).date() else f'{day:%A}'.lower()
    return generators.pick(seed, 'plan', list(PLANS)).format(day=word)


def day_line(connection, companion: dict, now, seed: str) -> str:
    """Payday, a sick day or a day off, from the block they are in or their budget."""
    found = pacing.block_now(connection, companion, now)
    block = found[0] if found else {}
    if block.get('sick_day'):
        return generators.pick(seed, 'sick', list(SICK))
    if block.get('holiday'):
        return generators.pick(seed, 'holiday', list(HOLIDAY))
    budget = money.snapshot(companion['version']['definition'], local(companion, now).date().isoformat())
    return generators.pick(seed, 'payday', list(PAYDAY)) if (budget.get('payday') or {}).get('today') else ''


def everyday(companion: dict, seed: str) -> str:
    interests = [item for item in companion['version']['definition'].get('interests') or [] if len(item) <= 40]
    lines = [line for line in EVERYDAY if '{interest}' not in line or interests]
    interest = generators.pick(seed, 'interest', interests) if interests else ''
    return generators.pick(seed, 'everyday', lines).format(interest=interest.lower())


def written(connection, companion: dict, now) -> str:
    """The app's line for this half day."""
    seed = f"{companion['id']}:{window(companion, now)}"
    events = big_events(connection, companion, now)
    if events:
        return events[0][1][:LIMIT]
    return (day_line(connection, companion, now, seed) or mood_line(connection, companion, now, seed)
            or plan_line(connection, companion, now, seed) or everyday(companion, seed))


def users_line(connection, companion: dict, now) -> str:
    """The user's own line, until something big happens after they set it."""
    row = optional(connection, 'SELECT status_text, status_set_at FROM companions WHERE id=?', (companion['id'],))
    if not row or not row['status_text']:
        return ''
    since = local(companion, parse(row['status_set_at'])).date().isoformat()
    newer = [on for on, _line in big_events(connection, companion, now) if on > since]
    return '' if newer else row['status_text']


def view(connection, companion: dict, now) -> dict:
    """{text, set_by: 'app'|'you', away: {text, glyph}|None}."""
    mine = users_line(connection, companion, now)
    return {'text': mine or written(connection, companion, now), 'set_by': 'you' if mine else 'app',
            'away': away(connection, companion, now)}


def for_all(connection, now) -> dict[str, dict]:
    """Every companion's status, by companion id, for the chat list."""
    from companion.characters import by_id
    result = {}
    for row in many(connection, 'SELECT id FROM companions WHERE active_version_id IS NOT NULL'):
        companion = by_id(connection, row['id'])
        if companion and companion['active_timeline_id']:
            result[row['id']] = view(connection, companion, now)
    return result


def set_line(database, companion_id: str, text: str) -> dict:
    """The user sets (or, with an empty line, clears) a companion's status."""
    from companion.characters import by_id
    from companion.errors import require
    line = ' '.join(text.split())[:LIMIT]
    with database.connect(write=True) as connection:
        companion = by_id(connection, companion_id)
        require(companion is not None, 'No such companion.', 404)
        now = database.clock.now()
        connection.execute('UPDATE companions SET status_text=?, status_set_at=? WHERE id=?',
                           (line, stamp(now) if line else None, companion_id))
        return view(connection, companion, now)
