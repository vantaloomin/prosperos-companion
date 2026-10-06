"""Running into townsfolk: the companion meets the city's background people while out (companion/world/townsfolk.py).

When an agenda slot takes the companion somewhere real (a cafe, a park, a bar), the townsfolk who are
there by their own rules at that hour may cross paths with them. The first time is a chat with a
stranger ("Got talking with Dana Kim, the barista there, who talked a mile a minute"); each time after,
the companion learns more: what they are working toward and how it is going, then their flaw and what
they seem to want. One meeting a day at most, so the city feels lived in without crowding the diary.

Only the meeting is saved (timeline, person key, slot). Like acquaintances (companion/life/network.py), a
meeting counts once its slot has happened and the agenda entry still records it, so a rebuilt day can't
leave a stale one behind. The person themself is rebuilt from their key each time. No model is involved.
"""
from datetime import date, datetime, timedelta

from companion.clock import stamp, zone
from companion.database import decode, many
from companion.life import network
from companion.world import generators, townsfolk

ACTIVE = True
CHANCE = 0.15
FAMILIAR_CHANCE = 0.35
KINDS = {'leisure', 'errand', 'social'}
STEP = timedelta(minutes=45)
CONTEXT_LIMIT = 6
# How many meetings before the companion knows their goal, then their flaw and desire.
KNOWS_GOAL, KNOWS_HEART = 2, 3


def moments(view: dict) -> list[datetime]:
    """Local moments through a slot, every 45 minutes from its start."""
    block, day = view['block'], date.fromisoformat(view['local_date'])
    start = datetime.combine(day, datetime.strptime(block['start'], '%H:%M').time())
    end = datetime.combine(day, datetime.strptime(block['end'], '%H:%M').time())
    end = end if end > start else end + timedelta(days=1)
    result, moment = [], start
    while moment < end and len(result) < 8:
        result.append(moment)
        moment += STEP
    return result


def eligible(companion: dict | None, entry: dict | None, block: dict) -> bool:
    return bool(ACTIVE and companion and entry and isinstance(entry.get('place'), dict) and entry['place'].get('id')
                and block['kind'] in KINDS and not entry.get('ran_into') and not entry.get('gathering')
                and not entry.get('townsfolk'))


def meet(connection, companion: dict | None, entry: dict | None, view: dict, block: dict, seed: str) -> dict | None:
    """Maybe add a townsperson met at this entry's place; returns the entry, changed or not."""
    if not eligible(companion, entry, block):
        return entry
    timeline_id = companion['active_timeline_id']
    history = counts(connection, timeline_id, None, before=view['starts_at'])
    lucky = roll(seed, 'stranger') < CHANCE
    if (not lucky and not history) or many(
            connection, 'SELECT 1 FROM townsfolk_encounters WHERE timeline_id=? AND local_date=? AND slot_key!=?',
            (timeline_id, view['local_date'], view['key'])):
        return entry
    data = network.city(connection, companion)
    found = present(data, entry['place']['id'], view, history)
    if not found:
        return entry
    moment, here = found
    familiar = sorted(key for key in here if key in history)
    strangers = sorted(key for key in here if key not in history)
    if familiar and roll(seed, 'familiar') < FAMILIAR_CHANCE:
        key = familiar[int(roll(seed, 'familiar-who') * len(familiar))]
    elif lucky and strangers:
        key = strangers[int(roll(seed, 'stranger-who') * len(strangers))]
    else:
        return entry
    sheet, times = here[key], len(history.get(key, ()))
    told = line(sheet, data, times, entry['place'], moment.date())
    connection.execute('INSERT OR REPLACE INTO townsfolk_encounters (timeline_id, key, slot_key, place, local_date, '
                       'met_at) VALUES (?, ?, ?, ?, ?, ?)',
                       (timeline_id, key, view['key'], entry['place'].get('name', ''), view['local_date'],
                        view['ends_at']))
    return {**entry, 'summary': f"{entry['summary']} {told}", 'townsfolk': {'key': key, 'times': times + 1}}


