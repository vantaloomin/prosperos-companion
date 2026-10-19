"""Expecting or adopting together (Hit List #73, v0.15 Room to Grow): once the user and a romance companion have
decided to start a family (companion/life/parenthood.py), the child comes, by the route picked for the pair.

The app decides, the user overrides ("the world exists outside of User", Vanta 2026-10-08). Everything is planned the
day it begins, from seeds and the consequence engine (odds under Hidden values), never by a model:

- Expecting (either of them, or a surrogate in a modern city): how long it takes to find out (family:soon), then a
  pregnancy over about nine months in real time: the news, telling their people (News travels, companion/news.py;
  how each took it from the bank), appointments on the Life admin calendar, the nursery and baby things from their
  money (life admin costs, companion/life/admin.py; a shared home too small grows a size through moving_in.grow), a
  baby shower as a big day in a modern city (companion/life/big_days.py `own_shower`), "any day now" and the birth.
  On Real life and Drama a pregnancy can take a hard turn (family:turn): bed rest, or an early arrival. Never a loss.
- Adopting: the agency, a home study, the wait (family:wait), the match and the day the child comes home; a baby or
  an older child (family:match). Fostering: the training, the home study, a placement, and with family:fostered
  adopting them some months on. Older cities take in a ward, a foundling or a relative's child.
- The app picks the child's name (never the companion's, the persona's, someone in their circle's or a word from a
  place in their city, as families.baby_name); the companion suggests it, and the user can rename them on the
  Character page. Born or home, the child is in `circle_children` as the pair's own (title 'ours', parent_id the
  companion), where Our child picks them up.

The chat context hears it in the 'steps' section through parenthood.context_lines: what stage it is at, the latest
moment and what comes next; first texts tell the news (`news_due`). Children keep v0.14's limits: words only (the
child's name is in families.names, so no picture is made of words naming them, and the shower has no photo), never
in Matchlight or the circle (`circle_children`, not circle_people), and with the adult side of life on nothing of it
goes in a chat prompt, a first text, the news or the calendar (`quiet`); it stays on the screens.
"""
import json
import random
from datetime import date, timedelta
from functools import cache

from companion import consequences
from companion.clock import stamp, zone
from companion.database import decode, encode, identifier, many, optional
from companion.errors import require
from companion.life import admin, circle, families, pronouns, steps
from companion.life.steps import FAMILY
from companion.world import catalog, generators

ACTIVE = True
# The news as a first text; off in most tests (tests/conftest.py).
FIRST_TEXTS = True
PREGNANCY = ('expecting_them', 'expecting_you', 'surrogacy')
ADOPTING = ('adoption',)
FOSTERING = ('fostering',)
TAKING_IN = ('ward', 'foundling', 'relative')
STATUSES = ('planned', 'running', 'home', 'called_off')
# family:soon, in days from deciding: how long until they find out they are expecting (or a surrogate is).
SOON_DAYS = ((14, 60), (60, 180), (180, 330))
# family:wait, in days from the agency: how long until a match.
WAIT_DAYS = ((90, 180), (180, 330), (330, 540))
# family:match: a baby, a young child (1 to 4) or an older one (5 to 11).
MATCH_AGES = ((0, 0), (1, 4), (5, 11))
TURNS = ('none', 'bed_rest', 'early')
# A pregnancy: found out about five weeks in, so due thirty-five weeks (forty in all) after the news.
DUE_AFTER = 245
RECENT_DAYS = 21
# After the child arrives, the birth or homecoming stays in the chat this long, as news.
ARRIVED_DAYS = 14
MOMENTS = 5
ERA_WORDS = {'modern': {'appointment': 'First scan', 'halfway': '20-week scan', 'birth': 'at the hospital',
                        'things': ('a crib', 'a car seat', 'a stroller', 'a changing table', 'a baby monitor')},
             # A jazz-age city (New York 1925): the doctor, no scans, a pram rather than a stroller.
             'jazz': {'appointment': "The doctor's visit", 'halfway': "The doctor's visit", 'birth': 'at the hospital',
                      'things': ('a crib', 'a bassinet', 'a pram', 'a high chair', 'a rocking chair')},
             # Victorian to Camelot: nothing that one of them lacks.
             'old': {'appointment': "The midwife's visit", 'halfway': "The midwife's visit", 'birth': 'at home, with the '
                     'midwife', 'things': ('a cradle', 'linens and swaddling', 'a woollen blanket', 'a little cap')}}
TOLD_PEOPLE = 3
# The baby shower is at least this many days before the birth, even an early one.
SHOWER_BEFORE = 7


@cache
def bank() -> dict:
    return json.loads((catalog.DATA / 'expecting.json').read_text(encoding='utf-8'))


def local_today(companion: dict, now) -> date:
    return now.astimezone(zone(companion['version']['timezone'])).date()


def quiet(connection) -> bool:
    """With the adult side of life on, none of it is in a chat prompt, a first text, the news or the calendar."""
    return families.withheld(connection)


def current(connection, timeline_id: str) -> dict | None:
    row = optional(connection, "SELECT * FROM family_journeys WHERE timeline_id=? AND status!='called_off' "
                   'ORDER BY created_at DESC LIMIT 1', (timeline_id,))
    return view(row) if row else None


def view(row: dict) -> dict:
    return {**row, 'stages': decode(row['stages']) or [], 'details': decode(row['details']) or {}}


def era_group(connection, companion: dict) -> str:
    """'modern', 'jazz' (a jazz-age city) or 'old' (Victorian to Camelot), for ERA_WORDS."""
    from companion.life import parenthood
    found = parenthood.era(connection, companion)
    if found in parenthood.OLD_ERAS:
        return 'old'
    return 'jazz' if found == 'jazz-age' else 'modern'


def modern(connection, companion: dict) -> bool:
    return era_group(connection, companion) == 'modern' and families.era_of(
        connection, companion['version']['definition']) not in families.UNFIT


def fitting(lines: list[dict], connection, companion: dict) -> list[dict]:
    """The bank lines for their city: every line in a modern one, only those for any era elsewhere, and none naming
    something the era lacks (families.UNFIT: no tea in Camelot)."""
    if modern(connection, companion):
        return lines
    unfit = families.UNFIT.get(families.era_of(connection, companion['version']['definition']))
    return [line for line in lines if line.get('era') == 'any' and not (unfit and unfit.search(line['text']))] or lines


# Starting --------------------------------------------------------------------------------------------------------------

def decided_on(connection, companion: dict) -> str | None:
    """When they decided on the child to come: starting a family for the first, another child once one is home."""
    from companion.life import parenthood
    timeline_id = companion['active_timeline_id']
    homes = len(many(connection, "SELECT id FROM family_journeys WHERE timeline_id=? AND status='home'", (timeline_id,)))
    row = parenthood.reached(connection, timeline_id, steps.SIBLING.key if homes else steps.FAMILY.key)
    return row['reached_on'] if row and homes < parenthood.MOST_CHILDREN else None


def facts(connection, companion: dict, now) -> dict:
    """What the engine reads for a journey: their age, the route, whether a hard turn can happen (Real life and Drama,
    by Life's big turns) and the city's era."""
    from companion.life import big_turns, parenthood
    route = parenthood.route_found(connection, companion)['route']
    found = parenthood.route_facts(connection, companion, now)
    carrier = found['your_age'] if route == 'expecting_you' else found['age']
    return {'age': carrier or found['age'], 'turns': int(big_turns.level(connection) > big_turns.GENTLE),
            'route': route, 'old': found['old'], 'tier': found['tier']}


