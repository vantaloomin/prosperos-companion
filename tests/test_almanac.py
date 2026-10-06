"""The built-in calendar (companion/almanac/): observances, seasons, daylight and the chat context section."""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from companion.almanac import context, days, sky
from companion.world import catalog
from companion.world.source import CatalogWorld

EASTERN = ZoneInfo('America/New_York')


def local(moment):
    return moment.astimezone(EASTERN).strftime('%H:%M') if moment else None


def test_sun_times_match_published_tables_within_a_few_minutes():
    def near(moment, expected):
        hours, minutes = map(int, expected.split(':'))
        actual = moment.astimezone(EASTERN)
        return abs(actual.hour * 60 + actual.minute - hours * 60 - minutes) <= 4
    rise, set_ = sky.sun(date(2026, 6, 21), 39.29, -76.61)  # Baltimore, longest day: 5:39 and 8:37 EDT
    assert near(rise, '05:39') and near(set_, '20:37')
    rise, set_ = sky.sun(date(2026, 12, 21), 40.71, -74.0)  # New York, shortest day: 7:16 and 4:32 EST
    assert near(rise, '07:16') and near(set_, '16:32')
    assert sky.sun(date(2026, 6, 21), 70.0, 20.0) == (None, None)  # midnight sun


def test_moon_phases_on_known_dates():
    assert sky.moon(datetime(2026, 10, 26, 12, tzinfo=timezone.utc)) == 'full moon'
    assert sky.moon(datetime(2026, 11, 9, 12, tzinfo=timezone.utc)) == 'new moon'
    assert sky.moon(datetime(2026, 10, 5, 12, tzinfo=timezone.utc)) == 'waning crescent'


def test_observances_and_seasons_for_a_modern_us_city():
    baltimore = catalog.city('baltimore', {})
    assert days.applies(baltimore) and not days.applies(catalog.city('london-1895', {}))
    found = {item['id']: item['date'] for item in days.days_between(baltimore, date(2026, 10, 1), date(2027, 3, 1))}
    assert found['indigenous-peoples-day'] == date(2026, 10, 12)
    assert found['dst-ends'] == date(2026, 11, 1)
    assert found['black-friday'] == date(2026, 11, 27)  # from the world's Thanksgiving
    assert found['super-bowl-sunday'] == date(2027, 2, 14)
    assert found['lunar-new-year'] == date(2027, 2, 6)
    assert found['election-day'] == date(2026, 11, 3)
    # A season that runs past New Year counts from the autumn before it.
    january = {item['id'] for item in days.spans_on(baltimore, date(2027, 1, 5))}
    assert {'nfl-season', 'nba-season', 'nhl-season'} <= january and 'mlb-season' not in january
    assert 'pride-month' in {item['id'] for item in days.spans_on(baltimore, date(2026, 6, 10))}


def test_parties_join_the_days_happenings_in_modern_us_cities_only():
    world = CatalogWorld()
    assert [item['name'] for item in world.happenings('baltimore', date(2026, 10, 31))] == ['Halloween parties']
    assert world.happenings('baltimore', date(2026, 10, 30)) == []
    assert not any(item['id'].startswith('gathering-') for item in world.happenings('london-1895', date(1895, 12, 31)))


def test_chat_context_section(app):
    with app.state.database.connect() as connection:
        check_context(connection)


def check_context(connection):
    now = datetime(2026, 10, 5, 16, tzinfo=timezone.utc)
    lines = dict(context.context_lines(connection, {'home_city': 'baltimore'}, 'America/New_York', now))
    assert lines['2026-10-05:coming'] == "- Coming up: Indigenous Peoples' Day / Columbus Day, Monday, October 12 " \
                                         "(in 7 days)."
    assert 'Hispanic Heritage Month (until October 15)' in lines['2026-10-05:seasons']
    assert 'Ravens football season' in lines['2026-10-05:seasons']
    assert lines['2026-10-05:daylight'].startswith('- Daylight: sunrise 7:0')
    assert 'never make them up' in lines['2026-10-05:no_news']
    christmas = dict(context.context_lines(connection, {'home_city': 'baltimore'}, 'America/New_York',
                                           datetime(2026, 12, 25, 16, tzinfo=timezone.utc)))
    assert christmas['2026-12-25:today'] == '- Today: Christmas Day (a public holiday).'
    assert context.context_lines(connection, {'home_city': ''}, 'America/New_York', now) == []
    camelot = dict(context.context_lines(connection, {'home_city': 'camelot'}, 'Europe/London', now))
    assert not any(key.endswith(':no_news') for key in camelot)


def test_the_reply_prompt_carries_the_calendar(client, provider):
    created = client.post('/api/companion', json={'name': 'Hana', 'personality': 'Warm', 'home_city': 'baltimore',
                                                    'timezone': 'America/New_York'})
    assert created.status_code == 200, created.text
    client.put('/api/connection', json={'base_url': 'http://127.0.0.1:1234/v1', 'model': 'local-model'})
    client.post('/api/conversation/messages', json={'text': 'Any plans this weekend?', 'client_id': 'almanac-1'})
    system = provider.requests[-1]['system']
    assert "## The calendar where you live (real dates and seasons from the app's built-in calendar)" in system
    assert '- Daylight: sunrise ' in system
