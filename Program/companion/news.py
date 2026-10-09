"""News travels (Feature Hit List #9): word of what happens in a companion's life gets around, one hop a day.

News is something big enough to share that happened in a companion's own life: a storyline beat that turned out
good or bad (never one of the storylines that are secrets) or a new chapter of their life. It starts with them and
spreads at the end of each day, for `SPREAD_DAYS` days, along who knows whom (memory/pairs.py): from a companion to
the people in their circle and the other companions they know, and from a circle person back to the companion and
to the rest of that circle. Whether one person passes it to another is the consequence engine's call (choice
`news:pass_on`, companion/consequences.py): likelier the closer the teller feels, from someone whose own news it is,
or from a gossip. The dice are seeded by the news, the pair and the day, so a day never changes after the fact.
So the sister hears Tuesday night, a coworker Wednesday, and a friend who is a companion too may text the user
about it Thursday, before the companion has said a word.

Everyone remembers who told them (`news_holders.told_by`). Saying it in a group counts too: everyone there hears
it (via `group`), from whoever said it. Openers (life/openers.py) and group replies (groups.py) pick from what each
person has heard. Secrets keep their own rules (companion/secrets.py) and never travel this way.

Only life events travel, never anything from the user's chats, so no companion can seem to have read the user's
chats with someone else; prompts also say they don't know whether the user has heard.
"""
from datetime import date, time, timedelta

from companion import consequences, secrets
from companion.characters import by_id
from companion.clock import parse, stamp, zone
from companion.database import decode, identifier, many
from companion.life import circle, storylines
from companion.memory import pairs

CHOICE = 'news:pass_on'
SPREAD_DAYS = 5
# A day's word gets around in the evening, their time.
EVENING = time(20, 0)
# How long heard news stays in a companion's chat context, and how much of it.
RECENT_DAYS = 14
CONTEXT_LIMIT = 5
# Between two circle people of the same companion, who are never worked out in memory/pairs.py.
CIRCLE_LEVEL = 2
TONES = ('good', 'bad')


# What counts as news --------------------------------------------------------------------------------------

def found(connection, companion: dict, now) -> list[dict]:
    """The companion's recent news: {source, text, happened_on}."""
    today = storylines.local_today(companion, now)
    since = (today - timedelta(days=RECENT_DAYS)).isoformat()
    result = []
    for item in storylines.visible(connection, companion, now, include_ended=True):
        if item['story'] in secrets.STORY_SECRETS:
            continue
        for index, beat in enumerate(item['beats']):
            if beat['tone'] in TONES and since <= beat['on'] <= today.isoformat():
                result.append({'source': f"storyline:{item['id']}:{index}", 'text': beat['text'].rstrip('.'),
                               'happened_on': beat['on']})
    for row in many(connection, 'SELECT * FROM life_chapters WHERE timeline_id=? AND undone_at IS NULL '
                    'AND started_on>=? AND started_on<=?', (companion['active_timeline_id'], since, today.isoformat())):
        result.append({'source': f"chapter:{row['id']}", 'text': row['title'].rstrip('.'),
                       'happened_on': row['started_on']})
    return result


def register(connection, companion: dict, now) -> None:
    """New news starts with the companion; a chapter's news follows its title and ends when it is undone."""
    key, timestamp = pairs.companion_key(companion['id']), stamp(now)
    current = {item['source']: item for item in found(connection, companion, now)}
    for item in current.values():
        news_id = identifier()
        added = connection.execute(
            'INSERT OR IGNORE INTO news (id, timeline_id, source, about, text, happened_on, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?)', (news_id, companion['active_timeline_id'], item['source'], key,
                                             item['text'], item['happened_on'], timestamp)).rowcount
        if added:
            hear(connection, news_id, key, None, 0, item['happened_on'], 'origin', timestamp)
    for row in many(connection, "SELECT * FROM news WHERE timeline_id=? AND status='active' AND source LIKE 'chapter:%'",
                    (companion['active_timeline_id'],)):
        item = current.get(row['source'])
        if item is None:
            connection.execute("UPDATE news SET status='ended' WHERE id=?", (row['id'],))
        elif item['text'] != row['text']:
            connection.execute('UPDATE news SET text=? WHERE id=?', (item['text'], row['id']))


