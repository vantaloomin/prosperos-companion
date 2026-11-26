"""Companions in the Story's scene (companion/story_cast.py): there when the story is where their day has them,
speaking in their own lines after the narrator's."""
from datetime import timedelta

import pytest
from conftest import Chunk, reconcile, send
from test_drop_by import SHIFTS
from test_story import ok, say
from test_together import mira

from companion import story_cast


@pytest.fixture
def barkeep(client, monkeypatch):
    """Mira works a shift at Club Charles, 09:00 to 17:00; the clock starts on Monday at noon."""
    mira(client, monkeypatch, schedule=SHIFTS)
    reconcile(client)


def script(provider, *texts):
    provider.replies = [[Chunk(text), Chunk('', 'stop')] for text in texts]


def at_work(client):
    return ok(client.put('/api/story/scene', json={'city_id': 'baltimore', 'place_id': 'club-charles'}))


def lines(client):
    return [(row['role'], row['text']) for row in ok(client.get('/api/story'))['messages']]


def test_a_companion_at_work_is_in_the_scene_and_answers_for_themself(client, barkeep, provider):
    opened = ok(client.get('/api/story'))
    found = opened['companions'][0]
    assert (found['name'], found['main'], found['here'], found['place']['id']) == ('Mira', True, False, 'club-charles')
    moved = at_work(client)
    assert moved['scene']['around'][0] == 'Mira' and moved['scene']['companions'][0]['name'] == 'Mira'
    assert moved['companions'][0]['here'] is True
    assert [(row['role'], row['text']) for row in moved['messages'][-2:]] == [
        ('scene', 'You arrive at Club Charles, Station North, Baltimore.'), ('cast', 'Mira is here.')]

    script(provider, 'The bar is dim and nearly empty.', 'Mira looks up from the taps. "You came."')
    sent = say(client, 'I look around.', 'story-0001')
    assert [(row['role'], row['name']) for row in sent['replies']] == [('narrator', None), ('companion', 'Mira')]
    assert sent['reply']['role'] == 'narrator' and sent['replies'][1]['text'] == 'Mira looks up from the taps. "You came."'

    narrator, own = provider.requests[-2], provider.requests[-1]
    # The narrator is told she speaks for herself, in the scene and again after the user's line.
    assert 'Mira speaks and acts for' in narrator['system'] and 'keep your part short' in narrator['system']
    assert narrator['messages'][-1]['content'].endswith(
        '[Mira will answer in their own words right after you. Write nothing Mira says or does: leave that to them.]')
    # Her own request: the scene rules, the scene, the story since she was in it, then who she is.
    assert own['system'].startswith('This is a scene in a story the user is living in person.')
    assert 'Place: Club Charles, a bar in Station North, Baltimore.' in own['system']
    assert '## The scene so far\nUser: I look around.\nNarrator: The bar is dim and nearly empty.' in own['system']
    assert 'You are Mira. For this whole conversation you are Mira' in own['system']
    assert 'Pictures: you send one only' not in own['system']  # In person, nobody texts.
    notes = own['messages'][-1]['content']
    assert 'You are Mira, in person with the user at Club Charles. You are at work here.' in notes
    assert 'You were here first. The user has come in' in notes
    assert notes.endswith("Write Mira's next turn in the scene: only what Mira says and does, with no name in front.")

    # The next line: the narrator reads her line under her name, on the user's side.
    script(provider, 'Rain ticks on the window.', '"Long," Mira says.')
    say(client, 'How was the shift?', 'story-0002')
    told = provider.requests[-2]['messages']
    assert '[Mira, in their own words:]\nMira looks up from the taps. "You came."' in told[-1]['content']
    assert 'Mira: Mira looks up from the taps. "You came."' in provider.requests[-1]['system']


def test_asleep_or_at_home_they_are_not_in_the_story(client, barkeep, provider, clock):
    clock.instant = clock.now() + timedelta(hours=13)  # 01:00: asleep.
    moved = at_work(client)
    assert 'Mira' not in moved['scene']['around'] and moved['scene']['companions'] == []
    found = moved['companions'][0]
    assert found['here'] is False and found['place'] is None
    script(provider, 'The bar is dim.')
    assert [row['role'] for row in say(client, 'I look around.', 'story-0001')['replies']] == ['narrator']
    refused = client.post('/api/story/find', json={'key': found['key']})
    assert refused.status_code == 409 and "Mira isn't anywhere you can go right now" in refused.text


