"""Debug time (Settings > Debug): check several days of a companion's life in minutes.

Everything that reads the time reads the app clock (clock.AppClock on Database.clock): life batches,
the agenda, first messages, paced replies, the feed, notifications, townsfolk and chat context. Debug
time moves that clock ahead and can run it faster, so all of them follow without special cases.

Starting takes a verified backup (Settings > Backups, "Before debug time") and a plain copy of the
database. Jumping ahead walks through the skipped time in steps, as if the app had stayed open, then
looks in once the way opening the app does. Nothing extra calls a model: what runs is what would have
run in that time. Returning to real time restores the copy, so real-time history stays as it was; the
user can keep what happened instead, but the companion's life then waits until real time catches up.
"""
import asyncio
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from companion import backup, start_over
from companion.clock import parse, stamp, zone
from companion.database import Database, many, optional, settings
from companion.errors import DomainError, require

FOLDER = 'debug-time'
SPEEDS = (1, 10, 60, 360, 1440)
MAX_JUMP = timedelta(days=30)
STEP = timedelta(minutes=15)


def snapshot_path(database: Database) -> Path:
    return database.path.parent / FOLDER / 'before-debug.sqlite3'


def load(database: Database):
    """Apply a debug time saved by an earlier run of the app, so it survives a restart."""
    with database.connect() as connection:
        row = optional(connection, 'SELECT * FROM debug_time WHERE id=1')
    if row is None:
        database.clock.reset()
        return
    database.clock.shift(parse(row['app_anchor']), row['speed'])
    database.clock.anchor_real = parse(row['real_anchor'])


def save(database: Database):
    clock = database.clock
    with database.connect(write=True) as connection:
        connection.execute('UPDATE debug_time SET app_anchor=?, real_anchor=?, speed=? WHERE id=1',
                           (stamp(clock.anchor_app), stamp(clock.anchor_real), clock.speed))


def status(database: Database, jumping: dict | None = None) -> dict:
    clock = database.clock
    with database.connect() as connection:
        row = optional(connection, 'SELECT * FROM debug_time WHERE id=1')
    view = {'active': row is not None, 'now': stamp(clock.now()), 'real_now': stamp(clock.real()),
            'speed': clock.speed, 'speeds': list(SPEEDS), 'started_at': None, 'app_started_at': None,
            'backup': None, 'jumping': jumping}
    if row:
        view.update(started_at=row['started_at'], app_started_at=row['app_started_at'], backup=row['backup'])
    return view


def start(database: Database) -> None:
    """Back up first; the copy is taken before the debug row exists, so restoring it ends debug time too."""
    with database.connect() as connection:
        if optional(connection, 'SELECT id FROM debug_time WHERE id=1'):
            return
    made = start_over.take_backup(database, 'debug')
    copy = snapshot_path(database)
    copy.parent.mkdir(parents=True, exist_ok=True)
    copy.unlink(missing_ok=True)
    backup.snapshot(database.path, copy)
    now = database.clock.now()
    database.clock.shift(now, 1)
    with database.connect(write=True) as connection:
        connection.execute('INSERT INTO debug_time (id, app_anchor, real_anchor, speed, started_at, app_started_at, '
                           'snapshot, backup) VALUES (1, ?, ?, 1, ?, ?, ?, ?)',
                           (stamp(now), stamp(database.clock.anchor_real), stamp(database.clock.real()), stamp(now),
                            copy.name, made['name']))


def require_active(database: Database):
    with database.connect() as connection:
        require(optional(connection, 'SELECT id FROM debug_time WHERE id=1') is not None,
                'Debug time is not on.', 409)


def set_speed(database: Database, speed: float):
    require(speed in SPEEDS, 'Choose one of the listed speeds.', 422)
    require_active(database)
    database.clock.shift(database.clock.now(), speed)
    save(database)


