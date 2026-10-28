"""Reading, watching and listening (Hit List #26): the companion is always in the middle of something.

Each companion has one current book (and how far along they are), one show they are partway through and one song on
repeat, picked by the app from banks of real, era-correct titles for our world (titles, authors and artists only:
never lyrics or excerpts) or of invented in-world titles for made-up worlds (Camelot, Oz, Grandport), in
companion/world/data/media/*.json. A made-up world's own titles come first: the city's `media` block, else titles
built from its places, people, festivals and lore (companion/life/media_world.py). Picks lean on their interests and stated likes, their city's country and, for
songs, the years they grew up in. In the past, a "show" is what people followed then: a serial in a magazine, a play,
a picture serial or a radio program.

Nothing asks the user. Items are chained per kind: when one ends the next starts after a seeded gap, all decided
when the item is first needed, with no model call; how long each takes follows how keen a reader or viewer they are.
A finished book or show leaves a seeded verdict they bring up, and something they loved they sometimes recommend to
the user (a first text, companion/life/openers.py). Something the user recommended (companion/life/recommendations.py)
goes ahead of their own: while they are on it, their own book or show waits and picks up again after.

The Realism tab's slider (life_settings.media_realism: 0 off, 1 light, 2 true to life, 3 dramatic) scales it: off,
nothing is tracked; light, they finish everything and mostly like it; true to life, mixed verdicts and now and then
something put down; dramatic, strong opinions, binges and more given up on. Books, a streaming subscription, theatre
tickets and magazines go through money.household (`purchases`).

The user can set what they are on now on the Character page (Set by you); the days ahead follow.
"""
import json
import math
import re
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

from companion.clock import app_now, parse, stamp, zone
from companion.database import decode, encode, identifier, many, optional
from companion.errors import require
from companion.life import circle, media_world, money
from companion.world import generators, looks, wording

COMPANION = 'companion'
BANKS = Path(__file__).resolve().parents[1] / 'world' / 'data' / 'media'
KINDS = ('book', 'show', 'music')
# Woven into the companion's agenda entries; tests turn it off.
WEAVE = True
RECOMMENDS = True

# Of a made-up world's picks, the share from the city's own block (the rest built from the city) and, for a city
# without one, the share built from the city (the rest from the shared bank).
OWN_SHARE = 0.8
BUILT_SHARE = 0.6
# Banks by era: real titles up to the era's year in our world, invented ones in made-up worlds.
ERA_BANKS = {'modern': 'modern', 'other': 'modern', 'victorian': 'nineteenth', 'steampunk': 'nineteenth',
             'frontier': 'nineteenth', 'jazz-age': 'jazz-age', 'fantasy': 'tales', 'medieval': 'tales',
             'future': 'future'}
ERA_YEARS = {'modern': 2026, 'other': 2026, 'victorian': 1895, 'steampunk': 1890, 'frontier': 1885, 'jazz-age': 1926}
REGIONS = (('us', ('us', 'usa', 'united states', 'united states of america', 'america')),
           ('uk', ('uk', 'united kingdom', 'england', 'scotland', 'wales', 'britain', 'great britain')),
           ('jp', ('japan',)), ('kr', ('korea', 'south korea')))
ERA_REGIONS = {'frontier': 'us', 'victorian': 'uk', 'steampunk': 'uk', 'jazz-age': 'us'}
# A city set in a year of its own (names.year, as companion/world/naming.py reads it) caps the titles at that year;
# one of era 'other' reads from the bank of its century.
YEAR_BANKS = ('modern', 'jazz-age', 'nineteenth')
# What was running then: a serial, a picture serial, a Broadway show or a radio program from the last few years, not
# one from decades before (a play can be a revival). The window widens until the bank still offers SHOWING_LEAST.
SHOWING_FORMATS = {'serial', 'film-serial', 'broadway', 'radio'}
SHOWING_YEARS = (4, 10, 20, 40)
SHOWING_LEAST = 100

# Their interests and likes, read as the banks' genre tags.
TAG_WORDS = {
    'mystery': ('mystery', 'mysteries', 'detective', 'whodunit', 'puzzle'), 'crime': ('crime', 'true crime', 'heist'),
    'thriller': ('thriller', 'suspense', 'spy'), 'romance': ('romance', 'romantic', 'love stories', 'rom-com'),
    'fantasy': ('fantasy', 'dragons', 'magic', 'tolkien'), 'scifi': ('sci-fi', 'scifi', 'science fiction', 'space'),
    'horror': ('horror', 'scary', 'spooky', 'ghost'), 'history': ('history', 'historical', 'museum'),
    'biography': ('biography', 'biographies'), 'memoir': ('memoir', 'memoirs'),
    # Not plain 'science': 'science fiction' is the scifi tag's, and 'novels' or 'reading' only say they read.
    'science': ('popular science', 'physics', 'biology', 'astronomy', 'chemistry', 'tech'),
    'nature': ('nature', 'hiking', 'birds', 'birdwatching', 'gardening', 'plants', 'animals', 'outdoors', 'wildlife'),
    'travel': ('travel', 'travelling', 'traveling'), 'poetry': ('poetry', 'poems', 'poet'),
    'humor': ('comedy', 'humor', 'humour', 'stand-up', 'jokes'), 'comedy': ('comedy', 'sitcom', 'funny', 'stand-up'),
    'cooking': ('cooking', 'baking', 'food', 'chef', 'recipes'), 'art': ('art', 'painting', 'drawing', 'design'),
    'music': ('music', 'concert', 'band', 'guitar', 'piano'), 'sports': ('sports', 'football', 'basketball', 'soccer',
                                                                          'baseball', 'running', 'tennis'),
    'philosophy': ('philosophy',), 'literary': ('literature', 'literary', 'classics'),
    'classic': ('classics', 'classic'), 'anime': ('anime', 'manga'), 'kdrama': ('k-drama', 'kdrama', 'korean drama'),
    'documentary': ('documentary', 'documentaries'), 'reality': ('reality tv', 'reality shows'),
    'pop': ('pop',), 'rock': ('rock',), 'indie': ('indie',), 'hiphop': ('hip hop', 'hip-hop', 'rap'),
    'rnb': ('r&b', 'rnb'), 'soul': ('soul', 'motown'), 'country': ('country music',), 'folk': ('folk',),
    'jazz': ('jazz',), 'blues': ('blues',), 'classical': ('classical', 'opera', 'orchestra'),
    'electronic': ('electronic', 'techno', 'edm', 'house music'), 'dance': ('dancing', 'dance', 'clubbing'),
    'metal': ('metal',), 'punk': ('punk',), 'latin': ('latin', 'salsa', 'reggaeton'), 'kpop': ('k-pop', 'kpop'),
    'jpop': ('j-pop', 'jpop', 'city pop'), 'musical': ('musicals', 'musical theater', 'musical theatre', 'broadway'),
    'adventure': ('adventure', 'adventures'), 'family': ('family',), 'religion': ('faith', 'church', 'religion'),
}
READ_WORDS = ('read', 'reader', 'reading', 'books', 'bookworm', 'novel', 'novels', 'literature', 'library', 'poetry',
              'writer', 'writing')
