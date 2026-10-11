"""Every era is wired end to end, and the modern calendars of other countries keep their own holidays."""
import copy
from datetime import date

import pytest
from pydantic import ValidationError

from companion import dating as dating_app
from companion.life import home, money, wardrobe
from companion.world import catalog, changes, dating, generators, naming, townsfolk
from companion.world.schema import Era, Holiday

ERAS = Era.__args__
# Eras without birth-year name lists: their banks' own names are used.
NO_BIRTH_YEARS = {'medieval', 'fantasy'}


def city_as(era: str, country: str = 'United States', **extra) -> dict:
    data = {key: value for key, value in copy.deepcopy(catalog.city('baltimore')).items()
            if key not in ('data_version', 'builtin', 'origin', 'pack_file')}
    # Baltimore's employers hire for today's careers only.
    employers = data['employers'] if era == 'modern' else []
    return catalog.prepare(data | {'era': era, 'country': country, 'names': None, 'employers': employers} | extra)


def on(data: dict, year: int) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for item in generators.holidays(data, date(year, 1, 1), date(year, 12, 31)):
        found.setdefault(item['id'], []).append(item['date'])
    return {key: value[0] if len(value) == 1 else value for key, value in found.items()}


@pytest.mark.parametrize('era', ERAS)
def test_every_era_has_names_a_change_style_and_a_year(era):
    assert era in catalog.names()['eras']
    assert changes.bank()['eras'][era] in changes.bank()['styles']
    assert (era in naming.data()['era_years']) == (era not in NO_BIRTH_YEARS)


def test_jazz_age_is_another_era_with_its_own_careers_names_and_calendar():
    data = city_as('jazz-age')
    assert catalog.category(data | {'origin': 'builtin'}) == 'other-eras'
    assert catalog.calendar_id(data) == 'us-1920s' and catalog.calendar_id(city_as('jazz-age', 'France')) is None
    offered = catalog.careers_for(data, needs_met=False)
    assert len([key for key, career in offered.items() if career['eras'] == ['jazz-age']]) >= 30
    assert {'switchboard-operator', 'speakeasy-bartender', 'teacher', 'journalist'} <= set(offered)
    assert 'software-engineer' not in offered
    assert naming.present_year(data) == 1926
    groups = {generators.name(data, seed=f'jazz-{index}', age=40)['group'] for index in range(200)}
    assert {'anglo', 'irish', 'german', 'italian'} <= groups
    year = on(data, 1926)
    assert year['thanksgiving'] == '1926-11-25' and year['armistice-day'] == '1926-11-11'
    assert year['decoration-day'] == '1926-05-30' and 'juneteenth' not in year


def test_jazz_age_townsfolk_have_period_jobs_and_looks():
    data = city_as('jazz-age')
    people = [sheet for place in data['places'] for sheet in townsfolk.at_place(data, place['id'])]
    roles = {sheet['role'] for sheet in people}
    assert 'barista' not in roles and 'DJ' not in roles and 'fiddler' not in roles
    assert roles & {'soda jerk', 'bandleader', 'barkeep', 'salesclerk', 'short-order cook'}
    occupations = {sheet['occupation'] for sheet in people if not sheet['staff']}
    jazz = {career['name'].lower() for career in catalog.careers_for(data).values()} | {'retired'}
    assert occupations <= jazz
    assert dating_app.surface(data) == 'column'
    styles = {dating.looks(sheet, data)['style'] for sheet in people}
    assert styles <= set(dating.STYLES['jazz-age'])
    goal = townsfolk.goal(people[0] | {'goals': ['band']}, data, 0)
    assert goal['text'] == townsfolk.ERA_GOALS['jazz-age']['band']


def test_jazz_age_homes_wardrobes_and_money_belong_to_the_1920s():
    data = city_as('jazz-age')
    vehicles = {(home.vehicle_item(f'v{index}', data) or {}).get('variety') for index in range(80)}
    assert vehicles <= {'motorcar', 'bicycle', None} and 'motorcar' in vehicles
    found = {'era': 'jazz-age'}
    assert wardrobe.catalog_for(found) is wardrobe.ERA_PIECES['jazz-age']
    assert money.era_of(data) == 'jazz-age' and money.era_of(city_as('victorian')) == 'other'


def test_modern_cities_abroad_keep_their_countrys_calendar():
    expected = {'United Kingdom': 'uk', 'England': 'uk', 'South Korea': 'south-korea', 'Japan': 'japan',
                'United States': 'us', 'France': None}
    assert {country: catalog.calendar_id(city_as('modern', country)) for country in expected} == expected
    assert catalog.calendar_id(city_as('modern', 'Japan', calendar='uk')) == 'uk'


def test_uk_bank_holidays():
    year = on(city_as('modern', 'United Kingdom'), 2026)
    assert year['good-friday'] == '2026-04-03' and year['easter-monday'] == '2026-04-06'
    assert year['early-may-bank-holiday'] == '2026-05-04' and year['spring-bank-holiday'] == '2026-05-25'
    assert year['summer-bank-holiday'] == '2026-08-31' and year['boxing-day'] == '2026-12-26'
    assert year['pancake-day'] == '2026-02-17' and year['mothering-sunday'] == '2026-03-15'
    assert year['remembrance-sunday'] == '2026-11-08' and year['bonfire-night'] == '2026-11-05'
    assert 'thanksgiving' not in year


