"""Model-found memories are saved automatically; contradictions and held sensitive facts wait (PRD M1, M7)."""
import asyncio
import json
from datetime import timedelta

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
    assert sent == [{'message': 1, 'to': 'Mira', 'text': f'{LONG}.'}]
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


def test_a_model_guess_never_replaces_a_core_fact_on_its_own(client, app, connected, provider):
    """"Moved from Denver last month" is not where the user lives now: Home city: Baltimore stays until they accept."""
    enable(client)
    client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Home city', 'value': 'Baltimore'})
    provider.respond = model_reply([{'message': 1, 'layer': 'user_fact', 'subject': 'Home city',
                                     'value': 'moved from Denver last month'}])
    send(client, 'It still feels strange that I moved from Denver last month, everything here is new', 'model-0001')
    run(client, app)
    assert [(item['subject'], item['value']) for item in client.get('/api/memories').json()] == [
        ('Home city', 'Baltimore')]
    [suggestion] = client.get('/api/memory/suggestions').json()
    assert (suggestion['reason'], suggestion['replaces']) == ('conflict', ['Baltimore'])


def test_a_model_correction_of_a_core_fact_waits_and_is_dated_by_its_message(client, app, clock, connected,
                                                                            provider):
    enable(client)
    client.post('/api/memories', json={'layer': 'user_fact', 'subject': 'Home city', 'value': 'Baltimore'})
    provider.respond = model_reply([{'message': 1, 'layer': 'user_fact', 'subject': 'Home city',
                                     'value': 'Towson these days', 'corrects': 'Home city'}])
    message = send(client, 'Small update about Baltimore, everything is in Towson for me these days since spring',
                   'model-0001')['message']
    clock.advance(timedelta(days=4))
    run(client, app)
    assert [item['value'] for item in client.get('/api/memories').json()] == ['Baltimore']
    [suggestion] = client.get('/api/memory/suggestions').json()
    assert (suggestion['reason'], suggestion['replaces']) == ('conflict', ['Baltimore'])
    kept = client.post(f"/api/memory/suggestions/{suggestion['id']}/accept").json()['memory']
    assert (kept['value'], kept['stated_at']) == ('Towson these days', message['created_at'])


def test_a_model_guess_the_rules_already_kept_is_not_saved_twice(client, app, connected, provider):
    enable(client)
    provider.respond = model_reply([{'message': 1, 'layer': 'user_fact', 'subject': 'Dog', 'value': 'Pepper'}])
    send(client, 'My dog Pepper and I walked all the way to Druid Hill Park this morning', 'model-0001')
    run(client, app)
    dogs = [item for item in client.get('/api/memories').json() if item['subject'] == 'Dog']
    assert [item['value'] for item in dogs] == ['Pepper']


BATS = 'we were out on the porch watching bats tonight, bats eat mosquitoes and flies and they live in the attic'


def test_small_talk_about_animals_is_not_saved_as_someone(client, app, connected, provider):
    enable(client)
    provider.respond = model_reply([{'message': 1, 'layer': 'user_fact', 'subject': "Bats' diet",
                                     'value': 'eat mosquitoes and flies'},
                                    {'message': 1, 'layer': 'user_fact', 'subject': "Bats' home",
                                     'value': 'live in the attic'}])
    send(client, BATS, 'model-0001')
    run(client, app)
    assert client.get('/api/memories').json() == []


def test_people_in_the_users_life_are_still_saved(client, app, connected, provider):
    enable(client)
    provider.respond = model_reply([{'message': 1, 'layer': 'user_fact', 'subject': "Mom's garden",
                                     'value': 'grows tomatoes every summer'},
                                    {'message': 2, 'layer': 'user_fact', 'subject': "Jo's hobby",
                                     'value': 'climbs at the gym on weekends'}])
    send(client, 'my mom grows tomatoes every summer and gives half of them away', 'model-0001')
    send(client, 'Jo climbs at the gym on weekends and keeps asking me to come', 'model-0002')
    run(client, app)
    assert sorted(memory['subject'] for memory in client.get('/api/memories').json()) == ["Jo's hobby", "Mom's garden"]


