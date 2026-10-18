"""Big days in the circle (Hit List #69, v0.14 Years Go By): weddings, milestone birthdays, retirement parties and
graduations in the companion's circle and town become days they go to, with the user as their plus-one; and a
friendship companion's own wedding is a big day with the user standing up at it.

The app decides, the user overrides ("the world exists outside of User", Vanta 2026-10-08):

- Where big days come from (`SOURCES`, checked once a day): a sibling's engagement storyline (sibling_engaged in
  companion/life/storylines.py) sets a wedding date for next year; friends in their circle get engaged and marry in
  seeded years, more often with the Their love life slider up; a parent, sibling, cousin or old friend turning 30, 40,
  50 ... has a party (companion/life/ages.py); a working relative reaching their seeded retirement age has a send-off;
  a circle member studying graduates in late spring; a townsperson the companion knows well marries
  (companion/world/couples.py); and a friend's own engagement (companion/life/love_life.py) plans their wedding.
  Later features add their own kinds (`KINDS`) and big days (`add`): graduations from life chapters, funerals.
- Whether they ask the user along is the consequence engine's `bigday:invite` (the Guests slider, how close they are,
  family or not, a romance), under Hidden values ("Why it went this way"). Asked or not, they go: a gift bought from
  their own money a week before (the bank's gifts for the kind, priced by their pay, through money.household), an
  outfit from their wardrobe (companion/life/wardrobe.py), and the day itself.
- The invitation is a first text (companion/life/openers.py) naming whose day it is, the day, the time and the place;
  sending it books the day as an outing (companion/life/outings.py, activity 'big-day'), in person with the circle
  there. Long distance, the user's stay with them is planned around it by v0.12's rules (a 'host' visit,
  companion/life/long_distance.py); when no visit can reach them, they go on their own.
- Saying no is fine and remembered: a no in the user's first reply to the invitation, or "Can't make it" on Today,
  and they go on their own with no hard feelings; the chat context keeps it.
- In a modern city the days before and after carry a line of group chat buzz from the bank for them to pass on.
- Afterwards a sibling or a friend is married, a relative retired and a student graduated (their circle row), the
  user keeps a memory of the day, and with pictures in chat on there is a photo (outings.py: safe wording, the usual
  checks). A friend's own wedding makes them married to their partner and, with the user there as their best friend,
  reaches the friendship ladder's last step (companion/life/steps.py "Stood up at their wedding").

No new slider: Guests and Their love life decide. No model decides anything: the model only puts it in words.
"""
import json
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import cache

from companion import consequences
from companion.clock import parse, stamp, zone
from companion.database import decode, encode, identifier, many, optional
from companion.life import ages, circle, money, outings, steps
from companion.life.upkeep import days_ago
from companion.world import catalog, generators

ACTIVE = True
# The invitation as a first text; off in most tests (tests/conftest.py).
FIRST_TEXTS = True
ACTIVITY = 'big-day'
INVITE = 'bigday:invite'
# Found this far ahead; one closer than SOONEST is too late to plan from now.
AHEAD = 42
SOONEST = 3
# The invitation goes out this many days before (seeded), the gift is bought this many days before.
INVITE_BEFORE = (14, 28)
GIFT_BEFORE = 7
INVITE_HOURS = (10, 21)
# No two big days the user is asked to within this many days of each other.
INVITE_GAP = 14
# How long the chat hears about a big day before it (group chat buzz) and after it.
BUZZ_BEFORE, BUZZ_AFTER, TOLD_DAYS = 7, 2, 30
# A friend's chance of marrying in a given year, by the Their love life slider (0 nothing new ... 3 lots going on).
FRIEND_RATE = (0.0, 0.03, 0.06, 0.12)
FRIEND_AGES = (24, 60)
FRIENDS = {'close friend', 'longtime friend', 'old friend from school', 'old classmate', 'friend', 'new friend',
           'roommate from years ago'}
# Whose milestone birthday is a party they go to, and who retires with a send-off.
CLOSE = {'parent', 'sibling', 'cousin', 'aunt', 'uncle', 'grandmother', 'grandfather', *circle.OLD_FRIENDS}
RELATIVES = {'parent', 'sibling', 'cousin', 'aunt', 'uncle'}
RETIRE_AGES = (62, 67)
STUDENTS = {'College student': 22, 'Graduate student': 26}
# A townsperson the companion has met this often is someone whose wedding they'd be asked to.
KNOWS_TOWNSPERSON = 6
STATUSES = ('planned', 'invited', 'declined', 'done', 'called_off')


@dataclass(frozen=True)
class Kind:
    key: str
    title: str  # Today: "Leo's wedding".
    said: str  # The companion: "your brother Leo's wedding".
    at: str
    until: str
    places: tuple[str, ...]  # City place kinds it can be held at.
    gift: str | None  # Gift bank, and what a gift costs in months of their take-home.
    share: float = 0.0
    modern: bool = False  # Only in a modern city (retirement parties, graduations).


