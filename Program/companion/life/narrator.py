"""The Watching page's narrator (Observer mode, companion/observer.py): one person's days told in close third person.

Nothing new happens here. The narrator reads what the world already decided and retells it as short lines, newest
day first, over the last week:

- a companion: their day as it went (`life_events`), the Life deck's small moments (companion/life/deck.py), dreams
  (companion/life/dreams.py), On their mind (companion/life/thoughts.py), storyline beats
  (companion/life/storylines.py), new chapters of their life (companion/life/chapters.py) and news they heard
  (companion/news.py), with how they feel now (companion/moods.py);
- a townsperson: where the town's rules put them through the day and how their goal is going
  (companion/world/townsfolk.py), and the companions who ran into them (`townsfolk_encounters`);
- someone in a companion's circle who lives in town (companion/life/circle.py): their days as their agenda went
  (`life_agenda`), the same days the companion's own can name them in.

Inner voice (Settings > Realism > Their days, `life_settings.inner_voice`) sets how much of what is on their mind the
lines carry: 0 just what happened; 1 a few thoughts (On their mind, what a townsperson is working toward); 2 true to
life (how they feel, and a thought after what stood out); 3 everything on their mind (a thought after every line, and
passing ones). Those thoughts come from fixed banks (world/data/inner_voice.json), picked by seeded dice, so a day
reads the same every time.

Hidden values follow the user's switches: by default feelings come through in words only; with moods shown the mood
also says its strength, and with odds shown a moment says how likely it was. With model phrasing and background
activity on, the model also writes the day before in a few lines (`observer_entries`, from these lines only).

Quiet limits: a line that reads as intimate is never told. With the adult side of life on it becomes a line that the
rest stayed private, unless anyone in it could be a child, when it is left out like everything else the check cannot
clear. A line the check fails on is left out too.
"""
import json
import random
import re
from datetime import date, datetime, time, timedelta
from functools import cache
from pathlib import Path

from companion import moods, observer
from companion.characters import by_id, current
from companion.clock import parse, stamp, zone
from companion.database import decode, many, optional, settings
from companion.images import content
from companion.life import narrator_love
from companion.providers.chat import INCOMPLETE
from companion.providers.scheduling import LIFE_SYNTHESIS, BackgroundInterrupted

DAYS = 7
USUAL_VOICE = 2
# Local times the narrator places day-long things at: a dream on waking, a small moment at midday, the day's
# thought in the evening (On their mind is written from 18:00, companion/life/thoughts.py).
WAKING, MIDDAY, AFTERNOON, EVENING = time(7, 30), time(12, 0), time(15, 30), time(21, 0)
# A townsperson's day, looked in on at these local times.
LOOKS = ((time(8, 30), 'morning'), (time(13, 0), 'afternoon'), (time(19, 30), 'evening'))
GOOD = frozenset({'happy', 'content', 'excited', 'proud', 'pleased', 'cheerful', 'warm', 'refreshed', 'satisfied',
                  'relaxed', 'calm', 'productive', 'social', 'upbeat', 'over the moon', 'good'})
BAD = frozenset({'sad', 'heartbroken', 'tired', 'unimpressed', 'restless', 'frustrated', 'down', 'anxious',
                 'annoyed', 'hurt', 'angry', 'bad', 'stressed', 'lonely', 'worried'})
# How a feeling comes through in words (companion/moods.py FEELINGS), from mild to strong.
FEELING_WORDS = {
    'calm': ('{first} feels calm.', '{first} feels properly at peace.', '{first} feels completely at ease.'),
    'happy': ('{first} is in a good mood.', '{first} is properly happy.', '{first} is over the moon.'),
    'excited': ('{first} has a buzz of excitement.', "{first} can hardly sit still.", "{first} is fizzing with it."),
    'annoyed': ('{first} is a little irritated.', '{first} is fed up.', "{first}'s patience is gone."),
    'hurt': ('{first} feels a little bruised.', '{first} is hurt.', '{first} is badly hurt.'),
    'angry': ('{first} is cross.', '{first} is angry.', '{first} is furious.'),
    'anxious': ('{first} feels uneasy.', '{first} is anxious.', "{first}'s nerves are frayed."),
    'sad': ('{first} feels a bit low.', '{first} is sad.', '{first} is heartsick.'),
}
ABOUT = {
    'happy': "{first} can't stop thinking about {other}.", 'excited': "{first} can't stop thinking about {other}.",
    'calm': '{first} feels easy around {other}.', 'annoyed': '{other} is getting on {first}\'s nerves.',
    'hurt': '{first} is still smarting over {other}.', 'angry': '{first} is angry with {other}.',
    'anxious': '{first} keeps worrying about {other}.', 'sad': '{first} misses how things were with {other}.',
}
# What the image check (companion/images/content.py) reads as intimate, plus words it only finds uncertain.
INTIMATE = frozenset({'sexual', 'sexual_violence', 'nudity'})
CLOSE = re.compile(r'\b(?:lingerie|underwear|sensual\w*|seduc\w*|steamy|intimate|in bed together|between the sheets|'
                   r'spent the night|made love|hook(?:ed)? up)\b')
