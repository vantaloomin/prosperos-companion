"""A work project the companion says is done is done (companion/life/work_said.py): the next one starts, the old one
comes back when that reply is replaced, and nothing unclear or user-set changes."""
import pytest
from conftest import reconcile, send, set_life

from companion.characters import require_current
from companion.database import decode, encode
from companion.life import body, composer, work, work_said
from companion.providers.chat import Chunk

TITLE = 'the guild register of new apprentices'
WEEKDAYS = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00', 'days': [0, 1, 2, 3, 4]},
            {'key': 'evening', 'label': 'Evening', 'kind': 'leisure', 'start': '17:00', 'end': '23:00'},
            {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]


@pytest.mark.parametrize('text', [
    "guild register's finally sorted. forty names down to twelve", "register's done, finally.",
    'apprentice register is finally done', 'finished the register, thank god', 'handed in the guild register today',
    'the register is all wrapped up'])
def test_saying_the_project_is_done_is_found(text):
    assert work_said.said_done(text, TITLE)


@pytest.mark.parametrize('text', [
    "register's finally out of my hands for the day, clerk took it", "this register's killing me.",
    'register ate my whole morning again', 'spent all morning sorting that register', 'almost done with the register',
    "register won't be done till friday", 'is the register done?', 'the register will be done by tomorrow',
    "i'm done for today, the register can wait", 'finished my coffee, then back to the register',
    'imagine if the register was done already', 'done with the yard, heading home'])
def test_anything_unclear_or_about_something_else_changes_nothing(text):
    assert not work_said.said_done(text, TITLE)


def test_a_title_of_only_common_words_is_never_matched():
    assert work_said.keys('the new project') == set()
    assert not work_said.said_done('the new project is done', 'the new project')


@pytest.fixture
def sett(client, monkeypatch, provider):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(work, 'ACTIVE', True)
    # The register is no clerk's project in the bank: keep it running (work.refreshed would replace it).
    monkeypatch.setattr(work, 'refreshed', lambda _connection, found, *_args: found)
    response = client.post('/api/companion', json={
        'name': 'Sett', 'timezone': 'UTC', 'schedule': WEEKDAYS, 'home_city': 'Baltimore',
        'identity': 'Sett is a clerk at the city records office.', 'personality': 'Dry and warm'})
    assert response.status_code == 200, response.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    set_life(client, automatic_events=True, phrase_with_model=False, catch_up_max_events=6,
             catch_up_lookback_hours=168)
    reconcile(client)
    with client.app.state.database.connect(write=True) as connection:
        found = work.state(connection, response.json()['active_timeline_id'])
        project = {**found['project'], 'title': TITLE, 'started': '2026-09-20', 'due': '2026-11-30'}
        connection.execute('UPDATE work_life SET project=? WHERE timeline_id=?',
                           (encode(project), found['timeline_id']))
    client.fake = provider
    return response.json()


def says(client, text, client_id):
    client.fake.replies.append([Chunk(text), Chunk('', 'stop')])
    return send(client, 'how was work?', client_id)


def project(client):
    return client.get('/api/life/work').json()['work']


def test_saying_it_is_done_ends_the_project_and_the_next_starts(client, sett):
    says(client, "register's done, finally. sorted the apprentices from the dead weight", 'work-said-1')
    view = project(client)
    assert view['project']['title'] != TITLE and view['project']['index'] == 1
    assert any(event['text'].startswith(f'wrapped up {TITLE};') for event in view['events'])
    with client.app.state.database.connect() as connection:
        lines = [line for _key, line in work.context_lines(connection, require_current(connection),
                                                           client.app.state.database.clock.now())]
    assert not any(f'in the middle of {TITLE}' in line for line in lines)
    assert any(f'wrapped up {TITLE}' in line for line in lines)


def test_upcoming_days_that_named_the_old_project_are_drawn_again(client, sett):
    database = client.app.state.database
    with database.connect(write=True) as connection:
        row = connection.execute("SELECT id, entry FROM life_agenda WHERE subject='companion' AND status='upcoming' "
                                 'AND starts_at>? AND entry IS NOT NULL ORDER BY starts_at DESC LIMIT 1',
                                 (database.now(),)).fetchone()
        entry = {**decode(row['entry']), 'summary': f'Sett spent the shift buried in {TITLE}.'}
        connection.execute('UPDATE life_agenda SET entry=? WHERE id=?', (encode(entry), row['id']))
    says(client, 'finished the guild register, thank god', 'work-said-2')
    with database.connect() as connection:
        assert connection.execute('SELECT 1 FROM life_agenda WHERE id=?', (row['id'],)).fetchone() is None


def test_a_replaced_reply_brings_the_project_back(client, sett):
    sent = says(client, 'apprentice register is finally done', 'work-said-3')
    assert project(client)['project']['title'] != TITLE
    client.fake.replies.append([Chunk('long day, the usual'), Chunk('', 'stop')])
    response = client.post(f"/api/conversation/messages/{sent['message']['id']}/alternatives")
    assert response.status_code == 200, response.text
    view = project(client)
    assert view['project']['title'] == TITLE and view['project']['index'] == 0
    assert not any(event['text'].startswith(f'wrapped up {TITLE}') for event in view['events'])


def test_a_hedge_changes_nothing(client, sett):
    says(client, "register's finally out of my hands for the day", 'work-said-4')
    assert project(client)['project']['title'] == TITLE


def test_a_project_the_user_wrote_stays(client, sett):
    response = client.put('/api/life/work/project', json={'title': TITLE})
    assert response.status_code == 200, response.text
    says(client, "register's done, finally.", 'work-said-5')
    assert project(client)['project']['title'] == TITLE


def test_a_title_word_that_is_not_what_it_is_about_is_not_enough():
    assert work_said.head(TITLE) == 'register'
    assert not work_said.said_done('sorted the apprentices into two groups', TITLE)
    assert work_said.said_done('the apprentices for the guild are all sorted', TITLE)


def test_a_world_whose_companion_already_said_it_was_done_heals_with_the_next_reply(client, sett, monkeypatch):
    real = work_said.notice
    monkeypatch.setattr(work_said, 'notice', lambda *_args: False)  # As before 1.4.2: nothing reads the reply.
    says(client, "register's done, finally.", 'work-said-6')
    assert project(client)['project']['title'] == TITLE
    monkeypatch.setattr(work_said, 'notice', real)
    says(client, 'long day, the usual', 'work-said-7')
    view = project(client)
    assert view['project']['title'] != TITLE and view['project'].get('read_back')
