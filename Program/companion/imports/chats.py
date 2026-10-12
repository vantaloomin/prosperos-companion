"""Bring your old chats (Hit List #37): a SillyTavern chat or a role/content transcript as older history.

Reading the two formats is adapted from prosperos-study server/migration/transcript_conversion.py
(`sillytavern`, `role_messages`). Changes: nothing is reviewed or mapped by hand; the user's lines become
the user's, everyone else's the companion's; system, narrator and hidden lines are left out; the selected
swipe is taken and its date read (`send_date` in SillyTavern's several formats, ISO text or epoch numbers).

The world exists outside of the user, so an import asks nothing: the messages land before everything
already in the chat (lower `seq`), dated from the file or, without dates, in made-up sittings ending an
hour before the first message there. Each carries `import_id`, so it reads as history but never counts as
new conversation: no reply, unread count, notification, mood, opener, recap, usual hours, closeness or
consequence comes from it (each of those reads `import_id IS NULL`, and `records.from_old_chats` keeps what
only an old chat said out of plans to follow up and shared moments). The user's lines go through the usual
rule-based memory pass (memory/formation.py) at once, in bounded batches and without a model call, so recall
finds what was said back then; a fact stated there never ends or corrects one said later.
"""
import base64
import binascii
import hashlib
import json
import re
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import PureWindowsPath

from companion.characters import by_id, require_current
from companion.clock import parse, stamp, zone
from companion.database import identifier, one, optional, settings
from companion.errors import DomainError, require
from companion.memory import formation

MAX_BYTES = 10 * 1024 * 1024
MAX_LINES = 20000
TEXT_LIMIT = 20000
# Undated lines are spaced as sittings of SITTING messages, STEP apart, a day between sittings.
SITTING = 60
STEP = timedelta(minutes=2)
BETWEEN = timedelta(days=1)
BEFORE_FIRST = timedelta(hours=1)
MEMORY_BATCH = 500
EARLIEST = datetime(1990, 1, 1, tzinfo=UTC)
HEADER_KEYS = ('chat_metadata', 'user_name', 'character_name')
ROLES = {'user': 'user', 'human': 'user', 'you': 'user', 'assistant': 'companion', 'model': 'companion',
         'bot': 'companion', 'ai': 'companion', 'char': 'companion', 'character': 'companion'}
DATE_KEYS = ('send_date', 'timestamp', 'created_at', 'create_time', 'date', 'time')
# SillyTavern's own stamp ("2024-3-1 @14h 05m 09s 120ms") and its older long form ("March 1, 2024 2:05pm").
HUMANIZED = re.compile(r'(\d{4})-(\d{1,2})-(\d{1,2})\s*@\s*(\d{1,2})h\s*(\d{1,2})m\s*(\d{1,2})s(?:\s*(\d{1,3})ms)?')
LONG_FORMS = ('%B %d, %Y %I:%M%p', '%B %d, %Y %I:%M %p', '%b %d, %Y %I:%M%p', '%b %d, %Y %I:%M %p',
              '%B %d, %Y %H:%M', '%B %d, %Y', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M:%S')


@dataclass
class Line:
    role: str
    text: str
    at: datetime | None


# Reading the file ---------------------------------------------------------------------------------

def decoded(data: str) -> bytes:
    try:
        raw = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError) as error:
        raise DomainError('The chat file did not arrive whole. Try choosing it again.', 422) from error
    require(len(raw) <= MAX_BYTES, 'Chat files are limited to 10 MB.', 413)
    return raw


def records(raw: bytes) -> object:
    """The whole file as JSON, or its lines as JSONL (one value per non-empty line)."""
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError as error:
        raise DomainError('This file is not a chat export: it is not text.', 422) from error
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    lines = [line for line in text.splitlines() if line.strip()]
    require(len(lines) <= MAX_LINES + 1, f'Chats are limited to {MAX_LINES:,} messages per file.', 413)
    try:
        return [json.loads(line) for line in lines]
    except json.JSONDecodeError as error:
        raise DomainError('This file is not a SillyTavern chat or a JSON list of messages.', 422) from error


def is_header(value) -> bool:
    return isinstance(value, dict) and 'mes' not in value and any(key in value for key in HEADER_KEYS)


def shaped(found) -> tuple[str, list, object]:
    """(format, rows, reader): SillyTavern JSONL with or without its header, else role/content messages
    as a list or under `messages`."""
    if isinstance(found, dict) and (is_header(found) or 'mes' in found):
        found = [found]
    if isinstance(found, list) and found and isinstance(found[0], dict) and (is_header(found[0]) or 'mes' in found[0]):
        return 'sillytavern', found[1:] if is_header(found[0]) else found, tavern_line
    rows = found.get('messages') if isinstance(found, dict) else found
    require(isinstance(rows, list), 'This file is not a SillyTavern chat or a JSON list of messages.', 422)
    return 'messages', rows, role_line


