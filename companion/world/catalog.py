"""Loading and querying the shipped city data. Everything here is read-only and needs no network."""
import hashlib
import math
import re
from functools import cache
from pathlib import Path

from companion.errors import DomainError
from companion.world.schema import Careers, City

DATA = Path(__file__).parent / 'data'


@cache
def careers() -> dict[str, dict]:
    catalogue = Careers.model_validate_json((DATA / 'careers.json').read_text(encoding='utf-8'))
    return {career.id: career.model_dump() for career in catalogue.careers}


@cache
def cities() -> dict[str, dict]:
    known = careers()
    result = {}
    for path in sorted((DATA / 'cities').glob('*.json')):
        raw = path.read_bytes()
        city = City.model_validate_json(raw).model_dump()
        if city['id'] != path.stem:
            raise ValueError(f'{path.name} holds city {city["id"]}.')
        for employer in city['employers']:
            unknown = set(employer['careers']) - set(known)
            if unknown:
                raise ValueError(f'{employer["id"]} names unknown careers {sorted(unknown)}.')
        # Identifies the exact data a generator used, so a recorded event can name its inputs (PRD T7).
        city['data_version'] = hashlib.sha256(raw).hexdigest()[:12]
        result[city['id']] = city
    return result


def city(city_id: str) -> dict:
    try:
        return cities()[city_id]
    except KeyError:
        raise DomainError(f'No world data for city {city_id!r}.', 404, 'unknown_city') from None


def summary(data: dict) -> dict:
    keys = ('id', 'name', 'region', 'country', 'timezone', 'aliases', 'summary', 'data_version')
    return {key: data[key] for key in keys} | {
        'counts': {key: len(data[key]) for key in ('neighborhoods', 'places', 'colleges', 'employers',
                                                   'annual_events')}}


def neighborhood(data: dict, hood_id: str) -> dict:
    for hood in data['neighborhoods']:
        if hood['id'] == hood_id:
            return hood
    raise DomainError(f'No neighborhood {hood_id!r} in {data["name"]}.', 404, 'unknown_neighborhood')


def find(data: dict, record_id: str) -> dict | None:
    for group in ('neighborhoods', 'places', 'colleges', 'employers', 'career_hubs', 'transit', 'annual_events'):
        for item in data[group]:
            if item['id'] == record_id:
                return item
    return None


def places(data: dict, *, kind: str | None = None, neighborhood: str | None = None, tag: str | None = None,
           good_for: str | None = None) -> list[dict]:
    return [item for item in data['places']
            if (kind is None or item['kind'] == kind) and (neighborhood is None or item['neighborhood'] == neighborhood)
            and (tag is None or tag in item['tags']) and (good_for is None or good_for in item['good_for'])]


def distance_km(a: dict, b: dict) -> float:
    """Great-circle distance between two records with `lat` and `lon`."""
    lat1, lon1, lat2, lon2 = map(math.radians, (a['lat'], a['lon'], b['lat'], b['lon']))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def nearby(data: dict, hood_id: str, limit: int = 4) -> list[dict]:
    """The closest other neighborhoods, nearest first."""
    origin = neighborhood(data, hood_id)
    others = [hood for hood in data['neighborhoods'] if hood['id'] != hood_id]
    return sorted(others, key=lambda hood: (distance_km(origin, hood), hood['id']))[:limit]


def _words(text: str) -> str:
    return ' '.join(re.findall(r'[a-z0-9]+', text.lower()))


def resolve(text: str) -> dict | None:
    """Match free text such as a character's `location` ("Fells Point, Baltimore") to a city and neighborhood.

    Returns `{"city": id, "neighborhood": id | None}` or `None` when no shipped city matches.
    """
    words = f' {_words(text)} '
    if not words.strip():
        return None
    for data in cities().values():
        names = [data['name'], data['id'].replace('-', ' '), *data['aliases']]
        if any(f' {_words(name)} ' in words for name in names if _words(name)):
            hood = next((item['id'] for item in data['neighborhoods'] if f' {_words(item["name"])} ' in words), None)
            return {'city': data['id'], 'neighborhood': hood}
    return None


def sources(data: dict) -> list[dict]:
    """Every source the city's records cite, for attribution screens."""
    return [{'id': key} | value for key, value in data['sources'].items()]
