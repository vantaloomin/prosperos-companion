"""Family circles (companion/life/family_tree.py, family_circle.py, family_words.py): the family is planned before
the friends, at true-to-life rates for the city's era, with people who died before now and family out of touch."""
import pytest
from test_social_circle import make

from companion.characters import current
from companion.database import decode
from companion.life import circle, family_tree

MODERN = {'era': 'modern'}
SEEDS = range(3000)


@pytest.fixture(autouse=True)
def planned(monkeypatch):
    monkeypatch.setattr(family_tree, 'ACTIVE', True)


def trees(data=MODERN, definition=None, level=2, age=40):
    return [family_tree.plan(definition or {'name': 'Mira'}, data, f'seed:{seed}', age, level) for seed in SEEDS]


def share(found, test):
    return sum(map(test, found)) / len(found)


def siblings(tree):
    return sum(item['role'] == 'sibling' for item in tree['people']) + tree['minors'] + tree['more']


def test_stories_and_siblings_come_at_the_tables_rates():
    found, rates = trees(), family_tree.rates(MODERN)
    for story in ('together', 'split', 'single'):
        assert share(found, lambda tree, story=story: tree['story'] == story) == pytest.approx(rates[story], abs=0.04)
    assert share(found, lambda tree: siblings(tree) == 0) == pytest.approx(rates['siblings'][0], abs=0.04)
    assert 0 < share(found, lambda tree: tree['story'] == 'same_sex') < 0.03


def test_older_eras_have_fewer_divorces_and_bigger_families():
    today, older = trees(), trees({'era': 'victorian'})
    assert share(older, lambda tree: tree['story'] == 'split') < share(today, lambda tree: tree['story'] == 'split')
    assert sum(map(siblings, older)) > sum(map(siblings, today))


def test_a_parent_is_likelier_gone_the_older_the_companion():
    def lost(tree):
        return any(item['died_at'] is not None for item in tree['people'] if item['role'] == 'parent')
    assert share(trees(age=60), lost) > share(trees(age=25), lost) * 2


def test_simple_keeps_parents_together_alive_and_in_touch():
    for tree in trees(level=0)[:500]:
        assert tree['story'] not in ('split', 'single')
        assert all(item['died_at'] is None and not item['estranged'] for item in tree['people'])


def test_the_sheets_own_words_shape_the_family():
    def one(text):
        return family_tree.plan({'name': 'Mira', 'personality': text}, MODERN, 'seed:1', 30)
    assert siblings(one('An only child, warm and curious.')) == 0
    dads = one('Raised by two dads in a busy house.')
    assert dads['story'] == 'same_sex'
    assert [item['pronouns'] for item in dads['people'] if item['role'] == 'parent'] == ['he/him', 'he/him']
    late = one('She still misses her late mother.')
    assert any(item['died_at'] is not None and item['pronouns'] == 'she/her' for item in late['people'])
    orphan = one('An orphan who made her own way.')
    assert all(item['died_at'] is not None for item in orphan['people'] if item['role'] == 'parent')


def test_parents_the_sheet_names_are_not_two_moms():
    for seed in range(300):
        tree = family_tree.plan({'name': 'Mira'}, MODERN, f'seed:{seed}', 30, named_parents=('she/her', 'he/him'))
        assert tree['story'] not in ('same_sex', 'single')


def test_a_city_can_set_its_own_rates():
    found = trees({'era': 'modern', 'family': {'split': 0.0, 'single': 0.0, 'unknown': 5}})
    assert share(found, lambda tree: tree['story'] == 'split') == 0


def rows(client):
    client.get('/api/life/circle')  # The circle is made when first needed.
    with client.app.state.database.connect() as connection:
        companion = current(connection)
        found = [row | {'details': decode(row['details'])} for row in
                 circle.people(connection, companion['active_timeline_id'], include_removed=True)]
        return found, family_tree.context_lines(connection, companion), family_tree.stored(connection, companion['active_timeline_id'])


