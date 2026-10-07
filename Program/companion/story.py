"""Story mode: free-form roleplay with a narrator around the cities, apart from every companion (docs/story.md).

The story has its own scene (`story_scene`: the city and place the user is at) and its own history
(`story_messages`). No companion prompt reads either, so nothing said here reaches the companion.

The app decides the scene from the city data and the townsfolk rules: the place, the local time and
weather, and who is there at that hour, the same people the companion's world has. The narrator model
only voices it. Moving somewhere else is the user's choice in the place picker, not the model's.
"""
from datetime import datetime

from companion import in_character, prompt_library
from companion.characters import current
from companion.clock import zone
from companion.database import identifier, many, one, optional
from companion.errors import DomainError, require
from companion.life import agenda, encounters, network
from companion.providers.chat import INCOMPLETE
from companion.providers.scheduling import CONVERSATION
from companion.text_models import config_for, default_name, key_for
from companion.world import catalog, changes, custom, generators, newcomers, townsfolk

JOB = 'story'
DEFAULT_CITY = 'baltimore'
HISTORY_LIMIT = 200
CHARS_PER_TOKEN = 4
# The kinds a story starts at when nothing else is chosen: somewhere people sit and talk.
OPENING_KINDS = ('cafe', 'tavern', 'bar', 'restaurant', 'market', 'park')

NARRATOR = """You are the narrator of an open-ended story. The user plays themself, arriving in a real place \
at a real hour; you describe the world around them and voice everyone they meet.

How to narrate:
- Write in the second person and present tense ("You push open the door..."), in two or three short paragraphs \
at most, then stop where the user can act.
- Never decide what the user says, does, thinks or feels. Describe, voice the people, and leave the next move \
to them.
- The scene below is fact: the place, the hour, the weather and who is there. Only the people listed are \
present, apart from unnamed passers-by. Each keeps their own job, mood and manner, and is busy if their \
listing says so.
- A person's name is unknown to the user until that person gives it. Do not narrate it before then.
- Everyone has a life of their own. People can be friendly, shy, busy or uninterested, and they answer the user \
as they would a stranger until they know them. Romance happens only if the user pursues it and the other \
person would plausibly welcome it.
- Keep to the place's era and the city's character; people talk as people there and then would.
- When the user wants to go somewhere else, narrate them setting off. Where they arrive is set by the app \
when they choose the place.
- You are a storyteller, not a character: never say you are an AI or a language model, and never add notes \
about the story. A message starting with OOC: or wrapped in ((double parentheses)) is the user stepping out \
of the story; answer it plainly and honestly instead."""


def no_model() -> DomainError:
    return DomainError('Add a text model in Settings > Models to tell the story.', 409, 'no_connection')


# The scene ----------------------------------------------------------------------------------------

def city_data(connection, city_id: str) -> dict:
    """The city as the companion's world has it: with the companion's own town and family names when the
    companion lives there, so the story meets the same people the companion does."""
    companion = current(connection)
    if companion and newcomers.city_for(connection, companion['version']['definition'])['id'] == city_id:
        return network.city(connection, companion)
    data = changes.resolve(city_id, custom.all_cities(connection))
    if data is None:
        raise DomainError(f'No world data for city {city_id!r}.', 404, 'unknown_city')
    return data | {'kin': [], 'town': companion.get('town_seed') or '' if companion else ''}


def opening_place(data: dict) -> dict:
    for kind in OPENING_KINDS:
        if found := catalog.places(data, kind=kind):
            return found[0]
    return data['places'][0]


def default_city(connection) -> str:
    """The companion's city, else Baltimore, the first shipped city."""
    companion = current(connection)
    return (newcomers.city_for(connection, companion['version']['definition'])['id'] if companion else '') or DEFAULT_CITY


def scene_row(connection) -> dict:
    """Where the story is; a new story starts in the companion's city (or the default one) at a cafe. A place
    or city that has since gone falls back the same way."""
    row = optional(connection, 'SELECT city_id, place_id FROM story_scene WHERE id=1')
    known = row and changes.resolve(row['city_id'], custom.all_cities(connection))
    data = city_data(connection, row['city_id'] if known else default_city(connection))
    if known and catalog.find(data, row['place_id']) in data['places']:
        return {'city_id': row['city_id'], 'place_id': row['place_id']}
    return {'city_id': data['id'], 'place_id': opening_place(data)['id']}


def local_moment(data: dict, now: datetime) -> datetime:
    return now.astimezone(zone(data['timezone'])).replace(tzinfo=None)


def present(connection, data: dict, place_id: str, moment: datetime) -> list[dict]:
    """Who the townsfolk rules put at the place now, never a companion: the story is apart from them."""
    companion = current(connection)
    cast = encounters.town_cast(connection, companion, data) if companion else encounters.NO_CAST
    found = encounters.present(data, place_id, [moment], {}, cast)
    people = []
    for key in found[1] if found else ():
        sheet = encounters.resolve(data, key, cast)
        if sheet and not key.startswith('cast:') and key not in cast['aliases']:
            people.append({'sheet': sheet, **townsfolk.whereabouts(sheet, data, moment)})
    return people


