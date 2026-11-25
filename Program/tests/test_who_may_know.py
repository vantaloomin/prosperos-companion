"""Who may know this: a secret and a piece of news never reach the prompt of anyone who doesn't hold them, through
any prompt builder (companion/secrets.py, companion/news.py).

One world for every builder: Billy knows Billy and Ottoline's secret, kept from Mira; Billy's news (glassblowing)
has reached Sally and nobody else. Mira holds neither, so no request written for Mira may carry either one: her
chat, a call, a first text and a voice note, an answer on the feed, a group chat, a Story scene, and the day the
Watching page tells. Each test also checks a holder's prompt does carry it, so an absence means something."""
from datetime import timedelta

import pytest
from conftest import reconcile, send, set_life
from test_drop_by import SHIFTS
from test_groups import ok, start
from test_groups import say as group_say
from test_openers import check, interview
from test_story import say as story_say
from test_story_secrets import sam as companion_in_baltimore
from test_together import mira
from test_voice_notes import speaker  # noqa: F401 - the fake built-in voice, used as a fixture.

from companion import news, story_cast
from companion.characters import by_id
from companion.life import narrator, post_comments
from companion.memory import context, pairs
from companion.providers.chat import Chunk
from companion.text_models import CHAT, reply_config
from companion.voice import notes
from companion.world import catalog

SECRET = 'Billy and Ottoline have been secretly seeing each other'
NEWS = 'Billy took up glassblowing in Fells Point'
GIVEAWAYS = ('Ottoline', 'secretly seeing', 'glassblowing')


def text_of(request: dict) -> str:
    return request['system'] + '\n' + '\n'.join(str(item['content']) for item in request['messages'])


def assert_kept(text: str):
    for word in GIVEAWAYS:
        assert word not in text, f'{word!r} reached a prompt of someone who does not hold it'


def plain(_system, messages):
    """Any reply at all: a group speaker or a Story companion says who they are."""
    content = str(messages[-1]['content']) if messages else ''
    for marker in ("Write ", "'s next"):
        if marker not in content:
            return [Chunk('Okay!'), Chunk('', 'stop')]
    name = content.split("Write ")[-1].split("'s next")[0]
    return [Chunk(f'"Hey," {name} says.'), Chunk('', 'stop')]


@pytest.fixture
def world(client, monkeypatch, provider):
    """Mira (main, tends bar at Club Charles 09:00 to 17:00), Billy and Sally; Monday noon."""
    mira(client, monkeypatch, schedule=SHIFTS)
    reconcile(client)
    found = {'Mira': client.get('/api/companion').json()['companion']['id'], 'Billy': companion_in_baltimore(client),
             'Sally': companion_in_baltimore(client)}
    database = client.app.state.database
    with database.connect(write=True) as connection:
        for name, full in (('Billy', 'Billy Hart'), ('Sally', 'Sally Moss')):
            connection.execute("UPDATE character_versions SET name=?, definition=json_set(definition, '$.name', ?) "
                               'WHERE companion_id=?', (full, full, found[name]))
    secret = ok(client.post('/api/secrets', json={'statement': SECRET, 'about': ['Billy', 'Ottoline'],
                                                  'knows': [found['Billy']], 'kept_from': [found['Mira']]}))
    assert any(item['statement'] == SECRET for item in secret['secrets'])
    today = database.clock.now().date().isoformat()
    monkeypatch.setattr(news, 'found', lambda _connection, companion, _now: [
        {'source': 'chapter:glass', 'text': NEWS, 'happened_on': today}] if companion['id'] == found['Billy'] else [])
    with database.connect(write=True) as connection:
        news.sync(connection, database.clock.now())
        item = connection.execute('SELECT id FROM news').fetchone()
        news.hear(connection, item['id'], pairs.companion_key(found['Sally']), pairs.companion_key(found['Billy']), 1,
                  today, 'word', database.now())
    provider.respond = plain
    return found


def own_prompt(client, companion_id: str) -> str:
    """A 1:1 chat prompt as the context builder makes it for anyone, holder or not."""
    database = client.app.state.database
    with database.connect() as connection:
        packet = context.build(connection, by_id(connection, companion_id), database.clock.now(), 8000)
    return text_of(packet)


