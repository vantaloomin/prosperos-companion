"""Townsfolk: seeded people at the city's places, run by rules, met by the companion while out."""
import copy
from collections import Counter
from datetime import date, datetime, timedelta

import pytest
from test_network import build
from test_social_circle import make

from companion.characters import require_current
from companion.database import decode
from companion.life import body, encounters, network
from companion.world import catalog, couples, dating, generators, naming, townsfolk


@pytest.fixture(autouse=True)
def steady(monkeypatch):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)


@pytest.fixture
def chatty(monkeypatch):
    monkeypatch.setattr(encounters, 'ACTIVE', True)
    monkeypatch.setattr(encounters, 'CHANCE', 1)
    monkeypatch.setattr(encounters, 'FAMILIAR_CHANCE', 1)


def test_every_place_has_its_own_people_rebuilt_the_same_from_their_key():
    for data in catalog.cities().values():
        for place in data['places']:
            people = townsfolk.at_place(data, place['id'])
            extra = len(townsfolk.notables_at(data, place['id']))
            assert townsfolk.PEOPLE[0] <= len(people) - extra <= townsfolk.PEOPLE[1]
            assert people == townsfolk.at_place(data, place['id'])
            for sheet in people:
                assert townsfolk.find(data, sheet['key']) == sheet
                assert sheet.get('notable') or not naming.is_invented(sheet['full'])
                assert sheet['flaw'] in townsfolk.FLAWS and sheet['desire'] in townsfolk.DESIRES
            if any(role[2] for role in townsfolk.ROLES.get(place['kind'], ())):
                assert people[0]['staff'] and people[0]['shifts']['days']
    data = catalog.city('baltimore')
    assert townsfolk.find(data, 'town:baltimore:nowhere:0') is None
    assert townsfolk.find(data, 'town:camelot:national-aquarium:0') is None
    assert townsfolk.at_place(data, 'nowhere') == []


def test_period_cities_get_period_jobs():
    data = catalog.city('camelot')
    roles = {sheet['role'] for place in data['places'] for sheet in townsfolk.at_place(data, place['id'])}
    assert 'barkeep' in roles and 'bartender' not in roles and 'barista' not in roles


def test_simple_rules_decide_where_they_are():
    data = catalog.city('baltimore')
    sheet = next(sheet for place in data['places'] for sheet in townsfolk.at_place(data, place['id'])
                 if sheet['staff'] and not sheet['night_owl'])
    day = date(2026, 10, 5)
    while day.weekday() not in sheet['shifts']['days']:
        day += timedelta(days=1)
    start = sheet['shifts']['window'][0]
    on_shift = townsfolk.whereabouts(sheet, data, datetime.combine(day, datetime.min.time())
                                     + timedelta(minutes=start + 30))
    assert on_shift['at_place'] and sheet['role'] in on_shift['doing']
    night = townsfolk.whereabouts(sheet, data, datetime(day.year, day.month, day.day, 3, 0))
    assert night == {'place': None, 'at_place': False, 'neighborhood': sheet['home'], 'doing': 'asleep',
                     'mood': night['mood']}
    regular = next(sheet for place in data['places'] for sheet in townsfolk.at_place(data, place['id'])
                   if not sheet['staff'] and sheet['visits']['part'] == 'afternoon')
    day = date(2026, 10, 5)
    while day.weekday() not in regular['visits']['days']:
        day += timedelta(days=1)
    visit = townsfolk.whereabouts(regular, data, datetime(day.year, day.month, day.day, 14, 0))
    assert visit['place']['id'] == regular['place']['id'] and 'usual spot' in visit['doing']


def test_goals_move_week_by_week_and_lead_to_the_next_one():
    data = catalog.city('baltimore')
    sheet = townsfolk.at_place(data, data['places'][0]['id'])[0]
    states = [townsfolk.story(sheet, data, townsfolk.EPOCH + timedelta(weeks=week)) for week in range(120)]
    assert states == [townsfolk.story(sheet, data, townsfolk.EPOCH + timedelta(weeks=week)) for week in range(120)]
    beats = {state['beat'] for state in states}
    assert {'progress', 'stall'} <= beats and 'achieved' in beats
    done = next(index for index, state in enumerate(states) if state['beat'] == 'achieved')
    assert states[done]['line'] and states[done]['reached'] and states[done]['goal'] != states[done - 1]['goal']
    assert townsfolk.story(sheet, data, date(2020, 1, 1))['beat'] == 'stall'