PRIVATE = '{first} kept the rest of that to {self}.'
SELF = {'she': 'herself', 'he': 'himself'}
# The day in a few lines, by the model (background, with model phrasing and background activity on).
ENTRY = (
    "Write the day these lines tell for {name}, as a narrator would: two or three short sentences in the third person, "
    'past tense. Use only what the lines say: keep every name and fact, add no people, places, events or feelings, '
    'and leave out anything about the user. When not using their name, call {name} {pronouns}. '
    'Reply with the sentences only.'
)
ENTRY_LIMIT = 500
CLOCK = re.compile(r'\b\d{1,2}:\d{2}\b')


@cache
def bank() -> dict:
    return json.loads((Path(__file__).parents[1] / 'world' / 'data' / 'inner_voice.json').read_text(encoding='utf-8'))


def town_zone(data: dict) -> str:
    return data.get('timezone') or 'UTC'


def first_name(name: str) -> str:
    return name.split()[0] if name and name.split() else name or 'They'


def tone(word: str | None) -> str:
    """Which bank a thought comes from: a tone as storylines and the Life deck give it, or a mood word."""
    word = (word or '').casefold()
    if word in ('good', 'bad', 'mixed'):
        return word
    return 'good' if word in GOOD else 'bad' if word in BAD else 'mixed' if word == 'odd' else 'calm'


def pick(category: str, seed: str) -> str:
    return random.Random(seed).choice(bank()[category])


def voice_level(connection) -> int:
    row = optional(connection, 'SELECT inner_voice FROM life_settings WHERE id=1')
    return row['inner_voice'] if row and row['inner_voice'] in range(4) else USUAL_VOICE


def at(day: date, moment: time, timezone: str) -> str:
    return stamp(datetime.combine(day, moment, tzinfo=zone(timezone)))


def item(key: str, when: str, kind: str, text: str, **extra) -> dict:
    return {'id': key, 'at': when, 'kind': kind, 'text': text, 'inner': extra.get('inner'),
            'numbers': extra.get('numbers') or []}


# Telling it safely ---------------------------------------------------------------------------------------------------

def reads(text: str) -> set[str] | None:
    """What the check finds in a line, or None when it could not be checked."""
    if not isinstance(text, str):
        return None
    try:
        normal = content.normalize(text)
        return content.matches(normal) | ({'close'} if CLOSE.search(normal) else set())
    except Exception:  # noqa: BLE001 - a line that cannot be checked is not told.
        return None


def told(entry: dict, first: str, pronoun: str, adult_side: bool, young: re.Pattern | None = None) -> dict | None:
    """The line as the page may show it: intimate lines never are, and fail closed (see the module notes)."""
    found = reads(entry['text'])
    inner = reads(entry['inner']) if entry.get('inner') else set()
    if found is None or inner is None:
        return None
    found |= inner
    if young and young.search(f"{entry['text']} {entry.get('inner') or ''}"):
        found.add('minor')
    if not found & (INTIMATE | {'close'}):
        return entry
    if adult_side and 'minor' not in found:
        return {**entry, 'kind': 'private', 'inner': None, 'numbers': [],
                'text': PRIVATE.format(first=first, self=SELF.get(pronoun, 'themselves'))}
    return None


def named_young(connection) -> re.Pattern | None:
    """The names of the children in anyone's circle (companion/life/families.py)."""
    from companion.life import families
    found = sorted(families.every_name(connection))
    return re.compile('|'.join(rf'\b{re.escape(name)}\b' for name in found)) if found else None


def safe(connection, entries: list[dict], first: str, pronoun: str) -> list[dict]:
    adult_side, young = bool(settings(connection)['adult_side']), named_young(connection)
    kept = [told(entry, first, pronoun, adult_side, young) for entry in entries]
    return [entry for entry in kept if entry is not None]


# A companion's days --------------------------------------------------------------------------------------------------

def thought_after(voice: int, notable: bool, key: str, feeling: str | None, first: str) -> str | None:
    """A thought after a line: after what stood out and stirred a feeling on true to life (2), after every line on
    everything (3)."""
    kind = tone(feeling)
    if voice >= 3 or voice == 2 and notable and kind != 'calm':
        return pick(kind, key).format(first=first)
    return None


def notable_events(rows: list[dict]) -> set[str]:
    """One ordinary event a day stands out to the narrator, picked by seeded dice."""
    days: dict[str, list[str]] = {}
    for row in rows:
        days.setdefault(row['starts_at'][:10], []).append(row['id'])
    return {min(ids, key=lambda found: random.Random(found).random()) for ids in days.values()}


def day_events(connection, companion, since: str, now, voice: int, first: str) -> list[dict]:
    from companion.life.composer import said
    rows = many(connection, "SELECT * FROM life_events WHERE timeline_id=? AND status='committed' AND kind!='plan' "
                'AND starts_at>=? AND starts_at<=? ORDER BY starts_at', (companion['active_timeline_id'], since,
                                                                        stamp(now)))
    standing = notable_events(rows)
    definition = companion['version']['definition']
    result = []
    for row in rows:
        mood = decode(row['details']).get('mood')
        inner = thought_after(voice, row['id'] in standing, f"event:{row['id']}", mood, first)
        text = said(row['summary'], definition).replace(definition['name'], first)
        result.append(item(f"event:{row['id']}", row['starts_at'], 'day', text, inner=inner))
    return result