def test_the_holders_have_it_so_its_absence_means_something(client, world):
    assert SECRET in own_prompt(client, world['Billy'])
    assert NEWS in own_prompt(client, world['Sally'])


def test_her_chat_and_a_call(client, world, provider, clock):
    send(client, 'Hey Mira, what is new with everyone?', 'sweep-chat')
    assert_kept(text_of(provider.requests[-1]))
    clock.advance(timedelta(hours=6))  # 18:00, off work: she picks up.
    send(client, 'can I call you?', 'sweep-call')
    assert 'You are on a phone call with the user right now' in provider.requests[-1]['prompt']
    send(client, 'So, any gossip about Billy?', 'sweep-call-2')
    assert_kept(text_of(provider.requests[-1]))


def test_a_first_text_and_a_voice_note(client, world, provider, clock, speaker, monkeypatch):  # noqa: F811
    set_life(client, texts_first=True)
    clock.advance(timedelta(hours=6))
    interview(client)
    monkeypatch.setattr(notes, 'CHANCE', 1.0)
    message = check(client)['message']
    assert message and message['voice']
    assert notes.INSTRUCTION in provider.requests[-1]['messages'][-1]['content']
    assert_kept(text_of(provider.requests[-1]))


def test_her_answer_on_the_feed(client, world):
    database = client.app.state.database
    with database.connect(write=True) as connection:
        config = reply_config(connection, CHAT)
        packet = post_comments.companion_packet(
            connection, by_id(connection, world['Mira']), config, database.clock.now(),
            {'text': 'Behind the bar tonight.'}, {'text': 'Who else was in?'}, [])
    assert_kept(text_of(packet))


def test_a_group_chat(client, world, provider):
    group = start(client, [world['Mira'], world['Billy'], world['Sally']])
    provider.requests.clear()
    group_say(client, group['id'], 'Mira, Billy, Sally: what is everyone up to?', 'sweep-group')
    by_name = {}
    for request in provider.requests:
        content = str(request['messages'][-1]['content'])
        for name in ('Mira', 'Billy', 'Sally'):
            if f"Write {name}'s next message" in content:
                by_name[name] = text_of(request)
    assert 'Ottoline' in by_name['Billy'] and 'glassblowing' in by_name['Sally']
    assert_kept(by_name['Mira'])
    assert 'Ottoline' not in by_name['Sally']


def test_a_story_scene(client, world, provider, monkeypatch):
    original = story_cast.place_now

    def place_now(connection, companion, data, now):
        if companion['id'] in (world['Billy'], world['Sally']):
            return catalog.find(data, 'club-charles'), story_cast.OWN_TIME
        return original(connection, companion, data, now)
    monkeypatch.setattr(story_cast, 'place_now', place_now)
    ok(client.put('/api/story/scene', json={'city_id': 'baltimore', 'place_id': 'club-charles'}))
    provider.requests.clear()
    story_say(client, 'I sit at the bar. "Evening, all of you."', 'sweep-story')
    by_name = {}
    for request in provider.requests:
        content = str(request['messages'][-1]['content'])
        for name in ('Mira', 'Billy', 'Sally'):
            if f"Write {name}'s next turn in the scene" in content:
                by_name[name] = text_of(request)
    assert 'Ottoline' in by_name['Billy'] and 'glassblowing' in by_name['Sally']
    assert_kept(by_name['Mira'])
    # The narrator holds nothing.
    assert_kept(text_of(provider.requests[0]))


def test_the_day_watching_tells(client, world, provider, clock):
    for _ in range(2):
        clock.advance(timedelta(hours=20))
        reconcile(client)
    ok(client.put('/api/observer', json={'watching': True, 'focus': f"companion:{world['Mira']}"}))
    shown = ok(client.get('/api/observer/feed'))
    assert_kept(str(shown))
    database = client.app.state.database
    with database.connect(write=True) as connection:  # It catches up their thoughts as it reads them.
        due = narrator.due_entry(connection, database.clock.now())
    assert_kept(str(due))
