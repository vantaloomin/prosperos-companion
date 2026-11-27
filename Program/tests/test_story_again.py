"""Another reply and Edit in the Story (companion/story_again.py): the replies to the latest line are told again, or
the line is said differently and answered anew, and what the old telling had done is taken back."""
import pytest
from conftest import Chunk, reconcile
from test_drafting import connect
from test_drop_by import SHIFTS
from test_social_circle import make
from test_story import busy_place, ok, say
from test_story_cast import at_work, script
from test_story_pursuit import PROFILE, someone
from test_together import mira

from companion import story_pursuit
from companion.memory.context import NOTE_CLOSE


def lines(client):
    return [(row['role'], row['text']) for row in ok(client.get('/api/story'))['messages']]


def edit(client, message_id, text):
    return client.put(f'/api/story/messages/{message_id}', json={'text': text})


def test_another_reply_tells_the_latest_reply_again_in_its_place(client, clock, provider):
    connect(client)
    provider.replies = [[Chunk('A man waves you over.'), Chunk('', 'stop')]]
    sent = say(client, 'Mh.. good evening...', 'story-0001')
    provider.replies = [[Chunk('The server nods toward the garden.'), Chunk('', 'stop')]]
    retold = ok(client.post('/api/story/retry'))
    assert retold['message']['id'] == sent['message']['id'] and retold['reply']['id'] != sent['reply']['id']
    assert lines(client) == [('user', 'Mh.. good evening...'), ('narrator', 'The server nods toward the garden.')]
    # The narrator is asked for the same line again, without the reply it gave before.
    assert provider.requests[-1]['messages'][-1]['content'].endswith(f'{NOTE_CLOSE}\nMh.. good evening...')
    assert 'met_before' not in retold['reply'] and 'met_before' not in retold['message']


def test_a_line_with_no_reply_at_all_can_be_tried_again(client, clock, provider):
    refused = client.post('/api/story/messages', json={'text': 'I look around.', 'client_id': 'story-0001'})
    assert refused.status_code == 409
    connect(client)
    provider.replies = [[Chunk('Rain on the awning.'), Chunk('', 'stop')]]
    assert ok(client.post('/api/story/retry'))['reply']['text'] == 'Rain on the awning.'


def test_editing_the_latest_line_answers_the_new_words(client, clock, provider):
    connect(client)
    provider.replies = [[Chunk('A man waves you over.'), Chunk('', 'stop')]]
    first = say(client, 'I sit down.', 'story-0001')
    provider.replies = [[Chunk('He laughs.'), Chunk('', 'stop')]]
    sent = say(client, 'Mh.. good evening...', 'story-0002')
    # Only the latest line can be changed: the story has one course.
    assert edit(client, first['message']['id'], 'I stand.').status_code == 409
    provider.replies = [[Chunk('"Evening," the server says.'), Chunk('', 'stop')]]
    edited = ok(edit(client, sent['message']['id'], 'Good evening.'))
    assert edited['message']['id'] == sent['message']['id'] and edited['message']['text'] == 'Good evening.'
    assert lines(client) == [('user', 'I sit down.'), ('narrator', 'A man waves you over.'),
                             ('user', 'Good evening.'), ('narrator', '"Evening," the server says.')]
    assert provider.requests[-1]['messages'][-1]['content'].endswith(f'{NOTE_CLOSE}\nGood evening.')
    assert edit(client, sent['message']['id'], ' ').status_code == 422


def test_once_the_story_has_gone_somewhere_else_the_line_stays_as_it_is(client, clock, provider):
    connect(client)
    provider.replies = [[Chunk('A man waves you over.'), Chunk('', 'stop')]]
    sent = say(client, 'I sit down.', 'story-0001')
    place = next(item for item in ok(client.get('/api/story'))['scene']['places']
                 if item['id'] != sent['message']['place_id'])
    ok(client.put('/api/story/scene', json={'city_id': 'baltimore', 'place_id': place['id']}))
    before = lines(client)
    assert client.post('/api/story/retry').status_code == 409
    assert edit(client, sent['message']['id'], 'I stand.').status_code == 409
    assert lines(client) == before


