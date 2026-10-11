"""Family traditions and a seasonal home (Hit List #24): their family has its ways.

Thanksgiving is always at their mom's in Towson, and the decorations go up and come down with the seasons. Both
are decided by rules and a seed, never by a model, from companion/world/data/traditions.json:

- traditions: a few holidays from the city's calendar (companion/world/data/holidays.json), always its biggest
  family ones, each with a host from the circle (a parent first, then a sibling or a cousin; a friend for a
  night out like New Year's Eve), a dish and a ritual. Seeded once per timeline, after the circle exists; the
  user can reword one, drop it, bring it back or add their own. Text is kept with a {their} token so the same
  line reads "their mom" on the Character page and "your mom" in the chat context.
- decorations: what is up at home today, from the season windows below and a seeded keenness (some people go
  all out, some only put up a tree, a few never bother). Nothing is stored; the date decides.

They show in the occasions part of the chat context and on Today when a holiday is a week away or less
(companion/life/occasions.py), as the companion's day on the holiday itself (companion/life/agenda.py), and
the decorations in the home section of the context and in pictures taken at home.
"""
import json
import random
from datetime import date, timedelta
from functools import cache
from pathlib import Path

from companion.almanac.context import city_for
from companion.clock import parse, stamp, zone
from companion.database import decode, identifier, many, optional
from companion.errors import require
from companion.life import circle
from companion.world import catalog, generators

DATA = Path(__file__).parents[1] / 'world' / 'data' / 'traditions.json'
MOST = 5
TEXT_LIMIT = 400
PARENTS = ('mom', 'dad', 'parent')
SIBLINGS = ('sister', 'brother', 'sibling')
# Seasons that go up for anyone who decorates at all, and those only for the keen.
BIG = {'winter', 'newyear', 'lunar', 'chuseok'}
KEEN = {'autumn', 'spring', 'july', 'tanabata'}
NEVER, BIG_ONLY, HALLOWEEN_TOO = 0.15, 0.45, 0.6


@cache
def data() -> dict:
    return json.loads(DATA.read_text(encoding='utf-8'))


def calendar_of(city: dict | None) -> str | None:
    return catalog.calendar_id(city) if city else None


def entries(calendar: str | None) -> list[dict]:
    return [item for item in data()['traditions'] if calendar in item['calendars']]


def holiday_names(city: dict) -> dict[str, str]:
    return {item['id']: item['name'] for item in generators.city_holidays(city)}


def dated(city: dict, start: date, end: date) -> list[dict]:
    """The city's holidays from `start` to `end` inclusive: {id, name, date}."""
    return [{'id': item['id'], 'name': item['name'], 'date': date.fromisoformat(item['date'])}
            for item in generators.holidays(city, start, end)]


# --- Seeding ----------------------------------------------------------------------------------------

def family(people: list[dict], roles) -> list[dict]:
    return [person for person in people if person['role'] in roles]


def host_for(kind: str, people: list[dict], rng: random.Random, main: bool = True) -> dict | None:
    """Who a tradition happens with: a parent first for the big family holidays, anyone in the family (or nobody,
    at their own place) for the smaller ones, a friend for a night out. None means their own place."""
    if kind in ('mom', 'dad'):
        found = family(people, (kind,)) or family(people, ('parent',))
        return rng.choice(found) if found else None
    if kind == 'friends':
        found = [person for person in people if 'friend' in person['role']]
        return rng.choice(found) if found else None
    if not main:
        options = family(people, (*PARENTS, *SIBLINGS, 'cousin'))
        return rng.choice([*options, None]) if options else None
    for roles in (PARENTS, SIBLINGS, ('cousin',)):
        if found := family(people, roles):
            return rng.choice(found)
    return None


def where(person: dict) -> str:
    """Where a circle row lives: their neighborhood, or out of town when they have no routine here."""
    if not decode(person['schedule']):
        return ', out of town'
    neighborhood = decode(person['details']).get('neighborhood')
    return f' in {neighborhood}' if neighborhood else ''


