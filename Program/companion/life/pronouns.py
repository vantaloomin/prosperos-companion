"""The companion's own pronouns in rule and template text: storylines, dreams, traditions and day events, Life deck
moments and the reasons an outcome went the way it did.

Templates speak of the companion as "they", which product copy keeps when their pronouns are not known. When their
description says "she" or "he" (companion/world/looks.pronouns_of reads it), the phrases that are about the companion
are said with those pronouns, verb included ("she is", not "they is"). Only listed phrases change: a "they" about
someone else in the same line stays. Swaps run when text is read, so lines already written read right too.
"""
from companion.world import looks

FORMS = {'she/her': {'they': 'she', 'them': 'her', 'their': 'her', 'theirs': 'hers', 'themselves': 'herself', 'are': 'is', 'were': 'was',
                     'do': 'does', 's': 's'},
         'he/him': {'they': 'he', 'them': 'him', 'their': 'his', 'theirs': 'his', 'themselves': 'himself', 'are': 'is', 'were': 'was',
                    'do': 'does', 's': 's'}}


def forms(definition: dict) -> dict | None:
    """The companion's pronoun forms, or None when they are not known (the text keeps "they")."""
    return FORMS.get(looks.pronouns_of(definition))


def their(definition: dict) -> str:
    """"their", or "her" / "his" when the companion's pronouns are known."""
    return (forms(definition) or {}).get('their', 'their')


def said(text: str | None, swaps: tuple[tuple[str, str], ...], definition: dict) -> str | None:
    """The text with each phrase about the companion said with their pronouns; `{they}`, `{them}`, `{their}`,
    `{theirs}`, `{themselves}`, `{are}`, `{were}`, `{do}` and `{s}` (a verb's "s": "like{s}") in the new phrase are filled from
    their forms."""
    found = forms(definition) if text else None
    if not found:
        return text
    for old, new in swaps:
        if old in text:
            for key, value in found.items():
                new = new.replace(f'{{{key}}}', value)
            text = text.replace(old, new)
    return text
