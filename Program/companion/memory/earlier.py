"""Earlier in this talk (Feature Hit List #99): a short, rule-built bridge of the turns that left the window.

The conversation sent with a reply is the last 20 to 31 turns (memory/context.py `window_start`). In a long chat the
turns before it are only reachable through recall, which needs shared words: a nickname, two films or a riddle answer
said only in chat were lost by message 50, and most misses were invented, not "I don't remember" (Cairn probe,
2026-11-03). This module puts a short note of those turns in front of the conversation, with no model call:

- "This talk" is the run of turns before the window with no gap longer than TALK_GAP, at most TALK_TURNS of them.
  During an in-person date it starts after the opening turns the conversation keeps (`context.date_opening`), so
  nothing is said twice.
- One entry per WINDOW_STEP turns that left the window, at most three lines: the user's key sentences picked by rule
  (`picked`), the companion's first and last actions, and any memory saved from those turns.
- About BUDGET tokens in all. Over it, the oldest entries shrink to one line, then drop; what they lose is still
  offered to recall (`spare`), under the turn's own identity so the same turn never surfaces twice.

It is worked out from the transcript on each reply, so an edit, a delete or a reroll of an early turn rebuilds it, and
nothing is stored. Its inputs only change when the window steps, so the start of the prompt still caches between steps.
"""
import re
from dataclasses import dataclass, field
from datetime import timedelta

from companion.clock import parse, zone
from companion.database import many
from companion.library import names
from companion.memory.budget import token_estimate

TALK_GAP = timedelta(hours=3)
TALK_TURNS = 150
BUDGET = 350
PICKED = 2
# A message scoring less than this (a number alone, say) is small talk.
LEAST = 2
CUT = 160
HEADING = ('Earlier in this talk (what was said before the conversation below, oldest first, from the app; the '
           "user's words are quoted. It is true: keep to it, use it when it fits and never recap it)")

SENTENCE = re.compile(r'[^.!?…\n]+(?:[.!?…]+["\'’”)]*|$)')
QUOTED = re.compile(r'["“][^"”]{2,60}["”]|(?<![\w])\'[^\']{2,60}\'(?![\w])')
NUMBER = re.compile(r'\d')
ACTION = re.compile(r'\*([^*\n]{3,200})\*')
# An action has a few words; "*really*" and "*Adolescence*" are emphasis and titles.
ACTION_WORDS = 3
# What people say when they hand over something to keep: a name to use, a favourite, a rule, an answer.
MARKED = re.compile(
    r"\b(?:call me|my (?:name|nickname) is|nickname|my fav(?:ou)?rite|from now on|new rule|the answer is|answer is|"
    r"my (?:birthday|address|number)|don'?t forget|remember (?:this|that)|i(?:'m| am) (?:allergic|scared|afraid)|"
    r"i (?:love|hate|can'?t stand)|we (?:need|should|could)|i vote|you (?:pick|choose|have to)|my first|"
    # News about themselves: what they did, got or tried.
    r"i (?:just |finally |accidentally )?(?:got|made|tried|burned|burnt|bought|started|quit|broke|lost|won|adopted|"
    r"booked|signed|passed|failed|finished|moved|met|ate)|riddle|guess what)\b", re.IGNORECASE)


@dataclass
class Entry:
    """One step of turns that left the window: its lines, newest-kept first in `lines`, and the message ids each
    line came from."""
    first: dict
    lines: list[tuple[str, str]] = field(default_factory=list)  # (message id, text)
    # The user's other key messages past the top PICKED: never shown, offered to recall only.
    extra: list[tuple[str, str]] = field(default_factory=list)

    def text(self, timezone: str, short: bool = False) -> str:
        lines = self.lines[:1] if short else self.lines
        when = local(self.first['created_at'], timezone)
        return '\n'.join(f'- {when}: {text}' if index == 0 else f'  {text}' for index, (_id, text) in enumerate(lines))


def local(at: str, timezone: str) -> str:
    return parse(at).astimezone(zone(timezone)).strftime('%a %H:%M') if timezone else at[11:16]


def talk(older: list[dict], first_recent: dict | None, opening: list[dict] = ()) -> list[dict]:
    """The turns of this talk that left the window, oldest first: back from the window's first turn while no gap is
    longer than TALK_GAP, at most TALK_TURNS, and only after a date's kept opening turns."""
    after = max((message['seq'] for message in opening), default=-1)
    kept, later = [], first_recent
    for message in reversed(older):
        if message['seq'] <= after or len(kept) >= TALK_TURNS:
            break
        if later is not None and parse(later['created_at']) - parse(message['created_at']) > TALK_GAP:
            break
        kept.append(message)
        later = message
    return kept[::-1]


def sentences(text: str) -> list[str]:
    plain = ACTION.sub(' ', text or '')
    return [' '.join(found.split()) for found in SENTENCE.findall(plain) if len(found.split()) >= 2]


def score(sentence: str, known: set[str], answers: bool) -> int:
    """How much a sentence looks like something to keep: a name the app does not know, a quoted title, a number, a
    marked phrase ("call me", "my favourite") and being an answer to the companion's question."""
    unknown = [name for name in names(sentence) if not all(part.casefold() in known for part in name.split())]
    return (3 * bool(unknown) + 3 * bool(QUOTED.search(sentence)) + 3 * bool(MARKED.search(sentence))
            + bool(NUMBER.search(sentence)) + bool(answers))


