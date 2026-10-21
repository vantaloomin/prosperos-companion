"""Lore that fits the moment (companion/lore_moments.py, companion/lore.py): weather, season, time of day, holidays,
places and work switch lore on, and city files carry lore of their own."""
import json
from datetime import date, datetime, timezone

import pytest

from companion import lore_moments as moments
from companion.world import catalog
from tests.conftest import send
from tests.test_bring_characters import as_json

CITIES_WITH_LORE = ('long-meridian', 'port-vesper', 'baltimore', 'osaka', 'grandport', 'london-1895', 'camelot',
                    'new-york-1925', 'pellmouth', 'whitlock', 'calderwick', 'emerald-city', 'ellerbruck')


def day(**values):
    return {'high_f': 60, 'low_f': 45, 'rain': False, 'note': '', **values}


def test_the_days_weather_reads_as_rain_snow_heat_or_fog():
    assert moments.weather_keys(day(rain=True)) == {'weather:rain'}
    assert moments.weather_keys(day(rain=True, low_f=26)) == {'weather:snow'}
    assert moments.weather_keys(day(rain=True, note='Light snow showers')) == {'weather:snow'}
    assert moments.weather_keys(day(high_f=94)) == {'weather:heat'}
    assert moments.weather_keys(day(note='Fog season starts; gas lamps lit by mid-afternoon.')) == {'weather:fog'}
    assert moments.weather_keys(day(rain=True, note='Damp and misty')) == {'weather:rain'}
    assert moments.weather_keys(None) == set()


@pytest.mark.parametrize(('hour', 'part'), [(4, 'night'), (5, 'morning'), (11, 'morning'), (12, 'afternoon'),
                                            (17, 'evening'), (21, 'night'), (23, 'night')])
def test_parts_of_the_day(hour, part):
    assert moments.part_of_day(hour) == part


def test_a_when_needs_one_condition_of_each_kind_it_names():
    now = {'weather:rain', 'time:night', 'season:fall', 'holiday:halloween'}
    assert moments.matches(['weather:rain', 'time:night'], now)
    assert moments.matches(['weather:rain', 'weather:snow'], now)
    assert not moments.matches(['weather:rain', 'time:morning'], now)
    assert moments.matches(['holiday:Halloween'], now)
    assert not moments.matches([], now)


def test_imported_keywords_that_are_a_moment_become_a_when_of_one_kind():
    assert moments.guessed(['Winter', 'brother'], []) == ['season:winter']
    assert moments.guessed(['winter', 'rain', 'summer'], []) == ['season:winter', 'season:summer']
    assert moments.guessed(['christmas day'], ['Christmas Day']) == ['holiday:Christmas Day']
    # "Fall" is a verb too, and nothing else is guessed.
    assert moments.guessed(['fall', 'harbor', 'mike'], []) == []


def test_a_city_files_lore_is_checked_and_a_bad_entry_dropped_with_a_note():
    data = json.loads((catalog.BUILTIN_CITIES / 'baltimore.json').read_bytes())
    data['lore'] = {'credit': 'Mine', 'entries': [
        {'id': 'rainy', 'title': 'Rain', 'text': 'Rain on the harbor.', 'when': {'weather': ['rain'], 'time': 'night'}},
        {'id': 'xmas', 'text': 'Lights in Hampden.', 'when': {'holiday': ['christmas'], 'place': ['hampden', 'mars']}},
        {'id': 'Bad Id', 'text': 'x', 'keywords': ['x']},
        {'id': 'nothing', 'text': 'No way in.', 'when': {'weather': ['hail']}},
        {'id': 'work', 'text': 'At the office.', 'keywords': ['office'], 'when': {'work': True}}]}
    city = catalog.prepare(data, mend=True)
    entries = {entry['id']: entry for entry in city['lore']['entries']}
    assert entries['rainy']['when'] == ['weather:rain', 'time:night'] and entries['rainy']['title'] == 'Rain'
    assert entries['xmas']['when'] == ['holiday:Christmas Day', 'place:hampden']
    assert entries['work']['when'] == ['work:yes'] and entries['work']['keywords'] == ['office']
    assert set(entries) == {'rainy', 'xmas', 'work'}
    notes = ' '.join(city['import_notes'])
    assert '"place: mars"' in notes and 'needs a lowercase id' in notes and 'needs keywords or a when' in notes


def test_a_city_without_lore_keeps_its_data():
    assert 'lore' not in catalog.cities()['chicago']


@pytest.mark.parametrize('city_id', CITIES_WITH_LORE)
def test_every_era_has_built_in_cities_with_moment_lore(city_id):
    city = catalog.cities()[city_id]
    written = json.loads((catalog.BUILTIN_LORE / f'{city_id}.json').read_bytes())['entries']
    assert city['origin'] == 'builtin' and not city.get('import_notes')
    assert len(city['lore']['entries']) == len(written) >= 12
    kinds = {when.partition(':')[0] for entry in city['lore']['entries'] for when in entry['when']}
    assert {'time', 'place', 'work'} <= kinds
    assert ('weather' in kinds) != (city.get('enclosed') is True)


def test_the_built_in_lore_covers_every_era_and_shelf():
    built_in = [city for city in catalog.cities().values() if city['origin'] == 'builtin']
    with_lore = [city for city in built_in if city.get('lore')]
    assert {city['era'] for city in built_in} == {city['era'] for city in with_lore}
    assert {catalog.category(city) for city in built_in} == {catalog.category(city) for city in with_lore}
    assert 'Oak' in catalog.cities()['grandport']['lore']['credit']


def in_city(client, city_id, timezone_name):
    created = client.post('/api/companion', json={'name': 'Hana', 'personality': 'Warm', 'home_city': city_id,
                                                    'timezone': timezone_name})
    assert created.status_code == 200, created.text
    return created.json()