def test_every_neighborhood_has_residents_with_their_own_days():
    data = catalog.city('baltimore')
    total = 0
    for hood in data['neighborhoods']:
        people = townsfolk.residents(data, hood['id'])
        total += len(people)
        assert townsfolk.RESIDENTS[0] <= len(people) <= townsfolk.RESIDENTS[1]
        for sheet in people[:5]:
            assert townsfolk.find(data, sheet['key']) == sheet and sheet['kind'] == 'resident'
            assert sheet['home'] == hood['id'] and sheet['full'] and not naming.is_invented(sheet['full'])
            assert sheet['place']['id'] in sheet['reach'] and f"~{hood['id']}" in sheet['reach']
    assert total >= 1000
    commuter = next(sheet for hood in data['neighborhoods'] for sheet in townsfolk.residents(data, hood['id'])
                    if sheet.get('commute') and sheet['commute']['stop'] and sheet['commute']['leave'] < 9 * 60
                    and not sheet['night_owl'])
    monday = date(2026, 10, 5)
    leave = datetime.combine(monday, datetime.min.time()) + timedelta(minutes=commuter['commute']['leave'] - 10)
    waiting = townsfolk.whereabouts(commuter, data, leave)
    assert waiting['place']['id'] == f"~{commuter['home']}" and waiting['doing'].startswith('waiting for the ')
    assert townsfolk.whereabouts(commuter, data, leave + timedelta(hours=3))['doing'].startswith('at work')
    assert townsfolk.whereabouts(commuter, data, datetime(2026, 10, 5, 3, 0))['doing'] == 'asleep'
    assert commuter in [sheet for sheet in townsfolk.residents(data, commuter['home'])]
    assert commuter['key'] in {sheet['key'] for sheet in townsfolk.reaching(data, f"~{commuter['home']}")}
    regulars = townsfolk.reaching(data, commuter['place']['id'])
    assert commuter['key'] in {sheet['key'] for sheet in regulars}
    assert all(commuter['place']['id'] in sheet['reach'] for sheet in regulars)
    assert townsfolk.find(data, 'town:baltimore:~nowhere:0') is None


def everyone(data):
    return [*(sheet for place in data['places'] for sheet in townsfolk.at_place(data, place['id'])),
            *(sheet for hood in data['neighborhoods'] for sheet in townsfolk.residents(data, hood['id']))]


def test_strangers_never_share_the_companions_family_name(client):
    data = catalog.city('baltimore')
    before = everyone(data)
    common = Counter(sheet['full'].split()[-1] for sheet in before).most_common(1)[0][0]
    make(client, 'Warm and curious.', name=f'Mya {common}')
    with client.app.state.database.connect() as connection:
        theirs = network.city(connection, require_current(connection))
    assert common in theirs['kin']
    after = everyone(theirs)
    assert not any(sheet['full'].endswith(f' {common}') for sheet in after)
    for old, new in zip(before, after, strict=True):
        # Only the family name that clashed is drawn again; everyone else keeps their name.
        assert new['full'] == old['full'] if not old['full'].endswith(f' {common}') else \
            new['full'].startswith(f"{old['name']} ") and new['pronouns'] == old['pronouns']
    for index in range(30):
        made = generators.circle(data, seed=f'kin-{index}', size=6, family=common)
        assert all(person['name']['family'] != common for person in made['people']
                   if generators.ROLES[person['role']][2] is False)


def test_the_city_view_lists_a_neighborhoods_residents(client):
    hood = catalog.city('baltimore')['neighborhoods'][0]['id']
    response = client.get(f'/api/world/cities/baltimore/neighborhoods/{hood}/people', params={'at': '08:00'})
    assert response.status_code == 200, response.text
    assert len(response.json()) >= townsfolk.RESIDENTS[0] and all(person['now']['doing'] for person in response.json())
    assert client.get('/api/world/cities/baltimore/neighborhoods/nowhere/people').status_code == 404


def test_neighbors_are_met_on_the_way_out(client, clock, chatty, monkeypatch):
    make(client, 'Warm and curious.')
    monkeypatch.setattr(encounters, 'KINDS', set())
    build(client)
    clock.instant = clock.now() + timedelta(days=14)
    met = [row for row in build(client) if row['entry'] and row['entry'].get('townsfolk')]
    assert met and all(decode(row['block'])['kind'] in encounters.COMMUTE_KINDS for row in met)
    assert all('On the way out that morning, got talking with ' in row['entry']['summary'] and 'a neighbor' in
               row['entry']['summary'] for row in met if row['entry']['townsfolk']['times'] == 1)


