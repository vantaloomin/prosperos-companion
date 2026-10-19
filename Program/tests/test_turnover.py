"""The town changes hands (companion/world/turnover.py): townsfolk move away, change jobs and retire, and newcomers
take their place, all seeded from the day with nothing stored."""
import copy
from datetime import UTC, date, datetime, timedelta

import pytest

from companion.clock import FixedClock
from companion.life import encounters
from companion.world import catalog, couples, paper, townsfolk, turnover

START = turnover.START


@pytest.fixture(autouse=True)
def active(monkeypatch):
    monkeypatch.setattr(turnover, 'ACTIVE', True)
    monkeypatch.setattr(turnover, 'STATE', turnover.Levels(FixedClock(datetime(2026, 10, 5, 12, tzinfo=UTC))))


def city(city_id='baltimore'):
    return catalog.cities()[city_id]


def everyone_at_places(data, day):
    return {place['id']: townsfolk.at_place(data, place['id'], day) for place in data['places']}


def later(years):
    return START + timedelta(days=round(365.25 * years))


def generation(sheet):
    return townsfolk.slot_of(int(sheet['key'].rsplit(':', 1)[1]))[1]


def test_nobody_has_left_before_the_town_started_changing_hands():
    data = city()
    before = everyone_at_places(data, START - timedelta(days=30))
    assert all(generation(sheet) == 0 for people in before.values() for sheet in people)


def test_years_on_newcomers_hold_some_spots_the_same_way_every_time():
    data = city()
    ten = everyone_at_places(data, later(10))
    assert ten == everyone_at_places(data, later(10))
    newcomers = [sheet for people in ten.values() for sheet in people if generation(sheet)]
    first = everyone_at_places(data, START)
    total = sum(len(people) for people in ten.values())
    # Most of a town has turned over in ten years, but not everyone, and no place is short of people.
    assert total // 4 < len(newcomers) < total
    assert all(len(ten[place]) == len(first[place]) for place in ten)
    for sheet in newcomers[:20]:
        assert townsfolk.find(data, sheet['key']) == sheet
        assert START.isoformat() <= sheet['arrived'] <= later(10).isoformat()


def test_a_newcomer_takes_over_the_same_work_at_the_place():
    data = city()
    for place in data['places']:
        old, new = townsfolk.at_place(data, place['id'], START), townsfolk.at_place(data, place['id'], later(20))
        for before, after in zip(old, new, strict=True):
            if before['staff']:
                assert (after['role'], after['staff']) == (before['role'], before['staff'])


def test_someone_who_left_is_still_found_and_their_leaving_is_known():
    data = city()
    sheet = next(sheet for sheet in townsfolk.at_place(data, data['places'][0]['id'], START)
                 if townsfolk.gone(sheet, data, later(30)))
    assert townsfolk.find(data, sheet['key']) == sheet
    found = townsfolk.gone(sheet, data, later(30))
    assert found['why'] in ('moved', 'new job', 'retired')
    assert townsfolk.gone(sheet, data, START - timedelta(days=1)) is None
    left = date.fromisoformat(found['day'])
    assert townsfolk.gone(sheet, data, left - timedelta(days=1)) is None
    assert sheet['key'] not in {other['key'] for other in townsfolk.at_place(data, sheet['place']['id'], left)}


def test_a_newcomers_goals_start_when_they_arrive():
    data = city()
    sheet = next(sheet for people in everyone_at_places(data, later(12)).values() for sheet in people
                 if generation(sheet) and sheet['arrived'] > later(11).isoformat())
    state = townsfolk.story(sheet, data, date.fromisoformat(sheet['arrived']))
    assert state['reached'] == [] and state['progress'] <= 1


def test_residents_move_away_and_new_neighbors_move_in():
    data = city()
    hood = data['neighborhoods'][0]['id']
    now, years_on = townsfolk.residents(data, hood, day=START), townsfolk.residents(data, hood, day=later(5))
    assert len(now) == len(years_on)
    moved_in = [sheet for sheet in years_on if sheet.get('arrived')]
    assert moved_in and all(townsfolk.find(data, sheet['key']) == sheet for sheet in moved_in)


def test_the_user_and_companions_made_from_townsfolk_keep_their_spot():
    data = city()
    leaving = [sheet for people in everyone_at_places(data, START).values() for sheet in people
               if townsfolk.gone(sheet, data, later(15))][:2]
    kept = data | {'you': leaving[0]['key'], 'kept': (leaving[1]['key'],)}
    for sheet in leaving:
        assert townsfolk.gone(sheet, kept, later(15)) is None
    keys = {sheet['key'] for people in everyone_at_places(kept, later(15)).values() for sheet in people}
    assert leaving[1]['key'] in keys and leaving[0]['key'] not in keys  # The user is never one of the town's people.


def test_a_packs_named_people_stay_unless_the_pack_lets_them_go():
    data = city('grandport')
    named = [item['id'] for item in data['notables']]
    found = {sheet['notable'] for people in everyone_at_places(data, later(60)).values() for sheet in people
             if sheet.get('notable')}
    assert set(named) <= found
    loose = copy.deepcopy(data)
    for item in loose['notables']:
        item['can_leave'] = True
    gone = {sheet['notable'] for people in everyone_at_places(loose, later(60)).values() for sheet in people
            if sheet.get('notable')}
    assert len(gone) < len(named)


