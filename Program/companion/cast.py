"""Switching the main character to someone the companion has met around town (companion/world/townsfolk.py).

The app is always about one companion, the one in slot 1 (companion/characters.py). The user can make a
townsperson the companion has met the main character instead: the townsperson gets a full character
definition, drafted from their rule sheet (or fleshed out by the text model), and from then on the model
plays them. The companion who steps back keeps every chat, memory and timeline, and goes on living in
the same city by the townsfolk's rules (companion/life/encounters.py), where the new main character can
run into them. They still text first and keep their chat (companion/chats.py), so switching is like opening
another chat: it puts them in slot 1 again, history intact.

A match on the dating app (companion/dating.py) becomes a companion the same way, with or without a main
character to step back, and starts as a romance unless the match was for friendship.
"""
from datetime import date

from companion import dating, drafting, story
from companion.characters import by_id, create_in, current, insert_version, named, require_current
from companion.clock import zone
from companion.database import identifier, many, optional
from companion.errors import DomainError, require
from companion.life import ages, encounters, network, town_personality
from companion.memory import pairs
from companion.models import CharacterDefinition, CharacterDraftRequest
from companion.world import catalog, generators, life_details, lifespans, looks, perception, profile_bank, townsfolk

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
# What being a regular at (or working at) a kind of place says they are into; a kind not listed (a landmark,
# a square, their street) says nothing, so it never shows up as an interest itself.
PLACE_INTERESTS = {
    'cafe': 'coffee', 'restaurant': 'good food', 'market': 'cooking', 'bar': 'nights out', 'tavern': 'nights out',
    'nightlife': 'dancing', 'library': 'reading', 'museum': 'history', 'park': 'walking', 'garden': 'gardening',
    'trail': 'hiking', 'beach': 'the beach', 'fitness': 'the gym', 'stadium': 'sports', 'venue': 'live music',
    'shopping': 'browsing the shops', 'workshop': 'making things', 'docks': 'boats',
}
# How a profile's line about who they know begins (shared_text).
SHARED = ('Has crossed paths with', 'Has met the user')
# Their profile speaks of them with the pronouns on their sheet, so pictures and storylines use them too
# (companion/world/looks.pronouns_of reads them back): (subject, noun).
SPOKEN = {'she/her': ('She', 'woman'), 'he/him': ('He', 'man')}
# Careers someone "is" rather than "works as".
STUDYING = ('student',)


# Who is in the cast ---------------------------------------------------------------------------------

def members(database) -> list[dict]:
    """Every companion in the workspace, the main character first, then most recently stepped back."""
    with database.connect() as connection:
        rows = many(connection, 'SELECT c.id, c.slot, c.townsfolk_key, c.stepped_back_at, c.created_at, v.name '
                    'FROM companions c JOIN character_versions v ON v.id=c.active_version_id '
                    'ORDER BY c.slot IS NULL, c.stepped_back_at DESC')
    return [{'id': row['id'], 'name': row['name'], 'main': row['slot'] == 1, 'from_town': bool(row['townsfolk_key']),
             'stepped_back_at': row['stepped_back_at'], 'created_at': row['created_at']} for row in rows]


ALREADY = 'They are already one of your companions. Switch to them instead.'


def met(connection, companion: dict, now) -> tuple[dict, dict, dict]:
    """The city, the town's view of the other companions, and everyone this companion has met by now."""
    data = network.city(connection, companion)
    cast = encounters.town_cast(connection, companion, data)
    return data, cast, encounters.history_for(connection, companion, cast, now)


def townsperson(connection, companion: dict, key: str, now) -> tuple[dict, dict, list[dict], dict | None]:
    """A townsperson the main character or the user's own story has met (companion/story_people.py), with the
    city, the companion's meetings and the story's record; refused otherwise."""
    require(not key.startswith('cast:') and not optional(connection, 'SELECT id FROM companions WHERE townsfolk_key=?', (key,)),
            ALREADY, 409)
    data, _cast, history = met(connection, companion, now)
    in_story = optional(connection, 'SELECT * FROM story_people WHERE key=?', (key,))
    if in_story and townsfolk.find(data, key) is None:
        data = story.city_data(connection, in_story['city_id'])  # Met in the story in another city.
    sheet = townsfolk.find(data, key)
    require(sheet is not None and (key in history or in_story is not None),
            f"{companion['version']['name']} hasn't met them. Only someone they or you have met can take over.", 404)
    return data, sheet, history.get(key, []), in_story


