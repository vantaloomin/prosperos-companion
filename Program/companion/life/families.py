"""Births and growing families (Hit List #70, v0.14 Years Go By): babies arrive in the circle and the companion
becomes an aunt, uncle or godparent.

A sibling, cousin, friend or coworker in the circle aged 24 to 42 may start expecting: a seeded roll each week, more
likely for a married sibling, at the pace of Realism > Their days > Growing families (`growing_families`, 0 none to
3 lots). A pregnancy runs as a storyline over months (companion/life/storylines.py `expecting`, which took over the
old one-line cousin_baby): the news with a due date, something halfway through, "any day now", then the birth with
the baby's name. Everything about it is decided by the seed the day the news comes, never by a model.

The baby joins the circle as a child (`circle_children`) the day they are born, with that birthday, and gets older
with it (companion/life/ages.py). A sibling's baby is the companion's niece or nephew, a close friend often asks the
companion to be the godparent, a cousin's or a coworker's baby is theirs. The companion babysits now and then and
hears how they are getting on (bank lines in world/data/families.json by age, storylines again), until they turn
13. A child's first birthday is a party at their parent's, a big day the companion goes to (companion/life/big_days.py
`first_birthdays`).

Children are words only. They are never circle_people, so nothing that reads the circle (the agenda, pictures, group
chats, Matchlight, love lives, the web of who knows whom) ever sees them; they are listed under their parent. With the
adult side of life on, nothing about them goes in a chat prompt (`withheld`), and no picture is made of words that
name one or their first birthday (`pictured`).

A companion's own baby with their partner, and children for the user and a companion, come with v0.15 (#73): the
companion's partner is never cast here.
"""
import json
import re
import string
from datetime import date, timedelta
from functools import cache

from companion.clock import stamp, zone
from companion.database import decode, encode, identifier, many, optional
from companion.life import ages, circle, pronouns
from companion.world import catalog, generators, intimacy

ACTIVE = True  # Off in most tests (tests/conftest.py), since new pregnancies would add storylines to unrelated ones.
LEVELS = ('none', 'now and then', 'true to life', 'lots')
USUAL = 2
PACE = (0.0, 0.5, 1.0, 1.7)
AGES = (24, 42)
# Each year's chance of expecting at the usual pace, by how the companion knows them.
YEARLY = {'married sibling': 0.22, 'sibling': 0.08, 'cousin': 0.12, 'close friend': 0.12, 'friend': 0.09,
          'coworker': 0.07}
SPACING = timedelta(days=548)  # After a baby, a year and a half before the next.
MOST_CHILDREN = 3
CATCH_UP_DAYS = 14
GODPARENT = 0.45  # A close friend asking the companion to be the godparent.
GROWN = 13  # Updates and babysitting stop here.
# Each week's chance, at the usual pace, of an update about a child and of babysitting them.
UPDATE = {'family': 1 / 5, 'friend': 1 / 14}
BABYSIT = 1 / 7
BABYSIT_FROM = 90  # Days old.
# The companion's own partner: their baby waits for v0.15.
PARTNERS = {'partner', 'wife', 'husband', 'girlfriend', 'boyfriend', 'fiancée', 'fiancé', 'spouse'}
FRIENDS = {'friend', 'new friend', 'roommate from years ago', 'neighbor'}
# A first birthday is a big day of its own (companion/life/big_days.py), so it is no longer a storyline beat.
FIRST_BIRTHDAY_BEAT = False
FIRST_BIRTHDAY = re.compile(r'\b(?:first|1st) (?:birthday|bday)\b', re.IGNORECASE)
STORIES = ('expecting', 'baby_update', 'babysat', 'first_birthday')
FIELDS = ('they', 'them', 'their', "they're", 'are', 'were', 'They', 'Their')


@cache
def bank() -> dict:
    return json.loads((catalog.DATA / 'families.json').read_text(encoding='utf-8'))


def level(connection) -> int:
    row = optional(connection, 'SELECT * FROM life_settings WHERE id=1') or {}
    return int(row.get('growing_families', USUAL))


def withheld(connection) -> bool:
    """With the adult side of life on, children stay out of chat prompts altogether (they stay on the screens)."""
    return intimacy.turned_on(connection)


