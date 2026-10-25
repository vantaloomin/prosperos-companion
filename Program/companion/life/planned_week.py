"""Their week, planned by the model: a few lines on what is on the main companion's mind (Settings > Life, off by
default; tester feedback 2026-10-25, A/B /mnt/project-files/companion-routines-ab/report.md).

The rules still decide the week: their routine, work or classes, plans and the people in it. With "Let the model plan
their week" on, the life model reads who they are and what the rules decided, once a week, and writes 3 to 5 lines
about what a person like them would be busy with or thinking about (a photography major's contact sheets, a
bartender's new menu). The chat reads them as their own section. A line that names a day, a time or a person the
week does not have, or a big life event, is dropped by `checked` before it is kept; when none is left, the week goes
without and the app tries again the next day. Only the companion open in the app gets a plan, and only while the
setting is on; turning it off drops the section at once.
"""
import re
from datetime import datetime, timedelta

from companion.clock import stamp, zone
from companion.database import decode, encode, optional
from companion.providers.chat import INCOMPLETE
from companion.providers.scheduling import LIFE_SYNTHESIS, BackgroundInterrupted

PROMPT_VERSION = 1
LINES = 5
LINE_MAX = 220
# A week that came back with nothing usable is tried again after this long.
RETRY = timedelta(days=1)
FILL = """You plan the coming week for {name}, a fictional character in an ongoing story, so their days match who they are.
The app already decided the facts below. Keep every one of them, and never contradict them or the character's description.

Who they are:
{card}

What the app decided for this week:
{facts}

Write 3 to 5 short lines about what is on their mind and how their days go this week: the specific things a person like them
would really be busy with or thinking about, drawn from their own work or studies, interests and situation in the description.
Rules: no new named people; no big life events (no breakups, new jobs, moves, illnesses, deaths); nothing about the user;
nothing that changes the decided facts. One line each, starting with "- ", in the second person ("You ..."), present tense."""
HEADING = 'On your mind this week (planned for you from who you are; keep to it, and bring it up only the way a person would)'
CARD = ('identity', 'personality', 'voice', 'background', 'routine', 'location')
WEEKDAYS = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
CLOCK = re.compile(r'\b\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)', re.IGNORECASE)
WEEKDAY = re.compile(r'\b(' + '|'.join(WEEKDAYS) + r')\b', re.IGNORECASE)
# The big turns the rules decide on their own (companion/life/big_turns.py, breakups.py, loss.py).
BIG = re.compile(r'\b(?:break(?:ing)? up|broke up|breakup|divorce|fired|laid off|new job|quit(?:ting)?|mov(?:e|ing) '
                 r'(?:out|away|to)|pregnan\w*|engaged|propos\w*|diagnos\w*|hospital\w*|surgery|died|dies|death|'
                 r'funeral|passed away|the user|your partner)\b', re.IGNORECASE)
# Capitalised words a line may start a sentence with or use without naming anyone.
COMMON = {'you', 'your', "you're", "you've", "you'll", 'i', 'the', 'a', 'an', 'and', 'but', 'so', 'between', 'after',
          'before', 'right', 'tonight', 'tomorrow', 'today', 'this', 'that', 'with', 'when', 'once', 'every', 'by',
          'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october',
          'november', 'december', *WEEKDAYS}
WORD = re.compile(r"[A-Z][\w'’-]*")


def enabled(connection) -> bool:
    return bool(optional(connection, 'SELECT model_routines FROM life_settings WHERE id=1')['model_routines'])


def week_of(companion, now: datetime) -> str:
    """The Monday of the companion's own week, so the plan turns over on their Monday."""
    today = now.astimezone(zone(companion['version']['timezone'])).date()
    return (today - timedelta(days=today.weekday())).isoformat()


def card(definition: dict) -> str:
    return '\n'.join(f'{key.capitalize()}: {definition[key]}' for key in CARD if definition.get(key))


def week_lines(connection, companion, now: datetime) -> list[str]:
    """Their work or classes for each day left this week, from the rules (companion/life/pacing.py)."""
    from companion.life import pacing
    from companion.memory.context import WORKING, block_name, clock_time
    tz = zone(companion['version']['timezone'])
    local = now.astimezone(tz)
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7 - local.weekday())
    days: dict[str, list[str]] = {}
    for block, starts_at, ends_at in pacing.day_blocks(connection, companion, start, end):
        if block['kind'] in WORKING and not block.get('sick_day'):
            day = starts_at.astimezone(tz).strftime('%A')
            days.setdefault(day, []).append(f'{block_name(block)} {clock_time(starts_at, tz)}-{clock_time(ends_at, tz)}')
    return [f'- {day}: {"; ".join(parts)}.' for day, parts in days.items()]


