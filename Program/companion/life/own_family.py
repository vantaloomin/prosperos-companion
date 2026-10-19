"""Companions' own babies (v0.15 Room to Grow, #73): a friendship companion and their own partner start a family.

Births and growing families (companion/life/families.py) gave babies to the circle and left out the companion's own
partner. Now a companion who is not the user's romance, married to or living with the partner they met
(companion/life/love_life.py) or the spouse their sheet names, can have a baby with them, decided by rules on a
Monday like every other pregnancy in the circle: whether they want children (`wants`, from Wanting children,
companion/life/parenthood.py), the Growing families slider, how old they are, married or living together. A romance
companion's family is with the user, never a partner's.

How the child comes is the app's call, seeded from the pair (`route`): one of them expecting (whoever can, by their
pronouns and age), or adopting a newborn (a pair where nobody can carry, and now and then any pair in a modern city);
an older city takes in a baby to raise. It runs as a storyline like a pregnancy in the circle (`expecting`, or
`adopting`): the news with the month, something in the middle from the banks (world/data/families.json
`own_expecting`, `own_adopting`), "any day now", then the baby with their name, all told to the user as a friend
would. The child joins `circle_children` as the companion's own (`whose` 'companion', the partner as `parent_id`)
and grows up with ages.py; updates come from the parent's side (`own_baby`, `own_toddler`, `own_child`).

Being a parent changes their days, seen from outside: parental leave from work after the baby comes (`leave_days`,
read by companion/life/work.py), baby things and then childcare out of their money (`purchases`,
companion/life/money.py), a naming day at home where a best
friend is asked to be the godparent (companion/life/big_days.py `naming`), and now and then an evening out with their
partner while the user babysits (`babysitting`, asked in a first text, a plain yes or no in the user's first reply).

Children are words only, as in v0.14: never in pictures, never in Matchlight, and with the adult side of life on
nothing about them reaches a chat prompt, the godparent day is called off and nobody is asked to babysit.
"""
from datetime import date, datetime, timedelta

from companion.clock import stamp, zone
from companion.database import decode, identifier, many, optional
from companion.life import ages, circle, families, steps
from companion.world import generators, intimacy, looks

WHOSE = 'companion'  # circle_children.whose for the companion's own child.
AGES = (24, 44)  # The companion's age while starting a family; whoever carries is 44 at most.
# Each year's chance of a baby at the usual pace, by how the pair lives, and how wanting children moves it.
YEARLY = {'married': 0.28, 'together': 0.12}
WANTING = {'yes': 1.6, 'someday': 0.6, 'no': 0.0}
ADOPT = 0.12  # A pair in a modern city who could carry adopting instead.
SPOUSES = {'wife', 'husband', 'spouse'}  # A partner the sheet names as married.
# Weeks away from work after the baby comes: the one who carried or a parent adopting, else the other parent.
LEAVE_WEEKS = {'carrying': 14, 'adopting': 12, 'partner': 2}
LEAVE = 'Parental leave'
# What a baby costs as a share of a month's take-home: the things before they come, then childcare each month
# once leave is over, until school (half of it theirs, the partner pays the rest).
THINGS, CHILDCARE, SCHOOL = 0.35, 0.09, 5
UPDATE = 1 / 3  # Each week's chance of an update about their own child, at the usual pace.
# Babysitting: each week's chance, at the usual pace, that they ask the user to watch the child for an evening
# (from three months old until 13), for a Saturday about a week or two on.
BABYSIT = 1 / 9
BABYSIT_FROM, BABYSIT_HOURS = 90, ('19:00', '23:00')
ASK_HOURS = (10, 21)
TOLD_DAYS = 14
STATUSES = ('planned', 'asked', 'yes', 'no', 'done', 'called_off')
EX = 'ex'  # The partner's role once they split up (companion/life/love_life.py).


# Who could start a family ---------------------------------------------------------------------------------------------

def wants(connection, companion: dict, now=None) -> str:
    """'yes', 'someday' or 'no' for children: Wanting children's answer (companion/life/parenthood.py), the user's
    pick on the Character page first, else their description, else seeded (recorded with `now`)."""
    from companion.life import parenthood
    return parenthood.wants(connection, companion, now)


