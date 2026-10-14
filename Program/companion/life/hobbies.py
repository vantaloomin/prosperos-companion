"""Hobbies that progress (Hit List #21, "Practice adds up"): pastimes with a skill that grows, milestones, dry spells.

Each companion keeps up to three pastimes (`MAX_ACTIVE`), their written interests first: an interest the catalogue
knows (world/data/hobbies/catalogue.json: "rock climbing", "the cello", "pottery") becomes a pastime they have been at
for a while, and when their interests name fewer than two or three, the app picks the rest from who they are and
their city's era. No model decides anything. Each pastime has a seeded skill (0 to 100), a talent and a weekly
rhythm; every session adds a little less as they get better, and passing a seeded threshold is a milestone drawn from
the bank for its kind (world/data/hobbies/<kind>.json, 100+ each, era-tagged): "finally sent their first V4". A
milestone day is always an event, so it reaches the feed with their own caption and the chat context.

Once a month (on a day seeded per timeline) a pastime may stall (work got busy), a stalled one may pick back up, an
app-added one stalled past a dry spell may be given up, and with room they may take up something new. Pastimes from
their written interests, and ones the user keeps, are never given up on their own. Gear for a new pastime and
monthly fees (classes, a climbing gym) are spending (`purchases`, money.household).

A timeline's life is walked one day at a time and written once to `hobby_log`, as pets.py does, so the past stays put;
every Monday a `mark` of each pastime is written, so after a change (a Realism setting, the user's edit, a fork) the
days ahead are walked again from the last mark (`rewind`). The Realism tab's slider (life_settings.hobbies_realism:
0 off, 1 light, 2 true to life, 3 dramatic) scales stalls, drops and new starts; off, nothing moves.

Other modules read it through `touch` (a practice session takes a free slot of their day), `context_lines` (the chat's
"hobbies" section), `purchases` (money), `news_due` and `invite_due` (first texts: a milestone, or asking the user
along), `patterns` and `outing_place` (the user suggesting one as a Go somewhere together plan, outings.py).
"""
import hashlib
import json
import re
from datetime import date, datetime, timedelta
from functools import cache
from pathlib import Path

from companion.clock import stamp, zone
from companion.database import decode, encode, identifier, many, optional
from companion.errors import require
from companion.life import circle, routine
from companion.world import generators, wording

COMPANION = 'companion'
BANKS = Path(__file__).resolve().parents[1] / 'world' / 'data' / 'hobbies'
MODERN = {'modern', 'future'}
# Practice sessions are woven into the companion's agenda, and now and then a milestone or an invitation opens a
# conversation; tests turn these off.
WEAVE = True
NEWS = True
INVITES = True

MAX_ACTIVE = 3
# The reason kept on a pastime the user gave up for them (not a dry spell).
USER_DROP = 'set aside by the user'
USER_MAX = 6
GAIN = 0.9
CEILING = 105
LEVEL_AT = (0, 10, 28, 50, 75)
LEVEL_TEXT = ('just starting out', 'getting the hang of it', 'getting good', 'good at it now', 'really good')
# By the hobbies slider (off, light, true to life, dramatic): a month's chance that an active pastime stalls, that a
# stalled one picks back up, that an app-added one stalled past the dry spell is given up, and that they take up a
# new one when there is room. Light (I want an easy life) never gives one up.
STALL = (0.0, 0.02, 0.05, 0.09)
RESUME = (0.0, 0.6, 0.4, 0.3)
DROP = (0.0, 0.0, 0.5, 0.7)
PICKUP = (0.0, 0.05, 0.1, 0.16)
DRY_SPELL = 56
RUST_AFTER = 30
RUST = 0.08
RUST_FLOOR = 0.75
OPEN_BLOCKS = {'leisure', 'rest'}
PLANNED = ('outing', 'own_plan', 'trip', 'recommendation', 'with', 'looks', 'hobby')
KEPT_ACTIVITIES = {'birthday', 'own-birthday', 'festival', 'tradition', 'gathering', 'sick-day'}
RECENT_DAYS = 21
GAVE_UP_DAYS = 120
SESSION_LINE = 0.45
CAPTIONS = ('Practice.', 'Another session in.', 'Slowly, then all at once.', 'Getting there.', 'Kept at it.',
            'The good kind of tired.', 'An hour well spent.', 'Showed up. That counts.')
NEWS_SHARE = 0.5
INVITE_EVERY = 21
INVITE_CHANCE = (0.0, 0.25, 0.35, 0.45)
INVITE_AHEAD = (2, 7)
USUAL = {'morning': ('09:30', '09:30'), 'evening': ('18:30', '14:00'), 'any': ('18:30', '14:00')}
CADENCE = {1: 'about once a week', 2: 'twice a week', 3: 'three times a week'}


# --- Banks ---

@cache
def catalogue() -> dict:
    return json.loads((BANKS / 'catalogue.json').read_text(encoding='utf-8'))


@cache
def bank(kind: str) -> dict:
    path = BANKS / f'{kind}.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'milestones': [], 'sessions': []}


@cache
def by_id() -> dict[str, dict]:
    return {item['id']: item for item in catalogue()['hobbies']}


def in_era(eras, era: str) -> bool:
    return 'any' in eras or era in eras


def era_of(data: dict | None) -> str:
    era = (data or {}).get('era') or 'modern'
    return 'modern' if era in MODERN else era


@cache
def word_patterns() -> list[tuple[re.Pattern, int, str]]:
    """(pattern, length, hobby id) for each word that names a pastime: longer words win, and stems of five letters
    or more match the start of a word ("calligraph" in "calligraphy")."""
    result = []
    for item in catalogue()['hobbies']:
        for word in item['words']:
            tail = r'\w*' if len(word) > 4 else r'\b'
            result.append((re.compile(rf'\b{re.escape(word)}{tail}', re.I), len(word), item['id']))
    return sorted(result, key=lambda found: -found[1])


def match(text: str, era: str | None = None) -> dict | None:
    """The catalogue pastime a phrase names ("bouldering on weekends" is rock climbing), in the era when given."""
    for pattern, _length, hobby_id in word_patterns():
        item = by_id()[hobby_id]
        if pattern.search(text or '') and (era is None or in_era(item['eras'], era)) and not any(
                re.search(rf'\b{re.escape(phrase)}', text, re.I) for phrase in item.get('not', ())):
            return item
    return None


def custom(name: str) -> dict:
    """A pastime the catalogue does not know, as the user wrote it: the general bank's milestones."""
    clean = ' '.join(name.replace('{', '').replace('}', '').split())[:40]
    return {'id': 'custom', 'label': clean[:1].upper() + clean[1:], 'name': clean, 'kind': 'general', 'eras': ['any'],
            'words': [], 'session': f'spent some time on {clean}', 'place': None, 'where': '', 'when': 'any',
            'together': None, 'ask': None, 'gear': None, 'fees': None, 'event': None,
            'picture': f'absorbed in {clean} at home'}


