"""Dreams: overnight, the companion's day turns into a short, odd dream (Feature Hit List #31).

Some nights (a seeded roll, a few times a week at most) rules pick fragments of the day before: people they spent
time with, a place they went, the day's small moment from the Life deck (companion/life/deck.py) and, once the two
of you are close enough, the user when you talked that day. A fixed template mixes them with an odd touch ("at
the beach, except somehow it was on a ferry"), and money pressure or a plan they look forward to adds a last line,
the same state that feeds On her mind (companion/life/thoughts.py). Rarely, someone they live with says they
talked in their sleep.

No model decides anything. The dream is told to the companion the morning after (it may come up, as a dream),
listed on Today, and can become a morning text (companion/life/openers.py) phrased by the model only when model
phrasing is allowed; otherwise the template text is used as written. A dream never gives away a secret they keep,
is never a nightmare, and uses no emotional trait they weren't given. A night is decided once (`dreams`).
"""
import json
import random
from datetime import date, datetime, time, timedelta
from functools import cache

from companion.clock import stamp, zone
from companion.database import decode, many, optional
from companion.life import circle, deck, money, storylines
from companion.memory import closeness
from companion.world import catalog

# Off in tests unless a test turns it on: a seeded dream would add context lines and first messages.
ACTIVE = True
WEEK = 7
# The user turns up in dreams from this closeness stage on (memory/closeness.py: 3 is when talking feels easy).
USER_LEVEL = 3
# A dream becomes a morning text from this stage, before noon where they live.
TEXT_LEVEL = 2
MORNING_ENDS = time(12, 0)
SLEEP_TALK = 6  # One dream night in this many, when someone lives with them.


@cache
def data() -> dict:
    return json.loads((catalog.DATA / 'dreams.json').read_text(encoding='utf-8'))


def first_name(name: str) -> str:
    return name.split()[0] if name.split() else name


# The day's fragments -------------------------------------------------------------------------------------------

def day_entries(connection, timeline_id: str, day: date) -> list[dict]:
    rows = many(connection, "SELECT entry FROM life_agenda WHERE timeline_id=? AND subject='companion' AND "
                "local_date=? AND status='happened' AND entry IS NOT NULL ORDER BY starts_at",
                (timeline_id, day.isoformat()))
    return [decode(row['entry']) for row in rows]


def person_name(connection, found: dict) -> str | None:
    row = optional(connection, "SELECT name FROM circle_people WHERE id=? AND status='active'", (found.get('id'),))
    return first_name(row['name']) if row else None


def fragments(connection, companion, day: date, now) -> dict:
    """{people: [first names], places: [names], user: bool} from the companion's day."""
    timeline_id, people, places = companion['active_timeline_id'], [], []
    for entry in day_entries(connection, timeline_id, day):
        if entry.get('place') and entry['place'].get('name') and entry['place']['name'] not in places:
            places.append(entry['place']['name'])
        if entry.get('with') and (name := person_name(connection, entry['with'])) and name not in people:
            people.append(name)
    moment = deck.on_day(connection, companion, day)
    friend = person_name(connection, {'id': moment['friend_id']}) if moment and moment.get('friend_id') else None
    if friend and friend not in people:
        people.append(friend)
    return {'people': people, 'places': places, 'user': with_user(connection, companion, day, now)}


def with_user(connection, companion, day: date, now) -> bool:
    if closeness.state(connection, companion, now)['level'] < USER_LEVEL:
        return False
    start = datetime.combine(day, time(0), zone(companion['version']['timezone']))
    return optional(connection, "SELECT id FROM messages WHERE timeline_id=? AND role='user' AND created_at>=? AND "
                    'created_at<? LIMIT 1', (companion['active_timeline_id'], stamp(start),
                                             stamp(start + timedelta(days=1)))) is not None


def mood_line(connection, companion, day: date, chooser: random.Random) -> str:
    """A last line from money pressure or a plan to look forward to, as On her mind would see them."""
    definition = companion['version']['definition']
    home = money.household(connection, companion['active_timeline_id'], definition, day)
    view = money.snapshot(definition, day.isoformat(), home)
    if view['available'] and view['tight']:
        return chooser.choice(data()['worried'])
    plans = optional(connection, "SELECT id FROM life_events WHERE timeline_id=? AND status='committed' AND kind='plan' "
                     'AND starts_at>? LIMIT 1', (companion['active_timeline_id'], stamp(
                         datetime.combine(day + timedelta(days=1), time(0), zone(companion['version']['timezone'])))))
    return chooser.choice(data()['hopeful']) if plans else ''


# Weaving a dream ---------------------------------------------------------------------------------------------

def fitting(found: dict) -> list[dict]:
    """The templates the day's fragments can fill; the user counts as a second person only."""
    people = len(found['people'])
    return [item for item in data()['templates']
            if (not item['place'] or found['places']) and
            (people >= item['people'] or (item['people'] == 2 and people == 1 and found['user']))]


def fill(template: dict, found: dict, first: str, chooser: random.Random) -> dict:
    """{text, told, share} for a template and the day's fragments."""
    people = chooser.sample(found['people'], min(len(found['people']), template['people']))
    second = people[1] if len(people) > 1 else None
    values = {'first': first, 'a': people[0] if people else '', 'place': chooser.choice(found['places'] or ['']),
              'odd': chooser.choice(data()['odd']), 'object': chooser.choice(data()['object'])}
    result = {}
    for field, user in (('text', 'you'), ('told', 'the user'), ('share', 'you')):
        result[field] = template[field].format(**values, b=second or user)
    return result


