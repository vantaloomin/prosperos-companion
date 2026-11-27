"""A Story reply the model stopped at the "Longest reply" limit ends at its last full sentence.

Chat marks a reply the service cut short as incomplete and offers Retry. The Story saved one as a finished reply,
ending wherever the limit fell: "To the room, she says, in" (real-model run of 1.5.2). The Story is a page to read
and to export, so a cut reply is trimmed back to its last full sentence, with a quote it leaves open closed, and
stays part of the story. The line remembers that it was cut (`story_messages.cut`), and while it is part of the
newest exchange the screen says so beside Another reply. A reply with no full sentence to keep stays as it is.
Rewording the reply by hand makes it the user's own, and whole. Rules only.
"""
import re

# Where a sentence ends: its mark, then any closing quotes, brackets or emphasis, then space or the end.
END = re.compile(r"""[.!?…]+["”’'»)\]*_]*(?=\s|$)""")
# A full stop that ends no sentence.
TITLE = re.compile(r'\b(?:Mr|Mrs|Ms|Dr|St|Mx|Prof|Sr|Jr|vs|etc|e\.g|i\.e)\.$', re.IGNORECASE)
PAIRS = (('“', '”'), ('«', '»'))


def trimmed(text: str) -> str:
    """The reply up to its last full sentence, with an open quote closed; as it is when it has none."""
    ends = [found.end() for found in END.finditer(text) if not TITLE.search(text[:found.end()])]
    if not ends:
        return text
    return closed(text[:ends[-1]].rstrip())


def closed(text: str) -> str:
    """A quote opened in the last paragraph and never closed is closed: the words that would have closed it are
    gone with the rest of the sentence."""
    last = text.rsplit('\n', 1)[-1]
    for opening, closing in PAIRS:
        if last.count(opening) > last.count(closing):
            return text + closing
    return text + '"' if last.count('"') % 2 else text
