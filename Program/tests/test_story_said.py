"""What is said in a Story scene sticks (companion/story_said.py): facts told face to face become memories, and the
user's words move how the companion feels, as a text would."""
import pytest
from conftest import reconcile, set_life
from test_drop_by import SHIFTS
from test_rough_patches import patch
from test_story import ok, say
from test_story_cast import at_work, script
from test_story_visits import leave
from test_together import mira

from companion import consequences, moods, story_said
from companion.characters import current
from companion.life import rough_patches


@pytest.fixture
def barkeep(client, monkeypatch):
    mira(client, monkeypatch, schedule=SHIFTS)
    reconcile(client)
    assert client.put('/api/settings', json={'automatic_memory': True}).status_code == 200


def tell(client, provider, text, number, reply='Mira nods. "Go on."'):
    script(provider, 'The bar hums quietly.', reply)
    say(client, text, f'said-{number:04d}')


def facts(client):
    return [memory for memory in ok(client.get('/api/memories')) if memory['layer'] == 'user_fact']


def mira_key(client):
    with client.app.state.database.connect() as connection:
        return story_said.key(current(connection))


def mood(client):
    database = client.app.state.database
    with database.connect() as connection:
        return moods.current(connection, mira_key(client), database.clock.now())


def companion_prompt(provider):
    """The latest request that was Mira's own line in the scene."""
    request = next(request for request in reversed(provider.requests) if 'Mira' in request['system'] and
                   'The scene so far' in request['system'])
    return request['system'] + request['messages'][-1]['content']


def test_a_fact_said_to_them_in_a_scene_is_a_memory_with_the_line_it_came_from(client, barkeep, provider):
    at_work(client)
    line = 'I lean on the bar. "My sister Ashley just moved to Denver," I tell Mira.'
    tell(client, provider, line, 1)
    found = {(memory['subject'], memory['value']): memory for memory in facts(client)}
    assert ('Sister', 'Ashley') in found
    memory = found[('Sister', 'Ashley')]
    assert memory['origin'] == 'automatic' and memory['source_message_ids'] == []
    # The card quotes the words said, not the narration (Iris).
    assert memory['story_line'] == 'My sister Ashley just moved to Denver,' and memory['in_story'] is False
    # Correcting it keeps where it came from; deleting it takes the link with it.
    corrected = ok(client.post(f"/api/memories/{memory['id']}/correct",
                               json={'value': 'Ash', 'expected_revision': memory['revision']}))
    assert next(item for item in facts(client) if item['id'] == corrected['id'])['story_line'] == memory['story_line']
    ok(client.post(f"/api/memories/{corrected['id']}/delete", json={'delete_sources': False}))
    with client.app.state.database.connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM story_memories WHERE memory_id=?',
                                  (corrected['id'],)).fetchone()[0] == 0


def test_only_the_words_said_count_and_not_what_the_user_does(client, barkeep, provider):
    at_work(client)
    tell(client, provider, 'I hand Mira the menu. "I hate cilantro." I grin. "And olives."', 0)
    assert [memory['story_line'] for memory in facts(client)] == ['I hate cilantro. … And olives.']
    tell(client, provider, 'I tell Mira that I hate olives.', 9)
    assert 'I tell Mira that I hate olives.' in [memory['story_line'] for memory in facts(client)]
    for memory in facts(client):
        ok(client.post(f"/api/memories/{memory['id']}/delete", json={'delete_sources': False}))
    tell(client, provider, "I'm wearing my blue jacket, so I take it off and hang it up. \"Busy night?\"", 1)
    tell(client, provider, 'I grab a stool and smile at Mira.', 2)
    assert facts(client) == []


def test_nothing_is_kept_with_automatic_memory_or_scenes_counting_off(client, barkeep, provider):
    at_work(client)
    client.put('/api/settings', json={'automatic_memory': False})
    tell(client, provider, '"I\'m allergic to peanuts," I tell Mira.', 1)
    assert facts(client) == []
    client.put('/api/settings', json={'automatic_memory': True})
    set_life(client, story_counts=False)
    tell(client, provider, '"My dog Pepper would love it here," I tell Mira.', 2)
    assert facts(client) == []
    set_life(client, story_counts=True)
    tell(client, provider, '"My dog Pepper would love it here," I tell Mira.', 3)
    assert [(memory['subject'], memory['value']) for memory in facts(client)] == [('Dog', 'Pepper')]


def test_a_line_to_someone_else_or_out_of_the_story_is_not_theirs(client, barkeep, provider):
    at_work(client)
    tell(client, provider, '((OOC: my sister Ashley is in Denver))', 1)
    assert facts(client) == []
    leave(client)  # Mira is not in the scene at the park.
    tell(client, provider, '"My dog Pepper loves this park," I say to nobody.', 2)
    assert facts(client) == []


def test_words_that_sting_in_a_scene_cool_them_and_their_line_knows_it(client, barkeep, provider):
    at_work(client)
    tell(client, provider, 'I roll my eyes. "You\'re so boring, Mira."', 1)
    found = mood(client)
    assert (found['feeling'], found['target']) == ('annoyed', moods.USER)  # True to life: a bit irritable first.
    tell(client, provider, '"So, how was your shift?"', 2)
    assert "- You're a bit irritable with the user (why: something you said stung). Let it show in how you speak and " \
           'act here' in companion_prompt(provider)
    # Said with a wink, it is teasing.
    database = client.app.state.database
    with database.connect(write=True) as connection:
        moods.forget(connection, mira_key(client))
    tell(client, provider, 'I grin and nudge Mira. "You\'re so boring."', 3)
    assert mood(client) is None


def test_their_line_saying_its_alright_clears_it(client, barkeep, provider):
    at_work(client)
    database = client.app.state.database
    with database.connect(write=True) as connection:
        moods.save(connection, mira_key(client), 'hurt', 1, moods.USER, 'something you said stung',
                   database.clock.now())
    tell(client, provider, '"I\'m sorry about earlier, Mira."', 1,
         reply='Mira softens. "It\'s okay, I understand. We\'re good," she says.')
    assert mood(client) is None or mood(client)['feeling'] == 'calm'


def test_a_rough_patch_opens_and_mends_in_person(client, barkeep, provider, monkeypatch):
    monkeypatch.setattr(rough_patches, 'ACTIVE', True)
    monkeypatch.setattr(consequences, 'roll', lambda seed, found: found[-1]['option'])
    set_life(client, rough_patches_realism=3)
    at_work(client)
    tell(client, provider, '"Go away, Mira."', 1)
    assert patch(client)['open']
    tell(client, provider, '"How are you?"', 2)
    assert 'Things are tense between you and the user right now.' in companion_prompt(provider)
    tell(client, provider, '"I\'m really sorry, Mira, I shouldn\'t have said that."', 3)
    assert not patch(client)['open']
    # A promise said in person stays with chat, where keeping it is checked.
    tell(client, provider, '"I\'ll call you tonight, Mira."', 4)
    with client.app.state.database.connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM rough_patch_promises').fetchone()[0] == 0
