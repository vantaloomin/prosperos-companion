"""Switching the main character to someone the companion has met around town (companion/world/townsfolk.py).

The app is always about one companion, the one in slot 1 (companion/characters.py). The user can make a
townsperson the companion has met the main character instead: the townsperson gets a full character
definition, drafted from their rule sheet (or fleshed out by the text model), and from then on the model
plays them. The companion who steps back keeps every chat, memory and timeline, and goes on living in
the same city by the townsfolk's rules (companion/life/encounters.py), where the new main character can
run into them. Switching back puts them in slot 1 again, history intact.
"""
from datetime import date

from companion import drafting
from companion.characters import current, insert_version, require_current
from companion.clock import zone
from companion.database import identifier, many, optional
from companion.errors import DomainError, require
from companion.life import encounters, network
from companion.models import CharacterDefinition, CharacterDraftRequest
from companion.world import catalog, generators, townsfolk

# A shift's part of the day sets when they sleep, as (bed, wake).
SLEEP = {'morning': ('21:30', '05:00'), 'afternoon': ('23:30', '08:00'), 'evening': ('01:30', '09:30'),
         'late': ('01:30', '09:30')}
# How each temperament talks, for the voice field.
VOICES = {
    'warm': 'Friendly and easy to talk to; asks after people and remembers the answers.',
    'gruff': 'Short sentences and a flat delivery at first; warms up once they know someone.',
    'shy': 'Quiet and a little hesitant; opens up in writing more than in person.',
    'chatty': 'Talks fast and goes off on tangents; laughs at their own stories.',
    'deadpan': 'Bone-dry humor, delivered completely straight.',
    'cheerful': 'Upbeat and quick to laugh; lots of exclamation marks.',
    'anxious': 'Second-guesses themselves mid-sentence and apologizes more than they need to.',
    'easygoing': 'Unhurried and relaxed; nothing seems to rattle them.',
    'driven': 'Direct and to the point; always has a plan.',
    'dreamy': 'Wanders off on ideas and loses the thread, then laughs about it.',
}
# What working toward each goal says about them.
GOAL_INTERESTS = {
    'own-place': 'saving up', 'race': 'running', 'band': 'music', 'exam': 'studying', 'novel': 'writing',
    'reconcile': 'family', 'move': 'apartment hunting', 'language': 'languages', 'promotion': 'work',
    'art': 'painting', 'dog': 'dogs', 'strong': 'lifting', 'side': 'their side business',
}


# Who is in the cast ---------------------------------------------------------------------------------

def members(database) -> list[dict]:
    """Every companion in the workspace, the main character first, then most recently stepped back."""
    with database.connect() as connection:
        rows = many(connection, 'SELECT c.id, c.slot, c.townsfolk_key, c.stepped_back_at, c.created_at, v.name '
                    'FROM companions c JOIN character_versions v ON v.id=c.active_version_id '
                    'ORDER BY c.slot IS NULL, c.stepped_back_at DESC')
    return [{'id': row['id'], 'name': row['name'], 'main': row['slot'] == 1, 'from_town': bool(row['townsfolk_key']),
             'stepped_back_at': row['stepped_back_at'], 'created_at': row['created_at']} for row in rows]


def met(connection, companion: dict, now) -> tuple[dict, dict, dict]:
    """The city, the town's view of the other companions, and everyone this companion has met by now."""
    data = network.city(connection, companion)
    cast = encounters.town_cast(connection, companion, data)
    return data, cast, encounters.history_for(connection, companion, cast, now)


def townsperson(connection, companion: dict, key: str, now) -> tuple[dict, dict, list[dict]]:
    """A townsperson the main character has met, with the city and their meetings; refused otherwise."""
    require(not key.startswith('cast:'), 'They are already one of your companions. Switch to them instead.', 409)
    data, _cast, history = met(connection, companion, now)
    sheet = townsfolk.find(data, key)
    require(sheet is not None and key in history,
            f"{companion['version']['name']} hasn't met them. Only someone they have met can take over.", 404)
    return data, sheet, history[key]


# Their profile --------------------------------------------------------------------------------------

