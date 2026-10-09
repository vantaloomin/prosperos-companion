"""Life chapters: every few months a lasting change, picked by the consequence engine, that the user can undo."""
from datetime import timedelta

import pytest
from conftest import reconcile
from test_consequences import change
from test_storylines import WORKDAY

from companion import consequences
from companion.characters import require_current
from companion.life import chapters, circle, home, storylines


def test_the_table_has_one_option_per_kind_of_chapter():
    table = consequences.tables()[chapters.CHOICE]
    assert len(table['options']) == len(chapters.KINDS)
    for option in table['options']:
        option['label'].format(name='Mira')
        for rule in option.get('rules', ()):
            rule['why'].format(name='Mira', a='someone', b='')


def test_state_moves_which_chapter_comes():
    names = {'name': 'Mira', 'a': 'someone', 'b': ''}
    every = {f'can_{kind}': 1 for kind in chapters.KINDS}
    plain = consequences.odds(chapters.CHOICE, {'drama': 1, 'friends': 4, **every}, names)
    tight = consequences.odds(chapters.CHOICE, {'drama': 1, 'friends': 4, 'money': -1, **every}, names)
    assert tight[0]['odds'] > plain[0]['odds'] and 'money has been tight for Mira' in tight[0]['reasons']
    no_pet = consequences.odds(chapters.CHOICE, {'drama': 1, 'friends': 4, **every, 'can_pet': 0}, names)
    assert no_pet[2]['odds'] == 0 and no_pet[2]['reasons'] == ['Mira already has a pet']


@pytest.fixture
def mira(client, clock, monkeypatch):
    from companion.life import body
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    monkeypatch.setattr(storylines, 'STORIES', ())
    response = client.post('/api/companion', json={'name': 'Mira Lane', 'timezone': 'UTC', 'schedule': WORKDAY,
                                                     'location': 'Fells Point, Baltimore'})
    assert response.status_code == 200, response.text
    return response.json()


def arrange(client, monkeypatch, clock, kind: str):
    """Their life is set up; a chapter begins tomorrow, and the dice land on `kind`."""
    reconcile(client)
    clock.advance(timedelta(days=1))
    monkeypatch.setattr(chapters, 'CHANCE', (1, 1, 1, 1))
    monkeypatch.setattr(chapters, 'SETTLE_IN', timedelta(0))
    monkeypatch.setattr(chapters, 'check_day', lambda _timeline: clock.now().day)
    monkeypatch.setattr(consequences, 'roll', lambda _seed, found: chapters.KINDS.index(kind)
                        if len(found) == len(chapters.KINDS) else max(found, key=lambda item: item['odds'])['option'])


def current(client):
    with client.app.state.database.connect() as connection:
        return require_current(connection)


def items(client, kind):
    companion = current(client)
    with client.app.state.database.connect() as connection:
        return [item for item in home.items_on(connection, companion['active_timeline_id'], client.app.state.database
                                               .clock.now().date()) if item['kind'] == kind]


def test_a_new_hobby_joins_their_interests_and_can_be_undone(client, mira, clock, monkeypatch):
    arrange(client, monkeypatch, clock, 'hobby')
    reconcile(client)
    listed = client.get('/api/life/chapters').json()
    assert [item['kind'] for item in listed] == ['hobby'] and listed[0]['title'].startswith('Mira took up ')
    hobby = listed[0]['title'].removeprefix('Mira took up ').removesuffix(' for real')
    assert hobby in current(client)['version']['definition']['interests']
    prompt = client.get('/api/context/preview').json()['prompt']
    assert f'A new chapter, since {listed[0]["started_on"]}: You took up {hobby} for real' in prompt
    why = client.get(f"/api/life/consequences/{listed[0]['consequence']}").json()
    assert why['label'] == "What changes next in Mira's life" and why['options'][3]['label'] == listed[0]['title']

    # The month's chapter day is used: another check the same day begins nothing more.
    reconcile(client)
    assert len(client.get('/api/life/chapters').json()) == 1
    response = client.post(f"/api/life/chapters/{listed[0]['id']}/undo")
    assert response.status_code == 200 and response.json() == []
    assert hobby not in (current(client)['version']['definition'].get('interests') or [])
    assert 'A new chapter' not in client.get('/api/context/preview').json()['prompt']


