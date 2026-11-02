"""Plans and outings two people share show in both their days (Vanta, 2026-11-01: Sett had dinner with Lestara at
Cloud Step Inn, as planned, but only Sett's timeline said so; Lestara's had her at the fish stalls at the time).

A companion's entry can name someone from their circle (`with`, companion/life/composer.py). That person's day gives
way to it: the slot of theirs it starts in holds the same outing told from their side, and any other slot of theirs it
fills a good part of stays quiet, so the two days never say they were in two places at once.

The person in the circle can also be another of the user's companions: the user wrote them into the description, or
added them by hand, under that companion's name (`twins`). Then the outing is in that companion's own day, and they
only go along when that day leaves them free (`free`): not at work or asleep, and not already busy with a plan.

Nothing is stored twice. A slot reads the entry it shares from the other day when it is composed (`shared`); a new
entry clears the other day's upcoming slots it touches so they are composed again (`make_room`); and an entry whose
other half has gone (the plan changed) is composed afresh (`drop_stale`, `holds`).
"""
from datetime import datetime, timedelta

from companion.clock import parse, stamp
from companion.database import decode, many, optional
from companion.life import composer, routine

COMPANION = 'companion'
BUSY = {'work', 'study', 'sleep'}
# Another slot of theirs that an outing fills at least this much of stays quiet.
MIN_OVERLAP = timedelta(minutes=30)
# A circle person the user named themselves can be another companion by first name alone ("Lestara" for Lestara Vey).
USER_NAMED = ('sheet', 'by_hand', 'edited')
# An entry that is already spoken for: a plan, an outing with the user, a trip, a session of a recommendation.
FIXED = ('own_plan', 'outing', 'trip', 'recommendation', 'admin', 'big_day', 'babysit')
# A block that is already spoken for.
FIXED_BLOCK = ('plans', 'trip', 'arrival', 'sick_day')


# Who is who ------------------------------------------------------------------------------------------------------

def companions(connection) -> list[dict]:
    """Every companion with a timeline: {id, timeline_id, name}."""
    return many(connection, 'SELECT c.id, c.active_timeline_id AS timeline_id, v.name FROM companions c JOIN '
                'character_versions v ON v.id=c.active_version_id WHERE c.active_timeline_id IS NOT NULL')


def is_them(person: dict, name: str) -> bool:
    """A circle person is the companion called `name`: the same full name, or, for someone the user named themselves,
    the same first name."""
    wanted = ' '.join(name.split()).casefold()
    if not wanted:
        return False
    details = decode(person['details']) or {}
    names = {' '.join(str(found).split()).casefold() for found in (person['name'], details.get('full_name'),
                                                                     details.get('sheet')) if found}
    if wanted in names:
        return True
    if not any(details.get(key) for key in USER_NAMED):
        return False
    return wanted.split()[0] in {found.split()[0] for found in names if found}


def twins(connection, timeline_id: str) -> dict[str, dict]:
    """{circle person id: the other companion they are} for this timeline's circle."""
    others = [found for found in companions(connection) if found['timeline_id'] != timeline_id]
    if not others:
        return {}
    result = {}
    for person in many(connection, "SELECT * FROM circle_people WHERE timeline_id=? AND status='active'",
                       (timeline_id,)):
        twin = next((found for found in others if is_them(person, found['name'])), None)
        if twin:
            result[person['id']] = twin
    return result


def stand_ins(connection, companion_id: str, name: str) -> list[dict]:
    """The circle people in the other companions' circles who are this companion: {timeline_id, person_id, other}
    with `other` the companion whose circle it is."""
    others = {found['timeline_id']: found for found in companions(connection) if found['id'] != companion_id}
    if not others:
        return []
    marks = ','.join('?' * len(others))
    rows = many(connection, f"SELECT * FROM circle_people WHERE status='active' AND timeline_id IN ({marks})",
                tuple(others))
    return [{'timeline_id': row['timeline_id'], 'person_id': row['id'], 'other': others[row['timeline_id']]}
            for row in rows if is_them(row, name)]


# Whether they can go -----------------------------------------------------------------------------------------------

def spoken_for(row: dict, timeline_id: str | None = None) -> bool:
    """An agenda row that cannot give way to someone else's outing. A row already sharing an outing from
    `timeline_id` can (it is that outing, composed again)."""
    block = decode(row['block']) or {}
    entry = decode(row['entry']) if row['entry'] else None
    if row['status'] != 'upcoming' or block.get('kind') in BUSY or any(block.get(key) for key in FIXED_BLOCK):
        return True
    if not entry:
        return False
    if (entry.get('joint') or {}).get('timeline_id') == timeline_id and timeline_id:
        return False
    return bool(entry.get('with') or entry.get('joint') or any(entry.get(key) for key in FIXED))