def test_telling_it_again_forgets_who_the_old_reply_introduced(client, clock, provider):
    make(client, 'Warm and curious.')
    connect(client)
    place, people = busy_place(client, clock)
    ok(client.put('/api/story/scene', json={'city_id': 'baltimore', 'place_id': place['id']}))
    them = people[0]['sheet']
    provider.replies = [[Chunk(f'"I\'m {them["name"]}," they say, wiping the counter.'), Chunk('', 'stop')]]
    say(client, 'I say hello.', 'story-0001')
    assert [item['key'] for item in ok(client.get('/api/story'))['people']] == [them['key']]
    # Told again without the name: they are a stranger again, to the screen and to the narrator.
    provider.replies = [[Chunk('Nobody looks up.'), Chunk('', 'stop')]]
    ok(client.post('/api/story/retry'))
    assert ok(client.get('/api/story'))['people'] == []
    assert 'The user has met them' not in provider.requests[-1]['system']
    # Someone met before keeps that meeting; only the sentences of the retold reply go.
    provider.replies = [[Chunk(f'"{them["name"]}," they say at last.'), Chunk('', 'stop')]]
    say(client, 'I ask their name.', 'story-0002')
    provider.replies = [[Chunk(f'{them["name"]} spills the tea.'), Chunk('', 'stop')]]
    say(client, 'I wave.', 'story-0003')
    assert len(ok(client.get('/api/story'))['people'][0]['notes']) == 2
    provider.replies = [[Chunk('The kettle sings.'), Chunk('', 'stop')]]
    ok(client.post('/api/story/retry'))
    [met] = ok(client.get('/api/story'))['people']
    assert met['meetings'] == 1 and met['notes'] == [f'"{them["name"]}," they say at last.']


def test_a_yes_told_again_is_said_again_and_an_ask_edited_away_is_no_match(client, clock, provider):
    make(client, 'Warm and curious.')
    connect(client)
    ok(client.put('/api/dating/profile', json=PROFILE))
    sheet = someone(client, clock, 'yes')
    name = sheet['name']
    provider.replies = [[Chunk(f'{name} grins. "I would like that."'), Chunk('', 'stop')]]
    asked = say(client, f'{name}, would you go out with me?', 'story-0001')
    assert asked['replies'][1]['text'] == f'{name} said yes.'
    provider.replies = [[Chunk(f'{name} laughs. "Yes. Yes, I would."'), Chunk('', 'stop')]]
    retold = ok(client.post('/api/story/retry'))
    # Their rules answer the same way: the narrator is told yes again, not that it was said before.
    assert provider.requests[-1]['messages'][-1]['content'].endswith(story_pursuit.NOTES['yes'].format(
        name=sheet['full'], first=name, status=''))
    assert [row['text'] for row in retold['replies']] == [f'{name} laughs. "Yes. Yes, I would."', f'{name} said yes.']
    with client.app.state.database.connect() as connection:
        assert story_pursuit.matched(connection, sheet['key'])
    # Said differently, with no ask in it, nobody said yes.
    provider.replies = [[Chunk(f'{name} nods.'), Chunk('', 'stop')]]
    edited = ok(edit(client, asked['message']['id'], f'{name}, a coffee please.'))
    assert [row['role'] for row in edited['replies']] == ['narrator']
    with client.app.state.database.connect() as connection:
        assert not story_pursuit.matched(connection, sheet['key'])


@pytest.fixture
def barkeep(client, monkeypatch):
    mira(client, monkeypatch, schedule=SHIFTS)
    reconcile(client)
    assert client.put('/api/settings', json={'automatic_memory': True}).status_code == 200


def self_facts(client):
    return {(fact['subject'], fact['value']) for fact in ok(client.get('/api/self-facts'))['facts']}


