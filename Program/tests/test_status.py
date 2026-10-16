"""Status messages: a line the companion sets for themselves, and an away line from their routine
(companion/life/status.py, Hit List #51)."""
from datetime import datetime, timedelta, timezone

from test_social_circle import make

from companion.characters import require_current
from companion.life import status


def at(clock, hour: int, minute: int = 0, day: int = 5):
    """Baltimore time on Monday 5 October 2026 (or another day that month)."""
    clock.instant = datetime(2026, 10, day, hour, minute, tzinfo=timezone(timedelta(hours=-4))).astimezone(timezone.utc)


def read(client):
    response = client.get('/api/companion')
    assert response.status_code == 200, response.text
    return response.json()['companion']['status']


def test_an_away_line_shows_while_they_sleep_work_or_go_out_and_never_says_online(client, clock):
    make(client, 'Warm and curious.', interests=['birdwatching'])
    at(clock, 10)
    working = read(client)
    assert working['away']['glyph'] == 'briefcase' and working['away']['text'] in {
        'at work till 5:00 PM', 'working, back at 5:00 PM', 'on the clock till 5:00 PM'}
    assert working['text'] and working['set_by'] == 'app'
    at(clock, 23, 30)
    assert read(client)['away']['glyph'] == 'moon'
    at(clock, 19)
    assert read(client)['away']['glyph'] == 'pin'
    at(clock, 8)
    assert read(client)['away'] is None
    for hour in range(24):
        at(clock, hour)
        found = read(client)
        words = f"{found['text']} {found['away'] and found['away']['text']}".lower()
        assert not any(word in words for word in ('online', 'idle', 'typing', 'offline'))


def test_the_written_line_changes_at_most_twice_a_day(client, clock):
    make(client, 'Warm and curious.', interests=['birdwatching', 'jazz'])
    lines = {}
    for hour in range(0, 24):
        at(clock, hour, day=7)
        lines.setdefault(hour < 12, set()).add(read(client)['text'])
    assert all(len(found) == 1 for found in lines.values())


def test_the_user_can_set_a_line_that_stays_until_something_big_happens(client, clock):
    mira = make(client, 'Warm and curious.')
    at(clock, 8)
    response = client.put(f"/api/companion/{mira['id']}/status", json={'text': '  gone   fishing  '})
    assert response.status_code == 200 and response.json()['text'] == 'gone fishing'
    assert read(client) | {'away': None, 'where': None} == {'text': 'gone fishing', 'set_by': 'you', 'away': None, 'where': None}
    chats = client.get('/api/chats').json()['chats']
    assert next(chat for chat in chats if chat['id'] == mira['id'])['status']['text'] == 'gone fishing'
    at(clock, 8, day=6)
    assert read(client)['text'] == 'gone fishing'
    with client.app.state.database.connect(write=True) as connection:
        companion = require_current(connection)
        connection.execute("INSERT INTO life_chapters (id, timeline_id, kind, started_on, title, told, share, created_at) "
                           "VALUES ('c1', ?, 'move', '2026-10-06', 'Moved', 'You moved.', 'I did it, I moved!', ?)",
                           (companion['active_timeline_id'], clock.now().isoformat()))
    assert read(client) | {'away': None, 'where': None} == {'text': 'I did it, I moved!', 'set_by': 'app', 'away': None, 'where': None}
    client.put(f"/api/companion/{mira['id']}/status", json={'text': 'new place who dis'})
    assert read(client)['text'] == 'new place who dis'
    cleared = client.put(f"/api/companion/{mira['id']}/status", json={'text': ''}).json()
    assert cleared['set_by'] == 'app' and cleared['text'] == 'I did it, I moved!'
    assert client.put('/api/companion/nobody/status', json={'text': 'x'}).status_code == 404


def test_a_big_event_later_the_same_day_replaces_the_users_line(client, clock):
    mira = make(client, 'Warm and curious.')
    at(clock, 8)
    with client.app.state.database.connect(write=True) as connection:
        timeline = require_current(connection)['active_timeline_id']
        connection.execute("INSERT INTO life_chapters (id, timeline_id, kind, started_on, title, told, share, created_at) "
                           "VALUES ('c0', ?, 'job', '2026-10-05', 'New job', 'You started.', 'first day!', ?)",
                           (timeline, clock.now().isoformat()))
    at(clock, 9)
    client.put(f"/api/companion/{mira['id']}/status", json={'text': 'gone fishing'})
    assert read(client)['text'] == 'gone fishing'
    at(clock, 15)
    with client.app.state.database.connect(write=True) as connection:
        connection.execute("INSERT INTO life_chapters (id, timeline_id, kind, started_on, title, told, share, created_at) "
                           "VALUES ('c1', ?, 'move', '2026-10-05', 'Moved', 'You moved.', 'I did it, I moved!', ?)",
                           (timeline, clock.now().isoformat()))
    assert read(client) | {'away': None, 'where': None} == {'text': 'I did it, I moved!', 'set_by': 'app', 'away': None, 'where': None}


