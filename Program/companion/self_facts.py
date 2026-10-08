"""What the companion has said about themselves (realism: an LLM must not flip its own facts).

Rules first: after each completed companion message, first-person statements
about their own tastes, people, pets, history, team and work ("I hate cilantro", "my brother Theo",
"I've never been to Europe", "I grew up in Duluth", "i play blocker") are noted with the sentence
they came from. With model memory on, the memory model later reads the same message for what the
rules miss (companion/memory/self_suggest.py), and its facts are noted the same way. Noted facts go
into the chat context so later replies stay consistent, and the user can keep or remove each one in Character Studio. A new statement that contradicts one already on
record waits as a conflict instead of quietly replacing it. A companion who texts in lowercase
writes names in lowercase too ("my cat juniper"), so in lowercase text a plain word after "my cat"
counts as a name unless it is a common word ("my cat is sleeping").

These are fiction about the character, never facts about the user (M1). They are separate from the
character definition (C1), so a deliberate edit still applies from a stated point. A fact belongs to
the message it came from: it applies on every timeline that holds that message or a copy of it, and
stops applying when that reply is replaced by another version or deleted.
"""
import re
from dataclasses import dataclass

from companion import self_checks, texting
from companion.characters import for_timeline, require_current
from companion.database import identifier, many, one, optional
from companion.errors import require
from companion.memory.extraction import CLAUSE_END, HYPOTHETICAL, NOT_THINGS, QUESTION_START, QUOTED, SENTENCE
from companion.memory.people_rules import NOT_NAMES, RELATIONS

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
SPORTS = ('roller derby', 'derby', 'soccer', 'softball', 'baseball', 'basketball', 'football', 'hockey', 'volleyball',
          'rugby', 'lacrosse', 'netball', 'cricket', 'water polo', 'ultimate frisbee', 'ultimate', 'tennis', 'golf',
          'badminton', 'pickleball', 'squash', 'chess', 'poker', 'bowling', 'curling', 'kickball', 'dodgeball')
INSTRUMENTS = ('piano', 'guitar', 'bass', 'cello', 'violin', 'viola', 'drums', 'ukulele', 'flute', 'clarinet',
               'saxophone', 'sax', 'trumpet', 'trombone', 'french horn', 'tuba', 'harp', 'banjo', 'mandolin', 'oboe',
               'accordion', 'keyboard', 'harmonica')
POSITIONS = ('blocker', 'jammer', 'pivot', 'goalie', 'goalkeeper', 'keeper', 'striker', 'defender', 'midfielder',
             'forward', 'center', 'centre', 'point guard', 'guard', 'pitcher', 'catcher', 'shortstop', 'first base',
             'second base', 'third base', 'outfield', 'quarterback', 'linebacker', 'setter', 'libero', 'winger',
             'fullback', 'left wing', 'right wing', 'defense', 'defence')
PLAYABLE = '|'.join(sorted(SPORTS + INSTRUMENTS + POSITIONS, key=len, reverse=True))
TEAM_SPORT = rf"(?:(?:{'|'.join(SPORTS)}|trivia|quiz|rowing|swim|track) )?"
TEAM = r"([\w'’&-]+(?: [\w'’&-]+){0,3})"
# Words that end a team name: "the crabshells and we won".
TEAM_END = {'and', 'are', 'is', 'was', 'were', 'who', 'we', 'but', 'so', 'just', 'won', 'lost', 'play', 'played',
            'have', 'had', 'this', 'last', 'next', 'tonight', 'today', 'tomorrow', 'in', 'at', 'on', 'for', 'with',
            'lol', 'haha'}
