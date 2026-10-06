"""OpenAI-compatible embeddings for semantic recall (PRD M10).

The Companion never downloads embedding weights: semantic recall uses the `/embeddings` endpoint of
the model profile assigned to recall when it names an embedding model, and keyword recall alone
otherwise. Only OpenAI, local and OpenAI-compatible profiles offer embeddings.
"""
import asyncio

import httpx

from companion.errors import DomainError, require
from companion.providers.chat import check_status, provider_of
from companion.providers.config import EMBEDDING_PROVIDERS
from companion.providers.requests import headers_for, validate_key

# Embedding the message being answered must not hold up the reply for long.
QUERY_TIMEOUT = 2


class EmbeddingProvider:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self.transport = transport

    async def embed(self, config: dict, key: str | None, texts: list[str], timeout: float | None = None
                    ) -> list[list[float]]:
        """One vector per text, in order."""
        limit = timeout or config['timeout_seconds']
        provider = provider_of(config)
        require(provider in EMBEDDING_PROVIDERS, 'Embeddings need an OpenAI, local or OpenAI-compatible profile.', 409)
        validate_key(provider, key)
        headers = headers_for({'provider': provider}, key)
        body = {'model': config['embedding_model'], 'input': texts}
        try:
            async with asyncio.timeout(limit):
                async with httpx.AsyncClient(transport=self.transport, timeout=limit, follow_redirects=False,
                                             trust_env=False) as client:
                    response = await client.post(config['base_url'] + '/embeddings', headers=headers, json=body)
                    check_status(response)
                    data = response.json().get('data')
        except (httpx.TimeoutException, TimeoutError) as error:
            raise DomainError('The embedding request timed out.', 504, 'timeout') from error
        except (httpx.RequestError, ValueError) as error:
            raise DomainError('Cannot reach the embedding service.', 502, 'connection') from error
        require(isinstance(data, list) and len(data) == len(texts), 'The service returned the wrong embeddings.', 502)
        ordered = sorted(data, key=lambda item: item.get('index', 0))
        vectors = [item.get('embedding') for item in ordered]
        require(all(isinstance(vector, list) and vector for vector in vectors), 'The service returned empty embeddings.',
                502)
        return [[float(value) for value in vector] for vector in vectors]
