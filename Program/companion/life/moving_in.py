"""Moving in together (Hit List #62, v0.13 Life Together): one home for a couple, once they reach the moving-in step.

The step itself is the steps ladder's (companion/life/steps.py): the companion brings it up, or the user does, and yes
reaches it. From then on the app decides the rest ("the world exists outside of User", Vanta 2026-10-08), and the user
can make it go another way under Hidden values:

- In the same city, whose place: the user's, theirs, or a new one, from how big their place is, what each costs, how
  far each is from their work, and whose pets live where (choice `moving_in:where`). The move takes a few weeks.
- In different cities, who moves, as the companion's question and never forced on the user (Vanta 2026-10-13, choice
  `moving_in:who`): they move to the user's city, odds from how rooted they are (family and friends around them, a job
  that is hard to leave), and it is a life chapter like any other (a new job in the user's city, the coworkers left
  behind, the user's city's clock); or they ask the user to move to theirs, and the user changes their home city
  themselves on the persona form. Until one of them moves they stay long distance.

Once moved in there is one shared home: the companion's home on the Character page is it, the user's neighbourhood is
its neighbourhood (`shared_home`, read by companion/life/where.py), and rent is split through companion/life/money.py
(`split`). Chores and cooking go by whose turn it is (`turn`, rules only). Evenings when they are both home count as
Together (companion/life/together.py), so the chat is written in person then and texted while either of them is out;
the user saying they are out, or Heading out on the chat strip, makes it texting for a while (`out_until`).

Moving out (`move_out`) comes after a breakup (Breaks and breakups) or the step taken back on the Character page: the one
who moved in moves out, picked by rules, and stays in town. No model decides anything: the model only puts it in words.

Sharing a home (Vanta's item 1, v0.13): when another romance companion's moving-in step is reached while the user lives
with someone (or is about to), the newcomer would move into that home. Everyone involved says whether they are open to
sharing it, one roll each in the consequence engine (choice `moving_in:share`, from an open-relationship interest, their
personality sliders, a trait like jealous or possessive, a rough patch over the user seeing someone else, the drama
level), and the one already living there hears about it (a line in the chat, and a first text). Everyone open: the
newcomer moves in on their own moving day, into the same home (`household`, grown to fit everyone: `grow`), the rent
split among everyone and the chores taking turns among everyone. Anyone not open: the move waits, asked again some
weeks later, and a small rough patch can open with the one who isn't ready. The user can make any of the rolls go the other way under Hidden values.
"""
import random
import re
from datetime import date, datetime, timedelta

from companion import consequences
from companion.clock import parse, stamp, zone
from companion.database import decode, encode, identifier, many, optional
from companion.errors import require
from companion.life import home, money, steps, where
from companion.world import generators

ACTIVE = True
STEP = 'moving_in'
PLACES = ('yours', 'theirs', 'new')  # moving_in:where, in this order.
MOVERS = ('them', 'you')  # moving_in:who, in this order.
# Days from deciding until the move: within a city, and to another city (notice at work, packing a life up).
SAME_CITY_DAYS = (10, 28)
OTHER_CITY_DAYS = (30, 60)
# Evenings at home together, from this time until they go to bed.
EVENING = '18:00'
# "I'm out" in the chat, or Heading out on the strip: texting for this long, unless they say they're home sooner.
OUT_FOR = timedelta(hours=3)
# Living together, they don't ring the moment the user steps out of the door.
JUST_OUT = timedelta(hours=1)
# How long the chat context keeps moving day, and a move out.
TOLD_DAYS = 3
UNITS = ('shared', 'studio', 'one_bedroom', 'two_bedroom')
# Sharing a home: the choice, how long a "not yet" holds before they are asked again, and traits that speak against it.
SHARE = 'moving_in:share'
SHARE_AGAIN = 45
MINDS_SHARING = re.compile(r'jealous|possessive|insecure|clingy|territorial', re.IGNORECASE)
FIRST_TEXTS = True
SETTLES = ('move_share',)
COUNTS = {2: 'two', 3: 'three', 4: 'four', 5: 'five'}
TASKS = ('cooking', 'dishes', 'laundry', 'tidying')
# Upkeep's areas of housework (companion/life/upkeep.py), as the chores they take turns at.
UPKEEP = {'laundry': 'laundry', 'dishes': 'dishes', 'clutter': 'tidying'}

# The user saying they are out, or back home.
OUT = re.compile(r"\b(?:i'?m|i am|im) (?:(?:still )?(?:out|at work|at the office|at the gym|at class|at the store|"
                 r"working late|out with)|heading out|going out|off out)\b|\b(?:heading|headed|going) out\b|\bon my way "
                 r"(?:out|to work)\b|\bwon'?t be home (?:until|till|for)\b", re.IGNORECASE)
HOME = re.compile(r"\b(?:i'?m|i am|im) (?:back )?home\b|\b(?:just )?got (?:back )?home\b|\bback home now\b|"
                  r"\bwalking in the door\b", re.IGNORECASE)
# The user saying a chore was left undone: on a day it was their turn, a small rough patch can start
# (companion/life/rough_patches.py `friction`, which rolls whether it does).
SKIPPED = re.compile(r"\b(?:forgot|didn'?t (?:get to|do|get round to)|did not do|haven'?t done|never did|skipped|"
                     r"left)\b[\w' ]{0,20}?\b(?P<task>cook(?:ing)?|dinner|dishes|washing[- ]up|laundry|tidy(?:ing)?(?: up)?|"
                     r"clean(?:ing)? up)\b", re.IGNORECASE)
SKIPPED_TASKS = (('cook', 'cooking'), ('dinner', 'cooking'), ('dishes', 'dishes'), ('washing', 'dishes'),
                 ('laundry', 'laundry'), ('tidy', 'tidying'), ('clean', 'tidying'))


# Reading -------------------------------------------------------------------------------------------------------

def latest(connection, timeline_id: str) -> dict | None:
    return optional(connection, 'SELECT * FROM moving_in WHERE timeline_id=? ORDER BY created_at DESC LIMIT 1',
                    (timeline_id,))


def current(connection, timeline_id: str) -> dict | None:
    """The plan or the shared home in place (moving, waiting for the user to move, or moved in)."""
    row = latest(connection, timeline_id)
    return row if row and row['status'] != 'moved_out' else None


def living(connection, companion: dict, day: date | None = None) -> dict | None:
    """The shared home, when they live together (on `day`, else now)."""
    row = current(connection, companion.get('active_timeline_id') or '')
    if not row or row['status'] != 'moved':
        return None
    return row if day is None or row['moved_on'] <= day.isoformat() else None


def moved_apart(connection, companion: dict) -> bool:
    """They lived together and don't now (the user moved to another city, say), with no new move under way."""
    row = latest(connection, companion.get('active_timeline_id') or '')
    return bool(row and row['status'] == 'moved_out' and row['moved_on'])


def shared_home(connection, city_id: str) -> str | None:
    """The neighbourhood of the home the user shares with a companion in their city, for where.py; None otherwise."""
    row = optional(connection, "SELECT m.neighbourhood FROM moving_in m JOIN companions c ON c.active_timeline_id="
                   "m.timeline_id WHERE m.status='moved' AND m.city_id=? ORDER BY m.moved_on DESC LIMIT 1", (city_id,))
    return row['neighbourhood'] if row and row['neighbourhood'] else None


def local_today(companion: dict, now) -> date:
    return now.astimezone(zone(companion['version']['timezone'])).date()


def reached(connection, companion: dict, now) -> bool:
    found = steps.state(connection, companion, now, write=False)
    return bool(found and found['ladder'] == 'romance'
                and steps.index_of('romance', found['step']) >= steps.index_of('romance', STEP))


# Deciding where, or who moves -----------------------------------------------------------------------------------

def begin(connection, companion: dict, now, message_id: str | None = None) -> dict | None:
    """Once the moving-in step is reached: whose place in the same city, or who moves across the distance."""
    if not ACTIVE or not companion.get('active_timeline_id') or not reached(connection, companion, now):
        return None
    step = step_row(connection, companion)
    last = latest(connection, companion['active_timeline_id'])
    if last and (last['status'] != 'moved_out' or not step or step['reached_on'] <= last['out_on']):
        return None  # Under way, or moved out since the step was reached: it takes the step reached anew.
    if step and step['how'] in ('history', 'start'):
        return already(connection, companion, step, now)
    mates = housemates(connection, companion)
    if mates:
        return decide_share(connection, companion, mates, now, message_id)
    return decide_fresh(connection, companion, now, message_id)


def decide_fresh(connection, companion: dict, now, message_id: str | None = None) -> dict:
    between = where.between(connection, companion['version']['definition'])
    if between.long_distance and between.your_city:
        return decide_who(connection, companion, between, now, message_id)
    return decide_where(connection, companion, between, now, message_id)


def step_row(connection, companion: dict) -> dict | None:
    return next((row for row in steps.reached(connection, companion['active_timeline_id'], 'romance')
                 if row['step'] == STEP), None)


def already(connection, companion: dict, step: dict, now) -> dict | None:
    """A couple who lived together before the app knew them ("we share a flat"): their place is the shared home, since
    the step's day, with nothing decided and no moving day. Not when the user's home is in another city."""
    timeline_id = companion['active_timeline_id']
    between = where.between(connection, companion['version']['definition'])
    if between.long_distance:
        return None
    city, hood = place_for(connection, companion, 'theirs', between, local_today(companion, now))
    connection.execute(
        'INSERT INTO moving_in (id, timeline_id, plan, status, city_id, neighbourhood, decided_on, move_on, moved_on, '
        "created_at) VALUES (?, ?, 'theirs', 'moved', ?, ?, ?, ?, ?, ?)",
        (identifier(), timeline_id, city['id'] if city else '', hood['id'] if hood else '', step['reached_on'],
         step['reached_on'], step['reached_on'], stamp(now)))
    return current(connection, timeline_id)


