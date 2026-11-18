"""A work project the companion says is done is done (tester, 1.4.1).

Work life (companion/life/work.py) runs one project for three to eight weeks, and every work slot, late night and the
chat's Job section names it until its due date. When the companion said in chat "the guild register's finally done",
nothing changed: the next day the notes still said "At work you are in the middle of the guild register", and so did
the companion. Now, after each completed companion message, a rule pass reads it for the running project said to be
finished: a word of its title ("register" for "the guild register of new apprentices") in the same sentence as a done
word ("done", "finished", "wrapped up", "handed in"), with no hedge ("almost done", "done for the day", "won't be
done till Friday", a question). A match ends the project on the day it was said, with how it went, and the next one
starts the day after; upcoming days that named the old project are composed again.

The companion's words stick only while the message does: another version chosen, or the message deleted, brings the
project back (`sweep`). A project the user wrote or gave a due date stays: what the user set wins over chat. Rules
only, no model, nothing the user has to approve.
"""
import re
from datetime import date, datetime, timedelta

from companion.clock import parse, stamp, zone
from companion.database import decode, many, optional
from companion.life import work
from companion.memory.extraction import HYPOTHETICAL, QUOTED, SENTENCE

SOURCE = 'said:'
# Title words that say nothing about which project it is.
GENERIC = frozenset({
    'the', 'a', 'an', 'of', 'for', 'and', 'to', 'in', 'on', 'at', 'with', 'from', 'by', 'new', 'next', 'big', 'old',
    'work', 'job', 'project', 'thing', 'stuff', 'this', 'that', 'year', 'week', 'month', 'day', 'season', 'final',
    'first', 'last', 'annual', 'yearly', 'monthly', 'weekly', 'quarterly', 'local', 'town', 'city', 'office', 'shop',
    'getting', 'making', 'doing', 'running', 'setting', 'putting', 'their', 'your', 'our', 'his', 'her', 'my', 'some',
    'major', 'small', 'full', 'whole', 'over', 'into', 'about', 'up', 'out', 'off'})
DONE = re.compile(
    r"\b(?:(?:all |finally |completely |totally |officially |properly )?(?:done|finished|complete|completed|sorted|"
    r"wrapped(?: up)?|handed in|turned in|submitted|filed|delivered|shipped|signed off|closed out|put to bed|"
    r"over and done|dealt with|in the bag|behind me|off my (?:desk|plate|hands)|out the door|out of my hands|"
    r"finally over|is over|nailed|knocked out|taken care of|wrapped|squared away|locked in|sent off|went out))\b",
    re.IGNORECASE)
# Not done yet, done only for now, or not about now: nothing changes.
HEDGE = re.compile(
    r"\b(?:not|never|almost|nearly|mostly|half|partly|part of|until|till|til|once|when|if|will|won't|gonna|going to|"
    r"should|could|would|might|may|hope|hopefully|by (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"tomorrow|tonight|next)|tomorrow|soon|yet|still|for the day|for today|for tonight|for now|for the night|"
    r"for the week|for the moment|this round|first round|first part|first half|draft|wish|can't wait|need to|"
    r"have to|got to|gotta|trying to|try to|want to|wanna|years ago|last year|nowhere near|far from|ever)\b|n't\b",
    re.IGNORECASE)
WORD = re.compile(r"[a-z]+", re.IGNORECASE)
# Where a title's head noun ends: "the guild register | of new apprentices".
AFTER_HEAD = frozenset({'of', 'for', 'to', 'at', 'on', 'with', 'from', 'in', 'before', 'after', 'about', 'by'})
# Parts of a sentence: "finished my coffee, then back to the register" says nothing about the register.
CLAUSE = re.compile(r",|\s[-–—]\s|\b(?:then|but|and then|so|because|while|after|before)\b", re.IGNORECASE)


def stem(word: str) -> str:
    word = word.lower()
    return word[:-1] if len(word) > 4 and word.endswith('s') and not word.endswith('ss') else word


def keys(title: str) -> set[str]:
    """The words of a project's title that name it: "register", "guild", "apprentice"."""
    return {stem(word) for word in WORD.findall(title) if len(word) >= 4 and word.lower() not in GENERIC}


def head(title: str) -> str | None:
    """The word a title is about: "register" in "the guild register of new apprentices"."""
    words = WORD.findall(title)
    cut = next((index for index, word in enumerate(words) if word.lower() in AFTER_HEAD), len(words))
    named = [word for word in words[:cut] if len(word) >= 4 and word.lower() not in GENERIC]
    return stem(named[-1]) if named else None


def about(clause: str, wanted: set[str], main: str | None) -> bool:
    """A clause names the project: its head word, or two words of its title."""
    words = {stem(word) for word in WORD.findall(clause.replace("'s", ''))}
    return main in words or len(words & wanted) >= 2


