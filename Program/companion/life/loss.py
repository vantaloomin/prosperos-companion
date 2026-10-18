"""Loss and grief (Hit List #71, v0.14 Years Go By): people in the companion's circle and in their town can pass away,
mostly the old; the funeral is a day they go to, the grief is a long, slow mood, and the date stays an anniversary.

Off unless the user turns on Settings > Realism > Their days > People can pass away (off on every preset, Vanta
2026-10-13); the Loss slider then sets how often. The app decides, the user overrides ("the world exists outside of
User", Vanta 2026-10-08):

- Who: anyone in the circle who is an adult, and townsfolk (companion/world/turnover.py, which already lets them pass
  away and has a newcomer take their place). Never a companion, never the user, never a child, never the companion's
  own partner, and never someone the user wrote into the character's description unless the user says they can on the
  circle list (`spared`).
- When: once a year for each person the consequence engine's `loss:passes` decides whether they pass away in the year
  ahead (Hidden values, "Why it went this way"). The odds rise steeply with age; the young have a tiny baseline; a
  parent whose care went harder (companion/life/health_turns.py `frail`) or who started treatment after a scare
  (the parent_health storyline) gets a decision of their own, with much higher odds. A death decided goes on a seeded
  day in that year.
- Then: they are 'late' (their circle row is removed with details `late`, so they leave every upcoming day), a caring
  turn for them ends, the companion tells the user in a first text, a funeral comes up as a big day
  (companion/life/big_days.py, kind 'funeral') with customs by culture and era (world/data/loss.json `customs`), the
  paper runs an obituary for someone local, and the date is an anniversary from then on.
- Grief, by rules: how deep follows who they were (a parent or sibling deepest, a friend less, someone from town
  least). Raw, then heavy, then lifting over weeks: a sad mood (companion/moods.py), fewer plans of their own (first
  texts that suggest plans hold back, companion/life/openers.py), the odd memory, and one context line while it lasts.
  Grief is sadness and missing someone: its lines never read as self-harm, and the crisis check (companion/safety.py)
  is unchanged.
- Undo: "Bring them back" on the circle list, or changing how it went under Hidden values, undoes a death; turning the
  switch off cancels the deaths still to come (those that happened stay).

No model decides anything; the model only puts it into words.
"""
import json
import random
import re
from datetime import date, datetime, timedelta
from functools import cache

from companion import consequences
from companion.clock import stamp, zone
from companion.database import decode, encode, identifier, many, optional
from companion.life import ages, circle, pronouns
from companion.world import catalog, generators

ACTIVE = True
# The news as a first text; off in most tests (tests/conftest.py), like the other first texts.
FIRST_TEXTS = True
CHOICE = 'loss:passes'
YEAR = 365
# A death decided today comes no sooner than this.
SOONEST = 2
ADULT = 18
# How long a parent's treatment after a scare (the parent_health storyline) counts toward their odds.
ILL_DAYS = 365
TREATMENT = 'treatment'
# Grief by depth: the days it stays raw, heavy and lifting, from the day they died.
GRIEF = {3: (14, 42, 90), 2: (7, 21, 45), 1: (3, 7, 14)}
DEEPEST = {'parent', 'sibling', 'grandparent', 'child', 'partner', 'grandmother', 'grandfather'}
DEEP = {'cousin', 'aunt', 'uncle', 'close friend', 'longtime friend', 'old friend from school', 'old classmate',
        'best friend', 'roommate from years ago'}
# The news goes out within this many days; the funeral is found this long after a death at most.
TOLD_DAYS, FUNERAL_WITHIN = 2, 21
# About one day in this many while grief lasts brings back a memory of them.
MEMORY_ONE_IN = 3
# A townsperson the companion has met this often is someone whose funeral they go to.
KNOWS_TOWNSPERSON = 6
STAGES = ('raw', 'heavy', 'lifting')
# Grief line by stage (A/B'd 2026-10-18, /mnt/project-files/companion-loss-ab/report.md).
FEELS = {
    'raw': "it's still raw: you're quieter than usual, you make fewer plans and it's hard to focus",
    'heavy': 'it still weighs on you: some days are fine and then it hits you again, and you make fewer plans than '
             'usual',
    'lifting': "it's lifting slowly: you're mostly yourself again, with the odd quiet moment",
}
CAUSES = {'illness': 'after an illness', 'old age': 'peacefully, of old age', 'sudden': 'suddenly'}
# The banks' lines that need a later era (texting, a phone, a radio, a photograph): the city's era as a rank, and the
# rank each needs. Other lines fit any era.
ERA_RANKS = {'modern': 3, 'future': 3, 'other': 3, 'jazz-age': 2, 'victorian': 1, 'steampunk': 1, 'frontier': 1}
ERA_NEEDS = ((re.compile(r'\btext', re.IGNORECASE), 3),
             (re.compile(r'\bcall|\bphone|\bradio\b|\bcrossword', re.IGNORECASE), 2),
             (re.compile(r'\bphotograph|\bcoffee\b|\bcocoa\b|\bpostcard|\bpocket watch', re.IGNORECASE), 1))


