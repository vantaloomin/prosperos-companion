"""Closeness between people: how close a companion and someone else in their world feel to each other.

The same five stages as the user's own closeness (memory/closeness.py), worked out from shared history every
time they are needed. It runs both ways: `closeness(a, b)` is how close `a` feels to `b`, which can be a step
apart from how `b` feels about `a`. Only pairs with at least one companion are ever worked out; two townsfolk,
or two circle people, are never computed, so the thousands of townsfolk in a city cost nothing.

Where a pair starts:
- two companions: "Just met", or higher the more often they have run into each other around town, unless the
  user wrote how they know each other when they were first put together (a group, or becoming a companion);
- a companion and someone in their circle: a default by the circle role, nudged one step up or down by the
  person's seed (some families are tight, some distant; not every close friend is the closest);
- a companion and a townsperson: higher the more often they have met (#204's rule for the user).

What moves it, all by rules: days both spoke in the same group (one a day, however long the talk), group
messages the user kept as a shared moment while both were there (never more than the days), good-news storyline
beats about a circle person, and falling-out beats with them (a step down, won back when they make up). Gentle
cooling after long silences follows the companion's own cooling switch (#204). A guarded secret someone found
out (the secrets ledger) lowers how they feel about the people it is about, but only when their character sheet
says they react that way: there is no built-in jealousy or betrayal. Someone whose "I see myself" lines show a
mask may keep others a step further than they are kept.

Only the one-time backstory is stored (`pair_backstories`); the user has no other dials between people.
"""
import json
import re

from companion import secrets
from companion.characters import by_id
from companion.clock import parse, stamp, zone
from companion.database import decode, many, optional, settings
from companion.errors import require
from companion.memory import closeness as own
from companion.world import generators, perception

STAGES = len(own.THRESHOLDS)
NAMES = own.NAMES
COMPANION, CIRCLE = 'companion:', 'circle:'
HOW_LIMIT = 300

# Circle role (companion/life/circle.py role_kind) -> (default stage, chance one step up, chance one step down).
ROLE_DEFAULTS = {
    'close friend': (4, 0.0, 0.25), 'close-friend': (4, 0.0, 0.25),
    'parent': (3, 0.3, 0.3), 'sibling': (3, 0.3, 0.3),
    'longtime friend': (3, 0.25, 0.25), 'old friend from school': (3, 0.25, 0.25), 'friend': (3, 0.25, 0.25),
    'cousin': (2, 0.3, 0.0), 'roommate from years ago': (2, 0.3, 0.0),
    'coworker': (2, 0.2, 0.0), 'neighbor': (2, 0.2, 0.0), 'new friend': (2, 0.2, 0.0), 'mentor': (2, 0.2, 0.0),
}
UNKNOWN_ROLE = (1, 0.0, 0.0)
# Meetings around town -> the stage they start at, highest first (the same as companion/cast.py for the user).
MEETINGS = ((6, 3), (3, 2), (0, 1))
# Storyline beats with a circle person that move the stage: {story: {beat index: steps, or steps by tone}}.
FALLINGS = {
    'friend_fight': {0: -1, 1: {'good': 1}},
    'drunk_kiss': {1: -1, 2: {'good': 2, 'mixed': 1}},
}
MOST_SECRET_STEPS = 2
# From this stage on, someone has let the other see how they see themselves ("I see myself").
SELF_VIEW_LEVEL = 4
MASK_CHANCE = 0.5
# Words in a character sheet that say finding out a secret about someone would hurt how they feel about them.
REACTS = re.compile(r"\b(?:jealous\w*|grudges?|unforgiving|(?:can't|cannot|never|won't) forgive\w*|betray\w*|"
                    r"possessive|trust issues|hates? (?:being lied to|lies|liars|secrets)|"
                    r"(?:can't|cannot) stand (?:being lied to|lies|liars|secrets)|takes? (?:it|things) personally|"
                    r"holds? on to (?:hurts?|slights?))", re.IGNORECASE)
NEGATED = re.compile(r"\b(?:not|never|isn't|aren't|wasn't|hardly|far from|anything but|no)\s+(?:\w+\s+)?$",
                     re.IGNORECASE)
SHEET_FIELDS = ('identity', 'personality', 'voice', 'background', 'absence_reaction')


# Person keys ----------------------------------------------------------------------------------------

def companion_key(companion_id: str) -> str:
    return f'{COMPANION}{companion_id}'


def normal(key: str) -> str:
    """One key per person: a stepped-back companion living in town (`cast:<id>`) is that companion."""
    return companion_key(key[5:]) if key.startswith('cast:') else key