def candidate(connection, key: str, now) -> dict:
    """Someone who may become the main character: a dating match who is not a companion yet, else a
    townsperson the main character has met."""
    require(not key.startswith('cast:'), ALREADY, 409)
    matched = dating.match(connection, key)
    if matched:
        require(optional(connection, 'SELECT id FROM companions WHERE townsfolk_key=?', (key,)) is None,
                ALREADY, 409)
        in_story = optional(connection, 'SELECT * FROM story_people WHERE key=?', (key,))
        still_here(matched['data'], matched['sheet'], now)
        return {'data': matched['data'], 'sheet': matched['sheet'], 'meetings': [], 'focus': current(connection),
                'match': matched, 'in_story': in_story}
    focus = require_current(connection)
    data, sheet, meetings, in_story = townsperson(connection, focus, key, now)
    still_here(data, sheet, now)
    return {'data': data, 'sheet': sheet, 'meetings': meetings, 'focus': focus, 'match': None, 'in_story': in_story}


def still_here(data: dict, sheet: dict, now, then: str = "you can't take over as them") -> None:
    """Refuses someone who has moved away, left their place or passed away (companion/world/turnover.py): keeping
    them in town for good would take back the newcomers who came after them. Code `left_town`, told as news."""
    gone = townsfolk.gone(sheet, data, now.astimezone(zone(data.get('timezone') or 'UTC')).date())
    if gone:
        raise DomainError(f'{townsfolk.gone_line(sheet, data, gone)}, so {then}.', 409, 'left_town')


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


def work_text(data: dict, sheet: dict, career: dict | None = None) -> str:
    """Their job, with what the career is like day to day when the city says, and the place they are known at."""
    place = sheet['place']
    hood = townsfolk.neighborhood_name(data, place.get('neighborhood') or '')
    at = f"{place['name']} in {hood}" if hood else place['name']
    if sheet['kind'] == 'staff':
        return f"Works as the {sheet['role']} at {at}."
    job = sheet.get('occupation') or ''
    verb = 'Is' if job.endswith(STUDYING) else 'Works as'
    summary = (career or {}).get('summary', '').rstrip('.')
    if summary[1:2].islower():
        summary = summary[:1].lower() + summary[1:]
    work = 'Retired.' if job == 'retired' else f"{verb} {article(job)} {job}{f': {summary}' if summary else ''}." \
        if job else ''
    return f"{work} A regular at {at}.".strip()


def article(word: str) -> str:
    return 'an' if word[:1].lower() in 'aeiou' else 'a'


def shared_text(focus_name: str, meetings: list[dict], in_story: dict | None = None) -> str:
    """How they know the companion stepping back and the user. It starts with one of SHARED, so a rewrite of
    the profile by the text model can keep it word for word."""
    met_user = ''
    if in_story:
        count = in_story['meetings']
        met_user = f" Has met the user in person {'once' if count == 1 else 'twice' if count == 2 else f'{count} times'}."
    if not meetings:
        return met_user.strip()
    places = list(dict.fromkeys(meeting['place'] for meeting in meetings if meeting['place']))[:3]
    times = 'once' if len(meetings) == 1 else 'twice' if len(meetings) == 2 else f'{len(meetings)} times'
    where = f" around {' and '.join(places)}" if places else ''
    heard = '' if in_story else f", and has heard about the user through {focus_name}"
    return f"{SHARED[0]} {focus_name} {times}{where}{heard}.{met_user}"


def met_text(found: dict) -> str:
    """How they know the user: through the dating app, or through the companion they ran into."""
    if found['focus'] is None and not found['match']:
        return f'{SHARED[1]} around town; the two of them are friends.'  # A new world's first companion.
    if found['match']:
        met = shared_text('', [], found['in_story'])
        return f"{found['match']['met']}. {met}".strip()
    return shared_text(found['focus']['version']['name'], found['meetings'], found['in_story'])


def relationship(found: dict) -> str:
    """A match starts as a romance unless they matched for friendship; a townsperson met in town as a friend."""
    return 'romance' if found['match'] and found['match']['details']['looking'] != 'friends' else 'friendship'


def starting_closeness(found: dict) -> int:
    """A match is a stranger. A townsperson starts as close as the times they have crossed paths make them:
    with the companion around town, or with the user in their own story."""
    if found['match']:
        return 1
    met = len(found['meetings']) + (found['in_story']['meetings'] if found['in_story'] else 0)
    return next(stage for stage, least in ((3, 6), (2, 3), (1, 0)) if met >= least)


