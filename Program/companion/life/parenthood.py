"""Wanting children and the family step (Hit List #73, v0.15 Room to Grow): whether a companion wants children, and
"Starting a family", the step a romance takes beside its ladder once the pair lives together.

The app decides, the user overrides ("the world exists outside of User", Vanta 2026-10-08):

- Every companion wants children (yes), wants them someday, or not (no). Their own description says it first ("never
  wanted kids", "always wanted a big family"); otherwise the consequence engine decides it once from their age,
  warmth and description (choice family:wants), with the odds under Hidden values. A "someday" the dice picked turns
  into a yes once a baby is born in their circle (companion/life/families.py). The user can set it on the Character
  page. `wants` is the one place every feature reads it from.
- How a child would come for the user and a romance companion is picked by the app from the pair (family:route):
  who of the two could carry a baby (their pronouns and descriptions, the persona's gender and about), their ages,
  money and the era of the city; expecting (either partner), adopting, fostering or, where it fits, a surrogate in a
  modern city; taking in a ward, a foundling or a relative's child in an older one. The Character page shows it and
  the user can change it.
- "Starting a family" (`steps.FAMILY`) comes after moving in, married or not. It is stored with the ladder's steps
  (relationship_steps and step_asks, ladder `parenthood`), so asking and answering work as for every other step
  (companion/life/steps.py): once they have lived together long enough and are close enough, the engine decides how
  soon they bring it up (family:when, sooner when they want children and once married, later for "someday"), and the
  user answers yes, not yet or no in the chat. A companion who doesn't want children never brings it up; when the user
  raises it, the engine answers (family:answer), mostly no for them. Saying no to a companion who wants children can
  start a rough patch on Real life and Drama (companion/life/rough_patches.py, cause family_no), never on an easy life.

Children keep v0.14's limits: with the adult side of life on, none of this goes in a chat prompt and the step is not
brought up in a first text (`quiet`, as families.withheld); it stays on the screens. A companion who reads as a minor
has no family step. No model decides anything: the model only puts it in words.
"""
import random
import re
from datetime import date, timedelta

from companion import consequences
from companion.clock import stamp
from companion.database import many, optional
from companion.errors import require
from companion.life import steps
from companion.life.steps import FAMILY, SIBLING, STAY, USER

ACTIVE = True
LADDER = steps.FAMILY_LADDER
WANTS = ('yes', 'someday', 'no')
WANTS_LABELS = {'yes': 'Yes', 'someday': 'Someday', 'no': 'Not for them'}
# In the order of the family:route table's options.
ROUTES = ('expecting_them', 'expecting_you', 'adoption', 'fostering', 'surrogacy', 'ward', 'foundling', 'relative')
MODERN_ROUTES = ('expecting_them', 'expecting_you', 'adoption', 'fostering', 'surrogacy')
OLD_ROUTES = ('expecting_them', 'expecting_you', 'ward', 'foundling', 'relative')
ROUTE_LABELS = {'expecting_them': '{name} carries the baby', 'expecting_you': 'You carry the baby',
                'adoption': 'Adopting', 'fostering': 'Fostering, which can lead to adopting',
                'surrogacy': 'Through a surrogate', 'ward': 'Taking in a ward', 'foundling': 'Taking in a foundling',
                'relative': "Raising a relative's child"}
# Cities from these eras take in a ward, a foundling or a relative's child (companion/world/schema.py `Era`).
OLD_ERAS = {'victorian', 'steampunk', 'frontier', 'medieval', 'fantasy'}
# Before clinics (New York 1925 and older): no surrogate, and two who could both carry have no donor to turn to.
NO_CLINIC_ERAS = {*OLD_ERAS, 'jazz-age'}
# "Someday" waits twice as long at moving in before they bring it up.
SOMEDAY_WAIT = 2
# After the user says no when they bring it up, they ask once more, half a year on at the soonest (Vanta 2026-10-19); a
# second no settles it (the user can still bring it up).
NO_AGAIN_DAYS = 182
MOST_NOS = 2
# After that second no, a companion who wants children (not "someday") asks whether the two of them stay as they are
# or separate, this many days later (seeded); never on an easy life (Vanta 2026-10-19).
STAY_AFTER = (7, 21)
# Another child (companion/life/our_child.py): no sooner than this many days after the youngest came home; one more.
SIBLING_AFTER = 548
MOST_CHILDREN = 2
# ... and only while the youngest is under this age (Vanta 2026-10-19: not a 44-year-old with an 18-year-old).
SIBLING_UNDER = 10
SIBLING_LINE = ('You and the user have decided to have another child, a brother or sister for {names}. Nothing has come '
                'of it yet.')
# The engine's choices about how the child comes (companion/life/expecting.py).
JOURNEY = ('family:soon', 'family:turn', 'family:wait', 'family:match', 'family:fostered')

