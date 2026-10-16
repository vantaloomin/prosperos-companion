"""Next steps (Hit List #60, v0.13 Life Together): the steps a relationship moves up, one ladder for every pair.

A pair (the user and a companion now; a companion and their partner later) sits on a ladder of steps, each stored with
the day it was reached (table relationship_steps). Romance goes dating, exclusive, the first "I love you", meeting their
people, a key to their place, moving in, engaged and married; a friendship goes friends, best friends, a first trip
together and standing up at their wedding. Mentor, family and other have no ladder. The step is never a score: it is
where things stand, said in one plain line on the Character page ("Together 8 months, exclusive") and in the chat
context, which keeps the companion from acting further along than they are.

The app decides, the user overrides ("the world exists outside of User", Vanta 2026-10-08):

- A companion with no steps yet starts at one the app picks, with no question asked: from how they know each other
  ("married for ten years" starts at married), else from closeness and the days talked (`start`).
- Once enough time has passed at a step and closeness is high enough, the consequence engine decides when they bring
  up the next one (choice `steps:when`: soon, in a few weeks or in a couple of months, from the Relationship pace slider,
  their description, their personality sliders and their mood lately). On that day they bring it up in a first text
  (companion/life/openers.py). The user's answer is read from the chat with fixed phrases: yes moves up, "not yet" waits
  and they ask again weeks later, no keeps it where it is for a long while. No answer in a few days counts as not yet.
- The user can raise the next step themselves ("can we be exclusive?", "I love you"), caught from the chat with fixed
  phrases the way recommendations are; the engine decides their answer (`steps:answer`) before the reply is written,
  and the reply says it.
- Friends can fall for you: now and then a close friend falls for the user (`steps:falls`, rare on a real life, likelier
  with more drama, never with the switch off or the companion's "just friends" lock on). It is a confession, never a
  silent change: yes makes them a romance at dating (a new character version), no keeps the friendship after a short
  awkward spell (a mood mark). The user can tell a friend how they feel too (`steps:friend_answer`).
- Steps whose life changes come with later features are brought up as each lands: moving in (companion/life/moving_in.py
  settles where and who moves once it is reached), and the engagement: they propose in person, on an evening out, and
  the wedding makes them married (companion/life/wedding.py). The user can still set any step on the Character page,
  or move it back.

Each step is an anniversary (companion/life/occasions.py) and a line in the scrapbook (companion/life/scrapbook.py).
Odds show under Hidden values ("Why it went this way"). No model decides anything: the model only puts it in words.
"""
import json
import random
import re
from dataclasses import dataclass
from datetime import date, timedelta
from functools import cache

from companion import consequences
from companion.clock import parse, stamp, zone
from companion.database import identifier, many, optional
from companion.errors import require
from companion.life import own_plans
from companion.world import catalog

ACTIVE = True
# Asks and confessions as first texts; off in most tests (tests/conftest.py).
FIRST_TEXTS = True
DEFAULT_PACE = 2
USER = 'user'
# An ask still open after this many days lapses: the user let it pass, which counts as not yet.
OPEN_DAYS = 3
# After "not yet" (or no answer) they wait this long before bringing it up again, by pace (slow, true to life, fast);
# after no, much longer.
WAIT_AFTER = (60, 35, 21)
NO_HOLD = 180
# When they bring it up, once the engine has picked how soon: days from the day it was decided.
WHEN = ((1, 7), (14, 35), (45, 75))
# A friend falling for the user: a seeded check once a month, only once they are this close and have known the user
# this long; never again within a year of a confession.
FALL_CLOSENESS = 4
FALL_AFTER = 60
FALL_HOLD = 365
# How long things stay awkward after the user says they only see a friend as a friend.
AWKWARD_DAYS = 5
# How long the chat context keeps a step just reached, or an answer just given.
FRESH = timedelta(hours=12)


@dataclass(frozen=True)
class Step:
    key: str
    label: str  # The Character page: "Exclusive".
    state: str  # Where things stand: "exclusive".
    did: str  # What they did: "became exclusive".
    topic: str  # What was brought up: "being exclusive".
    after: tuple[int, int, int]  # Days at the step before, by pace (slow, true to life, fast).
    closeness: int  # The closeness stage it needs (companion/memory/closeness.py).
    asks: bool  # Brought up by the app now; later features bring up the rest.
    line: str  # The context line while it is the current step.


ROMANCE = (
    Step('dating', 'Dating', 'dating', 'started dating', 'dating', (0, 0, 0), 1, False,
         'You are dating: it is still early. You are not exclusive yet and neither of you has said "I love you".'),
    Step('exclusive', 'Exclusive', 'exclusive', 'became exclusive', 'being exclusive', (75, 35, 14), 2, True,
         'You are exclusive: you only see each other. Neither of you has said "I love you" yet.'),
    Step('love', 'Said I love you', 'in love', 'said "I love you"', 'saying "I love you"', (90, 45, 21), 3, True,
         'You are exclusive and you have both said "I love you". The user has not met your family and friends yet.'),
    Step('their_people', 'Met their people', 'met their people', 'met each other\'s people', 'meeting your people',
         (90, 45, 21), 3, True,
         'You are in love, and you have agreed it is time the user met your family and friends (if they have not '
         'met yet, it is planned). You do not have keys to each other\'s places.'),
    Step('key', 'A key to their place', 'with a key to their place', 'swapped keys', 'a key to your place',
         (120, 60, 30), 4, True,
         'You are in love and the user has a key to your place. You do not live together.'),
    Step('moving_in', 'Living together', 'living together', 'decided to live together', 'moving in together',
         (240, 120, 60), 4, True, 'You have decided to live together (whether you have moved in yet is said where it '
         'says where you are with the user). You are not engaged.'),
    Step('engaged', 'Engaged', 'engaged', 'got engaged', 'getting engaged', (365, 240, 90), 5, True,
         'You are engaged to be married.'),
    Step('married', 'Married', 'married', 'got married', 'getting married', (365, 270, 120), 5, False,
         'You are married.'),
)
FRIENDSHIP = (
    Step('friends', 'Friends', 'friends', 'became friends', 'being friends', (0, 0, 0), 1, False,
         'You are friends.'),
    Step('best_friends', 'Best friends', 'best friends', 'became best friends', 'being best friends',
         (180, 90, 45), 4, True, 'You are best friends: you have both said so.'),
    Step('trip', 'First trip together', 'best friends with a first trip planned', 'agreed on a first trip together',
         'a first trip together', (120, 60, 30), 4, True,
         'You are best friends, and you have agreed to take a first trip away together sometime. Nothing is booked '
         'yet: when it comes up, talk about where you might go.'),
    Step('wedding_party', 'Stood up at their wedding', 'best friends', 'stood up at a wedding',
         'standing up at a wedding', (365, 365, 365), 5, False, 'You are best friends who have stood up at each '
         "other's wedding."),
)
LADDERS = {'romance': ROMANCE, 'friendship': FRIENDSHIP}
CONFESSION = 'confession'
HOW = ('start', 'history', 'them', 'you', 'set', 'confession')