HOME_FRAMES = ("Always at {their} {role} {name}'s{where}.",
               "Every year it's {their} {role} {name}'s place{where}.",
               "The whole family piles into {their} {role} {name}'s{where}.",
               "Same as every year: {their} {role} {name} hosts{where}.")
AWAY_FRAMES = ("It means going home to {their} {role} {name}'s, out of town.",
               "It's a trip home to {their} {role} {name}'s, out of town.")
OWN_FRAMES = ("It's {their} turn to host, at {their} own place.", "It happens at {their} own place these days.")
FRIEND_FRAMES = ("A standing plan with {their} friend {name}.", "It's always with {their} friend {name}.")


def compose(entry: dict, host: dict | None, rng: random.Random, turn: int = 0) -> str:
    """The tradition in a few plain sentences; the holiday's name sits above it. {their} stands for "their" or
    "your". `turn` picks the sentence frame, so a family's traditions don't all open the same way."""
    if entry['with'] == 'friends':
        opening = FRIEND_FRAMES[turn % 2].format(their='{their}', name=host['name']) if host else \
            "It's spent with friends."
    elif not host:
        opening = OWN_FRAMES[turn % 2]
    else:
        away = where(host) == ', out of town'
        frames = AWAY_FRAMES if away else HOME_FRAMES
        opening = frames[turn % len(frames)].format(
            their='{their}', role=host['role'], name=host['name'], where='' if away else where(host))
    dish, ritual = rng.choice(entry['dishes']), rng.choice(entry['rituals'])
    return f"{opening} There's always {dish}. {ritual}"


def teaser(connection, row: dict, holiday: str) -> str:
    """A short line for Today: "Thanksgiving at their mom Valerie's in Hampden". Just the holiday once the user
    has written their own."""
    host = optional(connection, 'SELECT * FROM circle_people WHERE id=?', (row['host_id'],)) if row['host_id'] else None
    if row['edited'] or row['origin'] == 'user':
        return holiday
    if not host:
        return f'{holiday} at their own place'
    if 'friend' in host['role']:
        return f"{holiday} with their friend {host['name']}"
    return f"{holiday} at their {host['role']} {host['name']}'s{where(host)}"


def seeded(timeline_id: str, city: dict, people: list[dict]) -> list[dict]:
    """The traditions a family keeps: every main one in the calendar, then a seeded few more, up to MOST."""
    names, calendar = holiday_names(city), calendar_of(city)
    rng = random.Random(f'traditions:{timeline_id}')
    found = [entry for entry in entries(calendar) if entry['holiday'] in names]
    mains = [entry for entry in found if entry['main']]
    others = [entry for entry in found if not entry['main']]
    rng.shuffle(others)
    chosen = mains + [entry for entry in others if rng.random() < 0.5][:max(0, MOST - len(mains))]
    result, turn = [], rng.randrange(len(HOME_FRAMES))
    for entry in chosen:
        pick = random.Random(f"traditions:{timeline_id}:{entry['holiday']}")
        host = host_for(entry['with'], people, pick, entry['main'])
        if entry['with'] in ('mom', 'dad') and not host:
            continue  # Mother's Day needs a mom in the circle.
        result.append({'holiday': entry['holiday'], 'host_id': host['id'] if host else None,
                       'text': compose(entry, host, pick, turn)})
        turn += 1
    return result


def ensure(connection, companion: dict, city: dict | None, now) -> int:
    """Seed the timeline's traditions once its circle exists. Never replaces a row, so the user's edits stay."""
    timeline_id = companion['active_timeline_id']
    if not city or optional(connection, 'SELECT 1 FROM family_traditions WHERE timeline_id=? LIMIT 1', (timeline_id,)):
        return 0
    people = circle.people(connection, timeline_id)
    rows = seeded(timeline_id, city, people)
    for row in rows:
        connection.execute('INSERT OR IGNORE INTO family_traditions (id, timeline_id, holiday, host_id, text, origin, '
                           "created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'seeded', ?, ?)",
                           (identifier(), timeline_id, row['holiday'], row['host_id'], row['text'], stamp(now),
                            stamp(now)))
    return len(rows)


# --- Reading ----------------------------------------------------------------------------------------

