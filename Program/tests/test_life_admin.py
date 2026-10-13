"""Life admin calendar: the dentist, taxes, the lease and the week's errands follow the city's country and era, take
their slots in the companion's day, and move rather than clash with plans with the user."""
from datetime import date, timedelta

import pytest
from conftest import reconcile, send, set_life

from companion.database import decode
from companion.life import admin, body, composer
from companion.providers.chat import Chunk
from companion.world import catalog

EVENINGS = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00', 'days': [0, 1, 2, 3, 4]},
            {'key': 'evening', 'label': 'Evening', 'kind': 'leisure', 'start': '17:00', 'end': '23:00'},
            {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]
TUESDAY, THURSDAY = date(2026, 10, 6), date(2026, 10, 8)


def kinds(city_id):
    return {rule['id'] for rule in admin.rules_for(catalog.city(city_id))}


def test_what_comes_due_follows_the_country_and_era():
    assert {'dentist', 'taxes', 'physical', 'lease', 'car-registration', 'car-inspection'} <= kinds('baltimore')
    # Florida has no state income tax and no car inspection.
    [florida] = [rule for rule in admin.rules_for(catalog.city('miami')) if rule['id'] == 'taxes']
    assert 'federal tax return' in florida['done'] and 'state' not in florida['done'].split('(')[0]
    assert 'car-inspection' not in kinds('miami')
    smog = [rule for rule in admin.rules_for(catalog.city('los-angeles')) if rule['id'] == 'car-inspection']
    assert [rule['title'] for rule in smog] == ['Smog check']
    assert {'mot', 'tv-licence', 'council-tax'} <= kinds('london') and 'taxes' not in kinds('london')
    assert 'quarter-rent' in kinds('london-1895') and 'dentist' not in kinds('london-1895')
    assert {'quarter-rent', 'tithe'} <= kinds('camelot') and 'car-inspection' not in kinds('camelot')
    assert {'residence-tax', 'year-end-adjustment'} <= kinds('osaka')
    assert 'year-end-settlement' in kinds('jeju')
    # Taxes were due March 15 in the 1920s; nobody files in Oz.
    [twenties] = [rule for rule in admin.rules_for(catalog.city('new-york-1925')) if rule['id'] == 'taxes']
    assert twenties['on'] == '03-15'
    assert kinds('emerald-city') == {'farrier'}


def test_repeating_appointments_are_seeded_and_deadlines_come_early_for_the_organised():
    dentist = next(rule for rule in admin.rules_for(catalog.city('baltimore')) if rule['id'] == 'dentist')
    found = admin.occurrences(dentist, 'seed', date(2026, 1, 1), date(2027, 12, 31))
    assert len(found) == 4 and found == admin.occurrences(dentist, 'seed', date(2026, 1, 1), date(2027, 12, 31))
    assert all((later[0] - earlier[0]).days == 183 for earlier, later in zip(found, found[1:]))
    taxes = next(rule for rule in admin.rules_for(catalog.city('baltimore')) if rule['id'] == 'taxes')
    due = date(2027, 4, 15)
    early = admin.planned_day(taxes, due, due, 'seed', 'organised')
    late = admin.planned_day(taxes, due, due, 'seed', 'scattered')
    assert early <= due - timedelta(days=21) and due - timedelta(days=3) <= late <= due


def test_habit_comes_from_their_own_words():
    assert admin.habit({'personality': 'Meticulous and punctual nurse'}) == 'organised'
    assert admin.habit({'personality': 'Warm, chaotic and forgetful', 'flaws': ['procrastinates']}) == 'scattered'
    assert admin.habit({'personality': 'Quiet'}) == 'average'


def test_the_banks_are_big_specific_and_era_tagged():
    for name in ('errands', 'paperwork', 'surprises'):
        items = admin.data()[name]
        assert len(items) >= 100, name
        for group in ('modern', 'industrial', 'old'):
            assert len([item for item in items if group in item['eras']]) >= 20, (name, group)
        assert all(item['title'] and item['done'] and item['where'] for item in items)
    assert all(item.get('line') for item in admin.data()['surprises'])


@pytest.fixture
def mira(client, monkeypatch, provider):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(composer, 'PLAN_SHARE', 0)
    monkeypatch.setattr(composer, 'THREAD_SHARE', 0)
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC', 'schedule': EVENINGS,
                                                    'home_city': 'Baltimore', 'personality': 'Organised, punctual'})
    assert response.status_code == 200, response.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    set_life(client, automatic_events=True, phrase_with_model=False, catch_up_max_events=6,
             catch_up_lookback_hours=168)
    return response.json()


