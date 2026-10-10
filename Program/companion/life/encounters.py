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

from companion.characters import for_timeline
from companion.clock import stamp, zone
from companion.database import decode, encode, many, optional, settings
from companion.life import money, network
from companion.world import generators, intimacy, newcomers, perception, townsfolk

ACTIVE = True
CHANCE = 0.15
FAMILIAR_CHANCE = 0.35
# Another companion there by their own day stands out from a crowd of strangers (small world).
FELLOW_CHANCE = 0.5
KINDS = {'leisure', 'errand', 'social'}
# On the way out to a morning shift or class, the companion may meet neighbors on their street.
COMMUTE_KINDS = {'work', 'study'}
MORNING = ('05:00', '11:00')
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


def setting(connection, companion: dict | None, entry: dict | None, view: dict, block: dict):
    """Where a meeting could happen in this slot, as (place, local moments, on the way out), or None: the
    entry's place on a leisure, errand or social outing, or the companion's own street on the way to a
    morning shift or class (neighbors at the stop)."""
    if not ACTIVE or not companion or not entry or entry.get('ran_into') or entry.get('gathering') \
            or entry.get('townsfolk'):
        return None
    place = entry.get('place')
    if block['kind'] in KINDS and isinstance(place, dict) and place.get('id'):
        return place, moments(view), False
    if block['kind'] in COMMUTE_KINDS and MORNING[0] <= block['start'] < MORNING[1]:
        data = network.city(connection, companion)
        hood = home_hood(data, companion['version']['definition'])
        if hood:
            start = moments(view)[0]
            return townsfolk.street(data, hood), [start - timedelta(minutes=25), start - timedelta(minutes=10)], True
    return None


def home_hood(data: dict, definition: dict) -> str | None:
    """The companion's neighborhood id: the one their budget puts them in (companion/life/money.py), else one
    named in their location."""
    found = money.profile(definition)
    names = [found.neighborhood] if found and found.city['id'] == data['id'] else []
    text = ' '.join(definition.get(key) or '' for key in ('near', 'location')).casefold()
    for hood in data['neighborhoods']:
        if hood['name'] in names or (text and hood['name'].casefold() in text):
            return hood['id']
    return None


def meet(connection, companion: dict | None, entry: dict | None, view: dict, block: dict, seed: str) -> dict | None:
    """Maybe add a townsperson met at this entry's place; returns the entry, changed or not."""
    if not ACTIVE or not companion or not entry:
        return entry
    timeline_id = companion['active_timeline_id']
    data = network.city(connection, companion)
    cast = town_cast(connection, companion, data)
    history = history_for(connection, companion, cast, None, before=view['starts_at'])
    lucky, fellow = roll(seed, 'stranger') < CHANCE, roll(seed, 'fellow') < FELLOW_CHANCE
    if (not lucky and not fellow and not history) or many(
            connection, 'SELECT 1 FROM townsfolk_encounters WHERE timeline_id=? AND local_date=? AND slot_key!=?',
            (timeline_id, view['local_date'], view['key'])):
        return entry
    found = setting(connection, companion, entry, view, block)
    if not found:
        return entry
    place, times_of_day, on_the_way = found
    plans = cast_plans(connection, cast, times_of_day)
    seen = present(data, place['id'], times_of_day, history, cast, plans)
    key = seen and pick(seen[1], history, lucky, seed, fellow and plans)
    if not key:
        return entry
    moment, here = seen
    sheet, times = resolve(data, key, cast), len(history.get(key, ()))
    home = home_hood(data, companion['version']['definition'])
    last = date.fromisoformat(history[key][-1]['local_date']) if times else None
    told = line(sheet, data, times, place, moment.date(), home, here[key].get('doing', ''), last)
    told = f'On the way out that morning, {told[:1].lower()}{told[1:]}' if on_the_way else told
    connection.execute('INSERT OR REPLACE INTO townsfolk_encounters (timeline_id, key, slot_key, place, local_date, '
                       'met_at) VALUES (?, ?, ?, ?, ?, ?)',
                       (timeline_id, key, view['key'], place.get('name', ''), view['local_date'], view['ends_at']))
    if key in plans:
        mirror(connection, companion, data, plans[key], place, moment, times, last)
    return {**entry, 'summary': f"{entry['summary']} {told}", 'townsfolk': {'key': key, 'times': times + 1}}


