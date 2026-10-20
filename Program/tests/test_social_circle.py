"""A sociable companion has a bigger circle; who knows whom inside it stays consistent."""
from datetime import timedelta

import pytest
from conftest import set_life

from companion.characters import current
from companion.clock import parse
from companion.life import ages, body, circle

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


def test_an_existing_circle_grows_on_its_own_without_changing_anyone(client):
    make(client, 'Warm and curious.')
    before = client.get('/api/life/circle').json()
    assert len(before) == circle.CIRCLE_SIZE
    assert client.get('/api/life/circle/room').json() == {'people': 5, 'target': 5, 'sociability': 'usual'}
    assert client.post('/api/life/circle/grow').status_code == 409
    set_life(client, circle_size=9)
    grown = client.get('/api/life/circle').json()
    assert len(grown) == 9 and client.post('/api/life/circle/grow').status_code == 409
    assert [(person['id'], person['name']) for person in grown[:5]] == [(person['id'], person['name'])
                                                                       for person in before]
    added = {circle.role_kind(person['role']) for person in grown[5:]}
    assert 'longtime friend' in added or 'new friend' in added
    names = [person['name'] for person in grown]
    assert len(set(names)) == len(names)


def test_a_quiet_companion_keeps_a_small_circle(client):
    make(client, 'Shy and reserved, a homebody.')
    assert len(client.get('/api/life/circle').json()) == 4


def test_someone_removed_is_not_replaced_until_the_user_asks(client):
    make(client, 'Warm and curious.')
    [first, *_rest] = client.get('/api/life/circle').json()
    client.post(f"/api/life/circle/{first['id']}/remove")
    assert len(client.get('/api/life/circle').json()) == circle.CIRCLE_SIZE - 1
    assert len(client.post('/api/life/circle/grow').json()) == circle.CIRCLE_SIZE


def test_grow_right_after_raising_the_size_adds_people_instead_of_refusing(client):
    make(client, 'Warm and curious.')
    assert len(client.get('/api/life/circle').json()) == circle.CIRCLE_SIZE
    set_life(client, circle_size=7)
    grown = client.post('/api/life/circle/grow')
    assert grown.status_code == 200, grown.text
    assert len(grown.json()) == 7 and len(client.get('/api/life/circle').json()) == 7
    assert client.post('/api/life/circle/grow').status_code == 409


def elders(client) -> list[dict]:
    return [person for person in client.get('/api/life/circle').json() if person.get('elder')]


def test_a_companion_under_40_has_a_grandparent_on_top_of_their_circle(client, monkeypatch):
    monkeypatch.setattr(circle, 'ELDERS', True)
    make(client, 'Warm and curious.', identity='34.')
    people = client.get('/api/life/circle').json()
    [elder] = elders(client)
    assert len(people) == circle.CIRCLE_SIZE + 1 and people[-1]['id'] == elder['id']
    assert elder['role'] in ('grandmother', 'grandfather', 'grandparent') and 76 <= elder['age'] <= 95
    assert elder['career'] == 'Retired' and elder['full_name']
    assert circle.role_kind(elder['role']) in circle.FAMILY
    # The size is still five: the room offer and growing count without them.
    assert client.get('/api/life/circle/room').json()['people'] == circle.CIRCLE_SIZE
    assert client.post('/api/life/circle/grow').status_code == 409


def test_a_companion_of_40_or_more_has_none(client, monkeypatch):
    monkeypatch.setattr(circle, 'ELDERS', True)
    make(client, 'Warm and curious.', identity='45.')
    assert elders(client) == []


def test_without_a_known_city_the_grandparent_still_has_an_age(client, monkeypatch):
    monkeypatch.setattr(circle, 'ELDERS', True)
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC', 'identity': '25.',
                                                     'personality': 'Warm.'})
    assert response.status_code == 200, response.text
    [elder] = elders(client)
    assert 75 <= elder['age'] <= 95 and elder['pronouns'] in ('she/her', 'he/him')


