"""The user's changes to the pets of the people in the companion's circle (companion/life/pets.py `circle_pets`).

The app still decides first: about half the circle has a pet, seeded by who they are. Once the user changes one
person's pets (renames one, makes it another kind, redescribes it, gives it another age, removes it or adds one),
that person's pets are kept as the user left them, in `pets_by_user` in their details, and seeding no longer
touches them: a removed pet stays removed. Each pet keeps its key (`circle:<person>:<n>`), so the life it lived so
far stays; the days ahead follow the new details.
"""
from datetime import date

from companion.clock import stamp
from companion.database import decode, encode
from companion.errors import require
from companion.life import circle, pets

KEPT = 'pets_by_user'


def entry_of(found: dict, number: int) -> dict:
    return {'n': number, 'name': found['name'], 'kind': found['kind'], 'looks': found['looks'],
            'born': found['born'].isoformat(), 'start': found['start'].isoformat(), 'lifespan': found['lifespan']}


def found_of(person_id: str, entry: dict, era: str) -> dict:
    return pets.pet(f"circle:{person_id}:{entry['n']}", entry['name'], entry['kind'], entry['looks'],
                    date.fromisoformat(entry['born']), date.fromisoformat(entry['start']), era, entry['lifespan'],
                    owner='circle', number=entry['n'])


def entries(person: dict, where: dict) -> list[dict]:
    """The person's pets as kept, removed ones included: the user's, else the seeded ones."""
    kept = person.get(KEPT)
    if kept is not None:
        return kept
    seeded = pets.circle_pets(person, where['era'], where['start'], where['aboard'])
    return [entry_of(found, number) for number, found in enumerate(seeded)]


def of_person(person: dict, where: dict) -> list[dict]:
    """Their pets for pets.lived: the seeded ones until the user changed any, then the user's, minus removed."""
    return [found_of(person['id'], entry, where['era']) for entry in entries(person, where) if not entry.get('removed')]


def change(connection, person_id: str, where: dict, now, update) -> dict:
    """Run `update(entries)` on one person's pets and keep the result as theirs from now on."""
    row = circle.person(connection, person_id)
    require(row['status'] == 'active', 'Restore this person before changing their pets.', 409)
    details = decode(row['details'])
    kept = [dict(entry) for entry in entries({**details, 'id': person_id, 'key': row['seed']}, where)]
    update(kept)
    details[KEPT] = kept
    connection.execute('UPDATE circle_people SET details=?, updated_at=? WHERE id=?',
                       (encode(details), stamp(now), person_id))
    return row


def find(kept: list[dict], number: int) -> dict:
    entry = next((entry for entry in kept if entry['n'] == number and not entry.get('removed')), None)
    require(entry is not None, 'That pet is not theirs any more.', 404)
    return entry


def kind_of(kind: str | None) -> str | None:
    if kind is None:
        return None
    require(kind in pets.kinds(), 'Pick one of the listed kinds.', 422)
    return kind


def edit(connection, person_id: str, number: int, given: dict, where: dict, today: date, now) -> None:
    """Rename, redescribe, re-kind or re-age one pet; what it lived through so far stays, the days ahead follow."""
    kind = kind_of(given.get('kind'))

    def update(kept):
        entry = find(kept, number)
        if given.get('name'):
            entry['name'] = ' '.join(given['name'].split())
        if given.get('looks') is not None and given['looks'].strip():
            entry['looks'] = given['looks'].strip()
        if kind and kind != entry['kind']:
            entry['kind'] = kind
            entry['lifespan'] = pets.lifespan_days(f'circle:{person_id}:{entry["n"]}:{kind}', kind)
        if given.get('born'):
            entry['born'] = given['born']
    change(connection, person_id, where, now, update)
    pets.forget_ahead(connection, [f'circle:{person_id}:{number}'], today)


def add(connection, person_id: str, given: dict, where: dict, today: date, now) -> int:
    """A pet the user gives them; its life is lived out from today. Returns its number."""
    kind = kind_of(given.get('kind')) or 'cat'
    added = {}

    def update(kept):
        number = max((entry['n'] for entry in kept), default=-1) + 1
        key = f'circle:{person_id}:{number}'
        born = given.get('born') or pets.draw(key, 'pet', where['era'], today)['details']['born']
        added['n'] = number
        kept.append({'n': number, 'name': ' '.join(given['name'].split()), 'kind': kind,
                     'looks': (given.get('looks') or '').strip() or pets.kind_phrase(kind), 'born': born,
                     'start': today.isoformat(), 'lifespan': pets.lifespan_days(key, kind)})
    change(connection, person_id, where, now, update)
    return added['n']


def remove(connection, person_id: str, number: int, where: dict, now) -> None:
    """They no longer have this pet, and the app does not give it back."""
    change(connection, person_id, where, now, lambda kept: find(kept, number).update(removed=True))
