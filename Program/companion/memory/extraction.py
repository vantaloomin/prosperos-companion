"""Rule-based capture of explicitly stated facts (PRD M7, M8), with no model call.

Only first-person, declarative statements are captured. Questions, hypotheticals, conditionals,
roleplay actions and quoted text never become candidates, so "Hypothetically, I live on the
moon" or a quoted line from a film cannot create a real-user fact. Every candidate keeps the
exact sentence it came from; the formation step decides whether it may be committed.
"""
import re
from dataclasses import dataclass, field, replace
from datetime import datetime

from companion.memory import dates, people_rules

EXTRACTOR_VERSION = 'rules-v1'

# Subjects that hold one current value: a new current value ends the previous one (M8).
SINGLE_VALUED = {'preferred_name', 'nickname', 'home_city', 'work', 'birthday'}
# Rules and words that say a value changed, so a new value may replace the current one (M8).
CHANGE_RULES = {'moved', 'new_job', 'person_moved'}
CHANGE_MARKER = re.compile(r'\b(?:now|these days|nowadays|any ?more|from now on|currently|changed|switched|new|'
                           r'instead|no longer|since)\b', re.IGNORECASE)
SUBJECT_KEYS = {
    'name': 'preferred_name', 'preferred name': 'preferred_name', 'what to call me': 'preferred_name',
    'home': 'home_city', 'home city': 'home_city', 'city': 'home_city', 'location': 'home_city',
    'where i live': 'home_city', 'lives in': 'home_city',
    'job': 'work', 'work': 'work', 'occupation': 'work', 'career': 'work', 'employer': 'work',
    'birthday': 'birthday',
    'nickname': 'nickname', 'nick name': 'nickname', 'my nickname': 'nickname',
}

SENSITIVE = re.compile(
    r'\b(?:diagnos\w*|disorder|depress\w*|anxiety|adhd|autis\w*|bipolar|ptsd|medicat\w*|therap\w*|pregnan\w*|'
    r'allerg\w*|cancer|doctor\'?s? appointment|diabet\w*|asthma|surgery|disabilit\w*|illness|'
    r'gay|lesbian|bisexual|queer|transgender|asexual|sexual\w*|'
    r'christian|muslim|jewish|hindu|buddhis\w*|atheis\w*|church|mosque|synagogue|religio\w*|'
    r'democrat\w*|republican|socialist|politic\w*|vot(?:e|ed|ing)|'
    r'debt|salary|bankrupt\w*|loan|income|arrest\w*|convict\w*|prison|lawsuit|visa|immigra\w*|undocumented|'
    r'\d+ \w+ (?:street|st|avenue|ave|road|rd|lane|ln)|\+?\d[\d -]{8,}\d)\b', re.IGNORECASE)

HYPOTHETICAL = re.compile(
    r'\b(?:hypothetical\w*|imagine|suppose|supposing|pretend\w*|what if|if i|if we|let\'?s say|in the story|'
    r'in character|role-?play\w*|my character|as a joke|kidding|jk|lol jk|dreamt|dreamed|in my dream)\b',
    re.IGNORECASE)
QUESTION_START = re.compile(
    r'^(?:do|does|did|should|would|could|can|will|what|why|how|where|when|who|is|are|am|was|were|have|has)\b',
    re.IGNORECASE)
QUOTED = re.compile(r'"[^"]*"|“[^”]*”|\([^)]*\booc\b[^)]*\)', re.IGNORECASE)
# A message with *actions* is written in character, so none of it is a real-life statement.
ROLEPLAY = re.compile(r'\*[^*\n]+\*')
SENTENCE = re.compile(r'[^.!?\n;]+[.!?]*')

PLACE = r"(?-i:([A-Z][\w.'’-]*(?:[ -](?:(?:de|la|del|upon|of|on) )?[A-Z][\w.'’-]*)*))"
# Capitalised words that end a place name ("Lisbon on Saturday", "Boston in March").
NOT_PLACE = set(dates.WEEKDAYS) | set(dates.MONTHS) | {'next', 'last', 'this', 'today', 'tomorrow', 'tonight'}
NAME = r"(?-i:([A-Z][\w'’-]+(?: [A-Z][\w'’-]+)?))"
THING = r"([^,.;!?]+)"
NOT_THINGS = {'you', 'it', 'that', 'this', 'them', 'him', 'her', 'those', 'these', 'everything', 'nothing',
              'something', 'anything', 'everyone', 'nobody', 'talking to you', 'that idea', 'this idea'}
