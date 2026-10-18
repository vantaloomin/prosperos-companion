"""Rough patches and making up (Hit List #63, v0.13 Life Together): a falling-out that lasts until it is mended.

What opens one, all caught by rules from what the app already knows:
- words that sting, aimed at them (`STINGS`, a narrower list than the one moods.py reads);
- an agreed plan with a date passing without a word, or their birthday or your anniversary going unmentioned
  (companion/life/reactions.py notices both);
- a secret coming out: you told someone what they trusted you with, or they found out you kept something from them
  (companion/secrets.py);
- a broken promise: "I'll call you tonight" said in the chat, and no word from you by then (`rough_patch_promises`);
- calling off an outing on its own day (small friction, gone in a day);
- finding out you're seeing someone else once you two are exclusive (`seeing_someone`, called by Next steps), never
  on an easy life;
- small everyday friction other features report through `friction` (a chore after moving in, or another of your
  partners wanting to move in when they aren't ready to share their home);
- saying no when they ask you to marry them (`proposal_no`, from companion/life/wedding.py).

Whether something you did starts a rough patch is a roll in the consequence engine (choice user:rough_patch in
world/data/consequences.json): odds from the Rough patches slider (life_settings.rough_patches_realism: 0 off,
1 easy, 2 real life, 3 dramatic), what happened, an emotional trait the user built that speaks to it, their own
description (forgiving, holds on to things) and how close they are. The odds stay under Hidden values ("Why it went
this way" on Today, with show_odds), where the user can also make it go the other way. One over the same thing as a
rough patch already open (or one that started that day) is less likely, a half for the second, a quarter for the third
(`stacked_on`), and counts for less where Breaks and breakups adds them up (`weighed`).

The companion can be the one at fault: on Real life and Drama they now and then call off an outing with you at the
last minute (`stand_ups`), and then apologise first, in a first text.

It lasts until mended: an apology the app recognises from fixed phrases (data/rough_patches/apologies.json), a
make-up gesture (a gift or kind act in the chat, data/rough_patches/gestures.json; or an outing or visit with you
that happens), or enough calm days. On an easy life it fades overnight; on real life an apology or a gesture mends
it, or a few calm days; on drama it lingers for two weeks unless you make up, and something serious (a secret, being
with someone else) needs both an apology and a gesture. When they were at fault, it mends when you accept their
apology (data/rough_patches/accepting.json), when the next plan together happens, or after a calm day or two.

While one is open, rules make them cooler: no check-ins, invitations, knocks or calls of their own (openers.py), and
one line in the chat notes ('patch') says what it is about and how it colors their replies. The Character page says
"Things are a bit tense"; with Hidden values > moods it also says what about, and offers Let it go.
"""
import json
import random
import re
from datetime import datetime, time, timedelta
from functools import cache

from companion import consequences
from companion.clock import parse, stamp, zone
from companion.database import identifier, many, one, optional, settings
from companion.errors import require
from companion.life import reactions
from companion.memory import pairs
from companion.world import catalog

# Off in unrelated tests (tests/conftest.py); tests/test_rough_patches.py turns it on.
ACTIVE = True
FIRST_TEXTS = True
DEFAULT_LEVEL = 2
CHOICE = 'user:rough_patch'
OPENS = 1  # The option in the odds table that starts one.

# cause: (size, whose fault)
CAUSES = {
    'words': ('big', 'user'), 'missed_plan': ('big', 'user'), 'forgot_occasion': ('big', 'user'),
    'secret_told': ('big', 'user'), 'secret_kept': ('big', 'user'), 'promise': ('big', 'user'),
    'seeing_someone': ('big', 'user'), 'called_off': ('small', 'user'), 'chore': ('small', 'user'), 'sharing': ('small', 'user'),
    'stood_up': ('big', 'companion'), 'hidden_partner': ('big', 'companion'), 'proposal_no': ('big', 'user'),
}
# What they did, for the lines about their own fault: (in the chat context, after "You let the user down: ", and
# after "The user forgave you for "). `hidden_partner` comes from Their own love life (companion/life/love_life.py).
THEIR_DEED = {'stood_up': ('you called off {about}', 'calling off {about}'),
              'hidden_partner': ('{about}', 'seeing someone behind their back')}
# On drama these need both an apology and a gesture.
SERIOUS = {'secret_told', 'secret_kept', 'seeing_someone'}
# Calm days before it mends by itself, by slider level, for (the user's fault, theirs). Level 1 fades overnight.
CALM = {2: (timedelta(days=3), timedelta(days=2)), 3: (timedelta(days=14), timedelta(days=4))}
SMALL_FOR = timedelta(days=1)
# How long the chat still hears that you just made up.
MADE_UP_FOR = timedelta(hours=6)
# Emotional traits whose names speak to each cause (reactions.MINDS covers the rest).
MINDS = {'words': r'sensitive|thin[- ]skinned|insecure|proud|need|lonely|sulk',
         'promise': reactions.MINDS['user:missed_plan'], 'missed_plan': reactions.MINDS['user:missed_plan'],
         'forgot_occasion': reactions.MINDS['user:forgot_occasion'], 'secret_told': reactions.MINDS['user:told_secret'],
         'secret_kept': r'trust|betray|honest|secret|loyal|guarded|parano',
         'seeing_someone': r'jealous|possessive|insecure|loyal|trust|clingy|need',
         'called_off': reactions.MINDS['user:missed_plan'], 'chore': r'tidy|neat|clean|particular|fussy',
         'sharing': r'jealous|possessive|insecure|territorial|clingy|need',
         'proposal_no': r'insecure|sensitive|need|lonely|reject|abandon|clingy|romantic'}