def visit(client):
    with client.app.state.database.connect() as connection:
        return dict(connection.execute('SELECT said, last_seq FROM story_visits').fetchone())


def test_with_a_companion_there_both_lines_are_told_again_and_hers_leaves_nothing_behind(client, barkeep, provider):
    at_work(client)
    script(provider, 'The bar hums quietly.', 'Mira wipes the bar. "My cousin Theo came by."')
    sent = say(client, '"How was your weekend, Mira?"', 'again-0001')
    assert ('cousin', 'Theo') in self_facts(client) and visit(client)['said'] == 1
    script(provider, 'The jukebox clicks over.', 'Mira shrugs. "Quiet."')
    retold = ok(client.post('/api/story/retry'))
    assert [(row['role'], row['text']) for row in retold['replies']] == [
        ('narrator', 'The jukebox clicks over.'), ('companion', 'Mira shrugs. "Quiet."')]
    # What she said about herself in the reply told before is not on record.
    assert ('cousin', 'Theo') not in self_facts(client)

    # Her line said differently: she hears the new words, and the time together counts the line once.
    script(provider, 'The bar hums quietly.', 'Mira looks up. "Denver? Nice."')
    edited = ok(edit(client, sent['message']['id'], '"My sister Ashley just moved to Denver," I tell Mira.'))
    assert [row['role'] for row in edited['replies']] == ['narrator', 'companion']
    mira_request = next(request for request in reversed(provider.requests) if 'The scene so far' in request['system'])
    said = mira_request['system'] + mira_request['messages'][-1]['content']
    assert 'Ashley just moved to Denver' in said and 'How was your weekend' not in said
    assert visit(client)['said'] == 1
    memories = {(memory['subject'], memory['value']) for memory in ok(client.get('/api/memories'))}
    assert ('Sister', 'Ashley') in memories


def test_the_narrators_reply_can_be_reworded_and_the_story_goes_on_from_it(client, clock, provider):
    """Vanta, 1.5.0: someone across the room remarked on a name she had shown only to the server. Cutting his
    lines from the reply takes them out of the story and out of what is kept about him."""
    make(client, 'Warm and curious.')
    connect(client)
    place, people = busy_place(client, clock)
    ok(client.put('/api/story/scene', json={'city_id': 'baltimore', 'place_id': place['id']}))
    name = people[0]['sheet']['name']
    provider.replies = [[Chunk(f'"I\'m {name}," they say. "Sit anywhere."'), Chunk('', 'stop')]]
    first = say(client, 'I say hello.', 'story-0001')
    kept = f'The server reads the note. {name} keeps wiping the counter.'
    told = f'{kept} {name} murmurs, "The Boss drinks tea?"'
    provider.replies = [[Chunk(told), Chunk('', 'stop')]]
    sent = say(client, 'I show the server a note, careful to let nobody else see it.', 'story-0002')
    assert any('The Boss' in note for note in ok(client.get('/api/story'))['people'][0]['notes'])

    edited = ok(edit(client, sent['reply']['id'], kept))
    assert edited['message']['text'] == kept and edited['message']['id'] == sent['reply']['id']
    now = ok(client.get('/api/story'))
    assert [row['text'] for row in now['messages']][-1] == kept and len(now['messages']) == 5
    assert now['people'][0]['notes'] == [f'"I\'m {name}," they say.', f'{name} keeps wiping the counter.']
    # The next reply is written from the new wording, and nothing of what was cut is remembered of them.
    provider.replies = [[Chunk('The kettle sings.'), Chunk('', 'stop')]]
    say(client, 'I wait.', 'story-0003')
    request = provider.requests[-1]
    assert 'The Boss' not in request['system'] + ' '.join(message['content'] for message in request['messages'])
    assert kept in request['messages'][-2]['content']
    # An earlier reply can be reworded too; a line that is not a reply cannot, and neither can one that is gone.
    assert ok(edit(client, first['reply']['id'], 'They nod.'))['message']['text'] == 'They nod.'
    assert ok(client.get('/api/story'))['people'][0]['notes'] == [f'{name} keeps wiping the counter.']
    arrival = next(row for row in now['messages'] if row['role'] == 'scene')
    assert edit(client, arrival['id'], 'You arrive somewhere else.').status_code == 409
    assert edit(client, 'no-such-line', 'Anything.').status_code == 404