def theirs(connection, companion: dict) -> bool:
    """Whether this companion can have a family with a partner of their own: an adult who isn't the user's romance."""
    definition = companion['version']['definition']
    if intimacy.reads_as_minor(definition) or not companion.get('active_timeline_id'):
        return False
    return definition.get('relationship') != 'romance' or steps.apart(connection, companion) == 'ended'


def pair(connection, companion: dict) -> dict | None:
    """{person, how ('married' or 'together')} for the partner they live with or married, else None."""
    from companion.life import love_life
    if not theirs(connection, companion):
        return None
    timeline_id = companion['active_timeline_id']
    for found in love_life.partners(connection, timeline_id):
        if found['secret'] or not found['person_id']:
            continue
        states = love_life.lived(connection, companion, found)
        how = 'married' if 'married' in states else 'together' if 'living together' in states else None
        person = optional(connection, "SELECT * FROM circle_people WHERE id=? AND status='active'",
                          (found['person_id'],))
        if how and person:
            return {'person': person, 'how': how}
    for person in circle.people(connection, timeline_id):
        if person['role'] in SPOUSES and decode(person['details']).get('sheet'):
            return {'person': person, 'how': 'married'}
    return None


def own_children(connection, timeline_id: str) -> list[dict]:
    return many(connection, "SELECT * FROM circle_children WHERE timeline_id=? AND whose=? AND status!='ended' "
                'ORDER BY born_on', (timeline_id, WHOSE))


def age_now(connection, companion: dict, day: date) -> int | None:
    return ages.companion_age(connection, companion['id'], companion['version']['definition'], day)


def ready(connection, companion: dict, day: date) -> dict | None:
    """The pair, when they could start expecting or adopting on this day: the right age, not already waiting for a
    baby, fewer than three, and a year and a half since the last."""
    found = pair(connection, companion)
    age = age_now(connection, companion, day)
    if not found or age is not None and not AGES[0] <= age <= AGES[1]:
        return None
    children = own_children(connection, companion['active_timeline_id'])
    if any(child['status'] == 'expected' for child in children) or len(children) >= families.MOST_CHILDREN or any(
            date.fromisoformat(child['born_on']) + families.SPACING > day for child in children):
        return None
    return found


def expect(connection, companion: dict, world, day: date, pace: float, now) -> int:
    """The news of their own baby this week (rolled on its Monday, like the circle's)."""
    found = ready(connection, companion, day) if pace else None
    want = WANTING[wants(connection, companion, now)] if found else 0.0
    if not want:
        return 0
    timeline_id, person = companion['active_timeline_id'], found['person']
    seed = f"own-family:{timeline_id}:{person['id']}"
    if generators.unit(seed, 'expecting', day.isoformat()) >= YEARLY[found['how']] * pace * want / 52:
        return 0
    told_on = day + timedelta(days=int(generators.unit(seed, 'told-on', day.isoformat()) * 7))
    if told_on > families.local_today(companion, now):
        return 0
    era = families.era_of(connection, companion['version']['definition'])
    how = route(connection, companion, person, f'{seed}:{told_on.isoformat()}', era, told_on)
    story = 'adopting' if how == 'adopting' else 'expecting'
    if families.told(connection, timeline_id, story, person['id'], told_on):
        return 0
    start(connection, companion, world, person, how, told_on, now)
    return 1


def route(connection, companion: dict, person: dict, seed: str, era: str, day: date) -> str:
    """'carrying' (the companion is expecting), 'partner' (their partner is) or 'adopting': whoever of them can carry
    (she/her, or they/them half the time) and is 44 or younger; adopting when nobody can, and now and then in a
    modern city."""
    details = decode(person['details'])
    mine = looks.pronouns_of(companion['version']['definition'])
    ages_ = {'carrying': age_now(connection, companion, day), 'partner': details.get('age')}
    able = [who for who, said in (('carrying', mine), ('partner', details.get('pronouns')))
            if (said == 'she/her' or said == 'they/them' and generators.unit(seed, f'can:{who}') < 0.5)
            and (ages_[who] is None or ages_[who] <= AGES[1])]
    if not able or era == 'modern' and generators.unit(seed, 'adopt') < ADOPT:
        return 'adopting'
    return generators.pick(seed, 'carrier', able)