# What their own description says, read in this order: "never wanted kids" before "wanted kids", "kids someday"
# before "wants kids". Each list is a set of alternatives.
_KIDS = r'(?:kids|children|a child|a baby|babies|a family|a big family)'
_PARENT = r'(?:a )?(?:mom|mum|mother|dad|father|parent)'
_SELF = r'(?:her|him|them|my|your|one)sel(?:f|ves)'
_WANT = r'want(?:s|ed)?'
_NOT = r"(?:don'?t|doesn'?t|do not|does not|won'?t|didn'?t|did not|never)"
# "never wanted kids to see her cry" is not about wanting children.
_NOT_ABOUT = r'(?! (?:to|around|near|in|at)\b)'
_SAYS_NO = (
    rf"never (?:planned on|planned to have) {_KIDS}",
    rf"{_NOT} (?:ever |really )?{_WANT} (?:to (?:have|raise) )?{_KIDS}{_NOT_ABOUT}",
    rf"{_NOT} (?:ever |really )?{_WANT} to be {_PARENT}",
    r'child[- ]?free',
    rf"no (?:interest in|desire for|plans for|intention of|wish for|wish to have) (?:having |raising )?{_KIDS}",
    r'not (?:the|a) (?:parenting|parent|maternal|paternal|family|kids?|baby) (?:type|person)',
    r"(?:hates|can'?t stand) (?:kids|children)",
    r"(?:kids|children|motherhood|fatherhood|parenthood|parenting|a family) (?:are|is|were|was|aren'?t|isn'?t|weren'?t|"
    r"wasn'?t) (?:never |not )?(?:in the cards|for (?:me|him|her|them))",
    r'decided (?:against|not to have) (?:having )?(?:kids|children)',
    r"(?:would|'d) rather not have (?:kids|children)",
    rf"never (?:saw|sees|see|pictured|imagined) {_SELF} (?:as {_PARENT}|with (?:kids|children))",
    rf"can'?t (?:imagine|see) (?:{_SELF} )?(?:being {_PARENT}|as {_PARENT}|having (?:kids|children))",
)
_SAYS_SOMEDAY = (
    rf"{_KIDS} (?:someday|some day|one day|eventually|down the line|later on)(?! soon)",
    r'maybe (?:kids|children)',
    r'someday,? (?:kids|children|a family)',
    r'not ready for (?:kids|children|a family|a baby) yet',
    r'(?:kids|children)\W+maybe later',
)
_SAYS_YES = (
    rf"(?:always )?(?:{_WANT}|hop(?:es|ing)? to have|(?:would|'d) like to have) {_KIDS}{_NOT_ABOUT}",
    rf"(?:always )?{_WANT} to (?:have|start|raise) {_KIDS}",
    rf"(?:always )?{_WANT} to be {_PARENT}",
    rf"{_WANT} (?:a houseful|lots|a bunch|two|three|four|five|several) (?:of )?(?:kids|children)",
    rf"dreams? (?:of|about) (?:a family|having (?:kids|children)|being {_PARENT})",
    rf"(?:would|'d) love (?:kids|children|a family|to be {_PARENT})",
    rf"can'?t wait to (?:be {_PARENT}|have (?:kids|children|a family|a baby))",
    r'baby fever',
    r'longs? for (?:a family|children|kids)',
    r'family[- ](?:minded|oriented)',
    rf"(?:always )?(?:pictured|pictures|imagined|imagines|sees|saw) {_SELF} (?:with (?:kids|children)|as {_PARENT})",
)
SAYS = tuple((wants, re.compile(rf"\b(?:{'|'.join(found)})\b", re.IGNORECASE))
             for wants, found in (('no', _SAYS_NO), ('someday', _SAYS_SOMEDAY), ('yes', _SAYS_YES)))
CANT = re.compile(r"\b(?:can'?t (?:have|carry) (?:kids|children|a baby|a child)|infertile|unable to have (?:kids|"
                  r"children)|had a hysterectomy|trans(?:gender)? (?:woman|girl)|(?:assigned )?male at birth|amab)\b",
                  re.IGNORECASE)
# A description that says they could carry a baby, whatever their pronouns: a trans man, someone assigned female at
# birth, "could get pregnant".
CAN = re.compile(r"\b(?:trans(?:gender)? (?:man|guy|boy)|(?:assigned )?female at birth|afab|(?:can|could) (?:get "
                 r"pregnant|carry (?:a baby|a child|children))|(?:has|have) a (?:uterus|womb))\b", re.IGNORECASE)

# The chat context ('steps' section): where they stand on children, and the family step once decided.
WANT_LINES = {'yes': 'On children: you would like to have children one day. If it comes up, say so honestly.',
              'someday': 'On children: you might want children someday, but not any time soon. If it comes up, say '
                         'so honestly.',
              'no': "On children: you don't want children of your own. If it comes up, say so honestly and kindly."}
