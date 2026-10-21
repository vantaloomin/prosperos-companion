"""The Watching feed's love life (Hit List #81, 1.0): what happened between the watched companion and the user, and in
the companion's own love life, told on the day by the narrator (companion/life/narrator.py).

Nothing new happens here either. The lines are read from the rows that already exist, the same way the Character page
and the scrapbook read them, so changing a roll on Today moves them:

- the steps the two of them took (companion/life/steps.py), from the first one the app did not pick at the start; when
  the step picker set several at once, only the highest is told;
- a big rough patch starting (companion/life/rough_patches.py), a break, a breakup or a falling out, and getting back
  together (companion/life/breakups.py);
- the companion's own love life (companion/life/love_life.py): someone new, their steps, a split. A secret partner is
  never told, as the circle never shows one.

Each line is one of a few from world/data/watching_love.json, picked by seeded dice. Hidden values stay hidden: the
feeling is in the words, never the odds. A thought after a parting comes only from the heartache bank
(world/data/inner_voice.json), never from the bad-luck lines; a step or making up takes a happy one.

The line under the companion's name follows where the two of them stand: "Your companion" while together, "On a
break", "Your ex", or "Your old friend" after a falling out.
"""
import json
import random
import re
from datetime import date, time
from functools import cache
from pathlib import Path

from companion.clock import parse, zone
from companion.database import decode, many, optional

KIND = 'love'
HURT = 'heartache'
# A step or a split known only by its day is told in the evening.
EVENING = time(21, 0)
LADDERS = ('romance', 'friendship')
# Partners whose story is not the narrator's to tell: a secret that came out, one the user took out of the circle,
# or one the app took back.
UNTOLD = ('came_out', 'removed', 'undone')
STANDING = {'break': 'On a break', 'ended': 'Your ex', 'fell_out': 'Your old friend'}
PRONOUNS = re.compile(r"\b(they|them|their|theirs|themself)\b")


@cache
def bank() -> dict:
    return json.loads((Path(__file__).parents[1] / 'world' / 'data' / 'watching_love.json').read_text(encoding='utf-8'))


def said(options: list[str], key: str, **names) -> str:
    return random.Random(key).choice(options).format(**names)


def local_day(when: str, timezone: str) -> date:
    return parse(when).astimezone(zone(timezone)).date()


def moment(written: str | None, day: str, timezone: str) -> str:
    """When a line known by its day is told: as it was written, when that was on the day, else that evening."""
    from companion.life.narrator import at
    if written and local_day(written, timezone).isoformat() == day[:10]:
        return written
    return at(date.fromisoformat(day[:10]), EVENING, timezone)


def thought(voice: int, key: str, first: str, hurt: bool) -> str | None:
    """A happy thought after a step, as after any good line; after a parting, one from the heartache bank on true to
    life (2) and up."""
    from companion.life.narrator import pick, thought_after
    if not hurt:
        return thought_after(voice, True, key, 'good', first)
    return pick(HURT, key).format(first=first) if voice >= 2 else None


class Teller:
    """Tells one companion's week: their first name, timezone, the days shown and how much of their mind is told."""

    def __init__(self, companion: dict, since: date, today: date, voice: int, first: str):
        self.companion, self.since, self.today, self.voice, self.first = companion, since, today, voice, first
        self.timezone = companion['version']['timezone']
        self.timeline = companion['active_timeline_id']

    def shown(self, when: str) -> bool:
        return self.since <= local_day(when, self.timezone) <= self.today

    def line(self, key: str, when: str, text: str, hurt: bool = False) -> dict:
        from companion.life.narrator import item
        return item(key, when, KIND, text, inner=thought(self.voice, key, self.first, hurt))


def told(connection, companion: dict, since: date, today: date, voice: int, first: str, pronouns: str) -> list[dict]:
    """Every love-life line for the week shown."""
    teller = Teller(companion, since, today, voice, first)
    return (our_steps(connection, teller) + patches(connection, teller, pronouns) + partings(connection, teller)
            + theirs(connection, teller))


