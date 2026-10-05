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

CITIES = sorted(key for key, value in catalog.cities().items() if value['origin'] == 'builtin')
DERIVED = ('data_version', 'builtin', 'origin', 'pack_file')
SEEDS = [f'seed-{index}' for index in range(60)]


def baltimore():
    return catalog.city('baltimore')


def plain(data):
    """A city as written, without the fields the loader adds."""
    return {key: value for key, value in copy.deepcopy(data).items() if key not in DERIVED}


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
    raw = plain(baltimore())
    City.model_validate(raw)
    raw['places'][0] = raw['places'][0] | {'neighborhood': 'atlantis'}
    with pytest.raises(ValidationError, match='atlantis|neighborhoods'):
        City.model_validate(raw)
    raw = plain(baltimore())
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
    raw = plain(baltimore())
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


def test_private_city_packs_load_from_a_local_folder(client, tmp_path, monkeypatch):
    pack = plain(baltimore()) | {'id': 'harbor-town', 'name': 'Harbor Town', 'aliases': [],
                                  'setting': 'fictional', 'distribution': 'private'}
    (tmp_path / 'harbor-town.json').write_text(json.dumps(pack), encoding='utf-8')
    (tmp_path / 'broken.json').write_text('{"id": "broken"}', encoding='utf-8')
    monkeypatch.setenv(catalog.PACKS_ENV, str(tmp_path))
    try:
        report = client.post('/api/world/packs/reload').json()
        assert [item['id'] for item in report['loaded']] == ['harbor-town']
        assert report['loaded'][0]['distribution'] == 'private' and report['loaded'][0]['origin'] == 'pack'
        assert report['errors'][0]['file'].endswith('broken.json')
        assert client.get('/api/world/cities/harbor-town/generate/job',
                          params={'career': 'teacher', 'seed': 's'}).status_code == 200
        assert client.delete('/api/world/cities/harbor-town').status_code == 409
        assert client.post('/api/world/cities', json=pack).status_code == 409
        copied = client.post('/api/world/cities/harbor-town/copy', json={'id': 'my-harbor', 'name': 'Mine'})
        assert copied.status_code == 200 and copied.json()['origin'] == 'user'
    finally:
        monkeypatch.delenv(catalog.PACKS_ENV)
        catalog.reload()
    assert 'harbor-town' not in catalog.cities()


def test_packs_are_not_committed():
    ignored = (Path(__file__).parent.parent / '.gitignore').read_text(encoding='utf-8')
    assert '/private-cities/' in ignored and catalog.CHECKOUT_PACKS.name == 'private-cities'


def test_small_currency_rents_use_the_whole_range():
    rents = {generators.home(catalog.city('camelot'), seed=seed)['rent'] for seed in SEEDS}
    assert len(rents) > 3


def test_the_world_source_filters_by_time_of_day_and_season():
    from companion.world.source import CatalogWorld
    world = CatalogWorld()
    evening = world.places('baltimore', ['museum', 'attraction'], day_part='evening')
    assert evening and 'National Aquarium' not in {place.name for place in evening}
    winter = world.places('baltimore', ['attraction'], day=date(2026, 1, 15))
    assert 'The Maryland Zoo' not in {place.name for place in winter}
    assert 'The Maryland Zoo' in {place.name for place in world.places('baltimore', ['attraction'],
                                                                        day=date(2026, 6, 15))}


def test_shipped_names_match_their_script_and_every_era_has_a_bank():
    script = Path(__file__).parent.parent / 'scripts' / 'world' / 'names.py'
    written = json.loads((catalog.DATA / 'names.json').read_text(encoding='utf-8'))
    assert runpy.run_path(str(script))['NAMES'] == written, 'Rerun the script.'
    for city_id in CITIES:
        groups, mix = catalog.name_groups(catalog.city(city_id))
        assert mix and set(mix) <= set(groups)


