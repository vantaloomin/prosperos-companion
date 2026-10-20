"""Everyone gets older (Hit List #67): ages move on with the calendar.

Until v0.14 nobody's age moved: a companion's came from their words ("34.", "in her thirties") or a seed, a circle
member's and a partner's were stored once, and a townsperson's was seeded. Now each person has one stored birth date
(the `birth_dates` table), worked out once from the age they had when it was first needed and their birthday, so
nobody's age jumps on the upgrade, and from then on their age goes up on each birthday. Nothing here calls a model.

- A companion: from their looks sheet's age (companion/world/looks.py: the Looks age the user set, else their
  identity's words, else seeded) and their birthday (the form's, else seeded by their id). When the user writes
  another age or birthday, their date is worked out again from the new words, so the form always wins. "Keeps their
  age" (the definition's `keeps_age`, on the Character page) holds them at the age they are when it goes on, for
  characters who shouldn't age; turned off again, they go on from there. A sheet that reads as under 18 has no age drawn and never
  gets a date: ages are only ever read upward from a stored adult date, and the adult side keeps reading their own
  words (companion/world/intimacy.py), so getting older never changes what it allows.
- A circle member or a love-life partner: from the age their row stores, and `sync` keeps that stored age current,
  so everything that reads it (storylines, their partner's line, later life chapters) sees how old they are now.
  A partner who joined the circle shares their circle row's date.
- A townsperson: rebuilt from a seed, so nothing is stored for them; their seeded age is their age on the day the
  town started getting older (the town row), and they turn a year older on each seeded birthday after it.

Every age here is a real one. Rules about how far through life someone is (odds, life chapters, health, passing
away, retiring) read their life age instead (`companion_life_age`, `person_life_age`, `town_life_age`): the same for
a human, stretched for a long-lived kind (companion/world/lifespans.py), so an elf of 300 is 48 in human terms.

Milestone birthdays (30, 40, 50 ...) are bigger occasions (companion/life/occasions.py, composer.py) and go in the
scrapbook (companion/life/scrapbook.py).
"""
from calendar import isleap, monthrange
from datetime import date, timedelta

from companion.clock import stamp, zone
from companion.database import decode, encode, many, optional
from companion.world import generators, intimacy, lifespans, looks

ADULT = 18
FIRST_MILESTONE = 30
ORDINAL_ENDS = {1: 'st', 2: 'nd', 3: 'rd'}


# --- Dates ---

def seeded_birthday(seed: str) -> str:
    """A birthday as "MM-DD" seeded by an id (never 29 February), the way circle members' and companions' are."""
    return (date(2001, 1, 1) + timedelta(days=int(generators.unit(seed, 'birthday') * 365))).strftime('%m-%d')


def birthday_in(year: int, birthday: str) -> date:
    """The day a "MM-DD" birthday falls in a year; 29 February falls on the 28th in other years."""
    month, day = map(int, birthday.split('-'))
    if month == 2 and day == 29 and not isleap(year):
        day = 28
    return date(year, month, min(day, monthrange(year, month)[1]))


def born_from(age: int, birthday: str, today: date) -> date:
    """The birth date that makes someone `age` today with this birthday."""
    year = today.year - age - (birthday_in(today.year, birthday) > today)
    return birthday_in(year, birthday)


def age_on(born: date, birthday: str, day: date) -> int:
    return day.year - born.year - (birthday_in(day.year, birthday) > day)


def last_birthday(birthday: str, day: date) -> date:
    this_year = birthday_in(day.year, birthday)
    return this_year if this_year <= day else birthday_in(day.year - 1, birthday)


def milestone(age: int | None, lifespan: int | None = lifespans.HUMAN_LIFESPAN) -> bool:
    """30, 40, 50 ...: a birthday that is a bigger occasion; 100, 150, 200 ... for a long-lived kind
    (companion/world/lifespans.py)."""
    return lifespans.milestone(age, lifespan)


