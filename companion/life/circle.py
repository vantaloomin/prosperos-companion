"""The companion's social circle (PRD T8).

A few supporting people, assembled once per timeline from the world data and a seed, without a
model. In a known city they come from the world data's circle generator: a name from the city's
name groups, how they know the companion, an age, a home, a job with its weekly routine and a few
regular haunts; relatives may live out of town and have no routine here. Elsewhere a simpler
version picks a first name, a role and a career's routine. Their days advance through the same precomputed agenda as the companion's
(companion/life/agenda.py). They are fictional supporting characters: never the user, never a
real person, and never a source of facts about the user. The user can rename or remove them.

How many people depends on who the companion is: a social butterfly (outgoing, extroverted, life of
the party) gets a bigger circle with friends old and new, coworkers and both parents; a shy homebody
a smaller one. The Life setting `circle_size` overrides it, and grow() adds people to a circle that
was assembled smaller. Who knows whom inside the circle (family, coworkers, old friends) is derived
from roles and a seed by ties(), so storylines between them stay consistent.

Parents and siblings carry the companion's family name. A difference needs a marriage to explain it: a
sibling the circle records as married may go by a married name, and a companion who has married (or names
a maiden name with "née") has relatives with their birth name, or a name of their own when none is given.
Cousins may or may not share it.
"""
import re
from datetime import date, timedelta

from companion.clock import stamp
from companion.database import decode, encode, identifier, many, one, optional
from companion.errors import require
from companion.world import catalog, generators, naming

CIRCLE_SIZE = 5
SIZES = {'quiet': 4, 'usual': CIRCLE_SIZE, 'social': 10}
ROLES = ('close friend', 'old friend from school', 'coworker', 'sibling', 'neighbor', 'cousin', 'roommate from years ago')
# The roles a sociable companion's circle fills in without city data (generators.SOCIAL with it).
SOCIAL_ROLES = ('close friend', 'longtime friend', 'coworker', 'sibling', 'parent', 'new friend', 'coworker',
                'friend', 'parent', 'new friend', 'cousin', 'friend')
SOCIAL_WORDS = re.compile(r"\b(?:social butterfly|outgoing|extroverted|extrovert|extraverted|extravert|gregarious|"
                          r"sociable|life of the party|people person|party (?:girl|guy|animal)|knows everyone|bubbly|"
                          r"social life|loves (?:people|parties|meeting people))\b", re.IGNORECASE)
QUIET_WORDS = re.compile(r"\b(?:introverted|introvert|shy|loner|reserved|homebody|recluse|reclusive|solitary|"
                         r"keeps to (?:herself|himself|themselves|themself)|private person|antisocial|anti-social)\b",
                         re.IGNORECASE)
NEGATED = re.compile(r"\b(?:not|never|isn't|aren't|wasn't|hardly|far from|anything but)\s+(?:\w+\s+)?$", re.IGNORECASE)
FAMILY = {'parent', 'mom', 'dad', 'sibling', 'sister', 'brother', 'cousin'}
# Relatives who share the companion's family name unless a marriage explains otherwise.
IMMEDIATE = {'parent', 'mom', 'dad', 'sibling', 'sister', 'brother'}
SUFFIXES = {'jr', 'jr.', 'sr', 'sr.', 'ii', 'iii', 'iv'}
BIRTH_NAME = re.compile(r"\b(?:n[ée]e|maiden name(?: is| was|:)?|born with the (?:last|family) name)\s+"
                        r"([A-Z][A-Za-z'’-]+)")
MARRIED = re.compile(r"\b(?:(?:is|was|got|been|happily|recently|newly|now|i'm|she's|he's|they're)\s+"
                     r"(?:married|divorced|widowed)|(?:a )?(?:widow|widower|divorcee)|"
                     r"(?:my|her|his|their)\s+(?:late |ex-?)?(?:husband|wife|spouse))\b", re.IGNORECASE)
# How likely a sibling of this age is married, and how likely a married sibling took their spouse's name.
MARRIED_BY_AGE = ((25, 0.0), (30, 0.3), (200, 0.55))
TAKES_NAME = {'she/her': 0.8, 'he/him': 0.03}
OLD_FRIENDS = {'close friend', 'longtime friend', 'old friend from school', 'old classmate'}
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


def sociability(definition: dict) -> str:
    """'social', 'quiet' or 'usual', from words in their identity, personality, interests and themes."""
    text = ' '.join([definition.get('identity') or '', definition.get('personality') or '',
                     *(definition.get('interests') or ()), *(definition.get('life_themes') or ())])

    def count(pattern):
        return sum(1 for match in pattern.finditer(text)
                   if not NEGATED.search(text[max(0, match.start() - 30):match.start()]))
    social, quiet = count(SOCIAL_WORDS), count(QUIET_WORDS)
    return 'social' if social > quiet else 'quiet' if quiet > social else 'usual'