LOWER_NAME = r"([a-z][\w'’-]+)"
# Words that follow "my cat" or "my sister" in lowercase text without being a name ("my dog just ate").
NOT_LOWER_NAMES = NOT_NAMES | NOT_THINGS | TEAM_END | set(RELATIONS) | set(RELATIVES) | set(PETS) | {
    'sat', 'bit', 'ran', 'fell', 'hit', 'let', 'put', 'saw', 'met', 'found', 'left', 'kept', 'slept', 'woke', 'threw',
    'broke', 'bought', 'brought', 'caught', 'sold', 'drove', 'wrote', 'chose', 'knew', 'got', 'made', 'ate', 'drank',
    'snores', 'sleeps', 'barks', 'bites', 'runs', 'cries', 'needs', 'gives', 'helps', 'hides', 'visits', 'visited',
    'yells', 'refuses', 'swears', 'sits', 'stays', 'sounds', 'looks', 'seems', 'feels', 'means', 'probably',
    'has', 'gets', 'got', 'will', 'would', 'can', 'could', 'should', 'does', 'did', 'do', 'which', 'from', 'to',
    'of', 'too', 'still', 'always', 'never', 'sometimes', 'usually', 'finally', 'already', 'even', 'now', 'omg',
    'ugh', 'me', 'us', 'all', 'both', 'like', 'because', 'if', 'when', 'where', 'what', 'how', 'why', 'not', 'ate',
    'said', 'says', 'calls', 'called', 'named', 'texts', 'texted', 'loves', 'hates', 'likes', 'wants', 'thinks',
    'knows', 'lives', 'works', 'keeps', 'makes', 'misses', 'sent', 'went', 'came', 'comes', 'goes', 'took', 'made',
    'told', 'tells', 'asked', 'asks', 'gave', 'died', 'passed', 'sleeps', 'eats', 'used', 'back', 'again', 'here',
    'home', 'over', 'every', 'one', 'lately', 'literally', 'basically', 'really', 'totally', 'actually', 'never'}
NOT_WORKPLACES = {'home', 'night', 'nights', 'the moment', 'moment', 'all', 'all hours', 'it', 'that', 'this'}


def kin(relations, name):
    return rf"\bmy ({'|'.join(relations)}),? (?:is |was )?(?:named |called )?{name}"


def kin_lowercase(relations):
    # "is" and "was" only before "named" or "called": "my mom was mad" names nobody.
    return rf"\bmy ({'|'.join(relations)}),? (?:(?:is |was )?(?:named|called) )?{LOWER_NAME}"


RULES = (
    ('likes', re.compile(rf"\bi {LIKE}(?:love|adore|like|enjoy)\s+{THING}", re.IGNORECASE)),
    ('dislikes', re.compile(rf"\bi {LIKE}(?:hate|loathe|dislike|can'?t stand|cannot stand|don'?t like|do not like)"
                            rf"\s+{THING}", re.IGNORECASE)),
    ('favorite', re.compile(r"\bmy (?:all-time |absolute )?favou?rite ([a-z]+(?: [a-z]+)?) (?:is|has to be|was) "
                            rf"{THING}", re.IGNORECASE)),
    ('person', re.compile(kin(RELATIVES, NAME), re.IGNORECASE)),
    ('pet', re.compile(kin(PETS, NAME), re.IGNORECASE)),
    ('never', re.compile(r"\bi(?:'ve| have) never (been to|tried|seen|read|watched|played|eaten|had|ridden|learned)"
                         rf"\s+{THING}", re.IGNORECASE)),
    ('grew_up', re.compile(r"\bi grew up (?:in|on|near|outside(?: of)?) " r"(?-i:([A-Z][\w.'’-]*(?: [A-Z][\w.'’-]*)*))",
                           re.IGNORECASE)),
    ('allergy', re.compile(rf"\bi(?:'m| am) allergic to {THING}", re.IGNORECASE)),
    ('team', re.compile(rf"\bmy {TEAM_SPORT}team(?:,| is| was|) (?:the|called|named) {TEAM}|"
                        rf"\bi (?:also |still )?play for the {TEAM}", re.IGNORECASE)),
    ('plays', re.compile(rf"\bi (?:also |still |mostly |usually )?play (?:the |as (?:a |an |the )?)?({PLAYABLE})\b",
                         re.IGNORECASE)),
    ('works_at', re.compile(rf"\bi (?:still |currently )?work(?: (?:in|on) [^,.;!?]{{2,30}}?)? at {THING}",
                            re.IGNORECASE)),
)
# In lowercase text the person and pet rules also take a lowercase name.
LOWERCASE_RULES = {'person': re.compile(kin_lowercase(RELATIVES), re.IGNORECASE),
                   'pet': re.compile(kin_lowercase(PETS), re.IGNORECASE)}
