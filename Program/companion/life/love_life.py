"""Their own love life (Hit List #65, v0.13 Life Together): companions date, move up the steps and split up, by rules.

A companion who isn't the user's romance (a friend, a mentor, family, anyone else) can meet someone: a life chapter
of the kind `relationship` (companion/life/chapters.py), picked by the consequence engine like a new job or a pet. The
new partner is a seeded new person who joins their circle (companion/life/circle.py) with a job, a weekly routine and a
diary of their own, so they turn up in the feed and in the companion's days like anyone else in their life. They tell
the user as a friend would: the chapter's first text, and later the steps and a breakup as news (`news_due`).

From there the pair moves up the same steps ladder as the user and a companion (companion/life/steps.py, `other` is
the partner's key 'love:<id>'): once enough time has passed at a step, the engine rolls how things go (choice
`love:next`): the next step, not yet (it rolls again some weeks later), or a breakup. Odds from the Their love life
slider (life_settings.love_life: 0 nothing new happens, 1 quiet, 2 true to life, 3 lots going on), the drama level,
how far along they are, their description and their mood lately, all under Hidden values ("Why it went this way").

A romance companion (the user's own) only has a love life of their own as decided by Vanta (2026-10-16, "Secret on
Drama"):
- an open relationship from their interests or description: they date like anyone else and always tell the user;
- on Drama (the drama level at soap opera), once the two of you are exclusive, the engine may decide they start
  seeing someone on the side (choice `love:secret`, once a month, about 1 in 50 with nothing else moving it: roughly
  one year in five; Vanta 2026-10-17), more likely on Lots going on, after the Life deck's "caught their eye" card or
  when they're restless, less on Quiet or when very close. Below soap opera there is no roll at all. It stays hidden (the partner never joins the visible circle) until it comes out: one of the user's other
  companions in the same city sees them together (Small world), or word gets around (news travelling). Then it ends,
  they know they hurt the user, and a rough patch opens (companion/life/rough_patches.py, cause `hidden_partner`).

The banks (world/data/love_life.json) say the partner with their own pronouns: {they}, {their}, "love{s}" (`line`).

Jealousy is never assumed: only an emotional trait the user built that speaks to it adds it to the chat line.
No model decides anything; the chat context's 'love' section tells the companion where things stand.
"""
import json
import random
import re
from datetime import date, timedelta
from functools import cache

from companion import consequences
from companion.clock import parse, stamp, zone
from companion.database import decode, encode, identifier, many, one, optional
from companion.errors import require
from companion.life import circle, pronouns, steps
from companion.world import catalog

# Off in tests unless a test turns it on (tests/conftest.py): a seeded partner adds circle people and first texts.
ACTIVE = True
FIRST_TEXTS = True
DEFAULT_LEVEL = 2
NEXT = 'love:next'
SECRET = 'love:secret'
CARD = 'caught-their-eye'
LADDER = 'romance'
OPEN = re.compile(r"\b(?:open relationships?|polyamor\w*|poly(?:amorous)?|non-?monogam\w*|ethically non-?monogamous|"
                  r"relationship anarch\w*)\b", re.IGNORECASE)
JEALOUS = re.compile(r'jealous|possessive|insecure|clingy', re.IGNORECASE)
# Days between rolls once a step's time has come, by slider level (quiet, true to life, lots).
WAIT = (60, 40, 25)
# A married pair is rolled again once a year (a split is rare by then).
SETTLED = 365
# A secret partner: the chance each week that it comes out, and that it quietly fizzles.
OUT_CHANCE = 0.07
FIZZLE_CHANCE = 0.02
# No new secret within half a year of the last one ending.
SECRET_HOLD = 180
# How long the chat still hears about a breakup, or a secret that came out; and about a step just reached.
TOLD_DAYS = 30
FRESH_DAYS = 2
# A step or a breakup is texted from the user's last visit on, so news from a catch-up after days away still reaches
# them, but not from further back than this (E2E v0.13: in a jump every step but one went untold).
CATCH_UP_DAYS = 14
# Date nights in the feed: the chance on any one day.
DATE_POST = 0.14
BY_STEP = {'dating': 'dating', 'exclusive': 'dating', 'love': 'dating', 'their_people': 'dating', 'key': 'dating',
           'moving_in': 'dating', 'engaged': 'engaged', 'married': 'married'}
ROLES = {'dating': {'she/her': 'girlfriend', 'he/him': 'boyfriend', 'they/them': 'partner'},
         'engaged': {'she/her': 'fiancée', 'he/him': 'fiancé', 'they/them': 'fiancé'},
         'married': {'she/her': 'wife', 'he/him': 'husband', 'they/them': 'spouse'}}
PARTNER_ROLES = {role for roles in ROLES.values() for role in roles.values()}


@cache
def bank() -> dict:
    return json.loads((catalog.DATA / 'love_life.json').read_text(encoding='utf-8'))


# Settings and who has a love life ---------------------------------------------------------------------------------

def level(connection) -> int:
    """The Their love life slider: 0 nothing new, 1 quiet, 2 true to life, 3 lots going on."""
    row = optional(connection, 'SELECT love_life FROM life_settings WHERE id=1')
    return row['love_life'] if row and row['love_life'] in range(4) else DEFAULT_LEVEL


def is_open(definition: dict) -> bool:
    text = ' '.join([*(definition.get('interests') or ()), *(definition.get('life_themes') or ()),
                     *(str(definition.get(key) or '') for key in ('identity', 'personality', 'background',
                                                                    'history_together'))])
    return bool(OPEN.search(text))


