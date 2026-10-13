"""Pets with lives of their own (companion/life/pets.py)."""
import json
from datetime import date, timedelta

import pytest
from conftest import send, set_life, show

from companion import moods
from companion.characters import require_current
from companion.images import prompts
from companion.life import home, pets, trips
from companion.world import life_details
from companion.world.source import CatalogWorld

MIRA = {'name': 'Mira', 'interests': ['vinyl records'], 'location': 'Fells Point, Baltimore',
        'timezone': 'America/New_York', 'background': 'Mira lives with a ginger cat named Biscuit.'}
NOW = date(2026, 10, 5)


@pytest.fixture
def mira(client):
    response = client.post('/api/companion', json=MIRA)
    assert response.status_code == 200, response.text
    return response.json()


def connect(client, write=True):
    return client.app.state.database.connect(write=write)


def timeline(client) -> str:
    with connect(client, False) as connection:
        return connection.execute('SELECT active_timeline_id FROM companions').fetchone()[0]


def biscuit(born: date, lifespan: int = 15 * 365, era='modern', kind='cat') -> dict:
    return pets.pet('test:biscuit', 'Biscuit', kind, 'a small orange tabby with a white bib', born, NOW, era, lifespan)


def test_the_bank_is_big_and_specific():
    data = pets.bank()
    for key in ('looks', 'sick', 'vet', 'home', 'photos'):
        assert len(data[key]) >= 100, key
    assert len(data['names']['modern']) >= 100 and len(data['names']['period']) >= 100
    assert set(data['townsfolk']) == {item['id'] for item in life_details.bank()['pets']}
    # Pictures use visible wording only: no illness or injury in what a photo shows.
    for shot in data['photos']:
        assert not any(word in shot['shows'] for word in ('sick', 'injur', 'wound', 'blood', 'limp', 'scar'))


def test_pets_suit_the_city_era_and_stay_the_same_for_the_same_seed():
    first = pets.draw('seed', 'pet', 'modern', NOW)
    assert pets.draw('seed', 'pet', 'modern', NOW) == first
    kinds = {pets.draw(f'seed{n}', 'pet', 'medieval', NOW)['variety'] for n in range(300)}
    assert kinds <= {'cat', 'dog', 'rabbit', 'tortoise', 'ferret', 'chickens', 'horse'} and {'cat', 'dog'} <= kinds
    modern = {pets.draw(f'seed{n}', 'pet', 'modern', NOW)['variety'] for n in range(600)}
    assert {'hamster', 'fish', 'lizard'} <= modern and 'horse' in modern  # common pets and a few rare ones
    born = date.fromisoformat(first['details']['born'])
    assert born < NOW and first['details']['lifespan_days'] > 365


def test_a_life_is_the_same_lived_in_steps_or_at_once(client, mira, clock):
    found = biscuit(NOW - timedelta(days=12 * 365))
    end = NOW + timedelta(days=700)
    with connect(client) as connection:
        set_realism(connection, 3, True)
        pets.evolve(connection, found, end, clock.now())
        once = [(row['local_date'], row['kind'], row['text']) for row in pets.log(connection, found['key'], NOW, end)]
        connection.execute('DELETE FROM pet_log')
        connection.execute('DELETE FROM pet_state')
        for step in range(0, 701, 50):
            pets.evolve(connection, found, NOW + timedelta(days=step), clock.now())
        steps = [(row['local_date'], row['kind'], row['text']) for row in pets.log(connection, found['key'], NOW, end)]
    assert once and once == steps
    assert {kind for _day, kind, _text in once} & {'sick', 'checkup'}


def set_realism(connection, level: int, can_die: bool):
    connection.execute('UPDATE life_settings SET pets_realism=?, pets_can_die=? WHERE id=1', (level, int(can_die)))


