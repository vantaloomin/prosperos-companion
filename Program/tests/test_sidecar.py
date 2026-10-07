"""The sidecar reads the app's context, stays out of it, and proposes changes that are checked against what it saw."""
import json

from conftest import send

from companion.providers.chat import Chunk


def says(provider, text):
    provider.replies.append([Chunk(text), Chunk('', 'stop')])


def answers(provider, *replies):
    queue = list(replies)
    provider.respond = lambda system, messages: [Chunk(queue.pop(0)), Chunk('', 'stop')]


def remember(client, subject, value):
    response = client.post('/api/memories', json={'layer': 'user_fact', 'subject': subject, 'value': value})
    assert response.status_code == 200, response.text
    return response.json()


def ask(client, message, **extra):
    response = client.post('/api/sidecar', json={'message': message, **extra})
    assert response.status_code == 200, response.text
    return response.json()


def test_the_sidecar_sees_the_conversation_and_memories_but_is_never_part_of_them(client, connected, provider):
    says(provider, 'I adore jazz.')
    send(client, 'Music?', 'client-side-01')
    remember(client, 'job', 'Works at a bakery')
    answers(provider, json.dumps({'reply': 'That reply fits her.', 'changes': []}))
    result = ask(client, 'Was her last reply in character?', view='conversation')
    assert result == {'reply': 'That reply fits her.', 'changes': [], 'prompt_version': 'character-draft-3'}
    request = provider.requests[-1]
    assert '[m1] The user' in request['system'] and '[m2] Mira' in request['system'] and 'I adore jazz.' in request['system']
    assert 'job: Works at a bakery' in request['system'] and 'looking at the chat' in request['system']
    assert '{{' not in request['system']
    # Nothing it said reached the conversation.
    history = client.get('/api/conversation').json()['messages']
    assert [message['text'] for message in history] == ['Music?', 'I adore jazz.']


def test_proposals_name_real_messages_and_memories(client, connected, provider):
    says(provider, 'I adore jazz.')
    sent = send(client, 'Music?', 'client-side-02')
    memory = remember(client, 'job', 'Works at a bakery')
    answers(provider, json.dumps({'reply': 'Here you go.', 'changes': [
        {'kind': 'reply', 'ref': 'm2', 'text': 'Jazz, mostly. Old records.'},
        {'kind': 'memory', 'ref': 'k1', 'value': 'user_fact · job: Works at a flower shop'},
        {'kind': 'new_memory', 'layer': 'user_fact', 'subject': 'pet', 'value': 'pet: Has a dog called Pip'},
        {'kind': 'forget_memory', 'ref': 'k1'},
        {'kind': 'field', 'field': 'voice', 'value': 'Short and warm.'}]}))
    changes = ask(client, 'Fix things up.')['changes']
    assert changes[0] == {'kind': 'reply', 'message_id': sent['reply']['id'], 'before': 'I adore jazz.',
                          'text': 'Jazz, mostly. Old records.', 'created_at': sent['reply']['created_at']}
    assert changes[1]['memory_id'] == memory['id'] and changes[1]['before'] == 'Works at a bakery'
    assert changes[1]['value'] == 'Works at a flower shop'
    assert changes[1]['revision'] == memory['revision']
    assert changes[2] == {'kind': 'new_memory', 'layer': 'user_fact', 'subject': 'pet', 'value': 'Has a dog called Pip'}
    assert changes[3]['kind'] == 'forget_memory' and changes[4] == {'kind': 'field', 'field': 'voice', 'value': 'Short and warm.'}


def test_made_up_references_and_forbidden_changes_are_sent_back_then_dropped(client, connected, provider):
    says(provider, 'I adore jazz.')
    send(client, 'Music?', 'client-side-03')
    bad = json.dumps({'reply': 'Done.', 'changes': [
        {'kind': 'reply', 'ref': 'm1', 'text': 'Edited user words'}, {'kind': 'memory', 'ref': 'k9', 'value': 'x'},
        {'kind': 'field', 'field': 'relationship', 'value': 'romance'}, {'kind': 'reply', 'ref': 'm2', 'text': 'Better.'}]})
    answers(provider, bad, bad)
    changes = ask(client, 'Change things.')['changes']
    assert "only Mira's replies" in provider.requests[-1]['messages'][-1]['content']
    assert [change['kind'] for change in changes] == ['reply']


def test_the_open_character_form_is_what_it_edits(client, provider):
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model'})
    answers(provider, json.dumps({'reply': 'Older now.', 'changes': [
        {'kind': 'field', 'field': 'identity', 'value': '41, a nurse.'}]}))
    form = {'name': 'Dana Whitfield', 'identity': '34, a nurse.', 'personality': 'Dry.', 'home_city': 'baltimore'}
    result = ask(client, 'Make her 41.', view='character', definition=form)
    assert result['changes'] == [{'kind': 'field', 'field': 'identity', 'value': '41, a nurse.'}]
    system = provider.requests[0]['system']
    assert 'open character form' in system and 'Dana Whitfield' in system and 'No messages yet.' in system


def test_the_sidecar_needs_a_model(client, companion):
    response = client.post('/api/sidecar', json={'message': 'hi'})
    assert response.status_code == 409 and response.json()['code'] == 'no_connection'


def test_editing_a_reply_keeps_the_old_words_and_rereads_what_she_said(client, connected, provider):
    says(provider, 'I adore jazz.')
    sent = send(client, 'Music?', 'client-side-04')
    reply = sent['reply']
    assert [fact['value'] for fact in client.get('/api/self-facts').json()['facts']] == ['jazz']
    response = client.post(f"/api/conversation/messages/{reply['id']}/edit",
                           json={'text': 'Honestly I hate cilantro.', 'expected_text': 'I adore jazz.'})
    assert response.status_code == 200, response.text
    assert response.json()['previous_text'] == 'I adore jazz.'
    assert client.get('/api/conversation').json()['messages'][-1]['text'] == 'Honestly I hate cilantro.'
    assert [fact['value'] for fact in client.get('/api/self-facts').json()['facts']] == ['cilantro']
    # A stale proposal is refused, and the user's own words are never edited here.
    stale = client.post(f"/api/conversation/messages/{reply['id']}/edit", json={'text': 'x', 'expected_text': 'I adore jazz.'})
    assert stale.status_code == 409
    own = client.post(f"/api/conversation/messages/{sent['message']['id']}/edit", json={'text': 'x', 'expected_text': 'Music?'})
    assert own.status_code == 422
    # Undo is an edit back.
    back = client.post(f"/api/conversation/messages/{reply['id']}/edit",
                       json={'text': 'I adore jazz.', 'expected_text': 'Honestly I hate cilantro.'})
    assert back.status_code == 200 and [fact['value'] for fact in client.get('/api/self-facts').json()['facts']] == ['jazz']
