"""Character-sheet lines for a townsperson who becomes a companion (companion/cast.py), drawn by seed from a bank,
no model: what their work makes them good at, something they are only middling at, what makes them laugh or snap,
and a few habits of how they talk.

Work skills are found by the career's id (shared careers and every city's own), else the title they hold at a place
in town (the bartender, the sexton), else the career's sector, so a career a custom city adds still gets some. A
retired townsperson keeps the skills of the job they retired from (companion/world/life_details.py). The bank is
data (world/data/profile_bank.json), so it can grow without code changes.
"""
import json
from functools import cache

from companion.world import catalog, generators, life_details, townsfolk

JOB_SKILLS = 2
SPEECH = 2
LISTS = ('laughs', 'snaps', 'speech', 'middling')


@cache
def bank() -> dict:
    data = json.loads((catalog.DATA / 'profile_bank.json').read_text(encoding='utf-8'))
    for kind in LISTS:
        if len(data[kind]) != len(set(data[kind])):
            raise ValueError(f'profile_bank.json repeats an entry in {kind}.')
    return data


def picks(seed: str, label: str, items: list[str], count: int) -> list[str]:
    """`count` of the items, the same ones every time for this seed."""
    return sorted(items, key=lambda item: generators.unit(seed, label, item))[:count]


def worked_as(data: dict, sheet: dict) -> dict | None:
    """The career they have now, or the one they retired from."""
    careers = catalog.careers_for(data, needs_met=False)
    occupation = (sheet.get('occupation') or '').lower()
    if occupation == 'retired':
        occupation = life_details.retired_from(data, sheet, townsfolk.drawn(sheet)) or ''
    return next((career for career in careers.values() if career['name'].lower() in (occupation, sheet['role'])), None)


def job_skills(data: dict, sheet: dict) -> list[str]:
    """Two things their work makes them good at, or none when the bank knows nothing about it."""
    found, career = bank(), worked_as(data, sheet)
    lines = (career and found['careers'].get(career['id'])) or \
        (sheet.get('staff') and found['staff'].get(sheet['role'])) or \
        (career and found['sectors'].get(career.get('sector', ''))) or []
    return picks(townsfolk.drawn(sheet), 'profile-skill', lines, JOB_SKILLS)


def middling(sheet: dict) -> str:
    return generators.pick(townsfolk.drawn(sheet), 'profile-middling', bank()['middling'])


def laughs_and_snaps(sheet: dict) -> tuple[str, str]:
    seed = townsfolk.drawn(sheet)
    return (generators.pick(seed, 'profile-laughs', bank()['laughs']),
            generators.pick(seed, 'profile-snaps', bank()['snaps']))


def speech(sheet: dict) -> list[str]:
    return picks(townsfolk.drawn(sheet), 'profile-speech', bank()['speech'], SPEECH)
