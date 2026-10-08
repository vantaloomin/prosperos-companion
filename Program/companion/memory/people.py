"""The people in the user's real life: who they are, what the user said about them, and what to ask next.

People are learned from the user's own statements under the same consent as every other memory
(automatic memory, or Remember this): `people_rules` finds them, formation matches each mention to a
stored person, and every fact about them is an ordinary memory carrying `person_id`. So correcting,
excluding and deleting work as they do for any memory, and a person with no memories left is removed.

Follow-up questions are picked here, without a model: recent news first ("Jo got engaged" a few days
ago), then a missing name, then a light check-in on someone who has not come up for a while. At most
one is offered at a time, rarely, never about a loss or anyone a boundary covers, and the model only
phrases it if it fits the conversation. The same question is not offered twice.
"""
from datetime import timedelta

from companion.characters import require_current
from companion.clock import parse
from companion.database import bump_memory_revision, decode, identifier, many, one, optional, settings
from companion.errors import require
from companion.memory import people_rules, records

TOPIC_ORDER = ('work', 'home_city', 'age', 'birthday', 'studies', 'has', 'likes', 'dislikes', 'news')
# How often a question may be offered, and which news is worth asking about.
ASK_GAP_REPLIES = 8
ASK_GAP = timedelta(hours=6)
RECEIPT_WINDOW = 200
NEWS_FROM = timedelta(hours=12)
NEWS_UNTIL = timedelta(days=21)
CHECK_IN_AFTER = timedelta(days=4)
CHECK_IN_WITHIN = timedelta(days=90)
CHECK_IN_AGAIN = timedelta(days=14)
ASK = ('A question you could ask, only if it fits what you are talking about (skip it if the user is busy, upset '
       'or on another topic; ask in your own words, once, like a friend would, never as an interview): ')


def label(person) -> str:
    return person['name'] or f"Your {person['relation'] or 'friend'}"


def topic_of(memory) -> str:
    return memory['subject_key'].rsplit('.', 1)[-1]


def subject_for(person, topic) -> str:
    if topic == 'who':
        return (person['relation'] or 'Someone').capitalize()
    return f"{label(person)}: {people_rules.TOPIC_LABELS.get(topic, topic.capitalize())}"


def known(connection, companion_id) -> list[dict]:
    return many(connection, 'SELECT * FROM user_people WHERE companion_id=? ORDER BY created_at, id', (companion_id,))


def names(people) -> dict:
    """Name to relation, so extraction recognises "Jo got promoted" once Jo is known."""
    return {person['name']: person['relation'] for person in people if person['name']}


def find(people, reference) -> dict | None:
    """The stored person a mention means, or None for someone new."""
    name, relation = reference.get('name'), reference.get('relation')
    if name:
        key = name.casefold()
        match = next((person for person in people if (person['name'] or '').casefold() == key), None)
        if match or not relation or relation in people_rules.NAMED_ONLY:
            return match
        # "My sister" first, "my sister Jo" later: the sister now has a name.
        unnamed = [person for person in people if not person['name'] and person['relation'] == relation]
        return unnamed[0] if len(unnamed) == 1 else None
    same = [person for person in people if person['relation'] == relation]
    return max(same, key=lambda person: person['last_mentioned_at'] or person['created_at'], default=None)


def relabel(connection, person, timestamp):
    """Subjects follow the person's current name and relation."""
    for memory in many(connection, 'SELECT id, subject_key FROM memories WHERE person_id=?', (person['id'],)):
        connection.execute('UPDATE memories SET subject=?, updated_at=? WHERE id=?',
                           (subject_for(person, topic_of(memory)), timestamp, memory['id']))