def entry_of(row: dict) -> dict:
    """The catalogue entry a tracked pastime follows."""
    return by_id().get(row['hobby']) or custom(row['name'])


# --- Who they are ---

def words_of(definition: dict) -> str:
    parts = [definition.get(key) or '' for key in ('identity', 'personality', 'background', 'voice')]
    return ' '.join([*parts, *definition.get('life_themes', ())]).casefold()


def natures(definition: dict) -> set[str]:
    text = words_of(definition)
    return {nature for nature, words in catalogue()['leanings'].items()
            if any(re.search(rf'\b{re.escape(word)}', text) for word in words)}


def written(definition: dict, era: str, extra=()) -> list[tuple[str, dict]]:
    """(interest, catalogue entry) for each written interest that names a pastime, first ones first, no repeats."""
    seen, result = set(), []
    for interest in [*(definition.get('interests') or ()), *extra]:
        item = match(interest, era) or match(interest)
        if item and item['id'] not in seen:
            seen.add(item['id'])
            result.append((interest, item))
    return result


def chapter_interests(connection, timeline_id: str) -> set[str]:
    """Interests a life chapter added (companion/life/chapters.py): taken up during the story, so the app's own."""
    rows = many(connection, "SELECT changes FROM life_chapters WHERE timeline_id=? AND undone_at IS NULL "
                "AND json_extract(changes, '$.interest') IS NOT NULL", (timeline_id,))
    return {decode(row['changes'])['interest'].casefold() for row in rows}


def available(item: dict, data: dict | None) -> bool:
    """Whether the city has somewhere for it: a pastime that needs a kind of place with certain tags (a climbing
    gym, a beach) only where the city has one."""
    place = item.get('place')
    if not place or not place.get('tags') or not data:
        return True
    return bool(places_for(item, data))


def places_for(item: dict, data: dict | None) -> list[dict]:
    place = item.get('place') or {}
    if not data or not place:
        return []
    wanted = set(place.get('tags') or ())
    return [found for found in data.get('places', ()) if found.get('kind') in place['kinds'] and
            (not wanted or wanted & set(found.get('tags') or ()))]


def choose_new(seed: str, label: str, definition: dict, data: dict | None, have: list[dict]) -> dict | None:
    """A pastime for the app to give them: one of their era the city has room for, leaning to who they are and away
    from kinds they already have."""
    era, taken = era_of(data), {row['hobby'] for row in have}
    kinds_had = {row['kind'] for row in have if row['status'] != 'dropped'}
    leaning = natures(definition)
    options = [item for item in catalogue()['hobbies'] if in_era(item['eras'], era) and item['id'] not in taken
               and available(item, data)]
    weights = [(3.0 if catalogue()['kinds'][item['kind']]['nature'] in leaning else 1.0) *
               (0.4 if item['kind'] in kinds_had else 1.0) for item in options]
    return generators.pick(seed, label, options, weights)


# --- State ---

def realism(connection) -> int:
    row = optional(connection, 'SELECT hobbies_realism FROM life_settings WHERE id=1')
    return row['hobbies_realism'] if row and row['hobbies_realism'] is not None else 2


def rows_of(connection, timeline_id: str) -> list[dict]:
    return many(connection, 'SELECT * FROM hobbies WHERE timeline_id=? ORDER BY position, created_at', (timeline_id,))


def as_of(connection, timeline_id: str, day: date) -> list[dict]:
    """Their pastimes as they stood on this local day: their life is walked a few days ahead with the agenda, so a
    stall or a new start written for later this week is not shown or told before it happens."""
    result = []
    for row in rows_of(connection, timeline_id):
        if row['created_on'] > day.isoformat():
            continue
        last = optional(connection, "SELECT kind, local_date, details FROM hobby_log WHERE hobby_id=? AND kind IN "
                        "('stalled', 'resumed', 'dropped') AND local_date<=? ORDER BY local_date DESC, created_at DESC "
                        'LIMIT 1', (row['id'], day.isoformat()))
        later = optional(connection, "SELECT id FROM hobby_log WHERE hobby_id=? AND kind IN ('stalled', 'resumed', "
                         "'dropped') AND local_date>? LIMIT 1", (row['id'], day.isoformat()))
        if later:
            status = {'stalled': 'stalled', 'resumed': 'active', 'dropped': 'dropped'}[last['kind']] if last else \
                'active'
            row = {**row, 'status': status, 'status_since': last['local_date'] if last else row['created_on'],
                   'reason': decode(last['details']).get('reason', '') if last else ''}
        # Practice already walked for the days ahead is not shown yet: the numbers as of the last session or mark.
        if optional(connection, "SELECT id FROM hobby_log WHERE hobby_id=? AND kind='session' AND local_date>? LIMIT 1",
                    (row['id'], day.isoformat())):
            known = optional(connection, "SELECT details FROM hobby_log WHERE hobby_id=? AND kind IN ('mark', 'session') "
                             "AND local_date<=? AND json_extract(details, '$.skill') IS NOT NULL ORDER BY local_date "
                             "DESC, kind='session' DESC, created_at DESC LIMIT 1", (row['id'], day.isoformat()))
            if known:
                numbers = decode(known['details'])
                row = {**row, **{key: numbers[key] for key in ('skill', 'best', 'sessions', 'next_at') if key in numbers}}
        result.append(row)
    return result


def start_day(connection, timeline_id: str, timezone: str, now) -> date:
    row = optional(connection, 'SELECT COALESCE(activated_at, created_at) AS since FROM timelines WHERE id=?',
                   (timeline_id,))
    since = datetime.fromisoformat(row['since'].replace('Z', '+00:00')) if row else now
    return min(since, now).astimezone(zone(timezone or 'UTC')).date()


def new_row(timeline_id: str, item: dict, source: str, day: date, seed: str, *, skill=None, months=None,
            position=0, now=None, name=None) -> dict:
    """A pastime as a row: written interests are years along, the app's first picks some months, new ones fresh."""
    label = f'{seed}:{item["id"]}:{name or ""}'
    span = {'interest': (12, 96), 'app': (2, 30), 'user': (0, 0), 'new': (0, 0)}[source]
    months = months if months is not None else span[0] + int((span[1] - span[0]) * generators.unit(label, 'months'))
    low, high = {'interest': (25, 70), 'app': (8, 45), 'user': (0, 6), 'new': (0, 4)}[source]
    skill = skill if skill is not None else low + (high - low) * generators.unit(label, 'skill')
    weekly = [1, 2, 3] if source == 'interest' else [1, 2]
    per_week = generators.pick(label, 'weekly', weekly, [3, 4, 2] if source == 'interest' else [5, 3])
    talent = 0.7 + 0.6 * generators.unit(label, 'talent')
    started = day - timedelta(days=int(months * 30.4))
    # Seeded, so a pastime taken up again on a re-walk is the same row, with the same sessions and milestones.
    row_id = hashlib.sha256(f'{timeline_id}:{label}:{source}:{day.isoformat()}:{position}'.encode()).hexdigest()[:32]
    return {'id': row_id, 'timeline_id': timeline_id, 'hobby': item['id'], 'label': item['label'],
            'name': name or item['name'], 'kind': item['kind'], 'source': 'app' if source == 'new' else source,
            'status': 'active', 'skill': round(skill, 2), 'best': round(skill, 2), 'talent': round(talent, 3),
            'per_week': per_week, 'started_on': started.isoformat(), 'status_since': day.isoformat(),
            'last_practice': None, 'sessions': 0, 'next_at': round(skill + (1.5 if months == 0 else step(label, 0)), 2),
            'used': '[]', 'reason': '', 'paid_through': '', 'kept': 0, 'position': position,
            'created_on': day.isoformat(), 'created_at': stamp(now) if now else '', 'updated_at': stamp(now) if now
            else ''}