def facts(connection, companion, now: datetime) -> str:
    """What the rules decided: today, their work or classes this week, the job's lines and the next plans."""
    from companion.life import agenda, work
    from companion.memory.context import day_text
    lines = [f'- {line}' for line in day_text(connection, companion, now).splitlines() if line]
    lines += week_lines(connection, companion, now)
    lines += [text if text.startswith('- ') else f'- {text}' for _identity, text in
              work.context_lines(connection, companion, now)]
    upcoming = agenda.upcoming(connection, companion['active_timeline_id'], companion['version']['id'], now,
                               hours=24 * 7, limit=8)
    lines += [agenda.intention_text(item) for item in upcoming]
    return '\n'.join(lines)


def known_names(connection, companion) -> set[str]:
    """Words a line may name: everything in who they are and what the week holds, and the people in their life."""
    from companion.life import circle
    rows = circle.people(connection, companion['active_timeline_id'])
    names = {part for row in rows for part in row['name'].split()}
    return {name.casefold() for name in names}


def checked(text: str, allowed: str, names: set[str]) -> list[str]:
    """The model's lines that keep to the week: a day, a time or a capitalised name must appear in what the app
    decided (`allowed`, the card and facts) or be someone in their life; no big life events or the user."""
    allowed_lower, clocks = allowed.casefold(), {plain(found) for found in CLOCK.findall(allowed)}
    known = names | {word.casefold() for word in WORD.findall(allowed)}
    kept = []
    for line in text.splitlines():
        line = ' '.join(line.strip().split())
        if not line.startswith('- ') or len(line) > LINE_MAX or BIG.search(line):
            continue
        if any(day.casefold() not in allowed_lower for day in WEEKDAY.findall(line)):
            continue
        if any(plain(found) not in clocks for found in CLOCK.findall(line)):
            continue
        words = [word.strip("'’-").casefold() for word in WORD.findall(line[2:])]
        if any(word not in COMMON and word not in known for word in words):
            continue
        kept.append(line)
    return kept[:LINES]


def plain(clock: str) -> str:
    """"9 AM", "9:00 a.m." and "9am" alike."""
    found = re.match(r'(\d{1,2})(?::(\d{2}))?\s*([ap])', clock.casefold())
    if not found:
        return clock.casefold()
    return f"{int(found[1])}:{found[2] or '00'}{found[3]}"


def due(connection, companion, now: datetime) -> dict | None:
    """What the model is asked for the companion's week, or None when the setting is off or the week is planned."""
    if companion is None or not enabled(connection):
        return None
    week = week_of(companion, now)
    row = optional(connection, 'SELECT * FROM planned_weeks WHERE timeline_id=? AND week=?',
                   (companion['active_timeline_id'], week))
    if row and (decode(row['lines']) or datetime.fromisoformat(row['tried_at']) > now - RETRY):
        return None
    definition = companion['version']['definition']
    about, decided = card(definition), facts(connection, companion, now)
    prompt = prompt_text(connection, definition['name'], about, decided)
    return {'timeline_id': companion['active_timeline_id'], 'week': week, 'prompt': prompt,
            'allowed': about + '\n' + decided, 'names': known_names(connection, companion)}


def prompt_text(connection, name: str, about: str, decided: str) -> str:
    from companion import prompt_library
    return prompt_library.text(connection, 'planned-week', name=name, card=about, facts=decided)


async def write(provider, scheduler, config, key, found: dict) -> list[str]:
    """The model's lines for the week, checked; empty when nothing usable came back. Background priority: a
    conversation interrupts it."""
    pieces = []
    async with scheduler.reserve(config, LIFE_SYNTHESIS) as lease:
        async for chunk in provider.stream(config, key, found['prompt'], [{'role': 'user', 'content': 'Write the lines.'}]):
            if lease.stop.is_set():
                raise BackgroundInterrupted()
            pieces.append(chunk.text)
            if chunk.finish_reason in INCOMPLETE:
                return []
    return checked(''.join(pieces), found['allowed'], found['names'])


def save(connection, found: dict, lines: list[str], config: dict | None, now: datetime):
    connection.execute('INSERT INTO planned_weeks (timeline_id, week, lines, model, prompt_version, tried_at) '
                       'VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (timeline_id, week) DO UPDATE SET lines=excluded.lines, '
                       'model=excluded.model, prompt_version=excluded.prompt_version, tried_at=excluded.tried_at',
                       (found['timeline_id'], found['week'], encode(lines), (config or {}).get('model'),
                        PROMPT_VERSION, stamp(now)))


def lines_for(connection, companion, now: datetime) -> list[str]:
    """This week's kept lines, while the setting is on and the companion is the one open in the app."""
    from companion.characters import current
    if not enabled(connection) or (current(connection) or {}).get('id') != companion['id']:
        return []
    row = optional(connection, 'SELECT lines FROM planned_weeks WHERE timeline_id=? AND week=?',
                   (companion['active_timeline_id'], week_of(companion, now)))
    return decode(row['lines']) if row else []


def offer(packet, connection, companion, now: datetime):
    for number, line in enumerate(lines_for(connection, companion, now)):
        packet.offer('planned_week', f'planned:{number}', line)