# Words aimed at them that can start one: a narrower set than the mood nudge, and only said to them.
STINGS = re.compile(r"\b(?:shut up|go away|leave me alone|you'?re (?:so )?(?:annoying|useless|boring|pathetic|"
                    r"stupid|dumb|an idiot)|you (?:idiot|loser)|i hate you|(?:you|you'?re) (?:are )?(?:so )?"
                    r"(?:selfish|clingy|exhausting))\b", re.IGNORECASE)
NEGATED = re.compile(r"\b(?:not|never|no way|don'?t|didn'?t|isn'?t|wasn'?t|won'?t|n't)\b[\w' ]{0,12}$", re.IGNORECASE)
NOT_AN_APOLOGY = re.compile(r"\bsorry (?:if |that )?you (?:feel|think|took|see)|\bsorry not sorry|\bsorry,? but you\b",
                            re.IGNORECASE)
# "I'm sorry to hear that": sympathy, not an apology.
SYMPATHY = re.compile(r" (?:to hear|for your loss|(?:that|this) happened to you|you(?:'re| are) (?:going through|dealing "
                      r"with)|you have to)\b")
# A plain "sorry" opening the message counts too ("hey sorry, crazy day"; Vanta 2026-10-18), after at most a greeting or
# filler word; not "sorry?" or "sorry, what?" (not catching what was said), nor sympathy.
BARE_SORRY = re.compile(r"^(?:(?:hey|hi|ok|okay|oh|ugh|um|look|listen|so|babe|love|honestly|god|omg|argh|ah)[,.!]*\s+){0,2}"
                        r"(?:so |really |very )?sorry\b(?!\s*\?)(?!,? (?:what|who|where|wrong|come again|didn'?t catch))")
# "I'll call you tonight", "I promise I'll text you after work": a promise the app can check.
PROMISE = re.compile(r"\b(?:i'?ll|i will|i promise(?: i'?ll| to| i will)?|i'?m (?:going to|gonna))\s+(?:call|text|"
                     r"message|ring|phone|facetime|write to|get back to)\s+(?:you|u)(?:\s+back)?\b(?P<when>[^.!?\n]{0,40})",
                     re.IGNORECASE)
WHEN = (('tomorrow', 'tomorrow'), ('in the morning', 'morning'), ('first thing', 'morning'),
        ('tonight', 'tonight'), ('this evening', 'tonight'), ('after work', 'after'), ('after class', 'after'),
        ('when i get home', 'after'), ("when i'm home", 'after'), ("when i'm done", 'after'),
        ("when i'm free", 'after'), ('later', 'soon'), ('in a bit', 'soon'), ('in a few', 'soon'), ('soon', 'soon'))
KEEP_GAP = timedelta(minutes=45)
# Standing someone up: the chance, by level, that an outing with the user is called off by them on the day.
STAND_UP = {2: 0.03, 3: 0.08}
STAND_UP_BEFORE = timedelta(hours=3)
# Stacking: a rough patch over the same thing as one already open, or one that started the same day, weighs less (the
# second counts half, the third a quarter; Vanta 2026-10-17), in the roll that starts it (reader `stacked`) and in what
# Breaks and breakups counts (`weighed`). Not a cap: four stinging messages in two minutes can still be four.
STACK_WEIGHT = 0.5


def level(connection) -> int:
    row = optional(connection, 'SELECT rough_patches_realism FROM life_settings WHERE id=1')
    return row['rough_patches_realism'] if row and row['rough_patches_realism'] in range(4) else DEFAULT_LEVEL


@cache
def bank(name: str) -> list[str]:
    data = json.loads((catalog.DATA / 'rough_patches' / f'{name}.json').read_text(encoding='utf-8'))
    return data.get('phrases') or data.get('reasons') or data['templates']


@cache
def pattern(name: str) -> re.Pattern:
    phrases = sorted(bank(name), key=len, reverse=True)
    return re.compile(r'(?<![\w])(?:' + '|'.join(re.escape(phrase) for phrase in phrases) + r')(?![\w])')


def plain(text: str) -> str:
    return ' '.join((text or '').replace('’', "'").replace('‘', "'").casefold().split())


def says(name: str, text: str) -> bool:
    """Whether the message says one of the bank's phrases, not negated ("I'm not sorry")."""
    words = plain(text)
    if name == 'apologies' and NOT_AN_APOLOGY.search(words):
        return False
    if name == 'apologies' and (bare := BARE_SORRY.match(words)) and not SYMPATHY.match(words, bare.end()):
        return True
    return any(not NEGATED.search(words[:found.start()]) and not (name == 'apologies' and SYMPATHY.match(words, found.end()))
               for found in pattern(name).finditer(words))


def stings(text: str) -> str | None:
    """The sentence of the message that stings, aimed at them, if any; jokes and negations don't count."""
    from companion.moods import JOKING, hurtful
    sentence = hurtful(text, STINGS, NEGATED, skip=JOKING)
    return sentence[:80] if sentence else None


# Opening ------------------------------------------------------------------------------------------------------

def local_day(companion: dict, now: datetime) -> str:
    return now.astimezone(zone(companion['version']['timezone'])).date().isoformat()


def facts(connection, companion: dict, cause: str, now: datetime) -> tuple[dict, str]:
    definition = companion['version']['definition']
    found = [(reactions.LEVELS.get(trait.get('intensity'), 1), trait['name'])
             for trait in definition.get('emotional_traits') or []
             if re.search(MINDS[cause], trait.get('name', ''), re.IGNORECASE)]
    minds, trait = max(found, default=(0, ''))
    from companion.memory import closeness
    try:
        near = closeness.state(connection, companion, now)['level']
    except Exception:  # noqa: BLE001 - a brand-new companion without history counts as just met.
        near = 1
    sheet = [group for group in ('forgiving', 'stubborn') if consequences.sheet_has(definition, group)]
    return {'level': level(connection), 'cause': cause, 'minds': minds, 'sheet': sheet, 'closeness': near}, trait


