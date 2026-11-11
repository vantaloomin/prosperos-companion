"""Friends of friends: the people around the companion's circle, a few layers out.

Everyone in the circle has their own people (a partner, friends, coworkers, a sibling, a roommate),
and each of those has theirs, down to MAX_DEPTH layers from the companion. Nobody out there is
stored or simulated: a person is a seeded path from a circle member (`circle:<timeline>:<n>/2/0`),
built the same way every time it is asked for, with an era-fitting name from the world data
(companion/world/naming.py). Most of them never come up.

They come up at gatherings and run-ins. A free circle friend now and then hosts something on a
Friday or Saturday evening (a Friendsgiving in November, a summer barbecue, game night), and the
companion goes when free: they meet a few of the host's people, sometimes one of theirs too. Who
they met is saved as an acquaintance with how they know them ("Jordan Lee, Becca's coworker, met
at Becca's Friendsgiving"), counted once the evening has happened. Later the companion may run
into one of them around town. The chat context lists recent acquaintances, so the companion can
say "you're Jordan from Becca's Friendsgiving!" No model is involved.
"""
from datetime import date

from companion.clock import parse, stamp
from companion.database import decode, encode, many, optional
from companion.life import circle, composer
from companion.world import generators, newcomers, ships

MAX_DEPTH = 4
SIZE = (4, 7)
FAMILY = {'parent', 'mom', 'dad', 'sibling', 'sister', 'brother', 'cousin'}
# (relation, weight, age spread either side, shares their family name)
RELATIONS = (('friend', 30, 5, False), ('coworker', 18, 12, False), ('sibling', 10, 6, True),
             ('roommate', 8, 4, False), ('neighbor', 7, 15, False), ('old friend', 12, 3, False),
             ('cousin', 6, 10, True), ('ex', 3, 4, False), ('gym buddy', 6, 8, False))
PARTNER_SHARE = 0.45
PARTNERS = ('partner', 'girlfriend', 'boyfriend')
# Someone's partner by the state of their love life (companion/life/circle_love.py), and an ex by how far they got.
LOVE_WORDS = {'seeing': {'she/her': 'girlfriend', 'he/him': 'boyfriend'},
              'engaged': {'she/her': 'fiancée', 'he/him': 'fiancé', '': 'fiancé'},
              'married': {'she/her': 'wife', 'he/him': 'husband', '': 'spouse'},
              'separated': {'she/her': 'wife', 'he/him': 'husband', '': 'spouse'}}
EX_WORDS = {False: {'she/her': 'ex-girlfriend', 'he/him': 'ex-boyfriend'}, True: {'she/her': 'ex-wife', 'he/him': 'ex-husband'}}
# A partner's partner is the person we came from, whatever the word for them.
TAKEN = {*PARTNERS, 'fiancée', 'fiancé', 'wife', 'husband', 'spouse'}
WORDS = {('sibling', 'she/her'): 'sister', ('sibling', 'he/him'): 'brother', ('partner', 'she/her'): 'girlfriend',
         ('partner', 'he/him'): 'boyfriend'}
# Gatherings a circle friend hosts: (key, wording, months or None for any).
OCCASIONS = (('friendsgiving', "{host}'s Friendsgiving", {11}), ('barbecue', "{host}'s barbecue", {5, 6, 7, 8, 9}),
             ('holiday-party', "{host}'s holiday party", {12}), ('game-night', "game night at {host}'s", None),
             ('dinner-party', "a dinner party at {host}'s", None), ('housewarming', "{host}'s housewarming", None),
             ('drinks', "drinks for {host}'s promotion", None))
HOST_CHANCE = 0.025
EVENING = '16:00'
GATHERING_KINDS = {'leisure', 'social'}
RUN_IN_KINDS = {'leisure', 'errand', 'social'}
RUN_IN_CHANCE = 0.05
ACTIVE = True
CONTEXT_LIMIT = 6
POSTS = ('Full house tonight.', 'Met some good people.', 'Hosting done right.', 'New faces, good food.')


# People ------------------------------------------------------------------------------------------

def root(row: dict, love: dict | None = None, voice: str = '') -> dict:
    """A circle member as the first layer: what their people are built around. `love` is their love life of record
    (circle_love.state), which decides who their partner and exes are among their people."""
    details = decode(row['details']) if isinstance(row['details'], str) else row['details']
    full = details.get('full_name') or row['name']
    return {'key': row['seed'], 'name': row['name'], 'full': full, 'family': full.split()[-1] if ' ' in full else '',
            'age': details.get('age') or 33, 'depth': 1, 'how': row['name'], 'circle_id': row['id'],
            'pronouns': details.get('pronouns', ''), 'love': love, 'voice': voice}


