"""Play a plan as a scene (1.5, docs/story.md): a plan with a companion that is under way can be played in the
Story, at its place, with the people it is with.

A plan is an outing (companion/life/outings.py): a date or anything else the two of them settled in chat, a meet-up
with the companion's people, a big day, or the plan a storyline the user is part of booked
(companion/life/shared_storylines.py). Rules decide all of it, and nothing is stored:

- While a plan is under way the companion is where the plan is, not where the rest of their day would have them
  (`placed`, read by companion/story_cast.py). When the story is there, they are in the scene as the person the user
  came with, and the people the plan is with are in it too, voiced by the narrator.
- The narrator and the companion are told it is the plan, in the scene and in the companion's own notes: the two
  came together, on purpose, and nobody is surprised to see the other.
- The app never moves the story by itself: Today's "Out together" and the Story offer to go there (`play`), and the
  user can always play the plan in the chat instead, as before.

What the time together leaves is the plan's own (the outing's memory, its bill, the storyline's next beat) and
companion/story_visits.py's: the day talked and what was said, told to their chat. The visit leaves no shared moment
of its own, since the plan already leaves one.
"""
from datetime import datetime

from companion.characters import by_id
from companion.database import many
from companion.errors import require
from companion.life import outings, their_people, together
from companion.world import catalog

ACTIVE = True
# What the plan is, after "for": as the screen says it to the user, and as the narrator is told about the two of them.
SHOWN = {'wedding': 'your wedding', 'visit-work': 'a visit while they work', 'meet-friends': 'drinks with their friends'}
TOLD = {'wedding': 'their wedding to the user', 'visit-work': 'a visit from the user during their shift',
        'meet-friends': 'drinks with their friends'}
DOING = 'here with the user, for {what}: a plan the two of them made'
# What the models read when the user starts the scene with the button: said for them, and never shown as theirs.
BEGIN = 'I turn to {name}.'
ARRIVED = '{name} is here with you, for {what}.'
# The narrator's line under the scene while a plan is being played.
PLAN = ('The plan: the user and {name} came here together for {what}, until about {until}. They planned it; they did '
        'not meet here by chance, and neither is surprised to see the other.')
ALONG = ('- {full}, {name}\'s {role}, here with them for the evening. {met} {manner} You voice {first}, as you do '
         'everyone but {name}.')
MET = {True: 'It is the first time {first} is meeting the user.', False: '{first} has met the user before.'}
# How each of their people is with the user (their_people.IMPRESSIONS), as the narrator is told.
MANNER = {'warm': '{first} is warm and easy with the user.', 'smitten': '{first} is delighted by the two of them.',
          'curious': '{first} is polite and has a lot of questions for the user.',
          'protective': '{first} is a little protective of {name} and watches the user closely.',
          'wary': '{first} is cool and reserved with the user.'}
# The companion's own notes (the 'story' section, companion/story_cast.py).
TOGETHER = ('You are {name}, in person with the user at {place}. You are here together: {what}, until about {until}. '
            'It is a plan the two of you made.')
CAME = ('You came here together. Neither of you is surprised to see the other: this is the time you set aside for '
        'each other.')
PEOPLE = 'Here with you: {people}.{first} The narrator speaks for them; you speak only as yourself.'


def under_way(connection, companion: dict, now: datetime) -> dict | None:
    """The plan with the user under way right now, as Today has it: where the two of them are now (the second place
    once they moved on, companion/life/onward.py, or where their chat took them, companion/life/scene_now.py)."""
    if not ACTIVE:
        return None
    outing = together.together_now(connection, companion, now)
    return outings.where_now(connection, companion, outing, now) if outing else None


def place_of(plan: dict, data: dict | None) -> dict | None:
    """The city place a plan is at, or None: at home, at their family's, on the move, or in a city that is gone."""
    found = catalog.find(data, plan['place'].get('id') or '') if data else None
    return found if found and found in data['places'] else None


def placed(plan: dict, data: dict | None) -> tuple[dict, str] | None:
    """(city place, what they are doing there) for a companion whose plan is under way, in the shape
    story_cast.place_now gives; None when the story cannot go there."""
    place = place_of(plan, data)
    return (place, DOING.format(what=what(plan, TOLD))) if place else None


def what(plan: dict, words: dict) -> str:
    """'dinner', 'a walk', 'Leo's wedding': the plan in a word or two, after "for"."""
    activity, place = plan['activity'], plan['place']
    if activity in words:
        return words[activity]
    if activity == 'big-day':
        return place.get('title') or 'a big day'
    if activity == 'hobby':
        hobby = place.get('hobby') or {}
        return hobby.get('event') or hobby.get('together') or 'a pastime together'
    return outings.ACTIVITIES[activity][5]