def add(client, **values):
    database = client.app.state.database
    with database.connect(write=True) as connection:
        from companion.characters import require_current
        companion = require_current(connection)
        fields = {'source': 'admin', 'kind': 'errand', 'title': 'Return library books',
                  'done': 'returned a stack of library books', 'now': database.clock.now(), **values}
        return admin.add(connection, companion, **fields)


def agenda_entry(client, slot_key):
    with client.app.state.database.connect() as connection:
        row = connection.execute("SELECT entry FROM life_agenda WHERE subject='companion' AND slot_key=?",
                                 (slot_key,)).fetchone()
    return decode(row['entry']) if row and row['entry'] else None


def says(provider, text):
    provider.replies.append([Chunk(text), Chunk('', 'stop')])


def test_an_entry_takes_a_free_slot_and_happens(client, mira, clock):
    chore = add(client, key='test:books', day=TUESDAY)
    # Weekdays are work until five: the evening is the first free time, at a seeded half hour in it.
    assert chore['local_date'] == '2026-10-06' and '17:30' <= chore['at_time'] <= '21:30'
    assert add(client, key='test:books', day=THURSDAY)['id'] == chore['id']  # The same key is the same entry.
    vet = add(client, key='pets:vet:test', source='pets', kind='vet', title='Vet visit for Biscuit',
              done='took Biscuit to the vet for a check-up', day=TUESDAY, fixed=True, out=True)
    # The evening already has the library books, so the vet goes to the next evening, while the vet is open.
    assert vet['local_date'] == '2026-10-07' and '17:30' <= vet['at_time'] < '18:00'
    reconcile(client)
    entry = agenda_entry(client, 'evening@2026-10-06')
    assert entry['summary'] == 'Mira returned a stack of library books.' and entry['admin']['id'] == chore['id']
    today = client.get('/api/today').json()
    # Only what this calendar holds: Looks' and Kitchen's own seeded items can show alongside, read-only.
    assert [item['title'] for item in today['plans']['admin'] if item['movable']] == \
        ['Return library books', 'Vet visit for Biscuit']
    clock.advance(timedelta(days=1, hours=12))  # Wednesday midnight: Tuesday's is done.
    reconcile(client)
    panel = client.get('/api/life/admin').json()
    assert [item['title'] for item in panel['done']] == ['Return library books']
    assert panel['state'][1:3] == ['Gets things done early.', 'Plans with you come first, except appointments booked with someone else.']


def test_a_plan_with_the_user_moves_a_chore_and_an_appointment_moves_the_plan(client, mira, provider, clock):
    add(client, key='test:books', day=TUESDAY)
    dentist = add(client, key='test:dentist', kind='dentist', title='Dentist check-up', fixed=True, out=True,
                  done='went to the dentist for a check-up and cleaning', day=THURSDAY)
    assert dentist['local_date'] == '2026-10-08'
    reconcile(client)
    says(provider, 'Yes!')
    send(client, 'Want to get dinner Tuesday?', 'client-admin-01')
    [outing] = client.get('/api/life/outings').json()['outings']
    assert outing['local_date'] == '2026-10-06'
    # The chore never cancels the plan: it moves to another evening.
    [moved] = [item for item in client.get('/api/life/admin').json()['upcoming'] if item['key'] == 'test:books']
    assert moved['local_date'] == '2026-10-07' and moved['moved_from'] == '2026-10-06'
    assert moved['moved_reason'] == 'moved for a plan'
    reconcile(client)
    assert agenda_entry(client, 'evening@2026-10-06')['outing']
    assert agenda_entry(client, 'evening@2026-10-07')['admin']['key'] == 'test:books'
    # Thursday evening is booked at the dentist: dinner then goes to Friday, and the reply says so.
    says(provider, 'I have the dentist, how about Friday?')
    send(client, 'Dinner Thursday?', 'client-admin-02')
    second = [item for item in client.get('/api/life/outings').json()['outings'] if item['id'] != outing['id']]
    assert second[0]['asked_date'] == '2026-10-08' and second[0]['local_date'] == '2026-10-09'
    assert "can't make that day" in provider.requests[-1]['prompt']


def test_the_user_can_move_an_entry_to_another_day(client, mira):
    chore = add(client, key='test:books', day=TUESDAY)
    panel = client.post(f"/api/life/admin/{chore['id']}/move").json()
    [moved] = [item for item in panel['upcoming'] if item['key'] == 'test:books']
    assert moved['local_date'] == '2026-10-07' and moved['moved_reason'] == 'moved by you'
    # Someone who leaves things to the last minute never puts off the day the user picked.
    database = client.app.state.database
    with database.connect(write=True) as connection:
        from companion.characters import require_current
        companion = require_current(connection)
        assert admin.put_off(connection, companion, TUESDAY, 1.0, database.clock.now()) == 0


