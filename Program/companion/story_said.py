"""What is said in a Story scene sticks (1.5, docs/story.md, "Scenes count"), as it does in a chat. Rules only:

- Facts the user tells a companion face to face become that companion's memories, by the rules a chat message goes
  through (companion/memory/formation.py, memory/extraction.py), read from the words said out loud (in quotation
  marks when the line has any). Every companion the line is said to hears it. A sensitive fact is kept only while
  sensitive memory is on: a scene has no message to offer it from as a suggestion. The memory remembers the line it
  came from (`story_memories`), so its card can say so; a new story clears the lines, not the memories.
- The user's words move the companion's mood (companion/moods.py `from_user`) and rough patches
  (companion/life/rough_patches.py `note`: words that sting, an apology, a gesture, accepting their apology) as a
  text does, for the one companion the line is meant for. A promise ("I'll call you tonight") stays with chat.
- Their own line in the scene can make up (moods `from_reply`), and is written knowing how they feel
  (`feeling_lines`), as their chat reply is.

All of it goes with "Story scenes count" (companion/story_visits.py `counts`), and memories with automatic memory.
"""
import re
from datetime import datetime

from companion import moods
from companion.database import many, optional, settings
from companion.life import rough_patches
from companion.life.steps import SPOKEN, out_loud
from companion.memory import formation, people

ACTIVE = True
LINE_CHARS = 300
# What the user does around the words that makes them banter: "I grin and nudge Mira."
PLAYFUL = re.compile(r"\b(?:grin|smirk|wink|laugh|giggl|chuckl|snort|teas|nudg|bump|poke|stick out my tongue|smil|ruffl|"
                     r"boop)\w*", re.IGNORECASE)
# How a mood colours a line said in person; the chat's own wording is about writing (moods.chat_lines).
FEEL = ("- You're {feel}{about} (why: {reason}). Let it show in how you speak and act here (your words, your face, "
        'how close you stand), not just in what you say. Never explain it unless asked.')


def key(companion: dict) -> str:
    return f"companion:{companion['id']}"


# The user's line --------------------------------------------------------------------------------------------

def user_line(connection, user: dict, heard_by: list[dict], target: dict | None, now: datetime) -> None:
    """The user's line was just saved and read for a step (story_visits.said): what it tells the companions it is
    said to is remembered, and the one it is meant for feels it."""
    if not ACTIVE:
        return
    for item in heard_by:
        remember(connection, item['companion'], user)
    if target:
        feel(connection, target['companion'], user, now)


def remember(connection, companion: dict, user: dict) -> list[dict]:
    """The memories one line leaves with one companion, as automatic memory would from a text. Returns them."""
    row = settings(connection)
    if not row['automatic_memory'] or not companion.get('active_timeline_id'):
        return []
    said = {'text': out_loud(user['text']), 'created_at': user['created_at']}
    people.touch(connection, companion['id'], said['text'], user['created_at'])
    written = []
    for candidate in formation.candidates_for(connection, said, companion):
        if declined(connection, companion, formation.fingerprint(candidate)):
            continue
        fields = people.bind_existing(connection, companion['id'], formation.proposal(candidate, said))
        if formation.hold_reason(fields, allowed_sensitive=bool(row['sensitive_memory'])):
            continue
        memory, outcome = formation.commit(connection, companion, fields, [], user['created_at'], 'automatic')
        formation.log(connection, user['created_at'], outcome, memory_id=memory and memory['id'], detail='story')
        if memory and outcome == 'committed':
            link(connection, memory, companion, user)
            written.append(memory)
    return written


def declined(connection, companion: dict, mark: str) -> bool:
    """The user turned this fact down before, in the chat (formation.record_candidate): not from a scene either."""
    return optional(connection, "SELECT 1 FROM memory_candidates WHERE fingerprint=? AND status='declined' AND "
                    'companion_id=?', (mark, companion['id'])) is not None


def link(connection, memory: dict, companion: dict, user: dict) -> None:
    text = ' '.join(user['text'].split())
    text = text if len(text) <= LINE_CHARS else text[:LINE_CHARS - 1].rstrip() + '…'
    connection.execute('INSERT OR IGNORE INTO story_memories (memory_id, companion_id, timeline_id, story_message_id, '
                       'said, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                       (memory['id'], companion['id'], memory['timeline_id'], user['id'], text, user['created_at']))


def feel(connection, companion: dict, user: dict, now: datetime) -> None:
    """Their mood and any rough patch read the line as they read a text: the words said for what stings or soothes,
    the whole line for a gesture ("I hand Mira the flowers"). A grin or a nudge in what the user does makes the words
    teasing, as a wink in a text does (moods.teasing)."""
    speech = out_loud(user['text'])
    if speech != user['text'] and PLAYFUL.search(SPOKEN.sub(' ', user['text'])):
        speech = f'{speech} ;)'
    moods.from_user(connection, key(companion), speech, now)
    rough_patches.note(connection, {'id': f"story:{user['id']}", 'role': 'user', 'text': speech,
                                    'created_at': user['created_at']}, companion, now, gesture_text=user['text'])


# Their own line -----------------------------------------------------------------------------------------------

def their_line(connection, companion: dict, line: dict, now: datetime) -> None:
    """Their own line in the scene, once written: saying it's alright now clears being upset with the user."""
    if ACTIVE and line['status'] == 'complete':
        moods.from_reply(connection, key(companion), out_loud(line['text']), now)


def feeling_lines(connection, companion: dict, now: datetime) -> list[tuple[str, str]]:
    """For their own line in the scene: how they feel right now, and a rough patch with the user, as their chat is
    told (memory/context.py), in words for being face to face."""
    if not ACTIVE:
        return []
    found = []
    mood = moods.current(connection, key(companion), now)
    if mood and mood['feeling'] != 'calm':
        mild, strong = moods.STYLE[mood['feeling']]
        about = (' with the user' if mood['target'] == moods.USER else
                 f" with {moods.labels_name(connection, mood['target'])}" if mood['target'] else '')
        found.append((f"mood:{mood['feeling']}:{mood['intensity']}:{mood['target']}",
                      FEEL.format(feel=strong if mood['intensity'] >= 2 else mild, about=about, reason=mood['reason'])))
    return found + rough_patches.context_lines(connection, companion, now)


# On Memories ----------------------------------------------------------------------------------------------------

def lines_for(connection, companion_id: str) -> dict[str, str]:
    """{memory id: the line it came from} for one companion's memories told in the Story."""
    return {row['memory_id']: row['said'] for row in many(
        connection, 'SELECT memory_id, said FROM story_memories WHERE companion_id=?', (companion_id,))}


def carry(connection, old_id: str, new_id: str) -> None:
    """A corrected memory (records.revise) still came from the scene."""
    connection.execute('INSERT OR IGNORE INTO story_memories (memory_id, companion_id, timeline_id, story_message_id, '
                       'said, created_at) SELECT ?, companion_id, timeline_id, story_message_id, said, created_at '
                       'FROM story_memories WHERE memory_id=?', (new_id, old_id))

