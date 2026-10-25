"""Choosing what to import from a file: the preview of what it holds, and importing only the ticked parts
(companion/imports/characters.py `inspect` and `bring`, companion/world/marinara.py for world maps)."""
import copy

from tests.test_bring_characters import CARD, IHDR, as_json, encoded, png_with
from tests.test_marinara_world import sample

V3 = {'spec': 'chara_card_v3', 'spec_version': '3.0', 'data': {
    **copy.deepcopy(CARD['data']), 'alternate_greetings': ['hi again'], 'creator_notes': 'Made for fun.'}}
MARINARA = {'type': 'marinara_character', 'version': 1, 'data': {**copy.deepcopy(CARD), 'avatar': None}}
MARINARA['data']['data']['extensions'] = {'appearance': 'Short dark hair.', 'backstory': 'Grew up by the docks.'}
BOOK = {'name': 'Harbour lore', 'entries': {'0': {'key': ['pier'], 'content': 'The pier is closed.'},
                                            '1': {'key': ['tide'], 'content': 'High tide at six.'}}}


def inspect(client, filename, data, status=200):
    response = client.post('/api/import/character/inspect', json={'filename': filename, 'data': data})
    assert response.status_code == status, response.text
    return response.json()


def bring(client, filename, data, pick=None, status=200):
    body = {'filename': filename, 'data': data} | ({'pick': pick} if pick is not None else {})
    response = client.post('/api/import/character', json=body)
    assert response.status_code == status, response.text
    return response.json()


def books(client):
    return {book['name']: book for book in client.get('/api/lore').json()['books'] if not book['city']}


def test_a_card_lists_its_character_lorebook_and_the_parts_left_out_without_saving(client, companion):
    found = inspect(client, 'dana.json', as_json(V3))
    assert found['format'] == 'Character Card V3' and found['character']['name'] == 'Dana Reyes'
    assert found['character']['about'].startswith('Dana Reyes is a night nurse') and not found['character']['more_about']
    assert found['picture'] is None and found['already'] is None
    assert [entry['title'] for entry in found['book']['entries']] == ['Brother', 'Entry 2', 'Entry 3', 'Entry 4']
    assert [entry['enabled'] for entry in found['book']['entries']] == [True, True, False, False]
    assert found['unused'] == ['Scenario', 'First message', 'Other greetings', "Creator's notes", 'System prompt']
    assert [member['name'] for member in found['companions']] == ['Mira']
    assert len(client.get('/api/companion/cast').json()['members']) == 1 and 'Dana lore' not in books(client)


def test_everything_ticked_is_the_same_as_before(client):
    made = bring(client, 'dana.json', as_json(CARD), {})
    assert made['companion']['version']['name'] == 'Dana Reyes' and made['book']['entries'] == 4
    assert made['book']['owner'] == 'Dana Reyes' and not made['book']['world']


def test_only_the_lorebook_becomes_the_worlds(client, companion):
    made = bring(client, 'dana.json', as_json(CARD), {'character': False})
    assert made['companion'] is None and made['book']['world'] and made['book']['owner'] is None
    assert [member['name'] for member in client.get('/api/companion/cast').json()['members']] == ['Mira']
    assert books(client)['Dana lore']['world']


def test_only_some_entries_for_a_companion_already_here(client, companion):
    made = bring(client, 'dana.json', as_json(CARD), {'character': False, 'entries': [1, 0, 0, 9],
                                                      'lore_for': companion['id']})
    assert made['book']['owner'] == 'Mira' and made['book']['entries'] == 2 and not made['book']['world']
    assert [entry['title'] for entry in books(client)['Dana lore']['entries']] == ['Brother', 'Entry 2']


def test_a_new_character_whose_lorebook_goes_to_the_world(client, companion):
    made = bring(client, 'dana.json', as_json(CARD), {'lore_for': 'world'})
    assert made['companion']['version']['name'] == 'Dana Reyes' and made['book']['world']
    assert made['book']['owner'] is None


def test_the_character_without_their_lorebook_or_picture(client):
    card = encoded(png_with([(b'IHDR', IHDR), (b'tEXt', b'chara\0' + as_json(CARD).encode())]))
    assert inspect(client, 'dana.png', card)['picture'] == {'usable': True, 'note': None, 'portrait': False}
    made = bring(client, 'dana.png', card, {'book': False, 'picture': False})
    assert made['companion']['version']['name'] == 'Dana Reyes' and made['book'] is None
    assert made['picture'] is False and made['picture_note'] is None and 'Dana lore' not in books(client)


def test_a_long_description_stays_theirs_when_the_lorebook_goes_elsewhere(client):
    card = copy.deepcopy(CARD)
    card['data']['description'] = 'Dana ' + 'restores boats. ' * 1200
    assert inspect(client, 'dana.json', as_json(card))['character']['more_about'] is True
    made = bring(client, 'dana.json', as_json(card), {'lore_for': 'world'})
    found = books(client)
    assert made['book']['world'] and found['Dana lore']['world']
    assert [entry['title'] for entry in found['Dana Reyes lore']['entries']] == ['More about Dana Reyes']
    assert not found['Dana Reyes lore']['world']


def test_someone_already_here_starts_as_the_lorebooks_owner(client):
    bring(client, 'dana.json', as_json(CARD))
    found = inspect(client, 'dana.json', as_json(MARINARA))
    assert found['format'] == 'Marinara Engine character' and found['already']['name'] == 'Dana Reyes'


def test_a_lorebook_file_and_nothing_ticked(client, companion):
    found = inspect(client, 'harbour.json', as_json(BOOK))
    assert found['character'] is None and found['unused'] == [] and len(found['book']['entries']) == 2
    assert bring(client, 'harbour.json', as_json(BOOK), {'book': False}, 422)['detail'] == 'Tick something to import.'
    assert bring(client, 'harbour.json', as_json(BOOK), {'entries': []}, 422)['detail'] == 'Tick something to import.'
    assert 'no longer here' in bring(client, 'harbour.json', as_json(BOOK), {'lore_for': 'nobody'}, 404)['detail']
    assert bring(client, 'harbour.json', as_json(BOOK), {'entries': [1]})['book']['entries'] == 1


def test_a_world_map_lists_its_city_and_lore_and_imports_either(client, companion):
    found = client.post('/api/world/import/marinara/inspect', json=sample()).json()
    assert found['city']['name'] == 'Lisbon' and found['already'] is None and found['book']['entries']
    picked = client.post('/api/world/import/marinara/picked', json={'map': sample(), 'pick': {'book': False}}).json()
    assert picked['name'] == 'Lisbon' and picked['book'] is None
    assert client.post('/api/world/import/marinara/inspect', json=sample()).json()['already'] == 'Lisbon'
    lore = client.post('/api/world/import/marinara/picked',
                       json={'map': sample(), 'pick': {'city': False, 'entries': [0]}}).json()
    assert lore['name'] is None and lore['book']['entries'] == 1 and lore['book']['world']
    refused = client.post('/api/world/import/marinara/picked', json={'map': sample(), 'pick': {'city': False,
                                                                                              'book': False}})
    assert refused.status_code == 422
