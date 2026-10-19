"""Life's big turns on a branch: a fork keeps each big turn as it stood at the fork point."""
from datetime import timedelta

import pytest
from conftest import reconcile, send
from test_big_turns import begun, details, make, next_stage
from test_big_turns_two import land, parent
from test_chapters import current


@pytest.fixture
def mira(client, monkeypatch, provider):
    make(client, monkeypatch, 'Mira is 34, an accountant.')
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})


def fork_from(client, message_id: str) -> str:
    fork = client.post('/api/timelines', json={'message_id': message_id}).json()
    assert client.post(f"/api/timelines/{fork['id']}/activate").status_code == 200
    return fork['id']


def rows(client, timeline_id: str) -> list[dict]:
    with client.app.state.database.connect() as connection:
        return [dict(row) for row in connection.execute('SELECT * FROM life_chapters WHERE timeline_id=?',
                                                        (timeline_id,))]


def test_a_fork_from_before_classes_start_is_still_signed_up(client, mira, clock, monkeypatch):
    chapter = begun(client, monkeypatch, clock, 'school')
    sent = send(client, 'Good luck with the course!', 'client-fork-school-1')['message']
    clock.advance(timedelta(days=1))
    next_stage(client, clock, chapter['id'])  # Classes start, after the fork point.
    assert any(block['kind'] == 'study' for block in current(client)['version']['definition']['schedule'])
    fork = fork_from(client, sent['id'])
    [copied] = rows(client, fork)
    assert details(client, copied['id'])['stage'] == 'enrolled'
    assert not any(block['kind'] == 'study' for block in current(client)['version']['definition']['schedule'])
    reconcile(client)  # The fork's own days bring classes again.
    assert details(client, copied['id'])['stage'] == 'studying'
    assert any(block['kind'] == 'study' for block in current(client)['version']['definition']['schedule'])


def test_undo_on_a_fork_leaves_the_parent_timelines_marks_alone(client, mira, clock, monkeypatch):
    reconcile(client)
    parent(client, 78)
    chapter = begun(client, monkeypatch, clock, 'caring')
    next_stage(client, clock, chapter['id'])  # Caring begins.
    land(monkeypatch, 'caring:how', 2)
    next_stage(client, clock, chapter['id'])  # It gets harder: marks on the parent timeline.
    main = current(client)['active_timeline_id']
    decided = details(client, chapter['id'])
    sent = send(client, 'How is your mom?', 'client-fork-care-1')['message']
    with client.app.state.database.connect() as connection:
        before = connection.execute('SELECT COUNT(*) AS n FROM marks WHERE timeline_id=?', (main,)).fetchone()['n']
    fork = fork_from(client, sent['id'])
    [copied] = rows(client, fork)
    assert details(client, copied['id'])['parent'] != decided['parent']  # The fork's own copy of the parent.
    client.post(f"/api/life/chapters/{copied['id']}/undo").raise_for_status()
    with client.app.state.database.connect() as connection:
        after = connection.execute('SELECT COUNT(*) AS n FROM marks WHERE timeline_id=?', (main,)).fetchone()['n']
    assert after == before
