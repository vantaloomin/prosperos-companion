"""Breaks and breakups (Hit List #64, v0.13 Life Together): when rough patches pile up, a relationship can come apart.

Only on a real life and with drama (the Breakups switch, life_settings.breakups: on there, off on an easy life). It
grows out of rough patches (companion/life/rough_patches.py), one warning at a time, each a roll in the consequence
engine with the odds under Hidden values ("Why it went this way" on Today) where the user can make it go another way:

- a rough patch of the user's making that drags on (or the third in a few weeks) can leave things strained
  (`user:strained`): "Things are strained" on the Character page and the chat strip;
- strained a few days with a patch still open, they start thinking about a break (`user:thinking`): "They're thinking
  about a break";
- thinking about it a few days more with a patch still open, they ask for one (`user:break`), in a first text;
- the break lasts two or three weeks; at its end they decide (`user:after_break`): try again or end it.

A friendship has no break: strained can turn into a falling out (`user:falling_out`). You can talk them round at
every step: making up (the rough patch mended) and a few calm days ease a warning; during a break, sorry or a kind
gesture counts for a lot, and asking to try again is answered at once (`user:talk_round`). Either side can end it: the
user from the chat with fixed phrases ("I'm breaking up with you", "can we take a break from us"), the companion after
a break.

Afterwards they are exes: nothing is deleted (the steps stay in the scrapbook), they keep their own life in town and
are free to date, the one who moved in moves out (companion/life/moving_in.py), and texting drops off by rules (only a
birthday, or reaching out). Getting back together is possible: now and then an ex reaches out (`user:reach_out`), or
the user asks (`user:back_together`). Back together, they start again from a key to each other's place: living
together, an engagement or a marriage are taken back (the scrapbook keeps them).

No model decides anything; the model only puts it in words.
"""
import json
import random
import re
from datetime import date, datetime, timedelta
from functools import cache

from companion import consequences
from companion.clock import parse, stamp, zone
from companion.database import decode, encode, identifier, many, one, optional, settings
from companion.errors import require
from companion.life import rough_patches, steps
from companion.world import catalog

ACTIVE = True
# A break asked for, an ending, an ex reaching out, as first texts; off in most tests (tests/conftest.py).
FIRST_TEXTS = True
LADDERS = ('romance', 'friendship')
YES = 1  # In every app-rolled choice here, option 1 is the one that moves things on.
TOGETHER, ENDS = 0, 1  # user:after_break

# Days a big rough patch of the user's making is open before it can leave things strained; or the number of big ones
# in the last weeks that does it at once.
STRAIN_AFTER = 2
PILED_UP = 3
LATELY = timedelta(days=45)
# Days at a warning, with a rough patch still open, before the next roll; and calm days (no open rough patch) that
# ease a warning, by the Rough patches slider (2 true to life, 3 dramatic).
NEXT_AFTER = {2: 4, 3: 3}
EASE_AFTER = {2: 5, 3: 10}
BREAK_DAYS = {2: 14, 3: 21}
# Exes: no reaching out for this long after it ended; then a seeded check about once a month.
REACH_AFTER = 45
REACH_OPEN = 3
# How long the chat context keeps something just said or decided.
FRESH = timedelta(hours=12)
# How long the chat strip still says it ended.
STRIP_ENDED = timedelta(days=7)

# The user, from the chat. Each needs to be about the two of them, so "I need a break from work" stays a sentence.
BREAK_UP = re.compile(r"\b(?:i'?m breaking up with you|i(?:'m| am)? (?:want|going) to break up|(?:i think )?we should "
                      r"(?:break up|split up|end (?:this|things|it|us))|let'?s (?:break up|split up|end (?:this|things|it|"
                      r"us))|i(?: want| need)? to end (?:this|things|us|our relationship|it between us)|i'?m ending "
                      r"(?:this|things|us|our relationship)|it'?s over between us|we'?re over|this is over between us|i'?m "
                      r"done with (?:us|this relationship|our relationship))\b", re.IGNORECASE)
FRIENDS_END = re.compile(r"\b(?:i don'?t want to be (?:your )?friends? (?:any ?more|anymore)|we'?re not friends "
                         r"(?:any ?more|anymore)|i'?m done with (?:you|this friendship|our friendship)|(?:i want to |let'?s )"
                         r"end (?:this|our) friendship|i'?m ending (?:this|our) friendship)\b", re.IGNORECASE)
TAKE_BREAK = re.compile(r"\b(?:(?:take|need|want) (?:a|some) (?:break|time apart|space) from (?:us|this relationship|our "
                        r"relationship|each other|this|you)|(?:we should|let'?s|can we|could we|maybe we should) (?:take|go "
                        r"on) a break|(?:be|go) on a break|take a break from (?:us|each other))\b", re.IGNORECASE)
COME_BACK = re.compile(r"\b(?:get back together|try again|give (?:us|this|it|me) (?:another|a second) (?:chance|go|shot|"
                       r"try)|i want you back|(?:can|could) we (?:fix|work on|work through|make up)|start (?:over|again) "
                       r"(?:together|with you)|be friends again|be together again|come back to me|i miss us)\b",
                       re.IGNORECASE)
NOT_NOW = re.compile(r"\b(?:if|what if|imagine|pretend|suppose|said|says|told|tell|telling|asked|asks|wish|never|not|don'?t|"
                     r"do not|wasn'?t|isn'?t|when (?:she|he|they))\b[^.!?]*$", re.IGNORECASE)


@cache
def bank(name: str) -> list[str]:
    return json.loads((catalog.DATA / 'breakups' / f'{name}.json').read_text(encoding='utf-8'))['templates']


# Settings and whether it applies ------------------------------------------------------------------------------------

def switched_on(connection) -> bool:
    row = optional(connection, 'SELECT breakups FROM life_settings WHERE id=1')
    return bool(row['breakups']) if row else True


def ladder_of(companion: dict) -> str | None:
    ladder = steps.ladder_of(companion['version']['definition'])
    return ladder if ladder in LADDERS else None


