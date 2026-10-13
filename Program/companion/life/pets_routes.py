"""Pets API: the companion's pets with their lives (companion/life/pets.py), the user's edits to them, and how the
user's own pets (their persona's) are doing. The companion's pets are their home's pet items (companion/life/home.py),
so edits go through the home and come back here."""
from datetime import timedelta

from fastapi import APIRouter, Request
from pydantic import Field

from companion.characters import require_current
from companion.life import home, pets, trips
from companion.models import Input

router = APIRouter(prefix='/api/life/pets')


class PetUpdate(Input):
    name: str | None = Field(default=None, min_length=1, max_length=80, pattern=r'\S')
    looks: str | None = Field(default=None, max_length=300)
    kind: str | None = Field(default=None, max_length=40)
    # Years old, when the user says; else the pet keeps its birth date.
    age: int | None = Field(default=None, ge=0, le=90)


class PetCreate(Input):
    name: str = Field(min_length=1, max_length=80, pattern=r'\S')
    looks: str = Field(default='', max_length=300)
    kind: str = Field(default='cat', max_length=40)
    age: int | None = Field(default=None, ge=0, le=90)


def born(age: int | None, today) -> str | None:
    """A birth date for an age in years the user gave, midway through that year."""
    return None if age is None else (today - timedelta(days=age * 365 + 180)).isoformat()


def away_care(connection, companion: dict, day) -> dict[str, str]:
    """While the companion is away on a trip: each pet's minder in words, by pet name."""
    trip = trips.by_date(connection, companion['active_timeline_id'], day.isoformat()).get(day.isoformat())
    if not trip:
        return {}
    care = trips.pet_care(connection, companion['active_timeline_id'], trip, day)
    return {item['pet']: f"{item['text']} while {companion['version']['name'].split()[0]} is away."
            for item in care if item['text'] and item['how'] != 'along'}


def pets_view(connection, companion: dict, day, now) -> dict:
    timeline_id = companion['active_timeline_id']
    numbers = pets.show_numbers(connection)
    care = away_care(connection, companion, day)
    living = []
    for found in pets.of_home(connection, timeline_id, day):
        shown = pets.view(connection, found, day, numbers)
        if shown['state'] == 'well' and found['name'] in care:
            shown |= {'state': 'away', 'status': care[found['name']]}
        living.append({**shown, 'id': found['item_id'], 'edited': found['edited']})
    gone = [{**pets.view(connection, found, day, numbers), 'id': found['item_id']}
            for found in pets.remembered(connection, timeline_id, day)]
    return {'today': day.isoformat(), 'pets': living, 'remembered': gone,
            'yours': pets.lived(connection, pets.of_persona(connection), day, now),
            'kinds': [{'id': kind, 'label': pets.label(kind)} for kind in pets.offered(connection, timeline_id)], 'numbers': numbers}


def change(request: Request, action=None) -> dict:
    """Run `action(connection, timeline_id, today, now)` on the active timeline's pets, then return them."""
    database, engine = request.app.state.database, request.app.state.life
    now = database.clock.now()
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        timeline_id, version = companion['active_timeline_id'], companion['version']
        today = home.today_for(version, now)
        home.ensure(connection, timeline_id, version['definition'], engine.world, now)
        home.evolve(connection, timeline_id, today, now)
        if action:
            action(connection, timeline_id, today, now)
        pets.evolve_home(connection, timeline_id, today, now)
        return pets_view(connection, companion, today, now)


@router.get('')
def read_pets(request: Request):
    """The companion's pets today, the ones they have lost, and how the user's own pets are."""
    return change(request)


@router.post('')
def add_pet(request: Request, body: PetCreate):
    return change(request, lambda connection, timeline_id, today, now: home.add(
        connection, timeline_id, {'kind': 'pet', 'name': body.name, 'variety': body.kind, 'description': body.looks,
                                  'born': born(body.age, today) or pets.age_from_looks(body.looks, body.kind, today)},
        today, now))


@router.patch('/{item_id}')
def edit_pet(request: Request, item_id: str, body: PetUpdate):
    return change(request, lambda connection, timeline_id, today, now: home.edit(
        connection, timeline_id, item_id, {'name': body.name, 'description': body.looks, 'variety': body.kind,
                                           'born': born(body.age, today) or pets.age_from_looks(body.looks, body.kind, today)},
        today, now))


@router.post('/{item_id}/remove')
def remove_pet(request: Request, item_id: str):
    """They no longer have this pet (rehomed, or the user would rather they never had it)."""
    return change(request, lambda connection, timeline_id, today, now: home.set_removed(
        connection, timeline_id, item_id, True, today, now))


@router.post('/{item_id}/restore')
def restore_pet(request: Request, item_id: str):
    """Bring a pet back, after it was removed or died; one that died is spared from then on."""
    return change(request, lambda connection, timeline_id, today, now: home.set_removed(
        connection, timeline_id, item_id, False, today, now))
