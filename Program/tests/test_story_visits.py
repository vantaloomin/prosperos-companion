"""Scenes count (companion/story_visits.py): time with a companion in the Story is part of their life together."""
from datetime import timedelta

import pytest
from conftest import reconcile, send, set_life
from test_drop_by import SHIFTS
from test_story import ok, say
from test_story_cast import at_work, script
from test_together import mira

from companion import story_visits
from companion.life import steps
from companion.memory import records


@pytest.fixture
def barkeep(client, monkeypatch):
    mira(client, monkeypatch, schedule=SHIFTS)
    reconcile(client)


def talk(client, provider, lines=2, start=1):
    """Lines said to Mira at the bar, each answered by the narrator and then by her."""
    for number in range(start, start + lines):
        script(provider, 'The bar hums quietly.', f'Mira grins. "Round {number} is on me."')
        say(client, f'I lean on the bar. "Mira, tell me about your day, part {number}."', f'story-{number:04d}')


def leave(client):
    return ok(client.put('/api/story/scene', json={'city_id': 'baltimore', 'place_id': 'patterson-park'}))


def closeness(client):
    return ok(client.get('/api/closeness'))


def moments(client):
    return [memory for memory in ok(client.get('/api/memories')) if memory['layer'] == 'shared_experience']


def test_a_scene_with_a_companion_is_a_day_talked_and_leaves_a_shared_moment(client, barkeep, provider):
    assert closeness(client)['days_talked'] == 0
    at_work(client)
    talk(client, provider)
    # A day talked from the first line said to them; the moment is kept once the scene is over.
    assert closeness(client)['days_talked'] == 1 and moments(client) == []
    leave(client)
    found = moments(client)
    assert [(memory['subject'], memory['value'], memory['origin']) for memory in found] == [
        ('In person at Club Charles', 'Mira and you spent time together at Club Charles.', 'automatic')]
    assert found[0]['in_story'] is True
    assert closeness(client)['shared_moments'] == 1 and closeness(client)['days_talked'] == 1


def test_their_chat_knows_the_scene_happened_and_how_it_ended(client, barkeep, provider):
    at_work(client)
    talk(client, provider)
    leave(client)
    script(provider, 'It was good to see you.')
    send(client, 'that was fun', 'chat-0001')
    system = provider.requests[-1]['system'] + provider.requests[-1]['messages'][0]['content']
    assert 'Earlier today, around 12:00, the user came by Club Charles while you were at work there, and the two of ' \
           'you spent time together in person.' in system
    assert '  The user: I lean on the bar. "Mira, tell me about your day, part 2."\n' \
           '  You: Mira grins. "Round 2 is on me."' in system
    # The moment, as she reads it.
    assert records.as_told({**moments(client)[0]}, 'Mira')['value'] == \
        'You and the user spent time together at Club Charles.'
    # A day and a half on, it is a memory and no longer news.
    with client.app.state.database.connect() as connection:
        companion = story_visits.by_id(connection, ok(client.get('/api/story'))['companions'][0]['id'])
        later = client.app.state.database.clock.now() + timedelta(hours=40)
        assert story_visits.context_lines(connection, companion, later) == []


def test_one_line_is_not_a_moment_and_a_day_leaves_one(client, barkeep, provider):
    at_work(client)
    talk(client, provider, lines=1)
    leave(client)
    assert moments(client) == [] and closeness(client)['days_talked'] == 1
    at_work(client)
    talk(client, provider, lines=2, start=2)
    leave(client)
    at_work(client)
    talk(client, provider, lines=2, start=4)
    # A new story clears the lines, never the time they spent.
    ok(client.delete('/api/story'))
    assert len(moments(client)) == 1
    with client.app.state.database.connect() as connection:
        visits = story_visits.many(connection, 'SELECT * FROM story_visits ORDER BY started_at')
    assert [bool(visit['ended_at']) for visit in visits] == [True, True, True]
    assert visits[1]['memory_id'] == visits[2]['memory_id'] and visits[0]['memory_id'] is None
    assert [line['who'] for line in story_visits.decode(visits[2]['excerpt'])] == ['user', 'you', 'user', 'you']


def test_a_line_to_someone_else_or_out_of_the_story_does_not_count(client, barkeep, provider):
    at_work(client)
    script(provider, 'Nothing stirs.')
    say(client, 'OOC: what time is it in the story?', 'story-0001')
    assert closeness(client)['days_talked'] == 0


def test_a_step_can_be_reached_face_to_face(client, provider, monkeypatch):
    mira(client, monkeypatch, schedule=SHIFTS, relationship='romance')
    reconcile(client)
    monkeypatch.setattr(steps, 'decide', lambda *_args, **_more: {'picked': 0, 'id': None})
    before = ok(client.get('/api/life/steps'))
    assert before['step'] == 'dating'
    at_work(client)
    script(provider, 'The room goes quiet.', 'Mira sets the glass down. "Yes. Only you."')
    say(client, 'Mira, I think we should be exclusive.', 'story-0001')
    assert ok(client.get('/api/life/steps'))['step'] == 'exclusive'
    # Her own line is written knowing her answer.
    assert 'The user just brought up' in provider.requests[-1]['system'] + provider.requests[-1]['messages'][-1]['content']


def test_an_answer_in_person_must_name_the_step_or_follow_her_asking():
    ask = {'step': 'exclusive'}
    assert steps.answer_in_person(ask, 'Yes, let us be exclusive.', '') == 'yes'
    assert steps.answer_in_person(ask, 'yes!', '') is None
    assert steps.answer_in_person(ask, 'yes!', 'Would you want to be exclusive?') == 'yes'
    assert steps.answer_in_person(ask, 'not yet, sorry', 'I want us to be exclusive.') == 'not_yet'
    assert steps.answer_in_person(ask, 'yes, another round please', 'Another round?') is None
    # In a scene the words in quotation marks are the speech; in a text they are someone else's.
    assert steps.out_loud('Mira takes a breath. "Would you want to be exclusive?" She waits. "Well?"') == \
        'Would you want to be exclusive? Well?'
    assert steps.out_loud('I nod. Yes.') == 'I nod. Yes.'


def test_with_the_switch_off_the_story_stays_apart(client, barkeep, provider):
    set_life(client, story_counts=False)
    at_work(client)
    talk(client, provider)
    leave(client)
    assert closeness(client)['days_talked'] == 0 and moments(client) == []
    script(provider, 'Hello.')
    send(client, 'hi', 'chat-0001')
    assert 'in person' not in provider.requests[-1]['system'] + provider.requests[-1]['messages'][0]['content']
