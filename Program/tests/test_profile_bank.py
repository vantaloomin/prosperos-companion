"""A townsperson's profile comes out filled in by rule (companion/world/profile_bank.py): skills from their work,
something they are only middling at, what makes them laugh or snap, how they talk, and their own pronouns."""
from datetime import date

from companion import cast
from companion.world import catalog, life_details, looks, profile_bank, townsfolk

FOUND = {'meetings': [], 'in_story': None, 'match': None, 'focus': None}


def test_the_bank_has_lines_for_every_career_and_title_and_a_hundred_of_each_kind():
    found = profile_bank.bank()
    for kind in profile_bank.LISTS:
        assert len(found[kind]) >= 100
    titles = {role[0] for roles in townsfolk.ROLES.values() for role in roles if role[2]} | \
        {role[1] for roles in townsfolk.ROLES.values() for role in roles if role[2]}
    assert titles <= set(found['staff'])
    for city in catalog.cities():
        data = catalog.city(city)
        for career in catalog.careers_for(data, needs_met=False).values():
            assert len(found['careers'].get(career['id'], [])) == 3, (city, career['id'])


def test_every_townsperson_gets_work_skills_and_their_own_pronouns():
    data = catalog.city('baltimore')
    for place in data['places'][:40]:
        for sheet in townsfolk.at_place(data, place['id']):
            definition = cast.profile(data, sheet, FOUND, date(2026, 3, 2))
            working = sheet.get('occupation') or sheet['kind'] == 'staff'
            assert len(definition['skills']) >= (4 if working and sheet['kind'] != 'staff' else 3)
            assert ' laugh' in definition['personality'] and ' snap' in definition['personality']
            assert definition['history_together']
            assert looks.pronouns_of(definition) == sheet['pronouns']


def test_a_story_told_about_someone_who_goes_by_they_agrees():
    assert life_details.agreed('was elected class president', 'they') == 'were elected class president'
    assert life_details.agreed('was elected class president', 'she') == 'was elected class president'
