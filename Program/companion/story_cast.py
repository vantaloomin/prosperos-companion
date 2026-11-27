"""Companions in the Story's scene (1.5, docs/story.md): when the story is where a companion is at that hour, they
are there, and they speak for themselves.

Rules decide who is there, as for everyone else in the scene. Every companion, the main character and those who
stepped back alike, is where their own day has them (the agenda the life sim keeps, else their routine): at work
during a shift, at the city place their slot happens at, or at one their block names. Asleep, off sick, at home or
anywhere the city has no place for, they are not in the story. While a plan with the user is under way they are
where the plan is, as the person the user came with (companion/story_plans.py).

`story_cast` keeps who is in the scene with the user and the line they came in at: a companion reads the story from
there on, never what was said before. A 'cast' line in the story says when one comes or goes. Someone the user is
in the middle of talking with stays a little longer than their day says (LINGER) rather than leaving mid-sentence.

Each reply in such a scene is the narrator's, then one ordinary model call for each companion there, the group chat
way (companion/groups.py): the scene rules, the scene and the story since they came in, the same for every speaker,
then that companion's own 1:1 sections with one `story` section (memory/context.py), then the turn. The narrator is
told who speaks for themself and never writes their lines. What the time together
leaves behind is companion/story_visits.py.
"""
import re
from datetime import datetime, timedelta

from companion import prompt_library, story_plans, story_private, texting
from companion.characters import by_id, current
from companion.clock import parse, stamp
from companion.database import decode, many, optional
from companion.images import places
from companion.life import pacing
from companion.life import pronouns as words
from companion.memory import context
from companion.memory.budget import token_estimate
from companion.world import catalog, looks, newcomers, townsfolk

ACTIVE = True
ROLE, NOTE = 'companion', 'cast'
# How long after the last line of the scene someone the user was with stays, once their own day has moved on.
LINGER = timedelta(minutes=45)
SPEAKERS = 3
TRANSCRIPT_SHARE = 0.4
AT_WORK, OWN_TIME = 'at work here', 'here on their own time'

RULES = """This is a scene in a story the user is living in person. The user plays themself. A narrator describes \
the place and voices everyone else there. You are one of the people in the scene, with your own life and memories, \
and you speak for yourself.

How the scene works:
- The scene so far is written as lines. "User:" is what the user says and does. "Narrator:" describes the place \
and the other people, and calls the user "you". Lines in [square brackets] are notes from the app, not part of \
the story.
- You and the user are in the same place, face to face. Nobody is texting: anything you would have sent, you say \
or do.
- Write only your own next turn, with no name in front: what you say, in quotation marks, with at most a sentence \
or two of what you do, written about yourself by name in the present tense, the way the narrator writes \
({name} looks up. "You came.").
- Never write what the user says, does, thinks or feels, and never write for the narrator or for anyone else in \
the scene. What the place is like and what other people do is the narrator's to tell.
- Keep it as short as one person's turn in a conversation: a few sentences at most, unless the moment needs \
more. If what the user just did was not meant for you, a look or a short line is enough.
- The scene's facts are true: the place, the hour, the weather and who is there. You are there for your own \
reasons, given in your notes. Keep to them."""

TURN = "Write {name}'s next turn in the scene: only what {name} says and does, with no name in front."
# How the narrator is told about a companion in the scene, in place of a person's sheet.
SPEAKS = ('- {full}, {pronouns}, {doing}. The user knows {name} well. {name} speaks and acts for {themself}: {their} '
          'own lines come right after yours, marked with {their} name. Never write what {name} says, does, thinks or '
          'feels. At most, say where {name} is.')
# Added under the scene while a companion is in it.
BESIDE = ('While the user is talking with {names}, keep your part short: a paragraph at most about the place and the '
          'other people, and stop before {names} would answer.')
# Last thing the narrator reads, after the user's line: small models follow what is nearest.
AFTER = ('[{names} will answer in {their} own words right after you. Write nothing {names} says or does: leave that '
         'to {them}.]')
