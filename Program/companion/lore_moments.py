"""Lore that fits the moment: a lore entry can say when it applies (companion/lore.py), not only which words bring it.

A "when" is a list of conditions, each `kind:value`: the weather (rain, snow, heat, fog), the season, the time of day,
a weekday or the weekend, one of the city's holidays, a place or neighbourhood, and "at work". Conditions of one kind
are alternatives and different kinds all have to hold, so ["weather:rain", "time:night"] is a rainy night and
["season:winter", "season:fall"] is either. The app reads the moment the way Today does (the day's weather, the
city's calendar, where the companion is in their day); aboard a ship or station there is no weather or Earth season,
so those never hold there, and night is ship's night. Rules only: no model picks anything.

City files can carry a `lore` block (`clean` checks it when the city loads), which joins the world's lore while the
companion lives there. Imported lorebooks get a "when" by rule only from a keyword that is itself a season, weather,
time of day or one of the city's holidays (`guessed`), and the user can take it off.
"""
import re
from datetime import datetime

from companion.clock import stamp, zone
from companion.database import decode, optional

WEATHER = {'rain': 'Rain', 'snow': 'Snow', 'heat': 'Heat', 'fog': 'Fog'}
SEASONS = {'spring': 'Spring', 'summer': 'Summer', 'fall': 'Fall', 'winter': 'Winter'}
TIMES = {'morning': 'Morning', 'afternoon': 'Afternoon', 'evening': 'Evening', 'night': 'Night'}
DAYS = {'weekday': 'Weekdays', 'weekend': 'Weekends'}
# The hour each part of the day starts, local time; night runs on to morning.
TIME_STARTS = ((5, 'morning'), (12, 'afternoon'), (17, 'evening'), (21, 'night'))
KINDS = ('weather', 'season', 'time', 'day', 'holiday', 'place', 'work')
WORK = 'work:yes'
# Heat from this high (°F) up, snow on a wet day this cold or colder at night.
HOT_F, SNOW_F = 88, 30
FOGGY = re.compile(r'\b(fog|fogs|foggy|mist|misty|haar|smog)\b', re.I)
SNOWY = re.compile(r'\b(snow\w*|sleet|blizzard)\b', re.I)
# Keywords of an imported entry that are themselves a moment (`guessed`). "Fall" is left out: it is a verb too.
WORDS = {'rain': 'weather:rain', 'rainy': 'weather:rain', 'snow': 'weather:snow', 'snowy': 'weather:snow',
         'heatwave': 'weather:heat', 'heat wave': 'weather:heat', 'fog': 'weather:fog', 'foggy': 'weather:fog',
         'spring': 'season:spring', 'summer': 'season:summer', 'autumn': 'season:fall', 'winter': 'season:winter',
         'morning': 'time:morning', 'afternoon': 'time:afternoon', 'evening': 'time:evening', 'night': 'time:night',
         'nighttime': 'time:night', 'weekend': 'day:weekend', 'weekday': 'day:weekday'}
MAX_ENTRIES, MAX_TEXT, MAX_TITLE, MAX_KEYWORDS = 300, 2000, 160, 32
ID = re.compile(r'[a-z0-9][a-z0-9-]{0,79}')


# Reading the moment ----------------------------------------------------------------------------------------

def part_of_day(hour: int) -> str:
    found = 'night'
    for start, name in TIME_STARTS:
        if hour >= start:
            found = name
    return found


def weather_keys(conditions: dict | None) -> set[str]:
    """What the day's weather (generated or observed, companion/life/agenda.py) counts as."""
    if not conditions:
        return set()
    note = conditions.get('note') or ''
    found = set()
    if conditions.get('rain'):
        snowing = conditions.get('low_f', 99) <= SNOW_F or bool(SNOWY.search(note))
        found.add('weather:snow' if snowing else 'weather:rain')
    elif FOGGY.search(note):
        found.add('weather:fog')
    if conditions.get('high_f', 0) >= HOT_F:
        found.add('weather:heat')
    return found


def place_keys(city: dict | None, entry: dict | None, home_hood: str) -> set[str]:
    """The place the companion is at and its neighbourhood, by the city's ids; at home, their own neighbourhood."""
    if not city:
        return set()
    hoods = {hood['name'].casefold(): hood['id'] for hood in city['neighborhoods']}
    place = (entry or {}).get('place')
    found = set()
    if isinstance(place, dict):
        found |= {f"place:{place['id']}"} if place.get('id') else set()
        hood = hoods.get((place.get('neighborhood') or '').casefold())
    else:
        hood = hoods.get(home_hood.casefold())
    return found | ({f'place:{hood}'} if hood else set())


