"""Next steps (companion/life/steps.py): the ladder, asks either way, a friend falling for you, and the Character page."""
from datetime import date, timedelta

import pytest
from conftest import reconcile, send, set_life

from companion import consequences
from companion.characters import current
from companion.life import occasions, steps
from companion.providers.chat import Chunk


def test_answers_are_read_from_the_message():
    assert steps.answer('yes!! of course') == 'yes'
    assert steps.answer('I love you too') == 'yes'
    assert steps.answer("I'd love that") == 'yes'
    assert steps.answer("I'm not ready yet, can we wait a bit?") == 'not_yet'
    assert steps.answer('maybe later?') == 'not_yet'
    assert steps.answer("no, I'd rather stay friends") == 'no'
    assert steps.answer("I don't feel the same, sorry") == 'no'
    assert steps.answer('how was work?') is None


def test_answers_are_not_misread():
    # E2E v0.13: excitement read as no, a hesitation or a plain refusal read as yes, "no" in passing read as no.
    assert steps.answer("I can't wait! Yes!") == 'yes'
    assert steps.answer('oh no, of course I will') == 'yes'
    assert steps.answer('No pressure, but yes') == 'yes'
    assert steps.answer("I'm not sure") == 'not_yet'
    assert steps.answer('I need to think about it') == 'not_yet'
    for text in ('Absolutely not', 'of course not', 'definitely not.', "I can't, sorry", 'no way'):
        assert steps.answer(text) == 'no', text
    assert steps.answer('I have no idea what to cook tonight') is None


def test_steps_brought_up_are_read_from_the_message():
    assert steps.raised('Can we be exclusive?', ['exclusive', 'love']) == 'exclusive'
    assert steps.raised('will you be my girlfriend?', ['exclusive']) == 'exclusive'
    assert steps.raised('I love you.', ['exclusive', 'love']) == 'love'
    assert steps.raised("I'd love to meet your family sometime", ['their_people']) == 'their_people'
    assert steps.raised('want a key to my place?', ['key']) == 'key'
    assert steps.raised("you're my best friend, you know that", ['best_friends']) == 'best_friends'
    assert steps.raised('we should take a trip together, just us?', ['trip']) == 'trip'
    for text in ('she said I love you to him', "I don't want to be exclusive", 'if I said I love you, what then',
                 'I love your cooking', 'be exclusive', 'they were exclusive last year?'):
        assert steps.raised(text, ['exclusive', 'love']) is None, text
    # Said sincerely, or as a plain wish: E2E v0.13.
    assert steps.raised('I just wanted to say I love you', ['exclusive', 'love']) == 'love'
    assert steps.raised('I have to tell you, I love you', ['exclusive', 'love']) == 'love'
    assert steps.raised('I think we should be exclusive', ['exclusive', 'love']) == 'exclusive'
    assert steps.raised('We should move in together', ['moving_in']) == 'moving_in'
    assert steps.raised('I told my mom I love you', ['exclusive', 'love']) is None
    assert steps.confessed('I think I have feelings for you')
    assert not steps.confessed("I don't have feelings for you")


def make(client, monkeypatch, relationship='romance', **values):
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'UTC', 'relationship': relationship,
                                                     **values})
    assert response.status_code == 200, response.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})


def view(client):
    response = client.get('/api/life/steps')
    assert response.status_code == 200, response.text
    return response.json()


def prompt(provider):
    return provider.requests[-1]['prompt']


def says(provider, text='Okay!'):
    provider.replies.append([Chunk(text), Chunk('', 'stop')])


def close(client, level):
    response = client.put('/api/closeness', json={'set_level': level})
    assert response.status_code == 200, response.text


def first_text(client, clock, key='step-message'):
    """The first text a step due today would send, saved the way openers.py saves it."""
    from companion.life import openers
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        found = [trigger for trigger in openers.candidates(connection, companion, clock.now())
                 if trigger.kind == 'next_step']
        if not found:
            return None
        trigger = found[0]
        connection.execute("INSERT INTO messages (id, timeline_id, seq, role, text, status, active, character_version_id, "
                           "memory_revision, created_at, completed_at) VALUES (?, ?, 99, 'companion', ?, 'complete', 1, ?, "
                           '0, ?, ?)', (key, companion['active_timeline_id'], trigger.template,
                                        companion['active_version_id'], clock.now().isoformat(), clock.now().isoformat()))
        connection.execute("INSERT INTO openers (id, timeline_id, trigger_key, kind, facts, message_id, wording, "
                           "created_at) VALUES (?, ?, ?, ?, '{}', ?, 'template', ?)",
                           (f'opener-{key}', companion['active_timeline_id'], trigger.key, trigger.kind, key,
                            clock.now().isoformat()))
        steps.settle(connection, companion, {'id': key}, trigger, clock.now().isoformat())
        return trigger


@pytest.fixture
def always(monkeypatch):
    """The engine lands on the first option every time."""
    monkeypatch.setattr(consequences, 'roll', lambda _seed, found: found[0]['option'])


