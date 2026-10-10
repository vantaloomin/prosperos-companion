"""How the app's own work grows with the number of worlds, and what automatic backups cost (docs/scale.md).

Run from Program/:  python scripts/bench_worlds.py [--max 50] [--heavy 25] [--speed 0.25] [--out results.json]

It builds a throwaway data folder in a temporary folder (nothing of yours is touched). The first world grows to
`--heavy` companions the way bench_companions.py does it, then more personas and worlds are added, each ready at
once with its own townsfolk and starter companion, and each lives a month. At 1, 2, 5, 10, 25 and 50 worlds it
times the requests that grow with the number of worlds, switching between them, catching a world up after it was
left for a month, and an automatic backup of every world. No model is used.

`--speed` caps the process at a share of one CPU core, as in bench_companions.py.
"""
import argparse
import asyncio
import json
import platform
import sys
import tempfile
import time
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bench_companions as bench  # noqa: E402

CHECKPOINTS = (1, 2, 5, 10, 25, 50, 100)


def folder_mb(path: Path, pattern: str) -> float:
    return round(sum(item.stat().st_size for item in path.rglob(pattern) if item.is_file()) / 2 ** 20, 1)


def add_world(client, clock, number: int):
    """A new persona (named by the user, as the app never invents one) with a world of their own, which then
    lives a month while the user is in it, and a switch back to the first world."""
    persona = bench.ok(client.post('/api/worlds/personas', json={'name': f'Persona {number}'}))
    world = persona['worlds'][0]
    bench.ok(client.post(f"/api/worlds/{world['id']}/switch"))
    bench.live(client, clock, 30)
    return world['id']


def back_up_all(app) -> tuple[list[Path], float]:
    from companion import auto_backup
    state = SimpleNamespace(database=app.state.database, conversation=SimpleNamespace(running=False),
                            groups=SimpleNamespace(rounds=False))
    began = time.perf_counter()
    done = asyncio.run(auto_backup.run_once(state))
    return done, round((time.perf_counter() - began) * 1000, 1)


def measure(client, app, clock, root: Path, first: str, worlds: list[str]) -> dict:
    from fastapi.testclient import TestClient

    def cold_start():
        with TestClient(bench.make_app(root / 'companion.sqlite3', clock), headers=bench.HEADERS) as fresh:
            bench.ok(fresh.get('/api/companion'))

    other = worlds[-1]
    switch_ms = bench.timed(lambda: (bench.ok(client.post(f'/api/worlds/{other}/switch')),
                                     bench.ok(client.post(f'/api/worlds/{first}/switch'))), 3) / 2
    # The first world is left for a month while the user is in another one, then caught up on return.
    bench.ok(client.post(f'/api/worlds/{other}/switch'))
    clock.instant += timedelta(days=30)
    began = time.perf_counter()
    bench.ok(client.post(f'/api/worlds/{first}/switch'))
    bench.ok(client.post('/api/life/reconcile', json={}))
    catch_up_ms = round((time.perf_counter() - began) * 1000, 1)
    # Automatic backups go by real time; put the newest ones a day back so every world is due again.
    for zipped in root.rglob('auto-*.zip'):
        zipped.unlink()
    made, backup_ms = back_up_all(app)
    again, again_ms = back_up_all(app)
    return {
        'worlds_list_ms': bench.timed(lambda: bench.ok(client.get('/api/worlds'))),
        'switch_ms': round(switch_ms, 1),
        'month_away_catch_up_ms': catch_up_ms,
        'today_ms': bench.timed(lambda: bench.ok(client.get('/api/today'))),
        'chat_prompt_ms': bench.timed(lambda: bench.ok(client.get('/api/context/preview'))),
        'start_up_ms': bench.timed(cold_start, 3),
        'auto_backup_all_ms': backup_ms,
        'auto_backups_made': len(made),
        'auto_backup_again_ms': again_ms,
        'auto_backups_again': len(again),
        'databases_mb': folder_mb(root, 'companion.sqlite3*'),
        'auto_backups_mb': folder_mb(root, 'auto-*.zip'),
        'largest_backup_mb': round(max((path.stat().st_size for path in made), default=0) / 2 ** 20, 1),
    }


def run(limit: int, heavy: int, out: Path | None, speed: float):
    from fastapi.testclient import TestClient

    from companion.clock import FixedClock
    clock = FixedClock(bench.START)
    results = {'computer': {'system': platform.platform(), 'python': platform.python_version(), 'speed': speed,
                            'cpu_score': bench.cpu_score(), 'heavy_world_companions': heavy}, 'rows': []}
    print(json.dumps(results['computer']), flush=True)
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        app = bench.make_app(root / 'companion.sqlite3', clock)
        with TestClient(app, headers=bench.HEADERS) as client:
            bench.ok(client.post('/api/companion', json={
                'name': 'Mira', 'timezone': 'America/New_York', 'schedule': bench.WORKDAY,
                'location': 'Fells Point, Baltimore', 'personality': 'Warm.'}))
            count = 1
            while count < heavy and bench.add_companion(client, clock):
                count += 1
            first = bench.ok(client.get('/api/worlds'))['active_world_id']
            worlds, began = [first], time.perf_counter()
            for checkpoint in [point for point in CHECKPOINTS if point <= limit]:
                while len(worlds) < checkpoint:
                    worlds.append(add_world(client, clock, len(worlds) + 1))
                    bench.ok(client.post(f'/api/worlds/{first}/switch'))
                row = {'worlds': len(worlds), 'first_world_companions': count,
                       'setup_s': round(time.perf_counter() - began, 1),
                       **measure(client, app, clock, root, first, worlds)}
                results['rows'].append(row)
                print(json.dumps(row), flush=True)
                if out:
                    out.write_text(json.dumps(results, indent=2), encoding='utf-8')
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--max', type=int, default=50, help='worlds to reach (default 50)')
    parser.add_argument('--heavy', type=int, default=25, help='companions in the first world (default 25)')
    parser.add_argument('--speed', type=float, default=1.0, help='share of one CPU core, e.g. 0.5 (default: no cap)')
    parser.add_argument('--out', type=Path, help='write results as JSON here as they come')
    args = parser.parse_args()
    bench.cap(args.speed)
    run(args.max, args.heavy, args.out, args.speed)


if __name__ == '__main__':
    main()
