"""World data API: the built-in and user cities, the generators built on them, and the city builder."""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Query, Request
from pydantic import Field

from companion.models import Input
from companion.world import catalog, custom, generators

router = APIRouter(prefix='/api/world')
Company = Literal['solo', 'friends', 'date', 'family', 'coworkers']
DayPart = Literal['morning', 'afternoon', 'evening', 'late']
Cost = Literal['free', '$', '$$', '$$$', '$$$$']


class CityRevision(Input):
    definition: dict
    expected_revision: int = Field(ge=1)


class CityCopy(Input):
    id: str = Field(pattern=r'^[a-z0-9]+(-[a-z0-9]+)*$', max_length=80)
    name: str = Field(min_length=1, max_length=400)


def user_cities(request: Request) -> dict[str, dict]:
    return custom.read(request.app.state.database)


def city(request: Request, city_id: str) -> dict:
    return catalog.city(city_id, user_cities(request))


@router.get('/cities')
def list_cities(request: Request):
    return [catalog.summary(data) for data in [*catalog.cities().values(), *user_cities(request).values()]]


@router.get('/careers')
def list_careers():
    return list(catalog.careers().values())


@router.get('/resolve')
def resolve(request: Request, text: str = Query(max_length=200)):
    return {'match': catalog.resolve(text, user_cities(request))}


@router.get('/packs')
def read_packs():
    return catalog.packs()


@router.post('/packs/reload')
def reload_packs():
    return catalog.reload()


@router.get('/template')
def read_template(request: Request):
    return custom.template(request.app.state.database.now()[:10])


@router.post('/validate')
def validate(definition: dict):
    data = custom.check(definition)
    return {'valid': True, 'data_version': data['data_version'], 'summary': catalog.summary(data)}


@router.post('/cities')
def create_city(request: Request, definition: dict):
    return custom.create(request.app.state.database, definition)


@router.get('/cities/{city_id}')
def read_city(request: Request, city_id: str):
    return city(request, city_id)


@router.put('/cities/{city_id}')
def update_city(request: Request, city_id: str, body: CityRevision):
    return custom.update(request.app.state.database, city_id, body.definition, body.expected_revision)


@router.delete('/cities/{city_id}')
def delete_city(request: Request, city_id: str):
    custom.delete(request.app.state.database, city_id)
    return {'deleted': city_id}


@router.post('/cities/{city_id}/copy')
def copy_city(request: Request, city_id: str, body: CityCopy):
    return custom.copy(request.app.state.database, city_id, body.id, body.name)


@router.get('/cities/{city_id}/careers')
def list_city_careers(request: Request, city_id: str):
    return list(catalog.careers_for(city(request, city_id)).values())


@router.get('/cities/{city_id}/sources')
def read_sources(request: Request, city_id: str):
    return catalog.sources(city(request, city_id))


@router.get('/cities/{city_id}/places')
def list_places(request: Request, city_id: str, kind: str | None = None, neighborhood: str | None = None,
                tag: str | None = None, good_for: Company | None = None):
    return catalog.places(city(request, city_id), kind=kind, neighborhood=neighborhood, tag=tag, good_for=good_for)


@router.get('/cities/{city_id}/conditions')
def read_conditions(request: Request, city_id: str, day: date, seed: str = ''):
    data = city(request, city_id)
    return {'conditions': generators.conditions(data, day, seed), 'annual_events': generators.annual_events(data, day),
            'holidays': generators.holidays(data, day)}


@router.get('/cities/{city_id}/holidays')
def list_holidays(request: Request, city_id: str, start: date, end: date | None = None):
    return {'calendar': catalog.calendar_id(city(request, city_id)),
            'holidays': generators.holidays(city(request, city_id), start, end)}


@router.get('/cities/{city_id}/commute')
def read_commute(request: Request, city_id: str, origin: str = Query(alias='from'),
                 destination: str = Query(alias='to'), mode: str | None = None):
    return generators.commute(city(request, city_id), origin, destination, mode)


@router.get('/cities/{city_id}/generate/outing')
def generate_outing(request: Request, city_id: str, seed: str, day: date | None = None,
                    day_part: DayPart = 'afternoon', company: Company = 'solo', neighborhood: str | None = None,
                    home: str | None = None, budget: Cost | None = None, kind: list[str] | None = Query(default=None),
                    exclude: list[str] = Query(default=[])):
    return {'outing': generators.outing(city(request, city_id), seed=seed, day=day, day_part=day_part,
                                        company=company, neighborhood=neighborhood, home=home, budget=budget,
                                        kinds=kind, exclude=exclude)}


@router.get('/cities/{city_id}/generate/meal')
def generate_meal(request: Request, city_id: str, seed: str, meal: str = 'dinner', day: date | None = None,
                  company: Company = 'solo', neighborhood: str | None = None, home: str | None = None,
                  budget: Cost | None = None, exclude: list[str] = Query(default=[])):
    return {'outing': generators.meal(city(request, city_id), seed=seed, meal=meal, day=day, company=company,
                                      neighborhood=neighborhood, home=home, budget=budget, exclude=exclude)}


@router.get('/cities/{city_id}/generate/job')
def generate_job(request: Request, city_id: str, career: str, seed: str, home: str | None = None):
    return generators.job(city(request, city_id), career, seed=seed, home=home)


@router.get('/cities/{city_id}/generate/home')
def generate_home(request: Request, city_id: str, seed: str, bedrooms: str = 'one_bedroom',
                  budget: int | None = Query(None, gt=0), vibe: str | None = None, near: str | None = None):
    return generators.home(city(request, city_id), seed=seed, bedrooms=bedrooms, budget=budget, vibe=vibe,
                           near=near)


Role = Literal['close-friend', 'friend', 'coworker', 'neighbor', 'old-classmate', 'mentor', 'sibling', 'parent',
               'cousin']


@router.get('/cities/{city_id}/generate/resident')
def generate_resident(request: Request, city_id: str, seed: str, role: Role = 'friend', career: str | None = None,
                      age: int | None = Query(None, ge=16, le=100), near: str | None = None,
                      employer: str | None = None, family: str | None = None, group: str | None = None,
                      local: bool = True):
    return generators.resident(city(request, city_id), seed=seed, role=role, career=career, age=age, near=near,
                               employer=employer, family=family, group=group, local=local)


@router.get('/cities/{city_id}/generate/circle')
def generate_circle(request: Request, city_id: str, seed: str, size: int = Query(6, ge=1, le=12),
                    home: str | None = None, age: int | None = Query(None, ge=16, le=100),
                    career: str | None = None, employer: str | None = None, family: str | None = None,
                    group: str | None = None):
    return generators.circle(city(request, city_id), seed=seed, size=size, home=home, age=age, career=career,
                             employer=employer, family=family, group=group)


@router.get('/names')
def read_names():
    return catalog.names()
