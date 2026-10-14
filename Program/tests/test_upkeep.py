"""Home upkeep: laundry, dishes, clutter and the big clean (companion/life/upkeep.py)."""
import re
from datetime import date, timedelta

import pytest
from conftest import reconcile

from companion.life import composer, home, upkeep, upkeep_bank

TODAY = date(2026, 10, 5)  # the test clock's
WORK = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'days': [0, 1, 2, 3, 4], 'start': '09:00', 'end': '17:00'},
        {'key': 'chores', 'label': 'Chores', 'kind': 'errand', 'start': '18:00', 'end': '20:00'},
        {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]
MIRA = {'name': 'Mira', 'personality': 'warm, a little chaotic and forgetful', 'location': 'Fells Point, Baltimore',
        'timezone': 'America/New_York', 'schedule': WORK}


@pytest.fixture
def mira(client, monkeypatch):
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(composer, 'PLAN_SHARE', 0)
    monkeypatch.setattr(composer, 'THREAD_SHARE', 0)
    response = client.post('/api/companion', json=MIRA)
    assert response.status_code == 200, response.text
    assert client.get('/api/life/upkeep').status_code == 200
    return response.json()


def connect(client, write=True):
    return client.app.state.database.connect(write=write)


def timeline(client) -> str:
    with connect(client, False) as connection:
        return connection.execute('SELECT active_timeline_id FROM companions').fetchone()[0]


def walk_to(client, day: date, slider=None, since=None) -> list[dict]:
    with connect(client, False) as connection:
        return upkeep.walk(connection, timeline(client), MIRA, day, slider, since=since or TODAY - timedelta(days=1))


def test_the_bank_has_a_hundred_moments_per_kind_and_no_gendered_words():
    banks = {'laundry': upkeep_bank.LAUNDRY_DONE + upkeep_bank.LAUNDRY_PILING,
             'dishes': upkeep_bank.DISHES_DONE + upkeep_bank.DISHES_PILING,
             'clutter': upkeep_bank.CLUTTER_DONE + upkeep_bank.CLUTTER_PILING + upkeep_bank.PET_MESS,
             'big clean': upkeep_bank.BIG_CLEAN}
    for kind, lines in banks.items():
        assert len(lines) >= 100 and len(set(lines)) == len(lines), kind
        for line in lines:
            assert not re.search(r'\b(he|she|his|her|him|hers|himself|herself)\b', line, re.IGNORECASE), line
            assert line.split('|')[-1][:1].isupper() and line.endswith('.'), line


def test_the_habit_leans_on_who_they_are():
    def share(definition, kind):
        return sum(upkeep.seeded_habit(f's{n}', definition) == kind for n in range(200))
    assert share({'personality': 'neat, organized and meticulous'}, 'neat') > share({}, 'neat') * 1.5
    assert share({'personality': 'messy, chaotic and forgetful'}, 'messy') > share({}, 'messy') * 1.5


def test_walks_are_seeded_and_agree_from_day_to_day(client, mira):
    end = TODAY + timedelta(days=120)
    first = {day['date']: day for day in walk_to(client, end, since=TODAY)}
    assert walk_to(client, end, since=TODAY) == list(first.values())
    # A walk to a later day tells the same story for the days they share.
    for later in (5, 17, 40):
        shared = [day for day in walk_to(client, end + timedelta(days=later), since=TODAY) if day['date'] in first]
        assert len(shared) == len(first) and all(first[day['date']] == day for day in shared)


def test_big_cleans_wait_for_a_free_day_and_mess_follows_the_slider(client, mira):
    end = TODAY + timedelta(days=200)
    days = walk_to(client, end)
    cleans = [day for day in days if 'big-clean' in day['done']]
    assert cleans and not any(day['busy'] for day in cleans)
    assert all(0 <= value <= 100 for day in days for value in day['mess'].values())

    def average(slider):
        found = walk_to(client, end, slider)
        return sum(sum(day['mess'].values()) for day in found) / len(found)
    assert average(1) < average(2) < average(3)
    assert walk_to(client, end, 0) == []


def test_no_big_clean_on_a_day_with_plans_with_the_user(client, mira, monkeypatch):
    end = TODAY + timedelta(days=90)
    free = [day['date'] for day in walk_to(client, end) if 'big-clean' in day['done']]
    monkeypatch.setattr(upkeep, 'user_plan_days', lambda connection, timeline_id, since: set(free))
    moved = walk_to(client, end)
    assert not any('big-clean' in day['done'] and day['date'] in free for day in moved)


