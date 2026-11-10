"""Their own words (Feature Hit List #97): stock wording is named from its first use, a habit that ignores a nudge
gets a firmer one and is then taken out by rule, and the user can keep a short list of words to drop or swap.

- Known AI-isms: the bank world/data/ai_isms.json (stock phrases anywhere; stock openers at the start of a reply,
  closers in its last sentence). One use in the companion's last RECENT replies is enough to name it in the reply's
  notes, beside the repeated wording companion/memory/phrases.py already finds.
- The ladder, worked out from the transcript so nothing is stored. Step 1 is the nudge. When a named phrase turns up
  again in the very next reply, it is at step 2: a firmer line naming that phrase alone. When it turns up after that
  too, step 3 takes the sentence holding it out of the finished reply (`Tidy`), only when at least two other
  sentences remain, and never in an out-of-character reply.
- The user's list (table word_rules): words to drop or swap after the reply is written, for this world or for
  every world, at most MAX_RULES. "Caught lately" in Settings shows what was caught; Keep marks a catchphrase that is
  never flagged again, Dismiss takes it off the list.

Names, the user's own words, anything in the companion's written voice and kept phrases are never flagged. The text
is passed on a sentence at a time while there is anything to change, so a sentence never shows and then vanishes.
Rules only, no model call.
"""
import json
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass
from functools import cache, lru_cache
from pathlib import Path

from companion.database import identifier, many, one, optional
from companion.errors import require
from companion.in_character import SENTENCE_END
from companion.memory import phrases

# The A/B arms (2026-11-10): off is today's nudge alone; LADDER off names stock wording without the later steps.
ACTIVE = True
LADDER = True
BANK = Path(__file__).resolve().parents[1] / 'world' / 'data' / 'ai_isms.json'
RECENT = phrases.RECENT_REPLIES
STOCK_SHOWN = 3
MAX_RULES = 50
ACTIONS = ('drop', 'swap', 'keep', 'dismiss')
WORD = re.compile(r"[^\W_]+(?:['\-][^\W_]+)*")
EDGE = '"“‘\'( \n\t'


def plain(text: str) -> str:
    """Text as the bank reads it: straight apostrophes, no asterisks or underscores around actions."""
    return text.replace('’', "'").replace('‘', "'").replace('*', '').replace('_', ' ')


def pattern(phrase: str) -> str:
    """A phrase matched as whole words, loose about the spaces and commas between them, with its own punctuation at
    either end kept ("spill!" is not "spill it"). A phrase with no words at all (an em-dash) is matched as it is."""
    text = plain(phrase).strip()
    words = WORD.findall(text)
    if not words:
        return re.escape(text)
    first, last = text.find(words[0]), text.rfind(words[-1]) + len(words[-1])
    before, after = text[:first].strip(), text[last:].strip()
    body = r"[^\w']+".join(re.escape(word) for word in words)
    lead = re.escape(before) + r'\s*' if before else r"(?<![\w'])"
    tail = r'\s*' + re.escape(after) if after else r"(?![\w'])"
    return lead + body + tail


@cache
def compiled(phrase: str) -> re.Pattern:
    return re.compile(pattern(phrase), re.IGNORECASE)


@cache
def bank() -> dict:
    data = json.loads(BANK.read_text(encoding='utf-8'))
    return {kind: tuple(data[kind]) for kind in ('phrases', 'openers', 'closers')}


def last_sentence(text: str) -> str:
    pieces = [piece for piece in SENTENCE_END.split(text.strip()) if piece.strip()]
    return pieces[-1] if pieces else ''


@lru_cache(maxsize=4096)
def stock_in(text: str) -> tuple[str, ...]:
    """The bank's phrases in one reply."""
    words, start = plain(text), plain(text).lstrip(EDGE)
    end = last_sentence(words)
    found = [phrase for phrase in bank()['phrases'] if compiled(phrase).search(words)]
    found += [phrase for phrase in bank()['openers'] if compiled(phrase).match(start)]
    found += [phrase for phrase in bank()['closers'] if compiled(phrase).search(end)]
    # A phrase inside a longer one found in the same reply adds nothing.
    return tuple(phrase for phrase in found if not any(phrase != other and phrase in other for other in found))