def test_seeded_admin_plans_ahead_and_counts_its_costs(client, mira, monkeypatch, clock):
    monkeypatch.setattr(admin, 'ACTIVE', True)
    reconcile(client)
    panel = client.get('/api/life/admin').json()
    assert panel['upcoming'], panel
    assert all('2026-10-05' <= item['local_date'] <= '2026-10-27' for item in panel['upcoming'])
    assert {item['title'] for item in panel['later']} >= {'Dentist check-up', 'File taxes'}
    # Again the same: seeded, not rolled afresh.
    reconcile(client)
    # Home upkeep's big cleans can join as its walk ahead settles; Life admin's own draws stay put.
    def own(view):
        return [item['key'] for item in view['upcoming'] if item['source'] == 'admin']
    assert own(client.get('/api/life/admin').json()) == own(panel)
    clock.advance(timedelta(days=22))
    reconcile(client)
    done = client.get('/api/life/admin').json()['done']
    assert done
    money = client.get('/api/today/money').json()
    # Money counts this pay period's spending only.
    priced = [item for item in done if item['cost_text'] and money.get('payday', {}).get('last', '9') <= item['local_date']]
    if money['available'] and priced:
        assert any(item['for'] == 'admin' for item in money['bought'])


def test_the_level_setting_is_saved(client, mira):
    assert client.get('/api/life/settings').json()['admin_realism'] == 2
    assert client.put('/api/life/settings', json={'admin_realism': 3}).json()['admin_realism'] == 3
    assert client.put('/api/life/settings', json={'admin_realism': 4}).status_code == 422


def test_who_gives_way_follows_the_slider():
    dentist = {'fixed': True, 'deadline': None, 'local_date': '2026-10-08'}
    taxes = {'fixed': False, 'deadline': '2026-10-08', 'local_date': '2026-10-08'}
    chore = {'fixed': False, 'deadline': None, 'local_date': '2026-10-08'}
    assert [admin.stands(dentist, level) for level in admin.LEVELS] == [False, False, True, True]
    assert [admin.stands(taxes, level) for level in admin.LEVELS] == [False, False, False, True]
    assert not any(admin.stands(chore, level) for level in admin.LEVELS)


def test_on_light_the_dentist_moves_for_dinner(client, mira, provider):
    client.put('/api/life/settings', json={'admin_realism': 1})
    add(client, key='test:dentist', kind='dentist', title='Dentist check-up', fixed=True, out=True,
        done='went to the dentist for a check-up and cleaning', day=THURSDAY)
    reconcile(client)
    says(provider, 'Yes!')
    send(client, 'Dinner Thursday?', 'client-admin-03')
    [outing] = client.get('/api/life/outings').json()['outings']
    assert outing['local_date'] == '2026-10-08'
    [moved] = [item for item in client.get('/api/life/admin').json()['upcoming'] if item['key'] == 'test:dentist']
    assert moved['local_date'] != '2026-10-08' and moved['moved_reason'] == 'moved for a plan'


def test_dinner_at_their_place_moves_a_chore_out_of_the_evening(client, mira, provider):
    add(client, key='test:books', day=TUESDAY)
    reconcile(client)
    says(provider, 'Yes, come over!')
    send(client, 'Can I come over for dinner at your place Tuesday?', 'client-admin-04')
    [outing] = client.get('/api/life/outings').json()['outings']
    assert outing['activity'] == 'dinner-in' and outing['local_date'] == '2026-10-06'
    [moved] = [item for item in client.get('/api/life/admin').json()['upcoming'] if item['key'] == 'test:books']
    assert moved['local_date'] == '2026-10-07' and moved['moved_reason'] == 'moved for a plan'


def test_big_cleans_from_home_upkeep_land_on_the_calendar_once(client, mira, monkeypatch, clock):
    monkeypatch.setattr(admin, 'ACTIVE', True)
    client.put('/api/life/settings', json={'admin_realism': 0})  # Only the home features' items, none of its own.
    from companion.life import upkeep
    monkeypatch.setattr(upkeep, 'chores_between', lambda *_args: [
        {'date': '2026-10-10', 'kind': 'big-clean', 'text': 'did a big clean'},
        {'date': '2026-10-07', 'kind': 'laundry', 'text': 'did the laundry'}])
    reconcile(client)
    # The walk ahead settles the same week's big clean on another day: still one big clean.
    monkeypatch.setattr(upkeep, 'chores_between', lambda *_args: [
        {'date': '2026-10-11', 'kind': 'big-clean', 'text': 'did a big clean'}])
    reconcile(client)
    reconcile(client)
    [clean] = [item for item in client.get('/api/life/admin').json()['upcoming'] if item['source'] == 'upkeep']
    assert (clean['source'], clean['title'], clean['key']) == ('upkeep', 'Big clean', 'upkeep:big-clean:2026-W41')
    with client.app.state.database.connect() as connection:
        assert upkeep.told(connection, mira['active_timeline_id'], '2026-10-10', 'big-clean')


