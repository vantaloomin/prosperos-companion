"""The scene keeps up (Hit List #100, v1.4): where an in-person meetup is now, and what they have on, from the chat.

Walking from dinner to the river, riding the bus back to the user's place, or putting a jacket round the companion's
shoulders happens only in the chat, so the app's own notes kept saying "Together at Lupa" and describing the
restaurant (Cairn probe, 2026-11-03). Rules follow it, no model: the action lines on both sides (*between asterisks*,
or the narration around quoted speech) from the start of the meetup are read for the phrases in
world/data/scene_moves.json.

Where they are:
- a place the city map knows, within NEAR_KM of where they were, becomes the new place;
- "my place" and "your place" become the right home;
- a bus, train, tram, ferry or car becomes "on the bus";
- anything else is "on the way to X" (a move) or "outside X" (an arrival somewhere the map doesn't know, or stepping
  out of where they were).
What they wear: things put on or taken off sit on top of today's outfit (companion/life/wardrobe.py), for the companion
and for what they know of the user ("the user's jacket around your shoulders").

Plans and questions are not moves ("we could walk to the river", "should we head to yours?"), and neither are
negations or the past. A move the app makes itself (Second location, companion/life/onward.py) wins when it fires: only
what was said after it counts. Nothing is stored: the scene is worked out from the meetup's messages each time
(cached by them), so an edit, a delete or a reroll corrects it. The one thing kept is the user's override: Back to
Lupa on the strip, for UNDO after a move, sets `scene_from` on the outing's place, and moves said before it no longer
count. When the meetup ends, everything goes back to normal.

Story mode (companion/story.py) reads the same moves from the story since the last place picked, for places only.
"""
import json
import re
from datetime import datetime, timedelta
from functools import lru_cache

from companion.clock import parse, stamp, zone
from companion.database import encode, many
from companion.errors import require
from companion.world import catalog

ACTIVE = True
UNDO = timedelta(minutes=2)  # How long Back to ... shows after a move made in the chat.
NEAR_KM = 1.5
OPENING_LEAD = timedelta(minutes=15)  # As memory/context.py: "just got here" before the start.
CACHE = 64
YOURS, THEIRS = '~yours', '~theirs'

ACTION = re.compile(r'\*([^*]+)\*')
SPEECH = re.compile(r'"[^"]*"|“[^”]*”')
CLAUSE = re.compile(r'[.!?;\n]+')
# Not a move: a plan, a wish, a question, a condition, the past, or a negation.
PLAN = re.compile(r"\b(?:could|should|shall|would|might|maybe|perhaps|let'?s|let us|wanna|want(?:s|ed)? to|"
                  r"gonna|about to|plan(?:s|ned|ning)? to|how about|what about|if|unless|once we|when we|before we|"
                  r"later|tomorrow|tonight|next (?:time|week)|some ?day|one day|another (?:day|time|night)|"
                  r"dream(?:s|ed)? of|imagine|thinking of|suggest(?:s|ed)?|offer(?:s|ed)? to)\b", re.IGNORECASE)
PAST = re.compile(r"\b(?:yesterday|last (?:night|week|time|year|month|summer|winter)|ago|used to|remember(?:s|ed)?|"
                  r"the other day|back then|that time|once upon)\b", re.IGNORECASE)
NEGATED = re.compile(r"\b(?:not|never|no longer|instead of|rather than|without)\b|n't\b", re.IGNORECASE)
# Where a destination stops: the end of the clause, or what they do next.
DEST_END = re.compile(r"\s*(?:,|\band\b|\bthen\b|\bwhere\b|\bwhile\b|\bto (?:get|see|grab|find|look|watch|sit|eat)\b|"
                      r"\buntil\b|\bfor\b|\bwith\b|\bas\b|\bso\b|\bjust\b|\bbecause\b|$)", re.IGNORECASE)
STARTS = re.compile(r"(?:(?i:the|a|an|that|this|our|my|your|his|her|their|some|one)\b|[A-Z0-9])")
# A thing, not a move ("tilts my head back to"), or a look, not a move ("looks back at the water").
NOUN_BEFORE = re.compile(r"\b(?:my|your|his|her|their|our|the|a|an|its|looks?|looked|looking|glances?|glanced|"
                         r"stares?|stared|smiles?|smiled|grins?|grinned|nods?|nodded|waves?|waved|points?|pointed|"
                         r"gazes?|gazed|peers?|peered|laughs?|laughed|squints?|squinted|winks?|winked|blinks?|"
                         r"blinked|frowns?|frowned|turns?|turned|leans?|leaned|smirks?|smirked|calls?|called|"
                         r"yells?|shouts?|whispers?|says?|said|tosses|throws?|threw|reaches?|reached|hands?|"
                         r"handed)\s+$", re.IGNORECASE)
