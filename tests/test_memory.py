from datetime import timedelta

from conftest import send

from companion.providers.chat import Chunk


def remember(client, **body):
    response = client.post('/api/memories', json=body)
    assert response.status_code == 200, response.text
    return response.json()


def system_prompt(client):
    return client.get('/api/context/preview').json()['system']


def test_remembered_fact_reaches_the_next_reply(client, connected, provider):
    remember(client, layer='user_fact', subject='Home city', value='Chicago')
    send(client, 'Hi', 'client-0001')
    assert 'Home city: Chicago' in provider.requests[0]['system']


def test_duplicate_remember_returns_the_existing_memory(client, companion):
    first = remember(client, layer='user_fact', subject='Pet', value='A cat named Biscuit')
    second = remember(client, layer='user_fact', subject='Pet', value='A cat named Biscuit')
    assert first['id'] == second['id']


def test_correction_supersedes_and_keeps_history(client, companion):
    chicago = remember(client, layer='user_fact', subject='Home city', value='Chicago')
    boston = client.post(f"/api/memories/{chicago['id']}/correct",
                         json={'value': 'Boston', 'expected_revision': 1}).json()
    assert boston['supersedes_id'] == chicago['id'] and boston['revision'] == 2
    prompt = system_prompt(client)
    assert 'Boston' in prompt and 'Chicago' not in prompt
    history = {item['id']: item['status'] for item in client.get('/api/memories?history=true').json()}
    assert history[chicago['id']] == 'superseded'
    stale = client.post(f"/api/memories/{chicago['id']}/correct", json={'value': 'Denver', 'expected_revision': 1})
    assert stale.status_code == 409


def test_exclusion_also_blocks_the_source_message(client, connected, provider):
    message = send(client, 'My sister is called Zorabel', 'client-0001')['message']
    memory = remember(client, layer='user_fact', subject='Sister', value='Zorabel',
                      source_message_ids=[message['id']])
    client.post(f"/api/memories/{memory['id']}/exclude")
    preview = client.get('/api/context/preview').json()
    assert 'Zorabel' not in preview['system']
    assert all('Zorabel' not in item['content'] for item in preview['messages'])


def test_delete_removes_every_version_and_can_redact_sources(client, connected):
    message = send(client, 'I am training for a marathon', 'client-0001')['message']
    memory = remember(client, layer='user_fact', subject='Training', value='Marathon',
                      source_message_ids=[message['id']])
    corrected = client.post(f"/api/memories/{memory['id']}/correct",
                            json={'value': 'Half marathon', 'expected_revision': 1}).json()
    result = client.post(f"/api/memories/{corrected['id']}/delete", json={'delete_sources': True}).json()
    assert sorted(result['deleted_memory_ids']) == sorted([memory['id'], corrected['id']])
    assert result['redacted_message_ids'] == [message['id']]
    assert client.get('/api/memories?history=true').json() == []
    messages = {item['id']: item for item in client.get('/api/conversation').json()['messages']}
    assert messages[message['id']]['text'] == '' and messages[message['id']]['redacted'] is True
    assert client.get('/api/conversation/search', params={'q': 'marathon'}).json()['results'] == []


def test_replies_to_forgotten_messages_leave_context_too(client, connected, provider):
    """The companion's reply usually repeats what it answered, so it must not resend forgotten content."""
    provider.respond = lambda system, messages: [Chunk(f"You said: {messages[-1]['content']}"), Chunk('', 'stop')]
    excluded = send(client, 'My sister is called Zorabel', 'client-0001')['message']
    deleted = send(client, 'I am training for a marathon', 'client-0002')['message']
    kept = send(client, 'I like tea', 'client-0003')['message']
    sister = remember(client, layer='user_fact', subject='Sister', value='Zorabel', source_message_ids=[excluded['id']])
    training = remember(client, layer='user_fact', subject='Training', value='Marathon',
                        source_message_ids=[deleted['id']])
    client.post(f"/api/memories/{sister['id']}/exclude")
    client.post(f"/api/memories/{training['id']}/delete", json={'delete_sources': True})
    send(client, 'What do you remember?', 'client-0004')
    sent = provider.requests[-1]['system'] + ''.join(item['content'] for item in provider.requests[-1]['messages'])
    assert 'Zorabel' not in sent and 'marathon' not in sent
    assert 'You said: I like tea' in sent and kept['text'] in sent

    search = client.get('/api/conversation/search', params={'q': 'marathon'}).json()['results']
    assert search == []
    assert [item['text'] for item in client.get('/api/conversation/search', params={'q': 'tea'}).json()['results']] \
        == ['You said: I like tea', 'I like tea']


def test_declined_message_cannot_become_a_memory(client, connected):
    message = send(client, 'Hypothetically, I live on the moon', 'client-0001')['message']
    client.post(f"/api/conversation/messages/{message['id']}/decline-memory")
    response = client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Home', 'value': 'Moon',
                                                  'source_message_ids': [message['id']]})
    assert response.status_code == 409


