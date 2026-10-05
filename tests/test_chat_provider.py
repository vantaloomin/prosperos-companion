import asyncio
import json

import httpx
import pytest

from companion.errors import DomainError
from companion.providers.chat import ChatProvider

CONFIG = {'base_url': 'http://127.0.0.1:1234/v1', 'model': 'm', 'max_output_tokens': 100, 'timeout_seconds': 10}


def collect(provider, key=None):
    async def run():
        return [chunk async for chunk in provider.stream(CONFIG, key, 'system text', [{'role': 'user', 'content': 'hi'}])]
    return asyncio.run(run())


def test_streams_openai_compatible_events():
    seen = {}

    def handler(request):
        seen['body'] = json.loads(request.content)
        seen['auth'] = request.headers.get('authorization')
        events = [{'choices': [{'delta': {'content': 'Hel'}}]},
                  {'choices': [{'delta': {'content': 'lo'}, 'finish_reason': 'stop'}]}]
        body = ''.join(f'data: {json.dumps(event)}\n\n' for event in events) + 'data: [DONE]\n\n'
        return httpx.Response(200, text=body, headers={'content-type': 'text/event-stream'})

    chunks = collect(ChatProvider(httpx.MockTransport(handler)), 'k')
    assert ''.join(chunk.text for chunk in chunks) == 'Hello'
    assert chunks[-1].finish_reason == 'stop'
    assert seen['body']['messages'][0] == {'role': 'system', 'content': 'system text'}
    assert seen['auth'] == 'Bearer k'


def test_authentication_failure_is_reported():
    provider = ChatProvider(httpx.MockTransport(lambda request: httpx.Response(401)))
    with pytest.raises(DomainError) as error:
        collect(provider)
    assert 'Authentication failed' in error.value.message


def test_unreachable_service_is_a_connection_error():
    def handler(request):
        raise httpx.ConnectError('refused')
    with pytest.raises(DomainError) as error:
        collect(ChatProvider(httpx.MockTransport(handler)))
    assert error.value.code == 'connection'
