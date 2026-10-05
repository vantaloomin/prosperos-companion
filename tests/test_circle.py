"""The social circle and precomputed agenda (PRD T8, T9)."""
import asyncio
from datetime import timedelta

import pytest
from conftest import life_reply, reconcile, set_life

from companion.clock import parse, stamp
from companion.database import decode
from companion.life import agenda, circle, composer
from companion.world.source import CatalogWorld

EVENING_OUT = [{'key': 'day', 'label': 'Day', 'kind': 'leisure', 'start': '09:00', 'end': '17:00'},
               {'key': 'out', 'label': 'Evening out', 'kind': 'social', 'start': '19:00', 'end': '22:00'},
               {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]


@pytest.fixture
def baltimore(client, monkeypatch):
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(composer, 'PLAN_SHARE', 0)
    monkeypatch.setattr(composer, 'THREAD_SHARE', 0)
    response = client.post('/api/companion', json={'name': 'Mira', 'timezone': 'America/New_York',
                                                     'location': 'Fells Point, Baltimore', 'schedule': EVENING_OUT})
    assert response.status_code == 200, response.text
    return response.json()


def rows(client, **where):
    clauses = ' AND '.join(f'{key}=?' for key in where) or '1=1'
    with client.app.state.database.connect() as connection:
        return [dict(row) for row in connection.execute(
            f'SELECT * FROM life_agenda WHERE {clauses} ORDER BY starts_at, subject', tuple(where.values()))]


def test_the_circle_is_assembled_from_the_city_data(client, baltimore):
    people = client.get('/api/life/circle').json()
    assert len(people) == circle.CIRCLE_SIZE and people[0]['role'] == 'close friend'
    names = [person['name'] for person in people]
    assert len(set(names)) == len(names) and 'Mira' not in names
    local = [person for person in people if person['local']]
    assert local
    for person in local:
        assert person['city'] == 'Baltimore' and person['neighborhood'] and person['haunts'] and person['schedule']
    for person in people:
        assert person['full_name'].startswith(person['name']) and person['age'] > 0
        if not person['local']:
            assert person['schedule'] == [] and person['now'] is None
    # Reading it again never assembles a second circle.
    assert [person['id'] for person in client.get('/api/life/circle').json()] == [person['id'] for person in people]


def test_assembly_is_deterministic():
    data = CatalogWorld().find('baltimore')
    first = circle.assemble('circle:t:1', 1, {'name': 'Mira'}, data, {'Mira'})
    assert circle.assemble('circle:t:1', 1, {'name': 'Mira'}, data, {'Mira'}) == first
    assert circle.assemble('circle:t:2', 2, {'name': 'Mira'}, data, {'Mira'}) != first


def test_the_week_ahead_is_precomputed_and_stays_hidden(client, baltimore, clock):
    clock.advance(timedelta(days=2))
    reconcile(client)
    now = clock.now()
    entries = rows(client)
    assert max(parse(row['ends_at']) for row in entries) > now + timedelta(days=6)
    assert all(row['status'] == 'upcoming' for row in entries if parse(row['ends_at']) > now)
    assert all(row['status'] == 'happened' for row in entries if parse(row['ends_at']) <= now)
    person = client.get('/api/life/circle').json()[0]
    diary = client.get(f"/api/life/circle/{person['id']}/diary").json()
    assert diary and all(parse(item['ends_at']) <= now for item in diary)
    assert person['recent'] == diary[:3]


def test_filling_in_downtime_matches_running_all_day(client, baltimore, clock):
    """A server ticking every few hours and one opened after three days reach the same entries."""
    client.put('/api/settings', json={'background_activity': True})
    engine = client.app.state.life
    for _ in range(18):
        clock.advance(timedelta(hours=4))
        asyncio.run(engine.reconcile('background'))
    ticked = {(row['subject'], row['slot_key']): row['entry'] for row in rows(client)
              if parse(row['ends_at']) <= clock.now()}
    with client.app.state.database.connect(write=True) as connection:
        connection.execute('DELETE FROM life_agenda')
        connection.execute('DELETE FROM agenda_cursors')
    reconcile(client)
    filled = {(row['subject'], row['slot_key']): row['entry'] for row in rows(client)
              if parse(row['ends_at']) <= clock.now()}
    assert ticked and filled == ticked


def test_social_slots_name_a_free_circle_member(client, baltimore, clock):
    clock.advance(timedelta(days=1))
    reconcile(client)
    social = [row for row in rows(client, subject='companion') if decode(row['block'])['kind'] == 'social']
    named = [decode(row['entry']) for row in social if decode(row['entry']).get('with')]
    assert named
    for row in social:
        entry = decode(row['entry'])
        if not entry.get('with'):
            continue
        assert entry['with']['name'] in entry['summary']
        busy = [other for other in rows(client, subject=entry['with']['id'])
                if other['starts_at'] < row['ends_at'] and other['ends_at'] > row['starts_at']]
        assert all(decode(other['block'])['kind'] not in agenda.BUSY for other in busy)


def test_a_simulated_event_uses_the_precomputed_entry(client, baltimore, clock):
    set_life(client, phrase_with_model=False, catch_up_max_events=6, catch_up_lookback_hours=96)
    clock.advance(timedelta(hours=1))
    reconcile(client)
    clock.advance(timedelta(days=2))
    events = reconcile(client)['run']['results']
    with client.app.state.database.connect() as connection:
        for result in events:
            event = dict(connection.execute('SELECT * FROM life_events WHERE id=?', (result['event_id'],)).fetchone())
            entry = decode(connection.execute(
                "SELECT entry FROM life_agenda WHERE subject='companion' AND slot_key=?",
                (decode(event['details'])['slot'],)).fetchone()['entry'])
            assert event['summary'] == entry['summary']
            assert decode(event['details'])['with'] == entry.get('with')


def test_changing_the_character_rebuilds_upcoming_entries(client, baltimore, clock):
    clock.advance(timedelta(days=1))
    reconcile(client)
    before = rows(client, subject='companion')
    current = client.get('/api/companion').json()['companion']
    definition = {**current['version']['definition'], 'schedule': EVENING_OUT[1:]}
    client.post('/api/companion/versions', json={'definition': definition,
                                                  'expected_version_id': current['active_version_id']})
    reconcile(client)
    after = rows(client, subject='companion')
    version_id = client.get('/api/companion').json()['companion']['active_version_id']
    upcoming = [row for row in after if row['status'] == 'upcoming']
    assert upcoming and all(row['basis'] == version_id for row in upcoming)
    assert not any(row['slot_key'].startswith('day@') for row in upcoming)
    # What already happened is kept.
    assert [row for row in after if row['status'] == 'happened'] == \
           [row for row in before if row['status'] == 'happened']


def test_rename_and_remove_rebuild_entries_that_name_the_person(client, baltimore, clock):
    clock.advance(timedelta(hours=1))
    reconcile(client)
    named = [decode(row['entry'])['with'] for row in rows(client, subject='companion', status='upcoming')
             if row['entry'] and decode(row['entry']).get('with')]
    assert named
    person_id = named[0]['id']
    renamed = client.patch(f'/api/life/circle/{person_id}', json={'name': 'Rowan'}).json()
    assert renamed['name'] == 'Rowan' and renamed['revision'] == 2
    for row in rows(client, subject='companion', status='upcoming'):
        entry = decode(row['entry']) if row['entry'] else {}
        if (entry.get('with') or {}).get('id') == person_id:
            assert entry['with']['name'] == 'Rowan' and 'Rowan' in entry['summary']
    assert all('Rowan' in decode(row['entry'])['summary']
               for row in rows(client, subject=person_id, status='upcoming') if row['entry'])
    removed = client.post(f'/api/life/circle/{person_id}/remove').json()
    assert removed['status'] == 'removed'
    assert rows(client, subject=person_id, status='upcoming') == []
    assert not any((decode(row['entry']) or {}).get('with', {}) and decode(row['entry'])['with']['id'] == person_id
                   for row in rows(client, subject='companion', status='upcoming') if row['entry'])
    assert person_id not in [person['id'] for person in client.get('/api/life/circle').json()]
    restored = client.post(f'/api/life/circle/{person_id}/restore').json()
    assert restored['status'] == 'active' and rows(client, subject=person_id, status='upcoming')


def test_a_pause_skips_entries_in_the_paused_interval(client, baltimore, clock):
    reconcile(client)
    paused_at = clock.now()
    client.post('/api/pause')
    clock.advance(timedelta(days=2))
    resumed_at = clock.now()
    client.post('/api/resume')
    reconcile(client)
    inside = [row for row in rows(client) if row['starts_at'] >= stamp(paused_at) and row['ends_at'] <= stamp(resumed_at)]
    assert inside and all(row['status'] == 'skipped' for row in inside)


def test_chat_context_names_the_circle(client, baltimore, provider, clock):
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    clock.advance(timedelta(days=1))
    reconcile(client)
    client.post('/api/conversation/messages', json={'text': 'How is everyone?', 'client_id': 'circle-0001'})
    system = provider.requests[-1]['system']
    assert 'People in your life' in system
    for person in client.get('/api/life/circle').json():
        assert person['name'] in system


def test_wording_prepared_ahead_is_used_when_its_slot_is_simulated(client, baltimore, provider, clock):
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    provider.respond = life_reply
    set_life(client, catch_up_max_events=6, catch_up_lookback_hours=96)
    engine = client.app.state.life
    assert asyncio.run(engine.prepare_now(limit=50))['prepared'] > 0
    phrasings = len([request for request in provider.requests if 'Rephrase one' in request['system']])
    clock.advance(timedelta(days=2))
    results = reconcile(client)['run']['results']
    events = {event['id']: event for event in client.get('/api/events?history=true').json()}
    used = [events[result['event_id']] for result in results if result.get('event_id') in events]
    assert used and all(event['inputs'].get('prepared') for event in used)
    assert all(event['summary'].startswith('Phrased: ') for event in used)
    # Nothing was phrased again on return.
    assert len([request for request in provider.requests if 'Rephrase one' in request['system']]) == phrasings
    assert asyncio.run(engine.prepare_now())['prepared'] == 2


def test_prepared_wording_from_another_model_is_not_used(client, baltimore, provider, clock):
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    provider.respond = life_reply
    engine = client.app.state.life
    asyncio.run(engine.prepare_now(limit=50))
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'other-model',
                                        'api_key': 'secret-key'})
    clock.advance(timedelta(days=1))
    results = reconcile(client)['run']['results']
    events = {event['id']: event for event in client.get('/api/events?history=true').json()}
    used = [events[result['event_id']] for result in results if result.get('event_id') in events]
    assert used and not any(event['inputs'].get('prepared') for event in used)
    assert all(event['inputs']['model'] == 'other-model' for event in used)