def pictured(connection, timeline_id: str, texts) -> bool:
    """Whether a picture's words name a child in the circle or a first birthday: none is ever made of them."""
    text = ' '.join(str(item) for item in texts if item)
    if not text:
        return False
    if FIRST_BIRTHDAY.search(text):
        return True
    return any(re.search(rf'\b{re.escape(name)}\b', text) for name in names(connection, timeline_id))


def names(connection, timeline_id: str) -> set[str]:
    return {row['name'] for row in many(connection, "SELECT name FROM circle_children WHERE timeline_id=? AND "
                                        "status!='ended'", (timeline_id,))}


def hidden(connection, timeline_id: str) -> re.Pattern | None:
    """With the adult side on, what no chat context line may hold: a child's name or a first birthday (the context
    packet drops any line that does, companion/memory/context.py). None with it off."""
    if not withheld(connection):
        return None
    found = sorted(names(connection, timeline_id))
    return re.compile('|'.join([f'(?i:{FIRST_BIRTHDAY.pattern})', *(rf'\b{re.escape(name)}\b' for name in found)]))


def childs_day(connection, outing_ids) -> bool:
    """Whether any of these outings is a child's big day (companion/life/big_days.py marks it `no_photo`), however
    the words about it were phrased."""
    ids = [item for item in outing_ids if item]
    if not ids:
        return False
    marks = ','.join('?' * len(ids))
    return any(decode(row['place']).get('no_photo') for row in many(
        connection, f'SELECT place FROM outings WHERE id IN ({marks})', tuple(ids)))


# Who may be expecting ------------------------------------------------------------------------------

def kinship(person: dict) -> str | None:
    """How the companion knows someone who could have a baby, for YEARLY; None for anyone who can't here (their
    parents, their own partner, family who would be a generation off)."""
    kind, details = circle.role_kind(person['role']), decode(person['details'])
    if kind == 'sibling':
        return 'married sibling' if details.get('married') else 'sibling'
    if kind == 'cousin':
        return 'cousin'
    if kind in circle.OLD_FRIENDS:
        return 'close friend'
    if kind in FRIENDS or kind == 'longtime friend':
        return 'friend'
    if kind == 'coworker':
        return 'coworker'
    return None


def eligible(connection, timeline_id: str, people: list[dict], day: date) -> list[tuple[dict, str]]:
    """(person, kinship) for each circle member who could start expecting on this day."""
    dating = {row['person_id'] for row in many(connection, 'SELECT person_id FROM love_partners WHERE timeline_id=? '
                                               'AND ended_on IS NULL AND person_id IS NOT NULL', (timeline_id,))}
    busy = {person for row in expecting(connection, timeline_id, day) for person in decode(row['cast_ids'])}
    found = []
    for person in people:
        age, how = decode(person['details']).get('age'), kinship(person)
        if not how or person['role'] in PARTNERS or person['id'] in dating | busy or not isinstance(age, int) \
                or not AGES[0] <= age <= AGES[1]:
            continue
        theirs = children_of(connection, person['id'])
        if len(theirs) >= MOST_CHILDREN or any(date.fromisoformat(child['born_on']) + SPACING > day for child in theirs):
            continue
        found.append((person, how))
    return found


def expecting(connection, timeline_id: str, day: date) -> list[dict]:
    """Pregnancy storylines whose baby hasn't arrived by this day."""
    rows = many(connection, "SELECT * FROM storylines WHERE timeline_id=? AND story='expecting' AND status='running'",
                (timeline_id,))
    return [row for row in rows if decode(row['stages'])[-1]['on'] > day.isoformat()]


def children_of(connection, person_id: str) -> list[dict]:
    return many(connection, "SELECT * FROM circle_children WHERE parent_id=? AND status!='ended'", (person_id,))


# A pregnancy ---------------------------------------------------------------------------------------

def title(how: str, seed: str) -> str:
    """What the baby is to the companion: 'family' (a niece or nephew), 'godchild' or 'friend' (someone's baby)."""
    if how in ('married sibling', 'sibling'):
        return 'family'
    if how == 'close friend' and generators.unit(seed, 'godparent') < GODPARENT:
        return 'godchild'
    return 'friend'


