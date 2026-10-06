"""How forked timelines relate to the ones they came from (PRD C4, M6, M12).

A fork copies its parent's conversation before the edited message, so every copy records the
message it was first written as (`origin_id`). Choices about a message, such as Don't remember
this, exclusion of a memory it supports, or deleting it, reach every copy of it, so a fork can
never bring back words the user removed elsewhere.

Memories are not copied. A timeline sees its own memories plus those its ancestors formed
before the fork, so fictional history before a historical edit carries over and nothing after it
does. Real-user profile facts may be shared across all timelines instead (a visible setting).
"""
from companion.database import many, optional

CHUNK = 400


def scope(connection, timeline_id) -> dict[str, str | None]:
    """{timeline id: cutoff}: the timeline itself (no cutoff) and each ancestor up to the
    earliest fork point on the way back."""
    found, cutoff = {timeline_id: None}, None
    row = optional(connection, 'SELECT parent_id, forked_at FROM timelines WHERE id=?', (timeline_id,))
    while row and row['parent_id'] and row['parent_id'] not in found:
        if row['forked_at']:
            cutoff = row['forked_at'] if cutoff is None else min(cutoff, row['forked_at'])
        found[row['parent_id']] = cutoff
        row = optional(connection, 'SELECT parent_id, forked_at FROM timelines WHERE id=?', (row['parent_id'],))
    return found


def within(scope_map: dict, timeline_id: str, stated_at: str) -> bool:
    if timeline_id not in scope_map:
        return False
    cutoff = scope_map[timeline_id]
    return cutoff is None or stated_at < cutoff


def chunks(items: list) -> list[list]:
    return [items[start:start + CHUNK] for start in range(0, len(items), CHUNK)]


def related(connection, message_ids) -> set[str]:
    """The given messages with every copy of them and the original they were copied from."""
    ids = sorted(set(message_ids))
    if not ids:
        return set()
    origins = set()
    for part in chunks(ids):
        marks = ','.join('?' * len(part))
        origins |= {row['origin'] for row in many(
            connection, f'SELECT COALESCE(origin_id, id) AS origin FROM messages WHERE id IN ({marks})', part)}
    result = set(ids) | origins
    for part in chunks(sorted(origins)):
        marks = ','.join('?' * len(part))
        result |= {row['id'] for row in many(
            connection, f'SELECT id FROM messages WHERE origin_id IN ({marks})', part)}
    return result


def declined(connection, message_id) -> bool:
    """Don't remember this on any copy of a message applies to all of them."""
    ids = sorted(related(connection, [message_id]))
    marks = ','.join('?' * len(ids))
    return optional(connection, f'SELECT 1 FROM memory_declines WHERE message_id IN ({marks}) LIMIT 1', ids) is not None
