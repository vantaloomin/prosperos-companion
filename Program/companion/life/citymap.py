"""The city map (Hit List #40): where the companion lives and goes, and every place in their city to click.

Everything comes from state the app already keeps, with no model: the city pack's neighbourhoods and places,
the companion's home, the places their committed life events happened at (usual ones and recent ones),
Story mode's current scene, and townsfolk the companion knows who are regulars or staff somewhere. Places
have no coordinates in the city packs, so each sits at a small seeded offset from its neighbourhood's centre
and says its location is approximate. Real public cities are drawn on a street map in the interface; the
rest (fictional, original and private cities) on a sketch of their neighbourhoods. Everyone's home in the city is
on it: theirs, the user's (where the user lives in this world, companion/life/where.py), the other companions' and
the people in any companion's circle who live here. It never shows where the user is right now.

What is inside a place is one list, the user's to rewrite: their home's rooms are kept on their home
(companion/life/home.py), and a place's spots in `place_spots` (companion/world/inside.py).
"""
import math
from datetime import timedelta

from companion.clock import stamp, zone
from companion.database import decode, many, optional
from companion.life import circle, encounters, home, network
from companion.world import catalog, generators, inside

USUAL_DAYS = 60
USUAL_TIMES = 2
RECENT_DAYS = 14
HISTORY = 3
# How far a place may sit from its neighbourhood's centre, in degrees (a few hundred metres).
SPREAD = 0.004
NEXT_TO = 2