def relation(title_: str, pronouns_: str) -> str | None:
    """'niece', 'nephew', 'goddaughter', 'godson', 'godchild', or None for a friend's baby."""
    she = pronouns_ == 'she/her'
    if title_ == 'family':
        return 'niece' if she else 'nephew'
    if title_ == 'godchild':
        return 'goddaughter' if she else 'godson'
    return None


def baby_name(definition: dict, world, seed: str, pronouns_: str, taken: set[str]) -> str:
    """A first name from their city's names for babies born now, else from the bank."""
    data = circle.city_data(definition, world) if world is not None else None
    for attempt in range(6):
        if data:
            given = generators.name(data, seed=f'{seed}:{attempt}', pronouns=pronouns_.split('/')[0], age=0)['given']
        else:
            given = generators.pick(f'{seed}:{attempt}', 'baby-name', bank()['names'][pronouns_.split('/')[0]])
        if given not in taken:
            return given
    return given


def plan(connection, companion: dict, world, person: dict, how: str, day: date) -> dict:
    """Everything about one pregnancy, decided now: the beats with their days, the baby and what they are to the
    companion."""
    seed = f"family:{companion['active_timeline_id']}:{person['id']}:{day.isoformat()}"
    rng = generators.unit
    born = day + timedelta(weeks=24 + int(rng(seed, 'due') * 7))
    due = born + timedelta(days=int(rng(seed, 'early') * 15) - 7)  # Babies keep their own time.
    halfway = day + timedelta(weeks=7 + int(rng(seed, 'halfway') * 6))
    soon = min(due, born) - timedelta(days=3 + int(rng(seed, 'soon') * 6))
    sex = 'she/her' if rng(seed, 'sex') < 0.49 else 'he/him'
    taken = {row['name'].split()[0] for row in circle.people(connection, companion['active_timeline_id'], True)}
    taken |= {row['name'] for row in many(connection, 'SELECT name FROM circle_children WHERE timeline_id=?',
                                          (companion['active_timeline_id'],))}
    name = baby_name(companion['version']['definition'], world, seed, sex, taken)
    kind = title(how, seed)
    middle = generators.pick(seed, 'middle', bank()['pregnancy'])
    child = {'name': name, 'pronouns': sex, 'title': kind}
    stages = [
        stage(day, *announced(how, due, kind, companion['version']['definition'])),
        stage(halfway, middle['text'], middle['share']),
        stage(soon, "{a}'s baby is due any day now, and {name} keeps checking for news.",
              'still no baby. I have checked my phone about four hundred times today'),
        stage(born, *arrived(child, kind, companion['version']['definition'])),
    ]
    return {'stages': stages, 'child': child, 'born': born}


def stage(on: date, text: str, share: str) -> dict:
    return {'on': on.isoformat(), 'text': text, 'share': share, 'tone': 'good'}


def announced(how: str, due: date, kind: str, definition: dict) -> tuple[str, str]:
    month = due.strftime('%B')
    text = f"{{name}}'s {{a_rel}} {{a}} is expecting a baby, due in {month}."
    if kind == 'family':
        return text, f'{{a}} is having a baby!!! due in {month}. I am going to be an {aunt(definition)}'
    if how == 'coworker':
        return text, f'{{a}} from work is having a baby, due in {month}. the office is already planning a shower'
    return text, f'{{a}} just told me they are having a baby!! due in {month}. I cried a little not gonna lie'


def aunt(definition: dict) -> str:
    """'aunt', 'uncle', or 'aunt or uncle or whatever I am' when their pronouns aren't known (they/them)."""
    found = (pronouns.forms(definition) or {}).get('they')
    return {'she': 'aunt', 'he': 'uncle'}.get(found, 'aunt. or uncle. a cool relative, anyway')


def arrived(child: dict, kind: str, definition: dict) -> tuple[str, str]:
    she = child['pronouns'] == 'she/her'
    girl = 'girl' if she else 'boy'
    text = f"{{a}} had the baby: a {girl} named {child['name']}."
    if kind == 'family':
        word = 'niece' if she else 'nephew'
        return (f"{text} {{name}} has a new {word}.",
                f"{child['name'].upper()} IS HERE. a little {girl}. I have a {word}!! I'm not crying you're crying")
    if kind == 'godchild':
        return (f"{text} {{a}} asked {{name}} to be {child['name']}'s godparent.",
                f"{{a}} had a baby {girl}, {child['name']}, and asked me to be the godparent. I said yes before they "
                'finished the sentence')
    return text, f"{{a}} had the baby! a {girl}, {child['name']}. everyone's doing great"


