"""Guests in group chats: people from the members' own lives join for a while (companion/group_guests.py)."""
import re
from datetime import timedelta

import pytest
from test_groups import companion_named, messages, ok, say, speaker, start

from companion import group_guests, groups
from companion.providers.chat import Chunk


def by_speaker(system, messages):
    return [Chunk(f'{speaker(messages)} here.' if speaker(messages) else 'Hello again.'), Chunk('', 'stop')]


@pytest.fixture
def cast(client, companion, connected, provider, monkeypatch):
    """Mira (with her circle) and Billy in a group; everyone awake, whatever the hour."""
    provider.respond = by_speaker
    monkeypatch.setattr(group_guests, 'doing', lambda connection, person, companion, now: 'at home')
    circle = ok(client.get('/api/life/circle'))
    billy = companion_named(client, 'Billy Hart')
    group = start(client, [companion['id'], billy], 'Friday crew')
    return {'Mira': companion['id'], 'Billy': billy, 'group': group['id'], 'circle': circle}


def guest_list(client, group_id):
    return ok(client.get(f'/api/groups/{group_id}/guests'))['people']


def add_guest(client, group_id, key):
    return ok(client.post(f'/api/groups/{group_id}/members', json={'companion_id': key}))


def test_anyone_a_member_knows_can_join_and_speaks_from_their_own_sheet(client, cast, provider):
    people = guest_list(client, cast['group'])
    friend = next(person for person in cast['circle'] if person['role'] == 'close friend')
    listed = next(person for person in people if person['key'] == friend['key'])
    assert listed['relation'] == "Mira's close friend" and listed['host_id'] == cast['Mira']
    assert {person['key'] for person in people} >= {person['key'] for person in cast['circle']}

    group = add_guest(client, cast['group'], friend['key'])
    guest = next(member for member in group['members'] if member['key'] == friend['key'])
    assert guest['companion_id'] is None and guest['guest']['relation'] == "Mira's close friend"
    assert guest['guest']['visits'] == 1 and not guest['guest']['kept'] and not guest['guest']['regular']
    assert group['title'] == 'Friday crew'
    assert messages(client, cast['group'])[-1]['text'] == f"You added {guest['label']}, Mira's close friend."
    assert friend['key'] not in {person['key'] for person in guest_list(client, cast['group'])}

    ok(client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Favourite fruit', 'value': 'Quince'}))
    provider.requests.clear()
    say(client, cast['group'], f"{guest['label']}, what are you up to tonight?", 'guest-0001')
    first = provider.requests[0]
    assert speaker(first['messages']) == guest['label']
    system = first['prompt']
    assert f"- {guest['label']} (Mira's close friend, a guest): " in system
    assert "You're a guest in this group chat: Mira brought you in." in system
    assert 'How you see yourself' in system and 'Quince' not in system
    assert "What you're doing: at home." in first['messages'][-1]['content']
    assert group_guests.NO_HISTORY in first['messages'][-1]['content']
    said = [line for line in messages(client, cast['group']) if line['kind'] == 'guest']
    assert said and said[0]['text'] == f"{guest['label']} here." and said[0]['name'] == guest['label']
    # Everyone else's shared part shows them in the cast too, the same bytes for every speaker.
    others = [request for request in provider.requests if request is not first]
    assert all(f"- {guest['label']} (Mira's close friend, a guest): " in request['prompt'] for request in others)


def test_a_member_pulls_in_someone_they_name_by_the_realism_slider(client, cast, provider, monkeypatch):
    friend = next(person for person in cast['circle'] if person['role'] == 'close friend')
    monkeypatch.setattr(group_guests, 'PULL_CHANCE', (0.0, 1.0, 1.0, 1.0))
    ok(client.put('/api/life/settings', json={'guests_realism': 0}))
    say(client, cast['group'], f"Is {friend['name']} coming on Friday?", 'pull-0001')
    assert all(line['kind'] != 'guest' for line in messages(client, cast['group']))
    assert not any(member['guest'] for member in ok(client.get(f"/api/groups/{cast['group']}"))['group']['members'])

    ok(client.put('/api/life/settings', json={'guests_realism': 2}))
    say(client, cast['group'], f"Honestly we should ask {friend['name']} along.", 'pull-0002')
    lines = messages(client, cast['group'])
    joined = next(line for line in lines if line['kind'] == 'app' and 'brought' in line['text'])
    assert re.match(rf"Mira brought {friend['name']}\b.*, their close friend\.", joined['text'])
    assert any(line['kind'] == 'guest' and line['seq'] > joined['seq'] for line in lines)
    # One pull-in at a time: someone else named straight after waits for the gap.
    other = next(person for person in cast['circle'] if person['key'] != friend['key'])
    say(client, cast['group'], f"And {other['name']} too?", 'pull-0003')
    members = ok(client.get(f"/api/groups/{cast['group']}"))['group']['members']
    assert other['key'] not in {member['key'] for member in members}


def test_whoever_answers_a_guest_who_has_said_their_piece_is_told_so(client, cast, provider):
    friend = next(person for person in cast['circle'] if person['role'] == 'close friend')
    group = add_guest(client, cast['group'], friend['key'])
    label = next(member['label'] for member in group['members'] if member['key'] == friend['key'])
    for index in range(group_guests.GUEST_REPLIES):
        say(client, cast['group'], f'{label}, story time {index}?', f'back-{index:04d}')
    note = groups.STEPPED_BACK.format(names=label)
    assert not any(note in request['messages'][-1]['content'] for request in provider.requests)
    provider.requests.clear()
    say(client, cast['group'], f'{label}, one more?', 'back-9999')
    assert provider.requests and all(note in request['messages'][-1]['content'] for request in provider.requests)
    assert all(speaker(request['messages']) != label for request in provider.requests)


def test_a_guest_says_only_so_much_and_never_while_asleep(client, cast, provider, monkeypatch):
    friend = next(person for person in cast['circle'] if person['role'] == 'close friend')
    group = add_guest(client, cast['group'], friend['key'])
    label = next(member['label'] for member in group['members'] if member['key'] == friend['key'])
    for index in range(group_guests.GUEST_REPLIES + 2):
        say(client, cast['group'], f'{label}, story time {index}?', f'cap-{index:04d}')
    said = [line for line in messages(client, cast['group']) if line['kind'] == 'guest']
    assert len(said) == group_guests.GUEST_REPLIES
    view = ok(client.get(f"/api/groups/{cast['group']}"))['group']['members']
    assert next(member for member in view if member['key'] == friend['key'])['guest']['replies_left'] == 0

    monkeypatch.setattr(group_guests, 'GUEST_REPLIES', 99)
    monkeypatch.setattr(group_guests, 'doing', lambda connection, person, companion, now: 'asleep')
    say(client, cast['group'], f'{label}, you there?', 'sleep-0001')
    assert len([line for line in messages(client, cast['group']) if line['kind'] == 'guest']) == len(said)


def test_guests_slip_out_when_it_goes_quiet_unless_kept_or_regular(app, client, cast, clock):
    friend, other = cast['circle'][0], cast['circle'][1]
    add_guest(client, cast['group'], friend['key'])
    add_guest(client, cast['group'], other['key'])
    ok(client.post(f"/api/groups/{cast['group']}/guests/keep", json={'person': other['key'], 'kept': True}))
    database = app.state.database
    assert groups.drift(database) == 0
    clock.advance(group_guests.QUIET + timedelta(minutes=1))
    assert groups.drift(database) == 1
    members = {member['key'] for member in ok(client.get(f"/api/groups/{cast['group']}"))['group']['members']}
    assert friend['key'] not in members and other['key'] in members
    assert messages(client, cast['group'])[-1]['text'].endswith('slipped out of the group.')

    # The third visit makes them a regular, who stays.
    for visit in range(2):
        add_guest(client, cast['group'], friend['key'])
        if visit == 0:
            clock.advance(group_guests.QUIET + timedelta(minutes=1))
            assert groups.drift(database) == 1
    assert messages(client, cast['group'])[-1]['text'].endswith('is a regular here now.')
    clock.advance(group_guests.QUIET + timedelta(minutes=1))
    assert groups.drift(database) == 0
    member = next(item for item in ok(client.get(f"/api/groups/{cast['group']}"))['group']['members']
                  if item['key'] == friend['key'])
    assert member['guest']['regular'] and member['guest']['visits'] == group_guests.REGULAR_VISITS


def test_guests_can_be_removed_and_leave_with_their_host(client, cast):
    friend = cast['circle'][0]
    add_guest(client, cast['group'], friend['key'])
    group = ok(client.delete(f"/api/groups/{cast['group']}/members/{friend['key']}"))
    assert friend['key'] not in {member['key'] for member in group['members']}
    assert client.post(f"/api/groups/{cast['group']}/members", json={'companion_id': 'circle:nobody:9'}).status_code == 404

    billy_group = start(client, [cast['Mira'], cast['Billy']])
    add_guest(client, billy_group['id'], friend['key'])
    with client.app.state.database.connect(write=True) as connection:
        groups.leave_everywhere(connection, cast['Mira'], client.app.state.database.now())
    members = ok(client.get(f"/api/groups/{billy_group['id']}"))['group']['members']
    assert [member['companion_id'] for member in members] == [cast['Billy']]


def test_someone_the_user_added_does_not_hold_back_a_pull_in(client, cast, provider, monkeypatch):
    friend, other = cast['circle'][0], cast['circle'][1]
    monkeypatch.setattr(group_guests, 'PULL_CHANCE', (0.0, 1.0, 1.0, 1.0))
    add_guest(client, cast['group'], friend['key'])
    say(client, cast['group'], f"Honestly we should ask {other['name']} along.", 'pull-user-0001')
    members = {member['key'] for member in ok(client.get(f"/api/groups/{cast['group']}"))['group']['members']}
    assert other['key'] in members


def test_a_guest_whose_time_is_up_leaves_before_the_next_message(client, cast, clock, provider):
    friend = cast['circle'][0]
    ok(client.put('/api/life/settings', json={'guests_realism': 0}))
    add_guest(client, cast['group'], friend['key'])
    say(client, cast['group'], 'Hello everyone', 'quiet-0001')
    clock.advance(group_guests.QUIET + timedelta(minutes=1))
    say(client, cast['group'], f"Morning! {friend['name']}, still here?", 'quiet-0002')
    lines = messages(client, cast['group'])
    asked = next(line for line in lines if line['text'].startswith('Morning!'))
    assert lines[asked['seq'] - 2]['text'].endswith('slipped out of the group.')
    assert not any(line['kind'] == 'guest' and line['seq'] > asked['seq'] for line in lines)


def test_guests_stay_put_while_the_app_is_paused(app, client, cast, clock):
    friend = cast['circle'][0]
    add_guest(client, cast['group'], friend['key'])
    clock.advance(group_guests.QUIET + timedelta(minutes=1))
    ok(client.post('/api/pause'))
    app.state.life.spread_news()
    assert friend['key'] in {member['key'] for member in ok(client.get(f"/api/groups/{cast['group']}"))['group']['members']}
    ok(client.post('/api/resume'))
    app.state.life.spread_news()
    assert friend['key'] not in {member['key'] for member in ok(client.get(f"/api/groups/{cast['group']}"))['group']['members']}


def test_a_renamed_circle_person_joins_under_the_name_the_user_gave(client, cast, provider):
    sister = cast['circle'][1]
    with client.app.state.database.connect(write=True) as connection:  # Seeded with a family name, as in a city.
        connection.execute('UPDATE circle_people SET details=json_set(details, \'$.full_name\', ?) WHERE id=?',
                           (f"{sister['name']} Moreno", sister['id']))
    assert next(person for person in guest_list(client, cast['group'])
                if person['key'] == sister['key'])['name'] == f"{sister['name']} Moreno"
    ok(client.patch(f"/api/life/circle/{sister['id']}", json={'name': 'Lizzie'}))
    listed = next(person for person in guest_list(client, cast['group']) if person['key'] == sister['key'])
    assert listed['name'] == 'Lizzie Moreno'
    add_guest(client, cast['group'], sister['key'])
    provider.requests.clear()
    say(client, cast['group'], 'Lizzie, what are you up to?', 'rename-0001')
    asked = next(request for request in provider.requests if speaker(request['messages']) == 'Lizzie')
    assert 'Who you are: Lizzie Moreno, ' in asked['prompt']


def test_a_guest_answers_a_little_less_often_than_members_however_long_they_have_been_quiet():
    weights = groups.guests_weighed({'companion:a': 2.0, 'companion:b': 3.0, 'circle:t:0': 6.0, 'circle:t:1': 1.0})
    assert weights['companion:a'] == 2.0 and weights['companion:b'] == 3.0
    assert weights['circle:t:0'] == 2.5 * group_guests.GUEST_WEIGHT  # The members' average, then the share.
    assert weights['circle:t:1'] == 1.0 * group_guests.GUEST_WEIGHT
    assert all(weights[guest] < min(weights['companion:a'], weights['companion:b']) for guest in ('circle:t:0', 'circle:t:1'))


def test_a_townsperson_guest_acts_on_their_sliders_with_the_users_edits(client, clock, provider, monkeypatch):
    from test_social_circle import make

    from companion.life import encounters
    from companion.world import catalog, personality, townsfolk

    provider.respond = by_speaker
    monkeypatch.setattr(group_guests, 'doing', lambda connection, person, companion, now: 'at home')
    mira = make(client, 'Warm and curious.', home_city='baltimore')
    ok(client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                            'api_key': 'secret-key'}))
    data = catalog.city('baltimore')
    sheet = townsfolk.at_place(data, data['places'][0]['id'])[0]
    original = encounters.history_for

    def met(connection, companion, cast, now, before=None):
        meetings = [{'place': sheet['place']['name'], 'local_date': f'2026-09-0{day}',
                     'met_at': f'2026-09-0{day}T18:00:00+00:00'} for day in (1, 2, 3)]
        return {**original(connection, companion, cast, now, before), sheet['key']: meetings}

    monkeypatch.setattr(encounters, 'history_for', met)
    group = start(client, [mira['id'], companion_named(client, 'Billy Hart')], 'Friday crew')
    social = personality.for_sheet(townsfolk.drawn(sheet), sheet)['social']['level']
    edited = 0 if social == 2 else 2
    ok(client.post('/api/life/townsfolk/personality',
                   json={'key': sheet['key'], 'sliders': {'social': {'level': edited, 'source': 'you'}}}))
    view = ok(client.post(f"/api/groups/{group['id']}/members", json={'companion_id': sheet['key']}))
    label = next(member['label'] for member in view['members'] if member['key'] == sheet['key'])
    provider.requests.clear()
    say(client, group['id'], f'{label}, how was your week?', 'town-0001')
    system = next(request for request in provider.requests if speaker(request['messages']) == label)['system']
    acts = system[system.index('How you tend to act'):]
    assert next(trait for trait in personality.traits() if trait['key'] == 'social')['model'][edited] in acts