def ordinal(number: int) -> str:
    """40th, 21st, 52nd."""
    end = 'th' if 10 <= number % 100 <= 20 else ORDINAL_ENDS.get(number % 10, 'th')
    return f'{number}{end}'


# --- Stored dates ---

def stored(connection, kind: str, key: str) -> dict | None:
    return optional(connection, 'SELECT * FROM birth_dates WHERE kind=? AND person_key=?', (kind, key))


def keep(connection, kind: str, key: str, age: int, birthday: str, today: date, now, written: int | None = None) -> dict:
    """Store (or work out again) someone's birth date from the age they are today; `written` is the age their words
    give when that differs (a companion whose birthday changed or who was held at an age), else `age`."""
    born = born_from(age, birthday, today)
    connection.execute(
        'INSERT INTO birth_dates (kind, person_key, born_on, birthday, from_age, anchored_on, held_age, created_at, '
        'updated_at) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?) ON CONFLICT(kind, person_key) DO UPDATE SET '
        'born_on=excluded.born_on, birthday=excluded.birthday, from_age=excluded.from_age, '
        'anchored_on=excluded.anchored_on, held_age=NULL, updated_at=excluded.updated_at',
        (kind, key, born.isoformat(), birthday, age if written is None else written, today.isoformat(), stamp(now),
         stamp(now)))
    return stored(connection, kind, key)


def age_from(row: dict, day: date) -> int:
    """Their age on a day by their stored date: never younger than the age it was worked out from, so a picture of a
    day before then reads the same as it always did."""
    return max(row['from_age'], age_on(date.fromisoformat(row['born_on']), row['birthday'], day))


# --- A companion ---

def written_age(companion_id: str, definition: dict) -> int | None:
    """The age their words and form give (companion/world/looks.for_companion), None when they read as under 18."""
    if intimacy.reads_as_minor(definition):
        return None
    age = looks.for_companion(companion_id, definition).get('age')
    return age if age and age >= ADULT else None


def own_birthday(companion_id: str, definition: dict) -> str:
    return definition.get('birthday') or seeded_birthday(companion_id)


def current(row: dict | None, age: int, birthday: str) -> bool:
    """Whether a companion's stored date still follows their form (the same age written, the same birthday)."""
    return bool(row) and row['from_age'] == age and row['birthday'] == birthday


def companion_age(connection, companion_id: str, definition: dict, day: date | None) -> int | None:
    """How old a companion is on a day. Before `sync` has stored their date, or right after the user wrote another
    age or birthday, it is the age written. Keeping their age, it is the age they were when the switch went on."""
    age = written_age(companion_id, definition)
    if age is None or connection is None or day is None:
        return age
    row = stored(connection, 'companion', companion_id)
    if not current(row, age, own_birthday(companion_id, definition)):
        return age
    if row['held_age']:  # Kept, or let go since the last `sync`, which carries on from here.
        return row['held_age']
    return age_from(row, day)


def turns_on(connection, companion_id: str, definition: dict, day: date) -> int | None:
    """The age a companion turns on a birthday by their stored date; None while they keep their age or before their
    date is stored or follows their form, so a birthday never counts an age it can't be sure of."""
    age = written_age(companion_id, definition)
    if age is None or lifespans.ageless(definition):
        return None
    row = stored(connection, 'companion', companion_id)
    if not current(row, age, own_birthday(companion_id, definition)):
        return None
    return age_on(date.fromisoformat(row['born_on']), row['birthday'], day)


