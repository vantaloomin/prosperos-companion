"""Build a place from one line: `python -m companion.world.draft "a cold fishing town, 1920s" [--seed 3] [-o FILE]`.

Prints the city file (or writes it to FILE), ready for Settings > Cities > Open a city file. The same line and seed
always give the same place; another seed gives another.
"""
import argparse
import json
import sys
from pathlib import Path

from companion.world import catalog, check
from companion.world.draft import build


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('line', nargs='?', default='', help='What the place is, in a few words (empty: surprise me)')
    parser.add_argument('--seed', default='', help='Another seed gives another place from the same line')
    parser.add_argument('-o', '--out', help='Write the city file here instead of printing it')
    args = parser.parse_args(argv)
    city = build(args.line, args.seed)['city']
    loaded = catalog.prepare(json.loads(json.dumps(city)), mend=True)
    text = json.dumps(city, indent=1, ensure_ascii=False) + '\n'
    if args.out:
        Path(args.out).write_text(text, encoding='utf-8')
        print(f'{loaded["name"]}: {len(loaded["neighborhoods"])} neighbourhoods, {len(loaded["places"])} places, '
              f'{len(loaded["employers"])} employers -> {args.out}', file=sys.stderr)
    else:
        sys.stdout.write(text)
    for line in [*loaded.get('import_notes', []), *check.warnings(loaded)]:
        print(f'note: {line}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