def resolve(connection, companion_id, reference, timestamp) -> dict:
    """Find or add the person a committed fact is about, filling in a name or relation learned now."""
    people = known(connection, companion_id)
    person = find(people, reference)
    if person is None:
        person = {'id': identifier(), 'name': reference.get('name'), 'relation': reference.get('relation')}
        connection.execute('INSERT INTO user_people (id, companion_id, name, relation, last_mentioned_at, created_at, '
                           'updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                           (person['id'], companion_id, person['name'], person['relation'], timestamp, timestamp,
                            timestamp))
        return one(connection, 'SELECT * FROM user_people WHERE id=?', (person['id'],))
    name = person['name'] or reference.get('name')
    relation = person['relation'] or reference.get('relation')
    if (name, relation) != (person['name'], person['relation']):
        connection.execute('UPDATE user_people SET name=?, relation=?, updated_at=? WHERE id=?',
                           (name, relation, timestamp, person['id']))
        person = one(connection, 'SELECT * FROM user_people WHERE id=?', (person['id'],))
        relabel(connection, person, timestamp)
        if name and not person_name_was_known(people, person):
            name_placeholder(connection, person, timestamp)
    return person


def person_name_was_known(people, person) -> bool:
    return any(item['id'] == person['id'] and item['name'] for item in people)


def name_placeholder(connection, person, timestamp):
    """"I have a sister" kept "Has a sister"; once her name is known, that memory becomes the name."""
    for memory in many(connection, "SELECT * FROM memories WHERE person_id=? AND status='active' AND subject_key=? "
                       "AND value LIKE 'Has a %'", (person['id'], f"person.{person['id']}.who")):
        records.revise(connection, memory, timestamp, value=person['name'])


def bind(fields, person) -> dict:
    topic = fields.get('topic') or 'who'
    return {**fields, 'person_id': person['id'], 'subject': subject_for(person, topic),
            'subject_key': f"person.{person['id']}.{topic}"}


def bind_existing(connection, companion_id, fields) -> dict:
    """A mention of someone already known uses their stored identity, so a new value for their home or work
    is checked against the current one like the user's own facts."""
    person = find(known(connection, companion_id), fields['person']) if fields.get('person') else None
    return bind(fields, person) if person else fields


def touch(connection, companion_id, text, timestamp):
    """Remember when each known person last came up, for check-ins."""
    found = people_rules.mentioned(text, known(connection, companion_id))
    connection.executemany('UPDATE user_people SET last_mentioned_at=? WHERE id=? AND '
                           '(last_mentioned_at IS NULL OR last_mentioned_at<?)',
                           [(timestamp, person_id, timestamp) for person_id in found])


def view(person, memories) -> dict:
    mine = [memory for memory in memories if memory.get('person_id') == person['id']]
    return {**person, 'label': label(person), 'memory_ids': [memory['id'] for memory in mine]}


def listing(database) -> list[dict]:
    with database.connect() as connection:
        companion = require_current(connection)
        memories = many(connection, "SELECT id, person_id FROM memories WHERE companion_id=? AND person_id IS NOT NULL "
                        "AND status IN ('active','excluded')", (companion['id'],))
        people = [view(person, memories) for person in known(connection, companion['id'])]
        return sorted(people, key=lambda person: (person['last_mentioned_at'] or '', person['created_at']),
                      reverse=True)


def add(database, body) -> dict:
    """Add someone by hand: their name and how they are related to the user, kept as a memory like any other."""
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        timestamp = database.now()
        reference = {'name': body.name.strip() or None, 'relation': body.relation.strip().casefold() or None}
        require(reference['name'] or reference['relation'], 'Give a name, a relation or both.', 422)
        person = resolve(connection, companion['id'], reference, timestamp)
        fields = bind({'layer': 'user_fact', 'subject': '', 'value': person['name'] or f"Has a {person['relation']}",
                       'topic': 'who'}, person)
        records.insert(connection, companion, fields, now=timestamp)
        return view(person, many(connection, 'SELECT id, person_id FROM memories WHERE person_id=?', (person['id'],)))


