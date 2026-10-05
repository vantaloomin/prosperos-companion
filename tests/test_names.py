"""Names come from what people were actually called in the year they were born, never from a model's habits."""
import json
import runpy
from pathlib import Path

import pytest

from companion.world import catalog, generators, naming

CITIES = sorted(key for key, value in catalog.cities().items() if value['origin'] == 'builtin')
SCRIPTS = Path(__file__).parent.parent / 'scripts' / 'world'


def test_shipped_given_names_match_their_script():
    written = json.loads((catalog.DATA / 'given_names.json').read_text(encoding='utf-8'))
    assert runpy.run_path(str(SCRIPTS / 'given_names.py'))['GIVEN_NAMES'] == written, \
        'Rerun scripts/world/given_names.py.'


def test_every_culture_a_name_group_links_to_exists_and_cohorts_are_full():
    cultures = naming.data()['cultures']
    for bank in catalog.names()['banks'].values():
        for group in bank.values():
            assert set(group['cultures']) - {'local'} <= set(cultures)
    for key, culture in cultures.items():
        for cohort in culture['cohorts']:
            assert cohort['start'] <= cohort['end']
            assert len(cohort['feminine']) >= 20 and len(cohort['masculine']) >= 20, (key, cohort['start'])
    us = cultures['us']
    assert [cohort['start'] for cohort in us['cohorts'] if not cohort['estimate']] == list(range(1920, 2009))
    assert all(len(cohort['feminine']) == 100 for cohort in us['cohorts'] if not cohort['estimate'])


def test_a_name_fits_the_year_the_person_was_born():
    city = catalog.city('san-diego')
    for age in (22, 45, 70):
        born = naming.present_year() - age
        for index in range(40):
            person = generators.name(city, seed=f'age-{index}', age=age, pronouns='she')
            if person['culture'] != 'us':
                continue
            years = [cohort for cohort in naming.data()['cultures']['us']['cohorts']
                     if born - naming.SPREAD <= cohort['end'] and cohort['start'] <= born + naming.SPREAD]
            assert any(person['given'] in cohort['feminine'] for cohort in years), (age, person['given'])


def test_older_and_younger_people_get_different_names():
    city = catalog.city('baltimore')
    older = {generators.name(city, seed=f'gen-{index}', age=72)['given'] for index in range(80)}
    younger = {generators.name(city, seed=f'gen-{index}', age=23)['given'] for index in range(80)}
    assert len(older & younger) < len(older) / 3


def test_a_culture_with_its_own_family_names_supplies_both_names():
    city = catalog.city('san-diego') | {'names': {'mix': {'south-asian': 1}}}
    people = [generators.name(city, seed=f'sa-{index}', age=35) for index in range(40)]
    indian = [person for person in people if person['culture'] == 'india']
    assert indian and all(person['family'] in naming.culture('india')['surnames'] for person in indian)


def test_a_city_abroad_uses_its_own_countrys_names():
    city = catalog.city('baltimore') | {'country': 'Japan', 'names': {'mix': {'anglo': 1}}}
    people = [generators.name(city, seed=f'jp-{index}', age=40) for index in range(20)]
    assert {person['culture'] for person in people} == {'japan'}
    assert all(person['family'] in naming.culture('japan')['surnames'] for person in people)


def test_relatives_keep_the_family_name_with_a_fitting_given_name():
    city = catalog.city('new-york')
    made = generators.circle(city, seed='kin', size=12, age=34)
    for person in made['people']:
        if person['role'] in ('parent', 'sibling'):
            assert naming.base_family(person['name']['culture'], person['name']['family']) == made['family']


@pytest.mark.parametrize('city_id', CITIES)
def test_generated_people_never_have_invented_sounding_names(city_id):
    city = catalog.city(city_id)
    for index in range(150):
        person = generators.name(city, seed=f'clean-{index}', age=18 + index % 70)
        assert not naming.is_invented(person['full']), person['full']


def test_invented_names_are_found_in_text_unless_allowed():
    assert naming.is_invented('Elara Voss') and naming.is_invented('Kael') and not naming.is_invented('Karen Smith')
    text = 'Her friend Elara met Vex at the bar near Thorne Street.'
    assert naming.invented_in(text) == ['Elara', 'Vex', 'Thorne']
    assert naming.invented_in(text, allowed='Thorne Street is a real place') == ['Elara', 'Vex']
    # Only capitalised words count, so ordinary words are never mistaken for names.
    assert naming.invented_in('a sable coat and a vesper bell') == []


def test_polish_and_russian_family_names_take_the_feminine_form():
    assert naming.gendered('poland', 'Kowalski', 'she') == 'Kowalska'
    assert naming.gendered('russia', 'Ivanov', 'she') == 'Ivanova'
    assert naming.gendered('russia', 'Ivanov', 'he') == 'Ivanov'
    assert naming.base_family('poland', 'Kowalska') == 'Kowalski'
    city = catalog.city('baltimore') | {'country': 'Poland', 'names': {'mix': {'anglo': 1}}}
    sister = generators.name(city, seed='pl', pronouns='she', family='Nowak', age=30)
    brother = generators.name(city, seed='pl', pronouns='he', family='Kowalska', age=30)
    assert sister['family'] == 'Nowak' and brother['family'] == 'Kowalski'
