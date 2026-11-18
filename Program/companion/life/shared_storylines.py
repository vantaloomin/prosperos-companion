"""Storylines you are part of (v1.5.0 "Rich and Strange"): things the world starts that involve the user.

A storyline was always something the user heard about: a friend's breakup, a parent's promotion. A tester's world
ran sixteen days and 398 of her messages with three of those and nothing that happened to her and her companion as a
pair (2026-11-18). A shared storyline is an ordinary storyline with the user in the cast. The world starts it, the
user is drawn in, and what the user does, or does not do, decides where it goes.

The rules that keep it honest ("the world exists outside of User", Vanta 2026-10-08):

- Every beat arrives through something that exists: a first text (companion/life/openers.py), or an invitation that
  books a plan on Today's "Out together" (companion/life/outings.py). It is a row in `storylines` with the story
  `shared:<key>`, so Today lists it, the chat context tells it and the user can end it, like any other.
- No beat waits for the user. Each has a default, and letting it pass is an answer with its own branch.
- The app only reads what it can tell for sure (`respond`): they went or called the plan off, they answered the
  text, said a plain yes or no, dropped by, or let it go by. It never guesses what a reply meant.
- What comes next is picked from that; where it could go more than one way, the consequence engine
  (companion/consequences.py) rolls from how close the two are, the companion's own description and the drama
  level, so "Why it went this way" and "Make it go this way" work as they do for any turning.
- One at a time, never two beats on one day, and nothing above the world's drama level.
- A quiet-spell floor: after `FLOOR` days with none, one starts, so something always turns up.

No model decides anything: the bank (world/data/shared_storylines.json) and seeded dice do, and the model only puts
a first text in the companion's words. Realism > Their days > "Things that involve you" sets how often: off, now and
then, true to life (about one a week) or often.
"""
import json
import random
import re
from datetime import date, datetime, time, timedelta
from functools import cache

from companion import consequences
from companion.clock import parse, stamp, zone
from companion.database import decode, encode, identifier, many, optional
from companion.errors import require
from companion.life import casting, circle, outings, routine, steps, storylines, their_people
from companion.world import catalog, perception

ACTIVE = True  # Off in most tests (tests/conftest.py): a storyline would start in unrelated ones.
FIRST_TEXTS = True
LEVELS = ('off', 'now and then', 'true to life', 'often')
USUAL = 2
# By the slider: the chance one starts on a day with none running, how many days after the last one ended before the
# next can start, and the quiet-spell floor (this many days with none and one starts).
CHANCE = (0.0, 0.1, 0.35, 0.6)
REST = (0, 7, 2, 1)
FLOOR = (0, 21, 6, 3)
# The same story again only after this long; with every fitting one told that recently, the one told longest ago
# comes round again once it is REUSE_AFTER days old, so the floor still holds in a small circle.
REPEAT_AFTER = 90
REUSE_AFTER = 30
SETTLE_IN = 2  # Days after the two first talked before anything starts.
AWAY_DAYS = 3  # Nothing starts while the user has not written for this long: a storyline nobody is there for.
# How long the user has to answer a text before it counts as let go by.
WINDOW = timedelta(hours=18)
GAP = (1, 3)
LEAD = (2, 4)
PENDING = 'shared'
SETTLES = ('shared_plan',)
# A plan with someone from their circle is a meet-up (companion/life/their_people.py), by who they are.
WITH = {'friends': their_people.OUT_WITH_FRIENDS, 'family': their_people.AT_FAMILY}
# What a kept plan with one of them is in the companion's day (`as_plans`), and the places an entry does not name.
WITH_ACTIVITY = {'friends': 'drinks', 'family': 'dinner'}
HOMES = ('home', 'your-home', 'family-home')
DROPPED_IN = ('in', 'work')
WARMER, COOLER = 'a good time together', 'you did not come'


@cache
def bank() -> dict[str, dict]:
    found = json.loads((catalog.DATA / 'shared_storylines.json').read_text(encoding='utf-8'))['stories']
    return {story['key']: story for story in found}


def key_of(row: dict) -> str:
    return row['story'].removeprefix(storylines.SHARED)


def level(connection) -> int:
    """Realism > Their days > Things that involve you: 0 off, 1 now and then, 2 true to life, 3 often."""
    row = optional(connection, 'SELECT shared_storylines FROM life_settings WHERE id=1')
    return row['shared_storylines'] if row else USUAL


def local(companion: dict, now: datetime) -> datetime:
    return now.astimezone(zone(companion['version']['timezone']))


def rows(connection, timeline_id: str, running: bool = False) -> list[dict]:
    status = "AND status='running' " if running else ''
    return many(connection, f'SELECT * FROM storylines WHERE timeline_id=? AND story LIKE ? {status}'  # noqa: S608
                'ORDER BY started_on, created_at', (timeline_id, storylines.SHARED + '%'))


def save(connection, row: dict, stages: list[dict]) -> None:
    connection.execute('UPDATE storylines SET stages=? WHERE id=?', (encode(stages), row['id']))


def unfolding(row: dict, today: str) -> bool:
    """Still going: a beat is to come, or its last one is today's."""
    last = decode(row['stages'])[-1]
    return bool(last.get('pending')) or last['on'] >= today


# Starting one -----------------------------------------------------------------------------------------------------

def advance(connection, companion: dict, now: datetime) -> int:
    """Each time the agenda extends: what the user did about the last beat decides the next, then today's roll for
    a new one. Cheap: no model. Returns how many started."""
    if not ACTIVE or not companion.get('active_timeline_id'):
        return 0
    follow(connection, companion, now)
    return int(start_due(connection, companion, now))