def test_set_it_and_the_habit_are_the_users_to_change(client, mira):
    spotless = client.put('/api/life/upkeep', json={'tidiness': 0}).json()
    assert spotless['tidiness'] == 0 and spotless['tidiness_label'] == 'Spotless' and spotless['set_on']
    assert all(area['value'] <= 5 for area in spotless['areas'])
    disaster = client.put('/api/life/upkeep', json={'tidiness': 4}).json()
    assert disaster['tidiness'] == 4 and 'The place is a mess.' in [area['text'] for area in disaster['areas']]
    picked = client.put('/api/life/upkeep', json={'habit': 'neat'}).json()
    assert picked['habit'] == 'neat' and picked['habit_set']
    back = client.put('/api/life/upkeep', json={'habit': 'auto'}).json()
    assert not back['habit_set']
    assert client.put('/api/life/upkeep', json={'tidiness': 9}).status_code == 422
    # It drifts with their week after that: a month on, a disaster has been dealt with.
    with connect(client, False) as connection:
        later = upkeep.on(connection, timeline(client), MIRA, date.fromisoformat(disaster['today']) + timedelta(days=30))
    assert upkeep.tidiness(later['mess']) < 4


def test_housework_is_woven_into_their_days_once(client, mira):
    client.put('/api/life/upkeep', json={'tidiness': 4})
    reconcile(client)
    with connect(client, False) as connection:
        told = [row[0] for row in connection.execute(
            "SELECT json_extract(entry, '$.upkeep.kind') || '@' || local_date FROM life_agenda "
            "WHERE subject='companion' AND json_extract(entry, '$.upkeep') IS NOT NULL")]
        others = connection.execute("SELECT COUNT(*) FROM life_agenda WHERE subject!='companion' "
                                    "AND json_extract(entry, '$.upkeep') IS NOT NULL").fetchone()[0]
    assert len(told) == len(set(told))
    assert others == 0
    # A chores moment always gets something done; a day's big clean or chore is told once.
    with connect(client) as connection:
        tid, day = timeline(client), (TODAY + timedelta(days=1)).isoformat()
        entry = {'activity': 'chores', 'summary': 'Mira did chores.'}
        woven = upkeep.touch(connection, tid, 'companion', entry, day, 's1', MIRA, None, client.app.state.database.clock.now())
        assert woven['upkeep']['kind'] and woven['summary'].startswith('Mira did chores. ')
        assert upkeep.touch(connection, tid, 'friend:1', entry, day, 's1', MIRA, None, None) == entry
        assert upkeep.touch(connection, tid, 'companion', {**entry, 'activity': 'busy-shift'}, day, 's1', MIRA, None,
                            None)['summary'] == 'Mira did chores.'


def test_chat_and_pictures_see_the_mess(client, mira):
    view = client.put('/api/life/upkeep', json={'tidiness': 4}).json()
    system = client.get('/api/context/preview').json()['system']
    assert '- Housework today: ' in system and 'The place is a mess.' in system and '- Your habit: you ' in system
    # It changes every day, so it sits with the daily sections, after home and belongings (prompt caching).
    assert system.index('## Housework at your place today') < system.index('- Housework today: ')
    assert '## Your home and belongings' not in system or \
        system.index('## Your home and belongings') < system.index('## Housework at your place today')
    with connect(client, False) as connection:
        tid = timeline(client)
        at_home = upkeep.image_hint(connection, tid, {'moment': {'activity': 'slow', 'local_date': view['today']}})
        out = upkeep.image_hint(connection, tid, {'place': 'Cafe', 'moment': {'activity': 'slow',
                                                                             'local_date': view['today']}})
    assert at_home.startswith('In view: ') and out == ''
    client.put('/api/life/settings', json={'upkeep_realism': 0})
    assert '- Housework today: ' not in client.get('/api/context/preview').json()['system']
    assert client.get('/api/life/upkeep').json()['on'] is False


def test_chores_ahead_for_life_admin(client, mira):
    today = date.fromisoformat(client.get('/api/life/upkeep').json()['today'])
    with connect(client, False) as connection:
        ahead = upkeep.chores_between(connection, timeline(client), MIRA, today, today + timedelta(days=60))
    assert ahead and {item['kind'] for item in ahead} <= {'big-clean', 'laundry'}
    assert all(today.isoformat() <= item['date'] for item in ahead)


def test_a_fork_keeps_the_habit_and_what_was_set_before_it(client, mira):
    view = client.put('/api/life/upkeep', json={'tidiness': 1, 'habit': 'messy'}).json()
    tid = timeline(client)
    with connect(client) as connection:
        connection.execute("INSERT INTO timelines (id, companion_id, status, created_at) "
                           "SELECT 'fork', companion_id, 'frozen', created_at FROM timelines WHERE id=?", (tid,))
        upkeep.copy(connection, tid, 'fork', f"{view['today']}T23:00:00Z")
        forked = dict(connection.execute("SELECT * FROM upkeep_state WHERE timeline_id='fork'").fetchone())
    assert forked['habit_set'] == 'messy' and forked['set_on'] == view['today'] and forked['set_level'] == 1




