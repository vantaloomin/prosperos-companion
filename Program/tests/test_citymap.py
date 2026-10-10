"""The city map: their home, usual and recent places, Story mode's scene and every place to click
(companion/life/citymap.py, Hit List #40)."""
from datetime import timedelta

import pytest
from test_network import build
from test_social_circle import make

from companion.characters import require_current
from companion.database import encode
from companion.life import body, citymap


@pytest.fixture(autouse=True)
def steady(monkeypatch):
    monkeypatch.setattr(body, 'state_on', lambda *_args: None)


def read(client):
    response = client.get('/api/life/map')
    assert response.status_code == 200, response.text
    return response.json()


def test_the_map_shows_every_place_in_their_city_near_its_neighbourhood(client):
    assert client.get('/api/life/map').status_code == 409
    make(client, 'Warm and curious.')
    found = read(client)
    assert found['city']['id'] == 'baltimore' and found['city']['real'] is True and found['story'] is False
    hoods = {hood['id']: hood for hood in found['hoods']}
    assert all(len(hood['next']) == citymap.NEXT_TO and hood['id'] not in hood['next'] for hood in hoods.values())
    places = [place for place in found['places'] if place['id'] != '~home']
    assert len(places) > 100 and all(place['approx'] for place in places)
    for place in places:
        hood = hoods[place['hood_id']]
        assert abs(place['lat'] - hood['lat']) <= citymap.SPREAD and abs(place['lon'] - hood['lon']) <= citymap.SPREAD
        assert 2 <= len(place['spots']) <= 4
    assert read(client)['places'] == found['places']


def test_their_home_and_the_places_they_go_are_marked_with_what_happened_there(client, clock):
    make(client, 'Warm and curious.')
    build(client)
    with client.app.state.database.connect(write=True) as connection:
        companion = require_current(connection)
        for index, days in enumerate((1, 9, 40)):
            at = (clock.now() - timedelta(days=days)).isoformat()
            connection.execute(
                'INSERT INTO life_events (id, companion_id, timeline_id, idempotency_key, kind, status, summary, details, '
                "starts_at, ends_at, character_version_id, permission_revision, created_at) VALUES (?, ?, ?, ?, 'routine', "
                "'committed', ?, ?, ?, ?, ?, 0, ?)",
                (f'e{index}', companion['id'], companion['active_timeline_id'], f'k{index}', f'Coffee number {index}.',
                 encode({'place': {'id': 'vaccaros', 'name': "Vaccaro's"}, 'block_kind': 'leisure'}), at, at,
                 companion['active_version_id'], at))
    found = read(client)
    homes = [place for place in found['places'] if place['id'] == '~home']
    assert homes and homes[0]['pins'] == ['home'] and homes[0]['name'] == "Mira's home" and homes[0]['spots']
    cafe = next(place for place in found['places'] if place['id'] == 'vaccaros')
    assert cafe['pins'] == ['recent', 'usual']
    assert [event['summary'] for event in cafe['history']] == ['Coffee number 0.', 'Coffee number 1.', 'Coffee number 2.']


def test_story_mode_marks_the_scene_and_fictional_cities_get_a_sketch(client):
    make(client, 'Warm and curious.')
    assert client.put('/api/settings', json={'story_mode': True}).status_code == 200
    scene = client.get('/api/story').json()['scene']
    found = read(client)
    assert found['story'] is True
    assert [place['id'] for place in found['places'] if 'scene' in place['pins']] == [scene['place']['id']]
    assert citymap.real({'setting': 'fictional'}) is False and citymap.real({'distribution': 'private'}) is False
    assert citymap.real({'setting': 'real'}) is True


def test_usual_and_recent_places_come_from_their_events_and_a_lunch_break_is_not_work(clock):
    now = clock.now()
    events = [{'id': '1', 'place': 'cafe', 'summary': '', 'at': (now - timedelta(days=2)).isoformat(), 'block': 'leisure'},
              {'id': '2', 'place': 'cafe', 'summary': '', 'at': (now - timedelta(days=30)).isoformat(), 'block': 'leisure'},
              {'id': '3', 'place': 'museum', 'summary': '', 'at': (now - timedelta(days=50)).isoformat(), 'block': 'leisure'},
              {'id': '4', 'place': 'office', 'summary': '', 'at': (now - timedelta(days=90)).isoformat(), 'block': 'work'}]
    marked = citymap.marks(events, now)
    assert marked == {'cafe': {'usual', 'recent'}}
