"""Big days in the circle (Hit List #69, v0.14 Years Go By): weddings, milestone birthdays, retirement parties and
graduations in the companion's circle and town become days they go to, with the user as their plus-one; and a
friendship companion's own wedding is a big day with the user standing up at it.

The app decides, the user overrides ("the world exists outside of User", Vanta 2026-10-08):

- Where big days come from (`SOURCES`, checked once a day): a sibling's engagement storyline (sibling_engaged in
  companion/life/storylines.py) sets a wedding date for next year; friends in their circle get engaged and marry in
  seeded years, more often with the Their love life slider up; a parent, sibling, cousin or old friend turning 30, 40,
  50 ... has a party (companion/life/ages.py); a working relative reaching their seeded retirement age has a send-off;
  a circle member studying graduates in late spring; a townsperson the companion knows well marries
  (companion/world/couples.py); a friend's own engagement (companion/life/love_life.py) plans their wedding; and a
  baby in their circle turning one has a party at their parent's (companion/life/families.py). Children are words
  only: the parent is the one there, there is no photo, no buzz, and with the adult side of life on there is no party.
  Later features add their own kinds (`KINDS`) and big days (`add`): graduations from life chapters, funerals.
- Whether they ask the user along is the consequence engine's `bigday:invite` (the Guests slider, how close they are,
  family or not, a romance), under Hidden values ("Why it went this way"). Asked or not, they go: a gift bought from
  their own money a week before (the bank's gifts for the kind, priced by their pay, through money.household), an
  outfit from their wardrobe (companion/life/wardrobe.py), and the day itself.
- The invitation is a first text (companion/life/openers.py) naming whose day it is, the day, the time and the place;
  sending it books the day as an outing (companion/life/outings.py, activity 'big-day'), in person with the circle
  there. Long distance, the user's stay with them is planned around it by v0.12's rules (a 'host' visit,
  companion/life/long_distance.py); when no visit can reach them, they go on their own. An out-of-town relative's
  day is in the city they live in (trips.hometown): the user comes along when a trip from the city they share
  reaches it, and either way the companion travels there (the fare from their money, a line saying so).
- The invitation never lands on a day an outing with the user already has: a party or a wedding moves a week on, a
  day that is its own (a graduation, a funeral) isn't asked to. Only days the user said yes to (or is still to
  answer) keep another from being asked within INVITE_GAP; after a no, the next one is weighed again.
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
import re
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
# The photo of their own wedding (images/prompts.py PICTURES): them in wedding clothes, not a guest at a celebration.
PICTURED = 'own-wedding-day'
INVITE = 'bigday:invite'
# Found this far ahead; one closer than SOONEST is too late to plan from now.
AHEAD = 42
SOONEST = 3
# The invitation goes out this many days before (seeded), the gift is bought this many days before.
INVITE_BEFORE = (14, 28)
GIFT_BEFORE = 7
INVITE_HOURS = (10, 21)
# No two big days the user is asked to within this many days of each other: only days the user said yes to (or is
# still to answer) count, so a no to one doesn't hide the next.
INVITE_GAP = 14
# Days whose date is the host's to pick: moved a week on (up to MOVE_WEEKS times) rather than asking the user to a day
# an outing with them already has. A graduation, a send-off on their last day or a funeral keeps its day.
MOVABLE = ('wedding', 'birthday', 'retirement', 'first_birthday', 'own_wedding')
MOVE_WEEKS = 4
# How long the chat hears about a big day before it (group chat buzz) and after it.
BUZZ_BEFORE, BUZZ_AFTER, TOLD_DAYS = 7, 2, 30
# A friend's chance of marrying in a given year, by the Their love life slider (0 nothing new ... 3 lots going on).
FRIEND_RATE = (0.0, 0.03, 0.06, 0.12)
FRIEND_AGES = (24, 60)
FRIENDS = {'close friend', 'longtime friend', 'old friend from school', 'old classmate', 'friend', 'new friend',
           'roommate from years ago'}
# Whose milestone birthday is a party they go to, and who retires with a send-off.
CLOSE = {'parent', 'sibling', 'cousin', 'aunt', 'uncle', 'grandmother', 'grandfather', 'grandparent',
         *circle.OLD_FRIENDS}
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
    # A baby in their circle turning one (companion/life/families.py): at their parent's place.
    'first_birthday': Kind('first_birthday', "{name}'s first birthday", "{who}'s first birthday party", '14:00',
                           '17:00', (), 'first_birthday', 0.01),
    # Their own baby's naming day at home (companion/life/own_family.py): a best friend is asked to be the godparent.
    'naming': Kind('naming', "{name}'s naming day", "{who}'s naming day", '11:00', '14:00', (), None),
    # The pair's baby shower (companion/life/expecting.py), thrown by someone close at their place: no photo, no buzz.
    'own_shower': Kind('own_shower', 'Baby shower at {name}\'s', 'the baby shower {who} is throwing for you and the user',
                       '14:00', '17:00', (), None, 0.0, True),
    # Someone in their circle or town who passed away (companion/life/loss.py): its word, times and place follow the
    # city's customs; a quiet day with no photo and no buzz.
    'funeral': Kind('funeral', "{name}'s {word}", "{who}'s {word}", '11:00', '15:00', ('temple', 'landmark', 'garden'),
                    None, 0.005),
}
# A child's day: the parent hosts, and it is never pictured or passed on as group chat buzz.
CHILDS = ('first_birthday', 'naming', 'own_shower')
GRADUATION_PLACES = ('university', 'college', 'campus', 'school', 'academy', 'institute')
NOT_PARTY = ('station', 'hospital', 'clinic', 'airport', 'prison', 'jail', 'court', 'police', 'parking', 'office')
# Bank lines that only fit a modern city (texts, cars, photos): left out in an old one, by the place's `modern`.
MODERN_ONLY = re.compile(r"\b(?:cars?|drive|driving|RSVP\w*|calendar|texts?|texting|phones?|photos?|selfies?|cameras?|"
                         r'coffee|open bar|hii+|vinyl|playlists?|DJ|emojis?|online)\b', re.IGNORECASE)


@cache
def bank() -> dict:
    return json.loads((catalog.DATA / 'big_days.json').read_text(encoding='utf-8'))


def local_today(companion: dict, now: datetime) -> date:
    return now.astimezone(zone(companion['version']['timezone'])).date()


def fitting(lines: list[str], place: dict) -> list[str]:
    """The bank's lines that fit the city's era (all of them in a modern city)."""
    return lines if place.get('modern', True) else [line for line in lines if not MODERN_ONLY.search(line)] or lines


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


def life_age_of(connection, row: dict, day: date, companion: dict) -> int | None:
    """Their life age (companion/world/lifespans.py), for when someone marries, retires or graduates."""
    return ages.person_life_age(connection, decode(row['details']) or {}, age_of(connection, row, day),
                                companion['version']['definition'])


# Where big days come from ----------------------------------------------------------------------------------------

def candidate(kind: str, source: str, row: dict | None, day: date, **details) -> dict:
    """A big day found by a source: whose (a circle row, when it is someone in the circle), what and when."""
    known = (decode(row['details']) or {}) if row else {}
    person = {'name': row['name'], 'role': row['role'], 'local': known.get('local', True),
              'city': known.get('city') or '', 'pronouns': known.get('pronouns') or ''} if row else {}
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
        age = life_age_of(connection, row, today, companion) or 0
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
        if ages.milestone(age, ages.person_lifespan(connection, decode(row['details']) or {},
                                                    companion['version']['definition'])):
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
        if (life_age_of(connection, row, birthday, companion) or 0) >= retire_at:
            day = birthday + timedelta(days=(4 - birthday.weekday()) % 7 or 7)
            result.append(candidate('retirement', f"retirement:{row['id']}", row, day))
    return result


def graduations(connection, companion: dict, today: date, people: dict, now) -> list[dict]:
    """A circle member studying for long enough graduates on a Saturday in May or June."""
    result = []
    for row in people.values():
        details = decode(row['details']) or {}
        old_enough = STUDENTS.get(details.get('career') or '')
        if not old_enough or details.get('graduated') or (life_age_of(connection, row, today, companion) or 0) < old_enough:
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


def first_birthdays(connection, companion: dict, today: date, people: dict, now) -> list[dict]:
    """A baby in their circle turning one (companion/life/families.py): a party at their parent's, the Saturday on or
    after it. None while the adult side of life is on."""
    from companion.life import families
    if families.withheld(connection):
        return []
    result, definition = [], companion['version']['definition']

    def said_role(row):  # 'mother' in 1895 (circle.said).
        return circle.said(row['role'], definition)
    for item in families.first_birthdays(connection, companion, today, today + timedelta(days=AHEAD)):
        row = people.get(item['parent_id'])
        if row is None:
            continue
        birthday = date.fromisoformat(item['date'])
        child = {'she/her': 'daughter', 'he/him': 'son'}.get(item['pronouns'], 'child')
        result.append(candidate('first_birthday', item['key'], row, birthday + timedelta(days=(5 - birthday.weekday()) % 7),
                                name=item['child'], role=item['relation'] or f"{said_role(row)} {first(row['name'])}'s {child}",
                                host=row['name'], host_role=said_role(row)))
    return result


def namings(connection, companion: dict, today: date, people: dict, now) -> list[dict]:
    """Their own baby's naming day (companion/life/own_family.py), at home with their partner. None while the adult
    side of life is on."""
    from companion.life import families, own_family
    if families.withheld(connection):
        return []
    result, name = [], first(companion['version']['definition']['name'])
    for item in own_family.naming_days(connection, companion, today, today + timedelta(days=AHEAD)):
        row = people.get(item['parent_id'])
        if row is not None:
            child = {'she/her': 'daughter', 'he/him': 'son'}.get(item['pronouns'], 'child')
            result.append(candidate('naming', item['key'], row, date.fromisoformat(item['date']), name=item['child'],
                                    role=child, pronouns=item['pronouns'], host=row['name'], host_role=row['role'],
                                    partner=first(row['name']),
                                    home=f"{name} and {first(row['name'])}'s place"))
    return result


def showers(connection, companion: dict, today: date, people: dict, now) -> list[dict]:
    """The pair's baby shower, while they are expecting (companion/life/expecting.py)."""
    from companion.life import expecting
    return expecting.showers(connection, companion, today, people, now)


