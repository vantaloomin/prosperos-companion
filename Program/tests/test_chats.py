"""Every companion texts first, within one shared allowance, and each chat shows what is unread (companion/chats.py,
companion/away.py)."""
from datetime import timedelta

from conftest import send, set_life

from companion.characters import insert_version
from companion.database import identifier
from companion.models import CharacterDefinition


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def check(client):
    return ok(client.post('/api/life/texts/check'))


def chats(client):
    return ok(client.get('/api/chats'))


def another(client, name='Sally', **changes):
    """A second companion, out of focus, the way one is after switching away from them."""
    database = client.app.state.database
    mira = ok(client.get('/api/companion'))['companion']
    definition = CharacterDefinition(**{**mira['version']['definition'], 'name': name, **changes})
    timestamp = database.now()
    with database.connect(write=True) as connection:
        companion_id, timeline_id = identifier(), identifier()
        connection.execute('INSERT INTO companions (id, slot, stepped_back_at, created_at) VALUES (?, NULL, ?, ?)',
                           (companion_id, timestamp, timestamp))
        version_id = insert_version(connection, companion_id, 1, definition, '', timestamp)
        connection.execute("INSERT INTO timelines (id, companion_id, status, created_at) VALUES (?, ?, 'active', ?)",
                           (timeline_id, companion_id, timestamp))
        connection.execute('UPDATE companions SET active_version_id=?, active_timeline_id=? WHERE id=?',
                           (version_id, timeline_id, companion_id))
    return companion_id, timeline_id


def focus(client, companion_id):
    return ok(client.post('/api/companion/cast/focus', json={'companion_id': companion_id}))


def missed_by(client, clock, mira):
    """Sally, who misses the user when they go quiet, talked with them three days ago; Mira is in focus."""
    sally, timeline = another(client, emotional_traits=[{'name': 'guilt over absence', 'intensity': 'moderate'}])
    focus(client, sally)
    send(client, 'Talk soon', 'client-sally-01')
    focus(client, mira['id'])
    clock.advance(timedelta(days=3))
    return sally, timeline


def test_a_companion_out_of_focus_texts_first_and_shows_unread(client, companion, clock):
    sally, timeline = missed_by(client, clock, companion)
    result = check(client)
    assert result['state'] == 'sent' and result['kind'] == 'silence'
    assert result['companion_id'] == sally and result['focus'] is False
    # It lands in Sally's chat, not in the one on screen.
    assert ok(client.get('/api/conversation'))['messages'] == []
    listed = chats(client)
    assert [chat['name'] for chat in listed['chats']] == ['Sally', 'Mira']
    sally_chat = listed['chats'][0]
    assert sally_chat['unread'] == 1 and sally_chat['thread_id'] == timeline and sally_chat['focus'] is False
    assert sally_chat['last']['role'] == 'companion' and sally_chat['last']['text'] == result['message']['text']
    assert listed['unread'] == 1
    # Seen: nothing unread any more.
    assert ok(client.post('/api/chats/read', json={'thread_id': timeline}))['unread'] == 0


def test_writing_back_counts_as_reading(client, companion, clock):
    sally, _timeline = missed_by(client, clock, companion)
    check(client)
    focus(client, sally)
    send(client, 'Sorry, busy week!', 'client-sally-02')
    assert chats(client)['unread'] == 0


def test_all_companions_share_one_allowance(client, companion, clock):
    sally, _timeline = missed_by(client, clock, companion)
    assert ok(client.get('/api/life/settings'))['away_daily'] == 6
    set_life(client, away_daily=0)
    assert check(client) == {'state': 'away_cap', 'message': None}
    set_life(client, away_daily=1)
    assert check(client)['companion_id'] == sally
    database = client.app.state.database
    with database.connect() as connection:
        from companion import away
        assert away.spent(connection, clock.now()) == 1 and not away.allowed(connection, clock.now())
    assert client.put('/api/life/settings', json={'away_daily': 41}).status_code == 422


def test_a_notification_names_the_companion_who_wrote(client, companion, clock):
    sally, _timeline = missed_by(client, clock, companion)
    ok(client.put('/api/notifications/settings', json={'enabled': True, 'quiet_start': '00:00', 'quiet_end': '00:00'}))
    message = check(client)['message']
    shown = ok(client.post('/api/notifications/next', json={'focused': False}))['notification']
    assert shown['kind'] == 'message' and shown['title'] == 'Sally' and shown['companion_id'] == sally
    assert shown['body'] == 'Sally sent you a message.' and message['text']


def test_a_held_back_companion_does_not_stop_the_others(client, companion, clock):
    sally, _timeline = missed_by(client, clock, companion)
    set_life(client, texts_first=True)
    # Mira has nothing to say; Sally does.
    assert check(client)['companion_id'] == sally
    # Sally waits for an answer now, and Mira still has nothing: the focus companion's state is reported.
    clock.advance(timedelta(hours=4))
    assert check(client)['state'] == 'nothing'
