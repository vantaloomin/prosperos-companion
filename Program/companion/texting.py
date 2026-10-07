"""How the companion texts: short bursts, all lowercase, the odd typo fixed with a *correction.

A per-character style (the definition's `texting`), all off by default. The model is told the style
in the character section of the context; once a reply is complete it is restyled by fixed rules, so
the style holds even when a model drifts: lowercase is applied, and with typos on a seeded few
replies get one swapped pair of letters and a "*word" line after it. Bursts are blank-line separated
parts, which the chat shows as separate bubbles. Nothing here calls a model.
"""
import random
import re

TYPO_SHARE = 0.12
WORD = re.compile(r'\b[a-zA-Z]{5,}\b')
LINK = re.compile(r'https?://\S+|\S+@\S+')
# A voice that avoids capitals ("texts in lowercase", "rarely uses capital letters").
LOWERCASE = re.compile(r'lower-?case|avoids? capital|no capital|without capital|never capitali|skips? capital'
                       r'|(?:rarely|seldom|hardly ever|never) (?:uses? |bothers? with )?capital', re.IGNORECASE)


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
