"""Streaming OpenAI-compatible chat completions.

SSE parsing and status handling are adapted from prosperos-study server/providers/http.py at
bbcbde4. The Companion starts with one connection type: any OpenAI-compatible endpoint, which
covers hosted APIs and local servers such as LM Studio. Other adapters need their own evidence.
"""
import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx

from companion.errors import DomainError, require

INCOMPLETE = {'length': 'The reply stopped at the output token limit.',
              'content_filter': "The provider stopped this reply because of its content filter."}


@dataclass
class Chunk:
    text: str = ''
    finish_reason: str | None = None


def check_status(response: httpx.Response):
    descriptions = {401: "Authentication failed. Check the connection's API key.",
                    403: 'This account cannot access the selected service or model.',
                    404: 'The service did not recognize this model or address.',
                    429: 'The service reached a rate or usage limit. Retry when it is available.'}
    if not response.is_success:
        raise DomainError(descriptions.get(response.status_code,
                          f'The service rejected this request (HTTP {response.status_code}).'), 502, 'provider')


async def sse_data(response: httpx.Response) -> AsyncIterator[dict]:
    lines = []
    async for line in response.aiter_lines():
        if line.startswith('data:'):
            lines.append(line[5:].lstrip())
        elif not line and lines:
            yield parse_sse('\n'.join(lines))
            lines = []
    if lines:
        yield parse_sse('\n'.join(lines))


def parse_sse(value: str) -> dict:
    if value == '[DONE]':
        return {'_done': True}
    try:
        data = json.loads(value)
        require(isinstance(data, dict), 'The service returned an invalid stream event.', 502)
        return data
    except json.JSONDecodeError as error:
        raise DomainError('The service returned a malformed stream event.', 502) from error


def chunk_from(data: dict) -> Chunk:
    choices = data.get('choices') or [{}]
    choice = choices[0] if isinstance(choices[0], dict) else {}
    delta = choice.get('delta') or {}
    text = delta.get('content') if isinstance(delta.get('content'), str) else ''
    return Chunk(text, choice.get('finish_reason'))


class ChatProvider:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self.transport = transport

    async def stream(self, config: dict, key: str | None, system: str, messages: list[dict]) -> AsyncIterator[Chunk]:
        body = {'model': config['model'], 'stream': True, 'max_tokens': config['max_output_tokens'],
                'messages': [{'role': 'system', 'content': system}, *messages]}
        headers = {'Authorization': f'Bearer {key}'} if key else {}
        try:
            async with asyncio.timeout(config['timeout_seconds']):
                async with httpx.AsyncClient(transport=self.transport, timeout=config['timeout_seconds'],
                                             follow_redirects=False, trust_env=False) as client:
                    async with client.stream('POST', config['base_url'] + '/chat/completions',
                                             headers=headers, json=body) as response:
                        check_status(response)
                        async for data in sse_data(response):
                            if data.get('_done'):
                                return
                            yield chunk_from(data)
        except (httpx.TimeoutException, TimeoutError) as error:
            raise DomainError('The reply reached the configured time limit. Partial text is saved.', 504,
                              'timeout') from error
        except httpx.RequestError as error:
            raise DomainError('Cannot reach the model service. Check the address and that it is running.', 502,
                              'connection') from error