def funerals(connection, companion: dict, today: date, people: dict, now) -> list[dict]:
    """A funeral for someone in their circle or town who passed away (companion/life/loss.py)."""
    from companion.life import loss
    return loss.funerals(connection, companion, today, now)


# In order; later features add their own.
SOURCES = [sibling_weddings, friend_weddings, milestone_birthdays, retirements, graduations, town_weddings, chapters,
           first_birthdays, namings, funerals, showers]
# The companion's own days: the user is there for them, and there is no gift or buzz about someone else.
OWN = ('own_wedding', 'own_graduation', 'own_retirement', 'own_shower')
# Days with no group chat buzz and no photo.
QUIET = ('funeral',)
# What they mean to ask the user, before they have: a plus-one, unless it is their own day or a funeral.
ASKING = {'own_wedding': 'to stand up with you at your wedding', 'own_graduation': 'to be there with you',
          'own_retirement': 'to be there with you', 'funeral': 'to come with you', 'naming': 'to be the godparent',
          'own_shower': 'to come with you'}


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
                                           age=ages.ordinal(details['age']) if details.get('age') else '',
                                           word=details.get('word', 'funeral'))


def who(details: dict) -> str:
    """'your brother Leo', 'Sam (the barista at Daily Grind)'."""
    if details.get('town'):
        return f"{first(details['name'])} ({details.get('role') or 'someone you know from town'})"
    return f"your {details['role']} {first(details['name'])}" if details.get('role') else first(details['name'])


