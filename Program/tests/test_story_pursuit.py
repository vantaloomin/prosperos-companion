"""Townsfolk the user can pursue in their own story: asked out in a scene, their rules answer, and a yes is a match
who can become a companion (companion/story_pursuit.py)."""
from datetime import timedelta

import pytest
from conftest import Chunk
from test_drafting import connect
from test_social_circle import make

from companion import story, story_pursuit
from companion.world import dating, turnover

PROFILE = {'name': 'Sam', 'age': 30, 'gender': 'man', 'interested_in': ['woman', 'man', 'nonbinary'],
           'looking_for': 'serious', 'age_min': 18, 'age_max': 99, 'bio': ''}


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def say(client, provider, text, client_id, reply='They look up.'):
    provider.replies = [[Chunk(reply), Chunk('', 'stop')]]
    return ok(client.post('/api/story/messages', json={'text': text, 'client_id': client_id}))


def someone(client, clock, wanted):
    """Move the story to a Baltimore place where someone whose rules answer `wanted` is, hours on if need be."""
    database = client.app.state.database
    for _hour in range(72):
        with database.connect() as connection:
            data = story.city_data(connection, 'baltimore')
            moment = story.local_moment(data, clock.now())
            for place in data['places']:
                for person in story.present(connection, data, place['id'], moment):
                    if story_pursuit.answer(connection, person['sheet'], data, 1)['verdict'] == wanted:
                        ok(client.put('/api/story/scene', json={'city_id': 'baltimore', 'place_id': place['id']}))
                        return person['sheet']
        clock.instant = clock.now() + timedelta(hours=1)
    raise AssertionError(f'Nobody in Baltimore answers {wanted!r} for three days.')


@pytest.mark.parametrize('line, asks', [
    ('I ask Dana out.', True), ('"Would you go out with me sometime, Dana?"', True),
    ('Dana, can I have your number?', True), ('I ask Dana whether I may come calling.', True),
    ('"Could I see you again, Dana?"', True), ('"Let me take you to dinner, Dana."', True),
    ('Good to see you again, Dana!', False), ('I ask Dana out of curiosity what she is reading.', False),
    ('I ask Dana about the way out.', False), ('Dana, a coffee please.', False),
])
def test_only_a_plain_ask_counts_and_it_goes_to_the_person_named(line, asks):
    dana = {'sheet': {'key': 'a', 'name': 'Dana', 'full': 'Dana Reyes'}}
    omar = {'sheet': {'key': 'b', 'name': 'Omar', 'full': 'Omar Haddad'}}
    assert (story_pursuit.asked(line, [dana, omar]) is dana) is asks
    # With nobody named it is the only person there, and nobody when there are several.
    assert story_pursuit.asked('Would you go out with me?', [omar]) is omar
    assert story_pursuit.asked('Would you go out with me?', [dana, omar]) is None


def test_their_own_rules_answer_and_meeting_them_more_warms_them():
    sheet = {'key': 'k', 'age': 30, 'temperament': 'warm'}
    found = {'status': 'single', 'drawn_to': ['man'], 'age_range': [24, 40], 'life': 30, 'looking': 'serious', 'picky': 0.5}
    user = {'gender': 'man', 'age': 31, 'seed': '', 'looking_for': None}
    assert story_pursuit.refusal(sheet, found, user) is None
    assert story_pursuit.refusal(sheet, found | {'status': 'married'}, user) == 'taken'
    assert story_pursuit.refusal(sheet, found, user | {'gender': 'woman'}) == 'not_drawn'
    assert story_pursuit.refusal(sheet, found, user | {'age': 60}) == 'age'
    # What is not known of the user is not held against them.
    assert story_pursuit.refusal(sheet, found, user | {'gender': None, 'age': None}) is None
    # Never anyone under 18 on either side, and never someone whose pack says they have no love life.
    assert story_pursuit.refusal(sheet | {'age': 17}, found | {'life': 17}, user) == 'never'
    assert story_pursuit.refusal(sheet, found, user | {'age': 16}) == 'never'
    assert story_pursuit.refusal(sheet | {'love_life': False}, found, user) == 'never'
    first = story_pursuit.chance(sheet, found, user, 1)
    assert first == dating.likes(sheet, found, {'looking_for': 'serious', 'age': 31})
    assert story_pursuit.chance(sheet, found, user, 0) == first
    assert story_pursuit.chance(sheet, found, user, 4) == pytest.approx(first + 3 * story_pursuit.WARMTH)
    assert story_pursuit.chance(sheet, found | {'picky': 1.0}, user, 6) >= 1  # Everyone free and drawn comes round.


