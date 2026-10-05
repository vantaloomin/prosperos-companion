from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from companion.clock import FixedClock
from companion.identity import CLIENT_HEADER
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

    async def stream(self, config, key, system, messages):
        self.requests.append({'config': config, 'key': key, 'system': system, 'messages': messages})
        if self.error:
            raise self.error
        for chunk in (self.replies.pop(0) if self.replies else [Chunk('Hello again.'), Chunk('', 'stop')]):
            yield chunk
        if self.before_finish:
            self.before_finish()


@pytest.fixture
def clock():
    return FixedClock(START)


@pytest.fixture
def provider():
    return FakeProvider()


@pytest.fixture
def app(tmp_path, clock, provider):
    return create_app(tmp_path / 'workspace' / 'companion.sqlite3', clock=clock, vault=MemoryVault(),
                      provider=provider)


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