@pytest.mark.parametrize('city_id', CITIES)
def test_circles_are_deterministic_and_coherent(city_id):
    data = catalog.city(city_id)
    hood = data['neighborhoods'][0]['id']
    employer = data['employers'][0]['id'] if data['employers'] else None
    for seed in SEEDS[:8]:
        result = generators.circle(data, seed=seed, size=12, home=hood, age=30, employer=employer)
        assert result == generators.circle(data, seed=seed, size=12, home=hood, age=30, employer=employer)
        people = result['people']
        assert len(people) == 12 and len({person['name']['full'] for person in people}) == 12
        assert len({person['id'] for person in people}) == 12
        for person in people:
            if person['role'] in ('parent', 'sibling'):
                assert person['name']['family'] == result['family']
                assert person['name']['group'] == people[2]['name']['group']
            if person['role'] == 'neighbor':
                assert person['home']['neighborhood']['id'] == hood
            if person['role'] == 'coworker' and employer:
                assert person['job']['employer']['id'] == employer
            if person['role'] == 'parent':
                assert person['age'] >= 30 + 24
            if person['local'] and person['schedule']:
                CharacterDefinition(name=person['name']['given'], schedule=person['schedule'])
            assert len(person['haunts']) <= 3
        assert result['refs'] and result['sources']


def test_residents_follow_their_arguments():
    data = baltimore()
    nurse = generators.resident(data, seed='n', career='registered-nurse', age=41, near='canton')
    assert nurse['job']['career']['id'] == 'registered-nurse' and nurse['age'] == 41
    assert nurse['job']['commute']['from'] == nurse['home']['neighborhood']['id']
    retired = generators.resident(data, seed='r', age=72)
    assert retired['job'] is None and retired['schedule'] == generators.RETIRED_SCHEDULE
    away = generators.resident(data, seed='a', role='parent', local=False, family='Okafor')
    assert away['home'] is None and away['name']['family'] == 'Okafor'
    student = generators.resident(data, seed='s', career='undergraduate')
    assert 18 <= student['age'] <= 22 and student['job']['employer']['fit'] == 'college'
    with pytest.raises(DomainError):
        generators.resident(data, seed='x', role='rival')
    with pytest.raises(DomainError):
        generators.resident(data, seed='x', employer='atlantis')


def test_names_follow_the_city_bank_and_its_own_groups():
    miami = catalog.city('miami')
    groups = [generators.name(miami, seed=seed)['group'] for seed in SEEDS]
    assert groups.count('hispanic') > len(SEEDS) / 3
    whitlock = catalog.city('whitlock')
    assert all(generators.name(whitlock, seed=seed)['group'] in catalog.names()['banks']['frontier'] for seed in SEEDS)
    raw = plain(baltimore()) | {'names': {'groups': {'harbor': {'feminine': ['Wren'], 'family': ['Tidewell']}}}}
    custom = catalog.prepare(raw)
    assert {generators.name(custom, seed=seed)['full'] for seed in SEEDS[:5]} == {'Wren Tidewell'}
    with pytest.raises(ValueError):
        catalog.prepare(plain(baltimore()) | {'names': {'bank': 'atlantis'}})


def test_people_api(client):
    circle = client.get('/api/world/cities/baltimore/generate/circle',
                        params={'seed': 's', 'size': 4, 'home': 'canton', 'age': 31, 'career': 'teacher'}).json()
    assert [person['role'] for person in circle['people']] == ['close-friend', 'coworker', 'sibling', 'friend']
    assert circle['people'][1]['job']['career']['id'] == 'teacher'
    person = client.get('/api/world/cities/whitlock/generate/resident', params={'seed': 's', 'role': 'mentor'})
    assert person.status_code == 200 and person.json()['role'] == 'mentor'
    assert client.get('/api/world/cities/baltimore/generate/circle', params={'seed': 's', 'size': 40}).status_code == 422
    assert 'modern' in client.get('/api/world/names').json()['banks']


def test_a_circle_spreads_across_workplaces():
    data = baltimore()
    for seed in SEEDS[:30]:
        people = generators.circle(data, seed=seed, size=6, home='fells-point')['people']
        employers = [person['job']['employer']['id'] for person in people
                     if person['job'] and person['job']['employer']['id']]
        assert all(employers.count(item) <= 2 for item in employers)


def test_shipped_holidays_match_their_script():
    script = Path(__file__).parent.parent / 'scripts' / 'world' / 'holidays.py'
    written = json.loads((catalog.DATA / 'holidays.json').read_text(encoding='utf-8'))
    assert runpy.run_path(str(script))['HOLIDAYS'] == written, 'Rerun the script.'