ARTICLE = re.compile(r"^(?:the|a|an|that|this|our|some|little|old)\s+", re.IGNORECASE)
VEHICLES = {'bus': 'on the bus', 'train': 'on the train', 'subway': 'on the subway', 'metro': 'on the metro',
            'tram': 'on the tram', 'streetcar': 'on the streetcar', 'ferry': 'on the ferry', 'boat': 'on the boat',
            'cab': 'in a cab', 'taxi': 'in a cab', 'uber': 'in a cab', 'car': 'in the car', 'carriage': 'in a carriage'}
HOME_WORDS = r"(?:place|apartment|flat|house|home|couch|sofa|bed|bedroom|room|kitchen|living room|front door|door|" \
             r"building|porch|garden|balcony)"
# Spots inside a place: walking to the bench or the bar is not going anywhere.
SPOTS = re.compile(r"\b(?:bench|table|booth|counter|bar|window|door|doorway|corner|railing|edge|seat|chair|stool|"
                   r"couch|sofa|bed|floor|stairs?|steps|kitchen|bathroom|restroom|toilet|dance ?floor|stage|"
                   r"water|shore|fountain|fire|fireplace|car park|parking|curb|kerb|sidewalk|pavement|street|road|"
                   r"crosswalk|light|lamp|tree|wall|gate|entrance|exit|line|queue|register|till|front|back|end|"
                   r"top|bottom|middle|side|other side|outside|inside|each other|me|you|him|her|them|it|there|here|"
                   r"bus stop|station|platform)\b", re.IGNORECASE)
GENERIC = {'park', 'bar', 'pub', 'cafe', 'café', 'restaurant', 'river', 'beach', 'shop', 'store', 'market', 'square',
           'street', 'bridge', 'pier', 'museum', 'gallery', 'club', 'hotel', 'church', 'library', 'place', 'spot',
           'centre', 'center', 'city', 'town', 'district', 'quarter', 'harbor', 'harbour', 'garden', 'gardens', 'lake',
           'hill', 'the', 'of', 'and', 'on', 'at', 'in', 'old', 'new', 'little', 'water', 'view', 'sky', 'skyline',
           'lights', 'light', 'rain', 'sun', 'moon', 'stars', 'night', 'air', 'crowd', 'people', 'music', 'food',
           'tower', 'house', 'hall', 'building', 'avenue', 'way', 'road', 'lane', 'mile', 'point', 'side', 'top',
           'great', 'big', 'grand', 'main', 'north', 'south', 'east', 'west', 'downtown', 'uptown', 'corner'}
LEAVING = re.compile(r'\b(?:out|outside|leave|leaves|left)\b')
CLOTHES = re.compile(r"\b(?:jacket|coat|blazer|cardigan|sweater|jumper|hoodie|sweatshirt|scarf|shawl|wrap|gloves?|"
                     r"mittens?|hat|cap|beanie|shoes?|boots?|heels|sneakers|trainers|sandals|slippers|socks|tie|"
                     r"bow ?tie|belt|vest|waistcoat|shirt|blouse|t-?shirt|top|dress|skirt|jeans|trousers|pants|"
                     r"shorts|sunglasses|glasses|necklace|earrings|bracelet|ring|watch|cloak|cape|robe|apron|"
                     r"stockings|tights|uniform|suit|tux|tuxedo|overcoat|raincoat|parka|fleece|poncho|helmet|mask|"
                     r"jersey|bra|lingerie)\b", re.IGNORECASE)
OWNER = re.compile(r"^(?:(?P<who>my|your|his|her|their|the|a|an|[A-Z][a-z]+'s)\s+)?(?P<item>.+)$")
TARGET = re.compile(r"\b(?:over|around|round|across|onto|on|about)\s+(?P<who>my|your|his|her|their|me|you|him|them)\b",
                    re.IGNORECASE)
SUBJECT = re.compile(r"\b(?P<who>i|you|we|he|she|they)\s+(?:\w+\s+)?$", re.IGNORECASE)


