"""Family traditions and a seasonal home (companion/life/traditions.py)."""
import json
from datetime import date, datetime, timedelta, timezone

import pytest
from conftest import reconcile

from companion.database import decode
from companion.life import body, composer, traditions
from companion.world import catalog
from companion.world.source import CatalogWorld

DAYS = [{'key': 'day', 'label': 'Day', 'kind': 'leisure', 'start': '09:00', 'end': '17:00'},
        {'key': 'evening', 'label': 'Evening', 'kind': 'social', 'start': '18:00', 'end': '22:00'},
        {'key': 'night', 'label': 'Asleep', 'kind': 'sleep', 'start': '23:00', 'end': '07:00'}]
MIRA = {'name': 'Mira', 'interests': ['cooking'], 'location': 'Fells Point, Baltimore'}


@pytest.fixture
def baltimore(client, monkeypatch):
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(composer, 'PLAN_SHARE', 0)
    monkeypatch.setattr(composer, 'THREAD_SHARE', 0)
    # A cold on the holiday (about 1 run in 100) keeps them home in bed instead of at the tradition.
    monkeypatch.setattr(body, 'sick', lambda *_args: False)
    response = client.post('/api/companion', json={**MIRA, 'timezone': 'America/New_York', 'schedule': DAYS})
    assert response.status_code == 200, response.text
    return response.json()


def connect(client, write=True):
    return client.app.state.database.connect(write=write)


def test_the_bank_is_big_specific_and_names_real_holidays():
    bank = traditions.data()
    calendars = catalog.holiday_calendars()
    assert sum(len(item['dishes']) for item in bank['traditions']) >= 100
    assert sum(len(item['rituals']) for item in bank['traditions']) >= 100
    assert len(bank['decorations']) >= 100
    for item in bank['traditions']:
        for calendar in item['calendars']:
            assert item['holiday'] in {holiday['id'] for holiday in calendars[calendar]['holidays']}, item
    # Product copy stays gender-neutral.
    words = json.dumps(bank).lower()
    assert not any(f' {word} ' in words for word in ('she', 'he', 'her', 'his', 'him'))


def test_seeding_keeps_the_big_holidays_and_names_a_host():
    city = CatalogWorld().find('baltimore')
    people = [{'id': 'p1', 'name': 'Ruth', 'role': 'mom', 'details': json.dumps({'neighborhood': 'Towson'}),
               'schedule': json.dumps([{'kind': 'work'}])},
              {'id': 'p2', 'name': 'Dev', 'role': 'close friend', 'details': '{}', 'schedule': '[]'}]
    first = traditions.seeded('t1', city, people)
    assert traditions.seeded('t1', city, people) == first
    holidays = [row['holiday'] for row in first]
    assert {'thanksgiving', 'christmas'} <= set(holidays) and len(holidays) <= traditions.MOST
    thanksgiving = next(row for row in first if row['holiday'] == 'thanksgiving')
    assert thanksgiving['host_id'] == 'p1'
    assert '{their} mom Ruth' in thanksgiving['text'] and 'Towson' in thanksgiving['text']
    assert 'Thanksgiving' not in thanksgiving['text'].split('.')[0]  # The card's heading names the holiday.
    # Without family, the holiday is kept at their own place.
    alone = traditions.seeded('t1', city, [])
    assert all('{their} own place' in row['text'] or 'friends' in row['text'] for row in alone)


def test_other_calendars_keep_their_own_holidays():
    seoul_like = {'name': 'Somewhere', 'country': 'South Korea', 'era': 'modern', 'holidays': []}
    kept = {row['holiday'] for row in traditions.seeded('t2', seoul_like, [])}
    assert {'seollal', 'chuseok'} <= kept and 'thanksgiving' not in kept


