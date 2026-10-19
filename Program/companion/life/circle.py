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

from companion.clock import stamp, zone
from companion.database import decode, encode, identifier, many, one, optional
from companion.errors import require
from companion.life import ages, named
from companion.world import catalog, generators, lifespans, naming

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
FAMILY = {'parent', 'mom', 'dad', 'sibling', 'sister', 'brother', 'cousin', 'partner', 'wife', 'husband', 'girlfriend',
          'boyfriend', 'fiancée', 'fiancé', 'son', 'daughter', 'aunt', 'uncle', 'grandmother', 'grandfather',
          'grandparent'}
GRANDPARENTS = {'grandparent', 'grandmother', 'grandfather', 'grandma', 'grandpa'}
# A companion younger than this has a grandparent in their circle, aged ELDER_AGES (v0.15: so People can pass away
# finds someone old). They come on top of the circle's size.
GRANDCHILD_UNDER = 40
ELDER_AGES = (75, 95)
ELDERS = True
# Parents in the circle who parted: a quarter today, this share in an older city, where it reads "separated".
OLDER_PARTED = 0.04
PARTED = {'divorced': 'Divorced from', 'separated': 'Separated from'}
COUPLED = ('married', *PARTED)
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
    if data:
        # Weighted towards the city's own industries, like its townsfolk.
        career = generators.town_career(data, seed)
        career_id = career['id']
        job = generators.job(data, career_id, seed=seed)
        details = {'career': career['name'], 'employer': job['employer']['name'],
                   'neighborhood': job['neighborhood']['name'], 'city': data['name'],
                   'refs': job['refs'], 'sources': job['sources'], 'data_version': job['data_version']}
        schedule = job['schedule']
    else:
        offered = {key: career for key, career in catalog.everyday(catalog.careers()).items() if 'modern' in career['eras']}
        career_id = generators.pick(seed, 'career', sorted(offered))
        career = offered[career_id]
        details = {'career': career['name'], 'employer': '', 'neighborhood': '', 'city': '', 'refs': [],
                   'sources': [], 'data_version': ''}
        schedule = generators.schedule(career, seed)
    return {'name': name, 'role': role, 'career': career_id, 'details': details, 'schedule': schedule}


def from_city(data: dict, definition: dict, timeline_id: str, size: int = CIRCLE_SIZE, seed: str | None = None,
              taken: set[str] | None = None, sheet: bool = True) -> list[dict]:
    """The circle from the world data's generator, closest first, living near the companion when
    their location names a neighborhood. A circle bigger than the usual one fills in sociably. With `sheet`, the
    people the character sheet names take their places (with_named)."""
    match = catalog.resolve(definition.get('location') or '')
    hoods = {hood['id'] for hood in data['neighborhoods']}
    home = match['neighborhood'] if match and match['neighborhood'] in hoods else None
    social = size > CIRCLE_SIZE
    order = generators.SOCIAL if social else generators.CIRCLE
    works = social and bool(work_blocks(definition))
    family, base = family_name(definition), seed or f'circle:{timeline_id}'
    group = family_group(data, family)
    folk = lifespans.sheet_kind(definition, data)  # Their relatives are their kind (companion/world/lifespans.py).
    made = generators.circle(data, seed=base, size=min(size, len(order)), home=home, order=order, coworkers=works,
                             family=family, group=group, folk=folk)
    sheet_people = named.in_circle(definition) if sheet else []
    taken = set(taken or ()) | {definition['name'], *definition['name'].split()[:1]} | \
        {person['name'].split()[0] for person in named.people(definition)}  # Their children's names too.
    result = [city_person(member, data, definition, family, timeline_id, taken) for member in made['people']]

    def make(index, person):
        role = person['generator_role']
        related = role in ('parent', 'sibling', 'cousin')
        member = generators.resident(data, seed=f'{base}:named:{index}', role=role, local=person['local'],
                                     near=home if role in ('neighbor', 'parent', 'sibling') else None,
                                     family=family if related else None, group=group if related else None,
                                     folk=folk if related else None)
        pronouns = person['pronouns'] or 'they/them'
        given = person['name'].split()[0]
        full = person['name'] if ' ' in person['name'] else given
        member['name'] = {**member['name'], 'given': given, 'full': full, 'pronouns': pronouns}
        made = city_person(member, data, definition, family, timeline_id, set(), named_role(person))
        return made | {'details': made['details'] | {'sheet': person['name']}}
    return with_named(result, sheet_people, make)


