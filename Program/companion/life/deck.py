"""The Life deck and random tables: small moments in the companion's days (Feature Hit List #33 and #35).

Her days pick up small surprises: a changed habit, an old joke coming back, a favor for a neighbor, a late bus.
Each day of hers, the seeded dice (companion/life/chance.py, from Prospero's Study) decide whether something
small happens and, if so, which card it is. The cards come from two places that share one picker: the Life deck
(world/data/life_deck.json), and Study's d100 random tables reworded for everyday life
(world/data/random_tables.json), whose rows join the deck as extra cards weighted by their dice ranges. This adapts
the idea of Study's Inspiration decks, not its code: there is no deck editor, versions or packs.

The drama level (Settings > Life) sets how often a moment turns up and which cards can: quiet keeps to the
gentle ones. A card that needs someone from the circle or a job is left out for a companion without one, a card
drawn in the last `repeat_days` steps aside so the weeks don't repeat, and a card that could give away a secret
the companion keeps is never drawn. No model decides anything: the chat context tells the companion what happened
("You found a forgotten twenty in an old coat pocket"), the model only puts it in their words, and a card with a
`share` line may become a first message (companion/life/openers.py).

A day's draw is written once (`life_moments`), so the last week reads back as it was. Today lists it with its odds
under "Why it went this way" (with Hidden values > odds on), where the user can make it go another way: another
card, or nothing at all. Names are filled in when shown, so renaming someone carries over.
"""
import json
from datetime import date, timedelta
from functools import cache

from companion import secrets
from companion.clock import stamp
from companion.database import many, optional
from companion.errors import require
from companion.life import chance, circle, storylines
from companion.memory import pairs
from companion.world import catalog

# Off in tests unless a test turns it on: a seeded moment would add context lines and first messages.
ACTIVE = True
WEEK = 7
# How many times a draw that would give a secret away is tried again before the day stays quiet.
TRIES = 4


@cache
def deck() -> dict:
    return json.loads((catalog.DATA / 'life_deck.json').read_text(encoding='utf-8'))


@cache
def tables() -> dict:
    return json.loads((catalog.DATA / 'random_tables.json').read_text(encoding='utf-8'))


def table_cards() -> list[dict]:
    """The random tables' rows as cards: each weighted by its share of the top table's roll and of its own table's,
    so the two together take `tables_weight` next to the deck."""
    found, data = [], tables()
    top = data['tables'][data['start']]['rows']
    top_width = sum(row['high'] - row['low'] + 1 for row in top)
    for parent in top:
        if parent['kind'] != 'event' or not parent.get('child'):
            continue
        child = data['tables'][parent['child']]
        rows = [row for row in child['rows'] if row['kind'] == 'event']
        width = sum(row['high'] - row['low'] + 1 for row in child['rows'])
        for row in rows:
            share = (parent['high'] - parent['low'] + 1) / top_width * (row['high'] - row['low'] + 1) / width
            found.append({'id': row['id'], 'source': child['name'], 'title': row['title'], 'tone': row['tone'],
                          'needs': row.get('needs', []), 'drama': row.get('drama', 0), 'text': row['text'],
                          'told': row['told'], 'share': row.get('share'), 'on': True,
                          'weight': max(1, round(deck()['tables_weight'] * share))})
    return found


@cache
def cards() -> tuple[dict, ...]:
    return tuple([{**card, 'source': 'Life deck'} for card in deck()['cards']] + table_cards())


def card(card_id: str | None) -> dict | None:
    return next((item for item in cards() if item['id'] == card_id), None)


# Drawing -------------------------------------------------------------------------------------------------

def eligible(level: int, has: set[str], recent: set[str]) -> list[dict]:
    return [item for item in cards() if item['on'] and item['drama'] <= level and set(item['needs']) <= has
            and item['id'] not in recent]


def pick(pool: list[dict], draws: chance.Draws) -> dict:
    point = draws.die(sum(item['weight'] for item in pool), 'deck', 'card')
    for item in pool:
        if point <= item['weight']:
            return item
        point -= item['weight']
    raise AssertionError('The deck has no card')


