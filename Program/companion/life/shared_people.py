"""People two companions both know (tester, 2026-10-26: Amanda, added on Sarek's page, is also Spock's mother).

Everyone in a circle lives in one companion's circle, their owner's, and keeps their week, job and diary there. The
user can add them to another companion's life too, saying how that companion knows them ("mother"). They then show
in that companion's circle list and one-on-one chat as the same person, and the owner's side says who else knows
them, so both chats agree. Only the owner's page changes who they are; the other side changes only how it knows them,
or lets them go. A share is kept by the person's seed, which a copied timeline keeps, and the person is read from the
owner's active timeline each time, so going back in time on either side keeps it.
"""
from companion.clock import stamp
from companion.database import decode, encode, many, optional
from companion.errors import require
from companion.life import agenda, ages, circle

ROLE_MAX = 40
# Places in someone's life only one person holds: someone shared in as mom takes the place of the mom the app made.
SLOTS = {'mother': {'mom', 'mother', 'mum'}, 'father': {'dad', 'father'}, 'spouse': {'wife', 'husband', 'spouse'}}
PARENT = {'she/her': 'mother', 'he/him': 'father'}


def owner_row(connection, owner_id: str, seed: str) -> tuple[dict, dict] | None:
    """The owner and the person as they are on the owner's active timeline; None once either is gone."""
    from companion.characters import by_id
    owner = by_id(connection, owner_id)
    row = owner and optional(connection, 'SELECT * FROM circle_people WHERE timeline_id=? AND seed=?',
                             (owner['active_timeline_id'], seed))
    return (owner, row) if row else None


def shared_with(connection, companion: dict, now) -> list[dict]:
    """People from other companions' circles that this one knows too, as circle_view has them, with `shared`: whose
    circle they live in and who they are there. Their diary leaves out what they did with the owner."""
    result = []
    for share in many(connection, 'SELECT * FROM circle_shares WHERE companion_id=? ORDER BY created_at',
                      (companion['id'],)):
        found = owner_row(connection, share['owner_id'], share['person_seed'])
        if not found or found[1]['status'] != 'active' or (decode(found[1]['details']) or {}).get('late'):
            continue
        owner, row = found
        timeline_id, said = owner['active_timeline_id'], circle.voice_of(connection, owner['active_timeline_id'])
        data = circle.city_of_timeline(connection, timeline_id)
        person = circle.view(row, data)
        if person.get('local', True) and not same_place(data, ages.city_of(connection, companion['version']['definition'])):
            person['local'] = False  # In the owner's town, which is not this companion's.
        recent = [{**entry, 'with_companion': None} for entry in agenda.diary(connection, timeline_id, row['id'], 6)
                  if entry['slot'] is not None][:3]
        result.append({**person, 'role': circle.era_word(share['role'], said), 'now': agenda.current(
            connection, timeline_id, row['id'], now), 'recent': recent, 'knows': [], 'shared': {
            'owner_id': owner['id'], 'owner': owner['version']['name'], 'role': circle.era_word(row['role'], said)}})
    return result


def same_place(first: dict | None, second: dict | None) -> bool:
    """Two companions' cities are one place; two the app doesn't know are taken as one too."""
    if not first or not second:
        return not first and not second
    return (first.get('id'), first.get('name')) == (second.get('id'), second.get('name'))


def also_known(connection, companion: dict) -> dict[str, list[dict]]:
    """For the owner's circle: {person id: [{companion_id, name, role}]}, the other companions who know them."""
    from companion.characters import by_id
    rows = {row['seed']: row['id'] for row in circle.people(connection, companion['active_timeline_id'], True)}
    said, result = circle.voice_of(connection, companion['active_timeline_id']), {}
    for share in many(connection, 'SELECT * FROM circle_shares WHERE owner_id=? ORDER BY created_at',
                      (companion['id'],)):
        other = by_id(connection, share['companion_id'])
        if other and share['person_seed'] in rows:
            result.setdefault(rows[share['person_seed']], []).append(
                {'companion_id': other['id'], 'name': other['version']['name'],
                 'role': circle.era_word(share['role'], said)})
    return result


def candidates(connection, companion: dict) -> list[dict]:
    """Who the user can add to this companion's life from the other companions' circles: the living, not already
    shared with them, grouped by companion in the order the web lists them."""
    from companion.life import web
    taken = {row['person_seed'] for row in many(connection, 'SELECT person_seed FROM circle_shares WHERE companion_id=?',
                                                (companion['id'],))}
    result = []
    for other in web.companions(connection):
        if other['id'] == companion['id'] or not other['active_timeline_id']:
            continue
        said = circle.voice_of(connection, other['active_timeline_id'])
        result += [{'id': row['id'], 'name': row['name'], 'full_name': circle.view(row).get('full_name') or row['name'],
                    'role': circle.era_word(row['role'], said),
                    'owner_id': other['id'], 'owner': other['version']['name']}
                   for row in circle.people(connection, other['active_timeline_id'])
                   if row['seed'] not in taken and not (decode(row['details']) or {}).get('late')]
    return result