def uses(text: str, phrase: str) -> bool:
    return bool(compiled(phrase).search(plain(text)))


@dataclass(frozen=True)
class Protected:
    """What is never flagged: names, words the user wrote, the companion's written voice and kept phrases."""
    names: frozenset = frozenset()
    said: str = ''

    def covers(self, phrase: str) -> bool:
        if any(word in self.names for word in WORD.findall(phrase.casefold())):
            return True
        return bool(self.said) and bool(compiled(phrase).search(self.said))


def found(replies: list[dict], protected: Protected) -> list[dict]:
    """What the nudge names for these replies: stock wording used even once, then repeated wording."""
    counts = Counter(phrase for reply in replies for phrase in set(stock_in(reply['text'])))
    stock = [{'phrase': phrase, 'kind': 'stock', 'count': count}
             for phrase, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
             if not protected.covers(phrase)][:STOCK_SHOWN] if ACTIVE else []
    named = [item['phrase'] for item in stock]
    repeats = [{'phrase': item['phrase'], 'kind': 'repeat', 'count': item['passage_count'], 'words': item['words']}
               for item in phrases.repeated(replies, protected.names, phrases.SHOWN + 2)
               if not protected.covers(item['phrase'])
               and not any(item['phrase'] in plain(other) or plain(other) in item['phrase'] for other in named)]
    # A phrase they keep using comes before a single word they use a lot, so it is the one named and asked about.
    repeats.sort(key=lambda item: item['words'] < phrases.MIN_WORDS)
    return stock + repeats[:phrases.SHOWN]


def ladder(replies: list[dict], protected: Protected) -> list[dict]:
    """`found` for the last RECENT of `replies` (oldest first, up to twice that many), each with its step: one more
    for every reply that used it after it was named."""
    items = found(replies[-RECENT:], protected)
    if not (ACTIVE and LADDER) or not items:
        return [{**item, 'step': 1} for item in items]
    wanted, ignored = {item['phrase'] for item in items if climbs(item)}, Counter()
    for index in range(max(1, len(replies) - RECENT), len(replies)):
        named = {item['phrase'] for item in found(replies[max(0, index - RECENT):index], protected)} & wanted
        ignored.update(phrase for phrase in named if uses(replies[index]['text'], phrase))
    return [{**item, 'step': min(3, 1 + ignored[item['phrase']]) if climbs(item) else 1} for item in items]


def climbs(item) -> bool:
    """Only stock wording and repeated phrases climb the ladder; a single word they use a lot ("hoodie", "down") is
    only ever pointed out, never asked about again or taken out."""
    return item['kind'] == 'stock' or item.get('words', 1) >= phrases.MIN_WORDS


def quoted(items) -> str:
    return ', '.join(f'"{item["phrase"]}"' for item in items)


def line(items: list[dict], total: int) -> str | None:
    """The reply's note about their wording: today's nudge for repeats, one for stock wording, and a firmer line for
    each phrase that came back after being named."""
    repeats = [item for item in items if item['step'] == 1 and item['kind'] == 'repeat']
    stock = [item for item in items if item['step'] == 1 and item['kind'] == 'stock']
    parts = []
    if repeats:
        listed = ', '.join(f'"{item["phrase"]}" ({item["count"]} of your last {total} messages)' for item in repeats)
        parts.append(f'You keep repeating: {listed}. Say it differently.')
    if stock:
        parts.append(f'Stock wording that reads as written, not said: {quoted(stock)}. Leave it out and say it your '
                     'own way.')
    parts += [f'You were asked not to write "{item["phrase"]}" and wrote it again. Do not use "{item["phrase"]}" in '
              'this reply, or anything close to it.' for item in items if item['step'] > 1]
    return ' '.join(parts) or None


# The user's list --------------------------------------------------------------------------------------------------

def rules(connection) -> list[dict]:
    return many(connection, 'SELECT * FROM word_rules ORDER BY created_at, id')


def swaps(rows) -> list[tuple[str, str]]:
    return [(row['phrase'], row['replacement'] if row['action'] == 'swap' else '') for row in rows
            if row['action'] in ('drop', 'swap')]


