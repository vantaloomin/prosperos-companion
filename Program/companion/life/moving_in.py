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
"""
import random
import re
from datetime import date, datetime, timedelta

from companion import consequences
from companion.clock import parse, stamp, zone
from companion.database import decode, encode, identifier, many, optional
from companion.errors import require
from companion.life import home, money, steps, where

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
# How long the chat context keeps moving day, and a move out.
TOLD_DAYS = 3
UNITS = ('shared', 'studio', 'one_bedroom', 'two_bedroom')
TASKS = ('cooking', 'dishes', 'laundry', 'tidying')

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
    elif row['status'] == 'moving' and row['move_on'] <= today.isoformat():
        move(connection, companion, row, now)
    elif row['status'] == 'waiting':
        settle_waiting(connection, companion, row, now)
    elif row['status'] == 'moved' and moved_away(connection, row):
        move_out(connection, companion, now, 'you')


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
    if row['plan'] in ('yours', 'new', 'them'):
        changes, found = rehome(connection, companion, row, day, now)
    else:
        share_theirs(connection, companion, row, day, True)
    if row['plan'] == 'them':
        changes.update(city_changes(connection, companion, row))
        found['removed'] = leave_behind(connection, companion, now)
    if changes:
        chapter = insert_chapter(connection, companion, row, day, changes, found, now)
    connection.execute("UPDATE moving_in SET status='moved', moved_on=?, chapter_id=?, home_item_id=?, "
                       'ended_item_ids=? WHERE id=?', (day.isoformat(), chapter, (found['added'] or [None])[0],
                                                       encode(found['ended']), row['id']))


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
        details.update({'bedrooms': unit, 'rent': int(round(rent / 25) * 25), 'rent_from': 'shared',
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
    if row['plan'] == 'them':
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
    """The one who moved in moves out; from a new place, whoever can't manage its rent alone (them, when unknown)."""
    if row['plan'] in ('yours', 'them'):
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
    if leaving == 'them' and not chapter_undone(connection, row):
        place_of_their_own(connection, companion, row, today, now)
    elif leaving == 'you':
        share_theirs(connection, companion, row, today, False)
    connection.execute("UPDATE moving_in SET status='moved_out', out_on=?, out_who=? WHERE id=?",
                       (today.isoformat(), leaving, row['id']))
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
    status = 'moved' if row['moved_on'] else 'waiting' if row['plan'] == 'you' else 'moving'
    connection.execute('UPDATE moving_in SET status=?, out_on=NULL, out_who=NULL WHERE id=?', (status, row['id']))
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


# Living together ------------------------------------------------------------------------------------------------------

def split(connection, timeline_id: str, costs: dict | None, day: date) -> dict | None:
    """The home's costs for their budget (money.py): living together, they pay half the rent."""
    if not costs or not costs.get('rent'):
        return costs
    row = current(connection, timeline_id)
    if not row or row['status'] != 'moved' or row['moved_on'] > day.isoformat():
        return costs
    return {**costs, 'rent': round(costs['rent'] / 2, 2), 'shared': True}


def turn(companion: dict, day: date, task: str) -> str:
    """Whose turn a chore is today, 'you' (the companion) or 'user', by rules: on their work days the user cooks and
    they do the dishes; on other days cooking takes turns and the dishes go to whoever didn't cook; laundry and
    tidying take turns week by week."""
    from companion.life import upkeep
    seed = random.Random(f"{companion['active_timeline_id']}:{task}:turns").randrange(2)
    if task in ('cooking', 'dishes'):
        cooks = 'user' if day.weekday() in upkeep.busy_days(companion['version']['definition']) else \
            ('you', 'user')[(day.toordinal() + seed) % 2]
        return cooks if task == 'cooking' else ('user' if cooks == 'you' else 'you')
    return ('you', 'user')[(day.isocalendar()[1] + seed) % 2]


def out_now(row: dict, now: datetime) -> bool:
    return bool(row['out_until'] and parse(row['out_until']) > now)


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
    if out_now(row, now):
        return {'status': 'out', 'until': row['out_until']}
    return {'status': 'home'} if home_state(connection, companion, now) else None


def set_out(connection, companion: dict, out: bool, now: datetime) -> None:
    row = living(connection, companion, local_today(companion, now))
    require(row is not None, 'You do not live together.', 409)
    connection.execute('UPDATE moving_in SET out_until=? WHERE id=?', (stamp(now + OUT_FOR) if out else None, row['id']))


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
        connection.execute('UPDATE moving_in SET out_until=NULL WHERE id=?', (row['id'],))
    elif OUT.search(message['text']):
        connection.execute('UPDATE moving_in SET out_until=? WHERE id=?', (stamp(now + OUT_FOR), row['id']))
    skipped(connection, companion, row, message['text'], now)


