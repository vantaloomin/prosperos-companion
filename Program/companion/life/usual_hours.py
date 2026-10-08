"""When the user is usually around, learned from when they start conversations.

Rules only, no model and nothing stored: the user's own messages from the last four weeks, in the user's
timezone, split into weekdays and weekends. A message counts when the user starts an exchange (nothing in
the conversation for a while before it, and not an answer to a text the companion started, so the
companion's own first texts never teach it the hours). A half hour is usual when the user started a
conversation in it on enough different days; neighbouring usual half hours join into one stretch.
The app never shows these hours anywhere; they only decide when the companion might reach out.
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from companion.clock import parse, stamp, zone
from companion.database import many, settings

LOOKBACK = timedelta(days=28)
# Silence before a user message for it to count as starting an exchange.
QUIET_BEFORE = timedelta(minutes=45)
SLOT_MINUTES = 30
# A usual half hour: a start on at least this many days, and on this share of the days the user wrote at all.
MIN_DAYS = 3
SHARE = 0.3


@dataclass(frozen=True)
class Stretch:
    start: time
    end: time
    days: int


def weekend(day: date) -> bool:
    return day.weekday() >= 5


def starts(connection, now) -> list[datetime]:
    """Times (UTC) the user started an exchange in the lookback, across every companion and timeline."""
    rows = many(connection, """
        SELECT created_at, previous_at, previous_id FROM (
          SELECT m.role, m.created_at,
                 LAG(m.created_at) OVER (PARTITION BY m.timeline_id ORDER BY m.seq) AS previous_at,
                 LAG(m.id) OVER (PARTITION BY m.timeline_id ORDER BY m.seq) AS previous_id
          FROM messages m WHERE m.status='complete' AND m.active=1)
        WHERE role='user' AND created_at>=? AND created_at<=?""",
                (stamp(now - LOOKBACK), stamp(now)))
    openers = {row['message_id'] for row in many(connection, 'SELECT message_id FROM openers')}
    found = []
    for row in rows:
        at = parse(row['created_at'])
        if row['previous_at'] is None:
            found.append(at)
        elif row['previous_id'] not in openers and at - parse(row['previous_at']) >= QUIET_BEFORE:
            found.append(at)
    return found


def stretches(connection, now, on_weekend: bool) -> list[Stretch]:
    """The user's usual stretches of the day (their local time) for weekdays or weekends."""
    user_zone = zone(settings(connection)['user_timezone'])
    slots: dict[int, set[date]] = {}
    active: set[date] = set()
    for at in starts(connection, now):
        local = at.astimezone(user_zone)
        if weekend(local.date()) != on_weekend:
            continue
        active.add(local.date())
        slots.setdefault((local.hour * 60 + local.minute) // SLOT_MINUTES, set()).add(local.date())
    needed = max(MIN_DAYS, SHARE * len(active))
    usual = sorted(slot for slot, days in slots.items() if len(days) >= needed)
    result, run = [], []
    for slot in usual:
        if run and slot != run[-1] + 1:
            result.append(_stretch(run, slots))
            run = []
        run.append(slot)
    if run:
        result.append(_stretch(run, slots))
    return result


def around_now(connection, now) -> tuple[Stretch, datetime] | None:
    """(stretch, its start today) when it is one of the user's usual stretches right now, else None."""
    local = now.astimezone(zone(settings(connection)['user_timezone']))
    for stretch in stretches(connection, now, weekend(local.date())):
        began = local.replace(hour=stretch.start.hour, minute=stretch.start.minute, second=0, microsecond=0)
        if stretch.start <= local.time() and (stretch.end == time(0) or local.time() < stretch.end):
            return stretch, began
    return None


def _stretch(run: list[int], slots: dict[int, set[date]]) -> Stretch:
    def at(slot: int) -> time:
        minutes = (slot * SLOT_MINUTES) % (24 * 60)
        return time(minutes // 60, minutes % 60)
    return Stretch(at(run[0]), at(run[-1] + 1), max(len(slots[slot]) for slot in run))

