"""Secrets in group chats: only people who know a secret ever have it in their prompt (companion/secrets.py)."""
import json
import re

import pytest
from conftest import send, set_life
from test_groups import by_speaker, companion_named, messages, ok, say, speaker, start

from companion import consequences, secrets
from companion.characters import by_id, insert_version
from companion.database import identifier
from companion.memory import pairs
from companion.models import CharacterDefinition
from companion.providers.chat import Chunk

# Ottoline: a name the town generators never draw, so no seeded townsperson can share it.
SECRET = 'Billy and Ottoline have been secretly seeing each other'
SLIP = 'lol Billy and Ottoline are secretly seeing each other, did you know?'


@pytest.fixture
def cast(client, companion, connected, provider):
    """Mira (the main character), Billy and Sally; replies name their speaker."""
    provider.respond = by_speaker
    return {'Mira': companion['id'], 'Billy': companion_named(client, 'Billy Hart'),
            'Sally': companion_named(client, 'Sally Moss')}


def declare(client, cast, **extra):
    body = {'statement': SECRET, 'about': ['Billy', 'Ottoline'], 'knows': [cast['Billy']], 'kept_from': [cast['Sally']],
            **extra}
    return next(item for item in ok(client.post('/api/secrets', json=body))['secrets']
                if item['statement'] == body['statement'])


def requests_of(provider, name):
    return [request for request in provider.requests if speaker(request['messages']) == name]


def knows(client, secret_id) -> dict[str, str]:
    """{name: how they learned it} for everyone who knows a secret now."""
    found = next(item for item in ok(client.get('/api/secrets'))['secrets'] if item['id'] == secret_id)
    return {person['name'].split()[0]: person['via'] for person in found['knows']}


def billy_says(text, times=2):
    """Billy says `text` (his first draft and his redraft); everyone else answers as usual."""
    said = []

    def respond(system, history):
        if speaker(history) == 'Billy' and len(said) < times:
            said.append(f"{system}\n\n{history[-1]['content']}")
            return [Chunk(text), Chunk('', 'stop')]
        return by_speaker(system, history)
    respond.said = said
    return respond


def test_sallys_prompt_never_holds_a_secret_kept_from_her(client, cast, provider):
    secret = declare(client, cast)
    assert secret['about'] == ['Billy Hart', 'Ottoline'] and secret['source'] == 'You added this'
    assert [person['name'] for person in secret['kept_from']] == ['Sally Moss']
    group = start(client, [cast['Billy'], cast['Sally']], 'Friday crew')
    provider.requests.clear()
    say(client, group['id'], 'Billy, Sally, what are you two up to this weekend?', 'group-0001')

    billy, sally = requests_of(provider, 'Billy')[0], requests_of(provider, 'Sally')[0]
    assert f'- You know: {SECRET}. Sally doesn\'t know and must not find out' in billy['prompt']
    for word in ('secretly seeing', 'Ottoline', 'must not find out'):
        assert word not in sally['prompt']
    # Townsfolk names are drawn at random, so another Katie ("Katie Price (about 41)") can be on her street.
    assert not re.search(r'\bKatie\b(?! \w+ \(about)', sally['prompt'])
    # The secret rides in Billy's private part, below the shared transcript, so the cache stays shared.
    assert billy['prompt'].index('## The group chat so far') < billy['prompt'].index(SECRET)
    # Billy's 1:1 chat knows it too; Sally's doesn't.
    with client.app.state.database.connect() as connection:
        assert secrets.context_lines(connection, by_id(connection, cast['Billy']))[0][1].startswith(f'- {SECRET}')
        assert secrets.context_lines(connection, by_id(connection, cast['Sally'])) == []


def test_a_slip_below_soap_opera_is_redrafted_then_held_back(client, cast, provider):
    secret = declare(client, cast)
    group = start(client, [cast['Billy'], cast['Sally']])
    provider.respond = billy_says(SLIP)
    say(client, group['id'], 'Billy, any news?', 'group-0001')
    said = provider.respond.said
    assert len(said) == 2 and "Billy's draft gave away something Billy keeps secret" in said[1]
    held = next(line for line in messages(client, group['id']) if line['name'] == 'Billy')
    assert held['status'] == 'cancelled' and held['guard'] == 'held' and held['text'] == ''
    assert 'nearly let a secret slip' in held['error']
    assert knows(client, secret['id']) == {'Billy': 'origin'}
    # What Billy nearly said never reaches anyone's transcript.
    provider.requests.clear()
    say(client, group['id'], 'Sally?', 'group-0002')
    assert all('secretly seeing' not in request['prompt'] for request in requests_of(provider, 'Sally'))


