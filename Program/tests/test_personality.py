"""Personality sliders (companion/world/personality.py): rolled for everyone, the user's words and changes win."""
import json
import re
from collections import Counter

from test_drafting import GOOD, connect, replying
from test_perception import GENDERED
from test_social_circle import make

from companion import cast
from companion.characters import require_current
from companion.life import town_personality
from companion.memory.context import character_text
from companion.world import catalog, perception, personality, townsfolk

TRAIT_NAMES = re.compile(r'\b(openness|conscientious\w*|extravers\w*|extrovers\w*|agreeabl\w*|neurotic\w*)\b', re.I)


def test_the_words_are_plain_and_every_bank_id_they_name_exists():
    bank = personality.bank()
    assert [trait['key'] for trait in bank['traits']] == ['social', 'warmth', 'order', 'curiosity', 'stress']
    for trait in bank['traits']:
        assert len(trait['shows']) == len(trait['model']) == 3 and trait['model'][1] == ''
        for text in [trait['name'], trait['low'], trait['high'], *trait['shows'], *trait['model']]:
            assert not TRAIT_NAMES.search(text) and not GENDERED.search(text), text
        assert 'anxious' not in json.dumps(trait['shows']) and 'neurotic' not in json.dumps(trait['shows'])
    ids = perception.ids()
    for facet, table in bank['implies'].items():
        assert set(table) <= set(ids[facet]), facet
        for poles in table.values():
            assert set(poles) <= set(personality.keys()) and set(poles.values()) <= {'low', 'high'}


def test_everyone_is_rolled_with_at_least_two_traits_away_from_the_middle():
    rolled = [personality.levels_of(personality.settle({}, f'seed-{n}')) for n in range(3000)]
    assert all(sum(level != 1 for level in levels.values()) >= 2 for levels in rolled)
    # Each stop turns up for every trait, so people around town differ.
    for key in personality.keys():
        counts = Counter(levels[key] for levels in rolled)
        assert all(counts[level] > 500 for level in (0, 1, 2)), (key, counts)
    assert personality.settle({}, 'same') == personality.settle({}, 'same')


def test_the_characters_own_words_settle_a_slider_and_the_roll_fills_the_rest():
    found = personality.from_words('A kind kindergarten teacher, kind of shy, never late, not lazy at all.')
    assert found == {'warmth': 2, 'social': 0}
    assert personality.from_words('Outgoing at work, but a quiet homebody at weekends.') == {'social': 1}
    sliders = personality.settle({'personality': 'Calm, and always late.'}, 'seed')
    assert sliders['stress'] == {'level': 0, 'source': 'idea'} and sliders['order'] == {'level': 0, 'source': 'idea'}
    assert {value['source'] for key, value in sliders.items() if key not in ('stress', 'order')} == {'rolled'}


def test_roll_again_and_a_type_only_change_what_the_user_and_their_idea_left_open():
    start = personality.settle({'personality': 'Shy.'}, 'seed')
    start['stress'] = {'level': 2, 'source': 'you'}
    for attempt in range(20):
        again = personality.reroll(start, f'seed:{attempt}')
        assert again['social'] == start['social'] and again['stress'] == start['stress']
        assert sum(value['level'] != 1 for value in again.values()) >= 2
    assert len({json.dumps(personality.reroll(start, f'seed:{n}')) for n in range(20)}) > 5
    typed = personality.from_type('enfj', start)
    assert typed['social'] == {'level': 0, 'source': 'idea'}  # Their idea says shy; the type leaves it.
    assert typed['curiosity'] == typed['warmth'] == typed['order'] == {'level': 2, 'source': 'you'}
    assert typed['stress'] == start['stress']
    assert personality.type_of(personality.levels_of(typed)) == 'INFJ'
    assert personality.type_of({'social': 1, 'curiosity': 2, 'warmth': 2, 'order': 2}) is None


def test_words_that_agree_with_a_roll_leave_it_rolled_and_words_that_differ_win():
    saved = {key: {'level': 2, 'source': 'rolled'} for key in personality.keys()}
    same = personality.settle({'personality': 'Outgoing.', 'personality_sliders': saved}, 'seed')
    assert same['social'] == {'level': 2, 'source': 'rolled'}
    other = personality.settle({'personality': 'Shy.', 'personality_sliders': saved}, 'seed')
    assert other['social'] == {'level': 0, 'source': 'idea'}
    mine = {**saved, 'social': {'level': 2, 'source': 'you'}}
    assert personality.settle({'personality': 'Shy.', 'personality_sliders': mine}, 'seed')['social']['source'] == 'you'


def test_the_model_reads_behaviour_only_and_nothing_for_the_middle():
    levels = {'social': 2, 'warmth': 1, 'order': 0, 'curiosity': 1, 'stress': 1}
    lines = personality.behaviour(levels)
    assert len(lines) == 2 and lines[0].startswith('Starts conversations') and lines[1].startswith('Runs late')
    assert personality.chips(levels) == ['Outgoing', 'Goes with the flow']
    assert personality.behaviour(dict.fromkeys(personality.keys(), 1)) == []


def test_perception_picks_suit_the_sliders():
    organized = {'order': 2}
    assert not personality.fits('tell', 'always-late', organized) and personality.fits('tell', 'always-early', organized)
    assert personality.fits('tell', 'always-late', {'order': 1})
    menu = perception.menu(organized)
    assert 'always-early' in menu and 'always-late' not in menu and 'always-late' in perception.menu()
    for n in range(200):
        definition = {'name': 'Bo', 'personality_sliders': {'order': {'level': 2, 'source': 'you'}}}
        picks = perception.automatic(definition, f'seed-{n}')['picks']
        assert all(personality.fits(facet, picks[facet], organized) for facet in ('tell', 'flaw', 'self_story'))