# Their baby on the way -------------------------------------------------------------------------------------------------

def plan(connection, companion: dict, world, person: dict, how: str, day: date) -> dict:
    """The beats with their days, the baby and the day they arrive, decided now."""
    timeline_id, definition = companion['active_timeline_id'], companion['version']['definition']
    seed, rng = f"own-family:{timeline_id}:{person['id']}:{day.isoformat()}", generators.unit
    weeks = 20 + int(rng(seed, 'home') * 21) if how == 'adopting' else 24 + int(rng(seed, 'due') * 7)
    born = day + timedelta(weeks=weeks)
    halfway = day + timedelta(weeks=7 + int(rng(seed, 'halfway') * 6))
    soon = born - timedelta(days=3 + int(rng(seed, 'soon') * 6))
    sex = 'she/her' if rng(seed, 'sex') < 0.49 else 'he/him'
    name = families.baby_name(definition, world, seed, sex, families.taken_names(connection, companion))
    era = families.era_of(connection, definition)
    middle = generators.pick(seed, 'middle', middle_lines(how, era))
    month = born.strftime('%B')
    child = {'name': name, 'pronouns': sex}
    stages = [{**families.stage(day, *news(how, month, era)), 'due': month, 'route': how},
              families.stage(halfway, middle['text'], middle['share']),
              families.stage(soon, *any_day(how, era)),
              families.stage(born, *arrived(how, child, era))]
    return {'stages': stages, 'child': child, 'born': born}


def middle_lines(how: str, era: str) -> list[dict]:
    """The bank's lines for the months between: who is carrying, and what fits their city's era."""
    if how == 'adopting':
        lines = [line for line in families.bank()['own_adopting'] if era == 'modern' or not line.get('modern')]
    else:
        wrong = 'them' if how == 'carrying' else 'me'
        lines = [line for line in families.bank()['own_expecting'] if line.get('carrying') != wrong]
    return families.fitting(lines, era)


def news(how: str, month: str, era: str) -> tuple[str, str]:
    """The news, and the companion's share of it (in an older city's voice there)."""
    old = families.older(era)
    if how == 'adopting' and era != 'modern':
        return (f'{{name}} and {{a}} will take in a baby to raise, around {month}.',
                f'{{a}} and I are to take in a baby to raise, around {month}, we think. My heart is so full.' if old else
                f'{{a}} and I are taking in a baby to raise. around {month}, we think. my heart is so full')
    if how == 'adopting':
        return (f'{{name}} and {{a}} are adopting a baby, who should come home around {month}.',
                f"so {{a}} and I have been keeping something quiet... we're adopting!! a baby, home around {month} "
                "if all goes well")
    if how == 'carrying':
        return (f'{{name}} and {{a}} are expecting a baby, due in {month}.',
                f'I have news, and I can hardly write it straight: I am expecting! {{a}} and I are to have a baby in '
                f'{month}.' if old else f"okay. sit down. I'm pregnant!! {{a}} and I are having a baby, due in {month}")
    return (f'{{name}} and {{a}} are expecting a baby, due in {month}.',
            f'{{a}} is expecting! We are to have a baby in {month}, and I cannot stop smiling.' if old else
            f"{{a}} is pregnant!!! we're having a baby. due in {month}. I can't stop smiling")


def any_day(how: str, era: str = 'modern') -> tuple[str, str]:
    """'Any day now', and the share; an older city has no agency match or hospital bag."""
    old = families.older(era)
    if how == 'adopting' and old:
        return (OLD_COMING, 'Any day now our little one comes to us. I cannot sit still.')
    if how == 'adopting':
        return ('{name} and {a} heard there is a match, and the baby comes home any day now.',
                "there's a match. a baby. ours. any day now and I can't sit still")
    if old:
        return (OLD_DUE, 'Any day now. The cradle is made up, the midwife knows to come, and we jump at every knock.')
    return ('The baby is due any day now, and {name} and {a} have the bag packed by the door.',
            "any day now. the bag's been packed by the door for two weeks and we keep checking it")


