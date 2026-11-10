"""Real weather for the companion's simulated day, when the user allows it (PRD X1, X3, W2).

A weather lookup for the companion's city (a real, modern place) can stand in for the city's
typical weather on that local date. Only a lookup made on that date counts, and only when a
temperature can be read from it; otherwise the day keeps its typical weather. The result is
marked `observed` with its source and time, so the context and the Today view never present
climate averages as a forecast or a lookup as anything other than what it is.
"""
import math
import re
from datetime import date, timedelta

from companion.characters import current
from companion.clock import parse, stamp
from companion.database import decode
from companion.world import skies

RAIN = re.compile(r'\b(rain|rainy|showers?|drizzle|thunder\w*|storms?|stormy|snow\w*|sleet|hail)\b', re.I)
NO_RAIN = re.compile(r'\b(no|without)\s+(rain|showers?|snow)\b', re.I)
TEMPERATURE = re.compile(r'(-?\d{1,3}(?:\.\d+)?)\s*°\s*([FC])\b|(-?\d{1,3}(?:\.\d+)?)\s*(?:degrees\s+)?(F|C)\b')
STRUCTURED_F = ('high_f', 'low_f', 'temperature_f', 'temp_f', 'max_temp_f', 'min_temp_f')
STRUCTURED_C = ('high_c', 'low_c', 'temperature_c', 'temp_c', 'max_temp_c', 'min_temp_c')
# The coldest and hottest air temperatures a weather lookup can report (°F).
LOWEST_F, HIGHEST_F = -60, 135
SUMMARY_KEYS = ('condition', 'conditions', 'summary', 'description', 'weather')


def fahrenheit(value: float, unit: str) -> int:
    return round(value * 9 / 5 + 32) if unit.upper() == 'C' else round(value)


def plausible(values: list[float]) -> list[int]:
    """Readings a place on Earth could have, in °F; a service's 9999, NaN or Infinity is left out."""
    return [round(value) for value in values if math.isfinite(value) and LOWEST_F <= value <= HIGHEST_F]


def readings(content: str, structured: dict | None) -> list[int]:
    """Temperatures in °F from structured fields named for their unit, else from the text."""
    found = []
    for key, value in (structured or {}).items():
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
            if key.lower() in STRUCTURED_F:
                found.append(value)
            elif key.lower() in STRUCTURED_C:
                found.append(value * 9 / 5 + 32)
    if found := plausible(found):
        return found
    for match in TEMPERATURE.finditer(content):
        number, unit = (match.group(1), match.group(2)) if match.group(1) else (match.group(3), match.group(4))
        found.append(fahrenheit(float(number), unit))
    return plausible(found)


def conditions_from(content: str, structured: dict | None) -> dict | None:
    """High, low, rain and a short summary, or None when no temperature can be read."""
    temperatures = readings(content, structured)
    if not temperatures:
        return None
    summary = next((str(structured[key]) for key in SUMMARY_KEYS if structured and isinstance(structured.get(key), str)),
                   '')
    # A named condition is today's own; the text can go on to tomorrow ("tomorrow light rain").
    text = summary or content.split('tomorrow')[0]
    rain = bool(RAIN.search(text)) and not NO_RAIN.search(text)
    first_line = content.strip().splitlines()[0] if content.strip() else ''
    found = {'high_f': max(temperatures), 'low_f': min(temperatures), 'rain': rain, 'note': (summary or first_line)[:160]}
    sky = skies.from_text(NO_RAIN.sub('', text))
    return {**found, 'sky': sky} if sky else found


def tomorrow_from(structured: dict | None) -> dict | None:
    """Tomorrow's forecast the built-in server gives beside today's (companion/mcp/servers/weather.py), if any."""
    ahead = (structured or {}).get('tomorrow')
    return conditions_from('', ahead) if isinstance(ahead, dict) else None


LOOKED_UP = ("SELECT * FROM context_observations WHERE category='weather' AND purpose='companion_city' AND "
             "status='ok' AND json_extract(location, '$.city')=? AND json_extract(location, '$.date')=? "
             'ORDER BY retrieved_at DESC, rowid DESC LIMIT 5')


def observed_for(connection, city_id: str, local_date: str) -> dict | None:
    """The latest readable weather lookup for the companion's city made on that local date, else the forecast for it
    that a lookup the day before gave (marked `forecast`)."""
    for row in connection.execute(LOOKED_UP, (city_id, local_date)).fetchall():
        found = conditions_from(row['content'], decode(row['structured']))
        if found:
            return {**found, 'observed': seen(row)}
    before = (date.fromisoformat(local_date) - timedelta(days=1)).isoformat()
    for row in connection.execute(LOOKED_UP, (city_id, before)).fetchall():
        found = tomorrow_from(decode(row['structured']))
        if found:
            return {**found, 'observed': {**seen(row), 'forecast': True}}
    return None


def seen(row) -> dict:
    return {'observation_id': row['id'], 'source': row['service_name'], 'tool': row['tool'],
            'retrieved_at': row['retrieved_at']}


class ObservedWorld:
    """A world source whose weather prefers a same-day lookup for real cities; all else is delegated."""

    def __init__(self, world, database):
        self.world = world
        self.database = database

    def __getattr__(self, name):
        return getattr(self.world, name)

    def weather(self, city: str, day) -> dict | None:
        typical = self.world.weather(city, day) if hasattr(self.world, 'weather') else None
        finder = getattr(self.world, 'find', None)
        data = finder(city) if finder else None
        if not data or data.get('setting') != 'real':
            return typical
        with self.database.connect() as connection:
            found = observed_for(connection, data['id'], day.isoformat())
        if not found:
            return typical
        season = typical['season'] if typical else None
        return {'season': season, **found}


def apply(database, observation: dict):
    """After a readable lookup for the companion's city, rebuild the rest of that day's schedule.

    Entries that already started keep the weather they were composed with; the agenda refills the
    removed ones on its next extension, composing them the same way except for the weather.
    """
    location = observation.get('location') or {}
    if (observation['category'] != 'weather' or observation['purpose'] != 'companion_city'
            or observation['status'] != 'ok' or not location.get('date')
            or not conditions_from(observation['content'], observation.get('structured'))):
        return
    days = [location['date']]
    if tomorrow_from(observation.get('structured')):
        days.append((date.fromisoformat(location['date']) + timedelta(days=1)).isoformat())
    now = stamp(database.clock.now())
    with database.connect(write=True) as connection:
        companion = current(connection)
        if companion is None:
            return
        timeline_id = companion['active_timeline_id']
        marks = ','.join('?' * len(days))
        removed = connection.execute(f"DELETE FROM life_agenda WHERE timeline_id=? AND local_date IN ({marks}) AND "
                                     "status='upcoming' AND starts_at>?", (timeline_id, *days, now)).rowcount
        if removed:
            connection.execute('UPDATE agenda_cursors SET through=MIN(through, ?) WHERE timeline_id=?',
                               (now, timeline_id))


def label(conditions: dict) -> str:
    """How the context names observed weather: its source and when it was looked up."""
    found = conditions['observed']
    when = parse(found['retrieved_at']).strftime('%H:%M UTC')
    return f"{'forecast' if found.get('forecast') else 'looked up'} from {found['source']} at {when}"