def test_tentative_memory_stays_out_until_confirmed(client, companion):
    guess = remember(client, layer='user_fact', subject='Hobby', value='Probably likes jazz', tentative=True)
    assert 'jazz' not in system_prompt(client)
    client.post(f"/api/memories/{guess['id']}/confirm")
    assert 'jazz' in system_prompt(client)


def test_temporary_context_expires_without_being_erased(client, companion, clock):
    until = (clock.now() + timedelta(days=2)).isoformat()
    memory = remember(client, layer='temporary', subject='Travel', value='Away in Rome', applies_until=until)
    assert 'Rome' in system_prompt(client)
    clock.advance(timedelta(days=3))
    assert 'Rome' not in system_prompt(client)
    assert [item['id'] for item in client.get('/api/memories').json()] == [memory['id']]


def test_open_plans_are_commitments_and_cancelled_plans_drop_out(client, companion):
    plan = remember(client, layer='plan', subject='Interview', value='Job interview Thursday', plan_status='agreed')
    assert '## Open plans and commitments' in system_prompt(client)
    client.post(f"/api/memories/{plan['id']}/correct",
                json={'value': 'Job interview Thursday', 'plan_status': 'cancelled', 'expected_revision': 1})
    assert 'interview' not in system_prompt(client).lower()


def test_personal_memories_cannot_be_marked_fictional(client, companion):
    response = client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Job', 'value': 'Pilot',
                                                  'reality': 'fiction'})
    assert response.status_code == 422


def test_boundaries_that_do_not_fit_are_reported(client, companion):
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'm',
                                        'context_tokens': 1024, 'max_output_tokens': 900})
    remember(client, layer='user_fact', subject='Topics', value='Never discuss my ex. ' * 40, boundary=True)
    response = client.get('/api/context/preview')
    assert response.status_code == 422
    assert response.json()['code'] == 'context_limit'


def test_older_turns_are_recalled_by_relevance(client, connected, provider):
    send(client, 'My favourite tea is genmaicha', 'client-0000')
    for index in range(1, 14):
        send(client, f'Small talk number {index}', f'client-{index:04d}')
    preview = client.get('/api/context/preview').json()
    assert 'genmaicha' not in str(preview['messages'])
    send(client, 'What tea should I buy, genmaicha again?', 'client-0099')
    assert 'favourite tea is genmaicha' in provider.requests[-1]['system']


def test_absence_reaction_is_a_character_trait(client, companion):
    assert 'do not express hurt, guilt or pressure' in system_prompt(client)
    definition = {**companion['version']['definition'], 'absence_reaction': 'Gets a little jealous and sulks'}
    client.post('/api/companion/versions', json={'definition': definition,
                                                 'expected_version_id': companion['active_version_id']})
    prompt = system_prompt(client)
    assert 'Gets a little jealous and sulks' in prompt
    assert 'do not express hurt' not in prompt


def revise(client, companion, **changes):
    definition = {**companion['version']['definition'], **changes}
    response = client.post('/api/companion/versions', json={'definition': definition,
                                                            'expected_version_id': companion['active_version_id']})
    assert response.status_code == 200, response.text
    return response.json()


def test_new_companions_have_no_emotional_traits(companion):
    assert companion['version']['definition']['emotional_traits'] == []


def test_emotional_traits_shape_the_character_with_their_intensity(client, companion):
    revise(client, companion, emotional_traits=[{'name': 'Guilt over absence', 'intensity': 'strong'},
                                                {'name': 'Jealousy', 'intensity': 'mild', 'note': 'teasing'}])
    prompt = system_prompt(client)
    assert 'Guilt over absence (strong); Jealousy (mild): teasing.' in prompt
    assert 'do not express hurt' not in prompt
    assert 'never express jealousy or possessiveness as romantic exclusivity' in prompt


def test_romantic_framing_allows_romantic_jealousy(client, companion):
    revise(client, companion, relationship='romance', emotional_traits=[{'name': 'Jealousy', 'intensity': 'moderate'}])
    assert 'romantic exclusivity' not in system_prompt(client)


def test_trait_intensity_is_validated(client, companion):
    definition = {**companion['version']['definition'], 'emotional_traits': [{'name': 'Jealousy', 'intensity': 'max'}]}
    response = client.post('/api/companion/versions', json={'definition': definition,
                                                            'expected_version_id': companion['active_version_id']})
    assert response.status_code == 422


def test_delete_preview_lists_what_would_go_and_what_stays(client, connected):
    message = send(client, 'My sister Ana lives in Porto', 'client-0001')['message']
    sister = remember(client, layer='user_fact', subject='Sister', value='Ana', source_message_ids=[message['id']])
    remember(client, layer='user_fact', subject="Sister's city", value='Porto', source_message_ids=[message['id']])
    corrected = client.post(f"/api/memories/{sister['id']}/correct",
                            json={'value': 'Ana Maria', 'expected_revision': 1}).json()
    preview = client.get(f"/api/memories/{corrected['id']}/delete-preview").json()
    assert sorted(preview['memory_ids']) == sorted([sister['id'], corrected['id']])
    assert preview['source_message_ids'] == [message['id']]
    assert [item['subject'] for item in preview['other_memories']] == ["Sister's city"]
    assert len(client.get('/api/memories?history=true').json()) == 3, 'a preview changes nothing'
