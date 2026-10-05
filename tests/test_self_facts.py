"""What the companion says about themselves is noted, stays consistent and is the user's to keep or remove."""
from datetime import timedelta

from conftest import send

from companion import self_facts
from companion.life import composer
from companion.providers.chat import Chunk


def says(provider, text):
    provider.replies.append([Chunk(text), Chunk('', 'stop')])


def keys(text):
    return [(fact.category, fact.subject, fact.value) for fact in self_facts.extract(text)]


def test_first_person_statements_are_captured():
    text = ("Honestly I hate cilantro. My brother Theo is visiting! I've never been to Europe, sadly. "
            'I grew up in Duluth. My favorite band is The National. My cat is called Miso. I love hiking.')
    assert keys(text) == [('dislikes', 'cilantro', 'cilantro'), ('person', 'brother', 'Theo'),
                          ('never', 'been to europe', 'Europe'), ('grew_up', 'hometown', 'Duluth'),
                          ('favorite', 'band', 'The National'), ('pet', 'cat', 'Miso'), ('likes', 'hiking', 'hiking')]


def test_talk_about_the_user_questions_and_maybes_are_not_facts():
    assert keys('I love that! I like talking to you. I love you too.') == []
    assert keys('Do you think I hate running? Maybe I would love sushi. If I grew up in Paris, who knows.') == []
    assert keys('*smiles* "I hate Mondays," she said in the film.') == []


def test_said_facts_reach_the_context_and_the_list(client, connected, provider):
    says(provider, "Ugh, I hate cilantro. My sister Ana would agree.")
    send(client, 'Want tacos?', 'client-self-01')
    facts = client.get('/api/self-facts').json()['facts']
    assert [(fact['label'], fact['value'], fact['status']) for fact in facts] == [('Dislikes', 'cilantro', 'noted'),
                                                                                 ('Person', 'Ana', 'noted')]
    system = client.get('/api/context/preview').json()['system']
    assert 'What you have said about yourself before' in system
    assert '- Dislikes: cilantro.' in system and '- Your sister is named Ana.' in system


def test_a_contradiction_waits_and_keeping_it_removes_the_old_one(client, connected, provider):
    says(provider, 'I hate cilantro, honestly.')
    send(client, 'Tacos?', 'client-self-02')
    says(provider, 'Oh I love cilantro!')
    send(client, 'With cilantro?', 'client-self-03')
    facts = client.get('/api/self-facts').json()['facts']
    old, new = facts
    assert old['status'] == 'noted' and new['status'] == 'conflict' and new['conflicts_with'] == old['id']
    assert 'Likes: cilantro' not in client.get('/api/context/preview').json()['system']
    facts = client.post(f"/api/self-facts/{new['id']}/keep").json()['facts']
    assert [(fact['category'], fact['status']) for fact in facts] == [('likes', 'kept')]
    system = client.get('/api/context/preview').json()['system']
    assert '- Likes: cilantro (confirmed).' in system and 'Dislikes: cilantro' not in system


def test_removing_a_fact_frees_what_waited_on_it(client, connected, provider):
    says(provider, 'My mom is named Rosa.')
    send(client, 'Family?', 'client-self-04')
    says(provider, 'My mom is named Clara.')
    send(client, 'Wait, what?', 'client-self-05')
    old, new = client.get('/api/self-facts').json()['facts']
    facts = client.post(f"/api/self-facts/{old['id']}/remove").json()['facts']
    assert [(fact['value'], fact['status']) for fact in facts] == [('Clara', 'noted')]


def test_a_replaced_reply_takes_its_facts_with_it(client, connected, provider):
    says(provider, 'I adore jazz.')
    sent = send(client, 'Music?', 'client-self-06')
    assert client.get('/api/self-facts').json()['facts']
    says(provider, 'Mostly podcasts, really.')
    response = client.post(f"/api/conversation/messages/{sent['message']['id']}/alternatives")
    assert response.status_code == 200, response.text
    assert client.get('/api/self-facts').json()['facts'] == []


def test_stated_dislikes_steer_the_companions_plans():
    definition = {'name': 'Mira', 'self_tastes': {'likes': [], 'dislikes': ['running', 'coffee']}}
    assert composer.aversions(definition) == {'workout', 'coffee'}
    slot = {'key': 'x@2026-10-07', 'local_date': '2026-10-07',
            'block': {'key': 'x', 'label': 'Free time', 'kind': 'leisure', 'start': '13:00', 'end': '17:00'}}
    from companion.life.world import EmptyWorld
    for index in range(60):
        event = composer.compose(slot, definition, EmptyWorld(), f'seed-{index}')
        assert event is None or event['activity'] not in {'workout', 'coffee'}
    assert 'reading' in composer.leanings({'self_tastes': {'likes': ['reading novels']}})


def test_a_first_message_is_read_for_facts_too(client, companion, clock):
    client.put('/api/life/settings', json={'texts_first': True})
    client.post('/api/memories', json={'layer': 'plan', 'subject': 'Exam', 'value': 'Exam Monday',
                                       'plan_status': 'agreed',
                                       'applies_from': (clock.now() - timedelta(hours=8)).isoformat(),
                                       'applies_until': (clock.now() - timedelta(hours=2)).isoformat()})
    assert client.post('/api/life/texts/check').json()['state'] == 'sent'
    assert client.get('/api/self-facts').json() == {'facts': []}


def test_a_reply_echoing_a_forgotten_message_takes_its_facts_with_it(client, connected, provider):
    provider.respond = lambda system, messages: [Chunk(f"Me too! {messages[-1]['content']}"), Chunk('', 'stop')]
    excluded = send(client, 'My sister is called Ana', 'client-self-07')['message']
    deleted = send(client, 'My dog is named Rex', 'client-self-08')['message']
    assert {fact['value'] for fact in client.get('/api/self-facts').json()['facts']} == {'Ana', 'Rex'}
    sister = client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Sister', 'value': 'Ana',
                                                'source_message_ids': [excluded['id']]}).json()
    dog = client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Dog', 'value': 'Rex',
                                             'source_message_ids': [deleted['id']]}).json()
    client.post(f"/api/memories/{sister['id']}/exclude")
    client.post(f"/api/memories/{dog['id']}/delete", json={'delete_sources': True})
    assert client.get('/api/self-facts').json()['facts'] == []