def test_finding_a_companion_goes_to_where_their_day_has_them(client, barkeep):
    opened = ok(client.get('/api/story'))
    assert opened['scene']['place']['id'] != 'club-charles'
    found = ok(client.post('/api/story/find', json={'key': opened['companions'][0]['key']}))
    assert found['scene']['place']['id'] == 'club-charles' and found['messages'][-1]['text'] == 'Mira is here.'


def test_they_read_the_story_only_from_when_they_were_in_it_and_so_does_their_chat(client, barkeep, provider):
    script(provider, 'The cafe is quiet.')
    say(client, 'I tell the barista the secret password is wuzzle.', 'story-0001')
    at_work(client)
    script(provider, 'The bar is dim.', '"Hey, you."')
    say(client, 'I sit at the bar.', 'story-0002')
    own = provider.requests[-1]
    assert 'wuzzle' not in own['system'] and 'wuzzle' not in own['messages'][-1]['content']
    assert 'User: I sit at the bar.' in own['system']
    # Their chat knows the time they spent together (companion/story_visits.py), never what was said before they came.
    script(provider, 'hi!')
    send(client, 'Hi Mira!', 'client-0001')
    chat = provider.requests[-1]
    told = chat['system'] + ''.join(item['content'] for item in chat['messages'])
    assert 'The user: I sit at the bar.' in told and 'wuzzle' not in told


def test_a_line_for_someone_else_or_out_of_the_story_is_not_theirs_to_answer(client, barkeep, provider):
    at_work(client)
    person = {'sheet': {'full': 'Dana Kim', 'name': 'Dana'}}
    cast = [{'id': '1', 'name': 'Mira', 'full': 'Mira Santos'}, {'id': '2', 'name': 'Sol', 'full': 'Sol Vega'}]
    assert story_cast.speakers(cast, [person], 'Dana, could I get the bill?') == []
    assert story_cast.speakers(cast, [person], 'I look around.') == cast
    assert story_cast.speakers(cast, [person], 'Dana, this is Sol.') == [cast[1], cast[0]]  # Whoever is named first.
    script(provider, "I'm the model writing the narrator.")
    honest = say(client, 'OOC: who writes Mira?', 'story-0001')
    assert [row['role'] for row in honest['replies']] == ['narrator']


def test_they_go_when_their_day_moves_on_but_not_in_the_middle_of_talking(client, barkeep, provider, clock):
    at_work(client)
    script(provider, 'The bar is dim.', '"You came."')
    say(client, 'I look around.', 'story-0001')
    clock.instant = clock.now() + timedelta(hours=5, minutes=20)  # 17:20: the shift is over, the talk is not fresh.
    assert ok(client.get('/api/story'))['scene']['companions'] == []
    script(provider, 'The stools are empty.')
    sent = say(client, 'I finish my drink.', 'story-0002')
    assert [row['role'] for row in sent['replies']] == ['narrator']
    assert lines(client)[-3:-1] == [('cast', 'Mira has gone.'), ('user', 'I finish my drink.')]


def test_someone_the_user_is_talking_with_stays_a_little_past_their_shift(client, barkeep, provider, clock):
    at_work(client)
    clock.instant = clock.now() + timedelta(hours=4, minutes=50)  # 16:50, ten minutes before the shift ends.
    script(provider, 'The bar is dim.', '"You came."')
    say(client, 'I look around.', 'story-0001')
    clock.instant = clock.now() + timedelta(minutes=20)  # 17:10.
    assert ok(client.get('/api/story'))['scene']['companions'][0]['name'] == 'Mira'
    script(provider, 'Chairs go up on the tables.', '"Walk me out?"')
    assert [row['role'] for row in say(client, 'I wait for her.', 'story-0002')['replies']] == ['narrator', 'companion']
    assert ('cast', 'Mira has gone.') not in lines(client)