def test_away_times_read_the_way_people_write_them():
    assert status.clock_text(datetime(2026, 10, 5, 18, 0)) == '6:00 PM'
    assert status.clock_text(datetime(2026, 10, 5, 17, 30)) == '5:30 PM'
    assert status.clock_text(datetime(2026, 10, 5, 0, 15)) == '12:15 AM'
    assert status.clock_text(datetime(2026, 10, 5, 17, 30), retro=True) == '5:30pm'
    assert status.clock_text(datetime(2026, 10, 5, 18, 0), retro=True) == '6pm'


def test_retro_im_draws_era_away_messages_from_the_bank(client, clock):
    """Retro IM swaps the everyday and away lines for 2000s away messages; other styles keep the plain ones."""
    make(client, 'Warm and curious.', interests=['birdwatching'])
    bank = status.retro_bank()
    assert client.put('/api/settings', json={'chat_style': 'retro'}).status_code == 200
    at(clock, 10)
    assert read(client)['away']['text'] in {line.format(until='5pm') for line in bank['away']['work']}
    everyday = set(bank['fake_deep'] + bank['emo'] + bank['random'])
    seen = set()
    for day in range(5, 25):
        at(clock, 8, day=day)
        seen.add(read(client)['text'])
    assert any(line in everyday or any(song in line for song in bank['songs']) for line in seen), seen
    assert client.put('/api/settings', json={'chat_style': 'feed'}).status_code == 200
    at(clock, 10)
    assert read(client)['away']['text'] in {'at work till 5:00 PM', 'working, back at 5:00 PM', 'on the clock till 5:00 PM'}


def test_the_retro_bank_is_big_and_never_says_online():
    bank = status.retro_bank()
    for kind in ('fake_deep', 'emo', 'random', 'songs'):
        assert len(bank[kind]) >= 100 and len(set(bank[kind])) == len(bank[kind]), kind
    assert set(bank['away']) == set(status.AWAY) and all(len(lines) >= 30 for lines in bank['away'].values())
    longest = max(bank['songs'], key=len)
    lines = [line.format(song=longest) for line in bank['song_lines']]
    lines += bank['fake_deep'] + bank['emo'] + bank['random']
    lines += [line.format(until='12:30') for kind in bank['away'].values() for line in kind]
    for line in lines:
        assert not any(word in line.lower() for word in ('online', 'idle', 'typing', 'offline')), line
        assert len(line) <= status.LIMIT, line


def test_your_own_lyrics_join_retro_im_from_a_file_in_the_data_folder(client, clock, monkeypatch):
    """retro-lyrics.txt next to the database: comments are skipped, and lyrics show as a quoted line."""
    monkeypatch.setattr(status, 'RETRO_KINDS', ())  # Only lyrics on days without a plan, whatever the random seed.
    make(client, 'Warm and curious.', interests=['birdwatching'])
    assert client.put('/api/settings', json={'chat_style': 'retro'}).status_code == 200
    with client.app.state.database.connect() as connection:
        path = status.lyrics_path(connection)
    assert path.name == 'retro-lyrics.txt'
    status.lyrics_template(path.parent)
    assert path.read_text(encoding='utf-8').startswith('#')
    path.write_text(path.read_text(encoding='utf-8') + 'a lyric only on this computer\n\n# skipped\n', encoding='utf-8')
    seen = set()
    for day in range(5, 30):
        at(clock, 8, day=day)
        seen.add(read(client)['text'])
    assert '♫ a lyric only on this computer ♫' in seen, seen
    assert not any('skipped' in line for line in seen)


def test_retro_work_lines_fit_their_job_and_their_era():
    def lines(career, city='baltimore'):
        return status.retro_away({'name': 'Ezra', 'home_city': city, 'money': {'career': career}}, 'work')
    boatbuilder = lines('boatbuilder', 'haddon-harbor')
    assert boatbuilder and not [line for line in boatbuilder if 'email' in line or 'office' in line or 'mall' in line]
    assert any('email' in line for line in lines('accountant'))
    assert lines('boatbuilder', 'pellmouth') == list(status.AWAY['work'])
