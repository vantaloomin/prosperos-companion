"""Meeting their people (Hit List #61, v0.13 Life Together): the family dinner or night out where the user meets the
companion's circle, and what each of them thinks of the user afterwards.

The app decides, the user overrides ("the world exists outside of User", Vanta 2026-10-08):

- Once a romance reaches the "meeting their people" step (companion/life/steps.py), a meet-up is planned a few days
  later with no question asked: dinner at their family's place when a parent or a sibling lives in town, else drinks
  with their friends. For a best friend, now and then (the engine's `people:night_out`, by the Relationship pace
  slider and how outgoing they are) a night out with their friends comes up too. A pair that has been together for
  years by how they know each other ("married for ten years") met everyone long ago: those first impressions are
  seeded straight away and nothing is planned.
- The companion invites the user in a first text (companion/life/openers.py) naming who, where and when; sending it
  books the outing (companion/life/outings.py), in person by v0.12's rules: never across a long distance, where it
  waits until they live in one city. Today's "Out together" lets the user call it off; called off, it is planned
  once more a few weeks later.
- Each person at the meet-up gets a seeded first impression of the user (the engine's `people:impression`: warm,
  lovely together, still making up their mind, protective or wary, by who they are to the companion and the drama
  level). It shows how they are at the table, and once the evening is over it is a circle-to-user pair that moves
  with what happens: plans kept warm it up, rough patches (companion/life/rough_patches.py) and called-off plans cool
  it. The companion passes it on now and then ("my mom keeps asking when you're coming back"), and it shows on the
  circle list.
- Afterwards someone they met may drop into a group chat with the companion as a v0.11 guest, by the Guests slider
  (companion/group_guests.py), knowing the user from that evening.

No new slider: the Relationship pace and Guests sliders decide. No model decides anything: the model only puts it in
words. Odds show under Hidden values ("Why it went this way").
"""
import json
import random
import re
from datetime import date, datetime, timedelta
from functools import cache

from companion import consequences
from companion.clock import parse, stamp, zone
from companion.database import decode, encode, identifier, many, optional
from companion.life import circle, outings, steps
from companion.world import catalog

ACTIVE = True
# The invitation as a first text; off in most tests (tests/conftest.py).
FIRST_TEXTS = True
# How many of their people come, and who: family for the dinner, friends for a night out.
MOST = 3
FAMILY = {'parent', 'sibling'}
FRIENDS = {'close friend', 'longtime friend', 'old friend from school', 'old classmate', 'friend', 'new friend',
           'roommate from years ago'}
# Days after the step before they invite the user; a meet-up that could not go out this long is dropped.
INVITE_AFTER = (2, 6)
LAPSE_DAYS = 45
# Called off: planned once more this many days later, and no more than this many times for the step.
AGAIN_AFTER = 21
STEP_TRIES = 2
# A best friend's night out with their friends: one roll in each window of this many days.
NIGHT_WINDOW = 60
NIGHT_AHEAD = (2, 10)
INVITE_HOURS = (10, 21)
# The meet-ups as outings, in outings.ACTIVITIES.
AT_FAMILY = 'meet-family'
OUT_WITH_FRIENDS = 'meet-friends'
MEETUPS = outings.MEETUPS
FAMILY_HOME = '~family'
FAMILY_SPOTS = ['around the dinner table', 'in the kitchen', 'in the living room', 'out on the back step']
# Preferred days: Sunday dinner with family, a Friday or Saturday night out with friends.
PREFERRED = {'family': (6, 5), 'friends': (4, 5)}

# First impressions (people:impression, in this order) and how warm each starts, from -2 (doubts) to 3 (the world of
# them). What moves it afterwards is checked once a week.
IMPRESSIONS = ('warm', 'smitten', 'curious', 'protective', 'wary')
START = {'warm': 2, 'smitten': 2, 'curious': 1, 'protective': 0, 'wary': -1}
LOW, HIGH = -2, 3
CHECK_EVERY = 7
KEPT_TO_WARM = 2
CALLED_OFF_TO_COOL = 2
# The circle list's short words, and the chat context's.
LABELS = {'warm': 'Liked you right away', 'smitten': 'Loves you two together', 'curious': 'Still making up their mind',
          'protective': 'Protective of {companion}', 'wary': 'Not sure about you yet'}
MOVED_LABELS = {'up': 'Warmed to you', 'high': 'Thinks the world of you', 'down': 'Cooled on you',
                'low': 'Has doubts about you'}