ROUTE_WORDS = {'expecting_them': 'you would carry the baby', 'expecting_you': 'the user would carry the baby',
               'adoption': 'you would adopt', 'fostering': 'you would foster, which may lead to adopting',
               'surrogacy': 'you would have a baby through a surrogate', 'ward': 'you would take in a ward',
               'foundling': 'you would take in a foundling', 'relative': "you would raise a relative's child"}
STAYED_LINE = ('You and the user settled on {on} that you stay together as you are, without children of your own. It '
               'is settled: do not bring up having children again.')
STEP_LINE = ('You and the user have decided to start a family together; when it happens, {route}. Nothing has come of '
             'it yet: nobody is expecting and nothing has been arranged.')


def first(companion: dict) -> str:
    return companion['version']['definition']['name'].split()[0]


def quiet(connection) -> bool:
    """With the adult side of life on, children stay out of chat prompts and first texts (companion/life/families.py)."""
    from companion.life import families
    return families.withheld(connection)


def wishes(connection, companion_id: str) -> dict:
    return optional(connection, 'SELECT * FROM family_wishes WHERE companion_id=?', (companion_id,)) or {}


# Wanting children ------------------------------------------------------------------------------------------------------

def described(definition: dict) -> str | None:
    """'yes', 'someday' or 'no' when their own description says it, else None."""
    themes = ' '.join(definition.get('life_themes') or [])
    text = f"{consequences.sheet_text(definition)} {definition.get('history_together') or ''} {themes}"
    text = text.replace('\u2019', "'").replace('\u2018', "'")  # "doesn’t" as typed on a phone.
    return next((wants for wants, pattern in SAYS if pattern.search(text)), None)


def age_of(connection, companion: dict, now) -> int:
    """Their life age (companion/world/lifespans.py), what the family odds read: their real age for a human."""
    from companion.life import ages
    day = steps.local_today(companion, now) if now else None
    return ages.companion_life_age(connection, companion['id'], companion['version']['definition'], day) or 0


def wants_facts(connection, companion: dict, now) -> dict:
    from companion.world import personality
    definition = companion['version']['definition']
    levels = personality.levels_of(definition.get('personality_sliders') or {})
    return {'age': age_of(connection, companion, now), 'warmth': levels.get('warmth', 1),
            'sheet': {group for group in consequences.WORDS if consequences.sheet_has(definition, group)}}


def rolled(connection, companion: dict, choice: str, subject: str, facts: dict, now) -> dict:
    """The engine's outcome for a choice decided once per companion: recorded with `now`, else worked out with the
    same seed and not kept (a read with no clock)."""
    if now is not None and companion.get('active_timeline_id'):
        return steps.decide(connection, companion, choice, subject, facts, FAMILY.topic, now)
    found = consequences.recorded(connection, subject, choice)
    if found:
        return found
    options = consequences.odds(choice, facts, steps.names(companion, FAMILY.topic))
    return {'id': None, 'picked': consequences.roll(f"{companion.get('active_timeline_id')}:{subject}:{choice}", options),
            'decided_on': None}


def wants_found(connection, companion: dict, now=None) -> dict:
    """{wants, how ('set', 'description', 'seeded' or 'nudged'), consequence_id, nudged_by}."""
    set_to = wishes(connection, companion['id']).get('wants')
    if set_to:
        return {'wants': set_to, 'how': 'set', 'consequence_id': None, 'nudged_by': None}
    said = described(companion['version']['definition'])
    if said:
        return {'wants': said, 'how': 'description', 'consequence_id': None, 'nudged_by': None}
    outcome = rolled(connection, companion, 'family:wants', f"family:wants:{companion['id']}",
                     wants_facts(connection, companion, now), now)
    found = {'wants': WANTS[outcome['picked']], 'how': 'seeded', 'consequence_id': outcome['id'], 'nudged_by': None}
    baby = nudged_by(connection, companion, outcome) if found['wants'] == 'someday' else None
    return {**found, 'wants': 'yes', 'how': 'nudged', 'nudged_by': baby} if baby else found


def nudged_by(connection, companion: dict, outcome: dict) -> str | None:
    """A baby born in their circle since it was decided turns a seeded "someday" into a yes: the baby's name."""
    if not outcome.get('decided_on') or not companion.get('active_timeline_id'):
        return None
    row = optional(connection, "SELECT name FROM circle_children WHERE timeline_id=? AND status='born' AND born_on>=? "
                   'ORDER BY born_on LIMIT 1', (companion['active_timeline_id'], outcome['decided_on']))
    return row['name'] if row else None


def wants(connection, companion: dict, now=None) -> str:
    """Whether this companion wants children: 'yes', 'someday' or 'no'. The one source for every feature."""
    return wants_found(connection, companion, now)['wants']


# How a child would come -------------------------------------------------------------------------------------------------

def persona(connection) -> dict:
    return optional(connection, 'SELECT gender, age, about FROM persona WHERE id=1') or {}


def old_era(connection, companion: dict) -> bool:
    return era(connection, companion) in OLD_ERAS


