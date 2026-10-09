"""Secrets: who knows what, and who must not find out (docs/group-chat.md, "Secrets").

A small ledger (`knowledge`, `knowledge_holders`) records facts a companion could not have learned in their own
life, and who knows each one. A speaker's prompt gets a secret only when they are on its knowers list, so Sally's
prompt never holds Billy and Katie's secret in the first place: no model is trusted to keep one it was handed.

Where secrets come from, all by rules:
- The user declares one in the Secrets panel: what it is, who it's about, who knows and who must not find out.
- A storyline that is a secret registers itself once its first beat has happened (`STORY_SECRETS`): the companion
  who found out and the people in it know, and it is kept from everyone else.
- A line in a companion's own description that reads as a secret ("secretly", "nobody knows", "never told")
  registers as one only they know, kept from everyone else.

Rows point at their source rather than copying it: a storyline's text is filled with today's names, a character
line is re-read from the current sheet (edit the sheet and the secret follows; remove the line and it ends),
and a declared secret is the user's own words, edited in the panel. So a correction reaches the ledger.

How people come to know one (`via` on each holder row):
- origin: the people it started with.
- witness: said in a group while they were there (the group's `present` list), by anyone.
- slip: a knower said it in front of someone it was kept from, and slips were allowed.
- history: added to a group with everything so far, where it had been said.
- reveal: the user chose "Let them find out", or told them in a group while it was kept from them.

A knower's reply in a group where someone it's kept from is present is checked by rules (`hits`): it names every
person the secret is about (the speaker counts as named when it's about them) and enough of its key words. A hit
is redrafted once with a reminder; if the redraft still gives it away, it stays as a slip only at the "soap
opera" drama setting, and otherwise that reply is held back. Paraphrases get through; that is accepted because a
slip is shown and recorded, never silently undone.

A gossip passes a secret on only to someone they feel Close to (`spreads`, with memory/pairs.py).
"""
import hashlib
import re

from companion.characters import by_id
from companion.clock import parse, stamp
from companion.database import decode, encode, identifier, many, one, optional, settings
from companion.errors import require
from companion.life import circle, storylines
from companion.world import perception

PASS_ON = 'secret:pass_on'  # The consequence engine's table for a gossip passing a secret on.
SLIP_LEVEL = 3  # Drama "soap opera": a slip that survives the redraft stays and becomes a reveal.
STATEMENT_LIMIT = 400

# Storylines that are secrets. `statement` is filled like a storyline beat; `subjects` are template fields;
# `knowers` the cast who know from the start besides the companion; `ends` a beat that makes it public.
STORY_SECRETS = {
    'secret_couple': {
        'statement': '{a} and {b} have been secretly seeing each other',
        'subjects': ('a', 'b'), 'knowers': ('a', 'b'), 'ends': 'made it official',
        'keys': ('seeing each other', 'secretly seeing', 'dating', 'hooking up', 'hooked up', 'sleeping together',
                 'sleeping with', 'slept', 'affair', 'sneaking around', 'a thing', 'a couple', 'kissed', 'in love',
                 'secret'),
    },
    'family_secret': {
        'statement': '{name} has a half-sibling they never knew about',
        'subjects': ('name',), 'knowers': ('a',), 'ends': None,
        'keys': ('half-sibling', 'half sibling', 'half-brother', 'half brother', 'half-sister', 'half sister',
                 'secret sibling', 'another sibling'),
    },
}

# A sentence in a companion's own description that reads as a secret.
SECRET_LINE = re.compile(r"\bsecret(?:ly|s)?\b|\b(?:nobody|no one|no-one)(?: else)? knows\b|"
                         r"\b(?:hasn't|has not|haven't|have not|never) told\b|\bbehind (?:his|her|their) backs?\b",
                         re.IGNORECASE)
CHARACTER_FIELDS = ('identity', 'personality', 'background', 'history_together', 'sees_self')
SENTENCE = re.compile(r'(?<=[.!?])\s+|\n+')

STOP = set('''about above after again against all also although always among another any anyone anything around
because been before being below between both but cannot could does doing done down during each either else even
ever every everyone from further going gone had has have having here hers herself him himself his how into its
itself just know knows knew like made make many more most much must never nobody none nothing now off once only
other others our ours ourselves out over own really said same says she should since some someone something still
such than that the their theirs them themselves then there these they thing things this those though through told
too under until upon very was were what when where which while who whom whose why will with without would yet you
your yours yourself told tell tells telling everybody anybody secret secretly secrets'''.split())