def picked(step: list[dict], known: set[str]) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """The user's key messages of a step, by rule, each cut to CUT characters: the top PICKED that score at least
    LEAST, in the order said, and the rest that score. A message scores as its best sentence, plus one for each other
    sentence that scores too."""
    scored, asked = [], False
    for message in step:
        if message['role'] != 'user':
            asked = '?' in ACTION.sub(' ', message['text'] or '')
            continue
        points = sorted((score(sentence, known, asked and index == 0)
                         for index, sentence in enumerate(sentences(message['text']))), reverse=True)
        total = points[0] + sum(1 for point in points[1:] if point >= LEAST) if points else 0
        if total >= LEAST:
            text = ' '.join(ACTION.sub(' ', message['text']).split())
            scored.append((total, message['seq'], message['id'], cut(text)))
        asked = False
    ranked = sorted(scored, key=lambda item: (-item[0], item[1]))

    def said(items):
        return [(identity, text) for _points, _seq, identity, text in sorted(items, key=lambda item: item[1])]
    return said(ranked[:PICKED]), said(ranked[PICKED:])


def cut(text: str, limit: int = CUT) -> str:
    return text if len(text) <= limit else text[:limit - 1].rsplit(' ', 1)[0] + '…'


def actions(step: list[dict]) -> list[tuple[str, str]]:
    """The companion's first and last actions of the step (*like this*)."""
    found = [(message['id'], ' '.join(match.split())) for message in step if message['role'] == 'companion'
             for match in ACTION.findall(message['text'] or '') if action(match)]
    return found[:1] + found[-1:] if len(found) > 1 and found[0][1] != found[-1][1] else found[:1]


def action(text: str) -> bool:
    """Whether starred text is something done: a few words, not a title in capitals ("*Where the Crawdads Sing*")."""
    words = text.split()
    return len(words) >= ACTION_WORDS and not all(word[:1].isupper() or len(word) <= 3 for word in words)


def saved(step: list[dict], memories: list[dict]) -> list[tuple[str, str]]:
    """Memories and plans saved from the step's turns, by their saved text."""
    ids = {message['id'] for message in step}
    return [(memory['id'], f"{memory['subject']}: {memory['value']}") for memory in memories
            if not memory.get('boundary') and ids & set(memory.get('source_message_ids') or ())]


def entry(step: list[dict], known: set[str], memories: list[dict]) -> Entry | None:
    (said, extra), done, kept = picked(step, known), actions(step), saved(step, memories)
    lines = []
    if said:
        lines.append((said[0][0], 'The user said: ' + ' / '.join(f'"{text}"' for _id, text in said)))
    if done:
        lines.append((done[0][0], 'You: ' + ' … '.join(f'*{cut(text, 100)}*' for _id, text in done)))
    if kept:
        lines.append((kept[0][0], 'Saved: ' + '; '.join(cut(text, 120) for _id, text in kept[:2])))
    return Entry(step[0], lines, [(identity, f'The user said: "{text}"') for identity, text in extra]) \
        if lines or extra else None


def steps(turns: list[dict], start: int, step: int) -> list[list[dict]]:
    """The talk cut where the window steps: `start` is the window's first index, a multiple of `step`, and each turn's
    index is counted back from it, so the cuts stay put as the window moves on."""
    groups: dict[int, list[dict]] = {}
    for offset, message in enumerate(reversed(turns), 1):
        groups.setdefault((start - offset) // step, []).insert(0, message)
    return [groups[key] for key in sorted(groups)]


@dataclass
class Bridge:
    """What goes in the section, and the lines left out of it that recall may still offer."""
    shown: list[tuple[str, str]]  # (identity, text) per entry, oldest first
    spare: list[dict]  # recall items: id (the turn's message id), created_at, role, text


def bridge(turns: list[dict], start: int, step: int, known: set[str], memories: list[dict], timezone: str,
           budget: int = BUDGET) -> Bridge:
    entries = [found for group in steps(turns, start, step) if (found := entry(group, known, memories))]
    every = [line for found in entries for line in (*found.lines, *found.extra)]
    short = 0
    while entries and fits(entries, short, timezone) > budget:
        if short < len(entries) and len(entries[short].lines) > 1:
            short += 1
        else:
            entries.pop(0)
            short = max(0, short - 1)
    shown = [(f"earlier:{found.first['id']}", found.text(timezone, index < short))
             for index, found in enumerate(entries) if found.lines]
    kept = {line for index, found in enumerate(entries) for line in (found.lines[:1] if index < short else found.lines)}
    by_id = {message['id']: message for message in turns}
    # Saved memories are recallable already; only the turns' own lines are added.
    spare = [{'id': identity, 'created_at': by_id[identity]['created_at'], 'role': by_id[identity]['role'],
              'text': text} for identity, text in every if (identity, text) not in kept and identity in by_id]
    return Bridge(shown, spare)


def fits(entries: list[Entry], short: int, timezone: str) -> int:
    return sum(token_estimate(found.text(timezone, index < short)) for index, found in enumerate(entries))


def known_names(connection, companion: dict) -> set[str]:
    """Words of names the app already knows: the companion, the user's persona, the people in their life and
    everything in the companion's saved memories. A capitalised name outside these is new, so likely said only in
    chat."""
    from companion.life import circle
    definition = (companion.get('version') or {}).get('definition') or {}
    persona = connection.execute('SELECT name FROM persona WHERE id=1').fetchone()
    memories = many(connection, "SELECT subject, value FROM memories WHERE companion_id=? AND status='active'",
                    (companion['id'],))
    texts = [definition.get('name', ''), persona['name'] if persona else '',
             *(row['name'] for row in circle.people(connection, companion['active_timeline_id'])),
             *(f"{memory['subject']} {memory['value']}" for memory in memories)]
    return {word.casefold() for text in texts for word in re.findall(r"[\w'’-]+", text or '')}