OWN_LINE = '[{name}, in {their} own words:]\n{text}'
LABELS = {'user': 'User', 'narrator': 'Narrator'}
YOU = re.compile(r'^You(r)?\b')


# Who is there -------------------------------------------------------------------------------------

def member(companion: dict, doing: str, main: bool) -> dict:
    definition = companion['version']['definition']
    name = definition['name'].strip()
    return {'id': companion['id'], 'name': name.split()[0], 'full': name, 'main': main, 'doing': doing,
            'pronouns': looks.pronouns_of(definition), 'companion': companion}


def place_now(connection, companion: dict, data: dict, now: datetime) -> tuple[dict, str] | None:
    """(city place, what they are doing there) by a companion's own day right now, or None: asleep, off sick, at
    home, or somewhere the city has no place for."""
    row = optional(connection, "SELECT block, entry FROM life_agenda WHERE timeline_id=? AND subject='companion' "
                   'AND starts_at<=? AND ends_at>? ORDER BY starts_at DESC LIMIT 1',
                   (companion['active_timeline_id'], stamp(now), stamp(now)))
    found = pacing.block_now(connection, companion, now)
    block = decode(row['block']) if row else found[0] if found else None
    if not block or block['kind'] == 'sleep' or block.get('sick_day'):
        return None
    if block['kind'] in ('work', 'study'):
        return work_place(connection, companion, data, block, now)
    entry = decode(row['entry']) if row and row['entry'] else {}
    named = entry.get('place') if isinstance(entry.get('place'), dict) else None
    place = named and catalog.find(data, named.get('id') or '') or places.first_named(block.get('label') or '', data)
    return (place, OWN_TIME) if place and place in data['places'] else None


def work_place(connection, companion: dict, data: dict, block: dict, now: datetime) -> tuple[dict, str] | None:
    """Where they work, during a shift that is not a holiday or time out with the user. A class has no place."""
    from companion.life import drop_by
    if block['kind'] != 'work' or not drop_by.on_shift(connection, companion, now):
        return None
    job = drop_by.workplace(connection, companion)
    place = job and catalog.find(data, job['id'])
    return (place, AT_WORK) if place and place in data['places'] else None


def everyone(connection) -> list[tuple[dict, bool]]:
    """Every companion in the workspace with a character, the main one first."""
    rows = many(connection, 'SELECT id, slot FROM companions WHERE active_version_id IS NOT NULL '
                'ORDER BY slot IS NULL, slot, created_at, id')
    found = [(by_id(connection, row['id']), row['slot'] == 1) for row in rows]
    return [(companion, main) for companion, main in found if companion]


def whereabouts(connection, data_for, now: datetime) -> list[dict]:
    """Every companion with where their day has them now: a member with `city` (their city's data, None when it
    is gone) and `place` (None: at home, asleep, somewhere the story can't go). `data_for(city_id)` is the Story's
    own city data (companion/story.py), or None."""
    if not ACTIVE:
        return []
    result = []
    for companion, main in everyone(connection):
        data = data_for(newcomers.city_for(connection, companion['version']['definition'])['id'])
        # A plan with the user under way is where they are, whatever the rest of their day says (story_plans.py).
        plan = story_plans.under_way(connection, companion, now)
        found = story_plans.placed(plan, data) if plan else place_now(connection, companion, data, now) if data else None
        result.append({**member(companion, found[1] if found else '', main), 'place': found and found[0], 'city': data,
                       'plan': plan if found else None})
    return result


def ruled(connection, data: dict, place_id: str, now: datetime) -> list[dict]:
    """Every companion whose day puts them at the place right now, the main character first."""
    found = whereabouts(connection, lambda city_id: data if city_id == data['id'] else None, now)
    return [item for item in found if item['place'] and item['place']['id'] == place_id]