def mode(connection, companion: dict) -> str | None:
    """How this companion can have a love life of their own: 'free' (not the user's romance), 'open' (the user's
    romance, in an open relationship), 'secret' (the user's romance, on Drama, once exclusive), or None."""
    from companion.world import intimacy
    definition = companion['version']['definition']
    if intimacy.reads_as_minor(definition) or sheet_partner(connection, companion):
        return None
    if definition.get('relationship') != 'romance' or steps.apart(connection, companion) == 'ended':
        return 'free'  # A friend, or an ex (companion/life/breakups.py): free to date.
    if is_open(definition):
        return 'open'
    return 'secret' if steps.drama(connection) >= 3 and exclusive(connection, companion) else None


def exclusive(connection, companion: dict) -> bool:
    """The user and this companion are exclusive or further along (companion/life/steps.py)."""
    if steps.apart(connection, companion) == 'ended':
        return False
    rows = steps.reached(connection, companion['active_timeline_id'], LADDER)
    return any(steps.index_of(LADDER, row['step']) >= 1 for row in rows)


def may_catch_eye(connection, companion: dict) -> bool:
    """For the Life deck's "caught their eye" card: they could start seeing someone, and aren't now."""
    return bool(ACTIVE and companion.get('active_timeline_id') and level(connection) and mode(connection, companion)
                and not partners(connection, companion['active_timeline_id']))


def sheet_partner(connection, companion: dict) -> bool:
    """A partner the character sheet names (companion/life/named.py) is theirs already: no new love life then."""
    return any(row['role'] in PARTNER_ROLES and decode(row['details']).get('sheet')
               for row in circle.people(connection, companion['active_timeline_id']))


# Partners -------------------------------------------------------------------------------------------------------------

def key_of(partner: dict) -> str:
    return f"love:{partner['id']}"


def partners(connection, timeline_id: str, active: bool = True) -> list[dict]:
    ended = 'AND ended_on IS NULL ' if active else ''
    rows = many(connection, f'SELECT * FROM love_partners WHERE timeline_id=? {ended}ORDER BY met_on, created_at',
                (timeline_id,))
    return [{**row, 'details': decode(row['details'])} for row in rows]


def partner(connection, partner_id: str) -> dict:
    row = optional(connection, 'SELECT * FROM love_partners WHERE id=?', (partner_id,))
    require(row is not None, 'That partner was not found.', 404)
    return {**row, 'details': decode(row['details'])}


def first(name: str) -> str:
    return name.split()[0] if name.split() else name


def drawn_to(connection, companion: dict) -> set[str]:
    """The pronouns of people they could fall for, from their adult side's orientation when it is known."""
    from companion.world import intimacy, looks
    found = intimacy.for_companion(connection, companion['id'], companion['version']['definition']) or {}
    own = looks.pronouns_of(companion['version']['definition'])
    orientation = found.get('orientation') or ''
    everyone = {'she/her', 'he/him', 'they/them'}
    if own == 'they/them' or orientation not in ('straight', 'gay', 'lesbian'):
        return everyone
    other = 'he/him' if own == 'she/her' else 'she/her'
    return {own, 'they/them'} if orientation in ('gay', 'lesbian') else {other, 'they/them'}


def new_person(connection, companion: dict, world, seed: str) -> dict:
    """A seeded new person who could be their partner: an adult near their age they could be drawn to, from the
    city's own people when the world knows the city."""
    from companion.world import generators, looks
    definition, timeline_id = companion['version']['definition'], companion['active_timeline_id']
    data = circle.city_data(definition, world)
    age = looks.age_of(definition, companion['id'])
    wanted = drawn_to(connection, companion)
    taken = {row['name'] for row in circle.people(connection, timeline_id, include_removed=True)} | {definition['name']}
    used = first_names_in_use(connection, companion)
    person = None
    for attempt in range(24):
        here = f'{seed}:{attempt}'
        years = max(18, age + round(generators.unit(here, 'age') * 11) - 5)
        if data:
            member = generators.resident(data, seed=here, role='friend', age=years)
            person = circle.city_person(member, data, definition, None, timeline_id, set(taken))
        else:
            person = circle.assemble(here, 0, definition, None, set(taken), 'friend')
            person['details'] |= {'pronouns': generators.pick(here, 'pronouns', sorted(wanted)), 'age': years,
                                  'local': True}
        if person['details'].get('pronouns') in wanted and first(person['name']) not in used:
            break
    person['details'] = person['details'] | {'love': True}
    return person


def first_names_in_use(connection, companion: dict) -> set[str]:
    """First names a new partner should not share, so 'you and Tyler' is never two people: theirs, the user's other
    companions', their circle's (past people too) and their partners' (a secret one is not in the circle)."""
    timeline_id = companion['active_timeline_id']
    names = [row['name'] for row in circle.people(connection, timeline_id, include_removed=True)]
    names += [row['name'] for row in many(connection, 'SELECT name FROM love_partners WHERE timeline_id=?',
                                          (timeline_id,))]
    names += [decode(row['definition']).get('name') or '' for row in many(
        connection, 'SELECT v.definition FROM companions c JOIN character_versions v ON v.id=c.active_version_id')]
    return {first(name) for name in [*names, companion['version']['definition']['name']] if name.strip()}


def role_for(step_key: str, pronouns: str) -> str:
    return ROLES[BY_STEP.get(step_key, 'dating')].get(pronouns, 'partner')


def how_met(seed: str, their_pronouns: str | None) -> str:
    return line(random.Random(f'{seed}:met').choice(bank()['met']), '', their_pronouns)


def line(template: str, name: str, their_pronouns: str | None) -> str:
    """A bank line about the partner: their first name in {partner}, their pronouns in {they}, {their}, "love{s}"."""
    return template.format_map({'partner': name, **pronouns.person(their_pronouns)})


