"""Townsfolk the user can pursue in their own story (docs/story.md, "Asking someone out").

When the user asks someone in the scene out, that person's own rules answer, the same ones the dating app reads
(companion/world/dating.py): whether they are free, drawn to the user and near their age, and then a chance from
how picky they are that grows with every day the user has met them. No model decides it. The narrator is told the
answer after the user's line and only plays it out; a line in the story then says it plainly.

Someone who says yes is a match, kept where the dating app keeps its own (`dating_swipes`, `source` 'story'), so
they can become a companion the same way (companion/cast.py), in the town they were met in.
"""
import re

from companion import story_people
from companion.database import optional, settings
from companion.life import ages
from companion.world import dating, generators, townsfolk, turnover

SOURCE = 'story'
# What each day the user has met them, after the first, adds to the chance they say yes.
WARMTH = 0.2
ADULT = 18
# The user's line asks someone out: plain phrases only, read as said. Anything else is just talk.
ASK = re.compile(
    r"\b(?:ask(?:s|ed|ing)?\s+(?:\w+\s+){0,2}out\b(?!\s+(?:of|back|front|there|here|loud|the)\b)|"
    r"(?:go|going)\s+out\s+with\s+me\b|go\s+on\s+a\s+date\b|\bon\s+a\s+date\s+with\s+me\b|"
    r"(?:take|taking)\s+you\s+(?:out|to\s+dinner|dancing)\b|have\s+(?:dinner|a\s+drink|coffee|lunch|supper)\s+with\s+me\b|"
    r"(?:get|grab|have)\s+(?:dinner|a\s+drink|drinks|coffee|lunch)\s+(?:together|sometime)\b|"
    r"(?:buy|get)\s+you\s+(?:a\s+drink|dinner)\s+sometime\b|"
    r"(?:have|get|ask(?:s|ed|ing)?\s+for)\s+(?:your|his|her|their)\s+(?:number|phone\s+number)\b|"
    r"(?:(?:can|could|may)\s+i|(?:like|love)\s+to)\s+see\s+you\s+again\b|"
    r"(?:may|might|can|could)\s+i\s+(?:call\s+on\s+you|court\s+you|come\s+calling)\b|"
    r"ask(?:s|ed|ing)?\s+(?:\w+\s+){0,3}(?:to\s+court|whether\s+i\s+may\s+come\s+calling|if\s+i\s+may\s+call)\b|"
    r"(?:will|would)\s+you\s+(?:go\s+out\s+with\s+me|be\s+my\s+(?:date|girlfriend|boyfriend|sweetheart|partner))\b)",
    re.IGNORECASE)
PERSONA_GENDERS = {'woman': 'woman', 'female': 'woman', 'she/her': 'woman', 'man': 'man', 'male': 'man',
                   'he/him': 'man', 'nonbinary': 'nonbinary', 'non-binary': 'nonbinary', 'they/them': 'nonbinary'}
# What the narrator is told after the user's line, by how the person's rules answered ({name}, {first}).
NOTES = {
    'yes': '[{name} says yes. {first} is glad to be asked and agrees to see the user again, in {first}\'s own '
           'manner. Do not have {first} hesitate, put it off or refuse.]',
    'already': '[{name} has already said yes to the user and is glad to hear it again.]',
    'not_yet': '[{name} does not say yes. {first} likes the user well enough but does not know them well enough '
               'yet, and turns it down kindly, leaving the door open. {first} agrees to nothing and gives no way '
               'to reach them.]',
    'taken': '[{name} does not say yes: {first} is {status} and says so kindly. {first} agrees to nothing and gives '
             'no way to reach them.]',
    'not_drawn': '[{name} does not say yes: {first} is not drawn to the user that way, and turns it down kindly '
                 'without being pressed for a reason. {first} agrees to nothing and gives no way to reach them.]',
    'age': '[{name} does not say yes: the gap in their ages is too wide for {first}, who turns it down kindly. '
           '{first} agrees to nothing and gives no way to reach them.]',
    'never': '[Nothing romantic happens with {name}: {first} does not take it that way, and the scene moves on.]',
}
# The line the story keeps afterward, for the user.
LINES = {
    'yes': '{first} said yes.',
    'already': '',
    'not_yet': "{first} didn't say yes this time.",
    'taken': '{first} said no.',
    'not_drawn': '{first} said no.',
    'age': '{first} said no.',
    'never': '',
}
STATUS_TEXT = {'seeing someone': 'seeing someone', 'married': 'married'}


def suitor(connection) -> dict:
    """The user as the person asked sees them: their dating profile when they have one, else who they are in this
    world (the Persona page). What is not known is None and is not held against them."""
    row = optional(connection, 'SELECT * FROM dating_profile WHERE id=1')
    if row:
        return {'gender': row['gender'], 'age': row['age'], 'seed': row['seed'],
                'looking_for': row['looking_for'] if row['looking_for'] != 'friends' else None}
    persona = optional(connection, 'SELECT name, gender, age, about, kind, lifespan FROM persona WHERE id=1') or {}
    age = ages.persona_life_age(connection, persona) if persona.get('age') else None
    return {'gender': PERSONA_GENDERS.get((persona.get('gender') or '').strip().lower()), 'age': age, 'seed': '',
            'looking_for': None}


def asked(text: str, people: list[dict]) -> dict | None:
    """The person in the scene the user's line asks out: the one it names, or the only one there."""
    if not ASK.search(text):
        return None
    named = [person for person in people if story_people.named(person['sheet'], text)]
    if len(named) == 1:
        return named[0]
    return people[0] if len(people) == 1 and not named else None


