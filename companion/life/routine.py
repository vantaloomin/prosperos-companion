"""Routine blocks and the concrete slots they produce in the companion's timezone (PRD T1, T2, C5).

A slot is one block on one local calendar date. Its key is `block@date`, so daylight-saving
changes, a timezone change or a clock moving backward can move a slot's instants but can never
produce a second slot for the same block and day.
"""
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from companion.clock import stamp, zone

# Used while a character has no structured schedule, so a new companion still has a day.
DEFAULT_SCHEDULE = (
    {'key': 'morning', 'label': 'Morning', 'kind': 'leisure', 'start': '09:00', 'end': '12:00'},
    {'key': 'afternoon', 'label': 'Afternoon', 'kind': 'leisure', 'start': '13:00', 'end': '17:00'},
    {'key': 'evening', 'label': 'Evening', 'kind': 'leisure', 'start': '18:00', 'end': '22:00'},
    {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'},
)
# Kinds that describe availability only; nothing is simulated inside them.
RESTING = {'sleep'}


@dataclass(frozen=True)
class Block:
    key: str
    label: str
    kind: str
    days: tuple[int, ...]
    start: time
    end: time
    themes: tuple[str, ...]

    def view(self) -> dict:
        return {'key': self.key, 'label': self.label, 'kind': self.kind, 'days': list(self.days),
                'start': self.start.strftime('%H:%M'), 'end': self.end.strftime('%H:%M'),
                'themes': list(self.themes)}


@dataclass(frozen=True)
class Slot:
    block: Block
    local_date: date
    starts_at: datetime
    ends_at: datetime

    @property
    def key(self) -> str:
        return f'{self.block.key}@{self.local_date.isoformat()}'

    def view(self) -> dict:
        return {'key': self.key, 'block': self.block.view(), 'local_date': self.local_date.isoformat(),
                'starts_at': stamp(self.starts_at), 'ends_at': stamp(self.ends_at)}


def slug(label: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-')[:60] or 'block'


def clock_time(value: str) -> time:
    hours, minutes = value.split(':')
    return time(int(hours), int(minutes))


def blocks(definition: dict) -> tuple[list[Block], bool]:
    """The character's schedule with stable keys, or the default schedule when none is set."""
    raw = definition.get('schedule') or []
    default = not raw
    seen, result = set(), []
    for item in (DEFAULT_SCHEDULE if default else raw):
        key = item.get('key') or slug(item['label'])
        base, index = key, 2
        while key in seen:
            key, index = f'{base}-{index}', index + 1
        seen.add(key)
        result.append(Block(key, item['label'], item.get('kind', 'leisure'), tuple(item.get('days', range(7))),
                            clock_time(item['start']), clock_time(item['end']), tuple(item.get('themes', ()))))
    return result, default


def slots(schedule: list[Block], timezone: str, start: datetime, end: datetime) -> list[Slot]:
    """Every slot that overlaps [start, end), in start order."""
    tz = zone(timezone)
    first, last = start.astimezone(tz).date() - timedelta(days=1), end.astimezone(tz).date()
    result = []
    day = first
    while day <= last:
        for block in schedule:
            if day.weekday() not in block.days:
                continue
            slot = make_slot(block, day, tz)
            if slot and slot.starts_at < end and slot.ends_at > start:
                result.append(slot)
        day += timedelta(days=1)
    return sorted(result, key=lambda slot: (slot.starts_at, slot.block.key))


def make_slot(block: Block, day: date, tz) -> Slot | None:
    """Local wall times resolve with fold=0, so a repeated hour uses its first occurrence."""
    end_day = day + timedelta(days=1) if block.end <= block.start else day
    starts_at = datetime.combine(day, block.start, tzinfo=tz).astimezone(UTC)
    ends_at = datetime.combine(end_day, block.end, tzinfo=tz).astimezone(UTC)
    if ends_at <= starts_at:
        return None
    return Slot(block, day, starts_at, ends_at)


def current_and_next(schedule: list[Block], timezone: str, now: datetime) -> tuple[Slot | None, Slot | None]:
    """What the routine says the companion is doing now, and what comes next (for Today and C5)."""
    window = slots(schedule, timezone, now - timedelta(days=1), now + timedelta(days=2))
    current = next((slot for slot in window if slot.starts_at <= now < slot.ends_at), None)
    upcoming = next((slot for slot in window if slot.starts_at > now), None)
    return current, upcoming
