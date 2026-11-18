"""The Story: free-form roleplay with a narrator around the cities (docs/story.md).

The story has its own scene (`story_scene`: the city and place the user is at) and its own history
(`story_messages`). Time spent with a companion here counts in their
life together (companion/story_visits.py): their chat is told of it and it leaves a shared moment.

The app decides the scene from the city data and the townsfolk rules: the place, the local time and
weather, and who is there at that hour, the same people the companion's world has. The narrator model
only voices it. Moving somewhere else is the user's choice in the place picker, not the model's.

When the story is where a companion is at that hour, they are in the scene and speak for themselves: the
narrator's reply comes first, then each companion's own line, written by their own character
(companion/story_cast.py).
"""
from datetime import datetime

from companion import (
    authors_note,
    in_character,
    prompt_library,
    safety,
    story_cast,
    story_people,
    story_plans,
    story_visits,
)
from companion.characters import current
from companion.clock import zone
from companion.database import identifier, many, one, optional
from companion.errors import DomainError, require
from companion.life import agenda, ages, encounters, network, scene_now
from companion.memory.context import NOTE_CLOSE
from companion.providers.chat import INCOMPLETE
from companion.providers.scheduling import CONVERSATION
from companion.text_models import CHAT, config_for, default_name, key_for, reply_config
from companion.world import (
    added_places,
    catalog,
    changes,
    custom,
    generators,
    inside,
    life_details,
    newcomers,
    skies,
    temperature,
    townsfolk,
)

JOB = 'story'
DEFAULT_CITY = 'baltimore'
HISTORY_LIMIT = 200
MOVES_READ = 60  # The latest story lines read for a move (companion/life/scene_now.py).
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
    data = added_places.merge(connection, changes.resolve(city_id, custom.all_cities(connection)))
    if data is None:
        raise DomainError(f'No world data for city {city_id!r}.', 404, 'unknown_city')
    town = companion.get('town_seed') or '' if companion else ''
    return data | {'kin': [], 'town': town, 'you': network.you(connection, town), 'kept': network.kept(connection, town)}


def opening_place(data: dict) -> dict:
    for kind in OPENING_KINDS:
        if found := catalog.places(data, kind=kind):
            return found[0]
    return data['places'][0]


def default_city(connection) -> str:
    """The companion's city, else the city the user lives in in this world (a new world starts with no companion, so
    a character brought in lives where the world is), else Baltimore, the first shipped city."""
    companion = current(connection)
    if companion:
        return newcomers.city_for(connection, companion['version']['definition'])['id'] or DEFAULT_CITY
    row = optional(connection, 'SELECT home_city_id FROM persona WHERE id=1')
    home = row and row['home_city_id'] and changes.resolve(row['home_city_id'], custom.all_cities(connection))
    return home['id'] if home else DEFAULT_CITY


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
    """Who the townsfolk rules put at the place now. Companions are not among them: they are in the scene in
    their own right (companion/story_cast.py)."""
    companion = current(connection)
    cast = encounters.town_cast(connection, companion, data) if companion else encounters.NO_CAST
    found = encounters.present(data, place_id, [moment], {}, cast)
    people = []
    for key in found[1] if found else ():
        sheet = encounters.resolve(data, key, cast)
        if sheet and not key.startswith('cast:') and key not in cast['aliases']:
            # How old they are now (companion/life/ages.py), as Around town says.
            people.append({'sheet': {**sheet, 'age': ages.town_age(connection, sheet, moment.date())},
                           **townsfolk.whereabouts(sheet, data, moment)})
    from companion import dating  # The user's date, while one is going on here (docs/dating.md).
    return dating.with_date(connection, data, place_id, moment, people)


