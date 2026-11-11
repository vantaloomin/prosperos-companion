"""A storyline only goes to people it can be true for (companion/life/casting.py, tester 2026-11-10: a promotion for a
seamstress who works from home, a breakup for the companion's rival who kept his girlfriend)."""
import json
from datetime import date, timedelta

from companion.life import casting, circle, circle_love, storylines

WORKDAY = [{'key': 'work', 'label': 'Work', 'kind': 'work', 'start': '09:00', 'end': '17:00', 'days': [0, 1, 2, 3, 4]}]


def person(person_id, role, seed=None, **details):
    return {'id': person_id, 'seed': seed or f'circle:t:{person_id}', 'name': person_id.title(), 'role': role,
            'career': '', 'status': 'active', 'details': json.dumps({'age': 50, **details})}


def seed_with_partner(want: bool) -> str:
    return next(f'circle:t:{index}' for index in range(200)
                if (circle_love.seeded_partner({'id': 'x', 'seed': f'circle:t:{index}'}) is not None) == want)


def cast(key, people, definition=None, **facts):
    story = storylines.find_story(key)
    return storylines.casts(story, people, definition or {'schedule': WORKDAY},
                            casting.Facts(people=people, **facts))


def test_a_parent_who_works_from_home_gets_a_big_order_never_a_promotion():
    mom = person('mom', 'mom', career='Seamstress', employer='from home')
    dad = person('dad', 'dad', career='Accountant', employer='Harbor Bank')
    assert cast('parent_promotion', [mom, dad]) == [('dad',)]
    assert cast('parent_big_order', [mom, dad]) == [('mom',)]
    freelance = person('mom', 'mom', career='Freelance photographer')
    assert cast('parent_promotion', [freelance]) == [] and cast('parent_big_order', [freelance]) == [('mom',)]
    retired = person('dad', 'dad', career='Retired')
    assert cast('parent_promotion', [retired]) == cast('parent_big_order', [retired]) == []
    # A job the user wrote is theirs: no story changes it.
    written = person('dad', 'dad', career='Accountant', employer='Harbor Bank', edited=['job'])
    assert cast('parent_promotion', [written]) == []


def test_the_seamstress_from_home_is_never_promoted_over_two_thousand_days(client, monkeypatch):
    response = client.post('/api/companion', json={'name': 'Sett', 'timezone': 'UTC', 'schedule': WORKDAY})
    assert response.status_code == 200, response.text
    monkeypatch.setattr(storylines, 'START', (1, 1, 1, 1))
    monkeypatch.setattr(storylines, 'RUNNING', (99, 99, 99, 99))
    with client.app.state.database.connect() as connection:
        from companion.characters import require_current
        companion = require_current(connection)
        people = [person('mom', 'mom', career='Seamstress', employer='from home'),
                  person('pal', 'close friend', career='Barista')]
        drawn = {storylines.start(connection, companion, people, date(2026, 1, 1) + timedelta(days=offset), 0)['story']
                 for offset in range(2000)}
    assert 'parent_promotion' not in drawn and 'parent_big_order' in drawn


def test_a_rival_never_confides_in_the_companion():
    rival = person('kaito', 'rival (regular)', seed=seed_with_partner(True), career='Accountant', employer='Bank')
    friend = person('ana', 'close friend', seed=seed_with_partner(True), career='Accountant', employer='Bank')
    for key in ('friend_breakup', 'friend_new_job'):
        assert cast(key, [rival, friend]) == [('ana',)]
    assert not casting.confidant(rival, casting.Facts(close=lambda _row: 5))
    noted = person('jo', 'gym buddy', note='My ex from college.')
    assert not casting.confidant(noted, casting.Facts(close=lambda _row: 5))
    stranger = person('lee', 'barista')
    assert not casting.confidant(stranger, casting.Facts(close=lambda _row: 2))
    assert casting.confidant(stranger, casting.Facts(close=lambda _row: 3))


def test_two_friends_feud_only_when_both_confide():
    rival = person('kaito', 'rival')
    pals = [person(name, 'close friend') for name in ('ana', 'bo')]
    rows = [*pals, rival]
    assert cast('friends_feud', rows, close=lambda _row: 5) == [('ana', 'bo')]