def present(data: dict, place_id: str, view: dict, history: dict) -> tuple[datetime, dict] | None:
    """The first moment in the slot when someone is at the place: the people seeded there whose rules put them
    there, and anyone already met whose rules bring them by (a regular elsewhere out for a run, say)."""
    seeded = townsfolk.at_place(data, place_id)
    met = [sheet for key in history if (sheet := townsfolk.find(data, key))]
    for moment in moments(view):
        here = {sheet['key']: sheet for sheet in seeded if townsfolk.whereabouts(sheet, data, moment)['at_place']}
        for sheet in met:
            spot = townsfolk.whereabouts(sheet, data, moment)['place']
            if spot and spot['id'] == place_id:
                here[sheet['key']] = sheet
        if here:
            return moment, here
    return None


def roll(seed: str, label: str) -> float:
    return generators.unit(seed, 'townsfolk', label)


def who(sheet: dict, place: dict) -> str:
    """'the barista there' at their own place, else 'the barista from Daily Grind'."""
    if sheet['place']['id'] == place.get('id'):
        return "a regular there" if not sheet['staff'] else f"the {sheet['role']} there"
    return f"a regular at {sheet['place']['name']}" if not sheet['staff'] else \
        f"the {sheet['role']} from {sheet['place']['name']}"


def line(sheet: dict, data: dict, times: int, place: dict, day: date) -> str:
    """What the companion's diary says about this meeting, more as they get to know them."""
    if times == 0:
        return f"Got talking with {sheet['full']}, {who(sheet, place)}, who {townsfolk.first_impression(sheet)}."
    state = townsfolk.story(sheet, data, day)
    if times + 1 == KNOWS_GOAL:
        lately = f" {state['line']}." if state['line'] else ''
        return f"Saw {sheet['name']} ({who(sheet, place)}) again; turns out {sheet['name']} wants to " \
               f"{state['goal']['text']}.{lately}"
    if state['beat'] == 'achieved':
        return f"Ran into {sheet['name']}, who had big news: {lower(state['line'])}."
    news = f" {state['line']}." if state['line'] else f" {sheet['name']} is still trying to {state['goal']['text']}."
    return f"Caught up with {sheet['name']} ({who(sheet, place)}).{news}"


def lower(text: str) -> str:
    return text[:1].lower() + text[1:] if text and not text[:1].isupper() else text


# Who the companion knows -------------------------------------------------------------------------

def counts(connection, timeline_id: str, now, before: str | None = None) -> dict[str, list[dict]]:
    """Each townsperson's meetings, oldest first: those that happened by `now` when given, else every
    meeting still on the agenda (for the next ones being planned), optionally only before `before`."""
    happened = "AND agenda.status='happened' AND met.met_at<=? " if now is not None else ''
    earlier = 'AND agenda.starts_at<? ' if before else ''
    rows = many(connection, 'SELECT met.*, agenda.entry FROM townsfolk_encounters met JOIN life_agenda agenda ON '
                'agenda.timeline_id=met.timeline_id AND agenda.slot_key=met.slot_key AND agenda.subject=\'companion\' '
                f'WHERE met.timeline_id=? {happened}{earlier}ORDER BY met.met_at',
                (timeline_id, *([stamp(now)] if now is not None else []), *([before] if before else [])))
    result: dict[str, list[dict]] = {}
    for row in rows:
        recorded = ((decode(row['entry']) or {}).get('townsfolk') or {}).get('key') if row['entry'] else None
        if recorded == row['key']:
            result.setdefault(row['key'], []).append({'place': row['place'], 'local_date': row['local_date'],
                                                      'met_at': row['met_at']})
    return result


