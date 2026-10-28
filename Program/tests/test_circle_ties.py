"""How people in the circle stand with the companion and with each other: where someone added by hand starts
(companion/memory/pairs.py word_start), friends by chance never family (companion/life/circle.py tie), and the user's
own word on how two of them know each other (circle.set_tie)."""
from companion.life import circle
from companion.memory import pairs


def companion(client):
    response = client.post('/api/companion', json={'name': 'Sett', 'timezone': 'America/New_York',
                                                    'home_city': 'baltimore', 'relationship': 'friendship'})
    assert response.status_code == 200, response.text


def add(client, **person):
    response = client.post('/api/life/circle/people', json=person)
    assert response.status_code == 200, response.text
    return response.json()


def test_the_words_of_a_role_and_note_say_where_they_start():
    assert pairs.word_start('rival', 'A pit fighter who has competed against Sett for years.') == 3
    assert pairs.word_start('enthusiastic fangirl', 'Regular spectator and unabashed admirer.') == 2
    assert pairs.word_start('self-proclaimed girlfriend', "She believes they're destined, although they've never "
                                                          'met.') == 1
    assert pairs.word_start('stranger') == 1
    assert pairs.word_start('the baker', 'Makes good bread.') is None
    # A role the defaults know keeps its default, whatever the note says.
    assert pairs.role_default('close friend', 'seed', 'never met')['default'] == 4
    assert pairs.role_default('rival', 'seed', 'for years')['level'] == 3


def test_people_added_by_hand_start_where_their_words_say(client):
    companion(client)
    rival = add(client, name='Kaito', role='rival', note='A pit fighter who has competed against Sett for years.')
    fan = add(client, name='Nari', role='enthusiastic fangirl', note='Regular spectator who rarely misses a fight.')
    stranger = add(client, name='Amaya', role='self-proclaimed girlfriend', note="They've never met.")
    stages = {person['name']: person['stage']['their_level'] for person in client.get('/api/life/circle').json()
              if person['name'] in ('Kaito', 'Nari', 'Amaya')}
    assert stages == {'Kaito': 3, 'Nari': 2, 'Amaya': 1}
    # The user says otherwise on their card; 0 is the app's pick again.
    def amaya(start):
        response = client.put(f"/api/life/circle/{stranger['id']}/about", json={'start_stage': start})
        assert response.status_code == 200, response.text
        return next(person for person in client.get('/api/life/circle').json() if person['name'] == 'Amaya')
    assert amaya(2)['stage']['their_level'] == 2
    found = amaya(0)
    assert found['stage']['their_level'] == 1 and 'start_stage' not in found
    assert rival['id'] and fan['id']


def test_friends_by_chance_are_never_family():
    mom = {'id': 'm', 'seed': 'circle:t:0', 'role': 'mom', 'details': '{}'}
    for index in range(200):
        other = {'id': f'o{index}', 'seed': f'circle:t:{index + 1}', 'role': 'rival', 'details': '{}'}
        assert circle.tie(mom, other) is None
    friends = [circle.tie({'id': 'a', 'seed': 's', 'role': 'friend', 'details': '{}'},
                          {'id': f'b{index}', 'seed': f's{index}', 'role': 'rival', 'details': '{}'})
               for index in range(200)]
    assert 'friends' in friends


def test_the_user_says_how_two_people_know_each_other(client):
    companion(client)
    kaito = add(client, name='Kaito', role='rival')
    amaya = add(client, name='Amaya', role='fan')
    for how, shown in (('rivals', 'rivals'), ('', None)):
        response = client.put(f"/api/life/circle/{kaito['id']}/ties", json={'other_id': amaya['id'], 'how': how})
        assert response.status_code == 200, response.text
        people = {person['name']: person for person in client.get('/api/life/circle').json()}
        knows = {item['name']: item['how'] for item in people['Kaito']['knows']}
        assert knows.get('Amaya') == shown
        assert {item['name']: item['how'] for item in people['Amaya']['knows']}.get('Kaito') == shown
    # None hands it back to the app; someone outside the circle or the person themself is refused.
    response = client.put(f"/api/life/circle/{kaito['id']}/ties", json={'other_id': amaya['id'], 'how': None})
    assert response.status_code == 200 and 'own_ties' not in response.json()
    assert client.put(f"/api/life/circle/{kaito['id']}/ties", json={'other_id': kaito['id'], 'how': 'friends'}
                      ).status_code == 422
    assert client.put(f"/api/life/circle/{kaito['id']}/ties", json={'other_id': amaya['id'], 'how': 'besties'}
                      ).status_code == 422


def test_a_new_name_carries_into_their_note(client):
    companion(client)
    person = add(client, name='Rokan', role='rival', note='Rokan is a seasoned pit fighter.')
    edited = client.put(f"/api/life/circle/{person['id']}/about", json={'name': 'Kaito'}).json()
    assert edited['note'] == 'Kaito is a seasoned pit fighter.'
