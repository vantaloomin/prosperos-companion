"""Play a plan as a scene (companion/story_plans.py): a plan under way is played in the Story, at its place, with
the people it is with."""
from datetime import timedelta

from conftest import Chunk, reconcile, send
from test_outings import EVENINGS
from test_story import ok, say
from test_together import mira

from companion.database import encode


def script(provider, *texts):
    provider.replies = [[Chunk(text), Chunk('', 'stop')] for text in texts]


def dinner(client, provider, clock, monkeypatch):
    """Mira and the user have dinner planned tonight at 19:00; the clock is moved to 19:10."""
    mira(client, monkeypatch, schedule=EVENINGS)
    reconcile(client)
    script(provider, 'Yes, tonight!')
    send(client, 'Want to get dinner tonight at 7?', 'client-plan-01')
    outing = ok(client.get('/api/life/outings'))['outings'][0]
    assert outing['state'] == 'planned' and outing['story'] is False
    clock.instant = clock.now().replace(hour=19, minute=10)
    return outing


def test_a_plan_under_way_is_played_where_it_is_with_the_companion_who_came_too(client, provider, clock, monkeypatch):
    outing = dinner(client, provider, clock, monkeypatch)
    listed = ok(client.get('/api/life/outings'))['outings'][0]
    assert listed['state'] == 'now' and listed['story'] is True
    before = ok(client.get('/api/story'))
    assert before['companions'][0]['plan']['outing_id'] == outing['id'] and before['scene']['plan'] is None

    played = ok(client.post('/api/story/plan', json={'outing_id': outing['id']}))
    assert played['scene']['place']['id'] == outing['place']['id']
    assert played['scene']['plan'] == {
        'outing_id': outing['id'], 'companion_id': played['companions'][0]['id'], 'name': 'Mira', 'what': 'dinner',
        'until': outing['until_time'], 'place': outing['place']['name'], 'storyline': False, 'people': []}
    assert played['scene']['around'][0] == 'Mira'
    assert [(row['role'], row['text']) for row in played['messages'][-2:]] == [
        ('scene', played['messages'][-2]['text']), ('cast', 'Mira is here with you, for dinner.')]

    script(provider, 'Candles on every table.', 'Mira pulls out a chair. "Finally."')
    # Start the scene says nothing as the user: the models read a line said for them, the screen and the export do not.
    assert ok(client.get('/api/life/where'))['story'] == {'with': None, 'meet': None, 'plan': outing['id']}
    sent = ok(client.post('/api/story/begin', json={'client_id': 'story-0001'}))
    assert ok(client.post('/api/story/plan/begin', json={'client_id': 'story-0001'}))['message']['id'] == sent['message']['id']
    assert sent['message']['hidden'] == 1 and sent['message']['text'] == 'I turn to Mira.'
    assert 'I turn to Mira.' not in client.get('/api/export/story').text
    assert [row['role'] for row in sent['replies']] == ['narrator', 'companion']
    narrator, own = provider.requests[-2], provider.requests[-1]
    assert 'here with the user, for dinner: a plan the two of them made' in narrator['system']
    assert 'The plan: the user and Mira came here together for dinner, until about' in narrator['system']
    notes = own['messages'][-1]['content']
    assert f"You are Mira, in person with the user at {outing['place']['name']}. You are here together: dinner at" in notes
    assert 'You came here together. Neither of you is surprised to see the other' in notes
    assert 'You were here first' not in notes and 'did not know they were coming' not in notes