def applies(connection, companion: dict) -> bool:
    return bool(ACTIVE and companion and companion.get('active_timeline_id') and ladder_of(companion)
                and switched_on(connection))


def level(connection) -> int:
    return rough_patches.level(connection)


def local_today(companion: dict, now: datetime) -> date:
    return now.astimezone(zone(companion['version']['timezone'])).date()


# Where things are -----------------------------------------------------------------------------------------------------

def rows(connection, timeline_id: str) -> list[dict]:
    return many(connection, 'SELECT * FROM breakups WHERE timeline_id=? ORDER BY created_at', (timeline_id,))


def picked(connection, consequence_id: str | None) -> int | None:
    if not consequence_id:
        return None
    found = optional(connection, 'SELECT picked FROM consequences WHERE id=?', (consequence_id,))
    return found['picked'] if found else None


def stage(connection, row: dict, on: bool = True) -> str:
    """Where this one stands, worked out when read, so changing a roll on Today moves it: 'together' (back together),
    'ended', 'break', 'thinking', 'strained', or 'eased' / 'none' (over, or never was). With the switch off a warning or
    a break counts as over; an ending stands."""
    if row['together_at'] and (not row['together_id'] or picked(connection, row['together_id']) == YES):
        return 'together'
    if row['ended_by'] == 'you' or (row['ended_by'] == 'them' and picked(connection, row['ended_id']) == YES):
        return 'ended'
    if row['ended_id'] and row['ended_by'] == 'break' and picked(connection, row['ended_id']) == TOGETHER:
        return 'together'
    if row['ended_id'] and row['ended_by'] == 'break' and picked(connection, row['ended_id']) == ENDS:
        return 'ended'
    if not on or row['eased_at']:
        return 'eased'
    if row['break_by'] == 'you' or (row['break_by'] == 'them' and picked(connection, row['break_id']) == YES):
        return 'break'
    if row['thinking_id'] and picked(connection, row['thinking_id']) == YES:
        return 'thinking'
    if row['strained_by'] == 'you' or picked(connection, row['strained_id']) == YES:
        return 'strained'
    return 'none'


OVER = ('together', 'eased', 'none')


def latest(connection, companion: dict) -> tuple[dict | None, str]:
    """The newest one on this timeline and its stage; (None, 'none') when there is none."""
    if not companion or not companion.get('active_timeline_id'):
        return None, 'none'
    found = rows(connection, companion['active_timeline_id'])
    if not found:
        return None, 'none'
    row = found[-1]
    return row, stage(connection, row, applies(connection, companion) or row['ended_at'] is not None)


def current(connection, companion: dict) -> tuple[dict | None, str]:
    """The one still going (a warning, a break, or apart), else (None, 'none')."""
    row, found = latest(connection, companion)
    return (row, found) if row and found not in OVER else (None, 'none')


def apart(connection, companion: dict) -> str | None:
    """'break' or 'ended' while the two of them are apart, else None (other features read this)."""
    if not ACTIVE:
        return None
    _row, found = current(connection, companion)
    return found if found in ('break', 'ended') else None


def ended(connection, companion: dict) -> bool:
    return apart(connection, companion) == 'ended'


def holds(connection, companion: dict) -> str | None:
    """How much they hold back on reaching out (companion/life/openers.py): 'cool' while strained or thinking about a
    break, 'break', 'ended', else None."""
    if not ACTIVE:
        return None
    _row, found = current(connection, companion)
    return 'cool' if found in ('strained', 'thinking') else found if found in ('break', 'ended') else None


# Rolling ----------------------------------------------------------------------------------------------------------

def big_patches(connection, companion: dict, since: datetime) -> list[dict]:
    """Big rough patches of the user's making that started since then and were picked to start."""
    found = many(connection, "SELECT * FROM rough_patches WHERE timeline_id=? AND fault='user' AND size='big' AND "
                 'started_at>=? ORDER BY started_at', (companion['active_timeline_id'], stamp(since)))
    return [row for row in found if rough_patches.picked_open(connection, row)]


def open_patch(connection, companion: dict, now: datetime) -> dict | None:
    """The big rough patch of the user's making open now, if any."""
    found = rough_patches.current(connection, companion, now)
    return found if found and found['size'] == 'big' and found['fault'] == 'user' else None


def facts(connection, companion: dict, now: datetime, row: dict | None = None) -> dict:
    from companion.memory import closeness
    definition = companion['version']['definition']
    try:
        near = closeness.state(connection, companion, now)['level']
    except Exception:  # noqa: BLE001 - a brand-new companion without history counts as just met.
        near = 1
    found = steps.state(connection, companion, now, write=False)
    patch = open_patch(connection, companion, now)
    return {'drama': steps.drama(connection), 'level': level(connection), 'closeness': near,
            'step': steps.index_of(found['ladder'], found['step']) if found else 0,
            'patches': len(big_patches(connection, companion, now - LATELY)),
            'cause': patch['cause'] if patch else '', 'talked': row['talked'] if row else 0,
            'sheet': [group for group in ('forgiving', 'stubborn') if consequences.sheet_has(definition, group)]}


def decide(connection, companion: dict, choice: str, subject: str, found_facts: dict, now: datetime) -> dict:
    names = {'name': companion['version']['definition']['name'].split()[0], 'a': 'someone', 'b': ''}
    table = consequences.tables()[choice]
    return consequences.decide(connection, timeline_id=companion['active_timeline_id'], choice=choice, subject=subject,
                               facts=found_facts, names=names,
                               labels=[option['label'].format(**names) for option in table['options']],
                               day=local_today(companion, now).isoformat(), timestamp=stamp(now), now=now)


def insert(connection, companion: dict, now: datetime, **values) -> dict:
    row_id = identifier()
    columns = {'id': row_id, 'timeline_id': companion['active_timeline_id'], 'companion_id': companion['id'],
               'ladder': ladder_of(companion), 'created_at': stamp(now), **values}
    marks = ', '.join('?' * len(columns))
    connection.execute(f"INSERT INTO breakups ({', '.join(columns)}) VALUES ({marks})",  # noqa: S608
                       tuple(columns.values()))
    return one(connection, 'SELECT * FROM breakups WHERE id=?', (row_id,))