def test_an_existing_circle_gains_a_grandparent_dated_from_then(client, clock, monkeypatch):
    make(client, 'Warm and curious.', identity='30.')
    before = client.get('/api/life/circle').json()
    clock.advance(timedelta(days=40))
    monkeypatch.setattr(circle, 'ELDERS', True)
    people = client.get('/api/life/circle').json()
    [elder] = elders(client)
    assert [person['id'] for person in people[:-1]] == [person['id'] for person in before]
    with client.app.state.database.connect() as connection:
        cursor = connection.execute('SELECT through FROM agenda_cursors WHERE subject=?', (elder['id'],)).fetchone()
        assert parse(cursor['through']) == clock.now()
        written = connection.execute('SELECT starts_at FROM life_agenda WHERE subject=?', (elder['id'],)).fetchall()
        assert all(parse(row['starts_at']) >= clock.now() - timedelta(minutes=1) for row in written)
        ages.sync(connection, clock.now())
        row = ages.stored(connection, 'circle', elder['id'])
        assert row['anchored_on'] == clock.now().date().isoformat() and row['from_age'] == elder['age']
    # Taken out by the user, they are not added again.
    client.post(f"/api/life/circle/{elder['id']}/remove")
    assert elders(client) == []


def test_parents_who_parted_in_an_older_city_are_separated_and_rarer():
    """A quarter of the circle's parents today are divorced; before 1950 (breakups.separated) few parted, and they
    separated."""
    pairs = [({'id': f'a{n}', 'role': 'mom'}, {'id': f'b{n}', 'role': 'dad'}) for n in range(2000)]
    today = [circle.tie(first, second) for first, second in pairs]
    older = [circle.tie(first, second, older=True) for first, second in pairs]
    assert set(today) == {'married', 'divorced'} and 0.2 < today.count('divorced') / len(pairs) < 0.3
    assert set(older) == {'married', 'separated'} and older.count('separated') / len(pairs) < 0.07
    assert circle.ties_text([{'name': 'Rui', 'how': 'separated'}]) == 'Separated from Rui.'


def test_an_older_citys_circle_says_its_parents_separated(client, monkeypatch):
    monkeypatch.setattr(circle, 'OLDER_PARTED', 1.0)
    response = client.post('/api/companion', json={'name': 'Ellis Hart', 'timezone': 'Europe/London',
                                                   'home_city': 'london-1895', 'identity': '29. A clerk.',
                                                   'relationship': 'friendship'})
    assert response.status_code == 200, response.text
    client.put('/api/life/settings', json={'circle_size': 12})
    people = client.get('/api/life/circle').json()
    parents = [person for person in people if circle.role_kind(person['role']) == 'parent']
    hows = {item['how'] for person in parents for item in person['knows'] if item['id'] in {p['id'] for p in parents}}
    assert len(parents) >= 2 and hows == {'separated'}


def test_the_grandparent_never_shares_a_first_name_with_someone_in_the_circle(client):
    make(client, 'Warm and curious.', identity='30.')
    world = client.app.state.life.world
    with client.app.state.database.connect() as connection:
        companion = current(connection)
    definition, timeline_id = companion['version']['definition'], companion['active_timeline_id']
    first = circle.grandparent(definition, world, timeline_id, 30, set())
    given = first['details']['full_name'].split()[0]
    again = circle.grandparent(definition, world, timeline_id, 30, {given, 'Someone Else'})
    assert again['details']['full_name'].split()[0] != given and again['name'] != first['name']


def test_an_employer_ending_in_a_full_stop_ends_the_line_once():
    from companion.memory.context import person_text
    person = {'name': 'Jane Hart', 'role': 'mother', 'career': 'Bank clerk', 'employer': 'Coutts and Co.'}
    assert person_text(person) == '- Jane Hart (mother): Bank clerk at Coutts and Co.'
    assert person_text({**person, 'local': False}) == \
        '- Jane Hart (mother): Bank clerk at Coutts and Co. Lives out of town.'
    assert person_text({**person, 'employer': 'Guy\'s Hospital'}) == "- Jane Hart (mother): Bank clerk at Guy's Hospital."
