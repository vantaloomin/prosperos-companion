"""Scenes count (1.5, docs/story.md): time the user spends with a companion in the Story is part of their life together.

A visit is one stretch of the story with a companion in the scene (`story_visits`): it opens with the user's first
line while they are there and ends when the user moves on, clears the pages, the companion's day takes them
away, or nothing has been said for a while. Rules only, no model:

- A day the user talked with them in person counts as a day talked, as a day of texting does
  (companion/memory/closeness.py), so closeness grows the same way and no faster.
- A visit with a real exchange leaves one shared moment (a memory, as an outing does), at most one a day for each
  companion and one for each place. It shows on Memories, in the scrapbook and in "Our history".
- What the user says to them is read by the relationship step rules chat uses (companion/life/steps.py): the user
  can bring a step up or answer one face to face, and the companion's own line answers it.
- What the user tells them there is remembered, and moves how they feel, as a text would (companion/story_said.py).
- Afterward their chat knows it happened: a line in the 'where' section says when and where, and how it ended in
  the words that were said, for a day or so (memory/context.py).

Settings > Realism > "Story scenes count" turns all of it off (life_settings.story_counts): the story is then apart
from the companion's life again, as it was before 1.5.
"""
from datetime import datetime, timedelta

from companion import in_character, story_cast, story_said
from companion.characters import by_id
from companion.clock import parse, stamp, zone
from companion.database import decode, encode, identifier, many, optional

ACTIVE = True
# No line for this long ends a visit, whoever is still standing there.
IDLE = timedelta(hours=2)
# A shared moment takes a real exchange: this many of the user's lines to them, and a line of their own.
MEMORY_SAID = 2
# How long their chat is told about a visit after it ends.
TOLD_FOR = timedelta(hours=36)
EXCERPT_LINES = 6
LINE_CHARS = 220

CAME = {'user': 'the user came by {place} while you were {doing}',
        'them': 'you came by {place} and found the user there'}
DOING = {story_cast.AT_WORK: 'at work there'}
# The user's own home (companion/story.py HOME) as a visit keeps it: the user reads "your place" on Memories, and the
# companion is told "the user's place" (memory/records.py as_told).
AT_YOURS = 'your place'
CAME_HOME = "you were at the user's place with them"
TOLD = ('- {when}, {came}, and the two of you spent time together in person. It really happened, and you remember '
        'it. You are apart again now, texting.')
# A plan played in the Story (companion/story_plans.py): the 'together' section already says what and where, and
# while it is still going on they are not apart.
TOLD_PLAN = ('- {when}, at {place}, the two of you talked face to face, on the plan you had made. It really '
             'happened, and you remember it.')
ENDED = ' How it ended, in the words that were said:'
SAID = ' The latest of what was said:'


def counts(connection) -> bool:
    """Whether scenes count at all (Settings > Realism > Story scenes count)."""
    row = optional(connection, 'SELECT story_counts FROM life_settings WHERE id=1')
    return ACTIVE and (bool(row['story_counts']) if row else True)


def open_visits(connection) -> list[dict]:
    return many(connection, 'SELECT * FROM story_visits WHERE ended_at IS NULL ORDER BY started_at')


# While the scene goes on ----------------------------------------------------------------------------

def start(connection, item: dict, user: dict, view: dict, now: datetime) -> dict:
    companion, visit_id = item['companion'], identifier()
    stay = optional(connection, 'SELECT since_seq FROM story_cast WHERE companion_id=?', (item['id'],))
    came = 'user' if story_cast.here_first(connection, stay['since_seq'] if stay else 0) else 'them'
    day = now.astimezone(zone(companion['version']['timezone'])).date().isoformat()
    connection.execute(
        'INSERT INTO story_visits (id, companion_id, timeline_id, city_id, place_id, place_name, doing, came, '
        'local_date, first_seq, last_seq, started_at, last_at, outing_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (visit_id, item['id'], companion['active_timeline_id'], view['city']['id'], view['place']['id'],
         AT_YOURS if view['place'].get('home') else view['place']['name'], item['doing'], came, day, user['seq'],
         user['seq'], stamp(now), stamp(now),
         item['plan']['id'] if item.get('plan') else None))
    return optional(connection, 'SELECT * FROM story_visits WHERE id=?', (visit_id,))


