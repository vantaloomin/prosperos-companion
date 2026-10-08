"""Closeness between people: two-way stages worked out from shared history (companion/memory/pairs.py)."""
import json
from datetime import timedelta

import pytest
from test_cast import met_someone
from test_groups import by_speaker, companion_named, ok, speaker, start

from companion import groups
from companion.characters import by_id, insert_version
from companion.clock import stamp
from companion.database import identifier
from companion.life import body, encounters
from companion.memory import closeness as own
from companion.memory import pairs
from companion.models import CharacterDefinition


@pytest.fixture(autouse=True)
def unmasked(monkeypatch):
    """Companion ids are random, so whether someone's mask keeps a person a step further is too; only the test
    about masks lets it happen."""
    monkeypatch.setattr(pairs, 'MASK_CHANCE', 0)


@pytest.fixture
def cast(client, companion, connected, provider):
    """Mira (the main character), Billy and Sally, with replies that name their speaker."""
    provider.respond = by_speaker
    return {'Mira': companion['id'], 'Billy': companion_named(client, 'Billy Hart'),
            'Sally': companion_named(client, 'Sally Moss')}


@pytest.fixture
def chatty(monkeypatch):
    """Meetings around town happen whenever they can (tests/test_cast.py)."""
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    monkeypatch.setattr(encounters, 'ACTIVE', True)
    monkeypatch.setattr(encounters, 'CHANCE', 1)
    monkeypatch.setattr(encounters, 'FAMILIAR_CHANCE', 1)


def key(companion_id: str) -> str:
    return pairs.companion_key(companion_id)


def spoke(client, group_id: str, author: str, day: int, text='Hi.'):
    """A finished group line by `author` (a member key, or 'user'), `day` days after the clock's start."""
    database = client.app.state.database
    with database.connect(write=True) as connection:
        at = stamp(database.clock.now() + timedelta(days=day))
        groups.add_line(connection, group_id, at, author, 'Name', text)


def stage(client, a: str, b: str) -> int | None:
    database = client.app.state.database
    with database.connect() as connection:
        return pairs.closeness(connection, a, b, database.clock.now())


def edit(client, companion_id: str, **changes):
    """A new version of a companion's sheet with these fields changed."""
    database = client.app.state.database
    with database.connect(write=True) as connection:
        found = by_id(connection, companion_id)
        definition = CharacterDefinition.model_validate({**found['version']['definition'], **changes})
        version_id = insert_version(connection, companion_id, found['version']['number'] + 1, definition, '',
                                    database.now())
        connection.execute('UPDATE companions SET active_version_id=? WHERE id=?', (version_id, companion_id))


def test_circle_roles_start_where_people_already_are_with_a_stable_nudge():
    family = [pairs.role_default('sister', f'circle:t:{n}')['level'] for n in range(200)]
    assert min(family) == 2 and max(family) == 4 and family.count(3) > 60
    close = [pairs.role_default('close friend', f'circle:t:{n}')['level'] for n in range(200)]
    assert set(close) == {3, 4} and close.count(4) > close.count(3)
    assert {pairs.role_default('coworker', f'circle:t:{n}')['level'] for n in range(200)} == {2, 3}
    assert pairs.role_default('mom', 'circle:t:7') == pairs.role_default('mom', 'circle:t:7')
    assert pairs.role_default('someone odd', 'circle:t:1')['level'] == 1


def test_two_companions_start_as_strangers_unless_their_backstory_is_told_once(client, cast):
    billy, sally, mira = key(cast['Billy']), key(cast['Sally']), key(cast['Mira'])
    assert stage(client, billy, sally) == 1
    untold = ok(client.post('/api/groups/untold', json={'companion_ids': [cast['Billy'], cast['Sally']]}))['pairs']
    assert [(item['a_name'], item['b_name'], item['level']) for item in untold] == [('Billy Hart', 'Sally Moss', 1)]

    group = ok(client.post('/api/groups', json={'companion_ids': [cast['Billy'], cast['Sally']], 'ties': [
        {'a': cast['Billy'], 'b': cast['Sally'], 'level': 3, 'how': 'They shared a flat in college.'}]}))
    assert stage(client, billy, sally) == stage(client, sally, billy) == 3
    # Told once: after they first share a group, nobody can set it again, through any door.
    assert ok(client.post('/api/groups/untold', json={'companion_ids': [cast['Billy'], cast['Sally']]}))['pairs'] == []
    ok(client.post('/api/groups', json={'companion_ids': [cast['Billy'], cast['Sally']], 'ties': [
        {'a': cast['Billy'], 'b': cast['Sally'], 'level': 5, 'how': 'Twins.'}]}))
    assert stage(client, billy, sally) == 3
    # Adding Mira tells her backstory with Billy only.
    ok(client.post(f"/api/groups/{group['id']}/members", json={'companion_id': cast['Mira'], 'ties': [
        {'a': cast['Mira'], 'b': cast['Billy'], 'level': 2}, {'a': cast['Billy'], 'b': cast['Sally'], 'level': 1}]}))
    assert stage(client, mira, billy) == 2 and stage(client, mira, sally) == 1 and stage(client, billy, sally) == 3
    with client.app.state.database.connect() as connection:
        rows = connection.execute('SELECT first, second, start_level, how FROM pair_backstories').fetchall()
    assert sorted((row['start_level'], row['how']) for row in rows) == [(2, ''), (3, 'They shared a flat in college.')]
    # Anyone outside a companion is never worked out.
    assert stage(client, 'town:baltimore:somewhere:0', 'town:baltimore:somewhere:1') is None


