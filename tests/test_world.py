import copy
import json
import runpy
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from companion.errors import DomainError
from companion.models import CharacterDefinition
from companion.world import catalog, generators
from companion.world.schema import City

CITIES = sorted(catalog.cities())
SEEDS = [f'seed-{index}' for index in range(60)]


def baltimore():
    return catalog.city('baltimore')


@pytest.mark.parametrize('city_id', CITIES)
def test_every_shipped_city_validates_and_cites_its_sources(city_id):
    data = catalog.city(city_id)
    assert data['country'] and data['data_version']
    for source in catalog.sources(data):
        assert source['license'] and source['retrieved']
    for career in catalog.careers_for(data):
        result = generators.job(data, career, seed=career)
        assert result['employer']['name'] and result['refs'] and result['sources']


@pytest.mark.parametrize('city_id', CITIES)
def test_generated_schedules_are_valid_character_routines(city_id):
    data = catalog.city(city_id)
    for career in catalog.careers_for(data):
        blocks = generators.job(data, career, seed=career)['schedule']
        CharacterDefinition(name='Mira', schedule=blocks)


@pytest.mark.parametrize('city_id', CITIES)
def test_shipped_json_matches_its_source_script(city_id):
    script = Path(__file__).parent.parent / 'scripts' / 'world' / f'{city_id.replace("-", "_")}.py'
    written = json.loads((catalog.DATA / 'cities' / f'{city_id}.json').read_text(encoding='utf-8'))
    assert runpy.run_path(str(script))['CITY'] == json.loads(json.dumps(written)), 'Rerun the script.'


def test_validation_rejects_broken_references():
    raw = copy.deepcopy(baltimore())
    raw.pop('data_version'), raw.pop('builtin')
    City.model_validate(raw)
    raw['places'][0] = raw['places'][0] | {'neighborhood': 'atlantis'}
    with pytest.raises(ValidationError, match='atlantis|neighborhoods'):
        City.model_validate(raw)
    raw = copy.deepcopy(baltimore())
    raw.pop('data_version'), raw.pop('builtin')
    raw['colleges'][0] = raw['colleges'][0] | {'source': 'made-up'}
    with pytest.raises(ValidationError, match='sources'):
        City.model_validate(raw)


def test_choices_are_stable_across_runs_and_python_versions():
    assert generators.unit('slot', 'outing') == generators.unit('slot', 'outing')
    assert round(generators.unit('stable', 'check'), 12) == 0.380102014478
    first = generators.outing(baltimore(), seed='evening@2026-10-04', day=date(2026, 10, 4), neighborhood='canton')
    again = generators.outing(baltimore(), seed='evening@2026-10-04', day=date(2026, 10, 4), neighborhood='canton')
    assert first == again


def test_outings_follow_constraints_and_prefer_the_neighborhood():
    data = baltimore()
    nearby = 0
    for seed in SEEDS:
        result = generators.outing(data, seed=seed, day_part='evening', company='date', neighborhood='fells-point',
                                   budget='$$', exclude=['berthas'])
        place = result['place']
        assert 'evening' in place['day_parts'] and 'date' in place['good_for']
        assert generators.COSTS.index(place['cost']) <= 2 and place['id'] != 'berthas'
        assert result['travel']['from'] == 'fells-point'
        nearby += result['travel']['distance_km'] <= 3
    assert nearby > len(SEEDS) / 2


def test_bad_weather_favours_indoor_places_and_seasons_are_respected():
    data = baltimore()
    winter = [generators.outing(data, seed=seed, day=date(2026, 1, 20)) for seed in SEEDS]
    assert all('winter' in r['place']['seasons'] or not r['place']['seasons'] for r in winter)
    july = [generators.outing(data, seed=seed, day=date(2026, 7, 15)) for seed in SEEDS]
    wet = [r for r in july if r['weather']['rain']]
    if wet:
        assert sum(r['place']['setting'] == 'outdoor' for r in wet) < len(wet) / 2


def test_meals_pick_food_places_for_the_time_of_day():
    for seed in SEEDS[:20]:
        result = generators.meal(baltimore(), seed=seed, meal='breakfast')
        assert result['place']['kind'] in generators.FOOD and result['meal'] == 'breakfast'


