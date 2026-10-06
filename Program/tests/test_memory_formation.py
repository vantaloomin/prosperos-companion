"""Automatic extraction, suggestions and the per-message memory controls (PRD M7, M12)."""
from datetime import UTC, datetime, timedelta

from conftest import send

from companion.memory import extraction
from companion.memory.formation import run_pending
from companion.providers.chat import Chunk


def enable(client, **flags):
    response = client.put('/api/settings', json={'automatic_memory': True, **flags})
    assert response.status_code == 200, response.text


def run(client):
    response = client.post('/api/memory/run')
    assert response.status_code == 200, response.text
    return response.json()


def memories(client, history=False):
    return client.get('/api/memories', params={'history': history}).json()


def values(client):
    return {(item['subject'], item['value']) for item in memories(client)}


def test_nothing_is_extracted_while_automatic_memory_is_off(client, connected):
    send(client, 'I live in Chicago', 'client-0001')
    assert run(client)['processed'] == 0
    assert memories(client) == []


def test_stated_facts_are_committed_with_their_source(client, connected):
    enable(client)
    message = send(client, 'I live in Chicago. My favourite tea is genmaicha.', 'client-0001')['message']
    assert run(client) == {'processed': 1, 'done': 1}
    found = {item['subject']: item for item in memories(client)}
    assert found['Home city']['value'] == 'Chicago'
    assert found['Home city']['origin'] == 'automatic'
    assert found['Home city']['source_message_ids'] == [message['id']]
    assert found['Favourite tea']['value'] == 'genmaicha'
    actions = [row['action'] for row in client.get('/api/memory/activity').json()]
    assert actions.count('committed') == 2 and actions.count('extracted') == 2
    assert 'Chicago' not in str(client.get('/api/memory/activity').json())


def test_questions_hypotheticals_quotes_and_roleplay_are_not_facts(client, connected):
    enable(client)
    for index, text in enumerate(['Hypothetically, I live on the moon', 'Do I live in Paris?',
                                  'My friend said "I live in Rome"', '*stretches* I live in Narnia',
                                  'If I lived in Oslo I would be cold', 'Imagine I work as a pilot']):
        send(client, text, f'client-{index:04d}')
    run(client)
    assert memories(client) == []


def test_companion_text_cannot_become_a_user_fact(client, connected, provider):
    provider.replies = [[Chunk('You probably live in Paris.'), Chunk('', 'stop')]]
    reply = send(client, 'Guess where I am', 'client-0001')['reply']
    assert client.post(f"/api/conversation/messages/{reply['id']}/remember").status_code == 422
    enable(client)
    run(client)
    assert memories(client) == []


def test_sensitive_facts_wait_for_permission(client, connected):
    enable(client)
    send(client, "I'm allergic to peanuts", 'client-0001')
    run(client)
    assert memories(client) == []
    [suggestion] = client.get('/api/memory/suggestions').json()
    assert suggestion['reason'] == 'sensitive' and suggestion['value'] == 'peanuts'
    accepted = client.post(f"/api/memory/suggestions/{suggestion['id']}/accept").json()
    assert accepted['outcome'] == 'committed' and accepted['memory']['sensitive'] is True
    assert accepted['memory']['origin'] == 'suggestion'
    assert client.get('/api/memory/suggestions').json() == []


def test_sensitive_permission_commits_directly(client, connected):
    enable(client, sensitive_memory=True)
    send(client, "I'm allergic to peanuts", 'client-0001')
    run(client)
    assert values(client) == {('Allergy', 'peanuts')}


def test_a_declined_suggestion_is_not_offered_again(client, connected):
    enable(client)
    send(client, "I'm allergic to peanuts", 'client-0001')
    run(client)
    [suggestion] = client.get('/api/memory/suggestions').json()
    client.post(f"/api/memory/suggestions/{suggestion['id']}/decline")
    send(client, "As I said, I'm allergic to peanuts", 'client-0002')
    run(client)
    assert client.get('/api/memory/suggestions').json() == []
    assert client.post(f"/api/memory/suggestions/{suggestion['id']}/accept").status_code == 409


def test_turning_automatic_memory_off_stops_queued_jobs(client, connected):
    enable(client)
    send(client, 'I live in Chicago', 'client-0001')
    client.put('/api/settings', json={'automatic_memory': False})
    assert run(client) == {'processed': 1, 'stale': 1}
    enable(client)
    assert run(client)['processed'] == 0
    assert memories(client) == []


def test_dont_remember_blocks_extraction_and_keeps_the_transcript(client, connected):
    enable(client)
    message = send(client, 'I live in Chicago', 'client-0001')['message']
    result = client.post(f"/api/conversation/messages/{message['id']}/decline-memory").json()
    assert result['declined'] is True
    assert run(client) == {'processed': 0}
    assert client.get('/api/memory/status').json()['jobs'] == {'skipped': 1}
    assert memories(client) == []
    texts = [item['text'] for item in client.get('/api/conversation').json()['messages']]
    assert 'I live in Chicago' in texts


def test_dont_remember_removes_what_was_extracted_automatically(client, connected):
    enable(client)
    message = send(client, 'I live in Chicago', 'client-0001')['message']
    run(client)
    [memory] = memories(client)
    result = client.post(f"/api/conversation/messages/{message['id']}/decline-memory").json()
    assert result['removed_memory_ids'] == [memory['id']]
    assert memories(client, history=True) == []
    assert 'Chicago' not in client.get('/api/context/preview').json()['system']