def consider(connection, companion: dict, cause: str, subject: str, about: str, now: datetime,
             outing_id: str | None = None, shown: str = '') -> dict | None:
    """Something happened that could start a rough patch: roll it once (a second call returns the first), and keep
    the row either way, so the user changing how it went on Today opens or closes it. `about` is said to the
    companion ("the user calling off ..."), `shown` to the user on the Character page ("over you calling off ...")."""
    if not ACTIVE or companion is None or not companion.get('active_timeline_id'):
        return None
    lvl = level(connection)
    if lvl == 0 or (cause == 'seeing_someone' and lvl < 2):
        return None
    found = optional(connection, 'SELECT * FROM rough_patches WHERE subject=?', (subject,))
    if found:
        return found
    size, fault = CAUSES[cause]
    consequence_id = None
    if fault == 'user':
        known, trait = facts(connection, companion, cause, now)
        known['stacked'] = stacked_on(connection, companion, {'cause': cause, 'started_at': stamp(now),
                                                              'started_on': local_day(companion, now)}, lvl)
        first = companion['version']['definition']['name'].split()[0]
        # The label is the user's to read on Today for weeks ("... over you calling off dinner on the day"), never the
        # companion's words.
        shown_about = re.sub(r' today$', ' on the day', shown.removeprefix('over '))
        names = {'name': first, 'a': 'someone', 'b': '', 'trait': trait, 'about': shown_about or about}
        table = consequences.tables()[CHOICE]
        outcome = consequences.decide(
            connection, timeline_id=companion['active_timeline_id'], choice=CHOICE, subject=f'patch:{subject}',
            facts=known, names=names, labels=[option['label'].format(**names) for option in table['options']],
            day=local_day(companion, now), timestamp=stamp(now), now=now)
        consequence_id = outcome['id']
    needs = 2 if lvl == 3 and cause in SERIOUS else 1
    row_id = identifier()
    connection.execute(
        'INSERT INTO rough_patches (id, timeline_id, companion_id, cause, subject, about, shown, fault, size, '
        'consequence_id, outing_id, needs, started_at, started_on, created_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (row_id, companion['active_timeline_id'], companion['id'], cause, subject, about[:240], (shown or about)[:240],
         fault, size,
         consequence_id, outing_id, needs, stamp(now), local_day(companion, now), stamp(now)))
    return one(connection, 'SELECT * FROM rough_patches WHERE id=?', (row_id,))


def seeing_someone(connection, companion: dict, other: str, now: datetime, subject: str | None = None) -> dict | None:
    """They found out you're seeing someone else once you two are exclusive (Next steps decides that, and calls
    this). Never on an easy life."""
    return consider(connection, companion, 'seeing_someone', subject or f"seeing:{companion['id']}:{other}",
                    f'you found out the user is seeing {other} too', now,
                    shown=f"over {first_name(companion)} finding out you're seeing {other} too")


def first_name(companion: dict) -> str:
    return companion['version']['definition']['name'].split()[0]


def seen_with_others(connection, companion: dict, now: datetime) -> None:
    """Once this pair is exclusive (companion/life/steps.py), the user's other romances (any other companion on the
    romance ladder that the user hasn't broken up with) come to their notice in the next daily pass: each one rolls
    once (`seeing_someone`)."""
    from companion.life import steps
    if level(connection) < 2 or not steps.exclusive(connection, companion, now):
        return
    for other in steps.other_romances(connection, companion, now, known_since(connection, companion, now)):
        seeing_someone(connection, companion, other['version']['name'], now,
                       subject=f"seeing:{companion['id']}:{other['id']}")


def known_since(connection, companion: dict, now: datetime) -> str:
    """When this pair became exclusive as far as the others go. A pair the app started out exclusive (an upgrade from
    before Next steps, or a companion who starts close) already lived alongside the user's other romances then, so only
    companions who came along afterwards are news; a step reached later minds everyone."""
    row = optional(connection, "SELECT created_at, how FROM relationship_steps WHERE timeline_id=? AND other='user' AND "
                   "ladder='romance' AND step='exclusive' AND undone_at IS NULL ORDER BY created_at DESC LIMIT 1",
                   (companion['active_timeline_id'],))
    if row is None:  # Not written yet: the app starts them now.
        return stamp(now)
    return row['created_at'] if row['how'] in ('start', 'history') else ''


def friction(connection, companion: dict, cause: str, subject: str, about: str, now: datetime,
             shown: str = '') -> dict | None:
    """Small everyday friction another feature noticed (a chore after moving in): gone in a day."""
    return consider(connection, companion, cause, subject, about, now, shown=shown)


def found_out(connection, secret: dict, member: str, now: datetime):
    """A companion found out a secret that was kept from them: when it's about the user, a rough patch can start."""
    if not any(subject.get('key') == 'user' for subject in secret.get('subjects') or ()):
        return
    from companion.characters import by_id
    companion = by_id(connection, pairs.companion_id(member) or '')
    if companion:
        consider(connection, companion, 'secret_kept', f"secret-kept:{secret['id']}>{member}",
                 f"the user kept something from you, and you found out ({secret['statement'].rstrip('.')})", now,
                 shown='over them finding out you kept something from them')