def pick(here: dict, history: dict, lucky: bool, seed: str, fellows: dict | None = None) -> str | None:
    """Who of the people here the companion talks to: another companion out on their own day when `fellows`
    (cast_plans) has them here, else someone familiar now and then, else a stranger on a lucky day."""
    among = sorted(key for key in here if key in (fellows or {}))
    if among:
        return among[int(roll(seed, 'fellow-who') * len(among))]
    familiar = sorted(key for key in here if key in history)
    strangers = sorted(key for key in here if key not in history)
    if familiar and roll(seed, 'familiar') < FAMILIAR_CHANCE:
        return familiar[int(roll(seed, 'familiar-who') * len(familiar))]
    if lucky and strangers:
        return strangers[int(roll(seed, 'stranger-who') * len(strangers))]
    return None


def present(data: dict, place_id: str, times_of_day: list[datetime], history: dict,
            cast: dict | None = None, plans: dict | None = None) -> tuple[datetime, dict] | None:
    """The first of these moments when someone is at the place, with what each is doing: the people seeded
    there, residents whose rules bring them there, anyone already met whose rules bring them by, and other
    companions in the town, where their own day puts them (`plans`, from cast_plans) or else by the town's rules.
    Never the companion themself."""
    cast, plans = cast or NO_CAST, plans or {}
    seeded = [] if place_id.startswith('~') else townsfolk.at_place(data, place_id)
    locals_ = townsfolk.reaching(data, place_id)
    met = [sheet for key in history if (sheet := resolve(data, key, cast))]
    people = [sheet for sheet in [*seeded, *locals_, *met, *cast['sheets'].values()]
              if sheet['key'] not in cast['own'] and sheet['key'] not in cast['aliases']]
    for moment in times_of_day:
        here = {}
        for sheet in people:
            found = planned(plans[sheet['key']], moment) if sheet['key'] in plans else \
                townsfolk.whereabouts(sheet, data, moment)
            if found['place'] and found['place']['id'] == place_id:
                here[sheet['key']] = {'doing': found['doing']}
        if here:
            return moment, here
    return None


def roll(seed: str, label: str) -> float:
    return generators.unit(seed, 'townsfolk', label)


def who(sheet: dict, place: dict, data: dict, home: str | None, doing: str = '') -> str:
    """'the barista there', 'a regular at Daily Grind', 'a neighbor waiting for the bus', 'a local from Canton'."""
    if sheet['kind'] == 'resident':
        neighbor = 'a neighbor' if sheet['home'] == home else \
            f"a local from {townsfolk.neighborhood_name(data, sheet['home'])}"
        return f'{neighbor} {doing}' if doing.startswith('waiting for') else neighbor
    if sheet['place']['id'] == place.get('id'):
        return "a regular there" if not sheet['staff'] else f"the {sheet['role']} there"
    return f"a regular at {sheet['place']['name']}" if not sheet['staff'] else \
        f"the {sheet['role']} from {sheet['place']['name']}"


def line(sheet: dict, data: dict, times: int, place: dict, day: date, home: str | None = None,
         doing: str = '', last: date | None = None) -> str:
    """What the companion's diary says about this meeting, more as they get to know them."""
    said = who(sheet, place, data, home, doing)
    if times == 0:
        return f"Got talking with {sheet['full']}, {said}, who {townsfolk.first_impression(sheet)}."
    state = townsfolk.story(sheet, data, day)
    if times + 1 == KNOWS_GOAL:
        lately = f" {state['line']}." if state['line'] else ''
        return f"Saw {sheet['name']} ({said}) again; turns out {sheet['name']} wants to " \
               f"{state['goal']['text']}.{lately}"
    fresh = last is None or townsfolk.week_of(last) != townsfolk.week_of(day)
    if state['beat'] == 'achieved' and fresh:
        return f"Ran into {sheet['name']}, who had big news: {lower(state['line'])}."
    if not fresh:
        return f"Caught up with {sheet['name']} ({said}) again."
    news = f" {state['line']}." if state['line'] else f" {sheet['name']} is still trying to {state['goal']['text']}."
    return f"Caught up with {sheet['name']} ({said}).{news}"


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
    cast = town_cast(connection, companion, data)
    found = settings(connection)
    result = []
    for key, meetings in history_for(connection, companion, cast, now).items():
        sheet = resolve(data, key, cast)
        if sheet:
            person = revealed(sheet, data, meetings, now, companion)
            if found['adult_side']:
                person |= adult_side(sheet, len(meetings), bool(found['show_adult_side']))
            result.append(person)
    return sorted(result, key=lambda person: person['last_met'], reverse=True)


