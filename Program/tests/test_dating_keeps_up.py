"""The dating app keeps up with the town's couples (Hit List #102): someone who started with a partner may join it a
few weeks after a split and leaves it when they meet someone new; a match the user already has stays a match
(companion/world/couples.py `looking_again`, companion/world/dating.py `status_now`)."""
from datetime import UTC, date, datetime, time, timedelta

from test_dating import PROFILE, everyone, ok

from companion import dating as app
from companion.world import couples, dating, townsfolk


def week_day(week: int) -> date:
    return townsfolk.EPOCH + timedelta(weeks=week, days=2)


def back_then_gone(data: dict, people: list[dict]) -> tuple[dict, int, int]:
    """A resident who started with a partner, split up, came back to the app and later met someone new: the person,
    the week of the split and the week they met someone."""
    for sheet in people:
        if 'desire' not in sheet or sheet.get('notable') or sheet['age'] < 25:
            continue
        found = dating.details(sheet, data)
        if found['status'] not in couples.PARTNERED or dating.details(sheet, data, matched=True)['looking'] in (
                'no', 'friends'):
            continue
        past = couples.history(townsfolk.drawn(sheet), found['status'], townsfolk.MAX_WEEKS)
        for (split, what, _), (met, then, _) in zip(past, past[1:], strict=False):
            if what == 'split' and then == 'met' and split > 45 and met - split > couples.BACK_ON_APP + 2:
                return sheet, split, met
    raise AssertionError('Nobody in town split up and met someone new.')


def test_someone_newly_single_joins_the_app_after_a_few_weeks_and_leaves_when_they_meet_someone():
    data, people = everyone('baltimore')
    sheet, split, met = back_then_gone(data, people)
    seeded = dating.details(sheet, data)['status']
    assert not dating.on_app(sheet, data) and not dating.on_app(sheet, data, week_day(split - 1))
    assert not dating.on_app(sheet, data, week_day(split + couples.BACK_ON_APP - 1))  # Getting over it.
    back = week_day(split + couples.BACK_ON_APP)
    assert dating.on_app(sheet, data, back) and dating.details(sheet, data, back)['status'] == 'single'
    assert couples.couple(sheet, data, back)['status'] == 'single'
    assert not dating.on_app(sheet, data, week_day(met))  # Seeing someone new.
    assert dating.details(sheet, data, week_day(met))['status'] == seeded
    # Someone who started single, a companion living in town and a pack's notable keep their seeded love life.
    single = next(item for item in people if 'desire' in item and dating.details(item, data)['status'] == 'single')
    assert not couples.looking_again(single, data, 'single', back)
    assert not couples.looking_again(sheet, data | {'companions': (sheet['key'],)}, seeded, back)
    assert not couples.looking_again({**sheet, 'love_life': False}, data, seeded, back)


def at(clock, day: date):
    clock.instant = datetime.combine(day, time(12), tzinfo=UTC)


def test_a_match_stays_a_match_when_they_meet_someone_new(client, clock):
    data, people = everyone('baltimore')
    sheet, split, met = back_then_gone(data, people)
    found = dating.details(sheet, data, matched=True)
    life = found['life']
    profile = PROFILE | {'gender': found['drawn_to'][0], 'interested_in': [found['gender']],
                         'looking_for': found['looking'], 'age': max(sum(found['age_range']) // 2, 18),
                         'age_min': max(18, life - 2), 'age_max': life + 2}
    ok(client.put('/api/debug-matches', json={'on': True}))
    ok(client.put('/api/dating/profile', json=profile))
    key = sheet['key']
    # Still with their partner: not on the app.
    at(clock, week_day(split - 1))
    assert client.post('/api/dating/swipes', json={'key': key, 'like': True}).status_code == 409

    at(clock, week_day(split + couples.BACK_ON_APP))
    shown = ok(client.get('/api/dating'))
    assert any(item[0]['key'] == key for item in app.pool(data))
    assert shown['remaining'] > 0
    matched = ok(client.post('/api/dating/swipes', json={'key': key, 'like': True}))['matched']
    assert matched['key'] == key and matched['looking'] == found['looking']

    # They meet someone new: gone from the app, still the user's match, as they were.
    at(clock, week_day(met + 1))
    assert not any(item[0]['key'] == key for item in app.pool(data))
    state = ok(client.get('/api/dating'))
    assert key not in [card['key'] for card in state['deck']]
    kept = next(item for item in state['matches'] if item['key'] == key)
    assert kept['looking'] == found['looking'] and kept['looking_text'] == matched['looking_text']
    draft = ok(client.get('/api/companion/cast/draft', params={'key': key}))
    assert draft['matched'] is True and draft['definition']['relationship'] == 'romance'