def moments(connection, companion, now, voice: int, odds: bool, first: str) -> list[dict]:
    from companion.life import deck
    deck.catch_up(connection, companion, now)
    timezone = companion['version']['timezone']
    tones = {card['title']: card.get('tone') for card in deck.cards()}
    return [item(f"moment:{found['day']}", at(date.fromisoformat(found['day']), MIDDAY, timezone), 'moment',
                 found['text'], inner=thought_after(voice, True, f"moment:{found['day']}", tones.get(found['title']),
                                                    first),
                 numbers=[f"{round(found['odds'] * 100)}% likely"] if odds and found.get('odds') is not None else [])
            for found in deck.week(connection, companion, now, odds=odds)]


def dreamed(connection, companion, now, voice: int) -> list[dict]:
    """Dreams are their inner world: told from a few thoughts (1) on."""
    from companion.life import dreams
    if voice < 1:
        return []
    dreams.catch_up(connection, companion, now)
    timezone = companion['version']['timezone']
    return [item(f"dream:{found['day']}", at(date.fromisoformat(found['day']), WAKING, timezone), 'dream',
                 found['text'], inner=found['sleep_talk'])
            for found in dreams.week(connection, companion, now)]


def on_their_mind(connection, companion, now, voice: int) -> list[dict]:
    from companion.life import thoughts
    if voice < 1 or not thoughts.enabled(connection):
        return []
    thoughts.catch_up(connection, companion, now)
    timezone = companion['version']['timezone']
    return [item(f"thought:{found['day']}", at(date.fromisoformat(found['day']), EVENING, timezone), 'thought',
                 found['text']) for found in thoughts.week(connection, companion, now)]


def fresh(thoughts: list[dict], told: list[dict]) -> list[dict]:
    """Thoughts not already told: by another line, or on a later day (a thought that stays all week shows once)."""
    seen = [line['text'].casefold() for line in told]
    result = []
    for line in sorted(thoughts, key=lambda found: found['at'], reverse=True):
        text = line['text'].casefold().rstrip('.')
        if not any(text in other for other in seen):
            result.append(line)
            seen.append(text)
    return result


def beats(connection, companion, now, since: date, voice: int, first: str) -> list[dict]:
    from companion.life import storylines
    timezone = companion['version']['timezone']
    result = []
    for story in storylines.visible(connection, companion, now, include_ended=True, shown=True):
        for number, beat in enumerate(story['beats']):
            day = date.fromisoformat(beat['on'])
            if day >= since:
                key = f"beat:{story['id']}:{number}"
                result.append(item(key, at(day, AFTERNOON, timezone), 'story', beat['text'],
                                   inner=thought_after(voice, True, key, beat['tone'], first)))
    return result


def chapters(connection, companion, since: date, voice: int, first: str) -> list[dict]:
    rows = many(connection, 'SELECT * FROM life_chapters WHERE timeline_id=? AND undone_at IS NULL AND started_on>=? '
                'ORDER BY started_on', (companion['active_timeline_id'], since.isoformat()))
    timezone = companion['version']['timezone']
    return [item(f"chapter:{row['id']}", at(date.fromisoformat(row['started_on'][:10]), MIDDAY, timezone), 'chapter',
                 f"A new chapter for {first}: {row['title'][:1].lower()}{row['title'][1:]}.".replace('..', '.'),
                 inner=thought_after(voice, True, f"chapter:{row['id']}", 'mixed', first))
            for row in rows]


def news_heard(connection, companion, since: date) -> list[dict]:
    from companion import news
    from companion.memory import pairs
    key = pairs.companion_key(companion['id'])
    timezone = companion['version']['timezone']
    result = []
    for found in news.heard(connection, key, since.isoformat(), limit=20):
        teller = news.who(connection, found['told_by'], key)
        teller = 'you' if teller == 'the user' else teller
        how = 'told' if found['via'] == 'word' else 'said in a group'
        result.append(item(f"news:{found['id']}", at(date.fromisoformat(found['heard_on']), EVENING, timezone),
                           'news', f"{teller[:1].upper()}{teller[1:]} {how} that {lowered(found['text'])}.",
                           inner=None))
    return result


def family(connection, companion, since: date, today: date, voice: int, first: str) -> list[dict]:
    """Their child's milestones (companion/life/our_child.py), told on the day, in words only."""
    from companion.life import our_child
    timezone = companion['version']['timezone']
    result = []
    for child in our_child.at_home(connection, companion['active_timeline_id'], today):
        for found in our_child.reached(connection, companion, child, today):
            day = date.fromisoformat(found['on'])
            if day >= since and found['key'] != 'grown':
                key = f"milestone:{child['id']}:{found['key']}"
                text = f"{our_child.first(child['name'])} {our_child.did(connection, companion, child, found['key'])}."
                result.append(item(key, at(day, MIDDAY, timezone), 'family', text,
                                   inner=thought_after(voice, True, key, 'good', first)))
    return result


def together(connection, companion, since: date, today: date, first: str) -> list[dict]:
    """Plans made with the user that went ahead (companion/life/outings.py), told as the memory they left: they still
    happen while the user is just watching (Vanta, v0.16 E2E)."""
    from companion.life import outings
    timezone, result = companion['version']['timezone'], []
    for outing in outings.in_force(connection, companion['active_timeline_id'], since.isoformat()):
        day = date.fromisoformat(outing['local_date'])
        if outing['status'] != 'done' or day > today:
            continue
        said = outings.memory_text(outing, first)['value'].rstrip('.')
        said = re.sub(r' on \w+day, \w+ \d{1,2}(?:, \d{4})?$', '', said)
        if not said.startswith(('You ', first)):
            said = f'You and {first} {said[:1].lower()}{said[1:]}'
        hour, minute = (int(part) for part in outing['at_time'].split(':')[:2])
        result.append(item(f"outing:{outing['id']}", at(day, time(hour, minute), timezone), 'day', f'{said}.'))
    return result