def chance(sheet: dict, found: dict, user: dict, meetings: int) -> float:
    """The dating app's chance (dating.likes) for what is known of the user, warmer for every day they have met."""
    profile = {'looking_for': user['looking_for'] or found['looking'],
               'age': user['age'] if user['age'] is not None else found['life']}
    return dating.likes(sheet, found, profile) + WARMTH * max(meetings - 1, 0)


def refusal(sheet: dict, found: dict, user: dict) -> str | None:
    """Why their rules rule the user out whatever the charm, or None."""
    if sheet['age'] < ADULT or found['life'] < ADULT or sheet.get('love_life') is False or \
            (user['age'] is not None and user['age'] < ADULT):
        return 'never'
    if found['status'] in STATUS_TEXT:
        return 'taken'
    if user['gender'] and user['gender'] not in found['drawn_to']:
        return 'not_drawn'
    low, high = found['age_range']
    return 'age' if user['age'] is not None and not low <= user['age'] <= high else None


def answer(connection, sheet: dict, data: dict, meetings: int) -> dict:
    """How this person answers being asked out: {'verdict', 'status'}."""
    if matched(connection, sheet['key']):
        return {'verdict': 'already', 'status': ''}
    user = suitor(connection)
    found = dating.details(sheet, data, turnover.today(data))
    why = refusal(sheet, found, user)
    if why:
        return {'verdict': why, 'status': STATUS_TEXT.get(found['status'], '')}
    sure = bool(settings(connection).get('debug_all_matches'))
    keen = generators.unit(townsfolk.drawn(sheet), 'likes-you', user['seed']) < chance(sheet, found, user, meetings)
    return {'verdict': 'yes' if sure or keen else 'not_yet', 'status': ''}


def matched(connection, key: str) -> bool:
    return optional(connection, 'SELECT 1 FROM dating_swipes WHERE person_key=? AND matched=1', (key,)) is not None


def ask(connection, view: dict, text: str) -> dict | None:
    """The ask in the user's line, answered: {'sheet', 'verdict', 'note', 'line', 'town'}, or None when the line
    asks nobody out."""
    person = asked(text, view['people'])
    if person is None:
        return None
    sheet = person['sheet']
    known = view['known'].get(sheet['key'])
    found = answer(connection, sheet, view['data'], known['meetings'] if known else 0)
    words = {'name': sheet['full'], 'first': sheet['name'], 'status': found['status']}
    return {'sheet': sheet, 'verdict': found['verdict'], 'town': view['data'].get('town', ''),
            'note': NOTES[found['verdict']].format(**words), 'line': LINES[found['verdict']].format(**words)}


def after(chat: list[dict], found: dict | None) -> list[dict]:
    """The narrator's conversation with the answer after the user's latest line."""
    if not found or not chat or chat[-1]['role'] != 'user':
        return chat
    return [*chat[:-1], {'role': 'user', 'content': f"{chat[-1]['content']}\n\n{found['note']}"}]


def settle(connection, add, found: dict | None, user: dict, city_id: str, now: str, day) -> None:
    """After the narrator has told it: a yes is a match from then on, and the story says how it went in a line of
    its own. `add` is the Story's own (companion/story.py)."""
    if not found:
        return
    sheet = found['sheet']
    if found['verdict'] == 'yes':
        connection.execute(
            'INSERT INTO dating_swipes (person_key, city_id, town, liked, matched, created_at, source) '
            'VALUES (?, ?, ?, 1, 1, ?, ?) ON CONFLICT(person_key) DO UPDATE SET liked=1, matched=1, '
            'town=excluded.town, created_at=excluded.created_at, source=excluded.source',
            (sheet['key'], city_id, found['town'], now, SOURCE))
        story_people.meet(connection, sheet, city_id, now, day)  # They are someone the user has met.
    if found['line']:
        add(connection, now, 'cast', found['line'], user, reply_to=user['id'])


def noted(connection, people: list[dict]) -> list[dict]:
    """The scene's people, with a line for the narrator on anyone who has said yes to the user."""
    keys = {row['person_key'] for row in connection.execute('SELECT person_key FROM dating_swipes WHERE matched=1')}
    return [{**person, 'note': person.get('note', '') + ' Has said yes to seeing the user and is glad when they come by.'}
            if person['sheet']['key'] in keys and not person.get('shown') else person for person in people]


def ask_line(data: dict, sheet: dict) -> dict:
    """The button that asks for the user, and the line it says, in the city's era."""
    name = sheet['name']
    if townsfolk.modern(data):
        return {'label': f'Ask {name} out', 'line': f'I ask {name} to go out with me sometime.'}
    return {'label': f'Ask to call on {name}', 'line': f'I ask {name} whether I may come calling.'}


def for_person(connection, data: dict, sheet: dict, here: bool) -> dict:
    """What the people list says about pursuing them: whether they said yes, became a companion, and the ask the
    user can make while they are in the scene."""
    companion = optional(connection, 'SELECT id FROM companions WHERE townsfolk_key=?', (sheet['key'],))
    said_yes = matched(connection, sheet['key'])
    can_ask = here and not said_yes and not companion and sheet['age'] >= ADULT
    return {'matched': said_yes, 'companion_id': companion and companion['id'],
            'ask': ask_line(data, sheet) if can_ask else None}