def turn_of(connection, timeline_id: str) -> int:
    return 1 + len(many(connection, 'SELECT id FROM moving_in WHERE timeline_id=?', (timeline_id,)))


def names(companion: dict) -> dict:
    return {'name': companion['version']['definition']['name'].split()[0], 'a': 'someone', 'b': ''}


def decide(connection, companion: dict, choice: str, facts: dict, now) -> dict:
    labels = names(companion)
    timeline_id = companion['active_timeline_id']
    table = consequences.tables()[choice]
    return consequences.decide(connection, timeline_id=timeline_id, choice=choice,
                               subject=f'moving_in:{timeline_id}:{turn_of(connection, timeline_id)}', facts=facts,
                               names=labels, labels=[option['label'].format(**labels) for option in table['options']],
                               day=local_today(companion, now).isoformat(), timestamp=stamp(now))


def their_home(connection, companion: dict, day: date) -> dict | None:
    return next((item for item in home.items_on(connection, companion['active_timeline_id'], day)
                 if item['kind'] == 'home'), None)


def your_hood(connection) -> tuple[dict | None, dict | None]:
    found = where.your_home(connection)
    return found if found else (None, None)


def hood_named(city: dict | None, name: str) -> dict | None:
    return next((hood for hood in (city or {}).get('neighborhoods') or [] if hood['name'] == name or hood['id'] == name),
                None)


def middle(hood: dict | None, unit: str) -> float | None:
    rents = (hood or {}).get('rent') or {}
    return sum(rents[unit]) / 2 if unit in rents else None


def commute_km(city: dict | None, definition: dict, hood: dict | None) -> float | None:
    """How far a neighbourhood is from where their work is in the city (its career hub), when both are known."""
    career, _guessed = money.career_for(definition, city) if city else (None, False)
    if not career or not hood or 'lat' not in hood:
        return None
    hubs = [name for hub in city.get('career_hubs') or [] if career.get('sector') in hub.get('sectors', ())
            for name in hub.get('neighborhoods', ())]
    spots = [found for name in hubs if (found := hood_named(city, name)) and 'lat' in found]
    from companion.world import catalog
    return min((catalog.distance_km(hood, spot) for spot in spots), default=None)


def where_facts(connection, companion: dict, between, today: date) -> dict:
    """What the engine reads for whose place: how big theirs is, which costs more, which is nearer their work, and
    whose pets live where."""
    from companion.life import outings, pets
    definition = companion['version']['definition']
    theirs = their_home(connection, companion, today) or {}
    city = between.your_city or outings.city_data(connection, definition)
    _city, mine = your_hood(connection)
    their_hood = hood_named(city, theirs.get('neighborhood') or '')
    size = UNITS.index(theirs['bedrooms']) if theirs.get('bedrooms') in UNITS else 2
    your_rent, their_rent = middle(mine, 'one_bedroom'), theirs.get('rent')
    to_yours, to_theirs = commute_km(city, definition, mine), commute_km(city, definition, their_hood)
    pet_count = sum(item['kind'] == 'pet' for item in home.items_on(connection, companion['active_timeline_id'], today))
    return {'their_size': size, 'their_pets': pet_count, 'your_pets': len(pets.of_persona(connection)),
            'their_rent_higher': int(bool(your_rent and their_rent and their_rent > your_rent * 1.1)),
            'their_rent_lower': int(bool(your_rent and their_rent and their_rent < your_rent * 0.9)),
            'yours_nearer': int(to_yours is not None and to_theirs is not None and to_yours + 2 < to_theirs),
            'theirs_nearer': int(to_yours is not None and to_theirs is not None and to_theirs + 2 < to_yours),
            'both_pets': int(pet_count > 0 and bool(pets.of_persona(connection))),
            'sheet': {group for group in consequences.WORDS if consequences.sheet_has(definition, group)}}


def decide_where(connection, companion: dict, between, now, message_id: str | None) -> dict:
    today = local_today(companion, now)
    outcome = decide(connection, companion, 'moving_in:where', where_facts(connection, companion, between, today), now)
    return insert(connection, companion, PLACES[outcome['picked']], 'moving', outcome['id'], now, message_id)


def rooted(connection, companion: dict) -> dict:
    """How tied they are to where they live: family and friends in their circle, and a job that is hard to leave."""
    from companion.life import circle
    people = circle.people(connection, companion['active_timeline_id'])
    family = sum(person['role'] in circle.FAMILY for person in people)
    friends = len(people) - family
    definition = companion['version']['definition']
    city = money.city_for(definition)
    career, _guessed = money.career_for(definition, city) if city else (None, False)
    pay = money.PAY_TIERS.get(career['pay'], money.DEFAULT_TIER) if career else money.DEFAULT_TIER
    return {'family': family, 'friends': friends, 'pay': pay,
            'rooted': min(3, (family >= 2) + (friends >= 3) + (pay >= 2)),
            'sheet': {group for group in consequences.WORDS if consequences.sheet_has(definition, group)}}


def decide_who(connection, companion: dict, between, now, message_id: str | None) -> dict:
    outcome = decide(connection, companion, 'moving_in:who', rooted(connection, companion), now)
    mover = MOVERS[outcome['picked']]
    return insert(connection, companion, mover, 'moving' if mover == 'them' else 'waiting', outcome['id'], now,
                  message_id, between)


def insert(connection, companion: dict, plan: str, status: str, consequence_id: str, now, message_id: str | None,
           between=None) -> dict:
    timeline_id = companion['active_timeline_id']
    today = local_today(companion, now)
    low, high = OTHER_CITY_DAYS if plan == 'them' else SAME_CITY_DAYS
    move_on = today + timedelta(days=random.Random(f'{timeline_id}:{plan}:move-day').randint(low, high))
    city, hood = place_for(connection, companion, plan, between, today)
    row_id = identifier()
    connection.execute(
        'INSERT INTO moving_in (id, timeline_id, plan, status, city_id, neighbourhood, decided_on, move_on, '
        'consequence_id, message_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (row_id, timeline_id, plan, status, city['id'] if city else '', hood['id'] if hood else '', today.isoformat(),
         move_on.isoformat() if status == 'moving' else None, consequence_id, message_id, stamp(now)))
    return optional(connection, 'SELECT * FROM moving_in WHERE id=?', (row_id,))


def place_for(connection, companion: dict, plan: str, between, today: date) -> tuple[dict | None, dict | None]:
    """The city and neighbourhood the shared home will be in."""
    from companion.life import outings
    definition = companion['version']['definition']
    if plan == 'you':
        return between.their_city, None  # Their place, once the user moves there.
    city, mine = your_hood(connection)
    if plan in ('yours', 'them'):
        return city, mine
    city = city or outings.city_data(connection, definition)
    theirs = hood_named(city, (their_home(connection, companion, today) or {}).get('neighborhood') or '')
    if plan == 'theirs':
        return city, theirs
    return city, new_hood(city, definition, f"{companion['active_timeline_id']}:new-place")


def new_hood(city: dict | None, definition: dict, seed: str) -> dict | None:
    """A new place for two: a neighbourhood with two-bedroom rents their pay and a share from the user can manage,
    the nearest to their work first."""
    if not city:
        return None
    found = money.profile(definition)
    tier = found.tier if found else money.DEFAULT_TIER
    hoods = [hood for hood in city.get('neighborhoods') or [] if (hood.get('rent') or {}).get('two_bedroom')]
    fitting = [hood for hood in hoods if hood.get('rent_tier') in money.HOOD_TIERS[tier]] or hoods
    if not fitting:
        return None
    ranked = sorted(fitting, key=lambda hood: (commute_km(city, definition, hood) or 0,
                                               random.Random(f"{seed}:{hood['id']}").random()))
    return ranked[0] if commute_km(city, definition, ranked[0]) is not None else \
        random.Random(seed).choice(sorted(fitting, key=lambda hood: hood['id']))


# Moving day ---------------------------------------------------------------------------------------------------------

def advance(connection, companion: dict, now) -> None:
    """Once a day: decide when the step is reached, move on moving day, settle in once the user moved to their city,
    and move out when the step was taken back or the user moved away. Cheap: no model."""
    if not ACTIVE or not companion.get('active_timeline_id'):
        return
    begin(connection, companion, now)
    row = current(connection, companion['active_timeline_id'])
    if row is None:
        return
    today = local_today(companion, now)
    if not reached(connection, companion, now) or chapter_undone(connection, row):
        move_out(connection, companion, now)
    elif row['status'] in ('moving', 'waiting') and on_break(connection, companion):
        hold(connection, row, today)
    elif joins(row) and row['status'] in ('moving', 'waiting'):
        follow_share(connection, companion, row, now)
    elif row['status'] == 'moving' and row['move_on'] <= today.isoformat() and not after_visit(connection, row, today):
        move(connection, companion, current(connection, companion['active_timeline_id']), now)
    elif row['status'] == 'waiting':
        settle_waiting(connection, companion, row, now)
    elif row['status'] == 'moved' and moved_away(connection, row):
        # The user moves out. One home stays: whoever set it up keeps it, and anyone who moved in with them since takes
        # a place of their own.
        move_out(connection, companion, now, 'them' if joins(row) else 'you')


def after_visit(connection, row: dict, today: date) -> bool:
    """A weekend visit across the distance under way on moving day puts the move off until the day after it ends
    (nobody moves out of the city the user is staying in with them). True while it is still to come."""
    found = optional(connection, "SELECT MAX(end_date) AS until FROM trips WHERE timeline_id=? AND visit!='' AND "
                     "status='planned' AND start_date<=? AND end_date>=?", (row['timeline_id'], today.isoformat(),
                                                                           row['move_on']))
    if not found or not found['until']:
        return False
    day = date.fromisoformat(found['until']) + timedelta(days=1)
    connection.execute('UPDATE moving_in SET move_on=? WHERE id=?', (day.isoformat(), row['id']))
    return day > today