def share(connection, companion: dict, person_id: str, role: str, now) -> list[dict]:
    """Add someone from another companion's circle to this one's life, or change how this one knows them. Returns
    the app-made people who stepped aside for them (step_aside)."""
    row = circle.person(connection, person_id)
    owner = optional(connection, 'SELECT companion_id FROM timelines WHERE id=?', (row['timeline_id'],))
    owner_id = owner and owner['companion_id']
    require(owner_id and owner_id != companion['id'], 'That person is already in their circle.', 409)
    require(optional(connection, 'SELECT id FROM companions WHERE id=? AND active_timeline_id=?',
                     (owner_id, row['timeline_id'])) is not None, 'That person is not in a circle now.', 404)
    require(row['status'] == 'active', 'Restore this person before adding them.', 409)
    role = ' '.join(role.split()).casefold()[:ROLE_MAX] or 'friend'
    connection.execute('INSERT INTO circle_shares (owner_id, person_seed, companion_id, role, created_at) VALUES '
                       '(?, ?, ?, ?, ?) ON CONFLICT (person_seed, companion_id) DO UPDATE SET role=excluded.role',
                       (owner_id, row['seed'], companion['id'], role, stamp(now)))
    step_back(connection, companion, row['seed'], now)
    return step_aside(connection, companion, row['seed'], role, now)


def slot_of(role: str, pronouns: str = '') -> str | None:
    """'mother', 'father' or 'spouse' for a role only one person holds; a plain 'parent' by their pronouns."""
    role = role.casefold()
    return next((slot for slot, words in SLOTS.items() if role in words), None) or \
        (PARENT.get(pronouns) if role == 'parent' else None)


def made_by_app(connection, row: dict) -> bool:
    """Someone the app made and the user never touched: not written into the character, not added or changed by
    hand, and not a partner the companion is seeing (companion/life/love_life.py)."""
    details = decode(row['details']) or {}
    if any(details.get(key) for key in ('sheet', 'by_hand', 'edited', 'late', 'kept')):
        return False
    return optional(connection, 'SELECT id FROM love_partners WHERE person_id=?', (row['id'],)) is None


def step_aside(connection, companion: dict, seed: str, role: str, now) -> list[dict]:
    """The app-made people in this companion's own circle whose place the shared person now takes (a second mom)
    step aside: removed, marked with whom they made room for, so Restore brings them back and taking the shared
    person out again does too. Returns their names and pronouns, for the notice."""
    if not (slot := slot_of(role)):
        return []
    timeline_id, names = companion['active_timeline_id'], []
    for row in circle.people(connection, timeline_id):
        details = decode(row['details']) or {}
        if slot_of(row['role'], details.get('pronouns', '')) == slot and made_by_app(connection, row):
            connection.execute("UPDATE circle_people SET status='removed', details=?, revision=revision+1, "
                               'updated_at=? WHERE id=?', (encode(details | {'stepped_aside': seed}), stamp(now),
                                                           row['id']))
            agenda.forget_person(connection, timeline_id, row['id'], now)
            names.append({'name': row['name'], 'pronouns': details.get('pronouns') or 'they/them'})
    return names


def step_back(connection, companion: dict, seed: str, now):
    """Whoever stepped aside for this shared person and is still out comes back."""
    timeline_id = companion['active_timeline_id']
    for row in circle.people(connection, timeline_id, include_removed=True):
        details = decode(row['details']) or {}
        if details.get('stepped_aside') == seed:
            details.pop('stepped_aside')
            if row['status'] == 'active':
                details['kept'] = True  # The user restored them themselves: they stay whatever happens next.
            status = 'active' if row['status'] == 'removed' else row['status']
            connection.execute('UPDATE circle_people SET status=?, details=?, revision=revision+1, updated_at=? '
                               'WHERE id=?', (status, encode(details), stamp(now), row['id']))
            agenda.forget_person(connection, timeline_id, row['id'], now)


def unshare(connection, companion: dict, person_id: str, now):
    """This companion no longer knows them; they stay in their owner's circle as they were, and whoever stepped
    aside for them comes back."""
    row = circle.person(connection, person_id)
    found = connection.execute('DELETE FROM circle_shares WHERE person_seed=? AND companion_id=?',
                               (row['seed'], companion['id'])).rowcount
    require(found > 0, 'That person is not in their life.', 404)
    step_back(connection, companion, row['seed'], now)


def is_shared(connection, companion: dict, person_id: str) -> bool:
    row = optional(connection, 'SELECT seed FROM circle_people WHERE id=?', (person_id,))
    return bool(row) and optional(connection, 'SELECT 1 AS found FROM circle_shares WHERE person_seed=? AND '
                                  'companion_id=?', (row['seed'], companion['id'])) is not None


def made_room(connection, companion: dict, people: list[dict], now) -> list[dict]:
    """The circle list's people, each who stepped aside with `made_room_for`: the name of who took their place."""
    names = {person['key']: person.get('full_name') or person['name'] for person in shared_with(
        connection, companion, now)} if any(person.get('stepped_aside') for person in people) else {}
    return [{**person, 'made_room_for': names.get(person.get('stepped_aside'))} if person.get('stepped_aside') else
            person for person in people]


def owner_text(shared: dict) -> str:
    """"Sarek's wife.": who someone from another circle is there, for the chat context."""
    return f"{shared['owner']}'s {shared['role']}."


def also_text(also: list[dict]) -> str:
    """"Also Spock's mother.": the other companions who know someone, for the owner's chat context."""
    names = [f"{item['name']}'s {item['role']}" for item in also]
    joined = names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"
    return f'Also {joined}.'