@lru_cache(maxsize=1)
def bank() -> dict:
    """The phrase bank, each kind as one pattern, longest phrase first."""
    found = json.loads((catalog.DATA / 'scene_moves.json').read_text(encoding='utf-8'))
    return {kind: re.compile(r'\b(?:' + '|'.join(re.escape(text) for text in sorted(found[kind], key=len,
                                                                                         reverse=True)) + r')\b',
                             re.IGNORECASE) for kind in ('moves', 'arrivals', 'put_on', 'take_off')}


# --- Reading the lines --------------------------------------------------------------------------------------------

def actions(text: str, narrated: bool = False) -> list[str]:
    """The action parts of a message: *between asterisks*, else the narration around quoted speech, else nothing
    (plain words in person are speech). `narrated` (Story mode) reads a whole line with no asterisks."""
    spans = ACTION.findall(text or '')
    if spans:
        return spans
    if SPEECH.search(text or '') or narrated:
        return [SPEECH.sub(' , ', text or '')]
    return []


def clauses(text: str, narrated: bool = False) -> list[str]:
    """The sentences of a message's action parts that say what happens now."""
    found = []
    for part in actions(text, narrated):
        for sentence in CLAUSE.split(part):
            if sentence.strip() and not (PLAN.search(sentence) or PAST.search(sentence) or NEGATED.search(sentence)):
                found.append(sentence.strip())
    return found


def destination(rest: str) -> str:
    """The words after a move: 'the riverwalk' from 'the riverwalk, hand in hand'."""
    end = DEST_END.search(rest)
    words = rest[:end.start() if end else len(rest)].strip(' ,-')
    return ' '.join(words.split()[:6])


def side(word: str, speaker: str, companion_words: tuple[str, ...]) -> str:
    """Whose a possessive or pronoun is: 'user' or 'companion'. `speaker` wrote the line; in the companion's lines a
    third person who is not them is the user."""
    word = (word or '').lower()
    other = 'companion' if speaker == 'user' else 'user'
    if word in ('my', 'me', 'i', 'mine'):
        return speaker
    if word in ('your', 'you', 'yours'):
        return other
    if speaker == 'user':
        return 'companion'
    return 'companion' if word in companion_words or word.endswith("'s") else 'user'


# --- Where ------------------------------------------------------------------------------------------------------

def home_of(words: str, speaker: str, companion_words: tuple[str, ...]) -> str | None:
    """'yours' (the user's place) or 'theirs' (the companion's) for "my place", "your apartment", "back to mine"."""
    found = re.search(rf"\b(?P<who>my|your|his|her|their)\s+(?:own\s+)?{HOME_WORDS}\b|\b(?P<own>mine|yours)\b",
                      words, re.IGNORECASE)
    if not found:
        return None
    who = side(found.group('who') or found.group('own'), speaker, companion_words)
    return 'yours' if who == 'user' else 'theirs'


def vehicle(words: str) -> str | None:
    found = re.search(r'\b(' + '|'.join(VEHICLES) + r')\b', words, re.IGNORECASE)
    return VEHICLES[found.group(1).lower()] if found else None


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9']+", text.lower()))


def near(data: dict, start: dict | None, item: dict) -> bool:
    """Within NEAR_KM of where they were, by neighbourhood (the same one always is)."""
    if not start or not start.get('neighborhood'):
        return True
    hoods = {hood['id']: hood for hood in data.get('neighborhoods', ())}
    by_name = {hood['name']: hood for hood in data.get('neighborhoods', ())}
    origin = hoods.get(start['neighborhood']) or by_name.get(start['neighborhood'])
    there = hoods.get(item.get('neighborhood'))
    if not origin or not there or origin['id'] == there['id']:
        return bool(origin and there)
    return 'lat' in origin and 'lat' in there and catalog.distance_km(origin, there) <= NEAR_KM


def known_place(data: dict | None, words: str, start: dict | None) -> dict | None:
    """The place the city map knows by these words, near where they were: its whole name said, or every telling word
    of what was said in its name ('the riverwalk' for Chicago Riverwalk)."""
    if not data or not words:
        return None
    said = tokens(ARTICLE.sub('', words.lower()))
    telling = said - GENERIC
    found = [item for item in data.get('places', ()) if len(item['name']) >= 4 and (
        re.search(rf"\b{re.escape(item['name'])}\b", words, re.IGNORECASE) or
        telling and telling <= tokens(item['name']))]
    found = [item for item in found if item['id'] != (start or {}).get('id') and near(data, start, item)]
    return min(found, key=lambda item: len(item['name'])) if found else None


