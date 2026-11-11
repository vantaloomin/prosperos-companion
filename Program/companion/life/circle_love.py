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
    """The day a life event left them single (a breakup, or widowed), when that was within `days` of today: else
    None."""
    recorded = circle.details_of(row).get('partner')
    if not isinstance(recorded, dict) or recorded.get('state') not in ('single', 'widowed') or not recorded.get('since'):
        return None
    today = today or date.today()
    return recorded['since'] if recorded['since'] >= (today - timedelta(days=days)).isoformat() else None


# Telling it (companion/memory/context.py) ---------------------------------------------------------------------------

# Their love life of record in their circle line, once a life event (or the user) has decided it: the seeded default
# says nothing, and a couple inside the circle already reads "Separated from Ana" (circle.ties_text).
# A/B 2026-11-11 (/mnt/project-files/companion-world-consistency/ab): asked about Kaito's girlfriend months after his
# breakup, 23 of 30 replies went along without the line, 1 of 30 with it; "who is Mara marrying?" 26 of 30 wrong
# (19 made up a name) without it, none with it.
SAID = {'seeing': 'Seeing {partner}.', 'engaged': 'Engaged to {partner}.', 'married': 'Married to {partner}.',
        'separated': 'Separated from {partner}.'}
SINCE = {'single': 'Single since a breakup in {month}.', 'divorced': 'Divorced since {month}.',
         'widowed': 'Widowed in {month}.'}


def prompt_line(connection, companion: dict, row: dict, today: date) -> str | None:
    """"Engaged to Ren Ito.", "Single since a breakup in November.", or None when nothing has changed it."""
    recorded = circle.details_of(row).get('partner')
    if not isinstance(recorded, dict) or recorded.get('state') not in STATES:
        return None
    found = state(connection, row)
    partner = named(connection, companion, row, found['partner'])
    if found['state'] in SAID and partner and partner.get('name') and not partner.get('circle_id'):
        return SAID[found['state']].format(partner=partner.get('full') or partner['name'])
    if found['state'] in SINCE and found['since']:
        when = date.fromisoformat(found['since'])
        month = when.strftime('%B') + ('' if when.year == today.year else f' {when.year}')
        if found['state'] != 'single' or found['exes']:
            return SINCE[found['state']].format(month=month)
    return None


# Changing it (companion/life/happenings.py) -------------------------------------------------------------------------

# States with a partner now; the rest have none.
WITH_PARTNER = ('seeing', 'engaged', 'married', 'separated')


def change(connection, row: dict, to: str, day: str, source: str, now, partner: dict | None = None,
           people: list[dict] | None = None) -> dict | None:
    """Their love life becomes `to` from `day`: the partner they had (when it is not `partner`) becomes an ex. Written
    as `details.partner`, with `married` kept in step for the readers that look at it. Returns the undo
    (records.write), or None when nothing changed."""
    from companion.life import records
    now_state = state(connection, row, people)
    old = now_state['partner']
    keeps = to in WITH_PARTNER
    partner = (partner or old) if keeps else None
    exes = [ex for ex in now_state['exes'] if not partner or ex.get('key') != partner.get('key')]
    if old and old.get('key') != 'companion' and (not partner or old.get('key') != partner.get('key')):
        exes.append({**old, 'until': day, **({'married': True} if now_state['state'] in ('married', 'separated')
                                             else {})})
    record = {'state': to, **(partner or {}), 'since': day, 'source': source, 'exes': exes}
    record = {key: value for key, value in record.items() if value not in (None, '', [])} | {'state': to}
    return records.write(connection, row['id'], now, {'partner': record,
                                                      'married': True if to in ('married', 'separated') else None})


def tie_between(connection, first: dict, second: dict, how: str | None, now) -> list[dict]:
    """How two circle people stand now by a life event (`details.ties`, by seed, both ways), '' for not speaking and
    None for the app's own reading again. Returns the undos."""
    from companion.life import records
    undos = []
    for one_side, other in ((first, second), (second, first)):
        ties = dict(circle.details_of(one_side).get('ties') or {})
        if how is None:
            ties.pop(other['seed'], None)
        else:
            ties[other['seed']] = how
        if undo := records.write(connection, one_side['id'], now, {'ties': ties or None}):
            undos.append(undo)
    return undos


def named(connection, companion: dict, row: dict, partner: dict | None) -> dict | None:
    """The partner with their name: as recorded, the circle person, the companion, or found among the person's own
    people (network.find)."""
    if not partner or partner.get('name'):
        return partner
    if partner.get('key') == 'companion':
        return {**partner, 'name': companion['version']['definition']['name'].split()[0]}
    found = network.find(connection, companion, partner['key']) if partner.get('key') else None
    return {**partner, **{key: found[key] for key in ('name', 'full', 'pronouns')}} if found else partner


def new_partner(connection, companion: dict, row: dict) -> dict:
    """Someone new for them, who is not one of their seeded people: keyed `<their key>/p<n>` so network.find still
    finds them, named for their city and era."""
    found = state(connection, row)
    taken = [item.get('key') or '' for item in [*found['exes'], found['partner'] or {}]]
    index = sum('/p' in key for key in taken)
    key = f'{key_of(row)}/p{index}'
    details = circle.details_of(row)
    full = details.get('full_name') or row['name']
    person = network.made({'key': key_of(row), 'name': row['name'], 'age': details.get('age') or 33, 'depth': 1,
                           'family': full.split()[-1] if ' ' in full else '', 'circle_id': row['id']},
                          {'key': key}, network.city(connection, companion),
                          network.names_taken(connection, companion) | {row['name']})
    return {'key': key, 'name': person['name'], 'full': person['full'], 'pronouns': person['pronouns']}