def rooted(connection, row: dict, people: list[dict] | None = None) -> dict:
    """root, with their love life of record and the city's words."""
    from companion.life import circle_love
    rows = people if people is not None else circle.people(connection, row['timeline_id'])
    return root(row, circle_love.state(connection, row, rows), circle.voice_of(connection, row['timeline_id']))


def relation_word(relation: str, pronouns: str) -> str:
    return WORDS.get((relation, pronouns), relation)


def their_people(parent: dict, data: dict, taken=frozenset()) -> list[dict]:
    """A person's own people, the same every time for the same parent and city."""
    if parent['depth'] >= MAX_DEPTH:
        return []
    seed = f"{parent['key']}:people"
    count = SIZE[0] + int(generators.unit(seed, 'count') * (SIZE[1] - SIZE[0] + 1))
    result, used = [], set(taken) | {parent['name']}
    for index in range(count):
        key = f"{parent['key']}/{index}"
        relation, spread, related = choose_relation(key, index, parent.get('relation'))
        age = max(18, parent['age'] + round((generators.unit(key, 'age') * 2 - 1) * spread))
        person = named(data, key, age, parent['family'] if related else None, used, parent['family'])
        word = relation_word(relation, person['pronouns'])
        used.add(person['given'])
        short = f"{parent['name']}'s {word}"
        how = short if parent['depth'] == 1 else f"{short} ({parent['name']} is {parent['short']})"
        result.append({'key': key, 'name': person['given'], 'full': person['full'], 'family': person['family'],
                       'pronouns': person['pronouns'],
                       'age': age, 'relation': word, 'depth': parent['depth'] + 1, 'of': parent['name'],
                       'how': how, 'short': short, 'circle_id': parent['circle_id'],
                       'occupation': occupation(data, key, age, person['pronouns'])})
    if parent['depth'] == 1 and parent.get('love'):
        return with_love(parent, result, data, used)
    return result


# Their love life among their people -----------------------------------------------------------------------------

def love_word(state: str, pronouns: str, voice: str = '') -> str:
    words = LOVE_WORDS.get(state, LOVE_WORDS['seeing'])
    return circle.era_word(words.get(pronouns, words.get('', 'partner')), voice)


def ex_word(ex: dict, pronouns: str) -> str:
    return EX_WORDS[bool(ex.get('married'))].get(pronouns, 'ex')


def labelled(parent: dict, item: dict, word: str, **extra) -> dict:
    short = f"{parent['name']}'s {word}"
    return {**item, 'relation': word, 'short': short, 'how': short, **extra}


def relabel(parent: dict, key: str, relation: str, pronouns: str) -> tuple[str, bool] | None:
    """What one of a circle member's own people is to them now, by their love life of record: (word, ex), or None
    when it is what the seed says."""
    love = parent.get('love') or {}
    partner = love.get('partner') or {}
    if key == partner.get('key'):
        return love_word(love['state'], pronouns, parent.get('voice', '')), False
    ex = next((item for item in love.get('exes') or () if item.get('key') == key), None)
    if ex:
        return ex_word(ex, pronouns), True
    if relation in PARTNERS and love.get('decided') != 'seed':
        # Their seeded partner is not theirs: they keep their name and become someone else to them.
        options = [item for item in RELATIONS if not item[3] and item[0] != 'ex']
        word = generators.pick(key, 'instead', options, [item[1] for item in options])[0]
        return relation_word(word, pronouns), False
    return None


def with_love(parent: dict, people: list[dict], data: dict, used: set) -> list[dict]:
    """Their people with their love life of record: the partner first, by the word for where they are, the seeded
    partner who is not theirs as someone else, and exes last. A partner or ex who is in the circle (or the companion)
    is not listed again."""
    current, rest, past = [], [], []
    for item in people:
        found = relabel(parent, item['key'], item['relation'], item['pronouns'])
        if not found:
            rest.append(item)
            continue
        word, ex = found
        target = past if ex else current if item['key'] == ((parent['love'].get('partner') or {}).get('key')) else rest
        target.append(labelled(parent, item, word, **({'ex': True} if ex else {})))
    listed = {item['key'] for item in people}
    love = parent['love']
    partner = love.get('partner') or {}
    if partner.get('key') and partner['key'] not in listed and outside(partner):
        current.append(labelled(parent, made(parent, partner, data, used), love_word(
            love['state'], partner.get('pronouns', ''), parent.get('voice', ''))))
    for ex in love.get('exes') or ():
        if ex.get('key') and ex['key'] not in listed and outside(ex):
            person = made(parent, ex, data, used)
            past.append(labelled(parent, person, ex_word(ex, person['pronouns']), ex=True))
    return current + rest + past