def said(row: dict) -> str:
    """The big day as the companion says it: "your brother Leo's wedding", "your wedding to Sam"."""
    details = row['details']
    return KINDS[row['kind']].said.format(who=who(details), name=first(details.get('name', '')),
                                          age=ages.ordinal(details['age']) if details.get('age') else '',
                                          word=details.get('word', 'funeral'))


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
    if kind.key in CHILDS:
        return {'id': '~big-day', 'name': details.get('home') or f"{first(details.get('host') or '')}'s place", 'kind': 'venue',
                'neighborhood': '', 'summary': '', 'cost': '', 'cuisine': '', 'city': '', 'city_id': '', 'spots': []}
    if kind.key in ('wedding', 'own_wedding'):
        return wedding.venue_for(data, wedding.customs(wedding.culture_of(data)), 'proper', seed, day=day)
    if kind.key == 'funeral':
        from companion.life import loss
        return loss.venue_for(connection, companion, data, seed, day, bool(details.get('notable')))
    options = [item for item in data['places'] if item['kind'] in kind.places
               and not any(word in item['name'].lower() for word in NOT_PARTY)]
    if kind.key in ('graduation', 'own_graduation'):
        options = [item for item in data['places'] if any(word in item['name'].lower() for word in GRADUATION_PLACES)
                   ] or options
    if wedding.cold(data, day):
        options = [item for item in options if item['kind'] not in wedding.OUTDOOR] or options
    part = 'morning' if kind.at < '12:00' else 'afternoon' if kind.at < '17:00' else 'evening'
    options = [item for item in options if part in item.get('day_parts', (part,))] or options  # Open then.
    item = generators.pick(seed, 'venue', options or data['places'])
    return outings.place_view(item, data)


def gift_for(connection, companion: dict, kind: Kind, seed: str, details: dict | None = None) -> tuple[str, float]:
    """(the gift in words, what it costs in the city's money): from the bank for the kind (its modern one in a modern
    city), priced by their pay. A funeral has none, only the flowers its details name (someone outside the family)."""
    if not kind.gift:
        found = money.profile(companion['version']['definition'])
        flowers = (details or {}).get('flowers', '')
        return flowers, round(money.monthly_share(found) * kind.share, 2) if flowers and found else 0.0
    gifts = bank()['gifts']
    gift = generators.pick(seed, 'gift', gifts.get(f'{kind.gift}_{gift_era(connection, companion)}') or gifts[kind.gift])
    found = money.profile(companion['version']['definition'])
    return gift, round(money.monthly_share(found) * kind.share, 2) if found else 0.0


def gift_era(connection, companion: dict) -> str:
    """Which gift bank: 'modern', 'old' in Camelot (medieval and fantasy cities), else the timeless one (1895, 1925:
    admin.era_group's 'industrial')."""
    from companion.life import admin
    return admin.era_group(outings.city_data(connection, companion['version']['definition']))


def outfit_for(connection, companion: dict, row_id: str, day: date, wear: str = '', kind: str = '') -> str:
    """What they wear on the day: what the customs ask for (a funeral's dark clothes, their own wedding's attire),
    else something to go out in from their wardrobe."""
    from companion.life import wardrobe, wedding
    if wear:
        return wear
    if kind == 'own_wedding':  # Their own wedding: what the city's customs have them marry in.
        data = outings.city_data(connection, companion['version']['definition'])
        return wedding.attire(companion['version']['definition'], wedding.culture_of(data))
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


def spoken(details: dict, companion: dict) -> str:
    """The role as the companion says it: 'mom' or 'brother' (by pronouns) for a parent or sibling, in their era."""
    role = details['role']
    if role in ('parent', 'sibling'):
        role = circle.relation(role, details.get('pronouns') or '')
    return circle.said(role, companion['version']['definition'])


def add(connection, companion: dict, found: dict, now: datetime) -> dict | None:
    """A big day in their life, once per source: where, when, the gift and whether they ask the user along. Later
    features call this with their own (a graduation from a life chapter, a funeral)."""
    timeline_id, today = companion['active_timeline_id'], local_today(companion, now)
    kind = KINDS[found['kind']]
    day = found['day']
    if optional(connection, 'SELECT id FROM big_days WHERE timeline_id=? AND source=?', (timeline_id, found['source'])) \
            or day < today + timedelta(days=SOONEST) or kind.modern and not modern_city(connection, companion):
        return None
    day = clear_day(connection, companion, kind.key, found['source'], day)
    row_id, timestamp = identifier(), stamp(now)
    if found['details'].get('role'):  # As they say it: 'mom' for a parent, 'mother' in 1895 (circle.said).
        found = {**found, 'details': {**found['details'], 'role': spoken(found['details'], companion)}}
    found = {**found, 'details': {**found['details'], **away(connection, companion, found, day)}}
    seed = f"bigday:{timeline_id}:{found['source']}"
    place = {**place_for(connection, companion, kind, day, seed, found['details']),
             'modern': modern_city(connection, companion)}
    gift, cost = gift_for(connection, companion, kind, seed, found['details'])
    lead = random.Random(f'{seed}:invite').randint(*INVITE_BEFORE)
    connection.execute(
        'INSERT INTO big_days (id, timeline_id, kind, source, person_id, local_date, at_time, until_time, place, '
        'details, invite_on, gift, gift_cost, gift_on, outfit, created_at, updated_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (row_id, timeline_id, kind.key, found['source'], found['person_id'], day.isoformat(),
         found['details'].get('at', kind.at), found['details'].get('until', kind.until), encode(place),
         encode(found['details']), max(today, day - timedelta(days=lead)).isoformat(), gift, cost,
         max(today, day - timedelta(days=GIFT_BEFORE)).isoformat(),
         outfit_for(connection, companion, row_id, day, found['details'].get('wear', ''), kind.key), timestamp,
         timestamp))
    row = get(connection, row_id)
    decide_invite(connection, companion, row, now)
    return get(connection, row_id)


