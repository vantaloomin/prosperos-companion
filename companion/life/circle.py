"""The companion's social circle (PRD T8).

A few supporting people, assembled once per timeline from the world data and a seed, without a
model. In a known city they come from the world data's circle generator: a name from the city's
name groups, how they know the companion, an age, a home, a job with its weekly routine and a few
regular haunts; relatives may live out of town and have no routine here. Elsewhere a simpler
version picks a first name, a role and a career's routine. Their days advance through the same precomputed agenda as the companion's
(companion/life/agenda.py). They are fictional supporting characters: never the user, never a
real person, and never a source of facts about the user. The user can rename or remove them.
"""
from datetime import date, timedelta

from companion.clock import stamp
from companion.database import decode, encode, identifier, many, one, optional
from companion.errors import require
from companion.world import catalog, generators

CIRCLE_SIZE = 5
ROLES = ('close friend', 'old friend from school', 'coworker', 'sibling', 'neighbor', 'cousin', 'roommate from years ago')
# The first slot is always a close friend; the rest vary by seed.
NAMES = (
    'Ada', 'Amara', 'Andre', 'Bea', 'Caleb', 'Camila', 'Dario', 'Dev', 'Elena', 'Eli', 'Farah', 'Felix', 'Gabe',
    'Grace', 'Hana', 'Hugo', 'Imani', 'Iris', 'Jae', 'Jonah', 'June', 'Kai', 'Keisha', 'Leo', 'Lina', 'Luis',
    'Maya', 'Milo', 'Nadia', 'Nico', 'Noor', 'Omar', 'Owen', 'Priya', 'Quinn', 'Rafael', 'Rosa', 'Sam', 'Sana',
    'Theo', 'Tess', 'Uma', 'Victor', 'Wen', 'Yusuf', 'Zara', 'Zoe', 'Marcus', 'Ines', 'Tomas',
)


def city_data(definition: dict, world) -> dict | None:
    """The world data for the companion's home city or location, if the world knows it."""
    find = getattr(world, 'find', None)
    for text in (definition.get('home_city'), definition.get('location')):
        if text and find and (data := find(text)):
            return data
    return None


def assemble(seed: str, ordinal: int, definition: dict, data: dict | None, taken: set[str]) -> dict:
    """One person, the same for the same seed, ordinal, city data and names already taken."""
    names = [name for name in NAMES if name not in taken]
    name = generators.pick(seed, 'name', names) if names else f'Friend {ordinal + 1}'
    role = ROLES[0] if ordinal == 0 else generators.pick(seed, 'role', list(ROLES[1:]))
    offered = catalog.careers_for(data) if data else {
        key: career for key, career in catalog.careers().items() if 'modern' in career['eras']}
    career_id = generators.pick(seed, 'career', sorted(offered))
    career = offered[career_id]
    if data:
        job = generators.job(data, career_id, seed=seed)
        details = {'career': career['name'], 'employer': job['employer']['name'],
                   'neighborhood': job['neighborhood']['name'], 'city': data['name'],
                   'refs': job['refs'], 'sources': job['sources'], 'data_version': job['data_version']}
        schedule = job['schedule']
    else:
        details = {'career': career['name'], 'employer': '', 'neighborhood': '', 'city': '', 'refs': [],
                   'sources': [], 'data_version': ''}
        schedule = generators.schedule(career, seed)
    return {'name': name, 'role': role, 'career': career_id, 'details': details, 'schedule': schedule}


