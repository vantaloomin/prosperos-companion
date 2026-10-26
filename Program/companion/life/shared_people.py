"""People two companions both know (tester, 2026-10-26: Amanda, added on Sarek's page, is also Spock's mother).

Everyone in a circle lives in one companion's circle, their owner's, and keeps their week, job and diary there. The
user can add them to another companion's life too, saying how that companion knows them ("mother"). They then show
in that companion's circle list and one-on-one chat as the same person, and the owner's side says who else knows
them, so both chats agree. Only the owner's page changes who they are; the other side changes only how it knows them,
or lets them go. A share is kept by the person's seed, which a copied timeline keeps, and the person is read from the
owner's active timeline each time, so going back in time on either side keeps it.
"""
from companion.clock import stamp
from companion.database import decode, many, optional
from companion.errors import require
from companion.life import agenda, ages, circle

ROLE_MAX = 40


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


def share(connection, companion: dict, person_id: str, role: str, now) -> str:
    """Add someone from another companion's circle to this one's life, or change how this one knows them. Returns
    the person's seed."""
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
    return row['seed']


def unshare(connection, companion: dict, person_id: str):
    """This companion no longer knows them; they stay in their owner's circle as they were."""
    row = circle.person(connection, person_id)
    found = connection.execute('DELETE FROM circle_shares WHERE person_seed=? AND companion_id=?',
                               (row['seed'], companion['id'])).rowcount
    require(found > 0, 'That person is not in their life.', 404)


def is_shared(connection, companion: dict, person_id: str) -> bool:
    row = optional(connection, 'SELECT seed FROM circle_people WHERE id=?', (person_id,))
    return bool(row) and optional(connection, 'SELECT 1 AS found FROM circle_shares WHERE person_seed=? AND '
                                  'companion_id=?', (row['seed'], companion['id'])) is not None


def owner_text(shared: dict) -> str:
    """"Sarek's wife.": who someone from another circle is there, for the chat context."""
    return f"{shared['owner']}'s {shared['role']}."


def also_text(also: list[dict]) -> str:
    """"Also Spock's mother.": the other companions who know someone, for the owner's chat context."""
    names = [f"{item['name']}'s {item['role']}" for item in also]
    joined = names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"
    return f'Also {joined}.'
