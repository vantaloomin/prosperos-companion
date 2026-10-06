"""Your timezone comes from this PC unless you pick one yourself."""
import sqlite3

import pytest
from fastapi.testclient import TestClient

from companion import local_zone
from companion.database import Database
from companion.identity import CLIENT_HEADER
from companion.main import create_app
from companion.providers.vault import MemoryVault


def open_app(path, monkeypatch, detected):
    monkeypatch.setattr('companion.local_zone.detect', lambda: detected)
    app = create_app(path, vault=MemoryVault(), life_tasks=False)
    return TestClient(app, headers={CLIENT_HEADER: 'workspace'})


def put(client, **values):
    response = client.put('/api/settings', json=values)
    assert response.status_code == 200, response.text
    return response.json()


def test_new_workspace_takes_the_pc_timezone(tmp_path, monkeypatch):
    with open_app(tmp_path / 'companion.sqlite3', monkeypatch, 'America/New_York') as client:
        settings = client.get('/api/settings').json()
    assert settings['user_timezone'] == 'America/New_York'
    assert settings['user_timezone_source'] == 'pc'
    assert settings['system_timezone'] == 'America/New_York'


def test_undetectable_pc_keeps_utc(client):
    settings = client.get('/api/settings').json()
    assert (settings['user_timezone'], settings['user_timezone_source'], settings['system_timezone']) == \
        ('UTC', 'default', None)


def test_the_interface_reports_the_browser_zone_until_the_user_picks_one(client):
    assert put(client, user_timezone='America/New_York', user_timezone_source='detected')['user_timezone_source'] \
        == 'pc'
    chosen = put(client, user_timezone='Europe/Berlin')
    assert (chosen['user_timezone'], chosen['user_timezone_source']) == ('Europe/Berlin', 'chosen')
    # A detected zone never replaces one the user picked.
    assert put(client, user_timezone='America/New_York', user_timezone_source='detected')['user_timezone'] \
        == 'Europe/Berlin'
    # Use this PC's timezone does, and the workspace follows the PC again.
    back = put(client, user_timezone='America/New_York', user_timezone_source='pc')
    assert (back['user_timezone'], back['user_timezone_source']) == ('America/New_York', 'pc')
    assert put(client, user_timezone='America/Chicago', user_timezone_source='detected')['user_timezone'] \
        == 'America/Chicago'


def test_unknown_detected_zone_is_refused(client):
    response = client.put('/api/settings', json={'user_timezone': 'Mars/Olympus', 'user_timezone_source': 'detected'})
    assert response.status_code == 422


def test_pc_zone_follows_on_startup_but_a_chosen_one_stays(tmp_path, monkeypatch):
    path = tmp_path / 'companion.sqlite3'
    with open_app(path, monkeypatch, 'America/New_York'):
        pass
    with open_app(path, monkeypatch, 'Europe/London') as client:
        assert client.get('/api/settings').json()['user_timezone'] == 'Europe/London'
        put(client, user_timezone='Asia/Tokyo')
    with open_app(path, monkeypatch, 'America/New_York') as client:
        assert client.get('/api/settings').json()['user_timezone'] == 'Asia/Tokyo'


@pytest.mark.parametrize(('stored', 'expected'), [('UTC', 'America/New_York'), ('America/Denver', 'America/Denver')])
def test_existing_workspace_keeps_a_zone_set_before_this_version(tmp_path, monkeypatch, stored, expected):
    path = tmp_path / 'companion.sqlite3'
    database = Database(path)
    with database.connect(write=True) as connection:
        connection.execute('UPDATE workspace_settings SET user_timezone=? WHERE id=1', (stored,))
        connection.execute("DELETE FROM app_identity WHERE key IN ('schema_digest', 'app_version')")
        connection.execute('ALTER TABLE workspace_settings DROP COLUMN user_timezone_source')
    with open_app(path, monkeypatch, 'America/New_York') as client:
        assert client.get('/api/settings').json()['user_timezone'] == expected
    assert 'user_timezone_source' in {row[1] for row in sqlite3.connect(path).execute(
        'PRAGMA table_info(workspace_settings)')}


def test_windows_zone_names_map_to_iana(monkeypatch):
    assert local_zone.WINDOWS_ZONES['Eastern Standard Time'] == 'America/New_York'
    assert all(local_zone.valid(name) for name in local_zone.WINDOWS_ZONES.values())


def test_posix_zone_reads_the_tz_variable(monkeypatch):
    monkeypatch.setenv('TZ', ':America/Phoenix')
    assert local_zone.posix_zone() == 'America/Phoenix'
    assert local_zone.valid('Not/AZone') is None
