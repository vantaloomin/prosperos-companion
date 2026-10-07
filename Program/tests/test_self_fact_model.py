"""The memory model reads the companion's replies for their own facts the rules miss (realism: her own facts)."""
import asyncio
import json

from conftest import send

from companion.providers.chat import Chunk

ASKED = "keep a fictional character"


def respond(reply, items):
    """Chat replies with `reply`; the self-facts prompt gets `items` (a list, or a function of the batch)."""
    def answer(system, messages):
        if ASKED in system:
            batch = json.loads(messages[-1]['content'])
            return [Chunk(json.dumps(items(batch) if callable(items) else items)), Chunk('', 'stop')]
        return [Chunk(reply), Chunk('', 'stop')]
    return answer


def read(app):
    return asyncio.run(app.state.memory.read_self_facts())


def facts(client):
    return [(fact['label'], fact['value'], fact['status']) for fact in client.get('/api/self-facts').json()['facts']]


def asked(provider):
    return [json.loads(request['messages'][0]['content']) for request in provider.requests if ASKED in request['system']]


def test_a_team_named_in_an_answer_is_noted_and_kept_in_context(client, app, connected, provider):
    provider.respond = respond("we're the harbor hellions lol. you should come to a bout",
                               [{'message': 1, 'category': 'team', 'subject': 'team', 'value': 'harbor hellions'}])
    send(client, "wait what's your derby team called?", 'self-model-01')
    assert facts(client) == []
    assert read(app) == 1
    [[sent]] = asked(provider)
    assert sent['answering'] == "wait what's your derby team called?" and sent['text'].startswith("we're the")
    assert facts(client) == [('Team', 'Harbor Hellions', 'noted')]
    assert '- Team: Harbor Hellions.' in client.get('/api/context/preview').json()['system']
    assert read(app) == 0, 'a message is read once'


def test_a_new_team_name_later_waits_as_a_conflict(client, app, connected, provider):
    provider.respond = respond("we're the harbor hellions, been on the team three years",
                               [{'message': 1, 'category': 'team', 'subject': 'team', 'value': 'Harbor Hellions'}])
    send(client, 'Which team are you on?', 'self-model-02')
    read(app)
    provider.respond = respond('the hellcats had a rough bout saturday, we lost by twenty',
                               [{'message': 1, 'category': 'team', 'subject': 'team', 'value': 'Hellcats'}])
    send(client, 'How did the bout go?', 'self-model-03')
    read(app)
    assert facts(client) == [('Team', 'Harbor Hellions', 'noted'), ('Team', 'Hellcats', 'conflict')]
    assert 'Hellcats' not in client.get('/api/context/preview').json()['system']


def test_people_details_and_tastes_use_her_own_words(client, app, connected, provider):
    provider.respond = respond(
        'my sister jo plays derby too, and my car is a beat up blue civic. i love the dedication though',
        [{'message': 1, 'category': 'person', 'subject': 'Sister', 'value': 'jo'},
         {'message': 1, 'category': 'detail', 'subject': 'car', 'value': 'beat up blue civic'},
         {'message': 1, 'category': 'likes', 'subject': 'dedication', 'value': 'the dedication'},
         {'message': 1, 'category': 'pet', 'subject': 'dog', 'value': 'Biscuit'},
         {'message': 2, 'category': 'team', 'subject': 'team', 'value': 'jo'},
         {'message': 1, 'category': 'job', 'subject': 'work', 'value': 'civic'}])
    send(client, 'Tell me about your family', 'self-model-04')
    read(app)
    assert facts(client) == [('Person', 'Jo', 'noted'), ('Detail', 'beat up blue civic', 'noted')]
    system = client.get('/api/context/preview').json()['system']
    assert '- Your sister is named Jo.' in system and '- Your car: beat up blue civic.' in system


def test_nothing_is_read_while_model_memory_is_off(client, app, connected, provider):
    client.put('/api/settings', json={'model_memory_suggestions': False})
    provider.respond = respond("we're the harbor hellions, been on the team three years", [])
    send(client, 'Which team are you on?', 'self-model-05')
    assert read(app) == 0 and asked(provider) == []


def test_a_reply_replaced_before_it_is_read_is_skipped(client, app, connected, provider):
    provider.respond = respond("we're the harbor hellions, been on the team three years",
                               [{'message': 1, 'category': 'team', 'subject': 'team', 'value': 'Harbor Hellions'}])
    reply = send(client, 'Which team are you on?', 'self-model-06')
    with app.state.database.connect(write=True) as connection:
        connection.execute('UPDATE messages SET active=0 WHERE reply_to=?', (reply['message']['id'],))
    assert read(app) == 1 and asked(provider) == [] and facts(client) == []


def test_names_from_the_users_own_life_are_not_hers(client, app, connected, provider):
    """Asked "what's my dog's name?", she answers with the user's dog; that is not her pet."""
    client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Dog', 'value': 'Pickles'})
    provider.respond = respond("pickles!! the sock thief. and my cat waffles says hi",
                               [{'message': 1, 'category': 'pet', 'subject': 'dog', 'value': 'Pickles'},
                                {'message': 1, 'category': 'pet', 'subject': 'cat', 'value': 'Waffles'}])
    send(client, "quiz time: what's my dog's name?", 'self-model-07')
    read(app)
    assert facts(client) == [('Pet', 'Waffles', 'noted')]


def test_her_job_negations_and_unnamed_relatives_are_left_out(client, app, connected, provider):
    provider.respond = respond("nursing in the er is wild, i can't play a note, my mom says hi. i play blocker",
                               [{'message': 1, 'category': 'works_at', 'subject': 'job', 'value': 'nursing'},
                                {'message': 1, 'category': 'plays', 'subject': 'instrument', 'value': "i can't play a note"},
                                {'message': 1, 'category': 'person', 'subject': 'mom', 'value': 'mom'},
                                {'message': 1, 'category': 'detail', 'subject': 'profession', 'value': 'nursing'},
                                {'message': 1, 'category': 'plays', 'subject': 'position', 'value': 'blocker'}])
    send(client, 'how was your day', 'self-model-08')
    read(app)
    assert facts(client) == [('Plays', 'blocker', 'noted')]


def test_a_shorter_form_of_the_same_team_is_not_a_conflict(client, app, connected, provider):
    provider.respond = respond('the baltimore blast won saturday, best bout all year',
                               [{'message': 1, 'category': 'team', 'subject': 'team', 'value': 'baltimore blast'}])
    send(client, 'Which team?', 'self-model-09')
    read(app)
    provider.respond = respond('the blast are on a roll, two wins in a row now',
                               [{'message': 1, 'category': 'team', 'subject': 'team', 'value': 'the blast'}])
    send(client, 'And now?', 'self-model-10')
    read(app)
    assert facts(client) == [('Team', 'Baltimore Blast', 'noted')]