def step(seed: str, count: int) -> float:
    return 4 + 5 * generators.unit(seed, 'step', count)


COLUMNS = ('id', 'timeline_id', 'hobby', 'label', 'name', 'kind', 'source', 'status', 'skill', 'best', 'talent',
           'per_week', 'started_on', 'status_since', 'last_practice', 'sessions', 'next_at', 'used', 'reason',
           'paid_through', 'kept', 'position', 'created_on', 'created_at', 'updated_at')
STATE = ('status', 'skill', 'best', 'status_since', 'last_practice', 'sessions', 'next_at', 'used', 'reason',
         'paid_through', 'per_week', 'kept')


def insert(connection, row: dict) -> None:
    connection.execute(f"INSERT INTO hobbies ({', '.join(COLUMNS)}) VALUES ({', '.join('?' * len(COLUMNS))})",
                       tuple(row[key] for key in COLUMNS))


def save_rows(connection, rows: list[dict], now) -> None:
    for row in rows:
        connection.execute(f"UPDATE hobbies SET {', '.join(f'{key}=?' for key in STATE)}, updated_at=? WHERE id=?",
                           (*(row[key] for key in STATE), stamp(now), row['id']))


def ensure(connection, timeline_id: str, definition: dict, world, now, timezone: str = 'UTC') -> dict:
    """The timeline's hobby state, seeding their pastimes the first time it is needed: written interests first, then
    the app's picks up to two or three."""
    state = optional(connection, 'SELECT * FROM hobby_state WHERE timeline_id=?', (timeline_id,))
    if state:
        return state
    seed, data = f'hobbies:{timeline_id}', circle.city_data(definition, world)
    day = start_day(connection, timeline_id, timezone, now)
    era, chapters = era_of(data), chapter_interests(connection, timeline_id)
    rows = []
    for interest, item in written(definition, era)[:MAX_ACTIVE]:
        source = 'app' if interest.casefold() in chapters else 'interest'
        rows.append(new_row(timeline_id, item, source, day, seed, position=len(rows), now=now))
    target = 2 + (generators.unit(seed, 'target') < 0.4)
    while len(rows) < target:
        item = choose_new(seed, f'first{len(rows)}', definition, data, rows)
        if not item:
            break
        rows.append(new_row(timeline_id, item, 'app', day, seed, position=len(rows), now=now))
    for row in rows:
        insert(connection, row)
    connection.execute('INSERT INTO hobby_state (timeline_id, seed, through, created_at, updated_at) VALUES '
                       '(?, ?, ?, ?, ?)', (timeline_id, seed, (day - timedelta(days=1)).isoformat(), stamp(now),
                                           stamp(now)))
    write_marks(connection, timeline_id, rows, day, now)
    return optional(connection, 'SELECT * FROM hobby_state WHERE timeline_id=?', (timeline_id,))


# --- The log ---

def log(connection, row: dict, day: date, kind: str, now, text='', post='', level=0, spend='', details=None) -> str:
    log_id = identifier()
    connection.execute('INSERT INTO hobby_log (id, timeline_id, hobby_id, local_date, kind, text, post, level, spend, '
                       'details, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                       (log_id, row['timeline_id'], row['id'], day.isoformat(), kind, text, post, level, spend,
                        encode(details or {}), stamp(now)))
    return log_id


def write_marks(connection, timeline_id: str, rows: list[dict], day: date, now) -> None:
    """Each pastime as it stands before this day, so a later change can walk the days from here again."""
    connection.execute("DELETE FROM hobby_log WHERE timeline_id=? AND kind='mark' AND local_date=?",
                       (timeline_id, day.isoformat()))
    for row in rows:
        log(connection, row, day, 'mark', now, details={key: row[key] for key in STATE})


def level_of(skill: float) -> int:
    return max(index for index, at in enumerate(LEVEL_AT) if skill >= at)


# --- Walking their life ---

class Life:
    """What a walk reads once: their state, pastimes, schedule, city, trips and outings."""

    def __init__(self, connection, timeline_id: str, definition: dict, world, state: dict, level: int | None = None):
        if world is None:
            from companion.world.source import CatalogWorld
            world = CatalogWorld()
        self.connection, self.timeline_id, self.definition, self.world = connection, timeline_id, definition, world
        self.seed, self.state = state['seed'], state
        self.level = realism(connection) if level is None else level
        self.data = circle.city_data(definition, world)
        self.era = era_of(self.data)
        self.schedule = routine.blocks(definition)[0]
        self.rows = rows_of(connection, timeline_id)
        row = optional(connection, 'SELECT companion_id FROM timelines WHERE id=?', (timeline_id,))
        self.companion_id = row['companion_id'] if row else None
        self.check_day = 1 + int(generators.unit(self.seed, 'check-day') * 28)
        self.memo: dict = {}

    def through(self) -> date:
        return date.fromisoformat(self.state['through'])

    def away(self, day: date) -> bool:
        from companion.life import trips
        return bool(self.companion_id) and trips.away_on(self.connection, self.companion_id, day)

    def outings_on(self, day: date) -> set[str]:
        """Pastimes the user does with them that day (Go somewhere together, outings.py)."""
        if 'outings' not in self.memo:
            from companion.life import outings
            found: dict[str, set] = {}
            for outing in outings.in_force(self.connection, self.timeline_id, self.state['through']):
                hobby = (outing['place'] or {}).get('hobby') if outing['activity'] == 'hobby' else None
                if hobby:
                    found.setdefault(outing['local_date'], set()).add(hobby['id'])
            self.memo['outings'] = found
        return self.memo['outings'].get(day.isoformat(), set())

    def free(self, day: date) -> list[str]:
        """The start times of free blocks in their routine that day."""
        return [block.view()['start'] for block in self.schedule if day.weekday() in block.days and
                block.kind in OPEN_BLOCKS]

    def week_days(self, row: dict, monday: date) -> set[date]:
        """The days they practise this week: seeded, leaning to days with free time when the pastime fits it."""
        key = ('week', row['id'], monday)
        if key not in self.memo:
            days = [monday + timedelta(days=offset) for offset in range(7)]
            when = entry_of(row)['when']
            weights = [0.05 + sum(fits(start, when, day) for start in self.free(day)) * (1.4 if day.weekday() >= 5
                                                                                        else 1.0) for day in days]
            chosen = set()
            for index in range(min(row['per_week'], 7)):
                options = [day for day in days if day not in chosen]
                chosen.add(generators.pick(row['id'], f'day:{monday.isoformat()}:{index}', options,
                                           [weights[days.index(day)] for day in options]))
            self.memo[key] = chosen
        return self.memo[key]


