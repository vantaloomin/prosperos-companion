"""Corrections of what is already remembered (PRD M8, M9), found by rules or marked by the model.

"My mom is not a gardener" while "Mom's interests: she loves gardening" is current is not a new fact
to file beside the old one: it says the old one is wrong. A correction never changes a memory on its
own. It waits as a `correction` suggestion that names the memory it corrects, like a conflict does;
keeping it supersedes that memory with the corrected words (the old value stays as history), or, when
the value simply stopped being true ("I don't live in Chicago anymore", or any negation of a home,
job or other single-valued subject), ends it so it is recalled as no longer current.

The rules are narrow on purpose. A sentence must open with who it is about (I, "my mom", "my sister
Jo", or a name already known), then a negation ("is not", "isn't", "doesn't", "don't", "no longer",
"never") or "is A, not B". The negated words must repeat a word of exactly one current fact about
that same someone, and a home or job is only ended by "don't live in" or "don't work". "I told her my
mom isn't a gardener", "my mom isn't home" and "my mom loves her garden" propose nothing.
"""
import hashlib
import re

from companion.database import bump_memory_revision, encode, identifier, many, optional
from companion.memory import extraction, people, people_rules, records
from companion.memory.retrieval import STOP

RULE = 'correction'
KNOWN_LIMIT = 6
NEGATED = re.compile(r"n['’]t\b|\b(?:not|no longer|never)\b", re.IGNORECASE)
LEADING = r"(?:(?:no|nope|nah|actually|well|wait|honestly|oh|sorry|um|ok|okay|also|btw|fyi|lol|haha|so)[,!]?\s+)*"
ADVERB = r'(?:(?:really|definitely|actually|honestly|certainly|totally|absolutely|clearly|seriously|just)\s+)?'
NEGATION = re.compile(
    rf"\s{ADVERB}(?P<neg>(?:is|are|am|was)\s+{ADVERB}(?:not|no longer)|isn't|aren't|wasn't|ain't|(?:does|do)\s+not|"
    rf"doesn't|don't|no longer|never)\s+", re.IGNORECASE)
COPULA = re.compile(r"^(?:is|are|am|was|isn't|aren't|wasn't|ain't)\b", re.IGNORECASE)
FILLER = re.compile(r'^(?:(?:really|actually|even|definitely|honestly|certainly|exactly|totally|ever|that|so|very)'
                    r'\s+)*', re.IGNORECASE)
# What someone does or likes; "I don't think", "she doesn't know" and "I never said" are not about a fact.
VERBS = {'live', 'work', 'like', 'love', 'enjoy', 'eat', 'drink', 'play', 'speak', 'own', 'have', 'cook', 'garden',
         'smoke', 'drive', 'teach', 'study', 'watch', 'read', 'run', 'swim', 'hike', 'knit', 'paint', 'bake', 'dance',
         'sing', 'climb', 'surf', 'fish', 'collect'}
# "I'm not sure", "she's not home", "I'm not in Chicago this week": a passing state, not a correction.
NOT_COMPLEMENTS = {'sure', 'certain', 'happy', 'sad', 'worried', 'mad', 'angry', 'upset', 'okay', 'ok', 'fine',
                   'ready', 'able', 'allowed', 'going', 'trying', 'saying', 'talking', 'kidding', 'joking', 'home',
                   'here', 'there', 'around', 'available', 'free', 'feeling', 'well', 'being', 'too', 'gonna', 'done',
                   'back', 'up', 'out', 'over', 'awake', 'asleep', 'busy', 'tired', 'sick', 'alone', 'scared', 'in',
                   'at', 'on', 'with', 'about', 'for', 'that', 'the', 'my', 'your', 'you', 'me', 'it', 'like'}
CLAUSE_END = re.compile(r'\s+(?:because|but|although|though|so|and|when|since|if|which|who)\b.*$', re.IGNORECASE)
TRAILING = re.compile(r'\s+(?:anymore|any more|now|these days|nowadays|at all|either|either way)$', re.IGNORECASE)
WORDS = re.compile(r'[a-z0-9]+')
IGNORED = STOP | {'not', 'no', 'longer', 'never', 'anymore', 'any', 'more', 'really', 'actually', 'even', 'definitely',
                  'much', 'very', 'love', 'loves', 'like', 'likes', 'enjoy', 'enjoys', 'into', 'fan', 'big', 'kind',
                  'sort', 'thing', 'one', 'person', 'type', 'live', 'lives', 'work', 'works', 'don', 'doesn', 'isn',
                  'aren', 'wasn', 'am', 's', 't', 'm', 're', 'now', 'just', 'still', 'own', 'have', 'has'}
