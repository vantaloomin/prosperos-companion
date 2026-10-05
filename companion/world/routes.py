"""World data API: read-only facts about the shipped cities and the generators built on them."""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Query

from companion.world import catalog, generators

router = APIRouter(prefix='/api/world')
Company = Literal['solo', 'friends', 'date', 'family', 'coworkers']
DayPart = Literal['morning', 'afternoon', 'evening', 'late']
Cost = Literal['free', '$', '$$', '$$$', '$$$$']


@router.get('/cities')
def list_cities():
    return [catalog.summary(data) for data in catalog.cities().values()]


@router.get('/careers')
def list_careers():
    return list(catalog.careers().values())


@router.get('/resolve')
def resolve(text: str = Query(max_length=200)):
    return {'match': catalog.resolve(text)}


@router.get('/cities/{city_id}')
def read_city(city_id: str):
    return catalog.city(city_id)


@router.get('/cities/{city_id}/sources')
def read_sources(city_id: str):
    return catalog.sources(catalog.city(city_id))


@router.get('/cities/{city_id}/places')
def list_places(city_id: str, kind: str | None = None, neighborhood: str | None = None, tag: str | None = None,
                good_for: Company | None = None):
    return catalog.places(catalog.city(city_id), kind=kind, neighborhood=neighborhood, tag=tag, good_for=good_for)


@router.get('/cities/{city_id}/conditions')
def read_conditions(city_id: str, day: date, seed: str = ''):
    data = catalog.city(city_id)
    return generators.conditions(data, day, seed) | {'annual_events': generators.annual_events(data, day)}


@router.get('/cities/{city_id}/commute')
def read_commute(city_id: str, origin: str = Query(alias='from'), destination: str = Query(alias='to'),
                 mode: str | None = None):
    return generators.commute(catalog.city(city_id), origin, destination, mode)


@router.get('/cities/{city_id}/generate/outing')
def generate_outing(city_id: str, seed: str, day: date | None = None, day_part: DayPart = 'afternoon',
                    company: Company = 'solo', neighborhood: str | None = None, home: str | None = None,
                    budget: Cost | None = None, kind: list[str] | None = Query(default=None),
                    exclude: list[str] = Query(default=[])):
    return {'outing': generators.outing(catalog.city(city_id), seed=seed, day=day, day_part=day_part,
                                        company=company, neighborhood=neighborhood, home=home, budget=budget,
                                        kinds=kind, exclude=exclude)}


@router.get('/cities/{city_id}/generate/meal')
def generate_meal(city_id: str, seed: str, meal: str = 'dinner', day: date | None = None, company: Company = 'solo',
                  neighborhood: str | None = None, home: str | None = None, budget: Cost | None = None,
                  exclude: list[str] = Query(default=[])):
    return {'outing': generators.meal(catalog.city(city_id), seed=seed, meal=meal, day=day, company=company,
                                      neighborhood=neighborhood, home=home, budget=budget, exclude=exclude)}


@router.get('/cities/{city_id}/generate/job')
def generate_job(city_id: str, career: str, seed: str, home: str | None = None):
    return generators.job(catalog.city(city_id), career, seed=seed, home=home)


@router.get('/cities/{city_id}/generate/home')
def generate_home(city_id: str, seed: str, bedrooms: str = 'one_bedroom', budget: int | None = Query(None, gt=0),
                  vibe: str | None = None, near: str | None = None):
    return generators.home(catalog.city(city_id), seed=seed, bedrooms=bedrooms, budget=budget, vibe=vibe, near=near)