def clear_day(connection, companion: dict, kind: str, source: str, day: date) -> date:
    """The day, or when an outing with the user already has it and the host could pick another, the same weekday a
    week on (up to MOVE_WEEKS times). A townsperson's wedding is the town's own date."""
    if kind not in MOVABLE or source.startswith('town:'):
        return day
    for weeks in range(MOVE_WEEKS + 1):
        if not with_user_on(connection, companion, day + timedelta(weeks=weeks)):
            return day + timedelta(weeks=weeks)
    return day


def with_user_on(connection, companion: dict, day: date) -> bool:
    """An outing with the user is booked for that day."""
    return bool(optional(connection, "SELECT id FROM outings WHERE companion_id=? AND local_date=? AND "
                         "status!='cancelled'", (companion['id'], day.isoformat())))


def away(connection, companion: dict, found: dict, day: date) -> dict:
    """An out-of-town relative's day is in the city they live in (trips.hometown, as a trip to see them goes): its
    name and id, and the fare there and back that comes out of their money the day before (trips.price, a weekend
    trip's share). {} for a day in town, or when no city can be told."""
    from companion.life import trips
    details = found['details']
    person_id = found['person_id'] or loss_person(connection, details)
    home = outings.city_data(connection, companion['version']['definition'])
    if details.get('local') is not False or details.get('city') or not person_id or not home:
        return {}
    city = trips.hometown(person_id, home)
    if city is None:
        return {}
    fare = trips.price(companion['version']['definition'], trips.COST_SHARE[2], day - timedelta(days=1), float('inf'))
    return {'city': city['name'], 'city_id': city['id'], 'fare': fare or 0.0}


def loss_person(connection, details: dict) -> str | None:
    """The circle person a funeral is for (companion/life/loss.py)."""
    found = optional(connection, 'SELECT person_id FROM losses WHERE id=?', (details.get('loss_id') or '',))
    return found['person_id'] if found else None


def travels(connection, companion: dict, row: dict) -> bool:
    """The user can come along to a day out of town: both live in the companion's city (long distance, the user
    can't come) and a trip from there reaches it (trips.fits, within a long weekend's reach)."""
    from companion.life import long_distance, trips
    home = outings.city_data(connection, companion['version']['definition'])
    city = catalog.cities().get(row['details'].get('city_id') or '')
    return bool(home and city) and not long_distance.far(connection, companion) and trips.in_reach(home, city, 3)


def invitable(connection, companion: dict, row: dict) -> bool:
    """Whether the user could come at all: someone in town or a trip they can make together (or a visit can reach
    them), not apart from the companion, and no other big day they are asked to that close (their own wedding and the
    pair's baby shower always ask them)."""
    from companion.life import long_distance
    if row['details'].get('local') is False and not travels(connection, companion, row) or \
            steps.apart(connection, companion) == 'ended':
        return False
    between = long_distance.far(connection, companion)
    if between and not long_distance.reachable(between):
        return False
    return row['kind'] in ('own_wedding', 'own_shower') or not crowded(connection, row)


def crowded(connection, row: dict) -> bool:
    """Another big day within INVITE_GAP days that the user said yes to, went to, or is still to be asked to or
    answer. One they said no to doesn't count, and a funeral in the family is never held back (loss.funerals)."""
    if row['kind'] == 'funeral' and row['details'].get('family'):
        return False
    low = (date.fromisoformat(row['local_date']) - timedelta(days=INVITE_GAP)).isoformat()
    high = (date.fromisoformat(row['local_date']) + timedelta(days=INVITE_GAP)).isoformat()
    return bool(optional(connection, "SELECT id FROM big_days WHERE timeline_id=? AND id!=? AND invite=1 AND "
                         "(status IN ('planned', 'invited') OR status='done' AND with_user=1) AND local_date>=? AND "
                         'local_date<=?', (row['timeline_id'], row['id'], low, high)))


def decide_invite(connection, companion: dict, row: dict, now: datetime) -> None:
    """Whether they ask the user along: always to their own wedding and to the pair's baby shower, else the engine's
    `bigday:invite`."""
    if not invitable(connection, companion, row):
        return
    if row['kind'] in ('own_wedding', 'naming', 'own_shower'):  # A naming day: godparent if best friends.
        found = steps.state(connection, companion, now, write=False) if row['kind'] == 'naming' else None
        if row['kind'] in ('own_wedding', 'own_shower') or found and found['ladder'] == 'friendship' and found['step'] != 'friends':
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
    reconsider(connection, companion, now)
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
        if row['status'] == 'declined' and state == 'planned':
            row = taken_back(connection, row, stamp(now))
        if row['status'] == 'invited' and state == 'planned':
            state = moved_apart(connection, companion, row, outing, now)
        if row['status'] == 'invited' and state in (None, 'cancelled'):
            decline(connection, row, stamp(now))
        elif row['status'] == 'invited' and state == 'done':
            finish(connection, companion, row, True, now)
        elif row['status'] != 'invited' and row['local_date'] < today.isoformat():
            finish(connection, companion, row, False, now)


def reconsider(connection, companion: dict, now: datetime) -> None:
    """Days still to be asked to: one left unasked while the user couldn't come (another big day close by they have
    since said no to, a move) is weighed again, and one whose day an outing with the user has taken since is moved
    a week on where the host could (`clear_day`)."""
    for row in rows(connection, companion['active_timeline_id'], ('planned',)):
        if not row['invite'] and not row['consequence_id']:
            decide_invite(connection, companion, row, now)
            row = get(connection, row['id'])
        day = date.fromisoformat(row['local_date'])
        moved = clear_day(connection, companion, row['kind'], row['source'], day) if row['invite'] and \
            with_user_on(connection, companion, day) else day
        if moved != day:
            gift_on = max(row['gift_on'] or '', (moved - timedelta(days=GIFT_BEFORE)).isoformat())
            connection.execute('UPDATE big_days SET local_date=?, gift_on=?, updated_at=? WHERE id=?',
                               (moved.isoformat(), gift_on, stamp(now), row['id']))