def start_due(connection, companion: dict, now: datetime) -> bool:
    """Today's roll, once a day. Days the app was closed are not rolled afterwards (an invitation for last week);
    the quiet-spell floor makes up for them."""
    timeline_id, today = companion['active_timeline_id'], local(companion, now).date()
    cursor = optional(connection, 'SELECT shared_through FROM storyline_days WHERE timeline_id=?', (timeline_id,))
    if cursor and cursor['shared_through'] and cursor['shared_through'] >= today.isoformat():
        return False
    connection.execute('INSERT INTO storyline_days (timeline_id, through, shared_through) VALUES (?, ?, ?) '
                       'ON CONFLICT(timeline_id) DO UPDATE SET shared_through=excluded.shared_through',
                       (timeline_id, (today - timedelta(days=1)).isoformat(), today.isoformat()))
    pace = level(connection)
    if not pace or held(connection, companion, now):
        return False
    quiet = quiet_days(connection, companion, today, now)
    if quiet is None or quiet < REST[pace]:
        return False
    rng = random.Random(f'shared:{timeline_id}:{today.isoformat()}')
    if rng.random() >= CHANCE[pace] and quiet < FLOOR[pace]:
        return False
    found = draw(connection, companion, today, now, rng)
    if found is None:
        return False
    story, cast = found
    row_id, first = identifier(), next(iter(story['beats']))
    stages = begin(row_id, story, first, today)
    connection.execute(
        'INSERT INTO storylines (id, timeline_id, story, level, cast_ids, stages, started_on, status, created_at) '
        "VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?)",
        (row_id, timeline_id, storylines.SHARED + story['key'], story['level'], encode(list(cast)), encode(stages),
         today.isoformat(), stamp(now)))
    return True


def held(connection, companion: dict, now: datetime) -> bool:
    """Nothing new starts while one is going, while the two are apart or it is tense, while they grieve, or while the
    user only watches (companion/observer.py)."""
    from companion import observer
    from companion.life import breakups, loss, rough_patches
    today = local(companion, now).date().isoformat()
    if any(unfolding(row, today) for row in rows(connection, companion['active_timeline_id'], running=True)):
        return True
    return bool(observer.watching(connection) or breakups.holds(connection, companion)
                or rough_patches.cool(connection, companion, now) or loss.holds_back(connection, companion, now))


def talked(connection, companion: dict) -> tuple[date, date] | None:
    """The local days of the user's first and latest message here, or None when they have not written."""
    tz = zone(companion['version']['timezone'])
    row = optional(connection, "SELECT MIN(created_at) AS first, MAX(created_at) AS last FROM messages WHERE "
                   "timeline_id=? AND role='user' AND status='complete' AND active=1", (companion['active_timeline_id'],))
    if not row or not row['first']:
        return None
    return parse(row['first']).astimezone(tz).date(), parse(row['last']).astimezone(tz).date()


def quiet_days(connection, companion: dict, today: date, now: datetime) -> int | None:
    """Days since the last storyline the user was part of had its last beat, or since the two had settled in; None
    while nothing may start: they have not talked yet, or the user has been away."""
    found = talked(connection, companion)
    if found is None or (today - found[1]).days > AWAY_DAYS:
        return None
    since = found[0] + timedelta(days=SETTLE_IN - REST[level(connection)])
    for row in rows(connection, companion['active_timeline_id']):
        told = [stage['on'] for stage in decode(row['stages']) if not stage.get('pending')]
        since = max(since, date.fromisoformat(max(told))) if told else since
    return (today - since).days


def draw(connection, companion: dict, today: date, now: datetime, rng: random.Random) -> tuple[dict, tuple] | None:
    """(story, cast) for the storyline that starts today: one that fits, not told lately, of another family than the
    last one where it can be."""
    past = {}
    for row in rows(connection, companion['active_timeline_id']):
        past[key_of(row)] = row['started_on']
    last_family = bank().get(next(reversed(past), ''), {}).get('family')
    fitting = [(story, casts) for story in bank().values()
               if (casts := fits(connection, companion, story, today, now))]
    fresh = [item for item in fitting if (today - date.fromisoformat(past.get(item[0]['key'], '0001-01-01'))).days
             >= REPEAT_AFTER]
    if not fresh:
        again = [item for item in fitting if (today - date.fromisoformat(past[item[0]['key']])).days >= REUSE_AFTER]
        fresh = sorted(again, key=lambda item: past[item[0]['key']])[:1]
    if not fresh:
        return None
    story, casts = rng.choices(fresh, [1 if story['family'] == last_family else 3 for story, _casts in fresh])[0]
    return story, rng.choice(casts)


def plans(story: dict) -> list[dict]:
    return [beat['plan'] for beat in story['beats'].values() if beat.get('via') == 'plan']


def fits(connection, companion: dict, story: dict, today: date, now: datetime) -> list[tuple]:
    """The casts this story could have today, [] when it does not fit this world: its drama level, the relationship,
    how long the two have talked, the city's era, a plan in person only where they can meet, and a visit to the
    companion's home only while the two live apart."""
    from companion.life import long_distance, moving_in
    from companion.memory import closeness
    definition = companion['version']['definition']
    if story['level'] > storylines.drama(connection):
        return []
    if 'relationships' in story and definition.get('relationship') not in story['relationships']:
        return []
    if story.get('modern') and not perception.era_modern(definition):
        return []
    if 'days_known' in story:
        first = closeness.state(connection, companion, now)['first_day']
        known = (today - date.fromisoformat(first)).days if first else 0
        if not story['days_known'][0] <= known <= story['days_known'][1]:
            return []
    if plans(story) and (long_distance.far(connection, companion) or not outings.city_data(connection, definition)):
        return []
    if story.get('apart') and moving_in.living(connection, companion):
        return []
    return casts(connection, companion, story, today)


