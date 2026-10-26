"""The user's changes to the circle's pets (companion/life/circle_pets.py)."""
import pytest

MIRA = {'name': 'Mira', 'interests': ['vinyl records'], 'location': 'Fells Point, Baltimore',
        'timezone': 'America/New_York', 'background': 'Mira lives with a ginger cat named Biscuit.'}


@pytest.fixture
def circle(client):
    assert client.post('/api/companion', json=MIRA).status_code == 200
    return client.get('/api/life/circle').json()


def owner(client, people: list[dict]) -> dict:
    """Someone with a pet: a seeded one when anyone has one (about one in three do), else one given by hand."""
    found = next((person for person in people if person['pets']), None)
    return found or ok(client.post(f"/api/life/circle/{people[0]['id']}/pets", json={'name': 'Rex', 'kind': 'dog'}))


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def test_a_seeded_pet_can_be_edited_and_keeps_its_life(client, circle):
    person = owner(client, circle)
    pet = person['pets'][0]
    changed = ok(client.patch(f"/api/life/circle/{person['id']}/pets/{pet['number']}",
                              json={'name': 'Pickles', 'kind': 'tortoise', 'looks': 'a stately old tortoise', 'age': 30}))
    shown = changed['pets'][0]
    assert (shown['name'], shown['kind'], shown['looks'], shown['key']) == \
        ('Pickles', 'tortoise', 'a stately old tortoise', pet['key'])
    assert shown['age'] == '30 years old'
    again = next(found for found in client.get('/api/life/circle').json() if found['id'] == person['id'])
    assert again['pets'] == changed['pets'] and 'pets_by_user' not in again


def test_a_removed_pet_stays_removed_and_one_can_be_added(client, circle):
    person = owner(client, circle)
    number = person['pets'][0]['number']
    assert ok(client.post(f"/api/life/circle/{person['id']}/pets/{number}/remove", json={}))['pets'] == []
    assert next(found for found in client.get('/api/life/circle').json() if found['id'] == person['id'])['pets'] == []
    missing = client.patch(f"/api/life/circle/{person['id']}/pets/{number}", json={'name': 'Back'})
    assert missing.status_code == 404
    added = ok(client.post(f"/api/life/circle/{person['id']}/pets", json={'name': 'Biscuit II', 'kind': 'dog'}))
    assert [(pet['name'], pet['kind'], pet['looks']) for pet in added['pets']] == [('Biscuit II', 'dog', 'a dog')]
    assert added['pets'][0]['number'] == number + 1
    years = int(added['pets'][0]['age'].split()[0]) if 'year' in added['pets'][0]['age'] else 0
    assert years <= 8 and added['pets'][0]['state'] != 'died'  # an age that fits a dog, picked for you


def test_someone_without_a_pet_can_be_given_one_and_kinds_are_checked(client, circle):
    person = next((person for person in circle if not person['pets']), None)
    if person is None:  # everyone drew a pet (rare): take one away first
        person = circle[0]
        for pet in person['pets']:
            ok(client.post(f"/api/life/circle/{person['id']}/pets/{pet['number']}/remove", json={}))
    bad = client.post(f"/api/life/circle/{person['id']}/pets", json={'name': 'Nessie', 'kind': 'dragon'})
    assert bad.status_code == 422
    added = ok(client.post(f"/api/life/circle/{person['id']}/pets",
                           json={'name': 'Mochi', 'kind': 'cat', 'looks': 'a tiny kitten'}))
    assert added['pets'][0]['age'].endswith(('weeks old', 'months old'))


def test_aboard_a_ship_pets_are_rare_and_fit_a_cabin():
    from datetime import date

    from companion.life import home, pets
    day = date(2026, 10, 5)
    earth = [pets.circle_pets({'id': f'p{n}'}, 'modern', day) for n in range(600)]
    aboard = [pets.circle_pets({'id': f'p{n}'}, 'modern', day, aboard=True) for n in range(600)]
    assert 0.27 < sum(1 for found in earth if found) / 600 < 0.39
    assert 0.06 < sum(1 for found in aboard if found) / 600 < 0.14
    assert {found[0]['kind'] for found in aboard if found} <= set(pets.CABIN)
    assert 'dog' in {found[0]['kind'] for found in earth if found}
    cabin = {home.pet_item(f'seed{n}', 'modern', aboard=True)['variety'] for n in range(300)}
    assert cabin <= set(pets.CABIN) and {'cat', 'fish'} <= cabin
    assert home.HAS_PET_ABOARD < home.HAS_PET / 3