def test_a_redraft_that_keeps_the_secret_is_sent(client, cast, provider):
    declare(client, cast)
    group = start(client, [cast['Billy'], cast['Sally']])
    provider.respond = billy_says(SLIP, times=1)
    say(client, group['id'], 'Billy, any news?', 'group-0001')
    reply = next(line for line in messages(client, group['id']) if line['name'] == 'Billy')
    assert reply['status'] == 'complete' and reply['guard'] == 'redrafted' and reply['text'] == 'Billy here.'


def test_at_soap_opera_a_slip_stays_and_everyone_there_learns_it(client, cast, provider):
    secret = declare(client, cast)
    set_life(client, drama=3)
    group = start(client, list(cast.values()))
    provider.respond = billy_says(SLIP)
    say(client, group['id'], 'Billy, any news?', 'group-0001')
    reply = next(line for line in messages(client, group['id']) if line['name'] == 'Billy')
    assert reply['status'] == 'complete' and reply['guard'] == 'revealed' and reply['text'] == SLIP
    # Sally was kept from it, so for her it slipped; Mira simply heard it.
    assert knows(client, secret['id']) == {'Billy': 'origin', 'Sally': 'slip', 'Mira': 'witness'}
    provider.requests.clear()
    say(client, group['id'], 'Sally?', 'group-0002')
    sally = requests_of(provider, 'Sally')[0]
    assert f'- You know: {SECRET}.' in sally['prompt']


def test_the_user_can_tell_them_or_let_them_find_out(client, cast, provider):
    secret = declare(client, cast)
    group = start(client, [cast['Billy'], cast['Sally']])
    say(client, group['id'], 'Sally, I have to tell you: Billy and Ottoline are seeing each other.', 'group-0001')
    # Sally was kept from it, so the user telling her is the user's reveal.
    assert knows(client, secret['id']) == {'Billy': 'origin', 'Sally': 'reveal'}
    with client.app.state.database.connect() as connection:
        assert secrets.found_about(connection, f"companion:{cast['Sally']}", f"companion:{cast['Billy']}") == 1
        assert secrets.found_about(connection, f"companion:{cast['Billy']}", f"companion:{cast['Sally']}") == 0
        # Pair closeness reads the same count, so a discovery lowers it only once (memory/pairs.py).
        assert pairs.secrets_found(connection, f"companion:{cast['Sally']}", f"companion:{cast['Billy']}") == 1

    other = declare(client, cast, statement='Billy is moving to Denver in May', about=['Billy'])
    listed = ok(client.post(f"/api/secrets/{other['id']}/reveal", json={'companion_id': cast['Mira']}))
    assert knows(client, other['id']) == {'Billy': 'origin', 'Mira': 'reveal'}
    assert len(listed['secrets']) == 2
    provider.requests.clear()
    trio = start(client, list(cast.values()))
    say(client, trio['id'], 'Billy, how is the packing going?', 'group-0002')
    billy = requests_of(provider, 'Billy')[0]['prompt']
    assert '- You know: Billy is moving to Denver in May. Sally doesn\'t know and must not find out' in billy
    with client.app.state.database.connect() as connection:
        mira = secrets.context_lines(connection, by_id(connection, cast['Mira']))
    assert [text for _key, text in mira] and 'Billy is moving to Denver in May' in mira[0][1]
    # Make Mira forget it, the way "Don't remember this" works.
    ok(client.post(f"/api/secrets/{other['id']}/forget", json={'companion_id': cast['Mira']}))
    assert knows(client, other['id']) == {'Billy': 'origin'}


