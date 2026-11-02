"""A companion's day that fails in the background is logged, not dropped (tester, 2026-11-01: a whole day with no feed
posts and nothing in the log). The same failure again within the hour is logged once."""
import asyncio
import logging
from datetime import timedelta


def test_a_failing_day_in_the_background_is_logged_once_an_hour(client, companion, clock, caplog, monkeypatch):
    engine = client.app.state.life

    async def broken(mode='return', companion_id=None):
        raise KeyError('neighborhoods')

    monkeypatch.setattr(engine, 'reconcile', broken)
    with caplog.at_level(logging.ERROR, logger='companion.life.simulation'):
        asyncio.run(engine.quietly('background'))
        asyncio.run(engine.quietly('background'))
        failed = [record for record in caplog.records if "day could not move on" in record.getMessage()]
        assert len(failed) == 1 and failed[0].exc_info[0] is KeyError
        clock.advance(timedelta(hours=1))
        asyncio.run(engine.quietly('background'))
        assert len([record for record in caplog.records if "day could not move on" in record.getMessage()]) == 2
