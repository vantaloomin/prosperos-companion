"""The absence mood from opt-in emotional traits (PRD C6, M4 and the absence acceptance row)."""
from datetime import timedelta

import pytest
from conftest import reconcile, send, show

from companion.memory.context import NEUTRAL_ABSENCE


@pytest.fixture(autouse=True)
def shown(client):
    """The absence mood shows on Today only with Hidden values > Show how they're feeling on."""
    show(client, show_moods=True)


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
    revise(client, emotional_traits=[{'name': 'guilt over absence', 'intensity': 'moderate'},
                                     {'name': 'neediness', 'intensity': 'mild'},
                                     {'name': 'jealousy', 'intensity': 'strong'}])
    result = away(client, clock, days=14)
    assert len(result['run']['plan']) <= 3  # absence never raises catch-up volume
    show(client, show_moods=False)
    assert client.get('/api/today').json()['mood'] is None  # Hidden unless the user turns it on.
    show(client, show_moods=True)
    mood = client.get('/api/today').json()['mood']
    assert mood['intensity'] == 'moderate' and mood['traits'] == ['guilt over absence', 'neediness']
    prompt = system(client)
    assert 'about 14 days' in prompt and '(moderate)' in prompt and NEUTRAL_ABSENCE not in prompt
    clock.advance(timedelta(hours=5))
    reconcile(client)
    assert client.get('/api/today').json()['mood']['id'] == mood['id']


def test_removing_the_trait_stops_the_mood_from_the_next_reply(client, life, clock):
    revise(client, emotional_traits=[{'name': 'Sulking', 'intensity': 'strong'}])
    away(client, clock)
    assert client.get('/api/today').json()['mood']['intensity'] == 'strong'
    revise(client, emotional_traits=[{'name': 'Sulking', 'intensity': 'mild'}])
    assert client.get('/api/today').json()['mood']['intensity'] == 'mild'
    revise(client, emotional_traits=[])
    assert client.get('/api/today').json()['mood'] is None
    prompt = system(client)
    assert 'mood about time apart' not in prompt and NEUTRAL_ABSENCE in prompt


def test_the_user_can_reset_the_mood(client, life, clock):
    revise(client, emotional_traits=[{'name': 'guilt over absence', 'intensity': 'mild'}])
    away(client, clock)
    mood = client.get('/api/today').json()['mood']
    assert client.post(f"/api/today/mood/{mood['id']}/reset").json() == {'mood': None}
    assert 'mood about time apart' not in system(client)


def test_a_paused_interval_is_not_an_absence(client, life, clock):
    revise(client, emotional_traits=[{'name': 'guilt over absence', 'intensity': 'strong'}])
    send(client, 'Pausing for a while', 'client-pause-01')
    client.post('/api/pause')
    clock.advance(timedelta(days=3))
    client.post('/api/resume')
    reconcile(client)
    assert client.get('/api/today').json()['mood'] is None


def test_traits_without_absence_words_record_no_mood(client, life, clock):
    revise(client, emotional_traits=[{'name': 'jealousy', 'intensity': 'strong'}])
    away(client, clock)
    assert client.get('/api/today').json()['mood'] is None


def test_controls_stay_neutral_with_traits(client, companion):
    revise(client, emotional_traits=[{'name': 'guilt over absence', 'intensity': 'strong'}])
    for response in (client.post('/api/pause'), client.post('/api/resume'), client.get('/api/settings'),
                     client.get('/api/life/settings')):
        assert 'guilt' not in response.text.lower() and 'hurt' not in response.text.lower()
