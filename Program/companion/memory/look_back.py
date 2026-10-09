"""She can ask to remember more (Feature Hit List #39): one extra look through memory when a reply needs it.

Recall runs once before a reply (companion/memory/context.py, "Possibly relevant memories"). When the user's message
points at the past ("remember when", "last summer", "you told me") two things can add to it:

- With no model call: when that first recall comes back thin, the app widens the search itself before the reply,
  with the user's last few messages for words and without holding back what came up lately.
- Once per reply: the companion's reply may start with a hidden request instead, `[[recall: the ferry trip]]`. The
  app catches it before any text is shown (`Lookout`), looks again with those words, adds what it found as a note
  at the end of the prompt (so prompt caching still works) and asks once more, without the option to ask again. So
  the worst case is two model calls for that reply. A text marker, not tool calling, because many local models
  handle tools poorly. The request never shows in chat; if nothing more turns up, she answers with what she has.

The Memory setting `recall_more` (on by default) turns the second part off; the widened search always runs.
"""
import re

PAST = re.compile(
    r"\b(?:remember(?:s|ed)?|recall|back when|that time|the time (?:we|you|i)|last (?:year|summer|winter|spring|"
    r"fall|autumn|month|week|time)|(?:years?|months?|weeks?) ago|used to|you (?:said|told me|mentioned|promised)|"
    r"i (?:told|said to|mentioned to) you|when we|we (?:went|had|did|talked)|forgot|forget)\b", re.IGNORECASE)
# Fewer recalled items than this (besides pinned ones) is a thin first recall.
THIN = 2
# The user's own recent messages added to a widened search.
WIDEN_MESSAGES = 3
OPEN = '[[recall'
MARKER = re.compile(r'^\s*\[\[\s*recall\s*:\s*([^\]\n]{1,200}?)\s*\]\]\s*', re.IGNORECASE)
# A start longer than this that never closes the request is ordinary text.
HOLD_LIMIT = 260
ASK = ("If the user is talking about something from before that is not in your notes or the conversation, and you "
       "need the details to answer well, you may reply with only [[recall: a few words to look up]] instead of a "
       "reply. The app will look through your memories and earlier conversations and ask you again, once. "
       "Otherwise just reply as usual, and never mention this.")
FOUND = ("You asked to remember more about «{query}». What the app found in your memories and earlier "
         "conversations:\n{lines}\nNow write your reply, using this where it fits. Do not ask to look anything up "
         "again.")
NOTHING = ("You asked to remember more about «{query}», but nothing more was found. Reply with what you know; if you "
           "don't remember, say so the way a person would. Do not ask to look anything up again.")


def points_back(text: str) -> bool:
    return bool(PAST.search(text or ''))


def found_note(query: str, lines: list[str]) -> str:
    return FOUND.format(query=query, lines='\n'.join(lines)) if lines else NOTHING.format(query=query)


class Lookout:
    """Holds back the start of a streamed reply until it is clear whether it asks to remember more. With `strip`,
    a request is dropped and the rest of the reply goes on (the second try may not ask again)."""

    def __init__(self, active: bool = True, strip: bool = False):
        self.decided, self.strip = not active, strip
        self.held = ''
        self.query: str | None = None

    def feed(self, piece: str) -> str:
        if self.decided:
            return '' if self.query else piece
        self.held += piece
        start = self.held.lstrip()
        if not start:
            return ''
        opening = start[:len(OPEN)].lower()
        if not OPEN.startswith(opening):
            return self.release()
        if found := MARKER.match(self.held):
            self.decided = True
            if self.strip:
                rest, self.held = self.held[found.end():], ''
                return rest
            self.query, self.held = found.group(1).strip(), ''
            return ''
        return self.release() if len(self.held) > HOLD_LIMIT else ''

    def release(self) -> str:
        self.decided = True
        text, self.held = self.held, ''
        return text

    def flush(self) -> str:
        return '' if self.query else self.release()