def decide(connection, companion: dict, choice: str, journey_id: str, found: dict, now) -> dict:
    return steps.decide(connection, companion, choice, f'{choice}:{journey_id}', found, FAMILY.topic, now)


def begin(connection, companion: dict, world, now) -> dict | None:
    """The day after the family step (or another child) is reached, everything about how the child comes is planned."""
    from companion.life import parenthood
    timeline_id, decided = companion['active_timeline_id'], decided_on(connection, companion)
    row = current(connection, timeline_id)
    if not decided or row and (row['status'] != 'home' or row['started_on'] >= decided):
        return None
    route = parenthood.route_found(connection, companion, now)['route']
    journey_id, timestamp = identifier(), stamp(now)
    connection.execute(
        'INSERT INTO family_journeys (id, timeline_id, companion_id, route, status, decided_on, started_on, stages, '
        "details, created_at, updated_at) VALUES (?, ?, ?, ?, 'planned', ?, ?, '[]', '{}', ?, ?)",
        (journey_id, timeline_id, companion['id'], route, decided, decided, timestamp, timestamp))
    plan(connection, companion, world, current(connection, timeline_id), now)
    return current(connection, timeline_id)


def picks(connection, companion: dict, row: dict, now) -> dict:
    """The engine's outcomes for this journey (recorded once; a change under Hidden values is read back here)."""
    found, route = facts(connection, companion, now), row['route']
    result = {}
    if route in PREGNANCY:
        result['soon'] = decide(connection, companion, 'family:soon', row['id'], found, now)
        result['turn'] = decide(connection, companion, 'family:turn', row['id'], found, now)
    if route in ADOPTING:
        result['wait'] = decide(connection, companion, 'family:wait', row['id'], found, now)
    if route in ADOPTING + FOSTERING:
        result['match'] = decide(connection, companion, 'family:match', row['id'], found, now)
    if route in FOSTERING:
        result['fostered'] = decide(connection, companion, 'family:fostered', row['id'], found, now)
    return result


def plan(connection, companion: dict, world, row: dict, now) -> None:
    """Works out the stages with their days. Stages already reached keep their days; a name the user gave stays."""
    found = picks(connection, companion, row, now)
    start, seed = date.fromisoformat(row['started_on']), f"journey:{row['id']}"
    builder = {**{route: pregnancy for route in PREGNANCY}, **{route: adopting for route in ADOPTING + FOSTERING},
               **{route: taking_in for route in TAKING_IN}}[row['route']]
    stages, details = builder(connection, companion, row, start, seed, found)
    details = {**details, **child(connection, companion, world, row, seed, details)}
    today = local_today(companion, now).isoformat()
    kept = [stage for stage in row['stages'] if stage['on'] <= today]
    keys = {stage['key'] for stage in kept}
    stages = sorted(kept + [stage for stage in stages if stage['key'] not in keys and stage['on'] > today],
                    key=lambda stage: (stage['on'], stage['key']))
    ids = {key: item['id'] for key, item in found.items()}
    connection.execute('UPDATE family_journeys SET stages=?, details=?, due_on=?, consequences=?, updated_at=? '
                       'WHERE id=?', (encode(stages), encode(details), details.get('due_on'), encode(ids), stamp(now),
                                      row['id']))


def at(day: date, key: str, **values) -> dict:
    return {'key': key, 'on': day.isoformat(), **values}


def span(seed: str, label: str, low_high: tuple[int, int]) -> int:
    low, high = low_high
    return low + int(generators.unit(seed, label) * (high - low + 1))


def pregnancy(connection, companion: dict, row: dict, start: date, seed: str, found: dict) -> tuple[list, dict]:
    """The news, telling their people, the scans, the nursery and baby things, the shower, the name, "any day now" and
    the birth, with a hard turn when the engine picked one."""
    stages, surrogate = [], row['route'] == 'surrogacy'
    if surrogate:
        stages.append(at(start + timedelta(days=span(seed, 'agency', (7, 21))), 'agency'))
    news = start + timedelta(days=span(seed, 'soon', SOON_DAYS[found['soon']['picked']]))
    due = news + timedelta(days=DUE_AFTER)
    turn = TURNS[found['turn']['picked']]
    born = due + timedelta(days=span(seed, 'born', (-10, 9)))
    if turn == 'early':
        born = due - timedelta(days=span(seed, 'early', (21, 35)))
    scan = news + timedelta(days=span(seed, 'scan', (42, 49)))
    halfway = news + timedelta(days=span(seed, 'halfway', (105, 112)))
    stages += [at(news, 'news'), at(scan, 'appointment'), at(scan + timedelta(days=span(seed, 'told', (2, 6))), 'told'),
               at(halfway, 'halfway'), at(news + timedelta(days=span(seed, 'nursery', (140, 170))), 'nursery'),
               at(news + timedelta(days=span(seed, 'things', (175, 200))), 'things')]
    if modern(connection, companion):
        stages.append(at(halfway + timedelta(days=span(seed, 'name', (14, 40))), 'name'))
        shower = due - timedelta(days=span(seed, 'shower', (35, 42)))
        shower += timedelta(days=(5 - shower.weekday()) % 7)
        if shower > born - timedelta(days=SHOWER_BEFORE):  # An early arrival: the Saturday a week or more before.
            shower = born - timedelta(days=SHOWER_BEFORE)
            shower -= timedelta(days=(shower.weekday() - 5) % 7)
        stages.append(at(shower, 'shower'))
    if turn == 'bed_rest':
        stages.append(at(due - timedelta(days=span(seed, 'rest', (63, 77))), 'bed_rest'))
    if turn != 'early':
        stages.append(at(min(due, born) - timedelta(days=span(seed, 'any-day', (4, 7))), 'soon'))
    stages += moments(news, born, seed) + [at(born, 'born', early=turn == 'early')]
    details = {'due_on': due.isoformat(), 'turn': turn}
    if surrogate:
        details['surrogate'] = generators.pick(seed, 'surrogate', families.bank()['names']['she'])
    return stages, details


