"""Someone in one companion's circle whom another companion knows too (companion/life/shared_people.py)."""
from test_groups import companion_named, ok

from companion.characters import by_id, require_current
from companion.life import circle
from companion.memory import context


def system(client, companion_id: str | None = None) -> str:
    database = client.app.state.database
    with database.connect() as connection:
        companion = by_id(connection, companion_id) if companion_id else require_current(connection)
        return context.build(connection, companion, database.clock.now(), 20_000)['system']


def billys_circle(client, billy_id: str) -> list[dict]:
    database = client.app.state.database
    with database.connect(write=True) as connection:
        return circle.ensure(connection, by_id(connection, billy_id), client.app.state.life.world, database.clock.now())


def test_someone_from_another_circle_is_known_on_both_sides(client, companion):
    billy = companion_named(client, 'Billy Hart')
    rows = billys_circle(client, billy)
    theirs = rows[0]
    offered = ok(client.get('/api/life/circle/shareable'))
    assert {person['id'] for person in offered} == {row['id'] for row in rows}
    assert {person['owner'] for person in offered} == {'Billy Hart'}

    shared = ok(client.post('/api/life/circle/shared', json={'person_id': theirs['id'], 'role': 'Aunt'}))
    assert (shared['name'], shared['role'], shared['shared']['owner'], shared['shared']['role']) == \
        (theirs['name'], 'aunt', 'Billy Hart', theirs['role'])
    listed = ok(client.get('/api/life/circle'))
    assert [person['id'] for person in listed if person.get('shared')] == [theirs['id']]
    assert theirs['id'] not in {person['id'] for person in ok(client.get('/api/life/circle/shareable'))}
    # Both chats know them as the same person.
    assert f"- {theirs['name']} (aunt)" in system(client) and f"Billy Hart's {theirs['role']}." in system(client)
    assert 'Also Mira' in system(client, billy) and "'s aunt." in system(client, billy)
    # The web links the companion to them.
    web = ok(client.get('/api/life/web'))
    links = {(link['source'], link['target'], link['label']) for link in web['links']}
    assert any(theirs['seed'] in (source, target) and label == 'aunt' for source, target, label in links)
    assert client.get(f"/api/life/circle/{theirs['id']}/diary").status_code == 200

    changed = ok(client.put(f"/api/life/circle/shared/{theirs['id']}", json={'role': 'godmother'}))
    assert changed['role'] == 'godmother'
    # Their own companion's page is where they are edited.
    assert client.put(f"/api/life/circle/{theirs['id']}/about", json={'name': 'Zed'}).status_code == 404

    ok(client.post(f"/api/life/circle/shared/{theirs['id']}/remove", json={}))
    assert not [person for person in ok(client.get('/api/life/circle')) if person.get('shared')]
    assert 'Also Mira' not in system(client, billy)
    assert client.post(f"/api/life/circle/shared/{theirs['id']}/remove", json={}).status_code == 404


def test_their_own_circle_cannot_be_shared_with_them(client, companion):
    own = ok(client.get('/api/life/circle'))[0]
    assert client.post('/api/life/circle/shared', json={'person_id': own['id'], 'role': 'mom'}).status_code == 409