def start(connection, companion: dict, world, person: dict, how: str, day: date, now) -> None:
    found, timeline_id = plan(connection, companion, world, person, how, day), companion['active_timeline_id']
    storyline_id = insert_story(connection, timeline_id, 'expecting', person['id'], found['stages'], day, now)
    child = found['child']
    connection.execute(
        'INSERT INTO circle_children (id, timeline_id, parent_id, storyline_id, name, pronouns, title, born_on, status, '
        "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'expected', ?, ?)",
        (identifier(), timeline_id, person['id'], storyline_id, child['name'], child['pronouns'], child['title'],
         found['born'].isoformat(), stamp(now), stamp(now)))


def insert_story(connection, timeline_id: str, story: str, person_id: str, stages: list[dict], day: date, now) -> str:
    storyline_id = identifier()
    connection.execute(
        'INSERT INTO storylines (id, timeline_id, story, level, cast_ids, stages, started_on, status, created_at) '
        "VALUES (?, ?, ?, 0, ?, ?, ?, 'running', ?)",
        (storyline_id, timeline_id, story, encode([person_id]), encode(stages), day.isoformat(), stamp(now)))
    return storyline_id


def told(connection, timeline_id: str, story: str, person_id: str, day: date) -> bool:
    return bool(optional(connection, 'SELECT id FROM storylines WHERE timeline_id=? AND story=? AND started_on=? AND '
                         'cast_ids=?', (timeline_id, story, day.isoformat(), encode([person_id]))))


# Each day ------------------------------------------------------------------------------------------

def local_today(companion: dict, now) -> date:
    return now.astimezone(zone(companion['version']['timezone'])).date()


def advance(connection, companion: dict, world, now) -> int:
    """Rules only, with the agenda (companion/life/agenda.py): babies arrive, pregnancies start, and updates and
    babysitting come round, for the days since the last check (at most CATCH_UP_DAYS). Returns how many began."""
    timeline_id, today = companion['active_timeline_id'], local_today(companion, now)
    settle(connection, timeline_id, today, now)
    if not ACTIVE:
        return 0
    pace = PACE[level(connection)]
    people = circle.people(connection, timeline_id)
    begun = 0
    for offset in range(CATCH_UP_DAYS, -1, -1):
        day = today - timedelta(days=offset)
        if pace and day.weekday() == 0:
            begun += expect(connection, companion, world, people, day, pace, now)
        begun += child_news(connection, companion, people, day, pace, now)
    return begun


def settle(connection, timeline_id: str, today: date, now) -> None:
    """A baby whose day has come is born; one whose storyline was ended (by the user, or with their parent removed
    from the circle) never is."""
    for row in many(connection, "SELECT c.id, c.born_on, s.status FROM circle_children c LEFT JOIN storylines s ON "
                    "s.id=c.storyline_id WHERE c.timeline_id=? AND c.status='expected'", (timeline_id,)):
        if row['status'] != 'running':
            connection.execute("UPDATE circle_children SET status='ended', updated_at=? WHERE id=?",
                               (stamp(now), row['id']))
        elif row['born_on'] <= today.isoformat():
            connection.execute("UPDATE circle_children SET status='born', updated_at=? WHERE id=?",
                               (stamp(now), row['id']))


def expect(connection, companion: dict, world, people: list[dict], day: date, pace: float, now) -> int:
    """Pregnancies whose news comes this week (rolled on its Monday)."""
    timeline_id, begun = companion['active_timeline_id'], 0
    for person, how in eligible(connection, timeline_id, people, day):
        seed = f'family:{timeline_id}:{person["id"]}'
        if generators.unit(seed, 'expecting', day.isoformat()) >= YEARLY[how] * pace / 52:
            continue
        told_on = day + timedelta(days=int(generators.unit(seed, 'told-on', day.isoformat()) * 7))
        if told_on > local_today(companion, now) or told(connection, timeline_id, 'expecting', person['id'], told_on):
            continue
        start(connection, companion, world, person, how, told_on, now)
        begun += 1
    return begun


