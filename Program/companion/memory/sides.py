"""Which side of life a reply's context carries while Settings > Realism > Adult side of life is on (v0.15).

Each reply's context carries either the family lines (children in the circle, the pair's own child) or the adult
side's lines (companion/world/intimacy.py), never both. A reply whose conversation, author's note or picture reads
intimate keeps the adult side and drops every line about a child, as v0.14 did for every reply; any other reply drops
the adult side's lines and keeps the family. Rules only, never a model, and it fails closed: anything unsure, or that
cannot be read, counts as intimate. A group chat reply always counts as intimate.
"""
import re
from functools import cache

from companion import authors_note
from companion.images import content
from companion.world import intimacy

# Not intimate in themselves: an injury reads "not confidently safe" for a picture, not for a reply.
NOT_INTIMATE = {r'bloody', r'blood', r'wounds?', r'injur(y|ies|ed)'}
# Words a chat drifting that way uses, beyond what a picture request would.
CHAT = (r'kiss\w*', r'make ?outs?', r'cuddl\w*', r'snuggl\w*', r'caress\w*', r'moan\w*', r'grind\w*', r'straddl\w*',
        r'thighs?', r'lips', r'tongues?', r'necks?', r'bedroom', r'(?:in|into|to|back to) bed', r'the sheets',
        r'unzip\w*', r'unbutton\w*', r'shirtless', r'panties', r'bra', r'boxers', r'turn(?:s|ed)? (?:me|you) on',
        r'turned on', r'want you(?! to)', r'need you(?! to)', r'take me', r'touch(?:es|ed|ing)? (?:me|you)',
        r'your body', r'my body', r'on top of (?:me|you)', r'shiver\w*', r'whimper\w*', r'pin(?:s|ned)? (?:me|you)',
        r'tie (?:me|you) up', r'spank\w*', r'collar', r'naughty', r'crav(?:e|ing) you',
        # More words and phrasings, slang and a few other languages.
        r'fu+c?k\w*', r'fck\w*', r'phuck\w*', r'shag(?:ged|ging)', r'shag (?:me|you)',
        r'screw(?:s|ed|ing)? (?:me|you)', r'bang(?:s|ed|ing)? (?:me|you)', r'seggs', r'secks', r'sext(?:s|ed|ing)?',
        r'nudes?', r'ma(?:ke|kes|de|king) love', r'fool(?:s|ed|ing)? around', r'frisky', r'ravish\w*',
        r'lust(?:s|ful|ing|y)?', r'have (?:my|your) way with', r'netflix and chill',
        r'(?:im|i am|getting|get you|make me|making me|so) wet', r'wet for (?:me|you)', r'(?:rock|getting) hard',
        r'hard for (?:me|you)', r'make (?:me|you) hard', r'hard ?on', r'boners?', r'erections?',
        r'lick(?:s|ed|ing)? (?:me|you|my|your|it)', r'suck(?:s|ed|ing)? (?:me|you|my|your|on|it)',
        r'rid(?:e|es|ing) (?:me|you)', r'go(?:es|ing)? down on', r'went down on', r'blow (?:me|you)', r'dicks?',
        r'cocks?', r'puss(?:y|ies)', r'clit\w*', r'cum(?:s|ming|med)?',
        r'(?:inside|in) (?:me|you) (?:tonight|now|deep)', r'inside (?:me|you)', r'come for (?:me|you)',
        r'make (?:me|you) come', r'tits?', r'titties', r'boobies', r'booty', r'butt(?:ocks)?', r'ass(?:es)?', r'arse',
        r'strip(?:s|ped)? (?:for|off|down)', r'take (?:it|this|that|them|everything|(?:my|your) \w+) off',
        r'clothes off', r'wearing nothing', r'what (?:im|i am) wearing', r'(?:spend|stay) the night',
        r'sle(?:ep|pt|eping) with (?:me|you)', r'l(?:ie|ay|ying) (?:down )?with me',
        r'(?:shower|bath|bathe|tub)\w* (?:together|with me|with you)', r'massag\w* (?:me|you|my|your)',
        r'bite (?:me|my|your)', r'nibbl\w* (?:on )?(?:my|your) (?:ears?|necks?|lips?)', r'choke (?:me|you)',
        r'handcuff\w*', r'blindfold\w*', r'kink\w*', r'submissive', r'domme', r'safe ?words?', r'grop\w*', r'fondl\w*',
        r'hump(?:s|ed|ing)?', r'thrust\w*', r'climax\w*', r'pleasur(?:e|ing) (?:me|you)', r'hickey\w*', r'smooch\w*',
        r'snog\w*', r'necking', r'nighties?', r'negligee', r'lap ?dances?', r'quickies?', r'booty call',
        r'one night stand', r'friends with benefits', r'doggy ?style', r'fantasi[sz]\w*',
        r'(?:my|your) fantas(?:y|ies)', r'talk(?:ing)? dirty', r'dirty talk',
        r'(?:you(?:re| re| are)?|looking|look so) (?:so )?hot', r'hot for (?:me|you)',
        r'(?:feeling|get|getting) spicy', r'kis+(?:e[sd]?|y|ing)?', r'b[eé]same', r'besa(?:r|me)', r'baise\w*',
        r'l amour', r'follar', r'ficken', r'k[uü]ss\w*', r'bacia\w*')
# Emoji that read intimate in a chat (they are not words, so they are looked for before anything is folded).
EMOJI = re.compile('[\U0001F346\U0001F351\U0001F4A6\U0001F445\U0001F975\U0001F608\U0001FAE6\U0001F51E'
                   '\U0001F48B\U0001F60F]')
