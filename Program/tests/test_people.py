"""The people in the user's life: learned from what the user says, remembered, and asked about now and then."""
from datetime import UTC, datetime, timedelta

from conftest import send

from companion.memory import extraction

STATED = datetime(2026, 10, 5, 12, tzinfo=UTC)


def found(text, known=None):
    return [(item.subject, item.value) for item in extraction.extract(text, STATED, 'UTC', known, ('mira',))
            if item.rule.startswith('person_')]


def test_people_and_facts_about_them_are_found_by_rules():
    assert found('My sister Jo just got engaged! She loves climbing. Her birthday is May 3.') == [
        ('Sister', 'Jo'), ('Jo: News', 'got engaged'), ('Jo: Likes', 'climbing'), ('Jo: Birthday', 'May 3')]
    assert found('My mum lives in Cork.') == [('Your mum: Home city', 'Cork')]
    assert found('Jo works at the Royal Library.', {'Jo': 'sister'}) == [('Jo: Work', 'Royal Library')]
    assert found('Sam is my best friend.') == [('Best friend', 'Sam')]
    assert found('I have a dog called Rex. He is 5.') == [('Dog', 'Rex'), ('Rex: Age', '5')]


def test_a_move_for_work_also_records_the_work():
    assert found('My brother Theo just moved to Denver for a nursing job.') == [
        ('Brother', 'Theo'), ('Theo: Home city', 'Denver'), ('Theo: Work', 'nursing job')]
    assert found('Theo moved to Denver to work as a nurse.', {'Theo': 'brother'})[-1] == ('Theo: Work', 'nurse')
    assert found('Theo moved to Denver to work at the Royal Hospital.', {'Theo': 'brother'})[-1] == (
        'Theo: Work', 'Royal Hospital')
    # No job is named here, so only the move is kept.
    assert found('Theo moved to Denver for work.', {'Theo': 'brother'}) == [('Theo: Home city', 'Denver')]
    assert found('Jo moved to York for a new job.', {'Jo': 'sister'}) == [('Jo: Home city', 'York')]


def test_details_in_contractions_and_and_clauses_are_kept():
    assert ('Dana: Likes', 'jellyfish') in found(
        "My sister Dana is visiting next Saturday. she's obsessed with jellyfish")
    assert ('Biscuit: Dislikes', 'the vacuum') in found('My cat is called Biscuit and she hates the vacuum')
    assert ('Tom: Has', 'a new dog') in found("My brother Tom moved. He's got a new dog")


def test_vague_or_unreal_mentions_are_not_people():
    for text in ('My friend loves cake.', 'My boss is an idiot.', 'Does my sister Jo live in Leeds?',
                 'Hypothetically, my sister Jo lives on the moon.', 'My friend said "Jo lives in Rome".',
                 'Jo works at the bank.', 'Mira is my best friend.', 'My sister Saturday is visiting.'):
        assert found(text) == [], text


def test_a_loss_is_sensitive():
    [item] = [item for item in extraction.extract('My grandad passed away last week.', STATED, 'UTC')
              if item.rule == 'person_news']
    assert item.sensitive


def enable(client, **flags):
    assert client.put('/api/settings', json={'automatic_memory': True, **flags}).status_code == 200


def say(client, text, counter=[0]):
    counter[0] += 1
    result = send(client, text, f'people-{counter[0]:05d}')
    assert client.post('/api/memory/run').status_code == 200
    return result


def people_section(client) -> str:
    system = client.get('/api/context/preview').json()['system']
    start = system.find("## People in the user's real life")
    return '' if start < 0 else system[start:].split('\n## ', 1)[0]


def test_nothing_about_people_is_kept_without_automatic_memory(client, connected):
    client.put('/api/settings', json={'automatic_memory': False})
    say(client, 'My sister Jo just got engaged.')
    assert client.get('/api/people').json() == []


def test_people_are_remembered_and_shown_to_the_companion(client, connected):
    enable(client)
    say(client, 'My sister Jo just got engaged. She loves climbing.')
    say(client, 'Jo works as a nurse.')
    say(client, 'My mum lives in Cork.')
    people = {person['label']: person for person in client.get('/api/people').json()}
    assert set(people) == {'Jo', 'Your mum'}
    assert people['Jo']['relation'] == 'sister' and len(people['Jo']['memory_ids']) == 4
    memories = {item['subject']: item for item in client.get('/api/memories').json()}
    assert memories['Jo: Work']['person_id'] == people['Jo']['id']
    text = people_section(client)
    assert "- Jo (the user's sister): work: nurse; likes: climbing; news (told you 2026-10-05): got engaged" in text
    assert "The user's mum (name not known yet): home city: Cork" in text
    assert 'Jo' not in client.get('/api/context/preview').json()['system'].split("## What you know about the user")[-1] \
        .split('## ')[0]


