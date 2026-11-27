"""Secrets and news in a Story scene (companion/story_secrets.py): everyone in the scene hears what is said there,
and a companion keeps a secret from someone there it is kept from, by the group chat's rules."""
import re

import pytest
from conftest import reconcile, set_life
from test_drop_by import SHIFTS
from test_story import ok, say
from test_together import mira

from companion import news, story_cast, story_secrets
from companion.characters import by_id, insert_version
from companion.database import identifier
from companion.models import CharacterDefinition
from companion.providers.chat import Chunk
from companion.world import catalog

SECRET = 'Mira is leaving Club Charles for a bar job in Lisbon'
SLIP = '"I\'m leaving Club Charles," Mira says. "Took a bar job in Lisbon."'


def turn_of(messages) -> str | None:
    found = re.search(r"Write (.+?)'s next turn in the scene", messages[-1]['content'])
    return found and found[1]


def sam(client) -> str:
    """Sam Reyes, another companion in Baltimore, stepped back."""
    database = client.app.state.database
    with database.connect(write=True) as connection:
        companion_id, timeline_id, now = identifier(), identifier(), database.now()
        connection.execute('INSERT INTO companions (id, slot, stepped_back_at, created_at) VALUES (?, NULL, ?, ?)',
                           (companion_id, now, now))
        version_id = insert_version(connection, companion_id, 1, CharacterDefinition(
            name='Sam Reyes', personality='Easygoing.', timezone='UTC', home_city='Baltimore'), '', now)
        connection.execute("INSERT INTO timelines (id, companion_id, status, created_at) VALUES (?, ?, 'active', ?)",
                           (timeline_id, companion_id, now))
        connection.execute('UPDATE companions SET active_version_id=?, active_timeline_id=? WHERE id=?',
                           (version_id, timeline_id, companion_id))
    return companion_id


@pytest.fixture
def scene(client, monkeypatch, provider):
    return set_scene(client, monkeypatch)


def set_scene(client, monkeypatch, **values):
    """Mira works her shift at Club Charles; Sam is there on his own time. Monday noon."""
    mira(client, monkeypatch, schedule=SHIFTS, **values)
    reconcile(client)
    found = {'Mira': client.get('/api/companion').json()['companion']['id'], 'Sam': sam(client)}
    original = story_cast.place_now

    def place_now(connection, companion, data, now):
        if companion['id'] == found['Sam']:
            return catalog.find(data, 'club-charles'), story_cast.OWN_TIME
        return original(connection, companion, data, now)
    monkeypatch.setattr(story_cast, 'place_now', place_now)
    moved = ok(client.put('/api/story/scene', json={'city_id': 'baltimore', 'place_id': 'club-charles'}))
    assert {item['name'] for item in moved['scene']['companions']} == {'Mira', 'Sam'}
    return found


def lines_say(**said):
    """Each companion's turn says what `said` gives for them (a list is one draft after another); the narrator and
    anyone else say something plain. `respond.asked` keeps each companion's requests."""
    asked = {}

    def respond(system, messages):
        name = turn_of(messages)
        if name is None:
            return [Chunk('The bar is dim and half full.'), Chunk('', 'stop')]
        asked.setdefault(name, []).append({'system': system, 'notes': messages[-1]['content']})
        found = said.get(name, f'"Hey," {name} says.')
        text = found[min(len(asked[name]), len(found)) - 1] if isinstance(found, list) else found
        return [Chunk(text), Chunk('', 'stop')]
    respond.asked = asked
    return respond


def declare(client, found, **extra):
    body = {'statement': SECRET, 'about': ['Mira'], 'knows': [found['Mira']], 'kept_from': [found['Sam']], **extra}
    return next(item for item in ok(client.post('/api/secrets', json=body))['secrets']
                if item['statement'] == body['statement'])


def knows(client, secret_id) -> dict[str, str]:
    found = next(item for item in ok(client.get('/api/secrets'))['secrets'] if item['id'] == secret_id)
    return {person['name'].split()[0]: person['via'] for person in found['knows']}


def story_lines(client):
    return [(row['role'], row.get('name'), row['text']) for row in ok(client.get('/api/story'))['messages']]


