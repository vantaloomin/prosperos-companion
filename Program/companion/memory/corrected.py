"""Old words of a corrected memory, marked wherever recall can still find them (M9, M12).

Correcting a memory makes a new revision of it (or, for a value that was never true, retracts it),
but the words it came from stay in the transcript. Raw recall can still find the user's original
message, the companion's reply to it, a later reply of hers that repeated the old value, and a day
summary quoting it; offered bare, they would put the wrong fact back in front of the model as
something the user said. So each of those gets a note naming what the user changed it to, or that
they said it was wrong. Worked out with rules from saved state on every reply, nothing stored, so
deleting or excluding the memory takes its notes with it.
"""
from companion.database import many, optional, settings
from companion.lineage import related, scope
from companion.memory import records
from companion.memory.corrections import negated, stems


def latest(connection, row) -> dict | None:
    """The revision a superseded memory led to, or None when it was retracted (superseded by nothing)."""
    seen = set()
    while row['status'] == 'superseded' and row['id'] not in seen:
        seen.add(row['id'])
        following = optional(connection, 'SELECT * FROM memories WHERE supersedes_id=? ORDER BY revision DESC LIMIT 1',
                             (row['id'],))
        if following is None and row['merged_into_id']:
            following = optional(connection, 'SELECT * FROM memories WHERE id=?', (row['merged_into_id'],))
        if following is None:
            return None
        row = following
    return row


def note_for(old, now: dict | None) -> str:
    if now is None:
        return f'the user later said this was wrong: {old["subject"]}: {old["value"]}'
    status = f' [{now["plan_status"]}]' if now['plan_status'] else ''
    return f'the user later changed this; it now reads: {now["subject"]}: {now["value"]}{status}'


def changed_words(old, now: dict | None) -> set[str]:
    """Words of the old value that are no longer true: all of them when it was retracted or negated ("she loves
    gardening" -> "not a gardener"), otherwise the ones the new value drops ("a lab" -> "a beagle")."""
    words = stems(old['value'], stems(old['subject']))
    return words if now is None or negated(now['value']) else words - stems(now['value'])


def notes(connection, companion, timeline_id, messages) -> dict[str, str]:
    """{message id: note} for the given messages that carry a value the user later corrected."""
    timelines, share = scope(connection, timeline_id), bool(settings(connection)['share_profile_across_timelines'])
    rows = many(connection, "SELECT * FROM memories WHERE companion_id=? AND status='superseded' "
                'AND merged_into_id IS NULL ORDER BY updated_at', (companion['id'],))
    found: dict[str, str] = {}
    for old in rows:
        now = latest(connection, old)
        if now is not None and (now['status'] != 'active' or not records.in_scope(now, timelines, share)):
            continue  # Excluded memories block their sources outright; another timeline's change stays there.
        if now is None and not records.in_scope(old, timelines, share):
            continue
        if now is not None and (now['value'], now['plan_status']) == (old['value'], old['plan_status']):
            continue
        sources = related(connection, [row['message_id'] for row in many(
            connection, 'SELECT message_id FROM memory_sources WHERE memory_id=?', (old['id'],))])
        if not sources:
            continue
        note = note_for(old, now)
        first = min((row['created_at'] for row in messages if row['id'] in sources), default=None)
        wrong = changed_words(old, now)
        for message in messages:
            if message['id'] in sources or message.get('reply_to') in sources or (
                    wrong and first and message['role'] == 'companion' and first <= message['created_at'] <= old['updated_at']
                    and stems(message['text']) & wrong):
                found[message['id']] = note
    return found


def summary_notes(summaries, marked: dict[str, str]) -> dict[str, str]:
    """{summary id: note} for day summaries quoting a marked message."""
    found = {}
    for summary in summaries:
        for source in summary['source_message_ids']:
            if source in marked:
                found[summary['id']] = marked[source]
    return found
