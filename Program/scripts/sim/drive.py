"""Build one world through the app's own API the way a user would, let time pass with debug time, and save what
every screen's endpoints say (scripts/sim/README.md). `checks.py` reads what this saves."""
import json
import time
from pathlib import Path

import httpx
import worlds as plan
from stack import HEADERS

# Endpoints read for each companion after time has passed: what the screens show.
PER_COMPANION = ['/api/companion', '/api/life/circle', '/api/life/pets', '/api/life/hobbies', '/api/life/work',
                 '/api/today', '/api/life/media', '/api/life/townsfolk', '/api/companion/ties', '/api/companion/town',
                 '/api/life/circle/shareable', '/api/life/where', '/api/life/outings', '/api/life/chapters',
                 '/api/life/web', '/api/life/home', '/api/life/kitchen', '/api/life/wardrobe', '/api/life/traditions',
                 '/api/life/upkeep', '/api/life/steps', '/api/life/admin', '/api/life/grooming', '/api/life/year',
                 '/api/life/history', '/api/today/money', '/api/life/acquaintances', '/api/life/paper',
                 '/api/life/recommendations', '/api/life/storylines', '/api/conversation', '/api/their-look',
                 '/api/closeness', '/api/people']
SHARED = ['/api/feed', '/api/chats', '/api/groups', '/api/worlds', '/api/companion/cast', '/api/settings',
          '/api/life/settings', '/api/notifications/settings', '/api/dating', '/api/observer/feed']
# The feed comes a page at a time: read as much as one page holds, so the user's own post from days ago is in it.
PARAMS = {'/api/feed': {'limit': 100}}


