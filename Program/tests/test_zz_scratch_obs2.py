from datetime import timedelta

from conftest import reconcile, send
from test_observer import feed, lines, watching  # noqa: F401


def test_become_while_watching(client, watching):
    town = next(c for c in watching['choices'] if c['kind'] == 'townsperson')
    client.put('/api/observer', json={'focus': town['key']})
    r = client.post('/api/worlds/become', json={'key': town['key']})
    print('BECOME', r.status_code)
    print('OBS', {k: v for k, v in client.get('/api/observer').json().items() if k != 'choices'})
    print('WORLDS', client.get('/api/worlds').json()['world'].get('watching'))


def test_fork_while_watching(client, connected, watching, provider, clock):
    from companion.providers.chat import Chunk
    provider.replies = [[Chunk('hi'), Chunk('', 'stop')]] * 3
    tl = client.get('/api/timelines').json()
    print('TL', str(tl)[:300])


def test_start_over_while_watching(client, watching):
    r = client.post('/api/companion/start-over', json={'keep': []})
    print('SO', r.status_code, r.text[:200])
    print('OBS', {k: v for k, v in client.get('/api/observer').json().items() if k != 'choices'})
    r = client.get('/api/observer/feed')
    print('FEED', r.status_code, r.text[:200])


def test_delete_followed_companion(client, watching):
    r = client.get('/api/companion/delete')
    print('DEL-GET', r.status_code, r.text[:200])