def fits(start: str, when: str, day: date) -> bool:
    """Whether a free block starting then suits a pastime done in the morning, the evening or any time."""
    if when == 'morning':
        return start < '12:00'
    if when == 'evening':
        return start >= '16:00' or day.weekday() >= 5 and start >= '12:00'
    return True


def evolve(life: Life, through: date, now) -> None:
    """Walk their pastimes up to `through`, once: walking in steps or all at once gives the same life."""
    day = life.through() + timedelta(days=1)
    if day > through:
        return
    sync(life, day, now)
    while day <= through:
        walk_day(life, day, now)
        day += timedelta(days=1)
    save_rows(life.connection, life.rows, now)
    life.state = {**life.state, 'through': through.isoformat()}
    life.connection.execute('UPDATE hobby_state SET through=?, updated_at=? WHERE timeline_id=?',
                            (through.isoformat(), stamp(now), life.timeline_id))


def sync(life: Life, day: date, now) -> None:
    """A newly written interest that names a pastime joins while there is room (a life chapter's as the app's)."""
    tracked = {row['hobby'] for row in life.rows} | {row['name'].casefold() for row in life.rows}
    going = [row for row in life.rows if row['status'] != 'dropped']
    chapters = chapter_interests(life.connection, life.timeline_id)
    for interest, item in written(life.definition, life.era):
        if item['id'] in tracked or len(going) >= MAX_ACTIVE:
            continue
        source = 'new' if interest.casefold() in chapters else 'interest'
        row = new_row(life.timeline_id, item, source, day, life.seed, position=len(life.rows), now=now,
                      months=0 if source == 'new' else None)
        insert(life.connection, row)
        life.rows.append(row)
        going.append(row)


def walk_day(life: Life, day: date, now) -> None:
    if day.weekday() == 0:
        write_marks(life.connection, life.timeline_id, life.rows, day, now)
    if not life.level:
        return
    away, monday = life.away(day), day - timedelta(days=day.weekday())
    with_user = life.outings_on(day)
    for row in life.rows:
        if row['id'] in with_user:
            if row['status'] == 'stalled':
                change(life, row, day, 'resumed', now)
            practise(life, row, day, now, together=True)
        elif row['status'] == 'active' and not away and day in life.week_days(row, monday):
            practise(life, row, day, now)
        else:
            rust(row, day)
    if day.day == life.check_day:
        monthly(life, day, now)


def practise(life: Life, row: dict, day: date, now, together=False) -> None:
    row['sessions'] += 1
    row['last_practice'] = day.isoformat()
    row['skill'] = round(row['skill'] + GAIN * row['talent'] * max(0.0, 1 - row['skill'] / CEILING), 3)
    row['best'] = max(row['best'], row['skill'])
    item = entry_of(row)
    log(life.connection, row, day, 'session', now, level=level_of(row['skill']),
        details={'together': together, **{key: row[key] for key in ('skill', 'best', 'sessions', 'next_at')}})
    month = day.isoformat()[:7]
    if item.get('fees') and row['paid_through'] != month:
        log(life.connection, row, day, 'fees', now, text=wording.regional(life.data, f"paid for {item['fees'][1]}"),
            spend=item['fees'][0])
        row['paid_through'] = month
    if row['skill'] >= row['next_at']:
        milestone(life, row, day, now)


def milestone(life: Life, row: dict, day: date, now) -> None:
    """A milestone from the bank for its kind that fits the level, the pastime and the era, not used before."""
    used = set(decode(row['used']))
    level = level_of(row['skill'])
    found = None
    for spread in (0, 1, 2):
        options = [(index, item) for index, item in enumerate(bank(row['kind'])['milestones'])
                   if index not in used and abs(item['level'] - level) <= spread and in_era(item['eras'], life.era)
                   and ('any' in item['for'] or row['hobby'] in item['for'])]
        weights = [3.0 if row['hobby'] in item['for'] else 1.0 for _index, item in options]
        found = generators.pick(row['id'], f'milestone:{row["sessions"]}', options, weights)
        if found:
            break
    row['next_at'] = round(row['skill'] + step(row['id'], row['sessions']), 2)
    if not found:
        return
    index, item = found
    row['used'] = encode(sorted(used | {index}))
    name = row['name']
    log(life.connection, row, day, 'milestone', now, text=wording.regional(life.data, item['text'].replace('{hobby}', name)),
        post=wording.regional(life.data, item['post'].replace('{hobby}', name)), level=level)


def rust(row: dict, day: date) -> None:
    """Out of practice for a month or more, the skill slips a little, never below three quarters of their best."""
    if row['status'] == 'dropped' or not row['last_practice']:
        return
    if (day - date.fromisoformat(row['last_practice'])).days > RUST_AFTER:
        row['skill'] = round(max(row['skill'] - RUST, row['best'] * RUST_FLOOR), 3)


def lines(key: str) -> list[str]:
    return catalogue()['lines'][key]


def change(life: Life, row: dict, day: date, kind: str, now) -> None:
    """A pastime stalls, picks back up or is given up, logged in words."""
    name = row['name']
    row['status_since'] = day.isoformat()
    if kind == 'stalled':
        row['status'] = 'stalled'
        row['reason'] = generators.pick(row['id'], f'stall:{day.isoformat()}', lines('stalls'))
        text = f"let {name} slide for a while because {row['reason']}"
    elif kind == 'resumed':
        row['status'], row['reason'] = 'active', ''
        text = generators.pick(row['id'], f'resume:{day.isoformat()}', lines('resumes')).format(name=name)
    else:
        row['status'] = 'dropped'
        text = generators.pick(row['id'], f'drop:{day.isoformat()}', lines('drops')).format(name=name) + \
            ' after a long dry spell'
    log(life.connection, row, day, kind, now, text=wording.regional(life.data, text), details={'reason': row['reason']})