def update(database, person_id, body) -> dict:
    """A new name or relation renames every memory about them; the "who" memory keeps the history."""
    with database.connect(write=True) as connection:
        person = one(connection, 'SELECT * FROM user_people WHERE id=?', (person_id,))
        timestamp = database.now()
        name = person['name'] if body.name is None else (body.name.strip() or None)
        relation = person['relation'] if body.relation is None else (body.relation.strip().casefold() or None)
        require(name or relation, 'Keep a name, a relation or both.', 422)
        connection.execute('UPDATE user_people SET name=?, relation=?, updated_at=? WHERE id=?',
                           (name, relation, timestamp, person_id))
        person = one(connection, 'SELECT * FROM user_people WHERE id=?', (person_id,))
        relabel(connection, person, timestamp)
        who = optional(connection, "SELECT * FROM memories WHERE person_id=? AND status='active' AND subject_key=?",
                       (person_id, f'person.{person_id}.who'))
        value = name or f'Has a {relation}'
        if who and who['value'] != value:
            records.revise(connection, who, timestamp, value=value)
        bump_memory_revision(connection, timestamp)
        memories = many(connection, 'SELECT id, person_id FROM memories WHERE person_id=? '
                        "AND status IN ('active','excluded')", (person_id,))
        return view(person, memories)


def delete(database, person_id) -> dict:
    """Forget someone: every memory about them goes, with the same deletion markers as any memory."""
    with database.connect() as connection:
        one(connection, 'SELECT id FROM user_people WHERE id=?', (person_id,))
        memory_ids = [row['id'] for row in many(
            connection, "SELECT id FROM memories WHERE person_id=? AND status<>'superseded'", (person_id,))]
    removed = []
    for memory_id in memory_ids:
        with database.connect() as connection:
            if not optional(connection, 'SELECT id FROM memories WHERE id=?', (memory_id,)):
                continue
        removed += records.delete(database, memory_id)['deleted_memory_ids']
    with database.connect(write=True) as connection:
        connection.execute('DELETE FROM user_people WHERE id=?', (person_id,))
    return {'id': person_id, 'deleted_memory_ids': sorted(set(removed))}


# Context: who they are, and at most one question.

def spoken(person) -> str:
    """How the context refers to someone: their name, or "the user's mum"."""
    return person['name'] or f"the user's {person['relation'] or 'friend'}"


def fact_text(memory) -> str:
    topic = topic_of(memory)
    if topic == 'news':
        return f"news (told you {memory['stated_at'][:10]}): {memory['value']}"
    return f"{people_rules.TOPIC_LABELS.get(topic, topic).lower()}: {memory['value']}"


def person_text(person, facts) -> str:
    head = f"- {person['name']} (the user's {person['relation']})" if person['name'] and person['relation'] else \
        f"- {person['name']}" if person['name'] else f"- The user's {person['relation']} (name not known yet)"
    shown = sorted((memory for memory in facts if topic_of(memory) != 'who'),
                   key=lambda memory: (TOPIC_ORDER.index(topic_of(memory)) if topic_of(memory) in TOPIC_ORDER
                                       else len(TOPIC_ORDER), memory['stated_at']))
    return head + (': ' + '; '.join(fact_text(memory) for memory in shown) if shown else '')


def asked(connection, timeline_id, now) -> tuple[bool, dict]:
    """Whether a question was offered recently, and when each question was last offered, from reply receipts."""
    rows = many(connection, "SELECT created_at, receipt FROM messages WHERE timeline_id=? AND role='companion' "
                'AND receipt IS NOT NULL ORDER BY seq DESC LIMIT ?', (timeline_id, RECEIPT_WINDOW))
    recent, when = False, {}
    for index, row in enumerate(rows):
        included = decode(row['receipt']).get('included') or {}
        for identity in included.get('people', []) + included.get('ask', []):
            if identity.startswith('ask:'):
                when.setdefault(identity, row['created_at'])
                recent = recent or index < ASK_GAP_REPLIES or parse(row['created_at']) > now - ASK_GAP
    return recent, when