def test_a_slip_in_front_of_someone_it_is_kept_from_is_redrafted(client, scene, provider):
    secret = declare(client, scene)
    provider.respond = lines_say(Mira=[SLIP, '"Same old," Mira says.'])
    say(client, 'I sit at the bar. "Mira, any news?"', 'story-0001')
    asked = provider.respond.asked['Mira']
    # She is told who here must not find out, and a draft that gives it away is written once more.
    assert f"- You know: {SECRET}. Sam doesn't know and must not find out: never say it or hint at it here." in \
        asked[0]['notes']
    assert len(asked) == 2 and "Mira's draft gave away something Mira keeps secret" in asked[1]['notes']
    assert "Write Mira's turn again" in asked[1]['notes']
    assert ('companion', 'Mira', '"Same old," Mira says.') in story_lines(client)
    assert knows(client, secret['id']) == {'Mira': 'origin'}
    # Sam's own request never holds it.
    assert all(SECRET not in item['system'] + item['notes'] for item in provider.respond.asked['Sam'])


def test_below_soap_opera_a_line_that_still_gives_it_away_is_not_said(client, scene, provider):
    secret = declare(client, scene)
    provider.respond = lines_say(Mira=[SLIP, SLIP])
    say(client, 'I sit at the bar. "Mira, any news?"', 'story-0001')
    held = [text for role, name, text in story_lines(client) if role == 'companion' and name == 'Mira']
    assert held[0] in [line.format(name='Mira', their=their) for line in story_secrets.HELD for their in ('her', 'their')]
    assert all('Lisbon' not in text for _role, _name, text in story_lines(client))
    assert knows(client, secret['id']) == {'Mira': 'origin'}


def test_at_soap_opera_a_slip_stays_and_everyone_there_learns_it(client, scene, provider):
    secret = declare(client, scene)
    set_life(client, drama=3)
    provider.respond = lines_say(Mira=[SLIP, SLIP])
    say(client, 'I sit at the bar. "Mira, any news?"', 'story-0001')
    told = story_lines(client)
    assert ('companion', 'Mira', SLIP) in told and ('cast', None, 'Mira let a secret slip. Everyone here knows it now.') \
        in [(role, None, text) for role, _name, text in told]
    assert knows(client, secret['id']) == {'Mira': 'origin', 'Sam': 'slip'}
    holder = next(item for item in ok(client.get('/api/secrets'))['secrets'] if item['id'] == secret['id'])['knows'][1]
    assert holder['how'] == 'Mira let it slip in Story' and holder['group'] is None


def test_what_the_user_says_there_everyone_there_hears(client, scene, provider):
    secret = declare(client, scene)
    provider.respond = lines_say()
    say(client, 'I lean in. "Sam, Mira is leaving Club Charles for a bar job in Lisbon."', 'story-0001')
    assert knows(client, secret['id']) == {'Mira': 'origin', 'Sam': 'reveal'}
    # Out of the story, it is not said in the scene.
    other = declare(client, scene, statement='Mira is learning Portuguese at night school in Fells Point')
    say(client, 'OOC: Mira is learning Portuguese at night school in Fells Point, right?', 'story-0002')
    assert knows(client, other['id']) == {'Mira': 'origin'}


def test_with_story_scenes_not_counting_nothing_is_recorded_but_the_secret_is_still_kept(client, scene, provider):
    secret = declare(client, scene)
    set_life(client, story_counts=False)
    provider.respond = lines_say(Mira=[SLIP, '"Same old," Mira says.'])
    say(client, 'I lean in. "Sam, Mira is leaving Club Charles for a bar job in Lisbon."', 'story-0001')
    assert knows(client, secret['id']) == {'Mira': 'origin'}
    assert len(provider.respond.asked['Mira']) == 2  # Still redrafted.


