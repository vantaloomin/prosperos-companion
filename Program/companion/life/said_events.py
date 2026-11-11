"""What a companion says about their people sticks (Hit List #103).

When a companion says in chat "my mom just retired", their mom's record, her diary and Their people agree from then
on. After each completed companion message (self_facts.note), a rule pass reads it for plain news about one person in
the circle, named by name ("Mara") or by a relation only one person fits ("my mom" with one mother in the circle),
in one of five kinds: work (promoted, a new job, laid off, retired, quit), love (seeing someone, engaged, married,
broke up), a move (in town, away, back), health (in hospital, surgery, hurt, ill, a diagnosis, better) and a baby
(expecting, born). The phrases are a bank of at least 100 per kind (world/data/said_changes.json).

A match goes through happenings.record with source `said:<self fact id>`: a line in their diary on the day it was
said, the change on their record, and the same undo as a storyline event. The self fact (category 'news') is what the
user sees in Character Studio; removing it, or Undo on the diary line, takes the change back, and so does the message
leaving the timeline (another version, or deleted).

A wrong record is worse than a missed one, so anything unclear changes nothing: two possible people, a hedge
("might", "thinking about"), a question, a joke, something long past ("retired years ago"), a negation. What the user
set wins over chat, and so does any storyline or event about the same part of their life from the last 60 days.
Rules only, no model, and nothing the user has to approve.
"""
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import cache

from companion.clock import parse, stamp, zone
from companion.database import decode, identifier, many, optional
from companion.life import casting, circle, circle_love, happenings, health_stays
from companion.memory.extraction import HYPOTHETICAL, QUESTION_START, QUOTED, SENTENCE
from companion.world import catalog

SOURCE = 'said:'
CATEGORY = 'news'
RECENT_DAYS = 60
# Nobody retires younger than this, whatever was said: news that far from the record does not stick (Iris, #103).
RETIRE_AGE = 50
# A baby born this recently is the one they had: no second baby from the same news.
BABY_DAYS = 300
# The part of someone's life each kind of event changes: news never overrides a recent event about the same part.
AREAS = {
    'job': {'promoted', 'new_job', 'left_job', 'moved_on', 'laid_off', 'retired', 'quit', 'job_offer', 'stayed_put',
            'gave_notice', 'big_order'},
    'partner': {'broke_up', 'together', 'apart', 'picked', 'engaged', 'married', 'separated', 'widowed',
                'doing_better', 'dating_companion'},
    'moved': {'moved', 'moved_to', 'moved_away', 'moved_away_to', 'moved_back'},
    'health': {'health_scare', 'results_fine', 'treatment', 'in_hospital', 'surgery', 'hurt', 'ill', 'diagnosed',
               'recovered'},
    'baby': {'expecting', 'had_baby'},
}
AREA_OF = {kind: area for area, kinds in AREAS.items() for kind in kinds}
# Pregnancy storylines (companion/life/families.py) are about a baby.
BABY_STORIES = {'expecting', 'adopting', 'baby_update', 'babysat', 'first_birthday'}

# Words that may come between the person and the news: "my mom just retired", "my sister's finally engaged".
FILLER = (r"(?:just|finally|actually|officially|recently|also|now|totally|literally|really|seriously|already|both|has|"
          r"have|went and|gone and)")
# In lowercase text a partner's name after "and" ("kaito and liss had their baby") is any word but a common one.
LOWER_NAME = r"[a-z][a-z'’-]+"
# Where someone is from or at, between them and the news: "darius from the yard just got engaged".
FROM = r"(?:\s+(?:from|at|over at|down at)\s+(?:the |my |our |her |his |their )?[\w'’-]+(?: [\w'’-]+)?)?"
# "$" at the end of a phrase: nothing may follow but the end of the sentence or when ("kaito finally moved.").
END = r"(?=\s*(?:[.!,;:)]|$|today|yesterday|this \w+|last \w+|lol|haha))"
NAME = r"(?-i:[A-Z][a-z][\w'’-]*(?: [A-Z][a-z][\w'’-]*)?)"
PLACE = r"(?-i:[A-Z][\w.'’-]*(?: (?:of |on |upon |de |la )?[A-Z][\w.'’-]*){0,3})"
# A word right after the news that turns it into something else: "got a job interview", "is sick of it".
NOT_AFTER = re.compile(r"^[\s,]*(?:done|interviews?|offers?|application|listing|posting|fair|ad|of|about|tired|"
                       r"the|a|an)\b", re.IGNORECASE)