THINKS = {'warm': '{name} liked the user right away',
          'smitten': '{name} thinks you two are lovely together and keeps asking after the user',
          'curious': '{name} was friendly but is still making up their mind about the user',
          'protective': '{name} is protective of you and is watching how the user treats you',
          'wary': "{name} isn't sure about the user yet"}
MOVED_THINKS = {'up': '{name} has warmed to the user since', 'high': '{name} thinks the world of the user now',
                'down': '{name} has cooled on the user lately', 'low': '{name} has real doubts about the user now'}
# How they are at the table, while the meet-up is under way.
AT_TABLE = {'warm': '{name} is warm and easy with the user', 'smitten': '{name} keeps beaming at the two of you',
            'curious': '{name} is polite and asks the user a lot of questions',
            'protective': '{name} is a little protective of you and watches the user closely',
            'wary': '{name} is cool and reserved with the user'}


@cache
def bank() -> dict:
    return json.loads((catalog.DATA / 'their_people.json').read_text(encoding='utf-8'))


def local_today(companion: dict, now: datetime) -> date:
    return now.astimezone(zone(companion['version']['timezone'])).date()


def first(name: str) -> str:
    return name.split()[0] if name.split() else name


# Who comes -------------------------------------------------------------------------------------------------------

def group_of(role: str) -> str | None:
    kind = circle.role_kind(role)
    return 'family' if kind in FAMILY else 'friends' if kind in FRIENDS else None


def local_people(connection, companion: dict) -> list[dict]:
    """Their circle who live in town, closest first, as {id, name, role, kind, group, pronouns, neighborhood, city}."""
    result = []
    for row in circle.people(connection, companion['active_timeline_id']):
        details = decode(row['details']) or {}
        group = group_of(row['role'])
        if group and details.get('local', True):
            result.append({'id': row['id'], 'name': row['name'], 'role': row['role'],
                           'kind': circle.role_kind(row['role']), 'group': group,
                           'neighborhood': details.get('neighborhood') or '', 'city': details.get('city') or ''})
    return result


def guests_for(connection, companion: dict, kind: str) -> tuple[str, list[dict]]:
    """(family or friends, who comes): family when a parent or sibling lives in town, else their friends."""
    found = local_people(connection, companion)
    family = sorted((person for person in found if person['group'] == 'family'), key=lambda item: item['kind'] != 'parent')
    friends = [person for person in found if person['group'] == 'friends']
    if kind == 'family' and family:
        return 'family', family[:MOST]
    return 'friends', friends[:MOST]


def people_text(people: list[dict], yours: bool = True) -> str:
    """'your mom Ana, your dad Rui and your brother Leo' (or without 'your': 'Ana, Rui and Leo')."""
    names = [f"your {person['role']} {person['name']}" if yours else person['name'] for person in people]
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


# Planning a meet-up ----------------------------------------------------------------------------------------------

def meetups(connection, timeline_id: str, statuses: tuple[str, ...] | None = None, why: str | None = None) -> list[dict]:
    where_sql, values = 'timeline_id=?', [timeline_id]
    if statuses:
        where_sql += f" AND status IN ({','.join('?' * len(statuses))})"
        values += statuses
    if why:
        where_sql += ' AND why=?'
        values.append(why)
    return many(connection, f'SELECT * FROM people_meetups WHERE {where_sql} ORDER BY created_at', tuple(values))


def insert_meetup(connection, timeline_id: str, kind: str, why: str, due_on: date, timestamp: str,
                  consequence_id: str | None = None) -> dict:
    meetup_id = identifier()
    connection.execute('INSERT INTO people_meetups (id, timeline_id, kind, why, due_on, consequence_id, created_at) '
                       'VALUES (?, ?, ?, ?, ?, ?, ?)',
                       (meetup_id, timeline_id, kind, why, due_on.isoformat(), consequence_id, timestamp))
    return optional(connection, 'SELECT * FROM people_meetups WHERE id=?', (meetup_id,))


def advance(connection, companion: dict, now: datetime) -> None:
    """Once a day: keep meet-ups in step with their outings, let impressions move, and plan what is due. Cheap: no
    model."""
    if not ACTIVE or not companion.get('active_timeline_id'):
        return
    follow(connection, companion, now)
    drift(connection, companion, now)
    found = steps.state(connection, companion, now, write=False)
    if found is None:
        return
    if found['ladder'] == 'romance':
        plan_for_step(connection, companion, found, now)
    elif steps.index_of('friendship', found['step']) >= steps.index_of('friendship', 'best_friends'):
        plan_night_out(connection, companion, now)