def test_commutes_choose_a_sensible_mode():
    data = baltimore()
    assert generators.commute(data, 'harbor-east', 'little-italy')['mode'] == 'walk'
    rail = generators.commute(data, 'mount-vernon', 'station-north')
    assert rail['mode'] == 'light-rail' and rail['line'] == 'Light RailLink'
    far = generators.commute(data, 'towson', 'inner-harbor')
    assert far['mode'] == 'car' and 20 <= far['minutes'] <= 90


def test_jobs_use_real_employers_and_fall_back_without_inventing_names():
    data = baltimore()
    nurse = generators.job(data, 'registered-nurse', seed='a', home='canton')
    assert nurse['employer']['named'] and nurse['employer']['fit'] == 'employer'
    assert nurse['commute']['from'] == 'canton'
    student = generators.job(data, 'undergraduate', seed='a')
    assert student['employer']['fit'] == 'college' and student['schedule'][0]['kind'] == 'study'
    barista = generators.job(data, 'barista', seed='a')
    assert barista['employer']['fit'] == 'workplace'
    assert catalog.find(data, barista['employer']['id'])['kind'] in {'cafe', 'market'}


def test_homes_stay_within_budget_and_typical_ranges():
    data = baltimore()
    for seed in SEEDS:
        result = generators.home(data, seed=seed, bedrooms='one_bedroom', budget=1400)
        low, high = result['neighborhood']['rent']['one_bedroom']
        assert low <= result['rent'] <= min(high, 1400) and result['rent'] % 25 == 0


def test_free_text_locations_resolve_to_cities_and_neighborhoods():
    assert catalog.resolve('Fells Point, Baltimore') == {'city': 'baltimore', 'neighborhood': 'fells-point'}
    assert catalog.resolve('Charm City') == {'city': 'baltimore', 'neighborhood': None}
    assert catalog.resolve('Lisbon') is None
    assert catalog.resolve('') is None


def test_world_api(client):
    cities = client.get('/api/world/cities').json()
    assert 'baltimore' in {city['id'] for city in cities}
    assert client.get('/api/world/cities/atlantis').status_code == 404
    places = client.get('/api/world/cities/baltimore/places', params={'kind': 'museum'}).json()
    assert places and all(place['kind'] == 'museum' for place in places)
    outing = client.get('/api/world/cities/baltimore/generate/outing',
                        params={'seed': 's', 'day': '2026-10-04', 'neighborhood': 'hampden', 'company': 'friends'})
    assert outing.status_code == 200 and outing.json()['outing']['company'] == 'friends'
    job = client.get('/api/world/cities/baltimore/generate/job', params={'career': 'teacher', 'seed': 's'}).json()
    assert job['schedule'][0]['key'] == 'work'
    commute = client.get('/api/world/cities/baltimore/commute', params={'from': 'canton', 'to': 'towson'})
    assert commute.status_code == 200 and commute.json()['mode']
    assert client.get('/api/world/resolve', params={'text': 'Hampden, Baltimore'}).json()['match'] == {
        'city': 'baltimore', 'neighborhood': 'hampden'}


def test_a_generated_schedule_drives_the_life_routine(client):
    job = client.get('/api/world/cities/baltimore/generate/job', params={'career': 'barista', 'seed': 'm'}).json()
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'America/New_York',
                                                     'location': 'Hampden, Baltimore', 'schedule': job['schedule']})
    assert response.status_code == 200, response.text
    routine = client.get('/api/life/routine').json()
    assert not routine['default_schedule'] and {block['key'] for block in routine['blocks']} >= {'work', 'sleep'}


def test_the_catalog_answers_the_life_composer(app):
    from companion.world.source import CatalogWorld
    assert isinstance(app.state.life.world, CatalogWorld)
    world = CatalogWorld()
    waterfront = world.places('baltimore', ['waterfront'])
    assert waterfront and all(place.kind == 'waterfront' and place.city == 'Baltimore' for place in waterfront)
    assert world.places('Fells Point, Baltimore', ['cafe', 'bar'])
    colleges = world.places('baltimore', ['college'])
    assert {'Johns Hopkins University'} <= {place.name for place in colleges}
    assert world.places('atlantis', ['cafe']) == []
    assert world.places('baltimore', ['cafe']) == world.places('baltimore', ['cafe'])