ONLY_ONE = {'mom', 'dad', 'mother', 'father', 'stepmom', 'stepdad', 'wife', 'husband', 'grandfather'}


def hushed(lines: list[dict], timezone: str) -> list[dict]:
    """From a death on: no small moments or passing thoughts that day, and no thought after a line (Loss and grief keeps the day quiet)."""
    deaths = {}
    for line in lines:
        if line['kind'] == 'loss':
            day = parse(line['at']).astimezone(zone(timezone)).date()
            deaths[day] = min(deaths.get(day, parse(line['at'])), parse(line['at']))
    result = []
    for line in lines:
        since = deaths.get(parse(line['at']).astimezone(zone(timezone)).date())
        if since is None or line['kind'] == 'loss' or parse(line['at']) < since:
            result.append(line)
        elif line['kind'] not in ('moment', 'thought'):
            result.append({**line, 'inner': None})
    return result


def losses(connection, companion, since: date, today: date, first: str) -> list[dict]:
    """Someone in their life who died (companion/life/loss.py), told on the day."""
    from companion.life import circle, loss
    definition, timezone = companion['version']['definition'], companion['version']['timezone']
    result = []
    for row in loss.rows(connection, companion['active_timeline_id']):
        day = date.fromisoformat(row['died_on'])
        if not row['happened'] or not since <= day <= today:
            continue
        name = loss.first(row['name'])
        # With only one of them (a mom, a husband), the name is an aside: "Mira's dad, James, died."
        aside = f', {name},' if row['role'] in ONLY_ONE else f' {name}'
        who = f"{name} ({row['role']})" if row['kind'] == 'town' else \
            f"{first}'s {circle.said(row['role'], definition)}{aside}"
        key = f"loss:{row['id']}"
        # No thought from the inner voice banks: none of them is written for grief.
        result.append(item(key, at(day, MIDDAY, timezone), 'loss', f'{who} died.'))
    return result


def lowered(text: str) -> str:
    text = text.strip().rstrip('.')
    return text[:1].lower() + text[1:] if text[1:2].islower() else text


def feeling(connection, companion, now, voice: int, shown: bool, first: str) -> list[dict]:
    """How they feel now, in words; its strength too with moods shown under Hidden values."""
    if voice < 2:
        return []
    key = f"companion:{companion['id']}"
    found = moods.current(connection, key, now)
    if not found or found['feeling'] not in FEELING_WORDS:
        return []
    strength = max(1, min(3, int(found.get('intensity') or 1)))
    words = FEELING_WORDS[found['feeling']][strength - 1].format(first=first)
    if found.get('target') and found['feeling'] in ABOUT:
        other = moods.labels_name(connection, found['target'])
        if other:
            words = ABOUT[found['feeling']].format(first=first, other=other)
    return [item(f"mood:{key}", stamp(now), 'mood', words,
                 numbers=[f"{found['feeling']} {strength} of 3"] if shown else [])]


def wandering(days: list[date], timezone: str, now, voice: int, key: str, first: str) -> list[dict]:
    """Passing thoughts, on everything on their mind (3)."""
    if voice < 3:
        return []
    result = []
    for day in days:
        when = at(day, AFTERNOON, timezone)
        if when <= stamp(now):
            seed = f'wander:{key}:{day.isoformat()}'
            result.append(item(seed, when, 'thought', pick('wander', seed).format(first=first)))
    return result


def companion_lines(connection, companion, now) -> list[dict]:
    from companion.life import storylines
    workspace, voice = settings(connection), voice_level(connection)
    first = first_name(companion['version']['definition']['name'])
    today = storylines.local_today(companion, now)
    since = today - timedelta(days=DAYS - 1)
    timezone = companion['version']['timezone']
    days = [since + timedelta(days=offset) for offset in range(DAYS)]
    pronouns = companion_pronouns(companion['version']['definition'])
    lines = (day_events(connection, companion, at(since, time(0), timezone), now, voice, first)
             + moments(connection, companion, now, voice, bool(workspace['show_odds']), first)
             + dreamed(connection, companion, now, voice) + beats(connection, companion, now, since, voice, first)
             + chapters(connection, companion, since, voice, first) + news_heard(connection, companion, since)
             + family(connection, companion, since, today, voice, first)
             + losses(connection, companion, since, today, first)
             + together(connection, companion, since, today, first)
             + narrator_love.told(connection, companion, since, today, voice, first, pronouns))
    lived = {parse(line['at']).astimezone(zone(timezone)).date() for line in lines}
    lines += fresh(on_their_mind(connection, companion, now, voice), lines)
    lines += feeling(connection, companion, now, voice, bool(workspace['show_moods']), first)
    lines += wandering([day for day in days if day in lived], timezone, now, voice, f"companion:{companion['id']}",
                       first)
    pronoun = pronouns.split('/')[0]
    name = companion['version']['definition']['name']
    lines = [{**line, 'text': line['text'].replace(name, first)} if name != first else line for line in lines]
    lines = narrator_love.cooled(hushed(lines, timezone), timezone, first)
    return safe(connection, [told_by(line, now) for line in lines], first, pronoun)