def test_life_s_big_turns_at_zero_keeps_everyone():
    turnover.STATE.pace = 0
    data = city()
    assert all(generation(sheet) == 0 for people in everyone_at_places(data, later(20)).values() for sheet in people)


def test_nobody_passes_away_unless_people_can_pass_away_is_on():
    data = city()
    reasons = set()
    for place in data['places']:
        for slot in range(townsfolk.everyone(data, place)):
            reasons |= {term.why for term in townsfolk.place_terms(data, place, slot, turnover.week_of(later(40)))}
    assert 'passed' not in reasons and {'moved', 'new job', 'retired'} <= reasons
    turnover.STATE.loss = 3
    reasons = set()
    for place in data['places']:
        for slot in range(townsfolk.everyone(data, place)):
            reasons |= {term.why for term in townsfolk.place_terms(data, place, slot, turnover.week_of(later(40)))}
    assert 'passed' in reasons


def test_the_paper_reports_comings_and_goings():
    data = city()
    items = []
    for week in range(30):
        sunday = paper.issue_date(later(1)) + timedelta(weeks=week)
        items += paper.comings_and_goings(data, (sunday - timedelta(days=6), sunday))
    headlines = ' '.join(item['headline'] for item in items)
    assert 'New ' in headlines and ('Farewell to' in headlines or 'moves on' in headlines or 'retires' in headlines)
    assert all(item['text'].endswith('.') for item in items)
    assert len({item['key'] for item in items}) == len(items)


def test_town_couples_have_babies_in_words_only_and_follow_growing_families():
    data = city()
    people = paper.sample(data, later(1))
    found = [item for sheet in people
             for item in couples.babies(sheet, data, (START, later(3)))]
    assert found and all(item['partner']['full'] for item in found)
    turnover.STATE.families = 0
    assert not [item for sheet in people for item in couples.babies(sheet, data, (START, later(3)))]


def test_a_companion_who_knew_someone_hears_they_left():
    data = city()
    sheet = next(sheet for people in everyone_at_places(data, START).values() for sheet in people
                 if sheet['staff'] and townsfolk.gone(sheet, data, later(5)))
    companion = {'version': {'timezone': 'UTC'}}
    assert encounters.left(sheet, data, 1, None, companion) is None  # Nobody has left yet today.
    found = encounters.left(sheet, data, 1, datetime.combine(later(5), datetime.min.time(), UTC), companion)
    assert found and found['text']
    line = ' '.join(encounters.news_of({'left': found}))
    assert line.startswith('They have since ') and date.fromisoformat(found['day']).strftime('%B %Y') in line


def test_before_1925_staff_retire_rarely_and_passing_away_is_likelier():
    modern = turnover.chances('staff', 68, 2, 3, 'modern')
    victorian = turnover.chances('staff', 68, 2, 3, 'victorian')
    assert victorian['retired'] < modern['retired'] / 4
    assert turnover.chances('staff', 80, 2, 3, 'medieval')['retired'] < 0.5 < turnover.chances('staff', 80, 2, 3)['retired']
    assert victorian['passed'] == pytest.approx(modern['passed'] * 2)
    # 1925 keeps today's ages and rates.
    assert turnover.chances('staff', 68, 2, 3, 'jazz-age') == modern
    assert victorian['moved'] == modern['moved']


def test_london_1895_staff_mostly_work_on_where_baltimore_staff_retire():
    def retired(city_id):
        data = city(city_id)
        found = 0
        for place in data['places'][:60]:
            for slot in range(3):
                found += sum(term.why == 'retired' for term in townsfolk.place_terms(data, place, slot,
                                                                                      turnover.week_of(later(20))))
        return found
    assert retired('london-1895') * 2 < retired('baltimore')


def test_the_paper_gives_the_age_around_town_does(monkeypatch):
    from companion.life import ages
    monkeypatch.setattr(turnover, 'STATE', turnover.Levels(turnover.STATE.clock, loss=4))
    data = city() | {'began': date(2027, 2, 14)}
    for place in data['places']:
        found = [term for term in townsfolk.place_terms(data, place, 0, turnover.week_of(later(30)))
                 if term.why == 'passed']
        if found:
            break
    term = found[0]

    def sheet_of(generation):
        return townsfolk.person(data, place, turnover.STRIDE * generation)
    [item] = [item for item in paper.moves(data, [term], range(term.left, term.left + 1), sheet_of)
              if item.get('obituary')]
    sheet, day = sheet_of(term.generation), turnover.week_day(term.left)
    assert f" at {ages.aged(sheet, day, data['began'])}" in item['text']
    assert couples.age_on(sheet, data, day) == ages.aged(sheet, day, data['began'])
    # Without the town's own day, the paper counts from when the town started changing hands.
    assert couples.age_on(sheet, city(), day) == ages.aged(sheet, day, turnover.START)
