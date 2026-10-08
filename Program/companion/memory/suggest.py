"""Model-found memories (PRD M1, M7): background-only, saved like rule-found facts.

With model memory on (with automatic memory; both on by default since 2026-10-07), the sentences of each message
the rules found nothing in are sent in small batches to the configured model at maintenance priority. Each answer
must name a message in the batch and use that message's own words. A supported answer is saved as an automatic
memory, shown as saved automatically in Memories where the user can correct or delete it; a sensitive one waits
while sensitive memory is off. Each message goes with the user's current facts its words touch (`known`); an
answer that says one of them is wrong (`corrects`, which must name one that was sent), or that negates the one
current memory with its layer and subject, waits as a correction of that memory (`corrections.py`), and a new
value for a single-valued subject waits as a conflict.
"""
import json
import re

from companion import prompt_library
from companion.characters import require_current
from companion.database import encode, identifier, many, optional, settings
from companion.memory import corrections, formation
from companion.memory.extraction import Candidate, sentences, subject_key
from companion.memory.retrieval import terms
from companion.providers.chat import INCOMPLETE
from companion.providers.scheduling import MAINTENANCE, BackgroundInterrupted
from companion.text_models import config_for

PROMPT_VERSION = 'memory-suggest-4'
BATCH = 8
MIN_WORDS = 6
NAMED = re.compile(r"\b[A-Z][a-z']+")
MONTHS = re.compile(r'\b(january|february|march|april|june|july|august|september|october|november|december)\b')
SUPPORT = 0.6
LAYERS = {'user_fact', 'plan', 'temporary', 'shared_experience', 'relationship'}
# A list of short rules with whole examples: small local models copy an example's shape, so every example names
# every field.
RULES = (
    'You help a companion app remember what the user said about their real life.\n'
    "Input: a JSON list of the user's messages, numbered.\n"
    'Output: JSON only, a list of facts, or [] when there is nothing. Each fact is {"message": number, "layer": '
    '"user_fact" | "plan" | "temporary" | "shared_experience" | "relationship", "subject": short label, "value": '
    'just the fact}.\n'
    'Rules:\n'
    '- Keep only lasting facts the user states plainly about themselves or their people.\n'
    '- "value" is the fact in a few of the user\'s own words, without "I", "I\'m" or "my" in front.\n'
    '- "subject" says whose fact it is when it is about someone else ("Mom\'s home", "Sister\'s job").\n'
    '- Leave out questions, hypotheticals, jokes, roleplay, quotes of other people, moments that will not matter '
    'tomorrow ("my dog is snoring"), someone the message does not name ("she\'s a lawyer"), facts listed under a '
    'message\'s "already_saved", and anything you would have to guess.\n'
    '- A message may list "known": what is already remembered. When the message says one of those is wrong or no '
    'longer true, add "corrects": that subject exactly as listed, with the corrected fact as the value.\n'
    'Examples:\n'
    '"I\'m Sam, I teach 8th grade science" gives [{"message": 1, "layer": "user_fact", "subject": "Name", "value": '
    '"Sam"}, {"message": 1, "layer": "user_fact", "subject": "Work", "value": "teaches 8th grade science"}]\n'
    '"my mom lives in Towson" gives [{"message": 1, "layer": "user_fact", "subject": "Mom\'s home", "value": '
    '"Towson"}]\n'
    '"I don\'t garden anymore" with "known": ["Hobby: gardening"] gives [{"message": 1, "layer": "user_fact", '
    '"subject": "Hobby", "value": "no longer gardens", "corrects": "Hobby"}]\n'
    '"my dog is snoring lol" gives []'
)


class SuggestionsInvalid(Exception):
    pass


def pending(connection, limit=BATCH) -> list[dict]:
    """Finished jobs the model has not seen, each with only the sentences the rules found nothing in:
    "I'm allergic to shellfish. I'm Sam." keeps "I'm Sam." for the model. A sentence the rules took a fact
    from stays, with what they saved, when it names more than they kept ("my brother Marcus and his wife Priya
    in Denver are having a baby in December" gives the rules only the brother)."""
    rows = many(connection, "SELECT messages.* FROM memory_jobs JOIN messages ON messages.id=memory_jobs.message_id "
                "WHERE memory_jobs.status='done' AND memory_jobs.model_status IS NULL AND messages.redacted_at IS NULL "
                'ORDER BY memory_jobs.queued_at LIMIT ?', (limit,))
    return [{**row, 'text': unhandled(connection, row), 'saved': saved(connection, row)} for row in rows]


def handled_proposals(connection, message) -> list[dict]:
    return [json.loads(row['proposal']) for row in many(
        connection, "SELECT proposal FROM memory_candidates WHERE message_id=? AND source!='model'", (message['id'],))]


def more_to_it(sentence: str, proposals: list[dict]) -> bool:
    """Whether a sentence the rules took facts from names something they did not keep: another name or place,
    or a month."""
    kept = {word.casefold() for proposal in proposals if proposal.get('excerpt') == sentence
            for word in re.findall(r"[\w']+", f"{proposal.get('subject', '')} {proposal.get('value', '')}")}
    names = {word.casefold() for word in NAMED.findall(sentence[1:])} | set(MONTHS.findall(sentence.casefold()))
    return bool(names - kept - {"i'm", "i've", "i'll", "i'd"})