# 'Any day now' in an older city (A/B: companion-e2e-v15/findings/ab-ownbabies.md).
OLD_COMING = 'Word has come that the baby {name} and {a} are to raise will come home within the week, any day now.'
OLD_DUE = 'The baby is due any day now, and {name} and {a} have the cradle made up and the midwife ready to send for.'


def arrived(how: str, child: dict, era: str = 'modern') -> tuple[str, str]:
    she, old = child['pronouns'] == 'she/her', families.older(era)
    girl, here, word = ('girl', "SHE'S HERE", 'daughter') if she else ('boy', "HE'S HERE", 'son')
    if how == 'adopting':
        return (f"{{name}} and {{a}} brought the baby home: a {girl} named {child['name']}.",
                f"{child['name']} is home with us. Our {word}. I keep just looking at {'her' if she else 'him'}." if old
                else f"{child['name']} is home. our {word}. I keep just looking at {'her' if she else 'him'}")
    return (f"{{name}} and {{a}} had the baby: a {girl} named {child['name']}.",
            f"{'She' if she else 'He'} is here! {child['name']}. {{a}} and I are worn out and quite in love." if old else
            f"{here}. {child['name']}. {{a}} and I are so tired and so in love")


def start(connection, companion: dict, world, person: dict, how: str, day: date, now) -> dict:
    found, timeline_id = plan(connection, companion, world, person, how, day), companion['active_timeline_id']
    story = 'adopting' if how == 'adopting' else 'expecting'
    storyline_id = families.insert_story(connection, timeline_id, story, person['id'], found['stages'], day, now)
    child = found['child']
    connection.execute(
        'INSERT INTO circle_children (id, timeline_id, parent_id, storyline_id, name, pronouns, title, born_on, status, '
        "whose, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'family', ?, 'expected', ?, ?, ?)",
        (identifier(), timeline_id, person['id'], storyline_id, child['name'], child['pronouns'],
         found['born'].isoformat(), WHOSE, stamp(now), stamp(now)))
    return found


def how_of(connection, child: dict) -> str:
    """How their child came: 'carrying', 'partner' or 'adopting' (from the storyline's first beat)."""
    row = optional(connection, 'SELECT stages FROM storylines WHERE id=?', (child['storyline_id'],))
    return (decode(row['stages'])[0].get('route') if row else None) or 'partner'


# Being a parent --------------------------------------------------------------------------------------------------------

def leave_days(connection, companion: dict, start: date, end: date) -> dict[str, str]:
    """{local date: 'Parental leave'} for the weeks after a baby of theirs came (companion/life/work.py days_off)."""
    result = {}
    if not companion.get('active_timeline_id'):
        return result
    for child in own_children(connection, companion['active_timeline_id']):
        first = date.fromisoformat(child['born_on'])
        day = max(start, first)
        last = min(end, first + timedelta(weeks=LEAVE_WEEKS[how_of(connection, child)]) - timedelta(days=1))
        while child['status'] == 'born' and day <= last:
            result[day.isoformat()] = LEAVE
            day += timedelta(days=1)
    return result


def broken_night(connection, timeline_id: str, day: date) -> dict | None:
    """The body state a broken night with their own baby leaves (companion/life/agenda.py `day_facts`), as for the
    pair's own (companion/life/our_child.py): by Family life, until the youngest sleeps through on a seeded day, a
    third as often after that while a toddler; never on an easy life, nor on a night the child is at their ex's."""
    from companion.life import our_child
    level = our_child.level(connection)
    kids = [child for child in own_children(connection, timeline_id) if child['status'] == 'born' and
            child['born_on'] < day.isoformat() and families.age_of(child, day) < 3] if our_child.BROKEN[level] else []
    if not kids or not with_them(connection, timeline_id, kids[-1], day - timedelta(days=1)):
        return None
    youngest, seed = kids[-1], f"own-nights:{kids[-1]['id']}"
    low, high = our_child.SLEEPS[level]
    sleeps = date.fromisoformat(youngest['born_on']) + timedelta(days=low + int(generators.unit(seed, 'sleeps') *
                                                                                 (high - low)))
    chance = our_child.BROKEN[level] / (3 if day >= sleeps else 1)
    if generators.unit(seed, 'night', day.isoformat()) >= chance:
        return None
    return {'state': 'tired', 'because': 'after a broken night'}