def told_secret(connection, companion: dict, secret: dict, listener: str, now: datetime):
    consider(connection, companion, 'secret_told', f"secret-told:{secret['id']}:{listener}>{companion['id']}",
             f"the user told {listener} something you trusted them with ({secret['statement'].rstrip('.')})", now,
             shown=f'over you telling {listener} something they trusted you with')


def called_off(connection, companion: dict, outing: dict, now: datetime):
    """The user called off an outing on its own day: a small one."""
    if outing['local_date'] == local_day(companion, now):
        from companion.life import outings
        consider(connection, companion, 'called_off', f"called-off:{outing['id']}",
                 f'the user called off {outings.what(outing)} today', now, outing_id=outing['id'],
                 shown=f'over you calling off {plan_name(outing)} today')


def quoted(sentence: str, limit: int = 60) -> str:
    """What they said, as the Character page quotes it: at most about 60 characters."""
    return sentence if len(sentence) <= limit else sentence[:limit - 1].rstrip() + '…'


# Outings named by what they are ("drinks at The Owl"); others are "the plan at ...".
PLAIN_PLANS = ('dinner', 'lunch-out', 'coffee', 'drinks', 'show', 'museum', 'walk', 'market')


def plan_name(outing: dict) -> str:
    """The plan as the user would name it: 'the visit', 'dinner at Lupa'."""
    if outing['activity'] in ('visit-in', 'visit-yours'):
        return 'the visit'
    if outing['activity'] in ('dinner-in', 'dinner-yours'):
        return 'dinner'
    if outing['activity'] in PLAIN_PLANS:
        from companion.life import outings
        return f"{outings.ACTIVITIES[outing['activity']][5]} at {outing['place']['name']}"
    return f"the plan at {outing['place']['name']}"


# Reading the user's messages -----------------------------------------------------------------------------------

def note(connection, message: dict, companion: dict, now: datetime):
    """A message from the user, before the reply is written: words that sting, a promise to keep, an apology, a
    gesture or accepting their apology, and a promise that lapsed before this message came."""
    if not ACTIVE or companion is None:
        return
    text = message['text'] or ''
    lapsed(connection, companion, now)
    if sentence := stings(text):
        sentence = sentence.rstrip('.')  # Quoted mid-sentence: 'over what you said: "go away".'
        consider(connection, companion, 'words', f"words:{message['id']}", f'the user said to you: "{sentence}"',
                 now, shown=f'over what you said: "{quoted(sentence)}"')
    promised(connection, companion, message, now)
    lvl = level(connection)
    for row in open_rows(connection, companion, lvl, now):
        if row['subject'] == f"words:{message['id']}":
            continue  # The message that started it doesn't also mend it.
        if row['fault'] == 'user':
            if says('apologies', text) and not row['apologised_at']:
                progress(connection, row, 'apologised_at', 'apology', now)
            elif says('gestures', text) and not row['gesture_at']:
                progress(connection, row, 'gesture_at', 'gesture', now)
        elif apologised(connection, row) and (says('accepting', text) or says('gestures', text)):
            mend(connection, row, 'accepted', now)


def progress(connection, row: dict, column: str, by: str, now: datetime):
    connection.execute(f'UPDATE rough_patches SET {column}=? WHERE id=?', (stamp(now), row['id']))  # noqa: S608
    fresh = one(connection, 'SELECT * FROM rough_patches WHERE id=?', (row['id'],))
    if bool(fresh['apologised_at']) + bool(fresh['gesture_at']) >= fresh['needs']:
        mend(connection, fresh, by, now)


def mend(connection, row: dict, by: str, now: datetime):
    connection.execute('UPDATE rough_patches SET mended_at=?, mended_by=? WHERE id=? AND mended_at IS NULL',
                       (stamp(now), by, row['id']))


def apologised(connection, row: dict) -> bool:
    """When they were at fault: whether they have written to the user since (the note told them to apologise)."""
    return bool(optional(connection, "SELECT id FROM messages WHERE timeline_id=? AND role='companion' "
                         "AND status='complete' AND created_at>=? LIMIT 1", (row['timeline_id'], row['started_at'])))


# Promises -----------------------------------------------------------------------------------------------------

def due_at(when: str, said: datetime, timezone) -> datetime:
    local = said.astimezone(timezone)
    end_of = lambda day, hour=23, minute=59: datetime.combine(day, time(hour, minute), timezone)  # noqa: E731
    if when == 'tomorrow':
        return end_of(local.date() + timedelta(days=1))
    if when == 'morning':
        return end_of(local.date() + timedelta(days=1 if local.hour >= 5 else 0), 13, 0)
    if when == 'tonight':
        return max(end_of(local.date()), said + timedelta(hours=3))
    return said + timedelta(hours=10 if when == 'after' else 6)


def promised(connection, companion: dict, message: dict, now: datetime):
    for found in PROMISE.finditer(plain(message['text'])):
        if NEGATED.search(plain(message['text'])[:found.start()]):
            continue
        when = next((kind for words, kind in WHEN if words in found.group('when')), None)
        if when is None:
            continue
        said = parse(message['created_at'])
        due = due_at(when, said, zone(settings(connection)['user_timezone']))
        connection.execute(
            'INSERT OR IGNORE INTO rough_patch_promises (id, timeline_id, companion_id, message_id, what, due_at, '
            'created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (identifier(), companion['active_timeline_id'], companion['id'], message['id'], found.group(0)[:120],
             stamp(due), message['created_at']))
        return