WATCH_WORDS = ('tv', 'television', 'shows', 'series', 'binge', 'netflix', 'anime', 'movies', 'films', 'theater',
               'theatre', 'drama')
NOT_READER = re.compile(r"\b(?:doesn'?t|does not|never|hates?) read", re.I)

# Days each takes, before how keen they are: a book's pages, at pages a day by how keen a reader they are; a show by
# its kind; a song on repeat.
PAGES = (160, 620)
PAGES_A_DAY = (10, 20, 35, 60)
SHOW_DAYS = {'series': (8, 30), 'serial': (30, 110), 'film-serial': (50, 100), 'radio': (40, 120),
             'play': (10, 21), 'broadway': (10, 21), 'cycle': (6, 18)}
WATCH_PACE = (1.5, 1.2, 0.9, 0.65)
SONG_DAYS = (5, 24)
GAPS = {'book': (0, 2), 'show': (0, 2), 'music': (0, 0)}
LIMITS = {'book': (2, 75), 'show': (2, 130), 'music': (3, 30)}
FIRST_ALONG = (0.1, 0.65)
# By the slider (off, light, true to life, dramatic): what they thought, how often something they are not into is put
# down partway, how often a show is binged in a third of the time, and how often something loved is recommended to
# the user.
VERDICTS = ('loved it', 'liked it', 'thought it was fine', 'was not really into it')
VERDICT_ODDS = ((0, 0, 0, 0), (4, 5, 1, 0), (3, 4, 2, 1), (4, 2, 1, 3))
DROP = (0.0, 0.0, 0.45, 0.7)
BINGE = (0.0, 0.0, 0.08, 0.2)
RECOMMEND = (0.0, 0.3, 0.4, 0.55)
RECENT_DAYS = 90
# A walk or a workout names the song on repeat only some days.
SONG_SHARE = 0.4
CONTEXT_FINISHED = 14
HOME_FORMATS = {'series', 'serial', 'radio'}
AT_HOME = {'reading', 'slow', 'nap', 'sick-day', 'chores', 'home-cooking', None}
# Share of the price of a month's take-home: a book, a month of streaming, a magazine and a theatre ticket.
COSTS = {'book': 0.004, 'series': 0.0035, 'serial': 0.0015, 'play': 0.006, 'broadway': 0.01, 'film-serial': 0.002,
         'cycle': 0.0005, 'radio': 0.0}
LIBRARY_SHARE = 0.3

# How far along, in four steps, by format.
PROGRESS = {
    'book': ('just started', 'a few chapters in', 'about halfway', 'nearly done'),
    'series': ('just started', 'a few episodes in', 'halfway through the season', 'on the last few episodes'),
    'serial': ('just started following it', 'a few instalments in', 'halfway through', 'nearly at the end'),
    'film-serial': ('just started following it', 'a few chapters in', 'halfway through', 'nearly at the end'),
    'cycle': ('just started', 'a few nights in', 'about halfway', 'nearly at the end'),
}


# --- Banks ---

@lru_cache(maxsize=8)
def bank(bank_id: str) -> dict:
    """One bank: {id, label, real, book, show, music}, each item {title, by, year, tags, format}."""
    raw = json.loads((BANKS / f'{bank_id}.json').read_text(encoding='utf-8'))
    found = {'id': raw['id'], 'label': raw['label'], 'real': raw['real']}
    for kind in KINDS:
        found[kind] = tuple({'title': title, 'by': by, 'year': year, 'tags': frozenset(tags.split()),
                             'format': format_of(kind, tags.split())} for title, by, year, tags in raw[kind])
    return found


def format_of(kind: str, tags) -> str:
    if kind != 'show':
        return kind
    return next((tag for tag in tags if tag in SHOW_DAYS), 'series')


def place_of(data: dict | None) -> dict:
    """Their bank, the year it runs to and the region it leans to, from their city."""
    era = (data or {}).get('era') or 'modern'
    country = ((data or {}).get('country') or 'United States').casefold()
    region = ERA_REGIONS.get(era) or next((key for key, names in REGIONS if country in names or any(
        len(name) > 3 and name in country for name in names)), 'world')
    bank_id, year = ERA_BANKS.get(era, 'modern'), ERA_YEARS.get(era)
    own = ((data or {}).get('names') or {}).get('year')
    if own and bank_id in YEAR_BANKS:
        if era == 'other':
            bank_id = 'nineteenth' if own < 1900 else 'jazz-age' if own < 1930 else 'modern'
        year = min(own, year or own)
    return {'bank': bank_id, 'year': year, 'region': region, 'era': era,
            'world': media_world.mark(data, bank_id, bank(bank_id)['real'])}