def outside(person: dict) -> bool:
    """Not someone in the circle, and not the companion."""
    return not person.get('circle_id') and person.get('key') != 'companion'


def made(parent: dict, person: dict, data: dict, used: set) -> dict:
    """A partner or ex who is not one of their seeded people: as recorded, else named from their key."""
    key = person['key']
    age = max(18, parent['age'] + round((generators.unit(key, 'age') * 2 - 1) * 4))
    if person.get('name'):
        full = person.get('full') or person['name']
        named_ = {'given': person['name'], 'full': full, 'family': full.split()[-1] if ' ' in full else '',
                  'pronouns': person.get('pronouns') or ''}
    else:
        named_ = named(data, key, age, None, used, parent['family'])
    used.add(named_['given'])
    return {'key': key, 'name': named_['given'], 'full': named_['full'], 'family': named_['family'],
            'pronouns': named_['pronouns'], 'age': age, 'relation': '', 'depth': parent['depth'] + 1,
            'of': parent['name'], 'how': '', 'short': '', 'circle_id': parent['circle_id'],
            'occupation': occupation(data, key, age, named_['pronouns'])}


def choose_relation(key: str, index: int, parent_relation: str | None) -> tuple[str, int, bool]:
    # A partner's partner is the person we came from, so a partner gets no partner of their own.
    partner = parent_relation not in TAKEN and index == 0 and generators.unit(key, 'partner') < PARTNER_SHARE
    if partner:
        return 'partner', 4, False
    relation, _weight, spread, related = generators.pick(key, 'relation', list(RELATIONS),
                                                          [item[1] for item in RELATIONS])
    return relation, spread, related


def named(data: dict, key: str, age: int, family: str | None, used: set, theirs: str = '') -> dict:
    """An era-fitting name not already used around this person; only relatives share their family name."""
    for attempt in range(6):
        person = generators.name(data, seed=f'{key}:name:{attempt}' if attempt else key, family=family or None, age=age)
        if person['given'] not in used and (family or not theirs or person['family'] != theirs):
            return person
    return person


def occupation(data: dict, key: str, age: int, pronouns: str | None = None) -> str:
    if age >= generators.RETIRED_AT:
        return 'retired'
    # Weighted towards the city's own industries, like its townsfolk (generators.town_career), and in an era that
    # kept work by gender, the work of their side.
    career = generators.town_career(data, key, pronouns=pronouns, age=age) if data.get('places') else None
    return career['name'].lower() if career else ''


def city(connection, companion: dict) -> dict:
    """The companion's city, carrying the family names strangers there never have (generators.name)."""
    town = companion.get('town_seed') or ''
    return newcomers.city_for(connection, companion['version']['definition']) | {
        'kin': kin(connection, companion), 'town': town, 'you': you(connection, town), 'kept': kept(connection, town)}


def you(connection, town: str) -> str:
    """The townsperson the user became in this world (companion/worlds.py, Become a townsperson), when this town is
    theirs: they are the user here, so they are no longer one of the town's people."""
    row = optional(connection, 'SELECT townsfolk_key, town_seed FROM persona WHERE id=1')
    return row['townsfolk_key'] if row and row['townsfolk_key'] and row['town_seed'] == town else ''


def kept(connection, town: str) -> tuple[str, ...]:
    """The townsfolk in this town who became companions: they keep their spot in town for good, whoever else moves
    away (companion/world/turnover.py)."""
    return tuple(row['townsfolk_key'] for row in many(
        connection, "SELECT townsfolk_key FROM companions WHERE townsfolk_key IS NOT NULL AND townsfolk_key!='' "
        "AND COALESCE(town_seed, '')=? ORDER BY townsfolk_key", (town,)))


def kin(connection, companion: dict) -> list[str]:
    """The companion's family names and their relatives': only family shares them, unless a marriage explains it."""
    definition = companion['version']['definition']
    names = [newcomers.surname(definition.get('name', '')), circle.family_name(definition)]
    for row in circle.people(connection, companion['active_timeline_id'], include_removed=True):
        if circle.role_kind(row['role']) in FAMILY:
            details = decode(row['details'])
            names += [newcomers.surname(details.get('full_name') or ''), details.get('birth_family')]
    return sorted({name for name in names if name})