def from_city(data: dict, definition: dict, timeline_id: str) -> list[dict]:
    """The circle from the world data's generator, closest first, living near the companion when
    their location names a neighborhood."""
    match = catalog.resolve(definition.get('location') or '')
    hoods = {hood['id'] for hood in data['neighborhoods']}
    home = match['neighborhood'] if match and match['neighborhood'] in hoods else None
    made = generators.circle(data, seed=f'circle:{timeline_id}', size=CIRCLE_SIZE, home=home)
    result, taken = [], {definition['name']}
    for member in made['people']:
        job = member['job'] or {}
        details = {'career': (job.get('career') or {}).get('name', 'Retired' if member['local'] else ''),
                   'employer': (job.get('employer') or {}).get('name', ''),
                   'neighborhood': member['home']['neighborhood']['name'] if member['home'] else '',
                   'city': data['name'] if member['local'] else '', 'full_name': member['name']['full'],
                   'pronouns': member['name']['pronouns'], 'age': member['age'], 'local': member['local'],
                   'closeness': member['closeness'], 'haunts': [spot['name'] for spot in member['haunts']],
                   'refs': member.get('refs', []), 'sources': member.get('sources', []),
                   'data_version': data['data_version']}
        # Two people with the same first name go by their full names, so events stay unambiguous.
        shown = member['name']['given'] if member['name']['given'] not in taken else member['name']['full']
        taken.add(shown)
        result.append({'name': shown, 'role': member['role'].replace('-', ' '),
                       'career': (job.get('career') or {}).get('id', ''), 'details': details,
                       'schedule': member['schedule'] or []})
    return result


def birthday(person_id: str) -> str:
    """A person's birthday as "MM-DD", seeded by their id (never 29 February)."""
    return (date(2001, 1, 1) + timedelta(days=int(generators.unit(person_id, 'birthday') * 365))).strftime('%m-%d')


def view(row: dict) -> dict:
    return {'id': row['id'], 'name': row['name'], 'role': row['role'], 'status': row['status'],
            'revision': row['revision'], **decode(row['details']), 'birthday': birthday(row['id']),
            'schedule': decode(row['schedule'])}


def ensure(connection, companion: dict, world, now) -> list[dict]:
    """The active timeline's circle, assembling it the first time it is needed."""
    timeline_id = companion['active_timeline_id']
    rows = people(connection, timeline_id, include_removed=True)
    if rows:
        return [row for row in rows if row['status'] == 'active']
    definition = companion['version']['definition']
    data = city_data(definition, world)
    if data:
        built = from_city(data, definition, timeline_id)
    else:
        taken, built = {definition['name']}, []
        for ordinal in range(CIRCLE_SIZE):
            built.append(assemble(f'circle:{timeline_id}:{ordinal}', ordinal, definition, None, taken))
            taken.add(built[-1]['name'])
    for ordinal, person in enumerate(built):
        seed = f'circle:{timeline_id}:{ordinal}'
        connection.execute(
            'INSERT OR IGNORE INTO circle_people (id, timeline_id, ordinal, seed, name, role, career, details, schedule, '
            'created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (identifier(), timeline_id, ordinal, seed, person['name'], person['role'], person['career'],
             encode(person['details']), encode(person['schedule']), stamp(now), stamp(now)))
    return people(connection, timeline_id)


def people(connection, timeline_id, include_removed=False) -> list[dict]:
    status = '' if include_removed else "AND status='active' "
    return many(connection, f'SELECT * FROM circle_people WHERE timeline_id=? {status}ORDER BY ordinal', (timeline_id,))


def person(connection, person_id) -> dict:
    row = optional(connection, 'SELECT * FROM circle_people WHERE id=?', (person_id,))
    require(row is not None, 'That person is not in the circle.', 404)
    return row


def rename(connection, person_id, name: str, now) -> dict:
    row = person(connection, person_id)
    require(row['status'] == 'active', 'Restore this person before renaming them.', 409)
    connection.execute('UPDATE circle_people SET name=?, revision=revision+1, updated_at=? WHERE id=?',
                       (name.strip(), stamp(now), person_id))
    return one(connection, 'SELECT * FROM circle_people WHERE id=?', (person_id,))


def set_status(connection, person_id, status: str, now) -> dict:
    """A removed person stops appearing in new entries; what already happened stays."""
    person(connection, person_id)
    connection.execute('UPDATE circle_people SET status=?, revision=revision+1, updated_at=? WHERE id=?',
                       (status, stamp(now), person_id))
    return one(connection, 'SELECT * FROM circle_people WHERE id=?', (person_id,))