def moved_apart(connection, companion: dict, row: dict, outing: dict, now: datetime) -> str:
    """They live apart since the invitation (one of them moved): the user's stay with them is planned around the day,
    or, when no visit can reach them, the user can't come after all ('cancelled'). Else the outing stays 'planned'."""
    from companion.life import long_distance
    between = long_distance.far(connection, companion)
    if not between or optional(connection, "SELECT id FROM trips WHERE id=? AND status='planned'",
                               (row['trip_id'] or '',)):
        return 'planned'
    if row['details'].get('city_id'):  # Out of town: the trip there together was from the city they shared.
        return 'cancelled'
    if long_distance.reachable(between):
        trip_id = stay(connection, companion, date.fromisoformat(row['local_date']), outing['message_id'], now)
        connection.execute('UPDATE big_days SET trip_id=? WHERE id=?', (trip_id or row['trip_id'], row['id']))
        return 'planned'
    return 'cancelled'


def gone(connection, row: dict) -> bool:
    if row['kind'] in CHILDS and withheld(connection):
        return True
    if row['kind'] == 'funeral':
        from companion.life import loss
        return loss.gone(connection, row)
    if row['kind'] == 'own_shower':
        from companion.life import expecting
        return expecting.shower_gone(connection, row)
    if row['person_id']:
        person = optional(connection, 'SELECT status FROM circle_people WHERE id=?', (row['person_id'],))
        if person is None or person['status'] == 'removed':
            return True
    partner_id = row['details'].get('partner_id')
    if partner_id:
        partner = optional(connection, 'SELECT ended_on FROM love_partners WHERE id=?', (partner_id,))
        return partner is None or partner['ended_on'] is not None
    return False


def withheld(connection) -> bool:
    from companion.life import families
    return families.withheld(connection)


def call_off(connection, row: dict, timestamp: str) -> None:
    connection.execute("UPDATE big_days SET status='called_off', updated_at=? WHERE id=?", (timestamp, row['id']))
    cancel_plans(connection, row, timestamp)


def cancel_plans(connection, row: dict, timestamp: str) -> None:
    """The outing and the user's stay with them for it, when they haven't happened yet."""
    connection.execute("UPDATE outings SET status='cancelled', cancelled_at=? WHERE id=? AND status='planned'",
                       (timestamp, row['outing_id'] or ''))
    connection.execute("UPDATE trips SET status='cancelled', cancelled_at=? WHERE id=? AND status='planned'",
                       (timestamp, row['trip_id'] or ''))


def undone(connection, outing_id: str, timestamp: str) -> None:
    """outings.undo of the day's outing: taken back at once, before a long distance day plans around a stay that
    was called off with the no (long_distance.far_plans)."""
    row = optional(connection, "SELECT * FROM big_days WHERE outing_id=? AND status='declined'", (outing_id,))
    if row:
        taken_back(connection, row, timestamp)


def taken_back(connection, row: dict, timestamp: str) -> dict:
    """"Can't make it" undone on Today (outings.undo): the user is coming after all, and long distance their stay
    for it (called off with the no) is back on."""
    connection.execute("UPDATE big_days SET status='invited', answered_at=NULL, updated_at=? WHERE id=?",
                       (timestamp, row['id']))
    connection.execute("UPDATE trips SET status='planned', cancelled_at=NULL WHERE id=? AND status='cancelled' AND "
                       'cancelled_at=?', (row['trip_id'] or '', row['answered_at'] or ''))
    return {**row, 'status': 'invited', 'answered_at': None}


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
    hidden = CHILDS if withheld(connection) else ()  # Called off at the next pass; never asked to meanwhile.
    row = next((item for item in rows(connection, companion['active_timeline_id'], ('planned',))
                if item['invite'] and item['invite_on'] <= today and item['local_date'] >= soonest
                and item['kind'] not in hidden and invitable(connection, companion, item)
                and not with_user_on(connection, companion, date.fromisoformat(item['local_date']))), None)
    if row is None:
        return []
    day = date.fromisoformat(row['local_date'])
    from companion.life import loss
    template = invitation(row, when_text(day, local.date()), clock_text(row['at_time']), loss.era_of(connection, companion))
    return [Trigger(f"bigday:{row['id']}", 'big_day', reason_for(row, day), template, (row['id'],))]


def when_text(day: date, today: date) -> str:
    """'Saturday' this week, 'next Saturday' the week after, else 'Saturday, November 14'."""
    ahead = (day - today).days
    return f'{day:%A}' if ahead < 7 else f'next {day:%A}' if ahead < 14 else f'{day:%A}, {day:%B} {day.day}'


def reason_for(row: dict, day: date) -> str:
    when = f"{day:%A} {day.day} {day:%B} at {row['at_time']}, at {row['place']['name']}"
    if row['kind'] == 'own_wedding':
        return (f"You and {first(row['details']['name'])} are getting married on {when}, and you want the user, your "
                'close friend, to stand up with you at the wedding. Ask them in your own words, naming the day and the '
                'place, warmly; it means a lot to you.')
    if row['kind'] == 'naming':
        return (f"You and {row['details']['partner']} are holding {first(row['details']['name'])}'s naming day at home "
                f"on {day:%A} {day.day} {day:%B} at {row['at_time']}, and you want the user, your close friend, to be "
                f"{first(row['details']['name'])}'s godparent. Ask them in your own words, naming the day and the time, "
                'warmly; it means a lot to you.')
    if row['kind'] == 'own_shower':
        return (f"{said(row)[:1].upper()}{said(row)[1:]} on {when}. You're both the guests of honour. Tell the user "
                'about it in your own words, naming the day, the time and the place.')
    if row['kind'] in OWN:
        return (f"It's {said(row)} on {when}, and you'd love the user to be there with you. Ask them in your own "
                "words, naming the day, the time and the place. If they can't come, that's fine.")
    if row['kind'] == 'funeral':
        return (f"You're going to {said(row)} on {when}, and you'd like the user there with you. Ask them gently, in "
                "your own words, naming the day, the time and the place. If they can't come, that's fine.")
    gift = f" You're bringing {row['gift']} as a gift." if row['gift'] else ''
    return (f"You're going to {said(row)} on {when}, and you'd love the user to come with you as your plus-one. Ask "
            f'them in your own words, naming whose it is, the day, the time and the place.{gift} If they can\'t come, '
            "that's fine.")


