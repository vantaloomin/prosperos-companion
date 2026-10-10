"""Runs queued memory work in the background, after replies and never in front of one (PRD M7, M10).

A drain forms memories from queued messages, then embeds memories and messages that lack a vector
when an embedding model is configured, then (hourly at most) writes episode summaries and merge
proposals. Every step yields to the conversation.
"""
import asyncio
import time

from companion.characters import require_current
from companion.database import settings
from companion.life import storylines
from companion.memory import consolidation, self_suggest, vectors
from companion.memory import suggest as model_suggestions
from companion.memory.formation import run_pending
from companion.providers.embeddings import EmbeddingProvider, as_documents, vector_model
from companion.providers.scheduling import MAINTENANCE
from companion.text_models import config_for, key_for

YIELD_SECONDS = 0.5
CONSOLIDATE_SECONDS = 3600


class MemoryWorker:
    def __init__(self, database, scheduler, vault=None, embedder=None, enabled=True, provider=None):
        self.database = database
        self.scheduler = scheduler
        self.vault = vault
        self.embedder = embedder or EmbeddingProvider()
        self.provider = provider
        self.enabled = enabled
        # One drain per world: a drain waiting on the model in the world just left must not hold up the one entered.
        self.tasks: dict[str, asyncio.Task] = {}
        self.consolidated_at = -CONSOLIDATE_SECONDS

    def kick(self):
        """Start draining this world unless its drain is already running. Safe to call often."""
        world = str(self.database.path)
        running = self.tasks.get(world)
        if not self.enabled or (running is not None and not running.done()):
            return
        try:
            with self.database.pin():  # The drain finishes the work of the world it was started in.
                self.tasks[world] = asyncio.get_running_loop().create_task(self.drain())
        except RuntimeError:
            self.tasks.pop(world, None)

    async def drain(self):
        while True:
            while self.scheduler.foreground:
                await asyncio.sleep(YIELD_SECONDS)
            try:
                formed = (await asyncio.to_thread(run_pending, self.database))['processed']
                indexed = await self.index()
                suggested = await self.suggest()
                read = await self.read_self_facts()
                if not formed and not indexed and not suggested and not read:
                    await self.consolidate()
                    return
            except Exception:  # noqa: BLE001 - memory work is optional; the next kick retries.
                return

    async def suggest(self) -> int:
        if self.provider is None:
            return 0
        return await model_suggestions.suggest(self.database, self.provider, self.scheduler,
                                     lambda config: key_for(self.vault, config))

    async def read_self_facts(self) -> int:
        if self.provider is None:
            return 0
        return await self_suggest.suggest(self.database, self.provider, self.scheduler,
                                          lambda config: key_for(self.vault, config))

    async def consolidate(self):
        """At most once per CONSOLIDATE_SECONDS, and only while automatic memory is on (M11)."""
        if time.monotonic() - self.consolidated_at < CONSOLIDATE_SECONDS:
            return
        with self.database.connect() as connection:
            if not settings(connection)['automatic_memory']:
                return
        self.consolidated_at = time.monotonic()
        await asyncio.to_thread(consolidation.run, self.database)

    async def index(self) -> int:
        """Embed one batch of memories, messages and old storylines without a current vector. Returns how many were saved."""
        with self.database.connect() as connection:
            config = config_for(connection, 'recall')
            if not config or not config.get('embedding_model'):
                return 0
            companion = require_current(connection)
            stories = storylines.recall_items(connection, companion, self.database.clock.now())
            items = vectors.missing(connection, vector_model(config), companion['active_timeline_id'], stories=stories)
        if not items:
            return 0
        key = key_for(self.vault, config)
        async with self.scheduler.reserve(config, MAINTENANCE):
            found = await self.embedder.embed(config, key, as_documents(config, [text for _kind, _id, text in items]))
        with self.database.connect(write=True) as connection:
            return vectors.store(connection, vector_model(config), items, found, self.database.now())