def casts(connection, companion: dict, story: dict, today: date) -> list[tuple]:
    """Who else could be in it: () for a story between the two, else one person from the circle who is in no other
    storyline now, lives in town when the story has a plan with them, and has or has not met the user as it asks."""
    cast, timeline_id = story.get('cast'), companion['active_timeline_id']
    if cast is None:
        return [()]
    people = circle.people(connection, timeline_id)
    known = casting.facts(connection, companion, people, today)
    if cast == 'work':
        return [()] if circle.work_blocks(companion['version']['definition']) and known.companion_employed else []
    busy = {person for row in storylines.running(connection, timeline_id, today.isoformat())
            for person in decode(row['cast_ids'])}
    met = {row['person_id'] for row in many(connection, 'SELECT person_id FROM people_impressions WHERE timeline_id=? '
                                            'AND met_on IS NOT NULL', (timeline_id,))}
    together = any(plan.get('with') for plan in plans(story))
    found = []
    for row in people:
        if row['id'] in busy or (story.get('met') and (story['met'] == 'known') != (row['id'] in met)):
            continue
        if together and not circle.details_of(row).get('local', True):
            continue
        if cast in ('friend', 'family'):
            fitting = their_people.group_of(row['role']) == ('friends' if cast == 'friend' else 'family')
        else:
            fitting = casting.SINGLE[cast](row, known)
        if fitting:
            found.append((row['id'],))
    return found


def begin(row_id: str, story: dict, beat_id: str, today: date) -> list[dict]:
    """A storyline's stages the day it starts: its first beat, and the day the next one is due."""
    stages = [stage(story, beat_id, today)]
    waiting(row_id, story, stages)
    return stages


def stage(story: dict, beat_id: str, on: date) -> dict:
    """A beat as a storyline's stage. An invitation's words wait under `invite` for the day, time and place
    (`invitation`), so `share`, which every reader of storylines fills as it stands, stays empty."""
    beat = story['beats'][beat_id]
    found = {'on': on.isoformat(), 'text': beat['text'], 'share': beat.get('share', ''),
             'tone': beat.get('tone', 'mixed'), 'beat': beat_id}
    return found | {'share': '', 'invite': found['share']} if beat.get('via') == 'plan' else found


def waiting(row_id: str, story: dict, stages: list[dict]) -> None:
    """After a beat that something follows: the day the next is due, seeded. A plan is that many days ahead
    (`plan_on`, until it is booked), and what follows it comes the day after."""
    last = stages[-1]
    beat = story['beats'][last['beat']]
    if not beat.get('then'):
        return
    rng, on = random.Random(f'shared:{row_id}:{len(stages)}'), date.fromisoformat(last['on'])
    if beat.get('via') == 'plan':
        ahead = rng.randint(*beat['plan'].get('lead', LEAD))
        planned = date.fromisoformat(last['plan_on']) if last.get('outing') else on + timedelta(days=ahead)
        last['plan_on'] = planned.isoformat()
        due = planned + timedelta(days=1)
    else:
        due = on + timedelta(days=rng.randint(*beat.get('gap', GAP)))
    stages.append({'on': due.isoformat(), 'text': '', 'share': '', 'tone': '', 'pending': PENDING})


# What the user did, and what follows -------------------------------------------------------------------------------

def follow(connection, companion: dict, now: datetime) -> int:
    """Beats whose day has come: what the user did about the one before picks the next, or ends the storyline. One
    still open (a plan not over yet, a text they may still answer) waits. Returns how many beats were decided."""
    today, decided = local(companion, now).date(), 0
    for row in rows(connection, companion['active_timeline_id'], running=True):
        stages = decode(row['stages'])
        if not stages[-1].get('pending') or stages[-1]['on'] > today.isoformat():
            continue
        story = bank().get(key_of(row))
        if story is None or stages[-2].get('beat') not in story['beats']:
            save(connection, row, stages[:-1])  # A story no longer in the bank ends where it stood.
            continue
        response = respond(connection, companion, row, len(stages) - 2, story, now)
        if response is None:
            continue
        stages[-2]['response'] = response
        met(connection, companion, row, stages[-2], story, response, now)
        stages.pop()
        found = next_beat(connection, companion, row, len(stages), story, stages[-1], response, today, now)
        if found:
            stages.append(found)
            waiting(row['id'], story, stages)
            effects(connection, companion, row, story['beats'][found['beat']], today, now)
            decided += 1
        save(connection, row, stages)
    return decided


def trigger_key(row: dict, index: int) -> str:
    return f"storyline:{row['id']}:{index}"


def moment(companion: dict, row: dict, index: int, found: dict) -> datetime:
    """When a beat happened, as a time."""
    schedule = storylines.Timing(routine.blocks(companion['version']['definition'])[0], {})
    at = storylines.beat_at(row, index, found, schedule)
    return datetime.combine(date.fromisoformat(found['on']), time(int(at[:2]), int(at[3:])),
                            zone(companion['version']['timezone']))


def respond(connection, companion: dict, row: dict, index: int, story: dict, now: datetime) -> str | None:
    """What the user did about a beat, as far as the app can tell for sure, in the words the bank's `then` uses;
    None while it is still open."""
    found = decode(row['stages'])[index]
    beat = story['beats'][found['beat']]
    if beat.get('via') == 'plan':
        return plan_response(connection, companion, found, now)
    then = beat.get('then') or {}
    opener = optional(connection, 'SELECT o.created_at, m.seq FROM openers o JOIN messages m ON m.id=o.message_id '
                      'WHERE o.timeline_id=? AND o.trigger_key=?', (row['timeline_id'], trigger_key(row, index)))
    since = parse(opener['created_at']) if opener else moment(companion, row, index, found)
    if 'dropped_by' in then and optional(
            connection, f"SELECT id FROM drop_bys WHERE timeline_id=? AND created_at>=? AND result IN "  # noqa: S608
            f"({','.join('?' * len(DROPPED_IN))})", (row['timeline_id'], stamp(since), *DROPPED_IN)):
        return 'dropped_by'
    reply = opener and optional(connection, "SELECT text FROM messages WHERE timeline_id=? AND role='user' AND "
                                "status='complete' AND active=1 AND seq>? ORDER BY seq LIMIT 1",
                                (row['timeline_id'], opener['seq']))
    if reply:
        said = {'yes': 'said_yes', 'no': 'said_no', 'not_yet': 'said_no'}.get(steps.answer(reply['text']))
        return said if said in then else 'answered'
    return 'passed' if now - since >= WINDOW else None


