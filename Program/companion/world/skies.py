"""Weather that settles in (Hit List #88): the day's sky and temperatures from the city's monthly climate.

Each day keeps yesterday's sky about 45% of the time (True to life); otherwise it draws from the month's mix of clear,
cloudy, overcast, fog, rain, storm and snow, built from the climate's rain days, temperatures and note. Because a kept
day and a fresh draw share the same mix, the month still has its real number of wet days; they just come in spells.
Temperatures wander around the month's typical high and low and lean with the sky. Everything is seeded by the city and
the date and stored nowhere, so the day is the same for everyone in the city, and each day is worked out from a week
before it.

The Weather step on Settings > Realism (world_life.weather, kept in each world's own database like its drama,
companion/life/world_drama.py) sets how the fronts behave: 0 Gentle
(short spells, rare storms), 1 True to life (the default), 2 Stormy (long spells, more storms, and more snow in season).
There is no Off: the climate was always there.
"""
import hashlib
import re
from datetime import date, timedelta

SKIES = ('clear', 'cloudy', 'overcast', 'fog', 'rain', 'storm', 'snow')
WET = frozenset({'rain', 'storm', 'snow'})
GENTLE, TRUE_TO_LIFE, STORMY = 0, 1, 2
LEVELS = (GENTLE, TRUE_TO_LIFE, STORMY)
# How often a day keeps yesterday's sky, how much more storm and snow the mix holds, how much wetter the month is and
# how far temperatures wander, by step.
KEEP = {GENTLE: 0.30, TRUE_TO_LIFE: 0.45, STORMY: 0.60}
STORMS = {GENTLE: 0.3, TRUE_TO_LIFE: 1.0, STORMY: 2.2}
SNOWS = {GENTLE: 0.6, TRUE_TO_LIFE: 1.0, STORMY: 1.6}
WETTER = {GENTLE: 1.0, TRUE_TO_LIFE: 1.0, STORMY: 1.2}
WANDER = {GENTLE: 0.6, TRUE_TO_LIFE: 1.0, STORMY: 1.3}
LOOKBACK = 7
# Degrees F the high and low lean on each sky: sun warms the afternoon and chills the night, cloud keeps nights mild.
LEAN = {'clear': (2, -2), 'cloudy': (0, 0), 'overcast': (-2, 2), 'fog': (-2, 1), 'rain': (-4, 1), 'storm': (-3, 2),
        'snow': (-5, -2)}
SNOW_CAP_F = 34  # A snowy day's high.
FOGGY = re.compile(r'\b(fogs?|foggy|mists?|misty|haar|smog|sea smoke|murk)\b', re.I)
STORMY_NOTE = re.compile(r'\b(thunder\w*|storms?|stormy|gales?|monsoon|typhoons?|hurricanes?|squalls?)\b', re.I)
SNOWY_NOTE = re.compile(r'\b(snow\w*|sleet|blizzards?)\b', re.I)
# How a sky reads in a sentence, and as the first words of one.
WORDS = {'clear': 'clear skies', 'cloudy': 'some cloud', 'overcast': 'overcast', 'fog': 'fog', 'rain': 'rain',
         'storm': 'storms', 'snow': 'snow'}
NTH = ('', 'first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth')


def level_of(connection) -> int:
    """This world's Weather step, True to life when unset."""
    row = connection.execute('SELECT weather FROM world_life WHERE id=1').fetchone()
    return row[0] if row and row[0] in LEVELS else TRUE_TO_LIFE


def set_level(connection, level: int, timestamp: str):
    connection.execute('INSERT INTO world_life (id, weather, updated_at) VALUES (1, ?, ?) ON CONFLICT(id) '
                       'DO UPDATE SET weather=excluded.weather, updated_at=excluded.updated_at', (level, timestamp))