def revealed(sheet: dict, data: dict, meetings: list[dict], now, companion: dict) -> dict:
    times, last = len(meetings), meetings[-1]
    person = {'key': sheet['key'], 'name': sheet['name'], 'full': sheet['full'], 'pronouns': sheet['pronouns'],
              'age': sheet['age'], 'role': sheet['role'], 'kind': sheet['kind'], 'staff': sheet['staff'],
              'place': sheet['place'],
              'neighborhood': townsfolk.neighborhood_name(data, sheet['home'] if sheet['kind'] == 'resident'
                                                          else sheet['place']['neighborhood']),
              'temperament': sheet['temperament'], 'quirk': sheet['quirk'], 'times': times,
              'first_met': meetings[0]['local_date'], 'first_place': meetings[0]['place'],
              'last_met': last['local_date'], 'last_place': last['place'],
              'goal': None, 'lately': None, 'reached': [], 'routine': None, 'flaw': None, 'desire': None,
              'cast': sheet.get('cast'), 'comes_across': None, 'says_they_are': None}
    person |= perception.revealed(data, sheet, times)
    if times >= KNOWS_GOAL:
        state = townsfolk.story(sheet, data, date.fromisoformat(last['local_date']))
        person |= {'goal': state['goal']['text'], 'lately': state['line'] or None, 'reached': state['reached'],
                   'routine': townsfolk.routine_text(sheet)}
    if times >= KNOWS_HEART:
        person |= {'flaw': sheet.get('flaw_text') or townsfolk.FLAWS[sheet['flaw']][0],
                   'desire': townsfolk.DESIRES[sheet['desire']]}
    return person


def adult_side(sheet: dict, times: int, shown: bool) -> dict:
    """With Settings > Realism > Adult side of life on (companion/world/intimacy.py): who they're drawn to once
    the companion knows their heart, and, as a hidden value the user can show, all of it for the user's eyes only.
    A companion living in town keeps theirs on their own sheet."""
    found = None if sheet.get('cast') else intimacy.for_sheet(sheet)
    if not found:
        return {}
    return {'orientation': found['orientation'] if times >= KNOWS_HEART else None,
            'adult_side': intimacy.view(found) if shown else None}


def text(person: dict) -> str:
    when = date.fromisoformat(person['last_met']).strftime('%d %B').lstrip('0')
    if person['kind'] == 'resident':
        where, hood = f"{person['role']}, lives in {person['neighborhood']}", ''
    else:
        where = f"{person['role']} at {person['place']['name']}" if person['staff'] else \
            f"a regular at {person['place']['name']}"
        hood = f" ({person['neighborhood']})" if person['neighborhood'] else ''
    times = 'once' if person['times'] == 1 else 'twice' if person['times'] == 2 else f"{person['times']} times"
    parts = [f"- {person['full']}, about {round(person['age'], -1) if person['age'] >= 25 else person['age']}, "
             f"{where}{hood}: {person['temperament']}, {person['quirk']}. You've crossed paths {times}, "
             f"last on {when} at {person['last_place']}."]
    if person.get('comes_across'):
        parts.append(f"How they come across: {person['comes_across']}")
    if person['goal']:
        lately = f" Last you heard: {person['lately']}." if person['lately'] else ''
        parts.append(f"They are trying to {person['goal']}.{lately}")
    if person['flaw']:
        parts.append(f"You've noticed they're {person['flaw']}; they seem to want {person['desire']}.")
    if person.get('orientation'):
        parts.append(f"From what you've picked up, they're {person['orientation']}.")
    if person.get('says_they_are'):
        parts.append(f"They once said they're {person['says_they_are']}.")
    if person.get('cast'):
        parts.append('They know the user well.')
    return ' '.join(parts)


def context_lines(connection, companion: dict, now) -> list[tuple[str, str]]:
    if not ACTIVE:
        return []
    return [(person['key'], text(person)) for person in known(connection, companion, now)[:CONTEXT_LIMIT]]


def whereabouts_now(connection, companion: dict, key: str, now) -> dict | None:
    """Where a townsperson the companion has met probably is right now, by their rules."""
    data = network.city(connection, companion)
    sheet = resolve(data, key, town_cast(connection, companion, data))
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



# Other companions in the town ------------------------------------------------------------------------
#
# When the user switches the main character (companion/cast.py), the companion who steps back keeps
# living in the same city by the same rules as the townsfolk, under the key `cast:<companion id>`: a
# townsperson who had become a companion goes back to their old sheet under their current name, and an
# original companion gets a resident's sheet in their own neighborhood. Meetings are shared both ways:
# what one companion's diary says about meeting the other counts for the other too.

NO_CAST = {'sheets': {}, 'aliases': {}, 'own': set(), 'others': []}


