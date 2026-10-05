"""Deterministic generators that assemble everyday life from the shipped city data.

The same city data, seed and arguments always give the same result, on any machine and Python
version: choices come from SHA-256 of the seed, never from `random`. Callers pass a seed that is
stable for the moment being simulated (a slot key, for example), so a resumed or repeated batch
picks the same outing. Results are plain dictionaries with `refs`, the ids of every record used,
and `sources`, so an event can record exactly which facts it was built from. The model only
phrases these facts; it never has to invent a place, employer, rent or commute.
"""
import hashlib
from datetime import date

from companion.errors import DomainError
from companion.world import catalog

COSTS = ['free', '$', '$$', '$$$', '$$$$']
SEASONS = {12: 'winter', 1: 'winter', 2: 'winter', 3: 'spring', 4: 'spring', 5: 'spring', 6: 'summer',
           7: 'summer', 8: 'summer', 9: 'fall', 10: 'fall', 11: 'fall'}
MEALS = {'breakfast': 'morning', 'brunch': 'morning', 'lunch': 'afternoon', 'dinner': 'evening', 'late': 'late'}
FOOD = ('restaurant', 'cafe', 'market', 'tavern', 'inn')
BEDROOMS = ('studio', 'one_bedroom', 'two_bedroom')
# Where a career with no named employer in the data can plausibly work.
WORKPLACE_KINDS = {
    'barista': ('cafe',), 'baker': ('cafe', 'market'), 'line-cook': ('restaurant',), 'server': ('restaurant',),
    'bartender': ('bar', 'nightlife', 'tavern', 'inn'), 'retail-associate': ('shopping',), 'tour-guide': ('attraction', 'landmark'),
    'performer': ('venue',), 'musician': ('venue', 'bar'), 'fitness-trainer': ('fitness',),
    'lifeguard': ('beach',), 'surf-instructor': ('beach',),
}
# Where any career in a sector can plausibly work, for cities that name no employer for it.
SECTOR_KINDS = {
    'food': ('cafe', 'market', 'restaurant'), 'hospitality': ('restaurant', 'bar', 'tavern', 'inn', 'cafe'),
    'entertainment': ('venue',), 'tourism': ('attraction', 'landmark'), 'retail': ('shopping', 'market'),
    'religion': ('temple',), 'trade': ('market', 'guildhall', 'workshop'), 'crafts': ('workshop',),
    'fitness': ('fitness',), 'recreation': ('beach', 'park'), 'logistics': ('docks',),
}
RAIL = {'subway', 'light-rail', 'commuter-rail', 'streetcar', 'monorail', 'tram'}
# Shared lines other than rail, and private ways to travel, fastest first.
LINES = {'bus', 'ferry', 'water-taxi', 'boat', 'airship', 'stagecoach'}
PRIVATE = ('car', 'carriage', 'horse', 'bike-share')
DEFAULT_SPEEDS = {'walk': 4.5, 'car': 25, 'rideshare': 25, 'bus': 13, 'carriage': 10, 'horse': 12, 'tram': 15}
OVERHEAD = {'walk': 0, 'car': 6, 'rideshare': 8, 'bus': 9, 'ferry': 10, 'water-taxi': 10, 'bike-share': 3}


def unit(seed: str, *parts) -> float:
    """A stable number in [0, 1) for this seed and label."""
    digest = hashlib.sha256('\x1f'.join(map(str, (seed, *parts))).encode()).digest()
    return int.from_bytes(digest[:8], 'big') / 2 ** 64


def pick(seed: str, label: str, items: list, weights: list[float] | None = None):
    """Weighted choice that depends only on the seed, the label and the order of `items`."""
    if not items:
        return None
    weights = weights or [1.0] * len(items)
    total = sum(weights)
    target, running = unit(seed, label) * total, 0.0
    for item, weight in zip(items, weights, strict=True):
        running += weight
        if target < running:
            return item
    return items[-1]


def provenance(data: dict, refs: list[str]) -> dict:
    records = [catalog.find(data, ref) for ref in refs]
    cited = sorted({record['source'] for record in records if record})
    return {'city': data['id'], 'data_version': data['data_version'], 'refs': refs, 'sources': cited}


# --- Climate and the calendar ---

def conditions(data: dict, day: date, seed: str = '') -> dict | None:
    """Typical weather for the date from monthly climate, with a seeded chance of rain; None without a climate."""
    if not data['climate']:
        return None
    month = data['climate']['months'][day.month - 1]
    wet = unit(seed or day.isoformat(), data['id'], 'rain') < month['rain_days'] / 30
    return {'season': SEASONS[day.month], 'month': day.month, 'high_f': month['high_f'], 'low_f': month['low_f'],
            'rain': wet, 'note': month['note'], 'typical': True}