def test_days_spoken_together_and_kept_moments_bring_them_closer(client, cast):
    billy, sally = key(cast['Billy']), key(cast['Sally'])
    group = start(client, [cast['Billy'], cast['Sally']])
    for day in range(3):
        spoke(client, group['id'], billy, day, 'Morning!')
        spoke(client, group['id'], billy, day, 'Again!')  # Many lines on one day count once.
    assert stage(client, billy, sally) == 1  # Only Billy talked.
    for day in range(3):
        spoke(client, group['id'], sally, day)
    assert stage(client, billy, sally) == stage(client, sally, billy) == 2  # 3 days together.

    line = next(item for item in ok(client.get(f"/api/groups/{group['id']}"))['messages'] if item['text'] == 'Morning!')
    kept = ok(client.post(f"/api/groups/{group['id']}/messages/{line['id']}/moment", json={'kept': True}))
    assert next(item for item in kept['messages'] if item['id'] == line['id'])['kept']
    other = [item for item in kept['messages'] if item['text'] == 'Again!']
    for item in other:
        ok(client.post(f"/api/groups/{group['id']}/messages/{item['id']}/moment", json={}))
    # 3 days + 3 moments (4 kept, capped at the days) reaches stage 2 still; one more day of talk reaches 3.
    assert stage(client, billy, sally) == 2
    spoke(client, group['id'], billy, 3)
    spoke(client, group['id'], sally, 3)
    spoke(client, group['id'], billy, 4)
    spoke(client, group['id'], sally, 4)
    assert stage(client, billy, sally) == 3
    # The app's own lines and the user's can't be kept.
    note = next(item for item in kept['messages'] if item['kind'] == 'app')
    assert client.post(f"/api/groups/{group['id']}/messages/{note['id']}/moment", json={}).status_code == 422
    ok(client.post(f"/api/groups/{group['id']}/messages/{line['id']}/moment", json={'kept': False}))
    assert stage(client, billy, sally) == 3


def test_the_group_section_names_each_stage_and_close_people_share_how_they_see_themselves(client, cast, provider):
    group = ok(client.post('/api/groups', json={'companion_ids': [cast['Billy'], cast['Sally']], 'ties': [
        {'a': cast['Billy'], 'b': cast['Sally'], 'level': 4, 'how': 'Neighbours for ten years.'}]}))
    ok(client.patch(f"/api/groups/{group['id']}", json={'reply_cap': 2}))
    provider.requests.clear()
    ok(client.post(f"/api/groups/{group['id']}/messages", json={'text': 'Hi you two', 'client_id': 'group-pairs-1'}))
    billy = next(request['prompt'] for request in provider.requests if speaker(request['messages']) == 'Billy')
    private = billy[billy.index('## This group chat (only you know this part)'):]
    assert groups.FEELS[3].format(name='Sally') in private
    assert 'How you know Sally: Neighbours for ten years.' in private
    with client.app.state.database.connect() as connection:
        view = pairs.self_view(connection, key(cast['Sally']))
    assert view and f'Sally has let you see how they see themselves: {view}' in private
    # Nothing about closeness reaches the part every speaker shares.
    shared = billy[:billy.index('## The group chat so far')]
    assert 'Neighbours' not in shared and groups.FEELS[3].format(name='Sally') not in shared


def test_strangers_dont_see_how_someone_sees_themselves(client, cast, provider):
    group = start(client, [cast['Billy'], cast['Sally']])
    provider.requests.clear()
    ok(client.post(f"/api/groups/{group['id']}/messages", json={'text': 'Billy?', 'client_id': 'group-pairs-2'}))
    billy = next(request['prompt'] for request in provider.requests if speaker(request['messages']) == 'Billy')
    assert groups.FEELS[0].format(name='Sally') in billy and 'how they see themselves' not in billy


def test_a_found_out_secret_lowers_it_only_when_their_sheet_says_so(client, cast):
    billy, sally = key(cast['Billy']), key(cast['Sally'])
    ok(client.post('/api/groups', json={'companion_ids': [cast['Billy'], cast['Sally']], 'ties': [
        {'a': cast['Billy'], 'b': cast['Sally'], 'level': 4}]}))
    # Sally finds out a secret about Billy that was kept from her (companion/secrets.py).
    secret = ok(client.post('/api/secrets', json={'statement': 'Billy is moving to Denver in May', 'about': ['Billy'],
                                                  'knows': [cast['Billy']], 'kept_from': [cast['Sally']]}))['secrets'][0]
    ok(client.post(f"/api/secrets/{secret['id']}/reveal", json={'companion_id': cast['Sally']}))
    before = stage(client, sally, billy)
    assert before == stage(client, billy, sally)  # Sally takes it in her stride: nothing built in.
    edit(client, cast['Sally'], personality='Warm, but she holds grudges and hates being lied to.')
    assert stage(client, sally, billy) == before - 1 and stage(client, billy, sally) == before
    edit(client, cast['Sally'], personality='Warm and not jealous at all.')
    assert stage(client, sally, billy) == before