@cache
def bank() -> dict:
    return json.loads((catalog.DATA / 'loss.json').read_text(encoding='utf-8'))


def era_of(connection, companion: dict) -> str:
    """The era of the companion's city ('modern' without one)."""
    from companion.life import outings
    data = outings.city_data(connection, companion['version']['definition'])
    return (data or {}).get('era') or 'modern'


def fitting(lines: list[str], era: str) -> list[str]:
    """The lines that fit the era: no texting before phones, no radio in 1895, no photograph in Camelot."""
    rank = ERA_RANKS.get(era, 0)
    return [line for line in lines if all(rank >= need for pattern, need in ERA_NEEDS if pattern.search(line))] or lines


def first(name: str) -> str:
    return name.split()[0] if name.split() else name


def local_today(companion: dict, now: datetime) -> date:
    return now.astimezone(zone(companion['version']['timezone'])).date()


# Settings ----------------------------------------------------------------------------------------------------------

def level(connection) -> int | None:
    """The Loss slider (0..3) when People can pass away is on, else None."""
    row = optional(connection, 'SELECT people_pass_away, loss FROM life_settings WHERE id=1')
    return row['loss'] if row and row['people_pass_away'] else None


def settings_changed(connection) -> None:
    """The switch or the slider moved: deaths still to come are decided again with the new odds (or, with the switch
    off, not at all). Those that happened stay. The town follows on its own (companion/world/turnover.py `load`)."""
    connection.execute('DELETE FROM consequences WHERE id IN (SELECT consequence_id FROM losses WHERE happened=0)')
    connection.execute('DELETE FROM losses WHERE happened=0')


# Who can pass away -------------------------------------------------------------------------------------------------

def spared(connection, timeline_id: str, row: dict) -> bool:
    """Never a child, the companion's own partner or anyone the user spared; someone the user wrote into the
    character's description is spared until the user says otherwise."""
    details = decode(row['details']) or {}
    if (ages.stored_age(details) or 0) < ADULT or details.get('late'):
        return True
    if details.get('spared', bool(details.get('sheet'))):
        return True
    return bool(optional(connection, 'SELECT id FROM love_partners WHERE timeline_id=? AND person_id=? AND '
                         'ended_on IS NULL', (timeline_id, row['id'])))


def set_spared(connection, person_id: str, value: bool, now) -> dict:
    """The circle list's "Can pass away" switch: a person spared has no death to come."""
    row = circle.person(connection, person_id)
    details = decode(row['details']) or {}
    connection.execute('UPDATE circle_people SET details=?, revision=revision+1, updated_at=? WHERE id=?',
                       (encode({**details, 'spared': value}), stamp(now), person_id))
    if value:
        connection.execute('DELETE FROM losses WHERE person_id=? AND happened=0', (person_id,))
    return circle.person(connection, person_id)


def depth(role: str) -> int:
    kind = circle.role_kind(role)
    return 3 if kind in DEEPEST else 2 if kind in DEEP else 1


# Deciding ----------------------------------------------------------------------------------------------------------