def invitation(row: dict, day: str, time: str, era: str = 'modern') -> str:
    seed = random.Random(f"{row['id']}:line")
    if row['kind'] == 'naming':
        line = seed.choice(fitting(bank()['godparent'], row['place'])).format(
            child=first(row['details']['name']), partner=row['details']['partner'], day=day, time=time)
    elif row['kind'] == 'own_wedding':
        line = seed.choice(fitting(bank()['stand_up'], row['place'])).format(
            partner=first(row['details']['name']), day=day, place=row['place']['name'])
    elif row['kind'] == 'own_shower':
        line = seed.choice(bank()['invite_shower']).format(host=first(row['details']['name']), day=day, time=time,
                                                           place=row['place']['name'])
    else:
        event = said(row).replace('your ', 'my ', 1)
        lines = fitting(bank()['invite_funeral' if row['kind'] == 'funeral' else 'invite'], row['place'])
        if row['kind'] == 'funeral':
            from companion.life import loss
            lines = loss.fitting(lines, era)
        line = seed.choice(lines).format(event=event, day=day, time=time, place=row['place']['name'])
        if row['kind'] == 'funeral':  # Those lines are written all in lower case.
            return line
    return re.sub(r'(^|[.?!] )next ', r'\1Next ', on_next(line[:1].upper() + line[1:]))


def on_next(text: str) -> str:
    """'on next Saturday' (a line's "on {day}" with `when_text`'s 'next Saturday') reads 'next Saturday'."""
    return re.sub(r'\b[Oo]n (next \w+day)\b', r'\1', text)


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
             'godparent': row['kind'] == 'naming',
             'own': row['kind'] in OWN, 'no_photo': row['kind'] in CHILDS, 'quiet': row['kind'] in QUIET,
             'people': [host(row)] if row['person_id'] else []}
    outing = together.insert(connection, companion, message['id'], ACTIVITY, place, day, row['at_time'],
                             row['until_time'], None, timestamp)
    trip_id = stay(connection, companion, day, message['id'], parse(timestamp))
    connection.execute("UPDATE big_days SET status='invited', message_id=?, outing_id=?, trip_id=?, updated_at=? "
                       'WHERE id=?', (message['id'], outing['id'], trip_id, timestamp, row['id']))
    return outings.get(connection, outing['id'])


def host(row: dict) -> dict:
    """The circle person whose day it is, or at a child's day their parent."""
    details = row['details']
    if details.get('host'):
        return {'id': row['person_id'], 'name': details['host'], 'role': details.get('host_role', '')}
    return {'id': row['person_id'], 'name': details.get('name', ''), 'role': details.get('role', '')}


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
    if place.get('godparent'):
        return f"held {place.get('title') or 'a naming day'} at home, with you as godparent"
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
            f"there to be {first(row['details']['name'])}'s godparent" if row['kind'] == 'naming' else
            'there for you' if row['kind'] in OWN + QUIET else 'your plus-one')
    parts = [f"Right now you are at {said(row)}, in person, at {row['place']['name']}, from {row['at_time']} until "
             f"about {row['until_time']}. The user is here with you, {role}.",
             f"You brought {row['gift']}." if row['gift'] and row['kind'] in QUIET else
             f"You brought {row['gift']} as your gift." if row['gift'] else '',
             f"You're wearing {row['outfit']}." if row['outfit'] else '', day_text(row)]
    return '- ' + ' '.join(part for part in parts if part)


def day_text(row: dict) -> str:
    """How the day feels: a funeral's order by its customs, else a happy, busy day."""
    if row['kind'] == 'funeral':
        details = row['details']
        return (f"It is a sad, quiet day: {details.get('service', 'a service')}, and "
                f"{details.get('after', 'time with the family afterward')}. "
                'Talk as if you are there together, face to face, not texting: what you say and do. You may be '
                'quiet, and you can still smile at a good story about them. Others are around too: you can say '
                'briefly what they say or do, but you speak only as yourself.')
    return ('It is a happy, busy day with lots of people around. Talk as if you are there together, face to face, not '
            'texting: what you say and do. Others are around too: you can say briefly what they say or do, but you '
            'speak only as yourself.')


def memory_text(outing: dict, name: str) -> dict:
    day = date.fromisoformat(outing['local_date'])
    place = outing['place']
    event = place.get('title') or 'a celebration'
    if place.get('standing_up'):
        return {'subject': event, 'value': f"You stood up at {name}'s wedding at {place['name']} on {day:%A, %B} "
                                           f'{day.day}, {day.year}.'}
    if place.get('godparent'):
        return {'subject': event, 'value': f"You became the godparent at {event} on {day:%A, %B} {day.day}, "
                                           f'{day.year}.'}
    if place.get('own'):
        return {'subject': event, 'value': f"You were there for {event} at {place['name']} on {day:%A, %B} {day.day}, "
                                           f'{day.year}.'}
    return {'subject': event, 'value': f"You went to {event} at {place['name']} with {name} on {day:%A, %B} "
                                       f'{day.day}, {day.year}.'}


def caption(outing: dict) -> str:
    return generators.pick(f"bigday:{outing['id']}", 'caption', fitting(bank()['captions'], outing['place']))


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


# Their day (companion/life/agenda.py, work.py) -----------------------------------------------------------------

def as_plans(connection, timeline_id: str, since: str) -> dict[str, list[dict]]:
    """The big days they go to without the user, by local date in the shape own_plans.assign takes, with the hours
    the day runs on (one the user comes to is an outing, companion/life/outings.py). The id changes with its status,
    so the agenda composes the slot again."""
    result = {}
    for row in rows(connection, timeline_id, ('planned', 'declined', 'done')):
        if row['local_date'] < since or row['with_user']:
            continue
        key = f"bigday:{row['id']}:{row['status']}"
        hours = [f'{hour:02d}:00' for hour in range(int(row['at_time'][:2]) + 1, int(row['until_time'][:2]))]
        result.setdefault(row['local_date'], []).extend(
            [{'id': key, 'at_time': row['at_time'], 'big_day': row},
             *({'id': f'{key}:{at}', 'at_time': at, 'big_day': row, 'continues': True} for at in hours)])
    return result