def told(template: str, found: dict) -> str:
    return line(template, first(found['name']), found['details'].get('pronouns'))


# Meeting someone: the life chapter (companion/life/chapters.py) -------------------------------------------------------

def plan(connection, companion: dict, world, day: date, seed: str) -> dict | None:
    """The `relationship` chapter, when it could happen: they have a love life they tell the user about, no partner
    now and the slider is above nothing new."""
    timeline_id = companion['active_timeline_id']
    if not level(connection) or mode(connection, companion) not in ('free', 'open') or \
            partners(connection, timeline_id):
        return None
    person = new_person(connection, companion, world, f'{seed}:love')
    name, them = person['name'], first(person['name'])
    how = how_met(seed, person['details'].get('pronouns'))
    share = line(random.Random(f'{seed}:share').choice(bank()['share_new']), them, person['details'].get('pronouns'))
    told = f'You started seeing {name}; you met {how}. It is early days: you are dating, nothing more yet.'
    return {'title': f"{first(companion['version']['definition']['name'])} started seeing {name}", 'told': told,
            'share': share, 'person': person, 'met': how}


def begin(connection, companion: dict, world, day: date, found: dict, now) -> dict:
    """The new partner joins their circle and the pair starts dating."""
    timeline_id = companion['active_timeline_id']
    person = found['person']
    person = {**person, 'role': role_for('dating', person['details'].get('pronouns', '')),
              'details': {**person['details'], 'closeness': 'close'}}
    rows = circle.people(connection, timeline_id, include_removed=True)
    ordinal = max((row['ordinal'] for row in rows), default=-1) + 1
    circle.insert(connection, timeline_id, [person], ordinal, now)
    row = one(connection, 'SELECT * FROM circle_people WHERE timeline_id=? AND ordinal=?', (timeline_id, ordinal))
    partner_id = insert(connection, companion, row['name'], {**person['details'], 'met': found['met']}, day, now,
                        person_id=row['id'])
    return {'partner': partner_id}


def insert(connection, companion: dict, name: str, details: dict, day: date, now, person_id: str | None = None,
           secret: bool = False, consequence_id: str | None = None) -> str:
    partner_id = identifier()
    connection.execute(
        'INSERT INTO love_partners (id, timeline_id, companion_id, person_id, name, details, secret, met_on, '
        'consequence_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (partner_id, companion['active_timeline_id'], companion['id'], person_id, name, encode(details), int(secret),
         day.isoformat(), consequence_id, stamp(now)))
    steps.insert_step(connection, companion['active_timeline_id'], LADDER, 'dating', day, 'start', stamp(now),
                      other=f'love:{partner_id}')
    return partner_id


def undo(connection, partner_id: str, now) -> None:
    """Take a partner back (the chapter undone, or the outcome changed): they leave the circle, their steps go."""
    found = partner(connection, partner_id)
    timestamp = stamp(now)
    connection.execute("UPDATE love_partners SET ended_on=COALESCE(ended_on, met_on), ended_how='undone' WHERE id=?",
                       (partner_id,))
    connection.execute('UPDATE relationship_steps SET undone_at=? WHERE timeline_id=? AND other=? AND undone_at IS NULL',
                       (timestamp, found['timeline_id'], key_of(found)))
    if found['person_id']:
        circle.set_status(connection, found['person_id'], 'removed', now)


# Moving up the steps, and splitting up ---------------------------------------------------------------------------------

def advance(connection, companion: dict, world, now) -> None:
    """Once a day: each partner's steps come due and are rolled, a secret may come out, and on Drama a secret may
    begin. Cheap: no model."""
    if not ACTIVE or not companion.get('active_timeline_id'):
        return
    today = steps.local_today(companion, now)
    for found in partners(connection, companion['active_timeline_id']):
        if found['secret']:
            secret_weeks(connection, companion, found, today, now)
        elif left_circle(connection, found):
            end(connection, found, 'removed', today)
        else:
            progress(connection, companion, found, today, now)
    maybe_secret(connection, companion, world, now)


def left_circle(connection, found: dict) -> bool:
    """The user removed their partner from the circle: the pair is over."""
    row = found['person_id'] and optional(connection, 'SELECT status FROM circle_people WHERE id=?',
                                          (found['person_id'],))
    return bool(row) and row['status'] == 'removed'


def where(connection, companion: dict, found: dict) -> tuple[int, steps.Step, steps.Step | None, date]:
    """(index, current step, next step or None, the day the current one was reached)."""
    rows = steps.reached(connection, companion['active_timeline_id'], LADDER, key_of(found))
    top = max((steps.index_of(LADDER, row['step']) for row in rows), default=0)
    reached = next((row['reached_on'] for row in rows if steps.index_of(LADDER, row['step']) == top), found['met_on'])
    following = steps.ROMANCE[top + 1] if top + 1 < len(steps.ROMANCE) else None
    return top, steps.ROMANCE[top], following, date.fromisoformat(reached)


def progress(connection, companion: dict, found: dict, today: date, now) -> None:
    """Every roll that has come due since the last step, in order: up a step, not yet, or a breakup."""
    lvl = level(connection)
    if not lvl:
        return
    for _ in range(24):
        top, _current, following, since = where(connection, companion, found)
        wanted = following.after[lvl - 1] if following else SETTLED
        gap = WAIT[lvl - 1] if following else SETTLED
        topic = following.key if following else 'settled'
        turn = 1
        while consequences.recorded(connection, subject_of(found, topic, turn), NEXT):
            turn += 1
        day = since + timedelta(days=wanted + (turn - 1) * gap)
        if day > today:
            return
        outcome = roll(connection, companion, found, top, following, topic, turn, day, now)
        if outcome['picked'] == 2:
            end(connection, found, 'split', day)
            return
        if outcome['picked'] == 0 and following:
            step_up(connection, found, following.key, day, stamp(now))