def on_break(connection, companion: dict) -> bool:
    from companion.life import breakups  # Imported here: breakups reads the steps ladder, which this module reads too.
    return breakups.apart(connection, companion) == 'break'


def hold(connection, row: dict, today: date) -> None:
    """On a break (Breaks and breakups) a move not made yet waits: moving day moves on a day at a time."""
    if row['move_on'] and row['move_on'] <= today.isoformat():
        connection.execute('UPDATE moving_in SET move_on=? WHERE id=?',
                           ((today + timedelta(days=1)).isoformat(), row['id']))


def follow_step(connection, companion: dict, now) -> None:
    """The step set on the Character page: reaching moving in decides where, and taking it back moves out."""
    if reached(connection, companion, now):
        begin(connection, companion, now)
    elif current(connection, companion['active_timeline_id']):
        move_out(connection, companion, now)


def chapter_undone(connection, row: dict) -> bool:
    found = row['chapter_id'] and optional(connection, 'SELECT undone_at FROM life_chapters WHERE id=?',
                                           (row['chapter_id'],))
    return bool(found and found['undone_at'])


def moved_away(connection, row: dict) -> bool:
    """The user changed their home city on the persona form while they lived together."""
    found = optional(connection, 'SELECT home_city_id FROM persona WHERE id=1')
    return bool(found and found['home_city_id'] and row['city_id'] and found['home_city_id'] != row['city_id'])


def settle_waiting(connection, companion: dict, row: dict, now) -> None:
    """They asked the user to move to their city: once the user's home is there, the user moves in at theirs."""
    between = where.between(connection, companion['version']['definition'])
    if between.long_distance:
        return
    today = local_today(companion, now)
    theirs = their_home(connection, companion, today) or {}
    hood = hood_named(between.your_city, theirs.get('neighborhood') or '')
    connection.execute("UPDATE moving_in SET status='moving', move_on=?, city_id=?, neighbourhood=? WHERE id=?",
                       (today.isoformat(), between.your_city['id'] if between.your_city else row['city_id'],
                        hood['id'] if hood else '', row['id']))
    move(connection, companion, current(connection, companion['active_timeline_id']), now)


def move(connection, companion: dict, row: dict, now) -> None:
    """Moving day: the shared home is theirs as it is, or a new home in the user's neighbourhood or a new one, and a
    move from another city is a life chapter (a new job here, coworkers left behind, this city's clock)."""
    day = date.fromisoformat(row['move_on'])
    found = {'ended': [], 'added': [], 'removed': []}
    changes, chapter = {}, None
    if joins(row):
        changes, found = join_home(connection, companion, row, day, now)
    elif row['plan'] in ('yours', 'new', 'them'):
        changes, found = rehome(connection, companion, row, day, now)
    else:
        share_theirs(connection, companion, row, day, True)
    if row['plan'] == 'them':
        changes.update(city_changes(connection, companion, row))
        found['removed'] = leave_behind(connection, companion, now)
    if changes:
        chapter = insert_chapter(connection, companion, row, day, changes, found, now)
    if changes.get('timezone') and changes['timezone'] != companion['version']['timezone']:
        replan(connection, companion['active_timeline_id'], now)
    connection.execute("UPDATE moving_in SET status='moved', moved_on=?, chapter_id=?, home_item_id=?, "
                       'ended_item_ids=? WHERE id=?', (day.isoformat(), chapter, (found['added'] or [None])[0],
                                                       encode(found['ended']), row['id']))


def replan(connection, timeline_id: str, now) -> None:
    """A move to another clock: the days already planned ahead (life_agenda) were laid out on the old one, so their
    still-to-come part is planned again on the new one (as self_facts.stamp_change does for new tastes)."""
    connection.execute("DELETE FROM life_agenda WHERE timeline_id=? AND subject='companion' AND status='upcoming' "
                       'AND starts_at>?', (timeline_id, stamp(now)))
    connection.execute("UPDATE agenda_cursors SET through=MIN(through, ?) WHERE timeline_id=? AND subject='companion'",
                       (stamp(now), timeline_id))


def share_theirs(connection, companion: dict, row: dict, day: date, shared: bool) -> None:
    """The user moves into their place: it becomes the shared home (and stops being one when the user moves out)."""
    theirs = their_home(connection, companion, day)
    if not theirs:
        return
    stored = optional(connection, 'SELECT details FROM home_items WHERE id=?', (theirs['id'],))
    details = {**decode(stored['details']), 'shared': shared}
    connection.execute('UPDATE home_items SET details=? WHERE id=?', (encode(details), theirs['id']))
    if shared:
        hood = hood_named(city_of(connection, row), theirs.get('neighborhood') or '')
        connection.execute('UPDATE moving_in SET neighbourhood=? WHERE id=?', (hood['id'] if hood else '', row['id']))


def city_of(connection, row: dict) -> dict | None:
    return where.known_cities(connection).get(row['city_id'])


def rehome(connection, companion: dict, row: dict, day: date, now) -> tuple[dict, dict]:
    """Their old home ends the day before moving day and the shared one begins."""
    city = city_of(connection, row)
    hood = hood_named(city, row['neighbourhood'])
    timeline_id = companion['active_timeline_id']
    old = [item for item in home.items_on(connection, timeline_id, day) if item['kind'] == 'home']
    for item in old:
        connection.execute('UPDATE home_items SET until=? WHERE id=?', (day.isoformat(), item['id']))
    location = f"{hood['name']}, {city['name']}" if hood and city else (city or {}).get('name', '')
    unit = 'two_bedroom' if row['plan'] == 'new' else 'one_bedroom'
    place = shared_place(f'home:{timeline_id}:together:{day.isoformat()}', companion, city, hood, unit)
    added = home.insert_item(connection, timeline_id, place, 'change', day, now)
    return ({'location': location} if location else {}), {'ended': [item['id'] for item in old], 'added': [added]}


def shared_place(seed: str, companion: dict, city: dict | None, hood: dict | None, unit: str) -> dict:
    """The home they share, built the way home.py builds one, at the size and rent of a place for two."""
    from companion.characters import apply_changes
    definition = companion['version']['definition']
    if city and hood:
        definition = apply_changes(definition, {'location': f"{hood['name']}, {city['name']}",
                                                'home_city': city['name']})
    place = home.place_item(seed, definition, city)
    details = dict(place['details'])
    rents = (hood or {}).get('rent') or {}
    if unit in rents and city:
        low, high = rents[unit]
        rent = low + (high - low) * random.Random(f'{seed}:rent').random()
        name = home.home_name(place['variety'], unit, city)
        step = generators.rent_step(rent)  # By 25 in dollars, by 1 in Camelot's pennies (never down to 0).
        details.update({'bedrooms': unit, 'rent': max(step, int(round(rent / step) * step)), 'rent_from': 'shared',
                        'description': f"{name} in {hood['name']}", 'neighborhood': hood['name']})
        place = {**place, 'name': name}
    return {**place, 'details': {**details, 'shared': True}}


def city_changes(connection, companion: dict, row: dict) -> dict:
    """Moving to the user's city: that city, its clock, and the same job there if it has one, else one like it."""
    from companion.world import catalog
    city = city_of(connection, row)
    if not city:
        return {}
    changes = {'home_city': city['name']}
    if city.get('timezone'):
        changes['timezone'] = city['timezone']
    definition = companion['version']['definition']
    old_city = money.city_for(definition)
    career, _guessed = money.career_for(definition, old_city) if old_city else (None, False)
    offered = catalog.everyday(catalog.careers_for(city)) if city.get('neighborhoods') else {}
    if career and offered:
        same = offered.get(career['id']) or next(
            (item for key, item in sorted(offered.items()) if item.get('sector') == career.get('sector')
             and item.get('schedule') == career.get('schedule')), None)
        if same:
            changes['career'] = same['id']
    return changes


def leave_behind(connection, companion: dict, now) -> list[str]:
    """Coworkers stay at the old job; family and friends stay in touch from the old city."""
    from companion.life import circle
    removed = []
    for person in circle.people(connection, companion['active_timeline_id']):
        if person['role'] == 'coworker':
            circle.set_status(connection, person['id'], 'removed', now)
            removed.append(person['id'])
    return removed


def insert_chapter(connection, companion: dict, row: dict, day: date, changes: dict, undo: dict, now) -> str:
    city = city_of(connection, row)
    hood = hood_named(city, row['neighbourhood'])
    name = companion['version']['definition']['name'].split()[0]
    there = f"{hood['name']}, {city['name']}" if hood and city else (city or {}).get('name', 'a new place')
    mates = listed(mate_names(connection, row)) if joins(row) else ''
    if mates:
        title = f'{name} moved in with you and {mates}'
        told = f'You moved in with the user and {mates}, at the place they share in {there}.'
        if row['plan'] == 'them':
            told += ' Your family and friends are back where you lived before, and you keep in touch by phone.'
        share = "Moved in today. It's a full house, and it already feels like home."
    elif row['plan'] == 'them':
        title = f'{name} moved to {city["name"]} to live with you' if city else f'{name} moved in with you'
        told = (f"You moved to {there} to live with the user. Your family and friends are back where you lived "
                'before, and you keep in touch by phone.')
        share = "I'm officially here. Boxes everywhere, but I'm home."
    else:
        title = f'{name} and you moved in together in {there}'
        told = {'yours': f"You moved into the user's place in {there}.",
                'new': f'You and the user moved into a new place together in {there}.'}.get(
            row['plan'], f'You and the user moved in together, at a place in {there}.')
        share = 'First night in our place. It already feels like home.'
    chapter_id = identifier()
    connection.execute('INSERT INTO life_chapters (id, timeline_id, kind, started_on, title, told, share, changes, undo, '
                       "created_at) VALUES (?, ?, 'move_in', ?, ?, ?, ?, ?, ?, ?)",
                       (chapter_id, companion['active_timeline_id'], day.isoformat(), title, told, share,
                        encode(changes), encode(undo), stamp(now)))
    return chapter_id


