"""How a companion takes what the user did: only four sure things, and only through traits the user built in."""
from datetime import timedelta

import pytest
from conftest import reconcile, send, show
from test_groups import companion_named, ok, say, start
from test_secrets import declare

from companion import consequences
from companion.characters import by_id, insert_version
from companion.database import identifier
from companion.life import reactions
from companion.models import CharacterDefinition


@pytest.fixture(autouse=True)
def shown(client):
    """How they took it shows on Today only with Hidden values > Show how they're feeling on."""
    show(client, show_moods=True)


def likeliest(monkeypatch):
    monkeypatch.setattr(consequences, 'roll', lambda _seed, found: max(found, key=lambda item: item['odds'])['option'])


def stinging(monkeypatch):
    """The dice land on the sting whenever it is possible at all."""
    monkeypatch.setattr(consequences, 'roll', lambda _seed, found: found[-1]['option'] if found[-1]['odds'] else 0)


def with_traits(client, companion_id, *traits):
    """The companion's definition again, with these emotional traits ({name: intensity})."""
    database = client.app.state.database
    with database.connect(write=True) as connection:
        found = by_id(connection, companion_id)
        definition = {**found['version']['definition'],
                      'emotional_traits': [{'name': name, 'intensity': level} for name, level in traits]}
        version_id = insert_version(connection, companion_id, found['version']['number'] + 1,
                                    CharacterDefinition(**definition), '', database.now())
        connection.execute('UPDATE companions SET active_version_id=? WHERE id=?', (version_id, companion_id))


def test_only_a_trait_that_speaks_to_it_can_make_it_sting():
    plain = {'name': 'Mira'}
    assert reactions.minds(plain, 'user:forgot_occasion') == (0, '')
    loyal = {'name': 'Mira', 'emotional_traits': [{'name': 'Fiercely loyal', 'intensity': 'strong'},
                                                   {'name': 'Jealousy', 'intensity': 'mild'}]}
    assert reactions.minds(loyal, 'user:told_secret') == (3, 'Fiercely loyal')
    assert reactions.minds(loyal, 'user:missed_plan') == (0, '')
    companion = {'version': {'definition': plain}}
    calm = reactions.what_if(companion, 'user:told_secret', {'a': 'Sally'})
    assert [item['odds'] for item in calm] == [1, 0]
    assert calm[1]['reasons'] == ["nothing in Mira's character says this would bother them"]
    hurt = reactions.what_if({'version': {'definition': loyal}}, 'user:told_secret', {'a': 'Sally'})
    assert hurt[1]['odds'] == 0.6 and hurt[1]['label'] == 'Mira is hurt the secret got out'
    assert 'Mira\'s character includes "Fiercely loyal"' in hurt[1]['reasons']


@pytest.fixture
def birthday_today(client, clock):
    today = clock.now().date()
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC',
                                                     'birthday': today.strftime('%m-%d')})
    assert response.status_code == 200, response.text
    return response.json()


def test_chatting_on_a_birthday_without_mentioning_it_can_sting(client, birthday_today, clock, provider, monkeypatch):
    with_traits(client, birthday_today['id'], ('Sentimental about birthdays', 'strong'))
    stinging(monkeypatch)
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    send(client, 'How was work?', 'client-reaction-01')
    clock.advance(timedelta(days=1))
    reconcile(client)
    listed = client.get('/api/life/reactions').json()
    assert len(listed) == 1 and listed[0]['choice'] == 'user:forgot_occasion' and listed[0]['picked'] == 1
    assert listed[0]['marks'][0]['kind'] == 'mood'
    prompt = client.get('/api/context/preview').json()['prompt']
    assert "You're a little hurt that the user chatted with you on your birthday without mentioning it." in prompt

    reconcile(client)
    assert len(client.get('/api/life/reactions').json()) == 1
    changed = ok(client.post(f"/api/life/consequences/{listed[0]['id']}/change", json={'option': 0}))
    assert changed['picked_by'] == 'user' and changed['marks'] == []
    assert 'a little hurt' not in client.get('/api/context/preview').json()['prompt']


def test_mentioning_it_or_not_minding_leaves_nothing(client, birthday_today, clock, provider, monkeypatch):
    stinging(monkeypatch)
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    send(client, 'How was work?', 'client-reaction-02')
    clock.advance(timedelta(days=1))
    reconcile(client)
    listed = client.get('/api/life/reactions').json()
    # No trait says Mira minds: she lets it go, whatever the dice.
    assert [item['picked'] for item in listed] == [0] and listed[0]['marks'] == []


