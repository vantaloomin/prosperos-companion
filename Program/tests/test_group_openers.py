"""Group chats starting conversations on their own (companion/group_openers.py, GroupChats.first_words)."""
import asyncio
import re
from datetime import timedelta

import pytest
from conftest import send, set_life
from test_cast_lives import settle
from test_groups import by_speaker, companion_named, messages, ok, say, start

from companion import group_openers
from companion.providers.chat import Chunk

OPENING = re.compile(r"Write (.+?)'s message starting a new conversation")


def respond(system, history):
    """An opening line says who shares it; answers name their speaker as in tests/test_groups.py."""
    found = OPENING.search(history[-1]['content'])
    return [Chunk(f'{found[1]} has news.'), Chunk('', 'stop')] if found else by_speaker(system, history)


@pytest.fixture
def cast(app, client, companion, connected, provider, clock, monkeypatch):
    """Billy and Sally, out of focus, with a day of their own lived and a group with the two of them."""
    monkeypatch.setattr(group_openers, 'awake', lambda companion, now: True)
    provider.respond = respond
    found = {'Billy': companion_named(client, 'Billy Hart'), 'Sally': companion_named(client, 'Sally Moss')}
    found['group'] = start(client, [found['Billy'], found['Sally']])['id']
    set_life(client, automatic_events=True)
    clock.advance(timedelta(days=1))
    ok(client.post('/api/life/reconcile', json={'mode': 'return'}))
    settle(app)
    return found


def first_words(app):
    return asyncio.run(app.state.groups.first_words())


def opening_requests(provider):
    return [request for request in provider.requests if OPENING.search(request['messages'][-1]['content'])]


def test_a_member_shares_news_from_their_day_and_the_others_answer(app, client, cast, provider):
    chosen = first_words(app)
    assert chosen and chosen['member'] in {f"companion:{cast['Billy']}", f"companion:{cast['Sally']}"}
    with app.state.database.connect() as connection:
        event = connection.execute('SELECT * FROM life_events WHERE id=?', (chosen['event_id'],)).fetchone()
        allowance = connection.execute("SELECT kind, thread_id FROM away_messages").fetchall()
    # The news is a finished moment from the speaker's own day, given to the model to phrase.
    [request] = opening_requests(provider)
    assert event['status'] == 'committed' and event['summary'] in request['messages'][-1]['content']
    sharer, other = ('Billy', 'Sally') if chosen['member'].endswith(cast['Billy']) else ('Sally', 'Billy')

    shown = [item for item in messages(client, cast['group']) if item['kind'] != 'app']
    assert [item['text'] for item in shown] == [f'{sharer} has news.', f'{other} here.']
    assert shown[1]['reply_to'] == shown[0]['id'] and shown[0]['reply_to'] is None
    # It counts toward the shared allowance for messages nobody asked for.
    assert [tuple(row) for row in allowance] == [('group', cast['group'])]

    # Not again until the user answers, and the same news is never shared twice.
    assert first_words(app) is None
    say(client, cast['group'], 'Tell me more!', 'user-answer-1')
    with app.state.database.connect() as connection:
        life = connection.execute('SELECT * FROM life_settings WHERE id=1').fetchone()
        assert group_openers.group_held(connection, cast['group'], life, app.state.database.clock.now()) == 'recent'
        later = app.state.database.clock.now() + timedelta(days=1)
        assert group_openers.group_held(connection, cast['group'], life, later) == 'too_soon'
        assert group_openers.group_held(connection, cast['group'], life, later + timedelta(days=1)) is None


def test_it_follows_the_holds_of_texting_first(app, client, cast, clock):
    set_life(client, texts_first=False)
    assert first_words(app) is None
    set_life(client, texts_first=True, away_daily=0)
    assert first_words(app) is None
    set_life(client, away_daily=6)
    send(client, 'Hi Mira', 'one-to-one')  # The user is chatting: a group starting up would interrupt.
    assert first_words(app) is None
    clock.advance(group_openers.BUSY)
    assert first_words(app) is not None


def test_news_that_gives_a_secret_away_stays_unshared(app, client, cast):
    ok(client.post('/api/secrets', json={'statement': 'Billy is dating Katie.', 'about': ['Billy', 'Katie'],
                                         'knows': [cast['Billy']], 'kept_from': [cast['Sally']]}))
    with app.state.database.connect(write=True) as connection:
        connection.execute("UPDATE life_events SET summary='Billy had dinner with Katie, who he is dating.' "
                           'WHERE timeline_id=(SELECT active_timeline_id FROM companions WHERE id=?)',
                           (cast['Billy'],))
    chosen = first_words(app)
    assert chosen and chosen['member'] == f"companion:{cast['Sally']}"


def test_an_opening_line_that_fails_is_not_kept_or_tried_again(app, client, cast, provider):
    provider.respond = lambda system, history: [Chunk('', 'length')]
    tried = first_words(app)
    assert tried is not None
    assert [item for item in messages(client, cast['group']) if item['kind'] != 'app'] == []
    # The day lived is random and may hold only one piece of news: give the second try another to share.
    with app.state.database.connect(write=True) as connection:
        connection.execute("INSERT INTO life_events SELECT id || '-also', companion_id, timeline_id, "
                           "idempotency_key || '-also', kind, status, summary || ' Then a second thing happened.', "
                           'details, starts_at, ends_at, character_version_id, permission_revision, inputs, revision, '
                           'supersedes_id, rejection, created_at, decided_at FROM life_events WHERE id=?',
                           (tried['event_id'],))
    first_words(app)
    with app.state.database.connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM away_messages').fetchone()[0] == 0
    # Each try shares other news: one that failed is not asked for again.
    asked = [request['messages'][-1]['content'] for request in opening_requests(provider)]
    assert len(asked) == 2 and len(set(asked)) == 2