def test_a_companions_line_reworded_is_what_they_said(client, barkeep, provider):
    at_work(client)
    script(provider, 'The bar hums quietly.', 'Mira wipes the bar. "My cousin Theo came by."')
    sent = say(client, '"How was your weekend, Mira?"', 'again-0001')
    assert ('cousin', 'Theo') in self_facts(client)
    line = sent['replies'][1]
    edited = ok(edit(client, line['id'], 'Mira wipes the bar. "Quiet. I hate cilantro, so I cooked."'))
    assert edited['message']['speaker'] == line['speaker'] and 'cilantro' in edited['message']['text']
    assert ('cousin', 'Theo') not in self_facts(client) and ('cilantro', 'cilantro') in self_facts(client)
    # Nothing was written again: the narrator's reply and her line are the ones there were.
    assert [row['id'] for row in ok(client.get('/api/story'))['messages'] if row['reply_to']] == \
        [row['id'] for row in sent['replies']]


# Undo on Another reply ------------------------------------------------------------------------------------

def undo(client):
    return client.post('/api/story/retry/undo')


def test_another_reply_can_be_undone_once_until_the_next_line(client, clock, provider):
    connect(client)
    provider.replies = [[Chunk('A man waves you over.'), Chunk('', 'stop')]]
    sent = say(client, 'Mh.. good evening...', 'story-0001')
    assert sent['message']['undo'] is False and undo(client).status_code == 409
    provider.replies = [[Chunk('The server nods toward the garden.'), Chunk('', 'stop')]]
    retold = ok(client.post('/api/story/retry'))
    assert retold['message']['undo'] is True and 'told_before' not in retold['message']
    assert ok(client.get('/api/story'))['messages'][0]['undo'] is True
    # The reply told before is back as it was, in place of the one told since, and nothing is written.
    asked = len(provider.requests)
    back = ok(undo(client))
    assert back['reply']['id'] == sent['reply']['id'] and back['message']['undo'] is False
    assert lines(client) == [('user', 'Mh.. good evening...'), ('narrator', 'A man waves you over.')]
    assert len(provider.requests) == asked and undo(client).status_code == 409
    # One step back: of two retellings, Undo brings back the one before the last.
    for text in ('The kettle sings.', 'Rain starts.'):
        provider.replies = [[Chunk(text), Chunk('', 'stop')]]
        ok(client.post('/api/story/retry'))
    assert ok(undo(client))['reply']['text'] == 'The kettle sings.'
    # Once the next line is sent there is nothing to undo; nor after the line is said differently.
    provider.replies = [[Chunk('Rain starts.'), Chunk('', 'stop')]]
    ok(client.post('/api/story/retry'))
    provider.replies = [[Chunk('He nods.'), Chunk('', 'stop')]]
    edited = ok(edit(client, sent['message']['id'], 'Good evening.'))
    assert edited['message']['undo'] is False and undo(client).status_code == 409
    ok(client.post('/api/story/retry'))
    say(client, 'I sit down.', 'story-0002')
    assert undo(client).status_code == 409
    assert all(row['undo'] is False for row in ok(client.get('/api/story'))['messages'])


def test_a_retelling_that_failed_can_be_undone(client, clock, provider):
    connect(client)
    provider.replies = [[Chunk('A man waves you over.'), Chunk('', 'stop')]]
    say(client, 'Mh.. good evening...', 'story-0001')
    provider.replies = [[Chunk('', 'stop')]]
    assert ok(client.post('/api/story/retry'))['reply']['status'] == 'failed'
    assert ok(undo(client))['reply']['text'] == 'A man waves you over.'
    assert lines(client) == [('user', 'Mh.. good evening...'), ('narrator', 'A man waves you over.')]


