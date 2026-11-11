"""Weather that settles in (companion/world/skies.py, Hit List #88): fronts, the Weather step, tomorrow."""
from collections import Counter
from datetime import date, timedelta

from conftest import reconcile, send, set_life

from companion.life import agenda
from companion.world import catalog, generators, paper, skies


def baltimore() -> dict:
    return catalog.city('baltimore')


def days(start: date, count: int):
    return [start + timedelta(days=offset) for offset in range(count)]


def year(data: dict, level: int = skies.TRUE_TO_LIFE, start: date = date(2026, 1, 1)) -> list[dict]:
    return [generators.conditions(data, day, level) for day in days(start, 365 * 3)]


def spells(found: list[dict]) -> float:
    """The average run of days under one sky."""
    runs, length = [], 1
    for before, after in zip(found, found[1:]):
        if after['sky'] == before['sky']:
            length += 1
        else:
            runs.append(length)
            length = 1
    return sum(runs) / len(runs)


def test_a_sky_settles_in_for_a_few_days_and_the_month_keeps_its_rain():
    data = baltimore()
    found = year(data)
    kept = sum(after['sky'] == before['sky'] for before, after in zip(found, found[1:])) / (len(found) - 1)
    assert 0.45 <= kept <= 0.7  # The 45% rule, plus a fresh draw that lands on the same sky.
    assert spells(found) >= 1.8
    for month in (1, 4, 7, 10):
        those = [item for item in found if item['month'] == month]
        wet = sum(item['rain'] for item in those) / len(those) * 30
        assert abs(wet - data['climate']['months'][month - 1]['rain_days']) <= 4, (month, wet)


def test_the_day_is_the_same_for_everyone_and_reads_like_weather():
    data = baltimore()
    day = date(2026, 1, 14)
    assert generators.conditions(data, day) == generators.conditions(catalog.city('baltimore'), day)
    item = generators.conditions(data, day)
    assert set(item) >= {'sky', 'days', 'high_f', 'low_f', 'rain', 'season', 'note', 'typical'}
    assert item['sky'] in skies.SKIES and item['low_f'] < item['high_f']
    assert item['rain'] == (item['sky'] in {'rain', 'storm', 'snow'})


def test_snow_only_when_it_is_cold_enough_and_never_on_a_warm_day():
    found = year(baltimore())
    snowy = [item for item in found if item['sky'] == 'snow']
    assert snowy and all(item['month'] in (11, 12, 1, 2, 3) and item['high_f'] <= skies.SNOW_CAP_F for item in snowy)
    assert not [item for item in year(catalog.city('las-vegas')) if item['sky'] == 'snow']
    temperatures = [item['high_f'] for item in found if item['month'] == 7]
    assert max(temperatures) - min(temperatures) >= 6  # Temperatures wander around the month's typical high.


def test_stormy_has_longer_spells_and_more_storms_than_gentle():
    data = baltimore()
    gentle, stormy = year(data, skies.GENTLE), year(data, skies.STORMY)
    assert spells(stormy) > spells(gentle) + 0.5
    count = lambda found, sky: Counter(item['sky'] for item in found)[sky]  # noqa: E731
    assert count(stormy, 'storm') > 3 * count(gentle, 'storm')
    assert count(stormy, 'snow') > count(gentle, 'snow')


def test_ships_have_no_weather():
    data = {**baltimore(), 'enclosed': True}
    assert generators.conditions(data, date(2026, 7, 1)) is None


def test_weather_words_name_the_sky_and_how_long_it_has_held():
    assert agenda.weather_text({'high_f': 40, 'low_f': 31, 'rain': True, 'sky': 'snow', 'days': 3, 'note': 'x'}) == \
        'High 40°F, low 31°F, snow, the third day of it.'
    assert agenda.weather_text({'high_f': 70, 'low_f': 55, 'rain': False, 'sky': 'clear', 'days': 4,
                                'note': 'Mild and bright.'}) == 'High 70°F, low 55°F, clear skies. Mild and bright.'
    # A day planned before skies were named still reads as it did.
    assert agenda.weather_text({'high_f': 70, 'low_f': 55, 'rain': True, 'note': 'x'}) == \
        'High 70°F, low 55°F, with rain.'


