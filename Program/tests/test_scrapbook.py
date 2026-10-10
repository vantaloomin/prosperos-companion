"""Our year so far (companion/life/scrapbook.py)."""
from datetime import date, timedelta

from conftest import send

from companion.life import scrapbook


def test_periods_cover_the_year_so_far_full_years_and_calendar_years():
    first = date(2025, 3, 10)
    found = scrapbook.periods(first, date(2026, 10, 5))
    assert [item['key'] for item in found] == ['so-far', 'year-1', 'cal-2025']
    assert found[0]['start'] == date(2026, 3, 10) and found[1]['end'] == date(2026, 3, 9)
    assert found[2]['start'] == first and found[2]['end'] == date(2025, 12, 31)
    leap = scrapbook.periods(date(2024, 2, 29), date(2025, 3, 1))
    assert leap[0]['start'] == date(2025, 2, 28)


def test_today_points_to_it_on_the_anniversary_and_at_new_year():
    first = date(2025, 3, 10)
    on_the_day = date(2026, 3, 10)
    assert scrapbook.featured(scrapbook.periods(first, on_the_day), first, on_the_day) == 'year-1'
    assert scrapbook.featured(scrapbook.periods(first, date(2026, 1, 3)), first, date(2026, 1, 3)) == 'cal-2025'
    assert scrapbook.featured(scrapbook.periods(first, date(2026, 3, 16)), first, date(2026, 3, 16)) == 'year-1'
    assert scrapbook.featured(scrapbook.periods(first, date(2026, 3, 17)), first, date(2026, 3, 17)) is None
    assert scrapbook.featured(scrapbook.periods(first, date(2026, 6, 1)), first, date(2026, 6, 1)) is None


def test_nothing_before_the_first_talk(client, companion):
    assert client.get('/api/life/year').json() == {'periods': [], 'featured': None, 'featured_days': 0}
    assert client.get('/api/life/year/so-far').status_code == 404


def test_the_pages_come_from_what_happened(client, connected, clock):
    send(client, 'Hi! I just moved here and I know nobody.', 'client-01')
    clock.advance(timedelta(days=2))
    send(client, 'Back again.', 'client-02')
    listing = client.get('/api/life/year').json()
    assert [item['key'] for item in listing['periods']] == ['so-far']
    book = client.get('/api/life/year/so-far').json()
    kinds = [page['kind'] for page in book['pages']]
    assert kinds[0] == 'cover' and kinds[1] == 'first' and kinds[-1] == 'closing'
    cover = book['pages'][0]
    assert {'value': '2', 'label': 'Days talked'} in cover['stats']
    first = book['pages'][1]
    assert first['title'] == 'The first thing you said' and first['said'].startswith('Hi! I just moved here')
    assert first['reply']
    assert '2 days talked so far' in book['pages'][-1]['text']
    clock.advance(timedelta(days=365))
    send(client, 'A year!', 'client-03')
    listing = client.get('/api/life/year').json()
    assert [item['key'] for item in listing['periods']] == ['so-far', 'year-1', 'cal-2026']
    # Two days after the anniversary, Today points to the first year until it is opened or put away.
    assert listing['featured'] == 'year-1' and listing['featured_days'] == 2
    assert client.post('/api/life/year/year-1/seen').json()['featured'] is None
    assert client.get('/api/life/year').json()['featured'] is None
    year = client.get('/api/life/year/year-1').json()
    assert year['title'] == 'Our first year' and year['pages'][1]['said'].startswith('Hi!')
    later = client.get('/api/life/year/so-far').json()
    assert later['pages'][1]['title'] == 'How the year started' and later['pages'][1]['said'] == 'A year!'