def kept(connection, timeline_id: str) -> list[dict]:
    return many(connection, 'SELECT * FROM family_traditions WHERE timeline_id=? AND removed=0 ORDER BY created_at, '
                'holiday', (timeline_id,))


def voiced(text: str, voice: str) -> str:
    return text.replace('{their}', voice)


def on_dates(connection, companion: dict, city: dict | None, start: date, end: date) -> dict[str, dict]:
    """Traditions falling between two local dates: {date: {holiday, name, host, text}} for the agenda."""
    rows = {row['holiday']: row for row in kept(connection, companion['active_timeline_id'])}
    if not rows or not city:
        return {}
    found = {}
    for item in dated(city, start, end):
        if row := rows.get(item['id']):
            host = optional(connection, "SELECT id, name, role, schedule FROM circle_people WHERE id=? AND "
                            "status='active'", (row['host_id'],)) if row['host_id'] else None
            found.setdefault(item['date'].isoformat(), {
                'holiday': item['id'], 'name': item['name'], 'friends': entry_with(city, item['id']) == 'friends',
                'host': {'id': host['id'], 'name': host['name'], 'role': host['role'],
                         'local': bool(decode(host['schedule']))} if host else None})
    return found


def entry_with(city: dict, holiday: str) -> str:
    return next((entry['with'] for entry in entries(calendar_of(city)) if entry['holiday'] == holiday), 'family')


def upcoming(connection, companion: dict, today: date, days: int) -> list[dict]:
    """Kept traditions whose holiday is within `days` of today: {holiday, name, date, days, text (your voice)}."""
    city = city_for(connection, companion['version']['definition'])
    rows = {row['holiday']: row for row in kept(connection, companion['active_timeline_id'])}
    if not city or not rows:
        return []
    return [{'id': rows[item['id']]['id'], 'holiday': item['id'], 'name': item['name'], 'date': item['date'],
             'days': (item['date'] - today).days, 'text': voiced(rows[item['id']]['text'], 'your'),
             'raw': rows[item['id']]['text'], 'short': teaser(connection, rows[item['id']], item['name'])}
            for item in dated(city, today, today + timedelta(days=days)) if item['id'] in rows]


def next_date(city: dict, holiday: str, today: date) -> date | None:
    found = [item['date'] for item in dated(city, today, today + timedelta(days=366)) if item['id'] == holiday]
    return found[0] if found else None


def view(connection, companion: dict, now) -> dict:
    """The Character page's panel: the traditions, the ones dropped, holidays free to add one for and what is up
    at home today."""
    timeline_id, version = companion['active_timeline_id'], companion['version']
    city = city_for(connection, version['definition'])
    today = now.astimezone(zone(version['timezone'])).date()
    names = holiday_names(city) if city else {}
    rows = many(connection, 'SELECT * FROM family_traditions WHERE timeline_id=? ORDER BY created_at, holiday',
                (timeline_id,))

    def item(row):
        when = next_date(city, row['holiday'], today) if city else None
        return {'id': row['id'], 'holiday': row['holiday'], 'name': names.get(row['holiday'], row['holiday']),
                'text': voiced(row['text'], 'their'), 'origin': row['origin'], 'edited': bool(row['edited']),
                'next': when.isoformat() if when else None}

    def listed(gone):
        return sorted((item(row) for row in rows if bool(row['removed']) == gone),
                      key=lambda found: found['next'] or '9999')

    taken = {row['holiday'] for row in rows}
    return {'traditions': listed(False), 'removed': listed(True),
            'holidays': [{'id': key, 'name': name} for key, name in names.items() if key not in taken],
            'decorations': decorations(home_seed(connection, timeline_id), city, today)}


# --- Edits ------------------------------------------------------------------------------------------

def row(connection, timeline_id: str, tradition_id: str) -> dict:
    found = optional(connection, 'SELECT * FROM family_traditions WHERE id=? AND timeline_id=?',
                     (tradition_id, timeline_id))
    require(found is not None, 'That tradition is not in their family.', 404)
    return found