# Categories with one current answer: a second team or workplace is a contradiction.
SINGLE = {'favorite', 'grew_up', 'person', 'team', 'works_at'}
LABELS = {'likes': 'Likes', 'dislikes': 'Dislikes', 'favorite': 'Favorite', 'person': 'Person', 'pet': 'Pet',
          'never': 'Never', 'grew_up': 'Grew up', 'allergy': 'Allergic to', 'team': 'Team', 'plays': 'Plays',
          'works_at': 'Works at', 'detail': 'Detail'}
STATUSES = ('noted', 'kept', 'rejected', 'conflict')
IN_FORCE = ('noted', 'kept')
# Objects that are the conversation, not a taste ("I love that", "I like talking to you").
NOT_TASTES = NOT_THINGS | {'it here', 'that too', 'this too', 'the idea', 'your', 'how you', 'when you', 'the way you',
                           'hearing', 'hearing that', 'that you', 'what you', 'having you', 'you too', 'us'}
# First words of a "liked" object that make it about the moment, not a taste.
NOT_TASTE_STARTS = {'you', 'your', 'it', 'that', 'this', 'these', 'those', 'how', 'what', 'when', 'where', 'why', 'who',
                    'almost', 'about', 'as', 'so', 'too', 'being', 'seeing', 'hearing', 'having', 'everything',
                    'anything', 'nothing', 'all', 'both', 'dedication', 'idea', 'sound', 'thought', 'energy', 'vibe',
                    'way', 'enthusiasm', 'commitment', 'effort', 'one', 'them', 'him', 'her', 'us', 'me', 'myself', 'yours', 'reading', 'getting', 'knowing'}


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


def titled(text: str) -> str:
    return ' '.join(word[:1].upper() + word[1:] for word in text.split())


def lowercase_style(text: str) -> bool:
    """Texted in lowercase: some sentence starts lowercase and no word is capitalised but "I" and sentence starts."""
    sentences = [part.split() for part in SENTENCE.findall(text) if part.strip()]
    starts = [words[0] for words in sentences]
    later = [word for words in sentences for word in words[1:]]
    return any(word[:1].islower() for word in starts) and not any(
        word[:1].isupper() and not re.match(r"I(?:['’]\w+)?\W*$", word) for word in later)


def named_fact(category: str, groups: list[str], sentence: str, lowercase: bool) -> Fact | None:
    relation, name = groups[0].lower(), groups[1]
    if lowercase:
        if name.lower() in NOT_LOWER_NAMES or re.search(r"(?:ing|ed|ly|n['’]t)$", name.lower()):
            return None
        name = titled(name)
    return Fact(category, SAME.get(relation, relation) if category == 'person' else relation, name, sentence)


def life_fact(category: str, groups: list[str], sentence: str) -> Fact | None:
    """Their team, what they play and where they work."""
    if category == 'team':
        words = groups[0].split()
        ends = [index for index, word in enumerate(words) if word.lower() in TEAM_END]
        team = ' '.join(words[:ends[0]] if ends else words)
        return Fact('team', 'team', titled(team) if team.islower() else team, sentence) if team else None
    if category == 'plays':
        return Fact('plays', groups[0].lower(), groups[0].lower(), sentence)
    place = re.sub(r'\s+(?:as|now|today|tonight|tomorrow|until|till|every|most|during|on|lol|haha)\b.*$', '',
                   clean(groups[-1]), flags=re.IGNORECASE)
    if not place[:1].isalpha() or place.lower() in NOT_WORKPLACES:
        return None
    return Fact('works_at', 'workplace', place, sentence)


