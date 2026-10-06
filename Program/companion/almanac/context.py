"""The calendar section of the chat context: what a person living in the companion's city knows about
the date without reading any news.

Holidays come from the world data; observances and seasons from companion/almanac/days.py; the
city's own seasons (a team's season) from its annual events; daylight and the moon from
companion/almanac/sky.py. All of it is computed, so it costs no model work and no network.
"""
from datetime import date, datetime, timedelta

from companion.almanac import days, sky
from companion.clock import zone
from companion.world import changes, custom, generators
from companion.world.source import seasonal

AHEAD = 21
COMING_LIMIT = 4
NO_NEWS = ('This is a calendar, not news: you do not know recent real-world events (scores, headlines, '
           'releases, prices) unless another section lists them, so never make them up.')


def city_for(connection, definition: dict) -> dict | None:
    place = definition.get('home_city') or definition.get('location') or ''
    return changes.resolve(place, custom.all_cities(connection)) if place else None


def when(day: date, today: date) -> str:
    gap = (day - today).days
    return f"{day:%A}, {day:%B} {day.day}" + (' (tomorrow)' if gap == 1 else f' (in {gap} days)')


def dated(city: dict, start: date, end: date) -> list[dict]:
    """Holidays from the world data, then observances; a world holiday wins on a shared name."""
    found = [{'name': item['name'], 'date': date.fromisoformat(item['date']), 'public': item['kind'] == 'public'}
             for item in generators.holidays(city, start, end)]
    if days.applies(city):
        names = {item['name'] for item in found}
        found += [{**item, 'public': False} for item in days.days_between(city, start, end) if item['name'] not in names]
    return sorted(found, key=lambda item: item['date'])


def daylight(city: dict, today: date, now: datetime, timezone: str) -> str | None:
    if 'lat' not in city or 'lon' not in city:
        return None
    rise, set_ = sky.sun(today, city['lat'], city['lon'])
    phase = sky.moon(now)
    if not rise:
        return f'- Daylight: no sunrise or sunset today this far north or south; moon phase: {phase}.'
    local = zone(timezone)
    length = round((set_ - rise).total_seconds() / 60)
    return (f"- Daylight: sunrise {clock(rise.astimezone(local))}, sunset {clock(set_.astimezone(local))} "
            f"({length // 60} h {length % 60} min of daylight); moon phase: {phase}.")


def clock(moment: datetime) -> str:
    return f"{moment.hour % 12 or 12}:{moment:%M} {'AM' if moment.hour < 12 else 'PM'}"


def going_on(city: dict, today: date) -> list[str]:
    seasons = [item['name'] + (f" (until {item['until']:%B} {item['until'].day})"
                               if (item['until'] - today).days <= 14 else '')
               for item in (days.spans_on(city, today) if days.applies(city) else [])]
    seasons += [f"{item['name']} ({item['summary'].rstrip('.')})" for item in city.get('annual_events', [])
                if seasonal(item) and today.month in item['months']]
    return seasons


def context_lines(connection, definition: dict, timezone: str, now: datetime) -> list[tuple[str, str]]:
    """(identity, text) lines for the calendar section; [] when the companion has no known city."""
    city = city_for(connection, definition)
    if not city:
        return []
    today = now.astimezone(zone(timezone)).date()
    lines = []
    upcoming = dated(city, today, today + timedelta(days=AHEAD))
    if today_items := [item['name'] + (' (a public holiday)' if item['public'] else '') for item in upcoming
                       if item['date'] == today]:
        lines.append(('today', f"- Today: {'; '.join(today_items)}."))
    if coming := [f"{item['name']}, {when(item['date'], today)}" for item in upcoming
                  if item['date'] > today][:COMING_LIMIT]:
        lines.append(('coming', f"- Coming up: {'; '.join(coming)}."))
    if seasons := going_on(city, today):
        lines.append(('seasons', f"- Going on now: {'; '.join(seasons)}."))
    if light := daylight(city, today, now, timezone):
        lines.append(('daylight', light))
    if lines and days.applies(city):
        lines.append(('no_news', f'- {NO_NEWS}'))
    return [(f'{today.isoformat()}:{key}', text) for key, text in lines]
