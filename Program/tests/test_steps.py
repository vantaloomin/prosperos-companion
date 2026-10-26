"""Next steps (companion/life/steps.py): the ladder, asks either way, a friend falling for you, and the Character page."""
from datetime import timedelta

import pytest
from conftest import reconcile, send, set_life

from companion import consequences
from companion.characters import current
from companion.life import chapters, occasions, steps
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
    # Real model run (E2E v0.13): asked this way, the companion agreed but the app stayed at dating.
    for text in ('So does this mean we are courting properly now? Only each other?', 'are we exclusive now?',
                 'Should we be a couple?'):
        assert steps.raised(text, ['exclusive', 'love']) == 'exclusive', text
    assert steps.raised('we were only each other for years, back then', ['exclusive']) is None
    assert steps.confessed('I think I have feelings for you')
    assert not steps.confessed("I don't have feelings for you")


def make(client, monkeypatch, relationship='romance', **values):
    # The dice some tests force would also start a life chapter (caring for a parent), whose news takes the first text.
    monkeypatch.setattr(chapters, 'CHANCE', (0, 0, 0, 0))
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


def test_someone_you_have_not_met_is_not_a_friend_yet(client, provider, monkeypatch):
    # A tester making a companion they had not met: Friendship at Just met read "Friends for 1 day" and told the
    # companion "You are friends", so they picked "Something else" for everyone they did not know.
    make(client, monkeypatch, relationship='friendship')
    found = view(client)
    assert found['step'] == 'friends' and found['text'] == 'Met today' and found['not_yet'] == 1
    assert found['ladder_steps'][0] == {'step': 'friends', 'label': 'Just met'}
    says(provider)
    send(client, 'hi, I think we have not met?', 'client-steps-stranger')
    assert 'you are not friends yet, just two people starting to talk' in prompt(provider)
    assert 'You are friends.' not in prompt(provider) and 'Friends since' not in prompt(provider)
    close(client, 2)
    found = view(client)
    assert found['label'] == 'Getting to know each other' and found['text'] == 'Met today'
    close(client, 3)
    found = view(client)
    assert found['text'] == 'Friends for 1 day' and found['not_yet'] is None


def test_old_friends_are_friends_from_the_start(client, monkeypatch):
    make(client, monkeypatch, relationship='friendship', history_together='Old friends from school.')
    found = view(client)
    assert found['text'] == 'Friends' and found['not_yet'] is None


def test_how_you_know_each_other_sets_the_start(client, monkeypatch):
    make(client, monkeypatch, history_together='We have been married for ten years and live in a little flat.')
    found = view(client)
    assert found['step'] == 'married' and found['text'] == 'Married'
    assert [item['how'] for item in found['steps']] == ['history'] * 8


def test_closeness_that_goes_further_than_how_they_know_each_other_sets_the_start(client, monkeypatch):
    """"Dating for a year" between two who are as close as can be (an upgrade from before Next steps) starts them where
    their closeness says, not at being exclusive with "I love you" still unsaid."""
    make(client, monkeypatch, history_together='We have been dating for about a year.', starting_closeness=5)
    found = view(client)
    assert found['step'] == 'their_people' and found['text'] == 'Met their people'  # No "together 1 day".
    assert [item['how'] for item in found['steps']] == ['history'] * 4


def test_a_friend_close_from_the_start_is_a_best_friend(client, monkeypatch):
    make(client, monkeypatch, relationship='friendship', starting_closeness=5,
         history_together='Close since we met at a reading room three years ago.')
    found = view(client)
    # Not "Friends for 1 day": they knew each other long before the first talk (E2E v0.13).
    assert found['step'] == 'best_friends' and found['text'] == 'Best friends'
    assert [item['how'] for item in found['steps']] == ['history', 'history']


def test_a_match_from_the_dating_app_counts_from_the_first_talk(client, monkeypatch):
    make(client, monkeypatch, starting_closeness=3, history_together='Matched on Matchlight.')
    found = view(client)
    # A new romance at "Comfortable" is still dating, not "Together 1 day, exclusive" (E2E v0.13 N4).
    assert found['text'] == 'Dating for 1 day' and found['steps'][0]['how'] == 'start'


