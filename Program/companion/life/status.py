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

While the chat style is Retro IM, the everyday and away lines come from a bank of 2000s away messages instead
(world/data/retro_status.json): fake-deep lines, a song on repeat, sparkly emo when they feel low, random
inside jokes, and era-style away lines. Big events, payday, sick days and plans still show as usual.

Song lyrics are not in the app (it is public). A person can keep their own in retro-lyrics.txt in the data folder,
one per line; when it has any, quoted lyrics join the mix. The file stays on their computer and is never shared.
"""
import json
import re
from datetime import date, datetime, time, timedelta
from functools import cache
from pathlib import Path

from companion.clock import parse, stamp, zone
from companion.database import many, optional
from companion.life import chapters, money, pacing, storylines, trips
from companion.world import catalog, generators

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
LOW = ('annoyed', 'hurt', 'angry', 'anxious', 'sad')
# How often each kind of Retro IM line comes up for an everyday status.
RETRO_KINDS = (('fake_deep', 3.0), ('songs', 3.0), ('random', 3.0), ('emo', 1.0))
# Retro IM work lines that only fit a desk job or a shop counter; anyone else (a boatbuilder, a nurse) gets the
# lines that fit any work.
DESK_LINES = re.compile(r'email|office|cubicle|desk|copier|copies|fax|printer|spreadsheet|computer|keyboard|memo|'
                        r'meeting|reply-all|tech support|solitaire|clicking|elevator|water cooler|lanyard|wore a tie|'
                        r'supply closet|chair|vending|microwave|break room|fluorescent|filing|stapling|phone|'
                        r'mail|air conditioning|synergy|please hold', re.IGNORECASE)
SHOP_LINES = re.compile(r'register|shelves|mall|sweaters|store|drive-thru|polo shirt|name tag|slinging coffee',
                        re.IGNORECASE)
SHOP_SECTORS = {'retail', 'hospitality', 'food'}
LYRICS_WEIGHT = 3.0
LYRICS_FILE = 'retro-lyrics.txt'
LYRICS_TEMPLATE = """# Your own song lyrics for Retro IM status messages (Prospero's Companion).
# Put one lyric per line, the way you'd type it into an away message. Lines starting with # are skipped.
# While this file has any lyrics, companions sometimes show one as their status in the Retro IM chat style.
# This file stays on this computer: the app never sends it anywhere, and backups leave it out.
"""


@cache
def retro_bank() -> dict:
    return json.loads((catalog.DATA / 'retro_status.json').read_text(encoding='utf-8'))


def lyrics_path(connection) -> Path | None:
    """retro-lyrics.txt in the data folder every world shares (worlds live in worlds/<id>/ below it)."""
    found = next((row[2] for row in connection.execute('PRAGMA database_list') if row[1] == 'main'), '')
    if not found:
        return None
    folder = Path(found).parent
    return (folder.parent.parent if folder.parent.name == 'worlds' else folder) / LYRICS_FILE


@cache
def read_lyrics(path: str, _changed: float) -> tuple[str, ...]:
    lines = Path(path).read_text(encoding='utf-8', errors='replace').splitlines()
    kept = (' '.join(line.split())[:LIMIT] for line in lines if line.strip() and not line.lstrip().startswith('#'))
    return tuple(dict.fromkeys(kept))


def lyrics(connection) -> tuple[str, ...]:
    """The person's own lyrics, re-read whenever the file changes; none if it is missing or unreadable."""
    path = lyrics_path(connection)
    try:
        return read_lyrics(str(path), path.stat().st_mtime) if path else ()
    except OSError:
        return ()


def lyrics_template(root: Path):
    """Leaves an empty, explained retro-lyrics.txt in the data folder so people can find where lyrics go."""
    path = Path(root) / LYRICS_FILE
    try:
        if not path.exists():
            path.write_text(LYRICS_TEMPLATE, encoding='utf-8')
    except OSError:
        pass


def retro_line(seed: str, kind: str = '', own: tuple[str, ...] = ()) -> str:
    """A 2000s away message: of the given kind, else a weighted pick of fake-deep, a song, a joke, emo or a lyric."""
    bank = retro_bank()
    kinds = RETRO_KINDS + ((('lyrics', LYRICS_WEIGHT),) if own else ())
    kind = kind or generators.pick(seed, 'retro-kind', [name for name, _ in kinds], [weight for _, weight in kinds])
    if kind == 'lyrics':
        return f'♫ {generators.pick(seed, "retro-lyric", list(own))} ♫'[:LIMIT]
    if kind == 'songs':
        song = generators.pick(seed, 'retro-song', bank['songs'])
        return generators.pick(seed, 'retro-song-line', bank['song_lines']).format(song=song)
    return generators.pick(seed, f'retro-{kind}', bank[kind])


def retro_on(connection) -> bool:
    row = optional(connection, 'SELECT chat_style FROM workspace_settings WHERE id=1')
    return bool(row) and row['chat_style'] == 'retro'


def local(companion: dict, now):
    return now.astimezone(zone(companion['version']['timezone']))


