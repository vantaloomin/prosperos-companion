"""Their day so far (companion/life/so_far.py): a reply after a photo knows what the photo showed and what today held,
so it never says the yoga class in the picture was "a couple days back"."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from companion.characters import current
from companion.clock import stamp, zone
from companion.database import encode, identifier
from companion.identity import CLIENT_HEADER
from companion.life import so_far
from companion.main import create_app
from companion.providers.vault import MemoryVault
from tests.test_chat_photos import ask
from tests.test_images import FakeAdapter, local_comfy


@pytest.fixture
def app(tmp_path, clock, provider):
    adapters = {'comfyui': FakeAdapter(), 'codex': FakeAdapter(), 'hosted': FakeAdapter()}
    return create_app(tmp_path / 'workspace' / 'companion.sqlite3', clock=clock, vault=MemoryVault(),
                      provider=provider, life_tasks=False, image_adapters=adapters)


@pytest.fixture
def client(app):
    with TestClient(app, headers={CLIENT_HEADER: 'workspace'}) as test_client:
        yield test_client


def notes(provider) -> str:
    return provider.requests[-1]['prompt']


def test_a_photo_sent_earlier_is_in_the_next_replies(client, life, clock, provider, monkeypatch):
    monkeypatch.setattr('companion.life.body.COLD_CHANCE', {'winter': 0, 'other': 0})
    local_comfy(client)
    photo = ask(client)['photo']
    assert photo and photo['summary']
    clock.advance(timedelta(minutes=40))
    ask(client, 'so was that a yoga day?', 'ask-0002')
    prompt = notes(provider)
    assert so_far.LEAD in prompt
    assert 'you sent the user a photo of what you were doing then' in prompt


def add_slot(connection, timeline_id, key, starts_at, hours, summary, kind='leisure'):
    connection.execute(
        'INSERT INTO life_agenda (id, timeline_id, subject, slot_key, starts_at, ends_at, local_date, block, entry, '
        "basis, created_at) VALUES (?, ?, 'companion', ?, ?, ?, ?, ?, ?, 'test', ?)",
        (identifier(), timeline_id, key, stamp(starts_at), stamp(starts_at + timedelta(hours=hours)),
         starts_at.date().isoformat(), encode({'kind': kind, 'label': 'Free time'}), encode({'summary': summary}),
         stamp(starts_at)))


def setup(client, app, clock):
    """A companion with today's agenda replaced by a night's sleep, a yoga class from 07:00 and climbing tonight."""
    ask(client)
    with app.state.database.connect(write=True) as connection:
        companion = current(connection)
        timeline_id = companion['active_timeline_id']
        connection.execute('DELETE FROM life_agenda')
        local = clock.now().astimezone(zone(companion['version']['timezone']))
        morning = local.replace(hour=7, minute=0, second=0, microsecond=0)
        add_slot(connection, timeline_id, 'k:night', morning - timedelta(hours=7), 7, 'Mira slept.', 'sleep')
        add_slot(connection, timeline_id, 'k:yoga', morning, 2, 'Mira went to a yoga class at Lotus Studio.')
        add_slot(connection, timeline_id, 'k:later', morning + timedelta(hours=12), 2, 'Mira went climbing.')
    return companion, morning


def test_the_slots_of_today_that_began_are_listed_and_later_ones_are_not(client, life, app, clock):
    companion, morning = setup(client, app, clock)
    with app.state.database.connect() as connection:
        [(_identity, text)] = so_far.lines(connection, companion, morning + timedelta(hours=3))
        [(_identity, during)] = so_far.lines(connection, companion, morning + timedelta(hours=1))
    assert text.splitlines() == [so_far.LEAD, '- Earlier today, 07:00-09:00: Mira went to a yoga class at Lotus Studio.']
    assert '- Now (since 07:00, until 09:00; still going): Mira went to a yoga class' in during
    assert 'climbing' not in text and 'slept' not in text


def test_a_slot_already_told_as_an_event_is_left_to_the_recent_life(client, life, app, clock):
    companion, morning = setup(client, app, clock)
    timeline_id = companion['active_timeline_id']
    with app.state.database.connect(write=True) as connection:
        connection.execute(
            'INSERT INTO life_events (id, companion_id, timeline_id, idempotency_key, kind, status, summary, starts_at, '
            "ends_at, character_version_id, permission_revision, created_at) VALUES (?, ?, ?, ?, 'routine', "
            "'committed', 'Mira went to a yoga class.', ?, ?, ?, 1, ?)",
            (identifier(), companion['id'], timeline_id, f'life:{timeline_id}:k:yoga#r2', stamp(morning),
             stamp(morning + timedelta(hours=2)), companion['active_version_id'], stamp(morning)))
        assert so_far.lines(connection, companion, morning + timedelta(hours=3)) == []
