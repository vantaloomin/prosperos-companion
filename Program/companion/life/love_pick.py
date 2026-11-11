"""The user's own pick for a circle person's love life (Edit person, "Their love life"), after the app has decided it.

The app decides first (companion/life/circle_love.py): a seeded partner, a couple in the circle, a life event. The
user can then say Single, Seeing someone, Engaged or Married, and who with: a name, someone in the circle, or left to
the app. The pick is written as `details.partner` with source 'user' and `partner` in `edited`, so no life event
changes it (casting.love_is_apps) until the user sets it back to the app, which puts back what the app had.

Picking someone in the circle links the two of them both ways, and whoever that person was with is left single, the
way a breakup would leave them, so nothing changes out of sight. What already happened keeps what it said: a pick
writes no diary line and makes nobody an ex. Rules only, no model.
"""
from companion.life import ages, circle, circle_love, records

CHOICES = ('single', 'seeing', 'engaged', 'married')
# How two circle people stand once one of them is picked away from the other.
PARTED_TIE = {'married': 'divorced', 'separated': 'divorced'}
TOGETHER_TIE = {'married': 'married'}


def editable(row: dict) -> bool:
    """Not the companion's own partner (their partner is the companion: the partner card), and an adult."""
    details = circle.details_of(row)
    if details.get('love') or row.get('role') in circle_love.PARTNER_ROLES:
        return False
    age = details.get('age')
    return not isinstance(age, int) or age >= ages.ADULT


def shown(connection, companion: dict, row: dict, people: list[dict]) -> dict:
    """For the form: {state, partner (first name or None), set (the user's pick), editable}."""
    found = circle_love.state(connection, row, people)
    partner = circle_love.named(connection, companion, row, found['partner'])
    return {'state': found['state'], 'partner': first_name(partner), 'set': found['decided'] == 'user',
            'editable': editable(row)}


def first_name(partner: dict | None) -> str | None:
    name = (partner or {}).get('name') or ''
    return name.split()[0] if name.split() else None


def suggestions(connection, companion: dict, people: list[dict]) -> list[dict]:
    """The circle people someone could be with, and where each stands now ("married to Kaito"), for "Who with"."""
    result = []
    for row in people:
        if not editable(row):
            continue
        found = shown(connection, companion, row, people)
        partner = found['partner']
        words = {'seeing': f'seeing {partner}', 'engaged': f'engaged to {partner}',
                 'married': f'married to {partner}'}.get(found['state']) if partner else None
        result.append({'id': row['id'], 'name': row['name'], 'stands': words})
    return result


def pick(connection, companion: dict, row: dict, love: str, name: str | None, now) -> None:
    """The user's pick: '' hands their love life back to the app."""
    people = circle.people(connection, row['timeline_id'])
    unlink(connection, row, people, now)
    row = circle.person(connection, row['id'])
    if not love:
        back_to_app(connection, row, now)
        return
    found = circle_love.state(connection, row, people)
    partner = partner_for(connection, companion, row, found, name, people) if love != 'single' else None
    if (found['partner'] or {}).get('circle_id') and (partner or {}).get('circle_id') != found['partner']['circle_id']:
        leave_partner(connection, row, people, now)  # Their partner in the circle is not theirs now.
    # Single by the user's word is no breakup: no "single since" unless a life event already left them single.
    since = (found['since'] if found['state'] == 'single' else None) if love == 'single' else now.date().isoformat()
    write(connection, row, love, partner, found['exes'], since, now)
    if partner and partner.get('circle_id'):
        other = circle.person(connection, partner['circle_id'])
        unlink(connection, other, people, now)
        leave_partner(connection, other, people, now)
        other = circle.person(connection, other['id'])
        mine = {'key': row['seed'], 'name': row['name'], 'circle_id': row['id']}
        write(connection, other, love, mine, circle_love.state(connection, other, people)['exes'],
              now.date().isoformat(), now)
        circle_love.tie_between(connection, circle.person(connection, row['id']), other,
                                TOGETHER_TIE.get(love, 'partners'), now)