def era(connection, companion: dict) -> str:
    from companion.life import families
    return families.era_of(connection, companion['version']['definition'])


def route_facts(connection, companion: dict, now) -> dict:
    from companion.life import ages, money
    from companion.world import looks
    definition = companion['version']['definition']
    you = persona(connection)
    can_them = could_carry(consequences.sheet_text(definition), looks.pronouns_of(definition) == 'she/her')
    can_you = could_carry(you.get('about') or '', you.get('gender') == 'woman')
    found = money.profile(definition)
    clinic = int(era(connection, companion) not in NO_CLINIC_ERAS)
    return {'can_them': can_them, 'can_you': can_you, 'can_carry': int(can_them or can_you),
            'no_donor': int(bool(can_them and can_you and not clinic)),
            'age': age_of(connection, companion, now), 'your_age': ages.persona_life_age(connection, you, definition),
            'tier': found.tier if found else 1, 'old': int(old_era(connection, companion)),
            'surrogate': clinic}


def could_carry(text: str, by_default: bool) -> int:
    """Whether someone could carry a baby: their description says so either way, else by their pronouns or gender."""
    text = text.replace('\u2019', "'")
    return int(not CANT.search(text) and (by_default or bool(CAN.search(text))))


def route_found(connection, companion: dict, now=None) -> dict:
    """{route, how ('set' or 'seeded'), consequence_id} for the user and this companion."""
    set_to = wishes(connection, companion['id']).get('route')
    if set_to:
        return {'route': set_to, 'how': 'set', 'consequence_id': None}
    outcome = rolled(connection, companion, 'family:route', f"family:route:{companion['id']}",
                     route_facts(connection, companion, now), now)
    return {'route': ROUTES[outcome['picked']], 'how': 'seeded', 'consequence_id': outcome['id']}


def routes_for(found_era: str) -> tuple[str, ...]:
    """The ways a child could come that fit the city's era."""
    if found_era in OLD_ERAS:
        return OLD_ROUTES
    return tuple(key for key in MODERN_ROUTES if key != 'surrogacy' or found_era not in NO_CLINIC_ERAS)


def route_label(route: str, companion: dict) -> str:
    return ROUTE_LABELS[route].format(name=first(companion))


def settle(connection, companion: dict, now) -> None:
    """Once a day: what they want and, for a romance, how a child would come are decided and kept, so a chat context
    (read only) reads the same pick."""
    if not ACTIVE or not companion.get('active_timeline_id'):
        return
    wants_found(connection, companion, now)
    if companion['version']['definition'].get('relationship') == 'romance':
        route_found(connection, companion, now)


# The family step -----------------------------------------------------------------------------------------------------------

def reached(connection, timeline_id: str, key: str = FAMILY.key) -> dict | None:
    """Starting a family reached (or, with `key` 'sibling', another child), not taken back."""
    return next((row for row in steps.reached(connection, timeline_id, LADDER) if row['step'] == key), None)


def ours(connection, timeline_id: str) -> list[dict]:
    """The pair's own children home with them, oldest first (companion/life/our_child.py)."""
    from companion.life import our_child
    return our_child.children(connection, timeline_id)


def children_names(connection, companion: dict) -> str:
    return steps.names_text([row['name'].split()[0] for row in ours(connection, companion['active_timeline_id'])])


def sibling_open(connection, companion: dict, found: dict | None, today: date | None = None) -> bool:
    """Whether another child can come up: they decided on a family, live together and aren't apart, their only child
    is home (by `today`, a year and a half or more, and under ten), nothing else is on the way and it isn't decided
    yet."""
    from companion.life import expecting
    from companion.world import intimacy
    timeline_id = companion['active_timeline_id']
    kids = ours(connection, timeline_id)
    if not ACTIVE or len(kids) != 1 or reached(connection, timeline_id, SIBLING.key) or not living_on(found):
        return False
    journey = expecting.current(connection, timeline_id)
    if (journey and journey['status'] != 'home') or steps.apart(connection, companion) or \
            intimacy.reads_as_minor(companion['version']['definition']):
        return False
    home = date.fromisoformat((journey or {}).get('arrived_on') or kids[0]['born_on'])
    return today is None or ((today - home).days >= SIBLING_AFTER and young_enough(kids, today))


def young_enough(kids: list[dict], today: date) -> bool:
    """Another child comes up only while the youngest is under ten."""
    from companion.life import families
    return families.age_of(kids[-1], today) < SIBLING_UNDER


def living_on(found: dict | None) -> str | None:
    """The day they decided to live together, while the romance is there or further along."""
    if not found or found['ladder'] != 'romance':
        return None
    if steps.index_of('romance', found['step']) < steps.index_of('romance', 'moving_in'):
        return None
    return next((item['on'] for item in found['steps'] if item['step'] == 'moving_in'), found['since'])