def test_trying_again_keeps_what_was_written_and_telling_again_replaces_it_all(client, barkeep, provider):
    at_work(client)
    script(provider, 'The bar is dim.', '')
    failed = say(client, 'I look around.', 'story-0001')
    assert [(row['role'], row['status']) for row in failed['replies']] == [('narrator', 'complete'), ('companion', 'failed')]
    count = len(provider.requests)
    script(provider, '"You came."')
    again = ok(client.post('/api/story/retry'))
    assert len(provider.requests) == count + 1  # Only her line was written again.
    assert [(row['role'], row['text']) for row in again['replies']] == [
        ('narrator', 'The bar is dim.'), ('companion', '"You came."')]
    # Sending the same line again asks nobody: both replies are there.
    assert say(client, 'I look around.', 'story-0001')['replies'] == again['replies']
    assert len(provider.requests) == count + 1
    # With nothing failed, Try again tells the whole reply anew.
    script(provider, 'Neon hums over the door.', '"Well, look who it is."')
    retold = ok(client.post('/api/story/retry'))
    assert [row['text'] for row in retold['replies']] == ['Neon hums over the door.', '"Well, look who it is."']
    assert [role for role, _text in lines(client)] == ['scene', 'cast', 'user', 'narrator', 'companion']


def test_their_line_is_their_own_turn_said_out_loud(client, barkeep, provider):
    at_work(client)
    script(provider, 'The bar is dim.', '**Mira:** "you came. sit."\n\nUser: I sit down.\n\nNarrator: The stool creaks.')
    sent = say(client, 'I look around.', 'story-0001')
    assert sent['replies'][1]['text'] == '"You came. Sit."'


def test_a_new_story_and_going_elsewhere_leave_them_behind(client, barkeep, provider):
    at_work(client)
    moved = ok(client.put('/api/story/scene', json={'city_id': 'new-york'}))
    assert moved['scene']['companions'] == [] and moved['messages'][-1]['role'] == 'scene'
    at_work(client)
    cleared = ok(client.delete('/api/story'))
    assert cleared['messages'] == []
    with client.app.state.database.connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM story_cast').fetchone()[0] == 0
    # Still at the bar: she is in the scene again with the first line of the new story.
    script(provider, 'The bar is dim.', '"Back already?"')
    say(client, 'I look around.', 'story-0001')
    assert lines(client)[0] == ('cast', 'Mira is here.')


def test_the_story_export_has_their_lines_under_their_name(client, barkeep, provider):
    at_work(client)
    script(provider, 'The bar is dim.', 'Mira looks up. "You came."')
    say(client, 'I look around.', 'story-0001')
    exported = client.get('/api/export/story', params={'format': 'md'})
    assert exported.status_code == 200, exported.text
    assert 'Mira looks up. "You came."' in exported.text and 'Mira is here.' in exported.text


def test_a_companion_comes_home_with_the_user_unless_the_line_says_they_part(client, barkeep, provider):
    at_work(client)
    script(provider, 'The bar is dim and nearly empty.', 'Mira looks up from the taps. "You came."')
    say(client, 'I look around.', 'story-0001')
    # Walking home in the middle of talking with her: she comes along, and is told whose home it is.
    script(provider, 'The two of you step out into the evening.', '"Lead the way," Mira says.')
    say(client, 'Mira and I walk back to my place.', 'story-0002')
    scene = ok(client.get('/api/story'))['scene']
    assert scene['place']['home'] and scene['around'] == ['Mira']
    narrator, own = provider.requests[-2], provider.requests[-1]
    assert "Place: The user's own home, in" in narrator['system'] and 'Mira speaks and acts for' in narrator['system']
    assert "Place: The user's own home, in" in own['system'] and 'at Your home' not in own['messages'][-1]['content']
    assert "You are Mira, in person with the user at the user's own home." in own['messages'][-1]['content']
    # Back at the bar, a line that says goodnight and walks home leaves her there: only the narrator answers.
    at_work(client)
    script(provider, 'Mira nods from behind the bar.', '"Back so soon?"')
    say(client, 'I sit at the bar.', 'story-0003')
    before = len(provider.requests)
    script(provider, 'The street is quiet on your way back.')
    sent = say(client, '"Goodnight, Mira." I walk home.', 'story-0004')
    assert [row['role'] for row in sent['replies']] == ['narrator'] and len(provider.requests) == before + 1
    scene = ok(client.get('/api/story'))['scene']
    assert scene['place']['home'] and scene['around'] == [] and 'Mira speaks' not in provider.requests[-1]['system']
