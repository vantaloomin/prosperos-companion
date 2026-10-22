"""Their voice stays theirs (companion/memory/voice.py): a few of their own earlier replies in every chat reply."""
from datetime import timedelta

from conftest import send

from companion.characters import require_current
from companion.memory import context, records, voice
from companion.providers.chat import Chunk


def system(app) -> str:
    database = app.state.database
    with database.connect() as connection:
        return context.build(connection, require_current(connection), database.clock.now(), 20_000)['system']


def section(prompt: str) -> list[str]:
    if '## How you sound' not in prompt:
        return []
    lines = prompt.split('## How you sound\n', 1)[1].split('\n\n', 1)[0].splitlines()
    assert lines[0] == voice.INTRO
    return [line.removeprefix('- "').removesuffix('"') for line in lines[1:]]


def echo(system, messages):
    """Each reply quotes the message it answers, so it can be found again."""
    text = messages[-1]['content'].rsplit('\n', 1)[-1]
    return [Chunk(f'Funny you say "{text}", honestly that made my whole afternoon. Tell me more later.'),
            Chunk('', 'stop')]


def chat(client, clock, count, prefix='m', days=3):
    for index in range(count):
        send(client, f'{prefix} {index:02d}', f'{prefix}-client-{index:04d}')
        if index % (count // days or 1) == 0:
            clock.advance(timedelta(days=1))


def test_an_excerpt_is_a_sentence_or_two_and_the_pick_mixes_days_and_lengths():
    assert voice.excerpt('ok') is None, 'too short to show a voice'
    assert voice.excerpt('Hey you, how was the pier?') == 'Hey you, how was the pier?'
    assert voice.excerpt('Hey you. I was just thinking about the pier. Anyway, later!') == \
        'Hey you. I was just thinking about the pier.'
    long = voice.excerpt('word ' * 100)
    assert long.endswith('…') and len(long) <= voice.EXCERPT_CHARS + 1
    items = [{'id': f'{day}-{kind}', 'day': day, 'kind': kind, 'text': ''}
             for day in ('d1', 'd2') for kind in ('short', 'medium', 'long') for _ in range(2)]
    picked = voice.choose(items, 'seed', 3)
    assert len({item['kind'] for item in picked}) == 3 and len({item['day'] for item in picked}) == 2
    assert picked == voice.choose(list(reversed(items)), 'seed', 3), 'the same pick from the same replies'


def test_the_app_picks_kept_replies_from_before_the_conversation_window(client, app, connected, provider, clock):
    provider.respond = echo
    chat(client, clock, 10)
    assert section(system(app)) == [], 'every reply is still in the conversation sent with the reply'
    chat(client, clock, 14, 'n')
    found = section(system(app))
    assert len(found) == voice.LIMIT
    with app.state.database.connect() as connection:
        rows = context.transcript(connection, require_current(connection)['active_timeline_id'], set())
    older = rows[:context.window_start(len(rows))]
    assert all(any(voice.excerpt(row['text']) == text for row in older) for text in found)
    with app.state.database.connect() as connection:
        group = voice.excerpts(connection, require_current(connection), rows, older, group=True)
    assert len(group) == voice.GROUP_LIMIT, 'two each in a group chat'
    send(client, 'one more', 'one-more-0001')
    assert section(system(app)) == found, 'the pick holds until the window steps, so the prompt stays cacheable'


def test_edited_retried_out_of_character_and_unsafe_replies_are_left_out(client, app, connected, provider, clock):
    provider.respond = echo
    chat(client, clock, 4, 'ooc')
    with app.state.database.connect(write=True) as connection:
        timeline = require_current(connection)['active_timeline_id']
        users = connection.execute("SELECT id FROM messages WHERE timeline_id=? AND role='user' ORDER BY seq",
                                   (timeline,)).fetchall()
        connection.execute("UPDATE messages SET text='OOC: ' || text WHERE id=?", (users[0]['id'],))
        replies = connection.execute("SELECT * FROM messages WHERE timeline_id=? AND role='companion' ORDER BY seq",
                                     (timeline,)).fetchall()
        connection.execute("INSERT INTO message_edits (id, message_id, before_text, after_text, created_at) "
                           "VALUES ('e1', ?, 'x', 'y', '2026-01-01')", (replies[1]['id'],))
        connection.execute("UPDATE messages SET text='Kiss me again, I want you so much tonight, really.' WHERE id=?",
                           (replies[2]['id'],))
        connection.execute("UPDATE messages SET text='The kids were wild at the park today, it was lovely.' WHERE id=?",
                           (replies[3]['id'],))
        rows = context.transcript(connection, timeline, set())
        kept = voice.kept(connection, rows)
        assert [row['id'] for row in kept] == [row['id'] for row in rows if row['role'] == 'companion'][2:]
        found = voice.excerpts(connection, require_current(connection), rows, rows)
    assert found == [], 'what is left reads intimate or names a child'


def test_sounds_like_them_pins_come_first_up_to_three(client, app, connected, provider, clock):
    provider.respond = echo
    chat(client, clock, 4)
    with app.state.database.connect() as connection:
        replies = [row['id'] for row in connection.execute(
            "SELECT id FROM messages WHERE role='companion' ORDER BY seq").fetchall()]
    response = client.post(f'/api/conversation/messages/{replies[3]}/voice', json={'pinned': True})
    assert response.status_code == 200, response.text
    assert [pin['message_id'] for pin in response.json()['pins']] == [replies[3]]
    found = section(system(app))
    assert len(found) == 1 and '"m 03"' in found[0], 'a pin shows even while it is in the conversation'
    for message in replies[:2]:
        client.post(f'/api/conversation/messages/{message}/voice', json={})
    full = client.post(f'/api/conversation/messages/{replies[2]}/voice', json={'pinned': True})
    assert full.status_code == 409
    assert len(client.get('/api/conversation/voice').json()['pins']) == 3
    left = client.post(f'/api/conversation/messages/{replies[3]}/voice', json={'pinned': False}).json()
    assert sorted(pin['message_id'] for pin in left['pins']) == sorted(replies[:2])
    with app.state.database.connect() as connection:
        user = connection.execute("SELECT id FROM messages WHERE role='user' LIMIT 1").fetchone()['id']
    assert client.post(f'/api/conversation/messages/{user}/voice', json={}).status_code == 422


def test_the_same_words_said_twice_are_one_excerpt(client, app, connected, provider, clock):
    provider.respond = lambda system, messages: [Chunk('Ha, you caught me mid-yawn. The kettle is on.'), Chunk('', 'stop')]
    chat(client, clock, 24)
    assert section(system(app)) == ['Ha, you caught me mid-yawn. The kettle is on.']


def test_a_pinned_reply_deleted_later_leaves_the_pins_and_frees_its_place(client, app, connected, provider, clock):
    provider.respond = echo
    chat(client, clock, 5)
    with app.state.database.connect() as connection:
        replies = [row['id'] for row in connection.execute(
            "SELECT id FROM messages WHERE role='companion' ORDER BY seq").fetchall()]
    for message in replies[:3]:
        assert client.post(f'/api/conversation/messages/{message}/voice', json={}).status_code == 200
    with app.state.database.connect(write=True) as connection:
        records.redact_messages(connection, [replies[0]], app.state.database.now())
    assert sorted(pin['message_id'] for pin in client.get('/api/conversation/voice').json()['pins']) == sorted(replies[1:3])
    response = client.post(f'/api/conversation/messages/{replies[3]}/voice', json={})
    assert response.status_code == 200, 'the deleted reply no longer takes one of the three places'
    assert sorted(pin['message_id'] for pin in response.json()['pins']) == sorted(replies[1:4])
