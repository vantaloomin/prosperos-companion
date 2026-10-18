"""A health turn and caring for a parent (Hit List #68, v0.14 Years Go By): Life's big turns, part 2
(companion/life/big_turns.py). Both are hard turns, so they never come on Gentle (Vanta 2026-10-18: good turns only on an
easy life).

- `health`: the companion has not been feeling right and the doctor sends them for tests (the results go on the
  calendar, companion/life/admin.py, source 'health'). On results day they are diagnosed with a long-term condition from
  the bank (world/data/life_chapters.json `conditions`, by era and age) and the engine says how it looks
  (`health:outlook`): manageable, or a harder road with check-ups twice as often and a low mood for a while. From then on
  the check-ups come round on the calendar, each with what it costs, and the kitchen follows (the overlay's `health`:
  companion/life/kitchen.py leaves out what they must avoid and orders in less). A few months on it is part of their
  routine and the turn ends; the condition and its check-ups stay. A companion never dies of it.
- `caring`: a parent in their circle who is getting on, or just started treatment after a scare
  (companion/life/storylines.py `parent_health`), needs more help. A week or two later two of their free evenings (a
  Saturday, for a parent out of town) become time at their parent's (the overlay's `caring`, an errand block themed
  'caring' that companion/life/composer.py fills), the parent's appointments go on the calendar and a share of their
  pay goes to the parent's care each month; the money and the worry leave marks the engine reads. Every three months the
  engine says how it is going (`caring:how`): better (the help eases off and the turn ends), the same, or harder. After a
  year it is simply part of their weeks.

Hook for Loss and grief: a parent whose care went harder is `frail`, and `end_care` closes the turn (and frees the
evenings) with a reason, such as their passing. Nothing here calls a model.
"""
import random
from datetime import date, timedelta

from companion import consequences
from companion.clock import stamp
from companion.database import decode, many, optional
from companion.life import big_turns, circle, money
from companion.memory import pairs

OUTLOOK, HOW = 'health:outlook', 'caring:how'
TEST_DAYS = (7, 21)  # From the first worry until the results (on the calendar from the start).
SETTLE_DAYS = (120, 180)  # From the diagnosis until it is part of their routine.
CHECKUPS_AHEAD = 21  # Check-ups and a parent's appointments go on the calendar this many days ahead.
# A check-up's cost as a share of a month's take-home, by era (a co-pay today, the doctor's fee in the past).
CHECKUP_COST = {'modern': 0.01, 'jazz-age': 0.02, 'other': 0.01}
CARE_FROM = 25  # The youngest who takes on a parent's care.
OLD_PARENT = 60  # A parent this old (or one in treatment) may need care.
ILL_DAYS = 180  # How long after a parent starts treatment it counts.
CARE_START = (5, 14)  # From deciding until the first evening at their parent's.
CARE_CHECK = 91
CARE_CHECKS = 4
CARE_COST = {'modern': 0.1, 'jazz-age': 0.08, 'other': 0.05}  # A month's share of their take-home.
APPOINTMENT_WEEKS = 4
CARE_OUTCOMES = ('better', 'same', 'harder')


# A health turn -------------------------------------------------------------------------------------------------

def plan_health(connection, companion, world, day, seed) -> dict | None:
    age = big_turns.free(connection, companion, day)
    definition = companion['version']['definition']
    if age is None or definition.get('health'):
        return None
    city = big_turns.city_of(definition, world)
    options = [entry for entry in big_turns.data()['conditions'][big_turns.era(city)] if entry['min_age'] <= age]
    if not options:
        return None
    condition = random.Random(f'{seed}:condition').choice(options)
    results = day + timedelta(days=random.Random(f'{seed}:results').randint(*TEST_DAYS))
    name, when = big_turns.first(definition), big_turns.day_text(results)
    return {'title': f'{name} is waiting on test results',
            'told': f"You haven't been feeling right lately, and the doctor sent you for tests; the results come on "
                    f'{when}.',
            'share': f"Doctor's sending me for some tests. Probably nothing, but I'll know on {when}.",
            'details': {'stage': 'tests', 'next_on': results.isoformat(), 'results_on': results.isoformat(),
                        'condition': condition, 'cost': checkup_cost(definition, city)}}