KIN = ({'mom', 'mum', 'mother'}, {'dad', 'father'}, {'grandma', 'gran', 'granny', 'nan', 'grandmother'},
       {'grandpa', 'grandad', 'grandfather'})


def stem(word: str) -> str:
    """Enough folding that "gardener", "gardening" and "gardens" meet; never shorter than four letters."""
    if word.endswith('ies') and len(word) > 4:
        word = word[:-3] + 'y'
    elif word.endswith(('ches', 'shes', 'xes', 'sses')):
        word = word[:-2]
    elif word.endswith('s') and not word.endswith('ss') and len(word) > 3:
        word = word[:-1]
    for suffix in ('ing', 'er', 'ed'):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            word = word[:-len(suffix)]
            break
    return word[:-1] if word.endswith('e') and len(word) > 4 else word


def stems(text: str, ignore=frozenset()) -> set[str]:
    folded = text.casefold().replace('’', "'")
    return {stem(word) for word in WORDS.findall(folded) if word not in IGNORED and len(word) > 1} - set(ignore)


def negated(value: str) -> bool:
    return bool(NEGATED.search(value))


def kin(word: str) -> set[str]:
    return next((group for group in KIN if word in group), {word})


def names_word(text: str, words) -> bool:
    folded = text.casefold().replace('’', "'")
    return any(re.search(rf"(?<![\w-]){re.escape(word)}(?![\w-])", folded) for word in words)


def reference_words(reference) -> set[str]:
    words = kin(reference['relation']) if reference.get('relation') else set()
    return words | ({reference['name'].casefold()} if reference.get('name') else set())


def subject_pattern(known: dict) -> re.Pattern:
    relations = '|'.join(re.escape(item) for item in sorted(people_rules.RELATIONS, key=len, reverse=True))
    names = '|'.join(re.escape(name) for name in sorted(known, key=len, reverse=True))
    known_name = f'|(?-i:(?P<known>{names}))' if names else ''
    return re.compile(rf"^{LEADING}(?:(?P<self>I)|my {people_rules.MODIFIER}(?P<relation>{relations})"
                      rf"(?:,? (?-i:(?P<name>[A-Z][\w-]*)))?{known_name})$", re.IGNORECASE)


def who(match, known: dict, exclude) -> dict | None:
    """{'self': True}, or the name and relation a subject gives; None when it names no one of the user's."""
    if match.group('self'):
        return {'self': True}
    if match.groupdict().get('known'):
        return {'name': match.group('known'), 'relation': known[match.group('known')]}
    name = match.group('name')
    if name and not people_rules.is_name(name, exclude):
        return None
    return {'name': name, 'relation': ' '.join(match.group('relation').casefold().split())}


def clean(text: str) -> str:
    return TRAILING.sub('', CLAUSE_END.sub('', text.split(',')[0]).strip(' \'"')).strip()


def statements(sentence: str, known: dict, exclude=()):
    """(reference, kind, negated words, corrected value, replacement) for a correction-shaped sentence; kind is
    'copula' or the verb ("live", "work", "like")."""
    text = re.sub(r"(\w)'(s|m|re) (not|no longer)\b",
                  lambda found: f"{found.group(1)} {dict(s='is', m='am', re='are')[found.group(2)]} {found.group(3)}",
                  sentence.replace('’', "'"))
    pattern = subject_pattern(known)
    if swap := re.match(r"^(?P<subject>.+?)(?: (?:is|are|was|am)|'s|'m) (?P<new>(?:(?!\b(?:not|never|no)\b)[^,])+?), not "
                        r"(?:an? |the )?(?P<old>[^,]+)$", text, re.IGNORECASE):
        subject = pattern.match(swap.group('subject'))
        if subject and (reference := who(subject, known, exclude)) and (old := clean(swap.group('old'))):
            new = clean(swap.group('new'))
            yield reference, 'copula', old, new, new
        return
    for negation in NEGATION.finditer(f' {text}'):
        subject = pattern.match(text[:negation.start()].strip())
        if not subject or not (reference := who(subject, known, exclude)):
            continue
        rest = clean(FILLER.sub('', text[negation.end() - 1:].strip()))
        first = (rest.split() or [''])[0].casefold()
        if not first or re.search(r'\bmy\b', rest, re.IGNORECASE):
            return
        if COPULA.match(negation.group('neg')):
            if first not in NOT_COMPLEMENTS:
                yield reference, 'copula', rest, f'not {rest}', None
        elif stem(first) in VERBS or first in VERBS:
            word = ' '.join(negation.group('neg').casefold().split())
            word = {"don't": "doesn't", 'do not': 'does not'}.get(word, word)
            yield reference, stem(first), rest.split(' ', 1)[-1] if ' ' in rest else rest, f'{word} {rest}', None
        return


