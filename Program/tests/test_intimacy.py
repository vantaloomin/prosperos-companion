"""The adult side of life (companion/world/intimacy.py): adults only, off by default, in their own prompt only."""
import json
import re
from collections import Counter

from companion.characters import require_current
from companion.life import encounters
from companion.memory.context import character_text
from companion.world import catalog, dating, intimacy, townsfolk

# Themes the bank must never touch: anyone under 18, anything without consent, family, animals, real people,
# and anything illegal or done to someone who can't say yes.
BANNED = re.compile(r'\b(minor|child|kid|teen|young|underage|school|student|age ?play|daddy|little|incest|step|'
                    r'sister|brother|mother|father|family|cousin|animal|beast|pet|non-?con|rape|forc|force|coerc|'
                    r'blackmail|drunk|asleep|sleeping|unconscious|drug|hidden|secretly|spy|public|stranger|'
                    r'celebrity|real person|blood|knife|choke|chok)', re.IGNORECASE)


def preview(client):
    return client.get('/api/context/preview').json()['prompt']


def revise(client, **changes):
    current = client.get('/api/companion').json()['companion']
    response = client.post('/api/companion/versions', json={'definition': {**current['version']['definition'], **changes},
                                                             'expected_version_id': current['active_version_id']})
    assert response.status_code == 200, response.text


def test_the_bank_only_holds_things_between_consenting_adults():
    data = json.loads((catalog.DATA / 'intimacy.json').read_text(encoding='utf-8'))
    for entry in data['interests'] + data['levels'] + data['drives']:
        words = f"{entry['id']} {entry['label']} {entry['text']}"
        assert not BANNED.search(words), words
    assert {entry['tier'] for entry in data['interests']} == {1, 2, 3}
    assert len({entry['id'] for entry in data['interests']}) == len(data['interests'])
    groups = {group['id'] for group in data['groups']}
    assert all(entry['group'] in groups for entry in data['interests'])
    assert {entry['group'] for entry in data['interests']} == groups


def test_nobody_under_18_gets_one():
    assert intimacy.roll('someone', 17, 'woman') is None
    assert intimacy.roll('someone', None, 'woman') is None
    assert intimacy.roll('someone', True, 'woman') is None
    assert intimacy.roll('someone', 18, 'woman') is not None
    for text in ('A 17-year-old barista.', 'Aged 16, loves skating.', 'A high school student.', 'Age: 15.',
                 'Still a teenager.', 'An underage runaway.'):
        assert intimacy.reads_as_minor({'identity': text}), text
        assert intimacy.rolled_for_companion(None, 'c1', None, {'identity': text}) is None
    assert not intimacy.reads_as_minor({'identity': '34, a nurse. Moved here at 12.', 'background': 'As a teen she ran.'})


def test_every_townsperson_is_an_adult_and_rolls_the_same_every_time():
    data = catalog.city('baltimore')
    sheets = [townsfolk.person(data, place, index) for place in data['places'][:40] for index in range(3)]
    sheets += townsfolk.residents(data, data['neighborhoods'][0]['id'])
    assert sheets and all(sheet['age'] >= 18 for sheet in sheets)
    for sheet in sheets:
        found = intimacy.for_sheet(sheet)
        assert found == intimacy.for_sheet(sheet)
        # The same orientation their Matchlight card has.
        assert found['orientation'] == dating.details(sheet, data)['orientation']


def test_most_people_are_in_the_middle_and_the_level_caps_what_they_are_into():
    tiers = {entry['id']: entry['tier'] for entry in intimacy.bank()['interests']}
    rolls = [intimacy.roll(f'seed-{n}', 35, 'man') for n in range(3000)]
    levels = Counter(found['level'] for found in rolls)
    assert set(levels) == set(intimacy.DRAWS)
    assert levels['curious'] > levels['adventurous'] > levels['wild']
    assert levels['conventional'] > levels['reserved']
    for found in rolls:
        count, boldest = intimacy.DRAWS[found['level']]
        assert len(found['interests']) <= count and all(tiers[entry] <= boldest for entry in found['interests'])
    assert all(not found['interests'] for found in rolls if found['level'] == 'reserved')


def test_it_is_off_by_default_and_only_their_own_prompt_has_it(client, companion):
    settings = client.get('/api/settings').json()
    assert settings['adult_side'] is False and settings['show_adult_side'] is False
    assert 'Your intimate side' not in preview(client)
    assert client.put('/api/settings', json={'adult_side': True}).json()['adult_side'] is True
    prompt = preview(client)
    assert 'Your intimate side' in prompt and 'How adventurous:' in prompt
    with client.app.state.database.connect() as connection:
        version = require_current(connection)['version']
        # Prompts whose words end up elsewhere (life events, the feed) never ask for it.
        assert 'Your intimate side' not in character_text(version, connection)
        assert 'Your intimate side' in character_text(version, connection, intimate=True)


def test_what_the_user_sets_wins_and_a_young_sheet_gets_nothing(client, companion):
    client.put('/api/settings', json={'adult_side': True})
    revise(client, identity='32, a librarian.', relationship='romance',
           intimacy={'orientation': '', 'level': 'wild', 'drive': 'low', 'interests': ['rope', 'nonsense'],
                     'note': 'Likes being asked first.'})
    prompt = preview(client)
    assert 'How adventurous: wild' in prompt and 'Drive: low; rarely the one to start things' in prompt and 'an agreed safeword' in prompt
    assert 'Likes being asked first.' in prompt and 'nonsense' not in prompt
    # A romance companion is drawn to the user; nothing rolled says otherwise.
    assert 'Orientation:' not in prompt
    revise(client, intimacy={'orientation': 'bisexual'})
    assert 'Orientation: bisexual.' in preview(client)
    revise(client, identity='A 17-year-old skater.')
    assert 'Your intimate side' not in preview(client)


def test_the_form_gets_the_roll_and_the_choices(client, companion):
    found = client.post('/api/companion/adult-side', json={'definition': companion['version']['definition']}).json()
    assert found['adult'] is True and found['rolled']['level_label']
    assert {level['id'] for level in found['levels']} == set(intimacy.DRAWS)
    young = client.post('/api/companion/adult-side', json={'definition': {'identity': 'Aged 16.'}}).json()
    assert young == {**young, 'adult': False, 'rolled': None}


def test_companions_learn_who_townsfolk_are_drawn_to_once_they_know_their_heart():
    data = catalog.city('baltimore')
    sheet = townsfolk.person(data, data['places'][0], 0)
    assert encounters.adult_side(sheet, 1, False) == {'orientation': None, 'adult_side': None}
    known = encounters.adult_side(sheet, encounters.KNOWS_HEART, True)
    assert known['orientation'] == intimacy.for_sheet(sheet)['orientation'] and known['adult_side']['level_label']
    assert encounters.adult_side({**sheet, 'cast': 'c1'}, 9, True) == {}
