"""Goals that fit their life (Hit List #101): a townsperson draws only goals they qualify for, and a goal that stops
fitting their love life gives way to another from the next week."""
from datetime import date, timedelta

from companion.life import casting
from companion.world import catalog, couples, townsfolk


def people(limit=6):
    for data in list(catalog.cities().values())[:limit]:
        for hood in data['neighborhoods'][:6]:
            for sheet in townsfolk.residents(data, hood['id']):
                yield data, sheet
        for place in data['places'][:15]:
            for sheet in townsfolk.at_place(data, place['id']):
                yield data, sheet


def test_every_need_in_the_bank_is_one_the_rules_read():
    for goal_id, needs in townsfolk.GOAL_NEEDS.items():
        assert goal_id in townsfolk.SHARED_GOALS
        assert set(needs) <= set(casting.GOAL_NEEDS), goal_id
        if 'ages' in needs:
            assert needs['ages'][0] <= needs['ages'][1]


def test_no_goal_drawn_that_their_life_rules_out():
    checked = 0
    for data, sheet in people(3):
        order = set(sheet['goals'])
        works = sheet['occupation'] not in ('', 'retired')
        if not works:
            assert not order & {'promotion', 'raise', 'mentor'}, sheet['key']
        if sheet['occupation'] == 'retired':
            assert not order & {'exam', 'restaurant-job', 'night-class'}, sheet['key']
        if 'owner' in f"{sheet['role']} {sheet['occupation']}":
            assert not order & {'promotion', 'raise'}, sheet['key']
        assert ('reconcile' in order) == casting.townsperson_sibling(sheet)
        life = casting.townsperson_life(sheet, data)
        if life > 62:
            assert 'anniversary' not in order
        checked += 1
    assert checked > 500


def test_goals_that_ask_nothing_stay_for_everyone():
    for data, sheet in people(2):
        for goal_id in ('novel', 'garden', 'chess'):
            assert goal_id in sheet['goals']


def taken(sheet, data, day):
    found = couples.couple(sheet, data, day)
    details = couples.details_of(sheet, data)
    return found['status'] != 'single' if found else not details or details['status'] in couples.PARTNERED


def test_asking_someone_out_gives_way_while_they_are_with_someone():
    shown = swapped = 0
    for data, sheet in people(2):
        if 'first-date' not in sheet['goals']:
            continue
        for weeks in range(0, 520, 26):
            day = townsfolk.EPOCH + timedelta(weeks=weeks, days=3)
            state = townsfolk.story(sheet, data, day)
            if state['goal']['id'] == 'first-date':
                shown += 1
                assert not taken(sheet, data, day), sheet['key']
            elif taken(sheet, data, day) and townsfolk.goal(sheet, data, 0)['id'] == 'first-date':
                swapped += 1
            assert state['progress'] < state['goal']['steps']
    assert shown and swapped


def test_a_stand_in_comes_from_the_far_end_so_it_never_comes_up_twice():
    for data, sheet in people(1):
        number = townsfolk.stand_in(sheet, data, date(2026, 11, 9))
        assert number is not None and number >= len(sheet['goals']) - 3