def skipped(connection, companion: dict, row: dict, text: str, now: datetime):
    """A chore the user says they left undone on their own turn: everyday friction, at most one roll a chore a day."""
    found = SKIPPED.search(text)
    task = found and next(task for start, task in SKIPPED_TASKS if found['task'].lower().startswith(start))
    today = local_today(companion, now)
    if not task or turn(companion, today, task) != 'user':
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


def chores_text(companion: dict, day: date) -> str:
    """Whose turn the chores are today: "Today cooking is yours; the dishes, the laundry and tidying up are the
    user's." """
    who = {task: turn(companion, day, task) for task in TASKS}
    parts = []
    for side, owner in (('you', 'yours'), ('user', "the user's")):
        tasks = [CHORES[task] for task in TASKS if who[task] == side]
        if tasks:
            parts.append(f"{listed(tasks)} {'is' if len(tasks) == 1 else 'are'} {owner}")
    return f"Today {'; '.join(parts)}."


def living_lines(connection, companion: dict, row: dict, now: datetime) -> list[tuple[str, str]]:
    from companion.life import outings, pets
    today = local_today(companion, now)
    since = 'today' if row['moved_on'] == today.isoformat() else f"since {day_text(row['moved_on'])}"
    shared = their_home(connection, companion, today)
    what = shared['description'] if shared else f'a place in {place_text(connection, row)}'
    yours = [found['name'] for found in pets.of_persona(connection)]
    animals = f" The user's pets ({', '.join(yours)}) live there too and are both of yours now." if yours else ''
    lines = [(f"moving-in:{row['id']}:home",
              f"- You and the user live together, {since}, at {what}. You split the rent and the bills. "
              f'{chores_text(companion, today)}{animals}')]
    if row['moved_on'] == today.isoformat():
        lines.append((f"moving-in:{row['id']}:today", '- Today was moving day: you just moved in together.'))
    if home_state(connection, companion, now):
        lines.append((f"moving-in:{row['id']}:evening", '- It is evening and you are both home, together in person. '
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
        return living_lines(connection, companion, row, now)
    if row['status'] == 'moved_out':
        if not row['out_who'] or (today - date.fromisoformat(row['out_on'])).days > TOLD_DAYS:
            return []
        who = 'You moved out' if row['out_who'] == 'them' else 'The user moved out'
        return [(f"moving-in:{row['id']}:out", f"- {who} of the place you shared on {day_text(row['out_on'])}. You "
                 'no longer live together.')]
    if on_break(connection, companion):
        return []  # The move waits while they are on a break (`hold`); the 'breakup' section says where they stand.
    lines = [(f"moving-in:{row['id']}:plan", f'- {plan_line(connection, row)}')]
    if row['message_id'] and row['message_id'] in fresh_ids:
        lines.append((f"moving-in:{row['id']}:just", '- You just agreed to live together, and this is how it will '
                      'go. Say so in this reply, in your own words.'))
    return lines


# The Character page and Hidden values -------------------------------------------------------------------------------------

def view(connection, companion: dict, now, show_odds: bool) -> dict | None:
    """The plan or the shared home, in plain words, for the steps panel."""
    row = current(connection, companion.get('active_timeline_id') or '')
    if row is None:
        return None
    shared = their_home(connection, companion, local_today(companion, now)) if row['status'] == 'moved' else None
    return {'status': row['status'], 'plan': row['plan'], 'city': (city_of(connection, row) or {}).get('name', ''),
            'place': place_text(connection, row), 'home': shared['description'] if shared else '',
            'move_on': row['move_on'], 'moved_on': row['moved_on'],
            'consequence_id': row['consequence_id'] if show_odds else None}


def change(connection, companion: dict, consequence_id: str, option: int, now) -> dict:
    """The user makes it go another way under Hidden values, while the move has not happened yet."""
    outcome = consequences.change(connection, consequence_id, option, stamp(now))
    require(outcome['timeline_id'] == companion['active_timeline_id'], 'That outcome is not on this timeline.', 404)
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
    """A fork keeps the plan or the shared home as it stood then (timelines.py inserts the rows)."""
    return [{**row, 'id': identifier(), 'timeline_id': new_id, 'chapter_id': None, 'home_item_id': None,
             'message_id': None, 'out_until': None}
            for row in many(connection, 'SELECT * FROM moving_in WHERE timeline_id=? AND decided_on<=?',
                            (parent_id, cutoff_date))]