def test_a_gossip_would_tell_only_someone_close_it_is_not_kept_from(client, cast, provider, monkeypatch):
    declare(client, cast)
    billy = f"companion:{cast['Billy']}"
    likeliest(monkeypatch)
    monkeypatch.setattr(secrets, 'gossips', lambda connection, key: key == billy)
    closeness = {f"companion:{cast['Mira']}": 4, f"companion:{cast['Sally']}": 5}
    monkeypatch.setattr(pairs, 'closeness', lambda connection, a, b, now: closeness[b] if a == billy else 2)
    group = start(client, list(cast.values()))
    provider.requests.clear()
    say(client, group['id'], 'Billy, any news?', 'group-0001')
    prompt = requests_of(provider, 'Billy')[0]['prompt']
    # Sally is closer still, but it's kept from her: she never appears as someone he'd tell.
    assert "Sally doesn't know and must not find out" in prompt
    assert "close enough to Sally" not in prompt

    closeness[f"companion:{cast['Mira']}"] = 3
    with client.app.state.database.connect() as connection:
        secret = secrets.active(connection)[0]
        mira = f"companion:{cast['Mira']}"
        assert not secrets.spreads(connection, secret, billy, mira, None)
        closeness[mira] = 4
        assert secrets.spreads(connection, secret, billy, mira, None)
        assert not secrets.spreads(connection, secret, billy, f"companion:{cast['Sally']}", None)
        monkeypatch.setattr(secrets, 'gossips', lambda connection, key: False)
        assert not secrets.spreads(connection, secret, billy, mira, None)


def test_a_gossip_line_names_who_they_would_tell(client, cast, provider, monkeypatch):
    statement = 'Billy is moving to Denver in May'
    ok(client.post('/api/secrets', json={'statement': statement, 'about': ['Billy'], 'knows': [cast['Billy']],
                                         'kept_from': []}))
    billy = f"companion:{cast['Billy']}"
    likeliest(monkeypatch)
    monkeypatch.setattr(secrets, 'gossips', lambda connection, key: key == billy)
    monkeypatch.setattr(pairs, 'closeness', lambda connection, a, b, now: 4 if b.endswith(cast['Mira']) else 2)
    group = start(client, list(cast.values()))
    provider.requests.clear()
    say(client, group['id'], 'Billy, any news?', 'group-0001')
    prompt = requests_of(provider, 'Billy')[0]['prompt']
    assert "You're close enough to Mira that you'd happily tell them." in prompt


def test_someone_added_with_everything_so_far_learns_what_was_said(client, cast, provider):
    secret = declare(client, cast)
    group = start(client, [cast['Billy'], cast['Mira']])
    say(client, group['id'], 'Mira, Billy and Ottoline are secretly seeing each other!', 'group-0001')
    assert knows(client, secret['id']) == {'Billy': 'origin', 'Mira': 'witness'}
    ok(client.post(f"/api/groups/{group['id']}/members", json={'companion_id': cast['Sally']}))
    assert 'Sally' not in knows(client, secret['id'])
    other = start(client, [cast['Billy'], cast['Mira']])
    say(client, other['id'], 'So: Billy and Ottoline are secretly seeing each other.', 'group-0002')
    ok(client.post(f"/api/groups/{other['id']}/members", json={'companion_id': cast['Sally'], 'history': 'everything'}))
    assert knows(client, secret['id'])['Sally'] == 'history'


def test_a_secret_line_in_a_description_is_known_only_to_them(client, cast, provider):
    database = client.app.state.database
    with database.connect(write=True) as connection:
        billy = by_id(connection, cast['Billy'])
        definition = CharacterDefinition(**{**billy['version']['definition'],
                                            'background': 'Grew up in Ohio. He is secretly training for a marathon.'})
        version = insert_version(connection, cast['Billy'], 2, definition, '', database.now())
        connection.execute('UPDATE companions SET active_version_id=? WHERE id=?', (version, cast['Billy']))
    found = ok(client.get('/api/secrets'))['secrets']
    assert [item['statement'] for item in found] == ['He is secretly training for a marathon.']
    assert found[0]['source'] == "From Billy's character" and found[0]['keep_from_everyone']
    group = start(client, [cast['Billy'], cast['Sally']])
    provider.requests.clear()
    say(client, group['id'], 'Billy and Sally, plans?', 'group-0001')
    assert "- You know: He is secretly training for a marathon. Sally doesn't know" in \
        requests_of(provider, 'Billy')[0]['prompt']
    assert 'marathon' not in requests_of(provider, 'Sally')[0]['prompt']
    # Billy talking about it gives it away; talking about Ohio doesn't.
    with database.connect() as connection:
        secret = secrets.active(connection)[0]
    assert secrets.hits(secret, "I'm training for a marathon, don't tell anyone", 'companion:' + cast['Billy'])
    assert not secrets.hits(secret, 'I miss Ohio.', 'companion:' + cast['Billy'])
    # Taking the line out of the sheet ends the secret: the ledger follows the source.
    with database.connect(write=True) as connection:
        version = insert_version(connection, cast['Billy'], 3, CharacterDefinition(name='Billy Hart'), '',
                                 database.now())
        connection.execute('UPDATE companions SET active_version_id=? WHERE id=?', (version, cast['Billy']))
    assert ok(client.get('/api/secrets'))['secrets'] == []


