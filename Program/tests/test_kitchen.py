"""Kitchen and food (companion/life/kitchen.py): how they cook and eat, the nightly rhythm, the pantry, and dinner at
their place."""
from contextlib import contextmanager
from datetime import date, timedelta

import pytest
from conftest import reconcile, send, set_life, show

from companion.database import decode
from companion.life import body, composer, kitchen, money, openers, outings
from companion.providers.chat import Chunk
from companion.world import catalog
from companion.world.source import CatalogWorld

WORLD = CatalogWorld()
TODAY = date(2026, 10, 5)  # A Monday.
EVENINGS = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00', 'days': [0, 1, 2, 3, 4]},
            {'key': 'evening', 'label': 'Evening', 'kind': 'leisure', 'start': '17:00', 'end': '23:00'},
            {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]


def found(definition, city='baltimore', seed='kitchen:t1'):
    return kitchen.profile(seed, definition, WORLD.find(city))


def test_each_city_cooks_from_its_own_era_and_cuisine():
    expected = {'baltimore': 'modern-us', 'london': 'modern-uk', 'osaka': 'modern-japan', 'jeju': 'modern-korea',
                'new-york-1925': 'jazz-age-us', 'pellmouth': 'jazz-age-us', 'london-1895': 'victorian-uk',
                'calderwick': 'victorian-uk', 'camelot': 'medieval', 'whitlock': 'frontier-us',
                'ellerbruck': 'old-world', 'grandport': 'old-world', 'emerald-city': 'old-world'}
    assert {city: kitchen.bank_for(WORLD.find(city)) for city in expected} == expected
    assert kitchen.bank_for({'era': 'modern', 'country': 'France'}) == 'modern-world'
    assert kitchen.bank_for(None) == 'modern-us'


def test_who_they_are_decides_how_they_eat_and_cook():
    vegan = found({'name': 'Ash', 'identity': 'A vegan barista who is allergic to peanuts.'})
    assert vegan['diet'] == 'vegan' and vegan['avoids'] == ['nuts']
    chef = found({'name': 'Rio', 'identity': 'They work as a line cook.', 'money': {'career': 'line-cook'}})
    assert chef['skill'] == 3
    hopeless = found({'name': 'Tam', 'identity': "They can't cook and live on takeout."})
    assert hopeless['skill'] == 0
    kosher = found({'name': 'Eli', 'identity': 'They keep kosher.'})
    assert set(kosher['avoids']) == {'pork', 'shellfish'}
    assert found({'name': 'Ash', 'identity': 'A barista.'}) == found({'name': 'Ash', 'identity': 'A barista.'})
    assert len({tuple(found({'name': 'Kim'}, seed=f'k{n}')['favorites']) for n in range(6)}) > 1


def test_dishes_keep_to_their_diet_and_what_they_avoid():
    me = {**found({'name': 'Ash', 'identity': 'A vegetarian, allergic to nuts.'}), 'skill': 3}
    options = kitchen.dishes_for(me)
    assert options and all(dish['tags'] & {'vegan', 'veg'} and 'nuts' not in dish['tags'] for dish in options)
    assert all(dish['skill'] <= 1 for dish in kitchen.dishes_for({**me, 'skill': 0}))


@pytest.fixture
def kim(client, monkeypatch, provider):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(composer, 'PLAN_SHARE', 0)
    monkeypatch.setattr(composer, 'THREAD_SHARE', 0)
    monkeypatch.setattr(kitchen, 'WEAVE', True)
    response = client.post('/api/companion', json={'name': 'Kim', 'timezone': 'UTC', 'schedule': EVENINGS,
                                                    'home_city': 'Baltimore', 'identity': 'They are a nurse.'})
    assert response.status_code == 200, response.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    set_life(client, automatic_events=True, phrase_with_model=False)
    return response.json()


@contextmanager
def day_for(client):
    database = client.app.state.database
    with database.connect(write=True) as connection:
        yield made(database, connection)


def made(database, connection):
    companion = connection.execute('SELECT active_timeline_id FROM companions').fetchone()
    version = connection.execute('SELECT definition FROM character_versions').fetchone()
    definition = decode(version['definition'])
    return kitchen.day_for(connection, companion['active_timeline_id'], definition, WORLD, database.clock.now())


