"""A sociable companion has a bigger circle; who knows whom inside it stays consistent."""
import pytest
from conftest import set_life

from companion.life import body, circle

WORKDAY = [{'key': 'work', 'label': 'Work at the agency', 'kind': 'work', 'start': '09:00', 'end': '17:00',
            'days': [0, 1, 2, 3, 4]},
           {'key': 'evening', 'label': 'Evening', 'kind': 'social', 'start': '18:00', 'end': '22:00'},
           {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]


@pytest.fixture(autouse=True)
def steady(monkeypatch):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)


def make(client, personality, **extra):
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'America/New_York',
                                                     'location': 'Fells Point, Baltimore', 'schedule': WORKDAY,
                                                     'personality': personality, **extra})
    assert response.status_code == 200, response.text
    return response.json()


def test_how_sociable_they_are_is_read_from_who_they_are():
    assert circle.sociability({'personality': 'A total social butterfly who knows everyone.'}) == 'social'
    assert circle.sociability({'personality': 'Shy, a homebody.'}) == 'quiet'
    assert circle.sociability({'personality': 'Not shy at all, and outgoing.'}) == 'social'
    assert circle.sociability({'personality': 'Warm and curious.', 'interests': ['social work']}) == 'usual'
    assert circle.target_size({'personality': 'outgoing'}) == 10
    assert circle.target_size({'personality': 'outgoing'}, 6) == 6


def test_a_social_butterfly_has_coworkers_friends_old_and_new_and_family(client):
    make(client, 'Outgoing, the life of the party.')
    people = client.get('/api/life/circle').json()
    assert len(people) == 10
    roles = [person['role'] for person in people]
    assert {'close friend', 'longtime friend', 'new friend'} <= set(roles)
    assert sum(circle.role_kind(role) == 'parent' for role in roles) == 2
    coworkers = [person for person in people if person['role'] == 'coworker']
    assert len(coworkers) == 2
    for person in coworkers:
        assert person['works_with_companion'] and person['career'] == 'Works with Mira'
        work = [block for block in person['schedule'] if block['kind'] == 'work']
        assert [(block['start'], block['end'], block['days']) for block in work] == [('09:00', '17:00', [0, 1, 2, 3, 4])]
    names = [person['name'] for person in people]
    assert len(set(names)) == len(names)


def test_parents_and_siblings_are_called_what_the_companion_calls_them(client):
    make(client, 'Outgoing.')
    roles = {person['role'] for person in client.get('/api/life/circle').json()}
    assert not roles & {'parent', 'sibling'} or roles & {'mom', 'dad', 'sister', 'brother'}
    assert circle.relation('parent', 'she/her') == 'mom' and circle.relation('sibling', 'he/him') == 'brother'
    assert circle.relation('parent', 'they/them') == 'parent'


def test_who_knows_whom_is_stable_and_reaches_the_context(client):
    make(client, 'Gregarious and sociable.')
    people = client.get('/api/life/circle').json()
    again = client.get('/api/life/circle').json()
    assert [person['knows'] for person in people] == [person['knows'] for person in again]
    coworkers = [person for person in people if person['role'] == 'coworker']
    assert {'id': coworkers[1]['id'], 'name': coworkers[1]['name'], 'how': 'coworkers'} in coworkers[0]['knows']
    parents = [person for person in people if circle.role_kind(person['role']) == 'parent']
    assert any(item['id'] == parents[1]['id'] and item['how'] in ('married', 'divorced')
               for item in parents[0]['knows'])
    system = client.get('/api/context/preview').json()['system']
    assert f"- {coworkers[0]['name']} (coworker): works with you." in system
    assert 'Knows ' in system


def test_an_existing_circle_grows_without_changing_anyone(client):
    make(client, 'Warm and curious.')
    before = client.get('/api/life/circle').json()
    assert len(before) == circle.CIRCLE_SIZE
    assert client.get('/api/life/circle/room').json() == {'people': 5, 'target': 5, 'sociability': 'usual'}
    assert client.post('/api/life/circle/grow').status_code == 409
    set_life(client, circle_size=9)
    grown = client.post('/api/life/circle/grow').json()
    assert len(grown) == 9
    assert [(person['id'], person['name']) for person in grown[:5]] == [(person['id'], person['name'])
                                                                       for person in before]
    added = {circle.role_kind(person['role']) for person in grown[5:]}
    assert 'longtime friend' in added or 'new friend' in added
    names = [person['name'] for person in grown]
    assert len(set(names)) == len(names)


def test_a_quiet_companion_keeps_a_small_circle(client):
    make(client, 'Shy and reserved, a homebody.')
    assert len(client.get('/api/life/circle').json()) == 4