def health_turns(connection, timeline_id: str, today: date) -> dict[str, list[tuple[str, str, str]]]:
    """{person id: [(key, since, fact)]}: parents in treatment after a scare, and parents whose care went harder
    (companion/life/health_turns.py)."""
    from companion.life import health_turns as care
    found: dict[str, list[tuple[str, str, str]]] = {}
    low = (today - timedelta(days=ILL_DAYS)).isoformat()
    for row in many(connection, "SELECT id, cast_ids, stages FROM storylines WHERE timeline_id=? AND "
                    "story='parent_health'", (timeline_id,)):
        stages, cast = decode(row['stages']), decode(row['cast_ids'])
        last = stages[-1] if len(stages) > 1 else None
        if cast and last and low <= last['on'] <= today.isoformat() and TREATMENT in last.get('text', ''):
            found.setdefault(cast[0], []).append((f"storyline:{row['id']}", last['on'], TREATMENT))
    for item in care.frail(connection, timeline_id):
        found.setdefault(item['person_id'], []).append((f"care:{item['chapter_id']}", item['since'], 'frail'))
    return found


def facts_for(connection, row: dict, today: date, turn: str | None, loss: int) -> dict:
    details = decode(row['details']) or {}
    age = ages.person_age(connection, 'circle', row['id'], today) or ages.stored_age(details) or 0
    return {'age': age, 'loss': loss, 'frail': int(turn == 'frail'), 'treatment': int(turn == TREATMENT),
            'family': int(circle.role_kind(row['role']) in circle.FAMILY)}


def decide(connection, companion: dict, row: dict, subject: str, facts: dict, now) -> bool:
    """The engine's `loss:passes` for one person and period: True when they pass away in it."""
    timeline_id = companion['active_timeline_id']
    names = {'name': first(companion['version']['definition']['name']), 'a': first(row['name']),
             'role': circle.said(row['role'], companion['version']['definition'])}
    table = consequences.tables()[CHOICE]
    outcome = consequences.decide(connection, timeline_id=timeline_id, choice=CHOICE, subject=subject, facts=facts,
                                  names=names, labels=[option['label'].format(**names) for option in table['options']],
                                  day=local_today(companion, now).isoformat(), timestamp=stamp(now))
    return outcome['picked'] == 1 and outcome


def watch_from(connection, row: dict, today: date, now) -> date:
    """The day the app started watching over this person (their years count from it), stored the first time."""
    details = decode(row['details']) or {}
    if details.get('loss_from'):
        return date.fromisoformat(details['loss_from'])
    connection.execute('UPDATE circle_people SET details=? WHERE id=?',
                       (encode({**details, 'loss_from': today.isoformat()}), row['id']))
    return today


def plan(connection, companion: dict, row: dict, day: date, today: date, outcome: dict, why: str, now,
         window: str) -> None:
    """A death decided: on its day they pass away (`happen`)."""
    details = decode(row['details']) or {}
    age = facts_for(connection, row, today, None, 0)['age']
    cause = 'illness' if why in ('frail', TREATMENT) else 'old age' if age >= 80 else \
        generators.pick(f"loss:{row['id']}", 'cause', ['illness', 'sudden'])
    connection.execute(
        'INSERT OR IGNORE INTO losses (id, timeline_id, kind, person_id, name, role, details, died_on, consequence_id, '
        "created_at, updated_at) VALUES (?, ?, 'circle', ?, ?, ?, ?, ?, ?, ?, ?)",
        (identifier(), companion['active_timeline_id'], row['id'], row['name'], row['role'],
         encode({'pronouns': details.get('pronouns', ''), 'local': details.get('local', True),
                 'city': details.get('city') or '', 'full_name': details.get('full_name') or row['name'],
                 'cause': cause, 'depth': depth(row['role']), 'window': window, 'neighborhood':
                 details.get('neighborhood') or ''}),
         max(day, today + timedelta(days=SOONEST)).isoformat(), outcome['id'], stamp(now), stamp(now)))


def consider(connection, companion: dict, row: dict, today: date, turns: list, loss: int, now) -> None:
    """This person's year, and any health turn of theirs: whether they pass away, decided once each."""
    start = watch_from(connection, row, today, now)
    window = (today - start).days // YEAR
    found = decide(connection, companion, row, f"loss:{row['id']}:{window}",
                   facts_for(connection, row, today, None, loss), now)
    if found:
        offset = int(generators.unit(row['id'], 'loss-day', window) * YEAR)
        ill = turns[-1][2] if turns else ''  # Someone already ill passes away of it.
        plan(connection, companion, row, start + timedelta(days=window * YEAR + offset), today, found, ill, now,
             str(window))
        return
    for key, since, fact in turns:
        found = decide(connection, companion, row, f"loss:{row['id']}:{key}",
                       facts_for(connection, row, today, fact, loss), now)
        if found:
            offset = 30 + int(generators.unit(row['id'], 'loss-turn', key) * 270)
            plan(connection, companion, row, date.fromisoformat(since) + timedelta(days=offset), today, found, fact,
                 now, key)
            return