def test_undo_brings_back_who_the_old_reply_introduced(client, clock, provider):
    make(client, 'Warm and curious.')
    connect(client)
    place, people = busy_place(client, clock)
    ok(client.put('/api/story/scene', json={'city_id': 'baltimore', 'place_id': place['id']}))
    them = people[0]['sheet']
    provider.replies = [[Chunk(f'"I\'m {them["name"]}," they say, wiping the counter.'), Chunk('', 'stop')]]
    say(client, 'I say hello.', 'story-0001')
    [met] = ok(client.get('/api/story'))['people']
    provider.replies = [[Chunk('Nobody looks up.'), Chunk('', 'stop')]]
    ok(client.post('/api/story/retry'))
    assert ok(client.get('/api/story'))['people'] == []
    ok(undo(client))
    assert ok(client.get('/api/story'))['people'] == [met]
    # And it can be told again from there, as before.
    provider.replies = [[Chunk('Nobody looks up.'), Chunk('', 'stop')]]
    ok(client.post('/api/story/retry'))
    assert ok(client.get('/api/story'))['people'] == []


def test_undo_brings_back_a_yes(client, clock, provider):
    make(client, 'Warm and curious.')
    connect(client)
    ok(client.put('/api/dating/profile', json=PROFILE))
    sheet = someone(client, clock, 'yes')
    name = sheet['name']
    provider.replies = [[Chunk(f'{name} grins. "I would like that."'), Chunk('', 'stop')]]
    asked = say(client, f'{name}, would you go out with me?', 'story-0001')
    provider.replies = [[Chunk('', 'stop')]]
    assert ok(client.post('/api/story/retry'))['reply']['status'] == 'failed'
    with client.app.state.database.connect() as connection:
        assert not story_pursuit.matched(connection, sheet['key'])
    back = ok(undo(client))
    assert [row['text'] for row in back['replies']] == [row['text'] for row in asked['replies']]
    with client.app.state.database.connect() as connection:
        assert story_pursuit.matched(connection, sheet['key'])


def test_undo_brings_back_what_a_companion_said_about_themselves(client, barkeep, provider):
    at_work(client)
    script(provider, 'The bar hums quietly.', 'Mira wipes the bar. "My cousin Theo came by."')
    sent = say(client, '"How was your weekend, Mira?"', 'again-0001')
    script(provider, 'The jukebox clicks over.', 'Mira shrugs. "My brother Sol called."')
    ok(client.post('/api/story/retry'))
    assert ('cousin', 'Theo') not in self_facts(client) and ('brother', 'Sol') in self_facts(client)
    back = ok(undo(client))
    assert [row['id'] for row in back['replies']] == [row['id'] for row in sent['replies']]
    assert ('cousin', 'Theo') in self_facts(client) and ('brother', 'Sol') not in self_facts(client)


def test_a_chapter_started_before_a_retelling_still_begins_with_the_next_line(client, clock, provider):
    connect(client)
    provider.replies = [[Chunk('A man waves you over.'), Chunk('', 'stop')]]
    say(client, 'Mh.. good evening...', 'story-0001')
    ok(client.post('/api/story/chapter'))
    # Told again, and the new reply never comes: the story is shorter than when the chapter was started.
    provider.replies = [[Chunk('', 'stop')]]
    assert ok(client.post('/api/story/retry'))['reply']['status'] == 'failed'
    assert ok(client.get('/api/story'))['next_chapter']['by'] == 'asked'
    ok(undo(client))
    provider.replies = [[Chunk('The kettle sings.'), Chunk('', 'stop')]]
    ok(client.post('/api/story/retry'))
    provider.replies = [[Chunk('He pours.'), Chunk('', 'stop')]]
    say(client, 'I sit down.', 'story-0002')
    opened = ok(client.get('/api/story'))
    assert [line['chapter'] for line in opened['messages']] == [1, 1, 2, 2] and opened['next_chapter'] is None