def town_cast(connection, companion: dict, data: dict) -> dict:
    """The other companions as the town sees them: their rule sheets by key, the townsfolk keys that now
    mean them, and this companion's own keys (never met by themself)."""
    others = many(connection, 'SELECT c.id, c.townsfolk_key, c.active_timeline_id, c.stepped_back_at, v.definition '
                  'FROM companions c JOIN character_versions v ON v.id=c.active_version_id WHERE c.id!=?',
                  (companion['id'],))
    own = {f"cast:{companion['id']}", *([companion['townsfolk_key']] if companion.get('townsfolk_key') else [])}
    if not others:
        return {**NO_CAST, 'own': own}
    sheets, aliases = {}, {}
    for row in others:
        definition = decode(row['definition'])
        if newcomers.city_for(connection, definition)['id'] != data['id']:
            continue
        sheet = stand_in(data, row['id'], row['townsfolk_key'], definition)
        if sheet:
            sheets[sheet['key']] = sheet
            if row['townsfolk_key']:
                aliases[row['townsfolk_key']] = sheet['key']
    return {'sheets': sheets, 'aliases': aliases, 'own': own, 'others': others}


def stand_in(data: dict, companion_id: str, townsfolk_key: str | None, definition: dict) -> dict | None:
    """A companion who is not the main character, as a townsperson: who they were in town, or a resident of
    their own neighborhood. The caller checks they live in this city."""
    base = townsfolk.find(data, townsfolk_key) if townsfolk_key else None
    extra = {}
    if base is None:
        if not data.get('neighborhoods'):  # No city set (naming.DEFAULT_CITY): nowhere to live in town.
            return None
        hood = home_hood(data, definition) or data['neighborhoods'][0]['id']
        base = townsfolk.resident(data, hood, 0, key=f'cast:{companion_id}')
        found = money.profile(definition)
        if found and found.career:
            extra['role'] = extra['occupation'] = found.career['name'].lower()
        if definition.get('flaws'):
            extra['flaw_text'] = definition['flaws'][0].rstrip('.')
    name = definition['name'].strip()
    # They come across in town the way they do everywhere else.
    extra['perception'] = perception.for_companion(companion_id, definition)
    return {**base, **extra, 'key': f'cast:{companion_id}', 'name': name.split()[0], 'full': name,
            'cast': companion_id}


def resolve(data: dict, key: str, cast: dict) -> dict | None:
    """The person a key names: another companion (under their own key or the townsfolk key they came from),
    else a townsperson."""
    key = cast['aliases'].get(key, key)
    return cast['sheets'].get(key) or (None if key.startswith('cast:') else townsfolk.find(data, key))


def history_for(connection, companion: dict, cast: dict, now, before: str | None = None) -> dict[str, list[dict]]:
    """Each person's meetings with this companion: their own diary's, under the keys the town uses now, plus
    every other companion's meetings with them. Every companion keeps living (#216), so either diary can hold a
    meeting, and both may hold the same one (`mirror`): a day counts once."""
    merged: dict[str, list[dict]] = {}
    for key, meetings in counts(connection, companion['active_timeline_id'], now, before).items():
        if key not in cast['own']:
            merged.setdefault(cast['aliases'].get(key, key), []).extend(meetings)
    for row in cast['others']:
        theirs = counts(connection, row['active_timeline_id'], now, before)
        shared = [meeting for key, meetings in theirs.items() if key in cast['own'] for meeting in meetings]
        if shared and f"cast:{row['id']}" in cast['sheets']:
            merged.setdefault(f"cast:{row['id']}", []).extend(shared)
    return {key: once_a_day(meetings) for key, meetings in merged.items()}


def once_a_day(meetings: list[dict]) -> list[dict]:
    """Meetings oldest first, one a day: two companions' diaries can tell the same meeting."""
    days, result = set(), []
    for meeting in sorted(meetings, key=lambda meeting: meeting['met_at']):
        if meeting['local_date'] not in days:
            days.add(meeting['local_date'])
            result.append(meeting)
    return result



# Small world: companions crossing paths ------------------------------------------------------------
#
# Every companion lives their own days (companion/life/simulation.py, #216), so another companion is wherever
# their own agenda puts them, not where the town's rules would: two companions who both go to the same gym on
# Thursday evenings can run into each other there. A meeting goes in both diaries, and the first one is news
# worth texting the user about (crossed_paths, used by companion/life/openers.py).

