from conftest import send

from companion import prompt_library
from companion.life import openers, synthesis
from companion.memory import context
from companion.providers.chat import Chunk

CUSTOM = ('You are {{name}}, a retired lighthouse keeper at heart, whatever your job. Relationship: '
          '{{relationship}}.')


def test_shipped_wording_fills_exactly_as_the_code_did():
    assert prompt_library.text(None, 'chat-character', name='Mira', relationship='friendship') == \
        context.GUIDANCE.format(name='Mira', relationship='friendship')
    assert prompt_library.text(None, 'life-phrasing', name='Mira') == synthesis.RULES.format(name='Mira')
    assert prompt_library.text(None, 'first-texts', reason='a test.') == openers.INSTRUCTION.format(reason='a test.')


def test_every_prompt_is_listed_with_its_default_and_placeholder_help(client):
    listed = {item['name']: item for item in client.get('/api/prompts').json()}
    assert set(listed) == set(prompt_library.PROMPTS)
    chat = listed['chat-character']
    assert chat['group'] == 'Chat and life' and not chat['customized'] and not chat['outdated']
    assert chat['placeholders'] == ['name', 'relationship'] and chat['text'] == chat['default']
    assert '{{name}}' in chat['default'] and '{name}' not in chat['default'].replace('{{name}}', '')
    for item in listed.values():
        assert set(item['placeholder_help']) == set(item['placeholders'])
        assert all(item['placeholder_help'].values()), item['name']


def test_a_reworded_chat_prompt_is_what_the_model_is_told(client, connected, provider):
    saved = client.put('/api/prompts/chat-character', json={'text': CUSTOM}).json()
    assert saved['customized'] and saved['text'] == CUSTOM
    provider.replies = [[Chunk('Evening.'), Chunk('', 'stop')]]
    send(client, 'Hi there', 'client-0001')
    system = provider.requests[0]['system']
    assert 'a retired lighthouse keeper at heart' in system and 'the way a method actor disappears' not in system
    assert '{{name}}' not in system and '{{relationship}}' not in system
    client.delete('/api/prompts/chat-character')
    provider.replies = [[Chunk('Hey.'), Chunk('', 'stop')]]
    send(client, 'Hi again', 'client-0002')
    assert 'the way a method actor disappears' in provider.requests[1]['system']


def test_rewording_the_chat_prompt_never_switches_off_the_in_character_filter(client, connected, provider):
    client.put('/api/prompts/chat-character', json={'text': 'Be {{name}}. {{relationship}}'})
    provider.replies = [[Chunk('Of course I miss you. '), Chunk("As an AI, I can't miss anyone. "),
                         Chunk('Tell me everything.'), Chunk('', 'stop')]]
    reply = send(client, 'Did you miss me?', 'client-0001')['reply']
    assert reply['text'] == 'Of course I miss you. Tell me everything.'


def test_placeholder_typos_are_refused_before_they_reach_a_reply(client):
    missing = client.put('/api/prompts/chat-character', json={'text': 'You are {{name}}.'})
    assert missing.status_code == 422 and '{{relationship}}' in missing.json()['detail']
    typo = client.put('/api/prompts/chat-character', json={'text': 'You are {{nmae}}. {{name}} {{relationship}}'})
    assert typo.status_code == 422 and '{{nmae}}' in typo.json()['detail']
    single = client.put('/api/prompts/chat-character', json={'text': 'You are {name}. {{relationship}}'})
    assert single.status_code == 422 and 'double braces' in single.json()['detail']
    extra = client.put('/api/prompts/picture-description', json={'text': 'Describe it for {{name}}.'})
    assert extra.status_code == 422 and 'has none' in extra.json()['detail']
    assert client.put('/api/prompts/no-such-prompt', json={'text': 'x'}).status_code == 404
    assert not client.get('/api/prompts').json()[0]['customized']


def test_saving_the_default_wording_is_the_same_as_resetting(client):
    default = prompt_library.PROMPTS['first-texts'].default()
    assert not client.put('/api/prompts/first-texts', json={'text': default}).json()['customized']


def test_an_update_to_the_default_keeps_the_users_wording_and_says_so(client, monkeypatch):
    client.put('/api/prompts/chat-character', json={'text': CUSTOM})
    monkeypatch.setattr(context, 'GUIDANCE', context.GUIDANCE + ' A newer line.')
    chat = next(item for item in client.get('/api/prompts').json() if item['name'] == 'chat-character')
    assert chat['customized'] and chat['outdated'] and chat['text'] == CUSTOM
    assert chat['default'].endswith('A newer line.')
    client.put('/api/prompts/chat-character', json={'text': CUSTOM + ' Still mine.'})
    chat = next(item for item in client.get('/api/prompts').json() if item['name'] == 'chat-character')
    assert not chat['outdated']


def test_other_prompts_use_the_users_wording(client):
    client.put('/api/prompts/first-texts', json={'text': 'Text them first, briefly. Reason: {{reason}}'})
    client.put('/api/prompts/memory-suggestions', json={'text': 'List facts as JSON. Reply [] when none.'})
    database = client.app.state.database
    with database.connect() as connection:
        assert prompt_library.text(connection, 'first-texts', reason='x.') == 'Text them first, briefly. Reason: x.'
        assert prompt_library.text(connection, 'memory-suggestions') == 'List facts as JSON. Reply [] when none.'
        assert prompt_library.text(connection, 'picture-description') == prompt_library.PROMPTS[
            'picture-description'].default()


