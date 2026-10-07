"""Streaming replies from every supported provider, plus the connection test.

SSE parsing, status handling and the per-provider dispatch are adapted from prosperos-study
server/providers/http.py and completion.py at bbcbde4. Changes: requests carry the Companion's
conversation, a reply stopped at the token limit or by a content filter stays a visible incomplete
reply (its `finish_reason`) rather than an error, and Codex CLI runs through the same interface.
"""
import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx

from companion.errors import DomainError, require
from companion.providers.codex import CodexProvider
from companion.providers.discovery import discover_models
from companion.providers.discovery_errors import check_with_deadline
from companion.providers.events import Chunk, anthropic_event, chat_event, google_event, openai_event
from companion.providers.requests import REQUESTS, headers_for, validate_key

__all__ = ['INCOMPLETE', 'Chunk', 'ChatProvider']

INCOMPLETE = {'length': 'The reply stopped at the output token limit.',
              'content_filter': "The provider stopped this reply because of its content filter."}
FAILURES = {
    'tool_calls': 'The model asked to use a tool instead of replying. The Companion does not run model tools.',
    'function_call': 'The model asked to use a tool instead of replying. The Companion does not run model tools.',
    'unrecognized': 'The provider reported an unsupported completion reason. Check its model and settings.',
}
PARSERS = {'openai': openai_event, 'anthropic': anthropic_event, 'google': google_event,
           'openrouter': chat_event, 'local': chat_event, 'compatible': chat_event}


def provider_of(config: dict) -> str:
    return config.get('provider') or 'compatible'


RATE_LIMIT_ATTEMPTS = 2
RATE_LIMIT_WAIT = (1.0, 2.0, 5.0)  # Shortest, default and longest wait before the one retry, in seconds.


def retry_delay(response: httpx.Response) -> float:
    shortest, default, longest = RATE_LIMIT_WAIT
    try:
        wanted = float(response.headers.get('retry-after', default))
    except ValueError:
        wanted = default
    return min(max(wanted, shortest), longest)


def check_status(response: httpx.Response):
    descriptions = {401: "Authentication failed. Check the model profile's API key.",
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


@dataclass
class Completion:
    """Whether the service finished its reply, and whether what arrived can be a reply at all."""
    completed: bool = False
    has_text: bool = False
    reasoning: bool = False
    finish_reason: str | None = None

    def observe(self, chunk: Chunk):
        self.completed = self.completed or chunk.done or bool(chunk.finish_reason)
        self.has_text = self.has_text or bool(chunk.text.strip())
        self.reasoning = self.reasoning or chunk.reasoning
        self.finish_reason = chunk.finish_reason or self.finish_reason

    def validate(self):
        require(self.completed, 'The connection ended before the service completed its reply.', 502)
        if self.finish_reason in FAILURES:
            raise DomainError(FAILURES[self.finish_reason], 502, 'provider')
        if self.reasoning and not self.has_text and self.finish_reason not in INCOMPLETE:
            raise DomainError('The model returned reasoning but no reply text. Check its thinking settings or raise '
                              'the longest reply in Settings > Models.', 502, 'provider')


class ChatProvider:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None, codex: CodexProvider | None = None):
        self.transport = transport
        self.codex = codex or CodexProvider()

    async def stream(self, config: dict, key: str | None, system: str, messages: list[dict]) -> AsyncIterator[Chunk]:
        provider = provider_of(config)
        if provider == 'codex':
            async for chunk in self.codex.stream(config, key, system, messages):
                yield chunk
            return
        config = {**config, 'provider': provider}
        validate_key(provider, key)
        path, body = REQUESTS[provider](config, system, messages)
        try:
            async with asyncio.timeout(config['timeout_seconds']):
                async with httpx.AsyncClient(transport=self.transport, timeout=config['timeout_seconds'],
                                             follow_redirects=False, trust_env=False) as client:
                    async for chunk in self.request(client, config, key, path, body):
                        yield chunk
        except (httpx.TimeoutException, TimeoutError) as error:
            raise DomainError('The reply reached the configured time limit. Partial text is saved.', 504,
                              'timeout') from error
        except httpx.RequestError as error:
            raise DomainError('Cannot reach the model service. Check the address and that it is running.', 502,
                              'connection') from error

    async def request(self, client, config, key, path, body) -> AsyncIterator[Chunk]:
        url = config['base_url'] + path
        if config['provider'] == 'kobold':
            response = await client.post(url, headers=headers_for(config, key), json=body)
            check_status(response)
            yield kobold_result(response)
            return
        completion, parser = Completion(), PARSERS[config['provider']]
        for attempt in range(RATE_LIMIT_ATTEMPTS):
            async with client.stream('POST', url, headers=headers_for(config, key), json=body) as response:
                if response.status_code == 429 and attempt + 1 < RATE_LIMIT_ATTEMPTS:
                    # Hosted models answer 429 for a few seconds at busy times; one short wait usually clears it.
                    await asyncio.sleep(retry_delay(response))
                    continue
                check_status(response)
                async for data in sse_data(response):
                    chunk = Chunk(done=True) if data.get('_done') else parser(data)
                    completion.observe(chunk)
                    if chunk.text or chunk.finish_reason:
                        yield chunk
            break
        completion.validate()

    async def check(self, config: dict, key: str | None) -> dict:
        """List the service's models without generating anything."""
        if config['provider'] == 'codex':
            return await self.codex.check(config, key)
        validate_key(config['provider'], key)
        async with httpx.AsyncClient(transport=self.transport, timeout=15, trust_env=False,
                                     follow_redirects=False) as client:
            return await check_with_deadline(discover_models, client, config, key)


def kobold_result(response: httpx.Response) -> Chunk:
    try:
        text = response.json()['results'][0]['text']
        require(isinstance(text, str), 'Kobold returned an invalid text result.', 502)
        return Chunk(text, 'stop', done=True)
    except (ValueError, KeyError, IndexError, TypeError) as error:
        raise DomainError('Kobold did not return a readable reply.', 502) from error