# The same, when they remember who told them (`told_by`).
TOLD_TEXT = {'origin': 'from the start', 'witness': 'heard it from {teller} in a group',
             'slip': '{teller} let it slip in a group', 'history': 'read what {teller} said in a group',
             'reveal': '{teller} told them in a group'}
VIA_TEXT = {'origin': 'from the start', 'witness': 'heard it in a group', 'slip': 'it slipped out in a group',
            'history': 'read it in a group', 'reveal': 'you let them find out'}


# People ------------------------------------------------------------------------------------------------

def companion_key(companion_id: str) -> str:
    return f'companion:{companion_id}'


def circle_key(connection, person_id: str) -> str:
    """A circle person's key is their seed (circle:<timeline>:<n>), the one memory/pairs.py uses too."""
    row = optional(connection, 'SELECT seed FROM circle_people WHERE id=?', (person_id,))
    return row['seed'] if row else f'circle:{person_id}'


def person_name(connection, key: str | None) -> str | None:
    """A person key's current name: companions by their active version, circle people as named now."""
    if not key:
        return None
    kind, _, value = key.partition(':')
    if kind == 'companion':
        found = by_id(connection, value)
        return found['version']['name'] if found else None
    if kind == 'circle':
        row = optional(connection, 'SELECT name FROM circle_people WHERE seed=?', (key,))
        return row['name'] if row else None
    return None


def forms(name: str) -> set[str]:
    """How a person can be named in a message: in full, or by first name."""
    words = name.split()
    return {name, words[0]} if words else set()


def mentions(text: str, name: str) -> bool:
    return any(re.search(rf'(?<!\w){re.escape(form)}(?!\w)', text, re.IGNORECASE) for form in forms(name) if form)


def first_name(name: str) -> str:
    return name.split()[0] if name.split() else name