# The two of them -------------------------------------------------------------------------------------------------------

def taken_back(connection, timeline_id: str) -> set[str]:
    """Steps taken back on getting back together: they happened, so they are still told."""
    rows = many(connection, 'SELECT steps_back FROM breakups WHERE timeline_id=? AND steps_back IS NOT NULL',
                (timeline_id,))
    return {step_id for row in rows for step_id in decode(row['steps_back']) or []}


def highest(rows: list[dict], ladder: str) -> list[dict]:
    """One step a day: the highest, when several were set at once."""
    from companion.life import steps
    days: dict[str, dict] = {}
    for row in rows:
        if row['reached_on'] not in days or steps.index_of(ladder, row['step']) > steps.index_of(
                ladder, days[row['reached_on']]['step']):
            days[row['reached_on']] = row
    return sorted(days.values(), key=lambda row: row['reached_on'])


def step_rows(connection, teller: Teller, other: str, ladder: str, kept: set[str] = frozenset()) -> list[dict]:
    rows = many(connection, "SELECT * FROM relationship_steps WHERE timeline_id=? AND other=? AND ladder=? AND how NOT "
                "IN ('start', 'history') AND reached_on>=? AND reached_on<=? ORDER BY reached_on, created_at",
                (teller.timeline, other, ladder, teller.since.isoformat(), teller.today.isoformat()))
    return highest([row for row in rows if row['undone_at'] is None or row['id'] in kept], ladder)


def our_steps(connection, teller: Teller) -> list[dict]:
    from companion.life import steps
    ladder = steps.ladder_of(teller.companion['version']['definition'])
    if ladder not in LADDERS:
        return []
    texts = bank()['steps'][ladder]
    result = []
    for row in step_rows(connection, teller, steps.USER, ladder, taken_back(connection, teller.timeline)):
        key = f"step:{row['id']}"
        if row['step'] in texts:
            result.append(teller.line(key, moment(row['created_at'], row['reached_on'], teller.timezone),
                                      said(texts[row['step']], key, first=teller.first)))
    return result


def patch_text(row: dict, key: str, first: str, pronouns: str) -> str:
    """How it started: "over ..." as the Character page says it, with the companion's own pronouns (never inside what
    the user said, which is quoted); a plan they called off; or just that things got tense."""
    from companion.life.pronouns import person
    texts, shown = bank()['patch'], row['shown'] or ''
    if shown.startswith('over '):
        words, quote, rest = shown.partition('"')
        forms = person(pronouns)
        over = PRONOUNS.sub(lambda match: forms.get(match[1], match[1]), words) + quote + rest
        return said(texts['over'], key, first=first, over=over)
    if row['cause'] == 'stood_up':
        plan = row['about'].rpartition(' (')[0] or row['about']
        return said(texts['called_off'], key, first=first, plan=plan)
    return said(texts['plain'], key, first=first)


def patch_stands(connection, row: dict) -> bool:
    """Picked to start, and not undone on Today (a plan they called off that is back on)."""
    from companion.life import rough_patches
    if not rough_patches.picked_open(connection, row):
        return False
    if row['cause'] == 'stood_up' and row['outing_id']:
        outing = optional(connection, 'SELECT status FROM outings WHERE id=?', (row['outing_id'],))
        return bool(outing) and outing['status'] == 'cancelled'
    return True


def patches(connection, teller: Teller, pronouns: str) -> list[dict]:
    """A big rough patch starting; a small one is gone by the next day, so it is not news."""
    rows = many(connection, "SELECT * FROM rough_patches WHERE timeline_id=? AND size='big' AND started_on>=? AND "
                'started_on<=? ORDER BY started_at', (teller.timeline, teller.since.isoformat(), teller.today.isoformat()))
    return [teller.line(f"patch:{row['id']}", row['started_at'],
                        patch_text(row, f"patch:{row['id']}", teller.first, pronouns), hurt=True)
            for row in rows if patch_stands(connection, row)]