def test_old_pets_die_unless_the_realism_tab_says_otherwise(client, mira, clock):
    old = biscuit(NOW - timedelta(days=15 * 365 - 10))
    with connect(client) as connection:
        set_realism(connection, 2, False)
        pets.evolve(connection, {**old, 'key': 'test:spared'}, NOW + timedelta(days=400), clock.now())
        assert pets.died_on(connection, 'test:spared') is None
        set_realism(connection, 2, True)
        pets.evolve(connection, old, NOW + timedelta(days=400), clock.now())
        died = pets.died_on(connection, old['key'])
        assert died is not None and died <= NOW + timedelta(days=11)
        assert pets.status_on(connection, old, NOW + timedelta(days=30))['state'] == 'died'
        set_realism(connection, 0, True)
        young = {**biscuit(NOW - timedelta(days=400)), 'key': 'test:young'}
        pets.evolve(connection, young, NOW + timedelta(days=700), clock.now())
        assert not pets.log(connection, young['key'], NOW, NOW + timedelta(days=700))


def test_a_young_pet_never_dies_of_illness(client, mira, clock):
    with connect(client) as connection:
        set_realism(connection, 3, True)
        for n in range(20):
            found = {**biscuit(NOW - timedelta(days=365)), 'key': f'test:young{n}'}
            pets.evolve(connection, found, NOW + timedelta(days=3 * 365), clock.now())
            assert pets.died_on(connection, found['key']) is None


def test_the_companion_pets_live_on_the_pets_panel(client, mira, clock):
    data = client.get('/api/life/pets').json()
    assert [pet['name'] for pet in data['pets']] == ['Biscuit'] and data['pets'][0]['kind'] == 'cat'
    assert data['pets'][0]['health'] is None and data['numbers'] is False
    show(client, show_home_meters=True)
    assert client.get('/api/life/pets').json()['pets'][0]['health'] > 0
    added = client.post('/api/life/pets', json={'name': 'Pickle', 'kind': 'guinea-pig', 'looks': 'a ginger guinea pig',
                                                     'age': 2})
    assert added.status_code == 200, added.text
    pickle = next(pet for pet in added.json()['pets'] if pet['name'] == 'Pickle')
    assert pickle['age'] == '2 years old'
    assert client.patch(f"/api/life/pets/{pickle['id']}", json={'age': 4}).json()['pets'][-1]['age'] == '4 years old'
    assert client.post('/api/life/pets', json={'name': 'Smaug', 'kind': 'dragon'}).status_code == 422
    renamed = client.patch(f"/api/life/pets/{pickle['id']}", json={'name': 'Pickles'}).json()
    assert 'Pickles' in [pet['name'] for pet in renamed['pets']]
    gone = client.post(f"/api/life/pets/{pickle['id']}/remove").json()
    assert 'Pickles' not in [pet['name'] for pet in gone['pets']] and not gone['remembered']


def test_a_pet_that_died_is_remembered_and_can_be_brought_back(client, mira, clock):
    client.get('/api/life/pets')
    tid = timeline(client)
    with connect(client) as connection:
        found = pets.of_home(connection, tid)[0]
        connection.execute("INSERT INTO pet_log (id, pet_key, local_date, kind, text, created_at) VALUES "
                           "('d1', ?, '2026-10-04', 'died', 'of old age', '2026-10-04')", (found['key'],))
        connection.execute("UPDATE home_items SET until='2026-10-05' WHERE id=?", (found['item_id'],))
        lines = home.context_lines(connection, tid, NOW)
    data = client.get('/api/life/pets').json()
    assert not data['pets'] and data['remembered'][0]['name'] == 'Biscuit'
    assert data['remembered'][0]['state'] == 'died'
    assert any('cat Biscuit died of old age' in line for _id, line in lines)
    back = client.post(f"/api/life/pets/{found['item_id']}/restore").json()
    assert back['pets'][0]['name'] == 'Biscuit' and back['pets'][0]['state'] != 'died'
    with connect(client, False) as connection:
        assert pets.of_home(connection, tid)[0]['spared']


def test_vet_visits_cost_money_and_feed_life_admin(client, mira, clock):
    client.get('/api/life/pets')
    tid = timeline(client)
    with connect(client) as connection:
        found = pets.of_home(connection, tid)[0]
        connection.execute("INSERT INTO pet_log (id, pet_key, local_date, kind, text, spend, created_at) VALUES "
                           "('v1', ?, '2026-10-06', 'vet', 'an ear infection', '$$', '2026-10-05')", (found['key'],))
        visits = pets.vet_visits(connection, tid, NOW, NOW + timedelta(days=7))
        bought = home.purchases(connection, tid, NOW, NOW + timedelta(days=7))
    assert visits == [{'date': '2026-10-06', 'pet': 'Biscuit', 'variety': 'cat', 'reason': 'an ear infection',
                       'kind': 'vet', 'pet_id': found['item_id'], 'movable': False}]
    assert any(item['text'] == 'took Biscuit to the vet for an ear infection' and item['spend'] == '$$'
               for item in bought)