def test_a_romance_talking_a_few_weeks_at_comfortable_starts_exclusive(client, clock, monkeypatch):
    make(client, monkeypatch, starting_closeness=3)
    with client.app.state.database.connect(write=True) as connection:
        companion = current(connection)
        connection.execute('DELETE FROM relationship_steps WHERE timeline_id=?', (companion['active_timeline_id'],))
        monkeypatch.setattr(occasions, 'first_talk', lambda *_args: clock.now().date() - timedelta(days=20))
        assert [key for key, _how in steps.start(connection, companion, 'romance', clock.now())] == ['dating', 'exclusive']


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
    # Making their answer go the other way and back again brings back the step it skipped too (E2E v0.13).
    client.put('/api/settings', json={'show_odds': True})
    outcome = view(client)['asks'][0]['consequence_id']
    for option in (1, 0):
        assert client.post(f'/api/life/consequences/{outcome}/change', json={'option': option}).status_code == 200
    assert [item['step'] for item in view(client)['steps']] == ['dating', 'exclusive', 'love']


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


def test_making_a_friend_fall_for_you_puts_a_smaller_step_off(client, clock, monkeypatch, always):
    # E2E v0.13: "Make it go this way" on a month they stayed a friend planned the confession for the same day as the
    # first trip they were about to bring up.
    make(client, monkeypatch, relationship='friendship', starting_closeness=5)
    client.put('/api/settings', json={'show_odds': True})
    view(client)
    close(client, 5)
    clock.advance(timedelta(days=200))
    reconcile(client)
    with client.app.state.database.connect() as connection:
        timeline_id = current(connection)['active_timeline_id']
        assert [row['step'] for row in steps.asks(connection, timeline_id, ('planned',))] == ['trip']
        [falls] = [row['id'] for row in connection.execute("SELECT id FROM consequences WHERE choice='steps:falls'")]
    assert client.post(f'/api/life/consequences/{falls}/change', json={'option': 1}).status_code == 200
    with client.app.state.database.connect() as connection:
        assert [row['step'] for row in steps.asks(connection, timeline_id, ('planned',))] == ['confession']


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
        companion = current(connection)
        assert steps.asks(connection, companion['active_timeline_id'], ('planned',)) == []
        # Asked, they answer true to life, not slowly ("the relationship pace is slow" never shows).
        found = steps.state(connection, companion, clock.now(), write=False)
        facts = steps.facts(connection, companion, found, steps.step_of('romance', 'exclusive'), clock.now())
        assert facts['pace'] == 2 and facts['short_days'] == max(35 - facts['days'], 0)


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
        "- Today it has been a year since you and the user became exclusive (5 October 2026)."]
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


# The user's other romances (E2E v0.13 N2): "you only see each other" only when it is true for that companion ----------

def add_romance(client, name, created_at=None, **values):
    """Another romance companion, with a timeline of their own."""
    from companion.characters import insert_version
    from companion.database import identifier
    from companion.models import CharacterDefinition
    database = client.app.state.database
    created_at = created_at or database.now()
    with database.connect(write=True) as connection:
        other, timeline = identifier(), identifier()
        connection.execute('INSERT INTO companions (id, slot, stepped_back_at, created_at) VALUES (?, NULL, ?, ?)',
                           (other, created_at, created_at))
        connection.execute("INSERT INTO timelines (id, companion_id, status, created_at) VALUES (?, ?, 'active', ?)",
                           (timeline, other, created_at))
        version = insert_version(connection, other, 1, CharacterDefinition(
            name=name, personality='Easygoing.', timezone='UTC', relationship='romance', **values), '', created_at)
        connection.execute('UPDATE companions SET active_version_id=?, active_timeline_id=? WHERE id=?',
                           (version, timeline, other))
    return other, timeline


def standing(client, group=None) -> str:
    from companion.memory import context
    database = client.app.state.database
    with database.connect() as connection:
        companion = current(connection)
        if group is not None:
            built = context.build(connection, companion, database.clock.now(), 24000, group=group)
            return next(line for line in (built['system'] + built['note']).split('\n') if 'Keep to where things' in line)
        return steps.context_lines(connection, companion, database.clock.now(), set())[0][1]


@pytest.fixture
def minds(monkeypatch):
    """Rough patches on ("Exclusive minds"), every roll landing on a rough patch."""
    from companion.life import rough_patches
    monkeypatch.setattr(rough_patches, 'ACTIVE', True)
    monkeypatch.setattr(consequences, 'roll', lambda _seed, found: found[-1]['option'])
    return rough_patches


def test_alone_they_are_a_couple_and_say_so_plainly(client, monkeypatch):
    make(client, monkeypatch)
    client.put('/api/life/steps', json={'step': 'exclusive'})
    line = standing(client)
    assert 'You are exclusive: you are a couple and only see each other. If the user asks what you are, say so ' \
           'plainly.' in line