def career_for(data: dict, sheet: dict) -> dict | None:
    occupation = sheet.get('occupation') or ''
    return next((career for career in catalog.careers_for(data).values()
                 if career['name'].lower() in (occupation, sheet['role'])), None)


def clock(minutes: int) -> str:
    minutes %= 24 * 60
    return f'{minutes // 60:02d}:{minutes % 60:02d}'


def schedule(data: dict, sheet: dict, career: dict | None) -> list[dict]:
    """The week the life simulation follows: the shift they already work in town, else their career's week,
    else sleep and their usual visits."""
    shifts = sheet.get('shifts')
    if shifts:
        bed, wake = SLEEP[shifts['part']]
        themes = (career['themes'][:4] if career else []) + [sheet['place']['name']]
        return generators.week(sheet['role'].capitalize(), 'work', shifts['days'], clock(shifts['window'][0]),
                               clock(shifts['window'][1]), bed, wake, themes)
    if career:
        return generators.schedule(career, sheet['key'])
    visits = sheet['visits']
    return [{'key': 'sleep', 'label': 'Asleep', 'kind': 'sleep', 'days': list(range(7)), 'start': '23:00',
             'end': '07:00', 'themes': []},
            {'key': 'usual-spot', 'label': f"At {sheet['place']['name']}", 'kind': 'leisure', 'days': visits['days'],
             'start': clock(visits['window'][0]), 'end': clock(visits['window'][1]), 'themes': [sheet['place']['name']]}]


def work_text(data: dict, sheet: dict) -> str:
    place = sheet['place']
    hood = townsfolk.neighborhood_name(data, place.get('neighborhood') or '')
    at = f"{place['name']} in {hood}" if hood else place['name']
    if sheet['kind'] == 'staff':
        return f"Works as the {sheet['role']} at {at}."
    job = sheet.get('occupation') or ''
    work = 'Retired.' if job == 'retired' else f'Works as {article(job)} {job}.' if job else ''
    return f"{work} A regular at {at}.".strip()


def article(word: str) -> str:
    return 'an' if word[:1].lower() in 'aeiou' else 'a'


def shared_text(focus_name: str, meetings: list[dict]) -> str:
    places = list(dict.fromkeys(meeting['place'] for meeting in meetings if meeting['place']))[:3]
    times = 'once' if len(meetings) == 1 else 'twice' if len(meetings) == 2 else f'{len(meetings)} times'
    where = f" around {' and '.join(places)}" if places else ''
    return f"Has crossed paths with {focus_name} {times}{where}, and has heard about the user through {focus_name}."


def profile(data: dict, sheet: dict, focus: dict, meetings: list[dict], today: date) -> dict:
    """A full character definition from a townsperson's sheet, with no model involved."""
    name, career = sheet['name'], career_for(data, sheet)
    state = townsfolk.story(sheet, data, today)
    home = townsfolk.neighborhood_name(data, sheet['home'])
    flaw = townsfolk.FLAWS[sheet['flaw']][0]
    temperament = sheet['temperament']
    lately = f" Lately: {state['line']}." if state['line'] else ''
    reached = f" Already managed to {'; '.join(state['reached'])}." if state['reached'] else ''
    goal_interest = GOAL_INTERESTS.get(state['goal']['id'])
    definition = {
        'name': sheet['full'],
        'identity': f"{sheet['age']}. {work_text(data, sheet)} Lives in {home}.",
        'personality': f"{name} is {temperament} and {sheet['quirk']}. People meeting {name} for the first time "
                       f"say they {townsfolk.first_impression(sheet)}. Underneath, {name} wants "
                       f"{townsfolk.DESIRES[sheet['desire']]}.",
        'voice': VOICES.get(temperament, ''),
        'flaws': [flaw[:1].upper() + flaw[1:] + '.'],
        'skills': [f"Knows the regulars and the rhythms of {sheet['place']['name']}."],
        'interests': [item for item in (goal_interest, sheet['place']['kind']) if item],
        'background': f"Has lived in {home} for years. Right now {name} is trying to {state['goal']['text']}."
                      f"{lately}{reached} {shared_text(focus['version']['name'], meetings)}",
        'routine': townsfolk.routine_text(sheet)[:1].upper() + townsfolk.routine_text(sheet)[1:] + '.',
        'location': f"{home}, {data['name']}, {data['region']}",
        'home_city': data['id'],
        'timezone': data['timezone'],
        'relationship': 'friendship',
        'schedule': schedule(data, sheet, career),
        'life_themes': list(career['themes'][:5]) if career else [sheet['place']['name']],
        'money': {'career': career['id'] if career else ''},
    }
    return CharacterDefinition.model_validate(definition).model_dump()