def city_person(member: dict, data: dict, definition: dict, family: str | None, timeline_id: str, taken: set[str],
                role: str | None = None) -> dict:
    """One generated city resident as a circle member; `role` is the sheet's own word for a named person."""
    job = member['job'] or {}
    details = {'career': (job.get('career') or {}).get('name', 'Retired' if member['local'] else ''),
               'employer': (job.get('employer') or {}).get('name', ''),
               'neighborhood': member['home']['neighborhood']['name'] if member['home'] else '',
               'city': data['name'] if member['local'] else '', 'full_name': member['name']['full'],
               'pronouns': member['name']['pronouns'], 'age': member['age'], 'local': member['local'],
               'closeness': member['closeness'], 'haunts': [spot['name'] for spot in member['haunts']],
               'refs': member.get('refs', []), 'sources': member.get('sources', []),
               'data_version': data['data_version']}
    if member.get('folk'):
        details['folk'] = member['folk']  # Not human (companion/world/lifespans.py).
    # Relatives carry the family name, unless the sheet gives a named one their full name.
    if family and member['role'] in ('parent', 'sibling') and (role is None or ' ' not in member['name']['full']):
        details['full_name'] = f"{member['name']['given']} {family_form(family, member['name']['pronouns'])}"
        if member['role'] == 'sibling' and role is None:
            # Married or not by their age in human terms (companion/world/lifespans.py).
            life = lifespans.life_age(member['age'], lifespans.lifespan_of(member.get('folk'), data))
            details |= married_sibling(data, timeline_id, member['name'], life, family)
    # Two people with the same first name go by their full names, so events stay unambiguous.
    shown = member['name']['given'] if member['name']['given'] not in taken else details['full_name']
    taken.add(shown)
    made_person = {'name': shown, 'role': role or relation(member['role'], member['name']['pronouns']),
                   'career': (job.get('career') or {}).get('id', ''), 'details': details,
                   'schedule': member['schedule'] or []}
    return colleague(made_person, definition) if member['role'] == 'coworker' else made_person


def named_role(person: dict) -> str:
    """How the circle lists someone the sheet names: mom or brother by their pronouns, else the sheet's word."""
    if person['kind'] in ('parent', 'sibling'):
        return relation(person['kind'], person['pronouns'])
    return person['role']


def with_named(built: list[dict], sheet_people: list[dict], make) -> list[dict]:
    """The circle with the people the sheet names (companion/life/named.py), each in place of a seeded person in
    the same role (mom for mom first) or added after them when nobody has it: the sheet's brother Tunde, never a
    seeded brother Darrell beside him. `make(index, person)` builds the named person's entry."""
    result, kept = list(built), set()
    for index, person in enumerate(sheet_people):
        entry = make(index, person)
        slots = named.SLOTS.get(person['kind'], ())
        open_slots = [at for at, row in enumerate(result) if at not in kept and row['role'] in slots]
        slot = next((at for at in open_slots if result[at]['role'] == entry['role']), open_slots[0] if open_slots else None)
        if slot is None:
            result.append(entry)
            kept.add(len(result) - 1)
        else:
            result[slot] = entry
            kept.add(slot)
    return result