def unhandled(connection, message) -> str:
    proposals = handled_proposals(connection, message)
    handled = {proposal.get('excerpt') for proposal in proposals}
    if not handled:
        return message['text']
    return ' '.join(f'{sentence}.' for sentence in sentences(message['text'])
                    if sentence not in handled or more_to_it(sentence, proposals))


def saved(connection, message) -> list[str]:
    """What the rules kept from the sentences still sent, so the model does not suggest it again."""
    proposals = handled_proposals(connection, message)
    return [f"{proposal['subject']}: {proposal['value']}" for proposal in proposals
            if more_to_it(proposal.get('excerpt') or '', proposals)]


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


def candidate(item, batch) -> tuple[dict, Candidate, dict | None] | None:
    """A supported answer, with the sent memory it corrects; a `corrects` naming anything not sent drops it."""
    index, layer = item.get('message'), item.get('layer')
    subject, value = str(item.get('subject') or '').strip()[:200], str(item.get('value') or '').strip()[:1000]
    if not isinstance(index, int) or not 1 <= index <= len(batch) or layer not in LAYERS or not subject or not value:
        return None
    message = batch[index - 1]
    if not supported(value, message['text']) or not sentences(message['text']):
        return None
    corrected = None
    if item.get('corrects') is not None:
        corrected = corrections.named(message.get('known') or [], item['corrects'])
        if corrected is None:
            return None
    return message, Candidate(layer, subject, value, 'model', message['text'][:500], subject_key=subject_key(subject),
                              plan_status='proposed' if layer == 'plan' else None), corrected


async def ask(provider, scheduler, config, key, batch, rules=RULES) -> list[dict]:
    content = json.dumps([{'message': index, 'text': message['text'],
                           **({'already_saved': message['saved']} if message.get('saved') else {}),
                           **({'known': [corrections.label(row) for row in message['known']]}
                              if message.get('known') else {})}
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


def correction(connection, companion, found, corrected, timestamp) -> dict | None:
    """The memory an answer corrects: the one it named, or the one current memory with its layer and subject when
    the answer negates it ("Mom's interests: not a gardener")."""
    if corrected is not None:
        return corrections.current(connection, {'corrects': corrected['id']}, timestamp)
    if not corrections.negated(found.value):
        return None
    return corrections.same_subject(connection, companion['id'], found.layer, found.subject_key, timestamp)


def store(connection, companion, message, found, corrected, timestamp) -> int:
    current = optional(connection, 'SELECT * FROM messages WHERE id=?', (message['id'],))
    if current is None or formation.blocked(connection, current):
        return 0
    if target := correction(connection, companion, found, corrected, timestamp):
        fields = corrections.fields_for(target, found.value, current, found.excerpt,
                                        ending=corrections.ends(target, found.value, current['text']),
                                        retracting=corrections.retracts(target, found.value, current['text']))
        added = corrections.record(connection, companion, current, fields, 'model', PROMPT_VERSION, timestamp)
        if added:
            formation.log(connection, timestamp, 'suggested', message_id=current['id'], detail=corrections.RULE)
        return added
    mark_value = formation.fingerprint(found)
    declined = optional(connection, "SELECT 1 FROM memory_candidates WHERE fingerprint=? AND status='declined'",
                        (mark_value,))
    duplicate = optional(connection, "SELECT 1 FROM memories WHERE companion_id=? AND status='active' AND "
                         'subject_key=? AND lower(value)=lower(?)', (companion['id'], found.subject_key, found.value))
    if declined or duplicate:
        return 0
    fields = formation.proposal(found, current)
    # A new value for a single-valued subject is the same choice as a rule-found conflict ("Denver" vs "Chicago").
    reason = 'conflict' if formation.contradicts(connection, companion, found, fields, timestamp) else 'model_guess'
    if reason == 'model_guess' and fields['sensitive'] and not settings(connection)['sensitive_memory']:
        reason = 'sensitive'
    candidate_id = identifier()
    cursor = connection.execute(
        'INSERT OR IGNORE INTO memory_candidates (id, companion_id, timeline_id, message_id, source, rule, proposal, '
        "fingerprint, status, reason, created_at) VALUES (?, ?, ?, ?, 'model', ?, ?, ?, 'pending', ?, ?)",
        (candidate_id, companion['id'], current['timeline_id'], current['id'], PROMPT_VERSION, encode(fields),
         mark_value, reason, timestamp))
    if cursor.rowcount and reason == 'model_guess':
        # Saved like a rule-found fact (users rarely review suggestions); it shows as saved automatically in
        # Memories, where it can be corrected or deleted. Conflicts, corrections and held sensitive facts still wait.
        memory, outcome = formation.commit(connection, companion, fields, [current['id']], timestamp, 'automatic')
        formation.resolve(connection, candidate_id, 'committed' if memory else 'dismissed', memory, outcome, timestamp)
        formation.log(connection, timestamp, outcome, memory_id=memory and memory['id'], candidate_id=candidate_id,
                      message_id=current['id'])
        return cursor.rowcount
    formation.log(connection, timestamp, 'suggested', message_id=current['id'], detail=reason)
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
        companion, now = require_current(connection), database.now()
        batch = [{**message, 'known': corrections.relevant(connection, companion['id'], message['text'], now)}
                 for message in batch if eligible(message)]
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