def weave(connection, companion, day: date, now) -> dict | None:
    """The night after `day`, or None when they don't dream (or remember it)."""
    timeline_id = companion['active_timeline_id']
    chooser = random.Random(f'dream:{timeline_id}:{day.isoformat()}')
    if not ACTIVE or chooser.randrange(100) >= data()['chance'] or recent_count(connection, timeline_id, day) >= \
            data()['per_week']:
        return None
    found = fragments(connection, companion, day, now)
    templates = fitting(found)
    if not templates:
        return None
    first = first_name(companion['version']['definition']['name'])
    dream = fill(chooser.choice(templates), found, first, chooser)
    if tail := mood_line(connection, companion, day, chooser):
        dream['text'] += ' ' + tail.format(first=first)
    if deck.kept_quiet(connection, companion, dream['told']):
        return None
    dream['sleep_talk'] = sleep_talker(connection, timeline_id, chooser)
    return dream


def sleep_talker(connection, timeline_id: str, chooser: random.Random) -> str | None:
    roles = set(data()['sleep_talk_roles'])
    sharing = [person for person in circle.people(connection, timeline_id) if person['role'] in roles]
    return chooser.choice(sharing)['id'] if sharing and chooser.randrange(SLEEP_TALK) == 0 else None


def recent_count(connection, timeline_id: str, day: date) -> int:
    since = (day - timedelta(days=WEEK - 1)).isoformat()
    return optional(connection, 'SELECT COUNT(*) AS n FROM dreams WHERE timeline_id=? AND night>=? AND night<? AND '
                    'text IS NOT NULL', (timeline_id, since, day.isoformat()))['n']


# Writing and reading -------------------------------------------------------------------------------------------

def catch_up(connection, companion, now) -> int:
    """Decide the nights of the last week not decided yet. A night is named by the day before it, and is decided
    once the morning comes where they live."""
    timeline_id, today = companion['active_timeline_id'], storylines.local_today(companion, now)
    kept = {row['night'] for row in many(connection, 'SELECT night FROM dreams WHERE timeline_id=? AND night>=?',
                                         (timeline_id, (today - timedelta(days=WEEK)).isoformat()))}
    day, written = max(today - timedelta(days=WEEK), deck.began(connection, companion)), 0
    while day < today:
        if day.isoformat() not in kept:
            dream = weave(connection, companion, day, now) or {}
            connection.execute('INSERT OR IGNORE INTO dreams (timeline_id, night, text, told, share, sleep_talk, '
                               'created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                               (timeline_id, day.isoformat(), dream.get('text'), dream.get('told'), dream.get('share'),
                                dream.get('sleep_talk'), stamp(now)))
            written += 1
        day += timedelta(days=1)
    return written


def sync(connection, now) -> int:
    """Catch up every companion with a life, in the world this runs in (a background tick)."""
    from companion.characters import by_id
    written = 0
    for row in many(connection, 'SELECT id FROM companions WHERE active_version_id IS NOT NULL AND '
                    'active_timeline_id IS NOT NULL'):
        if (companion := by_id(connection, row['id'])) is not None:
            written += catch_up(connection, companion, now)
    return written


def talker(connection, row, companion) -> str | None:
    """Someone they live with saying they talked in their sleep, with today's names."""
    if not row['sleep_talk']:
        return None
    found = optional(connection, "SELECT name FROM circle_people WHERE id=? AND status='active'", (row['sleep_talk'],))
    if not found:
        return None
    line = random.Random(f"sleep:{row['timeline_id']}:{row['night']}").choice(data()['sleep_talk'])
    return line.format(who=first_name(found['name']), first=first_name(companion['version']['definition']['name']),
                       object=random.Random(row['night']).choice(data()['object']))


def week(connection, companion, now) -> list[dict]:
    """The last week's dreams, newest first: {day (the morning after), text, sleep_talk}."""
    since = (storylines.local_today(companion, now) - timedelta(days=WEEK)).isoformat()
    rows = many(connection, 'SELECT * FROM dreams WHERE timeline_id=? AND night>=? AND text IS NOT NULL '
                'ORDER BY night DESC', (companion['active_timeline_id'], since))
    return [{'day': (date.fromisoformat(row['night']) + timedelta(days=1)).isoformat(), 'text': row['text'],
             'sleep_talk': talker(connection, row, companion)} for row in rows]


def last_night(connection, companion, now):
    night = (storylines.local_today(companion, now) - timedelta(days=1)).isoformat()
    return optional(connection, 'SELECT * FROM dreams WHERE timeline_id=? AND night=? AND text IS NOT NULL',
                    (companion['active_timeline_id'], night))


def context_lines(connection, companion, now) -> list[tuple[str, str]]:
    """Last night's dream, for the chat context the day after."""
    row = last_night(connection, companion, now)
    if row is None:
        return []
    lines = [(f"dream:{row['night']}", f"- {row['told']}")]
    if row['sleep_talk'] and (found := optional(connection, "SELECT name FROM circle_people WHERE id=? AND "
                                                "status='active'", (row['sleep_talk'],))):
        lines.append((f"sleep:{row['night']}", '- ' + data()['sleep_talk_told'].format(who=first_name(found['name']))))
    return lines


def fresh(connection, companion, now) -> list[dict]:
    """Last night's dream as a morning text: before noon where they live, once you are past strangers."""
    row = last_night(connection, companion, now)
    local = now.astimezone(zone(companion['version']['timezone'])).time()
    if row is None or not row['share'] or local >= MORNING_ENDS or \
            closeness.state(connection, companion, now)['level'] < TEXT_LEVEL:
        return []
    return [{'key': f"dream:{row['night']}", 'told': row['told'], 'share': row['share']}]


def view(database) -> list[dict]:
    """For Today: the last week's dreams, decided first where due."""
    from companion.characters import require_current
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        catch_up(connection, companion, now)
        return week(connection, companion, now)