def said_done(text: str, title: str) -> str | None:
    """The sentence of a message that says the project is finished, or None."""
    wanted, main = keys(title), head(title)
    if not wanted or HYPOTHETICAL.search(text):
        return None
    for sentence in SENTENCE.findall(QUOTED.sub(' ', text.replace('’', "'"))):
        sentence = sentence.strip()
        if not sentence or sentence.endswith('?') or HEDGE.search(sentence):
            continue
        if any(about(clause, wanted, main) and DONE.search(clause) for clause in CLAUSE.split(sentence)):
            return sentence
    return None


def standing(connection, timeline_id: str, message_id: str) -> bool:
    return optional(connection, "SELECT 1 FROM messages WHERE (id=? OR origin_id=?) AND timeline_id=? AND active=1 "
                    "AND status='complete' AND redacted_at IS NULL LIMIT 1",
                    (message_id, message_id, timeline_id)) is not None


def notice(connection, companion: dict, message: dict, now: datetime) -> bool:
    """Read one completed companion message for the running project said to be done, and end it. Before that, a
    project ended by a message no longer on the timeline comes back."""
    if not work.ACTIVE:
        return False
    timeline_id = companion['active_timeline_id']
    sweep(connection, companion, now)
    if message['role'] != 'companion' or message['status'] != 'complete' or message['timeline_id'] != timeline_id:
        return False
    found = work.state(connection, timeline_id)
    if not found or found['status'] != 'working' or not work.level(connection):
        return False
    project = found['project']
    if project.get('own') or project.get('own_due'):
        return False
    for said in [*([] if project.get('read_back') else earlier(connection, timeline_id, project, message)), message]:
        day = local_day(companion, said)
        if day.isoformat() >= project['started'] and said_done(said['text'], project['title']):
            finish(connection, companion, found, day, said['id'], now)
            return True
    if not project.get('read_back'):
        work.update(connection, timeline_id, now, project={**project, 'read_back': True})
    return False


def local_day(companion: dict, message: dict) -> date:
    return parse(message['created_at']).astimezone(zone(companion['version']['timezone'])).date()


def earlier(connection, timeline_id: str, project: dict, message: dict) -> list[dict]:
    """The companion's replies on the timeline since the running project started, read once per project: a world
    from before 1.4.2 whose companion already said it was done heals with its next reply."""
    return many(connection, "SELECT id, text, created_at FROM messages WHERE timeline_id=? AND role='companion' AND "
                "status='complete' AND active=1 AND redacted_at IS NULL AND id!=? AND created_at>=? ORDER BY seq",
                (timeline_id, message['id'], project['started']))


def finish(connection, companion: dict, found: dict, day: date, message_id: str, now: datetime) -> None:
    """End the running project on the day it was said, as work.finish_project does on its due date, and start the
    next one the day after. The new project remembers the old, for `sweep`."""
    timeline_id, project = companion['active_timeline_id'], found['project']
    seed = f'work:{timeline_id}:{found["career"]}'
    well, fine = work.OUTCOMES[work.level(connection)]
    roll = work.generators.unit(seed, 'outcome', project['index'])
    outcome = 'well' if roll < well else 'fine' if roll < well + fine else 'rough'
    work.record(connection, timeline_id, f'{SOURCE}{message_id}', 'project', day,
                f"wrapped up {project['title']}; {work.OUTCOME_WORDS[outcome]}", found['pay'], 0, now)
    following = work.next_project(connection, companion, {**found, 'project': {**project,
                                                                               'due': (day - timedelta(days=1)).isoformat()}})
    following = {**following, 'said': message_id, 'before': project, 'read_back': True}
    work.update(connection, timeline_id, now, project=following,
                used=[*work.used_titles(found), following['title']][-12:])
    redraw(connection, timeline_id, project['title'], now)


def sweep(connection, companion: dict, now: datetime) -> bool:
    """The project the companion said was done comes back when that message left the timeline (another version
    chosen, deleted, redacted), unless the user has set a project since."""
    timeline_id = companion['active_timeline_id']
    found = work.state(connection, timeline_id)
    if not found or found['status'] != 'working':
        return False
    project = found['project']
    said = project.get('said')
    if not said or project.get('own') or project.get('own_due') or standing(connection, timeline_id, said):
        return False
    connection.execute('DELETE FROM work_events WHERE timeline_id=? AND key=?', (timeline_id, f'{SOURCE}{said}'))
    work.update(connection, timeline_id, now, project=project['before'],
                used=[title for title in work.used_titles(found) if title != project['title']])
    redraw(connection, timeline_id, project['title'], now)
    return True


def redraw(connection, timeline_id: str, title: str, now: datetime) -> int:
    """Remove the companion's upcoming agenda entries that name a project no longer running, so they are composed
    again with the one that is."""
    removed = 0
    for row in many(connection, "SELECT id, entry FROM life_agenda WHERE timeline_id=? AND subject='companion' AND "
                    "status='upcoming' AND starts_at>? AND entry IS NOT NULL", (timeline_id, stamp(now))):
        if title in (decode(row['entry']) or {}).get('summary', ''):
            connection.execute('DELETE FROM life_agenda WHERE id=?', (row['id'],))
            removed += 1
    return removed