# Moving out -----------------------------------------------------------------------------------------------------------

def who_leaves(connection, companion: dict, row: dict) -> str:
    """The one who moved in moves out; from a new place, whoever can't manage its rent alone (them, when unknown). From
    a home shared with more of the user's partners, they move out and the others stay."""
    if row['plan'] in ('yours', 'them') or joins(row) or len(members(connection, household(row))) > 1:
        return 'them'
    if row['plan'] in ('theirs', 'you'):
        return 'you'
    found = money.profile(companion['version']['definition'])
    shared = their_home(connection, companion, date.fromisoformat(row['moved_on'] or row['decided_on'])) or {}
    rent = shared.get('rent')
    return 'you' if found and rent and rent <= found.income * money.RENT_CEILING else 'them'


def move_out(connection, companion: dict, now, who: str | None = None) -> dict | None:
    """They stop living together (Breaks and breakups calls this, as does the step taken back): a plan not yet carried
    out is dropped; otherwise whoever moved in moves out, or `who` when the caller knows. When they leave, they take a
    place of their own in the same city, from their budget, as a life chapter."""
    row = current(connection, companion.get('active_timeline_id') or '')
    if row is None:
        return None
    today = local_today(companion, now)
    if row['status'] != 'moved':
        connection.execute("UPDATE moving_in SET status='moved_out', out_on=?, out_who=NULL WHERE id=?",
                           (today.isoformat(), row['id']))
        return latest(connection, companion['active_timeline_id'])
    leaving = who or who_leaves(connection, companion, row)
    undone = chapter_undone(connection, row)  # The move undone on the Character page: it never happened.
    if undone and row['plan'] == 'them':
        replan(connection, row['timeline_id'], now)  # Back on their old city's clock.
    if leaving == 'them' and not undone:
        place_of_their_own(connection, companion, row, today, now)
    elif leaving == 'you':
        share_theirs(connection, companion, row, today, False)
    connection.execute("UPDATE moving_in SET status='moved_out', out_on=?, out_who=? WHERE id=?",
                       (today.isoformat(), None if undone else leaving, row['id']))
    return latest(connection, companion['active_timeline_id'])


def move_back(connection, companion: dict, since: str, now) -> dict | None:
    """A breakup taken back on Today (Breaks and breakups): a move out on or after `since` (a local day) is undone, so
    they live together as before; a plan dropped before moving day goes on."""
    from companion.life import chapters  # Imported here: chapters reads love_life, which reads the steps ladder.
    timeline_id = companion.get('active_timeline_id') or ''
    row = latest(connection, timeline_id)
    if row is None or row['status'] != 'moved_out' or (row['out_on'] or '') < since:
        return None
    if row['out_who'] == 'them':
        chapter = optional(connection, "SELECT * FROM life_chapters WHERE timeline_id=? AND kind='move_out' AND "
                           'undone_at IS NULL AND started_on=? ORDER BY created_at DESC LIMIT 1',
                           (timeline_id, row['out_on']))
        if chapter:
            chapters.reverse(connection, decode(chapter['undo']), now)
            connection.execute('UPDATE life_chapters SET undone_at=? WHERE id=?', (stamp(now), chapter['id']))
    elif row['out_who'] == 'you':
        share_theirs(connection, companion, row, local_today(companion, now), True)
    status = 'moved' if row['moved_on'] else 'waiting' if row['plan'] == 'you' or joins(row) else 'moving'
    connection.execute('UPDATE moving_in SET status=?, out_on=NULL, out_who=NULL WHERE id=?', (status, row['id']))
    if joins(row) and status == 'waiting':
        settle_share(connection, latest(connection, timeline_id), now)
    return latest(connection, timeline_id)


def place_of_their_own(connection, companion: dict, row: dict, day: date, now) -> None:
    city = city_of(connection, row)
    if not city:
        return
    definition = companion['version']['definition']
    found = money.profile(definition)
    tier = found.tier if found else money.DEFAULT_TIER
    hoods = sorted((hood for hood in city.get('neighborhoods') or [] if hood.get('rent')
                    and hood['id'] != row['neighbourhood'] and hood.get('rent_tier') in money.HOOD_TIERS[tier]),
                   key=lambda hood: hood['id'])
    if not hoods:
        return
    hood = random.Random(f"{row['id']}:moving-out").choice(hoods)
    timeline_id = companion['active_timeline_id']
    old = [item for item in home.items_on(connection, timeline_id, day) if item['kind'] == 'home']
    for item in old:
        connection.execute('UPDATE home_items SET until=? WHERE id=?', (day.isoformat(), item['id']))
    from companion.characters import apply_changes
    location = f"{hood['name']}, {city['name']}"
    place = home.place_item(f'home:{timeline_id}:{day.isoformat()}:own', apply_changes(definition, {
        'location': location, 'home_city': city['name']}), city)
    added = home.insert_item(connection, timeline_id, place, 'change', day, now)
    name = definition['name'].split()[0]
    connection.execute('INSERT INTO life_chapters (id, timeline_id, kind, started_on, title, told, share, changes, undo, '
                       "created_at) VALUES (?, ?, 'move_out', ?, ?, ?, '', ?, ?, ?)",
                       (identifier(), timeline_id, day.isoformat(), f"{name} moved out, to {hood['name']}",
                        f"You moved out of the place you shared with the user, to a place of your own in {hood['name']}.",
                        encode({'location': location}), encode({'ended': [item['id'] for item in old], 'added': [added]}),
                        stamp(now)))


# Sharing a home ---------------------------------------------------------------------------------------------------------

def household(row: dict) -> str:
    """The shared home a row belongs to, by the row that set it up (the first to live with the user there). A fork's
    copy of that row keeps its key (`origin`), so whoever moved in on another timeline still lives there."""
    return row.get('household') or row.get('origin') or row['id']


def joins(row: dict) -> bool:
    """A newcomer moving into (or living in) a home the user already shares with another of their partners."""
    return bool(row.get('household'))


def first_name(companion: dict) -> str:
    return companion['version']['definition']['name'].split()[0]


def owner_of(connection, timeline_id: str) -> dict | None:
    """The companion whose active timeline this is."""
    from companion.characters import by_id
    found = optional(connection, 'SELECT id FROM companions WHERE active_timeline_id=?', (timeline_id,))
    return by_id(connection, found['id']) if found else None


def first_of(connection, timeline_id: str) -> str:
    found = owner_of(connection, timeline_id)
    return first_name(found) if found else 'someone'


def members(connection, key: str, day: date | None = None) -> list[dict]:
    """Everyone living in this shared home (on `day`, else now), moved in and on their active timeline, in the order
    they moved in; `owner` is the companion's id."""
    rows = many(connection, "SELECT m.*, c.id AS owner FROM moving_in m JOIN companions c ON c.active_timeline_id="
                "m.timeline_id WHERE m.status='moved' AND (m.id=? OR m.origin=? OR m.household=?) "
                'ORDER BY m.moved_on, m.created_at', (key, key, key))
    return [row for row in rows if day is None or row['moved_on'] <= day.isoformat()]


def housemates(connection, companion: dict) -> list[tuple[dict, dict]]:
    """(companion, row) for the user's other partners who live with the user or are moving in with them, in one shared
    home (the first one set up): the home a newcomer would move into."""
    rows = many(connection, "SELECT m.* FROM moving_in m JOIN companions c ON c.active_timeline_id=m.timeline_id "
                "WHERE c.id<>? AND m.status IN ('moving', 'moved') AND m.plan<>'you' ORDER BY m.created_at",
                (companion['id'],))
    found = [(other, row) for row in rows if latest(connection, row['timeline_id'])['id'] == row['id']
             and (other := owner_of(connection, row['timeline_id']))]
    first = household(found[0][1]) if found else None
    return [(other, row) for other, row in found if household(row) == first]


def mates_of(connection, row: dict) -> list[dict]:
    """The others in the home a newcomer would move into, as companions."""
    owner = owner_of(connection, row['timeline_id'])
    return [other for other, found in housemates(connection, owner) if household(found) == row['household']] \
        if owner else []


def mate_names(connection, row: dict, statuses: tuple[str, ...] = ('moved',)) -> list[str]:
    """The first names of the others in the home this row shares, or will share."""
    key = household(row)
    rows = many(connection, 'SELECT m.timeline_id FROM moving_in m JOIN companions c ON c.active_timeline_id='
                "m.timeline_id WHERE (m.id=? OR m.origin=? OR m.household=?) AND m.id<>? AND m.status IN "
                f"({','.join('?' * len(statuses))}) ORDER BY m.created_at", (key, key, key, row['id'], *statuses))
    return [first_of(connection, found['timeline_id']) for found in rows]


def latest_shares(connection, row_id: str) -> dict[str, dict]:
    """Each one's latest answer about sharing the home, by companion id."""
    return {share['companion_id']: share for share in many(
        connection, 'SELECT * FROM moving_in_shares WHERE moving_in_id=? ORDER BY round, created_at', (row_id,))}


def readiness(connection, row: dict) -> tuple[bool, list[str]]:
    """Whether the newcomer is open to sharing the home, and the first names of those living there who aren't."""
    shares = latest_shares(connection, row['id'])
    mine = next((share for share in shares.values() if share['newcomer']), None)
    return bool(mine and mine['open']), [first_name(other) for other in mates_of(connection, row)
                                          if not (shares.get(other['id']) or {}).get('open')]