def family_name(definition: dict) -> str | None:
    """The family name the companion's parents and siblings carry (in its listed form: Kowalski for Anna
    Kowalska): their own last name (from the sheet when their name is one word), or the birth name they give with
    "née"; None for a one-word name or a companion who has married without naming one."""
    text = ' '.join(definition.get(key) or '' for key in ('identity', 'background'))
    if match := BIRTH_NAME.search(text):
        return family_form(match.group(1), 'he/him')
    words = [word for word in (definition.get('name') or '').split() if word.casefold() not in SUFFIXES]
    # A one-word name the sheet spells out in full: "Dana Okafor is 34 and...".
    if len(words) == 1 and (full := re.search(rf"\b{re.escape(words[0])} ((?!(?:Is|Was|Has|And)\b)[A-Z][a-z'’-]+)\b",
                                               text)):
        words.append(full.group(1))
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
    chance = next((share for limit, share in MARRIED_BY_AGE if (age or 0) < limit), MARRIED_BY_AGE[-1][1])
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
    words = {'parent': ('mom', 'dad'), 'sibling': ('sister', 'brother'),
             'grandparent': ('grandmother', 'grandfather')}.get(role)
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


def view(row: dict, data: dict | None = None) -> dict:
    """One person for the page; `data`: the companion's city, whose own kinds and lifespans their kind reads."""
    details = decode(row['details'])
    return {'id': row['id'], 'key': row['seed'], 'name': row['name'], 'role': row['role'], 'status': row['status'],
            'revision': row['revision'], **details, 'birthday': birthday(row['id']),
            'schedule': decode(row['schedule']), 'kind': ages.person_kind(details, data)}


def build(definition: dict, world, timeline_id: str, size: int, seed: str | None = None, taken=(),
          sheet: bool = True) -> list[dict]:
    """`size` people, closest first, from the city's generator when the world knows their city, with the people
    the sheet names in their places (`sheet`; False for people added to a circle later)."""
    base = seed or f'circle:{timeline_id}'
    data = city_data(definition, world)
    if data:
        return from_city(data, definition, timeline_id, size, base, set(taken), sheet)
    names, roles, built = set(taken) | {definition['name']}, SOCIAL_ROLES if size > CIRCLE_SIZE else None, []
    for ordinal in range(min(size, len(SOCIAL_ROLES))):
        person = assemble(f'{base}:{ordinal}', ordinal, definition, None, names, roles[ordinal] if roles else None)
        built.append(colleague(person, definition) if roles and person['role'] == 'coworker' else person)
        names.add(person['name'])

    def make(index, person):
        made = assemble(f'{base}:named:{index}', len(built) + index, definition, None, set(), named_role(person))
        full = person['name'] if ' ' in person['name'] else ''
        made |= {'name': person['name'].split()[0],
                 'details': made['details'] | {'pronouns': person['pronouns'] or 'they/them', 'local': person['local'],
                                               'sheet': person['name']}
                 | ({'full_name': full} if full else {})}
        if not person['local']:
            made |= {'career': '', 'schedule': [], 'details': made['details'] | {'career': '', 'employer': ''}}
        return made
    return with_named(built, named.in_circle(definition) if sheet else [], make)


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
        changed = match_family(connection, companion, world, rows, now)
        changed = add_named(connection, companion, world, rows, now) or changed
        # A circle assembled smaller than it should now be (a bigger size in Settings, a more sociable
        # companion) fills itself. People the user removed still count, so nobody is replaced behind their back.
        if (missing := target_size(companion['version']['definition'], setting(connection)) - len(sized(rows))) > 0:
            fill(connection, companion, world, rows, now, missing)
            changed = True
        changed = add_grandparent(connection, companion, world, now) or changed
        if changed:
            rows = people(connection, timeline_id, include_removed=True)
        return [row for row in rows if row['status'] == 'active']
    definition = companion['version']['definition']
    insert(connection, timeline_id, build(definition, world, timeline_id, target_size(definition, setting(connection))),
           0, now)
    add_grandparent(connection, companion, world, now)
    from companion.life import kids  # A companion new to the user: their kids, maybe seeded, and the other parent.
    kids.settle(connection, companion, world, now, fresh=True)
    return people(connection, timeline_id)