def fact_for(category: str, match, sentence: str, lowercase=False) -> Fact | None:
    groups = [group for group in match.groups() if group]
    if category in {'person', 'pet'}:
        return named_fact(category, groups, sentence, lowercase)
    if category in {'team', 'plays', 'works_at'}:
        return life_fact(category, groups, sentence)
    if category == 'favorite':
        thing = clean(groups[1])
        return Fact('favorite', groups[0].lower(), thing, sentence) if thing else None
    if category == 'never':
        thing = clean(groups[1])
        return Fact('never', f'{groups[0].lower()} {thing.lower()}', thing, sentence) if thing else None
    if category == 'grew_up':
        return Fact('grew_up', 'hometown', groups[0].rstrip('.'), sentence)
    thing = clean(groups[0])
    if not taste(thing):
        return None
    return Fact(category, thing.lower(), thing, sentence)


def taste(thing: str) -> bool:
    """A thing someone can like: "hiking", "the vibe of the games". Not a reaction to the conversation ("this for
    you", "the dedication"), a comparison ("almost as much") or half a sentence."""
    words = thing.lower().split()
    return bool(words) and thing.lower() not in NOT_TASTES and words[0] not in NOT_TASTE_STARTS and len(words) <= 5 \
        and all(re.fullmatch(r"[\w'’&-]+", word) for word in words)


def extract(text: str, lowercase=False) -> list[Fact]:
    """First-person statements in one companion message. Questions, hypotheticals and quoted lines are skipped.
    In lowercase text (or for a companion who texts in lowercase) names may be lowercase too."""
    text = QUOTED.sub(' ', ACTIONS.sub(' ', text))
    lowercase = lowercase or lowercase_style(text)
    rules = RULES + tuple(LOWERCASE_RULES.items()) if lowercase else RULES
    found, seen = [], set()
    for sentence in (part.strip() for part in SENTENCE.findall(text)):
        if not sentence or sentence.endswith('?') or QUESTION_START.match(sentence) or HYPOTHETICAL.search(sentence):
            continue
        if re.search(r"\b(?:wish|if only|maybe|might|probably)\b", sentence, re.IGNORECASE):
            continue
        for index, (category, pattern) in enumerate(rules):
            for match in pattern.finditer(sentence):
                fact = fact_for(category, match, sentence, index >= len(RULES))
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
    rows = many(connection, "SELECT self_facts.*, messages.reply_to AS reply_to, messages.id AS shown_id FROM "
                "self_facts JOIN messages ON (messages.id=self_facts.message_id OR "
                "messages.origin_id=self_facts.message_id) WHERE self_facts.status IN ('noted', 'kept') "
                "AND messages.timeline_id=? AND messages.active=1 AND messages.status='complete' "
                'AND messages.redacted_at IS NULL ORDER BY self_facts.created_at', (timeline_id,))
    return shown(connection, timeline_id, rows)


def shown(connection, timeline_id, rows: list[dict]) -> list[dict]:
    """Rows joined to their shown message (`shown_id`, `reply_to`), once each, leaving out those whose
    message or the message it answers is blocked or redacted."""
    from companion.memory.records import blocked_messages
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
        if row['category'] == fact.category and row['subject'] == fact.subject and not \
                same_value(row['value'], fact.value) and fact.category in SINGLE and (
                    fact.category != 'person' or fact.subject in ONE_OF):
            return row
    return None


# The circle's roles for a relative: "parent" and "sibling" when it was built without city data or pronouns.
FAMILY = {'mom': ('mom', 'parent'), 'mother': ('mom', 'parent'), 'dad': ('dad', 'parent'),
          'father': ('dad', 'parent'), 'sister': ('sister', 'sibling'), 'brother': ('brother', 'sibling')}
CIRCLE = 'circle:'


def first_name(name: str) -> str:
    return (name.split() or [''])[0].casefold()


def family_clash(connection, timeline_id, fact: Fact, definition: dict) -> dict | None:
    """The circle's mom, dad, sister or brother when a stated name matches none of the circle's people in that role.
    The circle is what the companion's feed, diary and storylines are built from, so a new name for their mom
    from one reply would otherwise sit beside Cathy in every later context. A name the definition gives is fine."""
    if fact.category != 'person' or not (roles := FAMILY.get(fact.subject.split()[-1])):
        return None
    family = many(connection, "SELECT id, name FROM circle_people WHERE timeline_id=? AND role IN (?, ?) "
                  "AND status='active' ORDER BY ordinal", (timeline_id, *roles))
    if not family or first_name(fact.value) in {first_name(row['name']) for row in family}:
        return None
    written = ' '.join(str(value) for value in definition.values() if isinstance(value, str))
    if re.search(rf"\b{re.escape(fact.value)}\b", written, re.IGNORECASE):
        return None
    return family[0]