def world_titles(me: dict, data: dict | None) -> dict | None:
    """Their city's own titles and those built from it (media_world.titles), or None."""
    return media_world.titles(data, me['bank'], bank(me['bank'])['real'])


def tastes(definition: dict) -> tuple[set, set]:
    """(liked tags, disliked tags) from their interests, themes and stated likes and dislikes."""
    own = definition.get('self_tastes') or {}
    liked = ' '.join([*(definition.get('interests') or ()), *(definition.get('life_themes') or ()),
                      *own.get('likes', ()), definition.get('identity') or '']).casefold()
    disliked = ' '.join(own.get('dislikes', ())).casefold()
    return ({tag for tag, words in TAG_WORDS.items() if any(said(word, liked) for word in words)},
            {tag for tag, words in TAG_WORDS.items() if any(said(word, disliked) for word in words)})


def said(word: str, text: str) -> bool:
    """The word on its own ('pop' is not in 'k-pop')."""
    return bool(re.search(rf'(?<![\w-]){re.escape(word)}(?![\w-])', text))


def keen(definition: dict, seed: str, words, label: str) -> int:
    """0 to 3: how much of a reader (or viewer) they are, from their own words, else seeded."""
    text = ' '.join([definition.get('identity') or '', definition.get('personality') or '',
                     *(definition.get('interests') or ())]).casefold()
    hits = sum(1 for word in words if re.search(rf'\b{re.escape(word)}\b', text))
    if label == 'reader' and NOT_READER.search(text):
        return 0
    base = generators.pick(seed, label, [0, 1, 2, 3], [2, 4, 3, 1])
    return min(3, base + hits)


def profile(seed: str, definition: dict, data: dict | None) -> dict:
    found = place_of(data)
    return {**found, 'reader': keen(definition, seed, READ_WORDS, 'reader'),
            'watcher': keen(definition, seed, WATCH_WORDS, 'watcher'),
            'library': generators.unit(seed, 'library') < LIBRARY_SHARE}


def weight(item: dict, kind: str, me: dict, liked: set, disliked: set, born: int | None) -> float:
    tags, value = item['tags'], 1.0 + 6.0 * len(item['tags'] & liked)
    if tags & disliked:
        value *= 0.15
    if me['region'] in tags:
        value *= 3.0
    elif tags & {'jp', 'kr'} and not tags & liked:  # what they are into wins over where they live
        value *= 0.5
    if me['bank'] == 'modern' and item['year'] >= 2016:
        value *= 2.0
    if kind == 'music' and born and born + 12 <= item['year'] <= born + 28:
        value *= 2.0
    return value


def candidates(me: dict, kind: str, taken: set) -> list[dict]:
    year = me.get('year')
    found = [item for item in bank(me['bank'])[kind]
             if (not year or not item['year'] or item['year'] <= year) and item['title'].casefold() not in taken]
    if not year or me['bank'] == 'modern':
        return found
    for span in SHOWING_YEARS:
        showing = [item for item in found
                   if item['format'] not in SHOWING_FORMATS or not item['year'] or item['year'] > year - span]
        if len(showing) >= SHOWING_LEAST:
            return showing
    return found


def options_for(seed: str, label: str, me: dict, kind: str, taken: set, titles: dict | None) -> list[dict]:
    """What one pick is drawn from: in a made-up world mostly the city's own titles, else ones built from it, else
    the shared bank; a list that has run out gives way to the next."""
    if titles:
        roll = generators.unit(seed, label, 'world')
        own = [item for item in titles['own'].get(kind, ()) if item['title'].casefold() not in taken]
        built = [item for item in titles['built'].get(kind, ()) if item['title'].casefold() not in taken]
        if own and (roll < OWN_SHARE or not built):
            return own
        if built and (titles['own'].get(kind) or roll < BUILT_SHARE):
            return built
    return candidates(me, kind, taken) or candidates(me, kind, set())


def choose(seed: str, label: str, me: dict, kind: str, definition: dict, taken: set,
           titles: dict | None = None) -> dict | None:
    """A pick for one kind: era-correct (or of their own world), not one they have had, leaning to their tastes."""
    options = options_for(seed, label, me, kind, taken, titles)
    liked, disliked = tastes(definition)
    born = (me.get('year') or ERA_YEARS['modern']) - looks.age_of(definition, seed)
    return generators.pick(seed, label, options, [weight(item, kind, me, liked, disliked, born) for item in options])


# --- State ---

def realism(connection) -> int:
    row = optional(connection, 'SELECT media_realism FROM life_settings WHERE id=1')
    return row['media_realism'] if row and row['media_realism'] is not None else 2


def ensure(connection, timeline_id: str, definition: dict, world, today: date | None = None) -> dict:
    """Their media state, seeded the first time it is needed (and placed again when their city's year moved)."""
    state = optional(connection, 'SELECT * FROM media_state WHERE timeline_id=?', (timeline_id,))
    if state:
        return replaced(connection, state, definition, world, today) if today else state
    seed = f'media:{timeline_id}'
    found = profile(seed, definition, circle.city_data(definition, world))
    connection.execute('INSERT INTO media_state (timeline_id, seed, profile, created_at, updated_at) '
                       'VALUES (?, ?, ?, ?, ?)', (timeline_id, seed, encode(found), stamp_now(), stamp_now()))
    return optional(connection, 'SELECT * FROM media_state WHERE timeline_id=?', (timeline_id,))