def test_a_move_changes_the_home_until_undone(client, mira, clock, monkeypatch):
    arrange(client, monkeypatch, clock, 'move')
    old = items(client, 'home')
    reconcile(client)
    listed = client.get('/api/life/chapters').json()
    assert [item['kind'] for item in listed] == ['move'], listed
    hood = listed[0]['title'].removeprefix('Mira moved to ')
    assert current(client)['version']['definition']['location'] == f'{hood}, Baltimore'
    moved = items(client, 'home')
    assert len(moved) == 1 and moved[0]['id'] != old[0]['id']
    client.post(f"/api/life/chapters/{listed[0]['id']}/undo")
    assert [item['id'] for item in items(client, 'home')] == [old[0]['id']]
    assert current(client)['version']['definition']['location'] == 'Fells Point, Baltimore'


def test_a_friend_moving_away_leaves_the_circle(client, mira, clock, monkeypatch):
    arrange(client, monkeypatch, clock, 'friend_moves')
    reconcile(client)
    listed = client.get('/api/life/chapters').json()
    if not listed:
        pytest.skip('no friend in this seeded circle')
    companion = current(client)
    with client.app.state.database.connect() as connection:
        gone = [person for person in circle.people(connection, companion['active_timeline_id'], include_removed=True)
                if person['status'] == 'removed']
    assert len(gone) == 1 and listed[0]['title'].startswith(f"{gone[0]['name']}, Mira's ")
    client.post(f"/api/life/chapters/{listed[0]['id']}/undo")
    with client.app.state.database.connect() as connection:
        assert all(person['status'] == 'active'
                   for person in circle.people(connection, companion['active_timeline_id'], include_removed=True))


def test_the_user_can_pick_another_chapter_instead(client, mira, clock, monkeypatch):
    arrange(client, monkeypatch, clock, 'hobby')
    reconcile(client)
    listed = client.get('/api/life/chapters').json()
    assert [item['kind'] for item in listed] == ['hobby']
    interests = current(client)['version']['definition'].get('interests') or []
    changed = change(client, listed[0]['consequence'], chapters.KINDS.index('move'))
    assert changed['picked_by'] == 'user' and changed['picked'] == chapters.KINDS.index('move')
    assert [item['kind'] for item in client.get('/api/life/chapters').json()] == ['move']
    definition = current(client)['version']['definition']
    assert definition['location'] != 'Fells Point, Baltimore' and len(definition.get('interests') or []) == len(interests) - 1


def test_nothing_happens_while_they_settle_in(client, mira, clock, monkeypatch):
    arrange(client, monkeypatch, clock, 'hobby')
    monkeypatch.setattr(chapters, 'SETTLE_IN', timedelta(days=45))
    reconcile(client)
    assert client.get('/api/life/chapters').json() == []


def test_a_new_job_changes_their_career(client, mira, clock, monkeypatch):
    arrange(client, monkeypatch, clock, 'new_job')
    before = current(client)['version']['definition'].get('money') or {}
    reconcile(client)
    listed = client.get('/api/life/chapters').json()
    assert [item['kind'] for item in listed] == ['new_job'] and 'started a new job as' in listed[0]['title']
    career = current(client)['version']['definition']['money']['career']
    assert career and career != before.get('career')


def test_a_fork_keeps_the_chapters_begun_before_it(client, mira, clock, monkeypatch, provider):
    from conftest import send
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    arrange(client, monkeypatch, clock, 'hobby')
    reconcile(client)
    sent = send(client, 'How was your day?', 'client-chapter-01')['message']
    listed = client.get('/api/life/chapters').json()
    response = client.post('/api/timelines', json={'message_id': sent['id'], 'text': 'How was your week?'})
    assert response.status_code == 200, response.text
    fork = response.json()['id']
    with client.app.state.database.connect() as connection:
        copied = connection.execute('SELECT * FROM life_chapters WHERE timeline_id=?', (fork,)).fetchall()
        assert [row['title'] for row in copied] == [listed[0]['title']]
        subject = consequences.by_id(connection, copied[0]['consequence_id'])['subject']
    assert subject == f"chapter:{fork}:{listed[0]['started_on']}"