def monthly(life: Life, day: date, now) -> None:
    """The month's turn: stalls, comebacks, giving up after a dry spell, and something new when there is room."""
    level, label = life.level, day.isoformat()
    for row in life.rows:
        roll = generators.unit(row['id'], 'month', label)
        if row['status'] == 'active':
            steady = row['source'] != 'app' or row['kept']
            if roll < STALL[level] * (0.5 if steady else 1.0) * (1.4 if row['talent'] < 0.85 else 1.0):
                change(life, row, day, 'stalled', now)
        elif row['status'] == 'stalled':
            dry = (day - date.fromisoformat(row['status_since'])).days >= DRY_SPELL
            if roll < RESUME[level]:
                change(life, row, day, 'resumed', now)
            elif row['source'] == 'app' and not row['kept'] and dry and \
                    generators.unit(row['id'], 'drop', label) < DROP[level]:
                change(life, row, day, 'dropped', now)
    going = [row for row in life.rows if row['status'] != 'dropped']
    if len(going) < MAX_ACTIVE and generators.unit(life.seed, 'pickup', label) < PICKUP[level]:
        take_up(life, day, now)


def take_up(life: Life, day: date, now) -> None:
    item = choose_new(life.seed, f'pickup:{day.isoformat()}', life.definition, life.data, life.rows)
    if not item:
        return
    row = new_row(life.timeline_id, item, 'new', day, life.seed, position=len(life.rows), now=now, months=0)
    insert(life.connection, row)
    life.rows.append(row)
    how = generators.pick(row['id'], 'how', lines('pickups'))
    log(life.connection, row, day, 'started', now, text=wording.regional(life.data, f"took up {row['name']} {how}"))
    if item.get('gear') and item['gear'][1]:
        log(life.connection, row, day, 'gear', now, text=wording.regional(life.data, item['gear'][1]),
            spend=item['gear'][0])


def life_for(connection, timeline_id: str, definition: dict, world, now, timezone: str = 'UTC',
             level: int | None = None) -> Life:
    return Life(connection, timeline_id, definition, world,
                ensure(connection, timeline_id, definition, world, now, timezone), level)


def rewind(life: Life, day: date, now) -> None:
    """Forget what was walked after `day` and restore each pastime from the last mark, then walk to `day` again under
    the same settings: the past stays the same, and the days after it can be walked afresh."""
    connection, timeline_id = life.connection, life.timeline_id
    mark = optional(connection, "SELECT MAX(local_date) AS day FROM hobby_log WHERE timeline_id=? AND kind='mark' AND "
                    'local_date<=?', (timeline_id, (day + timedelta(days=1)).isoformat()))
    if not mark or not mark['day']:
        return
    since = mark['day']
    marks = {row['hobby_id']: decode(row['details']) for row in many(
        connection, "SELECT hobby_id, details FROM hobby_log WHERE timeline_id=? AND kind='mark' AND local_date=?",
        (timeline_id, since))}
    connection.execute("DELETE FROM hobby_log WHERE timeline_id=? AND (local_date>? OR local_date=? AND kind!='mark')",
                       (timeline_id, since, since))
    for row in rows_of(connection, timeline_id):
        if row['id'] in marks:
            connection.execute(f"UPDATE hobbies SET {', '.join(f'{key}=?' for key in STATE)} WHERE id=?",
                               (*(marks[row['id']][key] for key in STATE), row['id']))
        elif row['source'] == 'app' and row['created_on'] >= since:
            connection.execute('DELETE FROM hobbies WHERE id=?', (row['id'],))
    previous = (date.fromisoformat(since) - timedelta(days=1)).isoformat()
    connection.execute('UPDATE hobby_state SET through=? WHERE timeline_id=?', (previous, timeline_id))
    life.state = {**life.state, 'through': previous}
    life.rows, life.memo = rows_of(connection, timeline_id), {}
    evolve(life, day, now)


def redraw(connection, timeline_id: str, now) -> None:
    """Upcoming agenda entries with a practice session are drawn again from the pastimes as they are now."""
    removed = connection.execute(
        "DELETE FROM life_agenda WHERE timeline_id=? AND subject=? AND status='upcoming' "
        "AND json_extract(entry, '$.hobby') IS NOT NULL", (timeline_id, COMPANION)).rowcount
    if removed:
        connection.execute('UPDATE agenda_cursors SET through=MIN(through, ?) WHERE timeline_id=? AND subject=?',
                           (stamp(now), timeline_id, COMPANION))


def settings_changed(connection, now, before: int) -> None:
    """The slider moved: each companion's pastimes are walked to today as they were, and from tomorrow under the new
    setting."""
    rows = many(connection, 'SELECT c.active_timeline_id AS timeline_id, v.timezone, v.definition FROM companions c '
                'JOIN character_versions v ON v.id=c.active_version_id JOIN hobby_state s ON '
                's.timeline_id=c.active_timeline_id')
    for row in rows:
        today = now.astimezone(zone(row['timezone'] or 'UTC')).date()
        life = life_for(connection, row['timeline_id'], decode(row['definition']), None, now, row['timezone'], before)
        rewind(life, today, now)
        write_marks(connection, life.timeline_id, life.rows, today + timedelta(days=1), now)
        redraw(connection, row['timeline_id'], now)


# --- Their day ---

def told(connection, timeline_id: str, session_id: str) -> bool:
    return bool(optional(connection, "SELECT id FROM life_agenda WHERE timeline_id=? AND subject=? AND "
                         "json_extract(entry, '$.hobby.session')=?", (timeline_id, COMPANION, session_id)))


def swappable(entry: dict | None, block: dict) -> bool:
    if block.get('kind') not in OPEN_BLOCKS or block.get('sick_day') or block.get('with_user'):
        return False
    if entry is None:
        return True
    return not any(entry.get(key) for key in PLANNED) and entry.get('activity') not in KEPT_ACTIVITIES


def touch(connection, timeline_id: str, subject: str, entry: dict | None, block: dict, local_date: str,
          definition: dict, world, now, timezone: str = 'UTC') -> dict | None:
    """The companion's agenda entry, or a practice session in its place: the first free slot of a practice day that
    suits the pastime (or any free slot when none does) holds it, with the day's milestone when there is one."""
    if subject != COMPANION or not WEAVE:
        return entry
    day = date.fromisoformat(local_date)
    life = life_for(connection, timeline_id, definition, world, now, timezone)
    evolve(life, day, now)
    if not swappable(entry, block):
        return entry
    for session in many(connection, "SELECT * FROM hobby_log WHERE timeline_id=? AND local_date=? AND kind='session' "
                        "AND json_extract(details, '$.together') IS NOT 1 ORDER BY created_at",
                        (timeline_id, local_date)):
        row = next((item for item in life.rows if item['id'] == session['hobby_id']), None)
        if row is None or told(connection, timeline_id, session['id']):
            continue
        when = entry_of(row)['when']
        if fits(block.get('start', ''), when, day) or not any(fits(start, when, day) for start in life.free(day)):
            return session_entry(life, row, session, entry, block, definition)
    return entry