def sync_companion(connection, companion: dict, now) -> None:
    """Store a companion's date the first time, and again when their form changed. "Keeps their age" holds them at
    the age they are when it goes on (Iris, v0.14: a lock that made a 40-year-old 39 again read as a bug); turned off
    again, they carry on from that age with no jump."""
    definition = companion['version']['definition']
    age = written_age(companion['id'], definition)
    if age is None:
        return
    today = now.astimezone(zone(companion['version']['timezone'])).date()
    birthday, row = own_birthday(companion['id'], definition), stored(connection, 'companion', companion['id'])
    if row and row['from_age'] == age and row['birthday'] != birthday:
        # Only the birthday changed: they stay the age they are now.
        row = keep(connection, 'companion', companion['id'], row['held_age'] or age_from(row, today), birthday, today,
                   now, written=age)
    elif not current(row, age, birthday):
        row = keep(connection, 'companion', companion['id'], age, birthday, today, now)
    held = lifespans.ageless(definition)  # "Keeps their age", or a kind that doesn't age.
    if held and not row['held_age']:
        connection.execute("UPDATE birth_dates SET held_age=? WHERE kind='companion' AND person_key=?",
                           (age_from(row, today), companion['id']))
    elif not held and row['held_age']:
        keep(connection, 'companion', companion['id'], row['held_age'], birthday, today, now, written=age)


def age_line(connection, companion_id: str, definition: dict, day: date | None) -> str | None:
    """"You are 35 now; you turned 35 on 3 March.", for their own prompt once a birthday has taken them past the age
    their words give, so the model doesn't answer with the age written (A/B: /mnt/project-files/companion-ages-ab).
    None until then."""
    age, written = companion_age(connection, companion_id, definition, day), written_age(companion_id, definition)
    if age is None or day is None:
        return None
    # A long-lived kind (companion/world/lifespans.py) also hears their age in human terms (A/B:
    # /mnt/project-files/companion-lifespan-ab), always, so the model plays an elf of 312 as someone in mid-life.
    span = companion_lifespan(connection, definition)
    life = lifespans.life_age(age, span) if span not in (None, lifespans.HUMAN_LIFESPAN) else None
    if age == written:
        return f'You are {age}, about {life} in human terms.' if life is not None else None
    birthday, row = own_birthday(companion_id, definition), stored(connection, 'companion', companion_id)
    # Held at an age, the birthday that made them that age; otherwise their latest one.
    turned = birthday_in(date.fromisoformat(row['born_on']).year + age, birthday) \
        if row['held_age'] else last_birthday(birthday, day)
    said = f"You are {age} now; you turned {age} on {turned.day} {turned.strftime('%B')}"
    return f'{said} (about {life} in human terms).' if life is not None else f'{said}.'


# --- Life age ---

def city_of(connection, definition: dict) -> dict | None:
    from companion.life import outings
    return outings.city_data(connection, definition) if connection is not None else None


def companion_lifespan(connection, definition: dict) -> int | None:
    """How long a companion lives: the Character page's pick, else their kind's (from their words) where they are."""
    return lifespans.sheet_lifespan(definition, city_of(connection, definition))


def companion_life_age(connection, companion_id: str, definition: dict, day: date | None) -> int | None:
    """How far through life a companion is in human terms (`companion_age` for a human)."""
    return lifespans.life_age(companion_age(connection, companion_id, definition, day),
                              companion_lifespan(connection, definition))


def person_lifespan(connection, details: dict, definition: dict | None = None) -> int | None:
    """How long a circle member or partner lives, from their row: their own pick, else their kind's (a relative of
    a long-lived companion shares their kind) in the companion's city."""
    kind, own = details.get('own_kind') or details.get('folk'), details.get('lifespan')
    if own is None and kind in (None, '', lifespans.HUMAN):
        return lifespans.HUMAN_LIFESPAN
    return lifespans.lifespan_of(kind, city_of(connection, definition) if definition else None, own)


def person_life_age(connection, details: dict, real: int | None, definition: dict | None = None) -> int | None:
    return lifespans.life_age(real, person_lifespan(connection, details, definition))


def person_kind(details: dict, data: dict | None = None) -> dict:
    """A circle member's kind for their page (lifespans.described): the user's pick, else the app's."""
    found = details.get('folk') or lifespans.HUMAN  # The app's pick.
    return lifespans.described(details.get('own_kind') or found, details.get('lifespan'), stored_age(details), data) \
        | {'found': found}