KINDS = {
    'wedding': Kind('wedding', "{name}'s wedding", "{who}'s wedding", '15:00', '22:00',
                    ('garden', 'landmark', 'inn', 'park', 'museum', 'temple', 'restaurant'), 'wedding', 0.04),
    'birthday': Kind('birthday', "{name}'s {age} birthday", "{who}'s {age} birthday party", '19:00', '23:00',
                     ('restaurant', 'tavern', 'bar', 'inn'), 'birthday', 0.02),
    'retirement': Kind('retirement', "{name}'s retirement party", "{who}'s retirement party", '18:30', '22:00',
                       ('restaurant', 'tavern', 'inn', 'bar'), 'retirement', 0.02, True),
    'graduation': Kind('graduation', "{name}'s graduation", "{who}'s graduation", '10:00', '14:00',
                       ('landmark', 'museum', 'park', 'garden'), 'graduation', 0.025, True),
    # A friend's own wedding to their partner (companion/life/love_life.py): the user stands up at it.
    # Their own graduation and send-off from work, from their life chapters (companion/life/big_turns.py).
    'own_graduation': Kind('own_graduation', "{companion}'s graduation", 'your graduation', '10:00', '14:00',
                           ('landmark', 'museum', 'park', 'garden'), None, 0.0, True),
    'own_retirement': Kind('own_retirement', "{companion}'s retirement party", 'your retirement party', '18:30',
                           '22:00', ('restaurant', 'tavern', 'inn', 'bar'), None, 0.0, True),
    'own_wedding': Kind('own_wedding', "{companion}'s wedding", 'your wedding to {name}', '15:00', '22:00',
                        ('garden', 'landmark', 'inn', 'park', 'museum', 'temple'), None),
}
GRADUATION_PLACES = ('university', 'college', 'campus', 'school', 'academy', 'institute')
NOT_PARTY = ('station', 'hospital', 'clinic', 'airport', 'prison', 'jail', 'court', 'police', 'parking', 'office')


@cache
def bank() -> dict:
    return json.loads((catalog.DATA / 'big_days.json').read_text(encoding='utf-8'))


def local_today(companion: dict, now: datetime) -> date:
    return now.astimezone(zone(companion['version']['timezone'])).date()


def first(name: str) -> str:
    return name.split()[0] if name.split() else name


def long_date(day: str) -> str:
    found = date.fromisoformat(day)
    return f"{found:%A}, {found.day} {found:%B}"


def saturday_in(year: int, seed: str, months: tuple[int, int] = (4, 9)) -> date:
    """A seeded Saturday in the given months of a year (April to September by default: wedding season)."""
    month = months[0] + int(generators.unit(seed, 'month', year) * (months[1] - months[0] + 1))
    start = date(year, month, 1)
    saturday = start + timedelta(days=(5 - start.weekday()) % 7)
    return saturday + timedelta(weeks=int(generators.unit(seed, 'week', year) * 4) % 4)


def next_birthday(person_id: str, today: date) -> date:
    birthday = circle.birthday(person_id)
    found = ages.birthday_in(today.year, birthday)
    return found if found >= today else ages.birthday_in(today.year + 1, birthday)


def age_of(connection, row: dict, day: date) -> int | None:
    return ages.person_age(connection, 'circle', row['id'], day) or ages.stored_age(decode(row['details']) or {})


# Where big days come from ----------------------------------------------------------------------------------------

def candidate(kind: str, source: str, row: dict | None, day: date, **details) -> dict:
    """A big day found by a source: whose (a circle row, when it is someone in the circle), what and when."""
    person = {'name': row['name'], 'role': row['role'], 'local': (decode(row['details']) or {}).get('local', True),
              'city': (decode(row['details']) or {}).get('city') or ''} if row else {}
    return {'kind': kind, 'source': source, 'person_id': row['id'] if row else None, 'day': day,
            'details': {**person, **details}}


def sibling_weddings(connection, companion: dict, today: date, people: dict, now) -> list[dict]:
    """A sibling's engagement (the sibling_engaged storyline) sets a date for next year once its second beat says so."""
    result = []
    for row in many(connection, "SELECT * FROM storylines WHERE timeline_id=? AND story='sibling_engaged'",
                    (companion['active_timeline_id'],)):
        stages, cast = decode(row['stages']), decode(row['cast_ids'])
        if len(stages) < 2 or stages[1]['on'] > today.isoformat() or not cast or cast[0] not in people:
            continue
        day = saturday_in(date.fromisoformat(stages[1]['on']).year + 1, f"bigday:{row['id']}")
        result.append(candidate('wedding', f"storyline:{row['id']}", people[cast[0]], day))
    return result


def friend_weddings(connection, companion: dict, today: date, people: dict, now) -> list[dict]:
    """Friends in their circle who aren't married get engaged and marry in seeded years, by Their love life."""
    from companion.life import love_life
    rate = FRIEND_RATE[love_life.level(connection)]
    result = []
    for row in people.values():
        details = decode(row['details']) or {}
        if circle.role_kind(row['role']) not in FRIENDS or details.get('married') or details.get('love'):
            continue
        age = age_of(connection, row, today) or 0
        for year in (today.year, today.year + 1):
            seed = f"bigday:friend:{row['id']}"
            if not FRIEND_AGES[0] <= age <= FRIEND_AGES[1] or generators.unit(seed, 'year', year) >= rate:
                continue
            day = saturday_in(year, f'{seed}:{year}')
            engaged = day - timedelta(days=200 + int(generators.unit(seed, 'engaged', year) * 120))
            if engaged <= today:
                result.append(candidate('wedding', f"friend:{row['id']}:{year}", row, day,
                                        engaged_on=engaged.isoformat()))
    return result


def milestone_birthdays(connection, companion: dict, today: date, people: dict, now) -> list[dict]:
    """A parent, sibling, cousin or old friend turning 30, 40, 50 ...: a party on the weekend of it."""
    result = []
    for row in people.values():
        if circle.role_kind(row['role']) not in CLOSE:
            continue
        birthday = next_birthday(row['id'], today)
        age = age_of(connection, row, birthday)
        if ages.milestone(age):
            day = birthday if birthday.weekday() >= 4 else birthday + timedelta(days=5 - birthday.weekday())
            result.append(candidate('birthday', f"birthday:{row['id']}:{birthday.year}", row, day, age=age))
    return result