def note(connection, message: dict, timestamp: str) -> list[dict]:
    """Record what one completed companion message says about the character. Idempotent per message.
    The message also waits for the memory model to read (companion/memory/self_suggest.py)."""
    if message['role'] != 'companion' or message['status'] != 'complete':
        return []
    # A companion out of focus may text first too (companion/life/openers.py); the message says whose it is.
    companion = for_timeline(connection, message['timeline_id']) or require_current(connection)
    from companion.memory import self_suggest
    self_suggest.queue(connection, message, timestamp)
    return record(connection, companion, message,
                  extract(message['text'], texting.style(companion['version']['definition'])['lowercase']), timestamp)


def same_value(old: str, new: str) -> bool:
    """The same name said shorter or longer: "the Blast" for "Baltimore Blast", "Harbor Hellions" for "Hellions"."""
    old_words, new_words = set(old.casefold().split()), set(new.casefold().split())
    return old_words <= new_words or new_words <= old_words


def record(connection, companion: dict, message: dict, facts: list[Fact], timestamp: str) -> list[dict]:
    """Note facts from one message, each as a conflict when it contradicts what is on record."""
    current = in_force(connection, message['timeline_id'])
    known = {row['key']: row for row in current}
    added = []
    for fact in facts:
        if fact.key in known and same_value(known[fact.key]['value'], fact.value):
            continue
        clash = contradiction(fact, current)
        definition = companion['version']['definition']
        if clash is None and (relative := family_clash(connection, message['timeline_id'], fact, definition)):
            clash = {'id': f"{CIRCLE}{relative['id']}"}
        # Something the user said was wrong, or the definition says otherwise (companion/self_checks.py).
        if clash is None and (reason := self_checks.earlier_dispute(connection, message['timeline_id'], fact.key,
                                                                    fact.value) or
                              self_checks.definition_clash(fact, definition)):
            clash = {'id': reason}
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


def view(row: dict, connection=None) -> dict:
    result = {key: row[key] for key in ('id', 'message_id', 'category', 'subject', 'value', 'statement', 'status',
                                        'conflicts_with', 'created_at', 'decided_at')} | {'label': LABELS[row['category']]}
    if connection is not None and row['status'] == 'conflict' and (row['conflicts_with'] or '').startswith(CIRCLE):
        person = optional(connection, 'SELECT name, role FROM circle_people WHERE id=?',
                          (row['conflicts_with'].removeprefix(CIRCLE),))
        if person:
            result['circle_person'] = f"{person['role']} {person['name']}"
    elif connection is not None and row['status'] == 'conflict':
        result |= self_checks.reason(connection, row['conflicts_with'])
    return result


def listing(database) -> dict:
    with database.connect() as connection:
        companion = require_current(connection)
        timeline_id = companion['active_timeline_id']
        active = {row['id'] for row in in_force(connection, timeline_id)}
        conflicts = many(connection, "SELECT self_facts.* FROM self_facts JOIN messages ON messages.id=message_id "
                         "WHERE self_facts.status='conflict' AND messages.timeline_id=? AND messages.active=1",
                         (timeline_id,))
        rows = [row for row in in_force(connection, timeline_id) if row['id'] in active] + conflicts
        return {'facts': [view(row, connection) for row in sorted(rows, key=lambda row: row['created_at'])]}


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
    if row['category'] == 'detail':
        return f"- Your {row['subject']}: {row['value']}{confirmed}."
    return f"- {LABELS[row['category']]}: {row['value']}{confirmed}."


def context_lines(connection, timeline_id) -> list[tuple[str, str]]:
    return [(row['id'], context_line(row)) for row in in_force(connection, timeline_id)]