def target_size(definition: dict, setting: int = 0) -> int:
    """How many people their circle has: the Life setting when set, else by how sociable they are."""
    return setting or SIZES[sociability(definition)]


def setting(connection) -> int:
    row = optional(connection, 'SELECT circle_size FROM life_settings WHERE id=1')
    return row['circle_size'] if row else 0


def assemble(seed: str, ordinal: int, definition: dict, data: dict | None, taken: set[str],
             role: str | None = None) -> dict:
    """One person, the same for the same seed, ordinal, city data and names already taken."""
    names = [name for name in NAMES if name not in taken]
    name = generators.pick(seed, 'name', names) if names else f'Friend {ordinal + 1}'
    role = role or (ROLES[0] if ordinal == 0 else generators.pick(seed, 'role', list(ROLES[1:])))
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


def from_city(data: dict, definition: dict, timeline_id: str, size: int = CIRCLE_SIZE, seed: str | None = None,
              taken: set[str] | None = None) -> list[dict]:
    """The circle from the world data's generator, closest first, living near the companion when
    their location names a neighborhood. A circle bigger than the usual one fills in sociably."""
    match = catalog.resolve(definition.get('location') or '')
    hoods = {hood['id'] for hood in data['neighborhoods']}
    home = match['neighborhood'] if match and match['neighborhood'] in hoods else None
    social = size > CIRCLE_SIZE
    order = generators.SOCIAL if social else generators.CIRCLE
    works = social and bool(work_blocks(definition))
    family = family_name(definition)
    made = generators.circle(data, seed=seed or f'circle:{timeline_id}', size=min(size, len(order)), home=home,
                             order=order, coworkers=works, family=family, group=family_group(data, family))
    result, taken = [], set(taken or ()) | {definition['name']}
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
        if family and member['role'] in ('parent', 'sibling'):
            details['full_name'] = f"{member['name']['given']} {family_form(family, member['name']['pronouns'])}"
            if member['role'] == 'sibling':
                details |= married_sibling(data, timeline_id, member['name'], member['age'], family)
        # Two people with the same first name go by their full names, so events stay unambiguous.
        shown = member['name']['given'] if member['name']['given'] not in taken else details['full_name']
        taken.add(shown)
        made_person = {'name': shown, 'role': relation(member['role'], member['name']['pronouns']),
                       'career': (job.get('career') or {}).get('id', ''), 'details': details,
                       'schedule': member['schedule'] or []}
        result.append(colleague(made_person, definition) if member['role'] == 'coworker' else made_person)
    return result


def family_name(definition: dict) -> str | None:
    """The family name the companion's parents and siblings carry (in its listed form: Kowalski for Anna
    Kowalska): their own last name, or the birth name they give with "née"; None for a one-word name or a companion who has married without naming one."""
    text = ' '.join(definition.get(key) or '' for key in ('identity', 'background'))
    if match := BIRTH_NAME.search(text):
        return family_form(match.group(1), 'he/him')
    words = [word for word in (definition.get('name') or '').split() if word.casefold() not in SUFFIXES]
    if len(words) < 2 or MARRIED.search(text):
        return None
    return family_form(words[-1], 'he/him')


def family_group(data: dict, family: str | None) -> str | None:
    """A name group of the city whose family names (or linked cultures') include this one, for fitting given names."""
    if not family:
        return None
    groups, mix = catalog.name_groups(data)
    for key in sorted(mix, key=lambda item: -mix[item]):
        group = groups[key]
        if family in group.get('family', ()) or any(
                naming.base_family(culture, family) in naming.culture_surnames(culture)
                for culture in naming.links(group, data)):
            return key
    return None


def family_form(family: str, pronouns: str) -> str:
    """The family name as this relative carries it (Kowalski for a brother, Kowalska for a sister)."""
    for culture in naming.FEMININE_ENDINGS:
        base = naming.base_family(culture, family)
        if base in naming.culture_surnames(culture):
            return naming.gendered(culture, base, 'she' if pronouns == 'she/her' else 'he')
    return family


def married_sibling(data: dict | None, timeline_id: str, name: dict, age: int, family: str) -> dict:
    """Whether a sibling is married, and the married name they go by when they took their spouse's.
    Seeded by the timeline, given name and age, so a circle rebuilt or corrected gets the same answer."""
    key = f"married:{timeline_id}:{name['given']}:{age}"
    chance = next(share for limit, share in MARRIED_BY_AGE if (age or 0) < limit)
    if generators.unit(key, 'married') >= chance:
        return {}
    details = {'married': True}
    if data and generators.unit(key, 'takes-name') < TAKES_NAME.get(name['pronouns'], 0.3):
        for attempt in range(5):
            spouse = generators.name(data, seed=f'{key}:spouse:{attempt}')['family']
            if spouse not in (family, name['given']):
                details |= {'birth_family': family_form(family, name['pronouns']),
                            'full_name': f"{name['given']} {family_form(spouse, name['pronouns'])}"}
                break
    return details


