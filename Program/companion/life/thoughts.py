"""On her mind: one private thought a day, shown folded on Today (Feature Hit List #8).

At the end of each of the companion's days (from `EVENING` their time) the app works out what is on their mind from
what actually happened that day, all by rules: a storyline beat or a new chapter of their life, how an outcome left
them feeling, money (payday, a tight week, a surprise bill), a plan they are looking forward to, a day that went off
plan, the user's closeness reaching a new stage or simply that the two of you talked. The weightiest topic wins (a
tie goes to the day's seeded dice), a topic used on either of the two days before steps aside when there is anything
else, and a fixed template words it. The model only polishes the wording, in the background, when background
activity and model phrasing are both on; a polish that drops the name is thrown away.

A thought is written once per day and kept (`thoughts`), so the last week reads back as it was. It never appears
in chat and the companion never learns it was read. Limits: nothing a secret they keep could give away, and thoughts
about the user stay light: no reactions, and never an emotional trait the character wasn't given.
"""
import random
import re
from datetime import date, datetime, time, timedelta

from companion import consequences, secrets
from companion.clock import stamp, zone
from companion.database import decode, many, optional
from companion.life import money, storylines
from companion.life.chapters import FRESH_DAYS
from companion.memory import closeness, pairs
from companion.providers.chat import INCOMPLETE
from companion.providers.scheduling import LIFE_SYNTHESIS, BackgroundInterrupted

EVENING = time(18, 0)
WEEK = 7
# A topic used this many days before steps aside for anything else.
REPEAT_DAYS = 2
PLAN_DAYS = 3
# Storylines that are secrets (companion/secrets.py) stay out of thoughts altogether.
SECRET_STORIES = frozenset(secrets.STORY_SECRETS)
TAILS = {
    'good': ('{first} is still smiling about it.', "It made {first}'s whole day.", "{first} can't stop grinning about it."),
    'bad': ("It's weighing on {first} tonight.", "{first} can't quite shake it.", '{first} keeps going over it.'),
    'mixed': ('{first} keeps turning it over.', "{first} isn't sure what to make of it yet.",
              "It's on {first}'s mind more than expected."),
}
CHAPTER_TAILS = ('{first} is still getting used to it.', 'It still feels new to {first}.')
# Closeness with the user reaching a stage that day; kept light, whatever the relationship.
STAGES = {2: '{first} is enjoying getting to know you.', 3: 'Talking with you has started to feel easy, and {first} likes that.',
          4: '{first} was thinking about how close you two have gotten.', 5: '{first} was thinking about how far back you two go now.'}
TALKED = ('{first} is glad you two talked today.', 'Talking with you was a nice part of the day for {first}.')
QUIET = ('{first} is winding down after the day.', 'Nothing big today. {first} is enjoying the quiet.',
         "{first} is looking forward to a good night's sleep.")
PHRASING = (
    "Reword this one line about what is on {name}'s mind tonight so it reads naturally, as a quiet glimpse written "
    'by a narrator. Keep it in the third person, keep every name and fact exactly, add nothing, and keep it to one '
    'or two short sentences. Reply with the line only.'
)
LIMIT = 300
CLOCK = re.compile(r'\b\d{1,2}:\d{2}\b')


# What could be on their mind on a day ------------------------------------------------------------------
# Each finder returns (weight, topic, text) candidates for one local day.

def first_name(companion: dict) -> str:
    name = companion['version']['definition']['name']
    return name.split()[0] if name.split() else name


def pick(seed: str, options) -> str:
    return random.Random(seed).choice(options)


def beats(connection, companion, day: date, now) -> list[tuple]:
    first, found = first_name(companion), []
    for item in storylines.visible(connection, companion, now, include_ended=True):
        if item['story'] in SECRET_STORIES:
            continue
        for index, beat in enumerate(item['beats']):
            if beat['on'] == day.isoformat():
                tail = pick(f"thought:{item['id']}:{index}", TAILS.get(beat['tone'], TAILS['mixed']))
                found.append((6, f"storyline:{item['id']}:{index}", f"{beat['text']} {tail.format(first=first)}"))
    return found


def chapters(connection, companion, day: date, now) -> list[tuple]:
    rows = many(connection, 'SELECT * FROM life_chapters WHERE timeline_id=? AND undone_at IS NULL AND started_on>=? '
                'AND started_on<=?', (companion['active_timeline_id'], (day - timedelta(days=FRESH_DAYS)).isoformat(),
                                      day.isoformat()))
    first = first_name(companion)
    return [(6 if row['started_on'] == day.isoformat() else 3, f"chapter:{row['id']}",
             f"{row['title']}. {pick(row['id'], CHAPTER_TAILS).format(first=first)}") for row in rows]