def with_them(connection, timeline_id: str, child: dict, day: date) -> bool:
    """Whether their child sleeps at theirs this night: always while together; after a split, by the pattern
    (companion/life/custody.py `own_line`): every night but some weekends, every other week, or weekends only."""
    from companion.life import custody, our_child
    person = optional(connection, 'SELECT * FROM circle_people WHERE id=?', (child['parent_id'],))
    if person is None or person['role'] != EX or not (decode(person['details']) or {}).get('co_parent'):
        return True
    companion = our_child.companion_of(connection, timeline_id)
    pattern = custody.OWN_PATTERNS[custody.own_outcome(connection, companion, person)['picked']] if companion else \
        'with_them'
    if pattern == 'shared':  # A week each, turn and turn about.
        return day.isocalendar().week % 2 == 0
    return pattern == 'with_them' or day.weekday() >= 5


def purchases(connection, timeline_id: str, start: date, day: date) -> list[dict]:
    """Baby things a month before a baby of theirs comes, then their half of childcare each month from the end of
    leave until school (companion/life/money.py household)."""
    from companion.life import money
    definition = definition_of(connection, timeline_id)
    found = money.profile(definition) if definition else None
    if not found:
        return []
    month, result = money.monthly_share(found), []
    for child in own_children(connection, timeline_id):
        born = date.fromisoformat(child['born_on'])
        things = born - timedelta(days=30)
        if start <= things <= day:
            result.append({'text': f"bought baby things for {child['name']}", 'date': things.isoformat(), 'spend': '',
                           'cost': round(month * THINGS, 2), 'for': 'baby'})
        care = born + timedelta(weeks=LEAVE_WEEKS[how_of(connection, child)])
        while care <= min(day, ages.birthday_in(born.year + SCHOOL, born.strftime('%m-%d'))):
            if care >= start and child['status'] == 'born':
                result.append({'text': f"paid their half of {child['name']}'s childcare", 'date': care.isoformat(),
                               'spend': '', 'cost': round(month * CHILDCARE, 2), 'for': 'childcare'})
            care += timedelta(days=30)
    return result


def definition_of(connection, timeline_id: str) -> dict | None:
    row = optional(connection, 'SELECT v.definition FROM timelines t JOIN companions c ON c.id=t.companion_id JOIN '
                   'character_versions v ON v.id=c.active_version_id WHERE t.id=?', (timeline_id,))
    return decode(row['definition']) if row else None


def news_on(child: dict, day: date, pace: float, era: str) -> tuple[str, str, str] | None:
    """(story, text, share) for an update about their own child on this day (families.news_on for the circle's)."""
    group = families.band(child, day)
    if not group or not pace:
        return None
    seed, first = f"child:{child['id']}", date.fromisoformat(child['born_on'])
    week = (day - first).days // 7
    if day.weekday() != int(generators.unit(seed, 'news-day', week) * 7) or \
            generators.unit(seed, 'update', week) >= UPDATE * pace:
        return None
    line = generators.pick(seed, f'update-line-{week}', families.fitting(families.bank()[f'own_{group}'], era))
    return 'baby_update', line['text'], line['share']


def naming_days(connection, companion: dict, low: date, high: date) -> list[dict]:
    """Their own baby's naming day at home, six to twelve weeks after they came, on a Saturday, for Big days in the
    circle: {key, date, child, parent_id, pronouns}."""
    result = []
    for child in own_children(connection, companion['active_timeline_id']):
        born = date.fromisoformat(child['born_on'])
        day = born + timedelta(days=42 + int(generators.unit(f"child:{child['id']}", 'naming') * 42))
        day += timedelta(days=(5 - day.weekday()) % 7)
        if child['status'] == 'born' and low <= day <= high:
            result.append({'key': f"naming:{child['id']}", 'date': day.isoformat(), 'child': child['name'],
                           'parent_id': child['parent_id'], 'pronouns': child['pronouns']})
    return result