def spot(life: Life, row: dict) -> dict | None:
    """Their usual place for it in the city, the same one each time, when the city has one."""
    places = places_for(entry_of(row), life.data)
    found = generators.pick(row['id'], 'spot', places)
    if not found:
        return None
    hoods = {hood['id']: hood['name'] for hood in (life.data or {}).get('neighborhoods', ())}
    return {'id': found['id'], 'name': found['name'], 'kind': found['kind'],
            'neighborhood': hoods.get(found.get('neighborhood'), '')}


def session_entry(life: Life, row: dict, session: dict, entry: dict | None, block: dict, definition: dict) -> dict:
    item, name = entry_of(row), definition['name']
    place = spot(life, row)
    did, where = item['session'], ''
    if place and item.get('where') and item['where'] in did:
        did = did.replace(item['where'], f"at {place['name']}")
    elif place:
        where = f" at {place['name']}"
    elif item.get('where') and item['where'] not in did:
        where = f" {item['where']}"
    summary = f"{name} {did}{where}."
    milestone_row = optional(life.connection, "SELECT * FROM hobby_log WHERE hobby_id=? AND local_date=? AND "
                             "kind='milestone'", (row['id'], session['local_date']))
    if milestone_row:
        summary += f" {name} {milestone_row['text']}."
        post = milestone_row['post']
    else:
        extra = session_line(life, row, session['id'])
        summary += f' {extra}' if extra else ''
        post = generators.pick(session['id'], 'caption', list(CAPTIONS))
    return {'summary': summary, 'post': post, 'mood': 'proud' if milestone_row else 'content', 'activity': 'hobby',
            'place': place, 'with': None, 'weather': (entry or {}).get('weather') or block.get('weather'),
            'hobby': {'id': row['id'], 'session': session['id'], 'label': row['label'], 'name': row['name'],
                      'milestone': milestone_row['id'] if milestone_row else None,
                      'picture': item['picture']},
            'composer_version': 'hobby-1'}


def session_line(life: Life, row: dict, seed: str) -> str:
    if generators.unit(seed, 'line?') >= SESSION_LINE:
        return ''
    options = [line['text'] for line in bank(row['kind']).get('sessions', ())
               if in_era(line['eras'], life.era) and ('any' in line['for'] or row['hobby'] in line['for'])]
    line = generators.pick(seed, 'line', options)
    return wording.regional(life.data, line.replace('{hobby}', row['name'])) if line else ''


# --- In words ---

def since_text(row: dict, day: date) -> str:
    """'about two years', 'four months', 'a few weeks', 'a few days'."""
    days = (day - date.fromisoformat(row['started_on'])).days
    if days < 10:
        return 'a few days'
    if days < 45:
        return 'a few weeks'
    if days < 330:
        months = max(2, round(days / 30.4))
        return f'{NUMBERS.get(months, str(months))} months'
    years = round(days / 365)
    return 'about a year' if years <= 1 else f'about {NUMBERS.get(years, str(years))} years'


NUMBERS = {2: 'two', 3: 'three', 4: 'four', 5: 'five', 6: 'six', 7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten',
           11: 'eleven'}
PANEL_LEVELS = ('Just started {name}', 'Getting the hang of {name}', 'Getting good at {name}', 'Good at {name}',
                'Really good at {name}')


def month_text(local_date: str) -> str:
    return f'{date.fromisoformat(local_date):%B}'


def context_lines(connection, timeline_id: str, now, timezone: str, definition: dict | None = None) \
        -> list[tuple[str, str]]:
    """(identity, line) pairs for the chat's "hobbies" section: each pastime, how far along they are and how often
    they go, one stalled lately or given up not long ago, and the milestones of the last three weeks."""
    if not optional(connection, 'SELECT seed FROM hobby_state WHERE timeline_id=?', (timeline_id,)):
        return []
    today = now.astimezone(zone(timezone or 'UTC')).date()
    data = circle.city_data(definition or {}, None) if definition else None
    result = []
    for row in as_of(connection, timeline_id, today):
        if text := pastime_line(row, today, data):
            result.append((f"hobbies:{row['id']}:{row['status']}:{level_of(row['skill'])}", text))
    since = (today - timedelta(days=RECENT_DAYS)).isoformat()
    for found in many(connection, "SELECT l.*, h.label FROM hobby_log l JOIN hobbies h ON h.id=l.hobby_id WHERE "
                      "l.timeline_id=? AND l.kind='milestone' AND l.local_date>? AND l.local_date<=? ORDER BY "
                      'l.local_date DESC LIMIT 2', (timeline_id, since, today.isoformat())):
        day = date.fromisoformat(found['local_date'])
        when = 'today' if day == today else 'yesterday' if day == today - timedelta(days=1) else \
            f'on {day:%A, %B} {day.day}'
        result.append((f"hobbies:milestone:{found['id']}",
                       f"- Lately: {when} you {yours(found['text'])} ({wording.regional(data, found['label'])})."))
    return result


def pastime_line(row: dict, today: date, data: dict | None) -> str:
    label = wording.regional(data, row['label'])
    if row['status'] == 'dropped':
        if (today - date.fromisoformat(row['status_since'])).days > GAVE_UP_DAYS:
            return ''
        why = '' if row.get('reason') == USER_DROP else ' after a dry spell'
        return f"- {label}: you gave it up in {month_text(row['status_since'])}{why}."
    how = f"{since_text(row, today)} in, {LEVEL_TEXT[level_of(row['skill'])]}"
    if row['status'] == 'stalled':
        return f"- {label}: {how}; it has stalled lately ({yours(row['reason'])})."
    return f"- {label}: {how}; you get to it {CADENCE.get(row['per_week'], 'most weeks')}."


YOURS = {'their': 'your', 'theirs': 'yours', 'they': 'you', 'them': 'you', 'themselves': 'yourself',
         'themself': 'yourself', "they're": "you're", "they've": "you've", "they'd": "you'd", "they'll": "you'll"}


def yours(text: str) -> str:
    """A bank line about them ("learned their first barre chord") as said to them, for the chat."""
    return re.sub(r"\b(?:their|theirs|they're|they've|they'd|they'll|they|them|themselves|themself)\b",
                  lambda found: YOURS[found.group(0).lower()], text, flags=re.I)


def level_line(row: dict) -> str:
    return PANEL_LEVELS[level_of(row['skill'])].format(name=row['name'])


# --- Money ---

def purchases(connection, timeline_id: str, start: date, end: date) -> list[dict]:
    """Gear for a new pastime and the month's fees between two local dates, as money.household purchases."""
    rows = many(connection, "SELECT * FROM hobby_log WHERE timeline_id=? AND spend!='' AND local_date>=? AND "
                'local_date<=? ORDER BY local_date', (timeline_id, start.isoformat(), end.isoformat()))
    return [{'date': row['local_date'], 'text': row['text'], 'spend': row['spend'], 'for': 'hobby'} for row in rows]


# --- First texts ---