def feelings(connection, companion, day: date, now) -> list[tuple]:
    """How an outcome left them, while its mood mark lasts. Marks about the user (`told`) stay out: thoughts about
    the user stay light."""
    key, first, found = pairs.companion_key(companion['id']), first_name(companion), []
    for row in consequences.active(connection, companion['active_timeline_id'], day.isoformat(), 'mood', key):
        if row['told']:
            continue
        fresh = date.fromisoformat(row['starts_on']) >= day - timedelta(days=1)
        if row['ripple']:
            holder = consequences.holder_name(connection, row['about'] or '') or 'a friend'
            text = f"{first} keeps thinking about {holder.split()[0]}: {row['note']}."
        else:
            text = f"{row['note']}."
        found.append((4 if fresh else 2, f"mark:{row['consequence_id']}", text[0].upper() + text[1:]))
    return found


def budget(connection, companion, day: date, now) -> list[tuple]:
    definition, first = companion['version']['definition'], first_name(companion)
    home = money.household(connection, companion['active_timeline_id'], definition, day)
    view = money.snapshot(definition, day.isoformat(), home)
    if not view['available']:
        return []
    found = []
    if view['surprise'] and view['surprise']['on'] == day.isoformat():
        found.append((3, 'money:surprise', f"{view['surprise']['label'][0].upper()}{view['surprise']['label'][1:]}. "
                                           f"{first} didn't see that one coming."))
    if view['splurge'] and view['splurge']['on'] == day.isoformat():
        found.append((2, 'money:splurge', f"{first} splurged on {view['splurge']['label']} and feels half thrilled, "
                                          'half guilty.'))
    if view['payday']['today']:
        found.append((2, 'money:payday', f'Payday today. {first} is feeling a little richer.'))
    elif view['tight']:
        payday = date.fromisoformat(view['payday']['next'])
        found.append((3, 'money:tight', f"Money is tight until payday on {payday:%A}, and {first} is counting every "
                                        'penny.'))
    return found


def looking_forward(connection, companion, day: date, now) -> list[tuple]:
    """A plan of their own in the next few days."""
    timezone = zone(companion['version']['timezone'])
    start, end = local_bounds(day + timedelta(days=1), timezone)[0], local_bounds(day + timedelta(days=PLAN_DAYS),
                                                                                    timezone)[1]
    rows = many(connection, "SELECT * FROM life_events WHERE timeline_id=? AND status='committed' AND kind='plan' "
                'AND starts_at>=? AND starts_at<? ORDER BY starts_at LIMIT 1',
                (companion['active_timeline_id'], stamp(start), stamp(end)))
    first = first_name(companion)
    return [(3, f"plan:{row['id']}", f"{re.sub(r'\s*\([^)]*\)', '', row['summary']).rstrip('.')}. {first} is already "
                                     'looking forward to it.') for row in rows]


def off_plan(connection, companion, day: date, now) -> list[tuple]:
    """A day that went off plan: plans falling through weigh most."""
    rows = many(connection, "SELECT id, block FROM life_agenda WHERE timeline_id=? AND subject='companion' "
                "AND local_date=? AND status='happened' ORDER BY starts_at", (companion['active_timeline_id'],
                                                                               day.isoformat()))
    weights, first, found = {'cancelled': 3, 'came_up': 2, 'drop_by': 2}, first_name(companion), []
    for row in rows:
        shift = decode(row['block']).get('shift')
        if shift and shift.get('text'):
            text = shift['text'].format(friend=(shift.get('friend') or {}).get('name', 'a friend'))
            found.append((weights.get(shift['key'], 1), f"shift:{row['id']}", f'{first} {text}.'))
    return found


def with_you(connection, companion, day: date, now) -> list[tuple]:
    """Light thoughts about the user: closeness reaching a stage that day, or that the two of you talked."""
    first, found = first_name(companion), []
    reached = [item for item in closeness.state(connection, companion, now)['history']
               if item.get('on') == day.isoformat() and item.get('kind') != 'set' and item['level'] in STAGES]
    if reached:
        level = reached[-1]['level']
        found.append((2, f'closeness:{level}', STAGES[level].format(first=first)))
    start, end = local_bounds(day, zone(companion['version']['timezone']))
    if optional(connection, "SELECT id FROM messages WHERE timeline_id=? AND role='user' AND created_at>=? "
                'AND created_at<? LIMIT 1', (companion['active_timeline_id'], stamp(start), stamp(end))):
        found.append((1, 'talked', pick(f"talked:{companion['id']}:{day}", TALKED).format(first=first)))
    return found


FINDERS = (beats, chapters, feelings, budget, looking_forward, off_plan, with_you)


def local_bounds(day: date, timezone) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time(0), timezone)
    return start, datetime.combine(day + timedelta(days=1), time(0), timezone)


def kept_quiet(connection, companion, text: str) -> bool:
    """Whether the line could give away a secret the companion keeps."""
    key = pairs.companion_key(companion['id'])
    return any(key in secret['knowers'] and secrets.hits(secret, text, key) for secret in secrets.active(connection))