def told_by(line: dict, now) -> dict:
    """A line set later in the day than now (today's Life deck moment is set at midday) is told as of now, just under
    how they feel now, which tops the day."""
    return {**line, 'at': stamp(now - timedelta(seconds=1))} if parse(line['at']) > now else line


# A townsperson's days ------------------------------------------------------------------------------------------------

# The town's words for what someone is doing (companion/world/townsfolk.py), as a narrator tells them afterwards.
AT_WORK = re.compile(r'\bat work \((?P<job>[^)]+)\)')
TOLD_AFTER = (('whoever passes', 'whoever passed'),)


def doing_text(found: dict, pronouns: str | None = None) -> str:
    from companion.life.pronouns import person
    doing, place = found['doing'], found.get('place')
    doing = AT_WORK.sub(lambda match: f"at work as {article(match['job'])} {match['job']}", doing)
    for now_, then in TOLD_AFTER:
        doing = doing.replace(now_, then)
    doing = re.sub(r'\btheir\b', person(pronouns)['their'], doing)
    if place and place.get('name') and place['name'] not in doing:
        return f"{doing} at {place['name']}"
    return doing


def article(word: str) -> str:
    return 'an' if word[:1].casefold() in 'aeiou' else 'a'


# The same part of the day as the day before, told so a routine does not read word for word each day.
AGAIN = ('{first} was {text} again that {part}.', 'The {part} found {first} {text} once more.',
         'As on most days, {first} spent the {part} {text}.', '{first} was back {text} in the {part}.')


def whereabouts(sheet: dict, data: dict, day: date, now) -> list[dict]:
    from companion.world import townsfolk
    timezone, first = town_zone(data), first_name(sheet['name'])
    result, last = [], None
    for moment, part in LOOKS:
        local = datetime.combine(day, moment, tzinfo=zone(timezone))
        if local > now:
            break
        found = townsfolk.whereabouts(sheet, data, local)
        text = doing_text(found, sheet.get('pronouns'))
        if found['doing'] != 'asleep' and text != last:
            key = f"where:{sheet['key']}:{day.isoformat()}:{part}"
            usual = doing_text(townsfolk.whereabouts(sheet, data, local - timedelta(days=1)), sheet.get('pronouns')) == text
            # Turned by the day, so the same part never reads the same two days running.
            turn = (day.toordinal() + random.Random(f"{sheet['key']}:{part}").randrange(len(AGAIN))) % len(AGAIN)
            words = AGAIN[turn] if usual else 'In the {part}, {first} was {text}.'
            result.append(item(key, stamp(local), 'day', words.format(part=part, first=first, text=text)))
        last = text
    return result


def goal_lines(sheet: dict, data: dict, day: date, now, voice: int, shown: bool) -> list[dict]:
    """How their goal went that week (on the day the week turned, or the first day shown) and, from a few thoughts
    on, what they are working toward."""
    from companion.world import townsfolk
    first, timezone = first_name(sheet['name']), town_zone(data)
    state = townsfolk.story(sheet, data, day)
    result = []
    numbers = [f"goal {state['progress']} of {state['goal']['steps']}"] if shown else []
    if state['line'] and (day.weekday() == 0 or day == (now.astimezone(zone(timezone)).date()
                                                        - timedelta(days=DAYS - 1))):
        result.append(item(f"goal:{sheet['key']}:{day.isoformat()}", at(day, MIDDAY, timezone), 'story',
                           f"{state['line'][:1].upper()}{state['line'][1:]}.", numbers=numbers))
    when = at(day, EVENING, timezone)
    if voice >= 1 and when <= stamp(now):
        seed = f"goalthought:{sheet['key']}:{day.isoformat()}"
        result.append(item(seed, when, 'thought', pick('goal', seed).format(first=first, goal=state['goal']['text'])))
    if voice >= 2 and day == now.astimezone(zone(timezone)).date():
        mood = townsfolk.mood_for(sheet, state)
        # With nothing new on their goal, their mood is just their temperament.
        words = f'{first} is {mood} today.' if state['beat'] in ('achieved', 'setback', 'progress') else \
            f'{first} is as {mood} as ever.'
        result.append(item(f"mood:{sheet['key']}", stamp(now), 'mood', words,
                           inner=pick(tone(mood), f"mood:{sheet['key']}:{day.isoformat()}").format(first=first)
                           if voice >= 3 else None, numbers=numbers))
    return result


def crossed(connection, sheet: dict, since: str, timezone: str) -> list[dict]:
    """Companions who ran into them (companion/life/encounters.py), from the townsperson's side."""
    from companion.characters import for_timeline
    rows = many(connection, 'SELECT * FROM townsfolk_encounters WHERE key=? AND local_date>=? ORDER BY met_at',
                (sheet['key'], since))
    result = []
    for row in rows:
        companion = for_timeline(connection, row['timeline_id'])
        if companion and companion.get('active_timeline_id') == row['timeline_id']:
            name = first_name(companion['version']['definition']['name'])
            result.append(item(f"met:{row['timeline_id']}:{row['slot_key']}", row['met_at'], 'met',
                               f"{first_name(sheet['name'])} ran into {name}."))
    return result