def persona_life_age(connection, persona: dict, definition: dict | None = None) -> int:
    """The user's life age: their kind as picked on the Persona page, else read from their words the way a
    companion's is."""
    data = city_of(connection, definition) if definition else None
    return lifespans.life_age(persona.get('age') or 0, lifespans.persona_lifespan(persona, data)) or 0


def persona_age_text(connection, persona: dict, definition: dict | None = None) -> str:
    """The user's age for the prompt's persona lines: "312 (an elf; about 49 in human terms)" for a kind picked on the
    Persona page or read from their words (A/B: findings/ab-r2-expecting.md, decide-screens), else just the age."""
    data = city_of(connection, definition) if definition else None
    kind, age = lifespans.persona_kind(persona, data), persona.get('age')
    span = lifespans.persona_lifespan(persona, data)
    if not age or (kind == lifespans.HUMAN and span == lifespans.HUMAN_LIFESPAN):
        return str(age or '')
    if span is None:
        return f"{age} (doesn't age)"
    label = lifespans.kinds(data)[kind]['label'].lower() if kind != lifespans.HUMAN else 'human'
    article = 'an' if label[:1] in 'aeiou' else 'a'
    life = lifespans.life_age(age, span)
    return f'{age} ({article} {label}; about {life} in human terms)' if life != age else f'{age} ({article} {label})'


def town_life_age(connection, sheet: dict, day: date, data: dict | None = None) -> int:
    """A townsperson's life age: their kind comes with their sheet (from their name group)."""
    return lifespans.life_age(town_age(connection, sheet, day), lifespans.lifespan_of(sheet.get('folk'), data))


# --- The circle, partners and the town ---

def person_age(connection, kind: str, key: str, day: date) -> int | None:
    """The age a circle member or partner is (or turns) on a day by their stored date, None before it is stored."""
    row = stored(connection, kind, key)
    return age_on(date.fromisoformat(row['born_on']), row['birthday'], day) if row else None


def stored_age(details: dict) -> int | None:
    age = details.get('age')
    return age if isinstance(age, int) and age >= ADULT else None


def sync_people(connection, companion: dict, now) -> int:
    """Store a date for each circle member and partner of a companion's timeline the first time, and keep the age
    their row stores current. Returns how many ages moved on."""
    today = now.astimezone(zone(companion['version']['timezone'])).date()
    ages = sync_circle(connection, companion['active_timeline_id'], today, now)
    return sum(ages.values()) + sync_partners(connection, companion['active_timeline_id'], ages, today, now)


def sync_circle(connection, timeline_id: str, today: date, now) -> dict[str, int]:
    """Each circle member's age today by their date, written to their row when it moved on: {id: 1 if it moved}."""
    from companion.life import circle
    moved = {}
    for person in circle.people(connection, timeline_id, include_removed=True):
        details = decode(person['details'])
        if (age := stored_age(details)) is None or details.get('late'):
            continue  # Someone who passed away (companion/life/loss.py) stays the age they were.
        row = stored(connection, 'circle', person['id']) or keep(connection, 'circle', person['id'], age,
                                                                circle.birthday(person['id']), today, now)
        now_age = age_from(row, today)
        if now_age != age:
            connection.execute('UPDATE circle_people SET details=? WHERE id=?',
                               (encode({**details, 'age': now_age}), person['id']))
        moved[person['id']] = int(now_age != age)
    return moved