CLAUSE_END = re.compile(r'\s+(?:because|but|although|though|so|and i|and my|when|since|if)\b.*$', re.IGNORECASE)
PLAN_NOUNS = ('interview', 'appointment', 'exam', 'meeting', 'date', 'flight', 'trip', 'party', 'wedding',
              'concert', 'game', 'match', 'presentation', 'deadline', 'holiday', 'vacation', 'birthday party',
              'dinner', 'call', 'move', 'surgery', 'class', 'test', 'visit')
PLAN_NOUN = '(' + '|'.join(sorted(PLAN_NOUNS, key=len, reverse=True)) + ')'
TEMPORARY = r'(tired|exhausted|sick|ill|unwell|busy|stressed|swamped|overwhelmed|travel(?:l)?ing|away|' \
            r'on holiday|on vacation|off work|working late|in a rush|sleepy|hungover|sad|down|happy|excited|nervous)'
# "I work nights as a nurse": when they work, between "work" and the job.
SHIFTS = r'(?:nights|days|evenings|mornings|weekends|shifts|part[- ]time|full[- ]time|from home|remotely)'
PRONOUN_CLAUSE = re.compile(r',?\s+and\s+(?=(?:he|she|they)\b)', re.IGNORECASE)
RELATIONS = r'(sister|brother|mum|mom|mother|dad|father|partner|wife|husband|girlfriend|boyfriend|son|' \
            r'daughter|best friend|roommate|flatmate|boss|cat|dog|rabbit|parrot|hamster)'


@dataclass
class Candidate:
    layer: str
    subject: str
    value: str
    rule: str
    excerpt: str
    subject_key: str = ''
    boundary: bool = False
    sensitive: bool = False
    plan_status: str | None = None
    applies_from: datetime | None = None
    applies_until: datetime | None = None
    dates_uncertain: bool = False
    # For plan updates: the words that identify the plan being changed.
    target: str | None = None
    extra: dict = field(default_factory=dict)

    def __post_init__(self):
        self.subject_key = self.subject_key or subject_key(self.subject)
        self.sensitive = self.sensitive or bool(SENSITIVE.search(f'{self.subject} {self.value}'))

    @property
    def signals_change(self) -> bool:
        """"I moved to Boston" or "these days I prefer tea" replaces; a bare "I live in Denver" does not say so."""
        return self.rule in CHANGE_RULES or bool(CHANGE_MARKER.search(self.excerpt))


def subject_key(subject: str) -> str:
    folded = ' '.join(subject.casefold().split())
    return SUBJECT_KEYS.get(folded, re.sub(r'[^\w]+', '_', folded).strip('_'))


def single_valued(key: str) -> bool:
    if key.startswith('person.'):
        return key.rsplit('.', 1)[-1] in people_rules.SINGLE_TOPICS
    return key in SINGLE_VALUED or key.startswith('favourite_')


def named(text: str) -> bool:
    """A capitalised word after "my sister" is a name, not a date word or "I'm"."""
    first = text.split()[0].casefold()
    return first not in NOT_PLACE and not first.startswith(('i\'', 'i’'))


def place(text: str) -> str:
    """A place name without trailing date words or connectors."""
    words = []
    for word in text.split():
        if word.casefold() in NOT_PLACE:
            break
        words.append(word)
    while len(words) > 1 and words[-1] in {'de', 'la', 'del', 'upon', 'of', 'on'}:
        words.pop()
    return ' '.join(words)


def thing(text: str) -> str | None:
    """A short object phrase, trimmed at the next clause; None when it is a pronoun or too long."""
    text = CLAUSE_END.sub('', text).strip(' \'"')
    text = re.sub(r'\s+(?:please|thanks|thank you|ok|okay|now|these days|nowadays|any ?more|currently|instead)$', '',
                  text, flags=re.IGNORECASE)
    if not text or text.casefold() in NOT_THINGS or len(text.split()) > 8:
        return None
    return text


