"""One love life of record for each person in the companion's circle.

Before v1.3.4 a circle person's love life was spread over places that never talked to each other: the seeded partner
among their own people (companion/life/network.py), `married` on their row, a tie to another circle row
(companion/life/circle.py), and whatever a storyline said. `state` reads them in one order, first match wins:

1. `details.partner`, written by a life event or by the user;
2. the companion's own partner (companion/life/love_life.py): their partner is the companion;
3. a couple tie with another active circle person (married, partners, separated, divorced);
4. `married` on their row;
5. the seeded partner among their own people: seeing someone;
6. otherwise single.

Rules only, no model.
"""
from datetime import date, timedelta

from companion.life import circle, network

STATES = ('single', 'seeing', 'engaged', 'married', 'separated', 'divorced', 'widowed')
# Someone the companion is seeing, by their circle role (love_life.ROLES), and the state it means.
PARTNER_ROLES = {'girlfriend': 'seeing', 'boyfriend': 'seeing', 'partner': 'seeing', 'sweetheart': 'seeing',
                 'fiancée': 'engaged', 'fiancé': 'engaged', 'wife': 'married', 'husband': 'married',
                 'spouse': 'married'}
TIES = {'married': 'married', 'partners': 'seeing', 'separated': 'separated', 'divorced': 'divorced'}


def found(state: str, partner: dict | None, decided: str, exes=(), since: str | None = None) -> dict:
    return {'state': state, 'partner': partner, 'exes': list(exes), 'since': since, 'decided': decided}


def key_of(row: dict) -> str:
    return row.get('seed') or row['id']


def state(connection, row: dict, people: list[dict] | None = None) -> dict:
    """{state, partner: {key, name?, circle_id?} or None, exes, since, decided: event|user|circle|seed}.
    `people` are the circle's active rows, for a couple inside the circle; `connection` may be None."""
    details = circle.details_of(row)
    recorded = details.get('partner')
    if isinstance(recorded, dict) and recorded.get('state') in STATES:
        partner = {key: recorded[key] for key in ('key', 'name', 'full', 'pronouns', 'circle_id')
                   if recorded.get(key)} or None
        return found(recorded['state'], partner, recorded.get('source') or 'event', recorded.get('exes') or (),
                     recorded.get('since'))
    if details.get('love') or row.get('role') in PARTNER_ROLES:
        return found(PARTNER_ROLES.get(row.get('role'), 'seeing'), {'key': 'companion'}, 'circle')
    if couple := couple_in_circle(row, people or ()):
        other, how, told = couple
        partner = {'key': key_of(other), 'name': other['name'], 'circle_id': other['id']}
        parted = TIES[how] == 'divorced'
        return found(TIES[how], None if parted else partner, 'user' if told else 'circle',
                     [partner] if parted else ())
    if details.get('married'):
        return found('married', {'key': seeded_partner(row) or f'{key_of(row)}/p0'}, 'circle')
    if seeded := seeded_partner(row):
        return found('seeing', {'key': seeded}, 'seed')
    return found('single', None, 'seed')


def couple_in_circle(row: dict, people) -> tuple[dict, str, bool] | None:
    """The other half of a couple tie inside the circle: (their row, how, whether the user set it)."""
    for other in people:
        if other['id'] == row['id'] or other.get('status', 'active') != 'active':
            continue
        how = circle.tie(row, other)
        if how in TIES:
            return other, how, circle.own_tie(row, other) is not None
    return None


def seeded_partner(row: dict) -> str | None:
    """The key of the partner the seed gives them among their own people (network.their_people), or None."""
    key = f'{key_of(row)}/0'
    relation, *_rest = network.choose_relation(key, 0, None)
    return key if relation == 'partner' else None


def single_by_event_since(row: dict, days: int, today: date | None = None) -> str | None:
    """The day a life event left them single, when that was within `days` of today: else None."""
    recorded = circle.details_of(row).get('partner')
    if not isinstance(recorded, dict) or recorded.get('state') != 'single' or not recorded.get('since'):
        return None
    today = today or date.today()
    return recorded['since'] if recorded['since'] >= (today - timedelta(days=days)).isoformat() else None