def find(connection, companion: dict, key: str) -> dict | None:
    """The person a key names, rebuilt by walking from their circle member, or None."""
    seed, *path = key.split('/')
    row = optional(connection, "SELECT * FROM circle_people WHERE timeline_id=? AND seed=? AND status='active'",
                   (companion['active_timeline_id'], seed))
    if not row or len(path) >= MAX_DEPTH:
        return None
    person, data, taken = rooted(connection, row), city(connection, companion), names_taken(connection, companion)
    for step in path:
        found = [item for item in their_people(person, data, taken) if item['key'] == f"{person['key']}/{step}"]
        if not found:
            return None
        person = found[0]
    return person


def names_taken(connection, companion: dict) -> set[str]:
    rows = circle.people(connection, companion['active_timeline_id'])
    return {row['name'] for row in rows} | {companion['version']['definition'].get('name', '')}


def people_of(connection, companion: dict, key: str) -> list[dict]:
    """Someone's people for the circle view, each marked when the companion has met them."""
    person = find(connection, companion, key)
    if person is None:
        return []
    met = {row['key']: row for row in acquaintances(connection, companion['active_timeline_id'], None)}
    return [{**item, 'met': met.get(item['key'], {}).get('occasion')}
            for item in their_people(person, city(connection, companion), names_taken(connection, companion))]


# Gatherings and run-ins ------------------------------------------------------------------------

def occasion_for(seed: str, day: date, aboard: bool = False) -> tuple[str, str]:
    """What a friend is hosting: now and then one for the time of year, except aboard a ship or station, which has
    no summer barbecues or Friendsgiving (companion/world/ships.py)."""
    fitting = [(key, text) for key, text, months in OCCASIONS if months is None or day.month in months and not aboard]
    seasonal = [(key, text) for key, text, months in OCCASIONS if months and day.month in months and not aboard]
    if seasonal and generators.unit(seed, 'seasonal') < 0.6:
        return generators.pick(seed, 'occasion', seasonal)
    return generators.pick(seed, 'occasion', fitting)


def host_for(connection, slot: dict, block: dict, company: list[dict], timeline_id: str) -> dict | None:
    """The circle row of a free friend (not family) hosting something this Friday or Saturday evening, if any."""
    day = date.fromisoformat(slot['local_date'])
    if not ACTIVE or block['kind'] not in GATHERING_KINDS or block['start'] < EVENING or day.weekday() not in (4, 5) \
            or block.get('sick_day'):
        return None
    for friend in company:
        if generators.unit(f"host:{timeline_id}:{friend['id']}:{slot['local_date']}") < HOST_CHANCE:
            row = optional(connection, 'SELECT * FROM circle_people WHERE id=?', (friend['id'],))
            if row and row['role'] not in FAMILY:
                return row
    return None


def gathering(connection, companion: dict, slot: dict, block: dict, company: list[dict], seed: str) -> dict | None:
    """The companion's evening at a friend's gathering, meeting a few of the host's people, or None."""
    timeline_id = companion['active_timeline_id']
    row = host_for(connection, slot, block, company, timeline_id)
    if not row:
        return None
    data, taken = city(connection, companion), names_taken(connection, companion)
    hosts = rooted(connection, row)
    guests = [person for person in their_people(hosts, data, taken) if not person.get('ex')]
    if not guests:
        return None
    picked = sorted(guests, key=lambda item: generators.unit(seed, 'guest', item['key']))[:2 + int(
        generators.unit(seed, 'guests') * 2)]
    if picked and generators.unit(seed, 'further') < 0.5:
        further = their_people(picked[0], data, taken)
        if further:
            picked.append(generators.pick(seed, 'further-guest', further))
    _key, text = occasion_for(seed, date.fromisoformat(slot['local_date']), ships.enclosed(data))
    occasion = text.format(host=row['name'])
    for person in picked:
        meet(connection, timeline_id, person, slot, occasion)
    name = companion['version']['definition']['name']
    met = ', '.join(f"{person['full']} ({person['how']})" for person in picked[:-1])
    met = f"{met} and {picked[-1]['full']} ({picked[-1]['how']})" if len(picked) > 1 else \
        f"{picked[0]['full']} ({picked[0]['how']})"
    return {'summary': f'{name} went to {occasion} and met {met}.', 'post': generators.pick(seed, 'post', list(POSTS)),
            'mood': 'social', 'activity': 'gathering', 'place': None, 'with': {'id': row['id'], 'name': row['name']},
            'weather': block.get('weather'), 'composer_version': composer.COMPOSER_VERSION,
            'gathering': {'occasion': occasion, 'met': [p['key'] for p in picked]}}