def test_pet_news_is_woven_into_their_day_once(client, mira, clock):
    client.get('/api/life/pets')
    tid = timeline(client)
    with connect(client) as connection:
        found = pets.of_home(connection, tid)[0]
        connection.execute("INSERT INTO pet_log (id, pet_key, local_date, kind, until, text, created_at) VALUES "
                           "('s1', ?, '2026-10-06', 'sick', '2026-10-09', 'an upset stomach', '2026-10-05')",
                           (found['key'],))
        news = pets.untold(connection, tid, date(2026, 10, 6), 'Mira')
        entry = home.woven({'summary': 'Mira stayed in.', 'activity': 'slow'}, news['sentence'], [news['item']], None,
                           news['extra'])
        assert entry['summary'] == ('Mira stayed in. Biscuit was poorly with an upset stomach, so Mira kept a close '
                                    'eye on them.')
        assert entry['home']['pet_event'] == 's1'
        status = pets.status_on(connection, found, date(2026, 10, 7))
        assert status == {'state': 'sick', 'text': 'Biscuit is under the weather: an upset stomach.', 'serious': False}
        assert pets.at_home(connection, found, date(2026, 10, 7), 'x', 'Mira').startswith('Biscuit rested')
        assert pets.sick_today(connection, tid, date(2026, 10, 7)) == {'Biscuit'}


def test_pet_only_photos_show_just_the_pet():
    found = biscuit(NOW - timedelta(days=900))
    shots = [shot for n in range(40) if (shot := pets.photo(found, f's{n}'))]
    assert shots and all(shot['caption'] and '{' not in shot['caption'] for shot in shots)
    prompt = pets.photo_prompt(found, shots[0]['shows'], '')
    assert 'a small orange tabby with a white bib (cat)' in prompt and 'Nobody in focus' in prompt


def test_someone_minds_the_pets_on_a_trip():
    trip = {'id': 't1'}
    cat = biscuit(NOW - timedelta(days=900))
    assert pets.minder(cat, trip, [{'name': 'Ada'}])['text'] == 'Biscuit is being fed by Ada'
    assert pets.minder(cat, trip, [])['how'] == 'sitter'
    fish = {**cat, 'kind': 'fish'}
    assert pets.minder(fish, trip, [])['how'] == 'none'
    dogs = [pets.minder({**cat, 'kind': 'dog', 'key': f'dog{n}'}, trip, [])['how'] for n in range(40)]
    assert 'along' in dogs and 'sitter' in dogs
    assert trips.care_text([{'text': 'Biscuit is being fed by Ada'}, {'text': ''}]) == 'Biscuit is being fed by Ada'


def test_circle_members_and_townsfolk_have_their_own_pets(client, mira):
    people = client.get('/api/life/circle').json()
    assert all('pets' in person for person in people)
    owning = [pets.circle_pets({'id': f'p{n}'}, 'modern', NOW) for n in range(40)]
    assert 8 < sum(1 for found in owning if found) < 32
    again = client.get('/api/life/circle').json()
    assert [person['pets'] for person in people] == [person['pets'] for person in again]
    data = CatalogWorld().find('baltimore')
    sheet = {'key': 'town:baltimore:x:1', 'cast': None}
    owners = 0
    for n in range(40):
        sheet = {'key': f'town:baltimore:x:{n}'}
        identity = life_details.pet_identity(f'seed{n}')
        found = pets.town_pets(sheet, identity, pets.era_of(data))
        if found:
            owners += 1
            assert found[0]['name'] == identity[1]
    assert owners > 5