def home_neighbourhood(connection, timeline_id: str, day) -> str:
    from companion.life import home
    found = next((item for item in home.items_on(connection, timeline_id, day) if item['kind'] == 'home'), None)
    return (found or {}).get('neighborhood') or ''


def where_keys(connection, companion: dict, city: dict | None, now: datetime) -> set[str]:
    """Where the companion is in their day right now, and whether they are at work."""
    from companion.life import agenda
    row = optional(connection, 'SELECT block, entry FROM life_agenda WHERE timeline_id=? AND subject=? AND starts_at<=? '
                   'AND ends_at>? LIMIT 1', (companion['active_timeline_id'], agenda.COMPANION, stamp(now), stamp(now)))
    block = decode(row['block']) if row else {}
    entry = decode(row['entry']) if row and row['entry'] else None
    working = block.get('kind') == 'work' and not block.get('sick_day')
    local = now.astimezone(zone(companion['version']['timezone'])).date()
    home_hood = '' if entry else home_neighbourhood(connection, companion['active_timeline_id'], local)
    return place_keys(city, entry, home_hood) | ({WORK} if working else set())


def holiday_keys(city: dict | None, day) -> set[str]:
    from companion.almanac.context import dated
    return {f"holiday:{item['name'].casefold()}" for item in dated(city, day, day)} if city else set()


def now_keys(connection, companion: dict, now: datetime) -> set[str]:
    """Every condition that holds for the companion right now."""
    from companion.almanac.context import city_for
    from companion.life import agenda
    from companion.world import generators, ships
    city = city_for(connection, companion['version']['definition'])
    local = now.astimezone(zone(companion['version']['timezone']))
    found = {f'time:{part_of_day(local.hour)}', 'day:weekend' if local.weekday() >= 5 else 'day:weekday'}
    if not ships.enclosed(city):
        found.add(f'season:{generators.SEASONS[local.month]}')
        found |= weather_keys(agenda.day_on(connection, companion['active_timeline_id'],
                                            local.date().isoformat())['weather'])
    return found | holiday_keys(city, local.date()) | where_keys(connection, companion, city, now)


def matches(when: list[str], keys: set[str]) -> bool:
    """Whether a "when" holds: one condition of each kind it names. An empty "when" never does."""
    wanted: dict[str, set[str]] = {}
    for condition in when:
        kind, _, value = condition.partition(':')
        wanted.setdefault(kind, set()).add(f'{kind}:{value.casefold()}')
    return bool(wanted) and all(options & keys for options in wanted.values())


# What an entry's "when" says ----------------------------------------------------------------------------------

def holiday_names(city: dict | None) -> list[str]:
    """The city's holidays and observances by name, for the picker and for guessing."""
    if not city:
        return []
    from companion.almanac import days
    from companion.world import generators
    names = [item['name'] for item in generators.city_holidays(city)]
    names += [item['name'] for item in days.data()['days']] if days.applies(city) else []
    return sorted(dict.fromkeys(names), key=str.casefold)


def guessed(keywords: list[str], holidays: list[str]) -> list[str]:
    """A "when" for an imported entry from keywords that are themselves a moment, of one kind only (the first found),
    so an entry keyed "winter" and "rain" switches on in winter, not only on wet winter days."""
    named = {name.casefold(): name for name in holidays}
    found = []
    for word in keywords:
        key = word.strip().casefold()
        condition = WORDS.get(key) or (f'holiday:{named[key]}' if key in named else None)
        if condition and (not found or condition.partition(':')[0] == found[0].partition(':')[0]):
            found.append(condition)
    return list(dict.fromkeys(found))


def choices(city: dict | None) -> dict:
    """What the pickers on the Lore screen offer, as [{key, label}] by kind."""
    def listed(kind, labels):
        return [{'key': f'{kind}:{key}', 'label': label} for key, label in labels.items()]
    from companion.world import ships
    hoods = {hood['id']: hood['name'] for hood in (city or {}).get('neighborhoods', [])}
    aboard = ships.enclosed(city)  # No weather or Earth seasons aboard, so nothing to pick.
    return {'weather': [] if aboard else listed('weather', WEATHER), 'season': [] if aboard else listed('season', SEASONS),
            'time': listed('time', TIMES),
            'day': listed('day', DAYS), 'holiday': [{'key': f'holiday:{name}', 'label': name}
                                                    for name in holiday_names(city)],
            'place': listed('place', dict(sorted(hoods.items(), key=lambda item: item[1].casefold()))),
            'work': [{'key': WORK, 'label': 'At work'}]}