def hear(connection, news_id: str, holder: str, told_by: str | None, hop: int, day: str, via: str, timestamp: str,
         message_id: str | None = None) -> bool:
    return connection.execute(
        'INSERT OR IGNORE INTO news_holders (news_id, holder, told_by, hop, heard_on, via, message_id, created_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (news_id, holder, told_by, hop, day, via, message_id, timestamp)).rowcount > 0


# Spreading ------------------------------------------------------------------------------------------------

class Ties:
    """Who each person could pass news to, and how close they feel, worked out once per sync."""

    def __init__(self, connection, now):
        self.connection, self.now, self.levels, self.near = connection, now, {}, {}

    def neighbours(self, key: str) -> list[str]:
        if key not in self.near:
            self.near[key] = sorted(self.find(key))
        return self.near[key]

    def find(self, key: str) -> list[str]:
        companion_id = pairs.companion_id(key)
        if companion_id:
            companion = by_id(self.connection, companion_id)
            if companion is None:
                return []
            people = [person['seed'] for person in circle.people(self.connection, companion['active_timeline_id'])]
            return people + pairs.known_companions(self.connection, companion, self.now)
        person = pairs.circle_person(self.connection, key)
        owner = person and pairs.owner_of(self.connection, person)
        if owner is None or person['status'] != 'active':
            return []
        rest = [other['seed'] for other in circle.people(self.connection, owner['active_timeline_id'])
                if other['seed'] != key]
        return [pairs.companion_key(owner['id']), *rest]

    def level(self, teller: str, listener: str) -> int:
        if (teller, listener) not in self.levels:
            found = pairs.closeness(self.connection, teller, listener, self.now)
            self.levels[teller, listener] = found if found is not None else CIRCLE_LEVEL
        return self.levels[teller, listener]


def passes(connection, ties: Ties, item: dict, teller: str, listener: str, day: str) -> bool:
    facts = {'closeness_a': ties.level(teller, listener), 'own': int(teller == item['about']),
             'gossip': int(secrets.gossips(connection, teller))}
    odds = consequences.odds(CHOICE, facts, {'name': 'they', 'a': 'them', 'b': ''})
    return consequences.roll(f"{item['id']}:{teller}>{listener}:{day}", odds) == 0


def ready_through(companion: dict, now) -> date:
    """The last day whose evening has come for the companion."""
    local = now.astimezone(zone(companion['version']['timezone']))
    return local.date() if local.time() >= EVENING else local.date() - timedelta(days=1)


def spread(connection, ties: Ties, item: dict, through: date, timestamp: str) -> int:
    """One hop a day: whoever had heard by the start of a day may pass it on that evening. Returns how many heard."""
    first = date.fromisoformat(item['happened_on'])
    day = date.fromisoformat(item['spread_through']) + timedelta(days=1) if item['spread_through'] else first
    last, count = min(through, first + timedelta(days=SPREAD_DAYS - 1)), 0
    while day <= last:
        rows = many(connection, 'SELECT holder, hop FROM news_holders WHERE news_id=? AND (heard_on<? OR hop=0) '
                    'ORDER BY hop, holder', (item['id'], day.isoformat()))
        heard = {row['holder'] for row in many(connection, 'SELECT holder FROM news_holders WHERE news_id=?',
                                               (item['id'],))}
        for row in rows:
            for listener in ties.neighbours(row['holder']):
                if listener not in heard and passes(connection, ties, item, row['holder'], listener, day.isoformat()):
                    hear(connection, item['id'], listener, row['holder'], row['hop'] + 1, day.isoformat(), 'word',
                         timestamp)
                    heard.add(listener)
                    count += 1
        connection.execute('UPDATE news SET spread_through=? WHERE id=?', (day.isoformat(), item['id']))
        day += timedelta(days=1)
    return count


def sync(connection, now) -> int:
    """Register every companion's new news and let it travel up to this evening. Rules only, no model."""
    ties, timestamp, count = Ties(connection, now), stamp(now), 0
    for row in many(connection, 'SELECT id FROM companions WHERE active_version_id IS NOT NULL ORDER BY id'):
        companion = by_id(connection, row['id'])
        register(connection, companion, now)
        through = ready_through(companion, now)
        for item in many(connection, "SELECT * FROM news WHERE timeline_id=? AND status='active' AND happened_on<=? "
                         'AND (spread_through IS NULL OR spread_through<?) ORDER BY happened_on, id',
                         (companion['active_timeline_id'], through.isoformat(), through.isoformat())):
            count += spread(connection, ties, item, through, timestamp)
    return count


# Reading ---------------------------------------------------------------------------------------------------

ACTIVE = "JOIN companions c ON c.active_timeline_id=n.timeline_id WHERE n.status='active'"


def heard(connection, holder: str, since: str, limit: int = CONTEXT_LIMIT) -> list[dict]:
    """News about someone else that this person heard since `since`, newest first, with who told them. Only news
    on its companion's active timeline: a forked or abandoned timeline's news stays where it was."""
    return many(connection, 'SELECT n.*, h.told_by, h.heard_on, h.hop, h.via FROM news n JOIN news_holders h '
                f'ON h.news_id=n.id AND h.holder=? {ACTIVE} AND n.about!=? AND h.heard_on>=? '
                'ORDER BY h.heard_on DESC, n.id LIMIT ?', (holder, holder, since, limit))


def who(connection, key: str | None, owner: str | None = None) -> str:
    """How a holder would name a person: "Ana (Kimberly's sister)" for a circle person, a companion by name."""
    if not key:
        return 'someone'
    if key == 'user':
        return 'the user'
    person = pairs.circle_person(connection, key)
    if person:
        found = pairs.owner_of(connection, person)
        if found and pairs.companion_key(found['id']) != owner:
            relation = circle.relation(circle.role_kind(person['role']), person.get('pronouns') or '')
            return f"{person['name']} ({secrets.first_name(found['version']['name'])}'s {relation})"
        return person['name']
    return secrets.person_name(connection, key) or 'someone'


def subject_name(connection, item: dict) -> str:
    return secrets.person_name(connection, item['about']) or 'someone'


def context_lines(connection, companion: dict, now) -> list[tuple[str, str]]:
    """A companion's 1:1 chat: news about other people they heard lately, and who told them."""
    key = pairs.companion_key(companion['id'])
    since = (storylines.local_today(companion, now) - timedelta(days=RECENT_DAYS)).isoformat()
    lines = []
    for item in heard(connection, key, since):
        teller = who(connection, item['told_by'], key)
        source = f'{teller} told you' if item['via'] == 'word' else f'{teller} said it in a group you are in'
        lines.append((f"news:{item['id']}", f"- Heard on {item['heard_on']} ({source}): {item['text']}."))
    return lines


def group_lines(connection, speaker: str, present: list[str], labels: dict[str, str], now) -> list[tuple[str, str]]:
    """The speaker's news in a group: what they have heard that someone here hasn't, and whose news it is."""
    holders = {}
    lines = []
    since = (now.date() - timedelta(days=RECENT_DAYS)).isoformat()
    for item in heard(connection, speaker, since):
        if item['id'] not in holders:
            holders[item['id']] = {row['holder'] for row in many(
                connection, 'SELECT holder FROM news_holders WHERE news_id=?', (item['id'],))}
        unaware = [secrets.label(connection, member, labels) for member in present
                   if member != speaker and member not in holders[item['id']] and member != item['about']]
        if not unaware:
            continue
        text = f"- You heard ({who(connection, item['told_by'], speaker)} told you): {item['text']}."
        if item['about'] in present:
            text += f" It is {secrets.label(connection, item['about'], labels)}'s news, so let them tell it."
        else:
            text += f" {secrets.names_text(unaware)} {'has' if len(unaware) == 1 else 'have'}n't heard yet."
        lines.append((f"news:{item['id']}", text))
    return lines


def witness(connection, message: dict) -> int:
    """A finished group message that tells someone's news: everyone there has heard it now, from whoever said it
    (the user too). Returns how many heard it this way."""
    author, present = message['author'], decode(message['present']) or []
    day = parse(message['created_at']).astimezone(pairs.timezone_of(connection)).date().isoformat()
    count = 0
    for item in many(connection, f'SELECT n.* FROM news n {ACTIVE}'):
        name = subject_name(connection, item)
        statement = {'keys': secrets.derived_keys(item['text'], [{'name': name}]), 'explicit': False,
                     'subjects': [{'key': item['about'], 'name': name}]}
        if not secrets.hits(statement, message['text'], author):
            continue
        for member in present:
            if member != author and hear(connection, item['id'], member, author, 1, day, 'group',
                                         message['created_at'], message['id']):
                count += 1
    return count


def listing(connection, companion: dict, now) -> list[dict]:
    """Today's "Word getting around": the companion's own recent news and who has heard it, in the order they did."""
    key = pairs.companion_key(companion['id'])
    since = (storylines.local_today(companion, now) - timedelta(days=RECENT_DAYS)).isoformat()
    result = []
    for item in many(connection, f'SELECT n.* FROM news n {ACTIVE} AND n.about=? AND n.happened_on>=? '
                     'ORDER BY n.happened_on DESC, n.id', (key, since)):
        rows = many(connection, 'SELECT * FROM news_holders WHERE news_id=? AND holder!=? ORDER BY heard_on, hop, '
                    'holder', (item['id'], key))
        result.append({'id': item['id'], 'text': item['text'], 'happened_on': item['happened_on'],
                       'heard': [{'name': who(connection, row['holder'], key), 'heard_on': row['heard_on'],
                                  'from': None if row['told_by'] == key else who(connection, row['told_by'], key),
                                  'companion_id': pairs.companion_id(row['holder'])} for row in rows]})
    return result


def read(database) -> list[dict]:
    from companion.characters import require_current
    now = database.clock.now()
    with database.connect(write=True) as connection:
        sync(connection, now)
        return listing(connection, require_current(connection), now)