def lingering(connection, known: set[str], now: datetime) -> list[dict]:
    """Companions already in the scene whose day has moved on, while the scene's last line is still fresh."""
    rows = [row for row in many(connection, 'SELECT * FROM story_cast ORDER BY since_seq, companion_id')
            if row['companion_id'] not in known]
    latest = optional(connection, 'SELECT created_at FROM story_messages ORDER BY seq DESC LIMIT 1')
    if not rows or not latest or now - parse(latest['created_at']) > LINGER:
        return []
    main = current(connection)
    found = [by_id(connection, row['companion_id']) for row in rows]
    return [member(companion, OWN_TIME, bool(main) and companion['id'] == main['id']) for companion in found if companion]


def here(connection, data: dict, place_id: str, now: datetime) -> list[dict]:
    found = ruled(connection, data, place_id, now)
    return found + lingering(connection, {item['id'] for item in found}, now)


# Coming and going ---------------------------------------------------------------------------------

def sync(connection, add, present: list[dict], now: str, where: dict) -> None:
    """Bring `story_cast` in line with who is in the scene: a 'cast' line for each companion who came or went.
    `add` is the Story's own (companion/story.py)."""
    there = {item['id']: item for item in present}
    for row in many(connection, 'SELECT * FROM story_cast'):
        if row['companion_id'] not in there:
            connection.execute('DELETE FROM story_cast WHERE companion_id=?', (row['companion_id'],))
            gone = by_id(connection, row['companion_id'])
            if gone:
                name = gone['version']['definition']['name'].split()[0]
                add(connection, now, NOTE, f'{name} has gone.', where, speaker=row['companion_id'], name=name)
    kept = {row['companion_id'] for row in many(connection, 'SELECT companion_id FROM story_cast')}
    for item in present:
        if item['id'] not in kept:
            text = story_plans.arrived(item) if item.get('plan') else f"{item['name']} is here."
            line = add(connection, now, NOTE, text, where, speaker=item['id'], name=item['name'])
            connection.execute('INSERT INTO story_cast (companion_id, since_seq, joined_at) VALUES (?, ?, ?)',
                               (item['id'], line['seq'], now))


def leave(connection) -> None:
    """The user went somewhere else, or cleared the pages: nobody is with them any more."""
    connection.execute('DELETE FROM story_cast')


# Who answers --------------------------------------------------------------------------------------

def named(item: dict, text: str) -> bool:
    return any(re.search(rf'(?<![\w-]){re.escape(name)}(?![\w-])', text) for name in (item['full'], item['name']))


def speakers(present: list[dict], people: list[dict], text: str) -> list[dict]:
    """The companions who take a turn after the narrator, anyone the user named first. A line that names only
    someone else in the scene ("Dana, could I get the bill?") is not theirs to answer, and a private moment is
    answered only by the one it was for (companion/story_private.py)."""
    from companion import story_people
    only = story_private.only(story_private.read(text, present, people), present)
    if only is not None:
        return only
    spoken_to = [item for item in present if named(item, text)]
    if not spoken_to and any(story_people.named(person['sheet'], text) for person in people):
        return []
    return (spoken_to + [item for item in present if item not in spoken_to])[:SPEAKERS]


# What the narrator is told ------------------------------------------------------------------------

def narrator_lines(present: list[dict]) -> list[str]:
    return [SPEAKS.format(full=item['full'], name=item['name'], pronouns=item['pronouns'], doing=item['doing'],
                          **words.person(item['pronouns'])) for item in present]


def beside(present: list[dict]) -> str:
    return BESIDE.format(names=names_text([item['name'] for item in present])) if present else ''


def after(chat: list[dict], present: list[dict]) -> list[dict]:
    """The narrator's conversation with the reminder after the user's latest line, while a companion is there."""
    if not present or not AFTER or not chat or chat[-1]['role'] != 'user':
        return chat
    forms = words.person(present[0]['pronouns'] if len(present) == 1 else None)
    note = AFTER.format(names=names_text([item['name'] for item in present]), **forms)
    return [*chat[:-1], {'role': 'user', 'content': f"{chat[-1]['content']}\n\n{note}"}]