def replaced(connection, state: dict, definition: dict, world, today: date) -> dict:
    """State saved before the city's own year capped the titles (a 1925 city once ran to 1926), or before a made-up
    world's own titles counted: the bank, year and world are read again, and what they are on today from after that
    year, or from the shared bank of a world that now has its own, is drawn again."""
    data = circle.city_data(definition, world)
    me = decode(state['profile'])
    found = place_of(data) if data else None
    if not found or (found['bank'], found['year'], found['world']) == (me['bank'], me['year'], me.get('world', '')):
        return state
    old, me = me, {**me, **found}
    timeline_id = state['timeline_id']
    connection.execute('UPDATE media_state SET profile=?, updated_at=? WHERE timeline_id=?',
                       (encode(me), stamp_now(), timeline_id))
    rewind(connection, timeline_id, today)
    years = {item['title'].casefold(): item['year'] for kind in KINDS for item in bank(old['bank'])[kind]}
    for item in items(connection, timeline_id):
        late = (years.get(item['title'].casefold()) or 0) > (me['year'] or 9999) or old['bank'] != me['bank'] or \
            old.get('world', '') != me['world']
        if item['status'] == 'current' and item['source'] == 'bank' and late:
            connection.execute('DELETE FROM media_items WHERE id=?', (item['id'],))
    return optional(connection, 'SELECT * FROM media_state WHERE timeline_id=?', (timeline_id,))


def rewind(connection, timeline_id: str, today: date, kinds=KINDS):
    """Back to today: the agenda draws the chains ahead of time, so what it started after today goes and what it
    ended after today is current again, to be drawn afresh (a recommendation came in, or the city's year changed)."""
    iso, marks = today.isoformat(), ','.join('?' * len(kinds))
    connection.execute(f"DELETE FROM media_items WHERE timeline_id=? AND kind IN ({marks}) AND started_on>? "
                       "AND status!='replaced'", (timeline_id, *kinds, iso))
    connection.execute(f"UPDATE media_items SET status='current' WHERE timeline_id=? AND kind IN ({marks}) AND "
                       "status='done' AND started_on<=? AND ends_on>?", (timeline_id, *kinds, iso, iso))


def rewind_at(connection, timeline_id: str, timestamp: str):
    """`rewind` to the companion's own date at an instant."""
    row = optional(connection, 'SELECT v.timezone FROM timelines t JOIN companions c ON c.id=t.companion_id '
                   'JOIN character_versions v ON v.id=c.active_version_id WHERE t.id=?', (timeline_id,))
    rewind(connection, timeline_id, parse(timestamp).astimezone(zone(row['timezone'] if row else 'UTC')).date())


def stamp_now() -> str:
    return stamp(app_now())


def items(connection, timeline_id: str, kind: str | None = None) -> list[dict]:
    if kind:
        return many(connection, 'SELECT * FROM media_items WHERE timeline_id=? AND kind=? ORDER BY started_on, seq',
                    (timeline_id, kind))
    return many(connection, 'SELECT * FROM media_items WHERE timeline_id=? ORDER BY started_on, seq', (timeline_id,))