def where_to(data, words: str, how: str, phrase: str, start: dict, people: tuple) -> dict | None:
    """Where a move or an arrival puts them, or None when it is no move (the bench, the other side of the table)."""
    speaker, companion_words = people
    # "walk out of Lupa", "reaches over", "head back to look at the skyline": no place named.
    if not re.match(r'(?:mine|yours)\b', words, re.IGNORECASE) and (
            not STARTS.match(words) or re.match(r'(?:of|from)\b', words, re.IGNORECASE)):
        words = ''
    if (home := home_of(words, speaker, companion_words)) is not None:
        return {'kind': home}
    if (item := known_place(data, words, start)) is not None:
        return {'kind': 'place', 'item': item}
    if not words:
        leaving = how == 'moves' and LEAVING.search(phrase.lower())
        ride = vehicle(phrase)
        return {'kind': 'transit', 'label': ride} if ride else \
            {'kind': 'outside', 'label': f"outside {start['name']}"} if leaving else None
    if SPOTS.search(' '.join(ARTICLE.sub('', words.lower()).split()[:3])):
        return None
    if (ride := vehicle(f'{phrase} {words}')) is not None:
        return {'kind': 'transit', 'label': ride}
    name = ARTICLE.sub('', words) if words.lower().startswith(('our ', 'that ', 'this ')) else words
    return {'kind': 'way' if how == 'moves' else 'outside',
            'label': f"on the way to {name}" if how == 'moves' else f"outside {name}"}


def moves_in(sentence: str, data, start: dict, people: tuple) -> list[dict]:
    """Each move or arrival a sentence makes, in order."""
    found = []
    for how, pattern in (('moves', bank()['moves']), ('arrivals', bank()['arrivals']), ('moves', TAKING)):
        for match in pattern.finditer(sentence):
            if NOUN_BEFORE.search(sentence[:match.start()]):
                continue  # "tilts my head back to", "the walk to": a thing, not a move.
            words = destination(sentence[match.end():])
            if (to := where_to(data, words, how, match.group(0), start, people)) is not None:
                found.append((match.start(), to))
    return [to for _at, to in sorted(found, key=lambda pair: pair[0])]


# --- Wearing -------------------------------------------------------------------------------------------------------

def garment(words: str) -> tuple[str | None, str]:
    """('your', 'jacket') from 'your jacket over'; (None, '') with no clothing in it."""
    words = destination(re.split(r'\b(?:over|around|round|across|onto|on|off|about|from|to)\b', words)[0])
    if not CLOTHES.search(words):
        return None, ''
    found = OWNER.match(words.strip())
    item = re.sub(r'(?:\s+(?:up|on|off|back|down|tight|tighter|higher|closer|in|out|away|aside))+$', '',
                  found.group('item').strip().lower())
    return (found.group('who') or None), item


def subject(sentence: str, start: int, speaker: str, companion_words: tuple[str, ...]) -> str:
    """Who does it: the pronoun just before the phrase, else whoever wrote the line."""
    found = SUBJECT.search(sentence[:start])
    if not found or found.group('who').lower() == 'we':
        return speaker
    word = found.group('who').lower()
    if word in ('i', 'you'):
        return side(word, speaker, companion_words)
    return 'companion' if speaker == 'companion' and word in companion_words else side(word, speaker, companion_words)


def changes_in(sentence: str, people: tuple) -> list[dict]:
    """What a sentence puts on or takes off: {'on': bool, 'who', 'item', 'owner', 'giving'}, in order."""
    found, last_off = split_off(sentence, people), None
    last_off = found[-1] if found else None
    for how in ('take_off', 'put_on'):
        for match in bank()[how].finditer(sentence):
            change = change_of(sentence, match, how == 'put_on', last_off, people)
            if change:
                found.append(change)
                last_off = change if how == 'take_off' else last_off
    return sorted(found, key=lambda change: change['at'])


