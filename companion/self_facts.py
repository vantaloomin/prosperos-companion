"""What the companion has said about themselves (realism: an LLM must not flip its own facts).

Rule-based capture, no model: after each completed companion message, first-person statements
about their own tastes, people, pets and history ("I hate cilantro", "my brother Theo", "I've
never been to Europe", "I grew up in Duluth") are noted with the sentence they came from. Noted
facts go into the chat context so later replies stay consistent, and the user can keep or remove
each one in Character Studio. A new statement that contradicts one already on record waits as a
conflict instead of quietly replacing it.

These are fiction about the character, never facts about the user (M1). They are separate from the
character definition (C1), so a deliberate edit still applies from a stated point. A fact belongs to
the message it came from: it applies on every timeline that holds that message or a copy of it, and
stops applying when that reply is replaced by another version or deleted.
"""
import re
from dataclasses import dataclass

from companion.characters import require_current
from companion.database import identifier, many, one
from companion.errors import require
from companion.memory.extraction import CLAUSE_END, HYPOTHETICAL, NOT_THINGS, QUESTION_START, QUOTED, SENTENCE

ACTIONS = re.compile(r'\*[^*\n]+\*')
THING = r"([^,.;!?]{2,50})"
NAME = r"(?-i:([A-Z][\w'’-]+))"
RELATIVES = ('older brother', 'younger brother', 'little brother', 'big brother', 'older sister', 'younger sister',
             'little sister', 'big sister', 'brother', 'sister', 'mom', 'mother', 'dad', 'father', 'grandma',
             'grandmother', 'grandpa', 'grandfather', 'aunt', 'uncle', 'cousin', 'best friend', 'roommate', 'boss',
             'ex', 'stepmom', 'stepdad', 'son', 'daughter')
PETS = ('cat', 'dog', 'kitten', 'puppy', 'rabbit', 'bunny', 'parrot', 'hamster', 'turtle', 'tortoise', 'snake', 'fish',
        'lizard', 'ferret', 'horse')
# Relations that have one current answer: a second name for them is a contradiction.
ONE_OF = {'mom', 'mother', 'dad', 'father', 'boss', 'stepmom', 'stepdad'}
SAME = {'mother': 'mom', 'father': 'dad'}
LIKE = r'(?:really |absolutely |totally |kind of |kinda |honestly |just )?'
RULES = (
    ('likes', re.compile(rf"\bi {LIKE}(?:love|adore|like|enjoy)\s+{THING}", re.IGNORECASE)),
    ('dislikes', re.compile(rf"\bi {LIKE}(?:hate|loathe|dislike|can'?t stand|cannot stand|don'?t like|do not like)"
                            rf"\s+{THING}", re.IGNORECASE)),
    ('favorite', re.compile(r"\bmy (?:all-time |absolute )?favou?rite ([a-z]+(?: [a-z]+)?) (?:is|has to be|was) "
                            rf"{THING}", re.IGNORECASE)),
    ('person', re.compile(rf"\bmy ({'|'.join(RELATIVES)}),? (?:is |was )?(?:named |called )?{NAME}", re.IGNORECASE)),
    ('pet', re.compile(rf"\bmy ({'|'.join(PETS)}),? (?:is |was )?(?:named |called )?{NAME}", re.IGNORECASE)),
    ('never', re.compile(r"\bi(?:'ve| have) never (been to|tried|seen|read|watched|played|eaten|had|ridden|learned)"
                         rf"\s+{THING}", re.IGNORECASE)),
    ('grew_up', re.compile(r"\bi grew up (?:in|on|near|outside(?: of)?) " r"(?-i:([A-Z][\w.'’-]*(?: [A-Z][\w.'’-]*)*))",
                           re.IGNORECASE)),
    ('allergy', re.compile(rf"\bi(?:'m| am) allergic to {THING}", re.IGNORECASE)),
)
LABELS = {'likes': 'Likes', 'dislikes': 'Dislikes', 'favorite': 'Favorite', 'person': 'Person', 'pet': 'Pet',
          'never': 'Never', 'grew_up': 'Grew up', 'allergy': 'Allergic to'}
STATUSES = ('noted', 'kept', 'rejected', 'conflict')
IN_FORCE = ('noted', 'kept')
# Objects that are the conversation, not a taste ("I love that", "I like talking to you").
NOT_TASTES = NOT_THINGS | {'it here', 'that too', 'this too', 'the idea', 'your', 'how you', 'when you', 'the way you',
                           'hearing', 'hearing that', 'that you', 'what you', 'having you', 'you too', 'us'}