def kept(connection, promise: dict) -> bool:
    """A word from the user after a real gap and by the time they said, or a call they started."""
    after = stamp(parse(promise['created_at']) + KEEP_GAP)
    if optional(connection, "SELECT id FROM messages WHERE timeline_id=? AND role='user' AND status='complete' "
                'AND created_at>=? AND created_at<=? LIMIT 1', (promise['timeline_id'], after, promise['due_at'])):
        return True
    return bool(optional(connection, "SELECT id FROM calls WHERE timeline_id=? AND direction='you' AND started_at>=? "
                         'AND started_at<=? LIMIT 1', (promise['timeline_id'], promise['created_at'], promise['due_at'])))


def lapsed(connection, companion: dict, now: datetime):
    """Promises whose time has passed: kept ones are closed, broken ones can start a rough patch."""
    for promise in many(connection, 'SELECT * FROM rough_patch_promises WHERE timeline_id=? AND settled_at IS NULL '
                        'AND due_at<?', (companion['active_timeline_id'], stamp(now))):
        good = kept(connection, promise)
        connection.execute('UPDATE rough_patch_promises SET settled_at=?, kept=? WHERE id=?',
                           (stamp(now), int(good), promise['id']))
        if not good:
            what = re.sub(r"^(?:i'?ll|i will|i promise(?: i'?ll| to| i will)?|i'?m (?:going to|gonna))\s+", '',
                          promise['what']).strip()
            consider(connection, companion, 'promise', f"promise:{promise['id']}",
                     f"the user said they'd {what} and didn't", now,
                     shown=f"over you saying you'd {re.sub(r'\byou\b', 'them', what)} and not doing it")


# Every so often ---------------------------------------------------------------------------------------------

def daily(connection, companion: dict, now: datetime):
    """From the agenda's regular pass: lapsed promises, a stand-up, make-up gestures from outings that happened, and
    rough patches that faded, written down."""
    if not ACTIVE:
        return
    lapsed(connection, companion, now)
    stand_ups(connection, companion, now)
    seen_with_others(connection, companion, now)
    lvl = level(connection)
    for row in rows(connection, companion):
        if not still_open(connection, row, lvl, now, companion, picked=True):
            mend(connection, row, 'calm', now)  # Faded by time, so changing it on Today no longer opens it.
        elif not picked_open(connection, row):
            continue  # Let go for now, but Today can still make it start.
        elif showed_up(connection, row, now) and not warned(connection, companion):
            if row['fault'] == 'companion':
                mend(connection, row, 'gesture', now)
            elif not row['gesture_at']:
                progress(connection, row, 'gesture_at', 'gesture', now)


def warned(connection, companion: dict) -> bool:
    """Strained or thinking about a break (companion/life/breakups.py): an outing together no longer mends it by itself
    then; an apology or a gesture still does."""
    from companion.life import breakups  # Imported here: breakups reads this module.
    return breakups.holds(connection, companion) == 'cool'


def showed_up(connection, row: dict, now: datetime) -> bool:
    """An outing or visit with the user that got under way after it started: a kept plan, showing up."""
    from companion.life import outings
    timezone = one(connection, 'SELECT timezone FROM character_versions WHERE id=(SELECT active_version_id FROM '
                   'companions WHERE id=?)', (row['companion_id'],))['timezone']
    for outing in outings.in_force(connection, row['timeline_id'], row['started_on']):
        start = outings.window(outing, timezone)[0]
        if parse(row['started_at']) < start <= now and outing['id'] != row['outing_id']:
            return True
    return False


def stand_ups(connection, companion: dict, now: datetime):
    """On real life and drama, now and then they call off an outing with the user on the day, a few hours before,
    and then apologise first. Seeded per outing; never a visit already under way or one the user set up as a knock."""
    lvl = level(connection)
    if lvl < 2:
        return
    from companion.life import outings
    tz = companion['version']['timezone']
    for outing in outings.in_force(connection, companion['active_timeline_id'], local_day(companion, now)):
        if outing['status'] != 'planned' or outing['place'].get('knock') or outing['ended_at']:
            continue
        start = outings.window(outing, tz)[0]
        if not start - STAND_UP_BEFORE <= now < start:
            continue
        subject = f"stood-up:{outing['id']}"
        if optional(connection, 'SELECT id FROM rough_patches WHERE subject=?', (subject,)):
            continue
        dice = random.Random(f"stand-up:{outing['id']}")
        if dice.random() >= STAND_UP[lvl]:
            continue
        reason = dice.choice(reasons(connection, companion))
        connection.execute("UPDATE outings SET status='cancelled', cancelled_at=? WHERE id=?", (stamp(now), outing['id']))
        consider(connection, companion, 'stood_up', subject, f'{outings.what(outing)} ({reason})', now,
                 outing_id=outing['id'], shown=f'they called off {plan_name(outing)} at the last minute')


# Reasons that only fit some eras (data/rough_patches/stand_up_reasons.json `needs`), by the home city's era.
ERA_NEEDS = {'jazz-age': {'motor', 'rail'}, 'victorian': {'rail'}, 'frontier': {'rail'}, 'steampunk': {'rail'},
             'medieval': set(), 'fantasy': set()}


def reasons(connection, companion: dict) -> list[str]:
    """Why they might call off a plan, fitting their city's era: no car trouble in Camelot."""
    from companion.world import newcomers
    era = newcomers.city_for(connection, companion['version']['definition']).get('era', 'modern')
    if era not in ERA_NEEDS:
        return bank('stand_up_reasons')
    needs = json.loads((catalog.DATA / 'rough_patches' / 'stand_up_reasons.json').read_text(encoding='utf-8'))['needs']
    unfit = {reason for tag, found in needs.items() if tag not in ERA_NEEDS[era] for reason in found}
    return [reason for reason in bank('stand_up_reasons') if reason not in unfit]


