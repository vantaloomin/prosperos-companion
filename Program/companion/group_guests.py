"""Guests in group chats: people from the members' own lives who join for a while (docs/group-chat.md, "Guests").

A guest is someone a companion in the group knows: a person in their circle (a sister, a coworker, an old friend),
or a townsperson they keep running into. Guests are group members like any other (a stay in `group_members`, under
their own person key: `circle:<timeline>:<n>` or a townsfolk key), with `host`, the companion who knows them.

Rules decide everything, no model calls:

- **Who comes in.** When someone in the chat names a person a member knows ("Ada would love this"), that member
  may pull them in: seeded by the message, more often at higher Settings > Realism > "Guests drop in"
  (`guests_realism`), never while that person is asleep, at most `MOST_GUESTS` passing guests at once and one
  pull-in per group in `PULL_GAP`. The user can also add or remove anyone a member knows.
- **How much they say.** Guests answer like members (anyone named first, then by weight, a little less often than
  members) but at most `GUEST_REPLIES` times a conversation, and never while asleep by their own day.
- **How long they stay.** Once the chat has been quiet for `QUIET` a passing guest slips out. Someone who comes back
  `REGULAR_VISITS` times becomes a regular and stays; the user can keep anyone with one tap (`kept`).

A guest has no 1:1 chat and no memory of their own: they remember the group through its own history, and their
reply is built from a short rule-made sheet (who they are to the host, how they come across and see themselves,
what they're doing right now).
"""
import random
import re
from datetime import timedelta

from companion.characters import by_id
from companion.clock import parse, zone
from companion.database import decode, many, one, optional
from companion.life import agenda, circle, encounters, network, town_personality
from companion.world import perception

COMPANION = 'companion:'
# Settings > Realism > "Guests drop in" (life_settings.guests_realism): never on their own, now and then, true to
# life, often. The chance a person named in the chat is pulled in, and the least time between two pull-ins.
DEFAULT_LEVEL = 2
PULL_CHANCE = (0.0, 0.15, 0.3, 0.55)
PULL_GAP = (None, timedelta(days=3), timedelta(hours=24), timedelta(hours=8))
# Passing guests (not kept, not regulars) in one group at once.
MOST_GUESTS = 2
# Replies a guest writes in one conversation; a conversation ends when the chat has been quiet for QUIET.
GUEST_REPLIES = 4
QUIET = timedelta(hours=3)
REGULAR_VISITS = 3
# A townsperson the companion has met this often knows them well enough to be pulled into a chat.
KNOWS_TOWNSPERSON = 3
# How likely a guest is picked to answer next to a member, when nobody is named.
GUEST_WEIGHT = 0.6
# Local hours when someone with no plan of their own for the hour is asleep.
NIGHT = (0, 7)

SHEET = """Who you are: {who}
You're a guest in this group chat: {host} brought you in. You have no chat of your own with the user and know them \
only from what is said here and what {host} has told you, so never claim history with the user beyond this chat. \
You have your own life and opinions; keep to what you'd plausibly know.
{lines}"""
# In a guest's own notes for each reply, with their group section: tested to keep them from going along with a
# shared past the user brings up (A/B, companion-v11-guests-ab: 80% held vs 58% with the sheet alone).
NO_HISTORY = ("You and the user have no history outside this chat: if they bring up something you did together, it "
              "didn't happen as far as you know.")
# Someone who has met the user in person (companion/life/their_people.py) and likes them may drop in on their own, not
# only when named: this share of the usual chance.
DROP_IN_SHARE = 0.25


def is_guest(key: str) -> bool:
    return not key.startswith(COMPANION)


def level(connection) -> int:
    row = optional(connection, 'SELECT guests_realism FROM life_settings WHERE id=1')
    return row['guests_realism'] if row and row['guests_realism'] in range(4) else DEFAULT_LEVEL


# Who they are --------------------------------------------------------------------------------------

def host_companion(connection, stay_or_candidate: dict) -> dict | None:
    host = stay_or_candidate.get('host') or ''
    return by_id(connection, host[len(COMPANION):]) if host.startswith(COMPANION) else None


def circle_people(connection, companion: dict) -> list[dict]:
    return circle.people(connection, companion['active_timeline_id']) if companion.get('active_timeline_id') else []


