"""The user's own changes to the people in the companion's life (companion/life/circle_edit.py), and the jobs the
character sheet gives them (companion/life/named.py, companion/life/job_words.py)."""
from companion.life import circle, circle_edit, job_words, named
from companion.memory import context
from companion.world import catalog
from companion.world.source import CatalogWorld

DANA = {'name': 'Dana', 'home_city': 'baltimore',
        'identity': 'Dana Okafor is 34. Her best friend Mia works as a tattoo artist. Her sister Bisi, a barista, '
                    'shares her love of records. Her mom Ana is a retired teacher. Her brother Tunde, a quiet man, '
                    'calls on Sundays.'}


def jobs(people):
    return {person['name']: person.get('job') for person in people}


def test_the_sheet_gives_its_people_jobs_and_ages():
    found = named.people({'name': 'Kai', 'identity': 'Her younger brother Tunde, a nurse at Mercy Medical Center, '
                                                     'visits. Her 61-year-old mom Ana runs a bakery. Her sister '
                                                     'Annika is a software engineer at Google.'})
    assert [(person['name'], person.get('job'), person.get('employer'), person.get('age')) for person in found] == [
        ('Tunde', 'nurse', 'Mercy Medical Center', None), ('Ana', None, None, 61),
        ('Annika', 'software engineer', 'Google', None)]
    assert jobs(named.people(DANA)) == {'Mia': 'tattoo artist', 'Bisi': 'barista', 'Ana': 'retired teacher',
                                        'Tunde': 'quiet man'}


def test_job_words_find_a_career_or_keep_the_words():
    offered = catalog.everyday(catalog.careers())
    assert job_words.career_match('ER nurse', offered)['id'] == 'registered-nurse'
    assert job_words.career_match('senior accountant', offered)['id'] == 'accountant'
    assert job_words.career_match('college student', offered)['id'] == 'undergraduate'
    assert job_words.career_match('quiet man', offered) is None
    assert job_words.no_job('retired teacher') == ('Retired', True)
    assert job_words.label('a tattoo artist') == 'Tattoo artist' and job_words.label('ER nurse') == 'ER nurse'


def test_the_circle_keeps_the_sheets_jobs():
    for world in (CatalogWorld(), None):
        sheet = DANA if world else {**DANA, 'home_city': ''}
        people = {person['name']: person for person in circle.build(sheet, world, 't1', 5)}
        assert people['Mia']['details']['career'] == 'Tattoo artist' and people['Mia']['schedule'][0]['label'] == \
            'Tattoo artist'
        assert people['Bisi']['career'] == 'barista' and people['Bisi']['details']['career'] == 'Barista'
        assert people['Ana']['details']['career'] == 'Retired' and people['Ana']['career'] == ''
        # Said in passing, "a quiet man" is no job: Tunde's is the app's.
        assert people['Tunde']['details']['career'] != 'Quiet man'


def companion(client, **definition):
    response = client.post('/api/companion', json={'name': 'Dana', 'timezone': 'America/New_York',
                                                    'home_city': 'baltimore', **definition})
    assert response.status_code == 200, response.text
    return response.json()


def test_the_user_edits_someone_in_the_circle(client):
    companion(client)
    person = client.get('/api/life/circle').json()[0]
    response = client.put(f"/api/life/circle/{person['id']}/about", json={
        'name': 'Robin Hale', 'role': 'Old roommate', 'pronouns': 'they/them', 'job': 'ER nurse',
        'employer': 'Mercy on Calvert', 'age': 41, 'note': 'Always late, never forgets a birthday'})
    assert response.status_code == 200, response.text
    edited = response.json()
    assert (edited['name'], edited['role'], edited['pronouns'], edited['age']) == ('Robin Hale', 'old roommate',
                                                                                   'they/them', 41)
    assert (edited['career'], edited['employer']) == ('ER nurse', 'Mercy on Calvert')
    assert edited['note'] == 'Always late, never forgets a birthday'
    assert {block['label'] for block in edited['schedule'] if block['kind'] == 'work'} == {'ER nurse'}
    assert context.person_text(edited).endswith('Always late, never forgets a birthday.')
    # A job the app doesn't know keeps the words, on office hours; moving away clears their week here.
    edited = client.put(f"/api/life/circle/{person['id']}/about", json={'job': 'Falconer'}).json()
    assert edited['career'] == 'Falconer' and {block['label'] for block in edited['schedule']
                                               if block['kind'] == 'work'} == {'Falconer'}
    edited = client.put(f"/api/life/circle/{person['id']}/about", json={'local': False}).json()
    assert edited['local'] is False and edited['schedule'] == [] and edited['career'] == 'Falconer'
    edited = client.put(f"/api/life/circle/{person['id']}/about", json={'local': True}).json()
    assert edited['local'] and edited['neighborhood'] and edited['schedule']
    # An empty note clears it; a removed person can't be changed.
    assert 'note' not in client.put(f"/api/life/circle/{person['id']}/about", json={'note': ''}).json()
    client.post(f"/api/life/circle/{person['id']}/remove")
    assert client.put(f"/api/life/circle/{person['id']}/about", json={'name': 'X'}).status_code == 409