def mix(month: dict, level: int = TRUE_TO_LIFE) -> dict[str, float]:
    """The month's chance of each sky (summing to 1), from its rain days, temperatures and note."""
    note = month.get('note') or ''
    wet = min(0.9, month['rain_days'] / 30 * WETTER[level])
    snowy = 0.0 if month['low_f'] > 34 else min(0.85, (34 - month['low_f']) / 24 + (0.1 if SNOWY_NOTE.search(note)
                                                                                        else 0))
    stormy = (0.3 if month['high_f'] >= 80 else 0.18 if month['high_f'] >= 70 else 0.06)
    stormy = min(0.6, (stormy + (0.1 if STORMY_NOTE.search(note) else 0)) * (1 - snowy))
    weights = {'snow': wet * snowy * SNOWS[level], 'storm': wet * stormy * STORMS[level]}
    weights['rain'] = max(0.0, wet - wet * snowy - wet * stormy)
    dry = 1 - wet
    fog = min(dry * 0.4, 0.12 if FOGGY.search(note) else 0.03)
    clear = max(0.2, 0.55 - wet)
    overcast = min(0.4, 0.1 + wet * 0.6)
    weights |= {'fog': fog, 'clear': (dry - fog) * clear, 'overcast': (dry - fog) * overcast,
                'cloudy': (dry - fog) * (1 - clear - overcast)}
    total = sum(weights.values())
    return {sky: weights[sky] / total for sky in SKIES}


def draw(data: dict, when: date, level: int) -> str:
    """A fresh sky for the day from its month's mix."""
    weights = mix(data['climate']['months'][when.month - 1], level)
    target, running = unit(data['id'], when.isoformat(), 'sky'), 0.0
    for sky in SKIES:
        running += weights[sky]
        if target < running:
            return sky
    return 'cloudy'


def spell(data: dict, day: date, level: int = TRUE_TO_LIFE) -> tuple[str, int]:
    """The day's sky and how many days running it has held (1 on a change), from a week of fronts before it."""
    start = day - timedelta(days=LOOKBACK)
    sky, days = draw(data, start, level), 1
    for offset in range(1, LOOKBACK + 1):
        when = start + timedelta(days=offset)
        possible = mix(data['climate']['months'][when.month - 1], level)[sky] > 0
        if possible and unit(data['id'], when.isoformat(), 'keep') < KEEP[level]:
            days += 1
            continue
        fresh = draw(data, when, level)
        days = days + 1 if fresh == sky else 1
        sky = fresh
    return sky, days


def drift(data: dict, day: date, level: int) -> float:
    """How far (°F) the day runs above or below the month's typical temperatures: a slow walk, within about 7°F."""
    walk = 0.0
    for offset in range(LOOKBACK, -1, -1):
        walk = walk * 0.6 + (unit(data['id'], (day - timedelta(days=offset)).isoformat(), 'warmth') - 0.5) * 8
    return max(-7.0, min(7.0, walk * WANDER[level]))


def day_weather(data: dict, day: date, level: int = TRUE_TO_LIFE) -> dict:
    """The day's sky, how long it has held, and its high and low (°F)."""
    month = data['climate']['months'][day.month - 1]
    sky, days = spell(data, day, level)
    shift = drift(data, day, level)
    lean_high, lean_low = LEAN[sky]
    high = round(month['high_f'] + shift + lean_high)
    low = round(month['low_f'] + shift * 0.7 + lean_low)
    if sky == 'snow':
        high = min(high, SNOW_CAP_F)
    low = min(low, high - 4)
    return {'sky': sky, 'days': days, 'high_f': high, 'low_f': low, 'rain': sky in WET}


def sky_words(conditions: dict) -> str:
    """'rain, the third day of it', 'clear skies', or '' for a day with no sky named (older or looked-up weather)."""
    sky = conditions.get('sky')
    if sky not in WORDS:
        return ''
    days = conditions.get('days') or 1
    if sky in WET | {'fog', 'overcast'} and 2 <= days < len(NTH):
        return f"{WORDS[sky]}, the {NTH[days]} day of it"
    return WORDS[sky]


def from_text(text: str) -> str | None:
    """The sky a weather service's words describe, such as 'light rain' or 'thunderstorms with hail'."""
    text = text.lower()
    for sky, words in (('storm', ('thunder', 'storm')), ('snow', ('snow', 'sleet', 'blizzard', 'flurr')),
                       ('rain', ('rain', 'drizzle', 'shower')), ('fog', ('fog', 'mist', 'haze')),
                       ('overcast', ('overcast', 'cloudy skies', 'grey', 'gray')),
                       ('cloudy', ('cloud',)), ('clear', ('clear', 'sun', 'fair'))):
        if any(word in text for word in words):
            return sky
    return None


def unit(seed: str, *parts) -> float:
    """A stable number in [0, 1), the same as companion/world/generators.py unit (which imports this module)."""
    digest = hashlib.sha256('\x1f'.join(map(str, (seed, *parts))).encode()).digest()
    return int.from_bytes(digest[:8], 'big') / 2 ** 64
