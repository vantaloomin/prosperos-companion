"""Story mode: free-form roleplay with a narrator around the cities, apart from every companion (docs/story.md).

The story has its own scene (`story_scene`: the city and place the user is at) and its own history
(`story_messages`). No companion prompt reads either, so nothing said here reaches the companion.

The app decides the scene from the city data and the townsfolk rules: the place, the local time and
weather, and who is there at that hour, the same people the companion's world has. The narrator model
only voices it. Moving somewhere else is the user's choice in the place picker, not the model's.
"""
from datetime import datetime

from companion import in_character, prompt_library, safety, story_people
from companion.characters import current
from companion.clock import zone
from companion.database import identifier, many, one, optional
from companion.errors import DomainError, require
from companion.life import agenda, encounters, network
from companion.providers.chat import INCOMPLETE
from companion.providers.scheduling import CONVERSATION
from companion.text_models import config_for, default_name, key_for
from companion.world import catalog, changes, custom, generators, inside, life_details, newcomers, townsfolk

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
- Never encourage, praise or help with self-harm or suicide, and never describe ways to do it. If the user says \
they want to hurt themselves, take it seriously: let the people in the scene answer with real care.
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
    town = companion.get('town_seed') or '' if companion else ''
    return data | {'kin': [], 'town': town, 'you': network.you(connection, town)}


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
    from companion import dating  # The user's date, while one is going on here (docs/dating.md).
    return dating.with_date(connection, data, place_id, moment, people)


def scene(connection, now: datetime) -> dict:
    row = scene_row(connection)
    data = city_data(connection, row['city_id'])
    place = catalog.find(data, row['place_id'])
    moment = local_moment(data, now)
    weather = generators.conditions(data, moment.date())
    hood = townsfolk.neighborhood_name(data, place['neighborhood'])
    return {'city': {'id': data['id'], 'name': data['name'], 'era': data.get('era', 'modern')},
            'place': {'id': place['id'], 'name': place['name'], 'kind': place['kind'], 'summary': place.get('summary', ''),
                      'neighborhood': hood, 'spots': inside.names(inside.for_place(place, data.get('era')))},
            'local_time': moment.isoformat(timespec='minutes'), 'weather': agenda.weather_text(weather) if weather else '',
            'people': present(connection, data, place['id'], moment), 'data': data, 'now': now,
            'known': story_people.known(connection)}


def person_line(person: dict, place: dict, data: dict, known: dict | None = None) -> str:
    sheet = person['sheet']
    seen = encounters.who(sheet, place, data, None, person['doing'])
    pronouns = f", {sheet['pronouns']}" if sheet.get('pronouns') else ''
    return (f"- {seen[0].upper()}{seen[1:]}: {sheet['full']}{pronouns}, {sheet['age']}, {person['doing']}, "
            f"{sheet.get('occupation') or sheet['role']}. {townsfolk.first_impression(sheet).capitalize()}; "
            f"{sheet['quirk']}.{life_text(data, sheet)} Mood: {person['mood']}.{story_people.remembered(known)}"
            f"{person.get('note', '')}")


def life_text(data: dict, sheet: dict) -> str:
    """Where they come from, a taste and a story they might tell, for the model to use or leave."""
    found = life_details.for_sheet(data, sheet)
    if not found:
        return ''
    story = f" Might tell the story of the time they {found['stories'][0]}." if found['stories'] else ''
    return f" {found['origin'][:1].upper()}{found['origin'][1:]}; {found['likes'][0]}.{story}"


def scene_text(view: dict) -> str:
    data, place = view['data'], view['place']
    moment = datetime.fromisoformat(view['local_time'])
    when = f"{moment:%A} {moment.day} {moment:%B}" + (f", {moment.year}" if data.get('era', 'modern') == 'modern' else '')
    lines = [f"Place: {place['name']}, a {place['kind']} in {place['neighborhood']}, {data['name']}. {place['summary']}",
             f"City: {data['summary']}" + ('' if townsfolk.modern(data) else f" The era is {data['era']}."),
             f"Local time: {when}, {moment.strftime('%H:%M')} ({townsfolk.part_of_day(moment.hour * 60 + moment.minute)})."]
    if place.get('spots'):
        lines.append(f"Spots here, for detail only (nobody moves between them): {', '.join(place['spots'])}.")
    if view['weather']:
        lines.append(f"Weather: {view['weather']}")
    lines.append('Who is here (their names are for you; the user knows only the names of people they have met):')
    lines += [person_line(person, {'id': place['id']}, data, view['known'].get(person['sheet']['key']))
              for person in view['people']] or \
        ['- Nobody the story knows; only passers-by.']
    return '## Scene\n' + '\n'.join(lines)