def test_a_plan_is_played_only_while_it_is_under_way_and_where_the_story_can_go(client, provider, clock, monkeypatch):
    mira(client, monkeypatch, schedule=EVENINGS)
    reconcile(client)
    script(provider, 'Yes, tonight!')
    send(client, 'Want to get dinner tonight at 7?', 'client-plan-01')
    outing = ok(client.get('/api/life/outings'))['outings'][0]
    early = client.post('/api/story/plan', json={'outing_id': outing['id']})
    assert early.status_code == 409 and early.json()['detail'] == "That plan isn't under way right now."
    assert client.post('/api/story/plan', json={'outing_id': 'nope'}).status_code == 404
    clock.instant = clock.now().replace(hour=19, minute=10)
    with client.app.state.database.connect(write=True) as connection:  # At their place: nowhere the story goes.
        connection.execute('UPDATE outings SET place=? WHERE id=?', (encode({**outing['place'], 'id': '~home', 'kind': 'home'}), outing['id']))
    assert ok(client.get('/api/life/outings'))['outings'][0]['story'] is False
    home = client.post('/api/story/plan', json={'outing_id': outing['id']})
    assert home.status_code == 409 and home.json()['detail'] == "This plan isn't somewhere your story can go."
    found = ok(client.get('/api/story'))['companions'][0]
    assert found['place'] is None and found['plan'] is None


def test_the_people_a_plan_is_with_are_in_the_scene_for_the_narrator_to_voice(client, provider, clock, monkeypatch):
    outing = dinner(client, provider, clock, monkeypatch)
    with client.app.state.database.connect(write=True) as connection:
        friend = connection.execute('SELECT id, name, timeline_id FROM circle_people ORDER BY ordinal LIMIT 1').fetchone()
        place = {**outing['place'], 'people': [{'id': friend['id'], 'name': friend['name'], 'role': 'close friend'}],
                 'first': True, 'storyline': 'shared-row'}
        connection.execute("UPDATE outings SET activity='meet-friends', place=? WHERE id=?", (encode(place), outing['id']))
        connection.execute(
            'INSERT INTO people_impressions (id, timeline_id, person_id, impression, warmth, created_at, updated_at) '
            "VALUES ('imp-1', ?, ?, 'curious', 1, '', '')", (friend['timeline_id'], friend['id']))
    first = friend['name'].split()[0]
    played = ok(client.post('/api/story/plan', json={'outing_id': outing['id']}))
    assert played['scene']['plan']['people'] == [{'name': first, 'role': 'close friend'}]
    assert played['scene']['plan']['storyline'] is True and played['scene']['plan']['what'] == 'drinks with their friends'
    assert played['scene']['around'][:2] == ['Mira', f"their close friend {first}"]
    script(provider, 'The bar hums.', '"This is them," Mira says.')
    say(client, 'I say hello.', 'story-0001')
    narrator, own = provider.requests[-2], provider.requests[-1]
    assert f"- {friend['name']}, Mira's close friend, here with them for the evening. It is the first time {first} " \
           f"is meeting the user. {first} is polite and has a lot of questions for the user. You voice {first}" in narrator['system']
    notes = own['messages'][-1]['content']
    assert f"Here with you: your close friend {friend['name']}. It is the first time they are meeting the user. " \
           'The narrator speaks for them; you speak only as yourself.' in notes
    assert f"Also here: {first}, Mira's close friend" in own['system']


def test_a_plan_played_in_the_story_leaves_the_plans_own_memory_and_tells_their_chat(client, provider, clock, monkeypatch):
    outing = dinner(client, provider, clock, monkeypatch)
    ok(client.post('/api/story/plan', json={'outing_id': outing['id']}))
    for index, text in enumerate(('Mira, this place is lovely.', 'Mira, shall we order?')):
        script(provider, 'A waiter passes.', '"Yes," Mira says.')
        say(client, text, f'story-000{index}')
    # Still out together: their chat is told what was said, and not that they are apart.
    script(provider, 'Mm.')
    send(client, 'so good', 'client-plan-02')
    told = str(provider.requests[-1])
    assert 'the two of you talked face to face, on the plan you had made' in told
    assert 'The latest of what was said:' in told and 'You are apart again now' not in told
    clock.instant = clock.now() + timedelta(hours=4)
    ok(client.put('/api/story/scene', json={'city_id': 'baltimore'}))
    with client.app.state.database.connect() as connection:
        visit = connection.execute('SELECT * FROM story_visits').fetchone()
        assert visit['outing_id'] == outing['id'] and visit['said'] == 2 and visit['memory_id'] is None
        assert connection.execute("SELECT COUNT(*) AS n FROM memories WHERE subject LIKE 'In person at%'").fetchone()['n'] == 0