def read(raw: bytes, timezone: str) -> tuple[str, list[Line], int]:
    """(format, lines kept, lines left out)."""
    kind, rows, reader = shaped(records(raw))
    require(len(rows) <= MAX_LINES, f'Chats are limited to {MAX_LINES:,} messages per file.', 413)
    lines = [reader(row, timezone) for row in rows]
    kept = [line for line in lines if line]
    require(kept, 'There are no messages from you or the character in this file.', 422)
    return kind, kept, len(lines) - len(kept)


def clipped(text) -> str:
    return text.strip()[:TEXT_LIMIT] if isinstance(text, str) else ''


def chosen_swipe(row: dict):
    """The alternative the user had picked, else the message text."""
    swipes, index = row.get('swipes'), row.get('swipe_id')
    if isinstance(swipes, list) and isinstance(index, int) and 0 <= index < len(swipes):
        return swipes[index]
    return row.get('mes')


def tavern_line(row, timezone) -> Line | None:
    """One SillyTavern message; system and narrator lines (and hidden ones, which are system) are left out."""
    if not isinstance(row, dict) or row.get('is_system') or (row.get('extra') or {}).get('type') == 'narrator':
        return None
    text = clipped(chosen_swipe(row))
    return Line('user' if row.get('is_user') else 'companion', text, when(row.get('send_date'), timezone)) \
        if text else None


def content(value) -> str:
    """Plain text, or the text parts of a list of content parts."""
    if isinstance(value, list):
        value = '\n'.join(part if isinstance(part, str) else str(part.get('text') or '')
                          for part in value if isinstance(part, str | dict))
    return clipped(value)


def role_line(row, timezone) -> Line | None:
    if not isinstance(row, dict):
        return None
    role, text = ROLES.get(str(row.get('role', '')).strip().casefold()), content(row.get('content'))
    if not role or not text:
        return None
    stamps = (when(row.get(key), timezone) for key in DATE_KEYS)
    return Line(role, text, next((at for at in stamps if at), None))


# Dates --------------------------------------------------------------------------------------------

def from_number(value: float) -> datetime | None:
    """Epoch seconds, or milliseconds when the number is too large to be seconds."""
    try:
        return datetime.fromtimestamp(value / 1000 if abs(value) > 1e11 else value, UTC)
    except (OverflowError, OSError, ValueError):
        return None


def from_text(text: str) -> datetime | None:
    if match := HUMANIZED.fullmatch(text):
        year, month, day, hour, minute, second, millis = (int(part or 0) for part in match.groups())
        try:
            return datetime(year, month, day, hour, minute, second, millis * 1000)
        except ValueError:
            return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    for form in LONG_FORMS:
        try:
            return datetime.strptime(text, form)
        except ValueError:
            continue
    return None