def test_strays_saved_by_an_earlier_prompt_are_tidied_away(client, app, connected, provider, monkeypatch):
    from companion.memory import owners, suggest
    enable(client)
    provider.respond = model_reply([{'message': 1, 'layer': 'user_fact', 'subject': "Bats' diet",
                                     'value': 'eat mosquitoes and flies'},
                                    {'message': 1, 'layer': 'user_fact', 'subject': 'Porch',
                                     'value': 'watching bats tonight'}])
    monkeypatch.setattr(owners, 'belongs', lambda *args: True)
    send(client, BATS, 'model-0001')
    run(client, app)
    monkeypatch.undo()
    database = app.state.database
    with database.connect(write=True) as connection:
        connection.execute("UPDATE memory_candidates SET rule='memory-suggest-4' WHERE source='model'")
    assert len(client.get('/api/memories').json()) == 2
    assert suggest.tidy(database) == 1
    assert [memory['subject'] for memory in client.get('/api/memories').json()] == ['Porch']
    assert suggest.tidy(database) == 0


MEETUP = "Thank you, I had a good time. I didn't feel afraid of you, like you were dangerous"


def test_the_companion_is_named_never_the_assistant(client, app, connected, provider):
    enable(client)
    provider.respond = model_reply([{'message': 1, 'layer': 'relationship', 'subject': 'Trust in assistant',
                                     'value': "didn't feel afraid of the assistant as if it were dangerous"}])
    send(client, MEETUP, 'model-0001')
    run(client, app)
    request = next(request for request in provider.requests if 'help a companion app remember' in request['system'])
    assert '"to": "Mira"' in request['messages'][-1]['content']
    [memory] = client.get('/api/memories').json()
    assert (memory['subject'], memory['value']) == ('Trust in Mira', "You didn't feel afraid of Mira as if they were dangerous")


def test_an_assistant_the_user_talks_about_stays_one(client, app, connected, provider):
    enable(client)
    provider.respond = model_reply([{'message': 1, 'layer': 'user_fact', 'subject': "Boss's assistant",
                                     'value': 'Priya, the assistant who runs the office'}])
    send(client, 'my boss has a new assistant, Priya, the assistant who runs the office now', 'model-0001')
    run(client, app)
    [memory] = client.get('/api/memories').json()
    assert (memory['subject'], memory['value']) == ("Boss's assistant", 'Priya, the assistant who runs the office')


def test_memories_an_earlier_prompt_called_the_assistant_get_the_name(client, app, connected, provider, monkeypatch):
    from companion.memory import addressed, suggest
    enable(client)
    provider.respond = model_reply([{'message': 1, 'layer': 'relationship', 'subject': 'Trust in assistant',
                                     'value': "didn't feel afraid of the assistant as if it were dangerous"}])
    send(client, MEETUP, 'model-0001')
    database = app.state.database
    monkeypatch.setattr(addressed, 'fields', lambda subject, value, *args: (subject, value))
    monkeypatch.setattr(addressed, 'voiced', lambda layer, value, message, name='': value)
    run(client, app)
    monkeypatch.undo()
    with database.connect(write=True) as connection:
        connection.execute("UPDATE memory_candidates SET rule='memory-suggest-5' WHERE source='model'")
    assert [memory['subject'] for memory in client.get('/api/memories').json()] == ['Trust in assistant']
    suggest.tidy(database)
    [memory] = client.get('/api/memories').json()
    assert (memory['subject'], memory['value']) == ('Trust in Mira', "You didn't feel afraid of Mira as if they were dangerous")
    assert addressed.tidy(database) == 0


def test_a_title_with_no_message_left_behind_it_still_gets_the_name(client, app, connected, provider, monkeypatch):
    from companion.memory import addressed, suggest
    enable(client)
    provider.respond = model_reply([{'message': 1, 'layer': 'relationship', 'subject': 'Trust in assistant',
                                     'value': "didn't feel afraid of Mira"}])
    send(client, MEETUP, 'model-0001')
    database = app.state.database
    monkeypatch.setattr(addressed, 'fields', lambda subject, value, *args: (subject, value))
    run(client, app)
    monkeypatch.undo()
    with database.connect(write=True) as connection:  # a later revision an older app saved: no candidate points at it
        connection.execute('DELETE FROM memory_candidates')
    suggest.tidy(database)
    assert [memory['subject'] for memory in client.get('/api/memories').json()] == ['Trust in Mira']
    assert addressed.tidy_titles(database) == 0
    assert addressed.title("Boss's assistant", 'Mira') == "Boss's assistant"
    assert addressed.title('Talks to the assistant at work', 'Mira') == 'Talks to the assistant at work'


