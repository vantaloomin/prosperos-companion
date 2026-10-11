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
        'at work till 5', 'working, back at 5', 'on the clock till 5'}
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
    assert read(client) | {'away': None} == {'text': 'gone fishing', 'set_by': 'you', 'away': None}
    chats = client.get('/api/chats').json()['chats']
    assert next(chat for chat in chats if chat['id'] == mira['id'])['status']['text'] == 'gone fishing'
    at(clock, 8, day=6)
    assert read(client)['text'] == 'gone fishing'
    with client.app.state.database.connect(write=True) as connection:
        companion = require_current(connection)
        connection.execute("INSERT INTO life_chapters (id, timeline_id, kind, started_on, title, told, share, created_at) "
                           "VALUES ('c1', ?, 'move', '2026-10-06', 'Moved', 'You moved.', 'I did it, I moved!', ?)",
                           (companion['active_timeline_id'], clock.now().isoformat()))
    assert read(client) | {'away': None} == {'text': 'I did it, I moved!', 'set_by': 'app', 'away': None}
    client.put(f"/api/companion/{mira['id']}/status", json={'text': 'new place who dis'})
    assert read(client)['text'] == 'new place who dis'
    cleared = client.put(f"/api/companion/{mira['id']}/status", json={'text': ''}).json()
    assert cleared['set_by'] == 'app' and cleared['text'] == 'I did it, I moved!'
    assert client.put('/api/companion/nobody/status', json={'text': 'x'}).status_code == 404


def test_away_times_read_the_way_people_write_them():
    assert status.clock_text(datetime(2026, 10, 5, 18, 0)) == '6'
    assert status.clock_text(datetime(2026, 10, 5, 17, 30)) == '5:30'
    assert status.clock_text(datetime(2026, 10, 5, 0, 15)) == '12:15'
