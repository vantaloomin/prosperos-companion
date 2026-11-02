"""Each world can have a drama level of its own (companion/life/world_drama.py); with none it follows Realism."""
from datetime import date, timedelta

from conftest import set_life

from companion.characters import require_current
from companion.life import circle, steps, storylines, world_drama


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def level(client) -> int:
    with client.app.state.database.connect() as connection:
        assert storylines.drama(connection) == steps.drama(connection)
        return storylines.drama(connection)


def test_a_world_follows_realism_until_it_has_its_own(client, companion):
    settings = ok(client.get('/api/life/settings'))
    assert settings['world_drama'] is None and settings['alone']
    with client.app.state.database.connect(write=True) as connection:
        connection.execute('UPDATE life_settings SET drama=3 WHERE id=1')  # The level carried from world to world.
    assert level(client) == 3
    changed = ok(client.put('/api/life/world', json={'drama': 0}))
    assert changed['world_drama'] == 0 and changed['drama'] == 0
    assert level(client) == 0
    assert ok(client.put('/api/life/world', json={'drama': None}))['world_drama'] is None
    assert level(client) == 3


def test_the_realism_slider_sets_this_world_only(client, companion):
    """Tester, 2026-10-31: "dramatic" for Sett's world changed Givardon too. The slider now sets this world's own."""
    changed = set_life(client, drama=3)
    assert changed['drama'] == 3 and changed['world_drama'] == 3 and level(client) == 3
    with client.app.state.database.connect() as connection:
        assert connection.execute('SELECT drama FROM life_settings WHERE id=1').fetchone()[0] == 1
    made = ok(client.post('/api/worlds', json={'name': 'Somewhere else'}))
    ok(client.post(f"/api/worlds/{made['id']}/switch"))
    assert ok(client.get('/api/life/settings'))['drama'] == 1
    set_life(client, drama=0)
    first = next(world for world in ok(client.get('/api/worlds'))['personas'][0]['worlds'] if world['first'])
    ok(client.post(f"/api/worlds/{first['id']}/switch"))
    assert ok(client.get('/api/life/settings'))['drama'] == 3
    ok(client.post(f"/api/worlds/{made['id']}/switch"))
    assert ok(client.get('/api/life/settings'))['drama'] == 0


def test_only_a_real_level_or_none(client, companion):
    assert client.put('/api/life/world', json={'drama': 4}).status_code == 422
    assert client.put('/api/life/world', json={'drama': -1}).status_code == 422
    assert client.put('/api/life/world', json={}).status_code == 422


def test_the_level_stays_in_its_world(client, companion):
    set_life(client, drama=1)
    ok(client.put('/api/life/world', json={'drama': 3}))
    made = ok(client.post('/api/worlds', json={'name': 'Somewhere else'}))
    ok(client.post(f"/api/worlds/{made['id']}/switch"))
    # Realism follows the user; the first world's own level does not.
    settings = ok(client.get('/api/life/settings'))
    assert settings['drama'] == 1 and settings['world_drama'] is None
    first = next(world for world in ok(client.get('/api/worlds'))['personas'][0]['worlds'] if world['first'])
    ok(client.post(f"/api/worlds/{first['id']}/switch"))
    assert ok(client.get('/api/life/settings'))['world_drama'] == 3


def test_a_companion_alone_in_their_world_gets_a_few_more_storylines(client, companion, monkeypatch):
    monkeypatch.setattr(storylines, 'START', (0.3, 0.3, 0.3, 0.3))
    with client.app.state.database.connect() as connection:
        assert world_drama.alone(connection)
        found = require_current(connection)
        people = circle.ensure(connection, found, client.app.state.life.world, client.app.state.database.clock.now())
        days = [date(2026, 1, 1) + timedelta(days=offset) for offset in range(300)]
        shared = sum(bool(storylines.start(connection, found, people, day, 1)) for day in days)
        alone = sum(bool(storylines.start(connection, found, people, day, 1, lone=True)) for day in days)
    assert alone > shared * 1.2