def test_a_recent_big_clean_reads_as_days_ago():
    assert upkeep.days_ago(date(2026, 10, 11), date(2026, 10, 13)) == 'Sunday, 2 days ago'
    assert upkeep.days_ago(date(2026, 10, 12), date(2026, 10, 13)) == 'yesterday'
    assert upkeep.days_ago(date(2026, 10, 13), date(2026, 10, 13)) == 'today'


def test_older_eras_get_no_modern_housework():
    modern = ('fridge', 'freezer', 'microwave', 'phone', 'remote', 'charger', 'recycling', 'vacuum', 'lint-roll',
              'litter', 'jeans', 't-shirt', 'toaster', 'gym', 'favourite', 'reorganised', 'hoover')
    old = {'era': 'medieval'}
    banks = [upkeep_bank.LAUNDRY_DONE, upkeep_bank.LAUNDRY_PILING, upkeep_bank.DISHES_DONE, upkeep_bank.DISHES_PILING,
             upkeep_bank.CLUTTER_DONE, upkeep_bank.CLUTTER_PILING, upkeep_bank.BIG_CLEAN, upkeep_bank.PET_MESS]
    lines = [line for bank in banks for line in upkeep.lines_for(old, bank)]
    lines += [upkeep.pet_line(old, f'seed{n}', [{'name': 'Rex', 'variety': 'cat'}]) for n in range(200)]
    assert not [line for line in lines if any(word in line.casefold() for word in modern)]


@pytest.mark.parametrize('era', ['modern', 'jazz-age', 'victorian', 'steampunk', 'frontier', 'medieval', 'fantasy'])
def test_every_era_has_a_hundred_moments_per_kind(era):
    state = {'era': era}
    banks = {'laundry': (upkeep_bank.LAUNDRY_DONE, upkeep_bank.LAUNDRY_PILING),
             'dishes': (upkeep_bank.DISHES_DONE, upkeep_bank.DISHES_PILING),
             'clutter': (upkeep_bank.CLUTTER_DONE, upkeep_bank.CLUTTER_PILING),
             'big clean': (upkeep_bank.BIG_CLEAN,), 'pet mess': (upkeep_bank.PET_MESS,)}
    for kind, parts in banks.items():
        assert len([line for bank in parts for line in upkeep.lines_for(state, bank)]) >= 100, (era, kind)


def test_a_home_without_plumbing_gets_no_sinks_or_mail():
    plumbed = ('sink', 'faucet', 'tap', 'mail', 'stove', 'oven', 'bathroom', 'shower', 'radiator', 'counter')
    old, victorian = {'era': 'medieval'}, {'era': 'victorian'}
    banks = [upkeep_bank.LAUNDRY_DONE, upkeep_bank.LAUNDRY_PILING, upkeep_bank.DISHES_DONE, upkeep_bank.DISHES_PILING,
             upkeep_bank.CLUTTER_DONE, upkeep_bank.CLUTTER_PILING, upkeep_bank.BIG_CLEAN, upkeep_bank.PET_MESS]
    lines = [line for bank in banks for line in upkeep.lines_for(old, bank)]
    lines += [upkeep.area_text(old, area, value) for area in upkeep.AREAS for value in (5, 30, 60, 90)]
    lines += list(upkeep.bank_for(old, upkeep_bank.PICTURE, upkeep_bank.PICTURE_RUSTIC).values())
    assert not [line for line in lines if any(re.search(rf'\b{word}', line.casefold()) for word in plumbed)]
    assert 'sink' in upkeep.area_text(victorian, 'dishes', 30) and 'washtub' in upkeep.area_text(old, 'dishes', 30)
    assert any('mail' in line for bank in banks for line in upkeep.lines_for(victorian, bank))


def test_a_pet_without_mess_gets_no_mess_line_and_each_kind_gets_its_own():
    state = {'era': 'modern'}
    assert upkeep.pet_line(state, 'seed', [{'name': 'Bubbles', 'variety': 'fish'}]) is None
    birds = {upkeep.pet_line(state, f'seed{n}', [{'name': 'Kiwi', 'variety': 'bird'}]) for n in range(200)}
    assert not [line for line in birds if re.search(r'\b(fur|hair|litter|paw)', line)]
    assert any('cage' in line for line in birds)