def protected_for(connection, timeline_id, definition, messages, rows) -> Protected:
    from companion.life import circle
    names = {word.casefold() for row in circle.people(connection, timeline_id, include_removed=True)
             for word in row['name'].split()} | {word.casefold() for word in definition.get('name', '').split()}
    said = [message['text'] for message in messages if message['role'] == 'user']
    said += [definition.get('voice') or '', *(row['phrase'] for row in rows if row['action'] == 'keep')]
    return Protected(frozenset(names), plain('\n'.join(said)))


def window(messages: list[dict]) -> list[dict]:
    """The messages the ladder reads: from the first of the companion's last 2 x RECENT replies on."""
    replies = [index for index, message in enumerate(messages) if message['role'] == 'companion']
    return messages[replies[-2 * RECENT]:] if len(replies) >= 2 * RECENT else messages


def caught(connection, timeline_id, definition, messages, rows=None) -> list[dict]:
    rows = rules(connection) if rows is None else rows
    span = window(messages)
    replies = [message for message in span if message['role'] == 'companion']
    return ladder(replies, protected_for(connection, timeline_id, definition, span, rows))


def plan(connection, timeline_id, definition, messages) -> tuple[str | None, dict]:
    """The reply's note and what to change in the finished reply: {'remove': step-3 phrases, 'swaps': [(find,
    replacement)]}."""
    rows = rules(connection)
    items = caught(connection, timeline_id, definition, messages, rows)
    total = min(RECENT, sum(message['role'] == 'companion' for message in messages))
    return line(items, total), {'remove': [item['phrase'] for item in items if item['step'] == 3],
                                'swaps': swaps(rows)}


def offer(packet, connection, timeline_id, definition, messages, group=None):
    """A one-on-one reply's note about their wording (section 'wording') and what to change in it (`packet.tidy`)."""
    if group is not None:
        return
    wording, packet.tidy = plan(connection, timeline_id, definition, messages)
    if wording:
        packet.offer('wording', 'wording', wording)


# The finished reply -----------------------------------------------------------------------------------------------

def swapped(text: str, pairs) -> str:
    changed = text
    for find, replacement in pairs:
        changed = compiled(find).sub(lambda _match, replacement=replacement: replacement, changed)
    if changed == text:
        return text
    # A dropped or swapped word leaves no double space, no space before a comma and no comma opening a sentence.
    changed = re.sub(r'[ \t]{2,}', ' ', changed)
    changed = re.sub(r' +([,.!?;:])', r'\1', changed)
    changed = re.sub(r'^(\s*)[,;:]\s*', r'\1', changed)
    was, now = re.search(r'[^\W\d_]', text), re.search(r'[^\W\d_]', changed)
    if was and now and was.group().isupper() and now.group().islower():
        changed = changed[:now.start()] + now.group().upper() + changed[now.end():]
    return changed


class Tidy:
    """Passes a streamed reply on a sentence at a time when there is anything to change: swaps and drops from the
    user's list, and sentences holding a step-3 phrase taken out while at least two others are kept. A taken-out
    sentence waits until two others are known; when the reply ends without them, it stays."""

    def __init__(self, plan: dict | None = None, in_character: bool = True):
        plan = plan or {}
        self.remove = [compiled(phrase) for phrase in plan.get('remove', ())] if in_character else []
        self.pairs = [tuple(pair) for pair in plan.get('swaps', ())]
        self.active = bool(self.remove or self.pairs)
        self.pending, self.held, self.kept, self.removed = '', [], 0, 0

    def feed(self, text: str) -> str:
        if not self.active:
            return text
        self.pending += text
        out, start = [], 0
        for end in SENTENCE_END.finditer(self.pending):
            out.append(self.sentence(self.pending[start:end.end()]))
            start = end.end()
        self.pending = self.pending[start:]
        return ''.join(out)

    def flush(self) -> str:
        if not self.active:
            return ''
        rest, self.pending = self.pending, ''
        out = self.sentence(rest) if rest else ''
        # Too few other sentences: what was held back stays after all.
        out += ''.join(sentence for sentence, _flagged in self.held)
        self.held = []
        return out

    def flagged(self, sentence: str) -> bool:
        words = plain(sentence)
        return any(rx.search(words) for rx in self.remove)

    def sentence(self, sentence: str) -> str:
        sentence = swapped(sentence, self.pairs) if self.pairs else sentence
        flagged, counts = self.flagged(sentence), bool(sentence.strip())
        if flagged and self.kept >= 2:
            self.removed += 1
            return '\n\n' if '\n\n' in sentence else ''
        if flagged or self.held:
            self.held.append((sentence, flagged))
            return self.release()
        self.kept += counts
        return sentence

    def release(self) -> str:
        others = sum(bool(sentence.strip()) for sentence, flagged in self.held if not flagged)
        if self.kept + others < 2:
            return ''
        out = []
        for sentence, flagged in self.held:
            if flagged:
                self.removed += 1
                out.append('\n\n' if '\n\n' in sentence else '')
            else:
                out.append(sentence)
        self.kept += others
        self.held = []
        return ''.join(out)