def ended_key(connection, companion: dict, row: dict) -> str:
    from companion.life import breakups
    if row['ladder'] == 'friendship':
        return 'fell_out'
    return breakups.ended_marriage(connection, companion, row) or row['ended_by']


def parting(connection, teller: Teller, row: dict) -> list[tuple[str, str, str, bool]]:
    """(key, when, text, hurt) for a break, an ending and getting back together, as the scrapbook reads them."""
    from companion.life import breakups
    found, texts, first = breakups.stage(connection, row, True), bank(), teller.first
    result = []
    if row['break_at'] and found in ('break', 'ended', 'together') and row['ladder'] == 'romance' and (
            row['break_by'] == 'you' or breakups.picked(connection, row['break_id']) == breakups.YES):
        key = f"break:{row['id']}"
        result.append((key, row['break_at'], said(texts['break'][row['break_by']], key, first=first), True))
    if row['ended_at'] and (found == 'ended' or found == 'together'
                            and breakups.stage_before_together(connection, row) == 'ended'):
        key = f"ended:{row['id']}"
        what = ended_key(connection, teller.companion, row)
        result.append((key, row['ended_at'], said(texts['ended'][what], key, first=first), True))
    if found == 'together' and (row['together_at'] or row['ended_at']):
        key = f"together:{row['id']}"
        result.append((key, row['together_at'] or row['ended_at'], said(texts['together'][row['ladder']], key,
                                                                        first=first), False))
    return result


def partings(connection, teller: Teller) -> list[dict]:
    from companion.life import breakups
    return [teller.line(key, when, text, hurt) for row in breakups.rows(connection, teller.timeline)
            for key, when, text, hurt in parting(connection, teller, row) if teller.shown(when)]


# Their own love life ---------------------------------------------------------------------------------------------------

def partner_lines(connection, teller: Teller, partner: dict) -> list[dict]:
    from companion.life import love_life
    texts, other = bank()['theirs'], love_life.first(partner['name'])
    names = {'first': teller.first, 'other': other}
    result = []
    if teller.since.isoformat() <= partner['met_on'] <= teller.today.isoformat():
        key = f"met:{partner['id']}"
        result.append(teller.line(key, moment(partner['created_at'], partner['met_on'], teller.timezone),
                                  said(texts['met'], key, **names)))
    for row in step_rows(connection, teller, love_life.key_of(partner), love_life.LADDER):
        key = f"step:{row['id']}"
        if row['step'] in texts:
            result.append(teller.line(key, moment(row['created_at'], row['reached_on'], teller.timezone),
                                      said(texts[row['step']], key, **names)))
    ended = partner['ended_on']
    if ended and partner['ended_how'] in texts and teller.since.isoformat() <= ended <= teller.today.isoformat():
        key = f"split:{partner['id']}"
        result.append(teller.line(key, moment(None, ended, teller.timezone), said(texts[partner['ended_how']], key,
                                                                                   **names), hurt=True))
    return result


def theirs(connection, teller: Teller) -> list[dict]:
    from companion.life import love_life
    return [line for partner in love_life.partners(connection, teller.timeline, active=False)
            if not partner['secret'] and partner['ended_how'] not in UNTOLD
            for line in partner_lines(connection, teller, partner)]


# The line under their name ---------------------------------------------------------------------------------------------

def standing(connection, companion: dict) -> str:
    """"Your companion" while together; "On a break", "Your ex", or "Your old friend" after a falling out."""
    from companion.life import breakups
    row, found = breakups.current(connection, companion)
    if found == 'ended' and row['ladder'] == 'friendship':
        found = 'fell_out'
    return STANDING.get(found, 'Your companion')