def sized(rows: list[dict]) -> list[dict]:
    """The rows the circle's size counts: all but the grandparent added on top of it."""
    return [row for row in rows if not (decode(row['details']) or {}).get('elder')]


def add_grandparent(connection, companion: dict, world, now) -> bool:
    """A grandparent for a companion under GRANDCHILD_UNDER whose circle has none (counting anyone removed or late),
    added after everyone else. Their date and their days start now: nothing is written for them before they joined
    (circle created in an existing world on the next reconcile). True when one was added."""
    timeline_id, definition = companion['active_timeline_id'], companion['version']['definition']
    rows = people(connection, timeline_id, include_removed=True)
    today = now.astimezone(zone(companion['version']['timezone'])).date()
    age = ages.companion_life_age(connection, companion['id'], definition, today)  # In human terms.
    if not ELDERS or age is None or age >= GRANDCHILD_UNDER or any(role_kind(row['role']) in GRANDPARENTS for row in rows):
        return False
    elder = grandparent(definition, world, timeline_id, age, {row['name'] for row in rows})
    ordinal = max((row['ordinal'] for row in rows), default=-1) + 1
    insert(connection, timeline_id, [elder], ordinal, now)
    added = one(connection, 'SELECT id FROM circle_people WHERE timeline_id=? AND ordinal=?', (timeline_id, ordinal))
    connection.execute('INSERT OR IGNORE INTO agenda_cursors (timeline_id, subject, through) VALUES (?, ?, ?)',
                       (timeline_id, added['id'], stamp(now)))
    return True


def elder_resident(data: dict, seed: str, age: int, local: bool, family: str | None, firsts: set[str],
                   folk: str | None) -> dict:
    """A resident for the grandparent whose first name nobody in the circle has (a sibling and a grandmother both
    "Ayo Solano" read as one person), after a few tries."""
    for attempt in range(8):
        member = generators.resident(data, seed=seed if not attempt else f'{seed}:{attempt}', role='parent', age=age,
                                     local=local, family=family, group=family_group(data, family), folk=folk)
        if member['name']['given'] not in firsts:
            break
    return member


def grandparent(definition: dict, world, timeline_id: str, age: int, taken: set[str]) -> dict:
    """The seeded grandparent: retired, local or out of town, on the family's side about half the time."""
    seed = f'circle:{timeline_id}:grandparent'
    low = max(ELDER_AGES[0], age + 42)
    elder_age = low + round((generators.unit(seed, 'age-a') + generators.unit(seed, 'age-b')) / 2 * (ELDER_AGES[1] - low))
    local = generators.unit(seed, 'local') < 0.5
    data = city_data(definition, world)
    folk = lifespans.sheet_kind(definition, data)  # Ages here are in human terms; their real one follows their kind.
    if data:
        family = family_name(definition) if generators.unit(seed, 'family-side') < 0.5 else None
        member = elder_resident(data, seed, elder_age, local, family, {name.split()[0] for name in taken}, folk)
        made = city_person(member, data, definition, None, timeline_id, set(taken) | {definition['name']},
                           relation('grandparent', member['name']['pronouns']))
        return made | {'details': made['details'] | {'career': 'Retired', 'elder': True}}
    pronouns = generators.pick(seed, 'pronouns', ['she/her', 'he/him'])
    made = assemble(seed, 0, definition, None, set(taken) | {definition['name']}, relation('grandparent', pronouns))
    details = made['details'] | {'career': 'Retired', 'pronouns': pronouns, 'local': local, 'elder': True,
                                 'age': lifespans.real_age(elder_age, lifespans.lifespan_of(folk, data))}
    details |= {'folk': folk} if folk != lifespans.HUMAN else {}
    return made | {'career': '', 'details': details,
                   'schedule': generators.RETIRED_SCHEDULE if local else []}