def share_facts(connection, companion: dict, now) -> tuple[dict, str]:
    """What the engine reads for sharing a home: an open-relationship interest, a trait like jealous or possessive,
    a rough patch over the user seeing someone else, their personality sliders, the drama level, their description."""
    from companion.life import love_life, rough_patches
    from companion.world import personality
    definition = companion['version']['definition']
    traits = [trait['name'] for trait in definition.get('emotional_traits') or []
              if MINDS_SHARING.search(trait.get('name') or '')]
    levels = personality.levels_of(definition.get('personality_sliders') or {})
    upset = rough_patches.ACTIVE and any(found['cause'] == 'seeing_someone' for found in rough_patches.open_rows(
        connection, companion, rough_patches.level(connection), now))
    return ({'open': int(love_life.is_open(definition)), 'minds': int(bool(traits)), 'upset': int(bool(upset)),
             'social': levels.get('social', 1), 'warmth': levels.get('warmth', 1), 'drama': steps.drama(connection),
             'sheet': {group for group in consequences.WORDS if consequences.sheet_has(definition, group)}},
            traits[0] if traits else '')


def ask(connection, asked: dict, row: dict, others: list[str], turn: int, now, raised: bool = False,
        newcomer: bool = False) -> None:
    """One of them says whether they are open to sharing a home with `others`: a roll of their own, kept with the move.
    One already living there who isn't ready can have a small rough patch with the user over it."""
    found, trait = share_facts(connection, asked, now)
    found.update(raised=int(raised), others=len(others) if newcomer else len(mates_of(connection, row)))
    labels = {'name': first_name(asked), 'a': listed(others), 'b': '', 'trait': trait}
    table = consequences.tables()[SHARE]
    outcome = consequences.decide(
        connection, timeline_id=asked['active_timeline_id'], choice=SHARE,
        subject=f"moving_in:share:{row['id']}:{asked['id']}:{turn}", facts=found, names=labels,
        labels=[option['label'].format(**labels) for option in table['options']],
        day=local_today(asked, now).isoformat(), timestamp=stamp(now))
    connection.execute('INSERT INTO moving_in_shares (id, moving_in_id, timeline_id, companion_id, newcomer, round, '
                       'consequence_id, open, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                       (identifier(), row['id'], asked['active_timeline_id'], asked['id'], int(newcomer), turn,
                        outcome['id'], int(outcome['picked'] == 0), stamp(now)))
    if not newcomer and outcome['picked'] != 0:
        from companion.life import rough_patches
        rough_patches.friction(connection, asked, 'sharing', f"sharing:{row['id']}:{asked['id']}:{turn}",
                               f'the user wanting {listed(others)} to move in too', now,
                               shown=f'over {listed(others)} moving in')


def ask_round(connection, companion: dict, row: dict, mates: list[dict], turn: int, now, only=None) -> None:
    """The newcomer and everyone living there (or only those in `only`) say whether they are open to sharing."""
    step = step_row(connection, companion)
    names = [first_name(other) for other in mates]
    if only is None or companion['id'] in only:
        ask(connection, companion, row, names, turn, now, bool(step and step['how'] == 'them'), True)
    for other in mates:
        if only is None or other['id'] in only:
            ask(connection, other, row, [first_name(companion)], turn, now)


def decide_share(connection, companion: dict, mates: list[tuple[dict, dict]], now, message_id: str | None) -> dict:
    """The user lives with another of their partners (or is about to): the newcomer would move into that home, if
    everyone is open to sharing it. Until they all are, the move waits."""
    host = mates[0][1]
    between = where.between(connection, companion['version']['definition'])
    row_id = identifier()
    connection.execute("INSERT INTO moving_in (id, timeline_id, plan, status, city_id, neighbourhood, decided_on, "
                       "message_id, household, created_at) VALUES (?, ?, ?, 'waiting', ?, ?, ?, ?, ?, ?)",
                       (row_id, companion['active_timeline_id'], 'them' if between.long_distance else 'yours',
                        host['city_id'], host['neighbourhood'], local_today(companion, now).isoformat(), message_id,
                        household(host), stamp(now)))
    row = optional(connection, 'SELECT * FROM moving_in WHERE id=?', (row_id,))
    ask_round(connection, companion, row, [other for other, _found in mates], 1, now)
    return settle_share(connection, row, now)


def settle_share(connection, row: dict, now) -> dict:
    """Everyone open: the move is on, with a moving day of its own. Anyone not: it waits."""
    ready, not_ready = readiness(connection, row)
    if ready and not not_ready and row['status'] == 'waiting':
        owner = owner_of(connection, row['timeline_id'])
        today = local_today(owner, now) if owner else now.date()
        low, high = OTHER_CITY_DAYS if row['plan'] == 'them' else SAME_CITY_DAYS
        start = max(date.fromisoformat(row['decided_on']), today)
        move_on = start + timedelta(days=random.Random(f"{row['id']}:share:move-day").randint(low, high))
        connection.execute("UPDATE moving_in SET status='moving', move_on=? WHERE id=?", (move_on.isoformat(), row['id']))
    elif not (ready and not not_ready) and row['status'] == 'moving':
        connection.execute("UPDATE moving_in SET status='waiting', move_on=NULL WHERE id=?", (row['id'],))
    return optional(connection, 'SELECT * FROM moving_in WHERE id=?', (row['id'],))


def follow_share(connection, companion: dict, row: dict, now) -> None:
    """Once a day for a move into a shared home: asked again some weeks after a not yet, carried out on moving day once
    someone lives there, and a move in like any other once nobody else lives with the user any more."""
    today = local_today(companion, now)
    mates = mates_of(connection, row)
    if not mates:
        connection.execute("UPDATE moving_in SET status='moved_out', out_on=?, out_who=NULL WHERE id=?",
                           (today.isoformat(), row['id']))
        decide_fresh(connection, companion, now)
    elif row['status'] == 'waiting':
        ask_again(connection, companion, row, mates, now)
    elif row['move_on'] <= today.isoformat() and not after_visit(connection, row, today):
        if members(connection, row['household'], today):
            move(connection, companion, current(connection, companion['active_timeline_id']), now)
        else:
            hold(connection, row, today)  # Whoever set up the home hasn't moved in yet.


def ask_again(connection, companion: dict, row: dict, mates: list[dict], now) -> None:
    """Some weeks after a not yet, whoever wasn't ready is asked again; anyone who came to live there since is asked
    straight away."""
    shares = latest_shares(connection, row['id'])
    keys = [companion['id'], *(other['id'] for other in mates)]
    last = max((parse(share['created_at']) for share in shares.values()), default=None)
    due = last is None or now - last >= timedelta(days=SHARE_AGAIN)
    again = {key for key in keys if key not in shares or (due and not shares[key]['open'])}
    if again:
        turn = 1 + max((share['round'] for share in shares.values()), default=0)
        ask_round(connection, companion, row, mates, turn, now, again)
    settle_share(connection, row, now)


def join_home(connection, companion: dict, row: dict, day: date, now) -> tuple[dict, dict]:
    """Moving into the home the user shares with another: the same place as theirs, and their old home ends."""
    house = members(connection, row['household'], day)
    host = house[0]
    connection.execute('UPDATE moving_in SET city_id=?, neighbourhood=? WHERE id=?',
                       (host['city_id'], host['neighbourhood'], row['id']))
    city = city_of(connection, host)
    hood = hood_named(city, host['neighbourhood'])
    grow(connection, house, city, hood, day, len(house) + 2)
    other = owner_of(connection, host['timeline_id'])
    shared = their_home(connection, other, day) if other else None
    timeline_id = companion['active_timeline_id']
    old = [item for item in home.items_on(connection, timeline_id, day) if item['kind'] == 'home']
    for item in old:
        connection.execute('UPDATE home_items SET until=? WHERE id=?', (day.isoformat(), item['id']))
    location = f"{hood['name']}, {city['name']}" if hood and city else (city or {}).get('name', '')
    place = same_place(shared) if shared else shared_place(f'home:{timeline_id}:together:{day.isoformat()}', companion,
                                                          city, hood, 'one_bedroom')
    added = home.insert_item(connection, timeline_id, place, 'change', day, now)
    return ({'location': location} if location else {}), {'ended': [item['id'] for item in old], 'added': [added]}


def size_for(people: int) -> str:
    """Bedrooms follow the household: a one-bedroom for a couple, the largest size the rents know for more."""
    return 'one_bedroom' if people <= 2 else 'two_bedroom'


def grow(connection, house: list[dict], city: dict | None, hood: dict | None, day: date, people: int) -> None:
    """Another of the user's partners moving in: a shared home too small for everyone gets the room they need (the
    same place, a size up, at that size's rent), on each copy of it."""
    unit = size_for(people)
    rents = (hood or {}).get('rent') or {}
    if not city or unit not in rents:
        return
    low, high = rents[unit]
    rent = int(round((low + (high - low) * random.Random(f'home:{household(house[0])}:{unit}').random()) / 25) * 25)
    for found in house:
        other = owner_of(connection, found['timeline_id'])
        item = their_home(connection, other, day) if other else None
        if not item or (item.get('bedrooms') in UNITS and UNITS.index(item['bedrooms']) >= UNITS.index(unit)):
            continue
        name = home.home_name(item['variety'], unit, city)
        stored = optional(connection, 'SELECT details FROM home_items WHERE id=?', (item['id'],))
        details = {**decode(stored['details']), 'bedrooms': unit, 'rent': rent, 'rent_from': 'shared',
                   'description': f"{name} in {hood['name']}"}
        connection.execute('UPDATE home_items SET name=?, details=? WHERE id=?', (name, encode(details), item['id']))


ITEM_KEYS = ('id', 'kind', 'name', 'variety', 'origin', 'since', 'until', 'edited', 'revision')


def same_place(shared: dict) -> dict:
    """A copy of the shared home, for the one moving in."""
    details = {key: value for key, value in shared.items() if key not in ITEM_KEYS}
    return {'kind': 'home', 'name': shared['name'], 'variety': shared['variety'], 'details': {**details, 'shared': True}}


