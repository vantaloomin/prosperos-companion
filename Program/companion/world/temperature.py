"""Celsius or Fahrenheit (tester, 1.4.1): how temperatures are said on Today, in the town paper and to the model.

The app picks by itself from where the companion lives: Fahrenheit in the United States and the few other places that
still use it, Celsius everywhere else, fantasy and future cities included. Settings > General > Temperature keeps one
for every world instead (workspace_settings.temperature_unit: 'auto', 'C' or 'F'). Weather is kept in °F throughout;
only the words change.
"""
from companion.database import settings

# Countries that say temperatures in Fahrenheit, as a city's `country` names them (lowercase).
FAHRENHEIT = {'us', 'usa', 'u.s.', 'u.s.a.', 'united states', 'united states of america', 'america', 'liberia',
              'belize', 'the bahamas', 'bahamas', 'cayman islands', 'palau', 'micronesia', 'marshall islands'}


def of_city(city: dict | None) -> str:
    """'F' for a city in a Fahrenheit country, else 'C'; no city at all keeps the first shipped city's (Baltimore)."""
    if not city:
        return 'F'
    return 'F' if (city.get('country') or '').strip().lower() in FAHRENHEIT else 'C'


def auto(connection) -> str:
    """The unit the app picks for this world: by the companion's city (or the user's, before there is a companion)."""
    from companion import story  # story reads agenda, which says the weather in this unit
    from companion.world import changes, custom
    return of_city(changes.resolve(story.default_city(connection), custom.all_cities(connection)))


def chosen(connection) -> str:
    """'C' or 'F': the one picked in Settings, else the app's own pick for this world."""
    picked = settings(connection).get('temperature_unit') or 'auto'
    return picked if picked in ('C', 'F') else auto(connection)


def degrees(fahrenheit: float, unit: str) -> int:
    return round(fahrenheit) if unit == 'F' else round((fahrenheit - 32) * 5 / 9)


def text(fahrenheit: float, unit: str) -> str:
    """'48°F' or '9°C'."""
    return f'{degrees(fahrenheit, unit)}°{unit}'
