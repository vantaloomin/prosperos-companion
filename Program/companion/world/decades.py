"""Decade rules for Back when (1.2 "The Dark Backward"): a modern city takes on the decade of its world's year.

A world can run in a past year (companion/world_year.py). There, a modern city reads the 1990s, 2000s, 2010s or 2020s
from that year, and the decade shows by rule, with no model call:

- careers and hobbies with `years` (`[from, until]`, either may be null) are only offered in those years: nobody
  drives for a ride-hailing app before there was one (catalog.careers_for, life/hobbies.choose_new);
- media is drawn from titles out by that year (life/media.place_of);
- rents and prices are scaled to that year by a per-currency price index (`dated`, through catalog.city);
- era words get the decade's own (era_words.json `decades`), under the same "Period words in period cities" switch;
- politics argues the questions of that year (politics.json `years`, through politics.present_year);
- pictures are told the year, and a camera of the decade (`picture`, images/prompts.py).

Era stays 'modern': about fifty places check for it, so a decade is never an era of its own. Period cities (1895,
1925, Camelot) keep their own eras and are left alone, and so is everything in a world in the present: there,
`world_year` is None and nothing here changes what the app did before. The year is read from the clock of the world
being served (companion/clock.CURRENT, which follows the open or pinned world).

Item 3 (decade banks) fills the data these rules read: `years` on more careers, hobbies and media, and each decade's
words. The rules read any of it without code changes.
"""
import json
from functools import cache
from pathlib import Path

from companion.clock import CURRENT, PRESENT

# Read beside the city data without importing catalog, which reads these rules (catalog.city, careers_for).
DATA = Path(__file__).parent / 'data' / 'decades.json'

MODERN_ERAS = ('modern',)
PARTS = ((3, 'early'), (6, 'mid'), (9, 'late'))


@cache
def table() -> dict:
    return json.loads(DATA.read_text(encoding='utf-8'))


# --- The year and its decade ---

def world_year() -> int | None:
    """The year in the world being served when it runs in a past year; None in the present."""
    clock = CURRENT[0]
    behind = getattr(clock, 'behind', None)
    if behind is None or behind() == PRESENT:
        return None
    return clock.now().year


def years_back() -> int:
    """How many years behind the real year the world being served runs: 0 in the present (world_year.years_back,
    read from the clock)."""
    behind = getattr(CURRENT[0], 'behind', None)
    return round(behind().days / 365.2425) if behind else 0


def modern(city: dict | None) -> bool:
    return ((city or {}).get('era') or 'modern') in MODERN_ERAS


def year_of(city: dict | None) -> int | None:
    """The past year a modern city is in, or None (the present, or a city of another era)."""
    return world_year() if modern(city) else None


def decade(year: int) -> str:
    """'1990s' for 1994."""
    return f'{year // 10 * 10}s'


def decade_of(city: dict | None) -> str | None:
    year = year_of(city)
    return decade(year) if year else None


def part(year: int) -> str:
    """Early, mid or late in its decade."""
    return next(word for last, word in PARTS if year % 10 <= last)


def rules(name: str) -> dict:
    """A decade's own rules; {} for a decade the table has none for."""
    return table()['decades'].get(name) or {}


# --- Years on careers, hobbies and questions ---

def in_years(item: dict, year: int) -> bool:
    """Whether something with optional `years` ([from, until], either null) exists in `year`."""
    years = item.get('years')
    if not years:
        return True
    start, until = years
    return (start is None or start <= year) and (until is None or year <= until)


def offered_year(city: dict | None) -> int | None:
    """The year a modern city's careers and hobbies are offered for: its world's past year, else this year (so one
    that ended, a video store clerk, is not offered today either). None for a city of another era."""
    return (world_year() or CURRENT[0].now().year) if modern(city) else None


def current(items, city: dict | None) -> list:
    """The items that exist in the city's year; all of them in a city of another era."""
    year = offered_year(city)
    return [item for item in items if year is None or in_years(item, year)]


# --- Prices ---

def level(code: str, year: int) -> float:
    """The currency's price level in `year`: the listed year's, or a steady rate between the two nearest."""
    prices = table()['prices']
    levels = {int(key): value for key, value in (prices['levels'].get(code) or
                                                 prices['levels'][prices['fallback']]).items()}
    first, last = min(levels), max(levels)
    year = min(max(year, first), last)
    if year in levels:
        return levels[year]
    before = max(key for key in levels if key < year)
    after = min(key for key in levels if key > year)
    return levels[before] * (levels[after] / levels[before]) ** ((year - before) / (after - before))


def factor(code: str, year: int) -> float:
    """What today's amount was in `year`, as a share: 0.53 for US dollars in 2000."""
    return level(code, year) / level(code, table()['prices']['base'])


def scaled_rent(rent: dict | None, share: float) -> dict | None:
    if not rent:
        return rent
    return {unit: [round(value * share) for value in values] for unit, values in rent.items()}


def dated(city: dict) -> dict:
    """The city as it was in its world's past year: rents and prices in that year's money, and `price_year` saying
    so (money.take_home reads it). The city itself when nothing changes."""
    year = year_of(city)
    code = (city.get('currency') or {}).get('code') or 'USD'
    if not year or code == 'none':
        return city
    share = factor(code, year)
    hoods = [hood | {'rent': scaled_rent(hood['rent'], share)} if hood.get('rent') else hood
             for hood in city.get('neighborhoods') or ()]
    prices = [item | {'low': round(item['low'] * share, 2), 'high': round(item['high'] * share, 2)}
              for item in city.get('prices') or ()]
    return city | {'neighborhoods': hoods, 'prices': prices, 'price_year': year}


def price_share(city: dict) -> float:
    """How a dated city's amounts compare with today's (1.0 for one in today's money)."""
    year = city.get('price_year')
    return factor((city.get('currency') or {}).get('code') or 'USD', year) if year else 1.0


# --- Words and pictures ---

def words(table_decades: dict, city: dict | None) -> dict[str, str]:
    """A modern city's decade words from the era words table's `decades`; {} in the present."""
    name = decade_of(city)
    return dict(table_decades.get(name) or {}) if name else {}


def picture(city: dict | None) -> dict | None:
    """How a picture shows the year: {'decade', 'scene', 'cameras', 'framings'}, or None in the present and in a
    city of another era."""
    year = year_of(city)
    if not year:
        return None
    found = rules(decade(year)).get('picture') or {}
    scene = (found.get('scene') or '').replace('{year}', str(year)).replace('{part}', part(year))
    return {'decade': decade(year), 'scene': scene, 'cameras': found.get('cameras') or {},
            'framings': found.get('framings') or {}}
