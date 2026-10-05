"""Opt-in emotional traits and the absence mood (PRD C6, M4 and the absence acceptance row)."""
from datetime import timedelta

from conftest import reconcile, send

from companion.memory.context import NEUTRAL_ABSENCE


def revise(client, **changes):
    current = client.get('/api/companion').json()['companion']
    definition = {**current['version']['definition'], **changes}
    return client.post('/api/companion/versions', json={'definition': definition,
                                                         'expected_version_id': current['active_version_id']})


def system(client):
    return client.get('/api/context/preview').json()['system']


def away(client, clock, days=3):
    send(client, 'See you soon', 'client-away-01')
    clock.advance(timedelta(days=days))
    return reconcile(client)


def test_without_traits_absence_is_neutral(client, life, clock):
    away(client, clock)
    assert client.get('/api/today').json()['mood'] is None
    prompt = system(client)
    assert NEUTRAL_ABSENCE in prompt and 'mood about time apart' not in prompt


def test_absence_trait_creates_a_visible_mood_at_the_chosen_intensity(client, life, clock):
    revise(client, emotional_traits=[{'trait': 'guilt_over_absence', 'intensity': 3},
                                     {'trait': 'neediness', 'intensity': 2}])
    result = away(client, clock, days=14)
    assert len(result['run']['plan']) <= 3  # absence never raises catch-up volume
    mood = client.get('/api/today').json()['mood']
    assert mood['intensity'] == 3 and mood['traits'] == ['guilt_over_absence', 'neediness']
    prompt = system(client)
    assert 'about 14 days' in prompt and '(intensity 3/5)' in prompt and NEUTRAL_ABSENCE not in prompt
    assert 'guilt over absence (3/5)' in prompt
    clock.advance(timedelta(hours=5))
    reconcile(client)
    assert client.get('/api/today').json()['mood']['id'] == mood['id']


def test_removing_the_trait_stops_the_mood_from_the_next_reply(client, life, clock):
    revise(client, emotional_traits=[{'trait': 'sulking', 'intensity': 4}])
    away(client, clock)
    assert client.get('/api/today').json()['mood']['intensity'] == 4
    revise(client, emotional_traits=[{'trait': 'sulking', 'intensity': 1}])
    assert client.get('/api/today').json()['mood']['intensity'] == 1
    revise(client, emotional_traits=[])
    assert client.get('/api/today').json()['mood'] is None
    prompt = system(client)
    assert 'mood about time apart' not in prompt and NEUTRAL_ABSENCE in prompt


def test_the_user_can_reset_the_mood(client, life, clock):
    revise(client, emotional_traits=[{'trait': 'guilt_over_absence', 'intensity': 2}])
    away(client, clock)
    mood = client.get('/api/today').json()['mood']
    assert client.post(f"/api/today/mood/{mood['id']}/reset").json() == {'mood': None}
    assert 'mood about time apart' not in system(client)


def test_a_paused_interval_is_not_an_absence(client, life, clock):
    revise(client, emotional_traits=[{'trait': 'guilt_over_absence', 'intensity': 5}])
    send(client, 'Pausing for a while', 'client-pause-01')
    client.post('/api/pause')
    clock.advance(timedelta(days=3))
    client.post('/api/resume')
    reconcile(client)
    assert client.get('/api/today').json()['mood'] is None


def test_jealousy_without_romance_is_never_romantic_exclusivity(client, companion):
    revise(client, emotional_traits=[{'trait': 'jealousy', 'intensity': 2}])
    assert 'never express jealousy or possessiveness as romantic exclusivity' in system(client)
    revise(client, relationship='romance')
    assert 'romantic exclusivity' not in system(client)


def test_traits_are_validated(client, companion):
    duplicate = [{'trait': 'jealousy', 'intensity': 2}, {'trait': 'jealousy', 'intensity': 3}]
    assert revise(client, emotional_traits=duplicate).status_code == 422
    assert revise(client, emotional_traits=[{'trait': 'jealousy', 'intensity': 6}]).status_code == 422
    assert client.get('/api/companion').json()['companion']['version']['definition']['emotional_traits'] == []


def test_controls_stay_neutral_with_traits(client, companion):
    revise(client, emotional_traits=[{'trait': 'guilt_over_absence', 'intensity': 5}])
    for response in (client.post('/api/pause'), client.post('/api/resume'), client.get('/api/settings'),
                     client.get('/api/life/settings')):
        assert 'guilt' not in response.text.lower() and 'hurt' not in response.text.lower()