def names_text(names: list[str]) -> str:
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def own_line(row: dict, pronouns: str | None = None) -> str:
    """A companion's line as the narrator reads it, on the user's side of the conversation."""
    return OWN_LINE.format(name=row['name'], text=row['text'], **words.person(pronouns))


# A companion's own turn ---------------------------------------------------------------------------

def line(row: dict, tags: dict | None = None) -> str:
    """A line of the scene, the same for every speaker, their own included. `tags` marks the private ones
    (companion/story_private.py)."""
    if row['role'] in ('scene', NOTE):
        return f"[{YOU.sub(lambda match: 'The user' + ('’s' if match[1] else ''), row['text'])}]"
    return story_private.tagged(f"{LABELS.get(row['role'], row['name'])}: {row['text']}", row, tags)


def visible(connection, companion_id: str) -> list[dict]:
    """The story since they came in (the line that says so is the app's, for the user)."""
    stay = optional(connection, 'SELECT since_seq FROM story_cast WHERE companion_id=?', (companion_id,))
    if stay is None:
        return []
    return many(connection, "SELECT * FROM story_messages WHERE status='complete' AND seq>? ORDER BY seq",
                (stay['since_seq'],))


def window(rows: list[dict], budget: int) -> list[dict]:
    """The newest lines that fit, always the last one."""
    kept, used = [], 0
    for row in reversed(rows):
        used += token_estimate(line(row)) + 1
        if kept and used > budget:
            break
        kept.insert(0, row)
    return kept


def scene_part(view: dict, item: dict, seen) -> str:
    """The scene as someone standing in it has it: the place, the hour, the weather and who else is there, as the
    screen shows them. `seen` is the Story's own (companion/story.py)."""
    place, moment = view['place'], datetime.fromisoformat(view['local_time'])
    part = townsfolk.part_of_day(moment.hour * 60 + moment.minute)
    around = story_plans.around(view['companions']) + [seen(person, view) for person in view['people']] + \
        [other['name'] for other in view['companions'] if other['id'] != item['id']]
    from companion import story  # Imported here: it reads this module.
    lines = [story.home_line(place, view['city']['name']) if place.get('home') else
             f"Place: {place['name']}, a {place['kind']} in {place['neighborhood']}, {view['city']['name']}. "
             f"{place['summary']}".rstrip(),
             f"Local time: {moment:%A} {moment.day} {moment:%B}, {moment:%H:%M} ({part})."]
    if view['weather']:
        lines.append(f"Weather: {view['weather']}")
    lines.append(f"Also here: {', '.join(around)}." if around else 'Nobody else you would notice is here.')
    return '## The scene\n' + '\n'.join(lines)


def shared_part(connection, view: dict, item: dict, rows: list[dict], budget: int, seen) -> str:
    kept = window(rows, int(budget * TRANSCRIPT_SHARE))
    tags = story_private.tags(rows, view, seen)  # What was for one person alone says so, for everyone who reads it.
    transcript = '## The scene so far\n' + ('\n'.join(line(row, tags) for row in kept) or
                                            '(Nothing has been said yet.)')
    return '\n\n'.join((prompt_library.text(connection, 'story-companion', name=item['name']),
                        scene_part(view, item, seen), transcript))