def townsperson_lines(connection, sheet: dict, data: dict, now) -> list[dict]:
    workspace, voice = settings(connection), voice_level(connection)
    first, timezone = first_name(sheet['name']), town_zone(data)
    today = now.astimezone(zone(timezone)).date()
    days = [today - timedelta(days=offset) for offset in range(DAYS - 1, -1, -1)]
    shown = bool(workspace['show_moods'])
    lines = [line for day in days for line in whereabouts(sheet, data, day, now)
             + goal_lines(sheet, data, day, now, voice, shown)]
    lines += crossed(connection, sheet, days[0].isoformat(), timezone)
    lines += wandering(days, timezone, now, voice, sheet['key'], first)
    return safe(connection, lines, first, (sheet.get('pronouns') or '').split('/')[0].casefold())



# Someone in a companion's circle -------------------------------------------------------------------------------------

def circle_lines(connection, row: dict, companion: dict, now) -> list[dict]:
    """Their days as their agenda went (companion/life/agenda.py), with the thoughts Inner voice allows."""
    voice, timezone = voice_level(connection), companion['version']['timezone']
    details = decode(row['details'])
    first = first_name(row['name'])
    today = now.astimezone(zone(timezone)).date()
    days = [today - timedelta(days=offset) for offset in range(DAYS - 1, -1, -1)]
    rows = many(connection, "SELECT * FROM life_agenda WHERE timeline_id=? AND subject=? AND status='happened' "
                'AND entry IS NOT NULL AND starts_at>=? AND starts_at<=? ORDER BY starts_at',
                (row['timeline_id'], row['id'], at(days[0], time(0), timezone), stamp(now)))
    entries = [(found, decode(found['entry'])) for found in rows]
    standing = notable_events([{'id': found['id'], 'starts_at': found['starts_at']} for found, _entry in entries])
    lines = []
    for found, entry in entries:
        if not isinstance(entry.get('summary'), str):
            continue
        key = f"circle:{row['id']}:{found['slot_key']}"
        text = entry['summary'].replace(row['name'], first)
        lines.append(item(key, found['starts_at'], 'day', text,
                          inner=thought_after(voice, found['id'] in standing, key, entry.get('mood'), first)))
    lived = {parse(line['at']).astimezone(zone(timezone)).date() for line in lines}
    lines += wandering([day for day in days if day in lived], timezone, now, voice, f"circle:{row['id']}", first)
    pronoun = (details.get('pronouns') or '').split('/')[0].casefold()
    return safe(connection, [told_by(line, now) for line in lines], first, pronoun)


# The page ------------------------------------------------------------------------------------------------------------

def grouped(lines: list[dict], timezone: str, entries: dict[str, str]) -> list[dict]:
    """Newest day first, each day's lines newest first, with the model's few lines for the day when there are."""
    days: dict[str, list[dict]] = {}
    for line in sorted(lines, key=lambda found: (found['at'], found['id']), reverse=True):
        local = parse(line['at']).astimezone(zone(timezone)).date().isoformat()
        days.setdefault(local, []).append(line)
    return [{'date': day, 'entry': entries.get(day), 'items': found} for day, found in days.items()]


def written(connection, focus: str) -> dict[str, str]:
    rows = many(connection, 'SELECT day, text FROM observer_entries WHERE focus=? AND text IS NOT NULL', (focus,))
    return {row['day']: row['text'] for row in rows}


def lines_for(connection, focus: dict, now) -> tuple[list[dict], str]:
    """Every line for the focus and the timezone their days are counted in."""
    if focus['kind'] == 'companion':
        companion = focus['companion']
        return companion_lines(connection, companion, now), companion['version']['timezone']
    if focus['kind'] == 'circle':
        companion = focus['companion']
        return circle_lines(connection, focus['row'], companion, now), companion['version']['timezone']
    return townsperson_lines(connection, focus['sheet'], focus['data'], now), town_zone(focus['data'])


def feed(connection, focus: dict, now) -> dict:
    lines, timezone = lines_for(connection, focus, now)
    workspace = settings(connection)
    return {'focus': public(focus), 'voice': voice_level(connection), 'timezone': timezone,
            'shown': {'moods': bool(workspace['show_moods']), 'odds': bool(workspace['show_odds'])},
            'days': grouped(lines, timezone, written(connection, focus['key']))}


def public(focus: dict) -> dict:
    return {key: focus[key] for key in ('key', 'kind', 'name', 'line', 'why', 'source', 'owner', 'companion_id',
                                         'town_key') if key in focus}


# Who can be watched ---------------------------------------------------------------------------------------------------

def city(connection) -> dict:
    """The town the world's people live in: the main companion's, else the city the persona lives in."""
    from companion import story
    from companion.life import network
    main = current(connection)
    data = network.city(connection, main) if main is not None else {}
    if data.get('places'):
        return data
    home = optional(connection, 'SELECT home_city_id FROM persona WHERE id=1')
    return story.city_data(connection, (home and home['home_city_id']) or story.default_city(connection))


def companion_focus(connection, companion_id: str) -> dict | None:
    companion = by_id(connection, companion_id)
    if companion is None or not companion.get('active_timeline_id'):
        return None
    definition = companion['version']['definition']
    job = ((definition.get('money') or {}).get('career') or '').replace('-', ' ')
    return {'key': f'companion:{companion_id}', 'kind': 'companion', 'name': definition['name'],
            'line': narrator_love.standing(connection, companion) + (f' · {job}' if job else ''),
            'companion_id': companion_id, 'companion': companion}


