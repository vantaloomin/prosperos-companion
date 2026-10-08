"""Group chats: several companions in one chat, each answering from what they know (companion/groups.py)."""
import json
import re

import pytest
from conftest import send, set_life

from companion import groups
from companion.characters import by_id, insert_version
from companion.database import identifier
from companion.models import CharacterDefinition
from companion.providers.chat import Chunk
from companion.world import perception


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def companion_named(client, name: str, personality='Easygoing.') -> str:
    """Another companion in the workspace, stepped back, as a dating match or a switch leaves them."""
    database = client.app.state.database
    with database.connect(write=True) as connection:
        companion_id, timeline_id, now = identifier(), identifier(), database.now()
        connection.execute('INSERT INTO companions (id, slot, stepped_back_at, created_at) VALUES (?, NULL, ?, ?)',
                           (companion_id, now, now))
        version_id = insert_version(connection, companion_id, 1, CharacterDefinition(
            name=name, personality=personality, timezone='America/New_York'), '', now)
        connection.execute("INSERT INTO timelines (id, companion_id, status, created_at) VALUES (?, ?, 'active', ?)",
                           (timeline_id, companion_id, now))
        connection.execute('UPDATE companions SET active_version_id=?, active_timeline_id=? WHERE id=?',
                           (version_id, timeline_id, companion_id))
    return companion_id


def speaker(messages) -> str | None:
    found = re.search(r"Write (.+?)'s next message", messages[-1]['content'])
    return found and found[1]


def by_speaker(system, messages):
    """Each speaker says who they are, so a test can tell the replies apart (a 1:1 reply just says hello)."""
    return [Chunk(f'{speaker(messages)} here.' if speaker(messages) else 'Hello again.'), Chunk('', 'stop')]


@pytest.fixture
def cast(client, companion, connected, provider):
    """Mira (the main character), Billy and Sally, with replies that name their speaker."""
    provider.respond = by_speaker
    return {'Mira': companion['id'], 'Billy': companion_named(client, 'Billy Hart'),
            'Sally': companion_named(client, 'Sally Moss')}


def start(client, ids, name=None):
    return ok(client.post('/api/groups', json={'companion_ids': ids, 'name': name}))


def say(client, group_id, text, client_id):
    return ok(client.post(f'/api/groups/{group_id}/messages', json={'text': text, 'client_id': client_id}))


def messages(client, group_id):
    return ok(client.get(f'/api/groups/{group_id}'))['messages']


def shared(system: str) -> str:
    """The part of a request every speaker shares: up to the speaker's own character guidance."""
    return system[:system.index('\n\nYou are ', system.index('## The group chat so far'))]


def test_a_group_takes_two_or_more_companions_and_never_changes_the_main_character(client, cast):
    refused = client.post('/api/groups', json={'companion_ids': [cast['Billy']]})
    assert refused.status_code == 422
    group = start(client, [cast['Billy'], cast['Sally']])
    assert group['title'] == 'Billy and Sally' and [member['label'] for member in group['members']] == ['Billy', 'Sally']
    assert [line['text'] for line in messages(client, group['id'])] == ['You started a group with Billy and Sally.']
    assert ok(client.get('/api/companion'))['companion']['id'] == cast['Mira']

    renamed = ok(client.patch(f"/api/groups/{group['id']}", json={'name': 'Power Twins'}))
    assert renamed['title'] == 'Power Twins'
    assert messages(client, group['id'])[-1]['text'] == 'You named the group "Power Twins".'
    everyone = start(client, list(cast.values()), 'Everyone!')
    listed = ok(client.get('/api/groups'))['groups']
    assert [item['title'] for item in listed] == ['Everyone!', 'Power Twins']
    assert listed[0]['latest']['kind'] == 'app'

    fresh = ok(client.post(f"/api/groups/{everyone['id']}/copy"))
    assert fresh['id'] != everyone['id'] and len(fresh['members']) == 3 and fresh['name'] == ''
    assert ok(client.delete(f"/api/groups/{fresh['id']}"))['groups'][0]['id'] == everyone['id']
    assert client.get(f"/api/groups/{fresh['id']}").status_code == 404