def news_due(connection, companion: dict, now: datetime) -> list:
    """Now and then a milestone from today opens a conversation: they tell the user, as they would a friend."""
    from companion.life.openers import Trigger
    version = companion['version']
    local = now.astimezone(zone(version['timezone']))
    if not NEWS or not 9 <= local.hour < 22:
        return []
    found = optional(connection, "SELECT l.*, h.name FROM hobby_log l JOIN hobbies h ON h.id=l.hobby_id WHERE "
                     "l.timeline_id=? AND l.kind='milestone' AND l.local_date=? ORDER BY l.created_at LIMIT 1",
                     (companion['active_timeline_id'], local.date().isoformat()))
    if not found or generators.unit(found['id'], 'news?') >= NEWS_SHARE:
        return []
    reason = (f"Something you are proud of happened with {found['name']} today: "
              f"you {yours(found['text'])}. "
              'Tell the user about it in your own words, the way you would tell a friend.')
    return [Trigger(f"hobby-news:{found['id']}", 'hobby_news', reason, found['post'], (found['id'],))]


def usual_time(item: dict, day: date) -> str:
    weekday, weekend = USUAL[item.get('when') or 'any']
    return weekend if day.weekday() >= 5 else weekday


def invite_due(connection, companion: dict, now: datetime) -> list:
    """Now and then a first text asking the user along to a pastime (a climbing session, their open mic night) a few
    days off, on a free day. Saving the text settles the plan (`settle_invite`)."""
    from companion.life import outings
    from companion.life.openers import Trigger
    version = companion['version']
    definition, timeline_id = version['definition'], companion['active_timeline_id']
    local = now.astimezone(zone(version['timezone']))
    state = optional(connection, 'SELECT * FROM hobby_state WHERE timeline_id=?', (timeline_id,))
    level = realism(connection)
    if not INVITES or not state or not 10 <= local.hour < 21:
        return []
    window = local.date().toordinal() // INVITE_EVERY
    if generators.unit(state['seed'], 'invite?', window) >= INVITE_CHANCE[level]:
        return []
    choices = [row for row in rows_of(connection, timeline_id) if row['status'] == 'active' and
               entry_of(row).get('together')]
    row = generators.pick(state['seed'], f'invite:{window}', choices)
    if not row:
        return []
    item, schedule = entry_of(row), routine.blocks(definition)[0]
    for ahead in range(*INVITE_AHEAD):
        day = local.date() + timedelta(days=ahead)
        at = usual_time(item, day)
        if outings.busy_at(schedule, day, at) or outings.cut_short(schedule, day, at, outings.until(at, 'hobby')) or \
                outings.taken(connection, companion, day):
            continue
        return [Trigger(f'hobby-invite:{timeline_id}:{window}', 'hobby_invite', invite_reason(row, item, day, at),
                        invite_template(item, day), (day.isoformat(), at, row['id']))]
    return []


def invite_reason(row: dict, item: dict, day: date, at: str) -> str:
    when = f'{day:%A, %B} {day.day} at {datetime.strptime(at, "%H:%M"):%I:%M %p}'.replace(' 0', ' ')
    since = since_text(row, day)
    if item.get('event'):
        return (f"You have {yours(item['event'])} on {when}, and you want the user to come and watch. You have been doing "
                f"{row['name']} for {since}. Invite them in your own words, naming the day.")
    return (f"You want the user to come along to {yours(item['together'])} with you on {when}. You have been doing "
            f"{row['name']} for {since} and are {LEVEL_TEXT[level_of(row['skill'])]}, so it is fine if they are new "
            'to it. Invite them in your own words, naming the day.')


def invite_template(item: dict, day: date) -> str:
    if item.get('ask'):
        return f"Want to {item['ask']} {day:%A}?"
    return f"Want to come along to {item['together']} {day:%A}?"


def settle_invite(connection, companion: dict, message: dict, trigger, timestamp: str) -> dict | None:
    """The invitation a first text made, as a plan for that day (the user can call it off on Today)."""
    from companion.life import outings
    day, at, row_id = date.fromisoformat(trigger.sources[0]), trigger.sources[1], trigger.sources[2]
    wanted = {'activity': 'hobby', 'day': day, 'at': at, 'place': None, 'word': '', 'waterside': False,
              'hobby': row_id}
    return outings.save(connection, companion, message, wanted, outings.city_data(
        connection, companion['version']['definition']), day, at, timestamp)


# --- Going together (outings.py) ---

def usual_at(connection, row_id: str, day: date) -> str | None:
    """The time of day they usually do this pastime ("go birding Saturday" is a morning), for a plan with no time."""
    row = optional(connection, 'SELECT * FROM hobbies WHERE id=?', (row_id,))
    return usual_time(entry_of(row), day) if row else None


def outing_added(connection, companion: dict, now) -> None:
    """A pastime with the user was just planned: the days already walked ahead are walked again, so the session
    together counts (and a stalled pastime picks back up)."""
    version = companion['version']
    timeline_id, today = companion['active_timeline_id'], now.astimezone(zone(version['timezone'] or 'UTC')).date()
    life = life_for(connection, timeline_id, version['definition'], None, now, version['timezone'])
    rewind(life, today, now)
    after_edit(connection, timeline_id, today, now)


def patterns(connection, timeline_id: str) -> list[dict]:
    """Each pastime they still do, with the words that name it in a message ("want to go climbing Saturday?")."""
    result = []
    for row in rows_of(connection, timeline_id):
        if row['status'] == 'dropped':
            continue
        words = entry_of(row)['words'] or [row['name']]
        pattern = re.compile(r'\b(?:' + '|'.join(re.escape(word) + (r'\w*' if len(word) > 4 else r'\b')
                                                 for word in words) + ')', re.I)
        result.append({'id': row['id'], 'pattern': pattern})
    return result


def outing_place(connection, timeline_id: str, row_id: str, definition: dict, data: dict | None) -> dict | None:
    """Where a pastime with the user happens, as an outing's place: their usual spot in the city, or the kind of
    place it is when the city has none (`spot`), with the pastime itself under `hobby`."""
    row = optional(connection, 'SELECT * FROM hobbies WHERE id=? AND timeline_id=?', (row_id, timeline_id))
    if not row:
        return None
    item = entry_of(row)
    places = places_for(item, data)
    found = generators.pick(row['id'], 'spot', places)
    hobby = {'id': row['id'], 'label': row['label'], 'session': item['session'], 'together': item.get('together') or
             row['label'].lower(), 'event': item.get('event'), 'picture': item['picture']}
    if found:
        from companion.life import outings
        return {**outings.place_view(found, data), 'hobby': hobby}
    where = (item.get('where') or 'at home').removeprefix('at ').removeprefix('in ').removeprefix('on ')
    return {'id': f"~hobby:{row['id']}", 'name': f"{definition['name']}'s place" if where == 'home' else where,
            'kind': 'home' if where == 'home' else 'spot', 'neighborhood': '', 'summary': '', 'cost': '',
            'cuisine': '', 'city': (data or {}).get('name', ''), 'city_id': (data or {}).get('id', ''), 'spots': [],
            'hobby': hobby}


