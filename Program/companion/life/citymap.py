"""The city map (Hit List #40): where the companion lives and goes, and every place in their city to click.

Everything comes from state the app already keeps, with no model: the city pack's neighbourhoods and places,
the companion's home, the places their committed life events happened at (usual ones and recent ones),
Story mode's current scene, and townsfolk the companion knows who are regulars or staff somewhere. Places
have no coordinates in the city packs, so each sits at a small seeded offset from its neighbourhood's centre
and says its location is approximate. Real public cities are drawn on a street map in the interface; the
rest (fictional, original and private cities) on a sketch of their neighbourhoods. The map never shows
where the user is.
"""
import math
from datetime import timedelta

from companion.clock import stamp, zone
from companion.database import decode, many
from companion.life import encounters, home, network
from companion.world import catalog, generators, inside

USUAL_DAYS = 60
USUAL_TIMES = 2
RECENT_DAYS = 14
HISTORY = 3
# How far a place may sit from its neighbourhood's centre, in degrees (a few hundred metres).
SPREAD = 0.004
NEXT_TO = 2


def real(data: dict) -> bool:
    """A real, public city gets a street map; anything else a sketch."""
    return data.get('setting', 'real') == 'real' and data.get('distribution', 'public') == 'public'


def offset(place_id: str) -> tuple[float, float]:
    angle = generators.unit(place_id, 'map-angle') * 2 * math.pi
    reach = SPREAD * (0.25 + 0.75 * math.sqrt(generators.unit(place_id, 'map-reach')))
    return reach * math.sin(angle), reach * math.cos(angle)


def neighbours(hoods: list[dict]) -> dict[str, list[str]]:
    """Each neighbourhood's nearest few, for the sketch's dotted lines: the packs say where each is, not what
    borders what, so being close stands in for being next to each other."""
    result = {}
    for hood in hoods:
        others = sorted((item for item in hoods if item['id'] != hood['id']),
                        key=lambda item: catalog.distance_km(hood, item))
        result[hood['id']] = [item['id'] for item in others[:NEXT_TO]]
    return result


def history(connection, timeline_id: str, now) -> list[dict]:
    """Committed events at a named place, newest first: {id, place, summary, at, block}."""
    rows = many(connection, "SELECT id, summary, starts_at, details FROM life_events WHERE timeline_id=? AND "
                "status='committed' AND starts_at<=? AND json_extract(details, '$.place.id') IS NOT NULL "
                'ORDER BY starts_at DESC LIMIT 400', (timeline_id, stamp(now)))
    found = []
    for row in rows:
        details = decode(row['details'])
        found.append({'id': row['id'], 'place': details['place']['id'], 'summary': row['summary'],
                      'at': row['starts_at'], 'block': details.get('block_kind', '')})
    return found


def marks(events: list[dict], now) -> dict[str, set[str]]:
    """Which places are their usual ones and recent ones, by place id. Companions have no set workplace yet (a lunch
    break at a deli is not where they work), so no place is marked as work."""
    usual_since, recent_since = stamp(now - timedelta(days=USUAL_DAYS)), stamp(now - timedelta(days=RECENT_DAYS))
    counts, result = {}, {}
    for event in events:
        if event['at'] >= usual_since:
            counts[event['place']] = counts.get(event['place'], 0) + 1
        if event['at'] >= recent_since:
            result.setdefault(event['place'], set()).add('recent')
    for place_id, count in counts.items():
        if count >= USUAL_TIMES:
            result.setdefault(place_id, set()).add('usual')
    return result


def regulars(connection, companion: dict, now) -> dict[str, list[str]]:
    """Names of townsfolk the companion knows, by the place they work at or frequent."""
    found = {}
    for person in encounters.known(connection, companion, now):
        if person['kind'] != 'resident' and not person['key'].startswith('cast:'):
            found.setdefault(person['place']['id'], []).append(person['name'])
    return found


def home_pin(connection, companion: dict, data: dict, hoods: dict, now) -> dict | None:
    """Their home as a pin at its neighbourhood's centre, when it is in this city."""
    day = now.astimezone(zone(companion['version']['timezone'])).date()
    item = next((item for item in home.items_on(connection, companion['active_timeline_id'], day)
                 if item['kind'] == 'home'), None)
    hood = item and next((hood for hood in hoods.values() if hood['name'] == item.get('neighborhood')), None)
    if not hood or item.get('city') not in (data['name'], None):
        return None
    return {'id': '~home', 'name': f"{companion['version']['name']}'s home", 'kind': 'home', 'hood': hood['name'],
            'hood_id': hood['id'], 'lat': hood['lat'], 'lon': hood['lon'], 'approx': True, 'pins': ['home'],
            'spots': inside.names(inside.for_home(item)), 'history': [], 'regulars': []}


def scene_place(connection, data: dict) -> str | None:
    from companion import story
    row = story.scene_row(connection)
    return row['place_id'] if row['city_id'] == data['id'] else None


def place_view(place: dict, hood: dict, pins: set[str], events: list[dict], people: list[str]) -> dict:
    north, east = offset(place['id'])
    return {'id': place['id'], 'name': place['name'], 'kind': place['kind'], 'hood': hood['name'], 'hood_id': hood['id'],
            'lat': round(hood['lat'] + north, 6), 'lon': round(hood['lon'] + east, 6), 'approx': True,
            'pins': sorted(pins), 'spots': inside.names(inside.for_place(place)),
            'history': [{'id': event['id'], 'summary': event['summary'], 'at': event['at']} for event in events[:HISTORY]],
            'regulars': sorted(set(people))}


def build(connection, companion: dict, now, story_on: bool) -> dict:
    data = network.city(connection, companion)
    hoods = {hood['id']: hood for hood in data['neighborhoods']}
    events = history(connection, companion['active_timeline_id'], now)
    marked = marks(events, now)
    scene = scene_place(connection, data) if story_on else None
    people = regulars(connection, companion, now)
    by_place = {}
    for event in events:
        by_place.setdefault(event['place'], []).append(event)
    places = []
    for place in data['places']:
        hood = hoods.get(place['neighborhood'])
        if hood:
            pins = marked.get(place['id'], set()) | ({'scene'} if place['id'] == scene else set())
            places.append(place_view(place, hood, pins, by_place.get(place['id'], []), people.get(place['id'], [])))
    found = home_pin(connection, companion, data, hoods, now)
    next_to = neighbours(list(hoods.values()))
    return {'city': {'id': data['id'], 'name': data['name'], 'lat': data['lat'], 'lon': data['lon'], 'real': real(data)},
            'hoods': [{'id': hood['id'], 'name': hood['name'], 'lat': hood['lat'], 'lon': hood['lon'],
                       'next': next_to[hood['id']]} for hood in hoods.values()],
            'places': ([found] if found else []) + places, 'water': data.get('water') or [], 'story': story_on}