def test_the_user_pets_are_their_own_words_with_lives(client, provider, connected):
    listing = client.get('/api/worlds').json()
    persona = listing['persona']
    saved = client.patch(f"/api/worlds/personas/{persona['id']}",
                         json={'name': 'Sam', 'pets': [{'name': 'Miso', 'kind': 'dog', 'looks': 'a scruffy terrier',
                                                        'age': 4}]})
    assert saved.status_code == 200, saved.text
    pet = client.get('/api/worlds').json()['persona']['pets'][0]
    assert pet['name'] == 'Miso' and pet['born'] < '2022-10-05' and pet['added'] == '2026-10-05'
    yours = client.get('/api/life/pets').json()['yours']
    assert yours[0]['name'] == 'Miso' and yours[0]['age'] == '4 years old'
    send(client, 'Hey!', 'pets-message-1')
    assert 'Pets: Miso (dog: a scruffy terrier, 4 years old)' in provider.requests[-1]['prompt']


def test_a_tracked_pet_wins_over_what_they_said(client, mira):
    client.get('/api/life/pets')
    tid = timeline(client)
    from companion import self_facts
    with connect(client, False) as connection:
        tracked = self_facts.tracked_pets(connection, tid)
    assert tracked == {'biscuit'}
    row = {'category': 'pet', 'value': 'Biscuit', 'subject': 'cat'}
    assert self_facts.pet_link(row, tracked) == 'tracked'
    assert self_facts.pet_link({**row, 'value': 'Luna'}, tracked) == 'untracked'
    assert pets.kind_for_word('kitten') == 'cat' and pets.kind_for_word('dragon') == 'cat'


def test_realism_settings_round_trip(client):
    data = set_life(client, pets_realism=1, pets_can_die=False)
    assert data['pets_realism'] == 1 and data['pets_can_die'] is False
    assert client.put('/api/life/settings', json={'pets_realism': 4}).status_code == 422


def test_an_added_pet_without_an_age_fits_its_looks_and_ages_read_in_years():
    old = date.fromisoformat(pets.age_from_looks('an elderly grey tabby with a torn ear', 'cat', NOW))
    assert (NOW - old).days > 8 * 365
    assert (NOW - date.fromisoformat(pets.age_from_looks('a fluffy kitten', 'cat', NOW))).days < 365
    assert pets.age_from_looks('a sleek black cat', 'cat', NOW) is None
    assert pets.age_text(NOW - timedelta(days=400), NOW) == '1 year old'
    assert pets.age_text(NOW - timedelta(days=200), NOW) == '6 months old'


def test_a_pet_that_died_today_is_remembered_not_listed_as_theirs(client, mira, clock):
    client.get('/api/life/pets')
    tid = timeline(client)
    with connect(client) as connection:
        found = pets.of_home(connection, tid)[0]
        # The home keeps it through the day it died: `until` is the day after.
        connection.execute("INSERT INTO pet_log (id, pet_key, local_date, kind, text, created_at) VALUES "
                           "('d1', ?, ?, 'died', 'of old age', '2026-10-04')", (found['key'], NOW.isoformat()))
        connection.execute('UPDATE home_items SET until=? WHERE id=?', ((NOW + timedelta(days=1)).isoformat(),
                                                                         found['item_id']))
        lines = [line for _id, line in home.context_lines(connection, tid, NOW)]
        assert pets.at_home(connection, found, NOW, 'x', 'Mira') is None
    data = client.get('/api/life/pets').json()
    assert not data['pets'] and [pet['name'] for pet in data['remembered']] == ['Biscuit']
    assert not any(line.startswith('- Pet: Biscuit') for line in lines)
    assert any('cat Biscuit died of old age' in line for line in lines)


