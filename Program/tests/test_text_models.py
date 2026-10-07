"""Settings > Models: profiles per provider, the connection test, job assignments and the move
from the single connection that came before profiles."""
import asyncio
import json
import sqlite3

import httpx
import pytest
from conftest import send

from companion import text_models
from companion.database import initialize
from companion.errors import DomainError
from companion.main import create_app
from companion.providers.chat import ChatProvider, Chunk
from companion.providers.requests import REQUESTS, headers_for, transcript
from companion.providers.vault import MemoryVault

LOCAL = {'provider': 'local', 'model': 'local-model'}
ANTHROPIC = {'provider': 'anthropic', 'model': 'claude-sonnet-5-5', 'max_output_tokens': 1000}


def add(client, config, name='', api_key=None, status=201):
    response = client.post('/api/models/profiles', json={'name': name, 'config': config, 'api_key': api_key})
    assert response.status_code == status, response.text
    return response.json()


def test_the_first_finished_profile_answers_in_chat_and_other_jobs_inherit_it(client, companion, provider):
    unfinished = add(client, {'provider': 'openrouter'}, api_key='or-key')
    assert not unfinished['ready'] and unfinished['has_saved_key']
    assert client.get('/api/models').json()['routes'] == {}
    local = add(client, LOCAL)
    overview = client.get('/api/models').json()
    assert overview['routes'] == {'chat': local['id']}
    assert {job['key'] for job in overview['jobs']} == {'chat', 'life', 'memory', 'drafting', 'sidecar', 'vision', 'story',
                                                       'recall'}
    with client.app.state.database.connect() as connection:
        assert text_models.config_for(connection, 'drafting')['profile_id'] == local['id']
    assert client.get('/api/connection').json()['connection']['provider'] == 'local'
    send(client, 'Hi', 'client-message-1')
    assert provider.requests[-1]['config']['model'] == 'local-model'


def test_a_job_can_use_its_own_profile(client, companion, provider):
    add(client, LOCAL)
    claude = add(client, ANTHROPIC, api_key='sk-ant')
    response = client.put('/api/models/routes', json={'job': 'drafting', 'profile_id': claude['id']})
    assert response.status_code == 200, response.text
    provider.respond = lambda system, messages: [Chunk('{"name": "Dana"}'), Chunk('', 'stop')]
    client.post('/api/companion/draft', json={'idea': 'a nurse'})
    drafted = provider.requests[-1]
    assert drafted['config']['provider'] == 'anthropic' and drafted['key'] == 'sk-ant'
    send(client, 'Hi', 'client-message-2')
    assert provider.requests[-1]['config']['provider'] == 'local'
    # Clearing the assignment falls back to the conversation profile.
    client.put('/api/models/routes', json={'job': 'drafting', 'profile_id': None})
    with client.app.state.database.connect() as connection:
        assert text_models.config_for(connection, 'drafting')['provider'] == 'local'


RECALL = {'provider': 'local', 'base_url': 'http://127.0.0.1:11434/v1', 'purpose': 'recall',
          'embedding_model': 'qwen3-embedding'}


def test_recall_has_its_own_profile_apart_from_text_profiles(client, companion):
    chat = add(client, {**ANTHROPIC}, api_key='anthropic-key')
    recall = add(client, RECALL)
    assert not recall['ready'] and recall['recall_ready'] and recall['name'] == 'Local / LM Studio · qwen3-embedding'
    assert client.get('/api/models').json()['routes'] == {'chat': chat['id'], 'recall': recall['id']}
    with client.app.state.database.connect() as connection:
        assert text_models.config_for(connection, 'recall')['embedding_model'] == 'qwen3-embedding'
        assert text_models.config_for(connection, 'drafting')['profile_id'] == chat['id']
    assert client.put('/api/models/routes', json={'job': 'drafting', 'profile_id': recall['id']}).status_code == 409
    assert client.put('/api/models/routes', json={'job': 'recall', 'profile_id': chat['id']}).status_code == 409
    emptied = client.put(f"/api/models/profiles/{recall['id']}", json={
        'name': '', 'config': {**RECALL, 'embedding_model': ''}, 'expected_revision': 1})
    assert emptied.status_code == 409
    add(client, {**LOCAL, 'embedding_model': 'nomic-embed'}, status=422)
    add(client, {**ANTHROPIC, 'purpose': 'recall', 'embedding_model': 'x'}, status=422)


