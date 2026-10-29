"""How people in the circle stand with the companion and with each other: where someone added by hand starts
(companion/memory/pairs.py word_start), friends by chance never family (companion/life/circle.py tie), and the user's
own word on how two of them know each other (circle.set_tie)."""
import json
from datetime import date, timedelta
from types import SimpleNamespace

from companion.database import one
from companion.life import agenda, circle
from companion.memory import context, pairs


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
    # The user says otherwise on their card; 0 is the app's pick again. Amaya has never met Sett, so until the user
    # says they know each other there is nothing between them.
    def amaya(**change):
        response = client.put(f"/api/life/circle/{stranger['id']}/about", json=change)
        assert response.status_code == 200, response.text
        return next(person for person in client.get('/api/life/circle').json() if person['name'] == 'Amaya')
    assert amaya(start_stage=2)['stage']['their_level'] == 1
    assert amaya(knowing='both')['stage']['their_level'] == 2
    found = amaya(start_stage=0)
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


def test_someone_never_met_knows_the_companion_one_way():
    def person(role, note=''):
        return {'role': role, 'details': json.dumps({'note': note} if note else {})}
    assert circle.knowing(person('self-proclaimed girlfriend', "An obsessive fangirl, although they've never met.")) \
        == 'they'
    assert circle.knowing(person('admirer', 'Admires him from afar.')) == 'they'
    assert circle.knowing(person('famous singer', "They haven't met; Sett plays her records.")) == 'companion'
    assert circle.knowing(person('stranger')) == 'companion'
    # Someone they know, family whatever the note says, and the user's own pick.
    assert circle.knowing(person('enthusiastic fangirl', 'Regular spectator who rarely misses a fight.')) == 'both'
    assert circle.knowing(person('mom', 'She never met her own father.')) == 'both'
    assert circle.knowing({'role': 'stranger', 'details': json.dumps({'knowing': 'both'})}) == 'both'


def test_one_sided_people_stay_out_of_the_companions_days_and_say_so_in_chat(client):
    companion(client)
    fan = add(client, name='Amaya', role='self-proclaimed girlfriend', note="An obsessive fangirl; they've never met.")
    star = add(client, name='Lio', role='singer', note='A friend.', knowing='companion')
    people = {person['name']: person for person in client.get('/api/life/circle').json()}
    assert people['Amaya']['knowing'] == 'they' and not people['Amaya']['knowing_set']
    assert people['Lio']['knowing'] == 'companion' and people['Lio']['knowing_set']
    assert context.person_text({**people['Amaya'], 'career': '', 'employer': ''}).count(
        "They know who you are, but you don't know them.") == 1
    assert "You know of them, but they don't know you." in context.person_text({**people['Lio'], 'career': ''})
    database = client.app.state.database
    with database.connect() as connection:
        timeline_id = one(connection, 'SELECT timeline_id FROM circle_people WHERE id=?', (fan['id'],))['timeline_id']
        slot = SimpleNamespace(local_date=date(2026, 3, 3), starts_at=database.clock.now(),
                               ends_at=database.clock.now() + timedelta(hours=1))
        free = {person['id'] for person in agenda.free_people(connection, timeline_id, slot)}
    assert fan['id'] not in free and star['id'] not in free
    # Back to the app's pick, then the user says they know each other.
    response = client.put(f"/api/life/circle/{star['id']}/about", json={'knowing': ''})
    assert response.status_code == 200 and response.json()['knowing'] == 'both' and not response.json()['knowing_set']
    response = client.put(f"/api/life/circle/{fan['id']}/about", json={'knowing': 'both'})
    assert response.status_code == 200
    people = {person['name']: person for person in client.get('/api/life/circle').json()}
    assert people['Amaya']['knowing'] == 'both' and people['Lio']['knowing'] == 'both'


def test_two_people_in_the_circle_can_know_each_other_one_way(client):
    companion(client)
    kaito = add(client, name='Kaito', role='rival')
    nari = add(client, name='Nari', role='fan')
    response = client.put(f"/api/life/circle/{nari['id']}/ties", json={'other_id': kaito['id'], 'how': 'knows of'})
    assert response.status_code == 200, response.text
    people = {person['name']: person for person in client.get('/api/life/circle').json()}
    assert {item['name']: item['how'] for item in people['Nari']['knows']}['Kaito'] == 'knows of'
    assert {item['name']: item['how'] for item in people['Kaito']['knows']}['Nari'] == 'known by'
    def told(name, other):
        return circle.ties_text([item for item in people[name]['knows'] if item['name'] == other])
    assert told('Nari', 'Kaito') == "Knows of Kaito, who doesn't know them."
    assert told('Kaito', 'Nari') == "Nari knows of them; they don't know Nari."
    # Said from the other card, it turns around.
    response = client.put(f"/api/life/circle/{nari['id']}/ties", json={'other_id': kaito['id'], 'how': 'known by'})
    people = {person['name']: person for person in client.get('/api/life/circle').json()}
    assert {item['name']: item['how'] for item in people['Kaito']['knows']}['Nari'] == 'knows of'