def open_to(connection, companion: dict, found: dict | None) -> bool:
    """Whether the family step can come up now: they live together, it isn't reached, they aren't apart."""
    from companion.world import intimacy
    if not living_on(found) or reached(connection, companion['active_timeline_id']):
        return False
    return not steps.apart(connection, companion) and not intimacy.reads_as_minor(companion['version']['definition'])


def facts(connection, companion: dict, found: dict, now) -> dict:
    """The step's facts (companion/life/steps.py `facts`), with the days counted from moving in, whether they want
    children, whether they are married and their age."""
    wanted = wants(connection, companion, now)
    found_facts = steps.facts(connection, companion, found, FAMILY, now)
    days = (steps.local_today(companion, now) - date.fromisoformat(living_on(found))).days
    needed = FAMILY.after[steps.timing(connection) - 1] * (SOMEDAY_WAIT if wanted == 'someday' else 1)
    married = int(any(item['step'] == 'married' for item in found['steps']))
    return {**found_facts, 'days': days, 'short_days': max(needed - days, 0), 'wants': wanted, 'married': married,
            'age': age_of(connection, companion, now)}


def plan(connection, companion: dict, found: dict, now) -> dict | None:
    """Once they have lived together long enough and are close enough, the engine decides how soon they bring up
    starting a family. Never when they don't want children, nor with nothing else waiting on an answer."""
    timeline_id = companion['active_timeline_id']
    if ACTIVE and steps.pace(connection) and reached(connection, timeline_id):
        return plan_sibling(connection, companion, found, now)
    if not ACTIVE or not steps.pace(connection) or not open_to(connection, companion, found):
        return None
    if quiet(connection) or steps.asks(connection, timeline_id, ('planned', 'open')):
        return None
    found_facts = facts(connection, companion, found, now)
    today = steps.local_today(companion, now)
    if len(noes(connection, timeline_id)) >= MOST_NOS:
        return plan_stay(connection, companion, found_facts['wants'], now)
    if found_facts['wants'] == 'no' or found_facts['short_days'] or found_facts['closeness_over'] < 0 or \
            steps.waiting(connection, timeline_id, FAMILY.key, today) or told_no(connection, timeline_id, today):
        return None
    turn = 1 + len(many(connection, 'SELECT id FROM step_asks WHERE timeline_id=? AND other=? AND step=? AND side=?',
                        (timeline_id, USER, FAMILY.key, 'them')))
    outcome = steps.decide(connection, companion, 'family:when', f'family:when:{timeline_id}:{turn}', found_facts,
                           FAMILY.topic, now)
    low, high = steps.WHEN[outcome['picked']]
    offset = random.Random(f'{timeline_id}:{FAMILY.key}:{turn}:when').randint(low, high)
    return steps.insert_ask(connection, timeline_id, LADDER, FAMILY.key, 'them', 'planned', stamp(now),
                            due_on=today + timedelta(days=offset), consequence_id=outcome['id'], turn=turn)


def noes(connection, timeline_id: str) -> list[dict]:
    """The user's noes when they brought up starting a family, newest first."""
    return many(connection, "SELECT settled_at FROM step_asks WHERE timeline_id=? AND other=? AND step=? AND side='them' "
                "AND status='no' AND settled_at IS NOT NULL ORDER BY settled_at DESC", (timeline_id, USER, FAMILY.key))


def told_no(connection, timeline_id: str, today: date) -> bool:
    """The user said no when they brought it up: twice, or once less than half a year ago."""
    nos = noes(connection, timeline_id)
    if len(nos) >= MOST_NOS:
        return True
    return bool(nos) and (today - date.fromisoformat(nos[0]['settled_at'][:10])).days < NO_AGAIN_DAYS


def plan_stay(connection, companion: dict, wanted: str, now) -> dict | None:
    """Two noes to a companion who wants children: a week or few after the second, they ask whether the two of them
    stay as they are or separate, once. "Someday" lets it rest, and so does an easy life (no breakups there)."""
    timeline_id = companion['active_timeline_id']
    if wanted != 'yes' or not may_part(connection, companion) or stay_ask(connection, timeline_id):
        return None
    last = date.fromisoformat(noes(connection, timeline_id)[0]['settled_at'][:10])
    offset = random.Random(f'{timeline_id}:{STAY.key}:when').randint(*STAY_AFTER)
    return steps.insert_ask(connection, timeline_id, LADDER, STAY.key, 'them', 'planned', stamp(now),
                            due_on=max(last + timedelta(days=offset), steps.local_today(companion, now)))


def may_part(connection, companion: dict) -> bool:
    """Separating can happen: Breaks and breakups apply and rough patches are true to life or more, so never on an
    easy life (companion/life/breakups.py)."""
    from companion.life import breakups, rough_patches
    return breakups.applies(connection, companion) and rough_patches.level(connection) >= 2


def stay_ask(connection, timeline_id: str) -> dict | None:
    """Their ask whether to stay as they are or separate, any but one given way to something else."""
    return optional(connection, "SELECT * FROM step_asks WHERE timeline_id=? AND other=? AND step=? AND status<>'dropped' "
                    'ORDER BY created_at DESC LIMIT 1', (timeline_id, USER, STAY.key))