def moments(low: date, high: date, seed: str, kind: str = 'pregnancy') -> list[dict]:
    """A few small moments spread between two days, from the bank (`pregnancy` or `waiting`)."""
    gap = (high - low).days
    if gap < 30:
        return []
    count = min(MOMENTS, gap // 45)
    return [at(low + timedelta(days=int(gap * (index + 0.5) / (count + 0.5)) + span(seed, f'm{index}', (-6, 6))),
               f'moment:{index}', bank_key=kind) for index in range(count)]


def adopting(connection, companion: dict, row: dict, start: date, seed: str, found: dict) -> tuple[list, dict]:
    """The agency, a home study, the wait, the match and the day they come home; fostering trains first and places a
    child, who with family:fostered is adopted some months on."""
    agency = start + timedelta(days=span(seed, 'agency', (10, 30)))
    study = agency + timedelta(days=span(seed, 'study', (35, 70)))
    if row['route'] in FOSTERING:
        home = study + timedelta(days=span(seed, 'placement', (45, 150)))
        stages = [at(agency, 'training'), at(study, 'home_study'), at(home, 'home')]
        if found['fostered']['picked'] == 0:
            stages.append(at(home + timedelta(days=span(seed, 'adopted', (180, 365))), 'adopted'))
        return stages + moments(agency, home, seed, 'waiting'), {}
    matched = agency + timedelta(days=span(seed, 'wait', WAIT_DAYS[found['wait']['picked']]))
    matched = max(matched, study + timedelta(days=30))
    home = matched + timedelta(days=span(seed, 'home', (14, 42)))
    stages = [at(agency, 'agency'), at(study, 'home_study'), at(matched, 'match'), at(home, 'home')]
    return stages + moments(agency, matched, seed, 'waiting'), {}


def taking_in(connection, companion: dict, row: dict, start: date, seed: str, found: dict) -> tuple[list, dict]:
    """An older city: word comes of a child who needs a home, and some weeks on they come to live with the pair."""
    news = start + timedelta(days=span(seed, 'soon', (20, 120)))
    return [at(news, 'need'), at(news + timedelta(days=span(seed, 'home', (7, 45))), 'home')], {}


def child(connection, companion: dict, world, row: dict, seed: str, details: dict) -> dict:
    """The child: their pronouns, name (kept once given, or set by the user) and, for an older child, their age."""
    old = row['details']
    pronouns = old.get('pronouns') or ('she/her' if generators.unit(seed, 'sex') < 0.49 else 'he/him')
    name = old.get('name') or families.baby_name(companion['version']['definition'], world, seed, pronouns,
                                                 taken(connection, companion))
    years = old.get('years')
    if years is None:
        years = age_for(connection, companion, row, seed)
    return {'pronouns': pronouns, 'name': name, 'years': years, 'renamed': bool(old.get('renamed'))}


def age_for(connection, companion: dict, row: dict, seed: str) -> int:
    """How old the child is when they come home: a newborn when expecting or a foundling; by family:match when
    adopting or fostering; a ward or a relative's child from a baby to about twelve."""
    if row['route'] in PREGNANCY or row['route'] == 'foundling':
        return 0
    if row['route'] in TAKING_IN:
        return span(seed, 'years', (0, 12))
    found = consequences.recorded(connection, f"family:match:{row['id']}", 'family:match')
    return span(seed, 'years', MATCH_AGES[found['picked'] if found else 0])


def taken(connection, companion: dict) -> set[str]:
    """Names the child can't have: those families.baby_name keeps out, and the user's own."""
    persona = optional(connection, 'SELECT name FROM persona WHERE id=1') or {}
    return families.taken_names(connection, companion) | set((persona.get('name') or '').split()[:1])


# Each day ------------------------------------------------------------------------------------------------------------

def advance(connection, companion: dict, world, now) -> None:
    """Once a day (companion/life/agenda.py): a decided family is planned, a change of route before anything happened
    plans it again, the calendar, the nursery and the shower follow the stages, and a child whose day has come is
    home. Rules only, no model."""
    if not ACTIVE or not companion.get('active_timeline_id') or \
            companion['version']['definition'].get('relationship') != 'romance':
        return
    row = current(connection, companion['active_timeline_id'])
    if row is None or row['status'] == 'home':  # Another child comes the same way (companion/life/parenthood.py).
        begin(connection, companion, world, now)
        return
    if follow_step(connection, companion, row, now):
        return
    today = local_today(companion, now)
    if row['status'] == 'planned' and started(row, today):
        connection.execute("UPDATE family_journeys SET status='running', updated_at=? WHERE id=?", (stamp(now), row['id']))
    arrive(connection, companion, row, today, now)
    calendar(connection, companion, current(connection, companion['active_timeline_id']), today, now)


def started(row: dict, today: date) -> bool:
    return any(stage['on'] <= today.isoformat() for stage in row['stages'])


def follow_step(connection, companion: dict, row: dict, now) -> bool:
    """Before anything has happened, the family step taken back (or a break or breakup) calls it off, and another
    route picked on the Character page plans it again. Once under way it goes on."""
    from companion.life import parenthood
    if row['status'] != 'planned':
        return False
    route = parenthood.route_found(connection, companion)['route']
    if decided_on(connection, companion) and route == row['route'] and not steps.apart(connection, companion):
        return False
    connection.execute("UPDATE family_journeys SET status='called_off', updated_at=? WHERE id=?", (stamp(now), row['id']))
    return True


def arrive(connection, companion: dict, row: dict, today: date, now) -> None:
    """The day of the birth or homecoming: the child joins `circle_children` as the pair's own."""
    stage = next((item for item in row['stages'] if item['key'] in ('born', 'home')), None)
    if row['status'] == 'home' or stage is None or stage['on'] > today.isoformat():
        return
    details, timestamp = row['details'], stamp(now)
    arrived = date.fromisoformat(stage['on'])
    years = details.get('years') or 0
    born_on = arrived - timedelta(days=round(years * 365.25) + span(row['id'], 'birthday', (0, 300)) if years else 0)
    child_id = identifier()
    connection.execute(
        'INSERT INTO circle_children (id, timeline_id, parent_id, storyline_id, name, pronouns, title, born_on, status, '
        "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'ours', ?, 'born', ?, ?)",
        (child_id, row['timeline_id'], companion['id'], row['id'], details['name'], details['pronouns'],
         born_on.isoformat(), timestamp, timestamp))
    connection.execute("UPDATE family_journeys SET status='home', child_id=?, arrived_on=?, details=?, updated_at=? "
                       'WHERE id=?', (child_id, arrived.isoformat(), encode({**details, 'far': far_on(
                           connection, companion, row)}), timestamp, row['id']))


def days_off(connection, companion: dict, start: date, end: date) -> dict[str, str]:
    """{local date: 'Bed rest'} for companion/life/work.py `days_off`: the companion carrying the baby stays home
    from the day bed rest begins until the birth ('Home day' with the adult side of life on, which names no baby)."""
    row = current(connection, companion['active_timeline_id']) if ACTIVE and companion.get('active_timeline_id') \
        else None
    if not row or row['route'] != 'expecting_them' or row['status'] == 'home':
        return {}
    found = {stage['key']: date.fromisoformat(stage['on']) for stage in row['stages']}
    if 'bed_rest' not in found or 'born' not in found:
        return {}
    label, result, day = 'Home day' if quiet(connection) else 'Bed rest', {}, max(start, found['bed_rest'])
    while day <= min(end, found['born']):
        result[day.isoformat()] = label
        day += timedelta(days=1)
    return result


# The day the child comes, in the companion's day (companion/life/agenda.py) -----------------------------------------

# Where a birth is, by era group: a hospital in a modern or jazz-age city, at home with the midwife in an older one.
BIRTH_PLACE = {'modern': 'at the hospital', 'jazz': 'at the hospital', 'old': 'at home'}
# The waking blocks of the day: (together, apart) by route. Apart is long distance (Together or apart: the one who
# lives away isn't there) or on a break or broken up (steps.apart).
ARRIVAL_LABELS = {'expecting_them': ('Having the baby {at}, together', 'Having the baby {at}'),
                  'expecting_you': ('With you {at} for the birth', 'Waiting for news of the birth'),
                  'surrogacy': ('{At} for the birth, together', '{At} for the birth'),
                  'home': ('Bringing {name} home, together', 'Bringing {name} home')}
# What the day was, for Today and the companion's life (third person; "you" is the user): (together, long distance,
# on a break or broken up).
ARRIVAL_SUMMARIES = {
    'expecting_them': ('{companion} gave birth to {name} {at}, with you there.',
                       '{companion} gave birth to {name} {at} while you were away.',
                       '{companion} gave birth to {name} {at}.'),
    'expecting_you': ('{companion} was with you {at} while you gave birth to {name}.',
                      '{companion} waited for news while you gave birth to {name}, far away.',
                      '{companion} waited for news while you gave birth to {name}.'),
    'surrogacy': ('{companion} and you were {at} when {surrogate} gave birth to {name}.',
                  '{companion} was {at} when {surrogate} gave birth to {name}.',
                  '{companion} was {at} when {surrogate} gave birth to {name}.'),
    'home': ('{companion} brought {name} home with you.', '{companion} brought {name} home.',
             '{companion} brought {name} home.')}
ARRIVAL_LATER = {'birth': '{companion} spent the rest of the day with {name}.',
                 'home': '{companion} helped {name} settle in at home.'}


def arrival_days(connection, companion: dict, since: str) -> dict[str, dict]:
    """{local date: the day} for the day the child is born or comes home, from `since` on: the whole waking day goes
    to it (agenda.write_arrival_slot), with the user there unless they live apart (long distance) or are on a break or
    broken up (`split`). None with the adult
    side of life on: that day is an ordinary one there."""
    row = current(connection, companion['active_timeline_id']) if ACTIVE and companion.get('active_timeline_id') \
        else None
    if not row or quiet(connection):
        return {}
    stage = next((item for item in row['stages'] if item['key'] in ('born', 'home')), None)
    if stage is None or stage['on'] < since:
        return {}
    birth = row['route'] in PREGNANCY
    return {stage['on']: {'id': row['id'], 'key': row['route'] if birth else 'home', 'birth': birth,
                          'name': row['details'].get('name') or 'the baby',
                          'surrogate': row['details'].get('surrogate') or 'the surrogate',
                          'far': far_on(connection, companion, row), 'split': bool(steps.apart(connection, companion)),
                          'at': BIRTH_PLACE[era_group(connection, companion)]}}


def arrival_block(view: dict, day: dict) -> dict:
    """A waking block of that day: the birth or homecoming, with the user unless far."""
    together, apart = ARRIVAL_LABELS[day['key']]
    away = day['far'] or day.get('split')
    label = (apart if away else together).format(at=day['at'], At=day['at'][:1].upper() + day['at'][1:],
                                                       name=first_name(day['name']))
    return {**view, 'kind': 'leisure' if away else 'social', 'label': label, 'arrival': day['id'],
            'holiday': None, 'sick_day': False, 'with_user': not away}


def arrival_entry(day: dict, block: dict, definition: dict) -> dict:
    """What a waking slot of that day holds: the birth or homecoming, then (from the evening) the rest of the day."""
    from companion.life import composer
    words = {'companion': definition['name'].split()[0], 'name': first_name(day['name']), 'at': day['at'],
             'surrogate': day['surrogate']}
    if composer.day_part(block.get('start') or '09:00') in ('morning', 'afternoon'):
        summary = ARRIVAL_SUMMARIES[day['key']][1 if day['far'] else 2 if day.get('split') else 0].format(**words)
    else:
        summary = ARRIVAL_LATER['birth' if day['birth'] else 'home'].format(**words)
    return {'summary': summary, 'post': summary, 'mood': 'happy', 'activity': 'family-arrival', 'place': None,
            'with': None, 'weather': block.get('weather'), 'arrival': {'id': day['id']},
            'composer_version': 'arrival-1'}


def first_name(name: str) -> str:
    return name.split()[0] if name else name


def repin(connection, timeline_id: str, days: dict[str, dict]) -> int:
    """Upcoming companion entries whose arrival day is not the one now planned for their date (the day moved under
    Hidden values, or a journey was called off) are removed, so they are composed again."""
    removed = 0
    for row in many(connection, "SELECT id, local_date, json_extract(block, '$.arrival') AS arrival FROM life_agenda "
                    "WHERE timeline_id=? AND subject='companion' AND status='upcoming'", (timeline_id,)):
        wanted = (days.get(row['local_date']) or {}).get('id')
        if row['arrival'] != wanted and (row['arrival'] or wanted):
            connection.execute('DELETE FROM life_agenda WHERE id=?', (row['id'],))
            removed += 1
    return removed


# The calendar, the nursery and the shower ----------------------------------------------------------------------------------

def calendar(connection, companion: dict, row: dict, today: date, now) -> None:
    """Appointments, the home study and buying for the baby go on the Life admin calendar as they come within its
    three weeks; with the adult side on, what is still to come is taken off."""
    key = f"journey:{row['id']}:"
    if quiet(connection):
        connection.execute("UPDATE life_admin SET status='removed', updated_at=? WHERE timeline_id=? AND key LIKE ? AND "
                           "status='planned'", (stamp(now), row['timeline_id'], f'{key}%'))
        return
    for stage in row['stages']:
        day = date.fromisoformat(stage['on'])
        task = TASKS.get(stage['key'])
        if task and today <= day <= today + timedelta(days=admin.AHEAD):
            task(connection, companion, row, stage, now)
        if stage['key'] == 'nursery' and day <= today:
            make_room(connection, companion, row, today)


def appointment(connection, companion: dict, row: dict, stage: dict, now) -> None:
    words = ERA_WORDS[era_group(connection, companion)]
    title = words['halfway' if stage['key'] == 'halfway' else 'appointment']
    who = {'expecting_them': '', 'expecting_you': ' with the user',
           'surrogacy': f" with {row['details'].get('surrogate', 'the surrogate')}"}[row['route']]
    admin.add(connection, companion, key=f"journey:{row['id']}:{stage['key']}", source='admin', kind='family',
              title=title, done=f'went to the {title.lower()}{who}', day=date.fromisoformat(stage['on']), minutes=90,
              fixed=True, out=era_group(connection, companion) != 'old', now=now)


def home_study(connection, companion: dict, row: dict, stage: dict, now) -> None:
    admin.add(connection, companion, key=f"journey:{row['id']}:home_study", source='admin', kind='family',
              title='Home study visit', done='had the home study visit with the user', at='10:00',
              day=date.fromisoformat(stage['on']), minutes=150, fixed=True, out=False, now=now)


def buying(connection, companion: dict, row: dict, stage: dict, now) -> None:
    """The nursery, then baby things: from their money (a share of a month's pay, admin.priced)."""
    definition, key = companion['version']['definition'], f"journey:{row['id']}:{stage['key']}"
    things = ERA_WORDS[era_group(connection, companion)]['things']
    if stage['key'] == 'nursery':
        title, done = 'Set up the nursery', 'set up the nursery with the user'
    else:
        first, second = random.Random(key).sample(things, 2)
        title, done = 'Buy baby things', f'bought {first} and {second} for the baby'
    admin.add(connection, companion, key=key, source='admin', kind='family', title=title, done=done,
              day=date.fromisoformat(stage['on']), minutes=180, out=stage['key'] == 'things',
              cost=admin.priced(definition, '$$$', key), now=now)


def agency(connection, companion: dict, row: dict, stage: dict, now) -> None:
    """Signing on with the agency (or the fostering training), with its fees."""
    words = {'agency': ('Meet the adoption agency', 'signed on with the adoption agency with the user'),
             'training': ('Foster carer training', 'went to the foster carer training with the user')}
    if row['route'] == 'surrogacy':
        words['agency'] = ('Meet the surrogacy agency', 'signed on with the surrogacy agency with the user')
    title, done = words[stage['key']]
    key = f"journey:{row['id']}:{stage['key']}"
    admin.add(connection, companion, key=key, source='admin', kind='family', title=title, done=done,
              day=date.fromisoformat(stage['on']), minutes=120, fixed=True, out=True,
              cost=admin.priced(companion['version']['definition'], '$$$' if stage['key'] == 'agency' else '$', key),
              now=now)


TASKS = {'appointment': appointment, 'halfway': appointment, 'home_study': home_study, 'nursery': buying,
         'things': buying, 'agency': agency, 'training': agency}


def make_room(connection, companion: dict, row: dict, today: date) -> None:
    """A shared home too small for a family of three grows a size (companion/life/moving_in.py `grow`), once."""
    from companion.life import moving_in
    if row['details'].get('room'):
        return
    living = moving_in.living(connection, companion, today)
    if living:
        house = moving_in.members(connection, moving_in.household(living), today)
        if house:
            city = moving_in.city_of(connection, house[0])
            moving_in.grow(connection, house, city, moving_in.hood_named(city, house[0]['neighbourhood']), today,
                           len(house) + 2)
    connection.execute('UPDATE family_journeys SET details=? WHERE id=?',
                       (encode({**row['details'], 'room': today.isoformat()}), row['id']))


def showers(connection, companion: dict, today: date, people: dict, now) -> list[dict]:
    """The baby shower someone close throws for the pair (a big day in a modern city, companion/life/big_days.py):
    a sibling or an old friend living nearby hosts at their place. None with the adult side of life on."""
    from companion.life import big_days
    row = current(connection, companion['active_timeline_id']) if ACTIVE else None
    stage = next((item for item in (row or {}).get('stages', []) if item['key'] == 'shower'), None)
    if stage is None or row['status'] == 'home' or quiet(connection):
        return []
    hosts = [person for person in people.values() if circle.role_kind(person['role']) in ('sibling', *circle.OLD_FRIENDS)
             and (decode(person['details']) or {}).get('local', True) is not False]
    host = generators.pick(f"journey:{row['id']}", 'host', sorted(hosts, key=lambda person: person['id']))
    if host is None:
        return []
    return [big_days.candidate('own_shower', f"journey:{row['id']}:shower", host, date.fromisoformat(stage['on']),
                               host=host['name'], host_role=host['role'])]


def shower_gone(connection, row: dict) -> bool:
    """A planned shower is called off once the child has come (an early arrival) or the journey is not this one."""
    found = current(connection, row['timeline_id'])
    return found is None or row['source'] != f"journey:{found['id']}:shower" or found['status'] == 'home' or \
        not any(stage['key'] == 'shower' for stage in found['stages'])


# Hidden values ---------------------------------------------------------------------------------------------------------

def change(connection, companion: dict, consequence_id: str, now) -> None:
    """A journey outcome made to go another way: what is still to come is planned again with it."""
    row = current(connection, companion['active_timeline_id'])
    if row and consequence_id in (decode(row['consequences']) or {}).values() and row['status'] != 'home':
        plan(connection, companion, None, row, now)


# A hard turn on Today (Vanta, 2026-10-19: "Yes, with Undos") ----------------------------------------------------------

# What Today says, "you" for the user: bed rest by who carries, then an early arrival.
TURN_TITLES = {'expecting_them': '{companion} went on bed rest, to be safe, until the baby comes',
               'expecting_you': 'You went on bed rest, to be safe, until the baby comes',
               'surrogacy': '{surrogate}, your surrogate, went on bed rest, to be safe, until the baby comes',
               'early': '{name} was born {weeks} weeks early, and is doing well'}


def turn_shown(connection, companion: dict, now) -> dict | None:
    """The pregnancy's hard turn once it has come, for Today with an Undo, as Life's big turns are: bed rest until the
    birth, an early arrival for `ARRIVED_DAYS` after it. None with the adult side of life on (as the news)."""
    row = current(connection, companion['active_timeline_id']) if ACTIVE and companion.get('active_timeline_id') \
        else None
    if row is None or row['route'] not in PREGNANCY or quiet(connection):
        return None
    turn, today, done = row['details'].get('turn'), local_today(companion, now), None
    if turn == 'bed_rest' and row['status'] != 'home':
        done = reached(row, today).get('bed_rest')
    born = next((stage for stage in row['stages'] if stage['key'] == 'born'), None)
    if turn == 'early' and row['status'] == 'home' and born and born.get('early') and \
            (today - date.fromisoformat(born['on'])).days <= ARRIVED_DAYS:
        done = born
    if done is None:
        return None
    weeks = max(1, round((date.fromisoformat(row['due_on'] or done['on']) - date.fromisoformat(done['on'])).days / 7))
    title = TURN_TITLES['early' if turn == 'early' else row['route']].format(
        companion=first_name(companion['version']['definition']['name']), weeks=weeks,
        **{'surrogate': 'Your surrogate', **row['details']})
    return {'id': row['id'], 'kind': turn, 'on': done['on'], 'title': title,
            'consequence': (decode(row['consequences']) or {}).get('turn')}


def undo_turn(connection, companion: dict, journey_id: str, now) -> None:
    """Take the hard turn back, as a chapter's Undo does: the engine's pick becomes "no hard turn" (you picked it) and
    what is still to come is planned again. Bed rest ends; an early arrival goes back to being on the way, due as
    planned. What happened in the meantime stays."""
    shown = turn_shown(connection, companion, now)
    require(shown is not None and shown['id'] == journey_id, 'That has already been undone or is past changing.', 409)
    row = current(connection, companion['active_timeline_id'])
    if shown['consequence']:
        consequences.change(connection, shown['consequence'], TURNS.index('none'), stamp(now))
    stages = [stage for stage in row['stages'] if stage['key'] != shown['kind'] and
              not (shown['kind'] == 'early' and stage['key'] == 'born')]
    if shown['kind'] == 'early':
        connection.execute('DELETE FROM circle_children WHERE id=?', (row['child_id'],))
        connection.execute("UPDATE family_journeys SET status='running', child_id=NULL, arrived_on=NULL WHERE id=?",
                           (row['id'],))
    details = {key: value for key, value in row['details'].items() if key != 'far'} | {'turn': 'none'}
    connection.execute('UPDATE family_journeys SET stages=?, details=?, updated_at=? WHERE id=?',
                       (encode(stages), encode(details), stamp(now), row['id']))
    plan(connection, companion, None, current(connection, companion['active_timeline_id']), now)
    still_to_come(connection, companion, row['id'], now)


def still_to_come(connection, companion: dict, journey_id: str, now) -> None:
    """After an early arrival is undone the birth is still to come: on the due date, or tomorrow when that has passed."""
    row = current(connection, companion['active_timeline_id'])
    if row is None or row['id'] != journey_id or any(stage['key'] == 'born' for stage in row['stages']):
        return
    day = max(date.fromisoformat(row['due_on']), local_today(companion, now) + timedelta(days=1))
    stages = sorted(row['stages'] + [at(day, 'born', early=False)], key=lambda stage: (stage['on'], stage['key']))
    connection.execute('UPDATE family_journeys SET stages=?, updated_at=? WHERE id=?',
                       (encode(stages), stamp(now), journey_id))


def rename(connection, companion: dict, name: str, now) -> None:
    """The user names the child (on the Character page): the name stays from then on."""
    row = current(connection, companion['active_timeline_id'])
    require(row is not None, 'There is no child on the way.', 404)
    name = ' '.join(name.split())
    require(0 < len(name) <= 40, 'Give a name of up to 40 characters.', 422)
    connection.execute('UPDATE family_journeys SET details=?, updated_at=? WHERE id=?',
                       (encode({**row['details'], 'name': name, 'renamed': True}), stamp(now), row['id']))
    if row['child_id']:
        connection.execute('UPDATE circle_children SET name=?, updated_at=? WHERE id=?', (name, stamp(now),
                                                                                         row['child_id']))


def names(connection, timeline_id: str) -> set[str]:
    """The names of children on the way, for families.names (no picture is made of words naming them)."""
    return {decode(row['details']).get('name') for row in many(
        connection, "SELECT details FROM family_journeys WHERE timeline_id=? AND status!='called_off'", (timeline_id,))
            } - {None}


# What the chat and the screens see -------------------------------------------------------------------------------------------

def reached(row: dict, today: date) -> dict[str, dict]:
    return {stage['key']: stage for stage in row['stages'] if stage['on'] <= today.isoformat()}


def coming(row: dict, today: date) -> dict[str, dict]:
    return {stage['key']: stage for stage in row['stages'] if stage['on'] > today.isoformat()}


def long_date(day: str) -> str:
    found = date.fromisoformat(day)
    return f'{found:%A}, {found.day} {found:%B}'


def daughter(row: dict) -> str:
    return {'she/her': 'daughter', 'he/him': 'son'}.get(row['details'].get('pronouns'), 'child')


def girl(row: dict) -> str:
    return {'she/her': 'girl', 'he/him': 'boy'}.get(row['details'].get('pronouns'), 'baby')


def named(row: dict) -> str:
    """How they landed on the name (the companion suggested it), from the bank; a name the user gave is theirs."""
    if row['details'].get('renamed'):
        return 'the user picked it'
    line = generators.pick(f"journey:{row['id']}", 'named', suggested())['text']
    return line.format(name=row['details']['name']).rstrip('.')


def suggested() -> list[dict]:
    """The names_talk lines where the companion came up with the name, as the Character page says ("Dana suggested
    it"); not those where the user did, which would also decide what the user did."""
    return [line for line in bank()['names_talk'] if not line['text'].startswith('the user ')]


CARRIER = {'expecting_them': 'you are the one carrying the baby', 'expecting_you': 'the user is carrying the baby',
           'surrogacy': 'your surrogate, {surrogate}, is carrying the baby for you two'}
CARRIES = {'expecting_them': 'You have', 'expecting_you': 'The user has', 'surrogacy': 'Your surrogate has'}


def pregnancy_lines(row: dict, done: dict, today: date) -> list[str]:
    """While expecting: the news, how far along, the name once picked, a hard turn and "any day now"."""
    details = row['details']
    if 'news' not in done:
        return ['- You and the user are having a baby through a surrogate, {surrogate}. You have signed on with the '
                'agency; nobody is expecting yet.'.format(**details)] if 'agency' in done else []
    weeks = 5 + (today - date.fromisoformat(done['news']['on'])).days // 7
    due = date.fromisoformat(details['due_on'])
    lines = [f"- You and the user are expecting a baby, due in {due:%B} (about {weeks} weeks along): "
             f"{CARRIER[row['route']].format(**details)}."]
    if 'name' in done:
        lines.append(f"- The baby is a {girl(row)}, and you two have settled on a name: {details['name']} ("
                     f"{named(row)}).")
    if 'bed_rest' in done:
        lines.append(f"- {CARRIES[row['route']]} been on bed rest since {long_date(done['bed_rest']['on'])}, to be "
                     'safe. The baby is fine; it just means taking it easy at home until the baby comes.')
    if 'soon' in done:
        lines.append('- The baby could come any day now.')
    return lines


def waiting_lines(row: dict, done: dict, today: date) -> list[str]:
    """While adopting or fostering: where it stands, and the match once there is one."""
    details = row['details']
    if 'training' in done:
        study = ' The home study went well, and you are approved.' if 'home_study' in done else ''
        return [f"- You and the user are becoming foster parents: you started the training on "
                f"{long_date(done['training']['on'])}.{study} No child has been placed with you yet; nothing is "
                'known about who.']
    if 'match' in done:
        home = next(stage for stage in row['stages'] if stage['key'] == 'home')
        return [f"- You and the user are adopting: the agency matched you with {details['name']}, {age_words(row)}. "
                f"{details['name']} comes home to you on {long_date(home['on'])}."]
    study = ' The home study went well.' if 'home_study' in done else ''
    return [f"- You and the user are adopting: you signed on with an adoption agency on "
            f"{long_date(done['agency']['on'])}.{study} You are waiting to be matched with a child; nothing is known "
            'about who yet.'] if 'agency' in done else []


NEEDS = {'ward': 'a ward, a child with nobody left to raise them, is to come into your care',
         'foundling': 'a foundling baby, left with nobody to claim them, needs a home',
         'relative': "a relative's child needs a home, and the family has asked you two"}


def taking_in_lines(row: dict, done: dict, today: date) -> list[str]:
    if 'need' not in done:
        return []
    home = next(stage for stage in row['stages'] if stage['key'] == 'home')
    return [f"- Word came on {long_date(done['need']['on'])}: {NEEDS[row['route']]}. You and the user are taking "
            f"them in: {row['details']['name']}, {age_words(row)}, comes to live with you on {long_date(home['on'])}."]


def age_words(row: dict) -> str:
    years = row['details'].get('years') or 0
    return f'a baby {girl(row)}' if years == 0 else f"a {girl(row)} of {years}"


def arrived_lines(row: dict, today: date) -> list[str]:
    """Born or home: for a while after, how the day went. Who the child is, from then on, is Our child's
    (companion/life/our_child.py, the 'kids' section)."""
    arrived = date.fromisoformat(row['arrived_on'])
    details, gap = row['details'], (today - arrived).days
    lines = []
    if gap <= ARRIVED_DAYS:
        when = 'today' if gap == 0 else 'yesterday' if gap == 1 else f'on {long_date(row["arrived_on"])}'
        lines.append(day_line(row, when) if row['route'] in PREGNANCY else
                     f"- {details['name']} came home to you and the user {when}.")
    return lines


BIRTH_WHERE = {'expecting_them': 'You gave birth {at}, with the user there with you.',
               'expecting_you': 'The user gave birth {at}, and you were there.',
               'surrogacy': 'Your surrogate, {surrogate}, gave birth {at}, and you and the user were there.'}
# Long distance on the day (companion/life/long_distance.py): the one who lives away wasn't there.
BIRTH_FAR = {'expecting_them': "You gave birth {at}. The user lives away and couldn't be there; you told them the news.",
             'expecting_you': "The user gave birth {at}, where they live. You live away and couldn't be there.",
             'surrogacy': "Your surrogate, {surrogate}, gave birth {at}, and you were there. The user lives away and "
                          "couldn't be."}


def day_line(row: dict, when: str) -> str:
    early = ', a few weeks early and doing well' if any(item.get('early') for item in row['stages']) else ''
    where = (BIRTH_FAR if row['details'].get('far') else BIRTH_WHERE)[row['route']]
    return (f"- Your baby was born {when}: a {girl(row)}, {row['details']['name']}{early}. "
            + where.format(**{'surrogate': 'your surrogate', **row['details']}))


def context_lines(connection, companion: dict, now) -> list[tuple[str, str]]:
    """(identity, line) for the 'steps' section, through parenthood.context_lines (which keeps all of it out with the
    adult side of life on)."""
    row = current(connection, companion['active_timeline_id']) if ACTIVE else None
    if row is None or row['status'] == 'planned':
        return []
    today, done = local_today(companion, now), reached(row, local_today(companion, now))
    if row['status'] == 'home':
        row = {**row, 'details': {**row['details'], 'at': birth_place(connection, companion),
                                  'far': far_on(connection, companion, row)}}
        lines = arrived_lines(row, today)
    elif row['route'] in PREGNANCY:
        lines = pregnancy_lines(row, done, today)
    elif row['route'] in TAKING_IN:
        lines = taking_in_lines(row, done, today)
    else:
        lines = waiting_lines(row, done, today)
    lines += told_line(connection, companion, row, done) + moment_line(connection, companion, row, done, today)
    return [(f"journey:{row['id']}:{index}:{line}", line) for index, line in enumerate(lines)]


def birth_place(connection, companion: dict) -> str:
    return ERA_WORDS[era_group(connection, companion)]['birth']


def far_on(connection, companion: dict, row: dict) -> bool:
    """Whether they lived apart, long distance, when the child came: kept from the day (`arrive`), else as now."""
    from companion.life import long_distance
    kept = row['details'].get('far')
    return bool(long_distance.far(connection, companion)) if kept is None else kept


def told_line(connection, companion: dict, row: dict, done: dict) -> list[str]:
    """How their people took the news, for the few weeks after they told them."""
    stage = done.get('told')
    if stage is None or row['status'] == 'home':
        return []
    reactions = reactions_of(connection, companion, row)
    return [f"- You two told your people about the baby on {long_date(stage['on'])}. {' '.join(reactions)}"] \
        if reactions else []


def reactions_of(connection, companion: dict, row: dict) -> list[str]:
    """How a few of their closest took it: family first, then old friends; from the bank, seeded."""
    order = ('parent', 'sibling', *circle.OLD_FRIENDS)
    people = sorted((person for person in circle.people(connection, row['timeline_id'])
                     if circle.role_kind(person['role']) in order),
                    key=lambda person: (order.index(circle.role_kind(person['role'])), person['id']))[:TOLD_PEOPLE]
    lines = fitting(bank()['reactions'], connection, companion)
    result = []
    for index, person in enumerate(people):
        details = decode(person['details']) or {}
        role = circle.said(circle.relation(circle.role_kind(person['role']), details.get('pronouns') or ''),
                           companion['version']['definition'])
        line = generators.pick(f"journey:{row['id']}:{person['id']}", f'reaction-{index}', lines)['text']
        sentence = reaction(line, f"your {role} {person['name'].split()[0]}", details.get('pronouns'))
        result.append(sentence[:1].upper() + sentence[1:])
    return result


def reaction(line: str, who: str, pronouns_: str | None) -> str:
    """A reactions bank line said of `who` with their own pronouns ("{they} forgot" for a dad is "he forgot"; A/B:
    findings/ab-r2-expecting.md, decide-screens); pronouns not known read "they"."""
    forms = pronouns.person(pronouns_)
    return line.format(who=who, **{key.replace("'", ''): value for key, value in forms.items()})


def moment_line(connection, companion: dict, row: dict, done: dict, today: date) -> list[str]:
    """The latest small moment while they wait, for three weeks."""
    latest = max((stage for key, stage in done.items() if key.startswith('moment:')), key=lambda stage: stage['on'],
                 default=None)
    if latest is None or row['status'] == 'home' or (today - date.fromisoformat(latest['on'])).days > RECENT_DAYS:
        return []
    line = moment_text(row, int(latest['key'].split(':')[1]), fitting(bank()[latest['bank_key']], connection, companion))
    return [f"- Lately ({long_date(latest['on'])}): {line}"]


def moment_text(row: dict, index: int, lines: list[dict]) -> str:
    """The bank line for the journey's moment `index`, never one an earlier moment of it had (seeded, in order)."""
    used: list[str] = []
    for each in range(index + 1):
        pool = [line for line in lines if line['text'] not in used] or lines
        used.append(generators.pick(f"journey:{row['id']}", f'moment:{each}', pool)['text'])
    return used[-1]


# First texts (companion/life/openers.py) ----------------------------------------------------------------------------------

NEWS = {
    'news': 'You and the user just found out you are expecting a baby, due in {due}: {carrier}. Text the user how you '
            'feel about it, in your own words.',
    'match': 'The adoption agency just called: you and the user have been matched with {name}, {age}, who comes home '
             'on {home}. Text the user about it, in your own words.',
    'home_fostering': '{name}, {age}, has just been placed with you and the user as your foster child, {when}. Text '
                      'the user about it, in your own words.',
    'need': 'Word just came that {need}. You and the user are taking them in: {name}, {age}, comes to live with you '
            'on {home}. Tell the user, in your own words.',
    'born_far': 'Your baby was born {when}: a {girl}, {name}. The user is away. Text them the news, in your own words.',
    # The day the name comes up, when the companion suggested it (A/B: findings/ab-r2-expecting.md, decide-screens).
    'name': "You've been thinking about names for the baby, and one keeps coming back to you: {name}. Suggest it to "
            'the user in your own words, and leave them room to say no.',
}


def news_due(connection, companion: dict, now) -> list:
    """The news as a first text: finding out, the match, a placement, word of a child who needs a home, or the birth
    when the user is away; the latest since yesterday or the user's last visit (love_life.news_since), so news on a
    day the user was away still comes. Never with the adult side of life on."""
    from companion.life import long_distance, love_life
    from companion.life.openers import Trigger
    row = current(connection, companion['active_timeline_id']) if ACTIVE and FIRST_TEXTS else None
    if row is None or row['status'] == 'planned' or quiet(connection):
        return []
    day = local_today(companion, now)
    today, since = day.isoformat(), love_life.news_since(connection, companion, now, day).isoformat()
    stage = max((item for item in row['stages'] if since <= item['on'] <= today and news_key(row, item['key'])),
                key=lambda item: item['on'], default=None)
    key = stage and stage['key']
    if key == 'home' and row['route'] in FOSTERING:
        key = 'home_fostering'
    elif key == 'born':
        key = 'born_far' if long_distance.far(connection, companion) else None
    if key not in NEWS:
        return []
    home = next((item['on'] for item in row['stages'] if item['key'] == 'home'), today)
    details = row['details']
    when = 'today' if stage['on'] == today else f"on {long_date(stage['on'])}"
    reason = NEWS[key].format(due=f"{date.fromisoformat(details.get('due_on') or today):%B}", when=when,
                              carrier=CARRIER.get(row['route'], '').format(**details), name=details['name'],
                              age=age_words(row), home=long_date(home), need=NEEDS.get(row['route'], ''),
                              girl=girl(row))
    return [Trigger(f"journey:{row['id']}:{key}", 'storyline', reason)]


def news_key(row: dict, key: str) -> bool:
    """Whether a stage is news told in a first text; the name only while it is the one the companion suggested
    (not once the user named the child)."""
    if key == 'name':
        return not row['details'].get('renamed')
    return key in NEWS or key == 'born' or key == 'home' and row['route'] in FOSTERING


def news_items(connection, companion: dict, since: str, today: str) -> list[dict]:
    """For News travels (companion/news.py): the news they are expecting, the match and the arrival. None with the
    adult side of life on."""
    row = current(connection, companion['active_timeline_id']) if ACTIVE else None
    if row is None or quiet(connection):
        return []
    name, other = companion['version']['definition']['name'].split()[0], 'the user'
    words = {'news': f'{name} and {other} are expecting a baby', 'match': f'{name} and {other} are adopting a child',
             'need': f'{name} and {other} are taking in a child', 'born': f'{name} and {other} had their baby',
             'home': f'{name} and {other} welcomed a child home'}
    return [{'source': f"journey:{row['id']}:{stage['key']}", 'text': words[stage['key']], 'happened_on': stage['on']}
            for stage in row['stages'] if stage['key'] in words and since <= stage['on'] <= today
            and not (stage['key'] == 'home' and row['route'] in PREGNANCY)]


# The Character page -------------------------------------------------------------------------------------------------

LABELS = {'agency': 'Signed on with the agency', 'training': 'Foster carer training', 'news': 'Found out',
          'appointment': 'First appointment', 'told': 'Told everyone', 'halfway': 'Halfway there',
          'nursery': 'Set up the nursery', 'things': 'Bought baby things', 'name': 'Picked a name',
          'shower': 'Baby shower', 'bed_rest': 'Bed rest, to be safe', 'soon': 'Any day now', 'born': 'Born',
          'home_study': 'Home study visit', 'match': 'Matched', 'home': 'Came home', 'adopted': 'Adopted',
          'need': 'Word of a child who needs a home'}


def panel(connection, companion: dict, now, show_odds: bool) -> dict | None:
    """The journey for the Family panel: where it stands, the stages (those to come only once the news is in, so the
    panel never gives away what the engine has planned), the child's name and the odds."""
    row = current(connection, companion['active_timeline_id'])
    if row is None:
        return None
    today = local_today(companion, now)
    done = reached(row, today)
    shown = sorted((shown_stage(stage, done, row) for stage in row['stages'] if listed(stage, done, row)),
                   key=lambda item: (item['date'] is None, item['date'] or ''))
    known = row['status'] == 'home' or any(key in done for key in ('name', 'match', 'need', 'born', 'home')) or \
        row['route'] in FOSTERING and 'home' in done
    return {'route': row['route'], 'status': row['status'], 'due_on': row['due_on'] if 'news' in done else None,
            'arrived_on': row['arrived_on'], 'name': row['details'].get('name') if known else None,
            'renamed': bool(row['details'].get('renamed')), 'stages': shown,
            'consequences': list((decode(row['consequences']) or {}).values()) if show_odds else [],
            # Which of the engine's choices each is (soon, turn, wait, match, fostered), so the panel can name them.
            'outcomes': [{'key': key, 'id': value} for key, value in (decode(row['consequences']) or {}).items()]
            if show_odds else []}


def listed(stage: dict, done: dict, row: dict) -> bool:
    """A stage the panel lists: those reached, and once it is under way those to come that anyone would know of. Never
    a hard turn, "any day now", a placement or an adoption before its day (the panel doesn't give away what the engine
    planned), nor the small moments. The match to come shows, without its day."""
    key = stage['key']
    if key.startswith('moment:'):
        return False
    if key in done:
        return True
    if row['status'] == 'planned' or key in ('bed_rest', 'soon', 'adopted'):
        return False
    return key != 'home' or 'match' in done or 'need' in done


def shown_stage(stage: dict, done: dict, row: dict) -> dict:
    """The birth to come shows as the due date, not the day the engine picked; the match to come has no date."""
    if stage['key'] == 'match' and 'match' not in done:
        return {'key': 'match', 'label': LABELS['match'], 'date': None, 'done': False}
    if stage['key'] == 'born' and stage['key'] not in done and row['due_on']:
        return {'key': 'due', 'label': 'Due', 'date': row['due_on'], 'done': False}
    return {'key': stage['key'], 'label': LABELS[stage['key']], 'date': stage['on'], 'done': stage['key'] in done}


# Branches -------------------------------------------------------------------------------------------------------------

def copy(connection, parent_id: str, new_id: str, cutoff_date: str) -> None:
    """A journey begun by the fork carries over with its plan (the days were picked the day it began, so the due date
    and the birth stay as they were; what is still to come on the copy comes on the copy) and its engine outcomes; a
    child home by then comes too."""
    for row in many(connection, "SELECT * FROM family_journeys WHERE timeline_id=? AND started_on<=? AND "
                    "status!='called_off'", (parent_id, cutoff_date)):
        found = view(row)
        reached_by = any(stage['on'] <= cutoff_date for stage in found['stages'])
        home = row['status'] == 'home' and (row['arrived_on'] or '') <= cutoff_date
        journey_id, child_id = identifier(), identifier() if home else None
        connection.execute(
            'INSERT INTO family_journeys (id, timeline_id, companion_id, route, status, decided_on, started_on, '
            'due_on, arrived_on, child_id, stages, details, consequences, created_at, updated_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (journey_id, new_id, row['companion_id'], row['route'], 'home' if home else 'running' if reached_by else
             'planned', row['decided_on'], row['started_on'], row['due_on'], row['arrived_on'] if home else None,
             child_id, row['stages'], row['details'], encode(copy_outcomes(connection, found, new_id, journey_id)),
             row['created_at'], row['updated_at']))
        if home:
            kid = optional(connection, 'SELECT * FROM circle_children WHERE id=?', (row['child_id'],))
            if kid:
                connection.execute(
                    'INSERT INTO circle_children (id, timeline_id, parent_id, storyline_id, name, pronouns, title, '
                    "born_on, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'ours', ?, ?, ?, ?)",
                    (child_id, new_id, kid['parent_id'], journey_id, kid['name'], kid['pronouns'], kid['born_on'],
                     kid['status'], kid['created_at'], kid['updated_at']))


def copy_outcomes(connection, row: dict, new_id: str, journey_id: str) -> dict:
    """The journey's engine outcomes on the copy (consequences.copy), so Hidden values there change the copy's own."""
    result = {}
    for key, consequence_id in (decode(row['consequences']) or {}).items():
        if consequence_id and optional(connection, 'SELECT id FROM consequences WHERE id=?', (consequence_id,)):
            result[key] = consequences.copy(connection, consequence_id, new_id, f'family:{key}:{journey_id}')
    return result