def plan_response(connection, companion: dict, found: dict, now: datetime) -> str | None:
    """'went' once the plan is over, 'called_off', 'passed' when the invitation never went out; None while the plan
    is still ahead or under way."""
    outing = optional(connection, 'SELECT * FROM outings WHERE id=?', (found.get('outing') or '',))
    if outing is None:
        return 'passed'
    state = outings.state(outings.view(outing), companion['version']['timezone'], now)
    return {'done': 'went', 'cancelled': 'called_off'}.get(state)


def next_beat(connection, companion: dict, row: dict, index: int, story: dict, last: dict, response: str,
              today: date, now: datetime) -> dict | None:
    """The beat that follows `last` given what the user did, as a stage on `today`; None when the storyline is over."""
    then = story['beats'][last['beat']].get('then') or {}
    found = then.get(response, then.get('any'))
    if found is None:
        return None
    if isinstance(found, str):
        return stage(story, found, today)
    if 'impression' in found:  # By what the person they met makes of the user (their_people.impress).
        cast = decode(row['cast_ids'])
        made = optional(connection, 'SELECT impression FROM people_impressions WHERE timeline_id=? AND person_id=?',
                        (row['timeline_id'], cast[0] if cast else ''))
        ways = found['impression']
        return stage(story, ways.get(made['impression'] if made else '', ways['any']), today)
    outcome = decide(connection, companion, row, index, found['choice'], today, now)
    return stage(story, found['beats'][outcome['picked']], today) | {'consequence': outcome['id']}


def decide(connection, companion: dict, row: dict, index: int, choice: str, today: date, now: datetime) -> dict:
    names = cast_names(connection, companion, row)
    return consequences.decide(
        connection, timeline_id=row['timeline_id'], choice=choice, subject=subject(row['id'], index),
        facts=facts(connection, companion, row, now), names=names,
        labels=[option['label'].format(**names) for option in consequences.tables()[choice]['options']],
        day=today.isoformat(), timestamp=stamp(now), holders=storylines.holders(companion, row), now=now)


def subject(row_id: str, index: int) -> str:
    return f'shared:{row_id}:{index}'


def cast_names(connection, companion: dict, row: dict) -> dict:
    cast = decode(row['cast_ids'])
    person = optional(connection, 'SELECT name FROM circle_people WHERE id=?', (cast[0],)) if cast else None
    return {'name': their_people.first(companion['version']['definition']['name']),
            'a': their_people.first(person['name']) if person else 'someone', 'b': ''}


def facts(connection, companion: dict, row: dict, now: datetime) -> dict:
    """What the engine reads for a turning: the storyline readers (drama, the companion's own description, mood,
    money, how close they are to the cast) and, for the two of them, `closeness` (1 to 5) and `romance`."""
    from companion.memory import closeness
    return {**storylines.facts(connection, companion, row, now),
            'closeness': closeness.state(connection, companion, now)['level'],
            'romance': int(steps.ladder_of(companion['version']['definition']) == 'romance')}


def met(connection, companion: dict, row: dict, found: dict, story: dict, response: str, now: datetime) -> None:
    """A plan with someone from their circle: once it is over they have met the user; called off, the first
    impression made for the evening goes, unless they had met before."""
    plan = story['beats'][found['beat']].get('plan') or {}
    cast = decode(row['cast_ids'])
    if not plan.get('with') or not cast or not found.get('outing'):
        return
    if response == 'went':
        day = optional(connection, 'SELECT local_date FROM outings WHERE id=?', (found['outing'],))['local_date']
        connection.execute('UPDATE people_impressions SET met_on=?, checked_on=?, updated_at=? WHERE timeline_id=? '
                           'AND person_id=? AND met_on IS NULL', (day, day, stamp(now), row['timeline_id'], cast[0]))
    else:
        connection.execute('DELETE FROM people_impressions WHERE timeline_id=? AND person_id=? AND met_on IS NULL '
                           'AND meetup_id IS NULL', (row['timeline_id'], cast[0]))


def effects(connection, companion: dict, row: dict, beat: dict, today: date, now: datetime) -> None:
    """What a beat does to the person in it: their opinion of the user warms or cools a step."""
    cast = decode(row['cast_ids'])
    made = optional(connection, 'SELECT * FROM people_impressions WHERE timeline_id=? AND person_id=? AND met_on IS '
                    'NOT NULL', (row['timeline_id'], cast[0])) if cast else None
    for effect in beat.get('effect', ()):
        if made and effect in ('warmer', 'cooler'):
            warmer = effect == 'warmer'
            their_people.move(connection, made, 1 if warmer else -1, WARMER if warmer else COOLER, today.isoformat(), now)


# The texts and invitations (companion/life/openers.py) ------------------------------------------------------------

