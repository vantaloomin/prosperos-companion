"""They can ask to remember more (companion/memory/look_back.py): a wider search, and one hidden recall request."""
import json

import pytest
from conftest import send
from test_memory import remember

from companion.memory import look_back
from companion.providers.chat import Chunk


@pytest.fixture(autouse=True)
def fresh_rates(monkeypatch):
    monkeypatch.setattr(look_back, 'RATES', look_back.Rates())


def feed(lookout, *pieces) -> str:
    return ''.join(lookout.feed(piece) for piece in pieces) + lookout.flush()


def test_ordinary_replies_pass_at_once():
    lookout = look_back.Lookout()
    assert lookout.feed('Hey you') == 'Hey you' and lookout.feed('!') == '!'
    assert feed(look_back.Lookout(), '[[', 'brb]]') == '[[brb]]'
    assert lookout.query is None


def test_a_request_is_caught_across_pieces_and_never_shown():
    lookout = look_back.Lookout()
    assert feed(lookout, ' [[re', 'call: the ferry', ' trip]]', 'ignored') == ''
    assert lookout.query == 'the ferry trip'


def test_the_second_try_only_drops_a_request():
    assert feed(look_back.Lookout(strip=True), '[[recall: again]] ', 'Oh, the ferry!') == 'Oh, the ferry!'
    assert feed(look_back.Lookout(strip=True), '[[recall: never closes', ' ' * 300) == '[[recall: never closes' + \
        ' ' * 300


def test_a_reply_cut_off_inside_a_request_never_shows_it():
    lookout = look_back.Lookout()
    assert feed(lookout, '[[recall: the ferry ', 'trip to Annapolis') == ''
    assert lookout.query == 'the ferry trip to Annapolis'
    assert feed(look_back.Lookout(), 'Sure, love. ', '[[recall: the fer') == 'Sure, love. '
    assert feed(look_back.Lookout(strip=True), 'Oh! [[Recall: zoo') == 'Oh! '


def test_only_messages_that_point_back_get_the_offer():
    assert look_back.points_back('Do you remember the ferry?') and look_back.points_back('Last summer was fun')
    assert not look_back.points_back('What are you doing tonight?')


def test_she_looks_again_and_answers(client, connected, provider):
    remember(client, layer='shared_experience', subject='Ferry trip', value='Took the ferry to Annapolis in June')
    replies = [[Chunk('[[recall: '), Chunk('Annapolis ferry]]'), Chunk('', 'stop')],
               [Chunk('Oh, Annapolis! The wind was wild.'), Chunk('', 'stop')]]
    provider.replies = replies
    result = send(client, 'Do you remember that boat thing we did?', 'client-look-back')
    assert result['reply']['text'] == 'Oh, Annapolis! The wind was wild.'
    assert len(provider.requests) == 2
    assert look_back.ASK.split('.')[0] in provider.requests[0]['prompt']
    second = provider.requests[1]['prompt']
    assert 'You asked to remember more about «Annapolis ferry»' in second and look_back.ASK not in second


def test_nothing_found_still_gets_an_answer(client, connected, provider):
    provider.replies = [[Chunk('[[recall: the zeppelin]]'), Chunk('', 'stop')],
                        [Chunk("Hmm, I don't remember that one."), Chunk('', 'stop')]]
    result = send(client, 'Remember the zeppelin?', 'client-look-nothing')
    assert result['reply']['text'] == "Hmm, I don't remember that one."
    assert 'nothing more was found' in provider.requests[1]['prompt']


def test_switched_off_she_is_never_offered_it(client, connected, provider):
    assert client.put('/api/settings', json={'recall_more': False}).status_code == 200
    send(client, 'Do you remember the ferry?', 'client-look-off')
    assert len(provider.requests) == 1 and look_back.ASK not in provider.requests[0]['prompt']


def test_a_thin_recall_widens_with_recent_messages(client, connected, provider):
    remember(client, layer='shared_experience', subject='Ferry trip', value='Took the ferry to Annapolis in June')
    send(client, 'I was thinking about Annapolis today', 'client-widen-1')
    reply = send(client, 'Do you remember that?', 'client-widen-2')['reply']
    assert 'Ferry trip: Took the ferry to Annapolis' in provider.requests[-1]['prompt']
    with client.app.state.database.connect() as connection:
        receipt = connection.execute('SELECT receipt FROM messages WHERE id=?', (reply['id'],)).fetchone()[0]
    assert json.loads(receipt)['widened_recall'] is True


def test_a_request_anywhere_else_is_cut_out_however_it_is_written():
    assert feed(look_back.Lookout(), 'Oh hi! [[Recall: x]', ']', ' and more') == 'Oh hi! and more'
    assert feed(look_back.Lookout(), 'Line one\n[recall the zoo] Next') == 'Line one\nNext'
    assert feed(look_back.Lookout(strip=True), '[Recall: zoo]] So!') == 'So!'
    assert feed(look_back.Lookout(), 'A [note] and [rock]') == 'A [note] and [rock]'
    lookout = look_back.Lookout()
    assert feed(lookout, '[recall the zoo]') == '' and lookout.query == 'the zoo'


def test_a_model_that_asks_too_often_stops_being_offered_it():
    rates = look_back.Rates()
    for number in range(look_back.RATE_AFTER):
        assert rates.allowed('small')
        rates.count('small', asked=number % 2 == 0)
        rates.count('steady', asked=number % 10 == 0)
    assert not rates.allowed('small') and rates.allowed('steady')
