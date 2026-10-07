"""A user's correction of a current memory waits as a correction of that memory, never as a stray fact (PRD M8, M9)."""
import asyncio
import json

from conftest import send

from companion.providers.chat import Chunk

GARDENING = {'layer': 'user_fact', 'subject': "Mom's interests", 'value': 'she loves gardening'}


def enable(client, **flags):
    response = client.put('/api/settings', json={'automatic_memory': True, **flags})
    assert response.status_code == 200, response.text


def remember(client, **body):
    response = client.post('/api/memories', json=body)
    assert response.status_code == 200, response.text
    return response.json()


def run(client):
    response = client.post('/api/memory/run')
    assert response.status_code == 200, response.text


def suggestions(client):
    return client.get('/api/memory/suggestions').json()


def accept(client, suggestion):
    response = client.post(f"/api/memory/suggestions/{suggestion['id']}/accept")
    assert response.status_code == 200, response.text
    return response.json()


def memories(client, history=False):
    return client.get('/api/memories', params={'history': history}).json()


def model_reply(items):
    def respond(system, messages):
        if 'help a companion app remember' not in system:
            return [Chunk('Hello again.'), Chunk('', 'stop')]
        return [Chunk(json.dumps(items)), Chunk('', 'stop')]
    return respond


def test_saying_a_remembered_fact_is_wrong_waits_as_a_correction_of_it(client, connected):
    """A real run kept "Mom's interests: she loves gardening" after "my mom is definitely not a gardener"."""
    old = remember(client, **GARDENING)
    enable(client)
    send(client, 'my mom is definitely not a gardener', 'client-0001')
    run(client)
    [suggestion] = suggestions(client)
    assert (suggestion['reason'], suggestion['corrects'], suggestion['ends']) == ('correction', old['id'], False)
    assert (suggestion['subject'], suggestion['value'], suggestion['replaces']) == (
        "Mom's interests", 'not a gardener', ['she loves gardening'])
    assert [item['value'] for item in memories(client)] == ['she loves gardening'], 'nothing changes on its own'
    result = accept(client, suggestion)
    assert result['outcome'] == 'corrected' and result['memory']['supersedes_id'] == old['id']
    assert [(item['subject'], item['value']) for item in memories(client)] == [("Mom's interests", 'not a gardener')]
    history = {item['value']: item['status'] for item in memories(client, history=True)}
    assert history == {'she loves gardening': 'superseded', 'not a gardener': 'active'}


def test_something_that_stopped_being_true_ends_as_history(client, connected):
    enable(client)
    send(client, 'I live in Chicago', 'client-0001')
    run(client)
    work = remember(client, layer='user_fact', subject='Work', value='teacher at Lincoln High')
    send(client, "Actually I don't live in Chicago anymore. I'm not a teacher anymore.", 'client-0002')
    run(client)
    found = {item['replaces'][0]: item for item in suggestions(client)}
    assert set(found) == {'Chicago', 'teacher at Lincoln High'}
    assert all(item['reason'] == 'correction' and item['ends'] for item in found.values())
    for suggestion in found.values():
        assert accept(client, suggestion)['outcome'] == 'ended'
    ended = {item['value']: item for item in memories(client)}
    assert ended['Chicago']['current'] is False and ended['teacher at Lincoln High']['current'] is False
    assert ended['teacher at Lincoln High']['id'] == work['id'] and len(ended) == 2, 'nothing new is invented'


def test_a_known_pet_corrected_by_name_is_reworded(client, connected):
    enable(client)
    send(client, 'I have a dog called Pickles', 'client-0001')
    run(client)
    breed = remember(client, layer='user_fact', subject="Pickles' breed", value='a lab')
    send(client, 'No, Pickles is a beagle, not a lab', 'client-0002')
    run(client)
    [suggestion] = suggestions(client)
    assert (suggestion['corrects'], suggestion['value'], suggestion['replaces']) == (breed['id'], 'a beagle', ['a lab'])
    assert accept(client, suggestion)['memory']['value'] == 'a beagle'