def test_the_panel_shows_their_week_in_words_and_the_user_can_change_it(client, kim):
    reconcile(client)
    view = client.get('/api/life/kitchen').json()
    assert len(view['week']) == 8 and sum(day['today'] for day in view['week']) == 1
    assert all(day['text'] or day['kind'] == 'away' for day in view['week'])
    assert view['summary'] and view['pantry_text'] and 'numbers' not in view
    changed = client.patch('/api/life/kitchen', json={'diet': 'vegan', 'skill': 3, 'bakes': True}).json()
    assert changed['diet'] == 'vegan' and changed['skill'] == 3 and set(changed['changed']) == {'diet', 'skill', 'bakes'}
    assert changed['summary'].startswith('A serious cook who loves baking; they are vegan')
    assert client.patch('/api/life/kitchen', json={'diet': 'carnivore'}).status_code == 422
    back = client.patch('/api/life/kitchen', json={'reset': True}).json()
    assert back['changed'] == [] and back['diet'] == view['diet']
    show(client, show_home_meters=True)
    assert 'numbers' in client.get('/api/life/kitchen').json()


def test_meals_are_drawn_the_same_way_every_time_and_follow_the_rhythm(client, kim):
    reconcile(client)
    with day_for(client) as found:
        days = [TODAY + timedelta(days=n) for n in range(-20, 2)]
        meals = [found.meal(day) for day in days]
        again = made(client.app.state.database, found.connection)
        assert [again.meal(day) for day in days] == meals
        kinds = {meal['kind'] for meal in meals}
        assert 'cook' in kinds and len(kinds) >= 2
        for meal in meals:
            assert kitchen.meal_text(meal)
            if meal['kind'] == 'leftovers':
                yesterday = date.fromisoformat(meal['date']) - timedelta(days=1)
                assert 'big' in next(dish for dish in kitchen.bank('modern-us')['dishes']
                                     if dish['name'] == meal['dish'])['tags'], yesterday
            if meal['kind'] == 'takeout':
                assert meal['cost'] > 0 and meal['takeout']['dish']


def test_staples_run_out_between_grocery_runs_except_on_the_easy_setting(client, kim):
    reconcile(client)
    set_life(client, kitchen_realism=3)
    with day_for(client) as found:
        states = [item['state'] for n in range(40) for item in found.pantry(TODAY - timedelta(days=n))]
        assert 'out' in states and 'stocked' in states
        run = next(TODAY - timedelta(days=n) for n in range(40) if found.grocery_day(TODAY - timedelta(days=n)))
        assert all(item['state'] == 'stocked' for item in found.pantry(run))
    set_life(client, kitchen_realism=0)
    with day_for(client) as easy:
        assert {item['state'] for n in range(40) for item in easy.pantry(TODAY - timedelta(days=n))} == {'stocked'}
        assert not any(easy.meal(TODAY - timedelta(days=n))['mishap'] for n in range(60))


def test_takeout_counts_as_spending_and_the_chat_knows_dinner(client, kim, provider):
    reconcile(client)
    with day_for(client) as found:
        budget = money.profile(found.definition)
        start = money.cycle_start(budget, TODAY)
        takeout = [found.meal(start + timedelta(days=n)) for n in range((TODAY - start).days + 1)]
        takeout = [meal for meal in takeout if meal['kind'] == 'takeout']
        bought = kitchen.purchases(found.connection, found.timeline_id, start, TODAY, found.definition, None, None)
        if takeout:
            assert bought[0]['for'] == 'food' and bought[0]['cost'] == round(sum(meal['cost'] for meal in takeout), 2)
        else:
            assert bought == []
    provider.replies.append([Chunk('Hey!'), Chunk('', 'stop')])
    send(client, 'What are you having for dinner?', 'client-kitchen-1')
    prompt = provider.requests[-1]['prompt']
    assert '## Your kitchen and meals' in prompt and 'In the kitchen you are' in prompt and 'Dinner tonight:' in prompt


