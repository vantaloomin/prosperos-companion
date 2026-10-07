"""What the companion says about themselves is noted, stays consistent and is the user's to keep or remove."""
from datetime import timedelta

from conftest import send

from companion import self_facts
from companion.life import composer
from companion.providers.chat import Chunk


def says(provider, text):
    provider.replies.append([Chunk(text), Chunk('', 'stop')])


def keys(text, lowercase=False):
    return [(fact.category, fact.subject, fact.value) for fact in self_facts.extract(text, lowercase)]


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


def test_reactions_to_the_conversation_are_not_tastes():
    for text in ('lol i love the dedication.', 'i love this for you 😄 ten weeks is plenty', 'i love it almost as much',
                 'i love what i do', 'honestly i just love the vibe of the games'):
        assert keys(text) == [], text
    assert keys('i just like going to games, eating overpriced food') == [('likes', 'going to games', 'going to games')]


def test_lowercase_texting_names_people_and_pets_in_lowercase():
    text = 'omg my cat juniper knocked my coffee over. my sister ashley thinks its hilarious. my cat is named miso'
    assert keys(text) == [('pet', 'cat', 'Juniper'), ('person', 'sister', 'Ashley')]
    assert keys('my cat is named miso') == [('pet', 'cat', 'Miso')]
    assert keys('My cat is sleeping', lowercase=True) == []
    assert keys('i love my sister ashley and my best friend kayla')[1:] == [('person', 'sister', 'Ashley'),
                                                                           ('person', 'best friend', 'Kayla')]


def test_lowercase_common_words_are_not_names():
    for text in ('my cat is sleeping', 'my sister and i went out', 'my mom was mad', 'my dog just ate my sock',
                 'my grandma calls every thursday', 'my ex boyfriend texted me', 'my dog snores so loud',
                 'my cat knocked it over'):
        assert keys(text) == [], text
    assert keys('My cat is sleeping. My mom was mad.') == []


def test_team_position_and_workplace_are_captured():
    assert keys('my team, the baltimore crabshells, won tonight') == [('team', 'team', 'Baltimore Crabshells')]
    assert keys('my team is the crabshells and we won') == [('team', 'team', 'Crabshells')]
    assert keys('my roller derby team, the crabshells') == [('team', 'team', 'Crabshells')]
    assert keys('i play for the Baltimore Crabshells') == [('team', 'team', 'Baltimore Crabshells')]
    assert keys('i play blocker. I also play the cello.') == [('plays', 'blocker', 'blocker'),
                                                              ('plays', 'cello', 'cello')]
    assert keys('i play video games. I play it cool. my team won.') == []
    assert keys('i work in the er at mercy hospital as a nurse') == [('works_at', 'workplace', 'mercy hospital')]
    assert keys('I work at Blue Bottle on weekends.') == [('works_at', 'workplace', 'Blue Bottle')]
    assert keys('i work at home. i work at 9 tomorrow') == []


def test_a_second_team_is_a_contradiction(client, connected, provider):
    says(provider, 'my team, the baltimore crabshells, is killing it')
    send(client, 'Derby?', 'client-self-09')
    says(provider, 'i play blocker for my team, the charm city furies')
    send(client, 'Wait, which team?', 'client-self-10')
    old, *rest = client.get('/api/self-facts').json()['facts']
    new = next(fact for fact in rest if fact['category'] == 'team')
    assert (old['label'], old['value'], old['status']) == ('Team', 'Baltimore Crabshells', 'noted')
    assert new['value'] == 'Charm City Furies' and new['status'] == 'conflict' and new['conflicts_with'] == old['id']
    assert ('Plays', 'blocker', 'noted') in [(fact['label'], fact['value'], fact['status']) for fact in rest]
    assert '- Team: Baltimore Crabshells.' in client.get('/api/context/preview').json()['system']


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


def test_a_relative_named_unlike_the_circle_waits_as_a_conflict(client, app, connected, provider):
    """One reply naming a mom the circle doesn't have would otherwise sit beside the circle's mom in every context."""
    person = client.get('/api/life/circle').json()[0]
    with app.state.database.connect(write=True) as connection:
        connection.execute("UPDATE circle_people SET role='mom', name='Cathy' WHERE id=?", (person['id'],))
    says(provider, 'My mom Linda would love this.')
    send(client, 'Family?', 'client-self-11')
    says(provider, 'My mom Cathy says hi.')
    send(client, 'Hi to her too', 'client-self-12')
    facts = {fact['value']: fact for fact in client.get('/api/self-facts').json()['facts']}
    linda, cathy = facts['Linda'], facts['Cathy']
    assert (linda['value'], linda['status'], linda['circle_person']) == ('Linda', 'conflict', 'mom Cathy')
    assert (cathy['value'], cathy['status']) == ('Cathy', 'noted') and 'circle_person' not in cathy
    system = client.get('/api/context/preview').json()['system']
    assert 'named Linda' not in system and '- Your mom is named Cathy.' in system
    facts = client.post(f"/api/self-facts/{linda['id']}/keep").json()['facts']
    assert ('Linda', 'kept') in [(fact['value'], fact['status']) for fact in facts]


def test_the_user_correcting_them_in_chat_holds_what_they_said(client, connected, provider):
    """"Your sister is Ashley, not Jo" takes Jo out of the very next reply's context, and Jo said again waits too."""
    says(provider, 'My sister Jo is visiting. I grew up in Ohio.')
    send(client, 'Family?', 'client-self-13')
    says(provider, 'Oh right, sorry!')
    sent = send(client, "Your sister is Ashley, not Jo. And you didn't grow up in Ohio.", 'client-self-14')['message']
    request = provider.requests[-1]['system']
    assert 'named Jo' not in request and 'Ohio' not in request.split('What you have said about yourself before')[-1]
    facts = {fact['value']: fact for fact in client.get('/api/self-facts').json()['facts']}
    assert facts['Jo']['status'] == facts['Ohio']['status'] == 'conflict'
    assert facts['Jo']['conflicts_with'] == f"user:{sent['id']}" and facts['Jo']['user_said'].startswith('Your sister')
    says(provider, 'My sister Jo says hi.')
    send(client, 'Hm?', 'client-self-15')
    assert [fact['status'] for fact in client.get('/api/self-facts').json()['facts'] if fact['value'] == 'Jo'] == \
        ['conflict', 'conflict']
    says(provider, 'Ha, fine.')
    send(client, 'What if your sister was called Jo?', 'client-self-16')
    kept = client.post(f"/api/self-facts/{facts['Ohio']['id']}/keep").json()['facts']
    assert ('Ohio', 'kept') in [(fact['value'], fact['status']) for fact in kept]


def test_a_place_the_definition_contradicts_waits(client, provider):
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'Europe/Lisbon',
                                                   'identity': 'A nurse who works at Mercy Hospital and grew up in Duluth.'})
    assert response.status_code == 200, response.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    says(provider, 'I work at Starbucks now. I grew up in Duluth, Minnesota.')
    send(client, 'Work?', 'client-self-17')
    facts = {fact['value']: fact for fact in client.get('/api/self-facts').json()['facts']}
    assert (facts['Starbucks']['status'], facts['Starbucks']['definition_says']) == ('conflict', 'Mercy Hospital')
    assert facts['Duluth']['status'] == 'noted'