def test_a_new_romance_starts_dating_and_the_chat_knows_where_things_stand(client, provider, monkeypatch):
    make(client, monkeypatch)
    found = view(client)
    assert found['ladder'] == 'romance' and found['step'] == 'dating' and found['next'] == 'exclusive'
    assert found['text'] == 'Dating for 1 day'
    says(provider)
    send(client, 'hey you', 'client-steps-1')
    assert 'Where things stand between you' in prompt(provider)
    assert 'You are dating: it is still early.' in prompt(provider)


def test_how_you_know_each_other_sets_the_start(client, monkeypatch):
    make(client, monkeypatch, history_together='We have been married for ten years and live in a little flat.')
    found = view(client)
    assert found['step'] == 'married' and found['text'] == 'Married'
    assert [item['how'] for item in found['steps']] == ['history'] * 8


def test_a_friend_close_from_the_start_is_a_best_friend(client, monkeypatch):
    make(client, monkeypatch, relationship='friendship', starting_closeness=5)
    assert view(client)['step'] == 'best_friends'


def test_mentors_and_family_have_no_ladder(client, provider, monkeypatch):
    make(client, monkeypatch, relationship='mentor')
    assert view(client)['ladder'] is None
    says(provider)
    send(client, 'hello', 'client-steps-2')
    assert 'Where things stand between you' not in prompt(provider)


def test_they_bring_up_the_next_step_and_yes_moves_it(client, provider, clock, monkeypatch, always):
    make(client, monkeypatch)
    monkeypatch.setattr(steps, 'FIRST_TEXTS', True)
    view(client)
    close(client, 3)
    clock.advance(timedelta(days=36))
    reconcile(client)
    found = client.get('/api/life/steps').json()
    assert found['step'] == 'dating'
    with client.app.state.database.connect() as connection:
        [planned] = steps.asks(connection, current(connection)['active_timeline_id'], ('planned',))
    assert planned['step'] == 'exclusive'
    clock.advance(timedelta(days=8))  # Soon is within a week.
    trigger = first_text(client, clock)
    assert trigger and 'exclusive' in trigger.reason and trigger.template in steps.bank()['exclusive']
    says(provider)
    send(client, 'yes!! of course I want that', 'client-steps-3')
    assert 'The user just said yes to being exclusive.' in prompt(provider)
    found = view(client)
    assert found['step'] == 'exclusive' and found['steps'][-1]['how'] == 'them'
    assert found['text'].startswith('Together ') and found['text'].endswith(', exclusive')


def test_not_yet_waits_and_no_answer_lapses(client, provider, clock, monkeypatch, always):
    make(client, monkeypatch)
    monkeypatch.setattr(steps, 'FIRST_TEXTS', True)
    view(client)
    close(client, 3)
    clock.advance(timedelta(days=36))
    reconcile(client)
    clock.advance(timedelta(days=8))
    assert first_text(client, clock)
    says(provider)
    send(client, "I'm not ready yet, can we take it slow?", 'client-steps-4')
    assert "The user just said they aren't ready for being exclusive yet." in prompt(provider)
    assert view(client)['step'] == 'dating'
    clock.advance(timedelta(days=10))
    reconcile(client)
    with client.app.state.database.connect() as connection:
        assert steps.asks(connection, current(connection)['active_timeline_id'], ('planned',)) == []


def test_you_bring_it_up_and_the_engine_answers(client, provider, clock, monkeypatch, always):
    make(client, monkeypatch)
    view(client)
    close(client, 3)
    clock.advance(timedelta(days=40))
    says(provider)
    send(client, 'I love you. Can we make this official?', 'client-steps-5')
    assert 'Your answer is yes' in prompt(provider)
    found = view(client)
    # "I love you" while only dating is being exclusive and in love at once.
    assert found['step'] == 'love' and [item['step'] for item in found['steps']] == ['dating', 'exclusive', 'love']


def test_too_soon_they_are_not_ready(client, provider, monkeypatch):
    make(client, monkeypatch)
    monkeypatch.setattr(consequences, 'roll', lambda _seed, found: max(found, key=lambda item: item['odds'])['option'])
    says(provider)
    send(client, 'can we be exclusive?', 'client-steps-6')
    assert "You aren't ready for that yet" in prompt(provider)
    assert view(client)['step'] == 'dating'


def test_a_friend_falls_for_you_and_yes_makes_it_a_romance(client, provider, clock, monkeypatch):
    make(client, monkeypatch, relationship='friendship')
    monkeypatch.setattr(steps, 'FIRST_TEXTS', True)
    monkeypatch.setattr(consequences, 'roll', lambda _seed, found: found[-1]['option'])
    view(client)
    close(client, 4)
    clock.advance(timedelta(days=95))
    reconcile(client)
    clock.advance(timedelta(days=28))
    reconcile(client)
    clock.advance(timedelta(days=13))
    trigger = first_text(client, clock)
    assert trigger and trigger.key.startswith('step-ask:') and 'fallen for the user' in trigger.reason
    says(provider)
    send(client, 'honestly? I feel the same', 'client-steps-7')
    companion = client.get('/api/companion').json()['companion']
    assert companion['version']['definition']['relationship'] == 'romance'
    assert 'they just said they feel the same' in prompt(provider)
    found = view(client)
    assert found['ladder'] == 'romance' and found['steps'][0]['how'] == 'confession'


