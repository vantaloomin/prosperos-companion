"""Stored embeddings for memories and messages, and semantic rankings over the eligible pool (PRD M10, M12).

Vectors are keyed by owner, model and the digest of the exact text embedded, so an edited or
redacted text never matches an old vector. Deleting a memory or redacting a message deletes its
vectors; excluded owners never enter the pool, so their vectors are never ranked.
"""
import hashlib
import math
from array import array

from companion import pictures
from companion.database import many

INDEX_BATCH = 32
MIN_SIMILARITY = 0.2


def digest(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def memory_text(memory) -> str:
    return f"{memory['subject']}: {memory['value']}"


def pack(vector) -> bytes:
    return array('f', vector).tobytes()


def unpack(blob: bytes) -> list[float]:
    values = array('f')
    values.frombytes(blob)
    return values.tolist()


def cosine(left, right) -> float:
    if len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    norm = math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right))
    return dot / norm if norm else 0.0


def forget(connection, kind: str, owner_ids):
    connection.executemany('DELETE FROM memory_vectors WHERE owner_kind=? AND owner_id=?',
                           [(kind, owner_id) for owner_id in owner_ids])


def missing(connection, model: str, timeline_id: str, limit=INDEX_BATCH) -> list[tuple[str, str, str]]:
    """(kind, id, text) for active memories and complete messages that lack a current vector."""
    memories = many(connection, "SELECT memories.* FROM memories LEFT JOIN memory_vectors v ON v.owner_kind='memory' "
                    "AND v.owner_id=memories.id AND v.model=? WHERE memories.status='active' AND v.owner_id IS NULL "
                    'LIMIT ?', (model, limit))
    found = [('memory', row['id'], memory_text(row)) for row in memories]
    messages = many(connection, "SELECT messages.id, messages.role, messages.text FROM messages "
                    "LEFT JOIN memory_vectors v ON v.owner_kind='message' AND v.owner_id=messages.id AND v.model=? "
                    "WHERE messages.timeline_id=? AND messages.status='complete' AND messages.active=1 "
                    "AND messages.redacted_at IS NULL AND (messages.text<>'' OR EXISTS (SELECT 1 FROM "
                    "message_pictures p WHERE p.message_id=messages.id AND p.status<>'pending')) "
                    "AND v.owner_id IS NULL ORDER BY messages.seq DESC LIMIT ?",
                    (model, timeline_id, limit - len(found)))
    # A message's text includes what its pictures show (companion/pictures.py).
    return found + [('message', row['id'], row['text']) for row in pictures.described(connection, messages)]


def store(connection, model, items, vectors, timestamp) -> int:
    """Save vectors only for owners whose text is unchanged since it was read."""
    saved = 0
    for (kind, owner_id, text), vector in zip(items, vectors):
        if current_text(connection, kind, owner_id) != text:
            continue
        connection.execute('INSERT OR REPLACE INTO memory_vectors (owner_kind, owner_id, model, digest, vector, '
                           'created_at) VALUES (?, ?, ?, ?, ?, ?)',
                           (kind, owner_id, model, digest(text), pack(vector), timestamp))
        saved += 1
    return saved


def current_text(connection, kind, owner_id) -> str | None:
    if kind == 'memory':
        rows = many(connection, "SELECT * FROM memories WHERE id=? AND status='active'", (owner_id,))
        return memory_text(rows[0]) if rows else None
    rows = many(connection, 'SELECT id, role, text FROM messages WHERE id=? AND redacted_at IS NULL', (owner_id,))
    return pictures.described(connection, rows)[0]['text'] if rows else None


def rank(connection, model: str, query_vector, owners: dict[str, str], limit: int) -> list[str]:
    """Owner keys (`memory:<id>` or `message:<id>`) by similarity, best first, above a floor.

    `owners` maps each eligible owner key to the exact text in the pool, so a stale vector is ignored.
    """
    if not owners or not query_vector:
        return []
    rows = many(connection, 'SELECT owner_kind, owner_id, digest, vector FROM memory_vectors WHERE model=?', (model,))
    scored = []
    for row in rows:
        key = f"{row['owner_kind']}:{row['owner_id']}"
        if key in owners and digest(owners[key]) == row['digest']:
            score = cosine(query_vector, unpack(row['vector']))
            if score >= MIN_SIMILARITY:
                scored.append((score, key))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [key for _score, key in scored[:limit]]