def test_cooking_nights_name_the_dish_in_their_day(client, kim, clock):
    # Their week is seeded from the timeline's random id, so look over a few days rather than one.
    for _day in range(5):
        reconcile(client)
        clock.advance(timedelta(days=1))
    with client.app.state.database.connect() as connection:
        rows = connection.execute("SELECT entry FROM life_agenda WHERE subject='companion' AND entry IS NOT NULL").fetchall()
    entries = [decode(row['entry']) for row in rows]
    for entry in entries:
        if entry['activity'] == 'home-cooking':
            assert entry['kitchen']['dish'] in entry['summary'] and entry['summary'].startswith('Kim cooked ')
    assert any(entry.get('kitchen') for entry in entries)


def hosted(text, firm=False):
    found = outings.proposal(text, TODAY, {}, catalog.city('baltimore'), firm)
    return found and (found['activity'], found['day'] and found['day'].isoformat())


def test_dinner_at_their_place_is_read_both_ways():
    assert hosted('Can I come over for dinner Friday?') == ('dinner-in', '2026-10-09')
    assert hosted('Dinner at your place this weekend?') == ('dinner-in', '2026-10-10')
    assert hosted('Would you cook for me sometime?') == ('dinner-in', None)
    assert hosted("Come over Saturday, I'll cook for you!", firm=True) == ('dinner-in', '2026-10-10')
    assert hosted('Come over for dinner Thursday?', firm=True) == ('dinner-in', '2026-10-08')
    # The user having them over, a vague wish from the companion, and the past are not dinner at their place.
    assert hosted("Want to come over to my place for dinner tomorrow? I'll cook") is None
    assert hosted('Come over for dinner sometime!', firm=True) is None
    assert hosted('Did you cook dinner at your place yesterday?') is None


def test_the_user_comes_over_and_they_cook(client, kim, provider, clock):
    provider.replies.append([Chunk('Yes! Come over.'), Chunk('', 'stop')])
    send(client, 'Can I come over for dinner Wednesday?', 'client-kitchen-2')
    [outing] = client.get('/api/life/outings').json()['outings']
    assert outing['activity'] == 'dinner-in' and outing['local_date'] == '2026-10-07'
    assert outing['place']['id'] == '~home' and outing['place']['name'] == "Kim's place"
    menu = outing['place']['menu']
    assert menu['dish'] or menu['takeout']
    notes = provider.requests[-1]['prompt']
    assert 'You are having the user over' in notes and 'at your place' in notes
    assert client.post(f"/api/life/outings/{outing['id']}/elsewhere", json={}).status_code == 409
    clock.advance(timedelta(days=2, hours=7, minutes=30))  # Wednesday 19:30.
    reconcile(client)
    preview = client.get('/api/context/preview').json()['prompt']
    assert 'Right now the user is over at your place, in person' in preview
    with day_for(client) as found:
        assert found.meal(date(2026, 10, 7))['kind'] == 'hosting'
        assert kitchen.cooked(found.connection, found.timeline_id, date(2026, 10, 7), found.definition, None,
                              None) == (1 if menu['takeout'] else 2)


def test_now_and_then_they_ask_the_user_over(client, kim, monkeypatch, clock):
    reconcile(client)
    monkeypatch.setattr(kitchen, 'INVITES', True)
    monkeypatch.setattr(kitchen, 'INVITE_CHANCE', 1.0)
    clock.advance(timedelta(hours=2))  # Monday 14:00.
    with client.app.state.database.connect(write=True) as connection:
        from companion.characters import current
        companion = current(connection)
        [trigger] = kitchen.invite_due(connection, companion, clock.now())
        assert trigger.kind == 'dinner_invite' and trigger.template.startswith('Come over for dinner')
        assert trigger in openers.candidates(connection, companion, clock.now())
        message = {'id': 'invite-message'}
        connection.execute("INSERT INTO messages (id, timeline_id, seq, role, text, status, active, character_version_id, "
                           "memory_revision, created_at, completed_at) VALUES ('invite-message', ?, 99, 'companion', ?, "
                           "'complete', 1, ?, 0, ?, ?)", (companion['active_timeline_id'], trigger.template,
                                                         companion['active_version_id'], clock.now().isoformat(),
                                                         clock.now().isoformat()))
        outing = kitchen.settle_invite(connection, companion, message, trigger, clock.now().isoformat())
        assert outing['activity'] == 'dinner-in' and outing['local_date'] == trigger.sources[0]