def test_vet_visits_haircuts_and_grocery_runs_show_alongside_read_only(client, mira, monkeypatch):
    from companion.life import grooming, kitchen, pets
    monkeypatch.setattr(kitchen, 'grocery_runs', lambda *_args: [
        {'date': '2026-10-10', 'text': 'Grocery run (out of eggs)', 'staples': ['eggs']}])
    monkeypatch.setattr(grooming, 'appointments', lambda *_args: [
        {'date': '2026-10-09', 'kind': 'haircut', 'title': 'Haircut', 'text': 'got a trim', 'spend': ''}])
    monkeypatch.setattr(pets, 'vet_visits', lambda *_args: [
        {'date': '2026-10-08', 'pet': 'Biscuit', 'variety': 'dog', 'reason': 'a check-up', 'kind': 'checkup',
         'pet_id': 'p1', 'movable': True}])
    add(client, key='test:books', day=TUESDAY)
    sources = [item['source'] for item in client.get('/api/life/admin').json()['upcoming']]
    assert sources == ['admin', 'pets', 'looks']  # No kitchen yet: only reads, so no grocery runs.
    database = client.app.state.database
    with database.connect(write=True) as connection:
        kitchen.ensure(connection, mira['active_timeline_id'], mira['version']['definition'], None, database.clock.now())
    today = client.get('/api/today').json()['plans']['admin']
    assert [(item['title'], item['movable'], item['fixed']) for item in today] == [
        ('Return library books', True, False), ('Vet check-up for Biscuit', False, True), ('Haircut', False, True),
        ('Grocery run (out of eggs)', False, False)]


def test_later_shows_the_soonest_of_each_kind(monkeypatch):
    """Quarter-day rent comes due at Christmas before Lady Day, whatever order the rule lists its days in."""
    monkeypatch.setattr(admin, 'owns', lambda *_args: {'rent'})
    companion = {'active_timeline_id': 't1', 'version': {'definition': {'name': 'Wynn'}}}
    found = admin.later(None, companion, catalog.city('camelot'), date(2026, 10, 13))
    assert {item['kind']: item['local_date'] for item in found}['quarter-rent'] == '2026-12-25'


def test_small_errands_cost_an_everyday_price_in_the_citys_money():
    nurse = {'name': 'Mara', 'home_city': 'baltimore', 'identity': 'A registered nurse at Hopkins.'}
    small = [admin.priced(nurse, '$', f'letter:{index}') for index in range(40)]
    assert all(4 <= cost <= 20 for cost in small), small
    assert all(25 <= admin.priced(nurse, '$$', f'repair:{index}') <= 100 for index in range(40))
    smith = {'name': 'Wat', 'home_city': 'camelot', 'identity': 'A smith by the castle gate.'}
    fines = [admin.priced(smith, '$', f'fine:{index}') for index in range(40)]
    assert all(0 < fine <= 3 for fine in fines), fines


def test_a_lower_level_takes_off_what_it_would_not_have_planned(client, mira):
    add(client, key='test:books', day=TUESDAY)
    add(client, key='test:dentist', kind='dentist', title='Dentist check-up', fixed=True, out=True,
        done='went to the dentist for a check-up and cleaning', day=THURSDAY)
    kept = add(client, key='test:keys', title='Cut spare keys', done='had spare keys cut', day=TUESDAY)
    client.post(f"/api/life/admin/{kept['id']}/move")  # The user's own move stays whatever the level.
    def keys():
        return {item['key'] for item in client.get('/api/life/admin').json()['upcoming']}
    client.put('/api/life/settings', json={'admin_realism': 1})
    reconcile(client)
    assert {'test:dentist', 'test:keys'} <= keys() and 'test:books' not in keys()
    client.put('/api/life/settings', json={'admin_realism': 0})
    reconcile(client)
    assert 'test:keys' in keys() and 'test:dentist' not in keys()


def test_in_older_eras_errands_out_keep_daylight_hours():
    from companion.life import routine
    taken = object.__new__(admin.Taken)
    taken.schedule, taken.away, taken.closed = routine.blocks({'schedule': EVENINGS})[0], set(), set()
    taken.times, taken.entries, taken.jitter = {}, {}, 0.99
    saturday = date(2026, 10, 10)  # No work: the evening is the only free block that ends after dark.
    taken.daylight = False
    assert taken.fits(saturday, None, True, False) >= '18:00'
    taken.daylight = True
    found = taken.fits(saturday, None, True, False)
    assert found is None or found < '18:00'
    assert taken.fits(saturday, None, False, False) >= '18:00'  # Paperwork at home can wait for the evening.
