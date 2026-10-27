"""The people of a companion's family plan (companion/life/family_tree.py) as circle members (companion/life/circle.py).

Parents and full siblings carry the family's name; a stepparent and their own child have a name of their own; a
half sibling has the name of the parent they share when that is their father, else their stepfather's. Each keeps
its place in the plan under `kin` ({id, ties}), so who is married to or divorced from whom (circle.tie) and the
family line in chat (family_tree.context_lines) follow the plan. Someone who died before now is late (Remembered,
no funeral: `long_ago` holds the companion's age then); someone they no longer talk to is removed and `estranged`.
"""
from datetime import date

from companion.clock import stamp
from companion.database import decode, encode, one
from companion.life import family_tree
from companion.world import generators, naming

SHORT = {'she/her': 'she', 'he/him': 'he', 'they/them': 'they'}
WORDS = {('parent', 'step'): ('stepmom', 'stepdad', 'stepparent'),
         ('sibling', 'half'): ('half sister', 'half brother', 'half sibling'),
         ('sibling', 'step'): ('stepsister', 'stepbrother', 'stepsibling')}
LOCAL = 0.6  # As circle relatives: most live in town.


def role_word(item: dict) -> str | None:
    """'stepdad' or 'half sister'; None for a parent or a full sibling, whom circle.relation names."""
    words = WORDS.get((item['role'], 'step' if item['step'] else item.get('kind', 'full')))
    if not words:
        return None
    return words[{'she/her': 0, 'he/him': 1}.get(item['pronouns'], 2)]


def ties(tree: dict, item: dict) -> dict[str, str]:
    """Whom in the plan this person is married to or parted from."""
    found = {item['partner']: item['how']} if item.get('partner') else {}
    if item.get('remarried'):
        found[item['remarried']] = 'married'
    return found


def surname(item: dict, by_id: dict, family: str, names: dict[str, str]) -> str | None:
    """The family name they carry: None for a stepparent or a stepparent's child (a name of their own)."""
    if item['step'] or item.get('kind') == 'step':
        return None
    if item.get('kind') == 'half' and by_id[item['via']]['pronouns'] == 'she/her':
        return names.get(item['with'])
    return family


def member(item: dict, ctx: dict, family: str | None) -> dict:
    """One resident for the plan's person, named for their pronouns."""
    seed = f"{ctx['base']}:kin:{item['id']}"
    age = ctx['life'] + item['offset'] if item['role'] == 'sibling' else None
    local = generators.unit(seed, 'local') < LOCAL
    return generators.resident(ctx['data'], seed=seed, role=item['role'], age=age, around_age=ctx['life'],
                               local=local, near=ctx['home'], family=family, group=ctx['group'] if family else None,
                               folk=ctx['folk'], named_as=SHORT.get(item['pronouns']))


def gone(item: dict, tree: dict, details: dict) -> tuple[str, dict]:
    """(status, details) for someone who died before now or whom they don't talk to."""
    if item['died_at'] is not None:
        years = max(1, tree['age'] - item['died_at'])
        today = date.fromisoformat(tree['today'])
        on = date(today.year - years, 1 + int(generators.unit(item['id'], tree['today'], 'month') * 12), 15)
        age = details.get('age')
        return 'removed', details | {'late': on.isoformat(), 'long_ago': item['died_at'],
                                     **({'age': max(1, age - years), 'age_now': age} if age else {})}
    if item['estranged']:
        return 'removed', details | {'estranged': True}
    return 'active', details


def people(tree: dict, ctx: dict, make) -> list[dict]:
    """Everyone in the plan as circle entries, parents first. `make(member, role)` is circle.city_person."""
    by_id, names, made = {item['id']: item for item in tree['people']}, {}, []
    for item in sorted(tree['people'], key=lambda one: (one['role'] != 'parent', one['step'])):
        family = surname(item, by_id, ctx['family'], names)
        resident = member(item, ctx, family)
        names[item['id']] = naming.base_family(resident['name'].get('culture'), resident['name']['family']) \
            if resident['name'].get('family') else ''
        entry = make(resident, role_word(item))
        status, details = gone(item, tree, entry['details'] | {'kin': {'id': item['id'], 'ties': ties(tree, item)}})
        made.append(entry | {'details': details, 'status': status})
    return made


def in_touch(entries: list[dict]) -> int:
    return sum(entry.get('status', 'active') == 'active' for entry in entries)


def plan_for(definition: dict, data: dict, timeline_id: str, life: int | None, level: int, today: date) -> dict:
    """The family plan for a new circle, with the parents and siblings the sheet names taken into account."""
    from companion.life import named
    sheet = named.in_circle(definition)
    parents = tuple(person['pronouns'] for person in sheet if person['kind'] == 'parent' and person['pronouns'])
    siblings = sum(person['kind'] == 'sibling' for person in sheet)
    tree = family_tree.plan(definition, data, f'family:{timeline_id}', life, level, parents, siblings)
    return tree | {'today': today.isoformat()}


GONE = ('late', 'long_ago', 'estranged', 'age_now')


def welcome_back(connection, person_id: str, now) -> None:
    """Someone of the plan the user restores: alive and in touch again, at the age they would be now."""
    details = decode(one(connection, 'SELECT details FROM circle_people WHERE id=?', (person_id,))['details'])
    if not details or not any(key in details for key in GONE):
        return
    kept = {key: value for key, value in details.items() if key not in GONE}
    if 'age_now' in details:
        kept['age'] = details['age_now']
    connection.execute('UPDATE circle_people SET details=?, revision=revision+1, updated_at=? WHERE id=?',
                       (encode(kept), stamp(now), person_id))