# Letters written as numbers or symbols, folded back so 's3x' or 'f*ck' reads as itself.
LEET = str.maketrans({'3': 'e', '0': 'o', '1': 'i', '4': 'a', '5': 's', '@': 'a', '$': 's', '*': ''})


@cache
def pattern() -> re.Pattern:
    """Every word that makes a reply read intimate: a picture's sexual, nude and unsure words, the chat's own, and
    the adult side's interests (companion/world/data/intimacy.json)."""
    terms = [*content.SEXUAL, *content.NUDITY, *(term for term in content.UNCERTAIN if term not in NOT_INTIMATE), *CHAT]
    terms += [re.escape(content.normalize(entry['label'])) for entry in intimacy.bank()['interests']]
    return re.compile(r'\b(?:' + '|'.join(terms) + r')\b')


def reads_intimate(texts) -> bool:
    """Whether any of these reads intimate: as written, with letters written as numbers or symbols read back, and
    with a letter drawn out ('sooo') read once."""
    text = ' '.join(text for text in texts if text)
    if EMOJI.search(text):
        return True
    folded = text.casefold().translate(LEET)
    found = pattern()
    return any(found.search(content.normalize(variant)) for variant in
               (text, folded, re.sub(r'(\w)\1+', r'\1', folded)))


# The character's own words, in every reply's context.
OWN = ('identity', 'personality', 'voice', 'background', 'appearance', 'routine', 'location', 'history_together')
# A child said without their name, in the conversation.
CHILD = re.compile(r"\b(?:(?:our|the|my|your|his|her|their) (?:daughters?|sons?|kids?|kiddos?|child|children|"
                   r"little ones?|toddlers?|newborns?|infants?)|(?:our|the) bab(?:y|ies))\b", re.IGNORECASE)

# A context line about a child without their name, left out of a reply that doesn't carry the family lines.
CHILD_WORDS = (r'(?i:\b(?:daughters?|sons?|kids?|kiddos?|child|children|childcare|toddlers?|newborns?|infants?|'
               r'bab(?:y|ies)|nursery|daycare|bedtimes?|school run|(?:grand|step|god)(?:child\w*|daughters?|sons?)|'
               r'nieces?|nephews?)\b)')


def own_words(companion: dict) -> list[str]:
    definition = companion['version']['definition']
    return [str(definition.get(key) or '') for key in OWN]


def family_reply(connection, companion: dict, recent: list[dict], group: dict | None, photo: dict | None) -> bool:
    """Whether this reply carries the family lines instead of the adult side's. With the adult side off there is
    nothing to choose, and children are in every reply (False here, families.withheld False too); with no child in
    their life or on the way, the adult side stays as it always has."""
    if not intimacy.turned_on(connection) or group is not None or not children(connection, companion):
        return False
    try:
        note = authors_note.prompt_text(connection, f"companion:{companion['id']}")
        texts = [message['text'] for message in recent] + [note, (photo or {}).get('text') or '', *own_words(companion)]
        return not reads_intimate(texts)
    except Exception:  # noqa: BLE001 - fails closed: unsure is intimate.
        return False


def adult_lines(connection, companion: dict, recent: list[dict], group: dict | None, photo: dict | None,
                family: bool) -> bool:
    """Whether this reply carries the adult side's lines (companion/world/intimacy.py says whether it is on at all):
    never in a family reply, and not while what goes with the reply anyway (the conversation, a group's shared part,
    the character's own words, the author's note) names a child or says one, so it carries neither side. Fails
    closed: anything that cannot be read carries neither."""
    if family:
        return False
    if not intimacy.turned_on(connection):
        return True
    try:
        found = every_name(connection)
        if not found:
            return True
        note = authors_note.prompt_text(connection, f"companion:{companion['id']}")
        texts = [message['text'] for message in recent] + [note, (photo or {}).get('text') or '', *own_words(companion),
                                                            (group or {}).get('shared') or '']
        return not names_child(texts, found)
    except Exception:  # noqa: BLE001 - fails closed.
        return False


def every_name(connection) -> set[str]:
    """Every child's name in any companion's life: a group chat or another companion's chat can say any of them."""
    from companion.life import families
    rows = connection.execute('SELECT active_timeline_id FROM companions WHERE active_timeline_id IS NOT NULL')
    return set().union(*(families.names(connection, row['active_timeline_id']) for row in rows.fetchall()))


def names_child(texts, names: set[str]) -> bool:
    text = ' '.join(text for text in texts if text)
    return bool(CHILD.search(text)) or any(re.search(rf'\b{re.escape(name)}\b', text) for name in names)


def children(connection, companion: dict) -> bool:
    """Whether there is a child in their life or on the way to keep or drop."""
    from companion.life import families
    timeline_id = companion.get('active_timeline_id')
    return bool(timeline_id and families.names(connection, timeline_id))


def hidden(connection, timeline_id: str, family: bool) -> re.Pattern | None:
    """What no context line may hold: in a family reply, anything that reads intimate; otherwise, with the adult side
    on, a child's name in any companion's life or a line about a child (companion/life/families.py `hidden`)."""
    from companion.life import families
    if family:
        return FamilyLines()
    found = families.hidden(connection, timeline_id)
    names = every_name(connection) if found is not None else set()
    if not names:
        return found
    return re.compile('|'.join([found.pattern, CHILD_WORDS, *(rf'\b{re.escape(name)}\b' for name in sorted(names))]))


class FamilyLines:
    """Matches a context line that reads intimate (`Packet.offer` drops it), the way a compiled pattern would."""

    def search(self, text: str):
        return reads_intimate([text]) or None