def names_text(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ', '.join(names[:-1]) + f' and {names[-1]}'


# Key words ---------------------------------------------------------------------------------------------

def derived_keys(statement: str, subjects: list[dict]) -> list[str]:
    """Key words from the statement itself: its content words, without the names it is about."""
    names = {form.casefold() for subject in subjects for form in forms(subject['name'])}
    words = re.findall(r"[a-z][a-z'-]+", statement.casefold())
    return list(dict.fromkeys(word for word in words
                              if len(word) >= 4 and word not in STOP and word not in names))


def has_key(text: str, key: str) -> bool:
    """A key word or phrase in the text; a single longer word also matches with an ending ("secret", "secretly")."""
    tail = r'\w*' if ' ' not in key and len(key) >= 4 else r'(?!\w)'
    return re.search(rf'(?<!\w){re.escape(key)}{tail}', text, re.IGNORECASE) is not None


def hits(secret: dict, text: str, author: str | None = None) -> bool:
    """Whether a message gives the secret away: it names everyone the secret is about (the author counts as named
    when it is about them) and enough of its key words: one of the user's own or a storyline's, or, for key words
    taken from the statement, one when it names two or more people and two otherwise."""
    if not text or not secret['keys']:
        return False
    for subject in secret['subjects']:
        if not (subject.get('key') and subject['key'] == author) and not mentions(text, subject['name']):
            return False
    found = {key.casefold() for key in secret['keys'] if has_key(text, key)}
    return len(found) >= (1 if secret['explicit'] or len(secret['subjects']) > 1 else 2)


# Reading the ledger ------------------------------------------------------------------------------------

def holders(connection, knowledge_id: str) -> list[dict]:
    return many(connection, 'SELECT * FROM knowledge_holders WHERE knowledge_id=? AND ended_at IS NULL '
                'ORDER BY learned_at, rowid', (knowledge_id,))


def story_parts(connection, row: dict) -> dict | None:
    """A storyline secret's statement and subjects, filled with today's names; None once the storyline is gone."""
    story = optional(connection, 'SELECT * FROM storylines WHERE id=?', (row['source_id'],))
    if story is None:
        return None
    companion = optional(connection, 'SELECT id FROM companions WHERE active_timeline_id=?', (story['timeline_id'],))
    found = by_id(connection, companion['id']) if companion else None
    if found is None:
        return None
    rule = STORY_SECRETS[story['story']]
    definition = found['version']['definition']
    names = {person['id']: {'name': person['name'], 'role': person['role']}
             for person in circle.people(connection, story['timeline_id'], include_removed=True)}
    cast = decode(story['cast_ids'])
    keys = {'name': companion_key(found['id'])} | {
        field: circle_key(connection, person_id) for field, person_id in zip(('a', 'b'), cast)}
    subjects = []
    for field in rule['subjects']:
        key = keys.get(field)
        subjects.append({'key': key, 'name': person_name(connection, key) or 'someone'})
    return {'statement': storylines.fill(rule['statement'], story, names, definition), 'subjects': subjects,
            'keys': list(rule['keys']), 'explicit': True}


def character_parts(connection, row: dict) -> dict | None:
    """A secret line from a companion's description, read from the current sheet; None once it's not there."""
    companion_id, _, digest = row['source_id'].partition(':')
    found = by_id(connection, companion_id)
    if found is None:
        return None
    line = character_lines(found['version']['definition']).get(digest)
    if line is None:
        return None
    subjects = [{'key': companion_key(companion_id), 'name': found['version']['name']}]
    return {'statement': line, 'subjects': subjects, 'keys': derived_keys(line, subjects), 'explicit': False}


def memory_text(memory: dict) -> str:
    value = ' '.join(memory['value'].split())
    text = value if SECRET_LINE.search(value) else f"{' '.join(memory['subject'].split())}: {value}"
    return text[:STATEMENT_LIMIT].rstrip('.')


def memory_parts(connection, row: dict) -> dict | None:
    """A memory that reads like a secret, read from the memory itself; None once it's corrected, excluded or gone."""
    memory = optional(connection, "SELECT subject, value FROM memories WHERE id=? AND status='active'",
                      (row['source_id'],))
    if memory is None:
        return None
    statement = memory_text(memory)
    return {'statement': statement, 'subjects': [], 'keys': derived_keys(statement, []), 'explicit': False}


def declared_parts(connection, row: dict) -> dict:
    subjects = [{'key': item.get('key'), 'name': person_name(connection, item.get('key')) or item['name']}
                for item in decode(row['subjects']) or []]
    return {'statement': row['statement'], 'subjects': subjects,
            'keys': derived_keys(row['statement'], subjects), 'explicit': False}


def view(connection, row: dict) -> dict | None:
    """One secret as the rules and the panel use it, or None when its source is gone."""
    parts = PARTS[row['kind']](connection, row)
    if parts is None:
        return None
    own_keys = decode(row['key_words'])
    if own_keys:
        parts |= {'keys': own_keys, 'explicit': True}
    rows = holders(connection, row['id'])
    knows = [holder for holder in rows if holder['role'] == 'knows']
    return {**parts, 'id': row['id'], 'kind': row['kind'], 'source_id': row['source_id'], 'status': row['status'],
            'guard_all': bool(row['guard_all']), 'own_keys': own_keys or [], 'created_at': row['created_at'],
            'knows': knows, 'knowers': {holder['holder'] for holder in knows},
            'guarded': {holder['holder'] for holder in rows if holder['role'] == 'guarded'}}


PARTS = {'storyline': story_parts, 'character': character_parts, 'memory': memory_parts,
         'declared': declared_parts}


def active(connection) -> list[dict]:
    rows = many(connection, "SELECT * FROM knowledge WHERE status='active' ORDER BY created_at, rowid")
    return [found for row in rows if (found := view(connection, row)) is not None]


def kept_from(secret: dict, key: str) -> bool:
    """Whether this person must not find out: on the guarded list, or anyone who doesn't know when kept from all."""
    return key not in secret['knowers'] and (secret['guard_all'] or key in secret['guarded'])


def gossips(connection, key: str) -> bool:
    """Whether this person's flaw is gossip: only companions have a sheet to read it from."""
    if not key.startswith('companion:'):
        return False
    found = by_id(connection, key.split(':', 1)[1])
    return bool(found) and perception.for_companion(found['id'], found['version']['definition'])['picks'].get(
        'flaw') == 'gossip'


def spreads(connection, secret: dict, teller: str, listener: str, now) -> bool:
    """Whether a knower would happily pass this on, decided by the consequence engine (companion/consequences.py,
    choice `secret:pass_on`): only a gossip, and only when it isn't being kept from that person; how likely
    comes from how close they feel. The dice are seeded by the secret, the two people and that closeness, so the
    answer holds until the closeness changes. Never anything kept from them; the slip check still guards that."""
    if teller not in secret['knowers'] or listener in secret['knowers'] or kept_from(secret, listener):
        return False
    if not gossips(connection, teller):
        return False
    from companion import consequences
    from companion.memory import pairs  # pairs reads found_about from here
    level = pairs.closeness(connection, teller, listener, now) or 0
    found = consequences.odds(PASS_ON, {'closeness_a': level}, {'name': 'they', 'a': 'them', 'b': ''})
    return consequences.roll(f"{secret['id']}:{teller}>{listener}:{level}", found) == 0


# Registering storyline and character secrets -----------------------------------------------------------

def character_lines(definition: dict) -> dict[str, str]:
    """{digest: sentence} for each sentence in the description that reads as a secret."""
    found = {}
    for field in CHARACTER_FIELDS:
        for sentence in SENTENCE.split(definition.get(field) or ''):
            sentence = sentence.strip()
            if sentence and SECRET_LINE.search(sentence):
                line = sentence[:STATEMENT_LIMIT]
                found[hashlib.sha1(' '.join(line.casefold().split()).encode()).hexdigest()[:16]] = line
    return found


def insert(connection, kind: str, source_id: str | None, timestamp: str, *, statement=None, subjects=None,
           key_words=None, guard_all=False) -> str:
    knowledge_id = identifier()
    connection.execute(
        'INSERT INTO knowledge (id, kind, source_id, statement, subjects, key_words, guard_all, status, created_at, '
        "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)",
        (knowledge_id, kind, source_id, statement, encode(subjects or []), encode(key_words or []), int(guard_all),
         timestamp, timestamp))
    return knowledge_id


def hold(connection, knowledge_id: str, holder: str, role: str, learned_at: str, via: str, message_id=None,
         told_by: str | None = None) -> bool:
    """Adds a holder row unless they already hold that role; returns whether one was added. `told_by` is who they
    heard it from (a person key or 'user'), which they remember."""
    existing = optional(connection, 'SELECT id FROM knowledge_holders WHERE knowledge_id=? AND holder=? AND role=? '
                        'AND ended_at IS NULL', (knowledge_id, holder, role))
    if existing:
        return False
    connection.execute('INSERT INTO knowledge_holders (id, knowledge_id, holder, role, learned_at, via, message_id, '
                       'told_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (identifier(), knowledge_id, holder, role,
                                                                    learned_at, via, message_id, told_by))
    return True