def meet(connection, timeline_id: str, person: dict, slot: dict, occasion: str):
    """Remember a meeting; acquaintances() keeps the first that is still on the agenda."""
    snapshot = {key: person[key] for key in ('name', 'full', 'pronouns', 'age', 'relation', 'how', 'of', 'occupation')}
    connection.execute('INSERT OR REPLACE INTO acquaintances (timeline_id, key, person, slot_key, occasion, met_on, '
                       'met_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                       (timeline_id, person['key'], encode(snapshot), slot['key'], occasion, slot['local_date'],
                        slot['ends_at']))


def run_in(connection, timeline_id: str, entry: dict | None, slot: dict, block: dict, seed: str) -> dict | None:
    """Now and then, out somewhere, the companion runs into someone they met before."""
    if not ACTIVE or not entry or not entry.get('place') or block['kind'] not in RUN_IN_KINDS \
            or generators.unit(seed, 'run-in') >= RUN_IN_CHANCE:
        return entry
    known = [row for row in acquaintances(connection, timeline_id, None) if row['met_at'] < slot['starts_at']]
    if not known:
        return entry
    person = generators.pick(seed, 'run-in-who', known)
    told = f"Ran into {person['full']} ({person['how']}, from {person['occasion']}) there."
    return {**entry, 'summary': f"{entry['summary']} {told}", 'ran_into': person['key']}


# Who the companion has met ---------------------------------------------------------------------------

def acquaintances(connection, timeline_id: str, now) -> list[dict]:
    """People met through others, newest first: once the evening has happened when `now` is given, else
    every meeting on the agenda (for run-ins being planned)."""
    happened = "AND agenda.status='happened' AND acquaintances.met_at<=? " if now is not None else ''
    rows = many(connection, 'SELECT acquaintances.*, agenda.entry FROM acquaintances JOIN life_agenda agenda ON '
                'agenda.timeline_id=acquaintances.timeline_id AND agenda.slot_key=acquaintances.slot_key AND '
                f"agenda.subject='companion' WHERE acquaintances.timeline_id=? {happened}"
                'ORDER BY acquaintances.met_at', (timeline_id, *([stamp(now)] if now is not None else [])))
    members = circle.people(connection, timeline_id)
    active = {row['seed'] for row in members}
    first = {}
    for row in rows:
        # A meeting counts while its evening is still a gathering where they met (a rebuilt day may differ).
        met = ((decode(row['entry']) or {}).get('gathering') or {}).get('met', []) if row['entry'] else []
        if row['key'] in met and row['key'].split('/')[0] in active and row['key'] not in first:
            first[row['key']] = {**decode(row['person']), 'key': row['key'], 'occasion': row['occasion'],
                                 'met_on': row['met_on'], 'met_at': row['met_at']}
    return sorted(refreshed(connection, list(first.values()), members), key=lambda person: person['met_at'], reverse=True)


def refreshed(connection, people: list[dict], rows: list[dict]) -> list[dict]:
    """People met through a circle member, with what they are to that member now: "Kaito's ex-girlfriend" once they
    broke up, though the evening they met she was his girlfriend."""
    by_seed, roots = {row['seed']: row for row in rows}, {}
    result = []
    for person in people:
        seed, *path = person['key'].split('/')
        if len(path) != 1 or seed not in by_seed:
            result.append(person)
            continue
        if seed not in roots:
            roots[seed] = rooted(connection, by_seed[seed], rows)
        found = relabel(roots[seed], person['key'], person.get('relation') or '', person.get('pronouns') or '')
        result.append(labelled(roots[seed], person, found[0], **({'ex': True} if found[1] else {})) if found else person)
    return result


def text(person: dict) -> str:
    when = parse(person['met_at']).strftime('%d %B').lstrip('0')
    job = f", {person['occupation']}" if person.get('occupation') else ''
    return f"- {person['full']}, {person['how']}{job}: you met at {person['occasion']} on {when}."


def context_lines(connection, timeline_id: str, now) -> list[tuple[str, str]]:
    return [(person['key'], text(person)) for person in acquaintances(connection, timeline_id, now)[:CONTEXT_LIMIT]]


def copy(connection, parent_id: str, new_id: str, cutoff: str):
    """A fork keeps the people met before it."""
    for row in many(connection, 'SELECT * FROM acquaintances WHERE timeline_id=? AND met_at<=?', (parent_id, cutoff)):
        connection.execute('INSERT OR IGNORE INTO acquaintances (timeline_id, key, person, slot_key, occasion, met_on, '
                           'met_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                           (new_id, row['key'], row['person'], row['slot_key'], row['occasion'], row['met_on'],
                            row['met_at']))