def beats_due(connection, companion: dict, now: datetime) -> list:
    """The latest beat of the storyline under way, once its time has come: a first text about it, or the invitation
    to its plan."""
    from companion.life.openers import Trigger
    if not ACTIVE or not FIRST_TEXTS or not companion.get('active_timeline_id'):
        return []
    here, definition = local(companion, now), companion['version']['definition']
    today, clock = here.date().isoformat(), here.strftime('%H:%M')
    names = storylines.names_by_id(connection, {'timeline_id': companion['active_timeline_id']})
    found = []
    for row in rows(connection, companion['active_timeline_id'], running=True):
        stages = [item for item in decode(row['stages']) if not item.get('pending')]
        index, last = len(stages) - 1, stages[-1]
        story = bank().get(key_of(row))
        if story is None or not (last['share'] or last.get('invite')) or last.get('told') or last.get('outing'):
            continue
        times = storylines.timing(connection, companion, [row])
        if not storylines.happened(last, storylines.beat_at(row, index, last, times), today, clock):
            continue
        told = storylines.fill(last['text'], row, names, definition, you=True)
        if story['beats'][last['beat']].get('via') == 'plan':
            found += invitation(connection, companion, row, index, last, story, told, names, here)
        elif last['on'] >= (here.date() - timedelta(days=1)).isoformat():
            found.append(Trigger(trigger_key(row, index), 'storyline',
                                 f'Something just happened in your life: {told} Tell the user, the way you would '
                                 'text a friend. Do not add what happens next.',
                                 storylines.fill(last['share'], row, names, definition)))
    return found


def person_of(connection, companion: dict, row: dict) -> dict | None:
    """The person in the storyline as a meet-up names them (their_people.local_people)."""
    cast = decode(row['cast_ids'])
    return next((person for person in their_people.local_people(connection, companion) if cast and
                 person['id'] == cast[0]), None)


def proposal(connection, companion: dict, row: dict, index: int, found: dict, story: dict,
             here: datetime) -> tuple | None:
    """(activity, day, at, place, person) for a beat's plan: a free time on the day it was planned for, else the
    nearest free day; None when it can't be: too late, too far apart, a rough patch, nowhere to go."""
    from companion.life import long_distance, loss, rough_patches
    plan, planned = story['beats'][found['beat']]['plan'], date.fromisoformat(found['plan_on'])
    if here.date() >= planned or long_distance.far(connection, companion) or \
            rough_patches.cool(connection, companion, here) or loss.holds_back(connection, companion, here):
        return None
    person = person_of(connection, companion, row) if plan.get('with') else None
    if plan.get('with') and person is None:
        return None
    activity = WITH[person['group']] if person else plan['activity']
    when = outings.when_free(connection, companion, {'activity': activity, 'day': planned, 'at': None, 'firm': False},
                             here)
    if not when:
        return None
    place = place_for(connection, companion, row, index, activity, *when, person)
    return (activity, *when, place, person) if place else None


def place_for(connection, companion: dict, row: dict, index: int, activity: str, day: date, at: str,
              person: dict | None) -> dict | None:
    """Where the plan is: their family's place, their own, or the companion's pick in their city for it (the same
    pick each time it is asked: seeded by the storyline and the beat)."""
    from companion.life import together
    if activity == their_people.AT_FAMILY:
        return their_people.family_place(connection, companion, [person], row['id'])
    if activity == 'visit-in':
        return together.their_place(connection, companion)
    definition = companion['version']['definition']
    data = outings.city_data(connection, definition)
    if not data:
        return None
    _cost, affordable = outings.bill(definition, activity, day)
    item = outings.pick_place(data, activity, day, at, definition, f"shared:{row['id']}:{index}", not affordable)
    return outings.place_view(item, data) if item else None


def invitation(connection, companion: dict, row: dict, index: int, found: dict, story: dict, told: str, names: dict,
               here: datetime) -> list:
    from companion.life.openers import Trigger
    made = proposal(connection, companion, row, index, found, story, here)
    if made is None:
        return []
    activity, day, at, place, person = made
    when = f'on {day:%A} {day.day} {day:%B} at {at}'
    if activity == 'visit-in':
        reason = (f'{told} You are asking the user over to your place {when}. Ask them in your own words, naming '
                  'the day and the time.')
    else:
        company = f" with your {person['role']} {their_people.first(person['name'])}" if person else ''
        thing = 'dinner' if activity == their_people.AT_FAMILY else 'drinks' if person else \
            outings.ACTIVITIES[activity][5]
        reason = (f"{told} You are asking the user along: {thing} at {place['name']}{company} {when}. Ask them in "
                  f"your own words, naming {'who will be there, ' if person else ''}the place, the day and the time.")
    values = {'{day}': day_words(day, here.date()), '{time}': their_people.clock_text(at),
              '{place}': place_words(activity, place)}
    share = found['invite']
    for key, value in values.items():
        share = share.replace(key, value.replace('{', '{{').replace('}', '}}'))
    template = storylines.fill(share, row, names, companion['version']['definition'])
    return [Trigger(trigger_key(row, index), 'shared_plan', reason, template,
                    (row['id'], str(index), activity, day.isoformat(), at, place['id'], person['id'] if person else ''))]


def place_words(activity: str, place: dict) -> str:
    """The place as the companion writes it to the user."""
    return 'my place' if activity == 'visit-in' else place['name']


def day_words(day: date, today: date) -> str:
    """'tomorrow', 'Friday', or 'next Friday' a week or more away."""
    ahead = (day - today).days
    return 'tomorrow' if ahead == 1 else f"{'next ' if ahead >= 7 else ''}{day:%A}"