def advance(connection, companion: dict, now: datetime) -> None:
    """Once a day, before the big days (companion/life/agenda.py): deaths decided and deaths that came, and townsfolk
    the companion knew who passed away. Cheap: no model."""
    loss = level(connection)
    if not ACTIVE or loss is None or not companion.get('active_timeline_id'):
        return
    timeline_id, today = companion['active_timeline_id'], local_today(companion, now)
    planned = {row['person_id'] for row in many(connection, 'SELECT person_id FROM losses WHERE timeline_id=?',
                                                (timeline_id,))}
    turns = health_turns(connection, timeline_id, today)
    for row in circle.people(connection, timeline_id):
        if row['id'] not in planned and not spared(connection, timeline_id, row):
            consider(connection, companion, row, today, turns.get(row['id'], []), loss, now)
    for row in many(connection, "SELECT * FROM losses WHERE timeline_id=? AND happened=0 AND died_on<=?",
                    (timeline_id, today.isoformat())):
        happen(connection, companion, row, now)
    town(connection, companion, today, now)


def happen(connection, companion: dict, row: dict, now) -> None:
    """They pass away: late in the circle (out of every upcoming day), their unfinished storylines end and a caring
    turn for them closes."""
    from companion.life import agenda, storylines
    person = optional(connection, 'SELECT * FROM circle_people WHERE id=?', (row['person_id'],))
    if person is None or person['status'] != 'active':
        connection.execute('DELETE FROM losses WHERE id=?', (row['id'],))
        return
    details = decode(person['details']) or {}
    connection.execute("UPDATE circle_people SET status='removed', details=?, revision=revision+1, updated_at=? "
                       'WHERE id=?', (encode({**details, 'late': row['died_on']}), stamp(now), person['id']))
    connection.execute('UPDATE losses SET happened=1, updated_at=? WHERE id=?', (stamp(now), row['id']))
    agenda.forget_person(connection, row['timeline_id'], person['id'], now)  # No more plans or drop-ins with them.
    storylines.end_removed(connection, row['timeline_id'], local_today(companion, now))
    end_care(connection, companion, row)


def end_care(connection, companion: dict, row: dict) -> None:
    """A caring turn for them (companion/life/health_turns.py) closes with their passing."""
    from companion.life import health_turns as care
    who = f"{circle.said(row['role'], companion['version']['definition'])} {first(row['name'])}"
    for item in caring(connection, row):
        if item['person_id'] == row['person_id']:
            care.end_care(connection, companion, item['chapter_id'], date.fromisoformat(row['died_on']), 'passed',
                          f"Your {who} died, and the evenings at their place have ended.",
                          f'My {who} passed away.')


def caring(connection, row: dict) -> list[dict]:
    return [{'chapter_id': found['id'], 'person_id': decode(found['details']).get('parent')}
            for found in many(connection, "SELECT id, details FROM life_chapters WHERE timeline_id=? AND kind='caring' "
                              "AND undone_at IS NULL AND json_extract(details, '$.ended_on') IS NULL",
                              (row['timeline_id'],))]


def town(connection, companion: dict, today: date, now) -> None:
    """A townsperson the companion knew well passed away (companion/world/turnover.py): a loss of theirs too."""
    from companion.life import encounters, outings
    from companion.world import townsfolk
    data = outings.city_data(connection, companion['version']['definition'])
    if not data:
        return
    cast = encounters.town_cast(connection, companion, data)
    for key, meetings in encounters.history_for(connection, companion, cast, now).items():
        sheet = encounters.resolve(data, key, cast) if len(meetings) >= KNOWS_TOWNSPERSON else None
        gone = townsfolk.gone(sheet, data, today) if sheet and not sheet.get('cast') else None
        if not gone or gone['why'] != 'passed' or (today - date.fromisoformat(gone['day'])).days > TOLD_DAYS * 5:
            continue
        role = sheet.get('role') or 'someone from town'
        where = '' if sheet.get('kind') == 'resident' else f" at {sheet['place']['name']}"
        connection.execute(
            'INSERT OR IGNORE INTO losses (id, timeline_id, kind, town_key, name, role, details, died_on, happened, '
            "created_at, updated_at) VALUES (?, ?, 'town', ?, ?, ?, ?, ?, 1, ?, ?)",
            (identifier(), companion['active_timeline_id'], key, sheet['full'], f'{role}{where}',
             encode({'pronouns': sheet.get('pronouns', ''), 'local': True, 'depth': 1, 'cause': '',
                     'age': ages.town_age(connection, sheet, date.fromisoformat(gone['day']))}),
             gone['day'], stamp(now), stamp(now)))


