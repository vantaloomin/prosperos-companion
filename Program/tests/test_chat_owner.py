"""What happens in one companion's chat stays with that companion, whoever is in focus when the work finishes:
memories, her own facts, the reply itself, and messages sent from a window still showing that chat."""
import asyncio
import json

from conftest import send
from test_chats import another

from companion.conversation import Conversation
from companion.models import MessageCreate
from companion.providers.chat import Chunk

LONG = 'Honestly the thing that keeps me going lately is my weekly pottery class with Jun'


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def focus(client, companion_id):
    return ok(client.post('/api/companion/cast/focus', json={'companion_id': companion_id}))


def memories_of(client, companion_id):
    with client.app.state.database.connect() as connection:
        return [row[0] for row in connection.execute(
            "SELECT value FROM memories WHERE companion_id=? AND status='active'", (companion_id,))]


def test_a_model_found_memory_goes_to_the_chat_it_came_from(client, app, connected, provider):
    def respond(system, messages):
        if 'help a companion app remember' not in system:
            return [Chunk('Hello again.'), Chunk('', 'stop')]
        return [Chunk(json.dumps([{'message': 1, 'layer': 'user_fact', 'subject': 'Hobby',
                                   'value': 'weekly pottery class with Jun'}])), Chunk('', 'stop')]
    provider.respond = respond
    mira = connected and ok(client.get('/api/companion'))['companion']
    sally, _timeline = another(client)
    send(client, LONG, 'owner-0001')
    client.post('/api/memory/run')
    focus(client, sally)  # The user opens Sally's chat before the model has read Mira's message.
    asyncio.run(app.state.memory.suggest())
    assert memories_of(client, mira['id']) == ['weekly pottery class with Jun']
    assert memories_of(client, sally) == []


def test_remember_this_keeps_it_with_the_companion_whose_chat_it_is(client, connected):
    mira = ok(client.get('/api/companion'))['companion']
    sally, _timeline = another(client)
    message = send(client, 'I live in Chicago', 'owner-0001')['message']
    focus(client, sally)  # Another window (or the phone) switched to Sally.
    ok(client.post(f"/api/conversation/messages/{message['id']}/remember"))
    assert 'Chicago' in memories_of(client, mira['id'])
    assert memories_of(client, sally) == []


def test_a_memory_written_in_a_window_names_its_companion(client, connected):
    mira = ok(client.get('/api/companion'))['companion']
    sally, _timeline = another(client)
    focus(client, sally)
    ok(client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Pet', 'value': 'Has a cat called Miso',
                                          'companion_id': mira['id']}))
    assert memories_of(client, mira['id']) == ['Has a cat called Miso']
    assert memories_of(client, sally) == []


def test_a_message_from_a_window_still_showing_a_chat_lands_in_that_chat(client, connected):
    mira = ok(client.get('/api/companion'))['companion']
    sally, sally_timeline = another(client)
    focus(client, sally)
    sent = ok(client.post('/api/conversation/messages', json={'text': 'Still here?', 'client_id': 'owner-0001',
                                                              'companion_id': mira['id']}))
    assert sent['message']['timeline_id'] == mira['active_timeline_id'] != sally_timeline
    assert sent['reply']['status'] == 'complete'
    assert ok(client.get('/api/companion'))['companion']['id'] == mira['id']


class WaitingProvider:
    """Writes the reply only once the test lets it, so the user can open another chat meanwhile."""

    def __init__(self):
        self.started, self.go = asyncio.Event(), asyncio.Event()

    async def stream(self, config, key, system, messages):
        self.started.set()
        await self.go.wait()
        yield Chunk('Here I am.')
        yield Chunk('', 'stop')


def test_opening_another_chat_while_she_writes_does_not_lose_her_reply(app, client, connected):
    mira = ok(client.get('/api/companion'))['companion']
    sally, _timeline = another(client)
    waiting = WaitingProvider()
    conversation = Conversation(app.state.database, app.state.vault, waiting)

    async def scenario():
        sending = asyncio.create_task(conversation.send(MessageCreate(text='Hi', client_id='owner-0001')))
        await waiting.started.wait()
        await asyncio.to_thread(focus, client, sally)
        waiting.go.set()
        return await sending

    reply = asyncio.run(scenario())['reply']
    assert reply['status'] == 'complete' and reply['timeline_id'] == mira['active_timeline_id']


def stopped_reply(client, text='I was going to say'):
    """A reply the user stopped part way."""
    sent = send(client, 'Tell me about your day', 'stop-0001')
    with client.app.state.database.connect(write=True) as connection:
        connection.execute("UPDATE messages SET status='cancelled', error='Stopped.', active=0, text=? WHERE id=?",
                           (text, sent['reply']['id']))
    return sent['reply']


def test_a_stopped_reply_can_be_edited_and_becomes_the_kept_reply(client, connected):
    reply = stopped_reply(client)
    edited = ok(client.post(f"/api/conversation/messages/{reply['id']}/edit",
                            json={'text': 'I was going to say I missed you.', 'expected_text': 'I was going to say'}))
    assert edited['text'] == 'I was going to say I missed you.'
    [shown] = [message for message in ok(client.get('/api/conversation'))['messages'] if message['id'] == reply['id']]
    assert shown['status'] == 'complete' and shown['active'] and shown['error'] is None


def test_a_stopped_reply_can_be_kept_as_it_is(client, connected):
    reply = stopped_reply(client)
    ok(client.post(f"/api/conversation/messages/{reply['id']}/edit",
                   json={'text': 'I was going to say', 'expected_text': 'I was going to say'}))
    [shown] = [message for message in ok(client.get('/api/conversation'))['messages'] if message['id'] == reply['id']]
    assert shown['status'] == 'complete' and shown['active']