def settle(connection, companion: dict, message: dict, trigger, timestamp: str) -> dict | None:
    """The invitation went out: the plan is booked to it (Today's "Out together", where the user can call it off),
    and what follows waits until the day after it."""
    from companion.life import together
    row_id, index, activity, day_text, at, place_id, person_id = trigger.sources
    row = optional(connection, "SELECT * FROM storylines WHERE id=? AND status='running'", (row_id,))
    story = bank().get(key_of(row)) if row else None
    stages = decode(row['stages']) if row else []
    index = int(index)
    if story is None or index >= len(stages) or stages[index].get('outing') or stages[index].get('pending'):
        return None
    day, now = date.fromisoformat(day_text), parse(timestamp)
    if not their_people.free_on(connection, companion, day):
        return None
    person = person_of(connection, companion, row) if person_id else None
    place = place_for(connection, companion, row, index, activity, day, at, person)
    if place is None or place['id'] != place_id or bool(person) != bool(person_id):
        return None
    cost = 0.0
    if activity not in (their_people.AT_FAMILY, 'visit-in'):
        bill, affordable = outings.bill(companion['version']['definition'], activity, day)
        cost = bill if affordable else round(bill * 0.6, 2)
    if person:
        knows = optional(connection, 'SELECT id FROM people_impressions WHERE timeline_id=? AND person_id=? AND '
                         'met_on IS NOT NULL', (row['timeline_id'], person_id))
        place = place | {'people': [{'id': person['id'], 'name': person['name'], 'role': person['role']}],
                         'first': knows is None}
        their_people.impress(connection, companion, person, None, now)
    outing = together.insert(connection, companion, message['id'], activity, place | {'storyline': row_id}, day, at,
                             outings.until(at, activity), None, timestamp)
    # With their people there is no photo: the image model can't place the user at the table (images/prompts.py).
    connection.execute('UPDATE outings SET cost=?, photo_tried=? WHERE id=?', (cost, int(bool(person)), outing['id']))
    stages[index] |= {'outing': outing['id'], 'plan_on': day_text}
    if stages[-1].get('pending'):
        stages[-1]['on'] = max(stages[-1]['on'], (day + timedelta(days=1)).isoformat())
    save(connection, row, stages)
    return outings.get(connection, outing['id'])


# The plan they kept without the user (companion/life/agenda.py) ---------------------------------------------------

def kept_beat(story: dict, found: dict, outing: dict | None, today: str) -> str | None:
    """The beat in which the companion keeps a plan the user is not coming to (the bank's `kept`), as soon as that is
    sure: the plan was called off, or its day has come and the invitation never went out. None for any other."""
    response = found.get('response')
    if not response and outing:
        response = 'called_off' if outing['status'] == 'cancelled' else None
    elif not response:
        response = 'passed' if found['plan_on'] <= today else None
    then = story['beats'][found['beat']].get('then') or {}
    after = then.get(response, then.get('any')) if response and response != 'went' else None
    return after if isinstance(after, str) and story['beats'][after].get('kept') else None


def as_plans(connection, companion: dict, since: str, now: datetime) -> dict[str, list[dict]]:
    """The plans the companion keeps without the user, by local date in the shape own_plans.assign takes. The beat
    that says so ("went for drinks with Nancy without you") comes the morning after; until v1.5.0 nothing held the
    evening itself, so their day showed a night in and the chat said so (A/B of 2026-11-18: 3 to 10 of 30 replies).
    It takes the time the plan was booked for, or the activity's usual time when the invitation never went out."""
    today, result = local(companion, now).date().isoformat(), {}
    for row in rows(connection, companion['active_timeline_id'], running=True):
        story = bank().get(key_of(row))
        for index, found in enumerate(decode(row['stages']) if story else []):
            beat = story['beats'].get(found.get('beat')) or {}
            if beat.get('via') != 'plan' or found.get('plan_on', '') < since:
                continue
            outing = optional(connection, 'SELECT * FROM outings WHERE id=?', (found.get('outing') or '',))
            after = kept_beat(story, found, outing, today)
            if after is None:
                continue
            shown = outings.view(outing) if outing else None
            person = person_of(connection, companion, row) if beat['plan'].get('with') else None
            activity = WITH_ACTIVITY[person['group']] if person else beat['plan']['activity']
            result.setdefault(found['plan_on'], []).append({
                'id': f"shared:{row['id']}:{index}:{after}",
                'at_time': shown['at_time'] if shown else outings.ACTIVITIES[activity][2],
                'kept': {'id': row['id'], 'beat': index, 'activity': activity, 'place': shown and shown['place'],
                         'with': person and {'id': person['id'], 'name': person['name']},
                         'summary': storylines.fill(story['beats'][after]['kept'], row, storylines.names_by_id(
                             connection, {'timeline_id': row['timeline_id']}), companion['version']['definition'])}})
    return result


def entry(plan: dict, block: dict, definition: dict) -> dict:
    """The agenda entry for the slot a kept plan takes: the companion there, without the user. With someone from
    their circle it names them, so that person's day holds the same evening (companion/life/joint.py). No post of
    its own: the first text about it comes the morning after."""
    kept = plan['kept']
    place = kept['place'] if kept['place'] and kept['place'].get('kind') not in HOMES else None
    return {'summary': kept['summary'], 'post': None, 'mood': 'content', 'activity': kept['activity'],
            'place': place and {key: place.get(key) for key in ('id', 'name', 'kind', 'city', 'neighborhood')},
            'with': kept['with'], 'weather': block.get('weather'),
            'storyline': {'id': kept['id'], 'beat': kept['beat']}, 'composer_version': 'shared-kept-1'}


# The chat context (companion/memory/context.py) -------------------------------------------------------------------

# Its own section of the context: the other storylines' heading says "these happened to you and your people, never
# to the user", which is not true of these. A/B of 2026-11-18 (three rounds, 1,800 replies, 10 models): told among
# the others, in this section, and in this section with each beat's day all read the same within the noise, and no
# reply in any arm pressed the user or told them their own part as news. This wording is kept for being true.
HEADING = ('What is going on that the user is part of (decided, and the user lived their part of it: never contradict '
           'it and never tell them their own part as news; never make up what comes next or how it ends; never press '
           'them to answer or to come, and never hold it against them when they did not)')
# The user's part in the latest beat, told to the companion, by what the app can tell for sure (`respond`). None
# is a beat still open: the text or the invitation is out and nothing has come of it yet.
TEXT_PART = {None: 'You texted the user about it, and they have not written back yet.',
             'answered': 'The user knows about it.', 'said_yes': 'The user said yes.',
             'said_no': 'The user said no.', 'dropped_by': 'The user came by after you told them.',
             'passed': 'The user did not write back about it.'}
