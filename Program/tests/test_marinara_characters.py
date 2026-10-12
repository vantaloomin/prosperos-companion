"""Marinara Engine's own .marinara.json exports (companion/imports/formats.py `marinara`)."""
import base64

from tests.test_bring_characters import IHDR, as_json, bring, png_with


def tiny_png() -> bytes:
    return png_with([(b'IHDR', IHDR)])


def envelope(kind, data):
    return {'type': kind, 'version': 1, 'exportedAt': '2026-10-07T12:00:00.000Z', 'data': data}


def character(avatar: bytes | None = None, **extensions):
    data = {'spec': 'chara_card_v2', 'spec_version': '2.0', 'metadata': {'createdAt': '2026-01-01'},
            'sprites': [{'filename': 'happy.png', 'data': 'data:image/png;base64,AAAA'}], 'gallery': [],
            'data': {'name': 'Tamsin Holt', 'description': '{{char}} restores old boats.', 'personality': 'Patient.',
                     'scenario': 'A storm.', 'first_mes': 'ahoy', 'mes_example': '', 'creator_notes': '',
                     'extensions': {'backstory': 'Grew up above a chandlery.', 'appearance': 'Tall, freckled, '
                                    'tar on {{char}} hands.', **extensions}}}
    if avatar:
        data['avatar'] = 'data:image/png;base64,' + base64.b64encode(avatar).decode()
    return envelope('marinara_character', data)


def test_a_marinara_character_brings_backstory_appearance_and_avatar(client, companion):
    made = bring(client, 'Tamsin.marinara.json', as_json(character(tiny_png())))
    definition = made['companion']['version']['definition']
    assert made['format'] == 'Marinara Engine character'
    assert definition['background'] == 'Tamsin Holt restores old boats.\n\nBackstory:\nGrew up above a chandlery.'
    assert definition['appearance'] == 'Tall, freckled, tar on Tamsin Holt hands.'
    assert made['picture'] is True and made['portrait'] is True
    references = client.get('/api/lora/references').json()['references']
    assert len(references) == 1
    assert made['companion']['portrait_reference_id'] == references[0]['id']


def test_a_marinara_character_without_an_avatar_still_comes(client, companion):
    made = bring(client, 'Tamsin.marinara.json', as_json(character()))
    assert made['picture'] is False and made['portrait'] is False
    assert made['companion']['version']['name'] == 'Tamsin Holt'


def test_a_broken_avatar_is_left_behind(client, companion):
    value = character()
    value['data']['avatar'] = 'data:image/png;base64,not base64!'
    assert bring(client, 'Tamsin.marinara.json', as_json(value))['picture'] is False


def test_a_marinara_lorebook_belongs_to_the_world(client, companion):
    value = envelope('marinara_lorebook', {'lorebook': {'name': 'Saltmarsh', 'description': 'The bay.'}, 'folders': [],
                                           'entries': [
        {'name': 'Ferry', 'keys': ['ferry'], 'content': 'The ferry stops at nine.', 'enabled': True,
         'constant': False},
        {'name': 'Fog', 'keys': [], 'content': 'Fog most mornings.', 'enabled': True, 'constant': True},
        {'name': 'Pattern', 'keys': ['fer+y'], 'content': 'Regex.', 'enabled': True, 'useRegex': True}]})
    made = bring(client, 'Saltmarsh.marinara.json', as_json(value))
    assert made['format'] == 'Marinara Engine lorebook' and made['companion'] is None
    assert made['book']['name'] == 'Saltmarsh' and made['book']['world'] is True
    assert made['book']['entries'] == 3 and made['book']['off'] == 1


def test_personas_and_other_versions_say_why(client):
    persona = envelope('marinara_persona', {'name': 'Me', 'description': 'Someone.'})
    assert 'persona' in bring(client, 'me.marinara.json', as_json(persona), 422)['detail']
    later = {**character(), 'version': 2}
    assert 'version 1' in bring(client, 'x.marinara.json', as_json(later), 422)['detail']