def test_a_new_circle_starts_from_the_family_then_friends(client):
    make(client, 'Warm and curious.', identity='34.')
    found, lines, tree = rows(client)
    kin = [row for row in found if row['details'].get('kin')]
    assert tree and len(kin) == len(tree['people'])
    assert sum(not row['details'].get('kin') for row in found) >= circle.FEWEST_FRIENDS
    assert lines and lines[0][1].startswith('- Your family: ')
    for row in kin:
        details = row['details']
        assert (row['status'] == 'removed') == bool(details.get('late') or details.get('estranged'))


def test_someone_out_of_touch_or_long_gone_shows_and_comes_back(client, monkeypatch):
    monkeypatch.setitem(family_tree.LEVELS, 2, (1.0, 8.0, 20.0))  # Loss and rifts nearly certain.
    make(client, 'Warm and curious.', identity='58.')
    found, lines, _ = rows(client)
    gone = [row for row in found if row['details'].get('estranged') or row['details'].get('long_ago') is not None]
    assert gone, found
    assert "anymore" in lines[0][1] or "died when you were" in lines[0][1]
    person = gone[0]
    shown = {item['id']: item for item in client.get('/api/life/circle').json()}
    assert person['id'] in shown
    answer = client.post(f"/api/life/circle/{person['id']}/restore")
    assert answer.status_code == 200
    back = {row['id']: row for row in rows(client)[0]}[person['id']]
    assert back['status'] == 'active'
    assert not {'late', 'long_ago', 'estranged', 'age_now'} & set(back['details'])


def test_planned_parents_are_married_or_parted_as_planned():
    mom = {'id': 'a', 'role': 'mom', 'details': {'kin': {'id': 'p1', 'ties': {'p2': 'divorced'}}}}
    dad = {'id': 'b', 'role': 'dad', 'details': {'kin': {'id': 'p2', 'ties': {'p1': 'divorced'}}}}
    assert circle.tie(mom, dad) == 'divorced'
    assert circle.tie(mom, dad, older=True) == 'separated'


def test_filling_a_planned_circle_never_adds_a_parent(client):
    make(client, 'Warm and curious.', identity='34.')
    found, _, _ = rows(client)
    friend = next(row for row in found if not row['details'].get('kin'))
    assert client.post(f"/api/life/circle/{friend['id']}/remove").status_code == 200
    client.post('/api/life/circle/grow')
    parents = [row for row in rows(client)[0] if circle.role_kind(row['role']) == 'parent']
    assert all(row['details'].get('kin') or row['details'].get('sheet') for row in parents)


def test_without_the_plan_a_circle_is_built_as_before(client, monkeypatch):
    monkeypatch.setattr(family_tree, 'ACTIVE', False)
    make(client, 'Warm and curious.', identity='34.')
    found, lines, tree = rows(client)
    assert tree is None and lines == []
    assert not any(row['details'].get('kin') for row in found)


def test_the_family_shapes_slider_saves(client):
    make(client, 'Warm and curious.')
    assert client.put('/api/life/settings', json={'family_shapes': 0}).json()['family_shapes'] == 0
    assert client.put('/api/life/settings', json={'family_shapes': 4}).status_code == 422


def test_step_and_half_family_are_never_just_met():
    from companion.memory import pairs
    for role in ('stepmom', 'stepdad', 'half sister', 'stepbrother'):
        assert all(pairs.role_default(role, f'seed:{seed}')['level'] >= 2 for seed in range(50)), role


def test_planned_family_in_touch_starts_at_least_comfortable(client):
    from companion.memory import pairs
    make(client, 'Warm and curious.', identity='34.')
    stages = {row['id']: row for row in client.get('/api/life/circle').json()}
    for row in rows(client)[0]:
        if row['details'].get('kin') and row['status'] == 'active':
            assert stages[row['id']]['stage']['level'] >= pairs.PLANNED_FLOOR, row['role']