def update(connection, row: dict, **values) -> dict:
    sets = ', '.join(f'{column}=?' for column in values)
    connection.execute(f'UPDATE breakups SET {sets} WHERE id=?', (*values.values(), row['id']))  # noqa: S608
    return one(connection, 'SELECT * FROM breakups WHERE id=?', (row['id'],))


def since(row: dict, column: str, now: datetime) -> int:
    return (now - parse(row[column])).days if row[column] else 0


def calm_since(connection, companion: dict, row: dict, now: datetime) -> datetime:
    """When things were last rough: the latest of the warning itself and any big rough patch mended or faded since."""
    latest_at = parse(row['thinking_at'] or row['strained_at'])
    for patch in big_patches(connection, companion, latest_at - LATELY):
        if rough_patches.still_open(connection, patch, level(connection), now, companion):
            return now
        ended_at = parse(patch['mended_at']) if patch['mended_at'] else None
        latest_at = max(latest_at, ended_at or parse(patch['started_at']))
    return latest_at


def daily(connection, companion: dict, now: datetime) -> None:
    """From the agenda's regular pass: a warning can start, ease or move on, a break ends, an ex may reach out. Cheap:
    no model."""
    if not applies(connection, companion):
        return
    row, found = current(connection, companion)
    lvl = level(connection)
    if found == 'none':
        strain(connection, companion, now)
    elif found in ('strained', 'thinking') and lvl >= 2:
        warn(connection, companion, row, found, lvl, now)
    elif found == 'break':
        end_break(connection, companion, row, lvl, now)
    elif found == 'ended':
        reach_out(connection, companion, row, now)
        lapse(connection, row, now)


def strain(connection, companion: dict, now: datetime) -> dict | None:
    """A big rough patch of the user's making open a couple of days, or the third in a few weeks, rolls once whether
    things get strained."""
    if level(connection) < 2:
        return None
    patch = open_patch(connection, companion, now)
    if not patch:
        return None
    dragged = now - parse(patch['started_at']) >= timedelta(days=STRAIN_AFTER)
    if not dragged and len(big_patches(connection, companion, now - LATELY)) < PILED_UP:
        return None
    subject = f"breakup:{patch['id']}:strained"
    if consequences.recorded(connection, subject, 'user:strained'):
        return None
    outcome = decide(connection, companion, 'user:strained', subject, facts(connection, companion, now), now)
    return insert(connection, companion, now, patch_id=patch['id'], strained_id=outcome['id'], strained_at=stamp(now))


def warn(connection, companion: dict, row: dict, found: str, lvl: int, now: datetime) -> None:
    """Strained or thinking about a break: calm days ease it; a rough patch still open after a few days moves it on."""
    if now - calm_since(connection, companion, row, now) >= timedelta(days=EASE_AFTER[lvl]):
        update(connection, row, eased_at=stamp(now))
        return
    patch = open_patch(connection, companion, now)
    at = 'thinking_at' if found == 'thinking' else 'strained_at'
    if not patch or since(row, at, now) < NEXT_AFTER[lvl]:
        return
    if row['ladder'] == 'friendship':
        outcome = decide(connection, companion, 'user:falling_out', f"breakup:{row['id']}:{patch['id']}:falling_out",
                         facts(connection, companion, now, row), now)
        if outcome['picked'] == YES:
            update(connection, row, ended_id=outcome['id'], ended_by='them', ended_at=stamp(now))
            after_end(connection, companion, now)
        return
    if found == 'strained':
        outcome = decide(connection, companion, 'user:thinking', f"breakup:{row['id']}:{patch['id']}:thinking",
                         facts(connection, companion, now, row), now)
        if outcome['picked'] == YES and not row['thinking_id']:
            update(connection, row, thinking_id=outcome['id'], thinking_at=stamp(now))
        return
    outcome = decide(connection, companion, 'user:break', f"breakup:{row['id']}:{patch['id']}:break",
                     facts(connection, companion, now, row), now)
    if outcome['picked'] == YES and not row['break_id']:
        update(connection, row, break_id=outcome['id'], break_by='them', break_at=stamp(now))
        call_off_plans(connection, companion, now)


def end_break(connection, companion: dict, row: dict, lvl: int, now: datetime) -> None:
    """At the end of the break they decide: try again, or end it. Talking them round during the break counts."""
    if since(row, 'break_at', now) < BREAK_DAYS[max(lvl, 2)]:
        return
    outcome = decide(connection, companion, 'user:after_break', f"breakup:{row['id']}:after_break",
                     facts(connection, companion, now, row), now)
    update(connection, row, ended_id=outcome['id'], ended_by='break', ended_at=stamp(now))
    if outcome['picked'] == ENDS:
        after_end(connection, companion, now)


def after_end(connection, companion: dict, now: datetime) -> None:
    """It is over: plans with the user are called off, and whoever moved in moves out."""
    call_off_plans(connection, companion, now)
    moving_out(connection, companion, now)


def moving_out(connection, companion: dict, now: datetime) -> None:
    from companion.life import moving_in  # Imported here: moving_in reads the steps ladder, which reads breakups.
    moving_in.move_out(connection, companion, now)


def change(connection, companion: dict, consequence_id: str, option: int, now: datetime) -> dict:
    """The user makes a roll go another way on Today ("Why it went this way"). The stage follows at read time; a step
    the roll held back is taken now; and what an ending set going follows here: an ending now moves them out and calls
    plans off, an ending taken back moves them back in, and a break now calls plans off."""
    outcome = consequences.by_id(connection, consequence_id)
    require(outcome['timeline_id'] == companion['active_timeline_id'], 'That outcome is not on this timeline.', 404)
    row = row_of(connection, outcome)
    before = stage(connection, row) if row else None
    changed = consequences.redo(connection, consequence_id, option, now, local_today(companion, now))
    latest_row, _found = latest(connection, companion)
    if row is None or latest_row is None or latest_row['id'] != row['id']:
        return changed
    row = held_back(connection, row, outcome, option, before, now)
    if outcome['choice'] == 'user:reach_out' and option == YES and before == 'ended':
        plan_reach(connection, companion, row, outcome['id'], local_today(companion, now), now)
    follow(connection, companion, row, before, stage(connection, row), now)
    return changed