def test_a_name_learned_later_joins_the_same_person(client, connected):
    enable(client)
    say(client, 'I have a sister.')
    say(client, 'My sister lives in Leeds.')
    say(client, 'My sister Ana is visiting next Saturday.')
    [person] = client.get('/api/people').json()
    assert person['name'] == 'Ana'
    subjects = {item['subject']: item['value'] for item in client.get('/api/memories').json()}
    assert subjects['Ana: Home city'] == 'Leeds' and subjects['Sister'] == 'Ana'


def test_a_different_home_without_a_change_word_waits(client, connected):
    enable(client)
    say(client, 'My sister Jo lives in Leeds.')
    say(client, 'Jo lives in York.')
    [suggestion] = client.get('/api/memory/suggestions').json()
    assert suggestion['reason'] == 'conflict' and suggestion['replaces'] == ['Leeds']
    say(client, 'Jo moved to York.')
    homes = [item['value'] for item in client.get('/api/memories').json() if item['subject'] == 'Jo: Home city'
             and item['current']]
    assert homes == ['York']


def test_correcting_renaming_and_forgetting_a_person(client, connected, app):
    enable(client)
    say(client, 'My best friend Sam loves jazz.')
    [person] = client.get('/api/people').json()
    renamed = client.put(f"/api/people/{person['id']}", json={'name': 'Samantha'}).json()
    assert renamed['label'] == 'Samantha'
    subjects = {item['subject'] for item in client.get('/api/memories').json()}
    assert subjects == {'Best friend', 'Samantha: Likes'}
    result = client.post(f"/api/people/{person['id']}/delete").json()
    assert len(result['deleted_memory_ids']) >= 2
    assert client.get('/api/people').json() == [] and client.get('/api/memories').json() == []
    assert 'Sam' not in people_section(client)


def test_deleting_the_last_memory_removes_the_person(client, connected):
    enable(client)
    say(client, 'My mum lives in Cork.')
    [memory] = client.get('/api/memories').json()
    client.post(f"/api/memories/{memory['id']}/delete", json={'delete_sources': False})
    assert client.get('/api/people').json() == []


def test_adding_someone_by_hand(client, connected):
    person = client.post('/api/people', json={'name': 'Priya', 'relation': 'Coworker'}).json()
    assert person['relation'] == 'coworker'
    assert [(item['subject'], item['value']) for item in client.get('/api/memories').json()] == [('Coworker', 'Priya')]
    assert client.post('/api/people', json={}).status_code == 422


def test_a_follow_up_question_is_offered_rarely_and_once(client, connected, clock, provider):
    enable(client)
    say(client, 'My sister Jo just got engaged.')
    assert 'A question you could ask' not in people_section(client), 'news is too fresh to ask about yet'
    clock.advance(timedelta(days=1))
    assert 'Jo got engaged (the user told you on 2026-10-05)' in people_section(client)
    say(client, 'Morning!')
    assert 'A question you could ask' in provider.requests[-1]['system']
    # Offered once: not again in the next replies, and never the same question twice.
    say(client, 'How are you?')
    assert 'A question you could ask' not in provider.requests[-1]['system']
    clock.advance(timedelta(days=2))
    say(client, 'Hello again')
    assert 'got engaged (the user told you' not in provider.requests[-1]['system']


def test_no_questions_after_a_loss_behind_a_boundary_or_when_turned_off(client, connected, clock):
    enable(client, sensitive_memory=True)
    say(client, 'My grandad passed away last week.')
    say(client, 'My brother Leo just got promoted.')
    say(client, "Please don't bring up my brother.")
    clock.advance(timedelta(days=1))
    text = people_section(client)
    assert 'Leo' in text and 'A question you could ask' not in text
    say(client, 'My aunt Rosa just got married.')
    clock.advance(timedelta(days=1))
    assert 'Rosa got married' in people_section(client)
    client.put('/api/settings', json={'ask_about_people': False})
    assert 'A question you could ask' not in people_section(client)


def test_asking_for_a_missing_name(client, connected, clock):
    enable(client)
    say(client, 'My boss loves golf.')
    assert "the name of the user's boss" in people_section(client)