# How the companion brings each step up, for the first text (the model writes it; a line from the bank stands in).
REASONS = {
    'exclusive': "You want to make things official with the user: you'd like the two of you to be exclusive and only "
                 'see each other. Ask them, simply and honestly, in your own words, and leave them room to say they '
                 "aren't ready.",
    'love': "You've realised you love the user, and you are telling them for the first time. Say it in your own words, "
            "simply. Don't ask them to say it back.",
    'their_people': "You'd like the user to meet your family and friends sometime soon. Ask them in your own words; no "
                    'day or place is set yet.',
    'key': "You'd like to give the user a key to your place. Offer it in your own words.",
    'moving_in': "You'd like the two of you to live together. Ask the user in your own words, simply, and leave them "
                 "room to say they aren't ready. Don't settle whose place or who moves yet.",
    'best_friends': 'The user has become your best friend, and you want them to know. Say so in your own words.',
    'trip': "You'd love to take a first trip away with the user sometime, just the two of you. Suggest it in your own "
            'words; nothing is booked and no dates are set.',
    CONFESSION: "You've fallen for the user, your close friend, and you have decided to tell them. Say it in your own "
                'words, nervous or brave as fits you, and make it easy for them to say they only see you as a friend.',
}

# The user's answer to something the companion brought up. "Not yet" is read first: "not ready" is no no.
NOT_YET = re.compile(r"\b(?:not yet|not ready|too (?:soon|early|fast)|slow (?:down|things down)|take (?:it|things|this) "
                     r"slow|give me (?:some |a little |a bit (?:of |more )?|more )?time|need (?:some |a little |more )?time|"
                     r"maybe (?:later|someday|some day|one day|soon|down the line)|can we wait|wait a (?:bit|while|little)|"
                     r"not right now|let me think|not just yet|in a while)\b", re.IGNORECASE)
NO = re.compile(r"\b(?:no|nope|nah|i don'?t (?:think so|want|feel|see|love you)|i can'?t|not interested|just friends|(?:only |just )?see you as (?:a |just a |only a )?friend|only "
                r"(?:as )?(?:a )?friends?|don'?t feel the same|not (?:in )?that way|i'?m not (?:looking|interested|in love)|"
                r"i'?d rather (?:not|stay friends|keep (?:things|it))|rather we didn'?t|stay friends|i'?m seeing someone)\b",
                re.IGNORECASE)
YES = re.compile(r"\b(?:yes|yess+|yeah|yea|yep|yup|ya|of course|absolutely|definitely|i'?d love (?:that|to|it)|love to|"
                 r"(?:i )?love you too|i love you|me too|you(?:'re| are) mine too|let'?s do (?:it|this)|i'?m in|sure|"
                 r"totally|obviously|why not|ok(?:ay)?|deal|i want that|count me in|i do|feel the same|same here|i'?d like "
                 r"that|i'?m yours|always|really\?? yes)\b", re.IGNORECASE)

# The user bringing a step up themselves. An ask needs a question, or a plain wish ("I want", "let's").
ASKS = re.compile(r"\?|\b(?:wanna|want to|do you want|would you|will you|can we|could we|should we|let'?s|i want|i'?d "
                  r"love|i'?d like|how about|what if we)\b", re.IGNORECASE)
RAISES = {
    'exclusive': re.compile(r"\b(?:be (?:exclusive|official)|make (?:it|this|us|things) official|only (?:see|date) each "
                            r"other|be my (?:boyfriend|girlfriend|partner|significant other|sweetheart)|go steady|be "
                            r"(?:mine|together) properly|stop seeing other people)\b", re.IGNORECASE),
    'love': re.compile(r"\b(?:i love you|i'?m in love with you|i am in love with you|i'?ve fallen (?:in love )?(?:for|with) "
                       r"you|love you so much|i love u)\b", re.IGNORECASE),
    'their_people': re.compile(r"\bmeet(?:ing)? (?:your|ur) (?:family|parents|folks|mom|mum|dad|mother|father|friends|"
                               r"people|siblings|brother|sister|crew|circle)\b", re.IGNORECASE),
    'key': re.compile(r"\b(?:(?:a |the |your |my )?(?:spare )?key to (?:your|my|our) (?:place|apartment|flat|house|home|"
                      r"rooms|door)|(?:give|get|have|cut) (?:you|me) a (?:spare )?key|swap keys)\b", re.IGNORECASE),
    'moving_in': re.compile(r"\b(?:move in (?:together|with (?:me|you))|moving in (?:together|with (?:me|you))|live "
                            r"together|living together|(?:get|got|getting|find|found) (?:a|our own|an?) (?:place|flat|"
                            r"apartment|home|house) together|(?:you|we) (?:could|should) move in)\b", re.IGNORECASE),
    'engaged': re.compile(r"\b(?:(?:will|would|wanna|want to|do you want to) (?:you )?marry me|marry me|be my "
                          r"(?:husband|wife|spouse|fianc[ée]e?)|(?:get|getting) engaged|(?:get|getting) married)\b",
                          re.IGNORECASE),
    'best_friends': re.compile(r"\b(?:you'?re|you are|be) my best friend|best friends? (?:forever|now)|bff\b",
                               re.IGNORECASE),
    'trip': re.compile(r"\b(?:take|go on|plan) a trip (?:together|with me|just us)|(?:go|travel|get) away (?:together|"
                       r"somewhere together|just us)|road ?trip together|(?:a )?(?:weekend|trip) away together\b",
                       re.IGNORECASE),
}
# A statement counts for these without a question: saying it is the step.
SAID_IS_ENOUGH = {'love', 'best_friends'}
# The user telling a friend they have feelings for them.
FEELINGS = re.compile(r"\b(?:i (?:have|'?ve got|'?ve had|have had|got) (?:feelings|a crush|a thing) (?:for|on) you|i'?m "
                      r"(?:falling for|into|crushing on|in love with) you|i like you (?:as more than|more than|like that)|"
                      r"(?:go|going) out with me|be more than friends|(?:want|like) to date you|i love you)\b",
                      re.IGNORECASE)
# Words around a phrase that mean it isn't said now and meant: "if I said I love you", "she said I love you".
NOT_MEANT = re.compile(r"\b(?:if|what if|imagine|pretend|suppose|said|says|say|told|tell|telling|asked|asks|wish|"
                       r"would you ever|when (?:she|he|they))\b[^.!?]*$", re.IGNORECASE)


@cache
def bank() -> dict:
    return json.loads((catalog.DATA / 'steps.json').read_text(encoding='utf-8'))


# Settings ------------------------------------------------------------------------------------------------------------

def pace(connection) -> int:
    """The Relationship pace slider (life_settings.steps_pace): 0 only when the user brings it up, 1 slow, 2 true to
    life, 3 fast."""
    row = optional(connection, 'SELECT steps_pace FROM life_settings WHERE id=1')
    return row['steps_pace'] if row and row['steps_pace'] in range(4) else DEFAULT_PACE