def add_named(connection, companion: dict, world, rows: list[dict], now) -> bool:
    """People the sheet names whom a circle assembled earlier lacks (the sheet was edited, or the circle is from
    before sheets were read), added after everyone else. Nobody already there is renamed: a mom or dad the circle
    already has keeps their place, and someone the user renamed or removed counts as there. True when anyone was
    added."""
    definition, timeline_id = companion['version']['definition'], companion['active_timeline_id']
    there = {row['name'].split()[0] for row in rows} | {decode(row['details']).get('sheet') for row in rows}
    parents = {row['role'] for row in rows if row['status'] == 'active' and role_kind(row['role']) == 'parent'}
    missing = {person['name'] for person in named.in_circle(definition) if person['name'].split()[0] not in there
               and person['name'] not in there and not (person['kind'] == 'parent' and parents & {named_role(person),
                                                                                                    'parent'})}
    if not missing:
        return False
    built = build(definition, world, timeline_id, 1, f'circle:{timeline_id}:sheet', {row['name'] for row in rows})
    added = [person for person in built if person['details'].get('sheet') in missing]
    insert(connection, timeline_id, added, max(row['ordinal'] for row in rows) + 1, now)
    return bool(added)


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
                                      lifespans.life_age(details.get('age') or 0, lifespans.lifespan_of(details.get('folk'), data)),
                                      family)
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
    return {'mom': 'parent', 'dad': 'parent', 'mother': 'parent', 'father': 'parent', 'sister': 'sibling',
            'brother': 'sibling', 'old classmate': 'old friend from school', 'ex-wife': 'ex',
            'ex-husband': 'ex'}.get(role, role)


# In the old eras (London 1895, Camelot) people say mother and father, not mom and dad.
OLD_WORDS = {'mom': 'mother', 'dad': 'father'}


def said(role: str, definition: dict) -> str:
    """The role as the companion says it in their era: 'mom', or 'mother' in 1895."""
    from companion.world import perception
    return role if role not in OLD_WORDS or perception.era_modern(definition) else OLD_WORDS[role]


def room(connection, companion: dict) -> dict:
    """How many people the circle has and could have, for the "add people" offer. Someone who passed away still
    holds their place: a death is not a removal (companion/life/loss.py)."""
    definition = companion['version']['definition']
    active = len([row for row in sized(people(connection, companion['active_timeline_id'], include_removed=True))
                  if row['status'] == 'active' or (decode(row['details']) or {}).get('late')])
    return {'people': active, 'target': target_size(definition, setting(connection)),
            'sociability': sociability(definition)}


def grow(connection, companion: dict, world, now) -> list[dict]:
    """Add people to a circle smaller than it should be, filling the roles a sociable circle has and this
    one lacks (coworkers, old and new friends, family) before anyone else. Nobody already there changes. A bigger
    size in Settings is filled by `ensure` itself, which counts as growing."""
    before = len(people(connection, companion['active_timeline_id'], include_removed=True))
    ensure(connection, companion, world, now)
    rows = people(connection, companion['active_timeline_id'], include_removed=True)
    active = [row for row in sized(rows) if row['status'] == 'active' or (decode(row['details']) or {}).get('late')]
    missing = target_size(companion['version']['definition'], setting(connection)) - len(active)
    require(missing > 0 or len(rows) > before, 'Their circle already has everyone it should. Raise the circle size in '
            'Settings to add more people.', 409)
    if missing > 0:
        fill(connection, companion, world, rows, now, missing)
    return people(connection, companion['active_timeline_id'])


def fill(connection, companion: dict, world, rows: list[dict], now, count: int):
    """Add `count` people to the circle, the roles it lacks first."""
    timeline_id, definition = companion['active_timeline_id'], companion['version']['definition']
    active = [row for row in rows if row['status'] == 'active']
    want = target_size(definition, setting(connection))
    taken = {row['name'] for row in rows}
    candidates = build(definition, world, timeline_id, len(SOCIAL_ROLES), f'circle:{timeline_id}:more:{len(rows)}', taken,
                       sheet=False)
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
    insert(connection, timeline_id, chosen[:count], max(row['ordinal'] for row in rows) + 1, now)


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


