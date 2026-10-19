"""The town changes hands (Hit List #72, v0.14 Years Go By): townsfolk move away, change jobs, retire and, with
People can pass away on, pass away, and newcomers take their place at the bakery.

Every spot a townsperson fills (the first person at a place, the third neighbor on a street) is a slot, and
whoever holds it is one generation of it. The first generation is the person seeded there from the start
(companion/world/townsfolk.py); each newcomer is rebuilt from the slot's number plus STRIDE times their
generation, so `town:<city>:<place>:1003` is the third person to hold slot 3 after the first. Keys keep their four
parts and their number, and someone who left is still found by their key: a companion who knew them remembers.

How long someone stays is seeded a year at a time from when they arrived: each year of their stay rolls once
against their chances that year (moving away, a new job, retiring, passing away), which follow their age and who
they are, and a roll that comes up picks the week they go. A newcomer takes the spot that same week, so a place
never runs short of people and a street never has a gap. Nothing is stored, and there is no horizon: the same slot on the same day has the same person, however many years on.

Nobody had left before START, so towns people already knew don't lose anyone on upgrade. A companion is never
removed: the user's own townsperson and every companion made from a townsperson keep their slot for good
(`data['you']`, `data['kept']`), and a city pack's named people stay unless the pack lets them go
(schema.Notable.can_leave).

The pace follows Realism > Their days > Life's big turns and passing away follows People can pass away and the
Loss slider, and town babies (companion/world/couples.py) follow Growing families: `load` reads them from life
settings (columns `life_turns`, `people_pass_away`, `loss` and `growing_families`, read with defaults until those
settings exist) when a world opens. Call `load` again when they change. A change only moves the town on from the
week after it (`record`, table town_levels): each year of someone's stay rolls at the levels that held when that year
began, so who left before the change, and when, stays as it was.
"""
import math
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache

from companion.clock import Clock, zone
from companion.world import generators

ACTIVE = True
STRIDE = 1000
MOST_GENERATIONS = 400
EPOCH = date(2026, 1, 5)  # townsfolk.EPOCH: weeks count from here.
START = date(2026, 10, 19)  # The Monday the town started changing hands (v0.14).
START_WEEK = (START - EPOCH).days // 7
YEAR = 52
# Each year's chance of leaving at the usual pace, by who they are, and how much likelier the young are to go.
MOVE = {'staff': 0.1, 'regular': 0.07, 'resident': 0.06}
NEW_JOB = 0.55  # Of staff who go, how many leave for another job in town rather than leaving town.
YOUNG, YOUNG_LIFT = 30, 1.6
# Staff retiring: each year's chance from these ages on, and the age by which everyone has.
RETIRE = ((62, 0.18), (66, 0.4), (70, 0.75))
RETIRED_BY = 75
# Passing away: a small chance at 30 that rises steeply with age.
DEATH_AT_30, DEATH_RISE = 0.0004, 0.09
# Life's big turns (0..3) as multipliers, and passing away: 0 off, then the Loss slider's 0..3 (rare, now and then,
# true to life, often) as 1..4.
PACE = (0.0, 0.5, 1.0, 1.6)
LOSS = (0.0, 0.25, 0.5, 1.0, 2.0)
USUAL_PACE = 2


@dataclass
class Levels:
    clock: Clock
    pace: int = USUAL_PACE
    loss: int = 0  # 0: nobody passes away; else the Loss slider plus one.
    families: int = USUAL_PACE  # Growing families (0..3): how often town couples have a baby.
    # Earlier levels and the week each stopped holding, oldest first: ((until, pace, loss, families), ...).
    before: tuple = ()


STATE = Levels(Clock())


def load(database):
    """Follow this world's clock (debug time included), its life settings and the levels they held before."""
    from companion.database import many, optional
    STATE.clock = database.clock
    with database.connect() as connection:
        row = optional(connection, 'SELECT * FROM life_settings WHERE id=1') or {}
        earlier = many(connection, 'SELECT * FROM town_levels ORDER BY until_week')
    STATE.pace, STATE.loss, STATE.families = levels_of(row)
    STATE.before = tuple((item['until_week'], item['pace'], item['loss'], item['families']) for item in earlier)


def levels_of(row: dict) -> tuple[int, int, int]:
    """(pace, loss, families) from a life_settings row."""
    loss = int(row.get('loss', 2)) + 1 if row.get('people_pass_away') else 0
    return int(row.get('life_turns', USUAL_PACE)), loss, int(row.get('growing_families', USUAL_PACE))