def draft(database, key: str) -> dict:
    """Their drafted profile for the form to review; nothing is saved."""
    now = database.clock.now()
    with database.connect() as connection:
        focus = require_current(connection)
        data, sheet, meetings = townsperson(connection, focus, key, now)
        today = now.astimezone(zone(focus['version']['timezone'])).date()
        return {'definition': profile(data, sheet, focus, meetings, today), 'person': person_view(data, sheet),
                'stepping_back': focus['version']['name']}


def person_view(data: dict, sheet: dict) -> dict:
    return {'key': sheet['key'], 'name': sheet['name'], 'full': sheet['full'], 'age': sheet['age'],
            'role': sheet['role'], 'kind': sheet['kind'], 'place': sheet['place']['name'],
            'neighborhood': townsfolk.neighborhood_name(data, sheet['home'])}


def idea(definition: dict) -> str:
    """The quick start's idea for the text model: everything the sheet says about them."""
    parts = [definition['identity'], definition['personality'], f"Flaw: {definition['flaws'][0]}",
             definition['background'], f"Routine: {definition['routine']}"]
    return ' '.join(parts)[:2000]


async def fleshed(state, key: str) -> dict:
    """Their profile written out by the text model from the sheet, keeping who and where they are."""
    found = draft(state.database, key)
    base = found['definition']
    body = CharacterDraftRequest(idea=idea(base), name=base['name'], relationship=base['relationship'],
                                 age=str(found['person']['age']), home_city=base['home_city'],
                                 timezone=base['timezone'])
    written = (await drafting.draft(state, body))['definition']
    shared = base['background'][base['background'].rfind('Has crossed paths'):]
    written |= {field: base[field] for field in ('name', 'location', 'home_city', 'timezone', 'relationship')}
    written['background'] = f"{written['background'].rstrip()} {shared}".strip()[:12000]
    return {**found, 'definition': written}


# Switching ------------------------------------------------------------------------------------------

def step_back(connection, timestamp: str, companion_id: str):
    """`companion_id` becomes the main character; whoever was steps back with everything they have."""
    connection.execute('UPDATE companions SET slot=NULL, stepped_back_at=? WHERE slot=1', (timestamp,))
    connection.execute('UPDATE companions SET slot=1, stepped_back_at=NULL WHERE id=?', (companion_id,))


def switch(database, key: str, definition) -> dict:
    """Make a townsperson the main character, with the definition the user reviewed."""
    zone(definition.timezone)
    timestamp = database.now()
    with database.connect(write=True) as connection:
        focus = require_current(connection)
        townsperson(connection, focus, key, database.clock.now())
        companion_id, timeline_id = identifier(), identifier()
        connection.execute('INSERT INTO companions (id, slot, townsfolk_key, created_at) VALUES (?, NULL, ?, ?)',
                           (companion_id, key, timestamp))
        version_id = insert_version(connection, companion_id, 1, definition, f"Met {focus['version']['name']} in town.",
                                    timestamp)
        connection.execute("INSERT INTO timelines (id, companion_id, status, created_at) VALUES (?, ?, 'active', ?)",
                           (timeline_id, companion_id, timestamp))
        connection.execute('UPDATE companions SET active_version_id=?, active_timeline_id=? WHERE id=?',
                           (version_id, timeline_id, companion_id))
        step_back(connection, timestamp, companion_id)
        return current(connection)


def focus_on(database, companion_id: str) -> dict:
    """Switch back to a companion who stepped back; their history is as they left it."""
    with database.connect(write=True) as connection:
        found = optional(connection, 'SELECT slot FROM companions WHERE id=?', (companion_id,))
        if found is None:
            raise DomainError('That companion is no longer in this workspace.', 404)
        if found['slot'] != 1:
            step_back(connection, database.now(), companion_id)
        return current(connection)