# Asked to get together while things are tense ---------------------------------------------------------------------

ASK_CHOICE = 'user:ask_while_tense'
NOT_NOW = 1  # The option in the odds table where they would rather not, for now.


def tension(connection, companion: dict, now: datetime) -> dict | None:
    """What makes things tense now, for the engine: `patch` (a big rough patch of the user's making is open) and
    `warning` (Breaks and breakups: 1 strained, 2 thinking about a break). None when nothing does."""
    row = current(connection, companion, now)
    patch = int(bool(row) and row['size'] == 'big' and row['fault'] == 'user')
    from companion.life import breakups  # Imported here: breakups reads this module.
    warning = {'strained': 1, 'thinking': 2}.get(breakups.current(connection, companion)[1], 0)
    return {'patch': patch, 'warning': warning} if patch or warning else None


def turned_down(connection, companion: dict, message: dict, kind: str, now: datetime) -> bool:
    """The user asks to get together (going out, or a visit) while things are tense: the engine decides whether they
    would rather not, for now. Then nothing is booked, and the reply says so (a visit turned down,
    companion/life/together.py). True when they turned it down."""
    if not ACTIVE or message['role'] != 'user' or not companion.get('active_timeline_id'):
        return False
    if optional(connection, 'SELECT id FROM together_asks WHERE message_id=?', (message['id'],)):
        return True
    found = tension(connection, companion, now)
    if found is None:
        return False
    definition = companion['version']['definition']
    names = {'name': first_name(companion), 'a': 'someone', 'b': ''}
    table = consequences.tables()[ASK_CHOICE]
    outcome = consequences.decide(
        connection, timeline_id=companion['active_timeline_id'], choice=ASK_CHOICE, subject=f"tense-ask:{message['id']}",
        facts={**found, 'level': level(connection),
               'sheet': [group for group in ('forgiving', 'stubborn') if consequences.sheet_has(definition, group)]},
        names=names, labels=[option['label'].format(**names) for option in table['options']],
        day=local_day(companion, now), timestamp=stamp(now), now=now)
    if outcome['picked'] != NOT_NOW:
        return False
    from companion.life import together
    return together.record(connection, companion, message, kind, {'why': 'tense'}, stamp(now))


def change_ask(connection, companion: dict, consequence_id: str, option: int, now: datetime) -> dict:
    """The user makes their answer go another way on Today: a yes books what was asked, as if they had said yes then;
    turned down calls off what it booked."""
    outcome = consequences.change(connection, consequence_id, option, stamp(now))
    require(outcome['timeline_id'] == companion['active_timeline_id'], 'That outcome is not on this timeline.', 404)
    message_id = outcome['subject'].split(':', 1)[1]
    if option == NOT_NOW:
        turn_down(connection, companion, message_id, now)
    else:
        connection.execute('DELETE FROM together_asks WHERE message_id=?', (message_id,))
        message = optional(connection, 'SELECT * FROM messages WHERE id=?', (message_id,))
        if message:
            from companion.life import outings
            outings.note(connection, message, companion, stamp(now))
    return consequences.by_id(connection, consequence_id)


def turn_down(connection, companion: dict, message_id: str, now: datetime) -> None:
    """Made to go "would rather not" on Today: what it booked is called off, and another reply to that message is told
    so (the together_asks row a roll that came out that way leaves)."""
    from companion.life import together
    booked = optional(connection, "SELECT activity FROM outings WHERE message_id=? AND status='planned'", (message_id,))
    connection.execute("UPDATE outings SET status='cancelled', cancelled_at=? WHERE message_id=? AND "
                       "status='planned'", (stamp(now), message_id))
    message = optional(connection, 'SELECT * FROM messages WHERE id=?', (message_id,))
    if message and not optional(connection, 'SELECT id FROM together_asks WHERE message_id=?', (message_id,)):
        kind = booked['activity'] if booked and booked['activity'] in together.TENSE_ASKED else 'out'
        together.record(connection, companion, message, kind, {'why': 'tense'}, stamp(now))


# What is open --------------------------------------------------------------------------------------------------

def rows(connection, companion: dict) -> list[dict]:
    return many(connection, 'SELECT * FROM rough_patches WHERE timeline_id=? AND mended_at IS NULL '
                'ORDER BY started_at', (companion['active_timeline_id'],))


def picked_open(connection, row: dict) -> bool:
    if not row['consequence_id']:
        return True
    found = optional(connection, 'SELECT picked FROM consequences WHERE id=?', (row['consequence_id'],))
    return bool(found) and found['picked'] == OPENS


def still_open(connection, row: dict, lvl: int, now: datetime, companion: dict, picked: bool = False) -> bool:
    """Not mended, picked to start (or taken as `picked`), not taken back, and not faded by time."""
    if row['mended_at'] or lvl == 0 or not (picked or picked_open(connection, row)):
        return False
    if row['cause'] in ('stood_up', 'called_off') and row['outing_id']:
        outing = optional(connection, 'SELECT status FROM outings WHERE id=?', (row['outing_id'],))
        if not outing or outing['status'] != 'cancelled':
            return False  # The plan is back on (Undo on Today).
    started = parse(row['started_at'])
    if row['size'] == 'small':
        return now - started < SMALL_FOR
    if lvl == 1:
        return local_day(companion, now) == row['started_on']
    calm = CALM[lvl][0 if row['fault'] == 'user' else 1]
    return now - started < calm