def target(database: Database, hours: float | None, local: str | None) -> datetime:
    """Where a jump lands: some hours ahead, or a date and time in the user's own timezone. Time only
    moves forward here, since the companion's life never runs backwards."""
    now = database.clock.now()
    if local is not None:
        with database.connect() as connection:
            user_zone = zone(settings(connection)['user_timezone'])
        try:
            moment = datetime.fromisoformat(local)
        except ValueError:
            raise DomainError('Give a date and time.', 422) from None
        landing = (moment if moment.tzinfo else moment.replace(tzinfo=user_zone)).astimezone(now.tzinfo)
    else:
        require(hours is not None and hours > 0, 'Jump ahead by some hours, or pick a date and time.', 422)
        landing = now + timedelta(hours=hours)
    require(landing > now, 'Pick a time after the current one. To go back, return to real time.', 422)
    require(landing - now <= MAX_JUMP, 'Jump at most 30 days at a time.', 422)
    return landing


async def walk(database: Database, life, landing: datetime, progress: dict):
    """Step through to `landing` as if the app had stayed open, then look in as opening the app does.
    Background batches run only when the user allows background activity; first messages follow their own
    setting. Optional work (pre-phrasing, real-world lookups for a spoofed day) is skipped."""
    clock, start_at = database.clock, database.clock.now()
    total = max((landing - start_at).total_seconds(), 1)
    try:
        while clock.now() < landing:
            clock.shift(min(clock.now() + STEP, landing))
            progress['done'] = min(1.0, (clock.now() - start_at).total_seconds() / total)
            await life.quietly_life('background')
            await life.quietly_text()
        await life.quietly_life('return')
    finally:
        save(database)


def image_files(path: Path) -> set[str]:
    connection = sqlite3.connect(f'{path.resolve().as_uri()}?mode=ro', uri=True)
    try:
        rows = connection.execute('SELECT output_file, raw_file FROM image_jobs').fetchall()
    finally:
        connection.close()
    return {f'images/{output}' for output, _raw in rows if output} | {f'images/raw/{raw}' for _output, raw in rows if raw}


def finish(database: Database, keep: bool) -> dict:
    """Back to real time. Unless kept, the database copy from the start replaces everything since, and
    pictures made during debug time are removed; the verified backup stays in Settings > Backups."""
    require_active(database)
    with database.connect() as connection:
        require(not many(connection, "SELECT id FROM messages WHERE status='streaming'"),
                'Wait for the reply being written to finish.', 409)
    copy = snapshot_path(database)
    if keep:
        with database.connect(write=True) as connection:
            connection.execute('DELETE FROM debug_time')
    else:
        require(copy.is_file(), 'The copy from before debug time is missing; restore the "Before debug time" '
                                'backup from Settings > Backups instead.', 409)
        made = image_files(database.path) - image_files(copy)
        backup.snapshot(copy, database.path)
        start_over.remove_files(database.path.parent, sorted(made))
    database.clock.reset()
    copy.unlink(missing_ok=True)
    return {'kept': keep}


class DebugTime:
    """One jump at a time for the running app; the walk runs as a task so the page can show progress."""

    def __init__(self, database: Database, life):
        self.database = database
        self.life = life
        self.task: asyncio.Task | None = None
        self.progress: dict | None = None

    def jumping(self) -> dict | None:
        return self.progress if self.task and not self.task.done() else None

    def status(self) -> dict:
        return status(self.database, self.jumping())

    def jump(self, hours: float | None = None, local: str | None = None) -> dict:
        require(self.jumping() is None, 'Already jumping ahead; wait for it to finish.', 409)
        require_active(self.database)
        landing = target(self.database, hours, local)
        self.progress = {'to': stamp(landing), 'done': 0.0}
        self.task = asyncio.get_running_loop().create_task(walk(self.database, self.life, landing, self.progress))
        return self.status()

    async def finish(self, keep: bool) -> dict:
        require(self.jumping() is None, 'Wait for the jump to finish.', 409)
        # Holding the life lock keeps a batch from writing into the database while the copy replaces it.
        async with self.life.lock:
            result = await asyncio.to_thread(finish, self.database, keep)
        return {**result, **self.status()}
