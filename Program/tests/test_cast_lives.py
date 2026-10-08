"""Everyone keeps living: companions out of focus live their days too (companion/life/simulation.py)."""
import asyncio
import time
from datetime import timedelta

from conftest import reconcile, set_life
from test_groups import companion_named

from companion.life import simulation


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def settle(app):
    """Wait for the round of the cast that a return to the app starts without waiting."""
    deadline = time.monotonic() + 10
    while app.state.life.casting is not None and not app.state.life.casting.done():
        assert time.monotonic() < deadline, 'The cast round did not finish.'
        time.sleep(0.01)


def timeline_events(app, companion_id):
    with app.state.database.connect() as connection:
        return [dict(row) for row in connection.execute(
            'SELECT e.* FROM life_events e JOIN companions c ON c.active_timeline_id=e.timeline_id WHERE c.id=? '
            'ORDER BY e.starts_at', (companion_id,)).fetchall()]


def phrasing_requests(provider):
    return [request for request in provider.requests if 'Rephrase one ordinary moment' in request['system']]


def test_a_companion_out_of_focus_lives_her_days_in_template_wording(app, client, life, clock):
    billy = companion_named(client, 'Billy Hart')
    set_life(client, automatic_events=True)
    clock.advance(timedelta(days=1))
    focus = reconcile(client)
    settle(app)
    assert [item['outcome'] for item in focus['run']['results']] == ['committed'] * 3

    theirs = timeline_events(app, billy)
    assert len(theirs) == 3 and {event['status'] for event in theirs} == {'committed'}
    assert {event['companion_id'] for event in theirs} == {billy}
    # Only the companion in focus is phrased by the model; Billy's days cost no model calls.
    assert len(phrasing_requests(life)) == 3
    assert all('Phrased' not in event['summary'] and 'Billy' in event['summary'] for event in theirs)
    # His posts wait on his Feed; desktop notices stay for the one in focus.
    with app.state.database.connect() as connection:
        queued = connection.execute('SELECT COUNT(*) FROM notifications n JOIN feed_posts p ON p.id=n.post_id '
                                    'JOIN companions c ON c.active_timeline_id=p.timeline_id WHERE c.id=?',
                                    (billy,)).fetchone()[0]
    assert queued == 0

    # Switching to him shows the day he had, as his own account.
    ok(client.post('/api/companion/cast/focus', json={'companion_id': billy}))
    shown = ok(client.get('/api/events'))
    assert [event['id'] for event in shown] == [event['id'] for event in theirs]
    assert ok(client.get('/api/feed'))['posts']


def test_the_cast_follows_the_same_settings_and_never_repeats_a_day(app, client, life, clock):
    billy = companion_named(client, 'Billy Hart')
    set_life(client, catch_up_on_return=False)
    clock.advance(timedelta(days=1))
    reconcile(client)
    settle(app)
    assert timeline_events(app, billy) == []

    set_life(client, catch_up_on_return=True)
    reconcile(client)
    settle(app)
    first = timeline_events(app, billy)
    assert len(first) == 3 and {event['status'] for event in first} == {'proposed'}
    reconcile(client)
    settle(app)
    assert len(timeline_events(app, billy)) == 3

    # Background ticks need the user's permission, for him as for the one in focus.
    engine = app.state.life
    clock.advance(timedelta(hours=20))
    assert {item['state'] for item in asyncio.run(engine.reconcile_cast('background'))} == {'not_permitted'}


def test_a_long_cast_takes_turns(app, client, companion):
    ids = [companion_named(client, f'Friend{index} Smith') for index in range(5)]
    engine = app.state.life
    with app.state.database.connect() as connection:
        first, engine.cast_offset = simulation.cast_turn(connection, 0)
        second, engine.cast_offset = simulation.cast_turn(connection, engine.cast_offset)
    assert len(first) == simulation.CAST_PER_TURN and set(first) | set(second) == set(ids)
    # Five companions, three a turn: the second turn takes the last two and starts the round again.
    assert second[2] == first[0] and not set(first[1:]) & set(second)