def their_people_step(found: dict) -> dict | None:
    """The "meeting their people" step once reached, with how and when."""
    if steps.index_of('romance', found['step']) < steps.index_of('romance', 'their_people'):
        return None
    return next((item for item in found['steps'] if item['step'] == 'their_people'), None)


def plan_for_step(connection, companion: dict, found: dict, now: datetime) -> dict | None:
    """At the step, a meet-up a few days on; a pair that knows each other from way back met everyone long ago."""
    reached = their_people_step(found)
    timeline_id = companion['active_timeline_id']
    if reached is None or meetups(connection, timeline_id, ('planned', 'booked', 'done'), 'step'):
        return None
    if reached['how'] == 'history':
        known_already(connection, companion, now)
        return None
    if len(meetups(connection, timeline_id, why='step')) >= STEP_TRIES:
        return None
    kind, people = guests_for(connection, companion, 'family')
    if not people:
        return None
    today = local_today(companion, now)
    low, high = INVITE_AFTER
    offset = random.Random(f"{timeline_id}:their-people:invite").randint(low, high)
    due = max(date.fromisoformat(reached['on']) + timedelta(days=offset), today)
    if meetups(connection, timeline_id, ('dropped',), 'step'):
        due = today + timedelta(days=AGAIN_AFTER)
    return insert_meetup(connection, timeline_id, kind, 'step', due, stamp(now))


def plan_night_out(connection, companion: dict, now: datetime) -> dict | None:
    """Now and then a best friend has the user out with their friends: one roll a window, by the pace slider."""
    timeline_id = companion['active_timeline_id']
    if not steps.pace(connection) or meetups(connection, timeline_id, ('planned', 'booked')):
        return None
    today = local_today(companion, now)
    window = (today.toordinal() + random.Random(f'night-out:{timeline_id}').randrange(NIGHT_WINDOW)) // NIGHT_WINDOW
    subject = f'people:{timeline_id}:night_out:{window}'
    if consequences.recorded(connection, subject, 'people:night_out'):
        return None
    _kind, people = guests_for(connection, companion, 'friends')
    if not people:
        return None
    from companion.memory import closeness
    from companion.world import personality
    definition = companion['version']['definition']
    levels = personality.levels_of(definition.get('personality_sliders') or {})
    outcome = decide(connection, companion, 'people:night_out', subject,
                     {'pace': steps.pace(connection), 'social': levels.get('social', 1),
                      'closeness': closeness.state(connection, companion, now)['level']},
                     {'name': first(definition['name']), 'a': 'their friends', 'b': ''}, now)
    if outcome['picked'] != 1:
        return None
    offset = random.Random(f'{subject}:when').randint(*NIGHT_AHEAD)
    return insert_meetup(connection, timeline_id, 'friends', 'friends', today + timedelta(days=offset), stamp(now),
                         outcome['id'])


def decide(connection, companion: dict, choice: str, subject: str, facts: dict, names: dict, now: datetime) -> dict:
    table = consequences.tables()[choice]
    return consequences.decide(connection, timeline_id=companion['active_timeline_id'], choice=choice, subject=subject,
                               facts=facts, names=names,
                               labels=[option['label'].format(**names) for option in table['options']],
                               day=local_today(companion, now).isoformat(), timestamp=stamp(now))


def known_already(connection, companion: dict, now: datetime) -> None:
    """A couple together for years by how they know each other: their family and friends know the user already, so
    each gets an impression from back then, with nothing planned."""
    for person in local_people(connection, companion)[:MOST * 2]:
        impress(connection, companion, person, None, now, met_on='before')


# The invitation (a first text, companion/life/openers.py) --------------------------------------------------------

def preferred_day(kind: str, today: date) -> date:
    """The next Sunday for family (Saturday if Sunday is too soon), the next Friday for friends, at least two days on."""
    start = today + timedelta(days=2)
    return min(start + timedelta(days=(weekday - start.weekday()) % 7) for weekday in PREFERRED[kind])


def family_place(people: list[dict], meetup_id: str) -> dict:
    """The family home the dinner is at: a parent's, else a sibling's ("Ana and Rui's place")."""
    host = people[0]
    parents = [person for person in people if person['kind'] == 'parent']
    owners = parents[:2] if host['kind'] == 'parent' else [host]
    name = ' and '.join(first(person['name']) for person in owners) + "'s place"
    return {'id': FAMILY_HOME, 'name': name, 'kind': 'family-home', 'neighborhood': host['neighborhood'],
            'summary': '', 'cost': '', 'cuisine': '', 'city': host['city'], 'city_id': '', 'spots': list(FAMILY_SPOTS),
            'host': host['id'], 'owners': [person['id'] for person in owners]}


