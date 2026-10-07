"""Model-found memories are saved automatically; contradictions and held sensitive facts wait (PRD M1, M7)."""
import asyncio
import json

from conftest import send

from companion.providers.chat import Chunk

LONG = 'Honestly the thing that keeps me going lately is my weekly pottery class with Jun'


def enable(client, **flags):
    response = client.put('/api/settings', json={'automatic_memory': True, 'model_memory_suggestions': True, **flags})
    assert response.status_code == 200, response.text


def model_reply(items):
    def respond(system, messages):
        if 'help a companion app remember' not in system:
            return [Chunk('Hello again.'), Chunk('', 'stop')]
        return [Chunk(json.dumps(items)), Chunk('', 'stop')]
    return respond


def run(client, app):
    client.post('/api/memory/run')
    return asyncio.run(app.state.memory.suggest())


def test_model_memory_is_on_by_default_and_can_be_turned_off(client, app, connected, provider):
    settings = client.get('/api/settings').json()
    assert settings['automatic_memory'] and settings['model_memory_suggestions'] and settings['sensitive_memory']
    client.put('/api/settings', json={'model_memory_suggestions': False})
    send(client, LONG, 'model-0001')
    assert run(client, app) == 0
    assert all('help a companion app remember' not in request['system'] for request in provider.requests)


def test_a_supported_guess_is_saved_automatically(client, app, connected, provider):
    enable(client)
    provider.respond = model_reply([{'message': 1, 'layer': 'user_fact', 'subject': 'Hobby',
                                     'value': 'weekly pottery class with Jun'}])
    send(client, LONG, 'model-0001')
    assert run(client, app) == 1
    [memory] = client.get('/api/memories').json()
    assert memory['value'] == 'weekly pottery class with Jun' and memory['origin'] == 'automatic'
    assert client.get('/api/memory/suggestions').json() == []
    assert run(client, app) == 0, 'a message is sent to the model once'


def test_a_sensitive_guess_waits_while_sensitive_memory_is_off(client, app, connected, provider):
    enable(client, sensitive_memory=False)
    provider.respond = model_reply([{'message': 1, 'layer': 'user_fact', 'subject': 'Allergy',
                                     'value': 'peanut allergy'}])
    send(client, 'ugh the bake sale is tomorrow and I have to avoid half of it, peanut allergy life', 'model-0001')
    run(client, app)
    assert client.get('/api/memories').json() == []
    [suggestion] = client.get('/api/memory/suggestions').json()
    assert suggestion['reason'] == 'sensitive' and suggestion['source'] == 'model'
    kept = client.post(f"/api/memory/suggestions/{suggestion['id']}/accept").json()['memory']
    assert kept['authority'] == 'confirmed' and kept['origin'] == 'suggestion'


def test_unsupported_or_malformed_guesses_are_dropped(client, app, connected, provider):
    enable(client)
    provider.respond = model_reply([{'message': 1, 'layer': 'user_fact', 'subject': 'Job', 'value': 'Works as a chef'},
                                    {'message': 9, 'layer': 'user_fact', 'subject': 'Hobby', 'value': 'pottery'},
                                    {'message': 1, 'layer': 'diagnosis', 'subject': 'Hobby', 'value': 'pottery'}])
    send(client, LONG, 'model-0001')
    run(client, app)
    assert client.get('/api/memory/suggestions').json() == []


def test_messages_the_rules_handled_are_not_sent(client, app, connected, provider):
    enable(client)
    provider.respond = model_reply([])
    send(client, 'I live in Chicago and I have lived here for many years now', 'model-0001')
    send(client, 'ok', 'model-0002')
    run(client, app)
    asked = [request for request in provider.requests if 'help a companion app remember' in request['system']]
    assert asked == []


def test_sentences_the_rules_missed_still_reach_the_model(client, app, connected, provider):
    enable(client)
    provider.respond = model_reply([{'message': 1, 'layer': 'user_fact', 'subject': 'Hobby',
                                     'value': 'weekly pottery class with Jun'}])
    send(client, f'I live in Chicago. {LONG}.', 'model-0001')
    assert run(client, app) == 1
    [asked] = [request for request in provider.requests if 'help a companion app remember' in request['system']]
    sent = json.loads(asked['messages'][0]['content'])
    assert sent == [{'message': 1, 'text': f'{LONG}.'}]
    assert sorted(item['value'] for item in client.get('/api/memories').json()) == ['Chicago', 'weekly pottery class with Jun']


def test_a_declined_guess_is_not_suggested_again(client, app, connected, provider):
    enable(client, sensitive_memory=False)
    provider.respond = model_reply([{'message': 1, 'layer': 'user_fact', 'subject': 'Allergy',
                                     'value': 'peanut allergy'}])
    send(client, 'ugh the bake sale is tomorrow and I have to avoid half of it, peanut allergy life', 'model-0001')
    run(client, app)
    [suggestion] = client.get('/api/memory/suggestions').json()
    client.post(f"/api/memory/suggestions/{suggestion['id']}/decline")
    send(client, 'the bake sale was a minefield again, peanut allergy life for real', 'model-0002')
    run(client, app)
    assert client.get('/api/memory/suggestions').json() == []


def test_turning_suggestions_off_while_the_model_works_discards_its_answer(client, app, connected, provider):
    enable(client)

    def respond(system, messages):
        if 'help a companion app remember' in system:
            client.put('/api/settings', json={'model_memory_suggestions': False})
            return [Chunk(json.dumps([{'message': 1, 'layer': 'user_fact', 'subject': 'Hobby',
                                       'value': 'weekly pottery class with Jun'}])), Chunk('', 'stop')]
        return [Chunk('Hello again.'), Chunk('', 'stop')]

    provider.respond = respond
    send(client, LONG, 'model-0001')
    run(client, app)
    assert client.get('/api/memory/suggestions').json() == []


def test_a_malformed_model_reply_leaves_the_conversation_intact(client, app, connected, provider):
    enable(client)
    provider.respond = lambda system, messages: [Chunk('not json'), Chunk('', 'stop')] \
        if 'help a companion app remember' in system else [Chunk('Hello again.'), Chunk('', 'stop')]
    send(client, LONG, 'model-0001')
    assert run(client, app) == 1
    assert client.get('/api/memory/suggestions').json() == []
    assert len(client.get('/api/conversation').json()['messages']) == 2


def test_a_sentence_that_names_more_than_the_rules_kept_still_reaches_the_model(client, app, connected, provider):
    """A long run lost the sister-in-law and the baby's due date: the rules kept the brother, so the model never saw
    the sentence."""
    enable(client)
    provider.respond = model_reply([{'message': 1, 'layer': 'user_fact', 'subject': "Brother's wife",
                                     'value': 'Priya'}])
    text = 'My brother Marcus and his wife Priya in Denver are having a baby in December'
    send(client, text, 'model-0001')
    assert run(client, app) == 1
    [asked] = [request for request in provider.requests if 'help a companion app remember' in request['system']]
    [sent] = json.loads(asked['messages'][0]['content'])
    assert sent['text'] == f'{text}.' and sent['already_saved'] == ['Brother: Marcus']
    assert 'without "I", "I\'m" or "my" in front' in asked['system']