def profile(data: dict, sheet: dict, found: dict, today: date, changed: dict | None = None, age: int | None = None) -> dict:
    """A full character definition from a townsperson's sheet, with no model involved; `changed`: the personality
    sliders the user set on their profile (companion/life/town_personality.py); `age`: how old they are now, birthdays
    since the town started getting older and all (companion/life/ages.py), else their sheet's."""
    age_now = age or sheet['age']
    name, career = sheet['name'], career_for(data, sheet)
    state = townsfolk.story(sheet, data, today)
    home = townsfolk.neighborhood_name(data, sheet['home'])
    flaw = townsfolk.FLAWS[sheet['flaw']][0]
    temperament = sheet['temperament']
    lately = f" Lately: {state['line']}." if state['line'] else ''
    reached = f" Already managed to {'; '.join(state['reached'])}." if state['reached'] else ''
    goal_interest = state['goal']['interest']
    who, noun = SPOKEN.get(sheet.get('pronouns', ''), ('They', ''))
    age = f"{age_now}-year-old {noun}." if noun else f"{age_now} years old."
    laughs, snaps = profile_bank.laughs_and_snaps(sheet)
    verb = 's' if noun else ''
    voice = VOICES.get(temperament) or perception.entry('temperament', temperament).get('town', {}).get('voice', '')
    definition = {
        'name': sheet['full'],
        'identity': f"{age} {work_text(data, sheet, career)} Lives in {home}.",
        'personality': f"{name} is {temperament} and {sheet['quirk']}. People meeting {name} for the first time "
                       f"say {who.lower()} {townsfolk.first_impression(sheet)}. Underneath, {name} {wants(townsfolk.DESIRES[sheet['desire']])}. "
                       f"{who} laugh{verb} at {laughs}, and snap{verb} when {snaps}.",
        'voice': ' '.join([voice, *profile_bank.speech(sheet)]).strip(),
        'flaws': [flaw[:1].upper() + flaw[1:] + '.'],
        'skills': [*profile_bank.job_skills(data, sheet), *([] if sheet['kind'] == 'staff' else [
            f"Knows the regulars and the rhythms of {sheet['place']['name']}."]), profile_bank.middling(sheet)],
        'interests': list(dict.fromkeys(item for item in (goal_interest, PLACE_INTERESTS.get(sheet['place']['kind']))
                                        if item)),
        'background': f"{life_details.background(data, sheet) or f'Has lived in {home} for years.'} Right now "
                      f"{name} is trying to {state['goal']['text']}.{lately}{reached}",
        'history_together': met_text(found),
        'routine': townsfolk.routine_text(sheet)[:1].upper() + townsfolk.routine_text(sheet)[1:] + '.',
        'location': f"{home}, {data['name']}, {data['region']}",
        'home_city': data['id'],
        'timezone': data['timezone'],
        'relationship': relationship(found),
        'starting_closeness': starting_closeness(found),
        'schedule': schedule(data, sheet, career),
        'life_themes': list(career['themes'][:5]) if career else [sheet['place']['name']],
        'money': {'career': career['id'] if career else ''},
    }
    # They keep their face and build, so their pictures show the person met in town (companion/world/looks.py).
    found = {field: value for field, value in looks.for_sheet(sheet, data).items() if field in looks.FIELDS}
    found['age'] = max(found.get('age') or 0, age_now)  # Their face as met, their age as it is now.
    if (folk := sheet.get('folk')) and lifespans.lifespan_of(folk, data) != lifespans.HUMAN_LIFESPAN:
        # A long-lived townsperson stays their kind (companion/world/lifespans.py), and their age, past what the form
        # holds, comes from their identity's "140 years old".
        definition['kind'] = folk
        found.pop('age')
    definition['looks'] = {**found, 'drawn': found}
    # They keep how they came across in town, and how they see themselves.
    lines = perception.for_sheet(data, sheet)
    definition |= {'seen_as': lines['public'], 'sees_self': '\n'.join(lines['private'])}
    # And the personality sliders they had in town.
    definition['personality_sliders'] = town_personality.sliders(sheet, changed)
    return CharacterDefinition.model_validate(definition).model_dump()


