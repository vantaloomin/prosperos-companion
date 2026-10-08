"""Semantic recall through the connection's embeddings endpoint, with keyword fallback (PRD M10, M12)."""
import asyncio
import re

import pytest
from conftest import send

from companion.errors import DomainError
from companion.identity import CLIENT_HEADER
from companion.main import create_app
from companion.providers.vault import MemoryVault

# Words that mean the same thing share a dimension, so similarity works without shared keywords.
CONCEPTS = {'dog': 0, 'puppy': 0, 'pup': 0, 'hound': 0, 'tea': 1, 'genmaicha': 1, 'brew': 1, 'sea': 2, 'ocean': 2,
            'beach': 2, 'swim': 2}


class FakeEmbedder:
    def __init__(self):
        self.calls = []
        self.error = None

    async def embed(self, config, key, texts, timeout=None):
        self.calls.append(texts)
        if self.error:
            raise self.error
        vectors = []
        for text in texts:
            vector = [0.0] * 4
            for word in re.findall(r'\w+', text.lower()):
                vector[CONCEPTS.get(word, 3)] += 1.0 if word in CONCEPTS else 0.05
            vectors.append(vector)
        return vectors


@pytest.fixture
def embedder():
    return FakeEmbedder()


@pytest.fixture
def app(tmp_path, clock, provider, embedder):
    return create_app(tmp_path / 'workspace' / 'companion.sqlite3', clock=clock, vault=MemoryVault(),
                      provider=provider, life_tasks=False, embedder=embedder)


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient
    with TestClient(app, headers={CLIENT_HEADER: 'workspace'}) as test_client:
        yield test_client


def configure(client, model='embed-small'):
    response = client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                                   'embedding_model': model})
    assert response.status_code == 200, response.text


def history_with_old_fact(client, fact='I adopted a hound named Rex'):
    send(client, fact, 'semantic-0000')
    for index in range(1, 17):
        send(client, f'Small talk number {index}', f'semantic-{index:04d}')


def index(app):
    return asyncio.run(app.state.memory.index())


def recalled(provider):
    match = re.search(r'## Possibly relevant memories\n(.*?)(?=\n## |\Z)', provider.requests[-1]['prompt'], re.S)
    return match.group(1) if match else ''


def test_without_an_embedding_model_recall_is_keyword_only(client, app, companion, provider, embedder):
    configure(client, model='')
    history_with_old_fact(client)
    assert index(app) == 0
    send(client, 'How is my puppy doing?', 'semantic-0099')
    assert 'hound' not in recalled(provider)
    assert embedder.calls == []


def test_semantic_recall_finds_related_words(client, app, companion, provider):
    configure(client)
    history_with_old_fact(client)
    assert index(app) > 0
    while index(app):  # Indexing goes in batches.
        pass
    reply = send(client, 'How is my puppy doing?', 'semantic-0099')['reply']
    assert 'hound named Rex' in recalled(provider)
    assert reply['status'] == 'complete'
    preview = client.get('/api/context/preview').json()
    assert preview['receipt']['semantic_recall'] is False, 'the preview has no query to embed'


def test_embedding_failure_falls_back_to_keywords(client, app, companion, provider, embedder):
    configure(client)
    history_with_old_fact(client)
    index(app)
    embedder.error = DomainError('down', 502)
    reply = send(client, 'How is my puppy doing?', 'semantic-0099')['reply']
    assert reply['status'] == 'complete'
    assert 'hound' not in recalled(provider)


def test_excluded_and_deleted_memories_are_never_ranked(client, app, companion, provider):
    configure(client)
    memory = client.post('/api/memories', json={'layer': 'shared_experience', 'subject': 'Beach day',
                                                'value': 'We talked about the ocean at sunset'}).json()
    index(app)
    send(client, 'I want to swim at the sea', 'semantic-0001')
    assert 'ocean at sunset' in recalled(provider)
    client.post(f"/api/memories/{memory['id']}/exclude")
    send(client, 'I want to swim at the sea again', 'semantic-0002')
    assert 'ocean' not in recalled(provider)
    client.post(f"/api/memories/{memory['id']}/delete", json={'delete_sources': False})
    with app.state.database.connect() as connection:
        rows = connection.execute("SELECT COUNT(*) FROM memory_vectors WHERE owner_id=?", (memory['id'],)).fetchone()
    assert rows[0] == 0


def test_redacting_a_message_deletes_its_vector(client, app, companion):
    configure(client)
    message = send(client, 'My hound is called Rex', 'semantic-0001')['message']
    memory = client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Dog', 'value': 'Rex',
                                                'source_message_ids': [message['id']]}).json()
    index(app)
    client.post(f"/api/memories/{memory['id']}/delete", json={'delete_sources': True})
    with app.state.database.connect() as connection:
        left = connection.execute('SELECT owner_id FROM memory_vectors').fetchall()
    assert message['id'] not in {row[0] for row in left} and memory['id'] not in {row[0] for row in left}


def test_a_corrected_memory_is_embedded_again(client, app, companion):
    configure(client)
    memory = client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Drink', 'value': 'Tea'}).json()
    index(app)
    corrected = client.post(f"/api/memories/{memory['id']}/correct",
                            json={'value': 'Genmaicha tea', 'expected_revision': 1}).json()
    with app.state.database.connect() as connection:
        owners = {row[0] for row in connection.execute('SELECT owner_id FROM memory_vectors')}
    assert memory['id'] not in owners and corrected['id'] not in owners
    index(app)
    with app.state.database.connect() as connection:
        owners = {row[0] for row in connection.execute('SELECT owner_id FROM memory_vectors')}
    assert corrected['id'] in owners

