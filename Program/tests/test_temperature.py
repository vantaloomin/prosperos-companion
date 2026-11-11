"""Celsius or Fahrenheit (companion/world/temperature.py): picked by the companion's city, kept in Settings."""
from datetime import date

from conftest import reconcile, send

from companion.life import agenda
from companion.world import catalog, paper, temperature


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def move_to(client, city: str, zone: str):
    found = client.get('/api/companion').json()['companion']
    ok(client.post('/api/companion/versions', json={
        'definition': {**found['version']['definition'], 'home_city': city, 'timezone': zone},
        'expected_version_id': found['active_version_id']}))


def test_fahrenheit_in_the_united_states_and_celsius_everywhere_else():
    assert temperature.of_city({'country': 'US'}) == 'F'
    assert temperature.of_city({'country': 'United States'}) == 'F'
    assert temperature.of_city({'country': 'United Kingdom'}) == 'C'
    assert temperature.of_city({'country': 'The Alnhama Republic'}) == 'C'
    assert temperature.of_city(None) == 'F'
    assert temperature.text(48, 'F') == '48°F' and temperature.text(48, 'C') == '9°C'
    assert temperature.degrees(-40, 'C') == -40


def test_the_weather_words_and_the_paper_say_celsius():
    assert agenda.weather_text({'high_f': 70, 'low_f': 55, 'rain': True, 'note': 'x'}, 'C') == \
        'High 21°C, low 13°C, with rain.'
    text = paper.weather(catalog.city('baltimore'), [date(2026, 1, 5 + offset) for offset in range(7)], unit='C')
    assert text.startswith('Highs around') and '°C' in text and '°F' not in text


def test_the_city_picks_until_the_user_keeps_one(client, app, connected, provider):
    settings = ok(client.get('/api/settings'))
    assert settings['temperature_unit'] == 'auto'
    move_to(client, 'london', 'Europe/London')
    reconcile(client)
    assert ok(client.get('/api/settings'))['temperature_auto'] == 'C'
    assert ok(client.get('/api/today'))['day']['temperature_unit'] == 'C'
    send(client, 'Cold out?', 'temp-0001')
    assert '°C' in provider.requests[-1]['prompt'] and '°F' not in provider.requests[-1]['prompt']
    saved = ok(client.put('/api/settings', json={'temperature_unit': 'F'}))
    assert saved['temperature_unit'] == 'F' and saved['temperature_auto'] == 'C'
    assert ok(client.get('/api/today'))['day']['temperature_unit'] == 'F'
    assert client.put('/api/settings', json={'temperature_unit': 'K'}).status_code == 422


def test_a_new_world_keeps_the_users_choice(client, companion):
    ok(client.put('/api/settings', json={'temperature_unit': 'C'}))
    made = ok(client.post('/api/worlds', json={}))
    ok(client.post(f"/api/worlds/{made['id']}/switch"))
    assert ok(client.get('/api/settings'))['temperature_unit'] == 'C'