def test_changing_the_pets_settings_relives_only_the_days_ahead(client, mira, clock):
    client.get('/api/life/pets')
    tid = timeline(client)
    ahead, past = NOW + timedelta(days=3), NOW - timedelta(days=1)
    with connect(client) as connection:
        found = pets.of_home(connection, tid)[0]
        # Their agenda is planned a few days ahead, and their pet's life with it.
        connection.execute("INSERT INTO pet_log (id, pet_key, local_date, kind, until, text, created_at) VALUES "
                           "('s1', ?, ?, 'sick', ?, 'an upset stomach', '2026-10-04')",
                           (found['key'], past.isoformat(), NOW.isoformat()))
        connection.execute("INSERT INTO pet_log (id, pet_key, local_date, kind, text, created_at) VALUES "
                           "('d1', ?, ?, 'died', 'of old age', '2026-10-04')", (found['key'], ahead.isoformat()))
        connection.execute('UPDATE home_items SET until=? WHERE id=?', ((ahead + timedelta(days=1)).isoformat(),
                                                                         found['item_id']))
        connection.execute('INSERT INTO pet_state (pet_key, through) VALUES (?, ?) ON CONFLICT (pet_key) DO UPDATE '
                           'SET through=excluded.through', (found['key'], (NOW + timedelta(days=7)).isoformat()))
        connection.execute("INSERT INTO life_agenda (id, timeline_id, subject, slot_key, starts_at, ends_at, local_date, "
                           "block, entry, basis, created_at) VALUES ('a1', ?, 'companion', 'evening@x', '', '', ?, "
                           "'evening', ?, 'test', '')", (tid, ahead.isoformat(),
                                                       '{"summary": "Mira said goodbye to Biscuit.", "home": '
                                                       '{"pet_event": "d1"}}'))
    set_life(client, pets_can_die=False)
    with connect(client, False) as connection:
        assert pets.died_on(connection, found['key']) is None
        assert [row['id'] for row in pets.log(connection, found['key'], past, NOW + timedelta(days=7))] == ['s1']
        assert connection.execute('SELECT through FROM pet_state WHERE pet_key=?',
                                  (found['key'],)).fetchone()[0] <= NOW.isoformat()
        assert pets.of_home(connection, tid, ahead + timedelta(days=2))
        assert not connection.execute("SELECT id FROM life_agenda WHERE id='a1'").fetchall()


def test_older_eras_get_no_modern_breeds_or_pet_lines():
    modern = ('pug', 'border collie', 'dachshund', 'dog park', 'squeaky toy', 'zoomies', 'cat television')
    seen = [pets.looks_for(f'seed{n}', 'pet', 'dog', 'medieval') for n in range(300)]
    seen += [pets.moment({'name': 'Rex', 'kind': kind, 'era': 'medieval'}, f'seed{n}') or ''
             for n in range(300) for kind in ('dog', 'cat')]
    assert not [line for line in seen if any(word in line for word in modern)]


def test_checkup_reasons_need_no_history_and_age_talk_waits_for_old_age():
    texts = {item['text'] for item in pets.bank()['vet']}
    assert not [text for text in texts if any(word in text for word in ('stitches', 'last month', 'last sick',
                                                                        'broken tooth', 'recheck', 'refill'))]
    assert 'a Lyme disease test' in texts
    young = biscuit(NOW - timedelta(days=2 * 365))
    old = biscuit(NOW - timedelta(days=14 * 365))
    said = {pets.vet_entry(young, NOW + timedelta(days=n)) for n in range(400)}
    assert not [text for text in said if 'older' in text or 'senior' in text]
    assert any('older' in pets.vet_entry(old, NOW + timedelta(days=n)) for n in range(400))


def test_a_sitter_costs_money_even_on_a_free_trip_and_a_trip_ahead_reads_as_a_plan(client, mira, clock,
                                                                                    monkeypatch):
    client.get('/api/life/pets')
    tid = timeline(client)
    monkeypatch.setattr(trips, 'local_people', lambda connection, timeline_id: [])
    start = NOW + timedelta(days=3)
    with connect(client) as connection:
        companion_id = connection.execute('SELECT id FROM companions').fetchone()[0]
        connection.execute("INSERT INTO trips (id, companion_id, timeline_id, start_date, end_date, city_id, city_name, "
                           "kind, cost, created_at) VALUES ('t1', ?, ?, ?, ?, 'chicago', 'Chicago', 'family', 0, '')",
                           (companion_id, tid, start.isoformat(), (start + timedelta(days=2)).isoformat()))
        bought = trips.purchases(connection, tid, NOW, start)
    assert [item['text'] for item in bought] == ['paid someone to look after Biscuit during the trip']
    with connect(client, False) as connection:
        lines = [text for _id, text in trips.context_lines(connection, require_current(connection), clock.now())]
    assert '- While you are away: Biscuit will be with a paid sitter.' in lines, lines
    dog = {**biscuit(NOW), 'kind': 'dog'}
    along = [pets.minder({**dog, 'key': f'd{n}'}, {'id': 't1'}, [], ahead=True)['text'] for n in range(20)]
    assert 'Biscuit is coming along' in along and 'Biscuit came along' not in along