HEDGE = re.compile(
    r"\b(?:maybe|might|perhaps|probably|possibly|thinking (?:about|of)|considering|plann?ing to|plans? to|wants? to|"
    r"wanted to|hoping|hopes? to|about to|trying to|tried to|supposed to|could|would|should|(?-i:may)|i think|i guess|"
    r"i bet|i hope|i doubt|apparently|supposedly|allegedly|rumou?r\w*|someday|one day|almost|nearly|wish\w*|if only|"
    r"if|unless|whether|pretty much|metaphorically|figuratively|sort of|kind of|kinda|sorta|technically|"
    r"pretend\w*)\b", re.IGNORECASE)
# A joke, a game of pretend or a memory anywhere in the message makes all of it unsure: "darius finally got fired.
# just remembering when he did it for real five years ago".
NOT_NEWS = re.compile(r"\b(?:jk|j/k|kidding|joking|joke|imagine|dream\w*|remember\w*|reminds? me|throwback|"
                      r"anniversary|basically|practically|might as well|as good as|in spirit)\b", re.IGNORECASE)
LONG_AGO = re.compile(
    r"\b(?:years? ago|decades? ago|months ago|a while ago|a while back|long ago|long time ago|back in|back when|"
    r"back then|used to|when i was|when we were|as a kid|growing up|in (?:19|20)\d\d|last year|for years|for decades|"
    r"for ages|for a long time|ever since|since forever|since i was|before i was born|once upon|in high school|"
    r"in college|in the past|again and again|every time|always)\b", re.IGNORECASE)
NEGATION = re.compile(r"\b(?:not|never|no longer|no|nobody|neither|nor)\b|n['’]t\b", re.IGNORECASE)
ACTIONS = re.compile(r'\*[^*\n]+\*')

# A relation word after "my", and the circle roles it can be: exact roles, or a general role with these pronouns.
RELATIONS = {
    'mom': ({'mom', 'mother', 'mum', 'mama'}, 'parent', 'she'), 'dad': ({'dad', 'father', 'papa'}, 'parent', 'he'),
    'sister': ({'sister'}, 'sibling', 'she'), 'brother': ({'brother'}, 'sibling', 'he'),
    'grandma': ({'grandma', 'grandmother'}, 'grandparent', 'she'),
    'grandpa': ({'grandpa', 'grandfather'}, 'grandparent', 'he'),
    'stepmom': ({'stepmom', 'stepmum', 'stepmother'}, 'stepparent', 'she'),
    'stepdad': ({'stepdad', 'stepfather'}, 'stepparent', 'he'),
    'aunt': ({'aunt'}, '', ''), 'uncle': ({'uncle'}, '', ''), 'cousin': ({'cousin'}, '', ''),
    'best friend': ({'best friend'}, '', ''), 'roommate': ({'roommate', 'flatmate'}, '', ''),
    'coworker': ({'coworker', 'co-worker', 'colleague'}, '', ''), 'neighbor': ({'neighbor', 'neighbour'}, '', ''),
    'boss': ({'boss'}, '', ''), 'ex': ({'ex', 'ex-wife', 'ex-husband', 'ex-girlfriend', 'ex-boyfriend'}, '', ''),
    'friend': (circle.OLD_FRIENDS | {'friend', 'new friend', 'best friend'}, '', ''),
}
WORDS = {'mother': 'mom', 'mum': 'mom', 'mama': 'mom', 'momma': 'mom', 'ma': 'mom', 'father': 'dad', 'papa': 'dad',
         'pa': 'dad', 'pops': 'dad', 'sis': 'sister', 'grandmother': 'grandma', 'nana': 'grandma', 'gran': 'grandma',
         'granny': 'grandma', 'grandfather': 'grandpa', 'granddad': 'grandpa', 'grandad': 'grandpa',
         'gramps': 'grandpa', 'stepmum': 'stepmom', 'stepmother': 'stepmom', 'stepfather': 'stepdad',
         'auntie': 'aunt', 'bestie': 'best friend', 'flatmate': 'roommate', 'co-worker': 'coworker',
         'colleague': 'coworker', 'neighbour': 'neighbor', 'ex-wife': 'ex', 'ex-husband': 'ex', 'ex-girlfriend': 'ex',
         'ex-boyfriend': 'ex'}
