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


def test_the_app_made_mom_makes_room_for_one_shared_in(client, companion):
    billy = companion_named(client, 'Billy Hart')
    theirs = billys_circle(client, billy)[0]
    own = ok(client.get('/api/life/circle'))
    made, kept = own[0], own[1]
    database = client.app.state.database
    with database.connect(write=True) as connection:  # One mom the app made, one the user wrote in by hand.
        connection.execute("UPDATE circle_people SET role='mom' WHERE id IN (?, ?)", (made['id'], kept['id']))
    ok(client.put(f"/api/life/circle/{kept['id']}/about", json={'note': 'My stepmom, really.'}))

    shared = ok(client.post('/api/life/circle/shared', json={'person_id': theirs['id'], 'role': 'Mom'}))
    assert [item['name'] for item in shared['made_room']] == [made['name']]
    listed = {person['id']: person for person in ok(client.get('/api/life/circle?include_removed=true'))}
    assert listed[made['id']]['status'] == 'removed' and listed[made['id']]['made_room_for']
    assert listed[kept['id']]['status'] == 'active'
    # Billy's person can share the app-made mom's seeded name; only the app-made mom's line must be gone.
    assert not [line for line in system(client).splitlines()
                if line.startswith(f"- {made['name']} (mom)") and 'Billy Hart' not in line]
    room = ok(client.get('/api/life/circle/room'))  # Stepping aside makes no room for a stranger.
    assert room['people'] == len(own)
    # A friend takes no one's place; back to mom, and out again, the app's mom comes back.
    assert ok(client.put(f"/api/life/circle/shared/{theirs['id']}", json={'role': 'friend'}))['made_room'] == []
    assert ok(client.get('/api/life/circle?include_removed=true'))[0]['status'] == 'active'
    ok(client.put(f"/api/life/circle/shared/{theirs['id']}", json={'role': 'mom'}))
    ok(client.post(f"/api/life/circle/shared/{theirs['id']}/remove", json={}))
    back = next(person for person in ok(client.get('/api/life/circle')) if person['id'] == made['id'])
    assert back['status'] == 'active' and not back.get('stepped_aside')


def test_a_mom_restored_by_hand_stays(client, companion):
    billy = companion_named(client, 'Billy Hart')
    theirs = billys_circle(client, billy)[0]
    made = ok(client.get('/api/life/circle'))[0]
    with client.app.state.database.connect(write=True) as connection:
        connection.execute("UPDATE circle_people SET role='mom' WHERE id=?", (made['id'],))
    ok(client.post('/api/life/circle/shared', json={'person_id': theirs['id'], 'role': 'mom'}))
    ok(client.post(f"/api/life/circle/{made['id']}/restore", json={}))
    assert ok(client.put(f"/api/life/circle/shared/{theirs['id']}", json={'role': 'mother'}))['made_room'] == []
    assert next(person for person in ok(client.get('/api/life/circle')) if person['id'] == made['id'])['status'] == 'active'