def test_a_big_clean_before_set_it_is_not_the_last_one(client, mira):
    tid = timeline(client)
    yesterday = (TODAY - timedelta(days=1)).isoformat()
    with connect(client) as connection:
        connection.execute("INSERT OR REPLACE INTO upkeep_days (timeline_id, local_date, mess, done, away, busy, "
                           "since_big) VALUES (?, ?, '{\"laundry\": 3, \"dishes\": 3, \"clutter\": 3}', "
                           "'[\"big-clean\"]', 0, 0, 0)", (tid, yesterday))
    assert client.get('/api/life/upkeep').json()['last_big_clean'] == yesterday
    disaster = client.put('/api/life/upkeep', json={'tidiness': 4}).json()
    assert disaster['last_big_clean'] is None
    system = client.get('/api/context/preview').json()['system']
    assert 'The place is a mess.' in system and 'you did a big clean' not in system


def test_turning_housework_off_forgets_upcoming_housework_moments(client, mira):
    tid = timeline(client)
    with connect(client) as connection:
        connection.execute("INSERT INTO life_agenda (id, timeline_id, subject, slot_key, starts_at, ends_at, local_date, "
                           "block, entry, basis, created_at) VALUES ('a1', ?, 'companion', 'evening@x', '', '', ?, "
                           "'evening', ?, 'test', '')", (tid, (TODAY + timedelta(days=3)).isoformat(),
                                                       '{"summary": "Mira did chores. Ran the dishwasher.", '
                                                       '"upkeep": {"kind": "dishes"}}'))
    assert client.put('/api/life/settings', json={'upkeep_realism': 0}).status_code == 200
    with connect(client, False) as connection:
        assert not connection.execute("SELECT id FROM life_agenda WHERE id='a1'").fetchall()


def test_a_day_being_drawn_is_not_kept_before_its_dinners_are_known(client, mira):
    tid, database = timeline(client), client.app.state.database
    later = database.clock.now() + timedelta(days=10)  # catching up: their today is well past the day drawn
    drawing = TODAY + timedelta(days=3)
    with connect(client) as connection:
        upkeep.touch(connection, tid, 'companion', {'activity': 'chores', 'summary': 'Mira did chores.'},
                     drawing.isoformat(), 's1', MIRA, None, later)
        kept = {row[0] for row in connection.execute('SELECT local_date FROM upkeep_days WHERE timeline_id=?', (tid,))}
    assert (drawing - timedelta(days=1)).isoformat() in kept and drawing.isoformat() not in kept


def test_a_chores_slot_is_left_to_housework(client, mira):
    # A plant fits any slot at home, so their things can come up whatever else the seed gave them.
    assert client.post('/api/life/home/items', json={'kind': 'plant', 'name': 'a pothos'}).status_code == 200
    tid, database = timeline(client), client.app.state.database
    entry = {'activity': 'chores', 'summary': 'Mira did chores.'}
    with connect(client) as connection:
        for n in range(12):
            woven = home.touch(connection, tid, 'companion', entry, (TODAY + timedelta(days=1)).isoformat(), f's{n}',
                               MIRA, None, database.clock.now())
            assert 'home' not in woven or woven['home'].get('pet_event') or woven['home'].get('change')
        connection.execute('UPDATE life_settings SET upkeep_realism=0')
        woven = [home.touch(connection, tid, 'companion', entry, (TODAY + timedelta(days=1)).isoformat(), f's{n}',
                            MIRA, None, database.clock.now()) for n in range(30)]
    assert any('home' in found for found in woven)  # with housework off, their things can come up again


def test_mess_shows_now_and_then_in_an_average_home_and_often_in_a_messy_one(monkeypatch):
    # Days with an area at the piling line, over four months on True to life with a work week and dinners at home.
    monkeypatch.setattr(upkeep, 'meals_cooked', lambda _context, _connection, _timeline, day: day.toordinal() % 3)
    monkeypatch.setattr(upkeep, 'pets_at_home', lambda *_args: [])

    def share(kind):
        piling = total = 0
        for run in range(20):
            context = {'kind': kind, 'busy': {0, 1, 2, 3, 4}, 'scale': upkeep.SCALE[2], 'keen': upkeep.KEEN[2],
                       'patience': upkeep.PATIENCE[2], 'planned': set(), 'seed': f'run-{run}', 'away': set()}
            day = {'date': '2026-01-01', 'mess': {area: upkeep.SETTLE[kind] for area in upkeep.AREAS}, 'done': [],
                   'away': False, 'busy': False, 'since_big': 0}
            for offset in range(1, 121):
                day = upkeep.step(None, 'timeline', day, date(2026, 1, 1) + timedelta(days=offset), context)
                total += 1
                piling += max(day['mess'].values()) >= upkeep.PILING
        return piling / total
    assert share('neat') < 0.03
    assert 0.07 <= share('average') <= 0.35
    assert share('messy') >= 0.45