def draft(database, key: str) -> dict:
    """Their drafted profile for the form to review; nothing is saved."""
    now = database.clock.now()
    with database.connect() as connection:
        found = candidate(connection, key, now)
        data, sheet, focus = found['data'], found['sheet'], found['focus']
        today = now.astimezone(zone(data['timezone'])).date()
        town = found['match']['town'] if found['match'] else town_personality.town_of(focus)
        changed = town_personality.edited(connection, town, key)
        age = ages.town_age(connection, sheet, today)
        return {'definition': profile(data, sheet, found, today, changed, age),
                'person': person_view(data, {**sheet, 'age': age}),
                'stepping_back': focus['version']['name'] if focus else None, 'matched': found['match'] is not None,
                'ties': pairs.defaults_for_new(connection, others(connection), key, now)}


def others(connection) -> list[dict]:
    """Every companion already in the workspace, the main character first."""
    rows = many(connection, 'SELECT id FROM companions WHERE active_version_id IS NOT NULL ORDER BY slot IS NULL, created_at')
    return [found for row in rows if (found := by_id(connection, row['id']))]


def person_view(data: dict, sheet: dict) -> dict:
    return {'key': sheet['key'], 'name': sheet['name'], 'full': sheet['full'], 'age': sheet['age'],
            'role': sheet['role'], 'kind': sheet['kind'], 'place': sheet['place']['name'],
            'neighborhood': townsfolk.neighborhood_name(data, sheet['home'])}


def idea(definition: dict) -> str:
    """The quick start's idea for the text model: everything the sheet says about them."""
    parts = [definition['identity'], definition['personality'], f"Flaw: {definition['flaws'][0]}",
             definition['background'], definition['history_together'], f"Routine: {definition['routine']}"]
    return ' '.join(part for part in parts if part)[:2000]


async def fleshed(state, key: str) -> dict:
    """Their profile written out by the text model from the sheet, keeping who and where they are."""
    found = draft(state.database, key)
    base = found['definition']
    body = CharacterDraftRequest(idea=idea(base), name=base['name'], relationship=base['relationship'],
                                 age=str(found['person']['age']), home_city=base['home_city'],
                                 timezone=base['timezone'])
    written = (await drafting.draft(state, body, base['personality_sliders']))['definition']
    written |= {field: base[field] for field in ('name', 'location', 'home_city', 'timezone', 'relationship', 'looks',
                                                 'starting_closeness', 'history_together', 'personality_sliders')}
    return {**found, 'definition': written}


# Switching ------------------------------------------------------------------------------------------

def step_back(connection, timestamp: str, companion_id: str):
    """`companion_id` becomes the main character; whoever was steps back with everything they have."""
    connection.execute('UPDATE companions SET slot=NULL, stepped_back_at=? WHERE slot=1', (timestamp,))
    connection.execute('UPDATE companions SET slot=1, stepped_back_at=NULL WHERE id=?', (companion_id,))


def switch(database, key: str, definition, ties=()) -> dict:
    """Make a townsperson the main character, with the definition the user reviewed, and how they know the
    companions already here when the user wrote it on the form (once; companion/memory/pairs.py)."""
    zone(definition.timezone)
    require(definition.name.strip(), 'Give them a name.', 422)
    timestamp = database.now()
    with database.connect(write=True) as connection:
        found = candidate(connection, key, database.clock.now())
        focus = found['focus']
        companion_id, timeline_id = identifier(), identifier()
        # They live in the same town, among the same people, as the companion who met them (or the town the
        # dating app found them in).
        town = found['match']['town'] if found['match'] else focus.get('town_seed') or ''
        connection.execute('INSERT INTO companions (id, slot, townsfolk_key, town_seed, created_at) '
                           'VALUES (?, NULL, ?, ?, ?)', (companion_id, key, town, timestamp))
        note = 'Matched on the dating app.' if found['match'] else f"Met {focus['version']['name']} in town."
        version_id = insert_version(connection, companion_id, 1, definition, note, timestamp)
        connection.execute("INSERT INTO timelines (id, companion_id, status, created_at) VALUES (?, ?, 'active', ?)",
                           (timeline_id, companion_id, timestamp))
        connection.execute('UPDATE companions SET active_version_id=?, active_timeline_id=? WHERE id=?',
                           (version_id, timeline_id, companion_id))
        step_back(connection, timestamp, companion_id)
        for tie in ties:
            pairs.tell(connection, pairs.companion_key(companion_id), pairs.companion_key(tie.companion_id), tie.level,
                       tie.how, timestamp)
        return current(connection)