def scope(connection, companion_id, reference, now) -> list[dict]:
    """Current facts about the same someone: the user's own, or one person's (by identity, or a subject that
    names them such as "Mom's interests")."""
    rows = many(connection, "SELECT * FROM memories WHERE companion_id=? AND status='active' AND layer='user_fact' "
                'AND boundary=0', (companion_id,))
    rows = [row for row in rows if not records.ended(row, now) and not negated(row['value'])
            and not row['subject_key'].endswith('dislikes') and not row['subject_key'].startswith('boundary')]
    everyone = people.known(connection, companion_id)
    if reference.get('self'):
        others = set(people_rules.RELATIONS) | {person['name'].casefold() for person in everyone if person['name']}
        return [row for row in rows if row['person_id'] is None and not names_word(row['subject'], others)]
    person = people.find(everyone, reference)
    words = reference_words(reference) | (reference_words(person) if person else set())
    return [row for row in rows if (person and row['person_id'] == person['id'])
            or (row['person_id'] is None and names_word(row['subject'], words))]


def allowed(row, kind) -> bool:
    """Only "don't live in" ends a home and only "don't work" or "not a ..." ends a job."""
    key = row['subject_key']
    home, work = key.endswith('home_city'), key == 'work' or key.endswith('.work')
    if kind == 'live':
        return home
    if kind == 'work':
        return work
    return not home and (kind == 'copula' or not work)


def target(rows, negated_words: str, ignore: set[str], replacement=None) -> dict | None:
    """The one current fact the negated words repeat most of; a tie is too unsure to propose."""
    wanted, new = stems(negated_words, ignore), stems(replacement or '', ignore)
    scored = []
    for row in rows:
        value = stems(row['value'], ignore)
        if value and wanted & value and not new & value:
            scored.append((len(wanted & value) / len(value), row))
    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored or len(scored) > 1 and scored[0][0] == scored[1][0]:
        return None
    return scored[0][1]


def ends(row, value: str, text: str, replacement=None) -> bool:
    """A negation of a home, a job or something that stopped ("anymore") ends the fact instead of rewording it."""
    return replacement is None and negated(value) and (
        extraction.single_valued(row['subject_key']) or bool(extraction.CHANGE_MARKER.search(text)))


def fields_for(row, value: str, message, excerpt: str, *, ending: bool) -> dict:
    return {'layer': row['layer'], 'subject': row['subject'], 'subject_key': row['subject_key'], 'value': value,
            'boundary': bool(row['boundary']), 'sensitive': bool(row['sensitive'] or extraction.SENSITIVE.search(value)),
            'plan_status': None, 'stated_at': message['created_at'], 'applies_from': None, 'applies_until': None,
            'dates_uncertain': False, 'target': None, 'excerpt': excerpt, 'corrects': row['id'], 'ends': ending}


def found(connection, companion, message, now) -> list[dict]:
    """Correction proposals the rules find in one user message."""
    everyone = people.known(connection, companion['id'])
    known = people.names(everyone)
    exclude = (companion['version']['definition']['name'].split()[0].casefold(),)
    proposals = []
    for sentence in extraction.sentences(message['text']):
        for reference, kind, words, value, replacement in statements(sentence, known, exclude):
            ignore = {stem(word) for word in reference_words(reference)} if not reference.get('self') else set()
            rows = [row for row in scope(connection, companion['id'], reference, now) if allowed(row, kind)]
            if row := target(rows, words, ignore, replacement):
                proposals.append(fields_for(row, value, message, sentence,
                                            ending=ends(row, value, sentence, replacement)))
    return proposals