# --- View and edits ---

def view(connection, timeline_id: str, definition: dict, world, now, timezone: str, show_numbers: bool = False) -> dict:
    """The Character page's Pastimes panel, in words; the numbers only when Hidden values are shown."""
    life = life_for(connection, timeline_id, definition, world, now, timezone)
    today = now.astimezone(zone(timezone or 'UTC')).date()
    evolve(life, today, now)
    result = [row_view(connection, {**row, 'label': wording.regional(life.data, row['label']),
                                    'name': wording.regional(life.data, row['name'])}, today, show_numbers)
              for row in as_of(connection, timeline_id, today)]
    going = sum(row['status'] != 'dropped' for row in result)
    return {'today': today.isoformat(), 'hobbies': result, 'level_names': list(LEVEL_TEXT), 'realism': life.level,
            'can_add': going < USER_MAX}


def row_view(connection, row: dict, today: date, show_numbers: bool) -> dict:
    recent = many(connection, "SELECT local_date, kind, text FROM hobby_log WHERE hobby_id=? AND kind IN "
                  "('milestone', 'stalled', 'resumed', 'dropped', 'started') AND local_date<=? ORDER BY local_date DESC "
                  'LIMIT 4', (row['id'], today.isoformat()))
    item = entry_of(row)
    result = {'id': row['id'], 'label': row['label'], 'name': row['name'], 'kind': row['kind'], 'source': row['source'],
              'status': row['status'], 'level': level_of(row['skill']), 'kept': bool(row['kept']),
              'level_text': level_line(row), 'since_text': f"{since_text(row, today)[:1].upper()}"
                                                           f"{since_text(row, today)[1:]} in",
              'status_text': status_text(row, item), 'recent': [{'date': found['local_date'], 'kind': found['kind'],
                                                                 'text': found['text']} for found in recent]}
    if show_numbers:
        result['numbers'] = {'skill': round(row['skill']), 'best': round(row['best']), 'sessions': row['sessions'],
                             'next_at': round(row['next_at']), 'talent': row['talent']}
    return result


def status_text(row: dict, item: dict) -> str:
    if row['status'] == 'dropped':
        return f"Gave it up in {month_text(row['status_since'])}."
    if row['status'] == 'stalled':
        return f"Stalled lately: {row['reason']}."
    return f"{CADENCE.get(row['per_week'], 'most weeks').capitalize()}."


def add(connection, timeline_id: str, definition: dict, world, now, timezone: str, name: str,
        level: int | None = None) -> dict:
    """A pastime the user gives them: the catalogue's when it knows it, else as written."""
    life = life_for(connection, timeline_id, definition, world, now, timezone)
    today = now.astimezone(zone(timezone or 'UTC')).date()
    clean = ' '.join((name or '').split())
    require(1 <= len(clean) <= 40, 'Name the pastime in a few words.', 422)
    going = [row for row in life.rows if row['status'] != 'dropped']
    require(len(going) < USER_MAX, f'They can keep up to {USER_MAX} pastimes going at once.', 409)
    item = match(clean) or custom(clean)
    existing = next((row for row in life.rows if row['hobby'] == item['id'] and (item['id'] != 'custom' or
                                                                                 row['name'] == item['name'])), None)
    rewind(life, today, now)
    if existing:
        connection.execute("UPDATE hobbies SET status='active', reason='', status_since=?, kept=1 WHERE id=?",
                           (today.isoformat(), existing['id']))
    else:
        skill = LEVEL_AT[level] + 2 if level is not None else None
        row = new_row(timeline_id, item, 'user', today, life.seed, position=len(life.rows), now=now, skill=skill,
                      name=None if item['id'] != 'custom' else item['name'])
        row['kept'] = 1
        insert(connection, row)
    after_edit(connection, timeline_id, today, now)
    return {}


def edit(connection, timeline_id: str, row_id: str, body: dict, definition: dict, world, now, timezone: str) -> None:
    """The user's change to one pastime: how good they are, keeping it, or giving it up or taking it back up."""
    life = life_for(connection, timeline_id, definition, world, now, timezone)
    today = now.astimezone(zone(timezone or 'UTC')).date()
    require(any(row['id'] == row_id for row in life.rows), 'That pastime could not be found.', 404)
    rewind(life, today, now)
    row = optional(connection, 'SELECT * FROM hobbies WHERE id=?', (row_id,))
    changes = {}
    if body.get('level') is not None:
        skill = LEVEL_AT[body['level']] + (LEVEL_AT[min(body['level'] + 1, 4)] - LEVEL_AT[body['level']]) * 0.3 \
            if body['level'] < 4 else 82.0
        changes.update(skill=round(skill, 2), best=max(row['best'], skill), next_at=round(skill + step(row_id, 0), 2))
    if body.get('kept') is not None:
        changes['kept'] = int(body['kept'])
    if body.get('status') in ('active', 'dropped') and body['status'] != row['status']:
        changes.update(status=body['status'], status_since=today.isoformat(),
                       reason=USER_DROP if body['status'] == 'dropped' else '')
        if body['status'] == 'active':
            changes['kept'] = 1
    if changes:
        connection.execute(f"UPDATE hobbies SET {', '.join(f'{key}=?' for key in changes)} WHERE id=?",
                           (*changes.values(), row_id))
    after_edit(connection, timeline_id, today, now)


def after_edit(connection, timeline_id: str, today: date, now) -> None:
    write_marks(connection, timeline_id, rows_of(connection, timeline_id), today + timedelta(days=1), now)
    redraw(connection, timeline_id, now)


# --- Timelines ---

def copy(connection, parent_id: str, new_id: str, cutoff: str) -> None:
    """A fork keeps their pastimes and what happened up to the cutoff; the same seed walks the days after it the same
    way until something changes."""
    state = optional(connection, 'SELECT * FROM hobby_state WHERE timeline_id=?', (parent_id,))
    if not state:
        return
    ids = {}
    for row in rows_of(connection, parent_id):
        ids[row['id']] = identifier()
        insert(connection, {**row, 'id': ids[row['id']], 'timeline_id': new_id})
    connection.execute('INSERT INTO hobby_state (timeline_id, seed, through, created_at, updated_at) VALUES '
                       '(?, ?, ?, ?, ?)', (new_id, state['seed'], state['through'], state['created_at'], cutoff))
    for row in many(connection, 'SELECT * FROM hobby_log WHERE timeline_id=?', (parent_id,)):
        if row['hobby_id'] in ids:
            connection.execute('INSERT INTO hobby_log (id, timeline_id, hobby_id, local_date, kind, text, post, level, '
                               'spend, details, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                               (identifier(), new_id, ids[row['hobby_id']], row['local_date'], row['kind'],
                                row['text'], row['post'], row['level'], row['spend'], row['details'],
                                row['created_at']))