def scene(connection, now: datetime) -> dict:
    row = scene_row(connection)
    data = city_data(connection, row['city_id'])
    place = catalog.find(data, row['place_id'])
    moment = local_moment(data, now)
    weather = generators.conditions(data, moment.date())
    hood = townsfolk.neighborhood_name(data, place['neighborhood'])
    return {'city': {'id': data['id'], 'name': data['name'], 'era': data.get('era', 'modern')},
            'place': {'id': place['id'], 'name': place['name'], 'kind': place['kind'], 'summary': place.get('summary', ''),
                      'neighborhood': hood},
            'local_time': moment.isoformat(timespec='minutes'), 'weather': agenda.weather_text(weather) if weather else '',
            'people': present(connection, data, place['id'], moment), 'data': data}


def person_line(person: dict, place: dict, data: dict) -> str:
    sheet = person['sheet']
    seen = encounters.who(sheet, place, data, None, person['doing'])
    pronouns = f", {sheet['pronouns']}" if sheet.get('pronouns') else ''
    return (f"- {seen[0].upper()}{seen[1:]}: {sheet['full']}{pronouns}, {sheet['age']}, {person['doing']}, "
            f"{sheet.get('occupation') or sheet['role']}. {townsfolk.first_impression(sheet).capitalize()}; "
            f"{sheet['quirk']}. Mood: {person['mood']}.")


def scene_text(view: dict) -> str:
    data, place = view['data'], view['place']
    moment = datetime.fromisoformat(view['local_time'])
    when = f"{moment:%A} {moment.day} {moment:%B}" + (f", {moment.year}" if data.get('era', 'modern') == 'modern' else '')
    lines = [f"Place: {place['name']}, a {place['kind']} in {place['neighborhood']}, {data['name']}. {place['summary']}",
             f"City: {data['summary']}" + ('' if townsfolk.modern(data) else f" The era is {data['era']}."),
             f"Local time: {when}, {moment.strftime('%H:%M')} ({townsfolk.part_of_day(moment.hour * 60 + moment.minute)})."]
    if view['weather']:
        lines.append(f"Weather: {view['weather']}")
    lines.append('Who is here (their names are for you; the user learns one only when it is given):')
    lines += [person_line(person, {'id': place['id']}, data) for person in view['people']] or \
        ['- Nobody the story knows; only passers-by.']
    return '## Scene\n' + '\n'.join(lines)


def scene_view(view: dict) -> dict:
    """The scene for the screen: what the user can see, never the names of people they have not met."""
    data = view['data']
    return {key: view[key] for key in ('city', 'place', 'local_time', 'weather')} | {
        'places': [{'id': item['id'], 'name': item['name'], 'kind': item['kind'],
                    'neighborhood': townsfolk.neighborhood_name(data, item['neighborhood'])} for item in data['places']],
        'around': [encounters.who(person['sheet'], {'id': view['place']['id']}, data, None, person['doing'])
                   .removesuffix(' there') for person in view['people']]}


# History ------------------------------------------------------------------------------------------

def next_seq(connection) -> int:
    return one(connection, 'SELECT COALESCE(MAX(seq), 0) + 1 AS seq FROM story_messages')['seq']


def add(connection, now: str, role: str, text: str, where: dict, **extra) -> dict:
    message_id = identifier()
    connection.execute(
        'INSERT INTO story_messages (id, seq, role, text, client_id, reply_to, status, error, city_id, place_id, '
        'created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (message_id, next_seq(connection), role, text, extra.get('client_id'), extra.get('reply_to'),
         extra.get('status', 'complete'), extra.get('error'), where['city_id'], where['place_id'], now))
    return one(connection, 'SELECT * FROM story_messages WHERE id=?', (message_id,))


def messages(connection, limit: int = HISTORY_LIMIT) -> list[dict]:
    rows = many(connection, 'SELECT id, seq, role, text, reply_to, status, error, city_id, place_id, created_at '
                'FROM story_messages ORDER BY seq DESC LIMIT ?', (limit,))
    return list(reversed(rows))


def story(database) -> dict:
    with database.connect() as connection:
        view = scene(connection, database.clock.now())
        return {'scene': scene_view(view), 'messages': messages(connection),
                'ready': config_for(connection, JOB) is not None}


