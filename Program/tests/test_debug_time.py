"""Debug time: jump ahead or speed up the app clock to check several days quickly, then go back."""
import time
from datetime import timedelta

from conftest import START, send

from companion.clock import parse
from companion.database import Database


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def settle(client):
    """Wait for a jump's walk to finish on the app's event loop."""
    for _ in range(600):
        status = ok(client.get('/api/debug-time'))
        if status['jumping'] is None:
            return status
        time.sleep(0.05)
    raise AssertionError('The jump did not finish.')


def count(client, table) -> int:
    with client.app.state.database.connect() as connection:
        return connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]  # noqa: S608


def test_starting_backs_up_and_leaves_the_time_alone(client, companion):
    status = ok(client.get('/api/debug-time'))
    assert status['active'] is False and parse(status['now']) == START
    status = ok(client.post('/api/debug-time/start', json={}))
    assert status['active'] is True and status['speed'] == 1 and parse(status['now']) == START
    workspace = client.app.state.database.path.parent
    assert status['backup'].startswith('before-debug-') and (workspace / 'backups' / status['backup']).is_file()
    assert (workspace / 'debug-time' / 'before-debug.sqlite3').is_file()
    listed = ok(client.get('/api/backups'))
    assert any(item['kind'] == 'before-debug' for item in listed['backups'])


def test_a_faster_clock_runs_the_whole_app_faster(client, companion, clock):
    ok(client.post('/api/debug-time/start', json={}))
    ok(client.post('/api/debug-time/speed', json={'speed': 60}))
    clock.advance(timedelta(minutes=2))
    status = ok(client.get('/api/debug-time'))
    assert parse(status['now']) == START + timedelta(hours=2) and parse(status['real_now']) == START + timedelta(minutes=2)
    assert client.app.state.database.clock.wait(60) == 1
    assert client.post('/api/debug-time/speed', json={'speed': 7}).status_code == 422


def test_debug_time_survives_a_restart(client, companion, clock):
    ok(client.post('/api/debug-time/start', json={}))
    ok(client.post('/api/debug-time/speed', json={'speed': 10}))
    clock.advance(timedelta(minutes=6))
    reopened = Database(client.app.state.database.path, clock)
    assert reopened.clock.now() == START + timedelta(hours=1)


def test_jumps_only_go_forward_and_need_debug_time(client, companion):
    assert client.post('/api/debug-time/jump', json={'hours': 5}).status_code == 409
    ok(client.post('/api/debug-time/start', json={}))
    assert client.post('/api/debug-time/jump', json={'to': '2026-10-01T09:00'}).status_code == 422
    assert client.post('/api/debug-time/jump', json={'hours': 24 * 31}).status_code == 422
    assert client.post('/api/debug-time/jump', json={'to': 'next tuesday'}).status_code == 422
    # A date and time without an offset is the user's own (UTC in tests).
    ok(client.post('/api/debug-time/jump', json={'to': '2026-10-06T09:30'}))
    assert parse(settle(client)['now']) == START.replace(day=6, hour=9, minute=30)


def test_jumping_lives_the_days_then_returning_puts_real_time_back(client, life):
    ok(client.put('/api/settings', json={'background_activity': True}))
    send(client, 'Hi! Before the jump.', 'client-0001')
    messages_before = count(client, 'messages')
    ok(client.post('/api/debug-time/start', json={}))
    ok(client.post('/api/debug-time/jump', json={'hours': 72}))
    status = settle(client)
    assert parse(status['now']) == START + timedelta(hours=72)
    with client.app.state.database.connect() as connection:
        days = {row[0][:10] for row in connection.execute('SELECT starts_at FROM life_events')}
    assert len(days) >= 3, days
    assert count(client, 'feed_posts') > 0
    ok(client.post('/api/debug-time/finish', json={}))
    status = ok(client.get('/api/debug-time'))
    assert status['active'] is False and parse(status['now']) == START
    assert count(client, 'life_events') == 0 and count(client, 'feed_posts') == 0
    assert count(client, 'messages') == messages_before
    assert not (client.app.state.database.path.parent / 'debug-time' / 'before-debug.sqlite3').exists()
    # The app works on after the restore.
    send(client, 'Back in real time.', 'client-0002')


def test_keeping_what_happened(client, life):
    ok(client.put('/api/settings', json={'background_activity': True}))
    ok(client.post('/api/debug-time/start', json={}))
    ok(client.post('/api/debug-time/jump', json={'hours': 24}))
    settle(client)
    events = count(client, 'life_events')
    assert events > 0
    status = ok(client.post('/api/debug-time/finish', json={'keep': True}))
    assert status['active'] is False and status['kept'] is True and parse(status['now']) == START
    assert count(client, 'life_events') == events


def test_only_the_pc_changes_debug_time():
    from companion.phone.access import pc_only
    assert pc_only('POST', '/api/debug-time/jump') and not pc_only('GET', '/api/debug-time')