# Family words a companion uses without "my": "mom got laid off", "grandpa's in the hospital".
BARE = ('mom', 'mum', 'dad', 'grandma', 'grandpa', 'nana', 'gramps', 'granny', 'grandad', 'granddad')
# "my friend" names nobody until a name follows it.
NEEDS_NAME = {'friend'}
AGE_WORDS = r"(?:(?:older|younger|little|big|baby|twin|kid|eldest|oldest|youngest|old|dear|sweet|lovely)\s+)?"
PLURAL = re.compile(r"\b(?:my|our)\s+(?:parents|folks|sisters|brothers|siblings|grandparents|cousins|friends|aunts|"
                    r"uncles|kids|coworkers|co-workers|colleagues|roommates|neighbou?rs|family|mom and dad|"
                    r"mum and dad|ma and pa)\b|\bour\s+(?:mom|mum|dad|mother|father)\b", re.IGNORECASE)
GIRL = re.compile(r"\b(?:girl|daughter|she)\b", re.IGNORECASE)
BOY = re.compile(r"\b(?:boy|son|he)\b", re.IGNORECASE)
BABY_NAME = re.compile(r"\b(?:named|called|name is|name's)\s+(?-i:([A-Z][a-z]+))", re.IGNORECASE)
SHE_WORDS = re.compile(r"\b(?:girlfriend|wife|woman|girl|lady)\b", re.IGNORECASE)
HE_WORDS = re.compile(r"\b(?:boyfriend|husband|man|guy|fella|gentleman)\b", re.IGNORECASE)


@dataclass(frozen=True)
class Phrase:
    area: str
    kind: str
    pattern: re.Pattern


@dataclass(frozen=True)
class Ref:
    start: int
    end: int
    ids: frozenset  # the circle people it can be: one is a match, none or two names nobody for sure


@dataclass
class Said:
    """One piece of news found in a message: who, what, and what came with it."""
    row: dict
    area: str
    kind: str
    statement: str
    given: dict


# The bank -------------------------------------------------------------------------------------------------------------

@cache
def bank() -> dict:
    found = json.loads((catalog.DATA / 'said_changes.json').read_text(encoding='utf-8'))
    return {area: kinds for area, kinds in found.items() if not area.startswith('_')}


def variants(phrase: str) -> list[str]:
    """The phrase, and with "'s" for a leading "is" or "has" ("my sister's engaged")."""
    first, _sep, rest = phrase.partition(' ')
    return [phrase, f"'s {rest}"] if first in ('is', 'has') and rest else [phrase]


def compiled(phrase: str) -> re.Pattern:
    tokens = phrase.split(' ')
    end = tokens[-1] == '$'
    tokens = tokens[:-1] if end else tokens
    parts = [rf"(?P<name>{NAME}|{LOWER_NAME})" if token == '{name}' and tokens[0] == 'and' else
             rf"(?P<name>{NAME})" if token == '{name}' else rf"(?P<place>{PLACE})" if token == '{place}'
             else re.escape(token) for token in tokens]
    lead = '' if phrase.startswith("'s") else rf"{FROM},?\s+"
    return re.compile(rf"^{lead}(?:{FILLER}\s+)*" + rf"\s+(?:{FILLER}\s+)*".join(parts) + r"(?![\w'’-])" +
                      (END if end else ''), re.IGNORECASE)


@cache
def phrases() -> tuple[Phrase, ...]:
    """Every phrase as a pattern, longest first, so "got engaged to Ren" wins over "got engaged"."""
    found = [(area, kind, text) for area, kinds in bank().items() for kind, texts in kinds.items()
             for phrase in texts for text in variants(phrase)]
    found.sort(key=lambda item: len(item[2]), reverse=True)
    return tuple(Phrase(area, kind, compiled(text)) for area, kind, text in found)


# Who a sentence is about ----------------------------------------------------------------------------------------------