def plan_sibling(connection, companion: dict, found: dict, now) -> dict | None:
    """A year and a half after their only child came home, the engine decides how soon they bring up another child
    (family:another). Never when they don't want children, and on easy kids (Family life 0) only when the user
    brings it up."""
    from companion.life import our_child
    timeline_id, today = companion['active_timeline_id'], steps.local_today(companion, now)
    if quiet(connection) or not our_child.level(connection) or steps.asks(connection, timeline_id, ('planned', 'open')):
        return None
    if not sibling_open(connection, companion, found, today) or steps.waiting(connection, timeline_id, SIBLING.key, today):
        return None
    found_facts = sibling_facts(connection, companion, found, now)
    if found_facts['wants'] == 'no' or found_facts['closeness_over'] < 0:
        return None
    turn = 1 + len(many(connection, 'SELECT id FROM step_asks WHERE timeline_id=? AND other=? AND step=? AND side=?',
                        (timeline_id, USER, SIBLING.key, 'them')))
    outcome = steps.decide(connection, companion, 'family:another', f'family:another:{timeline_id}:{turn}', found_facts,
                           SIBLING.topic, now)
    low, high = steps.WHEN[outcome['picked']]
    offset = random.Random(f'{timeline_id}:{SIBLING.key}:{turn}:when').randint(low, high)
    return steps.insert_ask(connection, timeline_id, LADDER, SIBLING.key, 'them', 'planned', stamp(now),
                            due_on=today + timedelta(days=offset), consequence_id=outcome['id'], turn=turn)


def sibling_facts(connection, companion: dict, found: dict, now) -> dict:
    """The family step's facts, with the youngest's age and Family life's level."""
    from companion.life import families, our_child
    kids = ours(connection, companion['active_timeline_id'])
    youngest = families.age_of(kids[-1], steps.local_today(companion, now)) if kids else 0
    return {**facts(connection, companion, found, now), 'short_days': 0, 'youngest': youngest,
            'level': our_child.level(connection)}


def still_due(connection, companion: dict, found: dict | None, key: str = FAMILY.key, today: date | None = None) -> bool:
    """A planned ask still holds while the step can come up (another child, by `today`'s date when given)."""
    if key == SIBLING.key:
        return sibling_open(connection, companion, found, today)
    if key == STAY.key:
        return open_to(connection, companion, found) and may_part(connection, companion) and \
            wants(connection, companion) == 'yes'
    return open_to(connection, companion, found)


def raised_by_user(connection, companion: dict, found: dict, message: dict, now, step=FAMILY) -> bool:
    """The user brought up starting a family (or another child): the engine decides the companion's answer (yes, not
    yet or no)."""
    timeline_id, timestamp = companion['active_timeline_id'], stamp(now)
    for row in steps.asks(connection, timeline_id, ('planned',)):
        connection.execute("UPDATE step_asks SET status='dropped', settled_at=? WHERE id=?", (timestamp, row['id']))
    another = step.key == SIBLING.key
    choice = 'family:another_answer' if another else 'family:answer'
    found_facts = sibling_facts(connection, companion, found, now) if another else facts(connection, companion, found,
                                                                                           now)
    outcome = steps.decide(connection, companion, choice, f"{choice}:{timeline_id}:{message['id']}", found_facts,
                           step.topic, now)
    status = ('yes', 'not_yet', 'no')[outcome['picked']]
    row = steps.insert_ask(connection, timeline_id, LADDER, step.key, 'you', status, timestamp,
                           message_id=message['id'], consequence_id=outcome['id'])
    if status == 'yes':
        steps.insert_step(connection, timeline_id, LADDER, step.key, steps.local_today(companion, now), 'you',
                          timestamp, row['id'])
        for waiting_ask in steps.asks(connection, timeline_id, ('open',)):
            if waiting_ask['ladder'] == LADDER:
                connection.execute("UPDATE step_asks SET status='dropped', settled_at=? WHERE id=?",
                                   (timestamp, waiting_ask['id']))
    return True


def answered(connection, companion: dict, ask: dict, said: str, message: dict, now) -> None:
    """The user answered when they brought it up: a no to a companion who wants children can start a rough patch (on
    Real life and Drama; companion/life/rough_patches.py keeps it off an easy life). Choosing to separate ends it
    (companion/life/breakups.py); staying settles it for good."""
    if ask['step'] == STAY.key:
        if said == 'no' and may_part(connection, companion):
            from companion.life import breakups
            breakups.parted(connection, companion, message, now)
        return
    if said != 'no' or ask['side'] != 'them' or ask['step'] != FAMILY.key or wants(connection, companion, now) != 'yes':
        return
    from companion.life import rough_patches
    rough_patches.consider(connection, companion, 'family_no', f"family:{ask['id']}",
                           'the user said no when you brought up starting a family', now,
                           shown='over you saying no to starting a family')