def test_add_a_pet_offers_the_kinds_of_the_city_era_and_the_ones_they_have(client, mira):
    modern = [kind['id'] for kind in client.get('/api/life/pets').json()['kinds']]
    assert {'hamster', 'snake', 'horse'} <= set(modern)
    with connect(client) as connection:
        connection.execute("UPDATE home_state SET era='medieval'")
    medieval = [kind['id'] for kind in client.get('/api/life/pets').json()['kinds']]
    assert 'horse' in medieval and 'cat' in medieval and not {'hamster', 'snake', 'lizard', 'fish'} & set(medieval)
    client.post('/api/life/pets', json={'name': 'Nibbles', 'kind': 'hamster'})
    assert 'hamster' in [kind['id'] for kind in client.get('/api/life/pets').json()['kinds']]


def test_a_death_on_a_day_already_drawn_is_still_told_and_weighs_on_their_mood(client, mira, clock):

    today = client.get('/api/life/pets').json()['today']
    tid = timeline(client)
    with connect(client) as connection:
        connection.execute("INSERT INTO life_agenda (id, timeline_id, subject, slot_key, starts_at, ends_at, local_date, "
                           "block, entry, basis, created_at) VALUES ('a1', ?, 'companion', 'evening@x', '', '', ?, "
                           "'evening', ?, 'test', '')", (tid, today, '{"summary": "Mira read at home.", '
                                                                      '"activity": "reading"}'))
    added = client.post('/api/life/pets', json={'name': 'Old Tom', 'kind': 'cat', 'looks': 'a gray tabby', 'age': 25})
    assert [pet['name'] for pet in added.json()['remembered']] == ['Old Tom']
    with connect(client, False) as connection:
        entry = json.loads(connection.execute("SELECT entry FROM life_agenda WHERE id='a1'").fetchone()[0])
        feelings = moods.day_moods(connection, require_current(connection), clock.now())
    assert entry['summary'] == 'Mira read at home. Mira said goodbye to Old Tom, who died of old age.'
    assert entry['mood'] == 'heartbroken' and entry['home']['pet_event']
    assert ('sad', 2) in [(mood['feeling'], mood['intensity']) for mood in feelings if 'Old Tom died' in mood['reason']]


@pytest.mark.parametrize('era', ['modern', 'jazz-age', 'victorian', 'steampunk', 'frontier', 'medieval', 'fantasy'])
def test_every_era_has_a_hundred_entries_per_kind_of_line(era):
    data = pets.bank()
    for key in ('looks', 'sick', 'vet', 'home', 'walks', 'photos'):
        fitting = [item for item in data[key] if pets.fits(item, None, era) and not item.get('out')]
        assert len(fitting) >= 100, (era, key)


def test_photos_at_home_are_never_taken_outdoors_and_suit_the_home():
    plumbed = ('sink', 'counter', 'cardboard', 'laptop', 'mail')
    for era in ('modern', 'medieval'):
        for kind in ('dog', 'cat', 'rabbit', 'tortoise'):
            found = {**biscuit(NOW - timedelta(days=900), era=era, kind=kind)}
            shows = {pets.photo(found, f's{n}')['shows'] for n in range(300)}
            outdoor = {item['shows'] for item in pets.bank()['photos'] if item.get('out')}
            assert shows and not shows & outdoor
            assert era == 'modern' or not [text for text in shows if any(word in text for word in plumbed)]
    assert {'splashing through a shallow stream', 'surrounded by fall leaves in a park'} <= outdoor
    lines = {pets.moment({'name': 'Rex', 'kind': 'dog', 'era': 'medieval'}, f's{n}') for n in range(300)}
    assert not [line for line in lines if 'mail' in line]


def test_a_digest_of_several_moments_is_not_drawn_as_a_pet_photo(client, mira):
    client.get('/api/life/pets')
    with connect(client) as connection:
        tid = timeline(client)
        found = pets.of_home(connection, tid)[0]
        event = {'moment': {'pet_photo': {'item': found['item_id'], 'shows': 'curled up on a blanket'}}}
        settings = {'style': ''}
        assert 'curled up on a blanket' in prompts.pet_prompt(connection, tid, [event], settings)
        assert prompts.pet_prompt(connection, tid, [event, {'moment': {}}], settings) == ''