def said(connection, user: dict, view: dict, now: datetime) -> None:
    """The user's line was just saved with these companions in the scene: each one's visit opens or goes on, and
    a line meant for one of them is read for a relationship step before anyone answers it."""
    if not counts(connection):
        return
    settle(connection, now, keep={item['id'] for item in view['companions']})
    if in_character.out_of_character(user['text']):
        return
    going = {visit['companion_id']: visit for visit in open_visits(connection)}
    spoken_to = {item['id'] for item in story_cast.speakers(view['companions'], view['people'], user['text'])}
    for item in view['companions']:
        visit = going.get(item['id'])
        if visit and (visit['place_id'] != view['place']['id'] or
                      visit['timeline_id'] != item['companion']['active_timeline_id']):
            close(connection, visit, now)
            visit = None
        visit = visit or start(connection, item, user, view, now)
        connection.execute('UPDATE story_visits SET last_seq=?, last_at=?, said=said+? WHERE id=?',
                           (user['seq'], stamp(now), int(item['id'] in spoken_to), visit['id']))
    target = meant_for(view['companions'], spoken_to, user['text'])
    if target:
        from companion.life import steps
        steps.said_in_person(connection, target['companion'], user, last_line(connection, target['id'], user['seq']))
    # What it tells them is remembered, and the one it is meant for feels it (companion/story_said.py).
    story_said.user_line(connection, user, [item for item in view['companions'] if item['id'] in spoken_to], target, now)


def said_again(connection, user: dict, old_text: str, view: dict, now: datetime) -> None:
    """The user's latest line was changed (companion/story_again.py): whoever the old words were said to no longer
    counts them, and the new words are read as a new line is. A relationship step the old words settled stays
    settled (steps.said_in_person reads a line once), and what they told a companion stays remembered until the new
    words correct it."""
    if counts(connection) and not in_character.out_of_character(old_text):
        for item in story_cast.speakers(view['companions'], view['people'], old_text):
            connection.execute('UPDATE story_visits SET said=MAX(said - 1, 0) WHERE companion_id=? AND ended_at IS NULL '
                               'AND last_seq>=?', (item['id'], user['seq']))
    said(connection, user, view, now)


def meant_for(present: list[dict], spoken_to: set[str], text: str) -> dict | None:
    """The one companion a line is said to: the only one there, or the only one it names."""
    found = [item for item in present if item['id'] in spoken_to]
    if len(found) > 1:
        found = [item for item in found if story_cast.named(item, text)]
    return found[0] if len(found) == 1 else None


def last_line(connection, companion_id: str, before_seq: int) -> str:
    """Their latest own line in the scene before this one, or ''."""
    row = optional(connection, "SELECT text FROM story_messages WHERE role=? AND speaker=? AND status='complete' AND "
                   'seq<? ORDER BY seq DESC LIMIT 1', (story_cast.ROLE, companion_id, before_seq))
    return row['text'] if row else ''


def heard(connection, line: dict, now: datetime) -> None:
    """A companion's own line was just saved: their visit runs up to it, and what they said can make up."""
    if line['status'] == 'complete':
        connection.execute('UPDATE story_visits SET last_seq=MAX(last_seq, ?), last_at=? WHERE companion_id=? AND '
                           'ended_at IS NULL', (line['seq'], stamp(now), line['speaker']))
        if counts(connection) and (companion := by_id(connection, line['speaker'])):
            story_said.their_line(connection, companion, line, now)


def fresh_lines(connection, companion: dict, user: dict, now: datetime) -> list[tuple[str, str]]:
    """For their own line in the scene: a step the user's line just settled (companion/life/steps.py)."""
    if not counts(connection):
        return []
    from companion.life import steps
    return [(identity, text.removeprefix('- ')) for identity, text in
            steps.fresh_lines(connection, companion, now, {user['id']})]


# When it ends ---------------------------------------------------------------------------------------

def lines_of(connection, visit: dict) -> list[dict]:
    """What the two of them said during the visit: the user's lines and the companion's own, in order."""
    return many(connection, "SELECT role, text FROM story_messages WHERE seq>=? AND seq<=? AND status='complete' AND hidden=0 AND "
                "(role='user' OR (role=? AND speaker=?)) ORDER BY seq",
                (visit['first_seq'], visit['last_seq'], story_cast.ROLE, visit['companion_id']))