def add(database, definition) -> dict:
    """A companion the user makes from scratch beside the ones here (the Character page's "Create another
    companion"): they live in the same town as the main character and take over from them. With nobody here yet
    they are simply the first."""
    zone(definition.timezone)
    timestamp = database.now()
    with database.connect(write=True) as connection:
        focus = current(connection)
        if focus is None:
            return create_in(connection, timestamp, definition)
        add_in(connection, timestamp, named(connection, definition), 'Made on the Character page.', focus)
        return current(connection)


def add_in(connection, timestamp: str, definition, note: str, focus: dict) -> str:
    """A new companion in `focus`'s town, who becomes the main character; `focus` steps back with everything they
    have. Also how an imported character arrives (companion/imports/characters.py)."""
    companion_id, timeline_id = identifier(), identifier()
    connection.execute('INSERT INTO companions (id, slot, town_seed, created_at) VALUES (?, NULL, ?, ?)',
                       (companion_id, focus.get('town_seed') or '', timestamp))
    version_id = insert_version(connection, companion_id, 1, definition, note, timestamp)
    connection.execute("INSERT INTO timelines (id, companion_id, status, created_at) VALUES (?, ?, 'active', ?)",
                       (timeline_id, companion_id, timestamp))
    connection.execute('UPDATE companions SET active_version_id=?, active_timeline_id=? WHERE id=?',
                       (version_id, timeline_id, companion_id))
    step_back(connection, timestamp, companion_id)
    return companion_id


def focus_on(database, companion_id: str) -> dict:
    """Switch back to a companion who stepped back; their history is as they left it."""
    with database.connect(write=True) as connection:
        found = optional(connection, 'SELECT slot FROM companions WHERE id=?', (companion_id,))
        if found is None:
            raise DomainError('That companion is no longer in this workspace.', 404)
        if found['slot'] != 1:
            step_back(connection, database.now(), companion_id)
        return current(connection)


# Their own town -------------------------------------------------------------------------------------

def reseed_town(database, fresh: bool) -> dict:
    """Seed new townsfolk for the companion (`fresh`), or go back to the city's shared ones. Everyone they had
    met becomes someone they never met, so those meetings are forgotten, except with the city's notables, who are in
    every town; earlier diary entries keep their words. Only while they are the workspace's one companion, since
    others share their town."""
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        others = connection.execute('SELECT COUNT(*) FROM companions WHERE id!=?', (companion['id'],)).fetchone()[0]
        require(others == 0, 'Your companions share one town. Seeding new townsfolk is only possible with one '
                'companion.', 409)
        town = identifier()[:16] if fresh else ''
        data = network.city(connection, companion)
        connection.execute('UPDATE companions SET town_seed=? WHERE id=?', (town, companion['id']))
        keep_notables(connection, companion['id'], data, {**data, 'town': town})
        return current(connection)


def town_view(database) -> dict:
    """Who stays whatever townsfolk are seeded: the companion's city's notables (a pack's well-known people), by
    name."""
    with database.connect() as connection:
        data = network.city(connection, require_current(connection))
    return {'notables': [notable['name'] for notable in data.get('notables') or ()]}


def keep_notables(connection, companion_id: str, before: dict, after: dict) -> None:
    """Everyone met around town is forgotten, except the city's notables: they are the same people in any town, so
    meetings with them move to the key they have in the new one (their spot comes after the seeded people at their
    place, so it can shift)."""
    timelines = '(SELECT id FROM timelines WHERE companion_id=?)'
    now = townsfolk.notable_keys(after)
    for notable, old in townsfolk.notable_keys(before).items():
        connection.execute(f'UPDATE townsfolk_encounters SET key=? WHERE key=? AND timeline_id IN {timelines}',
                           (f'kept|{now[notable]}', old, companion_id))
    connection.execute(f"DELETE FROM townsfolk_encounters WHERE key NOT LIKE 'kept|%' AND timeline_id IN {timelines}",
                       (companion_id,))
    connection.execute(f"UPDATE townsfolk_encounters SET key=substr(key, 6) WHERE timeline_id IN {timelines}",
                       (companion_id,))


def wants(desire: str) -> str:
    """'wants to be known', but 'longs for someone to look after them' (a desire written as "for …")."""
    return f"{'longs' if desire.startswith('for ') else 'wants'} {desire}"