def scene_view(view: dict) -> dict:
    """The scene for the screen: what the user can see, never the names of people they have not met."""
    data = view['data']
    return {key: view[key] for key in ('city', 'place', 'local_time', 'weather')} | {
        'places': [{'id': item['id'], 'name': item['name'], 'kind': item['kind'],
                    'neighborhood': townsfolk.neighborhood_name(data, item['neighborhood'])} for item in data['places']],
        'around': [seen(person, view) for person in view['people']]}


def seen(person: dict, view: dict) -> str:
    """'the barista', or 'Dana, the barista' once the user has met her."""
    if person.get('shown'):  # The user's date (companion/dating.py).
        return person['shown']
    sheet = person['sheet']
    who = encounters.who(sheet, {'id': view['place']['id']}, view['data'], None, person['doing']).removesuffix(' there')
    return f"{sheet['name']}, {who}" if sheet['key'] in view['known'] else who


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
    # The app's crisis note under a user's line that sounds like self-harm (companion/safety.py).
    return [{**row, 'crisis_help': row['role'] == 'user' and safety.crisis(row['text'])} for row in reversed(rows)]


def story(database) -> dict:
    with database.connect() as connection:
        view = scene(connection, database.clock.now())
        return {'scene': scene_view(view), 'messages': messages(connection), 'people': people(connection, view),
                'ready': config_for(connection, JOB) is not None, 'can_switch': current(connection) is not None}


def people(connection, view: dict) -> list[dict]:
    """Everyone the user has met in the story, most recent first, with where their rules put them now."""
    result, cities = [], {}
    for row in view['known'].values():
        if row['city_id'] not in cities:
            try:
                cities[row['city_id']] = city_data(connection, row['city_id'])
            except DomainError:
                cities[row['city_id']] = None
        data = cities[row['city_id']]
        sheet = townsfolk.find(data, row['key']) if data else None
        if sheet is None:
            continue  # Their city is gone, or its townsfolk were seeded anew.
        now = townsfolk.whereabouts(sheet, data, local_moment(data, view['now']))
        result.append({'key': row['key'], 'name': row['name'], 'role': sheet.get('occupation') or sheet['role'],
                       'city': data['name'], 'meetings': row['meetings'], 'last_met_at': row['last_met_at'],
                       'notes': row['notes'], 'doing': now['doing'],
                       'place': now['place'] and {'id': now['place']['id'], 'name': now['place']['name'],
                                                  'city_id': data['id']}})
    return result


def find(database, key: str) -> dict:
    """Go to where someone the user has met is right now."""
    with database.connect() as connection:
        view = scene(connection, database.clock.now())
        person = next((item for item in people(connection, view) if item['key'] == key), None)
    require(person is not None, "You haven't met them in your story.", 404)
    place = person['place']
    require(place is not None and not place['id'].startswith('~'),
            f"{person['name'].split()[0]} isn't anywhere you can go right now ({person['doing']}).", 409)
    return move(database, place['city_id'], place['id'])


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
    """A new story: the history and the people met go, the scene stays where it is."""
    with database.connect(write=True) as connection:
        connection.execute('DELETE FROM story_messages')
        connection.execute('DELETE FROM story_people')
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
    return {'system': system, 'messages': model_messages(rows, max(budget, 2000)), 'people': view['people'],
            'city_id': view['city']['id'], 'day': datetime.fromisoformat(view['local_time']).date()}


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
        if status == 'complete' and not in_character.out_of_character(user['text']):
            story_people.note_exchange(connection, packet['people'], packet['city_id'], user['text'], text,
                                       database.now(), packet['day'])
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