def was_open(row: dict, lvl: int, when: datetime, companion: dict) -> bool:
    """Whether a rough patch picked to start was still open at that moment, going by its own dates: not mended yet and
    not faded by time (`still_open` asks the same of now, with the outing it may be about)."""
    started = parse(row['started_at'])
    if started > when or (row['mended_at'] and parse(row['mended_at']) <= when) or lvl == 0:
        return False
    if row['size'] == 'small':
        return when - started < SMALL_FOR
    if lvl == 1:
        return local_day(companion, when) == row['started_on']
    return when - started < CALM[lvl][0 if row['fault'] == 'user' else 1]


def stacks(earlier: dict, row: dict, lvl: int, companion: dict) -> bool:
    """Whether `row` stacks on `earlier`: the same cause, from before it, and the same day or still open then."""
    return earlier['cause'] == row['cause'] and earlier['started_at'] < row['started_at'] and (
        earlier['started_on'] == row['started_on'] or was_open(earlier, lvl, parse(row['started_at']), companion))


def stacked_on(connection, companion: dict, row: dict, lvl: int) -> int:
    """How many rough patches of the user's making over the same thing this one stacks on."""
    since = stamp(parse(row['started_at']) - max(CALM[3][0], SMALL_FOR) - timedelta(days=1))
    earlier = [found for found in many(connection, "SELECT * FROM rough_patches WHERE timeline_id=? AND fault='user' "
                                       'AND cause=? AND started_at>=? AND started_at<?',
                                       (companion['active_timeline_id'], row['cause'], since, row['started_at']))
               if picked_open(connection, found)]
    return sum(stacks(found, row, lvl, companion) for found in earlier)


def weighed(connection, companion: dict, found: list[dict]) -> list[tuple[dict, float]]:
    """Rough patches with what each counts for (1, a half, a quarter...): one over the same thing as an earlier one in
    the list that was open then, or started the same day, counts less."""
    lvl = level(connection)
    return [(row, STACK_WEIGHT ** sum(stacks(earlier, row, lvl, companion) for earlier in found)) for row in found]


def open_rows(connection, companion: dict, lvl: int, now: datetime) -> list[dict]:
    return [row for row in rows(connection, companion) if still_open(connection, row, lvl, now, companion)]


def current(connection, companion: dict, now: datetime) -> dict | None:
    """The rough patch that colors things now: a big one before a small one, theirs to apologise for before yours,
    the newest first."""
    if not ACTIVE or companion is None:
        return None
    found = open_rows(connection, companion, level(connection), now)
    order = {('big', 'companion'): 0, ('big', 'user'): 1, ('small', 'user'): 2}
    return min(found, key=lambda row: (order.get((row['size'], row['fault']), 3), -parse(row['started_at']).timestamp()),
               default=None)


def cool(connection, companion: dict, now: datetime) -> bool:
    """Whether they hold back on reaching out (check-ins, invitations, knocks, calls): a big one of yours is open, or
    you found out they were seeing someone behind your back (they give you room; their apology still goes)."""
    row = current(connection, companion, now)
    return bool(row) and row['size'] == 'big' and (row['fault'] == 'user' or row['cause'] == 'hidden_partner')


# The chat notes ------------------------------------------------------------------------------------------------

LINES = {
    'open': ('- Things are tense between you and the user right now. What happened: {about}. You are still hurt by it. '
             'Be cooler than usual: shorter replies, fewer jokes, and no plans or invitations of your own. Do not '
             'pretend everything is fine, and do not lecture or keep bringing it up either. If they apologise or make '
             'it up to you, you can soften.'),
    'halfway': ('- Things have been tense between you and the user. What happened: {about}. They have {done}. It '
                'helps, but you are not over it yet: take it in, and stay a little guarded until they {missing}.'),
    'small': ('- A small thing is bugging you a little today: {about}. Let it show a bit (a little shorter, a little '
              'cooler), and let it go by tomorrow.'),
    'theirs': ('- You let the user down: {what}. You feel bad about it. Apologise first, in your own '
               'words, before anything else, and mean it; say what happened without piling on excuses.'),
    'theirs_said': ('- You let the user down recently ({what}) and you have apologised. Do not bring it '
                    'up again unless they do; be a little extra warm.'),
    # Owning up to seeing someone behind their back is not a cancelled plan: no "extra warm" (E2E v0.13 W12).
    'theirs_owned': ('- You let the user down recently ({what}), and you have owned up and apologised. Do not bring it '
                     'up again unless they do; give them room, and do not act as if nothing happened.'),
    'mended': ('- Things were tense between you and the user (what happened: {about}). They just {how}, and that is '
               'enough for you: accept it in your own words and let things be warm between you again.'),
    'forgiven': '- The user forgave you for {deed}. Things are good between you again.',
    # After calling off a plan: what kept them still happened today, so the free evening is no nice surprise (E2E R1).
    'forgiven_reason': ('- The user forgave you for calling off {plan} at the last minute. Things are good between you '
                        'again. What kept you ({reason}) is still part of your day, so do not talk about the evening as '
                        'if it opened up or was a nice surprise.'),
}
def deed(row: dict) -> tuple[str, str]:
    """What they did, said two ways (THEIR_DEED), for a rough patch of their making."""
    what, doing = THEIR_DEED.get(row['cause'], THEIR_DEED['stood_up'])
    return what.format(about=row['about']), doing.format(about=row['about'])


def forgiven_line(row: dict) -> str:
    """The user forgave them; for calling off a plan, with the reason they gave, which still stands."""
    plan, _sep, reason = row['about'].rpartition(' (')
    if row['cause'] != 'stood_up' or not plan:
        return LINES['forgiven'].format(deed=deed(row)[1])
    return LINES['forgiven_reason'].format(plan=plan, reason=reason.removesuffix(')'))