def companion_id(key: str) -> str | None:
    return key[len(COMPANION):] if key.startswith(COMPANION) else None


def ordered(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a <= b else (b, a)


# Stored backstory ---------------------------------------------------------------------------------

def backstory(connection, a: str, b: str) -> dict | None:
    first, second = ordered(normal(a), normal(b))
    return optional(connection, 'SELECT * FROM pair_backstories WHERE first=? AND second=?', (first, second))


def shared_a_group(connection, a: str, b: str) -> bool:
    return optional(connection, 'SELECT 1 FROM group_members one JOIN group_members two ON two.group_id=one.group_id '
                    'WHERE one.member=? AND two.member=? LIMIT 1', (normal(a), normal(b))) is not None


def can_tell(connection, a: str, b: str) -> bool:
    """The backstory is written once: before the two first share a group, and only if nobody wrote it yet."""
    return backstory(connection, a, b) is None and not shared_a_group(connection, a, b)


def tell(connection, a: str, b: str, level: int | None, how: str, timestamp: str) -> bool:
    """Save how two companions know each other, if it can still be told. Returns whether it was saved."""
    how = ' '.join((how or '').split())[:HOW_LIMIT]
    if not (level or how) or normal(a) == normal(b) or not can_tell(connection, a, b):
        return False
    if any(companion_id(normal(key)) and by_id(connection, companion_id(normal(key))) is None for key in (a, b)):
        return False
    require(level is None or 1 <= level <= STAGES, f'Pick a stage from 1 to {STAGES}.', 422)
    first, second = ordered(normal(a), normal(b))
    connection.execute('INSERT INTO pair_backstories (first, second, start_level, how, created_at) VALUES (?, ?, ?, ?, ?)',
                       (first, second, level, how, timestamp))
    return True


def tell_all(connection, ties, timestamp: str):
    """Several backstories from one form: each {a, b, level, how} with companion ids or person keys."""
    for item in ties or ():
        item = item if isinstance(item, dict) else item.model_dump()
        tell(connection, key_of(item['a']), key_of(item['b']), item.get('level'), item.get('how') or '', timestamp)


def tell_rest(connection, companion_ids: list[str], now, timestamp: str):
    """Pairs among these companions that nobody told about get the backstory the app works out for them."""
    for pair in untold(connection, companion_ids, now):
        tell(connection, companion_key(pair['a']), companion_key(pair['b']), None, pair['how'], timestamp)


def key_of(value: str) -> str:
    return value if ':' in (value or '') else companion_key(value or '')


def forget(connection, companion: str):
    """A companion who is deleted or starts over takes their backstories with them."""
    key = key_of(companion)
    connection.execute('DELETE FROM pair_backstories WHERE first=? OR second=?', (key, key))


# Shared history -----------------------------------------------------------------------------------

def timezone_of(connection):
    return zone(settings(connection)['user_timezone'])


def local_day(instant: str, timezone) -> str:
    return parse(instant).astimezone(timezone).date().isoformat()


def group_days(connection, a: str, b: str, timezone) -> list[str]:
    """Local days on which both spoke in the same group."""
    spoke: dict[str, set] = {a: set(), b: set()}
    for row in many(connection, "SELECT group_id, author, created_at FROM group_messages WHERE status='complete' "
                    'AND author IN (?, ?)', (a, b)):
        spoke[row['author']].add((row['group_id'], local_day(row['created_at'], timezone)))
    return sorted({day for _group, day in spoke[a] & spoke[b]})


def group_moments(connection, a: str, b: str, timezone) -> list[str]:
    """Days of the group messages kept as shared moments while both were in the group."""
    rows = many(connection, 'SELECT message.present, message.created_at FROM group_moments kept '
                'JOIN group_messages message ON message.id=kept.message_id')
    return sorted(local_day(row['created_at'], timezone) for row in rows
                  if {a, b} <= set(json.loads(row['present'] or '[]')))


def town_meetings(connection, companion: dict, other: str, now) -> list[str]:
    """Days a companion and someone ran into each other around town (companion/life/encounters.py)."""
    from companion.life import encounters, network
    try:
        data = network.city(connection, companion)
        cast = encounters.town_cast(connection, companion, data)
        history = encounters.history_for(connection, companion, cast, now)
    except Exception:  # noqa: BLE001 - no city, or a city that no longer loads: nobody was met there.
        return []
    keys = {other, f'cast:{companion_id(other)}'} if companion_id(other) else {other}
    return sorted(meeting['local_date'] for key in keys for meeting in history.get(key, ()))


def meeting_stage(count: int) -> int:
    return next(stage for least, stage in MEETINGS if count >= least)


def contact_days(days: list[str]) -> list[str]:
    return sorted(set(days))


# Rules about the people themselves ------------------------------------------------------------------

def role_default(role: str, seed: str) -> dict:
    """The stage a circle person starts at with the companion: their role's default, nudged by their seed."""
    from companion.life import circle
    base, up, down = ROLE_DEFAULTS.get(circle.role_kind(role), ROLE_DEFAULTS.get(role, UNKNOWN_ROLE))
    roll = generators.unit(seed, 'pair-closeness-nudge')
    nudge = 1 if roll < up else -1 if roll >= 1 - down else 0
    return {'level': min(max(base + nudge, 1), STAGES), 'default': base, 'nudge': nudge}


def masked(companion: dict | None, toward: str) -> bool:
    """A companion whose temperament is a mask (their "I see myself" lines) keeps some people a step further."""
    if companion is None:
        return False
    found = perception.for_companion(companion['id'], companion['version']['definition'])
    if found['gaps'].get('temperament') != 'mask' or found['written']['sees_self']:
        return False
    return generators.unit(f"{companion['id']}:{toward}", 'pair-closeness-mask') < MASK_CHANCE


def self_view(connection, key: str) -> str:
    """How a companion sees themselves, as much as they would tell someone close: the glimpse of their self-story,
    or the first line the user wrote for them."""
    found = by_id(connection, companion_id(normal(key)) or '')
    if found is None:
        return ''
    lines = perception.for_companion(found['id'], found['version']['definition'])
    if lines.get('glimpse'):
        return f"as {lines['glimpse']}."
    return f'"{lines["private"][0]}"' if lines['private'] else ''


def reacts_to_secrets(definition: dict) -> bool:
    """Whether finding out a secret would sour how they feel: only when their sheet says so."""
    parts = [str(definition.get(field) or '') for field in SHEET_FIELDS]
    parts += [str(item) for item in definition.get('flaws') or []]
    parts += [str(trait.get('name', '')) for trait in definition.get('emotional_traits') or [] if isinstance(trait, dict)]
    text = ' '.join(parts)
    return any(not NEGATED.search(text[max(0, match.start() - 30):match.start()]) for match in REACTS.finditer(text))


def secrets_found(connection, holder: str, about: str) -> int:
    """Secrets about `about` that were kept from `holder` and that they found out (it slipped, or the user let them
    find out). The secrets ledger counts them (companion/secrets.py)."""
    return secrets.found_about(connection, normal(holder), normal(about))


def story_moves(connection, companion: dict, person_id: str, today: str) -> dict:
    """What storylines with a circle person did: steps down from falling-outs (won back by making up), and
    points from good news they shared."""
    steps, points, reasons = 0, 0, []
    for row in many(connection, 'SELECT story, cast_ids, stages FROM storylines WHERE timeline_id=?',
                    (companion['active_timeline_id'],)):
        if person_id not in decode(row['cast_ids']):
            continue
        for index, stage in enumerate(decode(row['stages'])):
            if stage['on'] > today or stage.get('pending'):
                break
            move = FALLINGS.get(row['story'], {}).get(index)
            if isinstance(move, dict):
                move = move.get(stage['tone'], 0)
            if move:
                steps += move
                reasons.append({'kind': 'fell_out' if move < 0 else 'made_up', 'on': stage['on'], 'steps': move})
            elif stage['tone'] == 'good' and row['story'] not in FALLINGS:
                points += 1
                reasons.append({'kind': 'good_news', 'on': stage['on']})
    return {'steps': min(steps, 0), 'points': points, 'reasons': reasons}


def cooled(connection, companion: dict | None, days: list[str], now, timezone) -> int:
    """Steps lost to long silences, when the companion has gentle cooling on (closeness.py), counted from the day
    they turned it on. Never below the second stage; the caller applies the floor."""
    if companion is None:
        return 0
    chosen = own.options(connection, companion['active_timeline_id'])
    if chosen['cooling_since'] is None:
        return 0
    return own.cooling(days, local_day(chosen['cooling_since'], timezone), local_day(stamp(now), timezone))['steps']


# Working it out ----------------------------------------------------------------------------------

def level_from(start: int, points: int) -> int:
    return own.level_for(own.THRESHOLDS[start - 1] + points)


def clamp(level: int) -> int:
    return min(max(level, 1), STAGES)


def circle_person(connection, key: str) -> dict | None:
    return optional(connection, 'SELECT * FROM circle_people WHERE seed=?', (key,))


def owner_of(connection, person: dict) -> dict | None:
    row = optional(connection, 'SELECT companion_id FROM timelines WHERE id=?', (person['timeline_id'],))
    found = by_id(connection, row['companion_id']) if row else None
    return found if found and found['active_timeline_id'] == person['timeline_id'] else None


def both_companions(connection, a: str, b: str, first: dict, second: dict, now, timezone) -> dict:
    told = backstory(connection, a, b)
    met = town_meetings(connection, first, b, now)
    days, moments = group_days(connection, a, b, timezone), group_moments(connection, a, b, timezone)
    start = told['start_level'] if told and told['start_level'] else meeting_stage(len(met))
    base = level_from(start, len(days) + min(len(moments), len(days)))
    contact = contact_days(days + met)

    def toward(me: dict, them: str) -> dict:
        level = base - masked(me, them) - min(secrets_found(connection, companion_key(me['id']), them),
                                              MOST_SECRET_STEPS) * reacts_to_secrets(me['version']['definition'])
        level = clamp(level)
        steps = cooled(connection, me, contact, now, timezone)
        return {'level': max(level - steps, min(level, own.COOL_FLOOR)), 'cooled': steps > 0}

    return {'start': start, 'how': told['how'] if told else '', 'told': told is not None,
            'group_days': len(days), 'moments': min(len(moments), len(days)), 'meetings': len(met),
            'ab': toward(first, b), 'ba': toward(second, a)}


def with_circle(connection, a: str, b: str, me: dict, person: dict, now) -> dict:
    """A companion and someone in their own circle; both directions start at the role's default."""
    found = role_default(person['role'], person['seed'])
    today = now.astimezone(zone(me['version']['timezone'])).date().isoformat()
    moved = story_moves(connection, me, person['id'], today)
    base = clamp(level_from(found['level'], moved['points']) + moved['steps'])
    mine = clamp(base - masked(me, b) - min(secrets_found(connection, a, b), MOST_SECRET_STEPS)
                 * reacts_to_secrets(me['version']['definition']))
    return {'start': found['level'], 'role': person['role'], 'nudge': found['nudge'], 'how': '', 'told': False,
            'storylines': moved['reasons'], 'ab': {'level': mine, 'cooled': False},
            'ba': {'level': base, 'cooled': False}}


def with_townsperson(connection, a: str, b: str, me: dict, now) -> dict:
    met = town_meetings(connection, me, b, now)
    base = meeting_stage(len(met))
    mine = clamp(base - masked(me, b) - min(secrets_found(connection, a, b), MOST_SECRET_STEPS)
                 * reacts_to_secrets(me['version']['definition']))
    return {'start': base, 'how': '', 'told': False, 'meetings': len(met),
            'ab': {'level': mine, 'cooled': False}, 'ba': {'level': base, 'cooled': False}}


def pair(connection, a: str, b: str, now) -> dict | None:
    """Both directions between two people, with what made them; None when neither is a companion."""
    a, b = normal(a), normal(b)
    if a == b:
        return None
    first, second = (by_id(connection, companion_id(key) or '') for key in (a, b))
    if first is None and second is None:
        return None
    if first is None:
        flipped = pair(connection, b, a, now)
        return flipped and {**flipped, 'ab': flipped['ba'], 'ba': flipped['ab']}
    if second is not None:
        return both_companions(connection, a, b, first, second, now, timezone_of(connection))
    if b.startswith(CIRCLE):
        person = circle_person(connection, b)
        if person is None or owner_of(connection, person) is None or owner_of(connection, person)['id'] != first['id']:
            return None
        return with_circle(connection, a, b, first, person, now)
    return with_townsperson(connection, a, b, first, now)


def closeness(connection, a: str, b: str, now) -> int | None:
    """How close `a` feels to `b`, from 1 ("Just met") to 5; None when neither is a companion (never computed).
    Keys are person keys: `companion:<id>`, `circle:<timeline>:<n>` or a townsfolk key."""
    found = pair(connection, a, b, now)
    return found['ab']['level'] if found else None


def between(connection, a: str, b: str, now) -> dict | None:
    """Both directions with their stage names, for profiles and the group section."""
    found = pair(connection, a, b, now)
    if found is None:
        return None
    return {**found, 'a': normal(a), 'b': normal(b),
            'ab': {**found['ab'], 'name': NAMES[found['ab']['level'] - 1]},
            'ba': {**found['ba'], 'name': NAMES[found['ba']['level'] - 1]}}


# Who knows whom -----------------------------------------------------------------------------------

def known_companions(connection, companion: dict, now) -> list[str]:
    """Other companions this one has a tie with: a backstory, a group in common, or a meeting in town."""
    key = companion_key(companion['id'])
    others = [row['id'] for row in many(connection, 'SELECT id FROM companions WHERE id!=? AND active_version_id IS NOT NULL',
                                        (companion['id'],))]
    found = []
    for other in others:
        other_key = companion_key(other)
        if backstory(connection, key, other_key) or shared_a_group(connection, key, other_key) \
                or town_meetings(connection, companion, other_key, now):
            found.append(other_key)
    return found


def ties(connection, companion: dict, now) -> list[dict]:
    """A companion's ties to the other companions they know, both directions, read-only for their profile."""
    key = companion_key(companion['id'])
    result = []
    for other in known_companions(connection, companion, now):
        found = between(connection, key, other, now)
        other_companion = by_id(connection, companion_id(other))
        if found and other_companion:
            result.append({'companion_id': other_companion['id'], 'name': other_companion['version']['name'],
                           'feels': found['ab'], 'they_feel': found['ba'], 'how': found['how'],
                           'group_days': found['group_days'], 'meetings': found['meetings']})
    return result


def defaults_for_new(connection, others: list[dict], key: str, now) -> list[dict]:
    """The ties a new companion (a townsperson or match about to become one, `key` their town key) would start
    with, for the form that makes them a companion: every other companion, at the stage their meetings in town
    give, which the user can change once there."""
    result = []
    for other in others:
        met = town_meetings(connection, other, key, now)
        result.append({'companion_id': other['id'], 'name': other['version']['name'], 'meetings': len(met),
                       'level': meeting_stage(len(met)), 'name_of_level': NAMES[meeting_stage(len(met)) - 1]})
    return result


def untold(connection, companion_ids: list[str], now) -> list[dict]:
    """Pairs among these companions whose backstory can still be written, with the stage they would start at."""
    keys = [companion_key(item) for item in dict.fromkeys(companion_ids)]
    result = []
    for index, a in enumerate(keys):
        for b in keys[index + 1:]:
            if not can_tell(connection, a, b):
                continue
            first, second = by_id(connection, companion_id(a)), by_id(connection, companion_id(b))
            if first is None or second is None:
                continue
            met = len(town_meetings(connection, first, b, now))
            result.append({'a': first['id'], 'b': second['id'], 'a_name': first['version']['name'],
                           'b_name': second['version']['name'], 'level': meeting_stage(met),
                           'how': suggested_how(connection, first, second, met)})
    return result


def suggested_how(connection, first: dict, second: dict, met: int) -> str:
    """How two companions know each other, worked out from where they live and whether they have met in town, so
    the form starts filled in ("the world exists outside of User", Vanta 2026-10-08); the user can change it."""
    from companion.world import changes, custom
    cities = custom.all_cities(connection)
    homes = [changes.resolve(item['version']['definition'].get('home_city') or '', cities) if
             item['version']['definition'].get('home_city') else None for item in (first, second)]
    shared = homes[0]['name'] if homes[0] and homes[1] and homes[0]['id'] == homes[1]['id'] else ''
    if met:
        return f'Have run into each other around {shared}' if shared else 'Have run into each other around town'
    return f'Both live in {shared}, but only know each other through the user' if shared else \
        'Only know each other through the user'


def shown(found: dict | None) -> dict | None:
    """The read-only stage line for a profile or a person card: how the companion feels, and the other way."""
    if found is None:
        return None
    return {'level': found['ab']['level'], 'name': found['ab']['name'],
            'their_level': found['ba']['level'], 'their_name': found['ba']['name']}


def for_circle(connection, companion: dict, rows: list[dict], now) -> dict[str, dict]:
    """Each circle person's stage with the companion, by person id."""
    key = companion_key(companion['id'])
    return {row['id']: shown(between(connection, key, row['seed'], now)) for row in rows}


def for_townsperson(connection, companion: dict, person: dict, now) -> dict | None:
    """A met townsperson's stage with the companion: by how often they have met, or worked out in full for
    another companion living in town."""
    key = companion_key(companion['id'])
    if person.get('cast'):
        return shown(between(connection, key, companion_key(person['cast']), now))
    level = meeting_stage(person['times'])
    mine = clamp(level - masked(companion, person['key']) - min(secrets_found(connection, key, person['key']),
                 MOST_SECRET_STEPS) * reacts_to_secrets(companion['version']['definition']))
    return {'level': mine, 'name': NAMES[mine - 1], 'their_level': level, 'their_name': NAMES[level - 1]}