def sync(connection, now) -> None:
    """Registers storyline and character secrets that have come up, and ends the ones whose source is gone or
    made public. Cheap: a few rows per companion, all rules."""
    timestamp = stamp(now)
    sync_storylines(connection, now, timestamp)
    sync_characters(connection, timestamp)
    sync_memories(connection, timestamp)
    for row in many(connection, "SELECT * FROM knowledge WHERE status='active' AND kind!='declared'"):
        if view(connection, row) is None:
            connection.execute("UPDATE knowledge SET status='ended', updated_at=? WHERE id=?", (timestamp, row['id']))


def sync_storylines(connection, now, timestamp: str):
    stories = tuple(STORY_SECRETS)
    marks = ','.join('?' * len(stories))
    rows = many(connection, f'SELECT s.*, c.id AS companion_id FROM storylines s JOIN companions c '
                f'ON c.active_timeline_id=s.timeline_id WHERE s.story IN ({marks})', stories)
    for story in rows:
        companion = by_id(connection, story['companion_id'])
        if companion is None:
            continue
        today = storylines.local_today(companion, now).isoformat()
        stages = decode(story['stages'])
        if stages[0]['on'] > today:
            continue  # Nobody has found out yet.
        rule = STORY_SECRETS[story['story']]
        existing = optional(connection, "SELECT * FROM knowledge WHERE kind='storyline' AND source_id=?",
                            (story['id'],))
        public = rule['ends'] and any(stage['on'] <= today and rule['ends'] in stage['text'] for stage in stages)
        if existing is None and not public:
            knowledge_id = insert(connection, 'storyline', story['id'], timestamp, guard_all=True)
            learned = f"{stages[0]['on']}T12:00:00.000000+00:00"  # The day they found out.
            hold(connection, knowledge_id, companion_key(companion['id']), 'knows', learned, 'origin')
            cast = dict(zip(('a', 'b'), decode(story['cast_ids'])))
            for field in rule['knowers']:
                if field in cast:
                    hold(connection, knowledge_id, circle_key(connection, cast[field]), 'knows', learned, 'origin')
        elif existing is not None and public and existing['status'] == 'active':
            connection.execute("UPDATE knowledge SET status='ended', updated_at=? WHERE id=?",
                               (timestamp, existing['id']))


def sync_characters(connection, timestamp: str):
    companions = many(connection, 'SELECT id FROM companions WHERE active_version_id IS NOT NULL')
    for row in companions:
        found = by_id(connection, row['id'])
        for digest in character_lines(found['version']['definition']):
            source = f"{row['id']}:{digest}"
            if optional(connection, "SELECT id FROM knowledge WHERE kind='character' AND source_id=?", (source,)):
                continue
            knowledge_id = insert(connection, 'character', source, timestamp, guard_all=True)
            hold(connection, knowledge_id, companion_key(row['id']), 'knows', timestamp, 'origin')


