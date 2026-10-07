"""The people the user has met in their own story (Story mode, docs/story.md), kept apart from every companion.

Someone present in the scene is met once their name comes up: the narrator voices them giving it, or the
user uses it. Each local day they come up counts as one meeting. A few sentences of the story about them
are kept as notes, so the narrator remembers them the next time they are in the scene, however far back
the story has been trimmed. Townsfolk keep no memories of their own; this is the user's side only.
"""
import re
from datetime import date

from companion.database import decode, encode, many, optional

NOTES = 8
NOTE_CHARS = 240
SENTENCE = re.compile(r'[^.!?\n]+[.!?]["”’)]?')


def known(connection) -> dict[str, dict]:
    return {row['key']: row | {'notes': decode(row['notes'])} for row in many(
        connection, 'SELECT * FROM story_people ORDER BY last_met_at DESC')}


def named(sheet: dict, text: str) -> bool:
    """Their given name (or full name) as a word in the text, capitalized as a name is."""
    return any(name and re.search(rf'(?<![\w-]){re.escape(name)}(?![\w-])', text)
               for name in (sheet.get('full'), sheet.get('name')))


def about(sheet: dict, text: str, limit: int = 2) -> list[str]:
    """The sentences of the text that name them, trimmed for the notes."""
    found = [sentence.strip() for sentence in SENTENCE.findall(text) if named(sheet, sentence)]
    return [sentence if len(sentence) <= NOTE_CHARS else sentence[:NOTE_CHARS - 1].rstrip() + '…'
            for sentence in found[:limit]]


def meet(connection, sheet: dict, city_id: str, now: str, day: date, notes=()):
    """Record that the user met this person (again): one meeting per local day, the newest notes kept.
    Other features that put the user with someone in the story (a date, say) call this too."""
    row = optional(connection, 'SELECT * FROM story_people WHERE key=?', (sheet['key'],))
    if row is None:
        connection.execute(
            'INSERT INTO story_people (key, city_id, name, first_met_at, last_met_at, last_day, meetings, notes) '
            'VALUES (?, ?, ?, ?, ?, ?, 1, ?)', (sheet['key'], city_id, sheet['full'], now, now, day.isoformat(),
                                                 encode([note for note in notes][-NOTES:])))
        return
    kept = decode(row['notes'])
    kept += [note for note in notes if note not in kept]
    connection.execute('UPDATE story_people SET last_met_at=?, last_day=?, meetings=meetings+?, notes=? WHERE key=?',
                       (now, day.isoformat(), int(row['last_day'] != day.isoformat()), encode(kept[-NOTES:]),
                        sheet['key']))


def note_exchange(connection, people: list[dict], city_id: str, said: str, reply: str, now: str, day: date):
    """After the narrator's reply: everyone present whose name came up has met the user."""
    for person in people:
        sheet = person['sheet']
        if named(sheet, reply) or named(sheet, said):
            meet(connection, sheet, city_id, now, day, about(sheet, reply))


def remembered(row: dict | None) -> str:
    """What the narrator is told about someone the user has met, or '' for a stranger."""
    if not row:
        return ''
    times = 'once' if row['meetings'] == 1 else 'twice' if row['meetings'] == 2 else f"{row['meetings']} times"
    notes = ' '.join(row['notes'][-4:])
    return f" The user has met them {times} and knows their name; last on {row['last_day']}." + \
        (f' From before: {notes}' if notes else '')