def sentences(text: str) -> list[str]:
    """Declarative sentences with quotes, roleplay actions and questions removed."""
    if HYPOTHETICAL.match(text.strip()) or ROLEPLAY.search(text):
        return []
    found = []
    for raw in SENTENCE.findall(QUOTED.sub(' ', text)):
        sentence = ' '.join(raw.split())
        if not sentence or sentence.endswith('?') or QUESTION_START.match(sentence) or HYPOTHETICAL.search(sentence):
            continue
        found.append(sentence.rstrip('.!'))
    return found


@dataclass(frozen=True)
class Statement:
    sentence: str
    stated: datetime
    timezone: str

    def span(self, past=False):
        return dates.resolve(self.sentence, self.stated, self.timezone, past)

    def bounds(self, past=False, point=False):
        """`point` marks a span longer than a day uncertain when one moment is meant ("moved last week")."""
        span = self.span(past)
        if span is None:
            return None, None, False
        start, end = dates.bounds(span, self.timezone)
        return start, end, not span.certain or (point and (span.end - span.start).days > 1)


def name_rule(statement):
    match = re.search(rf"\b(?:my name is|my name's|call me|i go by)\s+{NAME}", statement.sentence, re.IGNORECASE)
    negated = match and re.search(r"(?:n't|\bnot|\bnever)\s+(?:ever\s+)?$", statement.sentence[:match.start()])
    if match and not negated and not dates.PHRASE.fullmatch(match.group(1)):
        yield Candidate('user_fact', 'Preferred name', match.group(1), 'name', statement.sentence)


def nickname_rule(statement):
    """Nicknames are often lower case ("my nickname is qoncat"), so the word after the phrase is taken as written."""
    match = re.search(r"\bmy nick ?name(?: is|'s|’s)\s+([\w'’-]+)", statement.sentence, re.IGNORECASE)
    negated = match and re.search(r"(?:n't|\bnot|\bnever)\s+(?:ever\s+)?$", statement.sentence[:match.start()])
    if match and not negated:
        yield Candidate('user_fact', 'Nickname', match.group(1), 'nickname', statement.sentence)


def place_rules(statement):
    """Moves, current homes, past homes and possible moves are different facts (M8)."""
    text = statement.sentence
    if match := re.search(rf"\bi(?:'m| am)? (?:might|may|could|thinking (?:about|of)|considering|hoping to|"
                          rf"want to|would like to) (?:move|moving|relocat\w*) to {PLACE}", text, re.IGNORECASE):
        yield Candidate('plan', 'Possible move', f'Might move to {place(match.group(1))}', 'possible_move', text,
                        plan_status='proposed')
        return
    if match := re.search(rf"\bi(?:'m| am| will be|'ll be) (?:moving|relocating) to {PLACE}", text, re.IGNORECASE):
        start, _end, uncertain = statement.bounds()
        yield Candidate('plan', 'Move', f'Moving to {place(match.group(1))}', 'planned_move', text, plan_status='agreed',
                        applies_from=start, dates_uncertain=uncertain)
        return
    if match := re.search(rf"\bi(?: used to| once)? lived in {PLACE}|\bi used to live in {PLACE}", text,
                          re.IGNORECASE):
        home = place(match.group(1) or match.group(2))
        start, end, uncertain = statement.bounds(past=True)
        until = end or statement.stated
        yield Candidate('user_fact', 'Home city', home, 'past_home', text, applies_from=start,
                        applies_until=min(until, statement.stated), dates_uncertain=uncertain or start is None)
        return
    if match := re.search(rf"\bi(?:'ve| have)? (?:just |finally |recently )?(?:moved|relocated) (?:to|into) {PLACE}",
                          text, re.IGNORECASE):
        start, _end, uncertain = statement.bounds(past=True, point=True)
        yield Candidate('user_fact', 'Home city', place(match.group(1)), 'moved', text,
                        applies_from=min(start or statement.stated, statement.stated), dates_uncertain=uncertain)
        return
    if match := re.search(rf"\bi(?: currently| now)? live in {PLACE}|\bi(?:'m| am) based in {PLACE}", text,
                          re.IGNORECASE):
        yield Candidate('user_fact', 'Home city', place(match.group(1) or match.group(2)), 'lives', text)