# Children ------------------------------------------------------------------------------------------

def born(connection, timeline_id: str, today: date, include_removed=False) -> list[dict]:
    """Children born by this day, oldest first; with their parent removed from the circle, only on request."""
    rows = many(connection, "SELECT c.*, p.name AS parent_name, p.role AS parent_role, p.status AS parent_status FROM "
                'circle_children c JOIN circle_people p ON p.id=c.parent_id WHERE c.timeline_id=? AND '
                "c.status='born' AND c.born_on<=? ORDER BY c.born_on, c.id",
                (timeline_id, today.isoformat()))
    return [row for row in rows if include_removed or row['parent_status'] == 'active']


def age_of(child: dict, day: date) -> int:
    born_on = date.fromisoformat(child['born_on'])
    return ages.age_on(born_on, born_on.strftime('%m-%d'), day)


def age_text(child: dict, day: date) -> str:
    """'3 weeks old', '7 months old', '2'."""
    days = (day - date.fromisoformat(child['born_on'])).days
    if days < 7:
        return 'a newborn'
    if days < 60:
        return f"{days // 7} weeks old"
    if (years := age_of(child, day)) < 1:
        return f"{days // 30} months old"
    return f'{years}'


def how_old(child: dict, day: date) -> str:
    """'a newborn', 'a baby, 7 months old', 'a child, 1 year old', 'a child, 6 years old'."""
    found = age_text(child, day)
    if not found.isdigit():
        return found if found == 'a newborn' else f'a baby, {found}'
    return f"a child, {found} year{'' if found == '1' else 's'} old"


def band(child: dict, day: date) -> str | None:
    """'baby', 'toddler' or 'child' for the bank; None once they are 13."""
    years = age_of(child, day)
    return 'baby' if years < 1 else 'toddler' if years < 4 else 'child' if years < GROWN else None


def fill_child(text: str, child: dict) -> str:
    """A bank line with the child's name and pronouns; {name}, {a} and {a_rel} stay for storylines.fill."""
    forms = pronouns.person(child['pronouns'])
    values = {'child': child['name'], **{key.replace("'", ''): value for key, value in forms.items()}}
    parts = []
    for literal, field, _spec, _conversion in string.Formatter().parse(text):
        parts.append(literal.replace('{', '{{').replace('}', '}}'))
        if field is not None:
            parts.append(values.get(field, f'{{{field}}}'))
    return ''.join(parts)


def child_news(connection, companion: dict, people: list[dict], day: date, pace: float, now) -> int:
    """An update, a babysitting evening or a first birthday on this day, at most one a day across the circle."""
    timeline_id = companion['active_timeline_id']
    local = {person['id']: decode(person['details']).get('local', True) for person in people}
    for child in born(connection, timeline_id, day):
        if child['parent_id'] not in local or child['born_on'] == day.isoformat():
            continue
        news = news_on(child, day, pace, bool(local[child['parent_id']]))
        if not news:
            continue
        if told(connection, timeline_id, news[0], child['parent_id'], day):
            return 0  # Already told on an earlier check.
        insert_story(connection, timeline_id, news[0], child['parent_id'],
                     [stage(day, fill_child(news[1], child), fill_child(news[2], child))], day, now)
        return 1
    return 0


def news_on(child: dict, day: date, pace: float, local: bool) -> tuple[str, str, str] | None:
    """(story, text, share) for what comes up about this child on this day, if anything."""
    seed, first = f"child:{child['id']}", date.fromisoformat(child['born_on'])
    if FIRST_BIRTHDAY_BEAT and day == ages.birthday_in(first.year + 1, first.strftime('%m-%d')):
        return ('first_birthday', "{name} went to {child}'s first birthday party at {a}'s.",
                "{child}'s first birthday today! there was cake everywhere. mostly on {child}")
    group = band(child, day)
    if not group or not pace:
        return None
    week = (day - first).days // 7
    weekday = int(generators.unit(seed, 'news-day', week) * 7)
    if day.weekday() != weekday:
        return None
    sits = child['title'] != 'friend' and local and (day - first).days >= BABYSIT_FROM
    if sits and generators.unit(seed, 'babysit', week) < BABYSIT * pace:
        line = generators.pick(seed, f'babysit-line-{week}', bank()[f'babysit_{group}'])
        return 'babysat', line['text'], line['share']
    chance = UPDATE['friend' if child['title'] == 'friend' else 'family'] * pace
    if generators.unit(seed, 'update', week) < chance:
        line = generators.pick(seed, f'update-line-{week}', bank()[f'{group}_update'])
        return 'baby_update', line['text'], line['share']
    return None


