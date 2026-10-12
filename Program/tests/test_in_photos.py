"""The In photos line (companion/images/prompts.py `in_photos`): what pictures say about a companion, shown and
editable on the character form."""
from companion.images import prompts

APPEARANCE = ("Kimberly is a woman with long auburn hair and freckles. She has a faint scar on her chin from a derby "
              "fall. She looks like someone who never sleeps enough. Usually wears black flats.")
EVENT = {'summary': 'Studied at the library', 'place': '', 'caption': '', 'mood': ''}


def test_left_empty_the_line_is_the_appearance_a_camera_can_see():
    line = prompts.in_photos({'name': 'Kimberly Smith', 'appearance': APPEARANCE})
    assert line == 'She is a woman with long auburn hair and freckles. She has a faint scar on her chin. ' \
                   'Usually wears black flats'
    dressed = prompts.in_photos({'name': 'Kimberly Smith', 'appearance': APPEARANCE}, dressed=True)
    assert 'flats' not in dressed and 'scar' in dressed


def test_the_users_own_line_is_used_as_written():
    definition = {'name': 'Kimberly Smith', 'appearance': APPEARANCE,
                  'in_photos': 'Kimberly has cat hair on her dark sweater, always. Black flats.'}
    assert prompts.in_photos(definition) == 'She has cat hair on her dark sweater, always. Black flats'
    assert prompts.in_photos(definition, dressed=True) == prompts.in_photos(definition)
    prompt = prompts.compose('Kimberly Smith', APPEARANCE, [EVENT], 'Candid photograph',
                             look=prompts.in_photos(definition))
    assert 'cat hair on her dark sweater' in prompt and 'auburn' not in prompt and 'Kimberly' not in prompt


def test_the_character_form_is_shown_the_automatic_line(client, companion):
    definition = {'name': 'Kimberly Smith', 'appearance': APPEARANCE, 'in_photos': 'Anything the user wrote.'}
    shown = client.post('/api/companion/looks', json={'definition': definition}).json()
    assert shown['in_photos'].startswith('She is a woman with long auburn hair') and 'derby' not in shown['in_photos']
    assert client.post('/api/companion/looks', json={'definition': {}}).json()['in_photos'] == ''


def test_the_line_is_saved_with_the_character(client, companion):
    definition = {**companion['version']['definition'], 'in_photos': 'Mira has paint on her fingers.'}
    body = {'definition': definition, 'note': 'In photos', 'expected_version_id': companion['active_version_id']}
    saved = client.post('/api/companion/versions', json=body).json()
    assert saved['version']['definition']['in_photos'] == 'Mira has paint on her fingers.'