def alone_doing(row: dict) -> str:
    """'went to Leo's wedding at The Belvedere', 'graduated at Johns Hopkins University'."""
    place = row['place']['name']
    if row['kind'] == 'naming':
        return f'held {title(row)} at home'
    if row['kind'] in OWN:
        return {'own_graduation': 'graduated', 'own_retirement': 'had their retirement party',
                'own_wedding': 'got married', 'own_shower': 'had their baby shower'}[row['kind']] + f' at {place}'
    return f'went to {title(row)} at {place}'


def entry(plan: dict, block: dict, definition: dict) -> dict:
    """The agenda entry for the slot a big day they go to on their own takes: them there."""
    row = plan['big_day']
    quiet = row['kind'] in QUIET
    return {'summary': f"{definition['name']} {alone_doing(row)}.",
            'post': 'Said goodbye today.' if quiet else generators.pick(f"bigday:{row['id']}", 'caption',
                                                                        fitting(bank()['captions'], row['place'])),
            'mood': 'sad' if quiet else 'happy', 'activity': ACTIVITY,
            'place': {key: row['place'].get(key, '') for key in ('id', 'name', 'kind', 'city', 'neighborhood')},
            'with': None, 'weather': block.get('weather'),
            'big_day': {'id': row['id'], 'at': row['at_time'], 'until': row['until_time']},
            'composer_version': 'big-day-1'}


def days_off(connection, companion: dict, start: date, end: date) -> dict[str, str]:
    """{local date: "Leo's wedding"} for the workdays a big day they go to falls in their working hours: they take
    the day off for it (companion/life/work.py days_off)."""
    from companion.life import work
    definition, result = companion['version']['definition'], {}
    if not ACTIVE or not companion.get('active_timeline_id'):
        return result
    for row in rows(connection, companion['active_timeline_id'], ('planned', 'invited', 'declined', 'done')):
        day = date.fromisoformat(row['local_date'])
        block = work.work_block(definition, day) if start <= day <= end else None
        if block and row['at_time'] < (block['end'] if block['end'] > block['start'] else '24:00') and \
                block['start'] < row['until_time']:
            result[row['local_date']] = title(row, definition['name'])
    return result


# What the chat context says ----------------------------------------------------------------------------------------

def coming_line(row: dict, today: date) -> str:
    when = 'today' if row['local_date'] == today.isoformat() else f"on {long_date(row['local_date'])}"
    head = f"- {said(row)[:1].upper()}{said(row)[1:]} is {when} at {row['at_time']}, at {row['place']['name']}."
    gift = (f" You're sending {row['gift']}." if row['kind'] in QUIET else f" You're bringing {row['gift']}.") \
        if row['gift'] else ''
    wear = f" You plan to wear {row['outfit']}." if row['outfit'] else ''
    if row['status'] == 'invited':
        company = (' The user is standing up with you.' if row['kind'] == 'own_wedding' else
                   ' The user is coming, to be the godparent.' if row['kind'] == 'naming' else
                   ' The user is coming, there for you.' if row['kind'] in OWN + QUIET else
                   ' The user is coming with you as your plus-one.')
    elif row['status'] == 'declined':
        company = (" The user can't make it, and that's completely fine with you: you're going on your own. Don't "
                   'hold it against them.')
    elif row['invite']:
        company = f" You mean to ask the user {ASKING.get(row['kind'], 'to come with you as your plus-one')}; you " \
            "haven't asked yet."
    else:
        company = " You're going." if row['kind'] in OWN else " You're holding it at home." \
            if row['kind'] == 'naming' else " You're going on your own."
    return head + company + travel_text(row) + gift + wear


def travel_text(row: dict) -> str:
    """A day out of town (`away`): they travel there for it, with the user when the user is coming."""
    if not row['details'].get('city_id'):
        return ''
    return f" It's out of town, in {row['details']['city']}: you travel there for it" + (
        ', the two of you together.' if row['status'] == 'invited' else '.')


def past_line(row: dict, today: date) -> str:
    when = f"{long_date(row['local_date'])} ({days_ago(date.fromisoformat(row['local_date']), today)})"
    if row['with_user'] and row['kind'] == 'naming':
        return f"- On {when} you held {said(row)} at home, and the user became {first(row['details']['name'])}'s godparent."
    if row['with_user']:
        return f'- On {when} you and the user went to {said(row)} together.'
    alone = " on your own; the user couldn't make it, and that was fine" if row['answered_at'] else ''
    return f'- On {when} you went to {said(row)}{alone}.'


def buzz_line(row: dict, today: date) -> str:
    """Group chat buzz about it, the days before and after (a modern city only), for them to pass on."""
    gap = (date.fromisoformat(row['local_date']) - today).days
    key = 'buzz_before' if 0 < gap <= BUZZ_BEFORE else 'buzz_after' if -BUZZ_AFTER <= gap < 0 else None
    if key is None or row['kind'] in OWN + QUIET or row['kind'] in CHILDS:
        return ''
    line = random.Random(f"{row['id']}:{key}").choice(bank()[key]).format(
        event=title(row), host=first(row['details'].get('name', '')))
    return f'- Group chat buzz you could pass on: "{line}"'