def work_rule(statement):
    text = statement.sentence
    if match := re.search(rf"\bi(?:'ve| have)? (?:just )?(?:started|got|landed) (?:a |my )?(?:new )?job "
                          rf"(?:as an? {THING}|at {PLACE})", text, re.IGNORECASE):
        start, _end, uncertain = statement.bounds(past=True, point=True)
        value = thing(match.group(1)) if match.group(1) else place(match.group(2))
        if value:
            yield Candidate('user_fact', 'Work', value, 'new_job', text,
                            applies_from=min(start or statement.stated, statement.stated), dates_uncertain=uncertain)
        return
    if match := re.search(rf"\bi work (?:{SHIFTS} )?(?:as an? {THING}|at {PLACE}|for {PLACE})", text, re.IGNORECASE):
        value = thing(match.group(1)) if match.group(1) else place(match.group(2) or match.group(3))
        if value:
            yield Candidate('user_fact', 'Work', value, 'work', text)


def preference_rules(statement):
    text = statement.sentence
    if match := re.search(r"\bmy fav(?:ou?rite)? (\w+(?: \w+)?) is " + THING, text, re.IGNORECASE):
        if value := thing(match.group(2)):
            topic = match.group(1).casefold()
            yield Candidate('user_fact', f'Favourite {topic}', value, 'favourite', text,
                            subject_key=f"favourite_{topic.replace(' ', '_')}")
        return
    if match := re.search(r"\bi (?:really |absolutely )?(?:hate|dislike|can't stand|cannot stand|don't like|"
                          r"do not like) " + THING, text, re.IGNORECASE):
        if value := thing(match.group(1)):
            yield Candidate('user_fact', 'Dislikes', value, 'dislike', text)
        return
    if match := re.search(r"\bi (?:really |absolutely )?(?:love|like|enjoy|adore) " + THING, text, re.IGNORECASE):
        if value := thing(match.group(1)):
            yield Candidate('user_fact', 'Likes', value, 'like', text)
        return
    if match := re.search(r"\bi(?:'d| would)? prefer " + THING, text, re.IGNORECASE):
        if value := thing(match.group(1)):
            yield Candidate('user_fact', 'Preference', f'Prefers {value}', 'prefer', text)


def boundary_rule(statement):
    text = statement.sentence
    match = re.search(r"\b(?:please )?(?:don't|do not|never) (?:ever )?(mention|bring up|talk about|ask (?:me )?about|"
                      r"call me|joke about) " + THING, text, re.IGNORECASE) or \
        re.search(r"\bi (?:don't|do not) want to (talk about|hear about|discuss) " + THING, text, re.IGNORECASE)
    if match and (value := thing(match.group(2))):
        verb = match.group(1).lower()
        yield Candidate('user_fact', 'Boundary', f"Don't {verb} {value}", 'boundary', text, boundary=True,
                        subject_key=f"boundary_{subject_key(value)}")


def personal_rules(statement):
    text = statement.sentence
    if match := re.search(r"\bi(?:'m| am) allergic to " + THING, text, re.IGNORECASE):
        if value := thing(match.group(1)):
            yield Candidate('user_fact', 'Allergy', value, 'allergy', text, sensitive=True)
    if match := re.search(r"\bmy birthday is (?:on )?" + THING, text, re.IGNORECASE):
        if value := thing(match.group(1)):
            yield Candidate('user_fact', 'Birthday', value, 'birthday', text)


def temporary_rule(statement):
    text = statement.sentence
    match = re.search(rf"\bi(?:'m| am| will be|'ll be)(?: (?:feeling|so|really|a bit|pretty|very|super|quite))* "
                      rf"{TEMPORARY}\b", text, re.IGNORECASE)
    if not match:
        return
    start, end, uncertain = statement.bounds()
    stated_day = dates.local_day(statement.stated, statement.timezone)
    today_end = dates.instant(stated_day, statement.timezone) + dates.timedelta(days=1)
    yield Candidate('temporary', 'Current circumstance', match.group(1).capitalize(), 'temporary', text,
                    applies_from=min(start or statement.stated, statement.stated), applies_until=end or today_end,
                    dates_uncertain=uncertain)