def test_without_a_recall_profile_the_conversation_profile_does_not_do_recall(client, companion):
    add(client, LOCAL)
    with client.app.state.database.connect() as connection:
        assert text_models.config_for(connection, 'recall') is None


def test_an_embedding_model_on_a_text_profile_moves_to_its_own_recall_profile(client, app, companion):
    claude = add(client, ANTHROPIC, api_key='sk-ant')
    local = add(client, LOCAL, api_key='local-key')
    with app.state.database.connect(write=True) as connection:
        config = json.loads(connection.execute('SELECT config FROM model_profiles WHERE id=?', (local['id'],)).fetchone()[0])
        connection.execute('UPDATE model_profiles SET config=? WHERE id=?',
                           (json.dumps({**config, 'embedding_model': 'nomic-embed'}), local['id']))
        connection.execute("INSERT INTO model_routes (job, profile_id, updated_at) VALUES ('recall', ?, 'x')", (local['id'],))
    for _ in range(2):
        with app.state.database.connect(write=True) as connection:
            text_models.split_recall(connection, '2026-10-07T12:00:00Z')
    overview = client.get('/api/models').json()
    recall = [profile for profile in overview['profiles'] if profile['recall_ready']]
    assert len(recall) == 1 and recall[0]['config']['embedding_model'] == 'nomic-embed' and recall[0]['has_saved_key']
    assert overview['routes']['recall'] == recall[0]['id'] and overview['routes']['chat'] == claude['id']
    text = next(profile for profile in overview['profiles'] if profile['id'] == local['id'])
    assert text['ready'] and not text['config']['embedding_model']
    # The shared key stays until neither profile uses it.
    client.delete(f"/api/models/profiles/{local['id']}")
    with app.state.database.connect() as connection:
        assert text_models.key_for(app.state.vault, text_models.config_for(connection, 'recall')) == 'local-key'
    client.delete(f"/api/models/profiles/{recall[0]['id']}")
    assert list(app.state.vault.secrets) == [claude_key(app, claude)]


def claude_key(app, claude):
    with app.state.database.connect() as connection:
        return connection.execute('SELECT credential_ref FROM model_profiles WHERE id=?', (claude['id'],)).fetchone()[0]


def test_official_addresses_and_adapter_limits_are_enforced(client):
    add(client, {**ANTHROPIC, 'base_url': 'https://example.com/v1'}, status=422)
    add(client, {**ANTHROPIC, 'temperature': 1.5}, status=422)
    add(client, {**LOCAL, 'base_url': 'http://192.168.1.20:1234/v1'}, status=422)
    add(client, {'provider': 'openai', 'model': 'gpt', 'top_k': 5}, status=422)
    add(client, {'provider': 'codex', 'model': 'gpt-5'}, api_key='nope', status=422)
    official = add(client, {'provider': 'openai', 'model': 'gpt'})
    assert official['config']['base_url'] == 'https://api.openai.com/v1'


def test_a_saved_key_never_follows_a_changed_address(client, app):
    vault = app.state.vault
    profile = add(client, {'provider': 'compatible', 'model': 'm', 'base_url': 'https://one.example/v1'}, api_key='k1')
    reference = next(iter(vault.secrets))
    same = client.put(f"/api/models/profiles/{profile['id']}", json={
        'name': 'Renamed', 'config': {'provider': 'compatible', 'model': 'm2', 'base_url': 'https://one.example/v1'},
        'expected_revision': profile['revision']}).json()
    assert same['has_saved_key'] and same['name'] == 'Renamed' and vault.secrets == {reference: 'k1'}
    moved = client.put(f"/api/models/profiles/{profile['id']}", json={
        'config': {'provider': 'compatible', 'model': 'm2', 'base_url': 'https://two.example/v1'},
        'expected_revision': same['revision']}).json()
    assert not moved['has_saved_key'] and vault.secrets == {}
    stale = client.put(f"/api/models/profiles/{profile['id']}", json={
        'config': {'provider': 'compatible', 'model': 'm3', 'base_url': 'https://two.example/v1'},
        'expected_revision': same['revision']})
    assert stale.status_code == 409


def test_deleting_a_profile_removes_its_key_and_jobs(client, app):
    local = add(client, LOCAL)
    claude = add(client, ANTHROPIC, api_key='sk-ant')
    client.put('/api/models/routes', json={'job': 'life', 'profile_id': claude['id']})
    result = client.delete(f"/api/models/profiles/{claude['id']}").json()
    assert result['routes'] == {'chat': local['id']} and app.state.vault.secrets == {}