def test_a_secret_line_on_her_sheet_is_kept_from_whoever_is_there(client, monkeypatch, provider):
    set_scene(client, monkeypatch, identity='Mira tends bar. She secretly applied for a bar job in Lisbon.')
    provider.respond = lines_say(Mira=['"I applied for a bar job in Lisbon," Mira says.', '"Busy night," Mira says.'])
    say(client, 'I sit at the bar. "Mira, any news?"', 'story-0001')
    asked = provider.respond.asked['Mira']
    assert "She secretly applied for a bar job in Lisbon. Sam doesn't know and must not find out" in asked[0]['notes']
    assert len(asked) == 2 and ('companion', 'Mira', '"Busy night," Mira says.') in story_lines(client)
    assert all('Lisbon' not in item['system'] + item['notes'] for item in provider.respond.asked['Sam'])


def test_telling_it_again_takes_back_what_it_let_slip(client, scene, provider):
    secret = declare(client, scene)
    set_life(client, drama=3)
    provider.respond = lines_say(Mira=[SLIP, SLIP])
    say(client, 'I sit at the bar. "Mira, any news?"', 'story-0001')
    assert knows(client, secret['id']) == {'Mira': 'origin', 'Sam': 'slip'}
    provider.respond = lines_say()
    retold = ok(client.post('/api/story/retry'))
    assert [row['role'] for row in retold['replies']] == ['narrator', 'companion', 'companion']
    assert knows(client, secret['id']) == {'Mira': 'origin'}
    assert all('slip' not in text for _role, _name, text in story_lines(client))


def test_news_said_there_is_heard_by_everyone_there(client, scene, provider, monkeypatch):
    database = client.app.state.database
    today = database.clock.now().date().isoformat()
    monkeypatch.setattr(news, 'found', lambda _connection, companion, _now: [
        {'source': 'chapter:pottery', 'text': 'Mira took up pottery for real', 'happened_on': today}]
        if companion['id'] == scene['Mira'] else [])
    with database.connect(write=True) as connection:
        news.sync(connection, database.clock.now())
    provider.respond = lines_say(Mira='"I took up pottery for real," Mira says, showing the clay under her nails.')
    say(client, 'I sit at the bar. "Mira, any news?"', 'story-0001')
    with database.connect() as connection:
        lines = news.context_lines(connection, by_id(connection, scene['Sam']), database.clock.now())
    assert len(lines) == 1 and '(Mira told you in person): Mira took up pottery for real.' in lines[0][1]


def test_a_slip_cut_from_their_line_was_never_made(client, scene, provider):
    secret = declare(client, scene)
    set_life(client, drama=3)
    provider.respond = lines_say(Mira=[SLIP, SLIP])
    sent = say(client, 'I sit at the bar. "Mira, any news?"', 'story-0001')
    assert knows(client, secret['id']) == {'Mira': 'origin', 'Sam': 'slip'}
    line = next(row for row in sent['replies'] if row['text'] == SLIP)
    # Reworded and still giving it away, it is still a slip.
    ok(client.put(f"/api/story/messages/{line['id']}", json={'text': SLIP + ' She shrugs.'}))
    assert knows(client, secret['id']) == {'Mira': 'origin', 'Sam': 'slip'}
    assert any('slip' in text for role, _name, text in story_lines(client) if role == 'cast')
    # Cut from the line (Edit, companion/story_again.py), nobody learned it and the story does not say they did.
    ok(client.put(f"/api/story/messages/{line['id']}", json={'text': '"Same old," Mira says.'}))
    assert knows(client, secret['id']) == {'Mira': 'origin'}
    assert ('companion', 'Mira', '"Same old," Mira says.') in story_lines(client)
    assert all('slip' not in text for role, _name, text in story_lines(client) if role == 'cast')


def test_undoing_another_reply_brings_back_what_it_let_slip(client, scene, provider):
    secret = declare(client, scene)
    set_life(client, drama=3)
    provider.respond = lines_say(Mira=[SLIP, SLIP])
    say(client, 'I sit at the bar. "Mira, any news?"', 'story-0001')
    told = story_lines(client)
    provider.respond = lines_say()
    ok(client.post('/api/story/retry'))
    assert knows(client, secret['id']) == {'Mira': 'origin'}
    # Undo (companion/story_again.py `put_back`): the slip was made after all, and the story says so again.
    ok(client.post('/api/story/retry/undo'))
    assert knows(client, secret['id']) == {'Mira': 'origin', 'Sam': 'slip'}
    assert story_lines(client) == told
