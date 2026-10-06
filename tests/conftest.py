import asyncio
import json
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from companion.clock import FixedClock
from companion.identity import CLIENT_HEADER
from companion.life import composer
from companion.main import create_app
from companion.providers.chat import Chunk
from companion.providers.vault import MemoryVault

START = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


class FakeProvider:
    """Records each request and replies with scripted chunks."""

    def __init__(self):
        self.requests = []
        self.replies = []
        self.before_finish = None
        self.error = None
        self.respond = None
        self.delay = 0

    async def stream(self, config, key, system, messages):
        self.requests.append({'config': config, 'key': key, 'system': system, 'messages': messages})
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        if self.respond:
            chunks = self.respond(system, messages)
        else:
            chunks = self.replies.pop(0) if self.replies else [Chunk('Hello again.'), Chunk('', 'stop')]
        for chunk in chunks:
            yield chunk
        if self.before_finish:
            self.before_finish()


@pytest.fixture(autouse=True)
def no_pc_timezone(monkeypatch):
    """Tests run in UTC whatever the machine's zone is; test_local_zone sets one where it needs it."""
    monkeypatch.setattr('companion.local_zone.detect', lambda: None)


@pytest.fixture(autouse=True)
def no_storylines(monkeypatch):
    """Storylines start on seeded days (companion/life/storylines.py) and would add context lines and first
    messages to unrelated tests; tests/test_storylines.py turns them back on."""
    monkeypatch.setattr('companion.life.storylines.START', (0, 0, 0, 0))
    # Likewise a birthday seeded by the companion's id (companion/life/occasions.py).
    monkeypatch.setattr('companion.life.occasions.SEEDED', False)
    # And replies held while the companion is busy (companion/life/pacing.py), on by default in the app.
    monkeypatch.setattr('companion.life.pacing.ACTIVE', False)
    # And days going off plan (companion/life/disruptions.py), which would move seeded schedules by chance.
    monkeypatch.setattr('companion.life.disruptions.ACTIVE', False)
    # And friends' gatherings and run-ins (companion/life/network.py), which add people met by chance.
    monkeypatch.setattr('companion.life.network.ACTIVE', False)


@pytest.fixture(autouse=True)
def no_unasked_pictures(monkeypatch):
    """Unasked chat pictures are a seeded chance; test_chat_photos turns them on where it needs them."""
    monkeypatch.setattr('companion.images.photos.UNASKED', False)


@pytest.fixture
def clock():
    return FixedClock(START)


@pytest.fixture
def provider():
    return FakeProvider()


@pytest.fixture
def app(tmp_path, clock, provider):
    return create_app(tmp_path / 'workspace' / 'companion.sqlite3', clock=clock, vault=MemoryVault(),
                      provider=provider, life_tasks=False)


@pytest.fixture
def client(app):
    with TestClient(app, headers={CLIENT_HEADER: 'workspace'}) as test_client:
        yield test_client


@pytest.fixture
def companion(client):
    response = client.post('/api/companion', json={'name': 'Mira', 'personality': 'Warm and curious',
                                                     'timezone': 'Europe/Lisbon'})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def connected(client, companion):
    response = client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                                   'api_key': 'secret-key'})
    assert response.status_code == 200, response.text
    return response.json()


def send(client, text, client_id):
    response = client.post('/api/conversation/messages', json={'text': text, 'client_id': client_id})
    assert response.status_code == 200, response.text
    return response.json()


def life_reply(system, messages):
    if 'Rephrase one ordinary moment' not in system:
        return [Chunk('Hello again.'), Chunk('', 'stop')]
    facts = json.loads(messages[-1]['content'])
    payload = {'summary': f"Phrased: {facts['summary']}", 'post': 'Lovely light today.'}
    return [Chunk(json.dumps(payload)), Chunk('', 'stop')]


@pytest.fixture
def life(provider, connected, monkeypatch):
    """A connected model that phrases events, with no randomly quiet slots or plans, so counts are exact."""
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(composer, 'PLAN_SHARE', 0)
    monkeypatch.setattr(composer, 'THREAD_SHARE', 0)
    provider.respond = life_reply
    return provider


def reconcile(client):
    response = client.post('/api/life/reconcile', json={'mode': 'return'})
    assert response.status_code == 200, response.text
    return response.json()


def set_life(client, **values):
    response = client.put('/api/life/settings', json=values)
    assert response.status_code == 200, response.text
    return response.json()