def plan_rules(statement):
    """Plans need a date; a status update names the plan it changes."""
    text = statement.sentence
    update = re.search(rf"\bmy {PLAN_NOUN} (?:got |was |has been |is |'s )?(postponed|moved|pushed back|rescheduled|"
                       rf"cancelled|canceled|called off|went well|went badly|is done|is over|happened)", text,
                       re.IGNORECASE)
    if update:
        word = update.group(2).lower()
        status = 'cancelled' if word in {'cancelled', 'canceled', 'called off'} else \
            'completed' if word in {'went well', 'went badly', 'is done', 'is over', 'happened'} else 'postponed'
        start, _end, uncertain = statement.bounds() if status == 'postponed' else (None, None, False)
        yield Candidate('plan', update.group(1).capitalize(), '', 'plan_update', text, plan_status=status,
                        applies_from=start, dates_uncertain=uncertain, target=update.group(1).lower())
        return
    visit = re.search(rf"\b(?:my {RELATIONS},?(?: {NAME})?|{NAME}) (?:is|are|'s|will be|'ll be) (?:visiting|"
                      rf"coming (?:over|to visit|to stay|to see (?:me|us))|staying with (?:me|us)|flying in)\b", text,
                      re.IGNORECASE)
    if visit and statement.span() is not None:
        start, _end, uncertain = statement.bounds()
        who = next((name for name in (visit.group(2), visit.group(3)) if name and named(name)), None) or \
            f'my {(visit.group(1) or "guest").lower()}'
        yield Candidate('plan', f'Visit from {who}', text, 'visit', text, plan_status='agreed', applies_from=start,
                        dates_uncertain=uncertain, target='visit')
        return
    match = re.search(rf"\bi(?:'ve| have)? (?:got )?(?:an? |my )?{PLAN_NOUN}\b", text, re.IGNORECASE) or \
        re.search(rf"\bi(?:'m| am) (?:going|flying|heading|travel(?:l)?ing|driving) to {PLACE}", text, re.IGNORECASE)
    span = statement.span()
    if match and span is not None:
        start, _end, uncertain = statement.bounds()
        noun = match.group(1)
        subject = noun.capitalize() if noun.lower() in PLAN_NOUNS else f'Trip to {place(noun)}'
        yield Candidate('plan', subject, text, 'plan', text, plan_status='agreed', applies_from=start,
                        dates_uncertain=uncertain, target=noun.lower())


RULES = (name_rule, nickname_rule, place_rules, work_rule, boundary_rule, preference_rules, personal_rules, temporary_rule,
         plan_rules)


def person_candidate(found, sentence) -> Candidate:
    """A fact about someone in the user's life; formation matches the reference to a stored person."""
    reference = found.reference
    if found.topic == 'who':
        subject = (reference.relation or 'Someone').capitalize()
    else:
        subject = f'{reference.label}: {people_rules.TOPIC_LABELS[found.topic]}'
    rule = 'person_moved' if found.changed else f'person_{found.topic}'
    return Candidate('user_fact', subject, found.value, rule, sentence, sensitive=found.grief,
                     subject_key=f'person.{reference.key}.{found.topic}',
                     extra={'person': reference.as_dict(), 'topic': found.topic, 'grief': found.grief})


def extract(text: str, stated: datetime, timezone: str, people: dict | None = None,
            exclude: tuple = ()) -> list[Candidate]:
    """Candidates from one user message, in sentence order, without duplicates.

    `people` maps the names of people the user already mentioned to their relation, so "Jo got
    promoted" is recognised once Jo is known; `exclude` holds names that are never the user's people
    (the companion's own).
    """
    found, seen, previous = [], set(), None
    for sentence in sentences(text):
        statement = Statement(sentence, stated, timezone)
        about_people = []
        # "My cat is Biscuit and she hates the vacuum": the clause after "and she" is about the same one.
        for clause in PRONOUN_CLAUSE.split(sentence):
            found_here, previous = people_rules.scan(clause, people or {}, previous,
                                                     tuple(name.casefold() for name in exclude))
            about_people += found_here
        candidates = [candidate for rule in RULES for candidate in rule(statement)]
        candidates += [person_candidate(item, sentence) for item in about_people]
        for candidate in candidates:
            identity = (candidate.layer, candidate.subject_key, candidate.value.casefold(), candidate.rule)
            if identity not in seen:
                seen.add(identity)
                found.append(replace(candidate))
    return found