def test_remember_this_works_with_automatic_memory_off(client, connected):
    message = send(client, "I'm allergic to peanuts and my name is Sam", 'client-0001')['message']
    result = client.post(f"/api/conversation/messages/{message['id']}/remember").json()
    assert {(item['subject'], item['value']) for item in result['memories']} == {
        ('Allergy', 'peanuts'), ('Preferred name', 'Sam')}
    assert result['draft'] is None


def test_remember_this_offers_a_draft_when_nothing_matches(client, connected):
    message = send(client, 'Today was the best day at the lake', 'client-0001')['message']
    result = client.post(f"/api/conversation/messages/{message['id']}/remember").json()
    assert result['memories'] == []
    assert result['draft'] == {'layer': 'shared_experience', 'subject': 'Something you told me',
                               'value': 'Today was the best day at the lake', 'source_message_ids': [message['id']]}


def test_remember_this_lifts_an_earlier_decline(client, connected):
    message = send(client, 'I live in Chicago', 'client-0001')['message']
    client.post(f"/api/conversation/messages/{message['id']}/decline-memory")
    client.post(f"/api/conversation/messages/{message['id']}/remember")
    assert values(client) == {('Home city', 'Chicago')}


def test_a_failed_extraction_leaves_the_conversation_intact(client, connected, monkeypatch):
    enable(client)
    send(client, 'I live in Chicago', 'client-0001')

    def broken(*_args):
        raise ValueError('boom')

    monkeypatch.setattr(extraction, 'extract', broken)
    assert run(client) == {'processed': 1, 'failed': 1}
    assert memories(client) == []
    assert len(client.get('/api/conversation').json()['messages']) == 2
    assert client.get('/api/memory/status').json()['jobs'] == {'failed': 1}


def test_an_added_fact_does_not_withhold_a_reply_in_progress(client, app, connected, provider):
    enable(client)
    send(client, 'I live in Chicago', 'client-0001')
    provider.before_finish = lambda: run_pending(app.state.database)
    reply = send(client, 'How are you?', 'client-0002')['reply']
    assert reply['status'] == 'complete'
    assert values(client) == {('Home city', 'Chicago')}


def test_a_move_ends_the_previous_home_during_a_reply_and_withholds_it(client, app, connected, provider):
    enable(client)
    send(client, 'I live in Chicago', 'client-0001')
    run(client)
    send(client, 'I moved to Boston', 'client-0002')
    provider.before_finish = lambda: run_pending(app.state.database)
    reply = send(client, 'Anyway', 'client-0003')['reply']
    assert reply['status'] == 'withheld'


def test_setting_a_date_answers_an_uncertain_one(client, connected):
    enable(client)
    send(client, "I'm going to Lisbon in a few weeks", 'client-0001')
    run(client)
    [plan] = memories(client)
    assert plan['dates_uncertain'] is True
    assert 'dates uncertain' in client.get('/api/context/preview').json()['system']
    fixed = client.post(f"/api/memories/{plan['id']}/correct", json={
        'value': plan['value'], 'applies_from': '2026-11-12T15:00:00Z', 'expected_revision': plan['revision']}).json()
    assert fixed['dates_uncertain'] is False and fixed['applies_from'].startswith('2026-11-12')
    assert 'dates uncertain' not in client.get('/api/context/preview').json()['system']


def test_a_contradiction_that_does_not_say_it_changed_waits_for_the_user(client, connected):
    enable(client)
    send(client, 'I live in Chicago', 'client-0001')
    run(client)
    send(client, 'I live in Denver', 'client-0002')
    run(client)
    assert values(client) == {('Home city', 'Chicago')}, 'Chicago stays current until the user says which holds'
    [suggestion] = client.get('/api/memory/suggestions').json()
    assert (suggestion['reason'], suggestion['value'], suggestion['replaces']) == ('conflict', 'Denver', ['Chicago'])
    client.post(f"/api/memory/suggestions/{suggestion['id']}/accept")
    homes = {item['value']: item for item in memories(client)}
    assert homes['Denver']['current'] is True and homes['Chicago']['ended_by_id'] == homes['Denver']['id']


def test_a_stated_change_or_a_deliberate_remember_replaces_directly(client, connected, clock):
    enable(client)
    send(client, 'My favourite tea is genmaicha', 'client-0001')
    run(client)
    clock.advance(timedelta(days=1))
    send(client, 'My favourite tea is hojicha now', 'client-0002')
    run(client)
    assert [item['value'] for item in memories(client) if item['current']] == ['hojicha']
    message = send(client, 'I live in Oslo', 'client-0003')['message']
    send(client, 'I live in Bergen', 'client-0004')
    client.post(f"/api/conversation/messages/{message['id']}/remember")
    assert ('Home city', 'Oslo') in values(client)


def test_a_named_relative_visiting_forms_the_person_and_the_dated_plan(client, connected):
    enable(client)
    send(client, 'My sister Jo is visiting next Saturday.', 'client-0001')
    run(client)
    found = {item['subject']: item for item in memories(client)}
    assert found['Sister']['value'] == 'Jo'
    visit = found['Visit from Jo']
    assert visit['layer'] == 'plan' and visit['plan_status'] == 'agreed' and visit['applies_from']
    send(client, 'My visit got cancelled.', 'client-0002')
    run(client)
    assert {item['subject']: item for item in memories(client)}['Visit from Jo']['plan_status'] == 'cancelled'


def test_words_after_a_relation_that_are_not_names_are_ignored():
    stated = datetime(2026, 10, 5, 12, tzinfo=UTC)
    for text in ('My sister Saturday is visiting.', "My dad I'm sure is fine."):
        assert not [item for item in extraction.extract(text, stated, 'UTC') if item.rule == 'relation']