def friends_fall(connection) -> bool:
    row = optional(connection, 'SELECT friends_fall FROM life_settings WHERE id=1')
    return bool(row['friends_fall']) if row else True


def just_friends(connection, companion_id: str) -> bool:
    row = optional(connection, 'SELECT just_friends FROM step_settings WHERE companion_id=?', (companion_id,))
    return bool(row and row['just_friends'])


def drama(connection) -> int:
    row = optional(connection, 'SELECT drama FROM life_settings WHERE id=1')
    return row['drama'] if row else 1


# The ladder and where a pair is on it -----------------------------------------------------------------------------

def ladder_of(definition: dict) -> str | None:
    relationship = definition.get('relationship')
    return relationship if relationship in LADDERS else None


def step_of(ladder: str, key: str) -> Step | None:
    return next((step for step in LADDERS.get(ladder, ()) if step.key == key), None)


def index_of(ladder: str, key: str) -> int:
    return next((index for index, step in enumerate(LADDERS[ladder]) if step.key == key), -1)


def local_today(companion: dict, now) -> date:
    return now.astimezone(zone(companion['version']['timezone'])).date()


def reached(connection, timeline_id: str, ladder: str, other: str = USER) -> list[dict]:
    """The steps reached on this ladder and not taken back, lowest first, one row per step."""
    rows = many(connection, 'SELECT * FROM relationship_steps WHERE timeline_id=? AND other=? AND ladder=? AND '
                'undone_at IS NULL ORDER BY reached_on, created_at', (timeline_id, other, ladder))
    found = {}
    for row in rows:
        found.setdefault(row['step'], row)
    return sorted(found.values(), key=lambda row: index_of(ladder, row['step']))


