"""The memory model reads the companion's replies for what they say about themselves (realism: her own facts).

The rules in companion/self_facts.py catch "my sister Ashley" but not "we're the Harbor Hellions" said in answer
to "what's your derby team called?", so in the six-month test the team's name drifted from month to month.
With model memory on, each completed companion message is queued here and sent in small batches, with the
message it answered, to the memory model at maintenance priority. Each answer must name a message in the batch
and use that message's own words; it is then noted like a rule-found fact (`self_facts.record`), so a different
value for something on record waits as a conflict instead of replacing it.
"""
import json
import re

from companion import in_character, prompt_library, self_facts
from companion.characters import require_current
from companion.database import many, optional, settings
from companion.memory.suggest import SuggestionsInvalid, parse, supported
from companion.providers.chat import INCOMPLETE
from companion.providers.scheduling import MAINTENANCE, BackgroundInterrupted
from companion.text_models import config_for

BATCH = 8
MIN_WORDS = 4
# "my mom" without a name: nothing to keep the same.
NOT_PERSON_NAMES = set(self_facts.RELATIVES) | set(self_facts.NOT_LOWER_NAMES) | {'friend', 'coworker', 'neighbor'}
PLAYABLE = set(self_facts.SPORTS + self_facts.INSTRUMENTS + self_facts.POSITIONS)
# Details the character definition and the life sim already hold.
NOT_DETAILS = {'profession', 'job', 'work', 'occupation', 'career', 'name', 'age', 'city', 'mood', 'feeling'}
FIXED_SUBJECTS = {'team': 'team', 'works_at': 'workplace', 'grew_up': 'hometown'}
CATEGORIES = {'person', 'pet', 'team', 'works_at', 'grew_up', 'plays', 'favorite', 'likes', 'dislikes', 'allergy',
              'detail'}
# Written for str.format: {name} is the companion's name, doubled braces are literal.
RULES = (
    'You help a companion app keep a fictional character, {name}, consistent. The user message is a JSON list of '
    'numbered messages {name} sent, each with the message it answered ("answering"). Reply with JSON only: a list '
    'of objects {{"message": number, "category": "person" | "pet" | "team" | "works_at" | "grew_up" | "plays" | '
    '"favorite" | "likes" | "dislikes" | "allergy" | "detail", "subject": short label, "value": the fact in '
    "{name}'s own words}}. Include only lasting facts {name} states plainly about their own life: the people in it "
    'by name, with the subject saying who they are to {name} ("sister", "coworker", "best friend"); pets (subject '
    'the animal, value its name); the team {name} is on (value the team name); the named place {name} works (not the '
    'job itself, which the app knows) and where {name} grew up; what {name} plays; favorites (subject what kind, like "band"); clear likes, dislikes and allergies; and other details '
    'that must stay the same later ("detail", subject like "car" or "tattoo"). "we\'re the Harbor Hellions" '
    'answering "what\'s your derby team called?" is {{"message": 1, "category": "team", "subject": "team", '
    '"value": "Harbor Hellions"}}; "my sister jo plays derby too" is {{"category": "person", "subject": "sister", '
    '"value": "Jo"}}. Leave out anything about the person {name} is texting: when "answering" asks about their life, people '
    'or pets ("what\'s my dog\'s name?", "who\'s due in december?"), the names in the answer are theirs, '
    "not {name}'s. Also leave out compliments, moods, plans, jokes, "
    'questions, hypotheticals and anything you would have to guess. Reply [] when there is nothing.'
)


def on(row) -> bool:
    return bool(row['automatic_memory'] and row['model_memory_suggestions'])


def queue(connection, message: dict, timestamp: str):
    """Queue a completed companion message for the model while model memory is on."""
    if on(settings(connection)) and len(message['text'].split()) >= MIN_WORDS:
        connection.execute("INSERT OR IGNORE INTO self_fact_jobs (message_id, status, queued_at) "
                           "VALUES (?, 'queued', ?)", (message['id'], timestamp))


def pending(connection, limit=BATCH) -> tuple[list[dict], int]:
    """Queued messages still shown, each with the text of the message it answered, and how many were skipped
    because their message was replaced, withheld or redacted, or answers an OOC question."""
    rows = many(connection, "SELECT messages.*, asked.text AS answering FROM self_fact_jobs "
                'JOIN messages ON messages.id=self_fact_jobs.message_id '
                'LEFT JOIN messages AS asked ON asked.id=messages.reply_to '
                "WHERE self_fact_jobs.status='queued' ORDER BY self_fact_jobs.queued_at LIMIT ?", (limit,))
    # An out-of-character answer is the model talking about the app, not the character.
    gone = [row for row in rows if row['status'] != 'complete' or not row['active'] or row['redacted_at']
            or in_character.out_of_character(row['answering'] or '')]
    mark(connection, gone, 'skipped')
    return [row for row in rows if row not in gone], len(gone)