def asked_of(connection, companion: dict) -> list[tuple[dict, dict]]:
    """(their latest answer, the newcomer's row) for each move into a home they live in that hasn't happened yet."""
    rows = many(connection, "SELECT m.* FROM moving_in m JOIN companions c ON c.active_timeline_id=m.timeline_id WHERE "
                "m.status IN ('waiting', 'moving') AND m.household IS NOT NULL AND m.id IN (SELECT moving_in_id FROM "
                'moving_in_shares WHERE companion_id=? AND newcomer=0) ORDER BY m.created_at', (companion['id'],))
    return [(latest_shares(connection, row['id'])[companion['id']], row) for row in rows
            if latest(connection, row['timeline_id'])['id'] == row['id']]


def plural(names: list[str]) -> dict:
    many_ = len(names) > 1
    return {'is': 'are' if many_ else 'is', 's': 's' if many_ else '', 'lives': 'live' if many_ else 'lives'}


# What the newcomer is told: the move on, or waiting (on themselves, or on someone living there).
JOINER = {
    'moving': "You're moving in with the user and {mates} on {day}, into the place they share in {place}. {mates} "
              "{is} also the user's partner{s}, and everyone is open to sharing a home.",
    'you_wait': "You'd like to live with the user, but they share a home with {mates} (also the user's partner{s}), "
                "and you aren't ready to share a home with them. So you aren't moving in for now.",
    'wait': "You'd like to live with the user, who shares a home with {mates} (also the user's partner{s}). You're open "
            "to sharing it, but {not_ready} {is_n} not ready to share it yet, so your move waits for now.",
}
THEM_TOO = " You'll leave your job and look for one in {city}, and your family and friends stay where you live now."
# What the one living there is told about a newcomer, and while it is new, to say how they feel.
SHARING = {
    'moving': '{name}, who the user is also seeing, is moving in with you and the user on {day}. You are open to '
              'sharing your home with {name}.',
    'wait': '{name}, who the user is also seeing, would like to move in with you and the user. You are open to it, but '
            '{not_ready} {is_n} not ready yet, so the move waits.',
    'no': "{name}, who the user is also seeing, would like to move in with you and the user. You aren't ready to share "
          "your home with another of the user's partners, so the move waits.",
}
JUST_WAITS = ('- You just agreed you want to live together, and this is where it stands. Say so in this reply, in your '
              'own words.')
SHARING_NEW = ' This is new: tell the user how you feel about it, honestly, in your own words.'


def joiner_line(connection, row: dict) -> str:
    mates = mate_names(connection, row, ('moved', 'moving'))
    ready, not_ready = readiness(connection, row)
    key = 'moving' if row['status'] == 'moving' else 'wait' if ready else 'you_wait'
    city = city_of(connection, row)
    text = JOINER[key].format(mates=listed(mates), day=day_text(row['move_on'] or row['decided_on']),
                              place=place_text(connection, row) or 'town', not_ready=listed(not_ready),
                              is_n=plural(not_ready)['is'], **plural(mates))
    return text + (THEM_TOO.format(city=(city or {}).get('name', 'their city')) if row['plan'] == 'them' and
                   key == 'moving' else '')


def share_lines(connection, companion: dict, now) -> list[tuple[str, str]]:
    """For one who lives with the user (or is moving in): another of the user's partners would move in too."""
    lines = []
    for share, row in asked_of(connection, companion):
        name = first_of(connection, row['timeline_id'])
        _ready, not_ready = readiness(connection, row)
        others = [found for found in not_ready if found != first_name(companion)]
        key = 'no' if not share['open'] else 'moving' if row['status'] == 'moving' else 'wait'
        new = SHARING_NEW if not share['told_at'] and now - parse(share['created_at']) < timedelta(days=TOLD_DAYS) else ''
        text = SHARING[key].format(name=name, day=day_text(row['move_on'] or row['decided_on']),
                                   not_ready=listed(others) or name, is_n=plural(others)['is'])
        lines.append((f"moving-in:share:{share['id']}", f'- {text}{new}'))
    return lines


def ask_reason(connection, companion: dict) -> str | None:
    """Bringing up moving in while the user lives with another of their partners: they know who lives there."""
    mates = [first_name(other) for other, _row in housemates(connection, companion)]
    if not mates:
        return None
    words = plural(mates)
    return (f"You'd like to live with the user. They share a home with {listed(mates)}, who {words['is']} also their "
            f"partner{words['s']}, and you know it. Ask the user in your own words, simply, how they'd feel about you "
            "moving in with them too, and leave them room to say they aren't ready. Don't settle anything yet.")


# The one living there texts the user about it (companion/life/openers.py); a line from the bank stands in.
SHARE_REASONS = {
    True: '{name}, who the user is also seeing, would like to move in with you and the user, and you are open to '
          'sharing your home. Text the user about it: how you feel about it, honestly, in your own words.',
    False: "{name}, who the user is also seeing, would like to move in with you and the user. You aren't ready to share "
           "your home with another of the user's partners. Text the user about it: tell them how you feel, honestly "
           'and kindly, in your own words.',
}
SHARE_TEXTS = {
    True: ("So, {name} moving in. I've been thinking about it, and I'm okay with it. Really.",
           'About {name} moving in: honestly? I think it could work.'),
    False: ("Can we talk about {name} moving in? I don't think I'm ready for that yet.",
            "About {name} moving in... I'm not there yet. Can we talk?"),
}


def share_due(connection, companion: dict, now) -> list:
    """A newcomer would move into the home they live in: they text the user how they feel, within a few days."""
    from companion.life.openers import Trigger
    if not ACTIVE or not FIRST_TEXTS or not companion.get('active_timeline_id'):
        return []
    result = []
    for share, row in asked_of(connection, companion):
        if share['told_at'] or now - parse(share['created_at']) >= timedelta(days=TOLD_DAYS):
            continue
        name, said = first_of(connection, row['timeline_id']), bool(share['open'])
        template = random.Random(f"{share['id']}:line").choice(SHARE_TEXTS[said]).format(name=name)
        result.append(Trigger(f"move-share:{share['id']}", 'move_share', SHARE_REASONS[said].format(name=name), template,
                              (share['id'],)))
    return result[:1]


def settle(connection, companion: dict, message: dict, trigger, timestamp: str) -> None:
    """Their text about it went out: the chat no longer needs to say it is new."""
    connection.execute('UPDATE moving_in_shares SET told_at=? WHERE id=?', (timestamp, trigger.sources[0]))


def newcomers_view(connection, companion: dict, show_odds: bool) -> list[dict]:
    """For the Character page of one living there: who would move in, and whether they themselves are open to it."""
    result = []
    for share, row in asked_of(connection, companion):
        _ready, not_ready = readiness(connection, row)
        result.append({'name': first_of(connection, row['timeline_id']), 'status': row['status'],
                       'move_on': row['move_on'], 'open': bool(share['open']), 'not_ready': not_ready,
                       'consequence_id': share['consequence_id'] if show_odds else None})
    return result


def move_in_now(connection, companion: dict, now) -> None:
    """Living together picked on the Character page while a move into a shared home waits or is on its way: the user
    makes it so. Everyone's answer becomes open (as Make it go this way would), and they move in today."""
    row = current(connection, companion.get('active_timeline_id') or '')
    if not row or not joins(row) or row['status'] not in ('moving', 'waiting'):
        return
    for share in latest_shares(connection, row['id']).values():
        if not share['open'] and share['consequence_id']:
            consequences.change(connection, share['consequence_id'], 0, stamp(now))
        connection.execute('UPDATE moving_in_shares SET open=1 WHERE id=?', (share['id'],))
    connection.execute("UPDATE moving_in SET status='moving', move_on=? WHERE id=?",
                       (local_today(companion, now).isoformat(), row['id']))
    follow_share(connection, companion, current(connection, companion['active_timeline_id']), now)


def change_share(connection, consequence_id: str, option: int, now) -> dict:
    """Hidden values: one of them is open to sharing after all, or isn't; the move is on, or waits, as it follows."""
    share = optional(connection, 'SELECT * FROM moving_in_shares WHERE consequence_id=?', (consequence_id,))
    require(share is not None, 'That outcome is not about sharing a home.', 404)
    row = optional(connection, 'SELECT * FROM moving_in WHERE id=?', (share['moving_in_id'],))
    require(row is not None and row['status'] in ('moving', 'waiting'), 'They already moved in.', 409)
    connection.execute('UPDATE moving_in_shares SET open=? WHERE id=?', (int(option == 0), share['id']))
    settle_share(connection, row, now)
    return consequences.by_id(connection, consequence_id)


def copy_shares(connection, old_id: str, new_row_id: str, parent_id: str, new_id: str) -> None:
    """A fork keeps the answers about sharing the home; the newcomer's own (on this timeline) can still be changed."""
    for share in many(connection, 'SELECT * FROM moving_in_shares WHERE moving_in_id=?', (old_id,)):
        mine = share['timeline_id'] == parent_id
        consequence_id = consequences.copy(
            connection, share['consequence_id'], new_id,
            f"moving_in:share:{new_row_id}:{share['companion_id']}:{share['round']}") \
            if mine and share['consequence_id'] else share['consequence_id']
        connection.execute('INSERT INTO moving_in_shares (id, moving_in_id, timeline_id, companion_id, newcomer, round, '
                           'consequence_id, open, told_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                           (identifier(), new_row_id, new_id if mine else share['timeline_id'], share['companion_id'],
                            share['newcomer'], share['round'], consequence_id, share['open'], share['told_at'],
                            share['created_at']))


# Living together ------------------------------------------------------------------------------------------------------

def split(connection, timeline_id: str, costs: dict | None, day: date) -> dict | None:
    """The home's costs for their budget (money.py): living together, they pay their share of the rent (half, or a
    third with another of the user's partners living there too)."""
    if not costs or not costs.get('rent'):
        return costs
    row = current(connection, timeline_id)
    if not row or row['status'] != 'moved' or row['moved_on'] > day.isoformat():
        return costs
    people = 1 + max(len(members(connection, household(row), day)), 1)
    return {**costs, 'rent': round(costs['rent'] / people, 2), 'shared': True}