PLAN_PART = {'went': 'The user came.', 'called_off': 'The user called it off.',
             'passed': 'In the end you never asked the user.'}
UNTOLD = 'You have not told the user yet.'
UNASKED = 'You have not asked the user yet.'
OPEN = 'What comes next is not decided yet.'


def context_lines(connection, companion: dict, now: datetime) -> list[tuple[str, str]]:
    """The storylines the user is part of, told to the companion: each beat with its day, the user's part in the
    latest one (`part`) and whether more is to come. One stays as long as any storyline does
    (storylines.context_lines): told in full while recent, by its outcome once settled."""
    today = local(companion, now).date()
    recent, pinned = ((today - timedelta(days=days)).isoformat()
                      for days in (storylines.RECENT_DAYS, storylines.SETTLED_DAYS))
    kept = {row['id']: row for row in rows(connection, companion['active_timeline_id'])}
    result = []
    for item in storylines.visible(connection, companion, now, you=True):
        if not item['with_you']:
            continue
        last, row = item['beats'][-1], kept[item['id']]
        if last['on'] >= recent:
            told = [f"on {outings.day_text(day)}: {beat['text']}"
                    for day, beat in zip(days(row), item['beats'], strict=False)]
            tail = part(connection, companion, row, len(told) - 1, now)
            result.append((item['id'], f"- O{' Then, '.join(told)[1:]}{tail}"))
        elif not item['unfolding'] and last['on'] >= pinned:
            result.append((item['id'], f"- Settled on {last['on']}: {last['text']}"))
    return result


def days(row: dict) -> list[str]:
    """The day each beat tells of: its own, or for one that says how a plan went, the day of the plan (the beat
    itself comes the morning after, and "went for drinks" read as that day's)."""
    found, before = [], {}
    for item in decode(row['stages']):
        found.append(before.get('plan_on') or item['on'])
        before = item
    return found


def part(connection, companion: dict, row: dict, index: int, now: datetime) -> str:
    """What the user did about a storyline's latest beat, and that more is to come; '' once it is over, when its
    last beat says how it went."""
    found, story = decode(row['stages'])[index], bank().get(key_of(row))
    beat = story['beats'].get(found.get('beat')) if story else None
    if not beat or not beat.get('then') or row['status'] != 'running':
        return ''
    if beat.get('via') == 'plan':
        said = plan_part(connection, companion, found, now)
    else:
        sent = optional(connection, 'SELECT id FROM openers WHERE timeline_id=? AND trigger_key=?',
                        (row['timeline_id'], trigger_key(row, index)))
        response = found.get('response') or respond(connection, companion, row, index, story, now)
        said = TEXT_PART[response] if sent or response else UNTOLD
    return f' {said} {OPEN}'


def plan_part(connection, companion: dict, found: dict, now: datetime) -> str:
    """An invitation's state: not out yet, set for a day (Today's "Out together" has the place), under way, or how
    it went."""
    response = found.get('response')
    outing = optional(connection, 'SELECT * FROM outings WHERE id=?', (found.get('outing') or '',))
    if response or outing is None:
        return PLAN_PART[response] if response else UNASKED
    shown = outings.view(outing)
    state = outings.state(shown, companion['version']['timezone'], now)
    if state == 'planned':
        return (f"You asked the user, and it is set for {outings.day_text(shown['local_date'])} at "
                f"{shown['at_time']}; it has not happened yet.")
    return {'now': 'It is happening now.', 'done': PLAN_PART['went'], 'cancelled': PLAN_PART['called_off']}[state]


# The screens (Today and the scrapbook) ----------------------------------------------------------------------------

# A finished one stays on Today this many days after its last beat; after that the scrapbook keeps it (`kept`).
STAYS = 7
KEPT_TITLE = 'Things you were part of'


def on_today(connection, companion: dict, items: list[dict], now: datetime) -> list[dict]:
    """Today's storylines (storylines.listing) with the ones the user is part of made ready for their own section:
    each beat says how it reached them (`via`) and what they did about it (`you`), and a finished one leaves
    `STAYS` days after its last beat."""
    since = (local(companion, now).date() - timedelta(days=STAYS)).isoformat()
    kept = {row['id']: row for row in rows(connection, companion['active_timeline_id'])}
    found = []
    for item in items:
        row = kept.get(item['id']) if item['with_you'] else None
        if row is None:
            found.append(item)
        elif item['unfolding'] or item['beats'][-1]['on'] >= since:
            story = bank().get(key_of(row))
            name = companion['version']['definition']['name']
            found.append(item | {'beats': [beat | {'text': first_name(beat['text'], name)}
                                           | your_part(connection, companion, row, index, story, now)
                                           for index, beat in enumerate(item['beats'])]})
    return found


def first_name(text: str, name: str) -> str:
    """A beat as these screens tell it: the companion by first name (Iris, 2026-11-18)."""
    return text.replace(name, their_people.first(name)) if name else text


def named_once(text: str, name: str) -> str:
    """A scrapbook entry names the companion once, by first name; after that "the two of you", "together" and
    "their" stand in where they read right, and the first name stays where they would not."""
    first = their_people.first(name)
    text = first_name(text, name)
    at = text.find(first)
    if at < 0:
        return text
    head, rest = text[:at + len(first)], text[at + len(first):]
    known = re.escape(first)
    for pattern, words in ((rf'\bYou and {known}\b(?!\'s)', 'The two of you'), (rf'\byou and {known}\b(?!\'s)', 'the two of you'),
                           (rf'\bwith {known}\b(?!\'s)', 'together'), (rf"\b{known}'s", 'their')):
        rest = re.sub(pattern, words, rest)
    return head + rest