def working(details: dict) -> bool:
    career = details.get('career') or ''
    return bool(career) and career != 'Retired' and career not in STUDENTS and not details.get('retired_on')


def retirements(connection, companion: dict, today: date, people: dict, now) -> list[dict]:
    """A working relative reaching their seeded retirement age (62 to 67) has a send-off the Friday after it."""
    result = []
    for row in people.values():
        details = decode(row['details']) or {}
        if circle.role_kind(row['role']) not in RELATIVES or not working(details):
            continue
        seed = f"bigday:retire:{row['id']}"
        retire_at = RETIRE_AGES[0] + int(generators.unit(seed, 'age') * (RETIRE_AGES[1] - RETIRE_AGES[0] + 1))
        birthday = next_birthday(row['id'], today)
        if (age_of(connection, row, birthday) or 0) >= retire_at:
            day = birthday + timedelta(days=(4 - birthday.weekday()) % 7 or 7)
            result.append(candidate('retirement', f"retirement:{row['id']}", row, day))
    return result


def graduations(connection, companion: dict, today: date, people: dict, now) -> list[dict]:
    """A circle member studying for long enough graduates on a Saturday in May or June."""
    result = []
    for row in people.values():
        details = decode(row['details']) or {}
        old_enough = STUDENTS.get(details.get('career') or '')
        if not old_enough or details.get('graduated') or (age_of(connection, row, today) or 0) < old_enough:
            continue
        day = saturday_in(today.year, f"bigday:graduate:{row['id']}", (5, 6))
        result.append(candidate('graduation', f"graduation:{row['id']}:{today.year}", row, day))
    return result


def town_weddings(connection, companion: dict, today: date, people: dict, now) -> list[dict]:
    """A townsperson the companion knows well marries (companion/world/couples.py): they're invited."""
    from companion.life import encounters
    from companion.world import couples
    data = outings.city_data(connection, companion['version']['definition'])
    if not data:
        return []
    cast = encounters.town_cast(connection, companion, data)
    result = []
    for key, meetings in encounters.history_for(connection, companion, cast, now).items():
        sheet = encounters.resolve(data, key, cast) if len(meetings) >= KNOWS_TOWNSPERSON else None
        if not sheet or sheet.get('cast'):
            continue
        for event in couples.events(sheet, data, (today, today + timedelta(days=AHEAD))):
            if event['what'] == 'married':
                result.append(candidate('wedding', f"town:{key}:{event['day'].isoformat()}", None, event['day'],
                                        name=sheet['name'], role=sheet.get('role') or 'someone from town',
                                        town=key, local=True, partner=event['partner']['name']))
    return result


def chapters(connection, companion: dict, today: date, people: dict, now) -> list[dict]:
    """Their own graduation or last day at work, from their life chapters (companion/life/big_turns.py)."""
    from companion.life import big_turns
    high = (today + timedelta(days=AHEAD)).isoformat()
    return [candidate(f"own_{item['kind']}", f"chapter:{item['chapter_id']}", None, date.fromisoformat(item['on']),
                      name=companion['version']['definition']['name'], chapter=item['title'])
            for item in big_turns.big_days(connection, companion['active_timeline_id'], today.isoformat(), high)]


# In order; later features add their own.
SOURCES = [sibling_weddings, friend_weddings, milestone_birthdays, retirements, graduations, town_weddings, chapters]
# The companion's own days: the user is there for them, and there is no gift or buzz about someone else.
OWN = ('own_wedding', 'own_graduation', 'own_retirement')


# Planning a big day ----------------------------------------------------------------------------------------------

def rows(connection, timeline_id: str, statuses: tuple[str, ...] = STATUSES) -> list[dict]:
    marks = ','.join('?' * len(statuses))
    found = many(connection, f'SELECT * FROM big_days WHERE timeline_id=? AND status IN ({marks}) ORDER BY local_date',
                 (timeline_id, *statuses))
    return [view(row) for row in found]


def view(row: dict) -> dict:
    return {**row, 'place': decode(row['place']) or {}, 'details': decode(row['details']) or {}}


def get(connection, row_id: str) -> dict | None:
    row = optional(connection, 'SELECT * FROM big_days WHERE id=?', (row_id,))
    return view(row) if row else None


def title(row: dict, companion_name: str = '') -> str:
    """"Leo's wedding", "Ana's 60th birthday", "Mira's wedding"."""
    details = row['details']
    return KINDS[row['kind']].title.format(name=first(details.get('name', '')), companion=first(companion_name),
                                           age=ages.ordinal(details['age']) if details.get('age') else '')


def who(details: dict) -> str:
    """'your brother Leo', 'Sam (the barista at Daily Grind)'."""
    if details.get('town'):
        return f"{first(details['name'])} ({details.get('role') or 'someone you know from town'})"
    return f"your {details['role']} {first(details['name'])}" if details.get('role') else first(details['name'])


def said(row: dict) -> str:
    """The big day as the companion says it: "your brother Leo's wedding", "your wedding to Sam"."""
    details = row['details']
    return KINDS[row['kind']].said.format(who=who(details), name=first(details.get('name', '')),
                                          age=ages.ordinal(details['age']) if details.get('age') else '')


