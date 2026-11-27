"""A Story reply the service stopped at the reply limit (companion/story_cut.py): trimmed to its last full sentence,
kept in the story, and marked while it is the newest."""
from conftest import Chunk
from test_drafting import connect
from test_story import ok, say

from companion import story_cut


def test_a_cut_reply_ends_at_its_last_full_sentence():
    assert story_cut.trimmed('The room goes quiet. To the room, she says, in') == 'The room goes quiet.'
    assert story_cut.trimmed('He grins. "Sit down, then." She does not move an') == 'He grins. "Sit down, then."'
    assert story_cut.trimmed('Rain on the awning…  The server') == 'Rain on the awning…'
    assert story_cut.trimmed('*She laughs.* Then she') == '*She laughs.*'
    # A reply that happens to end on a sentence is whole as it is.
    assert story_cut.trimmed('He laughs. "Evening."') == 'He laughs. "Evening."'
    # "Mr." ends no sentence, and with no full sentence to keep the reply stays as it is.
    assert story_cut.trimmed('The door opens. She turns to Mr. Tanaka and') == 'The door opens.'
    assert story_cut.trimmed('To the room, she says, in') == 'To the room, she says, in'


def test_a_quote_the_cut_leaves_open_is_closed():
    assert story_cut.trimmed('She leans in. "I told you already. I never said') == 'She leans in. "I told you already."'
    assert story_cut.trimmed('“You came back. I did not think you') == '“You came back.”'
    # A quote closed in an earlier paragraph says nothing about the last one.
    assert story_cut.trimmed('"Evening," he says.\n\nThe lamps are lit. Somewhere a') == \
        '"Evening," he says.\n\nThe lamps are lit.'


def test_the_story_keeps_a_cut_reply_trimmed_and_says_it_was_cut(client, clock, provider):
    connect(client)
    provider.replies = [[Chunk('A man waves you over. To the room, he says, in'), Chunk('', 'length')]]
    sent = say(client, 'Good evening.', 'story-0001')
    assert sent['reply']['status'] == 'complete' and sent['reply']['text'] == 'A man waves you over.'
    assert sent['reply']['cut'] is True and sent['message']['cut'] is False
    told = ok(client.get('/api/story'))['messages'][-1]
    assert told['text'] == 'A man waves you over.' and told['cut'] is True
    # In the user's own wording it is whole; a reply that ended by itself was never cut.
    edited = ok(client.put(f"/api/story/messages/{told['id']}", json={'text': 'A man waves you over and bows.'}))
    assert edited['message']['cut'] is False
    provider.replies = [[Chunk('The server nods toward the garden.'), Chunk('', 'stop')]]
    assert ok(client.post('/api/story/retry'))['reply']['cut'] is False