def test_users_build_their_own_cities(client):
    template = client.get('/api/world/template').json()
    assert client.post('/api/world/validate', json=template).json()['valid']
    broken = template | {'places': [template['places'][0] | {'neighborhood': 'nowhere'}]}
    response = client.post('/api/world/validate', json=broken)
    assert response.status_code == 422 and 'nowhere' in response.json()['detail']
    city = template | {'id': 'port-calloway', 'name': 'Port Calloway', 'aliases': ['Calloway']}
    created = client.post('/api/world/cities', json=city)
    assert created.status_code == 200, created.text
    assert created.json()['revision'] == 1 and not created.json()['builtin']
    assert client.post('/api/world/cities', json=city).status_code == 409
    assert client.post('/api/world/cities', json=template | {'id': 'baltimore'}).status_code == 409
    listed = {item['id']: item for item in client.get('/api/world/cities').json()}
    assert listed['port-calloway']['builtin'] is False and listed['baltimore']['builtin'] is True

    job = client.get('/api/world/cities/port-calloway/generate/job', params={'career': 'barista', 'seed': 's'})
    assert job.status_code == 200 and job.json()['neighborhood']['id'] == 'old-town'
    outing = client.get('/api/world/cities/port-calloway/generate/outing', params={'seed': 's', 'day': '2026-10-04'})
    assert outing.json()['outing']['place']['id'] == 'corner-cafe' and outing.json()['outing']['weather'] is None
    home = client.get('/api/world/cities/port-calloway/generate/home', params={'seed': 's'}).json()
    assert home['neighborhood']['id'] == 'old-town' and home['rent'] is None
    assert client.get('/api/world/resolve', params={'text': 'Calloway'}).json()['match']['city'] == 'port-calloway'

    edited = city | {'summary': 'A foggy harbour town.'}
    stale = client.put('/api/world/cities/port-calloway', json={'definition': edited, 'expected_revision': 2})
    assert stale.status_code == 409
    updated = client.put('/api/world/cities/port-calloway', json={'definition': edited, 'expected_revision': 1})
    assert updated.json()['summary'] == 'A foggy harbour town.' and updated.json()['revision'] == 2
    assert client.put('/api/world/cities/baltimore', json={'definition': edited, 'expected_revision': 1}
                      ).status_code == 409


def test_copying_a_built_in_city_and_living_in_a_user_city(app, client):
    copied = client.post('/api/world/cities/baltimore/copy', json={'id': 'my-baltimore', 'name': 'My Baltimore'})
    assert copied.status_code == 200, copied.text
    assert len(copied.json()['places']) == len(baltimore()['places']) and copied.json()['aliases'] == []
    client.post('/api/companion', json={'name': 'Mira', 'timezone': 'America/New_York', 'home_city': 'my-baltimore'})
    assert app.state.life.world.places('my-baltimore', ['cafe'])
    blocked = client.delete('/api/world/cities/my-baltimore')
    assert blocked.status_code == 409
    assert client.delete('/api/world/cities/baltimore').status_code == 409
    client.post('/api/world/cities/baltimore/copy', json={'id': 'spare', 'name': 'Spare'})
    assert client.delete('/api/world/cities/spare').json() == {'deleted': 'spare'}
    assert client.get('/api/world/cities/spare').status_code == 404


def test_settings_without_money_or_climate_still_generate():
    raw = copy.deepcopy(baltimore())
    for key in ('data_version', 'builtin'):
        raw.pop(key)
    raw |= {'id': 'storybook', 'setting': 'original', 'era': 'fantasy', 'climate': None, 'employers': [],
            'career_hubs': [], 'speeds': {'walk': 4.5, 'horse': 12},
            'careers': [{'id': 'baker-fantasy', 'name': 'Baker', 'sector': 'food', 'schedule': 'early', 'pay': '$',
                         'summary': 'Bakes bread before dawn.', 'themes': ['bread'], 'eras': ['fantasy']}],
            'neighborhoods': [hood | {'rent': None} for hood in raw['neighborhoods']]}
    data = catalog.prepare(raw)
    assert set(catalog.careers_for(data)) == {'baker-fantasy'}
    assert generators.job(data, 'baker-fantasy', seed='x')['employer']['fit'] == 'workplace'
    assert generators.home(data, seed='x', budget=10)['rent'] is None
    assert generators.commute(data, 'towson', 'inner-harbor')['mode'] == 'horse'
    assert generators.conditions(data, date(2026, 1, 1)) is None
    with pytest.raises(DomainError):
        generators.job(data, 'software-engineer', seed='x')