def test_their_people_stop_dropping_in_once_you_have_split(monkeypatch):
    from companion.life import breakups, their_people
    person = {'key': 'circle:t:1', 'kind': 'circle', 'person_id': 'p1', 'host': 'companion:c1'}
    monkeypatch.setattr(group_guests, 'candidates', lambda *_args: [person])
    monkeypatch.setattr(group_guests, 'host_companion', lambda *_args: {'id': 'c1'})
    monkeypatch.setattr(their_people, 'met_people', lambda *_args: {'p1'})
    monkeypatch.setattr(breakups, 'ended', lambda *_args: False)
    assert group_guests.dropping_in(None, [], None) == [person]
    monkeypatch.setattr(breakups, 'ended', lambda *_args: True)
    assert group_guests.dropping_in(None, [], None) == []


def test_in_an_older_era_a_guest_is_their_mother_not_their_mom():
    row = {'seed': 's', 'name': 'Edith', 'role': 'mom', 'details': '{}', 'id': 'p1', 'timeline_id': 't'}
    older = group_guests.from_circle(row, 'companion:x', 'Ada', older=True)
    assert older['relation'] == "Ada's mother" and older['tie'] == 'their mother'
    assert group_guests.from_circle(row, 'companion:x', 'Ada')['relation'] == "Ada's mom"
