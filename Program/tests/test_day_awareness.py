"""The reply knows what the companion's own day holds (a long run had her "just home from the ER" at 10 AM on a
day off, and "heading into a shift" on a free evening)."""
import re
from datetime import timedelta

from conftest import reconcile, set_life


def office_worker(client):
    current = client.get('/api/companion').json()['companion']
    definition = {**current['version']['definition'], 'schedule': [
        {'label': 'Office', 'kind': 'work', 'start': '09:00', 'end': '17:30', 'days': [0, 1, 2, 3, 4]},
        {'label': 'Asleep', 'kind': 'sleep', 'start': '23:30', 'end': '07:00'}]}
    response = client.post('/api/companion/versions', json={'definition': definition,
                                                            'expected_version_id': current['active_version_id']})
    assert response.status_code == 200, response.text


def time_section(client):
    system = client.get('/api/context/preview').json()['system']
    return system[system.index('## Time'):].split('\n## ')[0]


def test_a_work_day_says_where_she_is_now(client, companion, clock):
    office_worker(client)
    clock.instant = clock.now().replace(day=6, hour=9, minute=40)  # Tuesday, 10:40 in Lisbon.
    text = time_section(client)
    assert 'Your day today: Asleep until 07:00; Office (work shift) 09:00-17:30; Asleep from 23:30.' in text
    assert 'Right now you are: Office (work shift), until 17:30.' in text
    assert 'Your next shift' not in text and 'no work' not in text


def test_a_day_off_says_so_and_names_the_next_shift(client, companion, clock):
    office_worker(client)
    clock.instant = clock.now().replace(day=10, hour=11, minute=0)  # Saturday, noon in Lisbon.
    text = time_section(client)
    assert 'You have no work or classes today.' in text
    assert 'Right now you are: free.' in text
    assert 'Your next shift: Monday 12 October, 09:00-17:30.' in text
    clock.advance(timedelta(hours=12))  # Asleep, just after midnight.
    assert 'Right now you are: Asleep, until 07:00.' in time_section(client)


def test_recent_life_reads_in_her_own_time(client, companion, clock):
    set_life(client, automatic_events=True, catch_up_max_events=3, phrase_with_model=False)
    clock.advance(timedelta(days=2))
    reconcile(client)
    system = client.get('/api/context/preview').json()['system']
    section = system[system.index('## Your recent life'):].split('\n## ')[0]
    lines = section.splitlines()[1:]
    assert lines and all(re.match(r'- \w+day \d\d October, \d\d:\d\d: ', line) for line in lines)
