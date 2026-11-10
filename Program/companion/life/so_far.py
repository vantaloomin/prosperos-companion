"""Their day so far, for the chat: what the companion has done today and the photos they sent of it.

The precomputed agenda (companion/life/agenda.py) holds what each slot of their day is (a yoga class, a shift), but
a slot becomes a committed event only when a catch-up gets to it, and the chat's "Your day today" names blocks
("Free time"), not what filled them. A photo they sent is described only with the reply that sends it. So a reply
two hours after a photo of a yoga class had no word of it, said yoga was "a couple days back", and a later first text
read the committed event and said "had yoga this morning". These lines close that gap: what today's slots held, up
to now, and the photos sent today, from saved state only. What is still ahead stays hidden (`agenda.current`).
"""
from datetime import datetime, timedelta

from companion.clock import parse, stamp, zone
from companion.database import decode, many
from companion.life import composer, routine

LIMIT = 6
PHOTOS = 3
EVENT_KEY = 'life:{timeline}:{slot}'
LEAD = 'Your day so far (it happened; keep to it, and never say otherwise):'


def lines(connection, companion: dict, now: datetime) -> list[tuple[str, str]]:
    """(identity, text) pairs, one at most: the slots of today that have begun, not yet told as a committed event,
    and the photos sent today, under one lead line."""
    version, timeline_id = companion['version'], companion['active_timeline_id']
    tz = zone(version['timezone'])
    local = now.astimezone(tz)
    midnight = local.replace(hour=0, minute=0, second=0, microsecond=0)
    found = [*slot_lines(connection, timeline_id, version['definition'], tz, local),
             *photo_lines(connection, timeline_id, version['definition'], tz, midnight, now)]
    if not found:
        return []
    identity = 'so_far:' + ','.join(key for key, _text in found)
    return [(identity, '\n'.join([LEAD, *(text for _key, text in found)]))]


def slot_lines(connection, timeline_id: str, definition: dict, tz, local: datetime) -> list[tuple[str, str]]:
    rows = many(connection, "SELECT slot_key, starts_at, ends_at, block, entry FROM life_agenda WHERE timeline_id=? "
                "AND subject='companion' AND local_date=? AND starts_at<=? AND status!='skipped' AND entry IS NOT NULL "
                'ORDER BY starts_at', (timeline_id, local.date().isoformat(), stamp(local)))
    told = {row['idempotency_key'].split('#')[0] for row in many(
        connection, "SELECT idempotency_key FROM life_events WHERE timeline_id=? AND status='committed' AND "
        'starts_at>=?', (timeline_id, stamp(local.replace(hour=0, minute=0, second=0, microsecond=0))))}
    result = []
    for row in rows[-LIMIT:]:
        block, entry = decode(row['block']), decode(row['entry'])
        summary = composer.said(entry.get('summary'), definition)
        if not summary or block.get('kind') in routine.RESTING or block.get('with_user') or \
                EVENT_KEY.format(timeline=timeline_id, slot=row['slot_key']) in told:
            continue
        starts, ends = parse(row['starts_at']).astimezone(tz), parse(row['ends_at']).astimezone(tz)
        when = (f"Now (since {starts:%H:%M}, until {ends:%H:%M}; still going)" if ends > local
                else f'Earlier today, {starts:%H:%M}-{ends:%H:%M}')
        result.append((f"so_far:{row['slot_key']}", f'- {when}: {summary}'))
    return result


def photo_lines(connection, timeline_id: str, definition: dict, tz, midnight: datetime, now: datetime) \
        -> list[tuple[str, str]]:
    rows = many(connection, 'SELECT photo.message_id, photo.kind, photo.summary, message.created_at FROM chat_photos '
                'photo JOIN messages message ON message.id=photo.message_id WHERE message.timeline_id=? AND '
                "message.active=1 AND photo.removed_at IS NULL AND photo.kind!='meme' AND message.created_at>=? AND "
                'message.created_at<=? ORDER BY message.created_at DESC LIMIT ?',
                (timeline_id, stamp(max(midnight, now - timedelta(hours=18))), stamp(now), PHOTOS))
    result = []
    for row in reversed(rows):
        summary = composer.said(row['summary'], definition)
        if summary:
            sent = parse(row['created_at']).astimezone(tz)
            what = 'a selfie' if row['kind'] == 'selfie' else 'a photo'
            result.append((f"so_far:photo:{row['message_id']}",
                           f'- At {sent:%H:%M} you sent the user {what} of what you were doing then: {summary}'))
    return result