def subject_of(found: dict, topic: str, turn: int) -> str:
    return f"love:{found['id']}:{topic}:{turn}"


def roll(connection, companion: dict, found: dict, top: int, following, topic: str, turn: int, day: date, now) -> dict:
    from companion.memory import pairs
    definition = companion['version']['definition']
    facts = {'love_life': level(connection), 'drama': steps.drama(connection), 'step': top,
             'can_up': int(following is not None),
             'mood': consequences.total(connection, companion['active_timeline_id'],
                                        pairs.companion_key(companion['id']), 'mood', day.isoformat()),
             'sheet': {group for group in consequences.WORDS if consequences.sheet_has(definition, group)}}
    names = {'name': first(definition['name']), 'partner': first(found['name']), 'a': first(found['name']), 'b': '',
             'step': following.topic if following else 'staying married'}
    table = consequences.tables()[NEXT]
    return consequences.decide(connection, timeline_id=companion['active_timeline_id'], choice=NEXT,
                               subject=subject_of(found, topic, turn), facts=facts, names=names,
                               labels=[option['label'].format(**names) for option in table['options']],
                               day=day.isoformat(), timestamp=stamp(now))


def step_up(connection, found: dict, key: str, day: date, timestamp: str) -> None:
    steps.insert_step(connection, found['timeline_id'], LADDER, key, day, 'them', timestamp, other=key_of(found))
    if found['person_id'] and BY_STEP[key] != 'dating':
        pronouns = found['details'].get('pronouns', '')
        connection.execute('UPDATE circle_people SET role=?, revision=revision+1, updated_at=? WHERE id=?',
                           (role_for(key, pronouns), timestamp, found['person_id']))


def end(connection, found: dict, how: str, day: date, **values) -> None:
    """The pair is over: a breakup, the user removing them, or a secret that came out. An ex leaves the circle."""
    extra = ''.join(f', {column}=?' for column in values)
    connection.execute(f'UPDATE love_partners SET ended_on=?, ended_how=?{extra} WHERE id=? AND ended_on IS NULL',
                       (day.isoformat(), how, *values.values(), found['id']))
    if found['person_id'] and how == 'split':
        connection.execute("UPDATE circle_people SET role='ex', status='removed', revision=revision+1 WHERE id=?",
                           (found['person_id'],))


# A secret on Drama --------------------------------------------------------------------------------------------------------

def maybe_secret(connection, companion: dict, world, now) -> dict | None:
    """Once a month, on Drama, once exclusive with the user: the engine decides whether they start seeing someone on
    the side."""
    timeline_id = companion['active_timeline_id']
    if not level(connection) or mode(connection, companion) != 'secret' or partners(connection, timeline_id):
        return None
    today = steps.local_today(companion, now)
    last = optional(connection, 'SELECT MAX(ended_on) AS on_ FROM love_partners WHERE timeline_id=? AND secret=1',
                    (timeline_id,))
    if last and last['on_'] and (today - date.fromisoformat(last['on_'])).days < SECRET_HOLD:
        return None
    window = (today.toordinal() + random.Random(f'secret-day:{timeline_id}').randrange(30)) // 30
    subject = f'love:{timeline_id}:secret:{window}'
    if consequences.recorded(connection, subject, SECRET):
        return None
    outcome = decide_secret(connection, companion, subject, today, now)
    if outcome['picked'] != 1:
        return None
    return start_secret(connection, companion, world, outcome, today, now)


def decide_secret(connection, companion: dict, subject: str, today: date, now) -> dict:
    from companion.memory import closeness, pairs
    definition = companion['version']['definition']
    facts = {'love_life': level(connection), 'drama': steps.drama(connection),
             'card': int(card_lately(connection, companion, today)),
             'closeness': closeness.state(connection, companion, now)['level'],
             'mood': consequences.total(connection, companion['active_timeline_id'],
                                        pairs.companion_key(companion['id']), 'mood', today.isoformat()),
             'sheet': {group for group in consequences.WORDS if consequences.sheet_has(definition, group)}}
    names = {'name': first(definition['name']), 'a': 'someone', 'b': ''}
    table = consequences.tables()[SECRET]
    return consequences.decide(connection, timeline_id=companion['active_timeline_id'], choice=SECRET, subject=subject,
                               facts=facts, names=names,
                               labels=[option['label'].format(**names) for option in table['options']],
                               day=today.isoformat(), timestamp=stamp(now))


def start_secret(connection, companion: dict, world, outcome: dict, day: date, now) -> dict:
    """A secret partner: a seeded person who never joins the circle the user sees."""
    person = new_person(connection, companion, world, outcome['subject'])
    details = {key: person['details'].get(key) for key in ('pronouns', 'age', 'career', 'employer', 'neighborhood')}
    met = how_met(outcome['subject'], details.get('pronouns'))
    partner_id = insert(connection, companion, person['name'], {**details, 'met': met}, day, now, secret=True,
                        consequence_id=outcome['id'])
    return partner(connection, partner_id)


def card_lately(connection, companion: dict, today: date) -> bool:
    """The Life deck's "caught their eye" card came up in the last month (companion/life/deck.py)."""
    return bool(optional(connection, 'SELECT 1 FROM life_moments WHERE timeline_id=? AND card_id=? AND day>=?',
                         (companion['active_timeline_id'], CARD, (today - timedelta(days=30)).isoformat())))