def scene(connection, now: datetime) -> dict:
    row = scene_row(connection)
    data = city_data(connection, row['city_id'])
    place = catalog.find(data, row['place_id'])
    # Where the story's own lines have walked them since the place was picked (companion/life/scene_now.py).
    place = scene_now.story_place(data, place, messages(connection, MOVES_READ))
    place = inside.with_edits(place, inside.edited(connection, data['id']))
    moment = local_moment(data, now)
    weather = generators.conditions(data, moment.date(), skies.level_of(connection))
    hood = townsfolk.neighborhood_name(data, place['neighborhood'])
    return {'city': {'id': data['id'], 'name': data['name'], 'era': data.get('era', 'modern')},
            'place': {'id': place['id'], 'name': place['name'], 'kind': place['kind'], 'summary': place.get('summary', ''),
                      'neighborhood': hood, 'spots': inside.names(inside.for_place(place, data.get('era')))},
            'local_time': moment.isoformat(timespec='minutes'), 'weather': agenda.weather_text(weather, temperature.chosen(connection)) if weather else '',
            'people': present(connection, data, place['id'], moment), 'data': data, 'now': now,
            'known': story_people.known(connection),
            # Companions who are here at this hour, in their own right (companion/story_cast.py).
            'companions': (found := story_cast.here(connection, data, place['id'], now)),
            # The people a plan under way here is with, for the narrator to voice (companion/story_plans.py).
            'along': story_plans.narrator_people(connection, found)}


def person_line(person: dict, place: dict, data: dict, known: dict | None = None) -> str:
    sheet = person['sheet']
    seen = encounters.who(sheet, place, data, None, person['doing'])
    pronouns = f", {sheet['pronouns']}" if sheet.get('pronouns') else ''
    job = sheet.get('occupation') or sheet['role']
    # "working as the owner" already says the job: no "working as the owner, owner."
    job = '' if f' {job}' in f" {person['doing']}" else f', {job}'
    folk = townsfolk.folk_label(data, sheet)
    folk = f', {folk}' if folk else ''
    return (f"- {seen[0].upper()}{seen[1:]}: {sheet['full']}{pronouns}, {sheet['age']}{folk}, {person['doing']}{job}. "
            f"{townsfolk.first_impression(sheet).capitalize()}; "
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
    lines += story_cast.narrator_lines(view['companions']) + view['along'] + \
        [person_line(person, {'id': place['id']}, data, view['known'].get(person['sheet']['key']))
         for person in view['people']] or ['- Nobody the story knows; only passers-by.']
    if view['companions']:
        lines.append(story_cast.beside(view['companions']))
    lines += story_plans.narrator_plan(view['companions'])  # They came together, on purpose.
    return '## Scene\n' + '\n'.join(lines)


def scene_view(view: dict) -> dict:
    """The scene for the screen: what the user can see, never the names of people they have not met."""
    data = view['data']
    return {key: view[key] for key in ('city', 'place', 'local_time', 'weather')} | {
        'places': [{'id': item['id'], 'name': item['name'], 'kind': item['kind'],
                    'neighborhood': townsfolk.neighborhood_name(data, item['neighborhood'])} for item in data['places']],
        # A companion is someone the user knows: by name, and first.
        'around': [item['name'] for item in view['companions']] + story_plans.seen(view['companions'])
        + [seen(person, view) for person in view['people']],
        'companions': [{'id': item['id'], 'name': item['name']} for item in view['companions']],
        # The plan being played here (companion/story_plans.py), or None.
        'plan': next((story_plans.view(item) for item in view['companions'] if item.get('plan')), None)}


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
        'created_at, speaker, name, hidden) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (message_id, next_seq(connection), role, text, extra.get('client_id'), extra.get('reply_to'),
         extra.get('status', 'complete'), extra.get('error'), where['city_id'], where['place_id'], now,
         extra.get('speaker'), extra.get('name'), int(bool(extra.get('hidden')))))
    return one(connection, 'SELECT * FROM story_messages WHERE id=?', (message_id,))


def messages(connection, limit: int = HISTORY_LIMIT) -> list[dict]:
    rows = many(connection, 'SELECT id, seq, role, text, client_id, reply_to, status, error, city_id, place_id, '
                'created_at, speaker, name, hidden FROM story_messages ORDER BY seq DESC LIMIT ?', (limit,))
    # The app's crisis note under a user's line that sounds like self-harm (companion/safety.py).
    return [{**row, 'crisis_help': row['role'] == 'user' and safety.crisis(row['text'])} for row in reversed(rows)]


def story(database) -> dict:
    with database.connect() as connection:
        view = scene(connection, database.clock.now())
        return {'scene': scene_view(view), 'messages': messages(connection), 'people': people(connection, view),
                'companions': companions(connection, view),
                'ready': config_for(connection, JOB) is not None, 'can_switch': current(connection) is not None}