def test_mentions_without_a_contradiction_propose_nothing(client, connected):
    remember(client, **GARDENING)
    enable(client)
    send(client, 'I live in Chicago', 'client-0001')
    for index, text in enumerate(['My mom loves her garden.', 'I told her my mom is not a gardener.',
                                  "My mom isn't home today.", "I'm not sure about Chicago.",
                                  "I don't think my mom likes gardening.", "My mom isn't a fan of Chicago.",
                                  "I'm not in Chicago this week.", 'My mom is a gardener, not a cook.'], 2):
        send(client, text, f'client-{index:04}')
    run(client)
    assert [item for item in suggestions(client) if item['reason'] == 'correction'] == []
    assert {'she loves gardening', 'Chicago'} <= {item['value'] for item in memories(client) if item['current']}


def test_a_declined_correction_is_not_offered_again(client, connected):
    remember(client, **GARDENING)
    enable(client)
    send(client, 'my mom is not a gardener', 'client-0001')
    run(client)
    [suggestion] = suggestions(client)
    client.post(f"/api/memory/suggestions/{suggestion['id']}/decline")
    send(client, "My mom's not a gardener", 'client-0002')
    run(client)
    assert suggestions(client) == []


def suggest(client, app):
    run(client)
    return asyncio.run(app.state.memory.suggest())


def test_a_model_answer_that_corrects_a_sent_memory_waits_as_its_correction(client, app, connected, provider):
    old = remember(client, **GARDENING)
    enable(client, model_memory_suggestions=True)
    provider.respond = model_reply([{'message': 1, 'layer': 'user_fact', 'subject': "Mom's interests",
                                     'value': 'never really gardening', 'corrects': "Mom's interests"}])
    send(client, "Turns out gardening was never really my mom's thing at all", 'model-0001')
    assert suggest(client, app) == 1
    [asked] = [request for request in provider.requests if 'help a companion app remember' in request['system']]
    [sent] = json.loads(asked['messages'][0]['content'])
    assert sent['known'] == ["Mom's interests: she loves gardening"]
    assert '"corrects"' in asked['system']
    [suggestion] = suggestions(client)
    assert (suggestion['source'], suggestion['reason'], suggestion['corrects']) == ('model', 'correction', old['id'])
    assert suggestion['rule'] == 'memory-suggest-3' and suggestion['replaces'] == ['she loves gardening']
    assert accept(client, suggestion)['memory']['value'] == 'never really gardening'
    assert [item['value'] for item in memories(client)] == ['never really gardening']


def test_a_model_answer_negating_the_same_subject_is_routed_without_a_mark(client, app, connected, provider):
    old = remember(client, **GARDENING)
    enable(client, model_memory_suggestions=True)
    provider.respond = model_reply([{'message': 1, 'layer': 'user_fact', 'subject': "mom's  INTERESTS",
                                     'value': 'never really gardening'}])
    send(client, "Turns out gardening was never really my mom's thing at all", 'model-0001')
    suggest(client, app)
    [suggestion] = suggestions(client)
    assert (suggestion['reason'], suggestion['corrects']) == ('correction', old['id'])


def test_a_model_correction_of_something_not_sent_is_dropped(client, app, connected, provider):
    remember(client, **GARDENING)
    enable(client, model_memory_suggestions=True)
    provider.respond = model_reply([
        {'message': 1, 'layer': 'user_fact', 'subject': "Dad's interests", 'value': 'never really gardening',
         'corrects': "Dad's interests"},
        {'message': 1, 'layer': 'user_fact', 'subject': 'Hobby', 'value': 'gardening', 'corrects': ['Hobby']}])
    send(client, "Turns out gardening was never really my mom's thing at all", 'model-0001')
    suggest(client, app)
    assert suggestions(client) == []
    assert [item['value'] for item in memories(client)] == ['she loves gardening']


def test_a_model_fact_that_only_mentions_a_memory_stays_a_plain_guess(client, app, connected, provider):
    remember(client, **GARDENING)
    enable(client, model_memory_suggestions=True)
    provider.respond = model_reply([{'message': 1, 'layer': 'user_fact', 'subject': "Mom's garden",
                                     'value': 'tomatoes in the garden this summer'}])
    send(client, 'My mom planted tomatoes in the garden this summer', 'model-0001')
    suggest(client, app)
    [suggestion] = suggestions(client)
    assert suggestion['reason'] == 'model_guess' and 'corrects' not in suggestion