def test_a_profile_doing_a_job_must_keep_a_model(client):
    local = add(client, LOCAL)
    response = client.put(f"/api/models/profiles/{local['id']}", json={
        'config': {'provider': 'local', 'model': ''}, 'expected_revision': local['revision']})
    assert response.status_code == 409


def test_the_single_connection_becomes_the_conversation_profile_once(tmp_path, clock):
    path = tmp_path / 'workspace' / 'companion.sqlite3'
    vault = MemoryVault()
    vault.put('text-connection', 'old-key')
    app = create_app(path, clock=clock, vault=vault, life_tasks=False)
    with app.state.database.connect(write=True) as connection:
        connection.execute("INSERT INTO connection (id, base_url, model, credential_ref, max_output_tokens, "
                           "context_tokens, timeout_seconds, embedding_model, updated_at) VALUES "
                           "(1, 'https://api.example.com/v1', 'old-model', 'text-connection', 900, 900, 60, 'emb', 'x')")
    for _ in range(2):  # Every start runs the same initialization; only the first adopts.
        raw = sqlite3.connect(path)
        initialize(raw, '2026-10-05T12:00:00Z')
        raw.commit()
        raw.close()
    with app.state.database.connect() as connection:
        profiles = connection.execute('SELECT * FROM model_profiles').fetchall()
        assert len(profiles) == 2  # The text profile and, for its embedding model, a recall profile.
        assert connection.execute('SELECT COUNT(*) FROM connection').fetchone()[0] == 0
        config = text_models.config_for(connection, 'chat')
        # Settings the old form allowed (no room left for input) survive the move untouched.
        assert config['provider'] == 'compatible' and config['model'] == 'old-model'
        assert config['context_tokens'] == 900 and not config['embedding_model']
        assert text_models.key_for(vault, config) == 'old-key'
        recall = text_models.config_for(connection, 'recall')
        assert recall['embedding_model'] == 'emb' and text_models.key_for(vault, recall) == 'old-key'


def test_a_loopback_connection_becomes_a_local_profile(client, companion):
    summary = client.put('/api/connection', json={'base_url': 'http://localhost:1234/v1', 'model': 'm'}).json()
    assert summary['provider'] == 'local'
    again = client.put('/api/connection', json={'base_url': 'http://localhost:1234/v1', 'model': 'm2'}).json()
    assert again['profile_id'] == summary['profile_id'] and again['model'] == 'm2'


# --- Provider adapters ----------------------------------------------------------------------------

CONVERSATION = [{'role': 'assistant', 'content': 'Morning!'}, {'role': 'user', 'content': 'Hi'},
                {'role': 'user', 'content': 'Still there?'}]


def config(provider, **extra):
    return {'provider': provider, 'model': 'm', 'base_url': 'https://x.example/v1', 'max_output_tokens': 300,
            'context_tokens': 4000, 'timeout_seconds': 10, **extra}


def test_anthropic_and_gemini_get_alternating_turns_that_open_with_the_user():
    path, body = REQUESTS['anthropic'](config('anthropic', thinking_mode='adaptive'), 'sys', CONVERSATION)
    assert path == '/messages' and body['system'] == 'sys'
    assert [message['role'] for message in body['messages']] == ['user', 'assistant', 'user']
    assert body['messages'][-1]['content'] == 'Hi\n\nStill there?'
    assert body['thinking'] == {'type': 'adaptive'}
    path, body = REQUESTS['google'](config('google', model='models/gemini-3'), 'sys', CONVERSATION)
    assert path == '/models/gemini-3:streamGenerateContent?alt=sse'
    assert [content['role'] for content in body['contents']] == ['user', 'model', 'user']
    assert headers_for(config('anthropic'), 'k')['x-api-key'] == 'k'
    assert headers_for(config('google'), 'k')['x-goog-api-key'] == 'k'


