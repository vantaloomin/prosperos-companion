import asyncio
import json
import threading
import time

from companion.conversation import Conversation
from companion.memory import context
from companion.models import MessageCreate
from companion.providers.chat import Chunk


def parse_events(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split('\n\n'):
        lines = dict(line.split(': ', 1) for line in block.splitlines())
        events.append((lines['event'], json.loads(lines['data'])))
    return events


class GatedProvider:
    """Sends its first piece, then waits until released before sending the rest."""

    def __init__(self):
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def stream(self, config, key, system, messages):
        yield Chunk('First part. ')
        self.started.set()
        await self.release.wait()
        yield Chunk('And the rest.')
        yield Chunk('', 'stop')


def test_send_without_waiting_returns_the_saved_attempt(client, connected):
    result = client.post('/api/conversation/messages?wait=false', json={'text': 'Hi', 'client_id': 'client-0001'})
    assert result.status_code == 200, result.text
    reply = result.json()['reply']
    assert reply['role'] == 'companion'
    events = parse_events(client.get(f"/api/conversation/replies/{reply['id']}/events").text)
    name, final = events[-1]
    assert name == 'done'
    assert final['status'] == 'complete'
    assert final['text'] == 'Hello again.'


def test_events_for_a_finished_reply_send_only_the_saved_reply(client, connected):
    result = client.post('/api/conversation/messages', json={'text': 'Hi', 'client_id': 'client-0001'}).json()
    events = parse_events(client.get(f"/api/conversation/replies/{result['reply']['id']}/events").text)
    assert [name for name, _ in events] == ['done']
    assert events[0][1]['id'] == result['reply']['id']


def test_events_for_an_unknown_reply_are_not_found(client, connected):
    assert client.get('/api/conversation/replies/missing/events').status_code == 404


def test_stream_sends_snapshot_then_new_text_then_the_saved_reply(app, connected):
    gated = GatedProvider()
    conversation = Conversation(app.state.database, app.state.vault, gated)

    async def scenario():
        result = await conversation.send(MessageCreate(text='Hi', client_id='client-0001'), wait=False)
        assert result['reply']['status'] == 'streaming'
        await gated.started.wait()
        events = conversation.events(result['reply']['id'])
        first = await anext(events)
        gated.release.set()
        return [first] + [event async for event in events]

    events = asyncio.run(scenario())
    assert events[0] == ('snapshot', {'id': events[0][1]['id'], 'text': 'First part. '})
    assert events[1][0] == 'delta' and events[1][1]['text'] == 'And the rest.'
    assert events[-1][0] == 'done'
    assert events[-1][1]['status'] == 'complete'
    assert events[-1][1]['text'] == 'First part. And the rest.'


def test_closing_a_stream_does_not_stop_the_reply(app, connected):
    gated = GatedProvider()
    conversation = Conversation(app.state.database, app.state.vault, gated)

    async def scenario():
        result = await conversation.send(MessageCreate(text='Hi', client_id='client-0001'), wait=False)
        await gated.started.wait()
        events = conversation.events(result['reply']['id'])
        await anext(events)
        await events.aclose()
        gated.release.set()
        await conversation.running[result['reply']['id']].task
        return conversation.reply(result['reply']['id'])

    reply = asyncio.run(scenario())
    assert reply['status'] == 'complete'
    assert reply['text'] == 'First part. And the rest.'


def test_retrying_a_send_while_streaming_follows_the_same_reply(app, connected):
    gated = GatedProvider()
    conversation = Conversation(app.state.database, app.state.vault, gated)

    async def scenario():
        body = MessageCreate(text='Hi', client_id='client-0001')
        first = await conversation.send(body, wait=False)
        await gated.started.wait()
        second = await conversation.send(body, wait=False)
        gated.release.set()
        await conversation.running[first['reply']['id']].task
        return first, second

    first, second = asyncio.run(scenario())
    assert first['reply']['id'] == second['reply']['id']


class GatedEmbedder:
    """Holds the query embedding until released, like a slow service or one busy with background work."""

    def __init__(self):
        self.release = asyncio.Event()

    async def embed(self, config, key, texts, timeout):
        await self.release.wait()
        return [[1.0, 0.0] for _ in texts]


def test_send_without_waiting_returns_before_recall_and_lookups(app, client, companion, provider):
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'embedding_model': 'embed'})
    embedder = GatedEmbedder()
    conversation = Conversation(app.state.database, app.state.vault, provider, embedder=embedder)

    async def scenario():
        result = await asyncio.wait_for(
            conversation.send(MessageCreate(text='Hi', client_id='client-0001'), wait=False), 1)
        assert result['reply']['status'] == 'streaming' and provider.requests == []
        client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Home city', 'value': 'Lisbon'})
        embedder.release.set()
        await conversation.running[result['reply']['id']].task
        return conversation.reply(result['reply']['id'])

    reply = asyncio.run(scenario())
    # Built after the memory was added, so it uses it and is not withheld for it.
    assert reply['status'] == 'complete' and 'Home city: Lisbon' in provider.requests[0]['system']


def test_context_build_does_not_hold_the_event_loop(app, client, companion, provider, monkeypatch):
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model'})
    conversation = Conversation(app.state.database, app.state.vault, provider)
    building, release = threading.Event(), threading.Event()
    real_build = context.build

    def slow_build(*args, **kwargs):
        building.set()
        release.wait(5)
        return real_build(*args, **kwargs)

    monkeypatch.setattr(context, 'build', slow_build)

    async def scenario():
        result = await conversation.send(MessageCreate(text='Hi', client_id='client-0001'), wait=False)
        await asyncio.wait_for(asyncio.to_thread(building.wait, 2), 3)
        # Released from the loop: a build on the loop would hold it until its own timeout.
        release.set()
        await conversation.running[result['reply']['id']].task
        return conversation.reply(result['reply']['id'])

    started = time.perf_counter()
    assert asyncio.run(scenario())['status'] == 'complete'
    # A build holding the loop would take the full 5 seconds; a busy Windows runner can need just over 2
    # for the whole reply, so the margin sits between the two.
    assert time.perf_counter() - started < 4