def test_gentle_cooling_follows_the_companions_own_switch(client, cast, clock):
    billy, sally = key(cast['Billy']), key(cast['Sally'])
    ok(client.post('/api/groups', json={'companion_ids': [cast['Billy'], cast['Sally']], 'ties': [
        {'a': cast['Billy'], 'b': cast['Sally'], 'level': 4}]}))
    database = client.app.state.database
    with database.connect(write=True) as connection:
        own.save(connection, by_id(connection, cast['Sally'])['active_timeline_id'], database.now(),
                 cooling_since=database.now())
    clock.instant = clock.now() + timedelta(days=30)
    assert stage(client, sally, billy) == 3 and stage(client, billy, sally) == 4
    clock.instant = clock.now() + timedelta(days=60)
    assert stage(client, sally, billy) == 2  # Two steps at most, and never below the second stage.


def test_a_mask_makes_at_most_one_step_of_difference(client, companion, monkeypatch):
    monkeypatch.setattr(pairs, 'MASK_CHANCE', 1)
    ids = [companion_named(client, f'Person {n}') for n in range(12)]
    database = client.app.state.database
    with database.connect(write=True) as connection:
        for index, a in enumerate(ids):
            for b in ids[index + 1:]:
                assert pairs.tell(connection, key(a), key(b), 3, '', database.now())
        found = [(pairs.closeness(connection, key(a), key(b), database.clock.now()),
                  pairs.closeness(connection, key(b), key(a), database.clock.now()))
                 for index, a in enumerate(ids) for b in ids[index + 1:]]
    assert all(abs(mine - theirs) <= 1 and {mine, theirs} <= {2, 3} for mine, theirs in found)
    assert any(mine != theirs for mine, theirs in found)


def test_circle_people_show_their_stage_and_storylines_move_it(client):
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'America/New_York',
                                                     'location': 'Fells Point, Baltimore'})
    mira = ok(response)
    people = ok(client.get('/api/life/circle'))
    assert people and all(person['stage'] and person['stage']['level'] >= 2 for person in people
                          if person['role'] in ('mom', 'dad', 'sister', 'brother', 'close friend'))
    friend = next(person for person in people if person['role'] == 'close friend')
    start_level = friend['stage']['level']
    database = client.app.state.database
    today = database.clock.now().date()
    stages = [{'on': (today - timedelta(days=2)).isoformat(), 'text': 'fight', 'share': '', 'tone': 'bad'},
              {'on': (today + timedelta(days=3)).isoformat(), 'text': 'made up', 'share': '', 'tone': 'good'}]
    with database.connect(write=True) as connection:
        connection.execute("INSERT INTO storylines (id, timeline_id, story, level, cast_ids, stages, started_on, "
                           "status, created_at) VALUES (?, ?, 'friend_fight', 2, ?, ?, ?, 'running', ?)",
                           (identifier(), mira['active_timeline_id'], json.dumps([friend['id']]), json.dumps(stages),
                            stages[0]['on'], database.now()))
    fallen = next(person for person in ok(client.get('/api/life/circle')) if person['id'] == friend['id'])
    assert fallen['stage']['level'] == max(start_level - 1, 1)
    with database.connect(write=True) as connection:
        stages[1]['on'] = (today - timedelta(days=1)).isoformat()
        connection.execute('UPDATE storylines SET stages=?', (json.dumps(stages),))
    made_up = next(person for person in ok(client.get('/api/life/circle')) if person['id'] == friend['id'])
    assert made_up['stage']['level'] == start_level
    with database.connect() as connection:
        assert pairs.closeness(connection, friend['key'], key(mira['id']), database.clock.now()) == start_level


def test_a_new_companion_starts_at_their_meetings_and_the_form_can_tell_it_once(client, clock, chatty):
    mira, person = met_someone(client, clock)
    drafted = ok(client.get('/api/companion/cast/draft', params={'key': person['key']}))
    tie = drafted['ties'][0]
    assert tie['companion_id'] == mira['id'] and tie['meetings'] == person['times']
    assert tie['level'] == pairs.meeting_stage(person['times'])
    new = ok(client.post('/api/companion/cast/switch', json={
        'key': person['key'], 'definition': drafted['definition'],
        'ties': [{'companion_id': mira['id'], 'level': 4, 'how': 'Regulars at the same bar.'}]}))
    ties = ok(client.get('/api/companion/ties'))['ties']
    assert [(item['name'], item['feels']['level'], item['how']) for item in ties] == \
        [('Mira', 4, 'Regulars at the same bar.')]
    assert stage(client, key(new['id']), key(mira['id'])) == 4