def insert_step(connection, timeline_id: str, ladder: str, key: str, day: date, how: str, timestamp: str,
                ask_id: str | None = None, other: str = USER) -> str:
    step_id = identifier()
    connection.execute('INSERT INTO relationship_steps (id, timeline_id, other, ladder, step, reached_on, how, ask_id, '
                       'created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                       (step_id, timeline_id, other, ladder, key, day.isoformat(), how, ask_id, timestamp))
    return step_id


# Where an existing pair starts ------------------------------------------------------------------------------------------

HISTORY = {
    'romance': (('married', r'\b(?:married|my (?:husband|wife|spouse)|newlyweds?|wedding anniversary)\b'),
                ('engaged', r'\b(?:engaged|fianc[ée]e?|proposed)\b'),
                ('moving_in', r'\b(?:live together|living together|moved in (?:together|with)|share (?:a|an|our) '
                              r'(?:flat|apartment|place|house|home))\b'),
                ('key', r'\b(?:key to (?:my|your|their|our) place|spare key)\b'),
                ('love', r'\b(?:in love|love each other|said i love you)\b'),
                ('exclusive', r'\b(?:boyfriend|girlfriend|partner|together for|been together|dating for|going steady|'
                              r'official)\b')),
    'friendship': (('best_friends', r'\b(?:best friends?|bff|closest friends?|like (?:siblings|family))\b'),),
}


def start(connection, companion: dict, ladder: str, now) -> list[tuple[str, str]]:
    """(step, how) to start an existing pair at, with no question asked: the steps how they know each other says
    ("married for ten years"), else the ones closeness and the days talked so far suggest."""
    from companion.life import occasions
    from companion.memory import closeness
    definition = companion['version']['definition']
    text = f"{definition.get('history_together') or ''}"
    first = LADDERS[ladder][0].key
    for key, pattern in HISTORY[ladder]:
        if re.search(pattern, text, re.IGNORECASE) and not re.search(r'\b(?:not|never|no longer|used to be|ex)\b[^.]*'
                                                                         + pattern[2:], text, re.IGNORECASE):
            return [(step.key, 'history') for step in LADDERS[ladder][:index_of(ladder, key) + 1]]
    level = closeness.state(connection, companion, now)['level']
    timezone = zone(companion['version']['timezone'])
    talked = occasions.first_talk(connection, companion['active_timeline_id'], timezone)
    days = (local_today(companion, now) - talked).days if talked else 0
    head = int(definition.get('starting_closeness') or 1)
    found = [first]
    if ladder == 'romance':
        if level >= 3:
            found.append('exclusive')
        if level >= 4 and (days >= 30 or head >= 4):
            found.append('love')
        if level >= 5 and (days >= 90 or head >= 5):
            found.append('their_people')
    elif level >= 5 and (days >= 90 or head >= 5):
        found.append('best_friends')
    return [(key, 'start') for key in found]


def ensure(connection, companion: dict, now) -> str | None:
    """The pair's ladder, starting it where the app picks when it has no steps yet."""
    ladder = ladder_of(companion['version']['definition'])
    if ladder is None or not companion.get('active_timeline_id'):
        return ladder
    timeline_id = companion['active_timeline_id']
    if reached(connection, timeline_id, ladder):
        return ladder
    from companion.life import occasions
    talked = occasions.first_talk(connection, timeline_id, zone(companion['version']['timezone']))
    day = talked or local_today(companion, now)
    for key, how in start(connection, companion, ladder, now):
        insert_step(connection, timeline_id, ladder, key, day, how, stamp(now))
    return ladder


def state(connection, companion: dict, now, write: bool = True) -> dict | None:
    """Where the pair stands: {ladder, step, next, steps (reached, with dates), since, line}. None without a ladder.
    `write` starts a pair that has no steps yet (reads from a read-only connection pass False and see the start the
    app would pick)."""
    ladder = ensure(connection, companion, now) if write else ladder_of(companion['version']['definition'])
    if ladder is None:
        return None
    rows = reached(connection, companion['active_timeline_id'], ladder)
    if not rows:
        day = local_today(companion, now)
        rows = [{'step': key, 'reached_on': day.isoformat(), 'how': how, 'id': None, 'ask_id': None}
                for key, how in start(connection, companion, ladder, now)]
    ladder_steps = LADDERS[ladder]
    top = max(index_of(ladder, row['step']) for row in rows)
    current = ladder_steps[top]
    following = ladder_steps[top + 1] if top + 1 < len(ladder_steps) else None
    since = rows[0]['reached_on']
    today = local_today(companion, now)
    return {'ladder': ladder, 'step': current.key, 'label': current.label, 'next': following.key if following else None,
            'next_label': following.label if following else None, 'since': since,
            'steps': [{'step': row['step'], 'label': step_of(ladder, row['step']).label, 'on': row['reached_on'],
                       'how': row['how']} for row in rows],
            'text': plain_text(ladder, current, rows, today),
            'ladder_steps': [{'step': step.key, 'label': step.label} for step in ladder_steps]}


def exclusive(connection, companion: dict, now) -> bool:
    """Whether the user and this companion are exclusive (or further along): from then on, on a real life or more
    drama, finding out the user is seeing someone else opens a rough patch (Vanta's decision "Exclusive minds"). Not
    once they have broken up (companion/life/breakups.py)."""
    if apart(connection, companion) == 'ended':
        return False
    found = state(connection, companion, now, write=False)
    return bool(found and found['ladder'] == 'romance' and index_of('romance', found['step']) >= 1)


def apart(connection, companion: dict) -> str | None:
    """'break' or 'ended' while the pair is apart (companion/life/breakups.py, which reads this module)."""
    from companion.life import breakups
    return breakups.apart(connection, companion)


# Plain words ------------------------------------------------------------------------------------------------------------

def span_text(days: int) -> str:
    """'3 days', '2 weeks', '8 months', 'a year', '2 years and 3 months'."""
    if days < 14:
        return f"{max(days, 1)} day{'s' if max(days, 1) != 1 else ''}"
    if days < 60:
        return f'{days // 7} weeks'
    months = round(days / 30.44)
    if months < 12:
        return f'{months} months'
    years, rest = divmod(months, 12)
    whole = 'a year' if years == 1 else f'{years} years'
    return f"{whole} and {rest} month{'s' if rest != 1 else ''}" if rest else whole


def plain_text(ladder: str, current: Step, rows: list[dict], today: date) -> str:
    """'Together 8 months, living together', 'Dating for 3 weeks', 'Friends for 2 years, best friends', 'Married'."""
    first = rows[0]
    known = first['how'] != 'history'
    span = span_text((today - date.fromisoformat(first['reached_on'])).days) if known else ''
    if ladder == 'romance':
        if current.key == 'dating':
            return f'Dating for {span}' if span else 'Dating'
        return f'Together {span}, {current.state}' if span else current.state.capitalize()
    if current.key == 'friends':
        return f'Friends for {span}' if span else 'Friends'
    return f'Friends for {span}, {current.state}' if span else current.state.capitalize()


def long_date(day: str) -> str:
    found = date.fromisoformat(day)
    return f'{found.day} {found:%B %Y}'


def context_line(found: dict) -> str:
    """Where things stand, for the chat context: the step, how long, and what has not happened yet."""
    step = step_of(found['ladder'], found['step'])
    whose = 'Together' if found['ladder'] == 'romance' else 'Friends'
    dated = [item for item in found['steps'] if item['how'] != 'history']
    since = f" {whose} since {long_date(found['since'])}." if dated and dated[0]['step'] == found['steps'][0]['step'] else ''
    latest = found['steps'][-1]
    if len(found['steps']) > 1 and latest['how'] not in ('history', 'start'):
        since += f" You {step.did} on {long_date(latest['on'])}."
    return (f'- {step.line}{since} Keep to where things stand: do not act further along than this, and do not bring up '
            'a next step yourself unless a line here says you do.')


# The companion brings up the next step ----------------------------------------------------------------------------------

def facts(connection, companion: dict, found: dict, step: Step, now) -> dict:
    """What the engine reads: the pace, how close they are against what the step needs, days short of its time, their
    description, their personality sliders and their mood lately."""
    from companion.memory import closeness, pairs
    from companion.world import personality
    definition = companion['version']['definition']
    level = closeness.state(connection, companion, now)['level']
    today = local_today(companion, now)
    current = next(item for item in found['steps'] if item['step'] == found['step'])
    held = (today - date.fromisoformat(current['on'])).days
    wanted = step.after[max(pace(connection), 1) - 1]
    levels = personality.levels_of(definition.get('personality_sliders') or {})
    return {'pace': pace(connection), 'closeness': level, 'closeness_over': level - step.closeness,
            'short_days': max(wanted - held, 0), 'days': held, 'drama': drama(connection),
            'social': levels.get('social', 1), 'warmth': levels.get('warmth', 1),
            'mood': consequences.total(connection, companion['active_timeline_id'],
                                       pairs.companion_key(companion['id']), 'mood', today.isoformat()),
            'sheet': {group for group in consequences.WORDS if consequences.sheet_has(definition, group)}}


def names(companion: dict, topic: str) -> dict:
    """Names for the odds labels the user reads: "meeting your people" (the companion's words) is "their people"."""
    return {'name': companion['version']['definition']['name'].split()[0],
            'step': re.sub(r'\byour\b', 'their', topic), 'a': 'someone', 'b': ''}


def decide(connection, companion: dict, choice: str, subject: str, found_facts: dict, topic: str, now) -> dict:
    labels = names(companion, topic)
    table = consequences.tables()[choice]
    return consequences.decide(connection, timeline_id=companion['active_timeline_id'], choice=choice, subject=subject,
                               facts=found_facts, names=labels,
                               labels=[option['label'].format(**labels) for option in table['options']],
                               day=local_today(companion, now).isoformat(), timestamp=stamp(now))


def asks(connection, timeline_id: str, statuses: tuple[str, ...], other: str = USER) -> list[dict]:
    marks = ','.join('?' * len(statuses))
    return many(connection, f'SELECT * FROM step_asks WHERE timeline_id=? AND other=? AND status IN ({marks}) '
                'ORDER BY created_at', (timeline_id, other, *statuses))


def waiting(connection, timeline_id: str, step: str, today: date) -> bool:
    """Whether the last answer about this step still holds: a no for half a year, not yet for some weeks."""
    last = optional(connection, "SELECT status, settled_at FROM step_asks WHERE timeline_id=? AND other=? AND step=? "
                    "AND status IN ('no', 'not_yet', 'lapsed') ORDER BY settled_at DESC LIMIT 1",
                    (timeline_id, USER, step))
    if not last or not last['settled_at']:
        return False
    days = NO_HOLD if last['status'] == 'no' else WAIT_AFTER[max(pace(connection), 1) - 1]
    return (today - parse(last['settled_at']).date()).days < days


def advance(connection, companion: dict, now) -> None:
    """Once a day: start a pair with no steps, let a stale ask lapse, plan when the next step comes up, and now and then
    let a close friend fall for the user. Cheap: no model."""
    if not ACTIVE or not companion.get('active_timeline_id'):
        return
    found = state(connection, companion, now)
    if found is None:
        return
    lapse(connection, companion, now)
    falls(connection, companion, found, now)
    plan_next(connection, companion, found, now)


def lapse(connection, companion: dict, now) -> None:
    """An ask left unanswered for a few days lapses (not yet); a planned one the pair has moved past is dropped."""
    found = state(connection, companion, now, write=False)
    for row in asks(connection, companion['active_timeline_id'], ('open', 'planned')):
        if row['status'] == 'open' and now - parse(row['created_at']) >= timedelta(days=OPEN_DAYS):
            connection.execute("UPDATE step_asks SET status='lapsed', settled_at=? WHERE id=?", (stamp(now), row['id']))
        elif row['status'] == 'planned' and not still_next(found, row):
            connection.execute("UPDATE step_asks SET status='dropped', settled_at=? WHERE id=?", (stamp(now), row['id']))


def plan_next(connection, companion: dict, found: dict, now) -> dict | None:
    """Once the next step's time has come and they are close enough, the engine decides how soon they bring it up."""
    timeline_id = companion['active_timeline_id']
    step = step_of(found['ladder'], found['next']) if found['next'] else None
    if not step or not step.asks or not pace(connection) or asks(connection, timeline_id, ('planned', 'open')):
        return None
    if apart(connection, companion):
        return None  # Not while on a break or broken up (companion/life/breakups.py).
    today = local_today(companion, now)
    found_facts = facts(connection, companion, found, step, now)
    if found_facts['short_days'] or found_facts['closeness_over'] < 0 or waiting(connection, timeline_id, step.key, today):
        return None
    if found['ladder'] == 'friendship' and found['step'] == 'friends' and step.key != 'best_friends':
        return None
    turn = 1 + len(many(connection, 'SELECT id FROM step_asks WHERE timeline_id=? AND other=? AND step=? AND side=?',
                        (timeline_id, USER, step.key, 'them')))
    outcome = decide(connection, companion, 'steps:when', f'steps:{timeline_id}:{USER}:{step.key}:{turn}',
                     found_facts, step.topic, now)
    low, high = WHEN[outcome['picked']]
    offset = random.Random(f"{timeline_id}:{step.key}:{turn}:when").randint(low, high)
    return insert_ask(connection, timeline_id, found['ladder'], step.key, 'them', 'planned', stamp(now),
                      due_on=today + timedelta(days=offset), consequence_id=outcome['id'], turn=turn)


def insert_ask(connection, timeline_id: str, ladder: str, step: str, side: str, status: str, timestamp: str,
               due_on: date | None = None, message_id: str | None = None, consequence_id: str | None = None,
               turn: int = 1) -> dict:
    ask_id = identifier()
    connection.execute('INSERT INTO step_asks (id, timeline_id, other, ladder, step, side, status, due_on, message_id, '
                       'consequence_id, round, created_at, settled_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                       (ask_id, timeline_id, USER, ladder, step, side, status, due_on.isoformat() if due_on else None,
                        message_id, consequence_id, turn, timestamp,
                        timestamp if status in ('yes', 'not_yet', 'no') else None))
    return optional(connection, 'SELECT * FROM step_asks WHERE id=?', (ask_id,))