def place_for(connection, companion: dict, kind: Kind, day: date, seed: str, details: dict) -> dict:
    """Where it is held: a venue in their city that fits the kind; somewhere unnamed out of town or in a city the app
    doesn't know."""
    from companion.life import wedding
    data = outings.city_data(connection, companion['version']['definition'])
    away = details.get('city') if details.get('local') is False else ''
    if not data or away:
        name = f"a venue in {away}" if away else 'the venue'
        return {'id': '~big-day', 'name': name, 'kind': 'venue', 'neighborhood': '', 'summary': '', 'cost': '',
                'cuisine': '', 'city': away, 'city_id': '', 'spots': []}
    if kind.key in ('wedding', 'own_wedding'):
        return wedding.venue_for(data, wedding.customs(wedding.culture_of(data)), 'proper', seed, day=day)
    options = [item for item in data['places'] if item['kind'] in kind.places
               and not any(word in item['name'].lower() for word in NOT_PARTY)]
    if kind.key in ('graduation', 'own_graduation'):
        options = [item for item in data['places'] if any(word in item['name'].lower() for word in GRADUATION_PLACES)
                   ] or options
    if wedding.cold(data, day):
        options = [item for item in options if item['kind'] not in wedding.OUTDOOR] or options
    item = generators.pick(seed, 'venue', options or data['places'])
    return outings.place_view(item, data)


def gift_for(connection, companion: dict, kind: Kind, seed: str) -> tuple[str, float]:
    """(the gift in words, what it costs in the city's money): from the bank for the kind (its modern one in a modern
    city), priced by their pay."""
    if not kind.gift:
        return '', 0.0
    gifts = bank()['gifts']
    key = f'{kind.gift}_modern' if f'{kind.gift}_modern' in gifts and modern_city(connection, companion) else kind.gift
    gift = generators.pick(seed, 'gift', gifts[key])
    found = money.profile(companion['version']['definition'])
    return gift, round(money.monthly_share(found) * kind.share, 2) if found else 0.0


def outfit_for(connection, companion: dict, row_id: str, day: date) -> str:
    """What they wear on the day: their own wedding's attire, else something to go out in from their wardrobe."""
    from companion.life import wardrobe
    timeline_id = companion['active_timeline_id']
    state = optional(connection, 'SELECT * FROM wardrobe_state WHERE timeline_id=?', (timeline_id,))
    if not state:
        return ''
    items = wardrobe.items_on(connection, timeline_id, day)
    found = decode(state['profile'])
    worn = wardrobe.outfit(items, 'out', f"{state['seed']}:{row_id}:big-day", None, found.get('code', 'casual'),
                           False)
    return wardrobe.phrase(worn)


def modern_city(connection, companion: dict) -> bool:
    from companion.life import admin
    return admin.era_group(outings.city_data(connection, companion['version']['definition'])) == 'modern'


def add(connection, companion: dict, found: dict, now: datetime) -> dict | None:
    """A big day in their life, once per source: where, when, the gift and whether they ask the user along. Later
    features call this with their own (a graduation from a life chapter, a funeral)."""
    timeline_id, today = companion['active_timeline_id'], local_today(companion, now)
    kind = KINDS[found['kind']]
    day = found['day']
    if optional(connection, 'SELECT id FROM big_days WHERE timeline_id=? AND source=?', (timeline_id, found['source'])) \
            or day < today + timedelta(days=SOONEST) or kind.modern and not modern_city(connection, companion):
        return None
    row_id, timestamp = identifier(), stamp(now)
    seed = f"bigday:{timeline_id}:{found['source']}"
    place = place_for(connection, companion, kind, day, seed, found['details'])
    gift, cost = gift_for(connection, companion, kind, seed)
    lead = random.Random(f'{seed}:invite').randint(*INVITE_BEFORE)
    connection.execute(
        'INSERT INTO big_days (id, timeline_id, kind, source, person_id, local_date, at_time, until_time, place, '
        'details, invite_on, gift, gift_cost, gift_on, outfit, created_at, updated_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (row_id, timeline_id, kind.key, found['source'], found['person_id'], day.isoformat(), kind.at, kind.until,
         encode(place), encode(found['details']), max(today, day - timedelta(days=lead)).isoformat(), gift, cost,
         max(today, day - timedelta(days=GIFT_BEFORE)).isoformat(), outfit_for(connection, companion, row_id, day),
         timestamp, timestamp))
    row = get(connection, row_id)
    decide_invite(connection, companion, row, now)
    return get(connection, row_id)


def invitable(connection, companion: dict, row: dict) -> bool:
    """Whether the user could come at all: someone in town (or a visit can reach them), not apart from the companion,
    and no other big day they are asked to that close."""
    from companion.life import long_distance
    if row['details'].get('local') is False or steps.apart(connection, companion) == 'ended':
        return False
    between = long_distance.far(connection, companion)
    if between and not long_distance.reachable(between):
        return False
    low = (date.fromisoformat(row['local_date']) - timedelta(days=INVITE_GAP)).isoformat()
    high = (date.fromisoformat(row['local_date']) + timedelta(days=INVITE_GAP)).isoformat()
    return not optional(connection, "SELECT id FROM big_days WHERE timeline_id=? AND id!=? AND invite=1 AND "
                        "status IN ('planned', 'invited') AND local_date>=? AND local_date<=?",
                        (row['timeline_id'], row['id'], low, high))


def decide_invite(connection, companion: dict, row: dict, now: datetime) -> None:
    """Whether they ask the user along: always to their own wedding, else the engine's `bigday:invite`."""
    if not invitable(connection, companion, row):
        return
    if row['kind'] == 'own_wedding':
        connection.execute('UPDATE big_days SET invite=1 WHERE id=?', (row['id'],))
        return
    from companion import group_guests
    from companion.memory import closeness
    definition = companion['version']['definition']
    facts = {'guests': group_guests.level(connection), 'closeness': closeness.state(connection, companion, now)['level'],
             'family': int(circle.role_kind(row['details'].get('role') or '') in circle.FAMILY),
             'romance': int(steps.ladder_of(definition) == 'romance')}
    names = {'name': first(definition['name']), 'a': title(row), 'b': ''}
    table = consequences.tables()[INVITE]
    outcome = consequences.decide(connection, timeline_id=row['timeline_id'], choice=INVITE,
                                  subject=f"bigday:{row['id']}", facts=facts, names=names,
                                  labels=[option['label'].format(**names) for option in table['options']],
                                  day=local_today(companion, now).isoformat(), timestamp=stamp(now))
    connection.execute('UPDATE big_days SET invite=?, consequence_id=? WHERE id=?',
                       (int(outcome['picked'] == 1), outcome['id'], row['id']))