def town_focus(connection, key: str, data: dict | None = None) -> dict | None:
    from companion.world import townsfolk
    data = data or city(connection)
    sheet = townsfolk.find(data, key)
    if sheet is None or (sheet.get('age') or 30) < 18:
        return None
    where = (sheet.get('place') or {}).get('name')
    role = sheet.get('role') or sheet.get('occupation') or 'townsperson'
    return {'key': key, 'kind': 'townsperson', 'name': sheet.get('full') or sheet['name'],
            'line': f'{role[:1].upper()}{role[1:]}' + (f' at {where}' if where else ''), 'town_key': key,
            'sheet': sheet, 'data': data}


def circle_focus(connection, person_id: str) -> dict | None:
    """Someone in a companion's circle who lives in town (a week of their own there) and is grown up."""
    from companion.characters import for_timeline
    from companion.life import circle
    row = optional(connection, "SELECT * FROM circle_people WHERE id=? AND status='active'", (person_id,))
    if row is None or not decode(row['schedule']):
        return None  # Gone from the circle, or lives out of town with no days here.
    details = decode(row['details'])
    companion = for_timeline(connection, row['timeline_id'])
    if (details.get('age') or 30) < 18 or not companion or companion.get('active_timeline_id') != row['timeline_id']:
        return None
    owner = first_name(companion['version']['definition']['name'])
    job = (details.get('career') or '').strip()
    role = circle.relation(row['role'], details.get('pronouns', ''))
    return {'key': f'circle:{person_id}', 'kind': 'circle', 'name': details.get('full_name') or row['name'],
            'line': f"{owner}'s {role}" + (f' · {job[:1].lower()}{job[1:]}' if job else ''), 'owner': owner,
            'why': 'Lives in town.', 'row': row, 'companion': companion}


def resolve(connection, key: str) -> dict | None:
    if key.startswith('companion:'):
        return companion_focus(connection, key.split(':', 1)[1])
    if key.startswith('circle:'):
        return circle_focus(connection, key.split(':', 1)[1])
    if key.startswith('town:'):
        try:
            return town_focus(connection, key)
        except Exception:  # noqa: BLE001 - someone from a city that has since gone can no longer be watched.
            return None
    return None


def lively(connection, now, limit: int = 3) -> list[dict]:
    """Townsfolk with something going on this week (their goal moving), a seeded handful the same all week."""
    from companion.world import generators, townsfolk
    data = city(connection)
    today = now.astimezone(zone(town_zone(data))).date()
    seed = f"{data['id']}:{data.get('town', '')}:{townsfolk.week_of(today)}"
    places = sorted(data['places'], key=lambda place: generators.unit(seed, 'watch', place['id']))[:12]
    people = [sheet for place in places for sheet in townsfolk.at_place(data, place['id'], today)]
    busy = [sheet for sheet in people if townsfolk.story(sheet, data, today)['beat'] in ('progress', 'achieved')]
    chosen = sorted(busy or people, key=lambda sheet: generators.unit(seed, 'lively', sheet['key']))
    found = (town_focus(connection, sheet['key'], data) for sheet in chosen)
    # Nobody here knows them yet: say why the app offers them, by first name (their pronouns may not be known).
    return [focus | {'source': 'busy', 'why': f"Nobody you know has met {first_name(focus['name'])} yet. Picked for a "
                     'busy week.'} for focus in found if focus][:limit]


def companions(connection) -> list[dict]:
    rows = many(connection, 'SELECT id FROM companions WHERE active_version_id IS NOT NULL ORDER BY slot IS NULL, '
                'stepped_back_at DESC')
    found = (companion_focus(connection, row['id']) for row in rows)
    return [focus for focus in found if focus]


def met(connection, now, limit: int = 8) -> list[dict]:
    """Townsfolk the main companion has met, most recently first."""
    from companion.life import encounters
    main = current(connection)
    if main is None:
        return []
    found = []
    owner = first_name(main['version']['definition']['name'])
    for person in encounters.known(connection, main, now)[:limit]:
        focus = resolve(connection, person['key']) if person.get('key', '').startswith('town:') else None
        if focus:
            times = {1: 'once', 2: 'twice'}.get(person['times'], f"{person['times']} times")
            found.append(focus | {'source': 'met', 'owner': owner,
                                  'why': f"{owner} has run into {first_name(focus['name'])} around town {times}."})
    return found


def circles(connection) -> list[dict]:
    """The people in each companion's circle who live in town, the main companion's first."""
    rows = many(connection, "SELECT p.id FROM circle_people p JOIN companions c ON c.active_timeline_id=p.timeline_id "
                "WHERE p.status='active' AND c.active_version_id IS NOT NULL "
                'ORDER BY c.slot IS NULL, c.stepped_back_at DESC, p.ordinal')
    found = (circle_focus(connection, row['id']) for row in rows)
    return [focus for focus in found if focus]


