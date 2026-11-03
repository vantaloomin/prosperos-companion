"""Plans that are over close on their own (Vanta, 2026-10-30: "they don't go away once they are effectively done").

The world moves on without the user: once a plan's day has passed, or a plan with no date has gone unmentioned for
QUIET days, it is taken as done. It is marked in place (`settled_from` keeps the open status it had), so the
missed-plan reaction and anything keyed on the plan still find it. The user overrides from Memories ("It didn't
happen", "It moved"); their correction is a new revision with no `settled_from`, and a plan they restate after its
day gets QUIET days of its own before it closes again.
"""
from datetime import UTC, datetime, timedelta

from companion.clock import stamp
from companion.database import bump_memory_revision, many
from companion.memory.records import OPEN_PLANS

AFTER_DAY = timedelta(days=1)  # Past its day: a time on the day ("tonight at 8") is covered too.
UNCERTAIN = timedelta(days=3)  # A best-guess date gets a few more days.
QUIET = timedelta(days=14)
# A plan the memory model picked out of a chat with no day in it ("boil the meat next time") is a passing intention:
# it goes after a quiet week, as the tester expected (2026-11-03).
QUIET_GUESS = timedelta(days=7)
# Thinking about moving is a standing consideration, not something that gets done.
STANDING = ('possible_move',)


def instant(value: str) -> datetime:
    """A stored time; a bare day (written by hand or by an older build) is that day in UTC."""
    found = datetime.fromisoformat(value)
    return found if found.tzinfo else found.replace(tzinfo=UTC)


def due(plan) -> datetime | None:
    """When an open plan is over; None for one that never closes on its own."""
    if plan['subject_key'] in STANDING:
        return None
    said = instant(plan['stated_at'])
    day = plan['applies_until'] or plan['applies_from']
    quiet = QUIET_GUESS if plan['origin'] == 'automatic' else QUIET
    if day is None:
        return said + quiet
    over = instant(day) + AFTER_DAY + (UNCERTAIN if plan['dates_uncertain'] else timedelta())
    return over if said < over else said + quiet


def settle(connection, now) -> int:
    """Close every open plan that is over. Returns how many closed."""
    marks = ','.join('?' * len(OPEN_PLANS))
    plans = many(connection, "SELECT id, subject_key, stated_at, applies_from, applies_until, dates_uncertain, "
                 f"plan_status, origin FROM memories WHERE status IN ('active','excluded') AND layer='plan' "
                 f'AND plan_status IN ({marks})', OPEN_PLANS)
    over = [plan for plan in plans if (when := due(plan)) is not None and when <= now]
    if not over:
        return 0
    timestamp = stamp(now)
    connection.executemany("UPDATE memories SET plan_status='completed', settled_from=?, updated_at=? WHERE id=?",
                           [(plan['plan_status'], timestamp, plan['id']) for plan in over])
    bump_memory_revision(connection, timestamp)
    return len(over)
