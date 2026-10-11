"""How a body carries one day into the next (realism: tiredness, hangovers, colds).

A small physical state is computed for each local day from the day before, with no model: a late
night out leaves someone tired, drinks can leave a hangover, a workout leaves them sore and now
and then a cold keeps them home for a few days. The state is seeded by the subject and date, so a
day filled in after a long absence and one advanced on a running server agree.

The state lives on the day's agenda blocks (`block.body`), so the event, the feed post, the chat
context and any image all describe the same tired morning. It is ordinary and never dramatic: it
changes what a day looks like, not who the character is.
"""
import random
from datetime import date, timedelta

from companion.database import decode, many

# A cold starts at most once in each period, more often in winter, and lasts a few days.
COLD_PERIOD = 28
COLD_CHANCE = {'winter': 0.3, 'other': 0.1}
COLD_DAYS = (2, 2, 3)
WINTER_MONTHS = {11, 12, 1, 2, 3}

# What the day before can leave behind, by the activity it held, with a chance for each.
AFTER = {
    'drinks': (('hungover', 0.35), ('tired', 0.45)),
    'birthday': (('hungover', 0.2), ('tired', 0.5)),
    'festival': (('tired', 0.6),),
    'show': (('tired', 0.5),),
    'dinner': (('tired', 0.25),),
    'busy-shift': (('worn out', 0.5),),
    'workout': (('sore', 0.5),),
    # Home from a trip (companion/life/trips.py), after a sunny beach weekend or any other.
    'trip-home-sun': (('sunburnt', 0.55), ('tired', 0.5)),
    'trip-home': (('tired', 0.6),),
}
# Which state wins when the day before left more than one.
ORDER = ('sick', 'hungover', 'tired', 'worn out', 'sore', 'sunburnt')
LOW = {'tired', 'hungover', 'worn out'}
MOODS = {'sick': 'under the weather', 'hungover': 'sluggish', 'tired': 'tired', 'worn out': 'drained',
         'sore': 'sore', 'sunburnt': 'sunburnt'}
CAUSES = {
    'drinks': 'after drinks{at} last night', 'birthday': "after celebrating {friend}'s birthday",
    'festival': 'after a long day out at {event}', 'show': 'after a late show{at}',
    'dinner': 'after a late dinner{at}', 'busy-shift': 'after a hectic day at work',
    'workout': "after yesterday's workout",
    'trip-home-sun': 'after a sunny weekend in {event}', 'trip-home': 'after the trip back from {event}',
}


def winter(world, definition, day: date) -> bool:
    from companion.life.composer import weather
    conditions = weather(world, definition, day.isoformat())
    if conditions and conditions.get('season'):
        return conditions['season'] == 'winter'
    return day.month in WINTER_MONTHS


def cold_days(seed: str, period: int, world, definition) -> set[date]:
    """The days of this period's cold, if it has one."""
    rng = random.Random(f'cold:{seed}:{period}')
    start = date.fromordinal(period * COLD_PERIOD + 1 + rng.randrange(COLD_PERIOD))
    chance = COLD_CHANCE['winter' if winter(world, definition, start) else 'other']
    if rng.random() >= chance:
        return set()
    return {start + timedelta(days=offset) for offset in range(rng.choice(COLD_DAYS))}


def sick(seed: str, day: date, world, definition) -> bool:
    period = (day.toordinal() - 1) // COLD_PERIOD
    return any(day in cold_days(seed, index, world, definition) for index in (period - 1, period))


def cause(entry: dict) -> str:
    place, friend = entry.get('place') or {}, entry.get('with') or {}
    return CAUSES[entry['activity']].format(at=f" at {place['name']}" if place.get('name') else '',
                                            event=place.get('name') or (entry.get('trip') or {}).get('city')
                                            or 'the festival',
                                            friend=friend.get('name') or 'a friend')


def after(seed: str, day: date, yesterday: list[dict]) -> dict | None:
    """The strongest state the day before left, if any."""
    found = []
    for entry in yesterday:
        for state, chance in AFTER.get(entry['activity'], ()):
            if random.Random(f"after:{seed}:{day.isoformat()}:{entry['activity']}:{state}").random() < chance:
                found.append((ORDER.index(state), state, cause(entry)))
                break
    if not found:
        return None
    _rank, state, because = min(found)
    return {'state': state, 'because': because}


def state_on(seed: str, day: date, yesterday: list[dict], world, definition) -> dict | None:
    """The physical state for a local day. `seed` names the subject on its timeline; `yesterday`
    holds the previous day's composed entries in order."""
    if sick(seed, day, world, definition):
        first = not sick(seed, day - timedelta(days=1), world, definition)
        return {'state': 'sick', 'because': 'came down with a cold' if first else 'still getting over a cold'}
    return after(seed, day, yesterday)


def previous_entries(connection, timeline_id, subject, day: date) -> list[dict]:
    rows = many(connection, 'SELECT entry FROM life_agenda WHERE timeline_id=? AND subject=? AND local_date=? '
                'AND entry IS NOT NULL ORDER BY starts_at', (timeline_id, subject, (day - timedelta(days=1)).isoformat()))
    return [decode(row['entry']) for row in rows]


def sick_block(block: dict) -> dict:
    """A cold keeps the day at home: work or study becomes a sick day, and plans give way to rest."""
    if block['kind'] in {'work', 'study'}:
        return {**block, 'kind': 'rest', 'label': f"Sick day (no {block['label'].lower()})", 'sick_day': True}
    if block['kind'] in {'leisure', 'social', 'errand'}:
        return {**block, 'kind': 'rest', 'label': 'Home sick', 'sick_day': True}
    return block


def apply(block: dict, state: dict | None) -> dict:
    if not state:
        return block
    block = {**block, 'body': state}
    return sick_block(block) if state['state'] == 'sick' else block


def text(state: dict) -> str:
    return f"{state['state'].capitalize()}, {state['because']}."