# Undoing -----------------------------------------------------------------------------------------------------------

def undo(connection, companion: dict, loss_id: str, now) -> None:
    """"Bring them back": back in the circle as if it never happened, the funeral called off and the outcome changed
    to living on."""
    from companion.life import big_days
    row = optional(connection, 'SELECT * FROM losses WHERE id=? AND timeline_id=?',
                   (loss_id, companion['active_timeline_id']))
    if row is None:
        return
    person = optional(connection, 'SELECT * FROM circle_people WHERE id=?', (row['person_id'] or '',))
    if person and (decode(person['details']) or {}).get('late'):
        details = {key: value for key, value in decode(person['details']).items() if key != 'late'}
        connection.execute("UPDATE circle_people SET status='active', details=?, revision=revision+1, updated_at=? "
                           'WHERE id=?', (encode(details), stamp(now), person['id']))
    for found in many(connection, "SELECT * FROM big_days WHERE source=? AND status IN ('planned', 'invited', "
                      "'declined')", (f'loss:{loss_id}',)):
        big_days.call_off(connection, big_days.view(found), stamp(now))
    if row['consequence_id']:
        consequences.change(connection, row['consequence_id'], 0, stamp(now))
    connection.execute('DELETE FROM losses WHERE id=?', (loss_id,))


def change(connection, companion: dict, consequence_id: str, option: int, now) -> dict:
    """"Change how it went" under Hidden values: living on undoes the death; passing away plans it soon."""
    outcome = consequences.by_id(connection, consequence_id)
    row = optional(connection, 'SELECT * FROM losses WHERE consequence_id=?', (consequence_id,))
    if option == 0 and row:
        undo(connection, companion, row['id'], now)
    consequences.change(connection, consequence_id, option, stamp(now))
    person = optional(connection, 'SELECT * FROM circle_people WHERE id=?', (outcome['subject'].split(':')[1],))
    if option == 1 and row is None and person and person['status'] == 'active':
        today = local_today(companion, now)
        plan(connection, companion, person, today, today, outcome, '', now, outcome['subject'].split(':', 2)[2])
    return consequences.by_id(connection, consequence_id)


# What it looks like ------------------------------------------------------------------------------------------------

def rows(connection, timeline_id: str) -> list[dict]:
    return [view(row) for row in many(connection, 'SELECT * FROM losses WHERE timeline_id=? AND happened=1 ORDER BY '
                                      'died_on DESC', (timeline_id,))]


def view(row: dict) -> dict:
    return {**row, 'details': decode(row['details']) or {}}


def of_person(connection, person_id: str) -> dict | None:
    """The circle list's "Passed away" for someone late: when, and how it went under Hidden values."""
    row = optional(connection, 'SELECT * FROM losses WHERE person_id=? AND happened=1', (person_id,))
    return {'id': row['id'], 'died_on': row['died_on'], 'consequence_id': row['consequence_id']} if row else None


def stage(found: dict, today: date) -> str | None:
    """'raw', 'heavy' or 'lifting' while they grieve, else None."""
    days = (today - date.fromisoformat(found['died_on'])).days
    limits = GRIEF[found['details'].get('depth', 1)]
    return next((name for name, limit in zip(STAGES, limits, strict=True) if 0 <= days < limit), None)


def grieving(connection, companion: dict, now) -> tuple[dict, str] | None:
    """The loss they grieve most right now, and how far along: the deepest, then the newest."""
    today = local_today(companion, now)
    found = [(row, name) for row in rows(connection, companion['active_timeline_id'])
             if (name := stage(row, today))]
    return max(found, key=lambda item: (STAGES.index(item[1]) * -1, item[0]['details'].get('depth', 1),
                                        item[0]['died_on'])) if found else None