def test_holiday_dates():
    assert [generators.easter(year) for year in (1895, 2000, 2024, 2026, 2038)] == [
        date(1895, 4, 14), date(2000, 4, 23), date(2024, 3, 31), date(2026, 4, 5), date(2038, 4, 25)]
    year = {item['id']: item['date'] for item in generators.holidays(baltimore(), date(2026, 1, 1), date(2026, 12, 31))}
    assert year['thanksgiving'] == '2026-11-26' and year['memorial-day'] == '2026-05-25'
    assert year['labor-day'] == '2026-09-07' and year['mlk-day'] == '2026-01-19'
    london = generators.holidays(catalog.city('london-1895'), date(1895, 4, 12), date(1895, 4, 15))
    assert [item['id'] for item in london] == ['good-friday', 'easter', 'easter-monday']
    assert [item['id'] for item in generators.holidays(baltimore(), date(2026, 7, 4))] == ['independence-day']
    assert generators.holidays(catalog.city('emerald-city'), date(2026, 12, 25)) == []
    span = generators.holidays(baltimore(), date(2026, 12, 20), date(2027, 1, 2))
    assert [item['id'] for item in span] == ['christmas-eve', 'christmas', 'new-years-eve', 'new-years-day']
    with pytest.raises(DomainError):
        generators.holidays(baltimore(), date(2026, 1, 1), date(2028, 1, 1))


def test_cities_choose_and_add_holidays():
    assert {city: catalog.calendar_id(catalog.city(city)) for city in ('whitlock', 'calderwick', 'camelot')} == {
        'whitlock': 'us-1880s', 'calderwick': 'uk-victorian', 'camelot': 'medieval-england'}
    own = {'id': 'harbor-day', 'name': 'Harbor Day', 'kind': 'observance', 'month': 6, 'weekday': 5, 'nth': 1,
           'summary': 'Boats parade.'}
    custom = catalog.prepare(plain(baltimore()) | {'calendar': 'none', 'holidays': [own]})
    assert [item['date'] for item in generators.holidays(custom, date(2026, 1, 1), date(2026, 12, 31))] == ['2026-06-06']
    with pytest.raises(ValueError):
        catalog.prepare(plain(baltimore()) | {'calendar': 'atlantis'})
    with pytest.raises(ValidationError):
        catalog.prepare(plain(baltimore()) | {'holidays': [own | {'day': 3}]})


def test_holiday_api(client):
    result = client.get('/api/world/cities/baltimore/holidays', params={'start': '2026-11-01', 'end': '2026-11-30'})
    assert result.json()['calendar'] == 'us'
    assert [item['id'] for item in result.json()['holidays']] == ['veterans-day', 'thanksgiving']
    day = client.get('/api/world/cities/baltimore/conditions', params={'day': '2026-11-26'}).json()
    assert day['holidays'][0]['id'] == 'thanksgiving'


def test_local_color_is_seeded_and_seasonal():
    item = {'id': 'soft-shells', 'name': 'Soft-shell crabs', 'kind': 'dish', 'summary': 'Fried whole.',
            'places': ['fells-point'], 'seasons': ['summer'], 'source': plain(baltimore())['places'][0]['source']}
    other = item | {'id': 'hon', 'name': 'Hon', 'kind': 'saying', 'summary': 'Dear.', 'places': [], 'seasons': []}
    data = catalog.prepare(plain(baltimore()) | {'local_color': [item, other]})
    winter = generators.local_color(data, seed='s', day=date(2026, 1, 10), count=5)
    assert [entry['id'] for entry in winter] == ['hon']
    summer = generators.local_color(data, seed='s', day=date(2026, 7, 10), count=5)
    assert {entry['id'] for entry in summer} == {'hon', 'soft-shells'}
    assert generators.local_color(data, seed='s', kinds=['dish']) == [item]
    assert any(line.startswith('Local saying: Hon') for line in generators.facts(data))
    with pytest.raises(ValidationError, match='unknown places'):
        catalog.prepare(plain(baltimore()) | {'local_color': [item | {'places': ['atlantis']}]})


def test_generator_results_do_not_share_cached_data():
    data = baltimore()
    outing = generators.outing(data, seed='s')
    outing['place']['name'] = 'Changed'
    job = generators.job(data, 'teacher', seed='s')
    job['career']['name'] = 'Changed'
    assert all(place['name'] != 'Changed' for place in catalog.city('baltimore')['places'])
    assert catalog.careers_for(catalog.city('baltimore'))['teacher']['name'] != 'Changed'