def test_lore_that_fits_the_moment_joins_the_reply_notes(client, provider):
    # 2026-10-05 12:00 UTC is a Monday morning in the fall in Baltimore.
    in_city(client, 'baltimore', 'America/New_York')
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model'})
    send(client, 'Morning!', 'moment-1')
    request = provider.requests[-1]
    assert 'Ravens Sundays and Purple Fridays' in request['prompt']
    assert 'Ravens Sundays' not in request['system']
    assert 'Lore that fits the moment or what is being talked about' in request['prompt']
    # Not a weekend, not a holiday, not winter: those stay out.
    assert 'marble front steps' not in request['prompt'] and '34th Street lights' not in request['prompt']
    # A keyword still brings an entry in whatever the moment.
    send(client, 'Did you get to see the lights on the avenue in Hampden last year?', 'moment-2')
    assert 'famous block of Christmas lights' in provider.requests[-1]['prompt']


def test_the_lore_screen_lists_the_citys_lore_with_when_and_what_fits_now(client):
    in_city(client, 'baltimore', 'America/New_York')
    listed = client.get('/api/lore').json()
    book = next(book for book in listed['books'] if book['city'])
    assert book['name'] == 'Baltimore lore' and book['source_format'] == 'Comes with the city' and book['world']
    fall = next(entry for entry in book['entries'] if entry['title'] == 'Fall in Baltimore')
    assert fall['when'] == [{'key': 'season:fall', 'label': 'Fall'}] and fall['fits_now'] is True
    assert not fall['when_guessed']
    choices = listed['choices']
    assert {'key': 'weather:fog', 'label': 'Fog'} in choices['weather']
    assert {'key': 'place:hampden', 'label': 'Hampden'} in choices['place']
    assert {'key': 'holiday:Thanksgiving', 'label': 'Thanksgiving'} in choices['holiday']
    assert choices['work'] == [{'key': 'work:yes', 'label': 'At work'}]


def test_the_citys_lore_can_be_changed_and_switched_off_but_not_removed(client, provider):
    in_city(client, 'baltimore', 'America/New_York')
    book = next(book for book in client.get('/api/lore').json()['books'] if book['city'])
    fall = next(entry for entry in book['entries'] if entry['title'] == 'Fall in Baltimore')
    changed = client.put(f"/api/lore/entries/{fall['id']}/when", json={'when': ['season:winter', 'bogus', 'time:night']})
    assert changed.status_code == 200, changed.text
    entry = next(item for item in next(b for b in changed.json()['books'] if b['city'])['entries']
                 if item['id'] == fall['id'])
    assert [item['key'] for item in entry['when']] == ['season:winter', 'time:night'] and not entry['fits_now']
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model'})
    send(client, 'Morning!', 'moment-3')
    assert 'Ravens Sundays' not in provider.requests[-1]['prompt']
    off = client.put(f"/api/lore/books/{book['id']}", json={'enabled': False}).json()
    assert next(b for b in off['books'] if b['city'])['enabled'] is False
    send(client, 'Hampden?', 'moment-4')
    assert 'Christmas lights' not in provider.requests[-1]['prompt']
    refused = client.delete(f"/api/lore/books/{book['id']}")
    assert refused.status_code == 422 and 'comes with the city' in refused.json()['detail']
    assert client.put('/api/lore/entries/city:osaka:tsuyu', json={'enabled': False}).status_code == 404


def test_an_imported_entry_keyed_by_a_season_gets_a_when_the_user_can_take_off(client):
    in_city(client, 'chicago', 'America/Chicago')
    world = {'name': 'Harbor Town', 'entries': {
        '0': {'key': ['autumn', 'harvest'], 'content': 'The harvest fair fills the square.', 'comment': 'Fair'},
        '1': {'key': ['mike'], 'content': 'Mike runs the ferry.', 'comment': 'Mike'},
        '2': {'key': ['autumn'], 'content': 'Always on.', 'constant': True, 'comment': 'Always'}}}
    made = client.post('/api/import/character', json={'filename': 'harbor.json', 'data': as_json(world)})
    assert made.status_code == 200, made.text
    book = next(book for book in client.get('/api/lore').json()['books'] if not book['city'])
    fair, mike, always = book['entries']
    assert fair['when'] == [{'key': 'season:fall', 'label': 'Fall'}] and fair['when_guessed'] and fair['fits_now']
    assert mike['when'] == [] and always['when'] == []
    cleared = client.put(f"/api/lore/entries/{fair['id']}/when", json={'when': []}).json()
    fair = next(b for b in cleared['books'] if not b['city'])['entries'][0]
    assert fair['when'] == [] and not fair['when_guessed']
    refused = client.put(f"/api/lore/entries/{always['id']}/when", json={'when': ['time:night']})
    assert refused.status_code == 422


def test_aboard_a_ship_there_is_no_weather_or_season_but_there_is_ships_night(app, client):
    in_city(client, 'long-meridian', 'Europe/London')
    with app.state.database.connect() as connection:
        from companion.characters import require_current
        companion = require_current(connection)
        keys = moments.now_keys(connection, companion, datetime(2026, 10, 5, 23, tzinfo=timezone.utc))
    assert 'time:night' in keys and not any(key.startswith(('weather:', 'season:')) for key in keys)
    assert {'day:weekday', 'time:night'} <= keys
    choices = client.get('/api/lore').json()['choices']
    assert choices['weather'] == [] and choices['season'] == [] and len(choices['time']) == 4


def test_holidays_of_the_city_are_part_of_the_moment():
    city = catalog.cities()['grandport']
    assert moments.holiday_keys(city, date(2026, 10, 9)) == {'holiday:ash day'}
    assert "Chryseon's Night" in moments.holiday_names(city)