def edit(connection, timeline_id: str, tradition_id: str, text: str, now):
    row(connection, timeline_id, tradition_id)
    connection.execute('UPDATE family_traditions SET text=?, edited=1, updated_at=? WHERE id=?',
                       (text.strip(), stamp(now), tradition_id))


def set_removed(connection, timeline_id: str, tradition_id: str, gone: bool, now):
    row(connection, timeline_id, tradition_id)
    connection.execute('UPDATE family_traditions SET removed=?, updated_at=? WHERE id=?',
                       (int(gone), stamp(now), tradition_id))


def add(connection, companion: dict, holiday: str, text: str, now):
    city = city_for(connection, companion['version']['definition'])
    require(bool(city) and holiday in holiday_names(city), 'That holiday is not on their calendar.', 422)
    timeline_id = companion['active_timeline_id']
    existing = optional(connection, 'SELECT id FROM family_traditions WHERE timeline_id=? AND holiday=?',
                        (timeline_id, holiday))
    require(existing is None, 'They already have a tradition for that holiday. Edit that one instead.', 409)
    connection.execute("INSERT INTO family_traditions (id, timeline_id, holiday, host_id, text, origin, edited, "
                       "created_at, updated_at) VALUES (?, ?, ?, NULL, ?, 'user', 1, ?, ?)",
                       (identifier(), timeline_id, holiday, text.strip(), stamp(now), stamp(now)))


def rebuild(connection, companion: dict, holiday: str, now):
    """After an edit: the companion's upcoming entries on that holiday are composed again from the traditions as
    they are now."""
    city = city_for(connection, companion['version']['definition'])
    if not city:
        return
    today = now.astimezone(zone(companion['version']['timezone'])).date()
    days = [item['date'].isoformat() for item in dated(city, today, today + timedelta(days=8)) if item['id'] == holiday]
    timeline_id, removed = companion['active_timeline_id'], 0
    for day in days:
        removed += connection.execute("DELETE FROM life_agenda WHERE timeline_id=? AND subject='companion' AND "
                                      "status='upcoming' AND local_date=?", (timeline_id, day)).rowcount
    if removed:
        connection.execute("UPDATE agenda_cursors SET through=MIN(through, ?) WHERE timeline_id=? AND "
                           "subject='companion'", (stamp(now), timeline_id))


def copy(connection, parent_id: str, new_id: str, ids: dict):
    """A fork keeps the family's traditions as they are."""
    for found in many(connection, 'SELECT * FROM family_traditions WHERE timeline_id=?', (parent_id,)):
        connection.execute('INSERT INTO family_traditions (id, timeline_id, holiday, host_id, text, origin, edited, '
                           'removed, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                           (identifier(), new_id, found['holiday'], ids.get(found['host_id'], found['host_id']),
                            found['text'], found['origin'], found['edited'], found['removed'], found['created_at'],
                            found['updated_at']))


# --- Decorations ------------------------------------------------------------------------------------

def home_seed(connection, timeline_id: str) -> str:
    found = optional(connection, 'SELECT seed FROM home_state WHERE timeline_id=?', (timeline_id,))
    return found['seed'] if found else f'home:{timeline_id}'


def offset(seed: str, season: str, year: int, most: int) -> int:
    return int(generators.unit(seed, 'decorations', season, str(year)) * (most + 1))


# Seasons tied to one holiday: (the holiday, its window from that holiday's date, the year and the home's seed).
TIED = {
    'halloween': ('halloween', lambda day, year, seed: (date(year, 10, 1) + timedelta(days=offset(seed, 'halloween', year, 20)),
                                                        date(year, 11, 1))),
    'autumn': ('thanksgiving', lambda day, year, seed: (date(year, 9, 20), day)),
    'spring': ('easter', lambda day, year, seed: (day - timedelta(days=14 - offset(seed, 'spring', year, 7)),
                                                  day + timedelta(days=3))),
    'july': ('independence-day', lambda day, year, seed: (date(year, 6, 27), date(year, 7, 6))),
    'tanabata': ('tanabata', lambda day, year, seed: (date(year, 7, 1), date(year, 7, 8))),
    'chuseok': ('chuseok', lambda day, year, seed: (day - timedelta(days=5), day + timedelta(days=2))),
    'lunar': ('seollal', lambda day, year, seed: (day - timedelta(days=10), day + timedelta(days=2))),
}
PERIOD = {'us-1920s', 'us-1880s', 'uk-victorian', 'medieval-england'}


