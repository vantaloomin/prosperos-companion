"""How the companion texts: short bursts, all lowercase, the odd typo fixed with a *correction.

A per-character style (the definition's `texting`), all off by default. The model is told the style
in the character section of the context; once a reply is complete it is restyled by fixed rules, so
the style holds even when a model drifts: lowercase is applied, and with typos on a seeded few
replies get one swapped pair of letters and a "*word" line after it. Bursts are blank-line separated
parts, which the chat shows as separate bubbles. Nothing here calls a model.

Out loud (together in person or on a call) none of it applies: the "How you text" line goes and an "out loud" line
takes its place, since a Voice line like "texts in lowercase, typos everywhere" and the chat's earlier texts otherwise
carry the habits into what they say (A/B 2026-10-29: 73 of 108 in-person replies came out lowercase without the line,
17 of 109 with it, and as like the character either way). A reply that still has no capital at all gets its sentence
starts and "I" put back.
"""
import random
import re

TYPO_SHARE = 0.12
WORD = re.compile(r'\b[a-zA-Z]{5,}\b')
LINK = re.compile(r'https?://\S+|\S+@\S+')
# A voice that avoids capitals ("texts in lowercase", "rarely uses capital letters").
LOWERCASE = re.compile(r'lower-?case|avoids? capital|no capital|without capital|never capitali|skips? capital'
                       r'|(?:rarely|seldom|hardly ever|never) (?:uses? |bothers? with )?capital', re.IGNORECASE)
# A voice that makes typos ("typos everywhere", "fixes them with a *correction", "misspells words").
TYPOS = re.compile(r'typo|\*\s?correct|misspell', re.IGNORECASE)
OUT_LOUD = ('Out loud: your texting habits (all lowercase, typos and *corrections, separate short texts) are for texts '
            'only. When you talk, write what you say with ordinary capitals and punctuation, still in your own words, '
            'slang and attitude.')
SENTENCE_START = re.compile(r'(^|[.!?]\s+|\n\s*|(?:^|(?<=\s))["\u201c*]\s*)([a-z])')
LITTLE_I = re.compile(r"\bi(?=\b(?!\.\w)|')")


def style(definition: dict) -> dict:
    return {'bursts': False, 'lowercase': False, 'typos': False, **(definition.get('texting') or {})}


def instruction(definition: dict) -> str | None:
    """One line for the character section, or None when they text like anyone else."""
    chosen, parts = style(definition), []
    if chosen['bursts']:
        parts.append('send several short texts instead of one paragraph: two to four bursts, each on its own '
                     'line with a blank line between them')
    if chosen['lowercase']:
        parts.append('write in all lowercase, casually')
    return f"How you text: {'; '.join(parts)}." if parts else None


def line(definition: dict, texts: bool) -> str | None:
    """How they text, or while talking how they don't; None when there are no habits to mention."""
    return instruction(definition) if texts else out_loud(definition)


def out_loud(definition: dict) -> str | None:
    """The line for talking in person or on a call, for someone who texts with habits; None for anyone else."""
    chosen, voice = style(definition), definition.get('voice') or ''
    if chosen['bursts'] or chosen['lowercase'] or chosen['typos'] or LOWERCASE.search(voice) or TYPOS.search(voice):
        return OUT_LOUD
    return None


def spoken(text: str) -> str:
    """Capitals back at sentence starts and on "I" when a reply said out loud came back with none at all."""
    if any(character.isupper() for character in LINK.sub('', text)):
        return text
    pieces, last = [], 0
    for match in LINK.finditer(text):
        pieces += [capitalised(text[last:match.start()]), match.group()]
        last = match.end()
    return ''.join(pieces + [capitalised(text[last:])])


def capitalised(text: str) -> str:
    text = SENTENCE_START.sub(lambda match: match.group(1) + match.group(2).upper(), text)
    return LITTLE_I.sub('I', text)


def lowercase(text: str) -> str:
    """Lowercase everything except links and email addresses."""
    pieces, last = [], 0
    for match in LINK.finditer(text):
        pieces += [text[last:match.start()].lower(), match.group()]
        last = match.end()
    return ''.join(pieces + [text[last:].lower()])


def typo(text: str, seed: str) -> str:
    """Now and then, one swapped pair of letters in a longer word, corrected on its own line."""
    rng = random.Random(f'typo:{seed}')
    if rng.random() >= TYPO_SHARE:
        return text
    words = [match for match in WORD.finditer(text) if not LINK.search(text[max(0, match.start() - 8):match.end()])]
    if not words:
        return text
    match = rng.choice(words)
    word = match.group()
    at = rng.randint(1, len(word) - 3)
    wrong = word[:at] + word[at + 1] + word[at] + word[at + 2:]
    if wrong == word:
        return text
    return f'{text[:match.start()]}{wrong}{text[match.end():]}\n\n*{word}'


def restyle(text: str, definition: dict, seed: str) -> str:
    chosen = style(definition)
    if chosen['typos']:
        text = typo(text, seed)
    if chosen['lowercase']:
        text = lowercase(text)
    return text