def pronoun(row: dict) -> str:
    return (circle.details_of(row).get('pronouns') or '').split('/')[0]


def fits(row: dict, word: str) -> bool:
    roles, general, pronoun_ = RELATIONS[word]
    role = (row.get('role') or '').casefold()
    return role in roles or bool(general and circle.role_kind(role) == general and pronoun(row) == pronoun_)


def named(row: dict, name: str) -> bool:
    name = name.casefold()
    full = (circle.details_of(row).get('full_name') or row['name']).casefold()
    return name in (row['name'].casefold(), row['name'].split(' ')[0].casefold(), full)


def relation_pattern(people: list[dict], lowercase: bool) -> re.Pattern:
    words = sorted({*RELATIONS, *WORDS}, key=len, reverse=True)
    names = names_pattern(people, lowercase)
    name = rf"(?:,?\s+(?P<name>{names}))?" if names else ''
    bare = '|'.join(BARE)
    return re.compile(rf"(?:\bmy\s+{AGE_WORDS}(?P<rel>{'|'.join(re.escape(word) for word in words)})|"
                      rf"(?<![\w'’])(?<!your )(?<!his )(?<!her )(?<!their )(?<!our )(?<!the )(?<!a )"
                      rf"(?P<bare>{bare}))\b{name}", re.IGNORECASE)


def names_pattern(people: list[dict], lowercase: bool) -> str:
    """Their first and full names; in lowercase text names come lowercase too, but never a common word ("june")."""
    from companion.self_facts import NOT_LOWER_NAMES
    found = {part for row in people for part in (row['name'], row['name'].split(' ')[0],
                                                 circle.details_of(row).get('full_name') or '') if part}
    if lowercase:
        found = {name for name in found if name.casefold() not in NOT_LOWER_NAMES}
    alternatives = '|'.join(re.escape(name) for name in sorted(found, key=len, reverse=True))
    return alternatives and (alternatives if lowercase else f'(?-i:{alternatives})')


def refs(sentence: str, people: list[dict], lowercase: bool) -> list[Ref]:
    """Every mention of a person in the sentence: by relation ("my mom", "my sister Mara"), by name, or a plural that
    names several ("my parents")."""
    found = [Ref(match.start(), match.end(), frozenset()) for match in PLURAL.finditer(sentence)]
    for match in relation_pattern(people, lowercase).finditer(sentence):
        said = (match['rel'] or match['bare']).casefold()
        word = WORDS.get(said, said)
        given = match.groupdict().get('name')
        ids = {row['id'] for row in people if fits(row, word) and (not given or named(row, given))}
        if word in NEEDS_NAME and not given:
            ids = set()
        found.append(Ref(match.start(), match.end(), frozenset(ids)))
    names = names_pattern(people, lowercase)
    if names:
        pattern = re.compile(rf"\b(?:{names})\b", re.IGNORECASE if lowercase else 0)
        for match in pattern.finditer(sentence):
            if not any(ref.start <= match.start() < ref.end for ref in found):
                ids = {row['id'] for row in people if named(row, match.group(0))}
                found.append(Ref(match.start(), match.end(), frozenset(ids)))
    return sorted(found, key=lambda ref: ref.start)


# Reading a message ----------------------------------------------------------------------------------------------------

def plain(sentence: str) -> bool:
    """A plain statement: no question, hedge, joke or story from long ago."""
    return bool(sentence) and not sentence.rstrip().endswith('?') and not QUESTION_START.match(sentence) and not \
        HYPOTHETICAL.search(sentence) and not HEDGE.search(sentence)


def news_after(sentence: str, ref: Ref) -> tuple[Phrase, re.Match] | None:
    """The news that follows the person, with nothing but small words between."""
    rest = sentence[ref.end:].replace('’', "'")
    for phrase in phrases():
        match = phrase.pattern.match(rest)
        if match and not NOT_AFTER.match(rest[match.end():]) and not NEGATION.search(rest[:match.end()]) and \
                common(match.groupdict().get('name')):
            return phrase, match
    return None


