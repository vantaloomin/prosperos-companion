"""The Story's chapters and the time on each line (docs/story.md, "Chapters and times").

The Story is one ongoing story in a world that keeps going, so it is never finished and nothing has to be cleared to
go on with it. Chapters break it up on the page. Rules decide them from the lines' own times, with nothing stored: a
line that comes two hours or more after the one before it starts a new chapter (the stretch a visit ends at,
companion/story_visits.py). A reply never starts one, so a reply told again the next day stays with its line. The
user can also start a chapter themself (`story_chapters`: the next line after `after_seq` starts it).

Chapters and times are for the page and the export only: no model reads them.
"""
from datetime import datetime

from companion.clock import parse, zone
from companion.database import many, one
from companion.errors import DomainError, require
from companion.story_visits import IDLE

GAP = IDLE


def marks(connection, now: datetime) -> tuple[list[int], str | None]:
    """The seq of every line that starts a chapter after the first, in order, and whether another chapter is waiting
    for its first line: 'asked' when the user started it, 'time' when the story was left long enough, else None."""
    rows = many(connection, 'SELECT seq, created_at, gap FROM (SELECT seq, reply_to, created_at, julianday(created_at) - '
                'julianday(LAG(created_at) OVER (ORDER BY seq)) AS gap FROM story_messages) WHERE reply_to IS NULL '
                'ORDER BY seq')
    asked = [row['after_seq'] for row in many(connection, 'SELECT after_seq FROM story_chapters ORDER BY after_seq')]
    days, starts, due = GAP.total_seconds() / 86400, [], False
    for row in rows:
        while asked and asked[0] < row['seq']:
            asked.pop(0)
            due = True
        if due or (row['gap'] is not None and row['gap'] >= days):
            starts.append(row['seq'])
        due = False
    if not rows:
        return [], None
    last = one(connection, 'SELECT created_at FROM story_messages ORDER BY seq DESC LIMIT 1')
    waiting = 'asked' if asked else 'time' if now - parse(last['created_at']) >= GAP else None
    return starts, waiting


def number(starts: list[int], seq: int) -> int:
    """Which chapter the line with this seq is in, from 1."""
    return 1 + sum(1 for start in starts if start <= seq)


def zones(connection, rows: list[dict], data: dict | None = None) -> dict:
    """Each city's own clock for the lines' times, as the scene has it (the companion's own in their city). `data` is
    the city the story is in now, when the caller has it. A city that has since gone is read on that city's clock."""
    from companion import story
    found = {data['id']: zone(data['timezone'])} if data else {}
    for city_id in {row['city_id'] for row in rows} - set(found):
        try:
            found[city_id] = zone(story.city_data(connection, city_id)['timezone'])
        except DomainError:
            here = data or story.city_data(connection, story.scene_row(connection)['city_id'])
            found[city_id] = zone(here['timezone'])
    return found


def moment(row: dict, clocks: dict) -> datetime:
    """When a line was written, on its city's clock."""
    return parse(row['created_at']).astimezone(clocks[row['city_id']]).replace(tzinfo=None)


def local(row: dict, clocks: dict) -> str:
    """The same with no offset, as the scene's `local_time` is."""
    return moment(row, clocks).isoformat(timespec='minutes')


def dated(connection, rows: list[dict], view: dict) -> dict:
    """The lines with their `chapter` and `local_time`, the `chapters` they are in (each with the time of its first
    line, which the history limit may have cut off) and the `next_chapter` waiting for its first line, if one is."""
    starts, waiting = marks(connection, view['now'])
    shown = sorted({number(starts, row['seq']) for row in rows})
    opening = one(connection, 'SELECT MIN(seq) AS seq FROM story_messages')['seq']
    first_seq = {chapter: starts[chapter - 2] if chapter > 1 else opening for chapter in shown}
    firsts = {row['seq']: row for row in many(
        connection, f"SELECT seq, city_id, created_at FROM story_messages WHERE seq IN ({','.join('?' * len(shown))})",
        tuple(first_seq.values()))}
    clocks = zones(connection, [*rows, *firsts.values()], view['data'])
    return {'messages': [{**row, 'chapter': number(starts, row['seq']), 'local_time': local(row, clocks)} for row in rows],
            'chapters': [{'number': chapter, 'local_time': local(firsts[first_seq[chapter]], clocks)} for chapter in shown],
            'next_chapter': {'number': len(starts) + 2, 'by': waiting, 'local_time': view['local_time']} if waiting else None}


def begin(connection, now: str) -> None:
    """The user starts a new chapter: the next line begins it. Nothing is cleared. Asked twice, or when one is
    already waiting, it changes nothing."""
    last = one(connection, 'SELECT MAX(seq) AS seq FROM story_messages')['seq']
    require(last is not None, 'There is nothing in your story yet.', 409)
    connection.execute('INSERT OR IGNORE INTO story_chapters (after_seq, created_at) VALUES (?, ?)', (last, now))


def undo(connection) -> None:
    """Take back a chapter the user started, while nothing has been said in it."""
    connection.execute('DELETE FROM story_chapters WHERE after_seq >= COALESCE((SELECT MAX(seq) FROM story_messages '
                       'WHERE reply_to IS NULL), 0)')