def change(connection, companion: dict, consequence_id: str, option: int, now: datetime) -> dict:
    """"Change how it went" on whether they ask the user along: before the invitation goes out it follows; once the
    user is coming, going on their own is the same as the user saying no."""
    outcome = consequences.change(connection, consequence_id, option, stamp(now))
    row = optional(connection, 'SELECT * FROM big_days WHERE consequence_id=?', (consequence_id,))
    if row and row['status'] == 'planned':
        connection.execute('UPDATE big_days SET invite=? WHERE id=?', (int(option == 1), row['id']))
    elif row and row['status'] == 'invited' and option == 0:
        decline(connection, view(row), stamp(now))
    return consequences.by_id(connection, outcome['id'])


# A friend's own wedding (companion/life/love_life.py) ------------------------------------------------------------

def own_wedding(connection, companion: dict, partner: dict, decided: date, now: datetime) -> bool:
    """The engine decided a friend and their partner marry: the wedding is planned some months on, with the user
    asked to stand up at it. False when it isn't planned here (big days off, or the user's own romance)."""
    if not ACTIVE or companion['version']['definition'].get('relationship') == 'romance':
        return False
    today = local_today(companion, now)
    seed = f"bigday:love:{partner['id']}"
    months = 4 + int(generators.unit(seed, 'months') * 5)
    day = max(decided + timedelta(days=round(months * 30.44)), today + timedelta(days=30))
    day += timedelta(days=(5 - day.weekday()) % 7)
    found = candidate('own_wedding', f"love:{partner['id']}", None, day, name=partner['name'],
                      partner_id=partner['id'], local=True)
    return add(connection, companion, found, now) is not None


def waiting(connection, partner: dict) -> bool:
    """Their wedding to this partner is planned and still to come: the pair moves no further until it is held."""
    return bool(optional(connection, "SELECT id FROM big_days WHERE source=? AND status IN ('planned', 'invited', "
                         "'declined')", (f"love:{partner['id']}",)))


# Keeping big days in step ----------------------------------------------------------------------------------------

def advance(connection, companion: dict, now: datetime) -> None:
    """Once a day: find new big days, follow the ones planned and finish the ones held. Cheap: no model."""
    if not ACTIVE or not companion.get('active_timeline_id'):
        return
    today = local_today(companion, now)
    follow(connection, companion, now)
    people = {row['id']: row for row in circle.people(connection, companion['active_timeline_id'])}
    for source in SOURCES:
        for found in source(connection, companion, today, people, now):
            if found['day'] <= today + timedelta(days=AHEAD):
                add(connection, companion, found, now)


def follow(connection, companion: dict, now: datetime) -> None:
    """Called off when the person left the circle or the pair split up; the user said no when the outing was called
    off; held when its day is over (with the user when they went)."""
    today, timezone = local_today(companion, now), companion['version']['timezone']
    for row in rows(connection, companion['active_timeline_id'], ('planned', 'invited', 'declined')):
        if gone(connection, row):
            call_off(connection, row, stamp(now))
            continue
        outing = optional(connection, 'SELECT * FROM outings WHERE id=?', (row['outing_id'] or '',))
        state = outings.state(outings.view(outing), timezone, now) if outing else None
        if row['status'] == 'invited' and state in (None, 'cancelled'):
            decline(connection, row, stamp(now))
        elif row['status'] == 'invited' and state == 'done':
            finish(connection, companion, row, True, now)
        elif row['status'] != 'invited' and row['local_date'] < today.isoformat():
            finish(connection, companion, row, False, now)


def gone(connection, row: dict) -> bool:
    if row['person_id']:
        person = optional(connection, 'SELECT status FROM circle_people WHERE id=?', (row['person_id'],))
        if person is None or person['status'] == 'removed':
            return True
    partner_id = row['details'].get('partner_id')
    if partner_id:
        partner = optional(connection, 'SELECT ended_on FROM love_partners WHERE id=?', (partner_id,))
        return partner is None or partner['ended_on'] is not None
    return False


def call_off(connection, row: dict, timestamp: str) -> None:
    connection.execute("UPDATE big_days SET status='called_off', updated_at=? WHERE id=?", (timestamp, row['id']))
    cancel_plans(connection, row, timestamp)


def cancel_plans(connection, row: dict, timestamp: str) -> None:
    """The outing and the user's stay with them for it, when they haven't happened yet."""
    connection.execute("UPDATE outings SET status='cancelled', cancelled_at=? WHERE id=? AND status='planned'",
                       (timestamp, row['outing_id'] or ''))
    connection.execute("UPDATE trips SET status='cancelled', cancelled_at=? WHERE id=? AND status='planned'",
                       (timestamp, row['trip_id'] or ''))


def decline(connection, row: dict, timestamp: str) -> None:
    """The user can't come: fine, and remembered. They go on their own."""
    connection.execute("UPDATE big_days SET status='declined', answered_at=?, updated_at=? WHERE id=?",
                       (timestamp, timestamp, row['id']))
    cancel_plans(connection, row, timestamp)