def full_name(row: dict, details: dict) -> str:
    """Their full name as the circle shows it now: a name the user changed wins over the one they were seeded with
    ("Lizzie Napolitano" once Lisa is renamed Lizzie)."""
    shown, full = row['name'], details.get('full_name') or row['name']
    if ' ' in shown:
        return shown
    given, _, family = full.partition(' ')
    return full if given == shown else ' '.join(part for part in (shown, family) if part)


def from_circle(row: dict, host: str, host_name: str) -> dict:
    details = decode(row['details']) or {}
    return {'key': row['seed'], 'kind': 'circle', 'name': row['name'], 'full': full_name(row, details),
            'host': host, 'relation': f"{host_name}'s {row['role']}", 'tie': f"their {row['role']}", 'person_id': row['id'],
            'timeline_id': row['timeline_id']}


def town_tie(person: dict) -> str:
    """Who a townsperson is, as the host would introduce them: "the barista at Blue Moon", "a neighbor from Canton"."""
    if person['kind'] == 'resident':
        return f"a neighbor from {person['neighborhood']}" if person['neighborhood'] else 'someone from around town'
    # Once they've left their place (companion/world/turnover.py), it's who they used to be.
    once = 'formerly ' if person.get('left') else ''
    return f"{once}the {person['role']} at {person['place']['name']}" if person['staff'] else \
        f"{once}a regular at {person['place']['name']}"


def town_relation(person: dict, host_name: str) -> str:
    if person['kind'] == 'resident':
        return f"{host_name}'s neighbor from {person['neighborhood']}" if person['neighborhood'] else \
            f'someone {host_name} knows from around town'
    return f'{town_tie(person)}, someone {host_name} knows from around town'


def from_town(person: dict, host: str, host_name: str) -> dict:
    return {'key': person['key'], 'kind': 'town', 'name': person['name'], 'full': person['full'], 'host': host,
            'relation': town_relation(person, host_name), 'tie': town_tie(person)}


def known_by(connection, companion: dict, now) -> list[dict]:
    """Everyone this companion could bring into a group: their circle, then townsfolk they know well."""
    host, host_name = f"{COMPANION}{companion['id']}", companion['version']['name'].split()[0]
    found = [from_circle(row, host, host_name) for row in circle_people(connection, companion)]
    try:
        town = encounters.known(connection, companion, now)
    except Exception:  # noqa: BLE001 - no city to know anyone in: their circle is still there.
        town = []
    found += [from_town(person, host, host_name) for person in town
              if person['times'] >= KNOWS_TOWNSPERSON and not person.get('cast') and
              (person.get('left') or {}).get('why') != 'passed']  # Never someone who passed away.
    return found


def candidates(connection, members: list[dict], now) -> list[dict]:
    """People the companions in the group know who aren't in it, each once (the first member who knows them hosts)."""
    inside = {stay['member'] for stay in members}
    result, seen = [], set()
    for stay in members:
        companion = by_id(connection, stay['member'][len(COMPANION):]) if not is_guest(stay['member']) else None
        if companion is None:
            continue
        for person in known_by(connection, companion, now):
            if person['key'] not in inside and person['key'] not in seen:
                seen.add(person['key'])
                result.append(person)
    return result


def resolve(connection, key: str, host: str, now) -> dict | None:
    """The person a guest key names, as their host knows them now; None once they're gone (removed from the circle,
    the host deleted, a city changed)."""
    companion = host_companion(connection, {'host': host})
    if companion is None:
        return None
    return next((person for person in known_by(connection, companion, now) if person['key'] == key), None)


def lines(connection, person: dict, companion: dict) -> dict:
    """Their "Others see" line and their own "I see myself" lines (world/perception.py), by their person key, and
    for a townsperson how their personality sliders show (`behaviour`), with the user's edits on their profile."""
    if person['kind'] == 'town':
        data = network.city(connection, companion)
        sheet = encounters.resolve(data, person['key'], encounters.town_cast(connection, companion, data))
        if sheet:
            edited = town_personality.edited(connection, town_personality.town_of(companion), person['key'])
            return perception.sheet_lines(data, sheet, edited)
    return perception.seeded_lines(person['key'], perception.era_modern(companion['version']['definition']))