def test_the_city_view_lists_everyone_at_a_place(client):
    response = client.get('/api/world/cities/baltimore/places/national-aquarium/people', params={'at': '10:00'})
    assert response.status_code == 200, response.text
    people = response.json()
    assert people and all(person['story']['goal']['text'] and person['routine'] for person in people)
    assert client.get('/api/world/cities/baltimore/places/nowhere/people').status_code == 404


def test_the_companion_runs_into_townsfolk_and_learns_more_each_time(client, clock, chatty, monkeypatch):
    monkeypatch.setattr(encounters, 'KNOWS_HEART', 2)
    make(client, 'Warm and curious.')
    rows = build(client)
    met = [row for row in rows if row['entry'] and row['entry'].get('townsfolk')]
    assert met and 'got talking with ' in met[0]['entry']['summary'].lower()
    assert len({row['local_date'] for row in met}) == len(met)
    assert client.get('/api/life/townsfolk').json() == []
    # Who is where depends on the seeded city, so from here on the first person met is the one around: with others
    # there too, who gets talked to is seeded by the companion's id and the first one could be met only twice.
    first = met[0]['entry']['townsfolk']['key']
    seeded = encounters.present

    def around(data, place_id, times_of_day, history, cast=None, plans=None):
        found = seeded(data, place_id, times_of_day, history, cast, plans)
        return (found[0] if found else times_of_day[0]), {first: {'doing': ''}}

    monkeypatch.setattr(encounters, 'present', around)
    for _week in range(2):
        clock.instant = clock.now() + timedelta(days=7)
        build(client)
    known = client.get('/api/life/townsfolk').json()
    assert known and all(person['times'] >= 1 for person in known)
    often = next(person for person in known if person['key'] == first)
    assert often['times'] >= 3, known
    news = [row['entry']['summary'] for row in build(client) if row['entry'] and row['entry'].get('townsfolk')]
    assert any('turns out' in text for text in news)
    assert often['goal'] and often['flaw'] and often['desire'] and often['routine']
    once = [person for person in known if person['times'] == 1]
    assert all(person['goal'] is None and person['flaw'] is None for person in once)
    detail = client.get('/api/life/townsfolk/person', params={'key': often['key']})
    assert detail.status_code == 200 and detail.json()['now']['doing']
    assert client.get('/api/life/townsfolk/person', params={'key': 'town:baltimore:x:0'}).status_code == 404
    with client.app.state.database.connect() as connection:
        companion = require_current(connection)
        lines = encounters.context_lines(connection, companion, clock.now())
    recent = known[:encounters.CONTEXT_LIMIT]
    assert [key for key, _line in lines] == [person['key'] for person in recent]
    for (_key, line), person in zip(lines, recent, strict=True):
        # "They are trying to": a random "how they come across" line can say "trying to" too.
        assert person['full'] in line and ('They are trying to' in line) == bool(person['goal'])


def test_no_townsfolk_when_off(client):
    make(client, 'Warm and curious.')
    assert not any(row['entry'] and row['entry'].get('townsfolk') for row in build(client))


def test_replies_build_their_context_with_townsfolk_on(client, clock, chatty):
    make(client, 'Warm and curious.')
    assert client.get('/api/context/preview').status_code == 200
    build(client)
    clock.instant = clock.now() + timedelta(days=7)
    build(client)
    assert client.get('/api/life/townsfolk').json()
    preview = client.get('/api/context/preview')
    assert preview.status_code == 200, preview.text
    assert 'townsfolk' in preview.text, preview.json().keys()


def test_no_baltimore_resident_teaches_surfing():
    data = catalog.city('baltimore')
    jobs = {townsfolk._occupation(data, f'resident-{n}', 30) for n in range(2000)}
    assert 'surf instructor' not in jobs and len(jobs) > 20


OLD_WORK = ('london-1895', 'camelot', 'calderwick', 'whitlock', 'ellerbruck')
JAZZ_AGE = ('new-york-1925', 'pellmouth')


