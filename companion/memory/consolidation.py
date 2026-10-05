"""Bounded, deterministic consolidation (PRD M11): episode summaries and duplicate proposals.

Nothing here calls a model. An episode summary quotes the user's own sentences from one day, keeps
the exact source messages, and is a replaceable retrieval aid: it never becomes a source for
extraction, never confirms anything, and is dropped once any of its sources is deleted, declined or
blocked by an exclusion. Duplicate memories are only proposed; the user decides. Each run handles
a bounded number of days and commits only if the memory revision did not change while it worked.
"""
import hashlib
from collections import Counter
from datetime import datetime

from companion.characters import require_current
from companion.clock import parse, zone
from companion.database import bump_memory_revision, decode, encode, identifier, many, one, optional, settings
from companion.errors import require
from companion.lineage import related
from companion.memory import records
from companion.memory.extraction import sentences
from companion.memory.retrieval import terms

MIN_MESSAGES = 4
DAYS_PER_RUN = 5
QUOTES = 3
SIMILAR = 0.6


def local_day(value: str, timezone: str) -> str:
    return parse(value).astimezone(zone(timezone)).date().isoformat()


def excluded_sources(connection, companion_id) -> set[str]:
    declined = related(connection, [row['message_id'] for row in many(connection, 'SELECT message_id FROM memory_declines')])
    return declined | records.blocked_messages(connection, companion_id)


def episode_days(connection, companion, now: datetime) -> dict[str, list[dict]]:
    """User messages per local day, for finished days with enough conversation and no current summary."""
    timezone = settings(connection)['user_timezone']
    today = now.astimezone(zone(timezone)).date().isoformat()
    blocked = excluded_sources(connection, companion['id'])
    days: dict[str, list[dict]] = {}
    for message in many(connection, "SELECT id, text, created_at FROM messages WHERE timeline_id=? AND role='user' "
                        "AND status='complete' AND redacted_at IS NULL ORDER BY seq",
                        (companion['active_timeline_id'],)):
        if message['id'] not in blocked:
            days.setdefault(local_day(message['created_at'], timezone), []).append(message)
    existing = {row['day']: row['basis'] for row in many(
        connection, 'SELECT day, basis FROM memory_summaries WHERE timeline_id=?', (companion['active_timeline_id'],))}
    return {day: messages for day, messages in sorted(days.items())
            if day < today and len(messages) >= MIN_MESSAGES and existing.get(day) != basis(messages)}


def basis(messages) -> str:
    return hashlib.sha256('|'.join(message['id'] for message in messages).encode()).hexdigest()


def quotes(messages) -> list[tuple[str, str]]:
    """The day's most representative sentences, in the order they were said: (message id, sentence).

    A sentence scores by the topics it shares with the rest of the day; words in most sentences
    (filler) count for nothing, and a sentence close to one already chosen is skipped.
    """
    found = [(message['id'], sentence) for message in messages for sentence in sentences(message['text'])]
    words = [set(terms(sentence)) for _id, sentence in found]
    counts = Counter(term for group in words for term in group)
    common = len(found) / 2

    def score(group):
        return sum(counts[term] - 1 for term in group if counts[term] <= common) + len(group) / 10

    ranked = sorted((index for index, group in enumerate(words) if len(group) >= 3),
                    key=lambda index: (-score(words[index]), index))
    chosen = []
    for index in ranked:
        if len(chosen) == QUOTES:
            break
        if all(len(words[index] & words[other]) / len(words[index] | words[other]) <= 0.5 for other in chosen):
            chosen.append(index)
    return [found[index] for index in sorted(chosen)]


def summarize(database) -> dict:
    """Write summaries for up to DAYS_PER_RUN finished days. Stale work is discarded, not committed."""
    with database.connect() as connection:
        companion = require_current(connection)
        revision = settings(connection)['memory_revision']
        days = list(episode_days(connection, companion, database.clock.now()).items())[:DAYS_PER_RUN]
    planned = [(day, messages, quotes(messages)) for day, messages in days]
    with database.connect(write=True) as connection:
        if settings(connection)['memory_revision'] != revision:
            return {'summaries': 0, 'stale': True}
        written = 0
        for day, messages, chosen in planned:
            connection.execute('DELETE FROM memory_summaries WHERE timeline_id=? AND day=?',
                               (companion['active_timeline_id'], day))
            if not chosen:
                continue
            text = ' '.join(f'“{sentence}”' for _id, sentence in chosen)
            sources = sorted({message_id for message_id, _sentence in chosen})
            connection.execute('INSERT INTO memory_summaries (id, timeline_id, day, text, source_message_ids, basis, '
                               'created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                               (identifier(), companion['active_timeline_id'], day, text, encode(sources),
                                basis(messages), database.now()))
            written += 1
        return {'summaries': written, 'stale': False}