def sync_memories(connection, timestamp: str):
    """A companion's memory that reads like a secret ("hasn't told her sister", "nobody knows") is one they know,
    kept from everyone else: registered on its own, edited or removed in the panel like any other."""
    rows = many(connection, 'SELECT m.id, m.companion_id, m.subject, m.value FROM memories m JOIN companions c '
                "ON c.id=m.companion_id AND c.active_timeline_id=m.timeline_id WHERE m.status='active' AND NOT EXISTS "
                "(SELECT 1 FROM knowledge k WHERE k.kind='memory' AND k.source_id=m.id)")
    for row in rows:
        if SECRET_LINE.search(row['subject']) or SECRET_LINE.search(row['value']):
            knowledge_id = insert(connection, 'memory', row['id'], timestamp, guard_all=True)
            hold(connection, knowledge_id, companion_key(row['companion_id']), 'knows', timestamp, 'origin')


# The witness rule --------------------------------------------------------------------------------------

def witness(connection, message: dict) -> list[str]:
    """A finished group message: everyone present learns any secret it gives away. Returns the ids of secrets it
    gave away to someone they were kept from (`found_about` counts those for closeness between people)."""
    present = decode(message['present']) or []
    author = message['author'] if message['author'] not in ('user', 'app') else None
    slipped = []
    for secret in active(connection):
        if not hits(secret, message['text'], author):
            continue
        told_by_knower = author in secret['knowers']
        for member in [author, *present] if author else present:
            if member in secret['knowers']:
                continue
            # Someone it was kept from found out: from a knower it slipped; from the user it was the user's reveal.
            guarded = kept_from(secret, member)
            via = 'reveal' if guarded and message['author'] == 'user' else 'slip' if guarded and told_by_knower \
                else 'witness'
            hold(connection, secret['id'], member, 'knows', message['created_at'], via, message['id'], message['author'])
            if via in ('slip', 'reveal'):
                slipped.append(secret['id'])
            if via == 'reveal':
                from companion.life import reactions  # reactions reads secrets
                reactions.told_secret(connection, secret, member, parse(message['created_at']))
    return list(dict.fromkeys(slipped))


def history(connection, group_id: str, member: str, timestamp: str):
    """Added with everything so far: they learn every secret that was given away in the group before."""
    rows = many(connection, "SELECT * FROM group_messages WHERE group_id=? AND status='complete' AND author!='app' "
                'ORDER BY seq', (group_id,))
    for secret in active(connection):
        if member in secret['knowers']:
            continue
        said = next((row for row in rows if hits(secret, row['text'], row['author'])), None)
        if said:
            hold(connection, secret['id'], member, 'knows', timestamp, 'history', said['id'], said['author'])


# In prompts --------------------------------------------------------------------------------------------

def watched(connection, speaker: str, present: list[str]) -> list[dict]:
    """Secrets this speaker knows that someone present must not find out: their replies get checked."""
    return [secret for secret in active(connection) if speaker in secret['knowers']
            and any(kept_from(secret, member) for member in present if member != speaker)]


def label(connection, key: str, labels: dict[str, str]) -> str:
    return labels.get(key) or first_name(person_name(connection, key) or 'someone')


def group_lines(connection, speaker: str, present: list[str], labels: dict[str, str],
                now=None) -> list[tuple[str, str]]:
    """The speaker's private lines about secrets in this group: only those they know, with who here must not
    find out. `labels` names members as the chat does."""
    lines = []
    for secret in active(connection):
        if speaker not in secret['knowers']:
            continue
        others = [member for member in present if member != speaker]
        guarded = [label(connection, member, labels) for member in others if kept_from(secret, member)]
        unaware = [label(connection, member, labels) for member in others
                   if member not in secret['knowers'] and not kept_from(secret, member)]
        text = f"- You know: {secret['statement'].rstrip('.')}."
        if guarded:
            text += (f" {names_text(guarded)} {'does' if len(guarded) == 1 else 'do'}n't know and must not find "
                     'out: never say it or hint at it in this group.')
        elif unaware:
            text += f" {names_text(unaware)} {'does' if len(unaware) == 1 else 'do'}n't know it."
            told = [label(connection, member, labels) for member in others
                    if now is not None and spreads(connection, secret, speaker, member, now)]
            if told:
                text += f" You're close enough to {names_text(told)} that you'd happily tell them."
        elif others:
            text += ' Everyone else here knows it too.'
        lines.append((f"secret:{secret['id']}", text))
    return lines