def annual_events(data: dict, day: date) -> list[dict]:
    """Recurring events usually held in this month. Exact dates vary year to year."""
    return [event for event in data['annual_events'] if day.month in event['months']]


# --- Getting around ---

def commute(data: dict, origin: str, destination: str, mode: str | None = None) -> dict:
    """An estimated trip between two neighborhoods, by the given mode or the likeliest one."""
    start, end = catalog.neighborhood(data, origin), catalog.neighborhood(data, destination)
    km = round(catalog.distance_km(start, end) * 1.3 + 0.4, 1)
    shared = [line for line in data['transit'] if line['id'] in start['transit'] and line['id'] in end['transit']]
    rail = next((line for line in shared if line['kind'] in RAIL), None)
    bus = next((line for line in shared if line['kind'] in LINES), None)
    line = None
    if mode is None:
        if km <= 1.6:
            mode = 'walk'
        elif rail:
            mode, line = rail['kind'], rail
        elif bus and start['walkability'] != 'low' and km <= 8:
            mode, line = bus['kind'], bus
        else:
            mode = next((kind for kind in PRIVATE if kind in data['speeds']), 'walk')
    elif mode in RAIL or mode in LINES:
        line = next((item for item in shared if item['kind'] == mode), None)
    speed = data['speeds'].get(mode) or DEFAULT_SPEEDS.get(mode, 4.5)
    minutes = round(km / speed * 60 + OVERHEAD.get(mode, 8))
    return {'from': origin, 'to': destination, 'mode': mode, 'line': line['name'] if line else None,
            'distance_km': km, 'minutes': max(minutes, 3), 'estimate': True}


# --- Outings and meals ---

def _affordable(place: dict, budget: str | None) -> bool:
    return budget is None or COSTS.index(place['cost']) <= COSTS.index(budget)


def _weight(data: dict, place: dict, around: dict | None, weather: dict | None) -> float:
    weight = 1.0
    if around:
        if place['neighborhood'] == around['id']:
            weight *= 6
        else:
            km = catalog.distance_km(around, catalog.neighborhood(data, place['neighborhood']))
            weight *= 3 if km <= 2.5 else 1.5 if km <= 6 else 0.6
    if weather:
        harsh = weather['rain'] or weather['high_f'] >= 93 or weather['high_f'] <= 38
        if harsh:
            weight *= {'indoor': 3, 'mixed': 1, 'outdoor': 0.15}[place['setting']]
    return weight


def outing(data: dict, *, seed: str, day: date | None = None, day_part: str = 'afternoon', company: str = 'solo',
           neighborhood: str | None = None, home: str | None = None, budget: str | None = None,
           kinds: list[str] | None = None, exclude: list[str] | tuple = ()) -> dict | None:
    """A plausible place to spend part of a day, near `neighborhood` when given.

    Constraints relax in order (day part, then company) rather than failing; `None` only when the
    city has no place of the requested kinds at all. Pass recently used place ids in `exclude` for
    variety.
    """
    around = catalog.neighborhood(data, neighborhood) if neighborhood else None
    weather = conditions(data, day, seed) if day else None
    pool = [place for place in data['places'] if place['id'] not in exclude and (not kinds or place['kind'] in kinds)
            and _affordable(place, budget)]
    season = weather['season'] if weather else None
    attempts = (
        lambda p: day_part in p['day_parts'] and company in p['good_for'],
        lambda p: company in p['good_for'],
        lambda p: True,
    )
    for test in attempts:
        options = [p for p in pool if test(p) and (not season or not p['seasons'] or season in p['seasons'])]
        if options:
            break
    else:
        return None
    chosen = pick(seed, 'outing', options, [_weight(data, p, around, weather) for p in options])
    refs = [chosen['id'], chosen['neighborhood']]
    result = {'place': chosen, 'neighborhood': catalog.neighborhood(data, chosen['neighborhood']),
              'day_part': day_part, 'company': company, 'weather': weather, 'travel': None}
    origin = home or neighborhood
    if origin:
        result['travel'] = commute(data, origin, chosen['neighborhood'])
        refs.append(origin)
    return result | provenance(data, refs)


def meal(data: dict, *, seed: str, meal: str = 'dinner', **options) -> dict | None:
    """Somewhere to eat: an outing limited to restaurants, cafes and markets (bars for a late bite)."""
    if meal not in MEALS:
        raise DomainError(f'Meal is one of {", ".join(MEALS)}.', 422)
    kinds = [*FOOD, 'bar'] if meal == 'late' else list(FOOD)
    result = outing(data, seed=seed, day_part=MEALS[meal], kinds=kinds, **options)
    return result | {'meal': meal} if result else None