def test_townsfolk_sliders_follow_their_sheet_and_their_habits_fit():
    data = catalog.city('baltimore')
    checked = 0
    for place in data['places'][:60]:
        for sheet in townsfolk.at_place(data, place['id']):
            sliders = personality.for_sheet(townsfolk.drawn(sheet), sheet)
            levels = personality.levels_of(sliders)
            for key, pole in personality.sheet_words(sheet).items():
                assert levels[key] == pole
            picks = perception.for_sheet(data, sheet)['picks']
            checked += personality.fits('tell', picks['tell'], levels)
    assert checked > 100
    shy = {'temperament': 'shy', 'flaw': 'messy', 'key': 'k'}
    assert personality.sheet_words(shy) == {'social': 0, 'order': 0}
    assert personality.sheet_words({'temperament': 'cheerful', 'flaw': 'worrier'}) == {'stress': 1}


def test_a_companion_prompt_gets_the_behaviour_lines(client):
    sliders = {'social': {'level': 2, 'source': 'you'}, 'warmth': {'level': 1, 'source': 'you'},
               'order': {'level': 1, 'source': 'you'}, 'curiosity': {'level': 1, 'source': 'you'},
               'stress': {'level': 0, 'source': 'you'}}
    make(client, 'Likes crosswords.', personality_sliders=sliders)
    with client.app.state.database.connect() as connection:
        prompt = character_text(require_current(connection)['version'], connection)
    assert 'How you tend to act' in prompt
    assert '- Starts conversations easily' in prompt and '- Stays calm under pressure' in prompt
    assert 'Outgoing' not in prompt and 'Steady' not in prompt


def test_a_companion_saved_before_sliders_gets_the_same_ones_every_time(client):
    companion = make(client, 'Shy, and a bit of a worrier.')
    assert companion['version']['definition']['personality_sliders'] is None
    first = client.post('/api/companion/personality', json={'definition': companion['version']['definition']}).json()
    again = client.post('/api/companion/personality', json={'definition': companion['version']['definition']}).json()
    assert first == again
    assert first['sliders']['social'] == {'level': 0, 'source': 'idea'}
    assert first['sliders']['stress'] == {'level': 2, 'source': 'idea'}
    assert 'Reserved' in first['chips'] and [trait['key'] for trait in first['traits']][0] == 'social'
    rolled = client.post('/api/companion/personality', json={'definition': companion['version']['definition'],
                                                            'roll': 3}).json()
    assert rolled['sliders']['social'] == first['sliders']['social']
    bad = client.post('/api/companion/personality', json={'definition': {}, 'type': 'XXXX'})
    assert bad.status_code == 422


def test_a_new_character_form_rolls_from_its_own_seed(client):
    one = client.post('/api/companion/personality', json={'definition': {}, 'seed': 'a'}).json()
    two = client.post('/api/companion/personality', json={'definition': {}, 'seed': 'a'}).json()
    assert one == two
    others = {json.dumps(client.post('/api/companion/personality', json={'definition': {}, 'seed': s}).json()['sliders'])
              for s in 'bcdefgh'}
    assert len(others) > 3


def test_the_quick_start_rolls_first_and_the_idea_wins(client, provider):
    connect(client)
    provider.respond = replying(json.dumps(GOOD))
    response = client.post('/api/companion/draft', json={'idea': 'a kind, shy kindergarten teacher', 'timezone': 'UTC'})
    assert response.status_code == 200, response.text
    sliders = response.json()['definition']['personality_sliders']
    assert sliders['warmth'] == {'level': 2, 'source': 'idea'} and sliders['social'] == {'level': 0, 'source': 'idea'}
    system = provider.requests[0]['system']
    assert 'Their personality, decided by the app' in system
    assert 'Gives people the benefit of the doubt' in system and 'Needs time alone to recharge' in system
    assert 'Warm' not in system.split('Their personality, decided by the app')[1].split('\n\n')[0]


def test_townsfolk_sliders_can_be_edited_and_carry_over_when_they_take_over(client):
    make(client, 'Outgoing.')
    with client.app.state.database.connect() as connection:
        companion = require_current(connection)
        data = catalog.city('baltimore')
        sheet = townsfolk.at_place(data, data['places'][0]['id'])[0]
        before = town_personality.view(sheet, None)
        changed = {key: dict(value) for key, value in before['sliders'].items()}
        changed['warmth'] = {'level': 0 if before['sliders']['warmth']['level'] else 2, 'source': 'you'}
    with client.app.state.database.connect(write=True) as connection:
        town_personality.save(connection, town_personality.town_of(companion), sheet['key'], changed, 'now')
        kept = town_personality.edited(connection, town_personality.town_of(companion), sheet['key'])
    assert list(kept) == ['warmth']
    after = town_personality.view(sheet, kept)
    assert after['sliders']['warmth'] == changed['warmth']
    assert {key: value for key, value in after['sliders'].items() if key != 'warmth'} == \
           {key: value for key, value in before['sliders'].items() if key != 'warmth'}
    definition = cast.profile(data, sheet, {'focus': None, 'match': None, 'meetings': [], 'in_story': None},
                              __import__('datetime').date(2026, 3, 1), kept)
    assert definition['personality_sliders']['warmth'] == changed['warmth']
    lines = perception.sheet_lines(data, sheet, kept)
    assert lines['behaviour'] == personality.behaviour(personality.levels_of(after['sliders']))


def test_unknown_townsfolk_cannot_be_edited(client):
    make(client, 'Outgoing.')
    response = client.post('/api/life/townsfolk/personality',
                           json={'key': 'town:baltimore:nowhere:0', 'sliders': {'social': {'level': 2, 'source': 'you'}}})
    assert response.status_code == 404