def reminder(secrets: list[dict], name: str, present: list[str], connection, labels: dict[str, str]) -> str:
    """Private to the speaker: their draft gave a secret away, so it is written again."""
    guarded = sorted({label(connection, member, labels) for secret in secrets for member in present
                      if kept_from(secret, member)})
    what = '; '.join(secret['statement'] for secret in secrets)
    return (f"{name}'s draft gave away something {name} keeps secret ({what}) while {names_text(guarded)} "
            f"{'is' if len(guarded) == 1 else 'are'} here. Write {name}'s message again so it neither says it "
            'nor hints at it.')


def context_lines(connection, companion: dict) -> list[tuple[str, str]]:
    """A companion's 1:1 chat: secrets they learned from others or that the user declared. Their own storylines
    and sheet already tell them the rest. Facts heard in a group follow automatic memory, like other memories."""
    key = companion_key(companion['id'])
    remember = bool(settings(connection)['automatic_memory'])
    lines = []
    for secret in active(connection):
        mine = next((holder for holder in secret['knows'] if holder['holder'] == key), None)
        if mine is None or (secret['kind'] != 'declared' and mine['via'] == 'origin'):
            continue
        if mine['via'] in ('witness', 'slip', 'history') and not remember:
            continue
        guarded = [first_name(name) for member in secret['guarded'] - secret['knowers']
                   if (name := person_name(connection, member))]
        tail = (' Keep it to yourself.' if secret['guard_all'] else
                f" {names_text(guarded)} must not find out." if guarded else '')
        teller = told(connection, mine)
        since = f" ({f'{teller} told you, ' if teller else ''}since {parse(mine['learned_at']).date().isoformat()})"
        lines.append((f"secret:{secret['id']}", f"- {secret['statement'].rstrip('.')}{since}.{tail}"))
    return lines


def told(connection, holder: dict) -> str | None:
    """Who they heard it from, as they would say it: a name, "the user", or None when nobody told them."""
    teller = holder.get('told_by')
    if not teller or teller == holder['holder']:
        return None
    return 'the user' if teller == 'user' else first_name(person_name(connection, teller) or 'someone')


def found_about(connection, holder: str, about: str) -> int:
    """How many secrets about `about` that were kept from `holder` they found out (it slipped, or the user let them
    find out): what lowers how they feel about that person, when their sheet says they'd react (memory/pairs.py)."""
    found = 0
    for row in many(connection, "SELECT k.* FROM knowledge_holders h JOIN knowledge k ON k.id=h.knowledge_id WHERE "
                    "h.holder=? AND h.role='knows' AND h.via IN ('reveal', 'slip') AND h.ended_at IS NULL "
                    "AND k.status='active'", (holder,)):
        secret = view(connection, row)
        found += bool(secret and any(subject.get('key') == about for subject in secret['subjects']))
    return found


def slips_allowed(connection) -> bool:
    return storylines.drama(connection) >= SLIP_LEVEL


# The Secrets panel -------------------------------------------------------------------------------------

def companions(connection) -> list[dict]:
    rows = many(connection, 'SELECT c.id, v.name FROM companions c JOIN character_versions v '
                'ON v.id=c.active_version_id ORDER BY c.slot IS NULL, c.stepped_back_at DESC')
    return [{'id': row['id'], 'name': row['name']} for row in rows]


def holder_view(connection, holder: dict) -> dict:
    companion_id = holder['holder'].split(':', 1)[1] if holder['holder'].startswith('companion:') else None
    group = None
    if holder['message_id']:
        row = optional(connection, 'SELECT g.id, g.name FROM group_messages m JOIN group_chats g ON g.id=m.group_id '
                       'WHERE m.id=?', (holder['message_id'],))
        group = row and {'id': row['id'], 'name': row['name']}
    teller = told(connection, holder)
    how = VIA_TEXT[holder['via']] if teller is None else TOLD_TEXT[holder['via']].format(
        teller='you' if teller == 'the user' else teller)
    return {'key': holder['holder'], 'companion_id': companion_id,
            'name': person_name(connection, holder['holder']) or 'Someone no longer here', 'via': holder['via'],
            'how': how, 'told_by': teller, 'learned_at': holder['learned_at'], 'group': group}


SOURCE_TEXT = {'storyline': 'storyline', 'character': 'character', 'memory': 'memories'}