# --- Work and routine ---

WEEKDAYS = [0, 1, 2, 3, 4]
# Each schedule kind lists variants of (possible work days, work start, work end, bedtime, waking time).
PATTERNS = {
    'office': [([WEEKDAYS], '08:30', '17:00', '23:00', '07:00'), ([WEEKDAYS], '09:00', '17:30', '23:00', '07:00'),
               ([WEEKDAYS], '09:30', '18:00', '23:30', '07:30')],
    'shift-day': [([[0, 2, 4], [1, 3, 5], [0, 1, 3], [2, 4, 6]], '07:00', '19:30', '21:30', '05:45')],
    'shift-night': [([[0, 1, 2], [3, 4, 5], [1, 3, 5]], '19:00', '07:30', '09:00', '16:00')],
    'rotating': [([[0, 1, 2, 3, 4], [2, 3, 4, 5, 6], [0, 3, 4, 5, 6]], '07:00', '15:30', '22:30', '06:00'),
                 ([[0, 1, 2, 3, 4], [2, 3, 4, 5, 6], [0, 3, 4, 5, 6]], '15:00', '23:30', '01:00', '09:00')],
    'evening': [([[1, 2, 3, 4, 5], [2, 3, 4, 5, 6]], '16:00', '23:30', '01:30', '09:30')],
    'early': [([WEEKDAYS, [1, 2, 3, 4, 5]], '05:30', '13:30', '21:30', '05:00')],
    'academic': [([WEEKDAYS], '08:00', '15:30', '22:30', '06:30')],
    'flexible': [([WEEKDAYS], '10:00', '16:00', '00:00', '08:00')],
}
STUDY = {'undergraduate', 'graduate-student'}


def schedule(career: dict, seed: str, workplace: str = '') -> list[dict]:
    """A weekly routine for this career, in the character `schedule` shape the life simulation reads."""
    day_options, start, end, bed, wake = pick(seed, 'variant', PATTERNS[career['schedule']])
    days = pick(seed, 'days', day_options)
    themes = career['themes'][:5] + ([workplace] if workplace else [])
    blocks = [{'key': 'work', 'label': career['name'], 'kind': 'study' if career['id'] in STUDY else 'work',
               'days': list(days), 'start': start, 'end': end, 'themes': themes},
              {'key': 'sleep', 'label': 'Asleep', 'kind': 'sleep', 'days': list(range(7)), 'start': bed,
               'end': wake, 'themes': []}]
    free = _free_time(start, end, bed)
    if free:
        blocks.append({'key': 'after-work', 'label': 'Free time after work', 'kind': 'leisure', 'days': list(days),
                       'start': free[0], 'end': free[1], 'themes': []})
    off = [day for day in range(7) if day not in days]
    if off:
        rest = _minutes(wake) + 120
        blocks.append({'key': 'day-off', 'label': 'Day off', 'kind': 'leisure', 'days': off,
                       'start': _clock(rest), 'end': _clock(rest + 6 * 60), 'themes': []})
    return blocks


def _minutes(value: str) -> int:
    hours, minutes = value.split(':')
    return int(hours) * 60 + int(minutes)


def _clock(total: int) -> str:
    total %= 24 * 60
    return f'{total // 60:02d}:{total % 60:02d}'


def _free_time(start: str, end: str, bed: str) -> tuple[str, str] | None:
    """The waking stretch between the end of a daytime shift and bedtime, when it is at least two hours."""
    if _minutes(end) < _minutes(start):
        return None
    begin, sleep = _minutes(end) + 60, _minutes(bed)
    if sleep <= _minutes(end):
        sleep += 24 * 60
    if sleep - begin < 120:
        return None
    return _clock(begin), _clock(min(sleep, begin + 4 * 60))