def test_decorations_follow_the_season_and_stay_the_same_all_season():
    city = CatalogWorld().find('baltimore')
    keen = next(seed for seed in (f's{n}' for n in range(200))
                if traditions.generators.unit(seed, 'decorations', 'keen') > traditions.HALLOWEEN_TOO)
    never = next(seed for seed in (f's{n}' for n in range(200))
                 if traditions.generators.unit(seed, 'decorations', 'keen') < traditions.NEVER)
    assert traditions.seasons_up(keen, city, date(2026, 12, 20)) == ['winter']
    assert traditions.decorations(keen, city, date(2026, 12, 20)) == traditions.decorations(keen, city, date(2026, 12, 30))
    assert traditions.seasons_up(keen, city, date(2026, 10, 31)) == ['halloween', 'autumn']
    assert traditions.seasons_up(keen, city, date(2026, 8, 10)) == []
    assert traditions.seasons_up(never, city, date(2026, 12, 20)) == []
    # Winter's go up after Thanksgiving and come down early in January.
    assert 'winter' not in traditions.seasons_up(keen, city, date(2026, 11, 25))
    assert 'winter' not in traditions.seasons_up(keen, city, date(2027, 1, 12))


def test_a_coming_holiday_shows_its_tradition_and_the_day_goes_to_it(client, baltimore, clock):
    first = client.get('/api/life/traditions')
    assert first.status_code == 200, first.text
    panel = first.json()
    thanksgiving = next(item for item in panel['traditions'] if item['holiday'] == 'thanksgiving')
    assert thanksgiving['next'] == '2026-11-26' and '{their}' not in thanksgiving['text']
    assert all(item['id'] != 'thanksgiving' for item in panel['holidays'])

    clock.advance(datetime(2026, 11, 22, 15, tzinfo=timezone.utc) - clock.now())
    reconcile(client)
    today = client.get('/api/today').json()
    found = [item for item in today['occasions'] if item['kind'] == 'tradition' and item['holiday'] == 'Thanksgiving']
    assert found and found[0]['days'] == 4 and "Your family's tradition:" in found[0]['text']
    assert '{their}' not in found[0]['text'] and 'your' in found[0]['text'].split("tradition:")[1]
    assert found[0]['teaser'].startswith('Thanksgiving ') and len(found[0]['teaser']) < 80

    clock.advance(timedelta(days=5))
    reconcile(client)
    with connect(client, False) as connection:
        entries = [decode(row[0]) for row in connection.execute(
            "SELECT entry FROM life_agenda WHERE subject='companion' AND local_date='2026-11-26' AND entry IS NOT NULL")]
    kept = [entry for entry in entries if entry['activity'] == 'tradition']
    assert len(kept) == 1 and 'Thanksgiving' in kept[0]['summary']


def test_the_user_can_reword_drop_restore_and_add(client, baltimore, clock):
    panel = client.get('/api/life/traditions').json()
    first = panel['traditions'][0]
    edited = client.patch(f"/api/life/traditions/{first['id']}", json={'text': 'Pancakes at midnight.'})
    assert edited.status_code == 200, edited.text
    assert next(item for item in edited.json()['traditions'] if item['id'] == first['id'])['text'] == \
        'Pancakes at midnight.'
    gone = client.post(f"/api/life/traditions/{first['id']}/remove").json()
    assert first['id'] in {item['id'] for item in gone['removed']}
    assert first['id'] not in {item['id'] for item in gone['traditions']}
    back = client.post(f"/api/life/traditions/{first['id']}/restore").json()
    assert first['id'] in {item['id'] for item in back['traditions']}
    free = back['holidays'][0]
    added = client.post('/api/life/traditions', json={'holiday': free['id'], 'text': 'A long walk, every year.'})
    assert added.status_code == 200, added.text
    mine = next(item for item in added.json()['traditions'] if item['holiday'] == free['id'])
    assert mine['origin'] == 'user'
    again = client.post('/api/life/traditions', json={'holiday': free['id'], 'text': 'Twice?'})
    assert again.status_code == 409
    assert client.post('/api/life/traditions', json={'holiday': 'not-a-holiday', 'text': 'x'}).status_code == 422


def test_a_tradition_the_user_rewords_still_reads_in_the_companions_own_voice():
    text = traditions.stored("Thanksgiving is at their dad Richard's.  ")
    assert text == "Thanksgiving is at {their} dad Richard's."
    assert traditions.voiced(text, 'your') == "Thanksgiving is at your dad Richard's."