def first_birthdays(connection, companion: dict, low: date, high: date) -> list[dict]:
    """Children's first birthdays in a stretch of days, for Big days in the circle: {key, date, child, parent_id,
    parent, pronouns, relation}."""
    result = []
    for child in born(connection, companion['active_timeline_id'], high):
        first = date.fromisoformat(child['born_on'])
        day = ages.birthday_in(first.year + 1, first.strftime('%m-%d'))
        if low <= day <= high:
            result.append({'key': f"first-birthday:{child['id']}", 'date': day.isoformat(), 'child': child['name'],
                           'parent_id': child['parent_id'], 'parent': child['parent_name'],
                           'pronouns': child['pronouns'], 'relation': relation(child['title'], child['pronouns'])})
    return result


# What the screens and the chat see -----------------------------------------------------------------

def child_view(child: dict, day: date) -> dict:
    return {'id': child['id'], 'name': child['name'], 'pronouns': child['pronouns'], 'born_on': child['born_on'],
            'age': age_of(child, day), 'age_text': age_text(child, day),
            'relation': relation(child['title'], child['pronouns']), 'title': child['title']}


def for_circle(connection, companion: dict, now) -> dict[str, dict]:
    """{person id: {children, expecting}} for the people list: their children, and a due month while expecting."""
    timeline_id, today = companion['active_timeline_id'], local_today(companion, now)
    found = {}
    for child in born(connection, timeline_id, today, include_removed=True):
        found.setdefault(child['parent_id'], {'children': [], 'expecting': None})['children'].append(
            child_view(child, today))
    for row in expecting(connection, timeline_id, today):
        if row['started_on'] <= today.isoformat():
            person_id = decode(row['cast_ids'])[0]
            due = decode(row['stages'])[0]['text'].rsplit('due in ', 1)[-1].rstrip('.')
            found.setdefault(person_id, {'children': [], 'expecting': None})['expecting'] = due
    return found


def context_lines(connection, companion: dict, now) -> list[tuple[str, str]]:
    """The children in their circle for the chat context, told to the companion: "- Mia (your niece, 2 years old):
    your sister Ana's daughter." None with the adult side on."""
    if withheld(connection):
        return []
    today, result = local_today(companion, now), []
    for child in born(connection, companion['active_timeline_id'], today):
        what, whose = relation(child['title'], child['pronouns']), 'daughter' if child['pronouns'] == 'she/her' else 'son'
        lead = ', '.join(part for part in (f'your {what}' if what else '', how_old(child, today)) if part)
        result.append((f"child:{child['id']}", f"- {child['name']} ({lead}): your {child['parent_role']} "
                                                f"{child['parent_name']}'s {whose}."))
    return result


def copy(connection, parent_id: str, new_id: str, ids: dict, cutoff_date: str) -> None:
    """A fork's children: those whose storylines came with it (timelines.copy_storylines), by the copied storyline
    that has the same parent and day."""
    copies = {(row['started_on'], row['cast_ids']): row['id'] for row in many(
        connection, "SELECT id, started_on, cast_ids FROM storylines WHERE timeline_id=? AND story='expecting'",
        (new_id,))}
    for row in many(connection, 'SELECT c.*, s.started_on FROM circle_children c JOIN storylines s ON '
                    's.id=c.storyline_id WHERE c.timeline_id=?', (parent_id,)):
        person = ids.get(row['parent_id'])
        story = copies.get((row['started_on'], encode([person])))
        if person and story and row['started_on'] <= cutoff_date:
            connection.execute(
                'INSERT INTO circle_children (id, timeline_id, parent_id, storyline_id, name, pronouns, title, '
                'born_on, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (identifier(), new_id, person, story, row['name'], row['pronouns'], row['title'], row['born_on'],
                 row['status'], row['created_at'], row['updated_at']))