def falls(connection, companion: dict, found: dict, now) -> dict | None:
    """Once a month the engine decides whether a close friend falls for the user."""
    if found['ladder'] != 'friendship' or not may_fall(connection, companion, now):
        return None
    timeline_id = companion['active_timeline_id']
    today = local_today(companion, now)
    # A month is a 30-day window starting on a day seeded by the timeline, so a month the app is opened at all counts.
    window = (today.toordinal() + random.Random(f'falls-day:{timeline_id}').randrange(30)) // 30
    subject = f'steps:{timeline_id}:{USER}:falls:{window}'
    if consequences.recorded(connection, subject, 'steps:falls'):
        return None
    if asks(connection, timeline_id, ('open',)) or any(row['step'] == CONFESSION for row in asks(
            connection, timeline_id, ('planned',))):
        return None
    last = optional(connection, 'SELECT created_at FROM step_asks WHERE timeline_id=? AND step=? ORDER BY created_at '
                    'DESC LIMIT 1', (timeline_id, CONFESSION))
    if last and (today - parse(last['created_at']).date()).days < FALL_HOLD:
        return None
    from companion.memory import closeness
    level = closeness.state(connection, companion, now)['level']
    known = (today - date.fromisoformat(found['since'])).days
    if level < FALL_CLOSENESS or known < FALL_AFTER:
        return None
    outcome = decide(connection, companion, 'steps:falls', subject,
                     {'drama': drama(connection), 'closeness': level, 'months': known // 30}, 'falling for you', now)
    if outcome['picked'] != 1:
        return None
    offset = random.Random(f'{subject}:confess').randint(2, 12)
    for row in asks(connection, timeline_id, ('planned',)):  # A smaller step can wait.
        connection.execute("UPDATE step_asks SET status='dropped', settled_at=? WHERE id=?", (stamp(now), row['id']))
    return insert_ask(connection, timeline_id, 'friendship', CONFESSION, 'them', 'planned', stamp(now),
                      due_on=today + timedelta(days=offset), consequence_id=outcome['id'])


def may_fall(connection, companion: dict, now) -> bool:
    """A friend may fall for the user: the switch is on, the lock is off, they are an adult who could be drawn to the
    user (their adult side's orientation and the persona's gender, when both are known)."""
    from companion.world import intimacy
    definition = companion['version']['definition']
    if not friends_fall(connection) or just_friends(connection, companion['id']) or intimacy.reads_as_minor(definition):
        return False
    return drawn_to_user(connection, companion)


def drawn_to_user(connection, companion: dict) -> bool:
    from companion.world import intimacy, looks
    found = intimacy.for_companion(connection, companion['id'], companion['version']['definition']) or {}
    orientation = found.get('orientation') or ''
    persona = optional(connection, 'SELECT gender FROM persona LIMIT 1')
    theirs = {'she/her': 'woman', 'he/him': 'man'}.get(looks.pronouns_of(companion['version']['definition']))
    yours = (persona or {}).get('gender') or ''
    if orientation in ('', 'bisexual', 'pansexual', 'queer', 'asexual') or yours not in ('woman', 'man') or not theirs:
        return True
    same = yours == theirs
    return same if orientation in ('gay', 'lesbian') else not same


# First texts (companion/life/openers.py) ------------------------------------------------------------------------------

SETTLES = ('next_step',)


def ask_due(connection, companion: dict, now) -> list:
    """A step they planned to bring up, once its day has come and they are not low (they wait out a bad spell)."""
    from companion.life.openers import Trigger
    from companion.memory import pairs
    if not ACTIVE or not FIRST_TEXTS or not companion.get('active_timeline_id'):
        return []
    timeline_id = companion['active_timeline_id']
    today = local_today(companion, now)
    found = state(connection, companion, now, write=False)
    result = []
    for row in asks(connection, timeline_id, ('planned',)):
        if row['step'] == 'engaged':
            continue  # They propose in person, on an evening out (companion/life/wedding.py).
        if not row['due_on'] or row['due_on'] > today.isoformat():
            continue
        if not still_next(found, row):
            continue  # Moved on meanwhile; the daily check drops it (`lapse`).
        if consequences.total(connection, timeline_id, pairs.companion_key(companion['id']), 'mood', today.isoformat()) < 0:
            continue
        lines = bank()[row['step']]
        template = random.Random(f"{row['id']}:line").choice(lines)
        result.append(Trigger(f"step-ask:{row['id']}", 'next_step', REASONS[row['step']], template, (row['id'],)))
    return result


def still_next(found: dict | None, row: dict) -> bool:
    if found is None:
        return False
    if row['step'] == CONFESSION:
        return found['ladder'] == 'friendship'
    return found['ladder'] == row['ladder'] and found['next'] == row['step']


def settle(connection, companion: dict, message: dict, trigger, timestamp: str) -> None:
    """The first text that brought the step up went out: the ask is open for the user's answer."""
    connection.execute("UPDATE step_asks SET status='open', message_id=?, created_at=? WHERE id=? AND status='planned'",
                       (message['id'], timestamp, trigger.sources[0]))


# Reading the chat ----------------------------------------------------------------------------------------------------------

def plain(text: str) -> str:
    return own_plans.QUOTED.sub(' ', own_plans.ACTIONS.sub(' ', text)).replace('’', "'")


def answer(text: str) -> str | None:
    """'yes', 'not_yet' or 'no' when a message plainly answers something brought up, else None."""
    text = plain(text)
    if NOT_YET.search(text):
        return 'not_yet'
    if NO.search(text):
        return 'no'
    return 'yes' if YES.search(text) else None


def meant(sentence: str, found: re.Match) -> bool:
    return not NOT_MEANT.search(sentence[:found.start()]) and not own_plans.PAST.search(sentence[:found.start()])


def raised(text: str, keys: list[str]) -> str | None:
    """The step among `keys` a user message brings up, else None."""
    for sentence in re.split(r'(?<=[.!?])\s+|\n+', plain(text)):
        for key in keys:
            found = RAISES[key].search(sentence)
            if found and meant(sentence, found) and (key in SAID_IS_ENOUGH or ASKS.search(sentence)) and not \
                    re.search(r"\b(?:don'?t|do not|never|not)\b[^.!?]*$", sentence[:found.start()], re.IGNORECASE):
                return key
    return None


def confessed(text: str) -> bool:
    for sentence in re.split(r'(?<=[.!?])\s+|\n+', plain(text)):
        found = FEELINGS.search(sentence)
        if found and meant(sentence, found) and not re.search(r"\b(?:don'?t|do not|never|not)\b[^.!?]*$",
                                                              sentence[:found.start()], re.IGNORECASE):
            return True
    return False


def note(connection, message: dict, companion: dict, timestamp: str) -> bool:
    """A user message that answers a step they brought up, or brings one up itself: settled before the reply is
    written, so the reply says it. True when it was one of those."""
    if not ACTIVE or message['role'] != 'user' or not companion.get('active_timeline_id'):
        return False
    now = parse(message['created_at'])
    timeline_id = companion['active_timeline_id']
    if optional(connection, 'SELECT id FROM step_asks WHERE message_id=? OR answer_id=?', (message['id'], message['id'])):
        return True
    found = state(connection, companion, now)
    if found is None or apart(connection, companion):
        return False  # On a break or broken up, asking to try again is read by companion/life/breakups.py.
    open_ask = next(iter(asks(connection, timeline_id, ('open',))), None)
    if open_ask and (said := answer(message['text'])):
        settle_answer(connection, companion, open_ask, said, message, now)
        return True
    if found['ladder'] == 'friendship':
        if confessed(message['text']) and may_fall(connection, companion, now):
            return friend_answers(connection, companion, found, message, now)
    keys = upcoming(found)
    key = raised(message['text'], keys) if keys else None
    if key is None:
        return False
    return answers(connection, companion, found, key, message, now)


def upcoming(found: dict) -> list[str]:
    """The steps the user can bring up: the next two the app handles now (saying "I love you" while only dating is
    being exclusive and in love at once)."""
    ladder = LADDERS[found['ladder']]
    top = index_of(found['ladder'], found['step'])
    return [step.key for step in ladder[top + 1:top + 3] if step.asks]


def settle_answer(connection, companion: dict, row: dict, said: str, message: dict, now) -> None:
    timestamp = stamp(now)
    connection.execute('UPDATE step_asks SET status=?, answer_id=?, settled_at=? WHERE id=?',
                       (said, message['id'], timestamp, row['id']))
    day = local_today(companion, now)
    if said != 'yes':
        if row['step'] == CONFESSION:
            awkward(connection, companion, row, now)
        elif row['step'] == 'engaged':
            from companion.life import wedding
            wedding.answered(connection, companion, row, said, now)
        return
    if row['step'] == CONFESSION:
        become_romance(connection, companion, row['id'], day, timestamp)
        return
    insert_step(connection, companion['active_timeline_id'], row['ladder'], row['step'], day, 'them', timestamp,
                row['id'])
    if row['step'] == 'engaged':
        from companion.life import wedding
        wedding.answered(connection, companion, row, said, now)


def answers(connection, companion: dict, found: dict, key: str, message: dict, now) -> bool:
    """The user brought a step up: the engine decides the companion's answer, and yes takes them there."""
    timeline_id, timestamp = companion['active_timeline_id'], stamp(now)
    step = step_of(found['ladder'], key)
    for row in asks(connection, timeline_id, ('planned',)):
        connection.execute("UPDATE step_asks SET status='dropped', settled_at=? WHERE id=?", (timestamp, row['id']))
    found_facts = facts(connection, companion, found, step, now)
    skipped = [item for item in upcoming(found) if index_of(found['ladder'], item) < index_of(found['ladder'], key)]
    found_facts['skips'] = len(skipped)
    outcome = decide(connection, companion, 'steps:answer', f"steps:{timeline_id}:{USER}:{key}:you:{message['id']}",
                     found_facts, step.topic, now)
    status = 'yes' if outcome['picked'] == 0 else 'not_yet'
    row = insert_ask(connection, timeline_id, found['ladder'], key, 'you', status, timestamp, message_id=message['id'],
                     consequence_id=outcome['id'])
    if status == 'yes':
        day = local_today(companion, now)
        for item in [*skipped, key]:
            insert_step(connection, timeline_id, found['ladder'], item, day, 'you', timestamp, row['id'])
        if key == 'engaged':
            from companion.life import wedding
            wedding.answered(connection, companion, row, status, now)
    return True


def friend_answers(connection, companion: dict, found: dict, message: dict, now) -> bool:
    """The user told a friend how they feel: the engine decides whether the friend feels the same."""
    from companion.memory import closeness
    timeline_id, timestamp = companion['active_timeline_id'], stamp(now)
    level = closeness.state(connection, companion, now)['level']
    outcome = decide(connection, companion, 'steps:friend_answer', f"steps:{timeline_id}:{USER}:feelings:{message['id']}",
                     {'drama': drama(connection), 'closeness': level}, 'how you feel', now)
    status = 'yes' if outcome['picked'] == 0 else 'no'
    row = insert_ask(connection, timeline_id, 'friendship', CONFESSION, 'you', status, timestamp,
                     message_id=message['id'], consequence_id=outcome['id'])
    if status == 'yes':
        become_romance(connection, companion, row['id'], local_today(companion, now), timestamp)
    return True


def become_romance(connection, companion: dict, ask_id: str, day: date, timestamp: str) -> None:
    """A friendship that turned: a new character version with the relationship set to romance (the saved one, without
    life chapters on top), and dating from today."""
    from companion.characters import insert_version
    from companion.database import decode, one
    from companion.models import CharacterDefinition
    row = one(connection, 'SELECT definition, number FROM character_versions WHERE id=?', (companion['active_version_id'],))
    saved = CharacterDefinition.model_validate({**decode(row['definition']), 'relationship': 'romance'})
    version_id = insert_version(connection, companion['id'], row['number'] + 1, saved,
                                'Friends who fell for each other', timestamp)
    connection.execute('UPDATE companions SET active_version_id=? WHERE id=?', (version_id, companion['id']))
    insert_step(connection, companion['active_timeline_id'], 'romance', 'dating', day, 'confession', timestamp, ask_id)


def awkward(connection, companion: dict, row: dict, now) -> None:
    """They told the user how they feel and the user would rather stay friends: things are awkward for a few days."""
    from companion.memory import pairs
    if row['side'] != 'them':
        return
    day = local_today(companion, now)
    consequences.add_mark(connection, {
        'timeline_id': companion['active_timeline_id'], 'consequence_id': row['consequence_id'] or row['id'],
        'holder': pairs.companion_key(companion['id']), 'kind': 'mood', 'amount': -1, 'about': None,
        'note': f"{companion['version']['definition']['name'].split()[0]} feels awkward after saying how they feel",
        'told': "Things have felt a little awkward since you told the user how you feel and they said they'd rather "
                "stay friends. You're getting past it and you still want the friendship.",
        'starts_on': day.isoformat(), 'ends_on': (day + timedelta(days=AWKWARD_DAYS)).isoformat()}, stamp(now))


# What the chat context says -----------------------------------------------------------------------------------------------

ANSWERED = {
    'yes': 'The user just said yes to {topic}. It is new and it matters to you: react in your own words.',
    'not_yet': "The user just said they aren't ready for {topic} yet. Take it gracefully, with no pressure; you can "
               'come back to it another time.',
    'no': 'The user just said no to {topic}. It stings a little, but you respect it, and things stay as they are.',
    'lapsed': '',
}
YOUR_ANSWER = {
    'yes': 'The user just brought up {topic}. Your answer is yes: say so in your own words and mean it.',
    'not_yet': "The user just brought up {topic}. You aren't ready for that yet ({why}): say so kindly in your own "
               'words, without closing the door.',
}
CONFESSED = {
    'yes': 'You told the user you have feelings for them, and they just said they feel the same. You are dating now: '
           'it is new, and you are happy.',
    'no': "You told the user you have feelings for them, and they just said they'd rather stay friends. It stings, but "
          'you take it gracefully and keep the friendship.',
}
TOLD = {
    'yes': 'The user just told you they have feelings for you, and you feel the same: say so in your own words. You '
           'are dating now.',
    'no': "The user just told you they have feelings for you. You don't feel that way about them: say so kindly and "
          'honestly in your own words, and that you want to keep the friendship.',
}
WAITING = ('Earlier you brought up {topic} with the user and they have not answered yet. If they answer now, take it '
           'as they mean it; do not ask again.')


def fresh_lines(connection, companion: dict, now, turn: set[str]) -> list[tuple[str, str]]:
    """Lines for the turn being answered: an answer just given, or a step the user just brought up."""
    if not turn:
        return []
    marks = ','.join('?' * len(turn))
    rows = many(connection, f'SELECT * FROM step_asks WHERE timeline_id=? AND (answer_id IN ({marks}) OR (side=? AND '
                f'message_id IN ({marks})))', (companion['active_timeline_id'], *turn, 'you', *turn))
    result = []
    for row in rows:
        topic = topic_of(row)
        if row['step'] == CONFESSION:
            text = (CONFESSED if row['side'] == 'them' else TOLD).get(row['status'], '')
        elif row['side'] == 'them':
            text = ANSWERED.get(row['status'], '').format(topic=topic)
        else:
            text = YOUR_ANSWER.get(row['status'], '').format(topic=topic, why=reason(connection, row))
        if text:
            result.append((f"step-ask:{row['id']}:{row['status']}", f'- {text}'))
    return result


def topic_of(row: dict) -> str:
    step = step_of(row['ladder'], row['step'])
    return step.topic if step else 'how you feel'


def reason(connection, row: dict) -> str:
    """Why they aren't ready, from the strongest reason the engine had against yes."""
    from companion.database import decode
    found = optional(connection, 'SELECT options FROM consequences WHERE id=?', (row['consequence_id'] or '',))
    reasons = decode(found['options'])[0]['reasons'] if found else []
    against = [text for text in reasons if any(word in text for word in ('sooner', 'close enough', 'slow', 'low lately',
                                                                         'skips'))]
    return 'it feels too soon' if not against else REASON_WORDS.get(next(
        (key for key in REASON_WORDS if key in against[0]), ''), 'it feels too soon')


REASON_WORDS = {'sooner': 'it feels too soon', 'close enough': "you don't feel close enough yet",
                'slow': 'you like to take things slowly', 'low lately': "you've been low lately",
                'skips': "it's a big jump from where you are"}


def context_lines(connection, companion: dict, now, turn: set[str]) -> list[tuple[str, str]]:
    """(identity, line) for the 'steps' section: where things stand, something they brought up that waits for an
    answer, and an answer just given."""
    found = state(connection, companion, now, write=False)
    if found is None or apart(connection, companion) == 'ended':
        return []  # Exes: the 'breakup' section says where they stand (companion/life/breakups.py).
    result = [(f"steps:{found['ladder']}:{found['step']}", context_line(found))]
    for row in asks(connection, companion['active_timeline_id'], ('open',)):
        if row['message_id'] and row['answer_id'] is None:
            result.append((f"step-ask:{row['id']}:open", '- ' + WAITING.format(
                topic='how you feel about them' if row['step'] == CONFESSION else topic_of(row))))
    return result + fresh_lines(connection, companion, now, turn)


def offer(packet, connection, companion: dict, now, recent: list[dict], group=None) -> None:
    """Adds the 'steps' section. In a group chat only where things stand."""
    turn = set()
    if group is None:
        for message in reversed(recent):
            if message['role'] != 'user':
                break
            turn.add(message['id'])
    for identity, text in context_lines(connection, companion, now, turn):
        packet.offer('steps', identity, text)


# Anniversaries and the scrapbook ---------------------------------------------------------------------------------------------

def anniversaries(connection, companion: dict, day: date, ahead: int) -> list[dict]:
    """Steps whose anniversary falls within `ahead` days: {step, did, on (the day reached), date, years}. A step the
    app started them at from how they know each other has no real date, so no anniversary."""
    from companion.life import occasions
    found = state(connection, companion, now_for(day, companion), write=False)
    if found is None or apart(connection, companion) == 'ended':
        return []
    result = []
    for item in found['steps']:
        if item['how'] in ('history', 'start'):
            continue
        reached_on = date.fromisoformat(item['on'])
        for offset in range(ahead + 1):
            when = day + timedelta(days=offset)
            years = when.year - reached_on.year
            if years >= 1 and occasions.on(when, reached_on.strftime('%m-%d')):
                result.append({'step': item['step'], 'did': step_of(found['ladder'], item['step']).did,
                               'on': item['on'], 'date': when, 'days': offset, 'years': years})
    return result


def now_for(day: date, companion: dict):
    from datetime import datetime, time
    return datetime.combine(day, time(12), zone(companion['version']['timezone']))


def scrapbook_items(connection, companion: dict, low: str, high: str) -> list[dict]:
    """The steps reached in a stretch of time, for the scrapbook's "How you got closer" page."""
    result = []
    for ladder in LADDERS:
        for row in reached(connection, companion['active_timeline_id'], ladder):
            if row['how'] in ('history', 'start') or not low <= row['reached_on'] <= high:
                continue
            step = step_of(ladder, row['step'])
            result.append({'date': row['reached_on'], 'text': f'You {step.did}'})
    return result


# The Character page -----------------------------------------------------------------------------------------------------------

def view(connection, companion: dict, now, show_odds: bool) -> dict:
    """Where the user and this companion stand, the ladder, what was brought up lately, and the lock."""
    found = state(connection, companion, now, write=False)
    lock = just_friends(connection, companion['id'])
    if found is None:
        return {'ladder': None, 'just_friends': lock}
    planned = None
    if show_odds:
        row = next(iter(asks(connection, companion['active_timeline_id'], ('planned',))), None)
        planned = {'step': row['step'], 'due_on': row['due_on'], 'consequence_id': row['consequence_id'],
                   'topic': topic_of(row)} if row else None
    recent = many(connection, "SELECT * FROM step_asks WHERE timeline_id=? AND status NOT IN ('planned', 'dropped') "
                  'ORDER BY created_at DESC LIMIT 6', (companion['active_timeline_id'],))
    from companion.life import moving_in
    return {**found, 'just_friends': lock, 'can_fall': found['ladder'] == 'friendship', 'planned': planned,
            'moving_in': moving_in.view(connection, companion, now, show_odds),
            'asks': [{'id': row['id'], 'step': row['step'], 'side': row['side'], 'status': row['status'],
                      'topic': 'how you feel' if row['step'] == CONFESSION else topic_of(row),
                      'on': parse(row['created_at']).astimezone(zone(companion['version']['timezone'])).date().isoformat(),
                      'consequence_id': row['consequence_id'] if show_odds else None} for row in recent]}


def set_step(connection, companion: dict, key: str, now) -> None:
    """The user sets where things stand: a step further along is reached today (and any between), one further back
    takes the steps after it back. Open and planned asks give way."""
    ladder = ensure(connection, companion, now)
    require(ladder is not None, 'Only a romance or a friendship has steps.', 422)
    require(step_of(ladder, key) is not None, 'Pick one of the steps.', 422)
    timeline_id, timestamp = companion['active_timeline_id'], stamp(now)
    rows = reached(connection, timeline_id, ladder)
    have = {row['step'] for row in rows}
    wanted = index_of(ladder, key)
    for row in rows:
        if index_of(ladder, row['step']) > wanted:
            connection.execute('UPDATE relationship_steps SET undone_at=? WHERE id=?', (timestamp, row['id']))
    day = local_today(companion, now)
    for step in LADDERS[ladder][:wanted + 1]:
        if step.key not in have:
            insert_step(connection, timeline_id, ladder, step.key, day, 'set', timestamp)
    for row in asks(connection, timeline_id, ('planned', 'open')):
        connection.execute("UPDATE step_asks SET status='dropped', settled_at=? WHERE id=?", (timestamp, row['id']))


def copy_open(connection, parent_id: str, new_id: str, cutoff: str, ids: dict) -> dict[str, str]:
    """A branch (companion/timelines.py) keeps what was brought up and not yet answered at its fork: still open there,
    so the answer on the branch counts. The copies' ids by original id."""
    copied = {}
    for row in many(connection, "SELECT * FROM step_asks WHERE timeline_id=? AND status NOT IN ('planned', 'dropped') "
                    'AND created_at<? AND (settled_at IS NULL OR settled_at>=?)', (parent_id, cutoff, cutoff)):
        copied[row['id']] = identifier()
        connection.execute('INSERT INTO step_asks (id, timeline_id, other, ladder, step, side, status, due_on, message_id, '
                           "consequence_id, round, created_at) VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?, NULL, ?, ?)",
                           (copied[row['id']], new_id, row['other'], row['ladder'], row['step'], row['side'],
                            row['due_on'], ids.get(row['message_id']), row['round'], row['created_at']))
    return copied


def set_lock(connection, companion: dict, locked: bool, timestamp: str) -> None:
    connection.execute('INSERT INTO step_settings (companion_id, just_friends, updated_at) VALUES (?, ?, ?) '
                       'ON CONFLICT(companion_id) DO UPDATE SET just_friends=excluded.just_friends, '
                       'updated_at=excluded.updated_at', (companion['id'], int(locked), timestamp))
    if locked:
        for row in asks(connection, companion['active_timeline_id'], ('planned',)):
            if row['step'] == CONFESSION:
                connection.execute("UPDATE step_asks SET status='dropped', settled_at=? WHERE id=?", (timestamp, row['id']))


def change(connection, companion: dict, consequence_id: str, option: int, now) -> dict:
    """The user makes a decision go another way (Hidden values, "Why it went this way"): how soon they bring a step up
    moves its day; their answer to a step the user raised moves the step with it; a friend falling for the user plans
    the confession, or calls it off while it hasn't been said."""
    outcome = consequences.change(connection, consequence_id, option, stamp(now))
    require(outcome['timeline_id'] == companion['active_timeline_id'], 'That outcome is not on this timeline.', 404)
    row = optional(connection, 'SELECT * FROM step_asks WHERE consequence_id=?', (consequence_id,))
    timestamp, today = stamp(now), local_today(companion, now)
    if outcome['choice'] == 'steps:when' and row and row['status'] == 'planned':
        low, high = WHEN[option]
        offset = random.Random(f"{row['timeline_id']}:{row['step']}:{row['round']}:when").randint(low, high)
        connection.execute('UPDATE step_asks SET due_on=? WHERE id=?',
                           ((parse(row['created_at']).date() + timedelta(days=offset)).isoformat(), row['id']))
    elif outcome['choice'] == 'steps:answer' and row:
        status = 'yes' if option == 0 else 'not_yet'
        connection.execute('UPDATE step_asks SET status=? WHERE id=?', (status, row['id']))
        connection.execute('UPDATE relationship_steps SET undone_at=? WHERE ask_id=? AND undone_at IS NULL',
                           (timestamp, row['id']))
        if status == 'yes':
            insert_step(connection, row['timeline_id'], row['ladder'], row['step'], today, 'you', timestamp, row['id'])
    elif outcome['choice'] == 'steps:falls':
        if option == 1 and not row:
            insert_ask(connection, companion['active_timeline_id'], 'friendship', CONFESSION, 'them', 'planned',
                       timestamp, due_on=today + timedelta(days=1), consequence_id=consequence_id)
        elif option == 0 and row and row['status'] == 'planned':
            connection.execute("UPDATE step_asks SET status='dropped', settled_at=? WHERE id=?", (timestamp, row['id']))
    return consequences.by_id(connection, consequence_id)