def window(companion: dict, now) -> str:
    """'2026-10-10:am' or ':pm' in their time: the status is drawn once per window."""
    moment = local(companion, now)
    return f"{moment.date().isoformat()}:{'am' if moment.hour < 12 else 'pm'}"


def clock_text(moment, retro: bool = False) -> str:
    """'6:00 PM', '5:30 PM': an away message's time in the app's clock format (as messages show times). Retro IM
    writes it the 2000s way, '6pm' or '5:30pm'."""
    if retro:
        hour = moment.hour % 12 or 12
        return f"{hour}{'' if moment.minute == 0 else f':{moment.minute:02d}'}{'am' if moment.hour < 12 else 'pm'}"
    return f"{moment.hour % 12 or 12}:{moment.minute:02d} {'AM' if moment.hour < 12 else 'PM'}"


def away(connection, companion: dict, now, retro: bool = False) -> dict | None:
    """{text, glyph} while they are in a sleep, work, study, errand or social block, else None."""
    found = pacing.block_now(connection, companion, now)
    if not found:
        return None
    block, ends_at = found
    kind = 'sleep' if block['kind'] == 'sleep' else block['kind']
    if block.get('trip'):
        return trips.away_status(connection, block, f"{companion['id']}:{window(companion, now)}")
    if kind not in AWAY or block.get('sick_day') or block.get('holiday') or block.get('with_user'):
        return None
    until = clock_text(local(companion, parse(ends_at)), retro)
    seed = f"{companion['id']}:{window(companion, now)}:{kind}"
    lines = retro_away(companion['version']['definition'], kind) if retro else list(AWAY[kind])
    return {'text': generators.pick(seed, 'away', lines).format(until=until), 'glyph': GLYPHS[kind]}


def retro_away(definition: dict, kind: str) -> list[str]:
    """Retro IM away lines that fit them: the plain ones before the age of away messages (no emails in 1925), and
    at work only the lines that fit their job."""
    found = money.profile(definition)
    if found and found.era not in ('modern', 'future'):
        return list(AWAY[kind])
    lines = retro_bank()['away'][kind]
    career = found and found.career
    if kind != 'work' or not career:
        return lines
    desk, shop = career['schedule'] == 'office', career['sector'] in SHOP_SECTORS
    return [line for line in lines if (desk or not DESK_LINES.search(line)) and (shop or not SHOP_LINES.search(line))]


def big_events(connection, companion: dict, now) -> list[tuple[str, str, object]]:
    """(local date, line, when it came to be) for chapters and storyline beats they would share, from the last two
    days, newest first. A beat came to be at the start of its day, or when its outcome was decided."""
    found = [(row['started_on'], row['share'], parse(row['created_at']))
             for row in chapters.fresh(connection, companion, now) if row['share']]
    found += [(beat['on'], beat['share'], beat_since(connection, companion, beat))
              for _key, beat in storylines.fresh_beats(connection, companion, now) if beat.get('share')]
    return sorted(found, key=lambda item: (item[0], item[2]), reverse=True)


def beat_since(connection, companion: dict, beat: dict):
    start = datetime.combine(date.fromisoformat(beat['on']), time(), zone(companion['version']['timezone']))
    decided = beat.get('consequence') and optional(
        connection, 'SELECT COALESCE(changed_at, created_at) AS at FROM consequences WHERE id=?', (beat['consequence'],))
    return max(start, parse(decided['at'])) if decided else start


def mood_line(connection, companion: dict, now, seed: str, retro: bool = False) -> str:
    """How they feel. In Retro IM a low mood is a sparkly emo line, and a good one leaves it to the everyday line."""
    from companion import moods
    mood = moods.current(connection, f"companion:{companion['id']}", now)
    feeling = mood and mood['feeling']
    if retro:
        return retro_line(seed, 'emo') if feeling in LOW else ''
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


def written(connection, companion: dict, now, retro: bool = False) -> str:
    """The app's line for this half day."""
    seed = f"{companion['id']}:{window(companion, now)}"
    events = big_events(connection, companion, now)
    if events:
        return events[0][1][:LIMIT]
    return (day_line(connection, companion, now, seed) or mood_line(connection, companion, now, seed, retro)
            or plan_line(connection, companion, now, seed) or (retro_line(seed, own=lyrics(connection)) if retro else everyday(companion, seed)))


def users_line(connection, companion: dict, now) -> str:
    """The user's own line, until something big happens after they set it."""
    row = optional(connection, 'SELECT status_text, status_set_at FROM companions WHERE id=?', (companion['id'],))
    if not row or not row['status_text']:
        return ''
    since = parse(row['status_set_at'])
    newer = [on for on, _line, came in big_events(connection, companion, now) if came > since]
    return '' if newer else row['status_text']


def view(connection, companion: dict, now) -> dict:
    """{text, set_by: 'app'|'you', away: {text, glyph}|None}."""
    mine = users_line(connection, companion, now)
    retro = retro_on(connection)
    return {'text': mine or written(connection, companion, now, retro), 'set_by': 'you' if mine else 'app',
            'away': away(connection, companion, now, retro)}


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