def test_adding_a_tradition_starts_from_the_next_holiday(client, baltimore, clock):
    panel = client.get('/api/life/traditions').json()
    city = catalog.city('baltimore')
    today = clock.now().astimezone(timezone(timedelta(hours=-4))).date()
    free = {item['id'] for item in panel['holidays']}
    coming = [item['id'] for item in traditions.dated(city, today, today + timedelta(days=366)) if item['id'] in free]
    assert panel['holidays'][0]['id'] == coming[0]
    assert [item['id'] for item in panel['holidays']][:3] == list(dict.fromkeys(coming))[:3]


def test_tradition_lines_use_the_companions_own_pronouns_when_known():
    she, unknown = {'name': 'Mira', 'identity': 'She is a line cook.'}, {'name': 'Sam', 'identity': 'A line cook.'}
    host = "Mira spent Thanksgiving at their mom Valerie's, the way they always do."
    assert composer.said(host, she) == "Mira spent Thanksgiving at her mom Valerie's, the way she always does."
    assert composer.said(host, unknown) == host
    assert composer.said("Mira went home to their dad Rui's for Thanksgiving.", {'identity': 'He is a cook.'}) == \
        "Mira went home to his dad Rui's for Thanksgiving."
    assert composer.said('Mira hosted Diwali at their place, the way they always do.', she) == \
        'Mira hosted Diwali at her place, the way she always does.'
    # "at their" outside a tradition line may be someone else's.
    assert composer.said('Mira met Jo at their office.', she) == 'Mira met Jo at their office.'
    # Her own birthday is hers; a friend's stays theirs.
    assert composer.said('Mira treated themselves at Bar Vasco for their birthday.', she) == \
        'Mira treated herself at Bar Vasco for her birthday.'
    assert composer.said('Mira went out at Bar Vasco with Jo for their birthday.', she) == \
        'Mira went out at Bar Vasco with Jo for her birthday.'
    assert composer.said('Mira celebrated their birthday with Jo.', she) == 'Mira celebrated her birthday with Jo.'
    assert composer.said('Mira took Jo out at Bar Vasco for their birthday.', she) == \
        'Mira took Jo out at Bar Vasco for their birthday.'
    assert composer.said('Mira lost a favorite scarf somewhere around town and is retracing their steps.', she) == \
        'Mira lost a favorite scarf somewhere around town and is retracing her steps.'


def test_a_she_companions_tradition_reads_her_on_today_and_in_the_feed(client, monkeypatch, clock):
    monkeypatch.setattr(composer, 'QUIET_SHARE', 0)
    monkeypatch.setattr(composer, 'PLAN_SHARE', 0)
    monkeypatch.setattr(composer, 'THREAD_SHARE', 0)
    monkeypatch.setattr(body, 'sick', lambda *_args: False)
    response = client.post('/api/companion', json={**MIRA, 'identity': 'She is a line cook; her friends call her Mir.',
                                                     'timezone': 'America/New_York', 'schedule': DAYS})
    assert response.status_code == 200, response.text
    clock.advance(datetime(2026, 11, 22, 15, tzinfo=timezone.utc) - clock.now())
    reconcile(client)
    found = [item for item in client.get('/api/today').json()['occasions'] if item['kind'] == 'tradition']
    assert found and all(' their ' not in f" {item['teaser']} {item['tradition']} " for item in found)
    clock.advance(timedelta(days=5))
    reconcile(client)
    with connect(client, False) as connection:
        stored = [row[0] for row in connection.execute(
            "SELECT summary FROM life_events WHERE status='committed' AND summary LIKE '%Thanksgiving%'")]
    assert stored and all('their' in text or 'they' in text for text in stored)  # Stored as written.
    shown = [event['summary'] for post in client.get('/api/feed').json()['posts'] for event in post['events']
             if 'Thanksgiving' in event['summary']]
    today = [event['summary'] for event in client.get('/api/today').json()['changes']
             if 'Thanksgiving' in event['summary']]
    assert shown and today
    for text in shown + today:
        assert 'their' not in text and 'they' not in text and ('her ' in text or 'she always does' in text), text