def who(row: dict, definition: dict) -> str:
    """'your dad Ray', 'Sam (the barista at Daily Grind)'."""
    if row['kind'] == 'town':
        return f"{first(row['name'])} ({row['role']})"
    return f"your {circle.said(row['role'], definition)} {first(row['name'])}"


def long_date(day: str) -> str:
    found = date.fromisoformat(day)
    return f'{found:%A}, {found.day} {found:%B}'


def memory(row: dict, today: date, era: str = 'modern') -> str:
    """Now and then, something small brings them back (one day in MEMORY_ONE_IN, seeded)."""
    if generators.unit(row['id'], 'memory', today.isoformat()) * MEMORY_ONE_IN >= 1:
        return ''
    line = generators.pick(row['id'], f'memory:{today.isoformat()}', fitting(bank()['memories'], era))
    found = pronouns.person(row['details'].get('pronouns'))
    return f" Today something brought {found['them']} back: {line.format(**found)}."


def grief_line(row: dict, name: str, today: date, definition: dict, era: str = 'modern') -> str:
    gap = (today - date.fromisoformat(row['died_on'])).days
    ago = 'today' if gap == 0 else 'yesterday' if gap == 1 else f'{gap} days ago'
    cause = f", {CAUSES[row['details']['cause']]}" if row['details'].get('cause') in CAUSES else ''
    text = (f"- {who(row, definition)[:1].upper()}{who(row, definition)[1:]} died on {long_date(row['died_on'])} "
            f"({ago}){cause}. You're grieving, and {FEELS[name]}.")
    return (text + memory(row, today, era) + " You don't need to bring it up every time, and you can still laugh and enjoy "
            'things.')


def remembered_line(row: dict, today: date, definition: dict) -> str:
    """After grief lifts: the anniversary on its day, else a plain fact so they never come back to life."""
    died = date.fromisoformat(row['died_on'])
    years = today.year - died.year
    them = pronouns.person(row['details'].get('pronouns'))['them']
    if years >= 1 and (today.month, today.day) == (died.month, died.day):
        span = 'a year' if years == 1 else f'{years} years'
        return f"- Today it's {span} since {who(row, definition)} died. You're thinking of {them} today."
    return f"- {who(row, definition)[:1].upper()}{who(row, definition)[1:]} died in {died:%B} {died.year}. You still " \
        f'miss {them} now and then.'


def context_lines(connection, companion: dict, now) -> list[tuple[str, str]]:
    """(identity, line) for the 'loss' section: the grief while it lasts, then anniversaries and the plain fact."""
    today, definition = local_today(companion, now), companion['version']['definition']
    result, era = [], era_of(connection, companion)
    for row in rows(connection, companion['active_timeline_id']):
        name = stage(row, today)
        if name:
            result.append((f"loss:{row['id']}:{name}:{today.isoformat()}",
                           grief_line(row, name, today, definition, era)))
        elif date.fromisoformat(row['died_on']) <= today and row['kind'] == 'circle':
            result.append((f"loss:{row['id']}:after:{today.isoformat()}", remembered_line(row, today, definition)))
    return result


def offer(packet, connection, companion: dict, now: datetime, group=None) -> None:
    """Adds the 'loss' section, in a 1:1 chat."""
    if not ACTIVE or group is not None or not companion.get('active_timeline_id'):
        return
    for identity, text in context_lines(connection, companion, now):
        packet.offer('loss', identity, text)


def moods(connection, companion: dict, now) -> list[tuple[tuple[str, int], str]]:
    """For their mood (companion/moods.py): sad while grief is raw or heavy."""
    found = grieving(connection, companion, now)
    if not found or found[1] == 'lifting':
        return []
    row = found[0]
    feeling = ('sad', 2 if found[1] == 'raw' and row['details'].get('depth', 1) >= 2 else 1)
    said = circle.said(row['role'], companion['version']['definition'])  # 'dad', as the A/B'd note had it
    return [(feeling, f"{first(companion['version']['name'])}'s {said} "
                      f"{first(row['name'])} died" if row['kind'] == 'circle' else
             f"{first(row['name'])} from town died")]


def holds_back(connection, companion: dict, now) -> bool:
    """Fewer plans of their own while grief is raw (none) or heavy (about half the days)."""
    found = grieving(connection, companion, now)
    if not found or found[1] == 'lifting':
        return False
    return found[1] == 'raw' or generators.unit(found[0]['id'], 'plans', local_today(companion, now).isoformat()) < 0.5