def job(data: dict, career_id: str, *, seed: str, home: str | None = None) -> dict:
    """An employer, workplace neighborhood, weekly schedule and commute for a career in this city.

    Named employers come from the data. Careers the data has no employer for work at a fitting place
    (a cafe for a barista) or at an unnamed employer in a matching career hub, so nothing is invented.
    """
    career = catalog.careers_for(data).get(career_id)
    if not career:
        raise DomainError(f'{data["name"]} has no career {career_id!r}.', 404, 'unknown_career')
    employers = [item for item in data['employers'] if career_id in item['careers']]
    refs = []
    if employers:
        chosen = pick(seed, 'employer', employers)
        employer = {'id': chosen['id'], 'name': chosen['name'], 'named': True, 'summary': chosen['summary'],
                    'fit': 'employer'}
        hood = chosen['neighborhood']
        refs.append(chosen['id'])
    elif career_id in STUDY and data['colleges']:
        chosen = pick(seed, 'college', data['colleges'])
        employer = {'id': chosen['id'], 'name': chosen['name'], 'named': True,
                    'summary': f'Known for {", ".join(chosen["known_for"][:3]).replace("-", " ")}.', 'fit': 'college'}
        hood = chosen['neighborhood']
        refs.append(chosen['id'])
    elif places := [place for place in data['places'] if place['kind'] in
                    WORKPLACE_KINDS.get(career_id, SECTOR_KINDS.get(career['sector'], ()))]:
        chosen = pick(seed, 'workplace', places)
        employer = {'id': chosen['id'], 'name': chosen['name'], 'named': True, 'summary': chosen['summary'],
                    'fit': 'workplace'}
        hood = chosen['neighborhood']
        refs.append(chosen['id'])
    else:
        matching = [hub for hub in data['career_hubs'] if career['sector'] in hub['sectors']]
        hub = pick(seed, 'hub', matching or data['career_hubs'])
        hood = pick(seed, 'hub-neighborhood', hub['neighborhoods'] if hub else
                    [item['id'] for item in data['neighborhoods']])
        place_name = catalog.neighborhood(data, hood)['name']
        employer = {'id': None, 'name': f'a workplace in {place_name}' + (f' ({hub["name"]})' if hub else ''),
                    'named': False, 'summary': hub['summary'] if hub else '', 'fit': 'hub' if matching else 'weak'}
        refs.extend([hub['id']] if hub else [])
    refs.append(hood)
    result = {'career': career, 'employer': employer, 'neighborhood': catalog.neighborhood(data, hood),
              'schedule': schedule(career, seed, employer['name'] if employer['named'] else ''), 'commute': None}
    if home:
        result['commute'] = commute(data, home, hood)
        refs.append(home)
    return result | provenance(data, refs)


# --- Housing ---

def home(data: dict, *, seed: str, bedrooms: str = 'one_bedroom', budget: int | None = None,
         vibe: str | None = None, near: str | None = None) -> dict:
    """A neighborhood, housing type and rent within that neighborhood's typical range.

    `budget` is a maximum in the city's currency per its `rent_period`; when nothing fits, the cheapest
    neighborhoods are used. `rent` is None in settings without rents.
    """
    if bedrooms not in BEDROOMS:
        raise DomainError(f'Bedrooms is one of {", ".join(BEDROOMS)}.', 422)
    hoods = data['neighborhoods']
    priced = [hood for hood in hoods if hood['rent']]
    fits = [hood for hood in priced if budget is None or hood['rent'][bedrooms][0] <= budget]
    if priced and not fits:
        fits = sorted(priced, key=lambda hood: hood['rent'][bedrooms][0])[:3]
    fits = fits or hoods
    anchor = catalog.neighborhood(data, near) if near else None
    weights = []
    for hood in fits:
        weight = 3.0 if vibe and vibe in hood['vibe'] else 1.0
        if anchor:
            km = catalog.distance_km(anchor, hood)
            weight *= 4 if km <= 2 else 2 if km <= 5 else 1
        weights.append(weight)
    chosen = pick(seed, 'home', fits, weights)
    result = {'neighborhood': chosen, 'housing': pick(seed, 'housing', chosen['housing']), 'bedrooms': bedrooms,
              'rent': None, 'rent_range': None, 'currency': data['currency'], 'rent_period': data['rent_period'],
              'estimate': True}
    if chosen['rent']:
        low, high = chosen['rent'][bedrooms]
        top = max(low, min(high, budget)) if budget is not None else high
        result |= {'rent': low + round(unit(seed, 'rent') * (top - low) / 25) * 25, 'rent_range': [low, high]}
    return result | provenance(data, [chosen['id']])


# --- Grounding text ---

def facts(data: dict, neighborhood: str | None = None, limit: int = 8) -> list[str]:
    """Short factual lines for a prompt, so the model describes real places instead of inventing them."""
    lines = [f'{data["name"]}, {data["region"]}: {data["summary"]}']
    if neighborhood:
        hood = catalog.neighborhood(data, neighborhood)
        lines.append(f'{hood["name"]}: {hood["summary"]}')
        for place in catalog.places(data, neighborhood=neighborhood)[:limit]:
            lines.append(f'{place["name"]} ({place["kind"]}): {place["summary"]}')
    return lines