def test_other_romances_they_have_not_found_out_about_yet(client, monkeypatch, minds):
    make(client, monkeypatch)
    client.put('/api/life/steps', json={'step': 'exclusive'})
    add_romance(client, 'Theo Park')
    line = standing(client)
    assert 'as far as you know the user sees only you' in line and 'only see each other' not in line
    with client.app.state.database.connect(write=True) as connection:  # The daily pass: they find out, and it hurts.
        minds.seen_with_others(connection, current(connection), client.app.state.database.clock.now())
    line = standing(client)
    assert 'You are a couple. If the user asks what you are, say so plainly.' in line
    assert 'You found out on 5 October 2026 that the user is also seeing Theo, and it hurts.' in line
    with client.app.state.database.connect(write=True) as connection:
        connection.execute("UPDATE rough_patches SET mended_at=?, mended_by='apology'", (client.app.state.database.now(),))
    assert 'You found out on 5 October 2026 that the user is also seeing Theo; you have come to terms with it.' \
        in standing(client)


def test_other_romances_they_knew_of_before_the_app_started_them_out_exclusive(client, monkeypatch, minds):
    add_romance(client, 'Theo Park', '2026-01-01T00:00:00+00:00')
    make(client, monkeypatch, history_together='We have been dating for a year.')
    line = standing(client)
    assert 'The user was already seeing Theo when you two became a couple; you have known all along' in line
    assert 'only' not in line.split('Keep to')[0]


def test_an_open_relationship_an_easy_life_and_a_shared_home(client, monkeypatch, minds):
    make(client, monkeypatch, interests=['open relationships'])
    client.put('/api/life/steps', json={'step': 'love'})
    other, timeline = add_romance(client, 'Theo Park')
    line = standing(client)
    assert 'You are a couple and you have both said "I love you".' in line
    assert 'Your relationship with the user is open: the user is also seeing Theo, and you know.' in line
    with client.app.state.database.connect(write=True) as connection:
        version = current(connection)['active_version_id']
        connection.execute("UPDATE character_versions SET definition=json_set(definition, '$.interests', json('[]')) "
                           'WHERE id=?', (version,))
    set_life(client, rough_patches_realism=1)
    assert 'The user is also seeing Theo; you know, and it does not bother you.' in standing(client)
    database = client.app.state.database
    with database.connect(write=True) as connection:
        for timeline_id in (current(connection)['active_timeline_id'], timeline):
            connection.execute("INSERT INTO moving_in (id, timeline_id, plan, status, city_id, decided_on, moved_on, "
                               "created_at) VALUES (?, ?, 'yours', 'moved', 'baltimore', '2026-09-01', '2026-09-20', ?)",
                               (f'home-{timeline_id}', timeline_id, database.now()))
    assert 'Theo also lives with you and the user: the user is with Theo too, and you all know it.' in standing(client)


def test_an_ex_is_not_another_romance_and_a_group_chat_reads_the_same_line(client, monkeypatch, minds):
    make(client, monkeypatch)
    client.put('/api/life/steps', json={'step': 'exclusive'})
    other, _timeline = add_romance(client, 'Theo Park')
    group = {'older': [], 'query': '', 'lines': [], 'previous': None}
    assert 'as far as you know the user sees only you' in standing(client, group)
    monkeypatch.setattr(steps, 'apart', lambda _connection, companion: 'ended' if companion['id'] == other else None)
    assert 'you are a couple and only see each other' in standing(client)


# Which message is the answer (Vanta 2026-10-17): only the user's first reply after an ask is read whatever it says; a
# later one counts only when it plainly answers.

def asked(client, provider, clock, monkeypatch, relationship='romance'):
    """Mira brings up the next step (being exclusive; a confession for a friend) in a first text: open now."""
    make(client, monkeypatch, relationship=relationship)
    monkeypatch.setattr(steps, 'FIRST_TEXTS', True)
    view(client)
    if relationship == 'romance':
        close(client, 3)
        clock.advance(timedelta(days=36))
        reconcile(client)
        clock.advance(timedelta(days=8))
    else:
        monkeypatch.setattr(consequences, 'roll', lambda _seed, found: found[-1]['option'])
        close(client, 4)
        for days in (95, 28, 13):
            clock.advance(timedelta(days=days))
            if days != 13:
                reconcile(client)
    assert first_text(client, clock)


def open_asks(client):
    with client.app.state.database.connect() as connection:
        return [row['step'] for row in steps.asks(connection, current(connection)['active_timeline_id'], ('open',))]


def test_an_ok_about_something_else_later_is_not_a_yes(client, provider, clock, monkeypatch, always):
    asked(client, provider, clock, monkeypatch)
    says(provider)
    send(client, 'ugh my day was awful, my boss yelled at me', 'client-answer-1')
    says(provider, 'Oh no, that sounds rough. Want to talk about it?')
    send(client, 'lol ok so basically he hates my slides', 'client-answer-2')
    says(provider)
    send(client, "sure, I'll make pasta tonight", 'client-answer-3')
    assert view(client)['step'] == 'dating' and open_asks(client) == ['exclusive']
    assert 'they have not answered yet' in prompt(provider)
    says(provider)
    send(client, 'oh and about being exclusive: yes, I want that', 'client-answer-4')  # Names the step.
    assert 'The user just said yes to being exclusive.' in prompt(provider)
    assert view(client)['step'] == 'exclusive' and open_asks(client) == []


