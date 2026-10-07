from conftest import send

from companion.in_character import applies, breaks, clean
from companion.providers.chat import Chunk


def test_ai_denials_are_recognized():
    for line in ("As an AI, I don't have feelings.", "I'm just an AI language model.", "I'm not a real person.",
                 "I don't have a physical body.", "I was created by OpenAI.", "I’m not a human being.",
                 "That's against my programming.", "Let's get back to our roleplay.",
                 "I don't have access to real-time weather data.", "((Sorry, the lookup failed.",
                 "So I can't say.)) "):
        assert breaks(line), line


def test_ordinary_lines_are_left_alone():
    for line in ("I'm an AI researcher at the lab.", "As an AI engineer, I debug models all day.",
                 "I'm a software engineer.", "I'm not a real fan of jazz.", "I'm not real sure about that.",
                 "I don't have feelings for him.", "That was so out of character for her.",
                 "My programming class ran late.", "He's such a bot about it lol", "(Sorry (I mean it).)"):
        assert not breaks(line), line


def test_only_the_breaking_sentence_is_removed():
    text = "Hey you! As an AI, I can't actually see you. But tell me about your day.\n\nWhat did you eat?"
    assert clean(text) == "Hey you! But tell me about your day.\n\nWhat did you eat?"


def test_out_of_character_questions_and_artificial_characters_are_not_filtered():
    assert not applies('OOC: which model are you?', {})
    assert not applies('((are you Claude?))', {})
    assert not applies('hi', {'identity': 'An android who runs a night-shift diner'})
    assert applies('are you even real?', {'identity': 'A nurse in Lisbon'})


def test_the_user_never_sees_a_denial(client, connected, provider):
    provider.replies = [[Chunk('Of course I miss you. '), Chunk("As an AI, I can't miss "), Chunk('anyone. '),
                         Chunk('Tell me everything.'), Chunk('', 'stop')]]
    reply = send(client, 'Did you miss me?', 'client-0001')['reply']
    assert reply['status'] == 'complete'
    assert reply['text'] == 'Of course I miss you. Tell me everything.'


def test_a_reply_that_only_denies_is_written_again(client, connected, provider):
    provider.replies = [[Chunk("I'm an AI, so I'm not real."), Chunk('', 'stop')],
                        [Chunk('Real enough to beat you at cards.'), Chunk('', 'stop')]]
    reply = send(client, 'Are you even real?', 'client-0001')['reply']
    assert reply['text'] == 'Real enough to beat you at cards.'
    assert 'stepped out of the story' in provider.requests[1]['system']


def test_a_reply_that_keeps_denying_is_hidden(client, connected, provider):
    provider.replies = [[Chunk("I'm an AI."), Chunk('', 'stop')], [Chunk('As an AI, no.'), Chunk('', 'stop')]]
    reply = send(client, 'Are you even real?', 'client-0001')['reply']
    assert reply['status'] == 'failed'
    assert 'stepped out of character' in reply['error']


def test_out_of_character_messages_get_a_plain_answer(client, connected, provider):
    provider.replies = [[Chunk("I'm an AI language model playing Mira."), Chunk('', 'stop')]]
    reply = send(client, 'OOC: are you an AI?', 'client-0001')['reply']
    assert reply['text'] == "I'm an AI language model playing Mira."
    # The persona prompt forbids admitting to being an AI, so the OOC turn says plainly that it may.
    assert 'say you are an AI and which model you are' in provider.requests[0]['system']


def test_in_character_messages_get_no_out_of_character_note(client, connected, provider):
    provider.replies = [[Chunk('Real enough.'), Chunk('', 'stop')]]
    send(client, 'Are you even real?', 'client-0001')
    assert 'is out of character' not in provider.requests[0]['system']