# The news (a first text, companion/life/openers.py) -----------------------------------------------------------------

def news_due(connection, companion: dict, now) -> list:
    """Someone in their circle died today or yesterday: they tell the user."""
    from companion.life.openers import Trigger
    if not ACTIVE or not FIRST_TEXTS or not companion.get('active_timeline_id'):
        return []
    today, definition = local_today(companion, now), companion['version']['definition']
    result, lines = [], fitting(bank()['news'], era_of(connection, companion))
    for row in rows(connection, companion['active_timeline_id']):
        gap = (today - date.fromisoformat(row['died_on'])).days
        if row['kind'] != 'circle' or not 0 <= gap < TOLD_DAYS:
            continue
        when = 'today' if gap == 0 else 'yesterday'
        cause = f", {CAUSES[row['details']['cause']]}" if row['details'].get('cause') in CAUSES else ''
        line = random.Random(f"{row['id']}:news").choice(lines).format(
            who=who(row, definition).replace('your ', 'my ', 1), when=when)
        result.append(Trigger(f"loss:{row['id']}", 'storyline',
                              f"Something sad just happened: {who(row, definition)} died {when}{cause}. Tell the user, "
                              "the way you would text someone close. You're sad and you miss them; keep it simple.",
                              line[:1].upper() + line[1:]))
    return result


# Funerals (big days, companion/life/big_days.py) --------------------------------------------------------------------

def customs(connection, companion: dict) -> dict:
    from companion.life import outings, wedding
    data = outings.city_data(connection, companion['version']['definition'])
    found = bank()['customs']
    return found.get(wedding.culture_of(data)) or found['modern']


def funerals(connection, companion: dict, today: date, now) -> list[dict]:
    """A funeral for each loss of theirs, some days on by the city's customs."""
    from companion.life import big_days
    rules, definition = customs(connection, companion), companion['version']['definition']
    result = []
    for row in rows(connection, companion['active_timeline_id']):
        died = date.fromisoformat(row['died_on'])
        if (today - died).days > FUNERAL_WITHIN:
            continue
        low, high = rules['days']
        day = died + timedelta(days=low + int(generators.unit(row['id'], 'funeral') * (high - low + 1)))
        day = max(day, today + timedelta(days=big_days.SOONEST))
        result.append(big_days.candidate('funeral', f"loss:{row['id']}", None, day, name=row['name'],
                                         role=circle.said(row['role'], definition) if row['kind'] == 'circle' else '',
                                         town=row['town_key'] or '', local=row['details'].get('local', True),
                                         city=row['details'].get('city', ''), loss_id=row['id'], word=rules['word'],
                                         at=rules['at'], until=rules['until'], wear=rules['wear'],
                                         service=rules['service'], after=rules['after'], flowers=flowers(row)))
    return result


def flowers(row: dict) -> str:
    """Someone outside the family gets flowers sent; for family the companion brings nothing."""
    from companion.life import circle
    return '' if row['kind'] == 'circle' and circle.role_kind(row['role'] or '') in circle.FAMILY else 'flowers'


def venue_for(connection, companion: dict, data: dict, seed: str, day: date) -> dict:
    """Where the funeral is held: a chapel, church or hall in their city named by its customs, else a temple, else the
    customs' own unnamed place ("the funeral home"), never a lighthouse or a park."""
    import re

    from companion.life import big_days, outings, wedding
    rules = customs(connection, companion)
    words = re.compile(rf"\b(?:{rules['words']})", re.IGNORECASE)
    places = [item for item in data['places'] if not any(word in item['name'].lower() for word in big_days.NOT_PARTY)
              and item['kind'] not in wedding.OUTDOOR and not wedding.OUTDOOR_NAMES.search(item['name'])]
    options = held_in(places, words) or [item for item in places if item['kind'] == 'temple']
    if options:
        return outings.place_view(generators.pick(seed, 'venue', options), data)
    return {'id': '~funeral', 'name': rules['venue'], 'kind': 'venue', 'neighborhood': '', 'summary': '', 'cost': '',
            'cuisine': '', 'city': data['name'], 'city_id': data['id'], 'spots': []}