def their_words_for_place(place: dict, people: list[dict]) -> str:
    """How the companion says where: "my parents' place", "my mom's place", "The Owl Bar"."""
    if place['kind'] != 'family-home':
        return place['name']
    owners = [person for person in people if person['id'] in place.get('owners', ())]
    if len(owners) == 2:
        return "my parents' place"
    return f"my {owners[0]['role']}'s place" if owners else place['name']


def meet_due(connection, companion: dict, now: datetime) -> list:
    """A planned meet-up whose day has come: the companion invites the user, naming who, where and when."""
    from companion.life.openers import Trigger
    if not ACTIVE or not FIRST_TEXTS or not companion.get('active_timeline_id'):
        return []
    local = now.astimezone(zone(companion['version']['timezone']))
    if not INVITE_HOURS[0] <= local.hour < INVITE_HOURS[1]:
        return []
    from companion.life import long_distance
    row = next((item for item in meetups(connection, companion['active_timeline_id'], ('planned',))
                if item['due_on'] <= local.date().isoformat()), None)
    if row is None or long_distance.far(connection, companion):
        return []
    found = proposal(connection, companion, row, local)
    if found is None:
        return []
    activity, day, at, place, people = found
    words = their_words_for_place(place, people)
    names = people_text(people, yours=False)
    who = people_text(people)
    thing = 'dinner' if activity == AT_FAMILY else 'drinks'
    first_time = row['why'] == 'step'
    reason = (f"You've arranged for the user to {'meet' if first_time else 'come out with'} {who}: {thing} at "
              f"{words} on {day:%A} at {at}. Tell them in your own words, naming who will be there, the place, the day "
              f"and the time{', a little nervous and happy about it' if first_time else ''}.")
    template = agree(random.Random(f"{row['id']}:line").choice(bank()[row['kind']]), len(people) == 1).format(
        people=names, day=f'{day:%A}', time=clock_text(at), place=words)
    return [Trigger(f"meet:{row['id']}", 'meet_people', reason, template,
                    (row['id'], activity, day.isoformat(), at, place['id'], ','.join(person['id'] for person in people)))]


# A verb right after {people} in a line from the bank, said for one person.
ONE = {'are': 'is', 'have': 'has', 'want': 'wants', 'keep': 'keeps', 'insist': 'insists', 'ask': 'asks', 'were': 'was'}


def agree(template: str, single: bool) -> str:
    """"{people} are excited" for one person: "{people} is excited"."""
    if not single:
        return template
    return re.sub(r'\{people\} (\w+)\b', lambda found: f"{{people}} {ONE.get(found.group(1), found.group(1))}", template)


def clock_text(at: str) -> str:
    """'7', '6:30' on a twelve-hour clock, as a text says it."""
    hour, minute = int(at[:2]), at[3:]
    return f"{hour % 12 or 12}{'' if minute == '00' else ':' + minute}"


def proposal(connection, companion: dict, row: dict, local: datetime) -> tuple | None:
    """(activity, day, at, place, people) for the meet-up: a free evening near the preferred day."""
    kind, people = guests_for(connection, companion, row['kind'])
    if not people:
        return None
    activity = AT_FAMILY if kind == 'family' else OUT_WITH_FRIENDS
    wanted = {'activity': activity, 'day': preferred_day(kind, local.date()), 'at': None, 'firm': False}
    found = outings.when_free(connection, companion, wanted, local)
    if not found:
        return None
    day, at = found
    if activity == AT_FAMILY:
        return activity, day, at, family_place(people, row['id']), people
    definition = companion['version']['definition']
    data = outings.city_data(connection, definition)
    if not data:
        return None
    cost, affordable = outings.bill(definition, activity, day)
    item = outings.pick_place(data, activity, day, at, definition, f"meet:{row['id']}", not affordable)
    if item is None:
        return None
    return activity, day, at, outings.place_view(item, data), people