def common(name: str | None) -> bool:
    """A name, not a common word in lowercase ("my mom and dad are done")."""
    from companion.self_facts import NOT_LOWER_NAMES
    return not name or name[:1].isupper() or (name not in NOT_LOWER_NAMES and name not in BARE and
                                              name not in WORDS and name not in RELATIONS and
                                              not re.search(r"(?:ing|ed|ly)$", name))


def read(text: str, people: list[dict], lowercase: bool = False) -> list[tuple[str, str, str, dict, str]]:
    """(person id, area, kind, given, sentence) for each sentence with news about exactly one circle person."""
    from companion.self_facts import lowercase_style
    text = QUOTED.sub(' ', ACTIONS.sub(' ', text))
    lowercase = lowercase or lowercase_style(text)
    if NOT_NEWS.search(text) or LONG_AGO.search(text):
        return []
    found = []
    for sentence in (part.strip() for part in SENTENCE.findall(text)):
        if not plain(sentence):
            continue
        mentioned = refs(sentence, people, lowercase)
        if len(mentioned) != 1 or len(mentioned[0].ids) != 1:
            continue
        hit = news_after(sentence, mentioned[0])
        if hit:
            phrase, match = hit
            person_id = next(iter(mentioned[0].ids))
            found.append((person_id, phrase.area, phrase.kind, given_with(phrase, match, sentence), sentence))
    return found


def given_with(phrase: Phrase, match: re.Match, sentence: str) -> dict:
    """What came with the news: a partner's name and who they are, a place, a baby's name and sex."""
    groups = match.groupdict()
    given = {}
    if groups.get('name') and phrase.area == 'partner':
        given['partner_name'] = groups['name']
        given['partner_pronouns'] = 'she/her' if SHE_WORDS.search(sentence) else \
            'he/him' if HE_WORDS.search(sentence) else ''
    if groups.get('place'):
        given['place'] = groups['place'].rstrip('.')
    if phrase.area == 'health' and phrase.kind != 'recovered':  # How long it keeps them out of their days, by its words (health_stays.py).
        given['stay'] = health_stays.category(phrase.kind, match.string[match.start():])
        given['home_now'] = bool(health_stays.HOME_NOW.search(match.group(0)))
    if phrase.area == 'baby':
        baby = BABY_NAME.search(sentence[match.start():])
        given['child'] = baby.group(1) if baby else ''
        given['pronouns'] = 'she/her' if GIRL.search(sentence[match.start():]) else \
            'he/him' if BOY.search(sentence[match.start():]) else ''
    return {key: value for key, value in given.items() if value or key == 'stay'}


# Whether the news can change the record -------------------------------------------------------------------------------

def users(row: dict, area: str) -> bool:
    """The user set this part of their life, so their word stands."""
    touches = {'job': 'job', 'partner': 'love', 'moved': 'home'}.get(area)
    return bool(touches) and not happenings.apps(row, touches)


def recent(connection, timeline_id: str, row: dict, kind: str, day: date) -> bool:
    """An event (not news) or a storyline about the same part of their life in the last 60 days, or the same news
    already on their record then: the record stands."""
    area, since = AREA_OF[kind], (day - timedelta(days=RECENT_DAYS)).isoformat()
    for event in many(connection, "SELECT kind, source FROM person_events WHERE timeline_id=? AND subject=? AND "
                      "status='active' AND local_date>=?", (timeline_id, row['id'], since)):
        if event['kind'] == kind or (AREA_OF.get(event['kind']) == area and not event['source'].startswith(SOURCE)):
            return True
    return storyline_about(connection, timeline_id, row, area, since)


def storyline_about(connection, timeline_id: str, row: dict, area: str, since: str) -> bool:
    from companion.life import storylines
    for story in many(connection, "SELECT * FROM storylines WHERE timeline_id=? AND status='running' AND "
                      "(started_on>=? OR story IN ('expecting', 'adopting')) AND cast_ids LIKE ?",
                      (timeline_id, since, f'%"{row["id"]}"%')):
        if area == 'baby' and story['story'] in BABY_STORIES:
            return True
        kinds = {found[0] for index, stage in enumerate(decode(story['stages']))
                 if (found := storylines.effect_of(story, index, stage))}
        if any(AREA_OF.get(kind) == area for kind in kinds):
            return True
    return False