def mark(connection, row: dict, timestamp: str, **values) -> None:
    """Writes what the day changed into the circle row of the person whose day it was."""
    if not row['person_id']:
        return
    person = optional(connection, 'SELECT details FROM circle_people WHERE id=?', (row['person_id'],))
    if person:
        connection.execute('UPDATE circle_people SET details=?, revision=revision+1, updated_at=? WHERE id=?',
                           (encode({**(decode(person['details']) or {}), **values}), timestamp, row['person_id']))


def married(connection, companion: dict, row: dict, with_user: bool, now: datetime) -> None:
    mark(connection, row, stamp(now), married=True)


def retired(connection, companion: dict, row: dict, with_user: bool, now: datetime) -> None:
    mark(connection, row, stamp(now), career='Retired', retired_on=row['local_date'])


def graduated(connection, companion: dict, row: dict, with_user: bool, now: datetime) -> None:
    mark(connection, row, stamp(now), graduated=row['local_date'][:4])


def wed(connection, companion: dict, row: dict, with_user: bool, now: datetime) -> None:
    """A friend's own wedding: married to their partner, and the user, there as their best friend, stood up at it."""
    from companion.life import love_life
    day, timestamp = date.fromisoformat(row['local_date']), stamp(now)
    partner = optional(connection, 'SELECT * FROM love_partners WHERE id=?', (row['details'].get('partner_id'),))
    if partner and partner['ended_on'] is None:
        love_life.step_up(connection, {**partner, 'details': decode(partner['details'])}, 'married', day, timestamp)
    found = steps.state(connection, companion, now, write=False) if with_user else None
    if found and found['ladder'] == 'friendship' and found['step'] in ('best_friends', 'trip'):
        steps.insert_step(connection, companion['active_timeline_id'], 'friendship', 'wedding_party', day, 'them',
                          timestamp)


# What each kind changes once it is held; later features add their own.
AFTER = {'wedding': married, 'retirement': retired, 'graduation': graduated, 'own_wedding': wed}


def finish(connection, companion: dict, row: dict, with_user: bool, now: datetime) -> None:
    connection.execute("UPDATE big_days SET status='done', with_user=?, updated_at=? WHERE id=?",
                       (int(with_user), stamp(now), row['id']))
    if row['kind'] in AFTER:
        AFTER[row['kind']](connection, companion, row, with_user, now)


# The invitation (a first text, companion/life/openers.py) ----------------------------------------------------------

def invite_due(connection, companion: dict, now: datetime) -> list:
    """A big day they will ask the user to: on its day, the invitation naming whose, when and where."""
    from companion.life.openers import Trigger
    from companion.life.their_people import clock_text
    if not ACTIVE or not FIRST_TEXTS or not companion.get('active_timeline_id'):
        return []
    local = now.astimezone(zone(companion['version']['timezone']))
    if not INVITE_HOURS[0] <= local.hour < INVITE_HOURS[1]:
        return []
    today = local.date().isoformat()
    soonest = (local.date() + timedelta(days=2)).isoformat()
    row = next((item for item in rows(connection, companion['active_timeline_id'], ('planned',))
                if item['invite'] and item['invite_on'] <= today and item['local_date'] >= soonest
                and invitable(connection, companion, item)), None)
    if row is None:
        return []
    day = date.fromisoformat(row['local_date'])
    when = f"{'next ' if (day - local.date()).days >= 7 else ''}{day:%A}"
    template = invitation(row, when, clock_text(row['at_time']))
    return [Trigger(f"bigday:{row['id']}", 'big_day', reason_for(row, day), template, (row['id'],))]


def reason_for(row: dict, day: date) -> str:
    when = f"{day:%A} {day.day} {day:%B} at {row['at_time']}, at {row['place']['name']}"
    if row['kind'] == 'own_wedding':
        return (f"You and {first(row['details']['name'])} are getting married on {when}, and you want the user, your "
                'close friend, to stand up with you at the wedding. Ask them in your own words, naming the day and the '
                'place, warmly; it means a lot to you.')
    if row['kind'] in OWN:
        return (f"It's {said(row)} on {when}, and you'd love the user to be there with you. Ask them in your own "
                "words, naming the day, the time and the place. If they can't come, that's fine.")
    gift = f" You're bringing {row['gift']} as a gift." if row['gift'] else ''
    return (f"You're going to {said(row)} on {when}, and you'd love the user to come with you as your plus-one. Ask "
            f'them in your own words, naming whose it is, the day, the time and the place.{gift} If they can\'t come, '
            "that's fine.")


def invitation(row: dict, day: str, time: str) -> str:
    seed = random.Random(f"{row['id']}:line")
    if row['kind'] == 'own_wedding':
        line = seed.choice(bank()['stand_up']).format(partner=first(row['details']['name']), day=day,
                                                     place=row['place']['name'])
    else:
        event = said(row).replace('your ', 'my ', 1)
        line = seed.choice(bank()['invite']).format(event=event, day=day, time=time, place=row['place']['name'])
    return line[:1].upper() + line[1:]


SETTLES = ('big_day',)


def settle(connection, companion: dict, message: dict, trigger, timestamp: str) -> dict | None:
    """The invitation went out: the day is booked as an outing with the user (and, long distance, the user's stay
    with them around it)."""
    from companion.life import together
    row = get(connection, trigger.sources[0])
    if row is None or row['status'] != 'planned':
        return None
    day = date.fromisoformat(row['local_date'])
    place = {**row['place'], 'big_day': row['id'], 'title': title(row, companion['version']['definition']['name']),
             'event': row['kind'], 'gift': row['gift'], 'standing_up': row['kind'] == 'own_wedding',
             'own': row['kind'] in OWN,
             'people': [{'id': row['person_id'] or '', 'name': row['details'].get('name', ''),
                         'role': row['details'].get('role', '')}] if row['person_id'] else []}
    outing = together.insert(connection, companion, message['id'], ACTIVITY, place, day, row['at_time'],
                             row['until_time'], None, timestamp)
    trip_id = stay(connection, companion, day, message['id'], parse(timestamp))
    connection.execute("UPDATE big_days SET status='invited', message_id=?, outing_id=?, trip_id=?, updated_at=? "
                       'WHERE id=?', (message['id'], outing['id'], trip_id, timestamp, row['id']))
    return outings.get(connection, outing['id'])