def test_korean_lunar_holidays_follow_their_table():
    data = city_as('modern', 'South Korea')
    year = on(data, 2026)
    assert [year['seollal-eve'], year['seollal'], year['seollal-after']] == ['2026-02-16', '2026-02-17', '2026-02-18']
    assert [year['chuseok-eve'], year['chuseok'], year['chuseok-after']] == ['2026-09-24', '2026-09-25', '2026-09-26']
    assert year['buddhas-birthday'] == '2026-05-24' and year['hangul-day'] == '2026-10-09'
    # Korea counts the new moon in Korean time, so 2027's Seollal is the day after Chinese New Year.
    assert on(data, 2027)['seollal'] == '2027-02-07' and on(data, 2028)['seollal'] == '2028-01-27'
    for year_number in range(2026, 2036):
        assert {'seollal', 'chuseok', 'buddhas-birthday'} <= set(on(data, year_number))
    # A year beyond the table has no lunar holidays rather than wrong ones.
    assert 'seollal' not in on(data, 2041) and 'samiljeol' in on(data, 2041)


def test_japanese_holidays_with_happy_mondays_and_equinoxes():
    data = city_as('modern', 'Japan')
    year = on(data, 2026)
    assert year['coming-of-age-day'] == '2026-01-12' and year['marine-day'] == '2026-07-20'
    assert year['respect-for-the-aged-day'] == '2026-09-21' and year['sports-day'] == '2026-10-12'
    assert year['vernal-equinox-day'] == '2026-03-20' and year['autumnal-equinox-day'] == '2026-09-23'
    assert year['citizens-holiday'] == '2026-09-22'
    assert 'citizens-holiday' not in on(data, 2027)
    assert on(data, 2027)['vernal-equinox-day'] == '2027-03-21' and on(data, 2024)['autumnal-equinox-day'] == \
        '2024-09-22'
    assert {'showa-day', 'constitution-memorial-day', 'greenery-day', 'childrens-day', 'obon', 'tanabata',
            'shichi-go-san', 'christmas-eve'} <= set(year)


def test_a_holiday_by_table_of_dates():
    rule = {'id': 'lantern-night', 'name': 'Lantern night', 'kind': 'observance', 'summary': 'Lanterns.'}
    holiday = Holiday.model_validate(rule | {'dates': {'2026': '02-17', '2027': '02-06'}}).model_dump()
    assert generators.holiday_date(holiday, 2026) == date(2026, 2, 17)
    assert generators.holiday_date(holiday, 2028) is None
    for wrong in ({'dates': {'2026': '2-17'}}, {'dates': {'26': '02-17'}}, {'dates': {}},
                  {'dates': {'2026': '02-17'}, 'month': 2, 'day': 17}, {'dates': {'2026': '02-17'}, 'easter': 1}):
        with pytest.raises(ValidationError):
            Holiday.model_validate(rule | wrong)
    own = city_as('modern', calendar='none', holidays=[rule | {'dates': {'2026': '06-06'}}])
    assert [item['date'] for item in generators.holidays(own, date(2026, 6, 1), date(2026, 6, 30))] == ['2026-06-06']


def test_won_and_yen_read_as_people_write_them():
    won = {'code': 'KRW', 'symbol': '₩', 'name': 'South Korean won'}
    yen = {'code': 'JPY', 'symbol': '¥', 'name': 'Japanese yen'}
    assert money.amount(1_234_567, won) == '₩1,235,000' and money.amount(850_400, won) == '₩850,000'
    assert money.amount(68_432, yen) == '¥68,430' and money.amount(4.4, yen) == '¥4'
    assert money.amount(4.4, {'code': 'USD', 'symbol': '$', 'name': 'US dollars'}) == '$4.4'
    assert generators.figure(1_200_000) == '1,200,000' and generators.figure(4.5) == '4.5'
    assert generators.rent_step(650_000) == 1000 and generators.rent_step(1900) == 25
    data = city_as('modern', 'South Korea', currency=won,
                   prices=[{'id': 'coffee', 'item': 'Coffee', 'low': 4500, 'high': 6000, 'source':
                            catalog.city('baltimore')['places'][0]['source']}])
    assert any('₩4,500–₩6,000' in line for line in generators.facts(data))


def test_a_vet_is_an_errand_never_an_outing():
    vet = copy.deepcopy(catalog.city('baltimore')['places'][0]) | {'id': 'harbor-vet', 'name': 'Harbor Vet',
                                                                   'kind': 'vet'}
    data = city_as('modern', places=[*catalog.city('baltimore')['places'], vet])
    assert all(generators.outing(data, seed=f's{index}')['place']['kind'] != 'vet' for index in range(60))
    assert generators.outing(data, seed='s', kinds=['vet'])['place']['id'] == 'harbor-vet'
    assert townsfolk.at_place(data, 'harbor-vet')[0]['role'] == 'veterinarian'


def test_french_canadian_names_keep_their_quebec_family_names():
    data = city_as('modern', names={'mix': {'french-canadian': 1}})
    family = set(catalog.names()['banks']['modern']['french-canadian']['family'])
    people = [generators.name(data, seed=f'fc-{index}', age=50) for index in range(40)]
    assert all(person['family'] in family for person in people)
    assert {person['culture'] for person in people} == {'us', 'france'}