def test_someone_who_says_yes_is_a_match_who_can_become_a_companion(client, clock, provider):
    make(client, 'Warm and curious.')
    connect(client)
    ok(client.put('/api/dating/profile', json=PROFILE))
    sheet = someone(client, clock, 'yes')
    name = sheet['name']
    say(client, provider, f'Hello, {name}.', 'story-0001', f'{name} looks up and smiles.')
    person = next(item for item in ok(client.get('/api/story'))['people'] if item['key'] == sheet['key'])
    assert person['matched'] is False and person['ask']['label'] == f'Ask {name} out'

    told = say(client, provider, person['ask']['line'], 'story-0002', f'{name} grins. "I would like that."')
    # The narrator is told the answer right after the user's line, and only plays it out.
    assert provider.requests[-1]['messages'][-1]['content'].endswith(story_pursuit.NOTES['yes'].format(
        name=sheet['full'], first=name, status=''))
    assert [row['role'] for row in told['replies']] == ['narrator', 'cast']
    assert told['replies'][1]['text'] == f'{name} said yes.'
    after = next(item for item in ok(client.get('/api/story'))['people'] if item['key'] == sheet['key'])
    assert after['matched'] is True and after['ask'] is None
    # Sending the same line again writes nothing twice.
    again = ok(client.post('/api/story/messages', json={'text': person['ask']['line'], 'client_id': 'story-0002'}))
    assert [row['id'] for row in again['replies']] == [row['id'] for row in told['replies']]

    # They are a match where the dating app keeps its own, marked as met in the story.
    match = next(item for item in ok(client.get('/api/dating'))['matches'] if item['key'] == sheet['key'])
    assert match['in_story'] is True
    # From then on the narrator knows they said yes.
    say(client, provider, f'I wave to {name}.', 'story-0003')
    assert 'Has said yes to seeing the user' in provider.requests[-1]['system']

    draft = ok(client.get('/api/companion/cast/draft', params={'key': sheet['key']}))
    assert draft['matched'] is True and draft['definition']['relationship'] == 'romance'
    assert draft['definition']['history_together'].startswith('Met the user in person around town, and said yes')
    assert 'Has met the user in person' in draft['definition']['history_together']
    ok(client.post('/api/companion/cast/switch', json={'key': sheet['key'], 'definition': draft['definition']}))
    members = ok(client.get('/api/companion/cast'))['members']
    assert [member['main'] for member in members] == [True, False] and members[1]['name'] == 'Mira'
    # Deleting the dating profile keeps someone the app never matched; a new story lets go of the people met in it,
    # but never a companion.
    ok(client.delete('/api/dating/profile'))
    with client.app.state.database.connect() as connection:
        assert story_pursuit.matched(connection, sheet['key'])
    ok(client.delete('/api/story'))
    with client.app.state.database.connect() as connection:
        assert story_pursuit.matched(connection, sheet['key'])


def test_a_no_is_told_by_the_narrator_and_leaves_no_match(client, clock, provider):
    connect(client)
    ok(client.put('/api/dating/profile', json=PROFILE))
    sheet = someone(client, clock, 'taken')
    told = say(client, provider, f"{sheet['name']}, would you go out with me?", 'story-0001', 'A kind shake of the head.')
    note = provider.requests[-1]['messages'][-1]['content']
    assert f"{sheet['full']} does not say yes" in note and 'agrees to nothing' in note
    assert told['replies'][-1]['text'] == f"{sheet['name']} turned you down."
    assert ok(client.get('/api/dating'))['matches'] == []
    # Stepping out of the story asks nobody anything.
    say(client, provider, f"OOC: could I ask {sheet['name']} out?", 'story-0002')
    assert 'does not say yes' not in provider.requests[-1]['messages'][-1]['content']


def test_a_new_story_lets_go_of_who_said_yes_in_it_but_not_of_app_matches(client, clock, provider):
    connect(client)
    sheet = someone(client, clock, 'yes')  # No dating profile: who the user is in this world is enough.
    say(client, provider, f"I ask {sheet['name']} out.", 'story-0001')
    with client.app.state.database.connect(write=True) as connection:
        assert story_pursuit.matched(connection, sheet['key'])
        data = story.city_data(connection, 'baltimore')
        connection.execute("INSERT INTO dating_swipes (person_key, city_id, town, liked, matched, created_at) "
                           "VALUES ('town:baltimore:x:0', 'baltimore', '', 1, 1, '2026-01-01T00:00:00+00:00')")
        assert turnover.today(data)
    ok(client.delete('/api/story'))
    with client.app.state.database.connect() as connection:
        assert not story_pursuit.matched(connection, sheet['key'])
        assert story_pursuit.matched(connection, 'town:baltimore:x:0')