def stay(connection, companion: dict, day: date, message_id: str, now: datetime) -> str | None:
    """Long distance: the user's stay with them over the big day, by v0.12's rules (none needed when one covers it)."""
    from companion.life import long_distance, trips
    between = long_distance.far(connection, companion)
    if not between or not long_distance.reachable(between):
        return None
    days = [day - timedelta(days=1), day, day + timedelta(days=1)]
    if long_distance.overlaps(connection, companion, days):
        return None
    home = outings.city_data(connection, companion['version']['definition'])
    trip = long_distance.plan(connection, companion, home, between, days, long_distance.HOST, message_id) if home \
        else None
    return trips.insert(connection, companion, trip, now) if trip else None


def note(connection, message: dict, companion: dict, timestamp: str) -> bool:
    """A plain no in the user's first reply to an invitation: they can't come, which is fine."""
    if not ACTIVE or message['role'] != 'user' or steps.answer(message['text']) != 'no':
        return False
    for row in rows(connection, companion['active_timeline_id'], ('invited',)):
        asked = optional(connection, 'SELECT seq FROM messages WHERE timeline_id=? AND (id=? OR origin_id=?)',
                         (message['timeline_id'], row['message_id'] or '', row['message_id'] or ''))
        if asked and asked['seq'] < message['seq'] and steps.first_turn(connection, message, asked['seq']):
            decline(connection, row, timestamp)
            return True
    return False


# The outing (companion/life/outings.py) ----------------------------------------------------------------------------

def of_outing(connection, outing: dict) -> dict | None:
    return get(connection, outing['place'].get('big_day') or '')


def what(outing: dict) -> str:
    """"Leo's wedding at The Belvedere (a hotel in Mount Vernon)"."""
    place = outing['place']
    area = f" in {place['neighborhood']}" if place.get('neighborhood') else ''
    kind = f" ({place['kind']}{area})" if place.get('kind') and not place['id'].startswith('~') else ''
    return f"{place.get('title') or 'a big day'} at {place['name']}{kind}"


def doing(outing: dict) -> str:
    place = outing['place']
    if place.get('standing_up'):
        return f"got married at {place['name']}, with you standing up with them"
    if place.get('own'):
        did = 'graduated' if place.get('event') == 'own_graduation' else 'had their retirement party'
        return f"{did} at {place['name']}, with you there"
    return f"went to {place.get('title') or 'a celebration'} at {place['name']} with you"


def scene(connection, companion: dict, outing: dict, now: datetime | None) -> str:
    """Being there together, in person, with the circle around."""
    row = of_outing(connection, outing)
    if row is None:
        return f"- Right now you and the user are at {what(outing)}, in person, until about {outing['until_time']}."
    role = ('standing up with you as your closest friend' if row['kind'] == 'own_wedding' else
            'there for you' if row['kind'] in OWN else 'your plus-one')
    parts = [f"Right now you are at {said(row)}, in person, at {row['place']['name']}, from {row['at_time']} until "
             f"about {row['until_time']}. The user is here with you, {role}.",
             f"You brought {row['gift']} as your gift." if row['gift'] else '',
             f"You're wearing {row['outfit']}." if row['outfit'] else '',
             'It is a happy, busy day with lots of people around. Talk as if you are there together, face to face, not '
             'texting: what you say and do. Others are around too: you can say briefly what they say or do, but you '
             'speak only as yourself.']
    return '- ' + ' '.join(part for part in parts if part)


def memory_text(outing: dict, name: str) -> dict:
    day = date.fromisoformat(outing['local_date'])
    place = outing['place']
    event = place.get('title') or 'a celebration'
    if place.get('standing_up'):
        return {'subject': event, 'value': f"You stood up at {name}'s wedding at {place['name']} on {day:%A, %B} "
                                           f'{day.day}, {day.year}.'}
    if place.get('own'):
        return {'subject': event, 'value': f"You were there for {event} at {place['name']} on {day:%A, %B} {day.day}, "
                                           f'{day.year}.'}
    return {'subject': event, 'value': f"You went to {event} at {place['name']} with {name} on {day:%A, %B} "
                                       f'{day.day}, {day.year}.'}


def caption(outing: dict) -> str:
    return generators.pick(f"bigday:{outing['id']}", 'caption', bank()['captions'])


def photo_wearing(connection, outing: dict) -> str:
    row = of_outing(connection, outing)
    return f"Wearing {row['outfit']}." if row and row['outfit'] else ''


def dressed(connection, timeline_id: str, local_date: str, now: datetime | None = None) -> str:
    """What they wear at a big day on this date, else ''; with `now`, only while they are there."""
    for row in rows(connection, timeline_id, ('planned', 'invited', 'declined', 'done')):
        if row['local_date'] == local_date and row['outfit'] and (now is None or under_way(connection, row, now)):
            return row['outfit']
    return ''


def under_way(connection, row: dict, now: datetime) -> bool:
    timeline = optional(connection, 'SELECT companion_id FROM timelines WHERE id=?', (row['timeline_id'],))
    from companion.characters import by_id
    companion = by_id(connection, timeline['companion_id']) if timeline else None
    if companion is None:
        return False
    local = now.astimezone(zone(companion['version']['timezone']))
    return local.date().isoformat() == row['local_date'] and row['at_time'] <= local.strftime('%H:%M') < \
        row['until_time']