def godparent(connection, timeline_id: str, child_id: str) -> bool:
    """Whether the user stood as this child's godparent at their naming day."""
    return bool(optional(connection, "SELECT id FROM big_days WHERE timeline_id=? AND source=? AND status='done' AND "
                         'with_user=1', (timeline_id, f'naming:{child_id}')))


def context_lines(connection, companion: dict, now) -> list[tuple[str, str]]:
    """Their own children for the 'children' lines, told to the companion, and babysitting asked or done. The caller
    (families.context_lines) leaves all of it out with the adult side on."""
    timeline_id, today = companion['active_timeline_id'], families.local_today(companion, now)
    result = []
    for child in families.born(connection, timeline_id, today):
        if child.get('whose') != WHOSE:
            continue
        word = {'she/her': 'daughter', 'he/him': 'son'}.get(child['pronouns'], 'child')
        other = f"your {child['parent_role']} {child['parent_name']}" if child['parent_status'] == 'active' else \
            child['parent_name']
        extra = f" The user is {child['name']}'s godparent." if godparent(connection, timeline_id, child['id']) else ''
        result.append((f"child:{child['id']}", f"- {child['name']} (your {word}, {families.how_old(child, today)}): "
                                                f"yours and {other}'s.{extra}"))
        if found := own_custody(connection, companion, child):  # Since they split up (companion/life/custody.py).
            result.append(found)
    return result + babysitting_lines(connection, companion, now)


def own_custody(connection, companion: dict, child: dict) -> tuple[str, str] | None:
    from companion.life import custody
    return custody.own_line(connection, companion, child)


# Babysitting -----------------------------------------------------------------------------------------------------------

def plan_asks(connection, companion: dict, day: date, pace: float, now) -> int:
    """On a Monday, now and then: an evening the user could babysit one of their children, a Saturday about a week or
    two on, while they and their partner go out. Asked later in a first text (`ask_due`)."""
    timeline_id = companion['active_timeline_id']
    if day.weekday() != 0 or not pace or families.withheld(connection) or not reachable(connection, companion) or \
            optional(connection, "SELECT id FROM babysitting WHERE timeline_id=? AND status IN ('planned', 'asked', "
                     "'yes')", (timeline_id,)):
        return 0
    for child in families.born(connection, timeline_id, day):
        old = (day - date.fromisoformat(child['born_on'])).days
        seed = f"babysit:{child['id']}"
        if child.get('whose') != WHOSE or child['parent_status'] != 'active' or child['parent_role'] == EX or \
                old < BABYSIT_FROM or not families.band(child, day) or generators.unit(seed, 'ask', day.isoformat()) >= BABYSIT * pace:
            continue
        evening = day + timedelta(days=12 if generators.unit(seed, 'when', day.isoformat()) < 0.5 else 5)
        if evening < families.local_today(companion, now) + timedelta(days=3):
            continue  # A catch-up after days away: too late to ask about that one.
        connection.execute(
            'INSERT OR IGNORE INTO babysitting (id, timeline_id, child_id, local_date, at_time, until_time, ask_on, '
            "status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'planned', ?, ?)",
            (identifier(), timeline_id, child['id'], evening.isoformat(), *BABYSIT_HOURS, day.isoformat(),
             stamp(now), stamp(now)))
        return 1
    return 0


def reachable(connection, companion: dict) -> bool:
    """The user lives near enough to come over and isn't broken up with them."""
    from companion.life import long_distance
    return steps.apart(connection, companion) != 'ended' and long_distance.far(connection, companion) is None


def follow(connection, companion: dict, today: date, now) -> None:
    """An evening that has passed: babysat with a yes, else it went by (someone else watched the child). Where a child
    lives once their parents split up is decided (companion/life/custody.py)."""
    from companion.life import custody
    custody.own_advance(connection, companion, now)
    for row in rows(connection, companion['active_timeline_id'], ('planned', 'asked', 'yes')):
        child = optional(connection, 'SELECT c.status, p.role FROM circle_children c LEFT JOIN circle_people p ON '
                         'p.id=c.parent_id WHERE c.id=?', (row['child_id'],))
        # An evening out is with their partner: called off once the two of them have split up.
        if child is None or child['status'] == 'ended' or child['role'] == EX or families.withheld(connection):
            mark(connection, row, 'called_off', now)
        elif row['local_date'] < today.isoformat():
            mark(connection, row, 'done' if row['status'] == 'yes' else 'called_off', now)