def settle(connection, companion: dict, message: dict, trigger, timestamp: str) -> dict | None:
    """The invitation went out: the outing is booked to it, and each person gets their first impression."""
    from companion.life import together
    meetup_id, activity, day_text, at, place_id, person_ids = trigger.sources
    row = optional(connection, "SELECT * FROM people_meetups WHERE id=? AND status='planned'", (meetup_id,))
    if row is None:
        return None
    day, now = date.fromisoformat(day_text), parse(timestamp)
    everyone = {person['id']: person for person in local_people(connection, companion)}
    people = [everyone[person_id] for person_id in person_ids.split(',') if person_id in everyone]
    if not people or outings.taken(connection, companion, day):
        return None
    if activity == AT_FAMILY:
        place, cost = family_place(people, meetup_id), 0.0
    else:
        data = outings.city_data(connection, companion['version']['definition'])
        item = next((place for place in (data or {}).get('places', ()) if place['id'] == place_id), None)
        if item is None:
            return None
        place = outings.place_view(item, data)
        bill, affordable = outings.bill(companion['version']['definition'], activity, day)
        cost = bill if affordable else round(bill * 0.6, 2)
    place |= {'people': [{'id': person['id'], 'name': person['name'], 'role': person['role']} for person in people],
              'meetup': meetup_id, 'first': row['why'] == 'step'}
    outing = together.insert(connection, companion, message['id'], activity, place, day, at,
                             outings.until(at, activity), None, timestamp)
    # No photo of it: the image model can't place the user at a family table (images/prompts.py).
    connection.execute('UPDATE outings SET cost=?, photo_tried=1 WHERE id=?', (cost, outing['id']))
    connection.execute("UPDATE people_meetups SET status='booked', outing_id=?, people=?, settled_at=? WHERE id=?",
                       (outing['id'], encode([person['id'] for person in people]), timestamp, meetup_id))
    for person in people:
        impress(connection, companion, person, meetup_id, now)
    return outings.get(connection, outing['id'])


SETTLES = ('meet_people',)


# First impressions -------------------------------------------------------------------------------------------------

def impress(connection, companion: dict, person: dict, meetup_id: str | None, now: datetime,
            met_on: str | None = None) -> dict:
    """Their first impression of the user, decided once: someone who has met the user already keeps theirs."""
    timeline_id = companion['active_timeline_id']
    found = optional(connection, 'SELECT * FROM people_impressions WHERE timeline_id=? AND person_id=?',
                     (timeline_id, person['id']))
    if found:
        return found
    from companion.memory import closeness
    definition = companion['version']['definition']
    romance = steps.ladder_of(definition) == 'romance'
    facts = {'kind': circle.role_kind(person['role']) if person['group'] == 'family' else 'friend',
             'drama': steps.drama(connection), 'romance': int(romance),
             'closeness': closeness.state(connection, companion, now)['level']}
    names = {'name': first(person['name']), 'a': first(person['name']), 'b': first(definition['name'])}
    outcome = decide(connection, companion, 'people:impression', f"people:{timeline_id}:{person['id']}", facts, names,
                     now)
    kind = IMPRESSIONS[outcome['picked']]
    day = local_today(companion, now).isoformat()
    connection.execute('INSERT INTO people_impressions (id, timeline_id, person_id, meetup_id, impression, warmth, '
                       'met_on, checked_on, moves, consequence_id, created_at, updated_at) '
                       "VALUES (?, ?, ?, ?, ?, ?, ?, ?, '[]', ?, ?, ?)",
                       (identifier(), timeline_id, person['id'], meetup_id, kind, START[kind], met_on,
                        day if met_on else None, outcome['id'], stamp(now), stamp(now)))
    return optional(connection, 'SELECT * FROM people_impressions WHERE timeline_id=? AND person_id=?',
                    (timeline_id, person['id']))


def follow(connection, companion: dict, now: datetime) -> None:
    """Meet-ups follow their outings: over (everyone at it has now met the user), called off (planned once more,
    a few weeks on), or a planned one that could not go out in all this time (dropped)."""
    timeline_id = companion['active_timeline_id']
    today = local_today(companion, now)
    timestamp = stamp(now)
    for row in meetups(connection, timeline_id, ('planned', 'booked')):
        if row['status'] == 'planned':
            if (today - date.fromisoformat(row['due_on'])).days > LAPSE_DAYS:
                connection.execute("UPDATE people_meetups SET status='dropped', settled_at=? WHERE id=?",
                                   (timestamp, row['id']))
            continue
        outing = optional(connection, 'SELECT * FROM outings WHERE id=?', (row['outing_id'],))
        state = outings.state(outings.view(outing), companion['version']['timezone'], now) if outing else 'cancelled'
        if state == 'done':
            connection.execute("UPDATE people_meetups SET status='done', settled_at=? WHERE id=?", (timestamp, row['id']))
            met_again(connection, timeline_id, row, outing['local_date'], now)
        elif state == 'cancelled':
            connection.execute("UPDATE people_meetups SET status='dropped', settled_at=? WHERE id=?",
                               (timestamp, row['id']))
            connection.execute('DELETE FROM people_impressions WHERE meetup_id=? AND met_on IS NULL', (row['id'],))


