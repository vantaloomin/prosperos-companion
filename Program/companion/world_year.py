"""The year a world runs in: Back when (Feature Hit List #79, 1.2 "The Dark Backward").

A world can run in a past year. Its clock is anchored that many years back and runs at real speed from there, so
today in a 2009 world is today's date in 2009, at the user's real time of day. Everything that reads the time reads
the app clock (companion/clock.py AppClock), so birthdays, seasons, holidays, the calendar, the paper and Our history
follow without special cases, and debug time still works on top. The offset is a whole number of days fixed when the
world is made, so its clock never jumps (a start on 29 February lands on the 28th).

The clock asks the Database how far behind the world it serves runs, per world: work pinned to one world keeps its
year while the user opens another (companion/database.py PINNED).

Real-world lookups (weather, news, charts: companion/mcp/lookups.py) belong to the present and stay off in a past
year. A world's year is set when it is made (`create_world`'s `year`) and then stays: moving it later would run the
clock back past what already happened there.
"""
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from companion.clock import PRESENT
from companion.errors import require

# Back when goes back as far as 1990 (Vanta, 2026-10-28): the 1990s, 2000s and 2010s each get their decade.
EARLIEST = 1990


def same_day(today: date, year: int) -> date:
    """Today's date in another year; 29 February becomes the 28th where that year has none."""
    try:
        return today.replace(year=year)
    except ValueError:
        return today.replace(year=year, day=28)


def offset_days(year: int, today: date) -> int:
    return (today - same_day(today, year)).days


def check(year: int, today: date):
    require(EARLIEST <= year < today.year, f'Pick a year from {EARLIEST} to {today.year - 1}.', 422)


def stored(path: Path) -> dict | None:
    """The world's year as its database holds it, read without opening it for writing; None in the present, and for
    a database that does not exist yet or predates the table."""
    if not Path(path).is_file():
        return None
    connection = sqlite3.connect(f'{Path(path).resolve().as_uri()}?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute('SELECT * FROM world_year WHERE id=1').fetchone()
    except sqlite3.OperationalError:
        return None
    finally:
        connection.close()
    return dict(row) if row else None


def load(database, year: int | None = None) -> dict | None:
    """Anchor the clock for the world being opened. A new world asked to start in `year` gets its offset now, before
    anything in it is stamped; the row to write is returned for Database.open to store with the new tables."""
    row, new = stored(database.path), None
    if row is None and year:
        today = database.clock.real().date()
        check(year, today)
        row = new = {'year': year, 'offset_days': offset_days(year, today)}
    database.behind[database.path] = timedelta(days=row['offset_days']) if row else PRESENT
    return new


def write(connection, row: dict, timestamp: str):
    connection.execute('INSERT OR IGNORE INTO world_year (id, started_year, offset_days, created_at) '
                       'VALUES (1, ?, ?, ?)', (row['year'], row['offset_days'], timestamp))


def past(connection) -> bool:
    """Whether this world runs in a past year."""
    row = connection.execute('SELECT offset_days FROM world_year WHERE id=1').fetchone()
    return bool(row and row[0])


def world_year(database, timezone=None) -> int:
    """The year it is in the world being served (in `timezone` when given): 2009 in a world started in 2009, and
    2010 there a year later."""
    now = database.clock.now()
    return (now.astimezone(timezone) if timezone else now).year


def years_back(database) -> int:
    """How many years behind the real year the world runs: 0 in the present."""
    return round(database.behind.get(database.path, PRESENT).days / 365.2425)


def year_in(path: Path, real_now) -> int | None:
    """The year it is now in a world that runs in the past, read from its database without opening it (the worlds
    list); None for a world in the present."""
    row = stored(path)
    return (real_now - timedelta(days=row['offset_days'])).year if row else None


def view(database) -> dict:
    with database.connect() as connection:
        row = connection.execute('SELECT started_year FROM world_year WHERE id=1').fetchone()
    return {'year': world_year(database), 'started_year': row[0] if row else None, 'years_back': years_back(database)}
