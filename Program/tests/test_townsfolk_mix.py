"""Settings > Debug > Townsfolk mix (companion/world/mix.py, companion/townsfolk_mix.py): the shares the townsfolk
rolls use, shown, and a new world made with changed ones."""
from statistics import mean

import pytest

from companion.world import catalog, dating, generators, intimacy, mix, townsfolk


@pytest.fixture(autouse=True)
def built_in_mix():
    yield
    mix._active = dict(mix.DEFAULTS)


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


def residents(count=600):
    data = catalog.city('baltimore')
    hood = data['neighborhoods'][0]['id']
    total = townsfolk.resident_count(data, hood)
    sheets = [townsfolk.resident(data, hood, index) for index in range(total)]
    more = [townsfolk.resident(data, other['id'], index) for other in data['neighborhoods'][1:]
            for index in range(townsfolk.resident_count(data, other['id']))]
    return data, (sheets + more)[:count]


def test_the_built_in_mix_is_what_the_rolls_always_used():
    assert mix.current() == mix.DEFAULTS and mix.fingerprint() == ''
    assert mix.pronoun_weights(True) == [47, 47, 6] and mix.pronoun_weights(False) == [47, 47, 2]
    assert all(dating.rates(band[0]) == band for band in dating.ORIENTATION_RATES)
    assert mix.height_mean('woman', 162) == 162 and mix.beard_share() == 0.35
    # The slider values match the built-in rates across the town's ages.
    assert round(mix.built_in_share('gay'), 1) == mix.DEFAULTS['gay']
    assert round(mix.built_in_share('bisexual'), 1) == mix.DEFAULTS['bisexual']


def test_a_changed_mix_changes_who_the_town_is():
    data, people = residents()
    before = [dating.details(sheet, data) for sheet in people]
    with mix.using({'gay': 30, 'bisexual': 30, 'height_man': 190, 'beard': 100, 'slender': 0, 'middle': 0,
                    'heavier': 100}):
        after = [dating.details(sheet, data) for sheet in people]
    queer = {'gay', 'lesbian', 'bisexual'}
    assert sum(item['orientation'] in queer for item in after) > 4 * sum(item['orientation'] in queer for item in before)
    men = [item['looks'] for item in after if item['gender'] == 'man']
    assert mean(looks['height_cm'] for looks in men) > 185 and all(looks.get('beard') for looks in men)
    heavier = set(dating.BUILD_GROUPS['heavier']) | {'athletic'}  # Sporty people stay athletic.
    assert all(item['looks']['build'] in heavier for item in after)


def test_the_gender_mix_goes_through_every_name_drawn():
    data = catalog.city('baltimore')
    with mix.using({'nonbinary': 0, 'women': 100}):
        drawn = {generators.name(data, seed=f'mix-{n}')['pronouns'] for n in range(200)}
    assert drawn == {'she/her'}


def test_ages_and_the_adult_check_never_follow_the_mix():
    data, people = residents(100)
    with mix.using({'bolder': 2, 'drive': 2, 'gay': 40, 'nonbinary': 40}):
        assert [sheet['age'] for sheet in residents(100)[1]] == [sheet['age'] for sheet in people]
        assert intimacy.roll('someone', 17, 'woman') is None
        bold = [intimacy.roll(f'p{n}', 30, 'woman')['level'] for n in range(300)]
    plain = [intimacy.roll(f'p{n}', 30, 'woman')['level'] for n in range(300)]
    assert bold.count('wild') > plain.count('wild')


def test_debug_shows_the_mix_and_what_the_town_is_made_of(client, companion):
    found = ok(client.get('/api/townsfolk-mix'))
    assert found['mix'] == found['defaults'] and found['town']['people'] > 500
    town = found['town']
    assert 40 < town['genders']['woman'] < 60 and 150 < town['heights']['woman'] < 175
    assert sum(found['levels']['0'].values()) == pytest.approx(100, abs=0.5)
    assert len(found['bands']) == len(dating.ORIENTATION_RATES)


def test_a_new_world_takes_the_mix_and_the_old_one_keeps_its_own(client, companion, app):
    first = ok(client.get('/api/worlds'))['world']
    switched = ok(client.post('/api/townsfolk-mix/new-world', json={'mix': {'gay': 20, 'height_woman': 999}}))
    assert switched['world']['id'] != first['id']
    assert mix.current()['gay'] == 20 and mix.current()['height_woman'] == mix.LIMITS['height_woman'][1]
    assert ok(client.get('/api/townsfolk-mix'))['mix']['gay'] == 20
    # A world made from this one keeps the mix (so becoming a townsperson keeps the same people).
    made = ok(client.post('/api/worlds', json={}))
    ok(client.post(f"/api/worlds/{made['id']}/switch"))
    assert mix.current()['gay'] == 20
    # The first world, with its companion and townsfolk, is as it was.
    ok(client.post(f"/api/worlds/{first['id']}/switch"))
    assert mix.current() == mix.DEFAULTS
    assert ok(client.get('/api/companion'))['companion']['version']['name'] == 'Mira'


def test_with_100_percent_matches_every_like_is_a_match(client):
    assert ok(client.get('/api/debug-matches')) == {'on': False}
    ok(client.put('/api/debug-matches', json={'on': True}))
    state = ok(client.put('/api/dating/profile', json={'name': 'Sam', 'age': 30, 'gender': 'man',
                                                        'interested_in': ['woman'], 'looking_for': 'serious',
                                                        'age_min': 22, 'age_max': 40, 'bio': ''}))
    for _ in range(5):
        state = ok(client.post('/api/dating/swipes', json={'key': state['deck'][0]['key'], 'like': True}))
        assert state['matched']
    # A pass is still a pass.
    assert not ok(client.post('/api/dating/swipes', json={'key': state['deck'][0]['key'], 'like': False}))['matched']