def tidy(text: str, plan: dict | None, in_character: bool = True) -> str:
    """The whole text, tidied as a streamed reply is."""
    tidier = Tidy(plan, in_character)
    return tidier.feed(text) + tidier.flush()


# Settings ---------------------------------------------------------------------------------------------------------

def listing(connection, timeline_id, definition, messages) -> dict:
    rows = rules(connection)
    hidden = {row['phrase'].casefold() for row in rows if row['action'] in ('keep', 'dismiss')}
    items = [item for item in caught(connection, timeline_id, definition, messages, rows)
             if item['phrase'].casefold() not in hidden]
    return {'rules': [public(row) for row in rows if row['action'] != 'dismiss'],
            'caught': [{'phrase': item['phrase'], 'kind': item['kind'], 'step': item['step']} for item in items],
            'limit': MAX_RULES}


def public(row) -> dict:
    return {key: row[key] for key in ('id', 'phrase', 'action', 'replacement')} | {'everyone': bool(row['everyone'])}


def add(connection, phrase: str, action: str, replacement: str, everyone: bool, now: str) -> dict:
    phrase = ' '.join(phrase.split()) if WORD.search(phrase) else phrase.strip()
    require(bool(phrase), 'Write the words first.', 422)
    require(action in ACTIONS, 'Unknown action.', 422)
    listed = action != 'dismiss'
    if listed:
        count = one(connection, "SELECT COUNT(*) AS n FROM word_rules WHERE action!='dismiss'")['n']
        require(count < MAX_RULES, f'Your list holds {MAX_RULES} entries. Remove one to add another.', 409)
    # One entry a phrase for each use: Keep and Dismiss replace each other, a drop or swap replaces its own kind.
    same = ('keep', 'dismiss') if action in ('keep', 'dismiss') else (action, action)
    connection.execute('DELETE FROM word_rules WHERE phrase=? COLLATE NOCASE AND action IN (?, ?)', (phrase, *same))
    row_id = identifier()
    connection.execute('INSERT INTO word_rules (id, phrase, action, replacement, everyone, created_at) '
                       'VALUES (?, ?, ?, ?, ?, ?)',
                       (row_id, phrase, action, replacement if action == 'swap' else '', int(everyone), now))
    return public(optional(connection, 'SELECT * FROM word_rules WHERE id=?', (row_id,)))


def remove(connection, rule_id: str):
    connection.execute('DELETE FROM word_rules WHERE id=?', (rule_id,))


def carry(connection, source):
    """Entering a world (companion/worlds.py): the user's rules for every world come along from the one they left,
    in place of the ones there. `connection` is a plain sqlite3 connection to the world entered; `source` the path of
    the world left. A world from before word_rules has none to bring."""
    connection.execute('ATTACH DATABASE ? AS left_world', (str(source),))
    try:
        rows = connection.execute('SELECT id, phrase, action, replacement, created_at FROM left_world.word_rules '
                                  'WHERE everyone=1').fetchall()
        connection.execute('DELETE FROM main.word_rules WHERE everyone=1')
        connection.executemany('INSERT OR REPLACE INTO main.word_rules (id, phrase, action, replacement, everyone, '
                               'created_at) VALUES (?, ?, ?, ?, 1, ?)', rows)
    except sqlite3.OperationalError:
        pass
    finally:
        connection.execute('DETACH DATABASE left_world')