def met_again(connection, timeline_id: str, row: dict, day: str, now: datetime) -> None:
    """Everyone at it has met the user now; someone who had met them before warms a little more."""
    for person_id in decode(row['people']) or []:
        found = optional(connection, 'SELECT * FROM people_impressions WHERE timeline_id=? AND person_id=?',
                         (timeline_id, person_id))
        if found is None:
            continue
        if found['met_on'] is None:
            connection.execute('UPDATE people_impressions SET met_on=?, checked_on=?, updated_at=? WHERE id=?',
                               (day, day, stamp(now), found['id']))
        elif found['meetup_id'] != row['id']:
            move(connection, found, 1, 'saw you again', day, now)


def move(connection, row: dict, by: int, why: str, day: str, now: datetime) -> None:
    warmth = max(LOW, min(HIGH, row['warmth'] + by))
    if warmth == row['warmth']:
        return
    moves = [*(decode(row['moves']) or []), {'on': day, 'by': by, 'why': why}][-12:]
    connection.execute('UPDATE people_impressions SET warmth=?, moves=?, updated_at=? WHERE id=?',
                       (warmth, encode(moves), stamp(now), row['id']))
    row.update({'warmth': warmth, 'moves': encode(moves)})


def drift(connection, companion: dict, now: datetime) -> None:
    """Once a week each impression moves with what happened since: plans kept with the companion warm it, a big rough
    patch the user started or plans called off cool it, more so for family and the protective or wary."""
    timeline_id = companion['active_timeline_id']
    today = local_today(companion, now)
    for row in many(connection, 'SELECT * FROM people_impressions WHERE timeline_id=? AND met_on IS NOT NULL',
                    (timeline_id,)):
        since = row['checked_on'] or row['met_on']
        if (today - date.fromisoformat(since)).days < CHECK_EVERY:
            continue
        happened = since_then(connection, companion, since, today.isoformat())
        person = optional(connection, 'SELECT role FROM circle_people WHERE id=?', (row['person_id'],))
        touchy = row['impression'] in ('protective', 'wary') or (person and group_of(person['role']) == 'family')
        if happened['kept'] >= KEPT_TO_WARM:
            move(connection, row, 1, 'plans kept', today.isoformat(), now)
        if happened['patches'] and (touchy or happened['patches'] > 1):
            move(connection, row, -1, 'a rough patch', today.isoformat(), now)
        elif happened['called_off'] >= CALLED_OFF_TO_COOL and touchy:
            move(connection, row, -1, 'plans called off', today.isoformat(), now)
        connection.execute('UPDATE people_impressions SET checked_on=? WHERE id=?', (today.isoformat(), row['id']))


def since_then(connection, companion: dict, since: str, today: str) -> dict:
    """Plans kept and called off with the companion, and big rough patches the user started, between two days."""
    rows = many(connection, "SELECT status, activity, cancelled_at, local_date FROM outings WHERE companion_id=? AND "
                'local_date>? AND local_date<=?', (companion['id'], since, today))
    kept = sum(1 for row in rows if row['status'] == 'done' and row['activity'] not in MEETUPS)
    called_off = sum(1 for row in rows if row['status'] == 'cancelled')
    patches = 0
    if optional(connection, "SELECT name FROM sqlite_master WHERE type='table' AND name='rough_patches'"):
        patches = len(many(connection, "SELECT id FROM rough_patches WHERE timeline_id=? AND size='big' AND fault='user' "
                           'AND started_on>? AND started_on<=?', (companion['active_timeline_id'], since, today)))
    return {'kept': kept, 'called_off': called_off, 'patches': patches}


def moved(row: dict) -> str | None:
    """'up', 'high', 'down' or 'low' when it has moved from where it started; None while it hasn't."""
    if row['warmth'] >= HIGH and START[row['impression']] < HIGH:
        return 'high'
    if row['warmth'] <= LOW and START[row['impression']] > LOW:
        return 'low'
    change = row['warmth'] - START[row['impression']]
    return 'up' if change > 0 else 'down' if change < 0 else None