def test_you_becomes_the_name_in_plain_english():
    from companion.memory.addressed import named
    cases = {"you're the one I trust": 'Mira is the one you trust',
             "glad you've been honest": 'glad Mira has been honest',
             'feel safe when you are around': 'feel safe when Mira is around',
             'you make me laugh': 'Mira makes you laugh',
             "you don't judge, you never judge": "Mira doesn't judge, Mira never judges",
             'you came along to the dentist': 'Mira came along to the dentist',
             'thank you for listening': 'thank Mira for listening',
             'likes your laugh': "likes Mira's laugh",
             "didn't feel afraid of the assistant as if it were dangerous":
                 "didn't feel afraid of Mira as if they were dangerous",
             'trusts the assistant because it is kind': 'trusts Mira because they are kind',
             'love you very much': 'love Mira very much',
             'know you better now': 'know Mira better now',
             "you'd been drinking": 'Mira had been drinking',
             "you'd know": 'Mira would know',
             'you yourself said it': 'Mira said it'}
    assert {text: named(text, 'Mira', 'a message') for text in cases} == cases


def test_the_assistants_it_takes_the_companions_pronouns():
    from companion.memory.addressed import named
    text = "didn't feel afraid of the assistant as if it were dangerous, because it is kind"
    assert named(text, 'Sett', 'a message', 'he') == "didn't feel afraid of Sett as if he were dangerous, because he is kind"
    assert named(text, 'Ana', 'a message', 'she') == "didn't feel afraid of Ana as if she were dangerous, because she is kind"
    assert named(text, 'Jo', 'a message') == "didn't feel afraid of Jo as if they were dangerous, because they are kind"


def test_a_plan_with_two_people_in_it_says_who():
    from companion.memory.addressed import voiced
    said = "I'll delete your number and not contact you. I won't text you tomorrow before you text first. I trust you"
    cases = {('plan', "will delete Sett's number and not contact them"): "You will delete Sett's number and not contact them",
             ('plan', "won't text tomorrow before Sett texts first"): "You won't text tomorrow before Sett texts first",
             ('relationship', 'has allowed Sett to give a nickname'): 'You have allowed Sett to give a nickname',
             ('relationship', 'trusts Sett more than anyone'): 'You trust Sett more than anyone',
             ('plan', 'dinner with Sett on Friday'): 'dinner with Sett on Friday',
             ('plan', 'Sett will pick up the user'): 'Sett will pick up the user',
             ('user_fact', 'will move to Denver'): 'will move to Denver'}
    assert {key: voiced(*key, said) for key in cases} == cases


def test_the_companion_reads_a_voiced_plan_as_the_users():
    from companion.memory.records import as_told
    row = {'layer': 'plan', 'origin': 'automatic', 'subject': 'Contacting Sett',
           'value': "You won't text tomorrow before Sett texts first"}
    assert as_told(row, 'Sett') == {**row, 'subject': 'Contacting you',
                                    'value': "The user won't text tomorrow before you text first"}
    trust = {'layer': 'relationship', 'origin': 'automatic', 'subject': 'Trust in Sett',
             'value': 'You trust Sett more than anyone'}
    assert as_told(trust, 'Sett')['value'] == 'The user trusts you more than anyone'


def test_them_becomes_the_companions_pronoun_only_when_they_are_the_one_named():
    from companion.memory.addressed import named
    assert named("will delete Sett's number and not contact them", 'Sett', 'a message', 'he') == \
        "will delete Sett's number and not contact him"
    assert named('Sett said they are moving and their flat is nice', 'Sett', 'a message', 'she') == \
        'Sett said she is moving and her flat is nice'
    assert named("will tell Mom about Sett and ask them over", 'Sett', 'a message', 'he') == \
        "will tell Mom about Sett and ask them over"
    assert named('will introduce Sett to Jo and see them both', 'Sett', 'a message', 'he') == \
        'will introduce Sett to Jo and see them both'
    assert named("will delete Sett's number and not contact them", 'Sett', 'a message') == \
        "will delete Sett's number and not contact them"


SHORT = "honestly short replies from you make me wonder if you're mad at me"