def love_fits(state: dict, kind: str) -> bool:
    """A change of love life that is a change: no engagement for someone engaged, no breakup for someone single."""
    now = state['state']
    if (state['partner'] or {}).get('key') == 'companion':
        return False
    return {'picked': now in ('single', 'divorced', 'widowed'), 'engaged': now not in ('engaged', 'married'),
            'married': now != 'married', 'broke_up': now in circle_love.WITH_PARTNER}[kind]


def fits_now(connection, timeline_id: str, row: dict, kind: str, day: date) -> bool:
    """The news changes something about them as they are now."""
    details = circle.details_of(row)
    if kind == 'retired':
        return casting.has_job(row) and old_enough(connection, details)
    if kind in ('promoted', 'laid_off', 'quit'):
        return casting.has_job(row)
    if AREA_OF[kind] == 'partner':
        return love_fits(circle_love.state(connection, row, circle.people(connection, timeline_id)), kind)
    if kind in ('moved_away', 'moved_away_to'):
        return casting.in_town(row)
    if kind == 'moved_back':
        return not casting.in_town(row)
    if kind == 'recovered':
        return bool(details.get('health') or details.get('in_treatment_since'))
    if AREA_OF[kind] == 'baby':
        return baby_fits(connection, row, kind, day)
    return True


def old_enough(connection, details: dict) -> bool:
    """Old enough to retire, in human years; someone of no known age may."""
    from companion.life import ages
    age = details.get('age')
    return not isinstance(age, int) or (ages.person_life_age(connection, details, age) or age) >= RETIRE_AGE


def baby_fits(connection, row: dict, kind: str, day: date) -> bool:
    from companion.life import families
    if not families.ACTIVE or not families.kinship(row):
        return False
    since = (day - timedelta(days=BABY_DAYS)).isoformat()
    return not any(child['status'] == 'expected' or child['born_on'] >= since
                   for child in families.children_of(connection, row['id']))


def allowed(connection, timeline_id: str, row: dict, kind: str, day: date) -> bool:
    if circle.details_of(row).get('love') or row['role'] in circle_love.PARTNER_ROLES:
        return False  # The companion's own partner: that is the companion's love life, not news.
    if AREA_OF[kind] in ('job', 'partner', 'baby') and not casting.adult(row):
        return False
    return not users(row, AREA_OF[kind]) and not recent(connection, timeline_id, row, kind, day) and \
        fits_now(connection, timeline_id, row, kind, day)


# Writing it -----------------------------------------------------------------------------------------------------------

def placed(connection, companion: dict, row: dict, kind: str, given: dict) -> str:
    """A move with a place: into one of the city's neighborhoods, back to the city for someone out of town, else away
    to it."""
    from companion.life import outings
    place = given.get('place')
    if AREA_OF[kind] != 'moved' or not place:
        return kind
    data = outings.city_data(connection, companion['version']['definition']) or {}
    hoods = {hood['name'] for hood in data.get('neighborhoods') or []}
    if place not in hoods | {data.get('name') or ''}:
        return 'moved_away_to'
    if not casting.in_town(row):
        return 'moved_back'
    return 'moved_to' if place in hoods else 'moved'


def partner_of(connection, companion: dict, row: dict, given: dict) -> dict | None:
    """Someone new by the name the companion gave, keyed as circle_love.new_partner keys them."""
    if not given.get('partner_name'):
        return None
    made = circle_love.new_partner(connection, companion, row)
    name = given['partner_name']
    return {**made, 'name': name.split(' ')[0], 'full': name if ' ' in name else made['full'].replace(
        made['name'], name, 1), 'pronouns': given.get('partner_pronouns') or made['pronouns']}


def moment(companion: dict, message: dict) -> datetime:
    return parse(message['created_at']).astimezone(zone(companion['version']['timezone']))