def relation(role: str, pronouns: str) -> str:
    """How the companion would say it: "mom" and "brother" rather than "parent" and "sibling"."""
    words = {'parent': ('mom', 'dad'), 'sibling': ('sister', 'brother')}.get(role)
    if words and pronouns in ('she/her', 'he/him'):
        return words[pronouns != 'she/her']
    return role.replace('-', ' ')


def work_blocks(definition: dict) -> list[dict]:
    from companion.life import routine
    return [block.view() for block in routine.blocks(definition)[0] if block.kind == 'work']


def colleague(person: dict, definition: dict) -> dict:
    """A coworker works where the companion works, on the same hours; their own nights and free time
    stay theirs where they do not clash with work."""
    work = work_blocks(definition)
    if not work:
        return person
    own = [block for block in person['schedule'] if block['kind'] != 'work'
           and (block['kind'] == 'sleep' or not any(clashes(block, item) for item in work))]
    details = {**person['details'], 'career': f"Works with {definition['name']}", 'employer': '',
               'works_with_companion': True}
    return {**person, 'career': '', 'details': details, 'schedule': [*work, *own]}


def clashes(one_block: dict, other: dict) -> bool:
    days = set(one_block.get('days', range(7))) & set(other.get('days', range(7)))
    if not days or one_block['start'] >= one_block['end'] or other['start'] >= other['end']:
        return bool(days)
    return one_block['start'] < other['end'] and other['start'] < one_block['end']


def birthday(person_id: str) -> str:
    """A person's birthday as "MM-DD", seeded by their id (never 29 February)."""
    return (date(2001, 1, 1) + timedelta(days=int(generators.unit(person_id, 'birthday') * 365))).strftime('%m-%d')


def view(row: dict) -> dict:
    return {'id': row['id'], 'key': row['seed'], 'name': row['name'], 'role': row['role'], 'status': row['status'],
            'revision': row['revision'], **decode(row['details']), 'birthday': birthday(row['id']),
            'schedule': decode(row['schedule'])}


def build(definition: dict, world, timeline_id: str, size: int, seed: str | None = None, taken=()) -> list[dict]:
    """`size` people, closest first, from the city's generator when the world knows their city."""
    base = seed or f'circle:{timeline_id}'
    data = city_data(definition, world)
    if data:
        return from_city(data, definition, timeline_id, size, base, set(taken))
    names, roles, built = set(taken) | {definition['name']}, SOCIAL_ROLES if size > CIRCLE_SIZE else None, []
    for ordinal in range(min(size, len(SOCIAL_ROLES))):
        person = assemble(f'{base}:{ordinal}', ordinal, definition, None, names, roles[ordinal] if roles else None)
        built.append(colleague(person, definition) if roles and person['role'] == 'coworker' else person)
        names.add(person['name'])
    return built


def insert(connection, timeline_id, built: list[dict], first: int, now):
    for ordinal, person in enumerate(built, start=first):
        connection.execute(
            'INSERT OR IGNORE INTO circle_people (id, timeline_id, ordinal, seed, name, role, career, details, schedule, '
            'created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (identifier(), timeline_id, ordinal, f'circle:{timeline_id}:{ordinal}', person['name'], person['role'],
             person['career'], encode(person['details']), encode(person['schedule']), stamp(now), stamp(now)))


def ensure(connection, companion: dict, world, now) -> list[dict]:
    """The active timeline's circle, assembling it the first time it is needed."""
    timeline_id = companion['active_timeline_id']
    rows = people(connection, timeline_id, include_removed=True)
    if rows:
        if match_family(connection, companion, world, rows, now):
            rows = people(connection, timeline_id, include_removed=True)
        return [row for row in rows if row['status'] == 'active']
    definition = companion['version']['definition']
    insert(connection, timeline_id, build(definition, world, timeline_id, target_size(definition, setting(connection))),
           0, now)
    return people(connection, timeline_id)


