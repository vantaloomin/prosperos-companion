"""Runs queued memory work in the background, after replies and never in front of one (PRD M7, M10).

A drain forms memories from queued messages, then embeds memories and messages that lack a vector
when an embedding model is configured. Both steps yield to the conversation.
"""
import asyncio

from companion.characters import require_current
from companion.database import optional
from companion.memory import vectors
from companion.memory.formation import run_pending
from companion.providers.embeddings import EmbeddingProvider
from companion.providers.scheduling import MAINTENANCE
from companion.providers.vault import credential_for

YIELD_SECONDS = 0.5


class MemoryWorker:
    def __init__(self, database, scheduler, vault=None, embedder=None, enabled=True):
        self.database = database
        self.scheduler = scheduler
        self.vault = vault
        self.embedder = embedder or EmbeddingProvider()
        self.enabled = enabled
        self.task: asyncio.Task | None = None

    def kick(self):
        """Start draining unless a drain is already running. Safe to call often."""
        if not self.enabled or (self.task is not None and not self.task.done()):
            return
        try:
            self.task = asyncio.get_running_loop().create_task(self.drain())
        except RuntimeError:
            self.task = None

    async def drain(self):
        while True:
            while self.scheduler.foreground:
                await asyncio.sleep(YIELD_SECONDS)
            try:
                formed = (await asyncio.to_thread(run_pending, self.database))['processed']
                indexed = await self.index()
            except Exception:  # noqa: BLE001 - memory work is optional; the next kick retries.
                return
            if not formed and not indexed:
                return

    async def index(self) -> int:
        """Embed one batch of memories and messages without a current vector. Returns how many were saved."""
        with self.database.connect() as connection:
            config = optional(connection, 'SELECT * FROM connection WHERE id=1')
            if not config or not config.get('embedding_model'):
                return 0
            timeline_id = require_current(connection)['active_timeline_id']
            items = vectors.missing(connection, config['embedding_model'], timeline_id)
        if not items:
            return 0
        key = credential_for(self.vault, config['credential_ref'])
        async with self.scheduler.reserve(config, MAINTENANCE):
            found = await self.embedder.embed(config, key, [text for _kind, _id, text in items])
        with self.database.connect(write=True) as connection:
            return vectors.store(connection, config['embedding_model'], items, found, self.database.now())