def real(data: dict) -> bool:
    """A real, public city of today gets a street map; anything else (New York in 1925 too) a sketch."""
    return data.get('setting', 'real') == 'real' and data.get('distribution', 'public') == 'public' and \
        (data.get('era') or 'modern') == 'modern'


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
    """Committed events at a named place in their own city, newest first: {id, place, summary, at, block}. A plan
    is not a visit, and a trip's places are in another city (whose ids can match ones here)."""
    rows = many(connection, "SELECT id, summary, starts_at, details FROM life_events WHERE timeline_id=? AND "
                "status='committed' AND starts_at<=? AND json_extract(details, '$.place.id') IS NOT NULL "
                "AND kind<>'plan' AND json_extract(details, '$.trip') IS NULL "
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
    """Names of townsfolk the companion knows, by the place they frequent (not the staff who work there)."""
    found = {}
    for person in encounters.known(connection, companion, now):
        if person['kind'] != 'resident' and not person['staff'] and not person['key'].startswith('cast:') and \
                not person.get('left'):  # Not someone they know has since moved away (companion/world/turnover.py).
            found.setdefault(person['place']['id'], []).append(person['name'])
    return found


def home_item(connection, timeline_id: str, timezone: str, now) -> dict | None:
    day = now.astimezone(zone(timezone)).date()
    return next((item for item in home.items_on(connection, timeline_id, day) if item['kind'] == 'home'), None)


def hood_by_name(hoods: dict, name: str | None) -> dict | None:
    return next((hood for hood in hoods.values() if name and hood['name'] == name), None)


def home_view(place_id: str, name: str, hood: dict, pin: str, spots=(), about='', centre=False) -> dict:
    """A home as a place on the map: theirs at its neighbourhood's centre, everyone else's a little off it."""
    north, east = (0.0, 0.0) if centre else offset(place_id)
    return {'id': place_id, 'name': name, 'kind': 'home', 'hood': hood['name'], 'hood_id': hood['id'],
            'lat': round(hood['lat'] + north, 6), 'lon': round(hood['lon'] + east, 6), 'approx': True, 'pins': [pin],
            'spots': list(spots), 'about': about, 'history': [], 'regulars': []}


def home_pin(connection, companion: dict, data: dict, hoods: dict, now) -> dict | None:
    """Their home as a pin at its neighbourhood's centre, when it is in this city, with its rooms and description."""
    item = home_item(connection, companion['active_timeline_id'], companion['version']['timezone'], now)
    hood = item and hood_by_name(hoods, item.get('neighborhood'))
    if not hood or item.get('city') not in (data['name'], None):
        return None
    found = home_view('~home', f"{companion['version']['name']}'s home", hood, 'home',
                      inside.names(inside.for_home(item)), item.get('description', ''), centre=True)
    return found | {'item_id': item['id'], 'rooms_set': bool(item.get('rooms'))}


def your_pin(connection, data: dict, hoods: dict) -> dict | None:
    """Where the user lives in this world, when it is this city (companion/life/where.py)."""
    row = optional(connection, 'SELECT home_city_id, home_neighbourhood FROM persona WHERE id=1')
    hood = row and row['home_city_id'] == data['id'] and hoods.get(row['home_neighbourhood'])
    return home_view('~you', 'Your home', hood, 'yours') if hood else None


def known_pins(connection, companion: dict, data: dict, hoods: dict, now) -> list[dict]:
    """The other companions' homes in this city, then the homes of people in any companion's circle who live here,
    each person once, with who they are ("Sett's friend")."""
    others = many(connection, 'SELECT c.id, c.active_timeline_id, v.name, v.timezone FROM companions c JOIN '
                  'character_versions v ON v.id=c.active_version_id WHERE c.id<>? ORDER BY c.created_at',
                  (companion['id'],))
    taken, found = {companion['version']['name']}, []
    for other in others:
        item = home_item(connection, other['active_timeline_id'], other['timezone'], now)
        hood = item and item.get('city') == data['name'] and hood_by_name(hoods, item.get('neighborhood'))
        if hood and other['name'] not in taken:
            taken.add(other['name'])
            found.append(home_view(f"~companion:{other['id']}", f"{other['name']}'s home", hood, 'known',
                                   about=item.get('description', '')) | {'relation': 'Another companion'})
    owners = [(companion['active_timeline_id'], companion['version']['name']),
              *((other['active_timeline_id'], other['name']) for other in others)]
    for timeline_id, owner in owners:
        for person in circle.people(connection, timeline_id):
            details = decode(person['details'])
            hood = details.get('city') == data['name'] and hood_by_name(hoods, details.get('neighborhood'))
            if hood and person['name'] not in taken:
                taken.add(person['name'])
                role = circle.relation(person['role'], details.get('pronouns', ''))
                found.append(home_view(f"~circle:{person['id']}", f"{person['name']}'s home", hood, 'known')
                             | {'relation': f"{owner}'s {role}"})
    return found


def scene_place(connection, data: dict) -> str | None:
    from companion import story
    row = story.scene_row(connection)
    return row['place_id'] if row['city_id'] == data['id'] else None


def place_view(place: dict, hood: dict, pins: set[str], events: list[dict], people: list[str], era=None) -> dict:
    north, east = offset(place['id'])
    return {'id': place['id'], 'name': place['name'], 'kind': place['kind'], 'hood': hood['name'], 'hood_id': hood['id'],
            'lat': round(hood['lat'] + north, 6), 'lon': round(hood['lon'] + east, 6), 'approx': True,
            'pins': sorted(pins), 'spots': inside.names(inside.for_place(place, era)),
            'spots_set': bool(place.get('spots_set')),
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
    edits = inside.edited(connection, data['id'])
    for place in data['places']:
        hood = hoods.get(place['neighborhood'])
        if place['id'] in edits:
            place = inside.with_edits(place, edits) | {'spots_set': True}
        if hood:
            pins = marked.get(place['id'], set()) | ({'scene'} if place['id'] == scene else set())
            places.append(place_view(place, hood, pins, by_place.get(place['id'], []), people.get(place['id'], []), data.get('era')))
    homes = [pin for pin in (home_pin(connection, companion, data, hoods, now), your_pin(connection, data, hoods))
             if pin] + known_pins(connection, companion, data, hoods, now)
    next_to = neighbours(list(hoods.values()))
    return {'city': {'id': data['id'], 'name': data['name'], 'lat': data['lat'], 'lon': data['lon'], 'real': real(data),
                     'enclosed': data.get('enclosed') is True},
            'hoods': [{'id': hood['id'], 'name': hood['name'], 'lat': hood['lat'], 'lon': hood['lon'],
                       'next': next_to[hood['id']]} for hood in hoods.values()],
            'places': homes + places, 'water': data.get('water') or [], 'story': story_on}