def free(connection, twin: dict, starts_at: datetime, ends_at: datetime, timeline_id: str) -> bool:
    """Whether another companion can join an outing from `timeline_id` over [starts_at, ends_at): their routine has
    no work, study or sleep then, and nothing on their days ahead is spoken for."""
    from companion.characters import by_id
    found = by_id(connection, twin['id'])
    if found is None:
        return False
    schedule, _default = routine.blocks(found['version']['definition'])
    if any(slot.block.kind in BUSY for slot in routine.slots(schedule, found['version']['timezone'], starts_at,
                                                             ends_at)):
        return False
    rows = many(connection, 'SELECT * FROM life_agenda WHERE timeline_id=? AND subject=? AND starts_at<? AND ends_at>?',
                (twin['timeline_id'], COMPANION, stamp(ends_at), stamp(starts_at)))
    return not any(spoken_for(row, timeline_id) for row in rows)


# The other side of an outing ---------------------------------------------------------------------------------------

def told(entry: dict, own: str, other: str) -> str:
    """The outing from the other side: "Lestara had dinner with Sett at Cloud Step Inn." """
    activity, place = entry.get('activity'), entry.get('place') or {}
    at = f" at {place['name']}" if place.get('name') and place.get('kind') != 'event' else ''
    if activity in composer.PLANNABLE_TOGETHER:
        return f"{own} {composer.PLANNABLE_TOGETHER[activity][1].format(at=at, friend=other)}."
    if activity == 'gathering' and (entry.get('gathering') or {}).get('occasion'):
        return f"{other} came to {entry['gathering']['occasion']}."
    if activity == 'birthday':
        return f'{own} celebrated their birthday{at} with {other}.'
    if activity == 'own-birthday':
        return f"{own} celebrated {other}'s birthday{at}."
    if activity == 'festival' and place.get('name'):
        return f"{own} went out for {place['name']} with {other}."
    if activity == 'recommendation':
        return f'{own} went along with {other}{at}.'
    return f'{own} spent time with {other}{at}.'


def mirrored(source: dict, own: str, other: dict) -> dict:
    """The entry for the other side of `source` (a life_agenda row): the same outing, place and time, with `joint`
    naming where it comes from. `other` is {id, name} of whoever's entry it is."""
    entry = decode(source['entry'])
    return {'summary': told(entry, own, other['name']), 'post': entry.get('post') or '', 'mood': entry.get('mood'),
            'activity': entry.get('activity'), 'place': entry.get('place'),
            'with': {'id': other['id'], 'name': other['name']}, 'weather': entry.get('weather'),
            'composer_version': composer.COMPOSER_VERSION,
            'joint': {'timeline_id': source['timeline_id'], 'slot': source['slot_key'],
                      'person': entry['with']['id'], 'starts_at': source['starts_at'], 'ends_at': source['ends_at']}}


def sources(connection, scope: dict, starts_at: datetime, ends_at: datetime) -> list[tuple[dict, dict]]:
    """(row, other) for each companion entry naming this subject that overlaps [starts_at, ends_at), earliest first:
    for a circle person, their companion's; for a companion, the other companions' entries naming their stand-ins."""
    subject, timeline_id = scope['subject'], scope['timeline_id']
    if subject != COMPANION:
        owner = scope.get('companion')
        if not owner:
            return []
        rows = many(connection, "SELECT * FROM life_agenda WHERE timeline_id=? AND subject=? AND entry IS NOT NULL "
                    "AND json_extract(entry, '$.with.id')=? AND starts_at<? AND ends_at>? ORDER BY starts_at",
                    (timeline_id, COMPANION, subject, stamp(ends_at), stamp(starts_at)))
        other = {'id': f"companion:{owner['id']}", 'name': owner['version']['definition']['name']}
        return [(row, other) for row in rows]
    companion = scope.get('companion')
    if not companion:
        return []
    if 'stand_ins' not in scope:
        scope['stand_ins'] = stand_ins(connection, companion['id'], scope['definition']['name'])
    found = []
    for stand_in in scope['stand_ins']:
        for row in many(connection, "SELECT * FROM life_agenda WHERE timeline_id=? AND subject=? AND entry IS NOT NULL "
                        "AND json_extract(entry, '$.with.id')=? AND starts_at<? AND ends_at>? ORDER BY starts_at",
                        (stand_in['timeline_id'], COMPANION, stand_in['person_id'], stamp(ends_at), stamp(starts_at))):
            found.append((row, {'id': f"companion:{stand_in['other']['id']}", 'name': stand_in['other']['name']}))
    return sorted(found, key=lambda item: item[0]['starts_at'])