def split_off(sentence: str, people: tuple) -> list[dict]:
    """'kicks the boots off', 'pulls it off over my head': the thing between the verb and 'off'."""
    speaker, words = people
    found = []
    for match in SPLIT_OFF.finditer(sentence):
        if FROM_THING.match(sentence[match.end():]):
            continue  # "shrugs the coat off the back of the chair": it was not on them.
        thing = match.group('thing')
        if re.fullmatch(r'(?:it|them)', thing, re.IGNORECASE):
            named = list(CLOTHES.finditer(sentence[:match.start()]))
            thing = named[-1].group(0) if named else ''
        who_word, item = garment(thing)
        if item:
            doer = subject(sentence, match.start(), speaker, words)
            owner = side(who_word, speaker, words) if who_word and who_word.lower() not in ('the', 'a', 'an') else doer
            found.append({'at': match.start(), 'on': False, 'who': doer, 'item': item, 'owner': owner,
                          'giving': False})
    return found


def change_of(sentence: str, match, putting: bool, last_off: dict | None, people: tuple) -> dict | None:
    """One phrase's change, or None when no clothing is named (a hand on a shoulder) or nothing says who wears it."""
    speaker, words = people
    rest, phrase = sentence[match.end():], match.group(0).lower()
    if putting and re.match(r'\s*(?:\w+\s+){0,3}?off\b', rest, re.IGNORECASE):
        return None  # "pulls it off over her head" takes it off.
    who_word, item = garment(rest)
    owner = None
    if putting and not item and re.match(r'\s*(?:it|them)\b', rest) and last_off:
        item, owner = last_off['item'], last_off['owner']  # "takes off his jacket and drapes it over her".
    target = TARGET.search(rest[:80])
    direct = phrase.endswith((' on', ' into', ' up')) or phrase.split()[0] in ('don', 'dons', 'donned', 'donning')
    if not item or putting and not target and not direct:
        return None
    if putting and not direct and owner is None and side(target.group('who'), speaker, words) == \
            subject(sentence, match.start(), speaker, words) and (who_word or 'the').lower() in OWN_WORDS:
        return None  # "pulls her scarf up over her nose": their own, already on.
    doer = subject(sentence, match.start(), speaker, words)
    giving = phrase.split()[0] in GIVING
    wearer = side(target.group('who'), speaker, words) if putting and target else doer
    if owner is None:
        owner = side(who_word, speaker, words) if who_word and who_word.lower() not in ('the', 'a', 'an') else \
            (doer if giving else wearer)
    return {'at': match.start(), 'on': putting, 'who': wearer, 'item': item, 'owner': owner, 'giving': giving}


FROM_THING = re.compile(r"\s+(?:of\s+)?(?:the|a|its)\s+(?:back|hook|rack|hanger|chair|seat|peg|floor|table|bed|couch|"
                        r"sofa|railing|counter)\b", re.IGNORECASE)
# Taking the other one somewhere: "walks you back to his place", "pulls her over to the bar".
TAKING = re.compile(r"\b(?:walk|walks|walked|walking|take|takes|took|taking|lead|leads|led|leading|bring|brings|"
                    r"brought|bringing|drive|drives|drove|driving|guide|guides|guided|steer|steers|steered|pull|pulls|"
                    r"pulled|tug|tugs|tugged)\s+(?:you|him|her|them|me|us)\s+(?:(?:back|over|down|up|out|along|"
                    r"across|home)\s+)?to\b", re.IGNORECASE)
OWN_WORDS = ('my', 'his', 'her', 'their', 'the')
SPLIT_OFF = re.compile(r"\b(?:take|takes|took|taking|kick|kicks|kicked|kicking|pull|pulls|pulled|pulling|slip|slips|"
                       r"slipped|slipping|shrug|shrugs|shrugged|shrugging|peel|peels|peeled|peeling|tug|tugs|tugged|"
                       r"tugging|toss|tosses|tossed|tossing|yank|yanks|yanked|yanking)\s+"
                       r"(?P<thing>(?:(?:my|your|his|her|their|the|a|an)\s+)?(?:\w+\s+){0,2}?\w+)\s+off\b",
                       re.IGNORECASE)
GIVING = ('hand', 'hands', 'handed', 'handing', 'give', 'gives', 'gave', 'giving', 'return', 'returns', 'returned',
          'returning', 'pass', 'passes', 'passed', 'passing')