def who(connection, person: dict) -> str:
    """One line on who they are: their full name, who they are to the host, and their work."""
    text = f"{person['full']}, {person['relation']}"
    if person['kind'] == 'circle':
        row = optional(connection, 'SELECT * FROM circle_people WHERE id=?', (person['person_id'],))
        details = decode(row['details']) if row else {}
        if details.get('career'):
            text += f", {details['career'].lower()}" + (f" at {details['employer']}" if details.get('employer') else '')
    return text + '.'


def doing(connection, person: dict, companion: dict, now) -> str | None:
    """What they're doing right now, by their own day: a circle person's agenda, a townsperson's rules."""
    if person['kind'] == 'town':
        found = encounters.whereabouts_now(connection, companion, person['key'], now)
        return found['doing'] if found else None
    block = agenda.current(connection, person['timeline_id'], person['person_id'], now)
    if block:
        return 'asleep' if block['kind'] == 'sleep' else (block.get('label') or block['kind']).lower()
    hour = now.astimezone(zone(companion['version']['timezone'])).hour
    return 'asleep' if NIGHT[0] <= hour < NIGHT[1] else None


def asleep(connection, person: dict, companion: dict, now) -> bool:
    return doing(connection, person, companion, now) == 'asleep'


def sheet(connection, stay: dict, now) -> dict | None:
    """What a guest's own reply is built from: who they are, their lines, their host and what they're doing."""
    person = resolve(connection, stay['member'], stay['host'], now)
    companion = host_companion(connection, stay)
    if person is None or companion is None:
        return None
    found = lines(connection, person, companion)
    return {**person, 'who': who(connection, person), 'public': found['public'], 'private': found['private'],
            'behaviour': found.get('behaviour') or [],
            'host_name': companion['version']['name'].split()[0], 'timezone': companion['version']['timezone'],
            'doing': doing(connection, person, companion, now)}


def sheet_text(found: dict, text: str = SHEET) -> str:
    return text.format(who=found['who'], host=found['host_name'],
                       lines=perception.own_text(found['public'], found['private']))


# Visits ------------------------------------------------------------------------------------------

def visits(connection, group_id: str, key: str) -> int:
    return one(connection, 'SELECT COUNT(*) AS n FROM group_members WHERE group_id=? AND member=?',
               (group_id, key))['n']


def regular(connection, group_id: str, key: str) -> bool:
    return visits(connection, group_id, key) >= REGULAR_VISITS


def settled(connection, stay: dict) -> bool:
    """A member, a regular, or a guest the user kept: they stay however quiet the chat gets."""
    return not is_guest(stay['member']) or bool(stay['kept']) or regular(connection, stay['group_id'], stay['member'])


def passing(connection, members: list[dict]) -> list[dict]:
    return [stay for stay in members if not settled(connection, stay)]


def conversation_start(connection, group_id: str) -> str | None:
    """When this conversation began: the first message after the last quiet spell of QUIET or more."""
    rows = many(connection, "SELECT created_at FROM group_messages WHERE group_id=? AND status='complete' "
                'ORDER BY seq DESC LIMIT 400', (group_id,))
    start = None
    for row in rows:
        if start and parse(start) - parse(row['created_at']) >= QUIET:
            break
        start = row['created_at']
    return start


def replies_left(connection, group_id: str, key: str) -> int:
    since = conversation_start(connection, group_id)
    said = one(connection, "SELECT COUNT(*) AS n FROM group_messages WHERE group_id=? AND author=? AND "
               "status='complete' AND created_at>=?", (group_id, key, since or ''))['n']
    return max(GUEST_REPLIES - said, 0)


def resting(connection, members: list[dict], now) -> frozenset:
    """Guests who don't answer right now: asleep by their own day, or done talking this conversation."""
    result = set()
    for stay in members:
        if not is_guest(stay['member']):
            continue
        found = sheet(connection, stay, now)
        if found is None or found['doing'] == 'asleep' or not replies_left(connection, stay['group_id'], stay['member']):
            result.add(stay['member'])
    return frozenset(result)


# Pulling someone in ---------------------------------------------------------------------------------