MENDED_HOW = {'apology': 'apologised', 'gesture': 'made it up to you', 'you': 'cleared the air'}


def context_lines(connection, companion: dict, now: datetime) -> list[tuple[str, str]]:
    """(identity, line) for the 'patch' section: at most one line."""
    if not ACTIVE:
        return []
    row = current(connection, companion, now)
    if row is None:
        made = optional(connection, "SELECT * FROM rough_patches WHERE timeline_id=? AND mended_at>? AND mended_by!='calm' "
                        'ORDER BY mended_at DESC LIMIT 1', (companion['active_timeline_id'], stamp(now - MADE_UP_FOR)))
        if made is None or made['size'] == 'small' or not picked_open(connection, made):
            return []
        if made['fault'] == 'companion':
            return [(f"patch:{made['id']}:forgiven", forgiven_line(made))]
        return [(f"patch:{made['id']}:mended", LINES['mended'].format(
            how=MENDED_HOW.get(made['mended_by'], 'made up with you'), about=made['about']))]
    if row['fault'] == 'companion':
        key = ('theirs_owned' if row['cause'] == 'hidden_partner' else 'theirs_said') if apologised(connection, row) \
            else 'theirs'
        return [(f"patch:{row['id']}:{key}", LINES[key].format(what=deed(row)[0]))]
    if row['size'] == 'small':
        return [(f"patch:{row['id']}:small", LINES['small'].format(about=row['about']))]
    if row['apologised_at'] or row['gesture_at']:
        done, missing = (('apologised', 'show it, not just say it') if row['apologised_at']
                         else ('done something to make it up to you', 'say sorry'))
        return [(f"patch:{row['id']}:halfway", LINES['halfway'].format(done=done, about=row['about'],
                                                                       missing=missing))]
    return [(f"patch:{row['id']}:open", LINES['open'].format(about=row['about']))]


# The apology first text ------------------------------------------------------------------------------------------

def apology_due(connection, companion: dict, now: datetime) -> list:
    """They called off a plan with the user, or were found seeing someone behind their back: they text first to apologise (a first text, companion/life/openers.py)."""
    if not ACTIVE or not FIRST_TEXTS:
        return []
    from companion.life.openers import Trigger
    row = current(connection, companion, now)
    if row is None or row['fault'] != 'companion' or apologised(connection, row):
        return []
    seed = random.Random(f"apology:{row['id']}")
    if row['cause'] == 'hidden_partner':
        return [Trigger(f"patch:{row['id']}", 'apology',
                        f"You let the user down: {row['about']}. You have ended it, and you feel terrible. Apologise "
                        'to the user in your own words and mean it, without excuses; give them room.',
                        seed.choice(bank('companion_confessions')))]
    # The written-out text, used when the model's can't be: the plan as the user names it ("the visit", not "a visit
    # to the user's place"), and the reason in the last brackets (a place can have its own: "Tengu (kushikatsu ...)").
    from companion.life import outings
    found = optional(connection, 'SELECT id FROM outings WHERE id=?', (row['outing_id'] or '',))
    plan = plan_name(outings.get(connection, found['id'])) if found else 'our plans'
    reason = row['about'].rpartition(' (')[2].removesuffix(')')
    template = seed.choice(bank('companion_apologies'))
    return [Trigger(f"patch:{row['id']}", 'apology',
                    f'You called off {row["about"]} at the last minute, and you feel bad. Apologise to the user in your '
                    'own words, say briefly what happened, and offer to make it up to them if it fits.',
                    template.format(plan=plan, reason=reason))]


# Showing it -----------------------------------------------------------------------------------------------------

def view(connection, companion: dict, now: datetime) -> dict:
    """{open, text, since, about, mendable, id} for the Character page. What it is about shows with moods shown."""
    row = current(connection, companion, now)
    if row is None or row['size'] == 'small' and not settings(connection)['show_moods']:
        return {'open': False, 'id': None, 'text': '', 'since': None, 'about': None, 'small': False}
    about = row['shown'] if settings(connection)['show_moods'] else None
    return {'open': True, 'id': row['id'], 'small': row['size'] == 'small',
            'text': 'A little friction today' if row['size'] == 'small' else 'Things are a bit tense',
            'since': row['started_on'], 'about': about}


def let_go(database, patch_id: str) -> dict:
    """The user clears the air: this rough patch ends now, and any other one open with them, so the page doesn't
    turn to the next one."""
    from companion.characters import require_current
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        row = optional(connection, 'SELECT * FROM rough_patches WHERE id=? AND timeline_id=?',
                       (patch_id, companion['active_timeline_id']))
        require(row is not None, 'That rough patch is not on this timeline.', 404)
        now = database.clock.now()
        for found in [row, *open_rows(connection, companion, level(connection), now)]:
            mend(connection, found, 'you', now)
        return view(connection, companion, now)


def undo_let_go(database, patch_id: str) -> dict:
    """Take back Let it go: the rough patches it ended are open again as they were."""
    from companion.characters import require_current
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        row = optional(connection, "SELECT mended_at FROM rough_patches WHERE id=? AND timeline_id=? AND mended_by='you'",
                       (patch_id, companion['active_timeline_id']))
        require(row is not None, 'That can no longer be undone.', 409)
        connection.execute("UPDATE rough_patches SET mended_at=NULL, mended_by=NULL WHERE timeline_id=? AND "
                           "mended_by='you' AND mended_at=?", (companion['active_timeline_id'], row['mended_at']))
        return view(connection, companion, database.clock.now())


def read(database) -> dict:
    from companion.characters import require_current
    with database.connect() as connection:
        return view(connection, require_current(connection), database.clock.now())