def winter(seed: str, found: dict, calendar: str | None, year: int) -> list[tuple[str, date, date]]:
    """The winter holidays: up after Thanksgiving or in early December, down early in January. Earlier eras put
    greenery up just before Christmas and take it down on Twelfth Night; Japan swaps it for New Year's pine."""
    if calendar == 'japan':
        return [('winter', date(year, 12, 1) + timedelta(days=offset(seed, 'winter', year, 14)), date(year, 12, 26)),
                ('newyear', date(year, 12, 28), date(year + 1, 1, 7))]
    if 'christmas' not in found:
        return []
    if calendar in PERIOD:
        return [('winter', date(year, 12, 18) + timedelta(days=offset(seed, 'winter', year, 6)), date(year + 1, 1, 6))]
    start = found['thanksgiving'] + timedelta(days=1) if 'thanksgiving' in found else date(year, 12, 1)
    return [('winter', start + timedelta(days=offset(seed, 'winter', year, 14)),
             date(year + 1, 1, 1) + timedelta(days=offset(seed, 'down', year, 10)))]


def windows(seed: str, city: dict, year: int) -> list[tuple[str, date, date]]:
    """(season, up, down) for decorations put up in this year, from the city's calendar."""
    found = {item['id']: item['date'] for item in dated(city, date(year, 1, 1), date(year, 12, 31))}
    result = winter(seed, found, calendar_of(city), year)
    for season, (holiday, window) in TIED.items():
        if holiday in found:
            result.append((season, *window(found[holiday], year, seed)))
    return result


def seasons_up(seed: str, city: dict | None, day: date) -> list[str]:
    """The seasons whose decorations are up on this day, by how keen this home is."""
    if not city:
        return []
    keen = generators.unit(seed, 'decorations', 'keen')
    if keen < NEVER:
        return []
    found = []
    for year in (day.year - 1, day.year):
        for season, up, down in windows(seed, city, year):
            wanted = season in BIG or (season == 'halloween' and keen >= BIG_ONLY) or \
                (season in KEEN and keen >= HALLOWEEN_TOO)
            if wanted and up <= day < down and season not in found:
                found.append(season)
    return found


def decorations(seed: str, city: dict | None, day: date) -> list[str]:
    """What is up at home today, one seeded piece per season (the same piece all season)."""
    calendar = calendar_of(city)
    result = []
    for season in seasons_up(seed, city, day):
        choices = [item['text'] for item in data()['decorations']
                   if item['season'] == season and calendar in item['calendars']]
        if choices:
            year = day.year if day.month > 6 else day.year - 1
            result.append(choices[int(generators.unit(seed, 'decoration', season, str(year)) * len(choices))])
    return result


def decoration_line(connection, companion: dict, day: date) -> str | None:
    """The chat context's line about the home's decorations, or None when nothing is up."""
    city = city_for(connection, companion['version']['definition'])
    found = decorations(home_seed(connection, companion['active_timeline_id']), city, day)
    return f"- Up at home for the season: {' and '.join(found)}." if found else None


def image_hint(connection, timeline_id: str, event: dict) -> str:
    """Decorations in a picture taken at home on that day."""
    if event.get('place') or not event.get('starts_at'):
        return ''
    version = optional(connection, 'SELECT v.definition, v.timezone FROM timelines t JOIN companions c ON '
                       'c.id=t.companion_id JOIN character_versions v ON v.id=c.active_version_id WHERE t.id=?',
                       (timeline_id,))
    if not version:
        return ''
    day = parse(event['starts_at']).astimezone(zone(version['timezone'])).date()
    found = decorations(home_seed(connection, timeline_id), city_for(connection, decode(version['definition'])), day)
    return f"Decorated for the season: {' and '.join(found)}." if found else ''
