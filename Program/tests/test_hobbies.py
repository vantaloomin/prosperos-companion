"""Hobbies that progress (companion/life/hobbies.py): pastimes from their interests, practice that adds up,
milestones, dry spells, money, the chat and doing them together."""
import re
from datetime import date, timedelta

import pytest
from conftest import reconcile, send, set_life, show

from companion.database import decode
from companion.life import body, composer, hobbies, outings
from companion.providers.chat import Chunk
from companion.world import catalog
from companion.world.source import CatalogWorld

WORLD = CatalogWorld()
TODAY = date(2026, 10, 5)  # A Monday.
EVENINGS = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00', 'days': [0, 1, 2, 3, 4]},
            {'key': 'evening', 'label': 'Evening', 'kind': 'leisure', 'start': '17:00', 'end': '23:00'},
            {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]


def test_interests_name_pastimes_by_their_words_and_era():
    assert hobbies.match('bouldering on weekends')['id'] == 'climbing'
    assert hobbies.match('Calligraphy')['id'] == 'calligraphy'
    assert hobbies.match('learning Spanish')['id'] == 'spanish'
    assert hobbies.match('French cooking') is None and hobbies.match('true crime podcasts') is None
    assert hobbies.match('playing the lute', 'medieval')['id'] == 'lute'
    assert hobbies.match('rock climbing', 'medieval') is None
    assert hobbies.custom('metal detecting')['kind'] == 'general'


def test_the_app_picks_pastimes_that_fit_the_city():
    camelot, baltimore = WORLD.find('Camelot'), WORLD.find('Baltimore')
    picked = [hobbies.choose_new(f'seed{n}', 'first', {'name': 'Ash'}, camelot, []) for n in range(30)]
    assert all(hobbies.in_era(item['eras'], 'medieval') for item in picked)
    surfing = hobbies.by_id()['surfing']
    assert hobbies.available(surfing, baltimore) == bool(hobbies.places_for(surfing, baltimore))


@pytest.fixture
def kim(client, monkeypatch, provider):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(composer, 'PLAN_SHARE', 0)
    monkeypatch.setattr(composer, 'THREAD_SHARE', 0)
    monkeypatch.setattr(hobbies, 'WEAVE', True)
    # Their dice are seeded on the timeline's random id; no stalls keeps these checks from depending on the roll.
    monkeypatch.setattr(hobbies, 'STALL', (0.0, 0.0, 0.0, 0.0))
    response = client.post('/api/companion', json={
        'name': 'Kim', 'timezone': 'UTC', 'schedule': EVENINGS, 'home_city': 'Baltimore',
        'identity': 'They are a nurse.', 'interests': ['rock climbing', 'the cello', 'true crime podcasts']})
    assert response.status_code == 200, response.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    set_life(client, automatic_events=True, phrase_with_model=False)
    return response.json()


def rows(client):
    with client.app.state.database.connect() as connection:
        return connection.execute('SELECT * FROM hobbies ORDER BY position').fetchall()


def walk(client, days):
    """Walk their pastimes `days` ahead of today, as the agenda would."""
    database = client.app.state.database
    with database.connect(write=True) as connection:
        timeline = connection.execute('SELECT active_timeline_id FROM companions').fetchone()['active_timeline_id']
        definition = decode(connection.execute('SELECT definition FROM character_versions').fetchone()['definition'])
        life = hobbies.life_for(connection, timeline, definition, WORLD, database.clock.now())
        hobbies.evolve(life, TODAY + timedelta(days=days), database.clock.now())
        return timeline


def test_written_interests_come_first_and_the_panel_says_it_in_words(client, kim):
    view = client.get('/api/life/hobbies').json()
    found = {item['label']: item for item in view['hobbies']}
    assert {'Rock climbing', 'Cello'} <= set(found)
    assert found['Rock climbing']['source'] == 'interest' and found['Rock climbing']['status'] == 'active'
    assert found['Cello']['level_text'].endswith('the cello') and found['Cello']['since_text'].endswith(' in')
    assert 'numbers' not in found['Cello']
    show(client, show_home_meters=True)
    assert 'numbers' in client.get('/api/life/hobbies').json()['hobbies'][0]


def test_practice_adds_up_to_milestones_the_same_way_every_time(client, kim):
    client.get('/api/life/hobbies')
    before = {row['id']: row['skill'] for row in rows(client)}
    walk(client, 120)
    after = rows(client)
    assert all(row['skill'] > before[row['id']] for row in after if row['status'] == 'active' and row['id'] in before)
    with client.app.state.database.connect() as connection:
        found = connection.execute("SELECT * FROM hobby_log WHERE kind='milestone'").fetchall()
        sessions = connection.execute("SELECT COUNT(*) AS n FROM hobby_log WHERE kind='session'").fetchone()['n']
    assert found and sessions > 30
    assert all(item['text'][:1].islower() and '{' not in item['text'] for item in found)
    # Rewinding to today and walking again gives the same life.
    texts = sorted(item['text'] for item in found)
    database = client.app.state.database
    with database.connect(write=True) as connection:
        timeline = connection.execute('SELECT active_timeline_id FROM companions').fetchone()['active_timeline_id']
        definition = decode(connection.execute('SELECT definition FROM character_versions').fetchone()['definition'])
        life = hobbies.life_for(connection, timeline, definition, WORLD, database.clock.now())
        hobbies.rewind(life, TODAY, database.clock.now())
        hobbies.evolve(life, TODAY + timedelta(days=120), database.clock.now())
        again = connection.execute("SELECT text FROM hobby_log WHERE kind='milestone'").fetchall()
    assert sorted(item['text'] for item in again) == texts