def excerpt(lines: list[dict]) -> list[dict]:
    kept = [line for line in lines if not in_character.out_of_character(line['text'])][-EXCERPT_LINES:]
    return [{'who': 'user' if line['role'] == 'user' else 'you', 'text': clipped(line['text'])} for line in kept]


def clipped(text: str) -> str:
    text = ' '.join(text.split())
    return text if len(text) <= LINE_CHARS else text[:LINE_CHARS - 1].rstrip() + '…'


def close(connection, visit: dict, now: datetime) -> None:
    """The visit is over: what was said at the end is kept for their chat, and a real exchange is remembered."""
    lines = lines_of(connection, visit)
    spoke = sum(line['role'] != 'user' for line in lines)
    ended = min(stamp(now), stamp(parse(visit['last_at']) + IDLE))
    # A plan leaves its own memory when it ends (companion/life/outings.py): the visit adds none.
    memory_id = remember(connection, visit) if visit['said'] >= MEMORY_SAID and spoke and not visit['outing_id'] else None
    connection.execute('UPDATE story_visits SET ended_at=?, heard=?, excerpt=?, memory_id=? WHERE id=?',
                       (ended, spoke, encode(excerpt(lines)), memory_id, visit['id']))


def remember(connection, visit: dict) -> str | None:
    """The shared moment a visit leaves, one a day for each companion: a second visit that day is part of it."""
    from companion.memory import records
    companion = by_id(connection, visit['companion_id'])
    if companion is None or companion['active_timeline_id'] != visit['timeline_id']:
        return None
    earlier = optional(connection, 'SELECT memory_id FROM story_visits WHERE companion_id=? AND timeline_id=? AND '
                       'local_date=? AND memory_id IS NOT NULL LIMIT 1',
                       (visit['companion_id'], visit['timeline_id'], visit['local_date']))
    if earlier:
        return earlier['memory_id']
    fields = {**memory_text(visit, companion['version']['definition']['name'].split()[0]), 'layer': 'shared_experience',
              'stated_at': visit['last_at'], 'applies_from': None, 'applies_until': None}
    memory, _created = records.insert(connection, companion, fields, now=visit['last_at'], origin='automatic')
    return memory['id']


def memory_text(visit: dict, name: str) -> dict:
    """{subject, value} as the user reads it on Memories and the scrapbook: "you" is the user and the companion
    goes by their first name; the companion reads it the other way round (memory/records.py as_told). Plain, with
    no date (Iris: the card's own line says "In Story" and when), so time at the same place again is the same
    moment (records.find_duplicate): one for each place they have been together."""
    if visit['place_name'] == AT_YOURS:  # Named in the subject too, so it turns round whole for the companion.
        return {'subject': f'In person with {name} at {AT_YOURS}',
                'value': f'{name} and you spent time together at {AT_YOURS}.'}
    return {'subject': f"In person at {visit['place_name']}",
            'value': f"{name} and you spent time together at {visit['place_name']}."}


def settle(connection, now: datetime, keep: set[str] | None = None) -> int:
    """Close the visits that are over: the companion is no longer in the scene (`keep` is who is, when the caller
    knows; else `story_cast` says), or nothing has been said for a while. Returns how many closed."""
    if keep is None:
        keep = {row['companion_id'] for row in many(connection, 'SELECT companion_id FROM story_cast')}
    done = [visit for visit in open_visits(connection)
            if visit['companion_id'] not in keep or now - parse(visit['last_at']) > IDLE]
    for visit in done:
        close(connection, visit, now)
    return len(done)


def close_all(connection, now: datetime) -> None:
    """The user went somewhere else or cleared the pages: every visit ends here, before the lines can go."""
    for visit in open_visits(connection):
        close(connection, visit, now)


# What counts ----------------------------------------------------------------------------------------

def talk_days(connection, timeline_id: str, since: str | None, timezone) -> set[str]:
    """The local dates the user talked with them in person, for closeness (companion/memory/closeness.py)."""
    if not counts(connection):
        return set()
    rows = many(connection, 'SELECT started_at FROM story_visits WHERE timeline_id=? AND said>0 AND started_at>=?',
                (timeline_id, since or ''))
    return {parse(row['started_at']).astimezone(timezone).date().isoformat() for row in rows}