def cast_plans(connection, cast: dict, times_of_day: list[datetime]) -> dict[str, list[dict]]:
    """Where the other companions in town are on the days of these moments, from their own agendas:
    {cast key: [spot]}. A day their agenda doesn't reach yet finds them nowhere: whichever of the two plans that
    day later sees where the other is. Only a companion who has never lived a day is left out, and the town's
    rules place them instead."""
    days = sorted({day.isoformat() for moment in times_of_day for day in (moment.date(), moment.date() - timedelta(days=1))})
    if not days or not cast['others']:
        return {}
    result = {}
    for row in cast['others']:
        key = f"cast:{row['id']}"
        if key not in cast['sheets'] or not row['active_timeline_id']:
            continue
        rows = many(connection, 'SELECT id, local_date, block, entry, status FROM life_agenda WHERE timeline_id=? '
                    f"AND subject='companion' AND local_date IN ({','.join('?' * len(days))})",
                    (row['active_timeline_id'], *days))
        if rows or optional(connection, "SELECT 1 FROM life_agenda WHERE timeline_id=? AND subject='companion' LIMIT 1",
                            (row['active_timeline_id'],)):
            result[key] = [spot(found) for found in rows]
    return result


def spot(row) -> dict:
    """One slot of another companion's day, as local times, where they are and what they are doing there."""
    block, entry = decode(row['block']), decode(row['entry']) if row['entry'] else None
    day = date.fromisoformat(row['local_date'])
    start = datetime.combine(day, datetime.strptime(block['start'], '%H:%M').time())
    end = datetime.combine(day, datetime.strptime(block['end'], '%H:%M').time())
    place = (entry or {}).get('place')
    return {'id': row['id'], 'start': start, 'end': end if end > start else end + timedelta(days=1),
            'place': place if isinstance(place, dict) and place.get('id') else None, 'entry': entry,
            'status': row['status'], 'doing': (entry or {}).get('activity', '')}


def planned(spots: list[dict], moment: datetime) -> dict:
    """Where another companion's own day has them at this moment (no place: at home, asleep or travelling)."""
    found = next((item for item in spots if item['start'] <= moment < item['end']), None)
    return {'place': found and found['place'], 'doing': ''}


def mirror(connection, companion: dict, data: dict, spots: list[dict], place: dict, moment: datetime, times: int,
           last: date | None):
    """The other companion's diary tells the same meeting, when their slot there is still to come and has no
    meeting of its own yet."""
    found = next((item for item in spots if item['start'] <= moment < item['end']), None)
    entry = found and found['entry']
    if not entry or found['status'] != 'upcoming' or entry.get('townsfolk') or entry.get('ran_into') \
            or entry.get('gathering'):
        return
    row = optional(connection, 'SELECT * FROM life_agenda WHERE id=?', (found['id'],))
    other = for_timeline(connection, row['timeline_id'])
    sheet = other and stand_in(data, companion['id'], companion.get('townsfolk_key'), companion['version']['definition'])
    if not sheet or many(connection, 'SELECT 1 FROM townsfolk_encounters WHERE timeline_id=? AND local_date=?',
                         (row['timeline_id'], row['local_date'])):
        return
    told = line(sheet, data, times, place, moment.date(), home_hood(data, other['version']['definition']), '', last)
    changed = {**entry, 'summary': f"{entry['summary']} {told}", 'townsfolk': {'key': sheet['key'], 'times': times + 1}}
    connection.execute('UPDATE life_agenda SET entry=?, prepared=NULL WHERE id=?', (encode(changed), row['id']))
    connection.execute('INSERT OR REPLACE INTO townsfolk_encounters (timeline_id, key, slot_key, place, local_date, '
                       'met_at) VALUES (?, ?, ?, ?, ?, ?)',
                       (row['timeline_id'], sheet['key'], row['slot_key'], place.get('name', ''), row['local_date'],
                        row['ends_at']))


def crossed_paths(connection, companion: dict, now, within: timedelta) -> list[dict]:
    """Other companions this one met for the first time in the last `within`, by their own diary:
    [{key, companion_id, place, met_at}]."""
    rows = many(connection, 'SELECT met.key, met.place, met.met_at, agenda.entry FROM townsfolk_encounters met '
                'JOIN life_agenda agenda ON agenda.timeline_id=met.timeline_id AND agenda.slot_key=met.slot_key '
                "AND agenda.subject='companion' WHERE met.timeline_id=? AND met.key LIKE 'cast:%' "
                "AND agenda.status='happened' AND met.met_at>? AND met.met_at<=? ORDER BY met.met_at",
                (companion['active_timeline_id'], stamp(now - within), stamp(now)))
    result = []
    for row in rows:
        recorded = (decode(row['entry']) or {}).get('townsfolk') or {} if row['entry'] else {}
        if recorded.get('key') == row['key'] and recorded.get('times') == 1:
            result.append({'key': row['key'], 'companion_id': row['key'][5:], 'place': row['place'],
                           'met_at': row['met_at']})
    return result