def draw(seed: str, level: int, has: set[str], recent: set[str], forced: bool = False) -> tuple[dict | None, float]:
    """(card or None, its odds) for one day. `forced` skips the roll for whether anything happens (the user asked
    for another card)."""
    draws, chances = chance.Draws(seed), deck()['chance']
    happens = chances[min(level, len(chances) - 1)]
    if not forced and draws.die(100, 'deck', 'moment') > happens:
        return None, round(1 - happens / 100, 3)
    pool = eligible(level, has, recent)
    if not pool:
        return None, 1.0
    found = pick(pool, draws)
    share = found['weight'] / sum(item['weight'] for item in pool)
    return found, round(share if forced else happens / 100 * share, 3)


def friends(connection, timeline_id: str) -> list[dict]:
    return circle.people(connection, timeline_id)


def needs_met(connection, companion) -> set[str]:
    has = set()
    if friends(connection, companion['active_timeline_id']):
        has.add('friend')
    if circle.work_blocks(companion['version']['definition']):
        has.add('work')
    return has


def friend_for(connection, timeline_id: str, seed: str) -> str | None:
    people = friends(connection, timeline_id)
    return people[chance.Draws(seed).die(len(people), 'deck', 'friend') - 1]['id'] if people else None


def recent_cards(connection, timeline_id: str, day: date) -> set[str]:
    since = (day - timedelta(days=deck()['repeat_days'])).isoformat()
    return {row['card_id'] for row in many(connection, 'SELECT card_id FROM life_moments WHERE timeline_id=? AND day>=? '
                                           'AND day<? AND card_id IS NOT NULL', (timeline_id, since, day.isoformat()))}


def kept_quiet(connection, companion, text: str) -> bool:
    """Whether the moment could give away a secret the companion keeps."""
    key = pairs.companion_key(companion['id'])
    return any(key in secret['knowers'] and secrets.hits(secret, text, key) for secret in secrets.active(connection))


def decide(connection, companion, day: date, attempt: int = 0, avoid: frozenset = frozenset()) -> dict:
    """The day's moment: {card_id, friend_id, odds}. `attempt` above 0 is the user asking for another card."""
    timeline_id = companion['active_timeline_id']
    if not ACTIVE:
        return {'card_id': None, 'friend_id': None, 'odds': 1.0}
    level, has = storylines.drama(connection), needs_met(connection, companion)
    recent = recent_cards(connection, timeline_id, day) | set(avoid)
    for tried in range(TRIES):
        seed = f'{timeline_id}:{day.isoformat()}:{attempt}:{tried}'
        found, odds = draw(seed, level, has, recent, forced=attempt > 0)
        if found is None:
            return {'card_id': None, 'friend_id': None, 'odds': odds}
        friend_id = friend_for(connection, timeline_id, seed) if 'friend' in found['needs'] else None
        moment = {'card_id': found['id'], 'friend_id': friend_id, 'odds': odds}
        if not kept_quiet(connection, companion, worded(connection, moment, companion, 'told')):
            return moment
        recent.add(found['id'])
    return {'card_id': None, 'friend_id': None, 'odds': 1.0}


def save(connection, timeline_id: str, day: date, moment: dict, picked_by: str, timestamp: str):
    connection.execute(
        'INSERT INTO life_moments (timeline_id, day, card_id, friend_id, odds, picked_by, created_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(timeline_id, day) DO UPDATE SET card_id=excluded.card_id, '
        'friend_id=excluded.friend_id, odds=excluded.odds, picked_by=excluded.picked_by, attempts=attempts+1',
        (timeline_id, day.isoformat(), moment['card_id'], moment['friend_id'], moment['odds'], picked_by, timestamp))


def began(connection, companion) -> date:
    from companion.life import thoughts
    return thoughts.began(connection, companion)


def catch_up(connection, companion, now) -> int:
    """Draw the moments of the last week that are not drawn yet, oldest first. Returns how many were drawn."""
    timeline_id, today = companion['active_timeline_id'], storylines.local_today(companion, now)
    kept = {row['day'] for row in many(connection, 'SELECT day FROM life_moments WHERE timeline_id=? AND day>=?',
                                       (timeline_id, (today - timedelta(days=WEEK - 1)).isoformat()))}
    day, written = max(today - timedelta(days=WEEK - 1), began(connection, companion)), 0
    while day <= today:
        if day.isoformat() not in kept:
            save(connection, timeline_id, day, decide(connection, companion, day), 'dice', stamp(now))
            written += 1
        day += timedelta(days=1)
    return written