class Driver:
    def __init__(self, name: str, url: str, model_url: str, out: Path):
        self.name, self.url, self.model_url = name, url, model_url
        self.out = out / name
        self.out.mkdir(parents=True, exist_ok=True)
        self.http = httpx.Client(base_url=url, headers=HEADERS, timeout=600)
        self.errors = []
        self.sent = 0

    def call(self, method, path, quiet=False, **kwargs):
        response = self.http.request(method, path, **kwargs)
        if response.status_code >= 400:
            if not quiet:
                self.errors.append({'call': f'{method} {path}', 'status': response.status_code,
                                    'body': response.text[:500], 'sent': kwargs.get('json')})
            return None
        return response.json() if response.content else {}

    def save(self, label: str, value):
        (self.out / f'{label}.json').write_text(json.dumps(value, indent=1, default=str), encoding='utf-8')

    # Setting up ---------------------------------------------------------------------------------------------------

    def setup(self, world: dict):
        self.call('PUT', '/api/settings', json={'ai_notice_confirmed': True})
        # An empty key keeps the OS credential vault out of it (the stand-in model takes no key).
        self.call('PUT', '/api/connection', json={'base_url': self.model_url, 'model': 'stand-in', 'api_key': ''})
        if world.get('own_city'):
            self.call('POST', '/api/world/cities', json=world['own_city'])
        made = []
        for index, definition in enumerate(world['companions']):
            body = definition | {'home_city': world['city']}
            made.append(self.call('POST', '/api/companion' if index == 0 else '/api/companion/another', json=body))
        self.companions = [m for m in made if m]
        self.ids = [m['id'] for m in self.companions]
        self.save('created', self.companions)
        self.focus(0)

    def focus(self, index: int):
        if index < len(self.ids):
            self.call('POST', '/api/companion/cast/focus', json={'companion_id': self.ids[index]})

    def snapshot(self, label: str):
        """What each companion's screens say now, and the shared ones."""
        seen = {'shared': {path: self.call('GET', path, quiet=True, params=PARAMS.get(path)) for path in SHARED}, 'companions': {}}
        for index, companion_id in enumerate(self.ids):
            self.focus(index)
            seen['companions'][companion_id] = {path: self.call('GET', path, quiet=True) for path in PER_COMPANION}
        self.focus(0)
        self.save(label, seen)
        return seen

    # What the user does by hand -----------------------------------------------------------------------------------

    def edits(self):
        done = {}
        self.focus(0)
        done['hobby'] = self.call('POST', '/api/life/hobbies', json={'name': plan.HOBBY_BY_HAND})
        circle = self.call('GET', '/api/life/circle') or []
        done['circle_before'] = circle
        friend = next((p for p in circle if 'friend' in p['role']), None)
        if friend:
            done['friend_age'] = self.call('PUT', f"/api/life/circle/{friend['id']}/about",
                                           json={'age': plan.FRIEND_AGE_BY_HAND} | plan.JOB_BY_HAND)
            done['friend_id'] = friend['id']
            done['friend_pet'] = self.call('POST', f"/api/life/circle/{friend['id']}/pets", json=plan.PET_BY_HAND)
        done['mom'] = self.call('POST', '/api/life/circle/people', json=plan.MOM_BY_HAND)
        done['own_pet'] = self.call('POST', '/api/life/pets', json=plan.PET_BY_HAND | {'name': 'Pickle'})
        # The second companion knows the first one's friend too.
        if friend and len(self.ids) > 1:
            self.focus(1)
            done['shareable'] = self.call('GET', '/api/life/circle/shareable')
            done['shared'] = self.call('POST', '/api/life/circle/shared',
                                       json={'person_id': friend['id'], 'role': 'friend'})
            done['tie'] = self.call('POST', '/api/companion/ties', quiet=True,
                                    json={'companion_id': self.ids[0], 'level': 3, 'how': 'old friends'})
            self.focus(0)
        done['own_post'] = self.call('POST', '/api/feed/mine', json={'text': plan.OWN_POST})
        self.save('edits', done)
        return done

    def chat(self, turns: int = 4):
        for index in range(len(self.ids)):
            self.focus(index)
            for turn in range(turns):
                self.sent += 1
                self.call('POST', '/api/conversation/messages?wait=false',
                          json={'text': ['hey, how was your day?', 'what are you up to tonight?',
                                         'tell me about your friends', 'what are you reading lately?'][turn % 4],
                                'client_id': f'sim-{self.name}-{self.sent:05d}'})
        self.focus(0)

    def revise(self):
        """The user edits the main companion's sheet (a new version): what they set by hand elsewhere must stay."""
        self.focus(0)
        companion = (self.call('GET', '/api/companion') or {}).get('companion') or {}
        version = companion.get('version') or {}
        if version:
            definition = version['definition'] | {'personality': version['definition'].get('personality', '') +
                                                  ' Hums when they cook.'}
            self.save('revised', self.call('POST', '/api/companion/versions', json={
                'definition': definition, 'note': 'sim', 'expected_version_id': version['id']}))

    def group(self):
        if len(self.ids) > 1:
            made = self.call('POST', '/api/groups', json={'name': 'Night out at the usual place',
                                                         'companion_ids': self.ids})
            self.save('group', made)
            if made and made.get('id'):
                self.call('POST', f"/api/groups/{made['id']}/messages?wait=false",
                          json={'text': 'Who is free on Saturday?', 'client_id': f'sim-{self.name}-group-1'})
            return made

    # Time ---------------------------------------------------------------------------------------------------------

    def pass_time(self, hours: float):
        if not (self.call('GET', '/api/debug-time') or {}).get('active'):
            self.call('POST', '/api/debug-time/start')
        if self.call('POST', '/api/debug-time/jump', json={'hours': hours}) is None:
            return
        end = time.time() + 900
        while time.time() < end:
            status = self.call('GET', '/api/debug-time') or {}
            if not status.get('jumping'):
                return status
            time.sleep(1)
        self.errors.append({'call': 'debug-time jump', 'status': 'timeout', 'body': f'{hours}h did not finish'})

    def finish(self):
        self.save('errors', self.errors)


def run(name: str, url: str, model_url: str, out: Path, days: int = 10):
    world = plan.WORLDS[name]
    driver = Driver(name, url, model_url, out)
    driver.setup(world)
    driver.snapshot('fresh')
    driver.edits()
    driver.group()
    driver.chat()
    driver.revise()
    driver.snapshot('after-edits')
    driver.pass_time(24 * 2)
    driver.chat(2)
    driver.pass_time(24 * (days - 2))
    driver.snapshot('later')
    driver.finish()
    return driver