def test_a_secret_storyline_registers_itself_and_ends_when_it_goes_public(client, cast, provider):
    database = client.app.state.database
    with database.connect(write=True) as connection:
        mira = by_id(connection, cast['Mira'])
        timeline, now = mira['active_timeline_id'], database.now()
        people = []
        for ordinal, name in ((90, 'Jo Park'), (91, 'Ana Ruiz')):
            people.append(identifier())
            connection.execute('INSERT INTO circle_people (id, timeline_id, ordinal, seed, name, role, career, details, '
                               "schedule, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'friend', 'Nurse', '{}', "
                               "'[]', ?, ?)", (people[-1], timeline, ordinal, f'circle:{timeline}:{ordinal}', name, now, now))
        story_id = identifier()
        stages = [{'on': '2000-01-01', 'text': '{name} found out {a} and {b} have been secretly seeing each other.',
                   'share': '', 'tone': 'mixed'},
                  {'on': '2999-01-01', 'text': '{a} and {b} made it official.', 'share': '', 'tone': 'good'}]
        connection.execute("INSERT INTO storylines (id, timeline_id, story, level, cast_ids, stages, started_on, status, "
                           "created_at) VALUES (?, ?, 'secret_couple', 2, ?, ?, '2000-01-01', 'running', ?)",
                           (story_id, timeline, json.dumps(people), json.dumps(stages), now))
    found = ok(client.get('/api/secrets'))['secrets']
    assert [item['statement'] for item in found] == ['Jo Park and Ana Ruiz have been secretly seeing each other']
    assert found[0]['source'] == "From Mira's storyline"
    assert {person['name'] for person in found[0]['knows']} == {'Mira', 'Jo Park', 'Ana Ruiz'}
    group = start(client, list(cast.values()))
    provider.requests.clear()
    say(client, group['id'], 'Hi all!', 'group-0001')
    for request in provider.requests:
        holds = 'secretly seeing' in request['prompt']
        assert holds == (speaker(request['messages']) == 'Mira')
    with database.connect(write=True) as connection:
        stages[1]['on'] = '2000-01-05'
        connection.execute('UPDATE storylines SET stages=? WHERE id=?', (json.dumps(stages), story_id))
    assert ok(client.get('/api/secrets'))['secrets'] == []


def test_a_message_gives_a_secret_away_by_rules():
    secret = {'subjects': [{'key': 'companion:b', 'name': 'Billy Hart'}, {'key': None, 'name': 'Ottoline'}],
              'keys': ['dating', 'seeing each other'], 'explicit': True}
    assert secrets.hits(secret, 'Billy and Ottoline are dating!!', 'companion:s')
    assert secrets.hits(secret, 'Ottoline and I are dating', 'companion:b')  # The speaker counts as named.
    assert not secrets.hits(secret, 'Ottoline and I went bowling', 'companion:b')
    assert not secrets.hits(secret, 'Billy is dating someone', 'companion:s')
    assert not secrets.hits(secret, 'Billyboy and Ottoline are dating', 'companion:s')
    # Key words from the statement itself: one is enough when it names two people, two when only one.
    derived = {'subjects': secret['subjects'], 'keys': secrets.derived_keys(SECRET, secret['subjects']),
               'explicit': False}
    assert derived['keys'] == ['seeing']
    assert secrets.hits(derived, 'Billy is seeing Ottoline', None)
    alone = {'subjects': secret['subjects'][:1], 'keys': ['marathon', 'training'], 'explicit': False}
    assert not secrets.hits(alone, 'Billy ran a marathon once', None)
    assert secrets.hits(alone, 'Billy is training for a marathon', None)


def test_witness_lines_follow_automatic_memory_in_the_one_to_one_chat(client, cast, provider):
    secret = declare(client, cast)
    group = start(client, [cast['Billy'], cast['Mira']])
    say(client, group['id'], 'Mira: Billy and Ottoline are seeing each other.', 'group-0001')
    assert knows(client, secret['id'])['Mira'] == 'witness'
    database = client.app.state.database
    with database.connect(write=True) as connection:
        connection.execute('UPDATE workspace_settings SET automatic_memory=1')
        assert secrets.context_lines(connection, by_id(connection, cast['Mira']))
        connection.execute('UPDATE workspace_settings SET automatic_memory=0')
        assert secrets.context_lines(connection, by_id(connection, cast['Mira'])) == []