# What their chat is told ------------------------------------------------------------------------------

def when_text(ended: datetime, now: datetime, timezone) -> str:
    then, today = ended.astimezone(timezone), now.astimezone(timezone).date()
    days = (today - then.date()).days
    day = 'Earlier today' if days == 0 else 'Yesterday' if days == 1 else f'On {then:%A}'
    return f'{day}, around {then:%H:%M}'


def told_text(visit: dict, lines: list[dict], now: datetime, timezone) -> str:
    when = when_text(parse(visit['ended_at'] or visit['last_at']), now, timezone)
    if visit['outing_id']:
        text = TOLD_PLAN.format(when=when, place=visit['place_name'])
    else:
        came = CAME_HOME if visit['place_name'] == AT_YOURS else CAME[visit['came']].format(
            place=visit['place_name'], doing=DOING.get(visit['doing'], 'there on your own time'))
        text = TOLD.format(when=when, came=came)
    if not lines:
        return text
    said_lines = '\n'.join(f"  {'The user' if line['who'] == 'user' else 'You'}: {line['text']}" for line in lines)
    return f"{text}{ENDED if visit['ended_at'] or not visit['outing_id'] else SAID}\n{said_lines}"


def context_lines(connection, companion: dict, now: datetime) -> list[tuple[str, str]]:
    """(identity, line) for the 'where' section of their 1:1 chat: the latest visit of the last day or so."""
    if not counts(connection):
        return []
    visit = optional(connection, 'SELECT * FROM story_visits WHERE companion_id=? AND timeline_id=? AND said>0 '
                     'ORDER BY last_at DESC LIMIT 1', (companion['id'], companion['active_timeline_id']))
    if visit is None or now - parse(visit['ended_at'] or visit['last_at']) > TOLD_FOR:
        return []
    lines = decode(visit['excerpt']) if visit['ended_at'] else excerpt(lines_of(connection, visit))
    if not visit['ended_at'] and not any(line['who'] == 'you' for line in lines):
        return []  # Still going on and they have not said a word yet: nothing to remember.
    if visit['ended_at'] and not visit['heard']:
        return []
    timezone = zone(companion['version']['timezone'])
    return [(f"story-visit:{visit['id']}:{len(lines)}", told_text(visit, lines, now, timezone))]


# In their chat ---------------------------------------------------------------------------------------

CHAT_LINES = 60
SAME_LINE = timedelta(minutes=1)


def chat_lines(connection, companion: dict) -> list[dict]:
    """The visits that are over, for one line each in their 1:1 chat at the point it happened: "In Story at Club
    Charles · 2:06 to 2:31 PM · Read it" (docs/story.md, "Scenes count"). Only a visit with something said to them, and
    only while scenes count. `from` and `until` are the moments it began and the last thing was said: the chat shows
    them on the clock its own stamps are on (Iris). `at` is the same last moment, for placing it. `chapter` is the Story chapter it can be read in
    (companion/story_chapters.py), or None once its lines are cleared or further back than the Story shows."""
    if not counts(connection):
        return []
    from companion import story, story_chapters
    rows = many(connection, 'SELECT * FROM story_visits WHERE companion_id=? AND timeline_id=? AND said>0 AND '
                'ended_at IS NOT NULL ORDER BY last_at DESC LIMIT ?', (companion['id'], companion['active_timeline_id'], CHAT_LINES))
    if not rows:
        return []
    starts = story_chapters.marks(connection, parse(rows[0]['last_at']))[0]
    shown = many(connection, 'SELECT seq, created_at FROM story_messages ORDER BY seq DESC LIMIT ?', (story.HISTORY_LIMIT,))
    written = {row['seq']: parse(row['created_at']) for row in shown}

    def chapter(visit: dict) -> int | None:
        # The same line, not one that took its number after the pages were cleared.
        line = written.get(visit['first_seq'])
        same = line is not None and abs(line - parse(visit['started_at'])) <= SAME_LINE
        return story_chapters.number(starts, visit['first_seq']) if same else None

    return [{'id': visit['id'], 'at': visit['last_at'], 'place': visit['place_name'], 'from': visit['started_at'],
             'until': visit['last_at'], 'chapter': chapter(visit)} for visit in reversed(rows)]