def move(database, city_id: str, place_id: str | None) -> dict:
    """Go somewhere else: another place in this city, or another city (its opening place unless one is named)."""
    with database.connect(write=True) as connection:
        data = city_data(connection, city_id)
        place = catalog.find(data, place_id) if place_id else opening_place(data)
        require(place is not None and place in data['places'], 'No such place in this city.', 404)
        if scene_row(connection) != {'city_id': data['id'], 'place_id': place['id']}:
            connection.execute(
                'INSERT INTO story_scene (id, city_id, place_id, updated_at) VALUES (1, ?, ?, ?) ON CONFLICT(id) DO '
                'UPDATE SET city_id=excluded.city_id, place_id=excluded.place_id, updated_at=excluded.updated_at',
                (data['id'], place['id'], database.now()))
            where = {'city_id': data['id'], 'place_id': place['id']}
            hood = townsfolk.neighborhood_name(data, place['neighborhood'])
            add(connection, database.now(), 'scene', f"You arrive at {place['name']}, {hood}, {data['name']}.", where)
    return story(database)


def clear(database) -> dict:
    """A new story: the history goes, the scene stays where it is."""
    with database.connect(write=True) as connection:
        connection.execute('DELETE FROM story_messages')
    return story(database)


# The narrator -------------------------------------------------------------------------------------

def model_messages(rows: list[dict], budget_chars: int) -> list[dict]:
    """The story so far as chat turns, newest kept when it does not all fit. A move is a note on the user's side."""
    chat, used = [], 0
    for row in reversed(rows):
        if row['role'] == 'narrator' and row['status'] != 'complete':
            continue
        text = f"[{row['text']}]" if row['role'] == 'scene' else row['text']
        used += len(text)
        if used > budget_chars and chat:
            break
        role = 'assistant' if row['role'] == 'narrator' else 'user'
        if chat and chat[0]['role'] == role:
            chat[0] = {'role': role, 'content': text + '\n\n' + chat[0]['content']}
        else:
            chat.insert(0, {'role': role, 'content': text})
    return chat


def prompt(connection, now: datetime, config: dict, latest: dict) -> dict:
    view = scene(connection, now)
    system = prompt_library.text(connection, 'story-narrator') + '\n\n' + scene_text(view)
    if in_character.out_of_character(latest['text']):
        system += '\n\n' + in_character.OUT_OF_CHARACTER_NOTE.format(name='the narrator', model=default_name(config))
    budget = (config['context_tokens'] - config['max_output_tokens']) * CHARS_PER_TOKEN - len(system)
    rows = [row for row in messages(connection) if row['seq'] <= latest['seq']]
    return {'system': system, 'messages': model_messages(rows, max(budget, 2000))}


async def narrate(state, packet: dict, config: dict, active: bool) -> tuple[str, str | None]:
    conversation = state.conversation
    guard, text, error = in_character.Guard(active), [], None
    async with conversation.scheduler.reserve(config, CONVERSATION):
        async for chunk in conversation.provider.stream(config, key_for(state.vault, config), packet['system'],
                                                        packet['messages']):
            text.append(guard.feed(chunk.text))
            if chunk.finish_reason == 'content_filter':
                error = INCOMPLETE[chunk.finish_reason]
    text.append(guard.flush())
    return ''.join(text).strip(), error


async def answer(state, user: dict) -> dict:
    """The narrator's reply to the user's message, saved complete or failed with the reason."""
    database = state.database
    with database.connect() as connection:
        config = config_for(connection, JOB)
        if config is None:
            raise no_model()
        packet = prompt(connection, database.clock.now(), config, user)
    try:
        text, error = await narrate(state, packet, config, not in_character.out_of_character(user['text']))
    except DomainError as failure:
        text, error = '', failure.message
    status = 'complete' if text and not error else 'failed'
    error = None if status == 'complete' else error or 'The model returned no story text.'
    with database.connect(write=True) as connection:
        connection.execute("DELETE FROM story_messages WHERE reply_to=? AND status='failed'", (user['id'],))
        return add(connection, database.now(), 'narrator', text, user, reply_to=user['id'], status=status, error=error)


def record(database, text: str, client_id: str) -> tuple[dict, dict | None]:
    """The user's message, saved once whatever retries come; with the narrator's reply if it already has one."""
    with database.connect(write=True) as connection:
        user = optional(connection, 'SELECT * FROM story_messages WHERE client_id=?', (client_id,))
        if user is None:
            user = add(connection, database.now(), 'user', text, scene_row(connection), client_id=client_id)
        reply = optional(connection, "SELECT * FROM story_messages WHERE reply_to=? AND status='complete'",
                         (user['id'],))
        return user, reply


async def send(state, text: str, client_id: str) -> dict:
    user, reply = record(state.database, text, client_id)
    return {'message': user, 'reply': reply or await answer(state, user)}


async def retry(state) -> dict:
    """Tell the last part again: a new reply to the user's latest message, replacing the one there."""
    with state.database.connect(write=True) as connection:
        user = optional(connection, "SELECT * FROM story_messages WHERE role='user' ORDER BY seq DESC LIMIT 1")
        require(user is not None, 'There is nothing to retell yet.', 409)
        connection.execute('DELETE FROM story_messages WHERE reply_to=?', (user['id'],))
    return {'message': user, 'reply': await answer(state, user)}