def test_a_friend_told_no_stays_a_friend_after_an_awkward_spell(client, provider, clock, monkeypatch):
    make(client, monkeypatch, relationship='friendship')
    monkeypatch.setattr(steps, 'FIRST_TEXTS', True)
    monkeypatch.setattr(consequences, 'roll', lambda _seed, found: found[-1]['option'])
    view(client)
    close(client, 4)
    clock.advance(timedelta(days=95))
    reconcile(client)
    clock.advance(timedelta(days=28))
    reconcile(client)
    clock.advance(timedelta(days=13))
    assert first_text(client, clock)
    says(provider)
    send(client, "I'm sorry, I only see you as a friend", 'client-steps-8')
    assert client.get('/api/companion').json()['companion']['version']['definition']['relationship'] == 'friendship'
    says(provider)
    send(client, 'are we okay?', 'client-steps-9')
    assert 'Things have felt a little awkward' in prompt(provider)


def test_the_lock_and_the_switch_keep_a_friend_a_friend(client, clock, monkeypatch):
    make(client, monkeypatch, relationship='friendship')
    monkeypatch.setattr(consequences, 'roll', lambda _seed, found: found[-1]['option'])
    assert client.put('/api/life/steps', json={'just_friends': True}).json()['just_friends'] is True
    close(client, 4)
    clock.advance(timedelta(days=110))
    reconcile(client)
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        assert steps.asks(connection, companion['active_timeline_id'], ('planned',)) == []
        assert not steps.may_fall(connection, companion, clock.now())
    client.put('/api/life/steps', json={'just_friends': False})
    set_life(client, friends_fall=False)
    with client.app.state.database.connect() as connection:
        assert not steps.may_fall(connection, current(connection), clock.now())


def test_setting_the_step_on_the_character_page(client, monkeypatch):
    make(client, monkeypatch)
    found = client.put('/api/life/steps', json={'step': 'key'}).json()
    assert found['step'] == 'key' and [item['how'] for item in found['steps']] == ['start'] + ['set'] * 4
    assert found['text'].endswith('with a key to their place')
    found = client.put('/api/life/steps', json={'step': 'exclusive'}).json()
    assert found['step'] == 'exclusive' and len(found['steps']) == 2
    assert client.put('/api/life/steps', json={'step': 'nonsense'}).status_code == 422


def test_pace_off_means_only_when_you_bring_it_up(client, clock, monkeypatch, always):
    make(client, monkeypatch)
    set_life(client, steps_pace=0)
    close(client, 3)
    clock.advance(timedelta(days=60))
    reconcile(client)
    with client.app.state.database.connect() as connection:
        assert steps.asks(connection, current(connection)['active_timeline_id'], ('planned',)) == []


def test_each_step_is_an_anniversary_and_exclusive_is_known(client, clock, monkeypatch):
    make(client, monkeypatch)
    client.put('/api/life/steps', json={'step': 'exclusive'})
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        assert steps.exclusive(connection, companion, clock.now())
    clock.advance(timedelta(days=365))
    with client.app.state.database.connect() as connection:
        found = [item for item in occasions.occasions(connection, current(connection), clock.now())
                 if item['kind'] == 'step_anniversary']
    assert [item['text'] for item in found] == [
        f"- Today it has been a year since you and the user became exclusive ({date(2026, 10, 5):%d %B %Y})."]
    # Today says which step it was (E2E v0.13: it read "a year since you two started talking").
    assert (found[0]['did'], found[0]['span']) == ('became exclusive', 'a year')


def test_odds_show_only_with_hidden_values(client, provider, clock, monkeypatch, always):
    make(client, monkeypatch)
    view(client)
    close(client, 3)
    clock.advance(timedelta(days=40))
    says(provider)
    send(client, 'can we be exclusive?', 'client-steps-10')
    assert view(client)['asks'][0]['consequence_id'] is None
    client.put('/api/settings', json={'show_odds': True})
    [ask] = view(client)['asks']
    assert ask['status'] == 'yes' and ask['consequence_id']
    response = client.post(f"/api/life/consequences/{ask['consequence_id']}/change", json={'option': 1})
    assert response.status_code == 200, response.text
    assert view(client)['step'] == 'dating'


def test_each_reason_sits_under_the_answer_it_moved():
    """"Doesn't feel close enough yet" makes yes less likely, so it is listed under yes, which it lowered."""
    facts = {'pace': 2, 'sheet': set(), 'social': 1, 'closeness_over': 0, 'mood': 0, 'short_days': 0, 'skips': 0}
    plain, apart = (consequences.odds('steps:answer', dict(facts, closeness_over=value), {'name': 'Mira', 'step': 'x'})
                    for value in (0, -1))
    assert apart[0]['reasons'] == ["Mira doesn't feel close enough yet"] and apart[0]['odds'] < plain[0]['odds']
    assert apart[1]['reasons'] == []
    assert apart[0]['moves'] == ['less'], 'Today says "Less likely because Mira doesn\'t feel close enough yet"'
