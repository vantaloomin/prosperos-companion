"""How long a hospital stay or a sick spell keeps someone in the circle out of their days (1.4.1, after #103).

When a companion says "my dad's in the hospital", the stay fits the cause the words give (Vanta, 2026-11-11):

- `overnight`: the ER, stitches, a sprain, kept in for observation. In the hospital that day, then back to normal.
- `days`: a stay with no reason given, an appendix or gallbladder, a bad flu. Two to four days in the hospital, then
  "Home, resting" for a few more. A hurt with no hospital in it (a broken wrist, a thrown-out back) is the rest only.
- `weeks`: hip, knee, heart or back surgery, a broken leg or hip, a heart attack or a stroke. Two to three days in the
  hospital, then "Home, recovering", off work for two to six weeks in all.
- `critical`: the ICU, a coma, critical condition. In the hospital until someone says otherwise.
- `treatment`: a serious diagnosis (cancer, chemo, dialysis). "In treatment" on two weekdays a week, at work the rest,
  the way a long-term condition goes (companion/life/health_turns.py), until someone says otherwise.
- `ill`: "Home sick" for two to five days.

The plan is written once, on the person's record with the news (life_changes.unwell), with seeded lengths: nothing is
asked of the user and no model is called. "They're out of the hospital" (`recovered`) ends any of it early, and so
does Undo. Their days read it through the agenda (companion/life/agenda.py `day_facts`): the blocks it covers say where
they are, and the composer writes the hospital or the sofa, not a night out.
"""
import random
import re
from datetime import date, timedelta

HOSPITAL, HOME, TREATMENT = 'In the hospital', 'Home, resting', 'In treatment'
HOME_LABELS = {'days': HOME, 'weeks': 'Home, recovering', 'ill': 'Home sick'}
HOSPITAL_DAYS = {'overnight': (1, 1), 'days': (2, 4), 'weeks': (2, 3)}
HOME_DAYS = {'days': (2, 4), 'ill': (2, 5)}
WEEKS_OFF = (14, 42)  # From the day it happened until back at work, for `weeks`.
TREATMENT_WEEKDAYS = 2  # Weekdays a week in treatment; the rest at work.
OPEN = frozenset({'critical', 'treatment'})  # Until someone says otherwise.
OUT_KINDS = {'work', 'study', 'leisure', 'social', 'errand'}
WORK_KINDS = {'work', 'study'}

# The words that say how serious it is, checked in this order on the news and what follows it.
CRITICAL = re.compile(r"\b(?:icu|intensive care|coma|critical condition|ventilator|life support|in a bad way|"
                      r"hooked up to machines)\b", re.IGNORECASE)
BIG_SURGERY = re.compile(r"\b(?:hip|knee|heart|back|spine|spinal|bypass|transplant|stent|pacemaker|cardiac|"
                         r"heart attack|stroke|pelvis|broken leg|broke (?:her|his|their) leg)\b", re.IGNORECASE)
BAD_BREAK = re.compile(r"\b(?:broke|snapped|busted|fractured|shattered|fell and broke) (?:her|his|their) "
                       r"(?:leg|hip|pelvis|knee)\b", re.IGNORECASE)
OVERNIGHT = re.compile(r"\b(?:er|a&e|emergency room|stitches|sprain\w*|twisted|overnight|spent the night|"
                       r"observation|for tests|concussion)\b", re.IGNORECASE)
SERIOUS = re.compile(r"\b(?:cancer|leukemia|lymphoma|tumou?r|chemo|radiation|dialysis|kidney failure|heart failure|"
                     r"serious|bad news|bad diagnosis|rough diagnosis|scary diagnosis|treatment|transplant)\b",
                     re.IGNORECASE)
# Already home from it: "is home after surgery", "is laid up after surgery".
HOME_NOW = re.compile(r"\b(?:home|laid up)\b", re.IGNORECASE)


def category(kind: str, words: str) -> str | None:
    """The stay that fits the news (`words`: the phrase and what came after it), or None when it changes no days."""
    if kind in ('in_hospital', 'surgery'):
        if CRITICAL.search(words):
            return 'critical'
        if BIG_SURGERY.search(words) or BAD_BREAK.search(words):
            return 'weeks'
        return 'overnight' if OVERNIGHT.search(words) else 'days'
    if kind == 'hurt':
        if BAD_BREAK.search(words):
            return 'weeks'
        return 'overnight' if OVERNIGHT.search(words) else 'days'
    if kind == 'ill':
        return 'ill'
    if kind == 'diagnosed':
        return 'treatment' if SERIOUS.search(words) else None
    return None


def plan(kind: str, given: dict | None, since: str, seed: str) -> dict:
    """The stay to keep on their record: its category and the days it ends on (the first day back to normal)."""
    given = given or {}
    found = given['stay'] if 'stay' in given else category(kind, '')
    if found is None or found in OPEN:
        return {'stay': found} if found else {}
    rng, day = random.Random(f'stay:{seed}'), date.fromisoformat(since)
    in_hospital = rng.randint(*HOSPITAL_DAYS.get(found, (0, 0)))
    if given.get('home_now') or (kind == 'hurt' and found == 'days'):
        in_hospital = 0  # Already home from it, or a broken wrist or a bad back: rest at home, no stay.
    hospital_until = day + timedelta(days=in_hospital)
    if found == 'weeks':
        home_until = day + timedelta(days=rng.randint(*WEEKS_OFF))
    elif found in HOME_DAYS:
        home_until = hospital_until + timedelta(days=rng.randint(*HOME_DAYS[found]))
    else:
        home_until = hospital_until
    return {'stay': found, 'hospital_until': hospital_until.isoformat(), 'home_until': home_until.isoformat()}


def on(health: dict | None, day: date, seed: str = '') -> dict | None:
    """Where a stay has them on a local date: {'where': 'hospital' | 'home' | 'treatment', 'label': ...}, or None."""
    if not health or not health.get('stay') or day.isoformat() < health.get('since', ''):
        return None
    stay = health['stay']
    if stay == 'critical':
        return {'where': 'hospital', 'label': HOSPITAL}
    if stay == 'treatment':
        return {'where': 'treatment', 'label': TREATMENT} if treatment_day(seed, day) else None
    if day.isoformat() < health['hospital_until']:
        return {'where': 'hospital', 'label': HOSPITAL}
    if day.isoformat() < health['home_until']:
        return {'where': 'home', 'label': HOME_LABELS.get(stay, HOME)}
    return None


def treatment_day(seed: str, day: date) -> bool:
    """Two seeded weekdays of each week."""
    if day.weekday() >= 5:
        return False
    year, week, _ = day.isocalendar()
    return day.weekday() in random.Random(f'treatment:{seed}:{year}:{week}').sample(range(5), TREATMENT_WEEKDAYS)


def apply(block: dict, where: dict | None) -> dict:
    """A block on a stay's day: the hospital takes every waking block (and the night, by its label); home takes work and
    plans; treatment takes the working day."""
    if not where:
        return block
    kind, stay = block['kind'], where['where']
    if kind == 'sleep':
        return {**block, 'label': where['label'], 'stay': stay} if stay == 'hospital' else block
    if stay == 'hospital' or (stay == 'home' and kind in OUT_KINDS) or (stay == 'treatment' and kind in WORK_KINDS):
        return {**block, 'kind': 'rest', 'label': where['label'], 'sick_day': True, 'stay': stay}
    return block