def test_an_agreed_plan_passing_without_a_word(client, companion, clock, monkeypatch):
    with_traits(client, companion['id'], ('Feels let down easily', 'moderate'))
    stinging(monkeypatch)
    yesterday = (clock.now() - timedelta(days=1)).date().isoformat()
    database = client.app.state.database
    with database.connect(write=True) as connection:
        now = database.now()
        connection.execute(
            "INSERT INTO memories (id, companion_id, timeline_id, layer, subject, value, reality, authority, status, "
            "plan_status, stated_at, applies_from, created_at, updated_at) VALUES (?, ?, ?, 'plan', 'movie night', "
            "'movie night together', 'real', 'confirmed', 'active', 'agreed', ?, ?, ?, ?)",
            (identifier(), companion['id'], companion['active_timeline_id'], now, yesterday, now, now))
    reconcile(client)
    listed = client.get('/api/life/reactions').json()
    assert [item['choice'] for item in listed] == ['user:missed_plan']
    assert listed[0]['marks'][0]['note'] == 'Mira is let down the plan (movie night together) passed without a word'


def test_telling_someone_a_secret_in_a_group(client, companion, connected, provider, monkeypatch):
    from test_groups import by_speaker
    provider.respond = by_speaker
    cast = {'Mira': companion['id'], 'Billy': companion_named(client, 'Billy Hart'),
            'Sally': companion_named(client, 'Sally Moss')}
    with_traits(client, cast['Billy'], ('Values his privacy', 'strong'))
    likeliest(monkeypatch)
    declare(client, cast)
    group = start(client, [cast['Billy'], cast['Sally']])
    say(client, group['id'], 'Sally, I have to tell you: Billy and Ottoline are seeing each other.', 'group-0001')
    with client.app.state.database.connect() as connection:
        billy = by_id(connection, cast['Billy'])
        found = consequences.recent(connection, billy['active_timeline_id'], 'user:', '2000-01-01')
    assert [(item['choice'], item['picked']) for item in found] == [('user:told_secret', 1)]
    assert found[0]['label'] == 'How Billy takes the user telling Sally a secret'


def test_out_of_character_what_if_gets_the_odds(client, provider, clock, monkeypatch):
    from test_storylines import WORKDAY

    from companion.life import body, storylines
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    ok(client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC', 'schedule': WORKDAY,
                                           'location': 'Fells Point, Baltimore'}))
    monkeypatch.setattr(storylines, 'START', (1, 1, 1, 1))
    monkeypatch.setattr(storylines, 'STORIES', (storylines.find_story('promotion_chance'),))
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    reconcile(client)
    send(client, 'OOC: what happens with the promotion?', 'client-reaction-ooc')
    prompt = '\n'.join(str(item) for item in provider.requests[-1].values())
    assert 'answer honestly from these odds' in prompt
    assert 'Whether Mira gets the promotion' in prompt and 'Mira got the promotion (about 50%)' in prompt
    send(client, 'How was work?', 'client-reaction-in')
    assert 'answer honestly from these odds' not in '\n'.join(str(item) for item in provider.requests[-1].values())


def test_showing_a_newcomer_everything_said_before(client, companion, connected, provider, monkeypatch):
    from test_groups import by_speaker
    provider.respond = by_speaker
    billy, sally = companion_named(client, 'Billy Hart'), companion_named(client, 'Sally Moss')
    with_traits(client, billy, ('Guarded', 'strong'))
    likeliest(monkeypatch)
    group = start(client, [billy, companion['id']], name='Book club')
    say(client, group['id'], 'Billy, how was your week?', 'group-0001')
    ok(client.post(f"/api/groups/{group['id']}/members", json={'companion_id': sally, 'history': 'everything'}))
    with client.app.state.database.connect() as connection:
        found = consequences.recent(connection, by_id(connection, billy)['active_timeline_id'], 'user:', '2000-01-01')
    assert [(item['choice'], item['picked']) for item in found] == [('user:showed_everything', 1)]
    assert found[0]['marks'][0]['note'] == 'Billy feels exposed that Sally can read everything said in Book club'
