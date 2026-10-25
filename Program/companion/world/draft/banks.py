"""The Draft Table's data banks (world/data/draft): places, neighbourhoods, employers, events, local colour, transit
and the words names are made from. Every entry belongs to an era group and may narrow itself to some eras, to a
ship or the ground, or to a place by the sea, a river or a lake."""
import json
from functools import cache

from companion.world import catalog

DATA = catalog.DATA / 'draft'


@cache
def load(name: str) -> dict:
    return json.loads((DATA / f'{name}.json').read_text(encoding='utf-8'))


@cache
def folder(name: str) -> tuple[dict, ...]:
    """Every entry of a folder of bank files (places/, hoods/), each tagged with its file's group."""
    found = []
    for path in sorted((DATA / name).glob('*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        found += [entry | {'group': data['group']} for entry in data[name]]
    return tuple(found)


def words() -> dict:
    return load('words')


def kinds() -> dict:
    return load('kinds')['kinds']


def fits(entry: dict, brief: dict) -> bool:
    """Whether a bank entry suits the place: its group, then any era, water or ship-or-ground it asks for."""
    if entry['group'] != brief['group']:
        return False
    if entry.get('eras') and brief['era'] not in entry['eras']:
        return False
    if entry.get('water') and brief['water'] not in entry['water']:
        return False
    return entry.get('aboard') is None or entry['aboard'] == brief['aboard']


def places(brief: dict) -> list[dict]:
    return [entry for entry in folder('places') if fits(entry, brief)]


def hoods(brief: dict) -> list[dict]:
    return [entry for entry in folder('hoods') if fits(entry, brief)]


def entries(name: str, brief: dict) -> list[dict]:
    """The fitting entries of one bank file (employers, events, colour, transit), keyed by the file's name."""
    return [entry for entry in load(name)[name] if fits(entry, brief)]