def companions(connection, view: dict) -> list[dict]:
    """Every companion with where their day has them now, the main character first: somewhere the story can go
    (`place`), or not (`place` None: at home, asleep, out of town)."""
    def data_for(city_id: str) -> dict | None:
        try:
            return city_data(connection, city_id)
        except DomainError:
            return None
    here = {item['id'] for item in view['companions']}
    return [{'key': f"companion:{item['id']}", 'id': item['id'], 'name': item['name'], 'main': item['main'],
             'here': item['id'] in here, 'doing': item['doing'], 'city': item['city'] and item['city']['name'],
             # Their plan with the user under way, when the story can go to it (companion/story_plans.py).
             'plan': story_plans.view(item) if item.get('plan') else None,
             'place': item['place'] and {'id': item['place']['id'], 'name': item['place']['name'],
                                         'city_id': item['city']['id']}}
            for item in story_cast.whereabouts(connection, data_for, view['now'])]


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
    """Go to where someone the user has met, or a companion, is right now."""
    with database.connect() as connection:
        view = scene(connection, database.clock.now())
        found = companions(connection, view) if key.startswith('companion:') else people(connection, view)
        person = next((item for item in found if item['key'] == key), None)
    require(person is not None, "You haven't met them in your story.", 404)
    place = person['place']
    doing = f" ({person['doing']})" if person.get('doing') else ''
    require(place is not None and not place['id'].startswith('~'),
            f"{person['name'].split()[0]} isn't anywhere you can go right now{doing}.", 409)
    return move(database, place['city_id'], place['id'])


def play(database, outing_id: str) -> dict:
    """Play a plan under way as a scene: the story goes to where the plan is (companion/story_plans.py). The
    companion and the people it is with are there because the plan is, not because the story came."""
    with database.connect() as connection:
        companion, plan = story_plans.find(connection, outing_id, database.clock.now())
        try:
            data = city_data(connection, newcomers.city_for(connection, companion['version']['definition'])['id'])
        except DomainError:
            data = None
        place = story_plans.place_of(plan, data)
    require(place is not None, "This plan isn't somewhere your story can go.", 409)
    return move(database, data['id'], place['id'])


def move(database, city_id: str, place_id: str | None) -> dict:
    """Go somewhere else: another place in this city, or another city (its opening place unless one is named)."""
    with database.connect(write=True) as connection:
        data = city_data(connection, city_id)
        place = catalog.find(data, place_id) if place_id else opening_place(data)
        require(place is not None and place in data['places'], 'No such place in this city.', 404)
        row = scene_row(connection)
        # Picking the place the story walked them away from takes them back there (companion/life/scene_now.py).
        walked = row['city_id'] == data['id'] and scene_now.story_place(
            data, catalog.find(data, row['place_id']), messages(connection, MOVES_READ))['id'] != place['id']
        if row != {'city_id': data['id'], 'place_id': place['id']} or walked:
            connection.execute(
                'INSERT INTO story_scene (id, city_id, place_id, updated_at) VALUES (1, ?, ?, ?) ON CONFLICT(id) DO '
                'UPDATE SET city_id=excluded.city_id, place_id=excluded.place_id, updated_at=excluded.updated_at',
                (data['id'], place['id'], database.now()))
            where = {'city_id': data['id'], 'place_id': place['id']}
            hood = townsfolk.neighborhood_name(data, place['neighborhood'])
            add(connection, database.now(), 'scene', f"You arrive at {place['name']}, {hood}, {data['name']}.", where)
            # Whoever was with them stays behind; a companion who is at the new place is there when they walk in.
            story_visits.close_all(connection, database.clock.now())  # Their time together ends here.
            story_cast.leave(connection)
            story_cast.sync(connection, add, scene(connection, database.clock.now())['companions'], database.now(), where)
    return story(database)


def clear(database) -> dict:
    """A new story: the history and the people met go, the scene stays where it is."""
    with database.connect(write=True) as connection:
        # Time spent with a companion still happened (companion/story_visits.py): it is settled before the lines go.
        story_visits.close_all(connection, database.clock.now())
        connection.execute('DELETE FROM story_messages')
        connection.execute('DELETE FROM story_people')
        story_cast.leave(connection)
    return story(database)


# The narrator -------------------------------------------------------------------------------------