def holder(scope: dict, slot, begins: datetime) -> bool:
    """This slot of theirs holds an outing beginning at `begins`: it begins inside the slot, or before it while they
    were in no waking slot (asleep, or between blocks) and this is the first slot after."""
    if slot.starts_at <= begins < slot.ends_at:
        return True
    if begins >= slot.starts_at:
        return False
    schedule, _default = routine.blocks(scope['definition'])
    earlier = routine.slots(schedule, scope.get('timezone') or 'UTC', begins, slot.starts_at)
    return not any(found.block.kind not in routine.RESTING and found.starts_at < slot.starts_at for found in earlier)


def shared(connection, scope: dict, slot, block: dict, starts_at: datetime, ends_at: datetime):
    """What an outing someone else's entry shares with this subject makes of their slot: ('joint', entry) for the
    slot that holds it, ('quiet', None) for another slot it fills a good part of, or None when it does not touch it."""
    if block.get('kind') in BUSY or any(block.get(key) for key in FIXED_BLOCK):
        return None
    for row, other in sources(connection, scope, starts_at, ends_at):
        begins, finishes = parse(row['starts_at']), parse(row['ends_at'])
        if holder(scope, slot, begins):
            own = scope['definition']['name']
            return 'joint', mirrored(row, own, other)
        if min(ends_at, finishes) - max(starts_at, begins) >= MIN_OVERLAP:
            return 'quiet', None
    return None


def start(entry: dict | None, starts_at: datetime, ends_at: datetime, least: timedelta) -> datetime:
    """When their side of a shared outing starts: when the outing does, if that is later in their slot."""
    if not entry:
        return starts_at
    return max(starts_at, min(parse(entry['joint']['starts_at']), ends_at - least))


def make_room(connection, scope: dict, starts_at: datetime, ends_at: datetime, entry: dict | None) -> None:
    """A companion's new entry names someone: their upcoming slots it touches are cleared, and their cursor moved
    back, so those slots are composed again around it."""
    person = (entry or {}).get('with') or {}
    if scope['subject'] != COMPANION or not person.get('id') or (entry or {}).get('joint'):
        return
    timeline_id = scope['timeline_id']
    clear(connection, timeline_id, person['id'], starts_at, ends_at, timeline_id)
    row = optional(connection, 'SELECT * FROM circle_people WHERE id=? AND timeline_id=?', (person['id'], timeline_id))
    twin = row and twins_of(connection, timeline_id, row)
    if twin:
        clear(connection, twin['timeline_id'], COMPANION, starts_at, ends_at, timeline_id)


def twins_of(connection, timeline_id: str, person: dict) -> dict | None:
    return next((found for found in companions(connection) if found['timeline_id'] != timeline_id
                 and is_them(person, found['name'])), None)


def clear(connection, timeline_id: str, subject: str, starts_at: datetime, ends_at: datetime, source: str) -> None:
    rows = many(connection, "SELECT * FROM life_agenda WHERE timeline_id=? AND subject=? AND status='upcoming' "
                'AND starts_at<? AND ends_at>?', (timeline_id, subject, stamp(ends_at), stamp(starts_at)))
    gone = [row for row in rows if not spoken_for(row, source)]
    if not gone:
        return
    for row in gone:
        connection.execute('DELETE FROM life_agenda WHERE id=?', (row['id'],))
    back(connection, timeline_id, subject, min(row['starts_at'] for row in gone))


def back(connection, timeline_id: str, subject: str, since: str) -> None:
    connection.execute('UPDATE agenda_cursors SET through=MIN(through, ?) WHERE timeline_id=? AND subject=?',
                       (since, timeline_id, subject))


def holds(connection, entry: dict | None) -> bool:
    """A shared entry's other half is still there: the companion's entry it came from still names the same person."""
    joint = (entry or {}).get('joint')
    if not joint:
        return True
    return optional(connection, "SELECT 1 FROM life_agenda WHERE timeline_id=? AND subject=? AND slot_key=? "
                    "AND json_extract(entry, '$.with.id')=?",
                    (joint['timeline_id'], COMPANION, joint['slot'], joint['person'])) is not None


def drop_stale(connection, timeline_id: str, subject: str) -> None:
    """Upcoming shared entries whose other half has gone are composed again."""
    rows = many(connection, "SELECT id, starts_at, entry FROM life_agenda WHERE timeline_id=? AND subject=? AND "
                "status='upcoming' AND json_extract(entry, '$.joint') IS NOT NULL", (timeline_id, subject))
    gone = [row for row in rows if not holds(connection, decode(row['entry']))]
    for row in gone:
        connection.execute('DELETE FROM life_agenda WHERE id=?', (row['id'],))
    if gone:
        back(connection, timeline_id, subject, min(row['starts_at'] for row in gone))
