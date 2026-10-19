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
        r'tie (?:me|you) up', r'spank\w*', r'collar', r'naughty', r'crav(?:e|ing) you')


@cache
def pattern() -> re.Pattern:
    """Every word that makes a reply read intimate: a picture's sexual, nude and unsure words, the chat's own, and
    the adult side's interests (companion/world/data/intimacy.json)."""
    terms = [*content.SEXUAL, *content.NUDITY, *(term for term in content.UNCERTAIN if term not in NOT_INTIMATE), *CHAT]
    terms += [re.escape(content.normalize(entry['label'])) for entry in intimacy.bank()['interests']]
    return re.compile(r'\b(?:' + '|'.join(terms) + r')\b')


def reads_intimate(texts) -> bool:
    return bool(pattern().search(content.normalize(' '.join(text for text in texts if text))))


def family_reply(connection, companion: dict, recent: list[dict], group: dict | None, photo: dict | None) -> bool:
    """Whether this reply carries the family lines instead of the adult side's. With the adult side off there is
    nothing to choose, and children are in every reply (False here, families.withheld False too); with no child in
    their life or on the way, the adult side stays as it always has."""
    if not intimacy.turned_on(connection) or group is not None or not children(connection, companion):
        return False
    try:
        note = authors_note.prompt_text(connection, f"companion:{companion['id']}")
        texts = [message['text'] for message in recent] + [note, (photo or {}).get('text') or '']
        return not reads_intimate(texts)
    except Exception:  # noqa: BLE001 - fails closed: unsure is intimate.
        return False


def children(connection, companion: dict) -> bool:
    """Whether there is a child in their life or on the way to keep or drop."""
    from companion.life import families
    timeline_id = companion.get('active_timeline_id')
    return bool(timeline_id and families.names(connection, timeline_id))


def hidden(connection, timeline_id: str, family: bool) -> re.Pattern | None:
    """What no context line may hold: in a family reply, anything that reads intimate; otherwise, with the adult side
    on, a child's name (companion/life/families.py `hidden`)."""
    from companion.life import families
    if family:
        return FamilyLines()
    return families.hidden(connection, timeline_id)


class FamilyLines:
    """Matches a context line that reads intimate (`Packet.offer` drops it), the way a compiled pattern would."""

    def search(self, text: str):
        return reads_intimate([text]) or None
