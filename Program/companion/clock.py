"""Real instants are stored in UTC; tests substitute a controllable clock."""
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from companion.errors import DomainError


class Clock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock(Clock):
    def __init__(self, instant: datetime):
        self.instant = instant

    def now(self) -> datetime:
        return self.instant

    def advance(self, delta):
        self.instant += delta


def stamp(instant: datetime) -> str:
    return instant.astimezone(UTC).isoformat(timespec='microseconds')


def parse(value: str | None) -> datetime | None:
    if value is None:
        return None
    instant = datetime.fromisoformat(value)
    if instant.tzinfo is None:
        raise DomainError('Times must include a UTC offset.', 422)
    return instant.astimezone(UTC)


def zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise DomainError(f'Unknown timezone: {name}.', 422) from error