def story_lines(connection, view: dict, item: dict, rows: list[dict], now: datetime) -> list[tuple[str, str]]:
    """Their own view of the scene, private to them: where they are and why, who came to whom, and how they stand
    with any other companion there (as in a group chat, companion/groups.py)."""
    from companion import groups, story_said, story_visits
    lines = story_plans.own_lines(connection, item, view['place'], now) if item.get('plan') else \
        chance_lines(connection, view, item)
    lines.append(('story:sealed', 'What happens here is in person. You have seen only what the lines above show.'))
    lines += story_private.own_lines(rows, view, item)  # The user's line was for them alone.
    if story_visits.counts(connection):  # How they feel right now, as their chat is told (companion/story_said.py).
        lines += story_said.feeling_lines(connection, item['companion'], now)
    for other in view['companions']:
        if other['id'] != item['id']:
            lines += groups.member_lines(connection, groups.member_key(item['id']),
                                         {'member': groups.member_key(other['id']), 'name': other['name']}, now)
    # What they know that someone here must not find out, and news someone here hasn't heard (story_secrets.py).
    from companion import story_secrets
    return lines + story_secrets.lines(connection, view, item, now)


def chance_lines(connection, view: dict, item: dict) -> list[tuple[str, str]]:
    """With no plan between them: where they are and why, and who came to whom."""
    from companion import story  # Imported here: it reads this module.
    place = view['place']
    doing = 'at work here' if item['doing'] == AT_WORK else 'here on your own time'
    at = story.HOME_TOLD if place.get('home') else place['name']  # Their own home is not "Your home" to a companion.
    lines = [(f"story:{place['id']}", f"You are {item['name']}, in person with the user at {at}. "
              f"You are {doing}.")]
    stay = optional(connection, 'SELECT since_seq FROM story_cast WHERE companion_id=?', (item['id'],))
    if here_first(connection, stay['since_seq'] if stay else 0):
        lines.append(('story:came', 'You were here first. The user has come in; you did not know they were coming.'))
    else:
        lines.append(('story:came', 'The user was here before you. You have come in and found them here.'))
    return lines


def here_first(connection, since_seq: int) -> bool:
    """Nothing was said at this place before they were in the scene: the user walked in on them."""
    arrival = optional(connection, "SELECT COALESCE(MAX(seq), 0) AS seq FROM story_messages WHERE role='scene' AND seq<?",
                       (since_seq,))
    return optional(connection, "SELECT 1 FROM story_messages WHERE seq>? AND seq<? AND role IN ('user', 'narrator', "
                    "'companion')", (arrival['seq'], since_seq)) is None


def prompt(connection, view: dict, item: dict, config: dict, user: dict, seen) -> dict:
    """One companion's request: the shared part, then their private sections, then the turn."""
    from companion import story_visits  # Imported here: it reads this module.
    budget = config['context_tokens'] - config['max_output_tokens']
    rows = visible(connection, item['id'])
    shared = shared_part(connection, view, item, rows, budget, seen)
    private = context.build(connection, item['companion'], view['now'], max(budget - token_estimate(shared), 1000),
                            group={'older': [], 'query': user['text'], 'previous': None, 'shared': shared,
                                   'in_person': True, 'section': 'story',
                                   'lines': story_lines(connection, view, item, rows, view['now'])
                                   # A relationship step the user's line just settled (companion/story_visits.py).
                                   + story_visits.fresh_lines(connection, item['companion'], user, view['now'])})
    turn = TURN.format(name=item['name'])
    return {'system': f"{shared}\n\n{private['system']}", 'turn': turn,
            'messages': [{'role': 'user', 'content': f"{context.NOTE_OPEN}\n{private['note']}\n\n{turn}"}]}


def tidy(text: str, item: dict, view: dict) -> str:
    """Their own turn only: a leading "Name:" goes, the reply stops where it starts writing the user's or the
    narrator's line, and what was said out loud keeps its capitals (companion/texting.py)."""
    label = r'\**\s*:\s*\**\s*'
    text = re.sub(rf"^\s*\**(?:{re.escape(item['name'])}|{re.escape(item['full'])}){label}", '', text.strip(),
                  flags=re.IGNORECASE)
    names = ['User', 'You', 'Narrator'] + [other['name'] for other in view['companions'] if other['id'] != item['id']]
    cut = re.search(rf"(?m)^\s*\**(?:{'|'.join(re.escape(name) for name in names)}){label}", text)
    return texting.spoken((text[:cut.start()] if cut else text).strip())
