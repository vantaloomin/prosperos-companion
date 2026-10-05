"""Loading and querying the shipped city data. Everything here is read-only and needs no network."""
import hashlib
import json
import math
import os
import re
from functools import cache
from pathlib import Path

from pydantic import ValidationError

from companion.errors import DomainError
from companion.identity import data_dir
from companion.world.schema import Careers, City, Names

DATA = Path(__file__).parent / 'data'


@cache
def careers() -> dict[str, dict]:
    """The shared career catalogue, across every era."""
    catalogue = Careers.model_validate_json((DATA / 'careers.json').read_text(encoding='utf-8'))
    return {career.id: career.model_dump() for career in catalogue.careers}


def careers_for(data: dict) -> dict[str, dict]:
    """Careers a city offers: the shared ones for its era, then its own (which win on a shared id)."""
    shared = {key: value for key, value in careers().items() if data['era'] in value['eras']}
    return shared | {career['id']: career for career in data['careers']}


@cache
def names() -> dict:
    """The shared name banks and each era's default bank and group weights."""
    return Names.model_validate_json((DATA / 'names.json').read_text(encoding='utf-8')).model_dump()


def name_groups(data: dict) -> tuple[dict[str, dict], dict[str, float]]:
    """The name groups a city draws residents' names from, and the weight of each.

    A city's own `names.mix` wins; a city with its own groups and no mix uses only those; otherwise the era's
    weights apply when the city keeps its era's bank, else every group of the bank weighs the same.
    """
    own = data.get('names') or {}
    era = names()['eras'][data['era']]
    bank = own.get('bank') or era['bank']
    groups = names()['banks'][bank] | own.get('groups', {})
    if own.get('mix'):
        mix = own['mix']
    elif own.get('groups'):
        mix = dict.fromkeys(own['groups'], 1.0)
    elif bank == era['bank'] and era['mix']:
        mix = era['mix']
    else:
        mix = {}
    # Weights for groups the bank lacks (say, after a city changes era) are ignored.
    mix = {key: weight for key, weight in mix.items() if weight > 0 and key in groups}
    return groups, mix or dict.fromkeys(groups, 1.0)


def prepare(raw: bytes | str | dict) -> dict:
    """Validate one city definition and give it a `data_version`. Raises pydantic's ValidationError."""
    model = City.model_validate(raw) if isinstance(raw, dict) else City.model_validate_json(raw)
    data = model.model_dump(mode='json')
    known = careers_for(data)
    for employer in data['employers']:
        unknown = set(employer['careers']) - set(known)
        if unknown:
            raise ValueError(f'{employer["id"]} names careers this city does not offer: {sorted(unknown)}.')
    own = data.get('names') or {}
    if own.get('bank') and own['bank'] not in names()['banks']:
        raise ValueError(f'Unknown name bank {own["bank"]!r}; the banks are {sorted(names()["banks"])}.')
    # Identifies the exact data a generator used, so a recorded event can name its inputs (PRD T7).
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    data['data_version'] = hashlib.sha256(canonical.encode()).hexdigest()[:12]
    return data


PACKS_ENV = 'COMPANION_CITY_PACKS'
# Personal city packs (PRD W5), such as private fan cities. The checkout's folder is gitignored.
CHECKOUT_PACKS = Path(__file__).resolve().parents[2] / 'private-cities'


def pack_dirs() -> list[Path]:
    """Folders searched for city packs: `COMPANION_CITY_PACKS` (os.pathsep-separated) or the defaults."""
    if os.environ.get(PACKS_ENV):
        return [Path(item) for item in os.environ[PACKS_ENV].split(os.pathsep) if item]
    return [CHECKOUT_PACKS, data_dir() / 'city-packs']


@cache
def _library() -> tuple[dict[str, dict], tuple[dict, ...]]:
    result, errors = {}, []
    for path in sorted((DATA / 'cities').glob('*.json')):
        data = prepare(path.read_bytes())
        if data['id'] != path.stem:
            raise ValueError(f'{path.name} holds city {data["id"]}.')
        result[data['id']] = data | {'builtin': True, 'origin': 'builtin'}
    for folder in pack_dirs():
        for path in sorted(folder.glob('*.json')) if folder.is_dir() else []:
            try:
                data = prepare(path.read_bytes())
            except (ValidationError, ValueError, OSError) as error:
                errors.append({'file': str(path), 'error': str(error)[:2000]})
                continue
            if data['id'] in result:
                errors.append({'file': str(path), 'error': f'City id {data["id"]!r} is already loaded.'})
                continue
            result[data['id']] = data | {'builtin': False, 'origin': 'pack', 'pack_file': str(path)}
    return result, tuple(errors)


def cities() -> dict[str, dict]:
    """Built-in cities shipped with the app, then any city packs found in the pack folders. Read-only."""
    return _library()[0]


def packs() -> dict:
    """What the pack folders hold, for the interface and for troubleshooting a pack that did not load."""
    loaded = [summary(data) | {'file': data['pack_file']} for data in cities().values() if data['origin'] == 'pack']
    return {'folders': [str(folder) for folder in pack_dirs()], 'loaded': loaded, 'errors': list(_library()[1])}


def reload() -> dict:
    _library.cache_clear()
    return packs()


def city(city_id: str, extra: dict[str, dict] | None = None) -> dict:
    """A built-in city, or one of `extra` (the user's own cities)."""
    found = cities().get(city_id) or (extra or {}).get(city_id)
    if not found:
        raise DomainError(f'No world data for city {city_id!r}.', 404, 'unknown_city')
    return found


def summary(data: dict) -> dict:
    keys = ('id', 'name', 'setting', 'era', 'basis', 'region', 'country', 'timezone', 'aliases', 'summary',
            'data_version')
    return {key: data[key] for key in keys} | {
        'counts': {key: len(data[key]) for key in ('neighborhoods', 'places', 'colleges', 'employers',
                                                   'annual_events')}, 'builtin': data.get('builtin', False),
        'origin': data.get('origin', 'user'), 'distribution': data['distribution']}


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


def resolve(text: str, extra: dict[str, dict] | None = None) -> dict | None:
    """Match free text such as a character's `location` ("Fells Point, Baltimore") to a city and neighborhood.

    Returns `{"city": id, "neighborhood": id | None}` or `None` when no shipped city matches.
    """
    words = f' {_words(text)} '
    if not words.strip():
        return None
    for data in [*cities().values(), *(extra or {}).values()]:
        names = [data['name'], data['id'].replace('-', ' '), *data['aliases']]
        if any(f' {_words(name)} ' in words for name in names if _words(name)):
            hood = next((item['id'] for item in data['neighborhoods'] if f' {_words(item["name"])} ' in words), None)
            return {'city': data['id'], 'neighborhood': hood}
    return None


def sources(data: dict) -> list[dict]:
    """Every source the city's records cite, for attribution screens."""
    return [{'id': key} | value for key, value in data['sources'].items()]