def label(row: dict, companion_name: str) -> str:
    way = moved(row)
    return MOVED_LABELS[way] if way else LABELS[row['impression']].format(companion=first(companion_name))


def thinks(row: dict, name: str) -> str:
    way = moved(row)
    return (MOVED_THINKS[way] if way else THINKS[row['impression']]).format(name=first(name))


# What the chat context says ------------------------------------------------------------------------------------------

def long_date(day: str) -> str:
    found = date.fromisoformat(day)
    return f'{found.day} {found:%B}'


def met(connection, timeline_id: str) -> list[dict]:
    """Everyone who has met the user, with their circle row and the outing they met at."""
    rows = many(connection, 'SELECT impression.*, person.name, person.role, person.status AS person_status, '
                'meetup.outing_id FROM people_impressions impression JOIN circle_people person ON '
                'person.id=impression.person_id LEFT JOIN people_meetups meetup ON meetup.id=impression.meetup_id '
                'WHERE impression.timeline_id=? AND impression.met_on IS NOT NULL ORDER BY person.ordinal',
                (timeline_id,))
    return [row for row in rows if row['person_status'] == 'active']


def where_met(connection, row: dict) -> str:
    outing = optional(connection, 'SELECT activity, place FROM outings WHERE id=?', (row['outing_id'] or '',))
    if not outing:
        return ''
    place = decode(outing['place'])
    return f"dinner at {place['name']}" if outing['activity'] == AT_FAMILY else f"drinks at {place['name']}"


def context_lines(connection, companion: dict) -> list[tuple[str, str]]:
    """(identity, line) for the 'their_people' section: what each person who has met the user thinks of them."""
    if not companion.get('active_timeline_id'):
        return []
    result = []
    for row in met(connection, companion['active_timeline_id']):
        who = f"{row['name']} (your {row['role']})"
        if row['met_on'] == 'before':
            text = f'- {who} has known the user for a long time: {thinks(row, row["name"])}.'
        else:
            at = where_met(connection, row)
            text = f"- {who} met the user on {long_date(row['met_on'])}{', at ' + at if at else ''}: " \
                   f"{thinks(row, row['name'])}."
        result.append((f"their-people:{row['id']}:{row['warmth']}", text))
    return result


def offer(packet, connection, companion: dict, group=None) -> None:
    """Adds the 'their_people' section, in a 1:1 chat."""
    if group is not None:
        return
    for identity, text in context_lines(connection, companion):
        packet.offer('their_people', identity, text)


def is_meetup(outing: dict) -> bool:
    return outing['activity'] in MEETUPS


def what(outing: dict) -> str:
    """'dinner at Ana and Rui's place with your mom Ana and your dad Rui, so the user can meet them'."""
    place = outing['place']
    people = people_text(place.get('people') or [])
    thing = 'dinner' if outing['activity'] == AT_FAMILY else 'drinks'
    if outing['activity'] == OUT_WITH_FRIENDS:
        area = f" in {place['neighborhood']}" if place.get('neighborhood') else ''
        where = f"{place['name']} ({place['kind']}{area})"
    else:
        where = place['name']
    return f"{thing} at {where} with {people}" + (', so the user can meet them' if place.get('first') else '')


def scene(connection, companion: dict, outing: dict, spot: str | None) -> str:
    """Being at the meet-up together, in person, with their people in the room and how each is with the user."""
    place = outing['place']
    found = {row['person_id']: row for row in many(
        connection, 'SELECT * FROM people_impressions WHERE timeline_id=?', (companion['active_timeline_id'],))}
    people = place.get('people') or []
    moods = [AT_TABLE[found[person['id']]['impression']].format(name=first(person['name']))
             for person in people if person['id'] in found]
    parts = [f"Right now you and the user are out together, in person: {what(outing)}, until about "
             f"{outing['until_time']}.",
             f"Here with you: {people_text(people)}. Nobody else is there.",
             'It is the first time they are meeting the user.' if place.get('first') else '',
             f"How it is going: {'; '.join(moods)}." if moods else '',
             f'You are {spot}.' if spot else '',
             'Talk as if you are there together, face to face, not texting: what you say and do in the room. The '
             'others are in the room too: you can say briefly what they say or do, but you speak only as yourself.']
    return '- ' + ' '.join(part for part in parts if part)