def follow(connection, companion: dict, row: dict, before: str, after: str, now: datetime) -> None:
    """What a stage reached or left on Today sets going."""
    if before == 'together' and after != 'together':
        for step_id in decode(row['steps_back']) or []:  # Back apart: the steps taken back on getting together return.
            connection.execute('UPDATE relationship_steps SET undone_at=NULL WHERE id=?', (step_id,))
        row = update(connection, row, steps_back=None)
    if after == 'ended' and before != 'ended':
        after_end(connection, companion, now)
    elif before == 'ended' and after == 'together' and stage_before_together(connection, row) == 'ended':
        back_together(connection, companion, row, now)
    elif before == 'ended' and after != 'ended':
        from companion.life import moving_in
        moving_in.move_back(connection, companion, local_day(companion, row['ended_at'] or stamp(now)), now)
    elif after == 'break' and before != 'break':
        call_off_plans(connection, companion, now)


def row_of(connection, outcome: dict) -> dict | None:
    """The episode a roll belongs to: one it moved on, or the one named in its subject (breakup:<id>:...)."""
    found = optional(connection, 'SELECT * FROM breakups WHERE ? IN (strained_id, thinking_id, break_id, ended_id, '
                     'together_id)', (outcome['id'],))
    parts = outcome['subject'].split(':')
    return found or (optional(connection, 'SELECT * FROM breakups WHERE id=? AND timeline_id=?',
                              (parts[1], outcome['timeline_id'])) if len(parts) > 2 else None)


# A roll that held things back, made to move them on: what it would have set (`warn`, `talk_round`, `ask_back`), from
# the stage it was rolled at.
HELD = {'user:thinking': ('thinking_id', {'thinking_at': None}, ('strained',)),
        'user:break': ('break_id', {'break_by': 'them', 'break_at': None}, ('thinking',)),
        'user:falling_out': ('ended_id', {'ended_by': 'them', 'ended_at': None}, ('strained', 'thinking')),
        'user:talk_round': ('together_id', {'together_by': 'them', 'together_at': None}, ('break',)),
        'user:back_together': ('together_id', {'together_by': 'you', 'together_at': None}, ('ended',))}


def held_back(connection, row: dict, outcome: dict, option: int, before: str, now: datetime) -> dict:
    column, values, stages = HELD.get(outcome['choice'], (None, {}, ()))
    if column is None or option != YES or before not in stages:
        return row
    return update(connection, row, **{column: outcome['id']}, **{key: value or stamp(now)
                                                                  for key, value in values.items()})


def call_off_plans(connection, companion: dict, now: datetime) -> None:
    """Outings with the user that haven't started yet are off while they are apart."""
    from companion.life import outings
    tz = companion['version']['timezone']
    for outing in outings.in_force(connection, companion['active_timeline_id'], local_today(companion, now).isoformat()):
        if outings.state(outing, tz, now) == 'planned':
            connection.execute("UPDATE outings SET status='cancelled', cancelled_at=? WHERE id=?",
                               (stamp(now), outing['id']))


def back_together(connection, companion: dict, row: dict, now: datetime) -> None:
    """Back together after it ended: they start again from a key to each other's place. Living together, an engagement
    or a marriage are taken back (they live apart now); the scrapbook keeps them (`scrapbook_items`)."""
    if row['ladder'] != 'romance' or stage_before_together(connection, row) != 'ended':
        return
    cut = steps.index_of('romance', 'moving_in')
    taken = [found for found in steps.reached(connection, companion['active_timeline_id'], 'romance')
             if steps.index_of('romance', found['step']) >= cut]
    for found in taken:
        connection.execute('UPDATE relationship_steps SET undone_at=? WHERE id=?', (stamp(now), found['id']))
    if taken:
        update(connection, row, steps_back=encode([found['id'] for found in taken]))


def stage_before_together(connection, row: dict) -> str:
    """Whether they were apart for good (ended) before getting back together, or only on a break."""
    if row['ended_by'] in ('you', 'them') or picked(connection, row['ended_id']) == ENDS:
        return 'ended'
    return 'break'


# Exes ------------------------------------------------------------------------------------------------------------