def when(value, timezone: str) -> datetime | None:
    """A line's date, if it has a believable one. A date without an offset is the user's local time."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        found = from_number(value)
    elif isinstance(value, str) and (text := value.strip()):
        found = from_number(float(text)) if re.fullmatch(r'\d+(?:\.\d+)?', text) else from_text(text)
    else:
        return None
    if found is not None and found.tzinfo is None:
        found = found.replace(tzinfo=zone(timezone))
    return found.astimezone(UTC) if found is not None and found >= EARLIEST else None


def placed(lines: list[Line], first_existing: datetime, now: datetime) -> list[datetime]:
    """When each line was said: the file's dates, gaps filled a STEP after the last, never going back
    and never later than now; with no dates at all, sittings ending just before the chat's first message."""
    known = [index for index, line in enumerate(lines) if line.at]
    if not known:
        end, count = first_existing - BEFORE_FIRST, len(lines)
        return [end - (back // SITTING) * BETWEEN - (back % SITTING) * STEP
                for back in (count - 1 - index for index in range(count))]
    result, previous = [], lines[known[0]].at - STEP * (known[0] + 1)
    for line in lines:
        previous = min(max(line.at, previous) if line.at else previous + STEP, now)
        result.append(previous)
    return result


# Writing ------------------------------------------------------------------------------------------

def companion_for(connection, companion_id: str | None) -> dict:
    """The named companion, main or stepped back, or else the one in focus."""
    if not companion_id:
        return require_current(connection)
    found = by_id(connection, companion_id)
    require(found is not None and found['active_timeline_id'] is not None, 'That companion was not found.', 404)
    return found


def first_seq_and_time(connection, timeline_id, now: datetime) -> tuple[int, datetime]:
    """The lowest seq to write below (0 is never used, as a client reads it as "no page"), and when the
    chat's first message was said."""
    row = one(connection, 'SELECT MIN(seq) AS seq, MIN(created_at) AS at FROM messages WHERE timeline_id=?',
              (timeline_id,))
    top = min(row['seq'] if row['seq'] is not None else 1, 1) - 1
    return (top if top < 0 else -1), (parse(row['at']) if row['at'] else now)


def write_messages(connection, companion, import_id, lines, times, last_seq) -> list[str]:
    """Insert the lines oldest first; a companion line answers the user line before it, unless it already
    has an answer (then it stands alone, like a message the companion sent first). Returns the user lines."""
    timeline_id, version_id = companion['active_timeline_id'], companion['active_version_id']
    first, users, waiting, rows = last_seq - len(lines) + 1, [], None, []
    for offset, (line, at) in enumerate(zip(lines, times, strict=True)):
        message_id, created = identifier(), stamp(at)
        reply_to = waiting if line.role == 'companion' else None
        waiting = message_id if line.role == 'user' else None
        if line.role == 'user':
            users.append(message_id)
        rows.append((message_id, timeline_id, first + offset, line.role, line.text, reply_to, version_id, created,
                     created, import_id))
    connection.executemany(
        'INSERT INTO messages (id, timeline_id, seq, role, text, reply_to, status, active, character_version_id, '
        "created_at, completed_at, import_id) VALUES (?, ?, ?, ?, ?, ?, 'complete', 1, ?, ?, ?, ?)", rows)
    return users


def remember(database, companion_id, message_ids, dated: bool) -> int:
    """The usual rule-based pass over the user's lines, MEMORY_BATCH per transaction so a long chat never
    holds the database for long. Each line's job is recorded done, with model suggestions skipped. Without dates
    in the file, "tomorrow" counted from a made-up time is a guess, so such dates are marked uncertain."""
    count = 0
    for start in range(0, len(message_ids), MEMORY_BATCH):
        with database.connect(write=True) as connection:
            row, companion, timestamp = settings(connection), companion_for(connection, companion_id), database.now()
            if not row['automatic_memory']:
                return count
            for message_id in message_ids[start:start + MEMORY_BATCH]:
                count += formed(connection, companion, message_id, row['permission_revision'], timestamp, dated)
    return count


def formed(connection, companion, message_id, revision, timestamp, dated=True) -> int:
    """One user line through formation; a line the rules trip over is marked failed, as a queued job would be."""
    message, status = one(connection, 'SELECT * FROM messages WHERE id=?', (message_id,)), 'done'
    try:
        with savepoint(connection):
            written = formation.form(connection, companion, message, timestamp, deliberate=False)
            if not dated:
                connection.executemany('UPDATE memories SET dates_uncertain=1 WHERE id=? AND '
                                       '(applies_from IS NOT NULL OR applies_until IS NOT NULL)',
                                       [(memory['id'],) for memory in written])
            found = len(written)
    except Exception:  # noqa: BLE001 - one unreadable line never stops the rest of the history.
        found, status = 0, 'failed'
    connection.execute('INSERT OR IGNORE INTO memory_jobs (message_id, permission_revision, status, queued_at, '
                       "finished_at, model_status) VALUES (?, ?, ?, ?, ?, 'skipped')",
                       (message_id, revision, status, timestamp, timestamp))
    return found


@contextmanager
def savepoint(connection):
    connection.execute('SAVEPOINT line')
    try:
        yield
    except Exception:
        connection.execute('ROLLBACK TO line')
        connection.execute('RELEASE line')
        raise
    connection.execute('RELEASE line')


def bring(database, filename: str, data: str, companion_id: str | None = None) -> dict:
    """Read the file outside any transaction, write its lines in one, then remember from them in batches."""
    raw = decoded(data)
    digest, now = hashlib.sha256(raw).hexdigest(), database.clock.now()
    with database.connect() as connection:
        companion_for(connection, companion_id)
        timezone = settings(connection)['user_timezone']
    kind, lines, skipped = read(raw, timezone)
    with database.connect(write=True) as connection:
        companion = companion_for(connection, companion_id)
        timeline_id = companion['active_timeline_id']
        require(not optional(connection, 'SELECT 1 FROM chat_imports WHERE sha256=? AND id IN '
                             '(SELECT import_id FROM messages WHERE timeline_id=?)', (digest, timeline_id)),
                'This chat already came in.', 409)
        last_seq, first_at = first_seq_and_time(connection, timeline_id, now)
        times, import_id = placed(lines, first_at, now), identifier()
        connection.execute(
            'INSERT INTO chat_imports (id, companion_id, timeline_id, filename, format, sha256, messages, skipped, '
            'memories, dated, first_at, last_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)',
            (import_id, companion['id'], timeline_id, PureWindowsPath(filename).name[:200], kind, digest, len(lines),
             skipped, int(any(line.at for line in lines)), stamp(times[0]), stamp(times[-1]), database.now()))
        users = write_messages(connection, companion, import_id, lines, times, last_seq)
    memories = remember(database, companion['id'], users, any(line.at for line in lines))
    with database.connect(write=True) as connection:
        connection.execute('UPDATE chat_imports SET memories=? WHERE id=?', (memories, import_id))
        return summary(connection, import_id)


def summary(connection, import_id) -> dict:
    row = one(connection, 'SELECT * FROM chat_imports WHERE id=?', (import_id,))
    remembering = bool(settings(connection)['automatic_memory'])
    return {**row, 'dated': bool(row['dated']), 'automatic_memory': remembering}