def test_the_user_is_you_in_a_memory_from_their_message():
    """Vanta on 1.3.2: "short replies from Sett make him wonder if Sett is mad at him", "helping the user feel
    comfortable"; the companion's own pronoun is never put in for the user."""
    from companion.memory.addressed import named
    cases = {('short replies from you make them wonder if you are mad at them', SHORT):
             'short replies from Sett make you wonder if Sett is mad at you',
             ("short replies from you make me wonder if you're mad at me", SHORT):
             'short replies from Sett make you wonder if Sett is mad at you',
             ("Sett managed gently around the girls, helping the user feel comfortable", 'it helped me feel safe'):
             'Sett managed gently around the girls, helping you feel comfortable',
             ('the user feels safe when Sett is around', 'I feel safe when you are around'):
             'you feel safe when Sett is around',
             ("The user's mom likes Sett", 'my mom likes you'): 'Your mom likes Sett',
             ("I'm proud when Sett holds my hand, I am happy", 'x'): "You're proud when Sett holds your hand, you are happy",
             ("Sett remembered their sister's name", "you remembered my sister's name"):
             "Sett remembered your sister's name",
             ("will delete Sett's number and not contact them", "I'll delete your number and not contact you"):
             "will delete Sett's number and not contact him",
             ("won't text Sett until they text first", "I won't text you until you text me first"):
             "won't text Sett until he texts first",
             ('Sett said they are moving, I think', "you're moving? I think that's great"):
             'Sett said he is moving, you think'}
    assert {key: named(key[0], 'Sett', key[1], 'he') for key in cases} == cases


def test_a_second_verb_after_you_agrees():
    from companion.memory.addressed import voiced
    said = "I don't need gifts from you to want you to stay, I just like having you around"
    assert voiced('relationship', "You like having Sett around and doesn't need gifts", said) == \
        "You like having Sett around and don't need gifts"
    assert voiced('relationship', "doesn't need gifts from Sett, just likes having Sett around", said) == \
        "You don't need gifts from Sett, you just like having Sett around"
    gentle = "you were so gentle around the girls tonight, it helped me feel comfortable"
    assert voiced('relationship', 'was gentle around the girls, helped you feel comfortable', gentle, 'Sett') == \
        'Sett was gentle around the girls, helped you feel comfortable'
    assert voiced('relationship', 'was gentle around the girls', gentle) == 'was gentle around the girls'
    assert voiced('relationship', "You like Sett and Sett is kind, and gives", said) == \
        "You like Sett and Sett is kind, and gives"


def test_the_companion_reads_you_in_a_relationship_memory_as_the_user():
    from companion.memory.records import as_told
    row = {'layer': 'relationship', 'origin': 'automatic', 'subject': "Sett's short replies",
           'value': 'short replies from Sett make you wonder if Sett is mad at you'}
    assert as_told(row, 'Sett')['value'] == 'Short replies from you make the user wonder if you are mad at the user'
    plan = {'layer': 'plan', 'origin': 'automatic', 'subject': 'Pick up', 'value': 'can you pick me up Friday'}
    assert as_told(plan, 'Sett') == plan


def test_saved_memories_get_the_user_as_you_once(client, app, connected, provider, monkeypatch):
    from companion.memory import addressed, suggest
    enable(client)
    provider.respond = model_reply([{'message': 1, 'layer': 'relationship', 'subject': "Mira's short replies",
                                     'value': 'short replies from Mira make him wonder if Mira is mad at him'},
                                    {'message': 1, 'layer': 'relationship', 'subject': 'Worry',
                                     'value': 'Mira being mad worries the user'}])
    send(client, f'{SHORT}, I always overthink it', 'model-0001')
    database = app.state.database
    monkeypatch.setattr(addressed, 'fields', lambda subject, value, *args: (subject, value))
    monkeypatch.setattr(addressed, 'voiced', lambda layer, value, message, name='': value)
    run(client, app)
    monkeypatch.undo()
    with database.connect(write=True) as connection:
        connection.execute("UPDATE memory_candidates SET rule='memory-suggest-7' WHERE source='model'")
    suggest.tidy(database)
    values = sorted(memory['value'] for memory in client.get('/api/memories').json())
    assert values == ['Mira being mad worries you', 'short replies from Mira make you wonder if Mira is mad at you']
    assert addressed.tidy_yours(database) == 0


def test_a_plan_the_model_finds_takes_its_day_from_the_message(client, app, connected, provider, clock):
    """Tester on 1.3.0: "give them both a bath this weekend" stayed in Plans long after the weekend."""
    enable(client)
    provider.respond = model_reply([{'message': 1, 'layer': 'plan', 'subject': 'Bathing',
                                     'value': 'give them both a bath'}])
    send(client, "I'll give them both a bath this weekend, they smell like the garden", 'model-plan-01')
    run(client, app)
    [memory] = [item for item in client.get('/api/memories').json() if item['subject'] == 'Bathing']
    assert memory['applies_from'] is not None and memory['plan_status'] == 'proposed'
    clock.advance(timedelta(days=10))
    client.app.state.life.spread_news()
    [memory] = [item for item in client.get('/api/memories').json() if item['subject'] == 'Bathing']
    assert memory['plan_status'] == 'completed'