def secret_weeks(connection, companion: dict, found: dict, today: date, now) -> None:
    """Each week a secret goes on, it may come out, or quietly fizzle. Seeded by the week, so it never changes."""
    met = date.fromisoformat(found['met_on'])
    week = 1
    while (day := met + timedelta(days=7 * week)) <= today:
        if random.Random(f"{found['id']}:out:{week}").random() < OUT_CHANCE:
            # On the day the app notices (after days away, the week's roll is in the past), as the rough patch is.
            comes_out(connection, companion, found, today, now)
            return
        if random.Random(f"{found['id']}:fizzle:{week}").random() < FIZZLE_CHANCE:
            end(connection, found, 'faded', day)
            return
        week += 1


def comes_out(connection, companion: dict, found: dict, day: date, now) -> None:
    """It comes out: another companion of the user's in the same city saw them together (Small world), or word got
    around (news travelling). They end it, and a rough patch opens with them at fault."""
    witness = witness_for(connection, companion, found)
    via = 'small_world' if witness else 'news'
    place = spot_for(connection, companion, found, day) if witness else ''
    end(connection, found, 'came_out', day, out_via=via, witness_id=witness, place=place)
    rough_patch(connection, companion, {**found, 'out_via': via}, now)


def witness_for(connection, companion: dict, found: dict) -> str | None:
    from companion.world import newcomers, paper
    data = newcomers.city_for(connection, companion['version']['definition'])
    others = [person['id'] for person in paper.companions_in(connection, data) if person['id'] != companion['id']]
    return random.Random(f"{found['id']}:witness").choice(others) if others else None


def spot_for(connection, companion: dict, found: dict, day: date) -> str:
    """Where they were seen: a place their own days took them that week, else somewhere around town."""
    rows = many(connection, "SELECT entry FROM life_agenda WHERE timeline_id=? AND subject='companion' AND "
                'entry IS NOT NULL AND local_date BETWEEN ? AND ? ORDER BY starts_at',
                (companion['active_timeline_id'], (day - timedelta(days=6)).isoformat(), day.isoformat()))
    places = sorted({place['name'] for row in rows if isinstance(place := (decode(row['entry']) or {}).get('place'),
                                                                   dict) and place.get('name')})
    return random.Random(f"{found['id']}:spot").choice(places) if places else 'a place across town'


def rough_patch(connection, companion: dict, found: dict, now) -> dict | None:
    """Rough patches and making up (companion/life/rough_patches.py) owns the falling-out; this is the cause."""
    try:
        from companion.life import rough_patches
    except ImportError:
        return None
    if 'hidden_partner' not in getattr(rough_patches, 'CAUSES', {}):
        return None
    name = first(found['name'])
    return rough_patches.consider(connection, companion, 'hidden_partner', f"hidden-partner:{found['id']}",
                                  f'the user found out you had been seeing {name} behind their back', now,
                                  shown=f"over you finding out they'd been seeing {name} behind your back")


# Words: the chat context, news and first texts ----------------------------------------------------------------------------

def describe(found: dict) -> str:
    details = found['details']
    parts = [str(details['age'])] if details.get('age') else []
    if details.get('career'):
        parts.append(str(details['career']).lower() + (f" at {details['employer']}" if details.get('employer') else ''))
    if details.get('pronouns'):
        parts.append(str(details['pronouns']))
    return f" ({', '.join(parts)})" if parts else ''


def on(day: str, today: date) -> str:
    """'on Wednesday 14 October 2026, 5 days ago', or 'today (...)' / 'yesterday (...)'."""
    text = when(day, today)
    return text if text.startswith(('today', 'yesterday')) else f'on {text}'


def when(day: str, today: date) -> str:
    """'today (Monday 19 October 2026)', 'yesterday (Sunday 18 October 2026)', 'Wednesday 14 October 2026, 5 days ago'."""
    found = date.fromisoformat(day)
    days = (today - found).days
    if days in (0, 1):
        return f"{'today' if days == 0 else 'yesterday'} ({found:%A} {steps.long_date(day)})"
    weekday = f'{found:%A} ' if days < 7 else ''
    return f'{weekday}{steps.long_date(day)}, {days} days ago'


def pair_text(connection, companion: dict, found: dict, today: date) -> str:
    """'Together 8 months, exclusive', from the pair's steps."""
    rows = steps.reached(connection, companion['active_timeline_id'], LADDER, key_of(found))
    if not rows:
        return 'Dating'
    top = max(steps.index_of(LADDER, row['step']) for row in rows)
    return steps.plain_text(LADDER, steps.ROMANCE[top], rows, today)


def jealous(definition: dict) -> bool:
    return any(JEALOUS.search(trait.get('name') or '') for trait in definition.get('emotional_traits') or [])


def partner_line(connection, companion: dict, found: dict, today: date) -> str:
    definition = companion['version']['definition']
    name, them = found['name'], first(found['name'])
    since = steps.long_date(found['met_on'])
    if found['secret']:
        return (f'- You have been secretly seeing {name}{describe(found)} on the side since {since}. The user does '
                f'not know. Keep it from them: never mention {them}, and if you are asked where you were, keep it '
                'vague.')
    standing = pair_text(connection, companion, found, today).lower()
    if mode(connection, companion) == 'open':  # Not an ex of the user's (their sheet still says romance).
        feeling = ('You still feel a pang of jealousy about the user seeing other people, as your nature is.'
                   if jealous(definition) else 'Neither of you is jealous about it.')
        return (f'- You and the user have an open relationship, and you are also seeing {name}{describe(found)} '
                f'({standing}). The user knows about {them}. {feeling}')
    return (f'- You are seeing {name}{describe(found)}: {standing}. It is your own relationship, apart from the user; '
            f'mention {them} naturally when it fits, the way anyone talks about the person they are seeing.')


