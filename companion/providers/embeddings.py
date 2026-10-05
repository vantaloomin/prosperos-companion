"""OpenAI-compatible embeddings for semantic recall (PRD M10).

The Companion never downloads embedding weights: semantic recall uses the configured connection's
`/embeddings` endpoint when an embedding model is named, and keyword recall alone otherwise.
"""
import asyncio

import httpx

from companion.errors import DomainError, require
from companion.providers.chat import check_status

# Embedding the message being answered must not hold up the reply for long.
QUERY_TIMEOUT = 2


class EmbeddingProvider:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self.transport = transport

    async def embed(self, config: dict, key: str | None, texts: list[str], timeout: float | None = None
                    ) -> list[list[float]]:
        """One vector per text, in order."""
        limit = timeout or config['timeout_seconds']
        headers = {'Authorization': f'Bearer {key}'} if key else {}
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