def names_in(text: str, person: dict) -> bool:
    """Whether a message names them: their full name, or their first name written as a name (capitalised)."""
    first = person['name'].split()[0] if person['name'].split() else person['name']
    return any(word and re.search(rf'(?<![\w-]){re.escape(word)}(?![\w-])', text)
               for word in {person['full'], person['name'], first})


def last_pull_in(connection, group_id: str) -> str | None:
    row = one(connection, "SELECT MAX(joined_at) AS at FROM group_members WHERE group_id=? AND brought_by IS NOT NULL "
              "AND brought_by!='user'", (group_id,))
    return row['at']


def pull_in(connection, group_id: str, row: dict, members: list[dict], now) -> dict | None:
    """Whom a finished message brings into the chat, if anyone: someone it names that a companion here knows, pulled
    in by its writer when they know them, else by the first member who does. Seeded by the message."""
    chance = PULL_CHANCE[level(connection)]
    if not chance or row['author'] == 'app' or len(passing(connection, members)) >= MOST_GUESTS:
        return None
    gap, last = PULL_GAP[level(connection)], last_pull_in(connection, group_id)
    if last and now - parse(last) < gap:
        return None
    named = [person for person in candidates(connection, members, now) if names_in(row['text'], person)]
    if row['author'].startswith(COMPANION):
        mine = [{**person, 'host': row['author']} for person in candidates(connection, [{'member': row['author']}], now)
                if person['key'] in {item['key'] for item in named}]
        named = mine or named
    if not named:
        named = dropping_in(connection, members, now)
        chance *= DROP_IN_SHARE
    if not named or random.Random(f"guest-pull:{row['id']}").random() >= chance:
        return None
    person = named[0]
    companion = host_companion(connection, person)
    return None if companion is None or asleep(connection, person, companion, now) else person


def dropping_in(connection, members: list[dict], now) -> list[dict]:
    """People from a member's circle who have met the user and like them, who may drop in unasked; not once the user
    and that member have broken up (companion/life/breakups.py)."""
    from companion.life import breakups, their_people
    result = []
    for person in candidates(connection, members, now):
        companion = host_companion(connection, person) if person['kind'] == 'circle' else None
        if companion and not breakups.ended(connection, companion) and \
                person['person_id'] in their_people.met_people(connection, companion):
            result.append(person)
    return result


def history_line(connection, found: dict) -> str:
    """What a guest shares with the user outside this chat: nothing, unless they have met in person."""
    from companion.life import their_people
    if found.get('kind') == 'circle':
        return their_people.guest_line(connection, found['person_id'], found['timeline_id']) or NO_HISTORY
    return NO_HISTORY


# Slipping out ---------------------------------------------------------------------------------------

def drifting(connection, group_id: str, now) -> list[tuple[dict, str]]:
    """Guests who leave now, with the line that says so: anyone who is gone from their host's life, and passing
    guests once the chat has gone quiet."""
    members = many(connection, 'SELECT * FROM group_members WHERE group_id=? AND left_at IS NULL '
                   'ORDER BY joined_at, rowid', (group_id,))
    last = one(connection, "SELECT MAX(created_at) AS at FROM group_messages WHERE group_id=? AND status='complete'",
               (group_id,))['at']
    quiet = last is None or now - parse(last) >= QUIET
    result = []
    for stay in members:
        if not is_guest(stay['member']):
            continue
        if resolve(connection, stay['member'], stay['host'], now) is None:
            result.append((stay, f"{stay['name']} is no longer in the group."))
        elif quiet and not settled(connection, stay):
            result.append((stay, f"{stay['name']} slipped out of the group."))
    return result


def view(connection, stay: dict) -> dict | None:
    """What the people panel shows about a guest."""
    if not is_guest(stay['member']):
        return None
    count = visits(connection, stay['group_id'], stay['member'])
    companion = host_companion(connection, stay)
    return {'host_id': companion['id'] if companion else None, 'relation': stay['relation'] or '',
            'kept': bool(stay['kept']), 'regular': count >= REGULAR_VISITS, 'visits': count,
            'regular_after': REGULAR_VISITS, 'replies_left': replies_left(connection, stay['group_id'], stay['member']),
            'replies_each': GUEST_REPLIES}
