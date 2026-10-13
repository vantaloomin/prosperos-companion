"""Home upkeep: laundry, dishes, clutter and the big clean (companion/life/upkeep.py)."""
import re
from datetime import date, timedelta

import pytest
from conftest import reconcile

from companion.life import composer, upkeep, upkeep_bank

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
