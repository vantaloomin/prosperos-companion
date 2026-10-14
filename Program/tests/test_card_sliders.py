"""A character card's own words settle its personality sliders (companion/imports/characters.py `card_sliders`), and
companions imported before that read them once on upgrade (`card_sliders_upgrade`)."""
from test_bring_characters import as_json, bring

from companion.database import decode, encode
from companion.imports.characters import card_read, card_sliders_upgrade
from companion.world import personality

SHY = '{{char}} is a painfully shy, anxious librarian. She is a quiet introvert and a homebody.'


def card(name, description, personality_text=''):
    return {'spec': 'chara_card_v2', 'spec_version': '2.0', 'data': {
        'name': name, 'description': description, 'personality': personality_text, 'scenario': '', 'first_mes': '',
        'mes_example': '', 'creator_notes': '', 'tags': [], 'extensions': {}}}


def marinara(name, description):
    return {'type': 'marinara_character', 'version': 1, 'data': {**card(name, description), 'gallery': [],
                                                                  'sprites': []}}


def levels(sliders):
    return {key: (value['level'], value['source']) for key, value in sliders.items()}


def test_a_card_that_says_who_they_are_only_in_its_description_settles_its_sliders(client):
    made = bring(client, 'Ivy.json', as_json(card('Ivy Moss', SHY)))
    sliders = made['companion']['version']['definition']['personality_sliders']
    assert sliders['social'] == {'level': 0, 'source': 'idea'}
    assert sliders['stress'] == {'level': 2, 'source': 'idea'}
    found = client.post('/api/companion/personality', json={'definition': made['companion']['version']['definition']})
    assert levels(found.json()['sliders'])['social'] == (0, 'idea')


def test_a_marinara_description_settles_sliders_too(client):
    made = bring(client, 'Ivy.marinara.json', as_json(marinara('Ivy Moss', SHY)))
    assert made['companion']['version']['definition']['personality_sliders']['social'] == {'level': 0, 'source': 'idea'}


def test_loud_noises_do_not_make_anyone_outgoing():
    assert personality.from_words('Gets overwhelmed by crowds and loud noises.') == {}
    assert personality.from_words('A painfully shy homebody who hates loud noises.') == {'social': 0}


def older_import(client, name, description, personality_text='', mine=None):
    """A companion imported before cards settled sliders: no sliders stored (or, once saved, the user's own)."""
    made = bring(client, f'{name}.json', as_json(card(name, description, personality_text)))['companion']
    with client.app.state.database.connect(write=True) as connection:
        row = connection.execute('SELECT definition FROM character_versions WHERE id=?',
                                 (made['active_version_id'],)).fetchone()
        definition = {**decode(row['definition']), 'personality_sliders': mine}
        connection.execute('UPDATE character_versions SET definition=? WHERE id=?',
                           (encode(definition), made['active_version_id']))
    return made


def stored(client, version_id):
    with client.app.state.database.connect() as connection:
        row = connection.execute('SELECT definition FROM character_versions WHERE id=?', (version_id,)).fetchone()
    return decode(row['definition'])['personality_sliders']


def test_an_earlier_import_reads_its_card_and_only_rolled_sliders_change(client, companion):
    ivy = older_import(client, 'Ivy Moss', SHY, personality_text='Chatty once she knows you.')
    plain = older_import(client, 'Pat Lee', '{{char}} is an accountant who likes jazz.')
    saved = older_import(client, 'Rue Vale', SHY, mine={'social': {'level': 2, 'source': 'you'}})
    with client.app.state.database.connect(write=True) as connection:
        card_sliders_upgrade(connection)
    after = stored(client, ivy['active_version_id'])
    assert after['social'] == {'level': 2, 'source': 'idea'}  # their own personality field says chatty: kept
    assert after['stress'] == {'level': 2, 'source': 'idea'}  # Rolled, and the card says anxious
    assert sum(value['level'] != 1 for value in after.values()) >= 2
    assert stored(client, plain['active_version_id']) is None  # nothing in the card to read: left alone
    assert stored(client, saved['active_version_id']) == {'social': {'level': 2, 'source': 'you'}}
    assert stored(client, companion['active_version_id']) is None  # made by hand: never touched
    # Once stored, a later change is never read over again.
    changed = {**after, 'stress': {'level': 0, 'source': 'rolled'}}
    with client.app.state.database.connect(write=True) as connection:
        row = connection.execute('SELECT definition FROM character_versions WHERE id=?',
                                 (ivy['active_version_id'],)).fetchone()
        connection.execute('UPDATE character_versions SET definition=? WHERE id=?',
                           (encode({**decode(row['definition']), 'personality_sliders': changed}),
                            ivy['active_version_id']))
        card_sliders_upgrade(connection)
    assert stored(client, ivy['active_version_id'])['stress'] == {'level': 0, 'source': 'rolled'}


def test_from_your_idea_is_never_read_over_by_the_card():
    definition = {'personality': 'Chatty.', 'background': SHY}
    read = card_read(definition, 'seed')
    assert read['social'] == {'level': 2, 'source': 'idea'}  # their own personality says chatty; the card can't undo it
    assert read['stress'] == {'level': 2, 'source': 'idea'}  # a Rolled one the card settles