def source_text(connection, secret: dict) -> str:
    if secret['kind'] == 'declared':
        return 'You added this'
    owner = next((holder['holder'] for holder in secret['knows'] if holder['via'] == 'origin'
                  and holder['holder'].startswith('companion:')), None)
    name = first_name(person_name(connection, owner) or 'a companion')
    return f"From {name}'s {SOURCE_TEXT[secret['kind']]}"


def panel_view(connection, secret: dict) -> dict:
    return {'id': secret['id'], 'kind': secret['kind'], 'statement': secret['statement'],
            'source': source_text(connection, secret),
            'about': [subject['name'] for subject in secret['subjects']],
            'key_words': secret['keys'], 'own_key_words': secret['own_keys'],
            'keep_from_everyone': secret['guard_all'],
            'knows': [holder_view(connection, holder) for holder in secret['knows']],
            'kept_from': [{'key': key, 'companion_id': key.split(':', 1)[1] if key.startswith('companion:') else None,
                           'name': person_name(connection, key) or 'Someone no longer here'}
                          for key in sorted(secret['guarded'] - secret['knowers'])],
            'created_at': secret['created_at']}


def listing(database) -> dict:
    with database.connect(write=True) as connection:
        sync(connection, database.clock.now())
        return {'secrets': [panel_view(connection, secret) for secret in active(connection)],
                'companions': companions(connection), 'slips': slips_allowed(connection)}


def subjects_for(connection, names: list[str]) -> list[dict]:
    """Who a secret is about: a companion when the name is one of theirs (in full or first name), else as typed."""
    people = companions(connection)
    result = []
    for name in dict.fromkeys(' '.join(name.split()) for name in names):
        if not name:
            continue
        match = next((person for person in people if name.casefold() in
                      {form.casefold() for form in forms(person['name'])}), None)
        result.append({'key': companion_key(match['id']), 'name': match['name']} if match else
                      {'key': None, 'name': name[:80]})
    return result


def require_secret(connection, knowledge_id: str) -> dict:
    row = optional(connection, "SELECT * FROM knowledge WHERE id=? AND status='active'", (knowledge_id,))
    require(row is not None, 'That secret is gone.', 404)
    return row


def require_companion(connection, companion_id: str) -> str:
    require(by_id(connection, companion_id) is not None, 'That companion is no longer in this workspace.', 404)
    return companion_key(companion_id)


def set_people(connection, knowledge_id: str, knows: list[str], kept_from_ids: list[str], timestamp: str):
    """The user's lists: who knows (from the start) and who must not find out. Someone who learned it another way
    keeps knowing; taking someone off "knows" here is the panel's Forget."""
    knowers = [require_companion(connection, companion_id) for companion_id in dict.fromkeys(knows)]
    guarded = [require_companion(connection, companion_id) for companion_id in dict.fromkeys(kept_from_ids)]
    require(not set(knowers) & set(guarded), 'Someone cannot both know it and be kept from it.', 422)
    for key in knowers:
        hold(connection, knowledge_id, key, 'knows', timestamp, 'origin')
    connection.execute("UPDATE knowledge_holders SET ended_at=? WHERE knowledge_id=? AND role='guarded' "
                       'AND ended_at IS NULL', (timestamp, knowledge_id))
    for key in guarded:
        connection.execute('INSERT INTO knowledge_holders (id, knowledge_id, holder, role, learned_at, via) '
                           "VALUES (?, ?, ?, 'guarded', ?, 'origin')", (identifier(), knowledge_id, key, timestamp))


def clean_words(words: list[str] | None) -> list[str]:
    return list(dict.fromkeys(' '.join(word.split()).casefold() for word in words or [] if word.strip()))[:30]


def create(database, body) -> dict:
    timestamp = database.now()
    with database.connect(write=True) as connection:
        statement = ' '.join(body.statement.split())[:STATEMENT_LIMIT].rstrip('.')
        require(statement, 'Write what the secret is.', 422)
        require(body.knows, 'Pick at least one companion who knows it.', 422)
        knowledge_id = insert(connection, 'declared', None, timestamp, statement=statement,
                              subjects=subjects_for(connection, body.about), key_words=clean_words(body.key_words),
                              guard_all=body.keep_from_everyone)
        set_people(connection, knowledge_id, body.knows, [] if body.keep_from_everyone else body.kept_from, timestamp)
    return listing(database)