def follow_step(connection, companion: dict, now) -> None:
    """The user set the romance back before living together: the family step goes back too."""
    found = steps.state(connection, companion, now, write=False)
    row = reached(connection, companion['active_timeline_id'])
    if row and not living_on(found):
        connection.execute('UPDATE relationship_steps SET undone_at=? WHERE id=?', (stamp(now), row['id']))


# The chat context and the Character page ----------------------------------------------------------------------------------

def context_lines(connection, companion: dict, found: dict, now) -> list[tuple[str, str]]:
    """Where they stand on children, and the family step once decided, for the 'steps' section."""
    if not ACTIVE or quiet(connection) or found['ladder'] not in steps.LADDERS:
        return []
    wanted = wants(connection, companion)  # No clock: the context is read, never written (`settle` records it).
    result = [(f'family:wants:{wanted}', f'- {WANT_LINES[wanted]}')]
    stayed = stay_ask(connection, companion['active_timeline_id'])
    if stayed and stayed['status'] in ('yes', 'lapsed') and found['ladder'] == 'romance':
        on = steps.long_date(stayed['settled_at'][:10])
        result.append((f"family:stayed:{stayed['id']}", f'- {STAYED_LINE.format(on=on)}'))
    if found['ladder'] == 'romance' and reached(connection, companion['active_timeline_id']):
        route = route_found(connection, companion)['route']
        from companion.life import expecting
        lines = expecting.context_lines(connection, companion, now)
        if not lines and not ours(connection, companion['active_timeline_id']):
            # Once under way (companion/life/expecting.py), what is happening replaces the plan.
            result.append((f'family:step:{route}', f'- {STEP_LINE.format(route=ROUTE_WORDS[route])}'))
        elif sibling_waiting(connection, companion):
            names = children_names(connection, companion)
            result.append(('family:sibling', f'- {SIBLING_LINE.format(names=names)}'))
        result += lines
    return result


def journey_lines(connection, companion: dict, now) -> list[tuple[str, str]]:
    """After a breakup, a child still on the way (or just come) goes on (companion/life/expecting.py), in the same
    words as before."""
    from companion.life import expecting
    if not ACTIVE or quiet(connection) or not companion.get('active_timeline_id'):
        return []
    return expecting.context_lines(connection, companion, now)


def sibling_waiting(connection, companion: dict) -> bool:
    """Another child decided on, and nothing under way for them yet."""
    from companion.life import expecting
    timeline_id = companion['active_timeline_id']
    journey = expecting.current(connection, timeline_id)
    return bool(reached(connection, timeline_id, SIBLING.key)) and len(ours(connection, timeline_id)) < MOST_CHILDREN \
        and (journey is None or journey['status'] in ('home', 'planned'))


def view(connection, companion: dict, now, show_odds: bool) -> dict:
    """What the Family panel shows: whether they want children and why, and for a romance how a child would come and
    whether you two have decided to start a family."""
    from companion.world import intimacy
    definition = companion['version']['definition']
    if intimacy.reads_as_minor(definition):
        return {'shown': False}
    found = wants_found(connection, companion, now)
    result = {'shown': True, 'wants': found['wants'], 'wants_how': found['how'], 'nudged_by': found['nudged_by'],
              'wants_consequence_id': found['consequence_id'] if show_odds else None,
              'wants_options': [{'key': key, 'label': WANTS_LABELS[key]} for key in WANTS], 'romance': False}
    if definition.get('relationship') != 'romance' or not companion.get('active_timeline_id'):
        return result
    from companion.life import expecting
    route = route_found(connection, companion, now)
    row = reached(connection, companion['active_timeline_id'])
    journey = expecting.panel(connection, companion, now, show_odds)
    shown = routes_for(era(connection, companion))
    keys = shown if route['route'] in shown else (*shown, route['route'])
    return {**result, 'romance': True, 'route': route['route'], 'route_how': route['how'],
            'route_consequence_id': route['consequence_id'] if show_odds else None,
            'routes': [{'key': key, 'label': route_label(key, companion)} for key in keys],
            'decided_on': row['reached_on'] if row else None, 'decided_how': row['how'] if row else None,
            'can_decide': not under_way(journey) and (bool(row) or bool(living_on(steps.state(connection, companion, now,
                                                                                               write=False)))),
            'journey': journey, **another_view(connection, companion, now)}


def another_view(connection, companion: dict, now) -> dict:
    """Another child: whether you two decided on one, and whether it can be set now."""
    timeline_id = companion['active_timeline_id']
    row = reached(connection, timeline_id, SIBLING.key)
    found = steps.state(connection, companion, now, write=False)
    return {'another_on': row['reached_on'] if row else None,
            'can_decide_another': sibling_waiting(connection, companion) if row else
            sibling_open(connection, companion, found, steps.local_today(companion, now))}