def test_openai_uses_responses_and_compatible_services_use_chat_completions():
    path, body = REQUESTS['openai'](config('openai', reasoning_effort='low'), 'sys', CONVERSATION)
    assert path == '/responses' and body['instructions'] == 'sys' and body['store'] is False
    assert body['input'][0] == {'role': 'assistant', 'content': 'Morning!'} and body['reasoning'] == {'effort': 'low'}
    path, body = REQUESTS['compatible'](config('compatible', output_token_parameter='max_completion_tokens'), 'sys',
                                        CONVERSATION)
    assert path == '/chat/completions' and body['max_completion_tokens'] == 300
    assert body['messages'][0] == {'role': 'system', 'content': 'sys'}
    path, body = REQUESTS['openrouter'](config('openrouter'), 'sys', CONVERSATION)
    assert body['provider'] == {'allow_fallbacks': False, 'require_parameters': True}
    path, body = REQUESTS['kobold'](config('kobold'), 'sys', CONVERSATION)
    assert body['prompt'] == transcript('sys', CONVERSATION) and body['prompt'].endswith('Assistant:')


def sse(events):
    return ''.join(f'data: {json.dumps(event)}\n\n' for event in events)


def collect(provider, settings, key='k'):
    async def run():
        return [chunk async for chunk in provider.stream(settings, key, 'sys', [{'role': 'user', 'content': 'hi'}])]
    return asyncio.run(run())


def test_anthropic_stream_is_read_to_its_stop_reason():
    seen = {}

    def handler(request):
        seen['url'] = str(request.url)
        return httpx.Response(200, text=sse([
            {'type': 'message_start', 'message': {'usage': {'input_tokens': 3}}},
            {'type': 'content_block_delta', 'delta': {'type': 'text_delta', 'text': 'Hel'}},
            {'type': 'content_block_delta', 'delta': {'type': 'text_delta', 'text': 'lo'}},
            {'type': 'message_delta', 'delta': {'stop_reason': 'max_tokens'}},
            {'type': 'message_stop'}]))
    settings = {**config('anthropic'), 'base_url': 'https://api.anthropic.com/v1'}
    chunks = collect(ChatProvider(httpx.MockTransport(handler)), settings)
    assert ''.join(chunk.text for chunk in chunks) == 'Hello' and chunks[-1].finish_reason == 'length'
    assert seen['url'] == 'https://api.anthropic.com/v1/messages'


def test_a_stream_that_never_finishes_is_an_error():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=sse([
        {'choices': [{'delta': {'content': 'Hel'}}]}])))
    with pytest.raises(DomainError) as error:
        collect(ChatProvider(transport), config('compatible'))
    assert 'ended before' in error.value.message


def test_hosted_providers_need_a_key():
    with pytest.raises(DomainError) as error:
        collect(ChatProvider(httpx.MockTransport(lambda request: httpx.Response(500))), config('openrouter'), key=None)
    assert error.value.status == 409


def test_testing_a_form_lists_models_with_their_reported_limits(tmp_path, clock):
    seen = {}

    def handler(request):
        seen['auth'] = request.headers.get('authorization')
        return httpx.Response(200, json={'data': [
            {'id': 'anthropic/claude-sonnet-5.5', 'name': 'Claude Sonnet 5.5', 'context_length': 200000,
             'top_provider': {'max_completion_tokens': 64000}, 'supported_parameters': ['temperature', 'reasoning']},
            {'id': 'mystery/model'}]})
    app = create_app(tmp_path / 'w' / 'companion.sqlite3', clock=clock, vault=MemoryVault(),
                     provider=ChatProvider(httpx.MockTransport(handler)), life_tasks=False)
    from fastapi.testclient import TestClient

    from companion.identity import CLIENT_HEADER
    with TestClient(app, headers={CLIENT_HEADER: 'workspace'}) as client:
        missing = client.post('/api/models/discover', json={'config': {'provider': 'openrouter'}})
        assert missing.status_code == 409
        result = client.post('/api/models/discover', json={'config': {'provider': 'openrouter'}, 'api_key': 'or'})
        assert result.status_code == 200, result.text
        details = {model['id']: model for model in result.json()['model_details']}
        assert details['anthropic/claude-sonnet-5.5']['context_tokens'] == 200000
        assert details['anthropic/claude-sonnet-5.5']['max_output_tokens'] == 64000
        assert details['mystery/model']['limit_source'] == 'unreported'
        assert seen['auth'] == 'Bearer or'
        # A saved profile's key is reused for its own test, never typed again.
        profile = add(client, {'provider': 'openrouter'}, api_key='saved')
        client.post('/api/models/discover', json={'config': {'provider': 'openrouter'}, 'profile_id': profile['id']})
        assert seen['auth'] == 'Bearer saved'
        assert client.post(f"/api/models/profiles/{profile['id']}/check").status_code == 200