def off_limits(person, facts, boundaries) -> bool:
    """Never ask about someone the user set a boundary around, or after a loss."""
    words = [word.casefold() for word in (person['name'], person['relation']) if word]
    if any(word in boundary['value'].casefold() for boundary in boundaries for word in words):
        return True
    return any(topic_of(memory) == 'news' and people_rules.GRIEF.search(memory['value']) for memory in facts)


def questions(people, facts_by, boundaries, now):
    """Every question worth asking, best first, as (identity, text)."""
    news, names_, check_ins = [], [], []
    for person in people:
        facts = facts_by.get(person['id'], [])
        if off_limits(person, facts, boundaries):
            continue
        for memory in facts:
            stated = parse(memory['stated_at'])
            if topic_of(memory) == 'news' and not memory['sensitive'] and now - NEWS_UNTIL < stated < now - NEWS_FROM:
                news.append((memory['stated_at'], f"ask:news:{memory['id']}",
                             f"{spoken(person)} {memory['value']} (the user told you on {memory['stated_at'][:10]}). "
                             'You could ask how that is going or how it went.'))
        if not person['name'] and person['relation'] not in people_rules.PETS:
            names_.append(f"ask:name:{person['id']}")
        mentioned = parse(person['last_mentioned_at'] or person['created_at'])
        if now - CHECK_IN_WITHIN < mentioned < now - CHECK_IN_AFTER:
            missing = [people_rules.TOPIC_LABELS[topic].lower() for topic in ('work', 'home_city', 'likes')
                       if not any(topic_of(memory) == topic for memory in facts)]
            hint = f", or something you don't know yet such as their {missing[0]}" if missing and \
                person['relation'] not in people_rules.PETS else ''
            check_ins.append((person['last_mentioned_at'] or '', f"ask:checkin:{person['id']}",
                              f"how {spoken(person)} is doing{hint}. They have not come up for a while."))
    found = [(identity, text) for _when, identity, text in sorted(news, reverse=True)]
    for identity in names_:
        person = next(item for item in people if item['id'] == identity.rsplit(':', 1)[1])
        found.append((identity, f"the name of the user's {person['relation']}; you don't know it yet."))
    found += [(identity, text) for _when, identity, text in sorted(check_ins, reverse=True)]
    return found


def pick(connection, companion, people, facts_by, boundaries, now) -> tuple[str, str] | None:
    if not settings(connection)['ask_about_people']:
        return None
    recent, when = asked(connection, companion['active_timeline_id'], now)
    if recent:
        return None
    for identity, text in questions(people, facts_by, boundaries, now):
        last = when.get(identity)
        if last is None or (identity.startswith('ask:checkin:') and parse(last) < now - CHECK_IN_AGAIN):
            return identity, text
    return None


def offer(packet, connection, companion, memories, boundaries, now, since=None):
    """One line per person the user told you about, then at most one question. Facts saved since `since` (the start
    of the conversation sent with the reply) go in a line of their own with the reply's notes."""
    facts_by = {}
    for memory in memories:
        facts_by.setdefault(memory['person_id'], []).append(memory)
    people = [person for person in known(connection, companion['id']) if person['id'] in facts_by]
    for person in people:
        facts = facts_by[person['id']]
        new = [memory for memory in facts if since and memory['created_at'] >= since]
        if len(new) < len(facts) or not new:
            packet.offer('people', person['id'], person_text(person, [memory for memory in facts if memory not in new]))
        if new:
            packet.offer('people+', f"{person['id']}:new", person_text(person, new))
    people.sort(key=lambda person: person['last_mentioned_at'] or person['created_at'], reverse=True)
    if choice := pick(connection, companion, people, facts_by, boundaries, now):
        packet.offer('ask', choice[0], ASK + choice[1])