def turn(companion: dict, day: date, task: str, house: tuple[str, ...] = ()) -> str:
    """Whose turn a chore is today, 'you' (the companion) or 'user', by rules: on their work days the user cooks and
    they do the dishes; on other days cooking takes turns and the dishes go to whoever didn't cook; laundry and
    tidying take turns week by week. With more of the user's partners at home (`house`, the companions' ids in the
    order they moved in) everyone takes turns, and another's turn is their id."""
    from companion.life import upkeep
    if len(house) > 1:
        return rota(companion, day, task, house)
    # Cooking and the dishes share one seed, so the dishes always go to whoever didn't cook.
    shared = 'cooking' if task in ('cooking', 'dishes') else task
    seed = random.Random(f"{companion['active_timeline_id']}:{shared}:turns").randrange(2)
    if task in ('cooking', 'dishes'):
        cooks = 'user' if day.weekday() in upkeep.busy_days(companion['version']['definition']) else \
            ('you', 'user')[(day.toordinal() + seed) % 2]
        return cooks if task == 'cooking' else ('user' if cooks == 'you' else 'you')
    return ('you', 'user')[(day.isocalendar()[1] + seed) % 2]


def rota(companion: dict, day: date, task: str, house: tuple[str, ...]) -> str:
    """Turns among everyone at home: cooking by the day and the dishes to the next one along, laundry and tidying by
    the week. Seeded by the household, so each of them reads the same rota."""
    people = ('user', *house)
    shared = 'cooking' if task in ('cooking', 'dishes') else task
    seed = random.Random(f"{':'.join(house)}:{shared}:turns").randrange(len(people))
    if task in ('cooking', 'dishes'):
        index = (day.toordinal() + seed + (task == 'dishes')) % len(people)
    else:
        index = (day.isocalendar()[1] + seed) % len(people)
    found = people[index]
    return 'you' if found == companion['id'] else found


def house_of(connection, row: dict, day: date) -> tuple[str, ...]:
    """The companions' ids at home for the rota, when more of the user's partners live there; () for a couple."""
    ids = tuple(found['owner'] for found in members(connection, household(row), day))
    return ids if len(ids) > 1 else ()


def chore_turns(connection, companion: dict, day: date) -> dict[str, str] | None:
    """Living together on `day`, for upkeep.py: each area of housework is 'you' on their turn, else 'done' (it was
    someone else's turn) or 'undone' (the user said they left it on their own turn). None when they don't live
    together."""
    row = living(connection, companion, day)
    if not row:
        return None
    house = house_of(connection, row, day)
    left = {found['subject'].rsplit(':', 1)[1] for found in many(
        connection, "SELECT subject FROM rough_patches WHERE cause='chore' AND subject LIKE ?",
        (f"chore:{row['id']}:{day.isoformat()}:%",))}
    who = {area: turn(companion, day, task, house) for area, task in UPKEEP.items()}
    return {area: 'you' if found == 'you' else 'undone' if found == 'user' and UPKEEP[area] in left else 'done'
            for area, found in who.items()}


def out_now(row: dict, now: datetime) -> bool:
    return bool(row['out_until'] and parse(row['out_until']) > now)


def just_out(connection, companion: dict, now: datetime) -> bool:
    """The user headed out less than an hour ago (calls.py waits a while before they ring)."""
    row = living(connection, companion, local_today(companion, now))
    return bool(row and out_now(row, now) and parse(row['out_until']) - OUT_FOR > now - JUST_OUT)


def at_home_now(connection, companion: dict, now: datetime) -> bool:
    """Whether they are home this evening: free (not at work, out, away or asleep), from EVENING on."""
    from companion.life import pacing, together, trips
    local = now.astimezone(zone(companion['version']['timezone']))
    if local.strftime('%H:%M') < EVENING or trips.away_on(connection, companion['id'], local.date()):
        return False
    found = pacing.block_now(connection, companion, now)
    block = found[0] if found else None
    return not (block and (together.busy_kind(block) or block['kind'] == 'sleep'))


def home_state(connection, companion: dict, now: datetime) -> dict | None:
    """{state, kind, text} while they are both home of an evening (together.state reads this), else None."""
    row = living(connection, companion, local_today(companion, now))
    if not row or out_now(row, now) or not at_home_now(connection, companion, now):
        return None
    return {'state': 'together', 'kind': 'home', 'text': 'Home together'}


def view_strip(connection, companion: dict, now: datetime) -> dict | None:
    """What the chat strip shows while they live together: home together (with Heading out), or the user out (with I'm
    home)."""
    row = living(connection, companion, local_today(companion, now))
    if not row:
        return None
    if out_now(row, now):  # Whether they are home meanwhile, or at work or out themselves.
        return {'status': 'out', 'until': row['out_until'], 'they_home': at_home_now(connection, companion, now)}
    return {'status': 'home'} if home_state(connection, companion, now) else None


def set_out(connection, companion: dict, out: bool, now: datetime) -> None:
    row = living(connection, companion, local_today(companion, now))
    require(row is not None, 'You do not live together.', 409)
    mark_out(connection, row, stamp(now + OUT_FOR) if out else None)


def mark_out(connection, row: dict, until: str | None) -> None:
    """The user out, or home: for everyone they live with."""
    for found in members(connection, household(row)) or [row]:
        connection.execute('UPDATE moving_in SET out_until=? WHERE id=?', (until, found['id']))


def note(connection, message: dict, companion: dict, timestamp: str) -> None:
    """After the steps are read from a user message: a moving-in step just reached settles where (so the reply can say
    it), and "I'm out" or "I'm home" while living together moves the chat between texting and in person."""
    if not ACTIVE or message['role'] != 'user' or not companion.get('active_timeline_id'):
        return
    now = parse(message['created_at'])
    begin(connection, companion, now, message['id'])
    row = living(connection, companion, local_today(companion, now))
    if not row:
        return
    if HOME.search(message['text']):
        mark_out(connection, row, None)
    elif OUT.search(message['text']):
        mark_out(connection, row, stamp(now + OUT_FOR))
    skipped(connection, companion, row, message['text'], now)


def skipped(connection, companion: dict, row: dict, text: str, now: datetime):
    """A chore the user says they left undone on their own turn: everyday friction, at most one roll a chore a day."""
    found = SKIPPED.search(text)
    task = found and next(task for start, task in SKIPPED_TASKS if found['task'].lower().startswith(start))
    today = local_today(companion, now)
    if not task or turn(companion, today, task, house_of(connection, row, today)) != 'user':
        return
    from companion.life import rough_patches
    chore = CHORES[task]
    rough_patches.friction(connection, companion, 'chore', f"chore:{row['id']}:{today.isoformat()}:{task}",
                           f'the user left {chore} undone when it was their turn', now,
                           shown=f'over you leaving {chore} undone')


# What the chat context says ('where' section) ---------------------------------------------------------------------------

def day_text(day: str) -> str:
    found = date.fromisoformat(day)
    return f'{found:%A} {found.day} {found:%B}'


def place_text(connection, row: dict) -> str:
    city = city_of(connection, row)
    hood = hood_named(city, row['neighbourhood'])
    return hood['name'] if hood else (city or {}).get('name', '')


PLANNED = {
    'yours': "You're moving into the user's place in {place}, on {day}.",
    'theirs': 'The user is moving into your place in {place}, on {day}.',
    'new': "You're both moving into a new place together in {place}, on {day}.",
    'them': "You're moving to {city} to live with the user, on {day}: you'll leave your job and look for one there, "
            'and your family and friends stay where you live now.',
    'you': 'You asked the user to move to {city} to live with you. It is their choice and their move to make, so you '
           "don't press; until they do, you are long distance.",
}


def plan_line(connection, row: dict) -> str:
    city = city_of(connection, row)
    return PLANNED[row['plan']].format(place=place_text(connection, row) or 'town', day=day_text(row['move_on'] or
                                                                                                  row['decided_on']),
                                       city=(city or {}).get('name', 'your city'))


CHORES = {'cooking': 'cooking', 'dishes': 'the dishes', 'laundry': 'the laundry', 'tidying': 'tidying up'}


def listed(items: list[str]) -> str:
    """'cooking', 'cooking and the dishes', 'cooking, the dishes and the laundry'."""
    return ' and '.join(items) if len(items) < 3 else f"{', '.join(items[:-1])} and {items[-1]}"


def chores_text(companion: dict, day: date, house: tuple[str, ...] = (), names: dict | None = None) -> str:
    """Whose turn the chores are today: "Today cooking is yours; the dishes, the laundry and tidying up are the
    user's." With more at home, theirs too ("the dishes are Charles's")."""
    who = {task: turn(companion, day, task, house) if house else turn(companion, day, task) for task in TASKS}
    others = [(key, f"{name}'s") for key, name in (names or {}).items() if key != companion['id']]
    parts = []
    for side, owner in (('you', 'yours'), *others, ('user', "the user's")):
        tasks = [CHORES[task] for task in TASKS if who[task] == side]
        if tasks:
            parts.append(f"{listed(tasks)} {'is' if tasks in (['cooking'], ['the laundry'], ['tidying up']) else 'are'} {owner}")
    return f"Today {'; '.join(parts)}."