def test_prepare_returns_at_once(client, baltimore):
    assert client.post('/api/life/prepare').json()['state'] in {'started', 'in_progress'}


def test_places_are_open_at_the_time_of_their_slot(client, baltimore, clock):
    clock.advance(timedelta(days=1))
    reconcile(client)
    data = CatalogWorld().find('baltimore')
    open_at = {place['id']: place['day_parts'] for place in data['places']}
    placed = [row for row in rows(client) if row['entry'] and decode(row['entry'])['place']]
    assert placed
    for row in placed:
        place = decode(row['entry'])['place']
        if place['id'] in open_at:
            assert composer.day_part(decode(row['block'])['start']) in open_at[place['id']]


def test_circle_members_favor_their_haunts(client, baltimore, clock):
    clock.advance(timedelta(days=3))
    reconcile(client)
    people = {person['id']: person for person in client.get('/api/life/circle').json() if person['local']}
    visited = [(people[row['subject']], decode(row['entry'])['place']['name']) for row in rows(client)
               if row['subject'] in people and row['entry'] and decode(row['entry'])['place']]
    assert any(name in person['haunts'] for person, name in visited)


def test_a_shared_outing_shows_in_the_friends_diary(client, baltimore, clock):
    set_life(client, automatic_events=True, catch_up_max_events=6, catch_up_lookback_hours=96)
    clock.advance(timedelta(hours=1))
    reconcile(client)
    clock.advance(timedelta(days=3))
    reconcile(client)
    shared = [event for event in client.get('/api/events').json() if event['details'].get('with')]
    assert shared
    event = shared[0]
    diary = client.get(f"/api/life/circle/{event['details']['with']['id']}/diary?limit=100").json()
    assert {'event_id': event['id'], 'summary': event['summary']} in [item['with_companion'] for item in diary]


def test_chat_knows_the_companions_likely_next_plans(client, baltimore, provider, clock):
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model',
                                        'api_key': 'secret-key'})
    reconcile(client)
    client.post('/api/conversation/messages', json={'text': 'What are you up to later?', 'client_id': 'plans-0001'})
    system = provider.requests[-1]['system']
    assert 'likely to do next' in system
    upcoming = [row for row in rows(client, subject='companion', status='upcoming') if row['entry']
                and parse(row['starts_at']) > clock.now()]
    assert decode(upcoming[0]['entry'])['activity'].replace('-', ' ') in system
    # Intentions are not events: nothing was proposed or committed for them.
    assert client.get('/api/events?history=true').json() == []