def sync(connection, now) -> int:
    """Catch up every companion with a life, in the world this runs in (a background tick)."""
    from companion.characters import by_id
    written = 0
    for row in many(connection, 'SELECT id FROM companions WHERE active_version_id IS NOT NULL AND '
                    'active_timeline_id IS NOT NULL'):
        if (companion := by_id(connection, row['id'])) is not None:
            written += catch_up(connection, companion, now)
    return written


# Reading ---------------------------------------------------------------------------------------------------

def first_name(name: str) -> str:
    return name.split()[0] if name.split() else name


def worded(connection, moment: dict, companion, field: str) -> str:
    """A card's `text`, `told` or `share` with today's names filled in."""
    found = card(moment['card_id'])
    template = (found or {}).get(field) or ''
    friend = optional(connection, "SELECT name FROM circle_people WHERE id=? AND status='active'",
                      (moment['friend_id'],)) if moment.get('friend_id') else None
    return template.format(first=first_name(companion['version']['definition']['name']),
                           friend=first_name(friend['name']) if friend else 'a friend')


def on_day(connection, companion, day: date) -> dict | None:
    row = optional(connection, 'SELECT * FROM life_moments WHERE timeline_id=? AND day=? AND card_id IS NOT NULL',
                   (companion['active_timeline_id'], day.isoformat()))
    return dict(row) if row and card(row['card_id']) else None


def item_view(connection, companion, row: dict, odds: bool) -> dict:
    found = card(row['card_id'])
    item = {'day': row['day'], 'title': found['title'], 'text': worded(connection, row, companion, 'text'),
            'source': found['source'], 'picked_by': row['picked_by']}
    if odds:
        item['odds'] = row['odds']
    return item


def week(connection, companion, now, odds: bool = False) -> list[dict]:
    """The last week's moments, newest first."""
    since = (storylines.local_today(companion, now) - timedelta(days=WEEK - 1)).isoformat()
    rows = many(connection, 'SELECT * FROM life_moments WHERE timeline_id=? AND day>=? AND card_id IS NOT NULL '
                'ORDER BY day DESC', (companion['active_timeline_id'], since))
    return [item_view(connection, companion, dict(row), odds) for row in rows if card(row['card_id'])]


def context_lines(connection, companion, now) -> list[tuple[str, str]]:
    """Today's moment for the chat context, told to the companion as "you"."""
    found = on_day(connection, companion, storylines.local_today(companion, now))
    return [(f"moment:{found['day']}", f"- {worded(connection, found, companion, 'told')}")] if found else []


def fresh(connection, companion, now) -> list[dict]:
    """Today's moment when it has a first message to send about it: {key, told, share}."""
    found = on_day(connection, companion, storylines.local_today(companion, now))
    if not found or not card(found['card_id']).get('share'):
        return []
    return [{'key': f"moment:{found['day']}:{found['card_id']}", 'told': worded(connection, found, companion, 'told'),
             'share': worded(connection, found, companion, 'share')}]


def view(database) -> list[dict]:
    """For Today: the week's moments, drawn first where due, with their odds when Hidden values > odds is on."""
    from companion.characters import require_current
    from companion.database import settings
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        catch_up(connection, companion, now)
        return week(connection, companion, now, odds=bool(settings(connection)['show_odds']))


# Making it go another way -----------------------------------------------------------------------------------

def change(connection, companion, day: date, way: str, now) -> list[dict]:
    """The user makes a day's moment go another way: `another` card, or `nothing` at all. Returns the week."""
    timeline_id = companion['active_timeline_id']
    row = optional(connection, 'SELECT * FROM life_moments WHERE timeline_id=? AND day=?',
                   (timeline_id, day.isoformat()))
    require(row is not None, 'Nothing was drawn for that day yet.', 404)
    if way == 'nothing':
        moment = {'card_id': None, 'friend_id': None, 'odds': row['odds']}
    else:
        moment = decide(connection, companion, day, attempt=row['attempts'] + 1,
                        avoid=frozenset({row['card_id']} - {None}))
    save(connection, timeline_id, day, moment, 'user', stamp(now))
    from companion.database import settings
    return week(connection, companion, now, odds=bool(settings(connection)['show_odds']))