def test_the_paper_names_the_wet_days_by_their_sky():
    data = baltimore()
    week = days(date(2026, 1, 5), 7)
    text = paper.weather(data, week)
    found = [generators.conditions(data, day) for day in week]
    assert text.startswith('Highs around')
    for sky, label in paper.OUTLOOK:
        assert (f' {label} ' in text) == any(item['sky'] == sky for item in found)
    assert ('Dry all week' in text) == (not any(item['rain'] for item in found))


def test_the_weather_step_is_kept_in_each_world_and_replans_the_days_ahead(client, app, companion):
    assert set_life(client)['weather_realism'] == skies.TRUE_TO_LIFE
    reconcile(client)
    with app.state.database.connect() as connection:
        before = connection.execute("SELECT COUNT(*) FROM life_agenda WHERE status='upcoming'").fetchone()[0]
    assert before
    assert set_life(client, weather_realism=skies.STORMY)['weather_realism'] == skies.STORMY
    with app.state.database.connect() as connection:
        assert skies.level_of(connection) == skies.STORMY
        assert connection.execute('SELECT weather FROM world_life').fetchone()[0] == skies.STORMY
        today = connection.execute("SELECT local_date FROM life_agenda WHERE subject='companion' AND starts_at<=? "
                                   'ORDER BY starts_at DESC LIMIT 1', (app.state.database.now(),)).fetchone()[0]
        ahead = connection.execute("SELECT COUNT(*) FROM life_agenda WHERE subject='companion' AND status='upcoming' "
                                   'AND local_date>?', (today,)).fetchone()[0]
        kept = connection.execute("SELECT COUNT(*) FROM life_agenda WHERE subject='companion' AND local_date=?",
                                  (today,)).fetchone()[0]
    assert ahead == 0 and kept  # From tomorrow, planned again under the new skies; today keeps its weather.
    reconcile(client)
    with app.state.database.connect() as connection:
        refilled = connection.execute("SELECT COUNT(*) FROM life_agenda WHERE subject='companion' AND local_date>?",
                                      (today,)).fetchone()[0]
    assert refilled
    assert client.put('/api/life/settings', json={'weather_realism': 3}).status_code == 422  # No step past Stormy.


def test_today_and_the_chat_know_tomorrow(client, app, connected, provider):
    definition = client.get('/api/companion').json()['companion']['version']['definition']
    client.post('/api/companion/versions', json={
        'definition': {**definition, 'home_city': 'baltimore', 'timezone': 'America/New_York'},
        'expected_version_id': client.get('/api/companion').json()['companion']['active_version_id']})
    reconcile(client)
    day = client.get('/api/today').json()['day']
    assert day['weather']['sky'] in skies.SKIES and day['tomorrow']['sky'] in skies.SKIES
    expected = generators.conditions(baltimore(), date.fromisoformat(day['date']) + timedelta(days=1))
    assert day['tomorrow']['sky'] == expected['sky']
    send(client, 'Any plans tomorrow?', 'skies-0001')
    assert f"Tomorrow: {agenda.weather_text(day['tomorrow'])}" in provider.requests[-1]['prompt']


def test_a_ship_has_no_weather_step_to_offer(client):
    """E2E 1.4: Settings > Realism showed "Weather in The Long Meridian" aboard the ship, which has no weather."""
    assert client.get('/api/life/settings').json()['weather'] is True  # No companion yet.
    made = client.post('/api/companion', json={'name': 'Ilyan Voss', 'timezone': 'UTC', 'home_city': 'long-meridian'})
    assert made.status_code == 200, made.text
    assert client.get('/api/life/settings').json()['weather'] is False


def test_a_city_with_a_climate_has_one(client, companion):
    assert client.get('/api/life/settings').json()['weather'] is True