def people(plan: dict) -> list[dict]:
    """Who the plan is with besides the two of them: the companion's people at a meet-up
    (companion/life/their_people.py), or the person a storyline brought (companion/life/shared_storylines.py)."""
    return plan['place'].get('people') or []


def playable(connection, companion: dict, outing: dict) -> bool:
    """Whether Today can offer to play this outing in the Story: under way, somewhere in their city."""
    if not ACTIVE or outing.get('state') != 'now':
        return False
    return place_of(outing, outings.city_data(connection, companion['version']['definition'])) is not None


def find(connection, outing_id: str, now: datetime) -> tuple[dict, dict]:
    """(companion, plan) for an outing the user asked to play: it has to be under way now."""
    outing = outings.get(connection, outing_id)
    companion = by_id(connection, outing['companion_id'])
    plan = under_way(connection, companion, now) if companion else None
    require(plan is not None and plan['id'] == outing_id, "That plan isn't under way right now.", 409)
    return companion, plan


# What the screen shows ----------------------------------------------------------------------------

def arrived(item: dict) -> str:
    """The story's line when the companion of a plan is in the scene: "Mira is here with you, for dinner." """
    return ARRIVED.format(name=item['name'], what=what(item['plan'], SHOWN))


def view(item: dict) -> dict:
    """The plan for the screen: what it is, until when, who it is with and whether a storyline booked it."""
    plan = item['plan']
    return {'outing_id': plan['id'], 'companion_id': item['id'], 'name': item['name'], 'what': what(plan, SHOWN),
            'until': plan['until_time'], 'place': plan['place']['name'], 'storyline': bool(plan['place'].get('storyline')),
            'people': [{'name': their_people.first(person['name']), 'role': person['role']} for person in people(plan)]}


def seen(present: list[dict]) -> list[str]:
    """The people the plans in the scene are with, as the screen lists them after the companion: "their mom Ana"."""
    return [f"their {person['role']} {their_people.first(person['name'])}"
            for item in present if item.get('plan') for person in people(item['plan'])]


def around(present: list[dict]) -> list[str]:
    """The people the plans in the scene are with, as a companion's scene lists them: "Ana, Mira's mom"."""
    return [f"{their_people.first(person['name'])}, {item['name']}'s {person['role']}"
            for item in present if item.get('plan') for person in people(item['plan'])]


# What the narrator is told ------------------------------------------------------------------------

def impressions(connection, item: dict) -> dict[str, str]:
    rows = many(connection, 'SELECT person_id, impression FROM people_impressions WHERE timeline_id=?',
                (item['companion']['active_timeline_id'],))
    return {row['person_id']: row['impression'] for row in rows}


def narrator_people(connection, present: list[dict]) -> list[str]:
    """A line for each person the plans in the scene are with: who they are to the companion, whether they have met
    the user and how they are with them. The narrator voices them, as it does everyone but the companion."""
    lines = []
    for item in present:
        plan = item.get('plan')
        found = impressions(connection, item) if plan and people(plan) else {}
        for person in people(plan) if plan else ():
            names = {'first': their_people.first(person['name']), 'name': item['name']}
            manner = MANNER.get(found.get(person['id'], ''), '').format(**names)
            met = MET[bool(plan['place'].get('first'))].format(**names)
            lines.append(' '.join(ALONG.format(full=person['name'], role=person['role'], met=met, manner=manner,
                                               **names).split()))
    return lines


def narrator_plan(present: list[dict]) -> list[str]:
    return [PLAN.format(name=item['name'], what=what(item['plan'], TOLD), until=item['plan']['until_time'])
            for item in present if item.get('plan')]


# What the companion is told -----------------------------------------------------------------------

def own_lines(connection, item: dict, place: dict, now: datetime) -> list[tuple[str, str]]:
    """The companion's own notes on the plan they are on with the user, in place of who came to whom: what it is,
    that they came together, who else it is with and how long they have been at it."""
    plan, companion = item['plan'], item['companion']
    timezone = companion['version']['timezone']
    lines = [(f"story:{place['id']}", TOGETHER.format(name=item['name'], place=place['name'], what=outings.what(plan),
                                                     until=plan['until_time'])),
             ('story:came', CAME)]
    if people(plan):
        first = ' It is the first time they are meeting the user.' if plan['place'].get('first') else ''
        lines.append(('story:people', PEOPLE.format(people=their_people.people_text(people(plan)), first=first)))
    if plan['activity'] in outings.LONG_DAYS:  # The day's own order, guests and customs (wedding.py, big_days.py).
        lines.append(('story:day', outings.scene(connection, companion, plan, now).removeprefix('- ')))
    elif menu := outings.menu(outings.city_data(connection, companion['version']['definition']), plan):
        lines.append(('story:menu', menu))
    lines += [(identity, text.removeprefix('- ')) for identity, text in outings.since_lines(plan, timezone, now)]
    return lines
