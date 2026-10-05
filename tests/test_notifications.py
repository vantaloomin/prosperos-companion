"""Desktop notifications (PRD compute and job control, C6, M4)."""
import asyncio
from datetime import timedelta

import pytest
from conftest import send, set_life


def configure(client, **values):
    response = client.put('/api/notifications/settings', json=values)
    assert response.status_code == 200, response.text
    return response.json()


def check(client, focused=False):
    response = client.post('/api/notifications/next', json={'focused': focused})
    assert response.status_code == 200, response.text
    return response.json()


def background(app, client, clock, hours=20):
    clock.advance(timedelta(hours=hours))
    asyncio.run(app.state.life.reconcile('background'))
    return client.get('/api/feed').json()['posts']


@pytest.fixture
def active(client, life):
    client.put('/api/settings', json={'background_activity': True, 'user_timezone': 'UTC'})
    set_life(client, automatic_events=True)
    return life


def test_off_by_default_queues_nothing(app, client, active, clock):
    settings = client.get('/api/notifications/settings').json()
    assert settings['enabled'] is False and settings['queued'] == 0
    assert len(background(app, client, clock)) == 1
    assert client.get('/api/notifications/settings').json()['queued'] == 0
    assert check(client) == {'notification': None, 'held': 'off'}


def test_one_new_post_is_announced_once_with_name_only_preview(app, client, active, clock):
    configure(client, enabled=True, quiet_start='00:00', quiet_end='00:00')
    send(client, 'Talk soon', 'client-notify-01')
    post = background(app, client, clock, hours=26)[0]
    shown = check(client)['notification']
    assert shown['kind'] == 'post' and shown['post_ids'] == [post['id']]
    assert shown['title'] == 'Mira' and shown['body'] == 'Mira shared something new.'
    assert check(client) == {'notification': None, 'held': None}


def test_preview_privacy(app, client, active, clock):
    configure(client, enabled=True, quiet_start='00:00', quiet_end='00:00', preview='private')
    background(app, client, clock)
    assert check(client)['notification'] | {'id': None, 'post_ids': None} == {
        'id': None, 'post_ids': None, 'kind': 'post', 'title': 'Prospero Companion', 'body': 'Something new is waiting.'}
    configure(client, preview='full', min_gap_minutes=30)
    background(app, client, clock, hours=6)
    assert check(client)['notification']['body'] == 'Lovely light today.'


def test_quiet_hours_hold_and_missed_posts_collapse_into_one_digest(app, client, active, clock):
    # 08:00 and 14:00 UTC fall inside quiet hours from 07:00 to 15:00.
    configure(client, enabled=True, quiet_start='07:00', quiet_end='15:00', preview='full')
    background(app, client, clock)
    assert check(client) == {'notification': None, 'held': 'quiet_hours'}
    background(app, client, clock, hours=6)
    assert check(client)['held'] == 'quiet_hours'
    clock.advance(timedelta(hours=1, minutes=30))
    shown = check(client)['notification']
    assert shown['kind'] == 'digest' and len(shown['post_ids']) == 2
    assert shown['body'].startswith('Mira shared 2 new moments. Latest: ')
    assert check(client)['notification'] is None


def test_quiet_hours_can_cross_midnight():
    from datetime import datetime

    from companion.notifications import in_quiet_hours
    assert in_quiet_hours(datetime(2026, 1, 1, 23, 30), '22:00', '08:00')
    assert in_quiet_hours(datetime(2026, 1, 1, 7, 59), '22:00', '08:00')
    assert not in_quiet_hours(datetime(2026, 1, 1, 8, 0), '22:00', '08:00')
    assert not in_quiet_hours(datetime(2026, 1, 1, 8, 0), '00:00', '00:00')


def test_daily_cap_and_minimum_gap(app, client, active, clock):
    configure(client, enabled=True, quiet_start='00:00', quiet_end='00:00', daily_cap=1, min_gap_minutes=60)
    background(app, client, clock)
    assert check(client)['notification'] is not None
    background(app, client, clock, hours=6)
    assert check(client)['held'] == 'daily_cap'
    configure(client, daily_cap=3, min_gap_minutes=720)
    assert check(client)['held'] == 'min_gap'
    clock.advance(timedelta(hours=7))
    assert check(client)['notification']['kind'] == 'post'


def test_focused_app_waits_and_read_posts_are_dropped(app, client, active, clock):
    configure(client, enabled=True, quiet_start='00:00', quiet_end='00:00')
    background(app, client, clock)
    assert check(client, focused=True)['held'] == 'focused'
    client.post('/api/feed/read')
    assert check(client) == {'notification': None, 'held': None}
    assert client.get('/api/notifications/settings').json()['queued'] == 0


def test_turning_off_or_revoking_background_cancels_queued(app, client, active, clock):
    configure(client, enabled=True, quiet_start='00:00', quiet_end='23:59')
    background(app, client, clock)
    assert configure(client, enabled=False)['queued'] == 0
    configure(client, enabled=True)
    assert check(client)['notification'] is None
    background(app, client, clock, hours=6)
    assert client.get('/api/notifications/settings').json()['queued'] == 1
    client.put('/api/settings', json={'background_activity': False})
    assert client.get('/api/notifications/settings').json()['queued'] == 0


def test_absence_traits_change_wording_but_never_frequency(app, client, active, clock):
    current = client.get('/api/companion').json()['companion']
    definition = {**current['version']['definition'],
                  'emotional_traits': [{'name': 'guilt over absence', 'intensity': 'strong'}]}
    client.post('/api/companion/versions', json={'definition': definition,
                                                 'expected_version_id': current['active_version_id']})
    configure(client, enabled=True, quiet_start='00:00', quiet_end='00:00', daily_cap=1)
    send(client, 'Talk soon', 'client-notify-01')
    background(app, client, clock, hours=26)
    shown = check(client)['notification']
    assert shown['body'] == 'Did you forget about me? Mira shared something new.'
    background(app, client, clock, hours=10)
    assert check(client)['held'] == 'daily_cap'
    settings = client.get('/api/notifications/settings').json()
    assert settings['daily_cap'] == 1 and 'forget' not in str(settings)


def test_settings_are_validated(client, companion):
    assert client.put('/api/notifications/settings', json={'quiet_start': '25:00'}).status_code == 422
    assert client.put('/api/notifications/settings', json={'daily_cap': 50}).status_code == 422
    assert configure(client, quiet_start='7:5')['quiet_start'] == '07:05'


def test_restore_turns_notifications_off(app, client, active, clock, tmp_path):
    from companion import backup
    configure(client, enabled=True)
    created = client.post('/api/backups', json={}).json()
    restored = backup.restore(created['path'], tmp_path / 'restored' / 'companion.sqlite3', clock)
    with restored.connect() as connection:
        assert connection.execute('SELECT enabled FROM notification_settings').fetchone()[0] == 0