def whose(state: dict, change: dict, handed: dict | None) -> tuple[dict, dict | None]:
    """Whose it really is: taking off a borrowed jacket takes off the lender's, and putting "it" back on someone
    in the same sentence puts that one on."""
    borrowed = next((item for item in state[change['who']]['on'] if item['item'] == change['item']), None)
    if not change['on'] and borrowed:
        return {**change, 'owner': borrowed['owner']}, {'item': change['item'], 'owner': borrowed['owner']}
    if change['on'] and handed and handed['item'] == change['item']:
        return {**change, 'owner': handed['owner']}, None
    return change, handed


def wear(state: dict, change: dict, when: str) -> None:
    """Keep a change: putting on takes it out of 'off'; taking off a borrowed thing just hands it back."""
    who = state[change['who']] if not change['giving'] else None
    if change['giving']:  # Handing it back: whoever had it on no longer does.
        for person in state.values():
            person['on'] = [item for item in person['on'] if item['item'] != change['item']]
        return
    if change['on']:
        back_on = change['owner'] == change['who'] and change['item'] in who['off']
        who['off'] = [item for item in who['off'] if item != change['item']]
        who['on'] = [item for item in who['on'] if item['item'] != change['item']] + (
            [] if back_on else [{'item': change['item'], 'owner': change['owner'], 'since': when}])
        return
    if any(item['item'] == change['item'] for item in who['on']):
        who['on'] = [item for item in who['on'] if item['item'] != change['item']]
    elif change['item'] not in who['off']:
        who['off'].append(change['item'])


# --- The scene now -----------------------------------------------------------------------------------------------

def companion_words(companion: dict) -> tuple[str, ...]:
    """How the companion's own lines speak of them: their name and their pronouns."""
    definition = companion['version']['definition']
    name = definition.get('name', '').split()
    pronouns = (definition.get('pronouns') or 'they/them').lower().replace(' ', '')
    third = tuple(part for part in re.split(r'[/,]', pronouns) if part)
    possessive = {'he': ('his',), 'she': ('her', 'hers'), 'they': ('their', 'theirs')}
    extra = tuple(word for first in third for word in possessive.get(first, ()))
    return tuple(word.lower() for word in (*name[:1], *third, *extra))


def read(rows: list[dict], data, start: dict, words: tuple[str, ...], narrated: bool = False) -> dict:
    """The scene the lines make: {'move': {...} or None, 'wearing': {...}} over `rows` (oldest first)."""
    found = {'move': None, 'wearing': {'companion': {'on': [], 'off': []}, 'user': {'on': [], 'off': []}}}
    moved_at = None
    for index, row in enumerate(rows):
        speaker = 'user' if row['role'] == 'user' else 'companion'
        for sentence in clauses(row['text'], narrated or row['role'] == 'narrator'):
            for to in moves_in(sentence, data, start, (speaker, words)):
                found['move'], moved_at = {**to, 'message_id': row['id'], 'at': row['created_at']}, index
            handed = None
            for change in changes_in(sentence, (speaker, words)):
                change, handed = whose(found['wearing'], change, handed)
                wear(found['wearing'], change, row['created_at'])
    return arrived(found, rows, moved_at)


def arrived(found: dict, rows: list[dict], index: int | None) -> dict:
    """On the way somewhere the map doesn't know, and the talk has gone on past the reply to it: they are there."""
    move = found['move']
    later = index is not None and any(row['role'] == 'user' for row in rows[index + 1:])
    if move and move['kind'] == 'way' and later:
        found['move'] = {**move, 'kind': 'there', 'label': move['label'].replace('on the way to ', 'at ', 1)}
    return found


@lru_cache(maxsize=CACHE)
def cached(key: str, rows: str, data_key: str, start: str, words: tuple[str, ...]) -> str:
    """read() by the meetup's messages: an edit, a delete or a reroll is a new key."""
    return encode(read(json.loads(rows), DATA.get(data_key), json.loads(start), words))


DATA: dict[str, dict] = {}  # The city data a cached read used, by its id (kept small: one city per world).


def rows_since(connection, timeline_id: str, since: str) -> list[dict]:
    return many(connection, "SELECT id, role, text, created_at FROM messages WHERE timeline_id=? AND active=1 AND "
                "status='complete' AND redacted_at IS NULL AND created_at>=? ORDER BY seq", (timeline_id, since))