def sync_partners(connection, timeline_id: str, circle_ids, today: date, now) -> int:
    """Partners' ages: a partner in the circle goes by their circle date, one outside it by their own."""
    moved = 0
    for partner in many(connection, 'SELECT id, person_id, details FROM love_partners WHERE timeline_id=? AND '
                        'ended_on IS NULL', (timeline_id,)):
        details = decode(partner['details'])
        if (age := stored_age(details)) is None:
            continue
        kind, key = ('circle', partner['person_id']) if partner['person_id'] in circle_ids else ('partner', partner['id'])
        row = stored(connection, kind, key) or keep(connection, kind, key, age, seeded_birthday(key), today, now)
        if (now_age := age_from(row, today)) != age:
            connection.execute('UPDATE love_partners SET details=? WHERE id=?',
                               (encode({**details, 'age': now_age}), partner['id']))
            moved += 1
    return moved


def town_began(connection) -> date | None:
    row = stored(connection, 'town', '')
    return date.fromisoformat(row['anchored_on']) if row else None


def town_age(connection, sheet: dict, day: date) -> int:
    """A townsperson's age on a day: their seeded age on the day the town started getting older, a year more for each
    of their seeded birthdays since. A townsperson with a row of their own (one who became someone) goes by it."""
    if row := stored(connection, 'town', sheet['key']):
        return age_from(row, day)
    return aged(sheet, day, town_began(connection))


def aged(sheet: dict, day: date, began: date | None) -> int:
    """A townsperson's age on a day, from the day the town started getting older (`town_began`): for the paper and
    town couples (companion/world/paper.py, couples.py), which have that day but no connection."""
    # A newcomer (companion/world/turnover.py) was their seeded age the day they arrived in town.
    if began is not None and sheet.get('arrived'):
        began = max(began, date.fromisoformat(sheet['arrived']))
    if began is None or day <= began:
        return sheet['age']
    born = born_from(sheet['age'], seeded_birthday(sheet['seed']), began)
    return max(sheet['age'], age_on(born, seeded_birthday(sheet['seed']), day))


def sync(connection, now) -> int:
    """Rules only, a few times an hour (companion/life/simulation.py `spread_news`): the town's start, every
    companion's date and their people's ages. Returns how many ages moved on."""
    if town_began(connection) is None:
        connection.execute("INSERT OR IGNORE INTO birth_dates (kind, person_key, born_on, birthday, from_age, "
                           "anchored_on, created_at, updated_at) VALUES ('town', '', ?, '', 0, ?, ?, ?)",
                           (now.date().isoformat(), now.date().isoformat(), stamp(now), stamp(now)))
    from companion.characters import by_id
    moved = 0
    for row in many(connection, 'SELECT id FROM companions WHERE active_version_id IS NOT NULL AND '
                    'active_timeline_id IS NOT NULL'):
        companion = by_id(connection, row['id'])
        sync_companion(connection, companion, now)
        moved += sync_people(connection, companion, now)
    return moved


def milestones_between(connection, companion: dict, low: date, high: date) -> list[dict]:
    """The milestone birthdays in a stretch of time, theirs and their circle's: [{date, text}] for the scrapbook
    (companion/life/scrapbook.py), "Dana turned 40", "Dana's mom Ruth turned 60"."""
    from companion.life import circle
    definition, name = companion['version']['definition'], companion['version']['definition']['name']
    people = [(own_birthday(companion['id'], definition), name,
               lambda day: turns_on(connection, companion['id'], definition, day), low,
               companion_lifespan(connection, definition))]
    # Someone who joined the circle later (a grandparent added in v0.15) has no milestones from before they did.
    people += [(circle.birthday(person['id']), f"{name}'s {circle.said(person['role'], definition)} {person['name']}",
                lambda day, key=person['id']: person_age(connection, 'circle', key, day),
                max(low, date.fromisoformat(person['created_at'][:10])) if person['created_at'] else low,
                person_lifespan(connection, decode(person['details']) or {}, definition))
               for person in circle.people(connection, companion['active_timeline_id'])]
    found = []
    for birthday, who, age_of, since, span in people:
        for year in range(low.year, high.year + 1):
            day = birthday_in(year, birthday)
            if since <= day <= high and milestone(age := age_of(day), span):
                found.append({'date': day.isoformat(), 'text': f'{who} turned {age}'})
    return found