def fingerprint(fields) -> str:
    return hashlib.sha256(f"correct|{fields['corrects']}|{fields['value'].casefold()}|{bool(fields['ends'])}"
                          .encode()).hexdigest()


def record(connection, companion, message, fields, source, rule, timestamp) -> int:
    """Store a correction once per message; one declined before is kept dismissed. Returns 1 when it now waits."""
    mark = fingerprint(fields)
    declined = optional(connection, "SELECT 1 FROM memory_candidates WHERE fingerprint=? AND status='declined' "
                        'AND companion_id=?', (mark, companion['id']))
    cursor = connection.execute(
        'INSERT OR IGNORE INTO memory_candidates (id, companion_id, timeline_id, message_id, source, rule, proposal, '
        'fingerprint, status, reason, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (identifier(), companion['id'], message['timeline_id'], message['id'], source, rule, encode(fields), mark,
         'dismissed' if declined else 'pending', 'declined_before' if declined else RULE, timestamp))
    return 0 if declined else cursor.rowcount


def current(connection, fields, now) -> dict | None:
    row = optional(connection, "SELECT * FROM memories WHERE id=? AND status='active'", (fields['corrects'],))
    return None if row is None or records.ended(row, now) else row


def apply(connection, fields, message_id, timestamp) -> tuple[dict | None, str]:
    """Keeping a correction: the memory it names is reworded as a new revision, or ended as history."""
    row = current(connection, fields, timestamp)
    if row is None:
        return None, 'correction_target_changed'
    if fields.get('ends'):
        until = max(fields['stated_at'], row['applies_from'] or '')
        connection.execute('UPDATE memories SET applies_until=?, updated_at=? WHERE id=?', (until, timestamp, row['id']))
        memory_id, outcome = row['id'], 'ended'
        bump_memory_revision(connection, timestamp)
    else:
        memory_id = records.revise(connection, records.get(connection, row['id']), timestamp,
                                   value=fields['value'])['id']
        outcome = 'corrected'
    connection.execute('INSERT OR IGNORE INTO memory_sources (memory_id, message_id) VALUES (?, ?)',
                       (memory_id, message_id))
    return records.get(connection, memory_id), outcome


def relevant(connection, companion_id, text, now, limit=KNOWN_LIMIT) -> list[dict]:
    """Current facts a message's words touch, so the model can say which one it corrects. Sensitive memories
    and boundaries are never sent."""
    words = stems(text)
    rows = many(connection, "SELECT id, layer, subject, subject_key, value, applies_until FROM memories "
                "WHERE companion_id=? AND status='active' AND layer='user_fact' AND boundary=0 AND sensitive=0",
                (companion_id,))
    scored = [(len(words & stems(f"{row['subject']} {row['value']}")), row) for row in rows
              if not records.ended(row, now)]
    scored = sorted((item for item in scored if item[0]), key=lambda item: item[0], reverse=True)[:limit]
    return [{key: row[key] for key in ('id', 'layer', 'subject', 'subject_key', 'value')} for _score, row in scored]


def label(row) -> str:
    return f"{row['subject']}: {row['value']}"


def named(known: list[dict], corrects) -> dict | None:
    """The sent memory a model's `corrects` names, by subject or by the line sent; anything else is refused."""
    if not isinstance(corrects, str):
        return None
    wanted = ' '.join(corrects.casefold().split())
    matches = [row for row in known
               if wanted in {' '.join(row['subject'].casefold().split()), ' '.join(label(row).casefold().split())}]
    return matches[0] if len(matches) == 1 else None


def same_subject(connection, companion_id, layer, key, now) -> dict | None:
    """The one current memory with this layer and subject, if there is exactly one."""
    rows = [row for row in many(connection, "SELECT * FROM memories WHERE companion_id=? AND status='active' "
                                'AND layer=? AND subject_key=?', (companion_id, layer, key))
            if not records.ended(row, now)]
    return rows[0] if len(rows) == 1 else None