def read_from(outing: dict, raw: dict, timezone: str, now: datetime) -> str:
    """Where reading starts: the meetup's start, else after the app's own move (Second location) or the user's Back
    at ... (`scene_from`)."""
    from companion.life import onward, outings
    begun = outings.window(raw, timezone)[0] - OPENING_LEAD
    marks = [stamp(begun)]
    stop = onward.stop_of(raw)
    if stop and onward.moved(raw, timezone, now):
        marks.append(stamp(onward.move_time(raw, timezone)))
    if raw['place'].get('scene_from'):
        marks.append(raw['place']['scene_from'])
    return max(marks)


def scene(connection, companion: dict, raw: dict, here: dict, now: datetime) -> dict:
    """The scene now for an outing under way: {'move', 'wearing'} with times; nothing moved or worn while apart."""
    from companion.life import outings
    empty = {'move': None, 'wearing': {'companion': {'on': [], 'off': []}, 'user': {'on': [], 'off': []}}}
    if not ACTIVE or raw['ended_at'] or raw['activity'] in ('wedding', 'big-day'):
        return empty
    timezone = companion['version']['timezone']
    begun = stamp(outings.window(raw, timezone)[0] - OPENING_LEAD)
    rows = rows_since(connection, companion['active_timeline_id'], begun)
    if not rows:
        return empty
    data = outings.city_data(connection, companion['version']['definition'])
    data_key = data['id'] if data else ''
    if data:
        DATA[data_key] = data
    start = {key: here['place'].get(key) for key in ('id', 'name', 'neighborhood')}
    words = companion_words(companion)
    worn = json.loads(cached(f"{raw['id']}:wear", encode(rows), data_key, encode(start), words))['wearing']
    since = read_from(here, raw, timezone, now)
    moved = [row for row in rows if row['created_at'] > since or row['created_at'] == since and
             since == begun]
    found = json.loads(cached(raw['id'], encode(moved), data_key, encode(start), words))['move'] if moved else None
    return {'move': found, 'wearing': worn}


# --- What reads it ----------------------------------------------------------------------------------------------

def applied(connection, companion: dict, raw: dict, here: dict, now: datetime) -> tuple[dict, dict]:
    """The outing as it stands with the chat's move on it (place, activity, came_from, moved_at, and `scene` for the
    strip), and the scene itself."""
    from companion.life import outings
    found = scene(connection, companion, raw, here, now)
    move = found['move']
    if not move:
        return here, found
    timezone = companion['version']['timezone']
    at = parse(move['at']).astimezone(zone(timezone)).strftime('%H:%M')
    came = {'name': here['place']['name'], 'activity': here['activity'],
            'neighborhood': here['place'].get('neighborhood', '')}
    undo = now - parse(move['at']) < UNDO
    strip = {'back': undo, 'to': here['place']['name'], 'kind': move['kind']}
    if move['kind'] == 'place':
        data = outings.city_data(connection, companion['version']['definition'])
        place = {**outings.place_view(move['item'], data), 'spots': []}  # Just got there: not sat anywhere yet.
        walked = move['item']['kind'] in outings.kinds('walk') or move['item'].get('setting') == 'outdoor'
        return {**here, 'place': place, 'activity': 'walk' if walked else outings.activity_for_place(move['item']),
                'came_from': came,
                'moved_at': at, 'next': None, 'scene': strip}, found
    if move['kind'] in ('yours', 'theirs'):
        name = companion['version']['definition']['name']
        place = {'id': YOURS, 'name': "the user's place", 'kind': 'your-home'} if move['kind'] == 'yours' else \
            {'id': THEIRS, 'name': f"{name}'s place", 'kind': 'home'}
        return {**here, 'place': place, 'activity': 'visit-yours' if move['kind'] == 'yours' else 'visit-in',
                'came_from': came, 'moved_at': at, 'next': None, 'scene': strip}, found
    place = {'id': '~scene', 'name': move['label'], 'kind': 'scene', 'label': move['label']}
    return {**here, 'place': place, 'came_from': came, 'moved_at': at, 'next': None, 'scene': strip}, found


def right_now(connection, companion: dict, now: datetime) -> str | None:
    """'with the user, at Chicago Riverwalk (since 20:40, after The Berghoff)' for the day's Right now line, once the
    chat has taken them somewhere; None otherwise."""
    from companion.life import onward, together
    raw = together.together_now(connection, companion, now)
    if not raw:
        return None
    current = applied(connection, companion, raw, onward.here(raw, companion['version']['timezone'], now), now)[0]
    if not current.get('scene'):
        return None
    place = current['place']
    where = place.get('label') or ("at the user's place" if place['id'] == YOURS else f"at {place['name']}")
    return f"with the user, {where} (since {current['moved_at']}, after {current['came_from']['name']})"