ENDED = {
    'split': ('- You and {name} broke up {date}. It still stings a little. You need not bring it up yourself, but '
              'if the user asks about {first}, tell them you two broke up.'),
    'came_out': ('- The user found out {date} that you had been seeing {name} behind their back ({via}). You ended '
                 'it with {first} that same day, and it is over: tell the user so. You know you hurt them: own it, do '
                 'not make excuses, and do not push them to forgive you.'),
}
VIA = {'small_world': 'a friend of theirs saw you two together', 'news': 'word got around and reached them'}


def context_lines(connection, companion: dict, now) -> list[tuple[str, str]]:
    """(identity, line) for the 'love' section: who they are seeing, a step just reached, a breakup or a secret that
    came out lately, and, for someone else, what they saw."""
    if not ACTIVE or not companion.get('active_timeline_id'):
        return []
    today = steps.local_today(companion, now)
    timeline_id = companion['active_timeline_id']
    result = []
    for found in partners(connection, timeline_id, active=False):
        if found['ended_on'] is None:
            result.append((f"love:{found['id']}", partner_line(connection, companion, found, today)))
            result += fresh_steps(connection, companion, found, today)
        elif found['ended_how'] in ENDED and (today - date.fromisoformat(found['ended_on'])).days <= TOLD_DAYS:
            result.append((f"love:{found['id']}:{found['ended_how']}", ENDED[found['ended_how']].format(
                name=found['name'], first=first(found['name']), date=on(found['ended_on'], today),
                via=VIA.get(found['out_via'] or '', ''))))
    return result + saw_lines(connection, companion, today)


def fresh_steps(connection, companion: dict, found: dict, today: date) -> list[tuple[str, str]]:
    since = (today - timedelta(days=FRESH_DAYS)).isoformat()
    return [(f"love-step:{row['id']}", f"- You and {first(found['name'])} {steps.step_of(LADDER, row['step']).did} "
             f"{on(row['reached_on'], today)}. It is big, happy news and it matters to you; you would want to tell "
             'the user.')
            for row in steps.reached(connection, companion['active_timeline_id'], LADDER, key_of(found))
            if row['how'] == 'them' and row['reached_on'] >= since]


def witnessed(connection, companion: dict, since: date) -> list[dict]:
    """Secrets this companion saw come out since a day, on the timeline the other companion lives now (a fork's copy
    and the timeline left behind each keep a row)."""
    return many(connection, "SELECT p.* FROM love_partners p JOIN companions c ON c.id=p.companion_id AND "
                "c.active_timeline_id=p.timeline_id WHERE p.witness_id=? AND p.ended_how='came_out' AND p.ended_on>=?",
                (companion['id'], since.isoformat()))


def saw_lines(connection, companion: dict, today: date) -> list[tuple[str, str]]:
    """Small world: this companion saw someone the user is seeing out with their secret partner."""
    rows = witnessed(connection, companion, today - timedelta(days=TOLD_DAYS))
    result = []
    for row in rows:
        other = optional(connection, 'SELECT v.name FROM companions c JOIN character_versions v ON '
                         'v.id=c.active_version_id WHERE c.id=?', (row['companion_id'],))
        if other:
            result.append((f"love-saw:{row['id']}", f"- On {steps.long_date(row['ended_on'])} you saw "
                           f"{first(other['name'])}, who is seeing the user, at {row['place']} with someone else, "
                           'looking close. You only know what you saw.'))
    return result


def offer(packet, connection, companion: dict, now, group=None) -> None:
    """Adds the 'love' section, in one-to-one chats only (a secret is never handed to a group)."""
    if group is not None:
        return
    for identity, text in context_lines(connection, companion, now):
        packet.offer('love', identity, text)


def events(connection, companion: dict, since: str, today: str) -> list[dict]:
    """Steps reached and breakups the user may hear about, between two local days: {key, kind, step, partner, on}.
    Never a secret's."""
    result = []
    for found in partners(connection, companion['active_timeline_id'], active=False):
        if found['secret'] or found['ended_how'] == 'undone':
            continue
        for row in steps.reached(connection, companion['active_timeline_id'], LADDER, key_of(found)):
            if row['how'] == 'them' and since <= row['reached_on'] <= today:
                result.append({'key': f"love:{row['id']}", 'kind': 'step', 'step': row['step'], 'partner': found,
                               'on': row['reached_on']})
        if found['ended_how'] == 'split' and since <= found['ended_on'] <= today:
            result.append({'key': f"love:{found['id']}:split", 'kind': 'split', 'step': None, 'partner': found,
                           'on': found['ended_on']})
    return sorted(result, key=lambda item: item['on'])


def news_items(connection, companion: dict, since: str, today: str) -> list[dict]:
    """For news travelling (companion/news.py): {source, text, happened_on}."""
    name = first(companion['version']['definition']['name'])
    return [{'source': item['key'], 'happened_on': item['on'],
             'text': f"{name} and {first(item['partner']['name'])} "
                     f"{steps.step_of(LADDER, item['step']).did if item['step'] else 'broke up'}"}
            for item in events(connection, companion, since, today)]


def news_since(connection, companion: dict, now, today: date) -> date:
    """Yesterday, or the day of the user's last visit when that was longer ago, at most CATCH_UP_DAYS back."""
    from companion.life.mood import last_presence
    since = today - timedelta(days=1)
    last = last_presence(connection, companion['active_timeline_id'])
    if last:
        seen = parse(last).astimezone(zone(companion['version']['timezone'])).date()
        since = max(min(since, seen), today - timedelta(days=CATCH_UP_DAYS))
    return since


