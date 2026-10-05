"""Runs queued memory formation in the background, after replies and never in front of one (PRD M7)."""
import asyncio

from companion.memory.formation import run_pending

YIELD_SECONDS = 0.5


class MemoryWorker:
    def __init__(self, database, scheduler, enabled=True):
        self.database = database
        self.scheduler = scheduler
        self.enabled = enabled
        self.task: asyncio.Task | None = None

    def kick(self):
        """Start draining the queue unless a drain is already running. Safe to call often."""
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
                result = await asyncio.to_thread(run_pending, self.database)
            except Exception:  # noqa: BLE001 - memory work is optional; the next kick retries.
                return
            if not result['processed']:
                return
