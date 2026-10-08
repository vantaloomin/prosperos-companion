"""How others see a person and how they see themselves (companion/world/perception.py)."""
import json
import re
from collections import Counter

from test_drafting import GOOD, connect, replying
from test_social_circle import make

from companion.characters import require_current
from companion.life import encounters
from companion.memory.context import character_text
from companion.world import catalog, perception, townsfolk

GENDERED = re.compile(r"\b(he|she|him|her|his|hers|himself|herself|man|woman|men|women|guy|girl|boy|lady|ladies|"
                      r"gentleman|husband|wife|son|daughter|mother|father|brother|sister|mr|mrs|ms)\b", re.I)
SEEN_FIELDS = {'seen', 'glimpse'}


def walk(node, path=()):
    """Every phrase in the bank with the path to it (keywords and ids aside)."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key not in ('keywords', 'id', 'tags', 'inner', 'about', 'gap_kinds') and not key.endswith('_by_id'):
                yield from walk(value, (*path, key))
    elif isinstance(node, list):
        for item in node:
            yield from walk(item, path)
    elif isinstance(node, str):
        yield path, node


def test_the_bank_is_big_varied_and_safe_to_say_about_anyone():
    bank = perception.bank()
    assert set(bank['temperaments']) == set(townsfolk.TEMPERAMENTS)
    assert set(bank['flaws']) == set(townsfolk.FLAWS) and set(bank['desires']) == set(townsfolk.DESIRES)
    assert len(bank['tells']) >= 60 and len(bank['self_stories']) >= 40 and len(bank['sore_spots']) >= 40
    for kind in ('tells', 'self_stories', 'sore_spots'):
        assert len(bank[f'{kind}_by_id']) == len(bank[kind]), f'{kind} ids repeat'
    phrases = list(walk({key: value for key, value in bank.items() if not key.endswith('_by_id')}))
    assert len(phrases) > 1500
    repeated = [text for text, count in Counter(text for _path, text in phrases).items() if count > 1]
    assert not repeated, repeated[:5]
    for path, text in phrases:
        assert not GENDERED.search(text), (path, text)
        assert '"' not in text and text == text.strip(), (path, text)
        if SEEN_FIELDS & set(path):
            assert text[:1].islower() or text[:1].isdigit() or text.startswith('I'), (path, text)
            assert not text.endswith('.'), (path, text)
        else:
            assert text[-1] in '.!?', (path, text)


def test_the_same_person_always_gets_the_same_lines():
    data = catalog.city('baltimore')
    place = data['places'][0]
    first = [perception.for_sheet(data, sheet) for sheet in townsfolk.at_place(data, place['id'])]
    again = [perception.for_sheet(data, sheet) for sheet in townsfolk.at_place(data, place['id'])]
    assert first == again
    person = first[0]
    assert person['public'].count('; ') == 2 and person['public'].endswith('.')
    assert len(person['private']) == 6 and all(line[-1] in '.!?' for line in person['private'])


def test_nobody_at_one_place_or_on_one_street_shares_a_habit_or_a_self_story():
    for data in catalog.cities().values():
        for place in data['places']:
            people = [perception.for_sheet(data, sheet) for sheet in townsfolk.at_place(data, place['id'])]
            for facet in ('tell', 'self_story'):
                picks = [person['picks'][facet] for person in people]
                assert len(picks) == len(set(picks)), (data['id'], place['id'], facet)
    data = catalog.city('baltimore')
    hood = data['neighborhoods'][0]['id']
    tells = [perception.for_sheet(data, townsfolk.resident(data, hood, n))['picks']['tell'] for n in range(40)]
    assert len(set(tells)) == 40


def test_gaps_are_per_facet_at_most_two_and_often_none():
    found = [perception.gaps(f'seed-{n}') for n in range(4000)]
    gapped = [sum(kind != 'aligned' for kind in gap.values()) for gap in found]
    assert max(gapped) == 2
    assert 0.15 < gapped.count(0) / len(found) < 0.27
    assert all(gap[facet] in (perception.GAPS[facet], 'aligned') for gap in found for facet in gap)
    # Facets roll on their own, so mixed gaps happen.
    assert any(gap['temperament'] == 'mask' and gap['flaw'] == 'blind_spot' for gap in found)


def test_a_gap_changes_only_that_facets_own_line():
    picks = {'temperament': 'cheerful', 'tell': perception.ids()['tell'][0], 'flaw': 'gossip', 'desire': 'respect',
             'self_story': perception.ids()['self_story'][0], 'sore_spot': perception.ids()['sore_spot'][0]}
    aligned = dict.fromkeys(perception.FACETS, 'aligned')
    plain = perception.build('s', picks, aligned, True)
    blind = perception.build('s', picks, {**aligned, 'flaw': 'blind_spot'}, True)
    masked = perception.build('s', picks, {**aligned, 'temperament': 'mask'}, True)
    assert plain['public'] == blind['public'] == masked['public']
    flaw = perception.entry('flaw', 'gossip')
    assert plain['private'][3] in flaw['owned'] and blind['private'][3] in flaw['excuse']
    masks = [line for mask in perception.entry('temperament', 'cheerful')['masks'] for line in mask['own']]
    assert masked['private'][1] in masks and masked['inner']
    assert [line for n, line in enumerate(plain['private']) if n != 3] == \
           [line for n, line in enumerate(blind['private']) if n != 3]


def test_a_townsperson_is_revealed_meeting_by_meeting():
    data = catalog.city('baltimore')
    sheet = townsfolk.at_place(data, data['places'][0]['id'])[0]
    full = perception.for_sheet(data, sheet)
    assert perception.revealed(data, sheet, 0) == {}
    once = perception.revealed(data, sheet, 1)
    assert full['public'].startswith(once['comes_across'][:-1]) and 'says_they_are' not in once
    assert perception.revealed(data, sheet, 2) == {'comes_across': full['public']}
    thrice = perception.revealed(data, sheet, 3)
    assert thrice['says_they_are'] == full['glimpse']
    meetings = [{'place': 'X', 'local_date': '2026-03-0' + str(n), 'met_at': ''} for n in range(1, 4)]
    person = encounters.revealed(sheet, data, meetings, None, None)
    text = encounters.text(person)
    assert f"How they come across: {full['public']}" in text and full['glimpse'] in text
    # The sore spot never shows to anyone else.
    assert not any(line in text for line in full['private'])


def test_word_matching_reads_the_sheet():
    definition = {'name': 'Rae', 'flaws': ["Can't say no to anyone who asks for a favour."],
                  'personality': 'Cheerful and bubbly, the glue of the friend group.'}
    picks = perception.rule_picks(definition, 'seed')
    assert picks['flaw'] == 'pleaser' and picks['temperament'] == 'cheerful'
    lines = perception.for_companion('companion-1', definition)
    pleaser = perception.entry('flaw', 'pleaser')
    assert lines['private'][3] in pleaser['owned'] + pleaser['excuse']
    assert any(phrase in lines['public'] for phrase in pleaser['seen'])
    assert perception.for_companion('companion-1', definition) == lines
    # Nothing to match: the seed decides, the same every time.
    assert perception.rule_picks({'name': 'Bo'}, 'seed') == {}
    assert perception.for_companion('c2', {'name': 'Bo'}) == perception.for_companion('c2', {'name': 'Bo'})


def test_what_the_user_writes_wins_and_goes_in_their_own_prompt_only_as_theirs():
    definition = {'name': 'Rae', 'seen_as': 'Seems unflappable; always early; hates small talk.',
                  'sees_self': '- I am the calm one.\n\nI hate being rushed.'}
    lines = perception.for_companion('c1', definition)
    assert lines['public'] == 'Seems unflappable; always early; hates small talk.'
    assert lines['private'] == ['I am the calm one.', 'I hate being rushed.'] and lines['glimpse'] is None
    text = perception.own_text(lines['public'], lines['private'])
    assert 'How others see you' in text and '- I hate being rushed.' in text


def test_the_helper_picks_by_id_and_unknown_ids_are_dropped():
    tell = perception.ids()['tell'][3]
    found = perception.compose({'name': 'Rae'}, 'seed', {'flaw': 'pleaser', 'tell': tell, 'desire': 'not-a-desire',
                                                         'mood': 'x'}, {'flaw': 'blind_spot', 'tell': 'mask'})
    pleaser = perception.entry('flaw', 'pleaser')
    assert any(phrase in found['seen_as'] for phrase in pleaser['seen'])
    assert any(phrase in found['seen_as'] for phrase in perception.entry('tell', tell)['seen'])
    assert found['sees_self'].split('\n')[3] in pleaser['excuse']
    assert perception.valid_gaps({'flaw': 'blind_spot', 'tell': 'mask'}) == {
        **dict.fromkeys(perception.FACETS, 'aligned'), 'flaw': 'blind_spot'}
    assert perception.valid_gaps(None) is None
    assert 'pleaser' in perception.menu() and tell in perception.menu()


def test_the_quick_start_keeps_the_models_bank_picks(client, provider):
    connect(client)
    raw = {**GOOD, 'perception': {'flaw': 'gossip', 'temperament': 'made-up', 'gaps': {'flaw': 'blind_spot'}}}
    provider.respond = replying(json.dumps(raw))
    response = client.post('/api/companion/draft', json={'idea': 'a tired nurse', 'timezone': 'UTC'})
    assert response.status_code == 200, response.text
    definition = response.json()['definition']
    gossip = perception.entry('flaw', 'gossip')
    assert any(phrase in definition['seen_as'] for phrase in gossip['seen'])
    assert definition['sees_self'].split('\n')[3] in gossip['excuse']
    assert 'self_story' in provider.requests[0]['system']
    # Without picks the fields stay empty and fill themselves in from the sheet.
    provider.respond = replying(json.dumps(GOOD))
    plain = client.post('/api/companion/draft', json={'idea': 'a tired nurse', 'timezone': 'UTC'}).json()
    assert plain['definition']['seen_as'] == '' and plain['definition']['sees_self'] == ''


def test_a_companion_prompt_holds_both_lines_and_group_chat_gets_them_split(client):
    companion = make(client, 'Cheerful and bubbly.', flaws=["Can't say no."])
    with client.app.state.database.connect() as connection:
        current = require_current(connection)
        prompt = character_text(current['version'], connection)
        lines = perception.companion_lines(connection, companion['id'])
        assert perception.companion_lines(connection, 'nobody') == {'public': '', 'private': []}
    assert lines['public'] and len(lines['private']) == 6
    assert f"How others see you (how you come across, whether or not you agree): {lines['public']}" in prompt
    assert all(f'- {line}' in prompt for line in lines['private'])


def test_the_form_gets_suggestions_that_fit(client):
    body = {'definition': {'name': 'Rae', 'flaws': ["Can't say no."]}}
    fresh = client.post('/api/companion/perception', json=body).json()
    assert fresh['automatic'] is None and len(fresh['seen_as']) == 6 and len(set(fresh['sees_self'])) == 6
    pleaser = perception.entry('flaw', 'pleaser')
    assert all(any(phrase in line for phrase in pleaser['seen']) for line in fresh['seen_as'])
    make(client, 'Warm.')
    saved = client.post('/api/companion/perception', json=body).json()
    assert saved['automatic']['seen_as'] == saved['seen_as'][0]


def test_a_townsperson_who_becomes_a_companion_keeps_their_lines():
    from datetime import date

    from companion import cast
    data = catalog.city('baltimore')
    sheet = townsfolk.at_place(data, data['places'][0]['id'])[0]
    definition = cast.profile(data, sheet, {'meetings': [], 'in_story': None, 'match': None, 'focus': {'version': {'name': 'Mira'}}}, date(2026, 3, 2))
    lines = perception.for_sheet(data, sheet)
    assert definition['seen_as'] == lines['public'] and definition['sees_self'] == '\n'.join(lines['private'])


def test_period_towns_use_period_wording_where_the_bank_has_it():
    data = catalog.city('london-1895')
    assert not townsfolk.modern(data)
    sheet = townsfolk.at_place(data, data['places'][0]['id'])[0]
    assert perception.for_sheet(data, sheet)['public']