def test_a_breakup_needs_someone_to_break_up_with():
    seeing = person('ana', 'close friend', seed=seed_with_partner(True))
    alone = person('bo', 'close friend', seed=seed_with_partner(False))
    assert cast('friend_breakup', [seeing, alone]) == [('ana',)]
    assert circle_love.state(None, seeing)['state'] == 'seeing'
    assert circle_love.state(None, alone)['state'] == 'single'
    # Not someone whose wedding is planned, and not someone out of town in an era with no phones.
    assert cast('friend_breakup', [seeing], weddings=frozenset({'ana'})) == []
    away = person('ana', 'close friend', seed=seed_with_partner(True), local=False)
    assert cast('friend_breakup', [away], modern=False) == [] and cast('friend_breakup', [away]) == [('ana',)]


def test_the_love_life_of_record():
    girlfriend = person('gf', 'girlfriend', seed=seed_with_partner(True))
    assert circle_love.state(None, girlfriend) == {'state': 'seeing', 'partner': {'key': 'companion'}, 'exes': [],
                                                   'since': None, 'decided': 'circle'}
    assert circle_love.state(None, person('w', 'wife'))['state'] == 'married'
    married = person('sis', 'sister', seed=seed_with_partner(False), married=True)
    assert circle_love.state(None, married)['state'] == 'married'
    mom, dad = person('mom', 'mom'), person('dad', 'dad')
    how = circle.tie(mom, dad)
    found = circle_love.state(None, mom, [mom, dad])
    assert found['state'] == {'married': 'married', 'divorced': 'divorced'}[how]
    assert found['decided'] == 'circle'


def test_work_stories_need_a_companion_with_an_employer():
    assert cast('credit_taker', []) == [()]
    assert cast('credit_taker', [], companion_employed=False) == []
    assert cast('credit_taker', [], {'schedule': []}) == []


def test_only_a_coworker_at_the_companions_work_leaves_it():
    with_them = person('co', 'coworker', career='Works with Mira', works_with_companion=True)
    elsewhere = person('ex', 'coworker', career='Clerk')
    assert cast('coworker_leaving', [with_them, elsewhere]) == [('co',)]
    assert cast('coworker_leaving', [with_them], companion_employed=False) == []


def test_parents_the_user_married_are_not_separated_by_a_story():
    mom, dad = person('mom', 'mom'), person('dad', 'dad')
    if circle.tie(mom, dad) != 'married':
        mom = person('mom', 'mom', own_ties={dad['seed']: 'married'})
        assert cast('parents_separating', [mom, dad]) == []
        return
    assert cast('parents_separating', [mom, dad]) == [('mom', 'dad')]
    told = person('mom', 'mom', own_ties={dad['seed']: 'married'})
    assert cast('parents_separating', [told, dad]) == []


def test_a_secret_couple_is_two_single_adults():
    first = person('ana', 'close friend', seed=seed_with_partner(False))
    second = person('bo', 'close friend', seed=seed_with_partner(False), own_ties={})
    taken = person('cy', 'close friend', seed=seed_with_partner(True))
    rows = [first, second, taken]
    assert all('cy' not in pair for pair in cast('secret_couple', rows))
    young = person('bo', 'close friend', seed=seed_with_partner(False), age=16)
    assert cast('secret_couple', [first, young]) == []


def test_a_parent_the_companion_only_knows_of_has_no_health_scare():
    known = person('mom', 'mom')
    distant = person('dad', 'dad', knowing='companion')
    assert cast('parent_health', [known, distant]) == [('mom',)]


def test_the_drunk_kiss_needs_a_single_best_friend_and_a_love_life():
    single = person('bf', 'close friend', seed=seed_with_partner(False))
    taken = person('bf', 'close friend', seed=seed_with_partner(True))
    assert cast('drunk_kiss', [single]) == [('bf',)]
    assert cast('drunk_kiss', [taken]) == []
    assert cast('drunk_kiss', [single], love_level=0) == []