def choose(connection, companion, day: date, now, recent: set[str]) -> tuple[str, str]:
    """(topic, text) for the day: the weightiest candidate, fresh topics first, ties by the day's seeded dice."""
    found = [item for finder in FINDERS for item in finder(connection, companion, day, now)
             if not kept_quiet(connection, companion, item[2])]
    fresh = [item for item in found if item[1] not in recent] or found
    if not fresh:
        return 'quiet', pick(f"quiet:{companion['id']}:{day}", QUIET).format(first=first_name(companion))
    top = max(item[0] for item in fresh)
    best = sorted(item for item in fresh if item[0] == top)
    _weight, topic, text = random.Random(f"thought:{companion['id']}:{day}").choice(best)
    return topic, text


# Writing and reading ------------------------------------------------------------------------------------

def enabled(connection) -> bool:
    row = optional(connection, 'SELECT on_her_mind FROM life_settings WHERE id=1')
    return bool(row is None or row['on_her_mind'])


def last_ready(companion, now) -> date:
    """The newest day with a thought: today once it is evening for them, otherwise yesterday."""
    local = now.astimezone(zone(companion['version']['timezone']))
    return local.date() if local.time() >= EVENING else local.date() - timedelta(days=1)


def began(connection, companion) -> date:
    row = optional(connection, 'SELECT created_at FROM timelines WHERE id=?', (companion['active_timeline_id'],))
    instant = datetime.fromisoformat(row['created_at']) if row else datetime.now().astimezone()
    return instant.astimezone(zone(companion['version']['timezone'])).date()


def catch_up(connection, companion, now) -> int:
    """Write the thoughts of the last week that are due and not written yet. Returns how many were written."""
    timeline_id, latest = companion['active_timeline_id'], last_ready(companion, now)
    day, written = max(latest - timedelta(days=WEEK - 1), began(connection, companion)), 0
    kept = {row['day']: row['topic'] for row in many(connection, 'SELECT day, topic FROM thoughts WHERE timeline_id=?',
                                                     (timeline_id,))}
    while day <= latest:
        if day.isoformat() not in kept:
            recent = {kept.get((day - timedelta(days=back)).isoformat()) for back in range(1, REPEAT_DAYS + 1)}
            topic, text = choose(connection, companion, day, now, recent - {None})
            connection.execute('INSERT OR IGNORE INTO thoughts (timeline_id, day, topic, text, created_at) '
                               'VALUES (?, ?, ?, ?, ?)', (timeline_id, day.isoformat(), topic, text, stamp(now)))
            kept[day.isoformat()], written = topic, written + 1
        day += timedelta(days=1)
    return written


def week(connection, companion, now) -> list[dict]:
    """The last week of thoughts, newest first: {day, text}."""
    since = (last_ready(companion, now) - timedelta(days=WEEK - 1)).isoformat()
    rows = many(connection, 'SELECT day, text, phrased FROM thoughts WHERE timeline_id=? AND day>=? ORDER BY day DESC',
                (companion['active_timeline_id'], since))
    return [{'day': row['day'], 'text': row['phrased'] or row['text']} for row in rows]


def view(database, companion_id: str | None = None) -> dict | None:
    """For Today: the week of thoughts, written first where due; None when switched off in Settings > Life."""
    from companion.characters import by_id, require_current
    now = database.clock.now()
    with database.connect(write=True) as connection:
        if not enabled(connection):
            return None
        companion = by_id(connection, companion_id) if companion_id else require_current(connection)
        catch_up(connection, companion, now)
        return {'thoughts': week(connection, companion, now)}


# Polishing -----------------------------------------------------------------------------------------------

def unpolished(connection) -> dict | None:
    """The newest thought still in template wording, of any companion's active timeline."""
    return optional(connection, 'SELECT t.*, c.id AS companion_id FROM thoughts t JOIN companions c '
                    'ON c.active_timeline_id=t.timeline_id WHERE t.phrased IS NULL AND t.polish_tried=0 '
                    'ORDER BY t.day DESC LIMIT 1')


def usable(text: str, first: str) -> str | None:
    text = ' '.join(text.strip().strip('"').split())
    if not text or len(text) > LIMIT or CLOCK.search(text) or first.casefold() not in text.casefold():
        return None
    return text


async def polish(provider, scheduler, config, key, row: dict, name: str) -> str | None:
    """The model's wording for one thought, or None when it is not usable (the template wording stays)."""
    pieces = []
    async with scheduler.reserve(config, LIFE_SYNTHESIS) as lease:
        async for chunk in provider.stream(config, key, PHRASING.format(name=name),
                                           [{'role': 'user', 'content': row['text']}]):
            if lease.stop.is_set():
                raise BackgroundInterrupted()
            pieces.append(chunk.text)
            if chunk.finish_reason in INCOMPLETE:
                return None
    return usable(''.join(pieces), name.split()[0] if name.split() else name)


def save_polish(connection, row: dict, text: str | None):
    connection.execute('UPDATE thoughts SET phrased=?, polish_tried=1 WHERE timeline_id=? AND day=?',
                       (text, row['timeline_id'], row['day']))