def model_messages(rows: list[dict], budget_chars: int, pronouns: dict | None = None) -> list[dict]:
    """The story so far as chat turns, newest kept when it does not all fit. A move is a note on the user's side,
    and so is a companion coming or going; a companion's own line is on the user's side too, under their name."""
    chat, used = [], 0
    for row in reversed(rows):
        if row['role'] != 'user' and row['status'] != 'complete':
            continue
        text = f"[{row['text']}]" if row['role'] in ('scene', story_cast.NOTE) else \
            story_cast.own_line(row, (pronouns or {}).get(row['speaker'])) if row['role'] == story_cast.ROLE else row['text']
        used += len(text)
        if used > budget_chars and chat:
            break
        role = 'assistant' if row['role'] == 'narrator' else 'user'
        if chat and chat[0]['role'] == role:
            chat[0] = {'role': role, 'content': text + '\n\n' + chat[0]['content']}
        else:
            chat.insert(0, {'role': role, 'content': text})
    return chat


def steered(chat: list[dict], steer: str) -> list[dict]:
    """The story's author's note (companion/authors_note.py) right before the user's latest words."""
    if not steer or not chat or chat[-1]['role'] != 'user':
        return chat
    return [*chat[:-1], {'role': 'user', 'content': f"{steer}\n{NOTE_CLOSE}\n{chat[-1]['content']}"}]


def prompt(connection, now: datetime, config: dict, latest: dict) -> dict:
    view = scene(connection, now)
    system = prompt_library.text(connection, 'story-narrator') + '\n\n' + scene_text(view)
    if in_character.out_of_character(latest['text']):
        system += '\n\n' + in_character.OUT_OF_CHARACTER_NOTE.format(name='the narrator', model=default_name(config))
    budget = (config['context_tokens'] - config['max_output_tokens']) * CHARS_PER_TOKEN - len(system)
    rows = [row for row in messages(connection) if row['seq'] <= latest['seq']]
    chat = model_messages(rows, max(budget, 2000), {item['id']: item['pronouns'] for item in view['companions']})
    if not in_character.out_of_character(latest['text']):
        chat = steered(chat, authors_note.prompt_text(connection, 'story'))
        chat = story_cast.after(chat, view['companions'])  # A companion there answers for themself.
    return {'system': system, 'messages': chat, 'people': view['people'], 'view': view,
            'city_id': view['city']['id'], 'day': datetime.fromisoformat(view['local_time']).date()}


async def write(state, packet: dict, config: dict, active: bool) -> tuple[str, str | None]:
    """One reply from the model, the narrator's or a companion's, with the sentences that break character dropped."""
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


async def attempt(state, packet: dict, config: dict, active: bool) -> tuple[str, str | None]:
    try:
        return await write(state, packet, config, active)
    except DomainError as failure:
        return '', failure.message


def replies(connection, user: dict) -> list[dict]:
    return many(connection, "SELECT * FROM story_messages WHERE reply_to=? AND status='complete' ORDER BY seq",
                (user['id'],))


async def narrate(state, user: dict) -> tuple[dict, dict]:
    """The narrator's reply to the user's message, saved complete or failed with the reason; one that is already
    there is kept. Returns it with the scene it was told in."""
    database = state.database
    with database.connect() as connection:
        config = config_for(connection, JOB)
        if config is None:
            raise no_model()
        packet = prompt(connection, database.clock.now(), config, user)
        told = optional(connection, "SELECT * FROM story_messages WHERE reply_to=? AND role='narrator' AND "
                        "status='complete'", (user['id'],))
    if told:
        return told, packet['view']
    text, error = await attempt(state, packet, config, not in_character.out_of_character(user['text']))
    status = 'complete' if text and not error else 'failed'
    error = None if status == 'complete' else error or 'The model returned no story text.'
    with database.connect(write=True) as connection:
        connection.execute("DELETE FROM story_messages WHERE reply_to=? AND status='failed'", (user['id'],))
        if status == 'complete' and not in_character.out_of_character(user['text']):
            story_people.note_exchange(connection, packet['people'], packet['city_id'], user['text'], text,
                                       database.now(), packet['day'])
        return add(connection, database.now(), 'narrator', text, user, reply_to=user['id'], status=status,
                   error=error), packet['view']