def usable_summaries(connection, timeline_id, blocked: set[str]) -> list[dict]:
    """Summaries whose every source is still present and allowed (M12)."""
    rows = many(connection, 'SELECT * FROM memory_summaries WHERE timeline_id=? ORDER BY day', (timeline_id,))
    present = {row['id'] for row in many(connection, 'SELECT id FROM messages WHERE timeline_id=? '
                                         'AND redacted_at IS NULL', (timeline_id,))}
    usable = []
    for row in rows:
        sources = set(decode(row['source_message_ids']))
        if sources <= present and not sources & blocked:
            usable.append({**row, 'source_message_ids': sorted(sources)})
    return usable


def similarity(left: str, right: str) -> float:
    a, b = set(terms(left)), set(terms(right))
    return len(a & b) / len(a | b) if a and b else 0.0


def propose_merges(database) -> dict:
    """Propose merging near-identical active memories about the same subject; never merge on its own."""
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        rows = many(connection, "SELECT * FROM memories WHERE companion_id=? AND status='active' "
                    'ORDER BY layer, subject_key, created_at', (companion['id'],))
        proposed = 0
        for index, older in enumerate(rows):
            for newer in rows[index + 1:]:
                if (newer['layer'], newer['subject_key'], newer['timeline_id']) != \
                        (older['layer'], older['subject_key'], older['timeline_id']):
                    break
                if older['boundary'] == newer['boundary'] and similarity(older['value'], newer['value']) >= SIMILAR:
                    proposed += add_proposal(connection, older, newer, database.now())
        return {'proposed': proposed}


def add_proposal(connection, older, newer, timestamp) -> int:
    mark = hashlib.sha256(f"merge|{older['id']}|{newer['id']}".encode()).hexdigest()
    cursor = connection.execute("INSERT OR IGNORE INTO memory_proposals (id, kind, keep_id, merge_id, fingerprint, "
                                "status, created_at) VALUES (?, 'merge', ?, ?, ?, 'pending', ?)",
                                (identifier(), newer['id'], older['id'], mark, timestamp))
    return cursor.rowcount


def proposals(database) -> list[dict]:
    with database.connect() as connection:
        rows = many(connection, "SELECT * FROM memory_proposals WHERE status='pending' ORDER BY created_at")
        result = []
        for row in rows:
            keep = optional(connection, "SELECT * FROM memories WHERE id=? AND status='active'", (row['keep_id'],))
            merge = optional(connection, "SELECT * FROM memories WHERE id=? AND status='active'", (row['merge_id'],))
            if keep and merge:
                result.append({**row, 'keep': records.with_sources(connection, keep),
                               'merge': records.with_sources(connection, merge)})
        return result


def resolve(database, proposal_id, accept: bool) -> dict:
    """Accepting keeps the newer memory with both sets of sources; the older one becomes history."""
    with database.connect(write=True) as connection:
        row = one(connection, 'SELECT * FROM memory_proposals WHERE id=?', (proposal_id,))
        require(row['status'] == 'pending', 'This proposal was already handled.', 409)
        timestamp = database.now()
        if accept:
            for identity in (row['keep_id'], row['merge_id']):
                memory = one(connection, 'SELECT status FROM memories WHERE id=?', (identity,))
                require(memory['status'] == 'active', 'One of these memories changed. Review them again.', 409)
            connection.execute('INSERT OR IGNORE INTO memory_sources (memory_id, message_id) '
                               'SELECT ?, message_id FROM memory_sources WHERE memory_id=?',
                               (row['keep_id'], row['merge_id']))
            connection.execute("UPDATE memories SET status='superseded', merged_into_id=?, updated_at=? WHERE id=?",
                               (row['keep_id'], timestamp, row['merge_id']))
            bump_memory_revision(connection, timestamp)
        connection.execute('UPDATE memory_proposals SET status=?, resolved_at=? WHERE id=?',
                           ('accepted' if accept else 'declined', timestamp, proposal_id))
        return {'id': proposal_id, 'status': 'accepted' if accept else 'declined'}


def run(database) -> dict:
    return {**summarize(database), **propose_merges(database)}
