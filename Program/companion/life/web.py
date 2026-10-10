"""Who knows who (Hit List #44): everyone in the world the user has met or heard about, and how they are tied.

Nothing here is stored or asked of a model. The web is read from what the app already keeps: the companions
and their ties to each other (companion/memory/pairs.py), each companion's circle and how its members know
each other (companion/life/circle.py), people met through them (companion/life/network.py), townsfolk met
around town (companion/life/encounters.py), the people the user has told a companion about
(companion/memory/people.py), Matchlight matches (companion/dating.py) and people the user met in Story mode
(companion/story_people.py). Secrets, closeness and moods are left out, so the web shows only who knows who.

A node is {id, name, kind, detail, hood, companion_id?, main?}; a link is {source, target, label, kind}.
Townsfolk and network people keep their keys as ids, so someone two companions met is one node.
"""
from companion.database import many
from companion.errors import DomainError
from companion.life import circle, encounters, network
from companion.memory import pairs

YOU = 'you'
# How a relation word reads as a kind of tie, for the web's line styles and filters.
KINDS = {'family': {'mom', 'dad', 'parent', 'sister', 'brother', 'sibling', 'cousin', 'family', 'married', 'divorced',
                    'aunt', 'uncle', 'grandma', 'grandpa', 'son', 'daughter', 'mum', 'father', 'mother'},
         'partner': {'partner', 'girlfriend', 'boyfriend', 'husband', 'wife', 'spouse', 'match'},
         'work': {'coworker', 'coworkers', 'boss', 'colleague'},
         'neighbor': {'neighbor', 'roommate', 'roommate from years ago'},
         'ex': {'ex'}}


def kind_of(label: str) -> str:
    words = label.lower().replace('-', ' ')
    for kind, names in KINDS.items():
        if words in names or any(word in names for word in words.split()):
            return kind
    return 'friend' if 'friend' in words or 'buddy' in words else 'met'


class Web:
    """Nodes by id and links by unordered pair; a second link between the same two people is dropped."""

    def __init__(self):
        self.nodes: dict[str, dict] = {}
        self.links: dict[tuple[str, str], dict] = {}

    def add(self, node_id: str, name: str, kind: str, detail: str = '', hood: str = '', **extra):
        if node_id not in self.nodes:
            self.nodes[node_id] = {'id': node_id, 'name': name, 'kind': kind, 'detail': detail, 'hood': hood, **extra}

    def link(self, a: str, b: str, label: str, kind: str | None = None):
        pair = tuple(sorted((a, b)))
        if a != b and a in self.nodes and b in self.nodes and pair not in self.links:
            self.links[pair] = {'source': a, 'target': b, 'label': label, 'kind': kind or kind_of(label)}

    def view(self) -> dict:
        return {'nodes': list(self.nodes.values()), 'links': list(self.links.values())}


def companions(connection) -> list[dict]:
    from companion.characters import by_id
    rows = many(connection, 'SELECT id FROM companions WHERE active_version_id IS NOT NULL '
                'ORDER BY slot IS NULL, stepped_back_at DESC')
    return [found for row in rows if (found := by_id(connection, row['id']))]


def build(connection, now, story_on: bool = False) -> dict:
    web = Web()
    persona = connection.execute('SELECT name FROM persona WHERE id=1').fetchone()
    web.add(YOU, (persona and persona['name']) or 'You', 'you')
    cast = companions(connection)
    for companion in cast:
        key = pairs.companion_key(companion['id'])
        web.add(key, companion['version']['name'], 'companion', 'Your companion' if companion['slot'] == 1 else
                'Stepped back', companion_id=companion['id'], main=companion['slot'] == 1)
        web.link(YOU, key, 'your companion', 'you')
    for companion in cast:
        add_companion(connection, web, companion, now)
    add_yours(connection, web, cast, story_on)
    return web.view()


def add_companion(connection, web: Web, companion: dict, now):
    key = pairs.companion_key(companion['id'])
    for tie in pairs.ties(connection, companion, now):
        web.link(key, pairs.companion_key(tie['companion_id']), tie['how'] or 'know each other', 'friend')
    timeline_id = companion['active_timeline_id']
    add_circle(web, key, circle.people(connection, timeline_id))
    met = network.acquaintances(connection, timeline_id, now)
    # Everyone first, then the ties: newest come first, so a friend of a friend can be listed before the friend.
    for person in met:
        web.add(person['key'], person['full'], 'acquaintance', person.get('occupation') or '', '')
    for person in met:
        web.link(person['key'], person['key'].rsplit('/', 1)[0], person['relation'])
        web.link(key, person['key'], f"met at {person['occasion']}", 'met')
    add_townsfolk(web, key, encounters.known(connection, companion, now))


def add_circle(web: Web, key: str, rows: list[dict]):
    for row in rows:
        person = circle.view(row)
        web.add(person['key'], person.get('full_name') or person['name'], 'circle', person['role'])
        web.link(key, person['key'], person['role'])
    by_id = {row['id']: row['seed'] for row in rows}
    for person_id, known in circle.ties(rows).items():
        for other in known:
            web.link(by_id[person_id], by_id[other['id']], other['how'])


def add_townsfolk(web: Web, key: str, people: list[dict]):
    for person in people:
        if person['key'].startswith('cast:'):
            web.link(key, pairs.normal(person['key']), f"met at {person['place']['name']}", 'met')
            continue
        role = f"{person['role']} at {person['place']['name']}" if person['staff'] else person['role']
        web.add(person['key'], person['full'], 'townsperson', role, person['neighborhood'])
        web.link(key, person['key'], f"met at {person['first_place']}" if person.get('first_place') else 'met', 'met')
    staff = {}
    for person in people:
        if person['staff'] and not person['key'].startswith('cast:'):
            staff.setdefault(person['place']['id'], []).append(person)
    for together in staff.values():
        for index, first in enumerate(together):
            for second in together[index + 1:]:
                web.link(first['key'], second['key'], f"work at {first['place']['name']}", 'work')


def add_yours(connection, web: Web, cast: list[dict], story_on: bool):
    """The user's own people: those told to a companion, matches, and people met in Story mode."""
    seen = {}
    for companion in cast:
        for person in many(connection, 'SELECT * FROM user_people WHERE companion_id=? ORDER BY created_at, id',
                           (companion['id'],)):
            label = person['name'] or (person['relation'] or 'someone').capitalize()
            node_id = seen.setdefault((label.lower(), (person['relation'] or '').lower()), f"yours:{person['id']}")
            web.add(node_id, label, 'yours', person['relation'] or '')
            web.link(YOU, node_id, person['relation'] or 'someone you know')
    from companion import dating
    for row in many(connection, 'SELECT person_key, town FROM dating_swipes WHERE matched=1'):
        if companion_for(connection, row['person_key']):
            continue  # The match became a companion, who is already in the web.
        try:
            sheet, _data = dating.person(connection, row['person_key'], row['town'])
        except DomainError:
            continue  # Their city or place has gone.
        web.add(row['person_key'], sheet['full'], 'match', sheet.get('occupation') or sheet['role'])
        web.link(YOU, row['person_key'], 'match', 'partner')
    if story_on:
        for person in many(connection, 'SELECT key, name, meetings FROM story_people'):
            web.add(person['key'], person['name'], 'townsperson', 'Met in your story')
            web.link(YOU, person['key'], 'met in your story', 'met')


def companion_for(connection, key: str) -> str | None:
    row = connection.execute('SELECT id FROM companions WHERE townsfolk_key=?', (key,)).fetchone()
    return row and row['id']