def test_the_old_eras_keep_work_by_gender_and_fantasy_and_today_leave_it_open():
    assert all(generators.by_gender(catalog.city(city)) for city in (*OLD_WORK, *JAZZ_AGE))
    # Ellerbruck's fairy-tale customs turn it on; Grandport's republic and Oz leave it open, like today.
    for city in ('grandport', 'emerald-city', 'baltimore', 'london'):
        assert not generators.by_gender(catalog.city(city)), city
    assert not generators.by_gender(catalog.city('london-1895') | {'work_by_gender': False})


@pytest.mark.parametrize('city_id', OLD_WORK)
def test_in_an_older_era_nobody_works_the_other_sides_job(city_id):
    data = catalog.city(city_id)
    careers = catalog.careers_for(data)
    by_name = {career['name'].lower(): career for career in careers.values()}
    seen = Counter()
    for n in range(300):
        person = generators.resident(data, seed=f'era-{n}', role='friend', age=40)
        side = generators.SIDES.get(person['name']['pronouns'].split('/')[0])
        if person['job'] and side:
            worked_by = careers[person['job']['career']['id']].get('worked_by')
            assert worked_by in (None, side), (person['name']['full'], person['job']['career']['name'])
            seen[side, worked_by] += 1
        # The town's own people at home and on its streets, named or not yet, the same.
        resident = townsfolk.resident(data, data['neighborhoods'][n % len(data['neighborhoods'])]['id'], n)
        found, job = generators.SIDES.get(resident['pronouns'].split('/')[0]), by_name.get(resident['occupation'])
        if found and job:
            assert job.get('worked_by') in (None, found), (resident['full'], resident['occupation'])
        unnamed = townsfolk.resident(data, data['neighborhoods'][n % len(data['neighborhoods'])]['id'], n, named=False)
        assert unnamed['occupation'] == resident['occupation']
    # Both sides still have work of their own and work anyone does.
    assert seen['men', 'men'] and seen['women', 'women'] and seen['men', None] and seen['women', None], seen


@pytest.mark.parametrize('city_id', JAZZ_AGE)
def test_in_the_jazz_age_the_few_jobs_still_kept_to_men_go_to_men(city_id):
    """1925: a riveter, a motorman or a subway guard is a man; the rest of the work is open to anyone."""
    data = catalog.city(city_id)
    careers = catalog.careers_for(data)
    men_only = {key for key, career in careers.items() if career.get('worked_by') == 'men'}
    assert {'streetcar-motorman', 'longshoreman'} <= men_only or city_id == 'pellmouth'
    assert not any(career.get('worked_by') == 'women' for career in careers.values())
    women = {generators.town_career(data, f'w-{n}', pronouns='she/her')['id'] for n in range(400)}
    assert not women & men_only and len(women) > 20
    men = {generators.town_career(data, f'm-{n}', pronouns='he/him')['id'] for n in range(400)}
    assert men & men_only


def test_a_job_kept_to_an_age_goes_to_someone_that_age():
    """A squire is young, a governess not past fifty, a student 18 to 22 (Career.ages)."""
    camelot, london = catalog.city('camelot'), catalog.city('london-1895')
    assert list(catalog.careers_for(camelot)['squire']['ages']) == [18, 24]
    for n in range(300):
        older = generators.resident(camelot, seed=f'age-{n}', role='friend', age=55, pronouns='he/him')
        assert not older['job'] or older['job']['career']['id'] != 'squire'
        assert townsfolk._occupation(camelot, f'old-{n}', 55, 'he/him') != 'squire'
        assert townsfolk._occupation(london, f'old-{n}', 60, 'she/her') not in ('typist', 'governess')
    young = {generators.town_career(camelot, f'y-{n}', pronouns='he/him', age=20)['id'] for n in range(400)}
    assert 'squire' in young
    assert generators.fits_age({'ages': (18, 24)}, 24) and not generators.fits_age({'ages': (18, 24)}, 25)
    assert generators.fits_age({'name': 'Baker'}, 64) and generators.fits_age(None, 30)


def test_a_they_them_resident_and_a_city_of_today_pick_from_every_job():
    data = catalog.city('london-1895')
    assert generators.fits_side(data, 'they/them') is None and generators.fits_side(catalog.city('london'), 'she') is None
    women = {generators.town_career(data, f'w-{n}', pronouns='she/her')['id'] for n in range(400)}
    assert 'cabman' not in women and 'docker' not in women and {'governess', 'typist'} & women
    men = {generators.town_career(data, f'm-{n}', pronouns='he')['id'] for n in range(400)}
    assert 'governess' not in men and 'typist' not in men and 'cabman' in men