def known(connection, companion: dict, now) -> list[dict]:
    """Townsfolk the companion has met, most recently seen first, with only what they have learned."""
    data = network.city(connection, companion)
    result = []
    for key, meetings in counts(connection, companion['active_timeline_id'], now).items():
        sheet = townsfolk.find(data, key)
        if sheet:
            result.append(revealed(sheet, data, meetings, now, companion))
    return sorted(result, key=lambda person: person['last_met'], reverse=True)


def revealed(sheet: dict, data: dict, meetings: list[dict], now, companion: dict) -> dict:
    times, last = len(meetings), meetings[-1]
    person = {'key': sheet['key'], 'name': sheet['name'], 'full': sheet['full'], 'pronouns': sheet['pronouns'],
              'age': sheet['age'], 'role': sheet['role'], 'staff': sheet['staff'], 'place': sheet['place'],
              'neighborhood': townsfolk.neighborhood_name(data, sheet['place']['neighborhood']),
              'temperament': sheet['temperament'], 'quirk': sheet['quirk'], 'times': times,
              'first_met': meetings[0]['local_date'], 'first_place': meetings[0]['place'],
              'last_met': last['local_date'], 'last_place': last['place'],
              'goal': None, 'lately': None, 'reached': [], 'routine': None, 'flaw': None, 'desire': None}
    if times >= KNOWS_GOAL:
        state = townsfolk.story(sheet, data, date.fromisoformat(last['local_date']))
        person |= {'goal': state['goal']['text'], 'lately': state['line'] or None, 'reached': state['reached'],
                   'routine': townsfolk.routine_text(sheet)}
    if times >= KNOWS_HEART:
        person |= {'flaw': townsfolk.FLAWS[sheet['flaw']][0], 'desire': townsfolk.DESIRES[sheet['desire']]}
    return person


def text(person: dict) -> str:
    when = date.fromisoformat(person['last_met']).strftime('%d %B').lstrip('0')
    where = f"{person['role']} at {person['place']['name']}" if person['staff'] else \
        f"a regular at {person['place']['name']}"
    hood = f" ({person['neighborhood']})" if person['neighborhood'] else ''
    times = 'once' if person['times'] == 1 else 'twice' if person['times'] == 2 else f"{person['times']} times"
    parts = [f"- {person['full']}, about {round(person['age'], -1) if person['age'] >= 25 else person['age']}, "
             f"{where}{hood}: {person['temperament']}, {person['quirk']}. You've crossed paths {times}, "
             f"last on {when} at {person['last_place']}."]
    if person['goal']:
        lately = f" Last you heard: {person['lately']}." if person['lately'] else ''
        parts.append(f"They are trying to {person['goal']}.{lately}")
    if person['flaw']:
        parts.append(f"You've noticed they're {person['flaw']}; they seem to want {person['desire']}.")
    return ' '.join(parts)


def context_lines(connection, companion: dict, now) -> list[tuple[str, str]]:
    if not ACTIVE:
        return []
    return [(person['key'], text(person)) for person in known(connection, companion, now)[:CONTEXT_LIMIT]]


def whereabouts_now(connection, companion: dict, key: str, now) -> dict | None:
    """Where a townsperson the companion has met probably is right now, by their rules."""
    data = network.city(connection, companion)
    sheet = townsfolk.find(data, key)
    if not sheet:
        return None
    local = now.astimezone(zone(companion['version']['timezone'])).replace(tzinfo=None)
    found = townsfolk.whereabouts(sheet, data, local)
    return {'doing': found['doing'], 'place': found['place'], 'mood': found['mood']}


def copy(connection, parent_id: str, new_id: str, cutoff: str):
    """A fork keeps the townsfolk met before it."""
    for row in many(connection, 'SELECT * FROM townsfolk_encounters WHERE timeline_id=? AND met_at<=?',
                    (parent_id, cutoff)):
        connection.execute('INSERT OR IGNORE INTO townsfolk_encounters (timeline_id, key, slot_key, place, local_date, '
                           'met_at) VALUES (?, ?, ?, ?, ?, ?)',
                           (new_id, row['key'], row['slot_key'], row['place'], row['local_date'], row['met_at']))