def on_the_move_line(outing: dict, timezone: str, now: datetime) -> str:
    """The scene line on a bus, on the way somewhere or outside a place."""
    from companion.life import outings
    start = outings.window(outing, timezone)[0]
    return (f"- Right now you and the user are {outing['place']['label']}, together in person: you met up at "
            f"{start.astimezone(zone(timezone)).strftime('%H:%M')} at {outing['came_from']['name']} and left there at "
            f"{outing['moved_at']}. Talk as if you are there together, face to face, not texting.")


def on_text(item: dict, person: str, timezone: str) -> str:
    """"wearing the user's jacket since 20:44 (not the user)" for one thing put on."""
    since = parse(item['since']).astimezone(zone(timezone)).strftime('%H:%M')
    if person == 'companion':
        return f"wearing the user's {item['item']} since {since} (not the user)" if item['owner'] == 'user' else \
            f"put on your {item['item']} at {since}"
    return f"wearing your {item['item']} since {since} (not you)" if item['owner'] == 'companion' else \
        f"put on their {item['item']} at {since}"


def off_text(item: str, person: str, other: list[dict]) -> str:
    """"took off their jacket (you are wearing it now)"."""
    worn = any(thing['item'] == item and thing['owner'] == person for thing in other)
    whose = 'your' if person == 'companion' else 'their'
    return f"took off {whose} {item}{' (' + ('the user is' if person == 'companion' else 'you are') + ' wearing it now)' if worn else ''}"


def wearing_lines(outing: dict, found: dict, timezone: str) -> list[tuple[str, str]]:
    """What each of them has put on or taken off since they met up, on top of today's clothes."""
    result, worn = [], found['wearing']
    for person, lead in (('companion', "- Your clothes since you met up, on top of today's outfit:"),
                         ('user', "- The user's clothes since you met up:")):
        other = worn['user' if person == 'companion' else 'companion']['on']
        parts = [on_text(item, person, timezone) for item in worn[person]['on']]
        parts += [off_text(item, person, other) for item in worn[person]['off']]
        if parts:
            result.append((f"outing:{outing['id']}:wearing:{person}", f"{lead} {'; '.join(parts)}."))
    return result


def wearing_hint(found: dict) -> str:
    """For a picture taken during the meetup: what the companion has on beyond today's outfit."""
    state = found['wearing']['companion']
    parts = [f"{'a borrowed' if item['owner'] == 'user' else 'their'} {item['item']} on" for item in state['on']]
    parts += [f"{item} off" for item in state['off']]
    return f"{', '.join(parts)[:1].upper()}{', '.join(parts)[1:]}." if parts else ''


def back(connection, companion: dict, outing_id: str, now: datetime) -> dict:
    """Back to where they were: the move said in the chat no longer counts (for UNDO after it)."""
    from companion.life import onward, outings, together
    raw = outings.owned(connection, companion, outing_id)
    timezone = companion['version']['timezone']
    require(raw['status'] == 'planned' and not raw['ended_at'] and outings.state(raw, timezone, now) == 'now',
            'You are not together right now.', 409)
    found = scene(connection, companion, raw, onward.here(raw, timezone, now), now)
    require(bool(found['move']) and now - parse(found['move']['at']) < UNDO, 'That can no longer be undone.', 409)
    connection.execute('UPDATE outings SET place=? WHERE id=?',
                       (encode({**raw['place'], 'scene_from': found['move']['at']}), outing_id))
    return together.view(connection, companion, now)


# --- Story mode ----------------------------------------------------------------------------------------------------

def story_place(data: dict, place: dict, rows: list[dict]) -> dict:
    """Story mode: the place the story's own lines have moved to since the last place was picked, or `place`."""
    if not ACTIVE:
        return place
    since = max((index for index, row in enumerate(rows) if row['role'] == 'scene'), default=-1)
    told = [row for row in rows[since + 1:] if row['role'] in ('user', 'narrator') and row.get('status',
                                                                                              'complete') == 'complete']
    start = {'id': place['id'], 'name': place['name'], 'neighborhood': place['neighborhood']}
    found = read(told, data, start, ('they',), narrated=True)['move']
    return found['item'] if found and found['kind'] == 'place' else place