def set_kind(connection, person_id, kind: str, lifespan: int | None, now, data: dict | None = None) -> dict:
    """The user's pick of someone's kind and How long they live ('' and None: the app's again; 0: they don't age).
    Their real age stays; the rules read their life age from it (companion/world/lifespans.py). `data`: the
    companion's city, which may have kinds of its own."""
    row = person(connection, person_id)
    require(not kind or kind in lifespans.kinds(data), 'Pick one of the kinds listed.', 422)
    details = {key: value for key, value in decode(row['details']).items() if key not in ('own_kind', 'lifespan')}
    details |= ({'own_kind': kind} if kind else {}) | ({'lifespan': lifespan} if lifespan is not None else {})
    connection.execute('UPDATE circle_people SET details=?, revision=revision+1, updated_at=? WHERE id=?',
                       (encode(details), stamp(now), person_id))
    return one(connection, 'SELECT * FROM circle_people WHERE id=?', (person_id,))


def set_status(connection, person_id, status: str, now) -> dict:
    """A removed person stops appearing in new entries; what already happened stays."""
    person(connection, person_id)
    connection.execute('UPDATE circle_people SET status=?, revision=revision+1, updated_at=? WHERE id=?',
                       (status, stamp(now), person_id))
    return one(connection, 'SELECT * FROM circle_people WHERE id=?', (person_id,))


def tie(first: dict, second: dict, older: bool = False) -> str | None:
    """How two circle members know each other, the same every time for the same two people. In an older city
    (before 1950) parents who parted are separated, and far fewer did (breakups.separated)."""
    kinds = {role_kind(first['role']), role_kind(second['role'])}
    pair = ':'.join(sorted((first['id'], second['id'])))
    if kinds == {'parent'}:
        parted = generators.unit(pair, 'divorced') < (OLDER_PARTED if older else 0.25)
        return ('separated' if older else 'divorced') if parted else 'married'
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


def ties(rows: list[dict], older: bool = False) -> dict[str, list[dict]]:
    """Who each active member knows inside the circle: {person id: [{id, name, how}]}."""
    result = {row['id']: [] for row in rows}
    for index, first in enumerate(rows):
        for second in rows[index + 1:]:
            if how := tie(first, second, older):
                result[first['id']].append({'id': second['id'], 'name': second['name'], 'how': how})
                result[second['id']].append({'id': first['id'], 'name': first['name'], 'how': how})
    return result


def ties_text(known: list[dict]) -> str:
    """"Married to Rui. Knows Ana (family), Dev (coworkers).": for the chat context."""
    partners = [f"{PARTED.get(item['how'], 'Married to')} {item['name']}." for item in known if item['how'] in COUPLED]
    others = [f"{item['name']} ({item['how']})" for item in known if item['how'] not in COUPLED]
    return ' '.join(partners + ([f"Knows {', '.join(others)}."] if others else []))


def city_of_timeline(connection, timeline_id: str) -> dict | None:
    """The city of the timeline's companion, None for a place the app doesn't know."""
    from companion.characters import by_id
    row = optional(connection, 'SELECT companion_id FROM timelines WHERE id=?', (timeline_id,))
    companion = row and by_id(connection, row['companion_id'])
    return ages.city_of(connection, companion['version']['definition']) if companion else None


def older_era(connection, timeline_id: str) -> bool:
    """The timeline's companion lives in an older city (before 1950), as breakups.separated reads it."""
    from companion.characters import by_id
    from companion.world import newcomers, townsfolk
    row = optional(connection, 'SELECT companion_id FROM timelines WHERE id=?', (timeline_id,))
    companion = row and by_id(connection, row['companion_id'])
    return bool(companion) and not townsfolk.modern(newcomers.city_for(connection, companion['version']['definition']))
