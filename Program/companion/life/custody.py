"""When families change (Hit List #73, v0.15 Room to Grow): a breakup or a move with children shared, and the parents
the world spares while their baby is small.

The app decides, the user overrides ("the world exists outside of User", Vanta 2026-10-08). Rules and seeds only, no
model:

- A breakup with children of the pair (companion/life/our_child.py) means shared custody. Where the children live is
  the engine's `family:custody`, read from who was home with them, who carried them, the companion's work and whether
  the two of them now live in different cities: mostly with the companion (every other weekend with the user), half
  and half (a week each, turn and turn about), or mostly with the user (every other weekend with the companion). The
  weeks alternate the way a rota does (companion/life/shifts.py `monday_of`), from the week it ended. The user can
  set it on the Character page, or change how it went under Hidden values. The children go on in words in both
  lives: on Today and the Character page, and in the companion's texts, where they are and whose week it is. Getting
  back together ends it. Never on an easy life, which has no breakups (companion/life/breakups.py).
- Long distance with a child (companion/life/long_distance.py): the children stay with the parent they live with
  (the companion, unless custody gave them to the user), and the weekend visits are when the other one sees them.
- A companion and their own partner (companion/life/own_family.py) who split with a child: the ex stays in their
  circle as the child's other parent, and where the child lives is the engine's kids:custody, as for kids they had
  before (companion/life/kids.py).
- Loss (companion/life/loss.py): children are never the one who passes away, nor the pair's grown child; a parent
  with a baby under one, or one on the way, is spared until the baby turns one.

Children keep v0.14's limits everywhere: words only, and with the adult side of life on a reply carries the family
lines or the adult side's, never both (our_child.quiet).
"""
from datetime import date, timedelta

from companion import consequences
from companion.clock import parse, stamp
from companion.database import decode, encode, optional
from companion.errors import require
from companion.life import families, shifts, steps
from companion.life.steps import FAMILY

CHOICE = 'family:custody'
PATTERNS = ('with_them', 'shared', 'with_you')
LABELS = {'with_them': 'Mostly with {name}', 'shared': 'Half and half', 'with_you': 'Mostly with you'}
DETAILS = {'with_them': "with {name}, every other weekend with you", 'shared': 'a week with {name}, a week with you',
           'with_you': 'with you, every other weekend with {name}'}
FAR_DETAILS = {'with_them': 'with {name}; you see {them} on your visits', 'with_you': 'with you; {name} sees {them} on '
               'your visits'}
BABY_DAYS = 365
OWN_CHOICE = 'kids:custody'
OWN_PATTERNS = ('with_them', 'shared', 'weekends')
SPLIT = 'split'


def first(name: str) -> str:
    return name.split()[0] if name.split() else name


def names_of(kids: list[dict]) -> str:
    return steps.names_text([first(child['name']) for child in kids])


def verb(kids: list[dict], one: str, more: str) -> str:
    return one if len(kids) == 1 else more


# Where things stand ---------------------------------------------------------------------------------------------------

def ended(connection, companion: dict) -> dict | None:
    """The breakup that ended things between the user and this companion, while it stands; None together."""
    from companion.life import breakups
    row, found = breakups.current(connection, companion)
    return row if found == 'ended' else None


def far(connection, companion: dict):
    from companion.life import long_distance
    return long_distance.far(connection, companion)


def facts(connection, companion: dict) -> dict:
    """What the engine reads: who was home with them, who carried the first, whether the companion works, their
    city's era and whether the two of them live in different cities."""
    from companion.life import our_child
    found = our_child.care_facts(connection, companion, None)
    care = our_child.care_found(connection, companion)['care']
    return {'care': care, 'carried': found['carried'], 'carried_you': found['carried_you'], 'works': found['works'],
            'old': found['old'], 'far': int(far(connection, companion) is not None)}


def subject(companion: dict, row: dict) -> str:
    return f"{CHOICE}:{companion['active_timeline_id']}:{row['id']}"


def outcome_of(connection, companion: dict, row: dict, now=None) -> dict:
    """The engine's pick, recorded once (with `now`, in the day's pass); a read works it out the same way."""
    if now is not None:
        return steps.decide(connection, companion, CHOICE, subject(companion, row), facts(connection, companion),
                            FAMILY.topic, now)
    found = consequences.recorded(connection, subject(companion, row), CHOICE)
    if found:
        return found
    options = consequences.odds(CHOICE, facts(connection, companion), steps.names(companion, FAMILY.topic))
    return {'id': None, 'picked': consequences.roll(f"{companion['active_timeline_id']}:{subject(companion, row)}",
                                                    options)}


