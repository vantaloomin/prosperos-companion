"""Simulated end-to-end runs (scripts/sim/README.md).

    python scripts/sim/run.py --out <folder> [--worlds town ship ...] [--days 10] [--keep]

Starts the stand-ins and one app per world, builds each world through the API (drive.py), checks what the screens'
endpoints say (checks.py) and writes <out>/report.md and <out>/findings.json. With --keep the apps stay up so
`browse.mjs` can walk the screens; their addresses are in <out>/apps.json."""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import checks  # noqa: E402
import drive  # noqa: E402
import worlds  # noqa: E402
from stack import Stack  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--worlds', nargs='*', default=list(worlds.WORLDS))
    parser.add_argument('--days', type=int, default=10)
    parser.add_argument('--keep', action='store_true')
    parser.add_argument('--check-only', action='store_true', help='Check a run already saved in --out.')
    arguments = parser.parse_args()
    out = arguments.out.resolve()
    if arguments.check_only:
        print(checks.report(out, checks.run(out, arguments.worlds, out / 'apps')))
        return
    stack = Stack(out / 'apps')
    try:
        apps = {name: stack.app(name) for name in arguments.worlds}
        (out / 'apps.json').write_text(json.dumps(apps, indent=1))
        with ThreadPoolExecutor(len(apps)) as pool:
            list(pool.map(lambda name: drive.run(name, apps[name], stack.model_url(), out, arguments.days), apps))
        print(checks.report(out, checks.run(out, list(apps), stack.root)))
        if arguments.keep:
            print('apps up:', apps, flush=True)
            while True:
                time.sleep(3600)
    finally:
        stack.stop()


if __name__ == '__main__':
    main()