def rows(connection, timeline_id: str, statuses: tuple[str, ...] = STATUSES) -> list[dict]:
    marks = ','.join('?' * len(statuses))
    return many(connection, 'SELECT b.*, c.name AS child, c.parent_id FROM babysitting b JOIN circle_children c ON '
                f'c.id=b.child_id WHERE b.timeline_id=? AND b.status IN ({marks}) ORDER BY b.local_date',
                (timeline_id, *statuses))


def mark(connection, row: dict, status: str, now, **values) -> None:
    extra = ''.join(f', {column}=?' for column in values)
    connection.execute(f'UPDATE babysitting SET status=?, updated_at=?{extra} WHERE id=?',
                       (status, stamp(now), *values.values(), row['id']))


def partner_first(connection, row: dict) -> str:
    person = optional(connection, 'SELECT name FROM circle_people WHERE id=?', (row['parent_id'],))
    return person['name'].split()[0] if person else ''


def ask_due(connection, companion: dict, now: datetime) -> list:
    """The ask, as a first text, from the day it was planned until two days before the evening."""
    from companion.life.openers import Trigger
    from companion.life.their_people import clock_text
    if not families.ACTIVE or not companion.get('active_timeline_id') or families.withheld(connection):
        return []
    local = now.astimezone(zone(companion['version']['timezone']))
    if not ASK_HOURS[0] <= local.hour < ASK_HOURS[1]:
        return []
    soonest = (local.date() + timedelta(days=2)).isoformat()
    row = next((item for item in rows(connection, companion['active_timeline_id'], ('planned',))
                if item['ask_on'] <= local.date().isoformat() and item['local_date'] >= soonest), None)
    if row is None or not reachable(connection, companion):
        return []
    from companion.life import big_days
    day, partner = date.fromisoformat(row['local_date']), partner_first(connection, row)
    when, time = big_days.when_text(day, local.date()), clock_text(row['at_time'])
    reason = (f"You and {partner} would love an evening out on {day:%A} {day.day} {day:%B}, and you want to ask the "
              f"user, your close friend, to babysit {row['child']} at your place from {time}. Ask them in your own "
              "words, naming the day and the time; make it easy to say no.")
    template = generators.pick(f"babysit:{row['id']}", 'line', fitting_asks(connection, companion)).format(
        child=row['child'], partner=partner, day=when, time=time)
    return [Trigger(f"babysit:{row['id']}", 'babysit_ask', reason, template[:1].upper() + template[1:], (row['id'],))]


def fitting_asks(connection, companion: dict) -> list[str]:
    era = families.era_of(connection, companion['version']['definition'])
    unfit, wrong = families.UNFIT.get(era), 'modern' if families.older(era) else 'older'
    lines = families.bank()['babysit_ask']
    return [line for line in lines if not (unfit and unfit.search(line)) and
            wrong not in families.tags().get(line, ())] or lines


SETTLES = ('babysit_ask',)


def settle(connection, companion: dict, message: dict, trigger, timestamp: str) -> None:
    """The ask went out: waiting on the user's answer."""
    connection.execute("UPDATE babysitting SET status='asked', message_id=?, updated_at=? WHERE id=? AND "
                       "status='planned'", (message['id'], timestamp, trigger.sources[0]))


def note(connection, message: dict, companion: dict, timestamp: str) -> bool:
    """A plain yes or no in the user's first reply to the ask."""
    if not families.ACTIVE or message['role'] != 'user' or not companion.get('active_timeline_id'):
        return False
    said = steps.answer(message['text'])
    if said not in ('yes', 'no'):
        return False
    for row in rows(connection, companion['active_timeline_id'], ('asked',)):
        asked = optional(connection, 'SELECT seq FROM messages WHERE timeline_id=? AND (id=? OR origin_id=?)',
                         (message['timeline_id'], row['message_id'] or '', row['message_id'] or ''))
        if asked and asked['seq'] < message['seq'] and steps.first_turn(connection, message, asked['seq']):
            connection.execute('UPDATE babysitting SET status=?, answered_at=?, updated_at=? WHERE id=?',
                               (said, timestamp, timestamp, row['id']))
            return True
    return False