def your_part(connection, companion: dict, row: dict, index: int, story: dict | None, now: datetime) -> dict:
    """A beat's `via` (text or plan) and `you`: what the user did about it as far as the app can tell for sure, in
    the bank's words (`respond`), or where it stands: 'texted' (the text is out and still open), 'set' (the plan is
    booked, with its day and time), 'now' (the plan is under way). No `you` for a beat nothing follows, or one that
    has not reached the user yet."""
    found = decode(row['stages'])[index]
    beat = story['beats'].get(found.get('beat')) if story else None
    if not beat:
        return {}
    via = {'via': beat.get('via', 'text')}
    if not beat.get('then'):
        return via
    if beat.get('via') == 'plan':
        return via | plan_you(connection, companion, found, now)
    sent = optional(connection, 'SELECT id FROM openers WHERE timeline_id=? AND trigger_key=?',
                    (row['timeline_id'], trigger_key(row, index)))
    did = found.get('response') or (respond(connection, companion, row, index, story, now)
                                    if row['status'] == 'running' else None)
    did = did or ('texted' if sent else None)
    return via | ({'you': {'did': did}} if did else {})


def plan_you(connection, companion: dict, found: dict, now: datetime) -> dict:
    outing = optional(connection, 'SELECT * FROM outings WHERE id=?', (found.get('outing') or '',))
    if found.get('response'):
        return {'you': {'did': found['response']}}
    if outing is None:
        return {}
    shown = outings.view(outing)
    state = outings.state(shown, companion['version']['timezone'], now)
    if state == 'planned':
        return {'you': {'did': 'set', 'on': shown['local_date'], 'at': shown['at_time']}}
    return {'you': {'did': {'now': 'now', 'done': 'went', 'cancelled': 'called_off'}[state]}}


# The user's part in a beat as the scrapbook says it, where it turned the story (`turned`).
DID = {'answered': 'You wrote back.', 'said_yes': 'You said yes.', 'said_no': 'You said no.',
       'dropped_by': 'You came by.'}
LET_GO = 'You let it go by.'


def scrapbook_page(connection, companion: dict, low: str, high: str, now: datetime) -> dict | None:
    """The scrapbook's page of the storylines the user was part of that began in this stretch and have run their
    course: one entry each, from the day it began to its last beat, told beat by beat with the user's part where it
    turned the story. One the user ended is not kept, and one still unfolding waits until it is over."""
    kept = {row['id']: row for row in rows(connection, companion['active_timeline_id'])}
    items = []
    for item in storylines.visible(connection, companion, now, shown=True):
        if not item['with_you'] or item['unfolding'] or not low <= item['started_on'] <= high:
            continue
        row, told = kept[item['id']], []
        for found, beat in zip(decode(row['stages']), item['beats'], strict=False):
            told += [beat['text'], turned(bank().get(key_of(row)), found)]
        items.append({'date': item['started_on'], 'until': item['beats'][-1]['on'],
                      'text': named_once(' '.join(part for part in told if part),
                                         companion['version']['definition']['name'])})
    if not items:
        return None
    return {'kind': 'with-you', 'title': KEPT_TITLE, 'items': sorted(items, key=lambda item: item['date'])}


def turned(story: dict | None, found: dict) -> str:
    """What the user did about a text, when the story has a way of its own for it ('' when whatever they did led to
    the same place). A plan needs no line: the beat after it says whether they came."""
    beat = story['beats'].get(found.get('beat')) if story else None
    response = found.get('response')
    if not beat or beat.get('via') == 'plan' or response not in (beat.get('then') or {}):
        return ''
    return LET_GO if response == 'passed' else DID[response]


# Changing how it went, and forks ----------------------------------------------------------------------------------

def change(connection, companion: dict, consequence_id: str, option: int, now: datetime) -> dict:
    """The user makes a turning go another way: the storyline takes that beat instead, while nothing has followed
    it yet."""
    found = consequences.by_id(connection, consequence_id)
    row_id, index = found['subject'].removeprefix('shared:').rsplit(':', 1)
    row = optional(connection, 'SELECT * FROM storylines WHERE id=?', (row_id,))
    require(row is not None and row['timeline_id'] == companion['active_timeline_id'],
            'That outcome is not on this timeline.', 404)
    stages, index, story = decode(row['stages']), int(index), bank().get(key_of(row))
    last = len([item for item in stages if not item.get('pending')]) - 1
    require(story is not None and row['status'] == 'running' and index == last,
            'What came after it has already happened.', 409)
    then = story['beats'][stages[index - 1]['beat']]['then']
    ways = then.get(stages[index - 1].get('response'), then.get('any'))
    outcome = consequences.redo(connection, consequence_id, option, now, local(companion, now).date(),
                                storylines.holders(companion, row), cast_names(connection, companion, row))
    stages = stages[:index] + [stage(story, ways['beats'][option], date.fromisoformat(stages[index]['on']))
                               | {'consequence': consequence_id}]
    waiting(row['id'], story, stages)
    save(connection, row, stages)
    return outcome


def fork_stages(connection, row: dict, copy_id: str, timeline_id: str, cutoff: str) -> list[dict]:
    """A storyline's stages for a new timeline's copy (companion/timelines.py): the beats that had happened by the
    fork, with their outcomes; what follows is the copy's own, from what the user does there."""
    stages = [item for item in decode(row['stages']) if not item.get('pending') and item['on'] <= cutoff]
    for index, item in enumerate(stages):
        if item.get('consequence'):
            stages[index] = {**item, 'consequence': consequences.copy(connection, item['consequence'], timeline_id,
                                                                      subject(copy_id, index))}
    story = bank().get(key_of(row))
    if story and stages and stages[-1].get('beat') in story['beats']:
        waiting(copy_id, story, stages)
        if stages[-1].get('pending'):
            stages[-1]['on'] = max(stages[-1]['on'], (date.fromisoformat(cutoff) + timedelta(days=1)).isoformat())
    return stages