def with_notables(city_id: str = 'baltimore') -> dict:
    """A built-in city with two named people added, the way a pack lists its characters."""
    raw = copy.deepcopy(catalog.city(city_id))
    for key in ('data_version', 'builtin', 'origin', 'pack_file'):
        raw.pop(key, None)
    place = next(item for item in raw['places'] if item['kind'] == 'bar')
    source = next(iter(raw['sources']))
    raw['notables'] = [
        {'id': 'tess', 'name': 'Tess Harrow', 'pronouns': 'she/her', 'age': 41, 'place': place['id'],
         'role': 'owner', 'staff': True, 'about': 'Runs the bar her mother opened.', 'temperament': 'gruff',
         'source': source},
        {'id': 'old-ned', 'name': 'Edward "Ned" Pike', 'given': 'Ned', 'pronouns': 'he/him', 'age': 77,
         'place': place['id'], 'role': 'retired harbor pilot', 'about': 'Knows every ship that ever docked here.',
         'source': source}]
    return catalog.prepare(raw, mend=True)


def test_a_citys_notables_join_the_townsfolk_at_their_place():
    data = with_notables()
    place_id = data['notables'][0]['place']
    people = townsfolk.at_place(data, place_id)
    seeded = townsfolk.count(data, catalog.find(data, place_id))
    named = people[seeded:]
    assert [sheet['full'] for sheet in named] == ['Tess Harrow', 'Edward "Ned" Pike']
    tess, ned = named
    assert (tess['name'], tess['age'], tess['role'], tess['temperament'], tess['staff']) == \
        ('Tess', 41, 'owner', 'gruff', True)
    assert tess['shifts']['days'] and 'visits' not in tess
    assert ned['name'] == 'Ned' and not ned['staff'] and ned['visits']['days']
    assert ned['about'] == 'Knows every ship that ever docked here.' and ned['notable'] == 'old-ned'
    for sheet in named:
        assert townsfolk.find(data, sheet['key']) == sheet
        assert not dating.on_app(sheet, data)
        assert townsfolk.whereabouts(sheet, data, datetime(2026, 3, 4, 20, 0))
    assert tess['flaw'] != ned['flaw'] or tess['quirk'] != ned['quirk']


def test_what_the_companion_knows_of_a_notable_says_who_they_are():
    data = with_notables()
    sheet = townsfolk.at_place(data, data['notables'][1]['place'])[-1]
    person = encounters.revealed(sheet, data, [{'place': 'there', 'local_date': '2026-03-04'}], None, {})
    assert 'Who they are: Knows every ship that ever docked here.' in encounters.text(person)


def test_a_notable_can_be_of_another_kind_and_keep_no_seeded_love_life():
    raw = copy.deepcopy(catalog.city('grandport'))
    for key in ('data_version', 'builtin', 'origin', 'pack_file'):
        raw.pop(key, None)
    place = raw['places'][0]
    source = next(iter(raw['sources']))
    raw['notables'] = [
        {'id': 'ilwen', 'name': 'Ilwen', 'pronouns': 'she/her', 'age': 400, 'place': place['id'], 'role': 'archivist',
         'about': 'An elven archivist.', 'kind': 'elf', 'love_life': False, 'source': source},
        {'id': 'brom', 'name': 'Brom', 'pronouns': 'he/him', 'age': 50, 'place': place['id'], 'role': 'porter',
         'about': 'A porter.', 'kind': 'gnome', 'source': source}]
    data = catalog.prepare(raw, mend=True)
    assert any('"gnome"' in note for note in data['import_notes'])
    ilwen, brom = townsfolk.at_place(data, place['id'])[-2:]
    assert (ilwen['age'], ilwen['folk'], ilwen['love_life']) == (400, 'elf', False)
    assert dating.life_of(ilwen, data) < 60  # An elf of 400 is in mid-life.
    assert couples.details_of(ilwen, data) is None and couples.couple(ilwen, data, date(2027, 6, 1)) is None
    assert 'folk' not in brom and 'love_life' not in brom


def test_a_notables_kind_and_love_life_leave_older_cities_as_they_were():
    data = with_notables()
    assert all('kind' not in item and 'love_life' not in item for item in data['notables'])