def test_the_whole_first_reply_counts_even_in_two_messages(client, provider, clock, monkeypatch, always):
    asked(client, provider, clock, monkeypatch)
    with client.app.state.database.connect(write=True) as connection:  # "omg", sent before Mira wrote back.
        companion = current(connection)
        connection.execute("INSERT INTO messages (id, timeline_id, seq, role, text, status, active, created_at, "
                           "completed_at) VALUES ('omg', ?, 100, 'user', 'omg', 'complete', 1, ?, ?)",
                           (companion['active_timeline_id'], clock.now().isoformat(), clock.now().isoformat()))
    says(provider)
    send(client, 'yes!!', 'client-answer-5')
    assert view(client)['step'] == 'exclusive'


def test_a_clear_not_yet_right_after_they_bring_it_up_again(client, provider, clock, monkeypatch, always):
    asked(client, provider, clock, monkeypatch)
    says(provider, 'Sorry, that was a lot. So... how do you feel about being exclusive?')
    send(client, 'haha wait, what are you having for dinner?', 'client-answer-6')
    says(provider)
    send(client, 'not yet, sorry. I need a little more time', 'client-answer-7')
    assert "The user just said they aren't ready for being exclusive yet." in prompt(provider)
    assert view(client)['step'] == 'dating' and open_asks(client) == []


def test_a_later_no_counts_when_it_names_the_step_and_a_nah_about_lunch_does_not(client, provider, clock, monkeypatch,
                                                                                 always):
    asked(client, provider, clock, monkeypatch)
    says(provider, 'Ha, good morning to you too.')
    send(client, 'good morning!', 'client-answer-8')
    says(provider, 'Want to get lunch?')
    send(client, 'nah, I ate already', 'client-answer-9')  # A clear no, but to lunch.
    assert open_asks(client) == ['exclusive']
    says(provider)
    send(client, "I've thought about it and no, I don't want to be exclusive", 'client-answer-10')
    assert 'The user just said no to being exclusive.' in prompt(provider)
    assert view(client)['step'] == 'dating' and open_asks(client) == []


def test_bringing_up_the_step_they_asked_about_says_yes_to_it(client, provider, clock, monkeypatch, always):
    asked(client, provider, clock, monkeypatch)
    says(provider)
    send(client, 'how was work?', 'client-answer-11')
    says(provider)
    send(client, 'can we make it official? be my girlfriend?', 'client-answer-12')
    found = view(client)
    assert found['step'] == 'exclusive' and found['steps'][-1]['how'] == 'them' and open_asks(client) == []
    assert 'The user just said yes to being exclusive.' in prompt(provider)


def test_bringing_up_a_further_step_settles_the_one_waiting(client, provider, clock, monkeypatch, always):
    asked(client, provider, clock, monkeypatch)
    says(provider)
    send(client, 'how was work?', 'client-answer-13')
    says(provider)
    send(client, 'I just wanted to say I love you', 'client-answer-14')
    found = view(client)
    assert [item['step'] for item in found['steps']] == ['dating', 'exclusive', 'love'] and open_asks(client) == []


def test_a_friends_confession_is_answered_by_the_first_reply_or_a_plain_answer(client, provider, clock, monkeypatch):
    asked(client, provider, clock, monkeypatch, relationship='friendship')
    says(provider, 'Haha, sorry, forget I said anything.')
    send(client, 'wait what time is lunch tomorrow?', 'client-answer-15')
    says(provider, 'Noon at the usual place?')
    send(client, 'sure, noon works', 'client-answer-16')  # A yes to lunch, not to them.
    assert client.get('/api/companion').json()['companion']['version']['definition']['relationship'] == 'friendship'
    assert open_asks(client) == ['confession']
    says(provider)
    send(client, "about what you said the other day... I feel the same", 'client-answer-17')
    assert client.get('/api/companion').json()['companion']['version']['definition']['relationship'] == 'romance'
    assert 'they just said they feel the same' in prompt(provider)


def test_a_clear_answer_opens_the_message():
    assert steps.clear('yes!') == 'yes' and steps.clear('not yet, sorry') == 'not_yet'
    assert steps.clear('haha sure') == 'yes' and steps.clear('no. not ready for that') == 'no'
    assert steps.clear('lol ok so my day was awful') is None
    assert steps.clear('my day was long, ok whatever') is None