async def speak(state, user: dict, item: dict) -> dict:
    """One companion's own line after the narrator's, by their own character (companion/story_cast.py)."""
    database = state.database
    with database.connect(write=True) as connection:
        config = reply_config(connection, CHAT) or config_for(connection, JOB)
    with database.connect() as connection:
        view = scene(connection, database.clock.now())
        packet = story_cast.prompt(connection, view, item, config, user, seen)
        steer = authors_note.prompt_text(connection, 'story')
    if steer:  # The story's author's note, last of the notes, right before the turn.
        notes = packet['messages'][-1]['content'].removesuffix(packet['turn'])
        packet = {**packet, 'messages': [{'role': 'user', 'content': f"{notes}{steer}\n\n{packet['turn']}"}]}
    active = in_character.applies(user['text'], item['companion']['version']['definition'])
    text, error = await attempt(state, packet, config, active)
    text = story_cast.tidy(text, item, view)
    status = 'complete' if text and not error else 'failed'
    error = None if status == 'complete' else error or f"The model returned nothing for {item['name']}."
    with database.connect(write=True) as connection:
        line = add(connection, database.now(), story_cast.ROLE, text, user, reply_to=user['id'], status=status,
                   error=error, speaker=item['id'], name=item['name'])
        story_visits.heard(connection, line, database.clock.now())
        return line


async def answer(state, user: dict) -> list[dict]:
    """The replies to the user's message: the narrator's, then each companion in the scene in their own words.
    What is already written is kept, so sending again or trying again only fills in what is missing. A message out
    of the story is the narrator's alone to answer."""
    told, view = await narrate(state, user)
    if told['status'] != 'complete' or in_character.out_of_character(user['text']):
        return [told]
    with state.database.connect() as connection:
        done = {row['speaker'] for row in replies(connection, user)}
        newest = optional(connection, "SELECT id FROM story_messages WHERE role='user' ORDER BY seq DESC LIMIT 1")
    if newest['id'] == user['id']:  # Only the latest line is still being answered.
        for item in story_cast.speakers(view['companions'], view['people'], user['text']):
            if item['id'] not in done and (await speak(state, user, item))['status'] != 'complete':
                break
    with state.database.connect() as connection:
        return many(connection, 'SELECT * FROM story_messages WHERE reply_to=? ORDER BY seq', (user['id'],))


def record(database, text: str, client_id: str, hidden: bool = False) -> dict:
    """The user's message, saved once whatever retries come. A companion who has come to where the story is, or
    gone, since the last line does so first (companion/story_cast.py). A hidden one is the app's, to start a plan's
    scene (`begin`): the models read it and the screen does not show it."""
    with database.connect(write=True) as connection:
        user = optional(connection, 'SELECT * FROM story_messages WHERE client_id=?', (client_id,))
        if user is None:
            where, view = scene_row(connection), scene(connection, database.clock.now())
            story_cast.sync(connection, add, view['companions'], database.now(), where)
            user = add(connection, database.now(), 'user', text, where, client_id=client_id, hidden=hidden)
            # Time with a companion counts (companion/story_visits.py): read before anyone answers the line.
            story_visits.said(connection, user, view, database.clock.now())
        return user


async def send(state, text: str, client_id: str) -> dict:
    """`reply` is the narrator's; `replies` are all of them in order, a companion's own lines after it."""
    user = record(state.database, text, client_id)
    found = await answer(state, user)
    return {'message': user, 'reply': found[0], 'replies': found}


async def begin(state, client_id: str) -> dict:
    """Start the scene of the plan being played here without a line from the user: the narrator opens it and the
    companion speaks, as if the user had turned to them (companion/story_plans.py)."""
    database = state.database
    with database.connect() as connection:
        found = scene(connection, database.clock.now())
    item = next((item for item in found['companions'] if item.get('plan')), None)
    require(item is not None, "There is no plan under way here.", 409)
    user = record(database, story_plans.BEGIN.format(name=item['name']), client_id, hidden=True)
    replies_ = await answer(state, user)
    return {'message': user, 'reply': replies_[0], 'replies': replies_}


async def retry(state) -> dict:
    """Try again what failed in the replies to the user's latest message, keeping what was written; with nothing
    failed, tell the whole reply again."""
    with state.database.connect(write=True) as connection:
        user = optional(connection, "SELECT * FROM story_messages WHERE role='user' ORDER BY seq DESC LIMIT 1")
        require(user is not None, 'There is nothing to retell yet.', 409)
        failed = connection.execute("DELETE FROM story_messages WHERE reply_to=? AND status='failed'",
                                    (user['id'],)).rowcount
        if not failed:
            connection.execute('DELETE FROM story_messages WHERE reply_to=?', (user['id'],))
    found = await answer(state, user)
    return {'message': user, 'reply': found[0], 'replies': found}