@dataclass(frozen=True)
class Fact:
    category: str
    subject: str
    value: str
    statement: str

    @property
    def key(self) -> str:
        return f'{self.category}:{self.subject}'


def clean(thing: str) -> str:
    thing = CLAUSE_END.sub('', thing).strip().strip('"\'“”').strip()
    thing = re.sub(r'\s+(?:so much|a lot|too|honestly|though|lol|haha)$', '', thing, flags=re.IGNORECASE)
    # A lowercase article goes ("the beach"); a capitalised one is part of a name ("The National").
    return re.sub(r'^(?:the|a|an|my|some) ', '', thing).strip()


def fact_for(category: str, match, sentence: str) -> Fact | None:
    groups = [group for group in match.groups() if group]
    if category == 'person':
        relation, name = groups[0].lower(), groups[1]
        return Fact('person', SAME.get(relation, relation), name, sentence)
    if category == 'pet':
        return Fact('pet', groups[0].lower(), groups[1], sentence)
    if category == 'favorite':
        thing = clean(groups[1])
        return Fact('favorite', groups[0].lower(), thing, sentence) if thing else None
    if category == 'never':
        thing = clean(groups[1])
        return Fact('never', f'{groups[0].lower()} {thing.lower()}', thing, sentence) if thing else None
    if category == 'grew_up':
        return Fact('grew_up', 'hometown', groups[0].rstrip('.'), sentence)
    thing = clean(groups[0])
    if not thing or thing.lower() in NOT_TASTES or thing.lower().split()[0] in {'you', 'your', 'it', 'that', 'how'}:
        return None
    return Fact(category, thing.lower(), thing, sentence)


def extract(text: str) -> list[Fact]:
    """First-person statements in one companion message. Questions, hypotheticals and quoted lines are skipped."""
    text = QUOTED.sub(' ', ACTIONS.sub(' ', text))
    found, seen = [], set()
    for sentence in (part.strip() for part in SENTENCE.findall(text)):
        if not sentence or sentence.endswith('?') or QUESTION_START.match(sentence) or HYPOTHETICAL.search(sentence):
            continue
        if re.search(r"\b(?:wish|if only|maybe|might|probably)\b", sentence, re.IGNORECASE):
            continue
        for category, pattern in RULES:
            for match in pattern.finditer(sentence):
                fact = fact_for(category, match, sentence)
                if fact and fact.key not in seen and len(fact.value) <= 50:
                    seen.add(fact.key)
                    found.append(fact)
    return found


def opposite(fact: Fact) -> str | None:
    """The key a contradicting fact would have."""
    if fact.category == 'likes':
        return f'dislikes:{fact.subject}'
    if fact.category == 'dislikes':
        return f'likes:{fact.subject}'
    return None


def in_force(connection, timeline_id) -> list[dict]:
    """Facts whose message, or a copy of it, is an active complete message on this timeline. A reply to
    a message the user excluded or deleted from recall usually repeats it, so its facts leave with it (M12)."""
    from companion.memory.records import blocked_messages
    rows = many(connection, "SELECT self_facts.*, messages.reply_to AS reply_to, messages.id AS shown_id FROM "
                "self_facts JOIN messages ON (messages.id=self_facts.message_id OR "
                "messages.origin_id=self_facts.message_id) WHERE self_facts.status IN ('noted', 'kept') "
                "AND messages.timeline_id=? AND messages.active=1 AND messages.status='complete' "
                'AND messages.redacted_at IS NULL ORDER BY self_facts.created_at', (timeline_id,))
    if not rows:
        return []
    blocked = blocked_messages(connection, rows[0]['companion_id']) | {row['id'] for row in many(
        connection, 'SELECT id FROM messages WHERE timeline_id=? AND redacted_at IS NOT NULL', (timeline_id,))}
    result, seen = [], set()
    for row in rows:
        if row['id'] in seen or row['shown_id'] in blocked or (row['reply_to'] and row['reply_to'] in blocked):
            continue
        seen.add(row['id'])
        result.append({key: value for key, value in row.items() if key not in {'reply_to', 'shown_id'}})
    return result


def contradiction(fact: Fact, current: list[dict]) -> dict | None:
    for row in current:
        if row['key'] == opposite(fact):
            return row
        if row['category'] == fact.category and row['subject'] == fact.subject and row['value'].lower() != \
                fact.value.lower() and fact.category in {'favorite', 'grew_up', 'person'} and (
                    fact.category != 'person' or fact.subject in ONE_OF):
            return row
    return None