def living_lines(connection, companion: dict, row: dict, now: datetime) -> list[tuple[str, str]]:
    from companion.life import outings, pets
    today = local_today(companion, now)
    since = 'today' if row['moved_on'] == today.isoformat() else f"since {day_text(row['moved_on'])}"
    shared = their_home(connection, companion, today)
    what = shared['description'] if shared else f'a place in {place_text(connection, row)}'
    costs = 'mortgage' if shared and shared.get('owned') else 'rent'  # A place bought together (big_turns.py).
    yours = [found['name'] for found in pets.of_persona(connection)]
    house = members(connection, household(row), today)
    names = {found['owner']: first_of(connection, found['timeline_id']) for found in house}
    mates = [name for key, name in names.items() if key != companion['id']]
    ids = tuple(names) if mates else ()
    both = f"all {COUNTS.get(len(mates) + 2, 'of you')}" if mates else 'both'
    animals = f" The user's pets ({', '.join(yours)}) live there too and are {both} of yours now." if yours else ''
    living = (f"- You live with the user and {listed(mates)} (also the user's partner{'s' if len(mates) > 1 else ''}), "
              f"{since}, at {what}. The {COUNTS.get(len(mates) + 2, 'all')} of you split the {costs} and the bills. "
              if mates else f'- You and the user live together, {since}, at {what}. You split the {costs} and the bills. ')
    lines = [(f"moving-in:{row['id']}:home", f'{living}{chores_text(companion, today, ids, names)}{animals}')]
    if row['moved_on'] == today.isoformat():
        lines.append((f"moving-in:{row['id']}:today", '- Today was moving day: you just moved in together.'))
    if home_state(connection, companion, now):
        home_too = [first_of(connection, found['timeline_id']) for found in house if found['owner'] != companion['id']
                    and (other := owner_of(connection, found['timeline_id'])) and at_home_now(connection, other, now)]
        too = f" {listed(home_too)} {'is' if len(home_too) == 1 else 'are'} home too." if home_too else ''
        both = 'you and the user are both home' if mates else 'you are both home'
        lines.append((f"moving-in:{row['id']}:evening", f'- It is evening and {both}, together in person.{too} '
                      + outings.IN_PERSON))
    elif out_now(row, now):
        here = ' and you are at home' if at_home_now(connection, companion, now) else ''
        lines.append((f"moving-in:{row['id']}:out", f'- The user is out right now{here}; you are texting until they get home.'))
    return lines


def context_lines(connection, companion: dict, now: datetime, fresh_ids: set[str]) -> list[tuple[str, str]]:
    """(identity, line) for the 'where' section: the move planned (said in this reply when it was just decided), the
    shared home and whose turn the chores are, the evening at home, and a recent move out."""
    if not companion.get('active_timeline_id'):
        return []
    row = latest(connection, companion['active_timeline_id'])
    if row is None:
        return []
    today = local_today(companion, now)
    if row['status'] == 'moved':
        return living_lines(connection, companion, row, now) + share_lines(connection, companion, now)
    if row['status'] == 'moved_out':
        if not row['out_who'] or (today - date.fromisoformat(row['out_on'])).days > TOLD_DAYS:
            return []
        who = 'You moved out' if row['out_who'] == 'them' else 'The user moved out'
        return [(f"moving-in:{row['id']}:out", f"- {who} of the place you shared on {day_text(row['out_on'])}. You "
                 'no longer live together.')]
    if on_break(connection, companion):
        return []  # The move waits while they are on a break (`hold`); the 'breakup' section says where they stand.
    lines = [(f"moving-in:{row['id']}:plan", f'- {joiner_line(connection, row) if joins(row) else plan_line(connection, row)}')]
    lines += changed_line(connection, row)
    lines += share_lines(connection, companion, now)
    if row['message_id'] and row['message_id'] in fresh_ids:
        lines.append((f"moving-in:{row['id']}:just", JUST_WAITS if row['status'] == 'waiting' and joins(row) else
                      '- You just agreed to live together, and this is how it will go. Say so in this reply, in your '
                      'own words.'))
    return lines


def changed_line(connection, row: dict) -> list[tuple[str, str]]:
    """Until their next reply after the user changed the plan under Hidden values: that it changed, so the reply goes
    along with it rather than with what they said before (A/B, companion-v14 followups ab-d)."""
    found = optional(connection, "SELECT changed_at FROM consequences WHERE id=? AND picked_by='user' AND "
                     'changed_at IS NOT NULL', (row['consequence_id'] or '',))
    if found is None or joins(row) or optional(
            connection, "SELECT id FROM messages WHERE timeline_id=? AND role='companion' AND status='complete' AND "
            'active=1 AND created_at>? LIMIT 1', (row['timeline_id'], found['changed_at'])):
        return []
    return [(f"moving-in:{row['id']}:changed:{found['changed_at']}",
             f'- The plan changed: {plan_line(connection, row)} Go along with it as if you had talked it over.')]


# The Character page and Hidden values -------------------------------------------------------------------------------------

def view(connection, companion: dict, now, show_odds: bool) -> dict | None:
    """The plan or the shared home, in plain words, for the steps panel."""
    row = current(connection, companion.get('active_timeline_id') or '')
    if row is None:
        return None
    today = local_today(companion, now)
    shared = their_home(connection, companion, today) if row['status'] == 'moved' else None
    own = next((item for item in latest_shares(connection, row['id']).values() if item['newcomer']), None)
    consequence_id = own['consequence_id'] if own else row['consequence_id']
    pending = joins(row) and row['status'] != 'moved'
    ready, not_ready = readiness(connection, row) if pending else (True, [])
    return {'status': row['status'], 'plan': row['plan'], 'city': (city_of(connection, row) or {}).get('name', ''),
            'place': place_text(connection, row), 'home': shared['description'] if shared else '',
            'move_on': row['move_on'], 'moved_on': row['moved_on'], 'joins': joins(row), 'ready': ready,
            'with': mate_names(connection, row, ('moved',) if row['status'] == 'moved' else ('moved', 'moving')),
            'not_ready': not_ready,
            'newcomers': newcomers_view(connection, companion, show_odds),
            'rolls': rolls_view(connection, companion, row, show_odds) if pending else [],
            'consequence_id': consequence_id if show_odds and not pending else None}


def rolls_view(connection, companion: dict, row: dict, show_odds: bool) -> list[dict]:
    """While a move into a shared home waits or is on its way, each one's answer, the newcomer first, by name."""
    shares = latest_shares(connection, row['id'])
    people = [companion, *mates_of(connection, row)]
    return [{'name': first_name(person), 'open': bool(share['open']),
             'consequence_id': share['consequence_id'] if show_odds else None}
            for person in people if (share := shares.get(person['id']))]


def shown_with(connection, consequence_id: str, companion: dict) -> bool:
    """An answer about sharing a home that shows on this companion's page though it is another's: theirs, about this
    companion moving in."""
    found = optional(connection, 'SELECT m.timeline_id FROM moving_in_shares s JOIN moving_in m ON m.id=s.moving_in_id '
                     'WHERE s.consequence_id=?', (consequence_id,))
    return bool(found and found['timeline_id'] == companion.get('active_timeline_id'))


def change(connection, companion: dict, consequence_id: str, option: int, now) -> dict:
    """The user makes it go another way under Hidden values, while the move has not happened yet."""
    found = consequences.by_id(connection, consequence_id)
    require(found['timeline_id'] == companion['active_timeline_id'] or shown_with(connection, consequence_id, companion),
            'That outcome is not on this timeline.', 404)
    outcome = consequences.change(connection, consequence_id, option, stamp(now))
    if outcome['choice'] == SHARE:
        return change_share(connection, consequence_id, option, now)
    row = optional(connection, 'SELECT * FROM moving_in WHERE consequence_id=?', (consequence_id,))
    require(row is not None and row['status'] in ('moving', 'waiting'), 'They already moved in.', 409)
    today = local_today(companion, now)
    between = where.between(connection, companion['version']['definition'])
    plan = (MOVERS if outcome['choice'] == 'moving_in:who' else PLACES)[option]
    city, hood = place_for(connection, companion, plan, between, today)
    low, high = OTHER_CITY_DAYS if plan == 'them' else SAME_CITY_DAYS
    status = 'waiting' if plan == 'you' else 'moving'
    move_on = date.fromisoformat(row['decided_on']) + timedelta(
        days=random.Random(f"{row['timeline_id']}:{plan}:move-day").randint(low, high))
    connection.execute('UPDATE moving_in SET plan=?, status=?, city_id=?, neighbourhood=?, move_on=? WHERE id=?',
                       (plan, status, city['id'] if city else '', hood['id'] if hood else '',
                        max(move_on, today).isoformat() if status == 'moving' else None, row['id']))
    return consequences.by_id(connection, consequence_id)


def copy(connection, parent_id: str, new_id: str, cutoff_date: str) -> list[dict]:
    """A fork keeps the plan or the shared home as it stood then (timelines.py inserts the rows): a move or a move out
    that came after the fork point has not happened in the copy yet (`advance` carries a move out again on its day),
    and the outcome under Hidden values is copied with it, so it can still be changed there. Each copy keeps the row it
    came from (`origin`), so a home others moved into stays their home on the fork too."""
    rows = []
    for row in many(connection, 'SELECT * FROM moving_in WHERE timeline_id=? AND decided_on<=? ORDER BY created_at',
                    (parent_id, cutoff_date)):
        found = {**row, 'id': identifier(), 'timeline_id': new_id, 'chapter_id': None, 'home_item_id': None,
                 'message_id': None, 'out_until': None, 'origin': row.get('origin') or row['id'],
                 'consequence_id': row['consequence_id'] and consequences.copy(
                     connection, row['consequence_id'], new_id, f'moving_in:{new_id}:{len(rows) + 1}')}
        rows.append(found)
        if row['out_on'] and row['out_on'] > cutoff_date:
            found.update(status='moved', out_on=None, out_who=None)
        if found['status'] != 'moved_out' and (not row['moved_on'] or row['moved_on'] > cutoff_date):
            found.update(status='waiting' if (row['plan'] == 'you' or joins(row)) and not row['move_on'] else 'moving',
                         moved_on=None, ended_item_ids='[]')
        copy_shares(connection, row['id'], found['id'], parent_id, new_id)
    return rows