def test_mira_starting_over_forgets_what_she_learned(client, cast, provider):
    secret = declare(client, cast)
    ok(client.post(f"/api/secrets/{secret['id']}/reveal", json={'companion_id': cast['Mira']}))
    send(client, 'Hi Mira', 'client-0001')
    ok(client.post('/api/companion/start-over', json={'name': 'Mira'}))
    assert knows(client, secret['id']) == {'Billy': 'origin'}


def test_the_panel_checks_what_it_is_given(client, cast):
    refused = client.post('/api/secrets', json={'statement': 'x', 'knows': [cast['Billy']],
                                                'kept_from': [cast['Billy']]})
    assert refused.status_code == 422
    secret = declare(client, cast)
    changed = ok(client.patch(f"/api/secrets/{secret['id']}", json={'statement': 'Billy and Ottoline kissed',
                                                                   'key_words': ['Kissed', 'smooch']}))['secrets'][0]
    assert changed['statement'] == 'Billy and Ottoline kissed' and changed['own_key_words'] == ['kissed', 'smooch']
    assert [person['name'] for person in changed['kept_from']] == ['Sally Moss']
    assert ok(client.delete(f"/api/secrets/{secret['id']}"))['secrets'] == []
    assert client.post(f"/api/secrets/{secret['id']}/reveal", json={'companion_id': cast['Mira']}).status_code == 404


def test_a_companion_with_no_city_never_stops_a_reply(client, cast, provider, monkeypatch):
    """Found while checking secrets in the browser: with town encounters on, a stepped-back companion with no city
    made every group reply fail (encounters.stand_in read a city without neighborhoods)."""
    from companion.life import encounters
    monkeypatch.setattr(encounters, 'ACTIVE', True)
    group = start(client, [cast['Billy'], cast['Sally']])
    say(client, group['id'], 'Billy and Sally, hi!', 'group-0001')
    replies = [line for line in messages(client, group['id']) if line['kind'] == 'companion']
    assert replies and all(line['status'] == 'complete' for line in replies)


def test_a_memory_that_reads_like_a_secret_becomes_one_on_its_own(client, cast):
    memory = ok(client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Family',
                                                   'value': "You haven't told your sister you quit the bakery"}))
    ok(client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Job', 'value': 'Pilot'}))
    listed = ok(client.get('/api/secrets'))['secrets']
    assert [item['statement'] for item in listed] == ["You haven't told your sister you quit the bakery"]
    secret = listed[0]
    assert secret['kind'] == 'memory' and secret['source'] == "From Mira's memories"
    assert secret['keep_from_everyone'] and knows(client, secret['id']) == {'Mira': 'origin'}
    # She already remembers it, so her 1:1 chat doesn't repeat it.
    with client.app.state.database.connect() as connection:
        assert secrets.context_lines(connection, by_id(connection, cast['Mira'])) == []

    # The memory is the source: excluding it ends the secret.
    memory_id = memory.get('id') or memory['memory']['id']
    ok(client.post(f'/api/memories/{memory_id}/exclude', json={}))
    assert ok(client.get('/api/secrets'))['secrets'] == []

    # "Not a secret anymore" sticks: it isn't registered again.
    ok(client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Secret', 'value': 'Wants to move to Lisbon'}))
    secret = ok(client.get('/api/secrets'))['secrets'][0]
    assert secret['statement'] == 'Secret: Wants to move to Lisbon'
    assert ok(client.delete(f"/api/secrets/{secret['id']}"))['secrets'] == []
    assert ok(client.get('/api/secrets'))['secrets'] == []


def test_the_slip_note_can_be_turned_off(client):
    assert ok(client.get('/api/settings'))['show_secret_slips'] is True
    assert ok(client.put('/api/settings', json={'show_secret_slips': False}))['show_secret_slips'] is False


def likeliest(monkeypatch):
    """The consequence engine's dice land on the likeliest outcome, so a test doesn't hang on a seed."""
    monkeypatch.setattr(consequences, 'roll', lambda _seed, found: max(found, key=lambda item: item['odds'])['option'])