def doing(outing: dict) -> str:
    """'had dinner at Ana and Rui's place with you, Ana and Rui'."""
    people = [first(person['name']) for person in outing['place'].get('people') or []]
    company = ', '.join(['you', *people[:-1]]) + f' and {people[-1]}' if people else 'you'
    thing = 'had dinner' if outing['activity'] == AT_FAMILY else 'went out for drinks'
    return f"{thing} at {outing['place']['name']} with {company}"


def memory_text(outing: dict) -> dict:
    day = date.fromisoformat(outing['local_date'])
    people = people_text(outing['place'].get('people') or [], yours=False)
    met_word = 'met' if outing['place'].get('first') else 'saw'
    subject = f"The user {met_word} {people}"
    return {'subject': subject, 'value': f"{subject} over {what(outing).split(' with ')[0]} on {day:%A, %B} {day.day}."}


# The circle list and Hidden values --------------------------------------------------------------------------------------

def for_circle(connection, companion: dict, show_odds: bool) -> dict[str, dict]:
    """What each person who has met the user (or is about to) thinks of them, by person id, for the circle list."""
    if not companion.get('active_timeline_id'):
        return {}
    name = companion['version']['definition']['name']
    result = {}
    for row in many(connection, 'SELECT * FROM people_impressions WHERE timeline_id=?', (companion['active_timeline_id'],)):
        result[row['person_id']] = {
            'met_on': None if row['met_on'] in (None, 'before') else row['met_on'], 'before': row['met_on'] == 'before',
            'meeting': row['met_on'] is None, 'impression': row['impression'], 'warmth': row['warmth'],
            'label': label(row, name), 'consequence_id': row['consequence_id'] if show_odds else None}
    return result


def change(connection, companion: dict, consequence_id: str, option: int, now: datetime) -> dict:
    """The user makes a decision go another way: a different first impression (keeping how far it has moved since),
    or a best friend's night out planned or called off while nothing is booked."""
    outcome = consequences.change(connection, consequence_id, option, stamp(now))
    timeline_id = companion['active_timeline_id']
    if outcome['choice'] == 'people:impression':
        row = optional(connection, 'SELECT * FROM people_impressions WHERE consequence_id=?', (consequence_id,))
        if row:
            kind = IMPRESSIONS[option]
            warmth = max(LOW, min(HIGH, START[kind] + row['warmth'] - START[row['impression']]))
            connection.execute('UPDATE people_impressions SET impression=?, warmth=?, updated_at=? WHERE id=?',
                               (kind, warmth, stamp(now), row['id']))
    elif outcome['choice'] == 'people:night_out':
        row = optional(connection, 'SELECT * FROM people_meetups WHERE consequence_id=?', (consequence_id,))
        if option == 1 and row is None:
            insert_meetup(connection, timeline_id, 'friends', 'friends', local_today(companion, now) + timedelta(days=2),
                          stamp(now), consequence_id)
        elif option == 0 and row and row['status'] == 'planned':
            connection.execute("UPDATE people_meetups SET status='dropped', settled_at=? WHERE id=?",
                               (stamp(now), row['id']))
    return consequences.by_id(connection, consequence_id)


# Group chats (companion/group_guests.py) --------------------------------------------------------------------------------

def met_people(connection, companion: dict) -> dict[str, dict]:
    """Circle people who have met the user and like them well enough to drop into a chat, by person id."""
    if not companion.get('active_timeline_id'):
        return {}
    return {row['person_id']: row for row in met(connection, companion['active_timeline_id']) if row['warmth'] >= 1}


def guest_line(connection, person_id: str, timeline_id: str) -> str | None:
    """A guest who has met the user in person: when and where, instead of "no history outside this chat"."""
    row = next((item for item in met(connection, timeline_id) if item['person_id'] == person_id), None)
    if row is None:
        return None
    if row['met_on'] == 'before':
        when = 'You have known the user for a long time, through the person who brought you in.'
    else:
        at = where_met(connection, row)
        when = f"You have met the user in person, on {long_date(row['met_on'])}{' at ' + at if at else ''}."
    return (f"{when} {GUEST_FEELS[moved(row) or row['impression']]} Anything else you did together beyond that and "
            "this chat didn't happen as far as you know.")


GUEST_FEELS = {'warm': 'You liked them right away.', 'smitten': 'You think they and your person are lovely together.',
               'curious': 'You are still making up your mind about them.',
               'protective': 'You are protective of the person who brought you in, and you watch how they treat them.',
               'wary': "You aren't sure about them yet.", 'up': 'You have warmed to them since.',
               'high': 'You think the world of them.', 'down': 'You have cooled on them lately.',
               'low': 'You have real doubts about them.'}