def note(connection, message: dict, timestamp: str) -> list[dict]:
    """Record what one completed companion message says about the character. Idempotent per message."""
    if message['role'] != 'companion' or message['status'] != 'complete':
        return []
    companion = require_current(connection)
    current = in_force(connection, message['timeline_id'])
    known = {row['key']: row for row in current}
    added = []
    for fact in extract(message['text']):
        if fact.key in known and known[fact.key]['value'].lower() == fact.value.lower():
            continue
        clash = contradiction(fact, current)
        status = 'conflict' if clash else 'noted'
        row_id = identifier()
        inserted = connection.execute(
            'INSERT OR IGNORE INTO self_facts (id, companion_id, message_id, key, category, subject, value, statement, '
            'status, conflicts_with, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (row_id, companion['id'], message['id'], fact.key, fact.category, fact.subject, fact.value,
             fact.statement[:300], status, clash['id'] if clash else None, timestamp)).rowcount
        if inserted:
            added.append(one(connection, 'SELECT * FROM self_facts WHERE id=?', (row_id,)))
    if any(row['category'] in {'likes', 'dislikes'} and row['status'] == 'noted' for row in added):
        stamp_change(connection, timestamp)
    return added


def view(row: dict) -> dict:
    return {key: row[key] for key in ('id', 'message_id', 'category', 'subject', 'value', 'statement', 'status',
                                      'conflicts_with', 'created_at', 'decided_at')} | {'label': LABELS[row['category']]}


def listing(database) -> dict:
    with database.connect() as connection:
        companion = require_current(connection)
        timeline_id = companion['active_timeline_id']
        active = {row['id'] for row in in_force(connection, timeline_id)}
        conflicts = many(connection, "SELECT self_facts.* FROM self_facts JOIN messages ON messages.id=message_id "
                         "WHERE self_facts.status='conflict' AND messages.timeline_id=? AND messages.active=1",
                         (timeline_id,))
        rows = [row for row in in_force(connection, timeline_id) if row['id'] in active] + conflicts
        return {'facts': [view(row) for row in sorted(rows, key=lambda row: row['created_at'])]}


def decide(database, fact_id: str, keep: bool) -> dict:
    """Keep or remove a noted fact. Keeping a conflicting fact removes the one it contradicts."""
    timestamp = database.now()
    with database.connect(write=True) as connection:
        row = one(connection, 'SELECT * FROM self_facts WHERE id=?', (fact_id,))
        require(row['status'] != 'rejected' or keep, 'This was already removed.', 409)
        connection.execute('UPDATE self_facts SET status=?, decided_at=? WHERE id=?',
                           ('kept' if keep else 'rejected', timestamp, fact_id))
        if keep and row['conflicts_with']:
            connection.execute("UPDATE self_facts SET status='rejected', decided_at=? WHERE id=?",
                               (timestamp, row['conflicts_with']))
        if not keep:
            # Whatever waited on this one no longer contradicts anything.
            connection.execute("UPDATE self_facts SET status='noted', conflicts_with=NULL WHERE conflicts_with=? "
                               "AND status='conflict'", (fact_id,))
        stamp_change(connection, timestamp)
    return listing(database)


def stamp_change(connection, timestamp):
    """Tastes shape upcoming plans: the companion's precomputed week is rebuilt from now."""
    companion = require_current(connection)
    connection.execute("DELETE FROM life_agenda WHERE timeline_id=? AND subject='companion' AND status='upcoming' "
                       'AND starts_at>?', (companion['active_timeline_id'], timestamp))
    connection.execute("UPDATE agenda_cursors SET through=MIN(through, ?) WHERE timeline_id=? AND subject='companion'",
                       (timestamp, companion['active_timeline_id']))


def tastes(connection, timeline_id) -> dict:
    """The companion's own stated likes and dislikes, for the composer's leanings."""
    result = {'likes': [], 'dislikes': []}
    for row in in_force(connection, timeline_id):
        if row['category'] in result:
            result[row['category']].append(row['subject'])
    return result


def context_line(row: dict) -> str:
    confirmed = ' (confirmed)' if row['status'] == 'kept' else ''
    if row['category'] in {'person', 'pet'}:
        return f"- Your {row['subject']} is named {row['value']}{confirmed}."
    if row['category'] == 'favorite':
        return f"- Your favorite {row['subject']}: {row['value']}{confirmed}."
    if row['category'] == 'never':
        return f"- You have never {row['subject']}{confirmed}."
    return f"- {LABELS[row['category']]}: {row['value']}{confirmed}."


def context_lines(connection, timeline_id) -> list[tuple[str, str]]:
    return [(row['id'], context_line(row)) for row in in_force(connection, timeline_id)]