def record(connection, row: dict, day: date, timestamp: str):
    """Before the settings in `row` change: they keep holding through this week, so the town's past stays put."""
    until = week_of(day) + 1
    if until > START_WEEK:
        connection.execute('INSERT OR IGNORE INTO town_levels (until_week, pace, loss, families, created_at) '
                           'VALUES (?, ?, ?, ?, ?)', (until, *levels_of(row), timestamp))


def history() -> tuple:
    return STATE.before, STATE.pace, STATE.loss, STATE.families


def levels_at(week: int, found: tuple | None = None) -> tuple[int, int, int]:
    """(pace, loss, families) in a week."""
    before, *now = found or history()
    return next((tuple(item[1:]) for item in before if week < item[0]), tuple(now))


def today(data: dict) -> date:
    """Today in the city, by the app clock."""
    return STATE.clock.now().astimezone(zone(data.get('timezone') or 'UTC')).date()


def week_of(day: date) -> int:
    return (day - EPOCH).days // 7


def week_day(week: int, weekday: int = 0) -> date:
    return EPOCH + timedelta(weeks=week, days=weekday)


# How long someone stays ---------------------------------------------------------------------------

def chances(kind: str, age: int, pace: int, loss: int) -> dict[str, float]:
    """This year's chance of each way of leaving, for someone of this kind and age."""
    move = MOVE[kind] * (YOUNG_LIFT if age < YOUNG else 1.0) * PACE[pace]
    found = {'moved': move * (1 - NEW_JOB) if kind == 'staff' else move}
    if kind == 'staff':
        found['new job'] = move * NEW_JOB
        retire = 1.0 if age >= RETIRED_BY else next((chance for at, chance in reversed(RETIRE) if age >= at), 0.0)
        found['retired'] = retire if pace else 0.0
    if loss:
        found['passed'] = min(DEATH_AT_30 * math.exp(DEATH_RISE * (age - 30)) * LOSS[loss], 1.0)
    return found


@lru_cache(maxsize=65536)
def tenure(seed: str, kind: str, age: int, start: int, levels: tuple) -> tuple[int, str] | None:
    """(the week they leave, why) for someone who arrived at week `start` aged `age`, or None if they never do. Each
    year rolls at the levels (`history`) that held when it began."""
    for year in range(120):
        pace, loss, _families = levels_at(start + year * YEAR, levels)
        found = chances(kind, age + year, pace, loss)
        total = sum(found.values())
        roll = generators.unit(seed, 'turnover', year)
        if total and roll < min(total, 1.0):
            why = generators.pick(seed, f'turnover-why-{year}', sorted(found), [found[key] for key in sorted(found)])
            return start + year * YEAR + int(generators.unit(seed, 'turnover-week', year) * YEAR), why
    return None


@dataclass(frozen=True)
class Term:
    """One person's stay in a slot: from the week they arrived (None: there from the start) until the week they
    left, and why (None: still there for good)."""
    generation: int
    arrived: int | None
    left: int | None
    why: str | None


def terms(seed_of, kind: str, age_of, kept, until: int, last: int = MOST_GENERATIONS - 1) -> list[Term]:
    """Everyone who held a slot up to week `until` (or up to generation `last`), in order. `seed_of(generation)` is
    who they are drawn from, `age_of(seed, generation)` their age on arriving and `kept(generation)` whether they
    stay for good."""
    if not ACTIVE:
        return [Term(0, None, None, None)]
    result, arrived, start = [], None, START_WEEK
    for generation in range(last + 1):
        seed = seed_of(generation)
        found = None if kept(generation) else tenure(seed, kind, age_of(seed, generation), start, history())
        result.append(Term(generation, arrived, *(found or (None, None))))
        if found is None or found[0] > until:
            break
        arrived = start = found[0]
    return result


def holding(found: list[Term], week: int) -> Term | None:
    """Who holds the slot in this week (from the week they arrive until the week they leave), or None if the slot
    has run past MOST_GENERATIONS."""
    return next((term for term in found if (term.arrived is None or term.arrived <= week) and
                 (term.left is None or term.left > week)), None)


def gone_text(why: str, place: str) -> str:
    """'moved away', 'left the bakery for a new job', 'retired from the bakery', 'passed away'."""
    return {'moved': 'moved away', 'new job': f'left {place} for a new job' if place else 'took a new job',
            'retired': f'retired from {place}' if place else 'retired', 'passed': 'passed away'}[why]