def test_every_speaker_shares_the_cast_and_transcript_and_sees_only_their_own_life(client, cast, provider):
    # Mira's own chat and memories stay hers.
    send(client, 'The secret word is plum.', 'client-0001')
    ok(client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Favourite fruit', 'value': 'Quince'}))
    group = start(client, list(cast.values()), 'Everyone!')
    ok(client.patch(f"/api/groups/{group['id']}", json={'reply_cap': 3}))
    provider.requests.clear()

    say(client, group['id'], 'Hi everyone, how was your week?', 'group-0001')
    requests = provider.requests
    assert sorted(speaker(request['messages']) for request in requests) == ['Billy', 'Mira', 'Sally']
    prefixes = [shared(request['prompt']) for request in requests]
    # Each speaker's shared part is the one before plus the replies written since: the cache keeps it all.
    assert all(later.startswith(earlier) for earlier, later in zip(prefixes, prefixes[1:]))
    assert prefixes[0].startswith(groups.RULES)
    # The cast has everyone's "Others see" line; "I see myself" stays in each speaker's own part.
    with client.app.state.database.connect() as connection:
        lines = {name: perception.companion_lines(connection, value) for name, value in cast.items()}
    for name, found in lines.items():
        assert found['public'] and found['private'] and f"- {name}: {found['public']}" in prefixes[0]
        assert all(line not in prefixes[0] for line in found['private'])
    assert prefixes[0].endswith('User: Hi everyone, how was your week?')
    first = speaker(requests[0]['messages'])
    assert f'{first}: {first} here.' in prefixes[1]
    for request in requests:
        private = request['prompt'][len(shared(request['prompt'])):]
        assert f"You are {speaker(request['messages'])} in the group chat \"Everyone!\" with the user," in private
        assert '## This group chat (only you know this part)' in private
    mira = next(request for request in requests if speaker(request['messages']) == 'Mira')
    others = [request for request in requests if request is not mira]
    assert 'Quince' in mira['prompt'] and all('Quince' not in request['prompt'] for request in others)
    assert all(line in mira['prompt'] for line in lines['Mira']['private'])
    # Two people can draw the same bank phrase for themselves; only Mira's own lines must stay out of the others'.
    mine = set(lines['Mira']['private']) - {line for name in ('Billy', 'Sally') for line in lines[name]['private']}
    assert all(line not in request['prompt'] for request in others for line in mine)
    assert all('plum' not in request['prompt'] for request in others)

    # At one moment, every speaker who sees the same messages gets byte-identical shared text.
    database = client.app.state.database
    with database.connect() as connection:
        chat = groups.require_group(connection, group['id'])
        stays = groups.current_members(connection, group['id'])
        config = {'context_tokens': 16000, 'max_output_tokens': 800}
        built = [groups.prompt(connection, chat, by_id(connection, groups.companion_of(stay['member'])), stay,
                               database.clock.now(), config, 99, 'Hi') for stay in stays]
    assert len({item['shared'] for item in built}) == 1


def test_someone_added_from_now_on_sees_nothing_from_before_and_everything_shows_it_all(client, cast, provider):
    group = start(client, [cast['Billy'], cast['Mira']])
    say(client, group['id'], 'Before Sally joins: the party is a surprise.', 'group-0001')
    added = ok(client.post(f"/api/groups/{group['id']}/members", json={'companion_id': cast['Sally']}))
    assert [member['label'] for member in added['members']] == ['Billy', 'Mira', 'Sally']
    assert messages(client, group['id'])[-1]['text'] == 'You added Sally.'
    assert client.post(f"/api/groups/{group['id']}/members", json={'companion_id': cast['Sally']}).status_code == 409
    provider.requests.clear()
    say(client, group['id'], 'Sally, welcome!', 'group-0002')
    sally = provider.requests[0]
    assert speaker(sally['messages']) == 'Sally'
    assert 'surprise' not in sally['prompt'] and '[The user added Sally.]' in sally['prompt']
    assert 'have seen only what was said since you joined' in sally['prompt']
    assert all('surprise' in request['prompt'] for request in provider.requests[1:])

    # Shown everything so far, someone added later reads it all.
    other = start(client, [cast['Billy'], cast['Mira']])
    say(client, other['id'], 'The party is a surprise.', 'group-0003')
    ok(client.post(f"/api/groups/{other['id']}/members", json={'companion_id': cast['Sally'], 'history': 'everything'}))
    provider.requests.clear()
    say(client, other['id'], 'Sally, thoughts?', 'group-0004')
    assert 'surprise' in provider.requests[0]['prompt']
    assert 'since you joined' not in provider.requests[0]['prompt']


def test_the_witness_rule_records_who_was_there_and_removal_ends_what_they_see(client, cast, provider):
    group = start(client, list(cast.values()))
    say(client, group['id'], 'Hello all.', 'group-0001')
    first = next(line for line in messages(client, group['id']) if line['kind'] == 'user')
    with client.app.state.database.connect() as connection:
        row = connection.execute('SELECT present FROM group_messages WHERE id=?', (first['id'],)).fetchone()
    assert sorted(json.loads(row['present'])) == sorted(groups.member_key(value) for value in cast.values())

    ok(client.delete(f"/api/groups/{group['id']}/members/{cast['Billy']}"))
    assert messages(client, group['id'])[-1]['text'] == 'You removed Billy.'
    say(client, group['id'], 'Now that Billy is gone: his gift is a bike.', 'group-0002')
    say(client, group['id'], 'Billy? Billy!', 'group-0003')
    latest = messages(client, group['id'])
    assert all(line['name'] != 'Billy' for line in latest if line['kind'] == 'companion'
               and line['seq'] > first['seq'] + 4)
    with client.app.state.database.connect() as connection:
        billy = connection.execute('SELECT * FROM group_members WHERE member=?',
                                   (groups.member_key(cast['Billy']),)).fetchone()
        seen = groups.visible(connection, group['id'], billy['member'])
    assert all('bike' not in line['text'] for line in seen) and any(line['text'] == 'Hello all.' for line in seen)


def test_who_answers_is_decided_by_rules(client, cast):
    members = [{'member': f'companion:{name}', 'name': name} for name in ('Billy', 'Sally', 'Mira')]
    weight = {stay['member']: 1 for stay in members}
    # Anyone named answers first, in the order they come up; the rest fill up to the cap.
    assert groups.plan(members, 'mira and sally, what do you think?', 'seed', 2, weight) == \
        ['companion:Mira', 'companion:Sally']
    assert groups.plan(members, 'Billy?', 'seed', 1, weight) == ['companion:Billy']
    picked = groups.plan(members, 'hey all', 'seed', 2, weight)
    assert len(picked) == 2 and picked == groups.plan(members, 'hey all', 'seed', 2, weight)
    assert 'companion:Billy' not in groups.plan(members, 'hey all', 'seed', 3, weight, frozenset({'companion:Billy'}))
    # Someone who hasn't spoken for a while is far likelier to be picked.
    heavy = {**weight, 'companion:Sally': 1000}
    assert all(groups.plan(members, 'hey', f'seed-{n}', 1, heavy) == ['companion:Sally'] for n in range(20))
    # A reply naming someone who hasn't spoken has them answer next, beyond the plan once per round.
    queue = ['companion:Billy']
    assert groups.banter(queue, {'companion:Mira'}, 'What about you, Sally?', members, True) is True
    assert queue == ['companion:Sally', 'companion:Billy']
    assert groups.banter([], {'companion:Mira'}, 'Sally?', members, False) is False
    assert groups.mentioned('Billyboy and Sallyanne', members) == []


def test_replies_show_one_after_another_at_a_persons_pace(client, cast, monkeypatch):
    # Longer messages take longer to read and type, within bounds, and the same reply always takes the same time.
    quick, slow = groups.pace_seconds('hi', 'ok', 'a'), groups.pace_seconds('x' * 400, 'y' * 300, 'a')
    assert groups.PACE_SECONDS[0] <= quick < slow <= groups.PACE_SECONDS[1]
    assert quick == groups.pace_seconds('hi', 'ok', 'a')

    monkeypatch.setattr(groups, 'PACED', True)
    waits, seen = [], []

    async def pace(self, running, reply, seed):
        # Nobody sees a reply while it is written or held: it shows whole when it is sent.
        seen.append(dict(running.live))
        waits.append(reply)

    monkeypatch.setattr(groups.GroupChats, 'pace', pace)
    group = start(client, list(cast.values()))
    say(client, group['id'], 'Hey all, how is everyone?', 'group-pace')
    replies = [line for line in messages(client, group['id']) if line['kind'] == 'companion']
    assert len(waits) == len(replies) == 2 and seen == [{}, {}]
    # Turned off in Life settings, replies show as they are written.
    set_life(client, paced_replies=False)
    say(client, group['id'], 'Again?', 'group-pace-2')
    assert len(waits) == 2


def test_a_reply_keeps_only_the_speakers_own_words(client, cast):
    members = [{'member': 'a', 'name': 'Billy'}, {'member': 'b', 'name': 'Sally'}]
    assert groups.tidy('Billy: Sure thing!', 'Billy', members) == 'Sure thing!'
    assert groups.tidy('Sounds fun.\nSally: I agree!\nUser: ok', 'Billy', members) == 'Sounds fun.'
    assert groups.tidy('**Billy:** hi', 'Billy', members) == 'hi'


def test_the_transcript_drops_old_lines_in_chunks(client, cast):
    rows = [{'author': 'user', 'name': 'User', 'text': f'message number {n} ' + 'word ' * 20} for n in range(100)]
    budget = sum(groups.token_estimate(groups.line(row)) + 1 for row in rows[:50])
    start = groups.window(rows, budget)
    assert start % groups.CHUNK == 0 and 0 < start < 100
    # Messages added afterwards keep the same start until a whole chunk has to go.
    assert groups.window(rows + rows[:3], budget) in (start, start + groups.CHUNK)
    assert groups.window(rows[:10], budget) == 0


def test_replies_need_a_model_and_a_failed_one_can_be_tried_again(client, companion, provider):
    ids = [companion['id'], companion_named(client, 'Billy')]
    group = start(client, ids)
    unanswered = say(client, group['id'], 'Hi both!', 'group-0001')
    assert unanswered['connection'] == 'not_configured'
    assert ok(client.get(f"/api/groups/{group['id']}"))['ready'] is False
    ok(client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model'}))
    provider.replies = [[Chunk('', 'stop')]] * 2
    say(client, group['id'], 'Hi both!', 'group-0001')
    failed = [line for line in messages(client, group['id']) if line['kind'] == 'companion']
    assert failed and all(line['status'] == 'failed' and line['error'] for line in failed)
    provider.respond = by_speaker
    ok(client.post(f"/api/groups/{group['id']}/retry"))
    answered = [line for line in messages(client, group['id']) if line['kind'] == 'companion']
    assert len(answered) == 2 and all(line['status'] == 'complete' for line in answered)
    assert {line['text'] for line in answered} == {'Mira here.', 'Billy here.'}


def test_a_companion_who_starts_over_leaves_every_group_and_their_lines_stay(client, cast):
    group = start(client, list(cast.values()))
    say(client, group['id'], 'Mira, hello!', 'group-0001')
    ok(client.post('/api/companion/start-over', json={'name': 'Mira'}))
    view = ok(client.get(f"/api/groups/{group['id']}"))
    assert [member['label'] for member in view['group']['members']] == ['Billy', 'Sally']
    lines = view['messages']
    assert lines[-1]['text'] == 'Mira is no longer in the group.'
    assert any(line['name'] == 'Mira' and line['text'] == 'Mira here.' for line in lines)
