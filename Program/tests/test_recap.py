"""While you were away (companion/recap.py): a catch-up after a few days without a message."""
from datetime import timedelta

from conftest import send
from test_social_circle import make

from companion.characters import require_current
from companion.database import identifier


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def event(client, summary, at, kind='ordinary'):
    database = client.app.state.database
    with database.connect(write=True) as connection:
        companion = require_current(connection)
        connection.execute(
            "INSERT INTO life_events (id, companion_id, timeline_id, idempotency_key, kind, status, summary, starts_at, "
            "ends_at, character_version_id, permission_revision, created_at, decided_at) "
            "VALUES (?, ?, ?, ?, ?, 'committed', ?, ?, ?, ?, 1, ?, ?)",
            (identifier(), companion['id'], companion['active_timeline_id'], identifier(), kind, summary, at, at,
             companion['active_version_id'], at, at))


def away(client, clock, days):
    clock.instant = clock.now() + timedelta(days=days)


def test_coming_back_after_a_few_days_brings_a_catch_up_once(client, clock, provider):
    make(client, 'Warm and curious.')
    ok(client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model'}))
    send(client, 'See you soon!', 'before-away')
    assert ok(client.get('/api/conversation/recap'))['recap'] is None  # Not away yet.
    away(client, clock, 2)
    event(client, 'Mira went to a pottery class with Dana', (clock.now()).isoformat())
    assert ok(client.get('/api/conversation/recap'))['recap'] is None  # Two days is not a while.
    away(client, clock, 5)
    event(client, 'Mira had her friends over for a game night', clock.now().isoformat(), 'plan')
    recap = ok(client.get('/api/conversation/recap'))['recap']
    assert recap['days'] == 7
    assert recap['items'][:2] == ['Mira had her friends over for a game night.', 'Mira went to a pottery class with Dana.']
    assert any('Weekly came out' in item for item in recap['items'])
    ok(client.post('/api/conversation/recap/read', json={'since': recap['since']}))
    assert ok(client.get('/api/conversation/recap'))['recap'] is None


def test_it_can_be_turned_off(client, clock):
    make(client, 'Warm and curious.')
    ok(client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model'}))
    send(client, 'Bye for now', 'before-away')
    ok(client.put('/api/life/settings', json={'recap_after_days': 0}))
    away(client, clock, 10)
    assert ok(client.get('/api/conversation/recap'))['recap'] is None


def test_a_new_chat_has_nothing_to_catch_up_on(client, clock):
    make(client, 'Warm and curious.')
    away(client, clock, 10)
    assert ok(client.get('/api/conversation/recap'))['recap'] is None