def held_in(places: list[dict], words) -> list[dict]:
    """Places named for a funeral by the customs' words that are a place of worship, or a landmark named for more
    than being a hall: never a food hall, an arena, a bar (The Churchill Arms) or the abbey's library."""
    import re
    named = [item for item in places if words.search(item['name'])]
    return [item for item in named if item['kind'] == 'temple'] or [
        item for item in named if item['kind'] == 'landmark' and words.search(re.sub(r'\bhall\b', '', item['name'],
                                                                                     flags=re.IGNORECASE))]


def gone(connection, row: dict) -> bool:
    """A funeral is called off when the death it is for was undone."""
    loss_id = row['details'].get('loss_id')
    return bool(loss_id) and not optional(connection, 'SELECT id FROM losses WHERE id=?', (loss_id,))


# The paper (companion/world/paper.py) -------------------------------------------------------------------------------

def closing(seed: str, name: str, found_pronouns: str) -> str:
    line = generators.pick(seed, 'obituary', bank()['obituaries'])
    return line.format(name=first(name), their=pronouns.person(found_pronouns)['their'])


def obituary(full: str, where: str, age: int | None, seed: str, found_pronouns: str) -> str:
    """'Ada Fenwick, of Hampden, died this week at 87. Ada will be remembered for ...'."""
    at = f' at {age}' if age else ''
    return f"{full}, {where}, died this week{at}. {closing(seed, full, found_pronouns)}"


def paper_items(connection, data: dict, week: tuple[date, date]) -> list[dict]:
    """Obituaries for people in a companion's circle who lived in this city and died that week."""
    from companion.world import paper
    result = []
    for person in paper.companions_in(connection, data):
        for row in many(connection, "SELECT * FROM losses WHERE timeline_id=? AND kind='circle' AND happened=1 AND "
                        'died_on BETWEEN ? AND ?', (person['timeline_id'], week[0].isoformat(), week[1].isoformat())):
            found = view(row)
            if not found['details'].get('local', True):
                continue
            hood = found['details'].get('neighborhood')
            person_row = optional(connection, 'SELECT details FROM circle_people WHERE id=?', (found['person_id'],))
            age = ages.person_age(connection, 'circle', found['person_id'], date.fromisoformat(found['died_on'])) \
                or ages.stored_age(decode(person_row['details']) if person_row else {})
            full = found['details'].get('full_name') or found['name']
            result.append({'key': f"loss:{found['id']}", 'headline': f'{full} has died.',
                           'text': obituary(full, f'of {hood}' if hood else f"of {data['name']}", age, found['id'],
                                            found['details'].get('pronouns', ''))})
    return result


# Branches (companion/timelines.py) ----------------------------------------------------------------------------------

def copy(connection, parent_id: str, new_id: str, ids: dict, cutoff_date: str) -> None:
    """Deaths up to the fork carry over; one after it never happened on the copy (its circle row comes back)."""
    for row in many(connection, 'SELECT * FROM losses WHERE timeline_id=?', (parent_id,)):
        person_id = ids.get(row['person_id']) if row['person_id'] else None
        if row['happened'] and row['died_on'] <= cutoff_date:
            consequence = consequences.copy(connection, row['consequence_id'], new_id, row['consequence_id']) \
                if row['consequence_id'] else None
            copied = identifier()
            connection.execute(
                'INSERT INTO losses (id, timeline_id, kind, person_id, town_key, name, role, details, died_on, happened, '
                'consequence_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)',
                (copied, new_id, row['kind'], person_id, row['town_key'], row['name'], row['role'],
                 row['details'], row['died_on'], consequence, row['created_at'], row['updated_at']))
            follow_funeral(connection, new_id, row['id'], copied)
        elif person_id:
            person = optional(connection, 'SELECT details FROM circle_people WHERE id=?', (person_id,))
            details = decode(person['details']) if person else {}
            if details.get('late'):
                details.pop('late')
                connection.execute("UPDATE circle_people SET status='active', details=? WHERE id=?",
                                   (encode(details), person_id))


def follow_funeral(connection, timeline_id: str, old_id: str, new_id: str) -> None:
    """The funeral the copy carried over (companion/life/big_days.py `copy`) is for the copy's own loss, so it is not
    planned a second time."""
    connection.execute("UPDATE big_days SET source=?, details=json_set(details, '$.loss_id', ?) WHERE timeline_id=? AND "
                       'source=?', (f'loss:{new_id}', new_id, timeline_id, f'loss:{old_id}'))