def found(connection, companion: dict, now=None) -> dict | None:
    """{pattern, how ('set' or 'seeded'), consequence_id, since, far, split} while the children's parents live apart:
    split up, or in different cities. None while they are together under one roof."""
    from companion.life import our_child
    timeline_id = companion.get('active_timeline_id')
    if not our_child.children(connection, timeline_id):
        return None
    row, between = ended(connection, companion), far(connection, companion)
    if row is None:
        return {'pattern': 'with_them', 'how': 'seeded', 'consequence_id': None, 'since': None, 'far': between,
                'split': False} if between else None
    set_to = our_child.family_row(connection, timeline_id).get('custody')
    outcome = None if set_to else outcome_of(connection, companion, row, now)
    pattern = set_to or PATTERNS[outcome['picked']]
    if between and pattern == 'shared':
        pattern = 'with_them'  # A week each can't cross cities: they stay where they live, with the companion.
    since = shifts.monday_of(steps.local_today(companion, parse(row['ended_at'])))
    return {'pattern': pattern, 'how': 'set' if set_to else 'seeded', 'consequence_id': outcome and outcome['id'],
            'since': since, 'far': between, 'split': True}


def with_them(state: dict | None, day: date) -> bool:
    """Whether the children are with the companion on this day: always while together; across cities with the
    parent they live with; else by the weekends and weeks of the pattern."""
    if state is None:
        return True
    if state['far']:
        return state['pattern'] != 'with_you'
    odd = ((shifts.monday_of(day) - state['since']).days // 7) % 2 == 1
    weekend = day.weekday() >= 5
    if state['pattern'] == 'with_them':
        return not (weekend and odd)
    if state['pattern'] == 'shared':
        return not odd
    return weekend and not odd


def here(connection, companion: dict, day: date) -> bool:
    return with_them(found(connection, companion), day)


def advance(connection, companion: dict, now) -> None:
    """Once a day (our_child.advance): where the children live is decided once a breakup ends things."""
    found(connection, companion, now)


# The chat context -----------------------------------------------------------------------------------------------------

def context_lines(connection, companion: dict, kids: list[dict], today: date, now) -> list[tuple[str, str]]:
    """For the 'kids' section: where the children live since the breakup or the move, and a weekend visit with them."""
    state = found(connection, companion)
    if state is None or not kids:
        return []
    who, them = names_of(kids), verb(kids, families.fill_child('{them}', kids[0]), 'them')
    since = 'Since you and the user split up, ' if state['split'] else ''
    if state['far']:
        city = (state['far'].your_city or {}).get('name') or 'another city'
        line = (f"{who} {verb(kids, 'lives', 'live')} with you; the user lives in {city} and sees {them} when you visit "
                'each other.' if state['pattern'] == 'with_them' else
                f"{who} {verb(kids, 'lives', 'live')} with the user in {city}; you see {them} when you visit each other.")
    else:
        line = {'with_them': f"{who} {verb(kids, 'lives', 'live')} with you and {verb(kids, 'spends', 'spend')} every "
                             'other weekend with the user.',
                'shared': f"{who} {verb(kids, 'spends', 'spend')} a week with you, then a week with the user, turn and "
                          'turn about.',
                'with_you': f"{who} {verb(kids, 'lives', 'live')} with the user and {verb(kids, 'spends', 'spend')} "
                            'every other weekend with you.'}[state['pattern']]
    text = f'- {since}{line}'
    return [(f"ours:custody:{state['pattern']}:{bool(state['far'])}:{state['split']}", text)] + \
        visit_line(connection, companion, kids, state, today, now)


def visit_line(connection, companion: dict, kids: list[dict], state: dict, today: date,
               now) -> list[tuple[str, str]]:
    """Across cities, the next weekend visit is when the other parent sees them."""
    from companion.life import long_distance
    if not state['far']:
        return []
    for trip in long_distance.visits(connection, companion, today, now):
        if trip['status'] == 'planned' and trip['end_date'] >= today.isoformat():
            span = long_distance.span(trip)
            return [(f"ours:visit:{trip['id']}", f"- {names_of(kids)} will be with you both for the weekend visit "
                                                 f"({span}).")]
    return []


def today_line(connection, companion: dict, kids: list[dict], today: date) -> list[tuple[str, str]]:
    """For 'circle_now': whose day it is, when they split their time between the two homes in one city."""
    state = found(connection, companion)
    if state is None or state['far'] or not kids:
        return []
    is_here = with_them(state, today)
    where = 'with you' if is_here else 'with the user'
    return [(f'ours:today:{is_here}', f"- Today {names_of(kids)} {verb(kids, 'is', 'are')} {where}.")]


# The screens ----------------------------------------------------------------------------------------------------------

def view(connection, companion: dict, show_odds: bool) -> dict | None:
    """For the Family panel: where the children live while their parents live apart, the picks and who decided."""
    from companion.life import our_child
    state = found(connection, companion)
    if state is None:
        return None
    name = first(companion['version']['definition']['name'])
    kids = our_child.children(connection, companion['active_timeline_id'])
    them = families.fill_child('{them}', kids[0]) if len(kids) == 1 else 'them'
    keys = [key for key in PATTERNS if not (state['far'] and key == 'shared')]
    details = FAR_DETAILS if state['far'] else DETAILS
    return {'pattern': state['pattern'], 'how': state['how'], 'split': state['split'], 'far': bool(state['far']),
            'city': (state['far'].your_city or {}).get('name') if state['far'] else None,
            'detail': details[state['pattern']].format(name=name, them=them),
            'patterns': [{'key': key, 'label': LABELS[key].format(name=name)} for key in keys] if state['split'] else [],
            'consequence_id': state['consequence_id'] if show_odds else None}


def where_today(connection, companion: dict, today: date) -> str | None:
    """For Today: 'With Sam today' or 'With you today' while they split their time; None otherwise."""
    state = found(connection, companion)
    if state is None:
        return None
    if state['far']:
        return f"Lives with {first(companion['version']['definition']['name'])}" \
            if state['pattern'] == 'with_them' else 'Lives with you'
    return f"With {first(companion['version']['definition']['name'])} today" if with_them(state, today) else \
        'With you today'


def update(connection, companion: dict, custody: str, now) -> None:
    """The user sets where the children live after the breakup ('auto' gives it back to the app)."""
    from companion.life import our_child
    require(ended(connection, companion) is not None, 'You two are not apart.', 409)
    require(custody in ('auto', *PATTERNS), 'Pick where they live.', 422)
    timeline_id = companion['active_timeline_id']
    our_child.ensure_row(connection, timeline_id, now)
    connection.execute('UPDATE our_family SET custody=?, updated_at=? WHERE timeline_id=?',
                       (None if custody == 'auto' else custody, stamp(now), timeline_id))


# A companion and their own partner -----------------------------------------------------------------------------------

def shares_child(connection, person_id: str, day: date) -> bool:
    """Whether a love-life partner has a child under 18 with the companion (own_family.py), born or on the way."""
    rows = [row for row in families.children_of(connection, person_id) if row.get('whose') == 'companion']
    return any(row['status'] == 'expected' or families.age_of(row, day) < 18 for row in rows)


def keep_coparent(connection, person_id: str, day: date) -> bool:
    """A partner the companion split up with who shares a child stays in their circle as the child's other parent.
    Returns whether they stay."""
    person = optional(connection, 'SELECT * FROM circle_people WHERE id=?', (person_id,))
    if person is None or not shares_child(connection, person_id, day):
        return False
    details = decode(person['details']) or {}
    connection.execute("UPDATE circle_people SET role='ex', status='active', details=?, revision=revision+1 WHERE id=?",
                       (encode({**details, 'co_parent': True}), person_id))
    return True


def own_outcome(connection, companion: dict, person: dict, now=None) -> dict:
    """The engine's kids:custody for a child the companion has with an ex of theirs."""
    from companion.life import kids
    subject_ = f"{OWN_CHOICE}:own:{person['id']}"
    away = int(not (decode(person['details']) or {}).get('local', True))
    if now is not None:
        return kids.decide_choice(connection, companion, OWN_CHOICE, subject_, {'away': away},
                                  {'other': first(person['name'])}, now)
    recorded = consequences.recorded(connection, subject_, OWN_CHOICE)
    if recorded:
        return recorded
    options = consequences.odds(OWN_CHOICE, {'away': away}, {'name': first(companion['version']['definition']['name']),
                                                             'other': first(person['name'])})
    return {'id': None, 'picked': consequences.roll(f"{companion['active_timeline_id']}:{subject_}", options)}


def own_line(connection, companion: dict, child: dict, now=None) -> tuple[str, str] | None:
    """'- Ivy lives with you and spends every other weekend with Sam.' for a child whose parents split up."""
    person = optional(connection, "SELECT * FROM circle_people WHERE id=? AND status='active' AND role='ex'",
                      (child['parent_id'],))
    if person is None or not (decode(person['details']) or {}).get('co_parent'):
        return None
    pattern = OWN_PATTERNS[own_outcome(connection, companion, person, now)['picked']]
    other, name = first(person['name']), first(child['name'])
    text = {'with_them': f'{name} lives with you and spends every other weekend with {other}.',
            'shared': f'{name} spends a week with you, then a week with {other}, turn and turn about.',
            'weekends': f'{name} lives with {other} and spends every other weekend with you.'}[pattern]
    return f"custody:{child['id']}:{pattern}", f'- Since you and {other} split up, {text}'


def own_advance(connection, companion: dict, now) -> None:
    """Once a day: where a child of a split-up companion and their ex lives is decided once."""
    from companion.life import own_family
    for child in own_family.own_children(connection, companion['active_timeline_id']):
        if child['status'] == 'born':
            own_line(connection, companion, child, now)


# Loss ---------------------------------------------------------------------------------------------------------------

def spared(connection, person: dict, day: date) -> bool:
    """Never the pair's grown child, and never a parent while their baby is under one or on the way: their own
    (circle_children under them) or, for the kids' other parent, the companion's kids with them (kids.py)."""
    details = decode(person['details']) or {}
    if details.get('our_child'):
        return True
    young = (day - timedelta(days=BABY_DAYS)).isoformat()
    if optional(connection, "SELECT id FROM circle_children WHERE parent_id=? AND (status='expected' OR "
                "(status='born' AND born_on>?)) LIMIT 1", (person['id'], young)):
        return True
    return bool(optional(connection, "SELECT c.id FROM companion_kids k JOIN circle_children c ON "
                         "c.storyline_id='kids:' || k.timeline_id WHERE k.other_id=? AND c.status='born' AND "
                         'c.born_on>? LIMIT 1', (person['id'], young)))