def babysitting_lines(connection, companion: dict, now) -> list[tuple[str, str]]:
    from companion.life import big_days
    from companion.life.their_people import clock_text
    timeline_id, local = companion['active_timeline_id'], now.astimezone(zone(companion['version']['timezone']))
    today, result = local.date(), []
    for row in rows(connection, timeline_id, ('asked', 'yes', 'no', 'done')):
        day = date.fromisoformat(row['local_date'])
        partner, child = partner_first(connection, row), row['child']
        when = 'tonight' if day == today else f"on {big_days.long_date(row['local_date'])}"
        hours = f"from {clock_text(row['at_time'])} to {clock_text(row['until_time'])}"
        if row['status'] == 'done' and (today - day).days <= TOLD_DAYS:
            line = (f"- On {big_days.long_date(row['local_date'])} the user babysat {child} while you and {partner} "
                    'went out. You were grateful.')
        elif day < today or row['status'] == 'done':
            continue
        elif row['status'] == 'yes' and day == today and row['at_time'] <= local.strftime('%H:%M') < row['until_time']:
            line = (f'- Right now the user is at your place babysitting {child} while you and {partner} are out, '
                    f"until about {clock_text(row['until_time'])}.")
        elif row['status'] == 'yes':
            line = f'- The user is babysitting {child} at your place {when} {hours} while you and {partner} go out.'
        elif row['status'] == 'no':
            line = (f"- The user can't babysit {child} {when}, and that's fine with you: you'll find someone else. "
                    "Don't hold it against them.")
        else:
            line = (f'- You asked the user to babysit {child} {when} {hours} while you and {partner} go out; they '
                    "haven't said yet.")
        result.append((f"babysit:{row['id']}:{row['status']}", line))
    return result


def as_plans(connection, timeline_id: str, since: str) -> dict[str, list[dict]]:
    """The evenings out the user babysits for, by local date, in the shape own_plans.assign takes
    (companion/life/agenda.py)."""
    result = {}
    for row in rows(connection, timeline_id, ('yes', 'done')):
        if row['local_date'] >= since:
            result.setdefault(row['local_date'], []).append({'id': f"babysit:{row['id']}:{row['status']}",
                                                              'at_time': row['at_time'],
                                                              'babysit': {**row, 'partner': partner_first(connection, row)}})
    return result


def entry(plan: dict, block: dict, definition: dict) -> dict:
    """The agenda entry for their evening out: out with their partner while the user watches the child."""
    return {'summary': f"{definition['name']} went out for the evening with {plan['babysit']['partner']}.",
            'post': 'A night out. We remember how this works.', 'mood': 'happy', 'activity': 'date night',
            'place': {'id': '~evening-out', 'name': 'an evening out', 'kind': 'restaurant', 'city': '',
                      'neighborhood': ''},
            'with': None, 'weather': block.get('weather'), 'composer_version': 'babysit-1'}


def copy(connection, parent_id: str, new_id: str, ids: dict) -> None:
    """A fork keeps the evenings already answered for the children it copied (families.copy), by name and birthday."""
    children = {(row['name'], row['born_on']): row['id'] for row in many(
        connection, 'SELECT id, name, born_on FROM circle_children WHERE timeline_id=?', (new_id,))}
    for row in many(connection, 'SELECT b.*, c.name, c.born_on FROM babysitting b JOIN circle_children c ON '
                    "c.id=b.child_id WHERE b.timeline_id=? AND b.status IN ('yes', 'no', 'done')", (parent_id,)):
        child = children.get((row['name'], row['born_on']))
        if child:
            connection.execute(
                'INSERT OR IGNORE INTO babysitting (id, timeline_id, child_id, local_date, at_time, until_time, '
                'ask_on, status, message_id, answered_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '
                '?, ?, ?)', (identifier(), new_id, child, row['local_date'], row['at_time'], row['until_time'],
                             row['ask_on'], row['status'], ids.get(row['message_id']), row['answered_at'],
                             row['created_at'], row['updated_at']))