def reach_out(connection, companion: dict, row: dict, now: datetime) -> dict | None:
    """About once a month after a while apart, the engine decides whether they reach out about trying again."""
    if since(row, 'ended_at', now) < REACH_AFTER or open_reach(connection, row):
        return None
    today = local_today(companion, now)
    window = (today.toordinal() + random.Random(f"reach-day:{row['id']}").randrange(30)) // 30
    subject = f"breakup:{row['id']}:reach:{window}"
    if consequences.recorded(connection, subject, 'user:reach_out'):
        return None
    found_facts = {**facts(connection, companion, now, row), 'ended_by': row['ended_by'],
                   'months': since(row, 'ended_at', now) // 30}
    outcome = decide(connection, companion, 'user:reach_out', subject, found_facts, now)
    if outcome['picked'] != YES:
        return None
    due = today + timedelta(days=random.Random(f'{subject}:due').randint(1, 10))
    return plan_reach(connection, companion, row, outcome['id'], due, now)


def plan_reach(connection, companion: dict, row: dict, consequence_id: str, due: date, now: datetime) -> dict | None:
    """Reaching out, due on that day (a roll made to go this way on Today: today)."""
    if open_reach(connection, row) or optional(connection, 'SELECT id FROM breakup_reaches WHERE consequence_id=?',
                                               (consequence_id,)):
        return None
    reach_id = identifier()
    connection.execute("INSERT INTO breakup_reaches (id, breakup_id, timeline_id, status, due_on, consequence_id, "
                       "created_at) VALUES (?, ?, ?, 'planned', ?, ?, ?)",
                       (reach_id, row['id'], row['timeline_id'], due.isoformat(), consequence_id, stamp(now)))
    return one(connection, 'SELECT * FROM breakup_reaches WHERE id=?', (reach_id,))


def open_reach(connection, row: dict) -> dict | None:
    return optional(connection, "SELECT * FROM breakup_reaches WHERE breakup_id=? AND status IN ('planned', 'open') "
                    'ORDER BY created_at DESC LIMIT 1', (row['id'],))


def lapse(connection, row: dict, now: datetime) -> None:
    """Reaching out left unanswered for a few days lapses; one whose roll was changed on Today is dropped."""
    for reach in many(connection, "SELECT * FROM breakup_reaches WHERE breakup_id=? AND status IN ('planned', 'open')",
                      (row['id'],)):
        if picked(connection, reach['consequence_id']) != YES:
            connection.execute("UPDATE breakup_reaches SET status='dropped', settled_at=? WHERE id=?",
                               (stamp(now), reach['id']))
        elif reach['status'] == 'open' and now - parse(reach['created_at']) >= timedelta(days=REACH_OPEN):
            connection.execute("UPDATE breakup_reaches SET status='lapsed', settled_at=? WHERE id=?",
                               (stamp(now), reach['id']))


# First texts (companion/life/openers.py) ------------------------------------------------------------------------

SETTLES = ('reach_out',)
REASONS = {
    'break': "Things between you and the user have been strained for a while, and you have decided you need a break. "
             'Tell them, kindly and honestly, in your own words: it is a break, not a breakup, and you need some '
             'space to think. Do not list everything that went wrong.',
    'ending': 'You and the user have been on a break, and you have decided to end things for good. Tell them, gently '
              'and clearly, in your own words. Do not blame them or leave the door open.',
    'falling_out': 'Things between you and the user, your friend, have been strained for a while, and you need some '
                   'distance from the friendship for now. Tell them honestly and without cruelty, in your own words.',
    'reach_out': 'You and the user broke up a while ago, and you keep thinking about them. Reach out, tentatively, in '
                 'your own words, to see whether they would want to talk about trying again. Leave them room to say no.',
}


def told(connection, row: dict, at: str) -> bool:
    """Whether they have written to the user since `at` (the line told them to say it, or a first text did)."""
    return bool(optional(connection, "SELECT id FROM messages WHERE timeline_id=? AND role='companion' "
                         "AND status='complete' AND created_at>=? LIMIT 1", (row['timeline_id'], row[at])))


def news_due(connection, companion: dict, now: datetime) -> list:
    """They asked for a break, ended it, or fell out, and haven't said so yet; or reaching out is due."""
    from companion.life.openers import Trigger
    if not ACTIVE or not FIRST_TEXTS or not applies(connection, companion):
        return []
    row, found = current(connection, companion)
    if row is None:
        return []
    seed = random.Random(f"{row['id']}:{found}")
    if found == 'break' and row['break_by'] == 'them' and not told(connection, row, 'break_at'):
        return [Trigger(f"breakup:{row['id']}:break", 'breakup', REASONS['break'], seed.choice(bank('break_asks')))]
    if found == 'ended' and row['ended_by'] in ('them', 'break') and not told(connection, row, 'ended_at'):
        kind = 'falling_out' if row['ladder'] == 'friendship' else 'ending'
        return [Trigger(f"breakup:{row['id']}:ended", 'breakup', REASONS[kind], seed.choice(bank(kind)))]
    reach = open_reach(connection, row) if found == 'ended' else None
    if reach and reach['status'] == 'planned' and reach['due_on'] <= local_today(companion, now).isoformat() and \
            picked(connection, reach['consequence_id']) == YES:
        return [Trigger(f"breakup-reach:{reach['id']}", 'reach_out', REASONS['reach_out'],
                        random.Random(reach['id']).choice(bank('reaching_out')), (reach['id'],))]
    return []


def settle(connection, companion: dict, message: dict, trigger, timestamp: str) -> None:
    """Reaching out went out: it waits for the user's answer."""
    connection.execute("UPDATE breakup_reaches SET status='open', message_id=?, created_at=? WHERE id=? AND "
                       "status='planned'", (message['id'], timestamp, trigger.sources[0]))


# Reading the user's messages -------------------------------------------------------------------------------------

def said(pattern: re.Pattern, text: str) -> bool:
    for sentence in re.split(r'(?<=[.!?])\s+|\n+', steps.plain(text or '')):
        found = pattern.search(sentence)
        if found and not NOT_NOW.search(sentence[:found.start()]):
            return True
    return False


def note(connection, message: dict, companion: dict, now: datetime) -> None:
    """A user message, before the reply is written: ending it or asking for a break, asking to try again, an answer to
    reaching out, and sorry or a kind gesture during a break."""
    if not applies(connection, companion) or message['role'] != 'user':
        return
    if optional(connection, 'SELECT id FROM breakups WHERE message_id=? OR answer_id=?', (message['id'], message['id'])):
        return
    text, ladder = message['text'] or '', ladder_of(companion)
    row, found = current(connection, companion)
    if found != 'ended' and said(FRIENDS_END if ladder == 'friendship' else BREAK_UP, text):
        you_end(connection, companion, row, message, now)
        return
    if ladder == 'romance' and found not in ('break', 'ended') and said(TAKE_BREAK, text):
        you_break(connection, companion, row, message, now)
        return
    if found in ('ended', 'break'):
        while_apart(connection, companion, row, found, message, now)


def while_apart(connection, companion: dict, row: dict, found: str, message: dict, now: datetime) -> None:
    """Exes: an answer to reaching out, or asking to get back together. On a break: asking to try again, or sorry or a
    kind gesture, which counts at the end of the break."""
    text = message['text'] or ''
    if found == 'ended':
        reach = open_reach(connection, row)
        if reach and reach['status'] == 'open':
            answer_reach(connection, companion, row, reach, message, now)
        elif said(COME_BACK, text):
            ask_back(connection, companion, row, message, now)
    elif said(COME_BACK, text):
        talk_round(connection, companion, row, message, now)
    elif rough_patches.says('apologies', text) or rough_patches.says('gestures', text):
        update(connection, row, talked=row['talked'] + 1)


def you_end(connection, companion: dict, row: dict | None, message: dict, now: datetime) -> None:
    values = {'ended_by': 'you', 'ended_at': stamp(now), 'message_id': message['id']}
    if row is None:
        insert(connection, companion, now, strained_by='you', strained_at=stamp(now), **values)
    else:
        update(connection, row, **values)
    after_end(connection, companion, now)


def you_break(connection, companion: dict, row: dict | None, message: dict, now: datetime) -> None:
    values = {'break_by': 'you', 'break_at': stamp(now), 'message_id': message['id']}
    if row is None:
        insert(connection, companion, now, strained_by='you', strained_at=stamp(now), **values)
    else:
        update(connection, row, **values)
    call_off_plans(connection, companion, now)


def talk_round(connection, companion: dict, row: dict, message: dict, now: datetime) -> None:
    """During a break the user asks to try again: answered at once, once a day."""
    day = local_today(companion, now).isoformat()
    outcome = decide(connection, companion, 'user:talk_round', f"breakup:{row['id']}:round:{day}",
                     facts(connection, companion, now, row), now)
    row = update(connection, row, answer_id=message['id'], answer_said='yes' if outcome['picked'] == YES else 'no',
                 talked=row['talked'] + 1)
    if outcome['picked'] == YES:
        update(connection, row, together_at=stamp(now), together_by='them', together_id=outcome['id'])


def ask_back(connection, companion: dict, row: dict, message: dict, now: datetime) -> None:
    """An ex asked to get back together: the engine decides, once a week."""
    week = local_today(companion, now).toordinal() // 7
    found_facts = {**facts(connection, companion, now, row), 'ended_by': row['ended_by'],
                   'days_apart': since(row, 'ended_at', now)}
    outcome = decide(connection, companion, 'user:back_together', f"breakup:{row['id']}:back:{week}", found_facts, now)
    row = update(connection, row, answer_id=message['id'], answer_said='yes' if outcome['picked'] == YES else 'no')
    if outcome['picked'] == YES:
        row = update(connection, row, together_at=stamp(now), together_by='you', together_id=outcome['id'])
        back_together(connection, companion, row, now)


def answer_reach(connection, companion: dict, row: dict, reach: dict, message: dict, now: datetime) -> None:
    said_now = steps.answer(message['text'] or '')
    if said_now is None:
        return
    status = 'yes' if said_now == 'yes' else 'no'
    connection.execute('UPDATE breakup_reaches SET status=?, answer_id=?, settled_at=? WHERE id=?',
                       (status, message['id'], stamp(now), reach['id']))
    row = update(connection, row, answer_id=message['id'], answer_said=f'reach_{status}')
    if status == 'yes':
        row = update(connection, row, together_at=stamp(now), together_by='them')
        back_together(connection, companion, row, now)


# The chat notes ------------------------------------------------------------------------------------------------

LINES = {
    'strained': ('- Things have been strained between you and the user lately: the rough patches keep coming, and it '
                 'is wearing on you. You still care, but you are guarded and unsure where this is going. Do not talk '
                 'about the future or plans together unless they do.'),
    'thinking': ('- Things have been strained between you and the user for a while, and you have started wondering '
                 'whether you two need a break. You have not said so, and you do not bring it up now, but it weighs '
                 'on you: you are quieter and more distant than usual.'),
    'break_tell': ('- You have decided you need a break from the user: things have been strained for too long. Tell '
                   'them now, kindly and honestly, in your own words. It is a break, not a breakup: you need some '
                   'space to think.'),
    'break': ('- You and the user have been on a break since {date} ({who} asked for it). You are not broken up, but you '
              'are not acting as a couple right now: keep replies short and a little distant, make no plans, and do '
              'not flirt. If they want to talk about it, listen.'),
    'end_tell': ('- After your break, you have decided to end things with the user for good. Tell them now, gently and '
                 'clearly, in your own words. Do not blame them or leave the door open.'),
    'ended': ('- You and the user broke up on {date} ({who} ended it). You are exes now and you have your own life. Be '
              'polite and a little distant; do not flirt or act like a couple, and do not suggest getting back '
              'together.'),
    'fell_out_tell': ('- Things between you and the user, your friend, have been strained for too long: you need some '
                      'distance from the friendship for now. Tell them now, honestly and without cruelty, in your own '
                      'words.'),
    'fell_out': ('- You and the user had a falling out on {date} and you are not close right now. Be civil and brief, '
                 'and do not act as if nothing happened.'),
    'you_ended': ('- The user just broke up with you. It hurts. React honestly in your own words; do not beg or argue, '
                  'and do not pretend it is fine.'),
    'you_fell_out': ('- The user just told you they do not want to be friends anymore. It hurts. React honestly in your '
                     'own words; do not beg or argue.'),
    'you_break': ('- The user just asked for a break. It hurts, but take it in your own words; say how you feel if you '
                  'want to, and do not argue.'),
    'round_yes': '- The user asked to try again, and you want that too: say so in your own words. You are back together.',
    'round_no': ("- The user asked to try again. You aren't ready yet: say so kindly, in your own words. You still need "
                 'time.'),
    'back_yes': ('- The user asked to get back together, and you want that too: say so in your own words. You are '
                 'together again, carefully, starting over.'),
    'back_no': ("- The user asked to get back together. You don't want that: say so kindly and clearly, in your own "
                'words.'),
    'friends_yes': ('- The user asked to be friends again, and you want that too: say so in your own words. You have '
                    'made up.'),
    'friends_no': ("- The user asked to be friends again. You aren't ready: say so kindly and honestly, in your own "
                   'words.'),
    'reach_waiting': ('- Earlier you reached out to the user about maybe trying again, and they have not answered yet. '
                      'If they answer now, take it as they mean it; do not ask again.'),
    'reach_yes': ('- You reached out about trying again and the user just said yes. You are back together, carefully, '
                  'starting over: say how glad you are in your own words.'),
    'reach_no': ("- You reached out about trying again and the user just said no. It stings, but you respect it."),
    'together': ('- You and the user got back together a few hours ago, after {what}. It is tender and new again: let '
                 'them feel you are glad to be together again, warm and a little careful.'),
}


def long_date(when: str) -> str:
    return steps.long_date(when)


def who_said(row: dict, by: str) -> str:
    return 'the user' if row[by] == 'you' else 'you'


# In a group chat only where things stand: telling the user, or waiting for their answer, belongs to the 1:1 chat.
STANDING = {'break_tell': 'break', 'end_tell': 'ended', 'fell_out_tell': 'fell_out', 'reach_waiting': 'ended'}


def context_lines(connection, companion: dict, now: datetime, turn: set[str],
                  standing: bool = False) -> list[tuple[str, str]]:
    """(identity, line) for the 'breakup' section: at most one line; `standing` for a group chat."""
    if not ACTIVE or not companion or not ladder_of(companion):
        return []
    row, found = latest(connection, companion)
    if row is None or (found != 'ended' and not applies(connection, companion)):
        return []  # With the switch off an ending still stands (`stage`), so an ex still knows it.
    key = line_key(connection, row, found, now, turn)
    friend = row['ladder'] == 'friendship'
    if standing and key:
        key = STANDING.get(key, key)
        key = 'fell_out' if friend and key == 'ended' else key
    if key is None:
        return []
    if key == 'together':
        what = 'a falling out' if friend else 'breaking up' if stage_before_together(connection, row) == 'ended' \
            else 'a break'
        return [(f"breakup:{row['id']}:together", LINES['together'].format(what=what))]
    when = row['ended_at'] if found == 'ended' else row['break_at']
    by = 'ended_by' if found == 'ended' else 'break_by'
    text = LINES[key].format(date=long_date(local_day(companion, when)) if when else '',
                             who=who_said(row, by) if row[by] in ('you', 'them') else 'you')
    return [(f"breakup:{row['id']}:{key}", text)]


def local_day(companion: dict, when: str) -> str:
    return parse(when).astimezone(zone(companion['version']['timezone'])).date().isoformat()


def turn_key(row: dict, found: str, turn: set[str]) -> str | None:
    """A line for what the user said in the turn being answered: ending it, a break, or asking to try again."""
    friend = row['ladder'] == 'friendship'
    if row['answer_id'] and row['answer_id'] in turn:
        answered = row['answer_said'] or ''
        if answered.startswith('reach_'):
            return answered
        if found == 'together':
            return 'friends_yes' if friend else 'round_yes' if row['break_at'] and not row['ended_at'] else 'back_yes'
        return 'friends_no' if friend else 'back_no' if found == 'ended' else 'round_no'
    if row['message_id'] and row['message_id'] in turn and found in ('ended', 'break'):
        return ('you_fell_out' if friend else 'you_ended') if found == 'ended' else 'you_break'
    return None


def line_key(connection, row: dict, found: str, now: datetime, turn: set[str]) -> str | None:
    friend = row['ladder'] == 'friendship'
    if said_now := turn_key(row, found, turn):
        return said_now
    if found == 'together':
        when = row['together_at'] or row['ended_at']
        return 'together' if when and now - parse(when) < FRESH else None
    if found == 'ended':
        reach = open_reach(connection, row)
        if reach and reach['status'] == 'open':
            return 'reach_waiting'
        if row['ended_by'] in ('them', 'break') and not told(connection, row, 'ended_at'):
            return 'fell_out_tell' if friend else 'end_tell'
        return 'fell_out' if friend else 'ended'
    if found == 'break':
        return 'break_tell' if row['break_by'] == 'them' and not told(connection, row, 'break_at') else 'break'
    return found if found in ('strained', 'thinking') else None


def offer(packet, connection, companion: dict, now: datetime, recent: list[dict], group=None) -> None:
    """Adds the 'breakup' section; in a group chat only where things stand (so an ex in a group knows it)."""
    turn = set()
    for message in reversed(recent if group is None else []):
        if message['role'] != 'user':
            break
        turn.add(message['id'])
    for identity, text in context_lines(connection, companion, now, turn, standing=group is not None):
        packet.offer('breakup', identity, text)


# The steps line, the scrapbook ----------------------------------------------------------------------------------------

def scrapbook_items(connection, companion: dict, low: str, high: str) -> list[dict]:
    """Breaks, breakups and getting back together in a stretch of time, and steps taken back on getting back together
    (they happened, so they stay)."""
    result = []
    tz = companion['version']['timezone']
    for row in rows(connection, companion['active_timeline_id']):
        found = stage(connection, row, True)
        friend = row['ladder'] == 'friendship'
        items = []
        if row['break_at'] and found in ('break', 'ended', 'together') and (
                row['break_by'] == 'you' or picked(connection, row['break_id']) == YES):
            items.append((row['break_at'], 'You took a break'))
        if row['ended_at'] and (found == 'ended' or found == 'together' and stage_before_together(connection, row) == 'ended'):
            items.append((row['ended_at'], 'You had a falling out' if friend else 'You broke up'))
        if found == 'together' and (row['together_at'] or row['ended_at']):
            items.append((row['together_at'] or row['ended_at'], 'You made up' if friend else 'You got back together'))
        for when, text in items:
            day = parse(when).astimezone(zone(tz)).date().isoformat()
            if low <= day <= high:
                result.append({'date': day, 'text': text})
        for step_id in decode(row['steps_back']) or []:
            step_row = optional(connection, 'SELECT * FROM relationship_steps WHERE id=?', (step_id,))
            if step_row and low <= step_row['reached_on'] <= high:
                result.append({'date': step_row['reached_on'],
                               'text': f"You {steps.step_of('romance', step_row['step']).did}"})
    return result


# Showing it -------------------------------------------------------------------------------------------------------

TEXT = {'strained': 'Things are strained', 'thinking': "They're thinking about a break", 'break': 'On a break',
        'ended': 'Broke up', 'fell_out': 'Fell out'}


def view(connection, companion: dict, now: datetime) -> dict:
    """{stage, text, summary, since, by, id, odds, strip, mendable, ladder, on} for the Character page and the chat strip.
    `odds` are the rolls behind it, for "Why it went this way" with Hidden values > odds; `mendable` offers the override
    (getting back together always, a warning or a break with Hidden values > moods); `strip` is false a week after it
    ended."""
    empty = {'stage': None, 'text': '', 'since': None, 'by': None, 'id': None, 'odds': [], 'strip': False,
             'mendable': False, 'summary': '',
             'ladder': ladder_of(companion) if companion else None, 'on': bool(companion) and switched_on(connection)}
    if not ACTIVE or not companion:
        return empty
    row, found = current(connection, companion)
    if row is None:
        return empty
    friend = row['ladder'] == 'friendship'
    when = {'strained': 'strained_at', 'thinking': 'thinking_at', 'break': 'break_at', 'ended': 'ended_at'}[found]
    by = {'break': row['break_by'], 'ended': row['ended_by']}.get(found)
    shown = settings(connection)
    # The roll that brought it here (the earlier ones are on Today).
    odds = [row[column] for column in ('ended_id', 'break_id', 'thinking_id', 'strained_id') if row[column]][:1]
    recent = found != 'ended' or now - parse(row['ended_at']) < STRIP_ENDED
    return {**empty, 'stage': found, 'id': row['id'], 'since': local_day(companion, row[when]),
            'summary': summary(connection, companion, row, found, now),
            'text': TEXT['fell_out' if friend and found == 'ended' else found],
            'by': 'you' if by == 'you' else 'them' if by else None, 'strip': recent,
            'mendable': found == 'ended' or bool(shown.get('show_moods')),
            'odds': odds if shown.get('show_odds') else []}


def summary(connection, companion: dict, row: dict, found: str, now: datetime) -> str:
    """What stands in for the steps line ("Together 8 months, in love") while apart: "On a break", "Broke up after 8
    months", "Fell out after 2 years". Empty while it is only a warning."""
    if found == 'break':
        return 'On a break'
    if found != 'ended':
        return ''
    steps_now = steps.state(connection, companion, now, write=False)
    first = steps_now['steps'][0] if steps_now and steps_now['steps'] else None
    what = 'Fell out' if row['ladder'] == 'friendship' else 'Broke up'
    if not first or first['how'] in ('history', 'start'):  # No real date for where the app started them.
        return what
    days = (date.fromisoformat(local_day(companion, row['ended_at'])) - date.fromisoformat(first['on'])).days
    return f'{what} after {steps.span_text(days)}'


def mend(database, breakup_id: str) -> dict:
    """The user overrides: a warning or a break is over, or exes are back together."""
    from companion.characters import require_current
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        now = database.clock.now()
        row, found = current(connection, companion)
        require(row is not None and row['id'] == breakup_id, 'That is no longer going on.', 404)
        if found == 'ended':
            row = update(connection, row, together_at=stamp(now), together_by='set')
            back_together(connection, companion, row, now)
        else:
            update(connection, row, eased_at=stamp(now))
        return view(connection, companion, now)


def undo_mend(database, breakup_id: str) -> dict:
    """Take back the override: things are as they were (steps taken back on getting back together come back)."""
    from companion.characters import require_current
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        row = optional(connection, 'SELECT * FROM breakups WHERE id=? AND timeline_id=?',
                       (breakup_id, companion['active_timeline_id']))
        require(row is not None and (row['together_by'] == 'set' or row['eased_at'] and not row['together_at']),
                'That can no longer be undone.', 409)
        for step_id in decode(row['steps_back']) or []:
            connection.execute('UPDATE relationship_steps SET undone_at=NULL WHERE id=?', (step_id,))
        update(connection, row, together_at=None, together_by=None, eased_at=None, steps_back=None)
        return view(connection, companion, database.clock.now())


def read(database) -> dict:
    from companion.characters import require_current
    with database.connect() as connection:
        return view(connection, require_current(connection), database.clock.now())


# Branching (companion/timelines.py) ---------------------------------------------------------------------------------

# What a later moment set, and the columns it set: a fork from before it never had it.
LATER = (('thinking_at', ('thinking_id', 'thinking_at')), ('break_at', ('break_id', 'break_by', 'break_at')),
         ('ended_at', ('ended_id', 'ended_by', 'ended_at')), ('eased_at', ('eased_at',)),
         ('together_at', ('together_id', 'together_by', 'together_at', 'steps_back')))


def copy(connection, parent_id: str, new_id: str, ids: dict, cutoff: str) -> None:
    """Warnings, breaks and breakups begun by the fork carry over as they stood then, with their rolls; reaching out
    is the copy's own."""
    for row in rows(connection, parent_id):
        if row['created_at'] > cutoff:
            continue
        found = {**row, 'id': identifier(), 'timeline_id': new_id, 'message_id': ids.get(row['message_id']),
                 'answer_id': ids.get(row['answer_id'])}
        for at, columns in LATER:
            if row[at] and row[at] > cutoff:
                found.update(dict.fromkeys(columns))
        for column in ('strained_id', 'thinking_id', 'break_id', 'ended_id', 'together_id'):
            if found[column]:
                subject = optional(connection, 'SELECT subject FROM consequences WHERE id=?', (found[column],))
                found[column] = consequences.copy(connection, found[column], new_id, (subject or {}).get(
                    'subject', '').replace(row['id'], found['id']) or f"breakup:{found['id']}:{column}")
        marks = ', '.join('?' * len(found))
        connection.execute(f"INSERT INTO breakups ({', '.join(found)}) VALUES ({marks})",  # noqa: S608
                           tuple(found.values()))
