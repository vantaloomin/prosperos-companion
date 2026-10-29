"""Simulated end-to-end run of 1.2 "The Dark Backward": Back when and worlds in a past year (scripts/sim/README.md).

    python scripts/sim/past_years.py --out <folder> [--scenes back-when 1995 2005 2015 watch] [--days 2] [--keep]

`back-when` builds a Chicago world in the present, lets two days pass, then goes Back when from the companion's
Character page sheet twice: as strangers (the default) and with "Work it out from our history". Each year scene makes
a new world started in that year (the world creator's "Start in a past year"), builds companions there and does what
1.1.10 added (a comment on a feed post, a one-sided person). `watch` starts a past-year world just watching. Then
past_checks.py checks what the screens' endpoints say, and with --keep the apps stay up for browse.mjs."""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import drive  # noqa: E402
import past_checks  # noqa: E402
import worlds as plan  # noqa: E402
from stack import Stack  # noqa: E402

CITY = 'chicago'
FAN = {'name': 'Dana Fields', 'role': 'fan', 'pronouns': 'she/her', 'note': 'Has never met them, a big fan of their work.'}


class PastDriver(drive.Driver):
    def pass_time(self, hours: float):
        """No time at all with --days 0, for a quick look at the screens."""
        return super().pass_time(hours) if hours > 0 else None

    def finish_time(self):
        """Debug time ends before a switch (a world can't be left while it runs)."""
        if (self.call('GET', '/api/debug-time') or {}).get('active'):
            self.call('POST', '/api/debug-time/finish', json={'keep': True})

    def switch(self, world_id: str):
        self.finish_time()
        return self.call('POST', f'/api/worlds/{world_id}/switch')

    def adopt(self):
        """The companions of the world the user is in now, as setup() would have made them."""
        cast = self.call('GET', '/api/companion/cast') or {}
        people = cast.get('members') or []
        self.ids = [person['id'] for person in people if person.get('id')] or self.ids[:1]

    def year_world(self, year: int, watch: bool = False):
        made = self.call('POST', '/api/worlds', json={'year': year, 'city_id': CITY, 'watch': watch,
                                                      'name': f'Started in {year}'})
        self.save('world', made)
        if made:
            self.switch(made['id'])
        return made

    def newer_things(self):
        """What 1.1.10 added, done inside the world the user is in."""
        done = {}
        feed = self.call('GET', '/api/feed', params={'limit': 100}) or {}
        posts = feed.get('posts') if isinstance(feed, dict) else feed
        theirs = next((post for post in posts or [] if post.get('source') != 'user'), None)
        if theirs:
            done['comment'] = self.call('POST', f"/api/feed/{theirs['id']}/comments", params={'wait': 'true'},
                                        json={'text': 'Ha, that looks like a great night. Who else was there?'})
        done['fan'] = self.call('POST', '/api/life/circle/people', json=FAN)
        self.save('newer', done)
        return done


def back_when(driver: PastDriver, days: int):
    driver.setup(plan.WORLDS['town'])
    driver.edits()
    driver.chat(2)
    driver.pass_time(24 * days)
    driver.snapshot('present')
    present = (driver.call('GET', '/api/worlds') or {}).get('active_world_id')
    sheet = driver.call('GET', '/api/worlds/back-when') or {}
    driver.save('sheet', sheet)
    moments = sheet.get('moments') or []
    if not moments:
        driver.errors.append({'call': 'GET /api/worlds/back-when', 'status': 'no moments', 'body': json.dumps(sheet)})
        return
    driver.finish_time()
    strangers = driver.call('POST', '/api/worlds/back-when', json={'year': moments[0]['year']})
    driver.save('strangers-world', strangers)
    driver.adopt()
    driver.save('sheet-inside', {'status': driver.http.get('/api/worlds/back-when').status_code})
    driver.snapshot('strangers')
    driver.newer_things()
    driver.chat(2)
    driver.pass_time(24 * days)
    driver.snapshot('strangers-later')
    driver.switch(present)
    driver.adopt()
    year = (moments[1] if len(moments) > 1 else moments[0])['year']
    history = driver.call('POST', '/api/worlds/back-when', json={'year': year, 'from_history': True})
    driver.save('history-world', history)
    driver.adopt()
    driver.snapshot('history')


def year_scene(driver: PastDriver, year: int, days: int):
    # A first companion in the first world, so there is a world to make another from.
    driver.setup({'city': CITY, 'companions': plan.TOWN[:1]})
    driver.finish_time()
    driver.year_world(year)
    driver.setup(plan.WORLDS['town'])
    driver.snapshot('fresh')
    driver.edits()
    driver.newer_things()
    driver.chat(2)
    driver.pass_time(24 * days)
    driver.snapshot('later')


def watch_scene(driver: PastDriver, days: int):
    driver.setup({'city': CITY, 'companions': plan.TOWN[:1]})
    driver.finish_time()
    driver.year_world(2004, watch=True)
    driver.ids = []
    driver.pass_time(24 * days)
    driver.snapshot('later')


def scene(name: str, url: str, model_url: str, out: Path, days: int):
    driver = PastDriver(name, url, model_url, out)
    try:
        if name == 'back-when':
            back_when(driver, days)
        elif name == 'watch':
            watch_scene(driver, days)
        else:
            year_scene(driver, int(name), days)
    finally:
        driver.finish()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--scenes', nargs='*', default=['back-when', '1995', '2005', '2015', 'watch'])
    parser.add_argument('--days', type=int, default=2)
    parser.add_argument('--keep', action='store_true')
    parser.add_argument('--check-only', action='store_true')
    arguments = parser.parse_args()
    out = arguments.out.resolve()
    if arguments.check_only:
        print(past_checks.report(out, past_checks.run(out, arguments.scenes, out / 'apps')))
        return
    stack = Stack(out / 'apps')
    try:
        apps = {name: stack.app(name) for name in arguments.scenes}
        (out / 'apps.json').write_text(json.dumps(apps, indent=1))
        with ThreadPoolExecutor(len(apps)) as pool:
            list(pool.map(lambda name: scene(name, apps[name], stack.model_url(), out, arguments.days), apps))
        print(past_checks.report(out, past_checks.run(out, list(apps), stack.root)))
        if arguments.keep:
            print('apps up:', apps, flush=True)
            while True:
                time.sleep(3600)
    finally:
        stack.stop()


if __name__ == '__main__':
    main()