def context_lines(connection, companion: dict, now: datetime) -> list[tuple[str, str]]:
    """(identity, line) for the 'big_days' section: big days coming up, just held, and the buzz around them."""
    today = local_today(companion, now)
    modern = modern_city(connection, companion)
    result = []
    hidden = CHILDS if withheld(connection) else ()
    ended = steps.apart(connection, companion) == 'ended'  # Broken up: no longer asking the user along.
    for row in rows(connection, companion['active_timeline_id'], ('planned', 'invited', 'declined', 'done')):
        if row['kind'] in hidden:
            continue
        gap = (date.fromisoformat(row['local_date']) - today).days
        if row['status'] != 'done' and gap >= 0:
            shown = {**row, 'invite': 0} if ended and row['status'] == 'planned' else row
            result.append((f"bigday:{row['id']}:{row['status']}", coming_line(shown, today)))
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
    gifts = [{'text': f"sent {row['gift']}" if row['kind'] in QUIET else f"bought {row['gift']} as a gift",
              'date': row['gift_on'], 'spend': '', 'cost': row['gift_cost'], 'for': 'funeral' if row['kind'] in QUIET else 'gift'}
             for row in many(connection, "SELECT * FROM big_days WHERE timeline_id=? AND status!='called_off' AND "
                             'gift_cost>0 AND gift_on>=? AND gift_on<=?', (timeline_id, start.isoformat(),
                                                                          day.isoformat()))]
    # Out of town (`away`): the fare there and back, the day before.
    fares = [{'text': f"travelled to {view(row)['details']['city']} for {title(view(row))}", 'date': row['set_off'],
              'spend': '', 'cost': row['fare'], 'for': 'trip'}
             for row in many(connection, "SELECT *, date(local_date, '-1 day') AS set_off, json_extract(details, "
                             "'$.fare') AS fare FROM big_days WHERE timeline_id=? AND status!='called_off' AND "
                             "json_extract(details, '$.fare')>0 AND date(local_date, '-1 day') BETWEEN ? AND ?",
                             (timeline_id, start.isoformat(), day.isoformat()))]
    return gifts + fares


# Branches (companion/timelines.py) ---------------------------------------------------------------------------------

# What a big day's source and details name, by table, matched to the fork's copies by what the copy keeps.
SUCCESSORS = {'storylines': ('story', 'started_on'), 'love_partners': ('name', 'met_on'),
              'life_chapters': ('kind', 'started_on'), 'circle_children': ('name', 'born_on'),
              'losses': ('name', 'died_on')}
ID = re.compile(r'\b[0-9a-f]{32}\b')


def successors(connection, parent_id: str, new_id: str, ids: dict) -> dict:
    """{parent's id: the copy's} for the circle people, storylines, partners, chapters, children and losses a big
    day's source names, so the copy finds it as its own and never plans it again."""
    found = dict(ids)
    for table, names in SUCCESSORS.items():
        columns = ', '.join(('created_at', *names))
        copies = {tuple(row.values())[1:]: row['id'] for row in many(
            connection, f'SELECT id, {columns} FROM {table} WHERE timeline_id=?', (new_id,))}
        for row in many(connection, f'SELECT id, {columns} FROM {table} WHERE timeline_id=?', (parent_id,)):
            if tuple(row.values())[1:] in copies:
                found[row['id']] = copies[tuple(row.values())[1:]]
    return found


def copied_status(row: dict, ids: dict, cutoff: str) -> tuple[str, str | None]:
    """(its status on the copy, the copy of the invitation): held by the fork, asked by then (and answered no by
    then), else still to come; anything after the fork is the copy's own."""
    message = ids.get(row['message_id'] or '')
    if row['status'] == 'called_off' or row['status'] == 'done' and row['local_date'] <= cutoff[:10]:
        return row['status'], message
    if not message:
        return 'planned', None
    return ('declined' if row['answered_at'] and row['answered_at'] < cutoff else 'invited'), message


def copy(connection, parent_id: str, new_id: str, ids: dict, cutoff: str) -> None:
    """Big days known by the fork carry over, whose they are and how far they had got by then (`copied_status`);
    anything the user was asked to after it is the copy's own."""
    found = successors(connection, parent_id, new_id, ids)
    for row in many(connection, 'SELECT * FROM big_days WHERE timeline_id=? AND created_at<=?',
                    (parent_id, f'{cutoff[:10]}T23:59:59')):
        status, message = copied_status(row, ids, cutoff)
        row_id = identifier()
        outing = copied_outing(connection, row, row_id, message, cutoff) if status == 'invited' else None
        connection.execute(
            'INSERT INTO big_days (id, timeline_id, kind, source, person_id, status, local_date, at_time, until_time, '
            'place, details, invite, invite_on, consequence_id, gift, gift_cost, gift_on, outfit, message_id, '
            'outing_id, with_user, answered_at, created_at, updated_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (row_id, new_id, row['kind'], ID.sub(lambda match: found.get(match.group(), match.group()), row['source']),
             found.get(row['person_id']) if row['person_id'] else None, status, row['local_date'], row['at_time'],
             row['until_time'], row['place'], ID.sub(lambda match: found.get(match.group(), match.group()),
                                                     row['details']), row['invite'], row['invite_on'], row['gift'],
             row['gift_cost'], row['gift_on'], row['outfit'], message, outing,
             row['with_user'] if status == 'done' else 0, row['answered_at'] if status == 'declined' else None,
             row['created_at'], row['updated_at']))


def copied_outing(connection, row: dict, row_id: str, message: str, cutoff: str) -> str | None:
    """The day as booked on the copy: the parent's outing (shown on the copy through its invitation), or, when it was
    called off after the fork, one of the copy's own."""
    outing = optional(connection, 'SELECT * FROM outings WHERE id=?', (row['outing_id'] or '',))
    if outing is None or outing['status'] != 'cancelled' or (outing['cancelled_at'] or '') < cutoff:
        return row['outing_id']
    copied = identifier()
    place = {**(decode(outing['place']) or {}), 'big_day': row_id}
    connection.execute(
        'INSERT INTO outings (id, companion_id, message_id, local_date, at_time, until_time, activity, asked_date, '
        'place, named, cost, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (copied, outing['companion_id'], message, outing['local_date'], outing['at_time'], outing['until_time'],
         outing['activity'], outing['asked_date'], encode(place), outing['named'], outing['cost'],
         outing['created_at']))
    return copied