def label(condition: str, city: dict | None) -> str:
    kind, _, value = condition.partition(':')
    if kind == 'place':
        known = {item['id']: item['name'] for item in [*(city or {}).get('neighborhoods', []),
                                                         *(city or {}).get('places', [])]}
        return known.get(value, value.replace('-', ' ').capitalize())
    if kind == 'holiday':
        return value
    if kind == 'work':
        return 'At work'
    return {**WEATHER, **SEASONS, **TIMES, **DAYS}.get(value, value)


def tidy(when: list[str]) -> list[str]:
    """A "when" from the user, kept to known kinds and in a steady order."""
    kept = []
    for condition in when:
        kind, _, value = condition.partition(':')
        if kind in KINDS and value.strip() and condition not in kept:
            kept.append(f'{kind}:{value.strip()[:120]}')
    return sorted(kept, key=lambda item: KINDS.index(item.partition(':')[0]))[:40]


# A city file's lore block ---------------------------------------------------------------------------------------

def city_when(raw: dict, city: dict) -> tuple[list[str], list[str]]:
    """(conditions, notes) for one entry's `when` in a city file: holidays by id or name, places by id."""
    holidays = {}
    from companion.world import generators
    for item in generators.city_holidays(city):
        holidays[item['id']] = holidays[item['name'].casefold()] = item['name']
    known = {item['id'] for item in [*city['neighborhoods'], *city['places']]}
    allowed = {'weather': WEATHER, 'season': SEASONS, 'time': TIMES, 'day': DAYS}
    found, notes = [], []
    for kind, values in raw.items():
        values = values if isinstance(values, list) else [values]
        for value in values:
            text = str(value)
            if kind in allowed and text in allowed[kind]:
                found.append(f'{kind}:{text}')
            elif kind == 'holiday' and text.casefold() in holidays:
                found.append(f'holiday:{holidays[text.casefold()]}')
            elif kind == 'place' and text in known:
                found.append(f'place:{text}')
            elif kind == 'work' and value is True:
                found.append(WORK)
            else:
                notes.append(f'"{kind}: {text}"')
    return tidy(found), notes


def clean_entry(item, city: dict) -> tuple[dict | None, list[str]]:
    if not isinstance(item, dict) or not ID.fullmatch(str(item.get('id', ''))) or not str(item.get('text', '')).strip():
        return None, ['Dropped a lore entry: it needs a lowercase id and some text.']
    keywords = [str(word).strip()[:200] for word in item.get('keywords') or [] if str(word).strip()][:MAX_KEYWORDS]
    when, unknown = city_when(item.get('when') or {}, city) if isinstance(item.get('when') or {}, dict) else ([], [])
    notes = [f"The lore entry \"{item['id']}\" left out {', '.join(unknown)}, which the city doesn't have."] \
        if unknown else []
    if not keywords and not when:
        return None, notes + [f"Dropped the lore entry \"{item['id']}\": it needs keywords or a when."]
    return {'id': item['id'], 'title': str(item.get('title') or item['id'])[:MAX_TITLE],
            'text': str(item['text']).strip()[:MAX_TEXT], 'keywords': keywords, 'when': when}, notes


def clean(data: dict) -> list[str]:
    """Check a city's `lore` block in place ({credit, entries}): a bad entry is dropped with a note and the city
    still loads."""
    block = data.pop('lore', None)
    if block is None:
        return []
    if not isinstance(block, dict) or not isinstance(block.get('entries'), list):
        return ['Dropped the lore block: it needs a list of entries.']
    entries, notes, seen = [], [], set()
    for item in block['entries'][:MAX_ENTRIES]:
        entry, said = clean_entry(item, data)
        notes += said
        if entry and entry['id'] not in seen:
            seen.add(entry['id'])
            entries.append(entry)
    if entries:
        data['lore'] = {'credit': str(block.get('credit') or '')[:400], 'entries': entries}
    return notes