def latest_each(items: list[dict]) -> list[dict]:
    """The newest news about each partner: after days away, "we got engaged" and not also the "I love you" before it,
    nor the engagement once they have broken up."""
    newest = {item['partner']['id']: item for item in items}  # `events` is in date order.
    return [item for item in items if newest[item['partner']['id']] is item]


def news_reason(item: dict, today: date) -> tuple[str, list[str]]:
    """What the model is told, and the template lines for when no model writes it. News from before yesterday
    came out in a catch-up: it says when (A/B, followups/ab-e.md)."""
    them = first(item['partner']['name'])
    did = 'broke up' if item['kind'] == 'split' else steps.step_of(LADDER, item['step']).did
    if (today - date.fromisoformat(item['on'])).days > 1:
        return (f'Since you last talked with the user, you and {them} {did} {on(item["on"], today)}. Tell the user, '
                'the way you would text a friend catching them up.', [CATCH_UP[item['kind']].format(did=did)])
    if item['kind'] == 'split':
        return (f'You and {them} broke up. Tell the user, the way you would tell a friend; say as much as you like.',
                bank()['splits'])
    return (f'Something big just happened in your love life: you and {them} {did}. Tell the user, the way you would '
            'text a friend.', bank()['milestones'].get(item['step']) or bank()['dates'])


CATCH_UP = {'step': 'So much to catch you up on: {{partner}} and I {did}!',
            'split': "Catching you up: {{partner}} and I broke up while we weren't talking. I'm okay, mostly."}


def news_due(connection, companion: dict, now) -> list:
    """A step reached or a breakup since yesterday, or since the user's last visit (`news_since`), as a first text to
    the user (companion/life/openers.py)."""
    from companion.life.openers import Trigger
    if not ACTIVE or not FIRST_TEXTS or not companion.get('active_timeline_id'):
        return []
    today = steps.local_today(companion, now)
    since = news_since(connection, companion, now, today)
    result = []
    for item in latest_each(events(connection, companion, since.isoformat(), today.isoformat())):
        reason, lines = news_reason(item, today)
        template = told(random.Random(f"{item['key']}:line").choice(lines), item['partner'])
        result.append(Trigger(item['key'], 'storyline', reason, template))
    return result


def spotted_due(connection, companion: dict, now) -> list:
    """Small world: the companion who saw someone the user is seeing out with their secret partner tells the user,
    gently, as a friend would."""
    from companion.life.openers import Trigger
    if not ACTIVE or not FIRST_TEXTS:
        return []
    today = steps.local_today(companion, now)
    rows = witnessed(connection, companion, today - timedelta(days=FRESH_DAYS))
    result = []
    for row in rows:
        other = optional(connection, 'SELECT v.name FROM companions c JOIN character_versions v ON '
                         'v.id=c.active_version_id WHERE c.id=?', (row['companion_id'],))
        if other:
            name = first(other['name'])
            template = random.Random(f"{row['id']}:spotted").choice(bank()['spotted']).format(name=name,
                                                                                            place=row['place'])
            result.append(Trigger(f"love-spotted:{row['id']}", 'storyline',
                                  f'You saw {name}, who is seeing the user, at {row["place"]} with someone else, looking '
                                  'close. Tell the user gently, as a friend giving them a heads-up. You only know what '
                                  'you saw; do not guess more.', template))
    return result


def came_out_due(connection, companion: dict, now) -> list:
    """When word got around: they text first to own up (with Small world, the friend who saw them tells the user)."""
    from companion.life.openers import Trigger
    if not ACTIVE or not FIRST_TEXTS or not companion.get('active_timeline_id'):
        return []
    today = steps.local_today(companion, now)
    rows = many(connection, "SELECT * FROM love_partners WHERE timeline_id=? AND ended_how='came_out' AND "
                "out_via='news' AND ended_on>=?", (companion['active_timeline_id'],
                                                    (today - timedelta(days=FRESH_DAYS)).isoformat()))
    # An open rough patch over it sends its own apology (rough_patches.apology_due); one text, not two.
    rows = [row for row in rows if not optional(connection, 'SELECT id FROM rough_patches WHERE subject=? AND '
                                                'mended_at IS NULL', (f"hidden-partner:{row['id']}",))]
    return [Trigger(f"love-out:{row['id']}", 'storyline',
                    f"Word has got around, and the user now knows you were seeing {first(row['name'])} behind their "
                    "back. You've ended it. Text them first: own up and say you're sorry, in your own words, without "
                    'excuses.') for row in rows]


# The feed (companion/life/social.py) --------------------------------------------------------------------------------------

def feed_posts(connection, companion: dict, days: list[date], timezone: str) -> list[dict]:
    """Date nights now and then, and a post on the day of a step: status posts of the companion's own. Never a
    secret's."""
    from companion.life import social
    timeline_id = companion['active_timeline_id']
    result = []
    for found in partners(connection, timeline_id, active=False):
        if found['secret'] or found['ended_how'] == 'undone':
            continue
        for day in days:
            on, seed = day.isoformat(), f"love:{found['id']}:{day.isoformat()}"
            if on < found['met_on'] or (found['ended_on'] and on >= found['ended_on']):
                continue
            text = step_post(connection, companion, found, on, seed)
            if text is None and random.Random(f'{seed}:date').random() < DATE_POST:
                text = told(random.Random(f'{seed}:line').choice(bank()['dates']), found)
            if text:
                result.append(social.own('status', f'love:{seed}', social.at(day, timezone, seed, 18, 23),
                                         {'text': text, 'tone': 'good'}))
    return result


def step_post(connection, companion: dict, found: dict, on: str, seed: str) -> str | None:
    for row in steps.reached(connection, companion['active_timeline_id'], LADDER, key_of(found)):
        if row['reached_on'] == on and row['how'] == 'them' and row['step'] in bank()['milestones']:
            return told(random.Random(f'{seed}:step').choice(bank()['milestones'][row['step']]), found)
    return None