def mark(connection, batch, status):
    connection.executemany('UPDATE self_fact_jobs SET status=? WHERE message_id=?',
                           [(status, message['id']) for message in batch])


def rejected(category: str, subject: str, value: str) -> bool:
    """Answers that are not a fact to keep the same: "my mom" with no name, "i can't play a note", her job
    ("nursing", "the er") as a workplace, a detail the definition holds, a reaction as a taste."""
    lowered = value.lower()
    if category == 'person':
        return lowered in NOT_PERSON_NAMES or lowered == self_facts.SAME.get(subject, subject)
    if category == 'plays':
        return lowered not in PLAYABLE
    if category == 'detail':
        return subject in NOT_DETAILS
    if category == 'works_at':
        return len(value.split()) < 2 and value.islower()
    return category in {'likes', 'dislikes'} and not self_facts.taste(value)


def fact(item, batch) -> tuple[dict, self_facts.Fact] | None:
    """A supported answer as a fact keyed like the rules key it, so both kinds meet in one ledger."""
    index, category = item.get('message'), item.get('category')
    subject = re.sub(r'\s+', ' ', str(item.get('subject') or '')).strip().lower()[:40]
    value = re.sub(r'^(?:the|a|an|my) ', '', str(item.get('value') or '').strip().strip('"\'“”.!'), flags=re.I)[:50]
    if not isinstance(index, int) or not 1 <= index <= len(batch) or category not in CATEGORIES or not value:
        return None
    message = batch[index - 1]
    if not supported(value, message['text']):
        return None
    if value.islower() and category in {'person', 'pet', 'team'}:
        value = self_facts.titled(value)
    statement = next((sentence for sentence in self_facts.SENTENCE.findall(message['text'])
                      if value.lower() in sentence.lower()), message['text']).strip()
    if rejected(category, subject, value):
        return None
    if category == 'person':
        subject = self_facts.SAME.get(subject, subject)
    elif category in FIXED_SUBJECTS:
        subject = FIXED_SUBJECTS[category]
    elif category in {'likes', 'dislikes', 'allergy', 'plays'}:
        subject = value.lower()
    if not subject:
        return None
    return message, self_facts.Fact(category, subject, value, statement)


async def ask(provider, scheduler, config, key, batch, rules) -> list[dict]:
    content = json.dumps([{'message': index, 'text': message['text'],
                           **({'answering': message['answering']} if message.get('answering') else {})}
                          for index, message in enumerate(batch, 1)], ensure_ascii=False)
    text = []
    async with scheduler.reserve(config, MAINTENANCE) as lease:
        async for chunk in provider.stream(config, key, rules, [{'role': 'user', 'content': content}]):
            if lease.stop.is_set():
                raise BackgroundInterrupted()
            text.append(chunk.text)
            if chunk.finish_reason in INCOMPLETE:
                raise SuggestionsInvalid()
    return parse(''.join(text))


def user_names(connection, companion_id) -> set[str]:
    """Capitalised words in the values of the user's active memories: a name there is the user's person or pet, so her answer
    to "what's my dog's name?" is not her own dog."""
    rows = many(connection, "SELECT value FROM memories WHERE companion_id=? AND status='active'", (companion_id,))
    return {word.casefold() for row in rows for word in re.findall(r"\b[A-Z][\w'’-]+", row['value'])}


def record(database, batch, items) -> int:
    """Note the supported facts, unless model memory was turned off while the model worked."""
    with database.connect(write=True) as connection:
        if not on(settings(connection)):
            mark(connection, batch, 'stale')
            return 0
        companion, timestamp, added = require_current(connection), database.now(), 0
        theirs = user_names(connection, companion['id'])
        found = {}
        for message, new in filter(None, (fact(item, batch) for item in items)):
            if new.category in {'person', 'pet'} and new.value.casefold() in theirs:
                continue
            found.setdefault(message['id'], (message, []))[1].append(new)
        for message, facts in found.values():
            current = optional(connection, 'SELECT * FROM messages WHERE id=?', (message['id'],))
            if current is not None:
                added += len(self_facts.record(connection, companion, current, facts, timestamp))
        mark(connection, batch, 'done')
        return added


async def suggest(database, provider, scheduler, vault_key) -> int:
    """One batch. Returns how many messages were handled (0 when there is nothing to do)."""
    with database.connect(write=True) as connection:
        config = config_for(connection, 'memory')
        if not on(settings(connection)) or config is None:
            return 0
        batch, skipped = pending(connection)
        companion = require_current(connection)
        rules = prompt_library.text(connection, 'self-facts', name=companion['version']['definition'].get('name')
                                    or 'the character')
    if not batch:
        return skipped
    try:
        items = await ask(provider, scheduler, config, vault_key(config), batch, rules)
    except SuggestionsInvalid:
        with database.connect(write=True) as connection:
            mark(connection, batch, 'failed')
        return len(batch) + skipped
    record(database, batch, items)
    return len(batch) + skipped