def test_picture_lists_read_back_as_the_builders_own_constants():
    from companion.images import prompts
    assert prompt_library.words('image-moods') == prompts.EXPRESSIONS
    assert prompt_library.words('image-activities') == prompts.PICTURES
    assert prompt_library.words('image-openings') == prompts.OPENINGS
    assert prompt_library.words('image-cameras') == {key: value for key, value in prompts.CAMERAS.items()
                                                     if key != 'scene_both'}
    assert prompt_library.line('image-negative') == prompts.NEGATIVE
    assert 'walk: walking outdoors along a path, hands in {{possessive}} pockets' in \
        prompt_library.PROMPTS['image-activities'].default().splitlines()


def picture(connection, mood='tired', activity='walk'):
    from companion.images import prompts
    event = {'summary': 'Went for a walk.', 'place': '', 'mood': mood, 'activity': activity}
    with prompt_library.reading(connection):
        return prompts.compose('Mira', 'She has short dark hair.', [event], 'Candid, natural-light photograph')


def test_reworded_picture_pieces_are_what_the_picture_prompt_says(client):
    database = client.app.state.database
    with database.connect() as connection:
        before = picture(connection)
    assert 'tired eyes and a weary half-smile' in before and 'hands in her pockets' in before
    moods = prompt_library.PROMPTS['image-moods'].default().replace(
        'tired: tired eyes and a weary half-smile', 'tired: heavy eyelids and a crooked yawn')
    activities = prompt_library.PROMPTS['image-activities'].default().replace(
        'walk: walking outdoors along a path, hands in {{possessive}} pockets',
        'walk: strolling by the river, {{possessive}} scarf blowing')
    cameras = prompt_library.PROMPTS['image-cameras'].default().replace(
        'moment: Shot at eye level on a phone camera', 'moment: Shot on a 35mm film camera')
    for name, text in (('image-moods', moods), ('image-activities', activities), ('image-cameras', cameras)):
        assert client.put(f'/api/prompts/{name}', json={'text': text}).json()['customized']
    assert client.put('/api/prompts/image-negative', json={'text': 'text, logo'}).json()['customized']
    with database.connect() as connection:
        after = picture(connection)
        with prompt_library.reading(connection):
            from companion.images import prompts
            assert prompts.negative() == 'text, logo'
    assert 'heavy eyelids and a crooked yawn' in after and 'strolling by the river, her scarf blowing' in after
    assert after.endswith('Shot on a 35mm film camera, natural colours, realistic skin texture, shallow depth of field.')
    assert 'weary' not in after
    # Outside a request builder the pieces are the defaults.
    assert picture(None) == before


def test_picture_lists_keep_every_name_and_known_placeholders(client):
    default = prompt_library.PROMPTS['image-moods'].default()
    dropped = client.put('/api/prompts/image-moods', json={'text': default.replace('tired: tired eyes and a weary half-smile\n', '')})
    assert dropped.status_code == 422 and 'tired' in dropped.json()['detail']
    activities = prompt_library.PROMPTS['image-activities'].default()
    made_up = client.put('/api/prompts/image-activities', json={'text': activities + '\nskydiving: in free fall'})
    assert made_up.status_code == 422 and 'skydiving' in made_up.json()['detail']
    not_a_line = client.put('/api/prompts/image-moods', json={'text': default + '\njust some words'})
    assert not_a_line.status_code == 422 and 'colon' in not_a_line.json()['detail']
    typo = client.put('/api/prompts/image-activities', json={'text': prompt_library.PROMPTS['image-activities'].default()
                      .replace('{{possessive}} pockets', '{{possesive}} pockets')})
    assert typo.status_code == 422 and '{{possesive}}' in typo.json()['detail']
    # A line may drop its placeholder, or its words.
    plain = prompt_library.PROMPTS['image-activities'].default().replace('{{possessive}} pockets', 'the pockets') \
        .replace('workout: mid-workout, slightly out of breath', 'workout:')
    assert client.put('/api/prompts/image-activities', json={'text': plain}).status_code == 200


def test_a_name_a_newer_default_adds_uses_its_default_words(client, monkeypatch):
    from companion.images import prompts
    client.put('/api/prompts/image-moods', json={'text': prompt_library.PROMPTS['image-moods'].default().replace(
        'happy: a wide, easy smile', 'happy: beaming')})
    monkeypatch.setattr(prompts, 'EXPRESSIONS', prompts.EXPRESSIONS | {'grumpy': 'a scowl'})
    with client.app.state.database.connect() as connection, prompt_library.reading(connection):
        found = prompt_library.words('image-moods')
    assert found['happy'] == 'beaming' and found['grumpy'] == 'a scowl'


def test_a_mood_of_their_own_can_be_added(client):
    default = prompt_library.PROMPTS['image-moods'].default()
    assert client.put('/api/prompts/image-moods', json={'text': default + '\ngrumpy: a scowl'}).status_code == 200
    with client.app.state.database.connect() as connection:
        assert 'Her face shows a scowl.' in picture(connection, mood='grumpy')