def write(connection, row: dict, love: str, partner: dict | None, exes, since: str | None, now) -> None:
    """Their pick as `details.partner`, keeping what the app had to put back later."""
    details = circle.details_of(row)
    kept = [ex for ex in exes if not partner or ex.get('key') != partner.get('key')]
    record = {'state': love, **(partner or {}), 'since': since, 'source': 'user', 'exes': kept}
    record = {key: value for key, value in record.items() if value not in (None, '', [])}
    before = details.get('partner_before')
    if before is None:
        before = {'partner': details.get('partner'), 'married': details.get('married')}
    records.write(connection, row['id'], now, {
        'partner': record, 'married': True if love == 'married' else None, 'partner_before': before,
        'edited': sorted(set(details.get('edited', ())) | {'partner'})})


def back_to_app(connection, row: dict, now) -> None:
    """What the app had before the user's pick, and the app decides again from here."""
    details = circle.details_of(row)
    if 'partner_before' not in details and 'partner' not in set(details.get('edited', ())):
        return
    before = details.get('partner_before') or {}
    edited = sorted(set(details.get('edited', ())) - {'partner'})
    records.write(connection, row['id'], now, {'partner': before.get('partner'), 'married': before.get('married'),
                                               'partner_before': None, 'edited': edited or None})


def partner_for(connection, companion: dict, row: dict, found: dict, name: str | None, people) -> dict:
    """Who they are with: someone in the circle by name, the partner they have when the name is theirs (or none is
    given), else someone new by that name, or new and named by the app."""
    name = ' '.join((name or '').split())
    current = found['partner'] if found['partner'] and found['partner'].get('key') != 'companion' else None
    current = circle_love.named(connection, companion, row, current) if current else None
    if not name:
        return current or circle_love.new_partner(connection, companion, row)
    if current and plain(name) in {plain(current.get('name')), plain(current.get('full'))}:
        return current
    if other := in_circle(name, row, people):
        return {'key': other['seed'], 'name': other['name'], 'circle_id': other['id']}
    made = circle_love.new_partner(connection, companion, row)
    return {'key': made['key'], 'name': name.split()[0], 'full': name}


def in_circle(name: str, row: dict, people) -> dict | None:
    wanted = plain(name)
    return next((other for other in people if other['id'] != row['id'] and editable(other) and wanted in {
        plain(other['name']), plain(circle.details_of(other).get('full_name'))}), None)


def plain(text: str | None) -> str:
    return ' '.join((text or '').split()).casefold()


def unlink(connection, row: dict, people, now) -> None:
    """A partner in the circle the user linked them to earlier is handed back to the app as well."""
    recorded = circle.details_of(row).get('partner')
    if not isinstance(recorded, dict) or recorded.get('source') != 'user' or not recorded.get('circle_id'):
        return
    other = next((item for item in people if item['id'] == recorded['circle_id']), None)
    if other is None:
        return
    other = circle.person(connection, other['id'])
    theirs = circle.details_of(other).get('partner')
    if isinstance(theirs, dict) and theirs.get('source') == 'user' and theirs.get('circle_id') == row['id']:
        back_to_app(connection, other, now)
    circle_love.tie_between(connection, row, other, None, now)


def leave_partner(connection, row: dict, people, now) -> None:
    """Someone in the circle is picked to be with someone else: whoever in the circle they were with is single now,
    with them as an ex, as a breakup would leave them."""
    found = circle_love.state(connection, row, people)
    partner = found['partner'] or {}
    old = next((item for item in people if partner.get('circle_id') and item['id'] == partner['circle_id']), None)
    if old is None:
        return
    old = circle.person(connection, old['id'])
    theirs = circle_love.state(connection, old, people)['partner'] or {}
    if theirs.get('circle_id') != row['id'] and theirs.get('key') != row['seed']:
        return
    day = now.date().isoformat()
    circle_love.change(connection, old, 'single', day, f'user:{row["id"]}', now, people=people)
    circle_love.tie_between(connection, row, old, PARTED_TIE.get(found['state'], 'known for years'), now)