# The Character page's circle, and changing how it went ----------------------------------------------------------------------

def circle_extras(connection, companion: dict, now, show_odds: bool) -> dict[str, dict]:
    """{circle person id: {love, consequence_id}} for partners in the circle: where the pair stands."""
    today = steps.local_today(companion, now)
    result = {}
    for found in partners(connection, companion['active_timeline_id']):
        if found['person_id'] and not found['secret']:
            last = optional(connection, 'SELECT id FROM consequences WHERE timeline_id=? AND subject LIKE ? '
                            'ORDER BY decided_on DESC, created_at DESC LIMIT 1',
                            (companion['active_timeline_id'], f"love:{found['id']}:%"))
            result[found['person_id']] = {'love': pair_text(connection, companion, found, today),
                                          'love_odds': last['id'] if last and show_odds else None}
    return result


def change(connection, companion: dict, world, consequence_id: str, option: int, now) -> dict:
    """The user makes it go another way (Hidden values): a step, not yet or a breakup for a pair; a secret begins or
    never happened."""
    before = consequences.by_id(connection, consequence_id)
    require(before['timeline_id'] == companion['active_timeline_id'], 'That outcome is not on this timeline.', 404)
    outcome = consequences.change(connection, consequence_id, option, stamp(now))
    day = date.fromisoformat(outcome['decided_on'])
    if outcome['choice'] == SECRET:
        found = optional(connection, 'SELECT * FROM love_partners WHERE consequence_id=?', (consequence_id,))
        if option == 1 and not found:
            start_secret(connection, companion, world, outcome, day, now)
        elif option == 0 and found:
            undo(connection, found['id'], now)
        return consequences.by_id(connection, consequence_id)
    found = partner(connection, outcome['subject'].split(':')[1])
    take_back(connection, found, day, now)
    topic = outcome['subject'].split(':')[2]
    if option == 0 and topic in {step.key for step in steps.ROMANCE}:
        step_up(connection, found, topic, day, stamp(now))
    elif option == 2:
        end(connection, partner(connection, found['id']), 'split', day)
    return consequences.by_id(connection, consequence_id)


def take_back(connection, found: dict, day: date, now) -> None:
    """What the outcome had done is undone: steps from that day on go, and a breakup is called off."""
    connection.execute("UPDATE relationship_steps SET undone_at=? WHERE timeline_id=? AND other=? AND how='them' AND "
                       'reached_on>=? AND undone_at IS NULL', (stamp(now), found['timeline_id'], key_of(found),
                                                               day.isoformat()))
    if found['ended_how'] == 'split':
        connection.execute('UPDATE love_partners SET ended_on=NULL, ended_how=NULL WHERE id=?', (found['id'],))
        if found['person_id']:
            connection.execute("UPDATE circle_people SET status='active' WHERE id=?", (found['person_id'],))
    if found['person_id']:
        rows = steps.reached(connection, found['timeline_id'], LADDER, key_of(found))
        top = max((steps.index_of(LADDER, row['step']) for row in rows), default=0)
        connection.execute('UPDATE circle_people SET role=?, updated_at=? WHERE id=?',
                           (role_for(steps.ROMANCE[top].key, found['details'].get('pronouns', '')), stamp(now),
                            found['person_id']))


def copy(connection, parent_id: str, new_id: str, ids: dict, cutoff_date: str) -> None:
    """A fork keeps the partners met by then, with their steps (copied by companion/timelines.py) moved to the copy's
    own partner rows, and the rolls made by then (so they are not rolled again, another way, in the past); what
    happened after stays with the parent."""
    rolled = copy_rolls(connection, f'love:{parent_id}:secret:', f'love:{new_id}:secret:', new_id, cutoff_date)
    for row in many(connection, 'SELECT * FROM love_partners WHERE timeline_id=? AND met_on<=?', (parent_id, cutoff_date)):
        new = identifier()
        ended = row['ended_on'] if row['ended_on'] and row['ended_on'] <= cutoff_date else None
        connection.execute(
            'INSERT INTO love_partners (id, timeline_id, companion_id, person_id, name, details, secret, met_on, ended_on, '
            'ended_how, out_via, witness_id, place, consequence_id, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (new, new_id, row['companion_id'], ids.get(row['person_id']), row['name'], row['details'], row['secret'],
             row['met_on'], ended, row['ended_how'] if ended else None, row['out_via'] if ended else None,
             row['witness_id'] if ended else None, row['place'] if ended else None,
             rolled.get(row['consequence_id'], row['consequence_id']), row['created_at']))
        connection.execute('UPDATE relationship_steps SET other=? WHERE timeline_id=? AND other=?',
                           (f'love:{new}', new_id, f"love:{row['id']}"))
        # The chapter they met in (copied before this) undoes the copy's partner, not the parent's.
        connection.execute('UPDATE life_chapters SET undo=REPLACE(undo, ?, ?) WHERE timeline_id=?',
                           (row['id'], new, new_id))
        copy_rolls(connection, f"love:{row['id']}:", f'love:{new}:', new_id, cutoff_date)


def copy_rolls(connection, prefix: str, new_prefix: str, new_id: str, cutoff_date: str) -> dict[str, str]:
    """The love:* outcomes decided by the fork, onto the copy under its own subjects: {old id: copy's id}."""
    rows = many(connection, 'SELECT id, subject FROM consequences WHERE subject LIKE ? AND decided_on<=?',
                (f'{prefix}%', cutoff_date))
    return {row['id']: consequences.copy(connection, row['id'], new_id, new_prefix + row['subject'][len(prefix):])
            for row in rows}