def test_the_user_adds_someone_by_hand(client):
    companion(client)
    before = client.get('/api/life/circle').json()
    response = client.post('/api/life/circle/people', json={'name': 'Gran Iyabo', 'role': 'grandmother'})
    assert response.status_code == 200, response.text
    added = response.json()
    assert added['role'] == 'grandmother' and added['pronouns'] == 'she/her' and added['by_hand']
    assert added['spared'] is True and added['schedule']
    after = client.get('/api/life/circle').json()
    assert len(after) == len(before) + 1 and after[-1]['id'] == added['id']
    friend = client.post('/api/life/circle/people', json={'name': 'Mo', 'job': 'barista', 'local': False}).json()
    assert friend['role'] == 'friend' and friend['career'] == 'Barista' and friend['schedule'] == []
    assert client.post('/api/life/circle/people', json={'name': ' '}).status_code == 422


def test_a_mom_added_by_hand_takes_the_app_made_moms_place(client):
    companion(client)
    made = next(person for person in client.get('/api/life/circle').json() if person['role'] in ('mom', 'dad'))
    role = made['role']
    added = client.post('/api/life/circle/people', json={'name': 'Hollis', 'role': role}).json()
    listed = {person['id']: person for person in client.get('/api/life/circle?include_removed=true').json()}
    assert listed[made['id']]['status'] == 'removed' and listed[made['id']]['made_room_for'] == 'Hollis'
    assert [person['name'] for person in listed.values() if person['role'] == role and person['status'] == 'active'] \
        == ['Hollis']
    assert client.get('/api/life/circle/room').json()['people'] == len(listed) - 1  # Makes no room for a stranger.
    # Taken out again, the app's one comes back; put back, Hollis takes the place again.
    client.post(f"/api/life/circle/{added['id']}/remove", json={}).raise_for_status()
    back = {person['id']: person for person in client.get('/api/life/circle?include_removed=true').json()}
    assert back[made['id']]['status'] == 'active' and not back[made['id']].get('stepped_aside')
    client.post(f"/api/life/circle/{added['id']}/restore", json={}).raise_for_status()
    again = {person['id']: person for person in client.get('/api/life/circle?include_removed=true').json()}
    assert again[made['id']]['status'] == 'removed' and again[added['id']]['status'] == 'active'


def test_making_someone_mom_by_hand_takes_the_app_made_moms_place(client):
    companion(client)
    people = client.get('/api/life/circle').json()
    made = next(person for person in people if person['role'] in ('mom', 'dad'))
    friend = next(person for person in people if 'friend' in person['role'])
    client.put(f"/api/life/circle/{friend['id']}/about", json={'role': made['role']}).raise_for_status()
    listed = {person['id']: person for person in client.get('/api/life/circle?include_removed=true').json()}
    assert listed[made['id']]['status'] == 'removed' and listed[friend['id']]['status'] == 'active'
    assert listed[made['id']]['made_room_for'] == friend['full_name']


def test_someone_added_by_hand_takes_the_age_and_job_a_crew_list_gives():
    data = catalog.city('baltimore') | {'notables': [
        {'id': 'kirk', 'name': 'James T. Kirk', 'given': 'Jim', 'pronouns': 'he/him', 'age': 35, 'role': 'Captain'},
        {'id': 'scott', 'name': 'Montgomery Scott', 'pronouns': 'he/him', 'age': 46, 'role': 'Chief engineer'}]}
    sheet = {**DANA, 'identity': 'Dana Okafor is 38.'}

    def added(name, **change):
        person = circle_edit.words_person({'name': name, **change})
        return circle.city_named(data, sheet, 't1', person, f'circle:t1:by-hand:{name}')
    assert [added(name)['details']['age'] for name in ('James T. Kirk', 'Jim Kirk', 'Kirk', 'Montgomery Scott')] == \
        [35, 35, 35, 46]
    assert added('Kirk')['details']['career'] == 'Captain' and 'folk' not in added('Kirk')['details']
    # The user's own age and job win; someone the list doesn't name gets the app's.
    assert added('Kirk', age=50, job='Barista')['details']['age'] == 50
    assert added('Kirk', job='Barista')['details']['career'] == 'Barista'
    assert circle.notable_named(data, 'Scott Kirk') is None


def test_people_added_by_hand_are_not_all_one_age():
    sheet = {**DANA, 'identity': 'Dana Okafor is 38.'}
    data = catalog.city('baltimore')
    found = [circle.city_named(data, sheet, 't1', circle_edit.words_person({'name': f'Friend {index}'}),
                               f'circle:t1:by-hand:{index}')['details']['age'] for index in range(12)]
    assert len(set(found)) >= 7 and max(found) - min(found) >= 10
    assert 28 <= sum(found) / len(found) <= 48


def test_a_long_lived_companions_friends_are_their_age_in_years_while_a_human_could_be():
    data = catalog.city('baltimore') | {'kinds': {'vulcan': {'label': 'Vulcan', 'lifespan': 220, 'words': ['vulcan']}}}
    vulcan = {'name': 'Sorel', 'home_city': 'baltimore', 'identity': 'Sorel is a Vulcan of 38.'}
    life, peer = circle.centre_ages(data, vulcan, 't1')
    assert peer == 38 and life < 30  # 38 years is about 24 in human terms.
    elf = {'name': 'Ael', 'home_city': 'baltimore', 'identity': 'Ael is a 300-year-old elf.'}
    assert circle.centre_ages(data, elf, 't1') == (48, 48)  # No human friend is 300: theirs are about 48.