def first_pick(connection, now) -> dict | None:
    """The app's pick: the companion the user talks to most, else a lively townsperson."""
    talked = optional(connection, "SELECT t.companion_id AS id, COUNT(*) AS n FROM messages m JOIN timelines t "
                      "ON t.id=m.timeline_id WHERE m.role='user' GROUP BY t.companion_id ORDER BY n DESC LIMIT 1")
    focus = talked and companion_focus(connection, talked['id'])
    if focus:
        return focus
    main = current(connection)
    focus = main and companion_focus(connection, main['id'])
    return focus or next(iter(lively(connection, now, 1)), None)


def choices(connection, now, focus: dict | None) -> list[dict]:
    """Who the Focus picker offers, once each: the companions, the people in their circles who live in town,
    townsfolk the main companion has met and a few lively ones."""
    seen, result = set(), []
    for found in [*companions(connection), *circles(connection), *met(connection, now), *lively(connection, now)]:
        if found['key'] not in seen:
            seen.add(found['key'])
            result.append(public(found))
    if focus and focus['key'] not in seen:  # Followed from an earlier week, and still here.
        result.insert(0, public(focus))
    return result


def focus_now(connection, now, write: bool = False) -> dict | None:
    """Who the page follows: the saved focus while they can still be watched, else the app's pick (saved when it
    may write, so the pick holds)."""
    saved = observer.row(connection)['focus']
    focus = resolve(connection, saved) if saved else None
    if focus is None:
        focus = first_pick(connection, now)
        if focus and write:
            observer.follow(connection, focus['key'], stamp(now))
    return focus


def state(connection, now, write: bool = False) -> dict:
    row = observer.row(connection)
    focus = focus_now(connection, now, write)
    offered = choices(connection, now, focus)
    # The followed person as the picker offers them, with why they are there.
    shown = next((choice for choice in offered if focus and choice['key'] == focus['key']), None)
    return {'watching': bool(row['watching']), 'started_at': row['started_at'],
            'focus': shown or (public(focus) if focus else None), 'choices': offered}


def watched_person(connection, key: str) -> tuple[dict, dict] | None:
    """The townsperson the user is watching now, as (city, sheet), for Become them (companion/worlds.py)."""
    row = observer.row(connection)
    if not row['watching'] or row['focus'] != key:
        return None
    focus = resolve(connection, key)
    return (focus['data'], focus['sheet']) if focus and focus['kind'] == 'townsperson' else None


# The day in a few lines, by the model -------------------------------------------------------------------------------

def due_entry(connection, now) -> dict | None:
    """Yesterday for whoever is being watched, once, when it has lines and no try yet."""
    if not observer.watching(connection):
        return None
    focus = focus_now(connection, now)
    if focus is None:
        return None
    lines, timezone = lines_for(connection, focus, now)
    day = (now.astimezone(zone(timezone)).date() - timedelta(days=1)).isoformat()
    if optional(connection, 'SELECT day FROM observer_entries WHERE focus=? AND day=?', (focus['key'], day)):
        return None
    young = named_young(connection) if families_withheld(connection) else None
    texts = [line['text'] for line in lines if parse(line['at']).astimezone(zone(timezone)).date().isoformat() == day
             and line['kind'] not in ('private', 'mood') and not (young and young.search(line['text']))]
    if not texts:
        return None
    return {'focus': focus['key'], 'day': day, 'name': focus['name'], 'pronouns': pronouns_of(focus), 'lines': texts[:20]}


def families_withheld(connection) -> bool:
    from companion.life import families
    return families.withheld(connection)


def companion_pronouns(definition: dict) -> str:
    """'she/her', 'he/him', or they/them when the description does not say (companion/world/looks.py)."""
    from companion.world import looks
    return (definition.get('pronouns') or '').strip().casefold() or looks.pronouns_of(definition)


def pronouns_of(focus: dict) -> str:
    """'she/her', or they/them when the sheet does not say (companions are they/them unless their sheet says)."""
    if focus['kind'] == 'companion':
        return companion_pronouns(focus['companion']['version']['definition'])
    if focus['kind'] == 'circle':
        return (decode(focus['row']['details']).get('pronouns') or '').strip() or 'they/them'
    return (focus['sheet'].get('pronouns') or '').strip() or 'they/them'


def usable(text: str, name: str) -> str | None:
    text = ' '.join(text.strip().strip('"').split())
    first = first_name(name)
    if not text or len(text) > ENTRY_LIMIT or CLOCK.search(text) or first.casefold() not in text.casefold():
        return None
    found = reads(text)
    return text if found is not None and not found & (INTIMATE | {'close', 'minor'}) else None


async def write(provider, scheduler, config, key, due: dict) -> str | None:
    """The model's few lines for the day, or None when they are not usable (the rule-built lines stand alone)."""
    pieces = []
    async with scheduler.reserve(config, LIFE_SYNTHESIS) as lease:
        async for chunk in provider.stream(config, key, ENTRY.format(name=due['name'], pronouns=due.get('pronouns') or 'they/them'),
                                           [{'role': 'user', 'content': '\n'.join(due['lines'])}]):
            if lease.stop.is_set():
                raise BackgroundInterrupted()
            pieces.append(chunk.text)
            if chunk.finish_reason in INCOMPLETE:
                return None
    return usable(''.join(pieces), due['name'])


def save_entry(connection, due: dict, text: str | None, timestamp: str):
    connection.execute('INSERT OR IGNORE INTO observer_entries (focus, day, text, created_at) VALUES (?, ?, ?, ?)',
                       (due['focus'], due['day'], text, timestamp))