def match_family(connection, companion: dict, world, rows: list[dict], now) -> bool:
    """Give parents and siblings assembled before relatives shared the companion's family name that name
    (or a recorded married one). People the user renamed keep their name. True when anyone changed."""
    definition = companion['version']['definition']
    family = family_name(definition)
    relatives = [row for row in rows if role_kind(row['role']) in ('parent', 'sibling')]
    if not family or not relatives:
        return False
    data, changed = None, False
    for row in relatives:
        details = decode(row['details'])
        full = details.get('full_name')
        if not full or not (full == row['name'] or full.startswith(f"{row['name']} ")):
            continue
        given = row['name'] if full != row['name'] else full.split()[0]
        pronouns = details.get('pronouns', '')
        wanted = {'full_name': f'{given} {family_form(family, pronouns)}'}
        if role_kind(row['role']) == 'sibling':
            data = data or city_data(definition, world)
            wanted |= married_sibling(data, row['timeline_id'], {'given': given, 'pronouns': pronouns},
                                      details.get('age') or 0, family)
        current = {key: details[key] for key in ('full_name', 'married', 'birth_family') if key in details}
        if current == wanted:
            continue
        kept = {key: value for key, value in details.items() if key not in ('married', 'birth_family')}
        name = wanted['full_name'] if full == row['name'] else row['name']
        connection.execute('UPDATE circle_people SET name=?, details=?, updated_at=? WHERE id=?',
                           (name, encode(kept | wanted), stamp(now), row['id']))
        changed = True
    return changed


def role_kind(role: str) -> str:
    return {'mom': 'parent', 'dad': 'parent', 'sister': 'sibling', 'brother': 'sibling',
            'old classmate': 'old friend from school'}.get(role, role)


def room(connection, companion: dict) -> dict:
    """How many people the circle has and could have, for the "add people" offer."""
    definition = companion['version']['definition']
    active = len(people(connection, companion['active_timeline_id']))
    return {'people': active, 'target': target_size(definition, setting(connection)),
            'sociability': sociability(definition)}


def grow(connection, companion: dict, world, now) -> list[dict]:
    """Add people to a circle smaller than it should be, filling the roles a sociable circle has and this
    one lacks (coworkers, old and new friends, family) before anyone else. Nobody already there changes."""
    timeline_id, definition = companion['active_timeline_id'], companion['version']['definition']
    ensure(connection, companion, world, now)
    rows = people(connection, timeline_id, include_removed=True)
    active = [row for row in rows if row['status'] == 'active']
    want = target_size(definition, setting(connection))
    require(len(active) < want, 'Their circle already has everyone it should. Raise the circle size in Settings '
            'to add more people.', 409)
    taken = {row['name'] for row in rows}
    candidates = build(definition, world, timeline_id, len(SOCIAL_ROLES), f'circle:{timeline_id}:more:{len(rows)}', taken)
    have = {}
    for row in active:
        have[role_kind(row['role'])] = have.get(role_kind(row['role']), 0) + 1
    need = {}
    for role in SOCIAL_ROLES[:want]:
        need[role] = need.get(role, 0) + 1
    chosen = []
    for person in candidates:
        kind = role_kind(person['role'])
        if need.get(kind, 0) > have.get(kind, 0):
            chosen.append(person)
            have[kind] = have.get(kind, 0) + 1
    chosen += [person for person in candidates if person not in chosen]
    insert(connection, timeline_id, chosen[:want - len(active)], max(row['ordinal'] for row in rows) + 1, now)
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


def tie(first: dict, second: dict) -> str | None:
    """How two circle members know each other, the same every time for the same two people."""
    kinds = {role_kind(first['role']), role_kind(second['role'])}
    pair = ':'.join(sorted((first['id'], second['id'])))
    if kinds == {'parent'}:
        return 'divorced' if generators.unit(pair, 'divorced') < 0.25 else 'married'
    if kinds <= FAMILY:
        return 'family'
    if kinds == {'coworker'}:
        return 'coworkers'
    if kinds <= OLD_FRIENDS:
        return 'old friends'
    if kinds & OLD_FRIENDS and kinds & FAMILY:
        return 'known for years'
    chance = 0.15 if 'new friend' in kinds else 0.3
    return 'friends' if generators.unit(pair, 'friends') < chance else None


def ties(rows: list[dict]) -> dict[str, list[dict]]:
    """Who each active member knows inside the circle: {person id: [{id, name, how}]}."""
    result = {row['id']: [] for row in rows}
    for index, first in enumerate(rows):
        for second in rows[index + 1:]:
            if how := tie(first, second):
                result[first['id']].append({'id': second['id'], 'name': second['name'], 'how': how})
                result[second['id']].append({'id': first['id'], 'name': first['name'], 'how': how})
    return result


def ties_text(known: list[dict]) -> str:
    """"Married to Rui. Knows Ana (family), Dev (coworkers).": for the chat context."""
    partners = [f"{'Divorced from' if item['how'] == 'divorced' else 'Married to'} {item['name']}."
                for item in known if item['how'] in ('married', 'divorced')]
    others = [f"{item['name']} ({item['how']})" for item in known if item['how'] not in ('married', 'divorced')]
    return ' '.join(partners + ([f"Knows {', '.join(others)}."] if others else []))