def duration(seed: str, item: dict, me: dict, level: int) -> int:
    """Days it takes, from its kind and how keen they are; a binge takes a third of the time."""
    kind, low_high = item['kind'], LIMITS[item['kind']]
    if kind == 'book':
        pages = PAGES[0] + generators.unit(seed, 'pages') * (PAGES[1] - PAGES[0])
        days = math.ceil(pages / PAGES_A_DAY[me['reader']])
    elif kind == 'show':
        low, high = SHOW_DAYS.get(item['format'], SHOW_DAYS['series'])
        days = round((low + generators.unit(seed, 'days') * (high - low)) * WATCH_PACE[me['watcher']])
        if item['format'] == 'series' and generators.unit(seed, 'binge') < BINGE[level]:
            days = max(2, days // 3)
    else:
        days = round(SONG_DAYS[0] + generators.unit(seed, 'days') * (SONG_DAYS[1] - SONG_DAYS[0]))
    return max(low_high[0], min(low_high[1], days))


def verdict(seed: str, item: dict, level: int, definition: dict) -> str:
    """What they thought, seeded; something that fits their tastes leans warmer. Songs have none."""
    if item['kind'] == 'music':
        return ''
    liked, disliked = tastes(definition)
    tags = set(item.get('tags') or ())
    odds = list(VERDICT_ODDS[max(level, 1)])
    if tags & liked:
        odds[0], odds[1] = odds[0] + 2, odds[1] + 1
    if tags & disliked and odds[3]:
        odds[3] += 2
    return generators.pick(seed, 'verdict', list(VERDICTS), odds)


def plan(seed: str, item: dict, start: date, me: dict, level: int, definition: dict) -> dict:
    """Its days, how it ends and the verdict, all decided when it starts."""
    days = duration(seed, item, me, level)
    thought = verdict(seed, item, level, definition)
    outcome = 'finish'
    if thought == VERDICTS[3] and generators.unit(seed, 'drop') < DROP[level]:
        outcome = 'drop'
        days = max(1, round(days * (0.25 + 0.35 * generators.unit(seed, 'drop-at'))))
    return {'ends_on': (start + timedelta(days=days)).isoformat(), 'outcome': outcome, 'verdict': thought}


def insert(connection, timeline_id: str, kind: str, item: dict, source: str, start: date, planned: dict, seq: int):
    connection.execute(
        'INSERT INTO media_items (id, timeline_id, kind, seq, title, creator, format, tags, source, started_on, ends_on, '
        "outcome, verdict, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'current', ?)",
        (identifier(), timeline_id, kind, seq, item['title'], item.get('by') or '', item.get('format') or kind,
         ' '.join(sorted(item.get('tags') or ())), source, start.isoformat(), planned['ends_on'], planned['outcome'],
         planned['verdict'], stamp_now()))


def advance(connection, timeline_id: str, definition: dict, world, through: date,
            today: date | None = None) -> list[dict]:
    """Every kind's chain up to a local date: what ended is done and the next has started. Returns the items.
    `today` (the companion's own date now, when known) lets a state saved before the city's year counted be redrawn."""
    state = ensure(connection, timeline_id, definition, world, today)
    level = realism(connection)
    if level == 0:
        return []
    me = decode(state['profile'])
    titles = world_titles(me, circle.city_data(definition, world))
    for kind in KINDS:
        advance_kind(connection, timeline_id, state['seed'], me, kind, definition, through, level, titles)
    return items(connection, timeline_id)


def advance_kind(connection, timeline_id, seed, me, kind, definition, through: date, level: int, titles=None):
    chain = items(connection, timeline_id, kind)
    if not chain:
        first = choose(seed, f'{kind}:0', me, kind, definition, set(), titles)
        if not first:
            return
        first = {**first, 'kind': kind}
        planned = plan(f'{seed}:{kind}:0', first, through, me, level, definition)
        days = (date.fromisoformat(planned['ends_on']) - through).days
        along = FIRST_ALONG[0] + generators.unit(seed, kind, 'along') * (FIRST_ALONG[1] - FIRST_ALONG[0])
        start = through - timedelta(days=int(days * along))
        planned['ends_on'] = (start + timedelta(days=days)).isoformat()
        insert(connection, timeline_id, kind, first, 'bank', start, planned, 0)
        chain = items(connection, timeline_id, kind)
    for _step in range(200):
        last = chain[-1]
        if last['status'] == 'current' and not settle(connection, last, through):
            return
        start = date.fromisoformat(last['ends_on']) + timedelta(
            days=round(generators.unit(seed, kind, last['seq'], 'gap') * (GAPS[kind][1] - GAPS[kind][0])) + GAPS[kind][0])
        if start > through:
            return
        taken = {row['title'].casefold() for row in chain}
        label = f"{kind}:{last['seq'] + 1}"
        found = choose(seed, label, me, kind, definition, taken, titles)
        if not found:
            return
        found = {**found, 'kind': kind}
        insert(connection, timeline_id, kind, found, 'bank', start, plan(f'{seed}:{label}', found, start, me, level,
                                                                          definition), last['seq'] + 1)
        chain = items(connection, timeline_id, kind)


def settle(connection, item: dict, through: date) -> bool:
    """Whether a current item has ended by this date, once days spent on the user's recommendations push it back;
    an ended one is marked done."""
    held = held_days(connection, item)
    if held > item['held']:
        ends = date.fromisoformat(item['ends_on']) + timedelta(days=held - item['held'])
        connection.execute('UPDATE media_items SET ends_on=?, held=? WHERE id=?', (ends.isoformat(), held, item['id']))
        item.update(ends_on=ends.isoformat(), held=held)
    if date.fromisoformat(item['ends_on']) > through:
        return False
    connection.execute("UPDATE media_items SET status='done' WHERE id=?", (item['id'],))
    item['status'] = 'done'
    return True


def held_days(connection, item: dict) -> int:
    """Days their own book or show waited while they were on something the user recommended (one a session)."""
    row = optional(connection, "SELECT COUNT(DISTINCT local_date) AS days FROM life_agenda WHERE timeline_id=? "
                   "AND subject='companion' AND json_extract(entry, '$.recommendation.kind')=? "
                   'AND local_date>=? AND local_date<?',
                   (item['timeline_id'], item['kind'], item['started_on'], item['ends_on']))
    return row['days'] if row else 0


# --- Words ---

def quarter(item: dict, day: date) -> float:
    start, end = date.fromisoformat(item['started_on']), date.fromisoformat(item['ends_on'])
    total = max((end - start).days, 1)
    return min(max((day - start).days / total, 0.0), 0.99)


def progress_words(item: dict, day: date) -> str:
    steps = PROGRESS.get(item['format'], PROGRESS['book'])
    share = quarter(item, day)
    return steps[0 if share < 0.15 else 1 if share < 0.4 else 2 if share < 0.68 else 3]


def recorded(bank_id: str) -> bool:
    """Whether songs come on a record or a stream there (else they are sung and hummed)."""
    return bank_id in ('modern', 'jazz-age', 'future')


def by_line(item: dict, kind: str) -> str:
    return f" by {item['creator']}" if item.get('creator') and (kind != 'show' or item['format'] != 'series') else ''


NOW_WORDS = {  # (they, you): the Character page says "Reading X", the chat "You are reading X"
    'reading': ('Reading {t}{by}: {p}.', 'You are reading {t}{by} ({p}).'),
    'song': ('On repeat: {t}{by}.', 'Song on repeat: {t}{by}.'),
    'humming': ("Can't stop humming {t}{by}.", "You can't stop humming {t}{by}."),
    'radio': ('Never misses {t} on the radio.', 'You never miss {t} on the radio.'),
    'tickets': ('Has tickets for {t}{by}.', 'You have tickets for {t}{by}.'),
    'saw': ('Saw {t}{by} and is still talking about it.', 'You saw {t}{by} and are still talking about it.'),
    'watching': ('Watching {t}: {p}.', 'You are watching {t} ({p}).'),
    'following': ('Following {t}{by}{where}: {p}.', 'You are following {t}{by}{where} ({p}).'),
}


def now_key(item: dict, day: date, bank_id: str) -> str:
    fmt = item['format']
    if item['kind'] == 'book':
        return 'reading'
    if item['kind'] == 'music':
        return 'song' if recorded(bank_id) else 'humming'
    if fmt in ('play', 'broadway'):
        return 'tickets' if quarter(item, day) < 0.5 else 'saw'
    return {'radio': 'radio', 'series': 'watching'}.get(fmt, 'following')


def said_here(text: str, region: str = '') -> str:
    """A line as said where they live: one full stop after a name that ends in one ("Gary Clark Jr."), and American
    words in the United States ("installments", "at the movies")."""
    text = re.sub(r'(?<!\.)\.\.(?!\.)', '.', text)
    return wording.americanize(text) if region == 'us' else text


def now_text(item: dict, day: date, bank_id: str, person: str = 'they', region: str = '') -> str:
    """'Reading Middlemarch by George Eliot: about halfway.' (Character page) or, for the chat, 'You are reading
    Middlemarch by George Eliot (about halfway).'"""
    words = NOW_WORDS[now_key(item, day, bank_id)][person == 'you']
    where = ' at the pictures' if item['format'] == 'film-serial' else ' told at the inn' \
        if item['format'] == 'cycle' else ''
    return said_here(words.format(t=item['title'], by=by_line(item, item['kind']), p=progress_words(item, day),
                                  where=where), region)


def ended_verb(item: dict) -> str:
    """What ending it is: a play is seen, a season of a series finished, anything else finished."""
    return 'saw' if item['format'] in ('play', 'broadway') else 'finished a season of' \
        if item['format'] == 'series' else 'finished'


def ended_text(item: dict, person: str = 'they', region: str = '') -> str:
    """'Finished Middlemarch: loved it.', 'Saw Rose-Marie: loved it.' / 'Gave up on X partway through.'"""
    if item['outcome'] == 'drop':
        return said_here(f"Gave up on {item['title']} partway through.", region)
    if item['kind'] == 'music':
        return said_here(f"Moved on from {item['title']}.", region)
    thought, verb = item['verdict'], ended_verb(item)
    if person == 'you':
        return said_here(f"You {verb} {item['title']}{by_line(item, item['kind'])}: you {thought}.", region)
    return said_here(f"{verb[:1].upper()}{verb[1:]} {item['title']}{by_line(item, item['kind'])}: {thought}.", region)


# --- Agenda ---

def touch(connection, timeline_id: str, subject: str, entry: dict | None, local_date: str, definition: dict,
          world, today: date | None = None) -> dict | None:
    """The companion's agenda entry with what they are reading, watching or playing woven in, once a day."""
    if subject != COMPANION or not entry or entry.get('media') or not WEAVE or realism(connection) == 0:
        return entry
    day = date.fromisoformat(local_date)
    found = advance(connection, timeline_id, definition, world, day, today)
    if not found or woven_on(connection, timeline_id, day):
        return entry
    state = optional(connection, 'SELECT * FROM media_state WHERE timeline_id=?', (timeline_id,))
    me = decode(state['profile'])
    sentence, item = moment(found, entry.get('activity'), day, definition['name'], me['bank'])
    if not sentence:
        return entry
    sentence = said_here(sentence, me.get('region', ''))
    return {**entry, 'summary': f"{entry['summary'].rstrip()} {sentence}",
            'media': {'id': item['id'], 'kind': item['kind'], 'sentence': sentence}}


def moment(found: list[dict], activity, day: date, name: str, bank_id: str) -> tuple[str, dict | None]:
    """The sentence for this slot: something ending today at home, else a little more of what fits the slot."""
    iso = day.isoformat()
    if activity in AT_HOME:
        for item in found:
            if item['ends_on'] == iso and item['kind'] != 'music':
                return ended_sentence(item, name), item
    on = {item['kind']: item for item in found if item['started_on'] <= iso < item['ends_on']}
    book, show, song = on.get('book'), on.get('show'), on.get('music')
    if activity in ('reading', 'coffee') and book:
        return f"{name} read more of {book['title']}.", book
    if activity in ('slow', 'sick-day', 'nap') and show and show['format'] in HOME_FORMATS:
        verb = {'series': 'watched another episode of', 'serial': 'read the latest part of',
                'radio': 'listened to'}[show['format']]
        return f"{name} {verb} {show['title']}.", show
    if activity in ('walk', 'workout', 'commute') and song and generators.unit(song['id'], iso) < SONG_SHARE:
        played = 'had {title} on repeat the whole time' if recorded(bank_id) else 'kept humming {title}'
        return f"{name} {played.format(title=song['title'])}.", song
    return '', None


def ended_sentence(item: dict, name: str) -> str:
    if item['outcome'] == 'drop':
        return f"{name} gave up on {item['title']} partway through."
    verb = 'finished' if item['kind'] == 'book' or item['format'] in HOME_FORMATS - {'series'} else \
        'saw the last of' if item['format'] in ('film-serial', 'cycle') else ended_verb(item)
    return f"{name} {verb} {item['title']} and {item['verdict']}."


def woven_on(connection, timeline_id: str, day: date) -> bool:
    return bool(optional(connection, "SELECT id FROM life_agenda WHERE timeline_id=? AND subject='companion' AND "
                         "local_date=? AND json_extract(entry, '$.media') IS NOT NULL", (timeline_id, day.isoformat())))


# --- Chat ---

def context_lines(connection, timeline_id: str, definition: dict, world, now, timezone: str) -> list[tuple[str, str]]:
    """(identity, line) pairs for the chat's media section: what they are on now and what they finished lately."""
    state = optional(connection, 'SELECT * FROM media_state WHERE timeline_id=?', (timeline_id,))
    if not state or realism(connection) == 0:
        return []
    today = now.astimezone(zone(timezone)).date()
    found = items(connection, timeline_id)  # read only: the agenda and the panel move the chains on
    me = decode(state['profile'])
    region = me.get('region', '')
    lines = []
    for item in current(found, today):
        lines.append((f"media:{item['id']}:{today.isoformat()}",
                      f"- {now_text(item, today, me['bank'], 'you', region)}"))
    for item in finished(found, today, CONTEXT_FINISHED)[:2]:
        when = 'yesterday' if item['ends_on'] == (today - timedelta(days=1)).isoformat() else \
            f"on {date.fromisoformat(item['ends_on']):%B} {date.fromisoformat(item['ends_on']).day}"
        lines.append((f"media:{item['id']}:ended", f'- {ended_text(item, "you", region)[:-1]} ({when}).'))
    return lines


def current(found: list[dict], day: date) -> list[dict]:
    iso = day.isoformat()
    on = [item for item in found if item['started_on'] <= iso < item['ends_on'] and item['status'] != 'replaced']
    return sorted(on, key=lambda item: KINDS.index(item['kind']))


def finished(found: list[dict], day: date, within: int) -> list[dict]:
    """Ended (finished or put down) within the last days, songs aside, newest first."""
    since = (day - timedelta(days=within)).isoformat()
    ended = [item for item in found if since <= item['ends_on'] <= day.isoformat() and item['kind'] != 'music'
             and item['status'] != 'replaced']
    return sorted(ended, key=lambda item: item['ends_on'], reverse=True)


# --- Money ---

def purchases(connection, timeline_id: str, start: date, end: date, definition: dict) -> list[dict]:
    """Books bought, a month of streaming, magazines and tickets this pay period: {text, date, spend, cost, for}."""
    state = optional(connection, 'SELECT * FROM media_state WHERE timeline_id=?', (timeline_id,))
    found = money.profile(definition)
    if not state or not found or realism(connection) == 0:
        return []
    me, month = decode(state['profile']), money.monthly_share(found)
    bought, streaming = [], False
    for item in items(connection, timeline_id):
        if item['kind'] == 'music' or item['status'] == 'replaced':
            continue
        overlaps = item['started_on'] <= end.isoformat() and item['ends_on'] >= start.isoformat()
        if item['format'] == 'series' and me['bank'] == 'modern' and overlaps:
            streaming = True
            continue
        if not start.isoformat() <= item['started_on'] <= end.isoformat():
            continue
        if item['kind'] == 'book' and me.get('library'):
            continue
        share = COSTS.get(item['format'], 0)
        if share:
            bought.append({'text': said_here(bought_text(item), me.get('region', '')), 'date': item['started_on'], 'spend': '',
                           'cost': round(share * month, 2), 'for': 'media'})
    if streaming:
        bought.append({'text': 'paid for a month of streaming', 'date': start.isoformat(), 'spend': '',
                       'cost': round(COSTS['series'] * month, 2), 'for': 'media'})
    return bought


def bought_text(item: dict) -> str:
    return {'book': f"bought a copy of {item['title']}", 'serial': f"bought the magazine with {item['title']}",
            'play': f"bought tickets for {item['title']}", 'broadway': f"bought tickets for {item['title']}",
            'film-serial': f"went to the pictures for {item['title']}",
            'cycle': f"left a coin for the teller of {item['title']}"}.get(item['format'], f"paid for {item['title']}")


# --- Telling the user ---

def recommend_due(connection, companion: dict, now) -> list:
    """Now and then, a first text recommending something they just finished and loved (companion/life/openers.py)."""
    from companion.life.openers import Trigger
    version = companion['version']
    timeline_id = companion['active_timeline_id']
    local = now.astimezone(zone(version['timezone']))
    level = realism(connection)
    if not RECOMMENDS or level == 0 or not 10 <= local.hour < 21:
        return []
    state = optional(connection, 'SELECT * FROM media_state WHERE timeline_id=?', (timeline_id,))
    if not state:
        return []
    today = local.date()
    for item in finished(items(connection, timeline_id), today, 1):
        if item['verdict'] != VERDICTS[0] or item['source'] != 'bank' or \
                generators.unit(state['seed'], 'recommend', item['id']) >= RECOMMEND[level]:
            continue
        verb = 'read' if item['kind'] == 'book' else 'watch' if item['format'] in HOME_FORMATS else 'see'
        ended, region = ended_verb(item), decode(state['profile']).get('region', '')
        reason = said_here(f"You just {ended} {item['title']}{by_line(item, item['kind'])} and loved it. Recommend it "
                           'to the user in your own words: say what it did for you, not what happens in it. Never quote '
                           'from it, and do not describe its plot or people.', region)
        template = said_here(f"Just {ended} {item['title']} and I loved it. You should {verb} it.", region)
        return [Trigger(f"media-rec:{item['id']}", 'media_recommendation', reason, template, (item['id'],))]
    return []


# --- View and edits ---

def view(connection, timeline_id: str, definition: dict, world, now, timezone: str, show_numbers: bool = False) -> dict:
    """The Character page's panel: what they are on now in words, what ended lately, and what is set by the user."""
    level = realism(connection)
    today = now.astimezone(zone(timezone)).date()
    if level == 0:
        return {'off': True, 'today': today.isoformat(), 'now': [], 'lately': [], 'realism': 0, 'real': True}
    found = advance(connection, timeline_id, definition, world, today, today)
    forget_stale(connection, timeline_id, now)
    state = optional(connection, 'SELECT * FROM media_state WHERE timeline_id=?', (timeline_id,))
    me = decode(state['profile'])
    region, shown = me.get('region', ''), current(found, today)
    on, ended = recommended(connection, timeline_id, today, timezone)
    own = [{'id': item['id'], 'kind': item['kind'], 'title': item['title'], 'by': item['creator'],
            'format': item['format'], 'text': now_text(item, today, me['bank'], region=region),
            'set_by_you': item['source'] == 'user', 'started_on': item['started_on']} for item in shown]
    mine = {item['kind']: item['title'] for item in own}
    lately = [{'id': item['id'], 'kind': item['kind'], 'title': item['title'], 'ended_on': item['ends_on'],
               'text': ended_text(item, region=region)} for item in finished(found, today, RECENT_DAYS)]
    result = {'off': False, 'today': today.isoformat(), 'realism': level, 'real': bank(me['bank'])['real'],
              'bank': me['bank'],
              'now': sorted([*(item for item in own if item['kind'] not in on),
                             *({**row, 'waiting': mine.get(kind)} for kind, row in on.items())],
                            key=lambda item: KINDS.index(item['kind'])),
              'lately': sorted([*lately, *ended], key=lambda item: item['ended_on'], reverse=True)[:20]}
    if show_numbers:
        result['numbers'] = {'reader': me['reader'], 'watcher': me['watcher'], 'library': me['library'],
                             'items': {item['id']: {'along': round(quarter(item, today) * 100),
                                                    'days_left': (date.fromisoformat(item['ends_on']) - today).days,
                                                    'ends': 'put down' if item['outcome'] == 'drop' else 'finish'}
                                       for item in shown},
                             'drop': round(DROP[level] * 100), 'recommend': round(RECOMMEND[level] * 100)}
    return result


def recommended(connection, timeline_id: str, today: date, timezone: str) -> tuple[dict, list]:
    """A book, show or song the user recommended (companion/life/recommendations.py) as the panel shows it: the one
    they are on now goes ahead of their own pick ({kind: row}), and one they finished joins Lately with its verdict."""
    from companion.life import recommendations
    on, ended, since = {}, [], (today - timedelta(days=RECENT_DAYS)).isoformat()
    for rec in recommendations.progress(connection, timeline_id):
        if rec['kind'] not in KINDS:
            continue
        fmt = 'series' if rec['kind'] == 'show' else rec['kind']
        if rec['state'] == 'started':
            row = optional(connection, 'SELECT sessions FROM recommendations WHERE id=?', (rec['id'],))
            share = rec['sessions_done'] / max(row['sessions'] if row else 1, 1)
            steps = PROGRESS.get(fmt, PROGRESS['book'])
            words = NOW_WORDS[{'book': 'reading', 'show': 'watching', 'music': 'song'}[rec['kind']]][0]
            on[rec['kind']] = {'id': rec['id'], 'kind': rec['kind'], 'title': rec['title'], 'by': '', 'format': fmt,
                               'text': words.format(t=rec['title'], by='', where='',
                                                    p=steps[1 if share < 0.4 else 2 if share < 0.68 else 3]),
                               'set_by_you': False, 'recommended': True, 'started_on': rec['created_at'][:10]}
        elif rec['state'] == 'finished':
            day = parse(rec['finished_at']).astimezone(zone(timezone)).date().isoformat()
            verb = 'Listened to' if rec['kind'] == 'music' else 'Finished'
            if day >= since:
                ended.append({'id': rec['id'], 'kind': rec['kind'], 'title': rec['title'], 'ended_on': day,
                              'text': f"{verb} {rec['title']}, which you recommended: {rec['verdict']}."})
    return on, ended


def forget_stale(connection, timeline_id: str, now):
    """Upcoming days that mention something no longer on their list (drawn again) are composed again."""
    removed = connection.execute(
        "DELETE FROM life_agenda WHERE timeline_id=? AND subject='companion' AND status='upcoming' AND "
        "json_extract(entry, '$.media.id') IS NOT NULL AND json_extract(entry, '$.media.id') NOT IN "
        '(SELECT id FROM media_items WHERE timeline_id=?)', (timeline_id, timeline_id)).rowcount
    if removed:
        connection.execute('UPDATE agenda_cursors SET through=MIN(through, ?) WHERE timeline_id=? AND subject=?',
                           (stamp(now), timeline_id, COMPANION))


def change(connection, timeline_id: str, body: dict, definition: dict, world, now, timezone: str):
    """The user sets what they are on now for one kind (or `reset` it to the app's own pick); the days ahead follow."""
    kind = body['kind']
    require(kind in KINDS, 'Pick a book, a show or a song.', 422)
    level = realism(connection)
    require(level > 0, 'Reading, watching and listening is off in Settings > Realism.', 409)
    today = now.astimezone(zone(timezone)).date()
    advance(connection, timeline_id, definition, world, today, today)
    state = optional(connection, 'SELECT * FROM media_state WHERE timeline_id=?', (timeline_id,))
    me, seed = decode(state['profile']), state['seed']
    chain = items(connection, timeline_id, kind)
    iso = today.isoformat()
    connection.execute("DELETE FROM media_items WHERE timeline_id=? AND kind=? AND started_on>?", (timeline_id, kind, iso))
    # What they were on today ends here, whether or not the agenda has already moved the chain past it.
    connection.execute("UPDATE media_items SET status='replaced', ends_on=? WHERE timeline_id=? AND kind=? AND "
                       'started_on<=? AND ends_on>?', (iso, timeline_id, kind, iso, iso))
    seq = max((row['seq'] for row in chain), default=-1) + 1
    label = f'{kind}:{seq}'
    if body.get('reset'):
        titles = world_titles(me, circle.city_data(definition, world))
        item = choose(seed, label, me, kind, definition, {row['title'].casefold() for row in chain}, titles)
        source = 'bank'
    else:
        title = (body.get('title') or '').strip()
        require(title, 'Give it a title.', 422)
        fmt = 'series' if kind == 'show' else kind
        item = {'title': title, 'by': (body.get('by') or '').strip(), 'tags': frozenset(), 'format': fmt}
        source = 'user'
    item = {**item, 'kind': kind}
    insert(connection, timeline_id, kind, item, source, today, plan(f'{seed}:{label}', item, today, me, level,
                                                                     definition), seq)
    removed = connection.execute("DELETE FROM life_agenda WHERE timeline_id=? AND subject='companion' AND "
                                 "status='upcoming' AND json_extract(entry, '$.media') IS NOT NULL",
                                 (timeline_id,)).rowcount
    if removed:
        connection.execute("UPDATE agenda_cursors SET through=MIN(through, ?) WHERE timeline_id=? AND subject=?",
                           (stamp(now), timeline_id, COMPANION))


# --- Timelines ---

def copy(connection, parent_id: str, new_id: str, cutoff: str):
    """A fork keeps their state and what they had started by the fork; later picks are drawn again."""
    state = optional(connection, 'SELECT * FROM media_state WHERE timeline_id=?', (parent_id,))
    if not state:
        return
    connection.execute('INSERT INTO media_state (timeline_id, seed, profile, created_at, updated_at) '
                       'VALUES (?, ?, ?, ?, ?)', (new_id, state['seed'], state['profile'], state['created_at'], cutoff))
    day = cutoff[:10]
    for row in many(connection, 'SELECT * FROM media_items WHERE timeline_id=? AND started_on<=?', (parent_id, day)):
        status = 'current' if row['ends_on'] > day and row['status'] != 'replaced' else row['status']
        connection.execute(
            'INSERT INTO media_items (id, timeline_id, kind, seq, title, creator, format, tags, source, started_on, '
            'ends_on, outcome, verdict, held, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (identifier(), new_id, row['kind'], row['seq'], row['title'], row['creator'], row['format'], row['tags'],
             row['source'], row['started_on'], row['ends_on'], row['outcome'], row['verdict'], row['held'], status,
             row['created_at']))