def under_way(journey: dict | None) -> bool:
    """Once anything has happened (companion/life/expecting.py), the route and the step stay as they are."""
    return bool(journey) and journey['status'] != 'planned'


def update(connection, companion: dict, now, wants_to: str | None = None, route: str | None = None,
           decided: bool | None = None, name: str | None = None, another: bool | None = None) -> None:
    """The user sets what they want ('auto' lets the app decide again), how a child would come, the step, or the
    child's name."""
    from companion.life import expecting
    timestamp = stamp(now)
    journey = expecting.current(connection, companion['active_timeline_id']) if companion.get('active_timeline_id') \
        else None
    require(not under_way(journey) or (route is None and decided is None), 'A child is already on the way.', 409)
    if name is not None:
        expecting.rename(connection, companion, name, now)
    require(wants_to in (None, 'auto', *WANTS), 'Pick yes, someday or not for them.', 422)
    require(route in (None, 'auto', *ROUTES), 'Pick one of the ways a child could come.', 422)
    current = wishes(connection, companion['id'])
    values = {'wants': current.get('wants'), 'route': current.get('route')}
    if wants_to is not None:
        values['wants'] = None if wants_to == 'auto' else wants_to
    if route is not None:
        values['route'] = None if route == 'auto' else route
    connection.execute('INSERT INTO family_wishes (companion_id, wants, route, updated_at) VALUES (?, ?, ?, ?) '
                       'ON CONFLICT(companion_id) DO UPDATE SET wants=excluded.wants, route=excluded.route, '
                       'updated_at=excluded.updated_at', (companion['id'], values['wants'], values['route'], timestamp))
    if decided is not None:
        set_step(connection, companion, decided, now)
    if another is not None:
        set_step(connection, companion, another, now, SIBLING)


def set_step(connection, companion: dict, decided: bool, now, step=FAMILY) -> None:
    """Decided on the Character page: reached today; taken back: undone. Asks waiting about it give way. Another child
    can be set only while it could come up, and taken back only before anything happened."""
    require(companion['version']['definition'].get('relationship') == 'romance', 'Only a romance has this step.', 422)
    timeline_id, timestamp = companion['active_timeline_id'], stamp(now)
    row = reached(connection, timeline_id, step.key)
    if step.key == SIBLING.key:
        found = steps.state(connection, companion, now, write=False)
        require(sibling_waiting(connection, companion) if row else
                sibling_open(connection, companion, found, steps.local_today(companion, now)),
                'Another child can\'t be set now.', 409)
    if decided and not row:
        steps.insert_step(connection, timeline_id, LADDER, step.key, steps.local_today(companion, now), 'set',
                          timestamp)
    elif not decided and row:
        connection.execute('UPDATE relationship_steps SET undone_at=? WHERE id=?', (timestamp, row['id']))
    for ask in steps.asks(connection, timeline_id, ('planned', 'open')):
        if ask['ladder'] == LADDER:
            connection.execute("UPDATE step_asks SET status='dropped', settled_at=? WHERE id=?", (timestamp, ask['id']))


def change(connection, companion: dict, consequence_id: str, option: int, now) -> dict:
    """The user makes a decision go another way (Hidden values): how soon they bring it up moves its day; their answer
    when the user brought it up moves the step with it; what they want and how a child would come follow the pick."""
    outcome = consequences.change(connection, consequence_id, option, stamp(now))
    row = optional(connection, 'SELECT * FROM step_asks WHERE consequence_id=?', (consequence_id,))
    if outcome['choice'] in ('family:when', 'family:another') and row and row['status'] == 'planned':
        low, high = steps.WHEN[option]
        offset = random.Random(f"{row['timeline_id']}:{row['step']}:{row['round']}:when").randint(low, high)
        created = date.fromisoformat(row['created_at'][:10])
        connection.execute('UPDATE step_asks SET due_on=? WHERE id=?',
                           ((created + timedelta(days=offset)).isoformat(), row['id']))
    elif outcome['choice'] == 'family:care':
        from companion.life import our_child  # Who stays home: the days and money read the pick.
        our_child.change(connection, companion, consequence_id, option, now)
    elif outcome['choice'] in JOURNEY:
        from companion.life import expecting
        expecting.change(connection, companion, consequence_id, now)
    elif outcome['choice'] in ('family:answer', 'family:another_answer') and row:
        status = ('yes', 'not_yet', 'no')[option]
        connection.execute('UPDATE step_asks SET status=? WHERE id=?', (status, row['id']))
        connection.execute('UPDATE relationship_steps SET undone_at=? WHERE ask_id=? AND undone_at IS NULL',
                           (stamp(now), row['id']))
        if status == 'yes' and not reached(connection, row['timeline_id'], row['step']):
            steps.insert_step(connection, row['timeline_id'], LADDER, row['step'], steps.local_today(companion, now),
                              'you', stamp(now), row['id'])
    return consequences.by_id(connection, consequence_id)
