"""The user's own changes to the people in the companion's life (companion/life/circle_edit.py), and the jobs the
character sheet gives them (companion/life/named.py, companion/life/job_words.py)."""
from companion.life import circle, job_words, named
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