def people_there(connection, timeline_id: str, now: datetime) -> set[str]:
    """Circle people at their big day right now: there, not at work (companion/life/agenda.py circle_view)."""
    return {row['person_id'] for row in rows(connection, timeline_id, ('planned', 'invited', 'declined'))
            if row['person_id'] and under_way(connection, row, now)}


# What the chat context says ----------------------------------------------------------------------------------------

def coming_line(row: dict, today: date) -> str:
    when = 'today' if row['local_date'] == today.isoformat() else f"on {long_date(row['local_date'])}"
    head = f"- {said(row)[:1].upper()}{said(row)[1:]} is {when} at {row['at_time']}, at {row['place']['name']}."
    gift = f" You're bringing {row['gift']}." if row['gift'] else ''
    wear = f" You plan to wear {row['outfit']}." if row['outfit'] else ''
    if row['status'] == 'invited':
        company = (' The user is standing up with you.' if row['kind'] == 'own_wedding' else
                   ' The user is coming, there for you.' if row['kind'] in OWN else
                   ' The user is coming with you as your plus-one.')
    elif row['status'] == 'declined':
        company = (" The user can't make it, and that's completely fine with you: you're going on your own. Don't "
                   'hold it against them.')
    elif row['invite']:
        company = " You mean to ask the user to come with you as your plus-one; you haven't asked yet."
    else:
        company = " You're going." if row['kind'] in OWN else " You're going on your own."
    return head + company + gift + wear


def past_line(row: dict, today: date) -> str:
    when = f"{long_date(row['local_date'])} ({days_ago(date.fromisoformat(row['local_date']), today)})"
    if row['with_user']:
        return f'- On {when} you and the user went to {said(row)} together.'
    alone = " on your own; the user couldn't make it, and that was fine" if row['answered_at'] else ''
    return f'- On {when} you went to {said(row)}{alone}.'


def buzz_line(row: dict, today: date) -> str:
    """Group chat buzz about it, the days before and after (a modern city only), for them to pass on."""
    gap = (date.fromisoformat(row['local_date']) - today).days
    key = 'buzz_before' if 0 < gap <= BUZZ_BEFORE else 'buzz_after' if -BUZZ_AFTER <= gap < 0 else None
    if key is None or row['kind'] in OWN:
        return ''
    line = random.Random(f"{row['id']}:{key}").choice(bank()[key]).format(
        event=title(row), host=first(row['details'].get('name', '')))
    return f'- Group chat buzz you could pass on: "{line}"'


def context_lines(connection, companion: dict, now: datetime) -> list[tuple[str, str]]:
    """(identity, line) for the 'big_days' section: big days coming up, just held, and the buzz around them."""
    today = local_today(companion, now)
    modern = modern_city(connection, companion)
    result = []
    for row in rows(connection, companion['active_timeline_id'], ('planned', 'invited', 'declined', 'done')):
        gap = (date.fromisoformat(row['local_date']) - today).days
        if row['status'] != 'done' and gap >= 0:
            result.append((f"bigday:{row['id']}:{row['status']}", coming_line(row, today)))
        elif row['status'] == 'done' and -TOLD_DAYS <= gap <= 0:
            result.append((f"bigday:{row['id']}:done", past_line(row, today)))
        buzz = buzz_line(row, today) if modern and row['status'] != 'called_off' else ''
        if buzz:
            result.append((f"bigday:{row['id']}:buzz:{today.isoformat()}", buzz))
    return result


def offer(packet, connection, companion: dict, now: datetime, group=None) -> None:
    """Adds the 'big_days' section, in a 1:1 chat."""
    if not ACTIVE or group is not None or not companion.get('active_timeline_id'):
        return
    for identity, text in context_lines(connection, companion, now):
        packet.offer('big_days', identity, text)


# Money (money.household) -------------------------------------------------------------------------------------------

def purchases(connection, timeline_id: str, start: date, day: date) -> list[dict]:
    """Gifts bought this pay period (a week before each big day they go to)."""
    return [{'text': f"bought {row['gift']} as a gift", 'date': row['gift_on'], 'spend': '', 'cost': row['gift_cost'],
             'for': 'gift'}
            for row in many(connection, "SELECT * FROM big_days WHERE timeline_id=? AND status!='called_off' AND "
                            'gift_cost>0 AND gift_on>=? AND gift_on<=?', (timeline_id, start.isoformat(),
                                                                         day.isoformat()))]


# Branches (companion/timelines.py) ---------------------------------------------------------------------------------

def copy(connection, parent_id: str, new_id: str, cutoff_date: str) -> None:
    """Big days known by the fork carry over; anything the user was asked to after it is the copy's own."""
    for row in many(connection, 'SELECT * FROM big_days WHERE timeline_id=? AND created_at<=?',
                    (parent_id, f'{cutoff_date}T23:59:59')):
        status = row['status'] if row['status'] in ('planned', 'done', 'called_off') else 'planned'
        connection.execute(
            'INSERT INTO big_days (id, timeline_id, kind, source, person_id, status, local_date, at_time, until_time, '
            'place, details, invite, invite_on, consequence_id, gift, gift_cost, gift_on, outfit, with_user, '
            'created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?)',
            (identifier(), new_id, row['kind'], row['source'], row['person_id'], status, row['local_date'],
             row['at_time'], row['until_time'], row['place'], row['details'], row['invite'], row['invite_on'],
             row['gift'], row['gift_cost'], row['gift_on'], row['outfit'], row['with_user'], row['created_at'],
             row['updated_at']))