def checkup_cost(definition: dict, city: dict | None) -> float:
    found = money.profile(definition)
    return round(money.monthly_share(found) * CHECKUP_COST[big_turns.era(city)], 2) if found else 0.0


def diagnosed(connection, companion, row, details, day, now) -> dict:
    """Results day: the condition, and how it looks."""
    definition, condition = companion['version']['definition'], details['condition']
    name = big_turns.first(definition)
    outcome = consequences.decide(
        connection, timeline_id=row['timeline_id'], choice=OUTLOOK, subject=f"health:{row['id']}",
        facts={'age': big_turns.age_of(connection, companion, day), 'drama': drama(connection)},
        names={'name': name, 'a': condition['condition'], 'b': ''},
        labels=[option['label'].format(name=name, a=condition['condition'])
                for option in consequences.tables()[OUTLOOK]['options']],
        day=day.isoformat(), timestamp=stamp(now), holders={'me': pairs.companion_key(companion['id'])}, now=now)
    harder = outcome['picked'] == 1
    every = max(2, condition['every'] // 2) if harder else condition['every']
    settles = day + timedelta(days=random.Random(f"{row['id']}:settles").randint(*SETTLE_DAYS))
    told = (f"You were diagnosed with {condition['condition']} on {big_turns.day_text(day)}. It is something you will "
            f"live with; the doctor wants you to {condition['advice']}, and you have a {condition['checkup'].lower()} "
            f"every {weeks(every)}.") + (' It has been a harder road than you hoped.' if harder else '')
    return {'title': f"{name} was diagnosed with {condition['condition']}", 'changes': changes(condition),
            'told': told, 'share': f"Got my results. It's {condition['condition']}. Not the end of the world, but it's "
                                   'a lot to take in.',
            'undo': {'decided': [outcome['id']]},
            'details': {'stage': 'managing', 'diagnosed_on': day.isoformat(), 'every': every,
                        'outlook': 'harder' if harder else 'manageable', 'next_on': settles.isoformat()}}


def weeks(count: int) -> str:
    return 'week' if count == 1 else f'{count} weeks'


def changes(condition: dict) -> dict:
    return {'health': {key: condition[key] for key in ('condition', 'short', 'avoid', 'checkup')}}


def living_with(connection, companion, row, details, day, now) -> dict:
    condition = details['condition']
    name = big_turns.first(companion['version']['definition'])
    return {'title': f"{name} is living with {condition['condition']}", 'changes': changes(condition),
            'told': f"You have been living with {condition['condition']} for a few months now; the check-ups and "
                    'looking after yourself are part of your routine.',
            'share': f"Few months into the {condition['short'].lower()} thing. I've got a routine now.",
            'details': {'stage': 'living_with', 'next_on': None}}


def drama(connection) -> int:
    from companion.life import storylines
    return storylines.drama(connection)


# Caring for a parent -------------------------------------------------------------------------------------------

def parent_ill(connection, timeline_id: str, day: date) -> set[str]:
    """Parents who started treatment after a health scare (storylines.py `parent_health`) in the last half year."""
    since = (day - timedelta(days=ILL_DAYS)).isoformat()
    found = set()
    for row in many(connection, "SELECT cast_ids, stages FROM storylines WHERE timeline_id=? AND story='parent_health' "
                    'AND started_on>=?', (timeline_id, since)):
        last = decode(row['stages'])[-1]
        if last.get('tone') == 'bad' and last['on'] <= day.isoformat():
            found.update(decode(row['cast_ids'])[:1])
    return found


def parents(connection, companion: dict, day: date) -> list[tuple[dict, int, bool]]:
    """(parent, age, ill) for parents in the circle who might need care now, the most in need first."""
    timeline_id = companion['active_timeline_id']
    ill = parent_ill(connection, timeline_id, day)
    found = []
    for person in circle.people(connection, timeline_id):
        if circle.role_kind(person['role']) != 'parent' or cared_for(connection, timeline_id, person['id']):
            continue
        age = decode(person['details']).get('age') or 0
        if age >= OLD_PARENT or person['id'] in ill:
            found.append((person, age, person['id'] in ill))
    return sorted(found, key=lambda item: (not item[2], -item[1], item[0]['ordinal']))


def cared_for(connection, timeline_id: str, person_id: str) -> bool:
    return optional(connection, "SELECT id FROM life_chapters WHERE timeline_id=? AND kind='caring' AND undone_at IS NULL "
                    "AND json_extract(details, '$.parent')=? AND json_extract(details, '$.stage')!='eased'",
                    (timeline_id, person_id)) is not None


def facts(connection, companion: dict, day: date) -> dict:
    """What the engine reads for caring: the age of the parent most in need, and whether they are in treatment."""
    found = parents(connection, companion, day)
    return {'parent_age': found[0][1] if found else 0, 'parent_ill': int(bool(found and found[0][2]))}


def plan_caring(connection, companion, world, day, seed) -> dict | None:
    age = big_turns.free(connection, companion, day)
    found = parents(connection, companion, day)
    definition = companion['version']['definition']
    if age is None or age < CARE_FROM or not found:
        return None
    person, _age, _ill = found[0]
    local = decode(person['details']).get('local', True)
    slot = big_turns.class_slot(definition, f'{seed}:care', evenings=local)
    if not slot:
        return None
    role = circle.said(person['role'], definition)
    slot['label'] = f"{'Evening' if slot['start'] >= '17:00' else 'Day'} at {role.capitalize()}'s"
    start = day + timedelta(days=random.Random(f'{seed}:care-start').randint(*CARE_START))
    city = big_turns.city_of(definition, world)
    budget = money.profile(definition)
    cost = round(money.monthly_share(budget) * CARE_COST[big_turns.era(city)], 2) if budget else 0.0
    name, when, days = big_turns.first(definition), big_turns.day_text(start), big_turns.days_text(slot['days'])
    return {'title': f"{name} is taking on their {role} {person['name']}'s care",
            'told': f"Your {role} {person['name']} needs more help now, so you are taking it on: from {when} you spend "
                    f'{days} at their place, and you help with their bills.',
            'share': f"My {role} needs more help these days, so I'm going to be over there {days}. It's the right thing, "
                     "but it's a lot.",
            'details': {'stage': 'starting', 'next_on': start.isoformat(), 'starts_on': start.isoformat(),
                        'parent': person['id'], 'role': role, 'name': person['name'], 'caring': slot, 'cost': cost,
                        'checks': 0, 'outlook': 'steady'}}


def care_begins(connection, companion, row, details, day, now) -> dict:
    name = big_turns.first(companion['version']['definition'])
    return {'title': f"{name} is caring for their {details['role']} {details['name']}",
            'changes': {'caring': details['caring']},
            'told': f"You are caring for your {details['role']} {details['name']}: you spend "
                    f"{big_turns.days_text(details['caring']['days'])} at their place, take them to their appointments "
                    'and help with their bills.',
            'share': f"First evening at my {details['role']}'s as their helper. We made it work.",
            'details': {'stage': 'caring', 'starts_on': day.isoformat(),
                        'next_on': (day + timedelta(days=CARE_CHECK)).isoformat()}}


def care_check(connection, companion, row, details, day, now) -> dict:
    """Three months on: the engine says how it is going."""
    definition = companion['version']['definition']
    person = optional(connection, 'SELECT details FROM circle_people WHERE id=?', (details['parent'],))
    name = big_turns.first(definition)
    names = {'name': name, 'a': details['name'], 'b': ''}
    outcome = consequences.decide(
        connection, timeline_id=row['timeline_id'], choice=HOW, subject=f"caring:{row['id']}:{details['checks']}",
        facts={'age_a': decode(person['details']).get('age') if person else None, 'drama': drama(connection),
               'turns': big_turns.level(connection), 'checks': details['checks']}, names=names,
        labels=[option['label'].format(**names) for option in consequences.tables()[HOW]['options']],
        day=day.isoformat(), timestamp=stamp(now), holders={'me': pairs.companion_key(companion['id'])}, now=now)
    picked, checks = CARE_OUTCOMES[outcome['picked']], details['checks'] + 1
    parent = f"{details['role']} {details['name']}"
    if picked == 'better':
        return {'title': f"{name}'s {parent} is doing better", 'changes': {}, 'undo': {'decided': [outcome['id']]},
                'told': f'Your {parent} is doing better and needs less help, so your evenings are your own again.',
                'share': f"Good news: my {details['role']}'s doing so much better. They don't need me over there all "
                         'the time anymore.',
                'details': {'stage': 'eased', 'checks': checks, 'how': picked, 'ended_on': day.isoformat(),
                            'next_on': None}}
    harder = picked == 'harder' or details.get('outlook') == 'declining'
    settled = checks >= CARE_CHECKS
    told = (f'Your {parent} needs more help than before, and it is wearing on you.' if picked == 'harder' else
            f'Caring for your {parent} goes on much as before.') + \
        (' It is part of your weeks now.' if settled else '')
    return {'title': f"{name} is caring for their {parent}", 'changes': {'caring': details['caring']},
            'undo': {'decided': [outcome['id']]}, 'told': told,
            'share': f"Rough few weeks with my {details['role']}. They need more help than before." if picked == 'harder'
            else f"Still going over to my {details['role']}'s. We've got a rhythm.",
            'details': {'stage': 'settled' if settled else 'caring', 'checks': checks, 'how': picked,
                        'outlook': 'declining' if harder else 'steady',
                        'next_on': None if settled else (day + timedelta(days=CARE_CHECK)).isoformat()}}


def frail(connection, timeline_id: str) -> list[dict]:
    """Parents whose care went harder, for Loss and grief: [{chapter_id, person_id, since}]."""
    return [{'chapter_id': row['id'], 'person_id': decode(row['details'])['parent'],
             'since': decode(row['details']).get('stage_on') or row['started_on']}
            for row in many(connection, "SELECT * FROM life_chapters WHERE timeline_id=? AND kind='caring' AND "
                            "undone_at IS NULL AND json_extract(details, '$.outlook')='declining' AND "
                            "json_extract(details, '$.ended_on') IS NULL", (timeline_id,))]


def end_care(connection, companion: dict, chapter_id: str, day: date, why: str, told: str, share: str):
    """Close a caring turn from outside (Loss and grief: `why` 'passed'): the evenings are theirs again, and the costs
    and appointments stop. `told` and `share` say what happened."""
    row = optional(connection, 'SELECT * FROM life_chapters WHERE id=?', (chapter_id,))
    details = decode(row['details'])
    big_turns.save_stage(connection, row, {
        'title': row['title'], 'told': told, 'share': share, 'changes': {},
        'details': {'stage': 'ended', 'why': why, 'ended_on': day.isoformat(), 'next_on': None}}, day)
    connection.execute("UPDATE life_admin SET status='removed' WHERE timeline_id=? AND source='health' AND key LIKE ? "
                       "AND status='planned'", (row['timeline_id'], f"health:{row['id']}:%"))
    return details


PLANS = {'health': plan_health, 'caring': plan_caring}
STAGES = {('health', 'tests'): diagnosed, ('health', 'managing'): living_with, ('caring', 'starting'): care_begins,
          ('caring', 'caring'): care_check}


# The calendar and money ----------------------------------------------------------------------------------------

def rows(connection, timeline_id: str) -> list[dict]:
    return many(connection, "SELECT * FROM life_chapters WHERE timeline_id=? AND undone_at IS NULL AND kind IN "
                "('health', 'caring')", (timeline_id,))


def dates(details: dict, kind: str, today: date, until: date) -> list[date]:
    """Appointment days between two dates: test results; then a check-up every so many weeks from the diagnosis, or a
    parent's appointment every four weeks while caring."""
    if kind == 'health' and details['stage'] == 'tests':
        found = [date.fromisoformat(details['results_on'])]
    elif kind == 'health':
        found = every(date.fromisoformat(details['diagnosed_on']), details['every'], today, until)
    elif details['stage'] in ('caring', 'settled'):
        found = every(date.fromisoformat(details['starts_on']), APPOINTMENT_WEEKS, today, until)
    else:
        found = []
    return [day for day in found if today <= day <= until]


def every(start: date, weeks_apart: int, today: date, until: date) -> list[date]:
    step = timedelta(weeks=weeks_apart)
    first = start + step * max(1, -(-(today - start).days // step.days))
    found = []
    while first <= until:
        found.append(first)
        first += step
    return found


def calendar(connection, companion: dict, today: date, now) -> int:
    """Test results, check-ups and a parent's appointments coming up in the next three weeks go on the shared calendar,
    held like any appointment booked with someone else."""
    from companion.life import admin
    added = 0
    for row in rows(connection, companion['active_timeline_id']):
        details = decode(row['details'])
        for day in dates(details, row['kind'], today, today + timedelta(days=CHECKUPS_AHEAD)):
            key, what = f"health:{row['id']}:{day.isoformat()}", entry(row['kind'], details)
            # Booked in office hours; someone who works them all week gets an evening clinic that can move.
            added += bool(admin.add(connection, companion, key=key, source='health', day=day, at='10:00', minutes=90,
                                    fixed=True, out=True, now=now, **what)
                          or admin.add(connection, companion, key=key, source='health', day=day, minutes=90,
                                       out=True, now=now, **what))
    return added


def entry(kind: str, details: dict) -> dict:
    if kind == 'caring':
        return {'kind': 'care', 'title': f"{details['role'].capitalize()}'s appointment",
                'done': f"took their {details['role']} to an appointment"}
    if details['stage'] == 'tests':
        return {'kind': 'results', 'title': 'Test results', 'done': 'got their test results'}
    condition = details['condition']
    return {'kind': 'checkup', 'title': condition['checkup'], 'done': f"went to their {condition['checkup'].lower()}",
            'cost': details.get('cost') or 0.0}


def purchases(connection, timeline_id: str, start: date, end: date) -> list[dict]:
    """A share of their pay toward a parent's care each month they care for them, from the day it began."""
    found = []
    for row in rows(connection, timeline_id):
        details = decode(row['details'])
        if row['kind'] != 'caring' or details['stage'] not in ('caring', 'settled') or not details.get('cost'):
            continue
        first = date.fromisoformat(details['starts_on'])
        last = min(end, date.fromisoformat(details['ended_on'])) if details.get('ended_on') else end
        month, paid = 0, first
        while paid <= last:
            if paid >= start:
                found.append({'text': f"helped with your {details['role']}'s care", 'date': paid.isoformat(),
                              'shown': f"paid toward their {details['role']} {details['name']}'s care",
                              'cost': details['cost'], 'spend': '', 'for': 'care'})
            month += 1
            paid = big_turns.later(first, month)
    return found


# The Character page -------------------------------------------------------------------------------------------

def health_line(row: dict, details: dict) -> str:
    if details['stage'] == 'tests':
        return f"Waiting on test results; they come {big_turns.short_day(details['results_on'])}."
    condition = details['condition']
    return f"Living with {condition['condition']}; a {condition['checkup'].lower()} every {weeks(details['every'])}."


def caring_line(row: dict, details: dict) -> str:
    parent = f"their {details['role']} {details['name']}"
    if details['stage'] == 'starting':
        return f"Taking on {parent}'s care from {big_turns.short_day(details['starts_on'])}."
    return f"Caring for {parent} on {big_turns.days_text(details['caring']['days'])}."


LINES = {'health': health_line, 'caring': caring_line}
