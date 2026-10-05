import asyncio

from conftest import send

from companion.conversation import Conversation, recover
from companion.errors import DomainError
from companion.memory import records
from companion.models import MemoryCreate, MessageCreate
from companion.providers.chat import Chunk


def test_message_is_kept_without_a_model_connection(client, companion):
    result = send(client, 'Hi Mira', 'client-0001')
    assert result['connection'] == 'not_configured'
    assert result['reply'] is None
    messages = client.get('/api/conversation').json()['messages']
    assert [message['text'] for message in messages] == ['Hi Mira']


def test_reply_becomes_the_active_response(client, connected, provider):
    result = send(client, 'Hi Mira', 'client-0001')
    assert result['reply']['status'] == 'complete'
    assert result['reply']['active'] is True
    assert result['reply']['text'] == 'Hello again.'
    request = provider.requests[0]
    assert request['key'] == 'secret-key'
    assert request['messages'][-1] == {'role': 'user', 'content': 'Hi Mira'}
    assert 'You are Mira' in request['system']


def test_saved_connection_never_exposes_the_key(client, connected):
    assert 'secret-key' not in str(client.get('/api/connection').json())
    assert connected['has_key'] is True


def test_retrying_a_send_does_not_duplicate_messages(client, connected, provider):
    first = send(client, 'Hi Mira', 'client-0001')
    second = send(client, 'Hi Mira', 'client-0001')
    assert first['reply']['id'] == second['reply']['id']
    assert len(provider.requests) == 1
    assert len(client.get('/api/conversation').json()['messages']) == 2


def test_unreachable_model_keeps_the_users_text(client, connected, provider):
    provider.error = DomainError('Cannot reach the model service.', 502, 'connection')
    result = send(client, 'Are you there?', 'client-0001')
    assert result['message']['text'] == 'Are you there?'
    assert result['reply']['status'] == 'failed'
    assert result['reply']['active'] is False


def test_token_limit_reply_stays_visibly_incomplete(client, connected, provider):
    provider.replies = [[Chunk('Well, I was going to'), Chunk('', 'length')]]
    reply = send(client, 'Tell me a story', 'client-0001')['reply']
    assert reply['status'] == 'incomplete'
    assert reply['active'] is False
    assert reply['text'] == 'Well, I was going to'


def test_alternative_preserves_the_earlier_wording(client, connected, provider):
    provider.replies = [[Chunk('First.')], [Chunk('Second.')]]
    first = send(client, 'Hi', 'client-0001')
    second = client.post(f"/api/conversation/messages/{first['message']['id']}/alternatives").json()
    messages = {message['id']: message for message in client.get('/api/conversation').json()['messages']}
    assert messages[first['reply']['id']]['text'] == 'First.'
    assert messages[first['reply']['id']]['active'] is False
    assert messages[second['reply']['id']]['active'] is True


def test_alternative_does_not_see_the_reply_it_replaces(client, connected, provider):
    provider.replies = [[Chunk('First.')], [Chunk('Second.')]]
    first = send(client, 'Hi', 'client-0001')
    client.post(f"/api/conversation/messages/{first['message']['id']}/alternatives")
    assert provider.requests[1]['messages'] == [{'role': 'user', 'content': 'Hi'}]


def test_alternatives_only_for_the_latest_message(client, connected):
    first = send(client, 'One', 'client-0001')
    send(client, 'Two', 'client-0002')
    response = client.post(f"/api/conversation/messages/{first['message']['id']}/alternatives")
    assert response.status_code == 409


def test_correction_during_generation_withholds_the_stale_reply(client, app, connected, provider):
    database = app.state.database
    provider.before_finish = lambda: records.remember(
        database, MemoryCreate(layer='user_fact', subject='Home city', value='Boston'))
    reply = send(client, 'Hi', 'client-0001')['reply']
    assert reply['status'] == 'withheld'
    assert reply['active'] is False


def test_interrupted_reply_is_marked_incomplete_on_start(app, connected):
    database = app.state.database
    with database.connect(write=True) as connection:
        timeline = connection.execute('SELECT active_timeline_id FROM companions').fetchone()[0]
        connection.execute("INSERT INTO messages (id, timeline_id, seq, role, text, status, active, created_at) "
                           "VALUES ('m1', ?, 1, 'companion', 'Half', 'streaming', 0, ?)", (timeline, database.now()))
    recover(database)
    with database.connect() as connection:
        assert connection.execute("SELECT status FROM messages WHERE id='m1'").fetchone()[0] == 'incomplete'


class BlockingProvider:
    def __init__(self):
        self.started = asyncio.Event()

    async def stream(self, config, key, system, messages):
        yield Chunk('Partial ')
        self.started.set()
        await asyncio.Event().wait()


def test_stop_keeps_partial_text_as_cancelled(app, connected):
    blocking = BlockingProvider()
    conversation = Conversation(app.state.database, app.state.vault, blocking)

    async def scenario():
        sending = asyncio.create_task(conversation.send(MessageCreate(text='Hi', client_id='client-0001')))
        await blocking.started.wait()
        assert conversation.stop(next(iter(conversation.running)))
        return await sending

    reply = asyncio.run(scenario())['reply']
    assert reply['status'] == 'cancelled'
    assert reply['text'] == 'Partial '