def test_written_interests_are_never_given_up_and_the_slider_off_stops_everything(client, kim, monkeypatch):
    monkeypatch.setattr(hobbies, 'STALL', (0.0, 0.02, 0.05, 0.09))
    set_life(client, hobbies_realism=3)
    client.get('/api/life/hobbies')
    walk(client, 500)
    assert not [row for row in rows(client) if row['source'] == 'interest' and row['status'] == 'dropped']
    set_life(client, hobbies_realism=0)
    walk(client, 520)
    with client.app.state.database.connect() as connection:
        late = connection.execute("SELECT COUNT(*) AS n FROM hobby_log WHERE kind!='mark' AND local_date>?",
                                  ((TODAY + timedelta(days=501)).isoformat(),)).fetchone()['n']
    assert late == 0


def test_the_user_adds_keeps_and_gives_up_pastimes(client, kim):
    client.get('/api/life/hobbies')
    view = client.post('/api/life/hobbies', json={'name': 'metal detecting', 'level': 2}).json()
    added = next(item for item in view['hobbies'] if item['label'] == 'Metal detecting')
    assert added['source'] == 'user' and added['kept'] and added['level'] == 2
    view = client.patch(f"/api/life/hobbies/{added['id']}", json={'status': 'dropped'}).json()
    gone = next(item for item in view['hobbies'] if item['id'] == added['id'])
    assert gone['status'] == 'dropped' and gone['status_text'].startswith('Gave it up')
    cello = next(item for item in view['hobbies'] if item['label'] == 'Cello')
    view = client.patch(f"/api/life/hobbies/{cello['id']}", json={'level': 4}).json()
    assert next(item for item in view['hobbies'] if item['id'] == cello['id'])['level'] == 4
    assert client.patch('/api/life/hobbies/nope', json={'level': 1}).status_code == 404
    assert client.post('/api/life/hobbies', json={'name': ''}).status_code == 422


def test_sessions_take_free_evenings_and_reach_the_chat(client, kim, provider, clock):
    for _day in range(6):
        reconcile(client)
        clock.advance(timedelta(days=1))
    with client.app.state.database.connect() as connection:
        entries = [decode(row['entry']) for row in connection.execute(
            "SELECT entry FROM life_agenda WHERE subject='companion' AND entry IS NOT NULL").fetchall()]
    sessions = [entry for entry in entries if entry.get('hobby')]
    assert sessions and all(entry['activity'] == 'hobby' and entry['summary'].startswith('Kim ') for entry in sessions)
    provider.replies.append([Chunk('Hey!'), Chunk('', 'stop')])
    send(client, 'How was your week?', 'client-hobby-1')
    prompt = provider.requests[-1]['prompt']
    assert '## Your pastimes' in prompt and '- Rock climbing:' in prompt


def test_fees_and_gear_count_as_spending(client, kim):
    client.get('/api/life/hobbies')
    timeline = walk(client, 60)
    with client.app.state.database.connect() as connection:
        bought = hobbies.purchases(connection, timeline, TODAY, TODAY + timedelta(days=60))
    assert bought and all(item['for'] == 'hobby' and item['spend'] for item in bought)


def test_the_user_suggests_one_of_their_pastimes(client, kim, provider):
    client.get('/api/life/hobbies')
    provider.replies.append([Chunk('Yes! Let us.'), Chunk('', 'stop')])
    send(client, 'Want to go climbing together Saturday?', 'client-hobby-2')
    [outing] = client.get('/api/life/outings').json()['outings']
    assert outing['activity'] == 'hobby' and outing['local_date'] == '2026-10-10'
    assert outing['place']['hobby']['label'] == 'Rock climbing'


def test_a_proposal_names_the_pastime_before_any_other_outing():
    found = outings.proposal('Want to go climbing with me Saturday?', TODAY, {}, catalog.city('baltimore'),
                             pastimes=[{'id': 'row1', 'pattern': re.compile(r'\bclimb\w*', re.I)}])
    assert found['activity'] == 'hobby' and found['hobby'] == 'row1'
    plain = outings.proposal('Want to get dinner Saturday?', TODAY, {}, catalog.city('baltimore'),
                             pastimes=[{'id': 'row1', 'pattern': re.compile(r'\bclimb\w*', re.I)}])
    assert plain['activity'] == 'dinner' and plain['hobby'] is None


def test_bank_lines_about_them_are_said_to_them_in_the_chat():
    assert hobbies.yours('learned their first barre chord, which they had wanted for themselves') == \
        'learned your first barre chord, which you had wanted for yourself'
    assert hobbies.yours('theory class') == 'theory class'