def update(database, knowledge_id: str, body) -> dict:
    """The user's own secret can change in full; one from a storyline or a character keeps its words (they come
    from there) but takes the user's key words and who it's kept from."""
    timestamp = database.now()
    with database.connect(write=True) as connection:
        row = require_secret(connection, knowledge_id)
        if row['kind'] == 'declared' and body.statement is not None:
            statement = ' '.join(body.statement.split())[:STATEMENT_LIMIT].rstrip('.')
            require(statement, 'Write what the secret is.', 422)
            connection.execute('UPDATE knowledge SET statement=? WHERE id=?', (statement, knowledge_id))
        if row['kind'] == 'declared' and body.about is not None:
            connection.execute('UPDATE knowledge SET subjects=? WHERE id=?',
                               (encode(subjects_for(connection, body.about)), knowledge_id))
        if body.key_words is not None:
            connection.execute('UPDATE knowledge SET key_words=? WHERE id=?',
                               (encode(clean_words(body.key_words)), knowledge_id))
        if body.keep_from_everyone is not None:
            connection.execute('UPDATE knowledge SET guard_all=? WHERE id=?', (int(body.keep_from_everyone),
                                                                               knowledge_id))
        if body.knows is not None or body.kept_from is not None:
            current = view(connection, one(connection, 'SELECT * FROM knowledge WHERE id=?', (knowledge_id,)))
            knows = body.knows if body.knows is not None else []
            if row['kind'] == 'declared' and body.knows is not None:
                # "Who knows it" lists who knew from the start; whoever learned it since keeps knowing.
                keep = {companion_key(companion_id) for companion_id in knows}
                for holder in current['knows']:
                    if holder['via'] == 'origin' and holder['holder'] not in keep:
                        connection.execute('UPDATE knowledge_holders SET ended_at=? WHERE id=?',
                                           (timestamp, holder['id']))
            kept = body.kept_from if body.kept_from is not None else [
                key.split(':', 1)[1] for key in current['guarded'] if key.startswith('companion:')]
            set_people(connection, knowledge_id, knows, kept, timestamp)
        connection.execute('UPDATE knowledge SET updated_at=? WHERE id=?', (timestamp, knowledge_id))
    return listing(database)


def end(database, knowledge_id: str) -> dict:
    """Delete the user's own secret, or stop treating one from a memory, a storyline or a character as a secret
    (it stays on record as dismissed, so it isn't registered again)."""
    timestamp = database.now()
    with database.connect(write=True) as connection:
        row = require_secret(connection, knowledge_id)
        if row['kind'] == 'declared':
            connection.execute('DELETE FROM knowledge_holders WHERE knowledge_id=?', (knowledge_id,))
            connection.execute('DELETE FROM knowledge WHERE id=?', (knowledge_id,))
        else:
            connection.execute("UPDATE knowledge SET status='dismissed', updated_at=? WHERE id=?",
                               (timestamp, knowledge_id))
    return listing(database)


def reveal(database, knowledge_id: str, companion_id: str) -> dict:
    """Let them find out: they know it from now on, recorded as the user's doing."""
    timestamp = database.now()
    with database.connect(write=True) as connection:
        require_secret(connection, knowledge_id)
        key = require_companion(connection, companion_id)
        hold(connection, knowledge_id, key, 'knows', timestamp, 'reveal')
    return listing(database)


def forget(database, knowledge_id: str, companion_id: str) -> dict:
    """Make them forget it, the way "Don't remember this" works: their knowing ends. Whoever it started with on a
    storyline or in their own description can't forget it here."""
    timestamp = database.now()
    with database.connect(write=True) as connection:
        row = require_secret(connection, knowledge_id)
        key = companion_key(companion_id)
        if row['kind'] != 'declared':
            require(optional(connection, "SELECT id FROM knowledge_holders WHERE knowledge_id=? AND holder=? AND "
                             "via='origin' AND ended_at IS NULL", (knowledge_id, key)) is None,
                    'It happened in their own life, so they can\'t forget it.', 409)
        connection.execute("UPDATE knowledge_holders SET ended_at=? WHERE knowledge_id=? AND holder=? AND role='knows' "
                           'AND ended_at IS NULL', (timestamp, knowledge_id, key))
    return listing(database)


def forget_everywhere(connection, companion_id: str, timestamp: str):
    """Start over or Delete: the companion no longer knows what they learned. Secrets from their own description
    come back from the sheet; storyline ones go with their history."""
    connection.execute("UPDATE knowledge_holders SET ended_at=? WHERE holder=? AND ended_at IS NULL AND NOT "
                       "(via='origin' AND knowledge_id IN (SELECT id FROM knowledge WHERE kind='character'))",
                       (timestamp, companion_key(companion_id)))
