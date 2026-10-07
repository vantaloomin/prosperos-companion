"""Model-proposed memory suggestions (PRD M1, M7): optional, background-only and never committed alone.

When the user turns on model suggestions (with automatic memory), the sentences of each message the
rules found nothing in are sent in small batches to the configured model at maintenance priority. Its answers are
only candidates: each must name a message in the batch and use that message's own words, then it
waits as a suggestion the user keeps or declines. A model guess never becomes a fact on its own,
and repeating a guess does not confirm it.
"""
import json

from companion import prompt_library
from companion.characters import require_current
from companion.database import encode, identifier, many, optional, settings
from companion.memory import formation
from companion.memory.extraction import Candidate, sentences, subject_key
from companion.memory.retrieval import terms
from companion.providers.chat import INCOMPLETE
from companion.providers.scheduling import MAINTENANCE, BackgroundInterrupted
from companion.text_models import config_for

PROMPT_VERSION = 'memory-suggest-1'
BATCH = 8
MIN_WORDS = 6
SUPPORT = 0.6
LAYERS = {'user_fact', 'plan', 'temporary', 'shared_experience', 'relationship'}
RULES = (
    'You help a companion app remember what the user said about their real life. The user message is a JSON '
    'list of the user\'s messages, numbered. Reply with JSON only: a list of objects {"message": number, '
    '"layer": "user_fact" | "plan" | "temporary" | "shared_experience" | "relationship", "subject": short '
    'label, "value": the fact in the user\'s own words}. Include only facts the user states plainly about '
    'themselves. Leave out questions, hypotheticals, jokes, roleplay, quotes of other people and anything you '
    'would have to guess. Reply [] when there is nothing.'
)


class SuggestionsInvalid(Exception):
    pass


def pending(connection, limit=BATCH) -> list[dict]:
    """Finished jobs the model has not seen, each with only the sentences the rules found nothing in:
    "I'm allergic to shellfish. I'm Sam." keeps "I'm Sam." for the model."""
    rows = many(connection, "SELECT messages.* FROM memory_jobs JOIN messages ON messages.id=memory_jobs.message_id "
                "WHERE memory_jobs.status='done' AND memory_jobs.model_status IS NULL AND messages.redacted_at IS NULL "
                'ORDER BY memory_jobs.queued_at LIMIT ?', (limit,))
    return [{**row, 'text': unhandled(connection, row)} for row in rows]


def unhandled(connection, message) -> str:
    handled = {json.loads(row['proposal']).get('excerpt') for row in many(
        connection, 'SELECT proposal FROM memory_candidates WHERE message_id=?', (message['id'],))}
    if not handled:
        return message['text']
    return ' '.join(f'{sentence}.' for sentence in sentences(message['text']) if sentence not in handled)


def eligible(message) -> bool:
    return len(message['text'].split()) >= MIN_WORDS and bool(sentences(message['text']))


def parse(text: str) -> list[dict]:
    start, end = text.find('['), text.rfind(']')
    if start < 0 or end < start:
        raise SuggestionsInvalid()
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError as error:
        raise SuggestionsInvalid() from error
    if not isinstance(data, list):
        raise SuggestionsInvalid()
    return [item for item in data if isinstance(item, dict)]


def supported(value: str, message_text: str) -> bool:
    """Most of the value's words must come from the message itself, so the model cannot add facts."""
    words, source = set(terms(value)), set(terms(message_text))
    return bool(words) and len(words & source) / len(words) >= SUPPORT


def candidate(item, batch) -> tuple[dict, Candidate] | None:
    index, layer = item.get('message'), item.get('layer')
    subject, value = str(item.get('subject') or '').strip()[:200], str(item.get('value') or '').strip()[:1000]
    if not isinstance(index, int) or not 1 <= index <= len(batch) or layer not in LAYERS or not subject or not value:
        return None
    message = batch[index - 1]
    if not supported(value, message['text']) or not sentences(message['text']):
        return None
    return message, Candidate(layer, subject, value, 'model', message['text'][:500], subject_key=subject_key(subject),
                              plan_status='proposed' if layer == 'plan' else None)


async def ask(provider, scheduler, config, key, batch, rules=RULES) -> list[dict]:
    content = json.dumps([{'message': index, 'text': message['text']} for index, message in enumerate(batch, 1)],
                         ensure_ascii=False)
    text = []
    async with scheduler.reserve(config, MAINTENANCE) as lease:
        async for chunk in provider.stream(config, key, rules, [{'role': 'user', 'content': content}]):
            if lease.stop.is_set():
                raise BackgroundInterrupted()
            text.append(chunk.text)
            if chunk.finish_reason in INCOMPLETE:
                raise SuggestionsInvalid()
    return parse(''.join(text))


def mark(connection, batch, status):
    connection.executemany('UPDATE memory_jobs SET model_status=? WHERE message_id=?',
                           [(status, message['id']) for message in batch])


def record(database, batch, items, revision) -> int:
    """Store supported candidates as suggestions, unless permissions changed while the model worked."""
    with database.connect(write=True) as connection:
        row, timestamp = settings(connection), database.now()
        if not (row['automatic_memory'] and row['model_memory_suggestions']) or row['permission_revision'] != revision:
            mark(connection, batch, 'stale')
            return 0
        companion, added = require_current(connection), 0
        for found in filter(None, (candidate(item, batch) for item in items)):
            added += store(connection, companion, *found, timestamp)
        mark(connection, batch, 'done')
        return added


def store(connection, companion, message, found, timestamp) -> int:
    current = optional(connection, 'SELECT * FROM messages WHERE id=?', (message['id'],))
    if current is None or formation.blocked(connection, current):
        return 0
    mark_value = formation.fingerprint(found)
    declined = optional(connection, "SELECT 1 FROM memory_candidates WHERE fingerprint=? AND status='declined'",
                        (mark_value,))
    duplicate = optional(connection, "SELECT 1 FROM memories WHERE companion_id=? AND status='active' AND "
                         'subject_key=? AND lower(value)=lower(?)', (companion['id'], found.subject_key, found.value))
    if declined or duplicate:
        return 0
    cursor = connection.execute(
        'INSERT OR IGNORE INTO memory_candidates (id, companion_id, timeline_id, message_id, source, rule, proposal, '
        "fingerprint, status, reason, created_at) VALUES (?, ?, ?, ?, 'model', ?, ?, ?, 'pending', 'model_guess', ?)",
        (identifier(), companion['id'], current['timeline_id'], current['id'], PROMPT_VERSION,
         encode(formation.proposal(found, current)), mark_value, timestamp))
    formation.log(connection, timestamp, 'suggested', message_id=current['id'], detail='model_guess')
    return cursor.rowcount


async def suggest(database, provider, scheduler, vault_key) -> int:
    """One batch. Returns how many messages were handled (0 when there is nothing to do)."""
    with database.connect(write=True) as connection:
        row = settings(connection)
        config = config_for(connection, 'memory')
        if not (row['automatic_memory'] and row['model_memory_suggestions']) or config is None:
            return 0
        batch = pending(connection)
        skipped = [message for message in batch if not eligible(message)]
        mark(connection, skipped, 'skipped')
        batch = [message for message in batch if eligible(message)]
        revision = row['permission_revision']
        rules = prompt_library.text(connection, 'memory-suggestions')
    if not batch:
        return len(skipped)
    try:
        items = await ask(provider, scheduler, config, vault_key(config), batch, rules)
    except SuggestionsInvalid:
        with database.connect(write=True) as connection:
            mark(connection, batch, 'failed')
        return len(batch) + len(skipped)
    record(database, batch, items, revision)
    return len(batch) + len(skipped)