def note(connection, companion: dict, message: dict, said: Said, now) -> bool:
    """Write one piece of news: the self fact the user sees, then the event through happenings."""
    key = f"{CATEGORY}:{said.row['id']}:{said.kind}"
    if optional(connection, 'SELECT id FROM self_facts WHERE message_id=? AND key=?', (message['id'], key)):
        return False
    fact_id, local = identifier(), moment(companion, message)
    connection.execute(
        'INSERT INTO self_facts (id, companion_id, message_id, key, category, subject, value, statement, status, '
        "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'noted', ?)",
        (fact_id, companion['id'], message['id'], key, CATEGORY, said.row['name'], said.statement[:300],
         said.statement[:300], stamp(now)))
    given = {**said.given, 'message_id': message['id']}
    if partner := partner_of(connection, companion, said.row, said.given):
        given['partner'] = partner
    happenings.record(connection, companion, subject=said.row['id'], source=f'{SOURCE}{fact_id}', kind=said.kind,
                      day=local.date().isoformat(), at=local.strftime('%H:%M'), now=now, given=given)
    line = line_of(connection, companion['active_timeline_id'], fact_id)
    connection.execute('UPDATE self_facts SET value=? WHERE id=?', (line or said.statement[:300], fact_id))
    return True


def line_of(connection, timeline_id: str, fact_id: str) -> str | None:
    row = optional(connection, 'SELECT * FROM person_events WHERE timeline_id=? AND source=?',
                   (timeline_id, f'{SOURCE}{fact_id}'))
    if row is None:
        return None
    names = {person['id']: person['name'] for person in circle.people(connection, timeline_id, include_removed=True)}
    return happenings.filled(row, names, '')


def notice(connection, companion: dict, message: dict, lowercase: bool, now) -> int:
    """Read one completed companion message for news about their people, and write what can be written. Before that,
    news whose message has left the timeline is taken back (`sweep`)."""
    timeline_id = companion['active_timeline_id']
    sweep(connection, companion, now)
    if message['role'] != 'companion' or message['status'] != 'complete' or message['timeline_id'] != timeline_id:
        return 0
    people = circle.people(connection, timeline_id)
    rows = {row['id']: row for row in people}
    day = moment(companion, message).date()
    written = 0
    for person_id, area, kind, given, sentence in read(message['text'], people, lowercase):
        row = rows[person_id]
        kind = placed(connection, companion, row, kind, given)
        if allowed(connection, timeline_id, row, kind, day):
            written += note(connection, companion, message, Said(row, area, kind, sentence, given), now)
    return written


# Taking it back -------------------------------------------------------------------------------------------------------

def take_back(connection, timeline_id: str, fact_id: str, now) -> int:
    return happenings.take_back(connection, timeline_id, f'{SOURCE}{fact_id}', now)


def sweep(connection, companion: dict, now) -> int:
    """News whose message is no longer on the timeline (another version chosen, deleted, redacted) or whose fact the
    user removed: its change is taken back, as if never said."""
    from companion import self_facts
    timeline_id = companion['active_timeline_id']
    rows = many(connection, "SELECT source FROM person_events WHERE timeline_id=? AND status='active' AND source LIKE ?",
                (timeline_id, f'{SOURCE}%'))
    if not rows:
        return 0
    standing = {row['id'] for row in self_facts.in_force(connection, timeline_id)}
    gone = [row['source'].removeprefix(SOURCE) for row in rows if row['source'].removeprefix(SOURCE) not in standing]
    return sum(take_back(connection, timeline_id, fact_id, now) for fact_id in gone)


def undo(database, fact_id: str) -> dict:
    """Undo on the diary line: the change is taken back and the fact removed, so the companion's context drops it."""
    from companion import self_facts
    from companion.characters import require_current
    from companion.errors import require
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        fact = optional(connection, 'SELECT * FROM self_facts WHERE id=? AND category=?', (fact_id, CATEGORY))
        require(fact is not None, 'That news is not on record.', 404)
        connection.execute("UPDATE self_facts SET status='rejected', decided_at=? WHERE id=?", (stamp(now), fact_id))
        taken = take_back(connection, companion['active_timeline_id'], fact_id, now)
        self_facts.stamp_change(connection, stamp(now), companion)
    return {'taken_back': taken}


def said_view(connection, source: str) -> dict | None:
    """For a diary line from news: the fact behind it and the words it came from, for Undo."""
    if not source.startswith(SOURCE):
        return None
    fact = optional(connection, 'SELECT id, statement, created_at FROM self_facts WHERE id=?',
                    (source.removeprefix(SOURCE),))
    return {'fact_id': fact['id'], 'statement': fact['statement'], 'said_at': fact['created_at']} if fact else None
